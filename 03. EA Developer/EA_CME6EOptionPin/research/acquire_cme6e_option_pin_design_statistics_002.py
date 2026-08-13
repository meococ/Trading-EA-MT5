"""Acquire exactly the frozen HYP002 source-only statistics windows once."""

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


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-002"
CAMPAIGN_ID = "CME6EOPTPIN002-DESIGN-SOURCE-001"
DATASET = "GLBX.MDP3"
SCHEMA = "statistics"
REQUEST_COUNT = 516
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DBN_VERSION = 3
RUNTIME_REL = Path(
    "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
)
ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_pit_definitions"
)
REQUESTS_FILE = "design_statistics_request_plan_pit.jsonl"
QUOTES_FILE = "design_statistics_quotes_pit.jsonl"
QUOTE_SUMMARY_FILE = "design_statistics_quote_summary_pit.json"
RAW_DIR = "phase_02_statistics_raw"
MANIFEST_FILE = "phase_02_statistics_manifest_pit.json"
RECEIPT_FILE = "phase_02_statistics_acquisition_receipt_pit.json"
AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-002_PHASE_02_STATISTICS_AUTHORITY.json"
)
AUTHORITY_SHA256 = (
    "88CF258BD38305344A80ABDC2E1CA861A2F591EA5C4B1E1964E0A5547EDB0929"
)
OWNER_AUTHORITY_REL = Path(
    "03. EA Developer/EA_EventL1Replenishment/research/"
    "HYP-EVENT-L1-REPLEN-EURUSD-TICK-002_OWNER_AUTHORITY.json"
)
OWNER_AUTHORITY_SHA256 = (
    "CF68F81DB8717F7EDE8488DC7B17E78CD03486CA0FE225833BAD6847BF21B04D"
)
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


def require_file(workspace: Path, relative: Path, expected_sha: str) -> Path:
    path = (workspace / relative).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise AcquisitionError(f"path escaped workspace: {relative}") from exc
    if not path.is_file() or sha256_file(path) != expected_sha:
        raise AcquisitionError(f"missing or drifted authority input: {relative}")
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
        raise AcquisitionError("DATABENTO_API_KEY is absent or malformed")
    return key


