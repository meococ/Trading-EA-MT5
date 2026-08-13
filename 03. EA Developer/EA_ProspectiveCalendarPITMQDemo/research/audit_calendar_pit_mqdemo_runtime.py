from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-CALENDAR-PIT-MQDEMO-001"
EXPECTED_SERVER = "MetaQuotes-Demo"
REQUIRED_CURRENCIES = {"USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"}
PAIR_FIELDS = ("event_id", "value_id", "scheduled_unix", "period_unix", "payload_hash")
FATAL_PREFIXES = ("API_ERROR", "GAP_", "STATE_", "IO_ERROR", "CAPACITY_")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"non-object JSONL at line {line_number}")
            records.append(record)
    if not records:
        raise ValueError("empty runtime JSONL")
    return records


def audit(path: Path) -> dict[str, Any]:
    records = _load(path)
    kinds = [str(record.get("kind", "")) for record in records]
    currencies = {
        str(record.get("currency"))
        for record in records
        if record.get("kind") == "DISCOVERY_EVENT_DEFS"
    }
    frozen = [record for record in records if record.get("kind") == "CATALOG_FROZEN"]
    future = [record for record in records if record.get("kind") == "FUTURE_DISCOVERY_HISTORY"]
    idle = [record for record in records if record.get("kind") == "IDLE_PROOF_HISTORY"]
    fatal_indexes = [
        index
        for index, kind in enumerate(kinds)
        if any(kind.startswith(prefix) for prefix in FATAL_PREFIXES)
    ]
    shutdown_indexes = [index for index, kind in enumerate(kinds) if kind == "SHUTDOWN"]

    matching_pair: dict[str, Any] | None = None
    for first in future:
        for second in idle:
            if all(first.get(field) == second.get(field) for field in PAIR_FIELDS):
                matching_pair = {field: first.get(field) for field in PAIR_FIELDS}
                break
        if matching_pair is not None:
            break

    safety_ok = all(
        record.get("hypothesis_id") == HYPOTHESIS_ID
        and record.get("expected_server") == EXPECTED_SERVER
        and record.get("account_server") == EXPECTED_SERVER
        and record.get("outcome_accessed") is False
        and record.get("prices_read") is False
        and record.get("orders") is False
        and record.get("trading_disabled") is True
        for record in records
    )
    catalog_ok = currencies == REQUIRED_CURRENCIES and bool(frozen)
    fatal_free = not fatal_indexes
    pair_ok = matching_pair is not None
    accepted = safety_ok and catalog_ok and fatal_free and pair_ok

    if fatal_indexes:
        verdict = "KILL_MQDEMO_CAPABILITY_CHILD"
    elif accepted:
        verdict = "ADMISSIBLE_MQDEMO_CAPABILITY_CHILD"
    else:
        verdict = "INCOMPLETE_PROSPECTIVE_SAMPLE"

    first_fatal = fatal_indexes[0] if fatal_indexes else None
    first_shutdown_after_fatal = (
        next((index for index in shutdown_indexes if first_fatal is not None and index > first_fatal), None)
        if first_fatal is not None
        else None
    )
    stop_contract_met = (
        first_fatal is None
        or (
            len(fatal_indexes) == 1
            and first_shutdown_after_fatal == first_fatal + 1
        )
    )

    return {
        "schema_version": "calendar_pit_mqdemo_runtime_audit.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "input_path": str(path.resolve()),
        "input_sha256": _sha256(path),
        "record_count": len(records),
        "kind_counts": {kind: kinds.count(kind) for kind in sorted(set(kinds))},
        "currencies_discovered": sorted(currencies),
        "catalog": frozen[-1] if frozen else None,
        "matching_pair": matching_pair,
        "fatal_records": [records[index] for index in fatal_indexes],
        "shutdown": records[shutdown_indexes[-1]] if shutdown_indexes else None,
        "checks": {
            "safety_fields_exact": safety_ok,
            "currencies_8_of_8_and_catalog_frozen": catalog_ok,
            "future_then_idle_same_occurrence": pair_ok,
            "fatal_error_free": fatal_free,
            "stop_after_first_fatal": stop_contract_met,
        },
        "verdict": verdict,
        "economic_claims_authorized": False,
        "promotion_authorized": False,
    }


def main() -> int:
    common_root = Path(
        os.environ.get(
            "MT5_COMMON_FILES_ROOT",
            r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files",
        )
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=common_root / "calendar_pit_mqdemo_001" / "calendar_pit_mqdemo001.jsonl",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.input)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["verdict"] == "ADMISSIBLE_MQDEMO_CAPABILITY_CHILD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
