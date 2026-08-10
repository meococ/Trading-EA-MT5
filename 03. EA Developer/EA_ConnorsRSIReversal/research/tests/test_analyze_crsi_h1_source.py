from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_crsi_h1_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_crsi_h1_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def indicator_frame(prices: np.ndarray, start: str = "2017-11-01T00:00:00Z") -> pd.DataFrame:
    values = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {
            "time_utc": pd.date_range(start, periods=len(values), freq="1h"),
            "high": values + 1.0,
            "low": values - 1.0,
            "close": values,
        }
    )


def oscillating_frame(length: int = 3000) -> pd.DataFrame:
    axis = np.linspace(0.0, 42.0 * np.pi, length)
    prices = 100.0 + 4.0 * np.sin(axis) + 0.35 * np.sin(5.0 * axis)
    return indicator_frame(prices)


def raw_event_indices(data: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    indicator = MODULE.calculate_crsi(data)
    crsi = indicator["crsi"]
    design = (data["time_utc"] >= MODULE.DESIGN_START) & (data["time_utc"] < MODULE.DESIGN_END)
    usable = indicator["feature_valid"] & design
    long_mask = usable & (crsi.shift(1) < MODULE.LOWER_EXTREME) & (crsi >= MODULE.LOWER_EXTREME)
    short_mask = usable & (crsi.shift(1) > MODULE.UPPER_EXTREME) & (crsi <= MODULE.UPPER_EXTREME)
    return long_mask, short_mask


def test_wilder_rsi_seed_and_recurrence() -> None:
    values = pd.Series([1.0, 2.0, 3.0, 2.0, 3.0])
    rsi = MODULE.wilder_rsi(values, 3)
    assert np.isnan(rsi.iloc[2])
    assert rsi.iloc[3] == pytest.approx(66.66666666666667)
    expected_gain = (2.0 / 3.0 * 2.0 + 1.0) / 3.0
    expected_loss = (1.0 / 3.0 * 2.0 + 0.0) / 3.0
    assert rsi.iloc[4] == pytest.approx(100.0 - 100.0 / (1.0 + expected_gain / expected_loss))


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([5.0, 5.0, 5.0, 5.0], 50.0),
        ([1.0, 2.0, 3.0, 4.0], 100.0),
        ([4.0, 3.0, 2.0, 1.0], 0.0),
    ],
)
def test_wilder_rsi_zero_gain_loss_branches(values: list[float], expected: float) -> None:
    assert MODULE.wilder_rsi(pd.Series(values), 3).iloc[3] == expected


def test_exact_streak_equality_reset() -> None:
    close = pd.Series([10.0, 11.0, 12.0, 12.0, 11.0, 10.0, 11.0])
    assert MODULE.calculate_streak(close).tolist() == [0.0, 1.0, 2.0, 0.0, -1.0, -2.0, 1.0]


def test_percent_rank_uses_strict_previous_100_rocs() -> None:
    returns = np.r_[np.linspace(-0.20, 0.20, 100), 0.30, 0.30]
    close = [100.0]
    for change in returns:
        close.append(close[-1] * (1.0 + change / 100.0))
    _, rank = MODULE.calculate_percent_rank(pd.Series(close))
    assert np.isnan(rank.iloc[100])
    assert rank.iloc[101] == 100.0
    assert rank.iloc[102] == 99.0


def test_first_crsi_and_cross_dependency_indices_are_exact() -> None:
    data = indicator_frame(np.arange(140, dtype=float) + 100.0, start=MODULE.SOURCE_START.isoformat())
    indicator = MODULE.calculate_crsi(data)
    assert np.isfinite(indicator["crsi"].iloc[101])
    assert not bool(indicator["feature_valid"].iloc[101])
    assert bool(indicator["feature_valid"].iloc[102])


def test_invalid_oldest_geometry_dependency_blocks_102_not_103() -> None:
    data = indicator_frame(np.arange(140, dtype=float) + 100.0, start=MODULE.SOURCE_START.isoformat())
    data.loc[0, "high"] = np.nan
    indicator = MODULE.calculate_crsi(data)
    assert not bool(indicator["feature_valid"].iloc[102])
    assert bool(indicator["feature_valid"].iloc[103])


def test_reentry_events_match_exact_threshold_predicates() -> None:
    data = oscillating_frame()
    events, report = MODULE.analyze_frame(data)
    assert events
    assert {row["direction"] for row in events} == {"LONG", "SHORT"}
    for row in events:
        if row["direction"] == "LONG":
            assert row["prior_crsi"] < 10.0 <= row["crsi"]
        else:
            assert row["prior_crsi"] > 90.0 >= row["crsi"]
    assert report["funnel"]["raw_events"] == len(events)


