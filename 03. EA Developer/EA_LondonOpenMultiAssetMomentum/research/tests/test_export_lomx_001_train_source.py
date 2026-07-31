from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = Path(__file__).parents[1] / "export_lomx_001_train_source.py"
SPEC = importlib.util.spec_from_file_location("lomx_export", MODULE_PATH)
assert SPEC and SPEC.loader
lomx = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lomx)


def _rates_for_day(day: str, *, missing: int | None = None, spread: int = 12):
    dtype = [("time", "i8"), ("open", "f8"), ("spread", "i8")]
    rows = []
    for idx, hhmm in enumerate(lomx.REQUIRED_HHMM):
        if hhmm == missing:
            continue
        hour, minute = divmod(hhmm, 100)
        ts = pd.Timestamp(f"{day} {hour:02d}:{minute:02d}:00", tz="Europe/London").tz_convert("UTC")
        rows.append((int(ts.timestamp()), 1.10 + idx * 0.001, spread))
    return np.array(rows, dtype=dtype)


def test_import_is_inert_and_constants_are_train_only():
    assert lomx.TRAIN_YEARS == (2016, 2017, 2018, 2019, 2020)
    assert lomx.FORBIDDEN_YEAR_MIN == 2021
    assert lomx.SYMBOLS == ("EURUSD", "GBPUSD", "USDJPY", "EURJPY", "XAUUSD")


def test_exact_london_projection_is_closed_and_complete():
    rows = lomx.extract_daily_windows(
        _rates_for_day("2018-07-03"),
        symbol="EURUSD",
        point=0.00001,
        digits=5,
        broker_server=lomx.EXPECTED_SERVER,
    )
    assert len(rows) == 1
    assert rows[0]["local_date"] == "2018-07-03"
    assert rows[0]["open_0800"] == pytest.approx(1.10)
    assert rows[0]["open_1630"] == pytest.approx(1.105)
    assert rows[0]["spread_1600_points"] == 12


def test_missing_required_bar_skips_day_without_fill():
    rows = lomx.extract_daily_windows(
        _rates_for_day("2018-07-03", missing=1200),
        symbol="EURUSD",
        point=0.00001,
        digits=5,
        broker_server=lomx.EXPECTED_SERVER,
    )
    assert rows == []


def test_2021_or_later_rows_are_rejected():
    with pytest.raises(lomx.ContractError, match="forbidden 2021"):
        lomx.extract_daily_windows(
            _rates_for_day("2021-01-04"),
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            broker_server=lomx.EXPECTED_SERVER,
        )


def test_source_summary_fails_zero_spread_population():
    rows = []
    for symbol in lomx.SYMBOLS:
        for day in pd.bdate_range("2016-01-01", "2020-12-31"):
            row = {
                "symbol": symbol,
                "local_date": day.strftime("%Y-%m-%d"),
                "open_0800": 1.0,
                "open_0830": 1.0,
                "open_1200": 1.0,
                "open_1530": 1.0,
                "open_1600": 1.0,
                "open_1630": 1.0,
                "spread_0830_points": 0,
                "spread_1200_points": 0,
                "spread_1530_points": 0,
                "spread_1600_points": 0,
                "spread_1630_points": 0,
                "point": 0.00001,
                "digits": 5,
                "broker_server": lomx.EXPECTED_SERVER,
            }
            rows.append(row)
    frame = pd.DataFrame(rows, columns=lomx.SCHEMA_COLUMNS)
    with pytest.raises(lomx.ContractError, match="positive spread coverage"):
        lomx.summarize_source(frame)
