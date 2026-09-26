"""pva.py - TAH PVA (PVSRA volume classifier), code-exact reconstruction.

Source: INDICATORS.md §3 (S8/S14 code-exact), sonicr source indicator
`PVA_volumes.mq4` semantics:

  av[i]     = mean(vol[i-10 .. i-1])            # 10 PREVIOUS bars, excl. i
  sv_i      = vol[i] * (h[i]-l[i])
  HiValue2  = max(sv over the 10 PREVIOUS bars) # excl. i
  climax[i] = sv_i >= HiValue2 OR vol[i] >= 2*av
  rising[i] = vol[i] >= 1.5*av  (when not climax)

Class encoding: 0=normal, 1=rising, 2=climax. Direction by candle sign.
Causal: PVA[i] uses bars <= i only.
"""
from __future__ import annotations

import numpy as np

NORMAL, RISING, CLIMAX = 0, 1, 2


def pva_class(h: np.ndarray, l: np.ndarray, c: np.ndarray,
              o: np.ndarray, tv: np.ndarray):
    """Return (cls, dir) int arrays. cls in {0,1,2}; dir +1 bull, -1 bear,
    0 doji. First 10 bars are NORMAL (av undefined)."""
    n = len(tv)
    vol = np.asarray(tv, np.float64)
    sv = vol * (np.asarray(h, np.float64) - np.asarray(l, np.float64))
    cls = np.zeros(n, np.int8)
    av = np.full(n, np.nan)
    hi2 = np.full(n, np.nan)
    for i in range(10, n):
        a = vol[i - 10:i].mean()
        m = sv[i - 10:i].max()
        av[i] = a; hi2[i] = m
        if a <= 0:
            continue
        if sv[i] >= m or vol[i] >= 2.0 * a:
            cls[i] = CLIMAX
        elif vol[i] >= 1.5 * a:
            cls[i] = RISING
    d = np.sign(np.asarray(c, np.float64) - np.asarray(o, np.float64))
    return cls, d.astype(np.int8), av, hi2
