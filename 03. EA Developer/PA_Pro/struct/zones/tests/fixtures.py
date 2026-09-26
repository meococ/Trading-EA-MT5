"""fixtures.py — shared test helpers for the T-PAPRO-ZONE-1 zone prototypes.

Path setup + two data sources:
- `synthetic_bars()`: deterministic M5 bars on complete H1 buckets (unit tests
  run offline and fast);
- `load_ctx()` (from `data_helpers.py`): real EURUSD DESIGN bars via
  `PA_Pro/lib/pa_data.py` (READ-ONLY), M5 + complete H1 buckets.

No outcomes anywhere.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ZONES_DIR = os.path.dirname(HERE)                     # .../PA_Pro/struct/zones
PA_PRO = os.path.dirname(os.path.dirname(ZONES_DIR))  # .../PA_Pro
LIB = os.path.join(PA_PRO, "lib")
for _p in (ZONES_DIR, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import ZoneContext                      # noqa: E402
from data_helpers import load_ctx, slice_bars       # noqa: E402

__all__ = ["synthetic_bars", "load_ctx", "slice_bars", "synthetic_ctx"]

_START = 1451606400          # 2016-01-01 00:00:00 UTC, an exact hour boundary


def _weekday(ts):
    import datetime as dt
    return dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc).weekday()


def _h1_from_m5(m5):
    """Complete 12-bar H1 buckets (synthetic data is gapless)."""
    t = m5["t"]
    key = t // 3600
    _, first = np.unique(key, return_index=True)
    n = len(t) // 12
    o = np.array([m5["o"][first[i]] for i in range(n)])
    h = np.array([m5["h"][first[i]:first[i] + 12].max() for i in range(n)])
    l = np.array([m5["l"][first[i]:first[i] + 12].min() for i in range(n)])
    c = np.array([m5["c"][first[i] + 11] for i in range(n)])
    return {"symbol": "SYN", "t": (np.unique(key) * 3600).astype(np.int64),
            "o": o, "h": h, "l": l, "c": c}


def synthetic_bars(n=2400, seed=7, pip=1e-4):
    """Deterministic M5 bars with a trending + mean-reverting pattern."""
    rng = np.random.default_rng(seed)
    k = np.arange(n)
    drift = 0.00025 * np.sin(k / 130.0) + 0.00004 * (k // 400)
    noise = rng.normal(0.0, 1.2e-4, n)
    c = 1.1000 + np.cumsum(drift + noise)
    rng2 = np.random.default_rng(seed + 1)
    h = c + np.abs(rng2.normal(0.0, 0.7e-4, n)) + 0.2e-4
    l = c - np.abs(rng2.normal(0.0, 0.7e-4, n)) - 0.2e-4
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum.reduce([h, o, c])
    l = np.minimum.reduce([l, o, c])
    t = _START + 300 * np.arange(n, dtype=np.int64)
    m5 = {
        "symbol": "SYN", "split": "DESIGN", "tf": "M5", "pip": pip,
        "t": t, "o": o, "h": h, "l": l, "c": c,
        "warmup": np.zeros(n, dtype=bool),
        "utc_min": ((t % 86400) // 60).astype(np.int64),
        "srv_min": ((t % 86400) // 60).astype(np.int64),
        "dow": np.asarray([_weekday(x) for x in t], dtype=np.int64),
    }
    h1 = _h1_from_m5(m5)
    return m5, h1


def synthetic_ctx(n=2400, seed=7):
    m5, h1 = synthetic_bars(n=n, seed=seed)
    return ZoneContext(m5, h1)
