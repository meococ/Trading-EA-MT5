import copy
import hashlib
import importlib.util
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

import evaluate_trendstack_007_design_economics as evaluator


def _sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def _dates():
    result = []
    for year, count in zip(range(2016, 2021), (260, 260, 260, 260, 257)):
        cursor = date(year, 1, 1)
        for _ in range(count):
            result.append(cursor.isoformat())
            cursor += timedelta(days=1)
    assert len(result) == 1297 and len(set(result)) == 1297
    return result


def _synthetic_inputs():
    source_manifest = []
    source_rows = {}
    stage0 = []
    decision_manifest = []
    decision_packets = {}
    for index, day in enumerate(_dates()):
        source_sha = f"{index + 1:064X}"
        packet_sha = f"{index + 2001:064X}"
        source_manifest.append({
            "date": day,
            "relative_path": f"DESIGN/{day}/h1_1200.parquet",
            "sha256": source_sha,
            "rows": 1,
        })
        opening = 1.1000
        source_rows[day] = {
            "file_sha256": source_sha,
            "rows": [{
                "time_server": datetime.fromisoformat(f"{day}T14:00:00"),
                "time_utc": datetime.fromisoformat(f"{day}T12:00:00"),
                "utc_offset_h": 2,
                "open": opening,
                "high": 1.1008,
                "low": 1.0992,
                "close": 1.1004 if index % 2 == 0 else 1.0996,
                "tick_volume": 100,
                "spread": 10,
                "real_volume": 0,
            }],
        }
        m6_eligible = index < 1292
        stack_eligible = index < 661
        disagree_eligible = 661 <= index < 1292
        stage0.append({
            "opportunity_id": day,
            "split": "DESIGN",
            "packet_path": f"DESIGN/{day}.json",
            "packet_file_sha256": packet_sha,
            "control_m252_only_eligible": True,
            "control_m252_only_direction": 1 if index % 2 == 0 else -1,
            "control_m6_only_eligible": m6_eligible,
            "control_m6_only_direction": (-1 if index % 3 == 0 else 1) if m6_eligible else None,
            "challenger_stack_eligible": stack_eligible,
            "challenger_stack_direction": 1 if stack_eligible else None,
            "negative_disagree_eligible": disagree_eligible,
            "negative_disagree_direction": -1 if disagree_eligible else None,
        })
        packet = {
            "schema_version": "trendstack_002_decision_packet.v1",
            "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-002",
            "opportunity_id": day,
            "split": "DESIGN",
            "atr20": 0.0010,
        }
        packet_payload_sha = _sha(evaluator.canonical_json_bytes(packet))
        packet["packet_payload_sha256"] = packet_payload_sha
        stage0[-1]["packet_payload_sha256"] = packet_payload_sha
        decision_manifest.append({
            "opportunity_id": day,
            "split": "DESIGN",
            "packet_path": f"DESIGN/{day}.json",
            "packet_file_sha256": packet_sha,
            "packet_payload_sha256": packet_payload_sha,
        })
        decision_packets[day] = {
            "file_sha256": packet_sha,
            "packet": packet,
        }
    return source_manifest, source_rows, stage0, decision_manifest, decision_packets


def _full_stage0_authority_inputs():
    source_manifest, _, stage0_design, decision_design, _ = _synthetic_inputs()
    validation_rows = []
    validation_manifest = []
    cursor = date(2021, 1, 1)
    for _ in range(520):
        day = cursor.isoformat()
        validation_rows.append({
            "opportunity_id": day,
            "split": "VALIDATION_FEATURE_ONLY",
        })
        validation_manifest.append({
            "opportunity_id": day,
            "split": "VALIDATION_FEATURE_ONLY",
            "packet_path": f"VALIDATION_FEATURE_ONLY/{day}.json",
        })
        cursor += timedelta(days=1)
    return (
        source_manifest,
        stage0_design + validation_rows,
        decision_design + validation_manifest,
    )


def _passing_gate_values():
    finite = lambda value: {"status": "FINITE", "value": value}
    return {
        "cadence": 2.0,
        "pf_1_50": finite(1.3000001),
        "pf_2_25": finite(1.25),
        "pf_3_00": finite(1.0),
        "mean_net_r_1_50": 0.08,
        "total_net_r_1_50": 0.000001,
        "positive_years": 4,
        "dsr_1_50": 0.95,
        "stack_pf_delta_vs_best_standalone": {"status": "FINITE", "value": 0.15},
        "stack_mean_delta_vs_best_standalone": 0.05,
        "stack_pf_delta_vs_disagree": {"status": "FINITE", "value": 0.15},
        "stack_mean_delta_vs_disagree": 0.05,
    }


def _authority():
    authority = dict(evaluator.EXPECTED_ARTIFACT_AUTHORITY_SHA256)
    authority["economics_tool_sha256"] = "F" * 64
    authority["economics_tool_test_sha256"] = "E" * 64
    authority["input_contract_preflight_receipt_sha256"] = "B" * 64
    authority["implementation_review_receipt_sha256"] = "D" * 64
    authority["run_packet_sha256"] = "C" * 64
    return authority


def _run_packet():
    packet = dict(evaluator.RUN_PACKET_FROZEN_VALUES)
    packet.update({
        "implementation_task_v2_sha256": evaluator.IMPLEMENTATION_TASK_V2_SHA256,
        "implementation_task_v3_sha256": evaluator.IMPLEMENTATION_TASK_V3_SHA256,
        "economics_tool_sha256": "F" * 64,
        "economics_tool_test_sha256": "E" * 64,
        "implementation_review_receipt_sha256": "D" * 64,
        "input_contract_preflight_receipt_sha256": "B" * 64,
    })
    assert set(packet) == set(evaluator.RUN_PACKET_FIELDS)
    return packet


