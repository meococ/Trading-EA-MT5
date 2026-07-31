from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "research" / "stage0_trendstack.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("stage0_trendstack", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _bar(timestamp: str | pd.Timestamp, value: float) -> dict:
    return {
        "time_utc": pd.Timestamp(timestamp),
        "open": value,
        "high": value + 0.0003,
        "low": value - 0.0003,
        "close": value + 0.0001,
    }


def test_daily_sequence_rejects_partial_and_duplicate_utc_days() -> None:
    mod = load_module()
    complete = [_bar(pd.Timestamp("2020-01-02") + pd.Timedelta(hours=h), 1.10) for h in range(20)]
    partial = [_bar(pd.Timestamp("2020-01-03") + pd.Timedelta(hours=h), 1.11) for h in range(19)]
    duplicate = [_bar(pd.Timestamp("2020-01-06") + pd.Timedelta(hours=h), 1.12) for h in range(20)]
    duplicate.append(dict(duplicate[6]))

    daily = mod.build_valid_daily_sequence(pd.DataFrame(complete + partial + duplicate))

    assert daily.loc[pd.Timestamp("2020-01-02"), "valid"]
    assert daily.loc[pd.Timestamp("2020-01-02"), "daily_close"] == pytest.approx(1.1001)
    assert daily.loc[pd.Timestamp("2020-01-03"), "exclusion_reason"] == "PARTIAL_DAY_LT20"
    assert daily.loc[pd.Timestamp("2020-01-06"), "exclusion_reason"] == "DUPLICATE_UTC_OPEN"


def test_m252_requires_exactly_253_prior_valid_closes_and_never_uses_decision_day() -> None:
    mod = load_module()
    dates = pd.date_range("2019-01-01", periods=253, freq="D")
    daily = pd.DataFrame(
        {
            "date_utc": dates,
            "valid": True,
            "daily_close": [1.0 + i / 1000 for i in range(253)],
            "close_time_utc": dates + pd.Timedelta(hours=23),
        }
    ).set_index("date_utc")

    too_early = mod.compute_m252(daily, dates[-1])
    exact = mod.compute_m252(daily, dates[-1] + pd.Timedelta(days=1))

    assert too_early["direction"] is None
    assert too_early["reason"] == "INSUFFICIENT_M252_HISTORY"
    assert exact["direction"] == 1
    assert exact["oldest_source_date"] == "2019-01-01"
    assert exact["latest_source_date"] == str(dates[-1].date())


def test_m6_uses_exactly_0600_through_1100_and_rejects_missing_or_duplicate() -> None:
    mod = load_module()
    base = pd.Timestamp("2022-06-06")
    rows = [_bar(base + pd.Timedelta(hours=h), 1.1000 + (h - 6) * 0.0001) for h in range(6, 12)]
    rows.append(_bar(base + pd.Timedelta(hours=12), 9.0))

    valid = mod.compute_m6(pd.DataFrame(rows), base)
    missing = mod.compute_m6(pd.DataFrame(rows[1:]), base)
    duplicated_rows = rows + [dict(rows[2])]
    duplicate = mod.compute_m6(pd.DataFrame(duplicated_rows), base)

    assert valid["direction"] == 1
    assert valid["last_source_time_utc"] == "2022-06-06T11:00:00"
    assert missing["reason"] == "MISSING_SIX_HOUR_BAR"
    assert duplicate["reason"] == "DUPLICATE_SIX_HOUR_BAR"


def test_atr20_is_simple_tr_at_1100_and_ignores_1200_bar() -> None:
    mod = load_module()
    end = pd.Timestamp("2022-06-06 11:00:00")
    times = pd.date_range(end=end, periods=20, freq="h")
    rows = []
    for i, timestamp in enumerate(times):
        value = 100.0 + i * 0.5
        rows.append(
            {
                "time_utc": timestamp,
                "open": value,
                "high": value + 1.0,
                "low": value - 1.0,
                "close": value + 0.25,
            }
        )
    rows.append(
        {
            "time_utc": pd.Timestamp("2022-06-06 12:00:00"),
            "open": 1000.0,
            "high": 2000.0,
            "low": 1.0,
            "close": 1500.0,
        }
    )

    atr = mod.atr20_at_decision(pd.DataFrame(rows), pd.Timestamp("2022-06-06"))

    assert atr["reason"] is None
    assert atr["value"] == pytest.approx(2.0)
    assert atr["source_time_utc"] == "2022-06-06T11:00:00"


