"""sessions.py - session windows on London wall time (DST-aware).

Broker timezone: MQ-Demo server = UTC+2/+3 following US DST (verified in
DATA.md). All session logic converts server ctm -> London wall clock via
data.server_to_london; no hand-rolled offsets elsewhere.

Windows (hour in [h0,h1), London):
  J / Classic London : 08:00-16:00  (packet section 6, SnrSessionRead)
  extended London    : 07:00-16:00  (Lead brief Phase B)
  NY overlap         : 12:00-16:00  (F3 Lucy spec)
"""
from __future__ import annotations

import numpy as np

from .. import data as data_mod

WINDOWS = {
    "london_j": (8, 16),
    "london_ext": (7, 16),
    "ny_overlap": (12, 16),
}


def in_window(ctm: np.ndarray, name: str) -> np.ndarray:
    """Boolean: bar-open London time inside the named window, Mon-Fri."""
    h0, h1 = WINDOWS[name]
    hour, dow, _ = data_mod.london_parts(np.asarray(ctm))
    return (dow < 5) & (hour >= h0) & (hour < h1)


def friday_flatten_ctm(ctm: np.ndarray) -> np.ndarray:
    """For each ctm, the server-naive epoch of that day's Friday-flatten
    moment (Friday 20:00 London). Used to force-close positions before the
    weekend (GOAL: no weekend hold)."""
    lon = data_mod.server_to_london(np.asarray(ctm))
    days = lon // 86400
    dow = (days + 3) % 7            # Mon=0..Sun=6 (epoch day0 = Thu)
    # London epoch of Friday 20:00 for each bar's week
    fri_day = days + ((4 - dow) % 7)
    flat_lon = fri_day * 86400 + 20 * 3600
    # London -> UTC -> server naive (inverse: utc = lon - uk_off)
    utc = flat_lon - data_mod.uk_offset_hours(flat_lon) * 3600
    server = utc + data_mod.server_offset_hours(utc) * 3600
    return server
