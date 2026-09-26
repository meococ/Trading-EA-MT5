"""indicators.py - causal EMA/ATR primitives (closed bars only).

All functions are pure, return arrays aligned with the input index; warmup
positions are NaN. Sources: INDICATORS.md sections 1-2 (S13/S24 code-exact).
"""
from __future__ import annotations

import numpy as np


def ema(x: np.ndarray, period: int) -> np.ndarray:
    """Standard MT5-style EMA: seed = SMA of first `period` values, then
    recursive k = 2/(period+1). Output[i] uses x[0..i] only (causal).
    Positions < period-1 are NaN (MT5 returns EMPTY_VALUE there)."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    out = np.full(n, np.nan)
    if n < period or period < 1:
        return out
    k = 2.0 / (period + 1.0)
    seed = np.mean(x[:period])
    out[period - 1] = seed
    for i in range(period, n):
        out[i] = out[i - 1] + k * (x[i] - out[i - 1])
    return out


def atr_wilder(h: np.ndarray, l: np.ndarray, c: np.ndarray,
               period: int = 14) -> np.ndarray:
    """Wilder ATR (iATR semantics): TR then Wilder-smoothed, seeded by the
    SMA of the first `period` TRs at index `period`. Positions <= period-1
    NaN. Causal: ATR[i] uses bars <= i."""
    h = np.asarray(h, np.float64); l = np.asarray(l, np.float64)
    c = np.asarray(c, np.float64)
    n = len(h)
    tr = np.full(n, np.nan)
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    out = np.full(n, np.nan)
    if n <= period:
        return out
    out[period] = np.mean(tr[1:period + 1])
    for i in range(period + 1, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def dragon(d: dict, period: int = 34):
    """Filled Dragon (source-primary S13/S24, INDICATORS.md §1):
    EMA34 of High / Close / Low -> (high, mid, low) band."""
    return (ema(d["h"], period), ema(d["c"], period), ema(d["l"], period))


def trend(d: dict, period: int = 89) -> np.ndarray:
    """Trend = EMA89 of close (source-primary S10/S26)."""
    return ema(d["c"], period)


def dragon_angle_atr(mid: np.ndarray, atr: np.ndarray, n: int = 5):
    """W4 angle proxy (reconstructed — TAH code computes no slope):
    angle[t] = (mid[t]-mid[t-N]) / (N * ATR14[t]). Units: ATR per bar."""
    out = np.full(len(mid), np.nan)
    out[n:] = (mid[n:] - mid[:-n]) / (n * atr[n:])
    return out
