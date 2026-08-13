#!/usr/bin/env python3
"""One-shot Q1-2019 GC TBBO/definition/status source acquisition."""

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


HYPOTHESIS_ID = "HYP-GC-OFI-INNOV-XAU-M5-001"
ACQUISITION_ID = "GCOFI001-Q1-2019-SOURCE-PILOT-001"
DATASET = "GLBX.MDP3"
SYMBOL = "GC.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
START = "2019-01-01T00:00:00.000Z"
END = "2019-04-01T00:00:00.000Z"
SCHEMAS = ("tbbo", "definition", "status")
COST_MODE = "historical-streaming"
SDK_VERSION = "0.55.1"
OWNER_LIMIT_USD_EXCLUSIVE = 10.0
EXPECTED_QUOTE_USD = 8.955708209425
EXPECTED_QUOTE_BYTES = 343_488_960

BASE_REL = "03. EA Developer/EA_GCOrderFlowInnovation/research/"
SOURCE_PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_PILOT_PLAN.md"
PAID_PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_PAID_ACQUISITION_PLAN.md"
OWNER_REL = BASE_REL + HYPOTHESIS_ID + "_OWNER_AUTHORITY.json"
TOOL_REL = BASE_REL + "acquire_gc_order_flow_innovation_001.py"
TEST_REL = BASE_REL + "tests/test_acquire_gc_order_flow_innovation_001.py"
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

SOURCE_PLAN_SHA256 = "B769C8288F99DB879590765B3215BAE75030D403106BCAB8E2AD5638E23B802D"
PAID_PLAN_SHA256 = "FF329F099DC8027737C28CAC7B40A1303CDC3AB958731E710A246F285040E28D"
QUOTE_SHA256 = "AB7E59772C92149F903092FB5C32C95E97B4F974540690B10578B499BAFD7285"
RUNTIME_SHA256 = "E98FB8FC4E26865DF3FEA1FE75064CA86666E17B7781E543B2912BA49F3CC0BD"
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
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value) + b"\n")
    os.replace(temporary, path)


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


def request_args(schema: str) -> dict[str, object]:
    if schema not in SCHEMAS:
        raise AcquisitionError(f"schema outside frozen allowlist: {schema}")
    return {
        "dataset": DATASET,
        "schema": schema,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": START,
        "end": END,
    }


