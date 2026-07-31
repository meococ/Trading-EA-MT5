#!/usr/bin/env python3
"""Free metadata-only full-history quote for HYP-EURFXOFI-EURUSD-M1-003."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import threading
import time as time_module
from typing import Any
from zoneinfo import ZoneInfo


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-003"
QUOTE_ID = "EURFXOFI003-FREE-METADATA-QUOTE-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-003_SOURCE_QUOTE_PLAN.md"
TOOL_REL = BASE_REL + "quote_eurfxofi_cme6e_003.py"
TEST_REL = BASE_REL + "tests/test_quote_eurfxofi_cme6e_003.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
SELECTION_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-002/EURFXOFI002-SIGNAL-DATE-SELECTION-001"
)
LEDGER_REL = SELECTION_ROOT_REL + "/signal_dates.jsonl"
SELECTION_RECEIPT_REL = SELECTION_ROOT_REL + "/signal_date_selection_receipt.json"
FOUNDATION_REL = "03. EA Developer/EA_SweepCascadeContinuation/research/acquire_cme6e_mbp10_windows.py"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento/Scripts/python.exe"
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    f"{HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
)

PLAN_SHA256 = "9F63A20AE663128250956CE841BEFC2859A7885FFCE45BFDA4244AC1E1B32A06"
LEDGER_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
SELECTION_RECEIPT_SHA256 = "002601D91057392BAD61B0868E235F5D76918F7C92FEFE98C231AC71547B6398"
FOUNDATION_SHA256 = "1F7E38F8326743206CEDE0AE3AEA8760B6C1C4590E4DD7D7E544058CB5A8E78A"

EXPECTED_DATES = 1359
EXPECTED_SPLITS = {"TRAIN": 630, "VALIDATION": 526, "HOLDOUT": 203}
OWNER_CEILING_USD = 2.25
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
COST_MODE = "historical-streaming"
SDK_VERSION = "0.54.0"
WINDOW_SECONDS = 15
BERLIN = ZoneInfo("Europe/Berlin")

REVIEWED_REGISTRY_ROW_SHA256: str | None = "1B759603AE51B23FB1830161938898613709B0ABB9ED6970D0BEBD2605FAF689"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class QuoteError(RuntimeError):
    """Fail-closed metadata quote error; never a paid or economic result."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def normalized_tool_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise QuoteError("tool must contain exactly one valid registry sentinel")
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


def load_dates(path: Path) -> list[dict[str, str]]:
    if sha256_file(path) != LEDGER_SHA256:
        raise QuoteError("signal-date ledger hash mismatch")
    rows: list[dict[str, str]] = []
    for raw in path.read_bytes().splitlines():
        try:
            source = json.loads(raw)
            row = {
                "request_id": str(source["request_id"]),
                "local_date": str(source["local_date"]),
                "split": str(source["split"]),
            }
            datetime.strptime(row["local_date"], "%Y-%m-%d")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise QuoteError("invalid signal-date row") from exc
        if row["request_id"] != f"ECBFX-{row['local_date']}":
            raise QuoteError("signal-date request identity mismatch")
        rows.append(row)
    dates = [row["local_date"] for row in rows]
    if len(rows) != EXPECTED_DATES or len(set(dates)) != EXPECTED_DATES or dates != sorted(dates):
        raise QuoteError("signal-date population mismatch")
    counts = {name: sum(row["split"] == name for row in rows) for name in EXPECTED_SPLITS}
    if counts != EXPECTED_SPLITS:
        raise QuoteError("signal-date split counts mismatch")
    return rows


def build_window(row: dict[str, str]) -> dict[str, str]:
    day = datetime.strptime(row["local_date"], "%Y-%m-%d").date()
    end_local = datetime.combine(day, time(14, 15), tzinfo=BERLIN)
    start_local = end_local - timedelta(seconds=WINDOW_SECONDS)
    start = start_local.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    end = end_local.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {**row, "start": start, "end": end}


