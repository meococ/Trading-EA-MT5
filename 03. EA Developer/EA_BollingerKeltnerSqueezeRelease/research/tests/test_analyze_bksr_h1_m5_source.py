from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_bksr_h1_m5_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_bksr_h1_m5_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def h1_source(count: int = 50) -> pd.DataFrame:
    times = pd.date_range(MODULE.H1_START, periods=count, freq="1h")
    epochs = np.array([int(value.timestamp()) for value in times], dtype=np.int64)
    close = 100.0 + np.arange(count, dtype=float) * 0.1
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "H1", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False, "high": close + 1.0, "low": close - 1.0, "close": close})


def m5_source(count: int = 50) -> pd.DataFrame:
    times = pd.date_range(MODULE.M5_START, periods=count, freq="5min")
    epochs = np.array([int(value.timestamp()) for value in times], dtype=np.int64)
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "M5", "source_epoch": epochs, "time_utc": times, "utc_ambiguous": False})


def design_h1(count: int = 40) -> pd.DataFrame:
    frame = h1_source(count)
    times = pd.date_range(MODULE.DESIGN_START, periods=count, freq="1h")
    frame["time_utc"] = times
    frame["source_epoch"] = np.array([int(value.timestamp()) for value in times], dtype=np.int64)
    frame["high"] = 103.0
    frame["low"] = 97.0
    frame["close"] = 100.0
    return frame


def decision_clock(frame: pd.DataFrame) -> pd.DataFrame:
    times = pd.to_datetime(frame["time_utc"], utc=True) + pd.Timedelta(hours=1)
    return pd.DataFrame({"symbol": "XAUUSD", "timeframe": "M5", "source_epoch": frame["source_epoch"].to_numpy(dtype=np.int64) + 3600, "time_utc": times, "utc_ambiguous": False})


def synthetic_bands(count: int = 40) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    basis = np.full(count, 100.0)
    bb_upper = np.full(count, 112.0)
    bb_lower = np.full(count, 88.0)
    kc_upper = np.full(count, 110.0)
    kc_lower = np.full(count, 90.0)
    bb_upper[22:24] = 105.0
    bb_lower[22:24] = 95.0
    return basis, bb_upper, bb_lower, kc_upper, kc_lower


def test_harness_and_manifest_bindings_are_exact() -> None:
    assert MODULE.sha256_file(MODULE.HARNESS_PATH) == MODULE.HARNESS_SHA256
    manifest = json.loads((MODULE.ROOT / MODULE.MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    pairs = {"XAUUSD_H1_ALL_AVAILABLE_20260801.parquet": MODULE.H1_SHA256, "XAUUSD_M5_ALL_AVAILABLE_20260801.parquet": MODULE.M5_SHA256}
    for suffix, digest in pairs.items():
        matches = [item for item in manifest["files"] if str(item["path"]).replace("\\", "/").endswith(suffix)]
        assert len(matches) == 1 and matches[0]["sha256"] == digest


def test_sma_seeded_ema_exact_recurrence() -> None:
    values = np.arange(1.0, 25.0)
    result = MODULE.sma_seeded_ema(values, 20)
    assert np.isnan(result[:19]).all()
    assert result[19] == 10.5
    assert result[20] == pytest.approx(10.5 + 2.0 / 21.0 * (21.0 - 10.5))


def test_wilder_rma_exact_recurrence() -> None:
    values = np.arange(1.0, 25.0)
    result = MODULE.wilder_rma(values, 20)
    assert result[19] == 10.5
    assert result[20] == pytest.approx((19.0 * 10.5 + 21.0) / 20.0)


def test_bollinger_uses_population_std_and_true_range_at_zero() -> None:
    close = np.arange(1.0, 25.0)
    high, low = close + 2.0, close - 2.0
    basis, upper, lower, kc_upper, kc_lower = MODULE.calculate_bands(high, low, close)
    expected_mean = np.mean(close[:20])
    expected_std = np.std(close[:20], ddof=0)
    assert basis[19] == expected_mean
    assert upper[19] == pytest.approx(expected_mean + 2.0 * expected_std)
    assert lower[19] == pytest.approx(expected_mean - 2.0 * expected_std)
    assert kc_upper[19] - kc_lower[19] == pytest.approx(3.0 * 4.0)


def test_release_is_first_off_bar_after_consecutive_squeeze() -> None:
    frame = design_h1()
    frame.loc[24, "close"] = 102.0
    rows = MODULE.release_signals(frame, synthetic_bands(len(frame)))
    assert len(rows) == 1
    assert rows[0]["squeeze_start"] == 22 and rows[0]["_index"] == 24 and rows[0]["direction"] == "LONG"


def test_release_direction_is_symmetric() -> None:
    frame = design_h1()
    frame.loc[24, "close"] = 98.0
    rows = MODULE.release_signals(frame, synthetic_bands(len(frame)))
    assert len(rows) == 1 and rows[0]["direction"] == "SHORT"


def test_basis_equality_consumes_without_event() -> None:
    frame = design_h1()
    rows = MODULE.release_signals(frame, synthetic_bands(len(frame)))
    assert rows == []


def test_strict_band_equality_is_not_squeeze() -> None:
    frame = design_h1()
    bands = list(synthetic_bands(len(frame)))
    bands[1][22] = bands[3][22]
    bands[2][22] = bands[4][22]
    frame.loc[24, "close"] = 102.0
    rows = MODULE.release_signals(frame, tuple(bands))
    assert rows[0]["squeeze_start"] == 23


def test_analyze_maps_h1_release_to_exact_m5_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_h1()
    frame.loc[24, "close"] = 102.0
    clock = decision_clock(frame)
    monkeypatch.setattr(MODULE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    events, report = MODULE.analyze_frames(frame, clock)
    assert len(events) == 1 and set(events[0]) == MODULE.EVENT_KEYS
    assert events[0]["source_bar_index"] == 24 and events[0]["squeeze_start_index"] == 22
    assert events[0]["squeeze_end_index"] == 23 and events[0]["squeeze_length_bars"] == 2
    assert events[0]["decision_source_epoch"] == events[0]["source_bar_source_epoch"] + 3600
    assert report["funnel"]["raw_events"] == 1
    MODULE.assert_outcome_blind(events, report)


@pytest.mark.parametrize("mutation", ["missing_time", "wrong_epoch"])
def test_missing_or_wrong_m5_clock_consumes_raw_event(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    frame = design_h1()
    frame.loc[24, "close"] = 102.0
    clock = decision_clock(frame)
    if mutation == "missing_time":
        clock = clock.drop(index=24).reset_index(drop=True)
    else:
        clock.loc[24, "source_epoch"] += 300
    monkeypatch.setattr(MODULE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    events, report = MODULE.analyze_frames(frame, clock)
    assert events == [] and report["funnel"]["raw_events"] == 1 and report["funnel"]["gap_rejected_events"] == 1


def test_outcome_blind_allowlist_and_predicate_reject_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = design_h1()
    frame.loc[24, "close"] = 102.0
    monkeypatch.setattr(MODULE, "calculate_bands", lambda high, low, close: synthetic_bands(len(frame)))
    events, report = MODULE.analyze_frames(frame, decision_clock(frame))
    invalid = dict(events[0], next_close=100.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], close=99.0)
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], bb_upper=105.0, bb_lower=95.0, kc_upper=110.0, kc_lower=90.0)
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], squeeze_end_bb_upper=112.0)
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)
    invalid = dict(events[0], squeeze_end_index=events[0]["squeeze_end_index"] - 1)
    with pytest.raises(ValueError, match="predicate"):
        MODULE.assert_outcome_blind([invalid], report)


