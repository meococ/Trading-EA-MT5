#!/usr/bin/env python3
"""Merge official BitMEX quote/trade archives into a fixed binary MT5 stream.

This tool performs source normalization only. Trading, fills, PnL, and all
economic decisions remain inside the MQL5 simulator.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import gzip
import hashlib
import json
import re
import struct
from datetime import datetime
from pathlib import Path
from typing import Iterator


MAGIC = b"XBTMM01\0"
SCHEMA_VERSION = 1
HEADER = struct.Struct("<8sIIQqqQQ")
RECORD = struct.Struct("<qBddqqdqb")
QUOTE = 1
TRADE = 2
BUY = 1
SELL = -1
DAY_US = 86_400_000_000
BOUNDARY_TOLERANCE_US = 60_000_000
MAX_QUOTE_GAP_US = 60_000_000
MAX_CROSSED_BOOK_US = 50_000
MAX_INVALID_QUOTE_RATIO = 0.005
DESIGN_TICK_SIZE = 0.5
VENUE_LOT_CHANGE_US = 1_623_126_600_000_000
VENUE_LOT_BEFORE = 1
VENUE_LOT_AFTER = 100


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_timestamp_us(value: str) -> int:
    base, dot, fraction = value.strip().partition(".")
    dt = datetime.strptime(base, "%Y-%m-%dD%H:%M:%S")
    micros = int((fraction + "000000")[:6]) if dot else 0
    return calendar.timegm(dt.timetuple()) * 1_000_000 + micros


def quote_rows(path: Path, symbol: str) -> Iterator[dict]:
    last = -1
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = ["timestamp", "symbol", "bidSize", "bidPrice", "askPrice", "askSize"]
        if reader.fieldnames != expected:
            raise ValueError(f"unexpected quote schema: {reader.fieldnames!r}")
        for row in reader:
            if row["symbol"] != symbol:
                continue
            stamp = parse_timestamp_us(row["timestamp"])
            if stamp < last:
                raise ValueError(f"quote timestamp regressed: {stamp} < {last}")
            last = stamp
            yield {
                "time_us": stamp,
                "bid": float(row["bidPrice"]),
                "ask": float(row["askPrice"]),
                "bid_size": int(row["bidSize"]),
                "ask_size": int(row["askSize"]),
            }


def trade_rows(path: Path, symbol: str) -> Iterator[dict]:
    last = -1
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "symbol", "side", "size", "price"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"unexpected trade schema: {reader.fieldnames!r}")
        for row in reader:
            if row["symbol"] != symbol:
                continue
            stamp = parse_timestamp_us(row["timestamp"])
            if stamp < last:
                raise ValueError(f"trade timestamp regressed: {stamp} < {last}")
            last = stamp
            side = BUY if row["side"] == "Buy" else SELL if row["side"] == "Sell" else 0
            if side == 0:
                raise ValueError(f"unknown trade side: {row['side']!r}")
            yield {
                "time_us": stamp,
                "price": float(row["price"]),
                "size": int(row["size"]),
                "side": side,
            }


def next_or_none(iterator):
    try:
        return next(iterator)
    except StopIteration:
        return None


def utc_day_bounds_us(quote_path: Path, trade_path: Path) -> tuple[str, int, int]:
    tokens: list[str] = []
    for path in (quote_path, trade_path):
        match = re.search(r"(?<!\d)(20\d{6})(?!\d)", path.name)
        if match is None:
            raise ValueError(f"daily archive filename has no YYYYMMDD token: {path.name}")
        tokens.append(match.group(1))
    if tokens[0] != tokens[1]:
        raise ValueError(f"quote/trade UTC days differ: {tokens!r}")
    day = datetime.strptime(tokens[0], "%Y%m%d")
    start_us = calendar.timegm(day.timetuple()) * 1_000_000
    return tokens[0], start_us, start_us + DAY_US


def union_duration_us(intervals: list[tuple[int, int]]) -> int:
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def on_price_grid(value: float, tick_size: float = DESIGN_TICK_SIZE) -> bool:
    if value <= 0.0 or tick_size <= 0.0:
        return False
    return abs(value / tick_size - round(value / tick_size)) <= 1e-8


def venue_lot_size(time_us: int) -> int:
    return VENUE_LOT_BEFORE if time_us < VENUE_LOT_CHANGE_US else VENUE_LOT_AFTER


def build(quote_path: Path, trade_path: Path, out_path: Path, manifest_path: Path, symbol: str) -> dict:
    utc_day, day_start_us, day_end_us = utc_day_bounds_us(quote_path, trade_path)
    quote_iter = iter(quote_rows(quote_path, symbol))
    trade_iter = iter(trade_rows(trade_path, symbol))
    quote = next_or_none(quote_iter)
    trade = next_or_none(trade_iter)
    current_quote = None

    records = quotes = trades = 0
    first_us = last_us = 0
    crossed_quotes = 0
    price_grid_violations = 0
    size_grid_violations = 0
    quote_gaps_over_3s = trade_gaps_over_3s = 0
    max_quote_gap_us = max_trade_gap_us = 0
    previous_quote_us = previous_trade_us = None
    invalid_quote_intervals: list[tuple[int, int]] = []
    quote_gap_invalid_us = 0
    crossed_book_invalid_us = 0
    crossed_start_us: int | None = None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as output:
        output.write(HEADER.pack(MAGIC, SCHEMA_VERSION, RECORD.size, 0, 0, 0, 0, 0))
        while quote is not None or trade is not None:
            # At identical microsecond, already-existing orders see the trade
            # before the quote update and before any later strategy decision.
            take_trade = trade is not None and (quote is None or trade["time_us"] <= quote["time_us"])
            if take_trade:
                event = trade
                trade = next_or_none(trade_iter)
                stamp = event["time_us"]
                if previous_trade_us is not None:
                    gap = stamp - previous_trade_us
                    max_trade_gap_us = max(max_trade_gap_us, gap)
                    if gap > 3_000_000:
                        trade_gaps_over_3s += 1
                previous_trade_us = stamp
                if not on_price_grid(event["price"]):
                    price_grid_violations += 1
                if event["size"] <= 0 or event["size"] % venue_lot_size(stamp) != 0:
                    size_grid_violations += 1
                output.write(
                    RECORD.pack(
                        stamp,
                        TRADE,
                        current_quote["bid"] if current_quote is not None else 0.0,
                        current_quote["ask"] if current_quote is not None else 0.0,
                        current_quote["bid_size"] if current_quote is not None else 0,
                        current_quote["ask_size"] if current_quote is not None else 0,
                        event["price"],
                        event["size"],
                        event["side"],
                    )
                )
                trades += 1
            else:
                event = quote
                quote = next_or_none(quote_iter)
                stamp = event["time_us"]
                if previous_quote_us is not None:
                    gap = stamp - previous_quote_us
                    max_quote_gap_us = max(max_quote_gap_us, gap)
                    if gap > 3_000_000:
                        quote_gaps_over_3s += 1
                    if gap > MAX_QUOTE_GAP_US:
                        invalid_quote_intervals.append((previous_quote_us, stamp))
                        quote_gap_invalid_us += gap
                previous_quote_us = stamp
                if not on_price_grid(event["bid"]) or not on_price_grid(event["ask"]):
                    price_grid_violations += 1
                lot_size = venue_lot_size(stamp)
                if (
                    event["bid_size"] <= 0
                    or event["ask_size"] <= 0
                    or event["bid_size"] % lot_size != 0
                    or event["ask_size"] % lot_size != 0
                ):
                    size_grid_violations += 1
                if event["bid"] >= event["ask"]:
                    crossed_quotes += 1
                    if crossed_start_us is None:
                        crossed_start_us = stamp
                elif crossed_start_us is not None:
                    duration = stamp - crossed_start_us
                    if duration > MAX_CROSSED_BOOK_US:
                        invalid_quote_intervals.append((crossed_start_us, stamp))
                        crossed_book_invalid_us += duration
                    crossed_start_us = None
                current_quote = event
                output.write(
                    RECORD.pack(
                        stamp,
                        QUOTE,
                        event["bid"],
                        event["ask"],
                        event["bid_size"],
                        event["ask_size"],
                        0.0,
                        0,
                        0,
                    )
                )
                quotes += 1

            records += 1
            if first_us == 0:
                first_us = stamp
            last_us = stamp

        if crossed_start_us is not None:
            duration = day_end_us - crossed_start_us
            if duration > MAX_CROSSED_BOOK_US:
                invalid_quote_intervals.append((crossed_start_us, day_end_us))
                crossed_book_invalid_us += duration

        if records <= 0 or quotes <= 0 or trades <= 0:
            raise ValueError(f"empty required XBTUSD stream: records={records} quotes={quotes} trades={trades}")

        output.seek(0)
        output.write(
            HEADER.pack(
                MAGIC,
                SCHEMA_VERSION,
                RECORD.size,
                records,
                first_us,
                last_us,
                quotes,
                trades,
            )
        )

    invalid_quote_us = union_duration_us(invalid_quote_intervals)
    invalid_quote_ratio = invalid_quote_us / DAY_US
    within_day = first_us >= day_start_us and last_us < day_end_us
    boundary_coverage = (
        first_us <= day_start_us + BOUNDARY_TOLERANCE_US
        and last_us >= day_end_us - BOUNDARY_TOLERANCE_US
    )
    source_gate_pass = (
        within_day
        and boundary_coverage
        and invalid_quote_ratio <= MAX_INVALID_QUOTE_RATIO
        and price_grid_violations == 0
        and size_grid_violations == 0
    )

    payload = {
        "schema_version": "xbtmm_event_stream_manifest.v3",
        "symbol": symbol,
        "utc_day": utc_day,
        "event_order": "trade_before_quote_at_identical_microsecond",
        "instrument_schedule": {
            "tick_size": DESIGN_TICK_SIZE,
            "venue_lot_change_time_us": VENUE_LOT_CHANGE_US,
            "venue_lot_before": VENUE_LOT_BEFORE,
            "venue_lot_after": VENUE_LOT_AFTER,
            "strategy_quote_contracts": 100,
            "strategy_soft_inventory_contracts": 200,
            "strategy_hard_inventory_contracts": 400,
        },
        "quote_archive": {
            "path": str(quote_path.resolve()),
            "bytes": quote_path.stat().st_size,
            "sha256": sha256(quote_path),
        },
        "trade_archive": {
            "path": str(trade_path.resolve()),
            "bytes": trade_path.stat().st_size,
            "sha256": sha256(trade_path),
        },
        "output": {
            "path": str(out_path.resolve()),
            "bytes": out_path.stat().st_size,
            "sha256": sha256(out_path),
            "record_size": RECORD.size,
            "records": records,
            "quote_records": quotes,
            "trade_records": trades,
            "first_time_us": first_us,
            "last_time_us": last_us,
        },
        "integrity": {
            "timestamps_nondecreasing": True,
            "events_within_utc_day": within_day,
            "utc_boundary_coverage_pass": boundary_coverage,
            "boundary_tolerance_us": BOUNDARY_TOLERANCE_US,
            "crossed_quote_records": crossed_quotes,
            "crossed_book_threshold_us": MAX_CROSSED_BOOK_US,
            "crossed_book_invalid_us": crossed_book_invalid_us,
            "quote_gaps_over_3s": quote_gaps_over_3s,
            "quote_gap_segment_threshold_us": MAX_QUOTE_GAP_US,
            "quote_gap_invalid_us": quote_gap_invalid_us,
            "trade_gaps_over_3s": trade_gaps_over_3s,
            "max_quote_gap_us": max_quote_gap_us,
            "max_trade_gap_us": max_trade_gap_us,
            "invalid_quote_time_us_union": invalid_quote_us,
            "invalid_quote_time_ratio": invalid_quote_ratio,
            "invalid_quote_time_ratio_max": MAX_INVALID_QUOTE_RATIO,
            "trade_gap_standalone_gate": False,
            "price_grid_violations": price_grid_violations,
            "size_grid_violations": size_grid_violations,
            "source_gate_pass": source_gate_pass,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quote", type=Path, required=True)
    parser.add_argument("--trade", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--symbol", default="XBTUSD")
    args = parser.parse_args()
    result = build(args.quote, args.trade, args.out, args.manifest, args.symbol)
    print(json.dumps(result, indent=2))
    return 0 if result["integrity"]["source_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
