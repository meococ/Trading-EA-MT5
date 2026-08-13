#!/usr/bin/env python3
"""Analyze hash-bound XBTMM virtual fills after explicit economic authority.

The engine is virtual because native MT5 fills cannot enforce strict
trade-through.  This analyzer reconstructs FIFO holding time and daily XBT NAV
from the emitted fills, and refuses to run without a task packet that explicitly
authorizes economics.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


STARTING_NAV_XBT = 1.0
REFERENCE_RISK_CAPITAL_USD = 400.0
CAPITAL_CONTRACT = {
    "reference_risk_capital_usd": REFERENCE_RISK_CAPITAL_USD,
    "min_base_annualized_return": 0.15,
    "stress_taker_fee_bps": 15.0,
    "min_stress_annualized_return_exclusive": 0.0,
    "daily_max_drawdown_pct": 12.0,
    "max_recovery_calendar_days": 45,
    "intraday_v5_required_if_design_survives": True,
}
ENGINES = ("candidate", "matched_null")
SUMMARY_RE = re.compile(r"XBTMM_ENGINE_SUMMARY .*?engine=(candidate|matched_null) (.*)")
FIELD_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")


@dataclass
class Lot:
    side: int
    quantity: int
    open_us: int


def parse_day_token(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def utc_day_from_us(time_us: int) -> date:
    return datetime.fromtimestamp(time_us / 1_000_000, tz=timezone.utc).date()


def pf(values: list[float]) -> float:
    profit = sum(value for value in values if value > 0.0)
    loss = -sum(value for value in values if value < 0.0)
    return profit / loss if loss > 0.0 else (math.inf if profit > 0.0 else 0.0)


def load_days(index_path: Path) -> list[date]:
    with index_path.open("r", encoding="ascii", newline="") as handle:
        rows = list(csv.DictReader(handle))
    days = [parse_day_token(row["utc_day"]) for row in rows]
    if not days:
        raise ValueError("empty DESIGN index")
    expected = [days[0] + timedelta(days=offset) for offset in range(len(days))]
    if days != expected:
        raise ValueError("DESIGN index is not contiguous")
    return days


def load_authority(task_path: Path) -> dict:
    task = json.loads(task_path.read_text(encoding="utf-8"))
    if task.get("hypothesis_id") != "HYP-XBT-MM-TRADETHROUGH-004":
        raise ValueError("wrong economic task hypothesis")
    if task.get("economics_authorized") is not True:
        raise PermissionError("task does not authorize economics")
    if task.get("performance_metrics_authorized") is not True:
        raise PermissionError("task does not authorize performance metrics")
    if task.get("holdout_access_authorized") is not False:
        raise PermissionError("DESIGN analyzer cannot carry holdout authority")
    if task.get("capital_contract") != CAPITAL_CONTRACT:
        raise PermissionError("task does not bind the frozen outcome-blind capital contract")
    return task


def parse_engine_summaries(journal_path: Path) -> dict[str, dict[str, str]]:
    summaries: dict[str, dict[str, str]] = {}
    for line in journal_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SUMMARY_RE.search(line)
        if not match:
            continue
        engine = match.group(1)
        fields = dict(FIELD_RE.findall(match.group(2)))
        summaries[engine] = fields
    if set(summaries) != set(ENGINES):
        raise ValueError("journal lacks both complete engine summaries")
    return summaries


def nav_metrics(days: list[date], day_values: list[float], starting_nav: float) -> dict:
    nav = starting_nav
    peak = nav
    peak_day = days[0]
    max_dd_pct = 0.0
    max_dd_peak_day = days[0]
    max_dd_trough_day = days[0]
    peak_nav_at_max_dd = peak
    nav_by_day: list[tuple[date, float]] = []
    for day, pnl in zip(days, day_values, strict=True):
        nav += pnl
        nav_by_day.append((day, nav))
        if nav > peak:
            peak = nav
            peak_day = day
        drawdown = 100.0 * (peak - nav) / peak if peak > 0.0 else math.inf
        if drawdown > max_dd_pct:
            max_dd_pct = drawdown
            max_dd_peak_day = peak_day
            max_dd_trough_day = day
            peak_nav_at_max_dd = peak
    if max_dd_pct == 0.0:
        recovery_day = max_dd_trough_day
        recovery_days = 0
    else:
        recovery_day = next(
            (
                day
                for day, value in nav_by_day
                if day > max_dd_trough_day and value >= peak_nav_at_max_dd
            ),
            None,
        )
        recovery_days = (recovery_day - max_dd_trough_day).days if recovery_day else None
    return {
        "max_dd_pct": max_dd_pct,
        "max_dd_peak_day": max_dd_peak_day,
        "max_dd_trough_day": max_dd_trough_day,
        "recovery_day": recovery_day,
        "recovery_days": recovery_days,
        "final_nav": nav,
    }


def analyze_engine(rows: list[dict[str, str]], days: list[date], journal: dict[str, str]) -> dict:
    lots: deque[Lot] = deque()
    daily_pnl_xbt: dict[date, float] = defaultdict(float)
    daily_pnl_usd: dict[date, float] = defaultdict(float)
    daily_maker_fills: dict[date, int] = defaultdict(int)
    holding_quantity = 0
    holding_us_quantity = 0
    realized_values_xbt: list[float] = []
    realized_values_usd: list[float] = []
    fee_values_usd: list[float] = []
    inventory_violations = 0

    for row in rows:
        time_us = int(row["time_us"])
        side = 1 if row["side"] == "BUY" else -1
        quantity = int(row["quantity"])
        price = float(row["price"])
        realized = float(row["realized_delta_xbt"])
        fee = float(row["fee_xbt"])
        realized_usd = realized * price
        fee_usd = fee * price
        remaining = quantity
        while remaining > 0 and lots and lots[0].side != side:
            closed = min(remaining, lots[0].quantity)
            holding_quantity += closed
            holding_us_quantity += closed * (time_us - lots[0].open_us)
            lots[0].quantity -= closed
            remaining -= closed
            if lots[0].quantity == 0:
                lots.popleft()
        if remaining:
            lots.append(Lot(side=side, quantity=remaining, open_us=time_us))
        reconstructed = sum(lot.side * lot.quantity for lot in lots)
        if reconstructed != int(row["inventory"]):
            inventory_violations += 1
        day = utc_day_from_us(time_us)
        daily_pnl_xbt[day] += realized
        daily_pnl_usd[day] += realized_usd
        if row["type"] == "MAKER_FILL":
            daily_maker_fills[day] += 1
        realized_values_xbt.append(realized)
        realized_values_usd.append(realized_usd)
        fee_values_usd.append(fee_usd)

    if lots:
        raise ValueError("fill ledger ends with open FIFO inventory")
    if inventory_violations:
        raise ValueError(f"fill ledger inventory mismatches: {inventory_violations}")

    day_values_xbt = [daily_pnl_xbt.get(day, 0.0) for day in days]
    day_values_usd = [daily_pnl_usd.get(day, 0.0) for day in days]
    xbt_nav = nav_metrics(days, day_values_xbt, STARTING_NAV_XBT)
    capital_nav = nav_metrics(days, day_values_usd, REFERENCE_RISK_CAPITAL_USD)

    positive_days = sorted((value for value in day_values_usd if value > 0.0), reverse=True)
    top_count = max(1, math.ceil(0.05 * len(days)))
    positive_total = sum(positive_days)
    concentration = (
        sum(positive_days[:top_count]) / positive_total if positive_total > 0.0 else math.inf
    )
    stressed_pf = {
        str(multiplier): pf(
            [
                value - (multiplier - 1.0) * fee
                for value, fee in zip(realized_values_usd, fee_values_usd, strict=True)
            ]
        )
        for multiplier in (1.0, 1.5, 2.0)
    }
    stressed_net_usd = {
        str(multiplier): sum(
            value - (multiplier - 1.0) * fee
            for value, fee in zip(realized_values_usd, fee_values_usd, strict=True)
        )
        for multiplier in (1.0, 1.5, 2.0)
    }
    design_years = len(days) / 365.25
    annualized_returns = {
        multiplier: value / REFERENCE_RISK_CAPITAL_USD / design_years
        for multiplier, value in stressed_net_usd.items()
    }
    by_year: dict[str, dict[str, float | int]] = {}
    for year in sorted({day.year for day in days}):
        year_days = [day for day in days if day.year == year]
        fills = sum(daily_maker_fills.get(day, 0) for day in year_days)
        filled_days = sum(daily_maker_fills.get(day, 0) > 0 for day in year_days)
        by_year[str(year)] = {
            "maker_fills": fills,
            "calendar_days": len(year_days),
            "filled_days": filled_days,
            "filled_day_ratio": filled_days / len(year_days),
        }

    intraday_xbt_dd = float(journal["max_dd_xbt_pct"])
    maker_fill_count = sum(daily_maker_fills.values())
    return {
        "rows": len(rows),
        "maker_fills": maker_fill_count,
        "net_pnl_xbt": sum(realized_values_xbt),
        "net_pnl_usd": sum(realized_values_usd),
        "average_daily_pnl_xbt": sum(day_values_xbt) / len(days),
        "average_daily_pnl_usd": sum(day_values_usd) / len(days),
        "average_pnl_per_maker_contract_usd": (
            sum(realized_values_usd) / (100 * maker_fill_count)
            if maker_fill_count
            else 0.0
        ),
        "pf": stressed_pf["1.0"],
        "pf_x1_5": stressed_pf["1.5"],
        "pf_x2": stressed_pf["2.0"],
        "reference_risk_capital_usd": REFERENCE_RISK_CAPITAL_USD,
        "annualized_return_on_risk_capital": annualized_returns["1.0"],
        "annualized_return_on_risk_capital_x1_5": annualized_returns["1.5"],
        "annualized_return_on_risk_capital_x2": annualized_returns["2.0"],
        "daily_capital_max_dd_pct": capital_nav["max_dd_pct"],
        "xbt_nav_daily_max_dd_pct": xbt_nav["max_dd_pct"],
        "xbt_nav_intraday_max_dd_pct": intraday_xbt_dd,
        "max_dd_peak_day": capital_nav["max_dd_peak_day"].isoformat(),
        "max_dd_trough_day": capital_nav["max_dd_trough_day"].isoformat(),
        "recovery_day": (
            capital_nav["recovery_day"].isoformat() if capital_nav["recovery_day"] else None
        ),
        "recovery_days": capital_nav["recovery_days"],
        "top_5pct_days_positive_pnl_share": concentration,
        "average_holding_minutes": (
            holding_us_quantity / holding_quantity / 60_000_000 if holding_quantity else math.inf
        ),
        "by_year": by_year,
        "final_inventory": int(journal["inventory"]),
        "engineering_gate_pass": journal["engineering_gate_pass"].lower() == "true",
    }


def evaluate(candidate: dict, null: dict) -> dict[str, bool]:
    year_power = all(
        year["maker_fills"] >= 1800 and year["filled_day_ratio"] >= 0.60
        for year in candidate["by_year"].values()
    )
    recovery_ok = candidate["recovery_days"] is not None and candidate["recovery_days"] <= 45
    return {
        "engineering": candidate["engineering_gate_pass"] and null["engineering_gate_pass"],
        "year_power_and_coverage": year_power,
        "base_pf": candidate["pf"] >= 1.30,
        "positive_per_contract": candidate["average_pnl_per_maker_contract_usd"] > 0.0,
        "positive_net": candidate["net_pnl_usd"] > 0.0,
        "capital_efficiency": candidate["annualized_return_on_risk_capital"] >= 0.15,
        "capital_efficiency_x2": candidate["annualized_return_on_risk_capital_x2"] > 0.0,
        "stress_x1_5": candidate["pf_x1_5"] >= 1.10,
        "stress_x2": candidate["pf_x2"] >= 1.00,
        "daily_capital_drawdown": candidate["daily_capital_max_dd_pct"] <= 12.0,
        "recovery": recovery_ok,
        "concentration": candidate["top_5pct_days_positive_pnl_share"] <= 0.25,
        "holding_time": candidate["average_holding_minutes"] <= 12.0,
        "beats_null_pf": candidate["pf"] > null["pf"],
        "beats_null_daily_pnl": candidate["average_daily_pnl_usd"] > null["average_daily_pnl_usd"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fills", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    task = load_authority(args.task)
    days = load_days(args.index)
    if days[0] != date(2018, 1, 1) or days[-1] != date(2021, 12, 31) or len(days) != 1461:
        raise ValueError("economics require the exact 1,461-day DESIGN population")
    summaries = parse_engine_summaries(args.journal)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with args.fills.open("r", encoding="ascii", newline="") as handle:
        for row in csv.DictReader(handle):
            grouped[row["engine"]].append(row)
    if set(grouped) != set(ENGINES):
        raise ValueError("fill ledger lacks candidate or matched null")
    results = {engine: analyze_engine(grouped[engine], days, summaries[engine]) for engine in ENGINES}
    gates = evaluate(results["candidate"], results["matched_null"])
    payload = {
        "schema_version": "xbtmm_design_economic_report.v2",
        "hypothesis_id": "HYP-XBT-MM-TRADETHROUGH-004",
        "authority_task": str(args.task.resolve()),
        "authority": task["authority"],
        "population": {"from": days[0].isoformat(), "to": days[-1].isoformat(), "days": len(days)},
        "capital_contract": CAPITAL_CONTRACT,
        "engines": results,
        "gates": gates,
        "verdict": (
            "PASS_DESIGN_REQUIRES_V5_INTRADAY_RISK" if all(gates.values()) else "KILL_DESIGN"
        ),
        "promotion_precondition": (
            "A DESIGN survivor requires a metrics-only V5 replay with exact intraday "
            "USD-equivalent mark-to-market drawdown; signal and fill logic stay frozen."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, allow_nan=False))
    return 0 if payload["verdict"].startswith("PASS_DESIGN") else 2


if __name__ == "__main__":
    raise SystemExit(main())
