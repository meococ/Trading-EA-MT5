from __future__ import annotations

import ast
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


TOOL = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "setup_fivepercent_market_data.py"
)


def load_tool():
    spec = importlib.util.spec_from_file_location("setup_fivepercent_market_data", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_rates() -> np.ndarray:
    rows = np.zeros(
        3,
        dtype=[
            ("time", "i8"),
            ("open", "f8"),
            ("high", "f8"),
            ("low", "f8"),
            ("close", "f8"),
            ("tick_volume", "i8"),
            ("spread", "i4"),
            ("real_volume", "i8"),
        ],
    )
    rows["time"] = [1704067200, 1704067260, 1704067320]
    rows["open"] = [1.10, 1.11, 1.12]
    rows["high"] = [1.11, 1.12, 1.13]
    rows["low"] = [1.09, 1.10, 1.11]
    rows["close"] = [1.105, 1.115, 1.125]
    rows["tick_volume"] = [10, 11, 12]
    rows["spread"] = [12, 13, 14]
    return rows


def test_owner_aliases_normalize_to_canonical_symbols():
    mod = load_tool()

    assert mod.canonical_symbols(
        ["EURUSD", "JPYUSD", "GPBUSD", "XAUUSD", "BTCUSD"]
    ) == ("EURUSD", "USDJPY", "GBPUSD", "XAUUSD", "BTCUSD")
    with pytest.raises(mod.ContractError, match="unsupported symbol"):
        mod.canonical_symbols(["EURUSD", "ETHUSD"])


def test_terminal_contract_rejects_wrong_broker_trading_or_c_drive():
    mod = load_tool()
    terminal = {
        "trade_allowed": False,
        "data_path": r"D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent",
    }
    account = {
        "server": "FivePercentOnline-Real",
        "company": "Five Percent Online Ltd",
    }

    mod.validate_terminal_contract(terminal, account)
    with pytest.raises(mod.ContractError, match="trading enabled"):
        mod.validate_terminal_contract({**terminal, "trade_allowed": True}, account)
    with pytest.raises(mod.ContractError, match="broker identity"):
        mod.validate_terminal_contract(terminal, {**account, "server": "MetaQuotes-Demo"})
    with pytest.raises(mod.ContractError, match="must resolve to D"):
        mod.validate_terminal_contract({**terminal, "data_path": r"C:\MT5"}, account)


def test_rates_frame_keeps_exact_identity_and_excludes_open_bar():
    mod = load_tool()
    # MT5 epochs encode the FivePercent server wall clock; 2024-01-01 is
    # UTC+2, so server 00:00 maps to 2023-12-31 22:00 UTC.
    cutoff = datetime(2023, 12, 31, 22, 2, 30, tzinfo=timezone.utc)

    frame = mod.rates_to_frame(
        sample_rates(), symbol="EURUSD", timeframe="M1", cutoff_utc=cutoff
    )

    assert tuple(frame.columns) == mod.FRAME_COLUMNS
    assert frame["symbol"].eq("EURUSD").all()
    assert frame["timeframe"].eq("M1").all()
    assert len(frame) == 2
    assert frame["time_utc"].dt.tz is not None
    assert frame["time_utc"].is_monotonic_increasing


def test_frame_validation_rejects_duplicates_and_bad_prices():
    mod = load_tool()
    cutoff = datetime(2023, 12, 31, 22, 10, tzinfo=timezone.utc)
    frame = mod.rates_to_frame(
        sample_rates(), symbol="EURUSD", timeframe="M1", cutoff_utc=cutoff
    )
    summary = mod.validate_market_frame(frame, "EURUSD", "M1", cutoff)
    assert summary["rows"] == 3
    assert summary["duplicate_time_utc"] == 0

    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(mod.ContractError, match="duplicate"):
        mod.validate_market_frame(duplicate, "EURUSD", "M1", cutoff)
    broken = frame.copy()
    broken.loc[0, "low"] = -1.0
    with pytest.raises(mod.ContractError, match="OHLC"):
        mod.validate_market_frame(broken, "EURUSD", "M1", cutoff)


def test_continuous_btc_dst_collision_preserves_source_and_nulls_utc():
    mod = load_tool()
    rows = sample_rates()[:2].copy()
    rows["time"] = [
        int(datetime(2022, 3, 27, 2, 0, tzinfo=timezone.utc).timestamp()),
        int(datetime(2022, 3, 27, 3, 0, tzinfo=timezone.utc).timestamp()),
    ]
    rows["close"] = [42000.0, 42100.0]
    rows["open"] = [41900.0, 42000.0]
    rows["high"] = [42100.0, 42200.0]
    rows["low"] = [41800.0, 41900.0]
    cutoff = datetime(2022, 3, 27, 2, 0, tzinfo=timezone.utc)

    frame = mod.rates_to_frame(
        rows, symbol="BTCUSD", timeframe="M1", cutoff_utc=cutoff
    )
    summary = mod.validate_market_frame(frame, "BTCUSD", "M1", cutoff)

    assert frame["source_epoch"].is_unique
    assert frame["utc_ambiguous"].tolist() == [True, True]
    assert frame["time_utc"].isna().all()
    assert summary["utc_ambiguous_rows"] == 2
    assert summary["utc_ambiguous_groups"] == 1


def test_history_sync_retries_empty_result_before_accepting_rates(monkeypatch):
    mod = load_tool()

    class FakeMt5:
        def __init__(self):
            self.calls = 0

        def copy_rates_range(self, *_args):
            self.calls += 1
            return None if self.calls == 1 else sample_rates()

        def last_error(self):
            return (-1, "not synchronized")

    fake = FakeMt5()
    monkeypatch.setattr(mod.time, "sleep", lambda _seconds: None)
    rates = mod.copy_rates_range_with_retry(
        fake,
        "EURUSD",
        1,
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 2, tzinfo=timezone.utc),
        timeout_seconds=1.0,
        retry_seconds=0.0,
    )

    assert fake.calls == 2
    assert len(rates) == 3


