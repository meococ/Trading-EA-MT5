#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-WTX-EURUSD-H1-001"
ATTEMPT_ID = "WTX001-SOURCE-001"
SOURCE_SHA256 = "71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08"
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_H1_2015_now.parquet"
PREREG = Path(__file__).resolve().with_name("HYP-WTX-EURUSD-H1-001_FROZEN_SOURCE_PREREG.md")
TEST = Path(__file__).resolve().parent / "tests" / "test_analyze_wavetrend_h1_source.py"
OUTPUT = Path(__file__).resolve().parent / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
READ_FROM = pd.Timestamp("2015-01-01 00:00:00")
DESIGN_FROM = pd.Timestamp("2016-01-04 00:00:00")
DESIGN_TO = pd.Timestamp("2023-01-01 00:00:00")
CHANNEL_LENGTH = 10
AVERAGE_LENGTH = 21
SIGNAL_LENGTH = 4
CI_SCALE = 0.015
EXTREME = 60.0
DESIGN_WARMUP_ROWS = 40


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


def validate_source(frame: pd.DataFrame) -> None:
    expected = ["time_server", "time_utc", "open", "high", "low", "close"]
    if list(frame.columns) != expected:
        raise ValueError(f"unexpected source columns: {list(frame.columns)}")
    if frame[["time_server", "time_utc"]].isna().any().any():
        raise ValueError("null source timestamp")
    if not frame["time_server"].is_monotonic_increasing or frame["time_server"].duplicated().any():
        raise ValueError("H1 time_server must be strictly increasing and unique")
    if not frame["time_utc"].is_monotonic_increasing or frame["time_utc"].duplicated().any():
        raise ValueError("H1 time_utc must be strictly increasing and unique")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("nonfinite H1 OHLC")
    valid = (
        (values[:, 1] >= values[:, 2])
        & (values[:, 1] >= np.maximum(values[:, 0], values[:, 3]))
        & (values[:, 2] <= np.minimum(values[:, 0], values[:, 3]))
    )
    if not valid.all():
        raise ValueError("invalid H1 OHLC geometry")


def ema_first_finite(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=float)
    alpha = 2.0 / (period + 1.0)
    seeded = False
    prior = np.nan
    for i, value in enumerate(values):
        if not np.isfinite(value):
            continue
        if not seeded:
            prior = float(value)
            seeded = True
        else:
            prior = alpha * float(value) + (1.0 - alpha) * prior
        out[i] = prior
    return out


def wavetrend_state(frame: pd.DataFrame) -> pd.DataFrame:
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    ap = (high + low + close) / 3.0
    esa = ema_first_finite(ap, CHANNEL_LENGTH)
    deviation = ema_first_finite(np.abs(ap - esa), CHANNEL_LENGTH)
    ci = np.full(len(ap), np.nan, dtype=float)
    valid_ci = np.isfinite(esa) & np.isfinite(deviation) & (deviation > 0.0)
    ci[valid_ci] = (ap[valid_ci] - esa[valid_ci]) / (CI_SCALE * deviation[valid_ci])
    wt1 = ema_first_finite(ci, AVERAGE_LENGTH)
    wt2 = pd.Series(wt1).rolling(SIGNAL_LENGTH, min_periods=SIGNAL_LENGTH).mean().to_numpy()
    usable = np.isfinite(wt1) & np.isfinite(wt2)
    signal = np.zeros(len(ap), dtype=np.int8)
    for i in range(1, len(ap)):
        if not (usable[i - 1] and usable[i]):
            continue
        long_event = wt1[i - 1] <= wt2[i - 1] and wt1[i] > wt2[i] and wt1[i] < -EXTREME
        short_event = wt1[i - 1] >= wt2[i - 1] and wt1[i] < wt2[i] and wt1[i] > EXTREME
        if long_event and short_event:
            raise ValueError("WaveTrend direction conflict")
        if long_event:
            signal[i] = 1
        elif short_event:
            signal[i] = -1
    return pd.DataFrame({
        "ap": ap,
        "esa10": esa,
        "d10": deviation,
        "ci": ci,
        "wt1": wt1,
        "wt2": wt2,
        "usable": usable,
        "signal": signal,
    })


