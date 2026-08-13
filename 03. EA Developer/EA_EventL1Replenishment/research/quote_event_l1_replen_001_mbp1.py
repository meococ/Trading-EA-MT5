#!/usr/bin/env python3
"""Free DESIGN-only CME 6E MBP-1 quote for EVENTL1REPLEN001."""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
import time as time_module
from typing import Any, Callable


HYPOTHESIS_ID = "HYP-EVENT-L1-REPLEN-EURUSD-TICK-001"
QUOTE_ID = "EVENTL1REPLEN001-MBP1-DESIGN-FREE-QUOTE-001"
BASE_REL = "03. EA Developer/EA_EventL1Replenishment/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_QUOTE_PLAN.md"
TOOL_REL = BASE_REL + "quote_event_l1_replen_001_mbp1.py"
TEST_REL = BASE_REL + "tests/test_quote_event_l1_replen_001_mbp1.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento/Scripts/python.exe"
CLOCK_REL = (
    "03. EA Developer/EA_EventCLOBPersistence/research/source/"
    "point_release_clocks_2019_2022.csv"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_l1_replen/"
    f"{HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
)

PLAN_SHA256 = "D423A1CFF1CCA1852ACEEDDB83CA86D5700BBB50306CF1E17058A80211E32F11"
CLOCK_SHA256 = "5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B"
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-1"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
COST_MODE = "historical-streaming"
SDK_VERSION = "0.54.0"
WINDOW_SECONDS = 120
EXPECTED_DESIGN_CLOCKS = 329
DESIGN_YEARS = {2019, 2020}
EXPECTED_ELAPSED_WEEKS = 104.428571
MIN_NONZERO_SHARE = 0.95
MIN_CADENCE_PER_WEEK = 2.0

REVIEWED_REGISTRY_ROW_SHA256: str | None = "C5AB262248DAF092B3F363125D83E9E9007AE8DC4BAE401AA3F25BDE8A27CB9D"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = '
    rb'(?:None|"[A-F0-9]{64}")\r?$'
)
_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")


