from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).with_name("analyze_pdac_source.py")
SPEC = importlib.util.spec_from_file_location("pdac", MODULE_PATH)
PDAC = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PDAC)


def fixture(long: bool = True, exact_next: bool = True) -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2018-01-01 00:00:00")
    for day in range(1100):
        date = start + pd.Timedelta(days=day)
        base = 100.0 + day * 0.01
        for hour in range(24):
            close = base
            if day == 1 and hour == 0:
                close = 100.5 if long else 99.5
            if day == 1 and hour == 1:
                close = 101.0 if long else 99.0
            if day == 1 and hour == 2:
                close = 101.2 if long else 98.8
            dt = date + pd.Timedelta(hours=hour)
            rows.append({
                "symbol": "XAUUSD",
                "timeframe": "H1",
                "source_epoch": int(dt.timestamp()),
                "time_server": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "tick_volume": 10,
            })
    frame = pd.DataFrame(rows)
    if not exact_next:
        target = frame.index[frame["time_server"] == "2018-01-02 03:00:00"][0]
        frame.loc[target:, "source_epoch"] += 3600
    return frame


def test_long_two_close_acceptance_is_causal() -> None:
    report, ledger = PDAC.analyze_frame(fixture(long=True))
    assert ledger[0]["direction"] == "LONG"
    assert ledger[0]["decision_time_server"] == "2018-01-02T02:00:00"
    assert ledger[0]["exact_next"] is True
    assert report["economics_evaluated"] is False


def test_short_inverse() -> None:
    _, ledger = PDAC.analyze_frame(fixture(long=False))
    assert ledger[0]["direction"] == "SHORT"


def test_missing_exact_next_consumes_raw_not_executable() -> None:
    report, ledger = PDAC.analyze_frame(fixture(long=True, exact_next=False))
    assert report["raw_events"] >= 1
    assert len(ledger) == report["executable_events"]
    assert report["exact_next_coverage"] < 1.0


def test_wrong_symbol_fails_closed() -> None:
    frame = fixture()
    frame.loc[0, "symbol"] = "EURUSD"
    with pytest.raises(ValueError, match="symbol mismatch"):
        PDAC.analyze_frame(frame)
