from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_aroon_m15_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_aroon_m15_source", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def m5_frame(groups: int = 40, start: pd.Timestamp = MODULE.SOURCE_START) -> pd.DataFrame:
    count = groups * 3
    times = pd.date_range(start, periods=count, freq="5min")
    epochs = np.arange(count, dtype=np.int64) * 300 + 1_086_938_100
    base = 100.0 + np.sin(np.arange(count) / 5.0)
    return pd.DataFrame(
        {
            "symbol": ["XAUUSD"] * count,
            "timeframe": ["M5"] * count,
            "source_epoch": epochs,
            "time_utc": times,
            "utc_ambiguous": [False] * count,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base,
        }
    )


def aroon_frame(high: np.ndarray, low: np.ndarray, start: str = "2018-01-01T00:00:00Z") -> pd.DataFrame:
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    return pd.DataFrame(
        {
            "symbol": ["XAUUSD"] * len(high),
            "timeframe": ["M15"] * len(high),
            "source_epoch": np.arange(len(high), dtype=np.int64) * 900,
            "time_utc": pd.date_range(start, periods=len(high), freq="15min"),
            "complete": [True] * len(high),
            "high": high,
            "low": low,
            "close": (high + low) / 2.0,
        }
    )


def test_complete_m5_triplet_aggregates_exact_m15_ohlc() -> None:
    raw = MODULE.validate_m5_frame(m5_frame(groups=2))
    result = MODULE.aggregate_m15(raw)
    assert len(result) == 2
    assert result["complete"].tolist() == [True, True]
    assert result.at[0, "source_epoch"] == 1_086_938_100
    assert result.at[0, "high"] == pytest.approx(raw.loc[:2, "high"].max())
    assert result.at[0, "low"] == pytest.approx(raw.loc[:2, "low"].min())
    assert result.at[0, "close"] == pytest.approx(raw.at[2, "close"])


@pytest.mark.parametrize("mutation", ["missing", "duplicate_offset", "utc_gap", "invalid_price"])
def test_incomplete_m15_bucket_is_retained_invalid(mutation: str) -> None:
    raw = m5_frame(groups=3)
    if mutation == "missing":
        raw = raw.drop(index=1).reset_index(drop=True)
    elif mutation == "duplicate_offset":
        raw.loc[1, "source_epoch"] = raw.loc[0, "source_epoch"]
    elif mutation == "utc_gap":
        raw.loc[1, "time_utc"] = raw.loc[1, "time_utc"] + pd.Timedelta(minutes=1)
    else:
        raw.loc[1, "close"] = np.nan
    if mutation == "duplicate_offset":
        raw = raw.sort_values(["source_epoch", "time_utc"]).reset_index(drop=True)
        with pytest.raises(ValueError, match="source_epoch"):
            MODULE.validate_m5_frame(raw)
        return
    selected = MODULE.validate_m5_frame(raw)
    result = MODULE.aggregate_m15(selected)
    assert len(result) == 3
    assert not bool(result.at[0, "complete"])
    assert np.isnan(result.at[0, "high"])


def test_aroon_uses_26_bars_and_spans_zero_to_100() -> None:
    highs = np.arange(30, dtype=float)
    lows = np.arange(30, dtype=float)
    data = aroon_frame(highs, lows)
    result = MODULE.calculate_aroon(data)
    assert np.isnan(result["aroon_up"].iloc[24])
    assert result["aroon_up"].iloc[25] == 100.0
    assert result["aroon_down"].iloc[25] == 0.0


def test_equal_extreme_tie_chooses_most_recent_occurrence() -> None:
    highs = np.arange(30, dtype=float)
    lows = np.arange(30, dtype=float)
    highs[20] = 1000.0
    highs[24] = 1000.0
    lows[10] = -1000.0
    lows[23] = -1000.0
    data = aroon_frame(highs, lows)
    result = MODULE.calculate_aroon(data)
    assert result["aroon_up"].iloc[25] == pytest.approx(96.0)
    assert result["aroon_down"].iloc[25] == pytest.approx(92.0)


def test_first_signal_dependency_index_is_26() -> None:
    data = aroon_frame(np.arange(40, dtype=float), np.arange(40, dtype=float))
    result = MODULE.calculate_aroon(data)
    assert not bool(result["feature_valid"].iloc[25])
    assert bool(result["feature_valid"].iloc[26])


def test_invalid_oldest_dependency_bucket_blocks_26_not_27() -> None:
    data = aroon_frame(np.arange(40, dtype=float), np.arange(40, dtype=float))
    data.loc[0, "complete"] = False
    result = MODULE.calculate_aroon(data)
    assert not bool(result["feature_valid"].iloc[26])
    assert bool(result["feature_valid"].iloc[27])


