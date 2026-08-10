#!/usr/bin/env python3
"""Outcome-blind native-M5 Awesome Oscillator Twin Peaks source analyzer."""

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
HARNESS_RELATIVE_PATH = "03. EA Developer/EA_TRIXMomentum/research/analyze_trix_m5_source.py"
HARNESS_PATH = ROOT / HARNESS_RELATIVE_PATH
HARNESS_SHA256 = "FD101584D75ECAF98E0FC1E0E353AFF4C68EF51E061AA3FAA50B9EEF6B891AE8"
_SPEC = importlib.util.spec_from_file_location("aotp_harness_dependency", HARNESS_PATH)
if not _SPEC or not _SPEC.loader:
    raise RuntimeError("unable to load frozen source harness dependency")
BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(BASE)
if BASE.sha256_file(HARNESS_PATH) != HARNESS_SHA256:
    raise RuntimeError("frozen source harness dependency SHA mismatch")

HYPOTHESIS_ID = "HYP-AOTP-XAUUSD-M5-001"
ATTEMPT_ID = "AOTP001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "D21E63582575C95AA6B6902159BD711B5F90C0755739FDB61FC888B27C961A43"
TEST_SHA256 = "21D53CDEC4F799363E318D14AB7BED26225323325442DA9592EDF0BC66C137B1"
MANIFEST_SHA256 = BASE.MANIFEST_SHA256
DATA_SHA256 = BASE.DATA_SHA256
MANIFEST_RELATIVE_PATH = BASE.MANIFEST_RELATIVE_PATH
DATA_RELATIVE_PATH = BASE.DATA_RELATIVE_PATH
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_AwesomeOscillatorTwinPeaks/research/analyze_aotp_m5_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_AwesomeOscillatorTwinPeaks/research/tests/test_analyze_aotp_m5_source.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_AwesomeOscillatorTwinPeaks/research/HYP-AOTP-XAUUSD-M5-001_FROZEN_PREREG.md"
DATA_ACCESS_PREDICATE = BASE.DATA_ACCESS_PREDICATE
SOURCE_START = BASE.SOURCE_START
DESIGN_START = BASE.DESIGN_START
DESIGN_END = BASE.DESIGN_END
FAST_PERIOD = 5
SLOW_PERIOD = 34
FIRST_AO_INDEX = 33
FIRST_EVENT_INDEX = 37
MIN_ROWS = 300_000
MIN_FEATURE_COVERAGE = 0.999
MIN_NEXT_COVERAGE = 0.97
MIN_EVENTS = 500
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.30
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "high", "low", "close")
EVENT_KEYS = {
    "hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction",
    "anchor_ao", "left_ao", "pivot_ao", "confirmation_ao",
}
FALSE_PERMISSIONS = tuple(name for name in BASE.FALSE_PERMISSIONS if not name.startswith("native_itrix")) + (
    "native_iao_parity_authorized", "native_iao_economic_claim_authorized",
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
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise")
    for name in ("high", "low", "close"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    data = data.reset_index(drop=True)
    if data.empty or data.at[0, "time_utc"] != SOURCE_START or int(data.at[0, "source_epoch"]) % 300 != 0:
        raise ValueError("source frame does not begin at frozen M5 inception")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("reader materialized rows at or above frozen upper bound")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and strictly increasing")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("M5").all():
        raise ValueError("rows are not exclusively XAUUSD/M5")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    close = data["close"].to_numpy(dtype=float)
    valid = np.isfinite(high) & np.isfinite(low) & np.isfinite(close) & (high >= low) & (low <= close) & (close <= high) & (low > 0.0)
    if not valid.all():
        raise ValueError("full inception OHLC chain must be finite, positive and geometrically valid")
    return data


def calculate_ao(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    median = (np.asarray(high, dtype=float) + np.asarray(low, dtype=float)) / 2.0
    values = pd.Series(median, dtype=float)
    fast = values.rolling(FAST_PERIOD, min_periods=FAST_PERIOD).mean()
    slow = values.rolling(SLOW_PERIOD, min_periods=SLOW_PERIOD).mean()
    return (fast - slow).to_numpy(dtype=float)


def twin_peak_events(ao: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(ao, dtype=float)
    long_event = np.zeros(len(values), dtype=bool)
    short_event = np.zeros(len(values), dtype=bool)
    event_anchor = np.full(len(values), np.nan, dtype=float)
    event_pivot = np.full(len(values), np.nan, dtype=float)
    bullish_anchor = math.nan
    bearish_anchor = math.nan
    for confirmation in range(len(values)):
        current = values[confirmation]
        if not math.isfinite(current) or current == 0.0:
            bullish_anchor = math.nan
            bearish_anchor = math.nan
            continue
        if confirmation < 2 or not math.isfinite(values[confirmation - 1]) or not math.isfinite(values[confirmation - 2]):
            bullish_anchor = math.nan
            bearish_anchor = math.nan
            continue
        left = values[confirmation - 2]
        pivot = values[confirmation - 1]
        if current < 0.0:
            bearish_anchor = math.nan
            if left < 0.0 and pivot < 0.0 and left > pivot < current:
                if math.isfinite(bullish_anchor) and pivot > bullish_anchor:
                    long_event[confirmation] = True
                    event_anchor[confirmation] = bullish_anchor
                    event_pivot[confirmation] = pivot
                bullish_anchor = pivot
        else:
            bullish_anchor = math.nan
            if left > 0.0 and pivot > 0.0 and left < pivot > current:
                if math.isfinite(bearish_anchor) and pivot < bearish_anchor:
                    short_event[confirmation] = True
                    event_anchor[confirmation] = bearish_anchor
                    event_pivot[confirmation] = pivot
                bearish_anchor = pivot
    return long_event, short_event, event_anchor, event_pivot


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    ao_values = calculate_ao(data["high"].to_numpy(dtype=float), data["low"].to_numpy(dtype=float))
    long_values, short_values, anchors, pivots = twin_peak_events(ao_values)
    raw_long = pd.Series(long_values, index=data.index)
    raw_short = pd.Series(short_values, index=data.index)
    design = data["time_utc"].ge(DESIGN_START) & data["time_utc"].lt(DESIGN_END)
    usable = design & np.isfinite(ao_values)
    raw_long &= usable
    raw_short &= usable
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw = raw_long | raw_short
    exact_next = data["source_epoch"].shift(-1).eq(data["source_epoch"] + 300) & ((data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(minutes=5))
    executable = raw & exact_next
    events: list[dict[str, Any]] = []
    for index in data.index[executable]:
        source_time = data.at[index, "time_utc"]
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "decision_time_utc": (source_time + pd.Timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
            "anchor_ao": float(anchors[index]),
            "left_ao": float(ao_values[index - 2]),
            "pivot_ao": float(pivots[index]),
            "confirmation_ao": float(ao_values[index]),
        })
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
        "minimum_design_rows": design_rows >= MIN_ROWS,
        "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_NEXT_COVERAGE,
        "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(MIN_YEAR_CADENCE <= item["cadence_per_week"] <= MAX_YEAR_CADENCE for item in yearly.values()),
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "aotp_m5_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_AO_TWIN_PEAKS_AND_CADENCE_ONLY",
        "source_window": {"from": SOURCE_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"timeframe": "M5", "fast_period": FAST_PERIOD, "slow_period": SLOW_PERIOD, "price": "median", "strict_same_side_twin_peaks": True, "first_ao_index": FIRST_AO_INDEX, "first_possible_event_index": FIRST_EVENT_INDEX, "state_dependency": "inception_or_last_zero_reset"},
        "funnel": {"source_rows": int(len(data)), "prehistory_rows": int((data["time_utc"] < DESIGN_START).sum()), "design_rows": design_rows, "feature_usable_rows": int(usable.sum()), "raw_events": raw_count, "executable_events": count, "gap_rejected_events": raw_count - count, "direction_conflicts": int(conflicts.sum()), "long_events": longs, "short_events": shorts},
        "metrics": {"elapsed_weeks": elapsed_weeks, "feature_coverage": feature_coverage, "raw_event_exact_next_coverage": next_coverage, "event_cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_event_share": max_year_share},
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_AO_TWIN_PEAKS",
        "prohibitions": {"post_event_ohlc_read": False, "returns_computed": False, "trades_simulated": False, "pnl_computed": False, "profit_factor_computed": False, "economics_executed": False, "validation_opened": False, "holdout_opened": False, "direct_mql5_parity_authorized_by_attempt": passed, "economic_build_authorized": False, "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError("event ledger violates exact outcome-blind allowlist")
        if not all(math.isfinite(float(row[name])) for name in ("anchor_ao", "left_ao", "pivot_ao", "confirmation_ao")):
            raise ValueError("event ledger contains nonfinite fields")
        if row["direction"] == "LONG":
            valid = row["anchor_ao"] < row["pivot_ao"] < 0.0 and row["left_ao"] > row["pivot_ao"] < row["confirmation_ao"] < 0.0
        elif row["direction"] == "SHORT":
            valid = row["anchor_ao"] > row["pivot_ao"] > 0.0 and row["left_ao"] < row["pivot_ao"] > row["confirmation_ao"] > 0.0
        else:
            valid = False
        if not valid:
            raise ValueError("event ledger violates strict twin-peaks predicate")
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
        "probe": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "run_ids": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("source_feasibility_attempt_limit") == 1,
        "source": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "prehistory": validation.get("prehistory_source_access_authorized") is True,
        "prehistory_start": validation.get("prehistory_source_start") == SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest": validation.get("manifest_path") == MANIFEST_RELATIVE_PATH and validation.get("manifest_sha256") == MANIFEST_SHA256,
        "data": validation.get("data_path") == DATA_RELATIVE_PATH and validation.get("data_sha256") == DATA_SHA256,
        "predicate": validation.get("data_access_predicate") == DATA_ACCESS_PREDICATE,
        "analyzer": validation.get("reviewed_analyzer_path") == ANALYZER_RELATIVE_PATH and validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "tests": validation.get("reviewed_test_path") == TEST_RELATIVE_PATH and validation.get("reviewed_test_sha256") == TEST_SHA256,
        "harness": validation.get("harness_dependency_path") == HARNESS_RELATIVE_PATH and validation.get("harness_dependency_sha256") == HARNESS_SHA256,
        "zero_metrics": all(metrics.get(name) == 0 for name in ZERO_METRICS),
        "validation_closed": metrics.get("research_validation_opened") is False,
        "holdout_closed": metrics.get("research_holdout_opened") is False,
        "false_permissions": all(validation.get(name) is False for name in FALSE_PERMISSIONS),
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
    exclusive_json(marker, {"schema_version": "aotp_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": authority["analyzer_sha256"], "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"})
    return started, marker


def execute(root: Path) -> dict[str, Any]:
    prereg = root / PREREG_RELATIVE_PATH
    manifest = root / MANIFEST_RELATIVE_PATH
    data_path = root / DATA_RELATIVE_PATH
    tests = root / TEST_RELATIVE_PATH
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_AwesomeOscillatorTwinPeaks/research/evidence/HYP-AOTP-XAUUSD-M5-001/AOTP001-SOURCE-ATTEMPT-001"
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
        report_bytes = json_bytes(report)
        ledger_bytes = jsonl_bytes(events)
        report_path = output_dir / "aotp_001_source_report.json"
        ledger_path = output_dir / "aotp_001_event_ledger.jsonl"
        atomic_write(report_path, report_bytes)
        atomic_write(ledger_path, ledger_bytes)
        receipt = {"schema_version": "aotp_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": utc_now(), "bindings": {name: {"path": path.relative_to(root).as_posix(), "sha256": final_hashes[name]} for name, path in frozen_paths.items()}, "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority}, "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)}, "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()}, "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()}, "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0}, "verdict": report["verdict"]}
        receipt_bytes = json_bytes(receipt)
        receipt_path = output_dir / "source_feasibility_receipt.json"
        atomic_write(receipt_path, receipt_bytes)
        exclusive_json(output_dir / "attempt_terminal.json", {"schema_version": "aotp_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}
    except Exception as exc:
        terminal = output_dir / "attempt_terminal.json"
        if not terminal.exists():
            exclusive_json(terminal, {"schema_version": "aotp_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": utc_now(), "status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = execute(Path(__file__).resolve().parents[3])
    print(json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
