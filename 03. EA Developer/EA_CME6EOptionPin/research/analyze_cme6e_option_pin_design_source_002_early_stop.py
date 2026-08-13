"""Prove the frozen HYP002 95% source gate impossible from acquired payloads."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-002"
CAMPAIGN_ID = "CME6EOPTPIN002-DESIGN-SOURCE-001"
ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_pit_definitions"
)
AUTHORITY_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    f"{HYPOTHESIS_ID}_PHASE_02_STATISTICS_AUTHORITY.json"
)
SOURCE_ANALYZER_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "analyze_cme6e_option_pin_design_source_002.py"
)
MANIFEST_FILE = "phase_02_statistics_manifest_pit.json"
REQUESTS_FILE = "design_statistics_request_plan_pit.jsonl"
CONTRACTS_FILE = "design_option_contract_catalog_pit.csv"
ANALYSIS_FILE = "design_source_early_stop_analysis_pit.json"
RECEIPT_FILE = "design_source_early_stop_receipt_pit.json"
FROZEN_EVENT_COUNT = 516
FROZEN_COVERAGE_GATE = 0.95
AUDIT_PREFIX_COUNT = 30


class EarlyStopError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="ascii",
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]


def minimum_invalid_for_impossible_gate(total: int, coverage_gate: float) -> int:
    if total <= 0 or not 0.0 < coverage_gate <= 1.0:
        raise ValueError("invalid frozen gate")
    minimum_valid = math.ceil(total * coverage_gate)
    return total - minimum_valid + 1


def load_bound_source_analyzer(workspace: Path, authority: dict[str, Any]) -> Any:
    path = (workspace / SOURCE_ANALYZER_REL).resolve()
    path.relative_to(workspace)
    expected = str(authority.get("strict_analyzer_sha256", "")).upper()
    if not path.is_file() or sha256_file(path) != expected:
        raise EarlyStopError("authority-bound strict source analyzer drifted")
    spec = importlib.util.spec_from_file_location("hyp002_bound_source_analyzer", path)
    if spec is None or spec.loader is None:
        raise EarlyStopError("cannot load authority-bound strict source analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / ROOT_REL).resolve()
    root.relative_to(workspace)
    authority_path = (workspace / AUTHORITY_REL).resolve()
    manifest_path = root / MANIFEST_FILE
    requests_path = root / REQUESTS_FILE
    contracts_path = root / CONTRACTS_FILE
    for path in (authority_path, manifest_path, requests_path, contracts_path):
        if not path.is_file():
            raise EarlyStopError(f"missing required evidence: {path.name}")

    authority = json.loads(authority_path.read_text(encoding="ascii"))
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if (
        authority.get("hypothesis_id") != HYPOTHESIS_ID
        or authority.get("campaign_id") != CAMPAIGN_ID
        or authority.get("frozen_request_count") != FROZEN_EVENT_COUNT
        or authority.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
        or authority.get("automatic_retry_authorized") is not False
        or authority.get("target_or_outcome_authorized") is not False
    ):
        raise EarlyStopError("HYP002 authority is not the frozen source-only contract")
    if (
        manifest.get("hypothesis_id") != HYPOTHESIS_ID
        or manifest.get("campaign_id") != CAMPAIGN_ID
        or manifest.get("authorized_timeseries_calls") != FROZEN_EVENT_COUNT
        or manifest.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
        or manifest.get("automatic_retry_authorized") is not False
        or manifest.get("target_price_fields_used") != []
        or manifest.get("outcome_fields_used") != []
    ):
        raise EarlyStopError("in-flight manifest drifted from frozen source contract")

    requests = load_jsonl(requests_path)
    request_by_id = {row["request_id"]: row for row in requests}
    if len(requests) != FROZEN_EVENT_COUNT or len(request_by_id) != FROZEN_EVENT_COUNT:
        raise EarlyStopError("frozen request population is not 516 unique events")
    payloads = list(manifest.get("payloads", []))
    if len(payloads) < AUDIT_PREFIX_COUNT:
        raise EarlyStopError("fewer than 30 completed payloads; cannot prove early stop")
    selected = payloads[:AUDIT_PREFIX_COUNT]

    bound_analyzer = load_bound_source_analyzer(workspace, authority)
    contracts = pd.read_csv(contracts_path, dtype={"raw_symbol": str, "asset": str})
    import databento as db

    audited: list[dict[str, Any]] = []
    selected_payloads: list[dict[str, Any]] = []
    for ordinal, payload in enumerate(selected):
        request_id = str(payload["request_id"])
        request = request_by_id.get(request_id)
        if request is None:
            raise EarlyStopError(f"unknown request in manifest prefix: {request_id}")
        raw_path = (workspace / payload["path"]).resolve()
        raw_path.relative_to(workspace)
        actual_sha = sha256_file(raw_path) if raw_path.is_file() else ""
        if actual_sha != str(payload.get("raw_sha256", "")).upper():
            raise EarlyStopError(f"payload hash drift: {request_id}")
        event_contracts = contracts[
            (contracts["asset"] == request["asset"])
            & (contracts["underlying"] == request["underlying"])
            & (contracts["expiration_utc"] == request["expiration_utc"])
        ].copy()
        statistics = db.DBNStore.from_file(raw_path).to_df().reset_index()
        result, _ = bound_analyzer.analyze_event(request, statistics, event_contracts)
        audited.append(
            {
                "acquisition_ordinal": ordinal,
                "event_id": result["event_id"],
                "request_id": request_id,
                "definition_count": result["definition_count"],
                "published_oi_count": result["published_oi_count"],
                "missing_oi_count": result["missing_oi_count"],
                "definition_coverage": result["definition_coverage"],
                "post_decision_rows": result["post_decision_rows"],
                "unresolved_alias_rows": result["unresolved_alias_rows"],
                "oi_delete_rows": result["oi_delete_rows"],
                "source_valid": result["source_valid"],
            }
        )
        selected_payloads.append(
            {
                "acquisition_ordinal": ordinal,
                "request_id": request_id,
                "path": payload["path"],
                "raw_sha256": actual_sha,
            }
        )

    invalid_count = sum(not row["source_valid"] for row in audited)
    unknown_oi_count = sum(row["missing_oi_count"] > 0 for row in audited)
    minimum_invalid = minimum_invalid_for_impossible_gate(
        FROZEN_EVENT_COUNT, FROZEN_COVERAGE_GATE
    )
    maximum_possible_valid = FROZEN_EVENT_COUNT - invalid_count
    maximum_possible_coverage = maximum_possible_valid / FROZEN_EVENT_COUNT
    verdict = (
        "KILL_SOURCE_DESIGN_EARLY_MATHEMATICAL"
        if invalid_count >= minimum_invalid
        and maximum_possible_coverage < FROZEN_COVERAGE_GATE
        else "EARLY_STOP_NOT_PROVEN"
    )

    partial_files = []
    for path in sorted((root / "phase_02_statistics_raw").glob("*.partial")):
        partial_files.append(
            {
                "path": str(path.relative_to(workspace)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    report = {
        "schema_version": "cme6e_option_pin_design_source_early_stop.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "proof": {
            "frozen_event_count": FROZEN_EVENT_COUNT,
            "frozen_source_valid_coverage_gate": FROZEN_COVERAGE_GATE,
            "minimum_invalid_events_for_impossible_gate": minimum_invalid,
            "audited_manifest_prefix_count": len(audited),
            "audited_source_valid_events": len(audited) - invalid_count,
            "audited_invalid_events": invalid_count,
            "audited_events_with_unknown_oi": unknown_oi_count,
            "maximum_possible_valid_events_if_all_unaudited_pass": maximum_possible_valid,
            "maximum_possible_coverage_if_all_unaudited_pass": maximum_possible_coverage,
        },
        "acquisition": {
            "manifest_status_at_stop": manifest.get("status"),
            "completed_timeseries_calls_at_stop": manifest.get("timeseries_calls"),
            "completed_payloads_at_stop": len(payloads),
            "automatic_retry_authorized": False,
            "partial_resume_authorized": False,
            "partial_files_preserved": partial_files,
        },
        "audited_events": audited,
        "selected_payloads": selected_payloads,
        "bindings": {
            "authority_sha256": sha256_file(authority_path),
            "manifest_sha256_at_stop": sha256_file(manifest_path),
            "requests_sha256": sha256_file(requests_path),
            "contracts_sha256": sha256_file(contracts_path),
            "bound_strict_analyzer_sha256": sha256_file(
                workspace / SOURCE_ANALYZER_REL
            ),
        },
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economic_verdict": "NOT_OPENED",
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    report_path = root / ANALYSIS_FILE
    write_json(report_path, report)
    receipt = {
        "schema_version": "cme6e_option_pin_design_source_early_stop_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "audited_invalid_events": invalid_count,
        "minimum_invalid_events_for_impossible_gate": minimum_invalid,
        "maximum_possible_coverage": maximum_possible_coverage,
        "completed_payloads_at_stop": len(payloads),
        "analysis_path": str(report_path.relative_to(workspace)).replace("\\", "/"),
        "analysis_sha256": sha256_file(report_path),
        "analyzer_path": str(Path(__file__).resolve().relative_to(workspace)).replace(
            "\\", "/"
        ),
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "bound_strict_analyzer_sha256": sha256_file(workspace / SOURCE_ANALYZER_REL),
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economic_verdict": "NOT_OPENED",
    }
    receipt_path = root / RECEIPT_FILE
    write_json(receipt_path, receipt)
    return receipt_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        receipt_path = execute(args.workspace)
        receipt = json.loads(receipt_path.read_text(encoding="ascii"))
        print(
            f"CME6EOPTPIN002_{receipt['verdict']} "
            f"invalid={receipt['audited_invalid_events']} "
            f"min_invalid={receipt['minimum_invalid_events_for_impossible_gate']} "
            f"max_coverage={receipt['maximum_possible_coverage']:.6f} "
            f"receipt={receipt_path}"
        )
        return 3 if receipt["verdict"].startswith("KILL_") else 2
    except (EarlyStopError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"CME6EOPTPIN002_EARLY_STOP_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
