"""bars_cache — TUNE-v2 M5 bars for the boxlab lane, one bulk load.

BOX-LAB local copy of the linelab cache approach so all derived files stay
under ``research/perception/boxlab/``.  Bars come only through the sanctioned
door (``golden/book_loader.load_m5``, the read-only M1 parquet cache rolled
to M5).  TUNE dates only — HOLD is never touched.
"""
import os
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
_GOLD = os.path.join(_PERC, "golden")
for _p in (_GOLD, _PERC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import book_loader  # noqa: E402

CACHE_NPZ = os.path.join(_HERE, "cache", "tune_m5.npz")
TUNE = ("2012-03-01", "2012-06-01")


def load_all():
    """Load every TUNE day of M5 bars; npz cache under boxlab/cache/."""
    if os.path.exists(CACHE_NPZ):
        z = np.load(CACHE_NPZ)
        dates = [str(d) for d in z["dates"]]
        bars = {d: {k: z[f"{d}|{k}"] for k in ("m", "o", "h", "l", "c", "cet")}
                for d in dates}
        return dates, bars
    b = book_loader.load_m5(TUNE[0] + " 00:00", TUNE[1] + " 00:00")
    import datetime as _dt
    dates_arr = np.array([_dt.datetime.utcfromtimestamp(int(e)).date().isoformat()
                          for e in b["cet"]])
    out, store = {}, {}
    for d in np.unique(dates_arr):
        k = dates_arr == d
        day = {"m": b["cet_min"][k].astype(np.int64),
               "o": b["o"][k] * 1e4, "h": b["h"][k] * 1e4,
               "l": b["l"][k] * 1e4, "c": b["c"][k] * 1e4,
               "cet": b["cet"][k].astype(np.int64)}
        out[str(d)] = day
        for kk, vv in day.items():
            store[f"{d}|{kk}"] = vv
    os.makedirs(os.path.dirname(CACHE_NPZ), exist_ok=True)
    np.savez(CACHE_NPZ, dates=np.array(sorted(out)), **store)
    return sorted(out), out


def abr50(h, l, c):
    """50-bar EMA of true range (same construction as evalcheck/cache.abr)."""
    n = len(h)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    abr = np.zeros(n)
    abr[0] = tr[0]
    a = 2.0 / 51.0
    for i in range(1, n):
        abr[i] = a * tr[i] + (1 - a) * abr[i - 1]
    return abr


def day_slice(day, m0, m1):
    """Boolean mask of bars with m0 <= cet_min <= m1 (order-safe)."""
    if m0 is None or m1 is None:
        return np.zeros(len(day["m"]), dtype=bool)
    lo, hi = (m0, m1) if m0 <= m1 else (m1, m0)
    return (day["m"] >= lo) & (day["m"] <= hi)


def idx_of(day, cet_min, tol_bars=0):
    """Index of the bar at cet_min, else nearest within tol_bars*5m."""
    m = day["m"]
    if not len(m):
        return None
    j = int(np.argmin(np.abs(m - cet_min)))
    if abs(int(m[j]) - cet_min) <= max(0, tol_bars) * 5 + 2:
        return j
    return None
