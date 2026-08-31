from __future__ import annotations

import sys
from hashlib import sha256
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

ALPHA_ROOT = Path(__file__).resolve().parents[1]
if str(ALPHA_ROOT) not in sys.path:
    sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.artifacts import canonical_json_bytes
from session_trader.models import (
    AccountSnapshot,
    ArtifactRef,
    Bias,
    CalendarEvent,
    CorrelationGroup,
    Decision,
    Direction,
    Importance,
    MarketSnapshot,
    PositionSnapshot,
    QuoteSnapshot,
    RiskPolicy,
    RuntimeMode,
    Scenario,
    SessionConstraints,
    SessionName,
    SessionPlan,
    Stance,
    SymbolRiskPolicy,
    TradeIntent,
    TradeMode,
)
from session_trader.risk_gateway import evaluate_risk


NOW = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)
FINGERPRINT = "a" * 64


def ref(name: str) -> ArtifactRef:
    return ArtifactRef(schema_version=f"{name}.v1", path=f"artifacts/{name}.json", sha256="b" * 64)


def plan_ref(plan: SessionPlan) -> ArtifactRef:
    return ArtifactRef(
        schema_version=plan.schema_version,
        path="artifacts/session-plan.json",
        sha256=sha256(canonical_json_bytes(plan) + b"\n").hexdigest(),
    )


def make_intent(**updates: object) -> TradeIntent:
    values: dict[str, object] = {
        "intent_id": "TRADE_INTENT_8293",
        "created_at_utc": NOW - timedelta(minutes=1),
        "plan": plan_ref(make_plan()),
        "market_snapshot": ref("market"),
        "account_snapshot": ref("account"),
        "candidate": ref("candidate"),
        "critique": ref("critique"),
        "symbol": "EURUSD",
        "direction": Direction.LONG,
        "scenario_id": "LONDON_PULLBACK",
        "entry_min": 1.1000,
        "entry_max": 1.1005,
        "stop_loss": 1.0982,
        "take_profit": 1.1042,
        "expiry_utc": NOW + timedelta(hours=1),
        "requested_risk_pct": 0.25,
        "max_spread_points": 3.0,
        "architect_summary": "Scenario A, bounded London pullback.",
    }
    values.update(updates)
    return TradeIntent(**values)


def make_quote(**updates: object) -> QuoteSnapshot:
    values: dict[str, object] = {
        "symbol": "EURUSD",
        "bid": 1.1000,
        "ask": 1.1002,
        "point": 0.0001,
        "spread_points": 2.0,
        "tick_size": 0.0001,
        "tick_value_loss": 10.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
        "stops_level_points": 2.0,
        "asof_utc": NOW - timedelta(seconds=5),
        "server_time": "2026-08-27 10:00:00",
    }
    values.update(updates)
    return QuoteSnapshot(**values)


def make_market(**updates: object) -> MarketSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "MARKET_1",
        "captured_at_utc": NOW - timedelta(seconds=5),
        "source": "fixture",
        "connected": True,
        "server_utc_offset_minutes": 120,
        "time_mapping_verified": True,
        "time_mapping_source": "terminal-time-vs-utc-probe.v1",
        "calendar_available": True,
        "calendar_asof_utc": NOW - timedelta(seconds=5),
        "quotes": (make_quote(),),
    }
    values.update(updates)
    return MarketSnapshot(**values)


def make_account(**updates: object) -> AccountSnapshot:
    values: dict[str, object] = {
        "snapshot_id": "ACCOUNT_1",
        "captured_at_utc": NOW - timedelta(seconds=3),
        "account_fingerprint": FINGERPRINT,
        "server": "MetaQuotes-Demo",
        "trade_mode": TradeMode.DEMO,
        "currency": "USD",
        "balance": 10_000.0,
        "equity": 10_000.0,
        "margin_free": 9_500.0,
        "drawdown_pct": 0.5,
        "daily_loss_pct": 0.2,
        "weekly_loss_pct": 0.4,
        "open_risk_pct": 0.0,
        "risk_metrics_complete": True,
        "risk_metrics_source": "durable-deal-ledger.v1",
        "risk_state_sha256": "c" * 64,
        "risk_state_asof_utc": NOW - timedelta(seconds=4),
        "risk_state_session_plan_id": "SESSION_PLAN_2026-08-27_LONDON",
        "risk_state_ledger_head_sha256": "d" * 64,
        "trades_this_session": 0,
        "consecutive_losses": 0,
        "terminal_connected": True,
        "terminal_trade_allowed": True,
        "expert_trading_allowed": True,
    }
    values.update(updates)
    if values["risk_metrics_complete"] is False:
        values.update(
            risk_state_sha256=None,
            risk_state_asof_utc=None,
            risk_state_session_plan_id=None,
            risk_state_ledger_head_sha256=None,
        )
    return AccountSnapshot(**values)


