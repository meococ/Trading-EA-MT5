#!/usr/bin/env python3
"""Export raw same-broker BID/ASK samples without orders or outcome access.

The producer selects the first valid raw tick inside every synchronized M5 bar
in the requested window.  Coverage is measured against the actual MT5 M5 bar
population, not against the number of rows that happened to be written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d").replace(tzinfo=timezone.utc)


def is_d_path(path: Path) -> bool:
    return path.resolve().drive.upper() == "D:"


def first_valid_tick_by_bar(
    ticks: Iterable[Mapping[str, Any]],
    expected_bar_epochs: set[int],
    *,
    bar_seconds: int = 300,
) -> dict[int, tuple[int, float, float]]:
    """Return the earliest valid raw BID/ASK tick for each expected bar."""
    selected: dict[int, tuple[int, float, float]] = {}
    for row in ticks:
        epoch = int(row["time"])
        bar_epoch = epoch - epoch % bar_seconds
        if bar_epoch not in expected_bar_epochs:
            continue
        bid = float(row["bid"])
        ask = float(row["ask"])
        time_msc = int(row["time_msc"])
        if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0 or ask < bid:
            continue
        current = selected.get(bar_epoch)
        if current is None or time_msc < current[0]:
            selected[bar_epoch] = (time_msc, bid, ask)
    return selected


def first_valid_tick_by_bar_array(
    ticks: Any,
    expected_bar_epochs: set[int],
    *,
    bar_seconds: int = 300,
) -> dict[int, tuple[int, float, float]]:
    """Vectorized equivalent for MetaTrader5 NumPy structured arrays."""
    import numpy as np

    if len(ticks) == 0 or not expected_bar_epochs:
        return {}
    names = set(ticks.dtype.names or ())
    required = {"time", "time_msc", "bid", "ask"}
    if not required.issubset(names):
        raise ValueError(f"tick array is missing fields: {sorted(required - names)}")

    epochs = np.asarray(ticks["time"], dtype=np.int64)
    time_msc = np.asarray(ticks["time_msc"], dtype=np.int64)
    bid = np.asarray(ticks["bid"], dtype=np.float64)
    ask = np.asarray(ticks["ask"], dtype=np.float64)
    bar_epochs = epochs - epochs % bar_seconds
    expected = np.fromiter(expected_bar_epochs, dtype=np.int64)
    valid = (
        np.isin(bar_epochs, expected)
        & np.isfinite(bid)
        & np.isfinite(ask)
        & (bid > 0.0)
        & (ask >= bid)
    )
    valid_indices = np.flatnonzero(valid)
    if valid_indices.size == 0:
        return {}

    # Raw MT5 order is the final tie-breaker when multiple quotes share one
    # millisecond, matching the scalar first-seen contract deterministically.
    order = np.lexsort(
        (valid_indices, time_msc[valid_indices], bar_epochs[valid_indices])
    )
    ordered_indices = valid_indices[order]
    ordered_bars = bar_epochs[ordered_indices]
    first = np.empty(ordered_indices.size, dtype=bool)
    first[0] = True
    first[1:] = ordered_bars[1:] != ordered_bars[:-1]
    selected_indices = ordered_indices[first]
    return {
        int(bar_epochs[index]): (
            int(time_msc[index]),
            float(bid[index]),
            float(ask[index]),
        )
        for index in selected_indices
    }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--terminal-sha256", required=True)
    parser.add_argument("--expected-server", required=True)
    parser.add_argument("--expected-company", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--digits", type=int, required=True)
    parser.add_argument("--point", type=float, required=True)
    parser.add_argument("--from", dest="date_from", required=True)
    parser.add_argument("--to", dest="date_to", required=True)
    parser.add_argument("--chunk-days", type=int, default=1)
    parser.add_argument("--min-population-coverage", type=float, default=0.99)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()

    if args.chunk_days <= 0:
        raise ValueError("chunk-days must be positive")
    if not 0.99 <= args.min_population_coverage <= 1.0:
        raise ValueError("min-population-coverage must be between 0.99 and 1.0")
    terminal_path = args.terminal.resolve()
    output = args.out.resolve()
    receipt_out = args.receipt_out.resolve()
    for path, label in (
        (terminal_path, "terminal"),
        (output, "spread evidence output"),
        (receipt_out, "receipt output"),
    ):
        if not is_d_path(path):
            raise ValueError(f"{label} must remain on D: {path}")
    if sha256_file(terminal_path) != args.terminal_sha256.upper():
        raise ValueError("terminal SHA256 does not match the frozen authority")

    start = parse_date(args.date_from)
    end_exclusive = parse_date(args.date_to) + timedelta(days=1)
    if end_exclusive <= start:
        raise ValueError("requested spread window is invalid")

    try:
        import MetaTrader5 as mt5
    except Exception as exc:  # pragma: no cover - host dependent
        raise RuntimeError(f"MetaTrader5 import failed: {exc}") from exc

    if not mt5.initialize(path=str(terminal_path), timeout=60_000, portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        if not bool(terminal.connected) or bool(terminal.trade_allowed):
            raise RuntimeError("terminal must be connected with trading disabled")
        if not is_d_path(Path(str(terminal.data_path))):
            raise RuntimeError("terminal data_path must remain on D:")
        if str(account.server) != args.expected_server or str(account.company) != args.expected_company:
            raise RuntimeError("broker/server identity does not match the frozen scope")
        if not mt5.symbol_select(args.symbol, True):
            raise RuntimeError(f"symbol_select failed: {mt5.last_error()}")
        symbol_info = mt5.symbol_info(args.symbol)
        if symbol_info is None:
            raise RuntimeError(f"symbol_info unavailable: {args.symbol}")
        if int(symbol_info.digits) != args.digits or not math.isclose(
            float(symbol_info.point), args.point, rel_tol=0.0, abs_tol=1e-12
        ):
            raise RuntimeError("symbol geometry does not match the frozen scope")

        rates = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M5, start, end_exclusive)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"M5 population unavailable: {mt5.last_error()}")
        expected = {
            int(row["time"])
            for row in rates
            if int(start.timestamp()) <= int(row["time"]) < int(end_exclusive.timestamp())
        }
        if not expected:
            raise RuntimeError("requested M5 population is empty")

        selected: dict[int, tuple[int, float, float]] = {}
        raw_tick_count = 0
        cursor = start
        while cursor < end_exclusive:
            chunk_end = min(end_exclusive, cursor + timedelta(days=args.chunk_days))
            ticks = mt5.copy_ticks_range(args.symbol, cursor, chunk_end, mt5.COPY_TICKS_ALL)
            if ticks is None:
                raise RuntimeError(
                    f"copy_ticks_range failed for {cursor.isoformat()} to "
                    f"{chunk_end.isoformat()}: {mt5.last_error()}"
                )
            chunk_start_msc = int(cursor.timestamp() * 1000)
            chunk_end_msc = int(chunk_end.timestamp() * 1000)
            if getattr(getattr(ticks, "dtype", None), "names", None):
                tick_times_msc = ticks["time_msc"]
                ticks = ticks[
                    (tick_times_msc >= chunk_start_msc)
                    & (tick_times_msc < chunk_end_msc)
                ]
            else:  # pragma: no cover - defensive fallback for non-MT5 adapters
                ticks = [
                    tick
                    for tick in ticks
                    if chunk_start_msc <= int(tick["time_msc"]) < chunk_end_msc
                ]
            raw_tick_count += len(ticks)
            chunk_expected = {
                epoch
                for epoch in expected
                if int(cursor.timestamp()) <= epoch < int(chunk_end.timestamp())
            }
            if getattr(getattr(ticks, "dtype", None), "names", None):
                chunk_selected = first_valid_tick_by_bar_array(ticks, chunk_expected)
            else:  # pragma: no cover - defensive fallback for non-MT5 adapters
                chunk_selected = first_valid_tick_by_bar(ticks, chunk_expected)
            selected.update(chunk_selected)
            cursor = chunk_end

        population_count = len(expected)
        sample_count = len(selected)
        population_ratio = sample_count / population_count
        if population_ratio < args.min_population_coverage:
            raise RuntimeError(
                f"raw tick population coverage {population_ratio:.8f} is below "
                f"{args.min_population_coverage:.8f}"
            )

        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(["timestamp", "symbol", "bid", "ask"])
                for bar_epoch in sorted(selected):
                    time_msc, bid, ask = selected[bar_epoch]
                    timestamp = datetime.fromtimestamp(time_msc / 1000.0, tz=timezone.utc)
                    writer.writerow(
                        [
                            timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                            args.symbol,
                            f"{bid:.{args.digits}f}",
                            f"{ask:.{args.digits}f}",
                        ]
                    )
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)

        ordered_bars = sorted(selected)
        receipt = {
            "schema_version": "alphafactory_mt5_tick_spread_evidence.v1",
            "mode": "READ_ONLY_RAW_TICKS_NO_ORDERS_NO_OUTCOMES",
            "promotion_eligible": False,
            "symbol": args.symbol,
            "timeframe_population": "M5",
            "from": args.date_from,
            "to": args.date_to,
            "source_method": "first valid CopyTicksRange raw BID/ASK tick in each synchronized M5 bar",
            "broker": str(account.company),
            "server": str(account.server),
            "terminal_build": int(terminal.build),
            "terminal_path": str(terminal_path),
            "terminal_sha256": sha256_file(terminal_path),
            "terminal_data_path": str(terminal.data_path),
            "terminal_trade_allowed": bool(terminal.trade_allowed),
            "orders_sent": 0,
            "positions_opened": 0,
            "outcomes_accessed": False,
            "symbol_geometry": {
                "digits": args.digits,
                "point": args.point,
                "pip_size": 0.01 if args.symbol.endswith("JPY") else args.point * 10,
            },
            "coverage": {
                "expected_m5_bar_count": population_count,
                "sampled_m5_bar_count": sample_count,
                "missing_m5_bar_count": population_count - sample_count,
                "raw_tick_count": raw_tick_count,
                "population_coverage_ratio": population_ratio,
                "minimum_required": args.min_population_coverage,
                "first_sampled_bar_utc": datetime.fromtimestamp(
                    ordered_bars[0], tz=timezone.utc
                ).isoformat(),
                "last_sampled_bar_utc": datetime.fromtimestamp(
                    ordered_bars[-1], tz=timezone.utc
                ).isoformat(),
            },
            "output": str(output),
            "output_sha256": sha256_file(output),
            "output_bytes": output.stat().st_size,
            "generator": str(Path(__file__).resolve()),
            "generator_sha256": sha256_file(Path(__file__).resolve()),
        }
        atomic_json(receipt_out, receipt)
        print(json.dumps(receipt, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
