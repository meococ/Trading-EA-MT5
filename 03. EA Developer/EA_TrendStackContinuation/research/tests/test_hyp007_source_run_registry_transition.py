import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import supervise_trendstack_007_source_projection as supervisor


ROOT = Path(__file__).resolve().parents[4]
SCHEMA = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.schema.json"
REGISTRY_VALIDATOR = ROOT / "04. Memory/research/validate_candidate_registry.py"
REGISTRY = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
V2_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_AMENDMENT_V2.json"
V3_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_AMENDMENT_V3.json"
TASK_V5_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V5.json"
RECEIPT_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT_V5.json"
V4_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_REPAIR_AMENDMENT_V4.json"
TASK_V6_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V6.json"
RECEIPT_V6_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT_V6.json"

ROW_TO_PACKET_V5 = {
    "active_contract_bundle_path": "active_contract_bundle_path",
    "active_contract_bundle_sha256": "active_contract_bundle_sha256",
    "authority_amendment_path": "authority_amendment_v2_path",
    "authority_amendment_sha256": "authority_amendment_v2_sha256",
    "economic_access_authorized": "economic_access_authorized",
    "economics_authorized": "economics_authorized",
    "evidence_root": "evidence_root",
    "final_output_root": "final_output_root",
    "holdout_authorized": "holdout_authorized",
    "implementation_review_receipt_path": "implementation_review_receipt_path",
    "implementation_review_receipt_sha256": "implementation_review_receipt_sha256",
    "implementation_task_path": "implementation_task_v5_path",
    "implementation_task_sha256": "implementation_task_v5_sha256",
    "model0_authorized": "model0_authorized",
    "network_allowed": "network_allowed",
    "production_source_projection_authorized": "production_source_projection_authorized",
    "projection_attempt_id": "projection_attempt_id",
    "projector_test_path": "projector_test_path",
    "projector_test_sha256": "projector_test_sha256",
    "projector_tool_path": "projector_tool_path",
    "projector_tool_sha256": "projector_tool_sha256",
    "public_manifest_path": "public_manifest_path",
    "public_manifest_sha256": "public_manifest_sha256",
    "public_receipt_path": "public_receipt_path",
    "public_receipt_sha256": "public_receipt_sha256",
    "registry_mutation_allowed": "registry_mutation_allowed",
    "research_holdout_authorized": "research_holdout_authorized",
    "research_validation_authorized": "research_validation_authorized",
    "selection_manifest_path": "selection_manifest_path",
    "selection_manifest_sha256": "selection_manifest_sha256",
    "source_run_authorized": "source_run_authorized",
    "stage_root": "stage_root",
    "subprocess_allowed": "subprocess_allowed",
    "supervisor_review_base_sha256": "supervisor_review_base_sha256",
    "supervisor_test_path": "supervisor_test_path",
    "supervisor_test_sha256": "supervisor_test_sha256",
    "supervisor_tool_path": "supervisor_tool_path",
    "trading_mutation": "trading_mutation",
    "validation_authorized": "validation_authorized",
    "validator_test_path": "validator_test_path",
    "validator_test_sha256": "validator_test_sha256",
    "validator_tool_path": "validator_tool_path",
    "validator_tool_sha256": "validator_tool_sha256",
}
ROW_TO_PACKET_V6 = dict(ROW_TO_PACKET_V5)
ROW_TO_PACKET_V6.update({
    "implementation_task_path": "implementation_task_v6_path",
    "implementation_task_sha256": "implementation_task_v6_sha256",
})