def _review_receipt(packet):
    return {
        "schema_version": evaluator.IMPLEMENTATION_REVIEW_RECEIPT_SCHEMA,
        "hypothesis_id": evaluator.HYPOTHESIS_ID,
        "projection_attempt_id": packet["projection_attempt_id"],
        "verdict": evaluator.IMPLEMENTATION_REVIEW_PASS_VERDICT,
        "reviewed_sha256": {
            "implementation_task_v1_sha256": packet["implementation_task_v1_sha256"],
            "implementation_task_v2_sha256": packet["implementation_task_v2_sha256"],
            "implementation_task_v3_sha256": packet["implementation_task_v3_sha256"],
            "implementation_task_v4_sha256": packet["implementation_task_v4_sha256"],
            "implementation_task_v5_sha256": packet["implementation_task_v5_sha256"],
            "implementation_task_v6_sha256": packet["implementation_task_v6_sha256"],
            "economics_tool_sha256": packet["economics_tool_sha256"],
            "economics_tool_test_sha256": packet["economics_tool_test_sha256"],
        },
        "production_design_economics_run_authorized": True,
        "research_validation_authorized": False,
        "research_holdout_authorized": False,
        "mql5_authorized": False,
        "model0_authorized": False,
    }


def _input_contract_preflight_receipt(packet):
    return {
        "schema_version": evaluator.INPUT_CONTRACT_PREFLIGHT_RECEIPT_SCHEMA,
        "hypothesis_id": evaluator.HYPOTHESIS_ID,
        "status": evaluator.INPUT_CONTRACT_PREFLIGHT_PASS_STATUS,
        "reviewed_sha256": {
            field: packet[field]
            for field in evaluator.INPUT_CONTRACT_PREFLIGHT_HASH_FIELDS
        },
        "joined_rows": evaluator.EXPECTED_DATES,
        "first_design_date": _dates()[0],
        "last_design_date": _dates()[-1],
        "economics_executed": False,
        "pnl_metrics_emitted": False,
        "research_validation_opened": False,
        "research_holdout_opened": False,
        "independent_read_only_recheck_passed": True,
    }


def test_import_is_inert_and_contract_constants_are_exact():
    assert evaluator.IMPLEMENTATION_TASK_SHA256 == "45B9D7FFE1DC57DD655DEF40C7E2612CBF7FB5A78C3FE54DDBC48168A303F87A"
    assert evaluator.IMPLEMENTATION_TASK_V2_SHA256 == "8013FB8E9D387A375319020BF80F67FD6D1DC6303B54490B04FEB65AB2079B78"
    assert evaluator.IMPLEMENTATION_TASK_V3_SHA256 == "B02C766DFA5059B6BF80EF5DB0B44167BD9997404B32F1641C25864A6B075F46"
    assert evaluator.EXPECTED_ARM_COUNTS == {
        "CONTROL_M252_ONLY": 1297,
        "CONTROL_M6_ONLY": 1292,
        "CHALLENGER_STACK": 661,
        "NEGATIVE_DISAGREE": 631,
    }
    assert evaluator.COST_TIERS == (("1_50", 1.5), ("2_25", 2.25), ("3_00", 3.0))
    assert evaluator.ELAPSED_WEEKS == pytest.approx(260.571428571)
    assert evaluator.REQUIRED_ARTIFACTS == (
        "design_economics_trade_ledger.jsonl",
        "design_arm_cost_metrics.json",
        "design_yearly_metrics.json",
        "design_dsr_inputs.json",
        "design_gate_report.json",
        "design_economics_receipt.json",
        "attempt_terminal.json",
    )


def test_v6_packet_and_attempt004_authority_migration_is_exact():
    assert evaluator.IMPLEMENTATION_TASK_V4_SHA256 == "7419385BA3CA0604C4CABF4C6EF0AA65673CDBD623117B08371D58B4921BCB2F"
    assert evaluator.IMPLEMENTATION_TASK_V5_SHA256 == "DF7004B4A6398AD58A53B6CAEA3FDFBCFD4A303794EB817ECFCC20CBC648876B"
    assert evaluator.IMPLEMENTATION_TASK_V6_SHA256 == "04CEC53A9947EE6A17D4254D26113C6F22529D2887AD892098D0FAD6703921A5"
    assert evaluator.RUN_PACKET_FROZEN_VALUES["schema_version"] == "trendstack_007_design_economics_run_packet.v4"
    assert evaluator.RUN_PACKET_FROZEN_VALUES["projection_attempt_id"] == "HYP007-DESIGN-ECON-004"
    assert evaluator.RUN_PACKET_FROZEN_VALUES["output_root"].endswith("/HYP007-DESIGN-ECON-004")
    assert evaluator.RUN_PACKET_PATH.endswith("_DESIGN_ECONOMICS_RUN_PACKET_V4.json")
    assert evaluator.RUN_PACKET_FROZEN_VALUES["implementation_review_receipt_path"].endswith(
        "_IMPLEMENTATION_REVIEW_RECEIPT_V4.json"
    )
    assert {
        "implementation_task_v6_path", "implementation_task_v6_sha256",
        "attempt_003_terminal_path", "attempt_003_terminal_sha256",
        "attempt_003_design_economics_receipt_path",
        "attempt_003_design_economics_receipt_sha256",
        "input_contract_preflight_receipt_path",
        "input_contract_preflight_receipt_sha256",
    } <= set(evaluator.RUN_PACKET_FIELDS)
    assert {
        "implementation_task_v5_path", "implementation_task_v5_sha256",
        "attempt_002_terminal_path", "attempt_002_terminal_sha256",
        "attempt_002_design_economics_receipt_path",
        "attempt_002_design_economics_receipt_sha256",
    } <= set(evaluator.RUN_PACKET_FIELDS)
    assert {
        "implementation_task_v4_path", "implementation_task_v4_sha256",
        "attempt_001_terminal_path", "attempt_001_terminal_sha256",
        "attempt_001_design_economics_receipt_path",
        "attempt_001_design_economics_receipt_sha256",
    } <= set(evaluator.RUN_PACKET_FIELDS)
    assert len(evaluator.RUN_PACKET_FIELDS) == 65
    assert evaluator.IMPLEMENTATION_REVIEW_RECEIPT_SCHEMA.endswith(".v4")
    assert evaluator.RUN_PACKET_FROZEN_VALUES["input_contract_preflight_receipt_path"].endswith(
        "_DESIGN_INPUT_CONTRACT_PREFLIGHT_RECEIPT_V1.json"
    )
    assert "input_contract_preflight_receipt_sha256" not in evaluator.RUN_PACKET_FROZEN_VALUES


