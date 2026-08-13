"""Analyze the frozen futures-reference payloads without opening EURUSD outcomes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from decimal import Decimal
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
REQUESTS_FILE = "futures_reference_request_plan.jsonl"
CONDITIONS_FILE = "futures_reference_dataset_conditions.json"
QUOTE_SUMMARY_FILE = "futures_reference_quote_summary.json"
PAYLOAD_DIR = "payloads_once"
MANIFEST_FILE = "futures_reference_download_manifest.json"
FAILURE_RECEIPT = "futures_reference_acquisition_failure.json"
RESULTS_FILE = "futures_reference_results.csv"
DIRECTIONS_FILE = "futures_reference_directions.csv"
ANALYSIS_FILE = "futures_reference_analysis.json"
RECEIPT_FILE = "futures_reference_analysis_receipt.json"
EXPECTED_EVENTS = 509
MIN_COVERAGE = 0.95


class AnalysisError(RuntimeError):
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


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]


def normalize_frame(frame: Any) -> Any:
    import pandas as pd

    working = frame.copy()
    if working.index.name == "ts_recv":
        working["ts_recv"] = pd.to_datetime(working.index, utc=True)
        working = working.reset_index(drop=True)
    elif "ts_recv" in working.columns:
        working["ts_recv"] = pd.to_datetime(working["ts_recv"], utc=True)
    else:
        raise AnalysisError("mbp-1 payload has no ts_recv")
    return working


def select_reference(frame: Any, request: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import pandas as pd

    working = normalize_frame(frame)
    required = {"ts_recv", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00", "symbol"}
    if not required.issubset(working.columns):
        raise AnalysisError(f"mbp-1 columns missing: {sorted(required - set(working.columns))}")
    start = pd.Timestamp(request["start"])
    end = pd.Timestamp(request["end"])
    symbols = set(working["symbol"].dropna().astype(str))
    symbol_binding_valid = bool(not symbols or symbols == {request["underlying"]})
    in_window = (working["ts_recv"] >= start) & (working["ts_recv"] < end)
    finite = (
        np.isfinite(working["bid_px_00"].astype(float))
        & np.isfinite(working["ask_px_00"].astype(float))
        & np.isfinite(working["bid_sz_00"].astype(float))
        & np.isfinite(working["ask_sz_00"].astype(float))
    )
    valid = working.loc[
        in_window
        & finite
        & (working["bid_px_00"] > 0)
        & (working["ask_px_00"] > 0)
        & (working["bid_px_00"] < working["ask_px_00"])
        & (working["bid_sz_00"] > 0)
        & (working["ask_sz_00"] > 0)
        & (working["symbol"].astype(str) == request["underlying"])
    ].sort_values("ts_recv", kind="stable")
    base = {
        "event_id": request["event_id"],
        "request_id": request["request_id"],
        "underlying": request["underlying"],
        "expiration_utc": request["expiration_utc"],
        "decision_utc": request["decision_utc"],
        "pin_strike": request["pin_strike"],
        "payload_rows": len(working),
        "receive_window_rows": int(in_window.sum()),
        "post_decision_receive_rows": int((working["ts_recv"] >= end).sum()),
        "valid_bbo_rows": len(valid),
        "symbol_binding_valid": symbol_binding_valid,
        "transport_available": True,
    }
    if valid.empty or not symbol_binding_valid:
        return {
            **base,
            "reference_valid": False,
            "rejection_reason": "NO_VALID_BBO" if symbol_binding_valid else "SYMBOL_BINDING_MISMATCH",
            "reference_ts_recv": "",
            "bid_px": "",
            "ask_px": "",
            "bid_sz": "",
            "ask_sz": "",
            "reference_mid": "",
            "primary_direction": "NO_TRADE",
            "reverse_direction": "NO_TRADE",
        }
    selected = valid.iloc[-1]
    bid = Decimal(str(float(selected["bid_px_00"])))
    ask = Decimal(str(float(selected["ask_px_00"])))
    mid = (bid + ask) / Decimal(2)
    pin = Decimal(str(request["pin_strike"]))
    if pin > mid:
        primary, reverse = "BUY", "SELL"
    elif pin < mid:
        primary, reverse = "SELL", "BUY"
    else:
        primary = reverse = "NO_TRADE"
    return {
        **base,
        "reference_valid": True,
        "rejection_reason": "" if primary != "NO_TRADE" else "PIN_EQUALS_REFERENCE",
        "reference_ts_recv": selected["ts_recv"].isoformat().replace("+00:00", "Z"),
        "bid_px": format(bid, "f"),
        "ask_px": format(ask, "f"),
        "bid_sz": int(selected["bid_sz_00"]),
        "ask_sz": int(selected["ask_sz_00"]),
        "reference_mid": format(mid, "f"),
        "primary_direction": primary,
        "reverse_direction": reverse,
    }


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise AnalysisError("campaign root escaped workspace") from exc
    requests_path = root / REQUESTS_FILE
    conditions_path = root / CONDITIONS_FILE
    summary_path = root / QUOTE_SUMMARY_FILE
    payload_root = root / PAYLOAD_DIR
    manifest_path = payload_root / MANIFEST_FILE
    failure_path = payload_root / FAILURE_RECEIPT
    if not all(path.is_file() for path in (requests_path, conditions_path, summary_path, manifest_path, failure_path)):
        raise AnalysisError("futures acquisition artifacts are incomplete")
    requests = load_jsonl(requests_path)
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    failure = json.loads(failure_path.read_text(encoding="ascii"))
    summary = json.loads(summary_path.read_text(encoding="ascii"))
    if (
        len(requests) != EXPECTED_EVENTS
        or manifest.get("status") != "FAILED_INCOMPLETE_NO_RETRY"
        or manifest.get("attempted_calls") != EXPECTED_EVENTS
        or manifest.get("completed_calls") != 508
        or manifest.get("failed_calls") != 1
        or manifest.get("automatic_retry_calls") != 0
        or failure.get("manifest_sha256") != sha256_file(manifest_path)
        or summary.get("within_standing_authority") is not True
    ):
        raise AnalysisError("one-shot acquisition receipt does not match the frozen partial state")
    request_by_id = {row["request_id"]: row for row in requests}
    payloads = manifest.get("payloads", {})
    failures = {row["request_id"]: row for row in manifest.get("failures", [])}
    if (
        len(payloads) != 508
        or len(failures) != 1
        or set(payloads) | set(failures) != set(request_by_id)
        or set(payloads) & set(failures)
    ):
        raise AnalysisError("payload/failure identity partition is invalid")

    import databento as db

    results: list[dict[str, Any]] = []
    payload_hashes: list[str] = []
    for request in requests:
        request_id = request["request_id"]
        if request_id in failures:
            results.append(
                {
                    "event_id": request["event_id"],
                    "request_id": request_id,
                    "underlying": request["underlying"],
                    "expiration_utc": request["expiration_utc"],
                    "decision_utc": request["decision_utc"],
                    "pin_strike": request["pin_strike"],
                    "payload_rows": 0,
                    "receive_window_rows": 0,
                    "post_decision_receive_rows": 0,
                    "valid_bbo_rows": 0,
                    "symbol_binding_valid": True,
                    "transport_available": False,
                    "reference_valid": False,
                    "rejection_reason": "TRANSPORT_504_NO_RETRY",
                    "reference_ts_recv": "",
                    "bid_px": "",
                    "ask_px": "",
                    "bid_sz": "",
                    "ask_sz": "",
                    "reference_mid": "",
                    "primary_direction": "NO_TRADE",
                    "reverse_direction": "NO_TRADE",
                }
            )
            continue
        payload = payloads[request_id]
        raw_path = (workspace / payload["path"]).resolve()
        try:
            raw_path.relative_to(workspace)
        except ValueError as exc:
            raise AnalysisError("payload path escaped workspace") from exc
        if not raw_path.is_file() or sha256_file(raw_path) != payload.get("raw_sha256"):
            raise AnalysisError(f"missing or drifted payload: {request_id}")
        if payload.get("request", {}).get("underlying") != request["underlying"]:
            raise AnalysisError(f"request binding mismatch: {request_id}")
        payload_hashes.append(payload["raw_sha256"])
        frame = db.DBNStore.from_file(raw_path).to_df()
        results.append(select_reference(frame, request))

    results.sort(key=lambda row: (row["decision_utc"], row["event_id"]))
    result_columns = [
        "event_id", "request_id", "underlying", "expiration_utc", "decision_utc",
        "pin_strike", "transport_available", "payload_rows", "receive_window_rows",
        "post_decision_receive_rows", "valid_bbo_rows", "symbol_binding_valid",
        "reference_valid", "rejection_reason", "reference_ts_recv", "bid_px",
        "ask_px", "bid_sz", "ask_sz", "reference_mid", "primary_direction",
        "reverse_direction",
    ]
    results_path = root / RESULTS_FILE
    write_csv(results_path, results, result_columns)
    directions = [
        row for row in results if row["reference_valid"] and row["primary_direction"] != "NO_TRADE"
    ]
    directions_path = root / DIRECTIONS_FILE
    write_csv(
        directions_path,
        directions,
        [
            "event_id", "underlying", "expiration_utc", "decision_utc", "pin_strike",
            "reference_ts_recv", "reference_mid", "primary_direction", "reverse_direction",
        ],
    )
    valid = sum(bool(row["reference_valid"]) for row in results)
    directional = len(directions)
    coverage = valid / EXPECTED_EVENTS
    gates = {
        "all_attempts_partitioned_without_retry": True,
        "all_available_payloads_hash_bound": len(payload_hashes) == 508,
        "all_selected_symbol_bindings_valid": all(
            row["symbol_binding_valid"] for row in results if row["transport_available"]
        ),
        "reference_coverage_at_least_95_percent": coverage >= MIN_COVERAGE,
        "target_and_outcome_fields_absent": True,
    }
    verdict = "FUTURES_REFERENCE_PASS" if all(gates.values()) else "KILL_FUTURES_REFERENCE"
    analysis = {
        "schema_version": "cme6e_option_pin_futures_analysis.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "counts": {
            "frozen_events": EXPECTED_EVENTS,
            "transport_available_events": 508,
            "transport_failed_no_retry_events": 1,
            "valid_reference_events": valid,
            "directional_events": directional,
            "reference_coverage": coverage,
            "calendar_months_with_direction": len(
                {row["decision_utc"][:7] for row in directions}
            ),
            "post_decision_payload_rows_excluded": sum(
                int(row["post_decision_receive_rows"]) for row in results
            ),
        },
        "gates": gates,
        "bindings": {
            "requests_sha256": sha256_file(requests_path),
            "conditions_sha256": sha256_file(conditions_path),
            "quote_summary_sha256": sha256_file(summary_path),
            "manifest_sha256": sha256_file(manifest_path),
            "failure_receipt_sha256": sha256_file(failure_path),
            "payload_sha256": sorted(payload_hashes),
            "results_sha256": sha256_file(results_path),
            "directions_sha256": sha256_file(directions_path),
        },
        "futures_reference_fields_used": [
            "ts_recv", "symbol", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"
        ],
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "eurusd_target_authorized": verdict == "FUTURES_REFERENCE_PASS",
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    analysis_path = root / ANALYSIS_FILE
    write_json(analysis_path, analysis)
    receipt = {
        "schema_version": "cme6e_option_pin_futures_analysis_receipt.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "valid_reference_events": valid,
        "directional_events": directional,
        "reference_coverage": coverage,
        "analysis_path": str(analysis_path.relative_to(workspace)).replace("\\", "/"),
        "analysis_sha256": sha256_file(analysis_path),
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "eurusd_target_authorized": verdict == "FUTURES_REFERENCE_PASS",
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    receipt_path = root / RECEIPT_FILE
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
            f"CME6EOPTPIN_{receipt['verdict']} "
            f"valid={receipt['valid_reference_events']}/{EXPECTED_EVENTS} "
            f"directional={receipt['directional_events']}"
        )
        print(f"RECEIPT {path}")
        return 0
    except AnalysisError as exc:
        print(f"CME6EOPTPIN_FUTURES_ANALYSIS_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
