#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-PVPR-EURUSD-M15-002"
ATTEMPT_ID = "PVPR002-SOURCE-001"
SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
POINT = 0.00001
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
PREREG = Path(__file__).resolve().with_name("HYP-PVPR-EURUSD-M15-002_FROZEN_SOURCE_PREREG.md")
TEST = Path(__file__).resolve().parent / "tests" / "test_analyze_pvpr_m15_source_v2.py"
FORMULA_DEPENDENCY = Path(__file__).resolve().with_name("analyze_pvpr_m15_source.py")
OUTPUT = Path(__file__).resolve().parent / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID


def load_base():
    spec = importlib.util.spec_from_file_location("pvpr_m15_source_v1_dependency", FORMULA_DEPENDENCY)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen HYP001 formula dependency")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_exclusive(path: Path, raw: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path: Path, payload: dict) -> None:
    write_exclusive(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())


def price_to_points(value: float) -> int:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("price must be finite and positive")
    return int(math.floor(value / POINT + 0.5))


def profile_price_to_points(value: float) -> int:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("profile price must be finite and positive")
    profile_bin = int(math.floor(value / BASE.PIP + 0.5))
    return profile_bin * 10


def classify_reentry(source_open: float, source_close: float, profile: dict) -> tuple[str | None, dict[str, int]]:
    fields = {
        "poc_points": profile_price_to_points(float(profile["poc"])),
        "val_points": profile_price_to_points(float(profile["val"])),
        "vah_points": profile_price_to_points(float(profile["vah"])),
        "source_open_points": price_to_points(source_open),
        "source_close_points": price_to_points(source_close),
    }
    inside = fields["val_points"] <= fields["source_close_points"] <= fields["vah_points"]
    long_event = fields["source_open_points"] < fields["val_points"] and inside
    short_event = fields["source_open_points"] > fields["vah_points"] and inside
    if long_event and short_event:
        raise ValueError("profile reentry direction conflict")
    direction = "LONG" if long_event else "SHORT" if short_event else None
    return direction, fields


