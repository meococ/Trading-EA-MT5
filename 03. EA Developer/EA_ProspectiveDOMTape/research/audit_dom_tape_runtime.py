#!/usr/bin/env python3
"""Fail-closed runtime auditor for EA_ProspectiveDOMTape artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY")
REQUIRED_FILES = ("dom_tape_v1.jsonl", "dom_levels_v1.csv", "dom_state_v1.txt")
FATAL_KINDS = {"API_ERROR_BOOK", "IO_ERROR", "TICK64_REGRESS", "EMPTY_BOOK"}
SAFETY = {
    "schema_version": "1",
    "collector_version": "1.0.0",
    "recv_clock": "terminal_observation_not_official_first_public",
    "outcome_accessed": False,
    "prices_read": False,
    "orders": False,
    "trading_disabled": True,
}


def _error(errors: list[str], code: str, detail: str = "") -> None:
    errors.append(code if not detail else f"{code}: {detail}")


def audit(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    paths = {name: root / name for name in REQUIRED_FILES}
    for name, path in paths.items():
        if not path.is_file() or path.stat().st_size == 0:
            _error(errors, "MISSING_OR_EMPTY_FILE", name)
    if errors:
        return {"verdict": "FAIL", "errors": errors, "warnings": warnings}

    records: list[dict[str, Any]] = []
    with paths["dom_tape_v1.jsonl"].open("r", encoding="utf-8-sig") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                _error(errors, "JSON_DECODE", f"line={line_no} {exc}")
                continue
            if not isinstance(obj, dict):
                _error(errors, "JSON_NOT_OBJECT", f"line={line_no}")
                continue
            records.append(obj)

    if not records:
        _error(errors, "NO_JSON_RECORDS")
        return {"verdict": "FAIL", "errors": errors, "warnings": warnings}

    kinds = Counter(str(r.get("kind", "")) for r in records)
    fatal_seen = sorted(k for k in FATAL_KINDS if kinds[k])
    if fatal_seen:
        _error(errors, "FATAL_RECORDS", ",".join(fatal_seen))

    for index, record in enumerate(records, 1):
        for key, expected in SAFETY.items():
            if record.get(key) != expected:
                _error(errors, "SAFETY_FIELD", f"record={index} {key}={record.get(key)!r}")
        if not isinstance(record.get("terminal_build"), int) or record["terminal_build"] <= 0:
            _error(errors, "TERMINAL_BUILD", f"record={index}")
        if not record.get("account_server"):
            _error(errors, "ACCOUNT_SERVER", f"record={index}")

    init_indexes = [i for i, r in enumerate(records) if r.get("kind") == "INIT"]
    if not init_indexes:
        _error(errors, "NO_INIT_RECEIPT")
        session_start = 0
    else:
        init_index = init_indexes[-1]
        session_start = max([i + 1 for i in range(init_index) if records[i].get("kind") == "SHUTDOWN"] or [0])
        init = records[init_index]
        if tuple(init.get("symbols", [])) != SYMBOLS:
            _error(errors, "INIT_SYMBOLS", repr(init.get("symbols")))
        subscriptions = [
            r.get("symbol")
            for r in records[session_start : init_index + 1]
            if r.get("kind") == "SUBSCRIBE"
        ]
        if tuple(subscriptions[-4:]) != SYMBOLS:
            _error(errors, "SUBSCRIBE_COVERAGE", repr(subscriptions[-4:]))

    session = records[session_start:]
    snapshots = [r for r in session if r.get("kind") == "SNAPSHOT"]
    by_symbol = Counter(str(r.get("symbol", "")) for r in snapshots)
    for symbol in SYMBOLS:
        if by_symbol[symbol] < 1:
            _error(errors, "NO_SNAPSHOT", symbol)

    previous_tick: int | None = None
    previous_snapshot_seq: int | None = None
    previous_event: dict[str, int] = {}
    json_keys: dict[tuple[str, int, int, str], int] = {}
    for index, record in enumerate(session, 1):
        tick = record.get("tick64")
        if not isinstance(tick, int) or tick < 0:
            _error(errors, "INVALID_TICK64", f"session_record={index}")
        elif previous_tick is not None and tick < previous_tick:
            _error(errors, "GLOBAL_TICK64_REGRESSION", f"{previous_tick}->{tick}")
        if isinstance(tick, int):
            previous_tick = tick

        symbol = record.get("symbol")
        event_seq = record.get("event_seq")
        if symbol in SYMBOLS and isinstance(event_seq, int):
            if symbol in previous_event and event_seq <= previous_event[symbol]:
                _error(errors, "EVENT_SEQ_NOT_STRICT", f"{symbol} {previous_event[symbol]}->{event_seq}")
            previous_event[symbol] = event_seq

        if record.get("kind") != "SNAPSHOT":
            continue
        snap_seq = record.get("snapshot_seq")
        depth = record.get("depth")
        levels = record.get("levels")
        if not isinstance(snap_seq, int) or snap_seq <= 0:
            _error(errors, "INVALID_SNAPSHOT_SEQ", f"session_record={index}")
            continue
        if previous_snapshot_seq is not None and snap_seq <= previous_snapshot_seq:
            _error(errors, "SNAPSHOT_SEQ_NOT_STRICT", f"{previous_snapshot_seq}->{snap_seq}")
        previous_snapshot_seq = snap_seq
        if not isinstance(depth, int) or depth <= 0 or not isinstance(levels, list) or len(levels) != depth:
            _error(errors, "DEPTH_LEVEL_MISMATCH", f"snapshot_seq={snap_seq}")
            continue
        for level_index, level in enumerate(levels):
            if level.get("i") != level_index or level.get("type") not in (1, 2):
                _error(errors, "INVALID_LEVEL", f"snapshot_seq={snap_seq} i={level_index}")
            if not isinstance(level.get("price"), (int, float)) or level["price"] <= 0:
                _error(errors, "INVALID_PRICE", f"snapshot_seq={snap_seq} i={level_index}")
        key = (str(symbol), int(event_seq), snap_seq, str(record.get("payload_hash")))
        if key in json_keys:
            _error(errors, "DUPLICATE_JSON_KEY", repr(key))
        json_keys[key] = depth

    csv_counts: Counter[tuple[str, int, int, str]] = Counter()
    csv_level_indexes: dict[tuple[str, int, int, str], set[int]] = defaultdict(set)
    with paths["dom_levels_v1.csv"].open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {
            "kind", "ts_local", "ts_server", "ts_current", "tick64", "symbol",
            "event_seq", "snapshot_seq", "payload_hash", "depth", "level_index",
            "type", "price", "volume", "volume_real", "recv_clock",
        }
        if set(reader.fieldnames or ()) != expected:
            _error(errors, "CSV_HEADER", repr(reader.fieldnames))
        for row_no, row in enumerate(reader, 2):
            try:
                key = (
                    row["symbol"], int(row["event_seq"]), int(row["snapshot_seq"]), row["payload_hash"]
                )
                csv_counts[key] += 1
                csv_level_indexes[key].add(int(row["level_index"]))
                if row["kind"] != "SNAPSHOT" or row["recv_clock"] != SAFETY["recv_clock"]:
                    _error(errors, "CSV_SAFETY", f"row={row_no}")
            except (KeyError, TypeError, ValueError) as exc:
                _error(errors, "CSV_PARSE", f"row={row_no} {exc}")

    for key, depth in json_keys.items():
        if csv_counts[key] != depth:
            _error(errors, "CSV_JSON_COUNT", f"key={key!r} csv={csv_counts[key]} json={depth}")
        if csv_level_indexes[key] != set(range(depth)):
            _error(errors, "CSV_LEVEL_INDEX", repr(key))
    extra_csv = set(csv_counts) - set(json_keys)
    if extra_csv:
        _error(errors, "CSV_WITHOUT_JSON", f"count={len(extra_csv)}")

    state_lines = paths["dom_state_v1.txt"].read_text(encoding="utf-8-sig").splitlines()
    state_map: dict[str, str] = {}
    state_symbols: dict[str, list[str]] = {}
    for line in state_lines:
        if line.startswith("S\t"):
            fields = line.split("\t")
            if len(fields) != 9:
                _error(errors, "STATE_SYMBOL_FIELDS", line)
            else:
                state_symbols[fields[1]] = fields
        elif "=" in line:
            key, value = line.split("=", 1)
            if key in state_map:
                _error(errors, "STATE_DUPLICATE_KEY", key)
            state_map[key] = value
    if state_map.get("schema") != "1" or state_map.get("version") != "1.0.0":
        _error(errors, "STATE_VERSION")
    if state_map.get("symbols") != ",".join(SYMBOLS):
        _error(errors, "STATE_SYMBOL_LIST", repr(state_map.get("symbols")))
    if set(state_symbols) != set(SYMBOLS):
        _error(errors, "STATE_SYMBOL_ROWS", repr(sorted(state_symbols)))
    for key in ("snapshot_seq", "events", "snapshots", "duplicates", "empty", "api_errors", "io_errors"):
        try:
            if int(state_map[key]) < 0:
                raise ValueError
        except (KeyError, ValueError):
            _error(errors, "STATE_COUNTER", key)
    try:
        if int(state_map.get("empty", "-1")) != 0 or int(state_map.get("api_errors", "-1")) != 0 or int(state_map.get("io_errors", "-1")) != 0:
            _error(errors, "STATE_FATAL_COUNTERS")
    except ValueError:
        pass

    heartbeat_ok = any(
        r.get("kind") == "HEARTBEAT"
        and {x.get("symbol") for x in r.get("symbols", []) if x.get("subscribed") is True} == set(SYMBOLS)
        for r in session
    )
    if not heartbeat_ok:
        _error(errors, "NO_ALL_SUBSCRIBED_HEARTBEAT")

    metrics = {
        "records": len(records),
        "session_records": len(session),
        "kind_counts": dict(sorted(kinds.items())),
        "snapshots_by_symbol": {s: by_symbol[s] for s in SYMBOLS},
        "json_snapshots": len(json_keys),
        "csv_snapshot_keys": len(csv_counts),
        "csv_rows": sum(csv_counts.values()),
        "last_snapshot_seq": previous_snapshot_seq,
    }
    return {
        "verdict": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


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
