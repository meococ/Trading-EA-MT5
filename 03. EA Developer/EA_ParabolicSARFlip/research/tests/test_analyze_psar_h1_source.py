from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_psar_h1_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_psar_h1_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_frame(count: int = 20) -> pd.DataFrame:
    times = pd.date_range(MODULE.SOURCE_START, periods=count, freq="1h")
    epochs = 1_086_937_200 + np.arange(count, dtype=np.int64) * 3600
    close = 100.0 + np.arange(count, dtype=float)
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False, "high": close + 1.0, "low": close - 1.0, "close": close})


def design_frame(gap_after: int | None = None) -> pd.DataFrame:
    frame = source_frame(8)
    frame["time_utc"] = pd.date_range(MODULE.DESIGN_START, periods=len(frame), freq="1h")
    frame["source_epoch"] = 1_514_764_800 + np.arange(len(frame), dtype=np.int64) * 3600
    frame.loc[:, ["high", "low", "close"]] = np.array([
        [12.0, 10.0, 11.0], [11.0, 9.0, 10.0], [13.0, 8.0, 12.0],
        [14.0, 11.0, 13.0], [15.0, 12.0, 14.0], [16.0, 13.0, 15.0],
        [17.0, 14.0, 16.0], [18.0, 15.0, 17.0],
    ])
    if gap_after is not None:
        frame.loc[gap_after + 1 :, "time_utc"] += pd.Timedelta(hours=1)
        frame.loc[gap_after + 1 :, "source_epoch"] += 3600
    return frame


def test_harness_dependency_and_h1_manifest_are_exact() -> None:
    assert MODULE.sha256_file(MODULE.HARNESS_PATH) == MODULE.HARNESS_SHA256
    manifest = json.loads((MODULE.ROOT / MODULE.MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")]
    assert len(matches) == 1 and matches[0]["sha256"] == MODULE.DATA_SHA256


def test_initial_up_state_uses_first_low_and_second_high() -> None:
    state = MODULE.calculate_psar(np.array([11.0, 12.0]), np.array([9.0, 10.0]), np.array([10.0, 11.0]))
    assert np.isnan(state["sar"][0])
    assert state["direction"][1] == 1 and state["sar"][1] == 9.0
    assert state["ep"][1] == 12.0 and state["af"][1] == MODULE.STEP
    assert not state["long_event"].any() and not state["short_event"].any()


def test_initial_close_equality_is_frozen_down() -> None:
    state = MODULE.calculate_psar(np.array([11.0, 12.0]), np.array([9.0, 10.0]), np.array([10.0, 10.0]))
    assert state["direction"][1] == -1 and state["sar"][1] == 11.0
    assert state["ep"][1] == 10.0


def test_uptrend_no_reversal_clamps_then_updates_ep_and_af() -> None:
    state = MODULE.calculate_psar(np.array([10.0, 11.0, 12.0]), np.array([8.0, 9.0, 10.0]), np.array([9.0, 10.0, 11.0]))
    assert state["candidate"][2] == pytest.approx(8.06)
    assert state["sar"][2] == 8.0
    assert state["direction"][2] == 1 and state["ep"][2] == 12.0
    assert state["af"][2] == pytest.approx(0.04)


def test_penetration_is_checked_before_prior_bar_clamp() -> None:
    state = MODULE.calculate_psar(np.array([10.0, 11.0, 11.5]), np.array([8.0, 9.0, 8.0]), np.array([9.0, 10.0, 9.0]))
    assert state["candidate"][2] == pytest.approx(8.06)
    assert state["short_event"][2] and state["direction"][2] == -1
    assert state["sar"][2] == 11.0


def test_penetration_equality_does_not_reverse() -> None:
    state = MODULE.calculate_psar(np.array([10.0, 11.0, 11.5]), np.array([8.0, 9.0, 8.06]), np.array([9.0, 10.0, 9.5]))
    assert not state["short_event"][2] and state["direction"][2] == 1


def test_downtrend_reversal_is_strict_symmetric() -> None:
    state = MODULE.calculate_psar(np.array([12.0, 11.0, 13.0]), np.array([10.0, 9.0, 8.0]), np.array([11.0, 10.0, 12.0]))
    assert state["candidate"][2] == pytest.approx(11.94)
    assert state["long_event"][2] and state["direction"][2] == 1
    assert state["sar"][2] == 9.0


def test_acceleration_factor_never_exceeds_maximum() -> None:
    close = np.arange(30, dtype=float) + 100.0
    state = MODULE.calculate_psar(close + 1.0, close - 1.0, close)
    assert np.nanmax(state["af"]) == pytest.approx(MODULE.MAXIMUM)
    assert np.all(state["af"][np.isfinite(state["af"])] <= MODULE.MAXIMUM)


def test_analyze_emits_exact_fields_and_reversal_predicate() -> None:
    events, report = MODULE.analyze_frame(design_frame())
    assert len(events) == 1 and events[0]["direction"] == "LONG"
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert report["funnel"]["raw_events"] == 1
    MODULE.assert_outcome_blind(events, report)


def test_raw_gap_event_is_consumed() -> None:
    events, report = MODULE.analyze_frame(design_frame(gap_after=2))
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_flat_bar_is_valid_geometry() -> None:
    frame = source_frame()
    frame.loc[8, ["high", "low", "close"]] = 120.0
    validated = MODULE.validate_frame(frame)
    assert validated.loc[8, "high"] == validated.loc[8, "low"] == validated.loc[8, "close"]


@pytest.mark.parametrize("column", ["symbol", "timeframe"])
def test_null_identity_fails_closed(column: str) -> None:
    frame = source_frame(); frame.loc[1, column] = None
    with pytest.raises(ValueError, match="XAUUSD/H1"):
        MODULE.validate_frame(frame)


def test_outcome_blind_allowlist_and_predicate_reject_mutation() -> None:
    events, report = MODULE.analyze_frame(design_frame())
    invalid = dict(events[0], next_close=100.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], candidate_sar=invalid["trigger_extreme"] + 1.0)
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)


