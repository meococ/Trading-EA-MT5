from pathlib import Path
import importlib.util
import numpy as np


MODULE_PATH = Path(__file__).resolve().parents[1] / "research" / "mzms_offline_probe.py"
SPEC = importlib.util.spec_from_file_location("mzms_offline_probe", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_long_requires_completed_local_bottom():
    assert MODULE.histogram_turn(0.02, -0.01, 0.00, 0.50, 0.01) == 1
    assert MODULE.histogram_turn(0.02, -0.01, -0.02, 0.50, 0.01) == 0


def test_short_requires_completed_local_top():
    assert MODULE.histogram_turn(-0.02, 0.01, 0.00, 0.50, 0.01) == -1
    assert MODULE.histogram_turn(-0.02, 0.01, 0.02, 0.50, 0.01) == 0


def test_delta_is_normalized_by_atr_and_has_boundary():
    assert MODULE.histogram_turn(0.004, 0.0, 0.001, 0.50, 0.01) == 0
    assert MODULE.histogram_turn(0.005, 0.0, 0.001, 0.50, 0.01) == 1


def test_spread_guard_fails_closed_on_zero():
    assert not MODULE.spread_allowed(0.0, 35.0)
    assert MODULE.spread_allowed(35.0, 35.0)
    assert not MODULE.spread_allowed(35.01, 35.0)


def test_same_m1_bar_collision_is_stop_first():
    assert MODULE.resolve_bar_exit(1, 1.1000, 1.1020, 1.1010, 1.1010) == "STOP"
    assert MODULE.resolve_bar_exit(-1, 1.0980, 1.1000, 1.0990, 1.0990) == "STOP"


def test_equal_prior_exit_timestamp_is_not_released():
    prior_exit = np.datetime64("2022-01-03T10:00")
    assert not MODULE.position_released(prior_exit, prior_exit)
    assert MODULE.position_released(prior_exit + np.timedelta64(1, "m"), prior_exit)


def test_m1_bar_beginning_at_horizon_is_excluded():
    base = np.datetime64("2022-01-03T10:00")
    times = base + np.arange(76).astype("timedelta64[m]")
    utc = times.copy()
    low = np.full(76, 1.0995)
    high = np.full(76, 1.1005)
    close = np.full(76, 1.1000)
    high[75] = 1.1020
    _, _, kind, _ = MODULE.resolve_trade(
        1, base, 1.1000, 1.0990, 1.1020, 0.0010,
        times, utc, low, high, close,
    )
    assert kind == "TIME"


def test_flatten_boundary_uses_open_before_bar_extremes():
    base = np.datetime64("2022-01-03T18:14")
    times = base + np.arange(2).astype("timedelta64[m]")
    opens = np.array([1.1000, 1.1002])
    low = np.array([1.0995, 1.0995])
    high = np.array([1.1005, 1.1020])
    close = np.array([1.1000, 1.1015])
    _, gross_r, kind, price = MODULE.resolve_trade(
        1, base, 1.1000, 1.0990, 1.1020, 0.0010,
        times, times.copy(), low, high, close, m1_open=opens,
    )
    assert kind == "FLATTEN"
    assert price == opens[1]
    assert abs(gross_r - 0.2) < 1e-12
