"""Pure, fail-closed DESIGN economics for HYP007.

The implementation surface is deliberately in-memory.  A separately reviewed
runner may load the frozen inputs and pass decoded records here; importing this
module performs no reads, writes, network calls, or evaluation.  ATR20 is read
only from each manifest-bound decision packet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-007"
IMPLEMENTATION_TASK_SHA256 = "45B9D7FFE1DC57DD655DEF40C7E2612CBF7FB5A78C3FE54DDBC48168A303F87A"
IMPLEMENTATION_TASK_V2_SHA256 = "8013FB8E9D387A375319020BF80F67FD6D1DC6303B54490B04FEB65AB2079B78"
IMPLEMENTATION_TASK_V3_SHA256 = "B02C766DFA5059B6BF80EF5DB0B44167BD9997404B32F1641C25864A6B075F46"
IMPLEMENTATION_TASK_V4_SHA256 = "7419385BA3CA0604C4CABF4C6EF0AA65673CDBD623117B08371D58B4921BCB2F"
IMPLEMENTATION_TASK_V5_SHA256 = "DF7004B4A6398AD58A53B6CAEA3FDFBCFD4A303794EB817ECFCC20CBC648876B"
IMPLEMENTATION_TASK_V6_SHA256 = "04CEC53A9947EE6A17D4254D26113C6F22529D2887AD892098D0FAD6703921A5"
DSR_TOOL_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
EXPECTED_DATES = 1297
EXPECTED_STAGE0_TOTAL_ROWS = 1817
EXPECTED_STAGE0_VALIDATION_FEATURE_ONLY_ROWS = 520
PIP = 0.0001
ELAPSED_WEEKS = 260.571428571
DESIGN_YEARS = (2016, 2017, 2018, 2019, 2020)
ARMS = (
    "CONTROL_M252_ONLY",
    "CONTROL_M6_ONLY",
    "CHALLENGER_STACK",
    "NEGATIVE_DISAGREE",
)
EXPECTED_ARM_COUNTS = {
    "CONTROL_M252_ONLY": 1297,
    "CONTROL_M6_ONLY": 1292,
    "CHALLENGER_STACK": 661,
    "NEGATIVE_DISAGREE": 631,
}
EXPECTED_TOTAL_TRADES = sum(EXPECTED_ARM_COUNTS.values())
COST_TIERS = (("1_50", 1.5), ("2_25", 2.25), ("3_00", 3.0))
ARM_FIELDS = {
    "CONTROL_M252_ONLY": ("control_m252_only_eligible", "control_m252_only_direction"),
    "CONTROL_M6_ONLY": ("control_m6_only_eligible", "control_m6_only_direction"),
    "CHALLENGER_STACK": ("challenger_stack_eligible", "challenger_stack_direction"),
    "NEGATIVE_DISAGREE": ("negative_disagree_eligible", "negative_disagree_direction"),
}
REQUIRED_ARTIFACTS = (
    "design_economics_trade_ledger.jsonl",
    "design_arm_cost_metrics.json",
    "design_yearly_metrics.json",
    "design_dsr_inputs.json",
    "design_gate_report.json",
    "design_economics_receipt.json",
    "attempt_terminal.json",
)
EXPECTED_ARTIFACT_AUTHORITY_SHA256 = {
    "active_probe_plan_sha256": "FE740C0811E7060670D1F771802EAC5ADD6D5B2CD9DB0FDABD7E48A8A2D29735",
    "implementation_task_v1_sha256": IMPLEMENTATION_TASK_SHA256,
    "implementation_task_v2_sha256": IMPLEMENTATION_TASK_V2_SHA256,
    "implementation_task_v3_sha256": IMPLEMENTATION_TASK_V3_SHA256,
    "implementation_task_v4_sha256": IMPLEMENTATION_TASK_V4_SHA256,
    "implementation_task_v5_sha256": IMPLEMENTATION_TASK_V5_SHA256,
    "implementation_task_v6_sha256": IMPLEMENTATION_TASK_V6_SHA256,
    "attempt_001_terminal_sha256": "3C42C0C445AF2F8386752598490A8241BB43A5D8AA96F4DD5EB55D41DE0F5DB5",
    "attempt_001_design_economics_receipt_sha256": "E29C237E52143803E16987653D4B52E02FC9983BEA88A655C8C22E13244D477B",
    "attempt_002_terminal_sha256": "960A46269955F0BBA7F8F20CD470BC2897BF8760E6436CD263C904B6B56EA675",
    "attempt_002_design_economics_receipt_sha256": "1B96FED9C6112B6F0BAC2B502CCA1876A7507E1FF23AEE2EB3BF5B8358E9B858",
    "attempt_003_terminal_sha256": "685D3085125FEE161244C1555D297258CEA502353B82D8E8DF0B314DAFDA4470",
    "attempt_003_design_economics_receipt_sha256": "B5E1A9581DACA11AC163FC9A7758B1C66A426FD5CDEAA22B9810BD26F6C33F29",
    "source_terminal_sha256": "27463114985202A024E7F4732DA7DE0CD2314875012C90B81E5A1A4D32E65512",
    "source_data_tree_sha256": "C2D607981E7CA73B40681FC7AFF5E7FDFCF240B9D9419B3C42ADBE9F590A5197",
    "source_manifest_sha256": "B53E008BE9CFBDC3F13F7044A7FC718DBAB87A4725D8C1F7B9F24D5F97B3234B",
    "stage0_ledger_sha256": "3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7",
    "stage0_receipt_sha256": "5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE",
    "decision_packet_manifest_sha256": "D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA",
    "decision_packet_receipt_sha256": "DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320",
    "dsr_tool_sha256": DSR_TOOL_SHA256,
}
AUTHORITY_HASH_FIELDS = (
    *EXPECTED_ARTIFACT_AUTHORITY_SHA256,
    "economics_tool_sha256",
    "economics_tool_test_sha256",
    "input_contract_preflight_receipt_sha256",
    "implementation_review_receipt_sha256",
    "run_packet_sha256",
)
SHA256_RE = re.compile(r"^[A-F0-9]{64}$")
SOURCE_BAR_FIELDS = {
    "time_server", "time_utc", "utc_offset_h", "open", "high", "low", "close",
    "tick_volume", "spread", "real_volume",
}
RUN_PACKET_PATH = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_RUN_PACKET_V4.json"
)

RUN_PACKET_FIELDS = (
    "active_probe_plan_path", "active_probe_plan_sha256",
    "attempt_001_design_economics_receipt_path",
    "attempt_001_design_economics_receipt_sha256",
    "attempt_001_terminal_path", "attempt_001_terminal_sha256",
    "attempt_002_design_economics_receipt_path",
    "attempt_002_design_economics_receipt_sha256",
    "attempt_002_terminal_path", "attempt_002_terminal_sha256",
    "attempt_003_design_economics_receipt_path",
    "attempt_003_design_economics_receipt_sha256",
    "attempt_003_terminal_path", "attempt_003_terminal_sha256",
    "decision_packet_manifest_path", "decision_packet_manifest_sha256",
    "decision_packet_receipt_path", "decision_packet_receipt_sha256",
    "decision_packet_root", "dsr_tool_path", "dsr_tool_sha256",
    "economics_authorized", "economics_tool_path", "economics_tool_sha256",
    "economics_tool_test_path", "economics_tool_test_sha256",
    "holdout_authorized", "hypothesis_id", "implementation_review_receipt_path",
    "implementation_review_receipt_sha256", "implementation_task_v1_path",
    "implementation_task_v1_sha256", "implementation_task_v2_path",
    "implementation_task_v2_sha256", "implementation_task_v3_path",
    "implementation_task_v3_sha256", "implementation_task_v4_path",
    "implementation_task_v4_sha256", "implementation_task_v5_path",
    "implementation_task_v5_sha256", "implementation_task_v6_path",
    "implementation_task_v6_sha256", "input_contract_preflight_receipt_path",
    "input_contract_preflight_receipt_sha256", "mql5_authorized", "model0_authorized",
    "network_allowed", "output_root", "projection_attempt_id",
    "registry_mutation_allowed", "research_holdout_authorized",
    "research_validation_authorized", "schema_version", "source_data_tree_sha256",
    "source_manifest_path", "source_manifest_sha256", "source_projection_root",
    "source_terminal_path", "source_terminal_sha256", "stage0_ledger_path",
    "stage0_ledger_sha256", "stage0_receipt_path", "stage0_receipt_sha256",
    "trading_mutation", "validation_authorized",
)
RUN_PACKET_FROZEN_VALUES = {
    "schema_version": "trendstack_007_design_economics_run_packet.v4",
    "hypothesis_id": HYPOTHESIS_ID,
    "projection_attempt_id": "HYP007-DESIGN-ECON-004",
    "active_probe_plan_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_PROBE_PLAN_V6.md",
    "active_probe_plan_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["active_probe_plan_sha256"],
    "implementation_task_v1_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_TASK_V1.json",
    "implementation_task_v1_sha256": IMPLEMENTATION_TASK_SHA256,
    "implementation_task_v2_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_TASK_V2.json",
    "implementation_task_v3_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_TASK_V3.json",
    "implementation_task_v4_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_TASK_V4.json",
    "implementation_task_v4_sha256": IMPLEMENTATION_TASK_V4_SHA256,
    "implementation_task_v5_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_TASK_V5.json",
    "implementation_task_v5_sha256": IMPLEMENTATION_TASK_V5_SHA256,
    "implementation_task_v6_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_TASK_V6.json",
    "implementation_task_v6_sha256": IMPLEMENTATION_TASK_V6_SHA256,
    "attempt_001_terminal_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-001/attempt_terminal.json",
    "attempt_001_terminal_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["attempt_001_terminal_sha256"],
    "attempt_001_design_economics_receipt_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-001/design_economics_receipt.json",
    "attempt_001_design_economics_receipt_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["attempt_001_design_economics_receipt_sha256"],
    "attempt_002_terminal_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-002/attempt_terminal.json",
    "attempt_002_terminal_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["attempt_002_terminal_sha256"],
    "attempt_002_design_economics_receipt_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-002/design_economics_receipt.json",
    "attempt_002_design_economics_receipt_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["attempt_002_design_economics_receipt_sha256"],
    "attempt_003_terminal_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-003/attempt_terminal.json",
    "attempt_003_terminal_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["attempt_003_terminal_sha256"],
    "attempt_003_design_economics_receipt_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-003/design_economics_receipt.json",
    "attempt_003_design_economics_receipt_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["attempt_003_design_economics_receipt_sha256"],
    "source_projection_root": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_007_design_h1_1200",
    "source_manifest_path": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_007_design_h1_1200/design_1200_manifest.jsonl",
    "source_manifest_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["source_manifest_sha256"],
    "source_data_tree_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["source_data_tree_sha256"],
    "source_terminal_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_PROJECTION_ATTEMPTS/HYP007-SOURCE-PROJECTION-7C4A91E6D2B80F35/attempt_terminal.json",
    "source_terminal_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["source_terminal_sha256"],
    "stage0_ledger_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-002_STAGE0/stage0_eligibility_ledger.jsonl",
    "stage0_ledger_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["stage0_ledger_sha256"],
    "stage0_receipt_path": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-002_STAGE0/stage0_receipt.json",
    "stage0_receipt_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["stage0_receipt_sha256"],
    "decision_packet_root": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_002/decision_packets",
    "decision_packet_manifest_path": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_002/decision_packet_manifest.jsonl",
    "decision_packet_manifest_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["decision_packet_manifest_sha256"],
    "decision_packet_receipt_path": "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_002/decision_packet_receipt.json",
    "decision_packet_receipt_sha256": EXPECTED_ARTIFACT_AUTHORITY_SHA256["decision_packet_receipt_sha256"],
    "dsr_tool_path": "02. AlphaFactory/tools/research/dsr.py",
    "dsr_tool_sha256": DSR_TOOL_SHA256,
    "economics_tool_path": "03. EA Developer/EA_TrendStackContinuation/research/evaluate_trendstack_007_design_economics.py",
    "economics_tool_test_path": "03. EA Developer/EA_TrendStackContinuation/research/tests/test_evaluate_trendstack_007_design_economics.py",
    "input_contract_preflight_receipt_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_INPUT_CONTRACT_PREFLIGHT_RECEIPT_V1.json",
    "implementation_review_receipt_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS_IMPLEMENTATION_REVIEW_RECEIPT_V4.json",
    "output_root": "03. EA Developer/EA_TrendStackContinuation/research/evidence/HYP-TRENDSTACK-EURUSD-H1-007_DESIGN_ECONOMICS/HYP007-DESIGN-ECON-004",
    "economics_authorized": True,
    "validation_authorized": False, "holdout_authorized": False,
    "research_validation_authorized": False, "research_holdout_authorized": False,
    "mql5_authorized": False, "model0_authorized": False,
    "network_allowed": False, "registry_mutation_allowed": False,
    "trading_mutation": False,
}

IMPLEMENTATION_REVIEW_RECEIPT_SCHEMA = (
    "trendstack_007_design_economics_implementation_review_receipt.v4"
)
IMPLEMENTATION_REVIEW_PASS_VERDICT = "PASS_INDEPENDENT_QUANT_CODE_REVIEW"
IMPLEMENTATION_REVIEW_RECEIPT_FIELDS = {
    "schema_version", "hypothesis_id", "projection_attempt_id", "verdict",
    "reviewed_sha256", "production_design_economics_run_authorized",
    "research_validation_authorized", "research_holdout_authorized",
    "mql5_authorized", "model0_authorized",
}
IMPLEMENTATION_REVIEW_HASH_FIELDS = {
    "implementation_task_v1_sha256", "implementation_task_v2_sha256",
    "implementation_task_v3_sha256", "implementation_task_v4_sha256",
    "implementation_task_v5_sha256", "implementation_task_v6_sha256",
    "economics_tool_sha256",
    "economics_tool_test_sha256",
}
INPUT_CONTRACT_PREFLIGHT_RECEIPT_SCHEMA = (
    "trendstack_007_design_input_contract_preflight_receipt.v1"
)
INPUT_CONTRACT_PREFLIGHT_PASS_STATUS = "PASS"
INPUT_CONTRACT_PREFLIGHT_RECEIPT_FIELDS = {
    "schema_version", "hypothesis_id", "status", "reviewed_sha256",
    "joined_rows", "first_design_date", "last_design_date",
    "economics_executed", "pnl_metrics_emitted", "research_validation_opened",
    "research_holdout_opened", "independent_read_only_recheck_passed",
}
INPUT_CONTRACT_PREFLIGHT_HASH_FIELDS = {
    "implementation_task_v6_sha256", "economics_tool_sha256",
    "economics_tool_test_sha256", "source_data_tree_sha256",
    "source_terminal_sha256", "source_manifest_sha256", "stage0_ledger_sha256",
    "stage0_receipt_sha256", "decision_packet_manifest_sha256",
    "decision_packet_receipt_sha256", "dsr_tool_sha256",
}


class InvalidEngineering(RuntimeError):
    """The frozen engineering contract was not satisfied."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidEngineering(f"INVALID_ENGINEERING {message}")


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    _require(type(value) in (int, float) and not isinstance(value, bool), f"{label} malformed")
    normalized = float(value)
    _require(math.isfinite(normalized), f"{label} nonfinite")
    if positive:
        _require(normalized > 0, f"{label} must be positive")
    return normalized


