#!/usr/bin/env python3
"""Fetch the official Q1-2019 GLBX.MDP3 dataset-condition tape only."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


HYPOTHESIS_ID = "HYP-GC-OFI-INNOV-XAU-M5-003"
PROBE_ID = "GCOFI003-Q1-2019-DATASET-CONDITION-001"
DATASET = "GLBX.MDP3"
START_DATE = "2019-01-01"
END_DATE = "2019-04-01"
SDK_VERSION = "0.55.1"

BASE_REL = "03. EA Developer/EA_GCOrderFlowInnovation/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_CONDITION_PREREG.md"
REVIEW_REL = BASE_REL + HYPOTHESIS_ID + "_GROK_V3_REDTEAM_RECEIPT.md"
TOOL_REL = BASE_REL + "probe_gc_dataset_condition_003.py"
TEST_REL = BASE_REL + "tests/test_probe_gc_dataset_condition_003.py"
TBBO_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-001/GCOFI001-Q1-2019-SOURCE-PILOT-001/raw/tbbo.dbn.zst"
)
DEFINITION_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-002/GCOFI002-Q1-2019-REF-SOURCE-001/raw/definition.dbn.zst"
)
STATUS_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-002/GCOFI002-Q1-2019-REF-SOURCE-001/raw/status.dbn.zst"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    f"{HYPOTHESIS_ID}/{PROBE_ID}/dataset_condition_receipt.json"
)

EXPECTED_HASHES = {
    TBBO_REL: "6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB",
    DEFINITION_REL: "F3D611000866D8ACB45CB9636307410F91674EDB1B1609B9F4BB867CE5E144CB",
    STATUS_REL: "B20CE73170247CADF96179137D9729EBBC771B3DD831019CFFA2E0951B6D59BE",
}

_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")


class ConditionError(RuntimeError):
    pass


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical_json(value) + b"\n")
    os.replace(tmp, path)


def read_user_environment(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except (FileNotFoundError, OSError):
        return None


def load_api_key() -> str:
    key = os.environ.get("DATABENTO_API_KEY") or read_user_environment("DATABENTO_API_KEY")
    if not key or not _KEY_RE.fullmatch(key.strip()):
        raise ConditionError("DATABENTO_API_KEY missing or invalid")
    return key.strip()


def make_client(key: str) -> Any:
    try:
        import databento as db
    except ImportError as exc:
        raise ConditionError("Databento SDK unavailable") from exc
    if str(getattr(db, "__version__", "")) != SDK_VERSION:
        raise ConditionError("Databento SDK version mismatch")
    return db.Historical(key)


def validate_conditions(rows: object) -> list[dict[str, str]]:
    if not isinstance(rows, list) or not rows:
        raise ConditionError("empty dataset-condition response")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ConditionError("malformed dataset-condition row")
        date = str(item.get("date", ""))
        condition = str(item.get("condition", "")).lower()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not condition:
            raise ConditionError("missing date/condition field")
        if date in seen:
            raise ConditionError(f"duplicate condition date: {date}")
        seen.add(date)
        normalized.append({str(k): str(v) for k, v in sorted(item.items())})
    return normalized


def execute(workspace: Path, client: Any | None = None) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise ConditionError("workspace must stay on D:")
    bound = {
        "condition_prereg_sha256": workspace / PLAN_REL,
        "grok_v3_review_sha256": workspace / REVIEW_REL,
        "tool_sha256": workspace / TOOL_REL,
        "test_sha256": workspace / TEST_REL,
    }
    for label, path in bound.items():
        if not path.is_file():
            raise ConditionError(f"missing bound artifact: {label}")
    for relative, expected in EXPECTED_HASHES.items():
        path = workspace / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise ConditionError(f"source payload drift: {relative}")
    if client is None:
        client = make_client(load_api_key())
    rows = validate_conditions(
        client.metadata.get_dataset_condition(
            dataset=DATASET, start_date=START_DATE, end_date=END_DATE
        )
    )
    receipt = {
        "schema_version": "gc_order_flow_innovation_dataset_condition.v1",
        "created_at_utc": utc_now(),
        "status": "OFFICIAL_DATASET_CONDITION_CAPTURED_NO_AGGREGATE_SOURCE_READOUT",
        "hypothesis_id": HYPOTHESIS_ID,
        "probe_id": PROBE_ID,
        "dataset": DATASET,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "conditions": rows,
        "bindings": {label: sha256_file(path) for label, path in bound.items()},
        "source_payload_hashes": EXPECTED_HASHES,
        "api_method_counters": {
            "metadata.get_dataset_condition": 1,
            "timeseries.get_range": 0,
            "batch.submit_job": 0,
        },
        "tbbo_aggregate_read": False,
        "abn_counts_read": False,
        "event_cadence_read": False,
        "xauusd_outcome_read": False,
        "economics_executed": False,
    }
    output = workspace / OUTPUT_REL
    if output.exists():
        raise ConditionError("same-ID condition receipt already exists")
    write_json_atomic(output, receipt)
    return output


def main() -> int:
    try:
        output = execute(workspace_from_source())
        receipt = json.loads(output.read_text(encoding="ascii"))
        print(f"GCOFI003_CONDITION_OK rows={len(receipt['conditions'])}")
        print(f"RECEIPT {output}")
        return 0
    except ConditionError as exc:
        print(f"GCOFI003_CONDITION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