def test_current_threshold_equality_confirms_but_prior_equality_does_not() -> None:
    usable = pd.Series([False, True, True])
    crsi = pd.Series([5.0, 10.0, 11.0])
    raw_long = usable & (crsi.shift(1) < 10.0) & (crsi >= 10.0)
    assert raw_long.tolist() == [False, True, False]
    crsi = pd.Series([10.0, 9.0, 10.0])
    raw_long = usable & (crsi.shift(1) < 10.0) & (crsi >= 10.0)
    assert raw_long.tolist() == [False, False, True]


def test_raw_event_followed_by_gap_is_consumed() -> None:
    data = oscillating_frame()
    long_mask, short_mask = raw_event_indices(data)
    event_index = int((long_mask | short_mask)[lambda value: value].index[0])
    data.loc[event_index + 1 :, "time_utc"] = data.loc[event_index + 1 :, "time_utc"] + pd.Timedelta(hours=1)
    events, report = MODULE.analyze_frame(data)
    event_time = data.at[event_index, "time_utc"].isoformat().replace("+00:00", "Z")
    assert event_time not in {row["source_bar_time_utc"] for row in events}
    assert report["funnel"]["gap_rejected_events"] >= 1


def test_market_closure_inside_indicator_history_does_not_reset_state() -> None:
    data = oscillating_frame()
    baseline = MODULE.calculate_crsi(data)
    data.loc[500:, "time_utc"] = data.loc[500:, "time_utc"] + pd.Timedelta(days=2)
    shifted = MODULE.calculate_crsi(data)
    np.testing.assert_allclose(shifted["crsi"], baseline["crsi"], equal_nan=True)
    assert shifted["feature_valid"].equals(baseline["feature_valid"])


def test_event_ledger_exact_allowlist_and_no_outcome_fields() -> None:
    events, report = MODULE.analyze_frame(oscillating_frame())
    MODULE.assert_outcome_blind(events, report)
    assert events and set(events[0]) == MODULE.EVENT_KEYS
    assert not ({"entry_price", "exit_price", "pnl", "return", "profit_factor"} & set(events[0]))


def source_frame_for_validation(timeframe: str = "H1") -> pd.DataFrame:
    times = pd.to_datetime(
        [
            MODULE.SOURCE_START,
            MODULE.SOURCE_START + pd.Timedelta(hours=1),
            MODULE.DESIGN_START,
            MODULE.DESIGN_START + pd.Timedelta(hours=1),
        ],
        utc=True,
    )
    return pd.DataFrame(
        {
            "symbol": ["XAUUSD"] * 4,
            "timeframe": [timeframe] * 4,
            "source_epoch": [1, 2, 3, 4],
            "time_utc": times,
            "utc_ambiguous": [False] * 4,
            "high": [101.0] * 4,
            "low": [99.0] * 4,
            "close": [100.0] * 4,
        }
    )


def test_source_frame_requires_exact_inception_and_native_h1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MODULE, "MIN_ROWS", 1)
    assert len(MODULE.validate_source_frame(source_frame_for_validation())) == 4
    wrong_start = source_frame_for_validation()
    wrong_start.loc[0, "time_utc"] = MODULE.SOURCE_START + pd.Timedelta(minutes=1)
    with pytest.raises(ValueError, match="inception"):
        MODULE.validate_source_frame(wrong_start)
    with pytest.raises(ValueError, match="H1"):
        MODULE.validate_source_frame(source_frame_for_validation("M15"))


@pytest.mark.parametrize("bad_close", [np.nan, np.inf, 0.0, -1.0])
@pytest.mark.parametrize("row_index", [0, 2])
def test_source_frame_rejects_invalid_close_anywhere_in_prehistory_or_design(
    monkeypatch: pytest.MonkeyPatch, bad_close: float, row_index: int
) -> None:
    monkeypatch.setattr(MODULE, "MIN_ROWS", 1)
    frame = source_frame_for_validation()
    frame.loc[row_index, "close"] = bad_close
    with pytest.raises(ValueError, match="finite and strictly positive"):
        MODULE.validate_source_frame(frame)


