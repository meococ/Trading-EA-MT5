from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .artifacts import ArtifactIntegrityError, ArtifactStore, HashChainLedger
from .executor import build_execution_attempt
from .models import (
    AccountSnapshot,
    ArtifactRef,
    Candidate,
    Critique,
    Decision,
    ExecutionAttempt,
    MarketSnapshot,
    RiskDecision,
    RiskPolicy,
    RuntimeMode,
    SessionPlan,
    TradeIntent,
)
from .risk_gateway import evaluate_risk


class PipelineIntegrityError(RuntimeError):
    pass


T = TypeVar("T", bound=BaseModel)


def _load(store: ArtifactStore, reference: ArtifactRef, model_type: type[T]) -> T:
    try:
        value = model_type.model_validate_json(store.read_verified_bytes(reference))
    except (ArtifactIntegrityError, OSError, ValidationError) as exc:
        raise PipelineIntegrityError(f"invalid {model_type.__name__} artifact: {reference.path}") from exc
    if getattr(value, "schema_version", None) != reference.schema_version:
        raise PipelineIntegrityError(f"schema version mismatch for {reference.path}")
    return value


@dataclass(frozen=True)
class TradeChainRefs:
    plan: ArtifactRef
    market_snapshot: ArtifactRef
    account_snapshot: ArtifactRef
    candidate: ArtifactRef
    critique: ArtifactRef
    intent: ArtifactRef
    policy: ArtifactRef


@dataclass(frozen=True)
class VerifiedTradeChain:
    refs: TradeChainRefs
    plan: SessionPlan
    market_snapshot: MarketSnapshot
    account_snapshot: AccountSnapshot
    candidate: Candidate
    critique: Critique
    intent: TradeIntent
    policy: RiskPolicy


@dataclass(frozen=True)
class ShadowPipelineResult:
    risk_decision: RiskDecision
    risk_decision_ref: ArtifactRef
    handoff_packet: dict[str, object]
    handoff_ref: ArtifactRef
    execution_attempt: ExecutionAttempt
    execution_attempt_ref: ArtifactRef


def _same_ref(actual: ArtifactRef, expected: ArtifactRef, label: str) -> None:
    if actual != expected:
        raise PipelineIntegrityError(f"{label} artifact reference mismatch")


def load_verified_trade_chain(store: ArtifactStore, refs: TradeChainRefs) -> VerifiedTradeChain:
    plan = _load(store, refs.plan, SessionPlan)
    market = _load(store, refs.market_snapshot, MarketSnapshot)
    account = _load(store, refs.account_snapshot, AccountSnapshot)
    candidate = _load(store, refs.candidate, Candidate)
    critique = _load(store, refs.critique, Critique)
    intent = _load(store, refs.intent, TradeIntent)
    policy = _load(store, refs.policy, RiskPolicy)

    _same_ref(candidate.plan, refs.plan, "candidate.plan")
    _same_ref(candidate.market_snapshot, refs.market_snapshot, "candidate.market_snapshot")
    _same_ref(candidate.account_snapshot, refs.account_snapshot, "candidate.account_snapshot")
    _same_ref(critique.plan, refs.plan, "critique.plan")
    _same_ref(critique.market_snapshot, refs.market_snapshot, "critique.market_snapshot")
    _same_ref(critique.account_snapshot, refs.account_snapshot, "critique.account_snapshot")
    _same_ref(critique.candidate, refs.candidate, "critique.candidate")
    _same_ref(intent.plan, refs.plan, "intent.plan")
    _same_ref(intent.market_snapshot, refs.market_snapshot, "intent.market_snapshot")
    _same_ref(intent.account_snapshot, refs.account_snapshot, "intent.account_snapshot")
    _same_ref(intent.candidate, refs.candidate, "intent.candidate")
    _same_ref(intent.critique, refs.critique, "intent.critique")

    if critique.verdict != Decision.APPROVE:
        raise PipelineIntegrityError("TradeIntent cannot follow a critic rejection")
    if candidate.symbol not in plan.constraints.allowed_symbols:
        raise PipelineIntegrityError("candidate symbol is outside the SessionPlan")
    if candidate.scenario_id not in {scenario.scenario_id for scenario in plan.scenarios}:
        raise PipelineIntegrityError("candidate scenario is outside the SessionPlan")
    if candidate.requested_risk_pct > plan.constraints.max_risk_pct_per_trade:
        raise PipelineIntegrityError("candidate risk exceeds the SessionPlan")
    if intent.requested_risk_pct > plan.constraints.max_risk_pct_per_trade:
        raise PipelineIntegrityError("intent risk exceeds the SessionPlan")
    if intent.symbol != candidate.symbol or intent.direction != candidate.direction:
        raise PipelineIntegrityError("architect changed candidate symbol or direction")
    if intent.scenario_id != candidate.scenario_id:
        raise PipelineIntegrityError("architect changed the candidate scenario")
    if intent.stop_loss != candidate.stop_loss or intent.take_profit != candidate.take_profit:
        raise PipelineIntegrityError("architect changed candidate stop/target geometry")
    if intent.entry_min < candidate.entry_min or intent.entry_max > candidate.entry_max:
        raise PipelineIntegrityError("architect widened the candidate entry range")
    if intent.requested_risk_pct > candidate.requested_risk_pct:
        raise PipelineIntegrityError("architect increased candidate risk")
    if intent.expiry_utc > candidate.expiry_utc:
        raise PipelineIntegrityError("architect extended candidate expiry")
    if not (
        plan.created_at_utc
        <= candidate.created_at_utc
        <= critique.created_at_utc
        <= intent.created_at_utc
    ):
        raise PipelineIntegrityError("plan/candidate/critique/intent chronology is invalid")
    if market.captured_at_utc > candidate.created_at_utc:
        raise PipelineIntegrityError("candidate predates its market snapshot")
    if account.captured_at_utc > candidate.created_at_utc:
        raise PipelineIntegrityError("candidate predates its account snapshot")

    return VerifiedTradeChain(refs, plan, market, account, candidate, critique, intent, policy)


