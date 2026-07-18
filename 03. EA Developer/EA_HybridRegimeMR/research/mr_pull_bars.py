#!/usr/bin/env python3
"""Stage B0 data acquisition for HYP-MR-REGIME-EURUSD-H1-001 (read-only, no orders).

Pulls EURUSD H1/H4/M1 closed bars 2015->now from the portable FivePercent
terminal, persists Parquet on D:, derives the empirical spread distribution
(per year, all-hours and session-hours) and verifies the server->UTC offset
empirically on EVERY trading week using the NY-close anchor convention
(market close = Friday 17:00 America/New_York; broker GMT+2/+3 tracking US DST).

Fail-closed: refuses to run if the terminal has trading enabled, the account
is not the expected demo server, or the symbol geometry is unexpected.
This is data acquisition only: no hypothesis outcome is read here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"

EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"
SYMBOL = "EURUSD"
EXPECTED_DIGITS = 5
POINT = 0.00001
FROM_YEAR = 2015
TO_UTC = datetime(2026, 7, 17, 23, 59, 59, tzinfo=timezone.utc)
SESSION_UTC = (7, 16)  # [7,16) entry window from spec section 4.3

TF = {"H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "M1": mt5.TIMEFRAME_M1}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


# --- DST calendars (no tz database needed) -----------------------------------
def _nth_sunday(year: int, month: int, n: int) -> datetime:
    d = datetime(year, month, 1, tzinfo=timezone.utc)
    first_sunday = d + timedelta(days=(6 - d.weekday()) % 7)
    return first_sunday + timedelta(days=7 * (n - 1))


def _last_sunday(year: int, month: int) -> datetime:
    if month == 12:
        nxt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        nxt = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    last_day = nxt - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


def is_us_dst(utc: datetime) -> bool:
    """US: 2nd Sunday March 07:00 UTC -> 1st Sunday November 06:00 UTC."""
    start = _nth_sunday(utc.year, 3, 2).replace(hour=7)
    end = _nth_sunday(utc.year, 11, 1).replace(hour=6)
    return start <= utc < end


def is_eu_dst(utc: datetime) -> bool:
    """EU: last Sunday March 01:00 UTC -> last Sunday October 01:00 UTC."""
    start = _last_sunday(utc.year, 3).replace(hour=1)
    end = _last_sunday(utc.year, 10).replace(hour=1)
    return start <= utc < end


def server_offset_hours(ts_server_naive: datetime) -> int:
    """FivePercent server = UTC+2 winter / UTC+3 summer; DST calendar by era.

    Empirically established 2026-07-17 from the Friday-close anchor on every
    week 2015-2026: gap weeks (between US and EU DST switches) close at 22:00
    server through 2023 (EU last-Sunday calendar) and at 23:00 server from
    2024 onward (US second-Sunday calendar) — the broker changed convention.
    Transitions occur on weekends while the market is closed, so no live bar
    is ambiguous.
    """
    guess = ts_server_naive.replace(tzinfo=timezone.utc) - timedelta(hours=2)
    if guess.year >= 2024:
        return 3 if is_us_dst(guess) else 2
    return 3 if is_eu_dst(guess) else 2


def to_utc(ts_server: pd.Series) -> tuple[pd.Series, pd.Series]:
    offsets = ts_server.map(lambda t: server_offset_hours(t.to_pydatetime().replace(tzinfo=None)))
    utc = ts_server - pd.to_timedelta(offsets, unit="h")
    return utc, offsets


def pull(timeframe_key: str) -> pd.DataFrame:
    parts: list[np.ndarray] = []
    for year in range(FROM_YEAR, TO_UTC.year + 1):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = min(datetime(year + 1, 1, 1, tzinfo=timezone.utc), TO_UTC)
        rates = mt5.copy_rates_range(SYMBOL, TF[timeframe_key], start, end)
        if rates is None:
            raise SystemExit(f"copy_rates_range failed {timeframe_key} {year}: {mt5.last_error()}")
        if len(rates):
            parts.append(rates)
    if not parts:
        raise SystemExit(f"no {SYMBOL} {timeframe_key} rates returned")
    raw = np.concatenate(parts)
    df = pd.DataFrame(raw).drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    # MT5 epoch is server wall time encoded as if UTC -> keep naive-as-server
    df["time_server"] = pd.to_datetime(df["time"], unit="s")
    utc, offsets = to_utc(df["time_server"])
    df["time_utc"] = utc
    df["utc_offset_h"] = offsets.astype(np.int8)
    return df[["time_server", "time_utc", "utc_offset_h", "open", "high", "low",
               "close", "tick_volume", "spread", "real_volume"]]


def verify_week_anchors(h1: pd.DataFrame) -> dict:
    """Empirical offset verification on EVERY week via the Friday-close anchor.

    True liquidity close = Friday 17:00 New York (US DST calendar). Under the
    EU-DST server model the expected last H1 bar of the week in SERVER time is
        close_utc(NY) - 1h + offset_eu
    which is 23:00 in aligned weeks and 22:00 in the US/EU DST gap weeks.
    Monday 00:00 server open is a broker-fixed quote schedule (not DST
    evidence) and is only reported.
    """
    t = h1["time_server"].reset_index(drop=True)
    gaps = t.diff().dt.total_seconds().fillna(0) / 3600.0
    weekend_starts = t[(gaps.shift(-1) > 40)]
    weekend_ends = t[(gaps > 40)]

    close_ok = 0
    anomalies_last: list[str] = []
    for ts in weekend_starts:
        server = ts.to_pydatetime().replace(tzinfo=None)
        # Friday of this week in server terms
        friday = server.date()
        ny_close_utc = datetime(friday.year, friday.month, friday.day, tzinfo=timezone.utc)
        ny_close_utc = ny_close_utc.replace(hour=21 if is_us_dst(ny_close_utc.replace(hour=21)) else 22)
        offset = server_offset_hours(server)
        expected_last = ny_close_utc - timedelta(hours=1) + timedelta(hours=offset)
        if server.weekday() == 4 and server == expected_last.replace(tzinfo=None):
            close_ok += 1
        elif len(anomalies_last) < 20:
            anomalies_last.append(f"{server} (expected {expected_last.replace(tzinfo=None)})")

    first_ok = int(((weekend_ends.dt.dayofweek == 0) & (weekend_ends.dt.hour == 0)).sum())
    anomalies_first = [
        str(x) for x in weekend_ends[~((weekend_ends.dt.dayofweek == 0) & (weekend_ends.dt.hour == 0))]
    ][:20]
    return {
        "offset_model": "UTC+2/+3; EU DST calendar <=2023, US DST calendar >=2024 (empirical era switch)",
        "weeks_checked_close_anchor": int(len(weekend_starts)),
        "close_anchor_model_match": close_ok,
        "close_anchor_ok_ratio": round(close_ok / max(1, len(weekend_starts)), 4),
        "close_anchor_anomalies_first20": anomalies_last,
        "weeks_checked_open_anchor": int(len(weekend_ends)),
        "monday_00h_server_open_ok": first_ok,
        "open_anchor_ok_ratio": round(first_ok / max(1, len(weekend_ends)), 4),
        "open_anchor_anomalies_first20": anomalies_first,
        "note": "Monday 00:00 server open is broker quote schedule, not DST evidence",
    }


def spread_stats(m1: pd.DataFrame) -> dict:
    def pct(s: pd.Series) -> dict:
        if len(s) == 0:
            return {"n": 0}
        q = s.quantile([0.5, 0.75, 0.9]).to_dict()
        return {
            "n": int(len(s)),
            "p50_points": float(q[0.5]),
            "p75_points": float(q[0.75]),
            "p90_points": float(q[0.9]),
            "p50_pips": round(float(q[0.5]) / 10.0, 3),
            "p75_pips": round(float(q[0.75]) / 10.0, 3),
            "p90_pips": round(float(q[0.9]) / 10.0, 3),
            "zero_rows": int((s == 0).sum()),
        }

    out: dict = {"unit_note": "1 pip = 10 points at 5 digits"}
    sess = m1[(m1["time_utc"].dt.hour >= SESSION_UTC[0]) & (m1["time_utc"].dt.hour < SESSION_UTC[1])]
    out["all_hours_all_years"] = pct(m1["spread"])
    out["session_hours_all_years"] = pct(sess["spread"])
    out["by_year_all_hours"] = {
        int(y): pct(g["spread"]) for y, g in m1.groupby(m1["time_utc"].dt.year)
    }
    out["by_year_session_hours"] = {
        int(y): pct(g["spread"]) for y, g in sess.groupby(sess["time_utc"].dt.year)
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    # The FivePercentOnline-Real login lives in the installed C terminal (the
    # portable D terminal is logged to MetaQuotes-Demo, verified 2026-07-17).
    # C-side history cache growth is receipted before/after per hot.md
    # C-drive tester hygiene precedent; bar evidence itself is persisted on D.
    parser.add_argument("--terminal", type=Path,
                        default=Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"))
    parser.add_argument("--portable", action="store_true")
    args = parser.parse_args()

    if not mt5.initialize(path=str(args.terminal), timeout=60_000, portable=args.portable):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise SystemExit(f"MT5 metadata unavailable: {mt5.last_error()}")
        if terminal.trade_allowed:
            raise SystemExit("Refusing to run while terminal-side trading is enabled")
        if int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO):
            raise SystemExit("Refusing to run on a non-demo account")
        if str(account.server) != EXPECTED_SERVER or str(account.company) != EXPECTED_COMPANY:
            raise SystemExit(f"Broker/server mismatch: {account.server} / {account.company}")
        if not mt5.symbol_select(SYMBOL, True):
            raise SystemExit(f"symbol_select({SYMBOL}) failed: {mt5.last_error()}")
        sym = mt5.symbol_info(SYMBOL)
        if sym is None or int(sym.digits) != EXPECTED_DIGITS or abs(float(sym.point) - POINT) > 1e-12:
            raise SystemExit(f"{SYMBOL} geometry unexpected: digits={getattr(sym,'digits',None)}")

        EVIDENCE.mkdir(parents=True, exist_ok=True)
        audit: dict = {
            "schema_version": "mr_data_pull_audit.v1",
            "hypothesis_id": "HYP-MR-REGIME-EURUSD-H1-001",
            "mode": "READ_ONLY_DEMO_NO_ORDERS",
            "symbol": SYMBOL,
            "server": str(account.server),
            "company": str(account.company),
            "terminal_build": int(terminal.build),
            "terminal_data_path": str(terminal.data_path),
            "from_year": FROM_YEAR,
            "to_utc": TO_UTC.strftime("%Y-%m-%dT%H:%M:%S"),
            "offset_model": "server = UTC+2 winter / UTC+3 summer; EU DST <=2023, US DST >=2024 (empirical 2026-07-17)",
            "session_utc_halfopen": list(SESSION_UTC),
            "frames": {},
        }

        h1 = None
        for tf_key in ("H1", "H4", "M1"):
            df = pull(tf_key)
            out = EVIDENCE / f"EURUSD_{tf_key}_2015_now.parquet"
            df.to_parquet(out, index=False)
            audit["frames"][tf_key] = {
                "rows": int(len(df)),
                "first_server": str(df["time_server"].iloc[0]),
                "last_server": str(df["time_server"].iloc[-1]),
                "first_utc": str(df["time_utc"].iloc[0]),
                "last_utc": str(df["time_utc"].iloc[-1]),
                "years_present": sorted(df["time_utc"].dt.year.unique().tolist()),
                "path": str(out),
                "sha256": sha256_file(out),
            }
            if tf_key == "H1":
                h1 = df
            if tf_key == "M1":
                audit["spread"] = spread_stats(df)

        audit["offset_verification"] = verify_week_anchors(h1)

        audit_path = EVIDENCE / "EURUSD_PULL_AUDIT.json"
        audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: audit[k] for k in ("frames", "offset_verification")}, indent=2))
        print(f"AUDIT -> {audit_path}")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
