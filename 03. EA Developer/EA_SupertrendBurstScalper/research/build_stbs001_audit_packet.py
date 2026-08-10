#!/usr/bin/env python3
"""Build the hash-bound AlphaFactory packet for the sole HYP001 MT5 audit."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-001"
PARENT_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-012"
EA_NAME = "EA_SupertrendBurstScalper"
PACKET_ATTEMPT_ID = "STBS001-PACKET-BUILD-001"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
SOURCE_SHA256 = "B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D"
PARENT_TERMINAL_ROW_SHA256 = "DCF06201068DDDC52D6B225FD871F1D7A0691F9EB4B864D969A7BFD1422DF8C2"
FROM = "2005.01.01"
TO = "2023.01.01"
OVERRIDES = "InpAuditOnly=true"
ASOF = "2026-08-09T03:30:00Z"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()
PACKET_EVIDENCE_DIR = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-001/STBS001-PACKET-BUILD-001"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def claim_packet_attempt(evidence_dir: Path = PACKET_EVIDENCE_DIR) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=False)
    marker = evidence_dir / "attempt_started.json"
    write_exclusive(
        marker,
        json_bytes(
            {
                "schema_version": "stbs001_packet_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": PACKET_ATTEMPT_ID,
                "status": "STARTED",
                "same_id_retry_authorized": False,
                "started_at_utc": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        ),
    )
    return marker


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def git_lines(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8").splitlines()


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def latest_row(registry: Path, hypothesis_id: str) -> tuple[bytes, dict[str, Any]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis_id:
                matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no {hypothesis_id} row")
    return matches[-1]


def validate_authority(registry: Path) -> tuple[bytes, dict[str, Any]]:
    raw, row = latest_row(registry, HYPOTHESIS_ID)
    parent_raw, parent = latest_row(registry, PARENT_HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "probe",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_STBS001_PACKET_BUILD_AUTHORIZED",
        "source": row.get("source_hash") == SOURCE_SHA256,
        "parent": parent.get("state") == "parked"
        and sha256_bytes(parent_raw) == PARENT_TERMINAL_ROW_SHA256,
        "authority": validation.get("authority") == AUTHORITY,
        "attempt": validation.get("mt5_audit_attempt_id") == "STBS001-MT5-AUDIT-001",
        "limit": validation.get("mt5_audit_attempt_limit") == 1,
        "unconsumed": metrics.get("mt5_audit_attempts_consumed") == 0,
        "packet_build": validation.get("packet_build_authorized") is True,
        "packet_attempt": validation.get("packet_build_attempt_id")
        == "STBS001-PACKET-BUILD-001",
        "packet_limit": validation.get("packet_build_attempt_limit") == 1,
        "packet_unconsumed": metrics.get("packet_build_attempts_consumed") == 0,
        "no_mt5": validation.get("mt5_audit_run_authorized") is False,
        "no_model0": validation.get("model0_data_acquisition_authorized") is False,
        "builder": validation.get("reviewed_packet_builder_sha256")
        == sha256_file(Path(__file__).resolve()),
        "launcher": validation.get("reviewed_mt5_audit_launcher_sha256")
        == sha256_file(
            Path(__file__).resolve().with_name("run_stbs001_mt5_audit.py")
        ),
        "no_economics": validation.get("economics_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
        "no_run_authority": all(
            validation.get(name) is False
            for name in (
                "mt5_authorized",
                "model0_authorized",
                "model0_performance_authorized",
                "model4_authorized",
                "model4_data_acquisition_authorized",
                "model4_performance_authorized",
                "source_run_authorized",
                "compile_authorized",
                "run_compile_authorized",
                "mql5_compile_authorized",
                "standalone_compile_authorized",
                "trade_api_authorized",
                "performance_metrics_authorized",
                "outcome_prices_authorized",
                "post_event_ohlc_authorized",
                "artifact_collection_authorized",
                "comparator_execution_authorized",
                "visual_mode_authorized",
                "network_authorized",
                "paid_requests_authorized",
                "optimization_authorized",
                "validation_authorized",
                "holdout_authorized",
                "research_validation_access_authorized",
                "research_holdout_access_authorized",
                "promotion_eligible",
                "paper_trading_authorized",
                "market_edge_claim_authorized",
                "same_id_retry_authorized",
                "registry_mutation_allowed",
            )
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP001 packet authority failed: {failed}")
    return raw, row


def build_packet(marker: Path) -> dict[str, Any]:
    package = ROOT / "03. EA Developer/EA_SupertrendBurstScalper"
    research = package / "research"
    preflight = research / "preflight/HYP-STBS-XAUUSD-M15-001/V1"
    registry = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    gitignore = ROOT / ".gitignore"
    registry_snapshot = preflight / "candidate_registry.pre_mt5.jsonl"
    packet_path = preflight / "task_packet.control.json"
    receipt_path = preflight / "contract_receipt.control.json"
    source = package / "EA_SupertrendBurstScalper.mq5"
    prereg = research / "HYP-STBS-XAUUSD-M15-001_ENGINEERING_PREREG.md"
    cost = research / "HYP-STBS-XAUUSD-M15-001_COLLECTION_ONLY_COST_MANIFEST.json"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    launcher = research / "run_stbs001_mt5_audit.py"
    builder = Path(__file__).resolve()
    engineering_tests = research / "tests/test_stbs_001_engineering_contract.py"
    harness_tests = research / "tests/test_stbs001_mt5_audit_harness.py"
    nonrepaint_manifest = package / "HYP-STBS-XAUUSD-M15-001_NONREPAINT_MANIFEST.json"
    nonrepaint_audit = research / "HYP-STBS-XAUUSD-M15-001_NONREPAINT_AUDIT.json"
    static_root = research / (
        "evidence/HYP-STBS-XAUUSD-M15-001/STBS001-STATIC-COMPILE-001"
    )
    static_receipt = static_root / "static_compile_archive_receipt.json"
    static_terminal = static_root / "attempt_terminal.json"
    review = research / "HYP-STBS-XAUUSD-M15-001_PRE_MT5_REVIEW.md"
    parent_receipt = ROOT / (
        "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
        "HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001/st009_full_bar_parity_receipt.json"
    )
    parent_terminal = ROOT / (
        "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
        "HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001/attempt_terminal.json"
    )
    oracle = ROOT / (
        "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
        "HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
    )
    alpha = ROOT / "02. AlphaFactory/alpha.ps1"
    audit_tool = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
    required = (
        registry,
        gitignore,
        source,
        prereg,
        cost,
        ea_contract,
        launcher,
        builder,
        engineering_tests,
        harness_tests,
        nonrepaint_manifest,
        nonrepaint_audit,
        static_receipt,
        static_terminal,
        review,
        parent_receipt,
        parent_terminal,
        oracle,
        alpha,
        audit_tool,
    )
    if preflight.exists() or any(not path.is_file() for path in required):
        raise ValueError("preflight already exists or a required frozen input is absent")
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("reviewed source changed before packet build")
    raw_row, row = validate_authority(registry)

    preflight.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(registry, registry_snapshot)
    packet_path.touch()
    receipt_path.touch()
    data_quality = {
        "history_quality": {"operator": "gt", "value": 97.0},
        "coverage_mode": "fixed_window",
        "availability_asof_utc": ASOF,
        "requested_from": FROM,
        "requested_to": TO,
        "require_tester_journal_bounds": True,
    }
    packet: dict[str, Any] = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_candidate": PARENT_HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "source_path": repo_path(source),
        "source_sha256": SOURCE_SHA256,
        "registry_path": repo_path(registry_snapshot),
        "registry_sha256": sha256_file(registry_snapshot),
        "registry_row_sha256": sha256_bytes(raw_row),
        "prereg_path": repo_path(prereg),
        "prereg_sha256": sha256_file(prereg),
        "telemetry_profile": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": "XAUUSD",
        "period": "M15",
        "from": FROM,
        "to": TO,
        "data_quality_contract": data_quality,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "validation_stage": "engineering_correctness",
        "holding_contract": "non_trading_collection",
        "include_closure": [],
        "include_closure_sha256": EMPTY_SHA256,
        "indicator_dependencies": [],
        "broker_fingerprint": None,
        "server_fingerprint": None,
        "account_fingerprint": None,
        "data_fingerprint": None,
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "required_sidecars": [],
        "required_manifest_hashes": [
            "source_sha256",
            "config_sha256",
            "report_sha256",
            "ex5_sha256",
            "includes_sha256",
        ],
        "cost_source_manifest_path": repo_path(cost),
        "cost_source_manifest_sha256": sha256_file(cost),
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    commit = git_lines("rev-parse", "HEAD")[0].strip()
    status = git_lines("status", "--short", "--untracked-files=all")
    status_sha = sha256_bytes("\n".join(status).encode("utf-8"))
    packet["git_commit"] = commit
    packet["git_status"] = status
    packet["git_status_sha256"] = status_sha
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    binding = {
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "M15",
        "from": FROM,
        "to": TO,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "indicator_dependencies": [],
        "broker_fingerprint": None,
        "server_fingerprint": None,
        "account_fingerprint": None,
        "data_fingerprint": None,
        "symbol_geometry": packet["symbol_geometry"],
        "include_closure_sha256": EMPTY_SHA256,
        "data_quality_contract": data_quality,
    }
    evidence = [
        file_evidence("packet_attempt_started", marker),
        file_evidence("task_packet", packet_path),
        file_evidence("candidate_registry", registry_snapshot),
        file_evidence("gitignore", gitignore),
        file_evidence("source", source),
        file_evidence("prereg", prereg),
        file_evidence("cost_source_manifest", cost),
        file_evidence("ea_capability_contract", ea_contract),
        file_evidence("mt5_audit_launcher", launcher),
        file_evidence("packet_builder", builder),
        file_evidence("engineering_tests", engineering_tests),
        file_evidence("harness_tests", harness_tests),
        file_evidence("nonrepaint_manifest", nonrepaint_manifest),
        file_evidence("nonrepaint_audit", nonrepaint_audit),
        file_evidence("static_compile_receipt", static_receipt),
        file_evidence("static_compile_terminal", static_terminal),
        file_evidence("independent_pre_mt5_review", review),
        file_evidence("parent_parity_receipt", parent_receipt),
        file_evidence("parent_parity_terminal", parent_terminal),
        file_evidence("parent_oracle", oracle),
        file_evidence("alpha_ps1", alpha),
        file_evidence("nonrepaint_tool", audit_tool),
    ]
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "packet_build_attempt_id": PACKET_ATTEMPT_ID,
        "packet_attempt_started_sha256": sha256_file(marker),
        "authority_row_sha256": sha256_bytes(raw_row),
        "task_packet_sha256": sha256_file(packet_path),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": binding,
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if git_lines("status", "--short", "--untracked-files=all") != status:
        raise ValueError("git status changed while packet/receipt were being sealed")
    return {
        "task_packet": repo_path(packet_path),
        "task_packet_sha256": sha256_file(packet_path),
        "contract_receipt": repo_path(receipt_path),
        "contract_receipt_sha256": sha256_file(receipt_path),
        "registry_snapshot_sha256": sha256_file(registry_snapshot),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "authority_row_sha256": sha256_bytes(raw_row),
    }


def main() -> int:
    marker = claim_packet_attempt()
    marker_sha256 = sha256_file(marker)
    terminal = PACKET_EVIDENCE_DIR / "attempt_terminal.json"
    try:
        result = build_packet(marker)
        terminal_payload = {
            "schema_version": "stbs001_packet_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": PACKET_ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": "PACKET_BUILD_COMPLETE_NO_MT5_OR_ECONOMICS",
            "attempt_started_sha256": marker_sha256,
            "contract_receipt_sha256": result["contract_receipt_sha256"],
            "same_id_retry_authorized": False,
            "completed_at_utc": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
        write_exclusive(terminal, json_bytes(terminal_payload))
        result["packet_attempt_started"] = repo_path(marker)
        result["packet_attempt_started_sha256"] = marker_sha256
        result["packet_attempt_terminal"] = repo_path(terminal)
        result["packet_attempt_terminal_sha256"] = sha256_file(terminal)
        print(json.dumps(result, indent=2))
        return 0
    except BaseException as exc:
        if not terminal.exists():
            write_exclusive(
                terminal,
                json_bytes(
                    {
                        "schema_version": "stbs001_packet_attempt_terminal.v1",
                        "hypothesis_id": HYPOTHESIS_ID,
                        "attempt_id": PACKET_ATTEMPT_ID,
                        "status": "FAILED",
                        "verdict": "PACKET_BUILD_FAILED_ATTEMPT_CONSUMED",
                        "attempt_started_sha256": marker_sha256,
                        "failure_type": type(exc).__name__,
                        "failure": str(exc),
                        "same_id_retry_authorized": False,
                        "completed_at_utc": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                    }
                ),
            )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
