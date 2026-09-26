"""R81 s.81.5(1) TT-2 report (build lane, INFO).

Companion to _tt_report.py: measures the LIFETIME tags (line_broken,
line_cuts_bodies, stale_far) and the trade view they define.

LIVE:  DR_RULES_live.jsonl rows -> the same pickled C-3 engine at the
       row's tau -> TT.object_stats recomputed -> v1-only tags vs
       v1+v2 tags -> tradeable fraction per family.
GOLDEN: DR_RULES_golden.jsonl rows -> causal engine arrays -> TT-2
       predicates evaluated directly on the author's objects, with
       documented golden conventions:
       - golden line value at bar j = linear between (t0,price0) and
         (t1,price1) - converted to per-bar p0/slope/t0 so the same
         TT.s_* predicates run on both sides;
       - golden lines carry no defended side -> line_broken uses the
         either-direction convention (side=None);
       - golden birth ~ t0 (same as DR_RULES_measure).
"""
import json, os, sys, collections

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
import DR_RULES_measure as DM
from _tt_report import tags_live, tags_golden, eng_arrays

DR = os.path.join(_HERE, "deepresearch")
PIP = 1e4
V2TAGS = ("line_broken", "line_cuts_bodies", "stale_far")


def v2_stats_gold(g, fam, m, o, h, l, c, ema, abr, tau):
    """TT-2 measures on one golden object (spec_type already mapped
    to fam).  Returns dict of lbroken/lcuts/stale measures or {} when
    not evaluable."""
    t0, t1 = DM.to_min(g.get("t0")), DM.to_min(g.get("t1"))
    end = min(t1 if t1 is not None else tau, tau)
    j1 = DM.jle(m, end)
    j0 = DM.jge(m, t0) if t0 is not None else None
    if j0 is None or j1 is None or j0 > j1:
        return {}
    jb = j0
    out = {}
    if fam == "line":
        p0, p1 = g.get("price0"), g.get("price1")
        if p0 is None or p1 is None or t1 is None or t1 <= t0:
            return {}
        p0p, p1p = p0 * PIP, p1 * PIP
        slope_pb = (p1p - p0p) * 5.0 / (t1 - t0)   # M5 book
        # golden dir: 'up' = rising support (defended side below),
        # 'down' = falling resistance (defended side above)
        side = {"down": "top", "up": "bottom"}.get(g.get("dir"))
        gg = {"p0": p0p, "slope": slope_pb, "t0": j0,
              "side": side}
        out.update(TT.s_line_broken(gg, jb, j1, c, abr))
        out.update(TT.s_line_cuts(gg, j0, j1, o, c, abr))
        sg = gg
    elif fam == "box":
        if g.get("price_lo") is None:
            return {}
        sg = {"bottom": g["price_lo"] * PIP,
              "top": g["price_hi"] * PIP}
    elif fam == "level":
        if g.get("price") is None:
            return {}
        sg = {"price": g["price"] * PIP}
    else:
        return {}
    out.update(TT.s_stale_far(fam, sg, jb, j1, h, l, c, abr))
    return out


def report(rows_live2, rows_gold2):
    for title, rows in rows_live2 + rows_gold2:
        print("\n== %s ==" % title)
        for fam in ("box", "level", "line"):
            rs = [r for r in rows if r["fam"] == fam]
            if not rs:
                continue
            n = len(rs)
            # R81 semantics: tradeable = no TRADE_VIEW_HIDE tag.
            # v1 column = hide-set against v1 tags only (lone_edge
            # is a fact, never hides, under both columns).
            t1 = sum(1 for r in rs if TT.tradeable(r["tags_v1"]))
            t2 = sum(1 for r in rs if TT.tradeable(r["tags_all"]))
            u0 = sum(1 for r in rs if not r["tags_all"])
            per = collections.Counter(t for r in rs for t in
                                      r["tags_all"])
            ne = collections.Counter(t for r in rs
                                     for t in r["v2_na"])
            print("%-6s n=%d | tradeable v1-tags %d = %.3f | "
                  "v1+v2-tags %d = %.3f | untagged %d = %.3f" %
                  (fam, n, t1, t1 / n, t2, t2 / n, u0, u0 / n))
            for k in sorted(per):
                extra = (" (n/e %d)" % ne[k]) if ne[k] else ""
                print("        %-17s %3d = %.3f%s" %
                      (k, per[k], per[k] / n, extra))


def main():
    live = [json.loads(x) for x in
            open(os.path.join(DR, "DR_RULES_live.jsonl"),
                 encoding="utf8")]
    gold = [json.loads(x) for x in
            open(os.path.join(DR, "DR_RULES_golden.jsonl"),
                 encoding="utf8")]

    # ---- LIVE: recompute stats on the pickled engine at each tau ---
    live_by = collections.defaultdict(list)
    for r in live:
        live_by[(r["panel"], r["tau"])].append(r)
    live2 = []
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
                t_all = TT.tags_from_stats(fam, st)
                live2.append({"fam": r["fam"],
                              "tags_v1": tags_live(r),
                              "tags_all": t_all,
                              "v2_na": [t for t in V2TAGS
                                        if (t == "line_broken" and
                                            "lbroken" not in st) or
                                        (t == "line_cuts_bodies" and
                                         "lcuts" not in st) or
                                        (t == "stale_far" and
                                         "stale" not in st)]})

    # ---- GOLDEN: TT-2 predicates on the author's objects ----------
    gold_by = collections.defaultdict(list)
    for r in gold:
        gold_by[(r["panel"], r["tau"])].append(r)
    gold2 = []
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
                fam = r["fam"]
                st2 = v2_stats_gold(g, fam, m, o, h, l, c, ema,
                                    abr, tau)
                t_all = set(tags_golden(r))
                if st2.get("lbroken"):
                    t_all.add("line_broken")
                if st2.get("lcuts"):
                    t_all.add("line_cuts_bodies")
                if st2.get("stale"):
                    t_all.add("stale_far")
                gold2.append({"fam": fam, "tags_v1": tags_golden(r),
                              "tags_all": t_all,
                              "v2_na": [t for t in V2TAGS if
                                        (t == "line_broken" and
                                         "lbroken" not in st2) or
                                        (t == "line_cuts_bodies" and
                                         "lcuts" not in st2) or
                                        (t == "stale_far" and
                                         "stale" not in st2)]})

    report([("LIVE objects at golden-decision taus "
             "(DR_RULES_live)", live2)],
           [("GOLDEN objects at taus (DR_RULES_golden; author "
             "compliance)", gold2)])


if __name__ == "__main__":
    main()
