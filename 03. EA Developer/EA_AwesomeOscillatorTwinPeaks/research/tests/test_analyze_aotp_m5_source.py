from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_aotp_m5_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_aotp_m5_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_frame(count: int = 50) -> pd.DataFrame:
    times = pd.date_range(MODULE.SOURCE_START, periods=count, freq="5min")
    epochs = 1_086_938_100 + np.arange(count, dtype=np.int64) * 300
    median = 120.0 + np.arange(count, dtype=float) * 0.1
    return pd.DataFrame({
        "symbol": "XAUUSD", "timeframe": "M5", "source_epoch": epochs,
        "time_utc": times, "utc_ambiguous": False,
        "high": median + 1.0, "low": median - 1.0, "close": median,
    })


def design_frame(count: int = 50, gap_after: int | None = None) -> pd.DataFrame:
    frame = source_frame(count)
    frame["time_utc"] = pd.date_range(MODULE.DESIGN_START, periods=count, freq="5min")
    frame["source_epoch"] = 1_514_764_800 + np.arange(count, dtype=np.int64) * 300
    if gap_after is not None:
        frame.loc[gap_after + 1 :, "time_utc"] += pd.Timedelta(minutes=5)
        frame.loc[gap_after + 1 :, "source_epoch"] += 300
    return frame


def twin_peaks_ao(count: int = 50) -> np.ndarray:
    values = np.full(count, -1.0, dtype=float)
    values[:33] = np.nan
    values[33:38] = [-1.0, -3.0, -2.0, -2.5, -2.0]
    return values


