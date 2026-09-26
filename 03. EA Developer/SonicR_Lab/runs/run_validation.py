"""run_validation.py - ONE-TIME read of VALIDATION for selected configs.

Selection must already be frozen in runs/selection.json (written by
run_report.py after DESIGN+controls). This script refuses to run for any
config not in the frozen selection. Writes out/validation_summary.csv.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from src import data as dm
from src import metrics as mt
from src import runner
from src.variants.registry import CONFIGS
from src.variants.registry_2b import CONFIGS_2B

SEL_PATH = "runs/selection.json"
ALL_CFGS = {c["id"]: c for c in list(CONFIGS) + list(CONFIGS_2B)}


def main():
    if not os.path.exists(SEL_PATH):
        raise SystemExit("runs/selection.json missing - freeze the "
                         "selection first (never select after peeking).")
    sel = json.load(open(SEL_PATH))
    weeks = (dm.VALIDATION[1] - dm.VALIDATION[0]) / (7 * 86400)
    rows = []
    os.makedirs("out", exist_ok=True)
    for item in sel["selected"]:
        sym, cid = item["sym"], item["cfg"]
        cfg = dict(ALL_CFGS[cid])
        if cid == "F1_W4d":      # 2B: inject census-frozen Q
            q = json.load(open("runs/q_w4d.json"))["q_w4d"]
            cfg["w4d_q"] = q[sym]
        ctx = runner.get_ctx(sym, 5 if cfg["family"] == "F3" else 15)
        cap = runner.xau_sl_cap(runner.get_ctx(sym, 15)) \
            if sym == "XAUUSD" else None
        ctx.reset_zones()
        orders = runner.orders_for(ctx, cfg, *dm.VALIDATION, xau_cap=cap)
        for h, e1 in (("H0", False), ("H1", True)):   # A1: both harnesses
            tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                       atr=ctx.atr, skip_suspect=e1)
            tr.to_csv(f"out/val_trades_{sym}_{cid}_{h}.csv", index=False)
            s = mt.summarize(tr, weeks)
            s.update({"sym": sym, "cfg": cid, "harness": h,
                      "signals": len(orders)})
            rows.append(s)
            print(f"[val:{h}] {sym} {cid}: n={s['n']} "
                  f"pf1={s['pf_x1']:.2f} pfr1={s['pf_r_x1']:.2f} "
                  f"exp_r={s['exp_r']:.3f}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv("out/validation_summary.csv", index=False)
    print(df.to_string())


if __name__ == "__main__":
    main()
