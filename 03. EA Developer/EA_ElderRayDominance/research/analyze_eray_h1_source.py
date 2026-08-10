#!/usr/bin/env python3
"""Outcome-blind EURUSD H1 Elder-Ray EMA13 full-bar dominance source screen."""

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


HYPOTHESIS_ID = "HYP-ERAY-EURUSD-H1-001"
ATTEMPT_ID = "ERAY001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "355A834A3DFBC64CEF7313730CC7CDD47891E651456B72CBC3E6FE90007E43B4"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3"
TEST_SHA256 = "783AF68080C533629DCCEE7ACDC1C0E2B6B919A97A6901E46074D49087C64F86"
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
EMA_LENGTH = 13
MIN_ROWS = 25_000
EVENT_KEYS = {
    "hypothesis_id", "source_bar_time_utc", "source_epoch",
    "decision_time_utc", "decision_source_epoch", "direction",
    "prior_ema", "ema", "power_name", "prior_power", "power",
}
REQUIRED_COLUMNS = (
    "symbol", "timeframe", "source_epoch", "time_utc",
    "utc_ambiguous", "high", "low", "close",
)


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
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def finite(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite output {value!r}")
    return result


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("sealed 2023+ row materialized")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be strictly increasing and unique")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be strictly increasing and unique")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous row")
    if not data["symbol"].eq("EURUSD").all() or not data["timeframe"].eq("H1").all():
        raise ValueError("symbol/timeframe mismatch")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    values = data.loc[:, ["high", "low", "close"]].to_numpy(dtype=float)
    valid = (np.isfinite(values).all(axis=1) &
             (values[:, 0] >= values[:, 1]) &
             (values[:, 2] >= values[:, 1]) &
             (values[:, 2] <= values[:, 0]))
    if not bool(valid.all()):
        raise ValueError("invalid full-prehistory price geometry")
    design_rows = int(((data["time_utc"] >= DESIGN_START) &
                       (data["time_utc"] < DESIGN_END)).sum())
    if design_rows < MIN_ROWS:
        raise ValueError(f"design rows {design_rows} below {MIN_ROWS}")
    return data.reset_index(drop=True)


