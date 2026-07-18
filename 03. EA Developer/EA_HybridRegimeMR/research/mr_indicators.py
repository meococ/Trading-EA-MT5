"""Indicator math for HYP-MR-REGIME-EURUSD-H1-001.

Copied verbatim (math unchanged) from the Owner-supplied reference skeleton
`05. Playbook/Strategy/MR/mr_system/features/indicators.py`, which passed the
2026-07-17 adversarial leakage review (detrend / rolling_half_life /
atr_percentile confirmed leakage-clean and off-by-one-correct). ADX/ATR are
Wilder-style; MT5 iADX/iATR parity remains UNVERIFIED and is a precondition
for trusting a SURVIVE, not a KILL (PROBE_PLAN section 4/7).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

LN2 = float(np.log(2.0))


def wilder_rma(s: pd.Series, period: int) -> pd.Series:
    """Wilder smoothing: init = SMA(period), then alpha = 1/period."""
    arr = s.to_numpy(dtype=float)
    out = np.full(arr.shape, np.nan)
    if len(arr) < period:
        return pd.Series(out, index=s.index)
    valid = ~np.isnan(arr)
    first = np.argmax(valid) if valid.any() else len(arr)
    start = first + period - 1
    if start >= len(arr):
        return pd.Series(out, index=s.index)
    out[start] = np.nanmean(arr[first:first + period])
    alpha = 1.0 / period
    for i in range(start + 1, len(arr)):
        x = arr[i]
        out[i] = out[i - 1] if np.isnan(x) else out[i - 1] + alpha * (x - out[i - 1])
    return pd.Series(out, index=s.index)


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)


def atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return wilder_rma(true_range(df), period)


def adx_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l = df["high"], df["low"]
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_s = wilder_rma(true_range(df), period)
    pdi = 100.0 * wilder_rma(plus_dm, period) / atr_s
    mdi = 100.0 * wilder_rma(minus_dm, period) / atr_s
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi).replace(0.0, np.nan)
    return wilder_rma(dx, period)


def detrend(close: pd.Series, W: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """D = close - SMA(W); sigma = std(ddof=0) of D over W; z = D/sigma."""
    mu = close.rolling(W).mean()
    D = close - mu
    sigma = D.rolling(W).std(ddof=0)
    z = D / sigma.replace(0.0, np.nan)
    return D, sigma, z


def rolling_half_life(D: pd.Series, W: int) -> tuple[pd.Series, pd.Series]:
    """Regression dD_t = a + lambda*D_{t-1}: HL = -ln2/lambda (bars)."""
    y = D.diff().to_numpy(dtype=float)
    x = D.shift(1).to_numpy(dtype=float)
    n = len(D)
    lam = np.full(n, np.nan)
    for i in range(W, n):
        xs = x[i - W + 1: i + 1]
        ys = y[i - W + 1: i + 1]
        m = ~(np.isnan(xs) | np.isnan(ys))
        if m.sum() < int(0.8 * W):
            continue
        xv, yv = xs[m], ys[m]
        xm, ym = xv.mean(), yv.mean()
        den = float(((xv - xm) ** 2).sum())
        if den <= 0.0:
            continue
        lam[i] = float(((xv - xm) * (yv - ym)).sum()) / den
    lam_s = pd.Series(lam, index=D.index)
    hl = -LN2 / lam_s
    hl[lam_s >= 0] = np.nan
    return lam_s, hl


def atr_percentile(atr: pd.Series, lookback: int = 250) -> pd.Series:
    """Percentile of current ATR within the prior `lookback` bars (0..100)."""
    def _pct(w: np.ndarray) -> float:
        return 100.0 * (w[:-1] <= w[-1]).mean()
    return atr.rolling(lookback + 1).apply(_pct, raw=True)
