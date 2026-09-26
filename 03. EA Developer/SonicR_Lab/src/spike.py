"""spike.py - A1G AUDIT RULE A: phantom-winner spike detector.

For every winning trade with a TP exit:
  neighbours = minute-aligned, non-E0'-voided M1 bars with timestamps
  in [exit_time - 5min, exit_time + 5min], exit bar excluded.
  jump = TP - max(neighbour highs)  for a long
       = min(neighbour lows) - TP   for a short
  (same price convention the sim uses for TP fills: raw bar high/low).
  Flag "spike" if jump > 5 * median(high-low) of that server day's
  minute-aligned non-voided bars.
  Fewer than 4 neighbours -> flag "gap".
Detection only - nothing is voided or gated by this.
"""
from __future__ import annotations

import numpy as np


def day_med_range(m1: dict, void: np.ndarray):
    """day_index -> median (h-l) over minute-aligned non-voided bars."""
    t = m1["t"]
    day = t // 86400
    ok = (~void) & (t % 60 == 0)
    rng = m1["h"] - m1["l"]
    days = np.unique(day[ok])
    med = {}
    for d in days:
        r = rng[ok & (day == d)]
        med[int(d)] = float(np.median(r)) if len(r) else np.nan
    return med


def spike_flag(m1: dict, void: np.ndarray, dr: int, px: float,
               exit_ctm: int, med_cache: dict | None = None):
    """-> dict(flag, reason, jump, n_neigh, med_rng).
    px = the executed exit price (== order TP for a normal fill, bar
    open for a gap-through). med_cache: optional dict from
    day_med_range(m1, void)."""
    t = m1["t"]
    ok = (~void) & (t % 60 == 0)
    win = ok & (t >= exit_ctm - 300) & (t <= exit_ctm + 300) & \
        (t != exit_ctm)
    idx = np.nonzero(win)[0]
    n = len(idx)
    if med_cache is None:
        med_cache = day_med_range(m1, void)
    day = int(exit_ctm // 86400)
    med = med_cache.get(day, np.nan)
    if n < 4:
        return {"flag": True, "reason": "gap", "jump": np.nan,
                "n_neigh": n, "med_rng": med}
    if dr == 1:
        jump = float(px - m1["h"][idx].max())
    else:
        jump = float(m1["l"][idx].min() - px)
    flag = bool(np.isfinite(med)) and jump > 5 * med
    return {"flag": flag, "reason": "spike" if flag else "",
            "jump": jump, "n_neigh": n, "med_rng": med}
