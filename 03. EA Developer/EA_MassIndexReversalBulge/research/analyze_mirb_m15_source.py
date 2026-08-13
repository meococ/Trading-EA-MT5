#!/usr/bin/env python3
"""Outcome-blind EURUSD M15 Mass Index reversal-bulge source screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-MIRB-EURUSD-M15-001"
ATTEMPT_ID = "MIRB001-SOURCE-001"
ROOT = Path(__file__).resolve().parents[3]
PREREG = ROOT / "03. EA Developer/EA_MassIndexReversalBulge/research/HYP-MIRB-EURUSD-M15-001_FROZEN_SOURCE_PREREG.md"
TEST = ROOT / "03. EA Developer/EA_MassIndexReversalBulge/research/tests/test_analyze_mirb_m15_source.py"
MANIFEST = ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
DATA = ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8"
SOURCE_START = pd.Timestamp("2015-01-01T00:00:00Z")
DESIGN_START = pd.Timestamp("2016-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
EMA_LENGTH = 9
MASS_LENGTH = 25
UPPER = 27.0
LOWER = 26.5
MIN_ROWS = 190_000
MIN_FEATURE_COVERAGE = 0.99
MIN_NEXT_COVERAGE = 0.97
MIN_EVENTS = 730
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.20
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "open", "high", "low", "close")
EVENT_KEYS = {
    "hypothesis_id", "source_epoch", "source_bar_time_utc", "decision_time_utc",
    "direction", "mass_index", "prior_close_ema9", "close_ema9",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def ema_sma_seed(values: pd.Series, length: int) -> pd.Series:
    source = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    result = np.full(len(source), np.nan, dtype=float)
    seed: list[float] = []
    prior = math.nan
    alpha = 2.0 / (length + 1.0)
    for index, value in enumerate(source):
        if not math.isfinite(value):
            seed.clear()
            prior = math.nan
            continue
        if not math.isfinite(prior):
            seed.append(float(value))
            if len(seed) < length:
                continue
            if len(seed) > length:
                seed = seed[-length:]
            prior = float(sum(seed) / length)
        else:
            prior = float(value * alpha + prior * (1.0 - alpha))
        result[index] = prior
    return pd.Series(result, index=values.index, dtype=float)


def aggregate_complete_m15(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise").astype("int64")
    if not data["symbol"].eq("EURUSD").all() or not data["timeframe"].eq("M5").all():
        raise ValueError("source must contain only EURUSD/M5")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be strictly increasing and unique")
    if (data["time_utc"] < SOURCE_START).any() or (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("reader materialized rows outside the frozen source window")
    for column in ("open", "high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["bucket"] = (data["source_epoch"] // 900) * 900
    rows: list[dict[str, Any]] = []
    for bucket, group in data.groupby("bucket", sort=True):
        group = group.sort_values("source_epoch").reset_index(drop=True)
        epochs = group["source_epoch"].to_numpy(dtype=np.int64)
        exact = len(group) == 3 and np.array_equal(epochs, np.array([bucket, bucket + 300, bucket + 600], dtype=np.int64))
        times = group["time_utc"].astype("int64").to_numpy()
        exact_time = len(group) == 3 and np.array_equal(
            np.diff(times), np.array([300, 300], dtype=np.int64) * 1_000_000_000
        )
        prices = group.loc[:, ["open", "high", "low", "close"]].to_numpy(dtype=float)
        price_valid = len(group) == 3 and np.isfinite(prices).all() and np.all(prices[:, 0] > 0.0)
        price_valid = bool(price_valid and np.all(prices[:, 1] >= prices[:, 2])
                           and np.all(prices[:, 0] >= prices[:, 2]) and np.all(prices[:, 0] <= prices[:, 1])
                           and np.all(prices[:, 3] >= prices[:, 2]) and np.all(prices[:, 3] <= prices[:, 1]))
        valid = bool(exact and exact_time and price_valid)
        bucket_time = group.at[0, "time_utc"] - pd.Timedelta(seconds=int(group.at[0, "source_epoch"] - bucket))
        rows.append({
            "source_epoch": int(bucket), "time_utc": bucket_time,
            "open": float(group.at[0, "open"]) if valid else math.nan,
            "high": float(group["high"].max()) if valid else math.nan,
            "low": float(group["low"].min()) if valid else math.nan,
            "close": float(group.at[2, "close"]) if valid else math.nan,
        })
    result = pd.DataFrame(rows)
    if result.empty or result["source_epoch"].duplicated().any() or not result["source_epoch"].is_monotonic_increasing:
        raise ValueError("no valid strictly ordered M15 frame")
    return result


def calculate_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy().reset_index(drop=True)
    ranges = result["high"] - result["low"]
    ema1 = ema_sma_seed(ranges, EMA_LENGTH)
    ema2 = ema_sma_seed(ema1, EMA_LENGTH)
    ratio = ema1 / ema2.where(ema2 > 0.0)
    mass = ratio.rolling(MASS_LENGTH, min_periods=MASS_LENGTH).sum()
    close_ema = ema_sma_seed(result["close"], EMA_LENGTH)
    result["mass_index"] = mass
    result["close_ema9"] = close_ema
    result["feature_valid"] = np.isfinite(mass) & np.isfinite(close_ema) & np.isfinite(close_ema.shift(1))
    return result


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = calculate_features(frame)
    design = (data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)
    armed = False
    raw_rows: list[tuple[int, str]] = []
    consumed_without_direction = 0
    for index, row in data.iterrows():
        mass = float(row["mass_index"])
        if not bool(row["feature_valid"]) or not math.isfinite(mass):
            armed = False
            continue
        if not armed:
            if mass > UPPER:
                armed = True
            continue
        if mass >= LOWER:
            continue
        armed = False
        slope = float(row["close_ema9"] - data.at[index - 1, "close_ema9"])
        if slope < 0.0:
            direction = "LONG"
        elif slope > 0.0:
            direction = "SHORT"
        else:
            consumed_without_direction += int(bool(design.iloc[index]))
            continue
        if bool(design.iloc[index]):
            raw_rows.append((int(index), direction))
    events: list[dict[str, Any]] = []
    gap_rejects = 0
    for index, direction in raw_rows:
        exact_next = index + 1 < len(data) and int(data.at[index + 1, "source_epoch"]) == int(data.at[index, "source_epoch"]) + 900
        exact_next = exact_next and data.at[index + 1, "time_utc"] - data.at[index, "time_utc"] == pd.Timedelta(minutes=15)
        if not exact_next:
            gap_rejects += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_epoch": int(data.at[index, "source_epoch"]),
            "source_bar_time_utc": data.at[index, "time_utc"].isoformat().replace("+00:00", "Z"),
            "decision_time_utc": data.at[index + 1, "time_utc"].isoformat().replace("+00:00", "Z"),
            "direction": direction,
            "mass_index": float(data.at[index, "mass_index"]),
            "prior_close_ema9": float(data.at[index - 1, "close_ema9"]),
            "close_ema9": float(data.at[index, "close_ema9"]),
        })
    design_rows = int(design.sum())
    usable_rows = int((design & data["feature_valid"]).sum())
    count = len(events)
    raw_count = len(raw_rows)
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    longs = sum(event["direction"] == "LONG" for event in events)
    shorts = count - longs
    years = pd.Series([pd.Timestamp(event["decision_time_utc"]).year for event in events], dtype="int64")
    yearly: dict[str, Any] = {}
    for year in range(2016, 2023):
        n = int((years == year).sum()) if count else 0
        yearly[str(year)] = {"events": n, "cadence_per_week": n / year_weeks(year), "share": n / count if count else 0.0}
    cadence = count / elapsed_weeks
    feature_coverage = usable_rows / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
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
        "zero_direction_conflicts": True,
    }
    report = {
        "schema_version": "mirb_m15_source_report.v1", "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID, "verdict": "PASS_SOURCE_BUILD_AUTHORIZED" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY",
        "source_rows_m15": len(data), "design_rows": design_rows, "feature_usable_rows": usable_rows,
        "feature_coverage": feature_coverage, "raw_events": raw_count, "executable_events": count,
        "gap_rejected_events": gap_rejects, "directionless_consumed_events": consumed_without_direction,
        "exact_next_coverage": next_coverage, "elapsed_weeks": elapsed_weeks, "cadence_per_week": cadence,
        "long_events": longs, "short_events": shorts, "long_share": long_share, "short_share": short_share,
        "max_year_share": max_year_share, "by_decision_year": yearly, "gates": gates,
        "all_gates_pass": all(gates.values()), "outcomes_read": False, "trades_simulated": 0,
        "economics_evaluated": False, "paid_data_used": False,
    }
    return events, report


def execute(output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"attempt root already exists: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    started = {"schema_version": "mirb_source_attempt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID}
    start_path = output_dir / "attempt_started.json"
    start_path.write_bytes(canonical_bytes(started))
    if sha256_file(MANIFEST) != MANIFEST_SHA256 or sha256_file(DATA) != DATA_SHA256:
        raise ValueError("frozen manifest/data hash mismatch")
    initial_hashes = {str(path): sha256_file(path) for path in (PREREG, TEST, Path(__file__), MANIFEST, DATA)}
    frame = pd.read_parquet(
        DATA, columns=list(REQUIRED_COLUMNS), engine="pyarrow",
        filters=[("time_utc", ">=", SOURCE_START.to_pydatetime()), ("time_utc", "<", DESIGN_END.to_pydatetime())],
    )
    m15 = aggregate_complete_m15(frame)
    events, report = analyze_frame(m15)
    if {str(path): sha256_file(path) for path in (PREREG, TEST, Path(__file__), MANIFEST, DATA)} != initial_hashes:
        raise ValueError("bound input drift during source attempt")
    report_path = output_dir / "source_report.json"
    ledger_path = output_dir / "event_ledger.jsonl"
    atomic_write(report_path, canonical_bytes(report))
    atomic_write(ledger_path, jsonl_bytes(events))
    receipt = {
        "schema_version": "mirb_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "started_sha256": sha256_file(start_path), "report_sha256": sha256_file(report_path),
        "ledger_sha256": sha256_file(ledger_path), "bound_input_sha256": initial_hashes,
        "outcomes_read": False, "economics_evaluated": False, "paid_data_used": False,
    }
    receipt_path = output_dir / "source_receipt.json"
    atomic_write(receipt_path, canonical_bytes(receipt))
    terminal = {
        "schema_version": "mirb_source_terminal.v1", "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID, "status": "COMPLETE", "verdict": report["verdict"],
        "receipt_sha256": sha256_file(receipt_path), "same_id_retry_authorized": False,
    }
    atomic_write(output_dir / "attempt_terminal.json", canonical_bytes(terminal))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(execute(parse_args().output_dir.resolve()), indent=2, sort_keys=True))
