from __future__ import annotations

import ast
import hashlib
import inspect
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ALPHA_ROOT = Path(__file__).resolve().parents[1]
if str(ALPHA_ROOT) not in sys.path:
    sys.path.insert(0, str(ALPHA_ROOT))

import session_trader.executor as executor_module
from session_trader.executor import MQL5_HANDOFF_REQUIRED, build_execution_attempt
from session_trader.models import (
    ArtifactRef,
    Decision,
    Direction,
    ExecutionAttempt,
    RiskDecision,
    RuntimeMode,
    TradeIntent,
)


NOW = datetime(2026, 8, 27, 8, 0, tzinfo=timezone.utc)


def ref(name: str) -> ArtifactRef:
    return ArtifactRef(schema_version=f"{name}.v1", path=f"artifacts/{name}.json", sha256="d" * 64)


def content_ref(value: object, name: str) -> ArtifactRef:
    payload = value.model_dump(mode="json", exclude_none=False)  # type: ignore[attr-defined]
    digest = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return ArtifactRef(
        schema_version=str(getattr(value, "schema_version")),
        path=f"inline://{name}/{digest}.json",
        sha256=digest,
    )


def intent() -> TradeIntent:
    return TradeIntent(
        intent_id="TRADE_INTENT_8293",
        created_at_utc=NOW - timedelta(minutes=1),
        plan=ref("plan"),
        market_snapshot=ref("market"),
        account_snapshot=ref("account"),
        candidate=ref("candidate"),
        critique=ref("critique"),
        symbol="EURUSD",
        direction=Direction.LONG,
        scenario_id="LONDON_PULLBACK",
        entry_min=1.1000,
        entry_max=1.1005,
        stop_loss=1.0982,
        take_profit=1.1042,
        expiry_utc=NOW + timedelta(hours=1),
        requested_risk_pct=0.25,
        max_spread_points=3.0,
        architect_summary="Scenario A.",
    )


def decision(
    verdict: Decision = Decision.APPROVE, bound_intent: TradeIntent | None = None
) -> RiskDecision:
    approved = verdict == Decision.APPROVE
    bound_intent = bound_intent or intent()
    return RiskDecision(
        decision_id="RISK_1",
        created_at_utc=NOW,
        intent=content_ref(bound_intent, bound_intent.intent_id),
        policy=ref("policy"),
        market_snapshot=ref("market"),
        account_snapshot=ref("account"),
        decision=verdict,
        reasons=("APPROVED",) if approved else ("KILL_SWITCH_ACTIVE",),
        approved_risk_pct=0.24 if approved else 0.0,
        entry_price=1.1002,
        volume=0.12 if approved else 0.0,
        estimated_rr=2.0,
        idempotency_key="e" * 64,
    )


