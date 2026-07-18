"""Holdout-sealed bar loading + split utilities (mechanism-neutral).

The holdout boundary is enforced at READ time (parquet filter) and asserted
after load; the caller receives a seal receipt to embed in its artifact.
Split bounds and the holdout date are lane parameters from the frozen plan —
nothing here hardcodes windows.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load_sealed_bars(path: Path, holdout_start: pd.Timestamp,
                     time_col: str = "time_utc",
                     sort_col: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Load bars strictly before `holdout_start`; return (df, seal receipt)."""
    holdout_start = pd.Timestamp(holdout_start)
    df = pd.read_parquet(path, filters=[(time_col, "<", holdout_start)])
    if len(df) and pd.to_datetime(df[time_col]).max() >= holdout_start:
        raise RuntimeError(f"HOLDOUT SEAL VIOLATION: {path} contains bars >= {holdout_start}")
    df = df.sort_values(sort_col or time_col).reset_index(drop=True)
    receipt = {
        "bars_path": str(path),
        "bars_sha256": sha256_file(Path(path)),
        "time_col": time_col,
        "holdout_start": str(holdout_start),
        "bars_loaded": int(len(df)),
        "holdout_bars_loaded": 0,
        "last_bar_loaded": str(pd.to_datetime(df[time_col]).max()) if len(df) else None,
    }
    return df, receipt


def tag_splits(df: pd.DataFrame, bounds: dict[str, tuple[str, str]],
               time_col: str = "time_utc") -> pd.Series:
    """Label rows by named split; bounds = {name: (from_date, to_date)} inclusive."""
    t = pd.to_datetime(df[time_col])
    out = pd.Series([None] * len(df), index=df.index, dtype=object)
    for name, (lo, hi) in bounds.items():
        mask = (t >= pd.Timestamp(lo)) & (t <= pd.Timestamp(hi) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
        out[mask] = name
    return out


def elapsed_weeks(lo: str | date, hi: str | date) -> float:
    """Elapsed CALENDAR weeks (workspace cadence denominator), inclusive bounds."""
    lo_d, hi_d = pd.Timestamp(lo).date(), pd.Timestamp(hi).date()
    return ((hi_d - lo_d).days + 1) / 7.0
