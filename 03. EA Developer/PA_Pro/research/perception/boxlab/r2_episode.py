"""r2_episode.py -- R2/A2 offline falsification: episode state machine.

Pre-stated rule (before measurement, per 3.6):
  state LEG  while ER(20) >= 0.5   (Kaufman efficiency ratio:
           |c[i]-c[i-20]| / sum|c[k]-c[k-1]| over the window)
  state CONG opens at the first bar after 5 consecutive sub-0.5 bars;
           edges = running wick extremes (max h, min l) since open;
           edges readjust in place as new extremes print.
  CONG ends when a close prints >= 2 pips beyond an edge -> LEG.

  v2 correction (v1 bug: updating the edge with the current bar before
  the break test made breaks unreachable; ep0=0 everywhere):
  edges absorb wick pokes only up to absorb_tol = 4 pips beyond the
  CURRENT edge (the extreme ratchets to the poke); a close beyond
  edge+4p, or a wick beyond edge+4p, ends the episode -> LEG.

Test per golden at tau: does a CONG episode contain tau, and are BOTH
golden edges within tol (eval_v2.tol_px) of the episode's running
extremes at tau?  Report coverage on all 119 and on the 62
no_coverage subset (goldens with no engine proposal match -- from
r1_table buckets).

Read-only on bars + golden jsonl; never runs the engine.
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
L = 20
ER_TH = 0.5
FAIL_N = 5
BREAK_TOL = 2.0      # pips (in the 1e4-scaled price units used here)
ABSORB_TOL = 4.0     # wick pokes beyond the edge get absorbed <= this


def episodes(m, o, h, l, c):
    """Yield (i0_open, i1_close_or_end, top, bottom) live per bar."""
    n = len(c)
    er = np.zeros(n)
    for i in range(L, n):
        num = abs(c[i] - c[i - L])
        den = np.abs(np.diff(c[i - L:i + 1])).sum()
        er[i] = num / den if den > 0 else 0
    state = "LEG"
    fail = 0
    ep0 = 0
    top = bottom = None
    live = {}   # bar -> (top,bottom,ep0) for CONG bars
    done = []   # completed episodes (top,bottom,ep0,ep1)
    for i in range(n):
        if state == "LEG":
            if er[i] < ER_TH:
                fail += 1
            else:
                fail = 0
            if fail >= FAIL_N:
                state = "CONG"
                ep0 = i - FAIL_N + 1
                top = float(h[ep0:i + 1].max())
                bottom = float(l[ep0:i + 1].min())
        else:
            # break test vs the edges BEFORE this bar's extremes
            if h[i] > top + ABSORB_TOL or l[i] < bottom - ABSORB_TOL \
                    or c[i] > top + BREAK_TOL \
                    or c[i] < bottom - BREAK_TOL:
                # the breaking bar's extreme belongs to the episode
                # (author: absorption box includes the spike extreme)
                top = max(top, float(h[i]))
                bottom = min(bottom, float(l[i]))
                done.append((top, bottom, ep0, i))
                state = "LEG"
                fail = 0
                top = bottom = None
                continue
            top = max(top, float(h[i]))
            bottom = min(bottom, float(l[i]))
            live[i] = (top, bottom, ep0)
    return live, done


def main():
    n_cov = n_all = 0
    rows = []
    # load bucket table to mark no_coverage goldens
    import csv
    buck = {}
    tf = os.path.join(HERE, "c1_runs", "r1_table.csv")
    for r in csv.DictReader(open(tf, encoding="utf8")):
        buck[(r["panel"], int(r["gi"]))] = r["bucket"]
    for rec in C.load_tune():
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        live, done = episodes(m, o, h, l, c)
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
            # oracle: best episode (live at tau or done) whose span
            # overlaps the golden's build window ending near tau
            bs_min = g.get("build_start") or g.get("t0") or w0
            bi0 = int(np.searchsorted(m, bs_min))
            cand_eps = []
            if ti in live:
                t_, b_, s_ = live[ti]
                cand_eps.append((t_, b_, s_, ti, "live"))
            for (t_, b_, s_, e_) in done:
                # episode must overlap the golden's buildup era:
                # ends no earlier than 30 bars before build_start
                if e_ <= ti + 5 and e_ >= bi0 - 30:
                    cand_eps.append((t_, b_, s_, e_, "done"))
            hit = False
            ep = ""
            best_d = 1e9
            for (t_, b_, s_, e_, tag) in cand_eps:
                d = max(abs(t_ - ghi), abs(b_ - glo))
                if d < best_d:
                    best_d = d
                    ep = "%s[%.1f,%.1f]@%d-%d d=%.1f" \
                        % (tag, b_, t_, s_, e_, d)
            hit = best_d <= tol
            bk = buck.get((rec["id"], gi), "?")
            if hit:
                n_cov += 1
            rows.append((rec["id"], gi, tau, bk, hit, ep,
                         "%.1f-%.1f" % (glo, ghi)))
    noc = [r for r in rows if r[3] == "no_coverage"]
    noc_hit = sum(1 for r in noc if r[4])
    print("episode-live coverage of golden edges at tau:")
    print("  all 119 : %d/%d" % (n_cov, n_all))
    print("  no_cov62: %d/%d" % (noc_hit, len(noc)))
    print("\nno_coverage detail:")
    for r in noc:
        print("  %-6s g%d t%-5d %-14s %s" % (r[0], r[1], r[2],
                                            "COVERED" if r[4] else "-",
                                            r[5] or r[6]))


if __name__ == "__main__":
    main()
