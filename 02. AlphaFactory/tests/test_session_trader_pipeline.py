from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.artifacts import ArtifactStore  # noqa: E402
from session_trader.models import (  # noqa: E402
    AccountSnapshot,
    Bias,
    Candidate,
    CorrelationGroup,
    Critique,
    Decision,
    Direction,
    MarketSnapshot,
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
from session_trader.pipeline import PipelineIntegrityError, TradeChainRefs, run_shadow_pipeline  # noqa: E402


UTC = timezone.utc
HASH = "a" * 64


def build_chain(store: ArtifactStore) -> TradeChainRefs:
    plan_time = datetime(2026, 8, 27, 6, 0, tzinfo=UTC)
    market_time = plan_time + timedelta(minutes=10)
    account_time = plan_time + timedelta(minutes=11, seconds=45)
    candidate_time = plan_time + timedelta(minutes=11, seconds=50)
    critique_time = account_time + timedelta(seconds=10)
    intent_time = account_time + timedelta(seconds=20)

    plan = SessionPlan(
        plan_id="SESSION_PLAN_2026-08-27_LONDON",
        version=1,
        session_date=date(2026, 8, 27),
        session=SessionName.LONDON,
        created_at_utc=plan_time,
        market_asof_utc=plan_time - timedelta(minutes=1),
        created_by="planner",
        input_sha256=HASH,
        regime="range-to-trend",
        biases=(Bias(symbol="EURUSD", stance=Stance.BULLISH, summary="mild bullish"),),
        scenarios=(Scenario(scenario_id="A", name="pullback", trigger="M15 confirms", action="long", invalidation="below 1.168"),),
        global_invalidation="high-impact shock",
        constraints=SessionConstraints(
            max_risk_pct_per_trade=0.25,
            max_trades=1,
            news_blackout_before_minutes=15,
            news_blackout_after_minutes=15,
            allowed_symbols=("EURUSD",),
            correlation_note="no correlated full risk",
        ),
    )
    plan_ref = store.write_session_plan(plan)
    quote = QuoteSnapshot(
        symbol="EURUSD", bid=1.1700, ask=1.1701, point=0.00001, spread_points=10,
        tick_size=0.00001, tick_value_loss=1.0, volume_min=0.01, volume_max=100,
        volume_step=0.01, stops_level_points=10, asof_utc=market_time,
        server_time="2026.08.27 09:10:00",
    )
    market = MarketSnapshot(
        snapshot_id="MARKET-1", captured_at_utc=market_time, source="fixture", connected=True,
        server_utc_offset_minutes=0, time_mapping_verified=True, time_mapping_source="fixture",
        calendar_available=True, calendar_asof_utc=market_time, quotes=(quote,),
    )
    market_ref = store.write_artifact("snapshots/market.json", market)
    account = AccountSnapshot(
        snapshot_id="ACCOUNT-1", captured_at_utc=account_time, account_fingerprint=HASH,
        server="MetaQuotes-Demo", trade_mode=TradeMode.DEMO, currency="USD",
        balance=100000, equity=100000, margin_free=100000, drawdown_pct=0,
        daily_loss_pct=0, weekly_loss_pct=0, open_risk_pct=0,
        risk_metrics_complete=True, risk_metrics_source="fixture", trades_this_session=0,
        risk_state_sha256="b" * 64, risk_state_asof_utc=account_time,
        risk_state_session_plan_id=plan.plan_id, risk_state_ledger_head_sha256="c" * 64,
        consecutive_losses=0, terminal_connected=True, terminal_trade_allowed=True,
        expert_trading_allowed=True,
    )
    account_ref = store.write_artifact("snapshots/account.json", account)
    candidate = Candidate(
        candidate_id="CANDIDATE-1", created_at_utc=candidate_time, plan=plan_ref,
        market_snapshot=market_ref, account_snapshot=account_ref,
        symbol="EURUSD", direction=Direction.LONG,
        scenario_id="A", entry_condition="M15 close confirms", entry_min=1.1698,
        entry_max=1.1703, stop_loss=1.1680, take_profit=1.1750,
        expiry_utc=intent_time + timedelta(minutes=30), requested_risk_pct=0.25,
        expected_r=2.0, confidence=0.7, evidence_refs=("bar-1",),
    )
    candidate_ref = store.write_artifact("agents/candidate.json", candidate)
    critique = Critique(
        critique_id="CRITIQUE-1", created_at_utc=critique_time, plan=plan_ref,
        market_snapshot=market_ref, account_snapshot=account_ref, candidate=candidate_ref,
        verdict=Decision.APPROVE, checks=("plan", "news", "risk"),
    )
    critique_ref = store.write_artifact("agents/critique.json", critique)
    intent = TradeIntent(
        intent_id="INTENT-1", created_at_utc=intent_time, plan=plan_ref,
        market_snapshot=market_ref, account_snapshot=account_ref, candidate=candidate_ref,
        critique=critique_ref, symbol="EURUSD", direction=Direction.LONG, scenario_id="A",
        entry_min=1.1699, entry_max=1.1702, stop_loss=1.1680, take_profit=1.1750,
        expiry_utc=candidate.expiry_utc, requested_risk_pct=0.25, max_spread_points=20,
        architect_summary="Scenario A exact handoff",
    )
    intent_ref = store.write_artifact("intents/intent.json", intent)
    policy = RiskPolicy(
        policy_id="POLICY-SHADOW-1", runtime_mode=RuntimeMode.SHADOW, kill_switch=False,
        demo_execution_authorized=False, live_execution_authorized=False,
        allowed_account_fingerprints=(HASH,),
        symbols={"EURUSD": SymbolRiskPolicy(max_risk_pct_per_trade=0.25, max_spread_points=20, max_slippage_points=5, min_rr=1.5, max_open_risk_pct=0.25)},
        max_daily_loss_pct=1.0, max_weekly_loss_pct=2.0, max_drawdown_pct=3.0,
        max_aggregate_open_risk_pct=0.5, max_consecutive_losses=3,
        max_trades_per_session=1, quote_ttl_seconds=600, account_ttl_seconds=60,
        calendar_ttl_seconds=3600, news_blackout_before_minutes=15,
        news_blackout_after_minutes=15, magic=26082701,
        correlation_groups=(CorrelationGroup(group_id="USD_RISK", symbols=("EURUSD", "GBPUSD"), max_group_risk_pct=0.25),),
    )
    policy_ref = store.write_artifact("policy/shadow.json", policy)
    return TradeChainRefs(plan_ref, market_ref, account_ref, candidate_ref, critique_ref, intent_ref, policy_ref)


def test_shadow_pipeline_is_hash_bound_and_never_sends(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    refs = build_chain(store)
    now = datetime(2026, 8, 27, 6, 12, 30, tzinfo=UTC)
    ledger = tmp_path / "events.jsonl"

    result = run_shadow_pipeline(store, refs, ledger_path=ledger, now_utc=now)

    assert result.risk_decision.decision == Decision.APPROVE
    assert result.execution_attempt.status == "DRY_RUN"
    assert result.execution_attempt.sent is False
    assert result.handoff_packet["broker_mutation_allowed"] is False
    assert result.handoff_packet["handoff_target"] == "CANONICAL_MQL5_EA_EXECUTOR"

    with pytest.raises(PipelineIntegrityError, match="idempotency key"):
        run_shadow_pipeline(store, refs, ledger_path=ledger, now_utc=now)
