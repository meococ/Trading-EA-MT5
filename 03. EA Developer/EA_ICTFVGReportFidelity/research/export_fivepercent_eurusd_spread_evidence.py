#!/usr/bin/env python3
"""Export read-only FivePercent EURUSD M1 spread evidence for 2019-2022.

This acquisition is deliberately separated from strategy execution. It may
prove that the broker's reported M1 spread column is usable, or fail that gate;
it never sends an order and never upgrades the result to promotion evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, time, timezone
from pathlib import Path

import MetaTrader5 as mt5


EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"
SYMBOL = "EURUSD"
DIGITS = 5
POINT = 0.00001
PIP_SIZE = 0.0001
DEFAULT_FROM = "2019.01.01"
DEFAULT_TO = "2022.12.31"
MAX_ZERO_SPREAD_RATIO = 0.001
MIN_ROWS = 1_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def nearest_rank(values: list[int], quantile: float) -> int:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def utc_bounds(date_from: str, date_to: str) -> tuple[datetime, datetime]:
    start_date = datetime.strptime(date_from, "%Y.%m.%d").date()
    end_date = datetime.strptime(date_to, "%Y.%m.%d").date()
    if end_date < start_date:
        raise ValueError("end date precedes start date")
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date, time.max, tzinfo=timezone.utc),
    )


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--from", dest="date_from", default=DEFAULT_FROM)
    parser.add_argument("--to", dest="date_to", default=DEFAULT_TO)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()

    start, end = utc_bounds(args.date_from, args.date_to)
    if not mt5.initialize(path=args.terminal, portable=True, timeout=30_000):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        symbol = mt5.symbol_info(SYMBOL)
        if terminal is None or account is None or symbol is None:
            raise SystemExit(f"MT5 metadata unavailable: {mt5.last_error()}")
        if terminal.trade_allowed:
            raise SystemExit("Refusing export while terminal-side trading is enabled")
        if int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO):
            raise SystemExit("Refusing export from a non-demo account")
        if str(account.server) != EXPECTED_SERVER or str(account.company) != EXPECTED_COMPANY:
            raise SystemExit("Observed broker/server does not match the frozen scope")
        if int(symbol.digits) != DIGITS or not math.isclose(
            float(symbol.point), POINT, abs_tol=1e-12
        ):
            raise SystemExit("EURUSD geometry does not match 5-digit/0.00001-point scope")

        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, start, end)
        if rates is None or len(rates) == 0:
            raise SystemExit(f"No M1 rates returned: {mt5.last_error()}")

        args.out.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.out.with_name(f".{args.out.name}.{os.getpid()}.tmp")
        spreads: list[int] = []
        dates: set[str] = set()
        first_timestamp = ""
        last_timestamp = ""
        try:
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(["timestamp", "symbol", "bid", "ask"])
                for row in rates:
                    timestamp = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
                    timestamp_text = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
                    bid = float(row["close"])
                    spread_points = int(row["spread"])
                    if bid <= 0 or spread_points < 0:
                        raise SystemExit(f"Invalid M1 rate at {timestamp_text}")
                    ask = bid + spread_points * POINT
                    writer.writerow(
                        [timestamp_text, SYMBOL, f"{bid:.{DIGITS}f}", f"{ask:.{DIGITS}f}"]
                    )
                    spreads.append(spread_points)
                    dates.add(timestamp_text[:10])
                    first_timestamp = first_timestamp or timestamp_text
                    last_timestamp = timestamp_text
            temporary.replace(args.out)
        finally:
            temporary.unlink(missing_ok=True)

        zero_rows = sum(value == 0 for value in spreads)
        zero_ratio = zero_rows / len(spreads)
        full_boundary_coverage = (
            first_timestamp[:4] == args.date_from[:4]
            and last_timestamp[:4] == args.date_to[:4]
        )
        spread_usable = (
            len(spreads) >= MIN_ROWS
            and full_boundary_coverage
            and zero_ratio <= MAX_ZERO_SPREAD_RATIO
            and nearest_rank(spreads, 0.50) > 0
        )
        audit = {
            "schema_version": "ictfvg_eurusd_spread_export_audit.v1",
            "hypothesis_id": "HYP-ICT-FVG-FID-EURUSD-M5-001",
            "mode": "READ_ONLY_DEMO_NO_ORDERS",
            "symbol": SYMBOL,
            "timeframe": "M1",
            "from": args.date_from,
            "to": args.date_to,
            "source_method": "MT5 CopyRates M1 close bid plus same-bar reported spread points",
            "broker_company": EXPECTED_COMPANY,
            "server": EXPECTED_SERVER,
            "terminal_build": int(terminal.build),
            "terminal_trade_allowed": bool(terminal.trade_allowed),
            "account_trade_mode": "DEMO",
            "orders_sent": 0,
            "positions_opened": 0,
            "symbol_geometry": {"digits": DIGITS, "point": POINT, "pip_size": PIP_SIZE},
            "rows": len(spreads),
            "unique_dates": len(dates),
            "first_timestamp_utc": first_timestamp,
            "last_timestamp_utc": last_timestamp,
            "full_boundary_coverage": full_boundary_coverage,
            "zero_spread_rows": zero_rows,
            "zero_spread_ratio": zero_ratio,
            "max_zero_spread_ratio": MAX_ZERO_SPREAD_RATIO,
            "spread_points": {
                "p50": nearest_rank(spreads, 0.50),
                "p90": nearest_rank(spreads, 0.90),
                "p99": nearest_rank(spreads, 0.99),
                "max": max(spreads),
            },
            "source_csv": str(args.out.resolve()),
            "source_sha256": sha256_file(args.out),
            "spread_column_usable_as_cost": spread_usable,
            "promotion_eligible": False,
            "verdict": "PASS_SPREAD_PROVENANCE_ONLY" if spread_usable else "FAIL_SPREAD_COST_PROVENANCE",
            "remaining_requirements": [
                "At least 30 same-symbol commission lifecycles or a hash-bound broker contract",
                "At least 100 direction-aware slippage observations with 30 per side",
                "Historical news feed remains a separate gate",
            ],
        }
        atomic_json(args.audit_out, audit)
        print(json.dumps(audit, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
