#!/usr/bin/env python3
"""Outcome-blind capability audit for Foundation M5 bar real_volume."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


AUDIT_ID = "BAR-REAL-VOLUME-CAPABILITY-001"
PLAN_REL = "04. Memory/research/20260813_FOUNDATION_BAR_REAL_VOLUME_CAPABILITY_PLAN.md"
PLAN_SHA256 = "AD46D9E3F564AEC0EB285BBD83FD66010C9E9A25F7E2F6A2403C019D43F04670"
NATIVE_TICK_RECEIPT_REL = "04. Memory/research/20260812_NATIVE_TICK_RAW_FIELD_FRONTIER.md"
EVIDENCE_REL = "04. Memory/research/evidence/BAR-REAL-VOLUME-CAPABILITY-001"
SCRIPT_REL = "04. Memory/research/audit_foundation_bar_real_volume.py"
WINDOW_START = pd.Timestamp("2018-01-01T00:00:00Z")
WINDOW_END = pd.Timestamp("2026-08-01T00:00:00Z")
RECENT_START = pd.Timestamp("2026-07-01T00:00:00Z")
YEARS = tuple(range(2018, 2027))
REQUIRED_COLUMNS = ("time_utc", "tick_volume", "real_volume")

FILES = {
    "EURUSD": (
        "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
        "DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/"
        "EURUSD_M5_ALL_AVAILABLE_20260801.parquet",
        "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8",
    ),
    "GBPUSD": (
        "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
        "DATA-FIVEPERCENT-5ASSET-MULTITF-004/GBPUSD/"
        "GBPUSD_M5_ALL_AVAILABLE_20260801.parquet",
        "8EE2720261FC05A13A2E919C3EAA4FF50EEF75F9CB068519C61C48BB3D6B4F4B",
    ),
    "USDJPY": (
        "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
        "DATA-FIVEPERCENT-5ASSET-MULTITF-004/USDJPY/"
        "USDJPY_M5_ALL_AVAILABLE_20260801.parquet",
        "FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD",
    ),
    "XAUUSD": (
        "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
        "DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/"
        "XAUUSD_M5_ALL_AVAILABLE_20260801.parquet",
        "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Accumulator:
    rows: int = 0
    positive: int = 0
    equal_tick: int = 0
    min_positive: int | None = None
    max_positive: int | None = None
    gcd_positive: int = 0
    distinct_positive: set[int] = field(default_factory=set)
    first_positive_utc: pd.Timestamp | None = None
    last_positive_utc: pd.Timestamp | None = None
    corr_n: int = 0
    sum_x: float = 0.0
    sum_y: float = 0.0
    sum_x2: float = 0.0
    sum_y2: float = 0.0
    sum_xy: float = 0.0

    def add(self, ts: pd.DatetimeIndex, tick: np.ndarray, real: np.ndarray) -> None:
        self.rows += int(real.size)
        self.equal_tick += int(np.count_nonzero(real == tick))
        pos = real > 0
        count = int(np.count_nonzero(pos))
        self.positive += count
        if count == 0:
            return
        rv = real[pos].astype(np.uint64, copy=False)
        tv = tick[pos].astype(np.float64, copy=False)
        rvf = rv.astype(np.float64, copy=False)
        unique = np.unique(rv)
        self.distinct_positive.update(int(value) for value in unique.tolist())
        batch_gcd = int(np.gcd.reduce(unique))
        self.gcd_positive = math.gcd(self.gcd_positive, batch_gcd)
        batch_min = int(rv.min())
        batch_max = int(rv.max())
        self.min_positive = batch_min if self.min_positive is None else min(self.min_positive, batch_min)
        self.max_positive = batch_max if self.max_positive is None else max(self.max_positive, batch_max)
        pos_ts = ts[pos]
        batch_first = pos_ts.min()
        batch_last = pos_ts.max()
        self.first_positive_utc = (
            batch_first if self.first_positive_utc is None else min(self.first_positive_utc, batch_first)
        )
        self.last_positive_utc = (
            batch_last if self.last_positive_utc is None else max(self.last_positive_utc, batch_last)
        )
        self.corr_n += count
        self.sum_x += float(rvf.sum(dtype=np.float64))
        self.sum_y += float(tv.sum(dtype=np.float64))
        self.sum_x2 += float(np.square(rvf).sum(dtype=np.float64))
        self.sum_y2 += float(np.square(tv).sum(dtype=np.float64))
        self.sum_xy += float(np.multiply(rvf, tv).sum(dtype=np.float64))

    def pearson(self) -> float | None:
        if self.corr_n < 2:
            return None
        n = float(self.corr_n)
        numerator = n * self.sum_xy - self.sum_x * self.sum_y
        left = n * self.sum_x2 - self.sum_x * self.sum_x
        right = n * self.sum_y2 - self.sum_y * self.sum_y
        denominator = math.sqrt(max(0.0, left) * max(0.0, right))
        if denominator == 0.0:
            return None
        value = numerator / denominator
        return max(-1.0, min(1.0, float(value)))

    def summary(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "positive_real_volume_rows": self.positive,
            "zero_real_volume_rows": self.rows - self.positive,
            "positive_share": self.positive / self.rows if self.rows else None,
            "min_positive": self.min_positive,
            "max_positive": self.max_positive,
            "gcd_positive": self.gcd_positive if self.positive else None,
            "distinct_positive": len(self.distinct_positive),
            "real_volume_equals_tick_volume_rows": self.equal_tick,
            "real_volume_equals_tick_volume_share": self.equal_tick / self.rows if self.rows else None,
            "positive_real_volume_tick_volume_pearson": self.pearson(),
            "first_positive_utc": self.first_positive_utc.isoformat() if self.first_positive_utc is not None else None,
            "last_positive_utc": self.last_positive_utc.isoformat() if self.last_positive_utc is not None else None,
        }


def evaluate_symbol_gates(summary: dict[str, Any]) -> dict[str, bool]:
    years = summary["years"]
    return {
        "every_year_has_rows": all(years[str(year)]["rows"] > 0 for year in YEARS),
        "every_year_positive_share_at_least_0p95": all(
            years[str(year)]["positive_share"] is not None
            and years[str(year)]["positive_share"] >= 0.95
            for year in YEARS
        ),
        "recent_rows_at_least_1000": summary["recent"]["rows"] >= 1000,
        "recent_positive_share_at_least_0p95": (
            summary["recent"]["positive_share"] is not None
            and summary["recent"]["positive_share"] >= 0.95
        ),
        "recent_distinct_positive_at_least_100": summary["recent"]["distinct_positive"] >= 100,
        "full_exact_tick_identity_below_0p99": (
            summary["full"]["real_volume_equals_tick_volume_share"] is not None
            and summary["full"]["real_volume_equals_tick_volume_share"] < 0.99
        ),
        "counter_reconciliation": (
            summary["full"]["rows"]
            == summary["full"]["positive_real_volume_rows"] + summary["full"]["zero_real_volume_rows"]
        ),
    }


def analyze(path: Path) -> dict[str, Any]:
    parquet = pq.ParquetFile(path)
    missing = sorted(set(REQUIRED_COLUMNS) - set(parquet.schema_arrow.names))
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    full = Accumulator()
    recent = Accumulator()
    by_year = {year: Accumulator() for year in YEARS}
    data_rows_read = 0
    for batch in parquet.iter_batches(batch_size=262_144, columns=list(REQUIRED_COLUMNS)):
        frame = batch.to_pandas()
        ts = pd.DatetimeIndex(pd.to_datetime(frame["time_utc"], utc=True))
        tick = frame["tick_volume"].to_numpy(dtype=np.uint64, copy=False)
        real = frame["real_volume"].to_numpy(dtype=np.uint64, copy=False)
        if ts.hasnans:
            raise ValueError("non-finite time_utc")
        in_window = (ts >= WINDOW_START) & (ts < WINDOW_END)
        data_rows_read += int(np.count_nonzero(in_window))
        if not np.any(in_window):
            continue
        wts = ts[in_window]
        wtv = tick[in_window]
        wrv = real[in_window]
        full.add(wts, wtv, wrv)
        year_values = wts.year.to_numpy()
        for year in YEARS:
            mask = year_values == year
            if np.any(mask):
                by_year[year].add(wts[mask], wtv[mask], wrv[mask])
        rmask = wts >= RECENT_START
        if np.any(rmask):
            recent.add(wts[rmask], wtv[rmask], wrv[rmask])
    if data_rows_read != full.rows:
        raise ValueError("data row reconciliation failed")
    result = {
        "full": full.summary(),
        "recent": recent.summary(),
        "years": {str(year): by_year[year].summary() for year in YEARS},
        "data_rows_read": data_rows_read,
        "requested_columns": list(REQUIRED_COLUMNS),
    }
    result["gates"] = evaluate_symbol_gates(result)
    result["all_payload_gates_pass"] = all(result["gates"].values())
    return result


def execute(root: Path) -> int:
    plan = root / PLAN_REL
    if sha256_file(plan) != PLAN_SHA256:
        raise ValueError("plan hash mismatch")
    bindings: dict[str, Any] = {
        "plan": {"path": PLAN_REL, "sha256": PLAN_SHA256},
        "native_tick_receipt": {
            "path": NATIVE_TICK_RECEIPT_REL,
            "sha256": sha256_file(root / NATIVE_TICK_RECEIPT_REL),
        },
        "inputs": {},
    }
    for symbol, (relative, expected_hash) in FILES.items():
        actual_hash = sha256_file(root / relative)
        if actual_hash != expected_hash:
            raise ValueError(f"{symbol} hash mismatch")
        bindings["inputs"][symbol] = {"path": relative, "sha256": actual_hash}

    evidence = root / EVIDENCE_REL
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(exist_ok=False)
    started = {
        "audit_id": AUDIT_ID,
        "schema_version": "bar_real_volume_capability_started.v1",
        "started_at_utc": utc_now(),
        "bindings": bindings,
        "authorized_columns": list(REQUIRED_COLUMNS),
        "forbidden": ["OHLC", "spread", "returns", "direction", "targets", "trades", "economics", "MT5"],
    }
    write_json(evidence / "attempt_started.json", started)

    try:
        symbols: dict[str, Any] = {}
        for symbol, (relative, _) in FILES.items():
            symbols[symbol] = analyze(root / relative)
        all_payload_pass = all(item["all_payload_gates_pass"] for item in symbols.values())
        payload_verdict = (
            "PASS_BROKER_BAR_PAYLOAD_ONLY_NO_TRADE_PROVENANCE"
            if all_payload_pass
            else "KILL_REAL_VOLUME_PAYLOAD_COVERAGE_OR_TRIVIALITY"
        )
        causal_verdict = (
            "KILL_REAL_VOLUME_PROVENANCE_UNRECONCILED"
            if all_payload_pass
            else "NOT_REACHED_PAYLOAD_GATE_FAILED"
        )
        report = {
            "audit_id": AUDIT_ID,
            "schema_version": "bar_real_volume_capability_report.v1",
            "window": {"start": WINDOW_START.isoformat(), "end_exclusive": WINDOW_END.isoformat()},
            "recent_window": {"start": RECENT_START.isoformat(), "end_exclusive": WINDOW_END.isoformat()},
            "symbols": symbols,
            "payload_verdict": payload_verdict,
            "causal_source_verdict": causal_verdict,
            "all_payload_gates_pass": all_payload_pass,
            "native_tick_adverse_fact_preserved": True,
            "forbidden_counters": {
                "ohlc_columns_read": 0,
                "spread_columns_read": 0,
                "returns_computed": 0,
                "direction_maps_computed": 0,
                "targets_computed": 0,
                "trades_simulated": 0,
                "pnl_computed": 0,
                "profit_factor_computed": 0,
                "mt5_runs": 0,
                "mql5_files_created": 0,
                "validation_rows_read": 0,
                "holdout_rows_read": 0,
            },
        }
        report_path = evidence / "bar_real_volume_capability_report.json"
        write_json(report_path, report)
        receipt = {
            "audit_id": AUDIT_ID,
            "schema_version": "bar_real_volume_capability_receipt.v1",
            "completed_at_utc": utc_now(),
            "bindings": {
                **bindings,
                "auditor": {"path": SCRIPT_REL, "sha256": sha256_file(root / SCRIPT_REL)},
                "report": {
                    "path": f"{EVIDENCE_REL}/bar_real_volume_capability_report.json",
                    "sha256": sha256_file(report_path),
                },
            },
            "payload_verdict": payload_verdict,
            "causal_source_verdict": causal_verdict,
            "hypothesis_authorized": False,
            "outcomes_authorized": False,
            "mql5_or_mt5_authorized": False,
            "same_audit_rerun_authorized": False,
        }
        write_json(evidence / "bar_real_volume_capability_receipt.json", receipt)
        print(json.dumps({
            "payload_verdict": payload_verdict,
            "causal_source_verdict": causal_verdict,
            "symbols": {
                symbol: {
                    "full_positive_share": item["full"]["positive_share"],
                    "recent_positive_share": item["recent"]["positive_share"],
                    "recent_distinct_positive": item["recent"]["distinct_positive"],
                    "all_payload_gates_pass": item["all_payload_gates_pass"],
                }
                for symbol, item in symbols.items()
            },
        }, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        write_json(
            evidence / "attempt_failed.json",
            {
                "audit_id": AUDIT_ID,
                "schema_version": "bar_real_volume_capability_failed.v1",
                "failed_at_utc": utc_now(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "terminal_for_audit_id": True,
            },
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    root = Path(__file__).resolve().parents[2]
    return execute(root)


if __name__ == "__main__":
    raise SystemExit(main())
