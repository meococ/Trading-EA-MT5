from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Percent = Annotated[float, Field(ge=0.0, le=100.0)]
PositiveFloat = Annotated[float, Field(gt=0.0)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field_name} must be normalized to UTC")


class RuntimeMode(str, Enum):
    OBSERVE = "OBSERVE"
    SHADOW = "SHADOW"
    DEMO_EXECUTE = "DEMO_EXECUTE"
    LIVE_LOCKED = "LIVE_LOCKED"


class SessionName(str, Enum):
    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Stance(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class TradeMode(str, Enum):
    DEMO = "DEMO"
    CONTEST = "CONTEST"
    REAL = "REAL"
    UNKNOWN = "UNKNOWN"


class Importance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ArtifactRef(FrozenModel):
    schema_version: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")


class Bias(FrozenModel):
    symbol: str = Field(min_length=1)
    stance: Stance
    summary: str = Field(min_length=1, max_length=500)


class KeyZone(FrozenModel):
    zone_id: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1)
    lower: float
    upper: float
    purpose: Literal["ENTRY", "REACTION", "INVALIDATION", "NO_TRADE"]

    @model_validator(mode="after")
    def validate_bounds(self) -> "KeyZone":
        if self.upper < self.lower:
            raise ValueError("zone upper must be greater than or equal to lower")
        return self


class Scenario(FrozenModel):
    scenario_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    trigger: str = Field(min_length=1, max_length=600)
    action: str = Field(min_length=1, max_length=600)
    invalidation: str = Field(min_length=1, max_length=600)


class CalendarEvent(FrozenModel):
    event_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=300)
    currency: str = Field(min_length=3, max_length=8)
    importance: Importance
    event_time_utc: datetime
    event_time_server: str = Field(min_length=1, max_length=64)
    server_utc_offset_minutes: int = Field(ge=-14 * 60, le=14 * 60)
    source: str = Field(min_length=1, max_length=160)
    actual_released: bool = False

    @model_validator(mode="after")
    def validate_time(self) -> "CalendarEvent":
        require_utc(self.event_time_utc, "event_time_utc")
        return self


class SessionConstraints(FrozenModel):
    max_risk_pct_per_trade: Percent
    max_trades: int = Field(ge=0, le=100)
    news_blackout_before_minutes: int = Field(ge=0, le=1440)
    news_blackout_after_minutes: int = Field(ge=0, le=1440)
    allowed_symbols: tuple[str, ...] = Field(min_length=1)
    correlation_note: str = Field(min_length=1, max_length=600)


class SessionPlan(FrozenModel):
    schema_version: Literal["session_plan.v1"] = "session_plan.v1"
    plan_id: str = Field(pattern=r"^SESSION_PLAN_\d{4}-\d{2}-\d{2}_(ASIA|LONDON|NEW_YORK)$")
    version: int = Field(ge=1)
    session_date: date
    session: SessionName
    created_at_utc: datetime
    market_asof_utc: datetime
    created_by: str = Field(min_length=1, max_length=160)
    input_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    supersedes_sha256: str | None = Field(default=None, pattern=r"^[A-Fa-f0-9]{64}$")
    revision_reason: str | None = Field(default=None, max_length=800)
    regime: str = Field(min_length=1, max_length=160)
    biases: tuple[Bias, ...] = Field(min_length=1)
    key_zones: tuple[KeyZone, ...] = Field(default_factory=tuple)
    scenarios: tuple[Scenario, ...] = Field(min_length=1)
    global_invalidation: str = Field(min_length=1, max_length=800)
    calendar: tuple[CalendarEvent, ...] = Field(default_factory=tuple)
    constraints: SessionConstraints

    @model_validator(mode="after")
    def validate_revision_and_identity(self) -> "SessionPlan":
        require_utc(self.created_at_utc, "created_at_utc")
        require_utc(self.market_asof_utc, "market_asof_utc")
        expected_id = f"SESSION_PLAN_{self.session_date.isoformat()}_{self.session.value}"
        if self.plan_id != expected_id:
            raise ValueError(f"plan_id must be {expected_id}")
        if self.version == 1:
            if self.supersedes_sha256 is not None or self.revision_reason is not None:
                raise ValueError("v1 cannot supersede another plan or carry a revision_reason")
        elif self.supersedes_sha256 is None or not self.revision_reason:
            raise ValueError("v2+ requires supersedes_sha256 and revision_reason")
        if self.market_asof_utc > self.created_at_utc:
            raise ValueError("market_asof_utc cannot be later than created_at_utc")
        return self


