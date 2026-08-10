#!/usr/bin/env python3
"""Run the sole outer-HYP002, inner-HYP001 no-trade MT5 audit."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTER_ID = "HYP-STBS-XAUUSD-M15-002"
INNER_ID = "HYP-STBS-XAUUSD-M15-001"
OUTER_VERDICT = "FROZEN_STBS002_MT5_AUDIT_AUTHORIZED"
OUTER_ATTEMPT_ID = "STBS002-MT5-AUDIT-001"
OUTER_PACKET_ID = "STBS002-PACKET-BUILD-001"
FAILED_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-001"
BASE_PATH = Path(__file__).resolve().with_name("run_stbs001_mt5_audit.py")
FROZEN_BASE_RUNNER_SHA256 = "C4F2976F919EF9345CFC15891A9A8066F1FB5D474635C88BB29D047456645C14"
HYP001_FAILURE_SHA256 = "DB95F9073CBB1DAB328B344AA7953DC124B71F75359EDEFC813A8BD39A977D87"
HYP001_PACKET_RECEIPT_SHA256 = "27E8C1ED204A46CDF91A16030CD6952FEAF3D2C0F1271575282156CDA31FC6F5"
HYP001_PACKET_TERMINAL_SHA256 = "FCC97A591C57CC8ED33AE86AABF3E9E5FF4B33329425CB2DAB5A23BBA7B4E28F"
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
    "HYP-STBS-XAUUSD-M15-002/STBS002-MT5-AUDIT-001"
)
PACKET_ROOT = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-002/STBS002-PACKET-BUILD-001"
)
HYP001_FAILURE_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/"
    "HYP-STBS-XAUUSD-M15-001_PACKET_AUTHORITY_CHRONOLOGY_FAILURE.md"
)
HYP001_PACKET_RECEIPT_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/preflight/"
    "HYP-STBS-XAUUSD-M15-001/V1/contract_receipt.control.json"
)
HYP001_PACKET_TERMINAL_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-001/STBS001-PACKET-BUILD-001/attempt_terminal.json"
)
HYP001_TERMINAL_FALSE_FIELDS = (
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


def hyp001_terminal_contract(row: dict[str, Any]) -> bool:
    metrics = row.get("metrics", {})
    validation = row.get("validation", {})
    return (
        row.get("state") == "killed"
        and row.get("verdict") == "KILL_PACKET_AUTHORITY_TIMESTAMP_AFTER_ATTEMPT_NO_MT5"
        and metrics.get("packet_build_attempts_consumed") == 1
        and metrics.get("mt5_audit_attempts_consumed") == 0
        and metrics.get("run_compile_attempts_consumed") == 0
        and all(validation.get(name) is False for name in HYP001_TERMINAL_FALSE_FIELDS)
        and validation.get("chronology_failure_sha256") == HYP001_FAILURE_SHA256
        and validation.get("packet_build_receipt_sha256") == HYP001_PACKET_RECEIPT_SHA256
        and validation.get("packet_build_attempt_terminal_sha256")
        == HYP001_PACKET_TERMINAL_SHA256
    )


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
        "hyp001_terminal": hyp001_terminal_contract(failed_hypothesis),
        "hyp001_terminal_row": validation.get("hyp001_terminal_row_sha256")
        == BASE.sha256_bytes(failed_raw),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP002 outer authority failed: {failed}")

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
        ("HYP001 chronology failure", HYP001_FAILURE_PATH, HYP001_FAILURE_SHA256),
        ("HYP001 invalid packet receipt", HYP001_PACKET_RECEIPT_PATH, HYP001_PACKET_RECEIPT_SHA256),
        ("HYP001 invalid packet terminal", HYP001_PACKET_TERMINAL_PATH, HYP001_PACKET_TERMINAL_SHA256),
    ):
        BASE.require_bound_file(path, digest, label)
    receipt = json.loads(contract_receipt.read_text(encoding="utf-8"))
    if receipt.get("binding", {}).get("inner_implementation_hypothesis_id") != INNER_ID:
        raise ValueError("contract receipt inner implementation identity mismatch")
    if (
        receipt.get("binding", {}).get("hyp001_terminal_row_sha256")
        != validation.get("hyp001_terminal_row_sha256")
    ):
        raise ValueError("contract receipt HYP001 terminal row mismatch")
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
        raise ValueError("HYP002 final authority chronology is invalid")


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
