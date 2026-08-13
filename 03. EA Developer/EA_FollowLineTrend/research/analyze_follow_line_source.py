#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-FLI-EURUSD-M15-001"
ATTEMPT_ID = "FLI001-SOURCE-001"
SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
PREREG = Path(__file__).resolve().with_name("HYP-FLI-EURUSD-M15-001_FROZEN_SOURCE_PREREG.md")
TEST = Path(__file__).resolve().parent / "tests" / "test_analyze_follow_line_source.py"
OUTPUT = Path(__file__).resolve().parent / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
READ_FROM = pd.Timestamp("2015-01-01 00:00:00")
DESIGN_FROM = pd.Timestamp("2016-01-04 00:00:00")
DESIGN_TO = pd.Timestamp("2023-01-01 00:00:00")
BB_PERIOD = 21
BB_DEVIATION = 1.0
ATR_PERIOD = 5


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_exclusive(path: Path, raw: bytes) -> None:
    with path.open("xb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())


def write_json(path: Path, obj: dict) -> None:
    write_exclusive(path, (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode())


def aggregate_m15(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["time_server", "time_utc", "open", "high", "low", "close"]
    if list(frame.columns) != required:
        raise ValueError(f"unexpected columns: {list(frame.columns)}")
    if frame[["time_server", "time_utc"]].isna().any().any():
        raise ValueError("null timestamp")
    if not frame["time_server"].is_monotonic_increasing or frame["time_server"].duplicated().any():
        raise ValueError("M1 timestamps not strictly increasing/unique")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite M1 OHLC")
    valid_geometry = (
        (values[:, 1] >= values[:, 2])
        & (values[:, 1] >= np.maximum(values[:, 0], values[:, 3]))
        & (values[:, 2] <= np.minimum(values[:, 0], values[:, 3]))
    )
    if not valid_geometry.all():
        raise ValueError("invalid M1 geometry")
    work = frame.copy()
    work["bucket"] = work["time_server"].dt.floor("15min")
    bars = (
        work.groupby("bucket", sort=True, observed=True)
        .agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
             first_utc=("time_utc", "first"), m1_rows=("time_server", "size"))
        .reset_index()
        .rename(columns={"bucket": "time_server"})
    )
    if not bars["time_server"].is_monotonic_increasing or bars["time_server"].duplicated().any():
        raise ValueError("M15 timestamps not strictly increasing/unique")
    return bars


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    tr = np.full(len(close), np.nan, dtype=float)
    if len(close) == 0:
        return tr
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    out = np.full(len(close), np.nan, dtype=float)
    if len(close) < period:
        return out
    out[period - 1] = float(np.mean(tr[:period]))
    for i in range(period, len(close)):
        out[i] = ((period - 1) * out[i - 1] + tr[i]) / period
    return out


def follow_line_state(bars: pd.DataFrame) -> pd.DataFrame:
    close = bars["close"].to_numpy(dtype=float)
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    basis = pd.Series(close).rolling(BB_PERIOD, min_periods=BB_PERIOD).mean().to_numpy()
    sigma = pd.Series(close).rolling(BB_PERIOD, min_periods=BB_PERIOD).std(ddof=0).to_numpy()
    atr = wilder_atr(high, low, close, ATR_PERIOD)
    upper = basis + BB_DEVIATION * sigma
    lower = basis - BB_DEVIATION * sigma
    line = np.full(len(close), np.nan, dtype=float)
    trend = np.zeros(len(close), dtype=np.int8)
    signal = np.zeros(len(close), dtype=np.int8)
    usable = np.isfinite(upper) & np.isfinite(lower) & np.isfinite(atr)
    for i in range(1, len(close)):
        line[i] = line[i - 1]
        trend[i] = trend[i - 1]
        if not usable[i]:
            continue
        bb_signal = 1 if close[i] > upper[i] else (-1 if close[i] < lower[i] else 0)
        if not math.isfinite(line[i - 1]):
            if bb_signal > 0:
                line[i] = low[i] - atr[i]
                trend[i] = 1
            elif bb_signal < 0:
                line[i] = high[i] + atr[i]
                trend[i] = -1
            continue
        if bb_signal > 0:
            line[i] = max(low[i] - atr[i], line[i - 1])
        elif bb_signal < 0:
            line[i] = min(high[i] + atr[i], line[i - 1])
        if line[i] > line[i - 1]:
            trend[i] = 1
        elif line[i] < line[i - 1]:
            trend[i] = -1
        if trend[i - 1] == -1 and trend[i] == 1:
            signal[i] = 1
        elif trend[i - 1] == 1 and trend[i] == -1:
            signal[i] = -1
    return pd.DataFrame({"basis": basis, "sigma": sigma, "atr5": atr, "upper": upper, "lower": lower,
                         "follow_line": line, "trend": trend, "signal": signal, "usable": usable})


def analyze(bars: pd.DataFrame) -> tuple[dict, bytes]:
    state = follow_line_state(bars)
    times = bars["time_server"].tolist()
    raw = 0
    gap_rejects = 0
    boundary_rejects = 0
    events: list[dict] = []
    for i in range(len(bars)):
        direction_code = int(state.iloc[i]["signal"])
        if direction_code == 0 or not (DESIGN_FROM <= times[i] < DESIGN_TO):
            continue
        raw += 1
        exact_next = i + 1 < len(bars) and (times[i + 1] - times[i]).total_seconds() == 900
        if not exact_next:
            gap_rejects += 1
            continue
        if times[i + 1] >= DESIGN_TO:
            boundary_rejects += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_time_server": times[i].isoformat(),
            "decision_time_server": times[i].isoformat(),
            "availability_time_server": times[i + 1].isoformat(),
            "direction": "LONG" if direction_code > 0 else "SHORT",
            "follow_line_prior": round(float(state.iloc[i - 1]["follow_line"]), 12),
            "follow_line_current": round(float(state.iloc[i]["follow_line"]), 12),
            "trend_prior": int(state.iloc[i - 1]["trend"]),
            "trend_current": int(state.iloc[i]["trend"]),
            "atr5": round(float(state.iloc[i]["atr5"]), 12),
        })
    ledger = b"".join((json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n").encode() for e in events)
    design_mask = (bars["time_server"] >= DESIGN_FROM).to_numpy() & (bars["time_server"] < DESIGN_TO).to_numpy()
    design_rows = int(design_mask.sum())
    usable_rows = int((design_mask & state["usable"].to_numpy()).sum())
    weeks = (DESIGN_TO - DESIGN_FROM).total_seconds() / 604800.0
    n = len(events)
    directions = {d: sum(e["direction"] == d for e in events) for d in ("LONG", "SHORT")}
    years = range(2016, 2023)
    by_year = {str(y): sum(pd.Timestamp(e["decision_time_server"]).year == y for e in events) for y in years}
    year_weeks = {str(y): (min(DESIGN_TO, pd.Timestamp(f"{y+1}-01-01")) - max(DESIGN_FROM, pd.Timestamp(f"{y}-01-01"))).total_seconds() / 604800.0 for y in years}
    exact_next_coverage = n / raw if raw else 0.0
    gates = {
        "design_rows_gte_150000": design_rows >= 150000,
        "usable_coverage_gte_0_99": design_rows > 0 and usable_rows / design_rows >= 0.99,
        "exact_next_coverage_gte_0_97": exact_next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "pooled_cadence_2_to_5": 2.0 <= n / weeks <= 5.0,
        "each_direction_gte_0_30": n > 0 and all(v / n >= 0.30 for v in directions.values()),
        "max_year_share_lte_0_25": n > 0 and max(by_year.values(), default=0) / n <= 0.25,
        "each_year_cadence_1_25_to_6_5": all(1.25 <= by_year[y] / year_weeks[y] <= 6.5 for y in by_year),
        "zero_conflicts": True,
    }
    report = {
        "schema_version": "follow_line_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "formula": {"bb_period": BB_PERIOD, "bb_deviation": BB_DEVIATION, "atr_period": ATR_PERIOD,
                    "std_ddof": 0, "initial_line": "UNINITIALIZED_FIRST_BREAKOUT_NO_EVENT", "initial_trend": 0},
        "rows": {"m15_total": len(bars), "design": design_rows, "usable_design": usable_rows},
        "events": {"raw": raw, "executable": n, "gap_rejects": gap_rejects, "boundary_rejects": boundary_rejects},
        "weeks": weeks,
        "cadence_per_week": n / weeks,
        "exact_next_coverage": exact_next_coverage,
        "year_axis": "decision_time_server",
        "by_direction": directions,
        "direction_share": {d: directions[d] / n if n else 0.0 for d in directions},
        "by_year": by_year,
        "year_cadence": {y: by_year[y] / year_weeks[y] for y in by_year},
        "max_year_share": max(by_year.values(), default=0) / n if n else 0.0,
        "gates": gates,
        "verdict": "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY",
        "economic_fields_read": False,
    }
    return report, ledger


def execute() -> None:
    source, prereg, test, analyzer, output = SOURCE.resolve(), PREREG.resolve(), TEST.resolve(), Path(__file__).resolve(), OUTPUT.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "attempt_started.json", {"schema_version": "follow_line_source_attempt_started.v1",
               "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
               "started_at_utc": datetime.now(timezone.utc).isoformat(), "source_path": str(source)})
    stage = "ATTEMPT_CLAIMED"
    initial: dict[str, str] = {}
    observed: dict[str, object] = {}
    try:
        stage = "HASHING_BOUND_INPUTS"
        initial = {"source": sha256_file(source), "prereg": sha256_file(prereg),
                   "analyzer": sha256_file(analyzer), "test": sha256_file(test)}
        if initial["source"] != SOURCE_SHA256:
            raise ValueError(f"source SHA mismatch: {initial['source']}")
        stage = "READING_M1_SOURCE"
        table = pq.read_table(source, columns=["time_server", "time_utc", "open", "high", "low", "close"],
                              filters=[("time_server", ">=", READ_FROM.to_pydatetime()),
                                       ("time_server", "<", DESIGN_TO.to_pydatetime())])
        frame = table.to_pandas()
        observed["m1_rows"] = len(frame)
        stage = "AGGREGATING_M15"
        bars = aggregate_m15(frame)
        observed["m15_rows"] = len(bars)
        stage = "ANALYZING_SOURCE_GATES"
        report_a, ledger_a = analyze(bars)
        observed["design_rows"] = report_a["rows"]["design"]
        observed["raw_events"] = report_a["events"]["raw"]
        observed["executable_events"] = report_a["events"]["executable"]
        observed["gates"] = report_a["gates"]
        report_b, ledger_b = analyze(bars.copy(deep=True))
        report_raw = (json.dumps(report_a, indent=2, sort_keys=True) + "\n").encode()
        if report_raw != (json.dumps(report_b, indent=2, sort_keys=True) + "\n").encode() or ledger_a != ledger_b:
            raise ValueError("deterministic replay mismatch")
        stage = "WRITING_REPORT_LEDGER"
        write_exclusive(output / "source_ledger.jsonl", ledger_a)
        write_exclusive(output / "source_report.json", report_raw)
        stage = "REHASHING_BOUND_INPUTS"
        final = {"source": sha256_file(source), "prereg": sha256_file(prereg),
                 "analyzer": sha256_file(analyzer), "test": sha256_file(test)}
        if initial != final:
            raise ValueError("bound input changed during attempt")
        stage = "WRITING_RECEIPT_TERMINAL"
        write_json(output / "attempt_receipt.json", {"schema_version": "follow_line_source_receipt.v1",
                   "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "bindings": initial,
                   "started_sha256": sha256_file(output / "attempt_started.json"),
                   "report_sha256": sha256_file(output / "source_report.json"),
                   "ledger_sha256": sha256_file(output / "source_ledger.jsonl"),
                   "deterministic_replay": True, "outcomes_read": False})
        write_json(output / "attempt_terminal.json", {"schema_version": "follow_line_source_attempt_terminal.v1",
                   "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "status": "COMPLETE",
                   "verdict": report_a["verdict"], "receipt_sha256": sha256_file(output / "attempt_receipt.json"),
                   "same_id_retry_allowed": False})
        print(json.dumps(report_a, indent=2, sort_keys=True))
    except Exception as exc:
        write_json(output / "attempt_terminal.json", {"schema_version": "follow_line_source_attempt_terminal.v1",
                   "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "status": "FAILED",
                   "failed_stage": stage, "error": str(exc), "captured_bindings": initial,
                   "observed": observed, "same_id_retry_allowed": False})
        raise


if __name__ == "__main__":
    execute()
