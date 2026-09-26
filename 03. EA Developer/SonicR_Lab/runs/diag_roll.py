"""diag_roll.py - E1 diagnostic (Lead step 2, before applying E1).

Median M1 range in units of M15 ATR14, suspect vs clean bars, by server
hour, both symbols, DESIGN window. Decides whether E1 applies:
if suspect bars inside the roll window (EUR 00:00-00:15, XAU 01:00-01:16
server) are NOT abnormal (median range ratio suspect/clean < 2) -> E1 is
skipped, only E1b stays. Writes the table to stdout for DATA.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import runner


def main():
    for sym in dm.SYMBOLS:
        ctx = runner.get_ctx(sym, 15)
        m1 = ctx.m1
        atr15 = ctx.atr
        tf_t = ctx.tf["t"]
        # map each M1 bar -> its M15 bar index, then M15 ATR14
        m15_idx = np.searchsorted(tf_t, m1["t"], side="right") - 1
        ok = m15_idx >= 0
        a = atr15[np.clip(m15_idx, 0, len(atr15) - 1)]
        rng = (m1["h"] - m1["l"])
        ratio = np.where(ok & np.isfinite(a) & (a > 0), rng / a, np.nan)
        hour = (m1["t"] % 86400) // 3600
        sus = m1["suspect"].astype(bool)
        des = (m1["t"] >= dm.DESIGN[0]) & (m1["t"] < dm.DESIGN[1])
        print(f"== {sym} DESIGN: median M1 range / M15 ATR14 by server hour")
        print("hour | n_clean med_clean | n_sus med_sus | ratio")
        for h in range(24):
            mc = des & ~sus & (hour == h)
            ms = des & sus & (hour == h)
            if ms.sum() == 0:
                continue
            rc = np.nanmedian(ratio[mc]); rs = np.nanmedian(ratio[ms])
            print(f" {h:2d}  | {int(mc.sum()):7d} {rc:8.3f} | "
                  f"{int(ms.sum()):6d} {rs:8.3f} | {rs / rc:5.2f}")
        # roll-window aggregate
        win = {"EURUSD": (hour >= 23) | (hour == 0),
               "XAUUSD": (hour == 0) | (hour == 1)}[sym]
        mc = des & ~sus & win
        ms = des & sus & win
        rc = np.nanmedian(ratio[mc]); rs = np.nanmedian(ratio[ms])
        print(f"roll-window aggregate: clean med={rc:.3f} (n={mc.sum()}) "
              f"sus med={rs:.3f} (n={ms.sum()}) ratio={rs / rc:.2f}")
        print(f"decision: E1 {'APPLIES' if rs / rc >= 2 else 'SKIPPED'}"
              f" (threshold 2.0)")


if __name__ == "__main__":
    main()
