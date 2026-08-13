"""Analyze the frozen CME 6E option-pin pilot without reading target prices."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


HYPOTHESIS_ID = "HYP-CME6E-OPT-PIN-EURUSD-M15-001"
PILOT_ID = "CME6EOPTPIN001-SOURCE-PILOT-001"
DECISION = pd.Timestamp("2019-07-12T13:45:00Z")
EXPIRATION = pd.Timestamp("2019-07-12T14:00:00Z")
MAX_OI_REFERENCE = pd.Timestamp("2019-07-11T00:00:00Z")
EXPECTED_ASSET = "2EU"
EXPECTED_UNDERLYING = "6EU9"
OPEN_INTEREST_STAT_TYPE = 9
INVALID_QUANTITY = 2**63 - 1
PILOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{HYPOTHESIS_ID}/{PILOT_ID}"
)
ACQUISITION_RECEIPT = "source_pilot_acquisition_receipt.json"
ANALYSIS_FILE = "source_semantics_analysis.json"
SURFACE_FILE = "oi_surface_by_strike.csv"
RESULT_RECEIPT = "source_pilot_result_receipt.json"


class AnalysisError(RuntimeError):
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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    os.replace(temporary, path)


def _timestamp_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).isoformat().replace("+00:00", "Z")


def _required_columns(frame: pd.DataFrame, names: set[str], label: str) -> None:
    missing = sorted(names.difference(frame.columns))
    if missing:
        raise AnalysisError(f"{label} missing required columns: {missing}")


def select_definitions(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reconstruct the latest eligible outright definitions before decision."""
    required = {
        "ts_recv",
        "ts_event",
        "instrument_id",
        "instrument_class",
        "security_update_action",
        "user_defined_instrument",
        "asset",
        "underlying",
        "expiration",
        "strike_price",
        "symbol",
    }
    _required_columns(frame, required, "definition")
    working = frame.copy()
    working["strike_price"] = pd.to_numeric(
        working["strike_price"], errors="coerce"
    )
    post_decision_rows = int(
        ((working["ts_event"] >= DECISION) | (working["ts_recv"] >= DECISION)).sum()
    )
    if post_decision_rows:
        raise AnalysisError("definition payload contains a record at/after decision")

    ordered = working.sort_values(
        ["instrument_id", "ts_recv", "ts_event"], kind="stable"
    )
    latest = ordered.drop_duplicates("instrument_id", keep="last")
    eligible = latest[
        latest["instrument_class"].isin(["C", "P"])
        & (latest["security_update_action"] != "D")
        & (latest["user_defined_instrument"] == "N")
        & (latest["asset"] == EXPECTED_ASSET)
        & (latest["underlying"] == EXPECTED_UNDERLYING)
        & (latest["expiration"] == EXPIRATION)
        & latest["strike_price"].notna()
        & (latest["strike_price"] > 0)
    ].copy()
    eligible = eligible.sort_values(
        ["strike_price", "instrument_class", "instrument_id"], kind="stable"
    )

    stable_identity = bool(
        not eligible.empty
        and eligible["instrument_id"].is_unique
        and eligible["symbol"].is_unique
    )
    counts_by_class = {
        option_class: int(
            eligible.loc[
                eligible["instrument_class"] == option_class, "instrument_id"
            ].nunique()
        )
        for option_class in ("C", "P")
    }
    counters = {
        "raw_rows": int(len(working)),
        "raw_unique_instrument_ids": int(working["instrument_id"].nunique()),
        "latest_definition_rows": int(len(latest)),
        "eligible_rows": int(len(eligible)),
        "eligible_unique_strikes": int(eligible["strike_price"].nunique()),
        "eligible_by_class": counts_by_class,
        "excluded_latest_rows": int(len(latest) - len(eligible)),
        "post_decision_rows": post_decision_rows,
        "stable_instrument_identity": stable_identity,
        "max_ts_event": _timestamp_text(working["ts_event"].max()),
        "max_ts_recv": _timestamp_text(working["ts_recv"].max()),
    }
    return eligible, counters


