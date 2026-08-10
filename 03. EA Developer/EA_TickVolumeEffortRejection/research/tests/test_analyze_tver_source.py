from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_tver_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_tver_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def synthetic_frame() -> pd.DataFrame:
    times = pd.date_range("2018-01-01T00:00:00Z", periods=40, freq="5min")
    frame = pd.DataFrame(
        {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "source_epoch": (times.astype("int64") // 1_000_000_000).astype("int64"),
            "time_utc": times,
            "utc_ambiguous": False,
            "open": 100.0,
            "high": 100.5,
            "low": 99.5,
            "close": 100.1,
            "tick_volume": 100,
        }
    )

    frame.loc[20, ["open", "high", "low", "close", "tick_volume"]] = [
        100.25,
        100.35,
        99.65,
        100.30,
        250,
    ]
    frame.loc[30, ["open", "high", "low", "close", "tick_volume"]] = [
        99.75,
        100.35,
        99.65,
        99.70,
        250,
    ]
    return frame


def test_exact_closed_bar_rules_emit_symmetric_candidates() -> None:
    candidates, report = MODULE.analyze_frame(synthetic_frame())

    assert [row["direction"] for row in candidates] == ["LONG", "SHORT"]
    assert candidates[0]["source_bar_open_utc"] == "2018-01-01T01:40:00Z"
    assert candidates[0]["decision_time_utc"] == "2018-01-01T01:45:00Z"
    assert report["funnel"]["candidates"] == 2
    assert report["funnel"]["direction_conflicts"] == 0


def test_event_bar_is_excluded_from_relative_volume_and_atr_baselines() -> None:
    candidates, _ = MODULE.analyze_frame(synthetic_frame())
    long_event = candidates[0]

    assert long_event["prior_volume10"] == pytest.approx(100.0)
    assert long_event["relative_volume10"] == pytest.approx(2.5)
    assert long_event["prior_atr14"] == pytest.approx(1.0)
    assert long_event["range_to_prior_atr14"] == pytest.approx(0.7)


def test_gap_after_event_rejects_candidate_without_reading_next_prices() -> None:
    frame = synthetic_frame()
    frame.loc[21:, "time_utc"] = frame.loc[21:, "time_utc"] + pd.Timedelta(minutes=5)
    candidates, _ = MODULE.analyze_frame(frame)

    assert [row["direction"] for row in candidates] == ["SHORT"]


def test_candidate_ledger_has_no_future_or_economic_fields() -> None:
    candidates, report = MODULE.analyze_frame(synthetic_frame())
    MODULE.assert_output_is_outcome_blind(candidates, report)

    flattened_keys = {key for row in candidates for key in row}
    assert "open" not in flattened_keys
    assert "high" not in flattened_keys
    assert "low" not in flattened_keys
    assert "close" not in flattened_keys
    assert "spread" not in flattened_keys


def test_canonical_outputs_are_byte_deterministic() -> None:
    candidates_a, report_a = MODULE.analyze_frame(synthetic_frame())
    candidates_b, report_b = MODULE.analyze_frame(synthetic_frame())

    assert MODULE.canonical_jsonl_bytes(candidates_a) == MODULE.canonical_jsonl_bytes(candidates_b)
    assert MODULE.canonical_json_bytes(report_a) == MODULE.canonical_json_bytes(report_b)


def test_validate_selected_frame_fails_closed_on_ambiguous_utc() -> None:
    frame = pd.concat([synthetic_frame()] * 8, ignore_index=True)
    frame["time_utc"] = pd.date_range("2018-01-01T00:00:00Z", periods=len(frame), freq="5min")
    frame["source_epoch"] = frame["time_utc"].astype("int64") // 1_000_000_000
    frame.loc[20, "utc_ambiguous"] = True

    original_minimum = MODULE.MIN_DESIGN_ROWS
    MODULE.MIN_DESIGN_ROWS = 1
    try:
        with pytest.raises(ValueError, match="UTC-ambiguous"):
            MODULE.validate_and_select_frame(frame)
    finally:
        MODULE.MIN_DESIGN_ROWS = original_minimum


def test_validate_selected_frame_rejects_any_materialized_sealed_row() -> None:
    frame = synthetic_frame()
    frame.loc[39, "time_utc"] = pd.Timestamp("2023-01-01T00:00:00Z")

    original_minimum = MODULE.MIN_DESIGN_ROWS
    MODULE.MIN_DESIGN_ROWS = 1
    try:
        with pytest.raises(ValueError, match="outside the frozen design window"):
            MODULE.validate_and_select_frame(frame)
    finally:
        MODULE.MIN_DESIGN_ROWS = original_minimum


@pytest.mark.parametrize("invalid_index", [10, 19])
def test_any_invalid_prior_rv10_volume_rejects_event(invalid_index: int) -> None:
    frame = synthetic_frame()
    frame.loc[invalid_index, "tick_volume"] = 0
    candidates, _ = MODULE.analyze_frame(frame)

    assert not any(row["source_bar_open_utc"] == "2018-01-01T01:40:00Z" for row in candidates)


@pytest.mark.parametrize("invalid_index", [5, 19])
def test_any_invalid_prior_atr14_input_rejects_event(invalid_index: int) -> None:
    frame = synthetic_frame()
    frame.loc[invalid_index, "high"] = frame.loc[invalid_index, "low"] - 0.1
    candidates, _ = MODULE.analyze_frame(frame)

    assert not any(row["source_bar_open_utc"] == "2018-01-01T01:40:00Z" for row in candidates)


def test_validate_selected_frame_rejects_null_symbol_or_timeframe() -> None:
    frame = synthetic_frame()
    frame.loc[20, "symbol"] = None

    original_minimum = MODULE.MIN_DESIGN_ROWS
    MODULE.MIN_DESIGN_ROWS = 1
    try:
        with pytest.raises(ValueError, match="exclusively XAUUSD"):
            MODULE.validate_and_select_frame(frame)
    finally:
        MODULE.MIN_DESIGN_ROWS = original_minimum


def test_registry_authority_fails_closed_without_explicit_source_permission(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    row = {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "state": "probe",
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.FROZEN_PREREG_SHA256,
        "metrics": {"source_feasibility_attempts_consumed": 0},
        "validation": {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
            "source_feasibility_attempt_limit": 1,
            "source_run_authorized": False,
            "source_feasibility_only": True,
            "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
            "economics_authorized": False,
            "outcome_prices_authorized": False,
            "research_validation_access_authorized": False,
            "research_holdout_access_authorized": False,
            "mt5_authorized": False,
            "mql5_authorized": False,
            "live_trading_authorized": False,
        },
    }
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source_run_authorized"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive_and_durable(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    started_at, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)

    assert started_at.endswith("Z")
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
