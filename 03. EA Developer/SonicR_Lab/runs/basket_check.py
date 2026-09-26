"""basket_check.py - ROUND 2C step 1: outcome-blind data checks per basket
symbol (NO P/L, no signals, no outcomes).

Per symbol on the DESIGN window:
  - coverage: share of calendar weeks with >= 1 M1 bar (drop if < 90%).
  - suspect share of M1 bars.
  - roll window discovery: smallest contiguous arc of server
    minute-of-day (may wrap midnight, <= 60 min) covering >= 99% of
    suspect-bar mass.
  - exit-free roll diagnostic (A1-1 part b): per server-day, max M1
    range and max |open - prev close| inside the discovered roll window
    vs the two adjacent quiet windows of equal length -> median/P90/P99.
  - median daily range in pips (input for the per-symbol SL cap).

Writes out/basket_checks.csv and prints a table for BASKET.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm


def _mod_arr(t):
    return (t % 86400) // 60


def _roll_arc(sus_minutes, cover=0.99, max_len=60):
    """Smallest circular arc of minute-of-day containing >=cover of mass.
    Falls back to the max-mass max_len window if no arc reaches cover."""
    hist = np.bincount(sus_minutes, minlength=1440).astype(np.float64)
    if hist.sum() == 0:
        return None, 0.0
    h2 = np.concatenate([hist, hist])
    for cov in (cover, 0.95, 0.90):
        need = hist.sum() * cov
        best = None
        for start in range(1440):
            c = np.cumsum(h2[start:start + max_len])
            k = int(np.searchsorted(c, need)) + 1
            if k > max_len:
                continue
            if best is None or k < best[1] - best[0]:
                best = (start, start + k)
        if best is not None:
            break
    if best is None:                      # mass too spread: densest window
        cs = np.cumsum(np.concatenate([[0.0], h2]))
        masses = cs[max_len:1440 + max_len] - cs[:1440]
        start = int(np.argmax(masses))
        best = (start, start + max_len)
        cov = masses[start] / hist.sum()
    a = best[0] % 1440
    b = best[1] % 1440
    if b == 0:
        b = 1440
    return (a, b), float(cov)


def _in_arc(mod, a, b):
    return (mod >= a) | (mod < b) if a > b else (mod >= a) & (mod < b)


def _daily_stats(m1, win):
    """Per server-day max range & max |o - prev c| inside `win` (a,b)."""
    t, o, h, l, c = m1["t"], m1["o"], m1["h"], m1["l"], m1["c"]
    mod = _mod_arr(t)
    day = t // 86400
    inside = _in_arc(mod, *win)
    rng = h - l
    jump = np.abs(o - np.roll(c, 1)); jump[0] = 0.0
    same_day = np.diff(day, prepend=day[0]) == 0
    jump = np.where(same_day, jump, 0.0)
    idx = np.nonzero(inside)[0]
    days = np.unique(day[idx])
    mr = np.zeros(len(days)); mj = np.zeros(len(days))
    pos = np.searchsorted(day, days)
    for i, d0 in enumerate(days):
        m = inside & (day == d0)
        if m.any():
            mr[i] = rng[m].max(); mj[i] = jump[m].max()
        else:
            mr[i] = np.nan; mj[i] = np.nan
    return days, mr, mj


def _win_shift(win, k, length):
    a = (win[0] + k * length) % 1440
    b = (a + length) % 1440
    if b == 0:
        b = 1440
    return a, b


def main():
    rows = []
    for sym in dm.BASKET:
        m1 = dm.load_m1(sym, dm.DESIGN[0], dm.DESIGN[1])
        t = m1["t"]
        mod = _mod_arr(t)
        sus = m1["suspect"].astype(bool)
        # coverage: weeks with >= 1 bar
        wk = t // (7 * 86400)
        cov = len(np.unique(wk)) / (len(np.unique(
            np.arange(dm.DESIGN[0], dm.DESIGN[1]) // (7 * 86400))))
        share = float(sus.mean())
        win, win_cov = _roll_arc(mod[sus])
        # quiet windows: same length, immediately before/after
        ln = (win[1] - win[0]) % 1440 or 1440
        pre = _win_shift(win, -1, ln)
        post = _win_shift(win, 1, ln)
        d_r, mr_r, mj_r = _daily_stats(m1, win)
        d_p, mr_p, mj_p = _daily_stats(m1, pre)
        d_q, mr_q, mj_q = _daily_stats(m1, post)
        all_days = np.union1d(np.union1d(d_r, d_p), d_q)

        def _re(days, arr):
            out = np.full(len(all_days), np.nan)
            out[np.searchsorted(all_days, days)] = arr
            return out

        mr_r, mj_r = _re(d_r, mr_r), _re(d_r, mj_r)
        quiet_r = np.nanmean(np.vstack([_re(d_p, mr_p),
                                        _re(d_q, mr_q)]), axis=0)
        quiet_j = np.nanmean(np.vstack([_re(d_p, mj_p),
                                        _re(d_q, mj_q)]), axis=0)
        rr = mr_r / quiet_r; rj = mj_r / quiet_j
        # median daily range (server-day hi-lo) in pips
        day = t // 86400
        hi = pd.Series(m1["h"]).groupby(day).max().to_numpy()
        lo = pd.Series(m1["l"]).groupby(day).min().to_numpy()
        mdr = float(np.median(hi - lo) / dm.PIP[sym])
        def q(a, p):
            a = a[np.isfinite(a)]
            return float(np.percentile(a, p)) if len(a) else np.nan
        rows.append({
            "sym": sym, "coverage_wk": round(cov, 4),
            "suspect_share": round(share, 4),
            "roll_win": f"{win[0]//60:02d}:{win[0]%60:02d}-"
                        f"{win[1]//60:02d}:{win[1]%60:02d}",
            "roll_a": win[0], "roll_b": win[1],
            "roll_cover": round(win_cov, 3),
            "range_med": round(q(rr, 50), 1), "range_p90": round(q(rr, 90), 1),
            "range_p99": round(q(rr, 99), 1),
            "jump_med": round(q(rj, 50), 1), "jump_p90": round(q(rj, 90), 1),
            "jump_p99": round(q(rj, 99), 1),
            "mdr_pips": round(mdr, 1),
            "drop": cov < 0.90,
        })
        print(f"[basket] {sym}: cov={cov:.3f} sus={share:.3f} "
              f"win={rows[-1]['roll_win']} medR={rows[-1]['range_med']}x "
              f"mdr={mdr:.0f}p", flush=True)
        pd.DataFrame(rows).to_csv("out/basket_checks.csv", index=False)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))


if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    main()
