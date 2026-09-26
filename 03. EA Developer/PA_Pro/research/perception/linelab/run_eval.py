"""run_eval — evaluate an engine class on all TUNE panels under both
rulers (eval.py post-R9.1 conversion + evalcheck/eval_v2.py).

Usage: python run_eval.py [lab|v0|v1] [--limit N]

Reports PATTERN_LINE recall / precision overall, per repair stratum,
and on the L1 trusted subset; plus lines-per-panel volume.
"""

import argparse
import json
import os
import sys
from collections import Counter

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, _PERC)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, os.path.join(_PERC, "evalcheck"))
sys.path.insert(0, _HERE)

import bars_cache  # noqa: E402
import eval as EV  # noqa: E402
import eval_v2 as E2  # noqa: E402
import common as C  # noqa: E402

from anatomy import TIER_A  # noqa: E402

LINE_TYPES = ("PATTERN_LINE", "CONTEXT_LINE")


def eval_engine(cls, limit=0, quiet=False):
    """Returns per-panel detail rows + aggregate dict."""
    recs = bars_cache.tune_records()
    if limit:
        recs = recs[:limit]
    days = bars_cache.days()
    rows = []
    for k, rec in enumerate(recs):
        day = days[rec["date"]]
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        e = EV.run_engine(cls, day["m"], day["t"], day["o"], day["h"],
                          day["l"], day["c"], w1)
        gobjs, n_un, n_to = EV.gold_objects(rec)
        for g in gobjs:
            if g.get("t0") is None:
                g["t0"] = w0
            if g.get("t1") is None:
                g["t1"] = w1
        # eval.py column (post-R9.1: t1=last fed bar, no left clip)
        eo1 = EV.eng_objects(e, day["m"], w0, w1)
        p1, _ = C.match_panel(gobjs, eo1, [], [], day["m"],
                              EV.match, EV.match_mark, None)
        # eval_v2 column
        eo2 = E2.eng_objects(e, day["m"], w0, w1)
        g2 = [g for g in gobjs if E2.scorable(g, w0, w1)]
        p2, _ = C.match_panel(g2, eo2, [], [], day["m"],
                              E2.match, E2.match_mark, E2.score)
        rows.append({"id": rec["id"], "gobjs": gobjs, "g2": g2,
                     "eo1": eo1, "eo2": eo2, "p1": p1, "p2": p2})
        if not quiet and (k + 1) % 20 == 0:
            print("  %d/%d" % (k + 1, len(recs)), flush=True)
    return rows


def line_stats(rows):
    """PATTERN_LINE recall/precision under both rulers."""
    out = {}
    for tag, gk, pk in (("evalpy", "gobjs", "p1"), ("v2", "g2", "p2")):
        g_all = g_hit = 0
        e_all = 0
        strat = Counter()
        strat_hit = Counter()
        tr_g = tr_hit = 0
        lpp = []
        for r in rows:
            eo = r["eo1"] if tag == "evalpy" else r["eo2"]
            gl = r[gk]
            pairs = r[pk]
            mg = {gi for gi, _ in pairs}
            nl = sum(1 for eo in eo if eo["type"] in LINE_TYPES)
            lpp.append(nl)
            for gi, g in enumerate(gl):
                if g["spec_type"] != "PATTERN_LINE":
                    continue
                g_all += 1
                rm = g.get("repair_method") or "none"
                strat[rm] += 1
                hit = gi in mg
                g_hit += hit
                strat_hit[rm] += hit
                key = "%s#%d" % (r["id"],
                                 r["gobjs"].index(g)
                                 if g in r["gobjs"] else -1)
                # robust key: position in gobjs == position in objects
                # usable order — compute differently below
            # trusted subset via object list position
            objs = [o for o in r["gobjs"]
                    if o["spec_type"] == "PATTERN_LINE"]
            for gi, g in enumerate(gl):
                if g["spec_type"] != "PATTERN_LINE":
                    continue
                pass
        out[tag] = None
    return out


