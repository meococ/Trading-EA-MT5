"""run_design_2b.py - ROUND 2B DESIGN sims (after PREREG_V2 hash only).

Same metrics as run_design.py, for the 8 2B configs. Uses cached orders
from run_census_2b (frozen at census time). Writes out/trades_2b_* and
out/design_summary_2b.csv.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import order_cache
from src import data as dm
from src import metrics as mt
from src import runner
from src.variants.registry_2b import CONFIGS_2B


def main():
    e1 = os.environ.get("SONIC_E1") == "1"     # H1 harness (addendum A1)
    tag = "_e1" if e1 else ""
    weeks = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)
    os.makedirs("out", exist_ok=True)
    rows = []
    for sym in dm.SYMBOLS:
        ctx = runner.get_ctx(sym, 15)
        for cfg in CONFIGS_2B:
            t0 = time.time()
            orders = order_cache.load_orders(sym, cfg["id"], dm.DESIGN)
            if orders is None:
                raise SystemExit(f"missing cached orders {sym} {cfg['id']} "
                                 "- run run_census_2b.py + freeze "
                                 "PREREG_V2 first")
            tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                       atr=ctx.atr, skip_suspect=e1)
            tr.to_csv(f"out/trades_2b_{sym}_{cfg['id']}{tag}.csv",
                      index=False)
            s = mt.summarize(tr, weeks)
            s.update({"sym": sym, "cfg": cfg["id"], "harness": "H1" if e1
                      else "H0", "family": cfg["family"],
                      "signals": len(orders),
                      "rejected": tr.attrs.get("rejected", 0)})
            tr_f = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                         atr=ctx.atr, daily_flat_mod=1430,
                                         skip_suspect=e1)
            s["pf_r_x1_flat2350"] = mt.pf_r(tr_f, "r_x1")
            s["pf_x1_flat2350"] = mt.pf(tr_f, "pnl_px_x1")
            rows.append(s)
            print(f"[2B{tag}] {sym} {cfg['id']}: n={s['n']} "
                  f"pf1={s['pf_x1']:.2f} pfr1={s['pf_r_x1']:.2f} "
                  f"rej={tr.attrs.get('rejected', 0)} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(f"out/design_summary_2b{tag}.csv",
                                  index=False)
    df = pd.DataFrame(rows)
    print(df.to_string())


if __name__ == "__main__":
    main()
