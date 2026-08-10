from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_trix_m5_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_trix_m5_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_frame(count: int = 80) -> pd.DataFrame:
    times = pd.date_range(MODULE.SOURCE_START, periods=count, freq="5min")
    epochs = 1_086_938_100 + np.arange(count, dtype=np.int64) * 300
    return pd.DataFrame(
        {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "source_epoch": epochs,
            "time_utc": times,
            "utc_ambiguous": False,
            "close": 100.0 + np.arange(count, dtype=float) * 0.01,
        }
    )


def design_frame(trix_values: list[float], gap_after: int | None = None) -> pd.DataFrame:
    count = len(trix_values)
    times = pd.date_range(MODULE.DESIGN_START, periods=count, freq="5min")
    epochs = 1_514_764_800 + np.arange(count, dtype=np.int64) * 300
    if gap_after is not None:
        times = pd.DatetimeIndex(
            [value + (pd.Timedelta(minutes=5) if index > gap_after else pd.Timedelta(0)) for index, value in enumerate(times)]
        )
        epochs[gap_after + 1 :] += 300
    return pd.DataFrame(
        {
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "source_epoch": epochs,
            "time_utc": times,
            "utc_ambiguous": False,
            "close": np.full(count, 100.0),
            "_test_trix": trix_values,
        }
    )


def test_ema_uses_sma_seed_then_recursive_update() -> None:
    values = np.arange(1.0, 21.0)
    result = MODULE.ema_sma_seed(values)
    assert np.isnan(result[:17]).all()
    assert result[17] == pytest.approx(9.5)
    expected = MODULE.ALPHA * 19.0 + (1.0 - MODULE.ALPHA) * 9.5
    assert result[18] == pytest.approx(expected)


def test_ema_seeds_after_leading_unavailable_values() -> None:
    values = np.concatenate((np.full(17, np.nan), np.arange(1.0, 19.0)))
    result = MODULE.ema_sma_seed(values)
    assert np.isnan(result[:34]).all()
    assert result[34] == pytest.approx(9.5)


def test_triple_ema_warmup_indices_are_exact() -> None:
    close = 100.0 + np.arange(80, dtype=float) * 0.1
    state = MODULE.calculate_trix(close)
    assert np.isnan(state["ema1"][:17]).all() and np.isfinite(state["ema1"][17])
    assert np.isnan(state["ema2"][:34]).all() and np.isfinite(state["ema2"][34])
    assert np.isnan(state["ema3"][:51]).all() and np.isfinite(state["ema3"][51])
    assert np.isnan(state["trix"][:52]).all() and np.isfinite(state["trix"][52])


def test_constant_close_produces_zero_trix_and_no_events() -> None:
    frame = design_frame([0.0] * 80)
    frame["close"] = 100.0
    state = MODULE.calculate_trix(frame["close"].to_numpy(dtype=float))
    assert np.isnan(state["trix"][:52]).all()
    assert np.array_equal(state["trix"][52:], np.zeros(28))
    events, report = MODULE.analyze_frame(frame.drop(columns="_test_trix"))
    assert events == []
    assert report["funnel"]["raw_events"] == 0


def test_first_event_requires_current_and_prior_trix(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [np.nan] * 52 + [0.0, 0.25, -0.1, -0.1]
    frame = design_frame(values)
    monkeypatch.setattr(MODULE, "calculate_trix", lambda close: {"trix": np.asarray(values, dtype=float)})
    events, _ = MODULE.analyze_frame(frame.drop(columns="_test_trix"))
    assert [row["direction"] for row in events] == ["LONG", "SHORT"]
    assert events[0]["source_bar_time_utc"] == frame.at[53, "time_utc"].isoformat().replace("+00:00", "Z")


def test_prior_equality_arms_but_current_equality_emits_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [0.0, 0.2, 0.0, -0.3, 0.0]
    frame = design_frame(values)
    monkeypatch.setattr(MODULE, "calculate_trix", lambda close: {"trix": np.asarray(values, dtype=float)})
    events, report = MODULE.analyze_frame(frame.drop(columns="_test_trix"))
    assert [row["direction"] for row in events] == ["LONG", "SHORT"]
    assert report["funnel"]["raw_events"] == 2


def test_raw_gap_event_is_consumed_not_delayed(monkeypatch: pytest.MonkeyPatch) -> None:
    values = [-0.2, 0.3, 0.4]
    frame = design_frame(values, gap_after=1)
    monkeypatch.setattr(MODULE, "calculate_trix", lambda close: {"trix": np.asarray(values, dtype=float)})
    events, report = MODULE.analyze_frame(frame.drop(columns="_test_trix"))
    assert events == []
    assert report["funnel"]["raw_events"] == 1
    assert report["funnel"]["gap_rejected_events"] == 1


@pytest.mark.parametrize("column", ["symbol", "timeframe"])
def test_null_identity_fails_closed(column: str) -> None:
    frame = source_frame()
    frame.loc[1, column] = None
    with pytest.raises(ValueError, match="XAUUSD/M5"):
        MODULE.validate_frame(frame)


def test_nonmonotonic_time_and_invalid_close_fail_closed() -> None:
    frame = source_frame()
    frame.loc[2, "time_utc"] = frame.loc[0, "time_utc"]
    with pytest.raises(ValueError, match="time_utc"):
        MODULE.validate_frame(frame)
    frame = source_frame()
    frame.loc[5, "close"] = np.nan
    with pytest.raises(ValueError, match="finite and positive"):
        MODULE.validate_frame(frame)


def test_outcome_blind_exact_allowlist() -> None:
    valid = {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "source_bar_time_utc": "2018-01-01T00:00:00Z",
        "decision_time_utc": "2018-01-01T00:05:00Z",
        "direction": "LONG",
        "prior_trix": 0.0,
        "trix": 0.1,
    }
    report = {"prohibitions": {"post_event_ohlc_read": False, "native_itrix_parity_authorized_by_attempt": True}}
    MODULE.assert_outcome_blind([valid], report)
    invalid = dict(valid, next_close=101.0)
    with pytest.raises(ValueError, match="allowlist"):
        MODULE.assert_outcome_blind([invalid], report)


def authority_row() -> dict[str, object]:
    validation = {name: False for name in MODULE.FALSE_PERMISSIONS}
    validation.update(
        {
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
        }
    )
    metrics = {name: 0 for name in MODULE.ZERO_METRICS}
    metrics.update({"research_validation_opened": False, "research_holdout_opened": False})
    return {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "state": "probe",
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.PREREG_SHA256,
        "run_ids": [],
        "metrics": metrics,
        "validation": validation,
    }


@pytest.mark.parametrize("mutation", ["missing_native", "native_true", "attempt", "source_metric", "validation_open"])
def test_authority_mutations_fail_closed(mutation: str, tmp_path: Path) -> None:
    row = authority_row()
    validation = row["validation"]
    metrics = row["metrics"]
    assert isinstance(validation, dict) and isinstance(metrics, dict)
    if mutation == "missing_native":
        validation.pop("native_itrix_parity_authorized")
    elif mutation == "native_true":
        validation["native_itrix_parity_authorized"] = True
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
            "schema_version": "trix_source_attempt_terminal.v1",
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
