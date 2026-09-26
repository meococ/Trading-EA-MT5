"""sf_census.py — DESIGN census for a family detector (NO outcomes).

Counts signals per week / per symbol and prints a table.  Reads only the
zone caches; runs the detector, never the fill engine.

Usage: python sf_census.py f1_zone_rejection [--params k=v,...]
"""

import importlib
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx      # noqa: E402
import pa_costs    # noqa: E402

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]


def _parse_params(arg):
    out = {}
    if not arg:
        return out
    for kv in arg.split(","):
        k, v = kv.split("=", 1)
        try:
            v = int(v)
        except ValueError:
            try:
                v = float(v)
            except ValueError:
                pass
        out[k] = v
    return out


def census(mod, params=None, symbols=SYMBOLS):
    params = params or {}
    gen = params.get("gen", mod.DEFAULTS.get("gen", "line1_cluster"))
    rows = {}
    for sym in symbols:
        if hasattr(mod, "_load"):
            D = mod._load(sym)
        else:
            D = sf_ctx.load_cache(sym, gen)
        c_rt = pa_costs.C_RT_P90[sym]
        t0 = time.time()
        ent = mod.detect(D, c_rt, params)
        weeks = np.asarray(D["t"], dtype=np.int64) // 604800
        live = ~np.asarray(D["warmup"], dtype=bool)
        n_weeks = len(np.unique(weeks[live])) if live.any() else 1
        sigs = np.array([e["sig"] for e in ent], dtype=np.int64)
        per_week = (len(sigs) / n_weeks) if n_weeks else 0.0
        rows[sym] = {"n_signals": len(ent), "n_weeks": int(n_weeks),
                     "per_week": per_week, "secs": round(time.time() - t0, 1)}
    return rows


def main():
    fam = sys.argv[1] if len(sys.argv) > 1 else "f1_zone_rejection"
    params = _parse_params(
        next((a.split("=", 1)[1] for a in sys.argv[2:]
              if a.startswith("--params=")), None))
    mod = importlib.import_module(fam)
    rows = census(mod, params)
    tot_s = sum(r["n_signals"] for r in rows.values())
    tot_w = max(r["n_weeks"] for r in rows.values())
    print(f"{fam} params={params}")
    for sym, r in rows.items():
        print(f"  {sym:8s} signals={r['n_signals']:5d}  "
              f"per_week={r['per_week']:6.2f}  ({r['secs']}s)")
    print(f"  BASKET   signals={tot_s:5d}  per_week={tot_s/tot_w:6.2f}")


if __name__ == "__main__":
    main()
