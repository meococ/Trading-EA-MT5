#!/usr/bin/env python3
"""One-shot comparator for the exact completed HYP003 no-trade MT5 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-004"
FAILED_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-003"
ATTEMPT_ID = "STBS004-COMPARATOR-001"
VERDICT = "ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_GEOMETRY_AUDIT_PASS"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
INNER_ID = "HYP-STBS-XAUUSD-M15-001"
EA_NAME = "EA_SupertrendBurstScalper"
SOURCE_SHA256 = "B7D0092655A602C6619DD277848168F2B926C4F5ADB1311F4DB303AAC771757D"
HYP003_TERMINAL_ROW_SHA256 = "F7813C1663BA9E14C28CB90227422A612A776743F1634DC1D25C0FE00F97D593"
HYP003_SCREENED_ROW_SHA256 = "8ECC30240CBD3DC8F66CB89EFF4771CC97980645753A08A3E4C07476EC7B15DD"
ORACLE_SHA256 = "63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096"
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
BOM = b"\xef\xbb\xbf"

RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/research"
OUTPUT_DIR = RESEARCH / (
    "evidence/HYP-STBS-XAUUSD-M15-004/STBS004-COMPARATOR-001"
)
RUN_DIR = ROOT / (
    "02. AlphaFactory/runs/EA_SupertrendBurstScalper/20260809_123517"
)
HYP003_ATTEMPT_ROOT = RESEARCH / (
    "evidence/HYP-STBS-XAUUSD-M15-003/STBS003-MT5-AUDIT-001"
)
ORACLE_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
)
PREREG_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-004_EXISTING_RUN_COMPARATOR_PREREG.md"
TEST_PATH = RESEARCH / "tests/test_stbs004_existing_run_comparator.py"
REVIEW_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-004_PRE_COMPARATOR_REVIEW.md"
PREREG_SHA256 = "6DC4A6E70E33C330C735B3995D3212C204F498AC4840DC50498A2A53AC384CD3"
TEST_SHA256 = "32C6603BE818A48B230FBDAA9850A8ACE186C008218891DF2847B5831322F028"

STATIC_BINDINGS: dict[str, tuple[Path, str]] = {
    "hyp003_attempt_started": (
        HYP003_ATTEMPT_ROOT / "attempt_started.json",
        "9FCEBA75ED34EC3E7C3A290ACD37F8B74098E2034328E6AECEBA987A4177BC03",
    ),
    "hyp003_attempt_terminal": (
        HYP003_ATTEMPT_ROOT / "attempt_terminal.json",
        "BD0A8C6FCF38982F270DE2E3045E54B038880C629217BE41CBA46D0CB5FE6495",
    ),
    "hyp003_alpha_stdout": (
        HYP003_ATTEMPT_ROOT / "alpha_stdout.log",
        "2C957E7CF213CDAA2DDBFD571B188EF302620814EF9D9F3F38D2DDAA72ED956A",
    ),
    "hyp003_alpha_stderr": (
        HYP003_ATTEMPT_ROOT / "alpha_stderr.log",
        "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
    ),
    "hyp003_contract_receipt": (
        RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-003/V1/contract_receipt.control.json",
        "9355A3960D7DBEBD33EE9CF9B86BA8748F45B53C3CC6E2EA0EA76961C64A11D2",
    ),
    "hyp003_failure": (
        RESEARCH / "HYP-STBS-XAUUSD-M15-003_POST_MT5_VALIDATOR_FAILURE.md",
        "B55AA6972FC19DD8C665E5A525C9F4122C0DCBA14FBBFCA5317925E2ADE4C0B8",
    ),
    "hyp003_failure_review": (
        RESEARCH / "HYP-STBS-XAUUSD-M15-003_POST_FAILURE_REVIEW.md",
        "C6419755734EA30BBF1C31A5F78EF378C8BC445CB11E5961C9C15DD2A59DED80",
    ),
    "run_manifest": (
        RUN_DIR / "run_manifest.json",
        "3356D5AEC1A7802029B8D0F8A60D8397E1AF56505C92946B82476D099C5BEFA4",
    ),
    "run_manifest_duplicate": (
        RUN_DIR / "config/run_manifest.json",
        "3356D5AEC1A7802029B8D0F8A60D8397E1AF56505C92946B82476D099C5BEFA4",
    ),
    "report": (
        RUN_DIR / "report.html",
        "2CB5425C5827DEC6D81B58BF0DB785B58DD2CCFC169B990AAB3F761FE4D5A591",
    ),
    "report_duplicate": (
        RUN_DIR / "build/report.html",
        "2CB5425C5827DEC6D81B58BF0DB785B58DD2CCFC169B990AAB3F761FE4D5A591",
    ),
    "journal": (
        RUN_DIR / "logs/tester_journal_delta.log",
        "3D55018CB8E6FACA8E9D397BB642576905DFD970149B9F25F62D20D4BBC35E49",
    ),
    "summary": (
        RUN_DIR / "analysis/enhanced_summary.json",
        "B42E837D0CD2B2A09CEC0996110F856EA5F0186C0FA8FB415D4F12EE78A769D0",
    ),
    "source_snapshot": (
        RUN_DIR / "snapshot/source/EA_SupertrendBurstScalper.mq5",
        SOURCE_SHA256,
    ),
    "ex5_snapshot": (
        RUN_DIR / "snapshot/build/EA_SupertrendBurstScalper.ex5",
        "9FFB9894FAD88C754853302B5AE21863A3999622BDEF3C1A2034F152069AE70D",
    ),
    "config": (
        RUN_DIR / "config.ini",
        "C61B92A196890A7C4144498B8F4F3CA4B5102D6184F4EFD2CDB1A13EA520EEDC",
    ),
    "config_duplicate": (
        RUN_DIR / "config/config.ini",
        "C61B92A196890A7C4144498B8F4F3CA4B5102D6184F4EFD2CDB1A13EA520EEDC",
    ),
    "config_snapshot": (
        RUN_DIR / "snapshot/config/config.ini",
        "C61B92A196890A7C4144498B8F4F3CA4B5102D6184F4EFD2CDB1A13EA520EEDC",
    ),
    "overrides": (
        RUN_DIR / "overrides.txt",
        "4C1A8DD80B5ECA77D15A13E312BE2DEE7B2C0DF8DB50F773E906C62EFF84E1C4",
    ),
    "overrides_duplicate": (
        RUN_DIR / "config/overrides.txt",
        "4C1A8DD80B5ECA77D15A13E312BE2DEE7B2C0DF8DB50F773E906C62EFF84E1C4",
    ),
    "oracle": (ORACLE_PATH, ORACLE_SHA256),
}

FALSE_AUTHORITIES = (
    "packet_build_authorized", "mt5_audit_run_authorized", "mt5_authorized",
    "model0_authorized", "model0_data_acquisition_authorized",
    "model0_performance_authorized", "model4_authorized",
    "model4_data_acquisition_authorized", "model4_performance_authorized",
    "source_run_authorized", "compile_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "standalone_compile_authorized",
    "trade_api_authorized", "performance_metrics_authorized",
    "outcome_prices_authorized", "post_event_ohlc_authorized",
    "artifact_collection_authorized", "visual_mode_authorized",
    "network_authorized", "paid_requests_authorized", "economics_authorized",
    "optimization_authorized", "validation_authorized", "holdout_authorized",
    "research_validation_access_authorized", "research_holdout_access_authorized",
    "promotion_eligible", "paper_trading_authorized", "live_trading_authorized",
    "market_edge_claim_authorized", "same_id_retry_authorized",
    "registry_mutation_allowed",
)


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


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode_json(raw: bytes, label: str) -> Any:
    payload = raw
    if payload.startswith(BOM):
        payload = payload[len(BOM) :]
    if BOM in payload:
        raise ValueError(f"{label} contains double/interior UTF-8 BOM")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8") from exc
    return json.loads(text, object_pairs_hook=reject_duplicate_pairs)


def decode_strict_utf8(raw: bytes, label: str) -> str:
    if BOM in raw:
        raise ValueError(f"{label} must not contain UTF-8 BOM")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8") from exc


def latest_registry_row(raw_registry: bytes, hypothesis_id: str) -> tuple[bytes, dict[str, Any]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in raw_registry.splitlines():
        if not raw.strip():
            continue
        row = decode_json(raw, "registry row")
        if row.get("hypothesis_id") == hypothesis_id:
            matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no {hypothesis_id} row")
    return matches[-1]


def validate_authority(registry: Path) -> tuple[dict[str, Any], dict[str, str]]:
    self_raw = Path(__file__).resolve().read_bytes()
    self_sha = sha256_bytes(self_raw)
    registry_raw = registry.read_bytes()
    raw, row = latest_registry_row(registry_raw, HYPOTHESIS_ID)
    failed_raw, failed = latest_registry_row(registry_raw, FAILED_HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    issued = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict")
        == "FROZEN_STBS004_EXISTING_RUN_COMPARATOR_AUTHORIZED",
        "source": row.get("source_hash") == SOURCE_SHA256,
        "prereg_path": row.get("prereg_path")
        == PREREG_PATH.relative_to(ROOT).as_posix(),
        "prereg_sha": row.get("prereg_sha256") == PREREG_SHA256,
        "authority": validation.get("authority") == AUTHORITY,
        "comparator": validation.get("comparator_execution_authorized") is True,
        "attempt": validation.get("comparator_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("comparator_attempt_limit") == 1,
        "unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "self_path": validation.get("reviewed_comparator_path")
        == Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "self": validation.get("reviewed_comparator_sha256") == self_sha,
        "test_path": validation.get("reviewed_test_path")
        == TEST_PATH.relative_to(ROOT).as_posix(),
        "test_sha": validation.get("reviewed_test_sha256") == TEST_SHA256,
        "review_path": validation.get("independent_review_path")
        == REVIEW_PATH.relative_to(ROOT).as_posix(),
        "review_sha": re.fullmatch(
            r"[A-F0-9]{64}", str(validation.get("independent_review_sha256", ""))
        ) is not None,
        "evidence_root": validation.get("comparator_evidence_root")
        == OUTPUT_DIR.relative_to(ROOT).as_posix(),
        "nonfuture": issued <= datetime.now(timezone.utc),
        "hyp003_terminal_state": failed.get("state") == "killed",
        "hyp003_terminal_verdict": failed.get("verdict")
        == "KILL_POST_MT5_VALIDATOR_BOM_AND_CLOCK_AXIS_CONTRACT_NO_ECONOMICS",
        "hyp003_terminal_raw": sha256_bytes(failed_raw) == HYP003_TERMINAL_ROW_SHA256,
        "hyp003_bound": validation.get("hyp003_terminal_row_sha256")
        == HYP003_TERMINAL_ROW_SHA256,
        "no_other_authority": all(validation.get(name) is False for name in FALSE_AUTHORITIES),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise ValueError(f"HYP004 comparator authority failed: {failed_checks}")
    return row, {
        "registry_sha256": sha256_bytes(registry_raw),
        "latest_row_sha256": sha256_bytes(raw),
        "hyp003_terminal_row_sha256": sha256_bytes(failed_raw),
        "comparator_sha256": self_sha,
    }


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
    start = re.search(r"<b>\s*(?:Orders|CÃ¡c\s+lá»‡nh\s+Ä‘áº·t)\s*</b>", html, re.I)
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
    header, spacer = cells.findall(rows[0]), cells.findall(rows[1])
    if (
        len(header) != 11
        or parse_colspans(header) != EXPECTED_COLSPANS
        or sum(EXPECTED_COLSPANS) != 13
        or not all(
            re.fullmatch(r"\s*<b>.*?</b>\s*", inner, re.I | re.S)
            for _, inner in header
        )
    ):
        return False
    return (
        len(spacer) == 1
        and parse_colspans(spacer) == [1]
        and re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""
    )


def utc_epoch(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def server_text(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y.%m.%d %H:%M:%S")


def event_identity_checks(
    signal: dict[str, str],
    event: dict[str, Any],
    next_row: dict[str, Any],
) -> dict[str, bool]:
    next_server = int(event["next_source_epoch"])
    expected_exact = event.get("executable_event") == 1
    return {
        "source_utc": int(signal["source_epoch"]) == utc_epoch(event["time_utc"]),
        "decision_utc": int(signal["decision_epoch"]) == utc_epoch(next_row["time_utc"]),
        "source_server_text": signal.get("source") == server_text(int(event["source_epoch"])),
        "decision_server_text": signal.get("decision") == server_text(next_server),
        "direction": signal.get("direction") == event.get("direction"),
        "exact_next": signal.get("exact_next") == ("true" if expected_exact else "false"),
    }


def geometry_contract_checks(
    direction: str,
    atr: float,
    entry: float,
    stop: float,
    target: float,
    tick_size: float = 0.01,
    digits: int = 2,
) -> dict[str, bool]:
    tolerance = 0.5 * tick_size + 1e-9
    if direction == "LONG":
        expected_stop = round(math.floor((entry - atr) / tick_size) * tick_size, digits)
        risk = entry - expected_stop
        expected_target = round(
            math.ceil((entry + 1.5 * risk) / tick_size) * tick_size,
            digits,
        )
        sided = stop < entry < target
    elif direction == "SHORT":
        expected_stop = round(math.ceil((entry + atr) / tick_size) * tick_size, digits)
        risk = expected_stop - entry
        expected_target = round(
            math.floor((entry - 1.5 * risk) / tick_size) * tick_size,
            digits,
        )
        sided = target < entry < stop
    else:
        return {"direction": False, "sided": False, "stop": False, "target": False}
    return {
        "direction": True,
        "sided": sided,
        "stop": abs(stop - expected_stop) <= tolerance,
        "target": abs(target - expected_target) <= tolerance,
    }


def analyze(captured: dict[str, bytes]) -> dict[str, Any]:
    manifest = decode_json(captured["run_manifest"], "run manifest")
    if captured["run_manifest"] != captured["run_manifest_duplicate"]:
        raise ValueError("run manifest duplicate differs")
    if captured["report"] != captured["report_duplicate"]:
        raise ValueError("report duplicate differs")
    if not (
        captured["config"]
        == captured["config_duplicate"]
        == captured["config_snapshot"]
    ):
        raise ValueError("config duplicates differ")
    if captured["overrides"] != captured["overrides_duplicate"]:
        raise ValueError("overrides duplicate differs")

    manifest_checks = {
        "hypothesis": manifest.get("hypothesis_id") == FAILED_HYPOTHESIS_ID,
        "ea": manifest.get("ea_name") == EA_NAME,
        "symbol": manifest.get("symbol") == "XAUUSD",
        "period": manifest.get("period") == "M15",
        "from": manifest.get("from") == "2005.01.01",
        "to": manifest.get("to") == "2023.01.01",
        "model": manifest.get("model") == 0,
        "execution": manifest.get("execution_mode") == 0,
        "delay": manifest.get("fixed_delay_ms") == 0,
        "overrides": manifest.get("overrides") == "InpAuditOnly=true",
        "telemetry": manifest.get("telemetry_profile") == "none"
        and manifest.get("telemetry_tier") == "off",
        "source": manifest.get("source_sha256") == SOURCE_SHA256,
        "ex5": manifest.get("ex5_sha256") == sha256_bytes(captured["ex5_snapshot"]),
        "tester_ex5": manifest.get("tester_ex5_sha256")
        == sha256_bytes(captured["ex5_snapshot"]),
        "config": manifest.get("config_sha256") == sha256_bytes(captured["config_snapshot"]),
        "report": manifest.get("report_sha256") == sha256_bytes(captured["report"]),
        "receipt": manifest.get("contract_receipt_sha256")
        == sha256_bytes(captured["hyp003_contract_receipt"]),
        "run_root": Path(str(manifest.get("local_run_dir", ""))).resolve()
        == RUN_DIR.resolve(),
        "snapshot_root": Path(str(manifest.get("snapshot_root", ""))).resolve()
        == (RUN_DIR / "snapshot").resolve(),
        "source_path": Path(str(manifest.get("source_snapshot", ""))).resolve()
        == STATIC_BINDINGS["source_snapshot"][0].resolve(),
        "ex5_path": Path(str(manifest.get("ex5_snapshot", ""))).resolve()
        == STATIC_BINDINGS["ex5_snapshot"][0].resolve(),
        "config_path": Path(str(manifest.get("config_snapshot", ""))).resolve()
        == STATIC_BINDINGS["config_snapshot"][0].resolve(),
        "report_path": Path(str(manifest.get("report_path", ""))).resolve()
        == STATIC_BINDINGS["report"][0].resolve(),
    }
    failed = [name for name, passed in manifest_checks.items() if not passed]
    if failed:
        raise ValueError(f"manifest mismatch: {failed}")
    gate = manifest.get("data_quality_gate", {})
    proof = gate.get("series_proof", {})
    if (
        float(gate.get("history_quality", 0.0)) <= 97.0
        or gate.get("actual_from", "9999.99.99") > "2005.01.01"
        or gate.get("actual_to", "0000.00.00") < "2023.01.01"
        or gate.get("coverage_class") != "FULL_2018_PLUS"
        or gate.get("journal_path") != "logs/tester_journal_delta.log"
        or gate.get("journal_sha256") != sha256_bytes(captured["journal"])
        or gate.get("journal_truncated") is not False
        or proof.get("m5_synchronized") != 1
        or proof.get("copytime_result") != 1
        or proof.get("copytime_last_error") != 0
        or proof.get("copytime_first_epoch") != proof.get("m5_first_epoch")
    ):
        raise ValueError("data-quality/history/series proof failed")

    summary = decode_json(captured["summary"], "zero-trade summary")
    if summary != {
        "schema_version": "alphafactory_zero_trade_collection_summary.v1",
        "analysis_mode": "data_acquisition_only",
        "authority": AUTHORITY,
        "n_trades": 0,
        "performance_metrics_authorized": False,
        "generated_at_utc": summary.get("generated_at_utc"),
    } or not isinstance(summary.get("generated_at_utc"), str):
        raise ValueError("zero-trade summary is invalid")
    try:
        html = captured["report"].decode("utf-16")
    except UnicodeDecodeError as exc:
        raise ValueError("report is not strict UTF-16") from exc
    if not orders_section_is_empty(html):
        raise ValueError("report Orders section is not exactly empty")

    journal = decode_strict_utf8(captured["journal"], "tester journal")
    forbidden = ("STBS_FATAL|", "STBS_ENTRY_REQUEST|", "STBS_CLOSE_REQUEST|", "STBS_DEAL|")
    found = [token for token in forbidden if token in journal]
    if found:
        raise ValueError(f"journal contains forbidden records: {found}")
    physical = parse_keyed_lines(journal, "STBS_SIGNAL|")
    summaries = parse_keyed_lines(journal, "STBS_SUMMARY|")
    if len(summaries) != 2 or summaries[0] != summaries[1]:
        raise ValueError("journal summary multiplicity/payload mismatch")
    expected_summary = {
        "record": "STBS_SUMMARY", "hypothesis": INNER_ID, "reason": "1",
        **{name: str(value) for name, value in EXPECTED_COUNTS.items()},
        "entries": "0", "entry_rejects": "0", "closes": "0", "failed": "false",
    }
    if summaries[0] != expected_summary:
        raise ValueError("journal summary semantic mismatch")

    groups: dict[int, list[dict[str, str]]] = {}
    for signal in physical:
        groups.setdefault(int(signal.get("source_epoch", "-1")), []).append(signal)
    actual: list[dict[str, str]] = []
    for epoch in sorted(groups):
        records = groups[epoch]
        if len(records) != 2 or records[0] != records[1]:
            raise ValueError(f"signal {epoch} duplicate multiplicity/payload mismatch")
        actual.append(records[0])
    if len(physical) != 1380 or len(actual) != EXPECTED_COUNTS["raw"]:
        raise ValueError("journal physical/unique population mismatch")

    oracle_text = decode_strict_utf8(captured["oracle"], "oracle")
    oracle_rows = [decode_json(line.encode("utf-8"), "oracle row") for line in oracle_text.splitlines() if line.strip()]
    if len(oracle_rows) != 29460:
        raise ValueError("oracle row population mismatch")
    by_server: dict[int, dict[str, Any]] = {}
    for row in oracle_rows:
        epoch = int(row["source_epoch"])
        if epoch in by_server:
            raise ValueError("oracle source_epoch is duplicated")
        by_server[epoch] = row
    events = sorted(
        (row for row in oracle_rows if row.get("raw_event") == 1),
        key=lambda row: int(row["source_epoch"]),
    )
    if len(events) != EXPECTED_COUNTS["raw"]:
        raise ValueError("oracle raw-event population mismatch")

    executable = gaps = long_count = short_count = atr_ready = geometry_ready = 0
    for index, (signal, event) in enumerate(zip(actual, events, strict=True)):
        next_server = int(event["next_source_epoch"])
        if next_server not in by_server:
            raise ValueError(f"event {index} next oracle row is absent")
        next_row = by_server[next_server]
        expected_exact = event.get("executable_event") == 1
        comparisons = event_identity_checks(signal, event, next_row)
        mismatches = [name for name, passed in comparisons.items() if not passed]
        if mismatches:
            raise ValueError(f"signal {index} mismatch: {mismatches}")
        if expected_exact:
            required = {
                "record", "source", "decision", "source_epoch", "decision_epoch",
                "direction", "exact_next", "atr_ready", "geometry_ready", "atr",
                "entry", "sl", "tp", "volume", "audit",
            }
            if set(signal) != required:
                raise ValueError(f"signal {index} executable schema mismatch")
            if signal["atr_ready"] != "true" or signal["geometry_ready"] != "true" or signal["audit"] != "true":
                raise ValueError(f"signal {index} readiness/audit mismatch")
            values = {name: float(signal[name]) for name in ("atr", "entry", "sl", "tp", "volume")}
            if not all(math.isfinite(value) and value > 0.0 for value in values.values()):
                raise ValueError(f"signal {index} geometry is invalid")
            geometry_checks = geometry_contract_checks(
                signal["direction"],
                values["atr"],
                values["entry"],
                values["sl"],
                values["tp"],
            )
            geometry_failures = [
                name for name, passed in geometry_checks.items() if not passed
            ]
            if geometry_failures:
                raise ValueError(
                    f"signal {index} inherited 1ATR/1.5R geometry mismatch: "
                    f"{geometry_failures}"
                )
            if signal["direction"] == "LONG":
                long_count += 1
            else:
                short_count += 1
            executable += 1
            atr_ready += 1
            geometry_ready += 1
        else:
            required = {
                "record", "source", "decision", "source_epoch", "decision_epoch",
                "direction", "exact_next", "consumed",
            }
            if set(signal) != required or signal.get("consumed") != "true":
                raise ValueError(f"signal {index} gap schema/consumption mismatch")
            gaps += 1
    counts = {
        "raw": len(actual), "executable": executable, "gaps": gaps,
        "long": long_count, "short": short_count,
        "atr_ready": atr_ready, "geometry_ready": geometry_ready,
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"reconciled counts mismatch: {counts}")

    start = decode_json(captured["hyp003_attempt_started"], "HYP003 attempt start")
    terminal = decode_json(captured["hyp003_attempt_terminal"], "HYP003 attempt terminal")
    if (
        start.get("hypothesis_id") != FAILED_HYPOTHESIS_ID
        or start.get("attempt_id") != "STBS003-MT5-AUDIT-001"
        or start.get("latest_row_sha256") != HYP003_SCREENED_ROW_SHA256
        or terminal.get("hypothesis_id") != FAILED_HYPOTHESIS_ID
        or terminal.get("attempt_id") != "STBS003-MT5-AUDIT-001"
        or terminal.get("status") != "FAILED"
        or terminal.get("error_type") != "JSONDecodeError"
        or "UTF-8 BOM" not in str(terminal.get("error", ""))
        or terminal.get("same_id_retry_authorized") is not False
    ):
        raise ValueError("HYP003 attempt chain semantics mismatch")
    stdout = decode_strict_utf8(captured["hyp003_alpha_stdout"], "Alpha stdout")
    stderr = decode_strict_utf8(captured["hyp003_alpha_stderr"], "Alpha stderr")
    required_stdout = (
        "SUCCESS: 33830 bytes", "log 0 errors", "Starting MT5", "Report ready!",
        "Zero-trade data collection verified", str(RUN_DIR.resolve()),
    )
    if stderr != "" or not all(token in stdout for token in required_stdout):
        raise ValueError("Alpha stdout/stderr semantics mismatch")
    return {
        "schema_version": "stbs004_existing_run_comparator_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_run_hypothesis_id": FAILED_HYPOTHESIS_ID,
        "verdict": VERDICT,
        "history_quality": float(gate["history_quality"]),
        "actual_from": gate["actual_from"],
        "actual_to": gate["actual_to"],
        "journal_physical_records": len(physical),
        "journal_duplicate_multiplicity": 2,
        **{f"{name}_events": value for name, value in counts.items()},
        "source_utc_mismatches": 0,
        "decision_next_utc_mismatches": 0,
        "source_server_text_mismatches": 0,
        "decision_server_text_mismatches": 0,
        "direction_mismatches": 0,
        "exact_next_mismatches": 0,
        "orders_section_empty": True,
        "trades_executed": 0,
        "performance_metrics_authorized": False,
        "economics_evaluated": False,
        "exact_position_sizing_proven": False,
        "volume_readiness_only": True,
        "compile_zero_warning_claim_authorized": False,
    }


def execute(registry: Path) -> dict[str, Any]:
    row, authority = validate_authority(registry.resolve())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    started_path = OUTPUT_DIR / "attempt_started.json"
    terminal_path = OUTPUT_DIR / "attempt_terminal.json"
    write_exclusive(
        started_path,
        json_bytes({
            "schema_version": "stbs004_comparator_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "same_id_retry_authorized": False,
            **authority,
        }),
    )
    try:
        captured: dict[str, bytes] = {}
        bindings: list[dict[str, str]] = []
        for label, (path, expected) in STATIC_BINDINGS.items():
            raw = path.read_bytes()
            actual = sha256_bytes(raw)
            if actual != expected:
                raise ValueError(f"{label} changed: expected {expected}, got {actual}")
            captured[label] = raw
            bindings.append({"label": label, "path": path.resolve().as_posix(), "sha256": actual})
        validation = row["validation"]
        dynamic_bindings = (
            ("prereg", PREREG_PATH.resolve(), PREREG_SHA256),
            ("reviewed_test", TEST_PATH.resolve(), TEST_SHA256),
            (
                "independent_review",
                REVIEW_PATH.resolve(),
                str(validation["independent_review_sha256"]),
            ),
        )
        dynamic_paths = [path for _, path, _ in dynamic_bindings]
        static_paths = {path.resolve() for path, _ in STATIC_BINDINGS.values()}
        if (
            len(dynamic_paths) != len(set(dynamic_paths))
            or any(path in static_paths for path in dynamic_paths)
            or any(ROOT.resolve() not in path.parents for path in dynamic_paths)
        ):
            raise ValueError("dynamic comparator package paths are not unique/disjoint/rooted")
        for label, path, expected in dynamic_bindings:
            raw = path.read_bytes()
            actual = sha256_bytes(raw)
            if actual != expected:
                raise ValueError(f"{label} changed")
            captured[label] = raw
            bindings.append({"label": label, "path": path.as_posix(), "sha256": actual})
        first = analyze(captured)
        second = analyze(captured)
        first_raw = json_bytes(first)
        if first_raw != json_bytes(second):
            raise ValueError("same-capture deterministic replay mismatch")
        report_path = OUTPUT_DIR / "stbs004_existing_run_comparator_report.json"
        write_exclusive(report_path, first_raw)
        receipt = {
            "schema_version": "stbs004_existing_run_comparator_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "verdict": VERDICT,
            "authority": authority,
            "attempt_started_sha256": sha256_bytes(started_path.read_bytes()),
            "report_sha256": sha256_bytes(first_raw),
            "bindings": bindings,
            "deterministic_replay": "PASS",
            "trades_executed": 0,
            "performance_metrics_authorized": False,
            "economics_evaluated": False,
            "same_id_retry_authorized": False,
            "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        receipt_path = OUTPUT_DIR / "stbs004_existing_run_comparator_receipt.json"
        write_exclusive(receipt_path, json_bytes(receipt))
        write_exclusive(
            terminal_path,
            json_bytes({
                "schema_version": "stbs004_comparator_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "status": "COMPLETE",
                "verdict": VERDICT,
                "attempt_started_sha256": receipt["attempt_started_sha256"],
                "report_sha256": receipt["report_sha256"],
                "receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
                "same_id_retry_authorized": False,
                "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }),
        )
        return {
            "report": report_path.as_posix(),
            "report_sha256": receipt["report_sha256"],
            "receipt": receipt_path.as_posix(),
            "receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
            "terminal": terminal_path.as_posix(),
            "terminal_sha256": sha256_bytes(terminal_path.read_bytes()),
            "verdict": VERDICT,
        }
    except BaseException as exc:
        if not terminal_path.exists():
            write_exclusive(
                terminal_path,
                json_bytes({
                    "schema_version": "stbs004_comparator_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "status": "FAILED",
                    "verdict": "STBS004_COMPARATOR_FAILED_ATTEMPT_CONSUMED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "same_id_retry_authorized": False,
                    "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }),
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    print(json.dumps(execute(args.registry), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
