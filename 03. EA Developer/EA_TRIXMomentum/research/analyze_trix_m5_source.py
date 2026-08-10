#!/usr/bin/env python3
"""Outcome-blind native-M5 TRIX-18 zero-line source analyzer."""

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


HYPOTHESIS_ID = "HYP-TRIX-XAUUSD-M5-001"
ATTEMPT_ID = "TRIX001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "CBA2887C70AD3FF522ACCA175A45D9EAAEB1A3307AE524606F29571611BCE77C"
TEST_SHA256 = "192EC349277F8814546F317A094CFD761CE7533DA5C6724BC71F39807026C337"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
MANIFEST_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
DATA_RELATIVE_PATH = "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
ANALYZER_RELATIVE_PATH = "03. EA Developer/EA_TRIXMomentum/research/analyze_trix_m5_source.py"
TEST_RELATIVE_PATH = "03. EA Developer/EA_TRIXMomentum/research/tests/test_analyze_trix_m5_source.py"
PREREG_RELATIVE_PATH = "03. EA Developer/EA_TRIXMomentum/research/HYP-TRIX-XAUUSD-M5-001_FROZEN_PREREG.md"
DATA_ACCESS_PREDICATE = "time_utc<2023-01-01T00:00:00Z;score_only_2018-01-01T00:00:00Z<=time_utc<2023-01-01T00:00:00Z"
SOURCE_START = pd.Timestamp("2004-06-11T04:15:00Z")
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
PERIOD = 18
ALPHA = 2.0 / (PERIOD + 1.0)
FIRST_TRIX_INDEX = 52
FIRST_EVENT_INDEX = 53
MIN_ROWS = 300_000
MIN_FEATURE_COVERAGE = 0.999
MIN_NEXT_COVERAGE = 0.97
MIN_EVENTS = 500
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.30
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "close")
EVENT_KEYS = {"hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction", "prior_trix", "trix"}
FALSE_PERMISSIONS = (
    "performance_metrics_authorized", "outcome_prices_authorized", "post_event_ohlc_authorized", "economics_authorized",
    "mt5_authorized", "model0_authorized", "model0_data_acquisition_authorized", "model0_performance_authorized", "model0_audit_run_authorized",
    "model4_authorized", "model4_data_acquisition_authorized", "model4_performance_authorized", "mt5_train_run_authorized", "mt5_audit_run_authorized",
    "mq5_authorized", "mql5_authorized", "compile_authorized", "run_compile_authorized", "mql5_compile_authorized", "standalone_compile_authorized",
    "packet_build_authorized", "trade_api_authorized", "artifact_collection_authorized", "comparator_execution_authorized", "optimization_authorized",
    "research_falsification_authorized", "economic_validity_authorized", "validation_authorized", "validation_access_authorized", "holdout_authorized",
    "holdout_access_authorized", "research_validation_access_authorized", "research_holdout_access_authorized", "visual_mode_authorized", "network_authorized",
    "paid_requests_authorized", "paper_trading_authorized", "promotion_eligible", "live_trading_authorized", "market_edge_claim_authorized",
    "same_id_retry_authorized", "registry_mutation_allowed", "native_itrix_parity_authorized", "native_itrix_economic_claim_authorized",
)
ZERO_METRICS = (
    "source_feasibility_attempts_consumed", "source_runs_executed", "post_event_ohlc_rows_read", "returns_computed", "trades_simulated",
    "performance_trials_executed", "model0_runs", "model4_runs", "mql5_files_created",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError(f"exclusive artifact already exists: {path.name}") from exc


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_frozen_inputs(paths: dict[str, Path], expected: dict[str, str]) -> dict[str, str]:
    if set(paths) != set(expected):
        raise ValueError("frozen input labels differ")
    observed = {name: sha256_file(path) for name, path in paths.items()}
    mismatch = sorted(name for name in paths if observed[name] != expected[name])
    if mismatch:
        raise ValueError(f"frozen input SHA mismatch: {mismatch}")
    return observed


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.reset_index(drop=True)
    if data.empty or data.at[0, "time_utc"] != SOURCE_START or int(data.at[0, "source_epoch"]) % 300 != 0:
        raise ValueError("source frame does not begin at frozen M5 inception")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("reader materialized rows at or above frozen upper bound")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and strictly increasing")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("M5").all():
        raise ValueError("rows are not exclusively XAUUSD/M5")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    close = data["close"].to_numpy(dtype=float)
    if not np.isfinite(close).all() or not np.all(close > 0.0):
        raise ValueError("full inception close chain must be finite and positive")
    return data


def ema_sma_seed(values: np.ndarray, period: int = PERIOD) -> np.ndarray:
    source = np.asarray(values, dtype=float)
    out = np.full(len(source), np.nan, dtype=float)
    finite = np.flatnonzero(np.isfinite(source))
    if finite.size == 0:
        return out
    first = int(finite[0])
    if not np.isfinite(source[first:]).all():
        raise ValueError("EMA input has a nonfinite value after state begins")
    seed_index = first + period - 1
    if seed_index >= len(source):
        return out
    out[seed_index] = float(np.mean(source[first : seed_index + 1]))
    alpha = 2.0 / (period + 1.0)
    for index in range(seed_index + 1, len(source)):
        out[index] = alpha * source[index] + (1.0 - alpha) * out[index - 1]
    return out


def calculate_trix(close: np.ndarray) -> dict[str, np.ndarray]:
    ema1 = ema_sma_seed(close)
    ema2 = ema_sma_seed(ema1)
    ema3 = ema_sma_seed(ema2)
    trix = np.full(len(close), np.nan, dtype=float)
    denominator = ema3[:-1]
    valid = np.isfinite(ema3[1:]) & np.isfinite(denominator) & (denominator != 0.0)
    trix_values = np.full(len(close) - 1, np.nan, dtype=float)
    trix_values[valid] = 100.0 * (ema3[1:][valid] - denominator[valid]) / denominator[valid]
    trix[1:] = trix_values
    return {"ema1": ema1, "ema2": ema2, "ema3": ema3, "trix": trix}


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    state = calculate_trix(data["close"].to_numpy(dtype=float))
    trix = pd.Series(state["trix"], index=data.index, dtype=float)
    design = data["time_utc"].ge(DESIGN_START) & data["time_utc"].lt(DESIGN_END)
    usable = design & np.isfinite(trix) & np.isfinite(trix.shift(1))
    raw_long = usable & trix.shift(1).le(0.0) & trix.gt(0.0)
    raw_short = usable & trix.shift(1).ge(0.0) & trix.lt(0.0)
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw = raw_long | raw_short
    exact_next = data["source_epoch"].shift(-1).eq(data["source_epoch"] + 300) & ((data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(minutes=5))
    executable = raw & exact_next
    events: list[dict[str, Any]] = []
    prior = trix.shift(1)
    for index in data.index[executable]:
        source_time = data.at[index, "time_utc"]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (source_time + pd.Timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
                "prior_trix": float(prior.loc[index]),
                "trix": float(trix.loc[index]),
            }
        )
    raw_count = int(raw.sum())
    count = len(events)
    design_rows = int(design.sum())
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    event_years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, float | int]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {"events": year_count, "elapsed_weeks": weeks, "cadence_per_week": year_count / weeks, "share": year_count / count if count else 0.0}
    feature_coverage = int(usable.sum()) / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    cadence = count / elapsed_weeks
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
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
        "schema_version": "trix18_m5_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_TRIX18_ZERO_LINE_AND_CADENCE_ONLY",
        "source_window": {"from": SOURCE_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"timeframe": "M5", "period": PERIOD, "alpha": ALPHA, "ema_seed": "SMA18_FIRST_FINITE_CONSECUTIVE", "signal": "ZERO_LINE_CROSS", "first_trix_index": FIRST_TRIX_INDEX, "first_event_index": FIRST_EVENT_INDEX},
        "funnel": {"source_rows": int(len(data)), "prehistory_rows": int((data["time_utc"] < DESIGN_START).sum()), "design_rows": design_rows, "feature_usable_rows": int(usable.sum()), "raw_events": raw_count, "executable_events": count, "gap_rejected_events": raw_count - count, "direction_conflicts": int(conflicts.sum()), "long_events": longs, "short_events": shorts},
        "metrics": {"elapsed_weeks": elapsed_weeks, "feature_coverage": feature_coverage, "raw_event_exact_next_coverage": next_coverage, "event_cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_event_share": max_year_share},
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": "SCREENED_SOURCE_PASS_NATIVE_ITRIX_PARITY_CHILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_TRIX18_ZERO_CROSS",
        "prohibitions": {"post_event_ohlc_read": False, "returns_computed": False, "trades_simulated": False, "pnl_computed": False, "profit_factor_computed": False, "economics_executed": False, "validation_opened": False, "holdout_opened": False, "native_itrix_parity_authorized_by_attempt": passed, "economic_build_authorized": False, "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS or not all(math.isfinite(float(row[name])) for name in ("prior_trix", "trix")):
            raise ValueError("event ledger violates exact outcome-blind allowlist")
    forbidden = [name for name, value in report["prohibitions"].items() if name != "native_itrix_parity_authorized_by_attempt" and value is not False]
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
        "run_ids": row.get("run_ids") == [],
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "one_attempt": validation.get("source_feasibility_attempt_limit") == 1,
        "source_run": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "prehistory": validation.get("prehistory_source_access_authorized") is True,
        "prehistory_start": validation.get("prehistory_source_start") == SOURCE_START.isoformat().replace("+00:00", "Z"),
        "manifest_path": validation.get("manifest_path") == MANIFEST_RELATIVE_PATH,
        "manifest_sha": validation.get("manifest_sha256") == MANIFEST_SHA256,
        "data_path": validation.get("data_path") == DATA_RELATIVE_PATH,
        "data_sha": validation.get("data_sha256") == DATA_SHA256,
        "predicate": validation.get("data_access_predicate") == DATA_ACCESS_PREDICATE,
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
    return {"registry_sha256": hashlib.sha256(registry_bytes).hexdigest().upper(), "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(), "analyzer_sha256": sha256_file(Path(__file__).resolve())}


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    marker_path = output_dir / "attempt_started.json"
    exclusive_json(marker_path, {"schema_version": "trix_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": authority["analyzer_sha256"], "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"})
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg = root / PREREG_RELATIVE_PATH
    manifest = root / MANIFEST_RELATIVE_PATH
    data_path = root / DATA_RELATIVE_PATH
    tests = root / TEST_RELATIVE_PATH
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_TRIXMomentum/research/evidence/HYP-TRIX-XAUUSD-M5-001/TRIX001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    try:
        frozen_paths = {"preregistration": prereg, "manifest": manifest, "data": data_path, "analyzer": Path(__file__).resolve(), "tests": tests}
        expected = {"preregistration": PREREG_SHA256, "manifest": MANIFEST_SHA256, "data": DATA_SHA256, "analyzer": authority["analyzer_sha256"], "tests": TEST_SHA256}
        verify_frozen_inputs(frozen_paths, expected)
        validate_manifest(manifest, data_path)
        if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
            raise ValueError("Parquet schema missing required columns")
        raw = pd.read_parquet(data_path, columns=list(REQUIRED_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        selected = validate_frame(raw)
        events, report = analyze_frame(selected)
        assert_outcome_blind(events, report)
        replay_events, replay_report = analyze_frame(selected)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay failed")
        final_hashes = verify_frozen_inputs(frozen_paths, expected)
        report_bytes = json_bytes(report)
        ledger_bytes = jsonl_bytes(events)
        report_path = output_dir / "trix_001_source_report.json"
        ledger_path = output_dir / "trix_001_event_ledger.jsonl"
        atomic_write(report_path, report_bytes)
        atomic_write(ledger_path, ledger_bytes)
        receipt = {
            "schema_version": "trix_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": utc_now(),
            "bindings": {
                "preregistration": {"path": PREREG_RELATIVE_PATH, "sha256": final_hashes["preregistration"]},
                "manifest": {"path": MANIFEST_RELATIVE_PATH, "sha256": final_hashes["manifest"]},
                "data": {"path": DATA_RELATIVE_PATH, "sha256": final_hashes["data"]},
                "analyzer": {"path": ANALYZER_RELATIVE_PATH, "sha256": final_hashes["analyzer"]},
                "tests": {"path": TEST_RELATIVE_PATH, "sha256": final_hashes["tests"]},
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
        terminal = {"schema_version": "trix_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False}
        exclusive_json(output_dir / "attempt_terminal.json", terminal)
        return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}
    except Exception as exc:
        terminal_path = output_dir / "attempt_terminal.json"
        if not terminal_path.exists():
            exclusive_json(terminal_path, {"schema_version": "trix_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": utc_now(), "status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "attempt_started_sha256": sha256_file(start_path), "same_id_retry_authorized": False})
        raise


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
