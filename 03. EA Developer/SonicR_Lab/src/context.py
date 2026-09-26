"""context.py - per-symbol precomputed causal context on M15 (or M5/H1).

Build once per symbol/window; every config then reads arrays only.
Nothing here uses future data: all series are causal by construction
(EMA/ATR trailing, swings by confirmation bar, zones by confirm<=t).
"""
from __future__ import annotations

import numpy as np

from . import data as data_mod
from .components import indicators as ind
from .components import pva as pva_mod
from .components import sessions as sess
from .components import swings as sw_mod
from .components import zones as zn
from .components import wave as wave_mod


class Ctx:
    def __init__(self, symbol: str, tf: dict, m1: dict):
        self.symbol = symbol
        self.tf = tf
        self.m1 = m1
        d = tf
        self.dh, self.dm, self.dl = ind.dragon(d)
        self.ema89 = ind.trend(d)
        self.atr = ind.atr_wilder(d["h"], d["l"], d["c"], 14)
        self.angle5 = ind.dragon_angle_atr(self.dm, self.atr, 5)
        self.pva_cls, self.pva_dir, self.pva_av, self.pva_hi2 = \
            pva_mod.pva_class(d["h"], d["l"], d["c"], d["o"], d["tv"])
        self.frac = sw_mod.fractal2(d["h"], d["l"])
        self.zig = sw_mod.atr_zigzag(d["h"], d["l"], d["c"], self.atr, 1.5)
        self.hour, self.dow, self.ymd = data_mod.london_parts(d["t"])
        self.in_london_j = sess.in_window(d["t"], "london_j")
        self.in_london_ext = sess.in_window(d["t"], "london_ext")
        self.in_ny_overlap = sess.in_window(d["t"], "ny_overlap")
        self.zones_engine = zn.SwingZones(self.zig, d["h"], d["l"], d["c"],
                                        self.atr)
        self.n = len(d["t"])
        # J-side trend mask + dragon slope (16/08: mid >= mid-3)
        self.long_side = d["c"] > self.ema89
        self.short_side = d["c"] < self.ema89
        self.dragon_up = np.zeros(self.n, bool)
        self.dragon_dn = np.zeros(self.n, bool)
        self.dragon_up[3:] = self.dm[3:] >= self.dm[:-3]
        self.dragon_dn[3:] = self.dm[3:] <= self.dm[:-3]
        self._wave_cache: dict = {}

    def wave_shape(self, t: int, sw: dict, lookback: int = 40):
        return wave_mod.wave_shape_at(
            t, sw, self.dl, self.dh, self.tf["l"], self.tf["h"],
            self.tf["c"], lookback)

    def wave(self, t: int, sw: dict, lookback: int = 40):
        key = (t, id(sw), lookback)
        if key not in self._wave_cache:
            self._wave_cache[key] = wave_mod.wave_at(
                t, sw, self.dl, self.dh, self.tf["o"], self.tf["h"],
                self.tf["l"], self.tf["c"], lookback)
        return self._wave_cache[key]

    def zones_at(self, t: int):
        return self.zones_engine.zones_at(t)

    def reset_zones(self):
        self.zones_engine = zn.SwingZones(self.zig, self.tf["h"],
                                        self.tf["l"], self.tf["c"],
                                        self.atr)


def build(symbol: str, lo_ctm: int, hi_ctm: int, minutes: int = 15,
          pre_ctm: int | None = None, allow_holdout: bool = False,
          pre2010: bool = False) -> Ctx:
    """Load M1 (optionally extended with pre-2010 .hcc for parity),
    resample to `minutes`, return Ctx. Warm-up: `pre_ctm` includes earlier
    bars for indicator/swing warm-up (still all causal)."""
    m1a = data_mod.load_m1(symbol, lo_ctm if pre_ctm is None else
                           min(pre_ctm, lo_ctm), hi_ctm,
                           allow_holdout=allow_holdout)
    if pre2010:
        m1b = data_mod.load_m1_pre2010(symbol, data_mod.J_PARITY[0],
                                     m1a["t"][0] - 60,
                                     allow_holdout=allow_holdout)
        m1 = {k: np.concatenate((m1b[k], m1a[k])) for k in m1a}
    else:
        m1 = m1a
    tf = data_mod.resample(m1, minutes)
    return Ctx(symbol, tf, m1)
