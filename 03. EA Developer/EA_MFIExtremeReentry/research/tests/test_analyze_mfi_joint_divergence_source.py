from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_mfi_joint_divergence_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_mfi_joint_divergence_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def series_fixture(length: int = 32):
    times = pd.Series(pd.date_range("2018-01-01T00:00:00Z", periods=length, freq="5min"))
    lows = pd.Series(np.full(length, 10.0))
    highs = pd.Series(np.full(length, 20.0))
    mfi = pd.Series(np.full(length, 50.0))
    return lows, highs, mfi, times


def set_joint_low(lows: pd.Series, mfi: pd.Series, pivot: int, price: float, value: float) -> None:
    lows.iloc[pivot] = price
    mfi.iloc[pivot] = value


def set_joint_high(highs: pd.Series, mfi: pd.Series, pivot: int, price: float, value: float) -> None:
    highs.iloc[pivot] = price
    mfi.iloc[pivot] = value


def test_exact_bullish_joint_divergence() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 4.0, 30.0)

    events, diagnostics, usable = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert diagnostics == {
        "raw_events": 1,
        "executable_events": 1,
        "gap_rejected_events": 0,
        "direction_conflicts": 0,
    }
    assert events[0]["direction"] == "LONG"
    assert events[0]["previous_pivot_price"] == 5.0
    assert events[0]["current_pivot_price"] == 4.0
    assert events[0]["previous_pivot_mfi14"] == 20.0
    assert events[0]["current_pivot_mfi14"] == 30.0
    assert events[0]["confirmation_time_utc"] == times.iloc[23].isoformat().replace("+00:00", "Z")
    assert bool(usable.iloc[18])


def test_exact_bearish_joint_divergence() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_high(highs, mfi, 16, 30.0, 80.0)
    set_joint_high(highs, mfi, 21, 31.0, 70.0)

    events, diagnostics, _ = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert diagnostics["raw_events"] == 1
    assert [row["direction"] for row in events] == ["SHORT"]


def test_price_only_or_mfi_only_pivot_does_not_initialize() -> None:
    lows, highs, mfi, times = series_fixture()
    lows.iloc[16] = 5.0
    set_joint_low(lows, mfi, 21, 4.0, 30.0)

    events, diagnostics, _ = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert events == []
    assert diagnostics["raw_events"] == 0


def test_every_joint_pivot_replaces_anchor_even_without_signal() -> None:
    lows, highs, mfi, times = series_fixture(36)
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 6.0, 25.0)
    set_joint_low(lows, mfi, 26, 5.5, 30.0)

    events, _, _ = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert len(events) == 1
    assert events[0]["previous_pivot_price"] == 6.0


def test_equality_never_qualifies_divergence() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 5.0, 30.0)

    events, diagnostics, _ = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert events == []
    assert diagnostics["raw_events"] == 0


def test_invalid_dependency_window_resets_both_anchors() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 4.0, 30.0)
    mfi.iloc[19] = np.nan

    events, diagnostics, usable = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert events == []
    assert diagnostics["raw_events"] == 0
    assert not bool(usable.iloc[23])


def test_noncontiguous_window_resets_anchors() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 4.0, 30.0)
    times.loc[20:] = times.loc[20:] + pd.Timedelta(minutes=5)

    events, _, usable = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert events == []
    assert not bool(usable.iloc[23])


def test_raw_event_at_next_timestamp_gap_is_consumed() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 4.0, 30.0)
    times.loc[24:] = times.loc[24:] + pd.Timedelta(minutes=5)

    events, diagnostics, _ = MODULE.detect_joint_divergence(lows, highs, mfi, times)

    assert events == []
    assert diagnostics["raw_events"] == 1
    assert diagnostics["gap_rejected_events"] == 1


def test_event_ledger_uses_exact_allowlist() -> None:
    lows, highs, mfi, times = series_fixture()
    set_joint_low(lows, mfi, 16, 5.0, 20.0)
    set_joint_low(lows, mfi, 21, 4.0, 30.0)
    events, _, _ = MODULE.detect_joint_divergence(lows, highs, mfi, times)
    report = {"prohibitions": {"post_event_ohlc_read": False}}

    MODULE.assert_outcome_blind(events, report)
    assert set(events[0]) == MODULE.EVENT_KEYS


def test_registry_requires_dependency_and_explicit_permission(tmp_path: Path) -> None:
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
            "source_run_authorized": True,
            "source_feasibility_only": True,
            "reviewed_analyzer_sha256": MODULE.base.sha256_file(MODULE_PATH),
            "mfi_calculation_dependency_sha256": "0" * 64,
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
    with pytest.raises(ValueError, match="dependency"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
