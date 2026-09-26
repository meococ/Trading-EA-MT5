"""diagnostics.py — causal zone-count / speed diagnostic for the bake-off.

Usage (from `03. EA Developer/PA_Pro`):
    python struct/zones/diagnostics.py --max-bars 50000
    python struct/zones/diagnostics.py --max-bars 200000 --bars 30000 90000

Prints, per registered generator: wall seconds, zones created, live/armed
counts and armed width in ATR14(H1) at sampled bars.  No outcomes.
Heavy runs go through `lib/pa_slots.py` (max 2 our processes, 4 threads,
BelowNormal).
"""

import argparse
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(os.path.dirname(HERE))
for _p in (HERE, os.path.join(PA_PRO, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_slots  # noqa: E402  (thread caps + BelowNormal at import)

from data_helpers import load_ctx  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--max-bars", type=int, default=50000)
    ap.add_argument("--bars", type=int, nargs="*", default=None)
    args = ap.parse_args()

    import registry
    ctx = load_ctx(args.symbol, max_bars=args.max_bars)
    n = ctx.n
    qbars = args.bars or [int(x) for x in np.linspace(n // 6, n - 1, 5)]
    print(f"symbol={args.symbol} bars={n} queries={qbars}")
    for name, cls in registry.import_registry():
        t0 = time.time()
        g = cls(ctx).run()
        dt = time.time() - t0
        live, armed, widths = [], [], []
        for t in qbars:
            a, b = g.counts_at(t)
            live.append(a)
            armed.append(b)
            A = ctx.a(t)
            widths.extend((v.hi - v.lo) / A for v in g.views_at(t, arm=True))
        med = float(np.median(widths)) if widths else float("nan")
        print(f"{name:14s} {dt:7.1f}s created={len(g._zones):6d} "
              f"live={live} armed={armed} width_atr_med={med:.2f}")


if __name__ == "__main__":
    with pa_slots.slot("zone1_diagnostics", timeout=600):
        main()
