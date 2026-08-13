"""Fail-only audit for an abruptly terminated HYP002 statistics acquisition.

This audit can never pass the source design from a partial acquisition.  It may
only prove that the frozen 95% source-validity gate is already impossible, even
if every unacquired event were valid.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-002"
CAMPAIGN_ID = "CME6EOPTPIN002-DESIGN-SOURCE-001"
ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_pit_definitions"
)
ANALYZER_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "analyze_cme6e_option_pin_design_source_002.py"
)
MANIFEST_FILE = "phase_02_statistics_manifest_pit.json"
REQUESTS_FILE = "design_statistics_request_plan_pit.jsonl"
CONTRACTS_FILE = "design_option_contract_catalog_pit.csv"
ACQUISITION_RECEIPT = "phase_02_statistics_acquisition_receipt_pit.json"
AUDIT_FILE = "design_source_partial_monotonic_audit_pit.json"
TERMINAL_RECEIPT = "phase_02_statistics_terminal_receipt_pit.json"
SOURCE_VALIDITY_THRESHOLD = 0.95


class PartialAuditError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    os.replace(temporary, path)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]


def load_analyzer(workspace: Path):
    path = (workspace / ANALYZER_REL).resolve()
    try:
        path.relative_to(workspace)
    except ValueError as exc:
        raise PartialAuditError("analyzer escaped workspace") from exc
    spec = importlib.util.spec_from_file_location("option_pin_source_002", path)
    if spec is None or spec.loader is None:
        raise PartialAuditError("cannot load frozen HYP002 analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def monotonic_verdict(
    *, planned_events: int, acquired_events: int, invalid_acquired_events: int
) -> dict[str, Any]:
    if not 0 <= invalid_acquired_events <= acquired_events <= planned_events:
        raise PartialAuditError("invalid event counts")
    required_valid_events = math.ceil(
        SOURCE_VALIDITY_THRESHOLD * planned_events - 1e-12
    )
    maximum_invalid_events = planned_events - required_valid_events
    best_case_valid_events = planned_events - invalid_acquired_events
    impossible = best_case_valid_events < required_valid_events
    return {
        "required_valid_events": required_valid_events,
        "maximum_invalid_events": maximum_invalid_events,
        "best_case_valid_events_if_all_remaining_pass": best_case_valid_events,
        "source_validity_gate_mathematically_impossible": impossible,
        "verdict": (
            "KILL_SOURCE_DESIGN_MONOTONIC_PARTIAL"
            if impossible
            else "ACQUISITION_INCOMPLETE_NO_SOURCE_VERDICT"
        ),
    }


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise PartialAuditError("HYP002 root escaped workspace") from exc

    manifest_path = root / MANIFEST_FILE
    requests_path = root / REQUESTS_FILE
    contracts_path = root / CONTRACTS_FILE
    acquisition_receipt_path = root / ACQUISITION_RECEIPT
    if not all(path.is_file() for path in (manifest_path, requests_path, contracts_path)):
        raise PartialAuditError("required partial-acquisition evidence is missing")
    if acquisition_receipt_path.exists():
        raise PartialAuditError("complete acquisition receipt exists; partial audit forbidden")

    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if manifest.get("status") != "IN_FLIGHT" or manifest.get("failure_type"):
        raise PartialAuditError("manifest is not an abruptly stopped in-flight acquisition")
    requests = load_jsonl(requests_path)
    request_by_id = {str(row["request_id"]): row for row in requests}
    payloads = list(manifest.get("payloads", []))
    payload_by_id = {str(row["request_id"]): row for row in payloads}
    if len(request_by_id) != int(manifest.get("authorized_timeseries_calls", -1)):
        raise PartialAuditError("planned request count drifted")
    if len(payload_by_id) != len(payloads):
        raise PartialAuditError("duplicate payload request IDs")
    if not set(payload_by_id).issubset(request_by_id):
        raise PartialAuditError("payload identity escaped frozen request plan")
    if int(manifest.get("timeseries_calls", -1)) != len(payloads):
        raise PartialAuditError("call/payload count mismatch")

    analyzer, analyzer_path = load_analyzer(workspace)
    contracts = pd.read_csv(contracts_path, dtype={"raw_symbol": str, "asset": str})
    import databento as db

    results: list[dict[str, Any]] = []
    for request_id in sorted(payload_by_id):
        request = request_by_id[request_id]
        payload = payload_by_id[request_id]
        path = (workspace / payload["path"]).resolve()
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise PartialAuditError("payload escaped workspace") from exc
        if not path.is_file() or sha256_file(path) != payload.get("raw_sha256"):
            raise PartialAuditError(f"payload drift: {request_id}")
        event_contracts = contracts[
            (contracts["asset"] == request["asset"])
            & (contracts["underlying"] == request["underlying"])
            & (contracts["expiration_utc"] == request["expiration_utc"])
        ].copy()
        if event_contracts.empty:
            raise PartialAuditError(f"empty event catalog: {request_id}")
        statistics = db.DBNStore.from_file(path).to_df().reset_index()
        result, _ = analyzer.analyze_event(request, statistics, event_contracts)
        results.append(result)

    invalid = sum(not bool(row["source_valid"]) for row in results)
    arithmetic = monotonic_verdict(
        planned_events=len(requests),
        acquired_events=len(results),
        invalid_acquired_events=invalid,
    )
    unknown = sum(int(row["missing_oi_count"] > 0) for row in results)
    strict_valid = len(results) - invalid
    audit = {
        "schema_version": "cme6e_option_pin_partial_monotonic_audit.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": arithmetic["verdict"],
        "pass_from_partial_data_forbidden": True,
        "retry_or_resume_authorized": False,
        "economic_fields_used": [],
        "target_price_fields_used": [],
        "counts": {
            "planned_events": len(requests),
            "acquired_events": len(results),
            "unacquired_events": len(requests) - len(results),
            "source_valid_acquired_events": strict_valid,
            "source_invalid_acquired_events": invalid,
            "acquired_events_with_unknown_oi": unknown,
            **{key: value for key, value in arithmetic.items() if key != "verdict"},
        },
        "bindings": {
            "manifest_sha256": sha256_file(manifest_path),
            "requests_sha256": sha256_file(requests_path),
            "contracts_sha256": sha256_file(contracts_path),
            "analyzer_sha256": sha256_file(analyzer_path),
            "payload_sha256": sorted(str(row["raw_sha256"]) for row in payloads),
        },
        "source_threshold": SOURCE_VALIDITY_THRESHOLD,
        "interpretation": (
            "Partial evidence may only kill the frozen source gate when its "
            "best-case completion cannot reach 95%; it can never pass it."
        ),
    }
    audit_path = root / AUDIT_FILE
    write_json(audit_path, audit)
    terminal = {
        "schema_version": "cme6e_option_pin_statistics_terminal_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "acquisition_status": "ABRUPT_TERMINATION_MANIFEST_LEFT_IN_FLIGHT",
        "observed_timeseries_calls": int(manifest["timeseries_calls"]),
        "observed_payloads": len(payloads),
        "failed_request_id": manifest.get("failed_request_id"),
        "failure_type": manifest.get("failure_type"),
        "retry_or_resume_authorized": False,
        "source_verdict": arithmetic["verdict"],
        "audit_path": str(audit_path.relative_to(workspace)).replace("\\", "/"),
        "audit_sha256": sha256_file(audit_path),
        "economic_verdict": "NOT_OPENED",
        "mql5_authorized": False,
        "mt5_authorized": False,
        "paper_or_live_authorized": False,
    }
    terminal_path = root / TERMINAL_RECEIPT
    write_json(terminal_path, terminal)
    return terminal_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        path = execute(args.workspace)
        receipt = json.loads(path.read_text(encoding="ascii"))
        print(
            "CME6EOPTPIN002_PARTIAL_SOURCE_AUDIT "
            f"calls={receipt['observed_timeseries_calls']} "
            f"verdict={receipt['source_verdict']}"
        )
        print(f"RECEIPT {path}")
        return 3 if receipt["source_verdict"].startswith("KILL_") else 4
    except PartialAuditError as exc:
        print(f"CME6EOPTPIN002_PARTIAL_AUDIT_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