def analyze(frame: pd.DataFrame) -> tuple[dict, bytes]:
    state = wavetrend_state(frame)
    times = frame["time_server"].tolist()
    raw = 0
    gaps = 0
    boundaries = 0
    events: list[dict] = []
    for i in range(1, len(frame)):
        direction_code = int(state.iloc[i]["signal"])
        if direction_code == 0 or not (DESIGN_FROM <= times[i] < DESIGN_TO):
            continue
        raw += 1
        exact_next = i + 1 < len(frame) and (times[i + 1] - times[i]).total_seconds() == 3600
        if not exact_next:
            gaps += 1
            continue
        if times[i + 1] >= DESIGN_TO:
            boundaries += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_server": times[i].isoformat(),
            "decision_time_server": times[i + 1].isoformat(),
            "availability_time_server": times[i + 1].isoformat(),
            "direction": "LONG" if direction_code > 0 else "SHORT",
            "wt1_prior": round(float(state.iloc[i - 1]["wt1"]), 12),
            "wt2_prior": round(float(state.iloc[i - 1]["wt2"]), 12),
            "wt1_current": round(float(state.iloc[i]["wt1"]), 12),
            "wt2_current": round(float(state.iloc[i]["wt2"]), 12),
        })
    ledger = b"".join(
        (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for event in events
    )
    design_indices = np.flatnonzero(
        ((frame["time_server"] >= DESIGN_FROM) & (frame["time_server"] < DESIGN_TO)).to_numpy()
    )
    design_rows = int(len(design_indices))
    eligible_indices = design_indices[DESIGN_WARMUP_ROWS:]
    usable_rows = int(state.iloc[eligible_indices]["usable"].sum()) if len(eligible_indices) else 0
    eligible_rows = int(len(eligible_indices))
    weeks = (DESIGN_TO - DESIGN_FROM).total_seconds() / 604800.0
    n = len(events)
    by_direction = {direction: sum(e["direction"] == direction for e in events) for direction in ("LONG", "SHORT")}
    years = range(2016, 2023)
    by_year = {str(year): sum(pd.Timestamp(e["decision_time_server"]).year == year for e in events) for year in years}
    year_weeks = {
        str(year): (
            min(DESIGN_TO, pd.Timestamp(f"{year + 1}-01-01"))
            - max(DESIGN_FROM, pd.Timestamp(f"{year}-01-01"))
        ).total_seconds() / 604800.0
        for year in years
    }
    exact_next_coverage = n / raw if raw else 0.0
    conflicts = 0
    gates = {
        "design_rows_gte_40000": design_rows >= 40000,
        "usable_coverage_gte_0_99": eligible_rows > 0 and usable_rows / eligible_rows >= 0.99,
        "exact_next_coverage_gte_0_97": exact_next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "pooled_cadence_2_to_5": 2.0 <= n / weeks <= 5.0,
        "each_direction_gte_0_30": n > 0 and all(value / n >= 0.30 for value in by_direction.values()),
        "max_year_share_lte_0_25": n > 0 and max(by_year.values(), default=0) / n <= 0.25,
        "each_year_cadence_1_25_to_6_5": all(1.25 <= by_year[year] / year_weeks[year] <= 6.5 for year in by_year),
        "zero_conflicts": conflicts == 0,
    }
    report = {
        "schema_version": "wavetrend_h1_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "formula": {
            "channel_length": CHANNEL_LENGTH,
            "average_length": AVERAGE_LENGTH,
            "signal_length": SIGNAL_LENGTH,
            "ci_scale": CI_SCALE,
            "extreme": EXTREME,
            "ema_seed": "FIRST_FINITE",
        },
        "rows": {"h1_total": len(frame), "design": design_rows, "eligible_design": eligible_rows, "usable_design": usable_rows},
        "events": {"raw": raw, "executable": n, "gap_rejects": gaps, "boundary_rejects": boundaries, "conflicts": conflicts},
        "weeks": weeks,
        "cadence_per_week": n / weeks,
        "exact_next_coverage": exact_next_coverage,
        "feature_coverage": usable_rows / eligible_rows if eligible_rows else 0.0,
        "year_axis": "decision_time_server",
        "by_direction": by_direction,
        "direction_share": {direction: by_direction[direction] / n if n else 0.0 for direction in by_direction},
        "by_year": by_year,
        "year_cadence": {year: by_year[year] / year_weeks[year] for year in by_year},
        "max_year_share": max(by_year.values(), default=0) / n if n else 0.0,
        "gates": gates,
        "verdict": "SCREENED_SOURCE_PASS_DIRECT_MQL5_BUILD_AUTHORIZED" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY_EXACT_WAVETREND_EXTREME_CROSS",
        "outcomes_read": False,
        "economic_fields_read": False,
        "paid_data_used": False,
    }
    return report, ledger


