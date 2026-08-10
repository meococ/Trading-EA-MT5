#!/usr/bin/env python3
"""Outcome-blind H1 BB/KC first-release scan with exact next-H1 availability."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[3]
BASE_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/analyze_bksr_h1_m5_source.py"
BASE_PATH = ROOT / BASE_RELATIVE_PATH
BASE_SHA256 = "CC393F09795346901353DE120D6C9B94E94078AF4EFFC260E4DC43E1E86F8164"
_SPEC = importlib.util.spec_from_file_location("bksr001_formula_dependency", BASE_PATH)
if not _SPEC or not _SPEC.loader:
    raise RuntimeError("unable to load frozen BKSR001 formula dependency")
BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(BASE)
if BASE.sha256_file(BASE_PATH) != BASE_SHA256:
    raise RuntimeError("frozen BKSR001 formula dependency SHA mismatch")

HYPOTHESIS_ID = "HYP-BKSR-XAUUSD-M15-002"
ATTEMPT_ID = "BKSR002-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "E0EE52926EAA00F301446C3AA4D779B398CCC3E167A9E135C6AFE0217379A1E3"
TEST_SHA256 = "AF9E49ADBAC564FDF0B8DB2C3E5E0A10B6D5115FA24446A2FEF71FC6098CF8AA"
MANIFEST_SHA256 = BASE.MANIFEST_SHA256
H1_SHA256 = BASE.H1_SHA256
MANIFEST_RELATIVE_PATH = BASE.MANIFEST_RELATIVE_PATH
H1_RELATIVE_PATH = BASE.H1_RELATIVE_PATH
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/analyze_bksr_h1_next_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/tests/test_analyze_bksr_h1_next_source.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/HYP-BKSR-XAUUSD-M15-002_FROZEN_PREREG.md"
OUTPUT_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/evidence/HYP-BKSR-XAUUSD-M15-002/BKSR002-SOURCE-ATTEMPT-001"
DATA_ACCESS_PREDICATE = "H1_time_utc<2023-01-01T00:00:00Z;score_only_2018-01-01T00:00:00Z<=time_utc<2023-01-01T00:00:00Z;next_H1_timestamp_epoch_only"
DESIGN_START = BASE.DESIGN_START
DESIGN_END = BASE.DESIGN_END
MIN_ROWS = 25_000
MIN_FEATURE_COVERAGE = 0.99
MIN_NEXT_COVERAGE = 0.97
MIN_EVENTS = 500
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.30
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50
EVENT_KEYS = BASE.EVENT_KEYS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join((json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8") for row in rows)


def exclusive_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def verify_inputs(paths: dict[str, Path], expected: dict[str, str]) -> dict[str, str]:
    observed = {name: sha256_file(path) for name, path in paths.items()}
    failed = sorted(name for name in expected if observed.get(name) != expected[name])
    if failed or set(observed) != set(expected):
        raise ValueError(f"frozen input SHA mismatch: {failed}")
    return observed


def analyze_frame(h1: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = h1.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    bands = BASE.calculate_bands(
        data["high"].to_numpy(dtype=float),
        data["low"].to_numpy(dtype=float),
        data["close"].to_numpy(dtype=float),
    )
    raw_all = BASE.release_signals(data, bands)
    design = data["time_utc"].ge(DESIGN_START) & data["time_utc"].lt(DESIGN_END)
    usable_values = np.logical_and.reduce(tuple(np.isfinite(values) for values in bands))
    usable = design & pd.Series(usable_values)
    raw = [row for row in raw_all if bool(design.iloc[row["_index"]]) and bool(usable.iloc[row["_index"]])]
    events: list[dict[str, Any]] = []
    gap_rejects = 0
    boundary_rejects = 0
    for row in raw:
        index = int(row["_index"])
        if index + 1 >= len(data):
            gap_rejects += 1
            continue
        source_time = data.at[index, "time_utc"]
        next_time = data.at[index + 1, "time_utc"]
        source_epoch = int(data.at[index, "source_epoch"])
        next_epoch = int(data.at[index + 1, "source_epoch"])
        if next_time >= DESIGN_END:
            boundary_rejects += 1
            continue
        if next_time != source_time + pd.Timedelta(hours=1) or next_epoch != source_epoch + 3600:
            gap_rejects += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "decision_time_utc": next_time.isoformat().replace("+00:00", "Z"),
            "direction": row["direction"],
            "squeeze_start_index": int(row["squeeze_start"]),
            "squeeze_end_index": int(row["squeeze_end"]),
            "squeeze_length_bars": int(row["squeeze_length_bars"]),
            "source_bar_index": index,
            "squeeze_start_time_utc": data.at[row["squeeze_start"], "time_utc"].isoformat().replace("+00:00", "Z"),
            "source_bar_source_epoch": source_epoch,
            "decision_source_epoch": next_epoch,
            **{name: float(row[name]) for name in (
                "close", "bb_basis", "bb_upper", "bb_lower", "kc_upper", "kc_lower",
                "squeeze_end_bb_upper", "squeeze_end_bb_lower", "squeeze_end_kc_upper", "squeeze_end_kc_lower",
            )},
        })

    design_rows = int(design.sum())
    usable_rows = int(usable.sum())
    raw_count = len(raw)
    count = len(events)
    weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    by_direction = {name: sum(event["direction"] == name for event in events) for name in ("LONG", "SHORT")}
    by_year = {str(year): sum(pd.Timestamp(event["decision_time_utc"]).year == year for event in events) for year in range(2018, 2023)}
    year_weeks = {str(year): BASE.year_weeks(year) for year in range(2018, 2023)}
    year_cadence = {year: by_year[year] / year_weeks[year] for year in by_year}
    direction_share = {name: (value / count if count else 0.0) for name, value in by_direction.items()}
    max_year_share = max(by_year.values(), default=0) / count if count else 0.0
    coverage = count / raw_count if raw_count else 0.0
    cadence = count / weeks if weeks else 0.0
    gates = {
        "design_rows_gte_25000": design_rows >= MIN_ROWS,
        "usable_coverage_gte_0_99": usable_rows / design_rows >= MIN_FEATURE_COVERAGE if design_rows else False,
        "raw_event_exact_next_h1_coverage_gte_0_97": coverage >= MIN_NEXT_COVERAGE,
        "candidates_gte_500": count >= MIN_EVENTS,
        "pooled_cadence_2_to_5": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "each_direction_gte_0_30": all(value >= MIN_DIRECTION_SHARE for value in direction_share.values()),
        "max_year_share_lte_0_30": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence_1_25_to_6_5": all(MIN_YEAR_CADENCE <= value <= MAX_YEAR_CADENCE for value in year_cadence.values()),
        "zero_conflicts": True,
    }
    verdict = "SCREENED_SOURCE_PASS_DIRECT_MQL5_BUILD_AUTHORIZED" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY_EXACT_BBKC_NEXT_H1_OPEN"
    report = {
        "schema_version": "bksr_h1_next_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "formula_dependency_sha256": BASE_SHA256,
        "rows": {"h1_total": len(data), "design": design_rows, "usable_design": usable_rows},
        "events": {"raw": raw_count, "executable": count, "gap_rejects": gap_rejects, "boundary_rejects": boundary_rejects},
        "raw_event_exact_next_h1_coverage": coverage,
        "weeks": weeks,
        "cadence_per_week": cadence,
        "by_direction": by_direction,
        "direction_share": direction_share,
        "by_year": by_year,
        "year_cadence": year_cadence,
        "max_year_share": max_year_share,
        "gates": gates,
        "post_event_ohlc_rows_read": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
        "profit_factor_computed": 0,
        "verdict": verdict,
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for event in events:
        if set(event) != EVENT_KEYS:
            raise ValueError("event allowlist mismatch")
        if event["decision_source_epoch"] != event["source_bar_source_epoch"] + 3600:
            raise ValueError("event epoch mapping mismatch")
        if pd.Timestamp(event["decision_time_utc"]) != pd.Timestamp(event["source_bar_time_utc"]) + pd.Timedelta(hours=1):
            raise ValueError("event UTC mapping mismatch")
        if event["direction"] == "LONG" and not event["close"] > event["bb_basis"]:
            raise ValueError("LONG predicate mismatch")
        if event["direction"] == "SHORT" and not event["close"] < event["bb_basis"]:
            raise ValueError("SHORT predicate mismatch")
    if any(report[name] != 0 for name in ("post_event_ohlc_rows_read", "returns_computed", "trades_simulated", "profit_factor_computed")):
        raise ValueError("outcome-blind counters are nonzero")


def execute() -> dict[str, Any]:
    prereg = ROOT / PREREG_RELATIVE_PATH
    manifest = ROOT / MANIFEST_RELATIVE_PATH
    h1_path = ROOT / H1_RELATIVE_PATH
    tests = ROOT / TEST_RELATIVE_PATH
    analyzer = Path(__file__).resolve()
    output = ROOT / OUTPUT_RELATIVE_PATH
    if output.exists():
        raise ValueError("source attempt root already exists")
    output.mkdir(parents=True, exist_ok=False)
    started = utc_now()
    start_path = output / "attempt_started.json"
    exclusive_bytes(start_path, json_bytes({
        "schema_version": "bksr002_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "process_id": os.getpid(),
        "status": "CLAIMED_BEFORE_SOURCE_READ",
    }))
    try:
        paths = {"prereg": prereg, "manifest": manifest, "h1_data": h1_path, "analyzer": analyzer, "tests": tests, "formula_dependency": BASE_PATH}
        expected = {"prereg": PREREG_SHA256, "manifest": MANIFEST_SHA256, "h1_data": H1_SHA256, "analyzer": sha256_file(analyzer), "tests": TEST_SHA256, "formula_dependency": BASE_SHA256}
        before = verify_inputs(paths, expected)
        if not set(BASE.H1_COLUMNS) <= set(pq.ParquetFile(h1_path).schema_arrow.names):
            raise ValueError("H1 parquet schema missing required columns")
        frame = pd.read_parquet(h1_path, columns=list(BASE.H1_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        h1 = BASE.validate_h1(frame)
        events, report = analyze_frame(h1)
        assert_outcome_blind(events, report)
        replay_events, replay_report = analyze_frame(h1)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay mismatch")
        after = verify_inputs(paths, expected)
        if before != after:
            raise ValueError("frozen inputs changed during attempt")
        report_path = output / "bksr_002_source_report.json"
        ledger_path = output / "bksr_002_event_ledger.jsonl"
        exclusive_bytes(report_path, json_bytes(report))
        exclusive_bytes(ledger_path, jsonl_bytes(events))
        receipt = {
            "schema_version": "bksr002_source_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "completed_at_utc": utc_now(),
            "bindings": {name: {"path": path.relative_to(ROOT).as_posix(), "sha256": after[name]} for name, path in paths.items()},
            "attempt_started": {"path": start_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(start_path)},
            "report": {"path": report_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(report_path)},
            "event_ledger": {"path": ledger_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(ledger_path)},
            "outcome_blind": True,
            "verdict": report["verdict"],
        }
        receipt_path = output / "source_feasibility_receipt.json"
        exclusive_bytes(receipt_path, json_bytes(receipt))
        terminal_path = output / "attempt_terminal.json"
        exclusive_bytes(terminal_path, json_bytes({
            "schema_version": "bksr002_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": receipt["completed_at_utc"],
            "status": "COMPLETE",
            "verdict": report["verdict"],
            "attempt_started_sha256": sha256_file(start_path),
            "receipt_sha256": sha256_file(receipt_path),
            "same_id_retry_authorized": False,
        }))
        return report
    except Exception as exc:
        terminal_path = output / "attempt_terminal.json"
        if not terminal_path.exists():
            exclusive_bytes(terminal_path, json_bytes({
                "schema_version": "bksr002_source_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "completed_at_utc": utc_now(),
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
                "attempt_started_sha256": sha256_file(start_path),
                "same_id_retry_authorized": False,
            }))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    print(json_bytes(execute()).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
