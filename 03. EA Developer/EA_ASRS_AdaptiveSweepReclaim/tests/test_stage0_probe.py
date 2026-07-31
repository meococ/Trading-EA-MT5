from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "research" / "asrs_stage0_probe.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("asrs_stage0_probe", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resample_keeps_only_complete_consecutive_m5_bins():
    mod = load_module()
    times = list(pd.date_range("2020-01-02 10:00", periods=5, freq="min"))
    times.append(pd.Timestamp("2020-01-02 10:05"))
    m1 = pd.DataFrame(
        {
            "time_utc": times,
            "time_server": times,
            "utc_offset_h": [2] * 6,
            "open": [1.1000, 1.1001, 1.1002, 1.1003, 1.1004, 1.1005],
            "high": [1.1002, 1.1003, 1.1004, 1.1005, 1.1006, 1.1007],
            "low": [1.0998, 1.0999, 1.1000, 1.1001, 1.1002, 1.1003],
            "close": [1.1001, 1.1002, 1.1003, 1.1004, 1.1005, 1.1006],
            "tick_volume": [1, 2, 3, 4, 5, 6],
        }
    )

    bars, quality = mod.resample_complete_m5(m1)

    assert len(bars) == 1
    assert bars.iloc[0]["time_utc"] == pd.Timestamp("2020-01-02 10:00")
    assert bars.iloc[0]["tick_volume"] == 15
    assert bars.iloc[0]["open"] == pytest.approx(1.1000)
    assert bars.iloc[0]["close"] == pytest.approx(1.1005)
    assert quality["complete_m5_bins"] == 1
    assert quality["incomplete_m5_bins"] == 1


def test_n2_fractal_is_not_available_until_one_bar_after_right_side_closes():
    mod = load_module()
    bars = pd.DataFrame(
        {
            "high": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
            "low": [5.0, 4.0, 3.0, 4.0, 5.0, 2.5],
        }
    )

    pivots = mod.mark_confirmed_pivots(bars, strength=2)

    assert np.isnan(pivots.loc[4, "last_pivot_low"])
    assert pivots.loc[5, "last_pivot_low"] == pytest.approx(3.0)
    assert pivots.loc[5, "last_pivot_low_index"] == 2


def test_tick_volume_baseline_excludes_the_current_bar():
    mod = load_module()
    bars = pd.DataFrame({"tick_volume": [10.0] * 20 + [1000.0]})

    baseline = mod.prior_volume_mean(bars["tick_volume"], period=20)

    assert np.isnan(baseline.iloc[19])
    assert baseline.iloc[20] == pytest.approx(10.0)


def test_full_asrs_long_path_uses_next_bar_reclaim_and_immediate_retest():
    mod = load_module()
    n = 32
    times = pd.date_range("2020-01-02 08:00", periods=n, freq="5min")
    bars = pd.DataFrame(
        {
            "time_utc": times,
            "time_server": times + pd.Timedelta(hours=2),
            "utc_offset_h": [2] * n,
            "open": [1.1000] * n,
            "high": [1.1004] * n,
            "low": [1.0996] * n,
            "close": [1.1000] * n,
            "tick_volume": [100.0] * n,
            "atr": [0.0010] * n,
            "adx": [20.0] * n,
            "volume_mean20": [100.0] * n,
            "last_pivot_low": [np.nan] * n,
            "last_pivot_low_index": [np.nan] * n,
            "last_pivot_high": [np.nan] * n,
            "last_pivot_high_index": [np.nan] * n,
        }
    )
    sweep = 25
    bars.loc[sweep:, "last_pivot_low"] = 1.0990
    bars.loc[sweep:, "last_pivot_low_index"] = 20
    bars.loc[sweep, ["open", "high", "low", "close", "tick_volume"]] = [
        1.0994,
        1.0996,
        1.0984,
        1.0988,
        200.0,
    ]
    bars.loc[sweep + 1, ["open", "high", "low", "close"]] = [
        1.0988,
        1.0994,
        1.0987,
        1.0992,
    ]
    bars.loc[sweep + 2, ["open", "high", "low", "close"]] = [
        1.0991,
        1.0995,
        1.09895,
        1.0993,
    ]
    bars.loc[sweep + 3, "open"] = 1.0994

    result = mod.scan_asrs_events(bars)
    candidates = result["challenger_candidates"]

    assert len(candidates) == 1
    row = candidates.iloc[0]
    assert row["direction"] == "LONG"
    assert row["sweep_index"] == sweep
    assert row["reclaim_index"] == sweep + 1
    assert row["retest_index"] == sweep + 2
    assert row["entry_index"] == sweep + 3
    assert row["initial_risk_pips"] == pytest.approx(13.0)
    assert row["cost_r_1_5"] == pytest.approx(1.5 / 13.0)


def test_outcome_blind_guard_rejects_future_or_trade_result_columns():
    mod = load_module()
    safe = pd.DataFrame({"entry_time_utc": [pd.Timestamp("2020-01-01")], "risk_pips": [8.0]})
    mod.assert_outcome_blind(safe)

    for forbidden in ("pnl", "profit_factor", "mfe", "mae", "forward_return", "win"):
        bad = safe.assign(**{forbidden: [0.0]})
        with pytest.raises(RuntimeError, match="OUTCOME COLUMN"):
            mod.assert_outcome_blind(bad)

