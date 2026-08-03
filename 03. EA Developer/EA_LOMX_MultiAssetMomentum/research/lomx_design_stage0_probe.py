#!/usr/bin/env python3
"""Outcome-blind density/geometry probe for HYP-LOMX-DESIGN-M5-002."""

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


HYPOTHESIS_ID = "HYP-LOMX-DESIGN-M5-002"
START = pd.Timestamp("2016-01-04T00:00:00Z")
END = pd.Timestamp("2025-01-01T00:00:00Z")
ELAPSED_WEEKS = (END - START).total_seconds() / (7.0 * 24.0 * 3600.0)
PLAN_REL = (
    "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/"
    "HYP-LOMX-DESIGN-M5-002_PROBE_PLAN.md"
)
PLAN_SHA256 = "FB44311871144290B231DA3AFC083C89B4D950768D7FA1D5F4E61C695B8CD09E"
DATASETS = {
    "EURUSD": {
        "path": (
            "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
            "DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/"
            "EURUSD_M5_ALL_AVAILABLE_20260801.parquet"
        ),
        "sha256": "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8",
    },
    "XAUUSD": {
        "path": (
            "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
            "DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/"
            "XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
        ),
        "sha256": "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380",
    },
}
CANDIDATE_COLUMNS = [
    "symbol",
    "engine",
    "decision_time_utc",
    "direction",
    "decision_close",
    "atr14",
    "initial_risk_price",
    "asian_high",
    "asian_low",
    "volume_ratio",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def wilder_atr(frame: pd.DataFrame, period: int = 14) -> np.ndarray:
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    previous = np.roll(close, 1)
    previous[0] = close[0]
    true_range = np.maximum.reduce(
        [high - low, np.abs(high - previous), np.abs(low - previous)]
    )
    output = np.full(len(frame), np.nan, dtype=float)
    if len(frame) < period:
        return output
    output[period - 1] = float(np.mean(true_range[:period]))
    for index in range(period, len(frame)):
        output[index] = (
            output[index - 1] * (period - 1) + true_range[index]
        ) / period
    return output


def validate_bars(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    required = {
        "symbol",
        "timeframe",
        "time_utc",
        "utc_ambiguous",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{symbol} bars missing columns: {sorted(missing)}")
    result = frame.copy()
    result["time_utc"] = pd.to_datetime(result["time_utc"], utc=True)
    if result["time_utc"].isna().any() or result["utc_ambiguous"].astype(bool).any():
        raise ValueError(f"{symbol} has null or ambiguous UTC rows")
    if set(result["symbol"].astype(str)) != {symbol}:
        raise ValueError(f"{symbol} source contains another symbol")
    if set(result["timeframe"].astype(str)) != {"M5"}:
        raise ValueError(f"{symbol} source is not exact M5")
    result = result.loc[(result["time_utc"] >= START) & (result["time_utc"] < END)]
    result = result.sort_values("time_utc", kind="stable").reset_index(drop=True)
    if result.empty or result["time_utc"].duplicated().any():
        raise ValueError(f"{symbol} M5 window is empty or duplicated")
    for column in ("open", "high", "low", "close", "tick_volume"):
        values = pd.to_numeric(result[column], errors="coerce")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{symbol} {column} contains non-finite values")
        result[column] = values
    if not (
        (result["high"] >= result[["open", "close", "low"]].max(axis=1))
        & (result["low"] <= result[["open", "close", "high"]].min(axis=1))
    ).all():
        raise ValueError(f"{symbol} OHLC geometry is invalid")
    return result


def load_bars(path: Path, symbol: str) -> pd.DataFrame:
    columns = [
        "symbol",
        "timeframe",
        "time_utc",
        "utc_ambiguous",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    ]
    frame = pd.read_parquet(
        path,
        columns=columns,
        filters=[("time_utc", ">=", START), ("time_utc", "<", END)],
    )
    return validate_bars(frame, symbol)


def attach_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = frame.copy()
    result["utc_date"] = result["time_utc"].dt.date
    minute = result["time_utc"].dt.hour * 60 + result["time_utc"].dt.minute
    result["in_asian"] = (minute >= 0) & (minute < 6 * 60)
    result["in_trade"] = (minute >= 7 * 60) & (minute < 16 * 60)

    asian = (
        result.loc[result["in_asian"]]
        .groupby("utc_date", sort=False)
        .agg(
            asian_count=("time_utc", "size"),
            asian_high=("high", "max"),
            asian_low=("low", "min"),
        )
    )
    active_dates = set(result.loc[result["in_trade"], "utc_date"])
    complete_dates = set(asian.index[asian["asian_count"] == 72]) & active_dates
    result = result.join(asian, on="utc_date")
    result["asian_complete"] = result["utc_date"].isin(complete_dates)

    result["atr14"] = wilder_atr(result, 14)
    volume = result["tick_volume"].astype(float)
    result["volume_mean20"] = volume.shift(1).rolling(20, min_periods=20).mean()
    result["volume_std20"] = volume.shift(1).rolling(20, min_periods=20).std(ddof=0)
    result["volume_ratio"] = volume / result["volume_mean20"]
    bar_range = result["high"] - result["low"]
    result["range2"] = bar_range.shift(1)
    result["range_prior50_mean"] = bar_range.shift(2).rolling(50, min_periods=50).mean()
    result["box_high"] = result["high"].shift(1).rolling(15, min_periods=15).max()
    result["box_low"] = result["low"].shift(1).rolling(15, min_periods=15).min()
    coverage = {
        "active_trading_dates": len(active_dates),
        "complete_asian_dates": len(complete_dates),
        "asian_coverage_ratio": (
            len(complete_dates) / len(active_dates) if active_dates else 0.0
        ),
    }
    return result, coverage


def candidate_frame(
    source: pd.DataFrame,
    mask: pd.Series,
    symbol: str,
    engine: str,
    direction: int,
    risk: pd.Series,
) -> pd.DataFrame:
    selected = source.loc[mask].copy()
    output = pd.DataFrame(
        {
            "symbol": symbol,
            "engine": engine,
            "decision_time_utc": selected["time_utc"],
            "direction": direction,
            "decision_close": selected["close"],
            "atr14": selected["atr14"],
            "initial_risk_price": risk.loc[mask],
            "asian_high": selected["asian_high"],
            "asian_low": selected["asian_low"],
            "volume_ratio": selected["volume_ratio"],
        }
    )
    return output[CANDIDATE_COLUMNS]


def scan_symbol(frame: pd.DataFrame, symbol: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    bars, coverage = attach_features(validate_bars(frame, symbol))
    finite = (
        bars["in_trade"]
        & bars["asian_complete"]
        & bars["atr14"].gt(0)
        & np.isfinite(bars["volume_mean20"])
        & np.isfinite(bars["volume_std20"])
    )
    volume_spike = bars["tick_volume"].astype(float) > (
        bars["volume_mean20"] + 1.5 * bars["volume_std20"]
    )
    sweep_long_risk = bars["close"] - (bars["low"] - 0.2 * bars["atr14"])
    sweep_short_risk = (bars["high"] + 0.2 * bars["atr14"]) - bars["close"]
    asian_mid = (bars["asian_high"] + bars["asian_low"]) / 2.0
    sweep_long = (
        finite
        & volume_spike
        & (bars["low"] < bars["asian_low"] - 0.3 * bars["atr14"])
        & (bars["close"] > bars["asian_low"])
        & (asian_mid > bars["close"])
        & (bars["asian_high"] - bars["close"] >= 1.5 * sweep_long_risk)
        & sweep_long_risk.gt(0)
    )
    sweep_short = (
        finite
        & volume_spike
        & (bars["high"] > bars["asian_high"] + 0.3 * bars["atr14"])
        & (bars["close"] < bars["asian_high"])
        & (asian_mid < bars["close"])
        & (bars["close"] - bars["asian_low"] >= 1.5 * sweep_short_risk)
        & sweep_short_risk.gt(0)
    )

    compression = bars["range2"] < 0.70 * bars["range_prior50_mean"]
    volume_above_mean = bars["tick_volume"].astype(float) > bars["volume_mean20"]
    breakout_long_risk = bars["close"] - (bars["box_low"] - 0.1 * bars["atr14"])
    breakout_short_risk = (bars["box_high"] + 0.1 * bars["atr14"]) - bars["close"]
    breakout_finite = finite & np.isfinite(bars["range_prior50_mean"]) & np.isfinite(
        bars["box_high"]
    )
    breakout_long = (
        breakout_finite
        & compression
        & volume_above_mean
        & (bars["close"] > bars["box_high"] + 0.2 * bars["atr14"])
        & breakout_long_risk.gt(0)
    )
    breakout_short = (
        breakout_finite
        & compression
        & volume_above_mean
        & (bars["close"] < bars["box_low"] - 0.2 * bars["atr14"])
        & breakout_short_risk.gt(0)
    )

    candidates = pd.concat(
        [
            candidate_frame(
                bars, sweep_long, symbol, "ASIAN_RANGE_SWEEP_RECLAIM", 1, sweep_long_risk
            ),
            candidate_frame(
                bars, sweep_short, symbol, "ASIAN_RANGE_SWEEP_RECLAIM", -1, sweep_short_risk
            ),
            candidate_frame(
                bars,
                breakout_long,
                symbol,
                "BAR_RANGE_COMPRESSION_BREAKOUT",
                1,
                breakout_long_risk,
            ),
            candidate_frame(
                bars,
                breakout_short,
                symbol,
                "BAR_RANGE_COMPRESSION_BREAKOUT",
                -1,
                breakout_short_risk,
            ),
        ],
        ignore_index=True,
    ).sort_values(["decision_time_utc", "engine", "direction"], kind="stable")
    return candidates.reset_index(drop=True), coverage


def atomic_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    count = len(frame)
    direction_counts = {
        "long": int((frame["direction"] == 1).sum()),
        "short": int((frame["direction"] == -1).sum()),
    }
    direction_shares = {
        key: value / count if count else 0.0 for key, value in direction_counts.items()
    }
    years = pd.to_datetime(frame["decision_time_utc"], utc=True).dt.year
    year_counts = {str(int(key)): int(value) for key, value in years.value_counts().sort_index().items()}
    max_year_share = max(year_counts.values(), default=0) / count if count else 0.0
    positive_risk = bool(
        count
        and np.isfinite(frame["initial_risk_price"].to_numpy(dtype=float)).all()
        and frame["initial_risk_price"].gt(0).all()
    )
    gates = {
        "min_candidates_400": count >= 400,
        "min_candidates_per_week_1": count / ELAPSED_WEEKS >= 1.0,
        "both_direction_share_min_0_20": min(direction_shares.values()) >= 0.20,
        "max_year_share_0_25": max_year_share <= 0.25,
        "positive_finite_initial_risk": positive_risk,
    }
    return {
        "candidate_count": count,
        "candidates_per_elapsed_week": count / ELAPSED_WEEKS,
        "direction_counts": direction_counts,
        "direction_shares": direction_shares,
        "year_counts": year_counts,
        "max_year_share": max_year_share,
        "initial_risk_price_median": (
            float(frame["initial_risk_price"].median()) if count else None
        ),
        "gates": gates,
        "pass": all(gates.values()),
    }


def combined_metrics(frame: pd.DataFrame, coverage: dict[str, Any]) -> dict[str, Any]:
    grouped = frame.groupby("decision_time_utc", sort=True)
    opposing = int(sum(group["direction"].nunique() > 1 for _, group in grouped))
    selected_rows: list[pd.Series] = []
    for _, group in grouped:
        if group["direction"].nunique() > 1:
            continue
        sweep = group.loc[group["engine"] == "ASIAN_RANGE_SWEEP_RECLAIM"]
        selected_rows.append((sweep if not sweep.empty else group).iloc[0])
    combined = pd.DataFrame(selected_rows, columns=frame.columns)
    count = len(combined)
    cadence = count / ELAPSED_WEEKS
    gates = {
        "combined_candidates_per_week_2_to_5": 2.0 <= cadence <= 5.0,
        "asian_coverage_ratio_min_0_90": coverage["asian_coverage_ratio"] >= 0.90,
        "opposing_same_bar_collisions_zero": opposing == 0,
    }
    return {
        **coverage,
        "atomic_candidate_rows": len(frame),
        "deconflicted_candidate_count": count,
        "deconflicted_candidates_per_elapsed_week": cadence,
        "same_bar_overlap_rows_removed": len(frame) - count,
        "opposing_same_bar_collisions": opposing,
        "gates": gates,
        "pass": all(gates.values()),
    }


def run(root: Path, output_root: Path) -> dict[str, Any]:
    plan = root / PLAN_REL
    if sha256_file(plan) != PLAN_SHA256:
        raise ValueError("frozen probe plan hash mismatch")
    all_candidates: list[pd.DataFrame] = []
    atomic: dict[str, Any] = {}
    combined: dict[str, Any] = {}
    sources: dict[str, Any] = {}
    for symbol, contract in DATASETS.items():
        path = root / str(contract["path"])
        actual_hash = sha256_file(path)
        if actual_hash != contract["sha256"]:
            raise ValueError(f"{symbol} frozen dataset hash mismatch")
        bars = load_bars(path, symbol)
        candidates, coverage = scan_symbol(bars, symbol)
        all_candidates.append(candidates)
        sources[symbol] = {
            "path": contract["path"],
            "sha256": actual_hash,
            "window_rows": len(bars),
            "first_time_utc": bars["time_utc"].iloc[0].isoformat(),
            "last_time_utc": bars["time_utc"].iloc[-1].isoformat(),
        }
        for engine in (
            "ASIAN_RANGE_SWEEP_RECLAIM",
            "BAR_RANGE_COMPRESSION_BREAKOUT",
        ):
            key = f"{symbol}__{engine}"
            atomic[key] = atomic_metrics(candidates.loc[candidates["engine"] == engine])
        combined[symbol] = combined_metrics(candidates, coverage)

    candidate_rows = pd.concat(all_candidates, ignore_index=True)
    if set(candidate_rows.columns) != set(CANDIDATE_COLUMNS):
        raise ValueError("candidate output schema drift")
    forbidden = {"pnl", "profit", "return", "mfe", "mae", "win", "loss", "exit"}
    if any(any(token in column.lower() for token in forbidden) for column in candidate_rows.columns):
        raise ValueError("outcome-like candidate column detected")
    candidate_path = output_root / "candidates_outcome_blind.csv"
    atomic_csv(candidate_path, candidate_rows)
    full_pass = all(cell["pass"] for cell in atomic.values()) and all(
        cell["pass"] for cell in combined.values()
    )
    result = {
        "schema_version": "lomx_design_stage0_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS_ALL_FROZEN_P0_GATES" if full_pass else "FAIL_FROZEN_P0_GATES",
        "outcome_blind": True,
        "performance_outcome_read": False,
        "economics_executed": False,
        "mt5_launches": 0,
        "trades_simulated": 0,
        "window": {"from": START.isoformat(), "to_exclusive": END.isoformat()},
        "elapsed_calendar_weeks": ELAPSED_WEEKS,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "sources": sources,
        "atomic_cells": atomic,
        "combined_cells": combined,
        "candidate_csv": candidate_path.relative_to(root).as_posix(),
        "candidate_csv_sha256": sha256_file(candidate_path),
        "candidate_rows": len(candidate_rows),
        "full_plan_p0_pass": full_pass,
        "scanner_path": Path(__file__).resolve().relative_to(root).as_posix(),
        "scanner_sha256": sha256_file(Path(__file__).resolve()),
        "forbidden_outcome_fields": sorted(forbidden),
    }
    result_path = output_root / "stage0_result.json"
    atomic_json(result_path, result)
    print(json.dumps({"status": result["status"], "result": str(result_path)}, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output_root = (
        Path(args.output_root).resolve()
        if args.output_root
        else root
        / "03. EA Developer"
        / "EA_LOMX_MultiAssetMomentum"
        / "research"
        / "evidence"
        / HYPOTHESIS_ID
        / "P0_DESIGN_001"
    )
    run(root, output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
