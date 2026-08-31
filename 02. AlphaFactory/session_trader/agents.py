from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .models import (
    AccountSnapshot,
    ArtifactRef,
    Candidate,
    Critique,
    Decision,
    MarketSnapshot,
    SessionPlan,
)


class AgentError(RuntimeError):
    """Base class for fail-closed agent adapter errors."""


class AgentUnavailableError(AgentError):
    pass


class AgentOutputError(AgentError):
    pass


def _agent_account_view(account: AccountSnapshot) -> dict[str, Any]:
    """Expose only risk-relevant account fields to a potentially remote model."""

    return {
        "snapshot_id": account.snapshot_id,
        "captured_at_utc": account.captured_at_utc.isoformat(),
        "trade_mode": account.trade_mode.value,
        "drawdown_pct": account.drawdown_pct,
        "daily_loss_pct": account.daily_loss_pct,
        "weekly_loss_pct": account.weekly_loss_pct,
        "open_risk_pct": account.open_risk_pct,
        "risk_metrics_complete": account.risk_metrics_complete,
        "trades_this_session": account.trades_this_session,
        "consecutive_losses": account.consecutive_losses,
        "terminal_connected": account.terminal_connected,
        "terminal_trade_allowed": account.terminal_trade_allowed,
        "expert_trading_allowed": account.expert_trading_allowed,
        "positions": [
            {
                "symbol": position.symbol,
                "direction": position.direction.value,
                "current_price": position.current_price,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit,
                "risk_pct": position.risk_pct,
            }
            for position in account.positions
        ],
    }


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "agent_task.v1"
    task_id: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=80)
    provider_id: str = Field(min_length=1, max_length=120)
    model_id: str = Field(min_length=1, max_length=160)
    created_at_utc: datetime
    instructions: tuple[str, ...] = Field(min_length=1)
    inputs: dict[str, Any]
    output_schema: dict[str, Any]


class ModelAdapter(Protocol):
    provider_id: str
    model_id: str

    def generate_json(self, task: AgentTask) -> dict[str, Any]: ...


