#!/usr/bin/env python3
"""Free metadata quote for the 329-event MBP-10 depth-transfer DESIGN set."""

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
import time
from typing import Any, Callable


HYPOTHESIS_ID = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-003"
QUOTE_ID = "EVENTDEPTHTRANSFER003-MBP10-DESIGN-FREE-QUOTE-001"
BASE_REL = "03. EA Developer/EA_EventDepthTransfer/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_DESIGN_QUOTE_PLAN.md"
TOOL_REL = BASE_REL + "quote_event_depth_transfer_003_design.py"
TEST_REL = BASE_REL + "tests/test_quote_event_depth_transfer_003_design.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
CLOCK_REL = (
    "03. EA Developer/EA_EventCLOBPersistence/research/source/"
    "point_release_clocks_2019_2022.csv"
)
PILOT_RECEIPT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-002/"
    "EVENTDEPTHTRANSFER002-MBP10-PILOT-001/pilot_acquisition_receipt.json"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    f"{HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
)
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
COST_MODE = "historical-streaming"
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
CLOCK_SHA256 = "5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B"
PILOT_RECEIPT_SHA256 = "ADE357CAD391B5FA274BE99CE55454BC8CE2AD753D3EBCAEA8F30423345D83F5"
DESIGN_YEARS = {2019, 2020}
EXPECTED_CLOCKS = 329
WINDOW_SECONDS = 60
MAX_EVENT_USD = 0.02
MAX_AGGREGATE_USD = 10.0
MIN_NONZERO_SHARE = 0.95
_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")


class QuoteError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_workspace_path(workspace: Path, path: Path, label: str) -> Path:
    root = workspace.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise QuoteError(f"{label} escapes workspace") from exc
    if root.drive.upper() != "D:" or resolved.drive.upper() != "D:":
        raise QuoteError(f"{label} must stay on D:")
    return resolved


def read_design_clocks(path: Path) -> list[dict[str, str]]:
    if sha256_file(path) != CLOCK_SHA256:
        raise QuoteError("event clock ledger hash mismatch")
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            stamp = datetime.fromisoformat(source["event_time_utc"].replace("Z", "+00:00"))
            if stamp.year not in DESIGN_YEARS:
                continue
            if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
                raise QuoteError("event clock must be UTC")
            rows.append({
                "event_clock_id": source["event_clock_id"],
                "event_time_utc": stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            })
    identities = [row["event_clock_id"] for row in rows]
    clocks = [row["event_time_utc"] for row in rows]
    if (
        len(rows) != EXPECTED_CLOCKS or len(set(identities)) != EXPECTED_CLOCKS
        or len(set(clocks)) != EXPECTED_CLOCKS or clocks != sorted(clocks)
        or identities[0] != "EVT0001"
    ):
        raise QuoteError("DESIGN clock population mismatch")
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


def client_factory(key: str) -> Callable[[], Any]:
    try:
        import databento as db
    except ImportError as exc:
        raise QuoteError("Databento SDK is unavailable") from exc
    if str(getattr(db, "__version__", "")) != SDK_VERSION:
        raise QuoteError("Databento SDK version mismatch")
    return lambda: db.Historical(key)


def request_args(window: dict[str, str]) -> dict[str, Any]:
    return {
        "dataset": DATASET, "schema": SCHEMA, "symbols": [SYMBOL],
        "stype_in": STYPE_IN, "start": window["start"], "end": window["end"],
    }


