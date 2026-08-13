from datetime import datetime
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PATH = Path(__file__).with_name("analyze_xjrr_source.py")
SPEC = importlib.util.spec_from_file_location("xjrr", PATH)
XJRR = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(XJRR)


def small_source(symbol: str, epochs: np.ndarray) -> pd.DataFrame:
    close = 100.0 + np.arange(len(epochs)) * 0.01
    return pd.DataFrame({
        "symbol": symbol,
        "timeframe": "M5",
        "source_epoch": epochs,
        "time_server": pd.to_datetime(epochs, unit="s").strftime("%Y-%m-%d %H:%M:%S"),
        "open": close,
        "high": close + 0.1,
        "low": close - 0.1,
        "close": close,
        "tick_volume": 10,
    })


def test_server_clock_winter_summer_and_friday_boundary() -> None:
    assert XJRR.server_to_utc(datetime(2018, 1, 5, 12)) == datetime(2018, 1, 5, 10)
    assert XJRR.server_to_utc(datetime(2018, 6, 1, 12)) == datetime(2018, 6, 1, 9)
    assert XJRR.server_to_utc(datetime(2018, 3, 25, 2, 55)) == datetime(2018, 3, 25, 0, 55)
    assert XJRR.server_to_utc(datetime(2018, 3, 25, 3, 0)) == datetime(2018, 3, 25, 0, 0)
    assert XJRR.server_to_utc(datetime(2018, 10, 28, 3, 55)) == datetime(2018, 10, 28, 0, 55)
    assert XJRR.server_to_utc(datetime(2018, 10, 28, 4, 0)) == datetime(2018, 10, 28, 2, 0)


def test_validate_rejects_bad_server_clock_axis() -> None:
    epochs = np.array([XJRR.START_EPOCH, XJRR.START_EPOCH + 300, XJRR.START_EPOCH + 600])
    frame = small_source("XAUUSD", epochs)
    XJRR.validate(frame, "XAUUSD", minimum_rows=3)
    bad = frame.copy()
    bad.loc[1, "time_server"] = bad.loc[0, "time_server"]
    with pytest.raises(ValueError, match="time_server"):
        XJRR.validate(bad, "XAUUSD", minimum_rows=3)
    bad = frame.copy()
    bad.loc[1, "time_server"] = "2018-01-01 00:06:00"
    with pytest.raises(ValueError, match="mapping"):
        XJRR.validate(bad, "XAUUSD", minimum_rows=3)


def test_join_rejects_cross_symbol_clock_mismatch() -> None:
    epochs = np.array([XJRR.START_EPOCH, XJRR.START_EPOCH + 300, XJRR.START_EPOCH + 600])
    xau = small_source("XAUUSD", epochs)
    jpy = small_source("USDJPY", epochs)
    joined = XJRR.join_sources(xau, jpy)
    assert joined["both_symbols"].all()
    jpy.loc[1, "time_server"] = "2018-01-01 00:06:00"
    with pytest.raises(ValueError, match="joined server-clock"):
        XJRR.join_sources(xau, jpy)


def test_feature_uses_prior_window() -> None:
    n = 600
    epoch = np.arange(n) * 300 + XJRR.START_EPOCH
    jpy_ret = np.sin(np.arange(n) / 17) * 0.0001
    xau_ret = -0.7 * jpy_ret
    xau_ret[400] = -0.01
    xau_ret[401] = 0.0
    joined = pd.DataFrame({
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s").strftime("%Y-%m-%d %H:%M:%S"),
        "xau_close": 100 * np.exp(np.cumsum(xau_ret)),
        "jpy_close": 100 * np.exp(np.cumsum(jpy_ret)),
        "both_symbols": True,
    })
    features = XJRR.compute_features(joined)
    assert np.isnan(features.loc[XJRR.WINDOW, "z_prior"])
    assert np.isfinite(features.loc[400, "beta"])
    assert features.loc[400, "z"] < -2.0
    assert features.loc[401, "z_prior"] == features.loc[400, "z"]


