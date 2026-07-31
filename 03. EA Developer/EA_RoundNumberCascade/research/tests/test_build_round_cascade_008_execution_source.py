from __future__ import annotations

import ast
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "build_round_cascade_008_execution_source.py"
PLAN_PATH = (
    Path(__file__).parents[1]
    / "HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE_GUARD_REPAIR_PLAN.md"
)
SPEC = importlib.util.spec_from_file_location("round_cascade_008", MODULE_PATH)
assert SPEC and SPEC.loader
rc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rc)

UTC = timezone.utc


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minute_range(start: datetime, count: int) -> list[datetime]:
    return [start + timedelta(minutes=i) for i in range(count)]


def source(arm: str, at: datetime, ordinal: int = 1) -> dict[str, object]:
    return {
        "arm": arm,
        "planned_entry_time_utc": at,
        "source_lf_row_sha256": f"{ordinal:064X}"[-64:],
    }


def canonical_jsonl(rows: list[dict[str, object]]) -> bytes:
    return b"".join(rc.canonical_json(row) + b"\n" for row in rows)


def full_source_row(arm: str, at: str) -> dict[str, object]:
    return {
        "hypothesis_id": "HYP-ROUND-CASCADE-EURUSD-M5-002",
        "arm": arm,
        "direction": "LONG",
        "level_pips": 50 if arm == "TRUE_0050" else 25,
        "decision_bar_start_utc": at,
        "decision_time_utc": at,
        "planned_entry_time_utc": at,
        "atr20_pips": 8.0,
        "cost_to_stop_ratio_1p5": 0.125,
    }


def test_module_is_inert_and_plan_binding_is_exact() -> None:
    assert rc.PLAN_SHA256 == "1A153E509A8E7F5B43C355F86B398DE492F218A0947F695880B37A6DBE6A73CE"
    assert rc.sha256_bytes(PLAN_PATH.read_bytes()) == rc.PLAN_SHA256
    assert rc.REVIEWED_REGISTRY_ROW_SHA256 is None
    assert rc.ATTEMPT_ID == "HYP008-EXEC-SOURCE-001"
    assert rc.HYPOTHESIS_ID == "HYP-ROUND-CASCADE-EURUSD-M5-008"
    assert rc.PARENT_HYPOTHESIS_ID == "HYP-ROUND-CASCADE-EURUSD-M5-007"
    assert not rc.EVIDENCE_ROOT_REL.startswith("00. Old File/")
    assert "HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE" in rc.EVIDENCE_ROOT_REL
    assert rc.PASS_VERDICT == "PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP009_DESIGN_ECONOMICS"
    plan_text = PLAN_PATH.read_text(encoding="utf-8").lower()
    assert "implementation repair" in plan_text
    assert "not market rescue" in plan_text or "not a market-rule" in plan_text
    assert "implementation-only repair" in plan_text


def test_ast_source_has_no_sequence_index_or_price_column_request() -> None:
    source_text = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    assert isinstance(tree, ast.Module)
    assert ".index(" not in source_text
    assert 'columns=["time_utc"]' in source_text
    for forbidden in (
        'columns=["open"', 'columns=["high"', 'columns=["low"', 'columns=["close"',
        'columns=["spread"', 'columns=["tick_volume"', 'columns=["real_volume"',
    ):
        assert forbidden not in source_text
    # Production readout keys must use renamed diagnostics. Parent failure message
    # still cites design_shards_opened for exact HYP007 terminal binding.
    assert '"design_shards_read"' in source_text
    assert '"design_bytes_read"' in source_text
    assert '"design_timestamp_rows_read"' in source_text
    assert '"design_shards_read": len(entries)' in source_text
    assert '"design_bytes_read": opened_bytes' in source_text
    assert '"design_shards_opened":' not in source_text
    assert '"design_bytes_opened":' not in source_text


