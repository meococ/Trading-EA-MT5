"""Deterministic, fail-closed risk authority for session trade intents.

This module deliberately contains no broker adapter.  It converts immutable
snapshots plus an immutable policy into a :class:`RiskDecision`; only an MQL5
executor may later turn an approved decision into a broker request.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import Collection

from .artifacts import canonical_json_bytes
from .models import (
    AccountSnapshot,
    ArtifactRef,
    Decision,
    Direction,
    Importance,
    MarketSnapshot,
    QuoteSnapshot,
    RiskDecision,
    RiskPolicy,
    RuntimeMode,
    SessionPlan,
    TradeIntent,
    TradeMode,
)


APPROVED_REASON = "APPROVED_BY_DETERMINISTIC_RISK_GATEWAY"


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
    schema_version = str(getattr(value, "schema_version", "inline.v1"))
    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return ArtifactRef(
        schema_version=schema_version,
        path=f"inline://{artifact_id}/{digest}.json",
        sha256=digest,
    )


def _reference_binds_value(
    value: object,
    reference: ArtifactRef,
    artifact_id: str,
) -> bool:
    if reference.schema_version != str(getattr(value, "schema_version", "inline.v1")):
        return False
    if reference.path.startswith("inline://"):
        return reference == _artifact_ref(value, artifact_id)
    persisted_digest = hashlib.sha256(canonical_json_bytes(value) + b"\n").hexdigest()
    return reference.sha256.lower() == persisted_digest


def _require_utc_now(now_utc: datetime | None) -> datetime:
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("now_utc must be timezone-aware and normalized to UTC")
    return now


def _idempotency_key(intent: TradeIntent, account: AccountSnapshot) -> str:
    # Intent identity, not mutable content, is the once-only execution boundary.
    # Re-serializing an existing ID with altered fields must not create a fresh key.
    material = {
        "account_fingerprint": account.account_fingerprint.lower(),
        "intent_id": intent.intent_id,
    }
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _decision_id(intent: TradeIntent, idempotency_key: str) -> str:
    digest = hashlib.sha256(
        f"risk-decision:{intent.intent_id}:{idempotency_key}".encode("utf-8")
    ).hexdigest()
    return f"RISK_{digest[:32]}"


def _find_quote(market: MarketSnapshot, symbol: str) -> QuoteSnapshot | None:
    return next((quote for quote in market.quotes if quote.symbol == symbol), None)


def _symbol_currencies(symbol: str) -> set[str]:
    letters = "".join(character for character in symbol.upper() if character.isalpha())
    if len(letters) < 6:
        return set()
    return {letters[:3], letters[3:6]}


def _is_in_news_blackout(
    intent: TradeIntent,
    market: MarketSnapshot,
    policy: RiskPolicy,
    now_utc: datetime,
    session_plan: SessionPlan,
) -> bool:
    currencies = _symbol_currencies(intent.symbol)
    if not currencies:
        return False
    before_minutes = policy.news_blackout_before_minutes
    after_minutes = policy.news_blackout_after_minutes
    events = list(market.calendar)
    before_minutes = max(
        before_minutes, session_plan.constraints.news_blackout_before_minutes
    )
    after_minutes = max(
        after_minutes, session_plan.constraints.news_blackout_after_minutes
    )
    known = {(event.event_id, event.event_time_utc) for event in events}
    events.extend(
        event
        for event in session_plan.calendar
        if (event.event_id, event.event_time_utc) not in known
    )
    before = timedelta(minutes=before_minutes)
    after = timedelta(minutes=after_minutes)
    return any(
        event.importance == Importance.HIGH
        and event.currency.upper() in currencies
        and event.event_time_utc - before <= now_utc <= event.event_time_utc + after
        for event in events
    )


def _normalized_volume(
    *,
    equity: float,
    risk_pct: float,
    entry_price: float,
    stop_loss: float,
    quote: QuoteSnapshot,
) -> tuple[float, float]:
    """Return volume rounded down to the broker step and its effective risk %.

    Rounding down is essential: a gateway must never exceed the capped risk merely
    to satisfy a broker's volume grid.  A sub-minimum result remains zero so the
    caller can reject it rather than rounding up.
    """

    ticks_to_stop = abs(entry_price - stop_loss) / quote.tick_size
    loss_per_lot = ticks_to_stop * quote.tick_value_loss
    if not math.isfinite(loss_per_lot) or loss_per_lot <= 0.0 or equity <= 0.0:
        return 0.0, 0.0

    requested_cash_risk = equity * risk_pct / 100.0
    raw_volume = requested_cash_risk / loss_per_lot
    step = Decimal(str(quote.volume_step))
    raw = Decimal(str(raw_volume))
    stepped = (raw / step).to_integral_value(rounding=ROUND_FLOOR) * step
    maximum = Decimal(str(quote.volume_max))
    if stepped > maximum:
        stepped = (maximum / step).to_integral_value(rounding=ROUND_FLOOR) * step
    volume = float(stepped)
    if volume + 1e-12 < quote.volume_min:
        return 0.0, 0.0

    actual_cash_risk = volume * loss_per_lot
    effective_risk_pct = min(risk_pct, actual_cash_risk / equity * 100.0)
    return volume, effective_risk_pct


def evaluate_risk(
    intent: TradeIntent,
    policy: RiskPolicy,
    market_snapshot: MarketSnapshot,
    account_snapshot: AccountSnapshot,
    *,
    intent_ref: ArtifactRef | None = None,
    policy_ref: ArtifactRef | None = None,
    market_snapshot_ref: ArtifactRef | None = None,
    account_snapshot_ref: ArtifactRef | None = None,
    session_plan: SessionPlan,
    session_plan_ref: ArtifactRef,
    used_idempotency_keys: Collection[str] = (),
    now_utc: datetime | None = None,
) -> RiskDecision:
    """Evaluate an intent using deterministic rules and return one frozen verdict.

    All applicable rejection reasons are retained for auditability.  Inputs that
    cannot prove safety are rejected; the gateway never assumes missing account,
    symbol, quote, or risk information is benign.
    """

    now = _require_utc_now(now_utc)
    intent_ref = intent_ref or _artifact_ref(intent, intent.intent_id)
    policy_ref = policy_ref or _artifact_ref(policy, policy.policy_id)
    market_snapshot_ref = market_snapshot_ref or _artifact_ref(
        market_snapshot, market_snapshot.snapshot_id
    )
    account_snapshot_ref = account_snapshot_ref or _artifact_ref(
        account_snapshot, account_snapshot.snapshot_id
    )
    key = _idempotency_key(intent, account_snapshot)
    reasons: list[str] = []

    if policy.kill_switch:
        reasons.append("KILL_SWITCH_ACTIVE")
    if policy.runtime_mode == RuntimeMode.LIVE_LOCKED:
        reasons.append("LIVE_EXECUTION_LOCKED")
    if account_snapshot.trade_mode == TradeMode.REAL:
        reasons.append("REAL_ACCOUNT_FORBIDDEN")
    elif account_snapshot.trade_mode == TradeMode.UNKNOWN:
        reasons.append("UNKNOWN_ACCOUNT_MODE")
    elif account_snapshot.trade_mode == TradeMode.CONTEST:
        reasons.append("CONTEST_ACCOUNT_UNSUPPORTED")
    if account_snapshot.account_fingerprint.lower() not in {
        fingerprint.lower() for fingerprint in policy.allowed_account_fingerprints
    }:
        reasons.append("ACCOUNT_NOT_ALLOWLISTED")
    if not getattr(account_snapshot, "risk_metrics_complete", False):
        reasons.append("ACCOUNT_RISK_METRICS_INCOMPLETE")
    elif not all(
        (
            account_snapshot.risk_state_sha256,
            account_snapshot.risk_state_asof_utc,
            account_snapshot.risk_state_session_plan_id,
            account_snapshot.risk_state_ledger_head_sha256,
        )
    ):
        reasons.append("ACCOUNT_RISK_STATE_UNBOUND")
    elif account_snapshot.risk_state_session_plan_id != session_plan.plan_id:
        reasons.append("ACCOUNT_RISK_STATE_PLAN_MISMATCH")
    account_age = (now - account_snapshot.captured_at_utc).total_seconds()
    if account_age < 0 or account_age > policy.account_ttl_seconds:
        reasons.append("STALE_ACCOUNT_SNAPSHOT")
    if not market_snapshot.connected or not account_snapshot.terminal_connected:
        reasons.append("TERMINAL_DISCONNECTED")
    if not account_snapshot.terminal_trade_allowed:
        reasons.append("TERMINAL_TRADING_DISABLED")
    if not account_snapshot.expert_trading_allowed:
        reasons.append("EXPERT_TRADING_DISABLED")
    if intent.expiry_utc <= now:
        reasons.append("INTENT_EXPIRED")
    if (
        intent.plan != session_plan_ref
        or not _reference_binds_value(session_plan, session_plan_ref, session_plan.plan_id)
    ):
        reasons.append("SESSION_PLAN_REFERENCE_MISMATCH")
    if intent.symbol not in session_plan.constraints.allowed_symbols:
        reasons.append("SESSION_PLAN_SYMBOL_VIOLATION")
    if intent.scenario_id not in {
        scenario.scenario_id for scenario in session_plan.scenarios
    }:
        reasons.append("SESSION_PLAN_SCENARIO_VIOLATION")
    if intent.requested_risk_pct > session_plan.constraints.max_risk_pct_per_trade:
        reasons.append("SESSION_PLAN_RISK_LIMIT_EXCEEDED")
    if key in used_idempotency_keys:
        reasons.append("DUPLICATE_IDEMPOTENCY_KEY")
    if (
        not market_snapshot.time_mapping_verified
        or market_snapshot.server_utc_offset_minutes is None
    ):
        reasons.append("TIME_MAPPING_UNVERIFIED")
    if not market_snapshot.calendar_available:
        reasons.append("CALENDAR_UNAVAILABLE")
    elif market_snapshot.calendar_asof_utc is None:
        # The model normally prevents this state, but retain the fail-closed
        # branch in case an alternate snapshot implementation reaches here.
        reasons.append("CALENDAR_UNAVAILABLE")
    else:
        calendar_age = (now - market_snapshot.calendar_asof_utc).total_seconds()
        if calendar_age < 0 or calendar_age > policy.calendar_ttl_seconds:
            reasons.append("STALE_CALENDAR")

    symbol_policy = policy.symbols.get(intent.symbol)
    quote = _find_quote(market_snapshot, intent.symbol)
    entry_price = 0.0
    estimated_rr = 0.0
    capped_risk_pct = 0.0
    volume = 0.0
    effective_risk_pct = 0.0

    if symbol_policy is None:
        reasons.append("UNKNOWN_OR_DISALLOWED_SYMBOL")
    if quote is None:
        reasons.append("SYMBOL_QUOTE_MISSING")
    else:
        quote_age = (now - quote.asof_utc).total_seconds()
        if quote_age < 0:
            reasons.append("QUOTE_TIMESTAMP_IN_FUTURE")
        elif quote_age > policy.quote_ttl_seconds:
            reasons.append("STALE_QUOTE")
        entry_price = quote.ask if intent.direction == Direction.LONG else quote.bid
        if not (intent.entry_min <= entry_price <= intent.entry_max):
            reasons.append("ENTRY_OUTSIDE_AUTHORIZED_RANGE")

        if intent.direction == Direction.LONG:
            if not (intent.stop_loss < entry_price < intent.take_profit):
                reasons.append("INVALID_LONG_STOP_TARGET_GEOMETRY")
        elif not (intent.take_profit < entry_price < intent.stop_loss):
            reasons.append("INVALID_SHORT_STOP_TARGET_GEOMETRY")

        stop_distance = abs(entry_price - intent.stop_loss)
        target_distance = abs(intent.take_profit - entry_price)
        minimum_stop_distance = quote.stops_level_points * quote.point
        if stop_distance <= 0.0:
            reasons.append("STOP_LOSS_REQUIRED")
        elif stop_distance + 1e-12 < minimum_stop_distance:
            reasons.append("STOP_INSIDE_BROKER_MINIMUM")
        if target_distance <= 0.0:
            reasons.append("TAKE_PROFIT_REQUIRED")
        if stop_distance > 0.0:
            estimated_rr = target_distance / stop_distance

    if symbol_policy is not None and quote is not None:
        spread_limit = min(symbol_policy.max_spread_points, intent.max_spread_points)
        if quote.spread_points > spread_limit:
            reasons.append("SPREAD_LIMIT_EXCEEDED")
        if estimated_rr + 1e-12 < symbol_policy.min_rr:
            reasons.append("MINIMUM_RR_NOT_MET")

    if _is_in_news_blackout(intent, market_snapshot, policy, now, session_plan):
        reasons.append("HIGH_IMPACT_NEWS_BLACKOUT")
    if intent.requested_risk_pct <= 0.0:
        reasons.append("NON_POSITIVE_RISK_REQUEST")
    elif symbol_policy is not None:
        risk_caps = [intent.requested_risk_pct, symbol_policy.max_risk_pct_per_trade]
        risk_caps.append(session_plan.constraints.max_risk_pct_per_trade)
        capped_risk_pct = min(risk_caps)

    if account_snapshot.daily_loss_pct >= policy.max_daily_loss_pct:
        reasons.append("DAILY_LOSS_LIMIT_REACHED")
    if account_snapshot.weekly_loss_pct >= policy.max_weekly_loss_pct:
        reasons.append("WEEKLY_LOSS_LIMIT_REACHED")
    if account_snapshot.drawdown_pct >= policy.max_drawdown_pct:
        reasons.append("DRAWDOWN_LIMIT_REACHED")
    if account_snapshot.consecutive_losses >= policy.max_consecutive_losses:
        reasons.append("CONSECUTIVE_LOSS_LIMIT_REACHED")
    max_session_trades = min(
        policy.max_trades_per_session, session_plan.constraints.max_trades
    )
    if account_snapshot.trades_this_session >= max_session_trades:
        reasons.append("SESSION_TRADE_LIMIT_REACHED")

    if capped_risk_pct > 0.0:
        if (
            account_snapshot.open_risk_pct + capped_risk_pct
            > policy.max_aggregate_open_risk_pct + 1e-12
        ):
            reasons.append("AGGREGATE_OPEN_RISK_LIMIT_EXCEEDED")
        if symbol_policy is not None:
            same_symbol_risk = sum(
                position.risk_pct
                for position in account_snapshot.positions
                if position.symbol == intent.symbol
            )
            if (
                same_symbol_risk + capped_risk_pct
                > symbol_policy.max_open_risk_pct + 1e-12
            ):
                reasons.append("SYMBOL_OPEN_RISK_LIMIT_EXCEEDED")
        for group in policy.correlation_groups:
            if intent.symbol not in group.symbols:
                continue
            group_risk = sum(
                position.risk_pct
                for position in account_snapshot.positions
                if position.symbol in group.symbols
            )
            if group_risk + capped_risk_pct > group.max_group_risk_pct + 1e-12:
                reasons.append(f"CORRELATION_RISK_LIMIT_EXCEEDED:{group.group_id}")

    geometry_is_valid = not any(
        reason
        in {
            "INVALID_LONG_STOP_TARGET_GEOMETRY",
            "INVALID_SHORT_STOP_TARGET_GEOMETRY",
            "STOP_LOSS_REQUIRED",
            "STOP_INSIDE_BROKER_MINIMUM",
            "TAKE_PROFIT_REQUIRED",
        }
        for reason in reasons
    )
    if quote is not None and capped_risk_pct > 0.0 and geometry_is_valid:
        volume, effective_risk_pct = _normalized_volume(
            equity=account_snapshot.equity,
            risk_pct=capped_risk_pct,
            entry_price=entry_price,
            stop_loss=intent.stop_loss,
            quote=quote,
        )
        if volume <= 0.0:
            reasons.append("RISK_TOO_SMALL_FOR_MINIMUM_VOLUME")

    approved = not reasons
    return RiskDecision(
        decision_id=_decision_id(intent, key),
        created_at_utc=now,
        intent=intent_ref,
        policy=policy_ref,
        market_snapshot=market_snapshot_ref,
        account_snapshot=account_snapshot_ref,
        decision=Decision.APPROVE if approved else Decision.REJECT,
        reasons=(APPROVED_REASON,) if approved else tuple(reasons),
        approved_risk_pct=effective_risk_pct if approved else 0.0,
        entry_price=entry_price,
        volume=volume if approved else 0.0,
        estimated_rr=estimated_rr,
        idempotency_key=key,
    )


class RiskGateway:
    """Small injectable wrapper around :func:`evaluate_risk`."""

    def __init__(
        self,
        policy: RiskPolicy,
        session_plan: SessionPlan,
        session_plan_ref: ArtifactRef,
    ) -> None:
        self._policy = policy
        self._session_plan = session_plan
        self._session_plan_ref = session_plan_ref

    @property
    def policy(self) -> RiskPolicy:
        return self._policy

    def evaluate(
        self,
        intent: TradeIntent,
        market_snapshot: MarketSnapshot,
        account_snapshot: AccountSnapshot,
        **kwargs: object,
    ) -> RiskDecision:
        return evaluate_risk(
            intent,
            self._policy,
            market_snapshot,
            account_snapshot,
            session_plan=self._session_plan,
            session_plan_ref=self._session_plan_ref,
            **kwargs,  # type: ignore[arg-type]
        )


__all__ = ["APPROVED_REASON", "RiskGateway", "evaluate_risk"]
