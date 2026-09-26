"""run_eval_levels — evaluate a level proposer on all TUNE panels.

Usage: python run_eval_levels.py [lab|v1] [--limit N] [--params k=v,...]
       [--oracle] [--save file]

Reports per ruler (eval.py + eval_v2):
  LEVEL_CARRIED recall/precision, MINI_LEVEL ditto, trusted-subset
  recall (V1 Tier-A excluded), born levels per panel.
With --oracle: proposal-level coverage (price within golden tol AND
proposal bar inside golden span) — the lab funnel ceiling.
"""

import argparse
import collections
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, os.path.join(_PERC, "linelab"))

import bars_cache  # noqa: E402
import eval as EV  # noqa: E402
import eval_v2 as E2  # noqa: E402
import common as C  # noqa: E402

from anatomy_levels import TIER_A  # noqa: E402

LTYPES = E2.LEVEL_TYPES


def eval_engine(cls, recs, params=None, oracle=False):
    days = bars_cache.days()
    rows = []
    for k, rec in enumerate(recs):
        day = days[rec["date"]]
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        if params is None:
            e = EV.run_engine(cls, day["m"], day["t"], day["o"],
                              day["h"], day["l"], day["c"], w1)
        else:
            eng = cls(params=params)
            eng.cand_log = [] if oracle else None
            for i in range(len(day["m"])):
                if day["m"][i] > w1:
                    break
                # day arrays are pips; update() expects absolute prices
                eng.update(day["t"][i], day["o"][i] / 1e4,
                           day["h"][i] / 1e4, day["l"][i] / 1e4,
                           day["c"][i] / 1e4, cet_min=day["m"][i])
            e = eng
        gobjs, n_un, n_to = EV.gold_objects(rec)
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        eo1 = EV.eng_objects(e, day["m"], w0, w1)
        p1, _ = C.match_panel(gobjs, eo1, [], [], day["m"],
                              EV.match, EV.match_mark, None)
        eo2 = E2.eng_objects(e, day["m"], w0, w1)
        g2 = [g for g in gobjs if E2.scorable(g, w0, w1)]
        p2, _ = C.match_panel(g2, eo2, [], [], day["m"],
                              E2.match, E2.match_mark, E2.score)
        cands = getattr(e, "cand_log", None) or []
        rows.append({"id": rec["id"], "date": rec["date"],
                     "gobjs": gobjs, "g2": g2, "eo1": eo1, "eo2": eo2,
                     "p1": p1, "p2": p2, "cands": cands, "m": day["m"]})
        if (k + 1) % 20 == 0:
            print("  %d/%d" % (k + 1, len(recs)), flush=True)
    return rows


def oracle_stats(rows):
    """Golden level proposed (right-geometry) vs born."""
    out = {}
    for typ in LTYPES:
        g_all = prop = born = 0
        for r in rows:
            for g in r["g2"]:
                if g["spec_type"] != typ:
                    continue
                g_all += 1
                tol = E2.tol_px(g)
                gp = g["price"] * 1e4 if g.get("price") else None
                hit_prop = hit_born = False
                if gp is not None:
                    for cd in r["cands"]:
                        if cd.get("price") is None:
                            continue
                        im = r["m"][min(cd["idx"], len(r["m"]) - 1)]
                        if g["t0"] <= im <= g["t1"] and \
                                abs(cd["price"] - gp) <= tol:
                            hit_prop = True
                            if cd.get("outcome") == "born":
                                hit_born = True
                prop += hit_prop
                # born via ruler match
            mg = {gi for gi, _ in r["p2"]}
            for gi, g in enumerate(r["g2"]):
                if g["spec_type"] == typ and gi in mg:
                    pass
        out[typ] = (prop, g_all)
    return out


