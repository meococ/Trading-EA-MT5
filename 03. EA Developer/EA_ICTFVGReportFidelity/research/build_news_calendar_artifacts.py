#!/usr/bin/env python3
"""Validate weekly Forex Factory evidence and emit deterministic EA artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA = "alphafactory.news_calendar.browser_weekly.v1"
EXPECTED_FIRST_WEEK = "dec30.2018"
EXPECTED_LAST_WEEK = "dec25.2022"
EXPECTED_WEEK_COUNT = 209
EXPECTED_FILTER = {
    "impact_id": 3,
    "currency_ids": {"EUR": 5, "USD": 9},
    "event_type_ids": [1, 2, 3, 4, 5, 7, 8, 9, 10, 11],
}
CSV_FIELDS = [
    "event_time_utc",
    "event_id",
    "currency",
    "impact",
    "event_name",
    "event_date_local",
    "source_week",
    "source_url",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def parse_iso_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"timestamp is not UTC: {value}")
    return parsed


def parse_week(value: str) -> datetime:
    return datetime.strptime(value.title(), "%b%d.%Y").replace(tzinfo=timezone.utc)


def validate(raw: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[str] = []
    if raw.get("schema_version") != EXPECTED_SCHEMA:
        errors.append("schema_version")
    if raw.get("source_rank") != "C" or raw.get("promotion_eligible") is not False:
        errors.append("source_classification")

    filter_contract = raw.get("filter_contract", {})
    for key, expected in EXPECTED_FILTER.items():
        if filter_contract.get(key) != expected:
            errors.append(f"filter_contract.{key}")
    if filter_contract.get("timezone_display") != "GMT+7":
        errors.append("filter_contract.timezone_display")

    audits = raw.get("week_audits", [])
    if len(audits) != EXPECTED_WEEK_COUNT:
        errors.append("week_count")
    if not audits or audits[0].get("week") != EXPECTED_FIRST_WEEK:
        errors.append("first_week")
    if not audits or audits[-1].get("week") != EXPECTED_LAST_WEEK:
        errors.append("last_week")

    previous_week: datetime | None = None
    audit_ids: set[str] = set()
    for audit in audits:
        try:
            current_week = parse_week(str(audit["week"]))
        except (KeyError, ValueError) as exc:
            errors.append(f"invalid_week:{exc}")
            continue
        if previous_week is not None and (current_week - previous_week).days != 7:
            errors.append(f"week_sequence:{audit['week']}")
        previous_week = current_week
        if "Filters On" not in str(audit.get("timezone_banner", "")):
            errors.append(f"filters_off:{audit['week']}")
        if "GMT +7" not in str(audit.get("timezone_banner", "")):
            errors.append(f"timezone:{audit['week']}")
        if audit.get("duplicate_event_ids") != 0:
            errors.append(f"audit_duplicate:{audit['week']}")
        source_url = str(audit.get("source_url", ""))
        if "impacts=3" not in source_url or "currencies=5,9" not in source_url:
            errors.append(f"filter_url:{audit['week']}")
        audit_ids.add(str(audit.get("week", "")))

    events = raw.get("events", [])
    if len(events) < 1200:
        errors.append("event_count_below_1200")
    event_ids: set[str] = set()
    composite_keys: set[tuple[str, str, str]] = set()
    parsed_events: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event.get("event_id", ""))
        timestamp = str(event.get("event_time_utc", ""))
        currency = str(event.get("currency", ""))
        name = str(event.get("event_name", ""))
        local_date = str(event.get("event_date_local", ""))
        source_week = str(event.get("source_week", ""))
        if not event_id or event_id in event_ids:
            errors.append(f"duplicate_or_empty_event_id:{event_id}")
        event_ids.add(event_id)
        if currency not in {"EUR", "USD"}:
            errors.append(f"currency:{event_id}")
        if event.get("impact") != "High Impact Expected":
            errors.append(f"impact:{event_id}")
        if not ("2019-01-01" <= local_date <= "2022-12-31"):
            errors.append(f"coverage:{event_id}")
        if source_week not in audit_ids:
            errors.append(f"source_week:{event_id}")
        try:
            parsed_time = parse_iso_utc(timestamp)
        except ValueError as exc:
            errors.append(f"timestamp:{event_id}:{exc}")
            continue
        key = (timestamp, currency, name)
        if key in composite_keys:
            errors.append(f"duplicate_composite:{event_id}")
        composite_keys.add(key)
        parsed_events.append({**event, "_epoch": int(parsed_time.timestamp())})

    parsed_events.sort(key=lambda item: (item["_epoch"], str(item["event_id"])))
    if any(
        parsed_events[index]["_epoch"] > parsed_events[index + 1]["_epoch"]
        for index in range(len(parsed_events) - 1)
    ):
        errors.append("sort_order")

    anchors = {
        "nfp_exact": sum(e["event_name"] == "Non-Farm Employment Change" for e in parsed_events),
        "fomc_statement": sum(e["event_name"] == "FOMC Statement" for e in parsed_events),
        "ecb_main_refinancing_rate": sum(
            e["event_name"] == "Main Refinancing Rate" for e in parsed_events
        ),
        "dec_2022_cpi": sum(
            e["event_date_local"] == "2022-12-13" and "CPI" in e["event_name"]
            for e in parsed_events
        ),
        "dec_2022_fomc": sum(
            e["event_date_local"] == "2022-12-15"
            and ("FOMC" in e["event_name"] or e["event_name"] == "Federal Funds Rate")
            for e in parsed_events
        ),
        "dec_2022_ecb": sum(
            e["event_date_local"] == "2022-12-15"
            and any(token in e["event_name"] for token in ("Refinancing", "Monetary Policy", "ECB Press"))
            for e in parsed_events
        ),
    }
    if anchors["nfp_exact"] < 45:
        errors.append("anchor_nfp")
    if anchors["fomc_statement"] < 30:
        errors.append("anchor_fomc")
    if anchors["ecb_main_refinancing_rate"] < 20:
        errors.append("anchor_ecb")
    if anchors["dec_2022_cpi"] != 4:
        errors.append("anchor_dec_2022_cpi")
    if anchors["dec_2022_fomc"] != 4:
        errors.append("anchor_dec_2022_fomc")
    if anchors["dec_2022_ecb"] != 3:
        errors.append("anchor_dec_2022_ecb")

    metrics = {
        "week_count": len(audits),
        "event_count": len(parsed_events),
        "unique_event_ids": len(event_ids),
        "calendar_timestamp_count": len({event["_epoch"] for event in parsed_events}),
        "collapsed_same_timestamp_event_count": (
            len(parsed_events) - len({event["_epoch"] for event in parsed_events})
        ),
        "first_event_time_utc": parsed_events[0]["event_time_utc"] if parsed_events else None,
        "last_event_time_utc": parsed_events[-1]["event_time_utc"] if parsed_events else None,
        "untimed_eurusd_audit_count": sum(
            len(audit.get("untimed_eurusd_events", [])) for audit in audits
        ),
        "global_event_audit_count": sum(
            len(audit.get("global_events_excluded", [])) for audit in audits
        ),
        "anchors": anchors,
        "validation_errors": errors,
    }
    if errors:
        raise ValueError(json.dumps(metrics, ensure_ascii=False, indent=2))
    return parsed_events, metrics


def csv_text(events: list[dict[str, Any]]) -> str:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for event in events:
        writer.writerow({field: event[field] for field in CSV_FIELDS})
    return buffer.getvalue()


def include_text(events: list[dict[str, Any]], raw_hash: str) -> str:
    # The MQL5 lookup answers only "is any release near this timestamp?".
    # Preserve every event row in raw/CSV evidence, but collapse same-time
    # releases so the binary-search array remains strictly increasing.
    epochs = [str(epoch) for epoch in sorted({event["_epoch"] for event in events})]
    rows = [",".join(epochs[index : index + 12]) for index in range(0, len(epochs), 12)]
    body = ",\n   ".join(rows)
    return (
        "// Generated by build_news_calendar_artifacts.py; do not edit manually.\n"
        "#ifndef ICT_FVG_NEWS_CALENDAR_2019_2022_MQH\n"
        "#define ICT_FVG_NEWS_CALENDAR_2019_2022_MQH\n\n"
        f'const string NEWS_CALENDAR_SOURCE_SHA256="{raw_hash}";\n'
        'const string NEWS_CALENDAR_SOURCE_CLASS="C_DIAGNOSTIC_ONLY";\n'
        "const datetime NEWS_CALENDAR_COVERAGE_START_UTC=1546300800;\n"
        "const datetime NEWS_CALENDAR_COVERAGE_END_UTC=1672531199;\n"
        f"#define NEWS_CALENDAR_COUNT {len(epochs)}\n"
        "datetime NEWS_CALENDAR_UTC[NEWS_CALENDAR_COUNT]=\n"
        "  {\n   " + body + "\n  };\n\n"
        "#endif\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--csv-out", required=True, type=Path)
    parser.add_argument("--include-out", required=True, type=Path)
    parser.add_argument("--audit-out", required=True, type=Path)
    args = parser.parse_args()

    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    events, metrics = validate(raw)
    raw_hash = sha256(args.raw)
    atomic_write_text(args.csv_out, csv_text(events))
    atomic_write_text(args.include_out, include_text(events, raw_hash))

    audit = {
        "schema_version": "alphafactory.news_calendar.build_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_rank": "C",
        "promotion_eligible": False,
        "verdict": "PASS_DIAGNOSTIC_SOURCE_C",
        "raw_path": str(args.raw),
        "raw_sha256": raw_hash,
        "csv_path": str(args.csv_out),
        "csv_sha256": sha256(args.csv_out),
        "include_path": str(args.include_out),
        "include_sha256": sha256(args.include_out),
        "metrics": metrics,
        "limitations": raw.get("limitations", []),
    }
    atomic_write_text(args.audit_out, json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(audit, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
