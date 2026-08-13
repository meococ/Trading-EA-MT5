"""Acquire the frozen 2EU.OPT definition/statistics source pilot only."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
PILOT_ID = "CME6EOPTPIN001-SOURCE-PILOT-001"
DATASET = "GLBX.MDP3"
PARENT = "2EU.OPT"
STYPE_IN = "parent"
STYPE_OUT = "instrument_id"
START = "2019-07-11T00:00:00Z"
END = "2019-07-12T13:45:00Z"
SCHEMAS = ("definition", "statistics")
COST_MODE = "historical-streaming"
SPEND_CEILING_USD = 10.0
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DBN_VERSION = 3

PLAN_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_SOURCE_PILOT_PLAN.md"
)
PLAN_SHA256 = "5E4B63F81A02CFB790707D4E607813CDA925993C2BE41EF57C83AD0B978C7C55"
AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_SOURCE_PILOT_AUTHORITY.json"
)
AUTHORITY_SHA256 = "AD1BCC49FE4CFB68335BEB791283CBBDDD55D05C982E64A749D24597CDF6CC5D"
OWNER_AUTHORITY_REL = Path(
    "03. EA Developer/EA_EventL1Replenishment/research/"
    "HYP-EVENT-L1-REPLEN-EURUSD-TICK-002_OWNER_AUTHORITY.json"
)
OWNER_AUTHORITY_SHA256 = "CF68F81DB8717F7EDE8488DC7B17E78CD03486CA0FE225833BAD6847BF21B04D"
RUNTIME_REL = Path(
    "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
)
OUTPUT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{PILOT_ID}"
)
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


class PilotError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    os.replace(temporary, path)


def require_file(workspace: Path, relative: Path, expected_sha: str) -> Path:
    path = (workspace / relative).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise PilotError(f"path escaped workspace: {relative}") from exc
    if not path.is_file() or sha256_file(path) != expected_sha:
        raise PilotError(f"missing or drifted authority input: {relative}")
    return path


def load_api_key() -> str:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key and sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
                key = str(winreg.QueryValueEx(handle, "DATABENTO_API_KEY")[0])
        except OSError:
            key = None
    if not key or not key.startswith("db-"):
        raise PilotError("DATABENTO_API_KEY is absent or malformed")
    return key


def request_args(schema: str) -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": schema,
        "symbols": [PARENT],
        "stype_in": STYPE_IN,
        "start": START,
        "end": END,
    }


def payload_filename(schema: str) -> str:
    parent = PARENT.replace(".", "_")
    start = START.replace("-", "").replace(":", "").replace("T", "T")[:8]
    end = END.replace("-", "").replace(":", "").replace("T", "T")
    end = end.replace("Z", "")
    return f"{parent}_{start}_{end}_{schema}.dbn.zst"


def validate_raw(path: Path, expected_schema: str) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise PilotError(f"empty DBN payload for {expected_schema}")
    with path.open("rb") as handle:
        if handle.read(len(ZSTD_MAGIC)) != ZSTD_MAGIC:
            raise PilotError(f"invalid Zstandard DBN signature for {expected_schema}")
    try:
        import databento as db

        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        result = {
            "dataset": metadata.dataset,
            "schema": schema,
            "dbn_version": int(metadata.version),
            "metadata_start_ns": int(metadata.start),
            "metadata_end_ns": int(metadata.end),
            "raw_bytes": path.stat().st_size,
            "raw_sha256": sha256_file(path),
        }
    except Exception as exc:
        raise PilotError(f"DBN decode failed for {expected_schema}: {exc}") from exc
    if (
        result["dataset"] != DATASET
        or result["schema"] != expected_schema
        or result["dbn_version"] != DBN_VERSION
    ):
        raise PilotError(f"DBN metadata contract mismatch for {expected_schema}")
    return result


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise PilotError("workspace must be on D:")
    runtime = (workspace / RUNTIME_REL).resolve()
    if Path(sys.executable).resolve() != runtime:
        raise PilotError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise PilotError("Databento DBNv3 runtime mismatch")
    require_file(workspace, PLAN_REL, PLAN_SHA256)
    authority_path = require_file(workspace, AUTHORITY_REL, AUTHORITY_SHA256)
    require_file(workspace, OWNER_AUTHORITY_REL, OWNER_AUTHORITY_SHA256)
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    if (
        authority.get("paid_source_acquisition_authorized") is not True
        or authority.get("authorized_payload_calls") != 2
        or authority.get("automatic_retry_authorized") is not False
    ):
        raise PilotError("source-pilot authority is not armed")

    output = (workspace / OUTPUT_REL).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise PilotError("exclusive pilot root exists; automatic retry is forbidden")
    output.mkdir()
    raw_dir = output / "raw"
    raw_dir.mkdir()

    import databento as db

    client = db.Historical(load_api_key())
    quotes: list[dict[str, Any]] = []
    for schema in SCHEMAS:
        args = request_args(schema)
        cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
        size = int(client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0 or size <= 0:
            raise PilotError(f"invalid live metadata quote for {schema}")
        quotes.append(
            {"schema": schema, "estimated_usd": cost, "billable_bytes": size}
        )
    total_cost = sum(item["estimated_usd"] for item in quotes)
    total_bytes = sum(item["billable_bytes"] for item in quotes)
    if total_cost >= SPEND_CEILING_USD:
        raise PilotError("combined quote is outside Owner standing authority")

    quote_receipt = {
        "schema_version": "cme6e_option_pin_source_quote.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "pilot_id": PILOT_ID,
        "requests": [request_args(schema) for schema in SCHEMAS],
        "quotes": quotes,
        "combined_estimated_usd": total_cost,
        "combined_billable_bytes": total_bytes,
        "spend_ceiling_usd": SPEND_CEILING_USD,
        "metadata_get_cost_calls": 2,
        "metadata_get_billable_size_calls": 2,
        "payload_calls_at_receipt": 0,
        "plan_sha256": PLAN_SHA256,
        "authority_sha256": AUTHORITY_SHA256,
    }
    quote_path = output / "metadata_quote_receipt.json"
    write_json(quote_path, quote_receipt)

    manifest: dict[str, Any] = {
        "schema_version": "cme6e_option_pin_source_manifest.v1",
        "status": "IN_FLIGHT",
        "updated_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "pilot_id": PILOT_ID,
        "metadata_quote_receipt_sha256": sha256_file(quote_path),
        "timeseries_calls": 0,
        "batch_calls": 0,
        "target_price_fields_used": [],
        "payloads": {},
    }
    manifest_path = output / "download_manifest.json"
    write_json(manifest_path, manifest)

    for schema in SCHEMAS:
        final = raw_dir / payload_filename(schema)
        partial = final.with_suffix(final.suffix + ".partial")
        try:
            client.timeseries.get_range(
                **request_args(schema), stype_out=STYPE_OUT, path=partial
            )
        except Exception as exc:
            raise PilotError(
                f"paid source request failed for {schema}: {type(exc).__name__}"
            ) from exc
        manifest["timeseries_calls"] += 1
        raw_info = validate_raw(partial, schema)
        os.replace(partial, final)
        manifest["payloads"][schema] = {
            **raw_info,
            "path": str(final.relative_to(workspace)).replace("\\", "/"),
        }
        manifest["updated_at_utc"] = utc_now()
        write_json(manifest_path, manifest)

    manifest["status"] = "COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    write_json(manifest_path, manifest)
    receipt = {
        "schema_version": "cme6e_option_pin_source_pilot_receipt.v1",
        "created_at_utc": utc_now(),
        "status": "SOURCE_PAYLOADS_ACQUIRED_SEMANTICS_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "pilot_id": PILOT_ID,
        "dataset": DATASET,
        "parent": PARENT,
        "start": START,
        "end": END,
        "live_estimated_usd": total_cost,
        "live_billable_bytes": total_bytes,
        "payloads": manifest["payloads"],
        "bindings": {
            "plan_sha256": PLAN_SHA256,
            "authority_sha256": AUTHORITY_SHA256,
            "owner_authority_sha256": OWNER_AUTHORITY_SHA256,
            "metadata_quote_receipt_sha256": sha256_file(quote_path),
            "download_manifest_sha256": sha256_file(manifest_path),
        },
        "api_method_counters": {
            "metadata.get_cost": 2,
            "metadata.get_billable_size": 2,
            "timeseries.get_range": 2,
            "batch": 0,
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
        "validation_or_holdout_authorized": False,
    }
    receipt_path = output / "source_pilot_acquisition_receipt.json"
    write_json(receipt_path, receipt)
    return receipt_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        receipt_path = execute(args.workspace)
        receipt = json.loads(receipt_path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN001_SOURCE_ACQUIRED "
            f"cost={receipt['live_estimated_usd']:.12f} "
            f"bytes={receipt['live_billable_bytes']} calls=2"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except PilotError as exc:
        print(f"CME6EOPTPIN001_SOURCE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
