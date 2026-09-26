"""run_census.py - outcome-blind census on DESIGN (C2). No P/L anywhere."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from src import data as dm
from src import runner
from src.variants.registry import CONFIGS


def sig_frame(orders: list, tf) -> pd.DataFrame:
    return pd.DataFrame({
        "t": [o["t"] for o in orders],
        "ctm": [int(tf["t"][o["t"]]) for o in orders],
        "dir": [o["dir"] for o in orders],
        "at_sr": [o["meta"].get("at_sr", -1) for o in orders],
        "thru": [o["meta"].get("thru", -1) for o in orders],
        "pv_bias": [o["meta"].get("pv_bias", 0) for o in orders],
        "pv_mode": [o["meta"].get("pv_mode", 0) for o in orders],
    })


def main():
    rows = []
    all_sigs = {}
    for sym in dm.SYMBOLS:
        ctx15 = runner.get_ctx(sym, 15)
        ctx5 = runner.get_ctx(sym, 5)
        cap = runner.xau_sl_cap(ctx15) if sym == "XAUUSD" else None
        weeks = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)
        for cfg in CONFIGS:
            ctx = ctx5 if cfg["family"] == "F3" else ctx15
            ctx.reset_zones()
            orders = runner.orders_for(ctx, cfg, *dm.DESIGN, xau_cap=cap)
            order_cache.save_orders(sym, cfg["id"], dm.DESIGN, orders)
            sf = sig_frame(orders, ctx.tf)
            all_sigs[(sym, cfg["id"])] = sf
            n = len(sf)
            rows.append({
                "sym": sym, "cfg": cfg["id"], "family": cfg["family"],
                "signals": n,
                "sig_wk": n / weeks,
                "long": int((sf["dir"] == 1).sum()) if n else 0,
                "short": int((sf["dir"] == -1).sum()) if n else 0,
                "at_sr_share": float((sf["at_sr"] == 1).mean()) if n
                else np.nan,
                "thru_share": float((sf["thru"] == 1).mean()) if n
                else np.nan,
                "sparse": n / weeks < 0.5,
            })
    # pairwise overlap within each symbol (same signal bar + direction)
    ov_rows = []
    for sym in dm.SYMBOLS:
        sets = [set(zip(s["t"].tolist(), s["dir"].tolist()))
                for s in [all_sigs[(sym, c["id"])] for c in CONFIGS]]
        for i, a in enumerate(CONFIGS):
            for j, b in enumerate(CONFIGS):
                if j <= i:
                    continue
                inter = len(sets[i] & sets[j])
                if inter:
                    ov_rows.append({"sym": sym, "a": a["id"], "b": b["id"],
                                    "overlap": inter})
    df = pd.DataFrame(rows)
    os.makedirs("out", exist_ok=True)
    df.to_csv("out/census.csv", index=False)
    pd.DataFrame(ov_rows).to_csv("out/census_overlap.csv", index=False)
    with open("CENSUS.md", "w") as f:
        f.write("# CENSUS - outcome-blind signal census (DESIGN only)\n\n")
        f.write("No P/L is computed here or anywhere above this file.\n\n")
        f.write("```\n" + df.to_string(index=False) + "\n```\n")
        f.write("\n\n## Pairwise signal-bar overlap (same t and dir)\n\n")
        f.write("```\n" + (pd.DataFrame(ov_rows).to_string(index=False)
                if ov_rows else "(none)") + "\n```\n")
        f.write("\n")
    print(df.to_string())
    print("CENSUS.md + out/census.csv written")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"[census] done {time.time()-t0:.0f}s")
