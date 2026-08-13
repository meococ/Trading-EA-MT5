"""Analyze quarterly pilot 002 and audit absent-OI zero completion."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


BASE_SCRIPT = Path(__file__).with_name(
    "analyze_cme6e_option_pin_001_source_pilot.py"
)
BASE_SCRIPT_SHA256 = "E9307AC4FC027FBFD7B544C7D425D306699C868D354A38FB893AE8B135BA60DB"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


if sha256_file(BASE_SCRIPT) != BASE_SCRIPT_SHA256:
    raise RuntimeError("shared source-semantics implementation drifted")

SPEC = importlib.util.spec_from_file_location("option_pin_analysis", BASE_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load shared source-semantics implementation")
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)

analysis.PILOT_ID = "CME6EOPTPIN002-SOURCE-PILOT-002"
analysis.DECISION = pd.Timestamp("2019-09-06T13:45:00Z")
analysis.EXPIRATION = pd.Timestamp("2019-09-06T14:00:00Z")
analysis.MAX_OI_REFERENCE = pd.Timestamp("2019-09-05T00:00:00Z")
analysis.EXPECTED_ASSET = "EUU"
analysis.EXPECTED_UNDERLYING = "6EU9"
analysis.PILOT_REL = Path(
    "02. AlphaFactory/data/databento/cme_6e_option_pin/"
    f"{analysis.HYPOTHESIS_ID}/{analysis.PILOT_ID}"
)

PUBLISHED_SURFACE_FILE = "oi_surface_published_only.csv"
ZERO_COMPLETED_SURFACE_FILE = "oi_surface_zero_completed.csv"
MISSING_FILE = "definitions_without_published_oi.csv"
ANALYSIS_FILE = "source_semantics_analysis.json"
RESULT_RECEIPT = "source_pilot_result_receipt.json"


def zero_complete(
    definitions: pd.DataFrame, open_interest: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    values = open_interest[["instrument_id", "quantity"]].copy()
    completed = definitions[
        ["instrument_id", "instrument_class", "strike_price", "symbol"]
    ].merge(values, on="instrument_id", how="left", validate="one_to_one")
    missing = completed.loc[completed["quantity"].isna()].copy()
    completed["quantity"] = completed["quantity"].fillna(0).astype("int64")
    return completed, missing


def surface_max(surface: pd.DataFrame) -> tuple[float | None, int | None, bool]:
    if surface.empty:
        return None, None, False
    maxima = surface.loc[surface["total_oi"] == surface["total_oi"].max()]
    unique = bool(len(maxima) == 1 and int(maxima.iloc[0]["total_oi"]) > 0)
    if not unique:
        return None, None, False
    return (
        float(maxima.iloc[0]["strike_price"]),
        int(maxima.iloc[0]["total_oi"]),
        True,
    )


def write_missing(path: Path, missing: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="ascii", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["instrument_id", "instrument_class", "strike_price", "symbol"]
        )
        for row in missing.sort_values(
            ["strike_price", "instrument_class", "instrument_id"], kind="stable"
        ).itertuples(index=False):
            writer.writerow(
                [
                    int(row.instrument_id),
                    str(row.instrument_class),
                    f"{float(row.strike_price):.10f}",
                    str(row.symbol),
                ]
            )
    os.replace(temporary, path)


def alias_oi_rows(
    statistics: pd.DataFrame, missing: pd.DataFrame
) -> pd.DataFrame:
    if missing.empty:
        return statistics.iloc[0:0].copy()
    missing_symbols = set(missing["symbol"].astype(str))
    missing_ids = set(missing["instrument_id"].astype(int))
    quantity = pd.to_numeric(statistics["quantity"], errors="coerce")
    candidate = statistics[
        (statistics["stat_type"] == analysis.OPEN_INTEREST_STAT_TYPE)
        & quantity.notna()
        & (quantity >= 0)
        & (quantity < analysis.INVALID_QUANTITY)
        & (statistics["ts_event"] < analysis.DECISION)
        & (statistics["ts_recv"] < analysis.DECISION)
        & statistics["ts_ref"].notna()
        & (statistics["ts_ref"] <= analysis.MAX_OI_REFERENCE)
        & statistics["symbol"].astype(str).isin(missing_symbols)
    ]
    return candidate.loc[~candidate["instrument_id"].astype(int).isin(missing_ids)]


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    pilot_root = (workspace / analysis.PILOT_REL).resolve()
    try:
        pilot_root.relative_to(workspace)
    except ValueError as exc:
        raise analysis.AnalysisError("pilot root escaped workspace") from exc
    acquisition_receipt, payloads = analysis.verify_acquisition(pilot_root)
    definitions_raw = analysis.load_dbn(payloads["definition"])
    statistics_raw = analysis.load_dbn(payloads["statistics"])
    definitions, definition_counts = analysis.select_definitions(definitions_raw)
    open_interest, oi_counts = analysis.select_open_interest(
        statistics_raw, definitions
    )

    published_surface = analysis.aggregate_surface(open_interest)
    completed, missing = zero_complete(definitions, open_interest)
    zero_surface = analysis.aggregate_surface(completed)
    published_pin, published_total, published_unique = surface_max(published_surface)
    zero_pin, zero_total, zero_unique = surface_max(zero_surface)
    aliases = alias_oi_rows(statistics_raw, missing)

    base_gates, _, _ = analysis.determine_gates(
        definitions,
        definition_counts,
        open_interest,
        oi_counts,
        published_surface,
    )
    gates = {
        **base_gates,
        "published_surface_unique_positive_max": published_unique,
        "zero_completed_surface_unique_positive_max": zero_unique,
        "published_and_zero_completed_maxima_match": bool(
            published_unique
            and zero_unique
            and published_pin == zero_pin
            and published_total == zero_total
        ),
        "no_missing_symbol_alias_open_interest": bool(aliases.empty),
        "missing_definition_set_persisted": True,
    }
    verdict = "SOURCE_PILOT_PASS" if all(gates.values()) else "KILL_SOURCE_PILOT"

    published_path = pilot_root / PUBLISHED_SURFACE_FILE
    zero_path = pilot_root / ZERO_COMPLETED_SURFACE_FILE
    missing_path = pilot_root / MISSING_FILE
    analysis.write_surface(published_path, published_surface)
    analysis.write_surface(zero_path, zero_surface)
    write_missing(missing_path, missing)

    report: dict[str, Any] = {
        "schema_version": "cme6e_option_pin_source_semantics.v2",
        "created_at_utc": analysis.utc_now(),
        "hypothesis_id": analysis.HYPOTHESIS_ID,
        "pilot_id": analysis.PILOT_ID,
        "verdict": verdict,
        "frozen_contract": {
            "decision_utc": analysis._timestamp_text(analysis.DECISION),
            "expiration_utc": analysis._timestamp_text(analysis.EXPIRATION),
            "max_open_interest_reference_utc": analysis._timestamp_text(
                analysis.MAX_OI_REFERENCE
            ),
            "asset": analysis.EXPECTED_ASSET,
            "underlying": analysis.EXPECTED_UNDERLYING,
            "open_interest_stat_type": analysis.OPEN_INTEREST_STAT_TYPE,
        },
        "gates": gates,
        "definition_counts": definition_counts,
        "open_interest_counts": {
            **oi_counts,
            "missing_definition_rows": int(len(missing)),
            "missing_definition_rate": (
                float(len(missing) / len(definitions)) if len(definitions) else 0.0
            ),
            "missing_symbol_alias_oi_rows": int(len(aliases)),
        },
        "published_surface": {
            "strike_count": int(len(published_surface)),
            "unique_max_oi_strike": published_pin,
            "unique_max_total_oi": published_total,
            "path": str(published_path.relative_to(workspace)).replace("\\", "/"),
            "sha256": sha256_file(published_path),
        },
        "zero_completed_surface": {
            "strike_count": int(len(zero_surface)),
            "unique_max_oi_strike": zero_pin,
            "unique_max_total_oi": zero_total,
            "path": str(zero_path.relative_to(workspace)).replace("\\", "/"),
            "sha256": sha256_file(zero_path),
        },
        "missing_definitions": {
            "path": str(missing_path.relative_to(workspace)).replace("\\", "/"),
            "sha256": sha256_file(missing_path),
        },
        "bindings": {
            "acquisition_receipt_sha256": sha256_file(
                pilot_root / analysis.ACQUISITION_RECEIPT
            ),
            "definition_raw_sha256": sha256_file(payloads["definition"]),
            "statistics_raw_sha256": sha256_file(payloads["statistics"]),
            "shared_analyzer_sha256": BASE_SCRIPT_SHA256,
        },
        "live_estimated_usd": float(acquisition_receipt["live_estimated_usd"]),
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "trade_direction_produced": False,
        "economic_verdict": "NOT_OPENED",
        "mql5_authorized": False,
        "mt5_authorized": False,
    }
    report_path = pilot_root / ANALYSIS_FILE
    analysis.write_json(report_path, report)

    script_path = Path(__file__).resolve()
    result = {
        "schema_version": "cme6e_option_pin_source_pilot_result.v2",
        "created_at_utc": analysis.utc_now(),
        "hypothesis_id": analysis.HYPOTHESIS_ID,
        "pilot_id": analysis.PILOT_ID,
        "verdict": verdict,
        "unique_max_oi_strike": published_pin,
        "unique_max_total_oi": published_total,
        "definition_coverage": oi_counts["definition_coverage"],
        "artifact_bindings": {
            "analysis_path": str(report_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "analysis_sha256": sha256_file(report_path),
            "analyzer_path": str(script_path.relative_to(workspace)).replace(
                "\\", "/"
            ),
            "analyzer_sha256": sha256_file(script_path),
            "published_surface_sha256": sha256_file(published_path),
            "zero_completed_surface_sha256": sha256_file(zero_path),
            "missing_definitions_sha256": sha256_file(missing_path),
        },
        "target_price_fields_used": [],
        "outcome_fields_used": [],
        "economic_verdict": "NOT_OPENED",
    }
    result_path = pilot_root / RESULT_RECEIPT
    analysis.write_json(result_path, result)
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
            f"CME6EOPTPIN002_{result['verdict']} "
            f"pin={result['unique_max_oi_strike']} "
            f"total_oi={result['unique_max_total_oi']} "
            f"coverage={result['definition_coverage']:.6f}"
        )
        print(f"RECEIPT {result_path}")
        return 0 if result["verdict"] == "SOURCE_PILOT_PASS" else 3
    except analysis.AnalysisError as exc:
        print(f"CME6EOPTPIN002_ANALYSIS_BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
