#!/usr/bin/env python3
"""Append one T2 D0 selected PASS data-epoch evidence row after strict checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html import unescape
from pathlib import Path, PurePosixPath
from typing import Any


HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-001"
EA_NAME = "EA_PTR_T2_DataEpochD0"
EPOCH_CONTRACT_PATH = "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json"
EVIDENCE_LEDGER_PATH = "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EVIDENCE.jsonl"
EPOCH_SHA256 = "F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
SERVER = "FivePercentOnline-Real"
PERIOD = "M5"
MODEL = 0
FROM_DATE = "1970.01.01"
TO_DATE = "2026.07.30"
AVAILABILITY_CUTOFF_UTC = "2026-07-30T23:59:59Z"
HQ_THRESHOLD = 97.0
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
SUMMARY_KEYS = {
    "schema_version",
    "analysis_mode",
    "authority",
    "n_trades",
    "performance_metrics_authorized",
    "generated_at_utc",
}
ALLOWED_COVERAGE_CLASSES = {"FULL_2018_PLUS", "BROKER_LIMITED_START"}
SERIES_PROOF_KEYS = {
    "symbol",
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
}


class EvidenceError(ValueError):
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


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        parse_constant=reject_nonfinite,
        object_pairs_hook=reject_duplicate_keys,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_line_body(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest().upper()


def ps_json_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not (float("-inf") < value < float("inf")):
            raise EvidenceError("non-finite JSON scalar is forbidden")
        return format(value, ".15g")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    raise EvidenceError(f"unsupported JSON scalar: {type(value).__name__}")


def ps_compact_json(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(
            json.dumps(str(key), ensure_ascii=False, separators=(",", ":")) + ":" + ps_compact_json(item)
            for key, item in value.items()
        ) + "}"
    if isinstance(value, list):
        return "[" + ",".join(ps_compact_json(item) for item in value) + "]"
    return ps_json_scalar(value)


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def require_upper_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-F0-9]{64}", value) is None:
        raise EvidenceError(f"{label} must be uppercase SHA256")
    return value


def workspace_path(workspace: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise EvidenceError(f"{label} path must be a non-empty string")
    pure = PurePosixPath(raw)
    if (
        Path(raw).is_absolute()
        or pure.is_absolute()
        or ":" in raw
        or "\\" in raw
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != raw
    ):
        raise EvidenceError(f"{label} path must be normalized workspace-relative POSIX")
    path = workspace.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError as exc:
        raise EvidenceError(f"{label} path escapes workspace") from exc
    return path


def workspace_relative(workspace: Path, path: Path, label: str) -> str:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(workspace.resolve())
    except ValueError as exc:
        raise EvidenceError(f"{label} path is not under workspace: {resolved}") from exc
    return rel.as_posix()


def report_history_quality(report_text: str) -> float:
    match = re.search(
        r"(?is)<td[^>]*>\s*History Quality\s*:?\s*</td>\s*<td[^>]*>\s*(?:<b>)?\s*([^<]+)",
        report_text,
    )
    if not match:
        raise EvidenceError("report History Quality is absent")
    text = unescape(match.group(1)).strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    return float(text)


def report_server_identity(report_text: str) -> str:
    match = re.search(r"(?is)<b>\s*([^<]*\(Build\s+\d+\))\s*</b>", report_text)
    if not match:
        raise EvidenceError("report server/build identity is absent")
    return unescape(match.group(1)).strip()


def validate_epoch_contract(workspace: Path) -> dict[str, Any]:
    path = workspace_path(workspace, EPOCH_CONTRACT_PATH, "epoch contract")
    if sha256_file(path) != EPOCH_SHA256:
        raise EvidenceError("epoch contract SHA mismatch")
    contract = load_json(path)
    expected = {
        "schema_version": "alphafactory_data_epoch_contract.v1",
        "record_type": "data_epoch_contract",
        "campaign_id": "CAMPAIGN-PTR-E01",
        "generation": 2,
        "generation_id": "T2",
        "server": SERVER,
        "timeframe": PERIOD,
        "tester_model": MODEL,
        "requested_from": FROM_DATE,
        "availability_cutoff_utc": AVAILABILITY_CUTOFF_UTC,
        "history_quality": {"operator": "gt", "threshold_pct": HQ_THRESHOLD},
        "no_skip": True,
        "mandatory_symbols": MANDATORY_SYMBOLS,
        "evidence_ledger_path": EVIDENCE_LEDGER_PATH,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise EvidenceError(f"epoch contract {key} mismatch")
    return contract


def validate_summary(path: Path) -> dict[str, Any]:
    summary = load_json(path)
    if not isinstance(summary, dict) or set(summary) != SUMMARY_KEYS:
        raise EvidenceError("enhanced_summary must be exact zero-trade collection schema")
    expected = {
        "schema_version": "alphafactory_zero_trade_collection_summary.v1",
        "analysis_mode": "data_acquisition_only",
        "authority": AUTHORITY,
        "n_trades": 0,
        "performance_metrics_authorized": False,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise EvidenceError(f"enhanced_summary {key} mismatch")
    return summary


def validate_receipt(path: Path, symbol: str) -> dict[str, Any]:
    receipt = load_json(path)
    if not isinstance(receipt, dict):
        raise EvidenceError("receipt root must be object")
    if receipt.get("schema_version") != "alphafactory_execution_receipt.v1":
        raise EvidenceError("receipt schema mismatch")
    if receipt.get("authority") != AUTHORITY:
        raise EvidenceError("receipt authority mismatch")
    binding = receipt.get("binding")
    if not isinstance(binding, dict):
        raise EvidenceError("receipt binding missing")
    expected = {
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": symbol,
        "period": PERIOD,
        "from": FROM_DATE,
        "to": TO_DATE,
        "model": MODEL,
        "telemetry_profile": "none",
        "data_quality_contract": {
            "availability_asof_utc": AVAILABILITY_CUTOFF_UTC,
            "coverage_mode": "all_available_asof",
            "history_quality": {"operator": "gt", "value": HQ_THRESHOLD},
            "requested_from": FROM_DATE,
            "requested_to": TO_DATE,
            "require_tester_journal_bounds": True,
        },
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            raise EvidenceError(f"receipt binding {key} mismatch")
    return receipt


def validate_series_proof(raw: Any, symbol: str) -> None:
    if not isinstance(raw, dict) or set(raw) != SERIES_PROOF_KEYS:
        raise EvidenceError("data_quality_gate series_proof exact fields mismatch")
    if raw.get("symbol") != symbol:
        raise EvidenceError("series_proof symbol mismatch")
    expected_ints = [
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
    ]
    for key in expected_ints:
        if not isinstance(raw.get(key), int):
            raise EvidenceError(f"series_proof {key} must be integer")
    if raw["m5_synchronized"] != 1:
        raise EvidenceError("series_proof m5_synchronized must be 1")
    if raw["copytime_from_epoch"] != 0 or raw["copytime_count"] != 1:
        raise EvidenceError("series_proof CopyTime request mismatch")
    if raw["copytime_result"] != 1 or raw["copytime_last_error"] != 0:
        raise EvidenceError("series_proof CopyTime result invalid")
    for key in (
        "m5_first_epoch",
        "m5_terminal_first_epoch",
        "m1_server_first_epoch",
        "m1_terminal_first_epoch",
        "m5_bars",
        "terminal_maxbars",
        "copytime_first_epoch",
    ):
        if raw[key] <= 0:
            raise EvidenceError(f"series_proof {key} must be positive")
    if raw["copytime_first_epoch"] != raw["m5_first_epoch"]:
        raise EvidenceError("series_proof CopyTime first epoch must match M5 first epoch")


def validate_manifest(
    workspace: Path,
    path: Path,
    summary: dict[str, Any],
    symbol: str,
    contract_receipt_path: Path | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    manifest = load_json(path)
    if not isinstance(manifest, dict):
        raise EvidenceError("run_manifest root must be object")
    expected = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "run_role": "control",
        "symbol": symbol,
        "period": PERIOD,
        "model": MODEL,
        "from": FROM_DATE,
        "to": TO_DATE,
        "telemetry_profile": "none",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise EvidenceError(f"run_manifest {key} mismatch")

    report_path = Path(str(manifest.get("report_path"))).resolve()
    receipt_sha = require_upper_sha(manifest.get("contract_receipt_sha256"), "manifest contract_receipt_sha256")
    report_sha = require_upper_sha(manifest.get("report_sha256"), "manifest report_sha256")
    if not report_path.is_file():
        raise EvidenceError("manifest report_path is missing")
    if sha256_file(report_path) != report_sha:
        raise EvidenceError("report SHA mismatch")
    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    report_hq = report_history_quality(report_text)
    if not report_server_identity(report_text).startswith(f"{SERVER} (Build "):
        raise EvidenceError("report server identity mismatch")

    local_run_dir = Path(str(manifest.get("local_run_dir"))).resolve()
    manifest_path = path.resolve()
    if manifest_path.parent != local_run_dir:
        raise EvidenceError("run_manifest parent must equal local_run_dir")
    try:
        report_path.relative_to(local_run_dir)
    except ValueError as exc:
        raise EvidenceError("report_path must be run-local") from exc

    if contract_receipt_path is not None:
        receipt_path = contract_receipt_path.resolve()
        try:
            receipt_path.relative_to(workspace.resolve())
        except ValueError as exc:
            raise EvidenceError("contract receipt path must be under workspace") from exc
    else:
        receipt_path = local_run_dir / "config" / "contract_receipt.json"
        if not receipt_path.is_file():
            receipt_path = local_run_dir / "contract_receipt.json"
    if not receipt_path.is_file():
        raise EvidenceError("contract receipt file not found")
    if sha256_file(receipt_path) != receipt_sha:
        raise EvidenceError("contract receipt SHA mismatch")
    validate_receipt(receipt_path, symbol)

    dq_contract = manifest.get("data_quality_contract")
    dq_gate = manifest.get("data_quality_gate")
    journal = manifest.get("data_quality_journal_delta")
    basis = manifest.get("data_quality_fingerprint_basis")
    data_fingerprint = require_upper_sha(manifest.get("data_fingerprint"), "manifest data_fingerprint")
    fingerprint = require_upper_sha(manifest.get("data_quality_fingerprint"), "manifest data_quality_fingerprint")
    if dq_contract != {
        "schema_version": "alphafactory_data_quality_contract.v1",
        "symbol": symbol,
        "requested_from": FROM_DATE,
        "requested_to": TO_DATE,
        "history_quality_threshold": HQ_THRESHOLD,
        "coverage_mode": "all_available_asof",
        "availability_asof_utc": AVAILABILITY_CUTOFF_UTC,
        "require_tester_journal_bounds": True,
        "max_journal_delta_bytes": 1048576,
    }:
        raise EvidenceError("run_manifest data_quality_contract mismatch")
    if not isinstance(dq_gate, dict) or dq_gate.get("contract") != dq_contract:
        raise EvidenceError("data_quality_gate contract mismatch")
    coverage_class = dq_gate.get("coverage_class")
    if coverage_class == "INVALID_TRUNCATED_TERMINAL_CACHE":
        raise EvidenceError("coverage_class INVALID_TRUNCATED_TERMINAL_CACHE is rejected")
    if coverage_class not in ALLOWED_COVERAGE_CLASSES:
        raise EvidenceError("data_quality_gate coverage_class is not allowed")
    validate_series_proof(dq_gate.get("series_proof"), symbol)
    if float(dq_gate.get("history_quality", -1.0)) <= HQ_THRESHOLD:
        raise EvidenceError("History Quality does not exceed threshold")
    if report_hq != dq_gate.get("history_quality"):
        raise EvidenceError("report History Quality does not equal manifest gate")
    if not isinstance(dq_gate.get("actual_from"), str) or not dq_gate.get("actual_from"):
        raise EvidenceError("data_quality_gate actual_from missing")
    if dq_gate.get("actual_to") != TO_DATE:
        raise EvidenceError("data_quality_gate actual_to mismatch")
    if not isinstance(journal, dict) or journal.get("path") != "logs/tester_journal_delta.log":
        raise EvidenceError("journal delta path mismatch")
    if journal.get("truncated") is not False or int(journal.get("bytes_read", 0)) <= 0 or int(journal.get("files_read", 0)) <= 0:
        raise EvidenceError("journal delta is incomplete")
    if (
        journal.get("sha256") != dq_gate.get("journal_sha256")
        or journal.get("bytes_read") != dq_gate.get("journal_bytes_read")
        or journal.get("files_read") != dq_gate.get("journal_files_read")
        or journal.get("truncated") != dq_gate.get("journal_truncated")
    ):
        raise EvidenceError("journal delta does not match data_quality_gate")
    journal_path = local_run_dir / "logs" / "tester_journal_delta.log"
    if not journal_path.is_file() or sha256_file(journal_path) != journal.get("sha256"):
        raise EvidenceError("journal delta SHA mismatch")
    expected_basis = {
        "schema_version": "alphafactory_data_quality_fingerprint.v1",
        "base_data_fingerprint": data_fingerprint,
        "contract": dq_contract,
        "history_quality": dq_gate.get("history_quality"),
        "actual_from": dq_gate.get("actual_from"),
        "actual_to": dq_gate.get("actual_to"),
        "journal_sha256": dq_gate.get("journal_sha256"),
        "journal_bytes_read": dq_gate.get("journal_bytes_read"),
        "journal_files_read": dq_gate.get("journal_files_read"),
        "journal_truncated": dq_gate.get("journal_truncated"),
        "exact_match_count": dq_gate.get("exact_match_count"),
        "distinct_range_count": dq_gate.get("distinct_range_count"),
    }
    if basis != expected_basis:
        raise EvidenceError("data_quality_fingerprint_basis mismatch")
    if fingerprint != text_sha256(ps_compact_json(expected_basis)):
        raise EvidenceError("data_quality_fingerprint SHA mismatch")
    if summary["authority"] != AUTHORITY:
        raise EvidenceError("summary authority mismatch")
    return manifest, receipt_path, report_path


def latest_ledger_state(ledger_path: Path, symbol: str) -> tuple[str | None, set[str]]:
    if not ledger_path.is_file():
        raise EvidenceError("evidence ledger missing")
    prior_sha: str | None = None
    selected_pass: set[str] = set()
    for line_number, record in enumerate(ledger_path.read_bytes().splitlines(keepends=True), 1):
        if not record.endswith(b"\n") or record.count(b"\n") != 1:
            raise EvidenceError(f"ledger line {line_number} must have exactly one terminal LF")
        body = record[:-1]
        row = json.loads(body.decode("utf-8-sig" if line_number == 1 else "utf-8"))
        if line_number > 1 and row.get("selected") is True and row.get("status") == "PASS":
            selected_pass.add(str(row.get("symbol")))
        prior_sha = sha256_line_body(body)
    if symbol in selected_pass:
        raise EvidenceError(f"selected PASS row already exists for {symbol}")
    return prior_sha, selected_pass


def build_row(
    workspace: Path,
    symbol: str,
    manifest_path: Path,
    summary_path: Path,
    contract_receipt_path: Path | None = None,
) -> dict[str, Any]:
    if symbol not in MANDATORY_SYMBOLS:
        raise EvidenceError(f"symbol is not in mandatory universe: {symbol}")
    validate_epoch_contract(workspace)
    summary = validate_summary(summary_path)
    manifest, receipt_path, report_path = validate_manifest(workspace, manifest_path, summary, symbol, contract_receipt_path)
    ledger_path = workspace_path(workspace, EVIDENCE_LEDGER_PATH, "evidence ledger")
    prior_sha, _ = latest_ledger_state(ledger_path, symbol)
    return {
        "schema_version": "alphafactory_data_epoch_evidence.v1",
        "record_type": "data_epoch_symbol",
        "symbol": symbol,
        "status": "PASS",
        "selected": True,
        "prior_epoch_row_sha256": prior_sha,
        "receipt": {
            "path": workspace_relative(workspace, receipt_path, "receipt"),
            "sha256": sha256_file(receipt_path),
        },
        "run_manifest": {
            "path": workspace_relative(workspace, manifest_path, "run_manifest"),
            "sha256": sha256_file(manifest_path),
        },
        "data_quality_fingerprint": manifest["data_quality_fingerprint"],
        "report": {
            "path": workspace_relative(workspace, report_path, "report"),
            "sha256": sha256_file(report_path),
        },
    }


def append_row(ledger_path: Path, row: dict[str, Any]) -> None:
    payload = json.dumps(row, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8") + b"\n"
    with ledger_path.open("ab") as handle:
        handle.write(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, choices=MANDATORY_SYMBOLS)
    parser.add_argument("--run-manifest", required=True, type=Path)
    parser.add_argument("--enhanced-summary", required=True, type=Path)
    parser.add_argument("--contract-receipt", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()
    try:
        workspace = args.workspace.resolve()
        receipt_path = args.contract_receipt.resolve() if args.contract_receipt else None
        row = build_row(workspace, args.symbol, args.run_manifest.resolve(), args.enhanced_summary.resolve(), receipt_path)
        if args.append:
            append_row(workspace_path(workspace, EVIDENCE_LEDGER_PATH, "evidence ledger"), row)
            print(f"DATA_EPOCH_ROW_APPENDED symbol={args.symbol}")
        else:
            print(json.dumps(row, ensure_ascii=True, allow_nan=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(f"DATA_EPOCH_APPEND_ERROR {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