def _ledger_idempotency_keys(ledger: HashChainLedger) -> set[str]:
    keys: set[str] = set()
    for entry in ledger.verify():
        envelope = entry.get("payload")
        if not isinstance(envelope, dict):
            continue
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            continue
        value = payload.get("idempotency_key")
        if isinstance(value, str) and value:
            keys.add(value)
    return keys


def run_shadow_pipeline(
    store: ArtifactStore,
    refs: TradeChainRefs,
    *,
    ledger_path: str | Path,
    now_utc,
) -> ShadowPipelineResult:
    chain = load_verified_trade_chain(store, refs)
    if chain.policy.runtime_mode not in {RuntimeMode.OBSERVE, RuntimeMode.SHADOW}:
        raise PipelineIntegrityError("shadow pipeline accepts only OBSERVE or SHADOW policy")

    ledger = HashChainLedger(ledger_path)
    used_keys = _ledger_idempotency_keys(ledger)
    risk = evaluate_risk(
        chain.intent,
        chain.policy,
        chain.market_snapshot,
        chain.account_snapshot,
        intent_ref=refs.intent,
        policy_ref=refs.policy,
        market_snapshot_ref=refs.market_snapshot,
        account_snapshot_ref=refs.account_snapshot,
        session_plan=chain.plan,
        session_plan_ref=refs.plan,
        used_idempotency_keys=used_keys,
        now_utc=now_utc,
    )
    if risk.idempotency_key in used_keys:
        raise PipelineIntegrityError("intent idempotency key already exists in the ledger")

    ledger.reserve_idempotency_key(
        risk.idempotency_key,
        {
            "event_type": "INTENT_IDEMPOTENCY_RESERVED",
            "session_plan_id": chain.plan.plan_id,
            "idempotency_key": risk.idempotency_key,
            "payload": {
                "idempotency_key": risk.idempotency_key,
                "intent_id": chain.intent.intent_id,
            },
        },
    )

    risk_ref = store.write_artifact(
        f"risk/{risk.decision_id}.json",
        risk,
    )
    ledger.append(
        {
            "event_type": "RISK_DECISION_CREATED",
            "session_plan_id": chain.plan.plan_id,
            "artifact": risk_ref.model_dump(mode="json"),
            "payload": risk.model_dump(mode="json"),
        }
    )

    packet, attempt = build_execution_attempt(
        chain.intent,
        risk,
        runtime_mode=chain.policy.runtime_mode,
        intent_ref=refs.intent,
        risk_decision_ref=risk_ref,
        policy=chain.policy,
        now_utc=now_utc,
    )
    handoff_ref = store.write_artifact(
        f"handoff/{attempt.attempt_id}.json",
        packet,
        schema_version="mql5_trade_handoff.v1",
    )
    attempt_ref = store.write_artifact(
        f"execution/{attempt.attempt_id}.json",
        attempt,
    )
    ledger.append(
        {
            "event_type": "EXECUTION_ATTEMPT",
            "session_plan_id": chain.plan.plan_id,
            "artifact": attempt_ref.model_dump(mode="json"),
            "handoff": handoff_ref.model_dump(mode="json"),
            "payload": attempt.model_dump(mode="json"),
        }
    )
    return ShadowPipelineResult(risk, risk_ref, packet, handoff_ref, attempt, attempt_ref)