def test_canonical_run_packet_is_exact_and_hash_bound_without_opening_inputs():
    packet = _run_packet()
    payload = evaluator.canonical_json_bytes(packet) + b"\n"
    observed, observed_sha = evaluator.parse_run_packet_document(payload)
    assert observed == packet
    assert observed_sha == _sha(payload)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra", "missing", "path", "lower_sha", "task_v3_sha", "task_v4_sha",
        "task_v5_sha", "task_v6_sha", "preflight_sha",
    ],
)
def test_run_packet_drift_fails_before_any_authority_or_input_access(mutation):
    packet = _run_packet()
    if mutation == "extra":
        packet["extra"] = True
    elif mutation == "missing":
        packet.pop("output_root")
    elif mutation == "path":
        packet["source_projection_root"] += "-drift"
    elif mutation == "lower_sha":
        packet["economics_tool_sha256"] = packet["economics_tool_sha256"].lower()
    elif mutation == "task_v3_sha":
        packet["implementation_task_v3_sha256"] = "A" * 64
    elif mutation == "task_v4_sha":
        packet["implementation_task_v4_sha256"] = "A" * 64
    elif mutation == "task_v5_sha":
        packet["implementation_task_v5_sha256"] = "A" * 64
    elif mutation == "task_v6_sha":
        packet["implementation_task_v6_sha256"] = "A" * 64
    else:
        packet["input_contract_preflight_receipt_sha256"] = "lowercase" * 8
    payload = evaluator.canonical_json_bytes(packet) + b"\n"
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator.parse_run_packet_document(payload)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"schema_version":"trendstack_007_design_economics_run_packet.v4","schema_version":"duplicate"}\n',
        b'{"x":NaN}\n',
        b'{ "x":1}\n',
    ],
)
def test_run_packet_rejects_duplicate_nonfinite_and_noncanonical_json(payload):
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator.parse_run_packet_document(payload)


def test_authority_file_bindings_are_exact_and_do_not_include_output_root():
    packet = _run_packet()
    bindings = evaluator.authority_file_bindings(packet)
    assert packet["output_root"] not in bindings
    assert bindings[packet["implementation_task_v1_path"]] == evaluator.IMPLEMENTATION_TASK_SHA256
    assert bindings[packet["implementation_task_v2_path"]] == evaluator.IMPLEMENTATION_TASK_V2_SHA256
    assert bindings[packet["implementation_task_v3_path"]] == evaluator.IMPLEMENTATION_TASK_V3_SHA256
    assert bindings[packet["implementation_task_v4_path"]] == evaluator.IMPLEMENTATION_TASK_V4_SHA256
    assert bindings[packet["implementation_task_v5_path"]] == evaluator.IMPLEMENTATION_TASK_V5_SHA256
    assert bindings[packet["implementation_task_v6_path"]] == evaluator.IMPLEMENTATION_TASK_V6_SHA256
    assert bindings[packet["attempt_001_terminal_path"]] == packet["attempt_001_terminal_sha256"]
    assert bindings[packet["attempt_001_design_economics_receipt_path"]] == packet[
        "attempt_001_design_economics_receipt_sha256"
    ]
    assert bindings[packet["attempt_002_terminal_path"]] == packet["attempt_002_terminal_sha256"]
    assert bindings[packet["attempt_002_design_economics_receipt_path"]] == packet[
        "attempt_002_design_economics_receipt_sha256"
    ]
    assert bindings[packet["attempt_003_terminal_path"]] == packet["attempt_003_terminal_sha256"]
    assert bindings[packet["attempt_003_design_economics_receipt_path"]] == packet[
        "attempt_003_design_economics_receipt_sha256"
    ]
    assert bindings[packet["input_contract_preflight_receipt_path"]] == packet[
        "input_contract_preflight_receipt_sha256"
    ]
    assert bindings[packet["source_manifest_path"]] == evaluator.EXPECTED_ARTIFACT_AUTHORITY_SHA256["source_manifest_sha256"]


def test_artifact_authority_exactly_binds_dynamic_preflight_receipt_hash():
    packet = _run_packet()
    authority = evaluator.artifact_authority_from_packet(packet, "C" * 64)
    assert tuple(authority) == evaluator.AUTHORITY_HASH_FIELDS
    assert authority["input_contract_preflight_receipt_sha256"] == "B" * 64


def test_implementation_review_receipt_accepts_only_exact_structured_pass_contract():
    packet = _run_packet()
    evaluator._review_receipt_is_pass(
        evaluator.canonical_json_bytes(_review_receipt(packet)) + b"\n", packet
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_top", "missing_top", "prefix_verdict", "extra_hash", "missing_hash",
        "substring_hash", "wrong_hash", "wrong_task_v5_hash", "wrong_task_v6_hash",
        "opens_validation",
    ],
)
def test_implementation_review_receipt_is_fail_closed_without_substring_authority(mutation):
    packet = _run_packet()
    receipt = _review_receipt(packet)
    if mutation == "extra_top":
        receipt["note"] = "looks reviewed"
    elif mutation == "missing_top":
        receipt.pop("projection_attempt_id")
    elif mutation == "prefix_verdict":
        receipt["verdict"] = "PASS_BUT_NOT_THE_FROZEN_VERDICT"
    elif mutation == "extra_hash":
        receipt["reviewed_sha256"]["unreviewed_sha256"] = "A" * 64
    elif mutation == "missing_hash":
        receipt["reviewed_sha256"].pop("economics_tool_sha256")
    elif mutation == "substring_hash":
        receipt["reviewed_sha256"].pop("economics_tool_sha256")
        receipt["note"] = packet["economics_tool_sha256"]
    elif mutation == "wrong_hash":
        receipt["reviewed_sha256"]["economics_tool_sha256"] = "A" * 64
    elif mutation == "wrong_task_v5_hash":
        receipt["reviewed_sha256"]["implementation_task_v5_sha256"] = "A" * 64
    elif mutation == "wrong_task_v6_hash":
        receipt["reviewed_sha256"]["implementation_task_v6_sha256"] = "A" * 64
    else:
        receipt["research_validation_authorized"] = True
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator._review_receipt_is_pass(
            evaluator.canonical_json_bytes(receipt) + b"\n", packet
        )