def load_bound_quote(path: Path) -> dict[str, Any]:
    if sha256_file(path) != QUOTE_SHA256:
        raise AcquisitionError("metadata quote receipt drifted")
    quote = json.loads(path.read_text(encoding="ascii"))
    if (
        quote.get("status") != "FREE_METADATA_QUOTE_PASS_STRICTLY_BELOW_USD10"
        or quote.get("hypothesis_id") != HYPOTHESIS_ID
        or quote.get("quote_id") != ACQUISITION_ID
        or quote.get("dataset") != DATASET
        or quote.get("symbol") != SYMBOL
        or quote.get("stype_in") != STYPE_IN
        or quote.get("start") != START
        or quote.get("end") != END
        or quote.get("paid_request_made") is not False
        or quote.get("source_payload_read") is not False
        or quote.get("xauusd_outcome_read") is not False
        or quote.get("api_method_counters", {}).get("timeseries.get_range") != 0
        or not math.isclose(
            float(quote.get("estimated_total_usd")),
            EXPECTED_QUOTE_USD,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or int(quote.get("estimated_total_billable_bytes")) != EXPECTED_QUOTE_BYTES
    ):
        raise AcquisitionError("metadata quote contract mismatch")
    if [item.get("schema") for item in quote.get("quotes", [])] != list(SCHEMAS):
        raise AcquisitionError("metadata quote schema coverage mismatch")
    return quote


def validate_owner(path: Path) -> dict[str, Any]:
    owner = json.loads(path.read_text(encoding="utf-8"))
    verbatim = owner.get("owner_authorization_verbatim")
    if (
        not isinstance(verbatim, str)
        or sha256_bytes(verbatim.encode("utf-8")) != OWNER_VERBATIM_SHA256
        or owner.get("owner_authorization_verbatim_sha256")
        != OWNER_VERBATIM_SHA256
        or owner.get("hypothesis_id") != HYPOTHESIS_ID
        or owner.get("acquisition_id") != ACQUISITION_ID
        or owner.get("owner_limit_usd_exclusive") != OWNER_LIMIT_USD_EXCLUSIVE
        or owner.get("live_estimated_total_usd") != EXPECTED_QUOTE_USD
        or owner.get("live_estimated_total_billable_bytes") != EXPECTED_QUOTE_BYTES
        or owner.get("dataset") != DATASET
        or owner.get("symbol") != SYMBOL
        or owner.get("schemas") != list(SCHEMAS)
        or owner.get("start") != START
        or owner.get("end") != END
        or owner.get("source_pilot_plan_sha256") != SOURCE_PLAN_SHA256
        or owner.get("metadata_quote_receipt_sha256") != QUOTE_SHA256
        or owner.get("paid_acquisition_plan_sha256") != PAID_PLAN_SHA256
        or owner.get("runtime_receipt_sha256") != RUNTIME_SHA256
        or owner.get("paid_source_acquisition_authorized") is not True
        or owner.get("paid_timeseries_calls_authorized") != len(SCHEMAS)
        or owner.get("same_id_remote_retry_authorized") is not False
        or owner.get("subscription_authorized") is not False
        or owner.get("auto_renewal_authorized") is not False
    ):
        raise AcquisitionError("Owner authority contract mismatch")
    for field in (
        "source_transform_authorized",
        "xauusd_outcome_authorized",
        "economics_authorized",
        "mql5_authorized",
        "mt5_authorized",
        "optimization_authorized",
        "validation_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if owner.get(field) is not False:
            raise AcquisitionError(f"forbidden Owner authority open: {field}")
    return owner


def validate_registry(workspace: Path) -> dict[str, str]:
    registry = require_d(workspace / REGISTRY_REL, "candidate registry")
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
        "source_pilot_plan_sha256": sha256_file(workspace / SOURCE_PLAN_REL),
        "metadata_quote_receipt_sha256": sha256_file(workspace / QUOTE_REL),
        "paid_acquisition_plan_sha256": sha256_file(workspace / PAID_PLAN_REL),
        "owner_authority_receipt_sha256": sha256_file(workspace / OWNER_REL),
        "reviewed_acquisition_tool_sha256": sha256_file(workspace / TOOL_REL),
        "reviewed_acquisition_test_sha256": sha256_file(workspace / TEST_REL),
        "runtime_receipt_sha256": sha256_file(workspace / RUNTIME_REL),
        "mechanism_screen_sha256": sha256_file(workspace / MECHANISM_REL),
        "estimator_sha256": sha256_file(workspace / ESTIMATOR_REL),
        "estimator_test_sha256": sha256_file(workspace / ESTIMATOR_TEST_REL),
    }
    if (
        row.get("state") != "probe"
        or row.get("verdict")
        != "AUTHORIZE_ONE_SHOT_Q1_SOURCE_ACQUISITION_UNDER_USD10"
        or row.get("prereg_sha256") != PAID_PLAN_SHA256
        or validation.get("paid_source_acquisition_authorized") is not True
        or validation.get("paid_timeseries_calls_authorized") != len(SCHEMAS)
        or validation.get("same_id_remote_retry_authorized") is not False
    ):
        raise AcquisitionError("registry acquisition authority mismatch")
    for key, actual in bound.items():
        if validation.get(key) != actual:
            raise AcquisitionError(f"registry binding mismatch: {key}")
    for field in (
        "source_transform_authorized",
        "xauusd_outcome_authorized",
        "economics_authorized",
        "mql5_authorized",
        "mt5_authorized",
        "optimization_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
        "market_edge_claim_authorized",
    ):
        if validation.get(field) is not False:
            raise AcquisitionError(f"forbidden registry authority open: {field}")
    return {**bound, "registry_row_sha256": sha256_bytes(row_bytes)}


def validate_authority(workspace: Path) -> dict[str, str]:
    checks = {
        SOURCE_PLAN_REL: SOURCE_PLAN_SHA256,
        PAID_PLAN_REL: PAID_PLAN_SHA256,
        QUOTE_REL: QUOTE_SHA256,
        RUNTIME_REL: RUNTIME_SHA256,
    }
    for relative, expected in checks.items():
        path = require_d(workspace / relative, relative)
        if sha256_file(path) != expected:
            raise AcquisitionError(f"bound artifact drifted: {relative}")
    load_bound_quote(workspace / QUOTE_REL)
    validate_owner(require_d(workspace / OWNER_REL, "Owner authority"))
    return validate_registry(workspace)


def live_requote(client: Any) -> tuple[list[dict[str, Any]], float, int]:
    quotes: list[dict[str, Any]] = []
    for schema in SCHEMAS:
        args = request_args(schema)
        cost = float(client.metadata.get_cost(mode=COST_MODE, **args))
        size = int(client.metadata.get_billable_size(**args))
        if not math.isfinite(cost) or cost < 0.0 or size <= 0:
            raise AcquisitionError(f"invalid fresh quote for {schema}")
        quotes.append(
            {
                "schema": schema,
                "estimated_usd": cost,
                "billable_bytes": size,
                "request": args,
            }
        )
    total_cost = sum(float(item["estimated_usd"]) for item in quotes)
    total_bytes = sum(int(item["billable_bytes"]) for item in quotes)
    if not total_cost < OWNER_LIMIT_USD_EXCLUSIVE:
        raise AcquisitionError(
            f"fresh aggregate estimate {total_cost:.12f} is not strictly below USD 10"
        )
    return quotes, total_cost, total_bytes


def validate_dbn_file_v3(path: Path, expected_schema: str) -> int:
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
        if (
            int(metadata.version) != 3
            or metadata.dataset != DATASET
            or schema != expected_schema
        ):
            raise AcquisitionError(f"DBNv3 metadata mismatch: {expected_schema}")
        records = sum(1 for _ in store)
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(
            f"DBNv3 full-stream validation failed for {expected_schema}: {exc}"
        ) from exc
    if records <= 0:
        raise AcquisitionError(f"zero-record paid payload: {expected_schema}")
    return records


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


def download_one(
    *,
    client: Any,
    schema: str,
    quote: dict[str, Any],
    root: Path,
    manifest: dict[str, Any],
    manifest_path: Path,
) -> dict[str, Any]:
    raw = root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    final = raw / f"{schema}.dbn.zst"
    partial = final.with_suffix(final.suffix + ".partial")
    if final.exists() or partial.exists():
        raise AcquisitionError(f"unmanifested output collision: {schema}")
    in_flight = {
        "schema": schema,
        "filename": final.name,
        "start": START,
        "end": END,
        "estimated_usd": float(quote["estimated_usd"]),
        "billable_bytes": int(quote["billable_bytes"]),
        "started_at_utc": utc_now(),
    }
    manifest["status"] = "DOWNLOADING_SERIAL"
    manifest["in_flight"] = in_flight
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    try:
        client.timeseries.get_range(
            **request_args(schema), stype_out=STYPE_OUT, path=partial
        )
    except Exception as exc:
        raise AcquisitionError(
            f"paid request failed for {schema}: {type(exc).__name__}"
        ) from exc
    records = validate_dbn_file_v3(partial, schema)
    os.replace(partial, final)
    downloaded = {
        **in_flight,
        "bytes": final.stat().st_size,
        "sha256": sha256_file(final),
        "records": records,
        "dbn_version": 3,
        "dataset": DATASET,
        "completed_at_utc": utc_now(),
    }
    manifest["downloads"].append(downloaded)
    manifest["in_flight"] = None
    manifest["paid_timeseries_calls"] = len(manifest["downloads"])
    manifest["updated_at_utc"] = utc_now()
    write_json_atomic(manifest_path, manifest)
    return downloaded


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    require_d(workspace, "workspace")
    authority = validate_authority(workspace)
    root = require_d(workspace / OUTPUT_REL, "acquisition root")
    plan_path = root / "acquisition_plan.json"
    manifest_path = root / "download_manifest.json"
    receipt_path = root / "paid_acquisition_receipt.json"
    if plan_path.exists() or manifest_path.exists() or receipt_path.exists():
        raise AcquisitionError(
            "same-ID acquisition state already exists; remote retry is forbidden"
        )
    with exclusive_lock(root):
        client = make_client(load_api_key())
        quotes, total_cost, total_bytes = live_requote(client)
        plan = {
            "schema_version": "gc_order_flow_innovation_acquisition_plan.v1",
            "created_at_utc": utc_now(),
            "hypothesis_id": HYPOTHESIS_ID,
            "acquisition_id": ACQUISITION_ID,
            "dataset": DATASET,
            "symbol": SYMBOL,
            "schemas": list(SCHEMAS),
            "stype_in": STYPE_IN,
            "stype_out": STYPE_OUT,
            "start": START,
            "end": END,
            "cost_mode": COST_MODE,
            "owner_limit_usd_exclusive": OWNER_LIMIT_USD_EXCLUSIVE,
            "fresh_estimated_total_usd": total_cost,
            "fresh_estimated_total_billable_bytes": total_bytes,
            "quotes": quotes,
            "paid_calls_serial_only": True,
            "same_id_remote_retry_authorized": False,
            "bindings": authority,
            "source_transform_authorized": False,
            "xauusd_outcome_authorized": False,
            "economics_authorized": False,
            "mql5_authorized": False,
            "mt5_authorized": False,
        }
        write_json_atomic(plan_path, plan)
        manifest = {
            "schema_version": "gc_order_flow_innovation_download_manifest.v1",
            "status": "LIVE_QUOTED_NOT_DOWNLOADED",
            "created_at_utc": utc_now(),
            "updated_at_utc": utc_now(),
            "hypothesis_id": HYPOTHESIS_ID,
            "acquisition_id": ACQUISITION_ID,
            "acquisition_plan_sha256": sha256_file(plan_path),
            "owner_limit_usd_exclusive": OWNER_LIMIT_USD_EXCLUSIVE,
            "fresh_estimated_total_usd": total_cost,
            "fresh_estimated_total_billable_bytes": total_bytes,
            "downloads": [],
            "in_flight": None,
            "paid_timeseries_calls": 0,
            "source_transform_used": False,
            "xauusd_outcome_read": False,
            "economics_executed": False,
        }
        write_json_atomic(manifest_path, manifest)
        by_schema = {item["schema"]: item for item in quotes}
        for schema in SCHEMAS:
            download_one(
                client=client,
                schema=schema,
                quote=by_schema[schema],
                root=root,
                manifest=manifest,
                manifest_path=manifest_path,
            )
        if manifest["paid_timeseries_calls"] != len(SCHEMAS):
            raise AcquisitionError("paid call coverage mismatch")
        manifest["status"] = "COMPLETE_RAW_SOURCE_QUALITY_REQUIRED"
        manifest["updated_at_utc"] = utc_now()
        manifest["downloaded_bytes"] = sum(
            int(item["bytes"]) for item in manifest["downloads"]
        )
        manifest["records"] = sum(int(item["records"]) for item in manifest["downloads"])
        write_json_atomic(manifest_path, manifest)
        receipt = {
            "schema_version": "gc_order_flow_innovation_paid_acquisition_receipt.v1",
            "created_at_utc": utc_now(),
            "status": "COMPLETE_RAW_SOURCE_QUALITY_REQUIRED",
            "hypothesis_id": HYPOTHESIS_ID,
            "acquisition_id": ACQUISITION_ID,
            "fresh_estimated_total_usd": total_cost,
            "fresh_estimated_total_billable_bytes": total_bytes,
            "paid_timeseries_calls": len(SCHEMAS),
            "acquisition_plan_sha256": sha256_file(plan_path),
            "download_manifest_sha256": sha256_file(manifest_path),
            "downloads": manifest["downloads"],
            "bindings": authority,
            "source_quality_verdict": "PENDING",
            "source_transform_authorized": False,
            "xauusd_outcome_read": False,
            "economics_executed": False,
            "mql5_authorized": False,
            "mt5_authorized": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
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
            "GCOFI001_ACQUIRE_OK "
            f"estimated_usd={receipt['fresh_estimated_total_usd']:.12f} "
            f"paid_calls={receipt['paid_timeseries_calls']} "
            f"downloaded_bytes={sum(item['bytes'] for item in receipt['downloads'])}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"GCOFI001_ACQUIRE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

