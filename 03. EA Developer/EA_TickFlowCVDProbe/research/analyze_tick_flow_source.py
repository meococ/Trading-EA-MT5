#!/usr/bin/env python3
"""Outcome-blind source/cadence validator for HYP-TFCVD-XAUUSD-M5-001."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "alphafactory.tick_flow_cvd_source.v1"
HYPOTHESIS_ID = "HYP-TFCVD-XAUUSD-M5-001"
FORBIDDEN_COLUMNS = {
    "return", "future_return", "mfe", "mae", "pnl", "profit", "loss",
    "profit_factor", "balance", "equity", "drawdown", "stop_hit", "target_hit",
    "entry_price", "exit_price", "trade_result",
}
REQUIRED = {
    "schema_version", "hypothesis_id", "symbol", "timeframe", "bar_start_server",
    "total_ticks", "valid_quote_ticks", "invalid_ticks", "unique_quote_updates",
    "classified_updates", "quote_tick_delta", "mid_open", "mid_high", "mid_low",
    "mid_close", "bar_complete", "promotion_eligible",
}


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)


def is_candidate(row: dict[str, str]) -> tuple[bool, str | None]:
    unique = int(row["unique_quote_updates"])
    classified = int(row["classified_updates"])
    delta = int(row["quote_tick_delta"])
    open_mid = float(row["mid_open"])
    high_mid = float(row["mid_high"])
    low_mid = float(row["mid_low"])
    close_mid = float(row["mid_close"])
    price_range = high_mid - low_mid
    if unique < 20 or classified < 20 or price_range <= 0.0:
        return False, None
    normalized_delta = abs(delta) / classified
    close_efficiency = abs(close_mid - open_mid) / price_range
    if normalized_delta < 0.35 or close_efficiency > 0.20:
        return False, None
    if delta * (close_mid - open_mid) > 0.0:
        return False, None
    if delta > 0:
        return True, "short"
    if delta < 0:
        return True, "long"
    return False, None


def analyze(path: Path, history_quality: float) -> dict[str, object]:
    bars = 0
    qualified_bars = 0
    invalid_ticks = 0
    total_ticks = 0
    candidates = 0
    directions: Counter[str] = Counter()
    years: Counter[int] = Counter()
    first_time: datetime | None = None
    last_time: datetime | None = None
    prior_time: datetime | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED - fields
        forbidden = FORBIDDEN_COLUMNS & fields
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        if forbidden:
            raise ValueError(f"forbidden outcome columns: {sorted(forbidden)}")
        for row_number, row in enumerate(reader, start=2):
            if row["schema_version"] != SCHEMA or row["hypothesis_id"] != HYPOTHESIS_ID:
                raise ValueError(f"row {row_number}: identity mismatch")
            if row["symbol"] != "XAUUSD" or row["timeframe"] != "M5":
                raise ValueError(f"row {row_number}: symbol/timeframe mismatch")
            if row["bar_complete"].lower() != "true" or row["promotion_eligible"].lower() != "false":
                raise ValueError(f"row {row_number}: authority flags invalid")
            timestamp = parse_time(row["bar_start_server"])
            if prior_time is not None and timestamp <= prior_time:
                raise ValueError(f"row {row_number}: timestamps are not strictly increasing")
            prior_time = timestamp
            first_time = timestamp if first_time is None else first_time
            last_time = timestamp
            bars += 1
            total_ticks += int(row["total_ticks"])
            invalid_ticks += int(row["invalid_ticks"])
            if int(row["unique_quote_updates"]) >= 20:
                qualified_bars += 1
            candidate, direction = is_candidate(row)
            if candidate and direction is not None:
                candidates += 1
                directions[direction] += 1
                years[timestamp.year] += 1

    if bars == 0 or first_time is None or last_time is None:
        raise ValueError("telemetry contains no completed bars")
    elapsed_weeks = max((last_time - first_time).total_seconds() / 604800.0, 1.0 / 7.0)
    qualified_share = qualified_bars / bars
    invalid_share = invalid_ticks / total_ticks if total_ticks else 1.0
    cadence = candidates / elapsed_weeks
    min_direction_share = min(directions.values(), default=0) / candidates if candidates else 0.0
    max_year_share = max(years.values(), default=0) / candidates if candidates else 1.0
    gates = {
        "history_quality_gt_97": history_quality > 97.0,
        "qualified_bar_share_gte_0_95": qualified_share >= 0.95,
        "invalid_tick_share_lte_0_001": invalid_share <= 0.001,
        "candidate_count_gte_500": candidates >= 500,
        "candidate_cadence_2_to_8": 2.0 <= cadence <= 8.0,
        "each_direction_share_gte_0_30": min_direction_share >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
    }
    passed = all(gates.values())
    return {
        "schema_version": "alphafactory.tick_flow_cvd_source_analysis.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "evidence_class": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
        "source_csv": str(path.resolve()),
        "history_quality_pct": history_quality,
        "bars": bars,
        "elapsed_weeks": elapsed_weeks,
        "qualified_bar_share": qualified_share,
        "invalid_tick_share": invalid_share,
        "candidates": candidates,
        "candidate_cadence_per_week": cadence,
        "direction_counts": dict(directions),
        "year_counts": {str(key): value for key, value in sorted(years.items())},
        "min_direction_share": min_direction_share,
        "max_year_share": max_year_share,
        "gates": gates,
        "verdict": (
            "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_ECONOMIC_CHILD"
            if passed else "KILL_SOURCE_FEASIBILITY_EXACT_TICK_DELTA_MAPPING"
        ),
        "performance_or_economics_authorized": False,
        "promotion_eligible": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--history-quality", type=float, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.csv_path, args.history_quality)
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["verdict"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
