"""free_2f.py - 2F STEP C.2: free-running AM-only on C (report only).

Uses orders_once (cached per (sym,window) under the versioned key
'F2_NH_b_dstfix'); orders generated once, reused for both harnesses.
orders_for resets the zone engine internally (A2F fix).
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from validation_2f import orders_once, pf
from src import data as dm
from src import runner
from src import sim as sm

C_SET = ["NZDUSD", "USDCAD", "EURJPY", "AUDJPY", "EURGBP"]


def main():
    t00 = time.time()
    rows = []
    for e1 in (True, False):
        h = "H1" if e1 else "H0"
        for sym in C_SET:
            ctx = runner.get_ctx(sym, 15)
            cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
            orders = orders_once(sym, dm.DESIGN, cap)
            hour, _, _ = dm.london_parts(
                np.array([int(ctx.tf["t"][o["t"]]) for o in orders]))
            keep = [o for o, hh in zip(orders, hour) if 7 <= hh < 12]
            tr = sm.run_trades(ctx.m1, ctx.tf, keep, sym, atr=ctx.atr,
                               skip_suspect=e1)
            rows.append({"harness": h, "sym": sym, "n": len(tr),
                         "pf_r_x1": pf(tr["r_x1"]),
                         "pf_r_x15": pf(tr["r_x15"]),
                         "exp": float(tr["r_x1"].mean())})
            print(f"[free {h}] {sym} n={len(tr)} "
                  f"pf={pf(tr['r_x1']):.3f}", flush=True)
    pd.DataFrame(rows).to_csv("out/confirm_2f_free.csv", index=False)
    print(f"[free_2f] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
