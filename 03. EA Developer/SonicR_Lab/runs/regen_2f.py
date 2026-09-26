"""regen_2f.py - 2F STEP 1b: rerun X0-HOLD with the fixed London mapping.

Regenerates F2_NH_b orders (in_london_ext moved on the DST bug weeks)
and re-sims H0/H1, DESIGN window, all 12 symbols. Writes
out/trades_2f_<sym>_X0-HOLD_dstfix(_e1).csv - never touches 2C/2D files.
Prints before/after: trades changed, PF_R x1 per symbol per harness.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import managed as mg
import order_cache
from src import data as dm
from src import runner
from src import sim as sm
from src.variants.registry import CONFIGS

SYMS = list(dm.ALL_SYMBOLS)
CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]


def pf_r(r):
    r = pd.Series(r).dropna()
    neg = -r[r < 0].sum()
    return r[r > 0].sum() / neg if neg > 0 else np.nan


def main():
    t00 = time.time()
    rows = []
    for sym in SYMS:
        ctx = runner.get_ctx(sym, 15)
        cap = None if sym == "EURUSD" else runner.sl_cap(ctx, sym)
        orders = runner.orders_for(ctx, CFG, *dm.DESIGN, cap)
        for e1 in (True, False):
            h = "H1" if e1 else "H0"
            tr = sm.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1)
            out = (f"out/trades_2f_{sym}_X0-HOLD_dstfix"
                   f"{'_e1' if e1 else ''}.csv")
            tr.to_csv(out, index=False)
            old = mg.load_x0(sym, e1)
            ok = old.merge(tr[["sig_ctm", "dir", "r_x1"]],
                           on=["sig_ctm", "dir"], how="left",
                           indicator=True, suffixes=("", "_n"))
            n_gone = int((ok["_merge"] == "left_only").sum())
            n_new = len(tr) - int((ok["_merge"] == "both").sum())
            chg = ok[ok["_merge"] == "both"]
            n_chg = int((chg["r_x1"] != chg["r_x1_n"]).sum())
            rows.append({"sym": sym, "h": h, "n_old": len(old),
                         "n_new": len(tr), "gone": n_gone, "new": n_new,
                         "r_changed": n_chg,
                         "pf_old": pf_r(old["r_x1"]),
                         "pf_new": pf_r(tr["r_x1"])})
            print(f"[dstfix {h}] {sym} old={len(old)} new={len(tr)} "
                  f"gone={n_gone} new_sig={n_new} r_chg={n_chg} "
                  f"pf {pf_r(old['r_x1']):.3f}->{pf_r(tr['r_x1']):.3f}",
                  flush=True)
    rep = pd.DataFrame(rows)
    rep.to_csv("out/dstfix_diff_2f.csv", index=False)
    worst = (rep["gone"] + rep["new"] + rep["r_changed"]) / rep["n_old"]
    print(f"[dstfix] max share changed = {worst.max()*100:.2f}%")
    if worst.max() > 0.01:
        print("[dstfix] >1% CHANGED - STOP per backup plan", flush=True)
    print(f"[dstfix] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
