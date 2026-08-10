from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_aroon_m15_source_v2.py"
SPEC = importlib.util.spec_from_file_location("analyze_aroon_m15_source_v2", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.BASE


def m5_frame(groups: int = 10, start: pd.Timestamp = BASE.SOURCE_START) -> pd.DataFrame:
    count = groups * 3
    times = pd.date_range(start, periods=count, freq="5min")
    source_start = 1_086_938_100
    epochs = source_start + np.arange(count, dtype=np.int64) * 300
    center = 100.0 + np.sin(np.arange(count, dtype=float) / 7.0)
    return pd.DataFrame(
        {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "source_epoch": epochs,
            "time_utc": times,
            "utc_ambiguous": False,
            "high": center + 1.0,
            "low": center - 1.0,
            "close": center,
        }
    )


def assert_equivalent(raw: pd.DataFrame) -> None:
    expected = BASE.aggregate_m15(raw)
    actual = MODULE.aggregate_m15_vectorized(raw)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, check_exact=True)


def test_complete_triplets_are_byte_semantically_equivalent() -> None:
    assert_equivalent(m5_frame(20))


@pytest.mark.parametrize("offset", [0, 300, 600])
def test_missing_each_offset_matches_legacy_and_retains_invalid_bucket(offset: int) -> None:
    raw = m5_frame(4)
    second_bucket = int(raw.at[3, "source_epoch"] // 900 * 900)
    raw = raw.loc[raw["source_epoch"] != second_bucket + offset].reset_index(drop=True)
    assert_equivalent(raw)
    result = MODULE.aggregate_m15_vectorized(raw)
    assert len(result) == 4
    assert not bool(result.at[1, "complete"])


def test_missing_inception_offset_zero_is_symmetric_fail_closed() -> None:
    raw = m5_frame(4).drop(index=0).reset_index(drop=True)
    with pytest.raises(ValueError, match="inception"):
        BASE.aggregate_m15(raw)
    with pytest.raises(ValueError, match="inception"):
        MODULE.aggregate_m15_vectorized(raw)


def test_duplicate_and_extra_offsets_match_legacy() -> None:
    raw = m5_frame(4)
    duplicate = raw.iloc[[1]].copy()
    extra = raw.iloc[[2]].copy()
    extra["source_epoch"] = int(raw.at[0, "source_epoch"]) + 100
    extra["time_utc"] = raw.at[0, "time_utc"] + pd.Timedelta(seconds=100)
    mutated = pd.concat([raw, duplicate, extra], ignore_index=True).sort_values(["source_epoch", "time_utc"], kind="stable").reset_index(drop=True)
    assert_equivalent(mutated)
    assert not bool(MODULE.aggregate_m15_vectorized(mutated).at[0, "complete"])


def test_utc_gap_and_missing_offset_zero_match_legacy() -> None:
    raw = m5_frame(5)
    raw.loc[1, "time_utc"] = raw.loc[1, "time_utc"] + pd.Timedelta(minutes=1)
    raw = raw.drop(index=3).reset_index(drop=True)
    assert_equivalent(raw)
    result = MODULE.aggregate_m15_vectorized(raw)
    assert not bool(result.at[0, "complete"])
    assert not bool(result.at[1, "complete"])


@pytest.mark.parametrize("mutation", ["nan", "inverted", "outside_close", "nonpositive_close"])
def test_invalid_geometry_matches_legacy(mutation: str) -> None:
    raw = m5_frame(4)
    if mutation == "nan":
        raw.loc[1, "high"] = np.nan
    elif mutation == "inverted":
        raw.loc[1, "high"] = raw.loc[1, "low"] - 1.0
    elif mutation == "outside_close":
        raw.loc[1, "close"] = raw.loc[1, "high"] + 1.0
    else:
        raw.loc[1, "low"] = -2.0
        raw.loc[1, "close"] = 0.0
    assert_equivalent(raw)


def test_market_closure_does_not_synthesize_buckets() -> None:
    raw = m5_frame(8)
    removed_bucket = int(raw.at[6, "source_epoch"] // 900 * 900)
    raw = raw.loc[(raw["source_epoch"] // 900 * 900) != removed_bucket].reset_index(drop=True)
    assert_equivalent(raw)
    result = MODULE.aggregate_m15_vectorized(raw)
    assert removed_bucket not in set(result["source_epoch"])
    assert len(result) == 7


def test_design_window_boundaries_are_half_open() -> None:
    times = pd.to_datetime(
        [
            "2017-12-31T23:45:00Z",
            "2018-01-01T00:00:00Z",
            "2022-12-31T23:45:00Z",
            "2023-01-01T00:00:00Z",
        ],
        utc=True,
    )
    design = (times >= BASE.DESIGN_START) & (times < BASE.DESIGN_END)
    assert design.tolist() == [False, True, True, False]


def test_large_vectorized_aggregation_meets_source_scale() -> None:
    raw = m5_frame(100_000)
    started = time.perf_counter()
    result = MODULE.aggregate_m15_vectorized(raw)
    elapsed = time.perf_counter() - started
    assert len(result) == 100_000
    assert result["complete"].all()
    assert elapsed < 10.0


def test_formula_output_is_identical_after_vectorized_aggregation() -> None:
    raw = m5_frame(100)
    legacy = BASE.aggregate_m15(raw)
    vector = MODULE.aggregate_m15_vectorized(raw)
    BASE.HYPOTHESIS_ID = MODULE.HYPOTHESIS_ID
    BASE.ATTEMPT_ID = MODULE.ATTEMPT_ID
    legacy_events, legacy_report = BASE.analyze_frame(legacy)
    vector_events, vector_report = BASE.analyze_frame(vector)
    assert BASE.jsonl_bytes(legacy_events) == BASE.jsonl_bytes(vector_events)
    assert BASE.json_bytes(legacy_report) == BASE.json_bytes(vector_report)


def authority_rows(monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, object], dict[str, object]]:
    parent = {
        "hypothesis_id": MODULE.PARENT_HYPOTHESIS_ID,
        "state": "parked",
        "verdict": "PARK_ENGINEERING_TIMEOUT_BEFORE_SOURCE_REPORT_NO_ECONOMIC_VERDICT",
    }
    parent_raw = json.dumps(parent, separators=(",", ":")).encode()
    monkeypatch.setattr(MODULE, "PARENT_TERMINAL_ROW_SHA256", hashlib.sha256(parent_raw).hexdigest().upper())
    validation = {name: False for name in BASE.FALSE_PERMISSIONS}
    validation.update(
        {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
            "source_feasibility_attempt_limit": 1,
            "source_run_authorized": True,
            "source_feasibility_only": True,
            "prehistory_source_access_authorized": True,
            "prehistory_source_start": BASE.SOURCE_START.isoformat().replace("+00:00", "Z"),
            "manifest_path": BASE.MANIFEST_RELATIVE_PATH,
            "manifest_sha256": BASE.MANIFEST_SHA256,
            "data_path": BASE.DATA_RELATIVE_PATH,
            "data_sha256": BASE.DATA_SHA256,
            "data_access_predicate": BASE.DATA_ACCESS_PREDICATE,
            "reviewed_analyzer_path": MODULE.ANALYZER_RELATIVE_PATH,
            "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
            "reviewed_test_path": MODULE.TEST_RELATIVE_PATH,
            "reviewed_test_sha256": MODULE.TEST_SHA256,
            "formula_dependency_path": BASE.ANALYZER_RELATIVE_PATH,
            "formula_dependency_sha256": MODULE.BASE_SHA256,
            "parent_terminal_row_sha256": MODULE.PARENT_TERMINAL_ROW_SHA256,
            "parent_attempt_started_sha256": MODULE.PARENT_START_SHA256,
            "parent_failure_sha256": MODULE.PARENT_FAILURE_SHA256,
            "parent_post_failure_review_sha256": MODULE.PARENT_REVIEW_SHA256,
            "aggregation_semantic_diff_sha256": MODULE.SEMANTIC_DIFF_SHA256,
        }
    )
    metrics = {name: 0 for name in BASE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    current = {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "parent_candidate": MODULE.PARENT_HYPOTHESIS_ID,
        "state": "probe",
        "verdict": "FROZEN_VECTORIZED_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.PREREG_SHA256,
        "run_ids": [],
        "metrics": metrics,
        "validation": validation,
    }
    return parent, current


@pytest.mark.parametrize("mutation", ["missing_native", "native_true", "parent_hash", "formula_hash", "semantic_diff"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent, current = authority_rows(monkeypatch)
    validation = current["validation"]
    assert isinstance(validation, dict)
    if mutation == "missing_native":
        validation.pop("native_iaroon_claim_authorized")
    elif mutation == "native_true":
        validation["native_iaroon_claim_authorized"] = True
    elif mutation == "parent_hash":
        validation["parent_terminal_row_sha256"] = "0" * 64
    elif mutation == "formula_hash":
        validation["formula_dependency_sha256"] = "0" * 64
    else:
        validation["aggregation_semantic_diff_sha256"] = "0" * 64
    registry = tmp_path / "registry.jsonl"
    registry.write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in (parent, current)) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_and_phase_artifacts_are_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64, "parent_terminal_row_sha256": "C" * 64}
    started, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    phase_path = MODULE.phase(tmp_path / "attempt", 2, "hash_schema_verified", started, rows=0)
    assert marker.exists() and phase_path.exists()
    with pytest.raises(ValueError, match="already"):
        MODULE.phase(tmp_path / "attempt", 2, "hash_schema_verified", started, rows=0)
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)


def test_bound_input_mutation_fails_final_rehash_and_can_terminalize(tmp_path: Path) -> None:
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"frozen-first")
    second.write_bytes(b"frozen-second")
    paths = {"first": first, "second": second}
    expected = {name: MODULE.sha256_file(path) for name, path in paths.items()}
    assert MODULE.verify_frozen_inputs(paths, expected) == expected
    second.write_bytes(b"mutated-second")
    with pytest.raises(ValueError, match="second") as error:
        MODULE.verify_frozen_inputs(paths, expected)
    terminal = tmp_path / "attempt_terminal.json"
    MODULE.exclusive_json(
        terminal,
        {
            "schema_version": "aroon002_source_attempt_terminal.v1",
            "hypothesis_id": MODULE.HYPOTHESIS_ID,
            "attempt_id": MODULE.ATTEMPT_ID,
            "status": "FAILED",
            "error": str(error.value),
            "same_id_retry_authorized": False,
        },
    )
    payload = json.loads(terminal.read_text(encoding="utf-8"))
    assert payload["status"] == "FAILED"
    assert payload["same_id_retry_authorized"] is False
