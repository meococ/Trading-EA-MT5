from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
if str(ALPHA_ROOT) not in sys.path:
    sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.models import (  # noqa: E402
    AccountSnapshot,
    Bias,
    CalendarEvent,
    Direction,
    Importance,
    KeyZone,
    MarketSnapshot,
    PositionSnapshot,
    QuoteSnapshot,
    Scenario,
    SessionConstraints,
    SessionName,
    SessionPlan,
    Stance,
    StructuralEvent,
    TradeMode,
    WatchTrigger,
)
from session_trader.watcher import WatcherConfig, evaluate_watch  # noqa: E402


NOW = datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc)


def _plan(*, zones: tuple[KeyZone, ...] = (), calendar=()) -> SessionPlan:
    return SessionPlan(
        plan_id="SESSION_PLAN_2026-08-27_LONDON",
        version=1,
        session_date=date(2026, 8, 27),
        session=SessionName.LONDON,
        created_at_utc=NOW,
        market_asof_utc=NOW,
        created_by="planner",
        input_sha256="a" * 64,
        regime="range",
        biases=(Bias(symbol="EURUSD", stance=Stance.NEUTRAL, summary="range"),),
        key_zones=zones,
        scenarios=(
            Scenario(
                scenario_id="A",
                name="pullback",
                trigger="rejection",
                action="long",
                invalidation="range break",
            ),
        ),
        global_invalidation="range breaks",
        calendar=calendar,
        constraints=SessionConstraints(
            max_risk_pct_per_trade=0.25,
            max_trades=2,
            news_blackout_before_minutes=15,
            news_blackout_after_minutes=15,
            allowed_symbols=("EURUSD",),
            correlation_note="one EUR sleeve",
        ),
    )


def _quote(*, spread_points: float = 2.0, asof: datetime = NOW) -> QuoteSnapshot:
    bid = 1.1000
    ask = bid + spread_points * 0.0001
    return QuoteSnapshot(
        symbol="EURUSD",
        bid=bid,
        ask=ask,
        point=0.0001,
        spread_points=spread_points,
        tick_size=0.0001,
        tick_value_loss=1.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        asof_utc=asof,
        server_time="2026-08-27T09:00:00+03:00",
    )


def _market(
    *,
    quote: QuoteSnapshot | None = None,
    connected: bool = True,
    captured_at: datetime = NOW,
    events=(),
    calendar=(),
) -> MarketSnapshot:
    return MarketSnapshot(
        snapshot_id=f"market-{captured_at.timestamp()}",
        captured_at_utc=captured_at,
        source="fixture",
        connected=connected,
        quotes=(_quote() if quote is None else quote,),
        structural_events=events,
        calendar=calendar,
    )


def _account(
    *,
    captured_at: datetime = NOW,
    connected: bool = True,
    positions=(),
    drawdown_pct: float = 0.0,
    trades_this_session: int = 0,
) -> AccountSnapshot:
    return AccountSnapshot(
        snapshot_id=f"account-{captured_at.timestamp()}-{drawdown_pct}",
        captured_at_utc=captured_at,
        account_fingerprint="f" * 64,
        server="MetaQuotes-Demo",
        trade_mode=TradeMode.DEMO,
        currency="USD",
        balance=10_000,
        equity=10_000,
        margin_free=10_000,
        drawdown_pct=drawdown_pct,
        daily_loss_pct=0,
        weekly_loss_pct=0,
        open_risk_pct=0,
        risk_metrics_complete=True,
        risk_metrics_source="fixture",
        trades_this_session=trades_this_session,
        consecutive_losses=0,
        terminal_connected=connected,
        terminal_trade_allowed=False,
        expert_trading_allowed=False,
        positions=positions,
    )


def test_no_trigger_means_no_agent_and_decision_is_reproducible() -> None:
    plan = _plan()
    market = _market()
    account = _account()

    first = evaluate_watch(plan, market, account, evaluated_at_utc=NOW)
    second = evaluate_watch(plan, market, account, evaluated_at_utc=NOW)

    assert first == second
    assert first.invoke_market_agent is False
    assert first.triggers == ()
    assert first.details == ()