def test_input_contract_preflight_receipt_accepts_only_exact_non_economic_pass():
    packet = _run_packet()
    receipt = _input_contract_preflight_receipt(packet)
    evaluator._input_contract_preflight_receipt_is_pass(
        evaluator.canonical_json_bytes(receipt) + b"\n",
        packet,
        _dates(),
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "extra_top", "wrong_status", "wrong_rows", "wrong_first", "wrong_last",
        "economics", "pnl", "validation", "holdout", "recheck", "extra_hash",
        "missing_hash", "wrong_hash",
    ],
)
def test_input_contract_preflight_receipt_is_exact_and_fail_closed(mutation):
    packet = _run_packet()
    receipt = _input_contract_preflight_receipt(packet)
    if mutation == "extra_top":
        receipt["note"] = "not allowed"
    elif mutation == "wrong_status":
        receipt["status"] = "PASS_WITH_CAVEAT"
    elif mutation == "wrong_rows":
        receipt["joined_rows"] -= 1
    elif mutation == "wrong_first":
        receipt["first_design_date"] = "2016-01-02"
    elif mutation == "wrong_last":
        receipt["last_design_date"] = "2020-01-01"
    elif mutation == "economics":
        receipt["economics_executed"] = True
    elif mutation == "pnl":
        receipt["pnl_metrics_emitted"] = True
    elif mutation == "validation":
        receipt["research_validation_opened"] = True
    elif mutation == "holdout":
        receipt["research_holdout_opened"] = True
    elif mutation == "recheck":
        receipt["independent_read_only_recheck_passed"] = False
    elif mutation == "extra_hash":
        receipt["reviewed_sha256"]["extra_sha256"] = "A" * 64
    elif mutation == "missing_hash":
        receipt["reviewed_sha256"].pop("source_manifest_sha256")
    else:
        receipt["reviewed_sha256"]["implementation_task_v6_sha256"] = "A" * 64
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator._input_contract_preflight_receipt_is_pass(
            evaluator.canonical_json_bytes(receipt) + b"\n",
            packet,
            _dates(),
        )


def test_lifecycle_writes_attempt_started_before_synthetic_input_load_and_finishes_once():
    packet = _run_packet()
    run_payload = evaluator.canonical_json_bytes(packet) + b"\n"
    _, run_sha = evaluator.parse_run_packet_document(run_payload)
    events = []
    captured = {}

    def verify_authority(observed):
        assert observed is packet
        events.append("authority")
        return {"verified": True}

    def begin_attempt(observed, observed_sha, payload):
        assert observed is packet and observed_sha == run_sha
        started = json.loads(payload)
        assert started["attempt_state"] == "ATTEMPT_STARTED"
        assert started["production_input_opened"] is False
        assert started["implementation_task_v5_sha256"] == evaluator.IMPLEMENTATION_TASK_V5_SHA256
        assert started["implementation_task_v6_sha256"] == evaluator.IMPLEMENTATION_TASK_V6_SHA256
        assert started["attempt_002_terminal_sha256"] == packet["attempt_002_terminal_sha256"]
        assert started["attempt_002_design_economics_receipt_sha256"] == packet[
            "attempt_002_design_economics_receipt_sha256"
        ]
        assert started["attempt_003_terminal_sha256"] == packet["attempt_003_terminal_sha256"]
        assert started["attempt_003_design_economics_receipt_sha256"] == packet[
            "attempt_003_design_economics_receipt_sha256"
        ]
        assert started["input_contract_preflight_receipt_sha256"] == packet[
            "input_contract_preflight_receipt_sha256"
        ]
        events.append("started")

    def load_inputs(observed, authority_context):
        assert observed is packet and authority_context == {"verified": True}
        events.append("inputs")
        values = _synthetic_inputs()
        return {
            "source_manifest": values[0],
            "source_rows_by_date": values[1],
            "stage0_ledger": values[2],
            "decision_manifest": values[3],
            "decision_packets_by_date": values[4],
            "dsr_callable": lambda *args: 0.5,
        }

    def finish_attempt(observed, artifacts):
        assert observed is packet
        events.append("finished")
        captured.update(artifacts)

    result = evaluator.execute_validated_packet(
        packet,
        run_sha,
        verify_authority=verify_authority,
        begin_attempt=begin_attempt,
        load_inputs=load_inputs,
        finish_attempt=finish_attempt,
    )
    assert events == ["authority", "started", "inputs", "finished"]
    assert result["engineering_status"] == "PASS"
    assert tuple(captured) == evaluator.REQUIRED_ARTIFACTS


def test_post_start_engineering_failure_preserves_no_market_verdict_evidence():
    packet = _run_packet()
    run_sha = _sha(evaluator.canonical_json_bytes(packet) + b"\n")
    events = []
    captured = {}

    def broken_loader(*_):
        events.append("inputs")
        raise evaluator.InvalidEngineering("INVALID_ENGINEERING synthetic loader failure")

    evaluator.execute_validated_packet(
        packet,
        run_sha,
        verify_authority=lambda _: events.append("authority") or {},
        begin_attempt=lambda *_: events.append("started"),
        load_inputs=broken_loader,
        finish_attempt=lambda _, artifacts: (events.append("finished"), captured.update(artifacts)),
    )
    assert events == ["authority", "started", "inputs", "finished"]
    terminal = json.loads(captured["attempt_terminal.json"])
    assert terminal["engineering_status"] == "INVALID"
    assert terminal["error_code"] == "LOAD_INVALID_ENGINEERING"
    assert terminal["market_verdict"] is None


