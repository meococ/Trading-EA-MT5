"""run_census_2b.py - ROUND 2B outcome-blind census (LEAD_NOTE_4 step 1).

Computes, per symbol on DESIGN:
  - F0_J signals WITH element flags (essence=True) -> Q = median of
    dir*angle20 -> written to runs/q_w4d.json (needed by F1_W4d).
  - signal counts / cadence / direction split for the 8 2B configs.
  - confluence-score coverage on F0_J (S distribution).
NO P/L anywhere in this script. Writes out/census_2b.csv + q_w4d.json.
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
    for sym in dm.SYMBOLS:
        ctx = runner.get_ctx(sym, 15)
        cap = runner.xau_sl_cap(ctx) if sym == "XAUUSD" else None
        tf_t = ctx.tf["t"]
        # pass 1: F0_J essence orders -> element flags + Q
        ctx.reset_zones()
        e = dict(cfg0); e["essence"] = True
        t0 = time.time()
        orders0 = runner.orders_for(ctx, e, *dm.DESIGN, xau_cap=cap)
        a20s = np.array([o["dir"] * o["meta"]["a20"] for o in orders0
                         if np.isfinite(o["meta"]["a20"])])
        q = float(np.median(a20s))
        q_by_sym[sym] = q
        svals = np.array([o["meta"]["S"] for o in orders0])
        s_dist[sym] = {int(k): int((svals == k).sum())
                       for k in range(5)}
        el_cov = {k: float(np.mean([o["meta"][k] for o in orders0]))
                  for k in ("w2any", "w4c", "pv2a", "pv2b")}
        print(f"[2B-census] {sym} F0_J essence: n={len(orders0)} "
              f"Q(a20)={q:.4f} S-dist={s_dist[sym]} el_cov={el_cov} "
              f"({time.time()-t0:.0f}s)", flush=True)
        # pass 2: 2B configs
        for cfg in CONFIGS_2B:
            c2 = dict(cfg); c2["w4d_q"] = q
            ctx.reset_zones()
            t0 = time.time()
            orders = runner.orders_for(ctx, c2, *dm.DESIGN, xau_cap=cap)
            order_cache.save_orders(sym, cfg["id"], dm.DESIGN, orders)
            s = _stats(orders, weeks, tf_t)
            s["e2_removed"] = sim.e2_rejects(orders, ctx.atr, sym)
            s.update({"sym": sym, "cfg": cfg["id"]})
            rows.append(s)
            print(f"[2B-census] {sym} {cfg['id']}: n={s['n']} "
                  f"per_wk={s['per_wk']:.2f} L/S={s['long']}/{s['short']} "
                  f"({time.time()-t0:.0f}s)", flush=True)
            pd.DataFrame(rows).to_csv("out/census_2b.csv", index=False)
    json.dump({"q_w4d": q_by_sym, "S_dist_F0J": s_dist},
              open("runs/q_w4d.json", "w"), indent=2)
    print("q_w4d:", q_by_sym)


if __name__ == "__main__":
    main()
