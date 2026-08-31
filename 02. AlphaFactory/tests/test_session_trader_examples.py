from __future__ import annotations

import json
import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ALPHA_ROOT))

from session_trader.models import CalendarEvent, RiskPolicy, RiskState, SessionPlan  # noqa: E402
from session_trader.watcher import WatcherConfig  # noqa: E402


EXAMPLES = ALPHA_ROOT / "session_trader" / "examples"


def test_checked_in_examples_validate_and_default_fail_closed() -> None:
    plan = SessionPlan.model_validate_json(
        (EXAMPLES / "SESSION_PLAN_2099-01-01_LONDON_v1.json").read_bytes()
    )
    policy = RiskPolicy.model_validate_json(
        (EXAMPLES / "policy.shadow.example.json").read_bytes()
    )
    watcher = WatcherConfig(**json.loads((EXAMPLES / "watcher.example.json").read_text(encoding="utf-8")))
    risk_state = RiskState.model_validate_json(
        (EXAMPLES / "risk_state.example.json").read_bytes()
    )
    calendar = json.loads((EXAMPLES / "calendar.example.json").read_text(encoding="utf-8"))

    assert plan.global_invalidation == "Template has no trading authority"
    assert policy.kill_switch is True
    assert policy.allowed_account_fingerprints == ()
    assert policy.live_execution_authorized is False
    assert watcher.quote_ttl_seconds == 600
    assert risk_state.state_id == "TEMPLATE_NOT_RUNTIME_AUTHORITY"
    assert calendar["available"] is False
    assert tuple(CalendarEvent.model_validate(event) for event in calendar["events"]) == ()
