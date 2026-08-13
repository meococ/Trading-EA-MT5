#!/usr/bin/env python3
"""Acquire and inspect the single Owner-authorized EVT0001 MBP-1 pilot."""

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
import statistics
import sys
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-EVENT-L1-REPLEN-EURUSD-TICK-002"
ACQUISITION_ID = "EVENTL1REPLEN002-MBP1-PILOT-001"
PARENT_HYPOTHESIS_ID = "HYP-EVENT-L1-REPLEN-EURUSD-TICK-001"
QUOTE_ID = "EVENTL1REPLEN001-MBP1-DESIGN-FREE-QUOTE-001"
BASE_REL = "03. EA Developer/EA_EventL1Replenishment/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_PILOT_ACQUISITION_PLAN.md"
AUTHORITY_REL = BASE_REL + HYPOTHESIS_ID + "_OWNER_AUTHORITY.json"
TOOL_REL = BASE_REL + "acquire_event_l1_replen_002_pilot.py"
TEST_REL = BASE_REL + "tests/test_acquire_event_l1_replen_002_pilot.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
QUOTE_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_l1_replen/"
    f"{PARENT_HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
)
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
RUNTIME_RECEIPT_REL = (
    "03. EA Developer/EA_EventAggressorFlow/research/"
    "HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_l1_replen/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}"
)

PLAN_SHA256 = "B07C12FF6704A993D4FF52E5AECC2A6D992D526A5F6E5B56F767397AF8D5DEEB"
OWNER_AUTHORITY_SHA256 = "CF68F81DB8717F7EDE8488DC7B17E78CD03486CA0FE225833BAD6847BF21B04D"
OWNER_VERBATIM_SHA256 = "D81F34C50AACC76E9797D549ED8970CB8031E6AFEE901A5D8A6CED20CA7BEBC5"
SOURCE_QUOTE_PLAN_SHA256 = "D423A1CFF1CCA1852ACEEDDB83CA86D5700BBB50306CF1E17058A80211E32F11"
QUOTE_RECEIPT_SHA256 = "230E7D4F2BF291A78F276A7D0F4956BB2EC54CC226DE4D66E85858FA4BE31A64"
RUNTIME_RECEIPT_SHA256 = "E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD"

DATASET = "GLBX.MDP3"
SCHEMA = "mbp-1"
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
PARENT_ESTIMATED_USD = 0.00741443038
PARENT_BILLABLE_BYTES = 4_422_880
OWNER_CEILING_USD = 0.01
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")

REVIEWED_REGISTRY_ROW_SHA256: str | None = "75E247D8C9AC023C307D091C634F4A7504B820064635DAE80EBE88AB556CD756"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = '
    rb'(?:None|"[A-F0-9]{64}")\r?$'
)


