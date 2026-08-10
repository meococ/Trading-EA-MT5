#!/usr/bin/env python3
"""Seal the sole ST003 MT5 audit CSV and tester journal into its AlphaFactory run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
TARGET_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
AUDIT_RUN_ID = "ST003-MT5-PARITY-001"
ATTEMPT_ID = "ST008-ARTIFACT-COLLECT-001"
MT5_ATTEMPT_ID = "ST008-MT5-001"
COMMON_FILE_NAME = "ST003_MQL5_PARITY_001.csv"
LOCAL_AUDIT_NAME = "ST003_MQL5_PARITY_001.csv"
LOCAL_JOURNAL_NAME = "ST003_MT5_PARITY_001_tester_journal.log"
LOCAL_COMPILE_LOG_NAME = "ST004_MetaEditor_compile.log"
MQL_SOURCE_SHA256 = "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
ALPHA_PS1_SHA256 = "68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8"
EXACT_OVERRIDES = "InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpParityFileName=ST003_MQL5_PARITY_001.csv"
MQL_COLUMNS = [
    "schema_version", "hypothesis_id", "audit_run_id", "source_epoch", "time_server",
    "atr10", "final_upper", "final_lower", "supertrend", "prior_state", "state",
    "raw_event", "next_source_epoch", "exact_next", "executable_event", "direction",
]
SUMMARY = re.compile(
    r"ST003_SUMMARY\|run=ST003-MT5-PARITY-001\|reason=\d+\|rows=29460\|raw=690\|"
    r"executable=683\|gaps=7\|long=339\|short=344\|failed=false"
)
SERIES_PROOF = re.compile(
    r"DATA_EPOCH_D0_SERIES_PROOF symbol=(?P<symbol>\S+) "
    r"m5_synchronized=(?P<m5_synchronized>\d+) m5_first_epoch=(?P<m5_first_epoch>\d+) "
    r"m5_terminal_first_epoch=(?P<m5_terminal_first_epoch>\d+) "
    r"m1_server_first_epoch=(?P<m1_server_first_epoch>\d+) "
    r"m1_terminal_first_epoch=(?P<m1_terminal_first_epoch>\d+) m5_bars=(?P<m5_bars>\d+) "
    r"terminal_maxbars=(?P<terminal_maxbars>\d+) copytime_from_epoch=(?P<copytime_from_epoch>\d+) "
    r"copytime_count=(?P<copytime_count>\d+) copytime_result=(?P<copytime_result>-?\d+) "
    r"copytime_first_epoch=(?P<copytime_first_epoch>\d+) copytime_last_error=(?P<copytime_last_error>\d+)"
)


ROOT = Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO UTC string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} lacks timezone")
    return parsed.astimezone(timezone.utc)


def decode_text_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="ignore")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be", errors="ignore")
    return raw.decode("utf-8-sig", errors="ignore")


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def validate_registry(registry_path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == AUTHORITY_HYPOTHESIS_ID:
            matches.append((raw, row))
    if not matches:
        raise ValueError("missing frozen HYP008 MT5 authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "screened": row.get("state") == "screened",
        "verdict": row.get("verdict") == "FROZEN_ST008_MT5_PARITY_RUN_AUTHORIZED",
        "target": validation.get("parity_target_hypothesis_id") == TARGET_HYPOTHESIS_ID,
        "run": validation.get("mt5_parity_run_authorized") is True,
        "attempt": validation.get("mt5_parity_attempt_id") == MT5_ATTEMPT_ID,
        "limit": validation.get("mt5_parity_attempt_limit") == 1,
        "unconsumed": metrics.get("mt5_parity_attempts_consumed") == 0,
        "collect": validation.get("artifact_collection_authorized") is True,
        "collect_attempt": validation.get("artifact_collection_attempt_id") == ATTEMPT_ID,
        "collect_limit": validation.get("artifact_collection_attempt_limit") == 1,
        "collect_unconsumed": metrics.get("artifact_collection_attempts_consumed") == 0,
        "collector": validation.get("reviewed_artifact_collector_sha256") == sha256_file(Path(__file__).resolve()),
        "mql": validation.get("reviewed_mql_source_sha256") == MQL_SOURCE_SHA256,
        "run_compile": validation.get("run_compile_authorized") is True,
        "no_standalone_compile": validation.get("static_compile_pass") is False,
        "alpha": validation.get("reviewed_alpha_ps1_sha256") == ALPHA_PS1_SHA256,
        "alpha_file": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1") == ALPHA_PS1_SHA256,
        "common": validation.get("frozen_common_file_name") == COMMON_FILE_NAME,
        "no_outcomes": validation.get("performance_metrics_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP008 artifact authority failed: {failed}")
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> Path:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("artifact collection attempt already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = output_dir / "attempt_started.json"
    payload = {
        "schema_version": "st005_artifact_collection_attempt_started.v1",
        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "target_hypothesis_id": TARGET_HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "collector_sha256": sha256_file(Path(__file__).resolve()),
        "process_id": os.getpid(),
        **authority,
    }
    write_exclusive(marker, json_bytes(payload))
    return marker


def validate_run_manifest(run_dir: Path) -> tuple[dict[str, Any], datetime, datetime]:
    manifest_path = run_dir / "run_manifest.json"
    manifest = load_json(manifest_path)
    exact = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": "EA_SupertrendStateFlip",
        "symbol": "XAUUSD",
        "period": "H1",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": EXACT_OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "source_sha256": MQL_SOURCE_SHA256,
    }
    wrong = [key for key, expected in exact.items() if manifest.get(key) != expected]
    if wrong or manifest.get("required_sidecars") != []:
        raise ValueError(f"AlphaFactory run manifest mismatch: {wrong}")
    if Path(str(manifest.get("local_run_dir", ""))).resolve() != run_dir:
        raise ValueError("run manifest local_run_dir mismatch")
    data_contract = manifest.get("data_quality_contract", {})
    data_gate = manifest.get("data_quality_gate", {})
    if (
        data_contract.get("schema_version") != "alphafactory_data_quality_contract.v1"
        or data_contract.get("symbol") != "XAUUSD"
        or data_contract.get("requested_from") != "2005.01.01"
        or data_contract.get("requested_to") != "2023.01.01"
        or data_contract.get("coverage_mode") != "fixed_window"
        or data_contract.get("require_tester_journal_bounds") is not True
        or data_contract.get("history_quality_threshold") != 97
        or data_gate.get("history_quality", 0) <= 97
    ):
        raise ValueError("AlphaFactory data-quality contract/gate mismatch")
    start = parse_utc(manifest.get("artifact_collection_not_before_utc"), "run start")
    end = parse_utc(manifest.get("generated_at_utc"), "run end")
    if end <= start or end - start > timedelta(hours=2):
        raise ValueError("implausible AlphaFactory run interval")
    return manifest, start, end


def validate_compile_evidence(
    manifest: dict[str, Any], run_dir: Path, start: datetime, end: datetime
) -> tuple[Path, bytes, Path]:
    canonical_source = ROOT / "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5"
    canonical_ex5 = canonical_source.with_suffix(".ex5")
    canonical_log = canonical_source.with_suffix(".log")
    source_snapshot = run_dir / "snapshot/source/EA_SupertrendStateFlip.mq5"
    ex5_snapshot = run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5"
    expected_paths = {
        "main_file": canonical_source,
        "compiled_ex5_file": canonical_ex5,
        "source_snapshot": source_snapshot,
        "ex5_snapshot": ex5_snapshot,
    }
    wrong_paths = [
        key for key, expected in expected_paths.items()
        if Path(str(manifest.get(key, ""))).resolve() != expected.resolve()
    ]
    if wrong_paths:
        raise ValueError(f"AlphaFactory compile/snapshot path mismatch: {wrong_paths}")
    for path in (canonical_source, canonical_ex5, canonical_log, source_snapshot, ex5_snapshot):
        if not path.is_file():
            raise ValueError(f"required compile evidence is absent: {path}")
    if sha256_file(canonical_source) != MQL_SOURCE_SHA256 or sha256_file(source_snapshot) != MQL_SOURCE_SHA256:
        raise ValueError("canonical/run-snapshot MQL source hash mismatch")
    ex5_sha = sha256_file(ex5_snapshot)
    if (
        sha256_file(canonical_ex5) != ex5_sha
        or manifest.get("ex5_sha256") != ex5_sha
        or manifest.get("tester_ex5_sha256") != ex5_sha
    ):
        raise ValueError("canonical/snapshotted/executed EX5 hash mismatch")
    modified = datetime.fromtimestamp(canonical_log.stat().st_mtime, tz=timezone.utc)
    if modified < start - timedelta(minutes=15) or modified > end + timedelta(seconds=5):
        raise ValueError("MetaEditor compile log is not contemporaneous with the AlphaFactory run")
    raw = canonical_log.read_bytes()
    text = decode_text_bytes(raw)
    if (
        re.search(r"\b0\s+errors?\b", text, re.IGNORECASE) is None
        or re.search(r"\b0\s+warnings?\b", text, re.IGNORECASE) is None
    ):
        raise ValueError("MetaEditor compile log does not prove 0 errors / 0 warnings")
    if sha256_file(canonical_log) != hashlib.sha256(raw).hexdigest().upper():
        raise ValueError("MetaEditor compile log changed during collection")
    return canonical_log, raw, ex5_snapshot


def validate_data_quality_journal(manifest: dict[str, Any], run_dir: Path) -> Path:
    binding = manifest.get("data_quality_journal_delta", {})
    if (
        binding.get("path") != "logs/tester_journal_delta.log"
        or binding.get("truncated") is not False
        or int(binding.get("bytes_read", 0)) <= 0
        or int(binding.get("files_read", 0)) <= 0
    ):
        raise ValueError("run manifest data-quality journal binding mismatch")
    path = run_dir / "logs/tester_journal_delta.log"
    if not path.is_file() or binding.get("sha256") != sha256_file(path):
        raise ValueError("run-local data-quality journal hash mismatch")
    text = decode_text_bytes(path.read_bytes())
    proofs = [match.groupdict() for match in SERIES_PROOF.finditer(text)]
    distinct = {json.dumps(item, sort_keys=True) for item in proofs}
    if not proofs or len(distinct) != 1:
        raise ValueError("run-local journal lacks one distinct D0 series proof")
    proof = proofs[0]
    numeric = {key: int(value) for key, value in proof.items() if key != "symbol"}
    gate = manifest.get("data_quality_gate", {})
    contract = manifest.get("data_quality_contract", {})
    gate_proof = gate.get("series_proof", {})
    if (
        proof["symbol"] != "XAUUSD"
        or gate.get("contract") != contract
        or gate.get("history_quality", 0) <= 97
        or gate.get("coverage_class") != "FULL_2018_PLUS"
        or gate.get("journal_path") != binding.get("path")
        or gate.get("journal_sha256") != binding.get("sha256")
        or gate.get("journal_bytes_read") != binding.get("bytes_read")
        or gate.get("journal_files_read") != binding.get("files_read")
        or gate.get("journal_truncated") is not False
        or int(gate.get("exact_match_count", 0)) < 1
        or gate.get("distinct_range_count") != 1
        or gate_proof.get("symbol") != "XAUUSD"
        or any(gate_proof.get(key) != value for key, value in numeric.items())
        or numeric["m5_synchronized"] != 1
        or numeric["m5_first_epoch"] <= 0
        or numeric["m5_first_epoch"] != numeric["m5_terminal_first_epoch"]
        or numeric["m5_first_epoch"] != numeric["copytime_from_epoch"]
        or numeric["m5_first_epoch"] != numeric["copytime_first_epoch"]
        or numeric["m1_server_first_epoch"] != numeric["m1_terminal_first_epoch"]
        or numeric["m1_server_first_epoch"] > numeric["m5_first_epoch"]
        or numeric["m5_bars"] <= 0
        or numeric["terminal_maxbars"] <= 0
        or numeric["copytime_count"] != 1
        or numeric["copytime_result"] != 1
        or numeric["copytime_last_error"] != 0
    ):
        raise ValueError("run-local D0 proof and AlphaFactory data-quality gate do not reconcile")
    return path


def validate_contract_receipt(path: Path, manifest: dict[str, Any]) -> None:
    receipt = load_json(path)
    binding = receipt.get("binding", {})
    exact = {
        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": "EA_SupertrendStateFlip",
        "symbol": "XAUUSD",
        "period": "H1",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": EXACT_OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "indicator_dependencies": [],
    }
    if (
        receipt.get("schema_version") != "alphafactory_execution_receipt.v1"
        or receipt.get("authority") != "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
        or receipt.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or any(binding.get(key) != value for key, value in exact.items())
        or manifest.get("contract_receipt_sha256") != sha256_file(path)
    ):
        raise ValueError("AlphaFactory collection contract receipt mismatch")
    quality = binding.get("data_quality_contract", {})
    threshold = quality.get("history_quality", {})
    if (
        threshold != {"operator": "gt", "value": 97.0}
        or quality.get("coverage_mode") != "fixed_window"
        or quality.get("requested_from") != "2005.01.01"
        or quality.get("requested_to") != "2023.01.01"
        or quality.get("require_tester_journal_bounds") is not True
    ):
        raise ValueError("collection receipt data-quality contract mismatch")


def validate_mt5_run_chain(run_dir: Path, contract_receipt: Path) -> tuple[Path, Path]:
    evidence = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001"
    receipt_path = evidence / "mt5_run_receipt.json"
    terminal_path = evidence / "attempt_terminal.json"
    receipt = load_json(receipt_path)
    terminal = load_json(terminal_path)
    if (
        receipt.get("schema_version") != "st005_mt5_run_receipt.v1"
        or receipt.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or receipt.get("attempt_id") != MT5_ATTEMPT_ID
        or receipt.get("audit_run_id") != AUDIT_RUN_ID
        or receipt.get("verdict") != "MT5_ZERO_TRADE_COLLECTION_COMPLETE_PENDING_PARITY"
        or Path(str(receipt.get("alpha_run_dir", ""))).resolve() != run_dir
        or receipt.get("orders_executed") != 0
        or receipt.get("trades_executed") != 0
        or receipt.get("economics_evaluated") is not False
    ):
        raise ValueError("HYP008 MT5 run receipt mismatch")
    bindings = receipt.get("bindings", {})
    if (
        bindings.get("run_manifest", {}).get("sha256") != sha256_file(run_dir / "run_manifest.json")
        or bindings.get("contract_receipt", {}).get("sha256") != sha256_file(contract_receipt)
        or bindings.get("alpha_ps1", {}).get("sha256") != ALPHA_PS1_SHA256
        or terminal.get("schema_version") != "st005_mt5_run_terminal.v1"
        or terminal.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or terminal.get("attempt_id") != MT5_ATTEMPT_ID
        or terminal.get("status") != "COMPLETE"
        or terminal.get("verdict") != receipt.get("verdict")
        or terminal.get("receipt_sha256") != sha256_file(receipt_path)
        or terminal.get("same_id_retry_authorized") is not False
    ):
        raise ValueError("HYP008 MT5 run chain binding mismatch")
    return receipt_path, terminal_path


def validate_common_csv(path: Path, start: datetime, end: datetime) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("frozen FILE_COMMON audit CSV is absent")
    stat = path.stat()
    created = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    tolerance = timedelta(seconds=5)
    if created < start - tolerance or created > end + tolerance or modified < start - tolerance or modified > end + tolerance:
        raise ValueError("FILE_COMMON audit timestamps fall outside the AlphaFactory run interval")
    with path.open("r", encoding="ascii", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MQL_COLUMNS:
            raise ValueError("FILE_COMMON audit schema mismatch")
        rows = list(reader)
    if len(rows) != 29460:
        raise ValueError(f"FILE_COMMON audit row count mismatch: {len(rows)}")
    epochs = [int(row["source_epoch"]) for row in rows]
    if epochs != sorted(set(epochs)):
        raise ValueError("FILE_COMMON audit epochs are not unique/increasing")
    if any(
        row["schema_version"] != "st003_mql5_parity.v1"
        or row["hypothesis_id"] != TARGET_HYPOTHESIS_ID
        or row["audit_run_id"] != AUDIT_RUN_ID
        for row in rows
    ):
        raise ValueError("FILE_COMMON audit identity mismatch")
    raw = sum(int(row["raw_event"]) for row in rows)
    executable = sum(int(row["executable_event"]) for row in rows)
    gaps = sum(int(row["raw_event"] == "1" and row["exact_next"] == "0") for row in rows)
    longs = sum(int(row["executable_event"] == "1" and row["direction"] == "LONG") for row in rows)
    shorts = sum(int(row["executable_event"] == "1" and row["direction"] == "SHORT") for row in rows)
    if (raw, executable, gaps, longs, shorts) != (690, 683, 7, 339, 344):
        raise ValueError("FILE_COMMON audit frozen counters mismatch")
    return {
        "rows": len(rows), "raw_events": raw, "executable_events": executable,
        "gap_rejected_events": gaps, "long_events": longs, "short_events": shorts,
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
        "modified_at_utc": modified.isoformat().replace("+00:00", "Z"),
    }


def locate_tester_journal(tester_root: Path, start: datetime, end: datetime) -> tuple[Path, bytes]:
    candidates: list[tuple[Path, bytes]] = []
    tolerance = timedelta(minutes=5)
    for path in tester_root.rglob("*.log"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified < start - tolerance or modified > end + tolerance:
            continue
        raw = path.read_bytes()
        text = decode_text_bytes(raw)
        target = re.findall(r"ST003_SUMMARY\|run=ST003-MT5-PARITY-001\|[^\r\n]*", text)
        if target:
            if len(target) != 1 or len(SUMMARY.findall(text)) != 1 or "ST003_FATAL" in text:
                raise ValueError(f"tester journal has invalid ST003 evidence: {path}")
            candidates.append((path, raw))
    if len(candidates) != 1:
        raise ValueError(f"expected one tester journal with the frozen summary, found {len(candidates)}")
    return candidates[0]


def execute(run_dir: Path, registry_path: Path, contract_receipt: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    registry_path = registry_path.resolve()
    contract_receipt = contract_receipt.resolve()
    output_dir = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-ARTIFACT-COLLECT-001"
    authority_row, authority = validate_registry(registry_path)
    marker = claim_attempt(output_dir, authority)
    manifest, start, end = validate_run_manifest(run_dir)
    validate_contract_receipt(contract_receipt, manifest)
    if authority_row.get("validation", {}).get("contract_receipt_sha256") != sha256_file(contract_receipt):
        raise ValueError("HYP008 authority does not bind the collection contract receipt")
    mt5_receipt, mt5_terminal = validate_mt5_run_chain(run_dir, contract_receipt)
    canonical_compile_log, compile_log_bytes, ex5_snapshot = validate_compile_evidence(
        manifest, run_dir, start, end
    )
    data_quality_journal = validate_data_quality_journal(manifest, run_dir)
    storage = manifest.get("mt5_storage_contract", {})
    common_root = Path(str(storage.get("common_files_root", ""))).resolve()
    tester_root = Path(str(storage.get("tester_root", ""))).resolve()
    if not common_root.is_dir() or not tester_root.is_dir():
        raise ValueError("run manifest MT5 storage roots are invalid")
    common_path = common_root / COMMON_FILE_NAME
    counters = validate_common_csv(common_path, start, end)
    journal_path, journal_bytes = locate_tester_journal(tester_root, start, end)
    audit_bytes = common_path.read_bytes()
    audit_sha = hashlib.sha256(audit_bytes).hexdigest().upper()
    journal_sha = hashlib.sha256(journal_bytes).hexdigest().upper()
    if sha256_file(common_path) != audit_sha or sha256_file(journal_path) != journal_sha:
        raise ValueError("MT5 source artifact changed during collection")
    local_logs = run_dir / "logs"
    local_audit = local_logs / LOCAL_AUDIT_NAME
    local_journal = local_logs / LOCAL_JOURNAL_NAME
    local_compile_log = run_dir / "build" / LOCAL_COMPILE_LOG_NAME
    if local_audit.exists() or local_journal.exists() or local_compile_log.exists():
        raise ValueError("canonical run-local ST003 artifacts already exist")
    write_exclusive(local_audit, audit_bytes)
    write_exclusive(local_journal, journal_bytes)
    write_exclusive(local_compile_log, compile_log_bytes)
    if (
        sha256_file(canonical_compile_log) != sha256_file(local_compile_log)
        or sha256_file(ex5_snapshot) != manifest.get("ex5_sha256")
    ):
        raise ValueError("compile evidence changed during run-local sealing")
    completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema_version": "st005_mt5_artifact_collection_receipt.v1",
        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "target_hypothesis_id": TARGET_HYPOTHESIS_ID,
        "audit_run_id": AUDIT_RUN_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": completed,
        "run_interval_utc": {"start": start.isoformat().replace("+00:00", "Z"), "end": end.isoformat().replace("+00:00", "Z")},
        "bindings": {
            "collector": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "registry": {"path": registry_path.as_posix(), **authority},
            "authority_prereg": {"path": authority_row.get("prereg_path"), "sha256": authority_row.get("prereg_sha256")},
            "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
            "run_manifest": {"path": (run_dir / "run_manifest.json").as_posix(), "sha256": sha256_file(run_dir / "run_manifest.json")},
            "contract_receipt": {"path": contract_receipt.as_posix(), "sha256": sha256_file(contract_receipt)},
            "alpha_ps1": {"path": (ROOT / "02. AlphaFactory/alpha.ps1").as_posix(), "sha256": sha256_file(ROOT / "02. AlphaFactory/alpha.ps1")},
            "mt5_run_receipt": {"path": mt5_receipt.as_posix(), "sha256": sha256_file(mt5_receipt)},
            "mt5_run_terminal": {"path": mt5_terminal.as_posix(), "sha256": sha256_file(mt5_terminal)},
            "source_common_audit": {"path": common_path.as_posix(), "sha256": audit_sha},
            "run_local_audit": {"path": local_audit.as_posix(), "sha256": sha256_file(local_audit)},
            "source_tester_journal": {"path": journal_path.as_posix(), "sha256": journal_sha},
            "run_local_tester_journal": {"path": local_journal.as_posix(), "sha256": sha256_file(local_journal)},
            "data_quality_journal_delta": {"path": data_quality_journal.as_posix(), "sha256": sha256_file(data_quality_journal)},
            "source_compile_log": {"path": canonical_compile_log.as_posix(), "sha256": sha256_file(canonical_compile_log)},
            "run_local_compile_log": {"path": local_compile_log.as_posix(), "sha256": sha256_file(local_compile_log)},
            "run_ex5_snapshot": {"path": ex5_snapshot.as_posix(), "sha256": sha256_file(ex5_snapshot)},
        },
        "counters": counters,
        "verdict": "MT5_AUDIT_ARTIFACT_COLLECTION_PASS",
        "economics_evaluated": False,
        "orders_executed": 0,
        "trades_executed": 0,
    }
    receipt_bytes = json_bytes(receipt)
    receipt_path = output_dir / "artifact_collection_receipt.json"
    write_exclusive(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "st005_mt5_artifact_collection_terminal.v1",
        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": completed,
        "status": "COMPLETE",
        "verdict": receipt["verdict"],
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(output_dir / "attempt_terminal.json", json_bytes(terminal))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--contract-receipt", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    receipt = execute(args.run_dir, args.registry, args.contract_receipt)
    print(json_bytes({"verdict": receipt["verdict"], "counters": receipt["counters"]}).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