@pytest.mark.parametrize("failure_stage", ["loader", "evaluator", "dsr", "finish_prep"])
def test_unexpected_exception_after_attempt_start_closes_engineering_invalid(
    failure_stage, monkeypatch
):
    packet = _run_packet()
    run_sha = _sha(evaluator.canonical_json_bytes(packet) + b"\n")
    captured = {}

    def load_inputs(*_):
        if failure_stage == "loader":
            raise RuntimeError("unexpected loader failure")
        values = _synthetic_inputs()

        def dsr(*_):
            if failure_stage == "dsr":
                raise RuntimeError("unexpected DSR failure")
            return 0.5

        return {
            "source_manifest": values[0],
            "source_rows_by_date": values[1],
            "stage0_ledger": values[2],
            "decision_manifest": values[3],
            "decision_packets_by_date": values[4],
            "dsr_callable": dsr,
        }

    if failure_stage == "evaluator":
        monkeypatch.setattr(
            evaluator, "evaluate_design",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("unexpected evaluator failure")),
        )
    elif failure_stage == "finish_prep":
        monkeypatch.setattr(
            evaluator, "build_artifacts",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("unexpected finish prep failure")),
        )

    result = evaluator.execute_validated_packet(
        packet,
        run_sha,
        verify_authority=lambda _: {},
        begin_attempt=lambda *_: None,
        load_inputs=load_inputs,
        finish_attempt=lambda _, artifacts: captured.update(artifacts),
    )
    assert result["engineering_status"] == "INVALID"
    terminal = json.loads(captured["attempt_terminal.json"])
    assert terminal["verdict"] == "ENGINEERING_INVALID_NO_MARKET_VERDICT"
    assert terminal["error_code"] == {
        "loader": "LOAD_UNEXPECTED_EXCEPTION",
        "evaluator": "EVALUATION_UNEXPECTED_EXCEPTION",
        "dsr": "EVALUATION_UNEXPECTED_EXCEPTION",
        "finish_prep": "ARTIFACT_PREP_UNEXPECTED_EXCEPTION",
    }[failure_stage]
    assert terminal["market_verdict"] is None


@pytest.mark.parametrize(
    "failure_stage,expected_code",
    [
        ("evaluation", "EVALUATION_INVALID_ENGINEERING"),
        ("artifact_prep", "ARTIFACT_PREP_INVALID_ENGINEERING"),
    ],
)
def test_stage_specific_invalid_engineering_codes_after_attempt_start(
    failure_stage, expected_code, monkeypatch
):
    packet = _run_packet()
    run_sha = _sha(evaluator.canonical_json_bytes(packet) + b"\n")
    values = _synthetic_inputs()
    bundle = {
        "source_manifest": values[0],
        "source_rows_by_date": values[1],
        "stage0_ledger": values[2],
        "decision_manifest": values[3],
        "decision_packets_by_date": values[4],
        "dsr_callable": lambda *_: 0.5,
    }
    target = "evaluate_design" if failure_stage == "evaluation" else "build_artifacts"
    monkeypatch.setattr(
        evaluator,
        target,
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            evaluator.InvalidEngineering("INVALID_ENGINEERING synthetic stage failure")
        ),
    )
    captured = {}
    evaluator.execute_validated_packet(
        packet,
        run_sha,
        verify_authority=lambda _: {},
        begin_attempt=lambda *_: None,
        load_inputs=lambda *_: bundle,
        finish_attempt=lambda _, artifacts: captured.update(artifacts),
    )
    terminal = json.loads(captured["attempt_terminal.json"])
    assert terminal["error_code"] == expected_code
    assert terminal["market_verdict"] is None


def test_exact_join_counts_and_atr_comes_only_from_manifest_bound_decision_packet():
    inputs = _synthetic_inputs()
    joined = evaluator.join_frozen_inputs(*inputs)
    assert len(joined) == 1297
    assert evaluator.arm_counts(joined) == evaluator.EXPECTED_ARM_COUNTS
    assert joined[0]["atr20"] == pytest.approx(0.001)
    assert "atr20" not in joined[0]["source_bar"]


def test_full_stage0_1817_rows_are_hash_scope_but_only_exact_design_rows_reach_evaluation():
    source_manifest, stage0_full, decision_full = _full_stage0_authority_inputs()
    stage0_design, decision_design = evaluator.select_design_authority_scope(
        source_manifest, stage0_full, decision_full
    )
    assert len(stage0_full) == 1817
    assert len(stage0_design) == len(decision_design) == 1297
    assert all(row["split"] == "DESIGN" for row in stage0_design)
    assert all(row["split"] == "DESIGN" for row in decision_design)
    assert not any(row["split"] == "VALIDATION_FEATURE_ONLY" for row in decision_design)
    assert [row["opportunity_id"] for row in stage0_design] == [
        row["date"] for row in source_manifest
    ]


@pytest.mark.parametrize("mutation", ["unsorted", "duplicate", "date_set", "unknown_split"])
def test_stage0_design_filter_is_sorted_unique_and_exact_date_set(mutation):
    source_manifest, stage0_full, decision_full = _full_stage0_authority_inputs()
    if mutation == "unsorted":
        stage0_full[0], stage0_full[1] = stage0_full[1], stage0_full[0]
    elif mutation == "duplicate":
        stage0_full[0]["opportunity_id"] = stage0_full[1]["opportunity_id"]
    elif mutation == "date_set":
        stage0_full[0]["opportunity_id"] = "2015-12-31"
    else:
        stage0_full[-1]["split"] = "UNKNOWN"
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator.select_design_authority_scope(source_manifest, stage0_full, decision_full)


def test_production_loader_accepts_real_host_concrete_path_subclass_without_opening_inputs(
    tmp_path,
):
    root = tmp_path.resolve()
    assert isinstance(root, Path)
    assert type(root) is not Path
    context = {
        "workspace_root": root,
        "source_manifest": [],
        "stage0_ledger": [],
        "decision_manifest": [],
        "dsr_callable": lambda *_: 0.5,
    }
    loaded = evaluator.load_production_inputs(_run_packet(), context)
    assert loaded["source_rows_by_date"] == {}
    assert loaded["decision_packets_by_date"] == {}
    assert loaded["stage0_ledger"] == []


