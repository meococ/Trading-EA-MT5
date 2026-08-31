from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "audit_forexfactory_raw_surprise.py"
SPEC = importlib.util.spec_from_file_location("audit_forexfactory_raw_surprise", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def event(event_id: int, year: int, *, pit: bool, revision: bool) -> dict:
    release = datetime(year, 1, 2, 13, 30, tzinfo=timezone.utc)
    result = {
        "event_time_utc": release.isoformat().replace("+00:00", "Z"),
        "event_id": str(event_id),
        "currency": "USD",
        "event_name": "Synthetic numeric release",
        "actual": "1.2%",
        "forecast": "1.0%",
        "previous": "0.9%",
    }
    if pit:
        result["forecast_captured_at_utc"] = (
            release - timedelta(minutes=1)
        ).isoformat().replace("+00:00", "Z")
        result["actual_first_published_at_utc"] = release.isoformat().replace("+00:00", "Z")
    if revision:
        result["revision_history"] = [{
            "captured_at_utc": release.isoformat().replace("+00:00", "Z"),
            "snapshot_sha256": "A" * 64,
        }]
    return result


def payload(*, pit: bool, revision: bool, live: bool, rank: str = "A", promotion: bool = True) -> dict:
    events = []
    next_id = 1
    for year in MODULE.YEARS:
        for _ in range(100):
            events.append(event(next_id, year, pit=pit, revision=revision))
            next_id += 1
    result = {
        "schema_version": "alphafactory.news_calendar.browser_weekly.v1",
        "source_rank": rank,
        "promotion_eligible": promotion,
        "validation": {"events": len(events)},
        "events": events,
    }
    if live:
        result["live_update_contract"] = {
            "same_schema": True,
            "same_revision_policy": True,
            "documented_at": "2026-08-13",
        }
    return result


def test_numeric_parser_accepts_frozen_units() -> None:
    assert MODULE.parse_numeric("-12.5%") == (-12.5, "%")
    assert MODULE.parse_numeric("330K") == (330.0, "K")
    assert MODULE.parse_numeric("1,234.5") == (1234.5, "")


def test_numeric_parser_rejects_text_and_ranges() -> None:
    assert MODULE.parse_numeric(1.0) is None
    assert MODULE.parse_numeric("") is None
    assert MODULE.parse_numeric("1.0-1.5") is None
    assert MODULE.parse_numeric("Better than expected") is None


def test_complete_pit_fixture_passes_capability_only() -> None:
    report = MODULE.evaluate_payload(payload(pit=True, revision=True, live=True))
    assert report["verdict"] == "PASS_SOURCE_CAPABILITY_ONLY_NO_HYPOTHESIS"
    assert all(report["gates"].values())
    assert all(value == 0 for value in report["forbidden_counters"].values())


def test_retrospective_fixture_fails_pit_revision_live_and_rank() -> None:
    report = MODULE.evaluate_payload(
        payload(pit=False, revision=False, live=False, rank="C", promotion=False)
    )
    assert report["verdict"] == "KILL_RETROSPECTIVE_OR_NON_PIT_SURPRISE_SOURCE"
    assert report["gates"]["numeric_coverage"] is True
    assert report["gates"]["year_coverage"] is True
    assert report["gates"]["first_public_pit"] is False
    assert report["gates"]["revision_trace"] is False
    assert report["gates"]["historical_live_identity"] is False
    assert report["gates"]["source_rank"] is False


def test_mixed_units_are_not_counted_as_numeric_surprises() -> None:
    data = payload(pit=True, revision=True, live=True)
    for item in data["events"]:
        item["forecast"] = "1.0K"
    report = MODULE.evaluate_payload(data)
    assert report["counts"]["numeric_actual_forecast_pairs"] == 400
    assert report["counts"]["unit_consistent_numeric_pairs"] == 0
    assert report["gates"]["numeric_coverage"] is False
    assert report["verdict"] == "KILL_RETROSPECTIVE_OR_NON_PIT_SURPRISE_SOURCE"
