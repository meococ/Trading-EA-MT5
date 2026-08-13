"""Acquire the frozen full-DESIGN option definition universe, one call only."""

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
CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-SOURCE-001"
DATASET = "GLBX.MDP3"
SCHEMA = "definition"
PARENTS = [
    "EUU.OPT",
    "1EU.OPT",
    "2EU.OPT",
    "3EU.OPT",
    "4EU.OPT",
    "5EU.OPT",
    "WE1.OPT",
    "WE2.OPT",
    "WE3.OPT",
    "WE4.OPT",
    "WE5.OPT",
]
STYPE_IN = "parent"
STYPE_OUT = "instrument_id"
START = "2018-01-01T00:00:00Z"
END = "2023-01-01T00:00:00Z"
COST_MODE = "historical-streaming"
CAMPAIGN_SPEND_CEILING_USD = 10.0
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DBN_VERSION = 3
PLAN_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_SOURCE_CAMPAIGN_PLAN.md"
)
PLAN_SHA256 = "FE26F5571CF161357C2F39F8366E81A5A12448DE62DB33EC253B115AB1E7CF8C"
AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_SOURCE_PHASE_01_AUTHORITY.json"
)
AUTHORITY_SHA256 = (
    "C56CDB7BFD62F5474E6E80A722FE2420C42D1CDA2E1572617CDAAC41B202BCC4"
)
OWNER_AUTHORITY_REL = Path(
    "03. EA Developer/EA_EventL1Replenishment/research/"
    "HYP-EVENT-L1-REPLEN-EURUSD-TICK-002_OWNER_AUTHORITY.json"
)
OWNER_AUTHORITY_SHA256 = (
    "CF68F81DB8717F7EDE8488DC7B17E78CD03486CA0FE225833BAD6847BF21B04D"
)
PILOT_001_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/CME6EOPTPIN001-SOURCE-PILOT-001/"
    "source_pilot_result_receipt.json"
)
PILOT_001_SHA256 = (
    "15C66930E9C6EB68B7093CB659AF3A019AE81E2138D7FAEE09EB96E2EB30F7C7"
)
PILOT_002_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/CME6EOPTPIN002-SOURCE-PILOT-002/"
    "source_pilot_result_receipt.json"
)
PILOT_002_SHA256 = (
    "A63BF2340A2C3E2F58460FD75F5452AB01B81258802E978FD7F9FCA52E41362F"
)
RUNTIME_REL = Path(
    "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
)
OUTPUT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_definitions"
)
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


class CampaignError(RuntimeError):
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
        raise CampaignError(f"path escaped workspace: {relative}") from exc
    if not path.is_file() or sha256_file(path) != expected_sha:
        raise CampaignError(f"missing or drifted input: {relative}")
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
        raise CampaignError("DATABENTO_API_KEY is absent or malformed")
    return key


def request_args() -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": PARENTS,
        "stype_in": STYPE_IN,
        "start": START,
        "end": END,
    }


