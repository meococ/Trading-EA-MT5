#!/usr/bin/env python3
"""Outcome-blind H1 Bollinger-Keltner squeeze release with native-M5 decision clock."""

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
HARNESS_RELATIVE_PATH = "03. EA Developer/EA_BillWilliamsAlligatorFractal/research/analyze_bwaf_m5_source.py"
HARNESS_PATH = ROOT / HARNESS_RELATIVE_PATH
HARNESS_SHA256 = "C3F9E73F0F19E276BECE97CE46FC3AF2CED90229B0C7A28C57696A171FDEF602"
_SPEC = importlib.util.spec_from_file_location("bksr_harness_dependency", HARNESS_PATH)
if not _SPEC or not _SPEC.loader:
    raise RuntimeError("unable to load frozen source harness dependency")
BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(BASE)
if BASE.sha256_file(HARNESS_PATH) != HARNESS_SHA256:
    raise RuntimeError("frozen source harness dependency SHA mismatch")

HYPOTHESIS_ID = "HYP-BKSR-XAUUSD-M5-001"
ATTEMPT_ID = "BKSR001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "97E807BDE74ADB213AE01E026603C5149D2E958B8DE37D8FA8F412C3A0CB3E7C"
TEST_SHA256 = "9BCE42530E3880D42EC1E0BC25B107675B27BF31CE01A9005F9BB58332465E2E"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
H1_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
M5_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
MANIFEST_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
H1_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"
M5_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/analyze_bksr_h1_m5_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/tests/test_analyze_bksr_h1_m5_source.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/HYP-BKSR-XAUUSD-M5-001_FROZEN_PREREG.md"
DATA_ACCESS_PREDICATE = "H1_and_M5_time_utc<2023-01-01T00:00:00Z;score_only_H1_2018-01-01T00:00:00Z<=time_utc<2023-01-01T00:00:00Z"
H1_START = pd.Timestamp("2004-06-11T04:00:00Z")
M5_START = pd.Timestamp("2004-06-11T04:15:00Z")
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
LENGTH = 20
BB_MULTIPLIER = 2.0
KC_MULTIPLIER = 1.5
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
H1_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "high", "low", "close")
M5_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous")
EVENT_KEYS = {
    "hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction",
    "squeeze_start_index", "squeeze_end_index", "squeeze_length_bars", "source_bar_index", "squeeze_start_time_utc",
    "source_bar_source_epoch", "decision_source_epoch", "close", "bb_basis",
    "bb_upper", "bb_lower", "kc_upper", "kc_lower",
    "squeeze_end_bb_upper", "squeeze_end_bb_lower", "squeeze_end_kc_upper", "squeeze_end_kc_lower",
}
FALSE_PERMISSIONS = tuple(
    name for name in BASE.FALSE_PERMISSIONS
    if not name.startswith("native_ialligator") and not name.startswith("native_ifractals")
) + (
    "native_ibands_parity_authorized", "native_ima_parity_authorized", "native_iatr_parity_authorized",
    "native_ibands_economic_claim_authorized", "native_ima_economic_claim_authorized", "native_iatr_economic_claim_authorized",
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


def validate_h1(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(H1_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"H1 missing columns: {missing}")
    data = frame.loc[:, H1_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise")
    for name in ("high", "low", "close"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    data = data.reset_index(drop=True)
    if data.empty or data.at[0, "time_utc"] != H1_START or int(data.at[0, "source_epoch"]) % 3600 != 0:
        raise ValueError("H1 frame does not begin at frozen inception")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("H1 reader materialized sealed rows")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any() or not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("H1 clocks must be unique and increasing")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("H1").all() or data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("H1 identity/UTC contract failed")
    high, low, close = (data[name].to_numpy(dtype=float) for name in ("high", "low", "close"))
    valid = np.isfinite(high) & np.isfinite(low) & np.isfinite(close) & (high >= low) & (low <= close) & (close <= high) & (low > 0.0)
    if not valid.all():
        raise ValueError("H1 OHLC chain invalid")
    return data


def validate_m5_clock(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(M5_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"M5 missing columns: {missing}")
    data = frame.loc[:, M5_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise")
    data = data.reset_index(drop=True)
    if data.empty or data.at[0, "time_utc"] != M5_START or int(data.at[0, "source_epoch"]) % 300 != 0:
        raise ValueError("M5 clock does not begin at frozen inception")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("M5 reader materialized sealed rows")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any() or not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("M5 clocks must be unique and increasing")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("M5").all() or data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("M5 identity/UTC contract failed")
    return data


def sma_seeded_ema(values: np.ndarray, period: int) -> np.ndarray:
    source = np.asarray(values, dtype=float)
    result = np.full(len(source), np.nan, dtype=float)
    if len(source) < period:
        return result
    result[period - 1] = float(np.mean(source[:period]))
    alpha = 2.0 / (period + 1.0)
    for index in range(period, len(source)):
        result[index] = result[index - 1] + alpha * (source[index] - result[index - 1])
    return result


def wilder_rma(values: np.ndarray, period: int) -> np.ndarray:
    source = np.asarray(values, dtype=float)
    result = np.full(len(source), np.nan, dtype=float)
    if len(source) < period:
        return result
    result[period - 1] = float(np.mean(source[:period]))
    for index in range(period, len(source)):
        result[index] = ((period - 1) * result[index - 1] + source[index]) / period
    return result


def calculate_bands(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    series = pd.Series(close, dtype=float)
    bb_basis = series.rolling(LENGTH, min_periods=LENGTH).mean().to_numpy(dtype=float)
    deviation = series.rolling(LENGTH, min_periods=LENGTH).std(ddof=0).to_numpy(dtype=float)
    bb_upper = bb_basis + BB_MULTIPLIER * deviation
    bb_lower = bb_basis - BB_MULTIPLIER * deviation
    true_range = np.empty(len(close), dtype=float)
    true_range[0] = high[0] - low[0]
    if len(close) > 1:
        true_range[1:] = np.maximum.reduce((high[1:] - low[1:], np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    kc_basis = sma_seeded_ema(close, LENGTH)
    atr = wilder_rma(true_range, LENGTH)
    kc_upper = kc_basis + KC_MULTIPLIER * atr
    kc_lower = kc_basis - KC_MULTIPLIER * atr
    return bb_basis, bb_upper, bb_lower, kc_upper, kc_lower


def release_signals(data: pd.DataFrame, bands: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> list[dict[str, Any]]:
    basis, bb_upper, bb_lower, kc_upper, kc_lower = bands
    close = data["close"].to_numpy(dtype=float)
    active = False
    start = -1
    rows: list[dict[str, Any]] = []
    for index in range(len(data)):
        ready = all(math.isfinite(value) for value in (basis[index], bb_upper[index], bb_lower[index], kc_upper[index], kc_lower[index]))
        if not ready:
            active = False
            start = -1
            continue
        squeeze_on = bb_lower[index] > kc_lower[index] and bb_upper[index] < kc_upper[index]
        if squeeze_on:
            if not active:
                active = True
                start = index
            continue
        if not active:
            continue
        if close[index] > basis[index]:
            direction = "LONG"
        elif close[index] < basis[index]:
            direction = "SHORT"
        else:
            direction = "NONE"
        if direction != "NONE":
            rows.append({"_index": index, "direction": direction, "squeeze_start": start, "squeeze_end": index - 1, "squeeze_length_bars": index - start, "close": float(close[index]), "bb_basis": float(basis[index]), "bb_upper": float(bb_upper[index]), "bb_lower": float(bb_lower[index]), "kc_upper": float(kc_upper[index]), "kc_lower": float(kc_lower[index]), "squeeze_end_bb_upper": float(bb_upper[index - 1]), "squeeze_end_bb_lower": float(bb_lower[index - 1]), "squeeze_end_kc_upper": float(kc_upper[index - 1]), "squeeze_end_kc_lower": float(kc_lower[index - 1])})
        active = False
        start = -1
    return rows


def analyze_frames(h1: pd.DataFrame, m5_clock: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    h1 = h1.copy().reset_index(drop=True)
    h1["time_utc"] = pd.to_datetime(h1["time_utc"], utc=True, errors="raise")
    m5_clock = m5_clock.copy().reset_index(drop=True)
    m5_clock["time_utc"] = pd.to_datetime(m5_clock["time_utc"], utc=True, errors="raise")
    bands = calculate_bands(h1["high"].to_numpy(dtype=float), h1["low"].to_numpy(dtype=float), h1["close"].to_numpy(dtype=float))
    raw_rows = release_signals(h1, bands)
    design = h1["time_utc"].ge(DESIGN_START) & h1["time_utc"].lt(DESIGN_END)
    usable_values = np.logical_and.reduce(tuple(np.isfinite(values) for values in bands))
    usable = design & pd.Series(usable_values)
    raw_rows = [row for row in raw_rows if bool(design.iloc[row["_index"]]) and bool(usable.iloc[row["_index"]])]
    clock = {timestamp: int(epoch) for timestamp, epoch in zip(m5_clock["time_utc"], m5_clock["source_epoch"], strict=True)}
    events: list[dict[str, Any]] = []
    for row in raw_rows:
        index = int(row["_index"])
        source_time = h1.at[index, "time_utc"]
        decision_time = source_time + pd.Timedelta(hours=1)
        source_epoch = int(h1.at[index, "source_epoch"])
        decision_epoch = clock.get(decision_time)
        if decision_epoch != source_epoch + 3600:
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "decision_time_utc": decision_time.isoformat().replace("+00:00", "Z"),
            "direction": row["direction"],
            "squeeze_start_index": int(row["squeeze_start"]),
            "squeeze_end_index": int(row["squeeze_end"]),
            "squeeze_length_bars": int(row["squeeze_length_bars"]),
            "source_bar_index": index,
            "squeeze_start_time_utc": h1.at[row["squeeze_start"], "time_utc"].isoformat().replace("+00:00", "Z"),
            "source_bar_source_epoch": source_epoch,
            "decision_source_epoch": int(decision_epoch),
            **{name: float(row[name]) for name in ("close", "bb_basis", "bb_upper", "bb_lower", "kc_upper", "kc_lower", "squeeze_end_bb_upper", "squeeze_end_bb_lower", "squeeze_end_kc_upper", "squeeze_end_kc_lower")},
        })
    raw_count = len(raw_rows)
    count = len(events)
    design_rows = int(design.sum())
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, float | int]] = {}
    for year in range(2018, 2023):
        year_count = int((years == year).sum()) if count else 0
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
        "raw_event_exact_m5_decision_coverage": next_coverage >= MIN_NEXT_COVERAGE, "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(MIN_YEAR_CADENCE <= item["cadence_per_week"] <= MAX_YEAR_CADENCE for item in yearly.values()),
        "zero_direction_conflicts": True,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "bksr_h1_m5_source_report.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_H1_BBKC_SQUEEZE_RELEASE_M5_DECISION_AND_CADENCE_ONLY",
        "source_window": {"h1_from": H1_START.isoformat(), "m5_from": M5_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"signal_timeframe": "H1", "decision_timeframe": "M5", "length": LENGTH, "bb_basis": "SMA", "bb_std_ddof": 0, "bb_multiplier": BB_MULTIPLIER, "kc_basis": "SMA-seeded EMA", "atr": "SMA-seeded Wilder RMA", "kc_multiplier": KC_MULTIPLIER, "strict_inside": True, "direction": "release close versus BB basis"},
        "funnel": {"h1_source_rows": int(len(h1)), "m5_clock_rows": int(len(m5_clock)), "prehistory_rows": int((h1["time_utc"] < DESIGN_START).sum()), "design_rows": design_rows, "feature_usable_rows": int(usable.sum()), "raw_events": raw_count, "executable_events": count, "gap_rejected_events": raw_count - count, "direction_conflicts": 0, "long_events": longs, "short_events": shorts},
        "metrics": {"elapsed_weeks": elapsed_weeks, "feature_coverage": feature_coverage, "raw_event_exact_m5_decision_coverage": next_coverage, "event_cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_event_share": max_year_share},
        "yearly": yearly, "gates": gates, "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_PARITY_CHILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_BBKC_SQUEEZE_RELEASE",
        "prohibitions": {"post_event_ohlc_read": False, "m5_prices_read": False, "returns_computed": False, "trades_simulated": False, "pnl_computed": False, "profit_factor_computed": False, "economics_executed": False, "validation_opened": False, "holdout_opened": False, "direct_mql5_parity_authorized_by_attempt": passed, "economic_build_authorized": False, "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError("event ledger violates exact outcome-blind allowlist")
        numeric = ("close", "bb_basis", "bb_upper", "bb_lower", "kc_upper", "kc_lower", "squeeze_end_bb_upper", "squeeze_end_bb_lower", "squeeze_end_kc_upper", "squeeze_end_kc_lower")
        if not all(math.isfinite(float(row[name])) for name in numeric):
            raise ValueError("event ledger contains nonfinite values")
        source = pd.Timestamp(row["source_bar_time_utc"])
        decision = pd.Timestamp(row["decision_time_utc"])
        start_index = int(row["squeeze_start_index"])
        end_index = int(row["squeeze_end_index"])
        source_index = int(row["source_bar_index"])
        temporal = start_index <= end_index and end_index == source_index - 1 and int(row["squeeze_length_bars"]) == end_index - start_index + 1 and pd.Timestamp(row["squeeze_start_time_utc"]) <= source and decision == source + pd.Timedelta(hours=1) and int(row["decision_source_epoch"]) == int(row["source_bar_source_epoch"]) + 3600
        bands = row["bb_lower"] < row["bb_upper"] and row["kc_lower"] < row["kc_upper"]
        last_was_squeeze = row["squeeze_end_bb_lower"] > row["squeeze_end_kc_lower"] and row["squeeze_end_bb_upper"] < row["squeeze_end_kc_upper"]
        release_is_off = not (row["bb_lower"] > row["kc_lower"] and row["bb_upper"] < row["kc_upper"])
        direction = (row["direction"] == "LONG" and row["close"] > row["bb_basis"]) or (row["direction"] == "SHORT" and row["close"] < row["bb_basis"])
        if not temporal or not bands or not last_was_squeeze or not release_is_off or not direction:
            raise ValueError("event ledger violates frozen squeeze-release predicate")
    forbidden = [name for name, value in report["prohibitions"].items() if name != "direct_mql5_parity_authorized_by_attempt" and value is not False]
    if forbidden:
        raise ValueError(f"outcome-blind report contract failed: {forbidden}")


def validate_manifest(manifest_path: Path, h1_path: Path, m5_path: Path) -> None:
    if sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ValueError("manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {"XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet": H1_SHA256, "XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet": M5_SHA256}
    for suffix, digest in expected.items():
        matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith(suffix)]
        if len(matches) != 1 or matches[0].get("sha256") != digest:
            raise ValueError(f"manifest does not bind {suffix}")
    if not h1_path.as_posix().endswith(next(name for name in expected if "_H1_" in name)) or not m5_path.as_posix().endswith(next(name for name in expected if "_M5_" in name)):
        raise ValueError("unexpected source path")


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
    validation, metrics = row.get("validation", {}), row.get("metrics", {})
    checks = {
        "probe": row.get("state") == "probe", "verdict": row.get("verdict") == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256, "run_ids": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID, "limit": validation.get("source_feasibility_attempt_limit") == 1,
        "source": validation.get("source_run_authorized") is True, "source_only": validation.get("source_feasibility_only") is True,
        "prehistory": validation.get("prehistory_source_access_authorized") is True,
        "manifest": validation.get("manifest_path") == MANIFEST_RELATIVE_PATH and validation.get("manifest_sha256") == MANIFEST_SHA256,
        "h1": validation.get("h1_data_path") == H1_RELATIVE_PATH and validation.get("h1_data_sha256") == H1_SHA256,
        "m5": validation.get("m5_clock_path") == M5_RELATIVE_PATH and validation.get("m5_clock_sha256") == M5_SHA256,
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
    exclusive_json(marker, {"schema_version": "bksr_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": authority["analyzer_sha256"], "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"})
    return started, marker


def execute(root: Path) -> dict[str, Any]:
    prereg, manifest = root / PREREG_RELATIVE_PATH, root / MANIFEST_RELATIVE_PATH
    h1_path, m5_path = root / H1_RELATIVE_PATH, root / M5_RELATIVE_PATH
    tests, registry = root / TEST_RELATIVE_PATH, root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_BollingerKeltnerSqueezeRelease/research/evidence/HYP-BKSR-XAUUSD-M5-001/BKSR001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    try:
        frozen_paths = {"preregistration": prereg, "manifest": manifest, "h1_data": h1_path, "m5_clock": m5_path, "analyzer": Path(__file__).resolve(), "tests": tests, "harness": HARNESS_PATH}
        expected = {"preregistration": PREREG_SHA256, "manifest": MANIFEST_SHA256, "h1_data": H1_SHA256, "m5_clock": M5_SHA256, "analyzer": authority["analyzer_sha256"], "tests": TEST_SHA256, "harness": HARNESS_SHA256}
        verify_frozen_inputs(frozen_paths, expected)
        validate_manifest(manifest, h1_path, m5_path)
        if not set(H1_COLUMNS) <= set(pq.ParquetFile(h1_path).schema_arrow.names) or not set(M5_COLUMNS) <= set(pq.ParquetFile(m5_path).schema_arrow.names):
            raise ValueError("Parquet schema missing required columns")
        h1_raw = pd.read_parquet(h1_path, columns=list(H1_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        m5_raw = pd.read_parquet(m5_path, columns=list(M5_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        h1, m5 = validate_h1(h1_raw), validate_m5_clock(m5_raw)
        events, report = analyze_frames(h1, m5)
        assert_outcome_blind(events, report)
        replay_events, replay_report = analyze_frames(h1, m5)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay failed")
        final_hashes = verify_frozen_inputs(frozen_paths, expected)
        report_bytes, ledger_bytes = json_bytes(report), jsonl_bytes(events)
        report_path, ledger_path = output_dir / "bksr_001_source_report.json", output_dir / "bksr_001_event_ledger.jsonl"
        atomic_write(report_path, report_bytes)
        atomic_write(ledger_path, ledger_bytes)
        receipt = {"schema_version": "bksr_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": utc_now(), "bindings": {name: {"path": path.relative_to(root).as_posix(), "sha256": final_hashes[name]} for name, path in frozen_paths.items()}, "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority}, "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)}, "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()}, "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()}, "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "m5_price_columns_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0}, "verdict": report["verdict"]}
        receipt_bytes = json_bytes(receipt)
        receipt_path = output_dir / "source_feasibility_receipt.json"
        atomic_write(receipt_path, receipt_bytes)
        exclusive_json(output_dir / "attempt_terminal.json", {"schema_version": "bksr_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}
    except Exception as exc:
        terminal = output_dir / "attempt_terminal.json"
        if not terminal.exists():
            exclusive_json(terminal, {"schema_version": "bksr_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": utc_now(), "status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
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
