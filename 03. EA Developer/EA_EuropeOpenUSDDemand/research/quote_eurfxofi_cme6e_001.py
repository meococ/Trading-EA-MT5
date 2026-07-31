#!/usr/bin/env python3
"""Free metadata-only quote for HYP-EURFXOFI-EURUSD-M1-001."""

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
import sys
import threading
import time as time_module
from typing import Any
from zoneinfo import ZoneInfo


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-001"
QUOTE_ID = "EURFXOFI001-FREE-METADATA-QUOTE-001"
PLAN_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/HYP-EURFXOFI-EURUSD-M1-001_SOURCE_QUOTE_PLAN.md"
PLAN_SHA256 = "91E6A9FABCCB3449BD02B2354DE7872CBBEBB3644BFDD8AD7C962A0F24434A82"
TOOL_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/quote_eurfxofi_cme6e_001.py"
LEDGER_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EURFXREV-EURUSD-M1-001/EURFXREV001-TRAIN-ECON-001/trades.jsonl"
LEDGER_SHA256 = "952E193FFC65D91B43E7F55EE970A65E904B2E9DD50A5E6469B9659EDFC28E45"
FOUNDATION_REL = "03. EA Developer/EA_SweepCascadeContinuation/research/acquire_cme6e_mbp10_windows.py"
FOUNDATION_SHA256 = "1F7E38F8326743206CEDE0AE3AEA8760B6C1C4590E4DD7D7E544058CB5A8E78A"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento/Scripts/python.exe"
OUTPUT_REL = "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi_quote/EURFXOFI001-FREE-METADATA-QUOTE-001/metadata_quote_receipt.json"
EXPECTED_DATES = 612
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
COST_MODE = "historical-streaming"
SDK_VERSION = "0.54.0"
BERLIN = ZoneInfo("Europe/Berlin")


class QuoteError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise QuoteError(f"{label} must stay on D:")
    return resolved


def load_dates(path: Path) -> list[str]:
    if sha256_file(path) != LEDGER_SHA256:
        raise QuoteError("date-source ledger hash mismatch")
    dates: list[str] = []
    for raw in path.read_bytes().splitlines():
        try:
            row = json.loads(raw)
            day = str(row["local_date"])
            datetime.strptime(day, "%Y-%m-%d")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise QuoteError("invalid date-source row") from exc
        dates.append(day)
    if len(dates) != EXPECTED_DATES or len(set(dates)) != EXPECTED_DATES or dates != sorted(dates):
        raise QuoteError("date-source population mismatch")
    return dates


def build_window(day: str) -> dict[str, str]:
    date = datetime.strptime(day, "%Y-%m-%d").date()
    end_local = datetime.combine(date, time(14, 15), tzinfo=BERLIN)
    start_local = end_local - timedelta(seconds=30)
    start = start_local.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    end = end_local.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {"request_id": f"ECBFX-{day}", "local_date": day, "start": start, "end": end}