class QuoteError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def normalized_tool_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise QuoteError("tool must contain exactly one registry sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise QuoteError(f"{label} must stay on D:")
    return resolved


def load_design_clocks(path: Path) -> list[dict[str, str]]:
    if sha256_file(path) != CLOCK_SHA256:
        raise QuoteError("event clock ledger hash mismatch")
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            try:
                event_id = str(source["event_clock_id"])
                event_time = datetime.fromisoformat(
                    str(source["event_time_utc"]).replace("Z", "+00:00")
                )
                currencies = str(source["currencies"])
            except (KeyError, TypeError, ValueError) as exc:
                raise QuoteError("invalid event clock row") from exc
            if event_time.tzinfo is None or event_time.utcoffset() != timedelta(0):
                raise QuoteError("event clock must be UTC-aware")
            if event_time.year not in DESIGN_YEARS:
                continue
            if not event_id.startswith("EVT") or not ({"USD", "EUR"} & set(currencies.split("|"))):
                raise QuoteError("DESIGN event identity/currency mismatch")
            rows.append({
                "request_id": event_id,
                "event_clock_id": event_id,
                "split": "DESIGN",
                "event_time_utc": event_time.astimezone(timezone.utc)
                .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            })
    identities = [row["event_clock_id"] for row in rows]
    times = [row["event_time_utc"] for row in rows]
    if (
        len(rows) != EXPECTED_DESIGN_CLOCKS
        or len(set(identities)) != EXPECTED_DESIGN_CLOCKS
        or len(set(times)) != EXPECTED_DESIGN_CLOCKS
        or times != sorted(times)
        or identities[0] != "EVT0001"
    ):
        raise QuoteError("DESIGN event clock population mismatch")
    return rows


def build_window(row: dict[str, str]) -> dict[str, str]:
    start = datetime.fromisoformat(row["event_time_utc"].replace("Z", "+00:00"))
    end = start + timedelta(seconds=WINDOW_SECONDS)
    return {
        **row,
        "start": start.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "end": end.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    }


def _read_user_environment(name: str) -> str | None:
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
    key = os.environ.get("DATABENTO_API_KEY") or _read_user_environment("DATABENTO_API_KEY")
    if not key:
        raise QuoteError("DATABENTO_API_KEY is absent")
    key = key.strip()
    if not _KEY_RE.fullmatch(key):
        raise QuoteError("DATABENTO_API_KEY has an unexpected format")
    return key


def make_client(key: str) -> Any:
    try:
        import databento as db
    except ImportError as exc:
        raise QuoteError("Databento SDK is unavailable") from exc
    if str(getattr(db, "__version__", "")) != SDK_VERSION:
        raise QuoteError("Databento SDK version mismatch")
    return db.Historical(key)


def quote_all(
    client_factory: Callable[[], Any],
    windows: list[dict[str, str]],
    workers: int,
) -> list[dict[str, Any]]:
    if not 1 <= workers <= 16:
        raise QuoteError("workers must be 1..16")
    local = threading.local()

    def one(window: dict[str, str]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = client_factory()
        args = {
            "dataset": DATASET,
            "schema": SCHEMA,
            "symbols": [SYMBOL],
            "stype_in": STYPE_IN,
            "start": window["start"],
            "end": window["end"],
        }
        last: Exception | None = None
        for attempt in range(1, 4):
            try:
                cost = float(local.client.metadata.get_cost(mode=COST_MODE, **args))
                size = int(local.client.metadata.get_billable_size(**args))
                if not math.isfinite(cost) or cost < 0 or size < 0:
                    raise QuoteError("negative/non-finite metadata quote")
                return {**window, "estimated_usd": cost, "billable_bytes": size,
                        "metadata_attempt": attempt}
            except Exception as exc:
                last = exc
                if attempt < 3:
                    time_module.sleep((0.25, 1.0)[attempt - 1])
        raise QuoteError(
            f"metadata quote failed for {window['request_id']}: {type(last).__name__}"
        ) from None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        quotes = list(pool.map(one, windows))
    return sorted(quotes, key=lambda item: item["request_id"])


def validate_authority(workspace: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise QuoteError("registry sentinel is not armed")
    plan = require_d(workspace / PLAN_REL, "plan")
    clock = require_d(workspace / CLOCK_REL, "clock")
    tool = require_d(workspace / TOOL_REL, "tool")
    test = require_d(workspace / TEST_REL, "test")
    registry = require_d(workspace / REGISTRY_REL, "registry")
    if sha256_file(plan) != PLAN_SHA256 or sha256_file(clock) != CLOCK_SHA256:
        raise QuoteError("plan or event-clock hash drift")
    payload = tool.read_bytes()
    tool_base = normalized_tool_base_sha256(payload)
    test_sha = sha256_file(test)
    matches: list[tuple[dict[str, Any], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((row, raw + b"\n"))
    if not matches:
        raise QuoteError("hypothesis absent from candidate registry")
    row, line = matches[-1]
    row_sha = sha256_bytes(line)
    validation = row.get("validation", {})
    expected = {
        "source_quote_plan_sha256": PLAN_SHA256,
        "event_clock_sha256": CLOCK_SHA256,
        "reviewed_quote_tool_base_sha256": tool_base,
        "reviewed_quote_test_sha256": test_sha,
    }
    if (
        row_sha != REVIEWED_REGISTRY_ROW_SHA256
        or row.get("state") != "probe"
        or row.get("prereg_sha256") != PLAN_SHA256
        or validation.get("source_quote_authorized") is not True
    ):
        raise QuoteError("registry source-quote authority mismatch")
    for key, value in expected.items():
        if validation.get(key) != value:
            raise QuoteError(f"registry binding mismatch: {key}")
    for key in (
        "paid_acquisition_authorized", "source_download_authorized",
        "economics_authorized", "outcome_prices_authorized", "mql5_authorized",
        "model0_authorized", "research_validation_access_authorized",
        "research_holdout_access_authorized", "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise QuoteError(f"forbidden authority open: {key}")
    if QUOTE_ID in row.get("run_ids", []):
        raise QuoteError("free quote attempt already consumed")
    return {
        "registry_row_sha256": row_sha,
        "tool_base_sha256": tool_base,
        "tool_file_sha256": sha256_bytes(payload),
        "test_sha256": test_sha,
    }


def execute(workspace: Path, workers: int) -> Path:
    workspace = require_d(workspace, "workspace")
    runtime = require_d(workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise QuoteError("wrong Python runtime")
    if importlib.metadata.version("databento") != SDK_VERSION:
        raise QuoteError("Databento SDK version mismatch")
    authority = validate_authority(workspace)
    clocks = load_design_clocks(require_d(workspace / CLOCK_REL, "clock"))
    windows = [build_window(row) for row in clocks]
    key = load_api_key()
    quotes = quote_all(lambda: make_client(key), windows, workers)
    total_usd = float(sum(float(item["estimated_usd"]) for item in quotes))
    total_bytes = int(sum(int(item["billable_bytes"]) for item in quotes))
    nonzero = sum(int(item["billable_bytes"]) > 0 for item in quotes)
    nonzero_share = nonzero / len(quotes)
    cadence = nonzero / EXPECTED_ELAPSED_WEEKS
    gates = {
        "all_329_metadata_quotes_valid": len(quotes) == EXPECTED_DESIGN_CLOCKS,
        "nonzero_billable_share_at_least_0_95": nonzero_share >= MIN_NONZERO_SHARE,
        "nonzero_cadence_at_least_2_per_week": cadence >= MIN_CADENCE_PER_WEEK,
    }
    receipt = {
        "schema_version": "event_l1_replen_001_mbp1_design_free_quote.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "quote_id": QUOTE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "FREE_DESIGN_MBP1_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST",
        "dataset": DATASET, "schema": SCHEMA, "symbol": SYMBOL,
        "stype_in": STYPE_IN, "cost_mode": COST_MODE,
        "request_window": "[event_time_utc,event_time_utc+120s)",
        "window_seconds": WINDOW_SECONDS, "split": "DESIGN_2019_2020",
        "request_count": len(quotes), "estimated_total_usd": total_usd,
        "estimated_total_billable_bytes": total_bytes,
        "nonzero_billable_request_count": nonzero,
        "nonzero_billable_request_share": nonzero_share,
        "estimated_nonzero_cadence_per_week": cadence,
        "source_frontier_gates": gates,
        "source_frontier_gate_pass": all(gates.values()),
        "frozen_pilot_identity": "EVT0001",
        "quotes": quotes,
        "bindings": {"plan_sha256": PLAN_SHA256, "event_clock_sha256": CLOCK_SHA256, **authority},
        "api_method_counters": {
            "metadata.get_cost": sum(int(item["metadata_attempt"]) for item in quotes),
            "metadata.get_billable_size": len(quotes), "timeseries.get_range": 0,
            "batch.submit_job": 0, "batch.download": 0,
        },
        "paid_request_made": False, "price_data_read": False,
        "source_payload_read": False, "outcome_fields_used": [],
        "validation_source_quoted": False, "validation_source_read": False,
        "economics_authorized": False, "mql5_authorized": False,
        "model0_authorized": False,
    }
    output = require_d(workspace / OUTPUT_REL, "quote output")
    if output.exists() or output.parent.exists():
        raise QuoteError("exclusive quote output root already exists")
    output.parent.mkdir(parents=True, exist_ok=False)
    with output.open("xb") as handle:
        handle.write(canonical_json(receipt) + b"\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    try:
        output = execute(args.workspace.resolve(), args.workers)
        receipt = json.loads(output.read_text(encoding="ascii"))
        print(
            "EVENTL1REPLEN001_MBP1_FREE_QUOTE_OK "
            f"requests={receipt['request_count']} "
            f"nonzero={receipt['nonzero_billable_request_count']} "
            f"estimated_usd={receipt['estimated_total_usd']:.12f} "
            f"bytes={receipt['estimated_total_billable_bytes']} "
            f"gate_pass={str(receipt['source_frontier_gate_pass']).lower()} paid=0"
        )
        print(f"RECEIPT {output}")
        return 0
    except QuoteError as exc:
        print(f"EVENTL1REPLEN001_MBP1_FREE_QUOTE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
