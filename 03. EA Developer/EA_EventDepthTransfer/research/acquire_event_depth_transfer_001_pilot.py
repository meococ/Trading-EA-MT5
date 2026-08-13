#!/usr/bin/env python3
"""Acquire and score the one-shot EVT0001 CME 6E MBP-10 source pilot."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-001"
ACQUISITION_ID = "EVENTDEPTHTRANSFER001-MBP10-PILOT-001"
BASE_REL = "03. EA Developer/EA_EventDepthTransfer/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_PILOT_PREREG.md"
TOOL_REL = BASE_REL + "acquire_event_depth_transfer_001_pilot.py"
TEST_REL = BASE_REL + "tests/test_acquire_event_depth_transfer_001_pilot.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
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
EVENT_ID = "EVT0001"
START = "2019-01-03T15:00:00.000Z"
END = "2019-01-03T15:02:00.000Z"
BASELINE_SECONDS = 15
DECISION_SECONDS = 60
MIN_COVERAGE = 0.99
MAX_LOCKED_CROSSED_NS = 50_000_000
OWNER_CEILING_USD = 0.01
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


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


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


def request_args() -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": START,
        "end": END,
    }


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


def validate_registry_authority(workspace: Path) -> dict[str, str]:
    plan = require_workspace_path(workspace, workspace / PLAN_REL, "plan")
    tool = require_workspace_path(workspace, workspace / TOOL_REL, "tool")
    test = require_workspace_path(workspace, workspace / TEST_REL, "test")
    registry = require_workspace_path(workspace, workspace / REGISTRY_REL, "registry")
    bindings = {
        "plan_sha256": sha256_file(plan),
        "tool_sha256": sha256_file(tool),
        "test_sha256": sha256_file(test),
    }
    matches: list[tuple[dict[str, Any], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((row, raw + b"\n"))
    if not matches:
        raise AcquisitionError("hypothesis absent from candidate registry")
    row, line = matches[-1]
    validation = row.get("validation", {})
    if (
        row.get("state") != "probe"
        or row.get("prereg_sha256") != bindings["plan_sha256"]
        or validation.get("pilot_acquisition_id") != ACQUISITION_ID
        or validation.get("paid_acquisition_authorized") is not True
        or validation.get("source_download_authorized") is not True
        or validation.get("reviewed_acquisition_tool_sha256") != bindings["tool_sha256"]
        or validation.get("reviewed_acquisition_test_sha256") != bindings["test_sha256"]
        or float(validation.get("hard_cost_ceiling_usd", -1)) != OWNER_CEILING_USD
        or int(validation.get("paid_timeseries_call_limit", -1)) != 1
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
            raise AcquisitionError(f"forbidden registry authority open: {key}")
    if ACQUISITION_ID in row.get("run_ids", []):
        raise AcquisitionError("pilot attempt already consumed")
    return {**bindings, "registry_row_sha256": sha256_bytes(line)}


def _enum_char(value: Any) -> str:
    raw = getattr(value, "value", value)
    if isinstance(raw, bytes):
        raw = raw.decode("ascii")
    if isinstance(raw, int):
        raw = chr(raw)
    return str(raw)


def depth_sides(levels: Iterable[Any]) -> tuple[float, float]:
    book = list(levels)
    if len(book) < 10:
        raise ValueError("ten levels required")
    bid = 0.0
    ask = 0.0
    for index, level in enumerate(book[:10]):
        bid_px = int(level.bid_px)
        ask_px = int(level.ask_px)
        bid_sz = int(level.bid_sz)
        ask_sz = int(level.ask_sz)
        if bid_px <= 0 or ask_px <= 0 or bid_sz <= 0 or ask_sz <= 0:
            raise ValueError("positive ten-level book required")
        if index >= 1:
            weight = 10 - index
            bid += weight * bid_sz
            ask += weight * ask_sz
    if int(book[0].bid_px) >= int(book[0].ask_px):
        raise ValueError("locked or crossed BBO")
    return bid, ask


def classify_transfer(initial_sign: int, dbid0: float, dask0: float,
                      dbid1: float, dask1: float) -> dict[str, Any]:
    if initial_sign not in (-1, 1):
        return {"transfer_score": None, "classification": "FLAT", "direction": 0}
    if min(dbid0, dask0, dbid1, dask1) <= 0:
        raise ValueError("depth inputs must be positive")
    score = initial_sign * ((dbid1 - dbid0) / dbid0 - (dask1 - dask0) / dask0)
    if score > 0:
        classification, direction = "CONTINUATION", initial_sign
    elif score < 0:
        classification, direction = "REVERSAL", -initial_sign
    else:
        classification, direction = "FLAT", 0
    return {"transfer_score": score, "classification": classification,
            "direction": direction}


def analyze_records(records: Iterable[Any], start_ns: int, end_ns: int) -> dict[str, Any]:
    baseline_ns = start_ns + BASELINE_SECONDS * 1_000_000_000
    decision_ns = start_ns + DECISION_SECONDS * 1_000_000_000
    interval_ns = decision_ns - baseline_ns
    total = 0
    containment_violations = 0
    monotonicity_violations = 0
    malformed_snapshots = 0
    locked_crossed_records = 0
    max_locked_crossed_duration_ns = 0
    current_locked_start: int | None = None
    previous_ts: int | None = None
    last_ts: int | None = None
    last_valid_at_baseline: tuple[float, float] | None = None
    states: list[tuple[int, tuple[float, float] | None]] = []
    buyer_volume = 0
    seller_volume = 0
    action_counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    instrument_ids: set[int] = set()

    for message in records:
        total += 1
        ts_recv = int(message.ts_recv)
        if not start_ns <= ts_recv < end_ns:
            containment_violations += 1
        if previous_ts is not None and ts_recv < previous_ts:
            monotonicity_violations += 1
        previous_ts = ts_recv
        last_ts = ts_recv
        instrument_ids.add(int(message.instrument_id))
        action = _enum_char(message.action)
        side = _enum_char(message.side)
        action_counts[action] += 1
        side_counts[side] += 1
        if action == "T" and start_ns <= ts_recv < baseline_ns:
            size = int(message.size)
            if side == "B":
                buyer_volume += size
            elif side == "A":
                seller_volume += size

        try:
            values = depth_sides(message.levels)
            locked = False
        except (AttributeError, TypeError, ValueError):
            values = None
            malformed_snapshots += 1
            try:
                level0 = list(message.levels)[0]
                locked = int(level0.bid_px) > 0 and int(level0.bid_px) >= int(level0.ask_px)
            except (AttributeError, IndexError, TypeError, ValueError):
                locked = False

        if locked:
            locked_crossed_records += 1
            if current_locked_start is None:
                current_locked_start = ts_recv
        elif current_locked_start is not None:
            max_locked_crossed_duration_ns = max(
                max_locked_crossed_duration_ns, ts_recv - current_locked_start,
            )
            current_locked_start = None

        if ts_recv <= baseline_ns and values is not None:
            last_valid_at_baseline = values
        if baseline_ns <= ts_recv < decision_ns:
            states.append((ts_recv, values))

    if current_locked_start is not None:
        cap = min(last_ts if last_ts is not None else current_locked_start, decision_ns)
        max_locked_crossed_duration_ns = max(
            max_locked_crossed_duration_ns, max(0, cap - current_locked_start),
        )

    weighted_bid = 0.0
    weighted_ask = 0.0
    covered_ns = 0
    state = last_valid_at_baseline
    cursor = baseline_ns
    for ts_recv, next_state in states:
        bounded = min(max(ts_recv, baseline_ns), decision_ns)
        duration = max(0, bounded - cursor)
        if state is not None:
            weighted_bid += state[0] * duration
            weighted_ask += state[1] * duration
            covered_ns += duration
        cursor = max(cursor, bounded)
        state = next_state
    if cursor < decision_ns and state is not None:
        duration = decision_ns - cursor
        weighted_bid += state[0] * duration
        weighted_ask += state[1] * duration
        covered_ns += duration

    coverage = covered_ns / interval_ns
    initial_sign = 1 if buyer_volume > seller_volume else -1 if seller_volume > buyer_volume else 0
    dbid0 = last_valid_at_baseline[0] if last_valid_at_baseline else None
    dask0 = last_valid_at_baseline[1] if last_valid_at_baseline else None
    dbid1 = weighted_bid / covered_ns if covered_ns else None
    dask1 = weighted_ask / covered_ns if covered_ns else None
    classification = {"transfer_score": None, "classification": "FLAT", "direction": 0}
    if all(value is not None for value in (dbid0, dask0, dbid1, dask1)):
        classification = classify_transfer(
            initial_sign, float(dbid0), float(dask0), float(dbid1), float(dask1),
        )
    gates = {
        "records_nonzero": total > 0,
        "half_open_containment": containment_violations == 0,
        "ts_recv_monotone": monotonicity_violations == 0,
        "single_instrument_id": len(instrument_ids) == 1,
        "baseline_present": last_valid_at_baseline is not None,
        "interval_coverage_at_least_99pct": coverage >= MIN_COVERAGE,
        "no_locked_crossed_over_50ms": max_locked_crossed_duration_ns <= MAX_LOCKED_CROSSED_NS,
        "initial_aggressor_imbalance_nonzero": initial_sign != 0,
    }
    passed = all(gates.values())
    return {
        "total_records": total,
        "instrument_ids": sorted(instrument_ids),
        "action_counts": dict(sorted(action_counts.items())),
        "side_counts": dict(sorted(side_counts.items())),
        "buyer_aggressor_volume_t0_t15": buyer_volume,
        "seller_aggressor_volume_t0_t15": seller_volume,
        "initial_sign": initial_sign,
        "dbid0": dbid0, "dask0": dask0, "dbid1": dbid1, "dask1": dask1,
        "coverage": coverage,
        "malformed_snapshot_count": malformed_snapshots,
        "locked_crossed_record_count": locked_crossed_records,
        "max_locked_crossed_duration_ms": max_locked_crossed_duration_ns / 1_000_000,
        "containment_violation_count": containment_violations,
        "monotonicity_violation_count": monotonicity_violations,
        **classification,
        "semantic_gates": gates,
        "semantic_gate_pass": passed,
        "verdict": "PASS_DEPTH_SEMANTICS" if passed else "PARK_SOURCE_SEMANTICS",
    }


def decode_and_analyze(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file() or path.stat().st_size <= len(_ZSTD_MAGIC):
        raise AcquisitionError("DBN Zstandard file missing or empty")
    with path.open("rb") as handle:
        if handle.read(len(_ZSTD_MAGIC)) != _ZSTD_MAGIC:
            raise AcquisitionError("DBN Zstandard signature mismatch")
    try:
        import databento as db
        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        if int(metadata.version) != DBN_VERSION or metadata.dataset != DATASET or schema != SCHEMA:
            raise AcquisitionError("DBN metadata contract mismatch")
        start_ns = int(datetime.fromisoformat(START.replace("Z", "+00:00")).timestamp() * 1e9)
        end_ns = int(datetime.fromisoformat(END.replace("Z", "+00:00")).timestamp() * 1e9)
        analysis = analyze_records(store, start_ns, end_ns)
        raw = {
            "raw_sha256": sha256_file(path), "raw_bytes": path.stat().st_size,
            "dbn_version": int(metadata.version), "dataset": metadata.dataset,
            "schema": schema, "metadata_start": int(metadata.start),
            "metadata_end": int(metadata.end),
        }
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(f"DBNv3 decode failed: {exc}") from exc
    return raw, analysis


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    require_workspace_path(workspace, workspace, "workspace")
    runtime = require_workspace_path(workspace, workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise AcquisitionError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise AcquisitionError("Databento DBNv3 runtime mismatch")
    bindings = validate_registry_authority(workspace)
    client = make_client(load_api_key())
    args = request_args()
    live_cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
    live_bytes = int(client.metadata.get_billable_size(**args))
    if not math.isfinite(live_cost) or live_cost < 0 or live_cost > OWNER_CEILING_USD:
        raise AcquisitionError("live pilot quote exceeds USD 0.01 ceiling")
    if live_bytes <= 0:
        raise AcquisitionError("live pilot quote has no billable payload")

    root = require_workspace_path(workspace, workspace / OUTPUT_REL, "output root")
    if root.exists():
        raise AcquisitionError("exclusive pilot output root already exists; automatic retry forbidden")
    root.mkdir(parents=True, exist_ok=False)
    raw_dir = root / "raw"
    raw_dir.mkdir()
    plan_path = root / "acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    analysis_path = root / "pilot_semantics_analysis.json"
    receipt_path = root / "pilot_acquisition_receipt.json"
    final = raw_dir / "EVT0001_20190103T150000_20190103T150200_mbp-10.dbn.zst"
    partial = final.with_suffix(final.suffix + ".partial")
    live_plan = {
        "schema_version": "event_depth_transfer_001_live_plan.v1",
        "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID, "event_clock_id": EVENT_ID,
        "request_args": args, "stype_out": STYPE_OUT,
        "owner_ceiling_usd": OWNER_CEILING_USD,
        "live_estimated_usd": live_cost, "live_billable_bytes": live_bytes,
        "paid_call_limit": 1, "automatic_retry_authorized": False,
        "outcome_fields_authorized": [], "bindings": bindings,
    }
    write_json_atomic(plan_path, live_plan)
    manifest = {
        "schema_version": "event_depth_transfer_001_manifest.v1",
        "status": "IN_FLIGHT", "updated_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID, "acquisition_id": ACQUISITION_ID,
        "metadata_get_cost_calls": 1, "metadata_get_billable_size_calls": 1,
        "paid_timeseries_calls": 0, "batch_calls": 0,
        "automatic_retry_authorized": False, "eurusd_outcome_fields_used": [],
        "partial_path": str(partial.relative_to(workspace)).replace("\\", "/"),
    }
    write_json_atomic(manifest_path, manifest)
    try:
        client.timeseries.get_range(**args, stype_out=STYPE_OUT, path=partial)
    except Exception as exc:
        raise AcquisitionError(f"paid pilot request failed: {type(exc).__name__}") from exc
    manifest["paid_timeseries_calls"] = 1
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)

    raw_info, semantics = decode_and_analyze(partial)
    os.replace(partial, final)
    semantics.update({
        "raw_path": str(final.relative_to(workspace)).replace("\\", "/"),
        "raw_sha256": raw_info["raw_sha256"], "raw_bytes": raw_info["raw_bytes"],
    })
    write_json_atomic(analysis_path, semantics)
    manifest.update({
        "status": "COMPLETE", "updated_at_utc": utc_now(),
        "raw_path": semantics["raw_path"], "raw_sha256": raw_info["raw_sha256"],
        "raw_bytes": raw_info["raw_bytes"], "decoded_record_count": semantics["total_records"],
        "semantic_verdict": semantics["verdict"], "partial_path": None,
    })
    write_json_atomic(manifest_path, manifest)
    receipt = {
        "schema_version": "event_depth_transfer_001_pilot_receipt.v1",
        "created_at_utc": utc_now(), "status": "PAID_PILOT_COMPLETE",
        "hypothesis_id": HYPOTHESIS_ID, "acquisition_id": ACQUISITION_ID,
        "event_clock_id": EVENT_ID, "dataset": DATASET, "schema": SCHEMA,
        "symbol": SYMBOL, "start": START, "end": END,
        "owner_ceiling_usd": OWNER_CEILING_USD,
        "live_estimated_usd": live_cost, "live_billable_bytes": live_bytes,
        "runtime": {"python": sys.version.split()[0], "databento": SDK_VERSION,
                    "databento_dbn": DBN_PACKAGE_VERSION, "dbn_version": DBN_VERSION},
        "raw": raw_info,
        "semantics_analysis_path": str(analysis_path.relative_to(workspace)).replace("\\", "/"),
        "semantics_analysis_sha256": sha256_file(analysis_path),
        "semantic_verdict": semantics["verdict"],
        "classification": semantics["classification"],
        "direction": semantics["direction"], "transfer_score": semantics["transfer_score"],
        "bindings": {**bindings, "live_plan_sha256": sha256_file(plan_path),
                     "download_manifest_sha256": sha256_file(manifest_path)},
        "api_method_counters": {"metadata.get_cost": 1,
                                "metadata.get_billable_size": 1,
                                "timeseries.get_range": 1, "batch": 0},
        "eurusd_outcome_fields_used": [], "economics_authorized": False,
        "mql5_authorized": False, "mt5_authorized": False,
        "model0_authorized": False, "validation_authorized": False,
        "holdout_authorized": False, "paper_trading_authorized": False,
        "live_trading_authorized": False, "market_edge_claim_authorized": False,
    }
    write_json_atomic(receipt_path, receipt)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        receipt_path = execute(args.workspace.resolve())
        receipt = json.loads(receipt_path.read_text(encoding="ascii"))
        print(
            "EVENT_DEPTH_TRANSFER_001_PILOT_OK "
            f"cost={receipt['live_estimated_usd']:.12f} "
            f"verdict={receipt['semantic_verdict']} "
            f"classification={receipt['classification']}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"EVENT_DEPTH_TRANSFER_001_PILOT_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

