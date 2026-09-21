"""R02-A F4: the gate has no lenient 3-of-3 fallbacks."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

import phys_stats as ps  # noqa: E402

TOP = {"D": 0.08, "lo": 0.01}


def test_three_years_all_positive_is_not_a_pass():
    v = ps.gate_verdict(TOP, True,
                        {f"S{i}": 0.1 for i in range(4)},
                        {str(y): 0.1 for y in (2016, 2017, 2018)})
    assert v["checks"]["years_4of6"] is False
    assert not v["pass"]


def test_three_symbols_all_positive_is_not_a_pass():
    v = ps.gate_verdict(TOP, True,
                        {"A": 0.1, "B": 0.1, "C": 0.1},
                        {str(y): 0.1 for y in range(2016, 2022)})
    assert v["checks"]["symbols_3of4"] is False
    assert not v["pass"]


def test_full_six_years_and_four_symbols_still_pass():
    v = ps.gate_verdict(TOP, True,
                        {"A": 0.1, "B": 0.2, "C": 0.3, "D": -0.1},
                        {str(y): 0.1 for y in range(2016, 2022)})
    assert v["checks"]["years_4of6"] and v["checks"]["symbols_3of4"]
    assert v["pass"]
