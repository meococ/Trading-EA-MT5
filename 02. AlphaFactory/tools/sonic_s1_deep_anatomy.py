#!/usr/bin/env python3
"""
Sonic R XAU S1 deep anatomy.

Joins XAU_S1_SWEEP_RECLAIM Opportunities with final Trades, then reports
cost-adjusted bucket stability. This is research-only attribution; it does not
mutate EA behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


S1_SETUP = "XAU_S1_SWEEP_RECLAIM"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deep S1 bucket anatomy from Sonic opportunities/trades.")
    parser.add_argument("--run-dir", required=True, help="AlphaFactory run directory.")
    parser.add_argument("--cost", type=float, default=0.50, help="Report-only cost per trade.")
    parser.add_argument("--min-n", type=int, default=15, help="Minimum bucket trades for keep buckets.")
    parser.add_argument("--min-kept", type=int, default=80, help="Minimum kept trades for remove tests.")
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    parser.add_argument("--out-csv")
    return parser.parse_args()


def run_id_from_dir(run_dir: Path) -> str:
    return run_dir.name


def find_one(logs_dir: Path, pattern: str) -> Path:
    files = sorted(logs_dir.glob(pattern))
    files = [p for p in files if "PX6" not in p.name]
    if not files:
        raise FileNotFoundError(f"Missing {pattern} under {logs_dir}")
    return files[0]


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")
    except Exception:
        return None


def split_label(ts: str) -> str:
    dt = parse_dt(ts)
    if dt is None:
        return "UNKNOWN"
    half = "H1" if dt.month <= 6 else "H2"
    return f"{dt.year}{half}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


@dataclass
class Metrics:
    n: int
    net: float
    pf: float | None
    cost_net: float
    cost_pf: float | None
    win_rate: float
    avg_r: float
    tp: int
    sl: int
    manual: int
    splits: dict[str, dict[str, Any]]
    stable_splits: int
    weak_splits: int
    min_split_cost_pf: float | None


def profit_factor(values: list[float]) -> float | None:
    gross_profit = sum(v for v in values if v > 0)
    gross_loss = -sum(v for v in values if v < 0)
    if gross_loss <= 0:
        return None if gross_profit <= 0 else 999.99
    return gross_profit / gross_loss


def calc_metrics(rows: list[dict[str, Any]], cost: float) -> Metrics:
    pnls = [to_float(r.get("pnl_net")) for r in rows]
    cost_pnls = [p - cost for p in pnls]
    realized = [to_float(r.get("realized_r")) for r in rows]
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_split[row.get("split", "UNKNOWN")].append(row)

    split_metrics: dict[str, dict[str, Any]] = {}
    stable = 0
    weak = 0
    min_cost_pf: float | None = None
    for split, split_rows in sorted(by_split.items()):
        vals = [to_float(r.get("pnl_net")) for r in split_rows]
        cvals = [v - cost for v in vals]
        cpf = profit_factor(cvals)
        net = sum(vals)
        cnet = sum(cvals)
        if cpf is not None:
            min_cost_pf = cpf if min_cost_pf is None else min(min_cost_pf, cpf)
        if cnet > 0:
            stable += 1
        else:
            weak += 1
        split_metrics[split] = {
            "n": len(split_rows),
            "net": round(net, 4),
            "pf": pf_round(profit_factor(vals)),
            "cost_net": round(cnet, 4),
            "cost_pf": pf_round(cpf),
        }

    return Metrics(
        n=len(rows),
        net=round(sum(pnls), 4),
        pf=profit_factor(pnls),
        cost_net=round(sum(cost_pnls), 4),
        cost_pf=profit_factor(cost_pnls),
        win_rate=round(100.0 * sum(1 for p in pnls if p > 0) / len(rows), 4) if rows else 0.0,
        avg_r=round(sum(realized) / len(realized), 6) if realized else 0.0,
        tp=sum(1 for r in rows if str(r.get("exit_reason", "")).lower() == "tp"),
        sl=sum(1 for r in rows if str(r.get("exit_reason", "")).lower() == "sl"),
        manual=sum(1 for r in rows if str(r.get("exit_reason", "")).lower() not in {"tp", "sl"}),
        splits=split_metrics,
        stable_splits=stable,
        weak_splits=weak,
        min_split_cost_pf=min_cost_pf,
    )


def pf_round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def metrics_dict(metrics: Metrics) -> dict[str, Any]:
    return {
        "n": metrics.n,
        "net": metrics.net,
        "pf": pf_round(metrics.pf),
        "cost_net": metrics.cost_net,
        "cost_pf": pf_round(metrics.cost_pf),
        "win_rate_pct": metrics.win_rate,
        "avg_r": metrics.avg_r,
        "tp": metrics.tp,
        "sl": metrics.sl,
        "manual": metrics.manual,
        "stable_splits": metrics.stable_splits,
        "weak_splits": metrics.weak_splits,
        "min_split_cost_pf": pf_round(metrics.min_split_cost_pf),
        "splits": metrics.splits,
    }


def bucket_value(row: dict[str, Any], field: str) -> str:
    if field == "target_rr_bin":
        v = to_float(row.get("target_rr"))
        if v < 1.20:
            return "<1.20"
        if v < 1.60:
            return "1.20-1.59"
        if v < 2.20:
            return "1.60-2.19"
        return ">=2.20"
    if field == "risk_points_bin":
        v = to_float(row.get("risk_points"))
        if v < 150:
            return "<150"
        if v < 250:
            return "150-249"
        if v < 400:
            return "250-399"
        return ">=400"
    if field == "level_distance_bin":
        v = abs(to_float(row.get("level_distance_pips")))
        if v < 1:
            return "<1"
        if v < 3:
            return "1-3"
        if v < 6:
            return "3-6"
        return ">=6"
    if field == "score_bin":
        v = to_float(row.get("scalp_opportunity_score"))
        if v < 40:
            return "<40"
        if v < 50:
            return "40-49"
        if v < 60:
            return "50-59"
        return ">=60"
    if field == "trend_relation":
        h1 = to_int(row.get("h1_bias"))
        h4 = to_int(row.get("h4_bias"))
        if h1 < 0 and h4 < 0:
            return "H1H4_BEAR"
        if h1 > 0 and h4 > 0:
            return "H1H4_BULL"
        if h1 < 0 or h4 < 0:
            return "MIXED_BEAR"
        if h1 > 0 or h4 > 0:
            return "MIXED_BULL"
        return "NEUTRAL"
    value = str(row.get(field, "") or "NONE")
    return value if value != "" else "NONE"


def group_rows(rows: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[bucket_value(row, field)].append(row)
    return groups


def field_candidates(
    rows: list[dict[str, Any]],
    fields: list[str],
    cost: float,
    min_n: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for field in fields:
        for bucket, bucket_rows in group_rows(rows, field).items():
            if len(bucket_rows) < min_n:
                continue
            m = calc_metrics(bucket_rows, cost)
            out.append({
                "kind": "keep_bucket",
                "field": field,
                "bucket": bucket,
                **metrics_dict(m),
            })
    out.sort(key=lambda x: (to_float(x.get("cost_pf"), -999), to_float(x.get("cost_net")), x.get("n", 0)), reverse=True)
    return out


def remove_candidates(
    rows: list[dict[str, Any]],
    fields: list[str],
    cost: float,
    min_kept: int,
    baseline: Metrics,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    baseline_cost_pf = baseline.cost_pf or 0.0
    for field in fields:
        groups = group_rows(rows, field)
        for bucket, bucket_rows in groups.items():
            kept = [r for r in rows if bucket_value(r, field) != bucket]
            if len(kept) < min_kept:
                continue
            m = calc_metrics(kept, cost)
            removed = calc_metrics(bucket_rows, cost)
            cost_pf = m.cost_pf or 0.0
            out.append({
                "kind": "remove_bucket",
                "field": field,
                "bucket": bucket,
                "removed_n": len(bucket_rows),
                "removed_cost_net": removed.cost_net,
                "removed_cost_pf": pf_round(removed.cost_pf),
                "delta_cost_pf": round(cost_pf - baseline_cost_pf, 6),
                **metrics_dict(m),
            })
    out.sort(key=lambda x: (to_float(x.get("delta_cost_pf")), to_float(x.get("cost_net")), x.get("n", 0)), reverse=True)
    return out


def pair_candidates(
    rows: list[dict[str, Any]],
    pairs: list[tuple[str, str]],
    cost: float,
    min_n: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a, b in pairs:
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[(bucket_value(row, a), bucket_value(row, b))].append(row)
        for (av, bv), bucket_rows in groups.items():
            if len(bucket_rows) < min_n:
                continue
            m = calc_metrics(bucket_rows, cost)
            out.append({
                "kind": "keep_pair",
                "field": f"{a}+{b}",
                "bucket": f"{av}|{bv}",
                **metrics_dict(m),
            })
    out.sort(key=lambda x: (to_float(x.get("cost_pf"), -999), to_float(x.get("cost_net")), x.get("n", 0)), reverse=True)
    return out


def join_s1_rows(opportunity_rows: list[dict[str, str]], trade_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trades_by_key: dict[tuple[str, str], deque[dict[str, str]]] = defaultdict(deque)
    for trade in trade_rows:
        if trade.get("engine_variant") != S1_SETUP:
            continue
        if str(trade.get("is_final_close", "1")) not in {"1", "true", "True"}:
            continue
        key = (trade.get("entry_server_ts", ""), trade.get("direction", ""))
        trades_by_key[key].append(trade)

    joined: list[dict[str, Any]] = []
    unmatched_opportunities = 0
    fired = 0
    for opp in opportunity_rows:
        if opp.get("setup_type") != S1_SETUP or opp.get("outcome") != "FIRED":
            continue
        fired += 1
        key = (opp.get("server_ts", ""), opp.get("direction", ""))
        if not trades_by_key[key]:
            unmatched_opportunities += 1
            continue
        trade = trades_by_key[key].popleft()
        row: dict[str, Any] = {}
        row.update(opp)
        for k, v in trade.items():
            row[f"trade_{k}"] = v
        row["entry_server_ts"] = trade.get("entry_server_ts", opp.get("server_ts", ""))
        row["exit_reason"] = trade.get("exit_reason", "")
        row["pnl_net"] = to_float(trade.get("pnl_net"))
        row["realized_r"] = to_float(trade.get("realized_r"))
        row["split"] = split_label(str(row["entry_server_ts"]))
        joined.append(row)

    unmatched_trades = sum(len(q) for q in trades_by_key.values())
    return joined, {
        "s1_fired_opportunities": fired,
        "joined_rows": len(joined),
        "unmatched_opportunities": unmatched_opportunities,
        "unmatched_trades": unmatched_trades,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    excluded = {"splits"}
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key in excluded:
                continue
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def md_table(rows: list[dict[str, Any]], columns: list[str], limit: int) -> list[str]:
    shown = rows[:limit]
    if not shown:
        return ["_No rows._"]
    out = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in shown:
        values = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                value = round(value, 4)
            values.append(str(value))
        out.append("| " + " | ".join(values) + " |")
    return out


def write_md(path: Path, payload: dict[str, Any], top: int) -> None:
    lines: list[str] = []
    lines.append(f"# Sonic S1 Deep Anatomy - {payload['run_id']}")
    lines.append("")
    lines.append("## Overall")
    overall = payload["overall"]
    lines.append(f"- Joined S1 trades: `{overall['n']}`")
    lines.append(f"- Base net/PF: `{overall['net']}` / `{overall['pf']}`")
    lines.append(f"- Cost net/PF at `{payload['cost_per_trade']}`: `{overall['cost_net']}` / `{overall['cost_pf']}`")
    lines.append(f"- Stable/weak splits by cost net: `{overall['stable_splits']}` / `{overall['weak_splits']}`")
    lines.append("")
    lines.append("## Top Keep Buckets")
    lines.extend(md_table(payload["top_keep_buckets"], ["kind", "field", "bucket", "n", "net", "pf", "cost_net", "cost_pf", "stable_splits", "weak_splits", "min_split_cost_pf"], top))
    lines.append("")
    lines.append("## Top Remove Buckets")
    lines.extend(md_table(payload["top_remove_buckets"], ["kind", "field", "bucket", "removed_n", "n", "cost_net", "cost_pf", "delta_cost_pf", "stable_splits", "weak_splits", "min_split_cost_pf"], top))
    lines.append("")
    lines.append("## Top Pair Buckets")
    lines.extend(md_table(payload["top_pair_buckets"], ["kind", "field", "bucket", "n", "net", "pf", "cost_net", "cost_pf", "stable_splits", "weak_splits", "min_split_cost_pf"], top))
    lines.append("")
    lines.append("## Join")
    for key, value in payload["join"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Research-only. Buckets are hypothesis material, not production rules.")
    lines.append("- Cost is report-only and does not replace broker-real slippage/commission validation.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    analysis_dir = run_dir / "analysis"
    logs_dir = analysis_dir / "logs"
    opp_path = find_one(logs_dir, "*Opportunities*.csv")
    trade_path = find_one(logs_dir, "*Trades*.csv")

    joined, join_stats = join_s1_rows(read_csv(opp_path), read_csv(trade_path))
    if not joined:
        raise SystemExit("No joined S1 rows found.")

    fields = [
        "session_bucket",
        "hour_server",
        "weekday",
        "pvsra_event",
        "pvsra_grade",
        "pvsra_bias",
        "level_zone",
        "target_rr_bin",
        "risk_points_bin",
        "level_distance_bin",
        "score_bin",
        "trend_relation",
    ]
    remove_fields = [
        "hour_server",
        "weekday",
        "session_bucket",
        "pvsra_event",
        "pvsra_grade",
        "level_zone",
        "target_rr_bin",
        "risk_points_bin",
        "trend_relation",
    ]
    pairs = [
        ("session_bucket", "hour_server"),
        ("session_bucket", "pvsra_event"),
        ("hour_server", "pvsra_event"),
        ("pvsra_event", "level_zone"),
        ("target_rr_bin", "risk_points_bin"),
        ("trend_relation", "pvsra_event"),
    ]

    overall = calc_metrics(joined, args.cost)
    keep = field_candidates(joined, fields, args.cost, args.min_n)
    remove = remove_candidates(joined, remove_fields, args.cost, args.min_kept, overall)
    pair = pair_candidates(joined, pairs, args.cost, args.min_n)

    payload = {
        "schema_version": "sonic_s1_deep_anatomy.v1",
        "run_id": run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "opportunity_file": str(opp_path),
        "trade_file": str(trade_path),
        "cost_per_trade": args.cost,
        "join": join_stats,
        "overall": metrics_dict(overall),
        "top_keep_buckets": keep[: args.top],
        "top_remove_buckets": remove[: args.top],
        "top_pair_buckets": pair[: args.top],
    }

    out_json = Path(args.out_json) if args.out_json else analysis_dir / "sonic_s1_deep_anatomy.json"
    out_md = Path(args.out_md) if args.out_md else analysis_dir / "sonic_s1_deep_anatomy.md"
    out_csv = Path(args.out_csv) if args.out_csv else analysis_dir / "sonic_s1_deep_anatomy_candidates.csv"
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_md(out_md, payload, args.top)
    write_csv(out_csv, keep[: args.top] + remove[: args.top] + pair[: args.top])
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