def ema13(close: np.ndarray) -> np.ndarray:
    if len(close) < EMA_LENGTH:
        raise ValueError("insufficient EMA history")
    output = np.full(len(close), np.nan, dtype=float)
    output[EMA_LENGTH - 1] = float(np.mean(close[:EMA_LENGTH]))
    alpha = 2.0 / (EMA_LENGTH + 1.0)
    for index in range(EMA_LENGTH, len(close)):
        output[index] = alpha * close[index] + (1.0 - alpha) * output[index - 1]
    return output


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def decision_years(events: list[dict[str, Any]]) -> pd.Series:
    return pd.Series(
        [pd.Timestamp(row["decision_time_utc"]).year for row in events],
        dtype="int64",
    )


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    close = data["close"].to_numpy(dtype=float)
    ema = ema13(close)
    bull = high - ema
    bear = low - ema
    design = ((data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)).to_numpy()
    feature = design & np.isfinite(ema) & np.isfinite(np.roll(ema, 1))
    feature[0] = False
    long_raw = feature & (np.roll(bear, 1) <= 0.0) & (bear > 0.0)
    short_raw = feature & (np.roll(bull, 1) >= 0.0) & (bull < 0.0)
    long_raw[0] = False
    short_raw[0] = False
    conflict = long_raw & short_raw
    long_raw &= ~conflict
    short_raw &= ~conflict
    raw = long_raw | short_raw
    next_time = data["time_utc"].shift(-1)
    next_epoch = data["source_epoch"].shift(-1)
    exact_next = (((next_time - data["time_utc"]) == pd.Timedelta(hours=1)).to_numpy() &
                  (next_epoch.to_numpy(dtype=float) ==
                   data["source_epoch"].to_numpy(dtype=float) + 3600.0))
    executable = raw & exact_next
    events: list[dict[str, Any]] = []
    for index in np.flatnonzero(executable):
        is_long = bool(long_raw[index])
        source_time = data.at[index, "time_utc"]
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "source_epoch": int(data.at[index, "source_epoch"]),
            "decision_time_utc": (source_time + pd.Timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "decision_source_epoch": int(data.at[index, "source_epoch"]) + 3600,
            "direction": "LONG" if is_long else "SHORT",
            "prior_ema": finite(ema[index - 1]),
            "ema": finite(ema[index]),
            "power_name": "BearPower" if is_long else "BullPower",
            "prior_power": finite(bear[index - 1] if is_long else bull[index - 1]),
            "power": finite(bear[index] if is_long else bull[index]),
        })
    design_rows = int(design.sum())
    usable = int(feature.sum())
    raw_count = int(raw.sum())
    count = len(events)
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    years = decision_years(events)
    yearly: dict[str, Any] = {}
    for year in range(2018, 2023):
        number = int((years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {
            "events": number,
            "elapsed_weeks": weeks,
            "cadence_per_week": number / weeks,
            "share": number / count if count else 0.0,
        }
    feature_coverage = usable / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    cadence = count / elapsed_weeks
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    max_year_share = max((value["share"] for value in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": design_rows >= 25_000,
        "feature_coverage": feature_coverage >= 0.99,
        "raw_event_exact_next_coverage": next_coverage >= 0.97,
        "minimum_events": count >= 500,
        "pooled_cadence": 2.0 <= cadence <= 5.0,
        "direction_balance": long_share >= 0.30 and short_share >= 0.30,
        "year_concentration": max_year_share <= 0.30,
        "each_year_cadence": all(1.25 <= value["cadence_per_week"] <= 6.50
                                 for value in yearly.values()),
        "zero_direction_conflicts": int(conflict.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "eray_ema13_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "scope": "OUTCOME_BLIND_ELDER_RAY_DOMINANCE_AND_CADENCE_ONLY",
        "formula": {
            "ema_length": EMA_LENGTH,
            "ema_seed": "SMA13_then_alpha_2_over_14",
            "bull_power": "High-EMA13",
            "bear_power": "Low-EMA13",
            "long": "prior_bear_power_lte_0_and_current_gt_0",
            "short": "prior_bull_power_gte_0_and_current_lt_0",
        },
        "funnel": {
            "materialized_prehistory_rows": int(len(data)),
            "design_rows": design_rows,
            "feature_usable_rows": usable,
            "raw_events": raw_count,
            "executable_events": count,
            "gap_rejected_events": raw_count - count,
            "long_events": longs,
            "short_events": shorts,
            "direction_conflicts": int(conflict.sum()),
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
        "verdict": ("SCREENED_SOURCE_PASS_ERAY_MQL5_BUILD_AUTHORIZED"
                    if passed else "PARK_SOURCE_FEASIBILITY_EXACT_ERAY_EMA13_DOMINANCE"),
        "prohibitions": {
            "next_row_ohlc_read": False,
            "post_event_ohlc_read": False,
            "returns_computed": False,
            "trades_simulated": False,
            "profit_factor_computed": False,
            "economics_executed": False,
            "validation_opened": False,
            "holdout_opened": False,
            "mt5_opened": False,
            "mql5_created": False,
            "live_trading_authorized": False,
        },
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for event in events:
        if set(event) != EVENT_KEYS:
            raise ValueError(f"event keys differ from allowlist: {sorted(event)}")
    if any(report["prohibitions"].values()):
        raise ValueError("outcome-blind prohibitions changed")


def claim_attempt(output_dir: Path) -> tuple[str, Path, str]:
    if output_dir.exists():
        raise ValueError("attempt root already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    claimed_analyzer_sha = sha256_file(Path(__file__).resolve())
    marker = {
        "schema_version": "eray_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "analyzer_sha256": claimed_analyzer_sha,
        "status": "CLAIMED_BEFORE_BOUND_SOURCE_READ",
    }
    marker_path = output_dir / "attempt_started.json"
    exclusive_write(marker_path, json_bytes(marker))
    return started, marker_path, claimed_analyzer_sha


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_ElderRayDominance/research/HYP-ERAY-EURUSD-H1-001_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet"
    analyzer_path = Path(__file__).resolve()
    test_path = root / "03. EA Developer/EA_ElderRayDominance/research/tests/test_analyze_eray_h1_source.py"
    output_dir = root / "03. EA Developer/EA_ElderRayDominance/research/evidence/HYP-ERAY-EURUSD-H1-001/ERAY001-SOURCE-ATTEMPT-001"
    started, marker_path, claimed_analyzer_sha = claim_attempt(output_dir)
    try:
        bound_inputs = {
            "prereg": prereg,
            "manifest": manifest,
            "data": data_path,
            "analyzer": analyzer_path,
            "test": test_path,
        }
        initial_hashes = {name: sha256_file(path) for name, path in bound_inputs.items()}
        if initial_hashes["analyzer"] != claimed_analyzer_sha:
            raise ValueError("analyzer changed after durable claim")
        if initial_hashes["prereg"] != PREREG_SHA256:
            raise ValueError("prereg SHA mismatch")
        if initial_hashes["manifest"] != MANIFEST_SHA256 or initial_hashes["data"] != DATA_SHA256:
            raise ValueError("manifest/data SHA mismatch")
        if initial_hashes["test"] != TEST_SHA256:
            raise ValueError("test SHA mismatch")
        manifest_json = json.loads(manifest.read_text(encoding="utf-8"))
        matches = [row for row in manifest_json.get("files", [])
                   if str(row.get("path", "")).replace("\\", "/").endswith(
                       "EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet")]
        if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
            raise ValueError("manifest entry mismatch")
        raw = pd.read_parquet(
            data_path,
            columns=list(REQUIRED_COLUMNS),
            filters=[("time_utc", "<", DESIGN_END.to_pydatetime())],
            engine="pyarrow",
        )
        selected = validate_frame(raw)
        events, report = analyze_frame(selected)
        assert_outcome_blind(events, report)
        replay_events, replay_report = analyze_frame(selected)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay mismatch")
        final_hashes = {name: sha256_file(path) for name, path in bound_inputs.items()}
        if final_hashes != initial_hashes:
            raise ValueError("bound input changed during analysis")
        ledger_bytes = jsonl_bytes(events)
        report_bytes = json_bytes(report)
        ledger_path = output_dir / "eray_001_event_ledger.jsonl"
        report_path = output_dir / "eray_001_source_report.json"
        exclusive_write(ledger_path, ledger_bytes)
        exclusive_write(report_path, report_bytes)
        completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt = {
            "schema_version": "eray_source_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": started,
            "completed_at_utc": completed,
            "bindings": {
                "attempt_started": {"path": marker_path.relative_to(root).as_posix(),
                                    "sha256": sha256_file(marker_path)},
                "prereg": {"path": prereg.relative_to(root).as_posix(),
                            "sha256": initial_hashes["prereg"]},
                "manifest": {"path": manifest.relative_to(root).as_posix(),
                              "sha256": initial_hashes["manifest"]},
                "data": {"path": data_path.relative_to(root).as_posix(),
                          "sha256": initial_hashes["data"]},
                "analyzer": {"path": analyzer_path.relative_to(root).as_posix(),
                              "sha256": initial_hashes["analyzer"]},
                "test": {"path": test_path.relative_to(root).as_posix(),
                         "sha256": initial_hashes["test"]},
                "ledger": {"path": ledger_path.relative_to(root).as_posix(),
                            "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
                "report": {"path": report_path.relative_to(root).as_posix(),
                            "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
            },
            "outcome_blind_counters": {
                "next_row_ohlc_reads": 0,
                "post_event_ohlc_reads": 0,
                "returns_computed": 0,
                "trades_simulated": 0,
                "profit_factor_computed": 0,
                "validation_rows_read": 0,
                "holdout_rows_read": 0,
                "mt5_launches": 0,
                "mql5_files_created": 0,
            },
            "verdict": report["verdict"],
        }
        receipt_bytes = json_bytes(receipt)
        receipt_path = output_dir / "source_feasibility_receipt.json"
        exclusive_write(receipt_path, receipt_bytes)
        terminal = {
            "schema_version": "eray_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": completed,
            "status": "COMPLETE",
            "verdict": report["verdict"],
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
            "same_id_retry_authorized": False,
        }
        exclusive_write(output_dir / "attempt_terminal.json", json_bytes(terminal))
        return report
    except Exception as exc:
        terminal = {
            "schema_version": "eray_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "FAILED",
            "error": str(exc),
            "same_id_retry_authorized": False,
        }
        terminal_path = output_dir / "attempt_terminal.json"
        if not terminal_path.exists():
            exclusive_write(terminal_path, json_bytes(terminal))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    root = Path(__file__).resolve().parents[3]
    print(json_bytes(execute(root)).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
