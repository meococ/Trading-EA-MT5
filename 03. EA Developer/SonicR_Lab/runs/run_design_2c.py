"""run_design_2c.py - ROUND 2C DESIGN sims on the basket (post-PREREG_V3).

4 configs (F0_J, F2_NH_b, F5_S2, F5_S3) x 10 basket symbols, on the
harness selected by SONIC_E1 (H0 default, H1 with =1). Uses cached
orders from run_census_2c. Writes out/trades_2c_* + design_summary_2c*.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import order_cache
from src import data as dm
from src import metrics as mt
from src import runner

CENSUS_CFGS = ("F0_J", "F2_NH_b", "F5_S2", "F5_S3")


def main():
    e1 = os.environ.get("SONIC_E1") == "1"     # H1 harness
    tag = "_e1" if e1 else ""
    weeks = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)
    os.makedirs("out", exist_ok=True)
    rows = []
    for sym in dm.BASKET:
        ctx = runner.get_ctx(sym, 15)
        for cid in CENSUS_CFGS:
            t0 = time.time()
            orders = order_cache.load_orders(sym, cid, dm.DESIGN)
            if orders is None:
                raise SystemExit(f"missing cached orders {sym} {cid} "
                                 "- run run_census_2c.py first")
            tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                       atr=ctx.atr, skip_suspect=e1)
            tr.to_csv(f"out/trades_2c_{sym}_{cid}{tag}.csv", index=False)
            s = mt.summarize(tr, weeks)
            s.update({"sym": sym, "cfg": cid,
                      "harness": "H1" if e1 else "H0",
                      "signals": len(orders),
                      "rejected": tr.attrs.get("rejected", 0)})
            tr_f = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                         atr=ctx.atr, daily_flat_mod=1430,
                                         skip_suspect=e1)
            s["pf_r_x1_flat2350"] = mt.pf_r(tr_f, "r_x1")
            s["pf_x1_flat2350"] = mt.pf(tr_f, "pnl_px_x1")
            rows.append(s)
            print(f"[2C{tag}] {sym} {cid}: n={s['n']} "
                  f"pf1={s['pf_x1']:.2f} pfr1={s['pf_r_x1']:.2f} "
                  f"rej={tr.attrs.get('rejected', 0)} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(f"out/design_summary_2c{tag}.csv",
                                  index=False)
    df = pd.DataFrame(rows)
    print(df.to_string())


if __name__ == "__main__":
    main()
