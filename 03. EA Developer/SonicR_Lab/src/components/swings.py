"""swings.py - two fixed swing detectors (Phase B spec).

(a) fractal2: strength-2 fractal == 16/08 parser (SNR_Signal semantics,
    strict > / <). CONFIRMATION LAG = 2 bars: a swing at bar i is usable
    only for decision bars t >= i+2.
(b) atr_zigzag: reversal 1.5 x ATR14. An extreme becomes a confirmed swing
    on the bar whose counter-close exceeds 1.5*ATR14 measured at the
    extreme bar. CONFIRMATION LAG = variable: confirm_bar index is stored;
    a swing (idx,px) is usable for decision bar t iff confirm_bar <= t.

Both return arrays of confirmed swings in FORWARD time order:
    idx[]  int   bar index of the extreme
    px[]   float extreme price
    dir[]  int   +1 swing high, -1 swing low
    conf[] int   confirmation bar index (usable iff conf <= t)
"""
from __future__ import annotations

import numpy as np


def fractal2(h: np.ndarray, l: np.ndarray):
    """16/08 detector. Returns dict(idx, px, dir, conf). conf = idx+2."""
    n = len(h)
    idx, px, d = [], [], []
    for i in range(2, n - 2):
        hi = h[i]
        if hi > h[i - 1] and hi > h[i - 2] and hi > h[i + 1] and hi > h[i + 2]:
            idx.append(i); px.append(hi); d.append(1)
        lo = l[i]
        if lo < l[i - 1] and lo < l[i - 2] and lo < l[i + 1] and lo < l[i + 2]:
            idx.append(i); px.append(lo); d.append(-1)
    idx = np.asarray(idx, np.int64)
    return {"idx": idx, "px": np.asarray(px, np.float64),
            "dir": np.asarray(d, np.int8), "conf": idx + 2,
            "lag": 2, "name": "fractal2"}


def atr_zigzag(h: np.ndarray, l: np.ndarray, c: np.ndarray,
               atr: np.ndarray, mult: float = 1.5):
    """ATR zigzag. Track running extreme; when a bar CLOSES >= mult*ATR
    (ATR measured at the extreme bar) against the extreme, the extreme is
    confirmed and direction flips. First direction seeded by the first
    displacement >= mult*ATR from the first bar's close."""
    n = len(h)
    idx, px, d, conf = [], [], [], []
    if n == 0:
        return {"idx": np.array(idx), "px": np.array(px),
                "dir": np.array(d), "conf": np.array(conf),
                "lag": "variable", "name": "zigzag"}
    cur_dir = 0                        # 0 unseeded, +1 up-leg, -1 dn-leg
    hi_i, hi_p = 0, h[0]
    lo_i, lo_p = 0, l[0]
    for i in range(1, n):
        if cur_dir == 0:
            if h[i] > hi_p:
                hi_p, hi_i = h[i], i
            if l[i] < lo_p:
                lo_p, lo_i = l[i], i
            a_hi, a_lo = atr[hi_i], atr[lo_i]
            if np.isfinite(a_hi) and c[i] <= hi_p - mult * a_hi:
                idx.append(hi_i); px.append(hi_p); d.append(1)
                conf.append(i)
                cur_dir = -1; lo_p, lo_i = l[i], i
            elif np.isfinite(a_lo) and c[i] >= lo_p + mult * a_lo:
                idx.append(lo_i); px.append(lo_p); d.append(-1)
                conf.append(i)
                cur_dir = 1; hi_p, hi_i = h[i], i
        elif cur_dir == 1:
            a = atr[hi_i]
            if h[i] >= hi_p:
                hi_p, hi_i = h[i], i
            elif np.isfinite(a) and c[i] <= hi_p - mult * a:
                idx.append(hi_i); px.append(hi_p); d.append(1)
                conf.append(i)
                cur_dir = -1; lo_p, lo_i = l[i], i
        else:
            a = atr[lo_i]
            if l[i] <= lo_p:
                lo_p, lo_i = l[i], i
            elif np.isfinite(a) and c[i] >= lo_p + mult * a:
                idx.append(lo_i); px.append(lo_p); d.append(-1)
                conf.append(i)
                cur_dir = 1; hi_p, hi_i = h[i], i
    # final extreme stays UNCONFIRMED (no reversal seen) -> excluded.
    return {"idx": np.asarray(idx, np.int64),
            "px": np.asarray(px, np.float64),
            "dir": np.asarray(d, np.int8),
            "conf": np.asarray(conf, np.int64),
            "lag": "variable", "name": "zigzag"}


def swings_usable(sw: dict, t: int) -> np.ndarray:
    """Boolean mask over sw['idx']: usable for decision at close of bar t."""
    return sw["conf"] <= t


def last_before(sw: dict, t: int, direction: int):
    """Most recent usable swing of `direction` (-1 low / +1 high) at bar t.
    Returns (position_in_sw, bar_index) or (None, None)."""
    usable = np.nonzero((sw["conf"] <= t) & (sw["dir"] == direction))[0]
    if len(usable) == 0:
        return None, None
    k = usable[-1]
    return int(k), int(sw["idx"][k])
