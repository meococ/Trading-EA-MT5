#!/usr/bin/env python3
"""Outcome-blind XAUUSD M15 Aroon-25 polarity-crossover source analyzer."""

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


HYPOTHESIS_ID = "HYP-AROON-XAUUSD-M15-001"
ATTEMPT_ID = "AROON001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "D2D3C8F358D4D77FCC6D6838D7F7315423E6A1473202E2AF0623AE5763BA85F8"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
MANIFEST_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
DATA_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/analyze_aroon_m15_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_AroonTrendRecency/research/tests/test_analyze_aroon_m15_source.py"
TEST_SHA256 = "767FE486CE56E878E871FF007626AB4E8870F782410C1447406C8C41CF2C41C7"
DATA_ACCESS_PREDICATE = "time_utc<2023-01-01T00:00:00Z;aggregate_complete_M5_triplets_to_M15;score_only_2018-01-01T00:00:00Z<=time_utc<2023-01-01T00:00:00Z"
SOURCE_START = pd.Timestamp("2004-06-11T04:15:00Z")
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
PERIOD = 25
DEPENDENCY_ROWS = 27
MIN_ROWS = 100_000
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
    "prior_aroon_up",
    "prior_aroon_down",
    "aroon_up",
    "aroon_down",
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


def validate_m5_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("reader materialized rows at or above the frozen upper bound")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.reset_index(drop=True)
    if data.empty or data.at[0, "time_utc"] != SOURCE_START or int(data.at[0, "source_epoch"]) % 900 != 0:
        raise ValueError("source frame does not begin at the frozen aligned M5 inception")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and strictly increasing")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("M5").all():
        raise ValueError("rows are not exclusively XAUUSD/M5")
    return data


