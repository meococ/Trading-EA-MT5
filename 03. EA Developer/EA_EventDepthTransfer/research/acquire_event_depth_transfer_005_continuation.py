#!/usr/bin/env python3
"""Acquire only the 63 never-attempted windows after the DESIGN host interruption."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
from typing import Any


HYPOTHESIS_ID = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005"
ACQUISITION_ID = "EVENTDEPTHTRANSFER005-MBP10-CONTINUATION-001"
BASE_REL = "03. EA Developer/EA_EventDepthTransfer/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_CONTINUATION_PREREG.md"
TOOL_REL = BASE_REL + "acquire_event_depth_transfer_005_continuation.py"
TEST_REL = BASE_REL + "tests/test_acquire_event_depth_transfer_005_continuation.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
PARENT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004/"
    "EVENTDEPTHTRANSFER004-MBP10-DESIGN-001"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}"
)
PARENT_ENGINE_SHA256 = "71325CAC442DED57922EA336E4C92FB9EBDC1B8E993DCCB670431E692FC50D94"
PARENT_MANIFEST_SHA256 = "FD487BAB551F5C9C14002261DDA8B6C3BD7911F608E26C09A0A4DC83D93709FC"
PARENT_LIVE_PLAN_SHA256 = "996847D4CDD1F27BD104C4F3DA64ED4044656FC7002A1195865082542F9D1223"
EXPECTED_PARENT_COMPLETE = 256
EXPECTED_AMBIGUOUS = {
    "EVT0258", "EVT0260", "EVT0261", "EVT0262", "EVT0263", "EVT0264",
    "EVT0265", "EVT0266",
}
EXPECTED_CHILD = 63
EXPECTED_UNAVAILABLE = {"EVT0206", "EVT0228"}
MAX_EVENT_USD = 0.03
MAX_AGGREGATE_USD = 0.50
MIN_SEMANTIC_SHARE = 0.95
MIN_NONFLAT = 209
MIN_CLASS_SHARE = 0.10
MIN_DIRECTION_SHARE = 0.20
MAX_CLASS_SHARE = 0.80


class ContinuationError(RuntimeError):
    pass


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
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_workspace_path(workspace: Path, path: Path, label: str) -> Path:
    root = workspace.resolve(); resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContinuationError(f"{label} escapes workspace") from exc
    if root.drive.upper() != "D:" or resolved.drive.upper() != "D:":
        raise ContinuationError(f"{label} must stay on D:")
    return resolved


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    if temp.exists():
        raise ContinuationError(f"atomic temp collision: {temp}")
    with temp.open("xb") as handle:
        handle.write(canonical_json(payload) + b"\n")
        handle.flush(); os.fsync(handle.fileno())
    os.replace(temp, path)


def _load_parent() -> Any:
    path = Path(__file__).resolve().with_name("acquire_event_depth_transfer_004_design.py")
    spec = importlib.util.spec_from_file_location("event_depth_transfer_004_engine", path)
    if not spec or not spec.loader:
        raise ContinuationError("cannot load parent engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if sha256_file(path) != PARENT_ENGINE_SHA256:
        raise ContinuationError("parent acquisition engine drifted")
    return module


# The lane is revoked. Do not import or execute the paid parent engine at module
# import time; keeping the loader below supports read-only forensic helpers only.
PARENT = None


def load_parent_snapshot(workspace: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]],
                                                   list[dict[str, Any]], list[dict[str, Any]]]:
    root = require_workspace_path(workspace, workspace / PARENT_ROOT_REL, "parent root")
    manifest_path = root / "download_manifest.json"
    plan_path = root / "live_acquisition_plan.json"
    if sha256_file(manifest_path) != PARENT_MANIFEST_SHA256:
        raise ContinuationError("parent manifest drifted")
    if sha256_file(plan_path) != PARENT_LIVE_PLAN_SHA256:
        raise ContinuationError("parent live plan drifted")
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    plan = json.loads(plan_path.read_text(encoding="ascii"))
    complete = [item for item in manifest["entries"] if item["status"] == "COMPLETE"]
    ambiguous = [item for item in manifest["entries"] if item["status"] == "IN_FLIGHT"]
    unattempted = [item for item in manifest["entries"] if item["status"] == "UNATTEMPTED"]
    unavailable = plan["unavailable"]
    if (
        len(complete) != EXPECTED_PARENT_COMPLETE or len(unattempted) != EXPECTED_CHILD
        or {item["event_clock_id"] for item in ambiguous} != EXPECTED_AMBIGUOUS
        or {item["event_clock_id"] for item in unavailable} != EXPECTED_UNAVAILABLE
        or unattempted[0]["event_clock_id"] != "EVT0267"
        or unattempted[-1]["event_clock_id"] != "EVT0329"
    ):
        raise ContinuationError("parent continuation boundary mismatch")
    return complete, ambiguous, unattempted, unavailable


def validate_registry(workspace: Path) -> dict[str, str]:
    paths = {"plan_sha256": workspace / PLAN_REL, "tool_sha256": workspace / TOOL_REL,
             "test_sha256": workspace / TEST_REL}
    hashes = {key: sha256_file(require_workspace_path(workspace, path, key))
              for key, path in paths.items()}
    registry = require_workspace_path(workspace, workspace / REGISTRY_REL, "registry")
    matches = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append(row)
    if not matches:
        raise ContinuationError("hypothesis absent from registry")
    row = matches[-1]; validation = row.get("validation", {})
    if (
        row.get("state") != "probe" or row.get("prereg_sha256") != hashes["plan_sha256"]
        or validation.get("paid_acquisition_authorized") is not True
        or validation.get("source_download_authorized") is not True
        or validation.get("reviewed_acquisition_tool_sha256") != hashes["tool_sha256"]
        or validation.get("reviewed_acquisition_test_sha256") != hashes["test_sha256"]
        or validation.get("parent_manifest_sha256") != PARENT_MANIFEST_SHA256
        or validation.get("parent_live_plan_sha256") != PARENT_LIVE_PLAN_SHA256
        or validation.get("paid_timeseries_call_limit") != EXPECTED_CHILD
        or validation.get("automatic_retry_authorized") is not False
    ):
        raise ContinuationError("registry continuation authority mismatch")
    for key in ("outcome_prices_authorized", "economics_authorized", "mql5_authorized",
                "mt5_authorized", "model0_authorized", "validation_authorized",
                "holdout_authorized", "paper_trading_authorized", "live_trading_authorized",
                "market_edge_claim_authorized"):
        if validation.get(key) is not False:
            raise ContinuationError(f"forbidden authority open: {key}")
    return hashes


def summarize_combined(parent_complete: list[dict[str, Any]],
                       child: list[dict[str, Any]], ambiguous: list[dict[str, Any]],
                       unavailable: list[dict[str, Any]]) -> dict[str, Any]:
    child_complete = [item for item in child if item["status"] == "COMPLETE"]
    all_complete = parent_complete + child_complete
    semantic = [item for item in all_complete if item["semantic_gate_pass"]]
    classes = Counter(item["effective_classification"] for item in semantic)
    directions = Counter(item["effective_direction"] for item in semantic if item["effective_direction"])
    semantic_count = len(semantic); completed_count = len(all_complete)
    nonflat = classes["CONTINUATION"] + classes["REVERSAL"]
    continuation_share = classes["CONTINUATION"] / semantic_count if semantic_count else 0.0
    reversal_share = classes["REVERSAL"] / semantic_count if semantic_count else 0.0
    long_share = directions[1] / semantic_count if semantic_count else 0.0
    short_share = directions[-1] / semantic_count if semantic_count else 0.0
    gates = {
        "all_63_child_requests_complete": len(child_complete) == EXPECTED_CHILD,
        "zero_child_failures": len(child_complete) == len(child),
        "all_329_clocks_accounted": completed_count + len(ambiguous) + len(unavailable) == 329,
        "exact_8_ambiguous": len(ambiguous) == 8,
        "exact_2_unavailable": len(unavailable) == 2,
        "semantic_pass_share_at_least_95pct": semantic_count / completed_count >= MIN_SEMANTIC_SHARE,
        "nonflat_count_at_least_209": nonflat >= MIN_NONFLAT,
        "continuation_share_at_least_10pct": continuation_share >= MIN_CLASS_SHARE,
        "reversal_share_at_least_10pct": reversal_share >= MIN_CLASS_SHARE,
        "long_share_at_least_20pct": long_share >= MIN_DIRECTION_SHARE,
        "short_share_at_least_20pct": short_share >= MIN_DIRECTION_SHARE,
        "max_class_share_at_most_80pct": max(continuation_share, reversal_share) <= MAX_CLASS_SHARE,
    }
    return {
        "parent_complete_count": len(parent_complete), "child_complete_count": len(child_complete),
        "ambiguous_flat_count": len(ambiguous), "unavailable_flat_count": len(unavailable),
        "total_accounted": completed_count + len(ambiguous) + len(unavailable),
        "semantic_pass_count": semantic_count, "semantic_pass_share": semantic_count / completed_count,
        "effective_classification_counts": dict(sorted(classes.items())),
        "effective_direction_counts": {str(k): v for k, v in sorted(directions.items())},
        "nonflat_count": nonflat, "nonflat_per_week": nonflat / 104.428571,
        "continuation_share": continuation_share, "reversal_share": reversal_share,
        "long_share": long_share, "short_share": short_share,
        "gates": gates, "gate_pass": all(gates.values()),
        "verdict": "PASS_DESIGN_SOURCE_CENSUS" if all(gates.values()) else "PARK_DESIGN_SOURCE_CENSUS",
    }


def execute(workspace: Path, workers: int) -> Path:
    raise ContinuationError(
        "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005 is revoked: paid acquisition "
        "was not Owner-authorized; completed artifacts are quarantined and retry is forbidden"
    )
    if not 1 <= workers <= 8:
        raise ContinuationError("workers must be 1..8")
    workspace = workspace.resolve()
    runtime = require_workspace_path(workspace, workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise ContinuationError("wrong Python runtime")
    if (importlib.metadata.version("databento") != PARENT.SDK_VERSION
            or importlib.metadata.version("databento-dbn") != PARENT.DBN_PACKAGE_VERSION):
        raise ContinuationError("Databento runtime mismatch")
    bindings = validate_registry(workspace)
    parent_complete, ambiguous, unattempted, unavailable = load_parent_snapshot(workspace)
    key = PARENT.load_api_key()
    live = PARENT.live_quote_all(key, unattempted, workers)
    aggregate = sum(item["live_estimated_usd"] for item in live)
    if max(item["live_estimated_usd"] for item in live) > MAX_EVENT_USD or aggregate > MAX_AGGREGATE_USD:
        raise ContinuationError("continuation live quote outside contract")
    root = require_workspace_path(workspace, workspace / OUTPUT_REL, "output root")
    if root.exists():
        raise ContinuationError("exclusive continuation root exists; retry forbidden")
    root.mkdir(parents=True, exist_ok=False)
    raw_dir = root / "raw"; analysis_dir = root / "analysis"
    raw_dir.mkdir(); analysis_dir.mkdir()
    plan_path = root / "live_continuation_plan.json"
    manifest_path = root / "download_manifest.json"
    ledger_path = root / "combined_source_classification_ledger.jsonl"
    receipt_path = root / "source_continuation_receipt.json"
    live_plan = {
        "schema_version": "event_depth_transfer_005_live_plan.v1",
        "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID, "workers": workers,
        "aggregate_live_estimated_usd": aggregate,
        "aggregate_live_billable_bytes": sum(item["live_billable_bytes"] for item in live),
        "max_event_live_estimated_usd": max(item["live_estimated_usd"] for item in live),
        "expected_paid_calls": EXPECTED_CHILD, "automatic_retry_authorized": False,
        "windows": live, "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        "ambiguous_event_ids": sorted(EXPECTED_AMBIGUOUS),
        "unavailable_event_ids": sorted(EXPECTED_UNAVAILABLE), "bindings": bindings,
        "outcome_fields_authorized": [],
    }
    write_json_atomic(plan_path, live_plan)
    entries = [{"event_clock_id": item["event_clock_id"],
                "event_time_utc": item["event_time_utc"], "start": item["start"],
                "end": item["end"], "status": "UNATTEMPTED",
                "live_estimated_usd": item["live_estimated_usd"],
                "live_billable_bytes": item["live_billable_bytes"]} for item in live]
    by_id = {item["event_clock_id"]: item for item in entries}
    manifest = {"schema_version": "event_depth_transfer_005_manifest.v1",
                "status": "READY", "updated_at_utc": utc_now(), "entries": entries,
                "paid_timeseries_calls_attempted": 0, "paid_timeseries_calls_complete": 0,
                "failed_calls": 0, "automatic_retry_authorized": False}
    write_json_atomic(manifest_path, manifest)
    lock = threading.Lock(); local = threading.local()

    def persist() -> None:
        manifest["updated_at_utc"] = utc_now(); write_json_atomic(manifest_path, manifest)

    def one(item: dict[str, Any]) -> dict[str, Any]:
        event_id = item["event_clock_id"]
        with lock:
            by_id[event_id]["status"] = "IN_FLIGHT"; manifest["status"] = "IN_FLIGHT"
            manifest["paid_timeseries_calls_attempted"] += 1; persist()
        if not hasattr(local, "client"):
            local.client = PARENT.make_client(key)
        final = raw_dir / PARENT.raw_filename(item); partial = final.with_suffix(final.suffix + ".partial")
        try:
            local.client.timeseries.get_range(
                **PARENT.request_args(item), stype_out=PARENT.STYPE_OUT, path=partial,
            )
            raw, analysis = PARENT.decode_raw(partial, item); os.replace(partial, final)
            effective_class = analysis["classification"] if analysis["semantic_gate_pass"] else "SOURCE_INVALID_FLAT"
            effective_direction = analysis["direction"] if analysis["semantic_gate_pass"] else 0
            payload = {"schema_version": "event_depth_transfer_005_event_source.v1",
                       "hypothesis_id": HYPOTHESIS_ID, "event_clock_id": event_id,
                       "event_time_utc": item["event_time_utc"], "start": item["start"],
                       "end": item["end"], "raw_path": str(final.relative_to(workspace)).replace("\\", "/"),
                       "raw": raw, "analysis": analysis,
                       "effective_classification": effective_class,
                       "effective_direction": effective_direction,
                       "outcome_prices_read": False, "returns_computed": 0}
            analysis_path = analysis_dir / f"{event_id}_source_analysis.json"
            write_json_atomic(analysis_path, payload)
            result = {**by_id[event_id], "status": "COMPLETE",
                      "raw_path": payload["raw_path"], "raw_sha256": raw["raw_sha256"],
                      "raw_bytes": raw["raw_bytes"],
                      "analysis_path": str(analysis_path.relative_to(workspace)).replace("\\", "/"),
                      "analysis_sha256": sha256_file(analysis_path),
                      "semantic_gate_pass": analysis["semantic_gate_pass"],
                      "effective_classification": effective_class,
                      "effective_direction": effective_direction,
                      "transfer_score": analysis["transfer_score"]}
        except Exception as exc:
            result = {**by_id[event_id], "status": "FAILED_NO_RETRY",
                      "error_type": type(exc).__name__, "semantic_gate_pass": False,
                      "effective_classification": "SOURCE_FAILED_FLAT", "effective_direction": 0}
        with lock:
            by_id[event_id].update(result)
            if result["status"] == "COMPLETE": manifest["paid_timeseries_calls_complete"] += 1
            else: manifest["failed_calls"] += 1
            persist()
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = [future.result() for future in as_completed([pool.submit(one, item) for item in live])]
    results.sort(key=lambda item: item["event_time_utc"])
    summary = summarize_combined(parent_complete, results, ambiguous, unavailable)
    manifest["status"] = "COMPLETE" if manifest["failed_calls"] == 0 else "PARTIAL_NO_RETRY"; persist()
    ledger = []
    ledger.extend(parent_complete); ledger.extend(results)
    ledger.extend({"event_clock_id": item["event_clock_id"], "event_time_utc": item["event_time_utc"],
                   "status": "SOURCE_AMBIGUOUS_FLAT", "semantic_gate_pass": False,
                   "effective_classification": "SOURCE_AMBIGUOUS_FLAT", "effective_direction": 0}
                  for item in ambiguous)
    ledger.extend({"event_clock_id": item["event_clock_id"], "event_time_utc": item["event_time_utc"],
                   "status": "SOURCE_UNAVAILABLE_FLAT", "semantic_gate_pass": False,
                   "effective_classification": "SOURCE_UNAVAILABLE_FLAT", "effective_direction": 0}
                  for item in unavailable)
    ledger.sort(key=lambda item: item["event_time_utc"])
    with ledger_path.open("xb") as handle:
        for item in ledger:
            handle.write(canonical_json({key: item.get(key) for key in (
                "event_clock_id", "event_time_utc", "start", "end", "status",
                "semantic_gate_pass", "effective_classification", "effective_direction",
                "transfer_score", "raw_sha256", "analysis_sha256")}) + b"\n")
        handle.flush(); os.fsync(handle.fileno())
    receipt = {"schema_version": "event_depth_transfer_005_source_receipt.v1",
               "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
               "acquisition_id": ACQUISITION_ID, "summary": summary,
               "live_estimated_usd": aggregate,
               "live_billable_bytes": live_plan["aggregate_live_billable_bytes"],
               "api_method_counters": {"metadata.get_cost": EXPECTED_CHILD,
                                       "metadata.get_billable_size": EXPECTED_CHILD,
                                       "timeseries.get_range": manifest["paid_timeseries_calls_attempted"],
                                       "batch": 0},
               "bindings": {**bindings, "parent_engine_sha256": PARENT_ENGINE_SHA256,
                            "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
                            "parent_live_plan_sha256": PARENT_LIVE_PLAN_SHA256,
                            "live_plan_sha256": sha256_file(plan_path),
                            "manifest_sha256": sha256_file(manifest_path),
                            "ledger_sha256": sha256_file(ledger_path)},
               "ledger_path": str(ledger_path.relative_to(workspace)).replace("\\", "/"),
               "outcome_prices_read": False, "returns_computed": 0, "trades_simulated": 0,
               "economics_authorized": False, "mql5_authorized": False,
               "mt5_authorized": False, "validation_authorized": False,
               "holdout_authorized": False, "paper_trading_authorized": False,
               "live_trading_authorized": False, "market_edge_claim_authorized": False}
    write_json_atomic(receipt_path, receipt); return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    try:
        path = execute(args.workspace.resolve(), args.workers)
        receipt = json.loads(path.read_text(encoding="ascii")); summary = receipt["summary"]
        print("EVENT_DEPTH_TRANSFER_005_CONTINUATION_OK "
              f"cost={receipt['live_estimated_usd']:.12f} child={summary['child_complete_count']} "
              f"semantic={summary['semantic_pass_count']} verdict={summary['verdict']}")
        print(f"RECEIPT {path}"); return 0
    except ContinuationError as exc:
        print(f"EVENT_DEPTH_TRANSFER_005_CONTINUATION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
