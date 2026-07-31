from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import pytest


RESEARCH = Path(__file__).resolve().parents[1] / "research"
sys.path.insert(0, str(RESEARCH))

import hyp011_stage0_probe as probe


BASE = pd.Timestamp("2020-01-06 09:00:00")  # UTC 07:00 under FivePercent winter clock.


def frame(rows: list[dict], start: pd.Timestamp = BASE) -> pd.DataFrame:
    data = []
    for index, row in enumerate(rows):
        item = {
            "open": row.get("open", row["close"]),
            "high": row.get("high", row["close"]),
            "low": row.get("low", row["close"]),
            "close": row["close"],
            "vwap48": row.get("vwap48", 1.1000),
            "atr14": row.get("atr14", 0.0010),
            "contiguous_m1": row.get("contiguous_m1", True),
        }
        data.append(item)
    idx = [start + pd.Timedelta(minutes=5 * i) for i in range(len(rows))]
    return pd.DataFrame(data, index=pd.DatetimeIndex(idx))


def h1(close: float = 1.2000, ema: float = 1.0000, start: pd.Timestamp | None = None) -> pd.DataFrame:
    if start is None:
        start = BASE - pd.Timedelta(hours=3)
    idx = [start + pd.Timedelta(hours=i) for i in range(8)]
    out = pd.DataFrame({"time_server": idx, "close": [close] * len(idx), "ema200": [ema] * len(idx)})
    out.set_index("time_server", inplace=True, drop=False)
    return out


def accepted(rows: list[dict], h1_frame: pd.DataFrame | None = None) -> tuple[list[dict], dict]:
    return probe.run_stage0_fsm(frame(rows), h1_frame if h1_frame is not None else h1())


def test_long_and_short_are_mirrors() -> None:
    long_events, long_summary = accepted([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ])
    short_events, short_summary = probe.run_stage0_fsm(
        frame([
            {"close": 1.1010, "high": 1.1012, "low": 1.1008},
            {"close": 1.0995, "high": 1.1005, "low": 1.0990},
            {"close": 1.0994, "high": 1.0999, "low": 1.0989},
            {"close": 1.0988, "high": 1.0992, "low": 1.0987},
        ]),
        h1(close=0.9000, ema=1.0000),
    )
    assert long_events[0]["direction"] == "LONG"
    assert short_events[0]["direction"] == "SHORT"
    assert long_summary["counts"]["first_passage_accept"] == 1
    assert short_summary["counts"]["first_passage_accept"] == 1


def test_hold_bar_cannot_enter_even_when_it_breaks_reclaim_extreme() -> None:
    events, summary = accepted([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1012, "high": 1.1014, "low": 1.1001},
        {"close": 1.1015, "high": 1.1016, "low": 1.1010},
    ])
    assert events[0]["decision_time_server"] == "2020-01-06 09:15:00"
    assert events[0]["decision_lag_bars"] == 2
    assert summary["counts"]["hold_pass"] == 1


def test_first_passage_ordering_recross_before_accept_rejects() -> None:
    events, summary = accepted([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.0999, "high": 1.1020, "low": 1.0990},
    ])
    assert events == []
    assert summary["counts"]["vwap_recross_invalidation"] == 1


def test_h1_flip_rejects_before_price_resolution() -> None:
    h = h1(start=pd.Timestamp("2020-01-06 06:00:00"))
    h.loc[pd.Timestamp("2020-01-06 09:00:00"), ["close", "ema200"]] = [0.9000, 1.0000]
    events, summary = probe.run_stage0_fsm(frame([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.1007, "high": 1.1011, "low": 1.1002},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ], start=pd.Timestamp("2020-01-06 09:35:00")), h)
    assert events == []
    assert summary["counts"]["h1_flip"] == 1


def test_data_gap_resets_candidate() -> None:
    m5 = frame([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001, "contiguous_m1": False},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ])
    events, summary = probe.run_stage0_fsm(m5, h1())
    assert events == []
    assert summary["counts"]["data_gap_reset"] >= 1


def test_utc_session_boundaries_are_enforced() -> None:
    events, summary = probe.run_stage0_fsm(
        frame([
            {"close": 1.0990, "high": 1.0992, "low": 1.0988},
            {"close": 1.1005, "high": 1.1010, "low": 1.0995},
            {"close": 1.1006, "high": 1.1011, "low": 1.1001},
            {"close": 1.1012, "high": 1.1013, "low": 1.1008},
        ], start=pd.Timestamp("2020-01-06 07:00:00")),
        h1(start=pd.Timestamp("2020-01-06 04:00:00")),
    )
    assert events == []
    assert summary["counts"]["raw_reclaim"] == 0


def test_session_end_expires_before_hold_can_pass() -> None:
    events, summary = probe.run_stage0_fsm(
        frame([
            {"close": 1.0990, "high": 1.0992, "low": 1.0988},
            {"close": 1.1005, "high": 1.1010, "low": 1.0995},
            {"close": 1.1012, "high": 1.1014, "low": 1.1001},
        ], start=pd.Timestamp("2020-01-06 18:15:00")),
        h1(start=pd.Timestamp("2020-01-06 15:00:00")),
    )
    assert events == []
    assert summary["counts"]["session_expiry"] == 1
    assert summary["counts"]["hold_pass"] == 0