def quote_all(factory: Callable[[], Any], windows: list[dict[str, str]],
              workers: int) -> list[dict[str, Any]]:
    if not 1 <= workers <= 16:
        raise QuoteError("workers must be 1..16")
    local = threading.local()

    def quote_one(window: dict[str, str]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = factory()
        args = request_args(window)
        last: Exception | None = None
        for attempt in range(1, 4):
            try:
                cost = float(local.client.metadata.get_cost(mode=COST_MODE, **args))
                size = int(local.client.metadata.get_billable_size(**args))
                if not math.isfinite(cost) or cost < 0 or size < 0:
                    raise QuoteError("invalid metadata quote")
                return {**window, "estimated_usd": cost, "billable_bytes": size,
                        "metadata_attempt": attempt}
            except Exception as exc:
                last = exc
                if attempt < 3:
                    time.sleep((0.25, 1.0)[attempt - 1])
        raise QuoteError(
            f"metadata quote failed for {window['event_clock_id']}: {type(last).__name__}"
        ) from None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        quotes = list(pool.map(quote_one, windows))
    return sorted(quotes, key=lambda item: item["event_time_utc"])


def summarize(quotes: list[dict[str, Any]]) -> dict[str, Any]:
    costs = [float(item["estimated_usd"]) for item in quotes]
    sizes = [int(item["billable_bytes"]) for item in quotes]
    total = sum(costs)
    nonzero_share = sum(cost > 0 for cost in costs) / len(costs) if costs else 0.0
    gates = {
        "exact_329_quotes": len(quotes) == EXPECTED_CLOCKS,
        "unique_event_ids": len({item["event_clock_id"] for item in quotes}) == EXPECTED_CLOCKS,
        "positive_billable_bytes": bool(sizes) and min(sizes) > 0,
        "nonnegative_finite_cost": bool(costs) and all(math.isfinite(x) and x >= 0 for x in costs),
        "nonzero_quote_share_at_least_95pct": nonzero_share >= MIN_NONZERO_SHARE,
        "max_event_quote_at_most_0_02": bool(costs) and max(costs) <= MAX_EVENT_USD,
        "aggregate_quote_strictly_below_10": total < MAX_AGGREGATE_USD,
    }
    return {
        "event_count": len(quotes), "aggregate_estimated_usd": total,
        "min_event_estimated_usd": min(costs) if costs else None,
        "max_event_estimated_usd": max(costs) if costs else None,
        "aggregate_billable_bytes": sum(sizes),
        "min_event_billable_bytes": min(sizes) if sizes else None,
        "max_event_billable_bytes": max(sizes) if sizes else None,
        "nonzero_quote_share": nonzero_share,
        "max_metadata_attempt": max((item["metadata_attempt"] for item in quotes), default=0),
        "gates": gates, "gate_pass": all(gates.values()),
        "verdict": "PASS_DESIGN_SOURCE_QUOTE" if all(gates.values()) else "PARK_DESIGN_SOURCE_QUOTE",
    }


def validate_registry(workspace: Path) -> dict[str, str]:
    paths = {
        "plan_sha256": workspace / PLAN_REL,
        "tool_sha256": workspace / TOOL_REL,
        "test_sha256": workspace / TEST_REL,
        "pilot_receipt_sha256": workspace / PILOT_RECEIPT_REL,
    }
    hashes = {key: sha256_file(require_workspace_path(workspace, path, key))
              for key, path in paths.items()}
    if hashes["pilot_receipt_sha256"] != PILOT_RECEIPT_SHA256:
        raise QuoteError("pilot receipt drifted")
    registry = require_workspace_path(workspace, workspace / REGISTRY_REL, "registry")
    matches = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append(row)
    if not matches:
        raise QuoteError("hypothesis absent from registry")
    row = matches[-1]
    validation = row.get("validation", {})
    if (
        row.get("state") != "probe" or row.get("prereg_sha256") != hashes["plan_sha256"]
        or validation.get("metadata_quote_authorized") is not True
        or validation.get("reviewed_quote_tool_sha256") != hashes["tool_sha256"]
        or validation.get("reviewed_quote_test_sha256") != hashes["test_sha256"]
        or validation.get("pilot_receipt_sha256") != hashes["pilot_receipt_sha256"]
        or validation.get("paid_acquisition_authorized") is not False
        or validation.get("source_download_authorized") is not False
        or validation.get("outcome_prices_authorized") is not False
        or validation.get("economics_authorized") is not False
    ):
        raise QuoteError("registry quote authority mismatch")
    return hashes


def execute(workspace: Path, workers: int) -> Path:
    workspace = workspace.resolve()
    runtime = require_workspace_path(workspace, workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise QuoteError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise QuoteError("Databento runtime mismatch")
    bindings = validate_registry(workspace)
    clocks = read_design_clocks(
        require_workspace_path(workspace, workspace / CLOCK_REL, "clock ledger")
    )
    windows = [build_window(row) for row in clocks]
    quotes = quote_all(client_factory(load_api_key()), windows, workers)
    summary = summarize(quotes)
    output = require_workspace_path(workspace, workspace / OUTPUT_REL, "quote output")
    if output.exists():
        raise QuoteError("exclusive quote receipt already exists")
    output.parent.mkdir(parents=True, exist_ok=False)
    receipt = {
        "schema_version": "event_depth_transfer_003_design_quote.v1",
        "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
        "quote_id": QUOTE_ID, "dataset": DATASET, "schema": SCHEMA,
        "symbol": SYMBOL, "stype_in": STYPE_IN, "clock": "ts_recv",
        "window_seconds": WINDOW_SECONDS, "split": "DESIGN",
        "design_years": sorted(DESIGN_YEARS), "quotes": quotes, "summary": summary,
        "bindings": {**bindings, "clock_sha256": CLOCK_SHA256},
        "metadata_only": True, "paid_timeseries_calls": 0, "batch_calls": 0,
        "source_payload_read": False, "outcome_prices_read": False,
        "returns_computed": 0, "trades_simulated": 0,
        "purchase_authorized": False, "economics_authorized": False,
    }
    temp = output.with_suffix(output.suffix + ".tmp")
    with temp.open("xb") as handle:
        handle.write(canonical_json(receipt) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    try:
        path = execute(args.workspace.resolve(), args.workers)
        receipt = json.loads(path.read_text(encoding="ascii"))
        summary = receipt["summary"]
        print(
            "EVENT_DEPTH_TRANSFER_003_QUOTE_OK "
            f"events={summary['event_count']} cost={summary['aggregate_estimated_usd']:.12f} "
            f"verdict={summary['verdict']}"
        )
        print(f"RECEIPT {path}")
        return 0
    except QuoteError as exc:
        print(f"EVENT_DEPTH_TRANSFER_003_QUOTE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