def test_zone_and_explicit_structure_events_invoke_agent() -> None:
    zone = KeyZone(
        zone_id="london-entry",
        symbol="EURUSD",
        lower=1.0999,
        upper=1.1001,
        purpose="ENTRY",
    )
    event = StructuralEvent(
        event_id="bos-1",
        symbol="EURUSD",
        event_type="STRUCTURE_BREAK",
        observed_at_utc=NOW,
        details="M15 close above range",
    )

    decision = evaluate_watch(
        _plan(zones=(zone,)),
        _market(events=(event,)),
        _account(),
        evaluated_at_utc=NOW,
    )

    assert decision.invoke_market_agent is True
    assert WatchTrigger.ZONE_REACHED in decision.triggers
    assert WatchTrigger.STRUCTURE_CHANGED in decision.triggers


def test_spread_position_proximity_news_and_account_delta_are_detected() -> None:
    prior_position = PositionSnapshot(
        ticket=1,
        symbol="EURUSD",
        direction=Direction.LONG,
        volume=0.1,
        open_price=1.10,
        current_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        risk_pct=0.25,
        magic=765,
    )
    current_position = prior_position.model_copy(
        update={"ticket": 2, "stop_loss": 1.0995, "current_price": 1.1000}
    )
    upcoming = CalendarEvent(
        event_id="cpi",
        title="CPI",
        currency="USD",
        importance=Importance.HIGH,
        event_time_utc=NOW + timedelta(minutes=10),
        event_time_server="2026-08-27T09:10:00+03:00",
        server_utc_offset_minutes=180,
        source="MT5",
    )
    released = upcoming.model_copy(
        update={
            "event_id": "gdp",
            "title": "GDP",
            "event_time_utc": NOW - timedelta(minutes=1),
            "actual_released": True,
        }
    )
    previous_market = _market(quote=_quote(spread_points=2.0))
    market = _market(quote=_quote(spread_points=5.0), calendar=(upcoming, released))

    decision = evaluate_watch(
        _plan(),
        market,
        _account(positions=(current_position,), drawdown_pct=0.4, trades_this_session=1),
        evaluated_at_utc=NOW,
        previous_market=previous_market,
        previous_account=_account(positions=(prior_position,)),
        config=WatcherConfig(spread_limits_points={"EURUSD": 3.0}),
    )

    expected = {
        WatchTrigger.SPREAD_ABNORMAL,
        WatchTrigger.POSITION_CHANGED,
        WatchTrigger.SL_TP_NEAR,
        WatchTrigger.HIGH_IMPACT_NEWS_NEAR,
        WatchTrigger.ECONOMIC_RELEASED,
        WatchTrigger.ACCOUNT_RISK_CHANGED,
    }
    assert expected.issubset(set(decision.triggers))


def test_current_price_change_alone_does_not_count_as_position_change() -> None:
    position = PositionSnapshot(
        ticket=1,
        symbol="EURUSD",
        direction=Direction.LONG,
        volume=0.1,
        open_price=1.10,
        current_price=1.1010,
        stop_loss=1.0900,
        take_profit=1.1200,
        risk_pct=0.25,
        magic=765,
    )
    moved = position.model_copy(update={"current_price": 1.1020})

    decision = evaluate_watch(
        _plan(),
        _market(),
        _account(positions=(moved,)),
        evaluated_at_utc=NOW,
        previous_account=_account(positions=(position,)),
    )

    assert WatchTrigger.POSITION_CHANGED not in decision.triggers
    assert decision.invoke_market_agent is False


def test_stale_or_disconnected_state_triggers_fail_closed_review() -> None:
    old = NOW - timedelta(minutes=20)
    decision = evaluate_watch(
        _plan(),
        _market(quote=_quote(asof=old), connected=False, captured_at=old),
        _account(captured_at=old, connected=False),
        evaluated_at_utc=NOW,
    )

    assert WatchTrigger.STALE_MARKET in decision.triggers
    assert WatchTrigger.DISCONNECTED in decision.triggers
    assert decision.invoke_market_agent is True


def test_persistent_structural_and_release_events_do_not_reinvoke_agent() -> None:
    structure = StructuralEvent(
        event_id="bos-persistent",
        symbol="EURUSD",
        event_type="STRUCTURE_BREAK",
        observed_at_utc=NOW - timedelta(minutes=1),
        details="already handled",
    )
    release = CalendarEvent(
        event_id="cpi-released",
        title="CPI",
        currency="USD",
        importance=Importance.HIGH,
        event_time_utc=NOW - timedelta(minutes=5),
        event_time_server="2026-08-27T08:55:00+03:00",
        server_utc_offset_minutes=180,
        source="MT5",
        actual_released=True,
    )
    previous = _market(events=(structure,), calendar=(release,))
    current = previous.model_copy(update={"snapshot_id": "market-next"})

    decision = evaluate_watch(
        _plan(),
        current,
        _account(),
        evaluated_at_utc=NOW,
        previous_market=previous,
    )

    assert WatchTrigger.STRUCTURE_CHANGED not in decision.triggers
    assert WatchTrigger.ECONOMIC_RELEASED not in decision.triggers
    assert decision.invoke_market_agent is False


