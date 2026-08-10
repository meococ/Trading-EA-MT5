#!/usr/bin/env python3
"""Outcome-blind EURUSD H1 Coppock zero-cross source screen."""

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

HYPOTHESIS_ID = "HYP-COP-EURUSD-H1-001"
ATTEMPT_ID = "COP001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "919B182AF5E9CB1A1E576E1A3E607E944EB1AA64E313B4663F40121FE2F920A9"
TEST_SHA256 = "9551B71E69BC7823D12F9924A0DCEB8B14A7E28BFEEFCE7AA76BF1FCE4EBD298"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3"
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
MIN_ROWS = 25_000
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc",
                    "utc_ambiguous", "high", "low", "close")
EVENT_KEYS = {"hypothesis_id", "source_bar_time_utc", "source_epoch",
              "decision_time_utc", "decision_source_epoch", "direction",
              "prior_curve", "curve", "roc11", "roc14"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def exclusive_write(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload); handle.flush(); os.fsync(handle.fileno())


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("sealed 2023+ row materialized")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc order/uniqueness failure")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch order/uniqueness failure")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous row")
    if not data["symbol"].eq("EURUSD").all() or not data["timeframe"].eq("H1").all():
        raise ValueError("symbol/timeframe mismatch")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    values = data.loc[:, ["high", "low", "close"]].to_numpy(dtype=float)
    valid = (np.isfinite(values).all(axis=1) & (values > 0.0).all(axis=1) &
             (values[:, 0] >= values[:, 1]) & (values[:, 2] >= values[:, 1]) &
             (values[:, 2] <= values[:, 0]))
    if not bool(valid.all()):
        raise ValueError("invalid full-history price geometry")
    design_rows = int(((data["time_utc"] >= DESIGN_START) &
                       (data["time_utc"] < DESIGN_END)).sum())
    if design_rows < MIN_ROWS:
        raise ValueError("insufficient design rows")
    return data.reset_index(drop=True)


