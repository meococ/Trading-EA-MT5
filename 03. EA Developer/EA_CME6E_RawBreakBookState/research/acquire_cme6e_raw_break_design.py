#!/usr/bin/env python3
"""Acquire the Owner-approved CME 6E raw-BREAK DESIGN book corpus.

The frozen metadata source plan remains immutable. An execution authorization
packet binds that exact plan, this tool's SHA, and the Owner's USD ceilings.
Before the first paid request, every billable DESIGN window is re-quoted and
both the plan and combined-session ceilings are enforced. Downloads are serial,
hash-checkpointed, resumable, outcome-blind, and never open sealed OOS.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SOURCE_PLAN_SCHEMA_VERSION = "cme6e_raw_break_design_source_plan.v1"
EXECUTION_SCHEMA_VERSION = "cme6e_raw_break_design_execution.v1"
MANIFEST_SCHEMA_VERSION = "cme6e_raw_break_design_download_manifest.v1"
RECEIPT_SCHEMA_VERSION = "cme6e_raw_break_design_validation_receipt.v1"
CANDIDATE_IDENTITY = "CME_GLOBEX_6E_MBP10_RAW_BREAK_BOOK_STATE"
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
COST_MODE = "historical-streaming"
WINDOW_SECONDS = 120
DATABENTO_SDK_VERSION = "0.54.0"
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
KEY_PATTERN = re.compile(r"^db-[A-Za-z0-9_-]{29}$")

APPROVED_SOURCE_PLAN_ID = (
    "1825DC77A35F2794051BD83E5A35ED87C8952049FB08B47BEA1AF34E1802D98F"
)
APPROVED_SOURCE_PLAN_SHA256 = (
    "B780B7A4AD0F0C8B7CDF6A109DE41754C5F9CD88856D464085EE69513A1E24D5"
)
APPROVED_PLANNER_SHA256 = (
    "686457183C03BECB92BAEBB7D090C8E7E1EBC4F9196BEC57BC6B83DB9486FAB2"
)
APPROVED_MAX_USD = 0.68
PRIOR_SESSION_ESTIMATE_USD = 0.254399180414
COMBINED_SESSION_CAP_USD = 1.0

WORKSPACE = Path(__file__).resolve().parents[3]
MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
DATA_ROOT = WORKSPACE / "02. AlphaFactory" / "data"
DEFAULT_ROOT = DATA_ROOT / "databento" / "cme_6e_raw_break_design"
SOURCE_PLAN_PATH = DEFAULT_ROOT / "source_plan.json"
EXECUTION_NAME = "execution_authorization.json"
MANIFEST_NAME = "download_manifest.json"
RECEIPT_NAME = "validation_receipt.json"
PLANNER_PATH = PACKAGE / "research" / "plan_cme6e_raw_break_design.py"


class AcquisitionError(RuntimeError):
    """Fail-closed source acquisition error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AcquisitionError(f"expected a JSON object in {path}")
    return value


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _stable_execution(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"created_at_utc", "execution_id"}
    }


