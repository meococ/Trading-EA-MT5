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


HYPOTHESIS_ID = "HYP-PVPR-EURUSD-M15-001"
ATTEMPT_ID = "PVPR001-SOURCE-001"
SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
PREREG = Path(__file__).resolve().with_name("HYP-PVPR-EURUSD-M15-001_FROZEN_SOURCE_PREREG.md")
TEST = Path(__file__).resolve().parent / "tests" / "test_analyze_pvpr_m15_source.py"
OUTPUT = Path(__file__).resolve().parent / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
READ_FROM = pd.Timestamp("2015-01-01 00:00:00")
DESIGN_FROM = pd.Timestamp("2016-01-04 00:00:00")
DESIGN_TO = pd.Timestamp("2023-01-01 00:00:00")
PIP = 0.0001
VALUE_AREA_FRACTION = 0.70
MIN_PROFILE_ROWS = 1000
SESSION_START_MINUTE = 7 * 60
SESSION_END_MINUTE = 16 * 60


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
    expected = ["time_server", "time_utc", "open", "high", "low", "close", "tick_volume"]
    if list(frame.columns) != expected:
        raise ValueError(f"unexpected source columns: {list(frame.columns)}")
    if frame[["time_server", "time_utc"]].isna().any().any():
        raise ValueError("null timestamp")
    for field in ("time_server", "time_utc"):
        if not frame[field].is_monotonic_increasing or frame[field].duplicated().any():
            raise ValueError(f"{field} must be strictly increasing and unique")
    ohlc = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(ohlc).all() or not (ohlc > 0.0).all():
        raise ValueError("OHLC must be finite and strictly positive")
    valid_geometry = (
        (ohlc[:, 1] >= ohlc[:, 2])
        & (ohlc[:, 1] >= np.maximum(ohlc[:, 0], ohlc[:, 3]))
        & (ohlc[:, 2] <= np.minimum(ohlc[:, 0], ohlc[:, 3]))
    )
    if not valid_geometry.all():
        raise ValueError("invalid M1 OHLC geometry")
    volume = frame["tick_volume"].to_numpy(dtype=float)
    if not np.isfinite(volume).all() or not (volume >= 0.0).all():
        raise ValueError("tick volume must be finite and nonnegative")


def aggregate_m15(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame[["time_utc", "open", "high", "low", "close"]].copy()
    work["bucket"] = work["time_utc"].dt.floor("15min")
    bars = (
        work.groupby("bucket", sort=True, observed=True)
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            m1_rows=("time_utc", "size"),
        )
        .reset_index()
        .rename(columns={"bucket": "time_utc"})
    )
    if not bars["time_utc"].is_monotonic_increasing or bars["time_utc"].duplicated().any():
        raise ValueError("M15 UTC buckets must be strictly increasing and unique")
    return bars


def build_profile(day: pd.DataFrame) -> dict | None:
    if len(day) < MIN_PROFILE_ROWS:
        return None
    times = day["time_utc"]
    first_minute = int(times.iloc[0].hour * 60 + times.iloc[0].minute)
    last_minute = int(times.iloc[-1].hour * 60 + times.iloc[-1].minute)
    if first_minute > 15 or last_minute < 23 * 60 + 45:
        return None
    volume = day["tick_volume"].to_numpy(dtype=float)
    total_volume = float(volume.sum())
    if not np.isfinite(total_volume) or total_volume <= 0.0:
        return None
    typical = day[["high", "low", "close"]].to_numpy(dtype=float).mean(axis=1)
    bin_indices = np.floor(typical / PIP + 0.5).astype(np.int64)
    minimum_bin = int(bin_indices.min())
    maximum_bin = int(bin_indices.max())
    volumes = np.bincount(bin_indices - minimum_bin, weights=volume, minlength=maximum_bin - minimum_bin + 1)
    mean_bin = float(np.dot(bin_indices.astype(float), volume) / total_volume)
    max_volume = float(volumes.max())
    poc_candidates = np.flatnonzero(volumes == max_volume) + minimum_bin
    poc_bin = int(min(poc_candidates.tolist(), key=lambda value: (abs(value - mean_bin), value)))
    left = poc_bin - minimum_bin
    right = left
    included = float(volumes[left])
    target = VALUE_AREA_FRACTION * total_volume
    while included < target and (left > 0 or right + 1 < len(volumes)):
        lower_volume = float(volumes[left - 1]) if left > 0 else -1.0
        upper_volume = float(volumes[right + 1]) if right + 1 < len(volumes) else -1.0
        if left > 0 and lower_volume >= upper_volume:
            left -= 1
            included += float(volumes[left])
        else:
            right += 1
            included += float(volumes[right])
    return {
        "poc": poc_bin * PIP,
        "val": (minimum_bin + left) * PIP,
        "vah": (minimum_bin + right) * PIP,
        "total_volume": total_volume,
        "m1_rows": int(len(day)),
        "included_fraction": included / total_volume,
    }


