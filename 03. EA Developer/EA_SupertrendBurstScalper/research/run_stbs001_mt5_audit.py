#!/usr/bin/env python3
"""Claim, execute and seal the sole no-trade HYP001 MT5 correctness audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-001"
ATTEMPT_ID = "STBS001-MT5-AUDIT-001"
PACKET_ATTEMPT_ID = "STBS001-PACKET-BUILD-001"
EA_NAME = "EA_SupertrendBurstScalper"
SOURCE_SHA256 = "B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D"
PARENT_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-012"
PARENT_TERMINAL_ROW_SHA256 = "DCF06201068DDDC52D6B225FD871F1D7A0691F9EB4B864D969A7BFD1422DF8C2"
PARENT_PARITY_RECEIPT_SHA256 = "6ED0DDA55598CAAC14D08C328DDB90E16480D64084DB28B8CA968B415D326919"
PARENT_PARITY_TERMINAL_SHA256 = "02572F12BB50BC4A3E56C7BF2D17F2449E7A0A20DBD62C32A4571B8F214FCD6B"
PARENT_SOURCE_SHA256 = "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
ORACLE_SHA256 = "63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096"
ALPHA_PS1_SHA256 = "68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8"
EXACT_OVERRIDES = "InpAuditOnly=true"
OUTPUT_DIR = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-001/STBS001-MT5-AUDIT-001"
)
ORACLE_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
)
PARENT_RECEIPT_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001/st009_full_bar_parity_receipt.json"
)
PARENT_TERMINAL_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-012/ST012-COMPARATOR-001/attempt_terminal.json"
)
PACKET_ATTEMPT_ROOT = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
    "HYP-STBS-XAUUSD-M15-001/STBS001-PACKET-BUILD-001"
)
PACKET_STARTED_PATH = PACKET_ATTEMPT_ROOT / "attempt_started.json"
PACKET_TERMINAL_PATH = PACKET_ATTEMPT_ROOT / "attempt_terminal.json"
EXPECTED_COUNTS = {
    "raw": 690,
    "executable": 683,
    "gaps": 7,
    "long": 339,
    "short": 344,
    "atr_ready": 683,
    "geometry_ready": 683,
}
EXPECTED_COLSPANS = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]


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


def decode_text(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="strict")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be", errors="strict")
    return raw.decode("utf-8-sig", errors="strict")


def latest_registry_row(path: Path, hypothesis_id: str) -> tuple[bytes, dict[str, Any]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == hypothesis_id:
                matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no row for {hypothesis_id}")
    return matches[-1]


def require_false(validation: dict[str, Any], *names: str) -> bool:
    return all(validation.get(name) is False for name in names)


def validate_authority_metadata(
    registry: Path, contract_receipt: Path
) -> tuple[dict[str, Any], dict[str, str]]:
    raw, row = latest_registry_row(registry, HYPOTHESIS_ID)
    parent_raw, parent = latest_registry_row(registry, PARENT_HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_STBS001_MT5_AUDIT_AUTHORIZED",
        "source": row.get("source_hash") == SOURCE_SHA256,
        "parent_terminal": parent.get("state") == "parked"
        and sha256_bytes(parent_raw) == PARENT_TERMINAL_ROW_SHA256,
        "authority": validation.get("authority")
        == "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "run": validation.get("mt5_audit_run_authorized") is True,
        "model0_data": validation.get("model0_data_acquisition_authorized") is True,
        "model0": validation.get("model0_authorized") is True,
        "model0_no_performance": validation.get("model0_performance_authorized") is False,
        "mt5": validation.get("mt5_authorized") is True,
        "attempt": validation.get("mt5_audit_attempt_id") == ATTEMPT_ID,
        "attempt_limit": validation.get("mt5_audit_attempt_limit") == 1,
        "attempt_unconsumed": metrics.get("mt5_audit_attempts_consumed") == 0,
        "run_compile": validation.get("run_compile_authorized") is True,
        "mql5_run_compile": validation.get("mql5_compile_authorized") is True,
        "run_compile_limit": validation.get("run_compile_attempt_limit") == 1,
        "run_compile_unconsumed": metrics.get("run_compile_attempts_consumed") == 0,
        "launcher": validation.get("reviewed_mt5_audit_launcher_sha256")
        == sha256_file(Path(__file__).resolve()),
        "alpha": validation.get("reviewed_alpha_ps1_sha256") == ALPHA_PS1_SHA256,
        "receipt_path_metadata": validation.get("contract_receipt_path")
        == contract_receipt.relative_to(ROOT).as_posix(),
        "receipt_hash_metadata": re.fullmatch(
            r"[A-F0-9]{64}", str(validation.get("contract_receipt_sha256", ""))
        )
        is not None,
        "packet_attempt": validation.get("packet_build_attempt_id")
        == PACKET_ATTEMPT_ID,
        "packet_attempt_limit": validation.get("packet_build_attempt_limit") == 1,
        "packet_attempt_consumed": metrics.get("packet_build_attempts_consumed") == 1,
        "packet_started_path": validation.get("packet_build_attempt_started_path")
        == PACKET_STARTED_PATH.relative_to(ROOT).as_posix(),
        "packet_started_hash": re.fullmatch(
            r"[A-F0-9]{64}",
            str(validation.get("packet_build_attempt_started_sha256", "")),
        )
        is not None,
        "packet_terminal_path": validation.get("packet_build_attempt_terminal_path")
        == PACKET_TERMINAL_PATH.relative_to(ROOT).as_posix(),
        "packet_terminal_hash": re.fullmatch(
            r"[A-F0-9]{64}",
            str(validation.get("packet_build_attempt_terminal_sha256", "")),
        )
        is not None,
        "parent_row": validation.get("parent_hyp012_terminal_row_sha256")
        == PARENT_TERMINAL_ROW_SHA256,
        "parent_receipt": validation.get("parent_parity_receipt_sha256")
        == PARENT_PARITY_RECEIPT_SHA256,
        "parent_terminal_artifact": validation.get("parent_parity_terminal_sha256")
        == PARENT_PARITY_TERMINAL_SHA256,
        "parent_source": validation.get("parent_mql_source_sha256")
        == PARENT_SOURCE_SHA256,
        "oracle": validation.get("parent_oracle_sha256") == ORACLE_SHA256,
        "no_trade_outcomes": require_false(
            validation,
            "trade_api_authorized",
            "performance_metrics_authorized",
            "outcome_prices_authorized",
            "post_event_ohlc_authorized",
            "economics_authorized",
        ),
        "no_research": require_false(
            validation,
            "packet_build_authorized",
            "source_run_authorized",
            "artifact_collection_authorized",
            "comparator_execution_authorized",
            "optimization_authorized",
            "validation_authorized",
            "holdout_authorized",
            "research_validation_access_authorized",
            "research_holdout_access_authorized",
        ),
        "no_deploy": require_false(
            validation,
            "model4_authorized",
            "model4_data_acquisition_authorized",
            "model4_performance_authorized",
            "visual_mode_authorized",
            "network_authorized",
            "paid_requests_authorized",
            "promotion_eligible",
            "paper_trading_authorized",
            "live_trading_authorized",
            "market_edge_claim_authorized",
        ),
        "no_extra_compile": require_false(
            validation,
            "compile_authorized",
            "standalone_compile_authorized",
        ),
        "no_retry_mutation": require_false(
            validation, "same_id_retry_authorized", "registry_mutation_allowed"
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP001 MT5 audit authority failed: {failed}")
    return row, {
        "registry_sha256": sha256_file(registry),
        "latest_row_sha256": sha256_bytes(raw),
        "parent_terminal_row_sha256": sha256_bytes(parent_raw),
    }


def require_bound_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or not re.fullmatch(r"[A-F0-9]{64}", expected or ""):
        raise ValueError(f"{label} is absent or has invalid authority hash")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} changed: expected {expected}, got {actual}")


def validate_bound_files_after_claim(
    row: dict[str, Any], contract_receipt: Path
) -> None:
    validation = row["validation"]
    bindings = {
        "source": (ROOT / row["source_path"], row["source_hash"]),
        "prereg": (ROOT / row["prereg_path"], row["prereg_sha256"]),
        "alpha": (ROOT / "02. AlphaFactory/alpha.ps1", ALPHA_PS1_SHA256),
        "contract_receipt": (contract_receipt, validation["contract_receipt_sha256"]),
        "packet_attempt_started": (
            PACKET_STARTED_PATH,
            validation["packet_build_attempt_started_sha256"],
        ),
        "packet_attempt_terminal": (
            PACKET_TERMINAL_PATH,
            validation["packet_build_attempt_terminal_sha256"],
        ),
        "parent_parity_receipt": (
            PARENT_RECEIPT_PATH,
            PARENT_PARITY_RECEIPT_SHA256,
        ),
        "parent_parity_terminal": (
            PARENT_TERMINAL_PATH,
            PARENT_PARITY_TERMINAL_SHA256,
        ),
        "parent_oracle": (ORACLE_PATH, ORACLE_SHA256),
    }
    metadata_bindings = {
        "gitignore": "gitignore",
        "engineering_test": "reviewed_engineering_test",
        "nonrepaint_manifest": "nonrepaint_manifest",
        "nonrepaint_audit": "nonrepaint_audit",
        "static_compile_receipt": "static_compile_receipt",
        "static_compile_terminal": "static_compile_terminal",
        "pre_mt5_review": "independent_pre_mt5_review",
    }
    for label, prefix in metadata_bindings.items():
        bindings[label] = (
            ROOT / validation[f"{prefix}_path"],
            validation[f"{prefix}_sha256"],
        )
    for label, (path, expected) in bindings.items():
        require_bound_file(path.resolve(), str(expected), label)
    receipt = json.loads(contract_receipt.read_text(encoding="utf-8"))
    terminal = json.loads(PACKET_TERMINAL_PATH.read_text(encoding="utf-8"))
    semantic_checks = {
        "receipt_hypothesis": receipt.get("hypothesis_id") == HYPOTHESIS_ID,
        "receipt_attempt": receipt.get("packet_build_attempt_id") == PACKET_ATTEMPT_ID,
        "receipt_started": receipt.get("packet_attempt_started_sha256")
        == validation["packet_build_attempt_started_sha256"],
        "receipt_authority_row": receipt.get("authority_row_sha256")
        == validation.get("packet_build_authority_row_sha256"),
        "terminal_hypothesis": terminal.get("hypothesis_id") == HYPOTHESIS_ID,
        "terminal_attempt": terminal.get("attempt_id") == PACKET_ATTEMPT_ID,
        "terminal_status": terminal.get("status") == "COMPLETE",
        "terminal_started": terminal.get("attempt_started_sha256")
        == validation["packet_build_attempt_started_sha256"],
        "terminal_receipt": terminal.get("contract_receipt_sha256")
        == validation["contract_receipt_sha256"],
        "terminal_no_retry": terminal.get("same_id_retry_authorized") is False,
    }
    failed = [name for name, passed in semantic_checks.items() if not passed]
    if failed:
        raise ValueError(f"packet build evidence chain failed: {failed}")


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


def load_expected_events() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in ORACLE_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("raw_event") == 1:
                rows.append(row)
    rows.sort(key=lambda row: int(row["source_epoch"]))
    if len(rows) != EXPECTED_COUNTS["raw"]:
        raise ValueError("parent oracle raw-event population changed")
    return rows


def validate_signal_journal(journal: Path) -> dict[str, Any]:
    text = journal.read_text(encoding="utf-8-sig", errors="strict")
    forbidden = ("STBS_FATAL|", "STBS_ENTRY_REQUEST|", "STBS_CLOSE_REQUEST|", "STBS_DEAL|")
    found = [token for token in forbidden if token in text]
    if found:
        raise ValueError(f"journal contains forbidden runtime/trade records: {found}")

    physical_signals = parse_keyed_lines(text, "STBS_SIGNAL|")
    summaries = parse_keyed_lines(text, "STBS_SUMMARY|")
    if not summaries:
        raise ValueError("journal has no STBS_SUMMARY")
    summary_payloads = {
        json.dumps(summary, sort_keys=True, separators=(",", ":")) for summary in summaries
    }
    if len(summary_payloads) != 1:
        raise ValueError("journal contains non-identical STBS_SUMMARY records")
    summary = summaries[0]
    multiplicity = len(summaries)
    expected_summary = {
        "hypothesis": HYPOTHESIS_ID,
        **{name: str(value) for name, value in EXPECTED_COUNTS.items()},
        "entries": "0",
        "entry_rejects": "0",
        "closes": "0",
        "failed": "false",
    }
    for field, expected in expected_summary.items():
        if summary.get(field) != expected:
            raise ValueError(
                f"summary {field} mismatch: expected {expected}, got {summary.get(field)}"
            )

    groups: dict[int, list[dict[str, str]]] = {}
    for signal in physical_signals:
        source_epoch = int(signal.get("source_epoch", "-1"))
        groups.setdefault(source_epoch, []).append(signal)
    signals: list[dict[str, str]] = []
    for source_epoch in sorted(groups):
        records = groups[source_epoch]
        payloads = {
            json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records
        }
        if len(payloads) != 1:
            raise ValueError(f"source_epoch {source_epoch} has conflicting duplicate payloads")
        if len(records) != multiplicity:
            raise ValueError(
                f"source_epoch {source_epoch} multiplicity {len(records)} != summary multiplicity {multiplicity}"
            )
        signals.append(records[0])

    expected = load_expected_events()
    if len(signals) != len(expected):
        raise ValueError(f"unique signal population mismatch: {len(signals)} != {len(expected)}")
    exact_count = long_count = short_count = atr_count = geometry_count = 0
    for index, (actual, oracle) in enumerate(zip(signals, expected, strict=True)):
        source_epoch = int(actual.get("source_epoch", "-1"))
        decision_epoch = int(actual.get("decision_epoch", "-1"))
        expected_exact = oracle.get("executable_event") == 1
        comparisons = {
            "source_epoch": source_epoch == int(oracle["source_epoch"]),
            "decision_epoch": decision_epoch == int(oracle["next_source_epoch"]),
            "direction": actual.get("direction") == oracle.get("direction"),
            "exact_next": actual.get("exact_next") == ("true" if expected_exact else "false"),
        }
        failed = [name for name, passed in comparisons.items() if not passed]
        if failed:
            raise ValueError(f"signal {index} parent mismatch: {failed}")
        if expected_exact:
            exact_count += 1
            if actual.get("atr_ready") != "true" or actual.get("geometry_ready") != "true":
                raise ValueError(f"signal {index} lacks ATR/geometry readiness")
            values = {
                name: float(actual.get(name, "nan"))
                for name in ("atr", "entry", "sl", "tp", "volume")
            }
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
        "raw": len(signals),
        "executable": exact_count,
        "gaps": len(signals) - exact_count,
        "long": long_count,
        "short": short_count,
        "atr_ready": atr_count,
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
            r"\bcolspan\s*=\s*(?:\"([0-9]+)\"|'([0-9]+)'|([0-9]+))(?=\s|$)",
            attrs,
            re.I,
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
    start = re.search(r"<b>\s*(?:Orders|Các\s+lệnh\s+đặt)\s*</b>", html, re.I)
    if not start:
        return False
    end = re.search(r"<b>\s*Deals\s*</b>", html[start.end() :], re.I)
    if not end:
        return False
    section = html[start.end() : start.end() + end.start()]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", section, re.I | re.S)
    if len(rows) != 2:
        return False
    cells = re.compile(r"<td([^>]*)>(.*?)</td>", re.I | re.S)
    header = cells.findall(rows[0])
    spacer = cells.findall(rows[1])
    if (
        len(header) != 11
        or parse_colspans(header) != EXPECTED_COLSPANS
        or sum(EXPECTED_COLSPANS) != 13
    ):
        return False
    if not all(re.fullmatch(r"\s*<b>.*?</b>\s*", inner, re.I | re.S) for _, inner in header):
        return False
    return (
        len(spacer) == 1
        and parse_colspans(spacer) == [1]
        and re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""
    )


def validate_run(run_dir: Path, contract_receipt: Path) -> dict[str, Any]:
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
    for path in (source_snapshot, ex5_snapshot, config_snapshot):
        if not path.is_file():
            raise ValueError(f"exact run-local snapshot artifact is absent: {path}")
    checks = {
        "hypothesis": manifest.get("hypothesis_id") == HYPOTHESIS_ID,
        "ea": manifest.get("ea_name") == EA_NAME,
        "symbol": manifest.get("symbol") == "XAUUSD",
        "period": manifest.get("period") == "M15",
        "from": manifest.get("from") == "2005.01.01",
        "to": manifest.get("to") == "2023.01.01",
        "model": manifest.get("model") == 0,
        "execution_mode": manifest.get("execution_mode") == 0,
        "fixed_delay": manifest.get("fixed_delay_ms") == 0,
        "overrides": manifest.get("overrides") == EXACT_OVERRIDES,
        "telemetry_profile": manifest.get("telemetry_profile") == "none",
        "telemetry_tier": manifest.get("telemetry_tier") == "off",
        "source": manifest.get("source_sha256") == SOURCE_SHA256,
        "run_root": Path(str(manifest.get("local_run_dir", ""))).resolve() == run_dir,
        "snapshot_root": Path(str(manifest.get("snapshot_root", ""))).resolve()
        == snapshot_root,
        "source_snapshot_path": Path(str(manifest.get("source_snapshot", ""))).resolve()
        == source_snapshot,
        "ex5_snapshot_path": Path(str(manifest.get("ex5_snapshot", ""))).resolve()
        == ex5_snapshot,
        "config_snapshot_path": Path(str(manifest.get("config_snapshot", ""))).resolve()
        == config_snapshot,
        "report_path": Path(str(manifest.get("report_path", ""))).resolve() == report_path,
        "source_snapshot_hash": sha256_file(source_snapshot) == SOURCE_SHA256,
        "ex5_snapshot_hash": manifest.get("ex5_sha256") == sha256_file(ex5_snapshot),
        "tester_ex5_hash": manifest.get("tester_ex5_sha256") == sha256_file(ex5_snapshot),
        "config_snapshot_hash": manifest.get("config_sha256") == sha256_file(config_snapshot),
        "include_closure": manifest.get("includes_sha256")
        == hashlib.sha256(b"").hexdigest().upper(),
        "receipt": manifest.get("contract_receipt_sha256") == sha256_file(contract_receipt),
        "report_hash": manifest.get("report_sha256") == sha256_file(report_path),
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
        or gate.get("journal_sha256") != sha256_file(journal_path)
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
    counts = validate_signal_journal(journal_path)
    return {
        "manifest": manifest_path,
        "report": report_path,
        "journal": journal_path,
        "summary": summary_path,
        "source_snapshot": source_snapshot,
        "ex5_snapshot": ex5_snapshot,
        "config_snapshot": config_snapshot,
        "history_quality": float(gate["history_quality"]),
        "actual_from": gate["actual_from"],
        "actual_to": gate["actual_to"],
        "counts": counts,
    }


def build_alpha_command(contract_receipt: Path) -> list[str]:
    return [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "02. AlphaFactory/alpha.ps1"),
        "backtest",
        EA_NAME,
        "-Symbol",
        "XAUUSD",
        "-Period",
        "M15",
        "-From",
        "2005.01.01",
        "-To",
        "2023.01.01",
        "-Model",
        "0",
        "-ExecutionMode",
        "0",
        "-FixedDelayMs",
        "0",
        "-TimeoutSec",
        "3600",
        "-Overrides",
        EXACT_OVERRIDES,
        "-HypothesisId",
        HYPOTHESIS_ID,
        "-RunRole",
        "control",
        "-TelemetryTier",
        "off",
        "-Deposit",
        "10000",
        "-Leverage",
        "100",
        "-Spread",
        "",
        "-ContractReceipt",
        str(contract_receipt),
        "-ContractReceiptSha256",
        sha256_file(contract_receipt),
    ]


def execute(registry: Path, contract_receipt: Path) -> dict[str, Any]:
    registry = registry.resolve()
    contract_receipt = contract_receipt.resolve()
    row, authority = validate_authority_metadata(registry, contract_receipt)
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError("HYP001 MT5 audit attempt already exists")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = OUTPUT_DIR / "attempt_started.json"
    write_exclusive(
        marker,
        json_bytes(
            {
                "schema_version": "stbs001_mt5_audit_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "started_at_utc": started,
                "launcher_sha256": sha256_file(Path(__file__).resolve()),
                "contract_receipt_sha256": row["validation"][
                    "contract_receipt_sha256"
                ],
                "process_id": os.getpid(),
                **authority,
            }
        ),
    )
    try:
        validate_bound_files_after_claim(row, contract_receipt)
        completed = subprocess.run(
            build_alpha_command(contract_receipt),
            cwd=ROOT,
            capture_output=True,
            timeout=3900,
            check=False,
        )
        stdout_path = OUTPUT_DIR / "alpha_stdout.log"
        stderr_path = OUTPUT_DIR / "alpha_stderr.log"
        write_exclusive(stdout_path, completed.stdout)
        write_exclusive(stderr_path, completed.stderr)
        if completed.returncode != 0:
            raise ValueError(f"AlphaFactory returned {completed.returncode}")
        output = decode_text(completed.stdout) + "\n" + decode_text(completed.stderr)
        matches = re.findall(r"(?m)^ALPHA_RUN_DIR=(.+?)\s*$", output)
        if len(matches) != 1:
            raise ValueError(f"expected one ALPHA_RUN_DIR receipt, found {len(matches)}")
        run_dir = Path(matches[0].strip()).resolve()
        validated = validate_run(run_dir, contract_receipt)
        if sha256_file(validated["source_snapshot"]) != SOURCE_SHA256:
            raise ValueError("run-local source snapshot changed")
        finished = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bindings: dict[str, Any] = {
            "launcher": {
                "path": Path(__file__).resolve().as_posix(),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "registry": {"path": registry.as_posix(), **authority},
            "contract_receipt": {
                "path": contract_receipt.as_posix(),
                "sha256": sha256_file(contract_receipt),
            },
            "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
            "alpha_stdout": {"path": stdout_path.as_posix(), "sha256": sha256_file(stdout_path)},
            "alpha_stderr": {"path": stderr_path.as_posix(), "sha256": sha256_file(stderr_path)},
            "parent_oracle": {"path": ORACLE_PATH.as_posix(), "sha256": sha256_file(ORACLE_PATH)},
            "parent_parity_receipt": {
                "path": PARENT_RECEIPT_PATH.as_posix(),
                "sha256": sha256_file(PARENT_RECEIPT_PATH),
            },
        }
        for label in (
            "manifest",
            "report",
            "journal",
            "summary",
            "source_snapshot",
            "ex5_snapshot",
            "config_snapshot",
        ):
            path = validated[label]
            bindings[label] = {"path": path.as_posix(), "sha256": sha256_file(path)}
        receipt = {
            "schema_version": "stbs001_mt5_audit_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "completed_at_utc": finished,
            "verdict": "ENGINEERING_SIGNAL_ATR_GEOMETRY_PARITY_PASS_NO_TRADES",
            "bindings": bindings,
            "alpha_run_dir": run_dir.as_posix(),
            "history_quality": validated["history_quality"],
            "actual_from": validated["actual_from"],
            "actual_to": validated["actual_to"],
            **validated["counts"],
            "orders_executed": 0,
            "trades_executed": 0,
            "outcomes_read": 0,
            "economics_evaluated": False,
        }
        receipt_raw = json_bytes(receipt)
        receipt_path = OUTPUT_DIR / "mt5_audit_receipt.json"
        write_exclusive(receipt_path, receipt_raw)
        terminal = {
            "schema_version": "stbs001_mt5_audit_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": finished,
            "status": "COMPLETE",
            "verdict": receipt["verdict"],
            "receipt_sha256": sha256_bytes(receipt_raw),
            "same_id_retry_authorized": False,
        }
        write_exclusive(OUTPUT_DIR / "attempt_terminal.json", json_bytes(terminal))
        return receipt
    except Exception as exc:
        terminal_path = OUTPUT_DIR / "attempt_terminal.json"
        if not terminal_path.exists():
            write_exclusive(
                terminal_path,
                json_bytes(
                    {
                        "schema_version": "stbs001_mt5_audit_terminal.v1",
                        "hypothesis_id": HYPOTHESIS_ID,
                        "attempt_id": ATTEMPT_ID,
                        "completed_at_utc": datetime.now(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                        "status": "FAILED",
                        "verdict": "ENGINEERING_MT5_AUDIT_FAIL",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "same_id_retry_authorized": False,
                    }
                ),
            )
        raise


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
    receipt = execute(args.registry, args.contract_receipt)
    print(json.dumps({"verdict": receipt["verdict"], "run": receipt["alpha_run_dir"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