class AcquisitionError(RuntimeError):
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
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def normalized_tool_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [
        i for i, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise AcquisitionError("tool must contain exactly one registry sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
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


def load_parent_quote(path: Path) -> dict[str, Any]:
    if sha256_file(path) != QUOTE_RECEIPT_SHA256:
        raise AcquisitionError("parent quote receipt drifted")
    quote = json.loads(path.read_text(encoding="ascii"))
    if (
        quote.get("hypothesis_id") != PARENT_HYPOTHESIS_ID
        or quote.get("quote_id") != QUOTE_ID
        or quote.get("dataset") != DATASET
        or quote.get("schema") != SCHEMA
        or quote.get("symbol") != SYMBOL
        or quote.get("stype_in") != STYPE_IN
        or quote.get("paid_request_made") is not False
        or quote.get("source_payload_read") is not False
        or quote.get("validation_source_read") is not False
        or quote.get("bindings", {}).get("plan_sha256") != SOURCE_QUOTE_PLAN_SHA256
    ):
        raise AcquisitionError("parent quote contract mismatch")
    matches = [item for item in quote.get("quotes", []) if item.get("request_id") == EVENT_ID]
    if len(matches) != 1:
        raise AcquisitionError("parent pilot identity mismatch")
    item = matches[0]
    if (
        item.get("event_clock_id") != EVENT_ID
        or item.get("start") != START
        or item.get("end") != END
        or float(item.get("estimated_usd")) != PARENT_ESTIMATED_USD
        or int(item.get("billable_bytes")) != PARENT_BILLABLE_BYTES
    ):
        raise AcquisitionError("parent pilot quote fields drifted")
    return item


def validate_owner_authority(path: Path) -> dict[str, Any]:
    if sha256_file(path) != OWNER_AUTHORITY_SHA256:
        raise AcquisitionError("Owner authority receipt drifted")
    authority = json.loads(path.read_text(encoding="utf-8"))
    pilot = authority.get("pilot", {})
    policy = authority.get("standing_research_acquisition_policy", {})
    if (
        authority.get("hypothesis_id") != HYPOTHESIS_ID
        or authority.get("owner_authorization_verbatim_sha256") != OWNER_VERBATIM_SHA256
        or authority.get("authorization_basis_quote_id") != QUOTE_ID
        or authority.get("authorization_basis_source_quote_plan_sha256") != SOURCE_QUOTE_PLAN_SHA256
        or authority.get("authorization_basis_quote_receipt_sha256") != QUOTE_RECEIPT_SHA256
        or authority.get("paid_acquisition_plan_sha256") != PLAN_SHA256
        or pilot.get("approved") is not True
        or float(pilot.get("approved_max_usd")) != OWNER_CEILING_USD
        or pilot.get("dataset") != DATASET
        or pilot.get("schema") != SCHEMA
        or pilot.get("symbol") != SYMBOL
        or pilot.get("event_clock_id") != EVENT_ID
        or pilot.get("start") != START
        or pilot.get("end") != END
        or pilot.get("request_count") != 1
        or pilot.get("timeseries_call_limit") != 1
        or pilot.get("automatic_retry_authorized") is not False
        or policy.get("approved") is not True
        or float(policy.get("aggregate_campaign_cost_must_be_strictly_below")) != 10.0
        or policy.get("live_trading_capital_authorized") is not False
        or authority.get("eurusd_outcomes_authorized") is not False
        or authority.get("validation_source_authorized") is not False
    ):
        raise AcquisitionError("Owner authority contract mismatch")
    return authority


def validate_registry_authority(workspace: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise AcquisitionError("registry sentinel is not armed")
    plan = require_d(workspace / PLAN_REL, "plan")
    authority = require_d(workspace / AUTHORITY_REL, "authority")
    quote = require_d(workspace / QUOTE_REL, "parent quote")
    runtime_receipt = require_d(workspace / RUNTIME_RECEIPT_REL, "runtime receipt")
    tool = require_d(workspace / TOOL_REL, "tool")
    test = require_d(workspace / TEST_REL, "test")
    registry = require_d(workspace / REGISTRY_REL, "registry")
    if (
        sha256_file(plan) != PLAN_SHA256
        or sha256_file(authority) != OWNER_AUTHORITY_SHA256
        or sha256_file(quote) != QUOTE_RECEIPT_SHA256
        or sha256_file(runtime_receipt) != RUNTIME_RECEIPT_SHA256
    ):
        raise AcquisitionError("foundation hash drift")
    validate_owner_authority(authority)
    load_parent_quote(quote)
    payload = tool.read_bytes()
    tool_base = normalized_tool_base_sha256(payload)
    test_sha = sha256_file(test)
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
    row_sha = sha256_bytes(line)
    validation = row.get("validation", {})
    if (
        row_sha != REVIEWED_REGISTRY_ROW_SHA256
        or row.get("state") != "probe"
        or row.get("prereg_sha256") != PLAN_SHA256
        or validation.get("paid_acquisition_authorized") is not True
        or validation.get("source_download_authorized") is not True
        or validation.get("reviewed_acquisition_tool_base_sha256") != tool_base
        or validation.get("reviewed_acquisition_test_sha256") != test_sha
        or validation.get("owner_authority_receipt_sha256") != OWNER_AUTHORITY_SHA256
        or validation.get("quote_receipt_sha256") != QUOTE_RECEIPT_SHA256
    ):
        raise AcquisitionError("registry acquisition authority mismatch")
    for key in (
        "economics_authorized", "outcome_prices_authorized", "mql5_authorized",
        "model0_authorized", "research_validation_access_authorized",
        "research_holdout_access_authorized", "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise AcquisitionError(f"forbidden registry authority open: {key}")
    if ACQUISITION_ID in row.get("run_ids", []):
        raise AcquisitionError("pilot attempt already consumed")
    return {
        "registry_row_sha256": row_sha,
        "tool_base_sha256": tool_base,
        "tool_file_sha256": sha256_bytes(payload),
        "test_sha256": test_sha,
    }


def _enum_char(value: Any) -> str:
    raw = getattr(value, "value", value)
    if isinstance(raw, bytes):
        raw = raw.decode("ascii")
    if isinstance(raw, int):
        raw = chr(raw)
    return str(raw)


def analyze_records(records: Iterable[Any], start_ns: int, end_ns: int) -> dict[str, Any]:
    action_counts: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    field_values: dict[str, set[str]] = {name: set() for name in (
        "ts_recv", "ts_event", "action", "side", "price", "size", "flags",
        "depth", "sequence", "bid_px", "ask_px", "bid_sz", "ask_sz",
        "bid_ct", "ask_ct",
    )}
    field_nulls: Counter[str] = Counter()
    total = 0
    trades = 0
    monotonicity_violations = 0
    containment_violations = 0
    bbo_price_changes = 0
    bbo_size_updates = 0
    bbo_size_changes_unchanged_price = 0
    zero_size_or_empty_book = 0
    locked_or_crossed = 0
    valid_bbo_records = 0
    first_ts: int | None = None
    last_ts: int | None = None
    previous_ts: int | None = None
    previous_bbo: tuple[int, int, int, int] | None = None
    gaps_ms: list[float] = []

    for message in records:
        total += 1
        ts_recv = int(message.ts_recv)
        ts_event = int(message.ts_event)
        action = _enum_char(message.action)
        side = _enum_char(message.side)
        action_counts[action] += 1
        side_counts[side] += 1
        trades += int(action == "T")
        if first_ts is None:
            first_ts = ts_recv
        last_ts = ts_recv
        if not start_ns <= ts_recv < end_ns:
            containment_violations += 1
        if previous_ts is not None:
            if ts_recv < previous_ts:
                monotonicity_violations += 1
            else:
                gaps_ms.append((ts_recv - previous_ts) / 1_000_000.0)
        previous_ts = ts_recv

        try:
            level = list(message.levels)[0]
            bid_px, ask_px = int(level.bid_px), int(level.ask_px)
            bid_sz, ask_sz = int(level.bid_sz), int(level.ask_sz)
            bid_ct, ask_ct = int(level.bid_ct), int(level.ask_ct)
        except (AttributeError, IndexError, TypeError, ValueError):
            bid_px = ask_px = bid_sz = ask_sz = bid_ct = ask_ct = 0
            for name in ("bid_px", "ask_px", "bid_sz", "ask_sz", "bid_ct", "ask_ct"):
                field_nulls[name] += 1

        values = {
            "ts_recv": ts_recv, "ts_event": ts_event, "action": action,
            "side": side, "price": getattr(message, "price", None),
            "size": getattr(message, "size", None), "flags": getattr(message, "flags", None),
            "depth": getattr(message, "depth", None), "sequence": getattr(message, "sequence", None),
            "bid_px": bid_px, "ask_px": ask_px, "bid_sz": bid_sz,
            "ask_sz": ask_sz, "bid_ct": bid_ct, "ask_ct": ask_ct,
        }
        for name, value in values.items():
            if value is None:
                field_nulls[name] += 1
            else:
                field_values[name].add(str(value))

        if bid_px > 0 and ask_px > 0:
            valid_bbo_records += 1
            locked_or_crossed += int(bid_px >= ask_px)
        if bid_sz <= 0 or ask_sz <= 0 or bid_px <= 0 or ask_px <= 0:
            zero_size_or_empty_book += 1
        current_bbo = (bid_px, ask_px, bid_sz, ask_sz)
        if previous_bbo is not None:
            price_changed = current_bbo[:2] != previous_bbo[:2]
            size_changed = current_bbo[2:] != previous_bbo[2:]
            bbo_price_changes += int(price_changed)
            bbo_size_updates += int(size_changed)
            bbo_size_changes_unchanged_price += int(size_changed and not price_changed)
        previous_bbo = current_bbo

    required_populated = all(len(values) > 0 for values in field_values.values())
    gates = {
        "records_nonzero": total > 0,
        "half_open_containment": containment_violations == 0,
        "ts_recv_monotone": monotonicity_violations == 0,
        "required_fields_populated": required_populated,
        "trade_actions_present": trades > 0,
        "bbo_size_updates_present": bbo_size_updates > 0,
        "valid_bbo_present": valid_bbo_records > 0,
    }
    return {
        "total_records": total,
        "action_counts": dict(sorted(action_counts.items())),
        "side_counts": dict(sorted(side_counts.items())),
        "trade_action_count": trades,
        "bbo_price_change_count": bbo_price_changes,
        "bbo_size_update_count": bbo_size_updates,
        "bbo_size_change_unchanged_price_count": bbo_size_changes_unchanged_price,
        "zero_size_or_empty_book_count": zero_size_or_empty_book,
        "first_ts_recv_ns": first_ts,
        "last_ts_recv_ns": last_ts,
        "containment_violation_count": containment_violations,
        "monotonicity_violation_count": monotonicity_violations,
        "median_inter_message_gap_ms": statistics.median(gaps_ms) if gaps_ms else None,
        "max_inter_message_gap_ms": max(gaps_ms) if gaps_ms else None,
        "locked_or_crossed_record_share": (
            locked_or_crossed / valid_bbo_records if valid_bbo_records else None
        ),
        "field_unique_value_counts": {k: len(v) for k, v in field_values.items()},
        "field_null_counts": dict(sorted(field_nulls.items())),
        "semantic_gates": gates,
        "semantic_gate_pass": all(gates.values()),
        "verdict": "PASS_SEMANTICS" if all(gates.values()) else "PARK_SOURCE_SEMANTICS",
    }


def decode_and_analyze(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file() or path.stat().st_size <= len(_ZSTD_MAGIC):
        raise AcquisitionError("DBN Zstandard file missing or empty")
    raw_sha256 = sha256_file(path)
    with path.open("rb") as handle:
        if handle.read(len(_ZSTD_MAGIC)) != _ZSTD_MAGIC:
            raise AcquisitionError("DBN Zstandard signature mismatch")
    try:
        import databento as db
        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema_value = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        metadata_summary = {
            "version": int(metadata.version),
            "dataset": metadata.dataset,
            "schema": schema_value,
            "start": int(metadata.start),
            "end": int(metadata.end),
        }
        if (
            metadata_summary["version"] != DBN_VERSION
            or metadata_summary["dataset"] != DATASET
            or metadata_summary["schema"] != SCHEMA
        ):
            raise AcquisitionError("DBN metadata contract mismatch")
        start_ns = int(datetime.fromisoformat(START.replace("Z", "+00:00")).timestamp() * 1e9)
        end_ns = int(datetime.fromisoformat(END.replace("Z", "+00:00")).timestamp() * 1e9)
        analysis = analyze_records(store, start_ns, end_ns)
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(f"DBNv3 decode failed: {exc}") from exc
    return {"raw_sha256": raw_sha256, "raw_bytes": path.stat().st_size, **metadata_summary}, analysis


def execute(workspace: Path) -> Path:
    workspace = require_d(workspace, "workspace")
    runtime = require_d(workspace / RUNTIME_REL, "runtime")
    if Path(sys.executable).resolve() != runtime:
        raise AcquisitionError("wrong Python runtime")
    if (
        importlib.metadata.version("databento") != SDK_VERSION
        or importlib.metadata.version("databento-dbn") != DBN_PACKAGE_VERSION
    ):
        raise AcquisitionError("Databento DBNv3 runtime mismatch")
    bindings = validate_registry_authority(workspace)
    load_parent_quote(require_d(workspace / QUOTE_REL, "parent quote"))
    key = load_api_key()
    client = make_client(key)
    args = request_args()
    live_cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
    live_bytes = int(client.metadata.get_billable_size(**args))
    if (
        not math.isfinite(live_cost) or live_cost < 0
        or live_cost > OWNER_CEILING_USD or live_bytes <= 0
    ):
        raise AcquisitionError("live pilot quote outside Owner contract")

    root = require_d(workspace / OUTPUT_REL, "output root")
    if root.exists():
        raise AcquisitionError("exclusive pilot output root already exists; automatic retry forbidden")
    root.mkdir(parents=True, exist_ok=False)
    raw_dir = root / "raw"
    raw_dir.mkdir()
    plan_path = root / "acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    receipt_path = root / "pilot_acquisition_receipt.json"
    analysis_path = root / "pilot_semantics_analysis.json"
    final = raw_dir / "EVT0001_20190103T150000_20190103T150200_mbp-1.dbn.zst"
    partial = final.with_suffix(final.suffix + ".partial")
    live_plan = {
        "schema_version": "event_l1_replen_002_pilot_live_plan.v1",
        "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID, "event_clock_id": EVENT_ID,
        "request_args": args, "stype_out": STYPE_OUT,
        "owner_ceiling_usd": OWNER_CEILING_USD,
        "live_estimated_usd": live_cost, "live_billable_bytes": live_bytes,
        "paid_call_limit": 1, "automatic_retry_authorized": False,
        "bindings": bindings,
    }
    write_json_atomic(plan_path, live_plan)
    manifest = {
        "schema_version": "event_l1_replen_002_pilot_manifest.v1",
        "status": "IN_FLIGHT", "updated_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID, "acquisition_id": ACQUISITION_ID,
        "in_flight": {
            "event_clock_id": EVENT_ID, "start": START, "end": END,
            "partial_path": str(partial.relative_to(workspace)).replace("\\", "/"),
            "live_estimated_usd": live_cost, "live_billable_bytes": live_bytes,
        },
        "metadata_get_cost_calls": 1, "metadata_get_billable_size_calls": 1,
        "paid_timeseries_calls": 0, "batch_calls": 0,
        "eurusd_outcome_fields_used": [], "validation_source_read": False,
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
    semantics["raw_path"] = str(final.relative_to(workspace)).replace("\\", "/")
    semantics["raw_sha256"] = raw_info["raw_sha256"]
    semantics["raw_bytes"] = raw_info["raw_bytes"]
    write_json_atomic(analysis_path, semantics)
    manifest.update({
        "status": "COMPLETE", "updated_at_utc": utc_now(), "in_flight": None,
        "raw_path": semantics["raw_path"], "raw_sha256": raw_info["raw_sha256"],
        "raw_bytes": raw_info["raw_bytes"], "decoded_record_count": semantics["total_records"],
        "semantic_verdict": semantics["verdict"],
    })
    write_json_atomic(manifest_path, manifest)
    receipt = {
        "schema_version": "event_l1_replen_002_pilot_acquisition_receipt.v1",
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
        "bindings": {
            "paid_acquisition_plan_sha256": PLAN_SHA256,
            "owner_authority_receipt_sha256": OWNER_AUTHORITY_SHA256,
            "parent_quote_receipt_sha256": QUOTE_RECEIPT_SHA256,
            "runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
            "live_plan_sha256": sha256_file(plan_path),
            "download_manifest_sha256": sha256_file(manifest_path),
            **bindings,
        },
        "api_method_counters": {"metadata.get_cost": 1,
                                "metadata.get_billable_size": 1,
                                "timeseries.get_range": 1,
                                "batch": 0},
        "eurusd_outcome_fields_used": [], "validation_source_read": False,
        "economics_authorized": False, "mql5_authorized": False,
        "model0_authorized": False, "paper_trading_authorized": False,
        "live_trading_authorized": False,
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
            "EVENTL1REPLEN002_PILOT_OK "
            f"cost={receipt['live_estimated_usd']:.12f} "
            f"records={receipt['raw']['raw_bytes']}bytes "
            f"verdict={receipt['semantic_verdict']}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"EVENTL1REPLEN002_PILOT_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