class QuoteSnapshot(FrozenModel):
    symbol: str = Field(min_length=1)
    bid: PositiveFloat
    ask: PositiveFloat
    point: PositiveFloat
    spread_points: Annotated[float, Field(ge=0.0)]
    tick_size: PositiveFloat
    tick_value_loss: PositiveFloat
    volume_min: PositiveFloat
    volume_max: PositiveFloat
    volume_step: PositiveFloat
    stops_level_points: Annotated[float, Field(ge=0.0)] = 0.0
    asof_utc: datetime
    server_time: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_quote(self) -> "QuoteSnapshot":
        require_utc(self.asof_utc, "asof_utc")
        if self.ask < self.bid:
            raise ValueError("ask cannot be lower than bid")
        calculated = (self.ask - self.bid) / self.point
        if abs(calculated - self.spread_points) > max(0.25, calculated * 0.02):
            raise ValueError("spread_points does not reconcile with bid/ask/point")
        if self.volume_max < self.volume_min:
            raise ValueError("volume_max must be >= volume_min")
        return self


class StructuralEvent(FrozenModel):
    event_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1)
    event_type: Literal["ZONE_TOUCH", "STRUCTURE_BREAK", "EVENT_RELEASE", "PRICE_ALERT"]
    observed_at_utc: datetime
    details: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_time(self) -> "StructuralEvent":
        require_utc(self.observed_at_utc, "observed_at_utc")
        return self


