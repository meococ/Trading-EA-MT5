"""build_caches.py — build sf_ctx zone caches for SF01 (DESIGN only).

Usage: python build_caches.py [SYMBOL ...] [--gens g1,g2]
Acquires one pa_slots slot; skips existing caches.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_slots   # noqa: E402
import sf_ctx     # noqa: E402

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
GENS = ["line1_cluster", "sd_base"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    gens = GENS
    for a in sys.argv[1:]:
        if a.startswith("--gens="):
            gens = a.split("=", 1)[1].split(",")
    symbols = args or SYMBOLS
    with pa_slots.slot("sf01-zcache", timeout=7200):
        for sym in symbols:
            for gen in gens:
                path = sf_ctx.cache_path(sym, gen)
                if os.path.exists(path):
                    print(f"skip {sym}/{gen} (exists)", flush=True)
                    continue
                t0 = time.time()
                print(f"build {sym}/{gen} ...", flush=True)
                sf_ctx.build_cache(
                    sym, gen,
                    progress=lambda t, n: print(f"  {sym}/{gen} {t}/{n}",
                                                flush=True))
                print(f"done {sym}/{gen} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
