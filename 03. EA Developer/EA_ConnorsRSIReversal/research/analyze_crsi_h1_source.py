#!/usr/bin/env python3
"""Outcome-blind native-H1 Connors RSI(3,2,100) extreme-reentry source analyzer."""

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


HYPOTHESIS_ID = "HYP-CRSI-XAUUSD-H1-001"
ATTEMPT_ID = "CRSI001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "70951DE02291AA490F0F0D06B27A43AEE495A7D5AD43AA8C7A770A4E9CBB84F6"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
MANIFEST_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
DATA_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_ConnorsRSIReversal/research/analyze_crsi_h1_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_ConnorsRSIReversal/research/tests/test_analyze_crsi_h1_source.py"
TEST_SHA256 = "6189C091B5A54D838A81201B8E4A7F247BCDC54C3E0BC7E3CFBBF367DD7EBF4B"
DATA_ACCESS_PREDICATE = "time_utc<2023-01-01T00:00:00Z;score_only_2018-01-01T00:00:00Z<=time_utc<2023-01-01T00:00:00Z"
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
SOURCE_START = pd.Timestamp("2004-06-11T04:00:00Z")
RSI_CLOSE_LENGTH = 3
RSI_STREAK_LENGTH = 2
PERCENT_RANK_LENGTH = 100
LOWER_EXTREME = 10.0
UPPER_EXTREME = 90.0
WARMUP_ROWS = 102
DEPENDENCY_ROWS = 103
MIN_ROWS = 25_000
MIN_FEATURE_COVERAGE = 0.99
MIN_NEXT_COVERAGE = 0.97
MIN_EVENTS = 500
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.30
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "high", "low", "close")
EVENT_KEYS = {
    "hypothesis_id",
    "source_bar_time_utc",
    "decision_time_utc",
    "direction",
    "prior_crsi",
    "crsi",
    "rsi_close_3",
    "rsi_streak_2",
    "percent_rank_100",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def finite_float(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite output: {value!r}")
    return result


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def validate_source_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("reader materialized rows at or above the frozen upper bound")
    data = data.reset_index(drop=True)
    if data.empty or data.at[0, "time_utc"] != SOURCE_START:
        raise ValueError("source frame does not begin at the frozen native H1 inception")
    design_rows = int(((data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)).sum())
    if design_rows < MIN_ROWS:
        raise ValueError(f"design rows {design_rows} below {MIN_ROWS}")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and strictly increasing")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    if not data["symbol"].eq("XAUUSD").all():
        raise ValueError("rows are not exclusively XAUUSD")
    if not data["timeframe"].eq("H1").all():
        raise ValueError("rows are not exclusively H1")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    close_values = data["close"].to_numpy(dtype=float)
    if not np.isfinite(close_values).all() or not (close_values > 0.0).all():
        raise ValueError("every inception-through-design close must be finite and strictly positive")
    return data


def wilder_rsi(series: pd.Series, length: int) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    avg_gain = math.nan
    avg_loss = math.nan
    previous_ready = False
    for index in range(length, len(values)):
        window = values[index - length : index + 1]
        if not np.isfinite(window).all():
            previous_ready = False
            avg_gain = math.nan
            avg_loss = math.nan
            continue
        delta = values[index] - values[index - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        if previous_ready:
            avg_gain = ((length - 1) * avg_gain + gain) / length
            avg_loss = ((length - 1) * avg_loss + loss) / length
        else:
            deltas = np.diff(window)
            avg_gain = float(np.maximum(deltas, 0.0).mean())
            avg_loss = float(np.maximum(-deltas, 0.0).mean())
            previous_ready = True
        if avg_gain == 0.0 and avg_loss == 0.0:
            result[index] = 50.0
        elif avg_loss == 0.0:
            result[index] = 100.0
        elif avg_gain == 0.0:
            result[index] = 0.0
        else:
            result[index] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return pd.Series(result, index=series.index, dtype=float)


def calculate_streak(close: pd.Series) -> pd.Series:
    values = pd.to_numeric(close, errors="coerce").to_numpy(dtype=float)
    streak = np.full(len(values), np.nan, dtype=float)
    if len(values) and math.isfinite(values[0]):
        streak[0] = 0.0
    for index in range(1, len(values)):
        if not (math.isfinite(values[index]) and math.isfinite(values[index - 1])):
            continue
        previous = streak[index - 1] if math.isfinite(streak[index - 1]) else 0.0
        if values[index] > values[index - 1]:
            streak[index] = max(previous, 0.0) + 1.0
        elif values[index] < values[index - 1]:
            streak[index] = min(previous, 0.0) - 1.0
        else:
            streak[index] = 0.0
    return pd.Series(streak, index=close.index, dtype=float)


def calculate_percent_rank(close: pd.Series, length: int = PERCENT_RANK_LENGTH) -> tuple[pd.Series, pd.Series]:
    values = pd.to_numeric(close, errors="coerce").to_numpy(dtype=float)
    roc = np.full(len(values), np.nan, dtype=float)
    valid_pair = np.isfinite(values[1:]) & np.isfinite(values[:-1]) & (values[1:] > 0.0) & (values[:-1] > 0.0)
    pair_indices = np.nonzero(valid_pair)[0] + 1
    roc[pair_indices] = 100.0 * (values[pair_indices] / values[pair_indices - 1] - 1.0)
    rank = np.full(len(values), np.nan, dtype=float)
    for index in range(length + 1, len(values)):
        previous = roc[index - length : index]
        if math.isfinite(roc[index]) and np.isfinite(previous).all():
            rank[index] = float(np.count_nonzero(previous < roc[index]))
    return pd.Series(roc, index=close.index, dtype=float), pd.Series(rank, index=close.index, dtype=float)


def calculate_crsi(data: pd.DataFrame) -> dict[str, pd.Series]:
    high = pd.to_numeric(data["high"], errors="coerce").astype(float)
    low = pd.to_numeric(data["low"], errors="coerce").astype(float)
    close = pd.to_numeric(data["close"], errors="coerce").astype(float)
    geometry_valid = pd.Series(
        np.isfinite(np.column_stack((high, low, close))).all(axis=1)
        & (high.to_numpy() >= low.to_numpy())
        & (close.to_numpy() >= low.to_numpy())
        & (close.to_numpy() <= high.to_numpy())
        & (close.to_numpy() > 0.0),
        index=data.index,
        dtype=bool,
    )
    streak = calculate_streak(close)
    rsi_close = wilder_rsi(close, RSI_CLOSE_LENGTH)
    rsi_streak = wilder_rsi(streak, RSI_STREAK_LENGTH)
    roc1, percent_rank = calculate_percent_rank(close)
    crsi = (rsi_close + rsi_streak + percent_rank) / 3.0
    dependency_valid = geometry_valid.astype(int).rolling(DEPENDENCY_ROWS, min_periods=DEPENDENCY_ROWS).sum().eq(DEPENDENCY_ROWS)
    finite_feature = pd.Series(
        np.isfinite(np.column_stack((crsi, crsi.shift(1), rsi_close, rsi_streak, percent_rank))).all(axis=1),
        index=data.index,
        dtype=bool,
    )
    feature_valid = dependency_valid & finite_feature
    return {
        "streak": streak,
        "roc1": roc1,
        "rsi_close": rsi_close,
        "rsi_streak": rsi_streak,
        "percent_rank": percent_rank,
        "crsi": crsi,
        "feature_valid": feature_valid,
    }


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    indicator = calculate_crsi(data)
    crsi = indicator["crsi"]
    design_mask = (data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)
    usable = indicator["feature_valid"] & design_mask
    raw_long = usable & (crsi.shift(1) < LOWER_EXTREME) & (crsi >= LOWER_EXTREME)
    raw_short = usable & (crsi.shift(1) > UPPER_EXTREME) & (crsi <= UPPER_EXTREME)
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw_mask = raw_long | raw_short
    exact_next = (data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(hours=1)
    event_mask = raw_mask & exact_next
    events: list[dict[str, Any]] = []
    for index in data.index[event_mask]:
        bar_time = data.at[index, "time_utc"]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "source_bar_time_utc": bar_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (bar_time + pd.Timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
                "prior_crsi": finite_float(crsi.shift(1).loc[index]),
                "crsi": finite_float(crsi.loc[index]),
                "rsi_close_3": finite_float(indicator["rsi_close"].loc[index]),
                "rsi_streak_2": finite_float(indicator["rsi_streak"].loc[index]),
                "percent_rank_100": finite_float(indicator["percent_rank"].loc[index]),
            }
        )
    raw_count = int(raw_mask.sum())
    count = len(events)
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    cadence = count / elapsed_weeks
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    design_rows = int(design_mask.sum())
    feature_coverage = int(usable.sum()) / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    event_years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, float | int]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {
            "events": year_count,
            "elapsed_weeks": weeks,
            "cadence_per_week": year_count / weeks,
            "share": year_count / count if count else 0.0,
        }
    max_year_share = max((row["share"] for row in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": design_rows >= MIN_ROWS,
        "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_NEXT_COVERAGE,
        "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(MIN_YEAR_CADENCE <= row["cadence_per_week"] <= MAX_YEAR_CADENCE for row in yearly.values()),
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "crsi_3_2_100_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_CRSI_EXTREME_REENTRY_AND_CADENCE_ONLY",
        "source_window": {"from": SOURCE_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {
            "timeframe": "H1",
            "rsi_close_length": RSI_CLOSE_LENGTH,
            "rsi_streak_length": RSI_STREAK_LENGTH,
            "percent_rank_length": PERCENT_RANK_LENGTH,
            "lower_extreme": LOWER_EXTREME,
            "upper_extreme": UPPER_EXTREME,
            "signal": "confirmed_reentry_from_extreme",
        },
        "funnel": {
            "source_rows_through_design_end": int(len(data)),
            "prehistory_rows": int((data["time_utc"] < DESIGN_START).sum()),
            "design_rows": design_rows,
            "feature_usable_rows": int(usable.sum()),
            "raw_events": raw_count,
            "executable_events": count,
            "gap_rejected_events": raw_count - count,
            "direction_conflicts": int(conflicts.sum()),
            "long_events": longs,
            "short_events": shorts,
        },
        "metrics": {
            "elapsed_weeks": elapsed_weeks,
            "feature_coverage": feature_coverage,
            "raw_event_exact_next_coverage": next_coverage,
            "event_cadence_per_week": cadence,
            "long_share": long_share,
            "short_share": short_share,
            "max_year_event_share": max_year_share,
        },
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_CRSI_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_CRSI_3_2_100_EXTREME_REENTRY",
        "prohibitions": {
            "post_event_ohlc_read": False,
            "returns_computed": False,
            "trades_simulated": False,
            "pnl_computed": False,
            "profit_factor_computed": False,
            "economics_executed": False,
            "validation_opened": False,
            "holdout_opened": False,
            "mql5_build_authorized_by_attempt": passed,
            "economic_build_authorized": False,
            "native_iconnorsrsi_claim_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError(f"event-ledger keys differ from allowlist: {sorted(set(row))}")
    forbidden_true = [name for name, value in report["prohibitions"].items() if name not in {"mql5_build_authorized_by_attempt"} and value is not False]
    if forbidden_true:
        raise ValueError(f"outcome-blind report contract failed: {forbidden_true}")


def validate_manifest(manifest_path: Path, data_path: Path) -> None:
    if sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ValueError("manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [
        item
        for item in manifest.get("files", [])
        if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")
    ]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind frozen H1 data")
    if not data_path.as_posix().endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"):
        raise ValueError("unexpected H1 data path")


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    registry_bytes = registry_path.read_bytes()
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_bytes.splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing registry authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    false_permissions = (
        "performance_metrics_authorized",
        "outcome_prices_authorized",
        "post_event_ohlc_authorized",
        "economics_authorized",
        "mt5_authorized",
        "model0_authorized",
        "model0_data_acquisition_authorized",
        "model0_performance_authorized",
        "model0_audit_run_authorized",
        "model4_authorized",
        "model4_data_acquisition_authorized",
        "model4_performance_authorized",
        "mt5_train_run_authorized",
        "mt5_audit_run_authorized",
        "mq5_authorized",
        "mql5_authorized",
        "compile_authorized",
        "run_compile_authorized",
        "mql5_compile_authorized",
        "standalone_compile_authorized",
        "packet_build_authorized",
        "trade_api_authorized",
        "artifact_collection_authorized",
        "comparator_execution_authorized",
        "optimization_authorized",
        "research_falsification_authorized",
        "economic_validity_authorized",
        "validation_authorized",
        "validation_access_authorized",
        "holdout_authorized",
        "holdout_access_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "visual_mode_authorized",
        "network_authorized",
        "paid_requests_authorized",
        "paper_trading_authorized",
        "promotion_eligible",
        "live_trading_authorized",
        "market_edge_claim_authorized",
        "same_id_retry_authorized",
        "registry_mutation_allowed",
    )
    zero_metrics = (
        "source_feasibility_attempts_consumed",
        "source_runs_executed",
        "post_event_ohlc_rows_read",
        "returns_computed",
        "trades_simulated",
        "performance_trials_executed",
        "model0_runs",
        "model4_runs",
        "mql5_files_created",
    )
    checks = {
        "probe": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "run_ids_pristine": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "one_attempt": validation.get("source_feasibility_attempt_limit") == 1,
        "unconsumed": metrics.get("source_feasibility_attempts_consumed") == 0,
        "source_run": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "prehistory_authorized": validation.get("prehistory_source_access_authorized") is True,
        "prehistory_start": validation.get("prehistory_source_start") == SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest_path": validation.get("manifest_path") == MANIFEST_RELATIVE_PATH,
        "manifest_sha": validation.get("manifest_sha256") == MANIFEST_SHA256,
        "data_path": validation.get("data_path") == DATA_RELATIVE_PATH,
        "data_sha": validation.get("data_sha256") == DATA_SHA256,
        "data_predicate": validation.get("data_access_predicate") == DATA_ACCESS_PREDICATE,
        "analyzer_path": validation.get("reviewed_analyzer_path") == ANALYZER_RELATIVE_PATH,
        "analyzer": validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "test_path": validation.get("reviewed_test_path") == TEST_RELATIVE_PATH,
        "test_sha": validation.get("reviewed_test_sha256") == TEST_SHA256,
        "zero_metrics": all(metrics.get(name) == 0 for name in zero_metrics),
        "validation_closed": metrics.get("research_validation_opened") is False,
        "holdout_closed": metrics.get("research_holdout_opened") is False,
        "false_permissions": all(validation.get(name) is False for name in false_permissions),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest().upper(),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / "attempt_started.json"
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = {
        "schema_version": "crsi_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "process_id": os.getpid(),
        "registry_sha256": authority["registry_sha256"],
        "latest_hypothesis_row_sha256": authority["latest_row_sha256"],
        "analyzer_sha256": sha256_file(Path(__file__).resolve()),
        "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED",
    }
    try:
        with marker_path.open("xb") as handle:
            handle.write(json_bytes(marker))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("attempt already claimed") from exc
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_ConnorsRSIReversal/research/HYP-CRSI-XAUUSD-H1-001_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_ConnorsRSIReversal/research/evidence/HYP-CRSI-XAUUSD-H1-001/CRSI001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    if sha256_file(root / TEST_RELATIVE_PATH) != TEST_SHA256:
        raise ValueError("reviewed test SHA mismatch")
    validate_manifest(manifest, data_path)
    if sha256_file(data_path) != DATA_SHA256:
        raise ValueError("H1 data SHA mismatch")
    if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("Parquet schema missing required columns")
    raw = pd.read_parquet(
        data_path,
        columns=list(REQUIRED_COLUMNS),
        filters=[("time_utc", "<", DESIGN_END.to_pydatetime())],
        engine="pyarrow",
    )
    selected = validate_source_frame(raw)
    events, report = analyze_frame(selected)
    assert_outcome_blind(events, report)
    replay_events, replay_report = analyze_frame(selected)
    if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
        raise ValueError("deterministic replay failed")
    report_bytes = json_bytes(report)
    ledger_bytes = jsonl_bytes(events)
    report_path = output_dir / "crsi_001_source_report.json"
    ledger_path = output_dir / "crsi_001_event_ledger.jsonl"
    atomic_write(report_path, report_bytes)
    atomic_write(ledger_path, ledger_bytes)
    receipt = {
        "schema_version": "crsi_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": sha256_file(prereg)},
            "manifest": {"path": manifest.relative_to(root).as_posix(), "sha256": sha256_file(manifest)},
            "data": {"path": data_path.relative_to(root).as_posix(), "sha256": sha256_file(data_path)},
            "analyzer": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "tests": {"path": TEST_RELATIVE_PATH, "sha256": sha256_file(root / TEST_RELATIVE_PATH)},
            "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority},
            "source_authority_contract": {
                "prehistory_source_start": SOURCE_START.isoformat().replace("+00:00", "Z"),
                "manifest_path": MANIFEST_RELATIVE_PATH,
                "manifest_sha256": MANIFEST_SHA256,
                "data_path": DATA_RELATIVE_PATH,
                "data_sha256": DATA_SHA256,
                "data_access_predicate": DATA_ACCESS_PREDICATE,
                "reviewed_test_path": TEST_RELATIVE_PATH,
                "reviewed_test_sha256": TEST_SHA256,
            },
            "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)},
            "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
            "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
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
    receipt_bytes = json_bytes(receipt)
    receipt_path = output_dir / "source_feasibility_receipt.json"
    atomic_write(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "crsi_source_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": receipt["completed_at_utc"],
        "status": "COMPLETE",
        "verdict": report["verdict"],
        "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    atomic_write(output_dir / "attempt_terminal.json", json_bytes(terminal))
    return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    result = execute(Path(__file__).resolve().parents[3])
    print(json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
