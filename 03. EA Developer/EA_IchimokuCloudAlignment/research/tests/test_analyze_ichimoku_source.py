from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_ichimoku_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_ichimoku_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_frame(prices: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time_utc": pd.date_range("2018-01-01T00:00:00Z", periods=len(prices), freq="5min"),
            "high": prices + 1.0,
            "low": prices - 1.0,
            "close": prices,
        }
    )


def bullish_frame() -> pd.DataFrame:
    prices = np.r_[
        np.linspace(100.0, 150.0, 100),
        np.linspace(150.0, 140.0, 20),
        np.linspace(140.0, 170.0, 40),
    ]
    return source_frame(prices)


def bearish_frame() -> pd.DataFrame:
    prices = np.r_[
        np.linspace(150.0, 100.0, 100),
        np.linspace(100.0, 110.0, 20),
        np.linspace(110.0, 80.0, 40),
    ]
    return source_frame(prices)


def test_exact_midpoint_formulas_and_display_shift() -> None:
    prices = np.arange(100, dtype=float)
    indicator = MODULE.calculate_ichimoku(source_frame(prices))

    assert indicator["tenkan"].iloc[77] == pytest.approx(73.0)
    assert indicator["kijun"].iloc[77] == pytest.approx(64.5)
    assert indicator["displayed_span_a"].iloc[77] == pytest.approx(42.75)
    assert indicator["displayed_span_b"].iloc[77] == pytest.approx(25.5)


def test_first_usable_row_is_exactly_77() -> None:
    indicator = MODULE.calculate_ichimoku(source_frame(np.arange(100, dtype=float)))

    assert not bool(indicator["feature_valid"].iloc[76])
    assert bool(indicator["feature_valid"].iloc[77])


def test_invalid_oldest_dependency_row_blocks_77_not_78() -> None:
    frame = source_frame(np.arange(100, dtype=float))
    frame.loc[0, "high"] = np.nan
    indicator = MODULE.calculate_ichimoku(frame)

    assert not bool(indicator["feature_valid"].iloc[77])
    assert bool(indicator["feature_valid"].iloc[78])


def test_exact_bullish_full_alignment_event() -> None:
    events, report = MODULE.analyze_frame(bullish_frame())

    assert [row["direction"] for row in events] == ["LONG"]
    row = events[0]
    assert row["prior_tenkan"] <= row["prior_kijun"]
    assert row["tenkan"] > row["kijun"]
    assert row["source_close"] > max(row["displayed_span_a"], row["displayed_span_b"])
    assert row["displayed_span_a"] > row["displayed_span_b"]
    assert report["funnel"]["raw_events"] == 1


def test_exact_bearish_full_alignment_event() -> None:
    events, _ = MODULE.analyze_frame(bearish_frame())

    assert [row["direction"] for row in events] == ["SHORT"]
    row = events[0]
    assert row["prior_tenkan"] >= row["prior_kijun"]
    assert row["tenkan"] < row["kijun"]
    assert row["source_close"] < min(row["displayed_span_a"], row["displayed_span_b"])
    assert row["displayed_span_a"] < row["displayed_span_b"]


def test_raw_event_at_gap_is_consumed() -> None:
    frame = bullish_frame()
    event_index = 130
    frame.loc[event_index + 1 :, "time_utc"] = frame.loc[event_index + 1 :, "time_utc"] + pd.Timedelta(minutes=5)

    events, report = MODULE.analyze_frame(frame)

    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_normal_market_closure_inside_lookback_does_not_break_bar_count_indicator() -> None:
    frame = bullish_frame()
    frame.loc[50:, "time_utc"] = frame.loc[50:, "time_utc"] + pd.Timedelta(days=2)

    events, _ = MODULE.analyze_frame(frame)

    assert len(events) == 1


def test_event_ledger_uses_exact_allowlist() -> None:
    events, report = MODULE.analyze_frame(bullish_frame())

    MODULE.assert_outcome_blind(events, report)
    assert set(events[0]) == MODULE.EVENT_KEYS


def test_selected_frame_rejects_null_symbol() -> None:
    prices = np.arange(MODULE.MIN_ROWS, dtype=float) + 100.0
    frame = source_frame(prices)
    frame.insert(0, "symbol", "XAUUSD")
    frame.insert(1, "timeframe", "M5")
    frame.insert(2, "source_epoch", np.arange(len(frame)))
    frame.insert(4, "utc_ambiguous", False)
    frame.loc[10, "symbol"] = None

    with pytest.raises(ValueError, match="XAUUSD"):
        MODULE.validate_selected_frame(frame)


def test_registry_requires_explicit_source_permission(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    row = {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "state": "probe",
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.PREREG_SHA256,
        "metrics": {"source_feasibility_attempts_consumed": 0},
        "validation": {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
            "source_feasibility_attempt_limit": 1,
            "source_run_authorized": False,
            "source_feasibility_only": True,
            "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
            "outcome_prices_authorized": False,
            "economics_authorized": False,
            "research_validation_access_authorized": False,
            "research_holdout_access_authorized": False,
            "mt5_authorized": False,
            "mql5_authorized": False,
            "live_trading_authorized": False,
        },
    }
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source_run"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
