"""Acquire each frozen 6E futures-reference window exactly once without retry."""

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
CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-FUTURES-001"
ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/CME6EOPTPIN001-DESIGN-SOURCE-001/"
    "phase_01_definitions_batch_r2/phase_03_futures_reference"
)
RESEARCH_REL = Path("03. EA Developer/EA_CME6EOptionPin/research")
OWNER_AUTHORITY_REL = Path(
    "03. EA Developer/EA_EventL1Replenishment/research/"
    "HYP-EVENT-L1-REPLEN-EURUSD-TICK-002_OWNER_AUTHORITY.json"
)
AUTHORITY_FILE = f"{HYPOTHESIS_ID}_FUTURES_REFERENCE_AUTHORITY.json"
REQUESTS_FILE = "futures_reference_request_plan.jsonl"
CONDITIONS_FILE = "futures_reference_dataset_conditions.json"
QUOTES_FILE = "futures_reference_quotes.jsonl"
QUOTE_SUMMARY_FILE = "futures_reference_quote_summary.json"
OUTPUT_DIR = "payloads_once"
MANIFEST_FILE = "futures_reference_download_manifest.json"
FINAL_RECEIPT = "futures_reference_acquisition_receipt.json"
FAILURE_RECEIPT = "futures_reference_acquisition_failure.json"
EXPECTED_CALLS = 509
EXPECTED_COST_USD = 1.353354826562
EXPECTED_CUMULATIVE_USD = 6.371518928550319
EXPECTED_BILLABLE_BYTES = 807307600
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


