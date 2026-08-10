#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-RVI-EURUSD-H1-001"
ATTEMPT_ID = "RVI001-SOURCE-ATTEMPT-001"
SOURCE_SHA256 = "71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08"
RVI_REFERENCE_SHA256 = "AB6F66E19B0FDB1D1DA81CE42DA5D41C6C978607B2BE78B6EAFBE09C4E378DC0"
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_H1_2015_now.parquet"
RVI_REFERENCE = ROOT / "02. AlphaFactory" / "runtime" / "mt5-portable-fivepercent" / "MQL5" / "Indicators" / "Examples" / "RVI.mq5"
PREREG = Path(__file__).resolve().with_name("HYP-RVI-EURUSD-H1-001_FROZEN_PREREG.md")
TEST = Path(__file__).resolve().parent / "tests" / "test_analyze_rvi_source.py"
OUTPUT = Path(__file__).resolve().parent / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
DESIGN_FROM = pd.Timestamp("2016-01-04 00:00:00")
DESIGN_TO = pd.Timestamp("2021-01-01 00:00:00")
READ_FROM = pd.Timestamp("2015-01-01 00:00:00")
PERIOD = 10


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_json_x(path: Path, obj: dict) -> None:
    write_bytes_x(path, (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode())


def write_bytes_x(path: Path, raw: bytes) -> None:
    with path.open("xb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())


def rvi_values(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    co = (frame["close"] - frame["open"]).to_numpy(dtype=float)
    hl = (frame["high"] - frame["low"]).to_numpy(dtype=float)
    n = len(frame)
    weighted_up = np.full(n, np.nan)
    weighted_down = np.full(n, np.nan)
    for i in range(3, n):
        weighted_up[i] = co[i] + 2.0 * co[i - 1] + 2.0 * co[i - 2] + co[i - 3]
        weighted_down[i] = hl[i] + 2.0 * hl[i - 1] + 2.0 * hl[i - 2] + hl[i - 3]
    up_sum = pd.Series(weighted_up).rolling(PERIOD, min_periods=PERIOD).sum().to_numpy()
    down_sum = pd.Series(weighted_down).rolling(PERIOD, min_periods=PERIOD).sum().to_numpy()
    main = np.divide(up_sum, down_sum, out=np.full(n, np.nan), where=np.isfinite(down_sum) & (down_sum > 0.0))
    signal = np.full(n, np.nan)
    for i in range(3, n):
        values = main[i - 3 : i + 1]
        if np.isfinite(values).all():
            signal[i] = (values[3] + 2.0 * values[2] + 2.0 * values[1] + values[0]) / 6.0
    return main, signal


def validate_frame(frame: pd.DataFrame) -> None:
    expected = ["time_server", "time_utc", "open", "high", "low", "close"]
    if list(frame.columns) != expected:
        raise ValueError(f"unexpected columns: {list(frame.columns)}")
    if frame["time_server"].isna().any() or frame["time_utc"].isna().any():
        raise ValueError("null timestamp")
    if not frame["time_server"].is_monotonic_increasing or frame["time_server"].duplicated().any():
        raise ValueError("H1 timestamps not strictly unique/increasing")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite H1 OHLC")
    valid = ((values[:, 1] >= np.maximum(values[:, 0], values[:, 3])) &
             (values[:, 2] <= np.minimum(values[:, 0], values[:, 3])) &
             (values[:, 1] >= values[:, 2]))
    if not valid.all():
        raise ValueError("invalid H1 geometry")


def analyze(frame: pd.DataFrame) -> tuple[dict, bytes]:
    main, signal = rvi_values(frame)
    times = frame["time_server"].tolist()
    raw = gaps = boundaries = 0
    events = []
    for i in range(16, len(frame)):
        values = (main[i - 1], signal[i - 1], main[i], signal[i])
        if not all(math.isfinite(float(x)) for x in values):
            continue
        long_event = main[i - 1] <= signal[i - 1] and main[i] > signal[i] and main[i] < 0.0 and signal[i] < 0.0
        short_event = main[i - 1] >= signal[i - 1] and main[i] < signal[i] and main[i] > 0.0 and signal[i] > 0.0
        if long_event and short_event:
            raise ValueError("simultaneous direction conflict")
        if not (long_event or short_event) or not (DESIGN_FROM <= times[i] < DESIGN_TO):
            continue
        raw += 1
        if i + 1 >= len(frame) or (times[i + 1] - times[i]).total_seconds() != 3600:
            gaps += 1
            continue
        if times[i + 1] >= DESIGN_TO:
            boundaries += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_time_server": times[i].isoformat(),
            "decision_time_server": times[i + 1].isoformat(),
            "direction": "LONG" if long_event else "SHORT",
            "rvi_main_prior": round(float(main[i - 1]), 12),
            "rvi_signal_prior": round(float(signal[i - 1]), 12),
            "rvi_main_current": round(float(main[i]), 12),
            "rvi_signal_current": round(float(signal[i]), 12),
        })
    ledger = b"".join((json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n").encode() for e in events)
    design_mask = (frame["time_server"] >= DESIGN_FROM).to_numpy() & (frame["time_server"] < DESIGN_TO).to_numpy()
    usable = int((np.isfinite(main) & np.isfinite(signal) & design_mask).sum())
    design_rows = int(design_mask.sum())
    weeks = (DESIGN_TO - DESIGN_FROM).total_seconds() / 604800.0
    n = len(events)
    directions = {d: sum(e["direction"] == d for e in events) for d in ("LONG", "SHORT")}
    years = {str(y): sum(pd.Timestamp(e["source_time_server"]).year == y for e in events) for y in range(2016, 2021)}
    year_weeks = {}
    for y in range(2016, 2021):
        lo = max(DESIGN_FROM, pd.Timestamp(f"{y}-01-01")); hi = min(DESIGN_TO, pd.Timestamp(f"{y+1}-01-01"))
        year_weeks[str(y)] = (hi - lo).total_seconds() / 604800.0
    gates = {
        "design_rows_gte_25000": design_rows >= 25000,
        "usable_coverage_gte_0_99": design_rows > 0 and usable / design_rows >= 0.99,
        "candidates_gte_500": n >= 500,
        "pooled_cadence_2_to_5": 2.0 <= n / weeks <= 5.0,
        "each_direction_gte_0_30": n > 0 and all(v / n >= 0.30 for v in directions.values()),
        "max_year_share_lte_0_35": n > 0 and max(years.values(), default=0) / n <= 0.35,
        "each_year_cadence_1_25_to_6_5": all(1.25 <= years[y] / year_weeks[y] <= 6.5 for y in years),
        "zero_conflicts": True,
    }
    report = {
        "schema_version": "rvi_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "formula": {"period": PERIOD, "weighted_kernel": [1, 2, 2, 1], "signal_divisor": 6},
        "rows": {"h1_total": len(frame), "design": design_rows, "usable_design": usable},
        "events": {"raw": raw, "executable": n, "gap_rejects": gaps, "boundary_rejects": boundaries},
        "weeks": weeks,
        "cadence_per_week": n / weeks,
        "by_direction": directions,
        "direction_share": {d: directions[d] / n if n else 0.0 for d in directions},
        "by_year": years,
        "year_cadence": {y: years[y] / year_weeks[y] for y in years},
        "max_year_share": max(years.values(), default=0) / n if n else 0.0,
        "gates": gates,
        "verdict": "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY",
        "economic_fields_read": False,
    }
    return report, ledger


def execute() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=False)
    write_json_x(OUTPUT / "attempt_started.json", {
        "schema_version": "rvi_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_paths": {"source": str(SOURCE.resolve()), "reference": str(RVI_REFERENCE.resolve()), "prereg": str(PREREG.resolve()), "analyzer": str(Path(__file__).resolve()), "test": str(TEST.resolve())},
    })
    try:
        bound = {"source": SOURCE, "reference": RVI_REFERENCE, "prereg": PREREG, "analyzer": Path(__file__), "test": TEST}
        pre = {k: sha256_file(v.resolve()) for k, v in bound.items()}
        if pre["source"] != SOURCE_SHA256 or pre["reference"] != RVI_REFERENCE_SHA256:
            raise ValueError("source or MetaQuotes RVI reference SHA mismatch")
        table = pq.read_table(SOURCE, columns=["time_server", "time_utc", "open", "high", "low", "close"], filters=[("time_server", ">=", READ_FROM.to_pydatetime()), ("time_server", "<", DESIGN_TO.to_pydatetime())])
        frame = table.to_pandas(); validate_frame(frame)
        report_a, ledger_a = analyze(frame); report_b, ledger_b = analyze(frame.copy(deep=True))
        report_a_raw = (json.dumps(report_a, indent=2, sort_keys=True) + "\n").encode(); report_b_raw = (json.dumps(report_b, indent=2, sort_keys=True) + "\n").encode()
        if report_a_raw != report_b_raw or ledger_a != ledger_b:
            raise ValueError("deterministic replay mismatch")
        write_bytes_x(OUTPUT / "rvi_001_event_ledger.jsonl", ledger_a)
        write_bytes_x(OUTPUT / "rvi_001_source_report.json", report_a_raw)
        post = {k: sha256_file(v.resolve()) for k, v in bound.items()}
        if pre != post:
            raise ValueError("bound input changed during source attempt")
        receipt = {"schema_version": "rvi_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "bound_sha256": pre, "started_sha256": sha256_file(OUTPUT / "attempt_started.json"), "report_sha256": sha256_file(OUTPUT / "rvi_001_source_report.json"), "ledger_sha256": sha256_file(OUTPUT / "rvi_001_event_ledger.jsonl"), "deterministic_replay": True, "outcomes_read": False}
        write_json_x(OUTPUT / "source_feasibility_receipt.json", receipt)
        write_json_x(OUTPUT / "attempt_terminal.json", {"schema_version": "rvi_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "status": "COMPLETE", "verdict": report_a["verdict"], "receipt_sha256": sha256_file(OUTPUT / "source_feasibility_receipt.json"), "same_id_retry_allowed": False})
        print(json.dumps(report_a, indent=2, sort_keys=True))
    except Exception as exc:
        if not (OUTPUT / "attempt_terminal.json").exists():
            write_json_x(OUTPUT / "attempt_terminal.json", {"schema_version": "rvi_source_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "status": "FAILED", "error": str(exc), "same_id_retry_allowed": False})
        raise


def main() -> None:
    argparse.ArgumentParser(description="Run sole canonical RVI001 source scan").parse_args()
    execute()


if __name__ == "__main__":
    main()
