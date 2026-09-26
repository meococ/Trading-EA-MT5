"""R78 s.78.4(3) TT report (build lane, INFO).

1) PROOF the predicates are single-source: DR_RULES_measure imports
   them back from trade_tags.py; recompute stats on a sample of
   DR_RULES_golden.jsonl rows -> identical fields.
2) PROOF the engine path reproduces research stats: TT.object_stats
   on cached C-3 engines at each row's tau == DR_RULES_live.jsonl
   fields.
3) MEASURE: tradeable fraction + per-tag rates, per family, on live
   objects at golden-decision taus (DR_RULES_live.jsonl) and on
   golden objects (DR_RULES_golden.jsonl; should reproduce DR-RULES
   Part B within rounding).
"""
import json, os, sys, pickle, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, os.path.join(_HERE, "deepresearch"))
sys.path.insert(0, os.path.join(_HERE, "boxlab"))
sys.path.insert(0, _HERE)

import numpy as np
import trade_tags as TT
import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
import DR_RULES_measure as DM

DR = os.path.join(_HERE, "deepresearch")


def eng_arrays(e):
    """the same m,o,h,l,c,ema,abr,pivots DR_RULES_measure builds from
    a pickled engine."""
    m = np.array([b["cet_min"] for b in e.bars])
    o = np.array([b["o"] for b in e.bars])
    h = np.array([b["h"] for b in e.bars])
    l = np.array([b["l"] for b in e.bars])
    c = np.array([b["c"] for b in e.bars])
    return m, o, h, l, c, np.asarray(e.ema), np.asarray(e.abr), \
        e.book.seq


# ---- tag sets ----------------------------------------------------------
# live rows: same stats object_stats writes -> same predicate.
def tags_live(r):
    fam = r["fam"]
    tags = set()
    if fam == "box":
        if r.get("c1_abr") is not None and r["c1_abr"] > 1.0:
            tags.add("daylight")
        if r.get("c3_r_win") is not None and r["c3_r_win"] >= 3.0:
            tags.add("shock_inside")
        if r.get("c4_r_win") is not None and r["c4_r_win"] >= 4:
            tags.add("impulse_inside")
        # live objects carry no label precision: engine-side analog
        # of C6g uses the module's 5.0p ruler-default constant.
        if r.get("c6_maxd") is not None and \
                r["c6_maxd"] > TT.LONE_EDGE_TOL_PIPS:
            tags.add("lone_edge")
    if fam == "level":
        if r.get("c7_sw_full") is not None and r["c7_sw_full"] > 2:
            tags.add("zombie")
        if r.get("c8_beyond_abr_anch") is not None and \
                r["c8_beyond_abr_anch"] >= 1:
            tags.add("superseded")
    if fam == "line":
        if r.get("c7_sw_span") is not None and r["c7_sw_span"] > 2:
            tags.add("zombie")
    if fam in ("box", "level", "line") and r.get("c2_s") is not None \
            and r["c2_s"] > TT.C2_Q95[fam]:
        tags.add("steep")
    return tags


def tags_golden(r):
    """Same tags evaluated on the author objects.  Where the golden
    schema lacks the engine-window stat (C8a anchor, C7s drawn span),
    the closest evaluable stat stands in - matches DR-RULES Part B."""
    fam = r["fam"]
    tags = set()
    if fam == "box":
        if r.get("c1_abr") is not None and r["c1_abr"] > 1.0:
            tags.add("daylight")
        if r.get("c3_r_win") is not None and r["c3_r_win"] >= 3.0:
            tags.add("shock_inside")
        if r.get("c4_r_win") is not None and r["c4_r_win"] >= 4:
            tags.add("impulse_inside")
        if r.get("c6_maxd") is not None and r.get("tol_g") is not None \
                and r["c6_maxd"] > r["tol_g"]:
            tags.add("lone_edge")
    if fam == "level":
        if r.get("c7_sw_full") is not None and r["c7_sw_full"] > 2:
            tags.add("zombie")
        if r.get("c8_beyond_abr") is not None and \
                r["c8_beyond_abr"] >= 1:
            tags.add("superseded")
    if fam == "line":
        # golden C7s not evaluable in DR-RULES; c7_sw (birth->end) is
        # the closest measured span stat.
        if r.get("c7_sw") is not None and r["c7_sw"] > 2:
            tags.add("zombie")
    if fam in ("box", "level", "line") and r.get("c2_s") is not None \
            and r["c2_s"] > TT.C2_Q95[fam]:
        tags.add("steep")
    return tags


def frac(rows, fn):
    fams = collections.defaultdict(list)
    for r in rows:
        if r["fam"] in ("box", "level", "line"):
            fams[r["fam"]].append(fn(r))
    out = {}
    for fam, ts in fams.items():
        n = len(ts)
        tr = sum(1 for t in ts if not t)
        pertag = collections.Counter(t for s in ts for t in s)
        out[fam] = {"n": n, "tradeable": tr,
                    "frac": tr / n if n else None,
                    "tags": {k: (pertag[k], pertag[k] / n)
                             for k in sorted(pertag)}}
    return out