def test_48_bar_expiry_fires_before_late_acceptance() -> None:
    rows = [
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
    ]
    rows.extend({"close": 1.1007, "high": 1.1011, "low": 1.1002} for _ in range(46))
    rows.append({"close": 1.1012, "high": 1.1013, "low": 1.1008})
    events, summary = accepted(rows)
    assert events == []
    assert summary["counts"]["expiry_48_bar"] == 1


def test_comparators_use_origin_ids_and_jaccard() -> None:
    events, summary = accepted([
        {"close": 1.0990, "high": 1.1000, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1012, "high": 1.1014, "low": 1.1001},
        {"close": 1.1015, "high": 1.1016, "low": 1.1010},
    ])
    assert events[0]["origin_id"] == "202001060905_LONG"
    assert summary["origin_overlap"]["ONE_BAR_CONFIRM"]["intersection"] == 1
    assert summary["origin_overlap"]["ONE_BAR_CONFIRM"]["jaccard"] == 1.0


def test_one_bar_comparator_does_not_read_or_count_invalid_future_hold() -> None:
    events, summary = accepted([
        {"close": 1.0990, "high": 1.1000, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1012, "high": 1.1014, "low": 1.1001, "contiguous_m1": False},
    ])
    assert events == []
    assert summary["origin_overlap"]["ONE_BAR_CONFIRM"]["comparator"] == 0


def test_event_ledger_is_deterministic_json() -> None:
    events1, _ = accepted([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ])
    events2, _ = accepted([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ])
    encoded1 = json.dumps(events1, sort_keys=True)
    encoded2 = json.dumps(events2, sort_keys=True)
    assert hashlib.sha256(encoded1.encode()).hexdigest() == hashlib.sha256(encoded2.encode()).hexdigest()


def test_forbidden_paths_and_schema_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(probe.ContractViolation):
        probe.assert_allowed_path(Path("runs/foo/analysis/logs/EURUSD_LifecycleTrades_x.csv"))
    with pytest.raises(probe.ContractViolation):
        probe.assert_allowed_path(Path("research/evidence/random100/cases/casebook.json"))
    with pytest.raises(probe.ContractViolation):
        probe.assert_allowed_schema(["server_time", "status", "net_profit"])

    csv_path = tmp_path / "EURUSD_DecisionTelemetry_HYP011.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["server_time", "status", "direction", "exit_time"])
        writer.writeheader()
        writer.writerow({"server_time": "2020.01.06 09:00:00", "status": "ORDER_ACCEPTED", "direction": "1", "exit_time": "2020.01.06 10:00:00"})
    old_sha = probe.TELEMETRY_SHA256
    probe.TELEMETRY_SHA256 = probe.sha256_file(csv_path)
    try:
        with pytest.raises(probe.ContractViolation):
            probe.select_first100_order_accepted(csv_path)
    finally:
        probe.TELEMETRY_SHA256 = old_sha


