"""run_census_2c.py - ROUND 2C outcome-blind census on the 10-symbol basket.

Per symbol on DESIGN (NO P/L):
  - F0_J orders with essence=True -> Q = median(dir*a20) per symbol
    (same median rule as LEAD_NOTE_4), S distribution, element coverage.
  - signal counts / cadence / direction split + E2 removals for the 4
    round-2C configs: F0_J, F2_NH_b, F5_S2, F5_S3 (frozen 2B/A1 defs).
  - orders cached via order_cache for the design step.
Writes out/census_2c.csv + runs/q_w4d_2c.json.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from src import data as dm
from src import runner
from src import sim
from src.variants.registry import CONFIGS
from src.variants.registry_2b import CONFIGS_2B

CENSUS_CFGS = ("F0_J", "F2_NH_b", "F5_S2", "F5_S3")


def _stats(orders, weeks, tf_t):
    if not orders:
        return {"n": 0, "per_wk": 0.0, "long": 0, "short": 0}
    sig = np.array([tf_t[o["t"]] for o in orders])
    return {"n": len(orders), "per_wk": len(orders) / weeks,
            "long": int(sum(o["dir"] == 1 for o in orders)),
            "short": int(sum(o["dir"] == -1 for o in orders)),
            "first": int(sig.min()), "last": int(sig.max())}


def main():
    weeks = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)
    os.makedirs("out", exist_ok=True)
    q_by_sym = {}
    rows = []
    s_dist = {}
    cfg0 = next(c for c in CONFIGS if c["id"] == "F0_J")
    cfg_map = {c["id"]: c for c in list(CONFIGS) + list(CONFIGS_2B)}
    for sym in dm.BASKET:
        ctx = runner.get_ctx(sym, 15)
        cap = runner.sl_cap(ctx, sym)
        tf_t = ctx.tf["t"]
        # pass 1: F0_J essence orders -> element flags + Q (frozen rule)
        ctx.reset_zones()
        e = dict(cfg0); e["essence"] = True
        t0 = time.time()
        orders0 = runner.orders_for(ctx, e, *dm.DESIGN, xau_cap=cap)
        a20s = np.array([o["dir"] * o["meta"]["a20"] for o in orders0
                         if np.isfinite(o["meta"]["a20"])])
        q = float(np.median(a20s))
        q_by_sym[sym] = q
        svals = np.array([o["meta"]["S"] for o in orders0])
        s_dist[sym] = {int(k): int((svals == k).sum()) for k in range(5)}
        el_cov = {k: float(np.mean([o["meta"][k] for o in orders0]))
                  for k in ("w2any", "w4c", "pv2a", "pv2b")}
        print(f"[2C-census] {sym} F0_J essence: n={len(orders0)} "
              f"Q(a20)={q:.4f} S-dist={s_dist[sym]} el_cov={el_cov} "
              f"({time.time()-t0:.0f}s)", flush=True)
        # pass 2: the 4 census configs; F0_J reuses the essence orders
        for cid in CENSUS_CFGS:
            cfg = cfg_map[cid]
            c2 = dict(cfg); c2["w4d_q"] = q
            t0 = time.time()
            if cid == "F0_J":
                orders = orders0            # identical signals, meta richer
            else:
                ctx.reset_zones()
                orders = runner.orders_for(ctx, c2, *dm.DESIGN, xau_cap=cap)
            order_cache.save_orders(sym, cid, dm.DESIGN, orders)
            s = _stats(orders, weeks, tf_t)
            s["e2_removed"] = sim.e2_rejects(orders, ctx.atr, sym)
            s.update({"sym": sym, "cfg": cid, "w4d_q": q})
            rows.append(s)
            print(f"[2C-census] {sym} {cid}: n={s['n']} "
                  f"per_wk={s['per_wk']:.2f} e2={s['e2_removed']} "
                  f"L/S={s['long']}/{s['short']} ({time.time()-t0:.0f}s)",
                  flush=True)
            pd.DataFrame(rows).to_csv("out/census_2c.csv", index=False)
    json.dump({"q_w4d": q_by_sym, "S_dist_F0J": s_dist},
              open("runs/q_w4d_2c.json", "w"), indent=2)
    print("q_w4d:", q_by_sym)


if __name__ == "__main__":
    main()
