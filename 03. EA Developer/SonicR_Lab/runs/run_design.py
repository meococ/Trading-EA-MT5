"""run_design.py - DESIGN-window sims for all configs/symbols (D1).

Writes out/trades_<sym>_<cfg>.csv and out/design_summary.csv.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from src import data as dm
from src import metrics as mt
from src import runner
from src.variants.registry import CONFIGS


def main():
    e1 = os.environ.get("SONIC_E1") == "1"     # H1 harness (addendum A1)
    tag = "_e1" if e1 else ""
    weeks = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)
    os.makedirs("out", exist_ok=True)
    rows = []
    for sym in dm.SYMBOLS:
        t0 = time.time()
        ctx15 = runner.get_ctx(sym, 15)
        ctx5 = runner.get_ctx(sym, 5)
        cap = runner.xau_sl_cap(ctx15) if sym == "XAUUSD" else None
        for cfg in CONFIGS:
            ctx = ctx5 if cfg["family"] == "F3" else ctx15
            orders = order_cache.load_orders(sym, cfg["id"], dm.DESIGN)
            if orders is None:
                ctx.reset_zones()
                orders = runner.orders_for(ctx, cfg, *dm.DESIGN,
                                           xau_cap=cap)
            tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                       atr=ctx.atr, skip_suspect=e1)
            tr.to_csv(f"out/trades_{sym}_{cfg['id']}{tag}.csv",
                      index=False)
            s = mt.summarize(tr, weeks)
            s.update({"sym": sym, "cfg": cfg["id"], "harness": "H1" if e1
                      else "H0", "family": cfg["family"],
                      "signals": len(orders),
                      "rejected": tr.attrs.get("rejected", 0)})
            # secondary column: daily flat at 23:50 server (NOT selection)
            tr_f = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                         atr=ctx.atr, daily_flat_mod=1430,
                                         skip_suspect=e1)
            s["pf_r_x1_flat2350"] = mt.pf_r(tr_f, "r_x1")
            s["pf_x1_flat2350"] = mt.pf(tr_f, "pnl_px_x1")
            rows.append(s)
            print(f"[design{tag}] {sym} {cfg['id']}: n={s['n']} "
                  f"pf1={s['pf_x1']:.2f} pfr1={s['pf_r_x1']:.2f} "
                  f"pfr15={s['pf_r_x15']:.2f} "
                  f"rej={tr.attrs.get('rejected', 0)} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(f"out/design_summary{tag}.csv",
                                  index=False)
    df = pd.DataFrame(rows)
    df.to_csv(f"out/design_summary{tag}.csv", index=False)
    print(df.to_string())


if __name__ == "__main__":
    main()
