from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[3]
ANALYSIS_ROOT = WORKSPACE / "02. AlphaFactory" / "analysis"
if str(ANALYSIS_ROOT) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_ROOT))
from quant_analyzer import parse_deals as parse_mt5_deals  # noqa: E402


MIN_COMPLETED_LIFECYCLES = 1000

SCENARIOS = {
    "EURUSD_MIDDAY_CONT": {"symbol": "EURUSD", "polarity": 1, "entry": 8 * 60 + 31, "exit": 12 * 60},
    "GBPUSD_MIDDAY_REV": {"symbol": "GBPUSD", "polarity": -1, "entry": 8 * 60 + 31, "exit": 12 * 60},
    "GBPUSD_LATE_FIX_REV": {"symbol": "GBPUSD", "polarity": -1, "entry": 15 * 60 + 30, "exit": 16 * 60},
    "GBPUSD_FULL_SESSION_REV": {"symbol": "GBPUSD", "polarity": -1, "entry": 8 * 60 + 31, "exit": 16 * 60 + 30},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def minute(value: str) -> int:
    item = parse_time(value)
    return item.hour * 60 + item.minute


def as_int(row: dict[str, str], key: str) -> int:
    return int(row[key])


def as_float(row: dict[str, str], key: str) -> float:
    return float(row[key])


def report_deal_counts(report: Path, symbol: str) -> tuple[int, int]:
    entries = 0
    exits = 0
    for deal in parse_mt5_deals(report):
        if deal.symbol != symbol:
            continue
        direction = deal.direction.strip().lower()
        if direction == "in":
            entries += 1
        elif direction == "out":
            exits += 1
        elif direction == "in/out":
            raise ValueError("unexpected in/out reversal deal in audit-only report")
    return entries, exits


@dataclass
class ScenarioResult:
    scenario: str
    run_dir: str
    passed: bool
    errors: list[str]
    counts: dict[str, int]
    files: list[dict[str, Any]]
    run_meta: dict[str, Any]


def one_file(logs: Path, pattern: str, errors: list[str]) -> Path | None:
    matches = sorted(logs.glob(pattern))
    if len(matches) != 1:
        errors.append(f"expected exactly one {pattern}, found {len(matches)}")
        return None
    return matches[0]


def validate_scenario(scenario: str, run_dir: Path) -> ScenarioResult:
    contract = SCENARIOS[scenario]
    errors: list[str] = []
    logs = run_dir / "logs"
    decision_path = one_file(logs, "*_DecisionTelemetry_*.csv", errors)
    lifecycle_path = one_file(logs, "*_LifecycleTrades_*.csv", errors)
    meta_path = one_file(logs, "*_RunMeta_*.json", errors)
    report_candidates = sorted(run_dir.glob("report.*"))
    if not report_candidates:
        errors.append("report is missing")
    report_entries = -1
    report_exits = -1
    if report_candidates:
        try:
            report_entries, report_exits = report_deal_counts(report_candidates[0], contract["symbol"])
        except Exception as exc:
            errors.append(f"report deals parse failed: {exc}")

    files: list[dict[str, Any]] = []
    for path in [decision_path, lifecycle_path, meta_path, *report_candidates[:1]]:
        if path is not None and path.exists():
            files.append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)})

    if decision_path is None or lifecycle_path is None or meta_path is None:
        return ScenarioResult(scenario, str(run_dir), False, errors, {}, files, {})

    decisions = read_csv(decision_path)
    lifecycle = read_csv(lifecycle_path)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        meta = {}
        errors.append(f"RunMeta malformed: {exc}")

    required_decision = {
        "server_time", "utc_time", "london_time", "london_date", "event", "status",
        "scenario", "set_name", "hypothesis_id", "formation_sign", "polarity", "direction",
        "source_0800_server", "source_0830_server", "source_0800_open_bid",
        "source_0830_open_bid", "source_0800_shift", "source_0830_shift",
        "signal_observed_server", "entry_eligible_server", "bid", "ask", "spread_points",
        "request_price", "actual_deal_price", "volume", "order_id", "deal_id",
        "position_id", "retcode", "reason",
    }
    actual_decision = set(decisions[0]) if decisions else set()
    if not decisions:
        errors.append("decision telemetry has no data rows")
    elif actual_decision != required_decision:
        errors.append(f"decision columns mismatch missing={sorted(required_decision-actual_decision)} extra={sorted(actual_decision-required_decision)}")

    signals = [row for row in decisions if row.get("event") == "SIGNAL_READY" and row.get("status") == "PASS"]
    entry_requests = [row for row in decisions if row.get("event") == "ENTRY_REQUEST"]
    entry_deals = [row for row in decisions if row.get("event") == "ENTRY_DEAL"]
    exit_requests = [row for row in decisions if row.get("event") == "EXIT_REQUEST"]
    exit_deals = [row for row in decisions if row.get("event") == "EXIT_DEAL"]

    signal_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in signals:
        signal_by_date[row["london_date"]].append(row)
        if row["scenario"] != scenario:
            errors.append(f"signal scenario mismatch on {row['london_date']}")
        if minute(row["london_time"]) != 8 * 60 + 31:
            errors.append(f"signal outside exact 08:31 minute on {row['london_date']}")
        if parse_time(row["london_time"]).strftime("%Y.%m.%d") != row["london_date"]:
            errors.append(f"signal london_date context mismatch on {row['london_date']}")
        if as_int(row, "polarity") != contract["polarity"]:
            errors.append(f"polarity mismatch on {row['london_date']}")
        if as_int(row, "source_0800_shift") < 1 or as_int(row, "source_0830_shift") < 1:
            errors.append(f"non-closed source shift on {row['london_date']}")
        if as_float(row, "source_0800_open_bid") <= 0 or as_float(row, "source_0830_open_bid") <= 0:
            errors.append(f"nonpositive source open on {row['london_date']}")
        expected_sign = 1 if as_float(row, "source_0830_open_bid") > as_float(row, "source_0800_open_bid") else -1
        if as_int(row, "formation_sign") != expected_sign:
            errors.append(f"formation sign mismatch on {row['london_date']}")
        if as_int(row, "direction") != contract["polarity"] * expected_sign:
            errors.append(f"direction mismatch on {row['london_date']}")

    if any(len(rows) != 1 for rows in signal_by_date.values()):
        errors.append("a date has duplicate SIGNAL_READY rows")

    entry_request_by_date = Counter(row["london_date"] for row in entry_requests)
    for row in entry_requests:
        date = row["london_date"]
        if len(signal_by_date.get(date, [])) != 1:
            errors.append(f"entry on {date} lacks exactly one prior signal")
        elif parse_time(signal_by_date[date][0]["server_time"]) > parse_time(row["server_time"]):
            errors.append(f"entry precedes signal on {date}")
        entry_minute = minute(row["london_time"])
        if scenario == "GBPUSD_LATE_FIX_REV":
            if not (contract["entry"] <= entry_minute < contract["exit"]):
                errors.append(f"LATE_FIX entry outside [15:30,16:00) on {date}")
        elif entry_minute != contract["entry"]:
            errors.append(f"MIDDAY/FULL entry outside exact 08:31 minute on {date}")
        if parse_time(row["london_time"]).strftime("%Y.%m.%d") != date:
            errors.append(f"entry london_date context mismatch on {date}")
        direction = as_int(row, "direction")
        requested = as_float(row, "request_price")
        expected_side = as_float(row, "ask" if direction > 0 else "bid")
        if abs(requested - expected_side) > 1e-9:
            errors.append(f"entry request not on executable side on {date}")
    if any(count != 1 for count in entry_request_by_date.values()):
        errors.append("a date has duplicate entry requests")

    for row in entry_deals:
        if as_float(row, "actual_deal_price") <= 0 or as_int(row, "deal_id") <= 0 or as_int(row, "position_id") <= 0:
            errors.append(f"invalid entry deal identifiers on {row['london_date']}")

    for row in exit_requests:
        if minute(row["london_time"]) < contract["exit"] and row["reason"] != "OVERNIGHT_EMERGENCY":
            errors.append(f"exit before frozen time on {row['london_date']}")
        if parse_time(row["london_time"]).strftime("%Y.%m.%d") != row["london_date"]:
            errors.append(f"exit london_date context mismatch on {row['london_date']}")
        direction = as_int(row, "direction")
        requested = as_float(row, "request_price")
        expected_side = as_float(row, "bid" if direction > 0 else "ask")
        if abs(requested - expected_side) > 1e-9:
            errors.append(f"exit request not on executable side on {row['london_date']}")

    opens = [row for row in lifecycle if row.get("action") == "OPEN"]
    final_closes = [row for row in lifecycle if row.get("action") == "CLOSE" and row.get("is_final_close") == "1"]
    if len(opens) != len(entry_deals):
        errors.append(f"lifecycle OPEN {len(opens)} != ENTRY_DEAL {len(entry_deals)}")
    if len(final_closes) != len(exit_deals):
        errors.append(f"lifecycle final CLOSE {len(final_closes)} != EXIT_DEAL {len(exit_deals)}")
    if len(opens) != len(final_closes):
        errors.append(f"unclosed lifecycle count opens={len(opens)} closes={len(final_closes)}")
    if report_entries != len(entry_deals) or report_entries != len(opens):
        errors.append(
            f"report entry deals {report_entries} != decision/lifecycle {len(entry_deals)}/{len(opens)}"
        )
    if report_exits != len(exit_deals) or report_exits != len(final_closes):
        errors.append(
            f"report exit deals {report_exits} != decision/lifecycle {len(exit_deals)}/{len(final_closes)}"
        )

    population_counts = {
        "signals_ready": len(signals),
        "entry_requests": len(entry_requests),
        "entry_deals": len(entry_deals),
        "lifecycle_opens": len(opens),
        "exit_deals": len(exit_deals),
        "lifecycle_final_closes": len(final_closes),
    }
    for label, count in population_counts.items():
        if count < MIN_COMPLETED_LIFECYCLES:
            errors.append(
                f"{label} population {count} below frozen engineering floor {MIN_COMPLETED_LIFECYCLES}"
            )

    exposure = 0
    for row in sorted(lifecycle, key=lambda item: parse_time(item["event_time"])):
        if row["action"] == "OPEN":
            exposure += 1
            if exposure > 1:
                errors.append("more than one concurrent position")
        elif row["action"] == "CLOSE" and row.get("is_final_close") == "1":
            exposure -= 1
            if exposure < 0:
                errors.append("close without an open position")
    if exposure != 0:
        errors.append("final lifecycle exposure is not zero")

    if meta.get("schema_version") != "alphafactory_run_meta.v1":
        errors.append("RunMeta schema mismatch")
    if meta.get("ea_name") != "EA_LondonOpenExecutionAudit" or meta.get("symbol") != contract["symbol"]:
        errors.append("RunMeta EA/symbol mismatch")
    if meta.get("variant_tag") != scenario or meta.get("audit_only") is not True:
        errors.append("RunMeta scenario/audit_only mismatch")
    if meta.get("performance_metrics_authorized") is not False or meta.get("promotion_eligible") is not False:
        errors.append("RunMeta economic authority must remain false")
    diag = meta.get("diagnostic", {})
    if diag.get("entries_opened") != len(opens):
        errors.append("RunMeta entries_opened does not reconcile")
    if diag.get("entries_closed") != len(final_closes):
        errors.append("RunMeta entries_closed does not reconcile")
    if diag.get("overnight_violations") != 0:
        errors.append("RunMeta reports overnight violations")

    counts = {
        "decision_rows": len(decisions),
        "signals_ready": len(signals),
        "entry_requests": len(entry_requests),
        "entry_deals": len(entry_deals),
        "exit_requests": len(exit_requests),
        "exit_deals": len(exit_deals),
        "lifecycle_opens": len(opens),
        "lifecycle_final_closes": len(final_closes),
        "report_entry_deals": report_entries,
        "report_exit_deals": report_exits,
        "minimum_completed_lifecycles": MIN_COMPLETED_LIFECYCLES,
    }
    return ScenarioResult(scenario, str(run_dir), not errors, errors, counts, files, meta)


def main() -> int:
    parser = argparse.ArgumentParser()
    for scenario in SCENARIOS:
        parser.add_argument(f"--{scenario.lower().replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    results = []
    for scenario in SCENARIOS:
        attr = scenario.lower()
        results.append(validate_scenario(scenario, getattr(args, attr)))

    payload = {
        "schema_version": "lomx_execution_audit.v1",
        "hypothesis_id": "HYP-LOMX-EXEC-AUDIT-M1-003",
        "audit_only": True,
        "performance_metrics_authorized": False,
        "passed": all(item.passed for item in results),
        "scenario_results": [item.__dict__ for item in results],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "scenarios": {item.scenario: item.passed for item in results}}))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
