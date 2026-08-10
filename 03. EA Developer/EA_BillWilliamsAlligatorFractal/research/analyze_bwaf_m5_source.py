#!/usr/bin/env python3
"""Outcome-blind native-M5 Bill Williams Alligator-Fractal source analyzer."""

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
HARNESS_RELATIVE_PATH = "03. EA Developer/EA_AwesomeOscillatorTwinPeaks/research/analyze_aotp_m5_source.py"
HARNESS_PATH = ROOT / HARNESS_RELATIVE_PATH
HARNESS_SHA256 = "0D6581D275EAEE325AB4BC7E28C0676E4E1A23BF156B0AB7C1447D59F805D763"
_SPEC = importlib.util.spec_from_file_location("bwaf_harness_dependency", HARNESS_PATH)
if not _SPEC or not _SPEC.loader:
    raise RuntimeError("unable to load frozen source harness dependency")
BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(BASE)
if BASE.sha256_file(HARNESS_PATH) != HARNESS_SHA256:
    raise RuntimeError("frozen source harness dependency SHA mismatch")

HYPOTHESIS_ID = "HYP-BWAF-XAUUSD-M5-001"
ATTEMPT_ID = "BWAF001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "02B0104E88852AEA480DC26CF336FE82AF0C46E734601599029C8B7CA9DBAEA4"
TEST_SHA256 = "C1E58D6C1A19E6B192965BD64D2BEAC43E91E995BB03DB2B1774D942576470F7"
MANIFEST_SHA256 = BASE.MANIFEST_SHA256
DATA_SHA256 = BASE.DATA_SHA256
MANIFEST_RELATIVE_PATH = BASE.MANIFEST_RELATIVE_PATH
DATA_RELATIVE_PATH = BASE.DATA_RELATIVE_PATH
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_BillWilliamsAlligatorFractal/research/analyze_bwaf_m5_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_BillWilliamsAlligatorFractal/research/tests/test_analyze_bwaf_m5_source.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_BillWilliamsAlligatorFractal/research/HYP-BWAF-XAUUSD-M5-001_FROZEN_PREREG.md"
DATA_ACCESS_PREDICATE = BASE.DATA_ACCESS_PREDICATE
SOURCE_START = BASE.SOURCE_START
DESIGN_START = BASE.DESIGN_START
DESIGN_END = BASE.DESIGN_END
JAW_PERIOD, JAW_SHIFT = 13, 8
TEETH_PERIOD, TEETH_SHIFT = 8, 5
LIPS_PERIOD, LIPS_SHIFT = 5, 3
FIRST_ALIGNMENT_INDEX = 21
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
    "regime_start_time_utc", "fractal_pivot_time_utc", "fractal_confirmation_time_utc",
    "regime_start_index", "fractal_pivot_index", "fractal_confirmation_index", "source_bar_index",
    "source_bar_source_epoch", "decision_source_epoch",
    "anchor_price", "pivot_teeth", "prior_jaw", "prior_teeth", "prior_lips",
    "jaw", "teeth", "lips", "breakout_extreme",
}
FALSE_PERMISSIONS = tuple(name for name in BASE.FALSE_PERMISSIONS if not name.startswith("native_iao")) + (
    "native_ialligator_parity_authorized", "native_ifractals_parity_authorized",
    "native_ialligator_economic_claim_authorized", "native_ifractals_economic_claim_authorized",
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


def smma(values: np.ndarray, period: int) -> np.ndarray:
    source = np.asarray(values, dtype=float)
    result = np.full(len(source), np.nan, dtype=float)
    if len(source) < period:
        return result
    result[period - 1] = float(np.mean(source[:period]))
    for index in range(period, len(source)):
        result[index] = ((period - 1) * result[index - 1] + source[index]) / period
    return result


def displayed(raw: np.ndarray, shift: int) -> np.ndarray:
    result = np.full(len(raw), np.nan, dtype=float)
    if shift < len(raw):
        result[shift:] = raw[:-shift]
    return result


def calculate_alligator(high: np.ndarray, low: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    median = (np.asarray(high, dtype=float) + np.asarray(low, dtype=float)) / 2.0
    jaw = displayed(smma(median, JAW_PERIOD), JAW_SHIFT)
    teeth = displayed(smma(median, TEETH_PERIOD), TEETH_SHIFT)
    lips = displayed(smma(median, LIPS_PERIOD), LIPS_SHIFT)
    return jaw, teeth, lips


def strict_upper_fractal(high: np.ndarray, center: int) -> bool:
    return center >= 2 and center + 2 < len(high) and all(high[center] > high[index] for index in (center - 2, center - 1, center + 1, center + 2))


def strict_lower_fractal(low: np.ndarray, center: int) -> bool:
    return center >= 2 and center + 2 < len(low) and all(low[center] < low[index] for index in (center - 2, center - 1, center + 1, center + 2))


def raw_signals(data: pd.DataFrame, jaw: np.ndarray, teeth: np.ndarray, lips: np.ndarray) -> list[dict[str, Any]]:
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    mode: str | None = None
    regime_start = -1
    anchor = math.nan
    anchor_pivot = -1
    anchor_confirmation = -1
    consumed = False
    for index in range(len(data)):
        lines_ready = index > 0 and all(math.isfinite(value) for value in (jaw[index], teeth[index], lips[index], jaw[index - 1], teeth[index - 1], lips[index - 1]))
        bull = lines_ready and lips[index] > teeth[index] > jaw[index] and lips[index] > lips[index - 1] and teeth[index] > teeth[index - 1] and jaw[index] > jaw[index - 1]
        bear = lines_ready and lips[index] < teeth[index] < jaw[index] and lips[index] < lips[index - 1] and teeth[index] < teeth[index - 1] and jaw[index] < jaw[index - 1]
        desired = "BULL" if bull else "BEAR" if bear else None
        if desired != mode:
            mode = desired
            regime_start = index if mode else -1
            anchor = math.nan
            anchor_pivot = -1
            anchor_confirmation = -1
            consumed = False
        if mode == "BULL" and not consumed and math.isfinite(anchor) and index > anchor_confirmation and high[index] > anchor:
            rows.append({"_index": index, "direction": "LONG", "regime_start": regime_start, "pivot": anchor_pivot, "confirmation": anchor_confirmation, "anchor_price": anchor, "pivot_teeth": float(teeth[anchor_pivot]), "prior_jaw": float(jaw[index - 1]), "prior_teeth": float(teeth[index - 1]), "prior_lips": float(lips[index - 1]), "jaw": float(jaw[index]), "teeth": float(teeth[index]), "lips": float(lips[index]), "breakout_extreme": float(high[index])})
            consumed = True
            anchor = math.nan
        elif mode == "BEAR" and not consumed and math.isfinite(anchor) and index > anchor_confirmation and low[index] < anchor:
            rows.append({"_index": index, "direction": "SHORT", "regime_start": regime_start, "pivot": anchor_pivot, "confirmation": anchor_confirmation, "anchor_price": anchor, "pivot_teeth": float(teeth[anchor_pivot]), "prior_jaw": float(jaw[index - 1]), "prior_teeth": float(teeth[index - 1]), "prior_lips": float(lips[index - 1]), "jaw": float(jaw[index]), "teeth": float(teeth[index]), "lips": float(lips[index]), "breakout_extreme": float(low[index])})
            consumed = True
            anchor = math.nan
        if mode is None or consumed or math.isfinite(anchor) or index < 4:
            continue
        pivot = index - 2
        if pivot < regime_start:
            continue
        if mode == "BULL" and strict_upper_fractal(high, pivot) and math.isfinite(teeth[pivot]) and high[pivot] > teeth[pivot]:
            anchor = float(high[pivot])
            anchor_pivot = pivot
            anchor_confirmation = index
        elif mode == "BEAR" and strict_lower_fractal(low, pivot) and math.isfinite(teeth[pivot]) and low[pivot] < teeth[pivot]:
            anchor = float(low[pivot])
            anchor_pivot = pivot
            anchor_confirmation = index
    return rows


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    jaw, teeth, lips = calculate_alligator(data["high"].to_numpy(dtype=float), data["low"].to_numpy(dtype=float))
    raw_rows = raw_signals(data, jaw, teeth, lips)
    design = data["time_utc"].ge(DESIGN_START) & data["time_utc"].lt(DESIGN_END)
    usable = design & np.isfinite(jaw) & np.isfinite(teeth) & np.isfinite(lips) & pd.Series(np.r_[False, np.isfinite(jaw[:-1]) & np.isfinite(teeth[:-1]) & np.isfinite(lips[:-1])])
    raw_rows = [row for row in raw_rows if bool(design.iloc[row["_index"]]) and bool(usable.iloc[row["_index"]])]
    by_index: dict[int, set[str]] = {}
    for row in raw_rows:
        by_index.setdefault(int(row["_index"]), set()).add(str(row["direction"]))
    conflicts = {index for index, directions in by_index.items() if len(directions) != 1}
    raw_rows = [row for row in raw_rows if int(row["_index"]) not in conflicts]
    exact_next = data["source_epoch"].shift(-1).eq(data["source_epoch"] + 300) & ((data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(minutes=5))
    executable = [row for row in raw_rows if bool(exact_next.iloc[row["_index"]])]
    events: list[dict[str, Any]] = []
    for row in executable:
        index = int(row["_index"])
        source_time = data.at[index, "time_utc"]
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "decision_time_utc": (source_time + pd.Timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "direction": row["direction"],
            "regime_start_time_utc": data.at[row["regime_start"], "time_utc"].isoformat().replace("+00:00", "Z"),
            "fractal_pivot_time_utc": data.at[row["pivot"], "time_utc"].isoformat().replace("+00:00", "Z"),
            "fractal_confirmation_time_utc": data.at[row["confirmation"], "time_utc"].isoformat().replace("+00:00", "Z"),
            "regime_start_index": int(row["regime_start"]),
            "fractal_pivot_index": int(row["pivot"]),
            "fractal_confirmation_index": int(row["confirmation"]),
            "source_bar_index": index,
            "source_bar_source_epoch": int(data.at[index, "source_epoch"]),
            "decision_source_epoch": int(data.at[index + 1, "source_epoch"]),
            **{name: float(row[name]) for name in ("anchor_price", "pivot_teeth", "prior_jaw", "prior_teeth", "prior_lips", "jaw", "teeth", "lips", "breakout_extreme")},
        })
    raw_count = len(raw_rows)
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
        "zero_direction_conflicts": len(conflicts) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "bwaf_m5_source_report.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_BW_ALLIGATOR_FRACTAL_REGIME_BREAKOUT_AND_CADENCE_ONLY",
        "source_window": {"from": SOURCE_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"timeframe": "M5", "price": "median", "jaw": {"period": 13, "shift": 8}, "teeth": {"period": 8, "shift": 5}, "lips": {"period": 5, "shift": 3}, "smma_seed": "SMA", "fractal_neighbors_each_side": 2, "strict_ties": True, "first_alignment_index": FIRST_ALIGNMENT_INDEX, "one_event_per_opening_regime": True},
        "funnel": {"source_rows": int(len(data)), "prehistory_rows": int((data["time_utc"] < DESIGN_START).sum()), "design_rows": design_rows, "feature_usable_rows": int(usable.sum()), "raw_events": raw_count, "executable_events": count, "gap_rejected_events": raw_count - count, "direction_conflicts": len(conflicts), "long_events": longs, "short_events": shorts},
        "metrics": {"elapsed_weeks": elapsed_weeks, "feature_coverage": feature_coverage, "raw_event_exact_next_coverage": next_coverage, "event_cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_event_share": max_year_share},
        "yearly": yearly, "gates": gates, "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_BW_ALLIGATOR_FRACTAL_REGIME_BREAKOUT",
        "prohibitions": {"post_event_ohlc_read": False, "returns_computed": False, "trades_simulated": False, "pnl_computed": False, "profit_factor_computed": False, "economics_executed": False, "validation_opened": False, "holdout_opened": False, "direct_mql5_parity_authorized_by_attempt": passed, "economic_build_authorized": False, "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError("event ledger violates exact outcome-blind allowlist")
        numeric = ("anchor_price", "pivot_teeth", "prior_jaw", "prior_teeth", "prior_lips", "jaw", "teeth", "lips", "breakout_extreme")
        if not all(math.isfinite(float(row[name])) for name in numeric):
            raise ValueError("event ledger contains nonfinite fields")
        regime = pd.Timestamp(row["regime_start_time_utc"])
        pivot = pd.Timestamp(row["fractal_pivot_time_utc"])
        confirmation = pd.Timestamp(row["fractal_confirmation_time_utc"])
        source = pd.Timestamp(row["source_bar_time_utc"])
        decision = pd.Timestamp(row["decision_time_utc"])
        indices = (int(row["regime_start_index"]), int(row["fractal_pivot_index"]), int(row["fractal_confirmation_index"]), int(row["source_bar_index"]))
        temporal = (
            indices[0] <= indices[1]
            and indices[2] == indices[1] + 2
            and indices[3] > indices[2]
            and regime <= pivot <= confirmation < source
            and decision == source + pd.Timedelta(minutes=5)
            and int(row["decision_source_epoch"]) == int(row["source_bar_source_epoch"]) + 300
        )
        if row["direction"] == "LONG":
            predicate = row["lips"] > row["teeth"] > row["jaw"] and row["lips"] > row["prior_lips"] and row["teeth"] > row["prior_teeth"] and row["jaw"] > row["prior_jaw"] and row["anchor_price"] > row["pivot_teeth"] and row["breakout_extreme"] > row["anchor_price"]
        elif row["direction"] == "SHORT":
            predicate = row["lips"] < row["teeth"] < row["jaw"] and row["lips"] < row["prior_lips"] and row["teeth"] < row["prior_teeth"] and row["jaw"] < row["prior_jaw"] and row["anchor_price"] < row["pivot_teeth"] and row["breakout_extreme"] < row["anchor_price"]
        else:
            predicate = False
        if not temporal or not predicate:
            raise ValueError("event ledger violates frozen Bill Williams predicate")
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
        "prehistory": validation.get("prehistory_source_access_authorized") is True,
        "prehistory_start": validation.get("prehistory_source_start") == SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest": validation.get("manifest_path") == MANIFEST_RELATIVE_PATH and validation.get("manifest_sha256") == MANIFEST_SHA256,
        "data": validation.get("data_path") == DATA_RELATIVE_PATH and validation.get("data_sha256") == DATA_SHA256,
        "predicate": validation.get("data_access_predicate") == DATA_ACCESS_PREDICATE,
        "analyzer": validation.get("reviewed_analyzer_path") == ANALYZER_RELATIVE_PATH and validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "tests": validation.get("reviewed_test_path") == TEST_RELATIVE_PATH and validation.get("reviewed_test_sha256") == TEST_SHA256,
        "harness": validation.get("harness_dependency_path") == HARNESS_RELATIVE_PATH and validation.get("harness_dependency_sha256") == HARNESS_SHA256,
        "zero_metrics": all(metrics.get(name) == 0 for name in ZERO_METRICS),
        "validation_closed": metrics.get("research_validation_opened") is False, "holdout_closed": metrics.get("research_holdout_opened") is False,
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
    exclusive_json(marker, {"schema_version": "bwaf_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": authority["analyzer_sha256"], "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"})
    return started, marker


def execute(root: Path) -> dict[str, Any]:
    prereg = root / PREREG_RELATIVE_PATH
    manifest = root / MANIFEST_RELATIVE_PATH
    data_path = root / DATA_RELATIVE_PATH
    tests = root / TEST_RELATIVE_PATH
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_BillWilliamsAlligatorFractal/research/evidence/HYP-BWAF-XAUUSD-M5-001/BWAF001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    try:
        frozen_paths = {"preregistration": prereg, "manifest": manifest, "data": data_path, "analyzer": Path(__file__).resolve(), "tests": tests, "harness": HARNESS_PATH}
        expected = {"preregistration": PREREG_SHA256, "manifest": MANIFEST_SHA256, "data": DATA_SHA256, "analyzer": authority["analyzer_sha256"], "tests": TEST_SHA256, "harness": HARNESS_SHA256}
        verify_frozen_inputs(frozen_paths, expected)
        BASE.BASE.validate_manifest(manifest, data_path)
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
        report_path = output_dir / "bwaf_001_source_report.json"
        ledger_path = output_dir / "bwaf_001_event_ledger.jsonl"
        atomic_write(report_path, report_bytes)
        atomic_write(ledger_path, ledger_bytes)
        receipt = {"schema_version": "bwaf_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": utc_now(), "bindings": {name: {"path": path.relative_to(root).as_posix(), "sha256": final_hashes[name]} for name, path in frozen_paths.items()}, "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority}, "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)}, "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()}, "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()}, "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0}, "verdict": report["verdict"]}
        receipt_bytes = json_bytes(receipt)
        receipt_path = output_dir / "source_feasibility_receipt.json"
        atomic_write(receipt_path, receipt_bytes)
        exclusive_json(output_dir / "attempt_terminal.json", {"schema_version": "bwaf_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}
    except Exception as exc:
        terminal = output_dir / "attempt_terminal.json"
        if not terminal.exists():
            exclusive_json(terminal, {"schema_version": "bwaf_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": utc_now(), "status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
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
