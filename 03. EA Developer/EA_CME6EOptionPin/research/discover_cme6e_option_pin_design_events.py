"""Discover frozen 2018-2022 option expiry events from definitions only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
CAMPAIGN_ID = "CME6EOPTPIN001-DESIGN-SOURCE-001"
START = pd.Timestamp("2018-01-01T00:00:00Z")
END = pd.Timestamp("2023-01-01T00:00:00Z")
SER_CHANGE_LAST_OLD_EXPIRY = date(2019, 6, 9)
CHICAGO = ZoneInfo("America/Chicago")
ASSETS = {
    "EUU": "MONTHLY_QUARTERLY",
    "1EU": "FRIDAY_WEEKLY",
    "2EU": "FRIDAY_WEEKLY",
    "3EU": "FRIDAY_WEEKLY",
    "4EU": "FRIDAY_WEEKLY",
    "5EU": "FRIDAY_WEEKLY",
    "WE1": "WEDNESDAY_WEEKLY",
    "WE2": "WEDNESDAY_WEEKLY",
    "WE3": "WEDNESDAY_WEEKLY",
    "WE4": "WEDNESDAY_WEEKLY",
    "WE5": "WEDNESDAY_WEEKLY",
}
BATCH_ROOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{CAMPAIGN_ID}/phase_01_definitions_batch_r2"
)
ACQUISITION_RECEIPT = "phase_01_batch_acquisition_receipt.json"
CONTRACTS_FILE = "design_option_contract_catalog_r2.csv"
EVENTS_FILE = "design_expiry_events_r2.csv"
COLLISIONS_FILE = "design_overlap_collisions_r2.csv"
REQUESTS_FILE = "design_statistics_request_plan_r2.jsonl"
ANALYSIS_FILE = "design_definition_discovery_analysis_r2.json"
RESULT_FILE = "design_definition_discovery_receipt_r2.json"
V1_RESULT_FILE = "design_definition_discovery_receipt.json"
V1_RESULT_SHA256 = "7B29E8FE096C2C81CEEC4F8F9D5A18AB50987A621687818CEB05FE731716AE71"
CORRECTION_REL = Path(
    "03. EA Developer/EA_CME6EOptionPin/research/"
    "HYP-CME6E-OPT-PIN-EURUSD-M15-001_DESIGN_DISCOVERY_R2_CORRECTION.md"
)
CORRECTION_SHA256 = (
    "EF68887B42391A346E4459227704FE27FAE5FFC40736EEB0F1D03D14E7F8C213"
)


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


def require_columns(frame: pd.DataFrame, names: set[str]) -> None:
    missing = sorted(names.difference(frame.columns))
    if missing:
        raise DiscoveryError(f"definition payload missing columns: {missing}")


def eligible_contract_rows(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "ts_recv",
        "ts_event",
        "instrument_id",
        "raw_symbol",
        "security_update_action",
        "instrument_class",
        "expiration",
        "underlying",
        "asset",
        "strike_price",
        "user_defined_instrument",
    }
    require_columns(frame, required)
    working = frame.copy()
    working["strike_price"] = pd.to_numeric(
        working["strike_price"], errors="coerce"
    )
    working["raw_symbol"] = working["raw_symbol"].astype(str)
    working["underlying"] = working["underlying"].astype(str)
    return working[
        (working["ts_event"] < END)
        & (working["ts_recv"] < END)
        & (working["security_update_action"] != "D")
        & working["instrument_class"].isin(["C", "P"])
        & (working["user_defined_instrument"] == "N")
        & working["asset"].isin(ASSETS)
        & working["underlying"].str.startswith("6E")
        & (working["expiration"] >= START)
        & (working["expiration"] < END)
        & working["strike_price"].notna()
        & (working["strike_price"] > 0)
        & (working["raw_symbol"].str.len() > 0)
    ][
        [
            "ts_recv",
            "ts_event",
            "instrument_id",
            "raw_symbol",
            "instrument_class",
            "expiration",
            "underlying",
            "asset",
            "strike_price",
        ]
    ].drop_duplicates()


def stable_contracts(
    rows: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    semantic = [
        "instrument_class",
        "underlying",
        "asset",
        "strike_price",
    ]
    unstable: list[str] = []
    revised_expiration: list[str] = []
    latest_parts: list[pd.DataFrame] = []
    for raw_symbol, group in rows.groupby("raw_symbol", sort=False):
        if any(group[column].nunique(dropna=False) != 1 for column in semantic):
            unstable.append(str(raw_symbol))
            continue
        if group["expiration"].nunique(dropna=False) > 1:
            revised_expiration.append(str(raw_symbol))
        latest = group.sort_values(["ts_recv", "ts_event"], kind="stable").iloc[-1]
        for instrument_id in sorted(group["instrument_id"].unique()):
            row = latest.copy()
            row["instrument_id"] = instrument_id
            latest_parts.append(row.to_frame().T)
    if not latest_parts:
        return rows.iloc[0:0].copy(), sorted(unstable), sorted(revised_expiration)
    stable = pd.concat(latest_parts, ignore_index=True)
    stable["instrument_id"] = pd.to_numeric(stable["instrument_id"]).astype("uint32")
    stable["strike_price"] = pd.to_numeric(stable["strike_price"])
    stable["expiration"] = pd.to_datetime(stable["expiration"], utc=True)
    return stable, sorted(unstable), sorted(revised_expiration)


def clock_valid(expiration: pd.Timestamp) -> bool:
    local = expiration.to_pydatetime().astimezone(CHICAGO)
    expected_hour = 14 if local.date() <= SER_CHANGE_LAST_OLD_EXPIRY else 9
    return bool(
        local.hour == expected_hour
        and local.minute == 0
        and local.second == 0
        and local.microsecond == 0
    )


def discover_events(
    contracts: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (asset, underlying, expiration), group in contracts.groupby(
        ["asset", "underlying", "expiration"], sort=True
    ):
        counts = group.groupby("instrument_class")["raw_symbol"].nunique()
        calls = int(counts.get("C", 0))
        puts = int(counts.get("P", 0))
        expiration_ts = pd.Timestamp(expiration)
        decision = expiration_ts - pd.Timedelta(minutes=15)
        event_key = f"{asset}|{underlying}|{iso_utc(expiration_ts)}"
        event_id = hashlib.sha256(event_key.encode("ascii")).hexdigest()[:16].upper()
        records.append(
            {
                "event_id": event_id,
                "asset": str(asset),
                "family": ASSETS[str(asset)],
                "parent": f"{asset}.OPT",
                "underlying": str(underlying),
                "expiration_utc": expiration_ts,
                "decision_utc": decision,
                "expiration_chicago": expiration_ts.to_pydatetime().astimezone(
                    CHICAGO
                ).isoformat(),
                "call_definitions": calls,
                "put_definitions": puts,
                "strike_count": int(group["strike_price"].nunique()),
                "raw_symbol_count": int(group["raw_symbol"].nunique()),
                "instrument_id_count": int(group["instrument_id"].nunique()),
                "has_call_and_put": bool(calls > 0 and puts > 0),
                "clock_valid": clock_valid(expiration_ts),
                "m15_boundary": bool(
                    decision.second == 0
                    and decision.microsecond == 0
                    and decision.minute % 15 == 0
                ),
            }
        )
    events = pd.DataFrame(records)
    if events.empty:
        return events, events.copy(), {"collision_groups": 0, "collision_events": 0}
    collision_key = ["underlying", "expiration_utc", "decision_utc"]
    asset_counts = events.groupby(collision_key)["asset"].transform("nunique")
    collisions = events.loc[asset_counts > 1].copy()
    events["overlap_collision"] = asset_counts > 1
    counts = {
        "collision_groups": int(
            collisions[collision_key].drop_duplicates().shape[0]
        ),
        "collision_events": int(len(collisions)),
    }
    return events, collisions, counts


def eligible_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    return events[
        events["has_call_and_put"]
        & events["clock_valid"]
        & events["m15_boundary"]
        & ~events["overlap_collision"]
    ].copy()


def statistics_requests(events: pd.DataFrame) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for row in events.sort_values(["decision_utc", "parent", "event_id"]).itertuples(
        index=False
    ):
        decision = pd.Timestamp(row.decision_utc)
        start = decision.normalize()
        request_key = f"{row.parent}|{iso_utc(start)}|{iso_utc(decision)}"
        request_id = hashlib.sha256(request_key.encode("ascii")).hexdigest()[:16].upper()
        requests.append(
            {
                "schema_version": "cme6e_option_pin_statistics_request.v1",
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
                "max_oi_reference_utc": iso_utc(start - pd.Timedelta(days=1)),
            }
        )
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for request in requests:
        if request["request_id"] in seen:
            raise DiscoveryError("duplicate statistics request ID")
        seen.add(request["request_id"])
        unique.append(request)
    return unique


def write_events(path: Path, events: pd.DataFrame) -> None:
    columns = [
        "event_id",
        "asset",
        "family",
        "parent",
        "underlying",
        "expiration_utc",
        "decision_utc",
        "expiration_chicago",
        "call_definitions",
        "put_definitions",
        "strike_count",
        "raw_symbol_count",
        "instrument_id_count",
        "has_call_and_put",
        "clock_valid",
        "m15_boundary",
        "overlap_collision",
    ]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in events.sort_values(
            ["decision_utc", "asset", "underlying"], kind="stable"
        ).itertuples(index=False):
            values = row._asdict()
            writer.writerow(
                [
                    iso_utc(values[column])
                    if column in {"expiration_utc", "decision_utc"}
                    else values[column]
                    for column in columns
                ]
            )
    os.replace(temporary, path)


def write_contracts(path: Path, contracts: pd.DataFrame) -> None:
    columns = [
        "raw_symbol",
        "asset",
        "family",
        "underlying",
        "expiration_utc",
        "instrument_class",
        "strike_price",
        "instrument_ids",
    ]
    records: list[dict[str, Any]] = []
    for raw_symbol, group in contracts.groupby("raw_symbol", sort=True):
        row = group.iloc[0]
        records.append(
            {
                "raw_symbol": str(raw_symbol),
                "asset": str(row["asset"]),
                "family": ASSETS[str(row["asset"])],
                "underlying": str(row["underlying"]),
                "expiration_utc": iso_utc(row["expiration"]),
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


def write_requests(path: Path, requests: Iterable[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="\n") as handle:
        for request in requests:
            handle.write(json.dumps(request, sort_keys=True, ensure_ascii=True) + "\n")
    os.replace(temporary, path)


def load_contracts(payload_paths: list[Path]) -> tuple[pd.DataFrame, dict[str, Any]]:
    import databento as db

    unique_parts: list[pd.DataFrame] = []
    raw_rows = 0
    for path in sorted(payload_paths):
        frame = db.DBNStore.from_file(path).to_df().reset_index()
        raw_rows += len(frame)
        part = eligible_contract_rows(frame)
        if not part.empty:
            unique_parts.append(part)
    if not unique_parts:
        raise DiscoveryError("no eligible option definitions found")
    rows = pd.concat(unique_parts, ignore_index=True).drop_duplicates()
    stable, unstable, revised_expiration = stable_contracts(rows)
    counters = {
        "payload_file_count": len(payload_paths),
        "raw_definition_rows": int(raw_rows),
        "eligible_distinct_rows": int(len(rows)),
        "stable_distinct_rows": int(len(stable)),
        "distinct_raw_symbols": int(stable["raw_symbol"].nunique()),
        "unstable_raw_symbol_count": len(unstable),
        "unstable_raw_symbols": unstable,
        "expiration_revised_raw_symbol_count": len(revised_expiration),
        "expiration_revised_raw_symbols": revised_expiration,
    }
    return stable, counters


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    root = (workspace / BATCH_ROOT_REL).resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise DiscoveryError("batch root escaped workspace") from exc
    receipt_path = root / ACQUISITION_RECEIPT
    v1_result_path = root / V1_RESULT_FILE
    correction_path = (workspace / CORRECTION_REL).resolve()
    if not receipt_path.is_file():
        raise DiscoveryError("completed phase-01 acquisition receipt is missing")
    if (
        not v1_result_path.is_file()
        or sha256_file(v1_result_path) != V1_RESULT_SHA256
        or not correction_path.is_file()
        or sha256_file(correction_path) != CORRECTION_SHA256
    ):
        raise DiscoveryError("R2 correction authority is missing or drifted")
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    if (
        receipt.get("status") != "DEFINITIONS_ACQUIRED_EVENT_DISCOVERY_PENDING"
        or receipt.get("hypothesis_id") != HYPOTHESIS_ID
        or receipt.get("campaign_id") != CAMPAIGN_ID
        or receipt.get("target_price_fields_used") != []
        or receipt.get("outcome_fields_used") != []
    ):
        raise DiscoveryError("phase-01 receipt contract mismatch")
    payload_paths: list[Path] = []
    for payload in receipt.get("payloads", []):
        path = (workspace / str(payload.get("path", ""))).resolve()
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise DiscoveryError("payload path escaped workspace") from exc
        if not path.is_file() or sha256_file(path) != payload.get("raw_sha256"):
            raise DiscoveryError("definition payload missing or drifted")
        payload_paths.append(path)
    if not payload_paths:
        raise DiscoveryError("receipt contains no definition payloads")

    contracts, definition_counts = load_contracts(payload_paths)
    events, collisions, collision_counts = discover_events(contracts)
    eligible = eligible_events(events)
    requests = statistics_requests(eligible)

    contracts_path = root / CONTRACTS_FILE
    events_path = root / EVENTS_FILE
    collisions_path = root / COLLISIONS_FILE
    requests_path = root / REQUESTS_FILE
    write_contracts(contracts_path, contracts)
    write_events(events_path, events)
    write_events(collisions_path, collisions)
    write_requests(requests_path, requests)

    expiry_months = set(
        pd.Timestamp(value).strftime("%Y-%m") for value in events["expiration_utc"]
    )
    expected_months = set(pd.period_range("2018-01", "2022-12", freq="M").astype(str))
    gates = {
        "definition_payloads_hash_bound": True,
        "zero_unstable_raw_symbols": definition_counts["unstable_raw_symbol_count"]
        == 0,
        "no_design_month_empty_of_definitions": expected_months.issubset(expiry_months),
        "potential_nonoverlap_event_count_at_least_90": int(len(eligible)) >= 90,
        "target_and_outcome_fields_absent": True,
    }
    verdict = "PHASE_01_PASS" if all(gates.values()) else "KILL_SOURCE_DESIGN"
    report = {
        "schema_version": "cme6e_option_pin_design_definition_discovery.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
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
            "phase_01_acquisition_receipt_sha256": sha256_file(receipt_path),
            "v1_discovery_receipt_sha256": sha256_file(v1_result_path),
            "r2_correction_sha256": sha256_file(correction_path),
            "definition_payload_sha256": [
                sha256_file(path) for path in sorted(payload_paths)
            ],
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "statistics_payload_authorized": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    report_path = root / ANALYSIS_FILE
    write_json(report_path, report)
    result = {
        "schema_version": "cme6e_option_pin_design_definition_discovery_receipt.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "campaign_id": CAMPAIGN_ID,
        "verdict": verdict,
        "discovered_events": int(len(events)),
        "eligible_nonoverlap_events": int(len(eligible)),
        "statistics_request_count": len(requests),
        "analysis_path": str(report_path.relative_to(workspace)).replace("\\", "/"),
        "analysis_sha256": sha256_file(report_path),
        "analyzer_path": str(Path(__file__).resolve().relative_to(workspace)).replace(
            "\\", "/"
        ),
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
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
            f"CME6EOPTPIN_DESIGN_{result['verdict']} "
            f"events={result['discovered_events']} "
            f"eligible={result['eligible_nonoverlap_events']} "
            f"requests={result['statistics_request_count']}"
        )
        print(f"RECEIPT {result_path}")
        return 0 if result["verdict"] == "PHASE_01_PASS" else 3
    except DiscoveryError as exc:
        print(f"CME6EOPTPIN_DESIGN_DISCOVERY_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
