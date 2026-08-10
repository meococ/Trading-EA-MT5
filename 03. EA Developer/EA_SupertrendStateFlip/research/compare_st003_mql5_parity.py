#!/usr/bin/env python3
"""Compare the ST003 MT5 audit CSV with the sealed full-bar source oracle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
AUDIT_RUN_ID = "ST003-MT5-PARITY-001"
MT5_ATTEMPT_ID = "ST008-MT5-001"
COMPARATOR_ATTEMPT_ID = "ST008-COMPARATOR-001"
ALPHA_PS1_SHA256 = "68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8"
QUANT_ANALYZER_SHA256 = "A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B"
NONREPAINT_TOOL_SHA256 = "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360"
MQL_SOURCE_SHA256 = "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
HYP003_PREREG_SHA256 = "D82037A5730F0766EE872C3A3D1DB5AAB9DA3BD69BADC08B1323446B1FDF924D"
ORACLE_BUILDER_SHA256 = "C8358007C1C359CF4FE42650E9EA8683A29A5770FAF7AF3A4AB90D589DC472E4"
FORMULA_SHA256 = "2B48F3AA01BB2B00EB66A5AE97346F810EF549CEC2626B0DC9F175EEC890211C"
ST002_ANALYZER_SHA256 = "9B44FDCFEA2BC944E4CC70B3C0C9D92E0899BC6F4A9EDE1ECE4AF933F20EAF3B"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
EXACT_OVERRIDES = "InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpParityFileName=ST003_MQL5_PARITY_001.csv"
MQL_COLUMNS = [
    "schema_version", "hypothesis_id", "audit_run_id", "source_epoch", "time_server",
    "atr10", "final_upper", "final_lower", "supertrend", "prior_state", "state",
    "raw_event", "next_source_epoch", "exact_next", "executable_event", "direction",
]
EXACT_FIELDS = [
    "source_epoch", "prior_state", "state", "raw_event", "next_source_epoch",
    "exact_next", "executable_event", "direction",
]
FLOAT_FIELDS = ["atr10", "final_upper", "final_lower", "supertrend"]
ORACLE_KEYS = {
    "schema_version", "hypothesis_id", "source_epoch", "time_utc", "atr10",
    "final_upper", "final_lower", "supertrend", "prior_state", "state",
    "raw_event", "next_source_epoch", "exact_next", "executable_event", "direction",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


ROOT = Path(__file__).resolve().parents[3]
CLOCK_PATH = ROOT / "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
if sha256_file(CLOCK_PATH) != CLOCK_SHA256:
    raise ValueError("clock model SHA mismatch")
SPEC = importlib.util.spec_from_file_location("fivepercent_server_clock", CLOCK_PATH)
if not SPEC or not SPEC.loader:
    raise ValueError("unable to load clock model")
CLOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLOCK)


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_oracle(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("source oracle is empty")
    for row in rows:
        if set(row) != ORACLE_KEYS or row.get("schema_version") != "st003_source_parity_oracle.v1" or row.get("hypothesis_id") != HYPOTHESIS_ID:
            raise ValueError("source oracle schema/identity mismatch")
    return rows


def read_mql(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="ascii", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MQL_COLUMNS:
            raise ValueError(f"MQL audit schema mismatch: {reader.fieldnames}")
        rows = list(reader)
    if not rows:
        raise ValueError("MQL audit is empty")
    return rows


def tolerance(expected: float) -> float:
    return max(1e-10, 1e-12 * abs(expected))


def verify_server_time(epoch: int, text: str, expected_utc: str) -> None:
    server_naive = datetime.strptime(text, "%Y.%m.%d %H:%M:%S")
    epoch_server_naive = datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)
    if server_naive != epoch_server_naive:
        raise ValueError(f"source_epoch/time_server mismatch at {epoch}")
    mapped = CLOCK.server_to_utc(server_naive).replace(tzinfo=timezone.utc)
    target = datetime.fromisoformat(expected_utc.replace("Z", "+00:00"))
    if mapped != target:
        raise ValueError(f"server/UTC mapping mismatch at {epoch}")


def compare_rows(oracle: list[dict[str, Any]], mql: list[dict[str, str]]) -> dict[str, Any]:
    if len(oracle) != len(mql):
        raise ValueError(f"parity row count mismatch: oracle={len(oracle)} mql={len(mql)}")
    oracle_epochs = [int(row["source_epoch"]) for row in oracle]
    mql_epochs = [int(row["source_epoch"]) for row in mql]
    if oracle_epochs != sorted(set(oracle_epochs)) or mql_epochs != sorted(set(mql_epochs)):
        raise ValueError("parity epochs must be unique and strictly increasing")
    if oracle_epochs != mql_epochs:
        missing = sorted(set(oracle_epochs) - set(mql_epochs))[:5]
        extra = sorted(set(mql_epochs) - set(oracle_epochs))[:5]
        raise ValueError(f"parity epoch identity mismatch: missing={missing} extra={extra}")

    max_errors = {field: 0.0 for field in FLOAT_FIELDS}
    raw_count = executable_count = long_count = short_count = gap_count = 0
    for expected, actual in zip(oracle, mql, strict=True):
        epoch = int(expected["source_epoch"])
        if actual["schema_version"] != "st003_mql5_parity.v1" or actual["hypothesis_id"] != HYPOTHESIS_ID or actual["audit_run_id"] != AUDIT_RUN_ID:
            raise ValueError(f"MQL identity mismatch at {epoch}")
        verify_server_time(epoch, actual["time_server"], str(expected["time_utc"]))
        for field in EXACT_FIELDS:
            expected_value = str(expected[field])
            actual_value = actual[field]
            if actual_value != expected_value:
                raise ValueError(f"exact parity mismatch at {epoch} field={field}: {actual_value!r}!={expected_value!r}")
        for field in FLOAT_FIELDS:
            expected_value = float(expected[field])
            actual_value = float(actual[field])
            if not math.isfinite(actual_value):
                raise ValueError(f"non-finite MQL value at {epoch} field={field}")
            error = abs(actual_value - expected_value)
            max_errors[field] = max(max_errors[field], error)
            if error > tolerance(expected_value):
                raise ValueError(f"numeric parity mismatch at {epoch} field={field} error={error}")
        raw = int(actual["raw_event"])
        executable = int(actual["executable_event"])
        exact_next = int(actual["exact_next"])
        raw_count += raw
        executable_count += executable
        gap_count += int(raw == 1 and exact_next == 0)
        if executable:
            if actual["direction"] == "LONG":
                long_count += 1
            elif actual["direction"] == "SHORT":
                short_count += 1
            else:
                raise ValueError(f"executable event lacks direction at {epoch}")
    expected_counts = (690, 683, 7, 339, 344)
    actual_counts = (raw_count, executable_count, gap_count, long_count, short_count)
    if actual_counts != expected_counts:
        raise ValueError(f"frozen event counts mismatch: {actual_counts}!={expected_counts}")
    return {
        "schema_version": "st003_full_bar_parity_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "audit_run_id": AUDIT_RUN_ID,
        "oracle_rows": len(oracle),
        "mql_rows": len(mql),
        "raw_events": raw_count,
        "executable_events": executable_count,
        "gap_rejected_events": gap_count,
        "long_events": long_count,
        "short_events": short_count,
        "max_absolute_errors": max_errors,
        "exact_fields_pass": True,
        "numeric_tolerance_pass": True,
        "server_clock_mapping_pass": True,
        "all_gates_pass": True,
        "verdict": "ENGINEERING_VALID_DIRECT_MQL5_MT5_PARITY_PASS",
        "economics_evaluated": False,
        "trades_executed": 0,
    }


def tree_sha256(path: Path) -> str:
    if not path.is_dir() or not any(item.is_file() for item in path.rglob("*")):
        raise ValueError("AlphaFactory run directory is absent or empty")
    records: list[str] = []
    for item in sorted((p for p in path.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
        records.append(f"{item.relative_to(path).as_posix()}\t{sha256_file(item)}")
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def require_bound_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or not re.fullmatch(r"[A-F0-9]{64}", expected_sha256) or sha256_file(path) != expected_sha256:
        raise ValueError(f"{label} binding mismatch")


def same_path(actual: Any, expected: Path) -> bool:
    return isinstance(actual, str) and Path(actual).resolve() == expected.resolve()


def validate_registry_authority(registry_path: Path, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, str]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == AUTHORITY_HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing frozen HYP008 MT5 parity authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "screened": row.get("state") == "screened",
        "verdict": row.get("verdict") == "FROZEN_ST008_MT5_PARITY_RUN_AUTHORIZED",
        "target": validation.get("parity_target_hypothesis_id") == HYPOTHESIS_ID,
        "run": validation.get("mt5_parity_run_authorized") is True,
        "attempt": validation.get("mt5_parity_attempt_id") == MT5_ATTEMPT_ID,
        "limit": validation.get("mt5_parity_attempt_limit") == 1,
        "unconsumed": metrics.get("mt5_parity_attempts_consumed") == 0,
        "comparator": validation.get("reviewed_comparator_sha256") == sha256_file(Path(__file__).resolve()),
        "mql": validation.get("reviewed_mql_source_sha256") == MQL_SOURCE_SHA256,
        "tests": validation.get("reviewed_test_sha256") == sha256_file(args.test_source.resolve()),
        "run_compile": validation.get("run_compile_authorized") is True,
        "no_standalone_compile": validation.get("static_compile_pass") is False,
        "nonrepaint_manifest": validation.get("nonrepaint_manifest_sha256") == sha256_file(args.nonrepaint_manifest.resolve()),
        "nonrepaint_ratified": validation.get("nonrepaint_audit_ratified") is True,
        "contract_receipt": validation.get("contract_receipt_sha256") == sha256_file(args.contract_receipt.resolve()),
        "collect": validation.get("artifact_collection_authorized") is True,
        "collect_attempt": validation.get("artifact_collection_attempt_id") == "ST008-ARTIFACT-COLLECT-001",
        "collect_limit": validation.get("artifact_collection_attempt_limit") == 1,
        "collect_unconsumed": metrics.get("artifact_collection_attempts_consumed") == 0,
        "collector": validation.get("reviewed_artifact_collector_sha256") == sha256_file(args.artifact_collector.resolve()),
        "comparator_authorized": validation.get("comparator_execution_authorized") is True,
        "comparator_attempt": validation.get("comparator_attempt_id") == COMPARATOR_ATTEMPT_ID,
        "comparator_limit": validation.get("comparator_attempt_limit") == 1,
        "comparator_unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "legacy_tests": validation.get("reviewed_hyp003_test_sha256") == sha256_file(args.legacy_test_source.resolve()),
        "alpha": validation.get("reviewed_alpha_ps1_sha256") == ALPHA_PS1_SHA256,
        "quant": validation.get("reviewed_quant_analyzer_sha256") == QUANT_ANALYZER_SHA256,
        "audit_tool": validation.get("reviewed_nonrepaint_tool_sha256") == NONREPAINT_TOOL_SHA256,
        "no_economics": validation.get("economics_authorized") is False,
        "no_outcomes": validation.get("performance_metrics_authorized") is False,
        "no_optimization": validation.get("optimization_authorized") is False,
        "no_validation": validation.get("validation_authorized") is False,
        "no_holdout": validation.get("holdout_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
    }
    failed = [key for key, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"HYP008 parity authority failed: {failed}")
    bound = {
        "oracle": (args.oracle.resolve(), validation.get("oracle_sha256")),
        "oracle_start": (args.oracle_start.resolve(), validation.get("oracle_start_sha256")),
        "oracle_report": (args.oracle_report.resolve(), validation.get("oracle_report_sha256")),
        "oracle_receipt": (args.oracle_receipt.resolve(), validation.get("oracle_receipt_sha256")),
        "oracle_terminal": (args.oracle_terminal.resolve(), validation.get("oracle_terminal_sha256")),
        "mql_source": (args.mql_source.resolve(), validation.get("reviewed_mql_source_sha256")),
        "test_source": (args.test_source.resolve(), validation.get("reviewed_test_sha256")),
        "legacy_test_source": (args.legacy_test_source.resolve(), validation.get("reviewed_hyp003_test_sha256")),
        "nonrepaint_manifest": (args.nonrepaint_manifest.resolve(), validation.get("nonrepaint_manifest_sha256")),
        "nonrepaint_audit": (args.nonrepaint_audit.resolve(), validation.get("nonrepaint_audit_sha256")),
        "contract_receipt": (args.contract_receipt.resolve(), validation.get("contract_receipt_sha256")),
        "artifact_collector": (args.artifact_collector.resolve(), validation.get("reviewed_artifact_collector_sha256")),
        "alpha_ps1": (ROOT / "02. AlphaFactory/alpha.ps1", validation.get("reviewed_alpha_ps1_sha256")),
        "quant_analyzer": (ROOT / "02. AlphaFactory/analysis/quant_analyzer.py", validation.get("reviewed_quant_analyzer_sha256")),
        "nonrepaint_tool": (ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py", validation.get("reviewed_nonrepaint_tool_sha256")),
        "authority_prereg": (args.authority_prereg.resolve(), row.get("prereg_sha256")),
    }
    for label, (path, expected) in bound.items():
        require_bound_file(path, str(expected or ""), label)
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def validate_nonrepaint_audit(
    path: Path, manifest_path: Path, *, require_collection_authority: bool = False
) -> None:
    audit = load_json(path)
    manifest = load_json(manifest_path)
    expected_hypothesis = AUTHORITY_HYPOTHESIS_ID if require_collection_authority else HYPOTHESIS_ID
    expected_run = "ST008-MQL5-STATIC-001" if require_collection_authority else "ST003-MQL5-STATIC-001"
    if (
        audit.get("schema_version") != "alphafactory_nonrepaint_audit.v1"
        or audit.get("status") != "PASS"
        or audit.get("hypothesis_id") != expected_hypothesis
        or audit.get("run_id") != expected_run
        or audit.get("manifest_sha256") != sha256_file(manifest_path)
        or audit.get("collection_authority_verified") is not require_collection_authority
        or audit.get("findings") != []
    ):
        raise ValueError("non-repaint audit identity/verdict mismatch")
    audited = audit.get("audited_files")
    if not isinstance(audited, list) or len(audited) != 1:
        raise ValueError("non-repaint audit must bind exactly one MQL source")
    source = audited[0]
    if require_collection_authority:
        snapshot_root = Path(str(manifest.get("snapshot_root", ""))).resolve()
        snapshot_source = Path(str(manifest.get("source_snapshot", ""))).resolve()
        if (
            not snapshot_source.is_file()
            or not snapshot_source.is_relative_to(snapshot_root)
            or not same_path(source.get("path"), snapshot_source)
            or source.get("sha256") != MQL_SOURCE_SHA256
            or sha256_file(snapshot_source) != MQL_SOURCE_SHA256
        ):
            raise ValueError("non-repaint audit MQL source binding mismatch")
    else:
        snapshot_source = Path(str(source.get("path", ""))).resolve()
        if not snapshot_source.is_file() or source.get("sha256") != MQL_SOURCE_SHA256:
            raise ValueError("non-repaint audit MQL source binding mismatch")
    if require_collection_authority:
        allowed = audit.get("allowed_new_bar_gates")
        expected_allowed = [{
            "path": str(snapshot_source),
            "line": next(
                index for index, line in enumerate(
                    snapshot_source.read_text(encoding="utf-8-sig").splitlines(), 1
                ) if "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)" in line
            ),
            "rule": "collection_first_date_copytime",
            "function": "CopyTime",
            "disposition": "allowed_collection_provenance_read",
        }]
        if allowed != expected_allowed:
            raise ValueError("non-repaint audit collection provenance allowlist mismatch")


def validate_oracle_chain(args: argparse.Namespace) -> None:
    oracle_receipt = load_json(args.oracle_receipt)
    oracle_terminal = load_json(args.oracle_terminal)
    oracle_report = load_json(args.oracle_report)
    if (
        oracle_receipt.get("schema_version") != "st003_source_parity_oracle_receipt.v1"
        or oracle_receipt.get("hypothesis_id") != HYPOTHESIS_ID
        or oracle_receipt.get("attempt_id") != "ST003-ORACLE-001"
        or oracle_receipt.get("verdict") != "ORACLE_BUILD_PASS"
    ):
        raise ValueError("oracle receipt identity/verdict mismatch")
    bindings = oracle_receipt.get("bindings", {})
    expected_binding_hashes = {
        "preregistration": HYP003_PREREG_SHA256,
        "builder": ORACLE_BUILDER_SHA256,
        "st002_dependency": ST002_ANALYZER_SHA256,
        "formula_dependency": FORMULA_SHA256,
        "clock_model": CLOCK_SHA256,
        "manifest": MANIFEST_SHA256,
        "data": DATA_SHA256,
        "attempt_started": sha256_file(args.oracle_start),
        "oracle": sha256_file(args.oracle),
        "report": sha256_file(args.oracle_report),
    }
    if set(bindings) != set(expected_binding_hashes) | {"registry"} or any(
        bindings.get(label, {}).get("sha256") != expected for label, expected in expected_binding_hashes.items()
    ):
        raise ValueError("oracle receipt output binding mismatch")
    if (
        oracle_terminal.get("schema_version") != "st003_source_parity_oracle_terminal.v1"
        or oracle_terminal.get("hypothesis_id") != HYPOTHESIS_ID
        or oracle_terminal.get("attempt_id") != "ST003-ORACLE-001"
        or oracle_terminal.get("status") != "COMPLETE"
        or oracle_terminal.get("verdict") != "ORACLE_BUILD_PASS"
        or oracle_terminal.get("same_id_retry_authorized") is not False
    ):
        raise ValueError("oracle terminal mismatch")
    if oracle_terminal.get("oracle_receipt_sha256") != sha256_file(args.oracle_receipt):
        raise ValueError("oracle terminal/receipt binding mismatch")
    expected_counts = {
        "source_rows": 107679, "design_rows": 29461, "oracle_comparable_rows": 29460,
        "raw_events": 690, "executable_events": 683, "gap_rejected_events": 7,
        "long_events": 339, "short_events": 344,
    }
    if (
        oracle_report.get("schema_version") != "st003_source_parity_oracle_report.v1"
        or oracle_report.get("hypothesis_id") != HYPOTHESIS_ID
        or oracle_report.get("attempt_id") != "ST003-ORACLE-001"
        or any(oracle_report.get(key) != value for key, value in expected_counts.items())
        or any(oracle_report.get(key) != 0 for key in ("outcome_fields_emitted", "returns_computed", "trades_simulated"))
    ):
        raise ValueError("oracle report frozen invariants mismatch")
    counters = oracle_receipt.get("outcome_blind_counters", {})
    required_zero = (
        "outcome_fields_emitted", "returns_computed", "trades_simulated", "pnl_computed",
        "performance_metrics_computed", "validation_rows_read", "holdout_rows_read",
    )
    if set(counters) != set(required_zero) or any(counters.get(key) != 0 for key in required_zero):
        raise ValueError("oracle receipt outcome counters are not zero")


def decode_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="ignore")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be", errors="ignore")
    return raw.decode("utf-8-sig", errors="ignore")


def validate_artifact_collection_chain(args: argparse.Namespace) -> None:
    receipt = load_json(args.artifact_receipt)
    terminal = load_json(args.artifact_terminal)
    if (
        receipt.get("schema_version") != "st005_mt5_artifact_collection_receipt.v1"
        or receipt.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or receipt.get("target_hypothesis_id") != HYPOTHESIS_ID
        or receipt.get("audit_run_id") != AUDIT_RUN_ID
        or receipt.get("attempt_id") != "ST008-ARTIFACT-COLLECT-001"
        or receipt.get("verdict") != "MT5_AUDIT_ARTIFACT_COLLECTION_PASS"
        or receipt.get("economics_evaluated") is not False
        or receipt.get("orders_executed") != 0
        or receipt.get("trades_executed") != 0
    ):
        raise ValueError("MT5 artifact collection receipt identity/verdict mismatch")
    if (
        terminal.get("schema_version") != "st005_mt5_artifact_collection_terminal.v1"
        or terminal.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or terminal.get("attempt_id") != "ST008-ARTIFACT-COLLECT-001"
        or terminal.get("status") != "COMPLETE"
        or terminal.get("verdict") != receipt.get("verdict")
        or terminal.get("receipt_sha256") != sha256_file(args.artifact_receipt)
        or terminal.get("same_id_retry_authorized") is not False
    ):
        raise ValueError("MT5 artifact collection terminal mismatch")
    run_dir = args.alpha_run_dir.resolve()
    expected_audit = run_dir / "logs/ST003_MQL5_PARITY_001.csv"
    expected_journal = run_dir / "logs/ST003_MT5_PARITY_001_tester_journal.log"
    expected_compile_log = run_dir / "build/ST004_MetaEditor_compile.log"
    expected_data_journal = run_dir / "logs/tester_journal_delta.log"
    expected_run_ex5 = run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5"
    if args.mql_audit.resolve() != expected_audit or args.tester_journal.resolve() != expected_journal:
        raise ValueError("MT5 comparator inputs are not canonical run-local artifacts")
    bindings = receipt.get("bindings", {})
    exact_hashes = {
        "collector": sha256_file(args.artifact_collector),
        "run_manifest": sha256_file(args.run_manifest),
        "run_local_audit": sha256_file(args.mql_audit),
        "run_local_tester_journal": sha256_file(args.tester_journal),
        "run_local_compile_log": sha256_file(expected_compile_log),
        "data_quality_journal_delta": sha256_file(expected_data_journal),
        "run_ex5_snapshot": sha256_file(expected_run_ex5),
        "contract_receipt": sha256_file(args.contract_receipt),
        "alpha_ps1": ALPHA_PS1_SHA256,
        "mt5_run_receipt": sha256_file(ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001/mt5_run_receipt.json"),
        "mt5_run_terminal": sha256_file(ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001/attempt_terminal.json"),
    }
    if any(bindings.get(label, {}).get("sha256") != expected for label, expected in exact_hashes.items()):
        raise ValueError("MT5 artifact collection binding mismatch")
    if (
        bindings.get("source_common_audit", {}).get("sha256") != exact_hashes["run_local_audit"]
        or bindings.get("source_tester_journal", {}).get("sha256") != exact_hashes["run_local_tester_journal"]
        or bindings.get("source_compile_log", {}).get("sha256") != exact_hashes["run_local_compile_log"]
    ):
        raise ValueError("MT5 source-to-run-local copy hash mismatch")
    authority = bindings.get("registry", {})
    if (
        authority.get("registry_sha256") != sha256_file(args.registry)
        or authority.get("latest_row_sha256") != validate_registry_authority(args.registry.resolve(), args)[1]["latest_row_sha256"]
    ):
        raise ValueError("MT5 artifact receipt registry authority mismatch")
    counters = receipt.get("counters", {})
    expected_counters = {
        "rows": 29460, "raw_events": 690, "executable_events": 683,
        "gap_rejected_events": 7, "long_events": 339, "short_events": 344,
    }
    if any(counters.get(key) != value for key, value in expected_counters.items()):
        raise ValueError("MT5 artifact receipt frozen counters mismatch")


def validate_alpha_run(args: argparse.Namespace, authority_row: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(args.run_manifest)
    exact = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID, "run_role": "control",
        "ea_name": "EA_SupertrendStateFlip", "symbol": "XAUUSD", "period": "H1",
        "from": "2005.01.01", "to": "2023.01.01", "model": 0,
        "execution_mode": 0, "fixed_delay_ms": 0, "overrides": EXACT_OVERRIDES,
        "telemetry_tier": "off", "telemetry_profile": "none", "deposit": 10000,
        "leverage": 100, "spread": "current",
    }
    wrong = [key for key, value in exact.items() if manifest.get(key) != value]
    if wrong:
        raise ValueError(f"AlphaFactory run manifest contract mismatch: {wrong}")
    run_dir = args.alpha_run_dir.resolve()
    if args.run_manifest.resolve() != run_dir / "run_manifest.json":
        raise ValueError("run manifest must be the canonical AlphaFactory run artifact")
    if Path(str(manifest.get("local_run_dir", ""))).resolve() != run_dir:
        raise ValueError("run manifest local_run_dir mismatch")
    if manifest.get("source_sha256") != MQL_SOURCE_SHA256 or manifest.get("required_sidecars") != []:
        raise ValueError("run manifest source/sidecar binding mismatch")
    validation = authority_row.get("validation", {})
    run_ex5_snapshot = run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5"
    if args.compiled_ex5.resolve() != run_ex5_snapshot.resolve():
        raise ValueError("compiled EX5 must be the canonical run-local snapshot")
    compiled_sha = sha256_file(run_ex5_snapshot)
    if (
        manifest.get("ex5_sha256") != compiled_sha
        or manifest.get("tester_ex5_sha256") != compiled_sha
        or not same_path(manifest.get("compiled_ex5_file"), ROOT / "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.ex5")
        or not same_path(manifest.get("ex5_snapshot"), run_ex5_snapshot)
    ):
        raise ValueError("run manifest compiled binary binding mismatch")
    receipt_sha = sha256_file(args.contract_receipt)
    if manifest.get("contract_receipt_sha256") != receipt_sha:
        raise ValueError("run manifest contract receipt binding mismatch")
    if not same_path(manifest.get("main_file"), args.mql_source) or not same_path(manifest.get("source_snapshot"), run_dir / "snapshot/source/EA_SupertrendStateFlip.mq5"):
        raise ValueError("run manifest MQL source/snapshot path mismatch")
    if sha256_file(run_dir / "snapshot/source/EA_SupertrendStateFlip.mq5") != MQL_SOURCE_SHA256:
        raise ValueError("run source snapshot SHA mismatch")
    if Path(str(manifest.get("report_path", ""))).resolve() != args.tester_report.resolve() or manifest.get("report_sha256") != sha256_file(args.tester_report):
        raise ValueError("run manifest tester report binding mismatch")
    tree_sha256(run_dir)

    run_compile_log = run_dir / "build/ST004_MetaEditor_compile.log"
    if args.compile_log.resolve() != run_compile_log.resolve():
        raise ValueError("compile log must be the canonical run-local compile artifact")
    run_compile_text = decode_text(run_compile_log)
    if (
        re.search(r"\b0\s+errors?\b", run_compile_text, re.IGNORECASE) is None
        or re.search(r"\b0\s+warnings?\b", run_compile_text, re.IGNORECASE) is None
    ):
        raise ValueError("run-local compile log does not prove zero errors and zero warnings")
    journal = decode_text(args.tester_journal)
    if "ST003_FATAL" in journal:
        raise ValueError("tester journal contains ST003_FATAL")
    summary_pattern = re.compile(
        r"ST003_SUMMARY\|run=ST003-MT5-PARITY-001\|reason=\d+\|rows=29460\|raw=690\|executable=683\|gaps=7\|long=339\|short=344\|failed=false"
    )
    summaries = summary_pattern.findall(journal)
    all_target_summaries = re.findall(r"ST003_SUMMARY\|run=ST003-MT5-PARITY-001\|[^\r\n]*", journal)
    if len(summaries) != 1 or len(all_target_summaries) != 1:
        raise ValueError("tester journal lacks exactly one clean frozen ST003 summary")

    analyzer_path = ROOT / "02. AlphaFactory/analysis/quant_analyzer.py"
    if sha256_file(analyzer_path) != QUANT_ANALYZER_SHA256:
        raise ValueError("AlphaFactory quant analyzer hash drift")
    spec = importlib.util.spec_from_file_location("alphafactory_quant_analyzer", analyzer_path)
    if not spec or not spec.loader:
        raise ValueError("unable to load AlphaFactory report parser")
    analyzer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analyzer
    spec.loader.exec_module(analyzer)
    deals = analyzer.parse_deals_from_html_report(args.tester_report)
    if deals:
        raise ValueError(f"audit-only tester report contains {len(deals)} deals")
    return manifest


def claim_comparator(output_dir: Path, authority: dict[str, str]) -> Path:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("parity comparator attempt already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = output_dir / "attempt_started.json"
    payload = {
        "schema_version": "st003_parity_comparator_attempt_started.v1",
        "authority_hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "target_hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": COMPARATOR_ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "process_id": os.getpid(), "comparator_sha256": sha256_file(Path(__file__).resolve()),
        **authority,
    }
    with marker.open("xb") as handle:
        handle.write(json_bytes(payload))
        handle.flush()
        os.fsync(handle.fileno())
    return marker


def execute(args: argparse.Namespace) -> dict[str, Any]:
    oracle_path = args.oracle.resolve()
    mql_path = args.mql_audit.resolve()
    mql_source = args.mql_source.resolve()
    alpha_run_dir = args.alpha_run_dir.resolve()
    output_dir = args.output_dir.resolve()
    authority_row, authority = validate_registry_authority(args.registry.resolve(), args)
    marker = claim_comparator(output_dir, authority)
    validate_oracle_chain(args)
    validate_nonrepaint_audit(
        args.nonrepaint_audit, args.nonrepaint_manifest, require_collection_authority=True
    )
    validate_artifact_collection_chain(args)
    run_manifest = validate_alpha_run(args, authority_row)
    oracle = read_oracle(oracle_path)
    mql = read_mql(mql_path)
    report = compare_rows(oracle, mql)
    replay = compare_rows(oracle, mql)
    if json_bytes(report) != json_bytes(replay):
        raise ValueError("parity comparator replay mismatch")
    report_bytes = json_bytes(report)
    report_path = output_dir / "st003_full_bar_parity_report.json"
    report_path.write_bytes(report_bytes)
    receipt = {
        "schema_version": "st003_full_bar_parity_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "audit_run_id": AUDIT_RUN_ID,
        "bindings": {
            "oracle": {"path": oracle_path.as_posix(), "sha256": sha256_file(oracle_path)},
            "mql_audit": {"path": mql_path.as_posix(), "sha256": sha256_file(mql_path)},
            "mql_source": {"path": mql_source.as_posix(), "sha256": sha256_file(mql_source)},
            "compiled_ex5": {"path": args.compiled_ex5.resolve().as_posix(), "sha256": sha256_file(args.compiled_ex5)},
            "test_source": {"path": args.test_source.resolve().as_posix(), "sha256": sha256_file(args.test_source)},
            "legacy_test_source": {"path": args.legacy_test_source.resolve().as_posix(), "sha256": sha256_file(args.legacy_test_source)},
            "alpha_ps1": {"path": (ROOT / "02. AlphaFactory/alpha.ps1").as_posix(), "sha256": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1")},
            "quant_analyzer": {"path": (ROOT / "02. AlphaFactory/analysis/quant_analyzer.py").as_posix(), "sha256": sha256_file(ROOT / "02. AlphaFactory/analysis/quant_analyzer.py")},
            "nonrepaint_tool": {"path": (ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py").as_posix(), "sha256": sha256_file(ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py")},
            "clock_model": {"path": CLOCK_PATH.as_posix(), "sha256": sha256_file(CLOCK_PATH)},
            "alpha_run_directory": {"path": alpha_run_dir.as_posix(), "tree_sha256": tree_sha256(alpha_run_dir)},
            "run_manifest": {"path": args.run_manifest.resolve().as_posix(), "sha256": sha256_file(args.run_manifest)},
            "tester_journal": {"path": args.tester_journal.resolve().as_posix(), "sha256": sha256_file(args.tester_journal)},
            "tester_report": {"path": args.tester_report.resolve().as_posix(), "sha256": sha256_file(args.tester_report)},
            "compile_log": {"path": args.compile_log.resolve().as_posix(), "sha256": sha256_file(args.compile_log)},
            "run_compile_log": {"path": (alpha_run_dir / "build/ST004_MetaEditor_compile.log").as_posix(), "sha256": sha256_file(alpha_run_dir / "build/ST004_MetaEditor_compile.log")},
            "run_ex5_snapshot": {"path": (alpha_run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5").as_posix(), "sha256": sha256_file(alpha_run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5")},
            "contract_receipt": {"path": args.contract_receipt.resolve().as_posix(), "sha256": sha256_file(args.contract_receipt)},
            "artifact_collector": {"path": args.artifact_collector.resolve().as_posix(), "sha256": sha256_file(args.artifact_collector)},
            "artifact_collection_receipt": {"path": args.artifact_receipt.resolve().as_posix(), "sha256": sha256_file(args.artifact_receipt)},
            "artifact_collection_terminal": {"path": args.artifact_terminal.resolve().as_posix(), "sha256": sha256_file(args.artifact_terminal)},
            "nonrepaint_audit": {"path": args.nonrepaint_audit.resolve().as_posix(), "sha256": sha256_file(args.nonrepaint_audit)},
            "nonrepaint_manifest": {"path": args.nonrepaint_manifest.resolve().as_posix(), "sha256": sha256_file(args.nonrepaint_manifest)},
            "oracle_receipt": {"path": args.oracle_receipt.resolve().as_posix(), "sha256": sha256_file(args.oracle_receipt)},
            "oracle_terminal": {"path": args.oracle_terminal.resolve().as_posix(), "sha256": sha256_file(args.oracle_terminal)},
            "oracle_report": {"path": args.oracle_report.resolve().as_posix(), "sha256": sha256_file(args.oracle_report)},
            "authority_prereg": {"path": args.authority_prereg.resolve().as_posix(), "sha256": sha256_file(args.authority_prereg)},
            "candidate_registry": {"path": args.registry.resolve().as_posix(), **authority},
            "comparator": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
            "report": {"path": report_path.as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
        },
        "deterministic_replay": "PASS",
        "verdict": report["verdict"],
        "outcome_counters": {"orders": 0, "trades": 0, "returns": 0, "pnl": 0, "profit_factor": 0},
    }
    receipt_bytes = json_bytes(receipt)
    receipt_path = output_dir / "st003_full_bar_parity_receipt.json"
    receipt_path.write_bytes(receipt_bytes)
    terminal = {
        "schema_version": "st003_full_bar_parity_terminal.v1",
        "authority_hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "target_hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": COMPARATOR_ATTEMPT_ID,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "COMPLETE", "verdict": report["verdict"],
        "parity_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    (output_dir / "attempt_terminal.json").write_bytes(json_bytes(terminal))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--oracle-start", type=Path, required=True)
    parser.add_argument("--oracle-report", type=Path, required=True)
    parser.add_argument("--oracle-receipt", type=Path, required=True)
    parser.add_argument("--oracle-terminal", type=Path, required=True)
    parser.add_argument("--mql-audit", type=Path, required=True)
    parser.add_argument("--mql-source", type=Path, required=True)
    parser.add_argument("--compiled-ex5", type=Path, required=True)
    parser.add_argument("--test-source", type=Path, required=True)
    parser.add_argument("--legacy-test-source", type=Path, required=True)
    parser.add_argument("--alpha-run-dir", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--tester-journal", type=Path, required=True)
    parser.add_argument("--tester-report", type=Path, required=True)
    parser.add_argument("--compile-log", type=Path, required=True)
    parser.add_argument("--contract-receipt", type=Path, required=True)
    parser.add_argument("--artifact-collector", type=Path, required=True)
    parser.add_argument("--artifact-receipt", type=Path, required=True)
    parser.add_argument("--artifact-terminal", type=Path, required=True)
    parser.add_argument("--nonrepaint-audit", type=Path, required=True)
    parser.add_argument("--nonrepaint-manifest", type=Path, required=True)
    parser.add_argument("--authority-prereg", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = execute(args)
    print(json_bytes(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
