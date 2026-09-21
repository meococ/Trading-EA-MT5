import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

import phys_common as pc  # noqa: E402
import phys_stats as ps  # noqa: E402


def _rows(n, out=0.5):
    return [{"outcome": "BOUNCE" if (i % 2 == 0) else "BREAK",
             "strength": 0.5, "anchor_i": i, "year": 2016 + (i % 6),
             "symbol": "EURUSD"} for i in range(n)]


def test_wilson_bounds():
    lo, hi = pc.wilson_ci(50, 100)
    assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60
    assert pc.wilson_ci(0, 0)[0] != pc.wilson_ci(0, 0)[0]


def test_paired_diff_zero_when_identical():
    real = _rows(60)
    ctrl = []
    for i in range(60):
        for k in range(5):
            c = dict(real[i])
            c["anchor_i"] = i
            ctrl.append(c)
    st = ps.cell_stats(real, ctrl, ps._bounce_value, n_boot=2000)
    assert abs(st["D"]) < 1e-9
    assert st["n"] == 60


def test_paired_diff_positive():
    real = [dict(r, outcome="BOUNCE") for r in _rows(40)]
    ctrl = []
    for i in range(40):
        for k in range(5):
            row = dict(real[i], anchor_i=i, outcome="BREAK" if k else "BOUNCE")
            ctrl.append(row)
    st = ps.cell_stats(real, ctrl, ps._bounce_value, n_boot=2000)
    assert st["D"] > 0.7
    assert st["lo"] > 0
    assert st["p"] < 0.01


def test_gate_verdict():
    top = {"D": 0.08, "lo": 0.01}
    v = ps.gate_verdict(top, True,
                        {"EURUSD": 1.0, "GBPUSD": 0.5, "USDJPY": 0.2, "AUDUSD": -0.1},
                        {y: 0.1 for y in range(2016, 2022)})
    assert v["pass"]
    v2 = ps.gate_verdict({"D": 0.04, "lo": 0.01}, True,
                         {"EURUSD": 1.0, "GBPUSD": 0.5, "USDJPY": 0.2, "AUDUSD": -0.1},
                         {y: 0.1 for y in range(2016, 2022)})
    assert not v2["pass"]


def test_bh():
    out = ps.bh_across([0.001, 0.02, 0.5, 0.8], q=0.10)
    assert out["rejected"][0] is True
    assert out["rejected"][3] is False
