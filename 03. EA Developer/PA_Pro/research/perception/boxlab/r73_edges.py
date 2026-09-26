"""r73_edges.py — R73 s.73.3 step 1: what IS the author's edge?

For each of the 119 box-family goldens, take the bars inside the
golden's own drawn span [t0, t1] (minutes -> bar indices) and compute
three edge definitions per side:

  (a) raw       : max high / min low of the span
  (b) drop1     : second-most-extreme wick when the most extreme
                  exceeds it by > tol  (tol = max(1.0p, 0.25*ABR))
  (b2) drop1+tail: (b) PLUS the spec's tail test — only drop when the
                  extreme bar's offending tail > 50% of its range
                  (spec s3.1 FALSE_EXT rule, p217 Fig 5.5)
  (c) cluster2  : the most extreme price touched by >= 2 wicks within
                  tol of each other

Each computed edge is compared to the golden's drawn edge within
tol_px(golden) (the ruler's own tolerance).  Report per definition:
edge hits / total edges, split 68 unreachable vs 51 reachable.
"""
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
from snapshot import tau_of            # noqa: E402
# R78 s.78.4(3) TT: edge_defs/cluster_edge moved to trade_tags.py
# (leaf module the engine can import); re-export keeps every consumer
# (DR_RULES_measure, DR_RULES_S1_measure) on the same function object.
from trade_tags import edge_defs, cluster_edge   # noqa: E402,F401

PIP = 1e4


def main():
    recs = C.load_tune()
    rows = pickle.load(open(
        os.path.join(PERC, "deepresearch", "dr_rows.pkl"), "rb"))
    unreach = {(r["panel"], int(round(r["tau"]))) for r in rows
               if r["n_match"] == 0}

    defs = ["raw", "drop1", "drop1t", "clu"]
    hits = {d: {"un": 0, "re": 0, "un_top": 0, "un_bot": 0,
                "re_top": 0, "re_bot": 0, "un_n": 0, "re_n": 0}
            for d in defs}
    detail = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        abr = CA.abr(rec["date"])
        hp, lp = h, l                      # already pip-scale
        gobjs, _u, _to = EV.gold_objects(rec)
        for g in gobjs:
            if g["spec_type"] not in V2.BOX_TYPES or \
                    not V2.scorable(g, w0, w1):
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            key = (rec["id"], int(round(tau)))
            is_un = key in unreach
            j0 = int(np.searchsorted(m, g["t0"]))
            j1 = int(np.searchsorted(m, g["t1"]))
            j1 = min(max(j1, j0 + 1), len(m) - 1)
            j0 = min(j0, j1)
            h_seg = hp[j0:j1 + 1]
            l_seg = lp[j0:j1 + 1]
            if len(h_seg) == 0:
                continue
            a = abr[min(j1, len(abr) - 1)]
            tol_e = max(1.0, 0.25 * a)
            tol_g = V2.tol_px(g)
            glo, ghi = g["price_lo"] * PIP, g["price_hi"] * PIP
            o_seg = o[j0:j1 + 1]
            c_seg = c[j0:j1 + 1]
            ed = edge_defs(h_seg, l_seg, o_seg, c_seg, tol_e)
            grp = "un" if is_un else "re"
            for d in defs:
                hits[d][grp + "_n"] += 1
                top_ok = abs(ed[d + "_hi"] - ghi) <= tol_g
                bot_ok = abs(ed[d + "_lo"] - glo) <= tol_g
                hits[d][grp] += top_ok and bot_ok
                hits[d][grp + "_top"] += top_ok
                hits[d][grp + "_bot"] += bot_ok
            if is_un:
                detail.append((rec["id"], int(tau), round(ghi, 1),
                               round(glo, 1),
                               round(ed["raw_hi"], 1),
                               round(ed["drop1_hi"], 1),
                               round(ed["clu_hi"], 1),
                               round(ed["raw_lo"], 1),
                               round(ed["drop1_lo"], 1),
                               round(ed["clu_lo"], 1),
                               round(tol_g, 1)))

    print("%-8s %18s %18s %18s %18s" %
          ("def", "68un-both", "68un-edges", "51re-both",
           "51re-edges"))
    for d in defs:
        h = hits[d]
        print("%-8s %7d/%-10d %7d/%-10d %7d/%-10d %7d/%-10d" % (
            d, h["un"], h["un_n"], h["un_top"] + h["un_bot"],
            2 * h["un_n"], h["re"], h["re_n"],
            h["re_top"] + h["re_bot"], 2 * h["re_n"]))
    print("\nunreachable detail (gid,tau,ghi,glo | raw/drop1/clu hi | "
          "raw/drop1/clu lo | tol):")
    for d in detail:
        print("   ", d)
    pickle.dump(dict(hits=hits, detail=detail),
                open(os.path.join(HERE, "_r73_edges.pkl"), "wb"))


if __name__ == "__main__":
    main()
