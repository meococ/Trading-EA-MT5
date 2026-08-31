from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError


ALPHA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.models import (  # noqa: E402
    Bias,
    ExecutionAttempt,
    RuntimeMode,
    Scenario,
    SessionConstraints,
    SessionName,
    SessionPlan,
    Stance,
)


NOW = datetime(2026, 8, 27, 6, 0, tzinfo=timezone.utc)
HASH = "a" * 64


def plan_payload(version: int = 1) -> dict:
    payload = {
        "plan_id": "SESSION_PLAN_2026-08-27_LONDON",
        "version": version,
        "session_date": date(2026, 8, 27),
        "session": SessionName.LONDON,
        "created_at_utc": NOW,
        "market_asof_utc": NOW - timedelta(minutes=1),
        "created_by": "planner-test",
        "input_sha256": HASH,
        "regime": "range",
        "biases": (Bias(symbol="EURUSD", stance=Stance.NEUTRAL, summary="No directional edge"),),
        "scenarios": (
            Scenario(
                scenario_id="A",
                name="pullback",
                trigger="M15 closes above zone",
                action="candidate long may be proposed",
                invalidation="M15 closes below invalidation",
            ),
        ),
        "global_invalidation": "High-impact release invalidates the plan",
        "constraints": SessionConstraints(
            max_risk_pct_per_trade=0.25,
            max_trades=1,
            news_blackout_before_minutes=15,
            news_blackout_after_minutes=15,
            allowed_symbols=("EURUSD",),
            correlation_note="Do not stack full-risk EURUSD and GBPUSD",
        ),
    }
    if version > 1:
        payload["supersedes_sha256"] = "b" * 64
        payload["revision_reason"] = "Material regime change"
    return payload


def test_session_plan_revision_contract_is_explicit() -> None:
    v1 = SessionPlan(**plan_payload())
    assert v1.version == 1

    v2 = SessionPlan(**plan_payload(2))
    assert v2.supersedes_sha256 == "b" * 64

    invalid = plan_payload(2)
    invalid.pop("revision_reason")
    with pytest.raises(ValidationError, match=r"v2\+ requires"):
        SessionPlan(**invalid)


def test_v1_cannot_claim_it_supersedes_a_hidden_plan() -> None:
    invalid = plan_payload()
    invalid["supersedes_sha256"] = "b" * 64
    with pytest.raises(ValidationError, match="v1 cannot supersede"):
        SessionPlan(**invalid)


def test_shadow_execution_attempt_cannot_claim_an_order_was_sent() -> None:
    ref = {"schema_version": "x.v1", "path": "x.json", "sha256": HASH}
    with pytest.raises(ValidationError, match="SHADOW can never record sent=true"):
        ExecutionAttempt(
            attempt_id="ATTEMPT-1",
            created_at_utc=NOW,
            intent=ref,
            risk_decision=ref,
            runtime_mode=RuntimeMode.SHADOW,
            request_sha256=HASH,
            sent=True,
            status="SENT",
            detail="impossible",
        )
