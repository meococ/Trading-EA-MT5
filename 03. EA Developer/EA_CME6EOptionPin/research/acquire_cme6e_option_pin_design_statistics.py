"""Acquire all frozen per-expiry DESIGN statistics windows exactly once."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-SOURCE-001"
ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_definitions_batch_r2"
)
OUTPUT_NAME = "phase_02_statistics"
FINAL_RECEIPT = "phase_02_statistics_acquisition_receipt.json"
REQUESTS_FILE = "design_statistics_request_plan_r2.jsonl"
REQUESTS_SHA256 = "E2F45EC42F4629635C16D186EF2A5397B60E30079286D3A19B20ECCB5DC2EEB2"
QUOTES_FILE = "design_statistics_quotes.jsonl"
QUOTES_SHA256 = "86158F58983FD846559F04BC92318D85227C45391255A793D897291822ADDEF0"
QUOTE_SUMMARY_FILE = "design_statistics_quote_summary.json"
QUOTE_SUMMARY_SHA256 = (
    "0CB1776B22F4E7BF75D7075BE368BCC09A9E9D593B72A3D2749C7478F7D948A7"
)
DISCOVERY_FILE = "design_definition_discovery_receipt_r2.json"
DISCOVERY_SHA256 = (
    "2EAED406CCAFE9E0FC970F4629691ADFC559BF72C690AE1C93AF79C9B527654B"
)
PHASE_01_FILE = "phase_01_batch_acquisition_receipt.json"
PHASE_01_SHA256 = (
    "4073034E075CF32EA96FBB44CF71A30DDFCDE825982F47D8F6B261C670E41E25"
)
AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_SOURCE_PHASE_02_AUTHORITY.json"
)
AUTHORITY_SHA256 = (
    "A929BD63B0EDC9DA16E752530AE1F4A6A54A3E44D9F13187216B2CEA45CFD4FF"
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
EXPECTED_CALLS = 516
EXPECTED_STATISTICS_USD = 0.364300683141
EXPECTED_CUMULATIVE_USD = 5.01816410198832
SPEND_CEILING_USD = 10.0
MAX_WORKERS = 4
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DBN_VERSION = 3
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


class AcquisitionError(RuntimeError):
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


def require_file(workspace: Path, path: Path, expected_sha: str) -> Path:
    resolved = path.resolve() if path.is_absolute() else (workspace / path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise AcquisitionError(f"path escaped workspace: {path}") from exc
    if not resolved.is_file() or sha256_file(resolved) != expected_sha:
        raise AcquisitionError(f"missing or drifted input: {path}")
    return resolved


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]


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
        raise AcquisitionError("DATABENTO_API_KEY is absent or malformed")
    return key


def request_args(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": request["dataset"],
        "schema": request["schema"],
        "symbols": request["symbols"],
        "stype_in": request["stype_in"],
        "stype_out": request["stype_out"],
        "start": request["start"],
        "end": request["end"],
    }


def validate_raw(path: Path, request: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise AcquisitionError(f"empty statistics payload: {request['request_id']}")
    with path.open("rb") as handle:
        if handle.read(len(ZSTD_MAGIC)) != ZSTD_MAGIC:
            raise AcquisitionError(
                f"invalid Zstandard payload: {request['request_id']}"
            )
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
        raise AcquisitionError(
            f"DBN decode failed for {request['request_id']}: {exc}"
        ) from exc
    if (
        result["dataset"] != "GLBX.MDP3"
        or result["schema"] != "statistics"
        or result["dbn_version"] != DBN_VERSION
    ):
        raise AcquisitionError(
            f"DBN metadata mismatch: {request['request_id']}"
        )
    return result


def preflight(workspace: Path) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise AcquisitionError("workspace must be on D:")
    runtime = (workspace / RUNTIME_REL).resolve()
    if Path(sys.executable).resolve() != runtime:
        raise AcquisitionError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise AcquisitionError("Databento DBNv3 runtime mismatch")
    root = (workspace / ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise AcquisitionError("campaign root escaped workspace") from exc
    require_file(workspace, root / REQUESTS_FILE, REQUESTS_SHA256)
    require_file(workspace, root / QUOTES_FILE, QUOTES_SHA256)
    summary_path = require_file(
        workspace, root / QUOTE_SUMMARY_FILE, QUOTE_SUMMARY_SHA256
    )
    require_file(workspace, root / DISCOVERY_FILE, DISCOVERY_SHA256)
    require_file(workspace, root / PHASE_01_FILE, PHASE_01_SHA256)
    authority_path = require_file(workspace, AUTHORITY_REL, AUTHORITY_SHA256)
    require_file(workspace, OWNER_AUTHORITY_REL, OWNER_AUTHORITY_SHA256)
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    summary = json.loads(summary_path.read_text(encoding="ascii"))
    if (
        authority.get("paid_source_acquisition_authorized") is not True
        or authority.get("authorized_timeseries_calls") != EXPECTED_CALLS
        or authority.get("automatic_retry_authorized") is not False
        or summary.get("within_standing_authority") is not True
        or summary.get("statistics_request_count") != EXPECTED_CALLS
        or not math.isclose(
            float(summary.get("statistics_combined_estimated_usd")),
            EXPECTED_STATISTICS_USD,
            rel_tol=0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            float(summary.get("cumulative_campaign_estimated_usd")),
            EXPECTED_CUMULATIVE_USD,
            rel_tol=0,
            abs_tol=1e-12,
        )
        or float(summary["cumulative_campaign_estimated_usd"])
        >= SPEND_CEILING_USD
    ):
        raise AcquisitionError("phase-02 authority or quote contract mismatch")
    requests = load_jsonl(root / REQUESTS_FILE)
    quotes = load_jsonl(root / QUOTES_FILE)
    if len(requests) != EXPECTED_CALLS or len(quotes) != EXPECTED_CALLS:
        raise AcquisitionError("request or quote count mismatch")
    quote_by_id = {quote["request_id"]: quote for quote in quotes}
    if set(quote_by_id) != {request["request_id"] for request in requests}:
        raise AcquisitionError("request and quote identities differ")
    for request in requests:
        request["quote"] = quote_by_id[request["request_id"]]
    return root, requests, summary


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root, requests, quote_summary = preflight(workspace)
    output = (root / OUTPUT_NAME).resolve()
    if output.exists():
        raise AcquisitionError("exclusive phase-02 root exists; retry is forbidden")
    output.mkdir()
    raw_dir = output / "raw"
    raw_dir.mkdir()
    manifest_path = output / "download_manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": "cme6e_option_pin_design_statistics_manifest.v1",
        "status": "IN_FLIGHT",
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "authorized_calls": EXPECTED_CALLS,
        "attempted_calls": 0,
        "completed_calls": 0,
        "failed_calls": 0,
        "automatic_retry_calls": 0,
        "payloads": {},
        "failures": [],
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "bindings": {
            "authority_sha256": AUTHORITY_SHA256,
            "request_plan_sha256": REQUESTS_SHA256,
            "quotes_sha256": QUOTES_SHA256,
            "quote_summary_sha256": QUOTE_SUMMARY_SHA256,
            "discovery_receipt_sha256": DISCOVERY_SHA256,
            "phase_01_receipt_sha256": PHASE_01_SHA256,
        },
    }
    write_json(manifest_path, manifest)
    lock = threading.Lock()
    stop = threading.Event()
    local = threading.local()
    api_key = load_api_key()

    def acquire_one(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if stop.is_set():
            raise AcquisitionError("cancelled after a different request failed")
        request_id = request["request_id"]
        with lock:
            manifest["attempted_calls"] += 1
            manifest["updated_at_utc"] = utc_now()
            write_json(manifest_path, manifest)
        if not hasattr(local, "client"):
            import databento as db

            local.client = db.Historical(api_key)
        asset = "".join(
            character if character.isalnum() else "_"
            for character in str(request["asset"])
        )
        final = raw_dir / f"{request_id}_{asset}_statistics.dbn.zst"
        partial = final.with_suffix(final.suffix + ".partial")
        try:
            local.client.timeseries.get_range(
                **request_args(request), path=partial
            )
            raw_info = validate_raw(partial, request)
            os.replace(partial, final)
        except Exception as exc:
            stop.set()
            with lock:
                manifest["failed_calls"] += 1
                manifest["failures"].append(
                    {
                        "request_id": request_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    }
                )
                manifest["updated_at_utc"] = utc_now()
                write_json(manifest_path, manifest)
            raise
        payload = {
            **raw_info,
            "request_id": request_id,
            "event_id": request["event_id"],
            "path": str(final.relative_to(workspace)).replace("\\", "/"),
            "estimated_usd": float(request["quote"]["estimated_usd"]),
            "billable_bytes": int(request["quote"]["billable_bytes"]),
            "request": {
                key: request[key]
                for key in (
                    "dataset",
                    "schema",
                    "symbols",
                    "stype_in",
                    "stype_out",
                    "start",
                    "end",
                    "asset",
                    "underlying",
                    "expiration_utc",
                    "decision_utc",
                    "max_oi_reference_utc",
                )
            },
        }
        with lock:
            manifest["completed_calls"] += 1
            manifest["payloads"][request_id] = payload
            manifest["updated_at_utc"] = utc_now()
            write_json(manifest_path, manifest)
            completed = manifest["completed_calls"]
            if completed % 25 == 0 or completed == EXPECTED_CALLS:
                print(
                    f"CME6EOPTPIN_PHASE02_PROGRESS completed={completed}/"
                    f"{EXPECTED_CALLS}",
                    flush=True,
                )
        return request_id, payload

    failures: list[str] = []
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = [executor.submit(acquire_one, request) for request in requests]
    try:
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                failures.append(f"{type(exc).__name__}: {str(exc)[:500]}")
                stop.set()
                for pending in futures:
                    pending.cancel()
                break
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    if failures or manifest["completed_calls"] != EXPECTED_CALLS:
        manifest["status"] = "FAILED_INCOMPLETE_NO_RETRY"
        manifest["updated_at_utc"] = utc_now()
        write_json(manifest_path, manifest)
        failure = {
            "schema_version": "cme6e_option_pin_design_statistics_failure.v1",
            "created_at_utc": utc_now(),
            "status": "FAILED_INCOMPLETE_NO_RETRY",
            "hypothesis_id": HYPOTHESIS_ID,
            "campaign_id": CAMPAIGN_ID,
            "attempted_calls": manifest["attempted_calls"],
            "completed_calls": manifest["completed_calls"],
            "failed_calls": manifest["failed_calls"],
            "automatic_retry_calls": 0,
            "errors": failures,
            "manifest_sha256": sha256_file(manifest_path),
            "target_price_fields_used": [],
            "outcome_fields_used": [],
        }
        failure_path = output / "phase_02_failure_receipt.json"
        write_json(failure_path, failure)
        raise AcquisitionError(
            f"phase-02 incomplete: {manifest['completed_calls']}/{EXPECTED_CALLS}"
        )

    manifest["status"] = "COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    write_json(manifest_path, manifest)
    payloads = [manifest["payloads"][key] for key in sorted(manifest["payloads"])]
    receipt = {
        "schema_version": "cme6e_option_pin_design_statistics_acquisition.v1",
        "created_at_utc": utc_now(),
        "status": "STATISTICS_ACQUIRED_SEMANTICS_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "authorized_calls": EXPECTED_CALLS,
        "attempted_calls": manifest["attempted_calls"],
        "completed_calls": manifest["completed_calls"],
        "failed_calls": 0,
        "automatic_retry_calls": 0,
        "phase_02_estimated_usd": EXPECTED_STATISTICS_USD,
        "cumulative_campaign_estimated_usd": EXPECTED_CUMULATIVE_USD,
        "phase_02_billable_bytes": int(
            quote_summary["statistics_combined_billable_bytes"]
        ),
        "payload_file_count": len(payloads),
        "payload_raw_bytes": sum(int(payload["raw_bytes"]) for payload in payloads),
        "payloads": payloads,
        "bindings": {
            "authority_sha256": AUTHORITY_SHA256,
            "request_plan_sha256": REQUESTS_SHA256,
            "quotes_sha256": QUOTES_SHA256,
            "quote_summary_sha256": QUOTE_SUMMARY_SHA256,
            "discovery_receipt_sha256": DISCOVERY_SHA256,
            "phase_01_receipt_sha256": PHASE_01_SHA256,
            "download_manifest_sha256": sha256_file(manifest_path),
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "futures_reference_payload_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    receipt_path = root / FINAL_RECEIPT
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
            "CME6EOPTPIN_DESIGN_STATISTICS_ACQUIRED "
            f"calls={receipt['completed_calls']} "
            f"estimated_usd={receipt['phase_02_estimated_usd']:.12f}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"CME6EOPTPIN_DESIGN_STATISTICS_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