def test_production_loader_rejects_non_path_workspace_root_without_opening_inputs(tmp_path):
    context = {
        "workspace_root": str(tmp_path),
        "source_manifest": [],
        "stage0_ledger": [],
        "decision_manifest": [],
        "dsr_callable": lambda *_: 0.5,
    }
    with pytest.raises(evaluator.InvalidEngineering, match="authority workspace root malformed"):
        evaluator.load_production_inputs(_run_packet(), context)


def test_source_bar_accepts_real_pandas_timestamp_subclass_at_exact_design_clock():
    pd = pytest.importorskip("pandas")
    source_manifest, source_rows, *_ = _synthetic_inputs()
    day = source_manifest[0]["date"]
    source_file = copy.deepcopy(source_rows[day])
    source_file["rows"][0]["time_utc"] = pd.Timestamp(f"{day}T12:00:00")
    source_file["rows"][0]["time_server"] = pd.Timestamp(f"{day}T14:00:00")
    assert isinstance(source_file["rows"][0]["time_utc"], datetime)
    observed = evaluator._validate_source_bar(day, source_file, source_manifest[0]["sha256"])
    assert observed["time_utc"] == datetime.fromisoformat(f"{day}T12:00:00")
    assert observed["time_server"] - observed["time_utc"] == timedelta(hours=2)


@pytest.mark.parametrize("mutation", ["non_datetime", "wrong_utc", "wrong_server", "aware"])
def test_source_bar_rejects_non_datetime_and_wrong_clock_even_for_timestamp_subclass(
    mutation,
):
    pd = pytest.importorskip("pandas")
    source_manifest, source_rows, *_ = _synthetic_inputs()
    day = source_manifest[0]["date"]
    source_file = copy.deepcopy(source_rows[day])
    bar = source_file["rows"][0]
    bar["time_utc"] = pd.Timestamp(f"{day}T12:00:00")
    bar["time_server"] = pd.Timestamp(f"{day}T14:00:00")
    if mutation == "non_datetime":
        bar["time_utc"] = f"{day}T12:00:00"
    elif mutation == "wrong_utc":
        bar["time_utc"] = pd.Timestamp(f"{day}T11:59:59")
    elif mutation == "wrong_server":
        bar["time_server"] = pd.Timestamp(f"{day}T13:00:00")
    else:
        bar["time_utc"] = pd.Timestamp(f"{day}T12:00:00", tz="UTC")
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator._validate_source_bar(day, source_file, source_manifest[0]["sha256"])


def test_v3_native_parquet_physical_schema_is_exact_and_ns_timestamp_typed():
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    schema = pa.schema([
        pa.field("time_server", pa.timestamp("ns")),
        pa.field("time_utc", pa.timestamp("ns")),
        pa.field("utc_offset_h", pa.int8()),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("tick_volume", pa.uint64()),
        pa.field("spread", pa.int32()),
        pa.field("real_volume", pa.uint64()),
    ])
    table = pa.Table.from_pylist([{
        "time_server": datetime.fromisoformat("2016-01-04T14:00:00"),
        "time_utc": datetime.fromisoformat("2016-01-04T12:00:00"),
        "utc_offset_h": 2,
        "open": 1.1, "high": 1.101, "low": 1.099, "close": 1.1005,
        "tick_volume": 100, "spread": 10, "real_volume": 0,
    }], schema=schema)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    rows = evaluator._decode_source_shard(sink.getvalue().to_pybytes())
    assert rows[0]["time_utc"] == datetime.fromisoformat("2016-01-04T12:00:00")


def test_v3_rejects_ns_suffix_column_names_even_when_types_match():
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    table = pa.table({"time_server_ns": pa.array([0], type=pa.timestamp("ns"))})
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    with pytest.raises(evaluator.InvalidEngineering, match="physical schema"):
        evaluator._decode_source_shard(sink.getvalue().to_pybytes())


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_source",
        "extra_packet",
        "duplicate_ledger",
        "source_hash",
        "packet_hash",
        "packet_payload_hash",
        "packet_path",
        "source_time",
        "atr_invalid",
        "arm_count",
        "arm_conflict",
    ],
)
def test_join_is_fail_closed_without_fill_drop_substitute_or_atr_recompute(mutation):
    source_manifest, source_rows, stage0, decision_manifest, decision_packets = _synthetic_inputs()
    first = source_manifest[0]["date"]
    if mutation == "missing_source":
        source_rows.pop(first)
    elif mutation == "extra_packet":
        decision_packets["2021-01-01"] = copy.deepcopy(decision_packets[first])
    elif mutation == "duplicate_ledger":
        stage0.append(copy.deepcopy(stage0[0]))
    elif mutation == "source_hash":
        source_rows[first]["file_sha256"] = "F" * 64
    elif mutation == "packet_hash":
        decision_packets[first]["file_sha256"] = "F" * 64
    elif mutation == "packet_payload_hash":
        stage0[0]["packet_payload_sha256"] = "F" * 64
    elif mutation == "packet_path":
        decision_manifest[0]["packet_path"] = "DESIGN/wrong.json"
    elif mutation == "source_time":
        source_rows[first]["rows"][0]["time_utc"] = datetime.fromisoformat(f"{first}T11:00:00")
    elif mutation == "atr_invalid":
        decision_packets[first]["packet"]["atr20"] = 0
    elif mutation == "arm_count":
        stage0[0]["challenger_stack_eligible"] = False
        stage0[0]["challenger_stack_direction"] = None
    else:
        stage0[700]["challenger_stack_eligible"] = True
        stage0[700]["challenger_stack_direction"] = 1
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator.join_frozen_inputs(
            source_manifest, source_rows, stage0, decision_manifest, decision_packets
        )


