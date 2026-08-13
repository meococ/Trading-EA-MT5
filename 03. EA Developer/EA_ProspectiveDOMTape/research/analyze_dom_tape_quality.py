#!/usr/bin/env python3
"""Outcome-blind structural quality audit for stopped DOM tape v1.1."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY")


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p50": None, "p95": None, "max": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, int(0.95 * (len(ordered) - 1)))
    return {
        "min": ordered[0],
        "p50": statistics.median(ordered),
        "p95": ordered[p95_index],
        "max": ordered[-1],
    }


def pct(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else part / whole


def analyze(json_path: Path, csv_path: Path) -> dict[str, Any]:
    snapshots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sessions: dict[str, list[int]] = defaultdict(list)
    kinds: Counter[str] = Counter()
    records = 0
    with json_path.open("r", encoding="utf-8-sig") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            records += 1
            kinds[str(row.get("kind"))] += 1
            session = str(row.get("session_id", ""))
            tick = row.get("tick64")
            if session and isinstance(tick, int):
                sessions[session].append(tick)
            if row.get("kind") == "SNAPSHOT":
                snapshots[str(row["symbol"])].append(row)

    result_symbols: dict[str, Any] = {}
    total_levels = 0
    total_modal = 0
    all_volume_values: Counter[int] = Counter()
    all_volume_real_values: Counter[float] = Counter()
    for symbol in SYMBOLS:
        rows = snapshots[symbol]
        volumes: Counter[int] = Counter()
        volumes_real: Counter[float] = Counter()
        depths: list[float] = []
        spreads: list[float] = []
        outer_ask_gaps: list[float] = []
        outer_bid_gaps: list[float] = []
        imbalance: list[float] = []
        shapes: Counter[tuple[tuple[int, int, float], ...]] = Counter()
        one_sided = 0
        crossed = 0
        constant_volume_snapshots = 0
        same_shape_transitions = 0
        transitions = 0
        previous_shape: tuple[tuple[int, int, float], ...] | None = None
        for row in rows:
            levels = row["levels"]
            depths.append(float(len(levels)))
            shape = tuple((int(x["type"]), int(x["volume"]), float(x["volume_real"])) for x in levels)
            shapes[shape] += 1
            if previous_shape is not None:
                transitions += 1
                same_shape_transitions += int(shape == previous_shape)
            previous_shape = shape
            snapshot_volumes = {int(x["volume"]) for x in levels}
            if len(snapshot_volumes) == 1:
                constant_volume_snapshots += 1
            for level in levels:
                volumes[int(level["volume"])] += 1
                volumes_real[float(level["volume_real"])] += 1
            asks = [float(x["price"]) for x in levels if int(x["type"]) == 1]
            bids = [float(x["price"]) for x in levels if int(x["type"]) == 2]
            if not asks or not bids:
                one_sided += 1
                continue
            best_ask = min(asks)
            best_bid = max(bids)
            spread = best_ask - best_bid
            crossed += int(spread <= 0)
            spreads.append(spread)
            outer_ask_gaps.append(max(asks) - best_ask)
            outer_bid_gaps.append(best_bid - min(bids))
            bid_volume = sum(float(x["volume_real"]) for x in levels if int(x["type"]) == 2)
            ask_volume = sum(float(x["volume_real"]) for x in levels if int(x["type"]) == 1)
            imbalance.append((bid_volume - ask_volume) / (bid_volume + ask_volume))

        level_count = sum(volumes.values())
        modal_volume, modal_count = volumes.most_common(1)[0] if volumes else (None, 0)
        total_levels += level_count
        total_modal += modal_count
        all_volume_values.update(volumes)
        all_volume_real_values.update(volumes_real)
        result_symbols[symbol] = {
            "snapshots": len(rows),
            "levels": level_count,
            "depth": quantiles(depths),
            "unique_volume_values": len(volumes),
            "unique_volume_real_values": len(volumes_real),
            "modal_volume": modal_volume,
            "modal_volume_share": pct(modal_count, level_count),
            "constant_volume_snapshot_share": pct(constant_volume_snapshots, len(rows)),
            "unique_type_volume_shapes": len(shapes),
            "top_shape_share": pct(shapes.most_common(1)[0][1], len(rows)) if rows else 0.0,
            "same_shape_transition_share": pct(same_shape_transitions, transitions),
            "one_sided_books": one_sided,
            "crossed_or_locked_books": crossed,
            "spread": quantiles(spreads),
            "outer_ask_gap": quantiles(outer_ask_gaps),
            "outer_bid_gap": quantiles(outer_bid_gaps),
            "level_count_imbalance": quantiles(imbalance),
        }

    session_metrics = {}
    observed_seconds = 0.0
    for session, ticks in sessions.items():
        duration = 0.0 if not ticks else (max(ticks) - min(ticks)) / 1000.0
        observed_seconds += duration
        session_metrics[session] = {"records_with_tick": len(ticks), "duration_seconds": duration}
    size_bytes = json_path.stat().st_size + csv_path.stat().st_size
    projected = None if observed_seconds <= 0 else size_bytes / observed_seconds * 86400.0
    return {
        "files": {
            "json_bytes": json_path.stat().st_size,
            "csv_bytes": csv_path.stat().st_size,
            "combined_bytes": size_bytes,
            "combined_sha256_not_recomputed_here": True,
        },
        "records": records,
        "kind_counts": dict(sorted(kinds.items())),
        "sessions": session_metrics,
        "observed_seconds_sum": observed_seconds,
        "projected_bytes_per_day_at_smoke_rate": projected,
        "all_symbols": {
            "levels": total_levels,
            "unique_volume_values": len(all_volume_values),
            "unique_volume_real_values": len(all_volume_real_values),
            "modal_volume": all_volume_values.most_common(1)[0][0] if all_volume_values else None,
            "modal_volume_share": pct(total_modal, total_levels),
        },
        "symbols": result_symbols,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path", type=Path)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = analyze(args.json_path, args.csv_path)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.json_out:
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
