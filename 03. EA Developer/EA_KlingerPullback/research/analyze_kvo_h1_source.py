#!/usr/bin/env python3
"""Outcome-blind EURUSD H1 Klinger pullback re-entry source screen."""

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


HYPOTHESIS_ID = "HYP-KVO-EURUSD-H1-001"
ATTEMPT_ID = "KVO001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "C46E69EF5DBF4F4AEDBCBBCF9600F2C4EBC4C59B3C35A248C1CCE91C8EA2AD2C"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3"
TEST_SHA256 = "1BDA15BFE184267F5D689D0BDC39C2E18A3A83952042D46A546D6AD856C60A19"
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
MIN_ROWS = 25_000
IDLE, LONG_ARMED, SHORT_ARMED = 0, 1, 2
EVENT_KEYS = {
    "hypothesis_id", "source_bar_time_utc", "source_epoch",
    "decision_time_utc", "decision_source_epoch", "direction",
    "prior_ko", "ko", "prior_signal", "signal", "ema100", "vf",
}
REQUIRED_COLUMNS = (
    "symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous",
    "high", "low", "close", "tick_volume",
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
    output = float(value)
    if not math.isfinite(output):
        raise ValueError(f"non-finite output {value!r}")
    return output


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
    for column in ("high", "low", "close", "tick_volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    prices = data.loc[:, ["high", "low", "close"]].to_numpy(dtype=float)
    valid_prices = (np.isfinite(prices).all(axis=1) &
                    (prices[:, 0] >= prices[:, 1]) &
                    (prices[:, 2] >= prices[:, 1]) &
                    (prices[:, 2] <= prices[:, 0]))
    volume = data["tick_volume"].to_numpy(dtype=float)
    valid_volume = np.isfinite(volume) & (volume >= 0.0) & (volume == np.floor(volume))
    if not bool(valid_prices.all()) or not bool(valid_volume.all()):
        raise ValueError("invalid full-prehistory price/volume contract")
    design_rows = int(((data["time_utc"] >= DESIGN_START) &
                       (data["time_utc"] < DESIGN_END)).sum())
    if design_rows < MIN_ROWS:
        raise ValueError(f"design rows {design_rows} below {MIN_ROWS}")
    return data.reset_index(drop=True)


def seeded_ema(values: np.ndarray, length: int, first: int) -> np.ndarray:
    output = np.full(len(values), np.nan, dtype=float)
    seed = first + length - 1
    if len(values) <= seed or not np.isfinite(values[first:seed + 1]).all():
        raise ValueError(f"insufficient valid EMA{length} seed")
    output[seed] = float(np.mean(values[first:seed + 1]))
    alpha = 2.0 / (length + 1.0)
    for index in range(seed + 1, len(values)):
        if not math.isfinite(float(values[index])):
            raise ValueError(f"invalid EMA{length} input")
        output[index] = alpha * values[index] + (1.0 - alpha) * output[index - 1]
    return output


def calculate_indicators(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    dm = high - low
    composite = high + low + close
    trend = np.full(len(frame), -1.0, dtype=float)
    trend[1:] = np.where(composite[1:] > composite[:-1], 1.0, -1.0)
    cm = np.full(len(frame), np.nan, dtype=float)
    vf = np.full(len(frame), np.nan, dtype=float)
    if len(frame) < 100:
        raise ValueError("insufficient Klinger prehistory")
    cm[1] = dm[0] + dm[1]
    if cm[1] == 0.0:
        raise ValueError("CM is zero at index 1")
    vf[1] = volume[1] * 2.0 * (dm[1] / cm[1] - 1.0) * trend[1] * 100.0
    for index in range(2, len(frame)):
        cm[index] = (cm[index - 1] + dm[index]
                     if trend[index] == trend[index - 1]
                     else dm[index - 1] + dm[index])
        if not math.isfinite(float(cm[index])) or cm[index] == 0.0:
            raise ValueError(f"CM invalid at index {index}")
        vf[index] = (volume[index] * 2.0 *
                     (dm[index] / cm[index] - 1.0) * trend[index] * 100.0)
    ema34 = seeded_ema(vf, 34, 1)
    ema55 = seeded_ema(vf, 55, 1)
    ko = ema34 - ema55
    signal = seeded_ema(ko, 13, 55)
    ema100 = seeded_ema(close, 100, 0)
    return {"trend": trend, "dm": dm, "cm": cm, "vf": vf,
            "ema34": ema34, "ema55": ema55, "ko": ko,
            "signal": signal, "ema100": ema100}


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    ind = calculate_indicators(data)
    close = data["close"].to_numpy(dtype=float)
    ko, signal, ema100, vf = ind["ko"], ind["signal"], ind["ema100"], ind["vf"]
    design = ((data["time_utc"] >= DESIGN_START) & (data["time_utc"] < DESIGN_END)).to_numpy()
    usable = (design & np.isfinite(ko) & np.isfinite(signal) & np.isfinite(ema100) &
              np.isfinite(np.roll(ko, 1)) & np.isfinite(np.roll(signal, 1)))
    usable[0] = False
    state = IDLE
    raw_rows: list[tuple[int, str]] = []
    conflicts = 0
    for index in range(1, len(data)):
        feature = (math.isfinite(float(ko[index])) and
                   math.isfinite(float(signal[index])) and
                   math.isfinite(float(ema100[index])) and
                   math.isfinite(float(ko[index - 1])) and
                   math.isfinite(float(signal[index - 1])))
        if not feature:
            state = IDLE
            continue
        direction: str | None = None
        if state == LONG_ARMED:
            trigger = (ko[index - 1] <= signal[index - 1] and
                       ko[index] > signal[index] and ko[index] <= 0.0 and
                       close[index] > ema100[index])
            if trigger:
                direction = "LONG"
            state = (LONG_ARMED if direction is None and ko[index] <= 0.0 and
                     close[index] > ema100[index] else IDLE)
        elif state == SHORT_ARMED:
            trigger = (ko[index - 1] >= signal[index - 1] and
                       ko[index] < signal[index] and ko[index] >= 0.0 and
                       close[index] < ema100[index])
            if trigger:
                direction = "SHORT"
            state = (SHORT_ARMED if direction is None and ko[index] >= 0.0 and
                     close[index] < ema100[index] else IDLE)
        else:
            if ko[index] < 0.0 and close[index] > ema100[index]:
                state = LONG_ARMED
            elif ko[index] > 0.0 and close[index] < ema100[index]:
                state = SHORT_ARMED
        if direction is not None and design[index]:
            raw_rows.append((index, direction))

    next_time = data["time_utc"].shift(-1)
    next_epoch = data["source_epoch"].shift(-1)
    events: list[dict[str, Any]] = []
    gap_rejected = 0
    for index, direction in raw_rows:
        exact = (index + 1 < len(data) and
                 next_time.iloc[index] - data.at[index, "time_utc"] == pd.Timedelta(hours=1) and
                 int(next_epoch.iloc[index]) == int(data.at[index, "source_epoch"]) + 3600 and
                 next_time.iloc[index] < DESIGN_END)
        if not exact:
            gap_rejected += 1
            continue
        source_time = data.at[index, "time_utc"]
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "source_epoch": int(data.at[index, "source_epoch"]),
            "decision_time_utc": next_time.iloc[index].isoformat().replace("+00:00", "Z"),
            "decision_source_epoch": int(next_epoch.iloc[index]),
            "direction": direction,
            "prior_ko": finite(ko[index - 1]), "ko": finite(ko[index]),
            "prior_signal": finite(signal[index - 1]), "signal": finite(signal[index]),
            "ema100": finite(ema100[index]), "vf": finite(vf[index]),
        })

    design_rows = int(design.sum())
    feature_rows = int(usable.sum())
    raw_count = len(raw_rows)
    count = len(events)
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, Any] = {}
    for year in range(2018, 2023):
        number = int((years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {"events": number, "elapsed_weeks": weeks,
                             "cadence_per_week": number / weeks,
                             "share": number / count if count else 0.0}
    feature_coverage = feature_rows / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    cadence = count / elapsed_weeks
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    max_year_share = max((value["share"] for value in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": design_rows >= MIN_ROWS,
        "feature_coverage": feature_coverage >= 0.99,
        "raw_event_exact_next_coverage": next_coverage >= 0.97,
        "minimum_events": count >= 500,
        "pooled_cadence": 2.0 <= cadence <= 5.0,
        "direction_balance": long_share >= 0.30 and short_share >= 0.30,
        "year_concentration": max_year_share <= 0.30,
        "each_year_cadence": all(1.25 <= value["cadence_per_week"] <= 6.50
                                 for value in yearly.values()),
        "zero_direction_conflicts": conflicts == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "kvo_pullback_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
        "scope": "OUTCOME_BLIND_KLINGER_PULLBACK_SOURCE_AND_CADENCE_ONLY",
        "volume_provenance": "UNSIGNED_BROKER_TICK_ACTIVITY_PROXY_NOT_MONEY_FLOW",
        "formula": {"vf_absolute_value": False, "ema_vf": [34, 55],
                    "signal_ema": 13, "trend_ema_close": 100,
                    "states": ["IDLE", "LONG_ARMED", "SHORT_ARMED"]},
        "funnel": {"materialized_prehistory_rows": int(len(data)),
                   "design_rows": design_rows, "feature_usable_rows": feature_rows,
                   "raw_events": raw_count, "executable_events": count,
                   "gap_rejected_events": gap_rejected, "long_events": longs,
                   "short_events": shorts, "direction_conflicts": conflicts},
        "metrics": {"elapsed_weeks": elapsed_weeks,
                    "feature_coverage": feature_coverage,
                    "raw_event_exact_next_coverage": next_coverage,
                    "event_cadence_per_week": cadence,
                    "long_share": long_share, "short_share": short_share,
                    "max_year_event_share": max_year_share},
        "yearly": yearly, "gates": gates, "all_gates_pass": passed,
        "verdict": ("SCREENED_SOURCE_PASS_KVO_MQL5_BUILD_AUTHORIZED" if passed
                    else "PARK_SOURCE_FEASIBILITY_EXACT_KVO_PULLBACK"),
        "prohibitions": {"next_row_ohlc_read": False, "post_event_ohlc_read": False,
                         "returns_computed": False, "trades_simulated": False,
                         "profit_factor_computed": False, "economics_executed": False,
                         "validation_opened": False, "holdout_opened": False,
                         "mt5_opened": False, "mql5_created": False,
                         "live_trading_authorized": False},
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    if any(set(event) != EVENT_KEYS for event in events):
        raise ValueError("event ledger violates allowlist")
    if any(report["prohibitions"].values()):
        raise ValueError("outcome-blind prohibitions changed")


def claim_attempt(output_dir: Path) -> tuple[str, Path, str]:
    if output_dir.exists():
        raise ValueError("attempt root already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    analyzer_sha = sha256_file(Path(__file__).resolve())
    marker = {"schema_version": "kvo_source_attempt_started.v1",
              "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
              "started_at_utc": started, "analyzer_sha256": analyzer_sha,
              "status": "CLAIMED_BEFORE_BOUND_SOURCE_READ"}
    path = output_dir / "attempt_started.json"
    exclusive_write(path, json_bytes(marker))
    return started, path, analyzer_sha


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_KlingerPullback/research/HYP-KVO-EURUSD-H1-001_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet"
    analyzer_path = Path(__file__).resolve()
    test_path = root / "03. EA Developer/EA_KlingerPullback/research/tests/test_analyze_kvo_h1_source.py"
    output_dir = root / "03. EA Developer/EA_KlingerPullback/research/evidence/HYP-KVO-EURUSD-H1-001/KVO001-SOURCE-ATTEMPT-001"
    started, marker_path, claimed_analyzer_sha = claim_attempt(output_dir)
    try:
        bound = {"prereg": prereg, "manifest": manifest, "data": data_path,
                 "analyzer": analyzer_path, "test": test_path}
        initial = {name: sha256_file(path) for name, path in bound.items()}
        if initial["analyzer"] != claimed_analyzer_sha:
            raise ValueError("analyzer changed after durable claim")
        if initial["prereg"] != PREREG_SHA256 or initial["test"] != TEST_SHA256:
            raise ValueError("prereg/test SHA mismatch")
        if initial["manifest"] != MANIFEST_SHA256 or initial["data"] != DATA_SHA256:
            raise ValueError("manifest/data SHA mismatch")
        manifest_json = json.loads(manifest.read_text(encoding="utf-8"))
        matches = [row for row in manifest_json.get("files", [])
                   if str(row.get("path", "")).replace("\\", "/").endswith(
                       "EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet")]
        if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
            raise ValueError("manifest entry mismatch")
        raw = pd.read_parquet(data_path, columns=list(REQUIRED_COLUMNS),
                              filters=[("time_utc", "<", DESIGN_END.to_pydatetime())],
                              engine="pyarrow")
        selected = validate_frame(raw)
        events, report = analyze_frame(selected)
        assert_outcome_blind(events, report)
        replay_events, replay_report = analyze_frame(selected)
        if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
            raise ValueError("deterministic replay mismatch")
        final = {name: sha256_file(path) for name, path in bound.items()}
        if final != initial:
            raise ValueError("bound input changed during analysis")
        ledger_bytes, report_bytes = jsonl_bytes(events), json_bytes(report)
        ledger_path = output_dir / "kvo_001_event_ledger.jsonl"
        report_path = output_dir / "kvo_001_source_report.json"
        exclusive_write(ledger_path, ledger_bytes)
        exclusive_write(report_path, report_bytes)
        completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        bindings = {name: {"path": path.relative_to(root).as_posix(), "sha256": initial[name]}
                    for name, path in bound.items()}
        bindings.update({
            "attempt_started": {"path": marker_path.relative_to(root).as_posix(),
                                "sha256": sha256_file(marker_path)},
            "ledger": {"path": ledger_path.relative_to(root).as_posix(),
                       "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()},
            "report": {"path": report_path.relative_to(root).as_posix(),
                       "sha256": hashlib.sha256(report_bytes).hexdigest().upper()},
        })
        receipt = {"schema_version": "kvo_source_receipt.v1",
                   "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
                   "started_at_utc": started, "completed_at_utc": completed,
                   "bindings": bindings,
                   "outcome_blind_counters": {"next_row_ohlc_reads": 0,
                                               "post_event_ohlc_reads": 0,
                                               "returns_computed": 0,
                                               "trades_simulated": 0,
                                               "profit_factor_computed": 0,
                                               "validation_rows_read": 0,
                                               "holdout_rows_read": 0,
                                               "mt5_launches": 0,
                                               "mql5_files_created": 0},
                   "verdict": report["verdict"]}
        receipt_bytes = json_bytes(receipt)
        exclusive_write(output_dir / "source_feasibility_receipt.json", receipt_bytes)
        terminal = {"schema_version": "kvo_source_attempt_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
                    "completed_at_utc": completed, "status": "COMPLETE",
                    "verdict": report["verdict"],
                    "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
                    "same_id_retry_authorized": False}
        exclusive_write(output_dir / "attempt_terminal.json", json_bytes(terminal))
        return report
    except Exception as exc:
        terminal = {"schema_version": "kvo_source_attempt_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
                    "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "status": "FAILED", "error": str(exc),
                    "same_id_retry_authorized": False}
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
