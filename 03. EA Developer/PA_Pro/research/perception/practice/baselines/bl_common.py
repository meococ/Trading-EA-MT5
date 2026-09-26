"""bl_common.py — shared harness for PA-ATLAS causal baselines (Step 4).

A baseline is a pure function

    emit(t, m, o, h, l, c, abr) -> [obj, ...]

fed the day's M5 bars (all in pips; m = CET minute-of-day) and the
causal ABR(50) array from evalcheck/cache.py.  It returns OBJECTS, each:

    {"type":  "BOX" | "PATTERN_LINE" | "LEVEL_CARRIED",
     "birth": minute the object became drawable (causal),
     "birth_drawn": drawn left edge (may precede birth, like the
                    engine's t_left vs t_birth),
     "die":   minute it was retired, or None,
     "score": ranking score (higher = preferred at top-k),
     # payload
     "lo","hi"        pips            (BOX)
     "bs","be"        containment window in CET minutes (BOX)
     "p0","slope","t0_bar","side"     (PATTERN_LINE, bar-index space)
     "price","side"                   (LEVEL_CARRIED)}

Only objects with birth <= tau and (die is None or die > tau) are
"live" at decision time tau — the causal slice.  Conversion to the
ruler's record shape happens here (fields mirror
evalcheck/eval_v2.py::eng_objects output).  Nothing here edits or
copies evalcheck code — it is imported.
"""
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PRACTICE = os.path.dirname(HERE)
PERC = os.path.dirname(PRACTICE)                    # research/perception
EVC = os.path.join(PERC, "evalcheck")
for _p in (EVC, PERC, os.path.join(PERC, "golden")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import common as C                                  # noqa: E402
import eval as EV                                  # noqa: E402
import eval_v2 as V2                               # noqa: E402
import cache as CA                                  # noqa: E402
from snapshot import tau_of                        # noqa: E402

FKS = (1, 2, 5)
M1 = (("box", 1), ("level", 1), ("line", 2))


def _rec(o, w0, w1, last_min):
    """Baseline object -> eval_v2 engine record (minute space)."""
    t0 = max(o["birth_drawn"], w0)
    t1 = min(o["die"] if o["die"] is not None else last_min, w1)
    r = {"type": o["type"], "why": o.get("why", "baseline"),
         "t0": t0, "t1": t1, "t0_raw": o["birth_drawn"],
         "t1_raw": o["die"] if o["die"] is not None else last_min,
         "t_birth": o["birth"], "id": o.get("id", "b"),
         "events": [], "w0": w0, "w1": w1,
         "_score": o.get("score", 0.0)}
    if o["type"] in V2.BOX_TYPES:
        r["lo"], r["hi"] = o["lo"], o["hi"]
        r["bs"], r["be"] = o["bs"], o["be"]
    elif o["type"] in V2.LINE_TYPES:
        r["p0"], r["slope"], r["t0_bar"] = o["p0"], o["slope"], o["t0_bar"]
        r["side"] = o["side"]
        r["dirn"] = 1 if o["slope"] > 0.05 else \
            (-1 if o["slope"] < -0.05 else 0)
    elif o["type"] in V2.LEVEL_TYPES:
        r["price"], r["side"] = o["price"], o["side"]
    return r


def measure(emit, recs, max_objs=6):
    """Per-(panel,tau) recall@k rows + clutter, mirroring m1_row.measure
    for an external baseline.  emit() runs once per day (up to w1)."""
    tau_rows, diag_rows = [], []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        objs = emit(t, m, o, h, l, c, abr) or []
        # panel-visible objects for clutter (born before w1, alive
        # overlapping [w0,w1])
        vis = [x for x in objs if x["birth"] <= w1 and
               (x["die"] is None or x["die"] > w0)]
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        diag_rows.append({"panel": rec["id"], "date": rec["date"],
                          "n_eng": len(vis), "n_gold": len(g2),
                          "ratio": len(vis) / len(g2) if g2 else np.nan})
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            live = [x for x in objs
                    if x["birth"] <= tau and
                    (x["die"] is None or x["die"] > tau)]
            jlast = int(np.searchsorted(m, tau))
            jlast = min(jlast, len(m) - 1)
            last_min = int(m[jlast])
            recs_live = [_rec(x, w0, tau, last_min) for x in live]
            recs_live.sort(key=lambda r: (-r["_score"], -r["t_birth"]))
            recs_live = recs_live[:max_objs]
            fam_ranked = collections.defaultdict(list)
            for r in recs_live:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_ranked[f].append(r)
            row = {"panel": rec["id"], "date": rec["date"], "tau": tau,
                   "fg": collections.Counter(),
                   "fhit": collections.defaultdict(
                       lambda: collections.Counter()),
                   "n_live": len(recs_live)}
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                row["fg"][fg] += 1
                top_f = fam_ranked.get(fg, [])
                for k in FKS:
                    if any(V2.match(g, er, m) for er in top_f[:k]):
                        row["fhit"][fg][k] += 1
            tau_rows.append(row)
    return {"tau": tau_rows, "diag": diag_rows}


def report(tag, res):
    rows, d = res["tau"], res["diag"]
    ratios = [x["ratio"] for x in d if not np.isnan(x["ratio"])]
    print("%s  (tau-rows %d, panels %d)" % (tag, len(rows), len(d)))
    for fam, k in M1:
        g = sum(r["fg"][fam] for r in rows)
        h = sum(r["fhit"][fam][k] for r in rows)
        print("  %s@%d %.3f (%d/%d)" % (fam, k, h / g if g else 0, h, g))
    print("  clutter ratio med %.2f  (objects/panel med %.1f)"
          % (float(np.median(ratios)) if ratios else 0.0,
             float(np.median([x["n_eng"] for x in d])) if d else 0.0))