def make_policy(**updates: object) -> RiskPolicy:
    values: dict[str, object] = {
        "policy_id": "DEMO_SHADOW_V1",
        "runtime_mode": RuntimeMode.SHADOW,
        "kill_switch": False,
        "allowed_account_fingerprints": (FINGERPRINT,),
        "symbols": {
            "EURUSD": SymbolRiskPolicy(
                max_risk_pct_per_trade=0.25,
                max_spread_points=3.0,
                max_slippage_points=5,
                min_rr=1.5,
                max_open_risk_pct=0.75,
            )
        },
        "max_daily_loss_pct": 2.0,
        "max_weekly_loss_pct": 4.0,
        "max_drawdown_pct": 4.0,
        "max_aggregate_open_risk_pct": 1.5,
        "max_consecutive_losses": 3,
        "max_trades_per_session": 2,
        "quote_ttl_seconds": 30,
        "account_ttl_seconds": 30,
        "calendar_ttl_seconds": 3_600,
        "news_blackout_before_minutes": 15,
        "news_blackout_after_minutes": 15,
        "magic": 8293,
    }
    values.update(updates)
    return RiskPolicy(**values)


def make_plan(**updates: object) -> SessionPlan:
    values: dict[str, object] = {
        "plan_id": "SESSION_PLAN_2026-08-27_LONDON",
        "version": 1,
        "session_date": date(2026, 8, 27),
        "session": SessionName.LONDON,
        "created_at_utc": NOW - timedelta(hours=2),
        "market_asof_utc": NOW - timedelta(hours=2, minutes=1),
        "created_by": "fixture",
        "input_sha256": "e" * 64,
        "regime": "range",
        "biases": (
            Bias(symbol="EURUSD", stance=Stance.BULLISH, summary="mild"),
        ),
        "scenarios": (
            Scenario(
                scenario_id="LONDON_PULLBACK",
                name="pullback",
                trigger="M15 close",
                action="long",
                invalidation="below X",
            ),
        ),
        "global_invalidation": "event shock",
        "constraints": SessionConstraints(
            max_risk_pct_per_trade=0.25,
            max_trades=1,
            news_blackout_before_minutes=30,
            news_blackout_after_minutes=20,
            allowed_symbols=("EURUSD",),
            correlation_note="one EUR sleeve",
        ),
    }
    values.update(updates)
    return SessionPlan(**values)


def evaluate(
    *,
    intent: TradeIntent | None = None,
    policy: RiskPolicy | None = None,
    market: MarketSnapshot | None = None,
    account: AccountSnapshot | None = None,
    used: tuple[str, ...] = (),
):
    active_plan = make_plan()
    return evaluate_risk(
        intent or make_intent(),
        policy or make_policy(),
        market or make_market(),
        account or make_account(),
        session_plan=active_plan,
        session_plan_ref=plan_ref(active_plan),
        used_idempotency_keys=used,
        now_utc=NOW,
    )


def test_approval_respects_risk_cap_and_rounds_volume_down() -> None:
    decision = evaluate()

    assert decision.decision == Decision.APPROVE
    assert decision.entry_price == pytest.approx(1.1002)
    assert decision.estimated_rr == pytest.approx(2.0)
    assert decision.volume == pytest.approx(0.12)
    assert decision.approved_risk_pct == pytest.approx(0.24)
    assert decision.reasons == ("APPROVED_BY_DETERMINISTIC_RISK_GATEWAY",)


def test_session_plan_trade_limit_is_stricter_than_policy() -> None:
    active_plan = make_plan()
    decision = evaluate_risk(
        make_intent(plan=plan_ref(active_plan)),
        make_policy(max_trades_per_session=2),
        make_market(),
        make_account(trades_this_session=1),
        session_plan=active_plan,
        session_plan_ref=plan_ref(active_plan),
        now_utc=NOW,
    )

    assert decision.decision == Decision.REJECT
    assert "SESSION_TRADE_LIMIT_REACHED" in decision.reasons


def test_frozen_plan_calendar_and_wider_blackout_cannot_be_dropped() -> None:
    event = CalendarEvent(
        event_id="CPI-PLAN",
        title="CPI",
        currency="USD",
        importance=Importance.HIGH,
        event_time_utc=NOW + timedelta(minutes=25),
        event_time_server="2026.08.27 10:25",
        server_utc_offset_minutes=120,
        source="frozen plan",
    )
    active_plan = make_plan(calendar=(event,))
    decision = evaluate_risk(
        make_intent(plan=plan_ref(active_plan)),
        make_policy(news_blackout_before_minutes=15),
        make_market(calendar=()),
        make_account(),
        session_plan=active_plan,
        session_plan_ref=plan_ref(active_plan),
        now_utc=NOW,
    )

    assert decision.decision == Decision.REJECT
    assert "HIGH_IMPACT_NEWS_BLACKOUT" in decision.reasons


