import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

from phys_resolve import resolve_events  # noqa: E402
from synth import make_bars  # noqa: E402


def _bars(n=70, close=1.1000, spread=0.0002):
    bars = make_bars([close] * n, spread=spread)
    bars["o"][:] = close
    bars["h"][:] = close + spread
    bars["l"][:] = close - spread
    return bars


def _event(t=10, side=-1, near=1.1000, far=1.1010, m=0.0010):
    lo = min(near, far)
    hi = max(near, far)
    return {"bar_idx": t, "side": side, "lo": lo, "hi": hi,
            "near": near, "far": far, "m": m}


def test_bounce_first():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.0995, 1.1005, 1.1000
    bars["l"][12], bars["h"][12], bars["c"][12] = 1.0985, 1.1000, 1.0990
    res, cnt = resolve_events([_event()], bars)
    assert res[0]["outcome"] == "BOUNCE" and res[0]["bounce_bar"] == 12
    assert cnt["bounce"] == 1


def test_break_first():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.1000, 1.1030, 1.1025
    res, _ = resolve_events([_event()], bars)
    assert res[0]["outcome"] == "BREAK" and res[0]["break_bar"] == 11
    assert res[0]["break_close"] == pytest.approx(1.1025)
    assert res[0]["cont_outcome"] == "NONE"


def test_same_bar_break_wins():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.0985, 1.1030, 1.1025
    res, _ = resolve_events([_event()], bars)
    assert res[0]["outcome"] == "BREAK"


def test_bounce_before_break_wins():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.0985, 1.1000, 1.0990
    bars["l"][12], bars["h"][12], bars["c"][12] = 1.1000, 1.1030, 1.1025
    res, _ = resolve_events([_event()], bars)
    assert res[0]["outcome"] == "BOUNCE" and res[0]["bounce_bar"] == 11


def test_none():
    bars = _bars()
    for j in range(11, 59):
        bars["l"][j], bars["h"][j], bars["c"][j] = 1.0995, 1.1015, 1.1005
    res, cnt = resolve_events([_event()], bars)
    assert res[0]["outcome"] == "NONE" and cnt["none"] == 1


def test_side_plus_one():
    bars = _bars(close=1.1010)
    bars["o"][:] = 1.1010
    bars["h"][:] = 1.1012
    bars["l"][:] = 1.1008
    bars["h"][11], bars["l"][11], bars["c"][11] = 1.1025, 1.1015, 1.1020
    ev = _event(side=+1, near=1.1010, far=1.1000)
    res, _ = resolve_events([ev], bars)
    assert res[0]["outcome"] == "BOUNCE" and res[0]["bounce_bar"] == 11


def test_continuation_cont():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.1000, 1.1030, 1.1025
    bars["l"][12], bars["h"][12], bars["c"][12] = 1.1020, 1.1040, 1.1035
    res, _ = resolve_events([_event()], bars)
    assert res[0]["outcome"] == "BREAK"
    assert res[0]["cont_outcome"] == "CONT" and res[0]["cont_bar"] == 12


def test_continuation_return():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.1000, 1.1030, 1.1025
    bars["l"][12], bars["h"][12], bars["c"][12] = 1.1000, 1.1030, 1.1020
    res, _ = resolve_events([_event()], bars)
    assert res[0]["cont_outcome"] == "RETURN" and res[0]["return_bar"] == 12


def test_continuation_tie_return_wins():
    bars = _bars()
    bars["l"][11], bars["h"][11], bars["c"][11] = 1.1000, 1.1030, 1.1025
    bars["l"][12], bars["h"][12], bars["c"][12] = 1.1000, 1.1040, 1.1035
    res, _ = resolve_events([_event()], bars)
    assert res[0]["cont_outcome"] == "RETURN"


def test_dropped_window():
    bars = _bars(n=50)
    res, cnt = resolve_events([_event(t=10)], bars)
    assert res[0]["outcome"] == "DROPPED" and cnt["dropped_window"] == 1
