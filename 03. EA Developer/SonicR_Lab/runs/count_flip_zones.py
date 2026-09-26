"""count_flip_zones.py - LEAD_NOTE_3 addendum item 3.

Count distinct zone formations on DESIGN whose member set mixes highs
and lows (the 2-member 1-high+1-low case sums to 0 and is labelled
'support' -1 - kept this round, counted for the round-3 design question).
Zones deduped by member frozenset; scanned at swing confirmation bars
only (a new zone can only be born when a member confirms).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src import data as dm
from src import runner


def main():
    for sym in dm.SYMBOLS:
        ctx = runner.get_ctx(sym, 15)
        ctx.reset_zones()
        eng = ctx.zones_engine
        t0 = int(np.searchsorted(ctx.tf["t"], dm.DESIGN[0]))
        t1 = int(np.searchsorted(ctx.tf["t"], dm.DESIGN[1]))
        conf_bars = sorted({cf[0] for cf in eng._by_conf
                            if t0 <= cf[0] <= t1})
        sw_dir = {int(i): int(dr) for i, dr in
                  zip(ctx.zig["idx"], ctx.zig["dir"])}
        seen = {}
        for t in conf_bars:
            for z in ctx.zones_at(t):
                seen.setdefault(frozenset(z["members"]), z)
        zones = list(seen.values())
        mixed = [z for z in zones
                 if len({sw_dir[i] for i in z["members"]}) == 2]
        print(f"{sym}: distinct zones on DESIGN = {len(zones)}, "
              f"mixed high+low = {len(mixed)}")


if __name__ == "__main__":
    main()
