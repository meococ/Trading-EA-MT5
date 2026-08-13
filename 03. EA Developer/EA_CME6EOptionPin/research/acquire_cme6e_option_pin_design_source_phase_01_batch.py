"""Submit or resume the frozen phase-01 Databento batch definition job."""

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
START = "2018-01-01T00:00:00Z"
END = "2023-01-01T00:00:00Z"
SPEND_CEILING_USD = 10.0
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DBN_VERSION = 3
PLAN_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_SOURCE_CAMPAIGN_PLAN.md"
)
PLAN_SHA256 = "FE26F5571CF161357C2F39F8366E81A5A12448DE62DB33EC253B115AB1E7CF8C"
REVISION_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_SOURCE_PHASE_01_BATCH_R2_REVISION.md"
)
REVISION_SHA256 = (
    "597694858543A0495F64CE9AC754852B56DCF72FB9B593D78AF0950D1DD7D170"
)
AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_SOURCE_PHASE_01_BATCH_R2_AUTHORITY.json"
)
AUTHORITY_SHA256 = (
    "4E57DE17477066E96263480F34E1B327A9A2CDA52122966B292866C85ADA0744"
)
FAILURE_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_definitions_batch_r1/"
    "batch_r1_failure_receipt.json"
)
FAILURE_SHA256 = (
    "FED544D57CE96654C2C35EE6BD5EA038F602490432360A152E174FC4435DF34F"
)
OWNER_AUTHORITY_REL = Path(
    "03. EA Developer/EA_EventL1Replenishment/research/"
    "HYP-EVENT-L1-REPLEN-EURUSD-TICK-002_OWNER_AUTHORITY.json"
)
OWNER_AUTHORITY_SHA256 = (
    "CF68F81DB8717F7EDE8488DC7B17E78CD03486CA0FE225833BAD6847BF21B04D"
)
RUNTIME_REL = Path(
    "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
)
OUTPUT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_definitions_batch_r2"
)
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


class BatchError(RuntimeError):
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
        raise BatchError(f"path escaped workspace: {relative}") from exc
    if not path.is_file() or sha256_file(path) != expected_sha:
        raise BatchError(f"missing or drifted input: {relative}")
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
        raise BatchError("DATABENTO_API_KEY is absent or malformed")
    return key


def stream_request_args() -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": PARENTS,
        "stype_in": "parent",
        "start": START,
        "end": END,
    }


def batch_request_args() -> dict[str, Any]:
    return {
        **stream_request_args(),
        "stype_out": "instrument_id",
        "encoding": "dbn",
        "compression": "zstd",
        "split_duration": "month",
        "delivery": "download",
    }