def test_flat_h1_bar_is_valid_and_m5_reads_no_price() -> None:
    frame = h1_source()
    frame.loc[8, ["high", "low", "close"]] = 120.0
    assert MODULE.validate_h1(frame).loc[8, "close"] == 120.0
    assert set(MODULE.validate_m5_clock(m5_source()).columns) == set(MODULE.M5_COLUMNS)


@pytest.mark.parametrize("kind,mutation", [("h1", "null_symbol"), ("h1", "inverted"), ("h1", "outside"), ("m5", "null_timeframe"), ("m5", "ambiguous")])
def test_source_contracts_fail_closed(kind: str, mutation: str) -> None:
    if kind == "h1":
        frame = h1_source()
        if mutation == "null_symbol":
            frame.loc[1, "symbol"] = None
        elif mutation == "inverted":
            frame.loc[1, "high"] = frame.loc[1, "low"] - 1.0
        else:
            frame.loc[1, "close"] = frame.loc[1, "high"] + 1.0
        with pytest.raises(ValueError):
            MODULE.validate_h1(frame)
    else:
        frame = m5_source()
        if mutation == "null_timeframe":
            frame.loc[1, "timeframe"] = None
        else:
            frame.loc[1, "utc_ambiguous"] = True
        with pytest.raises(ValueError):
            MODULE.validate_m5_clock(frame)


def authority_row() -> dict[str, object]:
    validation = {name: False for name in MODULE.FALSE_PERMISSIONS}
    validation.update({"source_feasibility_attempt_id": MODULE.ATTEMPT_ID, "source_feasibility_attempt_limit": 1, "source_run_authorized": True, "source_feasibility_only": True, "prehistory_source_access_authorized": True, "manifest_path": MODULE.MANIFEST_RELATIVE_PATH, "manifest_sha256": MODULE.MANIFEST_SHA256, "h1_data_path": MODULE.H1_RELATIVE_PATH, "h1_data_sha256": MODULE.H1_SHA256, "m5_clock_path": MODULE.M5_RELATIVE_PATH, "m5_clock_sha256": MODULE.M5_SHA256, "data_access_predicate": MODULE.DATA_ACCESS_PREDICATE, "reviewed_analyzer_path": MODULE.ANALYZER_RELATIVE_PATH, "reviewed_analyzer_sha256": MODULE.sha256_file(MODULE_PATH), "reviewed_test_path": MODULE.TEST_RELATIVE_PATH, "reviewed_test_sha256": MODULE.TEST_SHA256, "harness_dependency_path": MODULE.HARNESS_RELATIVE_PATH, "harness_dependency_sha256": MODULE.HARNESS_SHA256})
    metrics = {name: 0 for name in MODULE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    return {"hypothesis_id": MODULE.HYPOTHESIS_ID, "state": "probe", "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN", "prereg_sha256": MODULE.PREREG_SHA256, "run_ids": [], "metrics": metrics, "validation": validation}


@pytest.mark.parametrize("mutation", ["missing_native", "native_true", "attempt", "h1", "m5", "source_metric", "holdout"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    row = authority_row()
    validation, metrics = row["validation"], row["metrics"]
    assert isinstance(validation, dict) and isinstance(metrics, dict)
    if mutation == "missing_native": validation.pop("native_ibands_parity_authorized")
    elif mutation == "native_true": validation["native_iatr_parity_authorized"] = True
    elif mutation == "attempt": validation["source_feasibility_attempt_id"] = "WRONG"
    elif mutation == "h1": validation["h1_data_sha256"] = "0" * 64
    elif mutation == "m5": validation["m5_clock_sha256"] = "0" * 64
    elif mutation == "source_metric": metrics["source_runs_executed"] = 1
    else: metrics["research_holdout_opened"] = True
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="authority"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_and_rehash_are_exclusive(tmp_path: Path) -> None:
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