def test_harness_dependency_and_m5_manifest_are_exact() -> None:
    assert MODULE.sha256_file(MODULE.HARNESS_PATH) == MODULE.HARNESS_SHA256
    manifest = json.loads((MODULE.ROOT / MODULE.MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet")]
    assert len(matches) == 1 and matches[0]["sha256"] == MODULE.DATA_SHA256


def test_ao_is_exact_sma5_minus_sma34_of_median_price() -> None:
    median = np.arange(60, dtype=float) + 100.0
    ao = MODULE.calculate_ao(median + 2.0, median - 2.0)
    assert np.isnan(ao[:33]).all()
    assert np.allclose(ao[33:], 14.5)


def test_bullish_twin_peaks_first_anchor_then_higher_valley() -> None:
    ao = np.array([-1.0, -3.0, -2.0, -2.5, -2.0])
    longs, shorts, anchors, pivots = MODULE.twin_peak_events(ao)
    assert np.flatnonzero(longs).tolist() == [4]
    assert not shorts.any()
    assert anchors[4] == -3.0 and pivots[4] == -2.5


def test_bearish_twin_peaks_is_strict_symmetric() -> None:
    ao = np.array([1.0, 3.0, 2.0, 2.5, 2.0])
    longs, shorts, anchors, pivots = MODULE.twin_peak_events(ao)
    assert not longs.any()
    assert np.flatnonzero(shorts).tolist() == [4]
    assert anchors[4] == 3.0 and pivots[4] == 2.5


def test_equal_second_peak_never_signals() -> None:
    ao = np.array([-1.0, -3.0, -2.0, -3.0, -2.0])
    longs, shorts, _, _ = MODULE.twin_peak_events(ao)
    assert not longs.any() and not shorts.any()


@pytest.mark.parametrize("separator", [0.0, np.nan])
def test_zero_or_invalid_value_resets_both_chains(separator: float) -> None:
    ao = np.array([-1.0, -3.0, -2.0, separator, -1.0, -2.5, -2.0])
    longs, shorts, _, _ = MODULE.twin_peak_events(ao)
    assert not longs.any() and not shorts.any()


def test_first_mathematically_possible_event_is_index_37() -> None:
    ao = twin_peaks_ao()
    longs, _, _, _ = MODULE.twin_peak_events(ao)
    assert np.flatnonzero(longs).tolist() == [37]
    assert MODULE.FIRST_EVENT_INDEX == 37


def test_analyze_emits_exact_fields_and_predicate(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_frame()
    monkeypatch.setattr(MODULE, "calculate_ao", lambda high, low: twin_peaks_ao(len(high)))
    events, report = MODULE.analyze_frame(frame)
    assert len(events) == 1 and events[0]["direction"] == "LONG"
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert report["funnel"]["raw_events"] == 1
    MODULE.assert_outcome_blind(events, report)


def test_raw_gap_event_is_consumed_but_pivot_state_is_not_delayed(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_frame(gap_after=37)
    monkeypatch.setattr(MODULE, "calculate_ao", lambda high, low: twin_peaks_ao(len(high)))
    events, report = MODULE.analyze_frame(frame)
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_flat_bar_is_valid_geometry() -> None:
    frame = source_frame()
    frame.loc[8, ["high", "low", "close"]] = 120.0
    validated = MODULE.validate_frame(frame)
    assert validated.loc[8, "high"] == validated.loc[8, "low"] == validated.loc[8, "close"]


@pytest.mark.parametrize("mutation", ["null_symbol", "null_timeframe", "inverted", "outside_close", "nonfinite"])
def test_source_identity_and_geometry_fail_closed(mutation: str) -> None:
    frame = source_frame()
    if mutation == "null_symbol":
        frame.loc[1, "symbol"] = None
    elif mutation == "null_timeframe":
        frame.loc[1, "timeframe"] = None
    elif mutation == "inverted":
        frame.loc[1, "high"] = frame.loc[1, "low"] - 1.0
    elif mutation == "outside_close":
        frame.loc[1, "close"] = frame.loc[1, "high"] + 1.0
    else:
        frame.loc[1, "low"] = np.nan
    with pytest.raises(ValueError):
        MODULE.validate_frame(frame)


def test_outcome_blind_allowlist_and_predicate_reject_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_frame()
    monkeypatch.setattr(MODULE, "calculate_ao", lambda high, low: twin_peaks_ao(len(high)))
    events, report = MODULE.analyze_frame(frame)
    invalid = dict(events[0], next_close=100.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], pivot_ao=-4.0)
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)


def authority_row() -> dict[str, object]:
    validation = {name: False for name in MODULE.FALSE_PERMISSIONS}
    validation.update({
        "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
        "source_feasibility_attempt_limit": 1,
        "source_run_authorized": True,
        "source_feasibility_only": True,
        "prehistory_source_access_authorized": True,
        "prehistory_source_start": MODULE.SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest_path": MODULE.MANIFEST_RELATIVE_PATH,
        "manifest_sha256": MODULE.MANIFEST_SHA256,
        "data_path": MODULE.DATA_RELATIVE_PATH,
        "data_sha256": MODULE.DATA_SHA256,
        "data_access_predicate": MODULE.DATA_ACCESS_PREDICATE,
        "reviewed_analyzer_path": MODULE.ANALYZER_RELATIVE_PATH,
        "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
        "reviewed_test_path": MODULE.TEST_RELATIVE_PATH,
        "reviewed_test_sha256": MODULE.TEST_SHA256,
        "harness_dependency_path": MODULE.HARNESS_RELATIVE_PATH,
        "harness_dependency_sha256": MODULE.HARNESS_SHA256,
    })
    metrics = {name: 0 for name in MODULE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    return {"hypothesis_id": MODULE.HYPOTHESIS_ID, "state": "probe", "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN", "prereg_sha256": MODULE.PREREG_SHA256, "run_ids": [], "metrics": metrics, "validation": validation}


@pytest.mark.parametrize("mutation", ["missing_native", "native_true", "attempt", "harness", "source_metric", "holdout"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    row = authority_row()
    validation = row["validation"]
    metrics = row["metrics"]
    assert isinstance(validation, dict) and isinstance(metrics, dict)
    if mutation == "missing_native":
        validation.pop("native_iao_parity_authorized")
    elif mutation == "native_true":
        validation["native_iao_parity_authorized"] = True
    elif mutation == "attempt":
        validation["source_feasibility_attempt_id"] = "WRONG"
    elif mutation == "harness":
        validation["harness_dependency_sha256"] = "0" * 64
    elif mutation == "source_metric":
        metrics["source_runs_executed"] = 1
    else:
        metrics["research_holdout_opened"] = True
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="authority"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_and_frozen_rehash_are_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64, "analyzer_sha256": "C" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)
    frozen = tmp_path / "frozen.bin"
    frozen.write_bytes(b"frozen")
    expected = {"frozen": MODULE.sha256_file(frozen)}
    assert MODULE.verify_frozen_inputs({"frozen": frozen}, expected) == expected
    frozen.write_bytes(b"drift")
    with pytest.raises(ValueError, match="frozen"):
        MODULE.verify_frozen_inputs({"frozen": frozen}, expected)
