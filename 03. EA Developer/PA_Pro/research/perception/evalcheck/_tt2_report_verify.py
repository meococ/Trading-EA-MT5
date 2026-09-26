"""EVAL-AUDIT independent recount of build's 28-TT2 table.

LIVE  leg: DR_RULES_live.jsonl rows -> pickled C-3 engine at the
           row's tau -> TT.object_stats -> tags -> tradeable
           fraction per family (v1 hide-set vs full hide-set) and
           per-tag rates.
GOLDEN leg: DR_RULES_golden.jsonl rows -> engine causal arrays at
           tau -> golden geometry converted to the TT predicate
           schema (per-bar slope, side inferred from dir, birth~t0)
           -> same tradeable/tag counts.

The predicates themselves are verified separately: unit tests in
test_engine_v1 + my own in-file recompute in _tt2_on_verify.py.
This script independently re-derives the row construction and
counting, not the predicates.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "deepresearch"))

import numpy as np                              # noqa: E402
import trade_tags as TT                         # noqa: E402
import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import DR_RULES_measure as DM                   # noqa: E402

PERC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DR = os.path.join(PERC, "deepresearch")
PIP = 1e4
V1_HIDE = TT.TRADE_VIEW_HIDE - {"line_broken", "line_cuts_bodies",
                               "stale_far"}
# v1 tag set reproduced from DR_RULES_report/make_pass conventions
# (the same tags the TT v1 facts emitted): box daylight/steep/
# shock_inside/impulse_inside/lone_edge; level steep/zombie/
# superseded; line steep/zombie.  v1 tradeable = no hide tag
# (lone_edge never hides).
V1_TAGS = {"daylight", "steep", "shock_inside", "impulse_inside",
           "lone_edge", "zombie", "superseded"}


def gold_v2_stats(g, fam, m, o, h, l, c, abr, tau):
    """Golden-side TT-2 measures; adapter is mine, predicates are
    the shared TT.s_* (unit-tested + recomputed elsewhere)."""
    t0, t1 = DM.to_min(g.get("t0")), DM.to_min(g.get("t1"))
    end = min(t1 if t1 is not None else tau, tau)
    j1 = DM.jle(m, end)
    j0 = DM.jge(m, t0) if t0 is not None else None
    if j0 is None or j1 is None or j0 > j1:
        return {}
    out = {}
    if fam == "line":
        p0, p1 = g.get("price0"), g.get("price1")
        if p0 is None or p1 is None or t1 is None or t1 <= t0:
            return {}
        p0p, p1p = p0 * PIP, p1 * PIP
        slope_pb = (p1p - p0p) * 5.0 / (t1 - t0)
        side = {"down": "top", "up": "bottom"}.get(g.get("dir"))
        gg = {"p0": p0p, "slope": slope_pb, "t0": j0, "side": side}
        out.update(TT.s_line_broken(gg, j0, j1, c, abr))
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
    out.update(TT.s_stale_far(fam, sg, j0, j1, h, l, c, abr))
    return out


def tags_golden_v1(r):
    """v1 tags on a DR_RULES_golden row, golden conventions: tol_g
    for lone_edge, c8_beyond_abr for superseded, c7_sw (birth->end)
    for line zombie - the same mapping the TT v1 report used."""
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
        if r.get("c7_sw") is not None and r["c7_sw"] > 2:
            tags.add("zombie")
    if fam in ("box", "level", "line") and r.get("c2_s") is not None \
            and r["c2_s"] > TT.C2_Q95[fam]:
        tags.add("steep")
    return tags


def main():
    live = [json.loads(x) for x in
            open(os.path.join(DR, "DR_RULES_live.jsonl"),
                 encoding="utf8")]
    gold = [json.loads(x) for x in
            open(os.path.join(DR, "DR_RULES_golden.jsonl"),
                 encoding="utf8")]

    live_rows = []
    live_by = collections.defaultdict(list)
    for r in live:
        live_by[(r["panel"], r["tau"])].append(r)
    for rec in C.load_tune():
        rows_here = [r for (p, tau), rs in live_by.items()
                     if p == rec["id"] for r in rs]
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
                                          e.ema, e.abr,
                                          e.book.seq)
                t_all = TT.tags_from_stats(fam, st)
                live_rows.append({"fam": fam, "tags": t_all})

    gold_rows = []
    gold_by = collections.defaultdict(list)
    for r in gold:
        gold_by[(r["panel"], r["tau"])].append(r)
    for rec in C.load_tune():
        w1 = rec["window"]["x1"] or 1439
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs
              if V2.scorable(g, rec["window"]["x0"], w1)]
        rows_here = [r for (p, tau), rs in gold_by.items()
                     if p == rec["id"] for r in rs]
        by_tau = collections.defaultdict(list)
        for r in rows_here:
            by_tau[r["tau"]].append(r)
        for tau, trs in sorted(by_tau.items()):
            e = DM.pickled(rec["date"], tau)
            if e is None:
                continue
            m = np.array([b["cet_min"] for b in e.bars])
            o = np.array([b["o"] for b in e.bars])
            h = np.array([b["h"] for b in e.bars])
            l = np.array([b["l"] for b in e.bars])
            c = np.array([b["c"] for b in e.bars])
            ema = np.asarray(e.ema)
            abr = np.asarray(e.abr)
            for r in trs:
                g = g2[r["gi"]] if r["gi"] < len(g2) else None
                if g is None:
                    continue
                fam = r["fam"]
                st2 = gold_v2_stats(g, fam, m, o, h, l, c, abr,
                                    tau)
                # v1 tags derived from the golden row's stats fields
                t_v1 = tags_golden_v1(r)
                t_all = set(t_v1)
                if st2.get("lbroken"):
                    t_all.add("line_broken")
                if st2.get("lcuts"):
                    t_all.add("line_cuts_bodies")
                if st2.get("stale"):
                    t_all.add("stale_far")
                gold_rows.append({"fam": fam, "tags_v1": t_v1,
                                  "tags_all": t_all,
                                  "id": (r["panel"], r["gi"])})

    for title, rows in (("LIVE", live_rows), ("GOLDEN", gold_rows)):
        print("== %s ==" % title)
        for fam in ("box", "level", "line"):
            rs = [r for r in rows if r["fam"] == fam]
            if not rs:
                continue
            n = len(rs)
            if title == "LIVE":
                t1 = sum(1 for r in rs
                         if not (r["tags"] & V1_HIDE))
                t2 = sum(1 for r in rs if TT.tradeable(r["tags"]))
                per = collections.Counter(
                    t for r in rs for t in r["tags"])
            else:
                t1 = sum(1 for r in rs
                         if not (r["tags_v1"] & V1_HIDE))
                t2 = sum(1 for r in rs
                         if TT.tradeable(r["tags_all"]))
                per = collections.Counter(
                    t for r in rs for t in r["tags_all"])
            print("%-6s n=%d | v1 %d = %.3f | v1+v2 %d = %.3f"
                  % (fam, n, t1, t1 / n, t2, t2 / n))
            for k in sorted(per):
                print("        %-17s %3d = %.3f"
                      % (k, per[k], per[k] / n))
    # keep ids of golden line_broken rows for spot-check
    print("golden line_broken rows:",
          [r["id"] for r in gold_rows
           if r["fam"] == "line" and "line_broken" in r["tags_all"]][:20])


if __name__ == "__main__":
    main()
