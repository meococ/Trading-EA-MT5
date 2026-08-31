from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import ArtifactExistsError, ArtifactStore, HashChainLedger
from .collector import collect_mt5_read_only
from .journal import build_journal_report
from .models import (
    AccountSnapshot,
    ArtifactRef,
    CalendarEvent,
    Candidate,
    Critique,
    ExecutionAttempt,
    JournalReport,
    MarketSnapshot,
    Reconciliation,
    RiskDecision,
    RiskPolicy,
    RiskState,
    SessionPlan,
    TradeIntent,
    WatchDecision,
)
from .pipeline import TradeChainRefs, run_shadow_pipeline
from .watcher import WatcherConfig, evaluate_watch


MODEL_TYPES = {
    "SessionPlan": SessionPlan,
    "MarketSnapshot": MarketSnapshot,
    "AccountSnapshot": AccountSnapshot,
    "Candidate": Candidate,
    "Critique": Critique,
    "TradeIntent": TradeIntent,
    "RiskPolicy": RiskPolicy,
    "RiskState": RiskState,
    "RiskDecision": RiskDecision,
    "ExecutionAttempt": ExecutionAttempt,
    "Reconciliation": Reconciliation,
    "WatchDecision": WatchDecision,
    "JournalReport": JournalReport,
}

# Authority artifacts are emitted only by their deterministic component.  The
# generic file adapter may validate their schema, but cannot mint approvals,
# broker attempts, reconciliations, account snapshots, or risk counters.
GENERIC_WRITABLE_TYPES = {
    "Candidate",
    "Critique",
    "TradeIntent",
}


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC (Z or +00:00)")
    return parsed


