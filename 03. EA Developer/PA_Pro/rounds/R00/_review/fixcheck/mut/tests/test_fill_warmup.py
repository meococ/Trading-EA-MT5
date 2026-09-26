"""E2 gap (R00 review): the fill engine refuses warm-up signal bars.

Charter section 3: warm-up bars (before the split start) must never produce
signals or outcomes.  ``first_live_idx`` is the first TF bar that is NOT
warm-up; an entry at or after it is legal, an entry before it is refused.
"""

import numpy as np
import pytest

import pa_data
import pa_fill


def _flat_m1(n_bars_m5=12):
    start = int(1546300800) + 2 * 3600          # 2019-01-01 02:00 server
    n = n_bars_m5 * 5
    t = np.int64(start) + np.arange(n, dtype=np.int64) * 60
    c = np.full(n, 1.1000, dtype=np.float64)
    return {"t": t, "o": c.copy(), "h": c.copy(), "l": c.copy(), "c": c.copy(),
            "pip": 1e-4, "symbol": "SYNX", "split": "DESIGN",
            "warmup": np.zeros(n, dtype=bool)}


def _ctx(m1, bars, first_live_idx):
    starts = np.searchsorted(m1["t"], bars["t"], side="left")
    return pa_fill.build_ctx(m1, bars, bars["t"], starts, m1["pip"],
                             symbol="SYNX", c_rt_pips=1.0,
                             first_live_idx=first_live_idx)


def test_warmup_signal_is_refused_and_first_live_is_legal():
    m1 = _flat_m1()
    bars = pa_data.resample(m1, "M5")
    ctx = _ctx(m1, bars, first_live_idx=5)
    spec = pa_fill.resolve_spec({"legacy_flats": False})

    with pytest.raises(ValueError, match="warm-up"):
        pa_fill.simulate(spec, ctx, [{"sig": 4, "side": 1, "tag": "warm"}], "gross")
    with pytest.raises(ValueError, match="warm-up"):
        pa_fill.simulate(spec, ctx, [{"sig": 0, "side": -1, "tag": "warm"}], "gross")

    # the first live bar itself is legal; the guard is `sig < first_live`
    tr = pa_fill.simulate(spec, ctx, [{"sig": 5, "side": 1, "tag": "live"}], "gross")
    assert len(tr) == 1
    assert tr[0]["status"] in ("FILLED", "CANCELLED", "EXPIRED")
