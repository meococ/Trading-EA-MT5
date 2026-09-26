"""Labeling + trade-path simulation on the data plane (fully vectorized).

Conventions mirror the governed tester:
- Signal bar t decides; ENTRY at OPEN of bar t+1 (next-bar-open fills).
- Path resolution uses M1 highs/lows; SL/TP checked intrabar, SL first on
  ambiguity (conservative, matches tester pessimism).
- Exit reasons: SL | TP | TIME.
- Returns are in PIPS relative to entry, side-normalized (+ = profit).
"""
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

_EXITS = np.array(["SL", "TP", "TIME"])
_BIG = 1 << 30
_CHUNK = 40000


SIM_VERSION = 4  # v4: per-event recorded-spread cost option (GATE B);
                 # v3: side-correct SL/TP fields (GATE A D1);
                 # v2: pip-unit fix


def spread_cost_arr(df, commission_p=0.7):
    """Per-bar round-trip cost in pips: recorded spread (points->pips)
    plus commission. Corrupt/insane `sp` values fall back to the
    symbol's sane median so corrupt records never zero the cost.
    Flat-proxy cost understates boundary windows by ~2x (GATE B kill
    of HYP-WOPEN-CHF-M1-001, 2026-09-19).

    Sane bound is garbage-signature based, NOT a fixed cap: exotics have
    real spreads of 200-2000pts (20-200p). Corrupt values observed are
    int64-garbage ~1e15. 2026-09-20: a fixed <200 bound silently imputed
    ~5p cost on EURZAR whose real median spread is ~107p -> phantom
    edges. Bound: sp in [0, 1e6)."""
    sp = df["sp"].to_numpy(dtype=float)
    sane = np.isfinite(sp) & (sp >= 0.0) & (sp < 1.0e6)
    med = float(np.median(sp[sane])) if sane.any() else 10.0
    return np.where(sane, sp, med) / 10.0 + commission_p


def _windows(arr, w, n, pad_val):
    """sliding windows of length w over arr, tail-padded with an inert value
    (h=-inf, l=+inf, sus=1) so phantom bars never trigger SL/TP and get
    dropped by the suspect-path rule instead of fabricating a path."""
    pad = np.empty(len(arr) + w, dtype=arr.dtype)
    pad[:len(arr)] = arr
    pad[len(arr):] = pad_val
    return sliding_window_view(pad, w)


class Evaluator:
    """Holds a symbol plane and caches sliding windows per max_hold so
    repeated eval_events calls over the same symbol stay cheap."""

    def __init__(self, df, pip):
        self.df = df
        self.pip = pip
        self.n = len(df)
        self.o = df["o"].to_numpy()
        self.c = df["c"].to_numpy()
        self.sus = df["suspect"].to_numpy()
        self.ctm = df.index.to_numpy()
        self._win = {}

    def windows(self, max_hold, drop_suspect_path=True):
        key = (max_hold, drop_suspect_path)
        if key not in self._win:
            w = max_hold + 1
            gap = np.zeros(self.n, dtype=np.int8)
            gap[:-1] = (np.diff(self.ctm) != 60).astype(np.int8)
            self._win[key] = (
                _windows(self.df["h"].to_numpy(), w, self.n, -np.inf),
                _windows(self.df["l"].to_numpy(), w, self.n, np.inf),
                _windows(self.sus.astype(np.int8), w, self.n, 1)
                if drop_suspect_path else None,
                _windows(gap, w, self.n, 1),
            )
        return self._win[key]

    def eval(self, mask, side, sl, tp, max_hold,
             drop_suspect_entry=True, drop_suspect_path=True, cost_rt=0.0,
             cost_arr=None):
        hw, lw, sw, gw = self.windows(max_hold, drop_suspect_path)
        return _eval(self.o, self.c, self.sus, self.ctm, self.n, hw, lw, sw,
                     gw, mask, side, sl, tp, max_hold, self.pip,
                     drop_suspect_entry, cost_rt, cost_arr)


def eval_events(df, mask, side, sl, tp, max_hold, pip,
                drop_suspect_entry=True, drop_suspect_path=True,
                cost_rt=0.0, cost_arr=None):
    """One-off eval (builds windows); for sweeps prefer Evaluator.eval."""
    ev = Evaluator(df, pip)
    return ev.eval(mask, side, sl, tp, max_hold,
                   drop_suspect_entry, drop_suspect_path, cost_rt, cost_arr)


