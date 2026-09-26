"""BTCUSD tick-plane probe: day-of-week drift + weekend behavior.

Crypto trades 24/7 on Dukascopy — weekend data exists, unlike FX.
Measure per-DOW forward drift at fixed entry hour, net of real spread.
Also weekend vs weekday vol, and Sat->Mon gap (FX has weekend gaps;
BTC does not close — test whether the 'gap' effect is FX-specific).
"""
import os
import sys
import glob
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_plane as tp

PIP = 1.0  # BTCUSD: 1 pip = $1 for reporting


def load_all(sym):
    files = sorted(glob.glob(os.path.join(
        tp.ROOT, sym, "decoded", "*", "*", "*.afdticks")))
    recs = []
    for p in files:
        d = datetime.strptime(os.path.basename(p)[:10], "%Y-%m-%d").date()
        r = tp.load_day(sym, d)
        if r is not None and len(r):
            recs.append(r)
    return np.concatenate(recs) if recs else np.empty(0, dtype=tp.REC)


def dow_drift(sym, entry_hour_utc, hold_min=60):
    """For each day: enter at entry_hour UTC, hold hold_min. Net of real spread."""
    r = load_all(sym)
    if len(r) == 0:
        return
    lo = np.minimum(r["ask"], r["bid"]); hi = np.maximum(r["ask"], r["bid"])
    mid = (lo + hi) * 0.5
    ts = r["ms"]
    days = ts // 86_400_000
    res = {}
    for d in np.unique(days):
        w = np.flatnonzero(days == d)
        day_ms = d * 86_400_000
        ei = np.searchsorted(ts, day_ms + entry_hour_utc * 3_600_000)
        xi = np.searchsorted(ts, day_ms + (entry_hour_utc * 3_600_000
                                           + hold_min * 60_000))
        if ei >= len(ts) or xi >= len(ts) or xi <= ei:
            continue
        dow = datetime.fromtimestamp(day_ms / 1000, tz=timezone.utc).weekday()
        long_pnl = (lo[xi] - hi[ei]) / PIP
        res.setdefault(dow, []).append(long_pnl)
    print(f"{sym} entry={entry_hour_utc:02d}h UTC hold={hold_min}m (net of spread)")
    for d in range(7):
        v = np.array(res.get(d, []))
        if len(v):
            wins, losses = v[v > 0], v[v <= 0]
            pf = wins.sum() / abs(losses.sum()) if losses.sum() else np.inf
            print(f"  dow={d} n={len(v):3d} mean={v.mean():+9.1f}$ "
                  f"PF={pf:5.2f} WR={(v>0).mean():.2f}")


if __name__ == "__main__":
    for h in (0, 8, 12, 16, 20):
        dow_drift("BTCUSD", h, 60)
        dow_drift("BTCUSD", h, 240)
