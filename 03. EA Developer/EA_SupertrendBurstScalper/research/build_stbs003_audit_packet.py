#!/usr/bin/env python3
"""Build the sole chronology-correct HYP003 AlphaFactory audit packet."""

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
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-003"
INNER_IMPLEMENTATION_ID = "HYP-STBS-XAUUSD-M15-001"
PARENT_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-012"
FAILED_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-002"
PACKET_ATTEMPT_ID = "STBS003-PACKET-BUILD-001"
MT5_ATTEMPT_ID = "STBS003-MT5-AUDIT-001"
EA_NAME = "EA_SupertrendBurstScalper"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
SOURCE_SHA256 = "B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D"
FROZEN_BASE_RUNNER_SHA256 = "C4F2976F919EF9345CFC15891A9A8066F1FB5D474635C88BB29D047456645C14"
PARENT_TERMINAL_ROW_SHA256 = "DCF06201068DDDC52D6B225FD871F1D7A0691F9EB4B864D969A7BFD1422DF8C2"
HYP002_TERMINAL_ROW_SHA256 = "A626D682AC44ADDA7D876DB4185BD6793A36A6A833425F66F775DC2CBAC32674"
HYP002_FAILURE_SHA256 = "0B49C03F83B85FFFDB29FB7668A97CA7B295CF5F0ACDB42E85FF387584692599"
HYP002_POST_FAILURE_REVIEW_SHA256 = "36F002EF2C27B5E9B890ACE6010ABAF6DCB901BC43234CEC3828E2DB3740824C"
HYP002_ATTEMPT_STARTED_SHA256 = "CF3A13807364159E2A1B136ED86E4043A25C6540CAD342402D042EB475D3B7DB"
HYP002_ATTEMPT_TERMINAL_SHA256 = "8A5860E3F97FE6D35B7BAFDE577010C9C32DDC7EB9BD5ECBB7A7C636E9426C67"
HYP002_ALPHA_STDOUT_SHA256 = "06BB013D1A8543DCBB096E78372239700247B5F551B37A007F75BEDF8BD568AA"
HYP002_ALPHA_STDERR_SHA256 = "299B2530FCC0BC5DD8D23194C5120FE8F5B8191A22D40F801E6D6375E3C60E92"
FROM = "2005.01.01"
TO = "2023.01.01"
OVERRIDES = "InpAuditOnly=true"
ASOF = "2026-08-09T05:05:00Z"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()
PACKET_EVIDENCE_DIR = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-003/STBS003-PACKET-BUILD-001"
)
HYP002_FAILURE_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/"
    "HYP-STBS-XAUUSD-M15-002_PRECOMPILE_STATUS_FAILURE.md"
)
HYP002_POST_FAILURE_REVIEW_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/"
    "HYP-STBS-XAUUSD-M15-002_POST_FAILURE_REVIEW.md"
)
HYP002_ATTEMPT_ROOT = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-002/STBS002-MT5-AUDIT-001"
)
RESERVED_REVIEW_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/"
    "HYP-STBS-XAUUSD-M15-003_POST_PACKET_REVIEW.md"
)
RESERVED_REVIEW_REPO_PATH = (
    "03. EA Developer/EA_SupertrendBurstScalper/research/"
    "HYP-STBS-XAUUSD-M15-003_POST_PACKET_REVIEW.md"
)
RESERVED_REVIEW_STATUS_LINE = f'?? "{RESERVED_REVIEW_REPO_PATH}"'
RESERVED_PLACEHOLDER_MARKER = "RESERVED_NON_AUTHORITATIVE_PLACEHOLDER"
RESERVED_PLACEHOLDER_BYTES = (RESERVED_PLACEHOLDER_MARKER + "\n").encode("utf-8")
HYP002_TERMINAL_FALSE_FIELDS = (
    "packet_build_authorized", "mt5_audit_run_authorized", "mt5_authorized",
    "model0_authorized", "model0_data_acquisition_authorized",
    "model0_performance_authorized", "model4_authorized",
    "model4_data_acquisition_authorized", "model4_performance_authorized",
    "source_run_authorized", "compile_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "standalone_compile_authorized",
    "trade_api_authorized", "performance_metrics_authorized",
    "outcome_prices_authorized", "post_event_ohlc_authorized",
    "artifact_collection_authorized", "comparator_execution_authorized",
    "visual_mode_authorized", "network_authorized", "paid_requests_authorized",
    "economics_authorized", "optimization_authorized", "validation_authorized",
    "holdout_authorized", "research_validation_access_authorized",
    "research_holdout_access_authorized", "promotion_eligible",
    "paper_trading_authorized", "live_trading_authorized",
    "market_edge_claim_authorized", "same_id_retry_authorized",
    "registry_mutation_allowed",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def latest_row(path: Path, hypothesis_id: str) -> tuple[bytes, dict[str, Any]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis_id:
                matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no {hypothesis_id} row")
    return matches[-1]


def claim_packet_attempt() -> Path:
    PACKET_EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    marker = PACKET_EVIDENCE_DIR / "attempt_started.json"
    write_exclusive(
        marker,
        json_bytes(
            {
                "schema_version": "stbs003_packet_attempt_started.v1",
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


def hyp002_terminal_contract(row: dict[str, Any]) -> bool:
    metrics = row.get("metrics", {})
    validation = row.get("validation", {})
    return (
        row.get("state") == "killed"
        and row.get("verdict")
        == "KILL_PRE_ALPHA_GIT_STATUS_PATHSET_DRIFT_NO_COMPILE_NO_MT5"
        and metrics.get("packet_build_attempts_consumed") == 1
        and metrics.get("mt5_audit_attempts_consumed") == 1
        and metrics.get("run_compile_attempts_consumed") == 0
        and metrics.get("model0_runs") == 0
        and metrics.get("mt5_launches") == 0
        and all(validation.get(name) is False for name in HYP002_TERMINAL_FALSE_FIELDS)
        and validation.get("failure_document_sha256") == HYP002_FAILURE_SHA256
        and validation.get("independent_post_failure_review_sha256")
        == HYP002_POST_FAILURE_REVIEW_SHA256
        and validation.get("mt5_attempt_started_sha256")
        == HYP002_ATTEMPT_STARTED_SHA256
        and validation.get("mt5_attempt_terminal_sha256")
        == HYP002_ATTEMPT_TERMINAL_SHA256
        and validation.get("alpha_stdout_sha256") == HYP002_ALPHA_STDOUT_SHA256
        and validation.get("alpha_stderr_sha256") == HYP002_ALPHA_STDERR_SHA256
    )


def hyp002_artifacts_match(
    failure: Path = HYP002_FAILURE_PATH,
    review: Path = HYP002_POST_FAILURE_REVIEW_PATH,
    attempt_root: Path = HYP002_ATTEMPT_ROOT,
) -> bool:
    expected = (
        (failure, HYP002_FAILURE_SHA256),
        (review, HYP002_POST_FAILURE_REVIEW_SHA256),
        (attempt_root / "attempt_started.json", HYP002_ATTEMPT_STARTED_SHA256),
        (attempt_root / "attempt_terminal.json", HYP002_ATTEMPT_TERMINAL_SHA256),
        (attempt_root / "alpha_stdout.log", HYP002_ALPHA_STDOUT_SHA256),
        (attempt_root / "alpha_stderr.log", HYP002_ALPHA_STDERR_SHA256),
    )
    return all(path.is_file() and sha256_file(path) == digest for path, digest in expected)


def validate_reserved_placeholder(
    path: Path,
    status: list[str],
    evidence_paths: tuple[tuple[str, Path], ...] = (),
) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("reserved post-packet review placeholder is absent")
    if path.read_bytes() != RESERVED_PLACEHOLDER_BYTES:
        raise ValueError("reserved post-packet review placeholder is invalid")
    if status.count(RESERVED_REVIEW_STATUS_LINE) != 1:
        raise ValueError("reserved post-packet review path is absent or duplicated")
    if any(candidate.resolve() == path.resolve() for _, candidate in evidence_paths):
        raise ValueError("reserved review placeholder entered immutable evidence")
    return {
        "path": RESERVED_REVIEW_REPO_PATH,
        "sealed_status_line": RESERVED_REVIEW_STATUS_LINE,
        "placeholder_status": RESERVED_PLACEHOLDER_MARKER,
        "immutable_evidence": False,
        "final_review": False,
    }


def validate_authority(registry: Path) -> tuple[bytes, dict[str, Any]]:
    raw, row = latest_row(registry, HYPOTHESIS_ID)
    parent_raw, parent = latest_row(registry, PARENT_HYPOTHESIS_ID)
    failed_raw, failed_hypothesis = latest_row(registry, FAILED_HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    issued = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    checks = {
        "state": row.get("state") == "probe",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_STBS003_PACKET_BUILD_AUTHORIZED",
        "source": row.get("source_hash") == SOURCE_SHA256,
        "inner_identity": validation.get("inner_implementation_hypothesis_id")
        == INNER_IMPLEMENTATION_ID,
        "parent": parent.get("state") == "parked"
        and sha256_bytes(parent_raw) == PARENT_TERMINAL_ROW_SHA256,
        "hyp002_terminal": hyp002_terminal_contract(failed_hypothesis),
        "hyp002_terminal_raw": sha256_bytes(failed_raw)
        == HYP002_TERMINAL_ROW_SHA256,
        "hyp002_terminal_row": validation.get("hyp002_terminal_row_sha256")
        == sha256_bytes(failed_raw),
        "authority": validation.get("authority") == AUTHORITY,
        "nonfuture_authority": issued <= now,
        "nonfuture_asof": datetime.fromisoformat(ASOF.replace("Z", "+00:00"))
        <= issued,
        "packet": validation.get("packet_build_authorized") is True,
        "packet_id": validation.get("packet_build_attempt_id") == PACKET_ATTEMPT_ID,
        "packet_limit": validation.get("packet_build_attempt_limit") == 1,
        "packet_unconsumed": metrics.get("packet_build_attempts_consumed") == 0,
        "mt5_id": validation.get("mt5_audit_attempt_id") == MT5_ATTEMPT_ID,
        "no_mt5": validation.get("mt5_audit_run_authorized") is False,
        "builder": validation.get("reviewed_packet_builder_sha256")
        == sha256_file(Path(__file__).resolve()),
        "base_runner_frozen": validation.get("reviewed_inner_mt5_runner_sha256")
        == FROZEN_BASE_RUNNER_SHA256,
        "no_run_authority": all(
            validation.get(name) is False
            for name in (
                "mt5_authorized",
                "model0_authorized",
                "model0_data_acquisition_authorized",
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
                "economics_authorized",
                "optimization_authorized",
                "validation_authorized",
                "holdout_authorized",
                "research_validation_access_authorized",
                "research_holdout_access_authorized",
                "promotion_eligible",
                "paper_trading_authorized",
                "live_trading_authorized",
                "market_edge_claim_authorized",
                "same_id_retry_authorized",
                "registry_mutation_allowed",
            )
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP003 packet authority failed: {failed}")
    return raw, row


def build_packet(marker: Path) -> dict[str, Any]:
    package = ROOT / "03. EA Developer/EA_SupertrendBurstScalper"
    research = package / "research"
    preflight = research / "preflight/HYP-STBS-XAUUSD-M15-003/V1"
    registry = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    registry_snapshot = preflight / "candidate_registry.pre_mt5.jsonl"
    packet_path = preflight / "task_packet.control.json"
    receipt_path = preflight / "contract_receipt.control.json"
    source = package / "EA_SupertrendBurstScalper.mq5"
    prereg = research / "HYP-STBS-XAUUSD-M15-003_ENGINEERING_PREREG.md"
    review = research / "HYP-STBS-XAUUSD-M15-003_PRE_MT5_REVIEW.md"
    failure = HYP002_FAILURE_PATH
    post_failure_review = HYP002_POST_FAILURE_REVIEW_PATH
    cost = research / "HYP-STBS-XAUUSD-M15-001_COLLECTION_ONLY_COST_MANIFEST.json"
    contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    outer_runner = research / "run_stbs003_mt5_audit.py"
    inner_runner = research / "run_stbs001_mt5_audit.py"
    tests = research / "tests/test_stbs003_governance_harness.py"
    engineering_tests = research / "tests/test_stbs_001_engineering_contract.py"
    nonrepaint_manifest = package / "HYP-STBS-XAUUSD-M15-001_NONREPAINT_MANIFEST.json"
    nonrepaint_audit = research / "HYP-STBS-XAUUSD-M15-001_NONREPAINT_AUDIT.json"
    static_root = research / "evidence/HYP-STBS-XAUUSD-M15-001/STBS001-STATIC-COMPILE-001"
    static_receipt = static_root / "static_compile_archive_receipt.json"
    static_terminal = static_root / "attempt_terminal.json"
    hyp002_attempt_started = HYP002_ATTEMPT_ROOT / "attempt_started.json"
    hyp002_attempt_terminal = HYP002_ATTEMPT_ROOT / "attempt_terminal.json"
    hyp002_alpha_stdout = HYP002_ATTEMPT_ROOT / "alpha_stdout.log"
    hyp002_alpha_stderr = HYP002_ATTEMPT_ROOT / "alpha_stderr.log"
    parent_receipt = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001/st009_full_bar_parity_receipt.json"
    parent_terminal = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001/attempt_terminal.json"
    oracle = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
    gitignore = ROOT / ".gitignore"
    alpha = ROOT / "02. AlphaFactory/alpha.ps1"
    audit_tool = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
    required = (
        registry, source, prereg, review, RESERVED_REVIEW_PATH, failure,
        post_failure_review, cost, contract, outer_runner,
        inner_runner, tests, engineering_tests, nonrepaint_manifest,
        nonrepaint_audit, static_receipt, static_terminal,
        hyp002_attempt_started, hyp002_attempt_terminal, hyp002_alpha_stdout,
        hyp002_alpha_stderr, parent_receipt, parent_terminal, oracle, gitignore,
        alpha, audit_tool,
    )
    if preflight.exists() or any(not path.is_file() for path in required):
        raise ValueError("HYP003 preflight exists or a required frozen input is absent")
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("inner implementation source changed")
    if sha256_file(inner_runner) != FROZEN_BASE_RUNNER_SHA256:
        raise ValueError("frozen HYP001 base runner changed")
    if not hyp002_artifacts_match():
        raise ValueError("canonical HYP002 failure artifact changed")
    raw_row, authority_row = validate_authority(registry)
    hyp002_terminal_raw, _ = latest_row(registry, FAILED_HYPOTHESIS_ID)
    marker_payload = json.loads(marker.read_text(encoding="utf-8"))
    authority_issued = datetime.fromisoformat(
        authority_row["updated_at_utc"].replace("Z", "+00:00")
    )
    packet_started = datetime.fromisoformat(
        marker_payload["started_at_utc"].replace("Z", "+00:00")
    )
    if authority_issued > packet_started:
        raise ValueError("HYP003 probe authority postdates packet claim")
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
            "source_sha256", "config_sha256", "report_sha256", "ex5_sha256",
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
    reserved_contract = [validate_reserved_placeholder(RESERVED_REVIEW_PATH, status)]
    packet.update(
        {
            "git_commit": commit,
            "git_status": status,
            "git_status_sha256": status_sha,
            "reserved_mutable_control_paths": reserved_contract,
        }
    )
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    binding = {
        "hypothesis_id": HYPOTHESIS_ID,
        "inner_implementation_hypothesis_id": INNER_IMPLEMENTATION_ID,
        "hyp002_terminal_row_sha256": sha256_bytes(hyp002_terminal_raw),
        "run_role": "control", "ea_name": EA_NAME, "symbol": "XAUUSD",
        "period": "M15", "from": FROM, "to": TO, "model": 0,
        "execution_mode": 0, "fixed_delay_ms": 0, "overrides": OVERRIDES,
        "telemetry_tier": "off", "telemetry_profile": "none",
        "deposit": 10000, "leverage": 100, "spread": "current",
        "required_sidecars": [], "indicator_dependencies": [],
        "broker_fingerprint": None, "server_fingerprint": None,
        "account_fingerprint": None, "data_fingerprint": None,
        "symbol_geometry": packet["symbol_geometry"],
        "include_closure_sha256": EMPTY_SHA256,
        "data_quality_contract": data_quality,
    }
    evidence_paths = (
        ("packet_attempt_started", marker), ("task_packet", packet_path),
        ("candidate_registry", registry_snapshot), ("gitignore", gitignore),
        ("source", source), ("prereg", prereg), ("independent_review", review),
        ("hyp002_precompile_status_failure", failure),
        ("hyp002_post_failure_review", post_failure_review),
        ("cost_source_manifest", cost),
        ("ea_capability_contract", contract), ("outer_mt5_runner", outer_runner),
        ("inner_mt5_runner", inner_runner), ("governance_tests", tests),
        ("engineering_tests", engineering_tests),
        ("nonrepaint_manifest", nonrepaint_manifest),
        ("nonrepaint_audit", nonrepaint_audit),
        ("static_compile_receipt", static_receipt),
        ("static_compile_terminal", static_terminal),
        ("hyp002_mt5_attempt_started", hyp002_attempt_started),
        ("hyp002_mt5_attempt_terminal", hyp002_attempt_terminal),
        ("hyp002_alpha_stdout", hyp002_alpha_stdout),
        ("hyp002_alpha_stderr", hyp002_alpha_stderr),
        ("parent_parity_receipt", parent_receipt),
        ("parent_parity_terminal", parent_terminal), ("parent_oracle", oracle),
        ("alpha_ps1", alpha), ("nonrepaint_tool", audit_tool),
    )
    # The reservation is a mutable control path, never immutable review evidence.
    validate_reserved_placeholder(RESERVED_REVIEW_PATH, status, evidence_paths)
    evidence = [file_evidence(label, path) for label, path in evidence_paths]
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "packet_build_attempt_id": PACKET_ATTEMPT_ID,
        "packet_attempt_started_sha256": sha256_file(marker),
        "authority_row_sha256": sha256_bytes(raw_row),
        "authority_issued_at_utc": authority_row["updated_at_utc"],
        "task_packet_sha256": sha256_file(packet_path),
        "git_commit": commit, "git_status_sha256": status_sha,
        "binding": binding,
        "reserved_mutable_control_paths": reserved_contract,
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "performance_metrics_authorized": False,
        "economics_authorized": False, "promotion_eligible": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if git_lines("status", "--short", "--untracked-files=all") != status:
        raise ValueError("git status changed while HYP003 packet was sealed")
    return {
        "task_packet": repo_path(packet_path),
        "task_packet_sha256": sha256_file(packet_path),
        "contract_receipt": repo_path(receipt_path),
        "contract_receipt_sha256": sha256_file(receipt_path),
        "registry_snapshot_sha256": sha256_file(registry_snapshot),
        "git_commit": commit, "git_status_sha256": status_sha,
        "authority_row_sha256": sha256_bytes(raw_row),
    }


def main() -> int:
    marker = claim_packet_attempt()
    marker_sha = sha256_file(marker)
    terminal = PACKET_EVIDENCE_DIR / "attempt_terminal.json"
    try:
        result = build_packet(marker)
        write_exclusive(
            terminal,
            json_bytes({
                "schema_version": "stbs003_packet_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID, "attempt_id": PACKET_ATTEMPT_ID,
                "status": "COMPLETE", "verdict": "PACKET_BUILD_COMPLETE_NO_MT5_OR_ECONOMICS",
                "attempt_started_sha256": marker_sha,
                "contract_receipt_sha256": result["contract_receipt_sha256"],
                "same_id_retry_authorized": False,
                "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }),
        )
        result.update({
            "packet_attempt_started": repo_path(marker),
            "packet_attempt_started_sha256": marker_sha,
            "packet_attempt_terminal": repo_path(terminal),
            "packet_attempt_terminal_sha256": sha256_file(terminal),
        })
        print(json.dumps(result, indent=2))
        return 0
    except BaseException as exc:
        if not terminal.exists():
            write_exclusive(
                terminal,
                json_bytes({
                    "schema_version": "stbs003_packet_attempt_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID, "attempt_id": PACKET_ATTEMPT_ID,
                    "status": "FAILED", "verdict": "PACKET_BUILD_FAILED_ATTEMPT_CONSUMED",
                    "attempt_started_sha256": marker_sha,
                    "failure_type": type(exc).__name__, "failure": str(exc),
                    "same_id_retry_authorized": False,
                    "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }),
            )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
