"""pvsra.py - PVSRA regime label (reconstructed, label-only).

Doctrine (atlas S4 / BAO_CAO section 3): market makers show as volume
below support (bulls) or above resistance (bears). Deterministic
reconstruction:

  Over the last K=20 bars, take bars with PVA class rising|climax.
  For each such bar j, let sup = nearest live support zone (dir=-1) and
  res = nearest live resistance zone (dir=+1), distances to close[j].
    bull_v += tv[j] if close[j] <= sup.hi   (activity at/under support)
    bear_v += tv[j] if close[j] >= res.lo   (activity at/above resistance)
  bias = bull if bull_v > 1.5*bear_v; bear if bear_v > 1.5*bull_v;
         else none (also none when no notable volume)
  mode = run  if sign(EMA34-mid slope over 3 bars) agrees with bias
         build if it disagrees; none if bias == none

All inputs closed-bar; zones evaluated at each lookback bar (causal).
Tag: reconstructed (PVSRA has no published deterministic regime code).
"""
from __future__ import annotations

import numpy as np

from . import pva as pva_mod

NONE_B, BULL, BEAR = 0, 1, -1
NONE_M, RUN, BUILD = 0, 1, 2
BIAS_NAME = {0: "none", 1: "bull", -1: "bear"}
MODE_NAME = {0: "none", 1: "run", 2: "build"}


def pvsra_label(t: int, cls: np.ndarray, close: np.ndarray,
                tv: np.ndarray, mid: np.ndarray, zones_of_bar,
                k: int = 20, slope_n: int = 3) -> tuple[int, int]:
    """Return (bias, mode) ints. zones_of_bar(j) -> live zones at bar j."""
    bull_v = bear_v = 0.0
    j0 = max(0, t - k + 1)
    for j in range(j0, t + 1):
        if cls[j] not in (pva_mod.RISING, pva_mod.CLIMAX):
            continue
        cj = close[j]
        sup = res = None
        dsup = dres = np.inf
        for z in zones_of_bar(j):
            d = min(abs(cj - z["lo"]), abs(cj - z["hi"]))
            if z["dir"] == -1 and d < dsup:
                sup, dsup = z, d
            elif z["dir"] == 1 and d < dres:
                res, dres = z, d
        if sup is not None and cj <= sup["hi"]:
            bull_v += tv[j]
        if res is not None and cj >= res["lo"]:
            bear_v += tv[j]
    if bull_v == 0.0 and bear_v == 0.0:
        return NONE_B, NONE_M
    if bull_v > 1.5 * bear_v:
        bias = BULL
    elif bear_v > 1.5 * bull_v:
        bias = BEAR
    else:
        return NONE_B, NONE_M
    if t - slope_n < 0 or not np.isfinite(mid[t]) or \
            not np.isfinite(mid[t - slope_n]):
        return bias, NONE_M
    slope = mid[t] - mid[t - slope_n]
    if bias == BULL:
        return bias, (RUN if slope > 0 else BUILD)
    return bias, (RUN if slope < 0 else BUILD)


def pv_agrees(bias: int, mode: int, direction: int) -> bool:
    """Ladder gate: bias == trade side AND mode == run."""
    return mode == RUN and ((direction > 0 and bias == BULL)
                            or (direction < 0 and bias == BEAR))
