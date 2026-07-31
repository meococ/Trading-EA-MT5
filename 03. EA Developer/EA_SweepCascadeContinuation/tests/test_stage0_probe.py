from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "research" / "scc_stage0_probe.py"
)
SPEC = importlib.util.spec_from_file_location("scc_stage0_probe", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _bars(count: int = 12) -> pd.DataFrame:
    times = pd.date_range("2022-06-06 08:00:00", periods=count, freq="5min")
    frame = pd.DataFrame(
        {
            "time_utc": times,
            "time_server": times + pd.Timedelta(hours=3),
            "utc_offset_h": 3,
            "open": 1.0990,
            "high": 1.0995,
            "low": 1.0985,
            "close": 1.0990,
            "tick_volume": 100,
            "atr": 0.0010,
            "last_pivot_high": np.nan,
            "last_pivot_high_index": np.nan,
            "last_pivot_low": np.nan,
            "last_pivot_low_index": np.nan,
        }
    )
    return frame


def _long_break_fixture(*, retest_close: float = 1.1006) -> pd.DataFrame:
    frame = _bars()
    frame.loc[1:, "last_pivot_high"] = 1.1000
    frame.loc[1:, "last_pivot_high_index"] = 0
    frame.loc[2, ["close", "high"]] = [1.0995, 1.0998]
    frame.loc[3, ["open", "low", "high", "close"]] = [
        1.0995,
        1.0992,
        1.1012,
        1.1008,
    ]
    frame.loc[4, ["open", "low", "high", "close"]] = [
        1.1008,
        1.1002,
        1.1015,
        1.1009,
    ]
    frame.loc[5, ["open", "low", "high", "close"]] = [
        1.1009,
        1.0997,
        1.1011,
        retest_close,
    ]
    frame.loc[6, ["open", "low", "high", "close"]] = [
        1.1007,
        1.1004,
        1.1012,
        1.1010,
    ]
    return frame


def test_resample_keeps_only_exact_five_minute_offsets() -> None:
    times = pd.to_datetime(
        [
            "2022-01-03 08:00",
            "2022-01-03 08:01",
            "2022-01-03 08:02",
            "2022-01-03 08:03",
            "2022-01-03 08:04",
            "2022-01-03 08:05",
            "2022-01-03 08:07",
        ]
    )
    m1 = pd.DataFrame(
        {
            "time_utc": times,
            "time_server": times + pd.Timedelta(hours=2),
            "utc_offset_h": 2,
            "open": np.arange(len(times), dtype=float),
            "high": np.arange(len(times), dtype=float) + 1,
            "low": np.arange(len(times), dtype=float) - 1,
            "close": np.arange(len(times), dtype=float) + 0.5,
            "tick_volume": 10,
        }
    )
    bars, quality = MODULE.resample_complete_m5(m1)
    assert list(bars["time_utc"]) == [pd.Timestamp("2022-01-03 08:00")]
    assert quality["complete_m5_bins"] == 1
    assert quality["incomplete_m5_bins"] == 1


def test_n2_pivot_is_not_exposed_until_known_before_scan_bar() -> None:
    frame = _bars(9)
    frame["high"] = [1, 2, 5, 2, 1, 2, 2, 2, 2]
    frame["low"] = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    pivots = MODULE.mark_confirmed_pivots(frame, strength=2)
    assert np.isnan(pivots.loc[4, "last_pivot_high"])
    assert pivots.loc[5, "last_pivot_high"] == 5
    assert pivots.loc[5, "last_pivot_high_index"] == 2


def test_break_hold_retest_accepts_at_close_and_uses_next_open_reference() -> None:
    result = MODULE.scan_scc_events(_long_break_fixture())
    control = result["control_candidates"]
    challenger = result["challenger_candidates"]
    assert len(control) == 1
    assert len(challenger) == 1
    row = challenger.iloc[0]
    assert row["direction"] == "LONG"
    assert row["break_index"] == 3
    assert row["hold_index"] == 4
    assert row["retest_index"] == 5
    assert row["entry_reference_index"] == 6
    assert row["passage_lag"] == 1
    assert row["origin_id"] == control.iloc[0]["origin_id"]
    assert row["initial_risk_pips"] > 0


def test_close_inside_has_priority_over_intrabar_touch() -> None:
    result = MODULE.scan_scc_events(
        _long_break_fixture(retest_close=1.0998)
    )
    assert result["challenger_candidates"].empty
    assert result["funnel"]["reject_close_inside"] == 1
    assert result["funnel"]["accepted_retests"] == 0


def test_first_arm_attempt_consumes_the_utc_day_even_after_hold_reject() -> None:
    frame = _long_break_fixture()
    frame.loc[4, "close"] = 1.0998  # first arm rejects at HOLD
    frame.loc[7:, "last_pivot_high"] = 1.1010
    frame.loc[7:, "last_pivot_high_index"] = 4
    frame.loc[6, "close"] = 1.1000
    frame.loc[7, ["high", "close"]] = [1.1020, 1.1015]
    result = MODULE.scan_scc_events(frame)
    assert len(result["control_candidates"]) == 1
    assert result["funnel"]["reject_hold"] == 1
    assert result["funnel"]["blocked_by_daily_attempt_cap"] >= 1


def test_gap_kills_active_state_before_price_logic() -> None:
    frame = _long_break_fixture()
    frame.loc[4:, "time_utc"] = frame.loc[4:, "time_utc"] + pd.Timedelta(
        minutes=5
    )
    result = MODULE.scan_scc_events(frame)
    assert result["challenger_candidates"].empty
    assert result["funnel"]["reject_gap"] == 1


def test_outcome_columns_are_rejected() -> None:
    with pytest.raises(RuntimeError, match="OUTCOME COLUMN FORBIDDEN"):
        MODULE.assert_outcome_blind(pd.DataFrame({"profit_factor": [1.0]}))
