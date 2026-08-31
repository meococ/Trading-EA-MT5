#!/usr/bin/env python3
"""Validate one HYP-014 quote-acceptance telemetry CSV fail-closed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "vras_quote_acceptance.v1"
HYPOTHESIS = "HYP-VRAS-EURUSD-M5-014"
SYMBOL = "EURUSD"
DATA_SOURCES = {"LIVE_QUOTES", "SYNTHETIC_TESTER_TICKS"}
TERMINALS = {
    "ACCEPTED_OBSERVATION",
    "REJECT_VWAP_RECROSS",
    "REJECT_SPREAD_SPIKE",
    "REJECT_STALE_GAP",
    "REJECT_INVALID_QUOTE",
    "EXPIRE_NO_ACCEPTANCE",
    "DEINIT_ACTIVE_ARM",
}
EVENTS = {"ARMED", "OBSERVE", *TERMINALS}
FIELDS = [
    "schema_version",
    "hypothesis_id",
    "run_id",
    "event_time_msc",
    "event_time_utc",
    "symbol",
    "event",
    "direction",
    "arm_bar_time",
    "arm_time_msc",
    "age_ms",
    "bid",
    "ask",
    "mid",
    "spread_points",
    "prearm_median_spread_points",
    "quote_updates",
    "price_changes",
    "directional_moves",
    "opposite_moves",
    "imbalance",
    "directional_net_points",
    "max_gap_ms",
    "max_spread_ratio",
    "frozen_vwap",
    "data_source",
    "promotion_eligible",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _integer(row: dict[str, str], field: str, line: int) -> int:
    try:
        return int(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"line {line}: {field} is not an integer") from exc


def _number(row: dict[str, str], field: str, line: int) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"line {line}: {field} is not numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"line {line}: {field} is not finite")
    return value


def _utc_msc(text: str, line: int) -> int:
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"line {line}: invalid event_time_utc") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"line {line}: event_time_utc must include timezone")
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def _bool_false(value: str) -> bool:
    return value.strip().lower() in {"false", "0"}


def _direction(row: dict[str, str], line: int) -> int:
    value = row.get("direction", "").strip().lower()
    if value == "long":
        return 1
    if value == "short":
        return -1
    raise ValueError(f"line {line}: direction must be long or short")


def validate(csv_path: Path, expected_source: str | None = None) -> dict[str, Any]:
    if not csv_path.is_file():
        raise ValueError(f"CSV missing: {csv_path}")
    if expected_source is not None and expected_source not in DATA_SOURCES:
        raise ValueError(f"unsupported expected data source: {expected_source}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError(
                "header mismatch: expected=" + ",".join(FIELDS)
                + " observed=" + ",".join(reader.fieldnames or [])
            )
        rows = list(reader)

    run_id: str | None = None
    data_source: str | None = None
    previous_msc = -1
    active: dict[str, Any] | None = None
    arms = 0
    accepted = 0
    terminal_counts = {event: 0 for event in sorted(TERMINALS)}

    for line, row in enumerate(rows, start=2):
        if row["schema_version"] != SCHEMA:
            raise ValueError(f"line {line}: schema_version mismatch")
        if row["hypothesis_id"] != HYPOTHESIS:
            raise ValueError(f"line {line}: hypothesis_id mismatch")
        if row["symbol"] != SYMBOL:
            raise ValueError(f"line {line}: symbol must be EURUSD")
        if row["event"] not in EVENTS:
            raise ValueError(f"line {line}: unsupported event {row['event']}")
        if not _bool_false(row["promotion_eligible"]):
            raise ValueError(f"line {line}: promotion_eligible must be false")
        if row["data_source"] not in DATA_SOURCES:
            raise ValueError(f"line {line}: invalid data_source")
        if expected_source is not None and row["data_source"] != expected_source:
            raise ValueError(f"line {line}: expected data_source {expected_source}")

        if run_id is None:
            run_id = row["run_id"]
            data_source = row["data_source"]
            if not run_id:
                raise ValueError(f"line {line}: run_id is empty")
        elif row["run_id"] != run_id or row["data_source"] != data_source:
            raise ValueError(f"line {line}: run identity drift")

        event_msc = _integer(row, "event_time_msc", line)
        if event_msc <= previous_msc:
            raise ValueError(f"line {line}: event_time_msc is not strictly increasing")
        if abs(_utc_msc(row["event_time_utc"], line) - event_msc) > 1:
            raise ValueError(f"line {line}: UTC/time_msc mismatch")
        previous_msc = event_msc

        direction = _direction(row, line)
        arm_msc = _integer(row, "arm_time_msc", line)
        age_ms = _integer(row, "age_ms", line)
        if age_ms != event_msc - arm_msc or age_ms < 0:
            raise ValueError(f"line {line}: age_ms does not match timestamps")

        bid = _number(row, "bid", line)
        ask = _number(row, "ask", line)
        mid = _number(row, "mid", line)
        spread = _number(row, "spread_points", line)
        median = _number(row, "prearm_median_spread_points", line)
        imbalance = _number(row, "imbalance", line)
        net_points = _number(row, "directional_net_points", line)
        max_gap = _integer(row, "max_gap_ms", line)
        max_spread_ratio = _number(row, "max_spread_ratio", line)
        frozen_vwap = _number(row, "frozen_vwap", line)
        quote_updates = _integer(row, "quote_updates", line)
        price_changes = _integer(row, "price_changes", line)
        directional_moves = _integer(row, "directional_moves", line)
        opposite_moves = _integer(row, "opposite_moves", line)

        if bid <= 0 or ask < bid or spread < 0 or median <= 0 or frozen_vwap <= 0:
            raise ValueError(f"line {line}: invalid quote/spread/VWAP geometry")
        if abs(mid - (bid + ask) / 2) > 1e-8:
            raise ValueError(f"line {line}: mid does not equal bid/ask midpoint")
        if not 0 <= imbalance <= 1 or min(
            quote_updates, price_changes, directional_moves, opposite_moves, max_gap
        ) < 0:
            raise ValueError(f"line {line}: negative count or invalid imbalance")
        if directional_moves + opposite_moves != price_changes:
            raise ValueError(f"line {line}: price-change decomposition mismatch")

        event = row["event"]
        if event == "ARMED":
            if active is not None:
                raise ValueError(f"line {line}: nested arm")
            if age_ms != 0:
                raise ValueError(f"line {line}: ARMED age must be zero")
            active = {
                "direction": direction,
                "arm_msc": arm_msc,
                "arm_spread_points": spread,
            }
            arms += 1
        else:
            if active is None:
                raise ValueError(f"line {line}: event without active arm")
            if direction != active["direction"] or arm_msc != active["arm_msc"]:
                raise ValueError(f"line {line}: active-arm identity drift")

        if event == "ACCEPTED_OBSERVATION":
            if not 30_000 <= age_ms <= 120_000:
                raise ValueError(f"line {line}: acceptance age gate failed")
            if quote_updates < 20 or price_changes < 12 or imbalance < 0.60:
                raise ValueError(f"line {line}: acceptance count/imbalance gate failed")
            if net_points + 1e-9 < active["arm_spread_points"]:
                raise ValueError(f"line {line}: acceptance expansion gate failed")
            if spread > median + 1e-9 or max_spread_ratio > 1.50 + 1e-9:
                raise ValueError(f"line {line}: acceptance spread gate failed")
            if max_gap > 15_000:
                raise ValueError(f"line {line}: acceptance stale-gap gate failed")
            if (direction == 1 and bid <= frozen_vwap) or (
                direction == -1 and ask >= frozen_vwap
            ):
                raise ValueError(f"line {line}: acceptance VWAP gate failed")
            accepted += 1
        elif event == "REJECT_VWAP_RECROSS":
            if not ((direction == 1 and bid <= frozen_vwap) or (direction == -1 and ask >= frozen_vwap)):
                raise ValueError(f"line {line}: VWAP rejection has no recross")
        elif event == "REJECT_SPREAD_SPIKE" and max_spread_ratio <= 1.50:
            raise ValueError(f"line {line}: spread rejection has no spike")
        elif event == "REJECT_STALE_GAP" and max_gap <= 15_000:
            raise ValueError(f"line {line}: stale rejection has no stale gap")
        elif event == "EXPIRE_NO_ACCEPTANCE" and age_ms <= 120_000:
            raise ValueError(f"line {line}: expiry is not past 120 seconds")

        if event in TERMINALS:
            terminal_counts[event] += 1
            active = None

    if active is not None:
        raise ValueError("capture ended with a non-terminal active arm")

    return {
        "schema_version": "alphafactory_vras_quote_capture_validation.v1",
        "status": "PASS",
        "verdict": "VALID_NO_ARMS" if not rows else "VALID_ENGINEERING_ONLY",
        "csv": str(csv_path.resolve()),
        "csv_sha256": _sha256(csv_path),
        "row_count": len(rows),
        "run_id": run_id,
        "data_source": data_source,
        "arms": arms,
        "accepted_observations": accepted,
        "terminal_counts": terminal_counts,
        "order_activity_verification": "OUT_OF_SCOPE_REQUIRES_SEPARATE_SAFETY_RECEIPT",
        "live_trading_authorized": False,
        "performance_metrics_authorized": False,
        "promotion_eligible": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-source", choices=sorted(DATA_SOURCES))
    args = parser.parse_args()
    try:
        result = validate(Path(args.csv).resolve(), args.expected_source)
        out = Path(args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "out": str(out)}))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI fail-closed receipt
        print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