def test_unbound_risk_metrics_are_rejected_even_if_marked_complete() -> None:
    unbound = make_account().model_copy(
        update={
            "risk_state_sha256": None,
            "risk_state_asof_utc": None,
            "risk_state_session_plan_id": None,
            "risk_state_ledger_head_sha256": None,
        }
    )
    decision = evaluate(account=unbound)

    assert decision.decision == Decision.REJECT
    assert "ACCOUNT_RISK_STATE_UNBOUND" in decision.reasons


def test_risk_state_and_intent_must_bind_the_active_plan() -> None:
    wrong_plan_account = make_account(
        risk_state_session_plan_id="SESSION_PLAN_2026-08-27_ASIA"
    )
    wrong_ref = ref("other-plan")
    decision = evaluate_risk(
        make_intent(),
        make_policy(),
        make_market(),
        wrong_plan_account,
        session_plan=make_plan(),
        session_plan_ref=wrong_ref,
        now_utc=NOW,
    )

    assert decision.decision == Decision.REJECT
    assert "ACCOUNT_RISK_STATE_PLAN_MISMATCH" in decision.reasons
    assert "SESSION_PLAN_REFERENCE_MISMATCH" in decision.reasons


def test_plan_reference_must_hash_the_supplied_plan_content() -> None:
    original = make_plan()
    original_ref = plan_ref(original)
    substituted = original.model_copy(update={"regime": "substituted after approval"})
    decision = evaluate_risk(
        make_intent(plan=original_ref),
        make_policy(),
        make_market(),
        make_account(),
        session_plan=substituted,
        session_plan_ref=original_ref,
        now_utc=NOW,
    )

    assert decision.decision == Decision.REJECT
    assert "SESSION_PLAN_REFERENCE_MISMATCH" in decision.reasons


@pytest.mark.parametrize(
    ("account_updates", "policy_updates", "expected_reason"),
    [
        ({}, {"kill_switch": True}, "KILL_SWITCH_ACTIVE"),
        ({"trade_mode": TradeMode.REAL}, {}, "REAL_ACCOUNT_FORBIDDEN"),
        ({"trade_mode": TradeMode.UNKNOWN}, {}, "UNKNOWN_ACCOUNT_MODE"),
        ({"account_fingerprint": "c" * 64}, {}, "ACCOUNT_NOT_ALLOWLISTED"),
        ({"risk_metrics_complete": False}, {}, "ACCOUNT_RISK_METRICS_INCOMPLETE"),
        (
            {"captured_at_utc": NOW - timedelta(seconds=31)},
            {},
            "STALE_ACCOUNT_SNAPSHOT",
        ),
        ({"terminal_connected": False}, {}, "TERMINAL_DISCONNECTED"),
        ({"terminal_trade_allowed": False}, {}, "TERMINAL_TRADING_DISABLED"),
        ({"expert_trading_allowed": False}, {}, "EXPERT_TRADING_DISABLED"),
        ({"daily_loss_pct": 2.0}, {}, "DAILY_LOSS_LIMIT_REACHED"),
        ({"weekly_loss_pct": 4.0}, {}, "WEEKLY_LOSS_LIMIT_REACHED"),
        ({"drawdown_pct": 4.0}, {}, "DRAWDOWN_LIMIT_REACHED"),
        ({"consecutive_losses": 3}, {}, "CONSECUTIVE_LOSS_LIMIT_REACHED"),
        ({"trades_this_session": 2}, {}, "SESSION_TRADE_LIMIT_REACHED"),
        ({"open_risk_pct": 1.3}, {}, "AGGREGATE_OPEN_RISK_LIMIT_EXCEEDED"),
    ],
)
def test_account_and_policy_fail_closed(
    account_updates: dict[str, object],
    policy_updates: dict[str, object],
    expected_reason: str,
) -> None:
    decision = evaluate(
        account=make_account(**account_updates), policy=make_policy(**policy_updates)
    )

    assert decision.decision == Decision.REJECT
    assert expected_reason in decision.reasons
    assert decision.volume == 0.0
    assert decision.approved_risk_pct == 0.0