def coppock(close: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(close) < 25 or not np.isfinite(close).all() or (close <= 0.0).any():
        raise ValueError("invalid Coppock input")
    roc11 = np.full(len(close), np.nan, dtype=float)
    roc14 = np.full(len(close), np.nan, dtype=float)
    roc11[11:] = 100.0 * (close[11:] / close[:-11] - 1.0)
    roc14[14:] = 100.0 * (close[14:] / close[:-14] - 1.0)
    raw = roc11 + roc14
    curve = np.full(len(close), np.nan, dtype=float)
    weights = np.arange(1.0, 11.0)
    for index in range(23, len(close)):
        window = raw[index - 9:index + 1]
        if not np.isfinite(window).all():
            raise ValueError("invalid Coppock WMA window")
        curve[index] = float(np.dot(window, weights) / 55.0)
    return roc11, roc14, curve


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    roc11, roc14, curve = coppock(data["close"].to_numpy(dtype=float))
    design = ((data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)).to_numpy()
    feature = design & np.isfinite(curve) & np.isfinite(np.roll(curve, 1))
    feature[0] = False
    long_raw = feature & (np.roll(curve, 1) <= 0.0) & (curve > 0.0)
    short_raw = feature & (np.roll(curve, 1) >= 0.0) & (curve < 0.0)
    long_raw[0] = False; short_raw[0] = False
    conflict = long_raw & short_raw
    long_raw &= ~conflict; short_raw &= ~conflict
    raw = long_raw | short_raw
    next_time = data["time_utc"].shift(-1)
    next_epoch = data["source_epoch"].shift(-1)
    exact = (((next_time - data["time_utc"]) == pd.Timedelta(hours=1)).to_numpy() &
             (next_epoch.to_numpy(dtype=float) ==
              data["source_epoch"].to_numpy(dtype=float) + 3600.0) &
             (next_time < DESIGN_END).fillna(False).to_numpy())
    executable = raw & exact
    events: list[dict[str, Any]] = []
    for index in np.flatnonzero(executable):
        source_time = data.at[index, "time_utc"]
        events.append({"hypothesis_id": HYPOTHESIS_ID,
                       "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
                       "source_epoch": int(data.at[index, "source_epoch"]),
                       "decision_time_utc": next_time.iloc[index].isoformat().replace("+00:00", "Z"),
                       "decision_source_epoch": int(next_epoch.iloc[index]),
                       "direction": "LONG" if long_raw[index] else "SHORT",
                       "prior_curve": float(curve[index - 1]), "curve": float(curve[index]),
                       "roc11": float(roc11[index]), "roc14": float(roc14[index])})
    design_rows, usable, raw_count, count = int(design.sum()), int(feature.sum()), int(raw.sum()), len(events)
    longs = sum(row["direction"] == "LONG" for row in events); shorts = count - longs
    elapsed = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, Any] = {}
    for year in range(2018, 2023):
        number = int((years == year).sum()) if count else 0; weeks = year_weeks(year)
        yearly[str(year)] = {"events": number, "elapsed_weeks": weeks,
                             "cadence_per_week": number / weeks,
                             "share": number / count if count else 0.0}
    feature_coverage = usable / max(design_rows, 1); next_coverage = count / max(raw_count, 1)
    cadence = count / elapsed; long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    max_year = max((item["share"] for item in yearly.values()), default=0.0)
    gates = {"minimum_design_rows": design_rows >= MIN_ROWS,
             "feature_coverage": feature_coverage >= 0.99,
             "raw_event_exact_next_coverage": next_coverage >= 0.97,
             "minimum_events": count >= 500,
             "pooled_cadence": 2.0 <= cadence <= 5.0,
             "direction_balance": long_share >= 0.30 and short_share >= 0.30,
             "year_concentration": max_year <= 0.30,
             "each_year_cadence": all(1.25 <= x["cadence_per_week"] <= 6.50 for x in yearly.values()),
             "zero_direction_conflicts": int(conflict.sum()) == 0}
    passed = all(gates.values())
    report = {"schema_version": "cop_zero_cross_source_report.v1",
              "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
              "scope": "OUTCOME_BLIND_COPPOCK_ZERO_CROSS_SOURCE_AND_CADENCE_ONLY",
              "formula": {"roc_periods": [11, 14], "wma_period": 10,
                          "wma_weights": "oldest_1_to_current_10"},
              "funnel": {"materialized_history_rows": int(len(data)), "design_rows": design_rows,
                         "feature_usable_rows": usable, "raw_events": raw_count,
                         "executable_events": count, "gap_rejected_events": raw_count - count,
                         "long_events": longs, "short_events": shorts,
                         "direction_conflicts": int(conflict.sum())},
              "metrics": {"elapsed_weeks": elapsed, "feature_coverage": feature_coverage,
                          "raw_event_exact_next_coverage": next_coverage,
                          "event_cadence_per_week": cadence, "long_share": long_share,
                          "short_share": short_share, "max_year_event_share": max_year},
              "yearly": yearly, "gates": gates, "all_gates_pass": passed,
              "verdict": ("SCREENED_SOURCE_PASS_COP_MQL5_BUILD_AUTHORIZED" if passed
                          else "PARK_SOURCE_FEASIBILITY_EXACT_COP_ZERO_CROSS"),
              "prohibitions": {"next_row_ohlc_read": False, "post_event_ohlc_read": False,
                               "returns_computed": False, "trades_simulated": False,
                               "profit_factor_computed": False, "economics_executed": False,
                               "validation_opened": False, "holdout_opened": False,
                               "mt5_opened": False, "mql5_created": False,
                               "live_trading_authorized": False}}
    return events, report


