#!/usr/bin/env python3
"""Profit-period anatomy for Sonic R long-window research runs.

Reads the enriched market-regime trade labels and answers where the EA actually
makes or loses money: months, years, phases, lanes, direction/session, and
regime buckets. This is analysis-only and never mutates EA logic.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"
TIME_FORMATS = ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def parse_ts(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def read_rows(path: Path, cost_per_trade: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            ts = parse_ts(row.get("entry_server_ts"))
            if ts is None:
                continue
            pnl = safe_float(row.get("pnl_net"))
            out: dict[str, Any] = dict(row)
            out["entry_ts"] = ts
            out["year"] = str(ts.year)
            out["month"] = f"{ts.year}-{ts.month:02d}"
            out["half_year"] = row.get("half_year") or f"{ts.year}H{1 if ts.month <= 6 else 2}"
            out["pnl_net"] = pnl
            out["pnl_after_cost"] = pnl - cost_per_trade
            out["hour"] = str(row.get("hour") or ts.hour)
            rows.append(out)
    return rows


def profit_factor(values: Iterable[float]) -> float:
    vals = list(values)
    gross_win = sum(value for value in vals if value > 0)
    gross_loss = -sum(value for value in vals if value < 0)
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [safe_float(row["pnl_net"]) for row in rows]
    cost = [safe_float(row["pnl_after_cost"]) for row in rows]
    by_half: dict[str, float] = defaultdict(float)
    by_year: dict[str, float] = defaultdict(float)
    for row in rows:
        by_half[str(row["half_year"])] += safe_float(row["pnl_after_cost"])
        by_year[str(row["year"])] += safe_float(row["pnl_after_cost"])
    return {
        "count": len(rows),
        "net": round(sum(pnl), 2),
        "net_after_cost": round(sum(cost), 2),
        "pf": round(profit_factor(pnl), 6),
        "pf_after_cost": round(profit_factor(cost), 6),
        "win_rate": round(sum(1 for value in pnl if value > 0) / len(pnl), 6) if pnl else 0.0,
        "expectancy": round(statistics.mean(pnl), 6) if pnl else 0.0,
        "expectancy_after_cost": round(statistics.mean(cost), 6) if cost else 0.0,
        "positive_half_years": sum(1 for value in by_half.values() if value > 0),
        "total_half_years": len(by_half),
        "positive_years": sum(1 for value in by_year.values() if value > 0),
        "total_years": len(by_year),
        "best_half_year": max(by_half.items(), key=lambda item: item[1]) if by_half else None,
        "worst_half_year": min(by_half.items(), key=lambda item: item[1]) if by_half else None,
    }


def group_by(rows: list[dict[str, Any]], fields: list[str], min_count: int) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(field) or "NA") for field in fields)
        buckets[key].append(row)
    out: list[dict[str, Any]] = []
    for key, bucket_rows in buckets.items():
        if len(bucket_rows) < min_count:
            continue
        summary = summarize_rows(bucket_rows)
        item: dict[str, Any] = {"group": "+".join(fields)}
        for field, value in zip(fields, key):
            item[field] = value
        item.update(summary)
        out.append(item)
    out.sort(key=lambda item: (-safe_float(item.get("net_after_cost")), -safe_float(item.get("pf_after_cost"))))
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_month_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_month[str(row["month"])].append(row)
    out = []
    for month, month_rows in sorted(by_month.items()):
        item = {"month": month}
        item.update(summarize_rows(month_rows))
        out.append(item)
    return out


def feature_means(rows: list[dict[str, Any]], numeric_fields: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for field in numeric_fields:
        vals = [safe_float(row.get(field), float("nan")) for row in rows]
        vals = [value for value in vals if math.isfinite(value)]
        if vals:
            out[field] = round(statistics.mean(vals), 6)
    return out


def render_markdown(result: dict[str, Any]) -> str:
    overall = result["overall"]
    lines = [
        "# Sonic Profit-Period Anatomy",
        "",
        f"- Run: `{result['run_id']}`",
        f"- Trades: `{overall['count']}`",
        f"- Net after cost: `{overall['net_after_cost']}`",
        f"- PF after cost: `{overall['pf_after_cost']}`",
        f"- Positive months: `{result['positive_months']}/{result['total_months']}`",
        f"- Positive half-years: `{overall['positive_half_years']}/{overall['total_half_years']}`",
        f"- Positive years: `{overall['positive_years']}/{overall['total_years']}`",
        "",
        "## Best Months",
        "",
        "| month | trades | net cost | PF cost |",
        "|---|---:|---:|---:|",
    ]
    for row in result["best_months"]:
        lines.append(f"| {row['month']} | {row['count']} | {row['net_after_cost']} | {row['pf_after_cost']} |")
    lines.extend(["", "## Worst Months", "", "| month | trades | net cost | PF cost |", "|---|---:|---:|---:|"])
    for row in result["worst_months"]:
        lines.append(f"| {row['month']} | {row['count']} | {row['net_after_cost']} | {row['pf_after_cost']} |")
    lines.extend(
        [
            "",
            "## Top Stable Buckets",
            "",
            "| group | bucket | trades | net cost | PF cost | half-years | years |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in result["top_buckets"][:15]:
        bucket = ", ".join(f"{key}={value}" for key, value in row.items() if key not in {
            "group",
            "count",
            "net",
            "net_after_cost",
            "pf",
            "pf_after_cost",
            "win_rate",
            "expectancy",
            "expectancy_after_cost",
            "positive_half_years",
            "total_half_years",
            "positive_years",
            "total_years",
            "best_half_year",
            "worst_half_year",
        })
        lines.append(
            f"| {row['group']} | {bucket} | {row['count']} | {row['net_after_cost']} | {row['pf_after_cost']} | {row['positive_half_years']}/{row['total_half_years']} | {row['positive_years']}/{row['total_years']} |"
        )
    lines.extend(
        [
            "",
            "## Decision Notes",
            "",
            "- Treat profitable buckets as market-model clues, not direct EA rules.",
            "- A bucket needs cost, split, and independent-test survival before coding.",
        ]
    )
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = run_dir_for(args.run, args.ea_name)
    analysis_dir = run_dir / "analysis"
    label_path = analysis_dir / "market_regime_trade_labels.csv"
    if not label_path.exists():
        label_path = analysis_dir / "market_phase_trade_labels.csv"
    if not label_path.exists():
        raise SystemExit(f"missing enriched trade labels under {analysis_dir}")
    rows = read_rows(label_path, args.cost_per_trade)
    month_table = build_month_table(rows)
    best_months = sorted(month_table, key=lambda row: safe_float(row.get("net_after_cost")), reverse=True)[:10]
    worst_months = sorted(month_table, key=lambda row: safe_float(row.get("net_after_cost")))[:10]
    categorical_groups = [
        ["year"],
        ["half_year"],
        ["market_phase"],
        ["engine_variant"],
        ["direction"],
        ["session_tag"],
        ["hour"],
        ["engine_variant", "market_phase"],
        ["engine_variant", "direction"],
        ["market_phase", "direction"],
        ["trend_bucket_36"],
        ["trend_bucket_96"],
        ["trend_bucket_288"],
        ["trend_bucket_1440"],
        ["range_bucket_36"],
        ["range_bucket_96"],
        ["efficiency_bucket_36"],
        ["efficiency_bucket_96"],
        ["vol_regime_1440"],
        ["macro_year_tag"],
        ["trade_aligns_5d_trend"],
        ["signal_dragon_angle_class"],
        ["signal_pvsra_bias"],
        ["signal_pvsra_event"],
        ["signal_level_zone"],
        ["signal_spread_regime"],
        ["engine_variant", "trend_bucket_288", "range_bucket_288"],
        ["engine_variant", "trend_bucket_1440", "range_bucket_1440"],
    ]
    buckets: list[dict[str, Any]] = []
    for fields in categorical_groups:
        buckets.extend(group_by(rows, fields, args.min_bucket_trades))
    top_buckets = [
        row
        for row in buckets
        if safe_float(row.get("net_after_cost")) > 0
        and safe_float(row.get("pf_after_cost")) >= 1.15
        and int(row.get("positive_years") or 0) >= 2
    ]
    top_buckets.sort(
        key=lambda row: (
            -int(row.get("positive_half_years") or 0),
            -safe_float(row.get("net_after_cost")),
            -safe_float(row.get("pf_after_cost")),
        )
    )
    positive_month_rows = [row for row in month_table if safe_float(row.get("net_after_cost")) > 0]
    negative_month_rows = [row for row in month_table if safe_float(row.get("net_after_cost")) <= 0]
    result = {
        "schema_version": "sonic_profit_period_anatomy.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "source": str(label_path),
        "cost_per_trade": args.cost_per_trade,
        "overall": summarize_rows(rows),
        "total_months": len(month_table),
        "positive_months": len(positive_month_rows),
        "negative_months": len(negative_month_rows),
        "best_months": best_months,
        "worst_months": worst_months,
        "top_buckets": top_buckets[:50],
        "all_bucket_rows": len(buckets),
        "profitable_feature_means": feature_means([row for row in rows if safe_float(row["pnl_after_cost"]) > 0], [
            "atr20_percentile_1440",
            "range_width_atr_36",
            "range_width_atr_96",
            "efficiency_36",
            "efficiency_96",
            "signal_dragon_slope_atr",
            "signal_trend_slope_atr",
            "signal_body_ratio",
            "signal_range_atr",
            "signal_level_distance_pips",
            "signal_spread_pips",
        ]),
        "losing_feature_means": feature_means([row for row in rows if safe_float(row["pnl_after_cost"]) <= 0], [
            "atr20_percentile_1440",
            "range_width_atr_36",
            "range_width_atr_96",
            "efficiency_36",
            "efficiency_96",
            "signal_dragon_slope_atr",
            "signal_trend_slope_atr",
            "signal_body_ratio",
            "signal_range_atr",
            "signal_level_distance_pips",
            "signal_spread_pips",
        ]),
    }
    json_path = analysis_dir / "sonic_profit_period_anatomy.json"
    md_path = analysis_dir / "sonic_profit_period_anatomy.md"
    month_path = analysis_dir / "sonic_profit_period_months.csv"
    bucket_path = analysis_dir / "sonic_profit_period_buckets.csv"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    write_csv(month_path, month_table)
    write_csv(bucket_path, buckets)
    result["outputs"] = {
        "json": str(json_path),
        "markdown": str(md_path),
        "months_csv": str(month_path),
        "buckets_csv": str(bucket_path),
    }
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="AlphaFactory run id or run directory")
    parser.add_argument("--ea-name", default=DEFAULT_EA)
    parser.add_argument("--cost-per-trade", type=float, default=0.50)
    parser.add_argument("--min-bucket-trades", type=int, default=20)
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "net_after_cost": result["overall"]["net_after_cost"],
                "pf_after_cost": result["overall"]["pf_after_cost"],
                "positive_months": f"{result['positive_months']}/{result['total_months']}",
                "positive_years": f"{result['overall']['positive_years']}/{result['overall']['total_years']}",
                "top_bucket_count": len(result["top_buckets"]),
                "markdown": result["outputs"]["markdown"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
