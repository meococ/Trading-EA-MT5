#!/usr/bin/env python3
"""Outcome-blind native-H1 perfected Setup-9 source analyzer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[3]
HARNESS_RELATIVE_PATH = "03. EA Developer/EA_WilliamsPercentRange/research/analyze_wpr_h1_source.py"
HARNESS_PATH = ROOT / HARNESS_RELATIVE_PATH
HARNESS_SHA256 = "F605A5336C1BB08B97ABD7D1758B77B707A2C3B02B64B99466E59CF70F4463F8"
_SPEC = importlib.util.spec_from_file_location("td9_harness_dependency", HARNESS_PATH)
if not _SPEC or not _SPEC.loader:
    raise RuntimeError("unable to load frozen source harness dependency")
BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(BASE)
if BASE.sha256_file(HARNESS_PATH) != HARNESS_SHA256:
    raise RuntimeError("frozen source harness dependency SHA mismatch")

HYPOTHESIS_ID = "HYP-TD9-XAUUSD-H1-001"
ATTEMPT_ID = "TD9001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "AF4CC69EE04046290425C9A29F53A0EC67BE48E0544279A252112891A97C6425"
TEST_SHA256 = "698B70DF03FE1A0B2CC7A9F824B581DD38531C4E1B632BB7A1C764B7DF7445C7"
MANIFEST_SHA256 = BASE.MANIFEST_SHA256
DATA_SHA256 = BASE.DATA_SHA256
MANIFEST_RELATIVE_PATH = BASE.MANIFEST_RELATIVE_PATH
DATA_RELATIVE_PATH = BASE.DATA_RELATIVE_PATH
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_TDSetup9Exhaustion/research/analyze_td9_h1_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_TDSetup9Exhaustion/research/tests/test_analyze_td9_h1_source.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_TDSetup9Exhaustion/research/HYP-TD9-XAUUSD-H1-001_FROZEN_PREREG.md"
DATA_ACCESS_PREDICATE = BASE.DATA_ACCESS_PREDICATE
SOURCE_START = BASE.SOURCE_START
DESIGN_START = BASE.DESIGN_START
DESIGN_END = BASE.DESIGN_END
FIRST_EVENT_INDEX = 12
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
REQUIRED_COLUMNS = BASE.REQUIRED_COLUMNS
EVENT_KEYS = {"hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction", "setup_count", "close", "close_four_back", "perfection_late_extreme", "perfection_reference_extreme"}
FALSE_PERMISSIONS = tuple(name for name in BASE.FALSE_PERMISSIONS if not name.startswith("native_iwpr")) + (
    "direct_mql5_parity_authorized", "direct_mql5_economic_claim_authorized",
)
ZERO_METRICS = BASE.ZERO_METRICS
sha256_file = BASE.sha256_file
json_bytes = BASE.json_bytes
jsonl_bytes = BASE.jsonl_bytes
atomic_write = BASE.atomic_write
exclusive_json = BASE.exclusive_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_frozen_inputs(paths: dict[str, Path], expected: dict[str, str]) -> dict[str, str]:
    if set(paths) != set(expected):
        raise ValueError("frozen input labels differ")
    observed = {name: sha256_file(path) for name, path in paths.items()}
    mismatch = sorted(name for name in paths if observed[name] != expected[name])
    if mismatch:
        raise ValueError(f"frozen input SHA mismatch: {mismatch}")
    return observed


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return BASE.validate_frame(frame)


def setup_events(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    size = len(close)
    long_event = np.zeros(size, dtype=bool)
    short_event = np.zeros(size, dtype=bool)
    late_extreme = np.full(size, np.nan, dtype=float)
    reference_extreme = np.full(size, np.nan, dtype=float)
    buy_count = 0
    sell_count = 0
    for index in range(4, size):
        if close[index] < close[index - 4]:
            buy_count += 1
            sell_count = 0
            if buy_count == 9:
                late = min(low[index - 1], low[index])
                reference = min(low[index - 3], low[index - 2])
                late_extreme[index] = late
                reference_extreme[index] = reference
                long_event[index] = late < reference
        elif close[index] > close[index - 4]:
            sell_count += 1
            buy_count = 0
            if sell_count == 9:
                late = max(high[index - 1], high[index])
                reference = max(high[index - 3], high[index - 2])
                late_extreme[index] = late
                reference_extreme[index] = reference
                short_event[index] = late > reference
        else:
            buy_count = 0
            sell_count = 0
    return long_event, short_event, late_extreme, reference_extreme


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    close = data["close"].to_numpy(dtype=float)
    long_values, short_values, late, reference = setup_events(high, low, close)
    raw_long = pd.Series(long_values, index=data.index)
    raw_short = pd.Series(short_values, index=data.index)
    design = data["time_utc"].ge(DESIGN_START) & data["time_utc"].lt(DESIGN_END)
    usable = design & (data.index >= FIRST_EVENT_INDEX)
    raw_long &= usable
    raw_short &= usable
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw = raw_long | raw_short
    exact_next = data["source_epoch"].shift(-1).eq(data["source_epoch"] + 3600) & ((data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(hours=1))
    executable = raw & exact_next
    events: list[dict[str, Any]] = []
    for index in data.index[executable]:
        source_time = data.at[index, "time_utc"]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (source_time + pd.Timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
                "setup_count": 9,
                "close": float(close[index]),
                "close_four_back": float(close[index - 4]),
                "perfection_late_extreme": float(late[index]),
                "perfection_reference_extreme": float(reference[index]),
            }
        )
    raw_count = int(raw.sum())
    count = len(events)
    design_rows = int(design.sum())
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    event_years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, float | int]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {"events": year_count, "elapsed_weeks": weeks, "cadence_per_week": year_count / weeks, "share": year_count / count if count else 0.0}
    feature_coverage = int(usable.sum()) / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    cadence = count / elapsed_weeks
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    max_year_share = max((item["share"] for item in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": design_rows >= MIN_ROWS, "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_NEXT_COVERAGE, "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(MIN_YEAR_CADENCE <= item["cadence_per_week"] <= MAX_YEAR_CADENCE for item in yearly.values()),
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "td9_h1_source_report.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_TD9_PERFECTED_SETUP_AND_CADENCE_ONLY",
        "source_window": {"from": SOURCE_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()}, "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"timeframe": "H1", "setup_count": 9, "compare_lag": 4, "strict_setup": True, "strict_perfection": True, "delayed_perfection": False, "first_event_index": FIRST_EVENT_INDEX},
        "funnel": {"source_rows": int(len(data)), "prehistory_rows": int((data["time_utc"] < DESIGN_START).sum()), "design_rows": design_rows, "feature_usable_rows": int(usable.sum()), "raw_events": raw_count, "executable_events": count, "gap_rejected_events": raw_count - count, "direction_conflicts": int(conflicts.sum()), "long_events": longs, "short_events": shorts},
        "metrics": {"elapsed_weeks": elapsed_weeks, "feature_coverage": feature_coverage, "raw_event_exact_next_coverage": next_coverage, "event_cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_event_share": max_year_share},
        "yearly": yearly, "gates": gates, "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_TD9_PERFECTED_SETUP",
        "prohibitions": {"post_event_ohlc_read": False, "returns_computed": False, "trades_simulated": False, "pnl_computed": False, "profit_factor_computed": False, "economics_executed": False, "validation_opened": False, "holdout_opened": False, "direct_mql5_parity_authorized_by_attempt": passed, "economic_build_authorized": False, "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS or row["setup_count"] != 9:
            raise ValueError("event ledger violates exact outcome-blind allowlist")
        if not all(math.isfinite(float(row[name])) for name in ("close", "close_four_back", "perfection_late_extreme", "perfection_reference_extreme")):
            raise ValueError("event ledger contains nonfinite fields")
    forbidden = [name for name, value in report["prohibitions"].items() if name != "direct_mql5_parity_authorized_by_attempt" and value is not False]
    if forbidden:
        raise ValueError(f"outcome-blind report contract failed: {forbidden}")


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    registry_bytes = registry_path.read_bytes()
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_bytes.splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing registry authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "probe": row.get("state") == "probe", "verdict": row.get("verdict") == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256, "run_ids": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID, "limit": validation.get("source_feasibility_attempt_limit") == 1,
        "source": validation.get("source_run_authorized") is True, "source_only": validation.get("source_feasibility_only") is True,
        "prehistory": validation.get("prehistory_source_access_authorized") is True, "prehistory_start": validation.get("prehistory_source_start") == SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest": validation.get("manifest_path") == MANIFEST_RELATIVE_PATH and validation.get("manifest_sha256") == MANIFEST_SHA256,
        "data": validation.get("data_path") == DATA_RELATIVE_PATH and validation.get("data_sha256") == DATA_SHA256,
        "predicate": validation.get("data_access_predicate") == DATA_ACCESS_PREDICATE,
        "analyzer": validation.get("reviewed_analyzer_path") == ANALYZER_RELATIVE_PATH and validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "tests": validation.get("reviewed_test_path") == TEST_RELATIVE_PATH and validation.get("reviewed_test_sha256") == TEST_SHA256,
        "harness": validation.get("harness_dependency_path") == HARNESS_RELATIVE_PATH and validation.get("harness_dependency_sha256") == HARNESS_SHA256,
        "zero_metrics": all(metrics.get(name) == 0 for name in ZERO_METRICS), "validation_closed": metrics.get("research_validation_opened") is False,
        "holdout_closed": metrics.get("research_holdout_opened") is False, "false_permissions": all(validation.get(name) is False for name in FALSE_PERMISSIONS),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {"registry_sha256": hashlib.sha256(registry_bytes).hexdigest().upper(), "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(), "analyzer_sha256": sha256_file(Path(__file__).resolve())}


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    marker = output_dir / "attempt_started.json"
    exclusive_json(marker, {"schema_version": "td9_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": authority["analyzer_sha256"], "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"})
    return started, marker


def execute(root: Path) -> dict[str, Any]:
    prereg = root / PREREG_RELATIVE_PATH
    manifest = root / MANIFEST_RELATIVE_PATH
    data_path = root / DATA_RELATIVE_PATH
    tests = root / TEST_RELATIVE_PATH
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_TDSetup9Exhaustion/research/evidence/HYP-TD9-XAUUSD-H1-001/TD9001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    try:
        frozen_paths = {"preregistration": prereg, "manifest": manifest, "data": data_path, "analyzer": Path(__file__).resolve(), "tests": tests, "harness": HARNESS_PATH}
        expected = {"preregistration": PREREG_SHA256, "manifest": MANIFEST_SHA256, "data": DATA_SHA256, "analyzer": authority["analyzer_sha256"], "tests": TEST_SHA256, "harness": HARNESS_SHA256}
        verify_frozen_inputs(frozen_paths, expected)
        BASE.validate_manifest(manifest, data_path)
        if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
            raise ValueError("Parquet schema missing required columns")
        raw = pd.read_parquet(data_path, columns=list(REQUIRED_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        selected = validate_frame(raw)
        events, report = analyze_frame(selected)
        assert_outcome_blind(events, report)
        replay_events, replay_report = analyze_frame(selected)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay failed")
        final_hashes = verify_frozen_inputs(frozen_paths, expected)
        report_bytes = json_bytes(report); ledger_bytes = jsonl_bytes(events)
        report_path = output_dir / "td9_001_source_report.json"; ledger_path = output_dir / "td9_001_event_ledger.jsonl"
        atomic_write(report_path, report_bytes); atomic_write(ledger_path, ledger_bytes)
        receipt = {"schema_version": "td9_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": utc_now(), "bindings": {name: {"path": path.relative_to(root).as_posix(), "sha256": final_hashes[name]} for name, path in frozen_paths.items()}, "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority}, "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)}, "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()}, "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()}, "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0}, "verdict": report["verdict"]}
        receipt_bytes = json_bytes(receipt); receipt_path = output_dir / "source_feasibility_receipt.json"; atomic_write(receipt_path, receipt_bytes)
        exclusive_json(output_dir / "attempt_terminal.json", {"schema_version": "td9_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}
    except Exception as exc:
        terminal = output_dir / "attempt_terminal.json"
        if not terminal.exists():
            exclusive_json(terminal, {"schema_version": "td9_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": utc_now(), "status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--execute", action="store_true"); args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = execute(Path(__file__).resolve().parents[3]); print(json_bytes(result["report"]).decode("utf-8"), end=""); return 0


if __name__ == "__main__":
    raise SystemExit(main())
