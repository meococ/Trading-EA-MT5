"""run_parity.py - J (object 20260816) known-answer parity test.

Runs F0_J on the J-PARITY window (2000-01-03 -> HOLDOUT_START, EURUSD).
Writes PARITY_J.md. Heavy: goes through heavy_run.py.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import runner
from src.variants.registry import CONFIGS


def pf(tr: pd.DataFrame, col: str = "pnl_px_x1") -> float:
    if len(tr) == 0:
        return float("nan")
    g = tr.loc[tr[col] > 0, col].sum()
    l = -tr.loc[tr[col] < 0, col].sum()
    return float(g / l) if l > 0 else float("inf")


def main():
    t0 = time.time()
    print("[parity] building EURUSD ctx with pre-2010 hcc ...", flush=True)
    ctx = runner.get_ctx("EURUSD", 15, pre2010=True)
    print(f"[parity] ctx: {len(ctx.tf['t'])} M15 bars, "
          f"{len(ctx.m1['t'])} M1 bars ({time.time()-t0:.0f}s)", flush=True)
    cfg = next(c for c in CONFIGS if c["id"] == "F0_J")
    ctx.reset_zones()
    orders = runner.orders_for(ctx, cfg, dm.J_PARITY[0], dm.J_PARITY[1])
    tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, "EURUSD")
    n = len(tr)
    p = pf(tr)
    # documented alternative interpretation: W2 gate ON (same F0 slot)
    cfg2 = dict(cfg); cfg2["w2"] = "whq"; cfg2["id"] = "F0_J_w2gate"
    ctx.reset_zones()
    orders2 = runner.orders_for(ctx, cfg2, dm.J_PARITY[0], dm.J_PARITY[1])
    tr2 = runner.sim.run_trades(ctx.m1, ctx.tf, orders2, "EURUSD")
    n2 = len(tr2)
    p2 = pf(tr2)
    tr2.to_csv("out/parity_J_w2gate_trades.csv", index=False)
    print(f"[parity] w2gate N={n2} PF_x1={p2:.3f}", flush=True)
    os.makedirs("out", exist_ok=True)
    tr.to_csv("out/parity_J_trades.csv", index=False)
    n_exp = 307 * (dm.J_PARITY[1] - dm.J_PARITY[0]) / \
        (1789775940 - dm.J_PARITY[0])      # vs assumed J end 2026-08-14
    n_ok = abs(n - n_exp) <= 0.20 * n_exp
    pf_ok = abs(p - 0.94) <= 0.15
    n2_ok = abs(n2 - n_exp) <= 0.20 * n_exp
    pf2_ok = abs(p2 - 0.94) <= 0.15
    print(f"[parity] N={n} (exp~{n_exp:.0f}) PF_x1={p:.3f} "
          f"N_ok={n_ok} PF_ok={pf_ok} ({time.time()-t0:.0f}s)", flush=True)
    with open("PARITY_J.md", "w") as f:
        f.write(f"""# PARITY_J - object J known-answer test

Reference run: 20260816_205426, EURUSD M15 London, N=307, PF=0.94 on
~2000-01-03..2026-08-14 (documented assumption; run artifacts deleted).

This harness: F0_J on J-PARITY window 2000-01-03..2023-05-17 (ends at the
HOLDOUT seal - holdout never loaded even for the control).

## Result

Interpretation A - F0_J as coded (W2 telemetry, no gate):
- fills N = {n}   (window-scaled expectation ~{n_exp:.0f}; tolerance
  |N-N_exp| <= 20% -> {"PASS" if n_ok else "FAIL"})
- PF after cost x1 = {p:.3f}   (tolerance |PF-0.94| <= 0.15 ->
  {"PASS" if pf_ok else "FAIL"})
- signals placed = {len(orders)}; fill rate = {n/max(len(orders),1):.1%}

Interpretation B - same config slot, W2 WHQ-proximity gate ON:
- fills N = {n2}   -> {"PASS" if n2_ok else "FAIL"} on N
- PF after cost x1 = {p2:.3f} -> {"PASS" if pf2_ok else "FAIL"} on PF
- signals placed = {len(orders2)}

- exits A: {tr['reason'].value_counts().to_dict() if n else {}}
- suspect fills A = {int(tr['suspect_fill'].sum()) if n else 0},
  suspect exits A = {int(tr['suspect_exit'].sum()) if n else 0}
- runtime {time.time()-t0:.0f}s

## Interpretation notes

- J config implements the 16/08 spec as coded: S/R proximity telemetry
  (no gate - sr.blocked never gates in the EA source), trend side +
  dragon slope + wave + leg-3 close beyond band + bullish/bearish candle,
  pending at signal extreme +/-3 pips, ttl 4 bars, SL leg-0 extreme
  -/+0.1*ATR14 cap 120 pips, TP first WHQ half-step >=15 pips else 1.5R,
  London 08-16, weekly cap 5.
""")
    print("[parity] PARITY_J.md written", flush=True)


if __name__ == "__main__":
    main()
