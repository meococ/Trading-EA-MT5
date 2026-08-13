"""Quote every frozen source-derived DESIGN statistics event window."""

from __future__ import annotations

import argparse
import hashlib
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
BATCH_ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_definitions_batch_r2"
)
PHASE_01_RECEIPT = "phase_01_batch_acquisition_receipt.json"
DISCOVERY_RECEIPT = "design_definition_discovery_receipt_r2.json"
REQUESTS_FILE = "design_statistics_request_plan_r2.jsonl"
QUOTES_FILE = "design_statistics_quotes.jsonl"
SUMMARY_FILE = "design_statistics_quote_summary.json"
SPEND_CEILING_USD = 10.0
MAX_WORKERS = 6


class QuoteError(RuntimeError):
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


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True, ensure_ascii=True) + "\n")
    os.replace(temporary, path)


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
        raise QuoteError("DATABENTO_API_KEY is absent or malformed")
    return key


def load_requests(path: Path) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        if not line.strip():
            continue
        request = json.loads(line)
        if (
            request.get("schema_version")
            != "cme6e_option_pin_statistics_request.v1"
            or request.get("dataset") != "GLBX.MDP3"
            or request.get("schema") != "statistics"
            or request.get("stype_in") != "parent"
            or request.get("stype_out") != "instrument_id"
            or len(request.get("symbols", [])) != 1
            or not request.get("request_id")
            or not request.get("event_id")
        ):
            raise QuoteError(f"invalid statistics request at line {line_number}")
        requests.append(request)
    if not requests:
        raise QuoteError("statistics request plan is empty")
    ids = [request["request_id"] for request in requests]
    if len(ids) != len(set(ids)):
        raise QuoteError("statistics request IDs are not unique")
    return requests


def request_args(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": request["dataset"],
        "schema": request["schema"],
        "symbols": request["symbols"],
        "stype_in": request["stype_in"],
        "start": request["start"],
        "end": request["end"],
    }


def quote_all(requests: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    import databento as db

    local = threading.local()

    def quote_one(request: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = db.Historical(api_key)
        args = request_args(request)
        cost = float(
            local.client.metadata.get_cost(mode="historical-streaming", **args)
        )
        size = int(local.client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0 or size <= 0:
            raise QuoteError(f"invalid quote for {request['request_id']}")
        return {
            "schema_version": "cme6e_option_pin_statistics_quote.v1",
            "request_id": request["request_id"],
            "event_id": request["event_id"],
            "estimated_usd": cost,
            "billable_bytes": size,
        }

    quotes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(quote_one, request): request for request in requests}
        for future in as_completed(futures):
            request = futures[future]
            try:
                quotes.append(future.result())
            except Exception as exc:
                if isinstance(exc, QuoteError):
                    raise
                raise QuoteError(
                    f"quote failed for {request['request_id']}: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
    return sorted(quotes, key=lambda value: value["request_id"])


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / BATCH_ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise QuoteError("batch root escaped workspace") from exc
    phase_01_path = root / PHASE_01_RECEIPT
    discovery_path = root / DISCOVERY_RECEIPT
    requests_path = root / REQUESTS_FILE
    if not phase_01_path.is_file() or not discovery_path.is_file() or not requests_path.is_file():
        raise QuoteError("phase-01 or discovery artifacts are missing")
    phase_01 = json.loads(phase_01_path.read_text(encoding="ascii"))
    discovery = json.loads(discovery_path.read_text(encoding="ascii"))
    if (
        phase_01.get("status") != "DEFINITIONS_ACQUIRED_EVENT_DISCOVERY_PENDING"
        or phase_01.get("target_price_fields_used") != []
        or phase_01.get("outcome_fields_used") != []
        or discovery.get("verdict") != "PHASE_01_PASS"
        or discovery.get("target_price_fields_used") != []
        or discovery.get("outcome_fields_used") != []
    ):
        raise QuoteError("phase-01 source contract has not passed")
    phase_01_cost = phase_01.get("cost_usd")
    if phase_01_cost is None or not math.isfinite(float(phase_01_cost)):
        raise QuoteError("completed batch job has no finite cost")
    requests = load_requests(requests_path)
    if len(requests) != int(discovery.get("statistics_request_count", -1)):
        raise QuoteError("statistics request count drifted from discovery receipt")
    quotes = quote_all(requests, load_api_key())
    quote_path = root / QUOTES_FILE
    write_jsonl(quote_path, quotes)
    statistics_cost = sum(float(quote["estimated_usd"]) for quote in quotes)
    statistics_bytes = sum(int(quote["billable_bytes"]) for quote in quotes)
    cumulative = float(phase_01_cost) + statistics_cost
    summary = {
        "schema_version": "cme6e_option_pin_statistics_quote_summary.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "statistics_request_count": len(requests),
        "metadata_get_cost_calls": len(requests),
        "metadata_get_billable_size_calls": len(requests),
        "phase_01_batch_cost_usd": float(phase_01_cost),
        "phase_01_batch_billed_size": phase_01.get("billed_size"),
        "statistics_combined_estimated_usd": statistics_cost,
        "statistics_combined_billable_bytes": statistics_bytes,
        "cumulative_campaign_estimated_usd": cumulative,
        "cumulative_spend_ceiling_usd": SPEND_CEILING_USD,
        "within_standing_authority": bool(cumulative < SPEND_CEILING_USD),
        "failed_stream_local_payload_bytes": 0,
        "failed_stream_charge_treatment": "ZERO_RECEIVED_BYTES_UNDER_INCREMENTAL_STREAMING_BILLING",
        "bindings": {
            "phase_01_acquisition_receipt_sha256": sha256_file(phase_01_path),
            "discovery_receipt_sha256": sha256_file(discovery_path),
            "statistics_requests_sha256": sha256_file(requests_path),
            "statistics_quotes_sha256": sha256_file(quote_path),
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "statistics_payload_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    summary_path = root / SUMMARY_FILE
    write_json(summary_path, summary)
    return summary_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        summary_path = execute(args.workspace)
        summary = json.loads(summary_path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN_DESIGN_STATISTICS_QUOTED "
            f"requests={summary['statistics_request_count']} "
            f"statistics_usd={summary['statistics_combined_estimated_usd']:.12f} "
            f"cumulative_usd={summary['cumulative_campaign_estimated_usd']:.12f} "
            f"authorized={summary['within_standing_authority']}"
        )
        print(f"RECEIPT {summary_path}")
        return 0
    except QuoteError as exc:
        print(f"CME6EOPTPIN_DESIGN_STATISTICS_QUOTE_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
