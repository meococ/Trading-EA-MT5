#!/usr/bin/env python3
"""Audit whether Foundation timestamps cure DFR's frozen horizon coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


AUDIT_ID = "DFR-FOUNDATION-TIMESTAMP-CURE-001"
PLAN_SHA256 = "E3B715C25B87ECA88C4E0F98613534A2D1F9B20B526DBD2BDC69395649F27FD0"
CLASSIFICATIONS_SHA256 = "E5AF87FE704DBA1114C89D1422DD016DBFB25F41DA442B8786CF26216CAAE8AC"
FOUNDATION_SHA256 = "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8"
EXPECTED_SIGNALS = 1235
EXPECTED_OLD_EXECUTABLE = 1220
EXPECTED_OLD_INCOMPLETE = 15
MIN_COVERAGE = 0.99
SOURCE_START = pd.Timestamp("2015-01-01T00:00:00Z")
SOURCE_END = pd.Timestamp("2021-01-01T00:00:00Z")
ALLOWED_CLASSIFICATION_KEYS = {
    "source_signal_id",
    "decision_utc",
    "entry_open_utc",
    "status",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def load_frozen_signals(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        source = json.loads(line)
        row = {key: source[key] for key in ALLOWED_CLASSIFICATION_KEYS}
        if row["status"] not in {"SOURCE_EXECUTABLE", "HORIZON_INCOMPLETE"}:
            raise ValueError("unexpected frozen classification status")
        row["decision_utc"] = pd.Timestamp(row["decision_utc"])
        row["entry_open_utc"] = pd.Timestamp(row["entry_open_utc"])
        if row["decision_utc"].tz is None or row["entry_open_utc"].tz is None:
            raise ValueError("classification timestamps must be UTC-aware")
        rows.append(row)
    ids = [row["source_signal_id"] for row in rows]
    statuses = [row["status"] for row in rows]
    if len(rows) != EXPECTED_SIGNALS or len(set(ids)) != EXPECTED_SIGNALS:
        raise ValueError("frozen classification identity mismatch")
    if statuses.count("SOURCE_EXECUTABLE") != EXPECTED_OLD_EXECUTABLE or statuses.count("HORIZON_INCOMPLETE") != EXPECTED_OLD_INCOMPLETE:
        raise ValueError("frozen classification population mismatch")
    return rows


def complete_m15_starts(times: pd.Series) -> set[int]:
    stamps = pd.to_datetime(times, utc=True, errors="raise")
    epoch = (stamps.astype("int64") // 1_000_000_000).to_numpy(dtype=np.int64)
    if len(epoch) == 0 or len(np.unique(epoch)) != len(epoch):
        raise ValueError("Foundation M5 timestamps must be nonempty and unique")
    epoch.sort()
    if np.any(np.diff(epoch) <= 0):
        raise ValueError("Foundation M5 timestamps must be strictly increasing")
    bucket = epoch - np.mod(epoch, 900)
    offsets = epoch - bucket
    complete: set[int] = set()
    start = 0
    while start < len(epoch):
        end = start + 1
        while end < len(epoch) and bucket[end] == bucket[start]:
            end += 1
        if end - start == 3 and np.array_equal(offsets[start:end], np.array([0, 300, 600], dtype=np.int64)):
            complete.add(int(bucket[start]))
        start = end
    return complete


def evaluate(signals: list[dict[str, Any]], m15_starts: set[int]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for signal in signals:
        entry_epoch = int(signal["entry_open_utc"].timestamp())
        horizon = [entry_epoch + 900 * index for index in range(6)]
        observed = sum(value in m15_starts for value in horizon)
        new_complete = observed == 6
        rows.append({
            "source_signal_id": signal["source_signal_id"],
            "decision_utc": signal["decision_utc"].isoformat().replace("+00:00", "Z"),
            "entry_open_utc": signal["entry_open_utc"].isoformat().replace("+00:00", "Z"),
            "old_status": signal["status"],
            "foundation_observed_horizon_bars": observed,
            "foundation_horizon_complete": new_complete,
        })
    complete_count = sum(row["foundation_horizon_complete"] for row in rows)
    old_exec = [row for row in rows if row["old_status"] == "SOURCE_EXECUTABLE"]
    old_incomplete = [row for row in rows if row["old_status"] == "HORIZON_INCOMPLETE"]
    retained = sum(row["foundation_horizon_complete"] for row in old_exec)
    recovered = sum(row["foundation_horizon_complete"] for row in old_incomplete)
    coverage = complete_count / len(rows)
    retained_ratio = retained / len(old_exec)
    gates = {
        "exact_frozen_signal_population": len(rows) == EXPECTED_SIGNALS,
        "foundation_horizon_coverage_at_least_0p99": coverage >= MIN_COVERAGE,
        "old_executable_retention_at_least_0p99": retained_ratio >= MIN_COVERAGE,
        "at_least_one_old_incomplete_recovered": recovered >= 1,
        "finite_metrics": all(math.isfinite(value) for value in (coverage, retained_ratio)),
        "forbidden_counters_zero": True,
    }
    return {
        "audit_id": AUDIT_ID,
        "epistemic_scope": "TIMESTAMP_CAPABILITY_ONLY_NO_PRICE_NO_OUTCOME",
        "population": {
            "frozen_signals": len(rows),
            "old_source_executable": len(old_exec),
            "old_horizon_incomplete": len(old_incomplete),
            "foundation_horizon_complete": complete_count,
            "foundation_horizon_incomplete": len(rows) - complete_count,
            "old_executable_retained": retained,
            "old_executable_lost": len(old_exec) - retained,
            "old_incomplete_recovered": recovered,
            "old_incomplete_still_incomplete": len(old_incomplete) - recovered,
        },
        "metrics": {
            "foundation_horizon_coverage": coverage,
            "old_executable_retention_ratio": retained_ratio,
        },
        "new_incomplete_signal_ids": [row["source_signal_id"] for row in rows if not row["foundation_horizon_complete"]],
        "recovered_signal_ids": [row["source_signal_id"] for row in old_incomplete if row["foundation_horizon_complete"]],
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "forbidden_counters": {
            "price_columns_read": 0,
            "post_entry_ohlc_rows_read": 0,
            "returns_computed": 0,
            "trades_simulated": 0,
            "pnl_computed": 0,
            "profit_factor_computed": 0,
            "mt5_runs": 0,
            "mql5_files_created": 0,
            "validation_rows_read": 0,
            "holdout_rows_read": 0,
        },
        "rows": rows,
    }


def execute(root: Path) -> dict[str, Any]:
    base = root / "03. EA Developer/EA_DiurnalResidualImpulse/research"
    plan = base / "DFR_FOUNDATION_TIMESTAMP_CURE_AUDIT_PLAN.md"
    classifications = base / "evidence/HYP-DFR-IC-EURUSD-M15-001_SOURCE_FEASIBILITY/DFRIC001-SOURCE-001/dfr_ic_001_source_classifications.jsonl"
    foundation = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet"
    output_dir = base / f"evidence/{AUDIT_ID}"
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("audit evidence already exists")
    if sha256_file(plan) != PLAN_SHA256 or sha256_file(classifications) != CLASSIFICATIONS_SHA256 or sha256_file(foundation) != FOUNDATION_SHA256:
        raise ValueError("frozen input hash mismatch")
    required = {"symbol", "timeframe", "time_utc", "utc_ambiguous"}
    if not required <= set(pq.ParquetFile(foundation).schema_arrow.names):
        raise ValueError("Foundation timestamp schema mismatch")
    signals = load_frozen_signals(classifications)
    timestamps = pd.read_parquet(
        foundation,
        columns=["symbol", "timeframe", "time_utc", "utc_ambiguous"],
        filters=[
            ("time_utc", ">=", SOURCE_START.to_pydatetime()),
            ("time_utc", "<", SOURCE_END.to_pydatetime()),
        ],
        engine="pyarrow",
    )
    if timestamps.empty or not timestamps["symbol"].eq("EURUSD").all() or not timestamps["timeframe"].eq("M5").all():
        raise ValueError("Foundation selection identity mismatch")
    ambiguous = int(timestamps["utc_ambiguous"].fillna(True).astype(bool).sum())
    if ambiguous != 0:
        raise ValueError("ambiguous Foundation UTC rows are forbidden")
    starts = complete_m15_starts(timestamps["time_utc"])
    result = evaluate(signals, starts)
    replay = evaluate(load_frozen_signals(classifications), set(starts))
    if canonical_json(result) != canonical_json(replay):
        raise ValueError("deterministic timestamp replay mismatch")
    result["foundation"] = {
        "m5_timestamp_rows": int(len(timestamps)),
        "complete_m15_timestamp_buckets": int(len(starts)),
        "ambiguous_utc_rows": ambiguous,
    }
    result["all_gates_pass"] = all(result["gates"].values())
    result["verdict"] = "PASS_INDEPENDENT_TIMESTAMP_CURE_EVIDENCE_ONLY" if result["all_gates_pass"] else "NO_DFR_REOPENABLE_TIMESTAMP_CURE"
    report_bytes = canonical_json(result)
    report_path = output_dir / "timestamp_cure_report.json"
    atomic_write(report_path, report_bytes)
    receipt = {
        "schema_version": "dfr_foundation_timestamp_cure_receipt.v1",
        "audit_id": AUDIT_ID,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "plan": {"path": plan.relative_to(root).as_posix(), "sha256": sha256_file(plan)},
            "classifications": {"path": classifications.relative_to(root).as_posix(), "sha256": sha256_file(classifications)},
            "foundation": {"path": foundation.relative_to(root).as_posix(), "sha256": sha256_file(foundation)},
            "auditor": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
        },
        "verdict": result["verdict"],
        "same_audit_rerun_authorized": False,
        "outcomes_authorized": False,
        "mql5_or_mt5_authorized": False,
    }
    atomic_write(output_dir / "timestamp_cure_receipt.json", canonical_json(receipt))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    root = Path(__file__).resolve().parents[3]
    result = execute(root)
    summary = {key: result[key] for key in ("audit_id", "population", "metrics", "gates", "all_gates_pass", "verdict")}
    print(canonical_json(summary).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