FALSE_PERMISSIONS = (
    "performance_metrics_authorized",
    "outcome_prices_authorized",
    "post_event_ohlc_authorized",
    "economics_authorized",
    "mt5_authorized",
    "model0_authorized",
    "model0_data_acquisition_authorized",
    "model0_performance_authorized",
    "model0_audit_run_authorized",
    "model4_authorized",
    "model4_data_acquisition_authorized",
    "model4_performance_authorized",
    "mt5_train_run_authorized",
    "mt5_audit_run_authorized",
    "mq5_authorized",
    "mql5_authorized",
    "compile_authorized",
    "run_compile_authorized",
    "mql5_compile_authorized",
    "standalone_compile_authorized",
    "packet_build_authorized",
    "trade_api_authorized",
    "artifact_collection_authorized",
    "comparator_execution_authorized",
    "optimization_authorized",
    "research_falsification_authorized",
    "economic_validity_authorized",
    "validation_authorized",
    "validation_access_authorized",
    "holdout_authorized",
    "holdout_access_authorized",
    "research_validation_access_authorized",
    "research_holdout_access_authorized",
    "visual_mode_authorized",
    "network_authorized",
    "paid_requests_authorized",
    "paper_trading_authorized",
    "promotion_eligible",
    "live_trading_authorized",
    "market_edge_claim_authorized",
    "same_id_retry_authorized",
    "registry_mutation_allowed",
)


def valid_registry_row() -> dict[str, object]:
    validation = {name: False for name in FALSE_PERMISSIONS}
    validation.update(
        {
            "source_feasibility_attempt_id": MODULE.ATTEMPT_ID,
            "source_feasibility_attempt_limit": 1,
            "source_run_authorized": True,
            "source_feasibility_only": True,
            "prehistory_source_access_authorized": True,
            "prehistory_source_start": "2004-06-11T04:00:00Z",
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
    return {
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "state": "probe",
        "verdict": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_sha256": MODULE.PREREG_SHA256,
        "run_ids": [],
        "metrics": {
            "source_feasibility_attempts_consumed": 0,
            "source_runs_executed": 0,
            "post_event_ohlc_rows_read": 0,
            "returns_computed": 0,
            "trades_simulated": 0,
            "performance_trials_executed": 0,
            "model0_runs": 0,
            "model4_runs": 0,
            "mql5_files_created": 0,
            "research_validation_opened": False,
            "research_holdout_opened": False,
        },
        "validation": validation,
    }


def write_registry(path: Path, row: dict[str, object]) -> None:
    path.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")


def test_registry_requires_explicit_source_permission(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    row = valid_registry_row()
    row["validation"]["source_run_authorized"] = False  # type: ignore[index]
    write_registry(registry, row)
    with pytest.raises(ValueError, match="source_run"):
        MODULE.validate_registry_authority(registry)


@pytest.mark.parametrize("permission", FALSE_PERMISSIONS)
def test_registry_rejects_every_broadened_permission(tmp_path: Path, permission: str) -> None:
    registry = tmp_path / "registry.jsonl"
    row = valid_registry_row()
    row["validation"][permission] = True  # type: ignore[index]
    write_registry(registry, row)
    with pytest.raises(ValueError, match="false_permissions"):
        MODULE.validate_registry_authority(registry)


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("prehistory_source_access_authorized", False),
        ("prehistory_source_start", "2018-01-01T00:00:00Z"),
        ("manifest_path", "wrong.json"),
        ("manifest_sha256", "0" * 64),
        ("data_path", "wrong.parquet"),
        ("data_sha256", "0" * 64),
        ("data_access_predicate", "2018-only"),
        ("reviewed_test_path", "wrong_test.py"),
        ("reviewed_test_sha256", "0" * 64),
    ],
)
def test_registry_rejects_prehistory_data_or_test_binding_drift(tmp_path: Path, field: str, bad_value: object) -> None:
    registry = tmp_path / "registry.jsonl"
    row = valid_registry_row()
    row["validation"][field] = bad_value  # type: ignore[index]
    write_registry(registry, row)
    with pytest.raises(ValueError):
        MODULE.validate_registry_authority(registry)


@pytest.mark.parametrize("mutation", ["run_id", "source_count", "validation_opened", "holdout_opened"])
def test_registry_requires_pristine_counters_and_run_ids(tmp_path: Path, mutation: str) -> None:
    registry = tmp_path / "registry.jsonl"
    row = valid_registry_row()
    if mutation == "run_id":
        row["run_ids"] = ["unexpected"]
    elif mutation == "source_count":
        row["metrics"]["source_runs_executed"] = 1  # type: ignore[index]
    elif mutation == "validation_opened":
        row["metrics"]["research_validation_opened"] = True  # type: ignore[index]
    else:
        row["metrics"]["research_holdout_opened"] = True  # type: ignore[index]
    write_registry(registry, row)
    with pytest.raises(ValueError):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)


def test_prereg_freezes_full_prehistory_and_reentry() -> None:
    text = (MODULE_PATH.parent / "HYP-CRSI-XAUUSD-H1-001_FROZEN_PREREG.md").read_text(encoding="utf-8")
    assert "2004-06-11T04:00:00Z" in text
    assert "prior `CRSI < 10` and current `CRSI >= 10`" in text
    assert "prior `CRSI > 90` and current `CRSI <= 90`" in text
    assert "Only `[2018,2023)` rows enter event/gate scoring" in text
