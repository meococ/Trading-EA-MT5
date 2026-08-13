#!/usr/bin/env python3
"""Build one outcome-blind HYP007 CME 6E aggressor-flow source receipt."""

from __future__ import annotations

import argparse
import calendar
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-007"
ATTEMPT_ID = "EVENTAGGFLOW007-SOURCE-QUALITY-001"
PARENT_HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-006"
PARENT_ACQUISITION_ID = "EVENTAGGFLOW006-TRADES-DESIGN-SOURCE-001"

BASE_REL = "03. EA Developer/EA_EventAggressorFlow/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_QUALITY_PLAN.md"
AUTHORITY_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_AUTHORITY.json"
TOOL_REL = BASE_REL + "build_event_aggflow_007_source_quality.py"
TEST_REL = BASE_REL + "tests/test_build_event_aggflow_007_source_quality.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
RUNTIME_RECEIPT_REL = (
    BASE_REL + "HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json"
)
PARENT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_aggflow/"
    f"{PARENT_HYPOTHESIS_ID}/{PARENT_ACQUISITION_ID}"
)
OUTPUT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"

PLAN_SHA256 = "FB5C326DBCE79E0249101056097FA3510184C90058F227652359690E4BA56F4E"
RUNTIME_RECEIPT_SHA256 = (
    "E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD"
)
SDK_VERSION = "0.55.1"
DBN_PACKAGE_VERSION = "0.35.0"
DATASET = "GLBX.MDP3"
SCHEMA = "trades"
SYMBOL = "6E.v.0"
EXPECTED_EVENTS = 329
MIN_DIRECT_EVENTS = 313
MIN_NONZERO_EVENTS = 261
MIN_DIRECTION_SHARE = 0.25
_ZSTD_MAGIC = bytes.fromhex("28B52FFD")
_REPARSE_ATTRIBUTE = 0x400


class SourceQualityError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise SourceQualityError(f"{label} must stay on D:")
    return resolved


def is_reparse(path: Path) -> bool:
    try:
        return bool(os.lstat(path).st_file_attributes & _REPARSE_ATTRIBUTE)
    except AttributeError:
        return path.is_symlink()


def ensure_contained_file(path: Path, root: Path, label: str) -> Path:
    root = root.resolve()
    if is_reparse(root):
        raise SourceQualityError(f"{label} root must not be a reparse point")
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SourceQualityError(f"{label} escapes parent raw root") from exc
    if not resolved.is_file() or is_reparse(path):
        raise SourceQualityError(f"{label} must be a regular non-reparse file")
    return resolved


