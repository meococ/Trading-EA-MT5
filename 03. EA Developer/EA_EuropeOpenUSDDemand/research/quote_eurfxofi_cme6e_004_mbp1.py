#!/usr/bin/env python3
"""Free full-history CME 6E MBP-1 quote for HYP004."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-004"
QUOTE_ID = "EURFXOFI004-MBP1-FREE-QUOTE-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-004_MBP1_SOURCE_QUOTE_PLAN.md"
TOOL_REL = BASE_REL + "quote_eurfxofi_cme6e_004_mbp1.py"
TEST_REL = BASE_REL + "tests/test_quote_eurfxofi_cme6e_004_mbp1.py"
PARENT_TOOL_REL = BASE_REL + "quote_eurfxofi_cme6e_003.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento/Scripts/python.exe"
LEDGER_REL = "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/HYP-EURFXOFI-EURUSD-M1-002/EURFXOFI002-SIGNAL-DATE-SELECTION-001/signal_dates.jsonl"
FOUNDATION_REL = "03. EA Developer/EA_SweepCascadeContinuation/research/acquire_cme6e_mbp10_windows.py"
OUTPUT_REL = f"02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/{HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"

PLAN_SHA256 = "F456A1D4038C0F71DBF166B2A7A805C33FB7EF6DCD56F0507B365988675AD4F2"
PARENT_TOOL_SHA256 = "1D12644CD674FFEA23480FEAB7BA43A2D31692FD4F6E6F9A202FDFB9C9DE63DB"
LEDGER_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
FOUNDATION_SHA256 = "1F7E38F8326743206CEDE0AE3AEA8760B6C1C4590E4DD7D7E544058CB5A8E78A"
SCHEMA = "mbp-1"
SDK_VERSION = "0.54.0"
OWNER_CEILING_USD = 2.25
EXPECTED_DATES = 1359

REVIEWED_REGISTRY_ROW_SHA256: str | None = "1FE1E9A0EEDE1A8CB97E1A6EAFD1B8A0B19568C1A87FA7F6CD18F6989E2A2C26"
_SENTINEL_RE = re.compile(rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$')


class QuoteError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def normalized_tool_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
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


def load_parent(path: Path) -> Any:
    if sha256_file(path) != PARENT_TOOL_SHA256:
        raise QuoteError("parent quote foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi004_parent_quote", path)
    if spec is None or spec.loader is None:
        raise QuoteError("cannot load parent quote foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def quote_all(parent: Any, client_factory: Any, windows: list[dict[str, str]], workers: int) -> list[dict[str, Any]]:
    original = parent.SCHEMA
    parent.SCHEMA = SCHEMA
    try:
        return parent.quote_all(client_factory, windows, workers)
    finally:
        parent.SCHEMA = original


def validate_authority(workspace: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise QuoteError("registry sentinel is not armed")
    if sha256_file(workspace / PLAN_REL) != PLAN_SHA256:
        raise QuoteError("plan hash drift")
    if sha256_file(workspace / LEDGER_REL) != LEDGER_SHA256:
        raise QuoteError("signal-date ledger hash drift")
    tool = workspace / TOOL_REL
    test = workspace / TEST_REL
    payload = tool.read_bytes()
    base_sha = normalized_tool_base_sha256(payload)
    test_sha = sha256_file(test)
    rows = []
    for raw in (workspace / REGISTRY_REL).read_bytes().splitlines():
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            rows.append((row, raw + b"\n"))
    if not rows:
        raise QuoteError("hypothesis absent from registry")
    row, line = rows[-1]
    row_sha = sha256_bytes(line)
    validation = row.get("validation", {})
    expected = {
        "source_quote_plan_sha256": PLAN_SHA256,
        "signal_date_ledger_sha256": LEDGER_SHA256,
        "reviewed_quote_tool_base_sha256": base_sha,
        "reviewed_quote_test_sha256": test_sha,
        "parent_quote_tool_sha256": PARENT_TOOL_SHA256,
    }
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256 or row.get("state") != "probe":
        raise QuoteError("registry sentinel/state mismatch")
    if validation.get("source_quote_authorized") is not True:
        raise QuoteError("free quote authority absent")
    for key, value in expected.items():
        if validation.get(key) != value:
            raise QuoteError(f"registry binding mismatch: {key}")
    for key in ("paid_acquisition_authorized", "economics_authorized", "outcome_prices_authorized", "mql5_authorized", "model0_authorized", "paper_trading_authorized", "live_trading_authorized"):
        if validation.get(key) is not False:
            raise QuoteError(f"forbidden authority open: {key}")
    if QUOTE_ID in row.get("run_ids", []):
        raise QuoteError("quote attempt already consumed")
    return {"row_sha": row_sha, "tool_base_sha": base_sha, "tool_file_sha": sha256_bytes(payload), "test_sha": test_sha}


def execute(workspace: Path, workers: int) -> Path:
    workspace = require_d(workspace, "workspace")
    if Path(sys.executable).resolve() != require_d(workspace / RUNTIME_REL, "runtime"):
        raise QuoteError("wrong Python runtime")
    if importlib.metadata.version("databento") != SDK_VERSION:
        raise QuoteError("Databento SDK version mismatch")
    authority = validate_authority(workspace)
    parent = load_parent(workspace / PARENT_TOOL_REL)
    rows = parent.load_dates(workspace / LEDGER_REL)
    windows = [parent.build_window(row) for row in rows]
    if len(windows) != EXPECTED_DATES:
        raise QuoteError("window population mismatch")
    foundation = parent.load_foundation(workspace / FOUNDATION_REL)
    key = foundation.load_api_key()
    quotes = quote_all(parent, lambda: foundation.make_client(key), windows, workers)
    total_usd = float(sum(float(item["estimated_usd"]) for item in quotes))
    total_bytes = int(sum(int(item["billable_bytes"]) for item in quotes))
    if len(quotes) != EXPECTED_DATES or not math.isfinite(total_usd) or total_usd < 0:
        raise QuoteError("aggregate quote invalid")
    payload = {
        "schema_version": "eurfxofi004_mbp1_free_quote.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "quote_id": QUOTE_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "FREE_MBP1_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST",
        "dataset": parent.DATASET,
        "schema": SCHEMA,
        "symbol": parent.SYMBOL,
        "request_window": "[14:14:45,14:15:00)_Europe/Berlin_DST",
        "request_count": len(quotes),
        "owner_ceiling_usd": OWNER_CEILING_USD,
        "estimated_total_usd": total_usd,
        "estimated_total_billable_bytes": total_bytes,
        "within_owner_ceiling": total_usd <= OWNER_CEILING_USD,
        "quotes": quotes,
        "bindings": {"plan_sha256": PLAN_SHA256, "signal_date_sha256": LEDGER_SHA256, "tool_base_sha256": authority["tool_base_sha"], "tool_file_sha256": authority["tool_file_sha"], "test_sha256": authority["test_sha"], "registry_row_sha256": authority["row_sha"], "parent_quote_tool_sha256": PARENT_TOOL_SHA256, "foundation_sha256": FOUNDATION_SHA256},
        "api_method_counters": {"metadata.get_cost": sum(int(item["metadata_attempt"]) for item in quotes), "metadata.get_billable_size": len(quotes), "timeseries.get_range": 0, "batch.submit_job": 0, "batch.download": 0},
        "paid_request_made": False,
        "price_data_read": False,
        "outcome_fields_used": [],
        "economics_authorized": False,
        "mql5_authorized": False,
        "model0_authorized": False,
    }
    output = require_d(workspace / OUTPUT_REL, "quote output")
    if output.exists() or output.parent.exists():
        raise QuoteError("exclusive quote output root exists")
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
        print(f"EURFXOFI004_MBP1_FREE_QUOTE_OK requests={receipt['request_count']} estimated_usd={receipt['estimated_total_usd']:.12f} bytes={receipt['estimated_total_billable_bytes']} within_ceiling={str(receipt['within_owner_ceiling']).lower()} paid=0")
        print(f"RECEIPT {output}")
        return 0
    except QuoteError as exc:
        print(f"EURFXOFI004_MBP1_FREE_QUOTE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
