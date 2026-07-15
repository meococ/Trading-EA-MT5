#!/usr/bin/env python3
"""Validate registry schema, arithmetic, split evidence, and physical bindings."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


RESEARCH_DIR = Path(__file__).resolve().parent
WORKSPACE = RESEARCH_DIR.parents[2]
REGISTRY_PATH = RESEARCH_DIR / "CANDIDATE_REGISTRY.jsonl"
SCHEMA_PATH = RESEARCH_DIR / "CANDIDATE_REGISTRY.schema.json"
EVIDENCE_STATES = {"challenger", "confirmed", "portfolio-sleeve"}
PROMOTION_STATES = {"confirmed", "portfolio-sleeve"}
PRODUCER_SCHEMA = "registry_producer_evidence.v2"
RUN_MANIFEST_SCHEMA = "alphafactory_run_manifest.v2"
NONREPAINT_SCHEMA = "alphafactory_nonrepaint_audit.v1"
READOUT_SCHEMA = "sonic_readout.v1"
PREFLIGHT_SCHEMA = "registry_preflight_clearance.v1"
OFFLINE_METADATA_MARKERS = (
    "offline",
    "intake",
    "preflight_only",
    "preflight only",
    "probe_only",
    "probe only",
    "no ea patch",
    "no mt5 run",
    "no backtest",
)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _zero_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def _finite_float(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate JSON object key is forbidden: {key}")
        payload[key] = value
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _canonical_sha256(value: Any) -> str | None:
    if not isinstance(value, str) or re.fullmatch(r"[A-Fa-f0-9]{64}", value) is None:
        return None
    return value.upper()


def _path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_evidence_file(
    raw_path: Any,
    anchor: Path,
    label: str,
    errors: list[str],
) -> Path | None:
    if not _nonempty_string(raw_path):
        errors.append(f"{label}: missing non-empty evidence path")
        return None
    try:
        candidate = Path(str(raw_path))
        if not candidate.is_absolute():
            candidate = anchor.parent / candidate
        resolved = candidate.resolve()
        workspace = WORKSPACE.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(f"{label}: invalid evidence path: {exc}")
        return None
    if not _path_is_within(resolved, workspace):
        errors.append(f"{label}: evidence path escapes the workspace: {raw_path}")
        return None
    if not resolved.is_file():
        errors.append(f"{label}: evidence file is absent or not regular: {raw_path}")
        return None
    return resolved


def verify_evidence_file(
    raw_path: Any,
    expected_hash: Any,
    anchor: Path,
    label: str,
    errors: list[str],
) -> Path | None:
    path = resolve_evidence_file(raw_path, anchor, label, errors)
    if path is None:
        return None
    declared = _canonical_sha256(expected_hash)
    if declared is None:
        errors.append(f"{label}: invalid SHA256")
        return None
    actual = sha256_file(path)
    if actual != declared:
        errors.append(f"{label}: SHA256 mismatch expected={declared} actual={actual}")
        return None
    return path


def validate_nontrivial_file(
    path: Path | None,
    label: str,
    errors: list[str],
    *,
    minimum_bytes: int = 128,
) -> None:
    if path is None:
        return
    try:
        payload = path.read_bytes()
    except OSError as exc:
        errors.append(f"{label}: cannot read artifact: {exc}")
        return
    if len(payload) < minimum_bytes:
        errors.append(
            f"{label}: artifact is trivial ({len(payload)} bytes; minimum {minimum_bytes})"
        )
        return
    if len(set(payload)) < 8:
        errors.append(f"{label}: artifact content is degenerate")


def canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def resolve_workspace_file(relative_path: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        errors.append(f"{label}: missing non-empty relative path")
        return None
    pure = PurePosixPath(relative_path)
    if (
        Path(relative_path).is_absolute()
        or pure.is_absolute()
        or "\\" in relative_path
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != relative_path
    ):
        errors.append(f"{label}: path is not normalized workspace-relative POSIX: {relative_path}")
        return None
    path = WORKSPACE / Path(*pure.parts)
    if not path.is_file():
        errors.append(f"{label}: file is absent or not regular: {relative_path}")
        return None
    return path


def verify_bound_file(
    relative_path: Any,
    expected_hash: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    path = resolve_workspace_file(relative_path, label, errors)
    if path is None:
        return None
    if not isinstance(expected_hash, str) or not re.fullmatch(
        r"[A-Fa-f0-9]{64}", expected_hash
    ):
        errors.append(f"{label}: invalid SHA256")
        return None
    actual = sha256_file(path)
    if actual != expected_hash.upper():
        errors.append(
            f"{label}: SHA256 mismatch expected={expected_hash.upper()} actual={actual}"
        )
        return None
    return path


def validate_cadence_arithmetic(
    metrics: dict[str, Any], label: str, errors: list[str]
) -> None:
    fields = ("trades", "elapsed_days", "elapsed_calendar_weeks", "trades_per_elapsed_week")
    values: dict[str, float] = {}
    for field in fields:
        value = metrics.get(field)
        converted = _finite_float(value)
        if converted is None:
            errors.append(f"{label}: {field} must be finite numeric evidence")
            return
        values[field] = converted
    if values["elapsed_days"] <= 0 or values["elapsed_calendar_weeks"] <= 0:
        errors.append(f"{label}: elapsed span must be positive")
        return
    expected_weeks = values["elapsed_days"] / 7.0
    if not math.isclose(
        values["elapsed_calendar_weeks"], expected_weeks, rel_tol=1e-9, abs_tol=1e-9
    ):
        errors.append(
            f"{label}: elapsed_calendar_weeks != elapsed_days/7 "
            f"({values['elapsed_calendar_weeks']} != {expected_weeks})"
        )
    expected_cadence = values["trades"] / expected_weeks
    if not math.isclose(
        values["trades_per_elapsed_week"], expected_cadence, rel_tol=1e-9, abs_tol=1e-9
    ):
        errors.append(
            f"{label}: trades_per_elapsed_week != trades/(elapsed_days/7) "
            f"({values['trades_per_elapsed_week']} != {expected_cadence})"
        )


def validate_artifact_ref(ref: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(ref, dict):
        errors.append(f"{label}: artifact reference must be an object")
        return None
    return verify_bound_file(ref.get("path"), ref.get("sha256"), label, errors)


def load_bound_json(ref: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    path = validate_artifact_ref(ref, label, errors)
    if path is None:
        return None
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8-sig"),
            parse_constant=reject_nonfinite_json,
            object_pairs_hook=reject_duplicate_keys,
        )
    except Exception as exc:
        errors.append(f"{label}: artifact is not strict JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label}: JSON root must be an object")
        return None
    return payload


def validate_producer_identity(
    payload: dict[str, Any],
    label: str,
    hypothesis_id: str,
    run_ids: list[str],
    artifact_type: str,
    errors: list[str],
    *,
    schema_version: str = PRODUCER_SCHEMA,
    status: str = "PASS",
) -> None:
    expected = {
        "schema_version": schema_version,
        "artifact_type": artifact_type,
        "status": status,
        "hypothesis_id": hypothesis_id,
        "run_ids": run_ids,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    if not _zero_integer(payload.get("producer_exit_code")):
        errors.append(f"{label}: producer_exit_code must be integer 0")
    producer_path = validate_artifact_ref(
        payload.get("producer"), f"{label}.producer", errors
    )
    if producer_path is not None and producer_path.suffix.lower() not in {
        ".py",
        ".ps1",
        ".exe",
    }:
        errors.append(f"{label}.producer: producer must be executable code")
    validate_nontrivial_file(
        producer_path, f"{label}.producer", errors, minimum_bytes=128
    )

    output_schema = payload.get("output_schema_version")
    if not _nonempty_string(output_schema):
        errors.append(f"{label}: output_schema_version must be a non-empty string")
    output_path = validate_artifact_ref(
        payload.get("output"), f"{label}.output_binding", errors
    )
    validate_nontrivial_file(
        output_path, f"{label}.output_binding", errors, minimum_bytes=128
    )
    output = load_bound_json(payload.get("output"), f"{label}.output", errors)
    if output is None:
        return
    if output.get("schema_version") != output_schema:
        errors.append(
            f"{label}.output: schema_version must equal {output_schema!r}"
        )
    for field, value in {
        "artifact_type": artifact_type,
        "status": status,
        "hypothesis_id": hypothesis_id,
        "run_ids": run_ids,
    }.items():
        if output.get(field) != value:
            errors.append(f"{label}.output: {field} must equal {value!r}")
    result = output.get("result")
    if not isinstance(result, dict) or not result:
        errors.append(f"{label}.output: result must be a non-empty object")
    producer_ref = payload.get("producer")
    output_ref = payload.get("output")
    if (
        isinstance(producer_ref, dict)
        and isinstance(output_ref, dict)
        and producer_ref.get("path") == output_ref.get("path")
    ):
        errors.append(f"{label}: producer and output must be distinct artifacts")


def validate_producer_artifact(
    ref: Any,
    label: str,
    hypothesis_id: str,
    run_ids: list[str],
    artifact_type: str,
    errors: list[str],
) -> dict[str, Any] | None:
    payload = load_bound_json(ref, label, errors)
    if payload is not None:
        validate_producer_identity(
            payload, label, hypothesis_id, run_ids, artifact_type, errors
        )
    return payload


def validate_cost_attestation(
    ref: Any,
    split_name: str,
    split: dict[str, Any],
    hypothesis_id: str,
    run_ids: list[str],
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.{split_name}.cost_manifest"
    payload = load_bound_json(ref, label, errors)
    if payload is None:
        return
    expected = {
        "schema_version": "registry_cost_attestation.v1",
        "status": "VERIFIED",
        "hypothesis_id": hypothesis_id,
        "split": split_name,
        "window": split.get("window"),
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    producer = validate_producer_artifact(
        payload.get("evidence"),
        f"{label}.evidence",
        hypothesis_id,
        run_ids,
        "cost_stress",
        errors,
    )
    if producer is not None:
        if producer.get("split") != split_name:
            errors.append(f"{label}.evidence: split must equal {split_name!r}")
        if producer.get("window") != split.get("window"):
            errors.append(
                f"{label}.evidence: window must equal {split.get('window')!r}"
            )
        if producer.get("provenance_status") != "VERIFIED":
            errors.append(f"{label}.evidence: provenance_status must equal 'VERIFIED'")


def validate_outcome_attestation(
    ref: Any,
    split_name: str,
    split: dict[str, Any],
    hypothesis_id: str,
    run_ids: list[str],
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.{split_name}.outcome_artifact"
    payload = load_bound_json(ref, label, errors)
    if payload is None:
        return
    expected = {
        "schema_version": "registry_split_outcome.v1",
        "status": "PASS",
        "hypothesis_id": hypothesis_id,
        "split": split_name,
        "window": split.get("window"),
        # Raw tester reports may be HTML/text; the strict JSON producer envelope
        # must bind their exact path/hash instead of treating raw text as a gate.
        "report": split.get("report"),
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    validate_producer_artifact(
        payload.get("producer_evidence"),
        f"{label}.producer_evidence",
        hypothesis_id,
        run_ids,
        "split_outcome",
        errors,
    )

    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        errors.append(f"{label}: metrics must be an object")
    else:
        for field in (
            "trades",
            "elapsed_days",
            "elapsed_calendar_weeks",
            "trades_per_elapsed_week",
            "cost_pf_x1",
            "cost_pf_x1_5",
            "cost_pf_x2",
            "net_r_x1_5",
            "mean_net_r_per_trade_x1",
            "positive_years",
            "total_years",
            "max_component_share_x1_5",
            "min_component_share_x1_5",
        ):
            actual = metrics.get(field)
            expected_value = split.get(field)
            if isinstance(actual, (int, float)) or isinstance(
                expected_value, (int, float)
            ):
                actual_number = _finite_float(actual)
                expected_number = _finite_float(expected_value)
                if (
                    actual_number is None
                    or expected_number is None
                    or not math.isclose(
                        actual_number,
                        expected_number,
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    )
                ):
                    errors.append(f"{label}: metric {field} does not match registry")
            elif actual != expected_value:
                errors.append(f"{label}: metric {field} does not match registry")

    artifact_controls = payload.get("controls")
    if artifact_controls != split.get("controls"):
        errors.append(f"{label}: controls do not exactly match registry split evidence")

    no_censor = payload.get("no_censor")
    if not isinstance(no_censor, dict):
        errors.append(f"{label}: no_censor must be an object")
    else:
        frozen = no_censor.get("frozen_episodes")
        complete = no_censor.get("complete_after_join")
        missing = no_censor.get("missing")
        outcome_rows = no_censor.get("outcome_rows")
        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (frozen, complete, missing, outcome_rows)
        ):
            errors.append(f"{label}: no_censor counts must be integers")
        elif missing != 0 or frozen != complete or outcome_rows != split.get("trades"):
            errors.append(f"{label}: no_censor counts fail closed")
        elif frozen < outcome_rows:
            errors.append(f"{label}: frozen episodes cannot be fewer than outcome rows")


def validate_gate_attestation(
    ref: Any,
    gate_name: str,
    hypothesis_id: str,
    run_ids: list[str],
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.validation.{gate_name}"
    payload = load_bound_json(ref, label, errors)
    if payload is None:
        return
    expected = {
        "schema_version": "registry_gate_attestation.v1",
        "gate": gate_name,
        "status": "PASS",
        "hypothesis_id": hypothesis_id,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    if payload.get("run_ids") != run_ids:
        errors.append(f"{label}: run_ids must exactly match the registry row")
    validate_producer_artifact(
        payload.get("evidence"),
        f"{label}.evidence",
        hypothesis_id,
        run_ids,
        gate_name,
        errors,
    )


def _split_symbol_contract(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def validate_preflight_clearance(
    ref: Any,
    hypothesis_id: str,
    run_ids: list[str],
    symbol: Any,
    row_window: Any,
    errors: list[str],
) -> dict[str, Any]:
    label = f"{hypothesis_id}.preflight"
    payload = load_bound_json(ref, label, errors)
    if payload is None:
        return {}
    expected = {
        "schema_version": PREFLIGHT_SCHEMA,
        "artifact_type": "preflight_clearance",
        "status": "PASS",
        "hypothesis_id": hypothesis_id,
        "run_ids": run_ids,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    producer_receipt = validate_producer_artifact(
        payload.get("producer_evidence"),
        f"{label}.producer_evidence",
        hypothesis_id,
        run_ids,
        "cost_data_preflight",
        errors,
    )
    contract = payload.get("target_contract")
    if not isinstance(contract, dict):
        errors.append(f"{label}: target_contract must be an object")
        return {}
    if contract.get("evidence_mode") != "ea_patch":
        errors.append(f"{label}: target_contract.evidence_mode must equal 'ea_patch'")
    if contract.get("cost_data_status") != "VERIFIED":
        errors.append(
            f"{label}: target_contract.cost_data_status must equal 'VERIFIED'"
        )
    declared_symbols = contract.get("symbols")
    expected_symbols = _split_symbol_contract(symbol)
    if (
        not isinstance(declared_symbols, list)
        or not declared_symbols
        or any(not _nonempty_string(item) for item in declared_symbols)
        or declared_symbols != expected_symbols
    ):
        errors.append(
            f"{label}: target_contract.symbols must exactly match {expected_symbols!r}"
        )
    train_window = contract.get("train_window")
    holdout_window = contract.get("holdout_window")
    train_bounds = parse_calendar_window(train_window, f"{label}.train_window", errors)
    holdout_bounds = parse_calendar_window(
        holdout_window, f"{label}.holdout_window", errors
    )
    row_bounds = parse_calendar_window(row_window, f"{label}.row_window", errors)
    if train_bounds is not None and holdout_bounds is not None:
        if train_bounds[1] != holdout_bounds[0]:
            errors.append(f"{label}: target train and holdout windows must be contiguous")
        combined = (train_bounds[0], holdout_bounds[1])
        if row_bounds is not None and row_bounds != combined:
            errors.append(f"{label}: row window must equal target train plus holdout")
    controls = contract.get("required_controls")
    if (
        not isinstance(controls, list)
        or not controls
        or any(not _nonempty_string(item) for item in controls)
        or len(controls) != len(set(controls))
    ):
        errors.append(
            f"{label}: target_contract.required_controls must be unique non-empty IDs"
        )
    if producer_receipt is not None:
        producer_output = load_bound_json(
            producer_receipt.get("output"),
            f"{label}.producer_evidence.output_recheck",
            errors,
        )
        result = producer_output.get("result") if producer_output is not None else None
        if not isinstance(result, dict) or result.get("cost_data_status") != "VERIFIED":
            errors.append(
                f"{label}: producer result cost_data_status must equal 'VERIFIED'"
            )
        symbol_results = result.get("symbols") if isinstance(result, dict) else None
        if not isinstance(symbol_results, dict) or set(symbol_results) != set(expected_symbols):
            errors.append(
                f"{label}: producer result symbols must exactly match {expected_symbols!r}"
            )
        else:
            minimums = {
                "spread_coverage_ratio": 0.95,
                "commission_lifecycles": 30,
                "slippage_roundturn_samples": 100,
                "slippage_buy_samples": 30,
                "slippage_sell_samples": 30,
            }
            for symbol_name in expected_symbols:
                evidence = symbol_results.get(symbol_name)
                if not isinstance(evidence, dict) or evidence.get("status") != "VERIFIED":
                    errors.append(
                        f"{label}: cost data for {symbol_name} must have VERIFIED status"
                    )
                    continue
                for field, minimum in minimums.items():
                    value = _finite_float(evidence.get(field))
                    if value is None or value < minimum:
                        errors.append(
                            f"{label}: cost data for {symbol_name} requires {field} >= {minimum}"
                        )
    return contract


def parse_readout_front_matter(
    path: Path, label: str, errors: list[str]
) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{label}: readout is not UTF-8 text: {exc}")
        return {}, ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append(f"{label}: readout machine identity front matter is missing")
        return {}, text
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        errors.append(f"{label}: readout machine identity front matter is unterminated")
        return {}, text
    metadata: dict[str, Any] = {}
    for index, line in enumerate(lines[1:end], 2):
        if ":" not in line:
            errors.append(f"{label}: invalid front matter line {index}")
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or key in metadata:
            errors.append(f"{label}: duplicate/empty front matter key at line {index}")
            continue
        if key == "run_ids":
            try:
                metadata[key] = json.loads(raw_value)
            except Exception as exc:
                errors.append(f"{label}: run_ids is not strict JSON: {exc}")
        else:
            metadata[key] = raw_value
    return metadata, "\n".join(lines[end + 1 :])


def validate_readout(
    path_value: Any,
    hash_value: Any,
    hypothesis_id: str,
    state: Any,
    run_ids: list[str],
    source_hash: Any,
    compiled_hash: Any,
    control_run_id: Any,
    challenger_run_id: Any,
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.readout"
    path = verify_bound_file(path_value, hash_value, label, errors)
    if path is None:
        return
    metadata, body = parse_readout_front_matter(path, label, errors)
    expected = {
        "schema_version": READOUT_SCHEMA,
        "hypothesis_id": hypothesis_id,
        "state": state,
        "run_ids": run_ids,
        "source_sha256": source_hash,
        "compiled_sha256": compiled_hash,
        "control_run_id": control_run_id,
        "challenger_run_id": challenger_run_id,
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            errors.append(f"{label}: machine identity {field} must equal {value!r}")
    required_sections = (
        "## Identity",
        "## Source Identity",
        "## Runs",
        "## Validation Artifacts",
        "## Verdict",
    )
    visible_body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    visible_body = re.sub(r"```.*?```", "", visible_body, flags=re.DOTALL)
    visible_headings = {
        match.group(0).strip()
        for match in re.finditer(r"(?m)^##\s+[^\r\n]+\s*$", visible_body)
    }
    for section in required_sections:
        if section not in visible_headings:
            errors.append(f"{label}: required section is missing: {section}")
    if len(body.encode("utf-8")) < 256:
        errors.append(f"{label}: readout body is trivial")


def _manifest_calendar_window(
    manifest: dict[str, Any], label: str, errors: list[str]
) -> str | None:
    def parse_date(raw: Any, field: str) -> datetime | None:
        if not isinstance(raw, str):
            errors.append(f"{label}: {field} must be a date string")
            return None
        for fmt in ("%Y.%m.%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        errors.append(f"{label}: {field} must use YYYY.MM.DD or YYYY-MM-DD")
        return None

    start = parse_date(manifest.get("from"), "from")
    inclusive_end = parse_date(manifest.get("to"), "to")
    if start is None or inclusive_end is None:
        return None
    if inclusive_end < start:
        errors.append(f"{label}: to must not precede from")
        return None
    exclusive_end = inclusive_end + timedelta(days=1)
    return (
        start.strftime("%Y-%m-%dT00:00:00Z")
        + "/"
        + exclusive_end.strftime("%Y-%m-%dT00:00:00Z")
    )


def _parse_tester_config(
    path: Path | None, label: str, errors: list[str]
) -> dict[str, Any]:
    if path is None:
        return {}
    text: str | None = None
    decode_errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except (OSError, UnicodeError) as exc:
            decode_errors.append(f"{encoding}: {exc}")
    if text is None:
        errors.append(f"{label}: config text decode failed: {'; '.join(decode_errors)}")
        return {}
    values: dict[str, Any] = {}
    tester_inputs: dict[str, str] = {}
    section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        target = tester_inputs if section == "TesterInputs" else values
        if key in target:
            errors.append(f"{label}: duplicate config key {section}.{key}")
            continue
        normalized = value.strip()
        if section == "TesterInputs":
            normalized = normalized.split("||", 1)[0].strip()
        target[key] = normalized
    required = (
        "Symbol",
        "Period",
        "Model",
        "ExecutionMode",
        "FromDate",
        "ToDate",
        "Deposit",
        "Leverage",
    )
    for field in required:
        if not _nonempty_string(values.get(field)):
            errors.append(f"{label}: config key {field} is required")
    values["__tester_inputs__"] = tester_inputs
    return values


def _parse_override_contract(value: Any, label: str, errors: list[str]) -> dict[str, str]:
    if not isinstance(value, str):
        errors.append(f"{label}: overrides must be a string")
        return {}
    parsed: dict[str, str] = {}
    for part in value.split(";"):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            errors.append(f"{label}: override lacks '=': {item!r}")
            continue
        key, raw = item.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if not key or key in parsed:
            errors.append(f"{label}: duplicate/empty override key {key!r}")
            continue
        parsed[key] = raw
    return parsed


def _manifest_file_binding(
    manifest: dict[str, Any],
    manifest_path: Path,
    path_field: str,
    hash_field: str,
    label: str,
    errors: list[str],
) -> Path | None:
    return verify_evidence_file(
        manifest.get(path_field),
        manifest.get(hash_field),
        manifest_path,
        f"{label}.{path_field}",
        errors,
    )


def validate_matched_run_manifest(
    ref: Any,
    label: str,
    hypothesis_id: str,
    run_ids: list[str],
    run_id: Any,
    run_role: str,
    report_ref: Any,
    source_hash: Any,
    compiled_hash: Any,
    exact_overrides: Any,
    row_symbol: Any,
    row_timeframe: Any,
    row_window: Any,
    errors: list[str],
) -> dict[str, Any] | None:
    manifest_path = validate_artifact_ref(ref, label, errors)
    if manifest_path is None:
        return None
    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8-sig"),
            parse_constant=reject_nonfinite_json,
            object_pairs_hook=reject_duplicate_keys,
        )
    except Exception as exc:
        errors.append(f"{label}: artifact is not strict JSON: {exc}")
        return None
    if not isinstance(manifest, dict):
        errors.append(f"{label}: JSON root must be an object")
        return None
    if manifest is None:
        return None
    expected = {
        "schema_version": RUN_MANIFEST_SCHEMA,
        "hypothesis_id": hypothesis_id,
        "run_id": run_id,
        "run_role": run_role,
        "source_sha256": source_hash,
        "ex5_sha256": compiled_hash,
        "tester_ex5_sha256": compiled_hash,
        "overrides": exact_overrides,
        "symbol": row_symbol,
        "period": row_timeframe,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    if not _zero_integer(manifest.get("model")):
        errors.append(f"{label}: model must be integer 0")
    manifest_window = _manifest_calendar_window(manifest, label, errors)
    if manifest_window != row_window:
        errors.append(f"{label}: manifest window must equal registry window {row_window!r}")

    report_path = _manifest_file_binding(
        manifest, manifest_path, "report_path", "report_sha256", label, errors
    )
    declared_report_path = validate_artifact_ref(
        report_ref, f"{label}.registry_report", errors
    )
    if (
        report_path is not None
        and declared_report_path is not None
        and report_path != declared_report_path.resolve()
    ):
        errors.append(f"{label}: manifest report_path must equal registry report path")
    if isinstance(report_ref, dict) and (
        _canonical_sha256(manifest.get("report_sha256"))
        != _canonical_sha256(report_ref.get("sha256"))
    ):
        errors.append(f"{label}: manifest report_sha256 must equal registry report hash")
    validate_nontrivial_file(report_path, f"{label}.report", errors, minimum_bytes=256)

    source_snapshot = _manifest_file_binding(
        manifest, manifest_path, "source_snapshot", "source_sha256", label, errors
    )
    ex5_snapshot = _manifest_file_binding(
        manifest, manifest_path, "ex5_snapshot", "ex5_sha256", label, errors
    )
    tester_ex5 = _manifest_file_binding(
        manifest, manifest_path, "tester_ex5_path", "tester_ex5_sha256", label, errors
    )
    validate_nontrivial_file(
        source_snapshot, f"{label}.source_snapshot", errors, minimum_bytes=64
    )
    validate_nontrivial_file(
        ex5_snapshot, f"{label}.ex5_snapshot", errors, minimum_bytes=64
    )
    validate_nontrivial_file(
        tester_ex5, f"{label}.tester_ex5", errors, minimum_bytes=64
    )

    config_path = _manifest_file_binding(
        manifest, manifest_path, "config_snapshot", "config_sha256", label, errors
    )
    validate_nontrivial_file(config_path, f"{label}.config", errors, minimum_bytes=64)
    config = _parse_tester_config(config_path, f"{label}.config", errors)
    config_expected = {
        "Symbol": str(manifest.get("symbol")),
        "Period": str(manifest.get("period")),
        "Model": "0",
        "ExecutionMode": str(manifest.get("execution_mode")),
        "FromDate": str(manifest.get("from")),
        "ToDate": str(manifest.get("to")),
        "Deposit": str(manifest.get("deposit")),
        "Leverage": str(manifest.get("leverage")),
    }
    for field, value in config_expected.items():
        if config.get(field) != value:
            errors.append(f"{label}.config: {field} must equal {value!r}")
    expected_inputs = _parse_override_contract(
        exact_overrides, f"{label}.overrides", errors
    )
    if config.get("__tester_inputs__") != expected_inputs:
        errors.append(
            f"{label}.config: TesterInputs must exactly match manifest overrides"
        )

    include_refs = manifest.get("include_snapshots")
    if not isinstance(include_refs, list) or not include_refs:
        errors.append(f"{label}: include_snapshots must be a non-empty array")
        include_refs = []
    audited_includes: list[dict[str, str]] = []
    for index, item in enumerate(include_refs):
        if not isinstance(item, dict):
            errors.append(f"{label}.include_snapshots[{index}]: entry must be an object")
            continue
        include_path = verify_evidence_file(
            item.get("snapshot_path"),
            item.get("sha256"),
            manifest_path,
            f"{label}.include_snapshots[{index}]",
            errors,
        )
        if include_path is not None:
            audited_includes.append(
                {"path": str(include_path), "sha256": sha256_file(include_path)}
            )

    for field in ("deposit", "leverage"):
        value = _finite_float(manifest.get(field))
        if value is None or value <= 0:
            errors.append(f"{label}: {field} must be finite and > 0")
    for field in ("execution_mode", "fixed_delay_ms"):
        value = manifest.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{label}: {field} must be a non-negative integer")
    if not isinstance(manifest.get("spread"), (str, int, float)) or isinstance(
        manifest.get("spread"), bool
    ):
        errors.append(f"{label}: spread must be a string or finite number")
    for field in (
        "broker_fingerprint",
        "server_fingerprint",
        "account_fingerprint",
        "data_fingerprint",
    ):
        if _canonical_sha256(manifest.get(field)) is None:
            errors.append(f"{label}: {field} must be a SHA256 identity")
    return {
        "payload": manifest,
        "path": manifest_path,
        "config": config,
        "source_snapshot": source_snapshot,
        "includes": audited_includes,
    }


def validate_matched_control_evidence(
    evidence: Any,
    hypothesis_id: str,
    run_ids: list[str],
    matched_control_run_id: Any,
    source_hash: Any,
    compiled_hash: Any,
    exact_overrides: Any,
    row_symbol: Any,
    row_timeframe: Any,
    row_window: Any,
    errors: list[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    label = f"{hypothesis_id}.matched_control"
    if not isinstance(evidence, dict):
        errors.append(f"{label}: matched_control_evidence must be an object")
        return None, None
    control_run_id = evidence.get("control_run_id")
    challenger_run_id = evidence.get("challenger_run_id")
    if control_run_id != matched_control_run_id:
        errors.append(f"{label}: control_run_id must equal matched_control_run_id")
    if control_run_id not in run_ids:
        errors.append(f"{label}: control_run_id must be present in run_ids")
    if challenger_run_id not in run_ids or challenger_run_id == control_run_id:
        errors.append(
            f"{label}: challenger_run_id must be a distinct member of run_ids"
        )
    control_overrides = evidence.get("control_overrides")
    challenger_overrides = evidence.get("challenger_overrides")
    if challenger_overrides != exact_overrides:
        errors.append(
            f"{label}: challenger_overrides must equal registry exact_overrides"
        )
    if not _nonempty_string(control_overrides):
        errors.append(f"{label}: control_overrides must be a non-empty string")
    if control_overrides == challenger_overrides:
        errors.append(f"{label}: control and challenger overrides must be distinct")

    # MT5 reports may be raw HTML/text. Both are accepted only when their exact
    # references are bound by strict machine-readable run manifests below.
    control_report = evidence.get("control_report")
    challenger_report = evidence.get("challenger_report")
    validate_artifact_ref(control_report, f"{label}.control_report", errors)
    validate_artifact_ref(challenger_report, f"{label}.challenger_report", errors)
    control_report_hash = (
        control_report.get("sha256") if isinstance(control_report, dict) else None
    )
    challenger_report_hash = (
        challenger_report.get("sha256") if isinstance(challenger_report, dict) else None
    )
    if (
        isinstance(control_report_hash, str)
        and isinstance(challenger_report_hash, str)
        and control_report_hash.upper() == challenger_report_hash.upper()
    ):
        errors.append(
            f"{label}: control and challenger reports must have distinct content hashes"
        )

    control_manifest_ref = evidence.get("control_manifest")
    challenger_manifest_ref = evidence.get("challenger_manifest")
    control_manifest = validate_matched_run_manifest(
        control_manifest_ref,
        f"{label}.control_manifest",
        hypothesis_id,
        run_ids,
        control_run_id,
        "control",
        control_report,
        source_hash,
        compiled_hash,
        control_overrides,
        row_symbol,
        row_timeframe,
        row_window,
        errors,
    )
    challenger_manifest = validate_matched_run_manifest(
        challenger_manifest_ref,
        f"{label}.challenger_manifest",
        hypothesis_id,
        run_ids,
        challenger_run_id,
        "challenger",
        challenger_report,
        source_hash,
        compiled_hash,
        challenger_overrides,
        row_symbol,
        row_timeframe,
        row_window,
        errors,
    )

    matched_identity: dict[str, Any] = {}
    if control_manifest is not None and challenger_manifest is not None:
        control_payload = control_manifest["payload"]
        challenger_payload = challenger_manifest["payload"]
        identity_fields = (
            "symbol",
            "period",
            "from",
            "to",
            "model",
            "execution_mode",
            "fixed_delay_ms",
            "deposit",
            "leverage",
            "spread",
            "broker_fingerprint",
            "server_fingerprint",
            "account_fingerprint",
            "data_fingerprint",
        )
        matched_identity = {field: control_payload.get(field) for field in identity_fields}
        for field in identity_fields:
            if control_payload.get(field) != challenger_payload.get(field):
                errors.append(
                    f"{label}: matched run identity differs for {field}"
                )
        for field in (
            "Symbol",
            "Period",
            "Model",
            "ExecutionMode",
            "FromDate",
            "ToDate",
            "Deposit",
            "Leverage",
        ):
            if control_manifest["config"].get(field) != challenger_manifest["config"].get(field):
                errors.append(f"{label}: matched config identity differs for {field}")
        control_config_hash = _canonical_sha256(control_payload.get("config_sha256"))
        challenger_config_hash = _canonical_sha256(
            challenger_payload.get("config_sha256")
        )
        if control_config_hash == challenger_config_hash:
            errors.append(
                f"{label}: control and challenger configs must be distinct artifacts"
            )

    comparison = load_bound_json(
        evidence.get("comparison"), f"{label}.comparison", errors
    )
    if comparison is not None:
        expected = {
            "schema_version": "registry_matched_control_comparison.v1",
            "artifact_type": "matched_control_comparison",
            "status": "PASS",
            "hypothesis_id": hypothesis_id,
            "run_ids": run_ids,
            "control_run_id": control_run_id,
            "challenger_run_id": challenger_run_id,
            "control_manifest": control_manifest_ref,
            "challenger_manifest": challenger_manifest_ref,
            "matched_identity_sha256": canonical_json_sha256(matched_identity),
        }
        for field, value in expected.items():
            if comparison.get(field) != value:
                errors.append(f"{label}.comparison: {field} must equal {value!r}")
        comparison_receipt = validate_producer_artifact(
            comparison.get("producer_evidence"),
            f"{label}.comparison.producer_evidence",
            hypothesis_id,
            run_ids,
            "matched_control_comparison",
            errors,
        )
        for field in ("net_delta", "risk_adjusted_delta"):
            value = _finite_float(comparison.get(field))
            if value is None or value <= 0:
                errors.append(f"{label}.comparison: {field} must be finite and > 0")
        if comparison_receipt is not None:
            comparison_output = load_bound_json(
                comparison_receipt.get("output"),
                f"{label}.comparison.producer_output_recheck",
                errors,
            )
            result = (
                comparison_output.get("result")
                if comparison_output is not None
                else None
            )
            expected_result = {
                "control_report": control_report,
                "challenger_report": challenger_report,
                "matched_identity_sha256": canonical_json_sha256(matched_identity),
                "net_delta": comparison.get("net_delta"),
                "risk_adjusted_delta": comparison.get("risk_adjusted_delta"),
            }
            if result != expected_result:
                errors.append(
                    f"{label}.comparison: producer result must exactly bind reports, identity, and deltas"
                )
    return control_manifest, challenger_manifest


def validate_nonrepaint_audit(
    ref: Any,
    hypothesis_id: str,
    source_hash: Any,
    challenger_run_id: Any,
    challenger_manifest_ref: Any,
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.nonrepaint_audit"
    audit_path = validate_artifact_ref(ref, label, errors)
    manifest_path = validate_artifact_ref(
        challenger_manifest_ref, f"{label}.run_manifest", errors
    )
    if audit_path is None or manifest_path is None:
        return
    try:
        payload = json.loads(
            audit_path.read_text(encoding="utf-8-sig"),
            parse_constant=reject_nonfinite_json,
            object_pairs_hook=reject_duplicate_keys,
        )
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8-sig"),
            parse_constant=reject_nonfinite_json,
            object_pairs_hook=reject_duplicate_keys,
        )
    except Exception as exc:
        errors.append(f"{label}: strict JSON load failed: {exc}")
        return
    if not isinstance(payload, dict) or not isinstance(manifest, dict):
        errors.append(f"{label}: audit and run manifest roots must be objects")
        return
    expected_keys = {
        "schema_version",
        "status",
        "hypothesis_id",
        "run_id",
        "manifest",
        "manifest_sha256",
        "audited_files",
        "findings",
        "allowed_new_bar_gates",
        "generated_at_utc",
    }
    if set(payload) != expected_keys:
        errors.append(
            f"{label}: artifact fields must exactly match the {NONREPAINT_SCHEMA} tool output"
        )
    expected = {
        "schema_version": NONREPAINT_SCHEMA,
        "status": "PASS",
        "hypothesis_id": hypothesis_id,
        "run_id": challenger_run_id,
        "manifest_sha256": sha256_file(manifest_path),
        "findings": [],
    }
    for field, value in expected.items():
        actual = payload.get(field)
        if field == "manifest_sha256" and isinstance(actual, str):
            actual = actual.upper()
        if actual != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    declared_manifest_path = resolve_evidence_file(
        payload.get("manifest"), audit_path, f"{label}.manifest", errors
    )
    if declared_manifest_path is not None and declared_manifest_path != manifest_path.resolve():
        errors.append(f"{label}: manifest path must bind the challenger run manifest")
    if manifest.get("source_sha256") != source_hash:
        errors.append(f"{label}: run manifest source_sha256 must match registry source_hash")

    def parse_utc_timestamp(value: Any, field: str) -> datetime | None:
        if not isinstance(value, str):
            errors.append(f"{label}: {field} must be an ISO-8601 UTC timestamp")
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{label}: {field} must be an ISO-8601 UTC timestamp")
            return None
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            errors.append(f"{label}: {field} must carry UTC timezone identity")
            return None
        return parsed

    audit_timestamp = parse_utc_timestamp(payload.get("generated_at_utc"), "generated_at_utc")
    manifest_timestamp = parse_utc_timestamp(
        manifest.get("generated_at_utc"), "run_manifest.generated_at_utc"
    )
    if (
        audit_timestamp is not None
        and manifest_timestamp is not None
        and audit_timestamp < manifest_timestamp
    ):
        errors.append(f"{label}: audit predates the bound run manifest")

    expected_files: dict[str, str] = {}
    source_path = verify_evidence_file(
        manifest.get("source_snapshot"),
        manifest.get("source_sha256"),
        manifest_path,
        f"{label}.source_snapshot",
        errors,
    )
    if source_path is not None:
        expected_files[str(source_path.resolve()).lower()] = sha256_file(source_path)
    include_refs = manifest.get("include_snapshots")
    if not isinstance(include_refs, list) or not include_refs:
        errors.append(f"{label}: run manifest include_snapshots must be non-empty")
        include_refs = []
    for index, item in enumerate(include_refs):
        if not isinstance(item, dict):
            errors.append(f"{label}.include_snapshots[{index}]: entry must be an object")
            continue
        path = verify_evidence_file(
            item.get("snapshot_path"),
            item.get("sha256"),
            manifest_path,
            f"{label}.include_snapshots[{index}]",
            errors,
        )
        if path is not None:
            expected_files[str(path.resolve()).lower()] = sha256_file(path)

    observed_files: dict[str, str] = {}
    audited_files = payload.get("audited_files")
    if not isinstance(audited_files, list) or not audited_files:
        errors.append(f"{label}: audited_files must be a non-empty array")
        audited_files = []
    for index, item in enumerate(audited_files):
        if not isinstance(item, dict):
            errors.append(f"{label}.audited_files[{index}]: entry must be an object")
            continue
        path = verify_evidence_file(
            item.get("path"),
            item.get("sha256"),
            audit_path,
            f"{label}.audited_files[{index}]",
            errors,
        )
        if path is None:
            continue
        key = str(path.resolve()).lower()
        if key in observed_files:
            errors.append(f"{label}: audited_files contains duplicate path {path}")
        observed_files[key] = sha256_file(path)
    if observed_files != expected_files:
        errors.append(
            f"{label}: audited_files must exactly equal the challenger source/include snapshot set"
        )
    if not isinstance(payload.get("allowed_new_bar_gates"), list):
        errors.append(f"{label}: allowed_new_bar_gates must be an array")


def parse_calendar_window(value: Any, label: str, errors: list[str]) -> tuple[int, int] | None:
    if not isinstance(value, str):
        errors.append(f"{label}: window must be a canonical UTC calendar-year interval")
        return None
    match = re.fullmatch(
        r"(\d{4})-01-01T00:00:00Z/(\d{4})-01-01T00:00:00Z", value
    )
    if match is None:
        errors.append(f"{label}: window must be a canonical UTC calendar-year interval")
        return None
    start_year, end_year = (int(part) for part in match.groups())
    if end_year <= start_year:
        errors.append(f"{label}: window end must be after start")
        return None
    return start_year, end_year


def validate_stability_buckets(
    buckets: Any,
    expected_periods: list[str],
    label: str,
    errors: list[str],
) -> list[float] | None:
    if not isinstance(buckets, list) or len(buckets) != len(expected_periods):
        errors.append(f"{label}: must contain exactly {len(expected_periods)} buckets")
        return None
    values: list[float] = []
    for index, (bucket, expected_period) in enumerate(zip(buckets, expected_periods)):
        bucket_label = f"{label}[{index}]"
        if not isinstance(bucket, dict) or set(bucket) != {"period", "net_r"}:
            errors.append(f"{bucket_label}: bucket must contain only period and net_r")
            return None
        if bucket.get("period") != expected_period:
            errors.append(
                f"{bucket_label}: period must equal {expected_period!r} "
                "(no gaps, duplicates, or reordering)"
            )
        net_r = _finite_float(bucket.get("net_r"))
        if net_r is None:
            errors.append(f"{bucket_label}: net_r must be a finite number")
            return None
        values.append(net_r)
    return values


def finite_sum(values: list[float], label: str, errors: list[str]) -> float | None:
    try:
        total = math.fsum(values)
    except (OverflowError, ValueError):
        errors.append(f"{label}: numeric overflow while summing bucket net_r")
        return None
    if not math.isfinite(total):
        errors.append(f"{label}: bucket net_r sum must be finite")
        return None
    return total


def positive_profit_share(
    values: list[float], label: str, errors: list[str]
) -> float | None:
    positives = [value for value in values if value > 0]
    if not positives:
        return 0.0
    total = finite_sum(positives, label, errors)
    return None if total is None else max(positives) / total


def validate_stability_evidence(
    stability: Any,
    hypothesis_id: str,
    run_ids: list[str],
    train_split: Any,
    holdout_split: Any,
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.stability"
    if not isinstance(stability, dict):
        errors.append(f"{label}: stability evidence must be an object")
        return
    train_window = train_split.get("window") if isinstance(train_split, dict) else None
    holdout_window = (
        holdout_split.get("window") if isinstance(holdout_split, dict) else None
    )
    train_bounds = parse_calendar_window(train_window, f"{label}.train", errors)
    holdout_bounds = parse_calendar_window(holdout_window, f"{label}.holdout", errors)
    surface_bounds = parse_calendar_window(stability.get("window"), label, errors)
    if train_bounds is not None and holdout_bounds is not None:
        if train_bounds[1] != holdout_bounds[0]:
            errors.append(f"{label}: train and holdout windows must be contiguous")
        combined = (train_bounds[0], holdout_bounds[1])
        if surface_bounds is not None and surface_bounds != combined:
            errors.append(f"{label}: window must exactly cover train plus holdout")
    if surface_bounds is not None and surface_bounds[1] - surface_bounds[0] != 7:
        errors.append(f"{label}: window must cover exactly 7 calendar years")

    payload = load_bound_json(stability.get("artifact"), f"{label}.artifact", errors)
    if payload is None:
        return
    expected_identity = {
        "schema_version": "registry_stability_surface.v1",
        "artifact_type": "stability_surface",
        "status": "PASS",
        "hypothesis_id": hypothesis_id,
        "run_ids": run_ids,
    }
    for field, value in expected_identity.items():
        if payload.get(field) != value:
            errors.append(f"{label}.artifact: {field} must equal {value!r}")
    validate_producer_artifact(
        payload.get("producer_evidence"),
        f"{label}.artifact.producer_evidence",
        hypothesis_id,
        run_ids,
        "stability_surface",
        errors,
    )
    if payload.get("window") != stability.get("window"):
        errors.append(f"{label}.artifact: window must exactly match registry stability")
    artifact_metrics = payload.get("metrics")
    expected_metrics = {
        key: value for key, value in stability.items() if key not in {"artifact", "window"}
    }
    if artifact_metrics != expected_metrics:
        errors.append(f"{label}.artifact: metrics must exactly match registry stability")

    if surface_bounds is None:
        return
    start_year, end_year = surface_bounds
    month_periods = [
        f"{year:04d}-{month:02d}"
        for year in range(start_year, end_year)
        for month in range(1, 13)
    ]
    half_year_periods = [
        f"{year:04d}-H{half}"
        for year in range(start_year, end_year)
        for half in (1, 2)
    ]
    year_periods = [f"{year:04d}" for year in range(start_year, end_year)]
    month_values = validate_stability_buckets(
        payload.get("month_buckets"),
        month_periods,
        f"{label}.artifact.month_buckets",
        errors,
    )
    half_year_values = validate_stability_buckets(
        payload.get("half_year_buckets"),
        half_year_periods,
        f"{label}.artifact.half_year_buckets",
        errors,
    )
    year_values = validate_stability_buckets(
        payload.get("year_buckets"),
        year_periods,
        f"{label}.artifact.year_buckets",
        errors,
    )
    if month_values is None or half_year_values is None or year_values is None:
        return

    if train_bounds is not None and holdout_bounds is not None:
        train_month_count = (train_bounds[1] - train_bounds[0]) * 12
        train_months = month_values[:train_month_count]
        holdout_months = month_values[train_month_count:]
        train_total = finite_sum(train_months, f"{label}.train_months", errors)
        holdout_total = finite_sum(holdout_months, f"{label}.holdout_months", errors)
        train_expected = (
            _finite_float(train_split.get("net_r_x1_5"))
            if isinstance(train_split, dict)
            else None
        )
        holdout_expected = (
            _finite_float(holdout_split.get("net_r_x1_5"))
            if isinstance(holdout_split, dict)
            else None
        )
        if (
            train_total is None
            or holdout_total is None
            or train_expected is None
            or holdout_expected is None
            or not math.isclose(train_total, train_expected, rel_tol=1e-9, abs_tol=1e-9)
            or not math.isclose(
                holdout_total, holdout_expected, rel_tol=1e-9, abs_tol=1e-9
            )
        ):
            errors.append(
                f"{label}: monthly net_r does not reconcile to train/holdout split totals"
            )

    recomputed_half_years: list[float] = []
    for index in range(0, len(month_values), 6):
        aggregate = finite_sum(
            month_values[index : index + 6],
            f"{label}.artifact.half_year_buckets[{index // 6}]",
            errors,
        )
        if aggregate is None:
            return
        recomputed_half_years.append(aggregate)
    recomputed_years: list[float] = []
    for index in range(0, len(month_values), 12):
        aggregate = finite_sum(
            month_values[index : index + 12],
            f"{label}.artifact.year_buckets[{index // 12}]",
            errors,
        )
        if aggregate is None:
            return
        recomputed_years.append(aggregate)
    for label_name, actual_values, expected_values in (
        ("half_year_buckets", half_year_values, recomputed_half_years),
        ("year_buckets", year_values, recomputed_years),
    ):
        for index, (actual, expected) in enumerate(zip(actual_values, expected_values)):
            sign_matches = (actual > 0) == (expected > 0) and (actual < 0) == (
                expected < 0
            )
            if not sign_matches or not math.isclose(
                actual, expected, rel_tol=1e-12, abs_tol=1e-12
            ):
                errors.append(
                    f"{label}.artifact.{label_name}[{index}]: net_r does not "
                    "equal the underlying month buckets"
                )

    month_concentration = positive_profit_share(
        month_values, f"{label}.artifact.month_buckets", errors
    )
    half_year_concentration = positive_profit_share(
        recomputed_half_years, f"{label}.artifact.half_year_buckets", errors
    )
    year_concentration = positive_profit_share(
        recomputed_years, f"{label}.artifact.year_buckets", errors
    )
    if (
        month_concentration is None
        or half_year_concentration is None
        or year_concentration is None
    ):
        return
    computed = {
        "months": len(month_values),
        "positive_months": sum(value > 0 for value in month_values),
        "positive_month_ratio": sum(value > 0 for value in month_values)
        / len(month_values),
        "max_month_positive_profit_share": month_concentration,
        "half_years": len(recomputed_half_years),
        "positive_half_years": sum(value > 0 for value in recomputed_half_years),
        "positive_half_year_ratio": sum(value > 0 for value in recomputed_half_years)
        / len(recomputed_half_years),
        "max_half_year_positive_profit_share": half_year_concentration,
        "years": len(recomputed_years),
        "positive_years": sum(value > 0 for value in recomputed_years),
        "positive_year_ratio": sum(value > 0 for value in recomputed_years)
        / len(recomputed_years),
        "max_year_positive_profit_share": year_concentration,
    }
    for field, expected in computed.items():
        actual = stability.get(field)
        if isinstance(expected, int):
            matches = (
                isinstance(actual, int)
                and not isinstance(actual, bool)
                and actual == expected
            )
        else:
            actual_number = _finite_float(actual)
            matches = (
                actual_number is not None
                and math.isclose(
                    actual_number, expected, rel_tol=1e-9, abs_tol=1e-9
                )
            )
        if not matches:
            errors.append(f"{label}: {field} does not match recomputed bucket surface")


def validate_portfolio_artifact(
    ref: Any,
    artifact_type: str,
    hypothesis_id: str,
    component_ids: list[str],
    component_run_ids: list[str],
    component_runs: dict[str, list[str]],
    expected_metrics: dict[str, Any],
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.portfolio.{artifact_type}"
    payload = load_bound_json(ref, label, errors)
    if payload is None:
        return
    expected = {
        "schema_version": "registry_portfolio_evidence.v1",
        "artifact_type": artifact_type,
        "status": "PASS",
        "hypothesis_id": hypothesis_id,
        "run_ids": component_run_ids,
        "component_ids": component_ids,
        "component_run_ids": component_run_ids,
        "component_runs": component_runs,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            errors.append(f"{label}: {field} must equal {value!r}")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != set(expected_metrics):
        errors.append(
            f"{label}: portfolio artifact metrics must contain exactly "
            f"{sorted(expected_metrics)}"
        )
    else:
        for field, expected_value in expected_metrics.items():
            actual = _finite_float(metrics.get(field))
            expected_number = _finite_float(expected_value)
            if (
                actual is None
                or expected_number is None
                or not math.isclose(actual, expected_number, rel_tol=1e-9, abs_tol=1e-9)
            ):
                errors.append(f"{label}: metric {field} does not match registry")
    validate_producer_artifact(
        payload.get("producer_evidence"),
        f"{label}.producer_evidence",
        hypothesis_id,
        component_run_ids,
        artifact_type,
        errors,
    )


def validate_split(
    split_name: str,
    split: dict[str, Any],
    hypothesis_id: str,
    run_ids: list[str],
    target_contract: dict[str, Any],
    errors: list[str],
) -> None:
    label = f"{hypothesis_id}.{split_name}"
    validate_cadence_arithmetic(split, label, errors)
    validate_artifact_ref(split.get("report"), f"{label}.report", errors)
    validate_cost_attestation(
        split.get("cost_manifest"),
        split_name,
        split,
        hypothesis_id,
        run_ids,
        errors,
    )
    validate_outcome_attestation(
        split.get("outcome_artifact"),
        split_name,
        split,
        hypothesis_id,
        run_ids,
        errors,
    )

    positive_years = split.get("positive_years")
    total_years = split.get("total_years")
    if isinstance(positive_years, int) and isinstance(total_years, int):
        if positive_years > total_years:
            errors.append(f"{label}: positive_years exceeds total_years")

    controls = split.get("controls")
    if not isinstance(controls, list):
        errors.append(f"{label}: controls must be an array")
        return
    control_ids: list[str] = []
    for index, item in enumerate(controls):
        if not isinstance(item, dict) or not _nonempty_string(item.get("control_id")):
            errors.append(f"{label}.controls[{index}]: control_id must be a string")
            continue
        control_ids.append(item["control_id"])
    if len(control_ids) != len(set(control_ids)):
        errors.append(f"{label}: duplicate control_id values")

    expected_window = target_contract.get(f"{split_name}_window")
    if split.get("window") != expected_window:
        errors.append(f"{label}: window must equal target contract {expected_window!r}")
    expected_controls = target_contract.get("required_controls")
    if isinstance(expected_controls, list) and set(control_ids) != set(expected_controls):
        errors.append(
            f"{label}: controls must be exactly {sorted(expected_controls)}"
        )
    bounds = parse_calendar_window(split.get("window"), f"{label}.window", errors)
    if bounds is not None and total_years != bounds[1] - bounds[0]:
        errors.append(f"{label}: total_years must equal the split calendar span")


def _is_offline_target_metadata(row: dict[str, Any]) -> bool:
    values = (
        row.get("model"),
        row.get("setup_type"),
        row.get("source_provenance"),
        row.get("exact_overrides"),
        row.get("reason"),
        row.get("lane"),
        row.get("feature_family"),
    )
    text = " ".join(str(value).lower() for value in values if value is not None)
    if any(marker in text for marker in OFFLINE_METADATA_MARKERS):
        return True
    validation = row.get("validation")
    if isinstance(validation, dict) and row.get("state") in {"idea", "probe"}:
        cost_state = str(validation.get("cost_stress") or "").strip().lower()
        if any(marker in cost_state for marker in ("blocked", "pending", "unavailable")):
            return True
    return False


def validate_row_semantics(
    row: Any,
    prior_rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(row, dict):
        return ["registry row must be a JSON object"]
    if row.get("record_type") != "candidate":
        return errors
    state = row.get("state")
    source_hash = row.get("source_hash")
    hypothesis_id = str(row.get("hypothesis_id", "<unknown>"))
    if state in EVIDENCE_STATES and prior_rows is not None:
        same_hypothesis = [
            prior
            for prior in prior_rows
            if prior.get("record_type") == "candidate"
            and prior.get("hypothesis_id") == hypothesis_id
        ]
        if any(_is_offline_target_metadata(prior) for prior in same_hypothesis):
            errors.append(
                f"{hypothesis_id}: offline/preflight target requires a new hypothesis_id "
                "before entering challenger or promotion states"
            )
    if isinstance(source_hash, str) and source_hash and state in EVIDENCE_STATES:
        verify_bound_file(
            row.get("source_path"), source_hash, f"{hypothesis_id}.source", errors
        )
    if state not in EVIDENCE_STATES:
        return errors

    if row.get("model") != 0:
        errors.append(f"{hypothesis_id}: {state} requires Model 0 evidence")
    validate_cadence_arithmetic(row.get("metrics", {}), hypothesis_id, errors)
    verify_bound_file(
        row.get("compiled_artifact_path"),
        row.get("compiled_artifact_hash"),
        f"{hypothesis_id}.compiled_artifact",
        errors,
    )
    raw_run_ids = row.get("run_ids", [])
    run_ids = raw_run_ids if isinstance(raw_run_ids, list) else []
    matched_control = row.get("matched_control_run_id")
    if matched_control not in run_ids:
        errors.append(f"{hypothesis_id}: matched_control_run_id is not in run_ids")
    preflight_contract = validate_preflight_clearance(
        row.get("preflight_evidence"),
        hypothesis_id,
        run_ids,
        row.get("symbol"),
        row.get("window"),
        errors,
    )
    control_manifest, challenger_manifest = validate_matched_control_evidence(
        row.get("matched_control_evidence"),
        hypothesis_id,
        run_ids,
        matched_control,
        source_hash,
        row.get("compiled_artifact_hash"),
        row.get("exact_overrides"),
        row.get("symbol"),
        row.get("timeframe"),
        row.get("window"),
        errors,
    )
    matched_evidence = row.get("matched_control_evidence")
    challenger_run_id = (
        matched_evidence.get("challenger_run_id")
        if isinstance(matched_evidence, dict)
        else None
    )
    validate_readout(
        row.get("readout_path"),
        row.get("readout_hash"),
        hypothesis_id,
        state,
        run_ids,
        source_hash,
        row.get("compiled_artifact_hash"),
        matched_control,
        challenger_run_id,
        errors,
    )
    validate_nonrepaint_audit(
        row.get("nonrepaint_audit"),
        hypothesis_id,
        source_hash,
        challenger_run_id,
        matched_evidence.get("challenger_manifest")
        if isinstance(matched_evidence, dict)
        else None,
        errors,
    )

    if state not in PROMOTION_STATES:
        return errors

    promotion = row.get("promotion_evidence")
    if not isinstance(promotion, dict):
        errors.append(f"{hypothesis_id}: promotion_evidence is required")
        promotion = {}
    for split_name in ("train", "holdout"):
        split = promotion.get(split_name)
        if not isinstance(split, dict):
            errors.append(f"{hypothesis_id}: missing {split_name} evidence")
        else:
            validate_split(
                split_name,
                split,
                hypothesis_id,
                run_ids,
                preflight_contract,
                errors,
            )
    train_split = promotion.get("train")
    holdout_split = promotion.get("holdout")
    if isinstance(train_split, dict) and isinstance(holdout_split, dict):
        train_net = _finite_float(train_split.get("net_r_x1_5"))
        holdout_net = _finite_float(holdout_split.get("net_r_x1_5"))
        aggregate_net = _finite_float(row.get("metrics", {}).get("net_r_x1_5"))
        if (
            train_net is None
            or holdout_net is None
            or aggregate_net is None
            or not math.isclose(
                aggregate_net, train_net + holdout_net, rel_tol=1e-9, abs_tol=1e-9
            )
        ):
            errors.append(
                f"{hypothesis_id}: aggregate net_r_x1_5 must equal train plus holdout"
            )
    validate_stability_evidence(
        promotion.get("stability"),
        hypothesis_id,
        run_ids,
        promotion.get("train"),
        promotion.get("holdout"),
        errors,
    )
    validation_artifacts = promotion.get("validation_artifacts")
    if not isinstance(validation_artifacts, dict):
        errors.append(f"{hypothesis_id}: validation_artifacts must be an object")
    else:
        for name, ref in validation_artifacts.items():
            validate_gate_attestation(ref, name, hypothesis_id, run_ids, errors)

    if state == "portfolio-sleeve":
        portfolio = row.get("portfolio_evidence")
        if not isinstance(portfolio, dict):
            errors.append(f"{hypothesis_id}: portfolio_evidence is required")
        else:
            raw_components = portfolio.get("component_ids", [])
            components = raw_components if isinstance(raw_components, list) else []
            if hypothesis_id not in components:
                errors.append(
                    f"{hypothesis_id}: portfolio component_ids must include the candidate"
                )
            resolved_component_runs: list[str] = []
            resolved_component_map: dict[str, list[str]] = {}
            if prior_rows is None:
                errors.append(
                    f"{hypothesis_id}: portfolio validation requires prior ledger rows"
                )
            else:
                for component_id in components:
                    prior_component_rows = [
                        prior
                        for prior in prior_rows
                        if prior.get("record_type") == "candidate"
                        and prior.get("hypothesis_id") == component_id
                    ]
                    if (
                        not prior_component_rows
                        or prior_component_rows[-1].get("state") != "confirmed"
                    ):
                        errors.append(
                            f"{hypothesis_id}: {component_id!r} is not a previously "
                            "confirmed component"
                        )
                        continue
                    component_runs = prior_component_rows[-1].get("run_ids")
                    if (
                        not isinstance(component_runs, list)
                        or not component_runs
                        or any(not _nonempty_string(run_id) for run_id in component_runs)
                    ):
                        errors.append(
                            f"{hypothesis_id}: {component_id!r} has no resolvable confirmed run_ids"
                        )
                        continue
                    canonical_component_runs = sorted(set(component_runs))
                    resolved_component_map[component_id] = canonical_component_runs
                    resolved_component_runs.extend(canonical_component_runs)
            expected_component_runs = sorted(set(resolved_component_runs))
            declared_component_runs = portfolio.get("component_run_ids")
            if declared_component_runs != expected_component_runs:
                errors.append(
                    f"{hypothesis_id}: component_run_ids must equal the union of confirmed component run_ids"
                )
            if portfolio.get("component_runs") != resolved_component_map:
                errors.append(
                    f"{hypothesis_id}: component_runs must resolve every confirmed component to its exact run_ids"
                )
            metric_contracts = {
                "correlation_exposure": {
                    "max_pairwise_abs_correlation": portfolio.get(
                        "max_pairwise_abs_correlation"
                    )
                },
                "overlap_audit": {
                    "max_overlap_share": portfolio.get("max_overlap_share")
                },
                "portfolio_drawdown": {
                    "portfolio_p95_dd_pct": portfolio.get("portfolio_p95_dd_pct"),
                    "risk_budget_dd_pct": portfolio.get("risk_budget_dd_pct"),
                },
                "combined_cost_stress": {
                    "combined_cost_pf_x1_5": portfolio.get("combined_cost_pf_x1_5"),
                    "combined_cost_pf_x2": portfolio.get("combined_cost_pf_x2"),
                },
            }
            for name, expected_metrics in metric_contracts.items():
                validate_portfolio_artifact(
                    portfolio.get(name),
                    name,
                    hypothesis_id,
                    components,
                    expected_component_runs,
                    resolved_component_map,
                    expected_metrics,
                    errors,
                )
            p95_dd = portfolio.get("portfolio_p95_dd_pct")
            risk_budget = portfolio.get("risk_budget_dd_pct")
            if isinstance(p95_dd, (int, float)) and isinstance(
                risk_budget, (int, float)
            ) and p95_dd > risk_budget:
                errors.append(
                    f"{hypothesis_id}: portfolio P95 DD exceeds the declared risk budget"
                )
    return errors


def main() -> int:
    errors: list[str] = []
    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8-sig"),
        parse_constant=reject_nonfinite_json,
        object_pairs_hook=reject_duplicate_keys,
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    rows: list[Any] = []
    for line_number, line in enumerate(
        REGISTRY_PATH.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(
                line,
                parse_constant=reject_nonfinite_json,
                object_pairs_hook=reject_duplicate_keys,
            )
        except Exception as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc}")
            continue
        prior_rows = list(rows)
        rows.append(row)
        row_schema_errors = sorted(
            validator.iter_errors(row), key=lambda item: list(item.path)
        )
        for error in row_schema_errors:
            errors.append(f"line {line_number}: schema: {error.message}")
        if not row_schema_errors:
            for error in validate_row_semantics(row, prior_rows=prior_rows):
                errors.append(f"line {line_number}: {error}")

    if errors:
        print(f"CANDIDATE_REGISTRY_FAIL: rows={len(rows)} errors={len(errors)}")
        for error in errors:
            print(f"- {error}")
        return 1
    counts: dict[str, int] = {}
    for row in rows:
        record_type = str(row.get("record_type"))
        counts[record_type] = counts.get(record_type, 0) + 1
    print(
        "CANDIDATE_REGISTRY_OK: "
        f"rows={len(rows)} "
        + " ".join(f"{name}={count}" for name, count in sorted(counts.items()))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