def parse_utc_ns(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SourceQualityError("invalid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise SourceQualityError("timestamp must be UTC-aware")
    parsed = parsed.astimezone(timezone.utc)
    return calendar.timegm(parsed.utctimetuple()) * 1_000_000_000 + parsed.microsecond * 1000


def normalize_code(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def aggregate_records(
    records: Iterable[Any], *, start_ns: int, end_ns: int
) -> dict[str, int]:
    if start_ns >= end_ns:
        raise SourceQualityError("invalid half-open source window")
    record_count = 0
    direct_records = 0
    unclassified_records = 0
    buy_volume = 0
    sell_volume = 0
    for record in records:
        record_count += 1
        action = normalize_code(getattr(record, "action", None))
        side = normalize_code(getattr(record, "side", None))
        size = getattr(record, "size", None)
        ts_recv = getattr(record, "ts_recv", None)
        if action != "T":
            raise SourceQualityError("non-trade action in trades schema")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise SourceQualityError("nonpositive or noninteger trade size")
        if isinstance(ts_recv, bool) or not isinstance(ts_recv, int):
            raise SourceQualityError("malformed ts_recv")
        if not start_ns <= ts_recv < end_ns:
            raise SourceQualityError("record ts_recv outside half-open source window")
        if side == "B":
            direct_records += 1
            buy_volume += size
        elif side == "A":
            direct_records += 1
            sell_volume += size
        elif side == "N":
            unclassified_records += 1
        else:
            raise SourceQualityError("unknown aggressor side")
    return {
        "record_count": record_count,
        "direct_record_count": direct_records,
        "unclassified_record_count": unclassified_records,
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "signed_flow": buy_volume - sell_volume,
    }


def classify_row(values: dict[str, int], coverage_kind: str) -> str:
    if coverage_kind == "live_zero_byte":
        return "NO_SOURCE"
    if values["direct_record_count"] == 0:
        return "NO_DIRECT"
    if values["signed_flow"] > 0:
        return "BUY"
    if values["signed_flow"] < 0:
        return "SELL"
    return "TIE"


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceQualityError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise SourceQualityError(f"{label} must be a JSON object")
    return value


def validate_authority(workspace: Path) -> dict[str, Any]:
    plan = require_d(workspace / PLAN_REL, "source-quality plan")
    authority_path = require_d(workspace / AUTHORITY_REL, "source authority")
    tool = require_d(workspace / TOOL_REL, "source-quality tool")
    test = require_d(workspace / TEST_REL, "source-quality tests")
    runtime_receipt = require_d(workspace / RUNTIME_RECEIPT_REL, "runtime receipt")
    registry = require_d(workspace / REGISTRY_REL, "registry")
    if sha256_file(plan) != PLAN_SHA256:
        raise SourceQualityError("source-quality plan drifted")
    if sha256_file(runtime_receipt) != RUNTIME_RECEIPT_SHA256:
        raise SourceQualityError("DBNv3 runtime receipt drifted")
    authority = load_json(authority_path, "source authority")
    tool_sha = sha256_file(tool)
    test_sha = sha256_file(test)
    authority_sha = sha256_file(authority_path)
    required = {
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "parent_acquisition_id": PARENT_ACQUISITION_ID,
        "source_quality_plan_sha256": PLAN_SHA256,
        "reviewed_source_tool_sha256": tool_sha,
        "reviewed_source_test_sha256": test_sha,
        "runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
    }
    for key, expected in required.items():
        if authority.get(key) != expected:
            raise SourceQualityError(f"source authority binding mismatch: {key}")
    for key in (
        "network_authorized",
        "api_key_authorized",
        "outcome_prices_authorized",
        "economics_authorized",
        "validation_source_authorized",
        "mql5_authorized",
        "mt5_authorized",
    ):
        if authority.get(key) is not False:
            raise SourceQualityError(f"forbidden source authority open: {key}")
    matches: list[dict[str, Any]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append(row)
    if not matches:
        raise SourceQualityError("source-quality hypothesis absent from registry")
    row = matches[-1]
    validation = row.get("validation", {})
    expected_registry = {
        "source_quality_plan_sha256": PLAN_SHA256,
        "source_authority_receipt_sha256": authority_sha,
        "reviewed_source_tool_sha256": tool_sha,
        "reviewed_source_test_sha256": test_sha,
        "runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
        "parent_live_plan_sha256": authority.get("parent_live_plan_sha256"),
        "parent_download_manifest_sha256": authority.get(
            "parent_download_manifest_sha256"
        ),
        "parent_paid_acquisition_receipt_sha256": authority.get(
            "parent_paid_acquisition_receipt_sha256"
        ),
    }
    if (
        row.get("state") != "probe"
        or row.get("prereg_sha256") != PLAN_SHA256
        or validation.get("source_quality_run_authorized") is not True
    ):
        raise SourceQualityError("registry source-quality authority mismatch")
    for key, expected in expected_registry.items():
        if validation.get(key) != expected:
            raise SourceQualityError(f"registry binding mismatch: {key}")
    for key in (
        "network_authorized",
        "paid_requests_authorized",
        "outcome_prices_authorized",
        "economics_authorized",
        "mql5_authorized",
        "mt5_authorized",
        "model0_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise SourceQualityError(f"forbidden registry authority open: {key}")
    return {"authority": authority, "authority_sha256": authority_sha}


def validate_parent(workspace: Path, authority: dict[str, Any]) -> dict[str, Any]:
    root = require_d(workspace / PARENT_ROOT_REL, "parent acquisition root")
    plan_path = root / "acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    receipt_path = root / "paid_acquisition_receipt.json"
    for path, key in (
        (plan_path, "parent_live_plan_sha256"),
        (manifest_path, "parent_download_manifest_sha256"),
        (receipt_path, "parent_paid_acquisition_receipt_sha256"),
    ):
        if not path.is_file() or sha256_file(path) != authority.get(key):
            raise SourceQualityError(f"parent artifact drift: {key}")
    plan = load_json(plan_path, "parent live plan")
    manifest = load_json(manifest_path, "parent download manifest")
    receipt = load_json(receipt_path, "parent paid acquisition receipt")
    windows = plan.get("windows")
    downloads = manifest.get("downloads")
    empties = manifest.get("source_empty_windows")
    if (
        plan.get("hypothesis_id") != PARENT_HYPOTHESIS_ID
        or plan.get("acquisition_id") != PARENT_ACQUISITION_ID
        or plan.get("dataset") != DATASET
        or plan.get("schema") != SCHEMA
        or plan.get("symbol") != SYMBOL
        or plan.get("request_count") != EXPECTED_EVENTS
        or float(plan.get("live_estimated_total_usd")) > 1.0
        or not isinstance(windows, list)
        or len(windows) != EXPECTED_EVENTS
        or manifest.get("status") != "DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED"
        or manifest.get("coverage_count") != EXPECTED_EVENTS
        or manifest.get("in_flight") is not None
        or not isinstance(downloads, list)
        or not isinstance(empties, list)
        or len(downloads) + len(empties) != EXPECTED_EVENTS
        or receipt.get("status") != "COMPLETE_RAW_SOURCE_QUALITY_REQUIRED"
    ):
        raise SourceQualityError("parent terminal acquisition contract mismatch")
    for payload in (plan, manifest, receipt):
        if (
            payload.get("outcome_fields_used") is not False
            or payload.get("price_data_read") is not False
            or payload.get("validation_source_read") is not False
        ):
            raise SourceQualityError("parent outcome/validation boundary opened")
    identities = [item.get("request_id") for item in windows]
    if identities != sorted(identities) or len(set(identities)) != EXPECTED_EVENTS:
        raise SourceQualityError("parent live identities invalid")
    return {
        "root": root,
        "raw": (root / "raw").resolve(),
        "plan": plan,
        "manifest": manifest,
        "receipt": receipt,
        "windows": {item["request_id"]: item for item in windows},
        "plan_path": plan_path,
        "manifest_path": manifest_path,
        "receipt_path": receipt_path,
    }


def decode_dbn(path: Path, *, start_ns: int, end_ns: int) -> tuple[dict[str, int], dict[str, Any]]:
    if path.stat().st_size <= len(_ZSTD_MAGIC):
        raise SourceQualityError("DBN file is empty")
    with path.open("rb") as handle:
        if handle.read(len(_ZSTD_MAGIC)) != _ZSTD_MAGIC:
            raise SourceQualityError("DBN Zstd signature mismatch")
    try:
        import databento as db

        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema_value = normalize_code(metadata.schema).lower()
        if (
            int(metadata.version) != 3
            or metadata.dataset != DATASET
            or schema_value != SCHEMA
        ):
            raise SourceQualityError("DBN metadata mismatch")
        values = aggregate_records(store, start_ns=start_ns, end_ns=end_ns)
    except SourceQualityError:
        raise
    except Exception as exc:
        raise SourceQualityError(f"DBN decode failure: {exc}") from exc
    return values, {
        "dbn_version": int(metadata.version),
        "dataset": metadata.dataset,
        "schema": schema_value,
    }


def build_rows(parent: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = parent["manifest"]
    windows = parent["windows"]
    raw_root = parent["raw"]
    downloads = {item["request_id"]: item for item in manifest["downloads"]}
    empties = {item["request_id"]: item for item in manifest["source_empty_windows"]}
    if len(downloads) != len(manifest["downloads"]) or len(empties) != len(
        manifest["source_empty_windows"]
    ):
        raise SourceQualityError("duplicate manifest identities")
    if downloads.keys() & empties.keys() or set(windows) != downloads.keys() | empties.keys():
        raise SourceQualityError("manifest coverage identity mismatch")
    rows: list[dict[str, Any]] = []
    for request_id in sorted(windows):
        window = windows[request_id]
        start = str(window["start"])
        end = str(window["end"])
        start_ns = parse_utc_ns(start)
        end_ns = parse_utc_ns(end)
        if end_ns - start_ns != 15_000_000_000:
            raise SourceQualityError("source window is not exactly 15 seconds")
        if request_id in empties:
            empty = empties[request_id]
            if (
                empty.get("start") != start
                or empty.get("end") != end
                or int(empty.get("live_billable_bytes")) != 0
                or empty.get("reason")
                != "LIVE_METADATA_ZERO_BILLABLE_BYTES_NO_TIMESERIES_CALL"
            ):
                raise SourceQualityError("live zero-byte binding mismatch")
            values = {
                "record_count": 0,
                "direct_record_count": 0,
                "unclassified_record_count": 0,
                "buy_volume": 0,
                "sell_volume": 0,
                "signed_flow": 0,
            }
            coverage_kind = "live_zero_byte"
            source_sha = ""
            source_bytes = 0
        else:
            item = downloads[request_id]
            if (
                item.get("start") != start
                or item.get("end") != end
                or item.get("filename") != f"{request_id}.dbn.zst"
            ):
                raise SourceQualityError("download request binding mismatch")
            path = ensure_contained_file(
                raw_root / item["filename"], raw_root, f"DBN {request_id}"
            )
            source_sha = sha256_file(path)
            source_bytes = path.stat().st_size
            if source_sha != item.get("sha256") or source_bytes != int(item.get("bytes")):
                raise SourceQualityError("download hash/byte mismatch")
            values, _metadata = decode_dbn(path, start_ns=start_ns, end_ns=end_ns)
            if values["record_count"] != int(item.get("records")):
                raise SourceQualityError("download record-count mismatch")
            coverage_kind = "dbn"
        row = {
            "request_id": request_id,
            "event_time_utc": window["event_time_utc"],
            "start_utc": start,
            "end_utc": end,
            "coverage_kind": coverage_kind,
            **values,
            "dominance": classify_row(values, coverage_kind),
            "source_bytes": source_bytes,
            "source_sha256": source_sha,
        }
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != EXPECTED_EVENTS or len({row["request_id"] for row in rows}) != EXPECTED_EVENTS:
        raise SourceQualityError("source row population mismatch")
    direct = sum(row["direct_record_count"] > 0 for row in rows)
    buys = sum(row["dominance"] == "BUY" for row in rows)
    sells = sum(row["dominance"] == "SELL" for row in rows)
    nonzero = buys + sells
    buy_share = buys / nonzero if nonzero else 0.0
    sell_share = sells / nonzero if nonzero else 0.0
    gates = {
        "coverage_329": len(rows) == EXPECTED_EVENTS,
        "direct_events_at_least_313": direct >= MIN_DIRECT_EVENTS,
        "nonzero_events_at_least_261": nonzero >= MIN_NONZERO_EVENTS,
        "buyer_share_at_least_25pct": buy_share >= MIN_DIRECTION_SHARE,
        "seller_share_at_least_25pct": sell_share >= MIN_DIRECTION_SHARE,
        "integrity_violations_zero": True,
        "network_calls_zero": True,
        "outcome_fields_zero": True,
        "validation_source_access_zero": True,
    }
    return {
        "schema_version": "event_aggflow_007_source_quality_summary.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "generated_at_utc": utc_now(),
        "event_count": len(rows),
        "dbn_events": sum(row["coverage_kind"] == "dbn" for row in rows),
        "live_zero_byte_events": sum(
            row["coverage_kind"] == "live_zero_byte" for row in rows
        ),
        "events_with_direct_side": direct,
        "nonzero_signed_flow_events": nonzero,
        "buyer_dominant_events": buys,
        "seller_dominant_events": sells,
        "tie_events": sum(row["dominance"] == "TIE" for row in rows),
        "no_direct_events": sum(row["dominance"] == "NO_DIRECT" for row in rows),
        "no_source_events": sum(row["dominance"] == "NO_SOURCE" for row in rows),
        "buyer_share_of_nonzero": buy_share,
        "seller_share_of_nonzero": sell_share,
        "total_records": sum(row["record_count"] for row in rows),
        "total_direct_records": sum(row["direct_record_count"] for row in rows),
        "total_unclassified_records": sum(
            row["unclassified_record_count"] for row in rows
        ),
        "gates": gates,
        "source_feasibility_pass": all(gates.values()),
        "network_calls": 0,
        "api_key_accessed": False,
        "outcome_fields_used": [],
        "price_data_read": False,
        "validation_source_read": False,
        "returns_computed": 0,
        "trades_simulated": 0,
        "economics_executed": False,
    }


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    fields = [
        "request_id",
        "event_time_utc",
        "start_utc",
        "end_utc",
        "coverage_kind",
        "record_count",
        "direct_record_count",
        "unclassified_record_count",
        "buy_volume",
        "sell_volume",
        "signed_flow",
        "dominance",
        "source_bytes",
        "source_sha256",
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("ascii")


def write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def execute(workspace: Path) -> Path:
    workspace = require_d(workspace, "workspace")
    runtime = require_d(workspace / RUNTIME_REL, "DBNv3 runtime")
    if Path(sys.executable).resolve() != runtime:
        raise SourceQualityError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise SourceQualityError("DBNv3 package version mismatch")
    bound = validate_authority(workspace)
    parent = validate_parent(workspace, bound["authority"])
    output = require_d(workspace / OUTPUT_REL, "source-quality output")
    if output.exists():
        raise SourceQualityError("exclusive source-quality output already exists")
    rows = build_rows(parent)
    summary = summarize(rows)
    output.mkdir(parents=True, exist_ok=False)
    csv_path = output / "event_signed_flow.csv"
    summary_path = output / "source_quality_summary.json"
    manifest_path = output / "artifact_manifest.json"
    write_exclusive(csv_path, csv_bytes(rows))
    write_exclusive(summary_path, canonical_json(summary) + b"\n")
    manifest = {
        "schema_version": "event_aggflow_007_source_artifact_manifest.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "source_quality_plan_sha256": PLAN_SHA256,
        "source_authority_receipt_sha256": bound["authority_sha256"],
        "runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
        "parent_live_plan_sha256": sha256_file(parent["plan_path"]),
        "parent_download_manifest_sha256": sha256_file(parent["manifest_path"]),
        "parent_paid_acquisition_receipt_sha256": sha256_file(parent["receipt_path"]),
        "artifacts": [
            {
                "name": csv_path.name,
                "sha256": sha256_file(csv_path),
                "bytes": csv_path.stat().st_size,
                "rows": len(rows),
            },
            {
                "name": summary_path.name,
                "sha256": sha256_file(summary_path),
                "bytes": summary_path.stat().st_size,
            },
        ],
        "network_calls": 0,
        "api_key_accessed": False,
        "outcome_fields_used": [],
        "price_data_read": False,
        "validation_source_read": False,
        "economics_executed": False,
    }
    write_exclusive(manifest_path, canonical_json(manifest) + b"\n")
    return summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        summary_path = execute(args.workspace.resolve())
        summary = load_json(summary_path, "source summary")
        print(
            "EVENTAGGFLOW007_SOURCE_QUALITY_OK "
            f"pass={summary['source_feasibility_pass']} "
            f"events={summary['event_count']} "
            f"direct={summary['events_with_direct_side']} "
            f"nonzero={summary['nonzero_signed_flow_events']} "
            f"buy={summary['buyer_dominant_events']} "
            f"sell={summary['seller_dominant_events']}"
        )
        print(f"SUMMARY {summary_path}")
        return 0
    except SourceQualityError as exc:
        print(f"EVENTAGGFLOW007_SOURCE_QUALITY_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
