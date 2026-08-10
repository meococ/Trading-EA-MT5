from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_wpr_h1_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_wpr_h1_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_frozen_h1_identity_matches_unique_manifest_entry_without_opening_parquet() -> None:
    root = Path(__file__).resolve().parents[4]
    manifest_path = root / MODULE.MANIFEST_RELATIVE_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [
        item
        for item in manifest.get("files", [])
        if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")
    ]
    assert len(matches) == 1
    assert matches[0]["sha256"] == MODULE.DATA_SHA256
    assert MODULE.DATA_RELATIVE_PATH.endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")


def source_frame(count: int = 40) -> pd.DataFrame:
    times = pd.date_range(MODULE.SOURCE_START, periods=count, freq="1h")
    epochs = 1_086_937_200 + np.arange(count, dtype=np.int64) * 3600
    center = 100.0 + np.arange(count, dtype=float) * 0.1
    return pd.DataFrame(
        {
            "symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False,
            "high": center + 1.0, "low": center - 1.0, "close": center,
        }
    )


def design_frame(values: list[float], gap_after: int | None = None) -> pd.DataFrame:
    count = len(values)
    times = pd.date_range(MODULE.DESIGN_START, periods=count, freq="1h")
    epochs = 1_514_764_800 + np.arange(count, dtype=np.int64) * 3600
    if gap_after is not None:
        times = pd.DatetimeIndex([value + (pd.Timedelta(hours=1) if index > gap_after else pd.Timedelta(0)) for index, value in enumerate(times)])
        epochs[gap_after + 1 :] += 3600
    return pd.DataFrame(
        {
            "symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False,
            "high": np.full(count, 101.0), "low": np.full(count, 99.0), "close": np.full(count, 100.0), "_test_wpr": values,
        }
    )


def test_wpr_formula_and_warmup_are_exact() -> None:
    high = np.arange(1.0, 17.0)
    low = high - 2.0
    close = low + 0.5
    result = MODULE.calculate_wpr(high, low, close)
    assert np.isnan(result[:13]).all()
    expected = -100.0 * (high[13] - close[13]) / (high[13] - low[0])
    assert result[13] == pytest.approx(expected)


def test_flat_rolling_range_is_unavailable() -> None:
    values = np.full(20, 100.0)
    result = MODULE.calculate_wpr(values, values, values)
    assert np.isnan(result).all()


def test_close_at_high_and_low_maps_to_zero_and_minus_100() -> None:
    high = np.full(15, 110.0)
    low = np.full(15, 90.0)
    close = np.full(15, 100.0)
    close[13] = 110.0
    close[14] = 90.0
    result = MODULE.calculate_wpr(high, low, close)
    assert result[13] == pytest.approx(0.0)
    assert result[14] == pytest.approx(-100.0)


