#!/usr/bin/env python3
"""Simulate Sonic R pre-entry risk routing from forensic rule candidates."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


INVALID_ENTRY_FIELDS = {
    "exit_reason",
    "close_source",
    "hold_minutes",
    "realized_r",
    "pnl_net",
    "is_win",
    "is_loss",
    "entry_year",
    "entry_month",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--rules-csv", type=Path)
    parser.add_argument("--multipliers", default="0.25,0.50,0.75")
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--out-csv", type=Path)
    return parser.parse_args()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def stats(values: list[float]) -> dict[str, Any]:
    wins = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    return {
        "n": len(values),
        "net": round(sum(values), 6),
        "pf": round(wins / losses if losses else (999.99 if wins else 0.0), 6),
        "win_rate": round(sum(1 for value in values if value > 0) / len(values), 6) if values else 0.0,
        "expectancy": round(sum(values) / len(values), 6) if values else 0.0,
    }


def load_joined(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "analysis" / "sonic_trade_state_joined.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    rows: list[dict[str, Any]] = []
    for row in read_csv_rows(path):
        converted: dict[str, Any] = dict(row)
        for key, value in row.items():
            if re.search(r"(score|atr|pips|ratio|points|minutes|pnl|realized)", key):
                converted[key] = safe_float(value)
        converted["pnl_net"] = safe_float(row.get("pnl_net"))
        rows.append(converted)
    return rows


def parse_atomic(expr: str) -> Callable[[dict[str, Any]], bool] | None:
    expr = expr.strip()
    match = re.match(r"^([A-Za-z0-9_]+)\s*==\s*(.+)$", expr)
    if match:
        field, value = match.group(1), match.group(2)
        if field in INVALID_ENTRY_FIELDS:
            return None
        return lambda row, f=field, v=value: str(row.get(f, "")) == v
    match = re.match(r"^([A-Za-z0-9_]+)\s*(<=|>=)\s*(-?[0-9.]+)$", expr)
    if match:
        field, op, raw_value = match.group(1), match.group(2), float(match.group(3))
        if field in INVALID_ENTRY_FIELDS:
            return None
        if op == "<=":
            return lambda row, f=field, v=raw_value: safe_float(row.get(f)) <= v
        return lambda row, f=field, v=raw_value: safe_float(row.get(f)) >= v
    return None


def parse_rule(expr: str) -> Callable[[dict[str, Any]], bool] | None:
    parts = [part.strip() for part in expr.split(" AND ")]
    predicates = []
    for part in parts:
        predicate = parse_atomic(part)
        if predicate is None:
            return None
        predicates.append(predicate)
    return lambda row, preds=predicates: all(predicate(row) for predicate in preds)


def simulate(rows: list[dict[str, Any]], rule_rows: list[dict[str, str]], multipliers: list[float]) -> list[dict[str, Any]]:
    base = stats([float(row["pnl_net"]) for row in rows])
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for rule_row in rule_rows:
        rule = rule_row.get("rule", "")
        predicate = parse_rule(rule)
        if predicate is None:
            continue
        affected = [row for row in rows if predicate(row)]
        if not affected:
            continue
        affected_stats = stats([float(row["pnl_net"]) for row in affected])
        if affected_stats["net"] >= 0:
            continue
        for multiplier in multipliers:
            key = (rule, multiplier)
            if key in seen:
                continue
            seen.add(key)
            pnls = [float(row["pnl_net"]) * (multiplier if predicate(row) else 1.0) for row in rows]
            simulated = stats(pnls)
            out.append(
                {
                    "rule": rule,
                    "risk_multiplier": multiplier,
                    "affected_n": affected_stats["n"],
                    "affected_net": affected_stats["net"],
                    "affected_pf": affected_stats["pf"],
                    "base_net": base["net"],
                    "base_pf": base["pf"],
                    "sim_net": simulated["net"],
                    "sim_pf": simulated["pf"],
                    "delta_net": round(simulated["net"] - base["net"], 6),
                    "delta_pf": round(simulated["pf"] - base["pf"], 6),
                }
            )
    return sorted(out, key=lambda row: (row["delta_pf"], row["delta_net"]), reverse=True)


def write_md(path: Path, rows: list[dict[str, Any]], top: int) -> None:
    fields = ["rule", "risk_multiplier", "affected_n", "affected_net", "sim_net", "sim_pf", "delta_net", "delta_pf"]
    lines = [
        "# Sonic Risk Router Simulation",
        "",
        "- Research-only report-only scaling simulation.",
        "- It assumes PnL scales linearly with risk; it is not a replacement for MT5 rerun.",
        "- Outcome/future/time-split fields are excluded from entry-rule simulation.",
        "",
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows[:top]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = load_joined(args.run_dir)
    rules_csv = args.rules_csv or args.run_dir / "analysis" / "sonic_trade_forensics_rules.csv"
    rule_rows = read_csv_rows(rules_csv)
    multipliers = [float(value.strip()) for value in args.multipliers.split(",") if value.strip()]
    results = simulate(rows, rule_rows, multipliers)
    out_json = args.out_json or args.run_dir / "analysis" / "sonic_risk_router_sim.json"
    out_md = args.out_md or args.run_dir / "analysis" / "sonic_risk_router_sim.md"
    out_csv = args.out_csv or args.run_dir / "analysis" / "sonic_risk_router_sim.csv"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"schema_version": "sonic_risk_router_sim.v1", "run_id": args.run_dir.name, "results": results}, indent=2), encoding="utf-8")
    write_md(out_md, results, args.top)
    write_csv(out_csv, results)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
