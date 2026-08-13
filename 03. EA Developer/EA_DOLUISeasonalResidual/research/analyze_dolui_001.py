"""Independent frozen-gate analyzer for DOLUI001 PRIMARY and REVERSE ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


HYPOTHESIS_ID = "HYP-DOL-UI-SEASONAL-RESIDUAL-EURUSD-H1-001"
EXPECTED_SOURCE_HASH = "3CD5D03DC85309724C5E3E616223657ACBA8DF86D4722F4A7EDAAB068C9009BA"
EXPECTED_SOURCE_RECEIPT_HASH = "58AF5CC103F8CFC2CD8D906818736C562E090EC3D3CD361C13903E01E06DB65C"
EXPECTED_TABLE_HASH = "20377DAA5449E0C10D67620768FA127B8FAEF5F49DDC802AF78DD8848F8C5A05"
EXPECTED_EVENTS = 260
EXPECTED_SOURCE_FLAT = 2
TRAIN_YEARS = {"2018", "2019", "2020", "2021", "2022"}
TERMINAL_STATUSES = {
    "CLOSED",
    "SKIP_SOURCE_FLAT",
    "SKIP_MISSED_ENTRY",
    "SKIP_DECISION_BAR_MISMATCH",
    "SKIP_WEEKEND_UNSAFE",
    "SKIP_OVERLAP",
    "ENTRY_REJECT",
    "EXIT_REJECT",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def close_enough(actual: float, expected: float, tolerance: float = 0.02) -> bool:
    return abs(actual - expected) <= tolerance


def profit_factor(values: list[float]) -> float:
    gain = sum(value for value in values if value > 0)
    loss = -sum(value for value in values if value < 0)
    return gain / loss if loss else math.inf


def closed_trade_drawdown(values: list[float], deposit: float = 100_000.0) -> float:
    equity = peak = deposit
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, 100.0 * (peak - equity) / peak)
    return maximum


def arm(rows: list[dict[str, str]], column: str) -> dict[str, float | int]:
    values = [float(row[column]) for row in rows]
    return {
        "trades": len(values),
        "net": sum(values),
        "profit_factor": profit_factor(values),
        "expectancy": sum(values) / len(values) if values else -math.inf,
        "closed_trade_drawdown_pct": closed_trade_drawdown(values),
    }


def validate_cost_row(row: dict[str, str]) -> None:
    lots = float(row["lots"])
    raw = float(row["raw_mid_pnl_usd"])
    executable = float(row["executable_pnl_usd"])
    observed = float(row["observed_spread_fill_cost_usd"])
    commission = float(row["commission_usd"])
    dynamic = float(row["dynamic_slippage_usd"])
    complete = float(row["complete_cost_usd"])
    entry_spread = float(row["entry_spread_pips"])
    exit_spread = float(row["exit_spread_pips"])
    pip_value = float(row["pip_value_per_lot"])
    expected_observed = max(0.0, raw - executable)
    expected_commission = 4.0 * lots
    expected_dynamic = 0.30 * (entry_spread + exit_spread) * pip_value * lots
    expected_complete = expected_observed + expected_commission + expected_dynamic
    if not close_enough(observed, expected_observed):
        raise ValueError(f"observed-cost mismatch for {row['event_id']}")
    if not close_enough(commission, expected_commission):
        raise ValueError(f"commission mismatch for {row['event_id']}")
    if not close_enough(dynamic, expected_dynamic):
        raise ValueError(f"dynamic-slippage mismatch for {row['event_id']}")
    if not close_enough(complete, expected_complete):
        raise ValueError(f"complete-cost mismatch for {row['event_id']}")
    for multiplier, column in ((1.0, "net_base_usd"), (1.5, "net_x1_5_usd"), (2.0, "net_x2_usd")):
        if not close_enough(float(row[column]), raw - multiplier * complete):
            raise ValueError(f"{column} mismatch for {row['event_id']}")


def read_role(path: Path, expected_role: str) -> tuple[list[dict[str, str]], dict[str, int]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_EVENTS:
        raise ValueError(f"event accounting mismatch in {path}: rows={len(rows)}")
    statuses: dict[str, int] = {}
    event_ids: set[str] = set()
    closed: list[dict[str, str]] = []
    for row in rows:
        status = row["status"]
        statuses[status] = statuses.get(status, 0) + 1
        if status not in TERMINAL_STATUSES:
            raise ValueError(f"unknown status {status} in {path}")
        if row["role"] != expected_role or row["hypothesis_id"] != HYPOTHESIS_ID:
            raise ValueError(f"role/hypothesis mismatch in {path}")
        if row["event_id"] in event_ids:
            raise ValueError(f"duplicate event {row['event_id']} in {path}")
        event_ids.add(row["event_id"])
        if status != "CLOSED":
            continue
        if int(row["entry_tick_msc"]) < 1000 * int(row["entry_target"]):
            raise ValueError(f"pre-boundary entry in {path}")
        if int(row["entry_tick_msc"]) > 1000 * (int(row["entry_target"]) + 300):
            raise ValueError(f"late accepted entry in {path}")
        if int(row["exit_tick_msc"]) < 1000 * int(row["exit_target"]):
            raise ValueError(f"pre-boundary exit in {path}")
        if not (0.0 < float(row["lots"]) <= 1.0):
            raise ValueError(f"invalid lot in {path}")
        validate_cost_row(row)
        closed.append(row)
    if statuses.get("SKIP_SOURCE_FLAT", 0) != EXPECTED_SOURCE_FLAT:
        raise ValueError(f"source-flat mismatch in {path}: {statuses}")
    return closed, statuses


def role_summary(path: Path, role: str) -> dict[str, object]:
    rows, statuses = read_role(path, role)
    year_net = {year: 0.0 for year in TRAIN_YEARS}
    year_trades = {year: 0 for year in TRAIN_YEARS}
    for row in rows:
        year = str(datetime.fromtimestamp(int(row["release_utc"]), tz=timezone.utc).year)
        if year not in TRAIN_YEARS:
            raise ValueError(f"unexpected TRAIN year {year}")
        year_net[year] += float(row["net_base_usd"])
        year_trades[year] += 1
    base_values = [float(row["net_base_usd"]) for row in rows]
    positive_total = sum(value for value in base_values if value > 0)
    top_count = math.ceil(len(base_values) * 0.05)
    top_share = (
        sum(sorted(base_values, reverse=True)[:top_count]) / positive_total
        if positive_total > 0
        else math.inf
    )
    return {
        "role": role,
        "ledger_path": str(path.resolve()),
        "ledger_sha256": sha256(path),
        "status_counts": statuses,
        "base": arm(rows, "net_base_usd"),
        "cost_x1_5": arm(rows, "net_x1_5_usd"),
        "cost_x2": arm(rows, "net_x2_usd"),
        "year_base_net": dict(sorted(year_net.items())),
        "year_completed_trades": dict(sorted(year_trades.items())),
        "positive_years": sum(value > 0 for value in year_net.values()),
        "top_5pct": {"count": top_count, "gross_profit_share": top_share},
    }


def validate_meta(path: Path, role: str) -> dict[str, object]:
    meta = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "hypothesis_id": HYPOTHESIS_ID,
        "role": role,
        "source_sha256": EXPECTED_SOURCE_HASH,
        "source_receipt_sha256": EXPECTED_SOURCE_RECEIPT_HASH,
        "table_sha256": EXPECTED_TABLE_HASH,
        "events": EXPECTED_EVENTS,
        "accounted": EXPECTED_EVENTS,
        "source_flat": EXPECTED_SOURCE_FLAT,
        "max_concurrent": 1,
        "active_event": -1,
        "runtime_failed": False,
    }
    for key, value in required.items():
        if meta.get(key) != value:
            raise ValueError(f"invalid run meta {key}: {path}")
    return {"path": str(path.resolve()), "sha256": sha256(path), "payload": meta}


def load_native_summary(path: Path) -> dict[str, object]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    if "max_drawdown_pct" not in summary:
        raise ValueError(f"native summary lacks max_drawdown_pct: {path}")
    return {"path": str(path.resolve()), "sha256": sha256(path), "payload": summary}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--primary-meta", type=Path, required=True)
    parser.add_argument("--primary-native-summary", type=Path, required=True)
    parser.add_argument("--reverse", type=Path, required=True)
    parser.add_argument("--reverse-meta", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    primary = role_summary(args.primary, "PRIMARY")
    reverse = role_summary(args.reverse, "REVERSE")
    primary_meta = validate_meta(args.primary_meta, "PRIMARY")
    reverse_meta = validate_meta(args.reverse_meta, "REVERSE")
    native = load_native_summary(args.primary_native_summary)
    gates = {
        "all_260_events_accounted": sum(primary["status_counts"].values()) == EXPECTED_EVENTS,
        "exactly_2_source_flat": primary["status_counts"].get("SKIP_SOURCE_FLAT", 0) == 2,
        "completed_at_least_250": primary["base"]["trades"] >= 250,
        "each_year_completed_at_least_48": all(
            value >= 48 for value in primary["year_completed_trades"].values()
        ),
        "at_least_3_of_5_positive_years": primary["positive_years"] >= 3,
        "base_pf_at_least_1_30": primary["base"]["profit_factor"] >= 1.30,
        "base_expectancy_positive": primary["base"]["expectancy"] > 0,
        "cost_x1_5_pf_at_least_1_25": primary["cost_x1_5"]["profit_factor"] >= 1.25,
        "cost_x2_pf_at_least_1_00": primary["cost_x2"]["profit_factor"] >= 1.0,
        "cost_x2_expectancy_nonnegative": primary["cost_x2"]["expectancy"] >= 0,
        "native_drawdown_at_most_8pct": float(native["payload"]["max_drawdown_pct"]) <= 8.0,
        "reverse_base_pf_inferior": reverse["base"]["profit_factor"] < primary["base"]["profit_factor"],
        "reverse_base_expectancy_inferior": reverse["base"]["expectancy"] < primary["base"]["expectancy"],
        "top_5pct_share_at_most_30pct": primary["top_5pct"]["gross_profit_share"] <= 0.30,
    }
    passed = all(gates.values())
    payload = {
        "schema_version": "dolui_001_train_economic_analysis.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_sha256": EXPECTED_SOURCE_HASH,
        "table_sha256": EXPECTED_TABLE_HASH,
        "primary_meta": primary_meta,
        "reverse_meta": reverse_meta,
        "primary_native_summary": native,
        "primary": primary,
        "reverse": reverse,
        "gates": gates,
        "passed_all_gates": passed,
        "verdict": "PASS_ALL_FROZEN_TRAIN_GATES" if passed else "KILL_FROZEN_MAPPING",
        "failed_gates": [name for name, value in gates.items() if not value],
        "validation_open_authorized": passed,
        "optimization_authorized": False,
        "same_id_rerun_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": payload["verdict"], "failed_gates": payload["failed_gates"]}))


if __name__ == "__main__":
    main()
