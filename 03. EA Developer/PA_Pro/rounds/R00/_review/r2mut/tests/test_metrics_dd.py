"""E2 gap (R00 review): the frozen equity / drawdown formula is locked.

Definition (pa_metrics docstring, frozen with ECON-1): 0.5% risk per trade on
the running equity, chronological by EXIT time (stable): ``eq *=
(1 + 0.005 * r)``; ``max_dd`` = largest peak-to-trough on that curve.

The market below produces exactly r = [-1, +2, -1, -1, +2] in exit order, so
the expected max DD can be hand-computed and asserted to 1e-12, and the
compounded formula can be discriminated from a linear (additive) one.
"""

import numpy as np
import pytest

import pa_data
import pa_eval

from conftest import synth_provider

R_SEQ = (-1.0, 2.0, -1.0, -1.0, 2.0)            # chronological by exit time


def _market_5_trades():
    start = 1546308000                          # 2019-01-01 02:00 server
    n = 300
    t = np.int64(start) + np.arange(n, dtype=np.int64) * 60
    o = np.full(n, 1.1000, dtype=np.float64)
    h = np.full(n, 1.1000, dtype=np.float64)
    l = np.full(n, 1.1000, dtype=np.float64)
    c = np.full(n, 1.1000, dtype=np.float64)
    # (signal M5 bar, outcome); stop = signal-bar high + 1 pip = 1.1006,
    # x1 fill = 1.1010 + 1 pip, SL = 1.1003, TP = 1.1027.  The trigger sits in
    # the NEXT M5 bucket so it cannot raise the signal bar's own high.
    for sig5, kind in ((0, "loss"), (12, "win"), (24, "loss"),
                       (36, "loss"), (48, "win")):
        i = sig5 * 5
        h[i] = 1.1005
        l[i] = 1.0995
        j = i + 5                              # first M1 bar after the signal bar
        o[j] = 1.1010
        h[j] = 1.1010
        c[j] = 1.1010
        if kind == "loss":
            l[j] = 1.1000                      # SL 1.1003 on the fill bar -> -1
        else:
            l[j] = 1.1004                      # fill bar holds
            o[j + 1] = 1.1010
            h[j + 1] = 1.1030
            l[j + 1] = 1.1010
            c[j + 1] = 1.1030                  # TP 1.1027 -> +2
    m1 = {"t": t, "o": o, "h": h, "l": l, "c": c, "pip": 1e-4,
          "symbol": "SYNX", "split": "DESIGN", "warmup": np.zeros(n, dtype=bool)}
    return m1, pa_data.resample(m1, "M5")


def _evaluate(entries):
    m1, bars = _market_5_trades()
    d = synth_provider(m1, bars)
    spec = {"family": "DD_FORMULA", "entries_fn": lambda s, b, sp: entries,
            "params": {"group": "dd"}, "legacy_flats": True}
    return pa_eval.evaluate(spec, "DESIGN", ["SYNX"], "M5", ["x1"],
                            round_name="R00", random_enabled=False,
                            data_provider=lambda sym, split, tf: d)


def test_compounded_dd_matches_hand_computed_value():
    entries = [{"sig": k, "side": 1, "tag": k} for k in (0, 12, 24, 36, 48)]
    m = _evaluate(entries)["tiers"]["x1"]["strategy"]
    assert m["N"] == 5
    assert m["exit_mix"] == {"SL": 3, "TP": 2}

    eq, peak, dd = 1.0, 1.0, 0.0
    for r in R_SEQ:
        eq *= (1.0 + 0.005 * r)
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
    assert m["max_dd_pct"] == pytest.approx(dd * 100.0, abs=1e-12)
    assert m["final_eq"] == pytest.approx(eq, abs=1e-12)

    # linear discriminator: `eq += 0.005 * r` would give a different DD
    lin_eq, lin_peak, lin_dd = 1.0, 1.0, 0.0
    for r in R_SEQ:
        lin_eq += 0.005 * r
        lin_peak = max(lin_peak, lin_eq)
        lin_dd = max(lin_dd, (lin_peak - lin_eq) / lin_peak)
    assert abs(m["max_dd_pct"] - lin_dd * 100.0) > 1e-6