def contained(workspace: Path, path: Path) -> Path:
    resolved = path.resolve() if path.is_absolute() else (workspace / path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise AcquisitionError(f"path escaped workspace: {path}") from exc
    return resolved


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
        raise AcquisitionError(f"empty futures payload: {request['request_id']}")
    with path.open("rb") as handle:
        if handle.read(len(ZSTD_MAGIC)) != ZSTD_MAGIC:
            raise AcquisitionError(f"invalid Zstandard payload: {request['request_id']}")
    try:
        import databento as db

        metadata = db.DBNStore.from_file(path).metadata
        schema = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        info = {
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
        info["dataset"] != "GLBX.MDP3"
        or info["schema"] != "mbp-1"
        or info["dbn_version"] != DBN_VERSION
    ):
        raise AcquisitionError(f"DBN metadata mismatch: {request['request_id']}")
    return info


def preflight(workspace: Path) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise AcquisitionError("workspace must be on D:")
    runtime = contained(
        workspace,
        Path("02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"),
    )
    if Path(sys.executable).resolve() != runtime:
        raise AcquisitionError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise AcquisitionError("Databento DBNv3 runtime mismatch")
    root = contained(workspace, ROOT_REL)
    research = contained(workspace, RESEARCH_REL)
    authority_path = research / AUTHORITY_FILE
    owner_path = contained(workspace, OWNER_AUTHORITY_REL)
    required = {
        "requests_sha256": root / REQUESTS_FILE,
        "conditions_sha256": root / CONDITIONS_FILE,
        "quotes_sha256": root / QUOTES_FILE,
        "quote_summary_sha256": root / QUOTE_SUMMARY_FILE,
        "owner_authority_sha256": owner_path,
    }
    if not authority_path.is_file() or not all(path.is_file() for path in required.values()):
        raise AcquisitionError("authority or quoted input is missing")
    authority = json.loads(authority_path.read_text(encoding="ascii"))
    bindings = authority.get("bindings", {})
    for name, path in required.items():
        if sha256_file(path) != bindings.get(name):
            raise AcquisitionError(f"drifted authority binding: {name}")
    summary = json.loads((root / QUOTE_SUMMARY_FILE).read_text(encoding="ascii"))
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    policy = owner.get("standing_research_acquisition_policy", {})
    if (
        authority.get("authorized") is not True
        or authority.get("authorized_timeseries_calls") != EXPECTED_CALLS
        or authority.get("automatic_retry_authorized") is not False
        or summary.get("frozen_request_count") != EXPECTED_CALLS
        or summary.get("within_standing_authority") is not True
        or policy.get("approved") is not True
        or policy.get("aggregate_campaign_cost_must_be_strictly_below") != SPEND_CEILING_USD
        or not math.isclose(float(summary.get("futures_estimated_usd")), EXPECTED_COST_USD, rel_tol=0, abs_tol=1e-12)
        or not math.isclose(float(summary.get("cumulative_campaign_estimated_usd")), EXPECTED_CUMULATIVE_USD, rel_tol=0, abs_tol=1e-12)
        or int(summary.get("futures_billable_bytes")) != EXPECTED_BILLABLE_BYTES
        or float(summary["cumulative_campaign_estimated_usd"]) >= SPEND_CEILING_USD
    ):
        raise AcquisitionError("authority or quote contract mismatch")
    requests = load_jsonl(root / REQUESTS_FILE)
    quotes = load_jsonl(root / QUOTES_FILE)
    if len(requests) != EXPECTED_CALLS or len(quotes) != EXPECTED_CALLS:
        raise AcquisitionError("request or quote count mismatch")
    quote_by_id = {row["request_id"]: row for row in quotes}
    if set(quote_by_id) != {row["request_id"] for row in requests}:
        raise AcquisitionError("request and quote identities differ")
    for request in requests:
        request["quote"] = quote_by_id[request["request_id"]]
    return root, requests, authority


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root, requests, authority = preflight(workspace)
    output = (root / OUTPUT_DIR).resolve()
    if output.exists():
        raise AcquisitionError("exclusive futures payload root exists; retry is forbidden")
    output.mkdir()
    raw_dir = output / "raw"
    raw_dir.mkdir()
    manifest_path = output / MANIFEST_FILE
    manifest: dict[str, Any] = {
        "schema_version": "cme6e_option_pin_futures_manifest.v1",
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
        "bindings": authority["bindings"],
    }
    write_json(manifest_path, manifest)
    lock = threading.Lock()
    stop = threading.Event()
    local = threading.local()
    api_key = load_api_key()

    def acquire_one(request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if stop.is_set():
            raise AcquisitionError("cancelled after another request failed")
        request_id = request["request_id"]
        with lock:
            manifest["attempted_calls"] += 1
            manifest["updated_at_utc"] = utc_now()
            write_json(manifest_path, manifest)
        if not hasattr(local, "client"):
            import databento as db

            local.client = db.Historical(api_key)
        final = raw_dir / f"{request_id}_{request['underlying']}_mbp1.dbn.zst"
        partial = final.with_suffix(final.suffix + ".partial")
        try:
            local.client.timeseries.get_range(**request_args(request), path=partial)
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
                    "underlying",
                    "expiration_utc",
                    "decision_utc",
                    "pin_strike",
                    "pin_total_oi",
                    "dataset_condition_date",
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
                    f"CME6EOPTPIN_FUTURES_PROGRESS completed={completed}/{EXPECTED_CALLS}",
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
            "schema_version": "cme6e_option_pin_futures_failure.v1",
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
        write_json(output / FAILURE_RECEIPT, failure)
        raise AcquisitionError(
            f"futures acquisition incomplete: {manifest['completed_calls']}/{EXPECTED_CALLS}"
        )

    manifest["status"] = "COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    write_json(manifest_path, manifest)
    payloads = [manifest["payloads"][key] for key in sorted(manifest["payloads"])]
    receipt = {
        "schema_version": "cme6e_option_pin_futures_acquisition.v1",
        "created_at_utc": utc_now(),
        "status": "FUTURES_ACQUIRED_REFERENCE_ANALYSIS_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "authorized_calls": EXPECTED_CALLS,
        "attempted_calls": manifest["attempted_calls"],
        "completed_calls": manifest["completed_calls"],
        "failed_calls": 0,
        "automatic_retry_calls": 0,
        "futures_estimated_usd": EXPECTED_COST_USD,
        "cumulative_campaign_estimated_usd": EXPECTED_CUMULATIVE_USD,
        "futures_billable_bytes": EXPECTED_BILLABLE_BYTES,
        "payload_file_count": len(payloads),
        "payload_raw_bytes": sum(int(row["raw_bytes"]) for row in payloads),
        "payloads": payloads,
        "bindings": {
            **authority["bindings"],
            "authority_sha256": sha256_file(
                workspace / RESEARCH_REL / AUTHORITY_FILE
            ),
            "download_manifest_sha256": sha256_file(manifest_path),
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "reference_analysis_authorized": True,
        "eurusd_target_authorized": False,
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
        path = execute(args.workspace)
        receipt = json.loads(path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN_FUTURES_ACQUIRED "
            f"calls={receipt['completed_calls']} "
            f"estimated_usd={receipt['futures_estimated_usd']:.12f}"
        )
        print(f"RECEIPT {path}")
        return 0
    except AcquisitionError as exc:
        print(f"CME6EOPTPIN_FUTURES_ACQUISITION_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
