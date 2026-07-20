#!/usr/bin/env python3
"""Verify the frozen LSS-OB detector against FivePercent native MT5 bars.

This is a read-only, no-outcome parity receipt.  It compares the M1-derived
M15/H1/H4 bars with the broker-native MT5 timeframe bars, then runs the same
closed-bar detector over both bar surfaces and compares deterministic event
identities and funnel counts.  It never requests ticks after a decision,
calculates a trade result, or sends an order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from sealed_loader import load_sealed_bars, sha256_file  # noqa: E402
from fivepercent_server_clock import server_offset_hours  # noqa: E402

from lss_ob_probe_engine import (  # noqa: E402
    FrozenSpec,
    NewsGuard,
    assert_no_outcome_schema,
    attach_context,
    resample_ohlc,
    scan_detector,
)


HYPOTHESIS_ID = "HYP-LSS-OB-REPL-EURUSD-M15-001"
EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"
SYMBOL = "EURUSD"
WINDOW_START = pd.Timestamp("2019-01-03T00:00:00")
HOLDOUT_START = pd.Timestamp("2023-01-01T00:00:00")
M1_PATH = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "fivepercent"
    / "EURUSD"
    / "EURUSD_M1_2015_now.parquet"
)
EXPECTED_M1_SHA = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
NEWS_PATH = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "forexfactory"
    / "EURUSD"
    / "news_events"
    / "forexfactory_high_impact_eurusd_2019_2022.csv"
)
EXPECTED_NEWS_SHA = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
DEFAULT_TERMINAL = (
    WORKSPACE
    / "02. AlphaFactory"
    / "runtime"
    / "mt5-portable-fivepercent"
    / "terminal64.exe"
)


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalize_native_rates(rates: object, minutes: int) -> pd.DataFrame:
    frame = pd.DataFrame(rates)
    if frame.empty:
        raise RuntimeError("native MT5 rate frame is empty")
    required = {"time", "open", "high", "low", "close", "tick_volume"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"native MT5 rate fields missing: {sorted(missing)}")
    # The FivePercent Python bridge exposes the broker's wall-clock epoch in
    # ``time``.  Treating it as UTC shifts every price series by +2/+3 hours.
    # Convert with the same hash-bound clock model used by the source parquet.
    frame["time_server"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(None)
    offsets = frame["time_server"].map(
        lambda value: server_offset_hours(pd.Timestamp(value).to_pydatetime())
    )
    frame["time_utc"] = frame["time_server"] - pd.to_timedelta(offsets, unit="h")
    frame = frame.loc[
        (frame["time_utc"] >= WINDOW_START) & (frame["time_utc"] < HOLDOUT_START),
        ["time_server", "time_utc", "open", "high", "low", "close", "tick_volume"],
    ].copy()
    frame = frame.sort_values("time_utc").drop_duplicates("time_utc", keep=False).reset_index(drop=True)
    frame["m1_count"] = np.nan
    frame["decision_time_utc"] = frame["time_utc"] + pd.Timedelta(minutes=minutes)
    return frame


def compare_ohlc(offline: pd.DataFrame, native: pd.DataFrame, tolerance: float = 1e-9) -> dict:
    joined = offline.merge(native, on="time_utc", how="outer", suffixes=("_offline", "_native"), indicator=True)
    both = joined.loc[joined["_merge"] == "both"].copy()
    fields: dict[str, dict] = {}
    for column in ("open", "high", "low", "close"):
        difference = (both[f"{column}_offline"] - both[f"{column}_native"]).abs()
        fields[column] = {
            "max_abs_difference": float(difference.max()) if len(difference) else None,
            "mismatch_count": int((difference > tolerance).sum()),
        }
    missing_native = joined.loc[joined["_merge"] == "left_only", "time_utc"]
    missing_offline = joined.loc[joined["_merge"] == "right_only", "time_utc"]
    passed = (
        len(offline) == len(native) == len(both)
        and all(item["mismatch_count"] == 0 for item in fields.values())
    )
    return {
        "offline_rows": int(len(offline)),
        "native_rows": int(len(native)),
        "joined_rows": int(len(both)),
        "missing_on_native": int(len(missing_native)),
        "missing_on_offline": int(len(missing_offline)),
        "missing_on_native_sample": [pd.Timestamp(value).isoformat() for value in missing_native.head(10)],
        "missing_on_offline_sample": [pd.Timestamp(value).isoformat() for value in missing_offline.head(10)],
        "fields": fields,
        "tolerance": tolerance,
        "status": "PASS" if passed else "FAIL",
    }


def pull_native(mt5: object, timeframe: int, minutes: int) -> pd.DataFrame:
    chunks = []
    for year in range(2019, 2023):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - pd.Timedelta(seconds=1)
        rates = mt5.copy_rates_range(SYMBOL, timeframe, start, end)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"copy_rates_range returned no rows for {year}: {mt5.last_error()}")
        chunks.append(pd.DataFrame(rates))
    return normalize_native_rates(pd.concat(chunks, ignore_index=True).to_records(index=False), minutes)


def run(terminal: Path, output: Path) -> dict:
    if sha256_file(M1_PATH) != EXPECTED_M1_SHA:
        raise RuntimeError("frozen M1 SHA mismatch")
    if sha256_file(NEWS_PATH) != EXPECTED_NEWS_SHA:
        raise RuntimeError("frozen news SHA mismatch")
    if not terminal.is_file():
        raise RuntimeError(f"portable terminal is absent: {terminal}")

    loaded, seal = load_sealed_bars(M1_PATH, HOLDOUT_START, time_col="time_utc")
    columns = ["time_utc", "open", "high", "low", "close", "tick_volume"]
    m1 = loaded.loc[loaded["time_utc"] >= WINDOW_START, columns].copy().reset_index(drop=True)
    offline = {
        "M15": resample_ohlc(m1, "15min"),
        "H1": resample_ohlc(m1, "1h"),
        "H4": resample_ohlc(m1, "4h"),
    }

    import MetaTrader5 as mt5

    if not mt5.initialize(path=str(terminal), portable=True, timeout=30_000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal_info = mt5.terminal_info()
        account = mt5.account_info()
        symbol = mt5.symbol_info(SYMBOL)
        if terminal_info is None or account is None or symbol is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        if bool(terminal_info.trade_allowed):
            raise RuntimeError("refusing parity while terminal-side trading is enabled")
        if int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO):
            raise RuntimeError("refusing parity on a non-demo account")
        if str(account.server) != EXPECTED_SERVER or str(account.company) != EXPECTED_COMPANY:
            raise RuntimeError("broker/server identity does not match frozen scope")
        if int(symbol.digits) != 5 or not math.isclose(float(symbol.point), 0.00001, abs_tol=1e-12):
            raise RuntimeError("EURUSD quote geometry does not match frozen scope")
        native_direct = {
            "M15": pull_native(mt5, mt5.TIMEFRAME_M15, 15),
            "H1": pull_native(mt5, mt5.TIMEFRAME_H1, 60),
            "H4": pull_native(mt5, mt5.TIMEFRAME_H4, 240),
        }
        native_m1 = pull_native(mt5, mt5.TIMEFRAME_M1, 1)
        broker_identity = {
            "server": str(account.server),
            "company": str(account.company),
            "account_trade_mode": int(account.trade_mode),
            "terminal_trade_allowed": bool(terminal_info.trade_allowed),
            "symbol_digits": int(symbol.digits),
            "symbol_point": float(symbol.point),
        }
    finally:
        mt5.shutdown()

    # The frozen contract is UTC-anchored.  M15/H1 native bars map directly
    # after server-clock conversion, while broker-native H4 is server-anchored
    # and is therefore an observation, not the canonical parity target.  The
    # authoritative comparison replays native MT5 M1 into UTC M15/H1/H4.
    direct_ohlc = {
        name: compare_ohlc(offline[name], native_direct[name])
        for name in ("M15", "H1", "H4")
    }
    native_replay = {
        "M15": resample_ohlc(native_m1, "15min"),
        "H1": resample_ohlc(native_m1, "1h"),
        "H4": resample_ohlc(native_m1, "4h"),
    }
    replay_ohlc = {
        "M1": compare_ohlc(m1, native_m1),
        **{
            name: compare_ohlc(offline[name], native_replay[name])
            for name in ("M15", "H1", "H4")
        },
    }
    spec = FrozenSpec()
    news_frame = pd.read_csv(NEWS_PATH, usecols=["event_time_utc"])
    event_times = pd.to_datetime(news_frame["event_time_utc"], utc=True)
    offline_bars = attach_context(offline["M15"], offline["H1"], offline["H4"], spec)
    native_bars = attach_context(
        native_replay["M15"], native_replay["H1"], native_replay["H4"], spec
    )
    offline_events, offline_funnel = scan_detector(
        offline_bars, m1, NewsGuard(event_times, spec.news_blackout_minutes), spec
    )
    native_events, native_funnel = scan_detector(
        native_bars, m1, NewsGuard(event_times, spec.news_blackout_minutes), spec
    )
    offline_ids = [event["event_id"] for event in offline_events]
    native_ids = [event["event_id"] for event in native_events]
    event_identity_pass = offline_ids == native_ids
    funnel_identity_pass = offline_funnel == native_funnel
    overall = (
        all(item["status"] == "PASS" for item in replay_ohlc.values())
        and event_identity_pass
        and funnel_identity_pass
    )
    receipt = {
        "schema_version": "lss_ob_native_mt5_parity.v1",
        "authority": "READ_ONLY_NO_OUTCOME_NATIVE_MT5_PARITY",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "promotion_eligible": False,
        "outcomes_included": False,
        "performance_metrics_authorized": False,
        "orders_sent": 0,
        "holdout_bars_loaded": int(seal.get("holdout_bars_loaded", 0)),
        "broker_identity": broker_identity,
        "input_identity": {
            "m1_path": M1_PATH.relative_to(WORKSPACE).as_posix(),
            "m1_sha256": EXPECTED_M1_SHA,
            "news_path": NEWS_PATH.relative_to(WORKSPACE).as_posix(),
            "news_sha256": EXPECTED_NEWS_SHA,
            "engine_sha256": file_sha(HERE / "lss_ob_probe_engine.py"),
            "parity_runner_sha256": file_sha(Path(__file__)),
        },
        "clock_contract": {
            "broker_time": "FivePercent server wall clock encoded as epoch",
            "canonical_time": "UTC via fivepercent_server_clock.py",
            "timeframe_anchor": "UTC_OPEN_LEFT_CLOSED",
            "native_h4_note": "broker-native H4 is server-anchored and is non-canonical for this frozen probe",
        },
        "native_m1_utc_replay_parity": replay_ohlc,
        "direct_native_timeframe_observation": direct_ohlc,
        "detector_parity": {
            "offline_event_count": int(len(offline_ids)),
            "native_event_count": int(len(native_ids)),
            "event_identity_status": "PASS" if event_identity_pass else "FAIL",
            "offline_only_event_ids": sorted(set(offline_ids) - set(native_ids))[:20],
            "native_only_event_ids": sorted(set(native_ids) - set(offline_ids))[:20],
            "funnel_identity_status": "PASS" if funnel_identity_pass else "FAIL",
            "offline_funnel": offline_funnel,
            "native_funnel": native_funnel,
        },
        "overall": "PASS" if overall else "FAIL",
    }
    assert_no_outcome_schema(receipt)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(output),
                "overall": receipt["overall"],
                "native_m1_utc_replay": {
                    name: item["status"] for name, item in replay_ohlc.items()
                },
                "direct_native_timeframes": {
                    name: item["status"] for name, item in direct_ohlc.items()
                },
                "detector_parity": receipt["detector_parity"],
            },
            indent=2,
        )
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", type=Path, default=DEFAULT_TERMINAL)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "evidence" / f"{HYPOTHESIS_ID}_NATIVE_MT5_PARITY.json",
    )
    args = parser.parse_args()
    receipt = run(args.terminal.resolve(), args.output.resolve())
    return 0 if receipt["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
