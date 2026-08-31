from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

from .models import JournalReport, ResearchSuggestion


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    value = event.get("payload", event)
    return value if isinstance(value, Mapping) else {}


def _event_type(event: Mapping[str, Any]) -> str:
    return str(event.get("event_type") or event.get("type") or "").upper()


def _session_plan_id(event: Mapping[str, Any]) -> str:
    direct = event.get("session_plan_id")
    if isinstance(direct, str):
        return direct
    payload = _payload(event)
    nested = payload.get("session_plan_id")
    return nested if isinstance(nested, str) else ""


def _suggestion_id(problem: str, refs: tuple[str, ...]) -> str:
    body = json.dumps({"problem": problem, "refs": refs}, sort_keys=True, separators=(",", ":"))
    return "RESEARCH-" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:16].upper()


def build_journal_report(
    events: Iterable[Mapping[str, Any]],
    *,
    session_plan_id: str,
    session_date: date,
    created_at_utc: datetime | None = None,
) -> JournalReport:
    """Summarize immutable event rows without modifying a live strategy."""

    created = created_at_utc or datetime.now(timezone.utc)
    rows = [event for event in events if _session_plan_id(event) == session_plan_id]
    candidates = 0
    critic_rejections = 0
    risk_rejections = 0
    executed = 0
    wins = 0
    losses = 0
    pnl_r = 0.0
    adherence_total = 0
    adherence_passed = 0
    disagreements = 0
    slippages: list[float] = []
    issues: list[tuple[int, str, str]] = []

    for event in rows:
        kind = _event_type(event)
        payload = _payload(event)
        ref = str(event.get("sha256") or event.get("event_hash") or event.get("artifact_sha256") or kind)
        if kind in {"CANDIDATE", "CANDIDATE_CREATED"}:
            candidates += 1
        elif kind in {"CRITIQUE", "CRITIQUE_CREATED"}:
            if str(payload.get("verdict", "")).upper() == "REJECT":
                critic_rejections += 1
            candidate_view = str(payload.get("candidate_verdict", "")).upper()
            critic_view = str(payload.get("verdict", "")).upper()
            if candidate_view and critic_view and candidate_view != critic_view:
                disagreements += 1
        elif kind in {"RISK_DECISION", "RISK_DECISION_CREATED"}:
            if str(payload.get("decision", "")).upper() == "REJECT":
                risk_rejections += 1
                issues.append((2, str(payload.get("primary_reason") or "risk gateway rejection"), ref))
        elif kind in {"EXECUTION_ATTEMPT", "EXECUTION_SENT"} and bool(payload.get("sent")):
            executed += 1
        elif kind in {"TRADE_CLOSED", "RECONCILIATION_CLOSED"}:
            value = float(payload.get("pnl_r") or 0.0)
            pnl_r += value
            if value > 0:
                wins += 1
            elif value < 0:
                losses += 1
        elif kind in {"RECONCILIATION", "RECONCILIATION_CREATED"}:
            status = str(payload.get("status", "")).upper()
            if payload.get("slippage_points") is not None:
                slippages.append(abs(float(payload["slippage_points"])))
            if status in {"AMBIGUOUS", "INCIDENT"}:
                issues.append((4, "broker reconciliation incident", ref))

        if "plan_adherent" in payload:
            adherence_total += 1
            if bool(payload["plan_adherent"]):
                adherence_passed += 1
            else:
                issues.append((3, str(payload.get("adherence_issue") or "plan adherence violation"), ref))

    plan_adherence = 100.0 if adherence_total == 0 else adherence_passed / adherence_total * 100.0
    average_slippage = sum(slippages) / len(slippages) if slippages else 0.0
    if issues:
        _, largest_issue, issue_ref = sorted(issues, key=lambda row: (-row[0], row[1], row[2]))[0]
        suggestion = ResearchSuggestion(
            suggestion_id=_suggestion_id(largest_issue, (issue_ref,)),
            created_at_utc=created,
            evidence_refs=(issue_ref,),
            problem=largest_issue,
            proposed_offline_test=(
                "Reproduce this issue from immutable session artifacts in an offline/shadow run; "
                "do not mutate the live strategy."
            ),
        )
        queue = (suggestion,)
    else:
        largest_issue = "No material issue detected in available evidence"
        queue = ()

    return JournalReport(
        report_id=(
            f"JOURNAL-{session_plan_id.removeprefix('SESSION_PLAN_')}-"
            f"{created.strftime('%H%M%S')}"
        ),
        session_plan_id=session_plan_id,
        session_date=session_date,
        created_at_utc=created,
        candidates=candidates,
        critic_rejections=critic_rejections,
        risk_rejections=risk_rejections,
        executed=executed,
        wins=wins,
        losses=losses,
        pnl_r=pnl_r,
        plan_adherence_pct=plan_adherence,
        disagreement_events=disagreements,
        average_slippage_points=average_slippage,
        largest_issue=largest_issue,
        research_queue=queue,
    )
