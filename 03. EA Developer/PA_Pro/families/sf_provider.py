"""sf_provider.py — data_provider for pa_eval.evaluate used by SF01.

Wraps ``pa_data.frame`` (the default provider path) and adds ``utc_start`` /
``utc_end``, which ``frame()`` does not return.  Without ``utc_start`` the
evaluator's matched-random warmup filter (`live_cut`) is silently disabled and
random picks on warm-up bars reach ``pa_fill.simulate``, which then raises on
``sig < first_live_idx``.  Both fields are inside ``_DATA_SHA_FIELDS`` so the
ledger commitment covers them.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import pa_data      # noqa: E402
import pa_sealed    # noqa: E402

__all__ = ["provider"]

FRAMES = {}


def provider(symbol, split, tf, warmup_days=30):
    key = (symbol, split, tf, warmup_days)
    if key not in FRAMES:
        d = pa_data.frame(symbol, split=split, tf=tf, warmup_days=warmup_days)
        lo, hi, _s, _e = pa_sealed.split_bounds(split)
        d["utc_start"] = int(lo)
        d["utc_end"] = int(hi)
        FRAMES[key] = d
    return FRAMES[key]