@pytest.mark.parametrize(
    "direction,bar,expected_exit,expected_gross,expected_reason",
    [
        (1, {"open": 1.1000, "high": 1.1009, "low": 1.0990, "close": 1.1008}, 1.0990, -1.0, "STOP_TOUCH"),
        (-1, {"open": 1.1000, "high": 1.1010, "low": 1.0991, "close": 1.0992}, 1.1010, -1.0, "STOP_TOUCH"),
        (1, {"open": 1.1000, "high": 1.1008, "low": 1.0991, "close": 1.1004}, 1.1004, 0.4, "BAR_CLOSE"),
        (-1, {"open": 1.1000, "high": 1.1009, "low": 1.0992, "close": 1.0996}, 1.0996, 0.4, "BAR_CLOSE"),
    ],
)
def test_single_bar_execution_stop_precedes_close(direction, bar, expected_exit, expected_gross, expected_reason):
    trade = evaluator.simulate_h1_trade(bar, direction=direction, atr20=0.001)
    assert trade["exit_bid"] == pytest.approx(expected_exit)
    assert trade["gross_R"] == pytest.approx(expected_gross)
    assert trade["exit_reason"] == expected_reason


def test_cost_r_uses_frozen_pip_and_packet_atr():
    assert evaluator.cost_r(atr20=0.001, round_trip_cost_pips=1.5) == pytest.approx(0.15)
    assert evaluator.apply_cost(0.4, atr20=0.001, round_trip_cost_pips=2.25) == pytest.approx(0.175)


@pytest.mark.parametrize(
    "values,status,value",
    [
        ([2.0, -1.0], "FINITE", 2.0),
        ([1.0, 0.0], "NO_LOSS", None),
        ([0.0, 0.0], "NO_WIN_NO_LOSS", None),
    ],
)
def test_profit_factor_statuses_never_encode_infinity(values, status, value):
    result = evaluator.profit_factor(values)
    assert result == {"status": status, "value": value}
    assert b"Infinity" not in evaluator.canonical_json_bytes(result)


@pytest.mark.parametrize(
    "challenger,comparator,status,value,passes",
    [
        ({"status": "FINITE", "value": 1.5}, {"status": "FINITE", "value": 1.2}, "FINITE", 0.3, True),
        ({"status": "NO_LOSS", "value": None}, {"status": "FINITE", "value": 2.0}, "POSITIVE_INFINITY", None, True),
        ({"status": "FINITE", "value": 2.0}, {"status": "NO_LOSS", "value": None}, "NEGATIVE_INFINITY", None, False),
        ({"status": "NO_LOSS", "value": None}, {"status": "NO_LOSS", "value": None}, "ZERO_BOTH_NO_LOSS", 0.0, False),
        ({"status": "NO_WIN_NO_LOSS", "value": None}, {"status": "FINITE", "value": 1.0}, "UNDEFINED", None, False),
    ],
)
def test_relative_pf_truth_table_is_finite_json(challenger, comparator, status, value, passes):
    result = evaluator.relative_profit_factor(challenger, comparator)
    assert result == {"status": status, "value": pytest.approx(value) if value is not None else None}
    assert evaluator.relative_pf_pass(result, 0.15) is passes
    assert b"Infinity" not in evaluator.canonical_json_bytes(result)


def test_fixed_year_denominator_and_elapsed_week_cadence():
    rows = [
        {"date": "2016-01-01", "net_R_1_50": 1.0},
        {"date": "2018-01-01", "net_R_1_50": -0.25},
        {"date": "2020-01-01", "net_R_1_50": 0.5},
    ]
    yearly = evaluator.yearly_metrics(rows)
    assert yearly["yearly_total_net_R_1_50"] == {
        "2016": 1.0, "2017": 0.0, "2018": -0.25, "2019": 0.0, "2020": 0.5
    }
    assert yearly["positive_years_1_50"] == 2
    assert evaluator.cadence(661) == pytest.approx(661 / 260.571428571)


def test_dsr_uses_per_trade_stack_nobs_four_trials_sample_sharpes_and_population_shape():
    calls = []

    def dsr(sr, n_obs, skew, kurt, var_sr_trials, n_trials):
        calls.append((sr, n_obs, skew, kurt, var_sr_trials, n_trials))
        return 0.96

    returns = {
        "CONTROL_M252_ONLY": [float(index % 3 - 1) for index in range(1297)],
        "CONTROL_M6_ONLY": [float(index % 5 - 2) for index in range(1292)],
        "CHALLENGER_STACK": [float(index % 4 - 1) for index in range(661)],
        "NEGATIVE_DISAGREE": [0.0 for _ in range(631)],
    }
    result = evaluator.compute_dsr(returns, dsr)
    assert result["n_obs"] == 661 and result["n_trials"] == 4
    assert result["dsr"] == 0.96
    assert len(calls) == 1 and calls[0][1] == 661 and calls[0][5] == 4
    assert calls[0][4] == pytest.approx(result["var_sr_trials"])
    assert result["arm_sharpes"]["NEGATIVE_DISAGREE"] == 0.0


def test_population_shape_zero_moment_fallback_is_zero_and_three():
    assert evaluator.population_shape([0.25] * 661) == (0.0, 3.0)


def test_canonical_dsr_loader_hash_binds_synthetic_module_without_import_side_effect(tmp_path):
    payload = b"def dsr(sr, n_obs, skew, kurt, var_sr_trials, n_trials):\n    return 0.75\n"
    path = tmp_path / "dsr.py"
    path.write_bytes(payload)
    function = evaluator.load_dsr_callable(path, _sha(payload))
    assert function(0, 661, 0, 3, 0, 4) == 0.75


def test_dsr_executes_exact_verified_bytes_even_if_path_is_swapped_after_hash(tmp_path, monkeypatch):
    verified = b"def dsr(sr, n_obs, skew, kurt, var_sr_trials, n_trials):\n    return 0.25\n"
    swapped = b"def dsr(sr, n_obs, skew, kurt, var_sr_trials, n_trials):\n    return 0.75\n"
    path = tmp_path / "dsr.py"
    path.write_bytes(verified)
    expected = _sha(verified)
    real_sha256 = evaluator.sha256_bytes

    def hash_then_swap(payload):
        observed = real_sha256(payload)
        path.write_bytes(swapped)
        return observed

    monkeypatch.setattr(evaluator, "sha256_bytes", hash_then_swap)
    function = evaluator.load_dsr_callable(path, expected)
    assert function(0, 661, 0, 3, 0, 4) == 0.25