def event_frame(server_times: list[datetime]) -> pd.DataFrame:
    epochs = np.array([int(pd.Timestamp(value).timestamp()) for value in server_times], dtype=np.int64)
    return pd.DataFrame({
        "source_epoch": epochs,
        "time_server": [value.strftime("%Y-%m-%d %H:%M:%S") for value in server_times],
        "both_symbols": True,
        "beta": 1.0,
        "sigma": 1.0,
        "z_prior": 0.0,
        "z": 0.0,
    })


def test_daily_consumption_keeps_only_first_raw_event(monkeypatch: pytest.MonkeyPatch) -> None:
    epoch = np.array([
        1515178800, 1515179100, 1515179400, 1515179700,
        1515180000, 1515180300, 1515180600, 1515180900,
        1515181200, 1515181500, 1515181800, 1515182100,
        1515182400, 1515182700, 1515183000, 1515183300,
    ], dtype=np.int64)
    data = pd.DataFrame({
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s").strftime("%Y-%m-%d %H:%M:%S"),
        "both_symbols": True,
        "beta": 1.0,
        "sigma": 1.0,
        "z_prior": 0.0,
        "z": 0.0,
    })
    data.loc[1, ["z_prior", "z"]] = [-2.1, -1.9]
    data.loc[3, ["z_prior", "z"]] = [2.1, 1.9]
    monkeypatch.setattr(XJRR, "compute_features", lambda _: data.copy())
    report, ledger = XJRR.analyze(data)
    assert len(ledger) == 1
    assert ledger[0]["direction"] == "LONG"
    assert report["raw_consumed_events"] == 1


def test_lockout_consumes_cross_date_event() -> None:
    times = [datetime(2018, 1, 1, 23, 50) + pd.Timedelta(minutes=5 * i) for i in range(18)]
    data = event_frame(times)
    data.loc[1, ["z_prior", "z"]] = [-2.1, -1.9]
    data.loc[3, ["z_prior", "z"]] = [2.1, 1.9]
    raw, conflicts = XJRR.extract_events(data)
    assert conflicts == 0
    assert len(raw) == 1
    assert raw[0]["direction"] == "LONG"


def test_gap_event_consumes_daily_slot() -> None:
    times = [datetime(2018, 1, 2, 9, 0) + pd.Timedelta(minutes=5 * i) for i in range(18)]
    times[2] = times[1] + pd.Timedelta(minutes=10)
    for i in range(3, len(times)):
        times[i] = times[i - 1] + pd.Timedelta(minutes=5)
    data = event_frame(times)
    data.loc[1, ["z_prior", "z"]] = [-2.1, -1.9]
    data.loc[4, ["z_prior", "z"]] = [2.1, 1.9]
    raw, _ = XJRR.extract_events(data)
    assert len(raw) == 1
    assert raw[0]["exact_next"] is False


def test_friday_2000_utc_availability_is_blocked() -> None:
    times = [datetime(2018, 1, 5, 21, 50) + pd.Timedelta(minutes=5 * i) for i in range(18)]
    data = event_frame(times)
    data.loc[1, ["z_prior", "z"]] = [-2.1, -1.9]
    raw, _ = XJRR.extract_events(data)
    assert len(raw) == 1
    assert raw[0]["availability_time_utc"] == "2018-01-05T20:00:00"
    assert raw[0]["friday_20utc_blocked"] is True


def test_no_outcome_fields_in_report_or_ledger() -> None:
    n = 700
    epoch = np.arange(n) * 300 + XJRR.START_EPOCH
    rng = np.random.default_rng(7)
    rj = rng.normal(0, 0.0002, n)
    rx = -0.5 * rj + rng.normal(0, 0.0003, n)
    joined = pd.DataFrame({
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s").strftime("%Y-%m-%d %H:%M:%S"),
        "xau_close": 100 * np.exp(np.cumsum(rx)),
        "jpy_close": 100 * np.exp(np.cumsum(rj)),
        "both_symbols": True,
    })
    report, ledger = XJRR.analyze(joined)
    assert report["outcomes_opened"] is False
    assert report["economics_evaluated"] is False
    forbidden = {"pnl", "profit", "return", "mfe", "mae", "next_close"}
    assert all(not (forbidden & set(row)) for row in ledger)


def test_exclusive_writer_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "one-shot.json"
    XJRR.write_exclusive(target, b"first")
    with pytest.raises(FileExistsError):
        XJRR.write_exclusive(target, b"second")