def oscillating_aroon_frame(length: int = 5000) -> pd.DataFrame:
    x = np.linspace(0.0, 100.0 * np.pi, length)
    center = 100.0 + 5.0 * np.sin(x)
    return aroon_frame(center + 1.0, center - 1.0)


def test_polarity_cross_events_match_exact_predicates() -> None:
    events, report = MODULE.analyze_frame(oscillating_aroon_frame())
    assert events
    assert {row["direction"] for row in events} == {"LONG", "SHORT"}
    for row in events:
        if row["direction"] == "LONG":
            assert row["prior_aroon_up"] <= row["prior_aroon_down"]
            assert row["aroon_up"] > row["aroon_down"]
        else:
            assert row["prior_aroon_up"] >= row["prior_aroon_down"]
            assert row["aroon_up"] < row["aroon_down"]
    assert report["funnel"]["raw_events"] == len(events)


def test_prior_equality_arms_and_current_equality_emits_nothing() -> None:
    up = pd.Series([50.0, 60.0, 50.0])
    down = pd.Series([50.0, 40.0, 50.0])
    usable = pd.Series([False, True, True])
    long_mask = usable & (up.shift(1) <= down.shift(1)) & (up > down)
    short_mask = usable & (up.shift(1) >= down.shift(1)) & (up < down)
    assert long_mask.tolist() == [False, True, False]
    assert short_mask.tolist() == [False, False, False]


def test_raw_event_followed_by_gap_is_consumed() -> None:
    data = oscillating_aroon_frame()
    events, _ = MODULE.analyze_frame(data)
    first_time = pd.Timestamp(events[0]["source_bar_time_utc"])
    index = int(data.index[data["time_utc"].eq(first_time)][0])
    data.loc[index + 1 :, "time_utc"] = data.loc[index + 1 :, "time_utc"] + pd.Timedelta(minutes=15)
    data.loc[index + 1 :, "source_epoch"] = data.loc[index + 1 :, "source_epoch"] + 900
    changed, report = MODULE.analyze_frame(data)
    assert events[0]["source_bar_time_utc"] not in {row["source_bar_time_utc"] for row in changed}
    assert report["funnel"]["gap_rejected_events"] >= 1


def test_event_ledger_is_exact_and_outcome_blind() -> None:
    events, report = MODULE.analyze_frame(oscillating_aroon_frame())
    MODULE.assert_outcome_blind(events, report)
    assert set(events[0]) == MODULE.EVENT_KEYS
    assert not ({"entry_price", "exit_price", "pnl", "return", "profit_factor"} & set(events[0]))


def test_registry_false_permission_matrix_matches_module() -> None:
    required = {
        "model0_data_acquisition_authorized",
        "model0_performance_authorized",
        "model4_data_acquisition_authorized",
        "mt5_train_run_authorized",
        "run_compile_authorized",
        "economic_validity_authorized",
        "validation_access_authorized",
        "holdout_access_authorized",
        "visual_mode_authorized",
        "network_authorized",
        "paid_requests_authorized",
        "native_iaroon_claim_authorized",
    }
    assert required <= set(MODULE.FALSE_PERMISSIONS)


def valid_registry_row() -> dict[str, object]:
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


@pytest.mark.parametrize("mutation", ["missing", "true"])
def test_registry_rejects_native_iaroon_authority(mutation: str, tmp_path: Path) -> None:
    row = valid_registry_row()
    validation = row["validation"]
    assert isinstance(validation, dict)
    if mutation == "missing":
        validation.pop("native_iaroon_claim_authorized")
    else:
        validation["native_iaroon_claim_authorized"] = True
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row, separators=(",", ":")) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="false_permissions"):
        MODULE.validate_registry_authority(registry)


def test_attempt_claim_is_exclusive(tmp_path: Path) -> None:
    authority = {"registry_sha256": "A" * 64, "latest_row_sha256": "B" * 64}
    _, marker = MODULE.claim_attempt(tmp_path / "attempt", authority)
    assert marker.exists()
    with pytest.raises(ValueError, match="already exists"):
        MODULE.claim_attempt(tmp_path / "attempt", authority)


def test_prereg_freezes_window_tie_and_no_rescue() -> None:
    text = (MODULE_PATH.parent / "HYP-AROON-XAUUSD-M15-001_FROZEN_PREREG.md").read_text(encoding="utf-8")
    assert "exactly 26 existing M15 bucket rows" in text
    assert "**most recent** occurrence" in text
    assert "prior `AroonUp <= AroonDown`" in text
    assert "No source data may be opened" in text
