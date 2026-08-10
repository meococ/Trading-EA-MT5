#!/usr/bin/env python3
"""Build the sole claim-first HYP008 Model-0 execution packet."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTrade"
RESEARCH = PACKAGE / "research"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTrade.mq5"
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-008_MODEL0_EXECUTION_PREREG.md"
STATIC_RESULT = RESEARCH / "HYP-STBS-XAUUSD-M15-007_STATIC_ENGINEERING_RESULT.md"
NONREPAINT = RESEARCH / "HYP-STBS-XAUUSD-M15-007_NONREPAINT_AUDIT.json"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST = ROOT / (
    "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/preflight/"
    "HYP-LASR-XAUUSD-M5-001/cost_source_manifest.json"
)
HYP007_FAILURE = RESEARCH / "HYP-STBS-XAUUSD-M15-007_PRE_RUN_HARNESS_FAILURE.md"
HYP007_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-007_PRE_RUN_HARNESS_REVIEW.md"
PRE_PACKET_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-008_PRE_PACKET_REVIEW.md"
RESERVED_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-008_POST_PACKET_REVIEW.md"
BUILDER = Path(__file__).resolve()
RUNNER = RESEARCH / "run_stbs008_model0_train.py"
TESTS = RESEARCH / "tests" / "test_stbs008_model0_harness.py"
GITIGNORE = ROOT / ".gitignore"
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
PREFLIGHT = RESEARCH / "preflight" / "HYP-STBS-XAUUSD-M15-008" / "V1"
TASK = PREFLIGHT / "task_packet.control.json"
RECEIPT = PREFLIGHT / "contract_receipt.control.json"
SNAPSHOT = PREFLIGHT / "candidate_registry.pre_mt5.jsonl"
PACKET_ROOT = RESEARCH / (
    "evidence/HYP-STBS-XAUUSD-M15-008/STBS008-PACKET-BUILD-001"
)
HYPOTHESIS = "HYP-STBS-XAUUSD-M15-008"
INNER_HYPOTHESIS = "HYP-STBS-XAUUSD-M15-007"
PACKET_ATTEMPT = "STBS008-PACKET-BUILD-001"
RUN_ATTEMPT = "STBS008-MODEL0-TRAIN-001"
ASOF = "2026-08-09T08:04:04Z"
PLACEHOLDER = b"RESERVED_NON_AUTHORITATIVE_PLACEHOLDER\n"
RESERVED_REPO_PATH = (
    "03. EA Developer/EA_SupertrendBurstScalperTrade/research/"
    "HYP-STBS-XAUUSD-M15-008_POST_PACKET_REVIEW.md"
)
RESERVED_STATUS_LINE = f'?? "{RESERVED_REPO_PATH}"'
EMPTY_SHA = hashlib.sha256(b"").hexdigest().upper()

PACKET_FALSE_FIELDS = (
    "mt5_train_run_authorized", "mt5_authorized", "model0_authorized",
    "model0_data_acquisition_authorized", "model0_performance_authorized",
    "model4_authorized", "model4_data_acquisition_authorized",
    "model4_performance_authorized", "source_run_authorized",
    "compile_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "standalone_compile_authorized",
    "trade_api_authorized", "performance_metrics_authorized",
    "outcome_prices_authorized", "post_event_ohlc_authorized",
    "artifact_collection_authorized", "comparator_execution_authorized",
    "visual_mode_authorized", "network_authorized", "paid_requests_authorized",
    "economics_authorized", "optimization_authorized", "validation_authorized",
    "holdout_authorized", "research_validation_access_authorized",
    "research_holdout_access_authorized", "validation_access_authorized",
    "holdout_access_authorized", "promotion_eligible",
    "paper_trading_authorized", "live_trading_authorized",
    "market_edge_claim_authorized", "same_id_retry_authorized",
    "registry_mutation_allowed", "research_falsification_authorized",
    "economic_validity_authorized",
)
HYP007_TERMINAL_FALSE_FIELDS = ("packet_build_authorized",) + PACKET_FALSE_FIELDS


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


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
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
        "schema_version": "stbs008_packet_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS,
        "attempt_id": PACKET_ATTEMPT,
        "status": "STARTED",
        "started_at_utc": now_text(),
        "same_id_retry_authorized": False,
    }))
    return marker


def validate_packet_authority(registry_raw: bytes) -> tuple[bytes, dict[str, Any]]:
    raw, row = latest_row_from_bytes(registry_raw, HYPOTHESIS)
    hyp007_raw, hyp007 = latest_row_from_bytes(registry_raw, INNER_HYPOTHESIS)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    hyp007_validation = hyp007.get("validation", {})
    hyp007_metrics = hyp007.get("metrics", {})
    issued = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
    checks = {
        "state": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_STBS008_PACKET_BUILD_AUTHORIZED",
        "model": row.get("model") == 0,
        "inner": validation.get("inner_implementation_hypothesis_id") == INNER_HYPOTHESIS,
        "packet": validation.get("packet_build_authorized") is True,
        "packet_id": validation.get("packet_build_attempt_id") == PACKET_ATTEMPT,
        "packet_limit": validation.get("packet_build_attempt_limit") == 1,
        "packet_unused": metrics.get("packet_build_attempts_consumed") == 0,
        "run_id": validation.get("mt5_train_attempt_id") == RUN_ATTEMPT,
        "run_limit": validation.get("mt5_train_attempt_limit") == 1,
        "run_unused": metrics.get("mt5_train_attempts_consumed") == 0,
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
        "builder": validation.get("reviewed_packet_builder_sha256") == sha_file(BUILDER),
        "runner": validation.get("reviewed_model0_launcher_sha256") == sha_file(RUNNER),
        "source": row.get("source_hash") == sha_file(SOURCE),
        "prereg": row.get("prereg_sha256") == sha_file(PREREG),
        "nonfuture": issued <= datetime.now(timezone.utc),
        "no_run_permissions": all(validation.get(name) is False
                                  for name in PACKET_FALSE_FIELDS),
        "hyp007_terminal_state": hyp007.get("state") == "parked",
        "hyp007_terminal_verdict": hyp007.get("verdict")
        == "PARK_PRE_RUN_HARNESS_AUTHORITY_INVALID_NO_PACKET_NO_MT5_NO_ECONOMICS",
        "hyp007_terminal_raw": validation.get("hyp007_terminal_row_sha256")
        == sha_bytes(hyp007_raw),
        "hyp007_zero_attempts": all(hyp007_metrics.get(name) == 0 for name in (
            "packet_build_attempts_consumed", "mt5_attempts_consumed",
            "run_compile_attempts_consumed", "model0_runs", "mt5_launches",
            "orders_executed", "trades_simulated", "returns_computed",
            "performance_trials_executed")),
        "hyp007_zero_opened": hyp007_metrics.get("economics_executed") is False
        and hyp007_metrics.get("research_validation_opened") is False
        and hyp007_metrics.get("research_holdout_opened") is False,
        "hyp007_no_authority": all(hyp007_validation.get(name) is False
                                   for name in HYP007_TERMINAL_FALSE_FIELDS),
        "hyp007_failure_binding": hyp007_validation.get("failure_document_sha256")
        == sha_file(HYP007_FAILURE),
        "hyp007_review_binding": hyp007_validation.get("independent_failure_review_sha256")
        == sha_file(HYP007_REVIEW),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP008 packet authority failed: {failed}")
    bound = {
        STATIC_RESULT: "static_engineering_result_sha256",
        NONREPAINT: "nonrepaint_audit_sha256",
        EA_CONTRACT: "ea_contract_sha256",
        COST: "cost_source_manifest_sha256",
        HYP007_FAILURE: "hyp007_failure_sha256",
        HYP007_REVIEW: "hyp007_independent_review_sha256",
        PRE_PACKET_REVIEW: "independent_pre_packet_review_sha256",
        TESTS: "reviewed_harness_tests_sha256",
        GITIGNORE: "gitignore_sha256",
        ALPHA: "alphafactory_sha256",
    }
    for path, field in bound.items():
        expected = validation.get(field)
        if not isinstance(expected, str) or sha_file(path) != expected:
            raise ValueError(f"bound artifact changed: {field}")
    if RESERVED_REVIEW.read_bytes() != PLACEHOLDER:
        raise ValueError("reserved post-packet review is not the frozen placeholder")
    return raw, row


def build_packet(marker: Path) -> dict[str, str]:
    registry_raw = REGISTRY.read_bytes()
    raw_row, row = validate_packet_authority(registry_raw)
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
        "hypothesis_id": HYPOTHESIS, "inner_implementation_hypothesis_id": INNER_HYPOTHESIS,
        "run_role": "control", "ea_name": "EA_SupertrendBurstScalperTrade",
        "symbol": "XAUUSD", "period": "M15", "from": "2005.01.01",
        "to": "2023.01.01", "model": 0, "execution_mode": 0,
        "fixed_delay_ms": 0, "overrides": "", "telemetry_tier": "off",
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
        **binding, "source_path": repo_path(SOURCE), "source_sha256": sha_file(SOURCE),
        "registry_path": repo_path(SNAPSHOT), "registry_sha256": sha_file(SNAPSHOT),
        "registry_row_sha256": sha_bytes(raw_row), "prereg_path": repo_path(PREREG),
        "prereg_sha256": sha_file(PREREG), "validation_stage": "train_baseline",
        "holding_contract": "h1_flip_m15_atr_trade_fsm",
        "include_closure": [], "required_manifest_hashes": [
            "source_sha256", "config_sha256", "report_sha256", "ex5_sha256",
            "includes_sha256"],
        "cost_source_manifest_path": repo_path(COST),
        "cost_source_manifest_sha256": sha_file(COST),
        "acceptance_contract": row["acceptance_contract"],
        "performance_metrics_authorized": True, "economics_authorized": True,
        "promotion_eligible": False, "git_commit": commit,
        "git_status": status, "git_status_sha256": status_sha,
        "reserved_mutable_control_paths": reserved,
    }
    TASK.write_bytes((json.dumps(task, indent=2) + "\n").encode("utf-8"))
    evidence_paths = (
        ("packet_attempt_started", marker), ("task_packet", TASK),
        ("candidate_registry", SNAPSHOT), ("source", SOURCE), ("prereg", PREREG),
        ("cost_source_manifest", COST), ("static_engineering_result", STATIC_RESULT),
        ("nonrepaint_audit", NONREPAINT), ("ea_capability_contract", EA_CONTRACT),
        ("hyp007_pre_run_harness_failure", HYP007_FAILURE),
        ("hyp007_independent_harness_review", HYP007_REVIEW),
        ("independent_pre_packet_review", PRE_PACKET_REVIEW),
        ("packet_builder", BUILDER), ("model0_launcher", RUNNER),
        ("harness_tests", TESTS), ("gitignore", GITIGNORE),
        ("alphafactory", ALPHA),
    )
    if any(path.resolve() == RESERVED_REVIEW.resolve() for _, path in evidence_paths):
        raise ValueError("reserved review entered immutable evidence")
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "hypothesis_id": HYPOTHESIS, "inner_implementation_hypothesis_id": INNER_HYPOTHESIS,
        "packet_build_attempt_id": PACKET_ATTEMPT,
        "packet_attempt_started_sha256": sha_file(marker),
        "authority_row_sha256": sha_bytes(raw_row),
        "authority_issued_at_utc": row["updated_at_utc"],
        "task_packet_sha256": sha_file(TASK), "git_commit": commit,
        "git_status_sha256": status_sha, "binding": binding,
        "reserved_mutable_control_paths": reserved,
        "evidence": [evidence(label, path) for label, path in evidence_paths],
        "generated_at_utc": now_text(), "performance_metrics_authorized": True,
        "economics_authorized": True, "promotion_eligible": False,
    }
    RECEIPT.write_bytes((json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
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
            "schema_version": "stbs008_packet_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS, "attempt_id": PACKET_ATTEMPT,
            "status": "COMPLETE", "verdict": "PACKET_COMPLETE_NO_MT5",
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
                "schema_version": "stbs008_packet_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS, "attempt_id": PACKET_ATTEMPT,
                "status": "FAILED", "verdict": "PACKET_FAILED_ATTEMPT_CONSUMED",
                "attempt_started_sha256": marker_sha,
                "failure_type": type(exc).__name__, "failure": str(exc),
                "completed_at_utc": now_text(), "same_id_retry_authorized": False,
            }))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