def load_foundation(path: Path) -> Any:
    if sha256_file(path) != FOUNDATION_SHA256:
        raise QuoteError("foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi003_quote_foundation", path)
    if spec is None or spec.loader is None:
        raise QuoteError("cannot load acquisition foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def quote_all(
    client_factory: Any,
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
        last: BaseException | None = None
        for attempt in range(1, 4):
            try:
                cost = float(local.client.metadata.get_cost(mode=COST_MODE, **args))
                size = int(local.client.metadata.get_billable_size(**args))
                if not math.isfinite(cost) or cost < 0 or size < 0:
                    raise QuoteError("non-finite or negative quote")
                return {
                    **window,
                    "estimated_usd": cost,
                    "billable_bytes": size,
                    "metadata_attempt": attempt,
                }
            except BaseException as exc:
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
    plan = workspace / PLAN_REL
    tool = workspace / TOOL_REL
    test = workspace / TEST_REL
    registry = workspace / REGISTRY_REL
    if sha256_file(plan) != PLAN_SHA256:
        raise QuoteError("source plan hash drift")
    if sha256_file(workspace / SELECTION_RECEIPT_REL) != SELECTION_RECEIPT_SHA256:
        raise QuoteError("selection receipt hash drift")
    selection_receipt = json.loads((workspace / SELECTION_RECEIPT_REL).read_text(encoding="utf-8"))
    if (
        selection_receipt.get("status") != "OUTCOME_BLIND_SIGNAL_DATE_SELECTION_COMPLETE"
        or int(selection_receipt.get("selected_dates", -1)) != EXPECTED_DATES
        or selection_receipt.get("information_boundary", {}).get("target_returns_read") != 0
        or selection_receipt.get("information_boundary", {}).get("paid_requests_made") != 0
    ):
        raise QuoteError("selection receipt does not preserve the source boundary")
    tool_payload = tool.read_bytes()
    tool_base = normalized_tool_base_sha256(tool_payload)
    test_sha = sha256_file(test)
    candidates: list[tuple[dict[str, object], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            candidates.append((row, raw + b"\n"))
    if not candidates:
        raise QuoteError("hypothesis absent from registry")
    row, line = candidates[-1]
    row_sha = sha256_bytes(line)
    validation = row.get("validation", {})
    if not isinstance(validation, dict):
        raise QuoteError("registry validation contract malformed")
    expected = {
        "source_plan_v2_sha256": PLAN_SHA256,
        "signal_date_ledger_sha256": LEDGER_SHA256,
        "signal_date_receipt_sha256": SELECTION_RECEIPT_SHA256,
        "reviewed_quote_tool_base_sha256": tool_base,
        "reviewed_quote_test_sha256": test_sha,
    }
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256:
        raise QuoteError("sentinel does not bind the latest HYP002 row")
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise QuoteError("registry state or source plan binding invalid")
    if validation.get("source_quote_authorized") is not True:
        raise QuoteError("free source-quote authority absent")
    for key, value in expected.items():
        if validation.get(key) != value:
            raise QuoteError(f"registry binding mismatch: {key}")
    for key in (
        "paid_acquisition_authorized",
        "economics_authorized",
        "outcome_prices_authorized",
        "mql5_authorized",
        "model0_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise QuoteError(f"forbidden authority open: {key}")
    if QUOTE_ID in row.get("run_ids", []):
        raise QuoteError("free quote attempt already consumed")
    return {
        "registry_row_sha256": row_sha,
        "tool_base_sha256": tool_base,
        "tool_file_sha256": sha256_bytes(tool_payload),
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
    rows = load_dates(require_d(workspace / LEDGER_REL, "signal-date ledger"))
    windows = [build_window(row) for row in rows]
    if len({(window["start"], window["end"]) for window in windows}) != EXPECTED_DATES:
        raise QuoteError("window identity mismatch")
    foundation = load_foundation(require_d(workspace / FOUNDATION_REL, "foundation"))
    key = foundation.load_api_key()

    def client_factory() -> Any:
        return foundation.make_client(key)

    quotes = quote_all(client_factory, windows, workers)
    if len(quotes) != EXPECTED_DATES:
        raise QuoteError("quote coverage mismatch")
    total_usd = float(sum(float(item["estimated_usd"]) for item in quotes))
    total_bytes = int(sum(int(item["billable_bytes"]) for item in quotes))
    if not math.isfinite(total_usd) or total_usd < 0:
        raise QuoteError("aggregate quote invalid")
    payload = {
        "schema_version": "eurfxofi003_free_metadata_quote.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "quote_id": QUOTE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "FREE_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST",
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "cost_mode": COST_MODE,
        "request_window": "[14:14:45,14:15:00)_Europe/Berlin_DST",
        "window_seconds": WINDOW_SECONDS,
        "request_count": len(quotes),
        "quoted_request_count": len(quotes),
        "split_counts": EXPECTED_SPLITS,
        "owner_ceiling_usd": OWNER_CEILING_USD,
        "estimated_total_usd": total_usd,
        "estimated_total_billable_bytes": total_bytes,
        "within_owner_ceiling": total_usd <= OWNER_CEILING_USD,
        "quotes": quotes,
        "bindings": {
            "plan_path": PLAN_REL,
            "plan_sha256": PLAN_SHA256,
            "tool_path": TOOL_REL,
            "tool_base_sha256": authority["tool_base_sha256"],
            "tool_file_sha256": authority["tool_file_sha256"],
            "test_path": TEST_REL,
            "test_sha256": authority["test_sha256"],
            "registry_row_sha256": authority["registry_row_sha256"],
            "signal_date_path": LEDGER_REL,
            "signal_date_sha256": LEDGER_SHA256,
            "selection_receipt_path": SELECTION_RECEIPT_REL,
            "selection_receipt_sha256": SELECTION_RECEIPT_SHA256,
            "foundation_path": FOUNDATION_REL,
            "foundation_sha256": FOUNDATION_SHA256,
            "runtime_path": RUNTIME_REL,
            "databento_sdk_version": SDK_VERSION,
        },
        "api_method_counters": {
            "metadata.get_cost": sum(int(item["metadata_attempt"]) for item in quotes),
            "metadata.get_billable_size": len(quotes),
            "timeseries.get_range": 0,
            "batch.submit_job": 0,
            "batch.download": 0,
        },
        "paid_request_made": False,
        "api_key_stored": False,
        "price_data_read": False,
        "outcome_fields_used": [],
        "download_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "model0_authorized": False,
    }
    output = require_d(workspace / OUTPUT_REL, "quote receipt")
    if output.exists() or output.parent.exists():
        raise QuoteError("exclusive quote output root already exists")
    output.parent.mkdir(parents=True, exist_ok=False)
    with output.open("xb") as handle:
        handle.write(canonical_json(payload) + b"\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    try:
        output = execute(args.workspace.resolve(), args.workers)
        receipt = json.loads(output.read_text(encoding="utf-8"))
        print(
            "EURFXOFI003_FREE_QUOTE_OK "
            f"requests={receipt['request_count']} "
            f"estimated_usd={receipt['estimated_total_usd']:.12f} "
            f"bytes={receipt['estimated_total_billable_bytes']} "
            f"within_ceiling={str(receipt['within_owner_ceiling']).lower()} paid=0"
        )
        print(f"RECEIPT {output}")
        return 0
    except QuoteError as exc:
        print(f"EURFXOFI003_FREE_QUOTE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