def test_first_event_requires_index_14_and_post_event_row(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [np.nan] * 13 + [-80.0, -79.0, -79.0]
    frame = design_frame(values)
    monkeypatch.setattr(MODULE, "calculate_wpr", lambda high, low, close: np.asarray(values, dtype=float))
    events, _ = MODULE.analyze_frame(frame.drop(columns="_test_wpr"))
    assert len(events) == 1 and events[0]["direction"] == "LONG"
    assert events[0]["source_bar_time_utc"] == frame.at[14, "time_utc"].isoformat().replace("+00:00", "Z")


def test_equality_arms_and_current_equality_emits_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [-80.0, -79.0, -50.0, -20.0, -20.0, -21.0, -50.0]
    frame = design_frame(values)
    monkeypatch.setattr(MODULE, "calculate_wpr", lambda high, low, close: np.asarray(values, dtype=float))
    events, report = MODULE.analyze_frame(frame.drop(columns="_test_wpr"))
    assert [row["direction"] for row in events] == ["LONG", "SHORT"]
    assert report["funnel"]["raw_events"] == 2


def test_raw_gap_event_is_consumed(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [-80.0, -79.0, -79.0]
    frame = design_frame(values, gap_after=1)
    monkeypatch.setattr(MODULE, "calculate_wpr", lambda high, low, close: np.asarray(values, dtype=float))
    events, report = MODULE.analyze_frame(frame.drop(columns="_test_wpr"))
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


def test_flat_source_bar_is_valid_geometry() -> None:
    frame = source_frame()
    frame.loc[4, ["high", "low", "close"]] = 100.0
    validated = MODULE.validate_frame(frame)
    assert validated.loc[4, "high"] == validated.loc[4, "low"] == validated.loc[4, "close"]


@pytest.mark.parametrize("mutation", ["nonfinite", "inverted", "outside"])
def test_invalid_geometry_fails_closed(mutation: str) -> None:
    frame = source_frame()
    if mutation == "nonfinite":
        frame.loc[3, "high"] = np.nan
    elif mutation == "inverted":
        frame.loc[3, "high"] = frame.loc[3, "low"] - 1.0
    else:
        frame.loc[3, "close"] = frame.loc[3, "high"] + 1.0
    with pytest.raises(ValueError, match="finite|geometry"):
        MODULE.validate_frame(frame)


@pytest.mark.parametrize("column", ["symbol", "timeframe"])
def test_null_identity_fails_closed(column: str) -> None:
    frame = source_frame()
    frame.loc[1, column] = None
    with pytest.raises(ValueError, match="XAUUSD/H1"):
        MODULE.validate_frame(frame)


def test_outcome_blind_exact_allowlist() -> None:
    row = {"hypothesis_id": MODULE.HYPOTHESIS_ID, "source_bar_time_utc": "2018-01-01T00:00:00Z", "decision_time_utc": "2018-01-01T01:00:00Z", "direction": "LONG", "prior_wpr": -80.0, "wpr": -79.0}
    report = {"prohibitions": {"post_event_ohlc_read": False, "native_iwpr_parity_authorized_by_attempt": True}}
    MODULE.assert_outcome_blind([row], report)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([dict(row, next_close=101.0)], report)


def authority_row() -> dict[str, object]:
    validation = {name: False for name in MODULE.FALSE_PERMISSIONS}
    validation.update(
        {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID, "source_feasibility_attempt_limit": 1,
            "source_run_authorized": True, "source_feasibility_only": True, "prehistory_source_access_authorized": True,
            "prehistory_source_start": MODULE.SOURCE_START.isoformat().replace("+00:00", "Z"),
            "manifest_path": MODULE.MANIFEST_RELATIVE_PATH, "manifest_sha256": MODULE.MANIFEST_SHA256,
            "data_path": MODULE.DATA_RELATIVE_PATH, "data_sha256": MODULE.DATA_SHA256, "data_access_predicate": MODULE.DATA_ACCESS_PREDICATE,
            "reviewed_analyzer_path": MODULE.ANALYZER_RELATIVE_PATH, "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH),
            "reviewed_test_path": MODULE.TEST_RELATIVE_PATH, "reviewed_test_sha256": MODULE.TEST_SHA256,
        }
    )
    metrics = {name: 0 for name in MODULE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    return {"hypothesis_id": MODULE.HYPOTHESIS_ID, "state": "probe", "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN", "prereg_sha256": MODULE.PREREG_SHA256, "run_ids": [], "metrics": metrics, "validation": validation}


@pytest.mark.parametrize("mutation", ["missing_native", "native_true", "attempt", "source_metric", "validation_open"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    row = authority_row()
    validation = row["validation"]
    metrics = row["metrics"]
    assert isinstance(validation, dict) and isinstance(metrics, dict)
    if mutation == "missing_native":
        validation.pop("native_iwpr_parity_authorized")
    elif mutation == "native_true":
        validation["native_iwpr_parity_authorized"] = True
    elif mutation == "attempt":
        validation["source_feasibility_attempt_id"] = "WRONG"
    elif mutation == "source_metric":
        metrics["source_runs_executed"] = 1
    else:
        metrics["research_validation_opened"] = True
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="authority"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64, "analyzer_sha256": "C" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)


def test_bound_input_mutation_fails_final_rehash(tmp_path: Path) -> None:
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"frozen-first")
    second.write_bytes(b"frozen-second")
    paths = {"first": first, "second": second}
    expected = {name: MODULE.sha256_file(path) for name, path in paths.items()}
    assert MODULE.verify_frozen_inputs(paths, expected) == expected
    second.write_bytes(b"mutated")
    with pytest.raises(ValueError, match="second"):
        MODULE.verify_frozen_inputs(paths, expected)
