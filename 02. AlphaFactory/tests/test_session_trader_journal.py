from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.journal import build_journal_report  # noqa: E402


def test_journal_reports_evidence_without_authorizing_strategy_mutation() -> None:
    plan_id = "SESSION_PLAN_2026-08-27_LONDON"
    report = build_journal_report(
        [
            {"event_type": "CANDIDATE_CREATED", "session_plan_id": plan_id, "event_hash": "a" * 64, "payload": {}},
            {
                "event_type": "CANDIDATE_CREATED",
                "session_plan_id": "SESSION_PLAN_2026-08-27_ASIA",
                "event_hash": "f" * 64,
                "payload": {},
            },
            {
                "event_type": "CRITIQUE_CREATED",
                "session_plan_id": plan_id,
                "event_hash": "b" * 64,
                "payload": {"candidate_verdict": "APPROVE", "verdict": "REJECT"},
            },
            {
                "event_type": "RISK_DECISION_CREATED",
                "session_plan_id": plan_id,
                "event_hash": "c" * 64,
                "payload": {"decision": "REJECT", "primary_reason": "spread too wide", "plan_adherent": True},
            },
            {
                "event_type": "RECONCILIATION_CREATED",
                "session_plan_id": plan_id,
                "event_hash": "d" * 64,
                "payload": {"status": "INCIDENT", "slippage_points": 2.0, "plan_adherent": False},
            },
        ],
        session_plan_id=plan_id,
        session_date=date(2026, 8, 27),
        created_at_utc=datetime(2026, 8, 27, 23, 30, tzinfo=timezone.utc),
    )

    assert report.candidates == 1
    assert report.critic_rejections == 1
    assert report.risk_rejections == 1
    assert report.disagreement_events == 1
    assert report.plan_adherence_pct == 50.0
    assert report.largest_issue == "broker reconciliation incident"
    assert report.research_queue[0].live_strategy_mutation_authorized is False


def test_journal_rejects_date_that_disagrees_with_plan_identity() -> None:
    with pytest.raises(ValueError, match="embedded"):
        build_journal_report(
            [],
            session_plan_id="SESSION_PLAN_2026-08-27_LONDON",
            session_date=date(2026, 8, 28),
            created_at_utc=datetime(2026, 8, 28, 0, 0, tzinfo=timezone.utc),
        )