def load_foundation(path: Path) -> Any:
    if sha256_file(path) != FOUNDATION_SHA256:
        raise QuoteError("foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi_quote_foundation", path)
    if spec is None or spec.loader is None:
        raise QuoteError("cannot load foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def quote_all(client_factory: Any, windows: list[dict[str, str]], workers: int) -> list[dict[str, Any]]:
    if not 1 <= workers <= 16:
        raise QuoteError("workers must be 1..16")
    local = threading.local()

    def one(window: dict[str, str]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = client_factory()
        args = {"dataset": DATASET, "schema": SCHEMA, "symbols": [SYMBOL], "stype_in": STYPE_IN, "start": window["start"], "end": window["end"]}
        last: BaseException | None = None
        for attempt in range(1, 4):
            try:
                cost = float(local.client.metadata.get_cost(mode=COST_MODE, **args))
                size = int(local.client.metadata.get_billable_size(**args))
                if not math.isfinite(cost) or cost < 0 or size < 0:
                    raise QuoteError("non-finite or negative quote")
                return {**window, "estimated_usd": cost, "billable_bytes": size, "metadata_attempt": attempt}
            except BaseException as exc:
                last = exc
                if attempt < 3:
                    time_module.sleep((0.25, 1.0)[attempt - 1])
        raise QuoteError(f"metadata quote failed for {window['request_id']}: {type(last).__name__}") from None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        quotes = list(pool.map(one, windows))
    return sorted(quotes, key=lambda item: item["request_id"])


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def execute(workspace: Path, workers: int) -> Path:
    workspace = require_d(workspace, "workspace")
    runtime = require_d(workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise QuoteError("wrong Python runtime")
    if importlib.metadata.version("databento") != SDK_VERSION:
        raise QuoteError("databento SDK version mismatch")
    plan = workspace / PLAN_REL
    tool = workspace / TOOL_REL
    if sha256_file(plan) != PLAN_SHA256:
        raise QuoteError("plan hash drift")
    dates = load_dates(require_d(workspace / LEDGER_REL, "date source"))
    windows = [build_window(day) for day in dates]
    if len({(w["start"], w["end"]) for w in windows}) != EXPECTED_DATES:
        raise QuoteError("window identity mismatch")
    foundation = load_foundation(require_d(workspace / FOUNDATION_REL, "foundation"))
    key = foundation.load_api_key()
    def client_factory():
        return foundation.make_client(key)
    quotes = quote_all(client_factory, windows, workers)
    if len(quotes) != EXPECTED_DATES:
        raise QuoteError("quote coverage mismatch")
    total_usd = float(sum(float(q["estimated_usd"]) for q in quotes))
    total_bytes = int(sum(int(q["billable_bytes"]) for q in quotes))
    payload = {
        "schema_version": "eurfxofi001_free_metadata_quote.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "quote_id": QUOTE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "FREE_METADATA_QUOTE_COMPLETE_NO_PURCHASE_AUTHORITY",
        "dataset": DATASET, "schema": SCHEMA, "symbol": SYMBOL, "stype_in": STYPE_IN, "cost_mode": COST_MODE,
        "request_window": "[14:14:30,14:15:00)_Europe/Berlin_DST",
        "request_count": len(quotes), "quoted_request_count": len(quotes),
        "estimated_total_usd": total_usd, "estimated_total_billable_bytes": total_bytes,
        "quotes": quotes,
        "bindings": {"plan_path": PLAN_REL, "plan_sha256": PLAN_SHA256, "tool_path": TOOL_REL, "tool_sha256": sha256_file(tool), "date_source_path": LEDGER_REL, "date_source_sha256": LEDGER_SHA256, "foundation_path": FOUNDATION_REL, "foundation_sha256": FOUNDATION_SHA256, "runtime_path": RUNTIME_REL, "databento_sdk_version": SDK_VERSION},
        "api_method_counters": {"metadata.get_cost": sum(int(q["metadata_attempt"]) for q in quotes), "metadata.get_billable_size": len(quotes), "timeseries.get_range": 0, "batch.submit_job": 0, "batch.download": 0},
        "paid_request_made": False, "api_key_stored": False, "price_data_read": False, "outcome_fields_used": [],
        "download_authorized": False, "economics_authorized": False, "mql5_authorized": False, "model0_authorized": False,
    }
    output = require_d(workspace / OUTPUT_REL, "quote receipt")
    if output.exists() or output.parent.exists():
        raise QuoteError("quote output root already exists")
    output.parent.mkdir(parents=True, exist_ok=False)
    with output.open("xb") as handle:
        handle.write(canonical_json(payload) + b"\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    output = execute(args.workspace.resolve(), args.workers)
    receipt = json.loads(output.read_text(encoding="utf-8"))
    print(f"EURFXOFI001_FREE_QUOTE_OK requests={receipt['request_count']} estimated_usd={receipt['estimated_total_usd']:.12f} bytes={receipt['estimated_total_billable_bytes']} paid=0")
    print(f"RECEIPT {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
