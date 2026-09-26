"""run_essence.py - the pre-registered 2B essence test (LEAD_NOTE_4).

On F0_J DESIGN trades (J exits, all signals, NO gates): confluence
score S = w2any + w3 + w4c + pv2a per trade. Report per S bucket:
  n, expectancy R (r_x1 mean), PF x1, PF x1.5, 90% bootstrap CI of
  expectancy (1000 samples); buckets <30 trades merge upward.
One-sided Spearman rho(S, r_x1) > 0, p < 0.05, per symbol + pooled.
Same split for each single element (with vs without).
Writes out/essence_2b.csv + prints the verdict table.
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
from src.variants.registry import CONFIGS

ELEMENTS = ("w2any", "w3", "w4c", "pv2a")


def _spearman_one_sided(x: np.ndarray, y: np.ndarray):
    """Spearman rho + one-sided p via normal approx (z=rho*sqrt(n-1))."""
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    rx = (rx - rx.mean()) / rx.std()
    ry = (ry - ry.mean()) / ry.std()
    rho = float((rx * ry).mean())
    z = rho * math.sqrt(n - 1)
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return rho, p


def _bucket_stats(tr: pd.DataFrame, key: str, min_n: int = 30):
    """Expectancy/PF per bucket of `key`; buckets <min_n merge upward."""
    out = []
    ks = sorted(tr[key].unique())
    acc = tr.iloc[0:0]
    for k in ks:
        acc = pd.concat([acc, tr[tr[key] == k]])
        if len(acc) < min_n and k != ks[-1]:
            continue
        r = acc["r_x1"].to_numpy()
        rng = np.random.default_rng(11)
        boots = np.array([r[rng.integers(0, len(r), len(r))].mean()
                          for _ in range(1000)])
        out.append({"bucket": f"{key}<={int(k)}" if len(acc) != len(tr[tr[key] == k])
                    else f"{key}={int(k)}",
                    "n": len(acc), "exp_r": float(r.mean()),
                    "pf_x1": mt.pf(acc, "pnl_px_x1"),
                    "pf_x15": mt.pf(acc, "pnl_px_x15"),
                    "ci_lo": float(np.percentile(boots, 5)),
                    "ci_hi": float(np.percentile(boots, 95))})
        acc = tr.iloc[0:0]
    return out


def essence_for(sym: str, ctx, cap, e1: bool = False):
    cfg0 = dict(next(c for c in CONFIGS if c["id"] == "F0_J"))
    cfg0["essence"] = True
    ctx.reset_zones()
    orders = runner.orders_for(ctx, cfg0, *dm.DESIGN, xau_cap=cap)
    key = {(ctx.tf["t"][o["t"]], o["dir"]): o["meta"] for o in orders}
    tr = runner.sim.run_trades(ctx.m1, ctx.tf, orders, sym, atr=ctx.atr,
                               skip_suspect=e1)
    for k in ("S", "w2any", "w3", "w4c", "pv2a", "pv2b"):
        tr[k] = [key[(s, d)][k]
                 for s, d in zip(tr["sig_ctm"], tr["dir"])]
    return tr, len(orders)


def main():
    e1 = os.environ.get("SONIC_E1") == "1"     # H1 harness (addendum A1)
    tag = "_e1" if e1 else ""
    rows = []
    all_tr = []
    for sym in dm.SYMBOLS:
        t0 = time.time()
        ctx = runner.get_ctx(sym, 15)
        cap = runner.xau_sl_cap(ctx) if sym == "XAUUSD" else None
        tr, n_sig = essence_for(sym, ctx, cap, e1=e1)
        tr["sym"] = sym
        all_tr.append(tr)
        # S buckets
        for b in _bucket_stats(tr, "S"):
            b.update({"sym": sym, "kind": "S"})
            rows.append(b)
        # single-element splits
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
        print(f"[essence{tag}] {sym}: sig={n_sig} trades={len(tr)} "
              f"spearman rho={rho:.3f} p={p:.4f} ({time.time()-t0:.0f}s)",
              flush=True)
        tr.to_csv(f"out/essence_trades_{sym}{tag}.csv", index=False)
    pooled = pd.concat(all_tr)
    rho, p = _spearman_one_sided(pooled["S"].to_numpy(),
                                 pooled["r_x1"].to_numpy())
    rows.append({"sym": "POOLED", "kind": "spearman", "bucket": "S~r",
                 "n": len(pooled), "exp_r": rho, "pf_x1": p,
                 "pf_x15": np.nan, "ci_lo": np.nan, "ci_hi": np.nan})
    print(f"[essence] POOLED: spearman rho={rho:.3f} p={p:.4f}")
    df = pd.DataFrame(rows)
    df.to_csv(f"out/essence_2b{tag}.csv", index=False)
    print(df.to_string())


if __name__ == "__main__":
    main()