class FileOutputAdapter:
    """Offline adapter for human/local-model generated JSON output.

    It never invokes a network model and is useful while the repository's USD 0
    spend constraint remains in force.
    """

    def __init__(self, path: str | Path, *, provider_id: str = "file", model_id: str = "offline") -> None:
        self.path = Path(path)
        self.provider_id = provider_id
        self.model_id = model_id

    def generate_json(self, task: AgentTask) -> dict[str, Any]:
        if not self.path.is_file():
            raise AgentUnavailableError(f"agent output file is unavailable: {self.path}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentOutputError(f"invalid agent output file: {self.path}") from exc
        if not isinstance(payload, dict):
            raise AgentOutputError("agent output must be one JSON object")
        return payload


T = TypeVar("T", bound=BaseModel)


def run_typed_agent(adapter: ModelAdapter, task: AgentTask, output_type: type[T]) -> T:
    if adapter.provider_id != task.provider_id or adapter.model_id != task.model_id:
        raise AgentUnavailableError("agent adapter identity does not match frozen task")
    try:
        payload = adapter.generate_json(task)
        return output_type.model_validate(payload)
    except AgentError:
        raise
    except ValidationError as exc:
        raise AgentOutputError(f"{task.role} output failed schema validation") from exc
    except Exception as exc:  # provider exceptions must never become implicit approval
        raise AgentUnavailableError(f"{task.role} adapter failed") from exc


def _task(
    *,
    task_id: str,
    role: str,
    provider_id: str,
    model_id: str,
    instructions: tuple[str, ...],
    inputs: dict[str, Any],
    output_type: type[BaseModel],
    created_at_utc: datetime | None,
) -> AgentTask:
    return AgentTask(
        task_id=task_id,
        role=role,
        provider_id=provider_id,
        model_id=model_id,
        created_at_utc=created_at_utc or datetime.now(timezone.utc),
        instructions=instructions,
        inputs=inputs,
        output_schema=output_type.model_json_schema(),
    )


def build_session_planner_task(
    *,
    provider_id: str,
    model_id: str,
    session_context: dict[str, Any],
    created_at_utc: datetime | None = None,
) -> AgentTask:
    return _task(
        task_id=str(session_context.get("plan_id") or "SESSION-PLANNER"),
        role="SESSION_PLANNER",
        provider_id=provider_id,
        model_id=model_id,
        instructions=(
            "Create one causal session plan from information available at market_asof_utc.",
            "Do not rewrite a prior version; v2+ must declare the immediate superseded SHA256 and material change reason.",
            "Normalize internal event times to UTC and retain broker server-time evidence.",
            "This output has no order or execution authority.",
        ),
        inputs=session_context,
        output_type=SessionPlan,
        created_at_utc=created_at_utc,
    )


def build_candidate_task(
    plan: SessionPlan,
    market: MarketSnapshot,
    account: AccountSnapshot,
    *,
    plan_ref: ArtifactRef,
    market_snapshot_ref: ArtifactRef,
    account_snapshot_ref: ArtifactRef,
    provider_id: str,
    model_id: str,
    created_at_utc: datetime | None = None,
) -> AgentTask:
    return _task(
        task_id=f"CANDIDATE-{plan.plan_id}-v{plan.version}",
        role="CANDIDATE_TRADER",
        provider_id=provider_id,
        model_id=model_id,
        instructions=(
            "Propose a candidate only when it fits an explicit SessionPlan scenario.",
            "Provide entry condition, invalidation, evidence references, expiry and requested risk; never create an order.",
            "Reject internally when market/account inputs are stale or incomplete rather than inventing facts.",
        ),
        inputs={
            "artifact_refs": {
                "plan": plan_ref.model_dump(mode="json"),
                "market_snapshot": market_snapshot_ref.model_dump(mode="json"),
                "account_snapshot": account_snapshot_ref.model_dump(mode="json"),
            },
            "session_plan": plan.model_dump(mode="json"),
            "market_snapshot": market.model_dump(mode="json"),
            "account_snapshot": _agent_account_view(account),
        },
        output_type=Candidate,
        created_at_utc=created_at_utc,
    )


def build_blind_critic_task(
    plan: SessionPlan,
    market: MarketSnapshot,
    account: AccountSnapshot,
    candidate: Candidate,
    *,
    provider_id: str,
    model_id: str,
    candidate_provider_id: str,
    require_distinct_provider: bool = True,
    created_at_utc: datetime | None = None,
) -> AgentTask:
    if require_distinct_provider and provider_id == candidate_provider_id:
        raise AgentUnavailableError("blind critic must use a distinct provider")
    sanitized_order = {
        "candidate_id": candidate.candidate_id,
        "symbol": candidate.symbol,
        "direction": candidate.direction.value,
        "scenario_id": candidate.scenario_id,
        "entry_min": candidate.entry_min,
        "entry_max": candidate.entry_max,
        "stop_loss": candidate.stop_loss,
        "take_profit": candidate.take_profit,
        "expiry_utc": candidate.expiry_utc.isoformat(),
        "requested_risk_pct": candidate.requested_risk_pct,
    }
    return _task(
        task_id=f"CRITIC-{candidate.candidate_id}",
        role="BLIND_RED_TEAM",
        provider_id=provider_id,
        model_id=model_id,
        instructions=(
            "Find evidence that requires this candidate order to be rejected.",
            "Check plan violation, late entry, news, RR, spread, correlation, regime drift, account risk and stale inputs.",
            "This first pass is blind: candidate reasoning, confidence and narrative are intentionally withheld.",
            "This output has no order or execution authority.",
        ),
        inputs={
            "session_plan": plan.model_dump(mode="json"),
            "raw_market_snapshot": market.model_dump(mode="json"),
            "raw_account_snapshot": _agent_account_view(account),
            "candidate_order": sanitized_order,
        },
        output_type=Critique,
        created_at_utc=created_at_utc,
    )


def build_trade_architect_task(
    plan: SessionPlan,
    market: MarketSnapshot,
    account: AccountSnapshot,
    candidate: Candidate,
    critique: Critique,
    *,
    provider_id: str,
    model_id: str,
    created_at_utc: datetime | None = None,
) -> AgentTask:
    if critique.verdict != Decision.APPROVE:
        raise AgentOutputError("trade architect cannot run after a critic rejection")
    from .models import TradeIntent

    return _task(
        task_id=f"INTENT-{candidate.candidate_id}",
        role="TRADE_ARCHITECT",
        provider_id=provider_id,
        model_id=model_id,
        instructions=(
            "Translate the approved candidate into one precise TradeIntent.",
            "Do not change the SessionPlan scenario, increase risk, extend expiry or send an order.",
            "The deterministic risk gateway is the only component allowed to approve money and volume.",
        ),
        inputs={
            "session_plan": plan.model_dump(mode="json"),
            "market_snapshot": market.model_dump(mode="json"),
            "account_snapshot": _agent_account_view(account),
            "candidate": candidate.model_dump(mode="json"),
            "critique": critique.model_dump(mode="json"),
        },
        output_type=TradeIntent,
        created_at_utc=created_at_utc,
    )
