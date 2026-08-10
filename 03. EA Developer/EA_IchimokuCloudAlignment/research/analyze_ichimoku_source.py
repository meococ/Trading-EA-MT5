#!/usr/bin/env python3
"""Outcome-blind Ichimoku 9/26/52 full-alignment source analyzer."""

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


HYPOTHESIS_ID = "HYP-ICH-XAUUSD-M5-001"
ATTEMPT_ID = "ICH001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "3811EDC4E5141A07D4074F2613A62540EA320BFB1D67A64BF69971AD600099A8"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"

DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
TENKAN_PERIOD = 9
KIJUN_PERIOD = 26
SPAN_B_PERIOD = 52
DISPLACEMENT = 26
WARMUP_ROWS = 77
MIN_ROWS = 300_000
MIN_FEATURE_COVERAGE = 0.99
MIN_RAW_EVENT_NEXT_COVERAGE = 0.97
MIN_EVENTS = 500
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
    "high",
    "low",
    "close",
)
EVENT_KEYS = {
    "hypothesis_id",
    "source_bar_time_utc",
    "decision_time_utc",
    "direction",
    "prior_tenkan",
    "prior_kijun",
    "tenkan",
    "kijun",
    "displayed_span_a",
    "displayed_span_b",
    "source_close",
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


def validate_selected_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if ((data["time_utc"] < DESIGN_START) | (data["time_utc"] >= DESIGN_END)).any():
        raise ValueError("reader materialized rows outside the frozen design window")
    data = data.reset_index(drop=True)
    if len(data) < MIN_ROWS:
        raise ValueError(f"design rows {len(data)} below {MIN_ROWS}")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and strictly increasing")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    if not data["symbol"].eq("XAUUSD").all():
        raise ValueError("rows are not exclusively XAUUSD")
    if not data["timeframe"].eq("M5").all():
        raise ValueError("rows are not exclusively M5")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    return data


def calculate_ichimoku(data: pd.DataFrame) -> dict[str, pd.Series]:
    high = data["high"].astype(float)
    low = data["low"].astype(float)
    close = data["close"].astype(float)
    finite = np.isfinite(np.column_stack((high, low, close))).all(axis=1)
    row_valid = pd.Series(
        finite & (high.to_numpy() > low.to_numpy()) & (close.to_numpy() >= low.to_numpy()) & (close.to_numpy() <= high.to_numpy()),
        index=data.index,
        dtype=bool,
    )
    tenkan = (high.rolling(TENKAN_PERIOD, min_periods=TENKAN_PERIOD).max() + low.rolling(TENKAN_PERIOD, min_periods=TENKAN_PERIOD).min()) / 2.0
    kijun = (high.rolling(KIJUN_PERIOD, min_periods=KIJUN_PERIOD).max() + low.rolling(KIJUN_PERIOD, min_periods=KIJUN_PERIOD).min()) / 2.0
    raw_span_a = (tenkan + kijun) / 2.0
    raw_span_b = (high.rolling(SPAN_B_PERIOD, min_periods=SPAN_B_PERIOD).max() + low.rolling(SPAN_B_PERIOD, min_periods=SPAN_B_PERIOD).min()) / 2.0
    displayed_span_a = raw_span_a.shift(DISPLACEMENT)
    displayed_span_b = raw_span_b.shift(DISPLACEMENT)
    dependency_valid = row_valid.astype(int).rolling(WARMUP_ROWS + 1, min_periods=WARMUP_ROWS + 1).sum().eq(WARMUP_ROWS + 1)
    feature_valid = dependency_valid & pd.Series(
        np.isfinite(np.column_stack((
            tenkan,
            kijun,
            tenkan.shift(1),
            kijun.shift(1),
            displayed_span_a,
            displayed_span_b,
            close,
        ))).all(axis=1),
        index=data.index,
        dtype=bool,
    )
    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "displayed_span_a": displayed_span_a,
        "displayed_span_b": displayed_span_b,
        "feature_valid": feature_valid,
    }


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    indicator = calculate_ichimoku(data)
    tenkan = indicator["tenkan"]
    kijun = indicator["kijun"]
    span_a = indicator["displayed_span_a"]
    span_b = indicator["displayed_span_b"]
    feature_valid = indicator["feature_valid"]

    raw_long = (
        feature_valid
        & (tenkan.shift(1) <= kijun.shift(1))
        & (tenkan > kijun)
        & (data["close"] > span_a)
        & (data["close"] > span_b)
        & (span_a > span_b)
    )
    raw_short = (
        feature_valid
        & (tenkan.shift(1) >= kijun.shift(1))
        & (tenkan < kijun)
        & (data["close"] < span_a)
        & (data["close"] < span_b)
        & (span_a < span_b)
    )
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw_mask = raw_long | raw_short
    exact_next = (data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(minutes=5)
    event_mask = raw_mask & exact_next

    events: list[dict[str, Any]] = []
    for index in data.index[event_mask]:
        bar_time = data.at[index, "time_utc"]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "source_bar_time_utc": bar_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (bar_time + pd.Timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
                "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
                "prior_tenkan": finite_float(tenkan.shift(1).loc[index]),
                "prior_kijun": finite_float(kijun.shift(1).loc[index]),
                "tenkan": finite_float(tenkan.loc[index]),
                "kijun": finite_float(kijun.loc[index]),
                "displayed_span_a": finite_float(span_a.loc[index]),
                "displayed_span_b": finite_float(span_b.loc[index]),
                "source_close": finite_float(data.at[index, "close"]),
            }
        )

    raw_count = int(raw_mask.sum())
    count = len(events)
    gap_rejected = raw_count - count
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    cadence = count / elapsed_weeks
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = sum(row["direction"] == "SHORT" for row in events)
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    feature_coverage = int(feature_valid.iloc[WARMUP_ROWS:].sum()) / max(len(data) - WARMUP_ROWS, 1)
    next_coverage = count / max(raw_count, 1)
    event_years = pd.Series([pd.Timestamp(row["source_bar_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, Any]] = {}
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
        "minimum_design_rows": len(data) >= MIN_ROWS,
        "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_RAW_EVENT_NEXT_COVERAGE,
        "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(MIN_YEAR_CADENCE <= row["cadence_per_week"] <= MAX_YEAR_CADENCE for row in yearly.values()),
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "ichimoku_full_alignment_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_ICHIMOKU_FULL_ALIGNMENT_AND_CADENCE_ONLY",
        "window": {"from": DESIGN_START.isoformat(), "to_exclusive": DESIGN_END.isoformat()},
        "parameters": {"tenkan": 9, "kijun": 26, "span_b": 52, "displacement": 26},
        "funnel": {
            "design_rows": int(len(data)),
            "feature_usable_rows": int(feature_valid.sum()),
            "raw_events": raw_count,
            "executable_events": count,
            "gap_rejected_events": gap_rejected,
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
        "verdict": "SCREENED_SOURCE_PASS_MQL5_IICHIMOKU_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_ICHIMOKU_FULL_ALIGNMENT",
        "prohibitions": {
            "post_event_ohlc_read": False,
            "returns_computed": False,
            "trades_simulated": False,
            "economics_executed": False,
            "validation_opened": False,
            "holdout_opened": False,
            "mql5_build_authorized_by_attempt": passed,
            "economic_build_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError(f"event-ledger keys differ from allowlist: {sorted(set(row))}")
    if report["prohibitions"]["post_event_ohlc_read"] is not False:
        raise ValueError("outcome-blind report contract failed")


def validate_manifest(manifest_path: Path, data_path: Path) -> None:
    if sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ValueError("manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet")]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind frozen data")
    if not data_path.as_posix().endswith("XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"):
        raise ValueError("unexpected data path")


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
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
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "one_attempt": validation.get("source_feasibility_attempt_limit") == 1,
        "unconsumed": metrics.get("source_feasibility_attempts_consumed") == 0,
        "source_run": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "analyzer": validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "no_outcomes": validation.get("outcome_prices_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_validation": validation.get("research_validation_access_authorized") is False,
        "no_holdout": validation.get("research_holdout_access_authorized") is False,
        "no_mt5": validation.get("mt5_authorized") is False,
        "no_mql5": validation.get("mql5_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {"registry_sha256": sha256_file(registry_path), "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper()}


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / "attempt_started.json"
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = {
        "schema_version": "ichimoku_attempt_started.v1",
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
    prereg = root / "03. EA Developer/EA_IchimokuCloudAlignment/research/HYP-ICH-XAUUSD-M5-001_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_IchimokuCloudAlignment/research/evidence/HYP-ICH-XAUUSD-M5-001/ICH001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    validate_manifest(manifest, data_path)
    if sha256_file(data_path) != DATA_SHA256:
        raise ValueError("data SHA mismatch")
    if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("Parquet schema missing required columns")
    raw = pd.read_parquet(
        data_path,
        columns=list(REQUIRED_COLUMNS),
        filters=[("time_utc", ">=", DESIGN_START.to_pydatetime()), ("time_utc", "<", DESIGN_END.to_pydatetime())],
        engine="pyarrow",
    )
    selected = validate_selected_frame(raw)
    events, report = analyze_frame(selected)
    assert_outcome_blind(events, report)
    replay_events, replay_report = analyze_frame(selected)
    if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
        raise ValueError("deterministic replay failed")
    report_bytes = json_bytes(report)
    ledger_bytes = jsonl_bytes(events)
    report_path = output_dir / "ich_001_source_report.json"
    ledger_path = output_dir / "ich_001_event_ledger.jsonl"
    atomic_write(report_path, report_bytes)
    atomic_write(ledger_path, ledger_bytes)
    receipt = {
        "schema_version": "ichimoku_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": sha256_file(prereg)},
            "manifest": {"path": manifest.relative_to(root).as_posix(), "sha256": sha256_file(manifest)},
            "data": {"path": data_path.relative_to(root).as_posix(), "sha256": sha256_file(data_path)},
            "analyzer": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority},
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
        "schema_version": "ichimoku_attempt_terminal.v1",
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
    root = Path(__file__).resolve().parents[3]
    result = execute(root)
    print(json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