def test_canonical_json_rejects_nonfinite_and_duplicate_json_keys() -> None:
    with pytest.raises((TypeError, ValueError)):
        rc.canonical_json({"x": float("nan")})
    with pytest.raises(rc.ContractError, match="duplicate"):
        rc.parse_canonical_object(b'{"x":1,"x":2}', label="duplicate")
    with pytest.raises(rc.ContractError, match="duplicate"):
        rc.parse_historical_json_object(b'{"x":1,"x":2}', label="duplicate")
    with pytest.raises(rc.ContractError, match="non-finite"):
        rc.parse_historical_json_object(b'{"x":Infinity}', label="inf")


def test_source_ledger_is_canonical_unique_and_exact_count_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        full_source_row("TRUE_0050", "2019-01-01T00:00:00Z"),
        full_source_row("SHIFTED_0025", "2019-01-01T00:05:00Z"),
    ]
    payload = canonical_jsonl(rows)
    monkeypatch.setattr(rc, "EXPECTED_SOURCE_COUNTS", {"TRUE_0050": 1, "SHIFTED_0025": 1})
    loaded = rc.load_source_ledger(payload, rc.sha256_bytes(payload))
    assert [len(loaded[arm]) for arm in rc.ARM_ORDER] == [1, 1]
    assert loaded["TRUE_0050"][0]["source_lf_row_sha256"] == rc.sha256_bytes(
        rc.canonical_json(rows[0]) + b"\n"
    )

    with pytest.raises(rc.ContractError, match="canonical"):
        rc.load_source_ledger(payload.replace(b"\n", b"\r\n"), rc.sha256_bytes(payload.replace(b"\n", b"\r\n")))
    with pytest.raises(rc.ContractError, match="count"):
        rc.load_source_ledger(canonical_jsonl(rows[:1]), rc.sha256_bytes(canonical_jsonl(rows[:1])))
    duplicate = canonical_jsonl([rows[0], rows[0]])
    monkeypatch.setattr(rc, "EXPECTED_SOURCE_COUNTS", {"TRUE_0050": 2, "SHIFTED_0025": 0})
    with pytest.raises(rc.ContractError, match="duplicate"):
        rc.load_source_ledger(duplicate, rc.sha256_bytes(duplicate))


def test_source_order_is_not_sorted_away(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        full_source_row("TRUE_0050", "2019-01-01T00:05:00Z"),
        full_source_row("TRUE_0050", "2019-01-01T00:00:00Z"),
    ]
    payload = canonical_jsonl(rows)
    monkeypatch.setattr(rc, "EXPECTED_SOURCE_COUNTS", {"TRUE_0050": 2, "SHIFTED_0025": 0})
    with pytest.raises(rc.ContractError, match="chronological"):
        rc.load_source_ledger(payload, rc.sha256_bytes(payload))


def test_timestamp_index_rejects_duplicate_reverse_unaligned_and_bad_row_shape() -> None:
    start = dt("2019-01-01T00:00:00Z")
    with pytest.raises(rc.ContractError, match="strictly increasing"):
        rc.build_timestamp_index([start, start])
    with pytest.raises(rc.ContractError, match="strictly increasing"):
        rc.build_timestamp_index([start + timedelta(minutes=1), start])
    with pytest.raises(rc.ContractError, match="minute aligned"):
        rc.build_timestamp_index([start + timedelta(seconds=1)])
    with pytest.raises(rc.ContractError, match="timestamp-only"):
        rc.build_timestamp_index([{"time_utc": start, "open": 1.1}])


def test_complete_m5_requires_all_five_observed_minutes_without_gap_fill() -> None:
    start = dt("2019-01-01T00:00:00Z")
    observed = minute_range(start, 15)
    observed.remove(start + timedelta(minutes=2))
    index = rc.build_timestamp_index(observed)
    assert start not in index.complete_m5_starts
    assert start + timedelta(minutes=5) in index.complete_m5_starts
    assert start + timedelta(minutes=10) in index.complete_m5_starts