@pytest.mark.parametrize(
    ("direction", "current_price", "stop_loss", "take_profit"),
    (
        (Direction.LONG, 1.0800, 1.0950, 1.1200),
        (Direction.LONG, 1.1300, 1.0950, 1.1200),
        (Direction.SHORT, 1.1200, 1.1050, 1.0800),
        (Direction.SHORT, 1.0700, 1.1050, 1.0800),
    ),
)
def test_gap_through_sl_or_tp_remains_an_urgent_trigger(
    direction: Direction,
    current_price: float,
    stop_loss: float,
    take_profit: float,
) -> None:
    position = PositionSnapshot(
        ticket=10,
        symbol="EURUSD",
        direction=direction,
        volume=0.1,
        open_price=1.10,
        current_price=current_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_pct=0.25,
        magic=765,
    )

    decision = evaluate_watch(
        _plan(),
        _market(),
        _account(positions=(position,)),
        evaluated_at_utc=NOW,
    )

    assert WatchTrigger.SL_TP_NEAR in decision.triggers


def test_missing_stop_loss_is_an_urgent_trigger() -> None:
    position = PositionSnapshot(
        ticket=11,
        symbol="EURUSD",
        direction=Direction.LONG,
        volume=0.1,
        open_price=1.10,
        current_price=1.1010,
        stop_loss=0,
        take_profit=1.1200,
        risk_pct=0.25,
        magic=765,
    )

    decision = evaluate_watch(
        _plan(),
        _market(),
        _account(positions=(position,)),
        evaluated_at_utc=NOW,
    )

    assert WatchTrigger.SL_TP_NEAR in decision.triggers
    detail = decision.details[decision.triggers.index(WatchTrigger.SL_TP_NEAR)]
    assert "no stop loss" in detail


def test_unplanned_position_without_quote_cannot_sleep() -> None:
    position = PositionSnapshot(
        ticket=12,
        symbol="GBPUSD",
        direction=Direction.LONG,
        volume=0.1,
        open_price=1.30,
        current_price=1.30,
        stop_loss=1.29,
        take_profit=1.32,
        risk_pct=0.25,
        magic=765,
    )

    decision = evaluate_watch(
        _plan(),
        _market(),
        _account(positions=(position,)),
        evaluated_at_utc=NOW,
    )

    assert WatchTrigger.STALE_MARKET in decision.triggers
    assert WatchTrigger.POSITION_CHANGED in decision.triggers


def test_account_identity_or_risk_integrity_change_invokes_review() -> None:
    previous = _account()
    current = previous.model_copy(
        update={
            "snapshot_id": "account-rebound",
            "account_fingerprint": "e" * 64,
            "server": "Other-Real",
            "trade_mode": TradeMode.REAL,
            "risk_metrics_complete": False,
            "risk_metrics_source": "degraded",
        }
    )

    decision = evaluate_watch(
        _plan(),
        _market(),
        current,
        evaluated_at_utc=NOW,
        previous_account=previous,
    )

    assert WatchTrigger.ACCOUNT_RISK_CHANGED in decision.triggers
    detail = decision.details[
        decision.triggers.index(WatchTrigger.ACCOUNT_RISK_CHANGED)
    ]
    assert "account_fingerprint" in detail
    assert "trade_mode" in detail
    assert "risk_metrics_complete" in detail


def test_structural_event_for_unwatched_symbol_does_not_wake_agent() -> None:
    unrelated = StructuralEvent(
        event_id="xau-break",
        symbol="XAUUSD",
        event_type="STRUCTURE_BREAK",
        observed_at_utc=NOW,
        details="unrelated symbol",
    )

    decision = evaluate_watch(
        _plan(),
        _market(events=(unrelated,)),
        _account(),
        evaluated_at_utc=NOW,
    )

    assert WatchTrigger.STRUCTURE_CHANGED not in decision.triggers
    assert decision.invoke_market_agent is False
