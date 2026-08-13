from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_mirb_m15_source.py"
SPEC = importlib.util.spec_from_file_location("mirb", MODULE_PATH)
assert SPEC and SPEC.loader
MIRB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIRB)


def test_ema_uses_sma9_seed_then_recursive_update() -> None:
    values = pd.Series([float(i) for i in range(1, 12)])
    ema = MIRB.ema_sma_seed(values, 9)
    assert ema.iloc[:8].isna().all()
    assert ema.iloc[8] == 5.0
    assert ema.iloc[9] == 6.0
    assert np.isclose(ema.iloc[10], 7.0)


def test_ema_resets_after_invalid_value() -> None:
    values = pd.Series([1.0] * 9 + [np.nan] + [2.0] * 9)
    ema = MIRB.ema_sma_seed(values, 9)
    assert ema.iloc[8] == 1.0
    assert np.isnan(ema.iloc[9])
    assert ema.iloc[10:18].isna().all()
    assert ema.iloc[18] == 2.0


def test_strict_bulge_boundaries_do_not_arm_or_trigger_on_equality() -> None:
    data = pd.DataFrame({
        "source_epoch": np.arange(8, dtype=np.int64) * 900,
        "time_utc": pd.date_range("2016-01-04", periods=8, freq="15min", tz="UTC"),
        "open": [1.0] * 8, "high": [2.0] * 8, "low": [0.5] * 8, "close": [1.0] * 8,
        "mass_index": [27.0, 26.4, 27.1, 26.5, 26.4, 27.1, 26.4, 26.4],
        "close_ema9": [1.00, 1.01, 1.02, 1.01, 1.00, 1.01, 1.02, 1.03],
        "feature_valid": [True] * 8,
    })
    original = MIRB.calculate_features
    MIRB.calculate_features = lambda _: data.copy()
    try:
        events, report = MIRB.analyze_frame(data)
    finally:
        MIRB.calculate_features = original
    assert [event["direction"] for event in events] == ["LONG", "SHORT"]
    assert report["raw_events"] == 2


def test_exact_next_gap_consumes_event() -> None:
    data = pd.DataFrame({
        "source_epoch": [0, 900, 1800, 3600],
        "time_utc": pd.to_datetime(["2016-01-04T00:00Z", "2016-01-04T00:15Z", "2016-01-04T00:30Z", "2016-01-04T01:00Z"]),
        "open": [1.0] * 4, "high": [2.0] * 4, "low": [0.5] * 4, "close": [1.0] * 4,
        "mass_index": [27.1, 26.4, 27.1, 26.4], "close_ema9": [1.0, 0.9, 1.0, 1.1],
        "feature_valid": [True] * 4,
    })
    original = MIRB.calculate_features
    MIRB.calculate_features = lambda _: data.copy()
    try:
        events, report = MIRB.analyze_frame(data)
    finally:
        MIRB.calculate_features = original
    assert len(events) == 1
    assert report["raw_events"] == 2
    assert report["gap_rejected_events"] == 1


def test_event_schema_has_no_outcome_fields() -> None:
    forbidden = {"next_open", "next_high", "next_low", "next_close", "return", "pnl", "profit_factor"}
    assert MIRB.EVENT_KEYS.isdisjoint(forbidden)
    assert MIRB.EVENT_KEYS == {
        "hypothesis_id", "source_epoch", "source_bar_time_utc", "decision_time_utc",
        "direction", "mass_index", "prior_close_ema9", "close_ema9",
    }


def test_incomplete_m5_triplet_is_retained_as_invalid_reset_bar() -> None:
    frame = pd.DataFrame({
        "symbol": ["EURUSD", "EURUSD"], "timeframe": ["M5", "M5"],
        "source_epoch": [1420070400, 1420070700],
        "time_utc": pd.to_datetime(["2015-01-01T00:00Z", "2015-01-01T00:05Z"]),
        "utc_ambiguous": [False, False], "open": [1.2, 1.2], "high": [1.3, 1.3],
        "low": [1.1, 1.1], "close": [1.2, 1.2],
    })
    result = MIRB.aggregate_complete_m15(frame)
    assert len(result) == 1
    assert result.iloc[0][["open", "high", "low", "close"]].isna().all()
