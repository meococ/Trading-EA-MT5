#!/usr/bin/env python3
"""One-shot raw-ID definition/status recovery for GC OFI source pilot."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterator


HYPOTHESIS_ID = "HYP-GC-OFI-INNOV-XAU-M5-002"
ACQUISITION_ID = "GCOFI002-Q1-2019-REF-SOURCE-001"
DATASET = "GLBX.MDP3"
SYMBOLS = ("32257", "14651", "142620")
INSTRUMENT_IDS = frozenset(int(value) for value in SYMBOLS)
STYPE_IN = "instrument_id"
STYPE_OUT = "instrument_id"
START = "2019-01-01T00:00:00.000Z"
END = "2019-04-01T00:00:00.000Z"
SCHEMAS = ("definition", "status")
COST_MODE = "historical-streaming"
SDK_VERSION = "0.55.1"
OWNER_LIMIT_USD_EXCLUSIVE = 10.0
EXPECTED_QUOTE_USD = 0.000400014222
EXPECTED_QUOTE_BYTES = 172_560
EXPECTED_TBBO_RECORDS = 4_292_841

BASE_REL = "03. EA Developer/EA_GCOrderFlowInnovation/research/"
SOURCE_PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_RECOVERY_PLAN.md"
PAID_PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_PAID_RECOVERY_PLAN.md"
OWNER_REL = BASE_REL + HYPOTHESIS_ID + "_OWNER_AUTHORITY.json"
TOOL_REL = BASE_REL + "acquire_gc_order_flow_innovation_002.py"
TEST_REL = BASE_REL + "tests/test_acquire_gc_order_flow_innovation_002.py"
PARENT_CLOSEOUT_REL = BASE_REL + "HYP-GC-OFI-INNOV-XAU-M5-001_ACQUISITION_ENGINEERING_CLOSEOUT.md"
PARENT_TBBO_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-001/GCOFI001-Q1-2019-SOURCE-PILOT-001/"
    "raw/tbbo.dbn.zst"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
QUOTE_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}/metadata_quote_receipt.json"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}"
)
RUNTIME_REL = (
    "03. EA Developer/EA_EventAggressorFlow/research/"
    "HYP-EVENT-AGGFLOW-EURUSD-TICK-005_DBV3_RUNTIME_RECEIPT.json"
)
MECHANISM_REL = "04. Memory/research/20260811_GC_SIGNED_FLOW_MECHANISM_SCREEN.md"
ESTIMATOR_REL = "04. Memory/research/gc_signed_flow_estimator_reference.py"
ESTIMATOR_TEST_REL = "04. Memory/research/tests/test_gc_signed_flow_estimator_reference.py"

SOURCE_PLAN_SHA256 = "2A769D9A36CD0EAB10F6B64D1020514CA3D02F0F0E8BA03C1CD85A94A45273DD"
PAID_PLAN_SHA256 = "1EE88F90F87D3FB38E5BC2E135809E2793713C7DCFCBB46FF37052B858478404"
QUOTE_SHA256 = "7422D510B2A483EC16C5E35776020E2175CC7438CE754964FFF5AE95DADCD9EB"
OWNER_SHA256 = "0AF2FB1A75B75DAFBCB01880785E3C9AEF840FE7E6521F4AEC639483FB2C3681"
RUNTIME_SHA256 = "E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD"
PARENT_CLOSEOUT_SHA256 = "032E2910FB9291F71DC730E32BE964DD36D04161FA72861ABEC3B52A734B11F1"
PARENT_TBBO_SHA256 = "6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB"
OWNER_VERBATIM_SHA256 = "6EC4AF3294B028D276DE20E44A35D79993D07D0BC462E566E0057F29A234BBBA"

_KEY_RE = re.compile(r"^db-[A-Za-z0-9_-]{20,}$")
_ZSTD_MAGIC = bytes.fromhex("28B52FFD")


class AcquisitionError(RuntimeError):
    pass


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value) + b"\n")
    os.replace(temporary, path)


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise AcquisitionError(f"missing {label}: {path}")
    return path


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
    key = os.environ.get("DATABENTO_API_KEY") or read_user_environment("DATABENTO_API_KEY")
    if not key:
        raise AcquisitionError("DATABENTO_API_KEY is absent")
    key = key.strip()
    if not _KEY_RE.fullmatch(key):
        raise AcquisitionError("DATABENTO_API_KEY has unexpected format")
    return key


def make_client(key: str) -> Any:
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError("Databento SDK unavailable") from exc
    if str(getattr(db, "__version__", "")) != SDK_VERSION:
        raise AcquisitionError("Databento SDK version mismatch")
    return db.Historical(key)


def request_args(schema: str) -> dict[str, object]:
    if schema not in SCHEMAS:
        raise AcquisitionError(f"schema outside frozen allowlist: {schema}")
    return {
        "dataset": DATASET,
        "schema": schema,
        "symbols": list(SYMBOLS),
        "stype_in": STYPE_IN,
        "start": START,
        "end": END,
    }


def load_bound_quote(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="ascii"))
    if (
        receipt.get("hypothesis_id") != HYPOTHESIS_ID
        or receipt.get("quote_id") != ACQUISITION_ID
        or receipt.get("dataset") != DATASET
        or receipt.get("symbols") != list(SYMBOLS)
        or receipt.get("schemas", list(SCHEMAS)) != list(SCHEMAS)
        or receipt.get("stype_in") != STYPE_IN
        or receipt.get("start") != START
        or receipt.get("end") != END
        or receipt.get("paid_request_made") is not False
        or receipt.get("tbbo_remote_retry_made") is not False
        or receipt.get("inherited_tbbo_sha256") != PARENT_TBBO_SHA256
        or not math.isclose(float(receipt.get("estimated_total_usd", -1)), EXPECTED_QUOTE_USD, abs_tol=1e-15)
        or int(receipt.get("estimated_total_billable_bytes", -1)) != EXPECTED_QUOTE_BYTES
    ):
        raise AcquisitionError("bound quote contract mismatch")
    if [item.get("schema") for item in receipt.get("quotes", [])] != list(SCHEMAS):
        raise AcquisitionError("bound quote schema mismatch")
    return receipt


def validate_owner(path: Path) -> None:
    if sha256_file(path) != OWNER_SHA256:
        raise AcquisitionError("owner receipt hash mismatch")
    owner = json.loads(path.read_text(encoding="utf-8"))
    verbatim = owner.get("owner_authorization_verbatim", "")
    if (
        sha256_bytes(verbatim.encode("utf-8")) != OWNER_VERBATIM_SHA256
        or owner.get("hypothesis_id") != HYPOTHESIS_ID
        or owner.get("acquisition_id") != ACQUISITION_ID
        or owner.get("owner_limit_usd_exclusive") != OWNER_LIMIT_USD_EXCLUSIVE
        or owner.get("paid_timeseries_calls_authorized") != len(SCHEMAS)
        or owner.get("tbbo_remote_call_authorized") is not False
        or owner.get("same_id_remote_retry_authorized") is not False
        or owner.get("source_recovery_plan_sha256") != SOURCE_PLAN_SHA256
        or owner.get("metadata_quote_receipt_sha256") != QUOTE_SHA256
        or owner.get("paid_recovery_plan_sha256") != PAID_PLAN_SHA256
        or owner.get("runtime_receipt_sha256") != RUNTIME_SHA256
        or owner.get("inherited_tbbo_sha256") != PARENT_TBBO_SHA256
    ):
        raise AcquisitionError("owner authority mismatch")
    for field in (
        "subscription_authorized", "auto_renewal_authorized", "source_transform_authorized",
        "xauusd_outcome_authorized", "economics_authorized", "mql5_authorized",
        "mt5_authorized", "optimization_authorized", "validation_authorized",
        "paper_trading_authorized", "live_trading_authorized", "market_edge_claim_authorized",
    ):
        if owner.get(field) is not False:
            raise AcquisitionError(f"forbidden owner authority open: {field}")


def validate_registry(workspace: Path) -> dict[str, str]:
    registry = require_file(workspace / REGISTRY_REL, "candidate registry")
    matches: list[tuple[dict[str, Any], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((row, raw + b"\n"))
    if not matches:
        raise AcquisitionError("hypothesis absent from candidate registry")
    row, row_bytes = matches[-1]
    validation = row.get("validation", {})
    bound = {
        "source_recovery_plan_sha256": sha256_file(workspace / SOURCE_PLAN_REL),
        "metadata_quote_receipt_sha256": sha256_file(workspace / QUOTE_REL),
        "paid_recovery_plan_sha256": sha256_file(workspace / PAID_PLAN_REL),
        "owner_authority_receipt_sha256": sha256_file(workspace / OWNER_REL),
        "reviewed_acquisition_tool_sha256": sha256_file(workspace / TOOL_REL),
        "reviewed_acquisition_test_sha256": sha256_file(workspace / TEST_REL),
        "runtime_receipt_sha256": sha256_file(workspace / RUNTIME_REL),
        "parent_closeout_sha256": sha256_file(workspace / PARENT_CLOSEOUT_REL),
        "inherited_tbbo_sha256": sha256_file(workspace / PARENT_TBBO_REL),
        "mechanism_screen_sha256": sha256_file(workspace / MECHANISM_REL),
        "estimator_sha256": sha256_file(workspace / ESTIMATOR_REL),
        "estimator_test_sha256": sha256_file(workspace / ESTIMATOR_TEST_REL),
    }
    if (
        row.get("state") != "probe"
        or row.get("verdict") != "AUTHORIZE_ONE_SHOT_RAW_ID_REFERENCE_RECOVERY_UNDER_USD10"
        or row.get("prereg_sha256") != PAID_PLAN_SHA256
        or validation.get("paid_source_acquisition_authorized") is not True
        or validation.get("paid_timeseries_calls_authorized") != len(SCHEMAS)
        or validation.get("tbbo_remote_call_authorized") is not False
        or validation.get("same_id_remote_retry_authorized") is not False
    ):
        raise AcquisitionError("registry acquisition authority mismatch")
    for key, actual in bound.items():
        if validation.get(key) != actual:
            raise AcquisitionError(f"registry binding mismatch: {key}")
    for field in (
        "source_transform_authorized", "xauusd_outcome_authorized", "economics_authorized",
        "mql5_authorized", "mt5_authorized", "optimization_authorized",
        "research_validation_access_authorized", "research_holdout_access_authorized",
        "paper_trading_authorized", "live_trading_authorized", "market_edge_claim_authorized",
    ):
        if validation.get(field) is not False:
            raise AcquisitionError(f"forbidden registry authority open: {field}")
    return {**bound, "registry_row_sha256": sha256_bytes(row_bytes)}


def validate_dbn_file(path: Path, expected_schema: str, expected_records: int | None = None) -> tuple[int, set[int]]:
    if not path.is_file() or path.stat().st_size <= len(_ZSTD_MAGIC):
        raise AcquisitionError(f"missing/empty DBN payload: {expected_schema}")
    with path.open("rb") as handle:
        if handle.read(len(_ZSTD_MAGIC)) != _ZSTD_MAGIC:
            raise AcquisitionError(f"DBN Zstandard signature mismatch: {expected_schema}")
    try:
        import databento as db

        if str(getattr(db, "__version__", "")) != SDK_VERSION:
            raise AcquisitionError("DBNv3 validator SDK mismatch")
        store = db.DBNStore.from_file(path)
        metadata = store.metadata
        schema = getattr(metadata.schema, "value", str(metadata.schema)).lower()
        if int(metadata.version) != 3 or metadata.dataset != DATASET or schema != expected_schema:
            raise AcquisitionError(f"DBNv3 metadata mismatch: {expected_schema}")
        records = 0
        instruments: set[int] = set()
        for record in store:
            records += 1
            instruments.add(int(record.instrument_id))
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(f"DBNv3 full-stream validation failed for {expected_schema}: {exc}") from exc
    if records <= 0 or (expected_records is not None and records != expected_records):
        raise AcquisitionError(f"record-count mismatch: {expected_schema}")
    if not instruments or not instruments.issubset(INSTRUMENT_IDS):
        raise AcquisitionError(f"instrument identity mismatch: {expected_schema}")
    return records, instruments


def validate_authority(workspace: Path) -> dict[str, str]:
    checks = {
        SOURCE_PLAN_REL: SOURCE_PLAN_SHA256, PAID_PLAN_REL: PAID_PLAN_SHA256,
        QUOTE_REL: QUOTE_SHA256, OWNER_REL: OWNER_SHA256, RUNTIME_REL: RUNTIME_SHA256,
        PARENT_CLOSEOUT_REL: PARENT_CLOSEOUT_SHA256, PARENT_TBBO_REL: PARENT_TBBO_SHA256,
    }
    for relative, expected in checks.items():
        path = require_file(workspace / relative, relative)
        if sha256_file(path) != expected:
            raise AcquisitionError(f"bound artifact drifted: {relative}")
    load_bound_quote(workspace / QUOTE_REL)
    validate_owner(workspace / OWNER_REL)
    validate_dbn_file(workspace / PARENT_TBBO_REL, "tbbo", EXPECTED_TBBO_RECORDS)
    return validate_registry(workspace)


def live_requote(client: Any) -> tuple[list[dict[str, Any]], float, int]:
    quotes: list[dict[str, Any]] = []
    for schema in SCHEMAS:
        args = request_args(schema)
        cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
        size = int(client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0.0 or size <= 0:
            raise AcquisitionError(f"invalid fresh quote for {schema}")
        quotes.append({"schema": schema, "estimated_usd": cost, "billable_bytes": size, "request": args})
    total_cost = sum(float(item["estimated_usd"]) for item in quotes)
    total_bytes = sum(int(item["billable_bytes"]) for item in quotes)
    if not total_cost < OWNER_LIMIT_USD_EXCLUSIVE:
        raise AcquisitionError(f"fresh aggregate estimate {total_cost:.12f} is not strictly below USD 10")
    return quotes, total_cost, total_bytes


@contextmanager
def exclusive_lock(root: Path) -> Iterator[None]:
    lock = root / ".paid_acquisition.lock"
    root.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise AcquisitionError("paid acquisition is already locked") from exc
    try:
        os.write(descriptor, f"pid={os.getpid()} utc={utc_now()}\n".encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def download_one(*, client: Any, schema: str, quote: dict[str, Any], root: Path, manifest: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    final = raw / f"{schema}.dbn.zst"
    partial = final.with_suffix(final.suffix + ".partial")
    if final.exists() or partial.exists():
        raise AcquisitionError(f"unmanifested output collision: {schema}")
    in_flight = {
        "schema": schema, "filename": final.name, "start": START, "end": END,
        "symbols": list(SYMBOLS), "estimated_usd": float(quote["estimated_usd"]),
        "billable_bytes": int(quote["billable_bytes"]), "started_at_utc": utc_now(),
    }
    manifest["status"] = "DOWNLOADING_SERIAL"
    manifest["in_flight"] = in_flight
    manifest["paid_timeseries_attempts"] += 1
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    try:
        client.timeseries.get_range(**request_args(schema), stype_out=STYPE_OUT, path=partial)
    except Exception as exc:
        raise AcquisitionError(f"paid request failed for {schema}: {type(exc).__name__}") from exc
    records, instruments = validate_dbn_file(partial, schema)
    os.replace(partial, final)
    downloaded = {
        **in_flight, "bytes": final.stat().st_size, "sha256": sha256_file(final),
        "records": records, "instrument_ids": sorted(instruments), "dbn_version": 3,
        "dataset": DATASET, "completed_at_utc": utc_now(),
    }
    manifest["downloads"].append(downloaded)
    manifest["in_flight"] = None
    manifest["paid_timeseries_calls"] = len(manifest["downloads"])
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    return downloaded


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise AcquisitionError("workspace must stay on D:")
    authority = validate_authority(workspace)
    root = workspace / OUTPUT_REL
    if not root.is_dir():
        raise AcquisitionError("quote output root missing")
    plan_path = root / "acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    receipt_path = root / "paid_acquisition_receipt.json"
    if plan_path.exists() or manifest_path.exists() or receipt_path.exists():
        raise AcquisitionError("same-ID acquisition state already exists; remote retry is forbidden")
    with exclusive_lock(root):
        client = make_client(load_api_key())
        quotes, total_cost, total_bytes = live_requote(client)
        plan = {
            "schema_version": "gc_order_flow_innovation_recovery_plan.v2",
            "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
            "acquisition_id": ACQUISITION_ID, "dataset": DATASET,
            "symbols": list(SYMBOLS), "schemas": list(SCHEMAS),
            "stype_in": STYPE_IN, "stype_out": STYPE_OUT, "start": START, "end": END,
            "owner_limit_usd_exclusive": OWNER_LIMIT_USD_EXCLUSIVE,
            "fresh_estimated_total_usd": total_cost,
            "fresh_estimated_total_billable_bytes": total_bytes, "quotes": quotes,
            "inherited_tbbo_sha256": PARENT_TBBO_SHA256, "tbbo_remote_call_authorized": False,
            "same_id_remote_retry_authorized": False, "bindings": authority,
            "source_transform_authorized": False, "xauusd_outcome_authorized": False,
            "economics_authorized": False, "mql5_authorized": False, "mt5_authorized": False,
        }
        write_json_atomic(plan_path, plan)
        manifest = {
            "schema_version": "gc_order_flow_innovation_recovery_manifest.v2",
            "status": "LIVE_QUOTED_NOT_DOWNLOADED", "created_at_utc": utc_now(),
            "updated_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
            "acquisition_id": ACQUISITION_ID, "acquisition_plan_sha256": sha256_file(plan_path),
            "owner_limit_usd_exclusive": OWNER_LIMIT_USD_EXCLUSIVE,
            "fresh_estimated_total_usd": total_cost, "fresh_estimated_total_billable_bytes": total_bytes,
            "inherited_tbbo_sha256": PARENT_TBBO_SHA256, "tbbo_remote_calls": 0,
            "downloads": [], "in_flight": None, "paid_timeseries_calls": 0,
            "paid_timeseries_attempts": 0, "source_transform_used": False,
            "xauusd_outcome_read": False, "economics_executed": False,
        }
        write_json_atomic(manifest_path, manifest)
        by_schema = {item["schema"]: item for item in quotes}
        for schema in SCHEMAS:
            download_one(client=client, schema=schema, quote=by_schema[schema], root=root, manifest=manifest, manifest_path=manifest_path)
        if manifest["paid_timeseries_calls"] != len(SCHEMAS) or manifest["tbbo_remote_calls"] != 0:
            raise AcquisitionError("paid call coverage mismatch")
        manifest["status"] = "COMPLETE_RAW_SOURCE_QUALITY_REQUIRED"
        manifest["updated_at_utc"] = utc_now()
        manifest["downloaded_bytes"] = sum(int(item["bytes"]) for item in manifest["downloads"])
        manifest["records"] = sum(int(item["records"]) for item in manifest["downloads"])
        write_json_atomic(manifest_path, manifest)
        receipt = {
            "schema_version": "gc_order_flow_innovation_paid_recovery_receipt.v2",
            "created_at_utc": utc_now(), "status": "COMPLETE_RAW_SOURCE_QUALITY_REQUIRED",
            "hypothesis_id": HYPOTHESIS_ID, "acquisition_id": ACQUISITION_ID,
            "fresh_estimated_total_usd": total_cost, "fresh_estimated_total_billable_bytes": total_bytes,
            "paid_timeseries_calls": len(SCHEMAS), "paid_timeseries_attempts": len(SCHEMAS),
            "tbbo_remote_calls": 0, "inherited_tbbo_sha256": PARENT_TBBO_SHA256,
            "acquisition_plan_sha256": sha256_file(plan_path),
            "download_manifest_sha256": sha256_file(manifest_path), "downloads": manifest["downloads"],
            "bindings": authority, "source_quality_verdict": "PENDING",
            "source_transform_authorized": False, "xauusd_outcome_read": False,
            "economics_executed": False, "mql5_authorized": False, "mt5_authorized": False,
            "paper_trading_authorized": False, "live_trading_authorized": False,
            "market_edge_claim_authorized": False,
        }
        write_json_atomic(receipt_path, receipt)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        receipt_path = execute(args.workspace)
        receipt = json.loads(receipt_path.read_text(encoding="ascii"))
        print(
            "GCOFI002_ACQUIRE_OK "
            f"estimated_usd={receipt['fresh_estimated_total_usd']:.12f} "
            f"paid_calls={receipt['paid_timeseries_calls']} "
            f"downloaded_bytes={sum(item['bytes'] for item in receipt['downloads'])}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"GCOFI002_ACQUIRE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
