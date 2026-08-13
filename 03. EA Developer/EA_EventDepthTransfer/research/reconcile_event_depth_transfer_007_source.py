#!/usr/bin/env python3
"""Reconcile complete source artifacts without network or outcome access."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-007"
ATTEMPT_ID = "EVENTDEPTHTRANSFER007-SOURCE-RECON-001"
BASE_REL = "03. EA Developer/EA_EventDepthTransfer/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_RECONCILIATION_PLAN.md"
AUTHORITY_REL = BASE_REL + HYPOTHESIS_ID + "_OWNER_AUTHORITY_RECONCILIATION.json"
TOOL_REL = BASE_REL + "reconcile_event_depth_transfer_007_source.py"
TEST_REL = BASE_REL + "tests/test_reconcile_event_depth_transfer_007_source.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
PARENT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004/"
    "EVENTDEPTHTRANSFER004-MBP10-DESIGN-001"
)
CHILD_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-005/"
    "EVENTDEPTHTRANSFER005-MBP10-CONTINUATION-001"
)
OUTPUT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PARENT_MANIFEST_SHA256 = "FD487BAB551F5C9C14002261DDA8B6C3BD7911F608E26C09A0A4DC83D93709FC"
CHILD_MANIFEST_SHA256 = "13693E3E291A5E5F85152FB42264E3BB8879D0595DEB5406C642FCE0AC7F248F"
CHILD_RECEIPT_SHA256 = "181A64D3DFD1806DB4877FF8559F9857E2020178D0576483FED2564C8A601249"
COMBINED_LEDGER_SHA256 = "4DE647CB8CC39F5CD26D10D844C11F1B5A493DAF7C69F2CB633AB361912326F0"
OWNER_VERBATIM_SHA256 = "6EC4AF3294B028D276DE20E44A35D79993D07D0BC462E566E0057F29A234BBBA"
AMBIGUOUS = {"EVT0258", "EVT0260", "EVT0261", "EVT0262", "EVT0263", "EVT0264", "EVT0265", "EVT0266"}
UNAVAILABLE = {"EVT0206", "EVT0228"}
INVALID = {"EVT0250"}


class ReconciliationError(RuntimeError):
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
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def contained(workspace: Path, path: Path, label: str) -> Path:
    root = workspace.resolve(); resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReconciliationError(f"{label} escapes workspace") from exc
    if root.drive.upper() != "D:" or resolved.drive.upper() != "D:":
        raise ReconciliationError(f"{label} must stay on D:")
    return resolved


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    if temp.exists():
        raise ReconciliationError("atomic temp collision")
    with temp.open("xb") as handle:
        handle.write(canonical_json(payload) + b"\n"); handle.flush(); os.fsync(handle.fileno())
    os.replace(temp, path)


def validate_authority(path: Path) -> dict[str, Any]:
    authority = json.loads(path.read_text(encoding="utf-8"))
    scope = authority.get("authority_scope", {})
    spend = authority.get("spend_reconciliation", {})
    if (
        authority.get("hypothesis_id") != HYPOTHESIS_ID
        or authority.get("owner_authorization_verbatim_sha256") != OWNER_VERBATIM_SHA256
        or scope.get("additional_spend_authorized") is not False
        or scope.get("artifact_integrity_reconciliation_authorized") is not True
        or scope.get("economic_use_after_reconciliation_authorized") is not True
        or scope.get("live_trading_authorized") is not False
        or float(spend.get("aggregate_worst_case_quoted_exposure_usd")) >= 10.0
    ):
        raise ReconciliationError("Owner authority reconciliation mismatch")
    return authority


def validate_registry(workspace: Path) -> dict[str, str]:
    paths = {"plan_sha256": workspace / PLAN_REL, "authority_sha256": workspace / AUTHORITY_REL,
             "tool_sha256": workspace / TOOL_REL, "test_sha256": workspace / TEST_REL}
    hashes = {key: sha256_file(contained(workspace, path, key)) for key, path in paths.items()}
    validate_authority(workspace / AUTHORITY_REL)
    registry = contained(workspace, workspace / REGISTRY_REL, "registry")
    matches = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append(row)
    if not matches:
        raise ReconciliationError("hypothesis absent from registry")
    row = matches[-1]; validation = row.get("validation", {})
    if (
        row.get("state") != "probe" or row.get("prereg_sha256") != hashes["plan_sha256"]
        or validation.get("source_reconciliation_authorized") is not True
        or validation.get("reviewed_tool_sha256") != hashes["tool_sha256"]
        or validation.get("reviewed_test_sha256") != hashes["test_sha256"]
        or validation.get("owner_authority_sha256") != hashes["authority_sha256"]
        or validation.get("network_authorized") is not False
        or validation.get("additional_spend_authorized") is not False
        or validation.get("outcome_prices_authorized") is not False
        or validation.get("economics_authorized") is not False
    ):
        raise ReconciliationError("registry reconciliation authority mismatch")
    return hashes


def load_inputs(workspace: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    parent_root = contained(workspace, workspace / PARENT_ROOT_REL, "parent root")
    child_root = contained(workspace, workspace / CHILD_ROOT_REL, "child root")
    parent_path = parent_root / "download_manifest.json"
    child_path = child_root / "download_manifest.json"
    receipt_path = child_root / "source_continuation_receipt.json"
    ledger_path = child_root / "combined_source_classification_ledger.jsonl"
    expected = ((parent_path, PARENT_MANIFEST_SHA256), (child_path, CHILD_MANIFEST_SHA256),
                (receipt_path, CHILD_RECEIPT_SHA256), (ledger_path, COMBINED_LEDGER_SHA256))
    for path, digest in expected:
        if sha256_file(path) != digest:
            raise ReconciliationError(f"input drift: {path.name}")
    parent = json.loads(parent_path.read_text(encoding="ascii"))
    child = json.loads(child_path.read_text(encoding="ascii"))
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    ledger = [json.loads(line) for line in ledger_path.read_text(encoding="ascii").splitlines()]
    return parent, child, receipt, ledger


def verify_complete(workspace: Path, item: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    if item.get("status") != "COMPLETE" or ledger.get("status") != "COMPLETE":
        raise ReconciliationError("non-complete row entered complete verifier")
    raw = contained(workspace, workspace / item["raw_path"], "raw")
    analysis = contained(workspace, workspace / item["analysis_path"], "analysis")
    if raw.suffix == ".partial" or ".partial" in raw.name:
        raise ReconciliationError("partial raw forbidden")
    if sha256_file(raw) != item["raw_sha256"] or item["raw_sha256"] != ledger["raw_sha256"]:
        raise ReconciliationError(f"raw hash mismatch: {ledger['event_clock_id']}")
    if sha256_file(analysis) != item["analysis_sha256"] or item["analysis_sha256"] != ledger["analysis_sha256"]:
        raise ReconciliationError(f"analysis hash mismatch: {ledger['event_clock_id']}")
    payload = json.loads(analysis.read_text(encoding="ascii"))
    if (
        payload.get("event_clock_id") != ledger["event_clock_id"]
        or int(payload.get("effective_direction")) != int(ledger["effective_direction"])
        or payload.get("effective_classification") != ledger["effective_classification"]
        or payload.get("outcome_prices_read") is not False
        or int(payload.get("returns_computed")) != 0
    ):
        raise ReconciliationError(f"analysis semantic mismatch: {ledger['event_clock_id']}")
    return {"raw_bytes": raw.stat().st_size,
            "source_records": int(payload["analysis"]["total_records"])}


def reconcile(workspace: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parent, child, receipt, ledger_rows = load_inputs(workspace)
    if receipt.get("outcome_prices_read") is not False or int(receipt.get("returns_computed")) != 0:
        raise ReconciliationError("child receipt opened outcomes")
    parent_complete = {item["event_clock_id"]: item for item in parent["entries"] if item["status"] == "COMPLETE"}
    child_complete = {item["event_clock_id"]: item for item in child["entries"] if item["status"] == "COMPLETE"}
    if len(parent_complete) != 256 or len(child_complete) != 63:
        raise ReconciliationError("complete manifest counts changed")
    if len(ledger_rows) != 329 or [row["event_clock_id"] for row in ledger_rows] != [f"EVT{i:04d}" for i in range(1, 330)]:
        raise ReconciliationError("combined ledger identity mismatch")
    verified_bytes = 0; verified_records = 0; clean: list[dict[str, Any]] = []
    for row in ledger_rows:
        event_id = row["event_clock_id"]
        if row["status"] == "COMPLETE":
            item = parent_complete.get(event_id) or child_complete.get(event_id)
            if item is None:
                raise ReconciliationError(f"complete event missing manifest: {event_id}")
            counts = verify_complete(workspace, item, row)
            verified_bytes += counts["raw_bytes"]; verified_records += counts["source_records"]
        elif event_id in AMBIGUOUS:
            if row["status"] != "SOURCE_AMBIGUOUS_FLAT" or row["effective_direction"] != 0:
                raise ReconciliationError("ambiguous event not frozen FLAT")
        elif event_id in UNAVAILABLE:
            if row["status"] != "SOURCE_UNAVAILABLE_FLAT" or row["effective_direction"] != 0:
                raise ReconciliationError("unavailable event not frozen FLAT")
        else:
            raise ReconciliationError(f"unexpected non-complete status: {event_id}")
        clean.append({"event_clock_id": event_id, "event_time_utc": row["event_time_utc"],
                      "source_status": row["status"],
                      "semantic_gate_pass": bool(row["semantic_gate_pass"]),
                      "classification": row["effective_classification"],
                      "direction": int(row["effective_direction"]),
                      "raw_sha256": row.get("raw_sha256"),
                      "analysis_sha256": row.get("analysis_sha256")})
    classes = Counter(row["classification"] for row in clean if row["semantic_gate_pass"])
    directions = Counter(row["direction"] for row in clean)
    gates = {"exact_319_complete": len(parent_complete) + len(child_complete) == 319,
             "exact_318_semantic_pass": sum(row["semantic_gate_pass"] for row in clean) == 318,
             "exact_classification_balance": classes == {"CONTINUATION": 146, "REVERSAL": 172},
             "exact_direction_balance": directions == {1: 162, -1: 156, 0: 11},
             "exact_8_ambiguous": sum(row["source_status"] == "SOURCE_AMBIGUOUS_FLAT" for row in clean) == 8,
             "exact_2_unavailable": sum(row["source_status"] == "SOURCE_UNAVAILABLE_FLAT" for row in clean) == 2,
             "exact_1_invalid": sum(row["classification"] == "SOURCE_INVALID_FLAT" for row in clean) == 1}
    summary = {"verified_complete_files": 319, "verified_raw_bytes": verified_bytes,
               "verified_source_records": verified_records,
               "classification_counts": dict(sorted(classes.items())),
               "direction_counts": {str(k): v for k, v in sorted(directions.items())},
               "gates": gates, "gate_pass": all(gates.values()),
               "verdict": "PASS_RECONCILED_SOURCE" if all(gates.values()) else "PARK_RECONCILIATION"}
    return clean, summary


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve(); bindings = validate_registry(workspace)
    clean, summary = reconcile(workspace)
    root = contained(workspace, workspace / OUTPUT_REL, "output root")
    if root.exists():
        raise ReconciliationError("exclusive reconciliation output exists")
    root.mkdir(parents=True, exist_ok=False)
    ledger_path = root / "reconciled_source_ledger.jsonl"
    with ledger_path.open("xb") as handle:
        for row in clean: handle.write(canonical_json(row) + b"\n")
        handle.flush(); os.fsync(handle.fileno())
    receipt_path = root / "source_reconciliation_receipt.json"
    receipt = {"schema_version": "event_depth_transfer_007_source_reconciliation.v1",
               "created_at_utc": utc_now(), "hypothesis_id": HYPOTHESIS_ID,
               "attempt_id": ATTEMPT_ID, "summary": summary,
               "input_bindings": {"parent_manifest_sha256": PARENT_MANIFEST_SHA256,
                                  "child_manifest_sha256": CHILD_MANIFEST_SHA256,
                                  "child_receipt_sha256": CHILD_RECEIPT_SHA256,
                                  "combined_ledger_sha256": COMBINED_LEDGER_SHA256,
                                  **bindings},
               "reconciled_ledger_path": str(ledger_path.relative_to(workspace)).replace("\\", "/"),
               "reconciled_ledger_sha256": sha256_file(ledger_path),
               "network_calls": 0, "additional_spend_usd": 0.0,
               "partial_files_read": 0, "outcome_prices_read": 0,
               "returns_computed": 0, "trades_simulated": 0,
               "economics_authorized": False, "mql5_authorized": False,
               "mt5_authorized": False, "validation_authorized": False,
               "holdout_authorized": False, "paper_trading_authorized": False,
               "live_trading_authorized": False, "market_edge_claim_authorized": False}
    write_json_atomic(receipt_path, receipt); return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        path = execute(args.workspace.resolve())
        receipt = json.loads(path.read_text(encoding="ascii"))
        print("EVENT_DEPTH_TRANSFER_007_RECONCILE_OK "
              f"files={receipt['summary']['verified_complete_files']} "
              f"verdict={receipt['summary']['verdict']}")
        print(f"RECEIPT {path}"); return 0
    except ReconciliationError as exc:
        print(f"EVENT_DEPTH_TRANSFER_007_RECONCILE_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

