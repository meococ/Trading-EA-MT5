"""Future-mutation canary (REVIEW_2 F5).

Mutating bars AFTER time t must not change:
  - the grid/placebo level envelopes for the day containing t
    (grid_columns, placebo_grid_levels);
  - detection-time event features at bars <= t (detect_touches).

The pre-fix envelope code (nanmedian(abr) over the whole day) is
replicated inline as legacy_day_abr and shown to move the level set
under a future mutation — old code fails, new code passes.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mk_common as K                       # noqa: E402
from mk_m3_levels import grid_columns, detect_touches  # noqa: E402

BASE = 1672531200
PIP = 1e-4


def synth_bars(n=700, seed=0):
    """3+ days of M5 bars, deterministic."""
    rng = np.random.default_rng(seed)
    t = BASE + 300 * np.arange(n)
    c = 1.1000 + np.cumsum(rng.normal(0, 15e-5, n))
    o = np.concatenate(([c[0]], c[:-1]))
    rng_w = np.abs(rng.normal(0, 8e-5, n)) + 4e-5
    h = np.maximum(o, c) + rng_w
    l = np.minimum(o, c) - rng_w
    dow = ((t // 86400) + 3) % 7
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "pip": PIP,
            "dow": dow.astype(np.int64),
            "utc_min": ((t % 86400) // 60).astype(np.int64),
            "warmup": np.zeros(n, bool), "tf": "M5"}


def synth_abr(bars, seed=1):
    rng = np.random.default_rng(seed)
    return np.full(len(bars["t"]), 25e-4) * \
        (1.0 + 0.1 * rng.normal(0, 1, len(bars["t"])))


def _col_prices(cols):
    return [np.unique(c["price"][np.isfinite(c["price"])])
            for c in cols]


def legacy_day_abr(abr, m):
    """Pre-fix: full-day median ABR (uses future bars)."""
    return float(np.nanmedian(abr[m]))


def test_grid_envelope_ignores_future_abr():
    bars = synth_bars()
    abr = synth_abr(bars)
    day = K.day_id(bars)
    d1 = sorted(np.unique(day))[1]          # second day (full day)
    m = day == d1
    idx = np.flatnonzero(m)
    i0, i1 = int(idx[0]), int(idx[-1])
    abr_mut = abr.copy()
    abr_mut[i0 + 5:i1 + 1] *= 8.0            # huge future vol, same day
    cols_a = grid_columns(bars, abr, off_pips=0.0)
    cols_b = grid_columns(bars, abr_mut, off_pips=0.0)
    assert len(cols_a) == len(cols_b)
    for x, y in zip(cols_a, cols_b):
        assert np.array_equal(x["price"][m], y["price"][m],
                              equal_nan=True), \
            "grid levels moved under a future-ABR mutation (F5)"
    # legacy sizing demonstrably moves
    assert not np.isclose(legacy_day_abr(abr, m),
                          float(abr[i0])), "fixture cannot distinguish"
    lev_lo_fixed = bars["o"][i0] - 3.5 * float(abr[i0])
    lev_lo_leg = bars["o"][i0] - 3.5 * legacy_day_abr(abr_mut, m)
    assert lev_lo_fixed != lev_lo_leg


def test_placebo_grid_levels_ignores_future_abr():
    bars = synth_bars()
    abr = synth_abr(bars)
    day = K.day_id(bars)
    d1 = sorted(np.unique(day))[1]
    idx = np.flatnonzero(day == d1)
    i0, i1 = int(idx[0]), int(idx[-1])
    abr_mut = abr.copy()
    abr_mut[i0 + 5:i1 + 1] *= 8.0            # mutate only inside day d1
    a = K.placebo_grid_levels(bars, abr, 8, 3.5, seed=K.SEED)
    b = K.placebo_grid_levels(bars, abr_mut, 8, 3.5, seed=K.SEED)
    assert a.keys() == b.keys()
    for d in a:
        pa = [p for p, _ in a[d]]
        pb = [p for p, _ in b[d]]
        assert np.allclose(pa, pb), f"placebo levels moved on day {d}"


def test_detect_touches_features_causal():
    """Event features at bars <= T0 identical after mutating all bars
    strictly after T0 (post-T0 events may differ; they are not compared)."""
    bars = synth_bars(n=400, seed=3)
    abr = synth_abr(bars, seed=4)
    tol = K.tol_array(abr, PIP)
    # one fixed level column near the price path
    price = np.full(len(bars["t"]), np.nan)
    price[:] = 1.1000
    col = {"price": price,
           "birth": np.zeros(len(price), np.int64),
           "lid": np.ones(len(price), np.int64),
           "kind": np.zeros(len(price), np.int64)}
    ev_a = detect_touches(bars, col, abr, tol)
    T0 = 250
    mut = {k: (v.copy() if isinstance(v, np.ndarray) else v)
           for k, v in bars.items()}
    rng = np.random.default_rng(9)
    for f in ("o", "h", "l", "c"):
        mut[f][T0 + 1:] = 1.3000 + rng.normal(0, 50e-5,
                                              len(bars["t"]) - T0 - 1)
    ev_b = detect_touches(mut, col, abr, tol)
    fa = [(e["bar"], e["side"], round(e["level"], 6),
           round(e["approach_atr"], 8), e["lid"], e["age_bars"])
          for e in ev_a if e["bar"] <= T0]
    fb = [(e["bar"], e["side"], round(e["level"], 6),
           round(e["approach_atr"], 8), e["lid"], e["age_bars"])
          for e in ev_b if e["bar"] <= T0]
    assert fa == fb, "detection-time features changed under future bars"


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("test_lookahead: all pass")
