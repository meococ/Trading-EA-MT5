"""bars_cache — one-door M5 access for the linelab lane.

All bars come from golden/book_loader.py (the only permitted door).
The whole TUNE date range is loaded once and cached to
linelab/cache/tune_m5.npz so repeat runs do not re-read the parquet.

Day dict: {"t": epoch, "m": cet_min int64, "o/h/l/c": float64 PIPS}
(matching eval.day_bars conventions: prices already divided by 1e-4).
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_PERC, "golden"))
sys.path.insert(0, _PERC)

import book_loader  # noqa: E402

TUNE = os.path.join(_PERC, "golden", "draft", "BOOK2012_TUNE_v2.jsonl")
CACHE_NPZ = os.path.join(_HERE, "cache", "tune_m5.npz")


def tune_records():
    with open(TUNE, encoding="utf8") as f:
        return [json.loads(x) for x in f if x.strip()]


def tune_dates():
    return sorted({r["date"] for r in tune_records()})


def _load_fresh():
    dates = tune_dates()
    b = book_loader.load_m5(dates[0] + " 00:00",
                            _next_day(dates[-1]) + " 00:00")
    return b


def _next_day(d):
    import datetime as dt
    x = dt.datetime.strptime(d, "%Y-%m-%d") + dt.timedelta(days=1)
    return x.strftime("%Y-%m-%d")


def load_all():
    """Full M5 arrays for the TUNE range (cached npz)."""
    if os.path.exists(CACHE_NPZ):
        z = np.load(CACHE_NPZ)
        return {k: z[k] for k in ("t", "cet", "cet_min", "o", "h",
                                  "l", "c")}
    b = _load_fresh()
    out = {k: b[k] for k in ("t", "cet", "cet_min", "o", "h", "l", "c")}
    np.savez(CACHE_NPZ, **out)
    return out


def days():
    """{date_str: day dict with o/h/l/c in PIPS, m = cet_min}."""
    b = load_all()
    import datetime as dt
    dates = np.array([dt.datetime.utcfromtimestamp(int(e)).date()
                      .isoformat() for e in b["cet"]])
    out = {}
    for d in np.unique(dates):
        k = dates == d
        out[str(d)] = {
            "t": b["t"][k], "m": b["cet_min"][k].astype(np.int64),
            "o": b["o"][k] / 1e-4, "h": b["h"][k] / 1e-4,
            "l": b["l"][k] / 1e-4, "c": b["c"][k] / 1e-4,
            # absolute-price copy for renderers that expect price units
            "o_abs": b["o"][k], "h_abs": b["h"][k],
            "l_abs": b["l"][k], "c_abs": b["c"][k]}
    return out


def abr(day, n=50):
    """ABR(n) in pips, causal (mean of last n closed-bar ranges)."""
    rng = day["h"] - day["l"]
    out = np.empty(len(rng))
    acc = 0.0
    for i in range(len(rng)):
        acc += rng[i]
        if i >= n:
            acc -= rng[i - n]
        out[i] = acc / min(i + 1, n)
    return out
