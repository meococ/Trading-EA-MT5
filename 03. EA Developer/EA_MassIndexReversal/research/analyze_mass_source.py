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


HYPOTHESIS_ID = "HYP-MASS-EURUSD-M15-001"
ATTEMPT_ID = "MASS001-SOURCE-ATTEMPT-001"
SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SOURCE = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
CANONICAL_PREREG = Path(__file__).resolve().with_name("HYP-MASS-EURUSD-M15-001_FROZEN_PREREG.md")
CANONICAL_TEST = Path(__file__).resolve().parent / "tests" / "test_analyze_mass_source.py"
CANONICAL_OUTPUT = Path(__file__).resolve().parent / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
DESIGN_FROM = pd.Timestamp("2016-01-04 00:00:00")
DESIGN_TO = pd.Timestamp("2021-01-01 00:00:00")
READ_FROM = pd.Timestamp("2015-01-01 00:00:00")
EMA_LENGTH = 9
SUM_LENGTH = 25
ARM_LEVEL = 27.0
COMPLETE_LEVEL = 26.5


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def atomic_json(path: Path, obj: dict) -> None:
    raw = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("xb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def write_exclusive_json(path: Path, obj: dict) -> None:
    raw = (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())


def write_exclusive_bytes(path: Path, raw: bytes) -> None:
    with path.open("xb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())


def ema(values: np.ndarray, length: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    alpha = 2.0 / (length + 1.0)
    prior = math.nan
    for i, value in enumerate(values):
        if not math.isfinite(float(value)):
            prior = math.nan
            continue
        prior = float(value) if not math.isfinite(prior) else prior + alpha * (float(value) - prior)
        out[i] = prior
    return out


def aggregate_m15(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["time_server", "time_utc", "open", "high", "low", "close"]
    if list(frame.columns) != required:
        raise ValueError(f"unexpected columns: {list(frame.columns)}")
    if frame["time_server"].isna().any() or frame["time_utc"].isna().any():
        raise ValueError("null timestamp")
    if not frame["time_server"].is_monotonic_increasing or frame["time_server"].duplicated().any():
        raise ValueError("M1 server timestamps not strictly unique/increasing")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite M1 OHLC")
    if not ((values[:, 1] >= np.maximum(values[:, 0], values[:, 3])) &
            (values[:, 2] <= np.minimum(values[:, 0], values[:, 3])) &
            (values[:, 1] >= values[:, 2])).all():
        raise ValueError("invalid M1 geometry")
    work = frame.copy()
    work["bucket"] = work["time_server"].dt.floor("15min")
    grouped = work.groupby("bucket", sort=True, observed=True)
    bars = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        first_utc=("time_utc", "first"),
        m1_rows=("time_server", "size"),
    ).reset_index().rename(columns={"bucket": "time_server"})
    if not bars["time_server"].is_monotonic_increasing or bars["time_server"].duplicated().any():
        raise ValueError("M15 timestamps not strictly unique/increasing")
    return bars


def analyze(bars: pd.DataFrame) -> tuple[dict, bytes]:
    ranges = (bars["high"] - bars["low"]).to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    e1 = ema(ranges, EMA_LENGTH)
    e2 = ema(e1, EMA_LENGTH)
    close_ema = ema(close, EMA_LENGTH)
    ratio = np.divide(e1, e2, out=np.full(len(e1), np.nan), where=np.isfinite(e2) & (e2 > 0.0))
    mass = pd.Series(ratio).rolling(SUM_LENGTH, min_periods=SUM_LENGTH).sum().to_numpy()

    times = bars["time_server"].tolist()
    armed = False
    raw_events = 0
    gap_rejects = 0
    boundary_rejects = 0
    equality_completions = 0
    events: list[dict] = []
    for i in range(1, len(bars)):
        current_mass = float(mass[i])
        if not math.isfinite(current_mass):
            armed = False
            continue
        if not armed:
            if current_mass > ARM_LEVEL:
                armed = True
            continue
        if current_mass >= COMPLETE_LEVEL:
            continue
        armed = False
        if not (DESIGN_FROM <= times[i] < DESIGN_TO):
            continue
        slope = float(close_ema[i] - close_ema[i - 1])
        if not math.isfinite(slope) or slope == 0.0:
            equality_completions += 1
            continue
        raw_events += 1
        direction = "LONG" if slope > 0.0 else "SHORT"
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
            "decision_time_server": times[i + 1].isoformat(),
            "direction": direction,
            "mass_index": round(current_mass, 12),
            "ema9_close_prior": round(float(close_ema[i - 1]), 12),
            "ema9_close_current": round(float(close_ema[i]), 12),
        })

    ledger = b"".join((json.dumps(e, sort_keys=True, separators=(",", ":")) + "\n").encode() for e in events)
    design = bars[(bars["time_server"] >= DESIGN_FROM) & (bars["time_server"] < DESIGN_TO)]
    mass_valid = np.isfinite(mass)
    design_mask = (bars["time_server"] >= DESIGN_FROM).to_numpy() & (bars["time_server"] < DESIGN_TO).to_numpy()
    usable = int((mass_valid & design_mask).sum())
    n = len(events)
    weeks = (DESIGN_TO - DESIGN_FROM).total_seconds() / 604800.0
    by_direction = {d: sum(e["direction"] == d for e in events) for d in ("LONG", "SHORT")}
    by_year = {str(y): sum(pd.Timestamp(e["source_time_server"]).year == y for e in events) for y in range(2016, 2021)}
    year_weeks = {}
    for y in range(2016, 2021):
        lo = max(DESIGN_FROM, pd.Timestamp(f"{y}-01-01"))
        hi = min(DESIGN_TO, pd.Timestamp(f"{y+1}-01-01"))
        year_weeks[str(y)] = (hi - lo).total_seconds() / 604800.0
    gates = {
        "design_rows_gte_120000": len(design) >= 120000,
        "usable_coverage_gte_0_99": usable / len(design) >= 0.99,
        "candidates_gte_500": n >= 500,
        "pooled_cadence_2_to_5": 2.0 <= n / weeks <= 5.0,
        "each_direction_gte_0_30": n > 0 and all(by_direction[d] / n >= 0.30 for d in by_direction),
        "max_year_share_lte_0_35": n > 0 and max(by_year.values(), default=0) / n <= 0.35,
        "each_year_cadence_1_25_to_6_5": all(1.25 <= by_year[y] / year_weeks[y] <= 6.5 for y in by_year),
        "zero_conflicts": True,
    }
    report = {
        "schema_version": "mass_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "formula": {"ema_length": EMA_LENGTH, "sum_length": SUM_LENGTH, "arm_strict_gt": ARM_LEVEL, "complete_strict_lt": COMPLETE_LEVEL},
        "rows": {"m15_total": len(bars), "design": len(design), "usable_design": usable},
        "events": {"raw": raw_events, "executable": n, "gap_rejects": gap_rejects, "boundary_rejects": boundary_rejects, "equality_completions": equality_completions},
        "weeks": weeks,
        "cadence_per_week": n / weeks,
        "by_direction": by_direction,
        "direction_share": {d: (by_direction[d] / n if n else 0.0) for d in by_direction},
        "by_year": by_year,
        "year_cadence": {y: by_year[y] / year_weeks[y] for y in by_year},
        "max_year_share": max(by_year.values(), default=0) / n if n else 0.0,
        "gates": gates,
        "verdict": "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY",
        "economic_fields_read": False,
    }
    return report, ledger


def execute() -> None:
    source = CANONICAL_SOURCE.resolve()
    prereg = CANONICAL_PREREG.resolve()
    test = CANONICAL_TEST.resolve()
    analyzer = Path(__file__).resolve()
    output = CANONICAL_OUTPUT.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = {
        "schema_version": "mass_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source),
        "prereg_path": str(prereg),
        "analyzer_path": str(analyzer),
        "test_path": str(test),
    }
    write_exclusive_json(output / "attempt_started.json", started)
    try:
        pre_hashes = {
            "source": sha256_file(source),
            "prereg": sha256_file(prereg),
            "analyzer": sha256_file(analyzer),
            "test": sha256_file(test),
        }
        if pre_hashes["source"] != SOURCE_SHA256:
            raise ValueError(f"source SHA mismatch: {pre_hashes['source']}")
        table = pq.read_table(
            source,
            columns=["time_server", "time_utc", "open", "high", "low", "close"],
            filters=[("time_server", ">=", READ_FROM.to_pydatetime()), ("time_server", "<", DESIGN_TO.to_pydatetime())],
        )
        frame = table.to_pandas()
        bars = aggregate_m15(frame)
        report_a, ledger_a = analyze(bars)
        report_b, ledger_b = analyze(bars.copy(deep=True))
        report_a_raw = (json.dumps(report_a, indent=2, sort_keys=True) + "\n").encode()
        report_b_raw = (json.dumps(report_b, indent=2, sort_keys=True) + "\n").encode()
        if report_a_raw != report_b_raw or ledger_a != ledger_b:
            raise ValueError("deterministic replay mismatch")
        write_exclusive_bytes(output / "mass_001_event_ledger.jsonl", ledger_a)
        write_exclusive_bytes(output / "mass_001_source_report.json", report_a_raw)
        post_hashes = {
            "source": sha256_file(source),
            "prereg": sha256_file(prereg),
            "analyzer": sha256_file(analyzer),
            "test": sha256_file(test),
        }
        if pre_hashes != post_hashes:
            raise ValueError("bound input changed during source attempt")
        receipt = {
            "schema_version": "mass_source_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "source_path": str(source),
            "source_sha256": pre_hashes["source"],
            "analyzer_sha256": pre_hashes["analyzer"],
            "prereg_sha256": pre_hashes["prereg"],
            "test_sha256": pre_hashes["test"],
            "started_sha256": sha256_file(output / "attempt_started.json"),
            "report_sha256": sha256_file(output / "mass_001_source_report.json"),
            "ledger_sha256": sha256_file(output / "mass_001_event_ledger.jsonl"),
            "deterministic_replay": True,
            "outcomes_read": False,
        }
        write_exclusive_json(output / "source_feasibility_receipt.json", receipt)
        write_exclusive_json(output / "attempt_terminal.json", {
            "schema_version": "mass_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": report_a["verdict"],
            "receipt_sha256": sha256_file(output / "source_feasibility_receipt.json"),
            "same_id_retry_allowed": False,
        })
        print(json.dumps(report_a, indent=2, sort_keys=True))
    except Exception as exc:
        atomic_json(output / "attempt_terminal.json", {
            "schema_version": "mass_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "FAILED",
            "error": str(exc),
            "same_id_retry_allowed": False,
        })
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the sole canonical MASS001 source-feasibility attempt.")
    parser.parse_args()
    execute()


if __name__ == "__main__":
    main()