@pytest.mark.parametrize(
    ("intent_updates", "quote_updates", "expected_reason"),
    [
        ({"entry_min": 1.0990, "entry_max": 1.1000}, {}, "ENTRY_OUTSIDE_AUTHORIZED_RANGE"),
        ({"stop_loss": 1.1010}, {}, "INVALID_LONG_STOP_TARGET_GEOMETRY"),
        ({"take_profit": 1.0990}, {}, "INVALID_LONG_STOP_TARGET_GEOMETRY"),
        ({"stop_loss": 1.1001}, {}, "STOP_INSIDE_BROKER_MINIMUM"),
        ({"take_profit": 1.1010}, {}, "MINIMUM_RR_NOT_MET"),
        ({}, {"bid": 1.0997, "spread_points": 5.0}, "SPREAD_LIMIT_EXCEEDED"),
        ({}, {"asof_utc": NOW - timedelta(seconds=31)}, "STALE_QUOTE"),
    ],
)
def test_price_geometry_and_market_quality_fail_closed(
    intent_updates: dict[str, object],
    quote_updates: dict[str, object],
    expected_reason: str,
) -> None:
    decision = evaluate(
        intent=make_intent(**intent_updates),
        market=make_market(quotes=(make_quote(**quote_updates),)),
    )

    assert decision.decision == Decision.REJECT
    assert expected_reason in decision.reasons


def test_unknown_symbol_and_missing_quote_are_both_explicit() -> None:
    decision = evaluate(
        intent=make_intent(symbol="GBPUSD"),
        market=make_market(quotes=()),
    )

    assert decision.decision == Decision.REJECT
    assert "UNKNOWN_OR_DISALLOWED_SYMBOL" in decision.reasons
    assert "SYMBOL_QUOTE_MISSING" in decision.reasons


def test_high_impact_currency_event_enforces_blackout() -> None:
    event = CalendarEvent(
        event_id="US_CPI",
        title="US CPI",
        currency="USD",
        importance=Importance.HIGH,
        event_time_utc=NOW + timedelta(minutes=10),
        event_time_server="2026-08-27 10:10:00",
        server_utc_offset_minutes=120,
        source="MT5",
    )

    decision = evaluate(market=make_market(calendar=(event,)))

    assert decision.decision == Decision.REJECT
    assert "HIGH_IMPACT_NEWS_BLACKOUT" in decision.reasons


@pytest.mark.parametrize(
    ("market_updates", "expected_reason"),
    [
        (
            {"calendar_available": False, "calendar_asof_utc": None},
            "CALENDAR_UNAVAILABLE",
        ),
        (
            {"calendar_asof_utc": NOW - timedelta(seconds=3_601)},
            "STALE_CALENDAR",
        ),
    ],
)
def test_calendar_truth_is_required_and_fresh(
    market_updates: dict[str, object], expected_reason: str
) -> None:
    decision = evaluate(market=make_market(**market_updates))

    assert decision.decision == Decision.REJECT
    assert expected_reason in decision.reasons


def test_unverified_server_time_mapping_is_rejected() -> None:
    decision = evaluate(
        market=make_market(
            server_utc_offset_minutes=None,
            time_mapping_verified=False,
            time_mapping_source="UNAVAILABLE",
        )
    )

    assert decision.decision == Decision.REJECT
    assert "TIME_MAPPING_UNVERIFIED" in decision.reasons


def test_correlation_and_same_symbol_exposure_are_rejected() -> None:
    position = PositionSnapshot(
        ticket=1,
        symbol="GBPUSD",
        direction=Direction.LONG,
        volume=0.1,
        open_price=1.27,
        current_price=1.271,
        stop_loss=1.265,
        take_profit=1.28,
        risk_pct=0.4,
        magic=8293,
    )
    group = CorrelationGroup(
        group_id="USD_LONG",
        symbols=("EURUSD", "GBPUSD"),
        max_group_risk_pct=0.5,
    )

    decision = evaluate(
        account=make_account(positions=(position,), open_risk_pct=0.4),
        policy=make_policy(correlation_groups=(group,)),
    )

    assert decision.decision == Decision.REJECT
    assert "CORRELATION_RISK_LIMIT_EXCEEDED:USD_LONG" in decision.reasons


def test_duplicate_idempotency_key_is_rejected() -> None:
    first = evaluate()
    duplicate = evaluate(used=(first.idempotency_key,))

    assert duplicate.decision == Decision.REJECT
    assert "DUPLICATE_IDEMPOTENCY_KEY" in duplicate.reasons


def test_altering_content_cannot_evade_once_only_intent_identity() -> None:
    first = evaluate()
    altered = evaluate(
        intent=make_intent(take_profit=1.1052), used=(first.idempotency_key,)
    )

    assert altered.idempotency_key == first.idempotency_key
    assert altered.decision == Decision.REJECT
    assert "DUPLICATE_IDEMPOTENCY_KEY" in altered.reasons


def test_volume_is_never_rounded_up_to_broker_minimum() -> None:
    decision = evaluate(
        intent=make_intent(requested_risk_pct=0.01),
        market=make_market(quotes=(make_quote(volume_min=0.10),)),
    )

    assert decision.decision == Decision.REJECT
    assert "RISK_TOO_SMALL_FOR_MINIMUM_VOLUME" in decision.reasons
