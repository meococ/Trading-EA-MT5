"""wave.py - Classic wave parser (object J parity + variant hooks).

16/08 semantics (SNR_Signal.mqh, packet section 6):
  scan back from decision bar t over confirmed swings (detector-dependent):
    leg2 = most recent swing in the pullback direction
           (long: swing LOW, short: swing HIGH)
    leg1 = most recent opposite swing before leg2
    leg0 = most recent same-direction swing before leg1
  long valid:  low[leg2] > low[leg0]            (higher low)
               low[leg0] < dragon_low[leg0]     (origin below Dragon)
               no prior break: close[k] <= d_high[k] for leg2<k<t
  trigger:     close[t] > d_high[t] AND close[t] > open[t]   (long)
  short is the mirror.

Flags (telemetry unless a config gates them):
  thru_dragon (W3): leg-1 leg pierced the Dragon band:
      high[leg0] > d_high[leg0] or low[leg1] < d_low[leg1]   (long)
  at_sr (W2):     leg-0 extreme within a live zone / WHQ band.
"""
from __future__ import annotations

import numpy as np


def _scan_wave_long(t, sw, d_lo, d_hi, low, high, close, lookback):
    """Return dict(leg0,leg1,leg2,prior_break,thru) or None. `sw` = swing
    dict; only swings with conf<=t are visible."""
    conf_ok = sw["conf"] <= t
    low_pos = np.nonzero(conf_ok & (sw["dir"] == -1)
                         & (sw["idx"] >= t - lookback))[0]
    if len(low_pos) == 0:
        return None
    p2 = int(low_pos[-1]); i2 = int(sw["idx"][p2])
    high_pos = np.nonzero(conf_ok & (sw["dir"] == 1)
                          & (sw["idx"] < i2))[0]
    if len(high_pos) == 0:
        return None
    p1 = int(high_pos[-1]); i1 = int(sw["idx"][p1])
    low_pos0 = np.nonzero(conf_ok & (sw["dir"] == -1)
                          & (sw["idx"] < i1))[0]
    if len(low_pos0) == 0:
        return None
    p0 = int(low_pos0[-1]); i0 = int(sw["idx"][p0])
    if not (low[i2] > low[i0]):            # higher low required
        return None
    if not (low[i0] < d_lo[i0]):           # origin below the band
        return None
    prior = bool(np.any(close[i2 + 1:t] > d_hi[i2 + 1:t])) if i2 + 1 < t \
        else False
    thru = bool(high[i0] > d_hi[i0] or low[i1] < d_lo[i1])
    return {"leg0": i0, "leg1": i1, "leg2": i2, "dir": 1,
            "prior_break": prior, "thru": thru}


def _scan_wave_short(t, sw, d_lo, d_hi, low, high, close, lookback):
    conf_ok = sw["conf"] <= t
    high_pos = np.nonzero(conf_ok & (sw["dir"] == 1)
                          & (sw["idx"] >= t - lookback))[0]
    if len(high_pos) == 0:
        return None
    p2 = int(high_pos[-1]); i2 = int(sw["idx"][p2])
    low_pos = np.nonzero(conf_ok & (sw["dir"] == -1)
                         & (sw["idx"] < i2))[0]
    if len(low_pos) == 0:
        return None
    p1 = int(low_pos[-1]); i1 = int(sw["idx"][p1])
    high_pos0 = np.nonzero(conf_ok & (sw["dir"] == 1)
                           & (sw["idx"] < i1))[0]
    if len(high_pos0) == 0:
        return None
    p0 = int(high_pos0[-1]); i0 = int(sw["idx"][p0])
    if not (high[i2] < high[i0]):          # lower high required
        return None
    if not (high[i0] > d_hi[i0]):          # origin above the band
        return None
    prior = bool(np.any(close[i2 + 1:t] < d_lo[i2 + 1:t])) if i2 + 1 < t \
        else False
    thru = bool(low[i0] < d_lo[i0] or high[i1] > d_hi[i1])
    return {"leg0": i0, "leg1": i1, "leg2": i2, "dir": -1,
            "prior_break": prior, "thru": thru}


def wave_at(t: int, sw: dict, d_lo: np.ndarray, d_hi: np.ndarray,
            o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
            lookback: int = 40):
    """Full J wave+trigger at decision bar t. Returns dict with
    dir/leg0/leg1/leg2/thru or None."""
    w = _scan_wave_long(t, sw, d_lo, d_hi, l, h, c, lookback)
    if w and not w["prior_break"] and c[t] > d_hi[t] and c[t] > o[t]:
        return w
    w = _scan_wave_short(t, sw, d_lo, d_hi, l, h, c, lookback)
    if w and not w["prior_break"] and c[t] < d_lo[t] and c[t] < o[t]:
        return w
    return None


