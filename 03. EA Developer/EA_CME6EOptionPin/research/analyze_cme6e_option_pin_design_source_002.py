"""Build strict HYP002 source-only OI pins; missing normalized OI is unknown."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
CONTRACTS_FILE = "design_option_contract_catalog_pit.csv"
EVENTS_FILE = "design_expiry_events_pit.csv"
REQUESTS_FILE = "design_statistics_request_plan_pit.jsonl"
DISCOVERY_RECEIPT = "design_definition_discovery_receipt_pit.json"
STATISTICS_RECEIPT = "phase_02_statistics_acquisition_receipt_pit.json"
EVENT_RESULTS_FILE = "design_event_source_results_strict.csv"
SURFACES_FILE = "design_oi_surfaces_strict.csv"
PINS_FILE = "design_source_pins_strict.csv"
ANALYSIS_FILE = "design_source_semantics_analysis_strict.json"
RESULT_FILE = "design_source_semantics_receipt_strict.json"
OPEN_INTEREST_STAT_TYPE = 9
OPEN_INTEREST_ADD_ACTION = 1
OPEN_INTEREST_DELETE_ACTION = 2
INVALID_QUANTITY = 2**63 - 1


class SourceAnalysisError(RuntimeError):
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


def instrument_ids(value: str) -> set[int]:
    return {int(part) for part in str(value).split(";") if part}


def surface_from_published(published: pd.DataFrame) -> pd.DataFrame:
    pivot = published.pivot_table(
        index="strike_price",
        columns="instrument_class",
        values="quantity",
        aggfunc="sum",
        fill_value=0,
    )
    for option_class in ("C", "P"):
        if option_class not in pivot.columns:
            pivot[option_class] = 0
    surface = pivot[["C", "P"]].rename(columns={"C": "call_oi", "P": "put_oi"})
    surface["total_oi"] = surface["call_oi"] + surface["put_oi"]
    return surface.reset_index().sort_values("strike_price", kind="stable")


def unique_max(surface: pd.DataFrame) -> tuple[float | None, int | None, bool]:
    if surface.empty:
        return None, None, False
    maxima = surface.loc[surface["total_oi"] == surface["total_oi"].max()]
    valid = bool(len(maxima) == 1 and int(maxima.iloc[0]["total_oi"]) > 0)
    if not valid:
        return None, None, False
    return (
        float(maxima.iloc[0]["strike_price"]),
        int(maxima.iloc[0]["total_oi"]),
        True,
    )


def analyze_event(
    request: dict[str, Any],
    statistics: pd.DataFrame,
    event_contracts: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame]:
    required = {
        "ts_recv",
        "ts_event",
        "instrument_id",
        "ts_ref",
        "quantity",
        "sequence",
        "stat_type",
        "update_action",
        "symbol",
    }
    missing_columns = sorted(required.difference(statistics.columns))
    if missing_columns:
        raise SourceAnalysisError(
            f"statistics {request['request_id']} missing columns: {missing_columns}"
        )
    if request.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID":
        raise SourceAnalysisError("request attempted non-strict missing-OI policy")

    decision = pd.Timestamp(request["decision_utc"])
    required_reference = pd.Timestamp(request["required_oi_reference_utc"])
    working = statistics.copy()
    working["quantity"] = pd.to_numeric(working["quantity"], errors="coerce")
    working["symbol"] = working["symbol"].astype(str)
    post_decision_rows = int(
        ((working["ts_event"] >= decision) | (working["ts_recv"] >= decision)).sum()
    )
    contract_symbols = set(event_contracts["raw_symbol"].astype(str))
    oi_scope = working[
        (working["stat_type"] == OPEN_INTEREST_STAT_TYPE)
        & (working["ts_event"] < decision)
        & (working["ts_recv"] < decision)
        & working["ts_ref"].notna()
        & (working["ts_ref"] == required_reference)
        & working["symbol"].isin(contract_symbols)
    ].copy()
    delete_rows = int(
        (oi_scope["update_action"] == OPEN_INTEREST_DELETE_ACTION).sum()
    )
    oi = oi_scope[
        (oi_scope["update_action"] == OPEN_INTEREST_ADD_ACTION)
        & oi_scope["quantity"].notna()
        & (oi_scope["quantity"] >= 0)
        & (oi_scope["quantity"] < INVALID_QUANTITY)
    ].copy()
    latest = (
        oi.sort_values(["symbol", "ts_event", "ts_recv", "sequence"], kind="stable")
        .drop_duplicates("symbol", keep="last")
        .copy()
    )

    ids_by_symbol = {
        str(row.raw_symbol): instrument_ids(row.instrument_ids)
        for row in event_contracts.itertuples(index=False)
    }
    alias_rows = int(
        sum(
            int(row.instrument_id) not in ids_by_symbol.get(str(row.symbol), set())
            for row in latest.itertuples(index=False)
        )
    )
    contract_fields = event_contracts[
        ["raw_symbol", "instrument_class", "strike_price"]
    ].copy()
    completed = contract_fields.merge(
        latest[["symbol", "quantity", "ts_event", "ts_recv", "ts_ref"]],
        left_on="raw_symbol",
        right_on="symbol",
        how="left",
        validate="one_to_one",
    )
    published = completed.loc[completed["quantity"].notna()].copy()
    missing_oi_count = int(len(completed) - len(published))
    published_by_class = {
        option_class: int(
            published.loc[
                published["instrument_class"] == option_class, "raw_symbol"
            ].nunique()
        )
        for option_class in ("C", "P")
    }
    complete_surface = missing_oi_count == 0
    surface = (
        surface_from_published(published)
        if complete_surface
        else pd.DataFrame(
            columns=["strike_price", "call_oi", "put_oi", "total_oi"]
        )
    )
    pin, total_oi, unique = unique_max(surface)
    strict_temporal = bool(
        not published.empty
        and (published["ts_event"] < decision).all()
        and (published["ts_recv"] < decision).all()
        and (published["ts_ref"] == required_reference).all()
    )
    source_valid = bool(
        post_decision_rows == 0
        and delete_rows == 0
        and alias_rows == 0
        and strict_temporal
        and complete_surface
        and published_by_class["C"] > 0
        and published_by_class["P"] > 0
        and int(surface["total_oi"].sum()) > 0
    )
    result = {
        "event_id": request["event_id"],
        "request_id": request["request_id"],
        "asset": request["asset"],
        "underlying": request["underlying"],
        "expiration_utc": request["expiration_utc"],
        "decision_utc": request["decision_utc"],
        "required_oi_reference_utc": request["required_oi_reference_utc"],
        "definition_count": int(len(event_contracts)),
        "published_oi_count": int(len(published)),
        "missing_oi_count": missing_oi_count,
        "definition_coverage": (
            float(len(published) / len(completed)) if len(completed) else 0.0
        ),
        "published_call_count": published_by_class["C"],
        "published_put_count": published_by_class["P"],
        "post_decision_rows": post_decision_rows,
        "oi_delete_rows": delete_rows,
        "unresolved_alias_rows": alias_rows,
        "strict_temporal": strict_temporal,
        "complete_published_oi_surface": complete_surface,
        "source_valid": source_valid,
        "surface_strike_count": int(len(surface)),
        "unique_positive_pin": bool(source_valid and unique),
        "pin_strike": pin if source_valid else None,
        "pin_total_oi": total_oi if source_valid else None,
    }
    if not surface.empty:
        surface.insert(0, "event_id", request["event_id"])
    return result, surface


def write_dict_rows(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=columns, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.replace(temporary, path)


def write_surfaces(path: Path, surfaces: list[pd.DataFrame]) -> None:
    nonempty = [surface for surface in surfaces if not surface.empty]
    combined = pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["event_id", "strike_price", "call_oi", "put_oi", "total_oi"])
        for row in combined.itertuples(index=False):
            writer.writerow(
                [
                    row.event_id,
                    f"{float(row.strike_price):.10f}",
                    int(row.call_oi),
                    int(row.put_oi),
                    int(row.total_oi),
                ]
            )
    os.replace(temporary, path)


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise SourceAnalysisError("HYP002 source root escaped workspace") from exc
    contracts_path = root / CONTRACTS_FILE
    events_path = root / EVENTS_FILE
    requests_path = root / REQUESTS_FILE
    discovery_path = root / DISCOVERY_RECEIPT
    statistics_receipt_path = root / STATISTICS_RECEIPT
    required_paths = [
        contracts_path,
        events_path,
        requests_path,
        discovery_path,
        statistics_receipt_path,
    ]
    if not all(path.is_file() for path in required_paths):
        raise SourceAnalysisError("HYP002 source campaign artifacts are incomplete")
    discovery = json.loads(discovery_path.read_text(encoding="ascii"))
    acquisition = json.loads(statistics_receipt_path.read_text(encoding="ascii"))
    if (
        discovery.get("verdict") != "PHASE_01_PASS"
        or discovery.get("selected_definition_post_decision_count") != 0
        or discovery.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
        or acquisition.get("status") != "STATISTICS_ACQUIRED_SEMANTICS_PENDING"
        or acquisition.get("missing_oi_policy") != "UNKNOWN_EVENT_INVALID"
        or acquisition.get("target_price_fields_used") != []
        or acquisition.get("outcome_fields_used") != []
    ):
        raise SourceAnalysisError("HYP002 source campaign is not ready for semantics")

    contracts = pd.read_csv(contracts_path, dtype={"raw_symbol": str, "asset": str})
    events = pd.read_csv(events_path)
    requests = load_jsonl(requests_path)
    request_by_id = {request["request_id"]: request for request in requests}
    payload_by_id = {
        payload["request_id"]: payload for payload in acquisition.get("payloads", [])
    }
    if set(request_by_id) != set(payload_by_id):
        raise SourceAnalysisError("HYP002 statistics payload/request identity mismatch")

    import databento as db

    results: list[dict[str, Any]] = []
    surfaces: list[pd.DataFrame] = []
    payload_hashes: list[str] = []
    for request_id in sorted(request_by_id):
        request = request_by_id[request_id]
        payload = payload_by_id[request_id]
        path = (workspace / payload["path"]).resolve()
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise SourceAnalysisError("HYP002 statistics payload escaped workspace") from exc
        if not path.is_file() or sha256_file(path) != payload.get("raw_sha256"):
            raise SourceAnalysisError(f"HYP002 statistics payload drift: {request_id}")
        payload_hashes.append(payload["raw_sha256"])
        event_contracts = contracts[
            (contracts["asset"] == request["asset"])
            & (contracts["underlying"] == request["underlying"])
            & (contracts["expiration_utc"] == request["expiration_utc"])
        ].copy()
        if event_contracts.empty:
            raise SourceAnalysisError(f"HYP002 event catalog empty: {request_id}")
        statistics = db.DBNStore.from_file(path).to_df().reset_index()
        result, surface = analyze_event(request, statistics, event_contracts)
        results.append(result)
        surfaces.append(surface)

    results.sort(key=lambda row: (row["decision_utc"], row["event_id"]))
    event_results_path = root / EVENT_RESULTS_FILE
    write_dict_rows(event_results_path, results, list(results[0].keys()))
    surfaces_path = root / SURFACES_FILE
    write_surfaces(surfaces_path, surfaces)
    pins = [row for row in results if row["source_valid"] and row["unique_positive_pin"]]
    pins_path = root / PINS_FILE
    pin_columns = [
        "event_id",
        "asset",
        "underlying",
        "expiration_utc",
        "decision_utc",
        "required_oi_reference_utc",
        "pin_strike",
        "pin_total_oi",
    ]
    write_dict_rows(pins_path, pins, pin_columns)

    source_valid_count = sum(bool(row["source_valid"]) for row in results)
    coverage = source_valid_count / len(results) if results else 0.0
    pin_months = {str(row["expiration_utc"])[:7] for row in pins}
    unresolved = sum(int(row["unresolved_alias_rows"]) for row in results)
    post_decision = sum(int(row["post_decision_rows"]) for row in results)
    deletes = sum(int(row["oi_delete_rows"]) for row in results)
    missing_events = sum(int(row["missing_oi_count"] > 0) for row in results)
    gates = {
        "all_statistics_payloads_hash_bound": len(payload_hashes) == len(requests),
        "zero_unresolved_instrument_remaps": unresolved == 0,
        "zero_post_decision_inputs": post_decision == 0,
        "zero_open_interest_delete_rows": deletes == 0,
        "missing_normalized_oi_never_zero_completed": True,
        "source_valid_coverage_at_least_95_percent": coverage >= 0.95,
        "unique_positive_pin_count_at_least_90": len(pins) >= 90,
        "pin_calendar_months_at_least_48": len(pin_months) >= 48,
        "target_and_outcome_fields_absent": True,
    }
    verdict = "SOURCE_DESIGN_PASS" if all(gates.values()) else "KILL_SOURCE_DESIGN"
    report = {
        "schema_version": "cme6e_option_pin_design_source_semantics.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "gates": gates,
        "counts": {
            "discovered_nonoverlap_events": len(results),
            "source_valid_events": source_valid_count,
            "source_valid_coverage": coverage,
            "events_with_unknown_oi": missing_events,
            "unique_positive_pin_events": len(pins),
            "pin_calendar_months": len(pin_months),
            "unresolved_instrument_remap_rows": unresolved,
            "open_interest_delete_rows": deletes,
            "post_decision_rows": post_decision,
        },
        "artifacts": {
            "event_results_path": str(event_results_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "event_results_sha256": sha256_file(event_results_path),
            "surfaces_path": str(surfaces_path.relative_to(workspace)).replace("\\", "/"),
            "surfaces_sha256": sha256_file(surfaces_path),
            "pins_path": str(pins_path.relative_to(workspace)).replace("\\", "/"),
            "pins_sha256": sha256_file(pins_path),
        },
        "bindings": {
            "discovery_receipt_sha256": sha256_file(discovery_path),
            "statistics_acquisition_receipt_sha256": sha256_file(
                statistics_receipt_path
            ),
            "contracts_sha256": sha256_file(contracts_path),
            "events_sha256": sha256_file(events_path),
            "requests_sha256": sha256_file(requests_path),
            "statistics_payload_sha256": sorted(payload_hashes),
        },
        "definition_selection": "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT",
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "trade_direction_produced": False,
        "economic_verdict": "NOT_OPENED",
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    report_path = root / ANALYSIS_FILE
    write_json(report_path, report)
    result = {
        "schema_version": "cme6e_option_pin_design_source_semantics_receipt.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "source_valid_events": source_valid_count,
        "events_with_unknown_oi": missing_events,
        "unique_positive_pin_events": len(pins),
        "pin_calendar_months": len(pin_months),
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
    result_path = root / RESULT_FILE
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
            f"source_valid={result['source_valid_events']} "
            f"unknown_events={result['events_with_unknown_oi']} "
            f"pins={result['unique_positive_pin_events']} "
            f"months={result['pin_calendar_months']}"
        )
        print(f"RECEIPT {result_path}")
        return 0 if result["verdict"] == "SOURCE_DESIGN_PASS" else 3
    except SourceAnalysisError as exc:
        print(f"CME6EOPTPIN002_SOURCE_ANALYSIS_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