def validate_dbn(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise AcquisitionError(f"empty HYP002 statistics DBN: {path.name}")
    with path.open("rb") as handle:
        if handle.read(len(ZSTD_MAGIC)) != ZSTD_MAGIC:
            raise AcquisitionError(f"invalid HYP002 DBN signature: {path.name}")
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
        raise AcquisitionError(f"HYP002 DBN decode failed: {path.name}") from exc
    if (
        result["dataset"] != DATASET
        or result["schema"] != SCHEMA
        or result["dbn_version"] != DBN_VERSION
    ):
        raise AcquisitionError(f"HYP002 DBN metadata mismatch: {path.name}")
    return result


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


def validate_contract(
    authority: dict[str, Any],
    summary: dict[str, Any],
    requests: list[dict[str, Any]],
    quotes: list[dict[str, Any]],
) -> None:
    if (
        authority.get("hypothesis_id") != HYPOTHESIS_ID
        or authority.get("campaign_id") != CAMPAIGN_ID
        or authority.get("paid_source_acquisition_authorized") is not True
        or authority.get("authorized_timeseries_calls") != REQUEST_COUNT
        or authority.get("authorized_batch_calls") != 0
        or authority.get("automatic_retry_authorized") is not False
        or authority.get("partial_resume_authorized") is not False
        or authority.get("target_or_outcome_authorized") is not False
        or authority.get("futures_reference_authorized") is not False
        or authority.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
    ):
        raise AcquisitionError("HYP002 statistics authority is not armed")
    if (
        summary.get("hypothesis_id") != HYPOTHESIS_ID
        or summary.get("campaign_id") != CAMPAIGN_ID
        or summary.get("within_standing_authority") is not True
        or summary.get("statistics_request_count") != REQUEST_COUNT
        or summary.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
        or not math.isfinite(
            float(summary.get("cumulative_related_research_estimated_usd", math.nan))
        )
        or float(summary["cumulative_related_research_estimated_usd"])
        >= float(summary.get("cumulative_spend_ceiling_usd", 0.0))
    ):
        raise AcquisitionError("HYP002 quote is outside standing authority")
    if len(requests) != REQUEST_COUNT or len(quotes) != REQUEST_COUNT:
        raise AcquisitionError("HYP002 request or quote count drifted")
    request_ids = [str(item.get("request_id", "")) for item in requests]
    quote_ids = [str(item.get("request_id", "")) for item in quotes]
    if (
        len(set(request_ids)) != REQUEST_COUNT
        or set(request_ids) != set(quote_ids)
        or any(
            request.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
            or request.get("definition_selection")
            != "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT"
            for request in requests
        )
    ):
        raise AcquisitionError("HYP002 request identity or policy drifted")
    quoted_cost = sum(float(item["estimated_usd"]) for item in quotes)
    quoted_bytes = sum(int(item["billable_bytes"]) for item in quotes)
    if (
        not math.isclose(
            quoted_cost,
            float(summary["statistics_combined_estimated_usd"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or quoted_bytes != int(summary["statistics_combined_billable_bytes"])
    ):
        raise AcquisitionError("HYP002 quote totals drifted")


def execute(workspace: Path) -> Path:
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
    authority_path = require_file(workspace, AUTHORITY_REL, AUTHORITY_SHA256)
    require_file(workspace, OWNER_AUTHORITY_REL, OWNER_AUTHORITY_SHA256)
    authority = json.loads(authority_path.read_text(encoding="ascii"))

    root = (workspace / ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise AcquisitionError("HYP002 output root escaped workspace") from exc
    requests_path = root / REQUESTS_FILE
    quotes_path = root / QUOTES_FILE
    summary_path = root / QUOTE_SUMMARY_FILE
    for path, authority_key in (
        (requests_path, "statistics_request_plan_sha256"),
        (quotes_path, "statistics_quotes_sha256"),
        (summary_path, "quote_summary_sha256"),
    ):
        if (
            not path.is_file()
            or sha256_file(path) != str(authority.get(authority_key, ""))
        ):
            raise AcquisitionError(f"HYP002 frozen input drifted: {path.name}")
    requests = load_jsonl(requests_path)
    quotes = load_jsonl(quotes_path)
    summary = json.loads(summary_path.read_text(encoding="ascii"))
    validate_contract(authority, summary, requests, quotes)

    raw_dir = root / RAW_DIR
    manifest_path = root / MANIFEST_FILE
    receipt_path = root / RECEIPT_FILE
    if raw_dir.exists() or manifest_path.exists() or receipt_path.exists():
        raise AcquisitionError("exclusive HYP002 statistics root exists; retry forbidden")
    raw_dir.mkdir()
    manifest: dict[str, Any] = {
        "schema_version": "cme6e_option_pin_statistics_manifest.v2",
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "status": "IN_FLIGHT",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "authorized_timeseries_calls": REQUEST_COUNT,
        "timeseries_calls": 0,
        "batch_calls": 0,
        "automatic_retry_authorized": False,
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "authority_sha256": sha256_file(authority_path),
        "statistics_requests_sha256": sha256_file(requests_path),
        "statistics_quotes_sha256": sha256_file(quotes_path),
        "quote_summary_sha256": sha256_file(summary_path),
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "payloads": [],
    }
    write_json(manifest_path, manifest)

    import databento as db

    client = db.Historical(load_api_key())
    for index, request in enumerate(requests, 1):
        request_id = str(request["request_id"])
        final = raw_dir / f"{request_id}.statistics.dbn.zst"
        partial = raw_dir / f"{request_id}.statistics.dbn.zst.partial"
        try:
            client.timeseries.get_range(**request_args(request), path=partial)
        except Exception as exc:
            manifest["status"] = "FAILED_NO_RETRY"
            manifest["updated_at_utc"] = utc_now()
            manifest["failed_request_id"] = request_id
            manifest["failure_type"] = type(exc).__name__
            write_json(manifest_path, manifest)
            raise AcquisitionError(
                f"paid HYP002 request failed without retry: {request_id}"
            ) from exc
        manifest["timeseries_calls"] += 1
        raw_info = validate_dbn(partial)
        os.replace(partial, final)
        manifest["payloads"].append(
            {
                "request_id": request_id,
                "event_id": request["event_id"],
                "path": str(final.relative_to(workspace)).replace("\\", "/"),
                **raw_info,
            }
        )
        manifest["updated_at_utc"] = utc_now()
        write_json(manifest_path, manifest)
        if index % 25 == 0 or index == REQUEST_COUNT:
            print(
                f"CME6EOPTPIN002_STATISTICS_PROGRESS {index}/{REQUEST_COUNT}",
                flush=True,
            )

    if manifest["timeseries_calls"] != REQUEST_COUNT:
        raise AcquisitionError("HYP002 statistics call count did not close")
    manifest["status"] = "COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    write_json(manifest_path, manifest)
    receipt = {
        "schema_version": "cme6e_option_pin_statistics_acquisition_receipt.v2",
        "created_at_utc": utc_now(),
        "status": "STATISTICS_ACQUIRED_SEMANTICS_PENDING",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "statistics_request_count": REQUEST_COUNT,
        "timeseries_calls": manifest["timeseries_calls"],
        "batch_calls": 0,
        "quoted_statistics_estimated_usd": summary[
            "statistics_combined_estimated_usd"
        ],
        "quoted_statistics_billable_bytes": summary[
            "statistics_combined_billable_bytes"
        ],
        "cumulative_related_research_estimated_usd": summary[
            "cumulative_related_research_estimated_usd"
        ],
        "payload_count": len(manifest["payloads"]),
        "payload_raw_bytes": sum(
            int(payload["raw_bytes"]) for payload in manifest["payloads"]
        ),
        "payloads": manifest["payloads"],
        "bindings": {
            "authority_sha256": sha256_file(authority_path),
            "owner_authority_sha256": OWNER_AUTHORITY_SHA256,
            "statistics_requests_sha256": sha256_file(requests_path),
            "statistics_quotes_sha256": sha256_file(quotes_path),
            "quote_summary_sha256": sha256_file(summary_path),
            "manifest_sha256": sha256_file(manifest_path),
        },
        "api_method_counters": {
            "metadata.get_cost": 0,
            "metadata.get_billable_size": 0,
            "timeseries.get_range": manifest["timeseries_calls"],
            "batch": 0,
        },
        "definition_selection": "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT",
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "futures_reference_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
        "validation_or_holdout_authorized": False,
        "optimization_authorized": False,
        "paper_or_live_authorized": False,
    }
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
            "CME6EOPTPIN002_STATISTICS_ACQUIRED "
            f"calls={receipt['timeseries_calls']} "
            f"payloads={receipt['payload_count']} "
            f"quoted_usd={receipt['quoted_statistics_estimated_usd']:.12f}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"CME6EOPTPIN002_STATISTICS_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

