#!/usr/bin/env python3
"""Export same-broker XAUUSD M1 spread evidence without sending orders.

The export is deliberately fail-closed: it only runs on the expected demo
account/server, requires terminal-side trading to be disabled, reads completed
M1 bars, and writes one bid/spread observation per bar.  It does not claim to
solve commission or slippage provenance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5


EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"
SYMBOL = "XAUUSD"
POINT = 0.01
FROM = datetime(2024, 1, 1, tzinfo=timezone.utc)
TO = datetime(2026, 7, 15, 23, 59, 59, tzinfo=timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def percentile(values: list[int], q: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--terminal",
        default=r"C:\Program Files\MetaTrader 5\terminal64.exe",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    args = parser.parse_args()

    if not mt5.initialize(path=args.terminal, timeout=30_000):
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
            raise SystemExit("Observed broker/server does not match the frozen export scope")
        if int(symbol.digits) != 2 or not math.isclose(float(symbol.point), POINT, abs_tol=1e-12):
            raise SystemExit("XAUUSD geometry does not match the frozen 2-digit/0.01-point scope")

        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, FROM, TO)
        if rates is None or len(rates) == 0:
            raise SystemExit(f"No M1 rates returned: {mt5.last_error()}")

        args.out.parent.mkdir(parents=True, exist_ok=True)
        spreads: list[int] = []
        dates: set[str] = set()
        zero_spread = 0
        first_timestamp = ""
        last_timestamp = ""
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["timestamp", "symbol", "bid", "ask"])
            for row in rates:
                timestamp = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
                text = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
                bid = float(row["close"])
                spread_points = int(row["spread"])
                if bid <= 0 or spread_points < 0:
                    raise SystemExit(f"Invalid M1 rate at {text}")
                ask = bid + spread_points * POINT
                writer.writerow([text, SYMBOL, f"{bid:.2f}", f"{ask:.2f}"])
                spreads.append(spread_points)
                dates.add(text[:10])
                zero_spread += int(spread_points == 0)
                first_timestamp = first_timestamp or text
                last_timestamp = text

        audit = {
            "schema_version": "unicorn_spread_export_audit.v1",
            "hypothesis_id": "HYP-UPS-XAU-M5-002",
            "mode": "READ_ONLY_DEMO_NO_ORDERS",
            "symbol": SYMBOL,
            "timeframe": "M1",
            "from": "2024.01.01",
            "to": "2026.07.15",
            "source_method": "MT5 CopyRates M1 close bid plus the same bar's reported spread points",
            "broker_company": EXPECTED_COMPANY,
            "server": EXPECTED_SERVER,
            "terminal_build": int(terminal.build),
            "terminal_trade_allowed": bool(terminal.trade_allowed),
            "account_trade_mode": "DEMO",
            "orders_sent": 0,
            "positions_opened": 0,
            "symbol_geometry": {"digits": 2, "point": POINT, "pip_size": POINT},
            "rows": len(spreads),
            "valid_rows": len(spreads),
            "coverage_ratio": 1.0,
            "unique_dates": len(dates),
            "first_timestamp_utc": first_timestamp,
            "last_timestamp_utc": last_timestamp,
            "zero_spread_rows": zero_spread,
            "spread_points": {
                "p50": percentile(spreads, 0.50),
                "p90": percentile(spreads, 0.90),
                "p99": percentile(spreads, 0.99),
                "max": max(spreads),
            },
            "source_csv": str(args.out.resolve()),
            "source_sha256": sha256_file(args.out),
            "remaining_blockers": [
                "No >=30 same-symbol XAUUSD commission lifecycles or explicit broker contract",
                "No >=100 independent-reference XAUUSD slippage fills with >=30 BUY and >=30 SELL",
            ],
        }
        args.audit_out.parent.mkdir(parents=True, exist_ok=True)
        args.audit_out.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
