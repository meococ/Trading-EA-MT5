"""trend.py - ROUND 2E multi-timeframe trend-agreement score S_T.

S_T in {0,1,2,3} per trade, joined on (sym, sig_ctm, dir):
  A1 TREND89 (M15 bar t = the signal bar, open=sig_ctm, close=sig_ctm+900):
     long:  EMA34(close)[t] > EMA89(close)[t];  short: <.
  A2 H1DRAGON (last usable H1 bar j1 = last j with tf60.t[j]+3600 <=
     sig_ctm+900):  long: close[j1] > EMA34(High)[j1];  short: < EMA34(Low).
  A3 H4TREND (last usable H4 bar j4 = last j with tf240.t[j]+14400 <=
     sig_ctm+900):  long: EMA89(close)[j4] > EMA89(close)[j4-6]; short: <.
Warm-up (3 x period bars of history): M15 EMA89 needs bar index >= 266,
H1 EMA34 >= 101, H4 EMA89 >= 266 (A3 lookback 6 subsumed). Any failure
-> S_T = NA and the trade is dropped from the base (same base for all
statistics, X0's own numbers included).

All higher-timeframe bars are built from ALL M1 bars in server time via
data.resample (the same routine the M15 signal context uses); EMAs use
indicators.ema (MT5-style SMA seed, causal). One label set is shared by
H0 and H1 (labels are direction/structure only; harness changes which
trades exist, not the labels).
"""
from __future__ import annotations

import numpy as np

from . import data as dm
from .components import indicators as ind

WARM15 = 3 * 89            # M15 EMA89 -> bar index >= 266
WARM60 = 3 * 34            # H1 EMA34 -> 101
WARM240 = 3 * 89           # H4 EMA89 -> 266
A3_BACK = 6


def build_trend_ctx(m1: dict) -> dict:
    """Per-M15-bar trend-state arrays + the HTF frames (for audits).

    Returns dict with:
      t15: M15 bar open times
      a1,a2,a3: int8 per M15 bar (+1 long-agree, -1 short-agree, 0 = NA)
      j1, j4: index of the usable H1 / H4 bar per M15 bar (-1 if none)
      tf60/tf240 frames for tests
    """
    tf15 = dm.resample(m1, 15)
    tf60 = dm.resample(m1, 60)
    tf240 = dm.resample(m1, 240)
    e34c = ind.ema(tf15["c"], 34)
    e89c = ind.ema(tf15["c"], 89)
    e34h60, _e34c60, e34l60 = ind.dragon(tf60)
    e89_240 = ind.ema(tf240["c"], 89)

    t15 = tf15["t"]
    # usable HTF bar per M15 bar i: open+step <= t15[i]+900
    j1 = np.searchsorted(tf60["t"] + 3600, t15 + 900, side="right") - 1
    j4 = np.searchsorted(tf240["t"] + 14400, t15 + 900, side="right") - 1
    n = len(t15)
    a1 = np.zeros(n, np.int8)
    a2 = np.zeros(n, np.int8)
    a3 = np.zeros(n, np.int8)
    ok1 = (np.arange(n) >= WARM15 - 1) & np.isfinite(e34c) & \
        np.isfinite(e89c)
    a1[ok1] = np.where(e34c[ok1] > e89c[ok1], 1, -1)
    ok2 = j1 >= WARM60 - 1
    j1c = np.clip(j1, 0, len(tf60["t"]) - 1)
    ok2 &= np.isfinite(e34h60[j1c]) & np.isfinite(e34l60[j1c])
    a2[ok2] = np.where(tf60["c"][j1c[ok2]] > e34h60[j1c[ok2]], 1, -1)
    ok3 = j4 >= max(WARM240 - 1, A3_BACK)
    j4c = np.clip(j4, A3_BACK, len(tf240["t"]) - 1)
    ok3 &= np.isfinite(e89_240[j4c]) & np.isfinite(e89_240[j4c - A3_BACK])
    a3[ok3] = np.where(
        e89_240[j4c[ok3]] > e89_240[j4c[ok3] - A3_BACK], 1, -1)
    return {"t15": t15, "a1": a1, "a2": a2, "a3": a3,
            "j1": j1, "j4": j4, "tf60": tf60, "tf240": tf240,
            "tf15": tf15}


def score_trades(tc: dict, trades, sig_col="sig_ctm", dir_col="dir"):
    """Vectorized S_T for a trade table. Returns (S_T float array with
    NaN for NA, and the per-component agreement arrays)."""
    t15, a1, a2, a3 = tc["t15"], tc["a1"], tc["a2"], tc["a3"]
    sig = np.asarray(trades[sig_col], dtype=np.int64)
    dr = np.asarray(trades[dir_col], dtype=np.int64)
    idx = np.searchsorted(t15, sig)                 # M15 bar at sig_ctm
    idx = np.clip(idx, 0, len(t15) - 1)
    ok_pos = t15[idx] == sig                        # exact bar match
    A1 = np.where(a1[idx] == dr, 1, 0)
    A2 = np.where(a2[idx] == dr, 1, 0)
    A3 = np.where(a3[idx] == dr, 1, 0)
    valid = ok_pos & (a1[idx] != 0) & (a2[idx] != 0) & (a3[idx] != 0)
    S = np.where(valid, A1 + A2 + A3, np.nan)
    return S, A1, A2, A3, valid


def score_at_shifted(tc: dict, sig_ctm, dr, lo, hi, shift_sec):
    """Regime-preserving null helper: score the trade as if its M15 bar
    were shifted by `shift_sec` in time, wrapped inside [lo,hi)."""
    t15 = tc["t15"]
    n = len(t15)
    sig = np.asarray(sig_ctm, dtype=np.int64)
    win = hi - lo
    shifted = lo + ((sig - lo + shift_sec) % win)
    idx = np.searchsorted(t15, shifted, side="right") - 1
    idx = np.clip(idx, 0, n - 1)
    dr = np.asarray(dr, dtype=np.int64)
    A1 = np.where(tc["a1"][idx] == dr, 1, 0)
    A2 = np.where(tc["a2"][idx] == dr, 1, 0)
    A3 = np.where(tc["a3"][idx] == dr, 1, 0)
    valid = (tc["a1"][idx] != 0) & (tc["a2"][idx] != 0) & \
            (tc["a3"][idx] != 0)
    S = np.where(valid, A1 + A2 + A3, np.nan)
    return S