def authority_row() -> dict[str, object]:
    validation = {name: False for name in MODULE.FALSE_PERMISSIONS}
    validation.update({
        "source_feasibility_attempt_id": MODULE.ATTEMPT_ID, "source_feasibility_attempt_limit": 1,
        "source_run_authorized": True, "source_feasibility_only": True, "prehistory_source_access_authorized": True,
        "prehistory_source_start": MODULE.SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest_path": MODULE.MANIFEST_RELATIVE_PATH, "manifest_sha256": MODULE.MANIFEST_SHA256,
        "data_path": MODULE.DATA_RELATIVE_PATH, "data_sha256": MODULE.DATA_SHA256, "data_access_predicate": MODULE.DATA_ACCESS_PREDICATE,
        "reviewed_analyzer_path": MODULE.ANALYZER_RELATIVE_PATH, "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
        "reviewed_test_path": MODULE.TEST_RELATIVE_PATH, "reviewed_test_sha256": MODULE.TEST_SHA256,
        "harness_dependency_path": MODULE.HARNESS_RELATIVE_PATH, "harness_dependency_sha256": MODULE.HARNESS_SHA256,
    })
    metrics = {name: 0 for name in MODULE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    return {"hypothesis_id": MODULE.HYPOTHESIS_ID, "state": "probe", "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN", "prereg_sha256": MODULE.PREREG_SHA256, "run_ids": [], "metrics": metrics, "validation": validation}


@pytest.mark.parametrize("mutation", ["missing_native", "native_true", "attempt", "harness", "source_metric", "holdout"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    row = authority_row(); validation = row["validation"]; metrics = row["metrics"]
    assert isinstance(validation, dict) and isinstance(metrics, dict)
    if mutation == "missing_native": validation.pop("native_isar_parity_authorized")
    elif mutation == "native_true": validation["native_isar_parity_authorized"] = True
    elif mutation == "attempt": validation["source_feasibility_attempt_id"] = "WRONG"
    elif mutation == "harness": validation["harness_dependency_sha256"] = "0" * 64
    elif mutation == "source_metric": metrics["source_runs_executed"] = 1
    else: metrics["research_holdout_opened"] = True
    registry = tmp_path / "registry.jsonl"; registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="authority"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_and_frozen_rehash_are_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64, "analyzer_sha256": "C" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
    frozen = tmp_path / "frozen.bin"; frozen.write_bytes(b"frozen"); expected = {"frozen": MODULE.sha256_file(frozen)}
    assert MODULE.verify_frozen_inputs({"frozen": frozen}, expected) == expected
    frozen.write_bytes(b"drift")
    with pytest.raises(ValueError, match="frozen"):
        MODULE.verify_frozen_inputs({"frozen": frozen}, expected)
