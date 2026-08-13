#!/usr/bin/env python3
"""Fail-closed stopped-session auditor for DOM collector revision 1.1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY")
FILES = {
    "json": "dom_tape_v1_1.jsonl",
    "csv": "dom_levels_v1_1.csv",
    "state": "dom_state_v1_1.txt",
}
FATAL = {"API_ERROR_BOOK", "API_ERROR_TIMER", "IO_ERROR", "TICK64_REGRESS", "EMPTY_BOOK"}
SAFETY = {
    "schema_version": "1.1",
    "collector_version": "1.1.1",
    "recv_clock": "terminal_observation_not_official_first_public",
    "crash_partial_possible": True,
    "transactional": False,
    "outcome_accessed": False,
    "prices_read": False,
    "orders": False,
    "trading_disabled": True,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def audit(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    paths = {key: root / name for key, name in FILES.items()}
    for key, path in paths.items():
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"MISSING_OR_EMPTY_{key.upper()}: {path}")
    if errors:
        return {"verdict": "FAIL", "errors": errors}

    records: list[dict[str, Any]] = []
    with paths["json"].open("r", encoding="utf-8-sig") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"JSON_DECODE line={line_no}: {exc}")
                continue
            if not isinstance(item, dict):
                errors.append(f"JSON_NOT_OBJECT line={line_no}")
                continue
            records.append(item)
    if not records:
        return {"verdict": "FAIL", "errors": errors + ["NO_JSON_RECORDS"]}

    kinds = Counter(str(row.get("kind", "")) for row in records)
    seen_fatal = sorted(kind for kind in FATAL if kinds[kind])
    if seen_fatal:
        errors.append("FATAL_KINDS: " + ",".join(seen_fatal))
    for index, row in enumerate(records, 1):
        for key, expected in SAFETY.items():
            if row.get(key) != expected:
                errors.append(f"SAFETY record={index} {key}={row.get(key)!r}")
        if not isinstance(row.get("terminal_build"), int) or row["terminal_build"] <= 0:
            errors.append(f"TERMINAL_BUILD record={index}")
        if not row.get("account_server") or not row.get("session_id"):
            errors.append(f"IDENTITY record={index}")

    init_indexes = [i for i, row in enumerate(records) if row.get("kind") == "INIT"]
    if not init_indexes:
        return {"verdict": "FAIL", "errors": errors + ["NO_INIT"]}
    init_index = init_indexes[-1]
    session_id = records[init_index].get("session_id")
    session = [row for row in records if row.get("session_id") == session_id]
    session_positions = [i for i, row in enumerate(records) if row.get("session_id") == session_id]
    if session_positions != list(range(session_positions[0], session_positions[-1] + 1)):
        errors.append("SESSION_NOT_CONTIGUOUS")
    session_kinds = [str(row.get("kind", "")) for row in session]
    expected_prefix = ["WRITER_LOCK", "SUBSCRIBE", "SUBSCRIBE", "SUBSCRIBE", "SUBSCRIBE", "INIT"]
    if session_kinds[:6] != expected_prefix:
        errors.append(f"STARTUP_ORDER: {session_kinds[:6]!r}")
    subscriptions = [row.get("symbol") for row in session[:6] if row.get("kind") == "SUBSCRIBE"]
    if tuple(subscriptions) != SYMBOLS:
        errors.append(f"SUBSCRIPTIONS: {subscriptions!r}")
    init = records[init_index]
    if tuple(init.get("symbols", [])) != SYMBOLS:
        errors.append(f"INIT_SYMBOLS: {init.get('symbols')!r}")
    if session_kinds[-1:] != ["SHUTDOWN"]:
        errors.append(f"NO_FINAL_SHUTDOWN: {session_kinds[-3:]!r}")

    heartbeats = [row for row in session if row.get("kind") == "HEARTBEAT"]
    if not any(
        {item.get("symbol") for item in row.get("symbols", []) if item.get("subscribed") is True}
        == set(SYMBOLS)
        for row in heartbeats
    ):
        errors.append("NO_ALL_SUBSCRIBED_HEARTBEAT")

    previous_tick: int | None = None
    previous_snapshot: int | None = None
    previous_event: dict[str, int] = {}
    by_symbol: Counter[str] = Counter()
    for row in session:
        tick = row.get("tick64")
        if not isinstance(tick, int) or tick < 0:
            errors.append("INVALID_TICK64")
        elif previous_tick is not None and tick < previous_tick:
            errors.append(f"TICK64_REGRESSION: {previous_tick}->{tick}")
        if isinstance(tick, int):
            previous_tick = tick
        symbol = row.get("symbol")
        event = row.get("event_seq")
        if symbol in SYMBOLS and isinstance(event, int):
            if symbol in previous_event and event <= previous_event[symbol]:
                errors.append(f"EVENT_NOT_STRICT {symbol}: {previous_event[symbol]}->{event}")
            previous_event[symbol] = event
        if row.get("kind") == "SNAPSHOT":
            by_symbol[str(symbol)] += 1
            snap = row.get("snapshot_seq")
            if not isinstance(snap, int) or snap <= 0:
                errors.append("INVALID_SNAPSHOT_SEQ")
            elif previous_snapshot is not None and snap <= previous_snapshot:
                errors.append(f"SNAPSHOT_NOT_STRICT: {previous_snapshot}->{snap}")
            if isinstance(snap, int):
                previous_snapshot = snap
    for symbol in SYMBOLS:
        if by_symbol[symbol] == 0:
            errors.append(f"NO_SNAPSHOT: {symbol}")

    json_keys: dict[tuple[str, str, int, int, str], int] = {}
    for row in records:
        if row.get("kind") != "SNAPSHOT":
            continue
        key = (
            str(row.get("session_id")), str(row.get("symbol")), int(row.get("event_seq", -1)),
            int(row.get("snapshot_seq", -1)), str(row.get("payload_hash")),
        )
        depth = row.get("depth")
        levels = row.get("levels")
        if key in json_keys:
            errors.append(f"DUPLICATE_JSON_KEY: {key!r}")
        if not isinstance(depth, int) or depth <= 0 or not isinstance(levels, list) or len(levels) != depth:
            errors.append(f"JSON_DEPTH: {key!r}")
            continue
        for level_index, level in enumerate(levels):
            if level.get("i") != level_index or level.get("type") not in (1, 2):
                errors.append(f"JSON_LEVEL: {key!r} i={level_index}")
        json_keys[key] = depth

    csv_counts: Counter[tuple[str, str, int, int, str]] = Counter()
    csv_indexes: dict[tuple[str, str, int, int, str], set[int]] = defaultdict(set)
    with paths["csv"].open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected_header = [
            "kind", "ts_local", "ts_server", "ts_current", "tick64", "symbol", "event_seq",
            "snapshot_seq", "payload_hash", "depth", "level_index", "type", "price", "volume",
            "volume_real", "session_id", "recv_clock",
        ]
        if reader.fieldnames != expected_header:
            errors.append(f"CSV_HEADER: {reader.fieldnames!r}")
        for line_no, row in enumerate(reader, 2):
            try:
                key = (
                    row["session_id"], row["symbol"], int(row["event_seq"]),
                    int(row["snapshot_seq"]), row["payload_hash"],
                )
                csv_counts[key] += 1
                csv_indexes[key].add(int(row["level_index"]))
                if row["kind"] != "SNAPSHOT" or row["recv_clock"] != SAFETY["recv_clock"]:
                    errors.append(f"CSV_SAFETY line={line_no}")
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"CSV_PARSE line={line_no}: {exc}")
    for key, depth in json_keys.items():
        if csv_counts[key] != depth:
            errors.append(f"CSV_JSON_COUNT {key!r}: {csv_counts[key]}!={depth}")
        if csv_indexes[key] != set(range(depth)):
            errors.append(f"CSV_INDEXES: {key!r}")
    if set(csv_counts) - set(json_keys):
        errors.append(f"CSV_WITHOUT_JSON: {len(set(csv_counts) - set(json_keys))}")

    state_map: dict[str, str] = {}
    state_symbols: dict[str, list[str]] = {}
    for line in paths["state"].read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("S\t"):
            fields = line.split("\t")
            if len(fields) != 9:
                errors.append(f"STATE_SYMBOL_FIELDS: {line}")
            else:
                state_symbols[fields[1]] = fields
        elif "=" in line:
            key, value = line.split("=", 1)
            if key in state_map:
                errors.append(f"STATE_DUPLICATE: {key}")
            state_map[key] = value
    required = {
        "schema", "version", "symbols", "snapshot_reserved", "snapshot_used", "events",
        "snapshots", "duplicates", "empty", "api_errors", "io_errors",
    }
    if set(state_map) != required:
        errors.append(f"STATE_KEYS: {sorted(state_map)!r}")
    if state_map.get("schema") != "1.1" or state_map.get("version") != "1.1.1":
        errors.append("STATE_VERSION")
    if state_map.get("symbols") != ",".join(SYMBOLS) or set(state_symbols) != set(SYMBOLS):
        errors.append("STATE_SYMBOLS")
    try:
        counters = {key: int(value) for key, value in state_map.items() if key not in {"schema", "version", "symbols"}}
        if any(value < 0 for value in counters.values()):
            errors.append("STATE_NEGATIVE")
        if counters["snapshot_used"] > counters["snapshot_reserved"]:
            errors.append("STATE_SNAPSHOT_FLOOR")
        if counters["empty"] or counters["api_errors"] or counters["io_errors"]:
            errors.append("STATE_FATAL_COUNTERS")
        for symbol, fields in state_symbols.items():
            if int(fields[3]) > int(fields[2]):
                errors.append(f"STATE_EVENT_FLOOR: {symbol}")
    except (KeyError, ValueError):
        errors.append("STATE_COUNTER_PARSE")

    shutdown = session[-1] if session and session[-1].get("kind") == "SHUTDOWN" else {}
    for key in ("events", "snapshots", "duplicates", "empty", "api_errors", "io_errors"):
        if key in state_map and shutdown.get(key) != int(state_map[key]):
            errors.append(f"SHUTDOWN_STATE_MISMATCH {key}: {shutdown.get(key)}!={state_map[key]}")

    metrics = {
        "session_id": session_id,
        "records": len(records),
        "session_records": len(session),
        "kind_counts": dict(sorted(kinds.items())),
        "snapshots_by_symbol": {symbol: by_symbol[symbol] for symbol in SYMBOLS},
        "json_snapshots": len(json_keys),
        "csv_snapshot_keys": len(csv_counts),
        "csv_rows": sum(csv_counts.values()),
        "last_session_snapshot_seq": previous_snapshot,
        "hashes_sha256": {key: sha256(path) for key, path in paths.items()},
    }
    return {"verdict": "PASS" if not errors else "FAIL", "errors": errors, "metrics": metrics}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.json_out:
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
