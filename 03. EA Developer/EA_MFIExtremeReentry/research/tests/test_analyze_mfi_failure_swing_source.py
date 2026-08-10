from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_mfi_failure_swing_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_mfi_failure_swing_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def detect(values: list[float], gap_after: int | None = None):
    times = pd.Series(pd.date_range("2018-01-01T00:00:00Z", periods=len(values), freq="5min"))
    if gap_after is not None:
        times.loc[gap_after + 1 :] = times.loc[gap_after + 1 :] + pd.Timedelta(minutes=5)
    return MODULE.detect_failure_swings(pd.Series(values, dtype=float), times)


def test_exact_bullish_four_step_path() -> None:
    events, diagnostics = detect([10, 25, 35, 30, 34, 36, 40])

    assert diagnostics == {
        "raw_events": 1,
        "executable_events": 1,
        "gap_rejected_events": 0,
        "direction_conflicts": 0,
    }
    assert events[0]["direction"] == "LONG"
    assert events[0]["trigger_mfi14"] == 35
    assert events[0]["prior_mfi14"] == 34
    assert events[0]["mfi14"] == 36


def test_exact_bearish_four_step_path() -> None:
    events, _ = detect([90, 75, 65, 70, 66, 64, 60])

    assert [row["direction"] for row in events] == ["SHORT"]
    assert events[0]["trigger_mfi14"] == 65
    assert events[0]["prior_mfi14"] == 66
    assert events[0]["mfi14"] == 64


def test_touching_extreme_restarts_and_prevents_old_trigger_break() -> None:
    bullish, _ = detect([10, 25, 35, 20, 36, 40])
    bearish, _ = detect([90, 75, 65, 80, 64, 60])

    assert bullish == []
    assert bearish == []


def test_after_event_fresh_extreme_is_required() -> None:
    events, _ = detect([10, 25, 35, 30, 36, 30, 40, 45, 30, 50])

    assert len(events) == 1


def test_invalid_mfi_resets_both_machines() -> None:
    events, _ = detect([10, 25, 35, np.nan, 30, 36, 40])

    assert events == []


def test_raw_event_at_gap_is_consumed_but_not_executable() -> None:
    events, diagnostics = detect([10, 25, 35, 30, 36, 40], gap_after=4)

    assert events == []
    assert diagnostics["raw_events"] == 1
    assert diagnostics["gap_rejected_events"] == 1


def test_strict_equality_does_not_form_pullback_or_break() -> None:
    events, _ = detect([10, 25, 35, 35, 30, 35, 36, 40])

    assert len(events) == 1
    assert events[0]["mfi14"] == 36


def test_event_ledger_is_outcome_blind() -> None:
    events, _ = detect([10, 25, 35, 30, 36, 40])
    report = {"prohibitions": {"post_event_ohlc_read": False}}
    MODULE.assert_outcome_blind(events, report)
    keys = {key for row in events for key in row}
    assert not {"open", "high", "low", "close", "return", "profit"} & keys


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
