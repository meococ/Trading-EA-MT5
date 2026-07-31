"""One-shot, fail-closed supervisor mechanics for HYP007 source projection.

The production packet remains disarmed in source.  The callable orchestration
surface accepts injected operations so lifecycle ordering and self-disarm can
be proven entirely with synthetic fixtures and without opening market payloads.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


HEX = frozenset("0123456789ABCDEF")
METADATA_FILES = (
    "projection_requests.jsonl",
    "projection_request_receipt.json",
    "design_1200_manifest.jsonl",
    "design_1200_source_trace.jsonl",
    "design_1200_reconciliation.json",
    "design_1200_projector_receipt.json",
)
SOURCE_RUN_PACKET_FIELDS = (
    "schema_version",
    "hypothesis_id",
    "projection_attempt_id",
    "workspace_root_path",
    "workspace_root_identity",
    "registry_path",
    "registry_sha256",
    "registry_row_index",
    "registry_row_sha256",
    "active_plan_path",
    "active_plan_sha256",
    "superseded_plan_sha256s",
    "contract_v4_path",
    "contract_v4_sha256",
    "contract_v5_path",
    "contract_v5_sha256",
    "contract_v6_path",
    "contract_v6_sha256",
    "contract_v7_path",
    "contract_v7_sha256",
    "superseded_contract_sha256s",
    "active_contract_bundle_path",
    "active_contract_bundle_sha256",
    "implementation_task_v1_path",
    "implementation_task_v1_sha256",
    "implementation_task_v2_path",
    "implementation_task_v2_sha256",
    "implementation_task_v3_path",
    "implementation_task_v3_sha256",
    "implementation_task_v4_path",
    "implementation_task_v4_sha256",
    "authority_amendment_v2_path",
    "authority_amendment_v2_sha256",
    "authority_amendment_v3_path",
    "authority_amendment_v3_sha256",
    "implementation_task_v5_path",
    "implementation_task_v5_sha256",
    "authority_repair_amendment_v4_path",
    "authority_repair_amendment_v4_sha256",
    "implementation_task_v6_path",
    "implementation_task_v6_sha256",
    "projector_tool_path",
    "projector_tool_sha256",
    "projector_test_path",
    "projector_test_sha256",
    "validator_tool_path",
    "validator_tool_sha256",
    "validator_test_path",
    "validator_test_sha256",
    "supervisor_tool_path",
    "supervisor_tool_sha256",
    "supervisor_test_path",
    "supervisor_test_sha256",
    "supervisor_review_base_sha256",
    "supervisor_runtime_sha256",
    "clock_path",
    "clock_sha256",
    "active_contract_path",
    "active_contract_sha256",
    "task_packet_path",
    "task_packet_sha256",
    "public_receipt_path",
    "public_receipt_sha256",
    "public_manifest_path",
    "public_manifest_sha256",
    "selection_manifest_path",
    "selection_manifest_sha256",
    "implementation_review_receipt_path",
    "implementation_review_receipt_sha256",
    "expected_dates",
    "expected_unselected_dates",
    "expected_date_set_sha256",
    "first_date",
    "last_date",
    "stage_root",
    "final_output_root",
    "evidence_root",
    "supervisor_runtime_path",
    "reviewed_source_run_packet_sha256",
    "production_source_projection_authorized",
    "source_run_authorized",
    "economic_access_authorized",
    "economics_authorized",
    "validation_authorized",
    "holdout_authorized",
    "research_validation_authorized",
    "research_holdout_authorized",
    "mql5_authorized",
    "model0_authorized",
    "network_allowed",
    "subprocess_allowed",
    "registry_mutation_allowed",
    "trading_mutation",
)
SOURCE_RUN_PACKET_DEFAULTS = {
    "schema_version": "trendstack_007_source_run_packet.v2",
    "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-007",
    "projection_attempt_id": "HYP007-SOURCE-PROJECTION-7C4A91E6D2B80F35",
    "workspace_root_path": ".",
    "workspace_root_identity": [1, 2, 0],
    "registry_path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    "active_plan_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_PROBE_PLAN_V6.md",
    "active_plan_sha256": "FE740C0811E7060670D1F771802EAC5ADD6D5B2CD9DB0FDABD7E48A8A2D29735",
    "superseded_plan_sha256s": [
        "8A3BB9AC6BCC015972856A9EA9882A6DA64D961C35FFE3936FBF2DC21D082603",
        "B20671C2D57014CC605CF956A368352519D179381310919306B489AC5182571E",
        "59C8EE2BDBA108492067704593A466EFC099111294FC10220326A8115DF409A0",
        "B82673A0D1F492D9BBFA0EA044EBA8B55F33ADFE614E58F62C71FD936CA3D80E",
        "0D143CE01DF6C97397C852B40177A47654FB36411E011A8BE4B91307AA04B099",
    ],
    "contract_v4_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V4.json",
    "contract_v4_sha256": "2F3D071F5E079B49B5705D47BABFFCC7F65998744AA0E1E9352389F89EA1EADB",
    "contract_v5_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V5.json",
    "contract_v5_sha256": "8B9B6391A79E699DB21A80D14223B6ACAA24287390ECE4A0D8602DD758F4631C",
    "contract_v6_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V6.json",
    "contract_v6_sha256": "4AC471AB7ABBCD84F008819D969EE6AF2A78DDAD15B87294CE0BECFAD6D8B828",
    "contract_v7_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_CONTRACT_V7.json",
    "contract_v7_sha256": "4ABAFB55831C01354BFD432864C236C2A5B236EFF9FFDA2A1921DEABD167ED62",
    "superseded_contract_sha256s": [
        "552C38E9F3DD8087C8D0A3F04F0780449D819799982FCDF961DF1356E4C4E39A",
        "8E1B3A909F9B87C045EC2A5B25D6E5F22F853F021B04148C72D6F6AB7977D6A4",
        "A43D7DFCC5154015D94793097A6E90F92C240DB4FCBDB814E48640BA72A3EDC5",
    ],
    "implementation_task_v1_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V1.json",
    "implementation_task_v1_sha256": "1A965777AF7D3E741813E3EE30E803FB55112F168280E25F07D2342A09007455",
    "implementation_task_v2_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V2.json",
    "implementation_task_v2_sha256": "E379A9579861F655B14473FE786938ECA39FD76CC685791E81303CBB00B2753C",
    "implementation_task_v3_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V3.json",
    "implementation_task_v3_sha256": "D5AEE13EF9DE1CC57A907C888694D5177C8AFC99222F0D01F5C8A93F73614AFC",
    "implementation_task_v4_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V4.json",
    "implementation_task_v4_sha256": "756DE35381CADC773CB5FF6EEE5BF1F3E9531E967AA0369626E96D6572DB163A",
    "authority_amendment_v2_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_AMENDMENT_V2.json",
    "authority_amendment_v2_sha256": "F399FF28A3ADCE35FD13111EC9EA6F3C33269415379F365BEFCC58F0319F3FFD",
    "authority_amendment_v3_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_AMENDMENT_V3.json",
    "authority_amendment_v3_sha256": "FA8F5A7E65C0D54E3BE20802BEC096528C1BD424961D1C615491CAF63E90C8AE",
    "implementation_task_v5_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V5.json",
    "implementation_task_v5_sha256": "E572E49FDE06717C396112FBD7D0278C0F59605369651825447C1913D241B725",
    "authority_repair_amendment_v4_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_REPAIR_AMENDMENT_V4.json",
    "authority_repair_amendment_v4_sha256": "3B9FB4C9D4469FBF612195C33FAF6771299DAC277D07CD3EA124F2C98989DBA8",
    "implementation_task_v6_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V6.json",
    "implementation_task_v6_sha256": "6CB1024E30A620D33A66D678AC7A24ECE2F3872F98E1F0F4FE8D2E23AE7EC892",
    "task_packet_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V4.json",
    "task_packet_sha256": "756DE35381CADC773CB5FF6EEE5BF1F3E9531E967AA0369626E96D6572DB163A",
    "projector_tool_path": "03. EA Developer/EA_TrendStackContinuation/research/project_trendstack_007_design_source.py",
    "projector_test_path": "03. EA Developer/EA_TrendStackContinuation/research/tests/test_project_trendstack_007_design_source.py",
    "validator_tool_path": "03. EA Developer/EA_TrendStackContinuation/research/validate_trendstack_007_design_source.py",
    "validator_test_path": "03. EA Developer/EA_TrendStackContinuation/research/tests/test_validate_trendstack_007_design_source.py",
    "supervisor_tool_path": "03. EA Developer/EA_TrendStackContinuation/research/supervise_trendstack_007_source_projection.py",
    "supervisor_runtime_path": "03. EA Developer/EA_TrendStackContinuation/research/supervise_trendstack_007_source_projection.py",
    "supervisor_test_path": "03. EA Developer/EA_TrendStackContinuation/research/tests/test_supervise_trendstack_007_source_projection.py",
    "clock_path": "02. AlphaFactory/tools/research/fivepercent_server_clock.py",
    "clock_sha256": "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52",
    "public_receipt_path": "02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002/public/design_receipt.json",
    "public_receipt_sha256": "623328512F0CB77B52B155F6CD314EA2B47DAC40636A7714BD38167BEA807B13",
    "public_manifest_path": "02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002/public/design_manifest.jsonl",
    "public_manifest_sha256": "DA513911B01B1C4232611225C77A4F22E9E3C89E719EE530923BD574D06451E5",
    "selection_manifest_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-006_DESIGN_DATE_SELECTION.jsonl",
    "selection_manifest_sha256": "D99C21ED2611A70D9F225170997EAADDD6567827B69759A1DFA9EA7F73C7A135",
    "expected_dates": 1297,
    "expected_unselected_dates": 258,
    "expected_date_set_sha256": "4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A",
    "first_date": "2016-01-04",
    "last_date": "2020-12-31",
    "final_output_root": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_007_design_h1_1200",
    "production_source_projection_authorized": True,
    "source_run_authorized": True,
    "economic_access_authorized": False,
    "economics_authorized": False,
    "validation_authorized": False,
    "holdout_authorized": False,
    "research_validation_authorized": False,
    "research_holdout_authorized": False,
    "mql5_authorized": False,
    "model0_authorized": False,
    "network_allowed": False,
    "subprocess_allowed": False,
    "registry_mutation_allowed": False,
    "trading_mutation": False,
}
HYP007_PRIOR_ROW_INDEX = 285
HYP007_PRIOR_ROW_SHA256 = "6D72D93644BF6C61D3D966013348FF272F3A78D13DE7444CB245A6809EB722DA"
HYP007_AUTHORIZED_ROW_INDEX = 286
HYP007_AUTHORIZED_ROW_SHA256 = "17512FE256454130E3EAE26D2372818631487D67EEB0F8B414D255FE2D5CA06E"
HYP007_REPAIR_BINDING_CHANGES = {
    "implementation_review_receipt_path",
    "implementation_review_receipt_sha256",
    "implementation_task_path",
    "implementation_task_sha256",
    "supervisor_review_base_sha256",
    "supervisor_test_sha256",
}
RECEIPT_V6_BINDING_PATHS = {
    "registry_schema": "04. Memory/research/CANDIDATE_REGISTRY.schema.json",
    "registry_validator": "04. Memory/research/validate_candidate_registry.py",
    "registry_integration_test": "03. EA Developer/EA_TrendStackContinuation/research/tests/test_hyp007_source_run_registry_transition.py",
}
IMPLEMENTATION_REVIEW_RECEIPT_V6_PATH = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT_V6.json"
)
SOURCE_RUN_BINDING_TO_PACKET = {
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
    "implementation_task_path": "implementation_task_v6_path",
    "implementation_task_sha256": "implementation_task_v6_sha256",
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
SOURCE_RUN_BINDING_CONSTANTS = {
    "schema_version": "trendstack_007_source_run_bindings.v2",
    "source_projection_attempt_limit": 1,
    "source_run_packet_review_required": True,
}


class InvalidSourceProjection(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedSourceRunPacket:
    values: dict[str, object]
    detached_sha256: str
    canonical_payload: bytes


REVIEWED_SOURCE_RUN_PACKET_SHA256: str | None = None


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except Exception as exc:
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json_object(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(
        payload.decode("utf-8", errors="strict"),
        object_pairs_hook=_pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
    )
    if type(value) is not dict or canonical_json(value) + b"\n" != payload:
        raise ValueError
    return value


def canonical_registry_row_sha256(record: bytes) -> str:
    """Hash one repository-ordered compact JSONL object without its LF."""

    try:
        _repository_ordered_registry_record(record)
        return sha256_bytes(record[:-1])
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _repository_ordered_registry_record(record: bytes) -> dict[str, object]:
    value = _strict_registry_record(record)
    body = record[:-1]
    compact = json.dumps(
        value, sort_keys=False, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")
    if compact != body:
        raise ValueError
    return value


def _strict_registry_record(record: bytes) -> dict[str, object]:
    if type(record) is not bytes or not record.endswith(b"\n") or record.count(b"\n") != 1:
        raise ValueError
    body = record[:-1]
    value = json.loads(
        body.decode("utf-8", errors="strict"),
        object_pairs_hook=_pairs,
        parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
    )
    if type(value) is not dict:
        raise ValueError
    return value


def validate_registry_source_run_authority(
    registry_payload: bytes,
    packet_values: dict[str, object],
) -> dict[str, object]:
    """Prove the packet-selected latest HYP007 row grants one bounded source run."""

    try:
        if type(registry_payload) is not bytes or not registry_payload or type(packet_values) is not dict:
            raise ValueError
        records = registry_payload.splitlines(keepends=True)
        if not records or b"".join(records) != registry_payload:
            raise ValueError
        rows = [_strict_registry_record(record) for record in records]
        row_index = packet_values.get("registry_row_index")
        row_sha = packet_values.get("registry_row_sha256")
        if (
            type(row_index) is not int or isinstance(row_index, bool) or row_index <= 0
            or row_index > len(rows) or not _valid_sha(row_sha)
            or not _valid_sha(packet_values.get("registry_sha256"))
            or sha256_bytes(registry_payload) != packet_values["registry_sha256"]
            or canonical_registry_row_sha256(records[row_index - 1]) != row_sha
        ):
            raise ValueError
        latest = [
            index for index, row in enumerate(rows, start=1)
            if row.get("record_type") == "hypothesis_state"
            and row.get("hypothesis_id") == SOURCE_RUN_PACKET_DEFAULTS["hypothesis_id"]
        ]
        if not latest or row_index != latest[-1] or row_index != HYP007_AUTHORIZED_ROW_INDEX + 1:
            raise ValueError
        prior_record = records[HYP007_AUTHORIZED_ROW_INDEX - 1]
        if canonical_registry_row_sha256(prior_record) != HYP007_AUTHORIZED_ROW_SHA256:
            raise ValueError
        prior = _repository_ordered_registry_record(prior_record)
        row = _repository_ordered_registry_record(records[row_index - 1])
        allowed_root_changes = {"reason", "updated_at_utc", "validation", "verdict"}
        allowed_validation_changes = {"probe_status", "source_run_bindings"}
        prior_validation = prior.get("validation")
        validation = row.get("validation")
        if (
            prior.get("record_type") != "hypothesis_state"
            or prior.get("schema_version") != "alphafactory_candidate_registry.v1"
            or prior.get("hypothesis_id") != SOURCE_RUN_PACKET_DEFAULTS["hypothesis_id"]
            or prior.get("state") != "probe" or row.get("state") != "probe"
            or set(prior) != set(row)
            or any(prior.get(key) != row.get(key) for key in set(prior) - allowed_root_changes)
            or type(prior_validation) is not dict or type(validation) is not dict
            or set(validation) != set(prior_validation)
            or any(
                prior_validation.get(key) != validation.get(key)
                for key in set(prior_validation) - allowed_validation_changes
            )
            or prior_validation.get("source_build_authorized") is not True
            or validation.get("source_build_authorized") is not True
            or prior_validation.get("source_run_authorized") is not True
            or validation.get("source_run_authorized") is not True
            or validation.get("probe_status")
            != "FROZEN_ONE_SHOT_SOURCE_PROJECTION_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
            or row.get("verdict")
            != "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
            or type(row.get("reason")) is not str or not row["reason"] or row["reason"] == prior.get("reason")
            or not str(row.get("updated_at_utc", "")).endswith("Z")
            or datetime.fromisoformat(str(row["updated_at_utc"]).replace("Z", "+00:00"))
            <= datetime.fromisoformat(str(prior["updated_at_utc"]).replace("Z", "+00:00"))
        ):
            raise ValueError
        prior_bindings = prior_validation.get("source_run_bindings")
        bindings = validation.get("source_run_bindings")
        if type(prior_bindings) is not dict or type(bindings) is not dict:
            raise ValueError
        changed_bindings = {
            key
            for key in set(prior_bindings) | set(bindings)
            if prior_bindings.get(key) != bindings.get(key)
        }
        if (
            set(prior_bindings) != set(bindings)
            or changed_bindings != HYP007_REPAIR_BINDING_CHANGES
            or set(bindings) != set(SOURCE_RUN_BINDING_TO_PACKET) | set(SOURCE_RUN_BINDING_CONSTANTS)
            or any(bindings[row_key] != packet_values.get(packet_key) for row_key, packet_key in SOURCE_RUN_BINDING_TO_PACKET.items())
            or any(bindings[key] != value for key, value in SOURCE_RUN_BINDING_CONSTANTS.items())
            or packet_values.get("authority_amendment_v2_path") != SOURCE_RUN_PACKET_DEFAULTS["authority_amendment_v2_path"]
            or packet_values.get("authority_amendment_v2_sha256") != SOURCE_RUN_PACKET_DEFAULTS["authority_amendment_v2_sha256"]
            or packet_values.get("authority_amendment_v3_path") != SOURCE_RUN_PACKET_DEFAULTS["authority_amendment_v3_path"]
            or packet_values.get("authority_amendment_v3_sha256") != SOURCE_RUN_PACKET_DEFAULTS["authority_amendment_v3_sha256"]
            or packet_values.get("implementation_task_v5_path") != SOURCE_RUN_PACKET_DEFAULTS["implementation_task_v5_path"]
            or packet_values.get("implementation_task_v5_sha256") != SOURCE_RUN_PACKET_DEFAULTS["implementation_task_v5_sha256"]
            or packet_values.get("authority_repair_amendment_v4_path")
            != SOURCE_RUN_PACKET_DEFAULTS["authority_repair_amendment_v4_path"]
            or packet_values.get("authority_repair_amendment_v4_sha256")
            != SOURCE_RUN_PACKET_DEFAULTS["authority_repair_amendment_v4_sha256"]
            or packet_values.get("implementation_task_v6_path")
            != SOURCE_RUN_PACKET_DEFAULTS["implementation_task_v6_path"]
            or packet_values.get("implementation_task_v6_sha256")
            != SOURCE_RUN_PACKET_DEFAULTS["implementation_task_v6_sha256"]
            or bindings.get("implementation_review_receipt_path")
            != IMPLEMENTATION_REVIEW_RECEIPT_V6_PATH
            or bindings.get("implementation_task_path")
            != SOURCE_RUN_PACKET_DEFAULTS["implementation_task_v6_path"]
            or bindings.get("implementation_task_sha256")
            != SOURCE_RUN_PACKET_DEFAULTS["implementation_task_v6_sha256"]
            or packet_values.get("supervisor_tool_path")
            != packet_values.get("supervisor_runtime_path")
            or packet_values.get("supervisor_tool_sha256")
            != packet_values.get("supervisor_review_base_sha256")
            or len(SOURCE_RUN_BINDING_TO_PACKET) != 43
            or len(bindings) != 46
        ):
            raise ValueError
        return row
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _strict_json_document(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
        )
        if type(value) is not dict:
            raise ValueError
        return value
    except Exception as exc:
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in HEX for char in value)


def _valid_attempt(value: object) -> bool:
    prefix = "HYP007-SOURCE-PROJECTION-"
    return (
        type(value) is str and value.startswith(prefix) and len(value) == len(prefix) + 16
        and all(char in HEX for char in value[len(prefix):])
    )


def compute_source_run_packet_sha256(packet: dict[str, object]) -> str:
    """Compute the detached digest with its embedded digest slot zeroed."""

    try:
        if type(packet) is not dict or set(packet) != set(SOURCE_RUN_PACKET_FIELDS):
            raise ValueError
        normalized = {
            key: value
            for key, value in packet.items()
            if key not in {"reviewed_source_run_packet_sha256", "supervisor_runtime_sha256"}
        }
        return sha256_bytes(canonical_json(normalized) + b"\n")
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _relative_path(value: object) -> bool:
    if type(value) is not str or not value or "\x00" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ":" not in value and all(part not in ("", ".", "..") for part in path.parts)


def validate_source_run_packet_document(payload: bytes, reviewed_sha256: str) -> VerifiedSourceRunPacket:
    try:
        if not _valid_sha(reviewed_sha256):
            raise ValueError
        packet = _json_object(payload)
        if set(packet) != set(SOURCE_RUN_PACKET_FIELDS):
            raise ValueError
        frozen_fields = (
            "schema_version", "hypothesis_id", "workspace_root_path", "registry_path",
            "active_plan_path", "active_plan_sha256",
            "superseded_plan_sha256s", "contract_v4_path", "contract_v4_sha256",
            "contract_v5_path", "contract_v5_sha256", "contract_v6_path", "contract_v6_sha256",
            "contract_v7_path", "contract_v7_sha256",
            "superseded_contract_sha256s", "implementation_task_v1_path",
            "implementation_task_v1_sha256", "implementation_task_v2_path",
            "implementation_task_v2_sha256", "implementation_task_v3_path",
            "implementation_task_v3_sha256", "implementation_task_v4_path",
            "implementation_task_v4_sha256", "authority_amendment_v2_path",
            "authority_amendment_v2_sha256", "authority_amendment_v3_path",
            "authority_amendment_v3_sha256", "implementation_task_v5_path",
            "implementation_task_v5_sha256", "authority_repair_amendment_v4_path",
            "authority_repair_amendment_v4_sha256", "implementation_task_v6_path",
            "implementation_task_v6_sha256", "task_packet_path", "task_packet_sha256",
            "projector_tool_path", "projector_test_path", "validator_tool_path",
            "validator_test_path", "supervisor_tool_path", "supervisor_runtime_path",
            "supervisor_test_path", "clock_path", "clock_sha256", "public_receipt_path",
            "public_receipt_sha256", "public_manifest_path", "public_manifest_sha256",
            "selection_manifest_path", "selection_manifest_sha256", "expected_dates",
            "expected_unselected_dates", "expected_date_set_sha256", "first_date", "last_date",
            "final_output_root", "production_source_projection_authorized", "source_run_authorized",
            "economic_access_authorized", "economics_authorized", "validation_authorized",
            "holdout_authorized", "research_validation_authorized", "research_holdout_authorized",
            "mql5_authorized", "model0_authorized", "network_allowed", "subprocess_allowed",
            "registry_mutation_allowed", "trading_mutation",
        )
        if (
            any(packet[field] != SOURCE_RUN_PACKET_DEFAULTS[field] for field in frozen_fields)
            or packet["schema_version"] != SOURCE_RUN_PACKET_DEFAULTS["schema_version"]
            or packet["hypothesis_id"] != SOURCE_RUN_PACKET_DEFAULTS["hypothesis_id"]
            or not _valid_attempt(packet["projection_attempt_id"])
            or packet["production_source_projection_authorized"] is not True
            or packet["source_run_authorized"] is not True
            or packet["economic_access_authorized"] is not False
            or packet["workspace_root_path"] != "."
            or type(packet["workspace_root_identity"]) is not list
            or len(packet["workspace_root_identity"]) != 3
            or any(type(value) is not int for value in packet["workspace_root_identity"])
            or type(packet["registry_row_index"]) is not int
            or isinstance(packet["registry_row_index"], bool)
            or packet["registry_row_index"] <= 0
            or not _valid_sha(packet["registry_row_sha256"])
            or type(packet["superseded_plan_sha256s"]) is not list
            or any(not _valid_sha(value) for value in packet["superseded_plan_sha256s"])
            or type(packet["superseded_contract_sha256s"]) is not list
            or any(not _valid_sha(value) for value in packet["superseded_contract_sha256s"])
            or packet["expected_dates"] != 1297
            or packet["expected_unselected_dates"] != 258
            or packet["expected_date_set_sha256"] != SOURCE_RUN_PACKET_DEFAULTS["expected_date_set_sha256"]
            or packet["first_date"] != "2016-01-04"
            or packet["last_date"] != "2020-12-31"
            or any(packet[field] is not False for field in (
                "economics_authorized", "validation_authorized", "holdout_authorized",
                "research_validation_authorized", "research_holdout_authorized", "mql5_authorized",
                "model0_authorized", "network_allowed", "subprocess_allowed",
                "registry_mutation_allowed", "trading_mutation",
            ))
            or packet["stage_root"] != (
                "02. AlphaFactory/data/fivepercent/EURUSD/.trendstack_007_design_h1_1200.attempt-"
                + packet["projection_attempt_id"]
            )
            or packet["evidence_root"] != (
                "03. EA Developer/EA_TrendStackContinuation/research/evidence/"
                "HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_ATTEMPTS/"
                + packet["projection_attempt_id"]
            )
        ):
            raise ValueError
        for field in SOURCE_RUN_PACKET_FIELDS:
            value = packet[field]
            if field.endswith("_sha256") and not _valid_sha(value):
                raise ValueError
            if (
                (field.endswith("_path") or field.endswith("_root"))
                and field != "workspace_root_path" and not _relative_path(value)
            ):
                raise ValueError
        detached = compute_source_run_packet_sha256(packet)
        if (
            detached != reviewed_sha256
            or packet["reviewed_source_run_packet_sha256"] != reviewed_sha256
        ):
            raise ValueError
        return VerifiedSourceRunPacket(dict(packet), detached, payload)
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _reparse(info: os.stat_result) -> bool:
    return bool(int(getattr(info, "st_file_attributes", 0)) & 0x400)


def _directory_identity(info: os.stat_result) -> tuple[int, int, int]:
    return (
        int(info.st_dev), int(info.st_ino),
        int(getattr(info, "st_file_attributes", 0)),
    )


def _inside(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(root)))) == os.path.normcase(str(root))
    except ValueError:
        return False


def bind_existing_ancestor_chain(
    workspace_root: Path | str,
    target_path: Path | str,
) -> tuple[tuple[Path, tuple[int, int, int]], ...]:
    """Bind every currently existing directory from workspace to target."""

    try:
        workspace = Path(workspace_root).absolute()
        target = Path(target_path).absolute()
        if target == workspace or not _inside(target, workspace):
            raise ValueError
        root_info = os.lstat(workspace)
        if not stat.S_ISDIR(root_info.st_mode) or workspace.is_symlink() or _reparse(root_info):
            raise ValueError
        device = int(root_info.st_dev)
        anchors = [(workspace, _directory_identity(root_info))]
        current = workspace
        missing_seen = False
        for component in target.relative_to(workspace).parts:
            if component in ("", ".", "..") or ":" in component:
                raise ValueError
            current = current / component
            if not os.path.lexists(current):
                missing_seen = True
                continue
            if missing_seen:
                raise ValueError
            info = os.lstat(current)
            if (
                not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _reparse(info)
                or int(info.st_dev) != device
            ):
                raise ValueError
            anchors.append((current, _directory_identity(info)))
        return tuple(anchors)
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def verify_existing_ancestor_chain(
    anchors: tuple[tuple[Path, tuple[int, int, int]], ...],
) -> None:
    try:
        if type(anchors) is not tuple or not anchors:
            raise ValueError
        for path, identity in anchors:
            info = os.lstat(path)
            if (
                not stat.S_ISDIR(info.st_mode) or path.is_symlink() or _reparse(info)
                or _directory_identity(info) != identity
            ):
                raise ValueError
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _safe_create_root(
    workspace_root: Path,
    target: Path,
    anchors: tuple[tuple[Path, tuple[int, int, int]], ...],
) -> None:
    try:
        if os.path.lexists(target):
            raise ValueError
        verify_existing_ancestor_chain(anchors)
        current = workspace_root
        for component in target.relative_to(workspace_root).parts:
            current = current / component
            if current == target:
                os.mkdir(current)
            elif not os.path.lexists(current):
                os.mkdir(current)
            info = os.lstat(current)
            if (
                not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _reparse(info)
                or int(info.st_dev) != int(os.lstat(workspace_root).st_dev)
            ):
                raise ValueError
        verify_existing_ancestor_chain(anchors)
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _stable_authority_read(path_value: Path | str) -> bytes:
    """Read one authority document through an identity-bound file handle."""

    try:
        path = Path(path_value).absolute()
        parent = path.parent
        parent_info = os.lstat(parent)
        before = os.lstat(path)
        if (
            not stat.S_ISDIR(parent_info.st_mode) or parent.is_symlink() or _reparse(parent_info)
            or not stat.S_ISREG(before.st_mode) or path.is_symlink() or _reparse(before)
            or int(before.st_nlink) != 1
        ):
            raise ValueError
        anchor = (
            int(before.st_dev), int(before.st_ino), int(before.st_size),
            int(before.st_mtime_ns), int(before.st_nlink),
            int(getattr(before, "st_file_attributes", 0)),
        )
        parent_anchor = (
            int(parent_info.st_dev), int(parent_info.st_ino), int(parent_info.st_mtime_ns),
            int(getattr(parent_info, "st_file_attributes", 0)),
        )
        flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            opened_anchor = (
                int(opened.st_dev), int(opened.st_ino), int(opened.st_size),
                int(opened.st_mtime_ns), int(opened.st_nlink),
                int(getattr(opened, "st_file_attributes", 0)),
            )
            if opened_anchor != anchor:
                raise ValueError
            chunks = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            final = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        final_anchor = (
            int(final.st_dev), int(final.st_ino), int(final.st_size),
            int(final.st_mtime_ns), int(final.st_nlink),
            int(getattr(final, "st_file_attributes", 0)),
        )
        after = os.lstat(path)
        after_anchor = (
            int(after.st_dev), int(after.st_ino), int(after.st_size),
            int(after.st_mtime_ns), int(after.st_nlink),
            int(getattr(after, "st_file_attributes", 0)),
        )
        parent_after = os.lstat(parent)
        parent_after_anchor = (
            int(parent_after.st_dev), int(parent_after.st_ino), int(parent_after.st_mtime_ns),
            int(getattr(parent_after, "st_file_attributes", 0)),
        )
        payload = b"".join(chunks)
        if final_anchor != anchor or after_anchor != anchor or parent_after_anchor != parent_anchor or len(payload) != anchor[2]:
            raise ValueError
        return payload
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _resolve_relative(workspace: Path, value: object) -> Path:
    if not _relative_path(value):
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
    path = (workspace / str(value)).absolute()
    if path == workspace or not _inside(path, workspace):
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
    return path


def _exclusive_write(path: Path, payload: bytes) -> None:
    try:
        if type(payload) is not bytes or os.path.lexists(path):
            raise ValueError
        parent_info = os.lstat(path.parent)
        if not stat.S_ISDIR(parent_info.st_mode) or path.parent.is_symlink() or _reparse(parent_info):
            raise ValueError
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if _stable_authority_read(path) != payload:
            raise ValueError
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _load_verified_module(path: Path, payload: bytes, name: str):
    try:
        module = types.ModuleType(name)
        module.__file__ = str(path)
        module.__package__ = ""
        previous = sys.modules.get(name)
        sys.modules[name] = module
        try:
            exec(compile(payload, str(path), "exec"), module.__dict__)
        except Exception:
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
            raise
        return module
    except Exception as exc:
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _runtime_review_base_payload(runtime_payload: bytes, reviewed_sha256: str) -> bytes:
    try:
        sentinel_prefix = b"REVIEWED_SOURCE_RUN_PACKET_SHA256" + b": str | None = "
        armed = sentinel_prefix + b'"' + reviewed_sha256.encode("ascii") + b'"'
        disarmed = sentinel_prefix + b"None"
        if runtime_payload.count(armed) != 1 or runtime_payload.count(disarmed) != 0:
            raise ValueError
        return runtime_payload.replace(armed, disarmed)
    except Exception as exc:
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _safe_ensure_parent_chain(
    workspace: Path,
    target_parent: Path,
    anchors: tuple[tuple[Path, tuple[int, int, int]], ...],
) -> None:
    try:
        verify_existing_ancestor_chain(anchors)
        current = workspace
        for component in target_parent.relative_to(workspace).parts:
            current = current / component
            if not os.path.lexists(current):
                os.mkdir(current)
            info = os.lstat(current)
            if (
                not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _reparse(info)
                or int(info.st_dev) != int(os.lstat(workspace).st_dev)
            ):
                raise ValueError
        verify_existing_ancestor_chain(anchors)
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _lstat_inventory_sha(root: Path) -> str:
    try:
        if not os.path.lexists(root):
            rows = []
        else:
            rows = []
            pending = [root]
            while pending:
                current = pending.pop()
                info = os.lstat(current)
                if current.is_symlink() or _reparse(info):
                    raise ValueError
                relative = "." if current == root else current.relative_to(root).as_posix()
                rows.append({
                    "file_attributes": int(getattr(info, "st_file_attributes", 0)),
                    "inode": int(info.st_ino), "kind": "dir" if stat.S_ISDIR(info.st_mode) else "file",
                    "relative_path": relative, "size": int(info.st_size),
                })
                if stat.S_ISDIR(info.st_mode):
                    pending.extend(sorted((Path(entry.path) for entry in os.scandir(current)), reverse=True))
                elif not stat.S_ISREG(info.st_mode):
                    raise ValueError
        return sha256_bytes(canonical_json({
            "entries": sorted(rows, key=lambda row: row["relative_path"]),
            "schema_version": "trendstack_007_partial_stage_inventory.v1",
        }))
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def preflight_synthetic_paths(
    workspace_root: Path | str,
    stage_relative: str,
    final_relative: str,
    evidence_relative: str,
) -> tuple[Path, Path, Path]:
    """Resolve three absent workspace-relative roots without creating them."""

    try:
        workspace = Path(workspace_root).absolute()
        info = os.lstat(workspace)
        if not stat.S_ISDIR(info.st_mode) or workspace.is_symlink() or _reparse(info):
            raise ValueError
        results = []
        for value in (stage_relative, final_relative, evidence_relative):
            if not _relative_path(value):
                raise ValueError
            resolved = (workspace / value).absolute()
            if resolved == workspace or not _inside(resolved, workspace) or os.path.lexists(resolved):
                raise ValueError
            results.append(resolved)
        if len(set(results)) != 3 or any(_inside(left, right) or _inside(right, left) for index, left in enumerate(results) for right in results[index + 1:]):
            raise ValueError
        return tuple(results)
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def publish_no_replace(stage_root: Path | str, final_root: Path | str) -> None:
    """Rename an unpublished directory only when the destination is absent."""

    try:
        stage = Path(stage_root).absolute()
        final = Path(final_root).absolute()
        if stage == final or os.path.lexists(final):
            raise ValueError
        info = os.lstat(stage)
        parent_info = os.lstat(final.parent)
        if (
            not stat.S_ISDIR(info.st_mode) or stage.is_symlink() or _reparse(info)
            or not stat.S_ISDIR(parent_info.st_mode) or final.parent.is_symlink() or _reparse(parent_info)
            or int(info.st_dev) != int(parent_info.st_dev)
        ):
            raise ValueError
        os.rename(stage, final)
        if os.path.lexists(stage) or not final.is_dir():
            raise ValueError
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def self_disarm_runtime(runtime_path: Path | str, reviewed_sha256: str) -> dict[str, object]:
    """Atomically replace exactly one armed sentinel with ``None``."""

    try:
        if not _valid_sha(reviewed_sha256):
            raise ValueError
        runtime = Path(runtime_path).absolute()
        info = os.lstat(runtime)
        if not stat.S_ISREG(info.st_mode) or runtime.is_symlink() or _reparse(info) or info.st_nlink != 1:
            raise ValueError
        payload = _stable_authority_read(runtime)
        sentinel_prefix = b"REVIEWED_SOURCE_RUN_PACKET_SHA256" + b": str | None = "
        armed = sentinel_prefix + b'"' + reviewed_sha256.encode("ascii") + b'"'
        disarmed = sentinel_prefix + b"None"
        if payload.count(armed) != 1 or payload.count(disarmed) != 0:
            raise ValueError
        replacement = payload.replace(armed, disarmed)
        temporary = runtime.with_name(runtime.name + ".disarm.tmp")
        if os.path.lexists(temporary):
            raise ValueError
        with temporary.open("xb") as handle:
            handle.write(replacement)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, runtime)
        readback = _stable_authority_read(runtime)
        if readback != replacement or readback.count(disarmed) != 1 or armed in readback:
            raise ValueError
        return {
            "supervisor_disarm_status": "DISARMED_NONE_VERIFIED",
            "supervisor_disarmed_sha256": sha256_bytes(readback),
        }
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


def _metadata_map(value: object) -> dict[str, str]:
    if (
        type(value) is not dict or set(value) != set(METADATA_FILES)
        or any(not _valid_sha(value[name]) for name in METADATA_FILES)
    ):
        raise ValueError
    return dict(value)


def exact_projection_tree_identity_digest(
    root_value: Path | str,
    manifest_payload: bytes,
    expected_shards: int,
) -> str:
    """Enforce the V7 tree exactly and bind listed shards without opening them."""

    try:
        if type(expected_shards) is not int or expected_shards <= 0:
            raise ValueError
        root = Path(root_value).absolute()
        root_info = os.lstat(root)
        if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode) or _reparse(root_info):
            raise ValueError
        device = int(root_info.st_dev)
        root_entries = {entry.name for entry in os.scandir(root)}
        if root_entries != set(METADATA_FILES) | {"DESIGN"}:
            raise ValueError

        regular_files = 0
        for name in METADATA_FILES:
            info = os.lstat(root / name)
            if (
                not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or _reparse(info)
                or int(info.st_nlink) != 1 or int(info.st_dev) != device
            ):
                raise ValueError
            regular_files += 1

        records = manifest_payload.splitlines(keepends=True)
        if len(records) != expected_shards or not records:
            raise ValueError
        rows = []
        previous = None
        manifest_fields = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
        for record in records:
            row = _json_object(record)
            day = row.get("date")
            if (
                type(day) is not str
                or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day
                or set(row) != manifest_fields
                or row["relative_path"] != f"DESIGN/{day}/h1_1200.parquet"
                or row["rows"] != 1
                or row["schema_version"] != "trendstack_007_projection_manifest_row.v1"
                or type(row["bytes"]) is not int or row["bytes"] <= 0
                or not _valid_sha(row["sha256"])
                or (previous is not None and day <= previous)
            ):
                raise ValueError
            rows.append(row)
            previous = day

        design = root / "DESIGN"
        design_info = os.lstat(design)
        if (
            not stat.S_ISDIR(design_info.st_mode) or stat.S_ISLNK(design_info.st_mode)
            or _reparse(design_info) or int(design_info.st_dev) != device
        ):
            raise ValueError
        dates = [str(row["date"]) for row in rows]
        if {entry.name for entry in os.scandir(design)} != set(dates):
            raise ValueError

        directory_count = 1
        identities = []
        for row in rows:
            relative = str(row["relative_path"])
            day_root = design / str(row["date"])
            day_info = os.lstat(day_root)
            if (
                not stat.S_ISDIR(day_info.st_mode) or stat.S_ISLNK(day_info.st_mode)
                or _reparse(day_info) or int(day_info.st_dev) != device
                or {entry.name for entry in os.scandir(day_root)} != {"h1_1200.parquet"}
            ):
                raise ValueError
            output = root / Path(relative)
            info = os.lstat(output)
            if (
                not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or _reparse(info)
                or int(info.st_nlink) != 1 or int(info.st_dev) != device
                or int(info.st_size) != row["bytes"]
            ):
                raise ValueError
            identities.append({
                "bytes": row["bytes"],
                "platform_file_identity": [
                    int(info.st_dev), int(info.st_ino), int(info.st_size), int(info.st_mtime_ns),
                    int(info.st_nlink), int(getattr(info, "st_file_attributes", 0)),
                ],
                "relative_path": relative,
            })
            directory_count += 1
            regular_files += 1
        if regular_files != expected_shards + len(METADATA_FILES) or directory_count != expected_shards + 1:
            raise ValueError
        return sha256_bytes(canonical_json({
            "files": identities,
            "schema_version": "trendstack_007_validated_file_identities.v1",
        }))
    except Exception as exc:
        if isinstance(exc, InvalidSourceProjection):
            raise
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc


class ProductionOperations:
    """Concrete reviewed filesystem composition for the one-shot source run."""

    def __init__(
        self,
        packet: VerifiedSourceRunPacket,
        *,
        _testing_workspace: Path | str | None = None,
    ) -> None:
        if type(packet) is not VerifiedSourceRunPacket:
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        self.packet = packet
        self.testing = _testing_workspace is not None
        self.workspace = (
            Path(_testing_workspace).absolute()
            if self.testing
            else Path(__file__).absolute().parents[3]
        )
        self._context = None

    @classmethod
    def for_testing(
        cls, packet: VerifiedSourceRunPacket, workspace_root: Path | str
    ) -> "ProductionOperations":
        return cls(packet, _testing_workspace=workspace_root)

    def _bound_payloads(self, values: dict[str, object]) -> tuple[dict[str, Path], dict[Path, bytes]]:
        path_fields = (
            "registry_path", "active_plan_path", "contract_v4_path", "contract_v5_path",
            "contract_v6_path", "contract_v7_path", "active_contract_bundle_path",
            "implementation_task_v1_path", "implementation_task_v2_path",
            "implementation_task_v3_path", "implementation_task_v4_path",
            "authority_amendment_v2_path", "authority_amendment_v3_path",
            "implementation_task_v5_path", "authority_repair_amendment_v4_path",
            "implementation_task_v6_path",
            "projector_tool_path", "projector_test_path",
            "validator_tool_path", "validator_test_path", "supervisor_tool_path",
            "supervisor_test_path", "supervisor_runtime_path", "clock_path",
            "public_receipt_path", "public_manifest_path", "selection_manifest_path",
            "implementation_review_receipt_path", "active_contract_path", "task_packet_path",
        )
        paths = {field: _resolve_relative(self.workspace, values[field]) for field in path_fields}
        paths.update({
            f"receipt_{name}_path": _resolve_relative(self.workspace, relative)
            for name, relative in RECEIPT_V6_BINDING_PATHS.items()
        })
        if (
            paths["active_contract_path"] != paths["active_contract_bundle_path"]
            or values["active_contract_sha256"] != values["active_contract_bundle_sha256"]
            or paths["task_packet_path"] != paths["implementation_task_v4_path"]
            or values["task_packet_sha256"] != values["implementation_task_v4_sha256"]
            or paths["supervisor_tool_path"] != paths["supervisor_runtime_path"]
            or values["supervisor_tool_sha256"] != values["supervisor_review_base_sha256"]
        ):
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        cache = {}
        for path in set(paths.values()):
            anchors = bind_existing_ancestor_chain(self.workspace, path.parent)
            verify_existing_ancestor_chain(anchors)
            cache[path] = _stable_authority_read(path)
            verify_existing_ancestor_chain(anchors)
        ordinary_pairs = (
            ("registry_path", "registry_sha256"), ("active_plan_path", "active_plan_sha256"),
            ("contract_v4_path", "contract_v4_sha256"), ("contract_v5_path", "contract_v5_sha256"),
            ("contract_v6_path", "contract_v6_sha256"), ("contract_v7_path", "contract_v7_sha256"),
            ("active_contract_bundle_path", "active_contract_bundle_sha256"),
            ("implementation_task_v1_path", "implementation_task_v1_sha256"),
            ("implementation_task_v2_path", "implementation_task_v2_sha256"),
            ("implementation_task_v3_path", "implementation_task_v3_sha256"),
            ("implementation_task_v4_path", "implementation_task_v4_sha256"),
            ("authority_amendment_v2_path", "authority_amendment_v2_sha256"),
            ("authority_amendment_v3_path", "authority_amendment_v3_sha256"),
            ("implementation_task_v5_path", "implementation_task_v5_sha256"),
            ("authority_repair_amendment_v4_path", "authority_repair_amendment_v4_sha256"),
            ("implementation_task_v6_path", "implementation_task_v6_sha256"),
            ("projector_tool_path", "projector_tool_sha256"),
            ("projector_test_path", "projector_test_sha256"),
            ("validator_tool_path", "validator_tool_sha256"),
            ("validator_test_path", "validator_test_sha256"),
            ("supervisor_test_path", "supervisor_test_sha256"),
            ("clock_path", "clock_sha256"), ("public_receipt_path", "public_receipt_sha256"),
            ("public_manifest_path", "public_manifest_sha256"),
            ("selection_manifest_path", "selection_manifest_sha256"),
            ("implementation_review_receipt_path", "implementation_review_receipt_sha256"),
        )
        for path_field, hash_field in ordinary_pairs:
            if sha256_bytes(cache[paths[path_field]]) != values[hash_field]:
                raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        runtime = cache[paths["supervisor_runtime_path"]]
        if (
            sha256_bytes(runtime) != values["supervisor_runtime_sha256"]
            or sha256_bytes(_runtime_review_base_payload(runtime, self.packet.detached_sha256))
            != values["supervisor_review_base_sha256"]
        ):
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        bundle = _json_object(cache[paths["active_contract_bundle_path"]])
        expected_bundle = {
            "contracts": [
                {"path": values["contract_v4_path"], "role": "base_v4", "sha256": values["contract_v4_sha256"]},
                {"path": values["contract_v5_path"], "role": "output_schema_v5", "sha256": values["contract_v5_sha256"]},
                {"path": values["contract_v6_path"], "role": "metadata_map_v6", "sha256": values["contract_v6_sha256"]},
                {"path": values["contract_v7_path"], "role": "terminal_tree_v7", "sha256": values["contract_v7_sha256"]},
            ],
            "hypothesis_id": values["hypothesis_id"],
            "schema_version": "trendstack_007_active_source_contract_bundle.v2",
        }
        task_v1 = _strict_json_document(cache[paths["implementation_task_v1_path"]])
        task_v2 = _strict_json_document(cache[paths["implementation_task_v2_path"]])
        task_v3 = _strict_json_document(cache[paths["implementation_task_v3_path"]])
        task_v4 = _strict_json_document(cache[paths["implementation_task_v4_path"]])
        task_v5 = _strict_json_document(cache[paths["implementation_task_v5_path"]])
        task_v6 = _strict_json_document(cache[paths["implementation_task_v6_path"]])
        amendment_v2 = _strict_json_document(cache[paths["authority_amendment_v2_path"]])
        amendment_v3 = _strict_json_document(cache[paths["authority_amendment_v3_path"]])
        amendment_v4 = _strict_json_document(cache[paths["authority_repair_amendment_v4_path"]])
        review = _strict_json_document(cache[paths["implementation_review_receipt_path"]])
        review_authority = review.get("reviewed_authority")
        review_snapshot = review.get("reviewed_snapshot")
        forbidden_receipt_keys = {
            "full_registry_sha256", "registry_row_index", "registry_row_sha256",
            "registry_sha256", "row287_sha256",
        }

        def contains_forbidden_key(value):
            if type(value) is dict:
                return bool(set(value) & forbidden_receipt_keys) or any(
                    contains_forbidden_key(item) for item in value.values()
                )
            if type(value) is list:
                return any(contains_forbidden_key(item) for item in value)
            return False

        if (
            bundle != expected_bundle
            or task_v1.get("hypothesis_id") != values["hypothesis_id"]
            or task_v1.get("schema_version") != "trendstack_007_source_implementation_task_packet.v1"
            or task_v2.get("hypothesis_id") != values["hypothesis_id"]
            or task_v2.get("schema_version") != "trendstack_007_source_implementation_task_packet.v2"
            or task_v3.get("hypothesis_id") != values["hypothesis_id"]
            or task_v3.get("schema_version") != "trendstack_007_source_implementation_task_packet.v3"
            or task_v4.get("hypothesis_id") != values["hypothesis_id"]
            or task_v4.get("schema_version") != "trendstack_007_source_implementation_task_packet.v4"
            or task_v5.get("hypothesis_id") != values["hypothesis_id"]
            or task_v5.get("schema_version") != "trendstack_007_source_implementation_task_packet.v5"
            or task_v6.get("hypothesis_id") != values["hypothesis_id"]
            or task_v6.get("schema_version") != "trendstack_007_source_implementation_task_packet.v6"
            or amendment_v2.get("hypothesis_id") != values["hypothesis_id"]
            or amendment_v2.get("schema_version") != "trendstack_007_source_run_authority_amendment.v2"
            or amendment_v3.get("hypothesis_id") != values["hypothesis_id"]
            or amendment_v3.get("schema_version") != "trendstack_007_source_run_authority_amendment_addendum.v3"
            or amendment_v4.get("hypothesis_id") != values["hypothesis_id"]
            or amendment_v4.get("schema_version")
            != "trendstack_007_source_run_authority_repair_amendment.v4"
            or review.get("hypothesis_id") != values["hypothesis_id"]
            or review.get("schema_version") != "trendstack_007_source_implementation_review_receipt.v6"
            or review.get("verdict") != "PASS_FOR_PRODUCTION_SOURCE_RUN_PACKET_PREPARATION"
            or type(review_authority) is not dict
            or review_authority.get("authority_repair_amendment_v4_sha256")
            != values["authority_repair_amendment_v4_sha256"]
            or review_authority.get("implementation_task_v6_sha256")
            != values["implementation_task_v6_sha256"]
            or type(review_snapshot) is not dict
            or review_snapshot.get("registry_schema_sha256")
            != sha256_bytes(cache[paths["receipt_registry_schema_path"]])
            or review_snapshot.get("registry_validator_sha256")
            != sha256_bytes(cache[paths["receipt_registry_validator_path"]])
            or review_snapshot.get("registry_integration_test_sha256")
            != sha256_bytes(cache[paths["receipt_registry_integration_test_path"]])
            or review_snapshot.get("supervisor_review_base_sha256")
            != values["supervisor_review_base_sha256"]
            or review_snapshot.get("supervisor_test_sha256")
            != values["supervisor_test_sha256"]
            or contains_forbidden_key(review)
        ):
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        return paths, cache

    def preflight(self, packet: VerifiedSourceRunPacket) -> dict[str, object]:
        values = packet.values
        if packet is not self.packet or values["workspace_root_path"] != ".":
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        workspace_info = os.lstat(self.workspace)
        if (
            not stat.S_ISDIR(workspace_info.st_mode) or self.workspace.is_symlink() or _reparse(workspace_info)
            or list(_directory_identity(workspace_info)) != values["workspace_root_identity"]
            or (not self.testing and values["expected_dates"] != 1297)
            or type(values["expected_dates"]) is not int or values["expected_dates"] <= 0
            or type(values["expected_unselected_dates"]) is not int or values["expected_unselected_dates"] < 0
        ):
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        paths, payloads = self._bound_payloads(values)
        validate_registry_source_run_authority(payloads[paths["registry_path"]], values)
        stage, final, evidence = preflight_synthetic_paths(
            self.workspace, values["stage_root"], values["final_output_root"], values["evidence_root"]
        )
        root_anchors = {
            "stage": bind_existing_ancestor_chain(self.workspace, stage),
            "final": bind_existing_ancestor_chain(self.workspace, final),
            "evidence": bind_existing_ancestor_chain(self.workspace, evidence),
        }
        if not self.testing and paths["supervisor_runtime_path"] != Path(__file__).absolute():
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        projector = _load_verified_module(
            paths["projector_tool_path"], payloads[paths["projector_tool_path"]],
            "_trendstack_007_projector_runtime",
        )
        validator = _load_verified_module(
            paths["validator_tool_path"], payloads[paths["validator_tool_path"]],
            "_trendstack_007_validator_runtime",
        )
        context = {
            "evidence": evidence, "final": final, "paths": paths, "payloads": payloads,
            "phase": "PREFLIGHT", "projector": projector, "root_anchors": root_anchors,
            "stage": stage, "validator": validator, "workspace": self.workspace,
        }
        self._context = context
        return context

    def start(self, packet: VerifiedSourceRunPacket, context: dict[str, object]):
        context["phase"] = "START"
        _safe_create_root(
            context["workspace"], context["evidence"], context["root_anchors"]["evidence"]
        )
        context["evidence_anchors"] = bind_existing_ancestor_chain(
            context["workspace"], context["evidence"]
        )
        values = packet.values
        started = {
            "active_contract_sha256": values["active_contract_bundle_sha256"],
            "active_plan_sha256": values["active_plan_sha256"], "attempt_state": "ATTEMPT_CONSUMED",
            "economics_authorized": False, "final_output_root": values["final_output_root"],
            "holdout_authorized": False, "hypothesis_id": values["hypothesis_id"],
            "model0_authorized": False, "network_allowed": False,
            "projection_attempt_id": values["projection_attempt_id"],
            "projector_test_sha256": values["projector_test_sha256"],
            "projector_tool_sha256": values["projector_tool_sha256"],
            "registry_mutation_allowed": False, "registry_row_index": values["registry_row_index"],
            "registry_row_sha256": values["registry_row_sha256"],
            "schema_version": "trendstack_007_projection_attempt_started.v1",
            "source_run_authorized": True, "stage_root": values["stage_root"],
            "started_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "subprocess_allowed": False,
            "superseded_contract_sha256s": values["superseded_contract_sha256s"],
            "superseded_plan_sha256s": values["superseded_plan_sha256s"],
            "supervisor_review_base_sha256": values["supervisor_review_base_sha256"],
            "supervisor_runtime_sha256": values["supervisor_runtime_sha256"],
            "supervisor_test_sha256": values["supervisor_test_sha256"],
            "task_packet_sha256": values["implementation_task_v4_sha256"],
            "trading_mutation": False, "validation_authorized": False,
            "validator_test_sha256": values["validator_test_sha256"],
            "validator_tool_sha256": values["validator_tool_sha256"],
            "workspace_root_identity": values["workspace_root_identity"],
        }
        payload = canonical_json(started) + b"\n"
        marker_path = context["evidence"] / "attempt_started.json"
        _exclusive_write(marker_path, payload)
        verify_existing_ancestor_chain(context["evidence_anchors"])
        context["marker_path"] = marker_path
        context["marker"] = started
        return started, sha256_bytes(payload)

    def reconcile_marker(self, packet: VerifiedSourceRunPacket, context: dict[str, object] | None):
        evidence = self._context["evidence"] if self._context is not None else _resolve_relative(self.workspace, packet.values["evidence_root"])
        marker_path = evidence / "attempt_started.json"
        if not os.path.lexists(marker_path):
            return None
        payload = _stable_authority_read(marker_path)
        marker = _json_object(payload)
        if marker.get("attempt_state") != "ATTEMPT_CONSUMED":
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        return marker, sha256_bytes(payload)

    def project(self, packet, marker, context):
        context["phase"] = "PROJECT"
        _safe_ensure_parent_chain(
            context["workspace"], context["stage"].parent, context["root_anchors"]["stage"]
        )
        context["stage_parent_anchors"] = bind_existing_ancestor_chain(
            context["workspace"], context["stage"].parent
        )
        verify_existing_ancestor_chain(context["stage_parent_anchors"])
        values = packet.values
        projector = context["projector"]
        decode_input, encode_output, decode_output = projector.pyarrow_projection_codecs()
        server_offset, server_to_utc = projector.verified_clock_functions(
            context["paths"]["clock_path"], context["workspace"], values["clock_sha256"]
        )
        public_root = context["paths"]["public_manifest_path"].parent
        shard_reader = projector.bounded_public_shard_reader(
            context["workspace"], public_root / "DESIGN"
        )
        authority = projector.ProjectionAuthority(
            projection_attempt_id=values["projection_attempt_id"],
            active_contract_sha256=values["active_contract_bundle_sha256"],
            task_packet_sha256=values["implementation_task_v4_sha256"],
            public_receipt_sha256=values["public_receipt_sha256"],
            public_manifest_sha256=values["public_manifest_sha256"],
            selection_manifest_sha256=values["selection_manifest_sha256"],
        )
        shape = projector.ProjectionShape(
            values["expected_dates"], values["expected_unselected_dates"],
            values["expected_date_set_sha256"], values["first_date"], values["last_date"],
        )
        result = projector.project_stage_from_paths(
            workspace_root=context["workspace"],
            public_receipt_path=context["paths"]["public_receipt_path"],
            public_manifest_path=context["paths"]["public_manifest_path"],
            selection_manifest_path=context["paths"]["selection_manifest_path"],
            stage_root=context["stage"], authority=authority, shape=shape,
            shard_reader=shard_reader, decode_input=decode_input, encode_output=encode_output,
            decode_output=decode_output, server_offset_hours=server_offset,
            server_to_utc=server_to_utc,
        )
        verify_existing_ancestor_chain(context["stage_parent_anchors"])
        context["project_result"] = result
        return result

    def validate(self, packet, project_result, context):
        context["phase"] = "VALIDATE"
        values = packet.values
        validator = context["validator"]
        authority = validator.ValidationAuthority(
            projection_attempt_id=values["projection_attempt_id"],
            active_contract_sha256=values["active_contract_bundle_sha256"],
            task_packet_sha256=values["implementation_task_v4_sha256"],
            validator_tool_sha256=values["validator_tool_sha256"],
            public_receipt_sha256=values["public_receipt_sha256"],
            public_manifest_sha256=values["public_manifest_sha256"],
            selection_manifest_sha256=values["selection_manifest_sha256"],
        )
        shape = types.SimpleNamespace(
            expected_dates=values["expected_dates"],
            expected_unselected_dates=values["expected_unselected_dates"],
            expected_date_set_sha256=values["expected_date_set_sha256"],
            first_date=values["first_date"], last_date=values["last_date"],
        )
        result = validator.validate_stage_from_paths(
            workspace_root=context["workspace"],
            public_receipt_path=context["paths"]["public_receipt_path"],
            public_manifest_path=context["paths"]["public_manifest_path"],
            selection_manifest_path=context["paths"]["selection_manifest_path"],
            active_contract_bundle_path=context["paths"]["active_contract_bundle_path"],
            active_contract_bundle_sha256=values["active_contract_bundle_sha256"],
            implementation_task_packet_path=context["paths"]["implementation_task_v4_path"],
            implementation_task_packet_sha256=values["implementation_task_v4_sha256"],
            stage_root=context["stage"], evidence_root=context["evidence"],
            authority=authority, shape=shape, decode_output=validator.pyarrow_output_decoder(),
        )
        receipt_payload = _stable_authority_read(context["evidence"] / "validation_receipt.json")
        result["validation_receipt_sha256"] = sha256_bytes(receipt_payload)
        context["validation_result"] = result
        return result

    def pre_publish_metadata_hashes(self, packet, context):
        context["phase"] = "PRE_PUBLISH"
        anchors = bind_existing_ancestor_chain(context["workspace"], context["stage"])
        payloads = {
            name: _stable_authority_read(context["stage"] / name) for name in METADATA_FILES
        }
        verify_existing_ancestor_chain(anchors)
        hashes = {name: sha256_bytes(payloads[name]) for name in METADATA_FILES}
        validation = context["validation_result"]
        if hashes != validation["stage_metadata_hashes"]:
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        identity_sha = exact_projection_tree_identity_digest(
            context["stage"], payloads["design_1200_manifest.jsonl"],
            packet.values["expected_dates"],
        )
        if identity_sha != validation["validated_file_identities_sha256"]:
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        context["pre_publish_metadata_hashes"] = hashes
        context["pre_publish_identity_sha256"] = identity_sha
        return hashes

    def publish(self, packet, context):
        context["phase"] = "PUBLISH"
        _safe_ensure_parent_chain(
            context["workspace"], context["final"].parent, context["root_anchors"]["final"]
        )
        final_parent_anchors = bind_existing_ancestor_chain(
            context["workspace"], context["final"].parent
        )
        verify_existing_ancestor_chain(final_parent_anchors)
        verify_existing_ancestor_chain(context["root_anchors"]["final"])
        publish_no_replace(context["stage"], context["final"])
        verify_existing_ancestor_chain(final_parent_anchors)

    def post_publish(self, packet, context):
        context["phase"] = "POST_PUBLISH"
        anchors = bind_existing_ancestor_chain(context["workspace"], context["final"])
        payloads = {
            name: _stable_authority_read(context["final"] / name) for name in METADATA_FILES
        }
        verify_existing_ancestor_chain(anchors)
        hashes = {name: sha256_bytes(payloads[name]) for name in METADATA_FILES}
        if hashes != context["validation_result"]["stage_metadata_hashes"]:
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        identity_sha = exact_projection_tree_identity_digest(
            context["final"], payloads["design_1200_manifest.jsonl"],
            packet.values["expected_dates"],
        )
        if identity_sha != context["validation_result"]["validated_file_identities_sha256"]:
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        info = os.lstat(context["final"])
        return {
            "metadata_hashes": hashes,
            "output_shard_lstats": packet.values["expected_dates"],
            "final_output_root_identity": list(_directory_identity(info)),
        }

    def disarm(self, packet, context):
        runtime = Path(__file__).absolute() if not self.testing else (
            context["paths"]["supervisor_runtime_path"]
            if context is not None else _resolve_relative(self.workspace, packet.values["supervisor_runtime_path"])
        )
        result = self_disarm_runtime(runtime, packet.detached_sha256)
        if result["supervisor_disarmed_sha256"] != packet.values["supervisor_review_base_sha256"]:
            raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION")
        return result

    def terminal(self, packet, marker_sha256, verdict, evidence, context):
        values = packet.values
        terminal_path = context["evidence"] / "attempt_terminal.json"
        completed = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        if verdict == "ENGINEERING_VALID_SOURCE_PROJECTION":
            document = {
                "attempt_started_sha256": marker_sha256, "completed_at_utc": completed,
                "data_tree_sha256": evidence["data_tree_sha256"], "economics_opened": False,
                "final_output_root": values["final_output_root"],
                "final_output_root_identity": evidence["final_output_root_identity"],
                "hypothesis_id": values["hypothesis_id"], "manifest_sha256": evidence["manifest_sha256"],
                "market_verdict": None, "post_publish_metadata_hashes": evidence["metadata_hashes"],
                "post_publish_output_shard_lstats": evidence["output_shards"],
                "projection_attempt_id": values["projection_attempt_id"],
                "projector_receipt_sha256": evidence["projector_receipt_sha256"],
                "reconciliation_sha256": evidence["reconciliation_sha256"],
                "research_holdout_opened": False, "research_validation_opened": False,
                "schema_version": "trendstack_007_projection_attempt_terminal_pass.v2",
                "source_projection_attempts_consumed": 1,
                "supervisor_disarm_status": evidence["supervisor_disarm_status"],
                "supervisor_disarmed_sha256": evidence["supervisor_disarmed_sha256"],
                "trace_sha256": evidence["trace_sha256"],
                "validated_file_identities_sha256": evidence["validated_file_identities_sha256"],
                "validation_receipt_sha256": evidence["validation_receipt_sha256"],
                "verdict": verdict,
            }
        else:
            error_class = str(evidence.get("error_class", "InvalidSourceProjection"))
            document = {
                "attempt_started_sha256": marker_sha256, "completed_at_utc": completed,
                "economics_opened": False, "error_class": error_class,
                "error_message_sha256": sha256_bytes((error_class + ":sanitized").encode("utf-8")),
                "failure_phase": context.get("phase", "UNKNOWN"),
                "final_output_absent": not os.path.lexists(context["final"]),
                "hypothesis_id": values["hypothesis_id"], "market_verdict": None,
                "partial_stage_inventory_sha256": _lstat_inventory_sha(context["stage"]),
                "projection_attempt_id": values["projection_attempt_id"],
                "research_holdout_opened": False, "research_validation_opened": False,
                "schema_version": "trendstack_007_projection_attempt_terminal_fail.v1",
                "source_projection_attempts_consumed": 1,
                "supervisor_disarm_status": evidence.get("supervisor_disarm_status", "DISARM_FAILED"),
                "supervisor_disarmed_sha256": evidence.get("supervisor_disarmed_sha256", "0" * 64),
                "verdict": verdict,
            }
        payload = canonical_json(document) + b"\n"
        _exclusive_write(terminal_path, payload)
        return sha256_bytes(payload)


def _run_one_shot_lifecycle(packet: VerifiedSourceRunPacket, operations: object) -> dict[str, object]:
    """Exercise the exact marker/project/validate/publish/disarm lifecycle."""

    global REVIEWED_SOURCE_RUN_PACKET_SHA256
    marked = False
    accepted = False
    disarm = None
    marker_sha256 = None
    context = None
    try:
        if (
            type(packet) is not VerifiedSourceRunPacket
            or REVIEWED_SOURCE_RUN_PACKET_SHA256 != packet.detached_sha256
            or not _valid_sha(packet.detached_sha256)
            or compute_source_run_packet_sha256(packet.values) != packet.detached_sha256
        ):
            raise ValueError
        accepted = True
        context = operations.preflight(packet)
        marker, marker_sha256 = operations.start(packet, context)
        if type(marker) is not dict or marker.get("attempt_state") != "ATTEMPT_CONSUMED" or not _valid_sha(marker_sha256):
            raise ValueError
        marked = True
        project_result = operations.project(packet, marker, context)
        if type(project_result) is not dict or type(project_result.get("output_shards")) is not int or project_result["output_shards"] <= 0:
            raise ValueError
        project_map = _metadata_map(project_result.get("stage_metadata_hashes"))
        validation_result = operations.validate(packet, project_result, context)
        if (
            type(validation_result) is not dict
            or validation_result.get("output_shards") != project_result["output_shards"]
            or not _valid_sha(validation_result.get("validation_receipt_sha256"))
        ):
            raise ValueError
        validation_map = _metadata_map(validation_result.get("stage_metadata_hashes"))
        pre_map = _metadata_map(operations.pre_publish_metadata_hashes(packet, context))
        if not (project_map == validation_map == pre_map):
            raise ValueError
        operations.publish(packet, context)
        post = operations.post_publish(packet, context)
        if (
            type(post) is not dict
            or _metadata_map(post.get("metadata_hashes")) != pre_map
            or post.get("output_shard_lstats") != project_result["output_shards"]
            or type(post.get("final_output_root_identity")) is not list
            or not post["final_output_root_identity"]
        ):
            raise ValueError
        disarm = operations.disarm(packet, context)
        if type(disarm) is not dict or disarm.get("supervisor_disarm_status") != "DISARMED_NONE_VERIFIED" or not _valid_sha(disarm.get("supervisor_disarmed_sha256")):
            raise ValueError
        evidence = {
            "final_output_root_identity": post["final_output_root_identity"],
            "metadata_hashes": pre_map,
            "output_shards": project_result["output_shards"],
            "supervisor_disarm_status": disarm["supervisor_disarm_status"],
            "supervisor_disarmed_sha256": disarm["supervisor_disarmed_sha256"],
            "validation_receipt_sha256": validation_result["validation_receipt_sha256"],
        }
        for key in (
            "data_tree_sha256", "manifest_sha256", "trace_sha256", "reconciliation_sha256",
            "projector_receipt_sha256", "validated_file_identities_sha256",
        ):
            value = validation_result.get(key, project_result.get(key))
            if value is not None:
                if not _valid_sha(value):
                    raise ValueError
                evidence[key] = value
        terminal_sha = operations.terminal(
            packet, marker_sha256, "ENGINEERING_VALID_SOURCE_PROJECTION", evidence, context
        )
        if not _valid_sha(terminal_sha):
            raise ValueError
        return {
            **evidence,
            "terminal_receipt_sha256": terminal_sha,
            "verdict": "ENGINEERING_VALID_SOURCE_PROJECTION",
        }
    except Exception as exc:
        if accepted and not marked and context is not None:
            reconcile = getattr(operations, "reconcile_marker", None)
            if callable(reconcile):
                try:
                    recovered = reconcile(packet, context)
                    if recovered is not None:
                        marker, marker_sha256 = recovered
                        if (
                            type(marker) is not dict
                            or marker.get("attempt_state") != "ATTEMPT_CONSUMED"
                            or not _valid_sha(marker_sha256)
                        ):
                            raise ValueError
                        marked = True
                except Exception:
                    pass
        if accepted and disarm is None:
            try:
                disarm = operations.disarm(packet, context)
            except Exception as disarm_exc:
                disarm = {"disarm_error_class": type(disarm_exc).__name__}
        if marked:
            failure_evidence = {"error_class": type(exc).__name__, "market_verdict": None}
            if type(disarm) is dict:
                failure_evidence.update(disarm)
            try:
                operations.terminal(
                    packet, marker_sha256,
                    "SOURCE_PROJECTION_FAILED_ENGINEERING_NO_MARKET_VERDICT",
                    failure_evidence, context,
                )
            except Exception:
                pass
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc
    finally:
        if accepted and disarm is None:
            try:
                operations.disarm(packet, context)
            except Exception:
                pass
        REVIEWED_SOURCE_RUN_PACKET_SHA256 = None


def run_one_shot_for_testing(
    packet: VerifiedSourceRunPacket, operations: object
) -> dict[str, object]:
    """Test-only injected-operations surface; production never calls this."""

    return _run_one_shot_lifecycle(packet, operations)


def supervise(source_run_packet_path: Path | str) -> dict[str, object]:
    """Run exactly one reviewed packet through concrete production operations."""

    global REVIEWED_SOURCE_RUN_PACKET_SHA256
    if REVIEWED_SOURCE_RUN_PACKET_SHA256 is None:
        raise InvalidSourceProjection("SOURCE_SUPERVISOR_DISARMED")
    reviewed_sha256 = REVIEWED_SOURCE_RUN_PACKET_SHA256
    runtime_path = Path(__file__).absolute()
    try:
        path = Path(source_run_packet_path).absolute()
        workspace = runtime_path.parents[3]
        if path == workspace or not _inside(path, workspace):
            raise ValueError
        packet_anchors = bind_existing_ancestor_chain(workspace, path.parent)
        packet_payload = _stable_authority_read(path)
        verify_existing_ancestor_chain(packet_anchors)
        packet = validate_source_run_packet_document(packet_payload, reviewed_sha256)
        operations = ProductionOperations(packet)
    except Exception as exc:
        try:
            self_disarm_runtime(runtime_path, reviewed_sha256)
        except Exception:
            pass
        finally:
            REVIEWED_SOURCE_RUN_PACKET_SHA256 = None
        raise InvalidSourceProjection("INVALID_SOURCE_PROJECTION") from exc
    return _run_one_shot_lifecycle(packet, operations)