def test_no_exact_entry_is_classified_before_refractory() -> None:
    start = dt("2019-01-01T00:00:00Z")
    index = rc.build_timestamp_index(minute_range(start, 180))
    rows = {
        "TRUE_0050": [source("TRUE_0050", start, 1), source("TRUE_0050", start + timedelta(seconds=30), 2)],
        "SHIFTED_0025": [],
    }
    result = rc.classify_sources(rows, index)
    assert result.eligible[0]["status"] == "ELIGIBLE_EXACT_ENTRY_NONOVERLAP"
    assert result.ineligible[0]["status"] == "NO_EXACT_ENTRY"
    assert result.ineligible[0]["next_observed_m1_utc"] == "2019-01-01T00:01:00Z"
    assert result.ineligible[0]["delay_minutes"] == 0.5


def test_greedy_arm_local_reservation_rejects_overlap_and_allows_equality() -> None:
    start = dt("2019-01-01T00:00:00Z")
    index = rc.build_timestamp_index(minute_range(start, 240))
    rows = {
        "TRUE_0050": [
            source("TRUE_0050", start, 1),
            source("TRUE_0050", start + timedelta(minutes=30), 2),
            source("TRUE_0050", start + timedelta(minutes=60), 3),
        ],
        "SHIFTED_0025": [source("SHIFTED_0025", start + timedelta(minutes=30), 4)],
    }
    result = rc.classify_sources(rows, index)
    assert [(row["arm"], row["planned_entry_time_utc"]) for row in result.eligible] == [
        ("TRUE_0050", "2019-01-01T00:00:00Z"),
        ("TRUE_0050", "2019-01-01T01:00:00Z"),
        ("SHIFTED_0025", "2019-01-01T00:30:00Z"),
    ]
    refractory = result.ineligible[0]
    assert refractory["status"] == "REFRACTORY_INELIGIBLE"
    assert refractory["blocking_eligible_identity"] == "TRUE_0050|2019-01-01T00:00:00Z"
    assert refractory["overlap_minutes"] == 30


def test_fewer_than_twelve_complete_m5_bars_is_engineering_invalid() -> None:
    start = dt("2019-01-01T00:00:00Z")
    index = rc.build_timestamp_index(minute_range(start, 59))
    rows = {"TRUE_0050": [source("TRUE_0050", start)], "SHIFTED_0025": []}
    with pytest.raises(rc.ContractError, match="twelve complete"):
        rc.classify_sources(rows, index)


def test_independent_replay_hash_is_deterministic_and_detects_tamper() -> None:
    start = dt("2019-01-01T00:00:00Z")
    index = rc.build_timestamp_index(minute_range(start, 120))
    rows = {"TRUE_0050": [source("TRUE_0050", start)], "SHIFTED_0025": []}
    first = rc.classify_sources(rows, index)
    second = rc.replay_sources_independently(rows, index)
    assert first.classification_sha256 == second.classification_sha256
    rc.require_replay_match(first, second)
    changed = second._replace(classification_sha256="0" * 64)
    with pytest.raises(rc.ContractError, match="replay"):
        rc.require_replay_match(first, changed)


def test_stage0_gates_bind_missing_exact_but_not_eligible_or_refractory_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    start = dt("2019-01-01T00:00:00Z")
    index = rc.build_timestamp_index(minute_range(start, 240))
    rows = {
        "TRUE_0050": [source("TRUE_0050", start, 1), source("TRUE_0050", start + timedelta(seconds=30), 2)],
        "SHIFTED_0025": [source("SHIFTED_0025", start, 3), source("SHIFTED_0025", start + timedelta(minutes=5), 4)],
    }
    result = rc.classify_sources(rows, index)
    monkeypatch.setattr(rc, "EXPECTED_SOURCE_COUNTS", {"TRUE_0050": 2, "SHIFTED_0025": 2})
    monkeypatch.setattr(rc, "EXPECTED_NO_EXACT_COUNTS", {"TRUE_0050": 1, "SHIFTED_0025": 0})
    report = rc.evaluate_stage0(result, rows, index, replay=result)
    assert report["verdict"] == "PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP009_DESIGN_ECONOMICS"
    assert report["hyp009_drafting_authorized"] is True
    assert report["actual_counts"]["REFRACTORY_INELIGIBLE"]["SHIFTED_0025"] == 1