def wave_shape_at(t: int, sw: dict, d_lo: np.ndarray, d_hi: np.ndarray,
                  l: np.ndarray, h: np.ndarray, c: np.ndarray,
                  lookback: int = 40):
    """Wave shape only (no trigger check) - for census decomposition."""
    out = []
    w = _scan_wave_long(t, sw, d_lo, d_hi, l, h, c, lookback)
    if w and not w["prior_break"]:
        out.append(w)
    w = _scan_wave_short(t, sw, d_lo, d_hi, l, h, c, lookback)
    if w and not w["prior_break"]:
        out.append(w)
    return out


class WaveTracker:
    """Incremental O(log n) wave scanner for the generator loop.

    Precomputes per-direction swing lists sorted by confirmation bar
    (which coincides with bar-index order for both detectors here:
    fractal conf=idx+2; zigzag emits swings in idx order).
    Caller iterates t in ASCENDING order; usable counts advance by
    searchsorted on conf.
    """

    def __init__(self, sw: dict):
        self.sw = sw
        m_lo = sw["dir"] == -1
        m_hi = sw["dir"] == 1
        for name, m in (("lo", m_lo), ("hi", m_hi)):
            idx = sw["idx"][m]; cf = sw["conf"][m]; px = sw["px"][m]
            order = np.argsort(cf, kind="stable")
            setattr(self, f"{name}_idx", idx[order])
            setattr(self, f"{name}_conf", cf[order])
            setattr(self, f"{name}_px", px[order])

    def _shape(self, t: int, dr: int, d_lo, d_hi, l, h, c, lookback):
        sw = self
        if dr == 1:
            a_idx, a_conf = sw.lo_idx, sw.lo_conf   # leg2: swing low
            b_idx, b_conf = sw.hi_idx, sw.hi_conf   # leg1: swing high
        else:
            a_idx, a_conf = sw.hi_idx, sw.hi_conf
            b_idx, b_conf = sw.lo_idx, sw.lo_conf
        n_a = int(np.searchsorted(a_conf, t, side="right"))
        n_b = int(np.searchsorted(b_conf, t, side="right"))
        # leg2 = last usable swing of type-a with idx >= t-lookback
        pos2 = int(np.searchsorted(a_idx[:n_a], t, side="right")) - 1
        if pos2 < 0:
            return None
        i2 = int(a_idx[pos2])
        if i2 < t - lookback:
            return None
        pos1 = int(np.searchsorted(b_idx[:n_b], i2, side="left")) - 1
        if pos1 < 0:
            return None
        i1 = int(b_idx[pos1])
        pos0 = int(np.searchsorted(a_idx[:n_a], i1, side="left")) - 1
        if pos0 < 0:
            return None
        i0 = int(a_idx[pos0])
        if dr == 1:
            if not (l[i2] > l[i0]):
                return None
            if not (l[i0] < d_lo[i0]):
                return None
            prior = bool(np.any(c[i2 + 1:t] > d_hi[i2 + 1:t])) \
                if i2 + 1 < t else False
            thru = bool(h[i0] > d_hi[i0] or l[i1] < d_lo[i1])
        else:
            if not (h[i2] < h[i0]):
                return None
            if not (h[i0] > d_hi[i0]):
                return None
            prior = bool(np.any(c[i2 + 1:t] < d_lo[i2 + 1:t])) \
                if i2 + 1 < t else False
            thru = bool(l[i0] < d_lo[i0] or h[i1] > d_hi[i1])
        return {"leg0": i0, "leg1": i1, "leg2": i2, "dir": dr,
                "prior_break": prior, "thru": thru}

    def shape(self, t: int, dr: int, d_lo, d_hi, l, h, c, lookback=40):
        """Wave shape for direction dr at bar t, or None."""
        return self._shape(t, dr, d_lo, d_hi, l, h, c, lookback)

    def shapes(self, t: int, d_lo, d_hi, l, h, c, lookback=40):
        out = []
        for dr in (1, -1):
            w = self._shape(t, dr, d_lo, d_hi, l, h, c, lookback)
            if w and not w["prior_break"]:
                out.append(w)
        return out
