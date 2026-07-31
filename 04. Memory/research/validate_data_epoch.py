#!/usr/bin/env python3
"""Validate a frozen campaign aggregate data-epoch contract and evidence ledger."""

from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
from html import unescape
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESEARCH_DIR = Path(__file__).resolve().parent
CANONICAL_WORKSPACE_ROOT = RESEARCH_DIR.parents[1]
WORKSPACE_ROOT = CANONICAL_WORKSPACE_ROOT
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from data_epoch_journal import (  # noqa: E402
    journal_range as _shared_journal_range,
    journal_series_proof as _shared_journal_series_proof,
    model4_mode_errors as _shared_model4_mode_errors,
)

MANDATORY_SYMBOLS = [
    "XAUUSD",
    "BTCUSD",
    "EURUSD",
    "USDJPY",
    "GBPUSD",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
]
MIN_GENERATION = 1
MAX_GENERATION = 100
HEX64 = set("0123456789ABCDEF")
CONTRACT_KEYS = {
    "schema_version",
    "record_type",
    "campaign_id",
    "generation",
    "generation_id",
    "charter",
    "server",
    "timeframe",
    "tester_model",
    "requested_from",
    "availability_cutoff_utc",
    "history_quality",
    "no_skip",
    "mandatory_symbols",
    "evidence_ledger_path",
}
CHARTER_KEYS = {"path", "sha256"}
HQ_KEYS = {"operator", "threshold_pct"}
HEADER_KEYS = {
    "schema_version",
    "record_type",
    "epoch_manifest_sha256",
    "campaign_id",
    "generation",
    "generation_id",
    "charter_sha256",
    "server",
    "timeframe",
    "tester_model",
    "requested_from",
    "availability_cutoff_utc",
    "history_quality",
    "no_skip",
    "mandatory_symbols",
    "prior_epoch_row_sha256",
}
EVIDENCE_KEYS = {
    "schema_version",
    "record_type",
    "symbol",
    "status",
    "selected",
    "prior_epoch_row_sha256",
    "receipt",
    "run_manifest",
    "data_quality_fingerprint",
    "report",
}
ARTIFACT_KEYS = {"path", "sha256"}
DQ_CONTRACT_KEYS = {
    "schema_version",
    "symbol",
    "requested_from",
    "requested_to",
    "history_quality_threshold",
    "coverage_mode",
    "availability_asof_utc",
    "require_tester_journal_bounds",
    "max_journal_delta_bytes",
}
DQ_GATE_KEYS = {
    "contract",
    "history_quality",
    "actual_from",
    "actual_to",
    "coverage_class",
    "series_proof",
    "journal_path",
    "journal_sha256",
    "journal_bytes_read",
    "journal_files_read",
    "journal_truncated",
    "exact_match_count",
    "distinct_range_count",
}
DQ_JOURNAL_DELTA_KEYS = {"path", "sha256", "bytes_read", "files_read", "truncated"}
DQ_FINGERPRINT_BASIS_KEYS = {
    "schema_version",
    "base_data_fingerprint",
    "contract",
    "history_quality",
    "actual_from",
    "actual_to",
    "coverage_class",
    "series_proof",
    "journal_sha256",
    "journal_bytes_read",
    "journal_files_read",
    "journal_truncated",
    "exact_match_count",
    "distinct_range_count",
}
SERIES_PROOF_FIELDS = (
    "m5_synchronized",
    "m5_first_epoch",
    "m5_terminal_first_epoch",
    "m1_server_first_epoch",
    "m1_terminal_first_epoch",
    "m5_bars",
    "terminal_maxbars",
    "copytime_from_epoch",
    "copytime_count",
    "copytime_result",
    "copytime_first_epoch",
    "copytime_last_error",
)
SERIES_PROOF_KEYS = set(SERIES_PROOF_FIELDS) | {"symbol"}
RECEIPT_BINDING_DQ_KEYS = {
    "availability_asof_utc",
    "coverage_mode",
    "history_quality",
    "requested_from",
    "requested_to",
    "require_tester_journal_bounds",
}
RECEIPT_HQ_KEYS = {"operator", "value"}


class ValidationResult(dict[str, Any]):
    pass


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        parse_constant=reject_nonfinite,
        object_pairs_hook=reject_duplicate_keys,
    )


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _line_sha256(raw_without_lf: bytes) -> str:
    return hashlib.sha256(raw_without_lf).hexdigest().upper()


def _is_upper_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX64