def aggregate_m15(data: pd.DataFrame) -> pd.DataFrame:
    work = data.copy()
    work["bucket_epoch"] = (work["source_epoch"].astype(np.int64) // 900) * 900
    rows: list[dict[str, Any]] = []
    for bucket, group in work.groupby("bucket_epoch", sort=True):
        group = group.sort_values("source_epoch").reset_index(drop=True)
        expected_epochs = np.array([bucket, bucket + 300, bucket + 600], dtype=np.int64)
        epochs = group["source_epoch"].to_numpy(dtype=np.int64)
        prices = group.loc[:, ["high", "low", "close"]].to_numpy(dtype=float)
        exact_epochs = len(group) == 3 and np.array_equal(epochs, expected_epochs)
        exact_utc = len(group) == 3 and np.array_equal(
            np.diff(group["time_utc"].astype("int64").to_numpy()), np.array([300, 300], dtype=np.int64) * 1_000_000_000
        )
        price_valid = (
            len(group) == 3
            and np.isfinite(prices).all()
            and np.all(prices[:, 0] >= prices[:, 1])
            and np.all(prices[:, 2] >= prices[:, 1])
            and np.all(prices[:, 2] <= prices[:, 0])
            and np.all(prices[:, 2] > 0.0)
        )
        complete = bool(exact_epochs and exact_utc and price_valid)
        first_time = group.at[0, "time_utc"]
        rows.append(
            {
                "symbol": "XAUUSD",
                "timeframe": "M15",
                "source_epoch": int(bucket),
                "time_utc": first_time,
                "complete": complete,
                "high": float(group["high"].max()) if complete else math.nan,
                "low": float(group["low"].min()) if complete else math.nan,
                "close": float(group.at[2, "close"]) if complete else math.nan,
            }
        )
    result = pd.DataFrame(rows)
    if result.empty or result.at[0, "time_utc"] != SOURCE_START:
        raise ValueError("aggregated M15 frame does not preserve frozen inception")
    return result


def calculate_aroon(data: pd.DataFrame) -> dict[str, pd.Series]:
    high = pd.to_numeric(data["high"], errors="coerce").to_numpy(dtype=float)
    low = pd.to_numeric(data["low"], errors="coerce").to_numpy(dtype=float)
    complete = data["complete"].fillna(False).astype(bool).to_numpy()
    up = np.full(len(data), np.nan, dtype=float)
    down = np.full(len(data), np.nan, dtype=float)
    for index in range(PERIOD, len(data)):
        start = index - PERIOD
        if not complete[start : index + 1].all():
            continue
        highs = high[start : index + 1]
        lows = low[start : index + 1]
        if not (np.isfinite(highs).all() and np.isfinite(lows).all()):
            continue
        days_since_high = int(np.argmax(highs[::-1]))
        days_since_low = int(np.argmin(lows[::-1]))
        up[index] = (PERIOD - days_since_high) * 100.0 / PERIOD
        down[index] = (PERIOD - days_since_low) * 100.0 / PERIOD
    up_series = pd.Series(up, index=data.index, dtype=float)
    down_series = pd.Series(down, index=data.index, dtype=float)
    dependency_valid = pd.Series(complete.astype(int), index=data.index).rolling(DEPENDENCY_ROWS, min_periods=DEPENDENCY_ROWS).sum().eq(DEPENDENCY_ROWS)
    finite = pd.Series(
        np.isfinite(np.column_stack((up_series, down_series, up_series.shift(1), down_series.shift(1)))).all(axis=1),
        index=data.index,
        dtype=bool,
    )
    return {"aroon_up": up_series, "aroon_down": down_series, "feature_valid": dependency_valid & finite}


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    indicator = calculate_aroon(data)
    up = indicator["aroon_up"]
    down = indicator["aroon_down"]
    design = (data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)
    usable = indicator["feature_valid"] & design
    raw_long = usable & (up.shift(1) <= down.shift(1)) & (up > down)
    raw_short = usable & (up.shift(1) >= down.shift(1)) & (up < down)
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw = raw_long | raw_short
    exact_next = (
        data["source_epoch"].shift(-1).eq(data["source_epoch"] + 900)
        & ((data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(minutes=15))
    )
    executable = raw & exact_next
    events: list[dict[str, Any]] = []
    for index in data.index[executable]:
        bar_time = data.at[index, "time_utc"]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "source_bar_time_utc": bar_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (bar_time + pd.Timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
                "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
                "prior_aroon_up": finite_float(up.shift(1).loc[index]),
                "prior_aroon_down": finite_float(down.shift(1).loc[index]),
                "aroon_up": finite_float(up.loc[index]),
                "aroon_down": finite_float(down.loc[index]),
            }
        )
    raw_count = int(raw.sum())
    count = len(events)
    design_rows = int(design.sum())
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    cadence = count / elapsed_weeks
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    feature_coverage = int(usable.sum()) / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    event_years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, float | int]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {"events": year_count, "elapsed_weeks": weeks, "cadence_per_week": year_count / weeks, "share": year_count / count if count else 0.0}
    max_year_share = max((item["share"] for item in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": design_rows >= MIN_ROWS,
        "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_NEXT_COVERAGE,
        "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(MIN_YEAR_CADENCE <= item["cadence_per_week"] <= MAX_YEAR_CADENCE for item in yearly.values()),
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "aroon25_m15_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_AROON25_POLARITY_AND_CADENCE_ONLY",
        "source_window": {"from": SOURCE_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"timeframe": "M15_FROM_COMPLETE_M5_TRIPLETS", "period": PERIOD, "window_bars": PERIOD + 1, "tie_policy": "most_recent_extreme", "signal": "polarity_crossover"},
        "funnel": {
            "represented_m15_rows_through_design_end": int(len(data)),
            "prehistory_rows": int((data["time_utc"] < DESIGN_START).sum()),
            "design_rows": design_rows,
            "complete_design_rows": int((data["complete"] & design).sum()),
            "feature_usable_rows": int(usable.sum()),
            "raw_events": raw_count,
            "executable_events": count,
            "gap_rejected_events": raw_count - count,
            "direction_conflicts": int(conflicts.sum()),
            "long_events": longs,
            "short_events": shorts,
        },
        "metrics": {"elapsed_weeks": elapsed_weeks, "feature_coverage": feature_coverage, "raw_event_exact_next_coverage": next_coverage, "event_cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_event_share": max_year_share},
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_AROON_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_AROON25_POLARITY_CROSS",
        "prohibitions": {"post_event_ohlc_read": False, "returns_computed": False, "trades_simulated": False, "pnl_computed": False, "profit_factor_computed": False, "economics_executed": False, "validation_opened": False, "holdout_opened": False, "mql5_build_authorized_by_attempt": passed, "economic_build_authorized": False, "native_iaroon_claim_authorized": False, "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError(f"event-ledger keys differ from allowlist: {sorted(set(row))}")
    forbidden = [name for name, value in report["prohibitions"].items() if name != "mql5_build_authorized_by_attempt" and value is not False]
    if forbidden:
        raise ValueError(f"outcome-blind report contract failed: {forbidden}")


def validate_manifest(manifest_path: Path, data_path: Path) -> None:
    if sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ValueError("manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet")]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind frozen M5 data")
    if not data_path.as_posix().endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"):
        raise ValueError("unexpected M5 data path")


FALSE_PERMISSIONS = (
    "performance_metrics_authorized", "outcome_prices_authorized", "post_event_ohlc_authorized", "economics_authorized",
    "mt5_authorized", "model0_authorized", "model0_data_acquisition_authorized", "model0_performance_authorized", "model0_audit_run_authorized",
    "model4_authorized", "model4_data_acquisition_authorized", "model4_performance_authorized", "mt5_train_run_authorized", "mt5_audit_run_authorized",
    "mq5_authorized", "mql5_authorized", "compile_authorized", "run_compile_authorized", "mql5_compile_authorized", "standalone_compile_authorized",
    "packet_build_authorized", "trade_api_authorized", "artifact_collection_authorized", "comparator_execution_authorized", "optimization_authorized",
    "research_falsification_authorized", "economic_validity_authorized", "validation_authorized", "validation_access_authorized", "holdout_authorized",
    "holdout_access_authorized", "research_validation_access_authorized", "research_holdout_access_authorized", "visual_mode_authorized", "network_authorized",
    "paid_requests_authorized", "paper_trading_authorized", "promotion_eligible", "live_trading_authorized", "market_edge_claim_authorized",
    "same_id_retry_authorized", "registry_mutation_allowed", "native_iaroon_claim_authorized",
)
ZERO_METRICS = (
    "source_feasibility_attempts_consumed", "source_runs_executed", "post_event_ohlc_rows_read", "returns_computed", "trades_simulated",
    "performance_trials_executed", "model0_runs", "model4_runs", "mql5_files_created",
)


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
    checks = {
        "probe": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "run_ids_pristine": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "one_attempt": validation.get("source_feasibility_attempt_limit") == 1,
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
        "analyzer_sha": validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "test_path": validation.get("reviewed_test_path") == TEST_RELATIVE_PATH,
        "test_sha": validation.get("reviewed_test_sha256") == TEST_SHA256,
        "zero_metrics": all(metrics.get(name) == 0 for name in ZERO_METRICS),
        "validation_closed": metrics.get("research_validation_opened") is False,
        "holdout_closed": metrics.get("research_holdout_opened") is False,
        "false_permissions": all(validation.get(name) is False for name in FALSE_PERMISSIONS),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {"registry_sha256": hashlib.sha256(registry_bytes).hexdigest().upper(), "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper()}


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / "attempt_started.json"
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = {"schema_version": "aroon_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": sha256_file(Path(__file__).resolve()), "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"}
    try:
        with marker_path.open("xb") as handle:
            handle.write(json_bytes(marker))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("attempt already claimed") from exc
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_AroonTrendRecency/research/HYP-AROON-XAUUSD-M15-001_FROZEN_PREREG.md"
    manifest = root / MANIFEST_RELATIVE_PATH
    data_path = root / DATA_RELATIVE_PATH
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_AroonTrendRecency/research/evidence/HYP-AROON-XAUUSD-M15-001/AROON001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    if sha256_file(root / TEST_RELATIVE_PATH) != TEST_SHA256:
        raise ValueError("reviewed test SHA mismatch")
    validate_manifest(manifest, data_path)
    if sha256_file(data_path) != DATA_SHA256:
        raise ValueError("M5 data SHA mismatch")
    if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("Parquet schema missing required columns")
    raw = pd.read_parquet(data_path, columns=list(REQUIRED_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
    selected = validate_m5_frame(raw)
    aggregated = aggregate_m15(selected)
    events, report = analyze_frame(aggregated)
    assert_outcome_blind(events, report)
    replay_events, replay_report = analyze_frame(aggregated)
    if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
        raise ValueError("deterministic replay failed")
    report_bytes = json_bytes(report)
    ledger_bytes = jsonl_bytes(events)
    report_path = output_dir / "aroon_001_source_report.json"
    ledger_path = output_dir / "aroon_001_event_ledger.jsonl"
    atomic_write(report_path, report_bytes)
    atomic_write(ledger_path, ledger_bytes)
    receipt = {
        "schema_version": "aroon_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": sha256_file(prereg)},
            "manifest": {"path": MANIFEST_RELATIVE_PATH, "sha256": sha256_file(manifest)},
            "data": {"path": DATA_RELATIVE_PATH, "sha256": sha256_file(data_path)},
            "analyzer": {"path": ANALYZER_RELATIVE_PATH, "sha256": sha256_file(Path(__file__).resolve())},
            "tests": {"path": TEST_RELATIVE_PATH, "sha256": sha256_file(root / TEST_RELATIVE_PATH)},
            "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority},
            "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": sha256_file(start_path)},
            "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
            "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
        },
        "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0},
        "verdict": report["verdict"],
    }
    receipt_bytes = json_bytes(receipt)
    receipt_path = output_dir / "source_feasibility_receipt.json"
    atomic_write(receipt_path, receipt_bytes)
    terminal = {"schema_version": "aroon_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "same_id_retry_authorized": False}
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