def _sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def _compact(value):
    return json.dumps(
        value, sort_keys=False, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8") + b"\n"


def _load_validator():
    spec = importlib.util.spec_from_file_location("hyp007_registry_validator", REGISTRY_VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dummy_row(index):
    return {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": f"HYP-DUMMY-{index:03d}",
        "ea_name": f"EA_Dummy{index:03d}",
        "state": "idea",
        "parent_candidate": None,
        "feature_family": "synthetic-registry-padding",
        "lane": f"synthetic-{index:03d}",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "window": {"from": "2020.01.01", "to": "2020.01.02"},
        "model": None,
        "source_provenance": "Synthetic schema-valid padding row.",
        "source_path": None,
        "source_hash": None,
        "prereg_path": None,
        "prereg_sha256": None,
        "exact_overrides": "",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2,
            "max_trades_per_week": 5,
            "max_drawdown_pct": 6,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1,
            "max_monte_carlo_p95_dd_pct": 6,
        },
        "verdict": "SYNTHETIC_PADDING_ONLY",
        "reason": "Synthetic schema-valid padding row.",
        "updated_at_utc": "2020-01-01T00:00:00Z",
        "run_ids": [],
        "metrics": {},
        "validation": {},
    }


def _copy_file(workspace, relative):
    target = workspace / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / relative).read_bytes())
    return target


def _binding_file(workspace, relative, payload=None):
    if payload is None:
        target = _copy_file(workspace, relative)
    else:
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return _sha(target.read_bytes())