def _print(value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def _load_model(store: ArtifactStore, ref: ArtifactRef, model_type):
    return model_type.model_validate_json(store.read_verified_bytes(ref))


def cmd_probe(args: argparse.Namespace) -> int:
    calendar: tuple[CalendarEvent, ...] = ()
    calendar_available = False
    calendar_asof = None
    if args.calendar:
        payload = _read_json(args.calendar)
        if not isinstance(payload, dict):
            raise ValueError("calendar input must be an object")
        calendar = tuple(CalendarEvent.model_validate(row) for row in payload.get("events", ()))
        available_value = payload.get("available")
        if not isinstance(available_value, bool):
            raise ValueError("calendar.available must be a JSON boolean")
        calendar_available = available_value
        calendar_asof = _utc(payload.get("asof_utc")) if payload.get("asof_utc") else None
    market, account = collect_mt5_read_only(
        args.symbol,
        terminal_path=args.terminal,
        calendar=calendar,
        calendar_available=calendar_available,
        calendar_asof_utc=calendar_asof,
        server_utc_offset_minutes=args.server_utc_offset_minutes,
        tick_time_basis=args.tick_time_basis,
    )
    result: dict[str, Any] = {
        "market_snapshot": market.model_dump(mode="json"),
        "account_snapshot": (
            account.model_dump(mode="json")
            if args.include_sensitive_account
            else {
                "snapshot_id": account.snapshot_id,
                "captured_at_utc": account.captured_at_utc.isoformat(),
                "account_fingerprint_prefix": account.account_fingerprint[:12],
                "trade_mode": account.trade_mode.value,
                "risk_metrics_complete": account.risk_metrics_complete,
                "risk_metrics_source": account.risk_metrics_source,
                "terminal_connected": account.terminal_connected,
                "terminal_trade_allowed": account.terminal_trade_allowed,
                "expert_trading_allowed": account.expert_trading_allowed,
                "positions_count": len(account.positions),
                "redacted": True,
            }
        ),
        "safety": {"read_only": True, "orders_sent": 0, "live_trading_authorized": False},
    }
    if args.artifact_root:
        store = ArtifactStore(args.artifact_root)
        market_ref = store.write_artifact(f"snapshots/{market.snapshot_id}.json", market)
        account_ref = store.write_artifact(f"snapshots/{account.snapshot_id}.json", account)
        result["refs"] = {
            "market_snapshot": market_ref.model_dump(mode="json"),
            "account_snapshot": account_ref.model_dump(mode="json"),
        }
    _print(result)
    return 0


def cmd_write_plan(args: argparse.Namespace) -> int:
    plan = SessionPlan.model_validate(_read_json(args.input))
    reference = ArtifactStore(args.artifact_root).write_session_plan(plan)
    _print(reference)
    return 0


def cmd_write_artifact(args: argparse.Namespace) -> int:
    if args.model == "SessionPlan":
        raise ValueError("SessionPlan must use write-plan so the version chain is enforced")
    model_type = MODEL_TYPES.get(args.model)
    if model_type is None:
        raise ValueError(f"unsupported artifact model: {args.model}")
    if args.model not in GENERIC_WRITABLE_TYPES:
        raise ValueError(
            f"{args.model} is authority-controlled and cannot be minted by write-artifact"
        )
    value = model_type.model_validate(_read_json(args.input))
    store = ArtifactStore(args.artifact_root)
    plan = _load_model(store, value.plan, SessionPlan)
    if plan.plan_id != args.session_plan_id:
        raise ValueError("session_plan_id does not match the artifact's verified plan")
    reference = store.expected_reference(args.path, value)
    event_type = {
        "Candidate": "CANDIDATE_CREATED",
        "Critique": "CRITIQUE_CREATED",
        "TradeIntent": "TRADE_INTENT_CREATED",
    }[args.model]
    event_key = f"{event_type}:{reference.path}"
    envelope = {
        "event_type": event_type,
        "event_key": event_key,
        "session_plan_id": plan.plan_id,
        "artifact": reference.model_dump(mode="json"),
        "payload": value.model_dump(mode="json"),
    }
    ledger = HashChainLedger(args.ledger)
    try:
        ledger.append_unique(event_key, envelope)
    except ArtifactExistsError:
        matching = [
            entry
            for entry in ledger.verify()
            if isinstance(entry.get("payload"), dict)
            and entry["payload"].get("event_key") == event_key
        ]
        if len(matching) != 1 or matching[0]["payload"] != envelope:
            raise
    try:
        written = store.write_artifact(args.path, value)
    except ArtifactExistsError:
        store.read_verified_bytes(reference)
        written = reference
    if written != reference:
        raise ValueError("artifact write did not match the pre-recorded ledger reference")
    _print(reference)
    return 0


def _ref(payload: dict[str, Any], key: str) -> ArtifactRef:
    if key not in payload:
        raise ValueError(f"refs manifest is missing {key}")
    return ArtifactRef.model_validate(payload[key])


def cmd_watch(args: argparse.Namespace) -> int:
    store = ArtifactStore(args.artifact_root)
    payload = _read_json(args.refs)
    plan = _load_model(store, _ref(payload, "plan"), SessionPlan)
    market = _load_model(store, _ref(payload, "market_snapshot"), MarketSnapshot)
    account = _load_model(store, _ref(payload, "account_snapshot"), AccountSnapshot)
    previous_market = None
    previous_account = None
    if payload.get("previous_market_snapshot"):
        previous_market = _load_model(
            store, ArtifactRef.model_validate(payload["previous_market_snapshot"]), MarketSnapshot
        )
    if payload.get("previous_account_snapshot"):
        previous_account = _load_model(
            store, ArtifactRef.model_validate(payload["previous_account_snapshot"]), AccountSnapshot
        )
    limits = _read_json(args.config) if args.config else {}
    decision = evaluate_watch(
        plan,
        market,
        account,
        evaluated_at_utc=_utc(args.now),
        previous_market=previous_market,
        previous_account=previous_account,
        config=WatcherConfig(**limits),
    )
    decision_ref = store.write_artifact(f"watch/{decision.decision_id}.json", decision)
    if args.ledger:
        HashChainLedger(args.ledger).append(
            {
                "event_type": "WATCH_DECISION",
                "session_plan_id": plan.plan_id,
                "artifact": decision_ref.model_dump(mode="json"),
                "payload": decision.model_dump(mode="json"),
            }
        )
    _print({"decision": decision.model_dump(mode="json"), "ref": decision_ref.model_dump(mode="json")})
    return 0


def cmd_shadow(args: argparse.Namespace) -> int:
    payload = _read_json(args.refs)
    refs = TradeChainRefs(
        plan=_ref(payload, "plan"),
        market_snapshot=_ref(payload, "market_snapshot"),
        account_snapshot=_ref(payload, "account_snapshot"),
        candidate=_ref(payload, "candidate"),
        critique=_ref(payload, "critique"),
        intent=_ref(payload, "intent"),
        policy=_ref(payload, "policy"),
    )
    result = run_shadow_pipeline(
        ArtifactStore(args.artifact_root),
        refs,
        ledger_path=args.ledger,
        now_utc=_utc(args.now),
    )
    _print(
        {
            "risk_decision": result.risk_decision.model_dump(mode="json"),
            "risk_decision_ref": result.risk_decision_ref.model_dump(mode="json"),
            "execution_attempt": result.execution_attempt.model_dump(mode="json"),
            "execution_attempt_ref": result.execution_attempt_ref.model_dump(mode="json"),
            "handoff_ref": result.handoff_ref.model_dump(mode="json"),
        }
    )
    return 0


def cmd_verify_ledger(args: argparse.Namespace) -> int:
    entries = HashChainLedger(args.ledger).verify()
    _print(
        {
            "valid": True,
            "entries": len(entries),
            "head_sha256": entries[-1]["entry_sha256"] if entries else "0" * 64,
        }
    )
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    entries = HashChainLedger(args.ledger).verify()
    events = [entry["payload"] for entry in entries]
    report = build_journal_report(
        events,
        session_plan_id=args.session_plan_id,
        session_date=date.fromisoformat(args.session_date),
        created_at_utc=_utc(args.now),
    )
    store = ArtifactStore(args.artifact_root)
    reference = store.write_artifact(f"journal/{report.report_id}.json", report)
    _print({"report": report.model_dump(mode="json"), "ref": reference.model_dump(mode="json")})
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    if args.model not in MODEL_TYPES:
        raise ValueError(f"unsupported schema model: {args.model}")
    _print(MODEL_TYPES[args.model].model_json_schema())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="session-trader",
        description="Fail-closed OBSERVE/SHADOW control plane; no Python order execution.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    probe = commands.add_parser("probe", help="Collect one read-only MT5 snapshot")
    probe.add_argument("--symbol", action="append", required=True)
    # Required since 2026-08-31. Without it the collector called
    # mt5.initialize() with no path, silently attaching to whichever terminal
    # happened to be running. The observation plane must name the terminal it
    # reads, so the snapshot's terminal_path_sha256 means something.
    probe.add_argument(
        "--terminal",
        required=True,
        help="Path to terminal64.exe to read. The observation plane targets the "
        "Owner GUI; research/backtest never runs here (see session_trader/README.md, "
        "'Hai mat phang MT5').",
    )
    probe.add_argument("--calendar")
    probe.add_argument("--server-utc-offset-minutes", type=int)
    probe.add_argument("--tick-time-basis", choices=("UTC", "SERVER"))
    probe.add_argument("--artifact-root")
    probe.add_argument("--include-sensitive-account", action="store_true")
    probe.set_defaults(func=cmd_probe)

    plan = commands.add_parser("write-plan", help="Validate and write one immutable SessionPlan")
    plan.add_argument("--input", required=True)
    plan.add_argument("--artifact-root", required=True)
    plan.set_defaults(func=cmd_write_plan)

    artifact = commands.add_parser("write-artifact", help="Validate and write one immutable typed artifact")
    artifact.add_argument("--model", required=True)
    artifact.add_argument("--input", required=True)
    artifact.add_argument("--path", required=True)
    artifact.add_argument("--artifact-root", required=True)
    artifact.add_argument("--ledger", required=True)
    artifact.add_argument("--session-plan-id", required=True)
    artifact.set_defaults(func=cmd_write_artifact)

    watch = commands.add_parser("watch", help="Run one deterministic heartbeat scan")
    watch.add_argument("--refs", required=True)
    watch.add_argument("--artifact-root", required=True)
    watch.add_argument("--config")
    watch.add_argument("--ledger")
    watch.add_argument("--now")
    watch.set_defaults(func=cmd_watch)

    shadow = commands.add_parser("shadow", help="Run the hash-bound risk/execution shadow slice")
    shadow.add_argument("--refs", required=True)
    shadow.add_argument("--artifact-root", required=True)
    shadow.add_argument("--ledger", required=True)
    shadow.add_argument("--now")
    shadow.set_defaults(func=cmd_shadow)

    verify = commands.add_parser("verify-ledger", help="Verify the append-only hash chain")
    verify.add_argument("--ledger", required=True)
    verify.set_defaults(func=cmd_verify_ledger)

    journal = commands.add_parser("journal", help="Build a read-only journal report")
    journal.add_argument("--ledger", required=True)
    journal.add_argument("--artifact-root", required=True)
    journal.add_argument("--session-date", required=True)
    journal.add_argument("--session-plan-id", required=True)
    journal.add_argument("--now")
    journal.set_defaults(func=cmd_journal)

    schema = commands.add_parser("schema", help="Print a core JSON Schema")
    schema.add_argument("--model", required=True)
    schema.set_defaults(func=cmd_schema)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
