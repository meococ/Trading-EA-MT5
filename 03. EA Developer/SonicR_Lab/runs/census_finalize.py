"""census_finalize.py - rebuild CENSUS.md from cached orders (no regen)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from src import data as dm
from src import runner
from src import sim
from src.variants.registry import CONFIGS


def main():
    rows = []
    all_sigs = {}
    weeks = (dm.DESIGN[1] - dm.DESIGN[0]) / (7 * 86400)
    for sym in dm.SYMBOLS:
        ctx15 = runner.get_ctx(sym, 15)
        ctx5 = runner.get_ctx(sym, 5)
        for cfg in CONFIGS:
            orders = order_cache.load_orders(sym, cfg["id"], dm.DESIGN)
            if orders is None:
                print("MISSING", sym, cfg["id"])
                continue
            ctx = ctx5 if cfg["family"] == "F3" else ctx15
            e2 = sim.e2_rejects(orders, ctx.atr, sym)
            sf = pd.DataFrame({
                "t": [o["t"] for o in orders],
                "dir": [o["dir"] for o in orders],
                "at_sr": [o["meta"].get("at_sr", -1) for o in orders],
                "thru": [o["meta"].get("thru", -1) for o in orders]})
            all_sigs[(sym, cfg["id"])] = sf
            n = len(sf)
            rows.append({"sym": sym, "cfg": cfg["id"],
                         "family": cfg["family"], "signals": n,
                         "sig_wk": round(n / weeks, 2),
                         "long": int((sf["dir"] == 1).sum()),
                         "short": int((sf["dir"] == -1).sum()),
                         "at_sr_share": round(float((sf["at_sr"] == 1)
                                                    .mean()), 3)
                         if n else np.nan,
                         "thru_share": round(float((sf["thru"] == 1)
                                                   .mean()), 3)
                         if n else np.nan,
                         "e2_removed": e2,
                         "sparse": n / weeks < 0.5})
    ov_rows = []
    for sym in dm.SYMBOLS:
        sets = {c["id"]: set(zip(all_sigs[(sym, c["id"])]["t"].tolist(),
                               all_sigs[(sym, c["id"])]["dir"].tolist()))
                for c in CONFIGS if (sym, c["id"]) in all_sigs}
        ids = list(sets)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                inter = len(sets[a] & sets[b])
                if inter:
                    ov_rows.append({"sym": sym, "a": a, "b": b,
                                    "overlap": inter})
    df = pd.DataFrame(rows)
    df.to_csv("out/census.csv", index=False)
    pd.DataFrame(ov_rows).to_csv("out/census_overlap.csv", index=False)
    with open("CENSUS.md", "w") as f:
        f.write("# CENSUS - outcome-blind signal census (DESIGN only)\n\n")
        f.write("No P/L is computed here or anywhere above this file.\n\n")
        f.write("```\n" + df.to_string(index=False) + "\n```\n")
        f.write("\n## Pairwise signal-bar overlap (same t and dir)\n\n```\n")
        f.write(pd.DataFrame(ov_rows).to_string(index=False)
                if ov_rows else "(none)")
        f.write("\n```\n")
    print(df.to_string())
    print("CENSUS.md + out/census.csv written")


if __name__ == "__main__":
    main()
