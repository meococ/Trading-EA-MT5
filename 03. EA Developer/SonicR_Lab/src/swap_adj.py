"""swap_adj.py - 2G swap adjustment (post-processing, NOT in the sim).

Per-night swap in price units, read by the Lead off MT5 on 24/09
(swap_mode = points; values are negative = cost to the position):
  XAUUSD long -0.126 USD/oz, short -0.046 USD/oz
  EURUSD long -0.0000070,      short -0.0000100
nights = server-day rollovers crossed between fill and exit
(Wednesday counts 3) - same counting as validation_2f._n_rolls.
  R_adj = R + swap_per_night * nights / |entry - SL|
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import sim as sm

SWAP_PER_NIGHT = {
    "XAUUSD": {1: -0.126, -1: -0.046},
    "EURUSD": {1: -0.0000070, -1: -0.0000100},
}


def n_rolls(fill_ctm, exit_ctm, sym_arr):
    """Rollovers crossed in (fill, exit] at the symbol's ROLL start
    (server-day boundary), Wednesday roll counts triple.

    NOTE: validation_2f._n_rolls has a latent bug (anchor0 uses
    seconds*86400, so its Wednesday +2 never fires). This version is
    correct - a position crossing only the Wed roll gets nights=3.
    Epoch day 0 = Thursday -> Wednesday = day_index % 7 == 6."""
    f = np.asarray(fill_ctm); e = np.asarray(exit_ctm)
    out = np.zeros(len(f), dtype=int)
    for sym in np.unique(sym_arr):
        m = sym_arr == sym
        phase = sm.ROLL[sym][0][0] * 60
        k0 = np.floor((f[m] - phase) / 86400).astype(int) + 1
        k1 = np.floor((e[m] - phase) / 86400).astype(int)
        idx = np.nonzero(m)[0]
        for ii, i in enumerate(np.nonzero(k1 >= k0)[0]):
            days = np.arange(k0[i], k1[i] + 1)
            out[idx[i]] = len(days) + 2 * int((days % 7 == 6).sum())
    return out


def swap_adj_r(df: pd.DataFrame, mult: float = 1.0,
               rcol: str = "r_x1") -> pd.Series:
    """R after per-night swap (mult=2.0 for the G2 stress; rcol=r_x15
    for the costs-x1.5 version)."""
    rolls = n_rolls(df["fill_ctm"].to_numpy(),
                    df["exit_ctm"].to_numpy(),
                    df["sym"].to_numpy())
    per = np.array([SWAP_PER_NIGHT.get(s, {}).get(int(d), 0.0)
                    for s, d in zip(df["sym"], df["dir"])])
    return df[rcol] + mult * (rolls * per) / df["risk_px"]