def test_stage0_rejects_bad_missing_exact_count_or_unreconciled_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    start = dt("2019-01-01T00:00:00Z")
    index = rc.build_timestamp_index(minute_range(start, 120))
    rows = {"TRUE_0050": [source("TRUE_0050", start)], "SHIFTED_0025": []}
    result = rc.classify_sources(rows, index)
    monkeypatch.setattr(rc, "EXPECTED_SOURCE_COUNTS", {"TRUE_0050": 1, "SHIFTED_0025": 0})
    monkeypatch.setattr(rc, "EXPECTED_NO_EXACT_COUNTS", {"TRUE_0050": 1, "SHIFTED_0025": 0})
    with pytest.raises(rc.ContractError, match="NO_EXACT_ENTRY"):
        rc.evaluate_stage0(result, rows, index, replay=result)
    broken = result._replace(eligible=())
    with pytest.raises(rc.ContractError, match="reconcile"):
        rc.evaluate_stage0(broken, rows, index, replay=broken)


def test_outcome_blind_guard_allows_timestamp_diagnostics_and_sealed_false_only() -> None:
    rc.assert_outcome_blind(
        {
            "planned_entry_time_utc": "2019-01-01T00:00:00Z",
            "reserved_exit_time_utc": "2019-01-01T01:00:00Z",
            "next_observed_m1_utc": None,
            "economics_authorized": False,
            "post_entry_ohlc_rows_read": 0,
            "trades_simulated": 0,
        }
    )
    for bad in (
        {"close": 1.1},
        {"nested": {"direction": "LONG"}},
        {"economics_authorized": True},
        {"trades_simulated": 1},
        {"entry_price": 1.2},
    ):
        with pytest.raises(rc.ContractError):
            rc.assert_outcome_blind(bad)


def test_safe_timestamp_diagnostics_pass_with_nonnegative_plain_integers() -> None:
    """Exact HYP008 repair: renamed diagnostics pass when values are plain ints."""

    rc.assert_outcome_blind(
        {
            "design_shards_read": 1555,
            "design_timestamp_rows_read": 1_859_820,
            "design_bytes_read": 0,
        }
    )
    rc.assert_outcome_blind(
        {
            "timestamp_readout": {
                "design_shards_read": 1,
                "design_timestamp_rows_read": 2,
                "design_bytes_read": 3,
            }
        }
    )
    assert rc.SAFE_TIMESTAMP_DIAGNOSTIC_KEYS == frozenset(
        {
            "design_shards_read",
            "design_timestamp_rows_read",
            "design_bytes_read",
        }
    )


def test_safe_timestamp_diagnostics_reject_wrong_negative_or_bool_values() -> None:
    for bad in (
        {"design_shards_read": -1},
        {"design_timestamp_rows_read": -5},
        {"design_bytes_read": -1},
        {"design_shards_read": True},
        {"design_bytes_read": False},
        {"design_timestamp_rows_read": 1.5},
        {"design_shards_read": "1"},
        {"design_bytes_read": None},
        {"design_timestamp_rows_read": 1.0},
    ):
        with pytest.raises(rc.ContractError, match="invalid safe diagnostic counter"):
            rc.assert_outcome_blind(bad)


def test_retired_opened_names_and_real_forbidden_outcome_keys_still_fail() -> None:
    """Do not broadly weaken the guard: old names and real outcome keys still fail."""

    for bad_key_payload in (
        {"design_shards_opened": 1},
        {"design_bytes_opened": 1},
        {"close": 1.1},
        {"open": 1.0},
        {"high": 1.2},
        {"low": 0.9},
        {"price": 1.1},
        {"spread": 2},
        {"tick_volume": 3},
        {"real_volume": 0},
        {"direction": "LONG"},
        {"trade_count": 1},
        {"return": 0.01},
        {"pnl": 1.0},
        {"profit": 1.0},
        {"performance": 1.0},
        {"economic_result": 1.0},
        {"outcome": "win"},
        {"nested": {"close": 1.1}},
        {"nested": {"design_shards_opened": 1}},
        {"my_open_count": 1},
        {"entry_price": 1.2},
    ):
        with pytest.raises(rc.ContractError, match="forbidden outcome field"):
            rc.assert_outcome_blind(bad_key_payload)


