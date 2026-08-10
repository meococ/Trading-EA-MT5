from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_bwaf_m5_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_bwaf_m5_source", MODULE_PATH)
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


def bull_fixture(count: int = 30) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    frame = design_frame(count)
    frame["high"] = 5.0
    frame["low"] = 1.0
    frame["close"] = 3.0
    frame.loc[5, "high"] = 10.0
    frame.loc[8, "high"] = 11.0
    slope = np.arange(count, dtype=float) * 0.1
    return frame, 1.0 + slope, 2.0 + slope, 3.0 + slope


def bear_fixture(count: int = 30) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    frame = design_frame(count)
    frame["high"] = 20.0
    frame["low"] = 15.0
    frame["close"] = 17.0
    frame.loc[5, "low"] = 10.0
    frame.loc[8, "low"] = 9.0
    slope = np.arange(count, dtype=float) * 0.1
    return frame, 13.0 - slope, 12.0 - slope, 11.0 - slope


def test_harness_dependency_and_m5_manifest_are_exact() -> None:
    assert MODULE.sha256_file(MODULE.HARNESS_PATH) == MODULE.HARNESS_SHA256
    manifest = json.loads((MODULE.ROOT / MODULE.MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet")]
    assert len(matches) == 1 and matches[0]["sha256"] == MODULE.DATA_SHA256


def test_smma_is_sma_seeded_then_recursive() -> None:
    values = np.arange(1.0, 8.0)
    result = MODULE.smma(values, 3)
    assert np.isnan(result[:2]).all()
    assert result[2] == 2.0
    assert result[3] == pytest.approx((2.0 * 2.0 + 4.0) / 3.0)
    assert result[4] == pytest.approx((2.0 * result[3] + 5.0) / 3.0)


def test_alligator_uses_older_raw_values_for_positive_plot_shift() -> None:
    median = np.arange(1.0, 60.0)
    jaw, teeth, lips = MODULE.calculate_alligator(median + 1.0, median - 1.0)
    raw_jaw = MODULE.smma(median, 13)
    raw_teeth = MODULE.smma(median, 8)
    raw_lips = MODULE.smma(median, 5)
    assert np.isnan(jaw[:20]).all() and jaw[20] == raw_jaw[12]
    assert np.isnan(teeth[:12]).all() and teeth[12] == raw_teeth[7]
    assert np.isnan(lips[:7]).all() and lips[7] == raw_lips[4]
    assert MODULE.FIRST_ALIGNMENT_INDEX == 21


def test_strict_fractal_rejects_any_tie() -> None:
    high = np.array([1.0, 2.0, 5.0, 5.0, 1.0])
    low = np.array([5.0, 4.0, 1.0, 1.0, 5.0])
    assert not MODULE.strict_upper_fractal(high, 2)
    assert not MODULE.strict_lower_fractal(low, 2)


def test_bull_regime_uses_confirmed_fractal_then_later_breakout_once() -> None:
    frame, jaw, teeth, lips = bull_fixture()
    rows = MODULE.raw_signals(frame, jaw, teeth, lips)
    assert len(rows) == 1
    assert rows[0]["direction"] == "LONG"
    assert rows[0]["pivot"] == 5 and rows[0]["confirmation"] == 7 and rows[0]["_index"] == 8
    assert rows[0]["anchor_price"] == 10.0 and rows[0]["breakout_extreme"] == 11.0


def test_bear_regime_is_exact_symmetric() -> None:
    frame, jaw, teeth, lips = bear_fixture()
    rows = MODULE.raw_signals(frame, jaw, teeth, lips)
    assert len(rows) == 1
    assert rows[0]["direction"] == "SHORT"
    assert rows[0]["pivot"] == 5 and rows[0]["confirmation"] == 7 and rows[0]["_index"] == 8


def test_broken_mouth_clears_anchor_and_requires_fresh_regime() -> None:
    frame, jaw, teeth, lips = bull_fixture()
    lips[8] = teeth[8]
    rows = MODULE.raw_signals(frame, jaw, teeth, lips)
    assert rows == []


def test_pivot_before_regime_start_is_not_reused() -> None:
    frame, jaw, teeth, lips = bull_fixture()
    jaw[:7] = np.nan
    teeth[:7] = np.nan
    lips[:7] = np.nan
    rows = MODULE.raw_signals(frame, jaw, teeth, lips)
    assert rows == []


def test_analyze_emits_exact_outcome_blind_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    frame, jaw, teeth, lips = bull_fixture()
    monkeypatch.setattr(MODULE, "calculate_alligator", lambda high, low: (jaw, teeth, lips))
    events, report = MODULE.analyze_frame(frame)
    assert len(events) == 1 and events[0]["direction"] == "LONG"
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert events[0]["fractal_confirmation_index"] == events[0]["fractal_pivot_index"] + 2
    assert events[0]["decision_source_epoch"] == events[0]["source_bar_source_epoch"] + 300
    assert report["funnel"]["raw_events"] == 1
    MODULE.assert_outcome_blind(events, report)


def test_gap_inside_fractal_window_preserves_physical_bar_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    frame, jaw, teeth, lips = bull_fixture()
    frame.loc[6:, "time_utc"] += pd.Timedelta(minutes=5)
    frame.loc[6:, "source_epoch"] += 300
    monkeypatch.setattr(MODULE, "calculate_alligator", lambda high, low: (jaw, teeth, lips))
    events, report = MODULE.analyze_frame(frame)
    assert len(events) == 1
    pivot = pd.Timestamp(events[0]["fractal_pivot_time_utc"])
    confirmation = pd.Timestamp(events[0]["fractal_confirmation_time_utc"])
    assert confirmation - pivot == pd.Timedelta(minutes=15)
    assert events[0]["fractal_confirmation_index"] == events[0]["fractal_pivot_index"] + 2
    MODULE.assert_outcome_blind(events, report)


def test_raw_gap_event_is_consumed_without_delayed_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    frame, jaw, teeth, lips = bull_fixture()
    frame.loc[9:, "time_utc"] += pd.Timedelta(minutes=5)
    frame.loc[9:, "source_epoch"] += 300
    monkeypatch.setattr(MODULE, "calculate_alligator", lambda high, low: (jaw, teeth, lips))
    events, report = MODULE.analyze_frame(frame)
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_outcome_blind_predicate_rejects_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    frame, jaw, teeth, lips = bull_fixture()
    monkeypatch.setattr(MODULE, "calculate_alligator", lambda high, low: (jaw, teeth, lips))
    events, report = MODULE.analyze_frame(frame)
    invalid = dict(events[0], next_close=100.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], breakout_extreme=events[0]["anchor_price"])
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)


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
        validation.pop("native_ialligator_parity_authorized")
    elif mutation == "native_true":
        validation["native_ifractals_parity_authorized"] = True
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
