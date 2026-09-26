"""r73_rankprobe.py — R73 s73.3 step 2b (read-only, follows r73_ladder).

Pool-reach headroom exists (L4 dtol8 -> 8/68, L9/L10 cum -> 10-11/68)
but UIP keeps only the YOUNGEST write <= tau, which caps at 2-3/68.
Question: where do matching cands sit in the <=j_tau stream, and does
any causal hold rule keep them?  Reports, per cell, for each
unreachable golden with a pool hit: rank-from-end of the LAST matching
cand, count of writes after it, and whether the matching cand is the
last write overall.
"""
import glob
import os
import pickle
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)
sys.path.insert(0, HERE)

import common as C                      # noqa: E402
import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import cache as CA                     # noqa: E402
from snapshot import tau_of            # noqa: E402
from r73_ladder import enum_stream, BASE, CELLS, ruler_hit  # noqa: E402

CELL_SUB = ["L4_dtol8", "L9_cum", "L10_cum_clu"]


def main():
    rows = pickle.load(open(
        os.path.join(PERC, "deepresearch", "dr_rows.pkl"), "rb"))
    unreach = {(r["panel"], int(round(r["tau"])))
               for r in rows if r["n_match"] == 0}
    pan_date = {r["panel"]: r["date"] for r in rows}
    pan_taus = defaultdict(list)
    for r in rows:
        pan_taus[r["date"]].append(int(round(r["tau"])))
    date_tau = {d: max(v) for d, v in pan_taus.items()}

    streams = {}
    for d, tau in sorted(date_tau.items()):
        fs = glob.glob(os.path.join(
            CA.CACHE, "run_c1r_p_base_ee2cbf12*_%s_*.pkl" % d))
        have = {int(os.path.basename(f).rsplit("_", 1)[1][:-4]): f
                for f in fs}
        f = have[min(t for t in have if t >= tau)]
        e1 = pickle.load(open(f, "rb"))
        pivs = sorted(e1.book.seq, key=lambda p: (p.t_conf, p.t_ext))
        _t, m, o, h, l, c = CA.bars(d)
        streams[d] = dict(pivs=pivs, m=m, h=h, l=l, abr=CA.abr(d))

    cell_streams = defaultdict(dict)
    for d, st in streams.items():
        for name in CELL_SUB:
            P = dict(BASE)
            P.update(CELLS[name])
            cell_streams[d][name] = enum_stream(
                st["pivs"], st["h"], st["l"], st["abr"], P)

    recs = C.load_tune()
    for name in CELL_SUB:
        det = []
        for rec in recs:
            d = rec["id"]
            dt = pan_date.get(d)
            if dt not in streams:
                continue
            w0 = rec["window"]["x0"]
            w1 = rec["window"]["x1"] or 1439
            m = streams[dt]["m"]
            nb = len(m)
            gobjs, _u, _to = EV.gold_objects(rec)
            for g in gobjs:
                if g["spec_type"] not in V2.BOX_TYPES or \
                        not V2.scorable(g, w0, w1):
                    continue
                tau = tau_of(g)
                if tau is None or tau < w0:
                    continue
                tau = min(tau, w1)
                key = (d, int(round(tau)))
                if key not in unreach:
                    continue
                j_tau = min(int(np.searchsorted(m, tau)), nb - 1)
                pool = [cd for cd in cell_streams[dt][name]
                        if cd["born"] <= j_tau]
                if not pool:
                    continue
                hits = [i for i, cd in enumerate(pool)
                        if ruler_hit(g, cd, m, tau, w0, w1)]
                if not hits:
                    continue
                last_hit = hits[-1]
                det.append((key, len(pool), len(pool) - 1 - last_hit,
                            last_hit == len(pool) - 1,
                            len(hits)))
        print("== %s: unreach goldens with pool hit: %d" %
              (name, len(det)))
        for key, npl, after, is_last, nh in sorted(det):
            print("   %-7s pool=%4d  writes_after_match=%3d  "
                  "match_is_last=%s  n_hits=%d" %
                  (key[0] + "@" + str(key[1]), npl, after, is_last, nh))
        if det:
            aft = [x[2] for x in det]
            print("   writes_after_match: med %.0f  p90 %.0f" %
                  (np.median(aft), np.percentile(aft, 90)))


if __name__ == "__main__":
    main()
