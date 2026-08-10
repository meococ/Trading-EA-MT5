#!/usr/bin/env python3
"""Build the sole claim-first HYP009 no-trade Model-0 audit packet."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV2"
RESEARCH = PACKAGE / "research"
OLD_PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTrade"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV2.mq5"
EX5 = PACKAGE / "EA_SupertrendBurstScalperTradeV2.ex5"
COMPILE_LOG = PACKAGE / "EA_SupertrendBurstScalperTradeV2.log"
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-009_FLAT_FASTPATH_PREREG.md"
GOVERNANCE_ADDENDUM = RESEARCH / "HYP-STBS-XAUUSD-M15-009_AUDIT_GOVERNANCE_ADDENDUM.md"
STATIC_RESULT = RESEARCH / "HYP-STBS-XAUUSD-M15-009_STATIC_ENGINEERING_RESULT.md"
NONREPAINT_MANIFEST = PACKAGE / "HYP-STBS-XAUUSD-M15-009_NONREPAINT_MANIFEST.json"
NONREPAINT_AUDIT = RESEARCH / "HYP-STBS-XAUUSD-M15-009_NONREPAINT_AUDIT.json"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/"
    "HYP-STBS-XAUUSD-M15-001_COLLECTION_ONLY_COST_MANIFEST.json"
)
HYP008_FAILURE = OLD_PACKAGE / "research" / "HYP-STBS-XAUUSD-M15-008_MODEL0_TIMEOUT_FAILURE.md"
HYP008_REVIEW = OLD_PACKAGE / "research" / "HYP-STBS-XAUUSD-M15-008_MODEL0_TIMEOUT_REVIEW.md"
PRE_PACKET_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-009_PRE_PACKET_REVIEW.md"
RESERVED_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-009_POST_PACKET_REVIEW.md"
SOURCE_TEST = PACKAGE / "tests" / "test_stbs009_trade_fsm_contract.py"
SCENARIO_TEST = PACKAGE / "tests" / "test_stbs009_trade_fsm_scenarios.py"
HARNESS_TEST = PACKAGE / "tests" / "test_stbs009_audit_harness.py"
BUILDER = Path(__file__).resolve()
RUNNER = RESEARCH / "run_stbs009_model0_audit.py"
GITIGNORE = ROOT / ".gitignore"
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
QUANT_ANALYZER = ROOT / "02. AlphaFactory" / "analysis" / "quant_analyzer.py"
ORACLE = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
)
ORACLE_SHA256 = "63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096"
PREFLIGHT = RESEARCH / "preflight" / "HYP-STBS-XAUUSD-M15-009" / "V1"
TASK = PREFLIGHT / "task_packet.control.json"
RECEIPT = PREFLIGHT / "contract_receipt.control.json"
SNAPSHOT = PREFLIGHT / "candidate_registry.pre_mt5.jsonl"
PACKET_ROOT = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-009/STBS009-PACKET-BUILD-001"
STATIC_EX5_ARCHIVE = PACKET_ROOT / "EA_SupertrendBurstScalperTradeV2.static.ex5"
STATIC_LOG_ARCHIVE = PACKET_ROOT / "EA_SupertrendBurstScalperTradeV2.static_compile.log"
HYPOTHESIS = "HYP-STBS-XAUUSD-M15-009"
PARENT = "HYP-STBS-XAUUSD-M15-008"
PACKET_ATTEMPT = "STBS009-PACKET-BUILD-001"
RUN_ATTEMPT = "STBS009-MODEL0-AUDIT-001"
ASOF = "2026-08-09T10:14:00Z"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
PLACEHOLDER = b"RESERVED_NON_AUTHORITATIVE_PLACEHOLDER\n"
RESERVED_REPO_PATH = (
    "03. EA Developer/EA_SupertrendBurstScalperTradeV2/research/"
    "HYP-STBS-XAUUSD-M15-009_POST_PACKET_REVIEW.md"
)
RESERVED_STATUS_LINE = f'?? "{RESERVED_REPO_PATH}"'
EMPTY_SHA = hashlib.sha256(b"").hexdigest().upper()
EXPECTED_DATA_ACCEPTANCE = {
    "history_quality_operator": "gt",
    "history_quality_threshold_pct": 97,
    "coverage_mode": "fixed_window",
    "mandatory_symbols": ["XAUUSD"],
    "no_skip": True,
    "require_tester_journal_bounds": True,
    "require_series_proof": True,
}

PROBE_FALSE_FIELDS = (
    "model0_audit_run_authorized", "mt5_authorized", "model0_authorized",
    "model0_data_acquisition_authorized", "model0_performance_authorized",
    "model4_authorized", "model4_data_acquisition_authorized",
    "model4_performance_authorized", "source_run_authorized",
    "compile_authorized", "run_compile_authorized", "mql5_compile_authorized",
    "standalone_compile_authorized", "trade_api_authorized",
    "performance_metrics_authorized", "outcome_prices_authorized",
    "post_event_ohlc_authorized", "artifact_collection_authorized",
    "comparator_execution_authorized", "visual_mode_authorized",
    "network_authorized", "paid_requests_authorized", "economics_authorized",
    "optimization_authorized", "validation_authorized", "holdout_authorized",
    "research_validation_access_authorized", "research_holdout_access_authorized",
    "validation_access_authorized", "holdout_access_authorized",
    "research_falsification_authorized", "economic_validity_authorized",
    "promotion_eligible", "paper_trading_authorized", "live_trading_authorized",
    "market_edge_claim_authorized", "same_id_retry_authorized",
    "registry_mutation_allowed",
)


def now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stable_bytes(path: Path) -> bytes:
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or len(raw) != before.st_size
    ):
        raise ValueError(f"bound artifact changed while reading: {path}")
    return raw


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def rewrite_claimed(path: Path, raw: bytes) -> None:
    with path.open("r+b") as handle:
        handle.seek(0)
        handle.write(raw)
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode("utf-8").splitlines()


def latest_row_from_bytes(registry_raw: bytes, hypothesis: str) -> tuple[bytes, dict[str, Any]]:
    found: tuple[bytes, dict[str, Any]] | None = None
    for raw in registry_raw.splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis:
                found = raw, row
    if found is None:
        raise ValueError(f"registry has no {hypothesis}")
    return found


def evidence(label: str, path: Path) -> dict[str, str]:
    return {"label": label, "kind": "file", "path": str(path.resolve()),
            "sha256": sha_file(path)}


def claim_packet() -> Path:
    PACKET_ROOT.mkdir(parents=True, exist_ok=False)
    marker = PACKET_ROOT / "attempt_started.json"
    write_exclusive(marker, json_bytes({
        "schema_version": "stbs009_packet_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS,
        "attempt_id": PACKET_ATTEMPT,
        "status": "STARTED",
        "started_at_utc": now_text(),
        "same_id_retry_authorized": False,
    }))
    return marker


def validate_parent(row_raw: bytes, row: dict[str, Any]) -> None:
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "parked",
        "verdict": row.get("verdict")
        == "PARK_ENGINEERING_INVALID_MODEL0_TIMEOUT_PRE_REPORT_NO_ECONOMIC_READOUT",
        "parent_source": row.get("source_hash")
        == "2E0501CC0C19A8FD8418242A0EC64D725EBC14425AD7A1718F9FEB444B977E32",
        "packet_consumed": metrics.get("packet_build_attempts_consumed") == 1,
        "mt5_consumed": metrics.get("mt5_train_attempts_consumed") == 1,
        "run_compile_consumed": metrics.get("run_compile_attempts_consumed") == 1,
        "no_completed_model0": metrics.get("model0_runs") == 0,
        "one_launch": metrics.get("mt5_launches") == 1,
        "no_orders": metrics.get("orders_executed") == 0,
        "no_trades": metrics.get("trades_simulated") == 0,
        "no_returns": metrics.get("returns_computed") == 0,
        "no_economics": metrics.get("economics_executed") is False,
        "failure_hash": validation.get("failure_document_sha256") == sha_file(HYP008_FAILURE),
        "review_hash": validation.get("independent_failure_review_sha256") == sha_file(HYP008_REVIEW),
        "no_retry": validation.get("same_id_retry_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"terminal HYP008 parent failed: {failed}")


def validate_packet_authority(registry_raw: bytes) -> tuple[bytes, dict[str, Any]]:
    raw, row = latest_row_from_bytes(registry_raw, HYPOTHESIS)
    parent_raw, parent = latest_row_from_bytes(registry_raw, PARENT)
    validate_parent(parent_raw, parent)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    issued = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
    checks = {
        "state": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_STBS009_PACKET_BUILD_AUTHORIZED",
        "parent": row.get("parent_candidate") == PARENT,
        "ea": row.get("ea_name") == "EA_SupertrendBurstScalperTradeV2",
        "symbol_timeframe": row.get("symbol") == "XAUUSD" and row.get("timeframe") == "M15",
        "window": row.get("window") == {"from": "2018.01.01", "to": "2022.12.31"},
        "model": row.get("model") == 0,
        "overrides": row.get("exact_overrides") == "InpAuditOnly=true",
        "data_contract_kind": row.get("evidence_contract_kind") == "data_acquisition",
        "no_economic_contract": row.get("acceptance_contract") is None,
        "data_acceptance": row.get("data_acceptance_contract") == EXPECTED_DATA_ACCEPTANCE,
        "authority": validation.get("authority") == AUTHORITY,
        "packet": validation.get("packet_build_authorized") is True,
        "packet_id": validation.get("packet_build_attempt_id") == PACKET_ATTEMPT,
        "packet_limit": validation.get("packet_build_attempt_limit") == 1,
        "packet_unused": metrics.get("packet_build_attempts_consumed") == 0,
        "run_id": validation.get("model0_audit_attempt_id") == RUN_ATTEMPT,
        "run_limit": validation.get("model0_audit_attempt_limit") == 1,
        "run_unused": metrics.get("model0_audit_attempts_consumed") == 0,
        "run_compile_unused": metrics.get("run_compile_attempts_consumed") == 0,
        "zero_model0_runs": metrics.get("model0_runs") == 0,
        "zero_mt5_launches": metrics.get("mt5_launches") == 0,
        "zero_orders": metrics.get("orders_executed") == 0,
        "zero_trades": metrics.get("trades_simulated") == 0,
        "zero_returns": metrics.get("returns_computed") == 0,
        "zero_trials": metrics.get("performance_trials_executed") == 0,
        "economics_unopened": metrics.get("economics_executed") is False,
        "validation_unopened": metrics.get("research_validation_opened") is False,
        "holdout_unopened": metrics.get("research_holdout_opened") is False,
        "source": row.get("source_hash") == sha_file(SOURCE),
        "prereg": row.get("prereg_sha256") == sha_file(PREREG),
        "parent_raw": validation.get("hyp008_terminal_row_sha256") == sha_bytes(parent_raw),
        "nonfuture": issued <= datetime.now(timezone.utc),
        "no_run_permissions": all(validation.get(name) is False for name in PROBE_FALSE_FIELDS),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP009 packet authority failed: {failed}")
    bound = {
        BUILDER: "reviewed_packet_builder_sha256",
        RUNNER: "reviewed_model0_audit_launcher_sha256",
        HARNESS_TEST: "reviewed_audit_harness_test_sha256",
        SOURCE_TEST: "reviewed_source_contract_test_sha256",
        SCENARIO_TEST: "reviewed_source_scenario_test_sha256",
        GOVERNANCE_ADDENDUM: "governance_addendum_sha256",
        STATIC_RESULT: "static_engineering_result_sha256",
        NONREPAINT_MANIFEST: "nonrepaint_manifest_sha256",
        NONREPAINT_AUDIT: "nonrepaint_audit_sha256",
        EA_CONTRACT: "ea_contract_sha256",
        COST: "cost_source_manifest_sha256",
        HYP008_FAILURE: "hyp008_failure_sha256",
        HYP008_REVIEW: "hyp008_independent_review_sha256",
        PRE_PACKET_REVIEW: "independent_pre_packet_review_sha256",
        ORACLE: "parent_oracle_sha256",
        GITIGNORE: "gitignore_sha256",
        ALPHA: "alphafactory_sha256",
        QUANT_ANALYZER: "quant_analyzer_sha256",
    }
    for path, field in bound.items():
        expected = validation.get(field)
        if not isinstance(expected, str) or not re.fullmatch(r"[A-F0-9]{64}", expected):
            raise ValueError(f"missing authority hash: {field}")
        if sha_file(path) != expected:
            raise ValueError(f"bound artifact changed: {field}")
    if validation.get("parent_oracle_sha256") != ORACLE_SHA256:
        raise ValueError("packet authority does not bind the frozen ST003 oracle")
    manifest = json.loads(NONREPAINT_MANIFEST.read_text(encoding="utf-8"))
    audit = json.loads(NONREPAINT_AUDIT.read_text(encoding="utf-8"))
    expected_audited = [{"path": str(SOURCE.resolve()), "sha256": sha_file(SOURCE)}]
    if (
        manifest.get("hypothesis_id") != HYPOTHESIS
        or manifest.get("source_sha256") != sha_file(SOURCE)
        or Path(str(manifest.get("source_snapshot", ""))).resolve() != SOURCE.resolve()
        or audit.get("status") != "PASS"
        or audit.get("hypothesis_id") != HYPOTHESIS
        or audit.get("manifest_sha256") != sha_file(NONREPAINT_MANIFEST)
        or audit.get("audited_files") != expected_audited
        or audit.get("findings") != []
    ):
        raise ValueError("static non-repaint evidence chain is invalid")
    if RESERVED_REVIEW.read_bytes() != PLACEHOLDER:
        raise ValueError("reserved post-packet review is not the frozen placeholder")
    review_text = PRE_PACKET_REVIEW.read_text(encoding="utf-8", errors="strict")
    if not review_text.startswith(
        "# HYP009 independent pre-packet review\n\nVerdict: `PASS_PRE_PACKET_AUTHORITY`\n"
    ):
        raise ValueError("independent pre-packet review has not passed the fresh harness")
    return raw, row


def archive_static_compile(validation: dict[str, Any]) -> tuple[str, str]:
    ex5_raw = stable_bytes(EX5)
    compile_raw = stable_bytes(COMPILE_LOG)
    ex5_sha = sha_bytes(ex5_raw)
    compile_sha = sha_bytes(compile_raw)
    if (
        not ex5_raw
        or ex5_sha != validation.get("static_ex5_sha256")
        or compile_sha != validation.get("static_compile_log_sha256")
    ):
        raise ValueError("captured static compile bytes differ from packet authority")
    compile_text = compile_raw.decode("utf-16", errors="strict")
    if compile_text.count("Result: 0 errors, 0 warnings") != 1:
        raise ValueError("captured static compile log is not exact 0E/0W")
    write_exclusive(STATIC_EX5_ARCHIVE, ex5_raw)
    write_exclusive(STATIC_LOG_ARCHIVE, compile_raw)
    if (
        sha_file(STATIC_EX5_ARCHIVE) != ex5_sha
        or sha_file(STATIC_LOG_ARCHIVE) != compile_sha
    ):
        raise ValueError("immutable static compile archive mismatch")
    return ex5_sha, compile_sha


def build_packet(marker: Path) -> dict[str, str]:
    registry_raw = REGISTRY.read_bytes()
    raw_row, row = validate_packet_authority(registry_raw)
    archive_static_compile(row["validation"])
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    issued = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
    started = datetime.fromisoformat(marker_payload["started_at_utc"].replace("Z", "+00:00"))
    if issued > started:
        raise ValueError("packet authority postdates durable packet claim")
    PREFLIGHT.mkdir(parents=True, exist_ok=False)
    write_exclusive(SNAPSHOT, registry_raw)
    write_exclusive(TASK, b"")
    write_exclusive(RECEIPT, b"")
    commit = git_lines("rev-parse", "HEAD")[0].strip()
    status = git_lines("status", "--short", "--untracked-files=all")
    if status.count(RESERVED_STATUS_LINE) != 1:
        raise ValueError("reserved post-packet review path is absent or duplicated")
    status_sha = sha_bytes("\n".join(status).encode("utf-8"))
    dq = {
        "history_quality": {"operator": "gt", "value": 97.0},
        "coverage_mode": "fixed_window", "availability_asof_utc": ASOF,
        "requested_from": "2005.01.01", "requested_to": "2023.01.01",
        "require_tester_journal_bounds": True,
    }
    reserved = [{
        "path": RESERVED_REPO_PATH,
        "sealed_status_line": RESERVED_STATUS_LINE,
        "placeholder_status": "RESERVED_NON_AUTHORITATIVE_PLACEHOLDER",
        "immutable_evidence": False, "final_review": False,
    }]
    binding = {
        "hypothesis_id": HYPOTHESIS, "run_role": "control",
        "ea_name": "EA_SupertrendBurstScalperTradeV2", "symbol": "XAUUSD",
        "period": "M15", "from": "2005.01.01", "to": "2023.01.01",
        "model": 0, "execution_mode": 0, "fixed_delay_ms": 0,
        "overrides": "InpAuditOnly=true", "telemetry_tier": "off",
        "telemetry_profile": "none", "deposit": 10000, "leverage": 100,
        "spread": "current", "required_sidecars": [], "visual_mode": False,
        "indicator_dependencies": [], "broker_fingerprint": None,
        "server_fingerprint": None, "account_fingerprint": None,
        "data_fingerprint": None,
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "include_closure_sha256": EMPTY_SHA, "data_quality_contract": dq,
    }
    task = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "authority": AUTHORITY, **binding,
        "parent_candidate": PARENT,
        "source_path": repo_path(SOURCE), "source_sha256": sha_file(SOURCE),
        "registry_path": repo_path(SNAPSHOT), "registry_sha256": sha_file(SNAPSHOT),
        "registry_row_sha256": sha_bytes(raw_row), "prereg_path": repo_path(PREREG),
        "prereg_sha256": sha_file(PREREG), "validation_stage": "engineering_correctness",
        "holding_contract": "non_trading_collection", "include_closure": [],
        "required_manifest_hashes": ["source_sha256", "config_sha256",
                                     "report_sha256", "ex5_sha256", "includes_sha256"],
        "cost_source_manifest_path": repo_path(COST),
        "cost_source_manifest_sha256": sha_file(COST),
        "data_acceptance_contract": EXPECTED_DATA_ACCEPTANCE,
        "performance_metrics_authorized": False, "economics_authorized": False,
        "promotion_eligible": False, "git_commit": commit,
        "git_status": status, "git_status_sha256": status_sha,
        "reserved_mutable_control_paths": reserved,
    }
    rewrite_claimed(TASK, (json.dumps(task, indent=2) + "\n").encode("utf-8"))
    evidence_paths = (
        ("packet_attempt_started", marker), ("task_packet", TASK),
        ("candidate_registry", SNAPSHOT), ("source", SOURCE), ("prereg", PREREG),
        ("audit_governance_addendum", GOVERNANCE_ADDENDUM),
        ("cost_source_manifest", COST), ("static_engineering_result", STATIC_RESULT),
        ("nonrepaint_manifest", NONREPAINT_MANIFEST),
        ("nonrepaint_audit", NONREPAINT_AUDIT), ("ea_capability_contract", EA_CONTRACT),
        ("static_ex5_archive", STATIC_EX5_ARCHIVE),
        ("static_compile_log_archive", STATIC_LOG_ARCHIVE),
        ("hyp008_timeout_failure", HYP008_FAILURE),
        ("hyp008_independent_timeout_review", HYP008_REVIEW),
        ("parent_st003_oracle", ORACLE),
        ("independent_pre_packet_review", PRE_PACKET_REVIEW),
        ("packet_builder", BUILDER), ("model0_audit_launcher", RUNNER),
        ("source_contract_test", SOURCE_TEST), ("source_scenario_test", SCENARIO_TEST),
        ("audit_harness_test", HARNESS_TEST), ("gitignore", GITIGNORE),
        ("alphafactory", ALPHA), ("quant_analyzer", QUANT_ANALYZER),
    )
    if any(path.resolve() == RESERVED_REVIEW.resolve() for _, path in evidence_paths):
        raise ValueError("reserved review entered immutable evidence")
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": AUTHORITY, "hypothesis_id": HYPOTHESIS,
        "packet_build_attempt_id": PACKET_ATTEMPT,
        "packet_attempt_started_sha256": sha_file(marker),
        "authority_row_sha256": sha_bytes(raw_row),
        "authority_issued_at_utc": row["updated_at_utc"],
        "task_packet_sha256": sha_file(TASK), "git_commit": commit,
        "git_status_sha256": status_sha, "binding": binding,
        "data_acceptance_contract": EXPECTED_DATA_ACCEPTANCE,
        "reserved_mutable_control_paths": reserved,
        "evidence": [evidence(label, path) for label, path in evidence_paths],
        "generated_at_utc": now_text(), "performance_metrics_authorized": False,
        "economics_authorized": False, "promotion_eligible": False,
    }
    rewrite_claimed(RECEIPT, (json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
    if git_lines("status", "--short", "--untracked-files=all") != status:
        raise ValueError("Git path set changed while packet was sealed")
    return {
        "task_packet_path": repo_path(TASK), "task_packet_sha256": sha_file(TASK),
        "contract_receipt_path": repo_path(RECEIPT),
        "contract_receipt_sha256": sha_file(RECEIPT),
        "registry_snapshot_path": repo_path(SNAPSHOT),
        "registry_snapshot_sha256": sha_file(SNAPSHOT),
        "packet_authority_row_sha256": sha_bytes(raw_row),
        "git_commit": commit, "git_status_sha256": status_sha,
    }


def main() -> int:
    marker = claim_packet()
    terminal = PACKET_ROOT / "attempt_terminal.json"
    marker_sha = sha_file(marker)
    try:
        result = build_packet(marker)
        write_exclusive(terminal, json_bytes({
            "schema_version": "stbs009_packet_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS, "attempt_id": PACKET_ATTEMPT,
            "status": "COMPLETE", "verdict": "PACKET_COMPLETE_NO_MT5_NO_ECONOMICS",
            "attempt_started_sha256": marker_sha,
            "contract_receipt_sha256": result["contract_receipt_sha256"],
            "completed_at_utc": now_text(), "same_id_retry_authorized": False,
        }))
        result.update({
            "packet_attempt_started_path": repo_path(marker),
            "packet_attempt_started_sha256": marker_sha,
            "packet_attempt_terminal_path": repo_path(terminal),
            "packet_attempt_terminal_sha256": sha_file(terminal),
        })
        print(json.dumps(result, indent=2))
        return 0
    except BaseException as exc:
        if not terminal.exists():
            write_exclusive(terminal, json_bytes({
                "schema_version": "stbs009_packet_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS, "attempt_id": PACKET_ATTEMPT,
                "status": "FAILED", "verdict": "PACKET_FAILED_ATTEMPT_CONSUMED",
                "attempt_started_sha256": marker_sha,
                "failure_type": type(exc).__name__, "failure": str(exc),
                "completed_at_utc": now_text(), "same_id_retry_authorized": False,
            }))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