def analyze(frame: pd.DataFrame) -> tuple[dict, bytes]:
    bars = BASE.aggregate_m15(frame)
    profiles = BASE.profile_map(frame)
    eligible_dates = [
        date
        for date in pd.date_range(BASE.DESIGN_FROM.normalize(), BASE.DESIGN_TO.normalize() - pd.Timedelta(days=1), freq="D")
        if date.weekday() in (1, 2, 3, 4)
    ]
    valid_dates = [date for date in eligible_dates if date - pd.Timedelta(days=1) in profiles]
    bar_date = bars["time_utc"].dt.normalize()
    bar_minute = bars["time_utc"].dt.hour * 60 + bars["time_utc"].dt.minute
    bars_by_date = {date: (bar_date == date).to_numpy().nonzero()[0] for date in valid_dates}
    raw = 0
    gaps = 0
    boundaries = 0
    conflicts = 0
    events: list[dict] = []
    for date in valid_dates:
        profile = profiles[date - pd.Timedelta(days=1)]
        selected: tuple[int, str, dict[str, int]] | None = None
        for index in bars_by_date[date]:
            minute = int(bar_minute.iloc[index])
            if minute < BASE.SESSION_START_MINUTE or minute >= BASE.SESSION_END_MINUTE:
                continue
            try:
                direction, point_fields = classify_reentry(
                    float(bars.iloc[index]["open"]),
                    float(bars.iloc[index]["close"]),
                    profile,
                )
            except ValueError as exc:
                if "conflict" in str(exc):
                    conflicts += 1
                raise
            if direction is not None:
                selected = (int(index), direction, point_fields)
                break
        if selected is None:
            continue
        index, direction, point_fields = selected
        raw += 1
        exact_next = (
            index + 1 < len(bars)
            and (bars.iloc[index + 1]["time_utc"] - bars.iloc[index]["time_utc"]).total_seconds() == 900
        )
        if not exact_next:
            gaps += 1
            continue
        if bars.iloc[index + 1]["time_utc"] >= BASE.DESIGN_TO:
            boundaries += 1
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "profile_date_utc": (date - pd.Timedelta(days=1)).date().isoformat(),
            "source_bar_time_utc": bars.iloc[index]["time_utc"].isoformat(),
            "decision_time_utc": bars.iloc[index + 1]["time_utc"].isoformat(),
            "availability_time_utc": bars.iloc[index + 1]["time_utc"].isoformat(),
            "direction": direction,
            **point_fields,
            "profile_m1_rows": int(profile["m1_rows"]),
            "profile_total_tick_volume": round(float(profile["total_volume"]), 6),
        })
    ledger = b"".join(
        (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
        for event in events
    )
    design_rows = int(((frame["time_utc"] >= BASE.DESIGN_FROM) & (frame["time_utc"] < BASE.DESIGN_TO)).sum())
    weeks = (BASE.DESIGN_TO - BASE.DESIGN_FROM).total_seconds() / 604800.0
    n = len(events)
    by_direction = {direction: sum(event["direction"] == direction for event in events) for direction in ("LONG", "SHORT")}
    years = range(2016, 2023)
    by_year = {str(year): sum(pd.Timestamp(event["decision_time_utc"]).year == year for event in events) for year in years}
    year_weeks = {
        str(year): (
            min(BASE.DESIGN_TO, pd.Timestamp(f"{year + 1}-01-01"))
            - max(BASE.DESIGN_FROM, pd.Timestamp(f"{year}-01-01"))
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
        else "PARK_SOURCE_FEASIBILITY_EXACT_PRIOR_DAY_VOLUME_PROFILE_REENTRY_INTEGER_POINTS"
    )
    report = {
        "schema_version": "pvpr_m15_source_report.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "parent_hypothesis_id": BASE.HYPOTHESIS_ID,
        "formula": {
            "broker_point": POINT,
            "profile_bin_points": 10,
            "price_rounding": "floor(price/0.00001+0.5)",
            "pip": BASE.PIP,
            "value_area_fraction": BASE.VALUE_AREA_FRACTION,
            "minimum_profile_m1_rows": BASE.MIN_PROFILE_ROWS,
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
    paths = {
        "source": SOURCE.resolve(),
        "prereg": PREREG.resolve(),
        "analyzer": Path(__file__).resolve(),
        "test": TEST.resolve(),
        "formula_dependency": FORMULA_DEPENDENCY.resolve(),
    }
    output = OUTPUT.resolve()
    output.mkdir(parents=True, exist_ok=False)
    stage = "ROOT_CLAIMED"
    initial: dict[str, str] = {}
    observed: dict[str, object] = {}
    try:
        write_json(output / "attempt_started.json", {
            "schema_version": "pvpr_source_attempt_started.v2",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": str(paths["source"]),
        })
        stage = "HASHING_BOUND_INPUTS"
        initial = {name: sha256_file(path) for name, path in paths.items()}
        if initial["source"] != SOURCE_SHA256:
            raise ValueError(f"source SHA mismatch: {initial['source']}")
        stage = "READING_NATIVE_M1_SOURCE"
        table = pq.read_table(
            paths["source"],
            columns=["time_server", "time_utc", "open", "high", "low", "close", "tick_volume"],
            filters=[
                ("time_utc", ">=", BASE.READ_FROM.to_pydatetime()),
                ("time_utc", "<", BASE.DESIGN_TO.to_pydatetime()),
            ],
        )
        frame = table.to_pandas()
        observed["m1_rows"] = len(frame)
        BASE.validate_source(frame)
        if frame["time_utc"].min() < BASE.READ_FROM or frame["time_utc"].max() >= BASE.DESIGN_TO:
            raise ValueError("source predicate window breach")
        stage = "ANALYZING_SOURCE_GATES"
        report_a, ledger_a = analyze(frame)
        observed["raw_events"] = report_a["events"]["raw"]
        observed["executable_events"] = report_a["events"]["executable"]
        observed["gates"] = report_a["gates"]
        report_b, ledger_b = analyze(frame.copy(deep=True))
        report_raw = (json.dumps(report_a, indent=2, sort_keys=True) + "\n").encode()
        if report_raw != (json.dumps(report_b, indent=2, sort_keys=True) + "\n").encode() or ledger_a != ledger_b:
            raise ValueError("deterministic replay mismatch")
        stage = "REHASHING_BOUND_INPUTS"
        final = {name: sha256_file(path) for name, path in paths.items()}
        if final != initial:
            raise ValueError("bound input changed during attempt")
        stage = "WRITING_REPORT_LEDGER"
        write_exclusive(output / "source_ledger.jsonl", ledger_a)
        write_exclusive(output / "source_report.json", report_raw)
        stage = "WRITING_RECEIPT_TERMINAL"
        write_json(output / "attempt_receipt.json", {
            "schema_version": "pvpr_source_receipt.v2",
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
            "schema_version": "pvpr_source_attempt_terminal.v2",
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
                "schema_version": "pvpr_source_attempt_terminal.v2",
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
