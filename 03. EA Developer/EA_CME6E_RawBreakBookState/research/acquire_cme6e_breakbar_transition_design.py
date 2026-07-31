#!/usr/bin/env python3
"""Acquire the Owner-approved clock-correct CME 6E break-bar DESIGN corpus."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


WORKSPACE = Path(__file__).resolve().parents[3]
MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
DATA_ROOT = WORKSPACE / "02. AlphaFactory" / "data"
DEFAULT_ROOT = DATA_ROOT / "databento" / "cme_6e_breakbar_transition_design"
SOURCE_PLAN_PATH = DEFAULT_ROOT / "source_plan.json"
PLANNER_PATH = PACKAGE / "research" / "plan_cme6e_breakbar_transition_design.py"
BASE_ACQUISITION_PATH = PACKAGE / "research" / "acquire_cme6e_raw_break_design.py"

APPROVED_SOURCE_PLAN_ID = (
    "C57B0AF9CAAB52095629C4D6F3BE449EA23629E02F9FA30C4F54C5CC164A1D1C"
)
APPROVED_SOURCE_PLAN_SHA256 = (
    "BF478C4FF9B181E0BC7C38E55C9613D69B44DBF348CBC351EC0909583E25D7F6"
)
APPROVED_PLANNER_SHA256 = (
    "95AC16109B8F73261CB549155F65FB2543A933CEB1EB4BFD43410101FC515406"
)
BASE_ACQUISITION_SHA256 = (
    "9B5D942AAEF0F2C9FC0DEEED1E8227CFBBF6A27D08D8C797E059BF4BB61C4F27"
)
APPROVED_MAX_USD = 1.40
CANDIDATE_IDENTITY = "CME_GLOBEX_6E_MBP10_RAW_BREAK_BREAKBAR_TRANSITION"
SOURCE_PLAN_SCHEMA_VERSION = "cme6e_breakbar_transition_source_plan.v1"
EXECUTION_SCHEMA_VERSION = "cme6e_breakbar_transition_execution.v1"
MANIFEST_SCHEMA_VERSION = "cme6e_breakbar_transition_download_manifest.v1"
RECEIPT_SCHEMA_VERSION = "cme6e_breakbar_transition_validation_receipt.v1"
EXECUTION_NAME = "execution_authorization.json"
MANIFEST_NAME = "download_manifest.json"
RECEIPT_NAME = "validation_receipt.json"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_module(BASE_ACQUISITION_PATH, "raw_break_acquisition_foundation")
AcquisitionError = base.AcquisitionError
sha256_file = base.sha256_file


def _configure_foundation() -> None:
    base.SOURCE_PLAN_SCHEMA_VERSION = SOURCE_PLAN_SCHEMA_VERSION
    base.EXECUTION_SCHEMA_VERSION = EXECUTION_SCHEMA_VERSION
    base.MANIFEST_SCHEMA_VERSION = MANIFEST_SCHEMA_VERSION
    base.RECEIPT_SCHEMA_VERSION = RECEIPT_SCHEMA_VERSION
    base.CANDIDATE_IDENTITY = CANDIDATE_IDENTITY
    base.APPROVED_SOURCE_PLAN_ID = APPROVED_SOURCE_PLAN_ID
    base.APPROVED_SOURCE_PLAN_SHA256 = APPROVED_SOURCE_PLAN_SHA256
    base.APPROVED_PLANNER_SHA256 = APPROVED_PLANNER_SHA256
    base.APPROVED_MAX_USD = APPROVED_MAX_USD
    base.PRIOR_SESSION_ESTIMATE_USD = 0.0
    base.COMBINED_SESSION_CAP_USD = APPROVED_MAX_USD
    base.WORKSPACE = WORKSPACE
    base.MODULE_PATH = MODULE_PATH
    base.DATA_ROOT = DATA_ROOT
    base.DEFAULT_ROOT = DEFAULT_ROOT
    base.SOURCE_PLAN_PATH = SOURCE_PLAN_PATH
    base.PLANNER_PATH = PLANNER_PATH
    base.EXECUTION_NAME = EXECUTION_NAME
    base.MANIFEST_NAME = MANIFEST_NAME
    base.RECEIPT_NAME = RECEIPT_NAME


_configure_foundation()


def _load_planner_module():
    return _load_module(PLANNER_PATH, "breakbar_transition_planner")


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
    if sha256_file(BASE_ACQUISITION_PATH) != BASE_ACQUISITION_SHA256:
        raise AcquisitionError("borrowed acquisition foundation SHA mismatch")
    if plan.get("schema_version") != SOURCE_PLAN_SCHEMA_VERSION:
        raise AcquisitionError("source plan schema mismatch")
    if plan.get("plan_id") != APPROVED_SOURCE_PLAN_ID:
        raise AcquisitionError("source plan ID is not the Owner-approved plan")
    if plan.get("candidate_identity") != CANDIDATE_IDENTITY:
        raise AcquisitionError("source plan candidate mismatch")
    if plan.get("design_utc_years") != [2021, 2022]:
        raise AcquisitionError("source plan DESIGN years mismatch")
    if plan.get("paid_request_made") is not False:
        raise AcquisitionError("source plan reports a paid request")
    if plan.get("download_authorized") is not False:
        raise AcquisitionError("metadata source plan was mutated to authorize download")
    if plan.get("outcomes_opened") is not False:
        raise AcquisitionError("source plan reports opened outcomes")

    input_contract = plan.get("input")
    clock = plan.get("clock")
    prior = plan.get("prior_hypothesis")
    tool = plan.get("tool")
    quote = plan.get("quote_provenance")
    if not all(isinstance(item, dict) for item in (input_contract, clock, prior, tool, quote)):
        raise AcquisitionError("source plan provenance is incomplete")
    if input_contract.get("fields_used") != [
        "position_id",
        "decision_time",
        "open_time",
        "direction",
    ]:
        raise AcquisitionError("source plan identity/clock fields mismatch")
    if input_contract.get("outcome_fields_used") is not False:
        raise AcquisitionError("source plan is not outcome-blind")
    if prior.get("oos_opened_under_prior_id") is not False:
        raise AcquisitionError("source plan opened HYP-001 OOS")
    if tool.get("sha256") != APPROVED_PLANNER_SHA256:
        raise AcquisitionError("source plan planner SHA mismatch")
    if sha256_file(PLANNER_PATH) != APPROVED_PLANNER_SHA256:
        raise AcquisitionError("source planner changed after Owner approval")
    if quote.get("paid_request_made") is not False or quote.get("timeseries_calls") != 0:
        raise AcquisitionError("source quote provenance contains a paid call")

    _verify_bound_file(input_contract, "path", "sha256")
    _verify_bound_file(clock, "path", "sha256")
    _verify_bound_file(prior, "readout_path", "readout_sha256")
    try:
        _load_planner_module().validate_plan(plan)
    except Exception as exc:
        raise AcquisitionError(f"source plan hash validation failed: {exc}") from exc

    semantics = plan.get("clock_semantics")
    if not isinstance(semantics, dict):
        raise AcquisitionError("source plan clock semantics are absent")
    if semantics.get("feature_window_start_role") != "BREAK_BAR_OPEN":
        raise AcquisitionError("source plan start role mismatch")
    if semantics.get("feature_window_end_role") != "ACTUAL_NEXT_BAR_DECISION_ENTRY":
        raise AcquisitionError("source plan end role mismatch")
    if semantics.get("records_must_be_strictly_before_actual_decision") is not True:
        raise AcquisitionError("source plan causal cutoff is not strict")

    requests = plan.get("requests")
    metadata_empty = plan.get("metadata_empty_windows")
    quotes = plan.get("live_quotes")
    if not isinstance(requests, list) or len(requests) != 561:
        raise AcquisitionError("billable request coverage mismatch")
    if not isinstance(metadata_empty, list) or len(metadata_empty) != 4:
        raise AcquisitionError("metadata-empty coverage mismatch")
    if not isinstance(quotes, list) or len(quotes) != 565:
        raise AcquisitionError("metadata quote coverage mismatch")
    all_windows = requests + metadata_empty
    identities: set[tuple[str, str]] = set()
    for item in all_windows:
        if not isinstance(item, dict):
            raise AcquisitionError("source plan contains an invalid window")
        if item.get("direction") not in {"BUY", "SELL"}:
            raise AcquisitionError("source plan contains an invalid direction")
        if item.get("start") != item.get("break_bar_open"):
            raise AcquisitionError("source window does not begin at break-bar open")
        if item.get("end") != item.get("actual_decision"):
            raise AcquisitionError("source window does not end at actual decision")
        duration = int(item.get("duration_seconds", -1))
        if duration not in {300, 330}:
            raise AcquisitionError("source plan contains an invalid duration")
        start = datetime.fromisoformat(str(item["start"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(item["end"]).replace("Z", "+00:00"))
        if int((end - start).total_seconds()) != duration or end.year not in {2021, 2022}:
            raise AcquisitionError("source plan contains an invalid DESIGN window")
        identity = (str(item.get("position_id")), str(item.get("actual_decision")))
        if identity in identities:
            raise AcquisitionError("source plan contains a duplicate identity")
        identities.add(identity)

    by_quote = {str(item.get("position_id")): item for item in quotes}
    if len(by_quote) != 565 or set(by_quote) != {str(item["position_id"]) for item in all_windows}:
        raise AcquisitionError("metadata quotes do not cover source windows")
    request_ids = {str(item["position_id"]) for item in requests}
    empty_ids = {str(item["position_id"]) for item in metadata_empty}
    if any(int(by_quote[item]["billable_bytes"]) <= 0 for item in request_ids):
        raise AcquisitionError("billable source window lacks positive bytes")
    if any(int(by_quote[item]["billable_bytes"]) != 0 for item in empty_ids):
        raise AcquisitionError("metadata-empty classification mismatch")
    estimated_cost = sum(float(by_quote[item]["estimated_cost_usd"]) for item in request_ids)
    estimated_bytes = sum(int(by_quote[item]["billable_bytes"]) for item in request_ids)
    if not math.isclose(estimated_cost, float(plan["estimated_cost_usd"]), abs_tol=1e-12):
        raise AcquisitionError("source plan cost does not reconcile")
    if estimated_bytes != int(plan["estimated_billable_bytes"]):
        raise AcquisitionError("source plan billable bytes do not reconcile")
    if not math.isclose(float(plan["recommended_owner_ceiling_usd"]), APPROVED_MAX_USD):
        raise AcquisitionError("source plan recommended Owner ceiling mismatch")


def load_approved_source_plan() -> dict[str, Any]:
    if not SOURCE_PLAN_PATH.is_file():
        raise AcquisitionError(f"approved source plan is absent: {SOURCE_PLAN_PATH}")
    actual = sha256_file(SOURCE_PLAN_PATH)
    if actual != APPROVED_SOURCE_PLAN_SHA256:
        raise AcquisitionError(
            f"approved source plan SHA mismatch: expected {APPROVED_SOURCE_PLAN_SHA256}, got {actual}"
        )
    plan = base.load_json(SOURCE_PLAN_PATH)
    validate_approved_source_plan(plan)
    return plan


def build_execution_authorization(
    *, plan: dict[str, Any], approved_max_usd: float
) -> dict[str, Any]:
    validate_approved_source_plan(plan)
    if not math.isclose(approved_max_usd, APPROVED_MAX_USD, abs_tol=1e-12):
        raise AcquisitionError("execution packet must bind the Owner-approved USD1.40 ceiling")
    payload: dict[str, Any] = {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "created_at_utc": base.utc_now(),
        "status": "OWNER_APPROVED_SOURCE_PLAN_BOUND",
        "source_plan": {
            "path": str(SOURCE_PLAN_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "plan_id": APPROVED_SOURCE_PLAN_ID,
            "sha256": APPROVED_SOURCE_PLAN_SHA256,
        },
        "acquisition_tool": {
            "path": str(MODULE_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": sha256_file(MODULE_PATH),
        },
        "foundation_tool": {
            "path": str(BASE_ACQUISITION_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": BASE_ACQUISITION_SHA256,
        },
        "owner_authority": (
            "2026-07-27 explicit approval for plan C57B0AF9...64A1D1C up to USD1.40"
        ),
        "approved_max_usd": approved_max_usd,
        "prior_session_estimate_usd": 0.0,
        "combined_session_cap_usd": approved_max_usd,
        "projected_combined_estimate_usd": float(plan["estimated_cost_usd"]),
        "billable_design_windows": len(plan["requests"]),
        "metadata_empty_design_windows": len(plan["metadata_empty_windows"]),
        "prior_hypothesis_oos_opened": False,
        "sealed_oos_opened": False,
        "outcome_fields_used": False,
        "prohibitions": [
            "no live estimate above the Owner USD1.40 ceiling",
            "no estimate above the frozen internal two-times drift ceiling",
            "no automatic retry for an unresolved in-flight paid request",
            "no outcome join before source validation plus fresh registry/prereg SHA bind",
            "no HYP-001 amendment, old DESIGN shift, MQL5, Model 0, paper or live action",
        ],
    }
    payload["execution_id"] = base.execution_id(payload)
    validate_execution_authorization(payload, plan)
    return payload


def validate_execution_authorization(
    packet: dict[str, Any], plan: dict[str, Any]
) -> None:
    if packet.get("schema_version") != EXECUTION_SCHEMA_VERSION:
        raise AcquisitionError("execution authorization schema mismatch")
    source = packet.get("source_plan")
    tool = packet.get("acquisition_tool")
    foundation = packet.get("foundation_tool")
    if not all(isinstance(item, dict) for item in (source, tool, foundation)):
        raise AcquisitionError("execution authorization bindings are absent")
    if source.get("plan_id") != APPROVED_SOURCE_PLAN_ID:
        raise AcquisitionError("execution authorization plan ID mismatch")
    if source.get("sha256") != APPROVED_SOURCE_PLAN_SHA256:
        raise AcquisitionError("execution authorization plan SHA mismatch")
    if tool.get("sha256") != sha256_file(MODULE_PATH):
        raise AcquisitionError("execution authorization tool SHA mismatch")
    if foundation.get("sha256") != BASE_ACQUISITION_SHA256:
        raise AcquisitionError("execution authorization foundation SHA mismatch")
    if sha256_file(BASE_ACQUISITION_PATH) != BASE_ACQUISITION_SHA256:
        raise AcquisitionError("borrowed acquisition foundation changed")
    if not math.isclose(float(packet.get("approved_max_usd", -1)), APPROVED_MAX_USD):
        raise AcquisitionError("execution authorization USD1.40 ceiling mismatch")
    if not math.isclose(float(packet.get("prior_session_estimate_usd", -1)), 0.0):
        raise AcquisitionError("execution authorization prior estimate mismatch")
    if not math.isclose(
        float(packet.get("combined_session_cap_usd", -1)), APPROVED_MAX_USD
    ):
        raise AcquisitionError("execution authorization combined cap mismatch")
    if packet.get("prior_hypothesis_oos_opened") is not False:
        raise AcquisitionError("execution authorization opened HYP-001 OOS")
    if packet.get("outcome_fields_used") is not False:
        raise AcquisitionError("execution authorization is not outcome-blind")
    if packet.get("sealed_oos_opened") is not False:
        raise AcquisitionError("execution authorization opened outcomes")
    if packet.get("execution_id") != base.execution_id(packet):
        raise AcquisitionError("execution authorization hash mismatch")


base.validate_approved_source_plan = validate_approved_source_plan
base.validate_execution_authorization = validate_execution_authorization


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("authorize", "download", "validate"))
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--expected-source-plan-id")
    parser.add_argument("--expected-execution-id")
    parser.add_argument("--approve-max-usd", type=float)
    parser.add_argument("--quote-workers", type=int, default=16)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.expected_source_plan_id != APPROVED_SOURCE_PLAN_ID:
            raise AcquisitionError(
                f"operation requires --expected-source-plan-id {APPROVED_SOURCE_PLAN_ID}"
            )
        plan = load_approved_source_plan()
        root = base.ensure_output_root(args.root)
        execution_path = root / EXECUTION_NAME
        if args.action == "authorize":
            if args.approve_max_usd is None:
                raise AcquisitionError("authorize requires --approve-max-usd")
            packet = build_execution_authorization(
                plan=plan, approved_max_usd=args.approve_max_usd
            )
            base.write_json_atomic(execution_path, packet)
            print(
                "CME6E_BREAKBAR_AUTHORIZE "
                f"status={packet['status']} execution_id={packet['execution_id']} "
                f"plan_id={APPROVED_SOURCE_PLAN_ID} approved_max_usd={APPROVED_MAX_USD:.2f}"
            )
            print(f"execution={execution_path}")
            return 0

        if not execution_path.is_file():
            raise AcquisitionError(f"execution authorization is absent: {execution_path}")
        execution = base.load_json(execution_path)
        validate_execution_authorization(execution, plan)
        if args.expected_execution_id != execution["execution_id"]:
            raise AcquisitionError(
                f"operation requires --expected-execution-id {execution['execution_id']}"
            )

        if args.action == "validate":
            receipt = base.validate_download(root, plan, execution)
            print(
                "CME6E_BREAKBAR_VALIDATE "
                f"status={receipt['status']} files={receipt['response_files']} "
                f"nonempty={receipt['nonempty_files']} "
                f"source_empty={receipt['source_empty_files']} "
                f"metadata_empty={receipt['planned_metadata_empty_windows']} "
                f"records={receipt['decoded_records']} bytes={receipt['compressed_bytes']}"
            )
            print(f"receipt={root / RECEIPT_NAME}")
            return 0

        key = base.load_api_key()
        client = base.make_client(key)
        manifest = base.download_windows(
            client=client,
            plan=plan,
            execution=execution,
            root=root,
            metadata_client_factory=lambda: base.make_client(key),
            quote_workers=args.quote_workers,
        )
        print(
            "CME6E_BREAKBAR_DOWNLOAD "
            f"status={manifest['status']} files={len(manifest['downloads'])} "
            f"nonempty={manifest['nonempty_files']} "
            f"source_empty={manifest['source_empty_files']} "
            f"live_estimate_usd={manifest['live_estimated_total_usd']:.12f}"
        )
        print(f"manifest={root / MANIFEST_NAME}")
        return 0
    except AcquisitionError as exc:
        print(f"CME6E_BREAKBAR_ACQUISITION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