def validate_environment(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise BatchError("workspace must be on D:")
    runtime = (workspace / RUNTIME_REL).resolve()
    if Path(sys.executable).resolve() != runtime:
        raise BatchError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise BatchError("Databento DBNv3 runtime mismatch")
    require_file(workspace, PLAN_REL, PLAN_SHA256)
    require_file(workspace, REVISION_REL, REVISION_SHA256)
    authority_path = require_file(workspace, AUTHORITY_REL, AUTHORITY_SHA256)
    require_file(workspace, FAILURE_REL, FAILURE_SHA256)
    require_file(workspace, OWNER_AUTHORITY_REL, OWNER_AUTHORITY_SHA256)
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    if (
        authority.get("paid_source_acquisition_authorized") is not True
        or authority.get("authorized_batch_submit_calls") != 1
        or authority.get("authorized_timeseries_calls") != 0
        or authority.get("automatic_resubmit_authorized") is not False
    ):
        raise BatchError("batch authority is not armed")
    return workspace


def job_summary(job: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "id",
        "state",
        "dataset",
        "schema",
        "stype_in",
        "stype_out",
        "start",
        "end",
        "encoding",
        "compression",
        "split_duration",
        "delivery",
        "cost_usd",
        "billed_size",
        "actual_size",
        "record_count",
        "ts_received",
        "ts_process_start",
        "ts_process_done",
        "ts_expiration",
        "progress",
    ]
    return {key: job.get(key) for key in allowed if key in job}


def find_job(client: Any, job_id: str) -> dict[str, Any]:
    jobs = client.batch.list_jobs()
    for job in jobs:
        if str(job.get("id")) == job_id:
            return job
    raise BatchError("persisted batch job is absent from active job list")


def validate_dbn(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise BatchError(f"empty batch DBN file: {path.name}")
    with path.open("rb") as handle:
        if handle.read(len(ZSTD_MAGIC)) != ZSTD_MAGIC:
            raise BatchError(f"invalid Zstandard DBN file: {path.name}")
    try:
        import databento as db

        metadata = db.DBNStore.from_file(path).metadata
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
        raise BatchError(f"DBN decode failed for {path.name}: {exc}") from exc
    if (
        result["dataset"] != DATASET
        or result["schema"] != SCHEMA
        or result["dbn_version"] != DBN_VERSION
    ):
        raise BatchError(f"DBN metadata mismatch for {path.name}")
    return result


def submit(workspace: Path) -> Path:
    workspace = validate_environment(workspace)
    output = (workspace / OUTPUT_REL).resolve()
    try:
        output.relative_to(workspace)
    except ValueError as exc:
        raise BatchError("output escaped workspace") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise BatchError("exclusive batch root exists; resubmit is forbidden")
    output.mkdir()

    import databento as db

    client = db.Historical(load_api_key())
    quote_args = stream_request_args()
    live_cost = float(
        client.metadata.get_cost(mode="historical-streaming", **quote_args)
    )
    live_size = int(client.metadata.get_billable_size(**quote_args))
    if (
        not math.isfinite(live_cost)
        or live_cost < 0
        or live_size <= 0
        or live_cost >= SPEND_CEILING_USD
    ):
        raise BatchError("live quote is outside batch authority")
    quote = {
        "schema_version": "cme6e_option_pin_design_batch_quote.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "live_estimated_usd": live_cost,
        "live_billable_bytes": live_size,
        "batch_request": batch_request_args(),
        "batch_submit_calls_at_receipt": 0,
        "plan_sha256": PLAN_SHA256,
        "revision_sha256": REVISION_SHA256,
        "authority_sha256": AUTHORITY_SHA256,
    }
    quote_path = output / "metadata_quote_receipt.json"
    write_json(quote_path, quote)
    manifest_path = output / "batch_manifest.json"
    manifest = {
        "schema_version": "cme6e_option_pin_design_batch_manifest.v1",
        "status": "PRE_SUBMIT",
        "updated_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "batch_submit_calls": 0,
        "timeseries_calls": 0,
        "metadata_quote_receipt_sha256": sha256_file(quote_path),
        "target_price_fields_used": [],
        "outcome_fields_used": [],
    }
    write_json(manifest_path, manifest)

    try:
        job = client.batch.submit_job(**batch_request_args())
    except Exception as exc:
        raise BatchError(f"batch submit failed: {type(exc).__name__}: {exc}") from exc
    job_id = str(job.get("id", ""))
    if not job_id:
        raise BatchError("batch submit returned no job ID")
    job_receipt = {
        "schema_version": "cme6e_option_pin_design_batch_job.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "job_id": job_id,
        "job": job_summary(job),
        "live_estimated_usd": live_cost,
        "live_billable_bytes": live_size,
        "batch_submit_calls": 1,
        "timeseries_calls": 0,
        "metadata_quote_receipt_sha256": sha256_file(quote_path),
    }
    job_path = output / "batch_job_receipt.json"
    write_json(job_path, job_receipt)
    manifest["status"] = "SUBMITTED"
    manifest["updated_at_utc"] = utc_now()
    manifest["batch_submit_calls"] = 1
    manifest["job_id"] = job_id
    manifest["batch_job_receipt_sha256"] = sha256_file(job_path)
    write_json(manifest_path, manifest)
    return job_path


def resume(workspace: Path) -> tuple[str, Path]:
    workspace = validate_environment(workspace)
    output = (workspace / OUTPUT_REL).resolve()
    job_path = output / "batch_job_receipt.json"
    manifest_path = output / "batch_manifest.json"
    if not job_path.is_file() or not manifest_path.is_file():
        raise BatchError("persisted batch job receipt is missing")
    job_receipt = json.loads(job_path.read_text(encoding="ascii"))
    job_id = str(job_receipt.get("job_id", ""))
    if not job_id or job_receipt.get("batch_submit_calls") != 1:
        raise BatchError("persisted batch job receipt is invalid")

    import databento as db

    client = db.Historical(load_api_key())
    job = find_job(client, job_id)
    state = str(job.get("state", "UNKNOWN")).lower()
    status_path = output / "latest_batch_status.json"
    write_json(
        status_path,
        {
            "schema_version": "cme6e_option_pin_design_batch_status.v1",
            "observed_at_utc": utc_now(),
            "hypothesis_id": HYPOTHESIS_ID,
            "campaign_id": CAMPAIGN_ID,
            "job_id": job_id,
            "job": job_summary(job),
        },
    )
    if state != "done":
        return state.upper(), status_path

    final_receipt = output / "phase_01_batch_acquisition_receipt.json"
    if final_receipt.is_file():
        return "COMPLETE", final_receipt
    raw_dir = output / "raw"
    raw_dir.mkdir(exist_ok=True)
    downloaded = client.batch.download(job_id, output_dir=raw_dir)
    paths = [Path(path).resolve() for path in downloaded]
    dbn_paths = [path for path in paths if path.name.endswith(".dbn.zst")]
    if not dbn_paths:
        dbn_paths = list(raw_dir.rglob("*.dbn.zst"))
    if not dbn_paths:
        raise BatchError("completed batch download contains no DBN files")
    payloads: list[dict[str, Any]] = []
    for path in sorted(dbn_paths):
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise BatchError("downloaded batch file escaped workspace") from exc
        payloads.append(
            {
                **validate_dbn(path),
                "path": str(path.relative_to(workspace)).replace("\\", "/"),
            }
        )
    cost = job.get("cost_usd")
    billed_size = job.get("billed_size")
    if cost is not None and (
        not math.isfinite(float(cost)) or float(cost) >= SPEND_CEILING_USD
    ):
        raise BatchError("completed batch job cost is outside authority")
    receipt = {
        "schema_version": "cme6e_option_pin_design_source_phase_01_batch.v1",
        "created_at_utc": utc_now(),
        "status": "DEFINITIONS_ACQUIRED_EVENT_DISCOVERY_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "job_id": job_id,
        "job": job_summary(job),
        "cost_usd": cost,
        "billed_size": billed_size,
        "payloads": payloads,
        "payload_file_count": len(payloads),
        "payload_raw_bytes": sum(item["raw_bytes"] for item in payloads),
        "bindings": {
            "plan_sha256": PLAN_SHA256,
            "revision_sha256": REVISION_SHA256,
            "authority_sha256": AUTHORITY_SHA256,
            "failed_batch_r1_receipt_sha256": FAILURE_SHA256,
            "batch_job_receipt_sha256": sha256_file(job_path),
            "latest_batch_status_sha256": sha256_file(status_path),
        },
        "api_method_counters": {
            "batch.submit_job": 1,
            "timeseries.get_range": 0,
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "statistics_payload_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    write_json(final_receipt, receipt)
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    manifest["status"] = "COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    manifest["phase_01_batch_acquisition_receipt_sha256"] = sha256_file(
        final_receipt
    )
    write_json(manifest_path, manifest)
    return "COMPLETE", final_receipt


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["submit", "resume"])
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        if args.action == "submit":
            path = submit(args.workspace)
            receipt = json.loads(path.read_text(encoding="ascii"))
            print(
                "CME6EOPTPIN_DESIGN_PHASE01_BATCH_SUBMITTED "
                f"job_id={receipt['job_id']} calls=1"
            )
            print(f"RECEIPT {path}")
            return 0
        state, path = resume(args.workspace)
        print(f"CME6EOPTPIN_DESIGN_PHASE01_BATCH_{state}")
        print(f"RECEIPT {path}")
        return 0
    except BatchError as exc:
        print(f"CME6EOPTPIN_DESIGN_PHASE01_BATCH_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