def profile_map(frame: pd.DataFrame) -> dict[pd.Timestamp, dict]:
    work = frame.copy()
    work["utc_date"] = work["time_utc"].dt.normalize()
    profiles: dict[pd.Timestamp, dict] = {}
    for utc_date, day in work.groupby("utc_date", sort=True, observed=True):
        profile = build_profile(day)
        if profile is not None:
            profiles[pd.Timestamp(utc_date)] = profile
    return profiles


def analyze(frame: pd.DataFrame) -> tuple[dict, bytes]:
    bars = aggregate_m15(frame)
    profiles = profile_map(frame)
    eligible_dates = [
        date
        for date in pd.date_range(DESIGN_FROM.normalize(), DESIGN_TO.normalize() - pd.Timedelta(days=1), freq="D")
        if date.weekday() in (1, 2, 3, 4)
    ]
    valid_dates = [date for date in eligible_dates if date - pd.Timedelta(days=1) in profiles]
    bar_date = bars["time_utc"].dt.normalize()
    bar_minute = bars["time_utc"].dt.hour * 60 + bars["time_utc"].dt.minute
    bars_by_date = {date: np.flatnonzero((bar_date == date).to_numpy()) for date in valid_dates}
    raw = 0
    gaps = 0
    boundaries = 0
    conflicts = 0
    events: list[dict] = []
    for date in valid_dates:
        profile = profiles[date - pd.Timedelta(days=1)]
        selected: tuple[int, str] | None = None
        for index in bars_by_date[date]:
            minute = int(bar_minute.iloc[index])
            if minute < SESSION_START_MINUTE or minute >= SESSION_END_MINUTE:
                continue
            source_open = float(bars.iloc[index]["open"])
            source_close = float(bars.iloc[index]["close"])
            inside = profile["val"] <= source_close <= profile["vah"]
            long_event = source_open < profile["val"] and inside
            short_event = source_open > profile["vah"] and inside
            if long_event and short_event:
                conflicts += 1
                raise ValueError("profile reentry direction conflict")
            if long_event or short_event:
                selected = (int(index), "LONG" if long_event else "SHORT")
                break
        if selected is None:
            continue
        index, direction = selected
        raw += 1
        exact_next = index + 1 < len(bars) and (bars.iloc[index + 1]["time_utc"] - bars.iloc[index]["time_utc"]).total_seconds() == 900
        if not exact_next:
            gaps += 1
            continue
        if bars.iloc[index + 1]["time_utc"] >= DESIGN_TO:
            boundaries += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "profile_date_utc": (date - pd.Timedelta(days=1)).date().isoformat(),
            "source_bar_time_utc": bars.iloc[index]["time_utc"].isoformat(),
            "decision_time_utc": bars.iloc[index + 1]["time_utc"].isoformat(),
            "availability_time_utc": bars.iloc[index + 1]["time_utc"].isoformat(),
            "direction": direction,
            "poc": round(float(profile["poc"]), 10),
            "val": round(float(profile["val"]), 10),
            "vah": round(float(profile["vah"]), 10),
            "source_open": round(float(bars.iloc[index]["open"]), 10),
            "source_close": round(float(bars.iloc[index]["close"]), 10),
            "profile_m1_rows": int(profile["m1_rows"]),
            "profile_total_tick_volume": round(float(profile["total_volume"]), 6),
        })
    ledger = b"".join(
        (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for event in events
    )
    design_rows = int(((frame["time_utc"] >= DESIGN_FROM) & (frame["time_utc"] < DESIGN_TO)).sum())
    weeks = (DESIGN_TO - DESIGN_FROM).total_seconds() / 604800.0
    n = len(events)
    by_direction = {direction: sum(event["direction"] == direction for event in events) for direction in ("LONG", "SHORT")}
    years = range(2016, 2023)
    by_year = {str(year): sum(pd.Timestamp(event["decision_time_utc"]).year == year for event in events) for year in years}
    year_weeks = {
        str(year): (
            min(DESIGN_TO, pd.Timestamp(f"{year + 1}-01-01"))
            - max(DESIGN_FROM, pd.Timestamp(f"{year}-01-01"))
        ).total_seconds() / 604800.0
        for year in years
    }
    profile_coverage = len(valid_dates) / len(eligible_dates) if eligible_dates else 0.0
    exact_next_coverage = n / raw if raw else 0.0
    gates = {
        "design_m1_rows_gte_1500000": design_rows >= 1_500_000,
        "valid_profile_coverage_gte_0_95": profile_coverage >= 0.95,
        "exact_next_coverage_gte_0_97": exact_next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "pooled_cadence_2_to_5": 2.0 <= n / weeks <= 5.0,
        "each_direction_gte_0_30": n > 0 and all(value / n >= 0.30 for value in by_direction.values()),
        "max_year_share_lte_0_25": n > 0 and max(by_year.values(), default=0) / n <= 0.25,
        "each_year_cadence_1_25_to_6_5": all(1.25 <= by_year[year] / year_weeks[year] <= 6.5 for year in by_year),
        "zero_conflicts": conflicts == 0,
    }
    verdict = (
        "SCREENED_SOURCE_PASS_MQL5_BUILD_AUTHORIZED"
        if all(gates.values())
        else "PARK_SOURCE_FEASIBILITY_EXACT_PRIOR_DAY_VOLUME_PROFILE_REENTRY"
    )
    report = {
        "schema_version": "pvpr_m15_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "formula": {
            "pip": PIP,
            "value_area_fraction": VALUE_AREA_FRACTION,
            "minimum_profile_m1_rows": MIN_PROFILE_ROWS,
            "eligible_weekdays": ["TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
            "session_utc": "07:00-16:00",
            "event_limit_per_date": 1,
        },
        "rows": {"m1_total": len(frame), "design_m1": design_rows, "m15_total": len(bars)},
        "profiles": {"eligible_dates": len(eligible_dates), "valid_dates": len(valid_dates), "coverage": profile_coverage},
        "events": {"raw": raw, "executable": n, "gap_rejects": gaps, "boundary_rejects": boundaries, "conflicts": conflicts},
        "weeks": weeks,
        "cadence_per_week": n / weeks,
        "exact_next_coverage": exact_next_coverage,
        "year_axis": "decision_time_utc",
        "by_direction": by_direction,
        "direction_share": {direction: by_direction[direction] / n if n else 0.0 for direction in by_direction},
        "by_year": by_year,
        "year_cadence": {year: by_year[year] / year_weeks[year] for year in by_year},
        "max_year_share": max(by_year.values(), default=0) / n if n else 0.0,
        "gates": gates,
        "verdict": verdict,
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
    stage = "ROOT_CLAIMED"
    initial: dict[str, str] = {}
    observed: dict[str, object] = {}
    try:
        write_json(output / "attempt_started.json", {
            "schema_version": "pvpr_source_attempt_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": str(source),
        })
        stage = "HASHING_BOUND_INPUTS"
        initial = {
            "source": sha256_file(source),
            "prereg": sha256_file(prereg),
            "analyzer": sha256_file(analyzer),
            "test": sha256_file(test),
        }
        if initial["source"] != SOURCE_SHA256:
            raise ValueError(f"source SHA mismatch: {initial['source']}")
        stage = "READING_NATIVE_M1_SOURCE"
        table = pq.read_table(
            source,
            columns=["time_server", "time_utc", "open", "high", "low", "close", "tick_volume"],
            filters=[
                ("time_utc", ">=", READ_FROM.to_pydatetime()),
                ("time_utc", "<", DESIGN_TO.to_pydatetime()),
            ],
        )
        frame = table.to_pandas()
        observed["m1_rows"] = len(frame)
        validate_source(frame)
        if frame["time_utc"].min() < READ_FROM or frame["time_utc"].max() >= DESIGN_TO:
            raise ValueError("source predicate window breach")
        stage = "ANALYZING_SOURCE_GATES"
        report_a, ledger_a = analyze(frame)
        observed["design_rows"] = report_a["rows"]["design_m1"]
        observed["valid_profile_dates"] = report_a["profiles"]["valid_dates"]
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
            "schema_version": "pvpr_source_receipt.v1",
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
            "schema_version": "pvpr_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": report_a["verdict"],
            "receipt_sha256": sha256_file(output / "attempt_receipt.json"),
            "same_id_retry_allowed": False,
        })
        print(json.dumps(report_a, indent=2, sort_keys=True))
    except Exception as exc:
        terminal = output / "attempt_terminal.json"
        if not terminal.exists():
            write_json(terminal, {
                "schema_version": "pvpr_source_attempt_terminal.v1",
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
