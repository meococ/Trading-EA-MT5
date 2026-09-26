"""stops_targets.py - SL/TP rules (Phase B spec).

SL variants:
  (a) wave leg-0 extreme -/+ 0.1*ATR14           (16/08 rule)
  (b) most significant swing of last 48 bars: the endpoint of the largest
      ATR-zigzag leg, -/+ 0.1*ATR14
Cap: EURUSD 120 pips. XAUUSD cap = same multiple of median daily range as
120 pips is for EURUSD, computed on DESIGN only (PREREG pins the number).
If SL > cap -> no trade (never shrink).

TP variants:
  (a) nearest opposing swing-zone edge at >= 1R
  (b) next WHQ whole/half level at >= 1R
If no target >= 1R -> no trade.

J-parity TP (16/08 exact): first WHQ half-step level >= 15 pips beyond
entry; fallback 1.5R when none within the cap lookahead.
"""
from __future__ import annotations

import numpy as np

from . import whq as whq_mod


def sl_leg0(wave: dict, d: dict, t: int, atr: np.ndarray,
            buf_atr: float = 0.1) -> float:
    """SL(a): beyond leg-0 extreme + buf. Long uses leg0 LOW, short HIGH."""
    i0 = wave["leg0"]
    a = atr[t]
    if wave["dir"] == 1:
        return d["l"][i0] - buf_atr * a
    return d["h"][i0] + buf_atr * a


def sl_big_swing(d: dict, t: int, atr: np.ndarray, zig: dict,
                 direction: int, pending_px: float, lookback: int = 48,
                 buf_atr: float = 0.1) -> float | None:
    """SL(b): beyond the most significant confirmed zigzag extreme of the
    last `lookback` bars on the protective side AND strictly beyond the
    pending price (long: extreme < pending_px; short: > pending_px).
    'Significant' = endpoint of the largest zigzag leg measured in ATR
    units at that leg. None when no qualifying extreme exists (no trade).
    Review fix R2 (LEAD errata 1c): the strict-side filter is the root
    cause fix for wrong-side SL orders; sim's E2 guard is the backstop."""
    ok = np.nonzero((zig["conf"] <= t) & (zig["idx"] >= t - lookback)
                    & (zig["dir"] == (-1 if direction > 0 else 1)))[0]
    if len(ok):
        if direction > 0:
            ok = ok[zig["px"][ok] < pending_px]
        else:
            ok = ok[zig["px"][ok] > pending_px]
    if len(ok) == 0:
        return None
    # largest leg = max |px - previous confirmed swing px| / atr at idx
    best, best_score = None, -1.0
    for k in ok:
        prev = zig["px"][k - 1] if k > 0 else zig["px"][k]
        a = atr[int(zig["idx"][k])]
        if not np.isfinite(a) or a <= 0:
            continue
        score = abs(zig["px"][k] - prev) / a
        if score > best_score:
            best_score, best = score, k
    if best is None:
        return None
    a = atr[t]
    if direction > 0:
        return float(zig["px"][best]) - buf_atr * a
    return float(zig["px"][best]) + buf_atr * a


def tp_zone(entry: float, sl: float, direction: int, zones: list) \
        -> float | None:
    """TP(a): nearest opposing zone's near edge >= 1R beyond entry."""
    r = abs(entry - sl)
    if r <= 0:
        return None
    cands = []
    for z in zones:
        if direction > 0 and z["dir"] == 1:
            edge = z["lo"]
            if edge - entry >= r:
                cands.append(edge)
        elif direction < 0 and z["dir"] == -1:
            edge = z["hi"]
            if entry - edge >= r:
                cands.append(edge)
    if not cands:
        return None
    return min(cands) if direction > 0 else max(cands)


def tp_whq(entry: float, sl: float, direction: int,
           symbol: str) -> float | None:
    """TP(b): next WHQ whole/half level at >= 1R."""
    r = abs(entry - sl)
    if r <= 0:
        return None
    p = whq_mod.next_whq(entry, symbol, direction, min_rank=whq_mod.HALF)
    if p is None:
        return None
    if direction > 0 and p - entry >= r:
        return p
    if direction < 0 and entry - p >= r:
        return p
    return None


def tp_j(entry: float, sl: float, direction: int, symbol: str,
         min_pips: float = 15.0, r_fallback: float = 1.5) -> float | None:
    """16/08 TP: first WHQ half-step level >= min_pips beyond entry;
    fallback = entry + r_fallback*R when no level qualifies."""
    p = whq_mod.j_whq_target(entry, symbol, direction, min_pips)
    r = abs(entry - sl)
    if p is not None:
        return p
    if r > 0:
        return entry + direction * r_fallback * r
    return None


def median_daily_range_pips(d15: dict, lo_ctm: int, hi_ctm: int,
                            symbol: str) -> float:
    """Median (high-low) of completed London days within [lo,hi] ctm,
    expressed in pips. DESIGN-only input for the XAU cap rule."""
    from .. import data as data_mod
    hour, dow, ymd = data_mod.london_parts(d15["t"])
    mask = (d15["t"] >= lo_ctm) & (d15["t"] < hi_ctm) & (dow < 5)
    idx = np.nonzero(mask)[0]
    if len(idx) == 0:
        return float("nan")
    days = np.unique(ymd[idx])
    rng = []
    pip = whq_mod.pip_size(symbol)
    for day in days:
        sel = idx[ymd[idx] == day]
        rng.append((d15["h"][sel].max() - d15["l"][sel].min()) / pip)
    return float(np.median(rng))