class MarketSnapshot(FrozenModel):
    schema_version: Literal["market_snapshot.v1"] = "market_snapshot.v1"
    snapshot_id: str = Field(min_length=1, max_length=128)
    captured_at_utc: datetime
    source: str = Field(min_length=1, max_length=160)
    terminal_path_sha256: str | None = Field(default=None, pattern=r"^[A-Fa-f0-9]{64}$")
    connected: bool
    server_utc_offset_minutes: int | None = Field(default=None, ge=-14 * 60, le=14 * 60)
    time_mapping_verified: bool = False
    time_mapping_source: str = Field(default="UNAVAILABLE", min_length=1, max_length=240)
    calendar_available: bool = False
    calendar_asof_utc: datetime | None = None
    quotes: tuple[QuoteSnapshot, ...] = Field(default_factory=tuple)
    structural_events: tuple[StructuralEvent, ...] = Field(default_factory=tuple)
    calendar: tuple[CalendarEvent, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_snapshot(self) -> "MarketSnapshot":
        require_utc(self.captured_at_utc, "captured_at_utc")
        symbols = [quote.symbol for quote in self.quotes]
        if len(symbols) != len(set(symbols)):
            raise ValueError("market snapshot contains duplicate symbols")
        if self.calendar_asof_utc is not None:
            require_utc(self.calendar_asof_utc, "calendar_asof_utc")
        if self.calendar_available and self.calendar_asof_utc is None:
            raise ValueError("available calendar requires calendar_asof_utc")
        if self.time_mapping_verified and self.server_utc_offset_minutes is None:
            raise ValueError("verified time mapping requires server_utc_offset_minutes")
        return self


class PositionSnapshot(FrozenModel):
    ticket: int = Field(gt=0)
    symbol: str = Field(min_length=1)
    direction: Direction
    volume: PositiveFloat
    open_price: PositiveFloat
    current_price: PositiveFloat
    stop_loss: float = Field(ge=0.0)
    take_profit: float = Field(ge=0.0)
    risk_pct: Percent
    magic: int = Field(ge=0)
    comment: str = Field(default="", max_length=64)


class RiskState(FrozenModel):
    """Deterministic session counters bound to one account and ledger head.

    This is evidence, not a self-issued ``verified`` flag.  A collector may only
    consume it when the account, SessionPlan, ledger head and freshness all match.
    """

    schema_version: Literal["risk_state.v1"] = "risk_state.v1"
    state_id: str = Field(min_length=1, max_length=128)
    asof_utc: datetime
    account_fingerprint: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    session_plan_id: str = Field(
        pattern=r"^SESSION_PLAN_\d{4}-\d{2}-\d{2}_(ASIA|LONDON|NEW_YORK)$"
    )
    ledger_head_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    deals_window_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    daily_loss_pct: Percent
    weekly_loss_pct: Percent
    trades_this_session: int = Field(ge=0)
    consecutive_losses: int = Field(ge=0)
    source: Literal["MQL5_DEAL_LEDGER_RECONCILIATION"]

    @model_validator(mode="after")
    def validate_binding(self) -> "RiskState":
        require_utc(self.asof_utc, "asof_utc")
        if self.ledger_head_sha256 == "0" * 64:
            raise ValueError("risk state must bind a non-empty verified ledger head")
        return self


class AccountSnapshot(FrozenModel):
    schema_version: Literal["account_snapshot.v1"] = "account_snapshot.v1"
    snapshot_id: str = Field(min_length=1, max_length=128)
    captured_at_utc: datetime
    account_fingerprint: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    server: str = Field(min_length=1, max_length=160)
    trade_mode: TradeMode
    currency: str = Field(min_length=3, max_length=8)
    balance: Annotated[float, Field(ge=0.0)]
    equity: Annotated[float, Field(ge=0.0)]
    margin_free: Annotated[float, Field(ge=0.0)]
    drawdown_pct: Percent
    daily_loss_pct: Percent
    weekly_loss_pct: Percent
    open_risk_pct: Percent
    risk_metrics_complete: bool
    risk_metrics_source: str = Field(min_length=1, max_length=240)
    risk_state_sha256: str | None = Field(default=None, pattern=r"^[A-Fa-f0-9]{64}$")
    risk_state_asof_utc: datetime | None = None
    risk_state_session_plan_id: str | None = Field(
        default=None,
        pattern=r"^SESSION_PLAN_\d{4}-\d{2}-\d{2}_(ASIA|LONDON|NEW_YORK)$",
    )
    risk_state_ledger_head_sha256: str | None = Field(
        default=None, pattern=r"^[A-Fa-f0-9]{64}$"
    )
    trades_this_session: int = Field(ge=0)
    consecutive_losses: int = Field(ge=0)
    terminal_connected: bool
    terminal_trade_allowed: bool
    expert_trading_allowed: bool
    positions: tuple[PositionSnapshot, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_time(self) -> "AccountSnapshot":
        require_utc(self.captured_at_utc, "captured_at_utc")
        bindings = (
            self.risk_state_sha256,
            self.risk_state_asof_utc,
            self.risk_state_session_plan_id,
            self.risk_state_ledger_head_sha256,
        )
        if any(value is not None for value in bindings) and any(
            value is None for value in bindings
        ):
            raise ValueError("RiskState audit bindings must be all present or all absent")
        if not self.risk_metrics_complete and any(value is not None for value in bindings):
            raise ValueError("incomplete risk metrics cannot claim RiskState bindings")
        if self.risk_state_asof_utc is not None:
            require_utc(self.risk_state_asof_utc, "risk_state_asof_utc")
        return self


class Candidate(FrozenModel):
    schema_version: Literal["candidate.v1"] = "candidate.v1"
    candidate_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    plan: ArtifactRef
    market_snapshot: ArtifactRef
    account_snapshot: ArtifactRef
    symbol: str = Field(min_length=1)
    direction: Direction
    scenario_id: str = Field(min_length=1, max_length=64)
    entry_condition: str = Field(min_length=1, max_length=600)
    entry_min: PositiveFloat
    entry_max: PositiveFloat
    stop_loss: PositiveFloat
    take_profit: PositiveFloat
    expiry_utc: datetime
    requested_risk_pct: Percent
    expected_r: Annotated[float, Field(gt=0.0)]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_candidate(self) -> "Candidate":
        require_utc(self.created_at_utc, "created_at_utc")
        require_utc(self.expiry_utc, "expiry_utc")
        if self.entry_max < self.entry_min:
            raise ValueError("entry_max must be >= entry_min")
        if self.expiry_utc <= self.created_at_utc:
            raise ValueError("candidate must expire after creation")
        return self


class Critique(FrozenModel):
    schema_version: Literal["critique.v1"] = "critique.v1"
    critique_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    plan: ArtifactRef
    market_snapshot: ArtifactRef
    account_snapshot: ArtifactRef
    candidate: ArtifactRef
    blind_first_pass: Literal[True] = True
    verdict: Decision
    reject_reasons: tuple[str, ...] = Field(default_factory=tuple)
    checks: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_critique(self) -> "Critique":
        require_utc(self.created_at_utc, "created_at_utc")
        if self.verdict == Decision.REJECT and not self.reject_reasons:
            raise ValueError("rejected critique requires at least one reason")
        if self.verdict == Decision.APPROVE and self.reject_reasons:
            raise ValueError("approved critique cannot contain reject reasons")
        return self


class TradeIntent(FrozenModel):
    schema_version: Literal["trade_intent.v1"] = "trade_intent.v1"
    intent_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    plan: ArtifactRef
    market_snapshot: ArtifactRef
    account_snapshot: ArtifactRef
    candidate: ArtifactRef
    critique: ArtifactRef
    symbol: str = Field(min_length=1)
    direction: Direction
    scenario_id: str = Field(min_length=1, max_length=64)
    order_type: Literal["MARKET"] = "MARKET"
    entry_min: PositiveFloat
    entry_max: PositiveFloat
    stop_loss: PositiveFloat
    take_profit: PositiveFloat
    expiry_utc: datetime
    requested_risk_pct: Percent
    max_spread_points: PositiveFloat
    architect_summary: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def validate_intent(self) -> "TradeIntent":
        require_utc(self.created_at_utc, "created_at_utc")
        require_utc(self.expiry_utc, "expiry_utc")
        if self.entry_max < self.entry_min:
            raise ValueError("entry_max must be >= entry_min")
        if self.expiry_utc <= self.created_at_utc:
            raise ValueError("intent must expire after creation")
        return self


class SymbolRiskPolicy(FrozenModel):
    max_risk_pct_per_trade: Percent
    max_spread_points: PositiveFloat
    max_slippage_points: Annotated[int, Field(ge=0, le=100000)]
    min_rr: Annotated[float, Field(gt=0.0)]
    max_open_risk_pct: Percent


class CorrelationGroup(FrozenModel):
    group_id: str = Field(min_length=1, max_length=64)
    symbols: tuple[str, ...] = Field(min_length=2)
    max_group_risk_pct: Percent


class RiskPolicy(FrozenModel):
    schema_version: Literal["risk_policy.v1"] = "risk_policy.v1"
    policy_id: str = Field(min_length=1, max_length=128)
    runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    kill_switch: bool = True
    demo_execution_authorized: bool = False
    live_execution_authorized: Literal[False] = False
    allowed_account_fingerprints: tuple[str, ...] = Field(default_factory=tuple)
    symbols: dict[str, SymbolRiskPolicy] = Field(default_factory=dict)
    max_daily_loss_pct: Percent
    max_weekly_loss_pct: Percent
    max_drawdown_pct: Percent
    max_aggregate_open_risk_pct: Percent
    max_consecutive_losses: int = Field(ge=0)
    max_trades_per_session: int = Field(ge=0)
    quote_ttl_seconds: int = Field(gt=0, le=3600)
    account_ttl_seconds: int = Field(default=30, gt=0, le=3600)
    calendar_ttl_seconds: int = Field(default=3600, gt=0, le=86400)
    news_blackout_before_minutes: int = Field(ge=0, le=1440)
    news_blackout_after_minutes: int = Field(ge=0, le=1440)
    magic: int = Field(gt=0, le=2147483647)
    correlation_groups: tuple[CorrelationGroup, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_authority(self) -> "RiskPolicy":
        if self.runtime_mode == RuntimeMode.DEMO_EXECUTE:
            if not self.demo_execution_authorized:
                raise ValueError("DEMO_EXECUTE requires demo_execution_authorized=true")
            if not self.allowed_account_fingerprints:
                raise ValueError("DEMO_EXECUTE requires an account allowlist")
        return self


class RiskDecision(FrozenModel):
    schema_version: Literal["risk_decision.v1"] = "risk_decision.v1"
    decision_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    intent: ArtifactRef
    policy: ArtifactRef
    market_snapshot: ArtifactRef
    account_snapshot: ArtifactRef
    decision: Decision
    reasons: tuple[str, ...] = Field(min_length=1)
    approved_risk_pct: Percent = 0.0
    entry_price: float = Field(ge=0.0)
    volume: float = Field(ge=0.0)
    estimated_rr: float = Field(ge=0.0)
    idempotency_key: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_decision(self) -> "RiskDecision":
        require_utc(self.created_at_utc, "created_at_utc")
        if self.decision == Decision.REJECT and (self.approved_risk_pct or self.volume):
            raise ValueError("rejected decision cannot authorize risk or volume")
        if self.decision == Decision.APPROVE and (self.approved_risk_pct <= 0 or self.volume <= 0):
            raise ValueError("approved decision requires positive risk and volume")
        return self


class ExecutionAttempt(FrozenModel):
    schema_version: Literal["execution_attempt.v1"] = "execution_attempt.v1"
    attempt_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    intent: ArtifactRef
    risk_decision: ArtifactRef
    runtime_mode: RuntimeMode
    request_sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    order_check_retcode: int | None = None
    order_send_retcode: int | None = None
    sent: bool
    broker_order: int | None = None
    broker_deal: int | None = None
    status: Literal["DRY_RUN", "CHECK_REJECTED", "SENT", "SEND_REJECTED", "INCIDENT"]
    detail: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_attempt(self) -> "ExecutionAttempt":
        require_utc(self.created_at_utc, "created_at_utc")
        if self.runtime_mode in {RuntimeMode.OBSERVE, RuntimeMode.SHADOW, RuntimeMode.LIVE_LOCKED} and self.sent:
            raise ValueError(f"{self.runtime_mode.value} can never record sent=true")
        return self


class Reconciliation(FrozenModel):
    schema_version: Literal["reconciliation.v1"] = "reconciliation.v1"
    reconciliation_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    execution_attempt: ArtifactRef
    status: Literal["DRY_RUN", "MATCHED", "REJECTED", "AMBIGUOUS", "INCIDENT"]
    broker_order: int | None = None
    broker_deal: int | None = None
    broker_position: int | None = None
    intended_volume: float = Field(ge=0.0)
    actual_volume: float = Field(ge=0.0)
    intended_price: float = Field(ge=0.0)
    actual_price: float = Field(ge=0.0)
    slippage_points: float | None = None
    mismatches: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_reconciliation(self) -> "Reconciliation":
        require_utc(self.created_at_utc, "created_at_utc")
        if self.status == "MATCHED" and self.mismatches:
            raise ValueError("matched reconciliation cannot have mismatches")
        if self.status in {"AMBIGUOUS", "INCIDENT"} and not self.mismatches:
            raise ValueError("ambiguous/incident reconciliation requires mismatch evidence")
        return self


class WatchTrigger(str, Enum):
    ZONE_REACHED = "ZONE_REACHED"
    STRUCTURE_CHANGED = "STRUCTURE_CHANGED"
    SPREAD_ABNORMAL = "SPREAD_ABNORMAL"
    POSITION_CHANGED = "POSITION_CHANGED"
    SL_TP_NEAR = "SL_TP_NEAR"
    HIGH_IMPACT_NEWS_NEAR = "HIGH_IMPACT_NEWS_NEAR"
    ECONOMIC_RELEASED = "ECONOMIC_RELEASED"
    ACCOUNT_RISK_CHANGED = "ACCOUNT_RISK_CHANGED"
    STALE_MARKET = "STALE_MARKET"
    DISCONNECTED = "DISCONNECTED"


class WatchDecision(FrozenModel):
    schema_version: Literal["watch_decision.v1"] = "watch_decision.v1"
    decision_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    invoke_market_agent: bool
    triggers: tuple[WatchTrigger, ...] = Field(default_factory=tuple)
    details: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_watch_decision(self) -> "WatchDecision":
        require_utc(self.created_at_utc, "created_at_utc")
        if self.invoke_market_agent != bool(self.triggers):
            raise ValueError("invoke_market_agent must equal bool(triggers)")
        if len(self.details) != len(self.triggers):
            raise ValueError("watch trigger details must align one-to-one with triggers")
        return self


class ResearchSuggestion(FrozenModel):
    suggestion_id: str = Field(min_length=1, max_length=128)
    created_at_utc: datetime
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    problem: str = Field(min_length=1, max_length=600)
    proposed_offline_test: str = Field(min_length=1, max_length=1000)
    live_strategy_mutation_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_time(self) -> "ResearchSuggestion":
        require_utc(self.created_at_utc, "created_at_utc")
        return self


class JournalReport(FrozenModel):
    schema_version: Literal["journal_report.v1"] = "journal_report.v1"
    report_id: str = Field(min_length=1, max_length=128)
    session_plan_id: str = Field(
        pattern=r"^SESSION_PLAN_\d{4}-\d{2}-\d{2}_(ASIA|LONDON|NEW_YORK)$"
    )
    session_date: date
    created_at_utc: datetime
    candidates: int = Field(ge=0)
    critic_rejections: int = Field(ge=0)
    risk_rejections: int = Field(ge=0)
    executed: int = Field(ge=0)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    pnl_r: float
    plan_adherence_pct: Percent
    disagreement_events: int = Field(ge=0)
    average_slippage_points: float = Field(ge=0.0)
    largest_issue: str = Field(min_length=1, max_length=600)
    research_queue: tuple[ResearchSuggestion, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_report(self) -> "JournalReport":
        require_utc(self.created_at_utc, "created_at_utc")
        embedded_date = self.session_plan_id.split("_")[2]
        if embedded_date != self.session_date.isoformat():
            raise ValueError("session_date must match the date embedded in session_plan_id")
        if self.wins + self.losses > self.executed:
            raise ValueError("wins + losses cannot exceed executed trades")
        return self
