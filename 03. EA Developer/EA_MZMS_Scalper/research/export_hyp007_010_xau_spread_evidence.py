#!/usr/bin/env python3
"""Campaign-specific read-only XAUUSD M1 spread export for MZMS HYP-007..010.

Uses the portable D: FivePercent terminal. Sends no orders. Exports every
available completed M1 bar/spread in 2018.01.01-2026.07.22 and records honest
coverage, missing calendar days, broker identity, and promotion=false.

Also stages the already-hashed Unicorn research-only commission and
quote-latency proxy sources without relabelling them as fills.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_MZMS_Scalper"
EVIDENCE = PACKAGE / "research" / "evidence"

DEFAULT_TERMINAL = (
    ROOT
    / "02. AlphaFactory"
    / "runtime"
    / "mt5-portable-fivepercent"
    / "terminal64.exe"
)

SYMBOL = "XAUUSD"
POINT = 0.01
PIP_SIZE = 0.01
DIGITS = 2
FROM_DATE = date(2018, 1, 1)
TO_DATE = date(2026, 7, 22)
FROM_DT = datetime(2018, 1, 1, tzinfo=timezone.utc)
TO_DT = datetime(2026, 7, 22, 23, 59, 59, tzinfo=timezone.utc)
FROM_TEXT = "2018.01.01"
TO_TEXT = "2026.07.22"
CAMPAIGN_ID = "HYP-MZMS-XAU-M5-007-010"

SPREAD_CSV = EVIDENCE / f"{CAMPAIGN_ID}_HISTORICAL_SPREAD_M1.csv"
AUDIT_JSON = EVIDENCE / f"{CAMPAIGN_ID}_SPREAD_EXPORT_AUDIT.json"
COMMISSION_CSV = EVIDENCE / f"{CAMPAIGN_ID}_TESTER_COMMISSION_MAX.csv"
QUOTE_CSV = EVIDENCE / f"{CAMPAIGN_ID}_QUOTE_LATENCY_1000MS.csv"
PROXY_RECEIPT = EVIDENCE / f"{CAMPAIGN_ID}_RESEARCH_COST_PROXY_RECEIPT.json"

UNICORN_COMMISSION = (
    ROOT
    / "03. EA Developer"
    / "EA_UnicornPrecisionScalper"
    / "research"
    / "evidence"
    / "HYP-UPS-XAU-M5-003_TESTER_COMMISSION_MAX.csv"
)
UNICORN_QUOTE = (
    ROOT
    / "03. EA Developer"
    / "EA_UnicornPrecisionScalper"
    / "research"
    / "evidence"
    / "HYP-UPS-XAU-M5-003_QUOTE_LATENCY_1000MS.csv"
)
UNICORN_RECEIPT = (
    ROOT
    / "03. EA Developer"
    / "EA_UnicornPrecisionScalper"
    / "research"
    / "evidence"
    / "HYP-UPS-XAU-M5-003_RESEARCH_COST_PROXY_RECEIPT.json"
)

EXPECTED_COMMISSION_SHA256 = "EE5BD051D400D0E49177671DA9AC9C082DC3EBA54F0D45E39566B4AA2744CCEF"
EXPECTED_QUOTE_SHA256 = "515619377D67EADAC3B4A55AFCEE49FC2C5A7EE3D39BBE07B54316D9B9A4836E"

EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def percentile(values: list[int], q: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def expected_market_days(start: date, end: date) -> list[date]:
    # Count Mon-Fri only. XAU also prints Sunday evening bars when present, but
    # Sunday is partial and must not inflate the missing-day denominator.
    days: list[date] = []
    for day in daterange(start, end):
        if day.weekday() <= 4:
            days.append(day)
    return days


def count_orders_positions() -> dict[str, int]:
    orders = mt5.orders_total()
    positions = mt5.positions_total()
    if orders is None or positions is None:
        raise RuntimeError(f"orders/positions query failed: {mt5.last_error()}")
    return {"orders": int(orders), "positions": int(positions)}


def stage_proxy_sources() -> dict[str, Any]:
    if not UNICORN_COMMISSION.is_file() or not UNICORN_QUOTE.is_file():
        raise FileNotFoundError("Unicorn research-proxy commission/quote sources are missing")
    commission_hash = sha256_file(UNICORN_COMMISSION)
    quote_hash = sha256_file(UNICORN_QUOTE)
    if commission_hash != EXPECTED_COMMISSION_SHA256:
        raise ValueError(
            f"Unicorn commission SHA mismatch: expected {EXPECTED_COMMISSION_SHA256}, got {commission_hash}"
        )
    if quote_hash != EXPECTED_QUOTE_SHA256:
        raise ValueError(
            f"Unicorn quote-latency SHA mismatch: expected {EXPECTED_QUOTE_SHA256}, got {quote_hash}"
        )

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(UNICORN_COMMISSION, COMMISSION_CSV)
    shutil.copy2(UNICORN_QUOTE, QUOTE_CSV)
    staged_commission_hash = sha256_file(COMMISSION_CSV)
    staged_quote_hash = sha256_file(QUOTE_CSV)
    if staged_commission_hash != EXPECTED_COMMISSION_SHA256:
        raise ValueError("Staged commission hash drifted after copy")
    if staged_quote_hash != EXPECTED_QUOTE_SHA256:
        raise ValueError("Staged quote-latency hash drifted after copy")

    receipt: dict[str, Any] = {
        "schema_version": "alphafactory_research_cost_proxy_evidence.v1",
        "campaign_id": CAMPAIGN_ID,
        "promotion_eligible": False,
        "fill_observed": False,
        "symbol": SYMBOL,
        "window": {"from": FROM_TEXT, "to": TO_TEXT},
        "reuse_policy": (
            "Copied already-hashed Unicorn XAU research-only commission and "
            "quote-latency proxy sources. Explicit non-fill / tester-simulation "
            "limitations are preserved; no fill provenance is claimed."
        ),
        "tester_commission_proxy": {
            "source_kind": "strategy_tester_simulation",
            "statistic_used": "maximum",
            "value": 4.4,
            "sample_count": 335,
            "source_original": str(UNICORN_COMMISSION.relative_to(ROOT).as_posix()),
            "source_original_sha256": EXPECTED_COMMISSION_SHA256,
            "output": str(COMMISSION_CSV.relative_to(ROOT).as_posix()),
            "output_sha256": staged_commission_hash,
            "limitation": "Strategy Tester simulation only; not observed live fills",
        },
        "quote_latency_proxy": {
            "fill_observed": False,
            "independent_quote_reference": True,
            "independent_reference": False,
            "fixed_latency_ms": 1000,
            "max_quote_wait_ms": 500,
            "sample_count": 31176,
            "buy_count": 15588,
            "sell_count": 15588,
            "p90_buy": 40.000000000009095,
            "p90_sell": 40.000000000009095,
            "p90_roundturn": 80.00000000001819,
            "source_original": str(UNICORN_QUOTE.relative_to(ROOT).as_posix()),
            "source_original_sha256": EXPECTED_QUOTE_SHA256,
            "output": str(QUOTE_CSV.relative_to(ROOT).as_posix()),
            "output_sha256": staged_quote_hash,
            "limitation": "Non-overlapping fixed-latency future executable quote proxy; no fill claimed",
        },
        "lineage_receipt_original": str(UNICORN_RECEIPT.relative_to(ROOT).as_posix())
        if UNICORN_RECEIPT.is_file()
        else "",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    PROXY_RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    terminal = DEFAULT_TERMINAL
    if not terminal.is_file():
        raise SystemExit(f"Portable MT5 terminal missing: {terminal}")

    proxy_receipt = stage_proxy_sources()

    if not mt5.initialize(path=str(terminal), timeout=60_000):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")

    try:
        terminal_info = mt5.terminal_info()
        account = mt5.account_info()
        symbol = mt5.symbol_info(SYMBOL)
        if terminal_info is None or account is None or symbol is None:
            raise SystemExit(f"MT5 metadata unavailable: {mt5.last_error()}")

        trade_mode = int(account.trade_mode)
        trade_allowed = bool(terminal_info.trade_allowed)
        # Safety: never export from a live account while terminal trading is armed.
        # Demo may still have AlgoTrading enabled on the portable terminal; this
        # exporter still sends zero orders and verifies orders/positions unchanged.
        if trade_mode == int(mt5.ACCOUNT_TRADE_MODE_REAL) and trade_allowed:
            raise SystemExit("Refusing export from REAL account while terminal trading is enabled")
        if trade_mode not in (
            int(mt5.ACCOUNT_TRADE_MODE_DEMO),
            int(mt5.ACCOUNT_TRADE_MODE_CONTEST),
            int(mt5.ACCOUNT_TRADE_MODE_REAL),
        ):
            raise SystemExit(f"Unsupported account trade_mode={trade_mode}")
        if trade_mode == int(mt5.ACCOUNT_TRADE_MODE_REAL) and not trade_allowed:
            # Read-only real account with AlgoTrading off is acceptable for history export.
            pass

        company = str(account.company)
        server = str(account.server)
        if company != EXPECTED_COMPANY or server != EXPECTED_SERVER:
            raise SystemExit(
                f"Broker/server mismatch: company={company!r} server={server!r}; "
                f"expected {EXPECTED_COMPANY!r}/{EXPECTED_SERVER!r}"
            )
        if int(symbol.digits) != DIGITS or not math.isclose(float(symbol.point), POINT, abs_tol=1e-12):
            raise SystemExit("XAUUSD geometry does not match frozen 2-digit / 0.01-point scope")

        before = count_orders_positions()
        EVIDENCE.mkdir(parents=True, exist_ok=True)

        reuse_existing = False
        spreads: list[int] = []
        dates: set[str] = set()
        zero_spread = 0
        first_timestamp = ""
        last_timestamp = ""

        if SPREAD_CSV.is_file() and SPREAD_CSV.stat().st_size > 1_000_000:
            # Fast path: re-audit an already-exported full dump without re-pulling
            # multi-million M1 bars (still identity-checked against live terminal).
            with SPREAD_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                required_cols = {"timestamp", "symbol", "bid", "ask"}
                if required_cols - set(reader.fieldnames or []):
                    raise SystemExit("Existing spread CSV is missing required columns")
                for row_number, row in enumerate(reader, start=2):
                    if str(row.get("symbol") or "") != SYMBOL:
                        raise SystemExit(f"Existing spread CSV symbol mismatch at row {row_number}")
                    text = str(row.get("timestamp") or "").strip()
                    bid = float(str(row.get("bid") or "nan"))
                    ask = float(str(row.get("ask") or "nan"))
                    if not math.isfinite(bid) or not math.isfinite(ask) or not 0 < bid <= ask:
                        raise SystemExit(f"Existing spread CSV invalid bid/ask at row {row_number}")
                    spread_points = int(round((ask - bid) / POINT))
                    spreads.append(spread_points)
                    dates.add(text[:10])
                    zero_spread += int(spread_points == 0)
                    first_timestamp = first_timestamp or text
                    last_timestamp = text
            if len(spreads) < 1000:
                raise SystemExit("Existing spread CSV has too few rows to reuse")
            reuse_existing = True
        else:
            rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, FROM_DT, TO_DT)
            if rates is None or len(rates) == 0:
                raise SystemExit(f"No M1 rates returned for requested window: {mt5.last_error()}")
            with SPREAD_CSV.open("w", encoding="utf-8", newline="") as handle:
                handle.write("timestamp,symbol,bid,ask\n")
                for row in rates:
                    timestamp = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
                    text = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
                    bid = float(row["close"])
                    spread_points = int(row["spread"])
                    if bid <= 0 or spread_points < 0:
                        raise SystemExit(f"Invalid M1 rate at {text}")
                    ask = bid + spread_points * POINT
                    handle.write(f"{text},{SYMBOL},{bid:.2f},{ask:.2f}\n")
                    spreads.append(spread_points)
                    dates.add(text[:10])
                    zero_spread += int(spread_points == 0)
                    first_timestamp = first_timestamp or text
                    last_timestamp = text

        after = count_orders_positions()
        if after != before:
            raise SystemExit(
                f"Orders/positions changed during export (before={before}, after={after}); aborting"
            )
        if after["orders"] != 0 or after["positions"] != 0:
            # Read-only export must not leave or open anything; existing state is recorded.
            pass

        actual_first_date = date.fromisoformat(first_timestamp[:10])
        actual_last_date = date.fromisoformat(last_timestamp[:10])
        observed_days = {date.fromisoformat(day) for day in dates}
        expected_days = expected_market_days(FROM_DATE, TO_DATE)
        missing_days = [day.isoformat() for day in expected_days if day not in observed_days]
        expected_count = len(expected_days)
        missing_count = len(missing_days)
        calendar_coverage_ratio = (
            (expected_count - missing_count) / expected_count if expected_count else 0.0
        )

        # Full-window honesty gate: first bar must start near 2018.01.01 and last near to-date.
        # Do not relabel partial 2024+ history as full-window evidence.
        starts_ok = actual_first_date <= date(2018, 1, 8)
        ends_ok = actual_last_date >= date(2026, 7, 15)
        # Weekday calendar coverage after holidays/weekends: require strong span + density.
        calendar_ok = calendar_coverage_ratio >= 0.95
        full_window_coverage = bool(starts_ok and ends_ok and calendar_ok and len(spreads) > 0)

        broker_fingerprint = sha256_text(company)
        server_fingerprint = sha256_text(f"{server}|Build {int(terminal_info.build)}")
        account_mode = (
            "DEMO"
            if trade_mode == int(mt5.ACCOUNT_TRADE_MODE_DEMO)
            else "CONTEST"
            if trade_mode == int(mt5.ACCOUNT_TRADE_MODE_CONTEST)
            else "REAL"
        )
        account_fingerprint = sha256_text(
            f"{int(account.login)}|{account.currency}|{account_mode}|{server}"
        )
        spread_sha = sha256_file(SPREAD_CSV)
        data_fingerprint = sha256_text(
            f"{SYMBOL}|M1|{FROM_TEXT}|{TO_TEXT}|{spread_sha}|digits={DIGITS}|point={POINT}"
        )

        audit = {
            "schema_version": "mzms_spread_export_audit.v1",
            "campaign_id": CAMPAIGN_ID,
            "mode": "READ_ONLY_NO_ORDERS",
            # Export-audit fingerprints use live-terminal formulas (login/mode,
            # "server|Build N", M1 spread CSV hash). They are cost/export
            # provenance only and must NOT be copied into task_packet post-run
            # identity fields (see mzms_report_identity_basis.v1 / Get-ReportIdentity).
            "identity_semantics": "spread_export_audit_only_not_post_run_report_identity",
            "promotion_eligible": False,
            "symbol": SYMBOL,
            "timeframe": "M1",
            "requested_from": FROM_TEXT,
            "requested_to": TO_TEXT,
            "actual_first_timestamp_utc": first_timestamp,
            "actual_last_timestamp_utc": last_timestamp,
            "source_method": (
                "MT5 CopyRates M1 close bid plus the same completed bar's reported spread points "
                "from the portable D: FivePercent terminal"
                + (" [re-audit existing dump]" if reuse_existing else "")
            ),
            "terminal_path": str(terminal.resolve()),
            "broker_company": company,
            "server": server,
            "terminal_build": int(terminal_info.build),
            "terminal_trade_allowed": bool(terminal_info.trade_allowed),
            "account_login": int(account.login),
            "account_currency": str(account.currency),
            "account_trade_mode": account_mode,
            "orders_positions_before": before,
            "orders_positions_after": after,
            "orders_sent": 0,
            "positions_opened": 0,
            "symbol_geometry": {"digits": DIGITS, "point": POINT, "pip_size": PIP_SIZE},
            "row_count": len(spreads),
            "valid_rows": len(spreads),
            "sample_validity_coverage_ratio": 1.0,
            "unique_calendar_dates": len(dates),
            "expected_market_days": expected_count,
            "missing_calendar_days_count": missing_count,
            "missing_calendar_days": missing_days[:200],
            "missing_calendar_days_truncated": missing_count > 200,
            "calendar_coverage_ratio": calendar_coverage_ratio,
            "full_window_coverage": full_window_coverage,
            "zero_spread_rows": zero_spread,
            "spread_points": {
                "p50": percentile(spreads, 0.50),
                "p90": percentile(spreads, 0.90),
                "p99": percentile(spreads, 0.99),
                "max": max(spreads),
            },
            "source_csv": str(SPREAD_CSV.resolve()),
            "source_sha256": spread_sha,
            "broker_fingerprint": broker_fingerprint,
            "server_fingerprint": server_fingerprint,
            "account_fingerprint": account_fingerprint,
            "data_fingerprint": data_fingerprint,
            "proxy_sources": {
                "commission_csv": str(COMMISSION_CSV.relative_to(ROOT).as_posix()),
                "commission_sha256": proxy_receipt["tester_commission_proxy"]["output_sha256"],
                "quote_latency_csv": str(QUOTE_CSV.relative_to(ROOT).as_posix()),
                "quote_latency_sha256": proxy_receipt["quote_latency_proxy"]["output_sha256"],
                "proxy_receipt": str(PROXY_RECEIPT.relative_to(ROOT).as_posix()),
                "proxy_receipt_sha256": sha256_file(PROXY_RECEIPT),
            },
            "honesty_note": (
                "Missing calendar days and actual first/last timestamps are reported honestly. "
                "This export does not relabel older 2024-only Unicorn spread sources as full-window "
                f"{FROM_TEXT}-{TO_TEXT} evidence."
            ),
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        AUDIT_JSON.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(audit, indent=2))

        if not full_window_coverage:
            # Exit non-zero so the campaign does not silently promote partial history.
            raise SystemExit(
                "BLOCKED: actual M1 history does not honestly cover the requested full window "
                f"{FROM_TEXT}-{TO_TEXT}. actual_first={first_timestamp}, actual_last={last_timestamp}, "
                f"calendar_coverage_ratio={calendar_coverage_ratio:.6f}, missing_days={missing_count}"
            )
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
