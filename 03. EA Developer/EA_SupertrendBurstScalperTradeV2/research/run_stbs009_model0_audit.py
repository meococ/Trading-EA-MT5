#!/usr/bin/env python3
"""Claim, run and seal the sole HYP009 no-trade Model-0 audit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV2"
RESEARCH = PACKAGE / "research"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
QUANT_ANALYZER = ROOT / "02. AlphaFactory" / "analysis" / "quant_analyzer.py"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV2.mq5"
CANONICAL_EX5 = PACKAGE / "EA_SupertrendBurstScalperTradeV2.ex5"
CANONICAL_COMPILE_LOG = PACKAGE / "EA_SupertrendBurstScalperTradeV2.log"
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-009_FLAT_FASTPATH_PREREG.md"
RECEIPT = RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-009/V1/contract_receipt.control.json"
TASK = RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-009/V1/task_packet.control.json"
SNAPSHOT = RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-009/V1/candidate_registry.pre_mt5.jsonl"
PACKET_ROOT = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-009/STBS009-PACKET-BUILD-001"
ATTEMPT_ROOT = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-009/STBS009-MODEL0-AUDIT-001"
STATIC_EX5_ARCHIVE = PACKET_ROOT / "EA_SupertrendBurstScalperTradeV2.static.ex5"
STATIC_LOG_ARCHIVE = PACKET_ROOT / "EA_SupertrendBurstScalperTradeV2.static_compile.log"
RUN_COMPILE_LOG_ARCHIVE = ATTEMPT_ROOT / "run_compile_log.bin"
BUILDER = RESEARCH / "build_stbs009_audit_packet.py"
RUNNER = Path(__file__).resolve()
HARNESS_TEST = PACKAGE / "tests" / "test_stbs009_audit_harness.py"
RESERVED_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-009_POST_PACKET_REVIEW.md"
ORACLE = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
)
ORACLE_SHA256 = "63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096"
RUNS_ROOT = ROOT / "02. AlphaFactory" / "runs" / "EA_SupertrendBurstScalperTradeV2"
ALPHA_TESTER_ROOT = ROOT / "AlphaTester"
HYPOTHESIS = "HYP-STBS-XAUUSD-M15-009"
PARENT = "HYP-STBS-XAUUSD-M15-008"
PACKET_ATTEMPT = "STBS009-PACKET-BUILD-001"
RUN_ATTEMPT = "STBS009-MODEL0-AUDIT-001"
RUN_VERDICT = "FROZEN_STBS009_MODEL0_AUDIT_AUTHORIZED"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
EA_NAME = "EA_SupertrendBurstScalperTradeV2"
TESTER_EXPERTS_ROOT = (
    ROOT / "02. AlphaFactory" / "runtime" / "mt5-portable-fivepercent" /
    "MQL5" / "Experts" / "AlphaFactoryRuns" / EA_NAME
)
SOURCE_SHA256 = "D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB"
EXACT_OVERRIDES = "InpAuditOnly=true"
RESERVED_REPO_PATH = (
    "03. EA Developer/EA_SupertrendBurstScalperTradeV2/research/"
    "HYP-STBS-XAUUSD-M15-009_POST_PACKET_REVIEW.md"
)
RESERVED_STATUS_LINE = f'?? "{RESERVED_REPO_PATH}"'
EXPECTED_COUNTS = {
    "raw": 690, "executable": 683, "gaps": 7, "long": 339,
    "short": 344, "atr_ready": 683, "geometry_ready": 683,
}
EXPECTED_COLSPANS = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]
SUPPORTED_ORDER_HEADINGS = ("Orders", "C\u00e1c l\u1ec7nh \u0111\u1eb7t")
EXPECTED_DATA_ACCEPTANCE = {
    "history_quality_operator": "gt",
    "history_quality_threshold_pct": 97,
    "coverage_mode": "fixed_window",
    "mandatory_symbols": ["XAUUSD"],
    "no_skip": True,
    "require_tester_journal_bounds": True,
    "require_series_proof": True,
}
RUN_TRUE_FIELDS = (
    "model0_audit_run_authorized", "mt5_authorized", "model0_authorized",
    "model0_data_acquisition_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "artifact_collection_authorized",
    "comparator_execution_authorized",
)
RUN_FALSE_FIELDS = (
    "packet_build_authorized", "model0_performance_authorized",
    "model4_authorized", "model4_data_acquisition_authorized",
    "model4_performance_authorized", "source_run_authorized",
    "compile_authorized", "standalone_compile_authorized", "trade_api_authorized",
    "performance_metrics_authorized", "outcome_prices_authorized",
    "post_event_ohlc_authorized", "visual_mode_authorized",
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


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def require_data_acceptance_documents(receipt: dict[str, Any], task: dict[str, Any]) -> None:
    if (
        receipt.get("data_acceptance_contract") != EXPECTED_DATA_ACCEPTANCE
        or task.get("data_acceptance_contract") != EXPECTED_DATA_ACCEPTANCE
    ):
        raise ValueError("packet full data-acceptance contract mismatch")


def require_packet_chronology(*values: str) -> None:
    parsed = [parse_time(value) for value in values]
    if parsed != sorted(parsed):
        raise ValueError("probe/packet/screened/run chronology is invalid")


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


def require_bound_file(path: Path, expected: Any, label: str) -> None:
    expected_text = str(expected or "")
    if not path.is_file() or not re.fullmatch(r"[A-F0-9]{64}", expected_text):
        raise ValueError(f"{label} is absent or has invalid authority hash")
    actual = sha_file(path)
    if actual != expected_text:
        raise ValueError(f"{label} changed: expected {expected_text}, got {actual}")


def snapshot_file_once(source: Path, destination: Path) -> str:
    before = source.stat()
    raw = source.read_bytes()
    after = source.stat()
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or len(raw) != before.st_size
    ):
        raise ValueError(f"mutable source changed while snapshotting: {source}")
    write_exclusive(destination, raw)
    digest = sha_bytes(raw)
    if sha_file(destination) != digest:
        raise ValueError(f"snapshot hash mismatch: {destination}")
    return digest


def claim(declared_receipt_sha: str) -> Path:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    marker = ATTEMPT_ROOT / "attempt_started.json"
    write_exclusive(marker, json_bytes({
        "schema_version": "stbs009_model0_audit_started.v1",
        "hypothesis_id": HYPOTHESIS, "attempt_id": RUN_ATTEMPT,
        "status": "STARTED", "started_at_utc": now_text(),
        "declared_receipt_path": str(RECEIPT.resolve()),
        "declared_receipt_sha256": declared_receipt_sha,
        "process_id": os.getpid(), "same_id_retry_authorized": False,
    }))
    return marker


def validate_authority_after_claim(marker: Path, declared_receipt_sha: str) -> tuple[dict[str, Any], dict[str, str]]:
    raw, row = latest_row(REGISTRY, HYPOTHESIS)
    parent_raw, parent = latest_row(REGISTRY, PARENT)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "verdict": row.get("verdict") == RUN_VERDICT,
        "parent": row.get("parent_candidate") == PARENT,
        "ea": row.get("ea_name") == EA_NAME,
        "symbol_timeframe": row.get("symbol") == "XAUUSD" and row.get("timeframe") == "M15",
        "window": row.get("window") == {"from": "2018.01.01", "to": "2022.12.31"},
        "model": row.get("model") == 0,
        "source": row.get("source_hash") == SOURCE_SHA256,
        "overrides": row.get("exact_overrides") == EXACT_OVERRIDES,
        "data_contract": row.get("evidence_contract_kind") == "data_acquisition",
        "data_acceptance": row.get("data_acceptance_contract") == EXPECTED_DATA_ACCEPTANCE,
        "no_economic_contract": row.get("acceptance_contract") is None,
        "authority": validation.get("authority") == AUTHORITY,
        "packet_consumed": metrics.get("packet_build_attempts_consumed") == 1,
        "run_unused": metrics.get("model0_audit_attempts_consumed") == 0,
        "run_limit": validation.get("model0_audit_attempt_limit") == 1,
        "run_id": validation.get("model0_audit_attempt_id") == RUN_ATTEMPT,
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
        "true_permissions": all(validation.get(name) is True for name in RUN_TRUE_FIELDS),
        "false_permissions": all(validation.get(name) is False for name in RUN_FALSE_FIELDS),
        "receipt_cli": validation.get("contract_receipt_sha256") == declared_receipt_sha,
        "parent_terminal": parent.get("state") == "parked"
        and parent.get("verdict")
        == "PARK_ENGINEERING_INVALID_MODEL0_TIMEOUT_PRE_REPORT_NO_ECONOMIC_READOUT",
        "parent_raw": validation.get("hyp008_terminal_row_sha256") == sha_bytes(parent_raw),
        "chronology": parse_time(row["updated_at_utc"])
        <= parse_time(json.loads(marker.read_text(encoding="utf-8"))["started_at_utc"]),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP009 screened audit authority failed: {failed}")
    bound = {
        RECEIPT: "contract_receipt_sha256", TASK: "task_packet_sha256",
        SNAPSHOT: "registry_snapshot_sha256", BUILDER: "reviewed_packet_builder_sha256",
        RUNNER: "reviewed_model0_audit_launcher_sha256",
        HARNESS_TEST: "reviewed_audit_harness_test_sha256",
        ALPHA: "alphafactory_sha256", QUANT_ANALYZER: "quant_analyzer_sha256",
        ORACLE: "parent_oracle_sha256",
        STATIC_EX5_ARCHIVE: "static_ex5_archive_sha256",
        STATIC_LOG_ARCHIVE: "static_compile_log_archive_sha256",
        PACKET_ROOT / "attempt_started.json": "packet_build_attempt_started_sha256",
        PACKET_ROOT / "attempt_terminal.json": "packet_build_attempt_terminal_sha256",
    }
    for path, field in bound.items():
        require_bound_file(path.resolve(), validation.get(field), field)
    if validation.get("parent_oracle_sha256") != ORACLE_SHA256:
        raise ValueError("authority does not bind the frozen ST003 oracle hash")
    require_bound_file(SOURCE.resolve(), row.get("source_hash"), "source_hash")
    require_bound_file(PREREG.resolve(), row.get("prereg_sha256"), "prereg_sha256")
    if sha_file(RECEIPT) != declared_receipt_sha:
        raise ValueError("actual receipt differs from declared receipt hash")
    review_raw = RESERVED_REVIEW.read_bytes()
    if sha_bytes(review_raw) != validation.get("independent_post_packet_review_sha256"):
        raise ValueError("post-packet review hash mismatch")
    review_text = review_raw.decode("utf-8", errors="strict")
    required_prefix = "# HYP009 post-packet independent review\n\nVerdict: `PASS_SCREENED_AUTHORITY`\n"
    if not review_text.startswith(required_prefix) or "RESERVED_NON_AUTHORITATIVE_PLACEHOLDER" in review_text:
        raise ValueError("post-packet review semantics failed")
    return row, {"registry_sha256": sha_file(REGISTRY), "latest_row_sha256": sha_bytes(raw)}


def validate_packet_chain_after_claim(row: dict[str, Any]) -> None:
    validation = row["validation"]
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    task = json.loads(TASK.read_text(encoding="utf-8"))
    packet_start = json.loads((PACKET_ROOT / "attempt_started.json").read_text(encoding="utf-8"))
    packet_terminal = json.loads((PACKET_ROOT / "attempt_terminal.json").read_text(encoding="utf-8"))
    run_start = json.loads((ATTEMPT_ROOT / "attempt_started.json").read_text(encoding="utf-8"))
    require_data_acceptance_documents(receipt, task)
    expected_reserved = [{
        "path": RESERVED_REPO_PATH, "sealed_status_line": RESERVED_STATUS_LINE,
        "placeholder_status": "RESERVED_NON_AUTHORITATIVE_PLACEHOLDER",
        "immutable_evidence": False, "final_review": False,
    }]
    checks = {
        "receipt_schema": receipt.get("schema_version") == "alphafactory_execution_receipt.v1",
        "receipt_authority": receipt.get("authority") == AUTHORITY,
        "receipt_hypothesis": receipt.get("hypothesis_id") == HYPOTHESIS,
        "receipt_attempt": receipt.get("packet_build_attempt_id") == PACKET_ATTEMPT,
        "receipt_probe_raw": receipt.get("authority_row_sha256")
        == validation.get("packet_build_authority_row_sha256"),
        "receipt_task": receipt.get("task_packet_sha256") == sha_file(TASK),
        "receipt_no_performance": receipt.get("performance_metrics_authorized") is False,
        "receipt_no_economics": receipt.get("economics_authorized") is False,
        "receipt_data_acceptance": receipt.get("data_acceptance_contract")
        == EXPECTED_DATA_ACCEPTANCE,
        "task_authority": task.get("authority") == AUTHORITY,
        "task_no_performance": task.get("performance_metrics_authorized") is False,
        "task_no_economics": task.get("economics_authorized") is False,
        "task_data_acceptance": task.get("data_acceptance_contract")
        == EXPECTED_DATA_ACCEPTANCE,
        "reserved_receipt": receipt.get("reserved_mutable_control_paths") == expected_reserved,
        "reserved_task": task.get("reserved_mutable_control_paths") == expected_reserved,
        "packet_terminal": packet_terminal.get("status") == "COMPLETE",
        "packet_no_retry": packet_terminal.get("same_id_retry_authorized") is False,
        "packet_receipt": packet_terminal.get("contract_receipt_sha256") == sha_file(RECEIPT),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP009 packet chain failed: {failed}")
    evidence_paths: set[Path] = set()
    for item in receipt.get("evidence", []):
        path = Path(str(item.get("path", ""))).resolve()
        if path in evidence_paths:
            raise ValueError("receipt has duplicate evidence path")
        evidence_paths.add(path)
        if item.get("kind") != "file":
            raise ValueError("receipt contains non-file evidence")
        require_bound_file(path, item.get("sha256"), f"receipt evidence {item.get('label')}")
    if RESERVED_REVIEW.resolve() in evidence_paths:
        raise ValueError("reserved review was incorrectly sealed as immutable evidence")
    snapshot_raw, _ = latest_row(SNAPSHOT, HYPOTHESIS)
    if sha_bytes(snapshot_raw) != receipt.get("authority_row_sha256"):
        raise ValueError("packet registry snapshot probe row mismatch")
    require_packet_chronology(
        receipt["authority_issued_at_utc"], packet_start["started_at_utc"],
        receipt["generated_at_utc"], packet_terminal["completed_at_utc"],
        row["updated_at_utc"], run_start["started_at_utc"],
    )
    live_status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.decode("utf-8").splitlines()
    if live_status != task.get("git_status") or live_status.count(RESERVED_STATUS_LINE) != 1:
        raise ValueError("live Git path set differs from sealed packet")


def parse_keyed_lines(text: str, prefix: str) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for line in text.splitlines():
        position = line.find(prefix)
        if position < 0:
            continue
        payload = line[position:].strip()
        fields: dict[str, str] = {"record": prefix.removesuffix("|")}
        for part in payload.split("|")[1:]:
            if "=" not in part:
                raise ValueError(f"malformed {prefix} field: {part!r}")
            key, value = part.split("=", 1)
            if not key or key in fields:
                raise ValueError(f"missing/duplicate {prefix} field: {key!r}")
            fields[key] = value
        parsed.append(fields)
    return parsed


def iso_epoch(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def server_axis_text(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y.%m.%d %H:%M:%S")


def load_oracle_rows() -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in ORACLE.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if not rows or len({int(row["source_epoch"]) for row in rows}) != len(rows):
        raise ValueError("parent oracle full source axis is empty or non-unique")
    return rows


def load_expected_events() -> list[dict[str, Any]]:
    rows = [row for row in load_oracle_rows() if row.get("raw_event") == 1]
    rows.sort(key=lambda item: int(item["source_epoch"]))
    if len(rows) != EXPECTED_COUNTS["raw"]:
        raise ValueError("parent oracle raw-event population changed")
    return rows


def validate_signal_journal(journal: Path) -> dict[str, Any]:
    text = journal.read_text(encoding="utf-8-sig", errors="strict")
    forbidden = (
        "STBS_FATAL|", "STBS_ENTRY_REQUEST|", "STBS_CLOSE_REQUEST|",
        "STBS_CANCEL_REQUEST|", "STBS_REQUEST_RESULT|", "STBS_DEAL|",
    )
    found = [token for token in forbidden if token in text]
    if found:
        raise ValueError(f"journal contains forbidden runtime/trade records: {found}")
    physical_signals = parse_keyed_lines(text, "STBS_SIGNAL|")
    summaries = parse_keyed_lines(text, "STBS_SUMMARY|")
    if not summaries:
        raise ValueError("journal has no STBS_SUMMARY")
    summary_payloads = {json.dumps(item, sort_keys=True, separators=(",", ":")) for item in summaries}
    if len(summary_payloads) != 1:
        raise ValueError("journal contains non-identical STBS_SUMMARY records")
    summary = summaries[0]
    multiplicity = len(summaries)
    expected_summary = {
        "hypothesis": HYPOTHESIS,
        **{name: str(value) for name, value in EXPECTED_COUNTS.items()},
        "entries": "0", "entry_rejects": "0", "closes": "0",
        "exec_state": "0", "exit_intent": "0", "failed": "false",
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            raise ValueError(f"summary {field} mismatch: expected {expected}, got {summary.get(field)}")
    groups: dict[int, list[dict[str, str]]] = {}
    for signal in physical_signals:
        source_epoch = int(signal.get("source_epoch", "-1"))
        groups.setdefault(source_epoch, []).append(signal)
    signals: list[dict[str, str]] = []
    for source_epoch in sorted(groups):
        records = groups[source_epoch]
        payloads = {json.dumps(item, sort_keys=True, separators=(",", ":")) for item in records}
        if len(payloads) != 1:
            raise ValueError(f"source_epoch {source_epoch} has conflicting duplicate payloads")
        if len(records) != multiplicity:
            raise ValueError(
                f"source_epoch {source_epoch} multiplicity {len(records)} != summary multiplicity {multiplicity}"
            )
        signals.append(records[0])
    all_oracle = load_oracle_rows()
    by_server_epoch = {int(row["source_epoch"]): row for row in all_oracle}
    expected = [row for row in all_oracle if row.get("raw_event") == 1]
    expected.sort(key=lambda row: int(row["source_epoch"]))
    if len(signals) != len(expected):
        raise ValueError(f"unique signal population mismatch: {len(signals)} != {len(expected)}")
    exact_count = long_count = short_count = atr_count = geometry_count = 0
    for index, (actual, oracle) in enumerate(zip(signals, expected, strict=True)):
        source_epoch = int(actual.get("source_epoch", "-1"))
        decision_epoch = int(actual.get("decision_epoch", "-1"))
        executable = oracle.get("executable_event") == 1
        next_oracle = by_server_epoch.get(int(oracle["next_source_epoch"]))
        if next_oracle is None:
            raise ValueError(f"signal {index} next oracle row is absent")
        expected_source_utc = iso_epoch(str(oracle["time_utc"]))
        expected_decision_utc = iso_epoch(str(next_oracle["time_utc"]))
        expected_source_server = server_axis_text(int(oracle["source_epoch"]))
        expected_decision_server = server_axis_text(int(oracle["next_source_epoch"]))
        comparisons = {
            "source_utc_epoch": source_epoch == expected_source_utc,
            "decision_utc_epoch": decision_epoch == expected_decision_utc,
            "source_server_text": actual.get("source") == expected_source_server,
            "decision_server_text": actual.get("decision") == expected_decision_server,
            "server_span": int(oracle["next_source_epoch"]) - int(oracle["source_epoch"])
            == int((datetime.strptime(actual.get("decision", ""), "%Y.%m.%d %H:%M:%S")
                    - datetime.strptime(actual.get("source", ""), "%Y.%m.%d %H:%M:%S")).total_seconds()),
            "direction": actual.get("direction") == oracle.get("direction"),
            "exact_next": actual.get("exact_next") == ("true" if executable else "false"),
        }
        failed = [name for name, passed in comparisons.items() if not passed]
        if failed:
            raise ValueError(f"signal {index} parent mismatch: {failed}")
        if executable:
            exact_count += 1
            if actual.get("atr_ready") != "true" or actual.get("geometry_ready") != "true":
                raise ValueError(f"signal {index} lacks ATR/geometry readiness")
            if actual.get("audit") != "true":
                raise ValueError(f"signal {index} did not execute through audit-only path")
            values = {name: float(actual.get(name, "nan"))
                      for name in ("atr", "entry", "sl", "tp", "volume")}
            if not all(math.isfinite(value) and value > 0.0 for value in values.values()):
                raise ValueError(f"signal {index} has invalid geometry values")
            if actual["direction"] == "LONG":
                long_count += 1
                if not values["sl"] < values["entry"] < values["tp"]:
                    raise ValueError(f"signal {index} LONG geometry is wrong-sided")
            else:
                short_count += 1
                if not values["tp"] < values["entry"] < values["sl"]:
                    raise ValueError(f"signal {index} SHORT geometry is wrong-sided")
            atr_count += 1
            geometry_count += 1
        elif actual.get("consumed") != "true":
            raise ValueError(f"gap signal {index} was not consumed")
    reconciled = {
        "raw": len(signals), "executable": exact_count,
        "gaps": len(signals) - exact_count, "long": long_count,
        "short": short_count, "atr_ready": atr_count,
        "geometry_ready": geometry_count,
    }
    if reconciled != EXPECTED_COUNTS:
        raise ValueError(f"reconciled signal counts changed: {reconciled}")
    return {**reconciled, "journal_record_multiplicity": multiplicity}


def parse_colspans(cells: list[tuple[str, str]]) -> list[int] | None:
    values: list[int] = []
    for attrs, _ in cells:
        occurrences = len(re.findall(r"\bcolspan\b", attrs, re.I))
        matches = re.findall(
            r"\bcolspan\s*=\s*(?:\"([0-9]+)\"|'([0-9]+)'|([0-9]+))(?=\s|$)", attrs, re.I,
        )
        if occurrences > 1 or (occurrences == 1 and len(matches) != 1):
            return None
        digits = next((part for part in matches[0] if part), "") if matches else ""
        value = int(digits) if digits else 1
        if value <= 0:
            return None
        values.append(value)
    return values


def orders_section_is_empty(html: str) -> bool:
    heading_pattern = "|".join(re.escape(value) for value in SUPPORTED_ORDER_HEADINGS)
    headings = list(re.finditer(rf"<b>\s*(?:{heading_pattern})\s*</b>", html, re.I))
    deals = list(re.finditer(r"<b>\s*Deals\s*</b>", html, re.I))
    if len(headings) != 1 or len(deals) != 1 or deals[0].start() <= headings[0].end():
        return False
    section = html[headings[0].end(): deals[0].start()]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", section, re.I | re.S)
    if len(rows) != 2:
        return False
    cells = re.compile(r"<td([^>]*)>(.*?)</td>", re.I | re.S)
    header = cells.findall(rows[0])
    spacer = cells.findall(rows[1])
    if len(header) != 11 or parse_colspans(header) != EXPECTED_COLSPANS:
        return False
    if not all(re.fullmatch(r"\s*<b>.*?</b>\s*", inner, re.I | re.S) for _, inner in header):
        return False
    return (
        len(spacer) == 1 and parse_colspans(spacer) == [1]
        and re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""
    )


def exact_funding_only(report_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("stbs009_quant_analyzer", QUANT_ANALYZER)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load quant analyzer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    deals = module.parse_deals_from_html_report(report_path)
    expected = module.Deal(
        time=datetime(2005, 1, 1, 0, 0, 0), deal_id=1, symbol="",
        side="balance", direction="", volume=0.0, price=0.0, order_id=None,
        commission=0.0, swap=0.0, profit=10000.0, balance=10000.0, comment="",
    )
    if deals != [expected]:
        raise ValueError("report is not the exact sole tester-start funding row")


def decode_artifact(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="strict")
    return raw.decode("utf-8-sig", errors="strict")


def parse_ini_exact(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line_number, raw_line in enumerate(decode_artifact(path).splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        section = re.fullmatch(r"\[([^\[\]]+)\]", line)
        if section:
            name = section.group(1)
            if name in sections:
                raise ValueError(f"duplicate config section {name!r} at line {line_number}")
            current = {}
            sections[name] = current
            continue
        if current is None or "=" not in line:
            raise ValueError(f"malformed config line {line_number}")
        key, value = line.split("=", 1)
        if not key or key in current:
            raise ValueError(f"missing/duplicate config key {key!r} at line {line_number}")
        current[key] = value
    return sections


def validate_config(path: Path, run_id: str) -> None:
    expected = {
        "Tester": {
            "Expert": f"AlphaFactoryRuns\\{EA_NAME}\\{run_id}\\{EA_NAME}.ex5",
            "Symbol": "XAUUSD", "Period": "M15", "Optimization": "0",
            "Visual": "0", "Model": "0", "ExecutionMode": "0", "Dates": "2",
            "FromDate": "2005.01.01", "ToDate": "2023.01.01",
            "Report": f"MQL5\\Profiles\\Tester\\AlphaRuns\\{run_id}\\report.html",
            "ReplaceReport": "1", "ShutdownTerminal": "1", "Deposit": "10000",
            "Currency": "USD", "Leverage": "100",
        },
        "TesterInputs": {"InpAuditOnly": "true||true||0||true||N"},
    }
    actual = parse_ini_exact(path)
    if actual != expected:
        raise ValueError(f"tester config differs from frozen contract: {actual}")


def require_exact_new_run(before: set[Path], after: set[Path], run_dir: Path) -> None:
    if run_dir.parent != RUNS_ROOT.resolve() or after != before | {run_dir}:
        raise ValueError("AlphaFactory did not create exactly a fresh canonical HYP009 run")


def validate_run(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "run_manifest.json"
    report_path = run_dir / "report.html"
    journal_path = run_dir / "logs/tester_journal_delta.log"
    summary_path = run_dir / "analysis/enhanced_summary.json"
    for path in (manifest_path, report_path, journal_path, summary_path):
        if not path.is_file():
            raise ValueError(f"required run artifact is absent: {path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    snapshot_root = (run_dir / "snapshot").resolve()
    source_snapshot = (snapshot_root / "source" / f"{EA_NAME}.mq5").resolve()
    ex5_snapshot = (snapshot_root / "build" / f"{EA_NAME}.ex5").resolve()
    config_snapshot = (snapshot_root / "config" / "config.ini").resolve()
    run_id = run_dir.name
    staged_ex5 = (TESTER_EXPERTS_ROOT / run_id / f"{EA_NAME}.ex5").resolve()
    live_config = (ALPHA_TESTER_ROOT / run_id / "config.ini").resolve()
    for path in (
        source_snapshot, ex5_snapshot, config_snapshot, staged_ex5,
        live_config, CANONICAL_EX5.resolve(), RUN_COMPILE_LOG_ARCHIVE.resolve(),
    ):
        if not path.is_file():
            raise ValueError(f"exact run-local snapshot artifact is absent: {path}")
    validate_config(config_snapshot, run_id)
    validate_config(live_config, run_id)
    compile_results = re.findall(
        r"(?m)^Result:\s*(\d+)\s+errors,\s*(\d+)\s+warnings\s*$",
        decode_artifact(RUN_COMPILE_LOG_ARCHIVE),
    )
    if compile_results != [("0", "0")]:
        raise ValueError(f"run compile log is not exact 0E/0W: {compile_results}")
    journal_sha = sha_file(journal_path)
    sidecars = manifest.get("sidecars")
    sidecars_ok = (
        isinstance(sidecars, list) and len(sidecars) == 1
        and sidecars[0].get("path") == "logs/tester_journal_delta.log"
        and sidecars[0].get("sha256") == journal_sha
        and sidecars[0].get("length") == journal_path.stat().st_size
        and sidecars[0].get("row_count") is None
    )
    geometry = manifest.get("contract_symbol_geometry", {})
    checks = {
        "schema": manifest.get("schema_version") == "alphafactory_run_manifest.v2",
        "run_id": manifest.get("run_id") == run_id
        and re.fullmatch(r"\d{8}_\d{6}", run_id) is not None,
        "run_role": manifest.get("run_role") == "control",
        "hypothesis": manifest.get("hypothesis_id") == HYPOTHESIS,
        "ea": manifest.get("ea_name") == EA_NAME,
        "symbol": manifest.get("symbol") == "XAUUSD", "period": manifest.get("period") == "M15",
        "from": manifest.get("from") == "2005.01.01", "to": manifest.get("to") == "2023.01.01",
        "model": manifest.get("model") == 0, "execution": manifest.get("execution_mode") == 0,
        "delay": manifest.get("fixed_delay_ms") == 0, "timeout": manifest.get("timeout_sec") == 300,
        "overrides": manifest.get("overrides") == EXACT_OVERRIDES,
        "telemetry": manifest.get("telemetry_profile") == "none"
        and manifest.get("telemetry_tier") == "off",
        "deposit": manifest.get("deposit") == 10000,
        "leverage": manifest.get("leverage") == 100,
        "spread": manifest.get("spread") == "current",
        "visual": manifest.get("visual_mode") is False,
        "indicators": manifest.get("indicator_dependencies") == [],
        "required_sidecars": manifest.get("required_sidecars") == [],
        "sidecars": sidecars_ok,
        "geometry": geometry.get("digits") == 2
        and geometry.get("point") == 0.01 and geometry.get("pip_size") == 0.01,
        "source": manifest.get("source_sha256") == SOURCE_SHA256,
        "main_file": Path(str(manifest.get("main_file", ""))).resolve() == SOURCE.resolve(),
        "compiled_ex5": Path(str(manifest.get("compiled_ex5_file", ""))).resolve()
        == CANONICAL_EX5.resolve(),
        "staged_ex5": Path(str(manifest.get("ex5_file", ""))).resolve() == staged_ex5
        and Path(str(manifest.get("tester_ex5_path", ""))).resolve() == staged_ex5,
        "live_config": Path(str(manifest.get("config_file", ""))).resolve() == live_config,
        "run_root": Path(str(manifest.get("local_run_dir", ""))).resolve() == run_dir,
        "snapshot_root": Path(str(manifest.get("snapshot_root", ""))).resolve() == snapshot_root,
        "source_snapshot_path": Path(str(manifest.get("source_snapshot", ""))).resolve() == source_snapshot,
        "ex5_snapshot_path": Path(str(manifest.get("ex5_snapshot", ""))).resolve() == ex5_snapshot,
        "config_snapshot_path": Path(str(manifest.get("config_snapshot", ""))).resolve() == config_snapshot,
        "report_path": Path(str(manifest.get("report_path", ""))).resolve() == report_path,
        "source_snapshot_hash": sha_file(source_snapshot) == SOURCE_SHA256,
        "ex5_snapshot_hash": manifest.get("ex5_sha256") == sha_file(ex5_snapshot)
        == sha_file(staged_ex5) == sha_file(CANONICAL_EX5),
        "tester_ex5_hash": manifest.get("tester_ex5_sha256") == manifest.get("ex5_sha256"),
        "config_snapshot_hash": manifest.get("config_sha256") == sha_file(config_snapshot)
        == sha_file(live_config),
        "include_closure": manifest.get("includes_sha256") == hashlib.sha256(b"").hexdigest().upper(),
        "include_snapshots": manifest.get("include_snapshots") == [],
        "receipt": manifest.get("contract_receipt_sha256") == sha_file(RECEIPT),
        "report_hash": manifest.get("report_sha256") == sha_file(report_path),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"run manifest mismatch: {failed}")
    gate = manifest.get("data_quality_gate", {})
    proof = gate.get("series_proof", {})
    if (
        float(gate.get("history_quality", 0.0)) <= 97.0
        or gate.get("actual_from", "9999.99.99") > "2005.01.01"
        or gate.get("actual_to", "0000.00.00") < "2023.01.01"
        or gate.get("coverage_class") != "FULL_2018_PLUS"
        or gate.get("journal_path") != "logs/tester_journal_delta.log"
        or gate.get("journal_sha256") != journal_sha
        or gate.get("journal_truncated") is not False
        or proof.get("m5_synchronized") != 1
        or proof.get("copytime_result") != 1
        or proof.get("copytime_last_error") != 0
        or proof.get("copytime_first_epoch") != proof.get("m5_first_epoch")
    ):
        raise ValueError("data-quality/history/series proof gate failed")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("schema_version") != "alphafactory_zero_trade_collection_summary.v1"
        or summary.get("n_trades") != 0
        or summary.get("performance_metrics_authorized") is not False
    ):
        raise ValueError("zero-trade collection summary is invalid")
    html = report_path.read_text(encoding="utf-16", errors="strict")
    if not orders_section_is_empty(html):
        raise ValueError("tester report Orders section is not exactly empty")
    exact_funding_only(report_path)
    counts = validate_signal_journal(journal_path)
    return {
        "manifest": manifest_path, "report": report_path, "journal": journal_path,
        "summary": summary_path, "source_snapshot": source_snapshot,
        "ex5_snapshot": ex5_snapshot, "config_snapshot": config_snapshot,
        "staged_ex5": staged_ex5, "live_config": live_config,
        "run_compile_log": RUN_COMPILE_LOG_ARCHIVE.resolve(),
        "history_quality": float(gate["history_quality"]),
        "actual_from": gate["actual_from"], "actual_to": gate["actual_to"],
        "counts": counts,
    }


def build_alpha_command(declared_receipt_sha: str) -> list[str]:
    return [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ALPHA),
        "backtest", EA_NAME, "-Symbol", "XAUUSD", "-Period", "M15",
        "-From", "2005.01.01", "-To", "2023.01.01", "-Model", "0",
        "-ExecutionMode", "0", "-FixedDelayMs", "0", "-TimeoutSec", "300",
        "-Overrides", EXACT_OVERRIDES, "-HypothesisId", HYPOTHESIS,
        "-RunRole", "control", "-TelemetryTier", "off", "-Deposit", "10000",
        "-Leverage", "100", "-ContractReceipt", str(RECEIPT),
        "-ContractReceiptSha256", declared_receipt_sha,
    ]


def execute(declared_receipt_sha: str) -> dict[str, Any]:
    marker = claim(declared_receipt_sha)
    terminal_path = ATTEMPT_ROOT / "attempt_terminal.json"
    stdout_path = ATTEMPT_ROOT / "alpha_stdout.log"
    stderr_path = ATTEMPT_ROOT / "alpha_stderr.log"
    try:
        row, authority = validate_authority_after_claim(marker, declared_receipt_sha)
        validate_packet_chain_after_claim(row)
        before = {path.resolve() for path in RUNS_ROOT.iterdir()} if RUNS_ROOT.is_dir() else set()
        command = build_alpha_command(declared_receipt_sha)
        with stdout_path.open("xb") as out, stderr_path.open("xb") as err:
            completed = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err,
                                       timeout=420, check=False)
        if completed.returncode != 0:
            raise ValueError(f"AlphaFactory returned {completed.returncode}")
        output = stdout_path.read_text(encoding="utf-8", errors="replace") + "\n" + \
            stderr_path.read_text(encoding="utf-8", errors="replace")
        matches = re.findall(r"(?m)^ALPHA_RUN_DIR=(.+?)\s*$", output)
        if len(matches) != 1:
            raise ValueError(f"expected one ALPHA_RUN_DIR receipt, found {len(matches)}")
        run_dir = Path(matches[0].strip()).resolve()
        after = {path.resolve() for path in RUNS_ROOT.iterdir()} if RUNS_ROOT.is_dir() else set()
        require_exact_new_run(before, after, run_dir)
        snapshot_file_once(CANONICAL_COMPILE_LOG.resolve(), RUN_COMPILE_LOG_ARCHIVE)
        validated = validate_run(run_dir)
        bindings: dict[str, Any] = {
            "launcher": {"path": str(RUNNER), "sha256": sha_file(RUNNER)},
            "registry": {"path": str(REGISTRY), **authority},
            "contract_receipt": {"path": str(RECEIPT), "sha256": sha_file(RECEIPT)},
            "attempt_started": {"path": str(marker), "sha256": sha_file(marker)},
            "alpha_stdout": {"path": str(stdout_path), "sha256": sha_file(stdout_path)},
            "alpha_stderr": {"path": str(stderr_path), "sha256": sha_file(stderr_path)},
            "parent_oracle": {"path": str(ORACLE), "sha256": sha_file(ORACLE)},
        }
        for label in (
            "manifest", "report", "journal", "summary", "source_snapshot",
            "ex5_snapshot", "config_snapshot", "staged_ex5", "live_config",
            "run_compile_log",
        ):
            path = validated[label]
            bindings[label] = {"path": str(path), "sha256": sha_file(path)}
        audit_receipt = {
            "schema_version": "stbs009_model0_audit_receipt.v1",
            "hypothesis_id": HYPOTHESIS, "attempt_id": RUN_ATTEMPT,
            "started_at_utc": json.loads(marker.read_text(encoding="utf-8"))["started_at_utc"],
            "completed_at_utc": now_text(),
            "verdict": "ENGINEERING_FASTPATH_SIGNAL_ATR_GEOMETRY_PARITY_PASS_NO_TRADES",
            "bindings": bindings, "alpha_run_dir": str(run_dir),
            "history_quality": validated["history_quality"],
            "actual_from": validated["actual_from"], "actual_to": validated["actual_to"],
            **validated["counts"], "strategy_requests": 0, "orders_executed": 0,
            "trades_executed": 0, "outcomes_read": 0, "economics_evaluated": False,
        }
        receipt_raw = json_bytes(audit_receipt)
        audit_receipt_path = ATTEMPT_ROOT / "mt5_audit_receipt.json"
        write_exclusive(audit_receipt_path, receipt_raw)
        write_exclusive(terminal_path, json_bytes({
            "schema_version": "stbs009_model0_audit_terminal.v1",
            "hypothesis_id": HYPOTHESIS, "attempt_id": RUN_ATTEMPT,
            "completed_at_utc": now_text(), "status": "COMPLETE",
            "verdict": audit_receipt["verdict"],
            "receipt_sha256": sha_bytes(receipt_raw),
            "attempt_started_sha256": sha_file(marker),
            "same_id_retry_authorized": False,
        }))
        return audit_receipt
    except BaseException as exc:
        if not terminal_path.exists():
            write_exclusive(terminal_path, json_bytes({
                "schema_version": "stbs009_model0_audit_terminal.v1",
                "hypothesis_id": HYPOTHESIS, "attempt_id": RUN_ATTEMPT,
                "completed_at_utc": now_text(), "status": "FAILED",
                "verdict": "ENGINEERING_AUDIT_ATTEMPT_FAILED_CONSUMED",
                "failure_type": type(exc).__name__, "failure": str(exc),
                "attempt_started_sha256": sha_file(marker),
                "alpha_stdout_sha256": sha_file(stdout_path) if stdout_path.exists() else "",
                "alpha_stderr_sha256": sha_file(stderr_path) if stderr_path.exists() else "",
                "same_id_retry_authorized": False,
            }))
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args()
    if re.fullmatch(r"[A-F0-9]{64}", args.receipt_sha256) is None:
        raise SystemExit("receipt SHA must be uppercase SHA256")
    result = execute(args.receipt_sha256)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
