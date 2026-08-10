#!/usr/bin/env python3
"""Claim and run the sole HYP008 Model-0 TRAIN baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTrade"
RESEARCH = PACKAGE / "research"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTrade.mq5"
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-008_MODEL0_EXECUTION_PREREG.md"
RECEIPT = RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-008/V1/contract_receipt.control.json"
TASK = RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-008/V1/task_packet.control.json"
SNAPSHOT = RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-008/V1/candidate_registry.pre_mt5.jsonl"
PACKET_ROOT = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-008/STBS008-PACKET-BUILD-001"
ATTEMPT_ROOT = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-008/STBS008-MODEL0-TRAIN-001"
BUILDER = RESEARCH / "build_stbs008_model0_packet.py"
RUNNER = Path(__file__).resolve()
RESERVED_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-008_POST_PACKET_REVIEW.md"
HYPOTHESIS = "HYP-STBS-XAUUSD-M15-008"
INNER_HYPOTHESIS = "HYP-STBS-XAUUSD-M15-007"
PACKET_ATTEMPT = "STBS008-PACKET-BUILD-001"
RUN_ATTEMPT = "STBS008-MODEL0-TRAIN-001"
RUN_VERDICT = "FROZEN_STBS008_MODEL0_TRAIN_AUTHORIZED"
EXPECTED_ACCEPTANCE = {
    "min_profit_factor": 1.3, "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0, "max_drawdown_pct": 8.0,
    "min_cost_pf_x1_5": 1.25, "min_cost_pf_x2": 1.0,
    "max_monte_carlo_p95_dd_pct": 8.0,
}
RESERVED_REPO_PATH = (
    "03. EA Developer/EA_SupertrendBurstScalperTrade/research/"
    "HYP-STBS-XAUUSD-M15-008_POST_PACKET_REVIEW.md"
)
RESERVED_STATUS_LINE = f'?? "{RESERVED_REPO_PATH}"'
RUN_TRUE_FIELDS = (
    "mt5_train_run_authorized", "mt5_authorized", "model0_authorized",
    "model0_performance_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "trade_api_authorized",
    "performance_metrics_authorized", "outcome_prices_authorized",
    "post_event_ohlc_authorized", "economics_authorized",
    "research_falsification_authorized",
)
RUN_FALSE_FIELDS = (
    "packet_build_authorized", "model0_data_acquisition_authorized",
    "model4_authorized", "model4_data_acquisition_authorized",
    "model4_performance_authorized", "source_run_authorized",
    "compile_authorized", "standalone_compile_authorized",
    "artifact_collection_authorized", "comparator_execution_authorized",
    "visual_mode_authorized", "network_authorized", "paid_requests_authorized",
    "optimization_authorized", "validation_authorized", "holdout_authorized",
    "research_validation_access_authorized", "research_holdout_access_authorized",
    "validation_access_authorized", "holdout_access_authorized",
    "economic_validity_authorized", "promotion_eligible",
    "paper_trading_authorized", "live_trading_authorized",
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


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def latest_row(path: Path, hypothesis: str) -> tuple[bytes, dict[str, Any]]:
    found: tuple[bytes, dict[str, Any]] | None = None
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis:
                found = raw, row
    if found is None:
        raise ValueError(f"registry has no {hypothesis}")
    return found


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def claim(receipt_sha: str) -> Path:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    marker = ATTEMPT_ROOT / "attempt_started.json"
    write_exclusive(marker, json_bytes({
        "schema_version": "stbs008_model0_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS, "attempt_id": RUN_ATTEMPT,
        "status": "STARTED", "started_at_utc": now_text(),
        "declared_receipt_path": str(RECEIPT),
        "declared_receipt_sha256": receipt_sha,
        "same_id_retry_authorized": False,
    }))
    return marker


def validate_after_claim(marker: Path, declared_receipt_sha: str) -> list[str]:
    raw, row = latest_row(REGISTRY, HYPOTHESIS)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "verdict": row.get("verdict") == RUN_VERDICT,
        "model": row.get("model") == 0,
        "inner": validation.get("inner_implementation_hypothesis_id") == INNER_HYPOTHESIS,
        "packet_consumed": metrics.get("packet_build_attempts_consumed") == 1,
        "run_unused": metrics.get("mt5_train_attempts_consumed") == 0,
        "run_limit": validation.get("mt5_train_attempt_limit") == 1,
        "run_id": validation.get("mt5_train_attempt_id") == RUN_ATTEMPT,
        "run_compile_unused": metrics.get("run_compile_attempts_consumed") == 0,
        "builder": validation.get("reviewed_packet_builder_sha256") == sha_file(BUILDER),
        "runner": validation.get("reviewed_model0_launcher_sha256") == sha_file(RUNNER),
        "true_permissions": all(validation.get(name) is True for name in RUN_TRUE_FIELDS),
        "false_permissions": all(validation.get(name) is False for name in RUN_FALSE_FIELDS),
        "receipt_cli": validation.get("contract_receipt_sha256") == declared_receipt_sha,
        "receipt_actual": sha_file(RECEIPT) == declared_receipt_sha,
        "source": row.get("source_hash") == sha_file(SOURCE),
        "prereg": row.get("prereg_sha256") == sha_file(PREREG),
        "empty_overrides": row.get("exact_overrides") == "",
        "economic_contract": row.get("evidence_contract_kind") == "economic"
        and row.get("acceptance_contract") == EXPECTED_ACCEPTANCE,
        "zero_model0_runs": metrics.get("model0_runs") == 0,
        "zero_mt5_launches": metrics.get("mt5_launches") == 0,
        "zero_orders": metrics.get("orders_executed") == 0,
        "zero_trades": metrics.get("trades_simulated") == 0,
        "zero_returns": metrics.get("returns_computed") == 0,
        "zero_trials": metrics.get("performance_trials_executed") == 0,
        "economics_unopened": metrics.get("economics_executed") is False,
        "validation_unopened": metrics.get("research_validation_opened") is False,
        "holdout_unopened": metrics.get("research_holdout_opened") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP008 screened run authority failed: {failed}")
    bound_paths = {
        RECEIPT: "contract_receipt_sha256", TASK: "task_packet_sha256",
        SNAPSHOT: "registry_snapshot_sha256",
        PACKET_ROOT / "attempt_started.json": "packet_build_attempt_started_sha256",
        PACKET_ROOT / "attempt_terminal.json": "packet_build_attempt_terminal_sha256",
    }
    for path, field in bound_paths.items():
        expected = validation.get(field)
        if not isinstance(expected, str) or sha_file(path) != expected:
            raise ValueError(f"screened bound artifact changed: {field}")
    review_raw = RESERVED_REVIEW.read_bytes()
    if sha_bytes(review_raw) != validation.get("independent_post_packet_review_sha256"):
        raise ValueError("post-packet review hash mismatch")
    try:
        review_text = review_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("post-packet review is not valid UTF-8") from exc
    review_prefix = "# HYP008 post-packet independent review\n\nVerdict: PASS_SCREENED_AUTHORITY\n"
    if not review_text.startswith(review_prefix) or "RESERVED_NON_AUTHORITATIVE_PLACEHOLDER" in review_text:
        raise ValueError("post-packet review semantics failed")
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    task = json.loads(TASK.read_text(encoding="utf-8"))
    expected_reserved = [{
        "path": RESERVED_REPO_PATH, "sealed_status_line": RESERVED_STATUS_LINE,
        "placeholder_status": "RESERVED_NON_AUTHORITATIVE_PLACEHOLDER",
        "immutable_evidence": False, "final_review": False,
    }]
    if receipt.get("reserved_mutable_control_paths") != expected_reserved or task.get("reserved_mutable_control_paths") != expected_reserved:
        raise ValueError("reserved mutable review contract changed")
    if any(Path(str(item.get("path", ""))).resolve() == RESERVED_REVIEW.resolve()
           for item in receipt.get("evidence", [])):
        raise ValueError("reserved review was incorrectly sealed as immutable evidence")
    if receipt.get("authority_row_sha256") != validation.get("packet_build_authority_row_sha256"):
        raise ValueError("packet authority raw-row binding mismatch")
    snapshot_raw, _ = latest_row(SNAPSHOT, HYPOTHESIS)
    if sha_bytes(snapshot_raw) != receipt.get("authority_row_sha256"):
        raise ValueError("packet registry snapshot row mismatch")
    packet_start = json.loads((PACKET_ROOT / "attempt_started.json").read_text(encoding="utf-8"))
    packet_terminal = json.loads((PACKET_ROOT / "attempt_terminal.json").read_text(encoding="utf-8"))
    run_start = json.loads(marker.read_text(encoding="utf-8"))
    if packet_terminal.get("status") != "COMPLETE" or packet_terminal.get("contract_receipt_sha256") != declared_receipt_sha:
        raise ValueError("packet terminal is not a complete receipt binding")
    chronology = (
        parse_time(receipt["authority_issued_at_utc"])
        <= parse_time(packet_start["started_at_utc"])
        <= parse_time(receipt["generated_at_utc"])
        <= parse_time(packet_terminal["completed_at_utc"])
        <= parse_time(row["updated_at_utc"])
        <= parse_time(run_start["started_at_utc"])
    )
    if not chronology:
        raise ValueError("probe/packet/screened/run chronology is invalid")
    status_result = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    live_status = status_result.stdout.decode("utf-8").splitlines()
    if live_status != task.get("git_status") or live_status.count(RESERVED_STATUS_LINE) != 1:
        raise ValueError("live Git path set differs from sealed packet")
    alpha_expected = validation.get("alphafactory_sha256")
    if not isinstance(alpha_expected, str) or sha_file(ALPHA) != alpha_expected:
        raise ValueError("AlphaFactory hash drift")
    return [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ALPHA),
        "backtest", "EA_SupertrendBurstScalperTrade", "-Symbol", "XAUUSD",
        "-Period", "M15", "-From", "2005.01.01", "-To", "2023.01.01",
        "-Model", "0", "-ExecutionMode", "0", "-FixedDelayMs", "0",
        "-TimeoutSec", "1800", "-HypothesisId", HYPOTHESIS,
        "-RunRole", "control", "-TelemetryTier", "off", "-Deposit", "10000",
        "-Leverage", "100", "-ContractReceipt", str(RECEIPT),
        "-ContractReceiptSha256", declared_receipt_sha,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args()
    declared = args.receipt_sha256.upper()
    if re.fullmatch(r"[A-F0-9]{64}", args.receipt_sha256) is None:
        raise SystemExit("receipt SHA must be uppercase SHA256")
    marker = claim(declared)
    terminal = ATTEMPT_ROOT / "attempt_terminal.json"
    stdout_path = ATTEMPT_ROOT / "alpha_stdout.log"
    stderr_path = ATTEMPT_ROOT / "alpha_stderr.log"
    exit_code = -1
    error = ""
    command: list[str] = []
    try:
        command = validate_after_claim(marker, declared)
        with stdout_path.open("xb") as out, stderr_path.open("xb") as err:
            completed = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err,
                                       timeout=2100)
        exit_code = completed.returncode
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
    write_exclusive(terminal, json_bytes({
        "schema_version": "stbs008_model0_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS, "attempt_id": RUN_ATTEMPT,
        "status": "COMPLETE" if exit_code == 0 else "FAILED",
        "exit_code": exit_code, "error": error, "command": command,
        "attempt_started_sha256": sha_file(marker),
        "stdout_sha256": sha_file(stdout_path) if stdout_path.exists() else "",
        "stderr_sha256": sha_file(stderr_path) if stderr_path.exists() else "",
        "completed_at_utc": now_text(), "same_id_retry_authorized": False,
    }))
    print(json.dumps(json.loads(terminal.read_text(encoding="utf-8")), indent=2))
    return 0 if exit_code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
