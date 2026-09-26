"""data_helpers.py — READ-ONLY data access for the zone prototypes.

Uses the PA-PRO loader (`PA_Pro/lib/pa_data.py`, READ-ONLY) for real EURUSD
DESIGN bars and `common.ZoneContext` for the shared context.  No outcomes.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(os.path.dirname(HERE))
LIB = os.path.join(PA_PRO, "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import ZoneContext  # noqa: E402

__all__ = ["slice_bars", "load_ctx"]

_START = 1451606400          # 2016-01-01 00:00:00 UTC


def slice_bars(bars, n):
    """First n bars of a pa_data-style dict (all same-length arrays)."""
    out = {}
    L = len(bars["t"])
    for k, v in bars.items():
        if isinstance(v, np.ndarray) and len(v) == L:
            out[k] = v[:n]
        else:
            out[k] = v
    return out


def load_ctx(symbol="EURUSD", max_bars=None, warmup_days=30):
    """Real DESIGN bars through the PA-PRO loader (READ-ONLY)."""
    import pa_data
    m1 = pa_data.load_m1(symbol, split="DESIGN", warmup_days=warmup_days)
    m5 = pa_data.resample(m1, "M5")
    h1 = pa_data.resample(m1, "H1")
    if max_bars is not None:
        m5 = slice_bars(m5, max_bars)
        keep = int(m5["t"][-1]) + 300
        h1 = slice_bars(h1, int(np.searchsorted(h1["t"] + 3600, keep,
                                                side="right")))
    return ZoneContext(m5, h1)