def _snapshot(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fixed_files = (
        "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_ACTIVE_SOURCE_CONTRACT_BUNDLE_V2.json",
        V2_PATH,
        V3_PATH,
        TASK_V5_PATH,
        "03. EA Developer/EA_TrendStackContinuation/research/project_trendstack_007_design_source.py",
        "03. EA Developer/EA_TrendStackContinuation/research/tests/test_project_trendstack_007_design_source.py",
        "03. EA Developer/EA_TrendStackContinuation/research/validate_trendstack_007_design_source.py",
        "03. EA Developer/EA_TrendStackContinuation/research/tests/test_validate_trendstack_007_design_source.py",
        "03. EA Developer/EA_TrendStackContinuation/research/supervise_trendstack_007_source_projection.py",
        "03. EA Developer/EA_TrendStackContinuation/research/tests/test_supervise_trendstack_007_source_projection.py",
        "02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002/public/design_manifest.jsonl",
        "02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002/public/design_receipt.json",
        "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-006_DESIGN_DATE_SELECTION.jsonl",
        "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_PROBE_PLAN_V6.md",
    )
    for relative in fixed_files:
        _copy_file(workspace, relative)
    receipt_sha = _binding_file(
        workspace,
        RECEIPT_PATH,
        _compact({"schema_version": "synthetic_review_receipt.v5", "verdict": "PASS"}),
    )
    bindings = {
        "active_contract_bundle_path": fixed_files[0],
        "active_contract_bundle_sha256": _sha((workspace / fixed_files[0]).read_bytes()),
        "authority_amendment_path": V2_PATH,
        "authority_amendment_sha256": _sha((workspace / V2_PATH).read_bytes()),
        "economic_access_authorized": False,
        "economics_authorized": False,
        "evidence_root": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_ATTEMPTS/HYP007-SOURCE-PROJECTION-7C4A91E6D2B80F35",
        "final_output_root": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_007_design_h1_1200",
        "holdout_authorized": False,
        "implementation_review_receipt_path": RECEIPT_PATH,
        "implementation_review_receipt_sha256": receipt_sha,
        "implementation_task_path": TASK_V5_PATH,
        "implementation_task_sha256": _sha((workspace / TASK_V5_PATH).read_bytes()),
        "model0_authorized": False,
        "network_allowed": False,
        "production_source_projection_authorized": True,
        "projection_attempt_id": "HYP007-SOURCE-PROJECTION-7C4A91E6D2B80F35",
        "projector_test_path": fixed_files[5],
        "projector_test_sha256": _sha((workspace / fixed_files[5]).read_bytes()),
        "projector_tool_path": fixed_files[4],
        "projector_tool_sha256": _sha((workspace / fixed_files[4]).read_bytes()),
        "public_manifest_path": fixed_files[10],
        "public_manifest_sha256": _sha((workspace / fixed_files[10]).read_bytes()),
        "public_receipt_path": fixed_files[11],
        "public_receipt_sha256": _sha((workspace / fixed_files[11]).read_bytes()),
        "registry_mutation_allowed": False,
        "research_holdout_authorized": False,
        "research_validation_authorized": False,
        "schema_version": "trendstack_007_source_run_bindings.v2",
        "selection_manifest_path": fixed_files[12],
        "selection_manifest_sha256": _sha((workspace / fixed_files[12]).read_bytes()),
        "source_projection_attempt_limit": 1,
        "source_run_authorized": True,
        "source_run_packet_review_required": True,
        "stage_root": "02. AlphaFactory/data/fivepercent/EURUSD/.trendstack_007_design_h1_1200.attempt-HYP007-SOURCE-PROJECTION-7C4A91E6D2B80F35",
        "subprocess_allowed": False,
        "supervisor_review_base_sha256": _sha((workspace / fixed_files[8]).read_bytes()),
        "supervisor_test_path": fixed_files[9],
        "supervisor_test_sha256": _sha((workspace / fixed_files[9]).read_bytes()),
        "supervisor_tool_path": fixed_files[8],
        "trading_mutation": False,
        "validation_authorized": False,
        "validator_test_path": fixed_files[7],
        "validator_test_sha256": _sha((workspace / fixed_files[7]).read_bytes()),
        "validator_tool_path": fixed_files[6],
        "validator_tool_sha256": _sha((workspace / fixed_files[6]).read_bytes()),
    }
    row285 = REGISTRY.read_bytes().splitlines(keepends=True)[284]
    prior = json.loads(row285)
    successor = copy.deepcopy(prior)
    successor["reason"] = "Authorize exactly one outcome-blind source projection; economics and downstream access remain closed."
    successor["updated_at_utc"] = "2026-07-28T23:59:59Z"
    successor["verdict"] = "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED"
    successor["validation"]["probe_status"] = "FROZEN_ONE_SHOT_SOURCE_PROJECTION_AUTHORIZED_PRE_PAYLOAD"
    successor["validation"]["source_run_authorized"] = True
    successor["validation"]["source_run_bindings"] = bindings
    successor_raw = _compact(successor)
    registry_payload = b"".join(_compact(_dummy_row(index)) for index in range(1, 285)) + row285 + successor_raw
    registry_path = workspace / "synthetic_registry.jsonl"
    registry_path.write_bytes(registry_payload)
    packet = {
        packet_key: bindings[row_key]
        for row_key, packet_key in ROW_TO_PACKET_V5.items()
    }
    packet.update({
        "authority_amendment_v3_path": V3_PATH,
        "authority_amendment_v3_sha256": _sha((workspace / V3_PATH).read_bytes()),
        "registry_sha256": _sha(registry_payload),
        "registry_row_index": 286,
        "registry_row_sha256": _sha(successor_raw[:-1]),
    })
    return {
        "bindings": bindings,
        "packet": packet,
        "prior": prior,
        "registry_path": registry_path,
        "registry_payload": registry_payload,
        "successor": successor,
        "successor_raw": successor_raw,
        "workspace": workspace,
    }


def _repair_snapshot(tmp_path):
    snapshot = _snapshot(tmp_path)
    workspace = snapshot["workspace"]
    for relative in (
        V4_PATH,
        TASK_V6_PATH,
        "04. Memory/research/CANDIDATE_REGISTRY.schema.json",
        "04. Memory/research/validate_candidate_registry.py",
        "03. EA Developer/EA_TrendStackContinuation/research/tests/test_hyp007_source_run_registry_transition.py",
    ):
        _copy_file(workspace, relative)
    _copy_file(workspace, RECEIPT_PATH)

    supervisor_path = workspace / snapshot["bindings"]["supervisor_tool_path"]
    supervisor_path.write_bytes(
        supervisor_path.read_bytes() + b"\n# synthetic reviewed V6 repair base\n"
    )
    supervisor_test_path = workspace / snapshot["bindings"]["supervisor_test_path"]
    repaired_supervisor_sha = _sha(supervisor_path.read_bytes())
    repaired_supervisor_test_sha = _sha(supervisor_test_path.read_bytes())

    receipt = {
        "schema_version": "trendstack_007_source_implementation_review_receipt.v6",
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
        "verdict": "PASS_FOR_PRODUCTION_SOURCE_RUN_PACKET_PREPARATION",
        "reviewed_authority": {
            "authority_repair_amendment_v4_sha256": _sha((workspace / V4_PATH).read_bytes()),
            "implementation_task_v6_sha256": _sha((workspace / TASK_V6_PATH).read_bytes()),
        },
        "reviewed_snapshot": {
            "registry_schema_sha256": _sha(
                (workspace / "04. Memory/research/CANDIDATE_REGISTRY.schema.json").read_bytes()
            ),
            "registry_validator_sha256": _sha(
                (workspace / "04. Memory/research/validate_candidate_registry.py").read_bytes()
            ),
            "registry_integration_test_sha256": _sha(
                (
                    workspace
                    / "03. EA Developer/EA_TrendStackContinuation/research/tests/test_hyp007_source_run_registry_transition.py"
                ).read_bytes()
            ),
            "supervisor_review_base_sha256": repaired_supervisor_sha,
            "supervisor_test_sha256": repaired_supervisor_test_sha,
        },
    }
    receipt_v6 = workspace / RECEIPT_V6_PATH
    receipt_v6.parent.mkdir(parents=True, exist_ok=True)
    receipt_v6.write_bytes(_compact(receipt))

    registry_rows = REGISTRY.read_bytes().splitlines(keepends=True)
    assert len(registry_rows) == 286
    row285 = registry_rows[284]
    row286 = registry_rows[285]
    prior = json.loads(row286)
    successor = copy.deepcopy(prior)
    successor["reason"] = (
        "Authorize the unchanged one-shot source projection after the reviewed "
        "pre-packet persistent-disarm repair; economics remain closed."
    )
    successor["updated_at_utc"] = "2026-07-28T23:59:59Z"
    successor["verdict"] = (
        "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    )
    successor["validation"]["probe_status"] = (
        "FROZEN_ONE_SHOT_SOURCE_PROJECTION_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    )
    bindings = successor["validation"]["source_run_bindings"]
    bindings.update({
        "implementation_review_receipt_path": RECEIPT_V6_PATH,
        "implementation_review_receipt_sha256": _sha(receipt_v6.read_bytes()),
        "implementation_task_path": TASK_V6_PATH,
        "implementation_task_sha256": _sha((workspace / TASK_V6_PATH).read_bytes()),
        "supervisor_review_base_sha256": repaired_supervisor_sha,
        "supervisor_test_sha256": repaired_supervisor_test_sha,
    })
    prior_bindings = prior["validation"]["source_run_bindings"]
    assert {
        key for key in bindings if bindings[key] != prior_bindings[key]
    } == {
        "implementation_review_receipt_path",
        "implementation_review_receipt_sha256",
        "implementation_task_path",
        "implementation_task_sha256",
        "supervisor_review_base_sha256",
        "supervisor_test_sha256",
    }
    successor_raw = _compact(successor)
    registry_payload = (
        b"".join(_compact(_dummy_row(index)) for index in range(1, 285))
        + row285
        + row286
        + successor_raw
    )
    registry_path = workspace / "synthetic_repair_registry.jsonl"
    registry_path.write_bytes(registry_payload)
    packet = {
        packet_key: bindings[row_key]
        for row_key, packet_key in ROW_TO_PACKET_V6.items()
    }
    packet.update({
        "authority_amendment_v3_path": V3_PATH,
        "authority_amendment_v3_sha256": _sha((workspace / V3_PATH).read_bytes()),
        "authority_repair_amendment_v4_path": V4_PATH,
        "authority_repair_amendment_v4_sha256": _sha((workspace / V4_PATH).read_bytes()),
        "implementation_task_v5_path": TASK_V5_PATH,
        "implementation_task_v5_sha256": _sha((workspace / TASK_V5_PATH).read_bytes()),
        "implementation_task_v6_path": TASK_V6_PATH,
        "implementation_task_v6_sha256": _sha((workspace / TASK_V6_PATH).read_bytes()),
        "registry_sha256": _sha(registry_payload),
        "registry_row_index": 287,
        "registry_row_sha256": _sha(successor_raw[:-1]),
        "supervisor_runtime_path": bindings["supervisor_tool_path"],
        "supervisor_tool_sha256": repaired_supervisor_sha,
    })
    return {
        "bindings": bindings,
        "packet": packet,
        "prior": prior,
        "registry_path": registry_path,
        "registry_payload": registry_payload,
        "successor": successor,
        "successor_raw": successor_raw,
        "workspace": workspace,
    }


def _canonical_errors(snapshot, successor=None):
    value = snapshot["successor"] if successor is None else successor
    payload = snapshot["registry_payload"][: -len(snapshot["successor_raw"])] + _compact(value)
    snapshot["registry_path"].write_bytes(payload)
    validator = _load_validator()
    validator.WORKSPACE = snapshot["workspace"]
    return validator.validate_registry(snapshot["registry_path"], SCHEMA)


def _canonical_repair_errors(snapshot, successor=None, existing_root_key=None):
    value = snapshot["successor"] if successor is None else successor
    payload = snapshot["registry_payload"][: -len(snapshot["successor_raw"])] + _compact(value)
    snapshot["registry_path"].write_bytes(payload)
    validator = _load_validator()
    validator.WORKSPACE = snapshot["workspace"]
    if existing_root_key is not None:
        expected = (
            snapshot["workspace"]
            / value["validation"]["source_run_bindings"][existing_root_key]
        ).resolve()
        actual_lexists = validator.os.path.lexists
        validator.os.path.lexists = lambda path: Path(path) == expected or actual_lexists(path)
    return validator.validate_registry(snapshot["registry_path"], SCHEMA)


def test_baseline_registry_remains_valid_at_286_rows():
    validator = _load_validator()
    assert validator.validate_registry(REGISTRY, SCHEMA) == []
    assert len(REGISTRY.read_bytes().splitlines()) == 286


def test_registry_schema_preserves_v2_shape_with_only_exact_v5_v6_path_variants():
    schema = json.loads(SCHEMA.read_bytes())
    amendment = json.loads((ROOT / V2_PATH).read_bytes())
    embedded = schema["properties"]["validation"]["properties"]["source_run_bindings"]
    expected = copy.deepcopy(amendment["source_run_bindings_json_schema"])
    expected["properties"]["implementation_review_receipt_path"] = {
        "enum": [RECEIPT_PATH, RECEIPT_V6_PATH]
    }
    expected["properties"]["implementation_task_path"] = {
        "enum": [TASK_V5_PATH, TASK_V6_PATH]
    }
    assert embedded == expected


def test_exact_initial_authorization_successor_remains_canonical_valid(tmp_path):
    snapshot = _snapshot(tmp_path)
    assert _canonical_errors(snapshot) == []


def test_exact_repair_successor_passes_canonical_and_supervisor_same_bytes(tmp_path):
    snapshot = _repair_snapshot(tmp_path)
    assert _canonical_repair_errors(snapshot) == []
    selected = supervisor.validate_registry_source_run_authority(
        snapshot["registry_payload"], snapshot["packet"]
    )
    assert selected["validation"]["source_run_bindings"] == snapshot["bindings"]


@pytest.mark.parametrize(
    "mutation",
    [
        "seventh_binding",
        "mixed_v5_v6_pair",
        "metric",
        "hypothesis",
        "economic_flag",
        "source",
        "run_ids",
    ],
)
def test_exact_repair_rejects_any_non_v4_diff(tmp_path, mutation):
    snapshot = _repair_snapshot(tmp_path)
    row = copy.deepcopy(snapshot["successor"])
    bindings = row["validation"]["source_run_bindings"]
    if mutation == "seventh_binding":
        bindings["network_allowed"] = True
    elif mutation == "mixed_v5_v6_pair":
        bindings["implementation_review_receipt_path"] = RECEIPT_PATH
        bindings["implementation_review_receipt_sha256"] = _sha(
            (snapshot["workspace"] / RECEIPT_PATH).read_bytes()
        )
    elif mutation == "metric":
        row["metrics"]["source_projection_attempts_consumed"] = 1
    elif mutation == "hypothesis":
        row["lane"] += "-drift"
    elif mutation == "economic_flag":
        bindings["economics_authorized"] = True
    elif mutation == "source":
        row["source_path"] = "unexpected/source.parquet"
    else:
        row["run_ids"] = ["unexpected"]
    assert _canonical_repair_errors(snapshot, row)


@pytest.mark.parametrize("root_key", ["stage_root", "final_output_root", "evidence_root"])
def test_exact_repair_requires_all_attempt_roots_absent(tmp_path, root_key):
    snapshot = _repair_snapshot(tmp_path)
    assert _canonical_repair_errors(snapshot, existing_root_key=root_key)


def test_second_repair_is_forbidden(tmp_path):
    snapshot = _repair_snapshot(tmp_path)
    later = copy.deepcopy(snapshot["successor"])
    later["reason"] += " second"
    later["updated_at_utc"] = "2026-07-29T00:00:00Z"
    payload = snapshot["registry_payload"] + _compact(later)
    snapshot["registry_path"].write_bytes(payload)
    validator = _load_validator()
    validator.WORKSPACE = snapshot["workspace"]
    assert validator.validate_registry(snapshot["registry_path"], SCHEMA)


@pytest.mark.parametrize(
    "mutation",
    ["exact_overrides", "metrics", "source", "model", "run_ids", "binding_extra", "binding_path", "binding_hash"],
)
def test_canonical_validator_rejects_prohibited_diff_or_binding_drift(tmp_path, mutation):
    snapshot = _snapshot(tmp_path)
    row = copy.deepcopy(snapshot["successor"])
    if mutation == "exact_overrides":
        row["exact_overrides"] += ";DRIFT"
    elif mutation == "metrics":
        row["metrics"]["economics_opened"] = True
    elif mutation == "source":
        row["source_path"] = "unexpected/source.parquet"
    elif mutation == "model":
        row["model"] = 0
    elif mutation == "run_ids":
        row["run_ids"] = ["unexpected"]
    elif mutation == "binding_extra":
        row["validation"]["source_run_bindings"]["extra"] = False
    elif mutation == "binding_path":
        row["validation"]["source_run_bindings"]["projector_tool_path"] = "../escape.py"
    elif mutation == "binding_hash":
        row["validation"]["source_run_bindings"]["projector_tool_sha256"] = "F" * 64
    assert _canonical_errors(snapshot, row)


@pytest.mark.parametrize("mutation", ["backslash", "absolute", "missing", "stale", "invalid_sha"])
def test_manual_binding_checks_reject_path_or_file_identity_drift(tmp_path, mutation):
    snapshot = _snapshot(tmp_path)
    row = copy.deepcopy(snapshot["successor"])
    bindings = row["validation"]["source_run_bindings"]
    receipt = snapshot["workspace"] / RECEIPT_PATH
    if mutation == "backslash":
        bindings["implementation_review_receipt_path"] = RECEIPT_PATH.replace("/", "\\")
    elif mutation == "absolute":
        bindings["implementation_review_receipt_path"] = "C:/escape/receipt.json"
    elif mutation == "missing":
        receipt.unlink()
    elif mutation == "stale":
        receipt.write_bytes(receipt.read_bytes() + b"drift")
    else:
        bindings["implementation_review_receipt_sha256"] = "not-a-sha"
    assert _canonical_errors(snapshot, row)


@pytest.mark.parametrize("relative", [V2_PATH, V3_PATH, TASK_V5_PATH])
def test_manual_validator_rejects_stale_amendment_or_task_file(tmp_path, relative):
    snapshot = _snapshot(tmp_path)
    target = snapshot["workspace"] / relative
    target.write_bytes(target.read_bytes() + b"drift")
    assert _canonical_errors(snapshot)


def test_manual_validator_rejects_armed_supervisor_even_when_hash_is_rebound(tmp_path):
    snapshot = _snapshot(tmp_path)
    row = copy.deepcopy(snapshot["successor"])
    relative = row["validation"]["source_run_bindings"]["supervisor_tool_path"]
    target = snapshot["workspace"] / relative
    disarmed = b"REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None"
    armed = b'REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = "' + b"A" * 64 + b'"'
    payload = target.read_bytes().replace(disarmed, armed)
    assert payload != target.read_bytes()
    target.write_bytes(payload)
    row["validation"]["source_run_bindings"]["supervisor_review_base_sha256"] = _sha(payload)
    assert _canonical_errors(snapshot, row)


@pytest.mark.parametrize(
    "mutation",
    ["generic_probe_probe", "other_hypothesis", "wrong_prior", "second_authorization", "true_to_false"],
)
def test_one_use_transition_exception_rejects_every_neighboring_transition(tmp_path, mutation):
    snapshot = _snapshot(tmp_path)
    prefix = snapshot["registry_payload"][: -len(snapshot["successor_raw"])]
    successor = copy.deepcopy(snapshot["successor"])
    payload = prefix + snapshot["successor_raw"]
    if mutation == "generic_probe_probe":
        successor["validation"] = copy.deepcopy(snapshot["prior"]["validation"])
        successor["verdict"] = snapshot["prior"]["verdict"]
        payload = prefix + _compact(successor)
    elif mutation == "other_hypothesis":
        successor["hypothesis_id"] = "HYP-OTHER-SOURCE-RUN-001"
        payload = prefix + _compact(successor)
    elif mutation == "wrong_prior":
        wrong_prior = copy.deepcopy(snapshot["prior"])
        wrong_prior["reason"] += " drift"
        padding = prefix[: -len(REGISTRY.read_bytes().splitlines(keepends=True)[284])]
        payload = padding + _compact(wrong_prior) + snapshot["successor_raw"]
    else:
        later = copy.deepcopy(snapshot["successor"])
        later["reason"] += " second"
        later["updated_at_utc"] = "2026-07-29T00:00:00Z"
        if mutation == "true_to_false":
            later["validation"]["source_run_authorized"] = False
            later["validation"].pop("source_run_bindings")
        payload += _compact(later)
    snapshot["registry_path"].write_bytes(payload)
    validator = _load_validator()
    validator.WORKSPACE = snapshot["workspace"]
    assert validator.validate_registry(snapshot["registry_path"], SCHEMA)


def test_supervisor_rejects_every_row_packet_mapping_group_before_authority_pass(tmp_path):
    snapshot = _repair_snapshot(tmp_path)
    assert len(ROW_TO_PACKET_V6) == len(supervisor.SOURCE_RUN_BINDING_TO_PACKET) == 43
    assert len(snapshot["bindings"]) == 46
    for row_key, packet_key in ROW_TO_PACKET_V6.items():
        packet = dict(snapshot["packet"])
        current = packet[packet_key]
        if isinstance(current, bool):
            packet[packet_key] = not current
        elif isinstance(current, str) and current.endswith("_sha256"):
            packet[packet_key] = "F" * 64
        elif packet_key.endswith("_sha256"):
            packet[packet_key] = "F" * 64
        else:
            packet[packet_key] = str(current) + ".drift"
        with pytest.raises(Exception):
            supervisor.validate_registry_source_run_authority(snapshot["registry_payload"], packet)