@pytest.mark.parametrize("mode", [RuntimeMode.OBSERVE, RuntimeMode.SHADOW])
def test_observe_and_shadow_only_build_hash_bound_would_send_packet(mode: RuntimeMode) -> None:
    proposed = intent()
    packet, attempt = build_execution_attempt(
        proposed,
        decision(bound_intent=proposed),
        runtime_mode=mode,
        magic=8293,
        max_slippage_points=5,
        now_utc=NOW,
    )

    expected_hash = hashlib.sha256(
        json.dumps(
            packet,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert packet["broker_mutation_allowed"] is False
    assert packet["handoff_target"] == "CANONICAL_MQL5_EA_EXECUTOR"
    assert packet["action"] == "BUY"
    assert packet["volume"] == pytest.approx(0.12)
    assert attempt.status == "DRY_RUN"
    assert attempt.sent is False
    assert attempt.request_sha256 == expected_hash
    with pytest.raises(Exception):
        attempt.sent = True


def test_demo_execute_is_an_explicit_mql5_handoff_incident() -> None:
    proposed = intent()
    packet, attempt = build_execution_attempt(
        proposed,
        decision(bound_intent=proposed),
        runtime_mode=RuntimeMode.DEMO_EXECUTE,
        now_utc=NOW,
    )

    assert packet["broker_mutation_allowed"] is False
    assert attempt.status == "INCIDENT"
    assert attempt.sent is False
    assert attempt.detail == MQL5_HANDOFF_REQUIRED


def test_live_locked_has_no_execution_path() -> None:
    proposed = intent()
    _, attempt = build_execution_attempt(
        proposed,
        decision(bound_intent=proposed),
        runtime_mode=RuntimeMode.LIVE_LOCKED,
        now_utc=NOW,
    )

    assert attempt.status == "INCIDENT"
    assert attempt.sent is False
    assert "LIVE_EXECUTION_LOCKED" in attempt.detail


def test_rejected_risk_decision_never_becomes_executable() -> None:
    proposed = intent()
    packet, attempt = build_execution_attempt(
        proposed,
        decision(Decision.REJECT, proposed),
        runtime_mode=RuntimeMode.SHADOW,
        now_utc=NOW,
    )

    assert packet["risk_approved"] is False
    assert attempt.status == "CHECK_REJECTED"
    assert attempt.sent is False


def test_mismatched_approved_intent_is_rejected() -> None:
    approved_for = intent()
    substituted = approved_for.model_copy(update={"take_profit": 1.1100})

    packet, attempt = build_execution_attempt(
        substituted,
        decision(bound_intent=approved_for),
        runtime_mode=RuntimeMode.SHADOW,
        now_utc=NOW,
    )

    assert packet["intent_binding_valid"] is False
    assert packet["risk_approved"] is False
    assert attempt.status == "CHECK_REJECTED"
    assert "INTENT_ARTIFACT_MISMATCH" in attempt.detail


def test_same_digest_with_substituted_artifact_path_is_rejected() -> None:
    proposed = intent()
    approved = decision(bound_intent=proposed)
    substituted_ref = approved.intent.model_copy(update={"path": "agents/other-intent.json"})

    packet, attempt = build_execution_attempt(
        proposed,
        approved,
        runtime_mode=RuntimeMode.SHADOW,
        intent_ref=substituted_ref,
        now_utc=NOW,
    )

    assert packet["intent_binding_valid"] is False
    assert attempt.status == "CHECK_REJECTED"


def test_approved_reference_cannot_authorize_substituted_intent_content() -> None:
    approved_for = intent()
    approved = decision(bound_intent=approved_for)
    substituted = approved_for.model_copy(update={"take_profit": 1.1100})

    packet, attempt = build_execution_attempt(
        substituted,
        approved,
        runtime_mode=RuntimeMode.SHADOW,
        intent_ref=approved.intent,
        now_utc=NOW,
    )

    assert packet["intent_binding_valid"] is False
    assert packet["risk_approved"] is False
    assert attempt.status == "CHECK_REJECTED"


def test_intent_expired_after_risk_approval_is_rejected() -> None:
    proposed = intent()
    packet, attempt = build_execution_attempt(
        proposed,
        decision(bound_intent=proposed),
        runtime_mode=RuntimeMode.SHADOW,
        now_utc=proposed.expiry_utc,
    )

    assert packet["intent_unexpired"] is False
    assert packet["risk_approved"] is False
    assert attempt.status == "CHECK_REJECTED"
    assert "INTENT_EXPIRED" in attempt.detail


def test_executor_has_no_mt5_import_or_broker_send_call() -> None:
    tree = ast.parse(inspect.getsource(executor_module))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    called_names = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "MetaTrader5" not in imported_modules
    assert "order_send" not in called_names
    assert "order_check" not in called_names


def test_execution_attempt_model_itself_rejects_sent_shadow_record() -> None:
    with pytest.raises(ValueError):
        ExecutionAttempt(
            attempt_id="bad",
            created_at_utc=NOW,
            intent=ref("intent"),
            risk_decision=ref("risk"),
            runtime_mode=RuntimeMode.SHADOW,
            request_sha256="f" * 64,
            sent=True,
            status="SENT",
            detail="must fail",
        )