def sha256_bytes(payload: bytes) -> str:
    _require(type(payload) is bytes, "hash payload must be bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidEngineering("INVALID_ENGINEERING non-canonical JSON value") from exc


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidEngineering("INVALID_ENGINEERING duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise InvalidEngineering(f"INVALID_ENGINEERING non-finite JSON constant {value}")


def _validate_run_packet_values(packet: Any) -> dict[str, Any]:
    _require(type(packet) is dict and set(packet) == set(RUN_PACKET_FIELDS), "run packet field set mismatch")
    for field, expected in RUN_PACKET_FROZEN_VALUES.items():
        _require(packet.get(field) == expected, f"run packet frozen field drift: {field}")
    _require(
        packet.get("implementation_task_v2_sha256") == IMPLEMENTATION_TASK_V2_SHA256,
        "run packet Task V2 SHA mismatch",
    )
    _require(
        packet.get("implementation_task_v3_sha256") == IMPLEMENTATION_TASK_V3_SHA256,
        "run packet Task V3 SHA mismatch",
    )
    _require(
        packet.get("implementation_task_v4_sha256") == IMPLEMENTATION_TASK_V4_SHA256,
        "run packet Task V4 SHA mismatch",
    )
    _require(
        packet.get("implementation_task_v5_sha256") == IMPLEMENTATION_TASK_V5_SHA256,
        "run packet Task V5 SHA mismatch",
    )
    _require(
        packet.get("implementation_task_v6_sha256") == IMPLEMENTATION_TASK_V6_SHA256,
        "run packet Task V6 SHA mismatch",
    )
    for field in (
        "implementation_task_v2_sha256", "implementation_task_v3_sha256",
        "implementation_task_v4_sha256", "implementation_task_v5_sha256",
        "implementation_task_v6_sha256",
        "economics_tool_sha256", "economics_tool_test_sha256",
        "input_contract_preflight_receipt_sha256",
        "implementation_review_receipt_sha256",
    ):
        _strict_sha(packet.get(field), field)
    return packet


def parse_run_packet_document(payload: bytes) -> tuple[dict[str, Any], str]:
    """Parse one canonical V4-bound packet without opening any referenced path."""

    _require(type(payload) is bytes and payload.endswith(b"\n"), "run packet must end with LF")
    _require(b"\r" not in payload and payload.count(b"\n") == 1, "run packet must be one line")
    try:
        packet = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_no_duplicate_object,
            parse_constant=_reject_json_constant,
        )
    except InvalidEngineering:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidEngineering("INVALID_ENGINEERING run packet JSON malformed") from exc
    _validate_run_packet_values(packet)
    _require(payload == canonical_json_bytes(packet) + b"\n", "run packet is not canonical one-line JSON")
    return packet, sha256_bytes(payload)


def authority_file_bindings(packet: dict[str, Any]) -> dict[str, str]:
    _validate_run_packet_values(packet)
    pairs = (
        ("active_probe_plan_path", "active_probe_plan_sha256"),
        ("attempt_001_terminal_path", "attempt_001_terminal_sha256"),
        (
            "attempt_001_design_economics_receipt_path",
            "attempt_001_design_economics_receipt_sha256",
        ),
        ("attempt_002_terminal_path", "attempt_002_terminal_sha256"),
        (
            "attempt_002_design_economics_receipt_path",
            "attempt_002_design_economics_receipt_sha256",
        ),
        ("attempt_003_terminal_path", "attempt_003_terminal_sha256"),
        (
            "attempt_003_design_economics_receipt_path",
            "attempt_003_design_economics_receipt_sha256",
        ),
        ("implementation_task_v1_path", "implementation_task_v1_sha256"),
        ("implementation_task_v2_path", "implementation_task_v2_sha256"),
        ("implementation_task_v3_path", "implementation_task_v3_sha256"),
        ("implementation_task_v4_path", "implementation_task_v4_sha256"),
        ("implementation_task_v5_path", "implementation_task_v5_sha256"),
        ("implementation_task_v6_path", "implementation_task_v6_sha256"),
        ("source_terminal_path", "source_terminal_sha256"),
        ("source_manifest_path", "source_manifest_sha256"),
        ("stage0_ledger_path", "stage0_ledger_sha256"),
        ("stage0_receipt_path", "stage0_receipt_sha256"),
        ("decision_packet_manifest_path", "decision_packet_manifest_sha256"),
        ("decision_packet_receipt_path", "decision_packet_receipt_sha256"),
        ("dsr_tool_path", "dsr_tool_sha256"),
        ("economics_tool_path", "economics_tool_sha256"),
        ("economics_tool_test_path", "economics_tool_test_sha256"),
        (
            "input_contract_preflight_receipt_path",
            "input_contract_preflight_receipt_sha256",
        ),
        ("implementation_review_receipt_path", "implementation_review_receipt_sha256"),
    )
    bindings = {packet[path_field]: packet[sha_field] for path_field, sha_field in pairs}
    _require(len(bindings) == len(pairs), "authority path collision")
    return bindings


def artifact_authority_from_packet(packet: dict[str, Any], run_packet_sha256: str) -> dict[str, str]:
    _validate_run_packet_values(packet)
    authority = {
        field: packet[field]
        for field in EXPECTED_ARTIFACT_AUTHORITY_SHA256
    }
    authority.update({
        "economics_tool_sha256": packet["economics_tool_sha256"],
        "economics_tool_test_sha256": packet["economics_tool_test_sha256"],
        "input_contract_preflight_receipt_sha256": packet[
            "input_contract_preflight_receipt_sha256"
        ],
        "implementation_review_receipt_sha256": packet["implementation_review_receipt_sha256"],
        "run_packet_sha256": _strict_sha(run_packet_sha256, "run packet"),
    })
    _require(tuple(authority) == AUTHORITY_HASH_FIELDS, "artifact authority order mismatch")
    return authority


def _workspace_path(workspace_root: Path, relative: str, *, must_exist: bool) -> Path:
    _require(type(relative) is str and relative and "\\" not in relative, "workspace path malformed")
    fragment = Path(relative)
    _require(not fragment.is_absolute() and ".." not in fragment.parts, "workspace path escapes root")
    root = workspace_root.resolve(strict=True)
    target = root.joinpath(fragment)
    try:
        resolved = target.resolve(strict=must_exist)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise InvalidEngineering("INVALID_ENGINEERING workspace path resolution failed") from exc
    return resolved


def stable_read_regular(path: Path, workspace_root: Path) -> bytes:
    root = workspace_root.resolve(strict=True)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
        opened_lstat = os.lstat(resolved)
        _require(stat.S_ISREG(opened_lstat.st_mode), "authority/input path is not regular")
        _require(not stat.S_ISLNK(opened_lstat.st_mode), "authority/input symlink forbidden")
        attributes = getattr(opened_lstat, "st_file_attributes", 0)
        _require(not (attributes & 0x400), "authority/input reparse point forbidden")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        descriptor = os.open(resolved, flags)
        try:
            before = os.fstat(descriptor)
            chunks = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except InvalidEngineering:
        raise
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING stable file read failed") from exc
    identity = lambda value: (
        value.st_dev, value.st_ino, value.st_size,
        getattr(value, "st_mtime_ns", int(value.st_mtime * 1_000_000_000)),
    )
    _require(identity(opened_lstat) == identity(before) == identity(after), "file changed during stable read")
    payload = b"".join(chunks)
    _require(len(payload) == before.st_size, "stable read size mismatch")
    return payload


def _parse_json_document(payload: bytes, label: str) -> Any:
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_no_duplicate_object,
            parse_constant=_reject_json_constant,
        )
    except InvalidEngineering:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING {label} JSON malformed") from exc