def line_stats2(rows):
    """Cleaner: rebuild golden line index -> (panel,obj) map once."""
    res = {}
    for tag, gkey, ekey, pkey in (("evalpy", "gobjs", "eo1", "p1"),
                                ("v2", "g2", "eo2", "p2")):
        g_all = g_hit = e_all = 0
        strat, strat_hit = Counter(), Counter()
        tr_g = tr_hit = 0
        lpp = []
        for r in rows:
            pairs = r[pkey]
            mg = {gi for gi, _ in pairs}
            me = {ei for _, ei in pairs}
            # index of each gobj within rec["objects"] to recover #idx
            for gi, g in enumerate(r[gkey]):
                if g["spec_type"] != "PATTERN_LINE":
                    continue
                g_all += 1
                rm = g.get("repair_method") or "none"
                strat[rm] += 1
                if gi in mg:
                    g_hit += 1
                    strat_hit[rm] += 1
                # trusted subset: key by (panel, ordinal among PL objs)
            e_lines = [eo for eo in r[ekey] if eo["type"] in LINE_TYPES]
            e_all += len(e_lines)
            lpp.append(len(e_lines))
        res[tag] = {"g": g_all, "hit": g_hit, "e": e_all,
                    "recall": g_hit / g_all if g_all else 0,
                    "prec": g_hit / e_all if e_all else 0,
                    "strat": strat, "strat_hit": strat_hit,
                    "lpp_med": float(np.median(lpp)),
                    "lpp_p90": float(np.percentile(lpp, 90))}
    return res


def trusted_stats(rows):
    """Recall on the L1 trusted subset (Tier-A excluded), both rulers."""
    # rebuild golden (panel,obj) identity: gobjs keep original index?
    # gold_objects drops unusable -> need original positions.  We
    # recompute: usable objects in original order keep position.
    recs = {r["id"]: r for r in bars_cache.tune_records()}
    res = {}
    for tag, gkey, pkey in (("evalpy", "gobjs", "p1"), ("v2", "g2", "p2")):
        g_all = g_hit = 0
        for r in rows:
            rec = recs[r["id"]]
            mg = {gi for gi, _ in r[pkey]}
            for gi, g in enumerate(r[gkey]):
                if g["spec_type"] != "PATTERN_LINE":
                    continue
                # find original object index in rec["objects"]
                oi = rec["objects"].index(g)
                key = "%s#%d" % (r["id"], oi)
                if key in TIER_A:
                    continue
                g_all += 1
                g_hit += gi in mg
        res[tag] = (g_hit, g_all)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=["lab", "v0", "v1"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--save", default="")
    args = ap.parse_args()
    if args.engine == "lab":
        import lines_lab
        cls = lines_lab.LineLabEngine
    elif args.engine == "v0":
        import engine_v0
        cls = engine_v0.PerceptionEngine
    else:
        import engine
        cls = engine.PerceptionEngine
    rows = eval_engine(cls, limit=args.limit)
    stats = line_stats2(rows)
    tr = trusted_stats(rows)
    tag = args.engine
    print("== %s ==" % tag)
    for ruler in ("evalpy", "v2"):
        s = stats[ruler]
        print("%s: PATTERN_LINE recall %d/%d=%.3f  prec %.3f  "
              "lines/panel med %.1f p90 %.1f  trusted %d/%d=%.3f"
              % (ruler, s["hit"], s["g"], s["recall"], s["prec"],
                 s["lpp_med"], s["lpp_p90"],
                 tr[ruler][0], tr[ruler][1],
                 tr[ruler][0] / tr[ruler][1] if tr[ruler][1] else 0))
        for rm in sorted(s["strat"]):
            print("    %-20s %d/%d" % (rm, s["strat_hit"][rm],
                                       s["strat"][rm]))
    if args.save:
        slim = [{"id": r["id"],
                 "e1": [x for x in r["eo1"] if x["type"] in LINE_TYPES],
                 "e2": [x for x in r["eo2"] if x["type"] in LINE_TYPES],
                 "p1": r["p1"], "p2": r["p2"]} for r in rows]
        with open(args.save, "w", encoding="utf8") as f:
            json.dump(slim, f, default=str)
        print("saved", args.save)


if __name__ == "__main__":
    main()
