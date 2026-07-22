#!/usr/bin/env python3
"""Fail-closed completion gate for an AlphaFactory EA development cycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "alphafactory_ea_delivery_packet.v1"
DELIVERY_CLASSES = {"economic_run", "zero_trade_terminal"}
VERDICTS = {"SCREENED", "CHALLENGER", "CONFIRMED", "PARKED", "KILLED", "INVALID"}
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")

BASE_BINDINGS = {
    "preregistration",
    "logic_matrix",
    "source",
    "compiled_binary",
    "compile_log",
    "test_receipt",
    "nonrepaint_audit",
    "run_manifest",
    "tester_report",
    "lifecycle_trades",
    "run_meta",
    "log_triage",
    "casebook_manifest",
    "decision_casebook_manifest",
    "readout",
}
ANALYSIS_DIMENSIONS = {
    "economics",
    "cost_stress",
    "cadence",
    "time_stability",
    "session_breakdown",
    "direction_breakdown",
    "regime_breakdown",
    "execution_quality",
    "funnel",
    "winning_trade_causes",
    "losing_trade_causes",
    "logic_conflicts",
    "limitations",
}
ALLOWED_ANALYSIS_STATUS = {
    "COMPLETE",
    "INSUFFICIENT_EXPLAINED",
    "NOT_APPLICABLE_ZERO_TRADES",
}
ZERO_TRADE_NA = {
    "economics",
    "cost_stress",
    "winning_trade_causes",
    "losing_trade_causes",
}


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=strict_object)


def as_dict(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def as_nonnegative_int(value: Any, name: str, errors: list[str]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"{name} must be a non-negative integer")
        return 0
    return value


def resolve_binding_path(workspace: Path, raw_path: Any, role: str, errors: list[str]) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{role} path must be a non-empty workspace-relative path")
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        errors.append(f"{role} path must be workspace-relative")
        return None
    resolved = (workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError:
        errors.append(f"{role} path escapes workspace: {raw_path}")
        return None
    return resolved


def validate_bindings(
    payload: dict[str, Any], workspace: Path, delivery_class: str, errors: list[str]
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    rows = payload.get("bindings")
    if not isinstance(rows, list):
        errors.append("bindings must be an array")
        return {}, {}
    by_role: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"binding[{index}] must be an object")
            continue
        role = row.get("role")
        if not isinstance(role, str) or not role:
            errors.append(f"binding[{index}] role is required")
            continue
        if role in by_role:
            errors.append(f"duplicate binding role: {role}")
            continue
        by_role[role] = row
        path = resolve_binding_path(workspace, row.get("path"), role, errors)
        if path is None:
            continue
        paths[role] = path
        if not path.is_file():
            errors.append(f"{role} file is missing: {row.get('path')}")
            continue
        expected_bytes = row.get("bytes")
        if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int):
            errors.append(f"{role} bytes must be an integer")
        elif path.stat().st_size != expected_bytes:
            errors.append(
                f"{role} byte-size mismatch: packet={expected_bytes} actual={path.stat().st_size}"
            )
        expected_sha = row.get("sha256")
        if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha.upper()):
            errors.append(f"{role} sha256 must be 64 hexadecimal characters")
        else:
            actual_sha = sha256(path)
            if actual_sha != expected_sha.upper():
                errors.append(f"{role} SHA256 mismatch: packet={expected_sha.upper()} actual={actual_sha}")

    required = set(BASE_BINDINGS)
    required.add("economic_analysis" if delivery_class == "economic_run" else "funnel_analysis")
    missing = sorted(required - set(by_role))
    if missing:
        errors.append("missing required binding roles: " + ", ".join(missing))
    return by_role, paths


def validate_logic(payload: dict[str, Any], errors: list[str]) -> None:
    contract = as_dict(payload.get("logic_contract"), "logic_contract", errors)
    total = as_nonnegative_int(contract.get("requirements_total"), "requirements_total", errors)
    mapped = as_nonnegative_int(
        contract.get("requirements_mapped_to_code"), "requirements_mapped_to_code", errors
    )
    tested = as_nonnegative_int(contract.get("requirements_tested"), "requirements_tested", errors)
    if total <= 0:
        errors.append("logic_contract must contain at least one requirement")
    if mapped != total:
        errors.append(f"logic mapping incomplete: mapped={mapped} total={total}")
    if tested != total:
        errors.append(f"logic verification incomplete: tested={tested} total={total}")
    if contract.get("closed_bar_decisions") is not True:
        errors.append("logic_contract closed_bar_decisions must be true")
    if contract.get("unresolved_material_ambiguities") != 0:
        errors.append("logic_contract has unresolved material ambiguities")


def validate_engineering(payload: dict[str, Any], paths: dict[str, Path], errors: list[str]) -> None:
    contract = as_dict(payload.get("engineering_contract"), "engineering_contract", errors)
    if as_nonnegative_int(contract.get("tests_passed"), "tests_passed", errors) <= 0:
        errors.append("engineering_contract requires at least one passing test")
    for key in ("tests_failed", "compile_errors", "compile_warnings"):
        if contract.get(key) != 0:
            errors.append(f"engineering_contract {key} must be 0")
    if contract.get("nonrepaint_status") != "PASS":
        errors.append("engineering_contract nonrepaint_status must be PASS")
    compile_log = paths.get("compile_log")
    if compile_log and compile_log.is_file():
        text = compile_log.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"Result:\s*0 errors,\s*0 warnings", text, re.IGNORECASE):
            errors.append("compile_log does not prove Result: 0 errors, 0 warnings")


def validate_run(payload: dict[str, Any], delivery_class: str, errors: list[str]) -> dict[str, Any]:
    contract = as_dict(payload.get("run_contract"), "run_contract", errors)
    if not isinstance(contract.get("run_id"), str) or not contract.get("run_id"):
        errors.append("run_contract run_id is required")
    if contract.get("model") != 0:
        errors.append("run_contract model must be 0")
    trades = as_nonnegative_int(contract.get("trades"), "run_contract trades", errors)
    if delivery_class == "economic_run" and trades <= 0:
        errors.append("economic_run requires at least one trade")
    if delivery_class == "zero_trade_terminal" and trades != 0:
        errors.append("zero_trade_terminal requires trades=0")
    if contract.get("report_lifecycle_reconciled") is not True:
        errors.append("report/lifecycle reconciliation must be true")
    if contract.get("lifecycle_open_rows") != trades:
        errors.append("lifecycle_open_rows must equal trades")
    if contract.get("lifecycle_final_rows") != trades:
        errors.append("lifecycle_final_rows must equal trades")
    if contract.get("unresolved_log_errors") != 0:
        errors.append("run_contract unresolved_log_errors must be 0")
    return contract


def validate_analysis(payload: dict[str, Any], delivery_class: str, errors: list[str]) -> None:
    contract = as_dict(payload.get("analysis_contract"), "analysis_contract", errors)
    statuses = as_dict(contract.get("statuses"), "analysis_contract.statuses", errors)
    exceptions = as_dict(contract.get("exceptions", {}), "analysis_contract.exceptions", errors)
    for name in sorted(ANALYSIS_DIMENSIONS):
        if name not in statuses:
            errors.append(f"analysis status missing: {name}")
            continue
        status = statuses[name]
        if status not in ALLOWED_ANALYSIS_STATUS:
            errors.append(f"analysis status invalid for {name}: {status}")
            continue
        if delivery_class == "economic_run" and status == "NOT_APPLICABLE_ZERO_TRADES":
            errors.append(f"economic_run cannot mark {name} NOT_APPLICABLE_ZERO_TRADES")
        if delivery_class == "zero_trade_terminal":
            if name in ZERO_TRADE_NA and status not in {"NOT_APPLICABLE_ZERO_TRADES", "COMPLETE"}:
                errors.append(f"zero_trade_terminal has invalid status for {name}: {status}")
            if name not in ZERO_TRADE_NA and status != "COMPLETE":
                errors.append(f"zero_trade_terminal requires COMPLETE analysis for {name}")
        elif name != "regime_breakdown" and status != "COMPLETE":
            errors.append(f"economic_run requires COMPLETE analysis for {name}")
        if status != "COMPLETE":
            reason = exceptions.get(name)
            if not isinstance(reason, str) or len(reason.strip()) < 20:
                errors.append(f"analysis exception needs a material explanation: {name}")


def classify_label(value: Any) -> str:
    text = str(value or "").lower()
    if any(token in text for token in ("loss", "loser", "negative", "non_positive", "stop")):
        return "loss"
    if any(token in text for token in ("win", "winner", "positive", "target", "tp")):
        return "win"
    if any(token in text for token in ("reject", "filtered", "near_miss", "candidate")):
        return "rejection"
    return "unknown"


def validate_casebook(
    payload: dict[str, Any], delivery_class: str, paths: dict[str, Path], errors: list[str]
) -> None:
    contract = as_dict(payload.get("chart_contract"), "chart_contract", errors)
    manifest_path = paths.get("casebook_manifest")
    if not manifest_path or not manifest_path.is_file():
        return
    try:
        manifest = load_json(manifest_path)
    except (ValueError, OSError) as exc:
        errors.append(f"casebook manifest cannot be parsed: {exc}")
        return
    if manifest.get("schema_version") != "chart_case_render.v2":
        errors.append("casebook manifest must use chart_case_render.v2")
    if manifest.get("mode") != "anatomy":
        errors.append("casebook must be rendered in anatomy mode")
    results = manifest.get("results")
    if not isinstance(results, list) or not results:
        errors.append("casebook results must contain rendered cases")
        return

    counts = {"win": 0, "loss": 0, "rejection": 0}
    for row in results:
        if not isinstance(row, dict):
            errors.append("casebook result must be an object")
            continue
        case_id = str(row.get("case_id", "UNKNOWN"))
        if row.get("status") != "RENDERED":
            errors.append(f"casebook {case_id} is not RENDERED")
            continue
        png_name = row.get("png")
        if not isinstance(png_name, str) or not png_name:
            errors.append(f"casebook {case_id} missing PNG path")
        else:
            png = (manifest_path.parent / png_name).resolve()
            try:
                png.relative_to(manifest_path.parent.resolve())
            except ValueError:
                errors.append(f"casebook {case_id} PNG escapes casebook directory")
            else:
                if not png.is_file():
                    errors.append(f"casebook {case_id} PNG is missing")
                elif sha256(png) != str(row.get("sha256", "")).upper():
                    errors.append(f"casebook {case_id} PNG SHA256 mismatch")
        if row.get("entry_marker_rendered") is not True:
            errors.append(f"casebook {case_id} missing entry marker")
        if delivery_class == "economic_run":
            if row.get("sl_line_rendered") is not True:
                errors.append(f"casebook {case_id} missing SL line")
            if row.get("tp_line_rendered") is not True:
                errors.append(f"casebook {case_id} missing TP line")
            if row.get("exit_marker_rendered") is not True:
                errors.append(f"casebook {case_id} missing exit marker")
        context = row.get("context")
        if not isinstance(context, dict):
            errors.append(f"casebook {case_id} missing higher-timeframe context")
        else:
            if context.get("timeframe") != contract.get("higher_timeframe"):
                errors.append(f"casebook {case_id} higher-timeframe mismatch")
            if context.get("entry_position") != "center":
                errors.append(f"casebook {case_id} HTF entry candle is not centered")
            if context.get("post_entry_outcome_region") is not True:
                errors.append(f"casebook {case_id} does not label post-entry outcome")
            if not isinstance(context.get("post_entry_bars_drawn"), int) or context.get("post_entry_bars_drawn") <= 0:
                errors.append(f"casebook {case_id} has no post-entry HTF bars")
            if context.get("decision_state_cutoff_enforced") is not True:
                errors.append(f"casebook {case_id} lacks decision-time cutoff proof")
        label_class = classify_label(row.get("label"))
        if label_class in counts:
            counts[label_class] += 1

    minimum = as_nonnegative_int(contract.get("minimum_each"), "chart minimum_each", errors)
    if minimum < 2:
        errors.append("chart minimum_each must be at least 2")
    if contract.get("higher_timeframe_context") is not True:
        errors.append("chart higher_timeframe_context must be true")
    if contract.get("higher_timeframe") not in {"M15", "H1", "H4", "D1"}:
        errors.append("chart higher_timeframe must be M15, H1, H4 or D1")
    for key in ("entry_candle_centered", "post_entry_bars_visible", "outcome_region_labeled"):
        if contract.get(key) is not True:
            errors.append(f"chart_contract {key} must be true")

    if delivery_class == "economic_run":
        if contract.get("sample_basis") != "wins_and_losses":
            errors.append("economic_run chart sample_basis must be wins_and_losses")
        if contract.get("entry_sl_tp_exit_visible") is not True:
            errors.append("economic_run charts must show entry, SL, TP and exit")
        required_wins = min(minimum, as_nonnegative_int(contract.get("available_winners"), "available_winners", errors))
        required_losses = min(minimum, as_nonnegative_int(contract.get("available_losers"), "available_losers", errors))
        if counts["win"] < required_wins or contract.get("rendered_winners") != counts["win"]:
            errors.append(f"casebook winner coverage mismatch: rendered={counts['win']} required={required_wins}")
        if counts["loss"] < required_losses or contract.get("rendered_losers") != counts["loss"]:
            errors.append(f"casebook loser coverage mismatch: rendered={counts['loss']} required={required_losses}")
    else:
        if contract.get("sample_basis") != "rejections":
            errors.append("zero_trade_terminal chart sample_basis must be rejections")
        required = min(
            minimum,
            as_nonnegative_int(contract.get("available_rejections"), "available_rejections", errors),
        )
        if counts["rejection"] < required or contract.get("rendered_rejections") != counts["rejection"]:
            errors.append(
                f"casebook rejection coverage mismatch: rendered={counts['rejection']} required={required}"
            )


def validate_decision_casebook(
    payload: dict[str, Any], paths: dict[str, Path], errors: list[str]
) -> None:
    contract = as_dict(payload.get("chart_contract"), "chart_contract", errors)
    for key in (
        "decision_asof_separate",
        "decision_outcome_hidden",
        "decision_net_r_hidden",
        "decision_active_indicators_visible",
    ):
        if contract.get(key) is not True:
            errors.append(f"chart_contract {key} must be true")
    provenance = contract.get("decision_indicator_provenance")
    if provenance not in {
        "mt5_decision_telemetry",
        "parity_proven_mt5_export",
        "diagnostic_recompute_nonparity_labeled",
    }:
        errors.append("chart_contract decision_indicator_provenance is invalid")

    decision_path = paths.get("decision_casebook_manifest")
    anatomy_path = paths.get("casebook_manifest")
    if not decision_path or not decision_path.is_file():
        return
    try:
        decision = load_json(decision_path)
    except (ValueError, OSError) as exc:
        errors.append(f"decision casebook manifest cannot be parsed: {exc}")
        return
    if decision.get("schema_version") != "chart_case_render.v2":
        errors.append("decision casebook manifest must use chart_case_render.v2")
    if decision.get("mode") != "asof":
        errors.append("decision casebook must be rendered in asof mode")
    results = decision.get("results")
    if not isinstance(results, list) or not results:
        errors.append("decision casebook results must contain rendered cases")
        return

    anatomy_ids: set[str] = set()
    if anatomy_path and anatomy_path.is_file():
        try:
            anatomy = load_json(anatomy_path)
        except (ValueError, OSError):
            anatomy = {}
        anatomy_results = anatomy.get("results")
        if isinstance(anatomy_results, list):
            anatomy_ids = {
                str(row.get("case_id")) for row in anatomy_results if isinstance(row, dict)
            }

    decision_ids: set[str] = set()
    for row in results:
        if not isinstance(row, dict):
            errors.append("decision casebook result must be an object")
            continue
        case_id = str(row.get("case_id", "UNKNOWN"))
        if case_id in decision_ids:
            errors.append(f"decision casebook duplicate case_id: {case_id}")
        decision_ids.add(case_id)
        if row.get("status") != "RENDERED":
            errors.append(f"decision casebook {case_id} is not RENDERED")
            continue
        if row.get("mode") != "asof":
            errors.append(f"decision casebook {case_id} mode must be asof")
        png_name = row.get("png")
        if not isinstance(png_name, str) or not png_name:
            errors.append(f"decision casebook {case_id} missing PNG path")
        else:
            png = (decision_path.parent / png_name).resolve()
            try:
                png.relative_to(decision_path.parent.resolve())
            except ValueError:
                errors.append(f"decision casebook {case_id} PNG escapes casebook directory")
            else:
                if not png.is_file():
                    errors.append(f"decision casebook {case_id} PNG is missing")
                elif sha256(png) != str(row.get("sha256", "")).upper():
                    errors.append(f"decision casebook {case_id} PNG SHA256 mismatch")
        if row.get("entry_marker_rendered") is not True:
            errors.append(f"decision casebook {case_id} missing entry marker")
        for key in ("cutoff_enforced", "outcome_hidden", "net_r_hidden", "label_hidden_in_image"):
            if row.get(key) is not True:
                errors.append(f"decision casebook {case_id} {key} must be true")
        context = row.get("context")
        if not isinstance(context, dict):
            errors.append(f"decision casebook {case_id} missing higher-timeframe context")
        else:
            if context.get("timeframe") != contract.get("higher_timeframe"):
                errors.append(f"decision casebook {case_id} higher-timeframe mismatch")
            if context.get("entry_position") != "center":
                errors.append(f"decision casebook {case_id} HTF entry candle is not centered")
            if context.get("future_region_hidden") is not True:
                errors.append(f"decision casebook {case_id} future region is not hidden")
            if context.get("post_entry_outcome_region") is not False:
                errors.append(f"decision casebook {case_id} discloses post-entry outcome")
            if context.get("post_entry_bars_drawn") != 0:
                errors.append(f"decision casebook {case_id} draws post-entry bars")
            if context.get("decision_state_cutoff_enforced") is not True:
                errors.append(f"decision casebook {case_id} lacks decision-time cutoff proof")

    if anatomy_ids and decision_ids != anatomy_ids:
        errors.append(
            "decision/anatomy case coverage mismatch: "
            f"decision={sorted(decision_ids)} anatomy={sorted(anatomy_ids)}"
        )


def validate_log_triage(paths: dict[str, Path], bindings: dict[str, dict[str, Any]], errors: list[str]) -> None:
    path = paths.get("log_triage")
    if not path or not path.is_file():
        return
    try:
        payload = load_json(path)
    except (ValueError, OSError) as exc:
        errors.append(f"log_triage cannot be parsed: {exc}")
        return
    if payload.get("schema_version") != "log_triage.v1":
        errors.append("log_triage must use log_triage.v1")
    if payload.get("clean") is not True and "log_findings_resolution" not in bindings:
        errors.append("flagged log_triage requires a hash-bound log_findings_resolution")


def validate_anti_overfit(payload: dict[str, Any], errors: list[str]) -> None:
    contract = as_dict(payload.get("anti_overfit_contract"), "anti_overfit_contract", errors)
    for key in ("plan_frozen_pre_outcome", "one_change_one_run"):
        if contract.get(key) is not True:
            errors.append(f"anti_overfit_contract {key} must be true")
    if contract.get("posthoc_rule_change_authorized") is not False:
        errors.append("anti_overfit_contract posthoc_rule_change_authorized must be false")


def validate_packet(packet: Path, workspace: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    try:
        payload = load_json(packet)
    except (ValueError, OSError) as exc:
        return [f"packet cannot be parsed: {exc}"], {}
    if not isinstance(payload, dict):
        return ["packet root must be an object"], {}
    if payload.get("schema_version") != SCHEMA:
        errors.append(f"schema_version must be {SCHEMA}")
    for key in ("created_at_utc", "hypothesis_id", "ea_name"):
        if not isinstance(payload.get(key), str) or not payload.get(key):
            errors.append(f"{key} is required")
    delivery_class = payload.get("delivery_class")
    if delivery_class not in DELIVERY_CLASSES:
        errors.append("delivery_class must be economic_run or zero_trade_terminal")
        delivery_class = "economic_run"
    if payload.get("completion_claim") is not True:
        errors.append("completion_claim must be true for the delivery gate")
    if payload.get("verdict") not in VERDICTS:
        errors.append("verdict is invalid")
    bindings, paths = validate_bindings(payload, workspace, delivery_class, errors)
    validate_logic(payload, errors)
    validate_engineering(payload, paths, errors)
    validate_run(payload, delivery_class, errors)
    validate_analysis(payload, delivery_class, errors)
    validate_casebook(payload, delivery_class, paths, errors)
    validate_decision_casebook(payload, paths, errors)
    validate_log_triage(paths, bindings, errors)
    validate_anti_overfit(payload, errors)
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
        help="Workspace root used to resolve hash-bound relative paths",
    )
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    packet = args.packet.resolve()
    errors, payload = validate_packet(packet, workspace)
    if errors:
        for error in errors:
            print(f"EA_DELIVERY_PACKET_ERROR {error}", file=sys.stderr)
        return 1
    print(
        "EA_DELIVERY_PACKET_OK "
        f"hypothesis={payload['hypothesis_id']} "
        f"ea={payload['ea_name']} "
        f"class={payload['delivery_class']} "
        f"verdict={payload['verdict']} "
        f"bindings={len(payload['bindings'])} "
        f"packet_sha256={sha256(packet)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
