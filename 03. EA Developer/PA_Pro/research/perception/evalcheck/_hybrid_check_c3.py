"""EVAL-AUDIT independent check of the R60 s.60.3 hybrid count.

"v1 with v0's box family": per panel the scored object set is
  v1 objects (a4b_off @ current V1 hash = C-2 defaults, flags OFF)
    minus v1 box-family objects
    plus v0 box-family objects (m1_v0 @ V0 hash, UNCHANGED).
Clutter on that combined set (LABEL_TF from v1), matching the
gate_pack clutter definition.

Reported per s.60.3.1: box@1, level@1, line@2, bracket@1,
clutter median, margin (panels <= 5.0), paired day-bootstrap CIs
vs v0 (same machinery, seed 20260921, 1000 resamples - EVAL-AUDIT
convention).  Gate per s.60.3.2: box >= 16 hits, other families
within -1 of the v1 row, clutter <= 5.0.  s.60.3.3 extra: added
box ink per panel (v0 box count - v1 box count).

Cache-only / read-only.  Independent code path: does not import
the build lane's _hybrid_v0box.py.
"""
import collections
import glob
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import tau_of, live_records       # noqa: E402
from salience import FAMILY as ENG_FAMILY       # noqa: E402

SEED = 20260921
BOOT = 1000
M1 = (("box", 1), ("level", 1), ("line", 2))
EXTRA = (("bracket", 1),)

H1 = F.code_hash(F.V1_FILES)
H0 = F.code_hash(F.V0_FILES)
V1_VAR = "a4b_off"
V0_VAR = "m1_v0"


def _pickled(eng_hash, variant, rec, w1):
    f = os.path.join(CA.CACHE, "run_%s%s_%s_%s.pkl"
                     % (variant + "_" if variant else "",
                        eng_hash, rec["date"], w1))
    if not os.path.exists(f):
        return None
    try:
        with open(f, "rb") as fh:
            return pickle.load(fh)
    except Exception:
        return None


def _score(r, e):
    """Rank key per R20 s.20.4.2 on the record's OWN engine:
    object-carried score, else born cand_log score, else recency."""
    osc = getattr(e, "_osc", None)
    if osc is None:
        osc = {o.id: getattr(o, "score", None) for o in e.objects}
        e._osc = osc
        e._smap = RK.score_map(e)
    s = osc.get(r["id"])
    if s is None:
        s = e._smap.get((r["type"], r.get("t_birth")))
    if s is not None:
        return (0, -s, -(r.get("t_birth") or 0))
    return (1, -(r.get("t_birth") or 0), 0)