def claim_attempt(output_dir: Path) -> tuple[str, Path, str]:
    if output_dir.exists(): raise ValueError("attempt root already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    analyzer_sha = sha256_file(Path(__file__).resolve())
    marker = {"schema_version": "cop_source_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID,
              "attempt_id": ATTEMPT_ID, "started_at_utc": started,
              "analyzer_sha256": analyzer_sha, "status": "CLAIMED_BEFORE_BOUND_SOURCE_READ"}
    marker_path = output_dir / "attempt_started.json"; exclusive_write(marker_path, json_bytes(marker))
    return started, marker_path, analyzer_sha


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_CoppockZeroCross/research/HYP-COP-EURUSD-H1-001_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet"
    analyzer_path = Path(__file__).resolve()
    test_path = root / "03. EA Developer/EA_CoppockZeroCross/research/tests/test_analyze_cop_h1_source.py"
    output_dir = root / "03. EA Developer/EA_CoppockZeroCross/research/evidence/HYP-COP-EURUSD-H1-001/COP001-SOURCE-ATTEMPT-001"
    started, marker_path, claimed = claim_attempt(output_dir)
    try:
        bound = {"prereg": prereg, "manifest": manifest, "data": data_path,
                 "analyzer": analyzer_path, "test": test_path}
        initial = {name: sha256_file(path) for name, path in bound.items()}
        if initial["analyzer"] != claimed: raise ValueError("analyzer changed after claim")
        if initial["prereg"] != PREREG_SHA256 or initial["test"] != TEST_SHA256:
            raise ValueError("prereg/test SHA mismatch")
        if initial["manifest"] != MANIFEST_SHA256 or initial["data"] != DATA_SHA256:
            raise ValueError("manifest/data SHA mismatch")
        manifest_json = json.loads(manifest.read_text(encoding="utf-8"))
        matches = [row for row in manifest_json.get("files", []) if
                   str(row.get("path", "")).replace("\\", "/").endswith("EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet")]
        if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
            raise ValueError("manifest entry mismatch")
        raw = pd.read_parquet(data_path, columns=list(REQUIRED_COLUMNS),
                              filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        selected = validate_frame(raw); events, report = analyze_frame(selected)
        if any(set(event) != EVENT_KEYS for event in events): raise ValueError("ledger allowlist failure")
        if any(report["prohibitions"].values()): raise ValueError("outcome boundary failure")
        replay_events, replay_report = analyze_frame(selected)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay mismatch")
        final = {name: sha256_file(path) for name, path in bound.items()}
        if final != initial: raise ValueError("bound input changed during analysis")
        ledger_bytes, report_bytes = jsonl_bytes(events), json_bytes(report)
        ledger_path = output_dir / "cop_001_event_ledger.jsonl"; report_path = output_dir / "cop_001_source_report.json"
        exclusive_write(ledger_path, ledger_bytes); exclusive_write(report_path, report_bytes)
        completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bindings = {name: {"path": path.relative_to(root).as_posix(), "sha256": initial[name]}
                    for name, path in bound.items()}
        bindings.update({"attempt_started": {"path": marker_path.relative_to(root).as_posix(), "sha256": sha256_file(marker_path)},
                         "ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
                         "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()}})
        receipt = {"schema_version": "cop_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID,
                   "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": completed,
                   "bindings": bindings,
                   "outcome_blind_counters": {"next_row_ohlc_reads": 0, "post_event_ohlc_reads": 0,
                                               "returns_computed": 0, "trades_simulated": 0,
                                               "profit_factor_computed": 0, "validation_rows_read": 0,
                                               "holdout_rows_read": 0, "mt5_launches": 0,
                                               "mql5_files_created": 0},
                   "verdict": report["verdict"]}
        receipt_bytes = json_bytes(receipt); receipt_path = output_dir / "source_feasibility_receipt.json"
        exclusive_write(receipt_path, receipt_bytes)
        terminal = {"schema_version": "cop_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID, "completed_at_utc": completed, "status": "COMPLETE",
                    "verdict": report["verdict"], "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
                    "same_id_retry_authorized": False}
        exclusive_write(output_dir / "attempt_terminal.json", json_bytes(terminal)); return report
    except Exception as exc:
        terminal_path = output_dir / "attempt_terminal.json"
        if not terminal_path.exists():
            exclusive_write(terminal_path, json_bytes({"schema_version": "cop_source_attempt_terminal.v1",
                                                       "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
                                                       "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                                                       "status": "FAILED", "error": str(exc),
                                                       "same_id_retry_authorized": False}))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute: parser.error("--execute is required")
    root = Path(__file__).resolve().parents[3]
    print(json_bytes(execute(root)).decode("utf-8"), end=""); return 0


if __name__ == "__main__": raise SystemExit(main())
