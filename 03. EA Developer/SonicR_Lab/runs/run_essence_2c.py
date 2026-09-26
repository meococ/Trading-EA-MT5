"""run_essence_2c.py - ROUND 2C essence test (R1) on the basket.

Per symbol: Spearman(S, r_x1) on F0_J DESIGN trades (cached essence
orders from census_2c), one-sided p; combined across the basket by
Stouffer's z weighted by sqrt(n). Runs on the harness set by SONIC_E1.
Writes out/essence_2c{,_e1}.csv.
"""
import math
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
from run_essence import _spearman_one_sided, _bucket_stats, ELEMENTS


def main():
    e1 = os.environ.get("SONIC_E1") == "1"
    tag = "_e1" if e1 else ""
    rows = []
    zsum = 0.0
    wsum = 0.0
    n_rho_pos = 0
    n_big = 0
    for sym in dm.BASKET:
        t0 = time.time()
        ctx = runner.get_ctx(sym, 15)
        orders = order_cache.load_orders(sym, "F0_J", dm.DESIGN)
        key = {(ctx.tf["t"][o["t"]], o["dir"]): o["meta"] for o in orders}
        tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym,
                                   atr=ctx.atr, skip_suspect=e1)
        tr = tr[[(s, d) in key for s, d in
                 zip(tr["sig_ctm"], tr["dir"])]].copy()
        for k in ("S", "w2any", "w3", "w4c", "pv2a", "pv2b"):
            tr[k] = [key[(s, d)][k]
                     for s, d in zip(tr["sig_ctm"], tr["dir"])]
        tr["sym"] = sym
        tr.to_csv(f"out/essence2c_trades_{sym}{tag}.csv", index=False)
        for b in _bucket_stats(tr, "S"):
            b.update({"sym": sym, "kind": "S"})
            rows.append(b)
        for el in ELEMENTS + ("pv2b",):
            for v, grp in tr.groupby(tr[el]):
                rows.append({"sym": sym, "kind": f"{el}={int(v)}",
                             "bucket": f"{el}={int(v)}", "n": len(grp),
                             "exp_r": float(grp["r_x1"].mean()),
                             "pf_x1": mt.pf(grp, "pnl_px_x1"),
                             "pf_x15": mt.pf(grp, "pnl_px_x15"),
                             "ci_lo": np.nan, "ci_hi": np.nan})
        rho, p = _spearman_one_sided(tr["S"].to_numpy(),
                                     tr["r_x1"].to_numpy())
        rows.append({"sym": sym, "kind": "spearman", "bucket": "S~r",
                     "n": len(tr), "exp_r": rho, "pf_x1": p,
                     "pf_x15": np.nan, "ci_lo": np.nan, "ci_hi": np.nan})
        if np.isfinite(rho):
            z = rho * math.sqrt(max(len(tr) - 1, 1))
            zsum += z * math.sqrt(len(tr))
            wsum += len(tr)
            if len(tr) >= 100:
                n_big += 1
                if rho > 0:
                    n_rho_pos += 1
        print(f"[essence2c{tag}] {sym}: trades={len(tr)} rho={rho:.3f} "
              f"p={p:.4f} ({time.time()-t0:.0f}s)", flush=True)
    zc = zsum / math.sqrt(wsum) if wsum else float("nan")
    pc = 0.5 * math.erfc(zc / math.sqrt(2)) if np.isfinite(zc) \
        else float("nan")
    rows.append({"sym": "BASKET", "kind": "stouffer", "bucket": "S~r",
                 "n": int(wsum), "exp_r": zc, "pf_x1": pc,
                 "pf_x15": np.nan, "ci_lo": np.nan, "ci_hi": np.nan})
    print(f"[essence2c{tag}] BASKET Stouffer z={zc:.2f} p={pc:.2e} "
          f"rho>0 on {n_rho_pos}/{n_big} symbols with >=100 trades")
    pd.DataFrame(rows).to_csv(f"out/essence_2c{tag}.csv", index=False)


if __name__ == "__main__":
    main()
