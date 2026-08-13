"""Discover HYP002 CME 6E option-pin events with point-in-time definitions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-002"
CAMPAIGN_ID = "CME6EOPTPIN002-DESIGN-SOURCE-001"
PARENT_HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
PARENT_CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-SOURCE-001"
PARENT_ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{PARENT_HYPOTHESIS_ID}/{PARENT_CAMPAIGN_ID}/"
    "phase_01_definitions_batch_r2"
)
OUTPUT_ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_pit_definitions"
)
PARENT_RECEIPT = "phase_01_batch_acquisition_receipt.json"
PARENT_RECEIPT_SHA256 = (
    "4073034E075CF32EA96FBB44CF71A30DDFCDE825982F47D8F6B261C670E41E25"
)
PREREG_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-002_SOURCE_PREREG.md"
)
PREREG_SHA256 = (
    "0C1999109572622BF579EE2B4233BA77CBA6A73E1516D7B648AC77EC92209B86"
)
PARENT_KILL_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_SOURCE_CONTRACT_KILL.md"
)
PARENT_KILL_SHA256 = (
    "0134ABA109D3B17B9C89605C4463F1342C6961853BCAC0D60E4E3B697B3F3F44"
)

CONTRACTS_FILE = "design_option_contract_catalog_pit.csv"
EVENTS_FILE = "design_expiry_events_pit.csv"
COLLISIONS_FILE = "design_overlap_collisions_pit.csv"
REQUESTS_FILE = "design_statistics_request_plan_pit.jsonl"
ANALYSIS_FILE = "design_definition_discovery_analysis_pit.json"
RESULT_FILE = "design_definition_discovery_receipt_pit.json"

BASE_PATH = Path(__file__).with_name("discover_cme6e_option_pin_design_events.py")
BASE_SPEC = importlib.util.spec_from_file_location("cme6e_option_pin_base", BASE_PATH)
if BASE_SPEC is None or BASE_SPEC.loader is None:
    raise RuntimeError("unable to load reviewed HYP001 discovery helpers")
base = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(base)


class DiscoveryError(RuntimeError):
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


def iso_utc(value: Any) -> str:
    return pd.Timestamp(value).isoformat().replace("+00:00", "Z")


def stable_contracts_pit(
    rows: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    semantic = ["instrument_class", "underlying", "asset", "strike_price"]
    stable_parts: list[pd.DataFrame] = []
    unstable: list[str] = []
    unavailable: list[str] = []
    revised: list[str] = []
    multiple_fixed_points: list[str] = []

    for raw_symbol, group in rows.groupby("raw_symbol", sort=False):
        working = group.copy()
        working["decision"] = working["expiration"] - pd.Timedelta(minutes=15)
        fixed_points: list[tuple[pd.Timestamp, pd.Series, pd.DataFrame]] = []
        candidate_decisions = sorted(
            pd.Timestamp(value) for value in working["decision"].unique()
        )
        for candidate_decision in candidate_decisions:
            knowable = working[
                (working["ts_event"] < candidate_decision)
                & (working["ts_recv"] < candidate_decision)
            ].copy()
            if knowable.empty:
                continue
            active = knowable.sort_values(
                ["ts_recv", "ts_event"], kind="stable"
            ).iloc[-1]
            active_decision = pd.Timestamp(active["expiration"]) - pd.Timedelta(
                minutes=15
            )
            if active_decision == candidate_decision:
                fixed_points.append((candidate_decision, active, knowable))

        if not fixed_points:
            unavailable.append(str(raw_symbol))
            continue
        if len(fixed_points) > 1:
            multiple_fixed_points.append(str(raw_symbol))
        selected_decision, latest, knowable = fixed_points[0]
        if any(knowable[column].nunique(dropna=False) != 1 for column in semantic):
            unstable.append(str(raw_symbol))
            continue
        if knowable["expiration"].nunique(dropna=False) > 1:
            revised.append(str(raw_symbol))
        selected_expiration = pd.Timestamp(latest["expiration"])
        if not (
            pd.Timestamp(latest["ts_event"]) < selected_decision
            and pd.Timestamp(latest["ts_recv"]) < selected_decision
            and selected_expiration - pd.Timedelta(minutes=15) == selected_decision
        ):
            raise DiscoveryError("selected definition violates PIT invariant")

        selected_history = knowable[
            knowable["expiration"] == selected_expiration
        ]
        for instrument_id in sorted(selected_history["instrument_id"].unique()):
            row = latest.copy()
            row["instrument_id"] = instrument_id
            stable_parts.append(row.to_frame().T)

    if not stable_parts:
        raise DiscoveryError("no point-in-time definitions survived")
    stable = pd.concat(stable_parts, ignore_index=True)
    stable["instrument_id"] = pd.to_numeric(stable["instrument_id"]).astype("uint32")
    stable["strike_price"] = pd.to_numeric(stable["strike_price"])
    stable["expiration"] = pd.to_datetime(stable["expiration"], utc=True)
    stable["ts_event"] = pd.to_datetime(stable["ts_event"], utc=True)
    stable["ts_recv"] = pd.to_datetime(stable["ts_recv"], utc=True)
    selected_decision = stable["expiration"] - pd.Timedelta(minutes=15)
    post_decision = int(
        (
            (stable["ts_event"] >= selected_decision)
            | (stable["ts_recv"] >= selected_decision)
        ).sum()
    )
    if post_decision != 0:
        raise DiscoveryError("nonzero post-decision selected definitions")

    audit = {
        "input_distinct_raw_symbols": int(rows["raw_symbol"].nunique()),
        "selected_distinct_raw_symbols": int(stable["raw_symbol"].nunique()),
        "selected_distinct_rows": int(len(stable)),
        "symbols_without_predecision_definition_count": len(unavailable),
        "symbols_without_predecision_definition": sorted(unavailable),
        "unstable_predecision_symbol_count": len(unstable),
        "unstable_predecision_symbols": sorted(unstable),
        "predecision_expiration_revision_symbol_count": len(revised),
        "predecision_expiration_revision_symbols": sorted(revised),
        "multiple_fixed_point_symbol_count": len(multiple_fixed_points),
        "multiple_fixed_point_symbols": sorted(multiple_fixed_points),
        "selected_definition_post_decision_count": post_decision,
    }
    return stable, audit


def load_contracts_pit(
    payload_paths: list[Path],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    import databento as db

    parts: list[pd.DataFrame] = []
    raw_rows = 0
    relevant_delete_rows = 0
    for path in sorted(payload_paths):
        frame = db.DBNStore.from_file(path).to_df().reset_index()
        raw_rows += len(frame)
        relevant_delete_rows += int(
            (
                (frame["security_update_action"] == "D")
                & frame["instrument_class"].isin(["C", "P"])
                & frame["asset"].isin(base.ASSETS)
                & frame["underlying"].astype(str).str.startswith("6E")
            ).sum()
        )
        part = base.eligible_contract_rows(frame)
        if not part.empty:
            parts.append(part)
    if not parts:
        raise DiscoveryError("no eligible definitions in parent payloads")
    rows = pd.concat(parts, ignore_index=True).drop_duplicates()
    stable, audit = stable_contracts_pit(rows)
    counters = {
        "payload_file_count": len(payload_paths),
        "raw_definition_rows": int(raw_rows),
        "eligible_distinct_rows": int(len(rows)),
        "relevant_delete_rows": relevant_delete_rows,
        **audit,
    }
    return stable, counters


def write_contracts_pit(path: Path, contracts: pd.DataFrame) -> None:
    columns = [
        "raw_symbol",
        "asset",
        "family",
        "underlying",
        "expiration_utc",
        "decision_utc",
        "selected_def_ts_event",
        "selected_def_ts_recv",
        "instrument_class",
        "strike_price",
        "instrument_ids",
    ]
    records: list[dict[str, Any]] = []
    for raw_symbol, group in contracts.groupby("raw_symbol", sort=True):
        row = group.iloc[0]
        expiration = pd.Timestamp(row["expiration"])
        records.append(
            {
                "raw_symbol": str(raw_symbol),
                "asset": str(row["asset"]),
                "family": base.ASSETS[str(row["asset"])],
                "underlying": str(row["underlying"]),
                "expiration_utc": iso_utc(expiration),
                "decision_utc": iso_utc(expiration - pd.Timedelta(minutes=15)),
                "selected_def_ts_event": iso_utc(row["ts_event"]),
                "selected_def_ts_recv": iso_utc(row["ts_recv"]),
                "instrument_class": str(row["instrument_class"]),
                "strike_price": f"{float(row['strike_price']):.10f}",
                "instrument_ids": ";".join(
                    str(int(value)) for value in sorted(group["instrument_id"].unique())
                ),
            }
        )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    os.replace(temporary, path)


def statistics_requests_pit(events: pd.DataFrame) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for row in events.sort_values(
        ["decision_utc", "parent", "event_id"], kind="stable"
    ).itertuples(index=False):
        decision = pd.Timestamp(row.decision_utc)
        start = decision.normalize()
        request_key = (
            f"{HYPOTHESIS_ID}|{row.parent}|{iso_utc(start)}|{iso_utc(decision)}"
        )
        request_id = hashlib.sha256(request_key.encode("ascii")).hexdigest()[:16].upper()
        requests.append(
            {
                "schema_version": "cme6e_option_pin_statistics_request.v2",
                "hypothesis_id": HYPOTHESIS_ID,
                "campaign_id": CAMPAIGN_ID,
                "request_id": request_id,
                "event_id": row.event_id,
                "dataset": "GLBX.MDP3",
                "schema": "statistics",
                "symbols": [row.parent],
                "stype_in": "parent",
                "stype_out": "instrument_id",
                "start": iso_utc(start),
                "end": iso_utc(decision),
                "asset": row.asset,
                "underlying": row.underlying,
                "expiration_utc": iso_utc(row.expiration_utc),
                "decision_utc": iso_utc(decision),
                "required_oi_reference_utc": iso_utc(
                    start - pd.Timedelta(days=1)
                ),
                "definition_selection": "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT",
                "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
            }
        )
    ids = [request["request_id"] for request in requests]
    if len(ids) != len(set(ids)):
        raise DiscoveryError("duplicate HYP002 statistics request ID")
    return requests


def write_requests(path: Path, requests: Iterable[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as handle:
        for request in requests:
            handle.write(json.dumps(request, sort_keys=True, ensure_ascii=True) + "\n")
    os.replace(temporary, path)


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    parent_root = (workspace / PARENT_ROOT_REL).resolve()
    output_root = (workspace / OUTPUT_ROOT_REL).resolve()
    prereg_path = (workspace / PREREG_REL).resolve()
    kill_path = (workspace / PARENT_KILL_REL).resolve()
    for path in (parent_root, output_root, prereg_path, kill_path):
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise DiscoveryError("source path escaped workspace") from exc

    receipt_path = parent_root / PARENT_RECEIPT
    if (
        not receipt_path.is_file()
        or sha256_file(receipt_path) != PARENT_RECEIPT_SHA256
        or not prereg_path.is_file()
        or sha256_file(prereg_path) != PREREG_SHA256
        or not kill_path.is_file()
        or sha256_file(kill_path) != PARENT_KILL_SHA256
    ):
        raise DiscoveryError("parent receipt or HYP002 authority binding drifted")
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    if (
        receipt.get("hypothesis_id") != PARENT_HYPOTHESIS_ID
        or receipt.get("campaign_id") != PARENT_CAMPAIGN_ID
        or receipt.get("target_price_fields_used") != []
        or receipt.get("outcome_fields_used") != []
    ):
        raise DiscoveryError("parent phase-01 receipt contract mismatch")

    payload_paths: list[Path] = []
    payload_hashes: list[str] = []
    for payload in receipt.get("payloads", []):
        path = (workspace / str(payload.get("path", ""))).resolve()
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise DiscoveryError("parent payload escaped workspace") from exc
        expected = str(payload.get("raw_sha256", ""))
        if not path.is_file() or sha256_file(path) != expected:
            raise DiscoveryError("parent definition payload missing or drifted")
        payload_paths.append(path)
        payload_hashes.append(expected)
    if len(payload_paths) != 60:
        raise DiscoveryError("expected exactly 60 parent definition payloads")

    output_root.mkdir(parents=True, exist_ok=True)
    contracts, definition_counts = load_contracts_pit(payload_paths)
    events, collisions, collision_counts = base.discover_events(contracts)
    eligible = base.eligible_events(events)
    requests = statistics_requests_pit(eligible)

    contracts_path = output_root / CONTRACTS_FILE
    events_path = output_root / EVENTS_FILE
    collisions_path = output_root / COLLISIONS_FILE
    requests_path = output_root / REQUESTS_FILE
    write_contracts_pit(contracts_path, contracts)
    base.write_events(events_path, events)
    base.write_events(collisions_path, collisions)
    write_requests(requests_path, requests)

    expiry_months = {
        pd.Timestamp(value).strftime("%Y-%m") for value in events["expiration_utc"]
    }
    expected_months = set(
        pd.period_range("2018-01", "2022-12", freq="M").astype(str)
    )
    gates = {
        "definition_payloads_hash_bound": True,
        "zero_selected_definition_rows_at_or_after_decision": (
            definition_counts["selected_definition_post_decision_count"] == 0
        ),
        "zero_unstable_predecision_symbols": (
            definition_counts["unstable_predecision_symbol_count"] == 0
        ),
        "zero_relevant_delete_rows": definition_counts["relevant_delete_rows"] == 0,
        "no_design_month_empty_of_definitions": expected_months.issubset(
            expiry_months
        ),
        "potential_nonoverlap_event_count_at_least_90": int(len(eligible)) >= 90,
        "statistics_requests_freeze_missing_oi_as_unknown": all(
            request["missing_oi_policy"] == "UNKNOWN_EVENT_INVALID"
            for request in requests
        ),
        "target_and_outcome_fields_absent": True,
    }
    verdict = "PHASE_01_PASS" if all(gates.values()) else "KILL_SOURCE_DESIGN"
    report = {
        "schema_version": "cme6e_option_pin_design_definition_discovery.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "verdict": verdict,
        "gates": gates,
        "definition_counts": definition_counts,
        "event_counts": {
            "discovered_events": int(len(events)),
            "eligible_nonoverlap_events": int(len(eligible)),
            "events_without_call_and_put": int((~events["has_call_and_put"]).sum()),
            "clock_mismatches": int((~events["clock_valid"]).sum()),
            "non_m15_decisions": int((~events["m15_boundary"]).sum()),
            "design_expiry_months": len(expiry_months.intersection(expected_months)),
            "statistics_request_count": len(requests),
            **collision_counts,
        },
        "family_counts": {
            str(key): int(value)
            for key, value in eligible.groupby("family").size().to_dict().items()
        },
        "artifacts": {
            "contracts_path": str(contracts_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "contracts_sha256": sha256_file(contracts_path),
            "events_path": str(events_path.relative_to(workspace)).replace("\\", "/"),
            "events_sha256": sha256_file(events_path),
            "collisions_path": str(collisions_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "collisions_sha256": sha256_file(collisions_path),
            "statistics_requests_path": str(
                requests_path.relative_to(workspace)
            ).replace("\\", "/"),
            "statistics_requests_sha256": sha256_file(requests_path),
        },
        "bindings": {
            "parent_phase_01_acquisition_receipt_sha256": sha256_file(receipt_path),
            "parent_source_contract_kill_sha256": sha256_file(kill_path),
            "hyp002_prereg_sha256": sha256_file(prereg_path),
            "definition_payload_sha256": sorted(payload_hashes),
        },
        "definition_selection": "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT",
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "statistics_payload_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    report_path = output_root / ANALYSIS_FILE
    write_json(report_path, report)
    result = {
        "schema_version": "cme6e_option_pin_design_definition_discovery_receipt.v3",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "verdict": verdict,
        "discovered_events": int(len(events)),
        "eligible_nonoverlap_events": int(len(eligible)),
        "statistics_request_count": len(requests),
        "selected_definition_post_decision_count": definition_counts[
            "selected_definition_post_decision_count"
        ],
        "analysis_path": str(report_path.relative_to(workspace)).replace("\\", "/"),
        "analysis_sha256": sha256_file(report_path),
        "analyzer_path": str(Path(__file__).resolve().relative_to(workspace)).replace(
            "\\", "/"
        ),
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economic_verdict": "NOT_OPENED",
    }
    result_path = output_root / RESULT_FILE
    write_json(result_path, result)
    return result_path


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        result_path = execute(args.workspace)
        result = json.loads(result_path.read_text(encoding="ascii"))
        print(
            f"CME6EOPTPIN002_DESIGN_{result['verdict']} "
            f"events={result['discovered_events']} "
            f"eligible={result['eligible_nonoverlap_events']} "
            f"requests={result['statistics_request_count']} "
            f"post_decision_defs={result['selected_definition_post_decision_count']}"
        )
        print(f"RECEIPT {result_path}")
        return 0 if result["verdict"] == "PHASE_01_PASS" else 3
    except (DiscoveryError, base.DiscoveryError) as exc:
        print(f"CME6EOPTPIN002_DISCOVERY_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