def test_bound_decision_telemetry_projects_only_allowlisted_state(tmp_path: Path) -> None:
    csv_path = tmp_path / "EURUSD_DecisionTelemetry_HYP011.csv"
    fieldnames = [
        "server_time", "variant", "status", "direction", "h1_close", "h1_ema",
        "rolling_vwap_48", "atr14", "entry", "stop", "target", "spread_pips",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for minute in range(100):
            writer.writerow({
                "server_time": (datetime(2020, 1, 6, 9, 0) + pd.Timedelta(minutes=minute)).strftime("%Y.%m.%d %H:%M:%S"),
                "variant": "BOUND",
                "status": "ORDER_ACCEPTED",
                "direction": "1",
                "h1_close": "1.2",
                "h1_ema": "1.1",
                "rolling_vwap_48": "1.15",
                "atr14": "0.001",
                "entry": "999",
                "stop": "998",
                "target": "1000",
                "spread_pips": "0.8",
            })
    old_sha = probe.TELEMETRY_SHA256
    probe.TELEMETRY_SHA256 = probe.sha256_file(csv_path)
    try:
        rows = probe.select_first100_order_accepted(csv_path)
    finally:
        probe.TELEMETRY_SHA256 = old_sha
    assert len(rows) == 100
    assert set(rows[0]) == {
        "server_time", "status", "direction", "h1_close", "h1_ema",
        "rolling_vwap_48", "atr14", "_file_index", "_parsed_server_time",
    }
    assert "entry" not in rows[0]
    assert "stop" not in rows[0]
    assert "target" not in rows[0]


def test_bound_decision_telemetry_rejects_unexpected_outcome_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "EURUSD_DecisionTelemetry_HYP011.csv"
    fieldnames = list(probe.BOUND_TELEMETRY_SCHEMA) + ["net_profit"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
    old_sha = probe.TELEMETRY_SHA256
    probe.TELEMETRY_SHA256 = probe.sha256_file(csv_path)
    try:
        with pytest.raises(probe.ContractViolation):
            probe.select_first100_order_accepted(csv_path)
    finally:
        probe.TELEMETRY_SHA256 = old_sha


def test_build_m5_rejects_duplicate_m1_and_marks_incomplete_bucket() -> None:
    m1 = pd.DataFrame(
        {
            "time_server": [datetime(2020, 1, 6, 9, 0), datetime(2020, 1, 6, 9, 0)],
            "open": [1.0, 1.0],
            "high": [1.0, 1.0],
            "low": [1.0, 1.0],
            "close": [1.0, 1.0],
            "tick_volume": [1, 1],
        }
    )
    with pytest.raises(probe.ContractViolation):
        probe.build_m5_from_m1(m1)

    sparse = pd.DataFrame(
        {
            "time_server": [datetime(2020, 1, 6, 9, 0), datetime(2020, 1, 6, 9, 1)],
            "open": [1.0, 1.0],
            "high": [1.0, 1.0],
            "low": [1.0, 1.0],
            "close": [1.0, 1.0],
            "tick_volume": [1, 1],
        }
    )
    built = probe.build_m5_from_m1(sparse)
    assert bool(built.iloc[0]["contiguous_m1"]) is False

    irregular = pd.DataFrame(
        {
            "time_server": [
                datetime(2020, 1, 6, 9, 0),
                datetime(2020, 1, 6, 9, 1),
                datetime(2020, 1, 6, 9, 1, 30),
                datetime(2020, 1, 6, 9, 3),
                datetime(2020, 1, 6, 9, 4),
            ],
            "open": [1.0] * 5,
            "high": [1.0] * 5,
            "low": [1.0] * 5,
            "close": [1.0] * 5,
            "tick_volume": [1] * 5,
        }
    )
    irregular_built = probe.build_m5_from_m1(irregular)
    assert bool(irregular_built.iloc[0]["contiguous_m1"]) is False


def test_incomplete_previous_bucket_cannot_seed_reclaim() -> None:
    m5 = frame([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988, "contiguous_m1": False},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ])
    events, summary = probe.run_stage0_fsm(m5, h1())
    assert events == []
    assert summary["counts"]["raw_reclaim"] == 0


def test_closed_h1_lookup_uses_only_fully_closed_bar() -> None:
    prepared = h1(start=pd.Timestamp("2020-01-06 06:00:00"))
    at_0859 = probe.closed_h1_at(prepared, pd.Timestamp("2020-01-06 08:59:59"))
    at_0900 = probe.closed_h1_at(prepared, pd.Timestamp("2020-01-06 09:00:00"))
    assert at_0859 is not None and at_0859["time_server"] == pd.Timestamp("2020-01-06 07:00:00")
    assert at_0900 is not None and at_0900["time_server"] == pd.Timestamp("2020-01-06 08:00:00")


def test_frozen_consolidated_plan_hash_matches() -> None:
    plan = RESEARCH / "HYP-VRAS-EURUSD-M5-011_STAGE0_PROBE_PLAN.md"
    assert probe.sha256_file(plan) == probe.PLAN_SHA256


def test_noncanonical_same_content_path_is_rejected(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.csv"
    copied = tmp_path / "copied.csv"
    canonical.write_text("same", encoding="utf-8")
    copied.write_text("same", encoding="utf-8")
    assert probe.sha256_file(canonical) == probe.sha256_file(copied)
    probe.assert_exact_path(canonical, canonical)
    with pytest.raises(probe.ContractViolation, match="non-canonical input path"):
        probe.assert_exact_path(copied, canonical)


def test_hyp011_schema_identifiers_are_emitted() -> None:
    events, summary = accepted([
        {"close": 1.0990, "high": 1.0992, "low": 1.0988},
        {"close": 1.1005, "high": 1.1010, "low": 1.0995},
        {"close": 1.1006, "high": 1.1011, "low": 1.1001},
        {"close": 1.1012, "high": 1.1013, "low": 1.1008},
    ])
    assert events[0]["schema_version"] == "hyp011_stage0_event_ledger.v1"
    assert summary["schema_version"] == "hyp011_stage0_summary.v1"
    assert events[0]["hypothesis_id"] == "HYP-VRAS-EURUSD-M5-011"


def test_parity_rejects_nonfinite_values_and_non_m5_timestamp() -> None:
    m5 = frame([{"close": 1.1, "high": 1.101, "low": 1.099}])
    h1_frame = h1()
    base_row = {
        "server_time": "2020-01-06 09:05:00",
        "status": "ORDER_ACCEPTED",
        "direction": "1",
        "h1_close": "1.2",
        "h1_ema": "1.0",
        "rolling_vwap_48": "nan",
        "atr14": "0.001",
    }
    with pytest.raises(probe.ContractViolation, match="non-finite"):
        probe.parity_first100([base_row], m5, h1_frame)

    second_row = dict(base_row, rolling_vwap_48="1.1", server_time="2020-01-06 09:05:02")
    with pytest.raises(probe.ContractViolation, match="exact M5 boundary"):
        probe.parity_first100([second_row], m5, h1_frame)
