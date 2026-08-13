"""Independent frozen-gate analyzer for DEPTH009 PRIMARY and REVERSE ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_SOURCE_HASH = "3B3B0F4CF85FD733B26DE0CA84F890265C94693DC7A58170507491985B2687B8"
EXPECTED_TABLE_HASH = "BD2D3F6CF9C048F606F822EF2BEDF0C6DCA4CE6C25673A5235D70F8AC096A3DD"
DEGRADED = {"EVT0006", "EVT0027", "EVT0031", "EVT0198", "EVT0270"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pf(values: list[float]) -> float:
    gain = sum(x for x in values if x > 0)
    loss = -sum(x for x in values if x < 0)
    return gain / loss if loss else math.inf


def drawdown(values: list[float], deposit: float = 100_000.0) -> float:
    equity = peak = deposit
    maximum = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, 100.0 * (peak - equity) / peak)
    return maximum


def close_enough(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= 1e-6 * max(1.0, abs(actual), abs(expected))


def arm(rows: list[dict[str, str]], column: str) -> dict[str, float | int]:
    values = [float(row[column]) for row in rows]
    return {
        "trades": len(values),
        "net": sum(values),
        "profit_factor": pf(values),
        "expectancy": sum(values) / len(values),
        "max_drawdown_pct": drawdown(values),
    }


def read_role(path: Path, expected_role: str) -> tuple[list[dict[str, str]], dict[str, int]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    statuses: dict[str, int] = {}
    for row in rows:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
        if row["role"] != expected_role:
            raise ValueError(f"role mismatch in {path}")
    allowed = {"CLOSED", "SKIP_ZERO", "SKIP_MISSED_TICK", "SKIP_OVERLAP", "ENTRY_REJECT"}
    if (
        len(rows) != 329
        or not set(statuses).issubset(allowed)
        or statuses.get("SKIP_ZERO", 0) != 11
        or sum(statuses.values()) != 329
    ):
        raise ValueError(f"event accounting mismatch in {path}: rows={len(rows)} statuses={statuses}")
    closed = [row for row in rows if row["status"] == "CLOSED"]
    if any(int(row["entry_tick_msc"]) < int(row["entry_target_msc"]) for row in closed):
        raise ValueError(f"pre-boundary entry in {path}")
    if any(int(row["exit_tick_msc"]) < int(row["exit_target_msc"]) for row in closed):
        raise ValueError(f"pre-boundary exit in {path}")
    if any(float(row["lots"]) <= 0 or float(row["lots"]) > 1.0 for row in closed):
        raise ValueError(f"invalid lot in {path}")
    for row in closed:
        lots = float(row["lots"])
        raw = float(row["raw_mid_pnl_usd"])
        executable = float(row["executable_pnl_usd"])
        commission = float(row["commission_usd"])
        dynamic_pips = float(row["dynamic_slippage_pips"])
        pip_value = float(row["pip_value_per_lot"])
        entry_spread = float(row["entry_spread_pips"])
        prior_median = float(row["prior_10_entry_spread_median_pips"])
        complete_cost = float(row["complete_cost_usd"])
        expected_commission = 4.0 * lots
        expected_dynamic_pips = max(0.0, entry_spread - prior_median)
        expected_complete = raw - executable + expected_commission + expected_dynamic_pips * pip_value * lots
        if not close_enough(dynamic_pips, expected_dynamic_pips):
            raise ValueError(f"dynamic slippage mismatch in {path}: {row['event_id']}")
        if not close_enough(commission, expected_commission):
            raise ValueError(f"commission mismatch in {path}: {row['event_id']}")
        if not close_enough(complete_cost, expected_complete):
            raise ValueError(f"complete cost mismatch in {path}: {row['event_id']}")
        if not close_enough(float(row["net_base_usd"]), raw - complete_cost):
            raise ValueError(f"base net mismatch in {path}: {row['event_id']}")
        if not close_enough(float(row["net_x1_5_usd"]), raw - 1.5 * complete_cost):
            raise ValueError(f"1.5x net mismatch in {path}: {row['event_id']}")
        if not close_enough(float(row["net_x2_usd"]), raw - 2.0 * complete_cost):
            raise ValueError(f"2x net mismatch in {path}: {row['event_id']}")
    return closed, statuses


def role_summary(path: Path, role: str) -> dict[str, object]:
    rows, statuses = read_role(path, role)
    years: dict[str, float] = {}
    for row in rows:
        year = str(datetime.fromtimestamp(int(row["event_utc_msc"]) / 1000, tz=timezone.utc).year)
        years[year] = years.get(year, 0.0) + float(row["net_base_usd"])
    base_values = [float(row["net_base_usd"]) for row in rows]
    positive_total = sum(value for value in base_values if value > 0)
    top_count = math.ceil(len(base_values) * 0.05)
    positive_values = sorted((value for value in base_values if value > 0), reverse=True)
    top_share = (
        sum(positive_values[:top_count]) / positive_total
        if positive_total > 0 else math.inf
    )
    excluded = [row for row in rows if row["event_id"] not in DEGRADED]
    return {
        "role": role,
        "ledger_path": str(path.resolve()),
        "ledger_sha256": sha256(path),
        "status_counts": statuses,
        "base": arm(rows, "net_base_usd"),
        "cost_x1_5": arm(rows, "net_x1_5_usd"),
        "cost_x2": arm(rows, "net_x2_usd"),
        "year_base_net": years,
        "top_5pct": {"count": top_count, "gross_profit_share": top_share},
        "degraded_cells": [
            {key: row[key] for key in ("event_id", "source_direction", "direction", "net_base_usd")}
            for row in rows
            if row["event_id"] in DEGRADED
        ],
        "degraded_exclusion_diagnostic": {
            "rescue_authorized": False,
            "base": arm(excluded, "net_base_usd"),
            "cost_x1_5": arm(excluded, "net_x1_5_usd"),
            "cost_x2": arm(excluded, "net_x2_usd"),
        },
    }


def validate_meta(path: Path, role: str) -> dict[str, object]:
    meta = json.loads(path.read_text(encoding="utf-8"))
    if (
        meta.get("role") != role
        or meta.get("source_sha256") != EXPECTED_SOURCE_HASH
        or meta.get("table_sha256") != EXPECTED_TABLE_HASH
        or meta.get("events") != 329
        or meta.get("accounted") != 329
        or meta.get("zero_source") != 11
        or meta.get("runtime_failed") is not False
        or meta.get("max_concurrent") != 1
    ):
        raise ValueError(f"invalid run meta: {path}")
    return {"path": str(path.resolve()), "sha256": sha256(path), "payload": meta}


def validate_exact_reverse(primary_path: Path, reverse_path: Path) -> None:
    with primary_path.open("r", encoding="utf-8-sig", newline="") as handle:
        primary = list(csv.DictReader(handle))
    with reverse_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reverse = list(csv.DictReader(handle))
    if len(primary) != 329 or len(reverse) != 329:
        raise ValueError("PRIMARY/REVERSE must each account for 329 events")
    fields = ("event_id", "event_utc_msc", "event_server_msc", "source_direction",
              "entry_target_msc", "exit_target_msc", "status")
    for left, right in zip(primary, reverse):
        if any(left[field] != right[field] for field in fields):
            raise ValueError(f"PRIMARY/REVERSE identity mismatch: {left.get('event_id')}")
        source_direction = int(left["source_direction"])
        if int(left["direction"]) != source_direction or int(right["direction"]) != -source_direction:
            raise ValueError(f"PRIMARY/REVERSE sign mismatch: {left['event_id']}")
        if left["entry_tick_msc"] != right["entry_tick_msc"] or left["exit_tick_msc"] != right["exit_tick_msc"]:
            raise ValueError(f"PRIMARY/REVERSE tick-boundary mismatch: {left['event_id']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--primary-meta", type=Path, required=True)
    parser.add_argument("--reverse", type=Path, required=True)
    parser.add_argument("--reverse-meta", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    validate_exact_reverse(args.primary, args.reverse)
    primary = role_summary(args.primary, "PRIMARY")
    reverse = role_summary(args.reverse, "REVERSE")
    gates = {
        "trades_at_least_300": primary["base"]["trades"] >= 300,
        "cadence_2_5_to_5_per_week": 2.5 <= primary["base"]["trades"] / (731 / 7) <= 5.0,
        "base_pf_at_least_1_30": primary["base"]["profit_factor"] >= 1.30,
        "base_expectancy_positive": primary["base"]["expectancy"] > 0,
        "cost_x1_5_pf_at_least_1_25": primary["cost_x1_5"]["profit_factor"] >= 1.25,
        "cost_x2_pf_at_least_1_00": primary["cost_x2"]["profit_factor"] >= 1.0,
        "cost_x2_expectancy_nonnegative": primary["cost_x2"]["expectancy"] >= 0,
        "both_years_positive": set(primary["year_base_net"]) == {"2019", "2020"}
        and all(value > 0 for value in primary["year_base_net"].values()),
        "base_drawdown_at_most_8pct": primary["base"]["max_drawdown_pct"] <= 8.0,
        "reverse_base_pf_inferior": reverse["base"]["profit_factor"] < primary["base"]["profit_factor"],
        "top_5pct_share_at_most_30pct": primary["top_5pct"]["gross_profit_share"] <= 0.30,
    }
    primary_meta = validate_meta(args.primary_meta, "PRIMARY")
    reverse_meta = validate_meta(args.reverse_meta, "REVERSE")
    if (
        primary_meta["payload"].get("completed") != primary["base"]["trades"]
        or reverse_meta["payload"].get("completed") != reverse["base"]["trades"]
    ):
        raise ValueError("run-meta completed count does not match audit ledger")
    payload = {
        "schema_version": "event_depth_transfer_009_economic_analysis.v1",
        "hypothesis_id": "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-009",
        "source_sha256": EXPECTED_SOURCE_HASH,
        "table_sha256": EXPECTED_TABLE_HASH,
        "primary_meta": primary_meta,
        "reverse_meta": reverse_meta,
        "primary": primary,
        "reverse": reverse,
        "gates": gates,
        "passed_all_gates": all(gates.values()),
        "verdict": "PASS_ALL_FROZEN_DESIGN_GATES" if all(gates.values()) else "KILL_FROZEN_MAPPING",
        "failed_gates": [name for name, passed in gates.items() if not passed],
        "validation_open_authorized": all(gates.values()),
        "optimization_authorized": False,
        "rerun_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": payload["verdict"], "failed_gates": payload["failed_gates"]}))


if __name__ == "__main__":
    main()