def execute() -> None:
    source = SOURCE.resolve()
    prereg = PREREG.resolve()
    test = TEST.resolve()
    analyzer = Path(__file__).resolve()
    output = OUTPUT.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "attempt_started.json", {
        "schema_version": "wavetrend_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source),
    })
    stage = "ATTEMPT_CLAIMED"
    initial: dict[str, str] = {}
    observed: dict[str, object] = {}
    try:
        stage = "HASHING_BOUND_INPUTS"
        initial = {
            "source": sha256_file(source),
            "prereg": sha256_file(prereg),
            "analyzer": sha256_file(analyzer),
            "test": sha256_file(test),
        }
        if initial["source"] != SOURCE_SHA256:
            raise ValueError(f"source SHA mismatch: {initial['source']}")
        stage = "READING_NATIVE_H1_SOURCE"
        table = pq.read_table(
            source,
            columns=["time_server", "time_utc", "open", "high", "low", "close"],
            filters=[
                ("time_server", ">=", READ_FROM.to_pydatetime()),
                ("time_server", "<", DESIGN_TO.to_pydatetime()),
            ],
        )
        frame = table.to_pandas()
        observed["h1_rows"] = len(frame)
        validate_source(frame)
        if frame["time_server"].min() < READ_FROM or frame["time_server"].max() >= DESIGN_TO:
            raise ValueError("source predicate window breach")
        stage = "ANALYZING_SOURCE_GATES"
        report_a, ledger_a = analyze(frame)
        observed["design_rows"] = report_a["rows"]["design"]
        observed["raw_events"] = report_a["events"]["raw"]
        observed["executable_events"] = report_a["events"]["executable"]
        observed["gates"] = report_a["gates"]
        report_b, ledger_b = analyze(frame.copy(deep=True))
        report_raw = (json.dumps(report_a, indent=2, sort_keys=True) + "\n").encode()
        if report_raw != (json.dumps(report_b, indent=2, sort_keys=True) + "\n").encode() or ledger_a != ledger_b:
            raise ValueError("deterministic replay mismatch")
        stage = "REHASHING_BOUND_INPUTS"
        final = {
            "source": sha256_file(source),
            "prereg": sha256_file(prereg),
            "analyzer": sha256_file(analyzer),
            "test": sha256_file(test),
        }
        if final != initial:
            raise ValueError("bound input changed during attempt")
        stage = "WRITING_REPORT_LEDGER"
        write_exclusive(output / "source_ledger.jsonl", ledger_a)
        write_exclusive(output / "source_report.json", report_raw)
        stage = "WRITING_RECEIPT_TERMINAL"
        write_json(output / "attempt_receipt.json", {
            "schema_version": "wavetrend_source_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "bindings": initial,
            "started_sha256": sha256_file(output / "attempt_started.json"),
            "report_sha256": sha256_file(output / "source_report.json"),
            "ledger_sha256": sha256_file(output / "source_ledger.jsonl"),
            "deterministic_replay": True,
            "outcomes_read": False,
            "paid_data_used": False,
        })
        write_json(output / "attempt_terminal.json", {
            "schema_version": "wavetrend_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": report_a["verdict"],
            "receipt_sha256": sha256_file(output / "attempt_receipt.json"),
            "same_id_retry_allowed": False,
        })
        print(json.dumps(report_a, indent=2, sort_keys=True))
    except Exception as exc:
        write_json(output / "attempt_terminal.json", {
            "schema_version": "wavetrend_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "FAILED",
            "failed_stage": stage,
            "error": str(exc),
            "captured_bindings": initial,
            "observed": observed,
            "same_id_retry_allowed": False,
        })
        raise


if __name__ == "__main__":
    execute()