def _parse_jsonl(payload: bytes, label: str) -> list[dict[str, Any]]:
    _require(type(payload) is bytes and payload.endswith(b"\n"), f"{label} must end with LF")
    rows = []
    for raw in payload.splitlines():
        _require(bool(raw), f"{label} contains blank row")
        row = _parse_json_document(raw, label)
        _require(type(row) is dict, f"{label} row malformed")
        rows.append(row)
    return rows


def read_run_packet(path: Path | str, workspace_root: Path | str = ".") -> tuple[dict[str, Any], str]:
    root = Path(workspace_root).resolve(strict=True)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _workspace_path(root, candidate.as_posix(), must_exist=True)
    payload = stable_read_regular(candidate, root)
    return parse_run_packet_document(payload)


def _source_data_tree_sha256(manifest_rows: list[dict[str, Any]]) -> str:
    _require(type(manifest_rows) is list and len(manifest_rows) == EXPECTED_DATES, "source manifest count mismatch")
    files = []
    for row in sorted(manifest_rows, key=lambda value: value.get("relative_path", "")):
        _require(type(row) is dict, "source manifest row malformed")
        relative = row.get("relative_path")
        size = row.get("bytes")
        digest = _strict_sha(row.get("sha256"), "source manifest row")
        _require(type(relative) is str and relative, "source manifest relative path malformed")
        _require(type(size) is int and not isinstance(size, bool) and size > 0, "source manifest bytes malformed")
        files.append({"relative_path": relative, "bytes": size, "sha256": digest})
    return sha256_bytes(canonical_json_bytes({
        "files": files,
        "schema_version": "trendstack_007_projection_data_tree.v1",
    }))


