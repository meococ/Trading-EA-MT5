"""diag_roll_v2.py - CORRECTED E1 diagnostic (Lead addendum A1, 19:17Z).

The median-range test hid the artifact; the direct evidence is where
trades exit. Three measurements, DESIGN window, both symbols:

(a) exits per 1000 trade-minutes inside the roll window vs outside,
    for every round-2 and 2B config (reads out/trades_*.csv);
(b) per day: max M1 range and max |open - prev close| inside the roll
    window vs two adjacent quiet windows of equal length, reported as
    median/P90/P99 ratios;
(c) jump-and-revert: share of days where price inside the roll window
    moves > 0.5 x ATR14(M15) away from the pre-roll close and is back
    within 0.2 x ATR14 of it 30 minutes after the window.
Numbers only - they document a decision the Lead already made.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import runner

# Lead's measured windows (server minute-of-day, half-open)
ROLL_MIN = {"EURUSD": (0, 20), "XAUUSD": (60, 80)}
QUIET = {"EURUSD": [(1410, 1425), (30, 45)],   # 23:30-45 / 00:30-45
         "XAUUSD": [(30, 45), (90, 105)]}      # 00:30-45 / 01:30-45


def _in(ctm_arr, a, b):
    mod = (ctm_arr % 86400) // 60
    if a > b:
        return (mod >= a) | (mod < b)
    return (mod >= a) & (mod < b)


def exits_per_1000min():
    print("== (a) exits per 1000 trade-minutes in roll window vs outside")
    print("sym cfg n exits_in time_in_min time_out_min rate_in rate_out")
    for sym in dm.SYMBOLS:
        a, b = ROLL_MIN[sym]
        files = sorted(glob.glob(f"out/trades_{sym}_*.csv")
                       + glob.glob(f"out/trades_2b_{sym}_*.csv"))
        for f in files:
            if os.path.getsize(f) < 10:
                continue
            tr = pd.read_csv(f)
            if len(tr) == 0:
                continue
            cfg = os.path.basename(f).replace(".csv", "") \
                .replace(f"trades_{sym}_", "").replace(f"trades_2b_{sym}_", "2B_")
            ex_in = _in(tr["exit_ctm"].to_numpy(), a, b)
            dur = np.maximum(tr["exit_ctm"].to_numpy()
                             - tr["fill_ctm"].to_numpy(), 60) / 60.0
            # minutes of each trade inside the window (per-day window)
            fill = tr["fill_ctm"].to_numpy(); ex = tr["exit_ctm"].to_numpy()
            t_in = np.zeros(len(tr))
            for i, (f0, e0) in enumerate(zip(fill, ex)):
                d0 = f0 - (f0 % 86400)
                lo = d0 + a * 60; hi = d0 + b * 60
                while lo <= e0:                    # may span >1 day
                    t_in[i] += max(0, min(e0, hi) - max(f0, lo)) / 60.0
                    lo += 86400; hi += 86400
            tin, tout = t_in.sum(), (dur - t_in).sum()
            ein = ex_in.sum(); eout = len(tr) - ein
            ri = ein / tin * 1000 if tin > 0 else np.nan
            ro = eout / tout * 1000 if tout > 0 else np.nan
            print(f"{sym} {cfg:12s} {len(tr):5d} {int(ein):4d} "
                  f"{tin:10.0f} {tout:10.0f} {ri:7.2f} {ro:7.2f}")


def window_stats():
    print("\n== (b) per-day max M1 range & max |open-prev_close| "
          "roll vs adjacent quiet windows")
    for sym in dm.SYMBOLS:
        ctx = runner.get_ctx(sym, 15)
        m1 = ctx.m1
        mt, mo, mh, ml, mc = (m1[k] for k in "tohlc")
        des = (mt >= dm.DESIGN[0]) & (mt < dm.DESIGN[1])
        idx = np.nonzero(des)[0]
        rng = mh - ml
        gap = np.abs(mo[1:] - mc[:-1])
        gap = np.concatenate([[np.nan], gap])
        days = np.unique(mt[idx] // 86400)
        ra, rb = ROLL_MIN[sym]
        rw = (ra, rb)
        qws = QUIET[sym]
        stats = {k: [] for k in ("r_rng", "r_gap", "q_rng", "q_gap")}
        for d in days:
            day_ctm = d * 86400
            m = (mt >= day_ctm) & (mt < day_ctm + 86400) & des
            i = np.nonzero(m)[0]
            if len(i) < 60:
                continue
            def winmask(a_, b_):
                mm = (mt >= day_ctm + a_ * 60) & (mt < day_ctm + b_ * 60)
                return i[np.isin(i, np.nonzero(mm)[0])]
            wr = winmask(*rw)
            if len(wr) == 0:
                continue
            stats["r_rng"].append(rng[wr].max())
            stats["r_gap"].append(np.nanmax(gap[wr]))
            qr, qg = [], []
            for qw in qws:
                w = winmask(*qw)
                if len(w):
                    qr.append(rng[w].max()); qg.append(np.nanmax(gap[w]))
            if qr:
                stats["q_rng"].append(max(qr)); stats["q_gap"].append(max(qg))
            else:
                stats["q_rng"].append(np.nan); stats["q_gap"].append(np.nan)
        for key, lab in (("rng", "max range"), ("gap", "max |o-c_prev|")):
            r = np.asarray(stats[f"r_{key}"]); q = np.asarray(stats[f"q_{key}"])
            rat = r / q
            print(f"{sym} {lab}: roll/quiet ratio "
                  f"med={np.nanmedian(rat):.2f} "
                  f"p90={np.nanpercentile(rat, 90):.2f} "
                  f"p99={np.nanpercentile(rat, 99):.2f} "
                  f"| roll med={np.nanmedian(r):.5f} "
                  f"quiet med={np.nanmedian(q):.5f}")


def jump_revert():
    print("\n== (c) jump-and-revert share of days")
    for sym in dm.SYMBOLS:
        ctx = runner.get_ctx(sym, 15)
        m1 = ctx.m1; tf_t = ctx.tf["t"]; atr = ctx.atr
        mt, mo, mc = m1["t"], m1["o"], m1["c"]
        des = (mt >= dm.DESIGN[0]) & (mt < dm.DESIGN[1])
        days = np.unique(mt[des] // 86400)
        ra, rb = ROLL_MIN[sym]
        n_days = 0; n_jr = 0
        for d in days:
            day_ctm = d * 86400
            ip = int(np.searchsorted(mt, day_ctm + ra * 60)) - 1
            if ip < 0:
                continue
            pre_close = mc[ip]                 # last bar before window
            i0 = int(np.searchsorted(mt, day_ctm + ra * 60))
            i1 = int(np.searchsorted(mt, day_ctm + rb * 60))
            if i1 <= i0:
                continue
            t15 = int(np.searchsorted(tf_t, day_ctm + ra * 60)) - 1
            a14 = atr[max(t15, 0)]
            if not np.isfinite(a14) or a14 <= 0:
                continue
            n_days += 1
            away = np.abs(mc[i0:i1] - pre_close).max() > 0.5 * a14
            ipost = int(np.searchsorted(mt, day_ctm + (rb + 30) * 60))
            if ipost >= len(mt):
                continue
            back = abs(mc[ipost] - pre_close) <= 0.2 * a14
            if away and back:
                n_jr += 1
        print(f"{sym}: {n_jr}/{n_days} days jump-and-revert "
              f"({100 * n_jr / max(n_days, 1):.1f}%)")


if __name__ == "__main__":
    exits_per_1000min()
    window_stats()
    jump_revert()
