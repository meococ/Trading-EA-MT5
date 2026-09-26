"""Tick-plane lead-lag probe: leader impulse -> follower drift.

Causality: leader return measured on [t-W, t]; follower entry uses the first
tick with ms > t; exit uses the first tick with ms > t+H. No same-ms leakage.
Dedup: after an event at t, no new trigger before t+H (cooldown).
Cost: follower round-trip pays measured half-spread at entry AND at exit tick
(hi-lo of those exact records) — real spread, no median-imputation needed.
"""
import os
import sys
from datetime import date

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_plane as tp

PIP = {"AUDUSD": 1e-4, "XAUUSD": 0.1, "BTCUSD": 1.0, "EURUSD": 1e-4,
       "USDJPY": 1e-2, "GBPUSD": 1e-4, "NZDUSD": 1e-4, "USDCAD": 1e-4,
       "USDCHF": 1e-4}


def first_tick_at_or_after(ms_arr, t):
    i = np.searchsorted(ms_arr, t, side="right")
    return i if i < len(ms_arr) else -1


def probe(leader, follower, d0, d1, w_sec=60, h_sec=300, thresh_pips=20.0,
          cooldown_mult=1):
    """Returns dict of event stats. w_sec=impulse window, h_sec=horizon."""
    L = tp.load_range(leader, d0, d1)
    F = tp.load_range(follower, d0, d1)
    if len(L) == 0 or len(F) == 0:
        return None
    lm, lms = tp.mid(L), L["ms"]
    fms = F["ms"]
    flo, fhi = np.minimum(F["ask"], F["bid"]), np.maximum(F["ask"], F["bid"])
    fmid = (flo + fhi) * 0.5
    lpip, fpip = PIP[leader], PIP[follower]

    W, H = w_sec * 1000, h_sec * 1000
    cd = H * cooldown_mult
    evs = []
    next_ok = 0
    # Leader impulse sampled at each leader tick (cheap scan via searchsorted)
    li = 0
    n = len(lms)
    while li < n:
        t = lms[li]
        if t < next_ok:
            li += 1
            continue
        j = np.searchsorted(lms, t - W, side="left")
        if j >= li or lms[j] > t - W:  # need a tick at/inside window edge
            li += 1
            continue
        gap_ms = t - lms[j]
        if gap_ms > W * 3:  # stale window (session gap) — skip
            li += 1
            continue
        ret = (lm[li] - lm[j]) / lpip
        if abs(ret) >= thresh_pips:
            ei = first_tick_at_or_after(fms, t)
            xi = first_tick_at_or_after(fms, t + H)
            if ei > 0 and xi > ei:
                entry = fhi[ei] if ret > 0 else flo[ei]
                exit_ = flo[xi] if ret > 0 else fhi[xi]
                pnl = (exit_ - entry) / fpip if ret > 0 else (entry - exit_) / fpip
                evs.append((t, ret, pnl))
                next_ok = t + cd
                li = np.searchsorted(lms, next_ok, side="left")
                continue
        li += 1
    if not evs:
        return {"n": 0}
    pnl = np.array([e[2] for e in evs])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    pf = wins.sum() / abs(losses.sum()) if losses.size and losses.sum() != 0 else np.inf
    days = max((d1 - d0).days, 1)
    return {"n": len(evs), "per_week": len(evs) / days * 7,
            "mean_pips": pnl.mean(), "pf": pf,
            "wr": (pnl > 0).mean()}


if __name__ == "__main__":
    d0, d1 = date(2026, 6, 1), date(2026, 7, 24)   # XAUUSD overlap so far
    print("leader AUDUSD -> follower XAUUSD, real-spread cost, dedup=H")
    for W in (15, 60, 300):
        for H in (5, 15, 60, 300, 900):
            for th in (3.0, 6.0, 10.0):
                r = probe("AUDUSD", "XAUUSD", d0, d1, W, H, th)
                if r and r["n"] >= 10:
                    print(f"W={W:4d}s H={H:4d}s th={th:4.1f}p | n={r['n']:5d} "
                          f"/wk={r['per_week']:6.1f} mean={r['mean_pips']:+7.2f}p "
                          f"PF={r['pf']:5.2f} WR={r['wr']:.2f}")
