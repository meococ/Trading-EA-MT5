"""run_controls_2c.py - ROUND 2C controls (R3) on the basket.

Per (sym, cfg, harness): 20-seed random-entry null (hour+dir matched,
same machinery as run_controls_h). Then the POOLED basket null: for each
seed s, pool that seed's null trades across all 10 symbols ->
pooled PF_R_s. Real pooled PF_R must sit >= 95th pct of that
distribution on H1 (R3). A 2000-draw bootstrap over the 20 per-symbol
seeds refines the pooled distribution.

Writes out/controls_2c.csv + out/controls_2c_null.npz.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from run_controls import _random_order
from src import data as dm
from src import metrics as mt
from src import runner

CENSUS_CFGS = ("F0_J", "F2_NH_b", "F5_S2", "F5_S3")
SEEDS = 20
POOL_DRAWS = 2000


def _pf_r_of(tr):
    r = tr["r_x1"].dropna()
    pos = r[r > 0].sum(); neg = -r[r < 0].sum()
    return pos / neg if neg > 0 else np.nan


def _pool_ctx(ctx, tf, orders, lo, hi):
    hour = ctx.hour
    sess = ctx.in_london_j
    t_lo = int(np.searchsorted(tf["t"], lo))
    t_hi = int(np.searchsorted(tf["t"], hi))
    pool = np.nonzero(sess & (np.arange(len(tf["t"])) >= t_lo)
                      & (np.arange(len(tf["t"])) < t_hi))[0]
    by_hd = {}
    for o in orders:
        by_hd.setdefault((hour[o["t"]], o["dir"]), []).append(o)
    pool_by_hour = {h: pool[hour[pool] == h] for h in np.unique(hour[pool])}
    return by_hd, pool, pool_by_hour


def main():
    os.makedirs("out", exist_ok=True)
    rows = []
    null_r = {}     # (sym,cid,h) -> list of per-seed r_x1 arrays
    real = {}       # (sym,cid,h) -> real pf_r + trades r array
    for sym in dm.BASKET:
        ctx = runner.get_ctx(sym, 15)
        tf = ctx.tf
        for cid in CENSUS_CFGS:
            orders = order_cache.load_orders(sym, cid, dm.DESIGN)
            t0 = time.time()
            by_hd, pool, pool_by_hour = _pool_ctx(ctx, tf, orders, *dm.DESIGN)
            for h, skip in (("H0", False), ("H1", True)):
                tr = runner.sim.run_trades(ctx.m1, tf, orders, sym,
                                           atr=ctx.atr, skip_suspect=skip)
                rp = _pf_r_of(tr)
                real[(sym, cid, h)] = (rp, tr["r_x1"].dropna().to_numpy())
                seed_rs = []
                for s in range(SEEDS):
                    rng = np.random.default_rng(20_000 + s)
                    ro = []
                    for (hh, dr), grp in by_hd.items():
                        cand = pool_by_hour.get(hh)
                        if cand is None or len(cand) == 0:
                            cand = pool
                        picks = rng.choice(cand, size=len(grp), replace=True)
                        for src, tn in zip(grp, picks):
                            ro.append(_random_order(src, int(tn), tf, rng))
                    ro.sort(key=lambda o: o["t"])
                    ntr = runner.sim.run_trades(ctx.m1, tf, ro, sym,
                                                atr=ctx.atr,
                                                skip_suspect=skip)
                    seed_rs.append(ntr["r_x1"].dropna().to_numpy())
                null_r[(sym, cid, h)] = seed_rs
                cell_null = np.array([_pf_r_of(pd.DataFrame({"r_x1": a}))
                                      if len(a) else np.nan
                                      for a in seed_rs])
                pct = float((cell_null < rp).mean() * 100) \
                    if np.isfinite(rp) else np.nan
                rows.append({"sym": sym, "cfg": cid, "harness": h,
                             "n_trades": len(tr), "real_pf_r": rp,
                             "cell_pct": pct,
                             "null_med": float(np.nanmedian(cell_null))})
            print(f"[ctrl2c] {sym} {cid}: done ({time.time()-t0:.0f}s)",
                  flush=True)
            pd.DataFrame(rows).to_csv("out/controls_2c.csv", index=False)
    # ---- pooled basket PF_R vs pooled null ------------------------------
    rng = np.random.default_rng(7)
    pool_rows = []
    for cid in CENSUS_CFGS:
        for h in ("H0", "H1"):
            rp_all = []
            for sym in dm.BASKET:
                rp_all.append(real[(sym, cid, h)][1])
            rpool = np.concatenate([a for a in rp_all if len(a)])
            pos = rpool[rpool > 0].sum(); neg = -rpool[rpool < 0].sum()
            real_pooled = pos / neg if neg > 0 else np.nan
            # null draw: pick one seed per symbol, pool R
            draws = []
            for _ in range(POOL_DRAWS):
                parts = []
                for sym in dm.BASKET:
                    rs = null_r[(sym, cid, h)]
                    parts.append(rs[rng.integers(0, len(rs))])
                a = np.concatenate([p for p in parts if len(p)])
                p_ = a[a > 0].sum(); n_ = -a[a < 0].sum()
                draws.append(p_ / n_ if n_ > 0 else np.nan)
            draws = np.asarray(draws)
            pct = float((draws < real_pooled).mean() * 100) \
                if np.isfinite(real_pooled) else np.nan
            pool_rows.append({"cfg": cid, "harness": h,
                              "pooled_pf_r": real_pooled,
                              "pooled_pct": pct,
                              "null_med": float(np.nanmedian(draws)),
                              "null_p95": float(np.nanpercentile(draws, 95))})
            print(f"[ctrl2c-pool] {cid} {h}: pooled_pf_r={real_pooled:.3f} "
                  f"pct={pct:.0f} null_p95={np.nanpercentile(draws,95):.3f}",
                  flush=True)
    pd.DataFrame(pool_rows).to_csv("out/controls_2c_pooled.csv",
                                   index=False)
    np.savez_compressed("out/controls_2c_null.npz",
                        **{f"{s}_{c}_{h}": np.array(
                            [len(a) for a in v]) for (s, c, h), v in
                            null_r.items()})


if __name__ == "__main__":
    main()
