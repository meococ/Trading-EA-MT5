"""c1_lvlsrc.py — R46 follow-on measurement (lab, next-round lever).

For the 38 no-edge BOX goldens under K6: is the author's edge
recoverable from a *prior-structure* level source?  Per golden edge
(price_hi / price_lo), distance to the nearest candidate level of
each type, measured causally (levels built only from bars CLOSED
before golden build_start):

  - pivot:    confirmed swing pivot prices (book.seq analog — too
              sparse per panel, the R44 negative)
  - touch:    touch-density levels — prices where prior bars' wick
              tips clustered (histogram peaks over trailing 12h)
  - round:    round numbers (10-pip grid; 25/50 sub-check)
  - tickdens: tick-density peaks — the session's volume-by-price
              proxy (close-price histogram over prior 24h)

All prices in pips.  Edge tol = eval_v2.tol_px(golden).
Question answered: what fraction of no-edge goldens have BOTH edges
within tol of a level the type can actually produce?
"""
import collections
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, PERC)

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import funnel as F                         # noqa: E402
import cache as CA                         # noqa: E402
from scoreboard import panel_cands         # noqa: E402

H8 = "9acaa206c8d386dc"
VAR = "m1_v1"


def _idx(m, minute):
    return int(np.searchsorted(m, minute))


def _peaks(vals, lo, hi, bw, min_cnt=3):
    """Histogram-peak levels: bins of width bw over [lo,hi]; a bin is
    a level if its count >= min_cnt and >= both neighbours.  Returns
    level prices (bin centres)."""
    if hi <= lo:
        return []
    nb = int((hi - lo) / bw) + 1
    hist, _ = np.histogram(vals, bins=nb, range=(lo, hi))
    out = []
    for j in range(nb):
        l = hist[j - 1] if j else 0
        r = hist[j + 1] if j < nb - 1 else 0
        if hist[j] >= min_cnt and hist[j] >= l and hist[j] >= r:
            out.append(lo + (j + 0.5) * bw)
    return out


def main():
    recs = C.load_tune()
    stat = collections.Counter()
    detail = []
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        pk = os.path.join(
            PERC, "evalcheck", "_cache",
            "run_%s_%s_%s_%s.pkl" % (VAR, H8, rec["date"], w1))
        if not os.path.exists(pk):
            continue
        e = pickle.load(open(pk, "rb"))
        abr = e.abr
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        cands = panel_cands(e, m, w0, w1)
        same = [r for r in cands if EV.FAMILY.get(r["type"]) == "box"]
        for gi, g in enumerate(g2):
            if g["spec_type"] != "BOX" or g.get("price_lo") is None:
                continue
            if any(F.edges_pass(g, r) for r in same):
                continue                      # has right edges
            glo, ghi = g["price_lo"] / C.PIP, g["price_hi"] / C.PIP
            gbs = g.get("build_start") or g.get("t0")
            if gbs is None:
                continue
            ibs = _idx(m, gbs)
            tol = V2.tol_px(g)
            # ---- level sources, causal: bars closed before ibs ----
            piv = [p.price for p in e.book.seq
                   if p.t_conf <= ibs]
            # touch-density: wick-tip histogram over trailing 12h
            # (144 bars), bandwidth = 0.5*ABR
            a = abr[min(ibs, len(abr) - 1)]
            i0 = max(0, ibs - 144)
            tips = np.concatenate([h[i0:ibs], l[i0:ibs]])
            touch = _peaks(tips, glo - 40, ghi + 40, 0.5 * a)
            # tick-density: close-price histogram over prior 24h
            i1 = max(0, ibs - 288)
            tick = _peaks(c[i1:ibs], glo - 40, ghi + 40, 0.5 * a,
                          min_cnt=6)
            # round numbers: 10-pip and 25-pip grids
            def _near(lvls, px):
                if not lvls:
                    return None
                d = min(abs(x - px) for x in lvls)
                return d
            rnd10 = [x for x in np.arange(
                np.floor((glo - 40) / 10) * 10,
                np.ceil((ghi + 40) / 10) * 10 + 1, 10)]
            rnd25 = [x for x in np.arange(
                np.floor((glo - 40) / 25) * 25,
                np.ceil((ghi + 40) / 25) * 25 + 1, 25)]
            res = {}
            for name, lvls in (("pivot", piv), ("touch", touch),
                               ("tick", tick), ("rnd10", rnd10),
                               ("rnd25", rnd25)):
                dt = _near(lvls, ghi)
                db = _near(lvls, glo)
                res[name] = (dt is not None and dt <= tol and
                             db is not None and db <= tol)
                res[name + "_d"] = (dt, db)
            for name in ("pivot", "touch", "tick", "rnd10", "rnd25"):
                stat[name] += res[name]
            detail.append((rec["id"], gi, round(tol, 1),
                           {k: v for k, v in res.items()
                            if not k.endswith("_d")}))
    n = len(detail)
    print("no-edge goldens analysed:", n)
    print("%-8s %-3s %5s  piv touch tick rnd10 rnd25" % ("panel", "gi",
                                                         "tol"))
    for pid, gi, tol, res in detail:
        print("%-8s %-3d %5.1f  %s" % (pid, gi, tol, "  ".join(
            ("Y" if res[k] else ".") for k in
            ("pivot", "touch", "tick", "rnd10", "rnd25"))))
    print("\nboth-edges-within-tol counts:")
    for k in ("pivot", "touch", "tick", "rnd10", "rnd25"):
        print("  %-6s %d/%d" % (k, stat[k], n))


if __name__ == "__main__":
    main()
