"""Session-open tick probe: minute-level drift after major session opens.

Canonical microstructure cell M1 couldn't resolve: does price drift
systematically in the first N minutes after London (07:00 UTC) / NY
(12:00-13:30 UTC) / Asia (00:00-01:00 UTC) opens? Ticks give exact
entry prices + real spread at any offset.
"""
import os
import sys
import glob
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_plane as tp

PIP = {"AUDUSD": 1e-4, "XAUUSD": 0.1, "EURUSD": 1e-4, "USDJPY": 1e-2,
       "BTCUSD": 1.0}
OPENS = {"asia": 0, "london": 7, "ny": 12}


def session_probe(sym, open_h_utc, entry_off_min, hold_min):
    """Enter at open+offset, hold hold_min. Both directions measured."""
    files = sorted(glob.glob(os.path.join(
        tp.ROOT, sym, "decoded", "*", "*", "*.afdticks")))
    pip = PIP.get(sym, 1e-4)
    pnls = []
    for p in files:
        d = datetime.strptime(os.path.basename(p)[:10], "%Y-%m-%d").date()
        r = tp.load_day(sym, d)
        if r is None or len(r) < 100:
            continue
        lo = np.minimum(r["ask"], r["bid"]); hi = np.maximum(r["ask"], r["bid"])
        mid = (lo + hi) * 0.5
        day_ms = datetime(d.year, d.month, d.day, tzinfo=timezone.utc
                          ).timestamp() * 1000
        e_ms = day_ms + (open_h_utc * 60 + entry_off_min) * 60000
        x_ms = e_ms + hold_min * 60000
        ei = np.searchsorted(r["ms"], e_ms, side="left")
        xi = np.searchsorted(r["ms"], x_ms, side="left")
        if ei >= len(r) or xi >= len(r) or xi <= ei:
            continue
        # direction = drift from day-open to entry (follow the open move)
        oi = np.searchsorted(r["ms"], day_ms + open_h_utc * 3600000,
                             side="left")
        if oi >= len(r):
            continue
        pre = (mid[ei] - mid[oi]) / pip
        if abs(pre) < 0.5:
            continue
        side = 1 if pre > 0 else -1  # follow pre-open drift
        ent = hi[ei] if side > 0 else lo[ei]
        ext = lo[xi] if side > 0 else hi[xi]
        pnls.append((ext - ent) / pip * side)
    v = np.array(pnls)
    if len(v) < 5:
        return None
    w = v[v > 0]; l = v[v <= 0]
    pf = w.sum() / abs(l.sum()) if l.sum() else np.inf
    return {"n": len(v), "mean": v.mean(), "pf": pf, "wr": (v > 0).mean()}


if __name__ == "__main__":
    for sym in ("AUDUSD", "XAUUSD"):
        print(f"== {sym} follow-open-drift ==")
        for name, h in OPENS.items():
            for off in (0, 1, 5, 15):
                for hold in (15, 60):
                    r = session_probe(sym, h, off, hold)
                    if r:
                        print(f"  {name:6s} +{off:2d}m h={hold:3d}m "
                              f"n={r['n']:3d} mean={r['mean']:+7.2f}p "
                              f"PF={r['pf']:5.2f} WR={r['wr']:.2f}")
