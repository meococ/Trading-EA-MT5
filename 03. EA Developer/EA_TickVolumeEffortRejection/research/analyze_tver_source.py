#!/usr/bin/env python3
"""Outcome-blind source/cadence analyzer for HYP-TVER-XAUUSD-M5-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-TVER-XAUUSD-M5-001"
ATTEMPT_ID = "TVER001-SOURCE-ATTEMPT-001"
FROZEN_PREREG_SHA256 = "047F5BD7D76291A15F00225AD5D71A9C79FECDA007E18F7B06A1A9A2F8C04F17"
FROZEN_MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
FROZEN_DATA_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"

DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
EXPECTED_SYMBOL = "XAUUSD"
EXPECTED_TIMEFRAME = "M5"

RV_LOOKBACK = 10
ATR_LOOKBACK = 14
RV_MIN = 2.00
RANGE_TO_ATR_MAX = 0.80
WICK_RATIO_MIN = 0.45
LONG_CLOSE_LOCATION_MIN = 0.60
SHORT_CLOSE_LOCATION_MAX = 0.40

MIN_DESIGN_ROWS = 300_000
MIN_FEATURE_COVERAGE = 0.99
MIN_EXACT_NEXT_COVERAGE = 0.97
MIN_CANDIDATES = 500
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.30
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50

REQUIRED_COLUMNS = (
    "symbol",
    "timeframe",
    "source_epoch",
    "time_utc",
    "utc_ambiguous",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
)
FORBIDDEN_OUTPUT_TOKENS = (
    "future",
    "return",
    "entry_price",
    "exit_price",
    "mfe",
    "mae",
    "profit",
    "pnl",
    "profit_factor",
    "drawdown",
    "spread",
    "commission",
    "slippage",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def canonical_jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _native_float(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric output: {value!r}")
    return number


def _year_elapsed_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def validate_and_select_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    selected = frame.loc[:, REQUIRED_COLUMNS].copy()
    selected["time_utc"] = pd.to_datetime(selected["time_utc"], utc=True, errors="raise")
    if ((selected["time_utc"] < DESIGN_START) | (selected["time_utc"] >= DESIGN_END)).any():
        raise ValueError("reader materialized rows outside the frozen design window")
    selected = selected.reset_index(drop=True)

    if len(selected) < MIN_DESIGN_ROWS:
        raise ValueError(f"design rows {len(selected)} below frozen minimum {MIN_DESIGN_ROWS}")
    if not selected["time_utc"].is_monotonic_increasing:
        raise ValueError("time_utc is not monotonically increasing")
    if selected["time_utc"].duplicated().any():
        raise ValueError("duplicate time_utc rows")
    if not selected["source_epoch"].is_monotonic_increasing:
        raise ValueError("source_epoch is not monotonically increasing")
    if selected["source_epoch"].duplicated().any():
        raise ValueError("duplicate source_epoch rows")
    if selected["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    if not selected["symbol"].eq(EXPECTED_SYMBOL).all():
        raise ValueError("selected rows are not exclusively XAUUSD")
    if not selected["timeframe"].eq(EXPECTED_TIMEFRAME).all():
        raise ValueError("selected rows are not exclusively M5")

    for column in ("open", "high", "low", "close", "tick_volume"):
        selected[column] = pd.to_numeric(selected[column], errors="raise")
    return selected


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Analyze an already selected ordered frame without any post-event outcome."""

    data = frame.copy().reset_index(drop=True)
    for column in ("open", "high", "low", "close", "tick_volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")

    price_columns = ["open", "high", "low", "close"]
    finite_prices = np.isfinite(data[price_columns].to_numpy(dtype=float)).all(axis=1)
    price_geometry_valid = (
        finite_prices
        & (data["high"] >= data[["open", "close"]].max(axis=1))
        & (data["low"] <= data[["open", "close"]].min(axis=1))
        & (data["high"] > data["low"])
    )
    volume_values = data["tick_volume"].to_numpy(dtype=float)
    volume_valid = pd.Series(
        np.isfinite(volume_values) & (volume_values > 0), index=data.index, dtype=bool
    )

    prior_close = data["close"].shift(1)
    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - prior_close).abs(),
            (data["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=False)
    prior_atr14 = true_range.shift(1).rolling(ATR_LOOKBACK, min_periods=ATR_LOOKBACK).mean()
    prior_volume10 = (
        data["tick_volume"].shift(1).rolling(RV_LOOKBACK, min_periods=RV_LOOKBACK).mean()
    )
    tr_input_valid = (
        price_geometry_valid
        & price_geometry_valid.shift(1, fill_value=False)
        & np.isfinite(true_range)
        & (true_range > 0)
    )
    prior_volume_all_valid10 = (
        volume_valid.astype(int)
        .shift(1)
        .rolling(RV_LOOKBACK, min_periods=RV_LOOKBACK)
        .sum()
        .eq(RV_LOOKBACK)
    )
    prior_tr_all_valid14 = (
        tr_input_valid.astype(int)
        .shift(1)
        .rolling(ATR_LOOKBACK, min_periods=ATR_LOOKBACK)
        .sum()
        .eq(ATR_LOOKBACK)
    )

    bar_range = data["high"] - data["low"]
    relative_volume = data["tick_volume"] / prior_volume10
    range_to_atr = bar_range / prior_atr14
    close_location = (data["close"] - data["low"]) / bar_range
    lower_wick_ratio = (data[["open", "close"]].min(axis=1) - data["low"]) / bar_range
    upper_wick_ratio = (data["high"] - data[["open", "close"]].max(axis=1)) / bar_range

    feature_usable = (
        price_geometry_valid
        & volume_valid
        & prior_volume_all_valid10
        & prior_tr_all_valid14
        & np.isfinite(relative_volume)
        & np.isfinite(range_to_atr)
        & np.isfinite(close_location)
        & np.isfinite(lower_wick_ratio)
        & np.isfinite(upper_wick_ratio)
        & (prior_volume10 > 0)
        & (prior_atr14 > 0)
    )
    exact_next_m5 = (data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(minutes=5)
    source_usable = feature_usable & exact_next_m5

    high_effort = source_usable & (relative_volume >= RV_MIN)
    low_progress = high_effort & (range_to_atr <= RANGE_TO_ATR_MAX)
    long_raw = (
        low_progress
        & (lower_wick_ratio >= WICK_RATIO_MIN)
        & (close_location >= LONG_CLOSE_LOCATION_MIN)
    )
    short_raw = (
        low_progress
        & (upper_wick_ratio >= WICK_RATIO_MIN)
        & (close_location <= SHORT_CLOSE_LOCATION_MAX)
    )
    conflicts = long_raw & short_raw
    long_signal = long_raw & ~conflicts
    short_signal = short_raw & ~conflicts
    candidate_mask = long_signal | short_signal

    candidates: list[dict[str, Any]] = []
    for index in data.index[candidate_mask]:
        direction = "LONG" if bool(long_signal.loc[index]) else "SHORT"
        bar_time = data.at[index, "time_utc"]
        row = {
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_open_utc": bar_time.isoformat().replace("+00:00", "Z"),
            "decision_time_utc": (bar_time + pd.Timedelta(minutes=5))
            .isoformat()
            .replace("+00:00", "Z"),
            "direction": direction,
            "tick_volume": int(data.at[index, "tick_volume"]),
            "prior_volume10": _native_float(prior_volume10.loc[index]),
            "relative_volume10": _native_float(relative_volume.loc[index]),
            "prior_atr14": _native_float(prior_atr14.loc[index]),
            "range_to_prior_atr14": _native_float(range_to_atr.loc[index]),
            "lower_wick_ratio": _native_float(lower_wick_ratio.loc[index]),
            "upper_wick_ratio": _native_float(upper_wick_ratio.loc[index]),
            "close_location": _native_float(close_location.loc[index]),
        }
        candidates.append(row)

    total_candidates = len(candidates)
    long_count = int(long_signal.sum())
    short_count = int(short_signal.sum())
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    cadence = total_candidates / elapsed_weeks
    long_share = long_count / total_candidates if total_candidates else 0.0
    short_share = short_count / total_candidates if total_candidates else 0.0

    warmup_denominator = max(len(data) - (ATR_LOOKBACK + 1), 1)
    feature_coverage = int(feature_usable.iloc[ATR_LOOKBACK + 1 :].sum()) / warmup_denominator
    next_denominator = max(int(feature_usable.iloc[:-1].sum()), 1)
    exact_next_coverage = int((feature_usable & exact_next_m5).iloc[:-1].sum()) / next_denominator

    yearly: dict[str, dict[str, Any]] = {}
    candidate_years = pd.Series(
        [pd.Timestamp(row["source_bar_open_utc"]).year for row in candidates], dtype="int64"
    )
    for year in range(2018, 2023):
        count = int((candidate_years == year).sum()) if total_candidates else 0
        weeks = _year_elapsed_weeks(year)
        year_cadence = count / weeks
        yearly[str(year)] = {
            "candidates": count,
            "elapsed_weeks": weeks,
            "cadence_per_week": year_cadence,
            "share": count / total_candidates if total_candidates else 0.0,
        }

    max_year_candidate_share = max((entry["share"] for entry in yearly.values()), default=0.0)
    yearly_cadence_pass = all(
        MIN_YEAR_CADENCE <= entry["cadence_per_week"] <= MAX_YEAR_CADENCE
        for entry in yearly.values()
    )

    gates = {
        "minimum_design_rows": len(data) >= MIN_DESIGN_ROWS,
        "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "exact_next_m5_coverage": exact_next_coverage >= MIN_EXACT_NEXT_COVERAGE,
        "minimum_candidates": total_candidates >= MIN_CANDIDATES,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE
        and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_candidate_share <= MAX_YEAR_SHARE,
        "each_year_cadence": yearly_cadence_pass,
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    all_gates_pass = all(gates.values())

    report = {
        "schema_version": "tver_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {
            "relative_volume_lookback": RV_LOOKBACK,
            "relative_volume_min": RV_MIN,
            "prior_atr_lookback": ATR_LOOKBACK,
            "range_to_prior_atr_max": RANGE_TO_ATR_MAX,
            "wick_ratio_min": WICK_RATIO_MIN,
            "long_close_location_min": LONG_CLOSE_LOCATION_MIN,
            "short_close_location_max": SHORT_CLOSE_LOCATION_MAX,
        },
        "funnel": {
            "design_rows": int(len(data)),
            "feature_usable_rows": int(feature_usable.sum()),
            "source_usable_exact_next_rows": int(source_usable.sum()),
            "high_effort_rows": int(high_effort.sum()),
            "low_progress_rows": int(low_progress.sum()),
            "long_candidates": long_count,
            "short_candidates": short_count,
            "direction_conflicts": int(conflicts.sum()),
            "candidates": total_candidates,
        },
        "metrics": {
            "elapsed_weeks": elapsed_weeks,
            "feature_coverage": feature_coverage,
            "exact_next_m5_coverage": exact_next_coverage,
            "candidate_cadence_per_week": cadence,
            "long_share": long_share,
            "short_share": short_share,
            "max_year_candidate_share": max_year_candidate_share,
        },
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": all_gates_pass,
        "verdict": (
            "SCREENED_SOURCE_PASS_MQL5_INDICATOR_BUILD_AUTHORIZED"
            if all_gates_pass
            else "PARK_SOURCE_FEASIBILITY_EXACT_TVER_MAPPING"
        ),
        "prohibitions": {
            "future_ohlc_read": False,
            "returns_computed": False,
            "trades_simulated": False,
            "economics_executed": False,
            "validation_opened": False,
            "holdout_opened": False,
            "mql5_build_authorized_by_attempt": all_gates_pass,
            "economic_build_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return candidates, report


def assert_output_is_outcome_blind(candidates: list[dict[str, Any]], report: dict[str, Any]) -> None:
    keys: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                keys.add(str(key).lower())
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(candidates)
    for key in keys:
        if any(token in key for token in FORBIDDEN_OUTPUT_TOKENS):
            raise ValueError(f"forbidden outcome/economic field in candidate ledger: {key}")

    if report["prohibitions"]["future_ohlc_read"] is not False:
        raise ValueError("report does not preserve outcome-blind scope")


def validate_manifest(manifest_path: Path, data_path: Path) -> None:
    if sha256_file(manifest_path) != FROZEN_MANIFEST_SHA256:
        raise ValueError("manifest SHA256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_data_path = data_path.as_posix()
    matching = [
        item
        for item in manifest.get("files", [])
        if str(item.get("path", "")).replace("\\", "/").endswith(
            "XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
        )
    ]
    if len(matching) != 1 or matching[0].get("sha256") != FROZEN_DATA_SHA256:
        raise ValueError("manifest does not bind the frozen XAUUSD M5 source")
    if not relative_data_path.endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"):
        raise ValueError("unexpected data path")


def validate_registry_authority(registry_path: Path) -> dict[str, Any]:
    matching: list[tuple[bytes, dict[str, Any]]] = []
    for raw_line in registry_path.read_bytes().splitlines():
        if not raw_line.strip():
            continue
        row = json.loads(raw_line.decode("utf-8"))
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matching.append((raw_line, row))
    if not matching:
        raise ValueError("no registry authority row for frozen hypothesis")

    raw_line, latest = matching[-1]
    validation = latest.get("validation", {})
    metrics = latest.get("metrics", {})
    analyzer_hash = sha256_file(Path(__file__).resolve())
    required = {
        "state_is_probe": latest.get("state") == "probe",
        "verdict_authorizes_source": latest.get("verdict")
        == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg_hash_matches": latest.get("prereg_sha256") == FROZEN_PREREG_SHA256,
        "attempt_id_matches": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "attempt_limit_is_one": validation.get("source_feasibility_attempt_limit") == 1,
        "attempt_unconsumed": metrics.get("source_feasibility_attempts_consumed") == 0,
        "source_run_authorized": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "analyzer_hash_matches": validation.get("reviewed_analyzer_sha256") == analyzer_hash,
        "economics_forbidden": validation.get("economics_authorized") is False,
        "outcomes_forbidden": validation.get("outcome_prices_authorized") is False,
        "validation_forbidden": validation.get("research_validation_access_authorized") is False,
        "holdout_forbidden": validation.get("research_holdout_access_authorized") is False,
        "mt5_forbidden": validation.get("mt5_authorized") is False,
        "mql5_forbidden": validation.get("mql5_authorized") is False,
        "live_forbidden": validation.get("live_trading_authorized") is False,
    }
    failed = [name for name, passed in required.items() if not passed]
    if failed:
        raise ValueError(f"registry authority failed closed: {failed}")
    return {
        "latest_row": latest,
        "latest_row_sha256": hashlib.sha256(raw_line).hexdigest().upper(),
        "registry_sha256": sha256_file(registry_path),
    }


def claim_attempt(output_dir: Path, registry_authority: dict[str, Any]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists; same-ID retry is forbidden")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / "attempt_started.json"
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = {
        "schema_version": "tver_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started_at,
        "process_id": os.getpid(),
        "registry_sha256": registry_authority["registry_sha256"],
        "latest_hypothesis_row_sha256": registry_authority["latest_row_sha256"],
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED",
    }
    marker_bytes = canonical_json_bytes(marker)
    try:
        with marker_path.open("xb") as handle:
            handle.write(marker_bytes)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("attempt already claimed by another process") from exc
    return started_at, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg_path = root / "03. EA Developer/EA_TickVolumeEffortRejection/research/HYP-TVER-XAUUSD-M5-001_FROZEN_PREREG.md"
    manifest_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
    registry_path = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_TickVolumeEffortRejection/research/evidence/HYP-TVER-XAUUSD-M5-001/TVER001-SOURCE-ATTEMPT-001"

    if sha256_file(prereg_path) != FROZEN_PREREG_SHA256:
        raise ValueError("frozen preregistration SHA256 mismatch")
    registry_authority = validate_registry_authority(registry_path)
    started_at, attempt_started_path = claim_attempt(output_dir, registry_authority)
    validate_manifest(manifest_path, data_path)
    if sha256_file(data_path) != FROZEN_DATA_SHA256:
        raise ValueError("frozen Parquet SHA256 mismatch")

    schema_names = set(pq.ParquetFile(data_path).schema_arrow.names)
    missing = sorted(set(REQUIRED_COLUMNS) - schema_names)
    if missing:
        raise ValueError(f"Parquet schema missing required columns: {missing}")

    raw = pd.read_parquet(
        data_path,
        columns=list(REQUIRED_COLUMNS),
        filters=[
            ("time_utc", ">=", DESIGN_START.to_pydatetime()),
            ("time_utc", "<", DESIGN_END.to_pydatetime()),
        ],
        engine="pyarrow",
    )
    selected = validate_and_select_frame(raw)
    candidates, report = analyze_frame(selected)
    assert_output_is_outcome_blind(candidates, report)
    replay_candidates, replay_report = analyze_frame(selected)
    if canonical_jsonl_bytes(candidates) != canonical_jsonl_bytes(replay_candidates):
        raise ValueError("deterministic candidate-ledger replay failed")
    if canonical_json_bytes(report) != canonical_json_bytes(replay_report):
        raise ValueError("deterministic source-report replay failed")

    report_bytes = canonical_json_bytes(report)
    ledger_bytes = canonical_jsonl_bytes(candidates)
    report_path = output_dir / "tver_001_source_report.json"
    ledger_path = output_dir / "tver_001_candidate_ledger.jsonl"
    atomic_write(report_path, report_bytes)
    atomic_write(ledger_path, ledger_bytes)

    receipt = {
        "schema_version": "tver_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "preregistration": {"path": prereg_path.relative_to(root).as_posix(), "sha256": sha256_file(prereg_path)},
            "manifest": {"path": manifest_path.relative_to(root).as_posix(), "sha256": sha256_file(manifest_path)},
            "data": {"path": data_path.relative_to(root).as_posix(), "sha256": sha256_file(data_path)},
            "analyzer": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "candidate_registry": {
                "path": registry_path.relative_to(root).as_posix(),
                "sha256": registry_authority["registry_sha256"],
                "latest_hypothesis_row_sha256": registry_authority["latest_row_sha256"],
            },
            "attempt_started": {
                "path": attempt_started_path.relative_to(root).as_posix(),
                "sha256": sha256_file(attempt_started_path),
            },
            "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
            "candidate_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
        },
        "outcome_blind_counters": {
            "post_event_ohlc_rows_read": 0,
            "returns_computed": 0,
            "trades_simulated": 0,
            "pnl_computed": 0,
            "profit_factor_computed": 0,
            "validation_rows_read": 0,
            "holdout_rows_read": 0,
        },
        "verdict": report["verdict"],
    }
    receipt_bytes = canonical_json_bytes(receipt)
    receipt_path = output_dir / "source_feasibility_receipt.json"
    atomic_write(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "tver_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": receipt["completed_at_utc"],
        "status": "COMPLETE",
        "verdict": report["verdict"],
        "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    terminal_path = output_dir / "attempt_terminal.json"
    atomic_write(terminal_path, canonical_json_bytes(terminal))
    return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the sole frozen source/cadence attempt and write canonical evidence.",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required; dry inspection does not open the frozen data")

    root = Path(__file__).resolve().parents[3]
    result = execute(root)
    print(canonical_json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
