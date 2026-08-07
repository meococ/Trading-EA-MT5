from __future__ import annotations

import importlib.util
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "build_jcdr_002_m5_source.py"
SPEC = importlib.util.spec_from_file_location("build_jcdr_002_m5_source", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
UTC = timezone.utc


def m1_row(at: datetime, open_price: float, close_price: float) -> dict[str, object]:
    pad = 0.00001
    return {
        "time_utc": at,
        "open": open_price,
        "high": max(open_price, close_price) + pad,
        "low": min(open_price, close_price) - pad,
        "close": close_price,
    }


def rows_from_m5_closes(closes: list[float]) -> list[dict[str, object]]:
    """Expand target M5 closes into exact five-constituent M1 bars."""

    start = datetime(2020, 1, 2, 0, 0, tzinfo=UTC)
    rows: list[dict[str, object]] = []
    previous = closes[0]
    for index, target in enumerate(closes):
        group_start = start + timedelta(minutes=index * 5)
        for minute in range(5):
            current_open = previous
            current_close = target if minute == 4 else previous
            rows.append(m1_row(group_start + timedelta(minutes=minute), current_open, current_close))
            previous = current_close
    return rows


def one_cluster_rows() -> list[dict[str, object]]:
    price = 1.10000
    closes: list[float] = []
    # Quiet burn-in: alternating 0.10-pip returns keep the frozen floor at
    # 1.20 pips and provide the exact prior-48 M5 scale.
    for index in range(100):
        if index in {50, 52, 54}:
            price += 0.00030  # three dominant +3-pip jumps
        elif index in {55, 56, 57}:
            price -= 0.00008  # causal three-bar quiescence + 26% re-entry
        else:
            price += 0.00001 if index % 2 == 0 else -0.00001
        closes.append(price)
    return rows_from_m5_closes(closes)


def test_import_is_disarmed() -> None:
    assert M.REVIEWED_REGISTRY_ROW_SHA256 is None
    with pytest.raises(M.ContractError, match="disarmed"):
        M.execute_probe(workspace_root=Path.cwd(), run_switch=False)


def test_exact_m5_construction_and_incomplete_group_reset() -> None:
    rows = rows_from_m5_closes([1.1000, 1.1002, 1.1001])
    segments, quality = M.construct_exact_m5(rows)
    assert quality["nonempty_aligned_m5_groups"] == 3
    assert quality["complete_exact_five_m5_groups"] == 3
    assert len(segments) == 1
    assert len(segments[0]) == 3
    assert segments[0][0]["time_utc"].minute == 4

    # Delete one constituent from the middle group. That group is not imputed
    # and the valid bars on either side become separate state segments.
    broken = [row for row in rows if row["time_utc"].minute != 7]
    segments, quality = M.construct_exact_m5(broken)
    assert quality["nonempty_aligned_m5_groups"] == 3
    assert quality["complete_exact_five_m5_groups"] == 2
    assert quality["incomplete_nonempty_m5_groups"] == 1
    assert [len(segment) for segment in segments] == [1, 1]


def test_m5_ohlc_and_decision_stamp_are_exact() -> None:
    start = datetime(2020, 1, 2, 0, 0, tzinfo=UTC)
    rows = [
        m1_row(start + timedelta(minutes=0), 1.1000, 1.1010),
        m1_row(start + timedelta(minutes=1), 1.1010, 1.0990),
        m1_row(start + timedelta(minutes=2), 1.0990, 1.1020),
        m1_row(start + timedelta(minutes=3), 1.1020, 1.0980),
        m1_row(start + timedelta(minutes=4), 1.0980, 1.1005),
    ]
    segments, quality = M.construct_exact_m5(rows)
    assert quality["complete_exact_five_m5_groups"] == 1
    bar = segments[0][0]
    assert bar["open"] == rows[0]["open"]
    assert bar["high"] == max(row["high"] for row in rows)
    assert bar["low"] == min(row["low"] for row in rows)
    assert bar["close"] == rows[-1]["close"]
    assert bar["m5_start_utc"] == start
    assert bar["time_utc"] == start + timedelta(minutes=4)


def test_whole_missing_m5_group_resets_continuity() -> None:
    rows = rows_from_m5_closes([1.1000, 1.1001, 1.1002, 1.1003])
    start = datetime(2020, 1, 2, 0, 0, tzinfo=UTC)
    without_second_group = [
        row
        for row in rows
        if not start + timedelta(minutes=5) <= row["time_utc"] < start + timedelta(minutes=10)
    ]
    segments, quality = M.construct_exact_m5(without_second_group)
    assert quality["nonempty_aligned_m5_groups"] == 3
    assert quality["complete_exact_five_m5_groups"] == 3
    assert quality["complete_exact_five_m5_groups"] / quality[
        "nonempty_aligned_m5_groups"
    ] == 1.0
    assert quality["m5_gap_breaks"] == 1
    assert [len(segment) for segment in segments] == [1, 2]


def test_nonempty_but_noncanonical_constituents_are_excluded() -> None:
    rows = rows_from_m5_closes([1.1000, 1.1001])
    # Group g has minutes 0,1,2,3 only; g+5 is present in the next group. The
    # two groups remain separately nonempty and neither can repair the other.
    malformed = [row for row in rows if row["time_utc"].minute != 4]
    segments, quality = M.construct_exact_m5(malformed)
    assert quality["nonempty_aligned_m5_groups"] == 2
    assert quality["complete_exact_five_m5_groups"] == 1
    assert quality["incomplete_nonempty_m5_groups"] == 1
    assert len(segments) == 1


def test_duplicate_m1_timestamp_is_fail_closed() -> None:
    rows = rows_from_m5_closes([1.1000])
    with pytest.raises(M.ContractError, match="duplicate"):
        M.construct_exact_m5(rows + [dict(rows[-1])])


def test_non_minute_aligned_constituent_is_fail_closed() -> None:
    rows = rows_from_m5_closes([1.1000])
    rows[0]["time_utc"] = rows[0]["time_utc"] + timedelta(seconds=1)
    with pytest.raises(M.ContractError, match="minute aligned"):
        M.construct_exact_m5(rows)


def test_cluster_decision_is_next_m5_open_and_outcome_blind() -> None:
    report = M.scan_source_once(one_cluster_rows())
    assert report["population"]["raw_first_per_day_count"] == 1
    assert report["population"]["eligible_count"] == 1
    assert report["arm_counts"] == {"TRUE_REVERSAL": 1, "FOLLOW_CONTROL": 1}
    true_row = report["signal_ledgers"]["TRUE"][0]
    decision = datetime.fromisoformat(true_row["decision_utc"].replace("Z", "+00:00"))
    availability = datetime.fromisoformat(true_row["entry_open_utc"].replace("Z", "+00:00"))
    assert availability - decision == timedelta(minutes=1)
    assert availability.minute % 5 == 0
    assert true_row["direction"] == "SHORT"
    assert true_row["source_signal_id"].startswith("JCDR002-SRC-")
    assert true_row["candidate_id"].startswith("JCDR002-TRUE-")
    assert not true_row["candidate_id"].startswith("JCDR001-")
    control_row = report["signal_ledgers"]["FOLLOW_CONTROL"][0]
    assert control_row["candidate_id"].startswith("JCDR002-FOLLOW_CONTROL-")
    assert report["exact_once"]["arm_identity_projection"][0]["TRUE"][
        "candidate_id"
    ] == true_row["candidate_id"]
    assert report["post_entry_ohlc_rows_read"] == 0
    assert report["returns_computed"] == 0
    assert report["trades_simulated"] == 0
    M.BASE.assert_outcome_blind(report)


def test_independent_replay_is_byte_identical() -> None:
    report = M.scan_source(one_cluster_rows())
    replay = report["independent_replay"]
    assert replay["digests_equal"] is True
    assert replay["primary_canonical_digest_sha256"] == replay[
        "replay_canonical_digest_sha256"
    ]


def test_gap_between_cluster_and_decay_cannot_leak_pending_state() -> None:
    rows = one_cluster_rows()
    gap_start = datetime(2020, 1, 2, 4, 35, tzinfo=UTC)  # M5 index 55
    broken = [
        row
        for row in rows
        if not gap_start <= row["time_utc"] < gap_start + timedelta(minutes=5)
    ]
    report = M.scan_source_once(broken)
    assert report["construction_diagnostics"]["m5_gap_breaks"] == 1
    assert report["population"]["raw_first_per_day_count"] == 0
    assert report["population"]["eligible_count"] == 0


def test_stage0_constituent_gate_fails_below_099() -> None:
    rows = rows_from_m5_closes([1.1000 + i * 0.00001 for i in range(100)])
    # Two partial groups remain in the denominator: 98 exact / 100 nonempty.
    broken = [
        row
        for row in rows
        if row["time_utc"]
        not in {
            datetime(2020, 1, 2, 0, 4, tzinfo=UTC),
            datetime(2020, 1, 2, 0, 9, tzinfo=UTC),
        }
    ]
    report = M.scan_source_once(broken)
    metrics = report["stage0"]["metrics"]
    assert metrics["formation_complete"] == 98
    assert metrics["formation_scheduled"] == 100
    assert math.isclose(metrics["formation_completeness_ratio"], 0.98)
    assert report["stage0"]["gates"][
        "formation_domain_completeness_at_least_0_99"
    ] is False


def test_construction_completeness_is_constituent_quality_not_lookback() -> None:
    report = M.scan_source_once(one_cluster_rows())
    metrics = report["stage0"]["metrics"]
    assert metrics["formation_complete"] == 100
    assert metrics["formation_scheduled"] == 100
    assert math.isclose(metrics["formation_completeness_ratio"], 1.0)
    # The economic/cadence gate correctly fails on this tiny synthetic sample;
    # construction validity alone is never promoted to source PASS.
    assert report["stage0"]["verdict"] == M.BASE.STAGE0_FAIL


def test_reviewed_builder_hash_ignores_only_sentinel_value() -> None:
    payload = MODULE_PATH.read_bytes()
    original = M._reviewed_builder_sha(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
    )
    assert M._reviewed_builder_sha(armed) == original
    mutated = payload.replace(b"LOOKBACK_RETURNS = 48", b"LOOKBACK_RETURNS = 49")
    assert M._reviewed_builder_sha(mutated) != original


def test_current_registry_validator_and_schema_are_hash_bound() -> None:
    workspace = Path(__file__).parents[4]
    validator = workspace / M.REGISTRY_VALIDATOR_REL
    schema = workspace / M.REGISTRY_SCHEMA_REL
    assert M.BASE.sha256_bytes(validator.read_bytes()) == M.REGISTRY_VALIDATOR_SHA256
    assert M.BASE.sha256_bytes(schema.read_bytes()) == M.REGISTRY_SCHEMA_SHA256
    assert M.BASE.REGISTRY_VALIDATOR_SHA256 == M.REGISTRY_VALIDATOR_SHA256
    assert M.BASE.REGISTRY_SCHEMA_SHA256 == M.REGISTRY_SCHEMA_SHA256


def test_nonfinite_ohlc_is_rejected() -> None:
    rows = rows_from_m5_closes([1.1000])
    rows[0]["high"] = float("nan")
    with pytest.raises(M.ContractError):
        M.construct_exact_m5(rows)
