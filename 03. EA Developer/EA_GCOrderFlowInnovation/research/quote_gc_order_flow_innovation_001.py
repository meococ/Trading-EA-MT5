#!/usr/bin/env python3
"""Free metadata requote for the frozen GC order-flow-innovation pilot."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any


HYPOTHESIS_ID = "HYP-GC-OFI-INNOV-XAU-M5-001"
QUOTE_ID = "GCOFI001-Q1-2019-SOURCE-PILOT-001"
DATASET = "GLBX.MDP3"
SYMBOL = "GC.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
START = "2019-01-01T00:00:00.000Z"
END = "2019-04-01T00:00:00.000Z"
SCHEMAS = ("tbbo", "definition", "status")
COST_MODE = "historical-streaming"
SDK_VERSION = "0.55.1"
OWNER_LIMIT_USD_EXCLUSIVE = 10.0

BASE_REL = "03. EA Developer/EA_GCOrderFlowInnovation/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_PILOT_PLAN.md"
TOOL_REL = BASE_REL + "quote_gc_order_flow_innovation_001.py"
TEST_REL = BASE_REL + "tests/test_quote_gc_order_flow_innovation_001.py"
MECHANISM_REL = "04. Memory/research/20260811_GC_SIGNED_FLOW_MECHANISM_SCREEN.md"
ESTIMATOR_REL = "04. Memory/research/gc_signed_flow_estimator_reference.py"
ESTIMATOR_TEST_REL = "04. Memory/research/tests/test_gc_signed_flow_estimator_reference.py"
RUNTIME_REL = (
    "03. EA Developer/EA_EventAggressorFlow/research/"
    "HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    f"{HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
)

_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")


class QuoteError(RuntimeError):
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
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value) + b"\n")
    os.replace(temporary, path)


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
    key = os.environ.get("DATABENTO_API_KEY") or read_user_environment(
        "DATABENTO_API_KEY"
    )
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


def request_args(schema: str) -> dict[str, object]:
    if schema not in SCHEMAS:
        raise QuoteError(f"schema outside frozen allowlist: {schema}")
    return {
        "dataset": DATASET,
        "schema": schema,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": START,
        "end": END,
    }


def quote_client(client: Any) -> list[dict[str, object]]:
    quoted: list[dict[str, object]] = []
    for schema in SCHEMAS:
        args = request_args(schema)
        cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
        size = int(client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0.0:
            raise QuoteError(f"invalid live cost for {schema}")
        if size <= 0:
            raise QuoteError(f"nonpositive live billable size for {schema}")
        quoted.append(
            {
                "schema": schema,
                "estimated_usd": cost,
                "billable_bytes": size,
                "request": args,
            }
        )
    return quoted


def validate_quote(quoted: list[dict[str, object]]) -> tuple[float, int]:
    if [item.get("schema") for item in quoted] != list(SCHEMAS):
        raise QuoteError("quoted schema order/coverage mismatch")
    total_cost = sum(float(item["estimated_usd"]) for item in quoted)
    total_bytes = sum(int(item["billable_bytes"]) for item in quoted)
    if not math.isfinite(total_cost) or total_cost < 0.0:
        raise QuoteError("invalid aggregate estimate")
    if total_bytes <= 0:
        raise QuoteError("invalid aggregate billable size")
    if not total_cost < OWNER_LIMIT_USD_EXCLUSIVE:
        raise QuoteError(
            f"aggregate estimate {total_cost:.12f} is not strictly below USD 10"
        )
    return total_cost, total_bytes


def execute(workspace: Path, client: Any | None = None) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise QuoteError("workspace must stay on D:")
    paths = {
        "plan_sha256": workspace / PLAN_REL,
        "tool_sha256": workspace / TOOL_REL,
        "test_sha256": workspace / TEST_REL,
        "mechanism_screen_sha256": workspace / MECHANISM_REL,
        "estimator_sha256": workspace / ESTIMATOR_REL,
        "estimator_test_sha256": workspace / ESTIMATOR_TEST_REL,
        "runtime_receipt_sha256": workspace / RUNTIME_REL,
    }
    for label, path in paths.items():
        if not path.is_file():
            raise QuoteError(f"missing bound artifact: {label}")
    if client is None:
        client = make_client(load_api_key())
    quoted = quote_client(client)
    total_cost, total_bytes = validate_quote(quoted)
    receipt = {
        "schema_version": "gc_order_flow_innovation_metadata_quote.v1",
        "created_at_utc": utc_now(),
        "status": "FREE_METADATA_QUOTE_PASS_STRICTLY_BELOW_USD10",
        "hypothesis_id": HYPOTHESIS_ID,
        "quote_id": QUOTE_ID,
        "dataset": DATASET,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "stype_out_required_for_paid_payload": STYPE_OUT,
        "start": START,
        "end": END,
        "cost_mode": COST_MODE,
        "owner_limit_usd_exclusive": OWNER_LIMIT_USD_EXCLUSIVE,
        "estimated_total_usd": total_cost,
        "estimated_total_billable_bytes": total_bytes,
        "quotes": quoted,
        "bindings": {label: sha256_file(path) for label, path in paths.items()},
        "api_method_counters": {
            "metadata.get_cost": len(SCHEMAS),
            "metadata.get_billable_size": len(SCHEMAS),
            "timeseries.get_range": 0,
            "batch.submit_job": 0,
        },
        "paid_request_made": False,
        "source_payload_read": False,
        "xauusd_outcome_read": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    output = workspace / OUTPUT_REL
    write_json_atomic(output, receipt)
    return output


def main() -> int:
    try:
        output = execute(workspace_from_source())
        receipt = json.loads(output.read_text(encoding="ascii"))
        print(
            "GCOFI001_METADATA_QUOTE_OK "
            f"estimated_usd={receipt['estimated_total_usd']:.12f} "
            f"billable_bytes={receipt['estimated_total_billable_bytes']}"
        )
        print(f"RECEIPT {output}")
        return 0
    except QuoteError as exc:
        print(f"GCOFI001_METADATA_QUOTE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