def main():
    live = [json.loads(x) for x in
            open(os.path.join(DR, "DR_RULES_live.jsonl"),
                 encoding="utf8")]
    gold = [json.loads(x) for x in
            open(os.path.join(DR, "DR_RULES_golden.jsonl"),
                 encoding="utf8")]

    # ---- PROOF 1: single-source predicates reproduce golden stats ---
    print("== proof 1: DR_RULES_measure (imported fns) vs stored "
          "golden rows ==")
    gold_by = collections.defaultdict(list)
    for r in gold:
        gold_by[(r["panel"], r["tau"])].append(r)
    n_ok = n_tot = 0
    for rec in C.load_tune():
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, rec["window"]["x0"],
                                            w1)]
        rows_here = [r for (p, tau), rs in gold_by.items()
                     if p == rec["id"] for r in rs]
        if not rows_here:
            continue
        by_tau = collections.defaultdict(list)
        for r in rows_here:
            by_tau[r["tau"]].append(r)
        for tau, trs in sorted(by_tau.items()):
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            m, o, h, l, c, ema, abr, pivots = eng_arrays(e)
            for r in trs:
                g = g2[r["gi"]] if r["gi"] < len(g2) else None
                if g is None:
                    continue
                st = DM.gold_stats(g, m, o, h, l, c, ema, abr, pivots,
                                   tau, w1)
                n_tot += 1
                keys = [k for k in ("c1_abr", "c2_s", "c3_r", "c4_r",
                                    "c6_maxd", "c7_sw", "c7_sw_full",
                                    "c8_beyond_abr")
                        if r.get(k) is not None]
                same = all(st.get(k) is not None and
                           abs(st[k] - r[k]) < 1e-6 for k in keys)
                n_ok += same
            if n_tot >= 80:
                break
        if n_tot >= 80:
            break
    print("golden rows recomputed identical: %d/%d" % (n_ok, n_tot))

    # ---- PROOF 2: engine object_stats == live-row stats --------------
    print("== proof 2: TT.object_stats on cached engines vs "
          "DR_RULES_live ==")
    live_by = collections.defaultdict(list)
    for r in live:
        live_by[(r["panel"], r["tau"])].append(r)
    n_ok = n_tot = 0
    checked = 0
    for rec in C.load_tune():
        rows_here = [r for (p, tau), rs in live_by.items()
                     if p == rec["id"] for r in rs]
        if not rows_here:
            continue
        by_tau = collections.defaultdict(list)
        for r in rows_here:
            by_tau[r["tau"]].append(r)
        for tau, trs in sorted(by_tau.items()):
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            nfed = len(e.bars) - 1
            objs = {ob.id: ob for ob in e.objects}
            for r in trs:
                ob = objs.get(r["id"])
                if ob is None:
                    continue
                fam, st = TT.object_stats(ob, nfed, e.bars,
                                          e.ema, e.abr, e.book.seq)
                n_tot += 1
                keys = [k for k in ("c1_abr", "c2_s", "c3_r", "c4_r",
                                    "c3_r_win", "c4_r_win", "c6_maxd",
                                    "c7_sw", "c7_sw_span", "c7_sw_full",
                                    "c8_beyond_abr",
                                    "c8_beyond_abr_anch")
                        if r.get(k) is not None]
                same = all(st.get(k) is not None and
                           abs(st[k] - r[k]) < 1e-6 for k in keys)
                if not same:
                    print("  MISMATCH", rec["id"], r["id"], tau,
                          {k: (st.get(k), r.get(k)) for k in keys
                           if st.get(k) is None or
                           abs(st.get(k, 0) - r.get(k, 0)) > 1e-6})
                n_ok += same
        checked += 1
        if checked >= 12:
            break
    print("live rows identical: %d/%d" % (n_ok, n_tot))

    # ---- MEASURE -----------------------------------------------------
    print("\n== LIVE objects at golden-decision taus "
          "(DR_RULES_live) ==")
    res = frac(live, tags_live)
    for fam in ("box", "level", "line"):
        d = res.get(fam)
        if not d:
            continue
        print("%-6s n=%d tradeable %d = %.3f" %
              (fam, d["n"], d["tradeable"], d["frac"]))
        for k, (c_, f_) in d["tags"].items():
            print("        %-15s %d = %.3f" % (k, c_, f_))
    print("\n== GOLDEN objects at taus (DR_RULES_golden) ==")
    res = frac(gold, tags_golden)
    for fam in ("box", "level", "line"):
        d = res.get(fam)
        if not d:
            continue
        print("%-6s n=%d tradeable %d = %.3f" %
              (fam, d["n"], d["tradeable"], d["frac"]))
        for k, (c_, f_) in d["tags"].items():
            print("        %-15s %d = %.3f" % (k, c_, f_))


if __name__ == "__main__":
    main()
