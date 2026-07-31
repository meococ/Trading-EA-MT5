#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_prepare_module():
    path = HERE / "prepare_hyp008_random100.py"
    spec = importlib.util.spec_from_file_location("prepare_hyp008_random100", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREP = load_prepare_module()
ROOT = PREP.ROOT
RUN = PREP.RUN
OUT = PREP.OUT
SUMMARY = OUT / "population_forensic_supplement.json"
WEEKEND = OUT / "weekend_tail_supplement.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def metrics(rows: list[dict]) -> dict:
    gains = sum(max(float(row["net_usd"]), 0.0) for row in rows)
    losses = -sum(min(float(row["net_usd"]), 0.0) for row in rows)
    initial_risk = sum(float(row["initial_risk_account"]) for row in rows)
    return {
        "n": len(rows),
        "wins": sum(float(row["net_usd"]) > 0 for row in rows),
        "losses": sum(float(row["net_usd"]) < 0 for row in rows),
        "flats": sum(float(row["net_usd"]) == 0 for row in rows),
        "win_rate_nonflat_pct": (
            100.0 * sum(float(row["net_usd"]) > 0 for row in rows)
            / max(sum(float(row["net_usd"]) != 0 for row in rows), 1)
        ),
        "net_usd": sum(float(row["net_usd"]) for row in rows),
        "profit_factor": gains / losses if losses else None,
        "mean_net_r": sum(float(row["net_r"]) for row in rows) / len(rows) if rows else None,
        "risk_weighted_net_r": sum(float(row["net_usd"]) for row in rows) / initial_risk if initial_risk else None,
    }


def grouped(rows: list[dict], key: str) -> dict:
    values = sorted({str(row[key]) for row in rows})
    return {value: metrics([row for row in rows if str(row[key]) == value]) for value in values}


def main() -> int:
    lifecycle = next((RUN / "analysis" / "logs").glob("*_LifecycleTrades_*.csv"))
    telemetry = next((RUN / "analysis" / "logs").glob("*_DecisionTelemetry_*.csv"))
    report = RUN / "report.html"
    selection_path = OUT / "selection_manifest.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))

    comments = PREP.load_report_close_comments(report)
    positions = PREP.load_positions(lifecycle, comments)
    if len(positions) != 3611:
        raise RuntimeError(f"Expected 3611 positions, got {len(positions)}")

    for row in positions:
        entry_server = datetime.strptime(row["entry_time"], "%Y.%m.%d %H:%M:%S")
        exit_server = datetime.strptime(row["exit_time"], "%Y.%m.%d %H:%M:%S")
        entry_utc = datetime.strptime(row["entry_time_utc"], "%Y.%m.%d %H:%M:%S")
        exit_utc = datetime.strptime(row["exit_time_utc"], "%Y.%m.%d %H:%M:%S")
        row["year"] = entry_utc.year
        row["overnight_utc"] = exit_utc.date() > entry_utc.date()
        row["weekend_crossing_utc"] = entry_utc.weekday() == 4 and exit_utc.date() > entry_utc.date()
        row["server_elapsed_minutes"] = (exit_server - entry_server).total_seconds() / 60.0

    decision_statuses: Counter[str] = Counter()
    with telemetry.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            decision_statuses[row["status"]] += 1

    weekend = [row for row in positions if row["weekend_crossing_utc"]]
    weekend.sort(key=lambda row: int(row["position_id"]))
    weekend_fields = [
        "position_id", "entry_time", "exit_time", "entry_time_utc", "exit_time_utc", "side",
        "entry", "lifecycle_sl", "exit", "net_usd", "net_r", "holding_minutes",
        "exit_class", "exit_comment", "active_stop_at_exit",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    with WEEKEND.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=weekend_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(weekend)

    payload = {
        "schema_version": "vras_hyp008_population_forensic_supplement.v1",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-008",
        "run_id": "20260722_233420",
        "forensic_only": True,
        "matched_pair_strict_validity": "PARTIAL_BINARY_HASH_MISMATCH_SOURCE_IDENTICAL",
        "exit_reason_authority": "MT5 closing-order comment joined by lifecycle final-close deal ID",
        "moved_sl_caveat": "MOVED_SL proves a changed close-stop price, not modification timing or successful +1R trigger logging",
        "population": metrics(positions),
        "by_exact_exit_class": grouped(positions, "exit_class"),
        "by_year_utc": grouped(positions, "year"),
        "by_direction": grouped(positions, "side"),
        "by_session_utc": grouped(positions, "session_utc"),
        "overnight_utc": metrics([row for row in positions if row["overnight_utc"]]),
        "weekend_crossing_utc": metrics(weekend),
        "weekend_extremes": {
            "best": max(weekend, key=lambda row: float(row["net_r"])) if weekend else None,
            "worst": min(weekend, key=lambda row: float(row["net_r"])) if weekend else None,
        },
        "decision_funnel": dict(sorted(decision_statuses.items())),
        "random_sample": {
            "selection_sha256": sha256(selection_path),
            "sample_composition": selection["sample_composition"],
            "weekend_sample_is_not_population_evidence": True,
        },
        "bindings": {
            "lifecycle": {"path": lifecycle.relative_to(ROOT).as_posix(), "sha256": sha256(lifecycle)},
            "decision_telemetry": {"path": telemetry.relative_to(ROOT).as_posix(), "sha256": sha256(telemetry)},
            "tester_report": {"path": report.relative_to(ROOT).as_posix(), "sha256": sha256(report)},
            "selection_manifest": {"path": selection_path.relative_to(ROOT).as_posix(), "sha256": sha256(selection_path)},
            "weekend_tail_csv": {"path": WEEKEND.relative_to(ROOT).as_posix(), "sha256": sha256(WEEKEND)},
        },
    }
    SUMMARY.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "HYP008_POPULATION_FORENSICS_READY",
        "population": payload["population"],
        "exit_classes": {key: value["n"] for key, value in payload["by_exact_exit_class"].items()},
        "weekend_crossings": payload["weekend_crossing_utc"]["n"],
        "summary": str(SUMMARY),
        "summary_sha256": sha256(SUMMARY),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