def test_all_twelve_gate_boundaries_pass_and_emit_exact_ids():
    report = evaluator.evaluate_twelve_gates(_passing_gate_values())
    assert report["all_pass"] is True
    assert [gate["gate_id"] for gate in report["gates"]] == [f"G{index:02d}" for index in range(1, 13)]
    assert evaluator.terminal_verdict(report) == "PROBE_SURVIVOR_DESIGN_ONLY"


@pytest.mark.parametrize(
    "key,value,gate_id",
    [
        ("cadence", 1.999999, "G01"),
        ("pf_1_50", {"status": "FINITE", "value": 1.30}, "G02"),
        ("pf_2_25", {"status": "FINITE", "value": 1.249999}, "G03"),
        ("pf_3_00", {"status": "FINITE", "value": 0.999999}, "G04"),
        ("mean_net_r_1_50", 0.079999, "G05"),
        ("total_net_r_1_50", 0.0, "G06"),
        ("positive_years", 3, "G07"),
        ("dsr_1_50", 0.949999, "G08"),
        ("stack_pf_delta_vs_best_standalone", {"status": "FINITE", "value": 0.149999}, "G09"),
        ("stack_mean_delta_vs_best_standalone", 0.049999, "G10"),
        ("stack_pf_delta_vs_disagree", {"status": "FINITE", "value": 0.149999}, "G11"),
        ("stack_mean_delta_vs_disagree", 0.049999, "G12"),
    ],
)
def test_each_gate_fails_on_its_frozen_boundary(key, value, gate_id):
    values = _passing_gate_values()
    values[key] = value
    report = evaluator.evaluate_twelve_gates(values)
    assert report["all_pass"] is False
    assert next(gate for gate in report["gates"] if gate["gate_id"] == gate_id)["status"] == "FAIL"
    assert evaluator.terminal_verdict(report) == "KILL_EXACT_HYP007_DESIGN_OBJECT"


def test_end_to_end_synthetic_evaluation_builds_exact_artifacts_and_create_new_persistence(tmp_path):
    evaluation = evaluator.evaluate_design(*_synthetic_inputs(), dsr_callable=lambda *args: 0.5)
    assert evaluation["engineering_status"] == "PASS"
    assert len(evaluation["trade_rows"]) == 3881
    assert set(evaluation["arm_metrics"]) == set(evaluator.ARMS)
    artifacts = evaluator.build_artifacts(
        evaluation, authority_hashes=_authority(), evaluator_sha256="F" * 64
    )
    assert tuple(artifacts) == evaluator.REQUIRED_ARTIFACTS
    for payload in artifacts.values():
        assert b"NaN" not in payload and b"Infinity" not in payload
    receipt = json.loads(artifacts["design_economics_receipt.json"])
    terminal = json.loads(artifacts["attempt_terminal.json"])
    assert receipt["artifact_sha256"]["design_gate_report.json"] == _sha(
        artifacts["design_gate_report.json"]
    )
    assert terminal["engineering_status"] == "PASS"
    output = tmp_path / "economics"
    evaluator.persist_artifacts(output, artifacts)
    assert sorted(path.name for path in output.iterdir()) == sorted(evaluator.REQUIRED_ARTIFACTS)
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator.persist_artifacts(output, artifacts)


def test_engineering_invalid_artifacts_never_fabricate_pf_wr_or_expectancy():
    artifacts = evaluator.engineering_invalid_artifacts(
        "JOIN_DATE_SET_MISMATCH", authority_hashes=_authority(), evaluator_sha256="F" * 64
    )
    assert tuple(artifacts) == evaluator.REQUIRED_ARTIFACTS
    joined = b"".join(artifacts.values())
    assert b"profit_factor" not in joined
    assert b"win_rate" not in joined
    assert b"expectancy" not in joined
    assert json.loads(artifacts["design_arm_cost_metrics.json"])["arm_metrics"] is None
    assert json.loads(artifacts["design_yearly_metrics.json"])["yearly_metrics"] is None
    assert json.loads(artifacts["design_dsr_inputs.json"])["dsr_inputs"] is None
    invalid_gates = json.loads(artifacts["design_gate_report.json"])
    assert invalid_gates["gates"] is None
    assert invalid_gates["all_pass"] is None
    terminal = json.loads(artifacts["attempt_terminal.json"])
    assert terminal["engineering_status"] == "INVALID"
    assert terminal["market_verdict"] is None


def test_production_attempt_writer_is_create_new_and_started_precedes_seven_artifacts(tmp_path, monkeypatch):
    monkeypatch.setitem(evaluator.RUN_PACKET_FROZEN_VALUES, "output_root", "synthetic-output")
    packet = _run_packet()
    run_sha = _sha(evaluator.canonical_json_bytes(packet) + b"\n")
    started = evaluator.attempt_started_payload(packet, run_sha)
    evaluator.begin_production_attempt(packet, run_sha, started, workspace_root=tmp_path)
    output = tmp_path / "synthetic-output"
    assert [path.name for path in output.iterdir()] == ["attempt_started.json"]
    artifacts = evaluator.engineering_invalid_artifacts(
        "SYNTHETIC_FAILURE", authority_hashes=_authority(), evaluator_sha256="F" * 64
    )
    evaluator.finish_production_attempt(packet, artifacts, workspace_root=tmp_path)
    assert {path.name for path in output.iterdir()} == {"attempt_started.json", *evaluator.REQUIRED_ARTIFACTS}
    with pytest.raises(evaluator.InvalidEngineering):
        evaluator.begin_production_attempt(packet, run_sha, started, workspace_root=tmp_path)


def test_source_contains_no_atr_recompute_surface_and_main_is_guarded():
    source = Path(evaluator.__file__).read_text(encoding="utf-8")
    assert "def compute_atr" not in source
    assert "true_range" not in source.lower()
    assert 'if __name__ == "__main__":' in source
