#!/usr/bin/env python3
"""Recover and seal the completed HYP008 MT5 parity artifacts without rerunning MT5."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-009"
RUN_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
TARGET_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
ATTEMPT_ID = "ST009-ARTIFACT-COLLECT-001"
RUN_DIR = ROOT / "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257"
OUTPUT_DIR = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-009/ST009-ARTIFACT-COLLECT-001"
CONTRACT_RECEIPT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/preflight/HYP-ST-XAUUSD-H1-008/V3/contract_receipt.control.json"
COMMON_FILE = Path.home() / "AppData/Roaming/MetaQuotes/Terminal/Common/Files/ST003_MQL5_PARITY_001.csv"
CANONICAL_COMPILE_LOG = ROOT / "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.log"

EXPECTED = {
    "run_manifest": "AC9CA6A3878E6545A86FD743FE3918F3EE3D913024676F48B54C62DEC771B9F8",
    "report": "178901C855F050FA18217762509F791870D8CB2A2903CEF08C0436E8A7EE79EB",
    "journal_delta": "3F441837BBF26A89EFFF310659CFB973824C76D3D903B887B98954E322453C2F",
    "source": "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF",
    "ex5": "DCE8F2EB93F9FCF6BF827151F576664D21316C5693E76B3886FCC289C499710C",
    "compile_log": "B766F5FBC26B8BAD7679E6D736E588EFA8462DFA1CDBB3E7D1F23550AD9E170D",
    "common_csv": "C404DDE7922C757CC0B1B3D7E3AF8F48C7A4E0F219716314A138D1AC4AB61DD3",
    "mt5_receipt": "C10CA25EB8FE6264DD9F1F12EAE0FA44CC53D69C29823D2C694330BCA2AF7CCA",
    "mt5_terminal": "991AFEB2C0C64A3CD9F0626CCFB56A1EA40A82D698546CA95E66EBB8C0682C5E",
}
FROZEN_SUMMARY = (
    "ST003_SUMMARY|run=ST003-MT5-PARITY-001|reason=1|rows=29460|raw=690|"
    "executable=683|gaps=7|long=339|short=344|failed=false"
)
SUMMARY_RE = re.compile(r"ST003_SUMMARY\|run=ST003-MT5-PARITY-001\|[^\r\n]*")
BASE_COLLECTOR_SHA256 = "9B406B3A964623C6C3C108A29EDC256AAC9D87087B3462D85AD38E2358C8BDFD"


def load_base():
    path = Path(__file__).resolve().with_name("collect_st004_mt5_artifacts.py")
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != BASE_COLLECTOR_SHA256:
        raise ValueError("frozen HYP008 collector dependency hash drift")
    spec = importlib.util.spec_from_file_location("st008_collector_dependency", path)
    if not spec or not spec.loader:
        raise ValueError("cannot load frozen HYP008 collector dependency")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256_file(path) != expected:
        raise ValueError(f"{label} hash binding mismatch")


def validate_registry(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == AUTHORITY_HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing HYP009 recovery authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_ST009_EXISTING_RUN_RECOVERY_AUTHORIZED",
        "recover": validation.get("artifact_collection_authorized") is True,
        "attempt": validation.get("artifact_collection_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("artifact_collection_attempt_limit") == 1,
        "unconsumed": metrics.get("artifact_collection_attempts_consumed") == 0,
        "collector": validation.get("reviewed_recovery_collector_sha256") == sha256_file(Path(__file__).resolve()),
        "no_mt5": validation.get("mt5_authorized") is False and validation.get("mt5_parity_run_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_outcomes": validation.get("performance_metrics_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
        "no_compile": validation.get("compile_authorized") is False
        and validation.get("run_compile_authorized") is False
        and validation.get("mql5_compile_authorized") is False
        and validation.get("standalone_compile_authorized") is False,
        "no_trade_api": validation.get("trade_api_authorized") is False,
        "no_outcome_prices": validation.get("outcome_prices_authorized") is False and validation.get("post_event_ohlc_authorized") is False,
        "no_research": validation.get("optimization_authorized") is False
        and validation.get("validation_authorized") is False
        and validation.get("holdout_authorized") is False
        and validation.get("research_validation_access_authorized") is False
        and validation.get("research_holdout_access_authorized") is False,
        "no_promotion": validation.get("promotion_eligible") is False and validation.get("paper_trading_authorized") is False and validation.get("market_edge_claim_authorized") is False,
        "no_retry_mutation": validation.get("same_id_retry_authorized") is False
        and validation.get("registry_mutation_allowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP009 recovery authority failed: {failed}")
    return row, {
        "registry_sha256": sha256_file(path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def claim(authority: dict[str, str]) -> Path:
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError("HYP009 recovery attempt already exists")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    marker = OUTPUT_DIR / "attempt_started.json"
    write_exclusive(
        marker,
        json_bytes(
            {
                "schema_version": "st009_artifact_recovery_started.v1",
                "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
                "run_hypothesis_id": RUN_HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "collector_sha256": sha256_file(Path(__file__).resolve()),
                "process_id": os.getpid(),
                **authority,
            }
        ),
    )
    return marker


def validate_identical_current_summaries(journal: Path) -> tuple[bytes, int]:
    raw = journal.read_bytes()
    text = BASE.decode_text_bytes(raw)
    if "ST003_FATAL" in text:
        raise ValueError("manifest-bound HYP008 journal delta contains ST003_FATAL")
    summaries = SUMMARY_RE.findall(text)
    if not summaries or len(set(summaries)) != 1 or summaries[0] != FROZEN_SUMMARY:
        raise ValueError("run-local ST003 summaries are missing, distinct or not frozen")
    return (FROZEN_SUMMARY + "\n").encode("ascii"), len(summaries)


def snapshot_common_csv_once(path: Path, start: datetime, end: datetime) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    before = path.stat()
    raw_bytes = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("common CSV changed during the single recovery read")
    if len(raw_bytes) != 5_791_799 or hashlib.sha256(raw_bytes).hexdigest().upper() != EXPECTED["common_csv"]:
        raise ValueError("frozen common CSV bytes mismatch")
    created = datetime.fromtimestamp(before.st_ctime, tz=timezone.utc)
    modified = datetime.fromtimestamp(before.st_mtime, tz=timezone.utc)
    tolerance = timedelta(seconds=5)
    if created < start - tolerance or created > end + tolerance or modified < start - tolerance or modified > end + tolerance:
        raise ValueError("common CSV timestamps fall outside the HYP008 run interval")
    reader = csv.DictReader(io.StringIO(raw_bytes.decode("ascii"), newline=""))
    if reader.fieldnames != BASE.MQL_COLUMNS:
        raise ValueError("common CSV schema mismatch")
    rows = list(reader)
    if len(rows) != 29460:
        raise ValueError(f"common CSV row count mismatch: {len(rows)}")
    epochs = [int(row["source_epoch"]) for row in rows]
    if epochs != sorted(set(epochs)) or epochs[0] != 1514883600 or epochs[-1] != 1672437600:
        raise ValueError("common CSV source epoch coverage mismatch")
    if int(rows[-1]["next_source_epoch"]) != 1672441200:
        raise ValueError("common CSV final next epoch mismatch")
    if any(
        row["schema_version"] != "st003_mql5_parity.v1"
        or row["hypothesis_id"] != TARGET_HYPOTHESIS_ID
        or row["audit_run_id"] != "ST003-MT5-PARITY-001"
        for row in rows
    ):
        raise ValueError("common CSV identity mismatch")
    raw_events = sum(int(row["raw_event"]) for row in rows)
    executable = sum(int(row["executable_event"]) for row in rows)
    gaps = sum(int(row["raw_event"] == "1" and row["exact_next"] == "0") for row in rows)
    longs = sum(int(row["executable_event"] == "1" and row["direction"] == "LONG") for row in rows)
    shorts = sum(int(row["executable_event"] == "1" and row["direction"] == "SHORT") for row in rows)
    if (raw_events, executable, gaps, longs, shorts) != (690, 683, 7, 339, 344):
        raise ValueError("common CSV frozen counters mismatch")
    counters = {
        "rows": len(rows), "raw_events": raw_events, "executable_events": executable,
        "gap_rejected_events": gaps, "long_events": longs, "short_events": shorts,
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
        "modified_at_utc": modified.isoformat().replace("+00:00", "Z"),
    }
    source_meta = {
        "bytes": len(raw_bytes),
        "created_at_utc": counters["created_at_utc"],
        "modified_at_utc": counters["modified_at_utc"],
        "captured_sha256": hashlib.sha256(raw_bytes).hexdigest().upper(),
    }
    return raw_bytes, counters, source_meta


def snapshot_compile_log_once(manifest: dict[str, Any], start: datetime, end: datetime) -> tuple[bytes, Path, dict[str, Any]]:
    source_snapshot = RUN_DIR / "snapshot/source/EA_SupertrendStateFlip.mq5"
    ex5_snapshot = RUN_DIR / "snapshot/build/EA_SupertrendStateFlip.ex5"
    canonical_source = ROOT / "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5"
    canonical_ex5 = canonical_source.with_suffix(".ex5")
    if (
        Path(str(manifest.get("main_file", ""))).resolve() != canonical_source
        or Path(str(manifest.get("compiled_ex5_file", ""))).resolve() != canonical_ex5
        or Path(str(manifest.get("source_snapshot", ""))).resolve() != source_snapshot
        or Path(str(manifest.get("ex5_snapshot", ""))).resolve() != ex5_snapshot
        or sha256_file(canonical_source) != EXPECTED["source"]
        or sha256_file(source_snapshot) != EXPECTED["source"]
        or sha256_file(canonical_ex5) != EXPECTED["ex5"]
        or sha256_file(ex5_snapshot) != EXPECTED["ex5"]
        or manifest.get("ex5_sha256") != EXPECTED["ex5"]
        or manifest.get("tester_ex5_sha256") != EXPECTED["ex5"]
    ):
        raise ValueError("HYP008 compile/source snapshot binding mismatch")
    before = CANONICAL_COMPILE_LOG.stat()
    compile_raw = CANONICAL_COMPILE_LOG.read_bytes()
    after = CANONICAL_COMPILE_LOG.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError("compile log changed during the single recovery read")
    if hashlib.sha256(compile_raw).hexdigest().upper() != EXPECTED["compile_log"]:
        raise ValueError("compile log bytes mismatch")
    modified = datetime.fromtimestamp(before.st_mtime, tz=timezone.utc)
    if modified < start - timedelta(minutes=15) or modified > end + timedelta(seconds=5):
        raise ValueError("compile log is not contemporaneous with HYP008")
    text = BASE.decode_text_bytes(compile_raw)
    if re.search(r"\b0\s+errors?\b", text, re.I) is None or re.search(r"\b0\s+warnings?\b", text, re.I) is None:
        raise ValueError("compile log does not prove 0E/0W")
    return compile_raw, ex5_snapshot, {
        "bytes": len(compile_raw),
        "created_at_utc": datetime.fromtimestamp(before.st_ctime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "modified_at_utc": modified.isoformat().replace("+00:00", "Z"),
        "captured_sha256": hashlib.sha256(compile_raw).hexdigest().upper(),
    }


def execute(registry: Path) -> dict[str, Any]:
    registry = registry.resolve()
    row, authority = validate_registry(registry)
    marker = claim(authority)
    terminal_path = OUTPUT_DIR / "attempt_terminal.json"
    try:
        files = {
            "run_manifest": RUN_DIR / "run_manifest.json",
            "report": RUN_DIR / "report.html",
            "journal_delta": RUN_DIR / "logs/tester_journal_delta.log",
            "source": RUN_DIR / "snapshot/source/EA_SupertrendStateFlip.mq5",
            "ex5": RUN_DIR / "snapshot/build/EA_SupertrendStateFlip.ex5",
            "compile_log": CANONICAL_COMPILE_LOG,
            "common_csv": COMMON_FILE,
            "mt5_receipt": ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001/mt5_run_receipt.json",
            "mt5_terminal": ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001/attempt_terminal.json",
        }
        for label, path in files.items():
            if label in {"compile_log", "common_csv"}:
                continue
            require_hash(path, EXPECTED[label], label)

        manifest, start, end = BASE.validate_run_manifest(RUN_DIR)
        BASE.validate_contract_receipt(CONTRACT_RECEIPT, manifest)
        BASE.validate_mt5_run_chain(RUN_DIR, CONTRACT_RECEIPT)
        journal_delta = BASE.validate_data_quality_journal(manifest, RUN_DIR)
        normalized_summary, summary_occurrences = validate_identical_current_summaries(journal_delta)
        compile_raw, ex5_snapshot, compile_source_meta = snapshot_compile_log_once(manifest, start, end)
        csv_raw, counters, csv_source_meta = snapshot_common_csv_once(COMMON_FILE, start, end)

        recovered_csv = OUTPUT_DIR / "st003_mql5_parity.csv"
        recovered_summary = OUTPUT_DIR / "st009_normalized_tester_summary.log"
        recovered_compile = OUTPUT_DIR / "ST004_MetaEditor_compile.log"
        write_exclusive(recovered_csv, csv_raw)
        write_exclusive(recovered_summary, normalized_summary)
        write_exclusive(recovered_compile, compile_raw)

        if sha256_file(recovered_compile) != EXPECTED["compile_log"] or sha256_file(ex5_snapshot) != EXPECTED["ex5"]:
            raise ValueError("fresh recovery compile evidence sealing mismatch")

        completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bindings = {
            label: {"path": path.resolve().as_posix(), "sha256": sha256_file(path)}
            for label, path in files.items()
            if label not in {"compile_log", "common_csv"}
        }
        bindings["compile_log"] = {
            "path": CANONICAL_COMPILE_LOG.resolve().as_posix(),
            "sha256": compile_source_meta["captured_sha256"],
            **compile_source_meta,
        }
        bindings["common_csv"] = {
            "path": COMMON_FILE.resolve().as_posix(),
            "sha256": csv_source_meta["captured_sha256"],
            **csv_source_meta,
        }
        bindings.update(
            {
                "collector": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
                "registry": {"path": registry.as_posix(), **authority},
                "authority_prereg": {"path": row.get("prereg_path"), "sha256": row.get("prereg_sha256")},
                "contract_receipt": {"path": CONTRACT_RECEIPT.as_posix(), "sha256": sha256_file(CONTRACT_RECEIPT)},
                "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
                "recovered_csv": {"path": recovered_csv.as_posix(), "sha256": sha256_file(recovered_csv)},
                "normalized_summary": {"path": recovered_summary.as_posix(), "sha256": sha256_file(recovered_summary)},
                "recovered_compile_log": {"path": recovered_compile.as_posix(), "sha256": sha256_file(recovered_compile)},
            }
        )
        if (
            bindings["common_csv"]["sha256"] != bindings["recovered_csv"]["sha256"]
            or bindings["compile_log"]["sha256"] != bindings["recovered_compile_log"]["sha256"]
        ):
            raise ValueError("captured mutable source hashes do not match sealed recovery artifacts")
        receipt = {
            "schema_version": "st009_existing_run_artifact_recovery_receipt.v1",
            "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
            "run_hypothesis_id": RUN_HYPOTHESIS_ID,
            "target_hypothesis_id": TARGET_HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": completed,
            "bindings": bindings,
            "summary_occurrences": summary_occurrences,
            "summary_distinct": 1,
            "counters": counters,
            "orders_executed": 0,
            "trades_executed": 0,
            "economics_evaluated": False,
            "verdict": "EXISTING_HYP008_ARTIFACT_RECOVERY_PASS",
        }
        receipt_raw = json_bytes(receipt)
        receipt_path = OUTPUT_DIR / "artifact_recovery_receipt.json"
        write_exclusive(receipt_path, receipt_raw)
        terminal = {
            "schema_version": "st009_existing_run_artifact_recovery_terminal.v1",
            "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": completed,
            "status": "COMPLETE",
            "verdict": receipt["verdict"],
            "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest().upper(),
            "same_id_retry_authorized": False,
        }
        write_exclusive(terminal_path, json_bytes(terminal))
        return receipt
    except Exception as exc:
        if not terminal_path.exists():
            write_exclusive(
                terminal_path,
                json_bytes(
                    {
                        "schema_version": "st009_existing_run_artifact_recovery_terminal.v1",
                        "hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
                        "attempt_id": ATTEMPT_ID,
                        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "status": "FAILED",
                        "verdict": "EXISTING_HYP008_ARTIFACT_RECOVERY_FAIL",
                        "error_type": type(exc).__name__,
                        "same_id_retry_authorized": False,
                    }
                ),
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--registry", type=Path, default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    receipt = execute(args.registry)
    print(json_bytes({"verdict": receipt["verdict"], "counters": receipt["counters"]}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
