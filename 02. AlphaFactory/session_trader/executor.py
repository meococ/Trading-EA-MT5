"""Non-mutating execution handoff builder.

Python is not an MT5 execution authority in this package.  OBSERVE and SHADOW
produce a hash-bound would-send packet.  DEMO_EXECUTE remains fail-closed until
the canonical MQL5 EA executor and reconciliation bridge are installed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .artifacts import canonical_json_bytes
from .models import (
    ArtifactRef,
    Decision,
    Direction,
    ExecutionAttempt,
    RiskDecision,
    RiskPolicy,
    RuntimeMode,
    TradeIntent,
)


MQL5_HANDOFF_REQUIRED = (
    "MQL5_HANDOFF_REQUIRED: canonical EA executor and broker-state "
    "reconciliation are not installed; no broker request was sent"
)


def _canonical_bytes(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_none=False)  # type: ignore[union-attr]
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _artifact_ref(value: object, artifact_id: str) -> ArtifactRef:
    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return ArtifactRef(
        schema_version=str(getattr(value, "schema_version", "inline.v1")),
        path=f"inline://{artifact_id}/{digest}.json",
        sha256=digest,
    )


def _require_utc_now(now_utc: datetime | None) -> datetime:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("now_utc must be timezone-aware and normalized to UTC")
    return now


def _reference_binds_intent(intent: TradeIntent, reference: ArtifactRef) -> bool:
    if reference.schema_version != intent.schema_version:
        return False
    if reference.path.startswith("inline://"):
        return reference == _artifact_ref(intent, intent.intent_id)
    persisted_digest = hashlib.sha256(canonical_json_bytes(intent) + b"\n").hexdigest()
    return reference.sha256.lower() == persisted_digest


def build_execution_attempt(
    intent: TradeIntent,
    risk_decision: RiskDecision,
    *,
    runtime_mode: RuntimeMode,
    intent_ref: ArtifactRef | None = None,
    risk_decision_ref: ArtifactRef | None = None,
    policy: RiskPolicy | None = None,
    magic: int | None = None,
    max_slippage_points: int | None = None,
    now_utc: datetime | None = None,
) -> tuple[dict[str, Any], ExecutionAttempt]:
    """Build a canonical MQL5 handoff packet without touching a terminal.

    The returned dictionary is an immutable-style artifact: it is fully derived,
    contains no live handle, and is hash-bound by ``ExecutionAttempt.request_sha256``.
    Callers should persist it rather than mutate it.
    """

    now = _require_utc_now(now_utc)
    intent_ref = intent_ref or _artifact_ref(intent, intent.intent_id)
    risk_decision_ref = risk_decision_ref or _artifact_ref(
        risk_decision, risk_decision.decision_id
    )

    if policy is not None:
        if magic is None:
            magic = policy.magic
        if max_slippage_points is None and intent.symbol in policy.symbols:
            max_slippage_points = policy.symbols[intent.symbol].max_slippage_points

    # Compare the complete immutable reference, not just a caller-supplied digest.
    # The pipeline has already read and validated both artifacts from one buffer.
    intent_binding_valid = (
        risk_decision.intent == intent_ref
        and _reference_binds_intent(intent, intent_ref)
    )
    intent_unexpired = now < intent.expiry_utc
    handoff_authorized = (
        risk_decision.decision == Decision.APPROVE
        and intent_binding_valid
        and intent_unexpired
    )
    packet: dict[str, Any] = {
        "schema_version": "mql5_trade_handoff.v1",
        "created_at_utc": now.isoformat().replace("+00:00", "Z"),
        "intent_id": intent.intent_id,
        "risk_decision_id": risk_decision.decision_id,
        "idempotency_key": risk_decision.idempotency_key,
        "symbol": intent.symbol,
        "action": "BUY" if intent.direction == Direction.LONG else "SELL",
        "order_type": intent.order_type,
        "entry_price_observed": risk_decision.entry_price,
        "authorized_entry_min": intent.entry_min,
        "authorized_entry_max": intent.entry_max,
        "volume": risk_decision.volume,
        "stop_loss": intent.stop_loss,
        "take_profit": intent.take_profit,
        "expiry_utc": intent.expiry_utc.isoformat().replace("+00:00", "Z"),
        "approved_risk_pct": risk_decision.approved_risk_pct,
        "max_spread_points": intent.max_spread_points,
        "max_slippage_points": max_slippage_points,
        "magic": magic,
        "runtime_mode": runtime_mode.value,
        "risk_approved": handoff_authorized,
        "intent_binding_valid": intent_binding_valid,
        "intent_unexpired": intent_unexpired,
        "broker_mutation_allowed": False,
        "handoff_target": "CANONICAL_MQL5_EA_EXECUTOR",
    }
    request_sha256 = hashlib.sha256(_canonical_bytes(packet)).hexdigest()
    attempt_id = f"EXEC_{request_sha256[:32]}"

    if risk_decision.decision != Decision.APPROVE:
        status = "CHECK_REJECTED"
        detail = "RISK_DECISION_REJECTED: no executable handoff was authorized"
    elif not intent_binding_valid:
        status = "CHECK_REJECTED"
        detail = "INTENT_ARTIFACT_MISMATCH: risk approval does not bind this intent"
    elif not intent_unexpired:
        status = "CHECK_REJECTED"
        detail = "INTENT_EXPIRED: approved intent expired before execution handoff"
    elif runtime_mode in {RuntimeMode.OBSERVE, RuntimeMode.SHADOW}:
        status = "DRY_RUN"
        detail = (
            f"{runtime_mode.value}_WOULD_SEND_ONLY: hash-bound MQL5 handoff packet "
            "created; no broker request was sent"
        )
    elif runtime_mode == RuntimeMode.DEMO_EXECUTE:
        status = "INCIDENT"
        detail = MQL5_HANDOFF_REQUIRED
    else:
        status = "INCIDENT"
        detail = "LIVE_EXECUTION_LOCKED: this package has no live execution path"

    attempt = ExecutionAttempt(
        attempt_id=attempt_id,
        created_at_utc=now,
        intent=intent_ref,
        risk_decision=risk_decision_ref,
        runtime_mode=runtime_mode,
        request_sha256=request_sha256,
        order_check_retcode=None,
        order_send_retcode=None,
        sent=False,
        broker_order=None,
        broker_deal=None,
        status=status,
        detail=detail,
    )
    return packet, attempt


__all__ = ["MQL5_HANDOFF_REQUIRED", "build_execution_attempt"]
