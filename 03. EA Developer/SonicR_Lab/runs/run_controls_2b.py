"""run_controls_2b.py - negative controls for 2B passers only (D2/D5).

Per LEAD_NOTE_4: controls (100-seed random entry, flip, +20b shift) run
ONLY for 2B configs that cleared the selection rule on DESIGN. Reuses
run_controls.controls_for on cached orders. Writes out/controls_2b.csv.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import order_cache
from run_controls import controls_for
from src import data as dm
from src import runner
from src.variants.registry_2b import CONFIGS_2B

SEL2B = "runs/selection_2b.json"


def main():
    sel = json.load(open(SEL2B))
    rows = []
    null_store = {}
    for item in sel["controls"]:
        sym, cid = item["sym"], item["cfg"]
        cfg = next(c for c in CONFIGS_2B if c["id"] == cid)
        ctx = runner.get_ctx(sym, 15)
        orders = order_cache.load_orders(sym, cid, dm.DESIGN)
        ctx.reset_zones()
        t0 = time.time()
        r = controls_for(sym, cfg, ctx, orders, dm.DESIGN)
        null_store[f"{sym}_{cid}"] = r["null_pfs"]
        rows.append({"sym": sym, "cfg": cid, "n_signals": r["n_signals"],
                     "real_pf": r["real_pf"], "pct": r["pct"],
                     "pf_flip": r["pf_flip"], "pf_shift20": r["pf_shift20"],
                     "null_med": float(np.nanmedian(r["null_pfs"])),
                     "null_p95": float(np.nanpercentile(r["null_pfs"], 95))})
        print(f"[ctrl-2B] {sym} {cid}: pf={r['real_pf']:.2f} "
              f"pct={r['pct']:.0f} flip={r['pf_flip']:.2f} "
              f"shift={r['pf_shift20']:.2f} ({time.time()-t0:.0f}s)",
              flush=True)
        pd.DataFrame(rows).to_csv("out/controls_2b.csv", index=False)
    np.savez_compressed("out/controls_2b_null.npz", **null_store)


if __name__ == "__main__":
    main()
