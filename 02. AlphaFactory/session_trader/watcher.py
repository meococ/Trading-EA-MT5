"""Pure, deterministic heartbeat scan for deciding whether an agent is needed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Iterable, Mapping

from .artifacts import canonical_json_bytes
from .models import (
    AccountSnapshot,
    Importance,
    MarketSnapshot,
    PositionSnapshot,
    SessionPlan,
    WatchDecision,
    WatchTrigger,
    require_utc,
)


@dataclass(frozen=True)
class WatcherConfig:
    """Thresholds for the cheap scan; all values are explicit and inspectable."""

    quote_ttl_seconds: int = 600
    account_ttl_seconds: int = 600
    spread_limits_points: Mapping[str, float] = field(default_factory=dict)
    spread_increase_ratio: float = 2.0
    zone_buffer_points: float = 0.0
    near_sl_tp_points: float = 10.0
    high_impact_news_horizon_minutes: int = 30
    account_risk_delta_pct: float = 0.10
    future_timestamp_tolerance_seconds: int = 5

    def __post_init__(self) -> None:
        positive = {
            "quote_ttl_seconds": self.quote_ttl_seconds,
            "account_ttl_seconds": self.account_ttl_seconds,
            "spread_increase_ratio": self.spread_increase_ratio,
            "high_impact_news_horizon_minutes": self.high_impact_news_horizon_minutes,
        }
        if any(value <= 0 for value in positive.values()):
            raise ValueError(f"watcher thresholds must be positive: {positive}")
        nonnegative = {
            "zone_buffer_points": self.zone_buffer_points,
            "near_sl_tp_points": self.near_sl_tp_points,
            "account_risk_delta_pct": self.account_risk_delta_pct,
            "future_timestamp_tolerance_seconds": self.future_timestamp_tolerance_seconds,
        }
        if any(value < 0 for value in nonnegative.values()):
            raise ValueError(f"watcher thresholds cannot be negative: {nonnegative}")
        if any(value <= 0 for value in self.spread_limits_points.values()):
            raise ValueError("spread limits must be positive")


def _position_identity(position: PositionSnapshot) -> tuple[object, ...]:
    # current_price changes every tick and must not turn every heartbeat into a trigger.
    return (
        position.ticket,
        position.symbol,
        position.direction.value,
        position.volume,
        position.open_price,
        position.stop_loss,
        position.take_profit,
        position.risk_pct,
        position.magic,
    )


def _positions(account: AccountSnapshot) -> tuple[tuple[object, ...], ...]:
    return tuple(sorted((_position_identity(item) for item in account.positions)))


def _append_detail(
    found: dict[WatchTrigger, list[str]], trigger: WatchTrigger, detail: str
) -> None:
    found.setdefault(trigger, []).append(detail)


def _unique_events(plan: SessionPlan, market: MarketSnapshot):
    # Live market copies override plan copies (for example actual_released changes).
    events = {event.event_id: event for event in plan.calendar}
    events.update({event.event_id: event for event in market.calendar})
    return tuple(events[key] for key in sorted(events))


def _decision_id(
    evaluated_at_utc: datetime,
    plan: SessionPlan,
    market: MarketSnapshot,
    account: AccountSnapshot,
    triggers: Iterable[WatchTrigger],
    details: Iterable[str],
) -> str:
    material = {
        "evaluated_at_utc": evaluated_at_utc.isoformat(),
        "plan_id": plan.plan_id,
        "plan_version": plan.version,
        "market_snapshot_id": market.snapshot_id,
        "account_snapshot_id": account.snapshot_id,
        "triggers": [trigger.value for trigger in triggers],
        "details": list(details),
    }
    digest = sha256(canonical_json_bytes(material)).hexdigest()[:16]
    stamp = evaluated_at_utc.strftime("%Y%m%dT%H%M%SZ")
    return f"WATCH_{stamp}_{digest}"


def evaluate_watch(
    plan: SessionPlan,
    market: MarketSnapshot,
    account: AccountSnapshot,
    *,
    evaluated_at_utc: datetime,
    previous_market: MarketSnapshot | None = None,
    previous_account: AccountSnapshot | None = None,
    config: WatcherConfig | None = None,
) -> WatchDecision:
    """Run the cheap scan.  An empty trigger set is an explicit sleep decision."""

    require_utc(evaluated_at_utc, "evaluated_at_utc")
    thresholds = config or WatcherConfig()
    found: dict[WatchTrigger, list[str]] = {}
    quote_by_symbol = {quote.symbol: quote for quote in market.quotes}
    prior_quote_by_symbol = (
        {quote.symbol: quote for quote in previous_market.quotes}
        if previous_market is not None
        else {}
    )
    watched_symbols = set(plan.constraints.allowed_symbols)
    watched_symbols.update(position.symbol for position in account.positions)

    if not market.connected or not account.terminal_connected:
        disconnected = []
        if not market.connected:
            disconnected.append("market source")
        if not account.terminal_connected:
            disconnected.append("terminal account")
        _append_detail(
            found,
            WatchTrigger.DISCONNECTED,
            f"disconnected: {', '.join(disconnected)}",
        )

    market_age = (evaluated_at_utc - market.captured_at_utc).total_seconds()
    account_age = (evaluated_at_utc - account.captured_at_utc).total_seconds()
    if market_age > thresholds.quote_ttl_seconds:
        _append_detail(
            found,
            WatchTrigger.STALE_MARKET,
            f"market snapshot age {market_age:.1f}s exceeds {thresholds.quote_ttl_seconds}s",
        )
    elif market_age < -thresholds.future_timestamp_tolerance_seconds:
        _append_detail(
            found,
            WatchTrigger.STALE_MARKET,
            "market snapshot timestamp is in the future",
        )
    if account_age > thresholds.account_ttl_seconds:
        _append_detail(
            found,
            WatchTrigger.STALE_MARKET,
            f"account snapshot age {account_age:.1f}s exceeds {thresholds.account_ttl_seconds}s",
        )
    elif account_age < -thresholds.future_timestamp_tolerance_seconds:
        _append_detail(
            found,
            WatchTrigger.STALE_MARKET,
            "account snapshot timestamp is in the future",
        )

    for symbol in sorted(watched_symbols):
        quote = quote_by_symbol.get(symbol)
        if quote is None:
            _append_detail(found, WatchTrigger.STALE_MARKET, f"missing quote for {symbol}")
            continue
        quote_age = (evaluated_at_utc - quote.asof_utc).total_seconds()
        if quote_age > thresholds.quote_ttl_seconds:
            _append_detail(
                found,
                WatchTrigger.STALE_MARKET,
                f"{symbol} quote age {quote_age:.1f}s exceeds {thresholds.quote_ttl_seconds}s",
            )
        elif quote_age < -thresholds.future_timestamp_tolerance_seconds:
            _append_detail(
                found,
                WatchTrigger.STALE_MARKET,
                f"{symbol} quote timestamp is in the future",
            )

    for zone in plan.key_zones:
        quote = quote_by_symbol.get(zone.symbol)
        if quote is None:
            continue
        buffer_price = thresholds.zone_buffer_points * quote.point
        overlaps = quote.ask >= zone.lower - buffer_price and quote.bid <= zone.upper + buffer_price
        prior_quote = prior_quote_by_symbol.get(zone.symbol)
        prior_overlaps = (
            prior_quote is not None
            and prior_quote.ask >= zone.lower - buffer_price
            and prior_quote.bid <= zone.upper + buffer_price
        )
        if overlaps and not prior_overlaps:
            _append_detail(
                found,
                WatchTrigger.ZONE_REACHED,
                f"{zone.symbol} reached zone {zone.zone_id} [{zone.lower}, {zone.upper}]",
            )

    prior_structural_ids = (
        {event.event_id for event in previous_market.structural_events}
        if previous_market is not None
        else set()
    )
    for event in market.structural_events:
        if event.symbol not in watched_symbols:
            continue
        if event.event_id in prior_structural_ids:
            continue
        if event.event_type == "ZONE_TOUCH":
            _append_detail(
                found,
                WatchTrigger.ZONE_REACHED,
                f"explicit zone event {event.event_id}: {event.details}",
            )
        elif event.event_type == "EVENT_RELEASE":
            _append_detail(
                found,
                WatchTrigger.ECONOMIC_RELEASED,
                f"explicit release event {event.event_id}: {event.details}",
            )
        else:
            _append_detail(
                found,
                WatchTrigger.STRUCTURE_CHANGED,
                f"explicit {event.event_type} event {event.event_id}: {event.details}",
            )

    for symbol in sorted(watched_symbols):
        quote = quote_by_symbol.get(symbol)
        if quote is None:
            continue
        limit = thresholds.spread_limits_points.get(symbol)
        if limit is not None and quote.spread_points > limit:
            _append_detail(
                found,
                WatchTrigger.SPREAD_ABNORMAL,
                f"{symbol} spread {quote.spread_points:g} exceeds limit {limit:g}",
            )
            continue
        prior_quote = prior_quote_by_symbol.get(symbol)
        if (
            prior_quote is not None
            and prior_quote.spread_points > 0
            and quote.spread_points
            >= prior_quote.spread_points * thresholds.spread_increase_ratio
        ):
            _append_detail(
                found,
                WatchTrigger.SPREAD_ABNORMAL,
                f"{symbol} spread increased from {prior_quote.spread_points:g} "
                f"to {quote.spread_points:g}",
            )

    if previous_account is not None and _positions(previous_account) != _positions(account):
        _append_detail(
            found,
            WatchTrigger.POSITION_CHANGED,
            "open position set or protection changed",
        )
    unexpected_symbols = sorted(
        {position.symbol for position in account.positions}
        - set(plan.constraints.allowed_symbols)
    )
    if unexpected_symbols:
        _append_detail(
            found,
            WatchTrigger.POSITION_CHANGED,
            f"open exposure outside session plan: {', '.join(unexpected_symbols)}",
        )

    for position in account.positions:
        quote = quote_by_symbol.get(position.symbol)
        point = quote.point if quote is not None else None
        if point is None:
            continue
        price = position.current_price
        buffer_price = thresholds.near_sl_tp_points * point
        if position.stop_loss <= 0:
            _append_detail(
                found,
                WatchTrigger.SL_TP_NEAR,
                f"position {position.ticket} has no stop loss",
            )
        levels = (("SL", position.stop_loss), ("TP", position.take_profit))
        for label, level in levels:
            if level <= 0:
                continue
            if position.direction.value == "LONG":
                is_near_or_crossed = (
                    price <= level + buffer_price
                    if label == "SL"
                    else price >= level - buffer_price
                )
            else:
                is_near_or_crossed = (
                    price >= level - buffer_price
                    if label == "SL"
                    else price <= level + buffer_price
                )
            if is_near_or_crossed:
                _append_detail(
                    found,
                    WatchTrigger.SL_TP_NEAR,
                    f"position {position.ticket} {label} is within "
                    f"{thresholds.near_sl_tp_points:g} points",
                )

    prior_calendar = (
        {event.event_id: event for event in previous_market.calendar}
        if previous_market is not None
        else {}
    )
    for event in _unique_events(plan, market):
        if event.importance != Importance.HIGH:
            continue
        seconds_to_event = (event.event_time_utc - evaluated_at_utc).total_seconds()
        release_age_seconds = -seconds_to_event
        prior_event = prior_calendar.get(event.event_id)
        newly_released = prior_event is None or not prior_event.actual_released
        release_is_current = (
            prior_event is not None and not prior_event.actual_released
        ) or (
            prior_event is None
            and 0 <= release_age_seconds <= thresholds.high_impact_news_horizon_minutes * 60
        )
        if event.actual_released and newly_released and release_is_current:
            _append_detail(
                found,
                WatchTrigger.ECONOMIC_RELEASED,
                f"high-impact event released: {event.event_id} {event.title}",
            )
        elif 0 <= seconds_to_event <= thresholds.high_impact_news_horizon_minutes * 60:
            _append_detail(
                found,
                WatchTrigger.HIGH_IMPACT_NEWS_NEAR,
                f"high-impact event {event.event_id} in {seconds_to_event / 60:.1f} minutes",
            )

    if previous_account is not None:
        changed: list[str] = []
        risk_fields = (
            "drawdown_pct",
            "daily_loss_pct",
            "weekly_loss_pct",
            "open_risk_pct",
        )
        for field_name in risk_fields:
            before = float(getattr(previous_account, field_name))
            after = float(getattr(account, field_name))
            if abs(after - before) >= thresholds.account_risk_delta_pct - 1e-12:
                changed.append(f"{field_name} {before:g}->{after:g}")
        discrete_fields = ("consecutive_losses", "trades_this_session")
        for field_name in discrete_fields:
            before = getattr(previous_account, field_name)
            after = getattr(account, field_name)
            if before != after:
                changed.append(f"{field_name} {before}->{after}")
        permission_fields = ("terminal_trade_allowed", "expert_trading_allowed")
        for field_name in permission_fields:
            if getattr(previous_account, field_name) != getattr(account, field_name):
                changed.append(f"{field_name} changed")
        identity_fields = (
            "account_fingerprint",
            "server",
            "trade_mode",
            "currency",
            "risk_metrics_complete",
            "risk_metrics_source",
        )
        for field_name in identity_fields:
            before = getattr(previous_account, field_name)
            after = getattr(account, field_name)
            if before != after:
                before_value = getattr(before, "value", before)
                after_value = getattr(after, "value", after)
                changed.append(f"{field_name} {before_value}->{after_value}")
        if changed:
            _append_detail(found, WatchTrigger.ACCOUNT_RISK_CHANGED, "; ".join(changed))

    trigger_order = tuple(trigger for trigger in WatchTrigger if trigger in found)
    details = tuple(" | ".join(found[trigger]) for trigger in trigger_order)
    return WatchDecision(
        decision_id=_decision_id(
            evaluated_at_utc,
            plan,
            market,
            account,
            trigger_order,
            details,
        ),
        created_at_utc=evaluated_at_utc,
        invoke_market_agent=bool(trigger_order),
        triggers=trigger_order,
        details=details,
    )


class DeterministicWatcher:
    """Small injectable wrapper for orchestration code."""

    def __init__(self, config: WatcherConfig | None = None) -> None:
        self.config = config or WatcherConfig()

    def evaluate(
        self,
        plan: SessionPlan,
        market: MarketSnapshot,
        account: AccountSnapshot,
        *,
        evaluated_at_utc: datetime,
        previous_market: MarketSnapshot | None = None,
        previous_account: AccountSnapshot | None = None,
    ) -> WatchDecision:
        return evaluate_watch(
            plan,
            market,
            account,
            evaluated_at_utc=evaluated_at_utc,
            previous_market=previous_market,
            previous_account=previous_account,
            config=self.config,
        )


MarketWatcher = DeterministicWatcher
scan_market = evaluate_watch


__all__ = [
    "DeterministicWatcher",
    "MarketWatcher",
    "WatcherConfig",
    "evaluate_watch",
    "scan_market",
]
