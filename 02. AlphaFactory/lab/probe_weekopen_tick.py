"""Week-open tick probe: Sunday-open drift vs real spread, per entry offset.

For each Sunday file: measure mid-drift from first tick to +H, and the
achievable entry cost at offsets E in {1,5,10,20,30,60}min. Net expectancy
= drift(entry->entry+H) - round-trip spread at those ticks.
Answers: does week-open drift survive real cost, and at which entry offset?
"""
import os
import sys
import glob
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tick_plane as tp

PIP = {"AUDUSD": 1e-4, "XAUUSD": 0.1, "EURUSD": 1e-4, "USDJPY": 1e-2,
       "GBPUSD": 1e-4, "NZDUSD": 1e-4, "USDCAD": 1e-4, "USDCHF": 1e-4}


def sunday_files(sym):
    out = []
    for p in glob.glob(os.path.join(tp.ROOT, sym, "decoded", "*", "*",
                                    "*.afdticks")):
        d = datetime.strptime(os.path.basename(p)[:10], "%Y-%m-%d").date()
        if d.weekday() == 6:
            out.append((d, p))
    return sorted(out)


def analyze(sym, d):
    r = tp.load_day(sym, d)
    if r is None or len(r) < 50:
        return None
    pip = PIP.get(sym, 1e-4)
    lo = np.minimum(r["ask"], r["bid"])
    hi = np.maximum(r["ask"], r["bid"])
    mid = (lo + hi) * 0.5
    t0 = r["ms"][0]
    rows = []
    for e_min in (1, 5, 10, 20, 30, 60):
        for h_min in (15, 60, 120):
            ei = np.searchsorted(r["ms"], t0 + e_min * 60000, side="left")
            xi = np.searchsorted(r["ms"], t0 + (e_min + h_min) * 60000,
                                 side="left")
            if ei >= len(r) - 1 or xi >= len(r) or xi <= ei:
                continue
            ent_long, ext_long = hi[ei], lo[xi]      # long pays ask, exits bid
            pnl_long = (ext_long - ent_long) / pip
            ent_short, ext_short = lo[ei], hi[xi]
            pnl_short = (ent_short - ext_short) / pip
            sp_e = (hi[ei] - lo[ei]) / pip
            rows.append((e_min, h_min, pnl_long, pnl_short, sp_e))
    return rows


if __name__ == "__main__":
    for sym in ("AUDUSD", "XAUUSD"):
        fs = sunday_files(sym)
        print(f"== {sym}: {len(fs)} Sundays ==")
        agg = {}
        for d, _ in fs:
            rows = analyze(sym, d)
            if not rows:
                continue
            for e, h, pl, ps, spe in rows:
                agg.setdefault((e, h), []).append((pl, ps))
        for (e, h), v in sorted(agg.items()):
            pl = np.array([x[0] for x in v]); ps = np.array([x[1] for x in v])
            print(f"  E=+{e:3d}m H={h:3d}m n={len(v):2d} | long {pl.mean():+6.2f}p "
                  f"(med {np.median(pl):+6.2f}) | short {ps.mean():+6.2f}p "
                  f"(med {np.median(ps):+6.2f})")
