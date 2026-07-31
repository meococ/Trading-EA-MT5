#!/usr/bin/env python3
"""Validate the generic AlphaFactory append-only hypothesis registry."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema

# Rows updated from this instant on must satisfy the probe-prereg rules below;
# earlier rows are grandfathered (append-only history cannot be rewritten).
PROBE_PREREG_ENFORCEMENT_START = datetime(2026, 7, 18, tzinfo=timezone.utc)


RESEARCH_DIR = Path(__file__).resolve().parent
WORKSPACE = RESEARCH_DIR.parents[1]
DEFAULT_REGISTRY = RESEARCH_DIR / "CANDIDATE_REGISTRY.jsonl"
DEFAULT_SCHEMA = RESEARCH_DIR / "CANDIDATE_REGISTRY.schema.json"
EXECUTION_STATES = {"screened", "challenger", "confirmed", "portfolio-sleeve"}
MODEL4_DATA_ACQUISITION_AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
HYP005_MODEL4_COLLECTION_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-005"
TERMINAL_STATES = {"parked", "killed"}
TRANSITIONS = {
    "idea": {"probe", "screened", "parked", "killed"},
    "probe": {"screened", "parked", "killed"},
    "screened": {"challenger", "parked", "killed"},
    "challenger": {"confirmed", "parked", "killed"},
    "confirmed": {"portfolio-sleeve", "parked", "killed"},
    "portfolio-sleeve": {"parked", "killed"},
    "parked": set(),
    "killed": set(),
}
HYP007_ID = "HYP-TRENDSTACK-EURUSD-H1-007"
HYP007_PRIOR_ROW_INDEX = 285
HYP007_PRIOR_ROW_SHA256 = "6D72D93644BF6C61D3D966013348FF272F3A78D13DE7444CB245A6809EB722DA"
HYP007_AMENDMENT_V2_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_AMENDMENT_V2.json"
HYP007_AMENDMENT_V2_SHA256 = "F399FF28A3ADCE35FD13111EC9EA6F3C33269415379F365BEFCC58F0319F3FFD"
HYP007_AMENDMENT_V3_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_AMENDMENT_V3.json"
HYP007_AMENDMENT_V3_SHA256 = "FA8F5A7E65C0D54E3BE20802BEC096528C1BD424961D1C615491CAF63E90C8AE"
HYP007_TASK_V5_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V5.json"
HYP007_TASK_V5_SHA256 = "E572E49FDE06717C396112FBD7D0278C0F59605369651825447C1913D241B725"
HYP007_AUTHORIZED_ROW_INDEX = 286
HYP007_AUTHORIZED_ROW_SHA256 = "17512FE256454130E3EAE26D2372818631487D67EEB0F8B414D255FE2D5CA06E"
HYP007_REPAIR_AMENDMENT_V4_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_RUN_AUTHORITY_REPAIR_AMENDMENT_V4.json"
HYP007_REPAIR_AMENDMENT_V4_SHA256 = "3B9FB4C9D4469FBF612195C33FAF6771299DAC277D07CD3EA124F2C98989DBA8"
HYP007_TASK_V6_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_TASK_PACKET_V6.json"
HYP007_TASK_V6_SHA256 = "6CB1024E30A620D33A66D678AC7A24ECE2F3872F98E1F0F4FE8D2E23AE7EC892"
HYP007_RECEIPT_V5_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT_V5.json"
HYP007_RECEIPT_V6_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-007_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT_V6.json"
HYP007_ALLOWED_ROOT_CHANGES = {"reason", "updated_at_utc", "validation", "verdict"}
HYP007_ALLOWED_VALIDATION_CHANGES = {"probe_status", "source_run_authorized", "source_run_bindings"}
HYP007_REPAIR_ALLOWED_VALIDATION_CHANGES = {"probe_status", "source_run_bindings"}
SOURCE_ONLY_ALLOWED_ROOT_CHANGES = {"reason", "updated_at_utc", "validation", "verdict"}
SOURCE_ONLY_ALLOWED_VALIDATION_ADDITIONS = {
    "independent_implementation_review_status",
    "independent_pre_run_review_status",
    "independent_quant_prereg_review_status",
    "independent_review_receipt_path",
    "independent_review_receipt_schema",
    "independent_review_receipt_sha256",
    "reviewed_builder_base_sha256",
    "reviewed_builder_path",
    "reviewed_test_path",
    "reviewed_test_sha256",
    "source_feasibility_attempt_id",
    "source_feasibility_evidence_root",
}
SOURCE_ONLY_ALLOWED_VALIDATION_CHANGES = {
    "probe_status",
    "source_build_authorized",
    "source_run_authorized",
} | SOURCE_ONLY_ALLOWED_VALIDATION_ADDITIONS
SOURCE_ONLY_REQUIRED_REVIEW_STATUS = {
    "independent_implementation_review_status": "PASS",
    "independent_pre_run_review_status": "PASS",
    "independent_quant_prereg_review_status": "PASS",
}
SOURCE_ONLY_FALSE_FIELDS = {
    "economics_authorized",
    "model0_authorized",
    "model4_authorized",
    "mql5_authorized",
    "mt5_authorized",
    "network_authorized",
    "paid_requests_authorized",
    "performance_metrics_authorized",
    "post_entry_price_projection_authorized",
    "promotion_eligible",
    "research_holdout_access_authorized",
    "research_validation_access_authorized",
}
SOURCE_ONLY_ZERO_METRICS = {
    "source_feasibility_attempts_consumed": 0,
    "source_runs_executed": 0,
    "post_entry_ohlc_rows_read": 0,
    "outcome_fields_emitted": 0,
    "returns_computed": 0,
    "trades_simulated": 0,
    "performance_trials_executed": 0,
    "economics_executed": False,
    "model0_runs": 0,
    "model4_runs": 0,
    "mt5_launches": 0,
    "mql5_files_created": 0,
    "research_validation_opened": False,
    "research_holdout_opened": False,
    "paid_requests_made": 0,
    "network_calls": 0,
}
SOURCE_ONLY_COMPLETION_ALLOWED_ROOT_CHANGES = {
    "metrics",
    "reason",
    "run_ids",
    "updated_at_utc",
    "validation",
    "verdict",
}
SOURCE_ONLY_COMPLETION_ALLOWED_VALIDATION_ADDITIONS = {
    "attempt_started_path",
    "attempt_started_sha256",
    "attempt_terminal_path",
    "attempt_terminal_sha256",
    "economic_edge_evaluated",
    "market_no_edge_claim_authorized",
    "source_feasibility_receipt_path",
    "source_feasibility_receipt_sha256",
    "source_feasibility_result_valid",
    "source_feasibility_verdict",
    "source_ledger_path",
    "source_ledger_sha256",
    "source_report_path",
    "source_report_sha256",
}
HYP007_REPAIR_BINDING_CHANGES = {
    "implementation_review_receipt_path",
    "implementation_review_receipt_sha256",
    "implementation_task_path",
    "implementation_task_sha256",
    "supervisor_review_base_sha256",
    "supervisor_test_sha256",
}
G10_XMOM_HYP002_ID = "HYP-G10-XMOM-W1-002"
G10_XMOM_EXPORT_ATTEMPT_ID = "G10XMOM002-TRAIN-EXPORT-001"
G10_XMOM_EXPORT_TO_EVAL_ROOT_CHANGES = {
    "metrics",
    "reason",
    "run_ids",
    "updated_at_utc",
    "validation",
    "verdict",
}
G10_XMOM_EXPORT_TO_EVAL_VALIDATION_CHANGES = {
    "economics_authorized",
    "independent_review_receipt_path",
    "independent_review_receipt_sha256",
    "mt5_authorized",
    "performance_metrics_authorized",
    "probe_status",
    "reviewed_test_path",
    "reviewed_test_sha256",
    "train_acquisition_authorized",
    "train_economics_authorized",
    "train_export_authorized",
    "train_price_data_acquisition_authorized",
    "train_source_run_authorized",
}
G10_XMOM_EXPORT_TO_EVAL_VALIDATION_ADDITIONS = {
    "dataset_manifest_path",
    "dataset_manifest_sha256",
    "dataset_parquet_path",
    "dataset_parquet_sha256",
    "dataset_row_count",
    "train_evaluate_authorized",
    "train_eval_attempt_id",
    "train_eval_evidence_root",
    "train_export_receipt_path",
    "train_export_receipt_sha256",
}
TRILAG_HYP002_ID = "HYP-TRILAG-EURJPY-M1-002"
TRILAG_EXPORT_ATTEMPT_ID = "TRILAG002-DESIGN-EXPORT-001"
TRILAG_REGISTRY_VALIDATOR_PATH = "04. Memory/research/validate_candidate_registry.py"
TRILAG_REGISTRY_VALIDATOR_SHA256 = "5B9C1CAE78FB7C4AAC5822AE17FE1AC127442E942D7F2668CF2EAB00538E2C1E"
TRILAG_EXPORT_TO_STRUCTURE_ROOT_CHANGES = {
    "metrics",
    "reason",
    "run_ids",
    "source_provenance",
    "updated_at_utc",
    "validation",
    "verdict",
}
TRILAG_EXPORT_TO_STRUCTURE_VALIDATION_CHANGES = {
    "design_export_run_authorized",
    "design_structure_evaluation_authorized",
    "mt5_authorized",
    "mt5_scope",
    "probe_status",
    "registry_validator_sha256",
}
TRILAG_EXPORT_TO_STRUCTURE_VALIDATION_ADDITIONS = {
    "dataset_manifest_path",
    "dataset_manifest_sha256",
    "dataset_parquet_path",
    "dataset_parquet_sha256",
    "dataset_row_count",
    "design_export_attempt_started_path",
    "design_export_attempt_started_sha256",
    "design_export_receipt_path",
    "design_export_receipt_sha256",
    "design_export_reconciliation_receipt_path",
    "design_export_reconciliation_receipt_sha256",
    "design_structure_evidence_root",
}
ROUND_HYP001_ID = "HYP-ROUND-CASCADE-EURUSD-M5-001"
ROUND_HYP001_TERMINAL_PRIOR_LINE = 293
ROUND_HYP001_TERMINAL_PRIOR_SHA256 = "C7ED7E262F48CBA68D5B6BA9C6F09CAA291C0B959FA2CE3CE4DE305A3F889DA2"
ROUND_HYP001_TERMINAL_RECONCILIATION_LINE = 294
ROUND_HYP001_TERMINAL_RECONCILIATION_SHA256 = "788F58A7CB2762E73AE2D7BBF2370FE8830F0C216B5115B1697A2F1EC9DCC873"
SOURCE_RUN_EXISTING_FILE_BINDINGS = (
    ("active_contract_bundle_path", "active_contract_bundle_sha256"),
    ("authority_amendment_path", "authority_amendment_sha256"),
    ("implementation_review_receipt_path", "implementation_review_receipt_sha256"),
    ("implementation_task_path", "implementation_task_sha256"),
    ("projector_test_path", "projector_test_sha256"),
    ("projector_tool_path", "projector_tool_sha256"),
    ("public_manifest_path", "public_manifest_sha256"),
    ("public_receipt_path", "public_receipt_sha256"),
    ("selection_manifest_path", "selection_manifest_sha256"),
    ("supervisor_test_path", "supervisor_test_sha256"),
    ("validator_test_path", "validator_test_sha256"),
    ("validator_tool_path", "validator_tool_sha256"),
)


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_workspace_path(raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw:
        errors.append(f"{label}: path must be a non-empty string")
        return None
    pure = PurePosixPath(raw)
    if (
        Path(raw).is_absolute()
        or pure.is_absolute()
        or ":" in raw
        or "\\" in raw
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != raw
    ):
        errors.append(f"{label}: path must be normalized workspace-relative POSIX: {raw}")
        return None
    candidate = (WORKSPACE / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(WORKSPACE.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes workspace: {raw}")
        return None
    return candidate


def resolve_workspace_path(raw: Any, label: str, errors: list[str]) -> Path | None:
    candidate = normalized_workspace_path(raw, label, errors)
    if candidate is None:
        return None
    if not candidate.is_file():
        errors.append(f"{label}: file is missing: {raw}")
        return None
    return candidate


def verify_binding(path_value: Any, hash_value: Any, label: str, errors: list[str]) -> Path | None:
    if path_value is None and hash_value is None:
        return None
    if path_value is None or hash_value is None:
        errors.append(f"{label}: path and SHA256 must be supplied together")
        return None
    path = resolve_workspace_path(path_value, label, errors)
    if path is None:
        return None
    if not isinstance(hash_value, str) or re.fullmatch(r"[A-Fa-f0-9]{64}", hash_value) is None:
        errors.append(f"{label}: SHA256 is invalid")
        return None
    actual = sha256_file(path)
    if actual != hash_value.upper():
        errors.append(f"{label}: SHA256 mismatch expected={hash_value.upper()} actual={actual}")
        return None
    return path


def verify_recorded_binding_shape(
    item: Any,
    label: str,
    errors: list[str],
) -> None:
    """Validate an immutable recorded path/SHA pair without rehashing mutable code."""
    if not isinstance(item, dict):
        errors.append(f"{label}: binding must be an object")
        return
    normalized_workspace_path(item.get("path"), label, errors)
    sha256 = item.get("sha256")
    if not isinstance(sha256, str) or re.fullmatch(r"[A-F0-9]{64}", sha256) is None:
        errors.append(f"{label}: recorded SHA256 must be uppercase hexadecimal")


def verify_source_binding(
    row: dict[str, Any],
    label: str,
    errors: list[str],
    terminal_snapshot: dict[str, Any] | None,
) -> Path | None:
    source_path = row.get("source_path")
    source_hash = row.get("source_hash")
    if source_path is None and source_hash is None:
        return None
    if source_path is None or source_hash is None:
        errors.append(f"{label}: path and SHA256 must be supplied together")
        return None
    source_file = resolve_workspace_path(source_path, label, errors)
    if source_file is None:
        return None
    if not isinstance(source_hash, str) or re.fullmatch(r"[A-Fa-f0-9]{64}", source_hash) is None:
        errors.append(f"{label}: SHA256 is invalid")
        return None
    expected_hash = source_hash.upper()
    actual_hash = sha256_file(source_file)
    if actual_hash == expected_hash:
        return source_file

    # An append-only terminal hypothesis may outlive a changing canonical EA.
    # Its latest terminal row must explicitly bind an immutable package-local
    # source snapshot. Active hypotheses never receive this fallback.
    if terminal_snapshot is not None:
        ea_name = str(row.get("ea_name") or "")
        snapshot_path = terminal_snapshot.get("source_snapshot_path")
        snapshot_hash = terminal_snapshot.get("source_snapshot_sha256")
        expected_prefix = f"03. EA Developer/{ea_name}/research/source_snapshots/"
        if isinstance(snapshot_path, str) and snapshot_path.startswith(expected_prefix):
            snapshot_file = verify_binding(snapshot_path, snapshot_hash, f"{label} terminal snapshot", errors)
            if snapshot_file is not None:
                if str(snapshot_hash).upper() != expected_hash:
                    errors.append(f"{label}: terminal snapshot SHA256 does not match frozen source_hash")
                else:
                    return snapshot_file
        else:
            errors.append(
                f"{label}: stale terminal source requires source_snapshot_path inside '{expected_prefix}'"
            )

    errors.append(f"{label}: SHA256 mismatch expected={expected_hash} actual={actual_hash}")
    return None


def validate_row_bindings(
    row: dict[str, Any],
    line: int,
    errors: list[str],
    terminal_snapshot: dict[str, Any] | None = None,
) -> None:
    label = f"line {line} {row.get('hypothesis_id', '<unknown>')}"
    ea_name = str(row.get("ea_name") or "")
    expected_source = f"03. EA Developer/{ea_name}/{ea_name}.mq5"
    source_path = row.get("source_path")
    prereg_path = row.get("prereg_path")

    if source_path is not None and source_path != expected_source:
        expected_snapshot_prefix = f"03. EA Developer/{ea_name}/research/source_snapshots/"
        if terminal_snapshot is None or not str(source_path).startswith(expected_snapshot_prefix):
            errors.append(f"{label}: source_path must be canonical '{expected_source}'")
    source_file = verify_source_binding(row, f"{label} source", errors, terminal_snapshot)
    prereg_file = verify_binding(prereg_path, row.get("prereg_sha256"), f"{label} prereg", errors)
    if prereg_path is not None:
        expected_prefix = f"03. EA Developer/{ea_name}/research/"
        if not str(prereg_path).startswith(expected_prefix):
            errors.append(f"{label}: prereg_path must be inside '{expected_prefix}'")
    if row.get("state") in EXECUTION_STATES:
        validation = row.get("validation")
        if (
            isinstance(validation, dict)
            and validation.get("authority") == MODEL4_DATA_ACQUISITION_AUTHORITY
            and row.get("model") != 4
        ):
            errors.append(
                f"{label}: authority {MODEL4_DATA_ACQUISITION_AUTHORITY} requires Model 4"
            )
        if row.get("model") == 4:
            model4_required = {
                "authority": MODEL4_DATA_ACQUISITION_AUTHORITY,
                "performance_metrics_authorized": False,
                "economics_authorized": False,
                "model4_data_acquisition_authorized": True,
                "model4_performance_authorized": False,
                "promotion_eligible": False,
                "paper_trading_authorized": False,
                "live_trading_authorized": False,
            }
            if not isinstance(validation, dict):
                errors.append(f"{label}: Model 4 execution requires validation authority gates")
            else:
                for key, expected in model4_required.items():
                    if validation.get(key) != expected:
                        errors.append(
                            f"{label}: Model 4 data acquisition requires validation.{key}={expected!r}"
                        )
        elif row.get("model") != 0:
            errors.append(f"{label}: execution state requires Model 0")
        if source_file is None or prereg_file is None:
            errors.append(f"{label}: execution state requires hash-bound canonical source and prereg")
    if row.get("state") == "probe":
        try:
            row_ts = datetime.fromisoformat(str(row["updated_at_utc"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            row_ts = None
        if (
            row_ts is not None
            and row_ts >= PROBE_PREREG_ENFORCEMENT_START
            and (row.get("prereg_path") is None or row.get("prereg_sha256") is None)
        ):
            errors.append(
                f"{label}: probe state requires a SHA-bound frozen plan (PROBE_PLAN/prereg) "
                f"from {PROBE_PREREG_ENFORCEMENT_START.date()}"
            )
    if row.get("updated_at_utc") and not str(row["updated_at_utc"]).endswith("Z"):
        errors.append(f"{label}: updated_at_utc must use a Z timestamp")
    try:
        start = datetime.strptime(str(row["window"]["from"]), "%Y.%m.%d")
        end = datetime.strptime(str(row["window"]["to"]), "%Y.%m.%d")
        if start >= end:
            errors.append(f"{label}: window.from must be earlier than window.to")
    except (KeyError, TypeError, ValueError):
        pass
    acceptance = row.get("acceptance_contract")
    if isinstance(acceptance, dict):
        minimum = acceptance.get("min_trades_per_week")
        maximum = acceptance.get("max_trades_per_week")
        if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)) and minimum > maximum:
            errors.append(f"{label}: acceptance_contract min_trades_per_week exceeds max_trades_per_week")


def _terminal_snapshot_amendment_errors(
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} terminal snapshot amendment"
    errors: list[str] = []
    if prior.get("state") not in TERMINAL_STATES or row.get("state") != prior.get("state"):
        return [f"{label}: transition must preserve the terminal state"]
    allowed_top_level_changes = {"updated_at_utc", "reason", "validation"}
    for key in set(prior) | set(row):
        if key in allowed_top_level_changes:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")
    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    if added != {"source_snapshot_path", "source_snapshot_sha256"} or removed:
        errors.append(
            f"{label}: only source_snapshot_path/source_snapshot_sha256 may be added"
        )
    for key, value in prior_validation.items():
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")
    expected_prefix = (
        f"03. EA Developer/{row.get('ea_name')}/research/source_snapshots/"
    )
    snapshot_path = validation.get("source_snapshot_path")
    snapshot_sha = validation.get("source_snapshot_sha256")
    if not isinstance(snapshot_path, str) or not snapshot_path.startswith(expected_prefix):
        errors.append(f"{label}: source snapshot path must be inside {expected_prefix!r}")
    if snapshot_sha != row.get("source_hash"):
        errors.append(f"{label}: source snapshot SHA must equal frozen source_hash")
    snapshot = verify_binding(
        snapshot_path,
        snapshot_sha,
        f"{label} source snapshot",
        errors,
    )
    if snapshot is None:
        errors.append(f"{label}: immutable source snapshot is not valid")
    if "immutable terminal source snapshot" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify the immutable terminal source snapshot")
    return errors


def _prelaunch_evidence_correction_errors(
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} prelaunch evidence correction"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")
    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    expected_added = {
        "engineering_receipt_correction_path",
        "engineering_receipt_correction_sha256",
    }
    if added != expected_added or removed:
        errors.append(
            f"{label}: only engineering receipt correction path/SHA may be added"
        )
    for key, value in prior_validation.items():
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")
    correction_path = validation.get("engineering_receipt_correction_path")
    correction_sha = validation.get("engineering_receipt_correction_sha256")
    expected_prefix = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
    )
    if not isinstance(correction_path, str) or not correction_path.startswith(expected_prefix):
        errors.append(f"{label}: correction path must be inside {expected_prefix!r}")
    correction_file = verify_binding(
        correction_path,
        correction_sha,
        f"{label} correction artifact",
        errors,
    )
    if correction_file is not None:
        try:
            correction = load_strict_json(correction_file)
        except Exception as exc:
            errors.append(f"{label}: correction artifact invalid JSON: {exc}")
            correction = None
        if isinstance(correction, dict):
            original = correction.get("original_receipt")
            exposure = correction.get("exposure_readback")
            if (
                correction.get("hypothesis_id") != hypothesis_id
                or correction.get("classification")
                != "PRELAUNCH_EVIDENCE_METADATA_CORRECTION"
                or not isinstance(original, dict)
                or not isinstance(exposure, dict)
                or original.get("path") != prior_validation.get("engineering_receipt_path")
                or original.get("sha256")
                != prior_validation.get("engineering_receipt_sha256")
                or exposure.get("hyp005_execution_receipts") != 0
                or exposure.get("economic_trials_consumed") != 0
            ):
                errors.append(f"{label}: correction artifact identity/exposure mismatch")
    runtime = WORKSPACE / "02. AlphaFactory/runtime"
    if runtime.is_dir():
        for receipt in runtime.glob("ea_execution_receipt_*.json"):
            try:
                if hypothesis_id in receipt.read_text(encoding="utf-8-sig"):
                    errors.append(
                        f"{label}: execution receipt already exists before correction: {receipt.name}"
                    )
            except OSError:
                continue
    if "prelaunch evidence metadata correction" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify the prelaunch evidence metadata correction")
    return errors


def _prelaunch_packet_authorization_errors(
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} prelaunch packet authorization"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    expected_added = {
        "campaign_data_repair_row_sha256",
        "prepacket_control_plane_receipt_path",
        "prepacket_control_plane_receipt_sha256",
    }
    if added != expected_added or removed:
        errors.append(
            f"{label}: added validation fields must be exactly campaign row and prepacket receipt bindings"
        )
    allowed_changed = {
        "probe_status",
        "campaign_prebinding_status",
        "task_packet_authorized_next",
        "required_journal_marker_case_sensitive",
        "packet_builder_wrapper_sha256",
        "packet_builder_core_sha256",
        "ledger_appender_core_sha256",
        "packet_rebind_core_sha256",
        "journal_parser_sha256",
        "data_epoch_validator_sha256",
        "runner_engine_sha256",
        "bound_tests",
    } | expected_added
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    required_changed = {
        "probe_status",
        "campaign_prebinding_status",
        "task_packet_authorized_next",
        "required_journal_marker_case_sensitive",
        "packet_builder_wrapper_sha256",
        "packet_builder_core_sha256",
        "ledger_appender_core_sha256",
        "packet_rebind_core_sha256",
        "journal_parser_sha256",
        "data_epoch_validator_sha256",
        "runner_engine_sha256",
        "bound_tests",
    } | expected_added
    if changed - allowed_changed:
        errors.append(
            f"{label}: prohibited validation changes {sorted(changed - allowed_changed)}"
        )
    if not required_changed.issubset(changed):
        errors.append(
            f"{label}: required packet-authority changes are missing "
            f"{sorted(required_changed - changed)}"
        )
    if (
        validation.get("probe_status") != "SCREENED_PRELAUNCH_PACKET_AUTHORIZED"
        or validation.get("campaign_prebinding_status") != "BOUND_DATA_REPAIR"
        or validation.get("task_packet_authorized_next") is not True
        or validation.get("required_journal_marker_case_sensitive") is not True
    ):
        errors.append(f"{label}: packet authority state is not exact")
    for flag in (
        "mt5_authorized",
        "model4_authorized",
        "trading_backtest_authorized",
        "trades_authorized",
        "performance_metrics_authorized",
        "economics_authorized",
        "optimization_authorized",
        "validation_access_authorized",
        "holdout_access_authorized",
        "promotion_eligible",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
        "task_packets_created",
    ):
        if validation.get(flag) is not False:
            errors.append(f"{label}: unsafe authority flag {flag!r} must remain false")

    campaign_records = (
        WORKSPACE / "04. Memory/research/CAMPAIGN_EXPOSURE.jsonl"
    ).read_bytes().splitlines()
    campaign_sha = (
        hashlib.sha256(campaign_records[-1]).hexdigest().upper()
        if campaign_records
        else None
    )
    campaign_row = (
        json.loads(campaign_records[-1].decode("utf-8"))
        if campaign_records
        else None
    )
    repair = campaign_row.get("data_repair") if isinstance(campaign_row, dict) else None
    replacement = repair.get("replacement_prereg") if isinstance(repair, dict) else None
    if (
        validation.get("campaign_data_repair_row_sha256") != campaign_sha
        or not isinstance(campaign_row, dict)
        or campaign_row.get("event") != "DATA_REPAIR"
        or campaign_row.get("active_hypothesis_id") is not None
        or not isinstance(replacement, dict)
        or replacement.get("hypothesis_id") != hypothesis_id
        or replacement.get("sha256") != row.get("prereg_sha256")
        or repair.get("economic_trials_consumed") != 0
        or repair.get("performance_metrics_authorized") is not False
        or repair.get("economics_authorized") is not False
    ):
        errors.append(f"{label}: latest campaign DATA_REPAIR binding is invalid")

    receipt_path = validation.get("prepacket_control_plane_receipt_path")
    receipt_sha = validation.get("prepacket_control_plane_receipt_sha256")
    expected_prefix = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
    )
    if not isinstance(receipt_path, str) or not receipt_path.startswith(expected_prefix):
        errors.append(f"{label}: prepacket receipt path must be inside {expected_prefix!r}")
    receipt_file = verify_binding(
        receipt_path,
        receipt_sha,
        f"{label} prepacket receipt",
        errors,
    )
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: prepacket receipt invalid JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            exposure = receipt.get("exposure_readback")
            tests = receipt.get("test_run")
            if (
                receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification") != "PRELAUNCH_PACKET_AUTHORITY"
                or receipt.get("campaign_data_repair_row_sha256") != campaign_sha
                or not isinstance(exposure, dict)
                or exposure.get("hyp005_execution_receipts") != 0
                or exposure.get("hyp005_run_manifests") != 0
                or exposure.get("trades_executed") != 0
                or exposure.get("economic_trials_consumed") != 0
                or not isinstance(tests, dict)
                or tests.get("result") != "PASS"
                or tests.get("failed") != 0
                or not isinstance(tests.get("passed"), int)
                or tests.get("passed") < 1
            ):
                errors.append(f"{label}: prepacket receipt identity/test/exposure mismatch")

    runtime = WORKSPACE / "02. AlphaFactory/runtime"
    if runtime.is_dir():
        for receipt in runtime.glob("ea_execution_receipt_*.json"):
            try:
                if hypothesis_id in receipt.read_text(encoding="utf-8-sig"):
                    errors.append(
                        f"{label}: execution receipt already exists before packet authorization: {receipt.name}"
                    )
            except OSError:
                continue
    if "prelaunch packet authorization" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify the prelaunch packet authorization")
    return errors


def _prelaunch_packet_scope_correction_errors(
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} prelaunch packet scope correction"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    expected_added = {
        "prepacket_control_plane_receipt_correction_path",
        "prepacket_control_plane_receipt_correction_sha256",
    }
    if added != expected_added or removed:
        errors.append(
            f"{label}: only prepacket receipt correction path/SHA may be added"
        )
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    expected_changed = {"bound_tests"} | expected_added
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    for key, value in prior_validation.items():
        if key == "bound_tests":
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    prior_tests = prior_validation.get("bound_tests")
    current_tests = validation.get("bound_tests")
    if not isinstance(prior_tests, list) or not isinstance(current_tests, list):
        errors.append(f"{label}: prior/current bound_tests must be arrays")
        prior_tests = []
        current_tests = []
    prior_paths = {
        item.get("path")
        for item in prior_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    current_paths = {
        item.get("path")
        for item in current_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    added_test_paths = current_paths - prior_paths
    if len(added_test_paths) != 1 or not prior_paths.issubset(current_paths):
        errors.append(f"{label}: correction must add exactly one bound test path")
    if len(current_paths) != len(current_tests):
        errors.append(f"{label}: current bound_tests paths must be unique")
    for index, item in enumerate(current_tests):
        verify_recorded_binding_shape(
            item,
            f"{label} bound_tests[{index}]",
            errors,
        )

    correction_path = validation.get(
        "prepacket_control_plane_receipt_correction_path"
    )
    correction_sha = validation.get(
        "prepacket_control_plane_receipt_correction_sha256"
    )
    expected_prefix = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
    )
    if not isinstance(correction_path, str) or not correction_path.startswith(
        expected_prefix
    ):
        errors.append(f"{label}: correction path must be inside {expected_prefix!r}")
    correction_file = verify_binding(
        correction_path,
        correction_sha,
        f"{label} correction artifact",
        errors,
    )
    if correction_file is not None:
        try:
            correction = load_strict_json(correction_file)
        except Exception as exc:
            errors.append(f"{label}: correction artifact invalid JSON: {exc}")
            correction = None
        if isinstance(correction, dict):
            original = correction.get("original_receipt")
            original_receipt = None
            if isinstance(original, dict):
                original_file = verify_binding(
                    original.get("path"),
                    original.get("sha256"),
                    f"{label} original receipt",
                    errors,
                )
                if original_file is not None:
                    try:
                        original_receipt = load_strict_json(original_file)
                    except Exception as exc:
                        errors.append(f"{label}: original receipt invalid JSON: {exc}")
            exposure = correction.get("exposure_readback")
            rerun = correction.get("exact_rerun")
            control_plane = correction.get("control_plane_corrections")
            original_tests = (
                original_receipt.get("test_run")
                if isinstance(original_receipt, dict)
                else None
            )
            if (
                correction.get("hypothesis_id") != hypothesis_id
                or correction.get("classification")
                != "PRELAUNCH_PACKET_SCOPE_CORRECTION"
                or not isinstance(original, dict)
                or original.get("path")
                != prior_validation.get("prepacket_control_plane_receipt_path")
                or original.get("sha256")
                != prior_validation.get("prepacket_control_plane_receipt_sha256")
                or correction.get("bound_tests") != current_tests
                or correction.get("added_test_path")
                not in added_test_paths
                or not isinstance(exposure, dict)
                or exposure.get("hyp005_execution_receipts") != 0
                or exposure.get("hyp005_run_manifests") != 0
                or exposure.get("trades_executed") != 0
                or exposure.get("economic_trials_consumed") != 0
                or not isinstance(rerun, dict)
                or rerun.get("framework") != "pytest"
                or rerun.get("result") != "PASS"
                or rerun.get("failed") != 0
                or not isinstance(rerun.get("passed"), int)
                or not isinstance(rerun.get("declared_test_file_count"), int)
                or rerun.get("declared_test_file_count") != len(current_tests)
                or not isinstance(original_tests, dict)
                or original_tests.get("result") != "PASS"
                or original_tests.get("failed") != 0
                or rerun.get("passed") != original_tests.get("passed")
                or not isinstance(control_plane, list)
                or not control_plane
            ):
                errors.append(f"{label}: correction identity/scope/test/exposure mismatch")
            if isinstance(control_plane, list):
                for index, item in enumerate(control_plane):
                    verify_recorded_binding_shape(
                        item,
                        f"{label} control_plane_corrections[{index}]",
                        errors,
                    )

    runtime = WORKSPACE / "02. AlphaFactory/runtime"
    if runtime.is_dir():
        for receipt in runtime.glob("ea_execution_receipt_*.json"):
            try:
                if hypothesis_id in receipt.read_text(encoding="utf-8-sig"):
                    errors.append(
                        f"{label}: execution receipt already exists before scope correction: {receipt.name}"
                    )
            except OSError:
                continue
    if "prelaunch packet scope correction" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify the prelaunch packet scope correction")
    return errors


def _prelaunch_scope_validator_hardening_errors(
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} prelaunch scope validator hardening"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    expected_added = {
        "prepacket_scope_validator_hardening_receipt_path",
        "prepacket_scope_validator_hardening_receipt_sha256",
    }
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    if added != expected_added or removed:
        errors.append(
            f"{label}: only scope-validator hardening receipt path/SHA may be added"
        )
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    expected_changed = {"bound_tests"} | expected_added
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    for key, value in prior_validation.items():
        if key == "bound_tests":
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    prior_tests = prior_validation.get("bound_tests")
    current_tests = validation.get("bound_tests")
    if not isinstance(prior_tests, list) or not isinstance(current_tests, list):
        errors.append(f"{label}: prior/current bound_tests must be arrays")
        prior_tests = []
        current_tests = []
    prior_paths = [
        item.get("path")
        for item in prior_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    current_paths = [
        item.get("path")
        for item in current_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    if (
        prior_paths != current_paths
        or len(prior_paths) != len(prior_tests)
        or len(current_paths) != len(current_tests)
        or len(set(current_paths)) != len(current_paths)
    ):
        errors.append(f"{label}: bound_tests path set/order must remain exact and unique")
    for index, item in enumerate(current_tests):
        verify_recorded_binding_shape(
            item,
            f"{label} bound_tests[{index}]",
            errors,
        )

    receipt_path = validation.get(
        "prepacket_scope_validator_hardening_receipt_path"
    )
    receipt_sha = validation.get(
        "prepacket_scope_validator_hardening_receipt_sha256"
    )
    expected_prefix = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
    )
    if not isinstance(receipt_path, str) or not receipt_path.startswith(
        expected_prefix
    ):
        errors.append(f"{label}: hardening receipt path must be inside {expected_prefix!r}")
    receipt_file = verify_binding(
        receipt_path,
        receipt_sha,
        f"{label} hardening receipt",
        errors,
    )
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: hardening receipt invalid JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            prior_correction = receipt.get("prior_scope_correction")
            exposure = receipt.get("exposure_readback")
            rerun = receipt.get("exact_rerun")
            guards = receipt.get("adversarial_guards")
            control_plane = receipt.get("control_plane")
            if (
                receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_SCOPE_VALIDATOR_HARDENING"
                or not isinstance(prior_correction, dict)
                or prior_correction.get("path")
                != prior_validation.get(
                    "prepacket_control_plane_receipt_correction_path"
                )
                or prior_correction.get("sha256")
                != prior_validation.get(
                    "prepacket_control_plane_receipt_correction_sha256"
                )
                or receipt.get("bound_tests") != current_tests
                or not isinstance(exposure, dict)
                or exposure.get("hyp005_execution_receipts") != 0
                or exposure.get("hyp005_run_manifests") != 0
                or exposure.get("trades_executed") != 0
                or exposure.get("economic_trials_consumed") != 0
                or not isinstance(rerun, dict)
                or rerun.get("framework") != "pytest"
                or rerun.get("result") != "PASS"
                or rerun.get("failed") != 0
                or rerun.get("passed") != 121
                or rerun.get("declared_test_file_count") != len(current_tests)
                or not isinstance(guards, dict)
                or guards.get("wrong_pass_count_rejected") is not True
                or guards.get("wrong_declared_file_count_rejected") is not True
                or not isinstance(control_plane, list)
                or not control_plane
            ):
                errors.append(f"{label}: hardening identity/scope/test/exposure mismatch")
            if isinstance(control_plane, list):
                for index, item in enumerate(control_plane):
                    verify_recorded_binding_shape(
                        item,
                        f"{label} control_plane[{index}]",
                        errors,
                    )

    runtime = WORKSPACE / "02. AlphaFactory/runtime"
    if runtime.is_dir():
        for receipt in runtime.glob("ea_execution_receipt_*.json"):
            try:
                if hypothesis_id in receipt.read_text(encoding="utf-8-sig"):
                    errors.append(
                        f"{label}: execution receipt already exists before validator hardening: {receipt.name}"
                    )
            except OSError:
                continue
    if "prelaunch scope validator hardening" not in str(
        row.get("reason", "")
    ).lower():
        errors.append(
            f"{label}: reason must identify the prelaunch scope validator hardening"
        )
    return errors


def _prelaunch_xau_model4_collection_authorization_errors(
    prior_line: int,
    prior_row_sha256: str,
    prior_registry_prefix_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} prelaunch XAU Model4 collection authorization"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")
    if row.get("verdict") != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORIZED":
        errors.append(f"{label}: verdict mismatch")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    expected_added = {
        "packet_set_dry_run_receipt_path",
        "packet_set_dry_run_receipt_sha256",
        "authorized_packet_registry_sha256",
        "authorized_packet_registry_row_sha256",
        "authorized_packet_git_status_sha256",
        "authorized_current_git_status_sha256",
        "xau_task_packet_path",
        "xau_task_packet_sha256",
        "xau_model4_collection_launch_authorized",
        "mt5_data_collection_authorized",
        "model4_data_collection_authorized",
        "authorized_symbol",
        "authorized_symbol_order_index",
        "authorized_launch_limit",
        "authorized_launches_consumed",
    }
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    if added != expected_added or removed:
        errors.append(
            f"{label}: scoped authority additions must be exactly {sorted(expected_added)}"
        )
    expected_changed = {
        "probe_status",
        "runner_engine_sha256",
        "bound_tests",
        "task_packets_created",
        "task_packet_authorized_next",
    } | expected_added
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    for key, value in prior_validation.items():
        if key in expected_changed:
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    exact = {
        "probe_status": "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORIZED",
        "task_packets_created": True,
        "task_packet_authorized_next": False,
        "xau_model4_collection_launch_authorized": True,
        "mt5_data_collection_authorized": True,
        "model4_data_collection_authorized": True,
        "authorized_symbol": "XAUUSD",
        "authorized_symbol_order_index": 0,
        "authorized_launch_limit": 1,
        "authorized_launches_consumed": 0,
    }
    for key, expected in exact.items():
        if validation.get(key) != expected:
            errors.append(f"{label}: validation.{key} must equal {expected!r}")
    for key in (
        "mt5_authorized",
        "model4_authorized",
        "trading_backtest_authorized",
        "trades_authorized",
        "performance_metrics_authorized",
        "economics_authorized",
        "optimization_authorized",
        "validation_access_authorized",
        "holdout_access_authorized",
        "promotion_eligible",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if validation.get(key) is not False:
            errors.append(f"{label}: broad/economic authority {key!r} must remain false")
    if (
        validation.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
        or validation.get("model4_data_acquisition_authorized") is not True
        or validation.get("model4_performance_authorized") is not False
    ):
        errors.append(f"{label}: collection-only Model4 authority contract mismatch")

    prior_tests = prior_validation.get("bound_tests")
    current_tests = validation.get("bound_tests")
    if not isinstance(prior_tests, list) or not isinstance(current_tests, list):
        errors.append(f"{label}: prior/current bound_tests must be arrays")
        prior_tests = []
        current_tests = []
    prior_paths = [
        item.get("path")
        for item in prior_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    current_paths = [
        item.get("path")
        for item in current_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    if (
        prior_paths != current_paths
        or len(prior_paths) != len(prior_tests)
        or len(current_paths) != len(current_tests)
        or len(set(current_paths)) != len(current_paths)
    ):
        errors.append(f"{label}: bound_tests path set/order must remain exact and unique")
    for index, item in enumerate(current_tests):
        verify_recorded_binding_shape(item, f"{label} bound_tests[{index}]", errors)

    expected_packet_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/preflight/{hypothesis_id}/"
        "task_packet.XAUUSD.control.json"
    )
    if validation.get("xau_task_packet_path") != expected_packet_path:
        errors.append(f"{label}: XAU task packet path mismatch")
    for key in (
        "runner_engine_sha256",
        "authorized_packet_registry_sha256",
        "authorized_packet_registry_row_sha256",
        "authorized_packet_git_status_sha256",
        "authorized_current_git_status_sha256",
        "xau_task_packet_sha256",
    ):
        value = validation.get(key)
        if not isinstance(value, str) or re.fullmatch(r"[A-F0-9]{64}", value) is None:
            errors.append(f"{label}: validation.{key} must be uppercase SHA256")

    campaign_records = (
        WORKSPACE / "04. Memory/research/CAMPAIGN_EXPOSURE.jsonl"
    ).read_bytes().splitlines()
    campaign_sha = (
        hashlib.sha256(campaign_records[-1]).hexdigest().upper()
        if campaign_records
        else None
    )
    campaign_row = (
        json.loads(campaign_records[-1].decode("utf-8"))
        if campaign_records
        else None
    )
    repair = campaign_row.get("data_repair") if isinstance(campaign_row, dict) else None
    replacement = repair.get("replacement_prereg") if isinstance(repair, dict) else None
    if (
        campaign_sha != validation.get("campaign_data_repair_row_sha256")
        or not isinstance(campaign_row, dict)
        or campaign_row.get("event") != "DATA_REPAIR"
        or campaign_row.get("active_hypothesis_id") is not None
        or not isinstance(replacement, dict)
        or replacement.get("hypothesis_id") != hypothesis_id
        or replacement.get("sha256") != row.get("prereg_sha256")
        or repair.get("data_acquisition_authorized") is not True
        or repair.get("performance_metrics_authorized") is not False
        or repair.get("economics_authorized") is not False
    ):
        errors.append(f"{label}: latest campaign DATA_REPAIR authority mismatch")

    receipt_path = validation.get("packet_set_dry_run_receipt_path")
    receipt_sha = validation.get("packet_set_dry_run_receipt_sha256")
    expected_prefix = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
    )
    if not isinstance(receipt_path, str) or not receipt_path.startswith(expected_prefix):
        errors.append(f"{label}: authority receipt path must be inside {expected_prefix!r}")
    receipt_file = verify_binding(
        receipt_path,
        receipt_sha,
        f"{label} authority receipt",
        errors,
    )
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: authority receipt invalid JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            prior_registry = receipt.get("prior_registry")
            authorized_git_status = receipt.get("authorized_git_status")
            dry_run = receipt.get("xau_dry_run")
            packet_set = receipt.get("packet_set")
            tests = receipt.get("exact_test_run")
            exposure = receipt.get("exposure_readback")
            control_plane = receipt.get("control_plane")
            expected_symbols = validation.get("mandatory_symbols")
            packet_symbols = (
                [item.get("symbol") for item in packet_set]
                if isinstance(packet_set, list)
                and all(isinstance(item, dict) for item in packet_set)
                else []
            )
            if (
                receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORITY"
                or not isinstance(prior_registry, dict)
                or prior_registry.get("line") != prior_line
                or prior_registry.get("row_sha256")
                != prior_row_sha256
                or prior_registry.get("full_registry_sha256")
                != prior_registry_prefix_sha256
                or validation.get("authorized_packet_registry_row_sha256")
                != prior_row_sha256
                or validation.get("authorized_packet_registry_sha256")
                != prior_registry_prefix_sha256
                or not isinstance(authorized_git_status, dict)
                or authorized_git_status.get("packet_sha256")
                != validation.get("authorized_packet_git_status_sha256")
                or authorized_git_status.get("current_sha256")
                != validation.get("authorized_current_git_status_sha256")
                or receipt.get("campaign_data_repair_row_sha256") != campaign_sha
                or not isinstance(packet_set, list)
                or len(packet_set) != 9
                or packet_symbols != expected_symbols
                or not isinstance(dry_run, dict)
                or dry_run.get("symbol") != "XAUUSD"
                or dry_run.get("exit_code") != 0
                or dry_run.get("execution_allowed") is not True
                or dry_run.get("execution_blockers") != []
                or dry_run.get("execute") is not False
                or dry_run.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or dry_run.get("task_packet_path") != expected_packet_path
                or dry_run.get("task_packet_sha256")
                != validation.get("xau_task_packet_sha256")
                or not isinstance(tests, dict)
                or tests.get("framework") != "pytest"
                or tests.get("result") != "PASS"
                or tests.get("failed") != 0
                or tests.get("passed") != 121
                or tests.get("declared_test_file_count") != len(current_tests)
                or not isinstance(exposure, dict)
                or exposure.get("hyp005_execution_receipts") != 0
                or exposure.get("hyp005_run_manifests") != 0
                or exposure.get("trades_executed") != 0
                or exposure.get("economic_trials_consumed") != 0
                or not isinstance(control_plane, list)
                or not control_plane
            ):
                errors.append(f"{label}: authority receipt identity/scope/test/exposure mismatch")
            if isinstance(packet_set, list):
                packet_paths: list[str] = []
                for index, item in enumerate(packet_set):
                    verify_recorded_binding_shape(
                        item,
                        f"{label} packet_set[{index}]",
                        errors,
                    )
                    if isinstance(item, dict):
                        packet_paths.append(str(item.get("path") or ""))
                if len(set(packet_paths)) != len(packet_paths):
                    errors.append(f"{label}: packet_set paths must be unique")
            if isinstance(control_plane, list):
                for index, item in enumerate(control_plane):
                    verify_recorded_binding_shape(
                        item,
                        f"{label} control_plane[{index}]",
                        errors,
                    )

    if "prelaunch xau model4 collection authorization" not in str(
        row.get("reason", "")
    ).lower():
        errors.append(
            f"{label}: reason must identify the prelaunch XAU Model4 collection authorization"
        )
    return errors


def _prelaunch_xau_model4_execute_gate_hardening_errors(
    prior_line: int,
    prior_row_sha256: str,
    prior_registry_prefix_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} prelaunch XAU Model4 execute-gate hardening"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")
    if row.get("verdict") != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED":
        errors.append(f"{label}: verdict mismatch")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    expected_added = {
        "candidate_registry_validator_sha256",
        "alpha_entrypoint_sha256",
        "execution_dependency_bindings",
        "execute_gate_hardening_receipt_path",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_line",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
        "launch_claim_path",
    }
    added = set(validation) - set(prior_validation)
    removed = set(prior_validation) - set(validation)
    if added != expected_added or removed:
        errors.append(
            f"{label}: execute-gate additions must be exactly {sorted(expected_added)}"
        )
    expected_changed = {
        "probe_status",
        "runner_engine_sha256",
        "bound_tests",
        "authorized_current_git_status_sha256",
    } | expected_added
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    for key, value in prior_validation.items():
        if key in expected_changed:
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    if (
        validation.get("probe_status")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED"
    ):
        errors.append(f"{label}: probe_status mismatch")
    for key, expected in {
        "task_packets_created": True,
        "task_packet_authorized_next": False,
        "xau_model4_collection_launch_authorized": True,
        "mt5_data_collection_authorized": True,
        "model4_data_collection_authorized": True,
        "authorized_symbol": "XAUUSD",
        "authorized_symbol_order_index": 0,
        "authorized_launch_limit": 1,
        "authorized_launches_consumed": 0,
    }.items():
        if validation.get(key) != expected:
            errors.append(f"{label}: validation.{key} must equal {expected!r}")
    for key in (
        "mt5_authorized",
        "model4_authorized",
        "trading_backtest_authorized",
        "trades_authorized",
        "performance_metrics_authorized",
        "economics_authorized",
        "optimization_authorized",
        "validation_access_authorized",
        "holdout_access_authorized",
        "promotion_eligible",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if validation.get(key) is not False:
            errors.append(f"{label}: broad/economic authority {key!r} must remain false")

    prior_tests = prior_validation.get("bound_tests")
    current_tests = validation.get("bound_tests")
    if not isinstance(prior_tests, list) or not isinstance(current_tests, list):
        errors.append(f"{label}: prior/current bound_tests must be arrays")
        prior_tests = []
        current_tests = []
    prior_paths = [
        item.get("path")
        for item in prior_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    current_paths = [
        item.get("path")
        for item in current_tests
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    if (
        prior_paths != current_paths
        or len(prior_paths) != len(prior_tests)
        or len(current_paths) != len(current_tests)
        or len(set(current_paths)) != len(current_paths)
    ):
        errors.append(f"{label}: bound_tests path set/order must remain exact and unique")
    for index, item in enumerate(current_tests):
        verify_recorded_binding_shape(item, f"{label} bound_tests[{index}]", errors)

    for key in (
        "runner_engine_sha256",
        "candidate_registry_validator_sha256",
        "alpha_entrypoint_sha256",
        "authorized_current_git_status_sha256",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
    ):
        value = validation.get(key)
        if not isinstance(value, str) or re.fullmatch(r"[A-F0-9]{64}", value) is None:
            errors.append(f"{label}: validation.{key} must be uppercase SHA256")
    if validation.get("execute_gate_prior_registry_line") != prior_line:
        errors.append(f"{label}: execute_gate_prior_registry_line mismatch")
    if validation.get("execute_gate_prior_registry_sha256") != prior_registry_prefix_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_sha256 mismatch")
    if validation.get("execute_gate_prior_registry_row_sha256") != prior_row_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_row_sha256 mismatch")

    expected_claim_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
    )
    if validation.get("launch_claim_path") != expected_claim_path:
        errors.append(f"{label}: launch_claim_path mismatch")

    dependency_bindings = validation.get("execution_dependency_bindings")
    expected_dependency_paths = [
        "02. AlphaFactory/alpha.ps1",
        "02. AlphaFactory/alpha.local.ps1",
        "02. AlphaFactory/tools/mt5_storage_contract.ps1",
        "02. AlphaFactory/tools/ea_contract.ps1",
        "02. AlphaFactory/tools/log_storage.ps1",
        "02. AlphaFactory/tools/audit_mql5_nonrepaint.py",
    ]
    dependency_paths = (
        [item.get("path") for item in dependency_bindings]
        if isinstance(dependency_bindings, list)
        and all(isinstance(item, dict) for item in dependency_bindings)
        else []
    )
    if dependency_paths != expected_dependency_paths:
        errors.append(f"{label}: execution dependency path/order mismatch")
    if isinstance(dependency_bindings, list):
        for index, item in enumerate(dependency_bindings):
            verify_recorded_binding_shape(
                item,
                f"{label} execution_dependency_bindings[{index}]",
                errors,
            )
    if (
        isinstance(dependency_bindings, list)
        and dependency_bindings
        and isinstance(dependency_bindings[0], dict)
        and dependency_bindings[0].get("sha256")
        != validation.get("alpha_entrypoint_sha256")
    ):
        errors.append(f"{label}: alpha_entrypoint_sha256 must match dependency[0]")

    receipt_path = validation.get("execute_gate_hardening_receipt_path")
    receipt_sha = validation.get("execute_gate_hardening_receipt_sha256")
    expected_receipt_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT.json"
    )
    if receipt_path != expected_receipt_path:
        errors.append(f"{label}: execute-gate hardening receipt path mismatch")
    receipt_file = verify_binding(receipt_path, receipt_sha, f"{label} receipt", errors)
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: receipt invalid strict JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            prior_registry = receipt.get("prior_registry")
            prior_authority = receipt.get("prior_authority_receipt")
            git_status = receipt.get("authorized_git_status")
            control_plane = receipt.get("control_plane")
            exposure = receipt.get("exposure_readback")
            test_run = receipt.get("exact_test_run")
            receipt_dependencies = (
                control_plane.get("execution_dependency_bindings")
                if isinstance(control_plane, dict)
                else None
            )
            if (
                receipt.get("schema_version")
                != "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v1"
                or receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_XAU_MODEL4_EXECUTE_GATE_HARDENING"
                or receipt.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or receipt.get("verdict") != "PASS_ONE_SHOT_XAU_EXECUTE_GATE"
                or not isinstance(prior_registry, dict)
                or prior_registry.get("path")
                != "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
                or prior_registry.get("line") != prior_line
                or prior_registry.get("row_sha256") != prior_row_sha256
                or prior_registry.get("sha256")
                != prior_registry_prefix_sha256
                or not isinstance(prior_authority, dict)
                or prior_authority.get("path")
                != validation.get("packet_set_dry_run_receipt_path")
                or prior_authority.get("sha256")
                != validation.get("packet_set_dry_run_receipt_sha256")
                or not isinstance(git_status, dict)
                or git_status.get("current_sha256")
                != validation.get("authorized_current_git_status_sha256")
                or not isinstance(control_plane, dict)
                or control_plane.get("runner")
                != {
                    "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                    "sha256": validation.get("runner_engine_sha256"),
                }
                or control_plane.get("candidate_registry_validator")
                != {
                    "path": "04. Memory/research/validate_candidate_registry.py",
                    "sha256": validation.get("candidate_registry_validator_sha256"),
                }
                or control_plane.get("alpha_entrypoint")
                != {
                    "path": "02. AlphaFactory/alpha.ps1",
                    "sha256": validation.get("alpha_entrypoint_sha256"),
                }
                or receipt_dependencies != dependency_bindings
                or receipt.get("launch_claim_path") != expected_claim_path
                or not isinstance(test_run, dict)
                or test_run.get("framework") != "pytest"
                or test_run.get("result") != "PASS"
                or test_run.get("passed") != 122
                or test_run.get("failed") != 0
                or test_run.get("declared_test_file_count") != len(current_tests)
                or test_run.get("symbol") != "XAUUSD"
                or test_run.get("model") != 4
                or test_run.get("run_role") != "control"
                or test_run.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or not isinstance(exposure, dict)
                or exposure.get("hyp005_execution_receipts") != 0
                or exposure.get("hyp005_run_manifests") != 0
                or exposure.get("launch_claims") != 0
                or exposure.get("trades_executed") != 0
                or exposure.get("economic_trials_consumed") != 0
            ):
                errors.append(f"{label}: receipt identity/control-plane/exposure mismatch")
    if "prelaunch xau model4 execute-gate hardening" not in str(
        row.get("reason", "")
    ).lower():
        errors.append(f"{label}: reason must identify the execute-gate hardening")
    return errors


def _prelaunch_xau_model4_postlock_revalidation_errors(
    prior_line: int,
    prior_row_sha256: str,
    prior_registry_prefix_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} post-lock execute-gate revalidation"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if (
        prior.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED"
        or row.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
    ):
        errors.append(f"{label}: prior/current verdict mismatch")
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    if set(prior_validation) != set(validation):
        errors.append(f"{label}: validation key set must remain exact")
    expected_changed = {
        "probe_status",
        "runner_engine_sha256",
        "candidate_registry_validator_sha256",
        "bound_tests",
        "authorized_current_git_status_sha256",
        "execute_gate_hardening_receipt_path",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_line",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
    }
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    if (
        validation.get("probe_status")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
    ):
        errors.append(f"{label}: probe_status mismatch")
    for key, expected in {
        "task_packets_created": True,
        "task_packet_authorized_next": False,
        "xau_model4_collection_launch_authorized": True,
        "mt5_data_collection_authorized": True,
        "model4_data_collection_authorized": True,
        "authorized_symbol": "XAUUSD",
        "authorized_symbol_order_index": 0,
        "authorized_launch_limit": 1,
        "authorized_launches_consumed": 0,
    }.items():
        if validation.get(key) != expected:
            errors.append(f"{label}: validation.{key} must equal {expected!r}")
    for key in (
        "mt5_authorized",
        "model4_authorized",
        "trading_backtest_authorized",
        "trades_authorized",
        "performance_metrics_authorized",
        "economics_authorized",
        "optimization_authorized",
        "validation_access_authorized",
        "holdout_access_authorized",
        "promotion_eligible",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if validation.get(key) is not False:
            errors.append(f"{label}: broad/economic authority {key!r} must remain false")

    prior_tests = prior_validation.get("bound_tests")
    current_tests = validation.get("bound_tests")
    prior_paths = (
        [item.get("path") for item in prior_tests]
        if isinstance(prior_tests, list)
        and all(isinstance(item, dict) for item in prior_tests)
        else []
    )
    current_paths = (
        [item.get("path") for item in current_tests]
        if isinstance(current_tests, list)
        and all(isinstance(item, dict) for item in current_tests)
        else []
    )
    if (
        not isinstance(prior_tests, list)
        or not isinstance(current_tests, list)
        or prior_paths != current_paths
        or len(current_paths) != len(prior_tests)
        or len(set(current_paths)) != len(current_paths)
    ):
        errors.append(f"{label}: bound_tests path set/order must remain exact")
    if isinstance(current_tests, list):
        for index, item in enumerate(current_tests):
            verify_recorded_binding_shape(item, f"{label} bound_tests[{index}]", errors)

    for key in (
        "runner_engine_sha256",
        "candidate_registry_validator_sha256",
        "alpha_entrypoint_sha256",
        "authorized_current_git_status_sha256",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
    ):
        value = validation.get(key)
        if not isinstance(value, str) or re.fullmatch(r"[A-F0-9]{64}", value) is None:
            errors.append(f"{label}: validation.{key} must be uppercase SHA256")
    if validation.get("execute_gate_prior_registry_line") != prior_line:
        errors.append(f"{label}: execute_gate_prior_registry_line mismatch")
    if validation.get("execute_gate_prior_registry_sha256") != prior_registry_prefix_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_sha256 mismatch")
    if validation.get("execute_gate_prior_registry_row_sha256") != prior_row_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_row_sha256 mismatch")

    expected_claim_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
    )
    if validation.get("launch_claim_path") != expected_claim_path:
        errors.append(f"{label}: launch_claim_path mismatch")
    dependency_bindings = validation.get("execution_dependency_bindings")
    if dependency_bindings != prior_validation.get("execution_dependency_bindings"):
        errors.append(f"{label}: execution dependency bindings must remain unchanged")

    receipt_path = validation.get("execute_gate_hardening_receipt_path")
    receipt_sha = validation.get("execute_gate_hardening_receipt_sha256")
    expected_receipt_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V2.json"
    )
    if receipt_path != expected_receipt_path:
        errors.append(f"{label}: V2 hardening receipt path mismatch")
    receipt_file = verify_binding(receipt_path, receipt_sha, f"{label} receipt", errors)
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: receipt invalid strict JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            prior_registry = receipt.get("prior_registry")
            prior_authority = receipt.get("prior_authority_receipt")
            git_status = receipt.get("authorized_git_status")
            control_plane = receipt.get("control_plane")
            test_run = receipt.get("exact_test_run")
            exposure = receipt.get("exposure_readback")
            if (
                receipt.get("schema_version")
                != "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v2"
                or receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_XAU_MODEL4_POSTLOCK_EXECUTE_GATE_HARDENING"
                or receipt.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or receipt.get("verdict")
                != "PASS_ONE_SHOT_XAU_POSTLOCK_EXECUTE_GATE"
                or prior_registry
                != {
                    "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
                    "line": prior_line,
                    "sha256": prior_registry_prefix_sha256,
                    "row_sha256": prior_row_sha256,
                }
                or not isinstance(prior_authority, dict)
                or prior_authority.get("path")
                != validation.get("packet_set_dry_run_receipt_path")
                or prior_authority.get("sha256")
                != validation.get("packet_set_dry_run_receipt_sha256")
                or git_status
                != {"current_sha256": validation.get("authorized_current_git_status_sha256")}
                or not isinstance(control_plane, dict)
                or control_plane.get("runner")
                != {
                    "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                    "sha256": validation.get("runner_engine_sha256"),
                }
                or control_plane.get("candidate_registry_validator")
                != {
                    "path": "04. Memory/research/validate_candidate_registry.py",
                    "sha256": validation.get("candidate_registry_validator_sha256"),
                }
                or control_plane.get("alpha_entrypoint")
                != {
                    "path": "02. AlphaFactory/alpha.ps1",
                    "sha256": validation.get("alpha_entrypoint_sha256"),
                }
                or control_plane.get("execution_dependency_bindings")
                != dependency_bindings
                or receipt.get("launch_claim_path") != expected_claim_path
                or test_run
                != {
                    "framework": "pytest",
                    "result": "PASS",
                    "passed": 10,
                    "failed": 0,
                    "declared_test_selector_count": 4,
                    "purpose": "POSTLOCK_GATE_TARGETED",
                    "symbol": "XAUUSD",
                    "model": 4,
                    "run_role": "control",
                    "authority": MODEL4_DATA_ACQUISITION_AUTHORITY,
                }
                or exposure
                != {
                    "hyp005_execution_receipts": 0,
                    "hyp005_run_manifests": 0,
                    "launch_claims": 0,
                    "trades_executed": 0,
                    "economic_trials_consumed": 0,
                }
            ):
                errors.append(f"{label}: receipt identity/control-plane/exposure mismatch")
    if "post-lock execute-gate revalidation" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify post-lock execute-gate revalidation")
    return errors


def _prelaunch_xau_model4_full_suite_authorization_errors(
    prior_line: int,
    prior_row_sha256: str,
    prior_registry_prefix_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} full-suite execute authorization"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if (
        prior.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
        or row.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
    ):
        errors.append(f"{label}: prior/current verdict mismatch")
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    if set(prior_validation) != set(validation):
        errors.append(f"{label}: validation key set must remain exact")
    expected_changed = {
        "probe_status",
        "execute_gate_hardening_receipt_path",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_line",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
    }
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    if (
        validation.get("probe_status")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
    ):
        errors.append(f"{label}: probe_status mismatch")
    if validation.get("execute_gate_prior_registry_line") != prior_line:
        errors.append(f"{label}: execute_gate_prior_registry_line mismatch")
    if validation.get("execute_gate_prior_registry_sha256") != prior_registry_prefix_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_sha256 mismatch")
    if validation.get("execute_gate_prior_registry_row_sha256") != prior_row_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_row_sha256 mismatch")
    for key, value in prior_validation.items():
        if key in expected_changed:
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    expected_claim_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
    )
    receipt_path = validation.get("execute_gate_hardening_receipt_path")
    receipt_sha = validation.get("execute_gate_hardening_receipt_sha256")
    expected_receipt_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V3.json"
    )
    if receipt_path != expected_receipt_path:
        errors.append(f"{label}: full-suite hardening receipt path mismatch")
    receipt_file = verify_binding(receipt_path, receipt_sha, f"{label} receipt", errors)
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: receipt invalid strict JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            control_plane = receipt.get("control_plane")
            if (
                receipt.get("schema_version")
                != "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v3"
                or receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_XAU_MODEL4_FULL_SUITE_EXECUTE_AUTHORIZATION"
                or receipt.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or receipt.get("verdict")
                != "PASS_ONE_SHOT_XAU_FULL_SUITE_EXECUTE_GATE"
                or receipt.get("prior_registry")
                != {
                    "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
                    "line": prior_line,
                    "sha256": prior_registry_prefix_sha256,
                    "row_sha256": prior_row_sha256,
                }
                or receipt.get("prior_authority_receipt")
                != {
                    "path": validation.get("packet_set_dry_run_receipt_path"),
                    "sha256": validation.get("packet_set_dry_run_receipt_sha256"),
                }
                or receipt.get("authorized_git_status")
                != {"current_sha256": validation.get("authorized_current_git_status_sha256")}
                or not isinstance(control_plane, dict)
                or control_plane.get("runner")
                != {
                    "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                    "sha256": validation.get("runner_engine_sha256"),
                }
                or control_plane.get("candidate_registry_validator")
                != {
                    "path": "04. Memory/research/validate_candidate_registry.py",
                    "sha256": validation.get("candidate_registry_validator_sha256"),
                }
                or control_plane.get("alpha_entrypoint")
                != {
                    "path": "02. AlphaFactory/alpha.ps1",
                    "sha256": validation.get("alpha_entrypoint_sha256"),
                }
                or control_plane.get("execution_dependency_bindings")
                != validation.get("execution_dependency_bindings")
                or receipt.get("launch_claim_path") != expected_claim_path
                or receipt.get("exact_test_run")
                != {
                    "framework": "pytest",
                    "result": "PASS",
                    "passed": 122,
                    "failed": 0,
                    "declared_test_file_count": 10,
                    "symbol": "XAUUSD",
                    "model": 4,
                    "run_role": "control",
                    "authority": MODEL4_DATA_ACQUISITION_AUTHORITY,
                }
                or receipt.get("exposure_readback")
                != {
                    "hyp005_execution_receipts": 0,
                    "hyp005_run_manifests": 0,
                    "launch_claims": 0,
                    "trades_executed": 0,
                    "economic_trials_consumed": 0,
                }
            ):
                errors.append(f"{label}: receipt identity/control-plane/exposure mismatch")
    if "full-suite execute authorization" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify full-suite execute authorization")
    return errors


def _prelaunch_xau_model4_targeted_bridge_errors(
    prior_line: int,
    prior_row_sha256: str,
    prior_registry_prefix_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} registry-lock targeted bridge"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if (
        prior.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
        or row.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
    ):
        errors.append(f"{label}: prior/current verdict mismatch")
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    if set(prior_validation) != set(validation):
        errors.append(f"{label}: validation key set must remain exact")
    expected_changed = {
        "probe_status",
        "runner_engine_sha256",
        "candidate_registry_validator_sha256",
        "bound_tests",
        "authorized_current_git_status_sha256",
        "execute_gate_hardening_receipt_path",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_line",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
    }
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    if (
        validation.get("probe_status")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
    ):
        errors.append(f"{label}: probe_status mismatch")
    if validation.get("execute_gate_prior_registry_line") != prior_line:
        errors.append(f"{label}: execute_gate_prior_registry_line mismatch")
    if validation.get("execute_gate_prior_registry_sha256") != prior_registry_prefix_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_sha256 mismatch")
    if validation.get("execute_gate_prior_registry_row_sha256") != prior_row_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_row_sha256 mismatch")
    for key, value in prior_validation.items():
        if key in expected_changed:
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    current_tests = validation.get("bound_tests")
    if not isinstance(current_tests, list):
        errors.append(f"{label}: bound_tests must be an array")
    else:
        for index, item in enumerate(current_tests):
            verify_recorded_binding_shape(item, f"{label} bound_tests[{index}]", errors)

    receipt_path = validation.get("execute_gate_hardening_receipt_path")
    receipt_sha = validation.get("execute_gate_hardening_receipt_sha256")
    expected_receipt_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V4.json"
    )
    if receipt_path != expected_receipt_path:
        errors.append(f"{label}: V4 bridge receipt path mismatch")
    receipt_file = verify_binding(receipt_path, receipt_sha, f"{label} receipt", errors)
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: receipt invalid strict JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            expected_receipt_keys = {
                "schema_version",
                "hypothesis_id",
                "classification",
                "authority",
                "verdict",
                "execution_authorized",
                "full_suite_attested",
                "prior_registry",
                "prior_execute_gate_receipt",
                "prior_authority_receipt",
                "authorized_git_status",
                "control_plane",
                "bound_tests",
                "launch_claim_path",
                "exact_test_run",
                "exposure_readback",
            }
            control_plane = receipt.get("control_plane")
            if (
                set(receipt) != expected_receipt_keys
                or
                receipt.get("schema_version")
                != "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v4"
                or receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_XAU_MODEL4_REGISTRY_LOCK_TOCTOU_TARGETED_HARDENING"
                or receipt.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or receipt.get("verdict")
                != "PASS_XAU_REGISTRY_LOCK_TOCTOU_TARGETED_GATE"
                or receipt.get("execution_authorized") is not False
                or receipt.get("full_suite_attested") is not False
                or receipt.get("prior_registry")
                != {
                    "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
                    "line": prior_line,
                    "sha256": prior_registry_prefix_sha256,
                    "row_sha256": prior_row_sha256,
                }
                or receipt.get("prior_execute_gate_receipt")
                != {
                    "path": prior_validation.get("execute_gate_hardening_receipt_path"),
                    "sha256": prior_validation.get("execute_gate_hardening_receipt_sha256"),
                }
                or receipt.get("prior_authority_receipt")
                != {
                    "path": validation.get("packet_set_dry_run_receipt_path"),
                    "sha256": validation.get("packet_set_dry_run_receipt_sha256"),
                }
                or receipt.get("authorized_git_status")
                != {"current_sha256": validation.get("authorized_current_git_status_sha256")}
                or not isinstance(control_plane, dict)
                or control_plane.get("runner")
                != {
                    "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                    "sha256": validation.get("runner_engine_sha256"),
                }
                or control_plane.get("candidate_registry_validator")
                != {
                    "path": "04. Memory/research/validate_candidate_registry.py",
                    "sha256": validation.get("candidate_registry_validator_sha256"),
                }
                or control_plane.get("alpha_entrypoint")
                != {
                    "path": "02. AlphaFactory/alpha.ps1",
                    "sha256": validation.get("alpha_entrypoint_sha256"),
                }
                or control_plane.get("execution_dependency_bindings")
                != validation.get("execution_dependency_bindings")
                or receipt.get("bound_tests") != validation.get("bound_tests")
                or receipt.get("launch_claim_path")
                != validation.get("launch_claim_path")
                or receipt.get("exact_test_run")
                != {
                    "framework": "pytest",
                    "result": "PASS",
                    "passed": 9,
                    "failed": 0,
                    "declared_test_selector_count": 3,
                    "purpose": "REGISTRY_LOCK_TOCTOU_TARGETED",
                    "symbol": "XAUUSD",
                    "model": 4,
                    "run_role": "control",
                    "authority": MODEL4_DATA_ACQUISITION_AUTHORITY,
                }
                or receipt.get("exposure_readback")
                != {
                    "hyp005_execution_receipts": 0,
                    "hyp005_run_manifests": 0,
                    "launch_claims": 0,
                    "trades_executed": 0,
                    "economic_trials_consumed": 0,
                }
            ):
                errors.append(f"{label}: receipt identity/control-plane/test/exposure mismatch")
    if "registry-lock toctou targeted hardening" not in str(row.get("reason", "")).lower():
        errors.append(f"{label}: reason must identify registry-lock TOCTOU targeted hardening")
    return errors


def _prelaunch_xau_model4_registry_lock_full_suite_authorization_errors(
    prior_line: int,
    prior_row_sha256: str,
    prior_registry_prefix_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} registry-lock full-suite execute authorization"
    errors: list[str] = []
    if prior.get("state") != "screened" or row.get("state") != "screened":
        return [f"{label}: transition must be screened->screened"]
    if (
        prior.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
        or row.get("verdict")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED"
    ):
        errors.append(f"{label}: prior/current verdict mismatch")
    if prior.get("run_ids") != [] or row.get("run_ids") != []:
        errors.append(f"{label}: run_ids must remain empty")
    for metrics, owner in ((prior.get("metrics"), "prior"), (row.get("metrics"), "current")):
        if not isinstance(metrics, dict) or any(
            metrics.get(key) != expected
            for key, expected in {
                "mt5_launches": 0,
                "economic_trials_consumed": 0,
                "trades_executed": 0,
                "economics_executed": False,
            }.items()
        ):
            errors.append(f"{label}: {owner} metrics must prove zero prelaunch exposure")
    for key in set(prior) | set(row):
        if key in {"updated_at_utc", "reason", "verdict", "validation"}:
            continue
        if row.get(key) != prior.get(key):
            errors.append(f"{label}: prohibited top-level change {key!r}")

    prior_validation = prior.get("validation")
    validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(validation, dict):
        return errors + [f"{label}: validation objects are required"]
    if set(prior_validation) != set(validation):
        errors.append(f"{label}: validation key set must remain exact")
    expected_changed = {
        "probe_status",
        "execute_gate_hardening_receipt_path",
        "execute_gate_hardening_receipt_sha256",
        "execute_gate_prior_registry_line",
        "execute_gate_prior_registry_sha256",
        "execute_gate_prior_registry_row_sha256",
    }
    changed = {
        key
        for key in set(prior_validation) | set(validation)
        if prior_validation.get(key) != validation.get(key)
    }
    if changed != expected_changed:
        errors.append(
            f"{label}: validation changes must be exactly {sorted(expected_changed)}"
        )
    if (
        validation.get("probe_status")
        != "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED"
    ):
        errors.append(f"{label}: probe_status mismatch")
    if validation.get("execute_gate_prior_registry_line") != prior_line:
        errors.append(f"{label}: execute_gate_prior_registry_line mismatch")
    if validation.get("execute_gate_prior_registry_sha256") != prior_registry_prefix_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_sha256 mismatch")
    if validation.get("execute_gate_prior_registry_row_sha256") != prior_row_sha256:
        errors.append(f"{label}: execute_gate_prior_registry_row_sha256 mismatch")
    for key, value in prior_validation.items():
        if key in expected_changed:
            continue
        if validation.get(key) != value:
            errors.append(f"{label}: prior validation field {key!r} changed")

    expected_claim_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
    )
    receipt_path = validation.get("execute_gate_hardening_receipt_path")
    receipt_sha = validation.get("execute_gate_hardening_receipt_sha256")
    expected_receipt_path = (
        f"03. EA Developer/{row.get('ea_name')}/research/evidence/{hypothesis_id}/"
        "HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V5.json"
    )
    if receipt_path != expected_receipt_path:
        errors.append(f"{label}: V5 hardening receipt path mismatch")
    receipt_file = verify_binding(receipt_path, receipt_sha, f"{label} receipt", errors)
    if receipt_file is not None:
        try:
            receipt = load_strict_json(receipt_file)
        except Exception as exc:
            errors.append(f"{label}: receipt invalid strict JSON: {exc}")
            receipt = None
        if isinstance(receipt, dict):
            expected_receipt_keys = {
                "schema_version",
                "hypothesis_id",
                "classification",
                "authority",
                "verdict",
                "execution_authorized",
                "full_suite_attested",
                "prior_registry",
                "prior_bridge_receipt",
                "prior_authority_receipt",
                "authorized_git_status",
                "control_plane",
                "bound_tests",
                "launch_claim_path",
                "exact_test_run",
                "exposure_readback",
            }
            control_plane = receipt.get("control_plane")
            if (
                set(receipt) != expected_receipt_keys
                or receipt.get("schema_version")
                != "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v5"
                or receipt.get("hypothesis_id") != hypothesis_id
                or receipt.get("classification")
                != "PRELAUNCH_XAU_MODEL4_REGISTRY_LOCK_FULL_SUITE_EXECUTE_AUTHORIZATION"
                or receipt.get("authority") != MODEL4_DATA_ACQUISITION_AUTHORITY
                or receipt.get("verdict")
                != "PASS_ONE_SHOT_XAU_REGISTRY_LOCK_FULL_SUITE_EXECUTE_GATE"
                or receipt.get("execution_authorized") is not True
                or receipt.get("full_suite_attested") is not True
                or receipt.get("prior_registry")
                != {
                    "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
                    "line": prior_line,
                    "sha256": prior_registry_prefix_sha256,
                    "row_sha256": prior_row_sha256,
                }
                or receipt.get("prior_bridge_receipt")
                != {
                    "path": prior_validation.get("execute_gate_hardening_receipt_path"),
                    "sha256": prior_validation.get("execute_gate_hardening_receipt_sha256"),
                }
                or receipt.get("prior_authority_receipt")
                != {
                    "path": validation.get("packet_set_dry_run_receipt_path"),
                    "sha256": validation.get("packet_set_dry_run_receipt_sha256"),
                }
                or receipt.get("authorized_git_status")
                != {"current_sha256": validation.get("authorized_current_git_status_sha256")}
                or not isinstance(control_plane, dict)
                or control_plane.get("runner")
                != {
                    "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                    "sha256": validation.get("runner_engine_sha256"),
                }
                or control_plane.get("candidate_registry_validator")
                != {
                    "path": "04. Memory/research/validate_candidate_registry.py",
                    "sha256": validation.get("candidate_registry_validator_sha256"),
                }
                or control_plane.get("alpha_entrypoint")
                != {
                    "path": "02. AlphaFactory/alpha.ps1",
                    "sha256": validation.get("alpha_entrypoint_sha256"),
                }
                or control_plane.get("execution_dependency_bindings")
                != validation.get("execution_dependency_bindings")
                or receipt.get("bound_tests") != validation.get("bound_tests")
                or receipt.get("launch_claim_path") != expected_claim_path
                or receipt.get("exact_test_run")
                != {
                    "framework": "pytest",
                    "result": "PASS",
                    "passed": 124,
                    "failed": 0,
                    "declared_test_file_count": 10,
                    "symbol": "XAUUSD",
                    "model": 4,
                    "run_role": "control",
                    "authority": MODEL4_DATA_ACQUISITION_AUTHORITY,
                }
                or receipt.get("exposure_readback")
                != {
                    "hyp005_execution_receipts": 0,
                    "hyp005_run_manifests": 0,
                    "launch_claims": 0,
                    "trades_executed": 0,
                    "economic_trials_consumed": 0,
                }
            ):
                errors.append(f"{label}: receipt identity/control-plane/test/exposure mismatch")
    if "registry-lock full-suite execute authorization" not in str(
        row.get("reason", "")
    ).lower():
        errors.append(
            f"{label}: reason must identify registry-lock full-suite execute authorization"
        )
    return errors


def _validate_latest_hyp005_execute_authority(
    line: int,
    row: dict[str, Any],
    errors: list[str],
) -> None:
    label = f"line {line} {HYP005_MODEL4_COLLECTION_ID} active one-shot authority"
    validation = row.get("validation")
    if not isinstance(validation, dict):
        errors.append(f"{label}: validation object is required")
        return
    expected_live_bindings = [
        (
            "02. AlphaFactory/tools/research_loop_engine.ps1",
            validation.get("runner_engine_sha256"),
            "runner",
        ),
        (
            "04. Memory/research/validate_candidate_registry.py",
            validation.get("candidate_registry_validator_sha256"),
            "candidate registry validator",
        ),
        (
            validation.get("execute_gate_hardening_receipt_path"),
            validation.get("execute_gate_hardening_receipt_sha256"),
            "execute-gate hardening receipt",
        ),
    ]
    for path, sha256, binding_label in expected_live_bindings:
        verify_binding(path, sha256, f"{label} {binding_label}", errors)
    dependencies = validation.get("execution_dependency_bindings")
    if not isinstance(dependencies, list):
        errors.append(f"{label}: execution_dependency_bindings must be an array")
    else:
        for index, item in enumerate(dependencies):
            if not isinstance(item, dict):
                errors.append(f"{label}: dependency[{index}] must be an object")
                continue
            verify_binding(
                item.get("path"),
                item.get("sha256"),
                f"{label} dependency[{index}]",
                errors,
            )
    bound_tests = validation.get("bound_tests")
    if not isinstance(bound_tests, list):
        errors.append(f"{label}: bound_tests must be an array")
    else:
        for index, item in enumerate(bound_tests):
            if not isinstance(item, dict):
                errors.append(f"{label}: bound_tests[{index}] must be an object")
                continue
            verify_binding(
                item.get("path"),
                item.get("sha256"),
                f"{label} bound_tests[{index}]",
                errors,
            )

    claim_path = normalized_workspace_path(
        validation.get("launch_claim_path"),
        f"{label} launch claim",
        errors,
    )
    if claim_path is not None and claim_path.exists():
        errors.append(
            f"{label}: durable launch claim already exists; authority is consumed/replay-blocked"
        )

    runtime = WORKSPACE / "02. AlphaFactory/runtime"
    if runtime.is_dir():
        for receipt_path in runtime.glob("ea_execution_receipt_*.json"):
            try:
                receipt = load_strict_json(receipt_path)
            except Exception as exc:
                errors.append(
                    f"{label}: unreadable execution receipt blocks authority: "
                    f"{receipt_path.name}: {exc}"
                )
                continue
            if (
                isinstance(receipt, dict)
                and receipt.get("hypothesis_id") == HYP005_MODEL4_COLLECTION_ID
            ):
                errors.append(
                    f"{label}: execution receipt already exists; authority is consumed/replay-blocked: "
                    f"{receipt_path.name}"
                )


def load_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        parse_constant=reject_nonfinite,
        object_pairs_hook=reject_duplicate_keys,
    )


def _is_reparse(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _source_only_safe_regular_path(
    raw: Any, label: str, errors: list[str]
) -> Path | None:
    normalized = normalized_workspace_path(raw, label, errors)
    if normalized is None:
        return None
    pure = PurePosixPath(str(raw))
    lexical = WORKSPACE.joinpath(*pure.parts)
    candidates = [WORKSPACE]
    current = WORKSPACE
    for part in pure.parts:
        current = current / part
        candidates.append(current)
    for candidate in candidates:
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink() or _is_reparse(candidate):
                errors.append(f"{label}: path contains symlink or reparse point: {raw}")
                return None
    if not lexical.is_file():
        errors.append(f"{label}: file is missing: {raw}")
        return None
    info = lexical.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        errors.append(f"{label}: file must be a single-link regular file: {raw}")
        return None
    return lexical


def _reviewed_base_source_sha256(path: Path, label: str, errors: list[str]) -> str | None:
    payload = path.read_bytes()
    pattern = re.compile(
        rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
    )
    lines = payload.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if pattern.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        errors.append(f"{label}: builder must contain exactly one normalized review sentinel")
        return None
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return hashlib.sha256(b"".join(lines)).hexdigest().upper()


def _generic_source_only_authority_transition_errors(
    prior: dict[str, Any], line: int, row: dict[str, Any]
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} source-only authority transition"
    errors: list[str] = []
    if hypothesis_id == HYP007_ID:
        errors.append(f"{label}: HYP007 must use its exact historical exception")
        return errors
    if prior.get("state") != "probe" or row.get("state") != "probe":
        errors.append(f"{label}: transition must be probe->probe")
    if set(prior) != set(row):
        errors.append(f"{label}: root field set changed")
    for key in set(prior) | set(row):
        if key not in SOURCE_ONLY_ALLOWED_ROOT_CHANGES and prior.get(key) != row.get(key):
            errors.append(f"{label}: prohibited root change '{key}'")

    prior_validation = prior.get("validation")
    successor = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(successor, dict):
        errors.append(f"{label}: validation objects are required")
        return errors
    if set(successor) != set(prior_validation) | SOURCE_ONLY_ALLOWED_VALIDATION_ADDITIONS:
        errors.append(f"{label}: validation field set is not the exact reviewed source-only successor set")
    for key in set(prior_validation) | set(successor):
        if key not in SOURCE_ONLY_ALLOWED_VALIDATION_CHANGES and prior_validation.get(key) != successor.get(key):
            errors.append(f"{label}: prohibited validation change '{key}'")

    if prior_validation.get("source_build_authorized") is not True:
        errors.append(f"{label}: prior source_build_authorized must be true")
    if successor.get("source_build_authorized") is not False:
        errors.append(f"{label}: successor must freeze source_build_authorized=false")
    if prior_validation.get("source_run_authorized") is not False:
        errors.append(f"{label}: prior source_run_authorized must be false")
    if successor.get("source_run_authorized") is not True:
        errors.append(f"{label}: successor source_run_authorized must be true")
    if prior_validation.get("source_feasibility_only") is not True or successor.get("source_feasibility_only") is not True:
        errors.append(f"{label}: source_feasibility_only must remain true")
    if prior_validation.get("source_feasibility_attempt_limit") != 1 or successor.get("source_feasibility_attempt_limit") != 1:
        errors.append(f"{label}: source feasibility attempt limit must remain exactly one")
    for key, expected in SOURCE_ONLY_REQUIRED_REVIEW_STATUS.items():
        if successor.get(key) != expected:
            errors.append(f"{label}: {key} must be PASS")
    for key in SOURCE_ONLY_FALSE_FIELDS:
        if successor.get(key) is not False:
            errors.append(f"{label}: {key} must be false")
    if "source_run_bindings" in successor:
        errors.append(f"{label}: HYP007-only source_run_bindings is forbidden")

    metrics = row.get("metrics")
    if (
        row.get("model") is not None
        or row.get("source_path") is not None
        or row.get("source_hash") is not None
        or row.get("run_ids") != []
        or not isinstance(metrics, dict)
    ):
        errors.append(f"{label}: source-only authority requires null model/source and no run ids")
    elif any(metrics.get(key) != expected for key, expected in SOURCE_ONLY_ZERO_METRICS.items()):
        errors.append(f"{label}: source/economic/runtime counters must remain exact zero")

    ea_name = str(row.get("ea_name") or "")
    research_prefix = f"03. EA Developer/{ea_name}/research/"
    builder_path_value = successor.get("reviewed_builder_path")
    test_path_value = successor.get("reviewed_test_path")
    receipt_path_value = successor.get("independent_review_receipt_path")
    evidence_root_value = successor.get("source_feasibility_evidence_root")
    if not isinstance(builder_path_value, str) or not builder_path_value.startswith(research_prefix) or not builder_path_value.endswith(".py"):
        errors.append(f"{label}: reviewed builder path must be a Python file in canonical package research")
    if not isinstance(test_path_value, str) or not test_path_value.startswith(research_prefix + "tests/") or not test_path_value.endswith(".py"):
        errors.append(f"{label}: reviewed test path must be a Python file in canonical package research/tests")
    if not isinstance(receipt_path_value, str) or not receipt_path_value.startswith(research_prefix) or not receipt_path_value.endswith(".json"):
        errors.append(f"{label}: independent review receipt must be package-local JSON")
    if not isinstance(evidence_root_value, str) or not evidence_root_value.startswith(research_prefix + "evidence/"):
        errors.append(f"{label}: evidence root must be inside canonical package research/evidence")
    attempt_id = successor.get("source_feasibility_attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id or not str(evidence_root_value).endswith("/" + attempt_id):
        errors.append(f"{label}: evidence root must end in the exact non-empty attempt id")

    builder_path = _source_only_safe_regular_path(builder_path_value, f"{label}.reviewed_builder_path", errors)
    test_path = _source_only_safe_regular_path(test_path_value, f"{label}.reviewed_test_path", errors)
    receipt_path = _source_only_safe_regular_path(receipt_path_value, f"{label}.independent_review_receipt_path", errors)
    builder_base_sha = _reviewed_base_source_sha256(builder_path, label, errors) if builder_path is not None else None
    expected_builder_sha = successor.get("reviewed_builder_base_sha256")
    if not isinstance(expected_builder_sha, str) or re.fullmatch(r"[A-F0-9]{64}", expected_builder_sha) is None or builder_base_sha != expected_builder_sha:
        errors.append(f"{label}: reviewed builder base SHA256 mismatch")
    expected_test_sha = successor.get("reviewed_test_sha256")
    if not isinstance(expected_test_sha, str) or re.fullmatch(r"[A-F0-9]{64}", expected_test_sha) is None or test_path is None or sha256_file(test_path) != expected_test_sha:
        errors.append(f"{label}: reviewed test SHA256 mismatch")
    expected_receipt_sha = successor.get("independent_review_receipt_sha256")
    if not isinstance(expected_receipt_sha, str) or re.fullmatch(r"[A-F0-9]{64}", expected_receipt_sha) is None or receipt_path is None or sha256_file(receipt_path) != expected_receipt_sha:
        errors.append(f"{label}: independent review receipt SHA256 mismatch")

    receipt_schema = successor.get("independent_review_receipt_schema")
    if not isinstance(receipt_schema, str) or re.fullmatch(r"[a-z0-9_.-]{3,120}", receipt_schema) is None:
        errors.append(f"{label}: independent review receipt schema is invalid")
    if receipt_path is not None:
        try:
            receipt = load_strict_json(receipt_path)
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{label}: independent review receipt is invalid: {exc}")
        else:
            expected_receipt = {
                "schema_version": receipt_schema,
                "hypothesis_id": hypothesis_id,
                "review_status": "PASS",
                "reviewed_builder": {"path": builder_path_value, "base_sha256": expected_builder_sha},
                "reviewed_tests": {"path": test_path_value, "sha256": expected_test_sha},
                "v1_plan": {"path": row.get("prereg_path"), "sha256": row.get("prereg_sha256")},
                "permissions": {
                    "source_feasibility_run": True,
                    "performance_or_economics": False,
                    "mt5_or_mql5": False,
                },
            }
            if receipt != expected_receipt:
                errors.append(f"{label}: independent review receipt contract mismatch")

    return errors


def _validate_generic_source_root_absent(
    row: dict[str, Any], line: int, errors: list[str]
) -> None:
    validation = row.get("validation")
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} source-only authority transition"
    root_value = validation.get("source_feasibility_evidence_root") if isinstance(validation, dict) else None
    root = normalized_workspace_path(root_value, f"{label}.source_feasibility_evidence_root", errors)
    if root is not None and os.path.lexists(root):
        errors.append(f"{label}: source feasibility evidence root must be absent before authorization")


def _generic_source_only_completion_errors(
    prior: dict[str, Any], line: int, row: dict[str, Any]
) -> list[str]:
    hypothesis_id = str(row.get("hypothesis_id") or "<unknown>")
    label = f"line {line} {hypothesis_id} source-only completion transition"
    errors: list[str] = []
    prior_validation = prior.get("validation")
    successor = row.get("validation")
    prior_metrics = prior.get("metrics")
    metrics = row.get("metrics")
    if prior.get("state") != "probe" or row.get("state") != "probe":
        errors.append(f"{label}: transition must be probe->probe")
    if not isinstance(prior_validation, dict) or not isinstance(successor, dict):
        errors.append(f"{label}: validation objects are required")
        return errors
    if prior_validation.get("source_run_authorized") is not True:
        errors.append(f"{label}: prior source_run_authorized must be true")
    if successor.get("source_run_authorized") is not False:
        errors.append(f"{label}: successor source_run_authorized must be false")
    if successor.get("source_build_authorized") is not False:
        errors.append(f"{label}: successor source_build_authorized must remain false")
    if "source_run_bindings" in successor:
        errors.append(f"{label}: HYP007-only source_run_bindings is forbidden")
    for key in set(prior) | set(row):
        if key not in SOURCE_ONLY_COMPLETION_ALLOWED_ROOT_CHANGES and prior.get(key) != row.get(key):
            errors.append(f"{label}: prohibited root change '{key}'")
    allowed_validation_keys = set(prior_validation) | SOURCE_ONLY_COMPLETION_ALLOWED_VALIDATION_ADDITIONS
    if not set(successor).issubset(allowed_validation_keys):
        errors.append(f"{label}: validation field set contains non-source-completion additions")
    for key in prior_validation:
        if key in {"probe_status", "source_build_authorized", "source_run_authorized"}:
            continue
        if successor.get(key) != prior_validation.get(key):
            errors.append(f"{label}: prohibited validation change '{key}'")
    for key in SOURCE_ONLY_FALSE_FIELDS:
        if successor.get(key) is not False:
            errors.append(f"{label}: {key} must remain false")
    if row.get("run_ids") != [successor.get("source_feasibility_attempt_id")]:
        errors.append(f"{label}: run_ids must contain exactly the source-feasibility attempt id")
    if not isinstance(prior_metrics, dict) or not isinstance(metrics, dict):
        errors.append(f"{label}: metrics objects are required")
    else:
        for key in SOURCE_ONLY_ZERO_METRICS:
            if key in {"source_feasibility_attempts_consumed", "source_runs_executed"}:
                continue
            if metrics.get(key) != SOURCE_ONLY_ZERO_METRICS[key]:
                errors.append(f"{label}: {key} must remain {SOURCE_ONLY_ZERO_METRICS[key]!r}")
        if metrics.get("source_feasibility_attempts_consumed") != 1 or metrics.get("source_runs_executed") != 1:
            errors.append(f"{label}: source attempt counters must both be 1")
    if successor.get("source_feasibility_verdict") != "PASS_SOURCE_FEASIBILITY":
        errors.append(f"{label}: source_feasibility_verdict must be PASS_SOURCE_FEASIBILITY")
    if successor.get("source_feasibility_result_valid") is not True:
        errors.append(f"{label}: source_feasibility_result_valid must be true")
    if successor.get("economic_edge_evaluated") is not False or successor.get("market_no_edge_claim_authorized") is not False:
        errors.append(f"{label}: economics and market no-edge claims must remain false")

    artifact_pairs = (
        ("attempt_started_path", "attempt_started_sha256"),
        ("attempt_terminal_path", "attempt_terminal_sha256"),
        ("source_report_path", "source_report_sha256"),
        ("source_ledger_path", "source_ledger_sha256"),
        ("source_feasibility_receipt_path", "source_feasibility_receipt_sha256"),
    )
    for path_key, sha_key in artifact_pairs:
        path_value = successor.get(path_key)
        expected_sha = successor.get(sha_key)
        artifact = normalized_workspace_path(path_value, f"{label}.{path_key}", errors)
        if not isinstance(expected_sha, str) or re.fullmatch(r"[A-F0-9]{64}", expected_sha) is None:
            errors.append(f"{label}: {sha_key} must be uppercase SHA256")
            continue
        if artifact is not None:
            info = artifact.stat() if artifact.exists() else None
            if info is None or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                errors.append(f"{label}: {path_key} must be a single-link regular file")
            elif sha256_file(artifact) != expected_sha:
                errors.append(f"{label}: {sha_key} mismatch")
    return errors


def _g10_xmom_export_to_eval_transition_errors(
    prior: dict[str, Any], line: int, row: dict[str, Any]
) -> list[str]:
    label = f"line {line} {G10_XMOM_HYP002_ID} export-to-eval transition"
    errors: list[str] = []
    prior_validation = prior.get("validation")
    successor = row.get("validation")
    prior_metrics = prior.get("metrics")
    metrics = row.get("metrics")
    if prior.get("state") != "probe" or row.get("state") != "probe":
        errors.append(f"{label}: transition must be probe->probe")
    if not isinstance(prior_validation, dict) or not isinstance(successor, dict):
        errors.append(f"{label}: validation objects are required")
        return errors
    for key in set(prior) | set(row):
        if key not in G10_XMOM_EXPORT_TO_EVAL_ROOT_CHANGES and prior.get(key) != row.get(key):
            errors.append(f"{label}: prohibited root change '{key}'")
    allowed_validation = (
        set(prior_validation)
        | G10_XMOM_EXPORT_TO_EVAL_VALIDATION_ADDITIONS
    )
    if not set(successor).issubset(allowed_validation):
        errors.append(f"{label}: unexpected validation additions")
    for key in prior_validation:
        if key in G10_XMOM_EXPORT_TO_EVAL_VALIDATION_CHANGES:
            continue
        if successor.get(key) != prior_validation.get(key):
            errors.append(f"{label}: prohibited validation change '{key}'")
    required_prior = {
        "train_export_authorized": True,
        "train_acquisition_authorized": True,
        "train_economics_authorized": False,
        "holdout_access_authorized": False,
        "one_use": True,
    }
    required_successor = {
        "train_export_authorized": False,
        "train_acquisition_authorized": False,
        "train_price_data_acquisition_authorized": False,
        "train_source_run_authorized": False,
        "mt5_authorized": False,
        "train_evaluate_authorized": True,
        "train_economics_authorized": True,
        "performance_metrics_authorized": True,
        "economics_authorized": True,
        "holdout_access_authorized": False,
        "promotion_authorized": False,
        "one_use": True,
    }
    for key, expected in required_prior.items():
        if prior_validation.get(key) is not expected:
            errors.append(f"{label}: prior {key} must be {expected!r}")
    for key, expected in required_successor.items():
        if successor.get(key) is not expected:
            errors.append(f"{label}: successor {key} must be {expected!r}")
    if row.get("verdict") != "FROZEN_ONE_SHOT_TRAIN_EVALUATION_AUTHORIZED":
        errors.append(f"{label}: verdict mismatch")
    if row.get("run_ids") != [G10_XMOM_EXPORT_ATTEMPT_ID]:
        errors.append(f"{label}: run_ids must contain the export attempt exactly once")
    if not isinstance(prior_metrics, dict) or not isinstance(metrics, dict):
        errors.append(f"{label}: metrics objects are required")
    else:
        expected_metrics = {
            "train_source_attempts_consumed": 1,
            "mt5_launches": 1,
            "w1_bars_read": 1456,
            "prices_read": 1456,
            "returns_computed": 0,
            "ranks_computed": 0,
            "signals_generated": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "outcomes_opened": 0,
            "performance_trials_executed": 0,
            "economics_executed": False,
            "research_holdout_opened": False,
        }
        for key, expected in expected_metrics.items():
            if metrics.get(key) != expected:
                errors.append(f"{label}: metric {key} must be {expected!r}")
    exact_paths = {
        "dataset_manifest_path": (
            "02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/"
            "HYP-G10-XMOM-W1-002/train_w1_manifest.json"
        ),
        "dataset_parquet_path": (
            "02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/"
            "HYP-G10-XMOM-W1-002/train_w1_bars.parquet"
        ),
        "train_export_receipt_path": (
            "03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/"
            "HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EXPORT-001/"
            "train_export_receipt.json"
        ),
    }
    for key, expected in exact_paths.items():
        if successor.get(key) != expected:
            errors.append(f"{label}: {key} mismatch")
    if successor.get("dataset_row_count") != 1456:
        errors.append(f"{label}: dataset_row_count must be 1456")
    for stem in ("dataset_manifest", "dataset_parquet", "train_export_receipt"):
        verify_binding(
            successor.get(f"{stem}_path"),
            successor.get(f"{stem}_sha256"),
            f"{label}.{stem}",
            errors,
        )
    if successor.get("train_eval_attempt_id") != "G10XMOM002-TRAIN-EVAL-001":
        errors.append(f"{label}: train_eval_attempt_id mismatch")
    return errors


def _validate_g10_xmom_eval_root_absent(
    row: dict[str, Any], line: int, errors: list[str]
) -> None:
    label = f"line {line} {G10_XMOM_HYP002_ID} latest evaluation authority"
    validation = row.get("validation")
    if not isinstance(validation, dict):
        errors.append(f"{label}: validation object is required")
        return
    eval_root = normalized_workspace_path(
        validation.get("train_eval_evidence_root"),
        f"{label}.train_eval_evidence_root",
        errors,
    )
    if eval_root is not None and os.path.lexists(eval_root):
        errors.append(f"{label}: train evaluation evidence root must be absent")


def _trilag_export_to_structure_transition_errors(
    prior: dict[str, Any], line: int, row: dict[str, Any]
) -> list[str]:
    label = f"line {line} {TRILAG_HYP002_ID} export-to-structure transition"
    errors: list[str] = []
    prior_validation = prior.get("validation")
    successor = row.get("validation")
    metrics = row.get("metrics")
    if prior.get("state") != "probe" or row.get("state") != "probe":
        errors.append(f"{label}: transition must be probe->probe")
    if not isinstance(prior_validation, dict) or not isinstance(successor, dict):
        errors.append(f"{label}: validation objects are required")
        return errors
    for key in set(prior) | set(row):
        if (
            key not in TRILAG_EXPORT_TO_STRUCTURE_ROOT_CHANGES
            and prior.get(key) != row.get(key)
        ):
            errors.append(f"{label}: prohibited root change '{key}'")
    allowed_validation = (
        set(prior_validation) | TRILAG_EXPORT_TO_STRUCTURE_VALIDATION_ADDITIONS
    )
    if set(successor) != allowed_validation:
        errors.append(f"{label}: validation field set must be exact")
    for key in prior_validation:
        if key in TRILAG_EXPORT_TO_STRUCTURE_VALIDATION_CHANGES:
            continue
        if successor.get(key) != prior_validation.get(key):
            errors.append(f"{label}: prohibited validation change '{key}'")
    required_prior = {
        "design_export_run_authorized": True,
        "design_structure_evaluation_authorized": False,
        "mt5_authorized": True,
        "one_use": True,
    }
    required_successor = {
        "design_export_run_authorized": False,
        "design_structure_evaluation_authorized": True,
        "mt5_authorized": False,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "research_validation_access_authorized": False,
        "research_holdout_access_authorized": False,
        "one_use": True,
    }
    for key, expected in required_prior.items():
        if prior_validation.get(key) is not expected:
            errors.append(f"{label}: prior {key} must be {expected!r}")
    for key, expected in required_successor.items():
        if successor.get(key) is not expected:
            errors.append(f"{label}: successor {key} must be {expected!r}")
    if row.get("verdict") != "FROZEN_DESIGN_STRUCTURE_EVALUATION_AUTHORIZED":
        errors.append(f"{label}: verdict mismatch")
    if row.get("run_ids") != [TRILAG_EXPORT_ATTEMPT_ID]:
        errors.append(f"{label}: run_ids must contain the export attempt exactly once")
    expected_metrics = {
        "design_export_attempt_limit": 1,
        "design_export_attempts_consumed": 1,
        "design_structure_attempt_limit": 1,
        "design_structure_attempts_consumed": 0,
        "source_runs_executed": 1,
        "bars_read": 5580755,
        "timestamps_read": 5580755,
        "prices_read": 5580755,
        "returns_computed": 0,
        "residuals_computed": 0,
        "raw_events_generated": 0,
        "accepted_events_generated": 0,
        "signals_generated": 0,
        "post_decision_bars_read": 0,
        "trades_simulated": 0,
        "costs_computed": 0,
        "outcomes_opened": 0,
        "performance_trials_executed": 0,
        "economics_executed": False,
        "model0_runs": 0,
        "model4_runs": 0,
        "mt5_launches": 1,
        "mql5_files_created": 0,
        "network_calls": 0,
        "paid_requests_made": 0,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }
    if metrics != expected_metrics:
        errors.append(f"{label}: metrics must exactly reconcile the one export")
    exact_paths = {
        "dataset_manifest_path": (
            "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
            "HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json"
        ),
        "dataset_parquet_path": (
            "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
            "HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet"
        ),
        "design_export_attempt_started_path": (
            "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
            "HYP-TRILAG-EURJPY-M1-002/TRILAG002-DESIGN-EXPORT-001/attempt_started.json"
        ),
        "design_export_receipt_path": (
            "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
            "HYP-TRILAG-EURJPY-M1-002/TRILAG002-DESIGN-EXPORT-001/"
            "design_export_receipt.json"
        ),
        "design_export_reconciliation_receipt_path": (
            "03. EA Developer/EA_TriangularConsensusLag/research/"
            "HYP-TRILAG-EURJPY-M1-002_DESIGN_EXPORT_RECONCILIATION_RECEIPT.json"
        ),
        "design_structure_evidence_root": (
            "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
            "HYP-TRILAG-EURJPY-M1-002/TRILAG002-DESIGN-STRUCTURE-001"
        ),
    }
    for key, expected in exact_paths.items():
        if successor.get(key) != expected:
            errors.append(f"{label}: {key} mismatch")
    if successor.get("dataset_row_count") != 5580755:
        errors.append(f"{label}: dataset_row_count mismatch")
    for stem in (
        "dataset_manifest",
        "dataset_parquet",
        "design_export_attempt_started",
        "design_export_receipt",
        "design_export_reconciliation_receipt",
    ):
        verify_binding(
            successor.get(f"{stem}_path"),
            successor.get(f"{stem}_sha256"),
            f"{label}.{stem}",
            errors,
        )
    if successor.get("design_structure_attempt_id") != "TRILAG002-DESIGN-STRUCTURE-001":
        errors.append(f"{label}: design_structure_attempt_id mismatch")
    if (
        successor.get("registry_validator_path") == TRILAG_REGISTRY_VALIDATOR_PATH
        and successor.get("registry_validator_sha256") == TRILAG_REGISTRY_VALIDATOR_SHA256
    ):
        normalized_workspace_path(
            successor.get("registry_validator_path"),
            f"{label}.registry_validator",
            errors,
        )
    else:
        verify_binding(
            successor.get("registry_validator_path"),
            successor.get("registry_validator_sha256"),
            f"{label}.registry_validator",
            errors,
        )
    return errors


def _validate_trilag_structure_root_absent(
    row: dict[str, Any], line: int, errors: list[str]
) -> None:
    label = f"line {line} {TRILAG_HYP002_ID} latest structural authority"
    validation = row.get("validation")
    if not isinstance(validation, dict):
        errors.append(f"{label}: validation object is required")
        return
    root = normalized_workspace_path(
        validation.get("design_structure_evidence_root"),
        f"{label}.design_structure_evidence_root",
        errors,
    )
    if root is not None and os.path.lexists(root):
        errors.append(f"{label}: structural evidence root must be absent")


def _generic_initial_source_only_authority_errors(
    line: int, row: dict[str, Any]
) -> list[str]:
    synthetic_prior = copy.deepcopy(row)
    prior_validation = synthetic_prior.get("validation")
    if not isinstance(prior_validation, dict):
        return [f"line {line}: source-only authority validation object is required"]
    for key in SOURCE_ONLY_ALLOWED_VALIDATION_ADDITIONS:
        prior_validation.pop(key, None)
    prior_validation["source_build_authorized"] = True
    prior_validation["source_run_authorized"] = False
    prior_validation["probe_status"] = "SYNTHETIC_PRE_REVIEW_SOURCE_BUILD_ONLY"
    return _generic_source_only_authority_transition_errors(synthetic_prior, line, row)


def _hyp007_initial_source_run_transition_errors(
    prior_line: int,
    prior_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    label = f"line {line} {HYP007_ID} source-run transition"
    errors: list[str] = []
    if prior_line != HYP007_PRIOR_ROW_INDEX or prior_sha256 != HYP007_PRIOR_ROW_SHA256:
        errors.append(f"{label}: prior row identity is not exact row 285")
    if prior.get("hypothesis_id") != HYP007_ID or row.get("hypothesis_id") != HYP007_ID:
        errors.append(f"{label}: exception is HYP007-only")
    if prior.get("state") != "probe" or row.get("state") != "probe":
        errors.append(f"{label}: transition must be probe->probe")
    if set(prior) != set(row):
        errors.append(f"{label}: root field set changed")
    for key in set(prior) | set(row):
        if key not in HYP007_ALLOWED_ROOT_CHANGES and prior.get(key) != row.get(key):
            errors.append(f"{label}: prohibited root change '{key}'")
    prior_validation = prior.get("validation")
    successor_validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(successor_validation, dict):
        errors.append(f"{label}: validation objects are required")
        return errors
    if set(successor_validation) != set(prior_validation) | {"source_run_bindings"}:
        errors.append(f"{label}: validation field set is not the exact V2 successor set")
    for key in set(prior_validation) | set(successor_validation):
        if key not in HYP007_ALLOWED_VALIDATION_CHANGES and prior_validation.get(key) != successor_validation.get(key):
            errors.append(f"{label}: prohibited validation change '{key}'")
    if prior_validation.get("source_build_authorized") is not True or successor_validation.get("source_build_authorized") is not True:
        errors.append(f"{label}: source_build_authorized must remain true")
    if prior_validation.get("source_run_authorized") is not False:
        errors.append(f"{label}: prior source_run_authorized must be false")
    if successor_validation.get("source_run_authorized") is not True:
        errors.append(f"{label}: successor source_run_authorized must be true")
    if successor_validation.get("probe_status") != "FROZEN_ONE_SHOT_SOURCE_PROJECTION_AUTHORIZED_PRE_PAYLOAD":
        errors.append(f"{label}: successor probe_status mismatch")
    if row.get("verdict") != "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED":
        errors.append(f"{label}: successor verdict mismatch")
    if not isinstance(successor_validation.get("source_run_bindings"), dict):
        errors.append(f"{label}: source_run_bindings is required")
    return errors


def _hyp007_repair_transition_errors(
    prior_line: int,
    prior_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    label = f"line {line} {HYP007_ID} pre-arm disarm repair transition"
    errors: list[str] = []
    if (
        prior_line != HYP007_AUTHORIZED_ROW_INDEX
        or prior_sha256 != HYP007_AUTHORIZED_ROW_SHA256
    ):
        errors.append(f"{label}: prior row identity is not exact row 286")
    if prior.get("hypothesis_id") != HYP007_ID or row.get("hypothesis_id") != HYP007_ID:
        errors.append(f"{label}: exception is HYP007-only")
    if prior.get("state") != "probe" or row.get("state") != "probe":
        errors.append(f"{label}: transition must be probe->probe")
    if set(prior) != set(row):
        errors.append(f"{label}: root field set changed")
    for key in set(prior) | set(row):
        if key not in HYP007_ALLOWED_ROOT_CHANGES and prior.get(key) != row.get(key):
            errors.append(f"{label}: prohibited root change '{key}'")

    prior_validation = prior.get("validation")
    successor_validation = row.get("validation")
    if not isinstance(prior_validation, dict) or not isinstance(successor_validation, dict):
        errors.append(f"{label}: validation objects are required")
        return errors
    if set(successor_validation) != set(prior_validation):
        errors.append(f"{label}: validation field set changed")
    for key in set(prior_validation) | set(successor_validation):
        if (
            key not in HYP007_REPAIR_ALLOWED_VALIDATION_CHANGES
            and prior_validation.get(key) != successor_validation.get(key)
        ):
            errors.append(f"{label}: prohibited validation change '{key}'")
    if (
        prior_validation.get("source_build_authorized") is not True
        or successor_validation.get("source_build_authorized") is not True
        or prior_validation.get("source_run_authorized") is not True
        or successor_validation.get("source_run_authorized") is not True
    ):
        errors.append(f"{label}: source build/run authorization must remain true")
    if successor_validation.get("probe_status") != (
        "FROZEN_ONE_SHOT_SOURCE_PROJECTION_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    ):
        errors.append(f"{label}: successor probe_status mismatch")
    if row.get("verdict") != (
        "FROZEN_SINGLE_1200_BAR_SOURCE_RUN_AUTHORIZED_AFTER_PREARM_DISARM_REPAIR"
    ):
        errors.append(f"{label}: successor verdict mismatch")

    prior_bindings = prior_validation.get("source_run_bindings")
    successor_bindings = successor_validation.get("source_run_bindings")
    if not isinstance(prior_bindings, dict) or not isinstance(successor_bindings, dict):
        errors.append(f"{label}: both source_run_bindings objects are required")
        return errors
    if set(prior_bindings) != set(successor_bindings):
        errors.append(f"{label}: source_run_bindings field set changed")
    changed = {
        key
        for key in set(prior_bindings) | set(successor_bindings)
        if prior_bindings.get(key) != successor_bindings.get(key)
    }
    if changed != HYP007_REPAIR_BINDING_CHANGES:
        errors.append(
            f"{label}: binding changes must be exactly {sorted(HYP007_REPAIR_BINDING_CHANGES)}"
        )
    if (
        successor_bindings.get("implementation_review_receipt_path")
        != HYP007_RECEIPT_V6_PATH
        or successor_bindings.get("implementation_task_path") != HYP007_TASK_V6_PATH
        or successor_bindings.get("implementation_task_sha256") != HYP007_TASK_V6_SHA256
    ):
        errors.append(f"{label}: repaired receipt/task V6 binding mismatch")

    metrics = row.get("metrics")
    if (
        row.get("model") is not None
        or row.get("source_path") is not None
        or row.get("source_hash") is not None
        or row.get("run_ids") != []
        or not isinstance(metrics, dict)
        or metrics.get("source_projection_attempts_consumed") != 0
        or metrics.get("source_content_opened") is not False
        or metrics.get("research_price_rows_opened") != 0
        or metrics.get("economics_opened") is not False
        or metrics.get("performance_trials_executed") != 0
        or metrics.get("research_validation_opened") is not False
        or metrics.get("research_holdout_opened") is not False
    ):
        errors.append(f"{label}: repair requires zero attempts/payload/economics and null source/model")
    return errors


def _validate_hyp007_repair_roots_absent(
    row: dict[str, Any], line: int, errors: list[str]
) -> None:
    label = f"line {line} {HYP007_ID} pre-arm disarm repair transition"
    validation = row.get("validation")
    bindings = validation.get("source_run_bindings") if isinstance(validation, dict) else None
    if not isinstance(bindings, dict):
        errors.append(f"{label}: source_run_bindings is required for root absence checks")
        return
    for root_key in ("stage_root", "final_output_root", "evidence_root"):
        root = normalized_workspace_path(bindings.get(root_key), f"{label}.{root_key}", errors)
        if root is not None and os.path.lexists(root):
            errors.append(f"{label}: {root_key} must remain absent before repair")


def _hyp007_source_run_transition_errors(
    prior_line: int,
    prior_sha256: str,
    prior: dict[str, Any],
    line: int,
    row: dict[str, Any],
) -> list[str]:
    if prior_line == HYP007_PRIOR_ROW_INDEX:
        return _hyp007_initial_source_run_transition_errors(
            prior_line, prior_sha256, prior, line, row
        )
    if prior_line == HYP007_AUTHORIZED_ROW_INDEX:
        return _hyp007_repair_transition_errors(
            prior_line, prior_sha256, prior, line, row
        )
    return [
        f"line {line} {HYP007_ID} source-run transition: no exact one-use exception for prior row {prior_line}"
    ]


def validate_source_run_bindings(
    row: dict[str, Any],
    line: int,
    row_sha256: str,
    errors: list[str],
) -> None:
    validation = row.get("validation")
    bindings = validation.get("source_run_bindings") if isinstance(validation, dict) else None
    if not isinstance(bindings, dict):
        return
    label = f"line {line} {HYP007_ID} source_run_bindings"
    historical_row286 = (
        line == HYP007_AUTHORIZED_ROW_INDEX
        and row_sha256 == HYP007_AUTHORIZED_ROW_SHA256
    )
    for key, value in bindings.items():
        if key.endswith("_path") or key.endswith("_root"):
            normalized_workspace_path(value, f"{label}.{key}", errors)
    for path_key, hash_key in SOURCE_RUN_EXISTING_FILE_BINDINGS:
        if historical_row286 and path_key == "supervisor_test_path":
            continue
        verify_binding(bindings.get(path_key), bindings.get(hash_key), f"{label}.{path_key}", errors)
    if (
        bindings.get("authority_amendment_path") != HYP007_AMENDMENT_V2_PATH
        or bindings.get("authority_amendment_sha256") != HYP007_AMENDMENT_V2_SHA256
    ):
        errors.append(f"{label}: Amendment V2 path/SHA mismatch")
    v5_pair = (
        bindings.get("implementation_review_receipt_path") == HYP007_RECEIPT_V5_PATH
        and bindings.get("implementation_task_path") == HYP007_TASK_V5_PATH
        and bindings.get("implementation_task_sha256") == HYP007_TASK_V5_SHA256
    )
    v6_pair = (
        bindings.get("implementation_review_receipt_path") == HYP007_RECEIPT_V6_PATH
        and bindings.get("implementation_task_path") == HYP007_TASK_V6_PATH
        and bindings.get("implementation_task_sha256") == HYP007_TASK_V6_SHA256
    )
    if not (v5_pair or v6_pair):
        errors.append(f"{label}: receipt/task paths must be the exact V5 pair or exact V6 repair pair")
    verify_binding(
        HYP007_AMENDMENT_V3_PATH,
        HYP007_AMENDMENT_V3_SHA256,
        f"{label}.authority_amendment_v3",
        errors,
    )
    if v6_pair:
        verify_binding(
            HYP007_REPAIR_AMENDMENT_V4_PATH,
            HYP007_REPAIR_AMENDMENT_V4_SHA256,
            f"{label}.authority_repair_amendment_v4",
            errors,
        )
        verify_binding(
            HYP007_TASK_V6_PATH,
            HYP007_TASK_V6_SHA256,
            f"{label}.implementation_task_v6",
            errors,
        )
    supervisor_path = resolve_workspace_path(
        bindings.get("supervisor_tool_path"), f"{label}.supervisor_tool_path", errors
    )
    review_base = bindings.get("supervisor_review_base_sha256")
    if not isinstance(review_base, str) or re.fullmatch(r"[A-F0-9]{64}", review_base) is None:
        errors.append(f"{label}: supervisor_review_base_sha256 is invalid")
    elif supervisor_path is not None and not historical_row286:
        payload = supervisor_path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest().upper()
        sentinel = b"REVIEWED_SOURCE_RUN_PACKET_SHA256" + b": str | None = None"
        armed = re.compile(rb'REVIEWED_SOURCE_RUN_PACKET_SHA256: str \| None = "[A-F0-9]{64}"')
        if actual != review_base:
            errors.append(f"{label}: disarmed supervisor review-base SHA256 mismatch")
        if payload.count(sentinel) != 1 or armed.search(payload) is not None:
            errors.append(f"{label}: supervisor review-base is not exact disarmed source")


def validate_registry(registry: Path, schema_path: Path) -> list[str]:
    errors: list[str] = []
    if not registry.is_file():
        return [f"registry is missing: {registry}"]
    if not schema_path.is_file():
        return [f"schema is missing: {schema_path}"]
    try:
        schema = load_strict_json(schema_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
    except Exception as exc:
        return [f"schema is invalid: {exc}"]

    latest: dict[str, tuple[int, dict[str, Any], datetime, str]] = {}
    parsed_rows: list[tuple[int, dict[str, Any], str]] = []
    valid_source_run_transition_lines: set[int] = set()
    valid_source_run_repair_lines: set[int] = set()
    valid_generic_source_authority_lines: dict[str, int] = {}
    rows = 0
    records = registry.read_bytes().splitlines(keepends=True)
    for line_number, record in enumerate(records, 1):
        if not record.endswith(b"\n") or record.count(b"\n") != 1:
            errors.append(f"line {line_number}: registry rows require exactly one terminal LF")
            continue
        body = record[:-1]
        try:
            raw = body.decode("utf-8-sig" if line_number == 1 else "utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            errors.append(f"line {line_number}: invalid UTF-8: {exc}")
            continue
        if not raw.strip():
            errors.append(f"line {line_number}: blank rows are forbidden")
            continue
        rows += 1
        try:
            row = json.loads(
                raw,
                parse_constant=reject_nonfinite,
                object_pairs_hook=reject_duplicate_keys,
            )
        except Exception as exc:
            errors.append(f"line {line_number}: invalid strict JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: row root must be an object")
            continue
        issues = sorted(validator.iter_errors(row), key=lambda item: str(list(item.path)))
        for issue in issues:
            location = ".".join(str(part) for part in issue.path) or "<root>"
            errors.append(f"line {line_number} {location}: {issue.message}")
        if issues:
            continue
        timestamp = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
        row_sha256 = hashlib.sha256(body).hexdigest().upper()
        hypothesis_id = row["hypothesis_id"]
        parsed_rows.append((line_number, row, row_sha256))
        if hypothesis_id in latest:
            prior_line, prior, prior_timestamp, prior_sha256 = latest[hypothesis_id]
            for invariant in ("ea_name", "parent_candidate", "feature_family", "lane", "symbol", "timeframe"):
                if row[invariant] != prior[invariant]:
                    errors.append(
                        f"line {line_number} {hypothesis_id}: invariant '{invariant}' changed from line {prior_line}"
                    )
            if timestamp <= prior_timestamp:
                errors.append(f"line {line_number} {hypothesis_id}: timestamp must increase")
            prior_state = prior["state"]
            if prior_state != "idea":
                for frozen in ("window", "model", "exact_overrides", "acceptance_contract"):
                    if row[frozen] != prior[frozen]:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: frozen '{frozen}' changed from line {prior_line}"
                        )
                if (
                    timestamp >= PROBE_PREREG_ENFORCEMENT_START
                    and prior.get("prereg_path") is not None
                ):
                    for frozen in ("prereg_path", "prereg_sha256"):
                        if row[frozen] != prior[frozen]:
                            errors.append(
                                f"line {line_number} {hypothesis_id}: bound prereg '{frozen}' changed after "
                                f"leaving idea (amend pre-outcome as _V2 at the idea->probe transition only)"
                            )
            if prior_state in EXECUTION_STATES:
                for frozen in ("source_path", "source_hash", "prereg_path", "prereg_sha256"):
                    if row[frozen] != prior[frozen]:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: execution-bound '{frozen}' changed from line {prior_line}"
                        )
            exception_applies = False
            if hypothesis_id == HYP007_ID and prior_state == "probe" and row["state"] == "probe":
                transition_errors = _hyp007_source_run_transition_errors(
                    prior_line, prior_sha256, prior, line_number, row
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row, sort_keys=False, separators=(",", ":"), ensure_ascii=True, allow_nan=False
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: authority successor must use compact insertion-order JSON"
                        )
                        exception_applies = False
                    else:
                        valid_source_run_transition_lines.add(line_number)
                        if prior_line == HYP007_AUTHORIZED_ROW_INDEX:
                            valid_source_run_repair_lines.add(line_number)
            elif prior_state == "probe" and row["state"] == "probe":
                prior_validation = prior.get("validation")
                successor_validation = row.get("validation")
                if (
                    hypothesis_id == TRILAG_HYP002_ID
                    and isinstance(prior_validation, dict)
                    and isinstance(successor_validation, dict)
                    and prior_validation.get("design_export_run_authorized") is True
                    and successor_validation.get("design_structure_evaluation_authorized") is True
                ):
                    transition_errors = _trilag_export_to_structure_transition_errors(
                        prior, line_number, row
                    )
                elif (
                    hypothesis_id == G10_XMOM_HYP002_ID
                    and isinstance(prior_validation, dict)
                    and isinstance(successor_validation, dict)
                    and prior_validation.get("train_export_authorized") is True
                    and successor_validation.get("train_evaluate_authorized") is True
                ):
                    transition_errors = _g10_xmom_export_to_eval_transition_errors(
                        prior, line_number, row
                    )
                elif (
                    isinstance(prior_validation, dict)
                    and isinstance(successor_validation, dict)
                    and prior_validation.get("source_run_authorized") is True
                    and successor_validation.get("source_run_authorized") is False
                ):
                    transition_errors = _generic_source_only_completion_errors(
                        prior, line_number, row
                    )
                else:
                    transition_errors = _generic_source_only_authority_transition_errors(
                        prior, line_number, row
                    )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: source-only authority successor must use compact insertion-order JSON"
                        )
                        exception_applies = False
                    elif (
                        isinstance(successor_validation, dict)
                        and successor_validation.get("source_run_authorized") is True
                    ):
                        valid_generic_source_authority_lines[hypothesis_id] = line_number
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "engineering_receipt_correction_path" not in prior["validation"]
                and "engineering_receipt_correction_sha256" not in prior["validation"]
                and "engineering_receipt_correction_path" in row["validation"]
                and "engineering_receipt_correction_sha256" in row["validation"]
            ):
                transition_errors = _prelaunch_evidence_correction_errors(
                    prior,
                    line_number,
                    row,
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: prelaunch evidence correction must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "prepacket_control_plane_receipt_path" not in prior["validation"]
                and "prepacket_control_plane_receipt_sha256" not in prior["validation"]
                and "prepacket_control_plane_receipt_path" in row["validation"]
                and "prepacket_control_plane_receipt_sha256" in row["validation"]
            ):
                transition_errors = _prelaunch_packet_authorization_errors(
                    prior,
                    line_number,
                    row,
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: prelaunch packet authorization must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "prepacket_control_plane_receipt_correction_path"
                not in prior["validation"]
                and "prepacket_control_plane_receipt_correction_sha256"
                not in prior["validation"]
                and "prepacket_control_plane_receipt_correction_path"
                in row["validation"]
                and "prepacket_control_plane_receipt_correction_sha256"
                in row["validation"]
            ):
                transition_errors = _prelaunch_packet_scope_correction_errors(
                    prior,
                    line_number,
                    row,
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: prelaunch packet scope correction must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "prepacket_scope_validator_hardening_receipt_path"
                not in prior["validation"]
                and "prepacket_scope_validator_hardening_receipt_sha256"
                not in prior["validation"]
                and "prepacket_scope_validator_hardening_receipt_path"
                in row["validation"]
                and "prepacket_scope_validator_hardening_receipt_sha256"
                in row["validation"]
            ):
                transition_errors = _prelaunch_scope_validator_hardening_errors(
                    prior,
                    line_number,
                    row,
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: prelaunch scope validator hardening must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "packet_set_dry_run_receipt_path" not in prior["validation"]
                and "packet_set_dry_run_receipt_sha256" not in prior["validation"]
                and "packet_set_dry_run_receipt_path" in row["validation"]
                and "packet_set_dry_run_receipt_sha256" in row["validation"]
            ):
                transition_errors = (
                    _prelaunch_xau_model4_collection_authorization_errors(
                        prior_line,
                        prior_sha256,
                        hashlib.sha256(
                            b"".join(records[: line_number - 1])
                        ).hexdigest().upper(),
                        prior,
                        line_number,
                        row,
                    )
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: prelaunch XAU Model4 collection authorization must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "execute_gate_hardening_receipt_path"
                not in prior["validation"]
                and "execute_gate_hardening_receipt_sha256"
                not in prior["validation"]
                and "execute_gate_hardening_receipt_path"
                in row["validation"]
                and "execute_gate_hardening_receipt_sha256"
                in row["validation"]
            ):
                transition_errors = (
                    _prelaunch_xau_model4_execute_gate_hardening_errors(
                        prior_line,
                        prior_sha256,
                        hashlib.sha256(
                            b"".join(records[: line_number - 1])
                        ).hexdigest().upper(),
                        prior,
                        line_number,
                        row,
                    )
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: prelaunch XAU Model4 execute-gate hardening must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and prior["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED"
                and row["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
            ):
                transition_errors = (
                    _prelaunch_xau_model4_postlock_revalidation_errors(
                        prior_line,
                        prior_sha256,
                        hashlib.sha256(
                            b"".join(records[: line_number - 1])
                        ).hexdigest().upper(),
                        prior,
                        line_number,
                        row,
                    )
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: post-lock execute-gate revalidation must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and prior["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
                and row["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
            ):
                transition_errors = (
                    _prelaunch_xau_model4_targeted_bridge_errors(
                        prior_line,
                        prior_sha256,
                        hashlib.sha256(
                            b"".join(records[: line_number - 1])
                        ).hexdigest().upper(),
                        prior,
                        line_number,
                        row,
                    )
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: registry-lock targeted bridge must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and prior["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
                and row["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED"
            ):
                transition_errors = (
                    _prelaunch_xau_model4_registry_lock_full_suite_authorization_errors(
                        prior_line,
                        prior_sha256,
                        hashlib.sha256(
                            b"".join(records[: line_number - 1])
                        ).hexdigest().upper(),
                        prior,
                        line_number,
                        row,
                    )
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: registry-lock full-suite execute authorization must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state == "screened"
                and row["state"] == "screened"
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and prior["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
                and row["validation"].get("probe_status")
                == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
            ):
                transition_errors = (
                    _prelaunch_xau_model4_full_suite_authorization_errors(
                        prior_line,
                        prior_sha256,
                        hashlib.sha256(
                            b"".join(records[: line_number - 1])
                        ).hexdigest().upper(),
                        prior,
                        line_number,
                        row,
                    )
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: full-suite execute authorization must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                prior_state in TERMINAL_STATES
                and row["state"] == prior_state
                and isinstance(prior.get("validation"), dict)
                and isinstance(row.get("validation"), dict)
                and "source_snapshot_path" not in prior["validation"]
                and "source_snapshot_sha256" not in prior["validation"]
                and "source_snapshot_path" in row["validation"]
                and "source_snapshot_sha256" in row["validation"]
            ):
                transition_errors = _terminal_snapshot_amendment_errors(
                    prior,
                    line_number,
                    row,
                )
                errors.extend(transition_errors)
                exception_applies = not transition_errors
                if exception_applies:
                    compact = json.dumps(
                        row,
                        sort_keys=False,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    ).encode("utf-8")
                    if compact != body:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: terminal snapshot amendment must use compact insertion-order JSON"
                        )
                        exception_applies = False
            elif (
                hypothesis_id == ROUND_HYP001_ID
                and prior_state == "parked"
                and row["state"] == "parked"
                and prior_line == ROUND_HYP001_TERMINAL_PRIOR_LINE
                and prior_sha256 == ROUND_HYP001_TERMINAL_PRIOR_SHA256
                and line_number == ROUND_HYP001_TERMINAL_RECONCILIATION_LINE
                and row_sha256 == ROUND_HYP001_TERMINAL_RECONCILIATION_SHA256
            ):
                # Exact append-only reconciliation of two independently written
                # terminal records for the same engineering-invalid attempt.
                exception_applies = True
            if not exception_applies and row["state"] not in TRANSITIONS[prior_state]:
                errors.append(
                    f"line {line_number} {hypothesis_id}: illegal transition {prior_state}->{row['state']}"
                )
        latest[hypothesis_id] = (line_number, row, timestamp, row_sha256)

    terminal_snapshots: dict[str, dict[str, Any]] = {}
    for hypothesis_id, (_, row, _, _) in latest.items():
        if row.get("state") in TERMINAL_STATES and isinstance(row.get("validation"), dict):
            terminal_snapshots[hypothesis_id] = row["validation"]
    for line_number, row, row_sha256 in parsed_rows:
        validate_row_bindings(
            row,
            line_number,
            errors,
            terminal_snapshots.get(str(row.get("hypothesis_id") or "")),
        )
        validation = row.get("validation")
        if (
            row.get("hypothesis_id") != HYP007_ID
            and row.get("state") == "probe"
            and isinstance(validation, dict)
            and validation.get("source_run_authorized") is True
            and "reviewed_builder_base_sha256" in validation
            and "independent_review_receipt_schema" in validation
        ):
            authority_errors = _generic_initial_source_only_authority_errors(
                line_number, row
            )
            errors.extend(authority_errors)
            if not authority_errors:
                valid_generic_source_authority_lines[str(row["hypothesis_id"])] = line_number
        if isinstance(validation, dict) and "source_run_bindings" in validation:
            if line_number not in valid_source_run_transition_lines:
                errors.append(
                    f"line {line_number} {row.get('hypothesis_id')}: source_run_bindings is allowed only on the exact one-use HYP007 transition"
                )
            validate_source_run_bindings(row, line_number, row_sha256, errors)

    latest_hyp007 = latest.get(HYP007_ID)
    latest_hyp007_is_terminal_successor = bool(
        latest_hyp007 is not None
        and latest_hyp007[1].get("state") in TERMINAL_STATES
        and latest_hyp007[0] > max(valid_source_run_transition_lines, default=0)
        and "source_run_bindings" not in (latest_hyp007[1].get("validation") or {})
    )
    if valid_source_run_transition_lines and not (
        latest_hyp007 is not None
        and (
            latest_hyp007[0] in valid_source_run_transition_lines
            or latest_hyp007_is_terminal_successor
        )
    ):
        errors.append(
            "HYP007 source-run authorization successor must remain latest until a valid terminal successor"
        )
    if latest_hyp007 is not None and latest_hyp007[0] in valid_source_run_repair_lines:
        _validate_hyp007_repair_roots_absent(
            latest_hyp007[1], latest_hyp007[0], errors
        )
    for hypothesis_id, authority_line in valid_generic_source_authority_lines.items():
        latest_row = latest.get(hypothesis_id)
        if latest_row is not None and latest_row[0] == authority_line:
            _validate_generic_source_root_absent(latest_row[1], authority_line, errors)

    latest_g10_xmom = latest.get(G10_XMOM_HYP002_ID)
    if latest_g10_xmom is not None:
        latest_line, latest_row, _, _ = latest_g10_xmom
        latest_validation = latest_row.get("validation")
        if (
            latest_row.get("state") == "probe"
            and isinstance(latest_validation, dict)
            and latest_validation.get("train_evaluate_authorized") is True
        ):
            _validate_g10_xmom_eval_root_absent(
                latest_row, latest_line, errors
            )

    latest_trilag = latest.get(TRILAG_HYP002_ID)
    if latest_trilag is not None:
        latest_line, latest_row, _, _ = latest_trilag
        latest_validation = latest_row.get("validation")
        if (
            latest_row.get("state") == "probe"
            and isinstance(latest_validation, dict)
            and latest_validation.get("design_structure_evaluation_authorized") is True
        ):
            _validate_trilag_structure_root_absent(
                latest_row, latest_line, errors
            )

    latest_hyp005 = latest.get(HYP005_MODEL4_COLLECTION_ID)
    if latest_hyp005 is not None:
        latest_line, latest_row, _, _ = latest_hyp005
        latest_validation = latest_row.get("validation")
        latest_probe_status = (
            latest_validation.get("probe_status")
            if isinstance(latest_validation, dict)
            else None
        )
        if (
            latest_probe_status
            in {
                "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED",
                "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED",
                "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED",
                "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED",
                "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED",
            }
        ):
            _validate_latest_hyp005_execute_authority(
                latest_line,
                latest_row,
                errors,
            )
        elif (
            latest_probe_status
            == "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORIZED"
        ):
            runtime = WORKSPACE / "02. AlphaFactory/runtime"
            if runtime.is_dir():
                for receipt_path in runtime.glob("ea_execution_receipt_*.json"):
                    try:
                        receipt = load_strict_json(receipt_path)
                    except Exception as exc:
                        errors.append(
                            f"line {latest_line} {HYP005_MODEL4_COLLECTION_ID}: "
                            "unreadable execution receipt blocks prelaunch authority: "
                            f"{receipt_path.name}: {exc}"
                        )
                        continue
                    if (
                        isinstance(receipt, dict)
                        and receipt.get("hypothesis_id")
                        == HYP005_MODEL4_COLLECTION_ID
                    ):
                        errors.append(
                            f"line {latest_line} {HYP005_MODEL4_COLLECTION_ID}: "
                            "execution receipt already exists; prelaunch authority is consumed"
                        )

    if rows == 0:
        errors.append("registry must contain at least one row")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    registry = args.registry.resolve()
    schema = args.schema.resolve()
    errors = validate_registry(registry, schema)
    if errors:
        for error in errors:
            print(f"CANDIDATE_REGISTRY_ERROR {error}", file=sys.stderr)
        return 1
    row_count = len(registry.read_text(encoding="utf-8-sig").splitlines())
    hypotheses = {
        json.loads(line)["hypothesis_id"]
        for line in registry.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    }
    print(f"CANDIDATE_REGISTRY_OK rows={row_count} hypotheses={len(hypotheses)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