def test_causal_cursor_never_releases_future_or_holdout_rows(tmp_path: Path) -> None:
    mod = load_module()
    path = tmp_path / "tiny_h1.parquet"
    pd.DataFrame(
        [
            _bar("2022-12-30 06:00:00", 1.09),
            _bar("2022-12-30 11:00:00", 1.10),
            _bar("2022-12-30 15:00:00", 1.11),
            _bar("2022-12-31 06:00:00", 1.12),
            _bar("2023-01-02 06:00:00", 1.20),
        ]
    ).to_parquet(path, index=False)
    expected_hash = mod.sha256_file(path)

    cursor = mod.CausalParquetCursor(path, expected_hash)
    first, first_trace = cursor.advance_to(pd.Timestamp("2022-12-30 12:00:00"))
    second, second_trace = cursor.advance_to(pd.Timestamp("2023-01-01 00:00:00"))

    assert list(first["time_utc"]) == [
        pd.Timestamp("2022-12-30 06:00:00"),
        pd.Timestamp("2022-12-30 11:00:00"),
    ]
    assert list(second["time_utc"]) == [
        pd.Timestamp("2022-12-30 15:00:00"),
        pd.Timestamp("2022-12-31 06:00:00"),
    ]
    assert pd.Timestamp(first_trace["max_visible_time_utc"]) < pd.Timestamp(
        first_trace["decision_cutoff"]
    )
    assert pd.Timestamp(second_trace["max_visible_time_utc"]) < pd.Timestamp(
        second_trace["decision_cutoff"]
    )
    assert cursor.holdout_rows_returned == 0
    with pytest.raises(RuntimeError, match="HOLDOUT"):
        cursor.advance_to(pd.Timestamp("2023-01-01 00:00:01"))
    assert mod.DATA_REL.endswith("EURUSD_H1_2015_now.parquet")


def test_scanner_source_has_no_full_frame_parquet_materialization() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "pd.read_parquet" not in source
    assert "load_sealed_bars" not in source
    assert "batch_size=1" in source


def test_four_arm_eligibility_is_mutually_reconciled() -> None:
    mod = load_module()
    aligned = mod.arm_eligibility(base_eligible=True, m252=1, m6=1)
    disagree = mod.arm_eligibility(base_eligible=True, m252=-1, m6=1)
    flat = mod.arm_eligibility(base_eligible=True, m252=1, m6=0)

    assert aligned == {
        "control_m252_eligible": True,
        "control_m6_eligible": True,
        "challenger_stack_eligible": True,
        "negative_disagree_eligible": False,
    }
    assert disagree["challenger_stack_eligible"] is False
    assert disagree["negative_disagree_eligible"] is True
    assert flat["control_m252_eligible"] is True
    assert flat["control_m6_eligible"] is False
    assert flat["challenger_stack_eligible"] is False
    assert flat["negative_disagree_eligible"] is False


def test_frozen_count_and_direction_gates_return_pass_or_park() -> None:
    mod = load_module()
    passing = pd.DataFrame(
        [
            {"split": "DESIGN", "challenger_stack_eligible": True, "m252_direction": 1}
            for _ in range(261)
        ]
        + [
            {"split": "DESIGN", "challenger_stack_eligible": True, "m252_direction": -1}
            for _ in range(261)
        ]
        + [
            {"split": "VALIDATION", "challenger_stack_eligible": True, "m252_direction": 1}
            for _ in range(100)
        ]
        + [
            {"split": "VALIDATION", "challenger_stack_eligible": True, "m252_direction": -1}
            for _ in range(109)
        ]
    )

    passed = mod.evaluate_stage0_gates(passing)
    parked = mod.evaluate_stage0_gates(
        passing.loc[~((passing["split"] == "DESIGN") & (passing.index == 0))]
    )

    assert passed["verdict"] == "PASS"
    assert passed["split_counts"]["DESIGN"]["challenger"] == 522
    assert passed["split_counts"]["VALIDATION"]["short"] == 109
    assert parked["verdict"] == "PARK"


def test_artifacts_are_hash_reconciled_outcome_blind_and_immutable(tmp_path: Path) -> None:
    mod = load_module()
    ledger = pd.DataFrame(
        [
            {
                "hypothesis_id": mod.HYPOTHESIS_ID,
                "plan_sha256": mod.PLAN_SHA256,
                "opportunity_id": "2022-01-03",
                "split": "VALIDATION",
                "challenger_stack_eligible": True,
                "m252_direction": 1,
            }
        ]
    )
    result = {
        "hypothesis_id": mod.HYPOTHESIS_ID,
        "plan_sha256": mod.PLAN_SHA256,
        "outcomes_opened": False,
        "holdout_opened": False,
    }

    written = mod.write_stage0_artifacts(tmp_path / "evidence", ledger, result)
    receipt = json.loads(written["receipt_path"].read_text(encoding="utf-8"))
    stored = json.loads(written["result_path"].read_text(encoding="utf-8"))

    assert stored["outcomes_opened"] is False
    assert stored["holdout_opened"] is False
    assert receipt["opportunity_ledger_sha256"] == mod.sha256_file(written["ledger_path"])
    assert receipt["stage0_result_sha256"] == mod.sha256_file(written["result_path"])
    with pytest.raises(FileExistsError):
        mod.write_stage0_artifacts(tmp_path / "evidence", ledger, result)
