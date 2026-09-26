"""Metrics through the real entry point: PF is None when the gross loss is 0."""

import numpy as np

import pa_data
import pa_eval

from conftest import synth_provider


def _market(spike_from=None, fall_from=None):
    start = 1546300800 + 2 * 3600               # 2019-01-01 02:00 server
    n = 300
    t = np.int64(start) + np.arange(n, dtype=np.int64) * 60
    o = np.full(n, 1.1000)
    h = np.full(n, 1.1000)
    l = np.full(n, 1.1000)
    c = np.full(n, 1.1000)
    h[0] = 1.1005
    l[0] = 1.0995                               # stop = 1.1006, SL/TP = +-8/16 pips
    o[5], h[5], l[5], c[5] = 1.1000, 1.1035, 1.1000, 1.1030
    o[6:], h[6:], l[6:], c[6:] = 1.1030, 1.1030, 1.1030, 1.1030
    if spike_from is not None:
        o[spike_from:], h[spike_from:], l[spike_from:], c[spike_from:] = \
            1.1030, 1.1032, 1.1026, 1.1029       # just runs the stop at 1.1031
    if fall_from is not None:
        o[fall_from:], h[fall_from:], l[fall_from:], c[fall_from:] = \
            1.0950, 1.0950, 1.0950, 1.0950       # runs the SL at 1.1023
    m1 = {"t": t, "o": o, "h": h, "l": l, "c": c,
          "pip": 1e-4, "symbol": "SYNX", "split": "DESIGN",
          "warmup": np.zeros(n, dtype=bool)}
    return m1, pa_data.resample(m1, "M5")


def _eval(entries_fn, m1, bars, family):
    d = synth_provider(m1, bars)
    spec = {"family": family, "entries_fn": entries_fn, "params": {"group": "t"},
            "legacy_flats": True}
    return pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["x1"], round_name="R00",
                            random_enabled=False,
                            data_provider=lambda sym, split, tf: d)


def test_pf_none_when_no_losses():
    m1, bars = _market()

    def entries_fn(symbol, bars_, spec):
        return [{"sig": 0, "side": +1, "tag": 0}]

    res = _eval(entries_fn, m1, bars, "PF_NULL")
    m = res["tiers"]["x1"]["strategy"]
    assert m["N"] == 1
    assert m["PF"] is None                  # never inf
    assert m["R_total"] == 2.0
    assert m["WR"] == 1.0
    assert m["b"] is None                   # no losing trade to define b
    assert m["max_dd_pct"] == 0.0


def test_pf_finite_when_losses_exist():
    m1, bars = _market(spike_from=105, fall_from=111)

    def entries_fn(symbol, bars_, spec):
        return [{"sig": 0, "side": +1, "tag": 0},    # wins at TP at M1 bar 5
                {"sig": 20, "side": +1, "tag": 1}]   # stop runs then SL loss

    res = _eval(entries_fn, m1, bars, "PF_FINITE")
    m = res["tiers"]["x1"]["strategy"]
    assert m["N"] == 2
    assert m["R_total"] == 1.0
    assert m["PF"] == 2.0
    assert m["WR"] == 0.5