def test_parent_terminal_requires_exact_bytes_and_object(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = rc.expected_parent_terminal()
    payload = (json.dumps(expected, indent=2, sort_keys=True) + "\n").encode("utf-8")
    monkeypatch.setattr(rc, "PARENT_TERMINAL_SHA256", rc.sha256_bytes(payload))
    assert rc.validate_parent_terminal(payload) == expected
    tampered = rc.canonical_json({**expected, "status": "DIFFERENT"})
    with pytest.raises(rc.ContractError, match="parent terminal"):
        rc.validate_parent_terminal(tampered)


def test_frozen_hyp007_parent_terminal_artifact_is_accepted() -> None:
    """Regression against the exact real HYP007 terminal that failed on design_shards_opened."""

    workspace_root = MODULE_PATH.parents[3]
    payload = (workspace_root / rc.PARENT_TERMINAL_REL).read_bytes()
    assert rc.sha256_bytes(payload) == rc.PARENT_TERMINAL_SHA256
    assert rc.PARENT_TERMINAL_SHA256 == (
        "2135A63C5E30A826A119E6BAFB3276C09E4BDC0ABF5F9D5F3A70465BC163C771"
    )
    assert rc.validate_parent_terminal(payload) == rc.expected_parent_terminal()
    assert rc.expected_parent_terminal()["status"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert rc.expected_parent_terminal()["reason"]["message"] == (
        "forbidden outcome field: design_shards_opened"
    )
    assert rc.expected_parent_terminal()["attempt_id"] == "HYP007-EXEC-SOURCE-001"
    assert rc.expected_parent_terminal()["hypothesis_id"] == "HYP-ROUND-CASCADE-EURUSD-M5-007"
    assert rc.expected_parent_terminal()["artifact_sha256"]["attempt_started.json"] == (
        "6EA7B5F6B37B1FC8A3F415A734354F89F3C70A493140DB7C632E7F1477CC7A72"
    )


def test_review_receipt_binds_plan_builder_and_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    builder = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None\n"
    tests = b"tests"
    receipt = rc.expected_review_receipt(builder, tests)
    payload = rc.canonical_json(receipt)
    assert rc.validate_review_receipt(
        payload,
        expected_sha256=rc.sha256_bytes(payload),
        builder_payload=builder,
        test_payload=tests,
    ) == receipt
    assert receipt["schema_version"] == "round_cascade_008_execution_source_implementation_review.v1"
    with pytest.raises(rc.ContractError, match="receipt"):
        rc.validate_review_receipt(payload, expected_sha256="0" * 64, builder_payload=builder, test_payload=tests)


def test_registry_authority_uses_canonical_generic_source_only_surface() -> None:
    builder = MODULE_PATH.read_bytes()
    tests = Path(__file__).read_bytes()
    bindings = rc._expected_authority_bindings(builder, tests)
    assert bindings["source_feasibility_attempt_limit"] == 1
    assert bindings["source_feasibility_attempt_id"] == rc.ATTEMPT_ID
    assert bindings["source_feasibility_evidence_root"] == rc.EVIDENCE_ROOT_REL
    assert bindings["parent_terminal_sha256"] == rc.PARENT_TERMINAL_SHA256
    assert bindings["parent_terminal_sha256"] == (
        "2135A63C5E30A826A119E6BAFB3276C09E4BDC0ABF5F9D5F3A70465BC163C771"
    )
    assert rc.AUTHORITY_TRUE_FIELDS >= {
        "source_run_authorized", "source_feasibility_only",
    }
    assert rc.SOURCE_ONLY_ZERO_METRICS["source_feasibility_attempts_consumed"] == 0
    assert rc.SOURCE_ONLY_ZERO_METRICS["source_runs_executed"] == 0
    assert rc.expected_review_receipt(builder, tests)["permissions"] == {
        "source_feasibility_run": True,
        "performance_or_economics": False,
        "mt5_or_mql5": False,
    }


def test_public_receipt_and_manifest_are_exactly_bound() -> None:
    receipt = {
        "collection_plan_sha256": rc.COLLECTION_PLAN_SHA256,
        "custodian_full_corpus_decoded": True,
        "custodian_tool_sha256": rc.CUSTODIAN_SHA256,
        "design_dates": 2,
        "design_manifest_sha256": "0" * 64,
        "design_rows": 3,
        "exact_once_status": "PASS",
        "private_custody_digest": "1" * 64,
        "private_custody_receipt_sha256": "2" * 64,
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "source_attempt_id": "x",
        "source_bytes": 1,
        "source_footer_length": 1,
        "source_footer_sha256": "3" * 64,
        "source_footer_start": 0,
        "source_sha256": rc.M1_SOURCE_SHA256,
        "stage_path": "D:\\stage",
        "stage_role": "CUSTODY",
        "supervisor_review_base_sha256": "4" * 64,
        "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }
    manifest_rows = [
        {"bytes": 10, "date": "2019-01-01", "relative_path": "public/DESIGN/2019-01-01/m1.parquet", "rows": 1, "sha256": "5" * 64},
        {"bytes": 11, "date": "2019-01-02", "relative_path": "public/DESIGN/2019-01-02/m1.parquet", "rows": 2, "sha256": "6" * 64},
    ]
    manifest = canonical_jsonl(manifest_rows)
    receipt["design_manifest_sha256"] = rc.sha256_bytes(manifest)
    # Canonical compact receipt still accepted under historical parser.
    entries = rc.validate_public_metadata(
        rc.canonical_json(receipt), manifest, expected_dates=2, expected_rows=3
    )
    assert [row["date"] for row in entries] == ["2019-01-01", "2019-01-02"]
    # Pretty / trailing-newline historical receipt also accepted with SHA bind.
    pretty = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    entries_pretty = rc.validate_public_metadata(
        pretty,
        manifest,
        expected_dates=2,
        expected_rows=3,
        expected_receipt_sha256=rc.sha256_bytes(pretty),
    )
    assert [row["date"] for row in entries_pretty] == ["2019-01-01", "2019-01-02"]
    bad = list(manifest_rows)
    bad[1] = {**bad[1], "date": "2019-01-01"}
    bad_payload = canonical_jsonl(bad)
    receipt["design_manifest_sha256"] = rc.sha256_bytes(bad_payload)
    with pytest.raises(rc.ContractError, match="ordered"):
        rc.validate_public_metadata(rc.canonical_json(receipt), bad_payload, expected_dates=2, expected_rows=3)
    # Manifest still requires canonical LF JSONL even when SHA is rebound.
    crlf_manifest = manifest.replace(b"\n", b"\r\n")
    receipt["design_manifest_sha256"] = rc.sha256_bytes(crlf_manifest)
    with pytest.raises(rc.ContractError, match="canonical"):
        rc.validate_public_metadata(
            rc.canonical_json(receipt), crlf_manifest, expected_dates=2, expected_rows=3
        )


def test_dual_receipt_binding_constants_preserved_from_hyp007() -> None:
    """Preserve dual raw + semantic receipt SHA constants without opening production data."""

    assert rc.M1_RECEIPT_SHA256 == "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
    assert rc.M1_RECEIPT_OBJECT_SHA256 == (
        "06AA44C3FB7E42BEDB781CD64826036F43CFFD806E2516F15886E848DAE1AD75"
    )
    assert rc.M1_MANIFEST_SHA256 == "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
    assert rc.M1_SOURCE_SHA256 == "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
    assert rc.SOURCE_LEDGER_SHA256 == "8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE"
    assert rc.EXPECTED_SOURCE_COUNTS == {"TRUE_0050": 1229, "SHIFTED_0025": 1220}
    assert rc.EXPECTED_NO_EXACT_COUNTS == {"TRUE_0050": 1, "SHIFTED_0025": 0}


def test_mutated_stage_path_rejected_by_frozen_object_sha_despite_rebound_raw_sha() -> None:
    """Object SHA must bind stage_path without reading production DESIGN files."""

    receipt = {
        "collection_plan_sha256": rc.COLLECTION_PLAN_SHA256,
        "custodian_full_corpus_decoded": True,
        "custodian_tool_sha256": rc.CUSTODIAN_SHA256,
        "design_dates": 1,
        "design_manifest_sha256": "0" * 64,
        "design_rows": 1,
        "exact_once_status": "PASS",
        "private_custody_digest": "1" * 64,
        "private_custody_receipt_sha256": "2" * 64,
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "source_attempt_id": "x",
        "source_bytes": 1,
        "source_footer_length": 1,
        "source_footer_sha256": "3" * 64,
        "source_footer_start": 0,
        "source_sha256": rc.M1_SOURCE_SHA256,
        "stage_path": "D:\\stage",
        "stage_role": "CUSTODY",
        "supervisor_review_base_sha256": "4" * 64,
        "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }
    manifest_rows = [
        {
            "bytes": 10,
            "date": "2019-01-01",
            "relative_path": "public/DESIGN/2019-01-01/m1.parquet",
            "rows": 1,
            "sha256": "5" * 64,
        },
    ]
    manifest = canonical_jsonl(manifest_rows)
    receipt["design_manifest_sha256"] = rc.sha256_bytes(manifest)
    pretty = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    object_sha = rc.sha256_bytes(rc.canonical_json(receipt))
    entries = rc.validate_public_metadata(
        pretty,
        manifest,
        expected_dates=1,
        expected_rows=1,
        expected_receipt_sha256=rc.sha256_bytes(pretty),
        expected_receipt_object_sha256=object_sha,
    )
    assert len(entries) == 1
    mutated = dict(receipt)
    mutated["stage_path"] = f"{receipt['stage_path']}-MUTATED"
    mutated_payload = (json.dumps(mutated, indent=2, sort_keys=True) + "\n").encode("utf-8")
    mutated_raw_sha = rc.sha256_bytes(mutated_payload)
    with pytest.raises(rc.ContractError, match="object equality"):
        rc.validate_public_metadata(
            mutated_payload,
            manifest,
            expected_dates=1,
            expected_rows=1,
            expected_receipt_sha256=mutated_raw_sha,
            expected_receipt_object_sha256=object_sha,
        )


def test_parquet_decoder_requests_only_time_utc_and_rejects_schema_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    fields = []
    arrays = []
    values = {
        "time_server": [datetime(2019, 1, 1)],
        "time_utc": [datetime(2019, 1, 1)],
        "utc_offset_h": [0],
        "open": [1.1], "high": [1.2], "low": [1.0], "close": [1.15],
        "tick_volume": [1], "spread": [2], "real_volume": [0],
    }
    for name, type_name, nullable in rc.EXPECTED_ARROW_SCHEMA:
        typ = {
            "timestamp[ns]": pa.timestamp("ns"), "int8": pa.int8(), "float64": pa.float64(),
            "uint64": pa.uint64(), "int32": pa.int32(),
        }[type_name]
        fields.append(pa.field(name, typ, nullable=nullable))
        arrays.append(pa.array(values[name], type=typ))
    table = pa.Table.from_arrays(arrays, schema=pa.schema(fields))
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, row_group_size=10)
    payload = sink.getvalue().to_pybytes()

    seen: list[object] = []
    original = pq.ParquetFile.read

    def spy(self: object, *args: object, **kwargs: object) -> object:
        seen.append(kwargs.get("columns"))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pq.ParquetFile, "read", spy)
    rows = rc.decode_timestamp_only_parquet(payload, label="synthetic")
    assert seen == [["time_utc"]]
    assert rows == ({"time_utc": datetime(2019, 1, 1)},)

    drift = table.set_column(9, "real_volume", pa.array([0], type=pa.int64()))
    sink = pa.BufferOutputStream()
    pq.write_table(drift, sink)
    with pytest.raises(rc.ContractError, match="schema"):
        rc.decode_timestamp_only_parquet(sink.getvalue().to_pybytes(), label="drift")


def test_stable_reader_rejects_outside_root_and_hardlink(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    file = allowed / "x.bin"
    file.write_bytes(b"x")
    assert rc.stable_read_regular(file, allowed) == b"x"
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"y")
    with pytest.raises(rc.ContractError, match="outside"):
        rc.stable_read_regular(outside, allowed)
    alias = allowed / "alias.bin"
    try:
        alias.hardlink_to(file)
    except OSError:
        pytest.skip("hardlinks unavailable")
    with pytest.raises(rc.ContractError, match="single-link"):
        rc.stable_read_regular(file, allowed)


def test_default_execute_is_disarmed_before_parent_or_design_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    called = []
    monkeypatch.setattr(rc, "stable_read_regular", lambda *args, **kwargs: called.append(args) or b"")
    with pytest.raises(rc.ContractError, match="explicit run switch"):
        rc.execute_probe(workspace_root=tmp_path, run_switch=False)
    assert called == []
    with pytest.raises(rc.ContractError, match="review sentinel is disarmed"):
        rc.execute_probe(workspace_root=tmp_path, run_switch=True)
    assert called == []


def test_create_new_writer_refuses_replay_and_hash_binds_bytes(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    digest = rc.write_new_bytes(target, b"abc")
    assert digest == rc.sha256_bytes(b"abc")
    assert target.read_bytes() == b"abc"
    with pytest.raises(rc.ContractError, match="create-new"):
        rc.write_new_bytes(target, b"changed")


def test_source_has_no_sequence_index_or_price_column_request() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert ".index(" not in text
    assert 'columns=["time_utc"]' in text
    for forbidden in (
        'columns=["open"', 'columns=["high"', 'columns=["low"', 'columns=["close"',
        'columns=["spread"', 'columns=["tick_volume"', 'columns=["real_volume"',
    ):
        assert forbidden not in text


def test_report_with_safe_readout_is_outcome_blind() -> None:
    """HYP007 failure path: readout with renamed keys must pass assert_outcome_blind."""

    report = {
        "schema_version": "round_cascade_008_execution_source_report.v1",
        "hypothesis_id": rc.HYPOTHESIS_ID,
        "attempt_id": rc.ATTEMPT_ID,
        "verdict": rc.PASS_VERDICT,
        "classification_sha256": "A" * 64,
        "source_input_counts": dict(rc.EXPECTED_SOURCE_COUNTS),
        "actual_counts": {
            "ELIGIBLE_EXACT_ENTRY_NONOVERLAP": {"TRUE_0050": 1, "SHIFTED_0025": 0},
            "REFRACTORY_INELIGIBLE": {"TRUE_0050": 0, "SHIFTED_0025": 0},
            "NO_EXACT_ENTRY": {"TRUE_0050": 0, "SHIFTED_0025": 0},
        },
        "gates": {
            "timestamp_only_outcome_blind": True,
            "historical_design_receipt_sha_bound_object_equal": True,
            "canonical_design_manifest_sha_bound": True,
        },
        "sealed_permissions": rc.sealed_permissions(),
        "source_only_counters": rc.executed_source_only_counters(),
        "hyp009_drafting_authorized": True,
        "timestamp_readout": {
            "design_shards_read": 1555,
            "design_timestamp_rows_read": 1_859_820,
            "design_bytes_read": 12_345,
        },
    }
    rc.assert_outcome_blind(report)
    # Exact HYP007 terminal failure name still rejected if reintroduced.
    with pytest.raises(rc.ContractError, match="forbidden outcome field: design_shards_opened"):
        rc.assert_outcome_blind(
            {
                **report,
                "timestamp_readout": {
                    "design_shards_opened": 1555,
                    "design_timestamp_rows_read": 1_859_820,
                    "design_bytes_opened": 12_345,
                },
            }
        )
