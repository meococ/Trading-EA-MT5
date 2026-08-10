#!/usr/bin/env python3
"""Outcome-blind strict joint price-MFI pivot-divergence source analyzer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


BASE_PATH = Path(__file__).resolve().with_name("analyze_mfi_source.py")
BASE_SPEC = importlib.util.spec_from_file_location("mfi001_calculation_dependency", BASE_PATH)
assert BASE_SPEC and BASE_SPEC.loader
base = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(base)

HYPOTHESIS_ID = "HYP-MFI-XAUUSD-M5-003"
ATTEMPT_ID = "MFI003-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "177506E1B8B73300976094E8C96497E7613AE0BAD525F252753E93D4F5893883"
BASE_SHA256 = "FEEB94E517FB9D8ACE560703F98BE4F28150AA0A2071D01A179C365966DFDC2E"

PIVOT_RADIUS = 2
WARMUP_ROWS = 18
MIN_EVENTS = 500
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_DIRECTION_SHARE = 0.30
MAX_YEAR_SHARE = 0.30
MIN_YEAR_CADENCE = 1.25
MAX_YEAR_CADENCE = 6.50
MIN_FEATURE_COVERAGE = 0.99
MIN_RAW_EVENT_NEXT_COVERAGE = 0.97

EVENT_KEYS = {
    "hypothesis_id",
    "pivot_time_utc",
    "confirmation_time_utc",
    "decision_time_utc",
    "direction",
    "previous_pivot_price",
    "current_pivot_price",
    "previous_pivot_mfi14",
    "current_pivot_mfi14",
}


def _strict_low(values: np.ndarray, center: int) -> bool:
    value = float(values[center])
    return all(value < float(values[index]) for index in range(center - 2, center + 3) if index != center)


def _strict_high(values: np.ndarray, center: int) -> bool:
    value = float(values[center])
    return all(value > float(values[index]) for index in range(center - 2, center + 3) if index != center)


def detect_joint_divergence(
    lows: pd.Series,
    highs: pd.Series,
    mfi: pd.Series,
    times: pd.Series,
) -> tuple[list[dict[str, Any]], dict[str, int], pd.Series]:
    low_values = pd.to_numeric(lows, errors="coerce").to_numpy(dtype=float)
    high_values = pd.to_numeric(highs, errors="coerce").to_numpy(dtype=float)
    mfi_values = pd.to_numeric(mfi, errors="coerce").to_numpy(dtype=float)
    timestamps = pd.to_datetime(times, utc=True, errors="raise").reset_index(drop=True)
    if not (len(low_values) == len(high_values) == len(mfi_values) == len(timestamps)):
        raise ValueError("source series lengths differ")

    usable = pd.Series(False, index=range(len(timestamps)), dtype=bool)
    low_anchor: dict[str, Any] | None = None
    high_anchor: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    raw_events = 0
    gap_rejected = 0
    conflicts = 0

    for confirmation in range(WARMUP_ROWS, len(timestamps)):
        dependency_times = timestamps.iloc[confirmation - WARMUP_ROWS : confirmation + 1]
        contiguous = dependency_times.diff().iloc[1:].eq(pd.Timedelta(minutes=5)).all()
        pivot_slice = slice(confirmation - 4, confirmation + 1)
        finite = (
            np.isfinite(low_values[pivot_slice]).all()
            and np.isfinite(high_values[pivot_slice]).all()
            and np.isfinite(mfi_values[pivot_slice]).all()
        )
        if not (contiguous and finite):
            low_anchor = None
            high_anchor = None
            continue

        usable.iloc[confirmation] = True
        pivot = confirmation - PIVOT_RADIUS
        joint_low = _strict_low(low_values, pivot) and _strict_low(mfi_values, pivot)
        joint_high = _strict_high(high_values, pivot) and _strict_high(mfi_values, pivot)
        raw_long = False
        raw_short = False
        previous_low: dict[str, Any] | None = None
        previous_high: dict[str, Any] | None = None

        if joint_low:
            previous_low = low_anchor
            current_low = {
                "time": timestamps.iloc[pivot],
                "price": float(low_values[pivot]),
                "mfi": float(mfi_values[pivot]),
            }
            if previous_low is not None:
                raw_long = (
                    current_low["price"] < previous_low["price"]
                    and current_low["mfi"] > previous_low["mfi"]
                )
            low_anchor = current_low

        if joint_high:
            previous_high = high_anchor
            current_high = {
                "time": timestamps.iloc[pivot],
                "price": float(high_values[pivot]),
                "mfi": float(mfi_values[pivot]),
            }
            if previous_high is not None:
                raw_short = (
                    current_high["price"] > previous_high["price"]
                    and current_high["mfi"] < previous_high["mfi"]
                )
            high_anchor = current_high

        if not (raw_long or raw_short):
            continue
        raw_events += 1
        if raw_long and raw_short:
            conflicts += 1
            continue

        exact_next = confirmation + 1 < len(timestamps) and (
            timestamps.iloc[confirmation + 1] - timestamps.iloc[confirmation]
        ) == pd.Timedelta(minutes=5)
        if not exact_next:
            gap_rejected += 1
            continue

        direction = "LONG" if raw_long else "SHORT"
        previous = previous_low if raw_long else previous_high
        current = low_anchor if raw_long else high_anchor
        assert previous is not None and current is not None
        confirmation_time = timestamps.iloc[confirmation]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "pivot_time_utc": current["time"].isoformat().replace("+00:00", "Z"),
                "confirmation_time_utc": confirmation_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (confirmation_time + pd.Timedelta(minutes=5))
                .isoformat()
                .replace("+00:00", "Z"),
                "direction": direction,
                "previous_pivot_price": base.finite_float(previous["price"]),
                "current_pivot_price": base.finite_float(current["price"]),
                "previous_pivot_mfi14": base.finite_float(previous["mfi"]),
                "current_pivot_mfi14": base.finite_float(current["mfi"]),
            }
        )

    diagnostics = {
        "raw_events": raw_events,
        "executable_events": len(events),
        "gap_rejected_events": gap_rejected,
        "direction_conflicts": conflicts,
    }
    return events, diagnostics, usable


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    for column in ("high", "low", "close", "tick_volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    _, mfi, _, _ = base.calculate_mfi(data)
    events, diagnostics, usable = detect_joint_divergence(
        data["low"], data["high"], mfi, data["time_utc"]
    )

    feature_coverage = int(usable.iloc[WARMUP_ROWS:].sum()) / max(
        len(data) - WARMUP_ROWS, 1
    )
    next_coverage = diagnostics["executable_events"] / max(diagnostics["raw_events"], 1)
    count = len(events)
    elapsed_weeks = (base.DESIGN_END - base.DESIGN_START).total_seconds() / 604800.0
    cadence = count / elapsed_weeks
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = sum(row["direction"] == "SHORT" for row in events)
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    event_years = pd.Series(
        [pd.Timestamp(row["confirmation_time_utc"]).year for row in events], dtype="int64"
    )
    yearly: dict[str, dict[str, Any]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = base.year_weeks(year)
        yearly[str(year)] = {
            "events": year_count,
            "elapsed_weeks": weeks,
            "cadence_per_week": year_count / weeks,
            "share": year_count / count if count else 0.0,
        }
    max_year_share = max((row["share"] for row in yearly.values()), default=0.0)

    gates = {
        "minimum_design_rows": len(data) >= base.MIN_ROWS,
        "feature_coverage": feature_coverage >= MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_RAW_EVENT_NEXT_COVERAGE,
        "minimum_events": count >= MIN_EVENTS,
        "pooled_cadence": MIN_CADENCE <= cadence <= MAX_CADENCE,
        "direction_balance": long_share >= MIN_DIRECTION_SHARE
        and short_share >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "each_year_cadence": all(
            MIN_YEAR_CADENCE <= row["cadence_per_week"] <= MAX_YEAR_CADENCE
            for row in yearly.values()
        ),
        "zero_direction_conflicts": diagnostics["direction_conflicts"] == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "mfi_joint_divergence_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_STRICT_JOINT_PRICE_MFI_PIVOT_DIVERGENCE_ONLY",
        "window": {
            "from": base.DESIGN_START.isoformat(),
            "to_exclusive": base.DESIGN_END.isoformat(),
        },
        "parameters": {"mfi_period": 14, "pivot_radius": PIVOT_RADIUS, "thresholds": None},
        "funnel": {
            "design_rows": int(len(data)),
            "usable_confirmation_rows": int(usable.sum()),
            **diagnostics,
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
        "verdict": (
            "SCREENED_SOURCE_PASS_MQL5_IMFI_JOINT_DIVERGENCE_BUILD_AUTHORIZED"
            if passed
            else "PARK_SOURCE_FEASIBILITY_EXACT_MFI_JOINT_DIVERGENCE"
        ),
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
        "analyzer": validation.get("reviewed_analyzer_sha256")
        == base.sha256_file(Path(__file__).resolve()),
        "dependency": validation.get("mfi_calculation_dependency_sha256") == BASE_SHA256,
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
    return {
        "registry_sha256": base.sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path = output_dir / "attempt_started.json"
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker = {
        "schema_version": "mfi_joint_divergence_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "process_id": os.getpid(),
        "registry_sha256": authority["registry_sha256"],
        "latest_hypothesis_row_sha256": authority["latest_row_sha256"],
        "analyzer_sha256": base.sha256_file(Path(__file__).resolve()),
        "mfi_calculation_dependency_sha256": base.sha256_file(BASE_PATH),
        "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED",
    }
    try:
        with marker_path.open("xb") as handle:
            handle.write(base.json_bytes(marker))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("attempt already claimed") from exc
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg = root / "03. EA Developer/EA_MFIExtremeReentry/research/HYP-MFI-XAUUSD-M5-003_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = root / "03. EA Developer/EA_MFIExtremeReentry/research/evidence/HYP-MFI-XAUUSD-M5-003/MFI003-SOURCE-ATTEMPT-001"

    if base.sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration SHA mismatch")
    if base.sha256_file(BASE_PATH) != BASE_SHA256:
        raise ValueError("MFI calculation dependency SHA mismatch")
    authority = validate_registry_authority(registry)
    started, start_path = claim_attempt(output_dir, authority)
    base.validate_manifest(manifest, data_path)
    if base.sha256_file(data_path) != base.DATA_SHA256:
        raise ValueError("data SHA mismatch")
    if not set(base.REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("Parquet schema missing required columns")

    raw = pd.read_parquet(
        data_path,
        columns=list(base.REQUIRED_COLUMNS),
        filters=[
            ("time_utc", ">=", base.DESIGN_START.to_pydatetime()),
            ("time_utc", "<", base.DESIGN_END.to_pydatetime()),
        ],
        engine="pyarrow",
    )
    selected = base.validate_selected_frame(raw)
    events, report = analyze_frame(selected)
    assert_outcome_blind(events, report)
    replay_events, replay_report = analyze_frame(selected)
    if base.jsonl_bytes(events) != base.jsonl_bytes(replay_events) or base.json_bytes(
        report
    ) != base.json_bytes(replay_report):
        raise ValueError("deterministic replay failed")

    report_bytes = base.json_bytes(report)
    ledger_bytes = base.jsonl_bytes(events)
    report_path = output_dir / "mfi_003_source_report.json"
    ledger_path = output_dir / "mfi_003_event_ledger.jsonl"
    base.atomic_write(report_path, report_bytes)
    base.atomic_write(ledger_path, ledger_bytes)
    receipt = {
        "schema_version": "mfi_joint_divergence_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bindings": {
            "preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": base.sha256_file(prereg)},
            "manifest": {"path": manifest.relative_to(root).as_posix(), "sha256": base.sha256_file(manifest)},
            "data": {"path": data_path.relative_to(root).as_posix(), "sha256": base.sha256_file(data_path)},
            "analyzer": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": base.sha256_file(Path(__file__).resolve())},
            "mfi_calculation_dependency": {"path": BASE_PATH.relative_to(root).as_posix(), "sha256": base.sha256_file(BASE_PATH)},
            "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority},
            "attempt_started": {"path": start_path.relative_to(root).as_posix(), "sha256": base.sha256_file(start_path)},
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
    receipt_bytes = base.json_bytes(receipt)
    receipt_path = output_dir / "source_feasibility_receipt.json"
    base.atomic_write(receipt_path, receipt_bytes)
    terminal = {
        "schema_version": "mfi_joint_divergence_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": receipt["completed_at_utc"],
        "status": "COMPLETE",
        "verdict": report["verdict"],
        "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "same_id_retry_authorized": False,
    }
    base.atomic_write(output_dir / "attempt_terminal.json", base.json_bytes(terminal))
    return {"report": report, "receipt": receipt, "output_dir": str(output_dir)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    root = Path(__file__).resolve().parents[3]
    result = execute(root)
    print(base.json_bytes(result["report"]).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