def select_design_authority_scope(
    source_manifest: list[dict[str, Any]],
    stage0_full: list[dict[str, Any]],
    decision_manifest_full: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate the full hash-bound ledgers, then expose only exact DESIGN rows."""

    _require(
        type(stage0_full) is list and len(stage0_full) == EXPECTED_STAGE0_TOTAL_ROWS,
        "full Stage-0 ledger count mismatch",
    )
    _require(
        all(
            type(row) is dict and row.get("split") in {"DESIGN", "VALIDATION_FEATURE_ONLY"}
            for row in stage0_full
        ),
        "full Stage-0 ledger split schema mismatch",
    )
    stage0_design = [row for row in stage0_full if row["split"] == "DESIGN"]
    validation_count = sum(row["split"] == "VALIDATION_FEATURE_ONLY" for row in stage0_full)
    _require(
        len(stage0_design) == EXPECTED_DATES
        and validation_count == EXPECTED_STAGE0_VALIDATION_FEATURE_ONLY_ROWS,
        "full Stage-0 split counts mismatch",
    )
    _require(type(decision_manifest_full) is list, "full decision manifest malformed")
    _require(
        all(
            type(row) is dict and row.get("split") in {"DESIGN", "VALIDATION_FEATURE_ONLY"}
            for row in decision_manifest_full
        ),
        "full decision manifest split schema mismatch",
    )
    decision_design = [row for row in decision_manifest_full if row["split"] == "DESIGN"]
    source_dates, _ = _index_unique(source_manifest, "date", "source manifest")
    stage0_dates, _ = _index_unique(stage0_design, "opportunity_id", "Stage-0 DESIGN ledger")
    decision_dates, _ = _index_unique(
        decision_design, "opportunity_id", "DESIGN decision packet manifest"
    )
    _require(
        source_dates == stage0_dates == decision_dates,
        "DESIGN authority date sets/order differ",
    )
    return stage0_design, decision_design


def _review_receipt_is_pass(payload: bytes, packet: dict[str, Any]) -> None:
    receipt = _parse_json_document(payload, "implementation review receipt")
    _require(
        type(receipt) is dict and set(receipt) == IMPLEMENTATION_REVIEW_RECEIPT_FIELDS,
        "implementation review receipt field set mismatch",
    )
    _require(
        receipt["schema_version"] == IMPLEMENTATION_REVIEW_RECEIPT_SCHEMA,
        "implementation review receipt schema mismatch",
    )
    _require(receipt.get("hypothesis_id") == HYPOTHESIS_ID, "implementation review hypothesis mismatch")
    _require(
        receipt["projection_attempt_id"] == packet["projection_attempt_id"],
        "implementation review attempt mismatch",
    )
    _require(
        receipt["verdict"] == IMPLEMENTATION_REVIEW_PASS_VERDICT,
        "independent implementation review is not PASS",
    )
    reviewed = receipt["reviewed_sha256"]
    _require(
        type(reviewed) is dict and set(reviewed) == IMPLEMENTATION_REVIEW_HASH_FIELDS,
        "implementation review hash field set mismatch",
    )
    for field in IMPLEMENTATION_REVIEW_HASH_FIELDS:
        _require(reviewed[field] == packet[field], f"implementation review hash mismatch: {field}")
    expected_authorizations = {
        "production_design_economics_run_authorized": True,
        "research_validation_authorized": False,
        "research_holdout_authorized": False,
        "mql5_authorized": False,
        "model0_authorized": False,
    }
    for field, expected in expected_authorizations.items():
        _require(
            type(receipt[field]) is bool and receipt[field] is expected,
            f"implementation review authorization mismatch: {field}",
        )


def _input_contract_preflight_receipt_is_pass(
    payload: bytes,
    packet: dict[str, Any],
    design_dates: list[str],
) -> None:
    """Validate the frozen, non-economic input-contract preflight receipt."""

    _validate_run_packet_values(packet)
    _require(
        type(design_dates) is list and len(design_dates) == EXPECTED_DATES,
        "input preflight DESIGN date count mismatch",
    )
    checked_dates = [
        _strict_date(value, "input preflight DESIGN date") for value in design_dates
    ]
    _require(
        checked_dates == sorted(checked_dates)
        and len(set(checked_dates)) == EXPECTED_DATES,
        "input preflight DESIGN dates malformed",
    )
    receipt = _parse_json_document(payload, "input contract preflight receipt")
    _require(
        type(receipt) is dict and set(receipt) == INPUT_CONTRACT_PREFLIGHT_RECEIPT_FIELDS,
        "input contract preflight receipt field set mismatch",
    )
    _require(
        receipt["schema_version"] == INPUT_CONTRACT_PREFLIGHT_RECEIPT_SCHEMA,
        "input contract preflight receipt schema mismatch",
    )
    _require(
        receipt["hypothesis_id"] == HYPOTHESIS_ID,
        "input contract preflight hypothesis mismatch",
    )
    _require(
        receipt["status"] == INPUT_CONTRACT_PREFLIGHT_PASS_STATUS,
        "input contract preflight is not PASS",
    )
    reviewed = receipt["reviewed_sha256"]
    _require(
        type(reviewed) is dict and set(reviewed) == INPUT_CONTRACT_PREFLIGHT_HASH_FIELDS,
        "input contract preflight hash field set mismatch",
    )
    for field in INPUT_CONTRACT_PREFLIGHT_HASH_FIELDS:
        _require(
            reviewed[field] == packet[field],
            f"input contract preflight hash mismatch: {field}",
        )
    _require(
        type(receipt["joined_rows"]) is int
        and receipt["joined_rows"] == EXPECTED_DATES,
        "input contract preflight joined row count mismatch",
    )
    _require(
        receipt["first_design_date"] == checked_dates[0]
        and receipt["last_design_date"] == checked_dates[-1],
        "input contract preflight DESIGN date bounds mismatch",
    )
    expected_flags = {
        "economics_executed": False,
        "pnl_metrics_emitted": False,
        "research_validation_opened": False,
        "research_holdout_opened": False,
        "independent_read_only_recheck_passed": True,
    }
    for field, expected in expected_flags.items():
        _require(
            type(receipt[field]) is bool and receipt[field] is expected,
            f"input contract preflight flag mismatch: {field}",
        )


def verify_production_authority(
    packet: dict[str, Any], workspace_root: Path | str = "."
) -> dict[str, Any]:
    """Hash all authority metadata while leaving source shards and packets closed."""

    _validate_run_packet_values(packet)
    root = Path(workspace_root).resolve(strict=True)
    output = _workspace_path(root, packet["output_root"], must_exist=False)
    _require(not os.path.lexists(output), "frozen output root already exists")
    payloads: dict[str, bytes] = {}
    for relative, expected_sha256 in authority_file_bindings(packet).items():
        path = _workspace_path(root, relative, must_exist=True)
        payload = stable_read_regular(path, root)
        _require(sha256_bytes(payload) == expected_sha256, f"authority SHA mismatch: {relative}")
        payloads[relative] = payload
    source_manifest = _parse_jsonl(payloads[packet["source_manifest_path"]], "source manifest")
    _require(
        _source_data_tree_sha256(source_manifest) == packet["source_data_tree_sha256"],
        "source data-tree SHA mismatch",
    )
    stage0_full = _parse_jsonl(payloads[packet["stage0_ledger_path"]], "Stage-0 ledger")
    decision_manifest_all = _parse_jsonl(
        payloads[packet["decision_packet_manifest_path"]], "decision packet manifest"
    )
    stage0, decision_manifest = select_design_authority_scope(
        source_manifest, stage0_full, decision_manifest_all
    )
    _review_receipt_is_pass(payloads[packet["implementation_review_receipt_path"]], packet)
    _input_contract_preflight_receipt_is_pass(
        payloads[packet["input_contract_preflight_receipt_path"]],
        packet,
        [row["date"] for row in source_manifest],
    )
    dsr_callable = load_dsr_callable_from_bytes(
        payloads[packet["dsr_tool_path"]],
        packet["dsr_tool_sha256"],
        source_name=packet["dsr_tool_path"],
    )
    for directory_field in ("source_projection_root", "decision_packet_root"):
        directory = _workspace_path(root, packet[directory_field], must_exist=True)
        _require(directory.is_dir() and not directory.is_symlink(), f"{directory_field} is not a safe directory")
    return {
        "workspace_root": root,
        "source_manifest": source_manifest,
        "stage0_ledger": stage0,
        "decision_manifest": decision_manifest,
        "dsr_callable": dsr_callable,
    }


EXPECTED_ARROW_TYPES = (
    ("time_server", "timestamp[ns]"),
    ("time_utc", "timestamp[ns]"),
    ("utc_offset_h", "int8"),
    ("open", "double"),
    ("high", "double"),
    ("low", "double"),
    ("close", "double"),
    ("tick_volume", "uint64"),
    ("spread", "int32"),
    ("real_volume", "uint64"),
)


def _decode_source_shard(payload: bytes) -> list[dict[str, Any]]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(pa.BufferReader(payload))
        schema = parquet.schema_arrow
        observed = tuple((field.name, str(field.type)) for field in schema)
        _require(observed == EXPECTED_ARROW_TYPES, "source Parquet physical schema mismatch")
        table = parquet.read()
        _require(table.num_rows == 1 and table.num_columns == len(EXPECTED_ARROW_TYPES), "source Parquet row shape mismatch")
        rows = table.to_pylist()
    except InvalidEngineering:
        raise
    except Exception as exc:
        raise InvalidEngineering("INVALID_ENGINEERING source Parquet decode failed") from exc
    _require(type(rows) is list and len(rows) == 1, "source Parquet decode row mismatch")
    return rows


def load_production_inputs(
    packet: dict[str, Any], authority_context: dict[str, Any]
) -> dict[str, Any]:
    """Open only the 1297 frozen DESIGN shards and DESIGN decision packets."""

    _validate_run_packet_values(packet)
    required_context = {
        "workspace_root", "source_manifest", "stage0_ledger",
        "decision_manifest", "dsr_callable",
    }
    _require(
        type(authority_context) is dict and set(authority_context) == required_context,
        "authority context malformed",
    )
    root = authority_context["workspace_root"]
    _require(isinstance(root, Path), "authority workspace root malformed")
    source_rows: dict[str, dict[str, Any]] = {}
    for meta in authority_context["source_manifest"]:
        _require(type(meta) is dict, "source manifest row malformed")
        day = _strict_date(meta.get("date"), "source manifest date")
        relative = meta.get("relative_path")
        _require(relative == f"DESIGN/{day}/h1_1200.parquet", "source manifest path mismatch")
        path = _workspace_path(
            root, f'{packet["source_projection_root"]}/{relative}', must_exist=True
        )
        payload = stable_read_regular(path, root)
        expected_sha = _strict_sha(meta.get("sha256"), "source manifest")
        _require(sha256_bytes(payload) == expected_sha, "source shard SHA mismatch")
        _require(meta.get("bytes") == len(payload) and meta.get("rows") == 1, "source shard size/row mismatch")
        _require(day not in source_rows, "source manifest duplicate date")
        source_rows[day] = {
            "file_sha256": expected_sha,
            "rows": _decode_source_shard(payload),
        }

    decision_packets: dict[str, dict[str, Any]] = {}
    for meta in authority_context["decision_manifest"]:
        _require(type(meta) is dict, "decision manifest row malformed")
        day = _strict_date(meta.get("opportunity_id"), "decision manifest opportunity")
        relative = meta.get("packet_path")
        _require(relative == f"DESIGN/{day}.json", "decision manifest path mismatch")
        path = _workspace_path(root, f'{packet["decision_packet_root"]}/{relative}', must_exist=True)
        payload = stable_read_regular(path, root)
        expected_sha = _strict_sha(meta.get("packet_file_sha256"), "decision manifest file")
        _require(sha256_bytes(payload) == expected_sha, "decision packet file SHA mismatch")
        if "packet_bytes" in meta:
            _require(meta["packet_bytes"] == len(payload), "decision packet byte count mismatch")
        decoded = _parse_json_document(payload, "decision packet")
        _require(type(decoded) is dict, "decision packet document malformed")
        _require(day not in decision_packets, "decision packet duplicate date")
        decision_packets[day] = {"file_sha256": expected_sha, "packet": decoded}

    return {
        "source_manifest": authority_context["source_manifest"],
        "source_rows_by_date": source_rows,
        "stage0_ledger": authority_context["stage0_ledger"],
        "decision_manifest": authority_context["decision_manifest"],
        "decision_packets_by_date": decision_packets,
        "dsr_callable": authority_context["dsr_callable"],
    }


def _strict_date(value: Any, label: str) -> str:
    _require(type(value) is str and len(value) == 10, f"{label} malformed")
    try:
        from datetime import date

        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING {label} malformed") from exc
    _require(parsed.isoformat() == value and 2016 <= parsed.year <= 2020, f"{label} outside DESIGN")
    return value


def _strict_sha(value: Any, label: str) -> str:
    _require(type(value) is str and SHA256_RE.fullmatch(value) is not None, f"{label} SHA256 malformed")
    return value


def _index_unique(rows: list[dict], key: str, label: str) -> tuple[list[str], dict[str, dict]]:
    _require(type(rows) is list and len(rows) == EXPECTED_DATES, f"{label} count mismatch")
    dates: list[str] = []
    indexed: dict[str, dict] = {}
    for row in rows:
        _require(type(row) is dict, f"{label} row malformed")
        day = _strict_date(row.get(key), f"{label} {key}")
        _require(day not in indexed, f"{label} duplicate date")
        dates.append(day)
        indexed[day] = row
    _require(dates == sorted(dates), f"{label} date order mismatch")
    return dates, indexed


def _validate_source_bar(day: str, source_file: Any, expected_sha256: str) -> dict:
    _require(
        type(source_file) is dict and set(source_file) == {"file_sha256", "rows"},
        "source file wrapper malformed",
    )
    _require(source_file["file_sha256"] == expected_sha256, "source manifest/file SHA mismatch")
    rows = source_file["rows"]
    _require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict, "source day must contain one row")
    bar = rows[0]
    _require(set(bar) == SOURCE_BAR_FIELDS, "source row schema mismatch")
    utc = bar["time_utc"]
    server = bar["time_server"]
    offset = bar["utc_offset_h"]
    _require(
        isinstance(utc, datetime)
        and utc.tzinfo is None
        and utc == datetime.fromisoformat(f"{day}T12:00:00"),
        "source row is not exact 12:00 UTC",
    )
    _require(
        isinstance(server, datetime)
        and server.tzinfo is None
        and type(offset) is int
        and not isinstance(offset, bool)
        and server - utc == timedelta(hours=offset),
        "source server clock geometry invalid",
    )
    for name in ("tick_volume", "spread", "real_volume"):
        _require(
            type(bar[name]) is int and not isinstance(bar[name], bool) and bar[name] >= 0,
            f"source {name} malformed",
        )
    opening = _number(bar.get("open"), "source open", positive=True)
    high = _number(bar.get("high"), "source high", positive=True)
    low = _number(bar.get("low"), "source low", positive=True)
    closing = _number(bar.get("close"), "source close", positive=True)
    _require(high >= max(opening, closing) and low <= min(opening, closing) and high >= low, "source OHLC geometry invalid")
    return bar


def _validate_stage0_row(
    day: str, row: dict, packet_sha256: str, packet_payload_sha256: str
) -> None:
    _require(row.get("opportunity_id") == day, "Stage-0 opportunity mismatch")
    _require(row.get("split") == "DESIGN", "Stage-0 split mismatch")
    _require(row.get("packet_path") == f"DESIGN/{day}.json", "Stage-0 packet path mismatch")
    _require(row.get("packet_file_sha256") == packet_sha256, "Stage-0 packet SHA mismatch")
    _require(
        row.get("packet_payload_sha256") == packet_payload_sha256,
        "Stage-0 packet payload SHA mismatch",
    )
    for arm, (eligible_field, direction_field) in ARM_FIELDS.items():
        eligible = row.get(eligible_field)
        direction = row.get(direction_field)
        _require(type(eligible) is bool, f"{arm} eligibility malformed")
        if eligible:
            _require(type(direction) is int and not isinstance(direction, bool) and direction in (-1, 1), f"{arm} direction malformed")
        else:
            _require(direction is None, f"{arm} ineligible direction must be null")
    _require(
        not (row["challenger_stack_eligible"] and row["negative_disagree_eligible"]),
        "STACK and DISAGREE cannot both be eligible",
    )


def _validate_decision_packet(
    day: str,
    packet_file: Any,
    expected_file_sha256: str,
    expected_payload_sha256: str,
) -> float:
    _require(
        type(packet_file) is dict and set(packet_file) == {"file_sha256", "packet"},
        "decision packet file wrapper malformed",
    )
    _require(packet_file["file_sha256"] == expected_file_sha256, "decision manifest/file SHA mismatch")
    packet = packet_file["packet"]
    _require(type(packet) is dict, "decision packet malformed")
    _require(packet.get("schema_version") == "trendstack_002_decision_packet.v1", "decision packet schema mismatch")
    _require(packet.get("hypothesis_id") == "HYP-TRENDSTACK-EURUSD-H1-002", "decision packet hypothesis mismatch")
    _require(packet.get("opportunity_id") == day, "decision packet opportunity mismatch")
    _require(packet.get("split") == "DESIGN", "decision packet split mismatch")
    payload_sha = _strict_sha(packet.get("packet_payload_sha256"), "decision packet payload")
    _require(payload_sha == expected_payload_sha256, "decision manifest/payload SHA mismatch")
    unhashed = {key: value for key, value in packet.items() if key != "packet_payload_sha256"}
    _require(sha256_bytes(canonical_json_bytes(unhashed)) == payload_sha, "decision packet payload SHA invalid")
    return _number(packet.get("atr20"), "decision packet atr20", positive=True)


def join_frozen_inputs(
    source_manifest: list[dict],
    source_rows_by_date: dict[str, list[dict]],
    stage0_ledger: list[dict],
    decision_manifest: list[dict],
    decision_packets_by_date: dict[str, dict],
) -> list[dict]:
    """Join the four frozen DESIGN surfaces without fill, drop, or substitution."""

    source_dates, source_index = _index_unique(source_manifest, "date", "source manifest")
    ledger_dates, ledger_index = _index_unique(stage0_ledger, "opportunity_id", "Stage-0 ledger")
    packet_dates, packet_manifest_index = _index_unique(
        decision_manifest, "opportunity_id", "decision packet manifest"
    )
    _require(type(source_rows_by_date) is dict, "source row map malformed")
    _require(type(decision_packets_by_date) is dict, "decision packet map malformed")
    exact_set = set(source_dates)
    _require(
        exact_set
        == set(ledger_dates)
        == set(packet_dates)
        == set(source_rows_by_date)
        == set(decision_packets_by_date),
        "joined date sets differ",
    )
    joined = []
    for day in source_dates:
        source_meta = source_index[day]
        source_sha = _strict_sha(source_meta.get("sha256"), "source manifest")
        _require(source_meta.get("relative_path") == f"DESIGN/{day}/h1_1200.parquet", "source manifest path mismatch")
        _require(source_meta.get("rows") == 1, "source manifest row count mismatch")
        bar = _validate_source_bar(day, source_rows_by_date[day], source_sha)

        packet_meta = packet_manifest_index[day]
        packet_sha = _strict_sha(packet_meta.get("packet_file_sha256"), "decision manifest file")
        packet_payload_sha = _strict_sha(
            packet_meta.get("packet_payload_sha256"), "decision manifest payload"
        )
        _require(packet_meta.get("split") == "DESIGN", "decision manifest split mismatch")
        _require(packet_meta.get("packet_path") == f"DESIGN/{day}.json", "decision manifest path mismatch")
        atr20 = _validate_decision_packet(
            day, decision_packets_by_date[day], packet_sha, packet_payload_sha
        )
        stage0 = ledger_index[day]
        _validate_stage0_row(day, stage0, packet_sha, packet_payload_sha)
        joined.append({
            "date": day,
            "source_bar": bar,
            "stage0": stage0,
            "atr20": atr20,
            "source_file_sha256": source_sha,
            "decision_packet_sha256": packet_sha,
        })
    _require(arm_counts(joined) == EXPECTED_ARM_COUNTS, "frozen arm counts mismatch")
    return joined


def arm_counts(joined: list[dict]) -> dict[str, int]:
    counts = {arm: 0 for arm in ARMS}
    for item in joined:
        _require(type(item) is dict and type(item.get("stage0")) is dict, "joined row malformed")
        stage0 = item["stage0"]
        for arm, (eligible_field, _) in ARM_FIELDS.items():
            eligible = stage0.get(eligible_field)
            _require(type(eligible) is bool, f"{arm} eligibility malformed")
            counts[arm] += int(eligible)
    return counts


def simulate_h1_trade(bar: dict, *, direction: int, atr20: float) -> dict[str, Any]:
    _require(type(direction) is int and not isinstance(direction, bool) and direction in (-1, 1), "direction must be -1 or +1")
    atr = _number(atr20, "atr20", positive=True)
    _require(type(bar) is dict, "source bar malformed")
    opening = _number(bar.get("open"), "open", positive=True)
    high = _number(bar.get("high"), "high", positive=True)
    low = _number(bar.get("low"), "low", positive=True)
    closing = _number(bar.get("close"), "close", positive=True)
    _require(high >= max(opening, closing) and low <= min(opening, closing), "OHLC geometry invalid")
    stop = opening - atr if direction == 1 else opening + atr
    touched = low <= stop if direction == 1 else high >= stop
    exit_bid = stop if touched else closing
    reason = "STOP_TOUCH" if touched else "BAR_CLOSE"
    gross_r = direction * (exit_bid - opening) / atr
    _require(math.isfinite(gross_r), "gross R nonfinite")
    return {
        "entry_bid": opening,
        "stop_bid": stop,
        "exit_bid": exit_bid,
        "exit_reason": reason,
        "gross_R": gross_r,
    }


def cost_r(*, atr20: float, round_trip_cost_pips: float) -> float:
    atr = _number(atr20, "atr20", positive=True)
    cost = _number(round_trip_cost_pips, "round-trip cost")
    _require(cost >= 0, "round-trip cost must be nonnegative")
    result = cost / (atr / PIP)
    _require(math.isfinite(result), "cost R nonfinite")
    return result


def apply_cost(gross_r: float, *, atr20: float, round_trip_cost_pips: float) -> float:
    gross = _number(gross_r, "gross R")
    result = gross - cost_r(atr20=atr20, round_trip_cost_pips=round_trip_cost_pips)
    _require(math.isfinite(result), "net R nonfinite")
    return result


def profit_factor(values: list[float]) -> dict[str, Any]:
    _require(type(values) is list and bool(values), "profit-factor sample empty")
    normalized = [_number(value, "profit-factor return") for value in values]
    gains = sum(value for value in normalized if value > 0)
    loss = -sum(value for value in normalized if value < 0)
    if loss == 0:
        if gains == 0:
            return {"status": "NO_WIN_NO_LOSS", "value": None}
        return {"status": "NO_LOSS", "value": None}
    return {"status": "FINITE", "value": gains / loss}


def _validate_pf(value: Any) -> dict[str, Any]:
    _require(type(value) is dict and set(value) == {"status", "value"}, "PF object malformed")
    status = value["status"]
    _require(status in {"FINITE", "NO_LOSS", "NO_WIN_NO_LOSS"}, "PF status malformed")
    if status == "FINITE":
        _number(value["value"], "finite PF")
    else:
        _require(value["value"] is None, "non-finite PF value must be null")
    return value


def relative_profit_factor(challenger: dict, comparator: dict) -> dict[str, Any]:
    left = _validate_pf(challenger)
    right = _validate_pf(comparator)
    if "NO_WIN_NO_LOSS" in {left["status"], right["status"]}:
        return {"status": "UNDEFINED", "value": None}
    if left["status"] == right["status"] == "NO_LOSS":
        return {"status": "ZERO_BOTH_NO_LOSS", "value": 0.0}
    if left["status"] == "NO_LOSS":
        return {"status": "POSITIVE_INFINITY", "value": None}
    if right["status"] == "NO_LOSS":
        return {"status": "NEGATIVE_INFINITY", "value": None}
    return {"status": "FINITE", "value": float(left["value"]) - float(right["value"])}


def relative_pf_pass(value: dict, threshold: float) -> bool:
    _require(type(value) is dict and set(value) == {"status", "value"}, "relative PF malformed")
    limit = _number(threshold, "relative PF threshold")
    if value["status"] == "POSITIVE_INFINITY":
        return True
    if value["status"] != "FINITE":
        return False
    return _number(value["value"], "relative PF delta") >= limit


def _absolute_pf_pass(value: dict, threshold: float, *, strict: bool) -> bool:
    pf = _validate_pf(value)
    if pf["status"] == "NO_LOSS":
        return True
    if pf["status"] != "FINITE":
        return False
    observed = float(pf["value"])
    return observed > threshold if strict else observed >= threshold


def cadence(trade_count: int) -> float:
    _require(type(trade_count) is int and not isinstance(trade_count, bool) and trade_count >= 0, "trade count malformed")
    return trade_count / ELAPSED_WEEKS


def yearly_metrics(rows: list[dict]) -> dict[str, Any]:
    _require(type(rows) is list, "yearly rows malformed")
    totals = {str(year): 0.0 for year in DESIGN_YEARS}
    for row in rows:
        _require(type(row) is dict, "yearly trade row malformed")
        day = _strict_date(row.get("date"), "trade date")
        totals[day[:4]] += _number(row.get("net_R_1_50"), "yearly net R")
    return {
        "yearly_total_net_R_1_50": totals,
        "positive_years_1_50": sum(value > 0 for value in totals.values()),
        "year_denominator": list(DESIGN_YEARS),
    }


def sample_sharpe(values: list[float]) -> float:
    _require(type(values) is list and len(values) >= 2, "Sharpe sample invalid")
    normalized = [_number(value, "Sharpe return") for value in values]
    deviation = statistics.stdev(normalized)
    return 0.0 if deviation == 0 else statistics.fmean(normalized) / deviation


def population_shape(values: list[float]) -> tuple[float, float]:
    _require(type(values) is list and bool(values), "shape sample invalid")
    normalized = [_number(value, "shape return") for value in values]
    mean = statistics.fmean(normalized)
    centered = [value - mean for value in normalized]
    second = statistics.fmean(value * value for value in centered)
    if second == 0:
        return 0.0, 3.0
    third = statistics.fmean(value**3 for value in centered)
    fourth = statistics.fmean(value**4 for value in centered)
    return third / second**1.5, fourth / second**2


def compute_dsr(
    arm_returns: dict[str, list[float]],
    dsr_callable: Callable[[float, int, float, float, float, int], float],
) -> dict[str, Any]:
    _require(type(arm_returns) is dict and set(arm_returns) == set(ARMS), "DSR requires four frozen arms")
    _require(callable(dsr_callable), "DSR callable missing")
    for arm in ARMS:
        _require(len(arm_returns[arm]) == EXPECTED_ARM_COUNTS[arm], f"{arm} DSR observation count mismatch")
    sharpes = {arm: sample_sharpe(arm_returns[arm]) for arm in ARMS}
    variance = statistics.variance(sharpes.values())
    challenger = [_number(value, "STACK DSR return") for value in arm_returns["CHALLENGER_STACK"]]
    skew, kurtosis = population_shape(challenger)
    arguments = {
        "sr": sharpes["CHALLENGER_STACK"],
        "n_obs": EXPECTED_ARM_COUNTS["CHALLENGER_STACK"],
        "skew": skew,
        "kurt": kurtosis,
        "var_sr_trials": variance,
        "n_trials": 4,
    }
    observed = dsr_callable(
        arguments["sr"], arguments["n_obs"], arguments["skew"], arguments["kurt"],
        arguments["var_sr_trials"], arguments["n_trials"],
    )
    value = _number(observed, "DSR result")
    _require(0 <= value <= 1, "DSR result outside probability range")
    return {
        "dsr": value,
        **arguments,
        "arm_sharpes": sharpes,
        "dsr_tool_sha256": DSR_TOOL_SHA256,
    }


def load_dsr_callable_from_bytes(
    payload: bytes, expected_sha256: str, *, source_name: str = "<verified-dsr.py>"
):
    """Compile and execute the exact bytes whose SHA was accepted."""

    expected = _strict_sha(expected_sha256, "DSR tool")
    _require(type(payload) is bytes, "DSR tool payload malformed")
    _require(sha256_bytes(payload) == expected, "DSR tool hash mismatch")
    try:
        code = compile(payload, source_name, "exec", dont_inherit=True, optimize=0)
        namespace = {
            "__name__": "trendstack_007_canonical_dsr",
            "__file__": source_name,
            "__package__": None,
        }
        exec(code, namespace, namespace)
    except Exception as exc:
        raise InvalidEngineering("INVALID_ENGINEERING DSR verified bytes cannot execute") from exc
    _require(callable(namespace.get("dsr")), "DSR function missing")
    return namespace["dsr"]


def load_dsr_callable(path: Path | str, expected_sha256: str):
    target = Path(path).absolute()
    try:
        payload = target.read_bytes()
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING DSR tool unreadable") from exc
    return load_dsr_callable_from_bytes(
        payload, expected_sha256, source_name=str(target)
    )


def evaluate_twelve_gates(values: dict[str, Any]) -> dict[str, Any]:
    required = {
        "cadence", "pf_1_50", "pf_2_25", "pf_3_00", "mean_net_r_1_50",
        "total_net_r_1_50", "positive_years", "dsr_1_50",
        "stack_pf_delta_vs_best_standalone", "stack_mean_delta_vs_best_standalone",
        "stack_pf_delta_vs_disagree", "stack_mean_delta_vs_disagree",
    }
    _require(type(values) is dict and set(values) == required, "12-gate value schema mismatch")
    observed_cadence = _number(values["cadence"], "cadence")
    mean_150 = _number(values["mean_net_r_1_50"], "mean net R 1.50")
    total_150 = _number(values["total_net_r_1_50"], "total net R 1.50")
    dsr_150 = _number(values["dsr_1_50"], "DSR 1.50")
    mean_control_delta = _number(values["stack_mean_delta_vs_best_standalone"], "standalone mean delta")
    mean_disagree_delta = _number(values["stack_mean_delta_vs_disagree"], "DISAGREE mean delta")
    positive_years = values["positive_years"]
    _require(type(positive_years) is int and not isinstance(positive_years, bool), "positive-year count malformed")
    checks = (
        ("G01", "cadence_2_to_5_inclusive", 2.0 <= observed_cadence <= 5.0, observed_cadence, "2.0<=x<=5.0"),
        ("G02", "pf_1_50_strict", _absolute_pf_pass(values["pf_1_50"], 1.30, strict=True), values["pf_1_50"], ">1.30"),
        ("G03", "pf_2_25", _absolute_pf_pass(values["pf_2_25"], 1.25, strict=False), values["pf_2_25"], ">=1.25"),
        ("G04", "pf_3_00", _absolute_pf_pass(values["pf_3_00"], 1.00, strict=False), values["pf_3_00"], ">=1.00"),
        ("G05", "mean_net_r_1_50", mean_150 >= 0.08, mean_150, ">=0.08"),
        ("G06", "total_net_r_1_50_strict", total_150 > 0.0, total_150, ">0"),
        ("G07", "positive_design_years", positive_years >= 4, positive_years, ">=4of5"),
        ("G08", "dsr_1_50", dsr_150 >= 0.95, dsr_150, ">=0.95"),
        ("G09", "pf_delta_best_standalone", relative_pf_pass(values["stack_pf_delta_vs_best_standalone"], 0.15), values["stack_pf_delta_vs_best_standalone"], ">=0.15"),
        ("G10", "mean_delta_best_standalone", mean_control_delta >= 0.05, mean_control_delta, ">=0.05"),
        ("G11", "pf_delta_disagree", relative_pf_pass(values["stack_pf_delta_vs_disagree"], 0.15), values["stack_pf_delta_vs_disagree"], ">=0.15"),
        ("G12", "mean_delta_disagree", mean_disagree_delta >= 0.05, mean_disagree_delta, ">=0.05"),
    )
    gates = [
        {"gate_id": gate_id, "name": name, "status": "PASS" if passed else "FAIL", "observed": observed, "threshold": threshold}
        for gate_id, name, passed, observed, threshold in checks
    ]
    return {
        "schema_version": "trendstack_007_design_economics_gate_report.v1",
        "gates": gates,
        "all_pass": all(item[2] for item in checks),
    }


def terminal_verdict(gate_report: dict) -> str:
    _require(type(gate_report) is dict and type(gate_report.get("all_pass")) is bool, "gate report malformed")
    return "PROBE_SURVIVOR_DESIGN_ONLY" if gate_report["all_pass"] else "KILL_EXACT_HYP007_DESIGN_OBJECT"


def _summarize_arm(rows: list[dict]) -> dict[str, Any]:
    _require(type(rows) is list and bool(rows), "arm trade sample empty")
    result: dict[str, Any] = {"trade_count": len(rows)}
    for suffix, cost_pips in COST_TIERS:
        values = [_number(row[f"net_R_{suffix}"], f"net R {suffix}") for row in rows]
        result[f"cost_{suffix}"] = {
            "round_trip_cost_pips": cost_pips,
            "profit_factor": profit_factor(values),
            "mean_net_R": statistics.fmean(values),
            "total_net_R": sum(values),
        }
    return result


def _better_standalone(left: dict, right: dict) -> dict:
    first = _validate_pf(left)
    second = _validate_pf(right)
    rank = {"NO_WIN_NO_LOSS": 0, "FINITE": 1, "NO_LOSS": 2}
    if rank[first["status"]] != rank[second["status"]]:
        return first if rank[first["status"]] > rank[second["status"]] else second
    if first["status"] == "FINITE":
        return first if float(first["value"]) >= float(second["value"]) else second
    return first


def evaluate_design(
    source_manifest: list[dict],
    source_rows_by_date: dict[str, list[dict]],
    stage0_ledger: list[dict],
    decision_manifest: list[dict],
    decision_packets_by_date: dict[str, dict],
    *,
    dsr_callable: Callable[[float, int, float, float, float, int], float],
) -> dict[str, Any]:
    joined = join_frozen_inputs(
        source_manifest, source_rows_by_date, stage0_ledger,
        decision_manifest, decision_packets_by_date,
    )
    trade_rows: list[dict] = []
    for item in joined:
        day = item["date"]
        stage0 = item["stage0"]
        for arm, (eligible_field, direction_field) in ARM_FIELDS.items():
            if not stage0[eligible_field]:
                continue
            direction = stage0[direction_field]
            execution = simulate_h1_trade(item["source_bar"], direction=direction, atr20=item["atr20"])
            row = {
                "schema_version": "trendstack_007_design_economics_trade.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "date": day,
                "opportunity_id": day,
                "arm": arm,
                "direction": direction,
                "atr20": item["atr20"],
                "atr20_source": f"decision_packets/DESIGN/{day}.json",
                "source_file_sha256": item["source_file_sha256"],
                "decision_packet_sha256": item["decision_packet_sha256"],
                **execution,
            }
            for suffix, cost_pips in COST_TIERS:
                row[f"cost_R_{suffix}"] = cost_r(
                    atr20=item["atr20"], round_trip_cost_pips=cost_pips
                )
                row[f"net_R_{suffix}"] = apply_cost(
                    execution["gross_R"], atr20=item["atr20"],
                    round_trip_cost_pips=cost_pips,
                )
            trade_rows.append(row)
    _require(len(trade_rows) == EXPECTED_TOTAL_TRADES, "evaluated trade count mismatch")
    grouped = {arm: [row for row in trade_rows if row["arm"] == arm] for arm in ARMS}
    _require({arm: len(rows) for arm, rows in grouped.items()} == EXPECTED_ARM_COUNTS, "evaluated arm counts mismatch")
    arm_metrics = {arm: _summarize_arm(rows) for arm, rows in grouped.items()}
    stack_yearly = yearly_metrics(grouped["CHALLENGER_STACK"])
    returns_150 = {
        arm: [float(row["net_R_1_50"]) for row in grouped[arm]] for arm in ARMS
    }
    dsr_inputs = compute_dsr(returns_150, dsr_callable)
    stack = arm_metrics["CHALLENGER_STACK"]
    m252 = arm_metrics["CONTROL_M252_ONLY"]
    m6 = arm_metrics["CONTROL_M6_ONLY"]
    disagree = arm_metrics["NEGATIVE_DISAGREE"]
    stack_pf = stack["cost_1_50"]["profit_factor"]
    better_standalone_pf = _better_standalone(
        m252["cost_1_50"]["profit_factor"], m6["cost_1_50"]["profit_factor"]
    )
    best_standalone_mean = max(
        m252["cost_1_50"]["mean_net_R"], m6["cost_1_50"]["mean_net_R"]
    )
    gate_values = {
        "cadence": cadence(stack["trade_count"]),
        "pf_1_50": stack_pf,
        "pf_2_25": stack["cost_2_25"]["profit_factor"],
        "pf_3_00": stack["cost_3_00"]["profit_factor"],
        "mean_net_r_1_50": stack["cost_1_50"]["mean_net_R"],
        "total_net_r_1_50": stack["cost_1_50"]["total_net_R"],
        "positive_years": stack_yearly["positive_years_1_50"],
        "dsr_1_50": dsr_inputs["dsr"],
        "stack_pf_delta_vs_best_standalone": relative_profit_factor(stack_pf, better_standalone_pf),
        "stack_mean_delta_vs_best_standalone": stack["cost_1_50"]["mean_net_R"] - best_standalone_mean,
        "stack_pf_delta_vs_disagree": relative_profit_factor(
            stack_pf, disagree["cost_1_50"]["profit_factor"]
        ),
        "stack_mean_delta_vs_disagree": stack["cost_1_50"]["mean_net_R"] - disagree["cost_1_50"]["mean_net_R"],
    }
    gate_report = evaluate_twelve_gates(gate_values)
    return {
        "schema_version": "trendstack_007_design_economics_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "engineering_status": "PASS",
        "verdict": terminal_verdict(gate_report),
        "cost_status": "UNVERIFIED_PROXY_KILL_ONLY",
        "trade_rows": trade_rows,
        "arm_metrics": arm_metrics,
        "yearly_metrics": stack_yearly,
        "dsr_inputs": dsr_inputs,
        "gate_values": gate_values,
        "gate_report": gate_report,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }


def _validate_authority(authority_hashes: dict[str, str], evaluator_sha256: str) -> None:
    _require(type(authority_hashes) is dict and tuple(authority_hashes) == AUTHORITY_HASH_FIELDS, "authority hash schema mismatch")
    for field, value in authority_hashes.items():
        _strict_sha(value, field)
    for field, expected in EXPECTED_ARTIFACT_AUTHORITY_SHA256.items():
        _require(authority_hashes[field] == expected, f"artifact authority SHA mismatch: {field}")
    _strict_sha(evaluator_sha256, "evaluator")
    _require(
        authority_hashes["economics_tool_sha256"] == evaluator_sha256,
        "evaluator SHA does not match artifact authority",
    )


def _artifact_prefix(
    trade_payload: bytes,
    metrics_payload: bytes,
    yearly_payload: bytes,
    dsr_payload: bytes,
    gate_payload: bytes,
) -> dict[str, bytes]:
    return {
        REQUIRED_ARTIFACTS[0]: trade_payload,
        REQUIRED_ARTIFACTS[1]: metrics_payload,
        REQUIRED_ARTIFACTS[2]: yearly_payload,
        REQUIRED_ARTIFACTS[3]: dsr_payload,
        REQUIRED_ARTIFACTS[4]: gate_payload,
    }


def _finish_artifacts(
    prefix: dict[str, bytes],
    *,
    authority_hashes: dict[str, str],
    evaluator_sha256: str,
    engineering_status: str,
    verdict: str,
    market_verdict: str | None,
    evaluated_trades: int,
    error_code: str | None,
) -> dict[str, bytes]:
    _validate_authority(authority_hashes, evaluator_sha256)
    artifact_hashes = {name: sha256_bytes(payload) for name, payload in prefix.items()}
    receipt = {
        "schema_version": "trendstack_007_design_economics_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "authority_sha256": dict(authority_hashes),
        "evaluator_sha256": evaluator_sha256,
        "artifact_sha256": artifact_hashes,
        "engineering_status": engineering_status,
        "evaluated_trades": evaluated_trades,
        "verdict": verdict,
        "market_verdict": market_verdict,
        "error_code": error_code,
        "research_validation_opened": False,
        "research_holdout_opened": False,
        "promotion_authorized": False,
    }
    receipt_payload = canonical_json_bytes(receipt) + b"\n"
    terminal = {
        "schema_version": "trendstack_007_design_economics_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "engineering_status": engineering_status,
        "verdict": verdict,
        "market_verdict": market_verdict,
        "error_code": error_code,
        "design_economics_receipt_sha256": sha256_bytes(receipt_payload),
        "evaluated_trades": evaluated_trades,
        "research_validation_opened": False,
        "research_holdout_opened": False,
        "promotion_authorized": False,
    }
    result = dict(prefix)
    result[REQUIRED_ARTIFACTS[5]] = receipt_payload
    result[REQUIRED_ARTIFACTS[6]] = canonical_json_bytes(terminal) + b"\n"
    _require(tuple(result) == REQUIRED_ARTIFACTS, "artifact set/order mismatch")
    return result


def build_artifacts(
    evaluation: dict[str, Any],
    *,
    authority_hashes: dict[str, str],
    evaluator_sha256: str,
) -> dict[str, bytes]:
    _require(type(evaluation) is dict and evaluation.get("engineering_status") == "PASS", "evaluation is not engineering-valid")
    trade_rows = evaluation.get("trade_rows")
    _require(type(trade_rows) is list and len(trade_rows) == EXPECTED_TOTAL_TRADES, "trade ledger count mismatch")
    trade_payload = b"".join(canonical_json_bytes(row) + b"\n" for row in trade_rows)
    metrics_payload = canonical_json_bytes({
        "schema_version": "trendstack_007_design_arm_cost_metrics.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "arm_metrics": evaluation["arm_metrics"],
    }) + b"\n"
    yearly_payload = canonical_json_bytes({
        "schema_version": "trendstack_007_design_yearly_metrics.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        **evaluation["yearly_metrics"],
    }) + b"\n"
    dsr_payload = canonical_json_bytes({
        "schema_version": "trendstack_007_design_dsr_inputs.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        **evaluation["dsr_inputs"],
    }) + b"\n"
    gate_payload = canonical_json_bytes({
        **evaluation["gate_report"],
        "hypothesis_id": HYPOTHESIS_ID,
        "gate_values": evaluation["gate_values"],
        "verdict": evaluation["verdict"],
    }) + b"\n"
    prefix = _artifact_prefix(
        trade_payload, metrics_payload, yearly_payload, dsr_payload, gate_payload
    )
    return _finish_artifacts(
        prefix,
        authority_hashes=authority_hashes,
        evaluator_sha256=evaluator_sha256,
        engineering_status="PASS",
        verdict=evaluation["verdict"],
        market_verdict=evaluation["verdict"],
        evaluated_trades=len(trade_rows),
        error_code=None,
    )


def engineering_invalid_artifacts(
    error_code: str,
    *,
    authority_hashes: dict[str, str],
    evaluator_sha256: str,
) -> dict[str, bytes]:
    _require(type(error_code) is str and error_code and error_code.replace("_", "").isalnum(), "engineering error code malformed")
    invalid = {
        "schema_version": "trendstack_007_design_economics_invalid.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "engineering_status": "INVALID",
        "error_code": error_code,
        "market_verdict": None,
    }
    prefix = _artifact_prefix(
        b"",
        canonical_json_bytes({**invalid, "arm_metrics": None}) + b"\n",
        canonical_json_bytes({**invalid, "yearly_metrics": None}) + b"\n",
        canonical_json_bytes({**invalid, "dsr_inputs": None}) + b"\n",
        canonical_json_bytes({**invalid, "gates": None, "all_pass": None}) + b"\n",
    )
    return _finish_artifacts(
        prefix,
        authority_hashes=authority_hashes,
        evaluator_sha256=evaluator_sha256,
        engineering_status="INVALID",
        verdict="ENGINEERING_INVALID_NO_MARKET_VERDICT",
        market_verdict=None,
        evaluated_trades=0,
        error_code=error_code,
    )


def attempt_started_payload(packet: dict[str, Any], run_packet_sha256: str) -> bytes:
    _validate_run_packet_values(packet)
    started = {
        "schema_version": "trendstack_007_design_economics_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "projection_attempt_id": packet["projection_attempt_id"],
        "attempt_state": "ATTEMPT_STARTED",
        "run_packet_sha256": _strict_sha(run_packet_sha256, "run packet"),
        "implementation_task_v1_sha256": IMPLEMENTATION_TASK_SHA256,
        "implementation_task_v2_sha256": IMPLEMENTATION_TASK_V2_SHA256,
        "implementation_task_v3_sha256": IMPLEMENTATION_TASK_V3_SHA256,
        "implementation_task_v4_sha256": IMPLEMENTATION_TASK_V4_SHA256,
        "implementation_task_v5_sha256": IMPLEMENTATION_TASK_V5_SHA256,
        "implementation_task_v6_sha256": IMPLEMENTATION_TASK_V6_SHA256,
        "attempt_001_terminal_sha256": packet["attempt_001_terminal_sha256"],
        "attempt_001_design_economics_receipt_sha256": packet[
            "attempt_001_design_economics_receipt_sha256"
        ],
        "attempt_002_terminal_sha256": packet["attempt_002_terminal_sha256"],
        "attempt_002_design_economics_receipt_sha256": packet[
            "attempt_002_design_economics_receipt_sha256"
        ],
        "attempt_003_terminal_sha256": packet["attempt_003_terminal_sha256"],
        "attempt_003_design_economics_receipt_sha256": packet[
            "attempt_003_design_economics_receipt_sha256"
        ],
        "economics_tool_sha256": packet["economics_tool_sha256"],
        "economics_tool_test_sha256": packet["economics_tool_test_sha256"],
        "input_contract_preflight_receipt_sha256": packet[
            "input_contract_preflight_receipt_sha256"
        ],
        "implementation_review_receipt_sha256": packet["implementation_review_receipt_sha256"],
        "production_input_opened": False,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }
    return canonical_json_bytes(started) + b"\n"


INPUT_BUNDLE_FIELDS = {
    "source_manifest", "source_rows_by_date", "stage0_ledger",
    "decision_manifest", "decision_packets_by_date", "dsr_callable",
}


def _stage_error_code(stage: str, error: Exception) -> str:
    _require(stage in {"LOAD", "EVALUATION", "ARTIFACT_PREP"}, "unknown attempt stage")
    suffix = "INVALID_ENGINEERING" if isinstance(error, InvalidEngineering) else "UNEXPECTED_EXCEPTION"
    return f"{stage}_{suffix}"


def _stage_invalid_artifacts(
    stage: str,
    error: Exception,
    *,
    authority_hashes: dict[str, str],
    evaluator_sha256: str,
) -> dict[str, bytes]:
    return engineering_invalid_artifacts(
        _stage_error_code(stage, error),
        authority_hashes=authority_hashes,
        evaluator_sha256=evaluator_sha256,
    )


def execute_validated_packet(
    packet: dict[str, Any],
    run_packet_sha256: str,
    *,
    verify_authority: Callable[[dict[str, Any]], Any],
    begin_attempt: Callable[[dict[str, Any], str, bytes], None],
    load_inputs: Callable[[dict[str, Any], Any], dict[str, Any]],
    finish_attempt: Callable[[dict[str, Any], dict[str, bytes]], None],
) -> dict[str, Any]:
    """Execute exactly once through injected, reviewable lifecycle boundaries."""

    _validate_run_packet_values(packet)
    observed_run_sha = _strict_sha(run_packet_sha256, "run packet")
    _require(callable(verify_authority), "authority verifier missing")
    _require(callable(begin_attempt), "attempt starter missing")
    _require(callable(load_inputs), "input loader missing")
    _require(callable(finish_attempt), "attempt finisher missing")
    authority_context = verify_authority(packet)
    authority_hashes = artifact_authority_from_packet(packet, observed_run_sha)
    begin_attempt(packet, observed_run_sha, attempt_started_payload(packet, observed_run_sha))
    evaluator_sha256 = packet["economics_tool_sha256"]
    try:
        bundle = load_inputs(packet, authority_context)
        _require(type(bundle) is dict and set(bundle) == INPUT_BUNDLE_FIELDS, "input bundle schema mismatch")
    except Exception as error:
        artifacts = _stage_invalid_artifacts(
            "LOAD", error,
            authority_hashes=authority_hashes,
            evaluator_sha256=evaluator_sha256,
        )
    else:
        try:
            evaluation = evaluate_design(
                bundle["source_manifest"], bundle["source_rows_by_date"],
                bundle["stage0_ledger"], bundle["decision_manifest"],
                bundle["decision_packets_by_date"], dsr_callable=bundle["dsr_callable"],
            )
        except Exception as error:
            artifacts = _stage_invalid_artifacts(
                "EVALUATION", error,
                authority_hashes=authority_hashes,
                evaluator_sha256=evaluator_sha256,
            )
        else:
            try:
                artifacts = build_artifacts(
                    evaluation,
                    authority_hashes=authority_hashes,
                    evaluator_sha256=evaluator_sha256,
                )
            except Exception as error:
                artifacts = _stage_invalid_artifacts(
                    "ARTIFACT_PREP", error,
                    authority_hashes=authority_hashes,
                    evaluator_sha256=evaluator_sha256,
                )
    finish_attempt(packet, artifacts)
    terminal = json.loads(artifacts["attempt_terminal.json"].decode("utf-8"))
    _require(type(terminal) is dict, "terminal artifact malformed")
    return terminal


def persist_artifacts(output_root: Path | str, artifacts: dict[str, bytes]) -> None:
    _require(type(artifacts) is dict and tuple(artifacts) == REQUIRED_ARTIFACTS, "artifact set/order mismatch")
    _require(all(type(payload) is bytes for payload in artifacts.values()), "artifact payload malformed")
    root = Path(output_root).absolute()
    try:
        root.mkdir(parents=False, exist_ok=False)
        for name in REQUIRED_ARTIFACTS:
            with (root / name).open("xb") as handle:
                handle.write(artifacts[name])
                handle.flush()
                os.fsync(handle.fileno())
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING artifact output must be create-new") from exc


def _write_new_fsynced(path: Path, payload: bytes) -> None:
    _require(type(payload) is bytes, "output payload malformed")
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING create-new output write failed") from exc


def begin_production_attempt(
    packet: dict[str, Any],
    run_packet_sha256: str,
    payload: bytes,
    *,
    workspace_root: Path | str = ".",
) -> None:
    _validate_run_packet_values(packet)
    root = Path(workspace_root).resolve(strict=True)
    output = _workspace_path(root, packet["output_root"], must_exist=False)
    expected = attempt_started_payload(packet, run_packet_sha256)
    _require(payload == expected, "attempt-start payload mismatch")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING output root must be absent") from exc
    _write_new_fsynced(output / "attempt_started.json", payload)


def finish_production_attempt(
    packet: dict[str, Any],
    artifacts: dict[str, bytes],
    *,
    workspace_root: Path | str = ".",
) -> None:
    _validate_run_packet_values(packet)
    _require(type(artifacts) is dict and tuple(artifacts) == REQUIRED_ARTIFACTS, "artifact set/order mismatch")
    root = Path(workspace_root).resolve(strict=True)
    output = _workspace_path(root, packet["output_root"], must_exist=True)
    _require(output.is_dir() and not output.is_symlink(), "attempt output root malformed")
    try:
        existing = {entry.name for entry in os.scandir(output)}
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING attempt output cannot be scanned") from exc
    _require(existing == {"attempt_started.json"}, "attempt output contains unexpected entries")
    for name in REQUIRED_ARTIFACTS:
        _write_new_fsynced(output / name, artifacts[name])


def run_reviewed_packet(
    run_packet_path: Path | str,
    workspace_root: Path | str = ".",
) -> dict[str, Any]:
    root = Path(workspace_root).resolve(strict=True)
    expected_packet_path = _workspace_path(root, RUN_PACKET_PATH, must_exist=True)
    candidate = Path(run_packet_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        observed_packet_path = candidate.resolve(strict=True)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING reviewed run packet path unreadable") from exc
    _require(observed_packet_path == expected_packet_path, "reviewed run packet path drift")
    packet, run_packet_sha256 = read_run_packet(expected_packet_path, root)
    return execute_validated_packet(
        packet,
        run_packet_sha256,
        verify_authority=lambda observed: verify_production_authority(observed, root),
        begin_attempt=lambda observed, digest, payload: begin_production_attempt(
            observed, digest, payload, workspace_root=root
        ),
        load_inputs=load_production_inputs,
        finish_attempt=lambda observed, artifacts: finish_production_attempt(
            observed, artifacts, workspace_root=root
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reviewed-run-packet",
        type=Path,
        required=True,
        help="Canonical V3-bound packet approved for the single DESIGN economics attempt.",
    )
    args = parser.parse_args(argv)
    try:
        terminal = run_reviewed_packet(args.reviewed_run_packet)
    except InvalidEngineering as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(canonical_json_bytes(terminal).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