def test_long_history_is_split_into_non_overlapping_calendar_chunks(monkeypatch):
    mod = load_tool()

    class FakeMt5:
        def __init__(self):
            self.bounds = []

        def copy_rates_range(self, _symbol, _timeframe, date_from, date_to):
            self.bounds.append((date_from, date_to))
            row = sample_rates()[:1].copy()
            row["time"] = int(date_from.timestamp())
            return row

        def last_error(self):
            return (1, "Success")

    fake = FakeMt5()
    monkeypatch.setattr(mod.time, "sleep", lambda _seconds: None)
    rates = mod.copy_rates_range_chunked(
        fake,
        "EURUSD",
        1,
        datetime(1970, 1, 1, tzinfo=timezone.utc),
        datetime(1991, 6, 1, tzinfo=timezone.utc),
        chunk_years=10,
    )

    assert len(rates) == 3
    assert fake.bounds[0][0] == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert fake.bounds[0][1] < fake.bounds[1][0]
    assert fake.bounds[1][1] < fake.bounds[2][0]
    assert fake.bounds[2][1] == datetime(1991, 6, 1, tzinfo=timezone.utc)


def test_only_exact_source_duplicates_are_collapsed():
    mod = load_tool()
    source = np.concatenate([sample_rates(), sample_rates()[:1], sample_rates()[:1]])

    clean, receipt = mod.reconcile_exact_source_duplicates(
        source, symbol="GBPUSD", timeframe="M1"
    )

    assert len(clean) == 3
    assert receipt == {
        "raw_source_rows": 5,
        "source_exact_duplicate_groups": 1,
        "source_exact_duplicate_rows_removed": 2,
        "source_conflicting_duplicate_groups": 0,
    }


def test_conflicting_same_epoch_source_bars_fail_closed():
    mod = load_tool()
    conflict = sample_rates()[:1].copy()
    conflict["close"] = 9.99
    source = np.concatenate([sample_rates(), conflict])

    with pytest.raises(mod.ContractError, match="conflicting source bars"):
        mod.reconcile_exact_source_duplicates(
            source, symbol="GBPUSD", timeframe="M1"
        )


def test_run_authority_verifies_plan_tool_and_test_hashes(tmp_path: Path):
    mod = load_tool()
    plan = tmp_path / "plan.md"
    source = tmp_path / "tool.py"
    tests = tmp_path / "tests.py"
    plan.write_text("plan\n", encoding="utf-8")
    source.write_text("source\n", encoding="utf-8")
    tests.write_text("tests\n", encoding="utf-8")
    authority = {
        "schema_version": "five_asset_data_run_authority.v1",
        "dataset_id": mod.DATASET_ID,
        "authorized": True,
        "one_use": True,
        "plan_path": str(plan),
        "plan_sha256": mod.sha256_file(plan),
        "tool_path": str(source),
        "tool_sha256": mod.sha256_file(source),
        "test_path": str(tests),
        "test_sha256": mod.sha256_file(tests),
        "symbols": list(mod.SYMBOLS),
        "timeframes": list(mod.TIMEFRAMES),
        "cutoff_utc": mod.CUTOFF_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    mod.validate_run_authority(authority)
    source.write_text("drift\n", encoding="utf-8")
    with pytest.raises(mod.ContractError, match="tool SHA256 mismatch"):
        mod.validate_run_authority(authority)


def test_tool_ast_contains_no_trading_or_outcome_api_calls():
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    forbidden = {
        "order_send",
        "order_check",
        "positions_get",
        "orders_get",
        "history_orders_get",
        "history_deals_get",
    }
    observed = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in forbidden
    }
    assert observed == set()
