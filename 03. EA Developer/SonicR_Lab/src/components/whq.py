"""whq.py - TAH Access Panel WHQ grid, code-exact (INDICATORS.md §4, S9/S15).

pip = Point*10. Levels 00/25/50/75 per 100-pip span:
  EURUSD (5-digit): pip=1e-4 -> quarter step 0.0025, half 0.005, whole 0.01
  XAUUSD (2-digit): pip=0.1  -> quarter 2.5, half 5, whole 10

NOTE: the old EA file SNR_SRLevels.mqh draws a WRONG 10/5/2.5-pip grid on
EURUSD. This module implements the canonical TAH spacing. Do not copy the
EA grid.
"""
from __future__ import annotations

import numpy as np

WHOLE, HALF, QUARTER = 2, 1, 0  # importance rank


def pip_size(symbol: str) -> float:
    from .. import data as _dm          # single source of truth
    return _dm.PIP[symbol]


def level_kind(price: float, symbol: str, tol: float = 1e-9) -> int | None:
    """Return WHOLE/HALF/QUARTER if price sits on a grid line, else None.
    tol in price units (use ~0.2 point for float noise)."""
    pip = pip_size(symbol)
    q = 25.0 * pip
    k = price / q
    if abs(k - round(k)) * q > tol:
        return None
    idx = int(round(k)) % 4
    return {0: WHOLE, 2: HALF, 1: QUARTER, 3: QUARTER}[idx]


def levels_between(lo: float, hi: float, symbol: str,
                   min_rank: int = QUARTER) -> list:
    """All grid levels in [lo,hi] with rank >= min_rank."""
    pip = pip_size(symbol)
    q = 25.0 * pip
    k0 = int(np.ceil(lo / q - 1e-9))
    k1 = int(np.floor(hi / q + 1e-9))
    out = []
    for k in range(k0, k1 + 1):
        p = k * q
        r = {0: WHOLE, 2: HALF, 1: QUARTER, 3: QUARTER}[k % 4]
        if r >= min_rank:
            out.append((p, r))
    return out


def next_whq(price: float, symbol: str, direction: int,
             min_rank: int = HALF) -> float | None:
    """First grid level strictly beyond `price` in `direction` (+1 up/-1 dn)
    with rank >= min_rank. None if none within +/-500 whole levels."""
    pip = pip_size(symbol)
    q = 25.0 * pip
    step = 1 if direction > 0 else -1
    k = int(np.floor(price / q + 1e-9)) if direction > 0 else \
        int(np.ceil(price / q - 1e-9))
    for i in range(1, 4 * 500):
        kk = k + step * i
        p = kk * q
        if direction > 0 and p <= price + 1e-12:
            continue
        if direction < 0 and p >= price - 1e-12:
            continue
        r = {0: WHOLE, 2: HALF, 1: QUARTER, 3: QUARTER}[kk % 4]
        if r >= min_rank:
            return p
    return None


def j_whq_target(entry: float, symbol: str, direction: int,
                 min_dist_pips: float) -> float | None:
    """16/08 spec TP helper (SNR_SRLevels parity): first 50-pip-step level
    (whole OR half) at least min_dist_pips beyond entry. Matches the J run
    where the grid step used for targets was the half-level spacing."""
    p = next_whq(entry, symbol, direction, min_rank=HALF)
    pip = pip_size(symbol)
    if p is not None and abs(p - entry) >= min_dist_pips * pip - 1e-12:
        return p
    return None
