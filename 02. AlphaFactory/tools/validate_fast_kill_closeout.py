#!/usr/bin/env python3
"""Validate a lean, hash-bound closeout for an early-killed research cell."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "alphafactory_fast_kill_closeout.v1"
EVIDENCE_CLASSES = {"offline_probe", "model0"}
VERDICTS = {"KILLED", "PARKED", "INVALID"}
KILL_CODES = {
    "data_invalid",
    "engineering_invalid",
    "cadence_fail",
    "gross_edge_fail",
    "cost_dominated",
    "matched_control_fail",
    "instability_fail",
    "risk_fail",
}
BASE_ROLES = {"preregistration", "result_summary", "readout"}
MODEL0_ROLES = {
    "source",
    "compile_log",
    "nonrepaint_audit",
    "run_manifest",
    "tester_report",
    "summary_metrics",
    "log_triage",
}
ECONOMIC_KILL_CODES = {
    "cadence_fail",
    "gross_edge_fail",
    "cost_dominated",
    "matched_control_fail",
    "instability_fail",
    "risk_fail",
}
COMPARATORS = {
    "lt": lambda actual, threshold: actual < threshold,
    "lte": lambda actual, threshold: actual <= threshold,
    "gt": lambda actual, threshold: actual > threshold,
    "gte": lambda actual, threshold: actual >= threshold,
}
SEQUENTIAL_METHODS = {
    "group_sequential_futility",
    "bayesian_predictive_futility",
    "e_value_futility",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("packet root must be an object")
    return payload


def as_dict(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_bindings(payload: dict[str, Any], workspace: Path, errors: list[str]) -> set[str]:
    rows = payload.get("bindings")
    if not isinstance(rows, list):
        errors.append("bindings must be an array")
        return set()
    roles: set[str] = set()
    workspace = workspace.resolve()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"binding {index} must be an object")
            continue
        role = row.get("role")
        raw_path = row.get("path")
        if not isinstance(role, str) or not role:
            errors.append(f"binding {index} role is required")
            continue
        if role in roles:
            errors.append(f"duplicate binding role: {role}")
        roles.add(role)
        if not isinstance(raw_path, str) or not raw_path:
            errors.append(f"{role} path is required")
            continue
        candidate = Path(raw_path)
        path = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
        try:
            path.relative_to(workspace)
        except ValueError:
            errors.append(f"{role} path escapes workspace: {raw_path}")
            continue
        if not path.is_file():
            errors.append(f"{role} file is missing: {raw_path}")
            continue
        expected_bytes = row.get("bytes")
        expected_hash = row.get("sha256")
        if not isinstance(expected_bytes, int) or expected_bytes <= 0:
            errors.append(f"{role} bytes must be a positive integer")
        elif path.stat().st_size != expected_bytes:
            errors.append(f"{role} byte count mismatch")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[A-F0-9]{64}", expected_hash):
            errors.append(f"{role} sha256 must be uppercase SHA256")
        elif sha256(path) != expected_hash:
            errors.append(f"{role} SHA256 mismatch")
    return roles


def validate_packet(packet: Path, workspace: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    try:
        payload = load_json(packet)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"packet cannot be parsed: {exc}"], {}

    if payload.get("schema_version") != SCHEMA:
        errors.append(f"schema_version must be {SCHEMA}")
    for key in ("created_at_utc", "hypothesis_id", "ea_name"):
        if not isinstance(payload.get(key), str) or not payload.get(key):
            errors.append(f"{key} is required")
    if not re.fullmatch(r"EA_[A-Za-z0-9_.-]+", str(payload.get("ea_name") or "")):
        errors.append("ea_name must be a canonical EA_* name")

    evidence_class = payload.get("evidence_class")
    if evidence_class not in EVIDENCE_CLASSES:
        errors.append("evidence_class must be offline_probe or model0")
    if payload.get("verdict") not in VERDICTS:
        errors.append("verdict must be KILLED, PARKED or INVALID")
    kill_code = payload.get("kill_code")
    if kill_code not in KILL_CODES:
        errors.append("kill_code is invalid")
    if payload.get("cell_closeout_claim") is not True:
        errors.append("cell_closeout_claim must be true")

    roles = validate_bindings(payload, workspace, errors)
    required_roles = set(BASE_ROLES)
    if evidence_class == "model0":
        required_roles |= MODEL0_ROLES
    missing = sorted(required_roles - roles)
    if missing:
        errors.append("missing required binding roles: " + ", ".join(missing))

    gate = as_dict(payload.get("frozen_kill_gate"), "frozen_kill_gate", errors)
    actual = gate.get("actual")
    threshold = gate.get("threshold")
    comparator = gate.get("comparator")
    if kill_code in ECONOMIC_KILL_CODES:
        if not finite_number(actual) or not finite_number(threshold):
            errors.append("economic fast-kill requires finite gate actual and threshold")
        elif comparator not in COMPARATORS:
            errors.append("economic fast-kill comparator must be lt, lte, gt or gte")
        elif not COMPARATORS[comparator](float(actual), float(threshold)):
            errors.append("frozen kill gate is not triggered by the supplied actual")
        if gate.get("frozen_pre_outcome") is not True:
            errors.append("frozen_kill_gate frozen_pre_outcome must be true")
        minimum_observations = gate.get("minimum_observations")
        if not isinstance(minimum_observations, int) or minimum_observations < 1:
            errors.append("economic fast-kill requires a positive frozen minimum_observations")
        if gate.get("observations_unit") != "completed_trades":
            errors.append("economic fast-kill observations_unit must be completed_trades")
        if gate.get("sequential_early_stop") is True:
            if gate.get("sequential_boundary_frozen_pre_outcome") is not True:
                errors.append("sequential early-stop boundary must be frozen pre-outcome")
            if gate.get("sequential_method") not in SEQUENTIAL_METHODS:
                errors.append(
                    "sequential_method must be group_sequential_futility, "
                    "bayesian_predictive_futility or e_value_futility"
                )
            if not isinstance(gate.get("sequential_parameters"), dict) or not gate.get("sequential_parameters"):
                errors.append("sequential early-stop requires non-empty sequential_parameters")
            maximum_looks = gate.get("maximum_looks")
            looks_evaluated = gate.get("looks_evaluated")
            if not isinstance(maximum_looks, int) or maximum_looks < 1:
                errors.append("sequential early-stop requires maximum_looks >= 1")
            if (
                not isinstance(looks_evaluated, int)
                or looks_evaluated < 1
                or (isinstance(maximum_looks, int) and looks_evaluated > maximum_looks)
            ):
                errors.append("looks_evaluated must be within the frozen maximum_looks")
    else:
        if gate.get("invalidated_before_economics") is not True:
            errors.append("data/engineering invalidation must declare invalidated_before_economics=true")

    metrics = as_dict(payload.get("metrics"), "metrics", errors)
    trades = metrics.get("trades")
    if not isinstance(trades, int) or trades < 0:
        errors.append("metrics.trades must be a nonnegative integer")
    if kill_code in ECONOMIC_KILL_CODES:
        if not isinstance(trades, int) or trades <= 0:
            errors.append("economic fast-kill requires at least one trade")
        if not finite_number(metrics.get("gross_profit_factor")):
            errors.append("economic fast-kill requires finite gross_profit_factor")
        minimum_observations = gate.get("minimum_observations")
        if isinstance(minimum_observations, int) and isinstance(trades, int) and trades < minimum_observations:
            errors.append("economic fast-kill has not reached its frozen minimum_observations")
    if kill_code == "cost_dominated" and not finite_number(metrics.get("cost_profit_factor_x1")):
        errors.append("cost_dominated requires finite cost_profit_factor_x1")

    anti = as_dict(payload.get("anti_overfit_contract"), "anti_overfit_contract", errors)
    for key in ("plan_frozen_pre_outcome", "terminal_state_recorded"):
        if anti.get(key) is not True:
            errors.append(f"anti_overfit_contract {key} must be true")
    for key in ("posthoc_rule_change_authorized", "same_id_rerun_authorized"):
        if anti.get(key) is not False:
            errors.append(f"anti_overfit_contract {key} must be false")

    limitations = payload.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        errors.append("limitations must contain at least one non-empty item")
    return errors, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Workspace root for hash-bound relative paths",
    )
    args = parser.parse_args()
    errors, payload = validate_packet(args.packet.resolve(), args.workspace.resolve())
    if errors:
        for error in errors:
            print(f"FAST_KILL_CLOSEOUT_ERROR {error}", file=sys.stderr)
        return 1
    print(
        "FAST_KILL_CLOSEOUT_OK "
        f"hypothesis={payload['hypothesis_id']} "
        f"ea={payload['ea_name']} "
        f"class={payload['evidence_class']} "
        f"verdict={payload['verdict']} "
        f"kill_code={payload['kill_code']} "
        f"packet_sha256={sha256(args.packet.resolve())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
