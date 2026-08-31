"""Single-source indicator math for offline probes (mechanism-neutral).

Pure functions over OHLC frames/series. No strategy defaults live here: every
period/threshold is a caller argument frozen in the lane's plan. Wilder
formulas follow the reviewed leakage-clean implementations; MT5 parity is
verified separately by tools/research/parity_harness.py.
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


def atr_wilder(df: pd.DataFrame, period: int) -> pd.Series:
    return wilder_rma(true_range(df), period)


def adx_wilder(df: pd.DataFrame, period: int) -> pd.Series:
    h, l = df["high"], df["low"]
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr_s = wilder_rma(true_range(df), period)
    pdi = 100.0 * wilder_rma(plus_dm, period) / atr_s
    mdi = 100.0 * wilder_rma(minus_dm, period) / atr_s
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi).replace(0.0, np.nan)
    return wilder_rma(dx, period)


def atr_mt5(df: pd.DataFrame, period: int) -> pd.Series:
    """MT5 iATR semantics: SIMPLE moving average of True Range (not Wilder).

    Parity-proven against build 6006 by tools/research/parity_harness.py.
    Use for EA/Model-0 parity; use atr_wilder for literature replication.
    """
    return true_range(df).rolling(period).mean()


def adx_mt5(df: pd.DataFrame, period: int) -> pd.Series:
    """MT5 iADX semantics: per-bar DI ratios smoothed with EMA(2/(period+1)).

    Follows MetaQuotes ADX.mq5: per-bar +DM/-DM with the tie-zero rule, per-bar
    TR, raw DI = 100*DM/TR, EMA-smoothed DIs, DX from smoothed DIs, EMA of DX.
    Parity-proven by tools/research/parity_harness.py. Use for EA/Model-0
    parity; use adx_wilder for literature replication.
    """
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff().to_numpy(float)
    dn = (-l.diff()).to_numpy(float)
    p = np.where(up > 0, up, 0.0)
    m = np.where(dn > 0, dn, 0.0)
    plus_dm = pd.Series(np.where(p > m, p, 0.0), index=df.index)
    minus_dm = pd.Series(np.where(m > p, m, 0.0), index=df.index)
    pc = c.shift(1)
    tr = pd.concat([h, pc], axis=1).max(axis=1) - pd.concat([l, pc], axis=1).min(axis=1)
    raw_p = (100.0 * plus_dm / tr).where(tr != 0.0, 0.0)
    raw_m = (100.0 * minus_dm / tr).where(tr != 0.0, 0.0)
    pdi = raw_p.iloc[1:].ewm(span=period, adjust=False).mean()
    mdi = raw_m.iloc[1:].ewm(span=period, adjust=False).mean()
    denom = (pdi + mdi)
    dx = (100.0 * (pdi - mdi).abs() / denom).where(denom != 0.0, 0.0)
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx.reindex(df.index)


def rsi_wilder(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = wilder_rma(gain, period)
    avg_loss = wilder_rma(loss, period)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    return rsi.where(avg_loss != 0.0, 100.0)


def sma(s: pd.Series, period: int) -> pd.Series:
    return s.rolling(period).mean()


def ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def detrend(close: pd.Series, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """D = close - SMA(window); sigma = std(ddof=0) of D over window; z = D/sigma."""
    mu = close.rolling(window).mean()
    d = close - mu
    sigma = d.rolling(window).std(ddof=0)
    z = d / sigma.replace(0.0, np.nan)
    return d, sigma, z


def rolling_half_life(d: pd.Series, window: int, min_coverage: float = 0.8) -> tuple[pd.Series, pd.Series]:
    """OLS dD_t = a + lambda*D_{t-1} over a rolling window; HL = -ln2/lambda."""
    y = d.diff().to_numpy(dtype=float)
    x = d.shift(1).to_numpy(dtype=float)
    n = len(d)
    lam = np.full(n, np.nan)
    for i in range(window, n):
        xs = x[i - window + 1: i + 1]
        ys = y[i - window + 1: i + 1]
        m = ~(np.isnan(xs) | np.isnan(ys))
        if m.sum() < int(min_coverage * window):
            continue
        xv, yv = xs[m], ys[m]
        xm, ym = xv.mean(), yv.mean()
        den = float(((xv - xm) ** 2).sum())
        if den <= 0.0:
            continue
        lam[i] = float(((xv - xm) * (yv - ym)).sum()) / den
    lam_s = pd.Series(lam, index=d.index)
    hl = -LN2 / lam_s
    hl[lam_s >= 0] = np.nan
    return lam_s, hl


def rolling_percentile(s: pd.Series, lookback: int) -> pd.Series:
    """Percentile (0..100) of the current value within the prior `lookback` values."""
    def _pct(w: np.ndarray) -> float:
        return 100.0 * (w[:-1] <= w[-1]).mean()
    return s.rolling(lookback + 1).apply(_pct, raw=True)