def measure(box_src, other_src, recs):
    """One TUNE pass.  box_src/other_src in {'v0','v1'}."""
    eng = {"v1": (H1, V1_VAR), "v0": (H0, V0_VAR)}
    tau_rows, diag_rows, miss = [], [], 0
    ink_delta = []   # v0-box count - v1-box count per panel
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        hB, vB = eng[box_src]
        hO, vO = eng[other_src]
        eB = _pickled(hB, vB, rec, w1)
        eO = _pickled(hO, vO, rec, w1)
        if eB is None or eO is None:
            miss += 1
            continue
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        eoB = V2.eng_objects(eB, m, w0, w1)
        eoO = V2.eng_objects(eO, m, w0, w1)
        comb = [r for r in eoO if r["type"] != "LABEL_TF"
                and ENG_FAMILY.get(r["type"]) != "box"]
        v0box = [r for r in eoB if r["type"] != "LABEL_TF"
                 and ENG_FAMILY.get(r["type"]) == "box"]
        v1box = [r for r in eoO if r["type"] != "LABEL_TF"
                 and ENG_FAMILY.get(r["type"]) == "box"]
        comb += v0box
        ink_delta.append(len(v0box) - len(v1box))
        emarks = [r for r in eoO if r["type"] == "LABEL_TF"]
        pairs, mpairs = C.match_panel(g2, comb, gmarks, emarks, m,
                                      V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        he = {ei for _, ei in pairs}
        diag = {"panel": rec["id"], "date": rec["date"],
                "g": collections.Counter(), "ghit": collections.Counter(),
                "e": collections.Counter(), "ehit": collections.Counter(),
                "tf_den": 0, "tf_hit": 0,
                "ratio": (len(comb) + len(emarks)) / len(g2)
                         if g2 else np.nan}
        for gi, g in enumerate(g2):
            diag["g"][g["spec_type"]] += 1
            diag["ghit"][g["spec_type"]] += gi in hg
        for ei, er in enumerate(comb):
            diag["e"][er["type"]] += 1
            diag["ehit"][er["type"]] += ei in he
        mbox = [g2[gi] for gi in hg if g2[gi]["spec_type"] == "BOX"]
        hit_marks = {id(gm) for gm, _ in mpairs}
        for gm in gmarks:
            if gm.get("t") is None:
                continue
            if any((g.get("t0") or w0) <= gm["t"] <= (g.get("t1") or w1)
                   for g in mbox):
                diag["tf_den"] += 1
                diag["tf_hit"] += id(gm) in hit_marks
        diag_rows.append(diag)
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is not None and tau >= w0:
                by_tau[min(tau, w1)].append(g)
        for tau, gs in sorted(by_tau.items()):
            rec_t = dict(rec, window=dict(rec["window"], x1=tau))
            eBt = _pickled(hB, vB, rec_t, tau)
            eOt = _pickled(hO, vO, rec_t, tau)
            if eBt is None or eOt is None:
                continue
            liveB, _x = live_records(eBt, m, w0, tau)
            liveO, _y = live_records(eOt, m, w0, tau)
            # per-side score resolution, then one joint sort
            scored = [(r, _score(r, eOt)) for r in liveO
                      if ENG_FAMILY.get(r["type"]) != "box"]
            scored += [(r, _score(r, eBt)) for r in liveB
                       if ENG_FAMILY.get(r["type"]) == "box"]
            scored.sort(key=lambda t: t[1])
            ranked = [r for r, _k in scored]
            fam_ranked = collections.defaultdict(list)
            for r in ranked:
                f = EV.FAMILY.get(r["type"])
                if f:
                    fam_ranked[f].append(r)
            row = {"panel": rec["id"], "date": rec["date"], "tau": tau,
                   "fg": collections.Counter(),
                   "fhit": collections.defaultdict(
                       lambda: collections.Counter())}
            for g in gs:
                fg = EV.FAMILY.get(g["spec_type"])
                if not fg:
                    continue
                row["fg"][fg] += 1
                top_f = fam_ranked.get(fg, [])
                for k in (1, 2, 5):
                    if any(V2.match(g, er, m) for er in top_f[:k]):
                        row["fhit"][fg][k] += 1
            tau_rows.append(row)
    return {"tau": tau_rows, "diag": diag_rows, "miss": miss,
            "ink": ink_delta}


def fam_recall(rows, fam, k):
    return (sum(r["fhit"][fam][k] for r in rows),
            sum(r["fg"][fam] for r in rows))


def day_diff_ci(rows_a, rows_b, fam, k, rng):
    da = collections.defaultdict(lambda: [0, 0])
    db = collections.defaultdict(lambda: [0, 0])
    for r in rows_a:
        da[r["date"]][0] += r["fhit"][fam][k]
        da[r["date"]][1] += r["fg"][fam]
    for r in rows_b:
        db[r["date"]][0] += r["fhit"][fam][k]
        db[r["date"]][1] += r["fg"][fam]
    days = sorted(d for d in da if da[d][1] and db.get(d, [0, 0])[1])
    diffs = np.array([da[d][0] / da[d][1] - db[d][0] / db[d][1]
                      for d in days])
    if not len(diffs):
        return None
    bs = sorted(np.mean([diffs[rng.randrange(len(diffs))]
                         for _ in range(len(diffs))])
                for _ in range(BOOT))
    return (float(diffs.mean()), bs[int(0.025 * (BOOT - 1))],
            bs[int(0.975 * (BOOT - 1))], len(diffs))


def report(tag, res, v0=None, rng=None):
    rows = res["tau"]
    print("%s  (tau-rows %d, panel misses %d)"
          % (tag, len(rows), res["miss"]))
    hits = {}
    for fam, k in M1 + EXTRA:
        h, g = fam_recall(rows, fam, k)
        hits[fam] = h
        s = "  %s@%d %.3f (%d/%d)" % (fam, k, h / g if g else 0, h, g)
        if v0 is not None and rng is not None:
            dd = day_diff_ci(rows, v0["tau"], fam, k, rng)
            if dd:
                s += "  vs v0 %+.3f [%+.3f..%+.3f]" % dd[:3]
        print(s)
    dg = collections.Counter(); gh = collections.Counter()
    en = collections.Counter(); eh = collections.Counter()
    tfd = tfh = 0; ratios = []; seen = set()
    for d in res["diag"]:
        if d["panel"] in seen:
            continue
        seen.add(d["panel"])
        dg.update(d["g"]); gh.update(d["ghit"])
        en.update(d["e"]); eh.update(d["ehit"])
        tfd += d["tf_den"]; tfh += d["tf_hit"]
        if not np.isnan(d["ratio"]):
            ratios.append(d["ratio"])
    margin = sum(x <= 5.0 for x in ratios)
    print("  diag: BOX rec %.3f prec %.3f | PL %.3f | LC %.3f | "
          "LTF-agree %d/%d | clutter med %.2f | margin<=5.0 %d/%d"
          % (gh["BOX"] / dg["BOX"] if dg["BOX"] else 0,
             eh["BOX"] / en["BOX"] if en["BOX"] else 0,
             gh["PATTERN_LINE"] / dg["PATTERN_LINE"]
             if dg["PATTERN_LINE"] else 0,
             gh["LEVEL_CARRIED"] / dg["LEVEL_CARRIED"]
             if dg["LEVEL_CARRIED"] else 0,
             tfh, tfd,
             np.median(ratios) if ratios else 0,
             margin, len(ratios)))
    return hits, np.median(ratios) if ratios else 0, margin


def main():
    recs = C.load_tune()
    print("V1 hash %s var %s | V0 hash %s var %s"
          % (H1, V1_VAR, H0, V0_VAR))
    rng = __import__("random").Random(SEED)
    v0 = measure("v0", "v0", recs)
    report("v0 reference (same machinery)", v0, rng=rng)
    v1 = measure("v1", "v1", recs)
    v1h, _cm, _mg = report("v1 pure (a4b_off, sanity)", v1, v0, rng)
    hyb = measure("v0", "v1", recs)
    hh, cmed, marg = report("HYBRID v1 + v0 box family", hyb, v0, rng)
    ink = np.array(hyb["ink"])
    print("\nbox ink delta per panel (v0box - v1box): "
          "med %+.1f mean %+.2f p75 %+.0f max %+.0f"
          % (np.median(ink), ink.mean(),
             np.percentile(ink, 75), ink.max()))
    print("\ns.60.3.2 gate: box@1 hits %d >=16 %s | "
          "level %d vs v1 %d (d=%+d) | line %d vs %d (d=%+d) | "
          "bracket %d vs %d (d=%+d) | clutter %.2f <=5.0 %s"
          % (hh["box"], hh["box"] >= 16,
             hh["level"], v1h["level"], hh["level"] - v1h["level"],
             hh["line"], v1h["line"], hh["line"] - v1h["line"],
             hh["bracket"], v1h["bracket"],
             hh["bracket"] - v1h["bracket"],
             cmed, cmed <= 5.0))
    def clean(res):
        for r in res["tau"]:
            r["fg"] = dict(r["fg"])
            r["fhit"] = {f: dict(c) for f, c in r["fhit"].items()}
        for d in res["diag"]:
            for kk in ("g", "ghit", "e", "ehit"):
                d[kk] = dict(d[kk])
        return res
    out = os.path.join(HERE, "_hybrid_rows_evalcheck.pkl")
    pickle.dump({"hybrid": clean(hyb), "v0": clean(v0),
                 "v1": clean(v1)}, open(out, "wb"))
    print("rows ->", out)


if __name__ == "__main__":
    main()
