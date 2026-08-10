from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_mfi_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_mfi_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def synthetic_frame() -> pd.DataFrame:
    times = pd.date_range("2018-01-01T00:00:00Z", periods=45, freq="5min")
    typical = [100.0 - 0.1 * i for i in range(20)]
    typical += [98.5 + 0.1 * (i - 20) for i in range(20, 35)]
    typical += [99.4 - 0.1 * (i - 35) for i in range(35, 45)]
    frame = pd.DataFrame(
        {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "source_epoch": times.astype("int64") // 1_000_000_000,
            "time_utc": times,
            "utc_ambiguous": False,
            "high": [value + 0.5 for value in typical],
            "low": [value - 0.5 for value in typical],
            "close": typical,
            "tick_volume": 100,
        }
    )
    frame.loc[20, "tick_volume"] = 400
    frame.loc[35, "tick_volume"] = 400
    return frame


def test_mfi_reentry_emits_symmetric_closed_bar_events() -> None:
    events, report = MODULE.analyze_frame(synthetic_frame())

    assert [row["direction"] for row in events] == ["LONG", "SHORT"]
    assert events[0]["source_bar_time_utc"] == "2018-01-01T01:40:00Z"
    assert events[0]["decision_time_utc"] == "2018-01-01T01:45:00Z"
    assert events[0]["prior_mfi14"] <= 20 < events[0]["mfi14"]
    assert events[1]["prior_mfi14"] >= 80 > events[1]["mfi14"]
    assert report["funnel"]["events"] == 2


def test_exact_mfi_formula_uses_typical_price_times_tick_volume() -> None:
    frame = synthetic_frame()
    _, mfi, positive14, negative14 = MODULE.calculate_mfi(frame)

    expected_positive = ((frame.loc[20, "high"] + frame.loc[20, "low"] + frame.loc[20, "close"]) / 3) * 400
    assert positive14.loc[20] == pytest.approx(expected_positive)
    assert negative14.loc[20] > 0
    expected_mfi = 100 - 100 / (1 + positive14.loc[20] / negative14.loc[20])
    assert mfi.loc[20] == pytest.approx(expected_mfi)


@pytest.mark.parametrize("invalid_index", [5, 19])
def test_any_invalid_event_lookback_input_rejects_long_event(invalid_index: int) -> None:
    frame = synthetic_frame()
    frame.loc[invalid_index, "tick_volume"] = 0
    events, _ = MODULE.analyze_frame(frame)

    assert not any(row["source_bar_time_utc"] == "2018-01-01T01:40:00Z" for row in events)


def test_exact_next_timestamp_gap_rejects_event_without_next_price() -> None:
    frame = synthetic_frame()
    frame.loc[21:, "time_utc"] = frame.loc[21:, "time_utc"] + pd.Timedelta(minutes=5)
    events, _ = MODULE.analyze_frame(frame)

    assert [row["direction"] for row in events] == ["SHORT"]


def test_ledger_has_no_price_or_economic_outcome_fields() -> None:
    events, report = MODULE.analyze_frame(synthetic_frame())
    MODULE.assert_outcome_blind(events, report)
    keys = {key for row in events for key in row}

    assert not {"open", "high", "low", "close", "spread", "profit", "return"} & keys


def test_outputs_are_byte_deterministic() -> None:
    events_a, report_a = MODULE.analyze_frame(synthetic_frame())
    events_b, report_b = MODULE.analyze_frame(synthetic_frame())

    assert MODULE.jsonl_bytes(events_a) == MODULE.jsonl_bytes(events_b)
    assert MODULE.json_bytes(report_a) == MODULE.json_bytes(report_b)


def test_selected_frame_rejects_materialized_sealed_row_and_null_symbol() -> None:
    frame = synthetic_frame()
    frame.loc[44, "time_utc"] = pd.Timestamp("2023-01-01T00:00:00Z")
    original = MODULE.MIN_ROWS
    MODULE.MIN_ROWS = 1
    try:
        with pytest.raises(ValueError, match="outside the frozen design window"):
            MODULE.validate_selected_frame(frame)
        frame.loc[44, "time_utc"] = pd.Timestamp("2018-01-01T03:40:00Z")
        frame.loc[10, "symbol"] = None
        with pytest.raises(ValueError, match="exclusively XAUUSD"):
            MODULE.validate_selected_frame(frame)
    finally:
        MODULE.MIN_ROWS = original


def test_registry_authority_requires_explicit_unconsumed_source_permission(tmp_path: Path) -> None:
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

