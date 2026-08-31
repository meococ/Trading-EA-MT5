from __future__ import annotations

import sys
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.collector import account_fingerprint, collect_mt5_read_only  # noqa: E402
from session_trader.models import RiskState, TradeMode  # noqa: E402


def nt(name: str, **values):
    record = namedtuple(name, values.keys())
    return record(**values)


class FakeMt5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_CONTEST = 1
    ACCOUNT_TRADE_MODE_REAL = 2
    POSITION_TYPE_BUY = 0

    def __init__(self) -> None:
        self.shutdown_called = False

    def initialize(self, **_kwargs):
        return True

    def shutdown(self):
        self.shutdown_called = True

    def last_error(self):
        return (1, "Success")

    def terminal_info(self):
        return nt(
            "TerminalInfo",
            path=r"C:\Program Files\MetaTrader 5",
            connected=True,
            trade_allowed=False,
        )

    def account_info(self):
        return nt(
            "AccountInfo",
            login=123456,
            server="MetaQuotes-Demo",
            trade_mode=0,
            currency="USD",
            balance=100_000.0,
            equity=99_900.0,
            margin_free=99_800.0,
            trade_expert=True,
        )

    def symbol_info(self, symbol):
        assert symbol == "EURUSD"
        return nt(
            "SymbolInfo",
            point=0.00001,
            trade_tick_size=0.00001,
            trade_tick_value_loss=1.0,
            trade_tick_value=1.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_stops_level=10,
        )

    def symbol_info_tick(self, symbol):
        assert symbol == "EURUSD"
        return nt(
            "Tick",
            bid=1.17000,
            ask=1.17010,
            time=int(datetime(2026, 8, 27, 9, 59, 55, tzinfo=timezone.utc).timestamp()),
        )

    def positions_get(self):
        return ()


def test_read_only_collector_fingerprints_account_and_marks_missing_risk_state() -> None:
    fake = FakeMt5()
    market, account = collect_mt5_read_only(
        ["EURUSD"],
        mt5_module=fake,
        server_utc_offset_minutes=180,
        tick_time_basis="SERVER",
        captured_at_utc=datetime(2026, 8, 27, 7, 0, tzinfo=timezone.utc),
    )

    assert fake.shutdown_called is True
    assert market.connected is True
    assert len(market.quotes) == 1
    assert market.quotes[0].spread_points == pytest.approx(10.0)
    assert account.trade_mode == TradeMode.DEMO
    assert account.terminal_trade_allowed is False
    assert account.risk_metrics_complete is False
    assert len(account.account_fingerprint) == 64


def test_quote_time_uses_explicit_server_epoch_mapping() -> None:
    market, _ = collect_mt5_read_only(
        ["EURUSD"],
        mt5_module=FakeMt5(),
        server_utc_offset_minutes=180,
        tick_time_basis="SERVER",
        captured_at_utc=datetime(2026, 8, 27, 7, 0, tzinfo=timezone.utc),
    )

    assert market.quotes[0].asof_utc == datetime(
        2026, 8, 27, 6, 59, 55, tzinfo=timezone.utc
    )
    assert market.server_utc_offset_minutes == 180


def test_read_only_collector_accepts_only_bound_fresh_risk_state() -> None:
    captured = datetime(2026, 8, 27, 7, 0, tzinfo=timezone.utc)
    plan_id = "SESSION_PLAN_2026-08-27_LONDON"
    ledger_head = "b" * 64
    fingerprint = account_fingerprint(
        123456,
        "MetaQuotes-Demo",
        r"C:\Program Files\MetaTrader 5",
    )
    risk_state = RiskState(
        state_id="RISK-STATE-1",
        asof_utc=captured,
        account_fingerprint=fingerprint,
        session_plan_id=plan_id,
        ledger_head_sha256=ledger_head,
        deals_window_sha256="c" * 64,
        daily_loss_pct=0.2,
        weekly_loss_pct=0.4,
        trades_this_session=1,
        consecutive_losses=0,
        source="MQL5_DEAL_LEDGER_RECONCILIATION",
    )
    _, account = collect_mt5_read_only(
        ["EURUSD"],
        mt5_module=FakeMt5(),
        server_utc_offset_minutes=180,
        tick_time_basis="SERVER",
        risk_state=risk_state,
        session_plan_id=plan_id,
        verified_ledger_head_sha256=ledger_head,
        captured_at_utc=captured,
    )

    assert account.risk_metrics_complete is True
    assert account.daily_loss_pct == 0.2
    assert account.trades_this_session == 1
    assert account.risk_state_session_plan_id == plan_id


def test_risk_state_account_or_ledger_substitution_fails_closed() -> None:
    captured = datetime(2026, 8, 27, 7, 0, tzinfo=timezone.utc)
    risk_state = RiskState(
        state_id="RISK-STATE-SUBSTITUTED",
        asof_utc=captured,
        account_fingerprint="f" * 64,
        session_plan_id="SESSION_PLAN_2026-08-27_LONDON",
        ledger_head_sha256="b" * 64,
        deals_window_sha256="c" * 64,
        daily_loss_pct=0,
        weekly_loss_pct=0,
        trades_this_session=0,
        consecutive_losses=0,
        source="MQL5_DEAL_LEDGER_RECONCILIATION",
    )
    _, account = collect_mt5_read_only(
        ["EURUSD"],
        mt5_module=FakeMt5(),
        server_utc_offset_minutes=180,
        tick_time_basis="SERVER",
        risk_state=risk_state,
        session_plan_id=risk_state.session_plan_id,
        verified_ledger_head_sha256="d" * 64,
        captured_at_utc=captured,
    )

    assert account.risk_metrics_complete is False
    assert account.risk_metrics_source == "ACCOUNT_FINGERPRINT_MISMATCH"
