#!/usr/bin/env python3
"""Recover EVT0001 DBNv3 and resume EVENTAGGFLOW006 under USD 1.00."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
from pathlib import Path
import re
import sys
import threading
import time as time_module
from typing import Any, Callable, Iterator


HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-006"
ACQUISITION_ID = "EVENTAGGFLOW006-TRADES-DESIGN-SOURCE-001"
PARENT_HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-001"
QUOTE_ID = "EVENTAGGFLOW001-TRADES-DESIGN-FREE-QUOTE-001"

BASE_REL = "03. EA Developer/EA_EventAggressorFlow/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_DBV3_RECOVERY_ACQUISITION_PLAN.md"
OWNER_REL = BASE_REL + HYPOTHESIS_ID + "_OWNER_AUTHORITY.json"
TOOL_REL = BASE_REL + "acquire_event_aggflow_006_trades.py"
TEST_REL = BASE_REL + "tests/test_acquire_event_aggflow_006_trades.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
QUOTE_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_aggflow/"
    f"{PARENT_HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
)
RUNTIME_REL = "02. AlphaFactory/runtime/python-databento-dbnv3/Scripts/python.exe"
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_aggflow/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}"
)
RUNTIME_RECEIPT_REL = (
    BASE_REL + "HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json"
)
RECOVERY_PARENT_HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-004"
RECOVERY_PARENT_ACQUISITION_ID = "EVENTAGGFLOW004-TRADES-DESIGN-SOURCE-001"
RECOVERY_PARENT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_aggflow/"
    f"{RECOVERY_PARENT_HYPOTHESIS_ID}/{RECOVERY_PARENT_ACQUISITION_ID}"
)
RECOVERY_PARENT_PLAN_REL = RECOVERY_PARENT_ROOT_REL + "/acquisition_plan.json"
RECOVERY_PARENT_MANIFEST_REL = RECOVERY_PARENT_ROOT_REL + "/download_manifest.json"
RECOVERY_PARENT_PARTIAL_REL = (
    RECOVERY_PARENT_ROOT_REL + "/raw/EVT0001.dbn.zst.partial"
)

PLAN_SHA256 = "4F6BEDE4E8758F6F1CA54C5D496D09AA46E9ABF9C8AB15C3B3FEB07559B1A482"
OWNER_AUTHORITY_SHA256 = (
    "28D4C50F8F99F69F667FFAA808FA39B3853EF1A42103CE7AF4DFFC5A7B95D32A"
)
OWNER_VERBATIM_SHA256 = (
    "795322E75582F099B1C7861A43C44D3D8929FD3DFA729D07CD27ECD4BD15E80E"
)
SOURCE_QUOTE_PLAN_SHA256 = (
    "0167C4F62B1020865771520AE9895AC302129BE524783B4BDFC2E1B0052E650F"
)
QUOTE_RECEIPT_SHA256 = (
    "9C48C85CEC7766E83C387841CD0F8502C7CF70BEAB3F4537737DD73E4DC12C9D"
)
RUNTIME_RECEIPT_SHA256 = (
    "E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD"
)
RECOVERY_PARENT_PLAN_SHA256 = (
    "9FFC85B6B0C8EE4948119C2DE1049AFAE312DE075371208D3F1E0B8D8A240BC4"
)
RECOVERY_PARENT_MANIFEST_SHA256 = (
    "124DA202639066F47D75204CB85FA7AF4C8235A75E2C7DD28C890B1AA41C1619"
)
RECOVERY_PARENT_PARTIAL_SHA256 = (
    "186F843AE99C9202FF70059329303ACE33843C27619B2D84CD7187A801870F50"
)
RECOVERY_PARENT_PARTIAL_BYTES = 9090
RECOVERY_REQUEST_ID = "EVT0001"
RECOVERY_ESTIMATED_USD = 0.007167220116
RECOVERY_BILLABLE_BYTES = 274848

DATASET = "GLBX.MDP3"
SCHEMA = "trades"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
COST_MODE = "historical-streaming"
SDK_VERSION = "0.55.1"
OWNER_CEILING_USD = 1.0
EXPECTED_REQUESTS = 329
EXPECTED_NONZERO_QUOTE_REQUESTS = 327
WINDOW_SECONDS = 15
_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")
_ZSTD_MAGIC = bytes.fromhex("28B52FFD")

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
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def normalized_tool_base_sha256(payload: bytes) -> str:
    return sha256_bytes(payload)


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise AcquisitionError(f"{label} must stay on D:")
    return resolved


def read_user_environment(name: str) -> str | None:
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
    key = os.environ.get("DATABENTO_API_KEY") or read_user_environment(
        "DATABENTO_API_KEY"
    )
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


def validate_dbn_file_v3(path: Path, *, allow_zero: bool) -> int:
    if not path.is_file() or path.stat().st_size <= len(_ZSTD_MAGIC):
        raise AcquisitionError(f"DBN Zstandard file is missing or empty: {path}")
    with path.open("rb") as handle:
        if handle.read(len(_ZSTD_MAGIC)) != _ZSTD_MAGIC:
            raise AcquisitionError(f"DBN Zstandard signature mismatch: {path}")
    try:
        import databento as db

        if str(getattr(db, "__version__", "")) != SDK_VERSION:
            raise AcquisitionError("DBNv3 validator SDK version mismatch")
        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema_value = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        if (
            int(metadata.version) != 3
            or metadata.dataset != DATASET
            or schema_value != SCHEMA
        ):
            raise AcquisitionError("DBNv3 file metadata contract mismatch")
        records = sum(1 for _ in store)
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(
            f"DBNv3 full-stream validation failed for {path}: {exc}"
        ) from exc
    if records == 0 and not allow_zero:
        raise AcquisitionError(f"DBNv3 file has zero records: {path}")
    return records


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise AcquisitionError("source clock must be UTC-aware")
    return parsed.astimezone(timezone.utc)


def load_quote(path: Path) -> dict[str, Any]:
    if sha256_file(path) != QUOTE_RECEIPT_SHA256:
        raise AcquisitionError("free quote receipt drifted")
    quote = json.loads(path.read_text(encoding="ascii"))
    bindings = quote.get("bindings", {})
    if (
        quote.get("hypothesis_id") != PARENT_HYPOTHESIS_ID
        or quote.get("quote_id") != QUOTE_ID
        or quote.get("status")
        != "FREE_DESIGN_TRADES_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST"
        or quote.get("dataset") != DATASET
        or quote.get("schema") != SCHEMA
        or quote.get("symbol") != SYMBOL
        or quote.get("stype_in") != STYPE_IN
        or quote.get("cost_mode") != COST_MODE
        or quote.get("split") != "DESIGN_2019_2020"
        or quote.get("request_count") != EXPECTED_REQUESTS
        or quote.get("nonzero_billable_request_count")
        != EXPECTED_NONZERO_QUOTE_REQUESTS
        or quote.get("paid_request_made") is not False
        or quote.get("source_payload_read") is not False
        or quote.get("price_data_read") is not False
        or quote.get("validation_source_read") is not False
        or bindings.get("plan_sha256") != SOURCE_QUOTE_PLAN_SHA256
    ):
        raise AcquisitionError("free quote contract mismatch")
    windows = quote.get("quotes")
    if not isinstance(windows, list) or len(windows) != EXPECTED_REQUESTS:
        raise AcquisitionError("free quote request population mismatch")
    ids: list[str] = []
    total_cost = 0.0
    total_bytes = 0
    for window in windows:
        request_id = window.get("request_id")
        if (
            not isinstance(request_id, str)
            or window.get("event_clock_id") != request_id
            or window.get("split") != "DESIGN"
        ):
            raise AcquisitionError("free quote identity mismatch")
        start = parse_utc(str(window.get("start")))
        end = parse_utc(str(window.get("end")))
        if end - start != timedelta(seconds=WINDOW_SECONDS) or start.year not in {
            2019,
            2020,
        }:
            raise AcquisitionError("free quote window mismatch")
        cost = float(window.get("estimated_usd"))
        size = int(window.get("billable_bytes"))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError("free quote cost/size invalid")
        ids.append(request_id)
        total_cost += cost
        total_bytes += size
    if ids != sorted(ids) or len(set(ids)) != EXPECTED_REQUESTS:
        raise AcquisitionError("free quote identities are duplicate or unsorted")
    if not math.isclose(
        total_cost,
        float(quote.get("estimated_total_usd")),
        rel_tol=0,
        abs_tol=1e-12,
    ) or total_bytes != int(quote.get("estimated_total_billable_bytes")):
        raise AcquisitionError("free quote aggregate mismatch")
    return quote


def validate_owner_authority(path: Path) -> dict[str, Any]:
    if sha256_file(path) != OWNER_AUTHORITY_SHA256:
        raise AcquisitionError("Owner authority receipt drifted")
    authority = json.loads(path.read_text(encoding="utf-8"))
    verbatim = authority.get("owner_authorization_verbatim")
    if (
        not isinstance(verbatim, str)
        or sha256_bytes(verbatim.encode("utf-8")) != OWNER_VERBATIM_SHA256
        or authority.get("owner_authorization_verbatim_sha256")
        != OWNER_VERBATIM_SHA256
        or authority.get("hypothesis_id") != HYPOTHESIS_ID
        or authority.get("authorization_basis_quote_id") != QUOTE_ID
        or authority.get("authorization_basis_source_quote_plan_sha256")
        != SOURCE_QUOTE_PLAN_SHA256
        or authority.get("authorization_basis_quote_receipt_sha256")
        != QUOTE_RECEIPT_SHA256
        or authority.get("paid_acquisition_plan_sha256") != PLAN_SHA256
        or authority.get("approved_max_usd") != OWNER_CEILING_USD
        or authority.get("dataset") != DATASET
        or authority.get("schema") != SCHEMA
        or authority.get("symbol") != SYMBOL
        or authority.get("split") != "DESIGN_2019_2020"
        or authority.get("request_count") != EXPECTED_REQUESTS
        or authority.get("recovery_parent_hypothesis_id")
        != RECOVERY_PARENT_HYPOTHESIS_ID
        or authority.get("recovery_parent_live_plan_sha256")
        != RECOVERY_PARENT_PLAN_SHA256
        or authority.get("recovery_parent_manifest_sha256")
        != RECOVERY_PARENT_MANIFEST_SHA256
        or authority.get("recovery_parent_partial_sha256")
        != RECOVERY_PARENT_PARTIAL_SHA256
        or authority.get("recovery_runtime_receipt_sha256")
        != RUNTIME_RECEIPT_SHA256
        or authority.get("remote_retry_evt0001_authorized") is not False
        or authority.get("resume_remaining_nonzero_identities_authorized") is not True
        or authority.get("self_contained_dbnv3_validator_required") is not True
        or authority.get("legacy_foundation_import_authorized") is not False
    ):
        raise AcquisitionError("Owner authority scope mismatch")
    for key in (
        "validation_source_authorized",
        "outcome_prices_authorized",
        "economics_authorized",
        "mql5_authorized",
        "model0_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise AcquisitionError(f"forbidden Owner authority open: {key}")
    return authority


def validate_registry_authority(workspace: Path, tool_payload: bytes) -> dict[str, str]:
    registry = require_d(workspace / REGISTRY_REL, "registry")
    tool_base = normalized_tool_base_sha256(tool_payload)
    test_sha = sha256_file(require_d(workspace / TEST_REL, "focused tests"))
    matches: list[tuple[dict[str, Any], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((row, raw + b"\n"))
    if not matches:
        raise AcquisitionError("paid successor is absent from candidate registry")
    row, line = matches[-1]
    row_sha = sha256_bytes(line)
    validation = row.get("validation", {})
    expected = {
        "paid_acquisition_plan_sha256": PLAN_SHA256,
        "owner_authority_receipt_sha256": OWNER_AUTHORITY_SHA256,
        "quote_receipt_sha256": QUOTE_RECEIPT_SHA256,
        "reviewed_acquisition_tool_sha256": tool_base,
        "reviewed_acquisition_test_sha256": test_sha,
        "recovery_runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
        "recovery_parent_live_plan_sha256": RECOVERY_PARENT_PLAN_SHA256,
        "recovery_parent_manifest_sha256": RECOVERY_PARENT_MANIFEST_SHA256,
        "recovery_parent_partial_sha256": RECOVERY_PARENT_PARTIAL_SHA256,
    }
    if (
        row.get("state") != "probe"
        or row.get("prereg_sha256") != PLAN_SHA256
        or validation.get("paid_acquisition_authorized") is not True
        or validation.get("source_download_authorized") is not True
    ):
        raise AcquisitionError("registry paid-acquisition authority mismatch")
    for key, value in expected.items():
        if validation.get(key) != value:
            raise AcquisitionError(f"registry binding mismatch: {key}")
    for key in (
        "source_transform_authorized",
        "outcome_prices_authorized",
        "economics_authorized",
        "mql5_authorized",
        "model0_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if validation.get(key) is not False:
            raise AcquisitionError(f"forbidden registry authority open: {key}")
    return {
        "registry_row_sha256": row_sha,
        "tool_base_sha256": tool_base,
        "tool_file_sha256": sha256_bytes(tool_payload),
        "test_sha256": test_sha,
    }


def validate_authority(workspace: Path) -> dict[str, Any]:
    plan = require_d(workspace / PLAN_REL, "paid acquisition plan")
    owner = require_d(workspace / OWNER_REL, "Owner authority")
    tool = require_d(workspace / TOOL_REL, "acquisition tool")
    runtime_receipt = require_d(workspace / RUNTIME_RECEIPT_REL, "DBNv3 runtime receipt")
    if sha256_file(plan) != PLAN_SHA256:
        raise AcquisitionError("paid acquisition plan drifted")
    if sha256_file(runtime_receipt) != RUNTIME_RECEIPT_SHA256:
        raise AcquisitionError("DBNv3 runtime receipt drifted")
    owner_payload = validate_owner_authority(owner)
    registry = validate_registry_authority(workspace, tool.read_bytes())
    return {**registry, "owner_authority": owner_payload}


def request_args(window: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": window["start"],
        "end": window["end"],
    }


def live_quote_all(
    client_factory: Callable[[], Any],
    windows: list[dict[str, Any]],
    workers: int,
) -> list[dict[str, Any]]:
    if not 1 <= workers <= 16:
        raise AcquisitionError("quote workers must be 1..16")
    local = threading.local()

    def one(window: dict[str, Any]) -> dict[str, Any]:
        if not hasattr(local, "client"):
            local.client = client_factory()
        last: Exception | None = None
        for attempt in range(1, 4):
            try:
                args = request_args(window)
                cost = float(
                    local.client.metadata.get_cost(mode=COST_MODE, **args)
                )
                size = int(local.client.metadata.get_billable_size(**args))
                if not math.isfinite(cost) or cost < 0 or size < 0:
                    raise AcquisitionError("invalid live metadata quote")
                return {
                    "request_id": window["request_id"],
                    "event_clock_id": window["event_clock_id"],
                    "split": window["split"],
                    "event_time_utc": window["event_time_utc"],
                    "start": window["start"],
                    "end": window["end"],
                    "live_estimated_usd": cost,
                    "live_billable_bytes": size,
                    "metadata_attempt": attempt,
                }
            except Exception as exc:  # bounded free-metadata retry only
                last = exc
                if attempt < 3:
                    time_module.sleep((0.25, 1.0)[attempt - 1])
        raise AcquisitionError(
            f"live quote failed for {window['request_id']}: {type(last).__name__}"
        ) from None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        quoted = list(pool.map(one, windows))
    return sorted(quoted, key=lambda item: item["request_id"])


def validate_live_quote(
    live: list[dict[str, Any]], source_windows: list[dict[str, Any]]
) -> tuple[float, int]:
    if len(live) != EXPECTED_REQUESTS or len(source_windows) != EXPECTED_REQUESTS:
        raise AcquisitionError("live quote coverage mismatch")
    expected = {
        item["request_id"]: (
            item["event_clock_id"],
            item["split"],
            item["event_time_utc"],
            item["start"],
            item["end"],
        )
        for item in source_windows
    }
    ids: list[str] = []
    total_usd = 0.0
    total_bytes = 0
    for item in live:
        request_id = item.get("request_id")
        if request_id not in expected or (
            item.get("event_clock_id"),
            item.get("split"),
            item.get("event_time_utc"),
            item.get("start"),
            item.get("end"),
        ) != expected[request_id]:
            raise AcquisitionError("live quote identity/window drift")
        cost = float(item.get("live_estimated_usd"))
        size = int(item.get("live_billable_bytes"))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError("live quote cost/size invalid")
        ids.append(str(request_id))
        total_usd += cost
        total_bytes += size
    if ids != sorted(ids) or len(set(ids)) != EXPECTED_REQUESTS:
        raise AcquisitionError("live quote identities duplicate or unsorted")
    if not math.isfinite(total_usd) or total_usd > OWNER_CEILING_USD:
        raise AcquisitionError(
            f"live aggregate USD {total_usd:.12f} exceeds Owner ceiling "
            f"{OWNER_CEILING_USD:.2f}"
        )
    return total_usd, total_bytes


def load_recovery_parent(
    workspace: Path, quote: dict[str, Any]
) -> dict[str, Any]:
    plan_path = require_d(workspace / RECOVERY_PARENT_PLAN_REL, "parent live plan")
    manifest_path = require_d(
        workspace / RECOVERY_PARENT_MANIFEST_REL, "parent stopped manifest"
    )
    partial_path = require_d(
        workspace / RECOVERY_PARENT_PARTIAL_REL, "parent EVT0001 partial"
    )
    if sha256_file(plan_path) != RECOVERY_PARENT_PLAN_SHA256:
        raise AcquisitionError("parent live plan drifted")
    if sha256_file(manifest_path) != RECOVERY_PARENT_MANIFEST_SHA256:
        raise AcquisitionError("parent stopped manifest drifted")
    if (
        partial_path.stat().st_size != RECOVERY_PARENT_PARTIAL_BYTES
        or sha256_file(partial_path) != RECOVERY_PARENT_PARTIAL_SHA256
    ):
        raise AcquisitionError("parent EVT0001 partial drifted")
    plan = json.loads(plan_path.read_text(encoding="ascii"))
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    live = plan.get("windows")
    if not isinstance(live, list):
        raise AcquisitionError("parent live windows are absent")
    total_usd, total_bytes = validate_live_quote(live, list(quote["quotes"]))
    if (
        plan.get("hypothesis_id") != RECOVERY_PARENT_HYPOTHESIS_ID
        or plan.get("acquisition_id") != RECOVERY_PARENT_ACQUISITION_ID
        or plan.get("quote_id") != QUOTE_ID
        or plan.get("quote_receipt_sha256") != QUOTE_RECEIPT_SHA256
        or plan.get("request_count") != EXPECTED_REQUESTS
        or plan.get("owner_ceiling_usd") != OWNER_CEILING_USD
        or not math.isclose(
            total_usd,
            float(plan.get("live_estimated_total_usd")),
            rel_tol=0,
            abs_tol=1e-12,
        )
        or total_bytes != int(plan.get("live_estimated_total_bytes"))
        or manifest.get("hypothesis_id") != RECOVERY_PARENT_HYPOTHESIS_ID
        or manifest.get("acquisition_id") != RECOVERY_PARENT_ACQUISITION_ID
        or manifest.get("status") != "DOWNLOADING_SERIAL"
        or manifest.get("live_plan_sha256") != RECOVERY_PARENT_PLAN_SHA256
        or manifest.get("downloads") != []
        or manifest.get("source_empty_windows") != []
        or manifest.get("paid_timeseries_calls") != 0
        or manifest.get("outcome_fields_used") is not False
        or manifest.get("price_data_read") is not False
        or manifest.get("validation_source_read") is not False
    ):
        raise AcquisitionError("parent recovery contract mismatch")
    in_flight = manifest.get("in_flight")
    expected = {item["request_id"]: item for item in live}[RECOVERY_REQUEST_ID]
    if (
        not isinstance(in_flight, dict)
        or in_flight.get("request_id") != RECOVERY_REQUEST_ID
        or in_flight.get("event_clock_id") != expected["event_clock_id"]
        or in_flight.get("split") != expected["split"]
        or in_flight.get("start") != expected["start"]
        or in_flight.get("end") != expected["end"]
        or in_flight.get("filename") != filename(expected)
        or float(in_flight.get("estimated_cost_usd")) != RECOVERY_ESTIMATED_USD
        or int(in_flight.get("billable_bytes")) != RECOVERY_BILLABLE_BYTES
        or float(expected["live_estimated_usd"]) != RECOVERY_ESTIMATED_USD
        or int(expected["live_billable_bytes"]) != RECOVERY_BILLABLE_BYTES
    ):
        raise AcquisitionError("parent in-flight EVT0001 binding mismatch")
    return {
        "plan_path": plan_path,
        "manifest_path": manifest_path,
        "partial_path": partial_path,
        "live": live,
        "total_usd": total_usd,
        "total_bytes": total_bytes,
    }


def filename(item: dict[str, Any]) -> str:
    return f"{item['request_id']}.dbn.zst"


@contextmanager
def exclusive_campaign_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".paid_acquisition.lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise AcquisitionError("paid acquisition campaign is already locked") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()} utc={utc_now()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise AcquisitionError(f"stale temporary artifact: {temporary.name}")
    with temporary.open("xb") as handle:
        handle.write(canonical_json(payload) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def recover_parent_partial(
    *,
    parent: dict[str, Any],
    root: Path,
    manifest: dict[str, Any],
    live_by_id: dict[str, dict[str, Any]],
    manifest_path: Path,
) -> dict[str, Any]:
    if manifest.get("downloads") or manifest.get("paid_timeseries_calls") != 0:
        raise AcquisitionError("successor recovery must start from zero local downloads")
    source = Path(parent["partial_path"])
    live = live_by_id[RECOVERY_REQUEST_ID]
    records = validate_dbn_file_v3(source, allow_zero=False)
    raw = root / "raw"
    raw.mkdir(exist_ok=True)
    final = raw / filename(live)
    temporary = final.with_suffix(final.suffix + ".recovery")
    if final.exists() or temporary.exists():
        raise AcquisitionError("successor recovery output collision")
    shutil.copyfile(source, temporary)
    if (
        temporary.stat().st_size != RECOVERY_PARENT_PARTIAL_BYTES
        or sha256_file(temporary) != RECOVERY_PARENT_PARTIAL_SHA256
        or validate_dbn_file_v3(temporary, allow_zero=False) != records
    ):
        raise AcquisitionError("copied EVT0001 recovery verification failed")
    os.replace(temporary, final)
    item = {
        "request_id": RECOVERY_REQUEST_ID,
        "event_clock_id": live["event_clock_id"],
        "split": live["split"],
        "start": live["start"],
        "end": live["end"],
        "filename": filename(live),
        "started_at_utc": manifest["updated_at_utc"],
        "estimated_cost_usd": live["live_estimated_usd"],
        "billable_bytes": live["live_billable_bytes"],
        "bytes": final.stat().st_size,
        "sha256": sha256_file(final),
        "records": records,
        "source_empty": False,
        "recovered_in_flight": True,
        "inherited_parent_hypothesis_id": RECOVERY_PARENT_HYPOTHESIS_ID,
        "inherited_parent_partial_sha256": RECOVERY_PARENT_PARTIAL_SHA256,
        "remote_retry_made": False,
        "decoded_only_for_integrity": True,
    }
    manifest["downloads"].append(item)
    manifest["paid_timeseries_calls"] = 1
    manifest["inherited_parent_paid_timeseries_calls"] = 1
    manifest["successor_paid_timeseries_calls"] = 0
    manifest["recovered_parent_request_id"] = RECOVERY_REQUEST_ID
    manifest["recovered_parent_records"] = records
    manifest["source_payloads_decoded_for_integrity"] = 1
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    return item


def verify_completed(
    root: Path, manifest: dict[str, Any], live_by_id: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    for item in manifest.get("downloads", []):
        request_id = item.get("request_id")
        if request_id not in live_by_id or request_id in completed:
            raise AcquisitionError("download manifest identity mismatch")
        live = live_by_id[request_id]
        if (
            item.get("filename") != filename(live)
            or item.get("start") != live["start"]
            or item.get("end") != live["end"]
            or float(item.get("estimated_cost_usd"))
            != float(live["live_estimated_usd"])
            or int(item.get("billable_bytes"))
            != int(live["live_billable_bytes"])
        ):
            raise AcquisitionError("download manifest binding mismatch")
        path = root / "raw" / item["filename"]
        records = validate_dbn_file_v3(path, allow_zero=True)
        if (
            records != int(item.get("records"))
            or path.stat().st_size != int(item.get("bytes"))
            or sha256_file(path) != item.get("sha256")
        ):
            raise AcquisitionError("completed DBN verification failed")
        completed[str(request_id)] = item
    return completed


def validate_existing_campaign(
    plan: dict[str, Any],
    manifest: dict[str, Any],
    source_windows: list[dict[str, Any]],
    plan_file_sha256: str,
) -> list[dict[str, Any]]:
    expected = {
        "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID,
        "owner_ceiling_usd": OWNER_CEILING_USD,
        "quote_id": QUOTE_ID,
        "quote_receipt_sha256": QUOTE_RECEIPT_SHA256,
        "paid_acquisition_plan_sha256": PLAN_SHA256,
        "owner_authority_receipt_sha256": OWNER_AUTHORITY_SHA256,
        "registry_row_sha256": authority["registry_row_sha256"],
        "tool_base_sha256": authority["tool_base_sha256"],
        "test_sha256": authority["test_sha256"],
        "recovery_runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
        "recovery_parent_live_plan_sha256": RECOVERY_PARENT_PLAN_SHA256,
        "recovery_parent_manifest_sha256": RECOVERY_PARENT_MANIFEST_SHA256,
        "recovery_parent_partial_sha256": RECOVERY_PARENT_PARTIAL_SHA256,
    }
    for key, value in expected.items():
        if plan.get(key) != value:
            raise AcquisitionError(f"existing acquisition plan mismatch: {key}")
    live = plan.get("windows")
    if not isinstance(live, list) or len(live) != EXPECTED_REQUESTS:
        raise AcquisitionError("existing live quote population mismatch")
    total_usd, total_bytes = validate_live_quote(live, source_windows)
    if (
        not math.isclose(
            total_usd,
            float(plan.get("live_estimated_total_usd")),
            rel_tol=0,
            abs_tol=1e-12,
        )
        or total_bytes != int(plan.get("live_estimated_total_bytes"))
        or manifest.get("live_plan_sha256") != plan_file_sha256
        or manifest.get("hypothesis_id") != HYPOTHESIS_ID
        or manifest.get("acquisition_id") != ACQUISITION_ID
        or manifest.get("owner_ceiling_usd") != OWNER_CEILING_USD
        or manifest.get("outcome_fields_used") is not False
        or manifest.get("price_data_read") is not False
        or manifest.get("validation_source_read") is not False
    ):
        raise AcquisitionError("existing campaign contract mismatch")
    return live


def validate_source_empty_entries(
    entries: Any, live_by_id: dict[str, dict[str, Any]]
) -> set[str]:
    if not isinstance(entries, list):
        raise AcquisitionError("source-empty manifest population is invalid")
    identities: set[str] = set()
    for entry in entries:
        request_id = entry.get("request_id")
        live = live_by_id.get(request_id)
        if (
            live is None
            or request_id in identities
            or int(live["live_billable_bytes"]) != 0
            or entry.get("event_clock_id") != live["event_clock_id"]
            or entry.get("start") != live["start"]
            or entry.get("end") != live["end"]
            or int(entry.get("live_billable_bytes")) != 0
            or float(entry.get("live_estimated_usd"))
            != float(live["live_estimated_usd"])
            or entry.get("reason")
            != "LIVE_METADATA_ZERO_BILLABLE_BYTES_NO_TIMESERIES_CALL"
        ):
            raise AcquisitionError("source-empty manifest binding mismatch")
        identities.add(str(request_id))
    return identities


def acquisition_receipt(
    *,
    status: str,
    authority: dict[str, Any],
    plan_path: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "event_aggflow_006_paid_acquisition_receipt.v1",
        "generated_at_utc": utc_now(),
        "status": status,
        "hypothesis_id": HYPOTHESIS_ID,
        "acquisition_id": ACQUISITION_ID,
        "owner_authorization_verbatim_sha256": OWNER_VERBATIM_SHA256,
        "approved_max_usd": OWNER_CEILING_USD,
        "quote_id": QUOTE_ID,
        "quote_receipt_sha256": QUOTE_RECEIPT_SHA256,
        "paid_acquisition_plan_sha256": PLAN_SHA256,
        "owner_authority_receipt_sha256": OWNER_AUTHORITY_SHA256,
        "recovery_runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
        "recovery_parent_live_plan_sha256": RECOVERY_PARENT_PLAN_SHA256,
        "recovery_parent_manifest_sha256": RECOVERY_PARENT_MANIFEST_SHA256,
        "recovery_parent_partial_sha256": RECOVERY_PARENT_PARTIAL_SHA256,
        "registry_row_sha256": authority["registry_row_sha256"],
        "live_plan_sha256": sha256_file(plan_path),
        "download_manifest_sha256": sha256_file(manifest_path),
        "live_estimated_total_usd": manifest["live_estimated_total_usd"],
        "live_estimated_total_bytes": manifest["live_estimated_total_bytes"],
        "paid_timeseries_calls": manifest["paid_timeseries_calls"],
        "inherited_parent_paid_timeseries_calls": manifest.get(
            "inherited_parent_paid_timeseries_calls", 0
        ),
        "successor_paid_timeseries_calls": manifest.get(
            "successor_paid_timeseries_calls", 0
        ),
        "coverage_count": len(manifest.get("downloads", []))
        + len(manifest.get("source_empty_windows", [])),
        "outcome_fields_used": False,
        "price_data_read": False,
        "validation_source_read": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "model0_authorized": False,
    }


def execute(workspace: Path, workers: int) -> Path:
    workspace = require_d(workspace, "workspace")
    runtime = require_d(workspace / RUNTIME_REL, "Databento runtime")
    if Path(sys.executable).resolve() != runtime:
        raise AcquisitionError("wrong Python runtime")
    if importlib.metadata.version("databento") != SDK_VERSION:
        raise AcquisitionError("Databento SDK version mismatch")

    authority = validate_authority(workspace)
    quote = load_quote(require_d(workspace / QUOTE_REL, "free quote receipt"))
    parent = load_recovery_parent(workspace, quote)
    key = load_api_key()
    root = require_d(workspace / OUTPUT_REL, "paid output root")
    expected_root = (workspace / OUTPUT_REL).resolve()
    if root != expected_root:
        raise AcquisitionError("paid output root drift")

    plan_path = root / "acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    receipt_path = root / "paid_acquisition_receipt.json"
    new_campaign = False
    with exclusive_campaign_lock(root):
        if plan_path.exists() or manifest_path.exists():
            if not plan_path.is_file() or not manifest_path.is_file():
                raise AcquisitionError("incomplete existing campaign artifacts")
            plan = json.loads(plan_path.read_text(encoding="ascii"))
            manifest = json.loads(manifest_path.read_text(encoding="ascii"))
            live = validate_existing_campaign(
                plan,
                manifest,
                authority,
                list(quote["quotes"]),
                sha256_file(plan_path),
            )
        else:
            source_windows = list(quote["quotes"])
            live = list(parent["live"])
            total_usd, total_bytes = validate_live_quote(live, source_windows)
            plan = {
                "schema_version": "event_aggflow_006_dbnv3_recovery_plan.v1",
                "created_at_utc": utc_now(),
                "hypothesis_id": HYPOTHESIS_ID,
                "acquisition_id": ACQUISITION_ID,
                "dataset": DATASET,
                "schema": SCHEMA,
                "symbol": SYMBOL,
                "stype_in": STYPE_IN,
                "stype_out": STYPE_OUT,
                "cost_mode": COST_MODE,
                "request_window": "[event_time_utc,event_time_utc+15s)",
                "split": "DESIGN_2019_2020",
                "request_count": EXPECTED_REQUESTS,
                "owner_ceiling_usd": OWNER_CEILING_USD,
                "live_estimated_total_usd": total_usd,
                "live_estimated_total_bytes": total_bytes,
                "quote_id": QUOTE_ID,
                "quote_receipt_sha256": QUOTE_RECEIPT_SHA256,
                "paid_acquisition_plan_sha256": PLAN_SHA256,
                "owner_authority_receipt_sha256": OWNER_AUTHORITY_SHA256,
                "registry_row_sha256": authority["registry_row_sha256"],
                "tool_base_sha256": authority["tool_base_sha256"],
                "tool_file_sha256": authority["tool_file_sha256"],
                "test_sha256": authority["test_sha256"],
                "recovery_runtime_receipt_sha256": RUNTIME_RECEIPT_SHA256,
                "recovery_parent_live_plan_sha256": RECOVERY_PARENT_PLAN_SHA256,
                "recovery_parent_manifest_sha256": RECOVERY_PARENT_MANIFEST_SHA256,
                "recovery_parent_partial_sha256": RECOVERY_PARENT_PARTIAL_SHA256,
                "recovery_parent_partial_bytes": RECOVERY_PARENT_PARTIAL_BYTES,
                "recovery_parent_request_id": RECOVERY_REQUEST_ID,
                "remote_retry_evt0001_authorized": False,
                "fresh_live_requote_made": False,
                "paid_calls_serial_only": True,
                "source_transform_authorized": False,
                "outcome_prices_authorized": False,
                "validation_source_authorized": False,
                "windows": live,
            }
            root.mkdir(parents=True, exist_ok=True)
            write_json_atomic(plan_path, plan)
            live_plan_sha256 = sha256_file(plan_path)
            manifest = {
                "schema_version": "event_aggflow_006_dbnv3_recovery_manifest.v1",
                "status": "PARENT_EVT0001_LOCAL_RECOVERY_PENDING",
                "updated_at_utc": utc_now(),
                "hypothesis_id": HYPOTHESIS_ID,
                "acquisition_id": ACQUISITION_ID,
                "owner_ceiling_usd": OWNER_CEILING_USD,
                "live_estimated_total_usd": total_usd,
                "live_estimated_total_bytes": total_bytes,
                "live_plan_sha256": live_plan_sha256,
                "downloads": [],
                "source_empty_windows": [],
                "in_flight": None,
                "paid_timeseries_calls": 0,
                "inherited_parent_paid_timeseries_calls": 0,
                "successor_paid_timeseries_calls": 0,
                "source_payloads_decoded_for_integrity": 0,
                "outcome_fields_used": False,
                "price_data_read": False,
                "validation_source_read": False,
            }
            write_json_atomic(manifest_path, manifest)
            new_campaign = True

        live_by_id = {item["request_id"]: item for item in live}
        if new_campaign:
            recover_parent_partial(
                parent=parent,
                root=root,
                manifest=manifest,
                live_by_id=live_by_id,
                manifest_path=manifest_path,
            )
        completed = verify_completed(root, manifest, live_by_id)
        recovered = completed.get(RECOVERY_REQUEST_ID)
        if (
            recovered is None
            or recovered.get("inherited_parent_hypothesis_id")
            != RECOVERY_PARENT_HYPOTHESIS_ID
            or recovered.get("inherited_parent_partial_sha256")
            != RECOVERY_PARENT_PARTIAL_SHA256
            or recovered.get("remote_retry_made") is not False
            or recovered.get("decoded_only_for_integrity") is not True
            or recovered.get("sha256") != RECOVERY_PARENT_PARTIAL_SHA256
            or int(recovered.get("bytes")) != RECOVERY_PARENT_PARTIAL_BYTES
        ):
            raise AcquisitionError("EVT0001 recovery provenance mismatch")
        empty_ids = validate_source_empty_entries(
            manifest.get("source_empty_windows", []), live_by_id
        )
        if completed.keys() & empty_ids:
            raise AcquisitionError("identity is both downloaded and source-empty")

        in_flight = manifest.get("in_flight")
        if in_flight:
            request_id = in_flight.get("request_id")
            live_in_flight = live_by_id.get(request_id)
            if (
                live_in_flight is None
                or request_id in completed
                or in_flight.get("event_clock_id")
                != live_in_flight["event_clock_id"]
                or in_flight.get("split") != live_in_flight["split"]
                or in_flight.get("start") != live_in_flight["start"]
                or in_flight.get("end") != live_in_flight["end"]
                or in_flight.get("filename") != filename(live_in_flight)
                or float(in_flight.get("estimated_cost_usd"))
                != float(live_in_flight["live_estimated_usd"])
                or int(in_flight.get("billable_bytes"))
                != int(live_in_flight["live_billable_bytes"])
            ):
                raise AcquisitionError("in-flight identity mismatch")
            final = root / "raw" / filename(live_in_flight)
            partial = final.with_suffix(final.suffix + ".partial")
            candidate = final if final.exists() else partial if partial.exists() else None
            if candidate is None:
                raise AcquisitionError(
                    "unresolved paid identity has no recoverable file; automatic retry forbidden"
                )
            records = validate_dbn_file_v3(candidate, allow_zero=True)
            if candidate == partial:
                os.replace(partial, final)
            item = {
                **in_flight,
                "bytes": final.stat().st_size,
                "sha256": sha256_file(final),
                "records": records,
                "source_empty": records == 0,
                "recovered_in_flight": True,
            }
            manifest["downloads"].append(item)
            manifest["in_flight"] = None
            manifest["paid_timeseries_calls"] = len(manifest["downloads"])
            manifest["successor_paid_timeseries_calls"] = max(
                0, len(manifest["downloads"]) - 1
            )
            manifest["updated_at_utc"] = utc_now()
            write_json_atomic(manifest_path, manifest)
            completed[request_id] = item

        raw = root / "raw"
        raw.mkdir(exist_ok=True)
        if RECOVERY_REQUEST_ID not in completed:
            raise AcquisitionError("EVT0001 must be locally recovered before remote resume")
        paid_client = make_client(key)
        for item in live:
            request_id = item["request_id"]
            if request_id in completed or request_id in empty_ids:
                continue
            if int(item["live_billable_bytes"]) == 0:
                manifest["source_empty_windows"].append(
                    {
                        "request_id": request_id,
                        "event_clock_id": item["event_clock_id"],
                        "start": item["start"],
                        "end": item["end"],
                        "live_estimated_usd": item["live_estimated_usd"],
                        "live_billable_bytes": 0,
                        "reason": "LIVE_METADATA_ZERO_BILLABLE_BYTES_NO_TIMESERIES_CALL",
                    }
                )
                empty_ids.add(request_id)
                manifest["updated_at_utc"] = utc_now()
                write_json_atomic(manifest_path, manifest)
                continue

            if float(plan["live_estimated_total_usd"]) > OWNER_CEILING_USD:
                raise AcquisitionError("aggregate ceiling drift before paid request")
            final = raw / filename(item)
            partial = final.with_suffix(final.suffix + ".partial")
            if final.exists() or partial.exists():
                raise AcquisitionError("unmanifested paid output collision")
            in_flight = {
                "request_id": request_id,
                "event_clock_id": item["event_clock_id"],
                "split": item["split"],
                "start": item["start"],
                "end": item["end"],
                "filename": filename(item),
                "started_at_utc": utc_now(),
                "estimated_cost_usd": item["live_estimated_usd"],
                "billable_bytes": item["live_billable_bytes"],
            }
            manifest["status"] = "DOWNLOADING_SERIAL"
            manifest["in_flight"] = in_flight
            manifest["updated_at_utc"] = utc_now()
            write_json_atomic(manifest_path, manifest)
            try:
                paid_client.timeseries.get_range(
                    **request_args(item), stype_out=STYPE_OUT, path=partial
                )
            except Exception as exc:
                raise AcquisitionError(
                    f"paid request failed for {request_id}: {type(exc).__name__}"
                ) from exc
            records = validate_dbn_file_v3(partial, allow_zero=True)
            os.replace(partial, final)
            downloaded = {
                **in_flight,
                "bytes": final.stat().st_size,
                "sha256": sha256_file(final),
                "records": records,
                "source_empty": records == 0,
                "recovered_in_flight": False,
            }
            manifest["downloads"].append(downloaded)
            manifest["in_flight"] = None
            manifest["paid_timeseries_calls"] = len(manifest["downloads"])
            manifest["successor_paid_timeseries_calls"] = max(
                0, len(manifest["downloads"]) - 1
            )
            manifest["updated_at_utc"] = utc_now()
            write_json_atomic(manifest_path, manifest)
            completed[request_id] = downloaded

        coverage = len(completed) + len(empty_ids)
        if coverage != EXPECTED_REQUESTS:
            raise AcquisitionError(f"source coverage incomplete: {coverage}/{EXPECTED_REQUESTS}")
        manifest["status"] = "DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED"
        manifest["updated_at_utc"] = utc_now()
        manifest["paid_timeseries_calls"] = len(manifest["downloads"])
        manifest["successor_paid_timeseries_calls"] = max(
            0, len(manifest["downloads"]) - 1
        )
        manifest["coverage_count"] = coverage
        manifest["downloaded_bytes"] = sum(
            int(item["bytes"]) for item in manifest["downloads"]
        )
        manifest["records"] = sum(
            int(item["records"]) for item in manifest["downloads"]
        )
        write_json_atomic(manifest_path, manifest)
        receipt = acquisition_receipt(
            status="COMPLETE_RAW_SOURCE_QUALITY_REQUIRED",
            authority=authority,
            plan_path=plan_path,
            manifest_path=manifest_path,
            manifest=manifest,
        )
        write_json_atomic(receipt_path, receipt)
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--quote-workers", type=int, default=16)
    args = parser.parse_args()
    try:
        manifest_path = execute(args.workspace.resolve(), args.quote_workers)
        manifest = json.loads(manifest_path.read_text(encoding="ascii"))
        print(
            "EVENTAGGFLOW006_TRADES_ACQUIRE_OK "
            f"status={manifest['status']} "
            f"coverage={manifest['coverage_count']}/{EXPECTED_REQUESTS} "
            f"paid_calls={manifest['paid_timeseries_calls']} "
            f"estimated_usd={manifest['live_estimated_total_usd']:.12f} "
            f"bytes={manifest['downloaded_bytes']} records={manifest['records']}"
        )
        print(f"MANIFEST {manifest_path}")
        return 0
    except AcquisitionError as exc:
        print(
            f"EVENTAGGFLOW006_TRADES_ACQUIRE_BLOCKED reason={exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
