from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.agents import AgentOutputError, AgentUnavailableError, build_blind_critic_task, build_trade_architect_task  # noqa: E402
from session_trader.models import (  # noqa: E402
    AccountSnapshot,
    ArtifactRef,
    Bias,
    Candidate,
    Critique,
    Decision,
    Direction,
    MarketSnapshot,
    QuoteSnapshot,
    Scenario,
    SessionConstraints,
    SessionName,
    SessionPlan,
    Stance,
    TradeMode,
)


NOW = datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc)
HASH = "a" * 64
REF = ArtifactRef(schema_version="x.v1", path="x.json", sha256=HASH)


def context():
    plan = SessionPlan(
        plan_id="SESSION_PLAN_2026-08-27_LONDON",
        version=1,
        session_date=date(2026, 8, 27),
        session=SessionName.LONDON,
        created_at_utc=NOW,
        market_asof_utc=NOW - timedelta(minutes=1),
        created_by="planner",
        input_sha256=HASH,
        regime="range",
        biases=(Bias(symbol="EURUSD", stance=Stance.BULLISH, summary="mild"),),
        scenarios=(Scenario(scenario_id="A", name="pullback", trigger="zone", action="long", invalidation="below X"),),
        global_invalidation="event shock",
        constraints=SessionConstraints(
            max_risk_pct_per_trade=0.25,
            max_trades=1,
            news_blackout_before_minutes=15,
            news_blackout_after_minutes=15,
            allowed_symbols=("EURUSD",),
            correlation_note="no correlated full risk",
        ),
    )
    quote = QuoteSnapshot(
        symbol="EURUSD", bid=1.17, ask=1.1701, point=0.00001, spread_points=10,
        tick_size=0.00001, tick_value_loss=1.0, volume_min=0.01, volume_max=100,
        volume_step=0.01, asof_utc=NOW, server_time="2026.08.27 09:00:00",
    )
    market = MarketSnapshot(snapshot_id="M1", captured_at_utc=NOW, source="test", connected=True, quotes=(quote,))
    account = AccountSnapshot(
        snapshot_id="A1", captured_at_utc=NOW, account_fingerprint=HASH, server="MetaQuotes-Demo",
        trade_mode=TradeMode.DEMO, currency="USD", balance=100000, equity=100000, margin_free=100000,
        drawdown_pct=0, daily_loss_pct=0, weekly_loss_pct=0, open_risk_pct=0,
        risk_metrics_complete=True, risk_metrics_source="test", trades_this_session=0,
        consecutive_losses=0, terminal_connected=True, terminal_trade_allowed=False,
        expert_trading_allowed=True,
    )
    candidate = Candidate(
        candidate_id="C1", created_at_utc=NOW, plan=REF, market_snapshot=REF,
        account_snapshot=REF, symbol="EURUSD",
        direction=Direction.LONG, scenario_id="A", entry_condition="M15 close", entry_min=1.17,
        entry_max=1.171, stop_loss=1.168, take_profit=1.175, expiry_utc=NOW + timedelta(hours=1),
        requested_risk_pct=0.25, expected_r=2.0, confidence=0.9, evidence_refs=("bar-1",),
    )
    return plan, market, account, candidate


def test_blind_critic_never_receives_candidate_narrative_or_confidence() -> None:
    plan, market, account, candidate = context()
    task = build_blind_critic_task(
        plan, market, account, candidate,
        provider_id="claude", model_id="critic", candidate_provider_id="openai",
        created_at_utc=NOW,
    )
    order = task.inputs["candidate_order"]
    assert "entry_condition" not in order
    assert "confidence" not in order
    assert "evidence_refs" not in order
    assert order["stop_loss"] == 1.168
    assert "balance" not in task.inputs["raw_account_snapshot"]
    assert "account_fingerprint" not in task.inputs["raw_account_snapshot"]


def test_blind_critic_can_require_a_distinct_provider() -> None:
    plan, market, account, candidate = context()
    with pytest.raises(AgentUnavailableError, match="distinct provider"):
        build_blind_critic_task(
            plan, market, account, candidate,
            provider_id="openai", model_id="critic", candidate_provider_id="openai",
        )


def test_trade_architect_cannot_override_a_rejected_critic() -> None:
    plan, market, account, candidate = context()
    critique = Critique(
        critique_id="R1", created_at_utc=NOW, plan=REF, market_snapshot=REF,
        account_snapshot=REF, candidate=REF, verdict=Decision.REJECT,
        reject_reasons=("news blackout",), checks=("news",),
    )
    with pytest.raises(AgentOutputError, match="critic rejection"):
        build_trade_architect_task(
            plan, market, account, candidate, critique,
            provider_id="openai", model_id="architect",
        )