def _eval(o, c, sus, ctm, n, hw, lw, sw, gw, mask, side, sl, tp, max_hold,
          pip, drop_suspect_entry, cost_rt, cost_arr):
    idx = np.flatnonzero(mask)
    w = max_hold + 1
    n_ev = len(idx)
    rets = np.empty(n_ev)
    exits = np.empty(n_ev, dtype=np.int8)
    maes = np.empty(n_ev)
    mfes = np.empty(n_ev)
    evt_ctm = np.empty(n_ev, dtype=np.int64)
    kept = 0
    dropped_entry = dropped_path = dropped_tail = 0
    n_gap_entry = n_gap_path = 0
    rng = np.arange(w)
    for s0 in range(0, n_ev, _CHUNK):
        ts = idx[s0:s0 + _CHUNK]
        i0 = ts + 1
        tail = i0 >= n
        i0c = np.minimum(i0, n - 1)
        gap_entry = (~tail) & ((ctm[i0c] - ctm[ts]) != 60)
        n_gap_entry += int(gap_entry.sum())
        # entry invalid if entry bar, signal bar suspect, or non-adjacent
        bad_entry = (~tail) & (sus[i0c] | sus[ts] | gap_entry) \
            if drop_suspect_entry else np.zeros(len(ts), dtype=bool)
        bad_path = np.zeros(len(ts), dtype=bool)
        if sw is not None:
            bad_path = (~tail) & (~bad_entry) & (sw[i0c].sum(axis=1) > 0)
        n_gap_path += int(((~tail) & (~bad_entry) & (~bad_path)
                           & (gw[i0c].sum(axis=1) > 0)).sum())
        dropped_tail += int(tail.sum())
        dropped_entry += int(bad_entry.sum())
        dropped_path += int(bad_path.sum())
        good = np.flatnonzero(~tail & ~bad_entry & ~bad_path)
        if len(good) == 0:
            continue
        gi0 = i0c[good]
        entry = o[gi0]
        # adverse/favorable excursions in pips, signed. For a short the
        # adverse field is the bar HIGH (wick-touch stop), not the low —
        # using lw here under-fired stops (GATE A defect D1, 2026-09-19).
        if side > 0:
            adv = (lw[gi0] - entry[:, None]) / pip   # low below entry = adverse
            fav = (hw[gi0] - entry[:, None]) / pip   # high above entry = favorable
        else:
            adv = (entry[:, None] - hw[gi0]) / pip   # high above entry = adverse
            fav = (entry[:, None] - lw[gi0]) / pip   # low below entry = favorable
        sl_hit = adv <= -sl
        tp_hit = (fav >= tp) if tp > 0 else np.zeros_like(sl_hit)
        i_sl = np.where(sl_hit.any(1), sl_hit.argmax(1), _BIG)
        i_tp = np.where(tp_hit.any(1), tp_hit.argmax(1), _BIG)
        is_sl = (i_sl <= i_tp) & (i_sl < _BIG)
        is_tp = (~is_sl) & (i_tp < _BIG)
        is_time = ~(is_sl | is_tp)
        jx = np.where(is_sl, i_sl, np.where(is_tp, i_tp, w - 1))
        r = np.where(is_sl, -sl, np.where(is_tp, float(tp), 0.0))
        if is_time.any():
            end_i = np.minimum(gi0 + max_hold, n - 1)
            r[is_time] = (c[end_i[is_time]] - entry[is_time]) * side / pip
        beyond = rng[None, :] > jx[:, None]
        adv_m = np.where(beyond, np.inf, adv)
        fav_m = np.where(beyond, -np.inf, fav)
        m = len(good)
        cost_i = cost_arr[gi0] if cost_arr is not None else cost_rt
        rets[kept:kept + m] = r - cost_i
        exits[kept:kept + m] = np.where(is_sl, 0, np.where(is_tp, 1, 2))
        maes[kept:kept + m] = adv_m.min(1)
        mfes[kept:kept + m] = fav_m.max(1)
        evt_ctm[kept:kept + m] = ctm[ts[good]]
        kept += m
    return {
        "ret": rets[:kept],
        "exit": _EXITS[exits[:kept]],
        "mae": maes[:kept],
        "mfe": mfes[:kept],
        "ctm": evt_ctm[:kept],
        "n_events": n_ev,
        "dropped_entry": dropped_entry,
        "dropped_path": dropped_path,
        "dropped_tail": dropped_tail,
        "n_gap_entry": n_gap_entry,
        "n_gap_path": n_gap_path,
        "sim_version": SIM_VERSION,
    }


def pf(returns):
    """Profit factor on per-trade returns (pips)."""
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 0:
        return np.inf if gains > 0 else np.nan
    return gains / losses