def snapshot_stats(rows):
    """Snapshot lens (evalcheck/SNAPSHOT.md): at golden tau=t0+10min,
    count live level objects (t_birth<=tau<=t1) and whether the golden
    is matched by a live object with price within tol."""
    out = {}
    for typ in LTYPES:
        g_all = g_hit = 0
        live_counts = []
        for r in rows:
            for g in r["g2"]:
                if g["spec_type"] != typ or g.get("price") is None:
                    continue
                g_all += 1
                tau = g["t0"] + 10
                tol = E2.tol_px(g)
                live = [eo for eo in r["eo2"] if eo["type"] in LTYPES
                        and eo["t_birth"] <= tau <= eo["t1"]]
                live_counts.append(len(live))
                if any(abs(eo.get("price", -9e9) - g["price"] / 1e-4)
                       <= tol for eo in live):
                    g_hit += 1
        out[typ] = {"g": g_all, "hit": g_hit,
                    "live_med": float(np.median(live_counts)) if
                    live_counts else 0}
    return out


def stats(rows, recs_map):
    res = {}
    for tag, gkey, ekey, pkey in (("evalpy", "gobjs", "eo1", "p1"),
                                ("v2", "g2", "eo2", "p2")):
        per = {}
        for typ in LTYPES:
            g_all = g_hit = e_all = tr_g = tr_hit = 0
            lpp = []
            for r in rows:
                rec = recs_map[r["id"]]
                pairs = r[pkey]
                mg = {gi for gi, _ in pairs}
                el = [eo for eo in r[ekey] if eo["type"] == typ]
                e_all += len(el)
                lpp.append(len(el))
                for gi, g in enumerate(r[gkey]):
                    if g["spec_type"] != typ:
                        continue
                    g_all += 1
                    hit = gi in mg
                    g_hit += hit
                    oi = rec["objects"].index(g)
                    if "%s#%d" % (r["id"], oi) not in TIER_A:
                        tr_g += 1
                        tr_hit += hit
            per[typ] = {"g": g_all, "hit": g_hit, "e": e_all,
                        "recall": g_hit / g_all if g_all else 0,
                        "prec": g_hit / e_all if e_all else 0,
                        "tr": (tr_hit, tr_g),
                        "lpp_med": float(np.median(lpp))}
        res[tag] = per
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=["lab", "v1"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--params", default="")
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--save", default="")
    args = ap.parse_args()
    recs = bars_cache.tune_records()
    if args.limit:
        recs = recs[:args.limit]
    recs_map = {r["id"]: r for r in recs}
    if args.engine == "v1":
        import engine as ENG
        rows = eval_engine(ENG.PerceptionEngine, recs)
    else:
        import levels_lab
        prm = None
        if args.params:
            prm = {}
            for kv in args.params.split(","):
                k, v = kv.split("=")
                prm[k] = json.loads(v)
        rows = eval_engine(levels_lab.LevelLabEngine, recs, prm,
                           oracle=True)
    st = stats(rows, recs_map)
    print("== %s ==" % args.engine)
    for ruler in ("evalpy", "v2"):
        for typ in LTYPES:
            s = st[ruler][typ]
            print("%s %-13s recall %d/%d=%.3f  prec %.3f  "
                  "trusted %d/%d=%.3f  e/panel med %.1f"
                  % (ruler, typ, s["hit"], s["g"], s["recall"],
                     s["prec"], s["tr"][0], s["tr"][1],
                     s["tr"][0] / s["tr"][1] if s["tr"][1] else 0,
                     s["lpp_med"]))
    if args.oracle:
        oc = oracle_stats(rows)
        for typ in LTYPES:
            p, g = oc[typ]
            print("oracle %-13s %d/%d = %.3f" % (typ, p, g,
                                               p / g if g else 0))
    sn = snapshot_stats(rows)
    for typ in LTYPES:
        s = sn[typ]
        print("snapshot %-13s hit %d/%d=%.3f  live-levels med %.1f"
              % (typ, s["hit"], s["g"],
                 s["hit"] / s["g"] if s["g"] else 0, s["live_med"]))
    if args.save:
        slim = [{"id": r["id"],
                 "e2": [x for x in r["eo2"] if x["type"] in LTYPES],
                 "p2": r["p2"],
                 "ncand": len(r["cands"])} for r in rows]
        with open(args.save, "w", encoding="utf8") as f:
            json.dump(slim, f, default=str)
        print("saved", args.save)


if __name__ == "__main__":
    main()
