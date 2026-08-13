"""Profile Dukascopy Jetta H1 OHLC geometry without reading price outcomes.

The profiler is deliberately source-only.  It decodes each monthly BID/ASK
payload, rounds prices to a nominated source point, and measures only whether
open/close lie outside the provider high/low envelope.  It never computes
returns, signals, trades, PnL, or any cross-bar price statistic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import dukascopy_jetta_h1 as jetta  # noqa: E402


SCHEMA = "alphafactory_dukascopy_jetta_h1_geometry_profile.v1"
AUTHORITY = "SOURCE_GEOMETRY_ONLY_NO_PERFORMANCE"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _round_to_point(value: float, point: float) -> float:
    return round(value / point) * point


def _decode_geometry(payload: bytes, label: str, point: float) -> dict[str, object]:
    row = jetta.load_json_bytes(payload, label)
    arrays = {
        name: jetta._number_array(row, name)
        for name in ("times", "opens", "highs", "lows", "closes", "volumes")
    }
    lengths = {len(values) for values in arrays.values()}
    if len(lengths) != 1:
        raise jetta.JettaH1Error(f"inconsistent Jetta arrays for {label}")
    count = lengths.pop()
    timestamp = int(jetta._finite_number(row.get("timestamp"), "timestamp"))
    multiplier = jetta._finite_number(row.get("multiplier", 1.0), "multiplier")
    shift = int(jetta._finite_number(row.get("shift", 1.0), "shift"))
    values = {
        name: jetta._finite_number(row.get(name), name)
        for name in ("open", "high", "low", "close")
    }
    if timestamp <= 0 or multiplier <= 0.0 or shift <= 0 or point <= 0.0:
        raise jetta.JettaH1Error(f"invalid profile metadata for {label}")

    corrections: list[int] = []
    high_corrections: list[int] = []
    low_corrections: list[int] = []
    violations: list[dict[str, int]] = []
    first_epoch: int | None = None
    last_epoch: int | None = None
    previous = -1
    open_points_by_epoch: dict[int, int] = {}
    for index in range(count):
        timestamp += shift * int(arrays["times"][index])
        for name in values:
            values[name] += multiplier * arrays[f"{name}s"][index]
        rounded = {name: _round_to_point(value, point) for name, value in values.items()}
        if timestamp <= previous or timestamp % 3_600_000 != 0:
            raise jetta.JettaH1Error(f"invalid H1 timestamp at bar {index} for {label}")
        if any(not math.isfinite(value) or value <= 0.0 for value in rounded.values()):
            raise jetta.JettaH1Error(f"invalid H1 price at bar {index} for {label}")
        high_deficit = max(rounded["open"], rounded["close"]) - rounded["high"]
        low_excess = rounded["low"] - min(rounded["open"], rounded["close"])
        high_points = max(0, int(math.ceil(high_deficit / point - 1e-8)))
        low_points = max(0, int(math.ceil(low_excess / point - 1e-8)))
        high_corrections.append(high_points)
        low_corrections.append(low_points)
        corrections.append(max(high_points, low_points))
        epoch = timestamp // 1000
        open_points_by_epoch[epoch] = int(round(rounded["open"] / point))
        if high_points > 0 or low_points > 0:
            violations.append(
                {
                    "epoch": epoch,
                    "high_correction_points": high_points,
                    "low_correction_points": low_points,
                    "required_envelope_correction_points": max(high_points, low_points),
                }
            )
        first_epoch = epoch if first_epoch is None else first_epoch
        last_epoch = epoch
        previous = timestamp

    return {
        "bar_count": count,
        "first_epoch": first_epoch,
        "last_epoch": last_epoch,
        "violating_bar_count": sum(value > 0 for value in corrections),
        "high_violation_count": sum(value > 0 for value in high_corrections),
        "low_violation_count": sum(value > 0 for value in low_corrections),
        "maximum_required_envelope_correction_points": max(corrections, default=0),
        "maximum_high_correction_points": max(high_corrections, default=0),
        "maximum_low_correction_points": max(low_corrections, default=0),
        "violations": violations,
        "open_points_by_epoch": open_points_by_epoch,
        "correction_points": corrections,
    }


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return int(ordered[index])


def _aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    corrections = [
        int(value)
        for row in rows
        for value in row.pop("correction_points")  # type: ignore[arg-type]
    ]
    violating = [value for value in corrections if value > 0]
    return {
        "bar_count": sum(int(row["bar_count"]) for row in rows),
        "violating_bar_count": sum(int(row["violating_bar_count"]) for row in rows),
        "violating_fraction": (
            sum(int(row["violating_bar_count"]) for row in rows)
            / max(1, sum(int(row["bar_count"]) for row in rows))
        ),
        "maximum_required_envelope_correction_points": max(corrections, default=0),
        "violating_only_correction_points_percentiles": {
            "p50": _percentile(violating, 0.50),
            "p90": _percentile(violating, 0.90),
            "p95": _percentile(violating, 0.95),
            "p99": _percentile(violating, 0.99),
            "p999": _percentile(violating, 0.999),
        },
    }


def _pair_open_stats(
    bid_points: dict[int, int], ask_points: dict[int, int]
) -> dict[str, object]:
    bid_times = set(bid_points)
    ask_times = set(ask_points)
    common = sorted(bid_times & ask_times)
    spreads = [ask_points[epoch] - bid_points[epoch] for epoch in common]
    crossed = [-value for value in spreads if value < 0]
    crossed_rows = [
        {
            "epoch": epoch,
            "bid_open_points": bid_points[epoch],
            "ask_open_points": ask_points[epoch],
            "crossed_open_deficit_points": bid_points[epoch] - ask_points[epoch],
        }
        for epoch in common
        if ask_points[epoch] < bid_points[epoch]
    ]
    return {
        "bid_timestamp_count": len(bid_times),
        "ask_timestamp_count": len(ask_times),
        "common_timestamp_count": len(common),
        "bid_only_timestamp_count": len(bid_times - ask_times),
        "ask_only_timestamp_count": len(ask_times - bid_times),
        "crossed_open_count": len(crossed),
        "crossed_open_fraction": len(crossed) / max(1, len(common)),
        "maximum_crossed_open_deficit_points": max(crossed, default=0),
        "crossed_open_deficit_points_percentiles": {
            "p50": _percentile(crossed, 0.50),
            "p90": _percentile(crossed, 0.90),
            "p95": _percentile(crossed, 0.95),
            "p99": _percentile(crossed, 0.99),
            "p999": _percentile(crossed, 0.999),
        },
        "minimum_uncrossed_spread_points": min(
            (value for value in spreads if value >= 0), default=None
        ),
        "maximum_uncrossed_spread_points": max(spreads, default=None),
        "crossed_open_rows": crossed_rows,
        "crossed_deficit_points": crossed,
    }


def _aggregate_open_pairs(
    rows: list[dict[str, object]], *, point: float, strategy_active_from_epoch: int
) -> dict[str, object]:
    crossed = [
        int(value)
        for row in rows
        for value in row.pop("crossed_deficit_points")  # type: ignore[arg-type]
    ]
    common = sum(int(row["common_timestamp_count"]) for row in rows)
    crossed_rows = [
        crossing
        for row in rows
        for crossing in row.get("crossed_open_rows", [])  # type: ignore[union-attr]
    ]
    before_activation = [
        crossing
        for crossing in crossed_rows
        if int(crossing["epoch"]) < strategy_active_from_epoch
    ]
    on_or_after_activation = [
        crossing
        for crossing in crossed_rows
        if int(crossing["epoch"]) >= strategy_active_from_epoch
    ]
    return {
        "common_timestamp_count": common,
        "bid_only_timestamp_count": sum(int(row["bid_only_timestamp_count"]) for row in rows),
        "ask_only_timestamp_count": sum(int(row["ask_only_timestamp_count"]) for row in rows),
        "crossed_open_count": len(crossed),
        "crossed_open_fraction": len(crossed) / max(1, common),
        "maximum_crossed_open_deficit_points": max(crossed, default=0),
        "maximum_crossed_open_deficit_price": max(crossed, default=0) * point,
        "crossed_open_deficit_points_percentiles": {
            "p50": _percentile(crossed, 0.50),
            "p90": _percentile(crossed, 0.90),
            "p95": _percentile(crossed, 0.95),
            "p99": _percentile(crossed, 0.99),
            "p999": _percentile(crossed, 0.999),
        },
        "strategy_active_from_epoch": strategy_active_from_epoch,
        "crossed_open_before_activation_count": len(before_activation),
        "crossed_open_on_or_after_activation_count": len(on_or_after_activation),
        "all_crossed_opens_strictly_pre_activation": len(crossed_rows) > 0
        and len(on_or_after_activation) == 0,
        "crossed_open_rows": crossed_rows,
    }


def build_profile(args: argparse.Namespace) -> int:
    contract, contract_sha = jetta.validate_contract(args.contract, args.contract_sha256)
    rows = contract["symbols"]
    assert isinstance(rows, list)
    selected = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("source_symbol") == args.symbol.upper()
    ]
    if len(selected) != 1:
        raise jetta.JettaH1Error(f"expected exactly one symbol row for {args.symbol}")
    row = selected[0]
    from_day = date.fromisoformat(str(row["history_from"]))
    to_exclusive = date.fromisoformat(str(row["history_to_exclusive"]))
    point = 10.0 ** (-args.digits)
    strategy_active_from_epoch = int(
        datetime.fromisoformat(str(row["strategy_active_from"]).replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .timestamp()
    )
    limiter = jetta.HostRateLimiter(jetta.MIN_REQUEST_INTERVAL_SECONDS)
    timeout = int(contract["download"]["timeout_seconds"])  # type: ignore[index]
    retries = int(contract["download"]["retries"])  # type: ignore[index]
    side_rows: dict[str, list[dict[str, object]]] = {"BID": [], "ASK": []}
    open_pair_rows: list[dict[str, object]] = []
    raw_receipts: list[dict[str, object]] = []

    for year, month in jetta.month_iter(from_day, to_exclusive):
        month_start, month_end = jetta._month_bounds(year, month)
        contract_end = int(
            datetime.fromisoformat(str(row["history_to_exclusive"]))
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
        partial = month_start * 1000 if contract_end < month_end else None
        month_receipt: dict[str, object] = {"year_month_utc": f"{year:04d}-{month:02d}"}
        for side in ("BID", "ASK"):
            raw_path = (
                args.data_root
                / "raw"
                / args.symbol.upper()
                / f"{year:04d}"
                / f"{month:02d}_{side.lower()}.json"
            )
            url = jetta.month_url(
                str(row["jetta_code"]), side, year, month, partial_from_msc=partial
            )
            if raw_path.is_file():
                payload = raw_path.read_bytes()
                acquisition = "retained_raw"
            else:
                payload, _headers = jetta.fetch_with_retry(url, timeout, retries, limiter)
                jetta.atomic_write(raw_path, payload)
                acquisition = "official_fetch"
            stats = _decode_geometry(
                payload, f"{args.symbol.upper()} {year:04d}-{month:02d} {side}", point
            )
            side_rows[side].append(stats)
            month_receipt[side.lower()] = {
                "url": url,
                "path": raw_path.resolve().as_posix(),
                "sha256": _sha256_bytes(payload),
                "bytes": len(payload),
                "acquisition": acquisition,
                "bar_count": stats["bar_count"],
                "violating_bar_count": stats["violating_bar_count"],
                "maximum_required_envelope_correction_points": stats[
                    "maximum_required_envelope_correction_points"
                ],
                "violations": stats["violations"],
            }
        bid_open_points = side_rows["BID"][-1].pop("open_points_by_epoch")
        ask_open_points = side_rows["ASK"][-1].pop("open_points_by_epoch")
        assert isinstance(bid_open_points, dict) and isinstance(ask_open_points, dict)
        pair_stats = _pair_open_stats(bid_open_points, ask_open_points)
        open_pair_rows.append(pair_stats)
        month_receipt["bid_ask_open_pairing"] = {
            key: value
            for key, value in pair_stats.items()
            if key != "crossed_deficit_points"
        }
        raw_receipts.append(month_receipt)
        print(
            f"PROFILE {args.symbol.upper()} {year:04d}-{month:02d} "
            f"BID_MAX={side_rows['BID'][-1]['maximum_required_envelope_correction_points']} "
            f"ASK_MAX={side_rows['ASK'][-1]['maximum_required_envelope_correction_points']} "
            f"CROSSED_OPEN={pair_stats['crossed_open_count']} "
            f"CROSS_MAX={pair_stats['maximum_crossed_open_deficit_points']}",
            flush=True,
        )

    payload = {
        "schema_version": SCHEMA,
        "authority": AUTHORITY,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "hypothesis_id": contract["hypothesis_id"],
        "symbol": args.symbol.upper(),
        "source_contract": {"path": args.contract.resolve().as_posix(), "sha256": contract_sha},
        "profile_rule": {
            "digits": args.digits,
            "point": point,
            "measurement": "Round each same-bar O/H/L/C to point; count the minimum whole points needed to expand H/L so it contains O/C.",
            "cross_bar_returns_or_pnl_read": False,
        },
        "sides": {side: _aggregate(rows) for side, rows in side_rows.items()},
        "bid_ask_open_pairing": _aggregate_open_pairs(
            open_pair_rows,
            point=point,
            strategy_active_from_epoch=strategy_active_from_epoch,
        ),
        "months": raw_receipts,
    }
    jetta.write_json_atomic(args.output, payload)
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": args.output.resolve().as_posix(),
                "sha256": jetta.sha256_file(args.output),
                "sides": payload["sides"],
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Outcome-blind Jetta H1 geometry profiler")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--digits", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return build_profile(args)
    except jetta.JettaH1Error as exc:
        print(f"FATAL {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
