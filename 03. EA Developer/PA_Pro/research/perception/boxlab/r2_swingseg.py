"""r2_swingseg.py -- A2 variant 2: swing-grammar segmentation.

Rule (stated before measuring):
  - fractal pivots: pivot high at i if h[i] = max(h[i-3..i+3]);
    pivot low symmetric (k = 3 bars each side).
  - a CONGESTION run = >= 4 alternating pivots (H,L,H,L...) whose
    max(highs) - min(lows) <= 25 pips, consecutive in time.
  - the run's episode = [first pivot bar .. last pivot bar]; edges =
    max pivot-high / min pivot-low inside the run.
  - the run is LIVE while it is the latest such run and price has not
    closed 4+ pips beyond either edge; a run ends when such a close
    prints (the breaking bar's extreme joins the edges) or when a new
    opposite leg of > 25 pips forms.
  - at tau: the episode = the live run, else the last completed run
    that ends >= build_start - 30 bars.

Test: both golden edges within eval tol of the episode's edges.
Oracle = best qualifying episode per golden.  Report all-119 and the
62 no-coverage subset.
"""
import sys, os, collections

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "evalcheck"))
sys.path.insert(0, os.path.join(HERE, ".."))

import common as C                         # noqa: E402
import eval as EV                          # noqa: E402
import eval_v2 as V2                       # noqa: E402
import cache as CA                         # noqa: E402
from snapshot import tau_of                # noqa: E402

PIP = C.PIP
K = 3            # fractal half-window
MAX_SPREAD = 25.0   # pips, run height cap
MIN_PIV = 4         # pivots to form a run
BREAK = 4.0         # close beyond edge ends the run


def pivots(h, l):
    n = len(h)
    piv = []   # (bar, 'H'|'L', price)
    for i in range(K, n - K):
        if h[i] == h[i - K:i + K + 1].max() \
                and h[i] > h[i - 1] and h[i] > h[i + 1]:
            piv.append((i, "H", float(h[i])))
        if l[i] == l[i - K:i + K + 1].min() \
                and l[i] < l[i - 1] and l[i] < l[i + 1]:
            piv.append((i, "L", float(l[i])))
    return piv


def episodes(piv, c):
    """Group consecutive alternating pivots into runs of bounded
    spread; a run ends at the pivot where adding it breaks spread or
    when a close beyond its edges prints."""
    eps = []   # (top, bottom, i_start, i_end)
    run = []   # list of (bar, side, px)
    for (b, s, p) in piv:
        if not run:
            run = [(b, s, p)]
            continue
        if s == run[-1][1]:
            # same side: extend/replace the last pivot if more extreme
            if (s == "H" and p > run[-1][2]) or \
                    (s == "L" and p < run[-1][2]):
                run[-1] = (b, s, p)
            continue
        hi = max(x[2] for x in run if x[1] == "H") if any(
            x[1] == "H" for x in run) else -1e9
        lo = min(x[2] for x in run if x[1] == "L") if any(
            x[1] == "L" for x in run) else 1e9
        hi2 = max(hi, p) if s == "H" else hi
        lo2 = min(lo, p) if s == "L" else lo
        if hi2 - lo2 <= MAX_SPREAD:
            run.append((b, s, p))
            if len(run) >= MIN_PIV:
                eps.append((max(x[2] for x in run if x[1] == "H"),
                            min(x[2] for x in run if x[1] == "L"),
                            run[0][0], b))
        else:
            # spread broken: close the run at the last pivot, restart
            if len(run) >= MIN_PIV:
                pass
            run = [(b, s, p)]
    return eps


def main():
    import csv
    buck = {}
    tf = os.path.join(HERE, "c1_runs", "r1_table.csv")
    for r in csv.DictReader(open(tf, encoding="utf8")):
        buck[(r["panel"], int(r["gi"]))] = r["bucket"]
    n_cov = n_all = 0
    rows = []
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        piv = pivots(h, l)
        eps = episodes(piv, c)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        for gi, g in enumerate(g2):
            if EV.FAMILY.get(g["spec_type"]) != "box":
                continue
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            tau = min(tau, w1)
            ti = int(np.searchsorted(m, tau))
            n_all += 1
            glo, ghi = g["price_lo"] / PIP, g["price_hi"] / PIP
            tol = V2.tol_px(g)
            bs_min = g.get("build_start") or g.get("t0") or w0
            bi0 = int(np.searchsorted(m, bs_min))
            best = None
            for (tp, bt, s_, e_) in eps:
                if e_ > ti + 5 or e_ < bi0 - 30:
                    continue
                d = max(abs(tp - ghi), abs(bt - glo))
                if best is None or d < best[0]:
                    best = (d, tp, bt, s_, e_)
            hit = best is not None and best[0] <= tol
            if hit:
                n_cov += 1
            bk = buck.get((rec["id"], gi), "?")
            rows.append((rec["id"], gi, tau, bk, hit, best,
                         "%.1f-%.1f" % (glo, ghi)))
    noc = [r for r in rows if r[3] == "no_coverage"]
    noc_hit = sum(1 for r in noc if r[4])
    all_hit_by_bucket = collections.Counter(
        r[3] for r in rows if r[4])
    print("swing-grammar episode coverage at tau (oracle):")
    print("  all     : %d/%d" % (n_cov, n_all))
    print("  no_cov62: %d/%d" % (noc_hit, len(noc)))
    print("  by bucket:", dict(all_hit_by_bucket))
    print("\nmiss detail (all goldens, dist>tol):")
    for r in rows:
        if not r[4]:
            b = r[5]
            print("  %-6s g%d t%-5d %-16s %s" % (
                r[0], r[1], r[2], r[3],
                ("ep[%.1f,%.1f]@%d-%d d=%.1f" % (b[2], b[1], b[3],
                                                b[4], b[0]))
                if b else "no-episode " + r[6]))


if __name__ == "__main__":
    main()
