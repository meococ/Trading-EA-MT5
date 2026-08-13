#!/usr/bin/env python3
"""Outcome-blind capability audit for the local ForexFactory raw surprise fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[2]
INPUT_PATH = WORKSPACE / (
    "02. AlphaFactory/data/forexfactory/EURUSD/news_events/"
    "forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json"
)
PLAN_PATH = WORKSPACE / "04. Memory/research/20260813_FOREXFACTORY_RAW_SURPRISE_CAPABILITY_PLAN.md"
TEST_PATH = WORKSPACE / "04. Memory/research/tests/test_audit_forexfactory_raw_surprise.py"
OUTPUT_ROOT = WORKSPACE / (
    "04. Memory/research/evidence/FOREXFACTORY-RAW-SURPRISE-CAPABILITY-001"
)

EXPECTED_INPUT_SHA256 = "78CB2656A27278B1DA04B2C594A2C73BB1877DBA3AB52BCCFAC36A215945EA8F"
EXPECTED_PLAN_SHA256 = "0ACF728A9F3D4A25D01F11548EE1B25F9A7C7238D3B98CCC02D26626E3629285"

REQUIRED_FIELDS = {
    "event_time_utc",
    "event_id",
    "currency",
    "event_name",
    "actual",
    "forecast",
    "previous",
}
YEARS = (2019, 2020, 2021, 2022)
NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:,\d{3})*|\d*)(?:\.\d+)?\s*([%KMBT]?)$", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_numeric(value: Any) -> tuple[float, str] | None:
    if not isinstance(value, str):
        return None
    text = value.strip().replace("\u2212", "-")
    if not text:
        return None
    match = NUMBER_RE.fullmatch(text)
    if match is None:
        return None
    unit = match.group(1).upper()
    number_text = text[:-1].strip() if unit else text
    number_text = number_text.replace(",", "")
    if number_text in {"", "+", "-", ".", "+.", "-."}:
        return None
    try:
        return float(number_text), unit
    except ValueError:
        return None


def has_first_public_pit(event: dict[str, Any]) -> bool:
    forecast_at = event.get("forecast_captured_at_utc")
    actual_at = event.get("actual_first_published_at_utc")
    release_at = event.get("event_time_utc")
    if not all(isinstance(v, str) and v for v in (forecast_at, actual_at, release_at)):
        return False
    try:
        forecast_dt = datetime.fromisoformat(forecast_at.replace("Z", "+00:00"))
        actual_dt = datetime.fromisoformat(actual_at.replace("Z", "+00:00"))
        release_dt = datetime.fromisoformat(release_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return forecast_dt < release_dt <= actual_dt


def has_revision_trace(event: dict[str, Any]) -> bool:
    history = event.get("revision_history")
    if not isinstance(history, list) or not history:
        return False
    for item in history:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("captured_at_utc"), str) or not item.get("captured_at_utc"):
            return False
        if not isinstance(item.get("snapshot_sha256"), str) or len(item.get("snapshot_sha256")) != 64:
            return False
    return True


def evaluate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("payload.events must be a list")

    embedded_count = payload.get("validation", {}).get("events")
    schema_version = payload.get("schema_version")
    field_complete = 0
    numeric_pairs = 0
    unit_consistent_pairs = 0
    pit_rows = 0
    revision_rows = 0
    numeric_by_year: Counter[int] = Counter()
    total_by_year: Counter[int] = Counter()
    currencies: Counter[str] = Counter()
    duplicate_ids = 0
    seen_ids: set[str] = set()

    for event in events:
        if not isinstance(event, dict):
            continue
        if REQUIRED_FIELDS.issubset(event):
            field_complete += 1
        event_id = str(event.get("event_id", ""))
        if event_id in seen_ids:
            duplicate_ids += 1
        seen_ids.add(event_id)
        currencies[str(event.get("currency", ""))] += 1

        time_text = event.get("event_time_utc")
        try:
            year = datetime.fromisoformat(str(time_text).replace("Z", "+00:00")).year
        except ValueError:
            year = 0
        if year:
            total_by_year[year] += 1

        actual = parse_numeric(event.get("actual"))
        forecast = parse_numeric(event.get("forecast"))
        if actual is not None and forecast is not None:
            numeric_pairs += 1
            if actual[1] == forecast[1]:
                unit_consistent_pairs += 1
                numeric_by_year[year] += 1
                if has_first_public_pit(event):
                    pit_rows += 1
                if has_revision_trace(event):
                    revision_rows += 1

    event_count = len(events)
    numeric_coverage = unit_consistent_pairs / event_count if event_count else 0.0
    per_year_coverage = {
        str(year): (
            numeric_by_year[year] / total_by_year[year] if total_by_year[year] else 0.0
        )
        for year in YEARS
    }

    live_contract = payload.get("live_update_contract")
    historical_live_identity = bool(
        isinstance(live_contract, dict)
        and live_contract.get("same_schema") is True
        and live_contract.get("same_revision_policy") is True
        and isinstance(live_contract.get("documented_at"), str)
    )
    source_rank_pass = (
        payload.get("source_rank") in {"A", "B"}
        and payload.get("promotion_eligible") is True
    )

    gates = {
        "container_identity": bool(
            schema_version == "alphafactory.news_calendar.browser_weekly.v1"
            and embedded_count == event_count
            and event_count > 0
            and duplicate_ids == 0
        ),
        "field_presence": field_complete == event_count and event_count > 0,
        "numeric_coverage": bool(
            numeric_coverage >= 0.70
            and all(per_year_coverage[str(year)] >= 0.50 for year in YEARS)
        ),
        "first_public_pit": pit_rows == unit_consistent_pairs and unit_consistent_pairs > 0,
        "revision_trace": revision_rows == unit_consistent_pairs and unit_consistent_pairs > 0,
        "historical_live_identity": historical_live_identity,
        "source_rank": source_rank_pass,
        "year_coverage": all(numeric_by_year[year] >= 100 for year in YEARS),
    }

    verdict = (
        "PASS_SOURCE_CAPABILITY_ONLY_NO_HYPOTHESIS"
        if all(gates.values())
        else "KILL_RETROSPECTIVE_OR_NON_PIT_SURPRISE_SOURCE"
    )
    return {
        "schema_version": "alphafactory.forexfactory_raw_surprise_capability.v1",
        "verdict": verdict,
        "source_only": True,
        "gates": gates,
        "counts": {
            "events": event_count,
            "embedded_validation_events": embedded_count,
            "field_complete_events": field_complete,
            "numeric_actual_forecast_pairs": numeric_pairs,
            "unit_consistent_numeric_pairs": unit_consistent_pairs,
            "first_public_pit_rows": pit_rows,
            "revision_trace_rows": revision_rows,
            "duplicate_event_ids": duplicate_ids,
            "by_currency": dict(sorted(currencies.items())),
            "total_by_year": {str(year): total_by_year[year] for year in YEARS},
            "numeric_by_year": {str(year): numeric_by_year[year] for year in YEARS},
        },
        "coverage": {
            "unit_consistent_numeric_pair_share": numeric_coverage,
            "numeric_pair_share_by_year": per_year_coverage,
        },
        "provenance_observations": {
            "declared_acquired_at_utc": payload.get("acquired_at_utc"),
            "declared_source_rank": payload.get("source_rank"),
            "declared_promotion_eligible": payload.get("promotion_eligible"),
            "declared_limitations": payload.get("limitations", []),
            "per_event_forecast_capture_timestamps": pit_rows,
            "per_event_revision_histories": revision_rows,
            "live_update_contract_present": isinstance(live_contract, dict),
        },
        "forbidden_counters": {
            "market_price_fields_read": 0,
            "post_event_returns_computed": 0,
            "directions_assigned": 0,
            "trades_simulated": 0,
            "pnl_pf_dd_metrics_computed": 0,
            "mt5_launches": 0,
            "validation_or_holdout_reads": 0,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(input_path: Path, plan_path: Path, output_root: Path) -> tuple[Path, Path]:
    input_sha = sha256_file(input_path)
    plan_sha = sha256_file(plan_path)
    if input_sha != EXPECTED_INPUT_SHA256:
        raise RuntimeError(f"input hash mismatch: {input_sha}")
    if plan_sha != EXPECTED_PLAN_SHA256:
        raise RuntimeError(f"plan hash mismatch: {plan_sha}")
    if output_root.exists():
        raise RuntimeError(f"evidence root already exists: {output_root}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    report = evaluate_payload(payload)
    report["bindings"] = {
        "input_path": input_path.relative_to(WORKSPACE).as_posix(),
        "input_sha256": input_sha,
        "plan_path": plan_path.relative_to(WORKSPACE).as_posix(),
        "plan_sha256": plan_sha,
    }

    report_path = output_root / "capability_report.json"
    write_json(report_path, report)
    receipt = {
        "schema_version": "alphafactory.forexfactory_raw_surprise_capability_receipt.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": report["verdict"],
        "report_path": report_path.relative_to(WORKSPACE).as_posix(),
        "report_sha256": sha256_file(report_path),
        "input_sha256": input_sha,
        "plan_sha256": plan_sha,
        "auditor_sha256": sha256_file(Path(__file__).resolve()),
        "test_sha256": sha256_file(TEST_PATH),
        "market_edge_claim_authorized": False,
        "hypothesis_authorized": False,
        "mql5_or_mt5_authorized": False,
        "paid_source_authorized": False,
    }
    receipt_path = output_root / "receipt.json"
    write_json(receipt_path, receipt)
    return report_path, receipt_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    report_path, receipt_path = run(args.input, args.plan, args.output_root)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(json.dumps({
        "verdict": report["verdict"],
        "gates": report["gates"],
        "report": str(report_path),
        "receipt": str(receipt_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
