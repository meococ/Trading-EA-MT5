#!/usr/bin/env python3
"""Acquire and classify the frozen 327-window MBP-10 DESIGN source census."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import threading
from typing import Any


HYPOTHESIS_ID = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004"
ACQUISITION_ID = "EVENTDEPTHTRANSFER004-MBP10-DESIGN-001"
BASE_REL = "03. EA Developer/EA_EventDepthTransfer/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_DESIGN_ACQUISITION_PREREG.md"
TOOL_REL = BASE_REL + "acquire_event_depth_transfer_004_design.py"
TEST_REL = BASE_REL + "tests/test_acquire_event_depth_transfer_004_design.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
QUOTE_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-003/"
    "EVENTDEPTHTRANSFER003-MBP10-DESIGN-FREE-QUOTE-001/metadata_quote_receipt.json"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}"
)
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
COST_MODE = "historical-streaming"
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DBN_VERSION = 3
EXPECTED_CLOCKS = 329
EXPECTED_ACQUIRED = 327
EXPECTED_UNAVAILABLE = {"EVT0206", "EVT0228"}
MAX_EVENT_USD = 0.03
MAX_AGGREGATE_USD = 2.20
MIN_SEMANTIC_SHARE = 0.95
MIN_NONFLAT = 209
MIN_CONTINUATION_SHARE = 0.10
MIN_REVERSAL_SHARE = 0.10
MIN_DIRECTION_SHARE = 0.20
MAX_CLASS_SHARE = 0.80
ENGINE_SHA256 = "D98340522620EB783762B4E8BDB8CAE99B71BEFE4F1D8D9A03EEE98E7F85B8F3"
QUOTE_SHA256 = "F34A30F47702371717DD7384A638E51AC890A1BDDFC0750EF3F990321CAA46ED"
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")


class AcquisitionError(RuntimeError):
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
    root = workspace.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AcquisitionError(f"{label} escapes workspace") from exc
    if root.drive.upper() != "D:" or resolved.drive.upper() != "D:":
        raise AcquisitionError(f"{label} must stay on D:")
    return resolved


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    if temp.exists():
        raise AcquisitionError(f"atomic temp collision: {temp}")
    with temp.open("xb") as handle:
        handle.write(canonical_json(payload) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _load_engine() -> Any:
    path = Path(__file__).resolve().with_name("acquire_event_depth_transfer_001_pilot.py")
    spec = importlib.util.spec_from_file_location("event_depth_transfer_engine_v1_design", path)
    if not spec or not spec.loader:
        raise AcquisitionError("cannot load acquisition engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if sha256_file(path) != ENGINE_SHA256:
        raise AcquisitionError("source-semantics engine drifted")
    return module


ENGINE = _load_engine()


def load_quote(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if sha256_file(path) != QUOTE_SHA256:
        raise AcquisitionError("DESIGN quote receipt drifted")
    receipt = json.loads(path.read_text(encoding="ascii"))
    if (
        receipt.get("hypothesis_id") != "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-003"
        or receipt.get("dataset") != DATASET or receipt.get("schema") != SCHEMA
        or receipt.get("paid_timeseries_calls") != 0
        or receipt.get("source_payload_read") is not False
        or receipt.get("outcome_prices_read") is not False
    ):
        raise AcquisitionError("DESIGN quote contract mismatch")
    quotes = receipt.get("quotes", [])
    positive = [item for item in quotes if int(item["billable_bytes"]) > 0]
    unavailable = [item for item in quotes if int(item["billable_bytes"]) == 0]
    if (
        len(quotes) != EXPECTED_CLOCKS or len(positive) != EXPECTED_ACQUIRED
        or {item["event_clock_id"] for item in unavailable} != EXPECTED_UNAVAILABLE
        or len({item["event_clock_id"] for item in quotes}) != EXPECTED_CLOCKS
    ):
        raise AcquisitionError("quoted DESIGN population mismatch")
    return positive, unavailable


def _read_user_environment(name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except (FileNotFoundError, OSError):
        return None


def load_api_key() -> str:
    key = os.environ.get("DATABENTO_API_KEY") or _read_user_environment("DATABENTO_API_KEY")
    if not key:
        raise AcquisitionError("DATABENTO_API_KEY is absent")
    key = key.strip()
    if not _KEY_RE.fullmatch(key):
        raise AcquisitionError("DATABENTO_API_KEY has an unexpected format")
    return key


def make_client(key: str) -> Any:
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError("Databento SDK is unavailable") from exc
    if str(getattr(db, "__version__", "")) != SDK_VERSION:
        raise AcquisitionError("Databento SDK version mismatch")
    return db.Historical(key)


def request_args(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": DATASET, "schema": SCHEMA, "symbols": [SYMBOL],
        "stype_in": STYPE_IN, "start": item["start"], "end": item["end"],
    }


def validate_registry(workspace: Path) -> dict[str, str]:
    files = {
        "plan_sha256": workspace / PLAN_REL,
        "tool_sha256": workspace / TOOL_REL,
        "test_sha256": workspace / TEST_REL,
        "quote_sha256": workspace / QUOTE_REL,
    }
    hashes = {key: sha256_file(require_workspace_path(workspace, path, key))
              for key, path in files.items()}
    if hashes["quote_sha256"] != QUOTE_SHA256:
        raise AcquisitionError("quote binding mismatch")
    registry = require_workspace_path(workspace, workspace / REGISTRY_REL, "registry")
    matches = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append(row)
    if not matches:
        raise AcquisitionError("hypothesis absent from registry")
    row = matches[-1]
    validation = row.get("validation", {})
    if (
        row.get("state") != "probe" or row.get("prereg_sha256") != hashes["plan_sha256"]
        or validation.get("paid_acquisition_authorized") is not True
        or validation.get("source_download_authorized") is not True
        or validation.get("reviewed_acquisition_tool_sha256") != hashes["tool_sha256"]
        or validation.get("reviewed_acquisition_test_sha256") != hashes["test_sha256"]
        or validation.get("quote_receipt_sha256") != hashes["quote_sha256"]
        or validation.get("reviewed_engine_sha256") != ENGINE_SHA256
        or validation.get("paid_timeseries_call_limit") != EXPECTED_ACQUIRED
        or validation.get("automatic_retry_authorized") is not False
    ):
        raise AcquisitionError("registry acquisition authority mismatch")
    for key in (
        "outcome_prices_authorized", "economics_authorized", "mql5_authorized",
        "mt5_authorized", "model0_authorized", "validation_authorized",
        "holdout_authorized", "paper_trading_authorized", "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if validation.get(key) is not False:
            raise AcquisitionError(f"forbidden authority open: {key}")
    return hashes


def live_quote_all(key: str, windows: list[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    local = threading.local()

    def one(item: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = make_client(key)
        args = request_args(item)
        cost = float(local.client.metadata.get_cost(mode=COST_MODE, **args))
        size = int(local.client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0 or cost > MAX_EVENT_USD or size <= 0:
            raise AcquisitionError(f"live quote outside contract: {item['event_clock_id']}")
        return {**item, "live_estimated_usd": cost, "live_billable_bytes": size}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        quoted = list(pool.map(one, windows))
    total = sum(item["live_estimated_usd"] for item in quoted)
    if total > MAX_AGGREGATE_USD:
        raise AcquisitionError("aggregate live quote exceeds USD 2.20")
    return sorted(quoted, key=lambda item: item["event_time_utc"])


def raw_filename(item: dict[str, Any]) -> str:
    start = item["start"].replace("-", "").replace(":", "").replace(".000Z", "Z")
    end = item["end"].replace("-", "").replace(":", "").replace(".000Z", "Z")
    return f"{item['event_clock_id']}_{start}_{end}_mbp-10.dbn.zst"


def decode_raw(path: Path, item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file() or path.stat().st_size <= len(_ZSTD_MAGIC):
        raise AcquisitionError("DBN payload missing or empty")
    with path.open("rb") as handle:
        if handle.read(len(_ZSTD_MAGIC)) != _ZSTD_MAGIC:
            raise AcquisitionError("DBN Zstandard signature mismatch")
    try:
        import databento as db
        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        if int(metadata.version) != DBN_VERSION or metadata.dataset != DATASET or schema != SCHEMA:
            raise AcquisitionError("DBN metadata mismatch")
        start_ns = int(datetime.fromisoformat(item["start"].replace("Z", "+00:00")).timestamp() * 1e9)
        end_ns = int(datetime.fromisoformat(item["end"].replace("Z", "+00:00")).timestamp() * 1e9)
        analysis = ENGINE.analyze_records(store, start_ns, end_ns)
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(f"DBN decode failed: {exc}") from exc
    raw = {"raw_sha256": sha256_file(path), "raw_bytes": path.stat().st_size,
           "dataset": metadata.dataset, "schema": schema, "dbn_version": int(metadata.version),
           "metadata_start": int(metadata.start), "metadata_end": int(metadata.end)}
    return raw, analysis


def summarize(entries: list[dict[str, Any]], unavailable: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [item for item in entries if item["status"] == "COMPLETE"]
    failures = [item for item in entries if item["status"] != "COMPLETE"]
    semantic = [item for item in complete if item["semantic_gate_pass"]]
    effective = Counter(item["effective_classification"] for item in complete)
    directions = Counter(item["effective_direction"] for item in complete if item["effective_direction"])
    semantic_count = len(semantic)
    nonflat = effective["CONTINUATION"] + effective["REVERSAL"]
    continuation_share = effective["CONTINUATION"] / semantic_count if semantic_count else 0.0
    reversal_share = effective["REVERSAL"] / semantic_count if semantic_count else 0.0
    long_share = directions[1] / semantic_count if semantic_count else 0.0
    short_share = directions[-1] / semantic_count if semantic_count else 0.0
    max_class_share = max(continuation_share, reversal_share)
    gates = {
        "all_327_requests_complete": len(complete) == EXPECTED_ACQUIRED and not failures,
        "all_329_clocks_accounted": len(entries) + len(unavailable) == EXPECTED_CLOCKS,
        "semantic_pass_share_at_least_95pct": semantic_count / EXPECTED_ACQUIRED >= MIN_SEMANTIC_SHARE,
        "nonflat_count_at_least_209": nonflat >= MIN_NONFLAT,
        "continuation_share_at_least_10pct": continuation_share >= MIN_CONTINUATION_SHARE,
        "reversal_share_at_least_10pct": reversal_share >= MIN_REVERSAL_SHARE,
        "long_share_at_least_20pct": long_share >= MIN_DIRECTION_SHARE,
        "short_share_at_least_20pct": short_share >= MIN_DIRECTION_SHARE,
        "max_class_share_at_most_80pct": max_class_share <= MAX_CLASS_SHARE,
    }
    return {
        "acquired_count": len(entries), "complete_count": len(complete),
        "failed_count": len(failures), "unavailable_count": len(unavailable),
        "semantic_pass_count": semantic_count,
        "semantic_pass_share": semantic_count / EXPECTED_ACQUIRED,
        "effective_classification_counts": dict(sorted(effective.items())),
        "effective_direction_counts": {str(k): v for k, v in sorted(directions.items())},
        "nonflat_count": nonflat, "nonflat_per_week": nonflat / 104.428571,
        "continuation_share": continuation_share, "reversal_share": reversal_share,
        "long_share": long_share, "short_share": short_share,
        "gates": gates, "gate_pass": all(gates.values()),
        "verdict": "PASS_DESIGN_SOURCE_CENSUS" if all(gates.values()) else "PARK_DESIGN_SOURCE_CENSUS",
    }


def execute(workspace: Path, workers: int) -> Path:
    raise AcquisitionError(
        "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004 is revoked: paid acquisition "
        "was not Owner-authorized and the revision relaxed observed HYP003 gates."
    )
    if not 1 <= workers <= 8:
        raise AcquisitionError("workers must be 1..8")
    workspace = workspace.resolve()
    runtime = require_workspace_path(workspace, workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise AcquisitionError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise AcquisitionError("Databento runtime mismatch")
    bindings = validate_registry(workspace)
    positive, unavailable = load_quote(
        require_workspace_path(workspace, workspace / QUOTE_REL, "quote receipt")
    )
    key = load_api_key()
    live = live_quote_all(key, positive, workers)
    root = require_workspace_path(workspace, workspace / OUTPUT_REL, "output root")
    if root.exists():
        raise AcquisitionError("exclusive DESIGN output root already exists; retry forbidden")
    root.mkdir(parents=True, exist_ok=False)
    raw_dir = root / "raw"
    analysis_dir = root / "analysis"
    raw_dir.mkdir(); analysis_dir.mkdir()
    plan_path = root / "live_acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    ledger_path = root / "source_classification_ledger.jsonl"
    receipt_path = root / "source_acquisition_receipt.json"
    live_plan = {
        "schema_version": "event_depth_transfer_004_live_plan.v1",
        "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID, "workers": workers,
        "expected_paid_calls": EXPECTED_ACQUIRED,
        "aggregate_live_estimated_usd": sum(item["live_estimated_usd"] for item in live),
        "aggregate_live_billable_bytes": sum(item["live_billable_bytes"] for item in live),
        "max_event_live_estimated_usd": max(item["live_estimated_usd"] for item in live),
        "max_event_usd": MAX_EVENT_USD, "max_aggregate_usd": MAX_AGGREGATE_USD,
        "automatic_retry_authorized": False, "windows": live,
        "unavailable": unavailable, "bindings": bindings,
        "outcome_fields_authorized": [],
    }
    write_json_atomic(plan_path, live_plan)
    entries = [{
        "event_clock_id": item["event_clock_id"], "event_time_utc": item["event_time_utc"],
        "start": item["start"], "end": item["end"], "status": "UNATTEMPTED",
        "live_estimated_usd": item["live_estimated_usd"],
        "live_billable_bytes": item["live_billable_bytes"],
    } for item in live]
    by_id = {item["event_clock_id"]: item for item in entries}
    manifest = {
        "schema_version": "event_depth_transfer_004_manifest.v1",
        "status": "READY", "updated_at_utc": utc_now(), "entries": entries,
        "unavailable_event_ids": sorted(EXPECTED_UNAVAILABLE),
        "paid_timeseries_calls_attempted": 0, "paid_timeseries_calls_complete": 0,
        "failed_calls": 0, "automatic_retry_authorized": False,
        "eurusd_outcome_fields_used": [],
    }
    write_json_atomic(manifest_path, manifest)
    lock = threading.Lock()
    local = threading.local()

    def persist() -> None:
        manifest["updated_at_utc"] = utc_now()
        write_json_atomic(manifest_path, manifest)

    def acquire_one(item: dict[str, Any]) -> dict[str, Any]:
        event_id = item["event_clock_id"]
        with lock:
            by_id[event_id]["status"] = "IN_FLIGHT"
            manifest["status"] = "IN_FLIGHT"
            manifest["paid_timeseries_calls_attempted"] += 1
            persist()
        if not hasattr(local, "client"):
            local.client = make_client(key)
        final = raw_dir / raw_filename(item)
        partial = final.with_suffix(final.suffix + ".partial")
        try:
            local.client.timeseries.get_range(
                **request_args(item), stype_out=STYPE_OUT, path=partial,
            )
            raw, analysis = decode_raw(partial, item)
            os.replace(partial, final)
            effective_class = analysis["classification"] if analysis["semantic_gate_pass"] else "SOURCE_INVALID_FLAT"
            effective_direction = analysis["direction"] if analysis["semantic_gate_pass"] else 0
            event_analysis = {
                "schema_version": "event_depth_transfer_004_event_source.v1",
                "hypothesis_id": HYPOTHESIS_ID, "event_clock_id": event_id,
                "event_time_utc": item["event_time_utc"], "start": item["start"], "end": item["end"],
                "raw_path": str(final.relative_to(workspace)).replace("\\", "/"),
                "raw": raw, "analysis": analysis,
                "effective_classification": effective_class,
                "effective_direction": effective_direction,
                "outcome_prices_read": False, "returns_computed": 0,
            }
            analysis_path = analysis_dir / f"{event_id}_source_analysis.json"
            write_json_atomic(analysis_path, event_analysis)
            result = {
                **by_id[event_id], "status": "COMPLETE",
                "raw_path": event_analysis["raw_path"], "raw_sha256": raw["raw_sha256"],
                "raw_bytes": raw["raw_bytes"],
                "analysis_path": str(analysis_path.relative_to(workspace)).replace("\\", "/"),
                "analysis_sha256": sha256_file(analysis_path),
                "semantic_gate_pass": analysis["semantic_gate_pass"],
                "effective_classification": effective_class,
                "effective_direction": effective_direction,
                "transfer_score": analysis["transfer_score"],
            }
        except Exception as exc:
            result = {**by_id[event_id], "status": "FAILED_NO_RETRY",
                      "error_type": type(exc).__name__, "semantic_gate_pass": False,
                      "effective_classification": "SOURCE_FAILED_FLAT", "effective_direction": 0}
        with lock:
            by_id[event_id].update(result)
            if result["status"] == "COMPLETE":
                manifest["paid_timeseries_calls_complete"] += 1
            else:
                manifest["failed_calls"] += 1
            persist()
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(acquire_one, item) for item in live]
        results = [future.result() for future in as_completed(futures)]
    results.sort(key=lambda item: item["event_time_utc"])
    summary = summarize(results, unavailable)
    manifest["status"] = "COMPLETE" if summary["failed_count"] == 0 else "PARTIAL_NO_RETRY"
    persist()
    with ledger_path.open("xb") as handle:
        for item in results:
            row = {key: item.get(key) for key in (
                "event_clock_id", "event_time_utc", "start", "end", "status",
                "semantic_gate_pass", "effective_classification", "effective_direction",
                "transfer_score", "raw_sha256", "analysis_sha256",
            )}
            handle.write(canonical_json(row) + b"\n")
        for item in unavailable:
            handle.write(canonical_json({
                "event_clock_id": item["event_clock_id"],
                "event_time_utc": item["event_time_utc"], "start": item["start"],
                "end": item["end"], "status": "SOURCE_UNAVAILABLE_FLAT",
                "semantic_gate_pass": False, "effective_classification": "SOURCE_UNAVAILABLE_FLAT",
                "effective_direction": 0, "transfer_score": None,
            }) + b"\n")
        handle.flush(); os.fsync(handle.fileno())
    receipt = {
        "schema_version": "event_depth_transfer_004_source_receipt.v1",
        "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID, "dataset": DATASET, "schema": SCHEMA,
        "symbol": SYMBOL, "split": "DESIGN", "summary": summary,
        "live_estimated_usd": live_plan["aggregate_live_estimated_usd"],
        "live_billable_bytes": live_plan["aggregate_live_billable_bytes"],
        "api_method_counters": {"metadata.get_cost": EXPECTED_ACQUIRED,
                                "metadata.get_billable_size": EXPECTED_ACQUIRED,
                                "timeseries.get_range": manifest["paid_timeseries_calls_attempted"],
                                "batch": 0},
        "bindings": {**bindings, "engine_sha256": ENGINE_SHA256,
                     "live_plan_sha256": sha256_file(plan_path),
                     "manifest_sha256": sha256_file(manifest_path),
                     "ledger_sha256": sha256_file(ledger_path)},
        "ledger_path": str(ledger_path.relative_to(workspace)).replace("\\", "/"),
        "outcome_prices_read": False, "returns_computed": 0, "trades_simulated": 0,
        "economics_authorized": False, "mql5_authorized": False,
        "mt5_authorized": False, "validation_authorized": False,
        "holdout_authorized": False, "paper_trading_authorized": False,
        "live_trading_authorized": False, "market_edge_claim_authorized": False,
    }
    write_json_atomic(receipt_path, receipt)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    try:
        path = execute(args.workspace.resolve(), args.workers)
        receipt = json.loads(path.read_text(encoding="ascii"))
        summary = receipt["summary"]
        print(
            "EVENT_DEPTH_TRANSFER_004_DESIGN_OK "
            f"cost={receipt['live_estimated_usd']:.12f} complete={summary['complete_count']} "
            f"semantic={summary['semantic_pass_count']} verdict={summary['verdict']}"
        )
        print(f"RECEIPT {path}")
        return 0
    except AcquisitionError as exc:
        print(f"EVENT_DEPTH_TRANSFER_004_DESIGN_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