def _is_exact_int(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def _parse_z(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_research_date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y.%m.%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _cutoff_research_date(value: Any) -> str | None:
    parsed = _parse_z(value)
    if parsed is None:
        return None
    return parsed.strftime("%Y.%m.%d")


def _ps_json_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not (value == value and value not in {float("inf"), float("-inf")}):
            raise ValueError("non-finite JSON number is forbidden")
        if value.is_integer():
            return str(int(value))
        return format(value, ".15g")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    raise TypeError(f"unsupported JSON scalar: {type(value).__name__}")


def _ps_compact_json(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(str(key), ensure_ascii=False, separators=(",", ":")) + ":" + _ps_compact_json(item)
            for key, item in value.items()
        ) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_ps_compact_json(item) for item in value) + "]"
    return _ps_json_scalar(value)


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _resolve_workspace_path(path_text: Any, errors: list[str], label: str) -> Path | None:
    if not isinstance(path_text, str) or not path_text:
        errors.append(f"{label}: path must be a non-empty string")
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = WORKSPACE_ROOT / path
    resolved = path.resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        errors.append(f"{label}: path must stay under workspace root")
        return None
    return resolved


def _expect_exact_keys(obj: Any, keys: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{label}: must be an object")
        return False
    actual = set(obj)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        errors.append(f"{label}: exact keys required missing={missing} extra={extra}")
        return False
    return True


def _validate_artifact(obj: Any, label: str, errors: list[str]) -> Path | None:
    if not _expect_exact_keys(obj, ARTIFACT_KEYS, label, errors):
        return None
    path = _resolve_workspace_path(obj["path"], errors, label)
    if not _is_upper_sha(obj["sha256"]):
        errors.append(f"{label}: sha256 must be uppercase SHA256")
    if path is None:
        return None
    if not path.is_file():
        errors.append(f"{label}: file is missing: {path}")
        return None
    actual = _raw_sha256(path)
    if obj["sha256"] != actual:
        errors.append(f"{label}: sha256 mismatch expected={obj['sha256']} actual={actual}")
    return path


def _registry_identity_for_model4(
    contract_sha: str,
    errors: list[str],
) -> dict[str, Any] | None:
    registry_path = (
        WORKSPACE_ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    ).resolve()
    if not registry_path.is_file():
        if WORKSPACE_ROOT.resolve() == CANONICAL_WORKSPACE_ROOT.resolve():
            errors.append(f"Model 4 identity registry is missing: {registry_path}")
        return None
    rows_by_sha: dict[str, dict[str, Any]] = {}
    prefix_sha_by_row: dict[str, str] = {}
    matching: list[tuple[int, str, dict[str, Any]]] = []
    digest = hashlib.sha256()
    for line_number, record in enumerate(registry_path.read_bytes().splitlines(keepends=True), 1):
        if not record.endswith(b"\n"):
            errors.append(f"Model 4 identity registry line {line_number} lacks terminal LF")
            continue
        digest.update(record)
        body = record[:-1]
        row_sha = _line_sha256(body)
        prefix_sha_by_row[row_sha] = digest.hexdigest().upper()
        try:
            row = json.loads(
                body.decode("utf-8-sig" if line_number == 1 else "utf-8"),
                parse_constant=reject_nonfinite,
                object_pairs_hook=reject_duplicate_keys,
            )
        except Exception as exc:
            errors.append(f"Model 4 identity registry line {line_number} is invalid: {exc}")
            continue
        if not isinstance(row, dict):
            continue
        rows_by_sha[row_sha] = row
        validation = row.get("validation")
        if (
            row.get("record_type") == "hypothesis_state"
            and _is_exact_int(row.get("model"), 4)
            and isinstance(validation, dict)
            and validation.get("data_epoch_contract_sha256") == contract_sha
        ):
            matching.append((line_number, row_sha, row))
    hypotheses = {str(row.get("hypothesis_id")) for _, _, row in matching}
    if len(hypotheses) != 1:
        errors.append(
            "Model 4 epoch must resolve to exactly one registry hypothesis; "
            f"found={sorted(hypotheses)}"
        )
        return None
    hypothesis_id = next(iter(hypotheses))
    rows = [(line, sha, row) for line, sha, row in matching if row.get("hypothesis_id") == hypothesis_id]
    latest_line, latest_sha, latest = rows[-1]
    immutable = {
        (
            row.get("ea_name"),
            row.get("source_path"),
            row.get("source_hash"),
            row.get("prereg_path"),
            row.get("prereg_sha256"),
        )
        for _, _, row in rows
    }
    if len(immutable) != 1:
        errors.append(f"Model 4 registry identity drifted across rows for {hypothesis_id}")
        return None
    return {
        "hypothesis_id": hypothesis_id,
        "ea_name": latest.get("ea_name"),
        "source_path": latest.get("source_path"),
        "source_sha256": latest.get("source_hash"),
        "prereg_path": latest.get("prereg_path"),
        "prereg_sha256": latest.get("prereg_sha256"),
        "cost_source_manifest_path": _manifest_get(
            latest, "validation", "cost_source_manifest_path"
        ),
        "cost_source_manifest_sha256": _manifest_get(
            latest, "validation", "cost_source_manifest_sha256"
        ),
        "data_epoch_contract_sha256": contract_sha,
        "registry_path": registry_path,
        "rows_by_sha": rows_by_sha,
        "prefix_sha_by_row": prefix_sha_by_row,
        "latest_line": latest_line,
        "latest_row_sha256": latest_sha,
    }


def _receipt_evidence_by_label(
    receipt: dict[str, Any],
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    evidence = receipt.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{label}: receipt evidence must be an array")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"{label}: receipt evidence[{index}] must be an object")
            continue
        item_label = item.get("label")
        if not isinstance(item_label, str) or not item_label:
            errors.append(f"{label}: receipt evidence[{index}] label is invalid")
            continue
        if item_label in result:
            errors.append(f"{label}: duplicate receipt evidence label {item_label}")
            continue
        result[item_label] = item
    return result


def _validate_model4_identity_chain(
    receipt: dict[str, Any],
    receipt_path: Path,
    manifest: dict[str, Any],
    row: dict[str, Any],
    identity: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expected_hypothesis = identity["hypothesis_id"]
    expected_ea = identity["ea_name"]
    binding = receipt.get("binding")
    if receipt.get("hypothesis_id") != expected_hypothesis:
        errors.append(f"{label}: receipt hypothesis_id must equal {expected_hypothesis}")
    if not isinstance(binding, dict):
        return
    for key, expected in {
        "hypothesis_id": expected_hypothesis,
        "ea_name": expected_ea,
        "run_role": "control",
        "telemetry_profile": "none",
    }.items():
        if binding.get(key) != expected:
            errors.append(f"{label}: receipt binding {key} must equal {expected}")
    for key, expected in {
        "hypothesis_id": expected_hypothesis,
        "ea_name": expected_ea,
        "run_role": "control",
        "source_sha256": identity["source_sha256"],
    }.items():
        if manifest.get(key) != expected:
            errors.append(f"{label}: run manifest {key} must equal {expected}")

    evidence = _receipt_evidence_by_label(receipt, label, errors)
    required = {
        "task_packet",
        "candidate_registry",
        "source",
        "prereg",
        "cost_source_manifest",
    }
    missing = sorted(required - set(evidence))
    if missing:
        errors.append(f"{label}: receipt identity evidence missing labels {missing}")
        return

    resolved: dict[str, Path] = {}
    for item_label in sorted(required - {"candidate_registry"}):
        item = evidence[item_label]
        path = _resolve_workspace_path(item.get("path"), errors, f"{label}: {item_label}")
        if path is None or not path.is_file():
            errors.append(f"{label}: receipt {item_label} file is missing")
            continue
        item_sha = item.get("sha256")
        if not _is_upper_sha(item_sha):
            errors.append(f"{label}: receipt {item_label} sha256 is invalid")
            continue
        actual = _raw_sha256(path)
        if actual != item_sha:
            errors.append(
                f"{label}: receipt {item_label} sha256 mismatch expected={item_sha} actual={actual}"
            )
        resolved[item_label] = path

    epoch_sha = identity["data_epoch_contract_sha256"]
    source_path = resolved.get("source")
    if source_path is not None:
        try:
            source_text = source_path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"{label}: source text cannot be read: {exc}")
        else:
            if source_text.count(epoch_sha) != 2:
                errors.append(
                    f"{label}: Model 4 source must bind the epoch manifest SHA exactly twice"
                )

    task_path = resolved.get("task_packet")
    if task_path is None:
        return
    try:
        task = load_strict_json(task_path)
    except Exception as exc:
        errors.append(f"{label}: task packet invalid strict JSON: {exc}")
        return
    if not isinstance(task, dict):
        errors.append(f"{label}: task packet root must be object")
        return
    task_sha = _raw_sha256(task_path)
    if receipt.get("task_packet_sha256") != task_sha:
        errors.append(f"{label}: receipt task_packet_sha256 does not match task packet")
    epoch_override = f"InpEpochManifestSha256={epoch_sha}"
    for owner, overrides in (
        ("receipt binding", binding.get("overrides")),
        ("task packet", task.get("overrides")),
    ):
        parts = str(overrides or "").split(";")
        if parts.count(epoch_override) != 1:
            errors.append(
                f"{label}: {owner} must bind the exact epoch manifest SHA override once"
            )
    for key, expected in {
        "hypothesis_id": expected_hypothesis,
        "ea_name": expected_ea,
        "run_role": "control",
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        "model": 4,
        "symbol": row["symbol"],
        "period": "M5",
        "source_path": identity["source_path"],
        "source_sha256": identity["source_sha256"],
        "prereg_path": identity["prereg_path"],
        "prereg_sha256": identity["prereg_sha256"],
        "cost_source_manifest_path": identity["cost_source_manifest_path"],
        "cost_source_manifest_sha256": identity["cost_source_manifest_sha256"],
    }.items():
        value = task.get(key)
        if key == "model":
            if not _is_exact_int(value, expected):
                errors.append(f"{label}: task packet model must be integer 4")
        elif value != expected:
            errors.append(f"{label}: task packet {key} must equal registry identity")

    registry_row_sha = receipt.get("registry_row_sha256")
    if not _is_upper_sha(registry_row_sha):
        errors.append(f"{label}: receipt registry_row_sha256 is invalid")
        return
    if task.get("registry_row_sha256") != registry_row_sha:
        errors.append(f"{label}: task packet registry_row_sha256 does not match receipt")
    registry_row = identity["rows_by_sha"].get(registry_row_sha)
    if not isinstance(registry_row, dict):
        errors.append(f"{label}: receipt registry row hash is absent from append-only registry")
        return
    for key, expected in {
        "hypothesis_id": expected_hypothesis,
        "ea_name": expected_ea,
        "source_path": identity["source_path"],
        "source_hash": identity["source_sha256"],
        "prereg_path": identity["prereg_path"],
        "prereg_sha256": identity["prereg_sha256"],
        "model": 4,
    }.items():
        value = registry_row.get(key)
        if key == "model":
            if not _is_exact_int(value, expected):
                errors.append(f"{label}: bound registry row model must be integer 4")
        elif value != expected:
            errors.append(f"{label}: bound registry row {key} mismatches expected identity")

    historical_registry_sha = identity["prefix_sha_by_row"].get(registry_row_sha)
    if task.get("registry_sha256") != historical_registry_sha:
        errors.append(f"{label}: task packet registry_sha256 does not match registry prefix")
    registry_evidence = evidence["candidate_registry"]
    registry_evidence_path = _resolve_workspace_path(
        registry_evidence.get("path"), errors, f"{label}: candidate_registry"
    )
    if registry_evidence_path != identity["registry_path"]:
        errors.append(f"{label}: receipt candidate_registry path is not canonical")
    if registry_evidence.get("sha256") != historical_registry_sha:
        errors.append(f"{label}: receipt candidate_registry sha256 does not match registry prefix")

    expected_paths = {
        "source": identity["source_path"],
        "prereg": identity["prereg_path"],
        "cost_source_manifest": identity["cost_source_manifest_path"],
    }
    expected_hashes = {
        "source": identity["source_sha256"],
        "prereg": identity["prereg_sha256"],
        "cost_source_manifest": identity["cost_source_manifest_sha256"],
    }
    for item_label in ("source", "prereg", "cost_source_manifest"):
        item = evidence[item_label]
        path = _resolve_workspace_path(item.get("path"), errors, f"{label}: {item_label}")
        expected_path = _resolve_workspace_path(
            expected_paths[item_label], errors, f"{label}: expected {item_label}"
        )
        if path != expected_path:
            errors.append(f"{label}: receipt {item_label} path mismatches registry identity")
        if item.get("sha256") != expected_hashes[item_label]:
            errors.append(f"{label}: receipt {item_label} sha256 mismatches registry identity")

    research_loop = manifest.get("research_loop")
    if not isinstance(research_loop, dict):
        errors.append(f"{label}: run manifest research_loop identity is missing")
        return
    for key, expected in {
        "hypothesis_id": expected_hypothesis,
        "run_role": "control",
        "prereg_sha256": identity["prereg_sha256"],
        "task_packet_sha256": task_sha,
    }.items():
        if research_loop.get(key) != expected:
            errors.append(f"{label}: run manifest research_loop {key} mismatch")
    if not _same_path(research_loop.get("task_packet_path"), str(task_path)):
        errors.append(f"{label}: run manifest research_loop task_packet_path mismatch")
    rl_evidence = research_loop.get("evidence")
    if not isinstance(rl_evidence, dict):
        errors.append(f"{label}: run manifest research_loop evidence is missing")
    else:
        if not _same_path(rl_evidence.get("execution_receipt_path"), str(receipt_path)):
            errors.append(f"{label}: research_loop execution_receipt_path mismatch")
        if rl_evidence.get("execution_receipt_sha256") != row["receipt"]["sha256"]:
            errors.append(f"{label}: research_loop execution_receipt_sha256 mismatch")


def validate_contract(contract_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        contract = load_strict_json(contract_path)
    except Exception as exc:
        return None, [f"contract invalid strict JSON: {exc}"]
    if not _expect_exact_keys(contract, CONTRACT_KEYS, "contract", errors):
        return None, errors

    if contract["schema_version"] != "alphafactory_data_epoch_contract.v1":
        errors.append("contract: schema_version must be alphafactory_data_epoch_contract.v1")
    if contract["record_type"] != "data_epoch_contract":
        errors.append("contract: record_type must be data_epoch_contract")
    if not isinstance(contract["campaign_id"], str) or not contract["campaign_id"]:
        errors.append("contract: campaign_id must be a non-empty string")
    generation = contract["generation"]
    if type(generation) is not int or not (MIN_GENERATION <= generation <= MAX_GENERATION):
        errors.append("contract: generation must be an integer from 1 through 100")
    expected_generation_id = f"T{generation}" if type(generation) is int else None
    if contract["generation_id"] != expected_generation_id:
        errors.append("contract: generation_id must equal T{generation}")
    if not isinstance(contract["server"], str) or not contract["server"]:
        errors.append("contract: server must be a non-empty string")
    if contract["timeframe"] != "M5":
        errors.append("contract: timeframe must be M5")
    if type(contract["tester_model"]) is not int or contract["tester_model"] not in {0, 4}:
        errors.append("contract: tester_model must be integer 0 or 4")
    if contract["requested_from"] != "1970.01.01":
        errors.append("contract: requested_from must be 1970.01.01")
    cutoff = _parse_z(contract["availability_cutoff_utc"])
    if cutoff is None:
        errors.append("contract: availability_cutoff_utc must be an ISO Z timestamp")
    if contract["no_skip"] is not True:
        errors.append("contract: no_skip must be true")
    if contract["mandatory_symbols"] != MANDATORY_SYMBOLS:
        errors.append("contract: mandatory_symbols must equal the frozen mandatory campaign list in exact order")

    if _expect_exact_keys(contract["history_quality"], HQ_KEYS, "contract.history_quality", errors):
        hq = contract["history_quality"]
        if hq["operator"] != "gt":
            errors.append("contract.history_quality: operator must be gt")
        if not isinstance(hq["threshold_pct"], (int, float)) or not (97 <= float(hq["threshold_pct"]) < 100):
            errors.append("contract.history_quality: threshold_pct must satisfy 97 <= threshold < 100")

    if _expect_exact_keys(contract["charter"], CHARTER_KEYS, "contract.charter", errors):
        charter = contract["charter"]
        if not _is_upper_sha(charter["sha256"]):
            errors.append("contract.charter: sha256 must be uppercase SHA256")
        charter_path = _resolve_workspace_path(charter["path"], errors, "contract.charter")
        if charter_path is not None:
            if not charter_path.is_file():
                errors.append(f"contract.charter: file is missing: {charter_path}")
            else:
                actual = _raw_sha256(charter_path)
                if charter["sha256"] != actual:
                    errors.append(f"contract.charter: sha256 mismatch expected={charter['sha256']} actual={actual}")

    ledger_path = _resolve_workspace_path(contract["evidence_ledger_path"], errors, "contract.evidence_ledger_path")
    if ledger_path is not None and ledger_path.suffix.lower() != ".jsonl":
        errors.append("contract.evidence_ledger_path: evidence ledger must be JSONL")
    return contract, errors


def _validate_header(header: dict[str, Any], contract: dict[str, Any], contract_sha: str, errors: list[str]) -> None:
    if not _expect_exact_keys(header, HEADER_KEYS, "line 1 header", errors):
        return
    expected = {
        "schema_version": "alphafactory_data_epoch_evidence.v1",
        "record_type": "data_epoch_header",
        "epoch_manifest_sha256": contract_sha,
        "campaign_id": contract["campaign_id"],
        "generation": contract["generation"],
        "generation_id": contract["generation_id"],
        "charter_sha256": contract["charter"]["sha256"],
        "server": contract["server"],
        "timeframe": contract["timeframe"],
        "tester_model": contract["tester_model"],
        "requested_from": contract["requested_from"],
        "availability_cutoff_utc": contract["availability_cutoff_utc"],
        "history_quality": contract["history_quality"],
        "no_skip": True,
        "mandatory_symbols": MANDATORY_SYMBOLS,
        "prior_epoch_row_sha256": None,
    }
    for key, value in expected.items():
        if header.get(key) != value:
            errors.append(f"line 1 header: {key} does not match contract")


def _manifest_get(manifest: dict[str, Any], *path: str) -> Any:
    current: Any = manifest
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _same_path(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    return Path(left).resolve() == Path(right).resolve()


def _journal_range(journal_text: str, symbol: str) -> dict[str, Any] | None:
    return _shared_journal_range(journal_text, symbol)


def _journal_series_proof(journal_text: str, symbol: str, actual_from: str) -> dict[str, Any] | None:
    return _shared_journal_series_proof(journal_text, symbol, actual_from)


def _report_history_quality(report_text: str) -> float | None:
    match = re.search(
        r"(?is)<td[^>]*>\s*History Quality\s*:?\s*</td>\s*<td[^>]*>\s*(?:<b>)?\s*([^<]+)",
        report_text,
    )
    if not match:
        return None
    text = unescape(match.group(1)).strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        value = float(text)
    except ValueError:
        return None
    if value != value or value in {float("inf"), float("-inf")}:
        return None
    return value


def _report_server_identity(report_text: str) -> str | None:
    match = re.search(r"(?is)<b>\s*([^<]*\(Build\s+\d+\))\s*</b>", report_text)
    if not match:
        return None
    return unescape(match.group(1)).strip()


def _read_report_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8")


def _model4_real_tick_mode_errors(
    journal_text: str,
    label: str,
    *,
    symbol: str,
    period: str,
    server: str,
) -> list[str]:
    return _shared_model4_mode_errors(
        journal_text,
        label=label,
        symbol=symbol,
        period=period,
        server=server,
    )


def _epoch_receipt_contract(contract: dict[str, Any], symbol: str, expected_to: str | None) -> dict[str, Any]:
    return {
        "availability_asof_utc": contract["availability_cutoff_utc"],
        "coverage_mode": "all_available_asof",
        "history_quality": {"operator": "gt", "value": contract["history_quality"]["threshold_pct"]},
        "requested_from": "1970.01.01",
        "requested_to": expected_to,
        "require_tester_journal_bounds": True,
    }


def _validate_receipt(
    receipt_path: Path,
    row: dict[str, Any],
    contract: dict[str, Any],
    expected_to: str | None,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        receipt = load_strict_json(receipt_path)
    except Exception as exc:
        errors.append(f"{label}: receipt invalid strict JSON: {exc}")
        return None
    if not isinstance(receipt, dict):
        errors.append(f"{label}: receipt root must be an object")
        return None
    if receipt.get("schema_version") != "alphafactory_execution_receipt.v1":
        errors.append(f"{label}: receipt schema_version must be alphafactory_execution_receipt.v1")
    expected_authority = (
        "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
        if contract["tester_model"] == 0
        else "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    )
    if receipt.get("authority") != expected_authority:
        errors.append(f"{label}: receipt authority must equal {expected_authority}")
    binding = receipt.get("binding")
    if not isinstance(binding, dict):
        errors.append(f"{label}: receipt binding must be an object")
        return receipt
    expected_binding = {
        "symbol": row["symbol"],
        "period": "M5",
        "from": "1970.01.01",
        "to": expected_to,
        "model": contract["tester_model"],
    }
    for key, expected in expected_binding.items():
        if key == "model":
            if not _is_exact_int(binding.get(key), expected):
                errors.append(f"{label}: receipt binding model must be integer {expected}")
        elif binding.get(key) != expected:
            errors.append(f"{label}: receipt binding {key} must equal {expected}")
    dq_contract = binding.get("data_quality_contract")
    if not _expect_exact_keys(dq_contract, RECEIPT_BINDING_DQ_KEYS, f"{label}: receipt binding data_quality_contract", errors):
        return receipt
    if not _expect_exact_keys(dq_contract.get("history_quality"), RECEIPT_HQ_KEYS, f"{label}: receipt binding data_quality_contract.history_quality", errors):
        return receipt
    expected_dq = _epoch_receipt_contract(contract, str(row["symbol"]), expected_to)
    if dq_contract != expected_dq:
        errors.append(f"{label}: receipt Stage-A data_quality_contract must exactly match epoch")
    return receipt


def _validate_manifest(
    manifest_path: Path,
    receipt_path: Path,
    row: dict[str, Any],
    contract: dict[str, Any],
    cutoff: datetime,
    label: str,
    errors: list[str],
    identity: dict[str, Any] | None = None,
    identity_required: bool = False,
) -> None:
    try:
        manifest = load_strict_json(manifest_path)
    except Exception as exc:
        errors.append(f"{label}: run manifest invalid strict JSON: {exc}")
        return
    if not isinstance(manifest, dict):
        errors.append(f"{label}: run manifest root must be an object")
        return

    expected_to = _cutoff_research_date(contract["availability_cutoff_utc"])
    expected_scalars = {
        "schema_version": "alphafactory_run_manifest.v2",
        "symbol": row["symbol"],
        "period": "M5",
        "model": contract["tester_model"],
        "from": "1970.01.01",
        "to": expected_to,
    }
    for key, expected in expected_scalars.items():
        if key == "model":
            if not _is_exact_int(manifest.get(key), expected):
                errors.append(f"{label}: run manifest model must be integer {expected}")
        elif manifest.get(key) != expected:
            errors.append(f"{label}: run manifest {key} must equal {expected}")
    if manifest.get("contract_receipt_sha256") != row["receipt"]["sha256"]:
        errors.append(f"{label}: manifest contract_receipt_sha256 must match row receipt sha256")
    if manifest.get("report_sha256") != row["report"]["sha256"]:
        errors.append(f"{label}: manifest report_sha256 must match row report sha256")

    local_run_dir = _resolve_workspace_path(manifest.get("local_run_dir"), errors, f"{label}: local_run_dir")
    report_path = _resolve_workspace_path(manifest.get("report_path"), errors, f"{label}: report_path")
    row_report_path = _resolve_workspace_path(row["report"]["path"], errors, f"{label}: row report")
    if manifest_path.parent.resolve() != local_run_dir:
        errors.append(f"{label}: run manifest parent must equal manifest local_run_dir")
    if local_run_dir is not None and report_path != (local_run_dir / "report.html").resolve():
        errors.append(f"{label}: report_path must be exact run-local report.html")
    if report_path is not None and row_report_path is not None and report_path != row_report_path:
        errors.append(f"{label}: row report path must equal manifest report_path")
    if local_run_dir is not None and report_path is not None:
        try:
            report_path.relative_to(local_run_dir)
        except ValueError:
            errors.append(f"{label}: report_path must be run-local")

    dq_contract = manifest.get("data_quality_contract")
    dq_gate = manifest.get("data_quality_gate")
    journal_delta = manifest.get("data_quality_journal_delta")
    basis = manifest.get("data_quality_fingerprint_basis")
    fingerprint = manifest.get("data_quality_fingerprint")
    data_fingerprint = manifest.get("data_fingerprint")
    if not _expect_exact_keys(dq_contract, DQ_CONTRACT_KEYS, f"{label}: data_quality_contract", errors):
        return
    if not _expect_exact_keys(dq_gate, DQ_GATE_KEYS, f"{label}: data_quality_gate", errors):
        return
    if not _expect_exact_keys(journal_delta, DQ_JOURNAL_DELTA_KEYS, f"{label}: data_quality_journal_delta", errors):
        return
    if not _expect_exact_keys(basis, DQ_FINGERPRINT_BASIS_KEYS, f"{label}: data_quality_fingerprint_basis", errors):
        return
    if not _is_upper_sha(fingerprint) or fingerprint != row["data_quality_fingerprint"]:
        errors.append(f"{label}: data_quality_fingerprint must be uppercase SHA256 and match row")
    if not _is_upper_sha(data_fingerprint):
        errors.append(f"{label}: data_fingerprint must be uppercase SHA256")
    receipt = _validate_receipt(receipt_path, row, contract, expected_to, label, errors)
    if contract["tester_model"] == 4:
        if identity is None and identity_required:
            errors.append(f"{label}: Model 4 expected registry identity is unavailable")
        elif receipt is not None:
            if identity is not None:
                _validate_model4_identity_chain(
                    receipt,
                    receipt_path,
                    manifest,
                    row,
                    identity,
                    label,
                    errors,
                )

    expected_contract_values = {
        "schema_version": "alphafactory_data_quality_contract.v1",
        "symbol": row["symbol"],
        "requested_from": "1970.01.01",
        "requested_to": expected_to,
        "coverage_mode": "all_available_asof",
        "require_tester_journal_bounds": True,
        "max_journal_delta_bytes": 1048576,
    }
    for key, expected in expected_contract_values.items():
        if dq_contract.get(key) != expected:
            errors.append(f"{label}: data_quality_contract {key} must equal {expected}")
    if dq_contract.get("history_quality_threshold") != contract["history_quality"]["threshold_pct"]:
        errors.append(f"{label}: data_quality_contract history_quality_threshold must match contract")
    if _parse_z(dq_contract.get("availability_asof_utc")) != _parse_z(contract["availability_cutoff_utc"]):
        errors.append(f"{label}: data_quality_contract availability_asof_utc must match contract cutoff instant")
    if dq_gate.get("contract") != dq_contract:
        errors.append(f"{label}: data_quality_gate.contract must equal data_quality_contract")
    series_proof = dq_gate.get("series_proof")
    _expect_exact_keys(series_proof, SERIES_PROOF_KEYS, f"{label}: data_quality_gate.series_proof", errors)
    if dq_gate.get("coverage_class") not in {"FULL_2018_PLUS", "BROKER_LIMITED_START"}:
        errors.append(f"{label}: data_quality_gate coverage_class is invalid or truncated-cache evidence")
    if journal_delta.get("path") != "logs/tester_journal_delta.log":
        errors.append(f"{label}: journal delta path must be logs/tester_journal_delta.log")
    if dq_gate.get("journal_path") != journal_delta.get("path"):
        errors.append(f"{label}: data_quality_gate journal_path must match journal delta")
    if dq_gate.get("journal_sha256") != journal_delta.get("sha256"):
        errors.append(f"{label}: data_quality_gate journal_sha256 must match journal delta")
    if dq_gate.get("journal_bytes_read") != journal_delta.get("bytes_read"):
        errors.append(f"{label}: data_quality_gate journal_bytes_read must match journal delta")
    if dq_gate.get("journal_files_read") != journal_delta.get("files_read"):
        errors.append(f"{label}: data_quality_gate journal_files_read must match journal delta")
    if dq_gate.get("journal_truncated") != journal_delta.get("truncated"):
        errors.append(f"{label}: data_quality_gate journal_truncated must match journal delta")

    quality = dq_gate.get("history_quality")
    if not isinstance(quality, (int, float)) or not float(quality) > float(contract["history_quality"]["threshold_pct"]):
        errors.append(f"{label}: data_quality_gate history_quality must be greater than contract threshold")
    actual_from = _parse_research_date(dq_gate.get("actual_from"))
    actual_to = _parse_research_date(dq_gate.get("actual_to"))
    requested_to = _parse_research_date(expected_to)
    if actual_from is None or actual_to is None:
        errors.append(f"{label}: data_quality_gate actual_from/actual_to must use yyyy.MM.dd")
    elif actual_from > actual_to:
        errors.append(f"{label}: data_quality_gate actual_from must not be later than actual_to")
    elif requested_to is not None and actual_to != requested_to:
        errors.append(
            f"{label}: data_quality_gate actual_to must equal the frozen requested_to cutoff"
        )
    if journal_delta.get("truncated") is not False or not isinstance(journal_delta.get("truncated"), bool):
        errors.append(f"{label}: journal delta must be complete and nontruncated")
    if not isinstance(journal_delta.get("bytes_read"), int) or journal_delta["bytes_read"] <= 0:
        errors.append(f"{label}: journal delta bytes_read must be positive")
    if not isinstance(journal_delta.get("files_read"), int) or journal_delta["files_read"] <= 0:
        errors.append(f"{label}: journal delta files_read must be positive")
    if not isinstance(dq_gate.get("exact_match_count"), int) or dq_gate.get("exact_match_count") < 1 or dq_gate.get("distinct_range_count") != 1:
        errors.append(f"{label}: journal history range must have one distinct range and at least one exact-symbol match")

    if local_run_dir is not None:
        journal_path = (local_run_dir / str(journal_delta.get("path"))).resolve()
        try:
            journal_path.relative_to(local_run_dir)
        except ValueError:
            errors.append(f"{label}: journal path must be run-local")
        if not journal_path.is_file():
            errors.append(f"{label}: journal file is missing: {journal_path}")
        elif _is_upper_sha(journal_delta.get("sha256")):
            journal_sha = _raw_sha256(journal_path)
            if journal_sha != journal_delta["sha256"]:
                errors.append(f"{label}: journal sha256 mismatch expected={journal_delta['sha256']} actual={journal_sha}")
            journal_text = journal_path.read_text(encoding="utf-8", errors="replace")
            if contract["tester_model"] == 4:
                errors.extend(
                    _model4_real_tick_mode_errors(
                        journal_text,
                        label,
                        symbol=str(row["symbol"]),
                        period=str(contract["timeframe"]),
                        server=str(contract["server"]),
                    )
                )
            journal_range = _journal_range(journal_text, str(row["symbol"]))
            if journal_range is None:
                errors.append(f"{label}: journal lacks one exact-symbol history synchronization range")
            else:
                for key in ("actual_from", "actual_to", "exact_match_count", "distinct_range_count"):
                    if dq_gate.get(key) != journal_range[key]:
                        errors.append(f"{label}: data_quality_gate {key} does not match journal")
                journal_proof = _journal_series_proof(journal_text, str(row["symbol"]), str(dq_gate.get("actual_from")))
                if journal_proof is None:
                    errors.append(f"{label}: journal D0 series proof is invalid or truncated-cache evidence")
                elif dq_gate.get("coverage_class") != journal_proof["coverage_class"] or series_proof != journal_proof["series_proof"]:
                    errors.append(f"{label}: data_quality_gate series proof/coverage class does not match journal")
        else:
            errors.append(f"{label}: journal sha256 must be uppercase SHA256")

    expected_basis = {
        "schema_version": "alphafactory_data_quality_fingerprint.v1",
        "base_data_fingerprint": data_fingerprint,
        "contract": dq_contract,
        "history_quality": dq_gate.get("history_quality"),
        "actual_from": dq_gate.get("actual_from"),
        "actual_to": dq_gate.get("actual_to"),
        "coverage_class": dq_gate.get("coverage_class"),
        "series_proof": series_proof,
        "journal_sha256": dq_gate.get("journal_sha256"),
        "journal_bytes_read": dq_gate.get("journal_bytes_read"),
        "journal_files_read": dq_gate.get("journal_files_read"),
        "journal_truncated": dq_gate.get("journal_truncated"),
        "exact_match_count": dq_gate.get("exact_match_count"),
        "distinct_range_count": dq_gate.get("distinct_range_count"),
    }
    if basis != expected_basis:
        errors.append(f"{label}: data_quality_fingerprint_basis does not match validated fields")
    else:
        expected_fingerprint = _text_sha256(_ps_compact_json(expected_basis))
        if fingerprint != expected_fingerprint:
            errors.append(f"{label}: data_quality_fingerprint does not match PowerShell-compatible compact JSON basis SHA256")

    if report_path is not None and report_path.is_file():
        try:
            report_text = _read_report_text(report_path)
        except (UnicodeDecodeError, OSError) as exc:
            errors.append(f"{label}: report encoding/read failed: {exc}")
            report_text = ""
        report_hq = _report_history_quality(report_text)
        if report_hq is None:
            errors.append(f"{label}: report History Quality is absent or nonnumeric")
        elif report_hq != dq_gate.get("history_quality"):
            errors.append(f"{label}: report History Quality must equal data_quality_gate history_quality")
        server_identity = _report_server_identity(report_text)
        if server_identity is None:
            errors.append(f"{label}: report server/build identity is absent")
        elif not server_identity.startswith(f"{contract['server']} (Build "):
            errors.append(f"{label}: report server/build identity must contain exact contract server")


def validate_epoch(contract_path: Path, require_complete: bool = False) -> ValidationResult:
    contract_path = contract_path.resolve()
    errors: list[str] = []
    contract, contract_errors = validate_contract(contract_path)
    errors.extend(contract_errors)
    if contract is None:
        return ValidationResult(ok=False, aggregate_ready=False, missing=MANDATORY_SYMBOLS, errors=errors, rows=0)
    ledger_path = _resolve_workspace_path(contract["evidence_ledger_path"], errors, "contract.evidence_ledger_path")
    if ledger_path is None:
        return ValidationResult(ok=False, aggregate_ready=False, missing=MANDATORY_SYMBOLS, errors=errors, rows=0)
    if not ledger_path.is_file():
        errors.append(f"evidence ledger is missing: {ledger_path}")
        return ValidationResult(ok=False, aggregate_ready=False, missing=MANDATORY_SYMBOLS, errors=errors, rows=0)

    selected_pass: dict[str, int] = {}
    seen_selected: dict[str, int] = {}
    contract_sha = _raw_sha256(contract_path)
    model4_identity = (
        _registry_identity_for_model4(contract_sha, errors)
        if contract["tester_model"] == 4
        else None
    )
    model4_identity_required = (
        contract["tester_model"] == 4
        and (
            WORKSPACE_ROOT
            / "04. Memory"
            / "research"
            / "CANDIDATE_REGISTRY.jsonl"
        ).is_file()
    )
    cutoff = _parse_z(contract["availability_cutoff_utc"])
    if cutoff is None:
        cutoff = datetime.max.replace(tzinfo=timezone.utc)
    prior_sha: str | None = None
    rows = 0
    records = ledger_path.read_bytes().splitlines(keepends=True)
    for line_number, record in enumerate(records, 1):
        if not record.endswith(b"\n") or record.count(b"\n") != 1:
            errors.append(f"line {line_number}: ledger rows require exactly one terminal LF")
            continue
        body = record[:-1]
        try:
            raw = body.decode("utf-8-sig" if line_number == 1 else "utf-8", errors="strict")
            row = json.loads(raw, parse_constant=reject_nonfinite, object_pairs_hook=reject_duplicate_keys)
        except Exception as exc:
            errors.append(f"line {line_number}: invalid strict JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: row root must be an object")
            continue
        rows += 1
        if line_number == 1:
            _validate_header(row, contract, contract_sha, errors)
            prior_sha = _line_sha256(body)
            continue
        label = f"line {line_number} {row.get('symbol', '<unknown>')} evidence"
        if not _expect_exact_keys(row, EVIDENCE_KEYS, label, errors):
            prior_sha = _line_sha256(body)
            continue
        if row["schema_version"] != "alphafactory_data_epoch_evidence.v1":
            errors.append(f"{label}: schema_version must be alphafactory_data_epoch_evidence.v1")
        if row["record_type"] != "data_epoch_symbol":
            errors.append(f"{label}: record_type must be data_epoch_symbol")
        if row["symbol"] not in MANDATORY_SYMBOLS:
            errors.append(f"{label}: symbol is not in mandatory campaign universe")
        if row["prior_epoch_row_sha256"] != prior_sha:
            errors.append(f"{label}: prior_epoch_row_sha256 must equal raw SHA256 of prior ledger row")
        if row["selected"] is True:
            previous = seen_selected.get(row["symbol"])
            if previous is not None:
                errors.append(f"{label}: duplicate selected row for symbol; first selected at line {previous}")
            seen_selected[row["symbol"]] = line_number
            if row["status"] == "PASS":
                selected_pass[row["symbol"]] = line_number
        elif row["selected"] is not False:
            errors.append(f"{label}: selected must be boolean")
        if row["status"] not in {"PASS", "FAIL", "INCOMPLETE"}:
            errors.append(f"{label}: status must be PASS, FAIL, or INCOMPLETE")
        if not _is_upper_sha(row["data_quality_fingerprint"]):
            errors.append(f"{label}: data_quality_fingerprint must be uppercase SHA256")
        receipt_path = _validate_artifact(row["receipt"], f"{label}: receipt", errors)
        manifest_path = _validate_artifact(row["run_manifest"], f"{label}: run_manifest", errors)
        _validate_artifact(row["report"], f"{label}: report", errors)
        if row["selected"] is True and row["status"] == "PASS" and receipt_path is not None and manifest_path is not None:
            _validate_manifest(
                manifest_path,
                receipt_path,
                row,
                contract,
                cutoff,
                label,
                errors,
                identity=model4_identity,
                identity_required=model4_identity_required,
            )
        prior_sha = _line_sha256(body)

    if rows == 0:
        errors.append("evidence ledger must contain a header row")
    missing = [symbol for symbol in MANDATORY_SYMBOLS if symbol not in selected_pass]
    aggregate_ready = not errors and not missing
    if require_complete and missing:
        errors.append(f"aggregate incomplete: missing selected PASS rows for {missing}")
    return ValidationResult(
        ok=not errors,
        aggregate_ready=aggregate_ready,
        missing=missing,
        errors=errors,
        rows=rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = validate_epoch(args.contract, require_complete=args.require_complete)
    if result["errors"]:
        for error in result["errors"]:
            print(f"DATA_EPOCH_ERROR {error}", file=sys.stderr)
        return 1
    print(
        "DATA_EPOCH_OK "
        f"rows={result['rows']} "
        f"aggregate_ready={str(result['aggregate_ready']).lower()} "
        f"missing={','.join(result['missing']) if result['missing'] else '-'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