def select_open_interest(
    frame: pd.DataFrame, definitions: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Select the latest strictly lagged OI record per eligible instrument."""
    required = {
        "ts_recv",
        "ts_event",
        "instrument_id",
        "ts_ref",
        "quantity",
        "sequence",
        "stat_type",
        "symbol",
    }
    _required_columns(frame, required, "statistics")
    working = frame.copy()
    working["quantity"] = pd.to_numeric(working["quantity"], errors="coerce")
    post_decision_rows = int(
        ((working["ts_event"] >= DECISION) | (working["ts_recv"] >= DECISION)).sum()
    )
    if post_decision_rows:
        raise AnalysisError("statistics payload contains a record at/after decision")

    eligible_ids = set(definitions["instrument_id"].astype(int).tolist())
    admissible = working[
        (working["stat_type"] == OPEN_INTEREST_STAT_TYPE)
        & working["quantity"].notna()
        & (working["quantity"] >= 0)
        & (working["quantity"] < INVALID_QUANTITY)
        & (working["ts_event"] < DECISION)
        & (working["ts_recv"] < DECISION)
        & working["ts_ref"].notna()
        & (working["ts_ref"] <= MAX_OI_REFERENCE)
        & working["instrument_id"].isin(eligible_ids)
    ].copy()
    latest = (
        admissible.sort_values(
            ["instrument_id", "ts_event", "ts_recv", "sequence"], kind="stable"
        )
        .drop_duplicates("instrument_id", keep="last")
        .copy()
    )
    joined = latest.merge(
        definitions[
            ["instrument_id", "instrument_class", "strike_price", "symbol"]
        ],
        on="instrument_id",
        how="inner",
        validate="one_to_one",
        suffixes=("_stat", "_definition"),
    )
    joined = joined.sort_values(
        ["strike_price", "instrument_class", "instrument_id"], kind="stable"
    )

    counts_by_class = {
        option_class: int(
            joined.loc[
                joined["instrument_class"] == option_class, "instrument_id"
            ].nunique()
        )
        for option_class in ("C", "P")
    }
    strict_temporal = bool(
        not joined.empty
        and (joined["ts_event"] < DECISION).all()
        and (joined["ts_recv"] < DECISION).all()
        and (joined["ts_ref"] <= MAX_OI_REFERENCE).all()
    )
    counters = {
        "raw_rows": int(len(working)),
        "raw_open_interest_rows": int(
            (working["stat_type"] == OPEN_INTEREST_STAT_TYPE).sum()
        ),
        "admissible_rows_before_latest": int(len(admissible)),
        "selected_latest_rows": int(len(joined)),
        "selected_by_class": counts_by_class,
        "selected_positive_quantity_rows": int((joined["quantity"] > 0).sum()),
        "selected_zero_quantity_rows": int((joined["quantity"] == 0).sum()),
        "definition_coverage": (
            float(len(joined) / len(definitions)) if len(definitions) else 0.0
        ),
        "post_decision_rows": post_decision_rows,
        "strict_temporal_contract": strict_temporal,
        "max_selected_ts_event": _timestamp_text(joined["ts_event"].max()),
        "max_selected_ts_recv": _timestamp_text(joined["ts_recv"].max()),
        "max_selected_ts_ref": _timestamp_text(joined["ts_ref"].max()),
    }
    return joined, counters


def aggregate_surface(open_interest: pd.DataFrame) -> pd.DataFrame:
    """Aggregate unsigned call plus put OI by exact strike."""
    if open_interest.empty:
        return pd.DataFrame(
            columns=["strike_price", "call_oi", "put_oi", "total_oi"]
        )
    pivot = open_interest.pivot_table(
        index="strike_price",
        columns="instrument_class",
        values="quantity",
        aggfunc="sum",
        fill_value=0,
    )
    for option_class in ("C", "P"):
        if option_class not in pivot.columns:
            pivot[option_class] = 0
    surface = pivot[["C", "P"]].rename(
        columns={"C": "call_oi", "P": "put_oi"}
    )
    surface["total_oi"] = surface["call_oi"] + surface["put_oi"]
    return surface.reset_index().sort_values("strike_price", kind="stable")


def determine_gates(
    definitions: pd.DataFrame,
    definition_counts: dict[str, Any],
    open_interest: pd.DataFrame,
    oi_counts: dict[str, Any],
    surface: pd.DataFrame,
) -> tuple[dict[str, bool], float | None, int | None]:
    if surface.empty:
        max_rows = surface
    else:
        max_rows = surface.loc[surface["total_oi"] == surface["total_oi"].max()]
    unique_max = bool(len(max_rows) == 1 and int(max_rows.iloc[0]["total_oi"]) > 0)
    pin_strike = float(max_rows.iloc[0]["strike_price"]) if unique_max else None
    max_oi = int(max_rows.iloc[0]["total_oi"]) if unique_max else None
    gates = {
        "parent_resolved_nonempty": bool(len(definitions) > 0),
        "eligible_call_and_put_definitions": bool(
            definition_counts["eligible_by_class"]["C"] > 0
            and definition_counts["eligible_by_class"]["P"] > 0
        ),
        "stable_instrument_identity": bool(
            definition_counts["stable_instrument_identity"]
        ),
        "admissible_call_and_put_open_interest": bool(
            oi_counts["selected_by_class"]["C"] > 0
            and oi_counts["selected_by_class"]["P"] > 0
        ),
        "strict_temporal_contract": bool(oi_counts["strict_temporal_contract"]),
        "no_post_decision_payload_records": bool(
            definition_counts["post_decision_rows"] == 0
            and oi_counts["post_decision_rows"] == 0
        ),
        "unique_positive_max_oi_strike": unique_max,
        "no_target_or_outcome_fields_used": True,
    }
    return gates, pin_strike, max_oi


def write_surface(path: Path, surface: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["strike_price", "call_oi", "put_oi", "total_oi"])
        for row in surface.itertuples(index=False):
            writer.writerow(
                [
                    f"{float(row.strike_price):.10f}",
                    int(row.call_oi),
                    int(row.put_oi),
                    int(row.total_oi),
                ]
            )
    os.replace(temporary, path)


def load_dbn(path: Path) -> pd.DataFrame:
    try:
        import databento as db

        return db.DBNStore.from_file(path).to_df().reset_index()
    except Exception as exc:
        raise AnalysisError(f"failed to decode {path.name}: {exc}") from exc


def verify_acquisition(pilot_root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    receipt_path = pilot_root / ACQUISITION_RECEIPT
    if not receipt_path.is_file():
        raise AnalysisError("acquisition receipt is missing")
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    if (
        receipt.get("status") != "SOURCE_PAYLOADS_ACQUIRED_SEMANTICS_PENDING"
        or receipt.get("hypothesis_id") != HYPOTHESIS_ID
        or receipt.get("pilot_id") != PILOT_ID
        or receipt.get("target_price_fields_used") != []
        or receipt.get("outcome_fields_used") != []
    ):
        raise AnalysisError("acquisition receipt contract mismatch")
    payload_paths: dict[str, Path] = {}
    for schema in ("definition", "statistics"):
        payload = receipt.get("payloads", {}).get(schema, {})
        raw_path = pilot_root.parents[5] / str(payload.get("path", ""))
        raw_path = raw_path.resolve()
        workspace = pilot_root.parents[5].resolve()
        try:
            raw_path.relative_to(workspace)
        except ValueError as exc:
            raise AnalysisError(f"{schema} path escaped workspace") from exc
        if (
            not raw_path.is_file()
            or sha256_file(raw_path) != payload.get("raw_sha256")
        ):
            raise AnalysisError(f"{schema} payload is missing or drifted")
        payload_paths[schema] = raw_path
    return receipt, payload_paths


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    pilot_root = (workspace / PILOT_REL).resolve()
    try:
        pilot_root.relative_to(workspace)
    except ValueError as exc:
        raise AnalysisError("pilot root escaped workspace") from exc
    receipt, payloads = verify_acquisition(pilot_root)
    definitions_raw = load_dbn(payloads["definition"])
    statistics_raw = load_dbn(payloads["statistics"])
    definitions, definition_counts = select_definitions(definitions_raw)
    open_interest, oi_counts = select_open_interest(statistics_raw, definitions)
    surface = aggregate_surface(open_interest)
    gates, pin_strike, max_oi = determine_gates(
        definitions, definition_counts, open_interest, oi_counts, surface
    )
    verdict = "SOURCE_PILOT_PASS" if all(gates.values()) else "KILL_SOURCE_PILOT"

    surface_path = pilot_root / SURFACE_FILE
    write_surface(surface_path, surface)
    analysis = {
        "schema_version": "cme6e_option_pin_source_semantics.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "pilot_id": PILOT_ID,
        "verdict": verdict,
        "frozen_contract": {
            "decision_utc": _timestamp_text(DECISION),
            "expiration_utc": _timestamp_text(EXPIRATION),
            "max_open_interest_reference_utc": _timestamp_text(MAX_OI_REFERENCE),
            "asset": EXPECTED_ASSET,
            "underlying": EXPECTED_UNDERLYING,
            "open_interest_stat_type": OPEN_INTEREST_STAT_TYPE,
            "call_put_treatment": "UNSIGNED_SUM_BY_EXACT_STRIKE",
        },
        "gates": gates,
        "definition_counts": definition_counts,
        "open_interest_counts": oi_counts,
        "surface": {
            "strike_count": int(len(surface)),
            "unique_max_oi_strike": pin_strike,
            "unique_max_total_oi": max_oi,
            "csv_path": str(surface_path.relative_to(workspace)).replace("\\", "/"),
            "csv_sha256": sha256_file(surface_path),
        },
        "bindings": {
            "acquisition_receipt_sha256": sha256_file(
                pilot_root / ACQUISITION_RECEIPT
            ),
            "definition_raw_sha256": sha256_file(payloads["definition"]),
            "statistics_raw_sha256": sha256_file(payloads["statistics"]),
        },
        "live_estimated_usd": float(receipt["live_estimated_usd"]),
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "trade_direction_produced": False,
        "economics_authorized": False,
        "mql5_authorized": False,
        "mt5_authorized": False,
        "validation_or_holdout_authorized": False,
    }
    analysis_path = pilot_root / ANALYSIS_FILE
    write_json(analysis_path, analysis)

    script_path = Path(__file__).resolve()
    result = {
        "schema_version": "cme6e_option_pin_source_pilot_result.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "pilot_id": PILOT_ID,
        "verdict": verdict,
        "unique_max_oi_strike": pin_strike,
        "unique_max_total_oi": max_oi,
        "artifact_bindings": {
            "analysis_path": str(analysis_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "analysis_sha256": sha256_file(analysis_path),
            "surface_path": str(surface_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "surface_sha256": sha256_file(surface_path),
            "analyzer_path": str(script_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "analyzer_sha256": sha256_file(script_path),
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economic_verdict": "NOT_OPENED",
    }
    result_path = pilot_root / RESULT_RECEIPT
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
            f"CME6EOPTPIN001_{result['verdict']} "
            f"pin={result['unique_max_oi_strike']} "
            f"total_oi={result['unique_max_total_oi']}"
        )
        print(f"RECEIPT {result_path}")
        return 0 if result["verdict"] == "SOURCE_PILOT_PASS" else 3
    except AnalysisError as exc:
        print(f"CME6EOPTPIN001_ANALYSIS_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
