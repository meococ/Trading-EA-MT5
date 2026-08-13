"""Freeze and quote the exact 509-event DESIGN futures-reference campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-FUTURES-001"
ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/CME6EOPTPIN001-DESIGN-SOURCE-001/"
    "phase_01_definitions_batch_r2"
)
RESEARCH_REL = Path("03. EA Developer/EA_CME6EOptionPin/research")
SOURCE_RECEIPT = "design_source_semantics_receipt.json"
SOURCE_ANALYSIS = "design_source_semantics_analysis.json"
SOURCE_PINS = "design_source_pins.csv"
ADDENDUM = f"{HYPOTHESIS_ID}_FUTURES_REFERENCE_ADDENDUM.md"
OUTPUT_DIR = "phase_03_futures_reference"
REQUESTS_FILE = "futures_reference_request_plan.jsonl"
CONDITIONS_FILE = "futures_reference_dataset_conditions.json"
QUOTES_FILE = "futures_reference_quotes.jsonl"
SUMMARY_FILE = "futures_reference_quote_summary.json"
EXCLUDED_DEGRADED_DATES = {
    "2019-02-22",
    "2019-03-13",
    "2020-02-28",
    "2020-07-01",
}
EXPECTED_SOURCE_PINS = 513
EXPECTED_REQUESTS = 509
SPEND_CEILING_USD = 10.0
MAX_WORKERS = 6


class QuoteError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise QuoteError(f"timestamp is not UTC: {value}")
    return parsed


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()[:16].upper()


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


def build_requests(pins: list[dict[str, str]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for pin in pins:
        decision = parse_utc(pin["decision_utc"])
        event_date = decision.date().isoformat()
        if event_date in EXCLUDED_DEGRADED_DATES:
            continue
        underlying = pin["underlying"].strip()
        if not underlying.startswith("6E") or not underlying.isalnum():
            raise QuoteError(f"invalid raw futures underlying: {underlying!r}")
        start = decision - timedelta(seconds=60)
        identity = (
            f"{HYPOTHESIS_ID}|{pin['event_id']}|{underlying}|"
            f"{iso_utc(start)}|{iso_utc(decision)}"
        )
        requests.append(
            {
                "schema_version": "cme6e_option_pin_futures_request.v1",
                "request_id": stable_id(identity),
                "event_id": pin["event_id"],
                "dataset": "GLBX.MDP3",
                "schema": "mbp-1",
                "symbols": [underlying],
                "stype_in": "raw_symbol",
                "stype_out": "instrument_id",
                "start": iso_utc(start),
                "end": iso_utc(decision),
                "underlying": underlying,
                "expiration_utc": pin["expiration_utc"],
                "decision_utc": pin["decision_utc"],
                "pin_strike": float(pin["pin_strike"]),
                "pin_total_oi": int(pin["pin_total_oi"]),
                "dataset_condition_date": event_date,
            }
        )
    requests.sort(key=lambda row: (row["decision_utc"], row["event_id"]))
    ids = [row["request_id"] for row in requests]
    events = [row["event_id"] for row in requests]
    if len(requests) != EXPECTED_REQUESTS:
        raise QuoteError(f"frozen request count is {len(requests)}, expected 509")
    if len(set(ids)) != len(ids) or len(set(events)) != len(events):
        raise QuoteError("duplicate request or event identity")
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
        cost = float(local.client.metadata.get_cost(mode="historical-streaming", **args))
        size = int(local.client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise QuoteError(f"invalid quote for {request['request_id']}")
        return {
            "schema_version": "cme6e_option_pin_futures_quote.v1",
            "request_id": request["request_id"],
            "event_id": request["event_id"],
            "estimated_usd": cost,
            "billable_bytes": size,
        }

    quotes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(quote_one, row): row for row in requests}
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
    return sorted(quotes, key=lambda row: row["request_id"])


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / ROOT_REL).resolve()
    research = (workspace / RESEARCH_REL).resolve()
    for candidate in (root, research):
        try:
            candidate.relative_to(workspace)
        except ValueError as exc:
            raise QuoteError("campaign path escaped workspace") from exc
    receipt_path = root / SOURCE_RECEIPT
    analysis_path = root / SOURCE_ANALYSIS
    pins_path = root / SOURCE_PINS
    addendum_path = research / ADDENDUM
    if not all(path.is_file() for path in (receipt_path, analysis_path, pins_path, addendum_path)):
        raise QuoteError("source-gate or addendum artifact is missing")
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    analysis = json.loads(analysis_path.read_text(encoding="ascii"))
    if (
        receipt.get("verdict") != "SOURCE_DESIGN_PASS"
        or receipt.get("unique_positive_pin_events") != EXPECTED_SOURCE_PINS
        or analysis.get("trade_direction_produced") is not False
        or analysis.get("target_price_fields_used") != []
        or analysis.get("outcome_fields_used") != []
        or not all(analysis.get("gates", {}).values())
    ):
        raise QuoteError("source gate has not passed cleanly")
    with pins_path.open("r", encoding="ascii", newline="") as handle:
        pins = list(csv.DictReader(handle))
    if len(pins) != EXPECTED_SOURCE_PINS:
        raise QuoteError("source pin count drifted")
    requests = build_requests(pins)
    api_key = load_api_key()

    import databento as db

    condition_rows = db.Historical(api_key).metadata.get_dataset_condition(
        "GLBX.MDP3", "2018-01-01", "2023-01-01"
    )
    by_date = {row["date"]: row for row in condition_rows}
    selected_conditions: list[dict[str, str]] = []
    for request in requests:
        date = request["dataset_condition_date"]
        condition = by_date.get(date)
        if condition is None or condition.get("condition") != "available":
            raise QuoteError(f"non-available futures event date: {date}: {condition}")
        selected_conditions.append(condition)
    degraded_observed = {
        date
        for date in EXCLUDED_DEGRADED_DATES
        if by_date.get(date, {}).get("condition") == "degraded"
    }
    if degraded_observed != EXCLUDED_DEGRADED_DATES:
        raise QuoteError("frozen degraded-date condition no longer matches provider")

    output = root / OUTPUT_DIR
    output.mkdir(exist_ok=True)
    requests_path = output / REQUESTS_FILE
    conditions_path = output / CONDITIONS_FILE
    quotes_path = output / QUOTES_FILE
    write_jsonl(requests_path, requests)
    write_json(
        conditions_path,
        {
            "schema_version": "cme6e_option_pin_futures_conditions.v1",
            "created_at_utc": utc_now(),
            "dataset": "GLBX.MDP3",
            "excluded_degraded_dates": sorted(EXCLUDED_DEGRADED_DATES),
            "selected_event_dates": sorted(
                {row["dataset_condition_date"] for row in requests}
            ),
            "selected_conditions": sorted(
                {json.dumps(row, sort_keys=True) for row in selected_conditions}
            ),
        },
    )
    quotes = quote_all(requests, api_key)
    write_jsonl(quotes_path, quotes)
    future_cost = sum(float(row["estimated_usd"]) for row in quotes)
    future_bytes = sum(int(row["billable_bytes"]) for row in quotes)
    source_campaign_cost = float(
        json.loads((root / "phase_02_statistics_acquisition_receipt.json").read_text(encoding="ascii"))[
            "cumulative_campaign_estimated_usd"
        ]
    )
    cumulative = source_campaign_cost + future_cost
    summary = {
        "schema_version": "cme6e_option_pin_futures_quote_summary.v1",
        "created_at_utc": utc_now(),
        "status": "FUTURES_REFERENCE_QUOTED",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "source_pin_count": EXPECTED_SOURCE_PINS,
        "excluded_degraded_event_count": 4,
        "frozen_request_count": len(requests),
        "metadata_get_cost_calls": len(requests),
        "metadata_get_billable_size_calls": len(requests),
        "futures_estimated_usd": future_cost,
        "futures_billable_bytes": future_bytes,
        "source_campaign_estimated_usd": source_campaign_cost,
        "cumulative_campaign_estimated_usd": cumulative,
        "standing_authority_ceiling_usd": SPEND_CEILING_USD,
        "within_standing_authority": bool(cumulative < SPEND_CEILING_USD),
        "bindings": {
            "source_receipt_sha256": sha256_file(receipt_path),
            "source_analysis_sha256": sha256_file(analysis_path),
            "source_pins_sha256": sha256_file(pins_path),
            "addendum_sha256": sha256_file(addendum_path),
            "requests_sha256": sha256_file(requests_path),
            "conditions_sha256": sha256_file(conditions_path),
            "quotes_sha256": sha256_file(quotes_path),
        },
        "futures_reference_payload_authorized": bool(cumulative < SPEND_CEILING_USD),
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    summary_path = output / SUMMARY_FILE
    write_json(summary_path, summary)
    return summary_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        path = execute(args.workspace)
        summary = json.loads(path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN_FUTURES_QUOTED "
            f"requests={summary['frozen_request_count']} "
            f"futures_usd={summary['futures_estimated_usd']:.12f} "
            f"cumulative_usd={summary['cumulative_campaign_estimated_usd']:.12f} "
            f"authorized={summary['within_standing_authority']}"
        )
        print(f"RECEIPT {path}")
        return 0
    except QuoteError as exc:
        print(f"CME6EOPTPIN_FUTURES_QUOTE_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
