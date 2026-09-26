"""Canonical research data plane.

One-time ETL: hcc_reader (.hcc, flagged API) -> per-symbol parquet cache with
integrity flags and derived calendar columns. Everything downstream reads this
plane only — no probe touches .hcc directly.

Conventions:
- ctm: int64 epoch seconds (server clock face; treated as naive UTC wall time).
- suspect=True marks burst/packed regions — prices there are NOT tradable
  evidence (roll 00:00-00:15 majors, 01:00-01:16 XAUUSD, scattered USDJPY).
- Event/label windows that overlap suspect bars are void by default.
"""
import os
import sys

import numpy as np
import pandas as pd

LAB = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(LAB, "..", "tools"))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import hcc_reader  # noqa: E402

CACHE = os.path.join(LAB, "cache")
PIP = {"USDJPY": 1e-2, "XAUUSD": 1e-1}
DEFAULT_PIP = 1e-4


def pip_size(sym):
    if sym in PIP:
        return PIP[sym]
    if sym.endswith("JPY"):
        return 1e-2
    return DEFAULT_PIP


def cache_path(sym, y0, y1):
    return os.path.join(CACHE, f"{sym}_M1_{y0}_{y1}.parquet")


def etl_symbol(sym, y0=2010, y1=2026, force=False):
    """Build parquet cache for one symbol. Returns output path."""
    out = cache_path(sym, y0, y1)
    if os.path.exists(out) and not force:
        return out
    bars, suspect, _reps = hcc_reader.load_symbol(sym, y0, y1, flagged=True)
    n = len(bars)
    ctm = np.fromiter(bars.keys(), dtype=np.int64, count=n)
    vals = np.empty((n, 6), dtype=np.float64)
    for i, t in enumerate(ctm):
        vals[i] = bars[t]
    order = np.argsort(ctm)
    ctm = ctm[order]
    vals = vals[order]
    # clip to requested years: year files contain out-of-year records
    lo = int(pd.Timestamp(f"{y0}-01-01", tz="UTC").timestamp())
    hi = int(pd.Timestamp(f"{y1}-12-31 23:59", tz="UTC").timestamp())
    keep = (ctm >= lo) & (ctm <= hi)
    ctm = ctm[keep]
    vals = vals[keep]
    df = pd.DataFrame(
        {
            "o": vals[:, 0],
            "h": vals[:, 1],
            "l": vals[:, 2],
            "c": vals[:, 3],
            "tv": vals[:, 4].astype(np.int32),
            "sp": vals[:, 5].astype(np.float32),
        },
        index=pd.Index(ctm, name="ctm"),
    )
    if len(suspect):
        sus = np.fromiter(suspect, dtype=np.int64)
        df["suspect"] = np.isin(ctm, sus)
    else:
        df["suspect"] = False
    dt = pd.to_datetime(df.index, unit="s", utc=True)
    df["mod"] = (dt.hour * 60 + dt.minute).astype(np.int16)
    df["dow"] = dt.dayofweek.astype(np.int8)
    df["mow"] = (df["dow"].astype(np.int32) * 1440 + df["mod"]).astype(np.int16)
    df["day"] = (df.index // 86400).astype(np.int32)
    df["year"] = dt.year.astype(np.int16)
    os.makedirs(CACHE, exist_ok=True)
    df.to_parquet(out)
    return out


def load(sym, y0=2010, y1=2026):
    """Load cached symbol plane; builds cache if missing."""
    out = cache_path(sym, y0, y1)
    if not os.path.exists(out):
        etl_symbol(sym, y0, y1)
    return pd.read_parquet(out)


SYMBOLS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
           "USDJPY", "XAUUSD"]