def validate_raw(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise CampaignError("definition DBN payload is empty")
    with path.open("rb") as handle:
        if handle.read(len(ZSTD_MAGIC)) != ZSTD_MAGIC:
            raise CampaignError("invalid Zstandard DBN signature")
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
        raise CampaignError(f"DBN decode failed: {exc}") from exc
    if (
        result["dataset"] != DATASET
        or result["schema"] != SCHEMA
        or result["dbn_version"] != DBN_VERSION
    ):
        raise CampaignError("DBN metadata contract mismatch")
    return result


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise CampaignError("workspace must be on D:")
    runtime = (workspace / RUNTIME_REL).resolve()
    if Path(sys.executable).resolve() != runtime:
        raise CampaignError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise CampaignError("Databento DBNv3 runtime mismatch")
    require_file(workspace, PLAN_REL, PLAN_SHA256)
    authority_path = require_file(workspace, AUTHORITY_REL, AUTHORITY_SHA256)
    require_file(workspace, OWNER_AUTHORITY_REL, OWNER_AUTHORITY_SHA256)
    require_file(workspace, PILOT_001_REL, PILOT_001_SHA256)
    require_file(workspace, PILOT_002_REL, PILOT_002_SHA256)
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    if (
        authority.get("paid_source_acquisition_authorized") is not True
        or authority.get("authorized_payload_calls") != 1
        or authority.get("authorized_schema") != SCHEMA
        or authority.get("statistics_payload_authorized") is not False
        or authority.get("automatic_retry_authorized") is not False
    ):
        raise CampaignError("phase-01 authority is not armed")

    output = (workspace / OUTPUT_REL).resolve()
    try:
        output.relative_to(workspace)
    except ValueError as exc:
        raise CampaignError("output escaped workspace") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise CampaignError("exclusive phase-01 root exists; retry is forbidden")
    output.mkdir()
    raw_dir = output / "raw"
    raw_dir.mkdir()

    import databento as db

    client = db.Historical(load_api_key())
    args = request_args()
    live_cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
    live_size = int(client.metadata.get_billable_size(**args))
    if (
        not math.isfinite(live_cost)
        or live_cost < 0
        or live_size <= 0
        or live_cost >= CAMPAIGN_SPEND_CEILING_USD
    ):
        raise CampaignError("live quote is outside cumulative campaign authority")

    quote = {
        "schema_version": "cme6e_option_pin_design_source_quote.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "phase": "PHASE_01_DEFINITIONS",
        "request": args,
        "live_estimated_usd": live_cost,
        "live_billable_bytes": live_size,
        "cumulative_campaign_spend_ceiling_usd": CAMPAIGN_SPEND_CEILING_USD,
        "payload_calls_at_receipt": 0,
        "plan_sha256": PLAN_SHA256,
        "authority_sha256": AUTHORITY_SHA256,
    }
    quote_path = output / "metadata_quote_receipt.json"
    write_json(quote_path, quote)

    manifest_path = output / "download_manifest.json"
    manifest = {
        "schema_version": "cme6e_option_pin_design_source_manifest.v1",
        "status": "IN_FLIGHT",
        "updated_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "phase": "PHASE_01_DEFINITIONS",
        "metadata_quote_receipt_sha256": sha256_file(quote_path),
        "timeseries_calls": 0,
        "target_price_fields_used": [],
        "outcome_fields_used": [],
    }
    write_json(manifest_path, manifest)

    final = raw_dir / "EU_OPTIONS_20180101_20230101_definition.dbn.zst"
    partial = final.with_suffix(final.suffix + ".partial")
    try:
        client.timeseries.get_range(**args, stype_out=STYPE_OUT, path=partial)
    except Exception as exc:
        raise CampaignError(
            f"paid definition request failed: {type(exc).__name__}"
        ) from exc
    manifest["timeseries_calls"] = 1
    raw_info = validate_raw(partial)
    os.replace(partial, final)
    manifest["status"] = "COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    manifest["payload"] = {
        **raw_info,
        "path": str(final.relative_to(workspace)).replace("\\", "/"),
    }
    write_json(manifest_path, manifest)

    receipt = {
        "schema_version": "cme6e_option_pin_design_source_phase_01.v1",
        "created_at_utc": utc_now(),
        "status": "DEFINITIONS_ACQUIRED_EVENT_DISCOVERY_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "request": args,
        "live_estimated_usd": live_cost,
        "live_billable_bytes": live_size,
        "payload": manifest["payload"],
        "bindings": {
            "plan_sha256": PLAN_SHA256,
            "authority_sha256": AUTHORITY_SHA256,
            "owner_authority_sha256": OWNER_AUTHORITY_SHA256,
            "pilot_001_result_sha256": PILOT_001_SHA256,
            "pilot_002_result_sha256": PILOT_002_SHA256,
            "metadata_quote_receipt_sha256": sha256_file(quote_path),
            "download_manifest_sha256": sha256_file(manifest_path),
        },
        "api_method_counters": {
            "metadata.get_cost": 1,
            "metadata.get_billable_size": 1,
            "timeseries.get_range": 1,
            "batch": 0,
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "statistics_payload_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    receipt_path = output / "phase_01_acquisition_receipt.json"
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
            "CME6EOPTPIN_DESIGN_PHASE01_ACQUIRED "
            f"cost={receipt['live_estimated_usd']:.12f} "
            f"bytes={receipt['live_billable_bytes']} calls=1"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except CampaignError as exc:
        print(f"CME6EOPTPIN_DESIGN_PHASE01_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