def execution_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        _stable_execution(payload), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _load_planner_module():
    spec = importlib.util.spec_from_file_location("raw_break_design_planner", PLANNER_PATH)
    if spec is None or spec.loader is None:
        raise AcquisitionError("cannot load the frozen source planner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_workspace_path(value: str) -> Path:
    path = (WORKSPACE / value).resolve()
    try:
        path.relative_to(WORKSPACE.resolve())
    except ValueError as exc:
        raise AcquisitionError(f"bound path escapes workspace: {value}") from exc
    return path


def _verify_bound_file(binding: dict[str, Any], path_key: str, sha_key: str) -> None:
    path = _resolve_workspace_path(str(binding.get(path_key, "")))
    expected = str(binding.get(sha_key, ""))
    if not path.is_file():
        raise AcquisitionError(f"bound source file is absent: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise AcquisitionError(
            f"bound source SHA mismatch for {path}: expected {expected}, got {actual}"
        )


def validate_approved_source_plan(plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != SOURCE_PLAN_SCHEMA_VERSION:
        raise AcquisitionError("source plan schema mismatch")
    if plan.get("plan_id") != APPROVED_SOURCE_PLAN_ID:
        raise AcquisitionError("source plan ID is not the Owner-approved plan")
    if plan.get("candidate_identity") != CANDIDATE_IDENTITY:
        raise AcquisitionError("source plan candidate identity mismatch")
    expected_surface = {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "cost_mode": COST_MODE,
        "window_seconds": WINDOW_SECONDS,
    }
    for field, expected in expected_surface.items():
        if plan.get(field) != expected:
            raise AcquisitionError(f"source plan {field} mismatch")
    if plan.get("design_utc_years") != [2019, 2020]:
        raise AcquisitionError("source plan DESIGN years mismatch")
    if plan.get("sealed_oos_utc_years") != [2021, 2022]:
        raise AcquisitionError("source plan sealed OOS years mismatch")
    if plan.get("sealed_oos_quoted") is not False:
        raise AcquisitionError("source plan opened sealed OOS")
    if plan.get("paid_request_made") is not False:
        raise AcquisitionError("source plan reports a paid request")
    if plan.get("download_authorized") is not False:
        raise AcquisitionError("metadata-only source plan was mutated to authorize download")
    input_contract = plan.get("input")
    if not isinstance(input_contract, dict):
        raise AcquisitionError("source plan input contract is absent")
    if input_contract.get("fields_used") != [
        "position_id",
        "decision_time",
        "direction",
    ]:
        raise AcquisitionError("source plan identity fields mismatch")
    if input_contract.get("outcome_fields_used") is not False:
        raise AcquisitionError("source plan is not outcome-blind")
    tool = plan.get("tool")
    if not isinstance(tool, dict) or tool.get("sha256") != APPROVED_PLANNER_SHA256:
        raise AcquisitionError("source plan planner SHA mismatch")
    if sha256_file(PLANNER_PATH) != APPROVED_PLANNER_SHA256:
        raise AcquisitionError("source planner changed after plan approval")

    try:
        _load_planner_module().validate_plan(plan)
    except Exception as exc:
        raise AcquisitionError(f"source plan hash validation failed: {exc}") from exc

    _verify_bound_file(input_contract, "path", "sha256")
    clock = plan.get("clock")
    parent = plan.get("source_feasibility_parent")
    quote = plan.get("quote_provenance")
    if not isinstance(clock, dict) or not isinstance(parent, dict) or not isinstance(quote, dict):
        raise AcquisitionError("source plan provenance bindings are incomplete")
    _verify_bound_file(clock, "path", "sha256")
    _verify_bound_file(parent, "plan_path", "plan_sha256")
    _verify_bound_file(parent, "manifest_path", "manifest_sha256")
    _verify_bound_file(quote, "path", "sha256")
    if quote.get("network_calls") != 0 or quote.get("paid_request_made") is not False:
        raise AcquisitionError("source quote provenance is not zero-paid")
    if quote.get("outcome_fields_used") is not False:
        raise AcquisitionError("source quote provenance is not outcome-blind")

    requests = plan.get("requests")
    metadata_empty = plan.get("metadata_empty_windows")
    quotes = plan.get("live_quotes")
    if not isinstance(requests, list) or len(requests) != 541:
        raise AcquisitionError("source plan billable request coverage mismatch")
    if not isinstance(metadata_empty, list) or len(metadata_empty) != 6:
        raise AcquisitionError("source plan metadata-empty coverage mismatch")
    if not isinstance(quotes, list) or len(quotes) != 547:
        raise AcquisitionError("source plan quote coverage mismatch")
    all_windows = requests + metadata_empty
    ids = [str(item.get("position_id", "")) for item in all_windows]
    filenames = [str(item.get("filename", "")) for item in all_windows]
    if len(set(ids)) != 547 or len(set(filenames)) != 547:
        raise AcquisitionError("source plan contains duplicate window identities")
    request_ids = set(ids[: len(requests)])
    empty_ids = set(ids[len(requests) :])
    quote_by_id: dict[str, dict[str, Any]] = {}
    for item in quotes:
        position_id = str(item.get("position_id", ""))
        if position_id in quote_by_id:
            raise AcquisitionError("source plan contains duplicate live quotes")
        quote_by_id[position_id] = item
    if set(quote_by_id) != request_ids | empty_ids:
        raise AcquisitionError("source plan quotes do not cover frozen windows")
    for item in all_windows:
        required = {"position_id", "direction", "start", "end", "filename"}
        if not isinstance(item, dict) or not required.issubset(item):
            raise AcquisitionError("source plan contains an invalid window")
        if item["direction"] not in {"BUY", "SELL"}:
            raise AcquisitionError("source plan contains an invalid direction")
        start = datetime.fromisoformat(str(item["start"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(item["end"]).replace("Z", "+00:00"))
        if end - start != timedelta(seconds=WINDOW_SECONDS) or end.year not in {2019, 2020}:
            raise AcquisitionError("source plan contains a non-DESIGN or invalid window")
    for position_id in request_ids:
        if int(quote_by_id[position_id].get("billable_bytes", 0)) <= 0:
            raise AcquisitionError("billable request lacks positive frozen metadata")
    for position_id in empty_ids:
        if int(quote_by_id[position_id].get("billable_bytes", -1)) != 0:
            raise AcquisitionError("metadata-empty window classification mismatch")
    estimated_cost = sum(
        float(quote_by_id[position_id]["estimated_cost_usd"])
        for position_id in request_ids
    )
    estimated_bytes = sum(
        int(quote_by_id[position_id]["billable_bytes"]) for position_id in request_ids
    )
    if not math.isclose(estimated_cost, float(plan["estimated_cost_usd"]), abs_tol=1e-12):
        raise AcquisitionError("source plan estimated cost does not reconcile")
    if estimated_bytes != int(plan["estimated_billable_bytes"]):
        raise AcquisitionError("source plan billable bytes do not reconcile")
    if not math.isclose(
        float(plan.get("recommended_owner_ceiling_usd", 0)), APPROVED_MAX_USD
    ):
        raise AcquisitionError("source plan Owner ceiling mismatch")


def load_approved_source_plan() -> dict[str, Any]:
    if not SOURCE_PLAN_PATH.is_file():
        raise AcquisitionError(f"approved source plan is absent: {SOURCE_PLAN_PATH}")
    actual = sha256_file(SOURCE_PLAN_PATH)
    if actual != APPROVED_SOURCE_PLAN_SHA256:
        raise AcquisitionError(
            "approved source plan file SHA mismatch: "
            f"expected {APPROVED_SOURCE_PLAN_SHA256}, got {actual}"
        )
    plan = load_json(SOURCE_PLAN_PATH)
    validate_approved_source_plan(plan)
    return plan


def build_execution_authorization(
    *,
    plan: dict[str, Any],
    approved_max_usd: float,
    prior_session_estimate_usd: float,
    combined_session_cap_usd: float,
) -> dict[str, Any]:
    validate_approved_source_plan(plan)
    if not math.isclose(approved_max_usd, APPROVED_MAX_USD, abs_tol=1e-12):
        raise AcquisitionError("execution packet does not match Owner-approved USD 0.68")
    if not math.isclose(
        prior_session_estimate_usd, PRIOR_SESSION_ESTIMATE_USD, abs_tol=1e-12
    ):
        raise AcquisitionError("prior session estimate does not match validated receipt")
    if not math.isclose(
        combined_session_cap_usd, COMBINED_SESSION_CAP_USD, abs_tol=1e-12
    ):
        raise AcquisitionError("combined session cap does not match Owner authority")
    projected = prior_session_estimate_usd + float(plan["estimated_cost_usd"])
    if projected > combined_session_cap_usd:
        raise AcquisitionError("projected combined estimate exceeds Owner session cap")
    payload: dict[str, Any] = {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "status": "OWNER_APPROVED_SOURCE_PLAN_BOUND",
        "source_plan": {
            "path": str(SOURCE_PLAN_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "plan_id": plan["plan_id"],
            "sha256": APPROVED_SOURCE_PLAN_SHA256,
        },
        "acquisition_tool": {
            "path": str(MODULE_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": sha256_file(MODULE_PATH),
        },
        "owner_authority": "2026-07-27 explicit approval for plan 1825DC77...02D98F",
        "approved_max_usd": approved_max_usd,
        "prior_session_estimate_usd": prior_session_estimate_usd,
        "combined_session_cap_usd": combined_session_cap_usd,
        "projected_combined_estimate_usd": projected,
        "billable_design_windows": len(plan["requests"]),
        "metadata_empty_design_windows": len(plan["metadata_empty_windows"]),
        "sealed_oos_opened": False,
        "outcome_fields_used": False,
        "prohibitions": [
            "no OOS quote, download, decode or outcome access",
            "no outcome join before a fresh hypothesis, registry row and SHA-bound prereg",
            "no HYP004 amendment, rerun or rescue claim",
            "no automatic paid retry for an unresolved in-flight request",
            "no combined estimated session cost above USD 1.00",
        ],
    }
    payload["execution_id"] = execution_id(payload)
    validate_execution_authorization(payload, plan)
    return payload


def validate_execution_authorization(
    packet: dict[str, Any], plan: dict[str, Any]
) -> None:
    if packet.get("schema_version") != EXECUTION_SCHEMA_VERSION:
        raise AcquisitionError("execution authorization schema mismatch")
    source = packet.get("source_plan")
    tool = packet.get("acquisition_tool")
    if not isinstance(source, dict) or not isinstance(tool, dict):
        raise AcquisitionError("execution authorization bindings are absent")
    if source.get("plan_id") != plan.get("plan_id"):
        raise AcquisitionError("execution authorization source plan ID mismatch")
    if source.get("sha256") != APPROVED_SOURCE_PLAN_SHA256:
        raise AcquisitionError("execution authorization source plan SHA mismatch")
    current_tool_sha = sha256_file(MODULE_PATH)
    if tool.get("sha256") != current_tool_sha:
        raise AcquisitionError("execution authorization acquisition tool SHA mismatch")
    if not math.isclose(float(packet.get("approved_max_usd", -1)), APPROVED_MAX_USD):
        raise AcquisitionError("execution authorization Owner ceiling mismatch")
    if not math.isclose(
        float(packet.get("prior_session_estimate_usd", -1)),
        PRIOR_SESSION_ESTIMATE_USD,
        abs_tol=1e-12,
    ):
        raise AcquisitionError("execution authorization prior estimate mismatch")
    if not math.isclose(
        float(packet.get("combined_session_cap_usd", -1)),
        COMBINED_SESSION_CAP_USD,
        abs_tol=1e-12,
    ):
        raise AcquisitionError("execution authorization combined cap mismatch")
    projected = PRIOR_SESSION_ESTIMATE_USD + float(plan["estimated_cost_usd"])
    if not math.isclose(
        float(packet.get("projected_combined_estimate_usd", -1)),
        projected,
        abs_tol=1e-12,
    ):
        raise AcquisitionError("execution authorization projected estimate mismatch")
    if projected > COMBINED_SESSION_CAP_USD:
        raise AcquisitionError("execution authorization exceeds combined session cap")
    if packet.get("outcome_fields_used") is not False:
        raise AcquisitionError("execution authorization is not outcome-blind")
    if packet.get("sealed_oos_opened") is not False:
        raise AcquisitionError("execution authorization opened sealed OOS")
    if packet.get("execution_id") != execution_id(packet):
        raise AcquisitionError("execution authorization hash mismatch")


def ensure_output_root(root: Path) -> Path:
    resolved = root.resolve()
    if resolved.drive.upper() != "D:":
        raise AcquisitionError(f"output root must be on D:, got {resolved}")
    try:
        resolved.relative_to(DATA_ROOT.resolve())
    except ValueError as exc:
        raise AcquisitionError(
            f"output root must remain under {DATA_ROOT.resolve()}, got {resolved}"
        ) from exc
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
        raise AcquisitionError(
            "DATABENTO_API_KEY is absent; configure it locally and never paste it into chat"
        )
    key = key.strip()
    if not KEY_PATTERN.fullmatch(key):
        raise AcquisitionError("DATABENTO_API_KEY has an unexpected format")
    return key


def make_client(key: str):
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError(
            "Databento SDK is missing; use the D-side python-databento runtime"
        ) from exc
    installed = str(getattr(db, "__version__", ""))
    if installed != DATABENTO_SDK_VERSION:
        raise AcquisitionError(
            f"Databento SDK version mismatch: required {DATABENTO_SDK_VERSION}, "
            f"installed {installed or 'unknown'}"
        )
    return db.Historical(key)


def validate_dbn_zstd(path: Path) -> None:
    if not path.is_file() or path.stat().st_size <= len(ZSTD_MAGIC):
        raise AcquisitionError(f"DBN Zstandard file is missing or empty: {path}")
    with path.open("rb") as handle:
        signature = handle.read(len(ZSTD_MAGIC))
    if signature != ZSTD_MAGIC:
        raise AcquisitionError(f"DBN file has invalid Zstandard signature: {path}")


def validate_dbn_file(path: Path, allow_zero: bool = False) -> int:
    validate_dbn_zstd(path)
    try:
        import databento as db
    except ImportError as exc:
        raise AcquisitionError("Databento SDK is required for DBN validation") from exc
    installed = str(getattr(db, "__version__", ""))
    if installed != DATABENTO_SDK_VERSION:
        raise AcquisitionError("Databento SDK version mismatch during DBN validation")
    try:
        records = sum(1 for _ in db.DBNStore.from_file(path))
    except Exception as exc:
        raise AcquisitionError(f"DBN full-stream validation failed for {path}: {exc}") from exc
    if records <= 0 and not allow_zero:
        raise AcquisitionError(f"DBN file contains zero market-data records: {path}")
    return records


def _api_call(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": item["start"],
        "end": item["end"],
    }


def quote_windows(
    client,
    requests: list[dict[str, Any]],
    *,
    client_factory: Callable[[], Any] | None = None,
    workers: int = 1,
) -> list[dict[str, Any]]:
    if workers < 1 or workers > 16:
        raise AcquisitionError("metadata quote workers must be between 1 and 16")
    local = threading.local()

    def quote(item: dict[str, Any]) -> dict[str, Any]:
        if client_factory is None:
            metadata = client.metadata
        else:
            if not hasattr(local, "client"):
                local.client = client_factory()
            metadata = local.client.metadata
        call = _api_call(item)
        cost = float(metadata.get_cost(mode=COST_MODE, **call))
        size = int(metadata.get_billable_size(**call))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError(
                f"invalid live quote for position {item['position_id']}: cost={cost}, size={size}"
            )
        return {
            "position_id": item["position_id"],
            "start": item["start"],
            "end": item["end"],
            "estimated_cost_usd": cost,
            "billable_bytes": size,
        }

    if workers == 1:
        return [quote(item) for item in requests]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(quote, requests))


def _validate_manifest_contract(
    manifest: dict[str, Any], plan: dict[str, Any], execution: dict[str, Any]
) -> None:
    if not manifest:
        return
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise AcquisitionError("existing download manifest schema mismatch")
    if manifest.get("plan_id") != plan["plan_id"]:
        raise AcquisitionError("existing download manifest belongs to another plan")
    if manifest.get("source_plan_sha256") != APPROVED_SOURCE_PLAN_SHA256:
        raise AcquisitionError("existing download manifest source plan SHA mismatch")
    if manifest.get("execution_id") != execution["execution_id"]:
        raise AcquisitionError("existing download manifest execution ID mismatch")
    if manifest.get("acquisition_tool_sha256") != sha256_file(MODULE_PATH):
        raise AcquisitionError("existing download manifest tool SHA mismatch")
    if manifest.get("outcome_fields_used") is not False:
        raise AcquisitionError("existing download manifest is not outcome-blind")
    if manifest.get("sealed_oos_opened") is not False:
        raise AcquisitionError("existing download manifest opened sealed OOS")


def _verified_downloads(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not manifest:
        return {}
    _validate_manifest_contract(manifest, plan, execution)
    planned = {str(item["filename"]): item for item in plan["requests"]}
    verified: dict[str, dict[str, Any]] = {}
    for item in manifest.get("downloads", []):
        if not isinstance(item, dict):
            raise AcquisitionError("download manifest contains an invalid file entry")
        filename = str(item.get("filename", ""))
        if filename not in planned:
            raise AcquisitionError(
                f"download manifest contains an output outside the frozen plan: {filename}"
            )
        if filename in verified:
            raise AcquisitionError(f"download manifest contains a duplicate output: {filename}")
        request = planned[filename]
        for field in ("position_id", "direction", "start", "end"):
            if str(item.get(field, "")) != str(request[field]):
                raise AcquisitionError(
                    f"download manifest identity mismatch for {filename}: {field}"
                )
        path = root / "raw" / filename
        source_empty = item.get("source_empty") is True
        records = validate_dbn_file(path, allow_zero=source_empty)
        if source_empty != (records == 0):
            raise AcquisitionError(
                f"checkpointed source-empty classification mismatch for {filename}"
            )
        if int(item.get("records", -1)) != records:
            raise AcquisitionError(f"checkpointed record count mismatch for {filename}")
        if sha256_file(path) != str(item.get("sha256", "")):
            raise AcquisitionError(f"checkpointed DBN hash mismatch for {filename}")
        if path.stat().st_size != int(item.get("bytes", -1)):
            raise AcquisitionError(f"checkpointed DBN byte count mismatch for {filename}")
        verified[filename] = item
    return verified


def _recover_in_flight(
    *,
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    quotes_by_position: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    in_flight = manifest.get("in_flight")
    if in_flight in (None, {}):
        return None
    if not isinstance(in_flight, dict):
        raise AcquisitionError("download manifest has an invalid in-flight journal")
    filename = str(in_flight.get("filename", ""))
    planned = {str(item["filename"]): item for item in plan["requests"]}
    if filename not in planned:
        raise AcquisitionError("in-flight journal is outside the frozen plan")
    request = planned[filename]
    for field in ("position_id", "direction", "start", "end"):
        if str(in_flight.get(field, "")) != str(request[field]):
            raise AcquisitionError(f"in-flight journal identity mismatch: {field}")
    output = root / "raw" / filename
    partial = output.with_suffix(output.suffix + ".partial")
    if output.exists() and partial.exists():
        raise AcquisitionError("both final and partial in-flight files exist")
    candidate = output if output.exists() else partial
    if not candidate.exists():
        raise AcquisitionError(
            "in-flight paid request has no recoverable file; refusing automatic retry "
            f"for position {request['position_id']}"
        )
    records = validate_dbn_file(candidate, allow_zero=True)
    if candidate == partial:
        os.replace(partial, output)
    quote = quotes_by_position[request["position_id"]]
    return {
        "position_id": request["position_id"],
        "direction": request["direction"],
        "start": request["start"],
        "end": request["end"],
        "filename": filename,
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "records": records,
        "source_empty": records == 0,
        "estimated_cost_usd": quote["estimated_cost_usd"],
        "billable_bytes": quote["billable_bytes"],
        "recovered_from_in_flight": True,
    }


def _refresh_manifest_counts(manifest: dict[str, Any]) -> None:
    downloads = manifest["downloads"]
    manifest["paid_requests_completed"] = len(downloads)
    manifest["nonempty_files"] = sum(
        1 for item in downloads if item.get("source_empty") is not True
    )
    manifest["source_empty_files"] = sum(
        1 for item in downloads if item.get("source_empty") is True
    )
    manifest["decoded_records"] = sum(int(item["records"]) for item in downloads)
    manifest["estimated_cost_completed_usd"] = sum(
        float(item["estimated_cost_usd"]) for item in downloads
    )
    manifest["updated_at_utc"] = utc_now()


def download_windows(
    *,
    client,
    plan: dict[str, Any],
    execution: dict[str, Any],
    root: Path,
    metadata_client_factory: Callable[[], Any] | None = None,
    quote_workers: int = 1,
) -> dict[str, Any]:
    validate_approved_source_plan(plan)
    validate_execution_authorization(execution, plan)
    root = ensure_output_root(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / MANIFEST_NAME
    existing = load_json(manifest_path) if manifest_path.is_file() else {}
    verified = _verified_downloads(root, existing, plan, execution)

    requests = list(plan["requests"])
    quotes = quote_windows(
        client,
        requests,
        client_factory=metadata_client_factory,
        workers=quote_workers,
    )
    if len(quotes) != len(requests):
        raise AcquisitionError("live quote coverage does not match frozen requests")
    now_empty = [item["position_id"] for item in quotes if item["billable_bytes"] <= 0]
    if now_empty:
        raise AcquisitionError(
            "planned billable windows are now empty; no paid request made: "
            + ",".join(now_empty)
        )
    live_total = sum(float(item["estimated_cost_usd"]) for item in quotes)
    live_bytes = sum(int(item["billable_bytes"]) for item in quotes)
    approved_max = float(execution["approved_max_usd"])
    if live_total > approved_max:
        raise AcquisitionError(
            f"live estimate ${live_total:.6f} exceeds approved ceiling ${approved_max:.6f}"
        )
    drift_ceiling = float(plan["internal_2x_cost_ceiling_usd"])
    if live_total > drift_ceiling:
        raise AcquisitionError(
            f"live estimate ${live_total:.6f} exceeds frozen two-times drift ceiling "
            f"${drift_ceiling:.6f}"
        )
    combined = float(execution["prior_session_estimate_usd"]) + live_total
    if combined > float(execution["combined_session_cap_usd"]):
        raise AcquisitionError(
            f"combined live estimate ${combined:.6f} exceeds Owner session cap"
        )

    by_position = {str(item["position_id"]): item for item in quotes}
    downloads = list(verified.values())
    completed_names = set(verified)
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "updated_at_utc": utc_now(),
        "status": "QUOTED_NOT_DOWNLOADED",
        "candidate_identity": CANDIDATE_IDENTITY,
        "plan_id": plan["plan_id"],
        "source_plan_sha256": APPROVED_SOURCE_PLAN_SHA256,
        "execution_id": execution["execution_id"],
        "acquisition_tool_sha256": sha256_file(MODULE_PATH),
        "approved_max_usd": approved_max,
        "prior_session_estimate_usd": execution["prior_session_estimate_usd"],
        "combined_session_cap_usd": execution["combined_session_cap_usd"],
        "live_estimated_total_usd": live_total,
        "live_estimated_billable_bytes": live_bytes,
        "combined_live_estimated_usd": combined,
        "live_quotes": quotes,
        "planned_metadata_empty_windows": plan["metadata_empty_windows"],
        "downloads": downloads,
        "resume_verified_files": len(verified),
        "recovered_in_flight_files": int(existing.get("recovered_in_flight_files", 0)),
        "in_flight": existing.get("in_flight"),
        "outcome_fields_used": False,
        "sealed_oos_opened": False,
        "api_key_stored": False,
    }
    _refresh_manifest_counts(manifest)
    write_json_atomic(manifest_path, manifest)

    raw_root = root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    recovered = _recover_in_flight(
        root=root,
        manifest=manifest,
        plan=plan,
        quotes_by_position=by_position,
    )
    if recovered is not None:
        if recovered["filename"] in completed_names:
            raise AcquisitionError("in-flight journal duplicates a checkpointed download")
        downloads.append(recovered)
        completed_names.add(recovered["filename"])
        manifest["downloads"] = downloads
        manifest["in_flight"] = None
        manifest["recovered_in_flight_files"] += 1
        _refresh_manifest_counts(manifest)
        write_json_atomic(manifest_path, manifest)

    for request in requests:
        filename = str(request["filename"])
        if filename in completed_names:
            continue
        output = raw_root / filename
        partial = output.with_suffix(output.suffix + ".partial")
        if output.exists():
            raise AcquisitionError(f"unmanifested output exists; refusing overwrite: {output}")
        if partial.exists():
            raise AcquisitionError(
                f"unmanifested partial exists; refusing paid retry: {partial}"
            )
        quote = by_position[str(request["position_id"])]
        manifest["status"] = "DOWNLOADING"
        manifest["in_flight"] = {
            "position_id": request["position_id"],
            "direction": request["direction"],
            "start": request["start"],
            "end": request["end"],
            "filename": filename,
            "started_at_utc": utc_now(),
            "estimated_cost_usd": quote["estimated_cost_usd"],
            "billable_bytes": quote["billable_bytes"],
        }
        _refresh_manifest_counts(manifest)
        write_json_atomic(manifest_path, manifest)
        try:
            client.timeseries.get_range(
                **_api_call(request), stype_out=STYPE_OUT, path=partial
            )
        except Exception as exc:
            raise AcquisitionError(
                f"paid request failed for position {request['position_id']}: {exc}"
            ) from exc
        records = validate_dbn_file(partial, allow_zero=True)
        os.replace(partial, output)
        downloads.append(
            {
                "position_id": request["position_id"],
                "direction": request["direction"],
                "start": request["start"],
                "end": request["end"],
                "filename": filename,
                "bytes": output.stat().st_size,
                "sha256": sha256_file(output),
                "records": records,
                "source_empty": records == 0,
                "estimated_cost_usd": quote["estimated_cost_usd"],
                "billable_bytes": quote["billable_bytes"],
            }
        )
        completed_names.add(filename)
        manifest["downloads"] = downloads
        manifest["in_flight"] = None
        _refresh_manifest_counts(manifest)
        write_json_atomic(manifest_path, manifest)

    if len(downloads) != len(requests):
        raise AcquisitionError(f"download coverage incomplete: {len(downloads)}/{len(requests)}")
    _verified_downloads(root, manifest, plan, execution)
    manifest["status"] = "DOWNLOADED_RAW_VALIDATION_REQUIRED"
    _refresh_manifest_counts(manifest)
    write_json_atomic(manifest_path, manifest)
    return manifest


def validate_download(
    root: Path, plan: dict[str, Any], execution: dict[str, Any]
) -> dict[str, Any]:
    validate_approved_source_plan(plan)
    validate_execution_authorization(execution, plan)
    root = ensure_output_root(root)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise AcquisitionError(f"download manifest is absent: {manifest_path}")
    manifest = load_json(manifest_path)
    verified = _verified_downloads(root, manifest, plan, execution)
    if len(verified) != len(plan["requests"]):
        raise AcquisitionError(
            f"validated DBN coverage is incomplete: {len(verified)}/{len(plan['requests'])}"
        )
    year_counts: dict[str, dict[str, int]] = {}
    for item in verified.values():
        year = str(item["end"])[:4]
        bucket = year_counts.setdefault(
            year, {"files": 0, "nonempty_files": 0, "source_empty_files": 0, "records": 0}
        )
        bucket["files"] += 1
        bucket["records"] += int(item["records"])
        if item.get("source_empty") is True:
            bucket["source_empty_files"] += 1
        else:
            bucket["nonempty_files"] += 1
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "RAW_DESIGN_SOURCE_HASH_VALIDATION_PASS",
        "candidate_identity": CANDIDATE_IDENTITY,
        "plan_id": plan["plan_id"],
        "source_plan_sha256": APPROVED_SOURCE_PLAN_SHA256,
        "execution_id": execution["execution_id"],
        "execution_authorization_sha256": sha256_file(root / EXECUTION_NAME),
        "acquisition_tool_sha256": sha256_file(MODULE_PATH),
        "manifest_sha256": sha256_file(manifest_path),
        "response_files": len(verified),
        "nonempty_files": sum(
            1 for item in verified.values() if item.get("source_empty") is not True
        ),
        "source_empty_files": sum(
            1 for item in verified.values() if item.get("source_empty") is True
        ),
        "planned_metadata_empty_windows": len(plan["metadata_empty_windows"]),
        "covered_design_decisions": len(verified) + len(plan["metadata_empty_windows"]),
        "decoded_records": sum(int(item["records"]) for item in verified.values()),
        "compressed_bytes": sum(int(item["bytes"]) for item in verified.values()),
        "live_estimated_cost_usd": manifest["live_estimated_total_usd"],
        "live_estimated_billable_bytes": manifest["live_estimated_billable_bytes"],
        "combined_live_estimated_usd": manifest["combined_live_estimated_usd"],
        "invoice_verified_actual_charge": False,
        "year_counts": year_counts,
        "outcome_fields_used": False,
        "sealed_oos_opened": False,
    }
    write_json_atomic(root / RECEIPT_NAME, receipt)
    return receipt


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("authorize", "download", "validate"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--expected-source-plan-id")
    parser.add_argument("--expected-execution-id")
    parser.add_argument("--approve-max-usd", type=float)
    parser.add_argument("--prior-session-estimate-usd", type=float)
    parser.add_argument("--combined-session-cap-usd", type=float)
    parser.add_argument("--quote-workers", type=int, default=8)
    return parser.parse_args(argv)


def _require_expected_source_plan_id(value: str | None) -> None:
    if value != APPROVED_SOURCE_PLAN_ID:
        raise AcquisitionError(
            f"operation requires --expected-source-plan-id {APPROVED_SOURCE_PLAN_ID}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        root = ensure_output_root(args.root)
        _require_expected_source_plan_id(args.expected_source_plan_id)
        plan = load_approved_source_plan()
        execution_path = root / EXECUTION_NAME

        if args.action == "authorize":
            if args.approve_max_usd is None:
                raise AcquisitionError("authorize requires --approve-max-usd")
            if args.prior_session_estimate_usd is None:
                raise AcquisitionError("authorize requires --prior-session-estimate-usd")
            if args.combined_session_cap_usd is None:
                raise AcquisitionError("authorize requires --combined-session-cap-usd")
            packet = build_execution_authorization(
                plan=plan,
                approved_max_usd=args.approve_max_usd,
                prior_session_estimate_usd=args.prior_session_estimate_usd,
                combined_session_cap_usd=args.combined_session_cap_usd,
            )
            write_json_atomic(execution_path, packet)
            print(
                "CME6E_RAW_BREAK_AUTHORIZE "
                f"status={packet['status']} execution_id={packet['execution_id']} "
                f"plan_id={plan['plan_id']} approved_max_usd={packet['approved_max_usd']:.2f} "
                f"combined_cap_usd={packet['combined_session_cap_usd']:.2f}"
            )
            print(f"execution={execution_path}")
            return 0

        if not execution_path.is_file():
            raise AcquisitionError(f"execution authorization is absent: {execution_path}")
        execution = load_json(execution_path)
        validate_execution_authorization(execution, plan)
        if args.expected_execution_id != execution["execution_id"]:
            raise AcquisitionError(
                f"operation requires --expected-execution-id {execution['execution_id']}"
            )

        if args.action == "validate":
            receipt = validate_download(root, plan, execution)
            print(
                "CME6E_RAW_BREAK_VALIDATE "
                f"status={receipt['status']} files={receipt['response_files']} "
                f"nonempty={receipt['nonempty_files']} "
                f"source_empty={receipt['source_empty_files']} "
                f"metadata_empty={receipt['planned_metadata_empty_windows']} "
                f"records={receipt['decoded_records']} bytes={receipt['compressed_bytes']}"
            )
            print(f"receipt={root / RECEIPT_NAME}")
            return 0

        key = load_api_key()
        client = make_client(key)
        manifest = download_windows(
            client=client,
            plan=plan,
            execution=execution,
            root=root,
            metadata_client_factory=lambda: make_client(key),
            quote_workers=args.quote_workers,
        )
        print(
            "CME6E_RAW_BREAK_DOWNLOAD "
            f"status={manifest['status']} files={len(manifest['downloads'])} "
            f"nonempty={manifest['nonempty_files']} "
            f"source_empty={manifest['source_empty_files']} "
            f"live_estimate_usd={manifest['live_estimated_total_usd']:.12f} "
            f"combined_estimate_usd={manifest['combined_live_estimated_usd']:.12f}"
        )
        print(f"manifest={root / MANIFEST_NAME}")
        return 0
    except AcquisitionError as exc:
        print(f"CME6E_RAW_BREAK_ACQUISITION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
