#!/usr/bin/env python3
"""Run the sole outer-HYP003, inner-HYP001 no-trade MT5 audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTER_ID = "HYP-STBS-XAUUSD-M15-003"
INNER_ID = "HYP-STBS-XAUUSD-M15-001"
OUTER_VERDICT = "FROZEN_STBS003_MT5_AUDIT_AUTHORIZED"
OUTER_ATTEMPT_ID = "STBS003-MT5-AUDIT-001"
OUTER_PACKET_ID = "STBS003-PACKET-BUILD-001"
FAILED_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-002"
BASE_PATH = Path(__file__).resolve().with_name("run_stbs001_mt5_audit.py")
FROZEN_BASE_RUNNER_SHA256 = "C4F2976F919EF9345CFC15891A9A8066F1FB5D474635C88BB29D047456645C14"
HYP002_TERMINAL_ROW_SHA256 = "A626D682AC44ADDA7D876DB4185BD6793A36A6A833425F66F775DC2CBAC32674"
HYP002_FAILURE_SHA256 = "0B49C03F83B85FFFDB29FB7668A97CA7B295CF5F0ACDB42E85FF387584692599"
HYP002_POST_FAILURE_REVIEW_SHA256 = "36F002EF2C27B5E9B890ACE6010ABAF6DCB901BC43234CEC3828E2DB3740824C"
HYP002_ATTEMPT_STARTED_SHA256 = "CF3A13807364159E2A1B136ED86E4043A25C6540CAD342402D042EB475D3B7DB"
HYP002_ATTEMPT_TERMINAL_SHA256 = "8A5860E3F97FE6D35B7BAFDE577010C9C32DDC7EB9BD5ECBB7A7C636E9426C67"
HYP002_ALPHA_STDOUT_SHA256 = "06BB013D1A8543DCBB096E78372239700247B5F551B37A007F75BEDF8BD568AA"
HYP002_ALPHA_STDERR_SHA256 = "299B2530FCC0BC5DD8D23194C5120FE8F5B8191A22D40F801E6D6375E3C60E92"
SPEC = importlib.util.spec_from_file_location("stbs001_frozen_runner_dependency", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen HYP001 runner dependency")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

BASE_RUNNER_SHA256 = BASE.sha256_file(BASE_PATH)
if BASE_RUNNER_SHA256 != FROZEN_BASE_RUNNER_SHA256:
    raise RuntimeError("frozen HYP001 runner dependency changed")
OUTER_PATH = Path(__file__).resolve()
OUTER_ROOT = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-003/STBS003-MT5-AUDIT-001"
)
PACKET_ROOT = ROOT / (
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

BASE.HYPOTHESIS_ID = OUTER_ID
BASE.ATTEMPT_ID = OUTER_ATTEMPT_ID
BASE.PACKET_ATTEMPT_ID = OUTER_PACKET_ID
BASE.OUTPUT_DIR = OUTER_ROOT
BASE.PACKET_ATTEMPT_ROOT = PACKET_ROOT
BASE.PACKET_STARTED_PATH = PACKET_ROOT / "attempt_started.json"
BASE.PACKET_TERMINAL_PATH = PACKET_ROOT / "attempt_terminal.json"
# Make the inherited self-hash gate and receipts identify this outer entrypoint.
BASE.__file__ = str(OUTER_PATH)

ORIGINAL_LATEST = BASE.latest_registry_row
ORIGINAL_AUTHORITY = BASE.validate_authority_metadata
ORIGINAL_BOUND = BASE.validate_bound_files_after_claim
ORIGINAL_SIGNAL = BASE.validate_signal_journal


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


def expected_reserved_contract() -> list[dict[str, Any]]:
    return [
        {
            "path": RESERVED_REVIEW_REPO_PATH,
            "sealed_status_line": RESERVED_REVIEW_STATUS_LINE,
            "placeholder_status": RESERVED_PLACEHOLDER_MARKER,
            "immutable_evidence": False,
            "final_review": False,
        }
    ]


def git_status_lines() -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8").splitlines()


def validate_final_review_contract(
    row: dict[str, Any],
    receipt: dict[str, Any],
    packet: dict[str, Any],
    review_path: Path = RESERVED_REVIEW_PATH,
    live_status: list[str] | None = None,
) -> None:
    validation = row.get("validation", {})
    expected = expected_reserved_contract()
    if receipt.get("reserved_mutable_control_paths") != expected:
        raise ValueError("receipt reserved mutable path contract mismatch")
    if packet.get("reserved_mutable_control_paths") != expected:
        raise ValueError("task packet reserved mutable path contract mismatch")
    packet_status = packet.get("git_status")
    if not isinstance(packet_status, list) or packet_status.count(
        RESERVED_REVIEW_STATUS_LINE
    ) != 1:
        raise ValueError("sealed packet reserved status line mismatch")
    if live_status is not None and live_status != packet_status:
        raise ValueError("live Git path set differs from sealed packet")
    if validation.get("reserved_post_packet_review_path") != RESERVED_REVIEW_REPO_PATH:
        raise ValueError("final review authority path mismatch")
    expected_sha = str(validation.get("reserved_post_packet_review_sha256", ""))
    if not review_path.is_file() or re.fullmatch(r"[A-F0-9]{64}", expected_sha) is None:
        raise ValueError("reserved post-packet review is absent or has invalid authority hash")
    review_raw = review_path.read_bytes()
    actual_sha = BASE.sha256_bytes(review_raw)
    if actual_sha != expected_sha:
        raise ValueError(
            "reserved post-packet review changed: "
            f"expected {expected_sha}, got {actual_sha}"
        )
    try:
        review_text = review_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("reserved post-packet review is not valid UTF-8") from exc
    if (
        "PASS_SCREENED_AUTHORITY" not in review_text
        or RESERVED_PLACEHOLDER_MARKER in review_text
    ):
        raise ValueError("final post-packet review semantics failed")
    for item in receipt.get("evidence", []):
        if Path(str(item.get("path", ""))).resolve() == review_path.resolve():
            raise ValueError("reserved review was incorrectly sealed as immutable evidence")


def chronology_is_valid(
    probe_issued: datetime,
    packet_started: datetime,
    receipt_generated: datetime,
    packet_completed: datetime,
    screened_issued: datetime,
    mt5_started: datetime,
) -> bool:
    return (
        probe_issued
        <= packet_started
        <= receipt_generated
        <= packet_completed
        <= screened_issued
        <= mt5_started
    )


def validate_outer_authority(
    registry: Path, contract_receipt: Path
) -> tuple[dict[str, Any], dict[str, str]]:
    raw, actual = ORIGINAL_LATEST(registry, OUTER_ID)
    failed_raw, failed_hypothesis = ORIGINAL_LATEST(registry, FAILED_HYPOTHESIS_ID)
    validation = actual.get("validation", {})
    issued = datetime.fromisoformat(actual["updated_at_utc"].replace("Z", "+00:00"))
    checks = {
        "outer_verdict": actual.get("verdict") == OUTER_VERDICT,
        "outer_runner": validation.get("reviewed_mt5_audit_launcher_sha256")
        == BASE.sha256_file(OUTER_PATH),
        "inner_runner": validation.get("reviewed_inner_mt5_runner_sha256")
        == BASE_RUNNER_SHA256,
        "inner_identity": validation.get("inner_implementation_hypothesis_id")
        == INNER_ID,
        "nonfuture_authority": issued <= datetime.now(timezone.utc),
        "hyp002_terminal": hyp002_terminal_contract(failed_hypothesis),
        "hyp002_terminal_raw": BASE.sha256_bytes(failed_raw)
        == HYP002_TERMINAL_ROW_SHA256,
        "hyp002_terminal_row": validation.get("hyp002_terminal_row_sha256")
        == BASE.sha256_bytes(failed_raw),
        "reserved_review_path": validation.get("reserved_post_packet_review_path")
        == RESERVED_REVIEW_REPO_PATH,
        "reserved_review_hash": re.fullmatch(
            r"[A-F0-9]{64}",
            str(validation.get("reserved_post_packet_review_sha256", "")),
        )
        is not None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP003 outer authority failed: {failed}")

    def compatibility_latest(path: Path, hypothesis_id: str):
        latest_raw, row = ORIGINAL_LATEST(path, hypothesis_id)
        if hypothesis_id == OUTER_ID:
            row = dict(row)
            row["verdict"] = "FROZEN_STBS001_MT5_AUDIT_AUTHORIZED"
        return latest_raw, row

    BASE.latest_registry_row = compatibility_latest
    try:
        _, authority = ORIGINAL_AUTHORITY(registry, contract_receipt)
    finally:
        BASE.latest_registry_row = ORIGINAL_LATEST
    return actual, authority


def validate_outer_bound(row: dict[str, Any], contract_receipt: Path) -> None:
    ORIGINAL_BOUND(row, contract_receipt)
    validation = row["validation"]
    BASE.require_bound_file(
        BASE_PATH,
        validation["reviewed_inner_mt5_runner_sha256"],
        "inner HYP001 runner dependency",
    )
    for label, path, digest in (
        ("HYP002 pre-Alpha status failure", HYP002_FAILURE_PATH, HYP002_FAILURE_SHA256),
        ("HYP002 post-failure review", HYP002_POST_FAILURE_REVIEW_PATH, HYP002_POST_FAILURE_REVIEW_SHA256),
        ("HYP002 MT5 attempt start", HYP002_ATTEMPT_ROOT / "attempt_started.json", HYP002_ATTEMPT_STARTED_SHA256),
        ("HYP002 MT5 attempt terminal", HYP002_ATTEMPT_ROOT / "attempt_terminal.json", HYP002_ATTEMPT_TERMINAL_SHA256),
        ("HYP002 Alpha stdout", HYP002_ATTEMPT_ROOT / "alpha_stdout.log", HYP002_ALPHA_STDOUT_SHA256),
        ("HYP002 Alpha stderr", HYP002_ATTEMPT_ROOT / "alpha_stderr.log", HYP002_ALPHA_STDERR_SHA256),
    ):
        BASE.require_bound_file(path, digest, label)
    receipt = json.loads(contract_receipt.read_text(encoding="utf-8"))
    if receipt.get("binding", {}).get("inner_implementation_hypothesis_id") != INNER_ID:
        raise ValueError("contract receipt inner implementation identity mismatch")
    if (
        receipt.get("binding", {}).get("hyp002_terminal_row_sha256")
        != validation.get("hyp002_terminal_row_sha256")
    ):
        raise ValueError("contract receipt HYP002 terminal row mismatch")
    expected_packet_path = (
        ROOT
        / "03. EA Developer/EA_SupertrendBurstScalper/research/preflight/"
        "HYP-STBS-XAUUSD-M15-003/V1/task_packet.control.json"
    ).resolve()
    task_entries = [
        item for item in receipt.get("evidence", [])
        if item.get("label") == "task_packet"
    ]
    if len(task_entries) != 1:
        raise ValueError("receipt must bind exactly one task packet")
    task_entry = task_entries[0]
    if Path(str(task_entry.get("path", ""))).resolve() != expected_packet_path:
        raise ValueError("receipt task packet path mismatch")
    BASE.require_bound_file(
        expected_packet_path,
        str(task_entry.get("sha256", "")),
        "HYP003 task packet",
    )
    packet = json.loads(expected_packet_path.read_text(encoding="utf-8"))
    validate_final_review_contract(
        row,
        receipt,
        packet,
        RESERVED_REVIEW_PATH,
        git_status_lines(),
    )
    packet_terminal = json.loads(
        BASE.PACKET_TERMINAL_PATH.read_text(encoding="utf-8")
    )
    packet_started_payload = json.loads(
        BASE.PACKET_STARTED_PATH.read_text(encoding="utf-8")
    )
    mt5_started = json.loads(
        (BASE.OUTPUT_DIR / "attempt_started.json").read_text(encoding="utf-8")
    )
    issued = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
    probe_issued = datetime.fromisoformat(
        receipt["authority_issued_at_utc"].replace("Z", "+00:00")
    )
    packet_started = datetime.fromisoformat(
        packet_started_payload["started_at_utc"].replace("Z", "+00:00")
    )
    receipt_generated = datetime.fromisoformat(
        receipt["generated_at_utc"].replace("Z", "+00:00")
    )
    packet_completed = datetime.fromisoformat(
        packet_terminal["completed_at_utc"].replace("Z", "+00:00")
    )
    run_started = datetime.fromisoformat(
        mt5_started["started_at_utc"].replace("Z", "+00:00")
    )
    if not chronology_is_valid(
        probe_issued,
        packet_started,
        receipt_generated,
        packet_completed,
        issued,
        run_started,
    ):
        raise ValueError("HYP003 final authority chronology is invalid")


def validate_inner_journal(journal: Path) -> dict[str, Any]:
    outer = BASE.HYPOTHESIS_ID
    BASE.HYPOTHESIS_ID = INNER_ID
    try:
        return ORIGINAL_SIGNAL(journal)
    finally:
        BASE.HYPOTHESIS_ID = outer


BASE.validate_authority_metadata = validate_outer_authority
BASE.validate_bound_files_after_claim = validate_outer_bound
BASE.validate_signal_journal = validate_inner_journal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--contract-receipt", type=Path, required=True)
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    receipt = BASE.execute(args.registry, args.contract_receipt)
    print(
        json.dumps(
            {
                "outer_hypothesis_id": OUTER_ID,
                "inner_implementation_hypothesis_id": INNER_ID,
                "verdict": receipt["verdict"],
                "run": receipt["alpha_run_dir"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
