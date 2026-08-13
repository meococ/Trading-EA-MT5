#!/usr/bin/env python3
"""Fail-closed audit of the prospective economic-calendar collector runtime."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


TARGET_CURRENCIES = {"USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"}
REQUIRED_SAFETY = {
    "outcome_accessed": False,
    "prices_read": False,
    "orders": False,
    "trading_disabled": True,
}


def parse_local(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def audit(root: Path, now: datetime | None = None, stale_after_seconds: int = 125) -> dict[str, Any]:
    is_v15 = (root / "calendar_pit_v15.jsonl").is_file()
    v14_suffix = "v141" if (root / "calendar_pit_v141.jsonl").is_file() else "v14"
    is_v14 = not is_v15 and (root / f"calendar_pit_{v14_suffix}.jsonl").is_file()
    if is_v15:
        jsonl_path = root / "calendar_pit_v15.jsonl"
        state_path = root / "catalog_state_v15.txt"
    else:
        jsonl_path = root / (f"calendar_pit_{v14_suffix}.jsonl" if is_v14 else "calendar_pit.jsonl")
        state_path = root / (f"event_state_{v14_suffix}.txt" if is_v14 else "currency_state.txt")
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    record_lines: list[int] = []

    if not jsonl_path.is_file():
        return {"status": "FAIL", "errors": [f"missing {jsonl_path.name}"]}
    if not state_path.is_file():
        errors.append(f"missing {state_path.name}")

    for line_number, raw in enumerate(jsonl_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSONL line {line_number}: {exc.msg}")
            continue
        records.append(record)
        record_lines.append(line_number)

    init_indexes = [index for index, record in enumerate(records) if record.get("kind") == "INIT"]
    if not init_indexes:
        errors.append("missing INIT receipt")
        session_records = records
        session_lines = record_lines
    else:
        session_start = init_indexes[-1]
        session_records = records[session_start:]
        session_lines = record_lines[session_start:]

    for line_number, record in zip(session_lines, session_records):
        for key, expected in REQUIRED_SAFETY.items():
            if record.get(key) is not expected:
                errors.append(f"line {line_number} safety mismatch {key}")

    kinds = [record.get("kind") for record in session_records]
    prime_kind = "PRIME_EVENT" if is_v14 else "PRIME"
    prime_rows: list[dict[str, Any]] = []
    if not is_v15:
        if prime_kind not in kinds:
            errors.append(f"missing {prime_kind} receipt")
        prime_rows = [record for record in session_records if record.get("kind") == prime_kind]
    discovery_currencies: set[str] = set()
    if is_v14 or is_v15:
        discovery_currencies = {
            str(record.get("currency"))
            for record in session_records
            if record.get("kind") == "DISCOVERY_EVENT_DEFS"
        }
        if any(
            record.get("kind") == "INIT" and record.get("enum_ok_loaded") == len(TARGET_CURRENCIES)
            for record in session_records
        ):
            discovery_currencies = set(TARGET_CURRENCIES)
        if discovery_currencies != TARGET_CURRENCIES:
            missing = sorted(TARGET_CURRENCIES - discovery_currencies)
            unexpected = sorted(discovery_currencies - TARGET_CURRENCIES)
            errors.append(
                f"event discovery coverage mismatch: missing={missing}, unexpected={unexpected}"
            )
        if "DISCOVERY_COUNTRIES" not in kinds and not any(
            record.get("countries_loaded") is True
            for record in session_records
            if record.get("kind") == "INIT"
        ):
            errors.append("missing country discovery/load receipt")
        if is_v15 and "CATALOG_FROZEN" not in kinds and not any(
            record.get("catalog_frozen") is True
            for record in session_records
            if record.get("kind") == "INIT"
        ):
            errors.append("missing frozen catalog receipt")
    else:
        prime_currencies = {record.get("currency_filter") for record in prime_rows}
        if prime_currencies != TARGET_CURRENCIES:
            missing = sorted(TARGET_CURRENCIES - prime_currencies)
            unexpected = sorted(str(value) for value in prime_currencies - TARGET_CURRENCIES)
            errors.append(
                f"PRIME currency coverage mismatch: missing={missing}, unexpected={unexpected}"
            )
    for prime in prime_rows:
        if prime.get("values_returned") != 0:
            errors.append(f"{prime_kind} returned snapshot rows")
        change_id = prime.get("change_id_after") if is_v14 else prime.get("change_id")
        if not isinstance(change_id, int) or change_id <= 0:
            errors.append(f"{prime_kind} has invalid change_id")

    value_kinds = {"OBSERVATION_HISTORY", "MUTATION_HISTORY"} if is_v15 else {"VALUE"}
    values = [record for record in session_records if record.get("kind") in value_kinds]
    for record in values:
        if is_v14 or is_v15:
            source_currencies = set(str(record.get("source_currencies", "")).split("|"))
            if not source_currencies or not source_currencies <= TARGET_CURRENCIES:
                errors.append(f"VALUE has invalid source currencies: {sorted(source_currencies)}")
        else:
            currency = record.get("currency", "")
            scope_status = record.get("scope_status")
            if scope_status == "TARGET" and currency not in TARGET_CURRENCIES:
                errors.append(f"non-target currency emitted as TARGET: {currency}")
            if scope_status not in {"TARGET", "UNKNOWN_METADATA"}:
                errors.append(f"invalid scope_status: {scope_status}")
        if not record.get("payload_hash"):
            errors.append("VALUE missing payload_hash")

    now = now or datetime.now()
    last_record_time = parse_local(session_records[-1]["ts_local"]) if session_records else None
    age_seconds = (now - last_record_time).total_seconds() if last_record_time else None
    heartbeat_seen = "HEARTBEAT" in kinds
    if age_seconds is not None and age_seconds > stale_after_seconds:
        errors.append(f"collector stale: {age_seconds:.0f}s")

    fatal_runtime_kinds = {
        "API_ERROR",
        "API_ERROR_HISTORY",
        "API_ERROR_COUNTRIES",
        "API_ERROR_ENUM",
        "API_ERROR_EVENT",
        "IO_ERROR_HISTORY",
        "GAP_OVERFLOW",
        "MISSING_DUE_HISTORY",
        "SOURCE_CAPACITY_ERROR",
        "BATCH_IO_ERROR",
    }
    api_errors = sum(kind in fatal_runtime_kinds for kind in kinds)
    if api_errors:
        errors.append(f"latest runtime session has {api_errors} Calendar API error(s)")
    init_rows = [record for record in session_records if record.get("kind") == "INIT"]
    runtime_age_seconds = None
    if init_rows:
        runtime_age_seconds = (now - parse_local(init_rows[-1]["ts_local"])).total_seconds()
    if runtime_age_seconds is not None and runtime_age_seconds > 90 and not heartbeat_seen:
        errors.append("runtime older than 90s without HEARTBEAT")
    if len(kinds) >= 2 and all(kind in fatal_runtime_kinds for kind in kinds[-2:]):
        errors.append("two consecutive Calendar API errors")
    state: dict[str, str] = {}
    durable_event_count = 0
    primed_event_count = 0
    selected_event_count = 0
    occurrence_count = 0
    future_history_seen = "FUTURE_DISCOVERY_HISTORY" in kinds
    idle_history_seen = "IDLE_PROOF_HISTORY" in kinds
    paired_history_proof = False
    if state_path.is_file():
        state_lines = state_path.read_text(encoding="utf-8-sig").splitlines()
        for raw in state_lines:
            if "=" in raw:
                key, value = raw.split("=", 1)
                state[key] = value
        if is_v15:
            if state.get("schema") != "15":
                errors.append("durable catalog schema is not 15")
            if state.get("version") != "1.5.0":
                errors.append("durable catalog version is not 1.5.0")
            if state.get("frozen") != "1":
                errors.append("durable catalog is not frozen")
            if state.get("enum_ok") != "1,1,1,1,1,1,1,1":
                errors.append("durable event discovery is incomplete")

            event_rows = [raw.split("\t") for raw in state_lines if raw.startswith("E\t")]
            selected_event_count = len(event_rows)
            try:
                declared_selected = int(state.get("n_sel", "0"))
            except ValueError:
                declared_selected = -1
            if declared_selected <= 0 or declared_selected != selected_event_count:
                errors.append(
                    "durable selected-event count mismatch: "
                    f"declared={declared_selected}, rows={selected_event_count}"
                )
            try:
                if int(state.get("catalog_hash", "0")) == 0:
                    errors.append("durable catalog hash is zero")
            except ValueError:
                errors.append("durable catalog hash is not an integer")

            event_ids: set[int] = set()
            for fields in event_rows:
                if len(fields) < 11:
                    errors.append("malformed durable catalog event row")
                    continue
                try:
                    event_id = int(fields[1])
                except ValueError:
                    event_id = 0
                if event_id <= 0:
                    errors.append("durable catalog contains invalid event id")
                elif event_id in event_ids:
                    errors.append(f"durable catalog contains duplicate event id {event_id}")
                event_ids.add(event_id)
                source_currencies = set(fields[2].split("|"))
                if not source_currencies or not source_currencies <= TARGET_CURRENCIES:
                    errors.append(
                        f"durable catalog event {event_id} has invalid source currencies"
                    )

            occurrence_path = root / "occurrence_v15.txt"
            if not occurrence_path.is_file():
                errors.append("missing occurrence_v15.txt")
            else:
                occurrence_lines = occurrence_path.read_text(encoding="utf-8-sig").splitlines()
                occurrence_state: dict[str, str] = {}
                for raw in occurrence_lines:
                    if "=" in raw:
                        key, value = raw.split("=", 1)
                        occurrence_state[key] = value
                if occurrence_state.get("schema") != "15":
                    errors.append("durable occurrence schema is not 15")
                occurrence_rows = [
                    raw.split("\t") for raw in occurrence_lines if raw.startswith("O\t")
                ]
                occurrence_count = len(occurrence_rows)
                try:
                    declared_occurrences = int(occurrence_state.get("n_occ", "-1"))
                except ValueError:
                    declared_occurrences = -1
                if declared_occurrences < 0 or declared_occurrences != occurrence_count:
                    errors.append(
                        "durable occurrence count mismatch: "
                        f"declared={declared_occurrences}, rows={occurrence_count}"
                    )
                occurrence_keys: set[tuple[int, int, int, int]] = set()
                for fields in occurrence_rows:
                    if len(fields) < 18:
                        errors.append("malformed durable occurrence row")
                        continue
                    try:
                        key = tuple(int(fields[index]) for index in (1, 2, 3, 4))
                    except ValueError:
                        key = (0, 0, 0, 0)
                    if min(key[:3]) <= 0:
                        errors.append("durable occurrence contains invalid identity")
                    elif key in occurrence_keys:
                        errors.append(f"durable occurrence contains duplicate identity {key}")
                    occurrence_keys.add(key)

            def occurrence_key(record: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
                return (
                    record.get("event_id"),
                    record.get("value_id"),
                    record.get("scheduled"),
                    record.get("period"),
                )

            future_keys = {
                occurrence_key(record)
                for record in session_records
                if record.get("kind") == "FUTURE_DISCOVERY_HISTORY"
            }
            idle_keys = {
                occurrence_key(record)
                for record in session_records
                if record.get("kind") == "IDLE_PROOF_HISTORY"
            }
            paired_history_proof = bool(future_keys & idle_keys)
            if not future_history_seen:
                errors.append("missing FUTURE_DISCOVERY_HISTORY receipt")
            if not idle_history_seen:
                errors.append("missing IDLE_PROOF_HISTORY receipt")
            if future_history_seen and idle_history_seen and not paired_history_proof:
                errors.append("future and idle History receipts do not identify the same occurrence")
        elif is_v14:
            if state.get("countries_ok") != "1":
                errors.append("durable country discovery is incomplete")
            if state.get("enum_ok") != "1,1,1,1,1,1,1,1":
                errors.append("durable event discovery is incomplete")
            event_rows = [raw.split("\t") for raw in state_lines if raw.startswith("E\t")]
            durable_event_count = len(event_rows)
            try:
                declared_events = int(state.get("nev", "0"))
            except ValueError:
                declared_events = -1
            if declared_events <= 0 or declared_events != durable_event_count:
                errors.append(
                    f"durable event count mismatch: declared={declared_events}, rows={durable_event_count}"
                )
            for fields in event_rows:
                if len(fields) < 4:
                    errors.append("malformed durable event state row")
                    continue
                try:
                    change_id = int(fields[2])
                except ValueError:
                    change_id = 0
                if fields[3] == "1":
                    primed_event_count += 1
                if fields[3] != "1" or change_id <= 0:
                    errors.append(f"event {fields[1]} is not durably primed")
            acceptance_evidence_seen = "IDLE_PROOF_EVENT" in kinds or bool(values)
            if not acceptance_evidence_seen:
                errors.append("missing post-prime IDLE_PROOF_EVENT or VALUE receipt")
        else:
            for currency in TARGET_CURRENCIES:
                if state.get(f"{currency}_primed") != "1":
                    errors.append(f"durable state is not primed for {currency}")
                try:
                    if int(state.get(f"{currency}_change_id", "0")) <= 0:
                        errors.append(f"durable change_id is invalid for {currency}")
                except ValueError:
                    errors.append(f"durable change_id is not an integer for {currency}")

    durable_ids = None if (is_v14 or is_v15) else {
        currency: int(state.get(f"{currency}_change_id", "0") or 0)
        for currency in sorted(TARGET_CURRENCIES)
    }

    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_version": "calendar_pit_runtime_audit.v4",
        "collector_version": init_rows[-1].get("collector_version") if init_rows else None,
        "total_records": len(records),
        "session_records": len(session_records),
        "value_records": len(values),
        "api_errors": api_errors,
        "heartbeat_seen": heartbeat_seen,
        "runtime_age_seconds": runtime_age_seconds,
        "last_record_age_seconds": age_seconds,
        "durable_change_ids": durable_ids,
        "durable_event_count": durable_event_count if is_v14 else None,
        "primed_event_count": primed_event_count if is_v14 else None,
        "selected_event_count": selected_event_count if is_v15 else None,
        "occurrence_count": occurrence_count if is_v15 else None,
        "future_history_seen": future_history_seen if is_v15 else None,
        "idle_history_seen": idle_history_seen if is_v15 else None,
        "paired_history_proof": paired_history_proof if is_v15 else None,
        "discovery_currencies": sorted(discovery_currencies) if (is_v14 or is_v15) else None,
        "acceptance_evidence_seen": (
            paired_history_proof
            if is_v15
            else (("IDLE_PROOF_EVENT" in kinds or bool(values)) if is_v14 else None)
        ),
        "errors": errors,
        "authority": "prospective_source_collection_only_no_edge_claim",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stale-after-seconds", type=int, default=125)
    args = parser.parse_args()
    result = audit(args.root, stale_after_seconds=args.stale_after_seconds)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
