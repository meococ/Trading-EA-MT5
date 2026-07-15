#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phoenix_equity_diagnostics.py
=============================

Deep equity-curve diagnostics for Phoenix / MT5 HTML reports.

Why this exists
---------------
PF alone can hide ugly path dependency. This tool focuses on:
- equity shape
- underwater duration
- rolling 3M / 6M pain
- yearly concentration
- monthly consistency
- ulcer-style pain metrics
- top-trade concentration

Outputs
-------
- equity_diagnostics_summary.json
- rolling_3m.csv
- rolling_6m.csv
- yearly_breakdown.csv
- monthly_breakdown.csv
- equity_diagnostics.png
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except Exception:
    HAS_MPL = False

from quant_analyzer import Trade, deals_to_trades, parse_deals


START_EQUITY = 10000.0


def _pf(profits: Iterable[float]) -> float:
    gross_win = sum(p for p in profits if p > 0)
    gross_loss = abs(sum(p for p in profits if p < 0))
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def rebuild_equity(trades: List[Trade], start_equity: float = START_EQUITY) -> List[Tuple[datetime, float]]:
    bal = start_equity
    pts: List[Tuple[datetime, float]] = []
    for t in sorted(trades, key=lambda x: x.exit_time):
        bal += t.profit
        pts.append((t.exit_time, round(bal, 2)))
    return pts


def drawdown_series(points: List[Tuple[datetime, float]]) -> List[Tuple[datetime, float]]:
    peak = START_EQUITY
    dd = []
    for ts, eq in points:
        peak = max(peak, eq)
        pct = 0.0 if peak <= 0 else (eq - peak) / peak * 100.0
        dd.append((ts, round(pct, 4)))
    return dd


def ulcer_index(dd_points: List[Tuple[datetime, float]]) -> float:
    if not dd_points:
        return 0.0
    sq = [(min(0.0, dd) ** 2) for _, dd in dd_points]
    return math.sqrt(sum(sq) / len(sq))


def cagr(start: float, end: float, start_dt: datetime, end_dt: datetime) -> float:
    years = max((end_dt - start_dt).total_seconds() / (365.25 * 86400.0), 1e-9)
    if start <= 0 or end <= 0:
        return 0.0
    return ((end / start) ** (1.0 / years) - 1.0) * 100.0


def rolling_month_windows(monthly_net: Dict[str, float], window: int) -> List[Dict[str, float]]:
    keys = sorted(monthly_net.keys())
    out: List[Dict[str, float]] = []
    for i in range(len(keys) - window + 1):
        chunk = keys[i:i + window]
        out.append({
            "start": chunk[0],
            "end": chunk[-1],
            "months": window,
            "net_profit": round(sum(monthly_net[k] for k in chunk), 2),
        })
    return sorted(out, key=lambda x: x["net_profit"])


def month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def build_month_grid(monthly_net: Dict[str, float]) -> Tuple[List[int], List[List[float]]]:
    years = sorted({int(k[:4]) for k in monthly_net})
    grid = []
    for y in years:
        row = []
        for m in range(1, 13):
            row.append(round(monthly_net.get(f"{y:04d}-{m:02d}", 0.0), 2))
        grid.append(row)
    return years, grid


def longest_flat_period(points: List[Tuple[datetime, float]]) -> Dict[str, float]:
    if not points:
        return {"days": 0.0, "peak_time": None, "recovery_time": None}
    peak_eq = START_EQUITY
    peak_time = points[0][0]
    best_days = 0.0
    best = {"days": 0.0, "peak_time": peak_time, "recovery_time": peak_time}
    in_flat = False
    flat_peak_time = peak_time
    flat_peak_eq = peak_eq
    for ts, eq in points:
        if eq >= peak_eq:
            if in_flat:
                days = (ts - flat_peak_time).total_seconds() / 86400.0
                if days > best_days:
                    best_days = days
                    best = {
                        "days": round(days, 2),
                        "peak_time": flat_peak_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "recovery_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                in_flat = False
            peak_eq = eq
            peak_time = ts
            flat_peak_time = ts
            flat_peak_eq = eq
            continue
        if eq < flat_peak_eq:
            in_flat = True
    return best


def plot_pack(points: List[Tuple[datetime, float]],
              dd_points: List[Tuple[datetime, float]],
              years: List[int],
              month_grid: List[List[float]],
              rolling3: List[Dict[str, float]],
              rolling6: List[Dict[str, float]],
              yearly_rows: List[Dict[str, float]],
              out_path: Path) -> None:
    if not HAS_MPL or not points:
        return

    fig, axs = plt.subplots(3, 2, figsize=(18, 13))

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    ddx = [x for x, _ in dd_points]
    ddy = [y for _, y in dd_points]

    ax = axs[0, 0]
    ax.plot(xs, ys, color="royalblue", lw=1.4)
    ax.fill_between(xs, ys, START_EQUITY, color="steelblue", alpha=0.15)
    ax.set_title("Equity Curve")
    ax.set_ylabel("Equity ($)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax = axs[0, 1]
    ax.plot(ddx, ddy, color="firebrick", lw=1.1)
    ax.fill_between(ddx, ddy, 0, color="salmon", alpha=0.4)
    ax.set_title("Underwater / Drawdown %")
    ax.set_ylabel("Drawdown %")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax = axs[1, 0]
    ax.bar([f"{r['start']}->{r['end']}" for r in rolling3[:12]],
           [r["net_profit"] for r in rolling3[:12]],
           color=["firebrick" if r["net_profit"] < 0 else "forestgreen" for r in rolling3[:12]])
    ax.axhline(0, color="black", lw=1)
    ax.set_title("Worst Rolling 3M Windows")
    ax.tick_params(axis="x", labelrotation=60)

    ax = axs[1, 1]
    ax.bar([f"{r['start']}->{r['end']}" for r in rolling6[:12]],
           [r["net_profit"] for r in rolling6[:12]],
           color=["firebrick" if r["net_profit"] < 0 else "forestgreen" for r in rolling6[:12]])
    ax.axhline(0, color="black", lw=1)
    ax.set_title("Worst Rolling 6M Windows")
    ax.tick_params(axis="x", labelrotation=60)

    ax = axs[2, 0]
    y_labels = [str(r["year"]) for r in yearly_rows]
    y_vals = [r["return_pct"] for r in yearly_rows]
    ax.bar(y_labels, y_vals, color=["forestgreen" if v >= 0 else "firebrick" for v in y_vals])
    ax.axhline(0, color="black", lw=1)
    ax.set_title("Yearly Return %")
    ax.set_ylabel("%")

    ax = axs[2, 1]
    im = ax.imshow(month_grid, cmap="RdYlGn", aspect="auto")
    ax.set_title("Monthly Net Profit Heatmap")
    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], rotation=45)
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels([str(y) for y in years])
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Net Profit")

    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Deep equity diagnostics for Phoenix")
    ap.add_argument("--report", required=True, help="Path to MT5 report.html")
    ap.add_argument("--out", default="", help="Output directory")
    args = ap.parse_args()

    report = Path(args.report)
    if not report.exists():
        raise SystemExit(f"Report not found: {report}")

    out_dir = Path(args.out) if args.out else (report.parent / "equity_diagnostics")
    out_dir.mkdir(parents=True, exist_ok=True)

    deals = parse_deals(report)
    trades = sorted(deals_to_trades(deals), key=lambda t: t.exit_time)
    if not trades:
        raise SystemExit("No trades parsed from report")

    points = rebuild_equity(trades)
    dd_points = drawdown_series(points)
    monthly_net: Dict[str, float] = defaultdict(float)
    yearly_bucket: Dict[int, List[Trade]] = defaultdict(list)

    for t in trades:
        monthly_net[month_key(t.exit_time)] += t.profit
        yearly_bucket[t.exit_time.year].append(t)

    rolling3 = rolling_month_windows(monthly_net, 3)
    rolling6 = rolling_month_windows(monthly_net, 6)
    years, month_grid = build_month_grid(monthly_net)

    bal = START_EQUITY
    yearly_rows = []
    total_net = points[-1][1] - START_EQUITY
    for year in sorted(yearly_bucket):
        profits = [t.profit for t in yearly_bucket[year]]
        net = sum(profits)
        ret_pct = (net / bal * 100.0) if bal > 0 else 0.0
        bal += net
        yearly_rows.append({
            "year": year,
            "trades": len(profits),
            "net_profit": round(net, 2),
            "return_pct": round(ret_pct, 2),
            "profit_factor": round(_pf(profits), 3),
            "contribution_pct_of_total": round((net / total_net * 100.0) if total_net else 0.0, 2),
        })

    monthly_rows = [
        {"month": k, "net_profit": round(v, 2)}
        for k, v in sorted(monthly_net.items())
    ]
    monthly_negative = [r for r in monthly_rows if r["net_profit"] < 0]

    sorted_trades = sorted((t.profit for t in trades), reverse=True)
    top10_contrib = (sum(sorted_trades[:10]) / total_net * 100.0) if total_net else 0.0
    late_years = [r for r in yearly_rows if r["year"] >= 2024]
    late_contrib = sum(r["net_profit"] for r in late_years) / total_net * 100.0 if total_net else 0.0

    summary = {
        "report": str(report),
        "n_trades": len(trades),
        "start_equity": START_EQUITY,
        "final_equity": round(points[-1][1], 2),
        "net_profit": round(total_net, 2),
        "cagr_pct": round(cagr(START_EQUITY, points[-1][1], points[0][0], points[-1][0]), 2),
        "max_drawdown_pct": round(min((dd for _, dd in dd_points), default=0.0), 2),
        "ulcer_index": round(ulcer_index(dd_points), 3),
        "profit_factor": round(_pf([t.profit for t in trades]), 3),
        "worst_rolling_3m": rolling3[:10],
        "worst_rolling_6m": rolling6[:10],
        "negative_months": len(monthly_negative),
        "negative_month_ratio_pct": round(len(monthly_negative) / len(monthly_rows) * 100.0, 2) if monthly_rows else 0.0,
        "late_year_contribution_pct": round(late_contrib, 2),
        "top10_trade_contribution_pct": round(top10_contrib, 2),
        "worst_year": min(yearly_rows, key=lambda x: x["net_profit"]),
        "best_year": max(yearly_rows, key=lambda x: x["net_profit"]),
        "longest_flat_period": longest_flat_period(points),
    }

    with (out_dir / "equity_diagnostics_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    for name, rows in [
        ("rolling_3m.csv", rolling3),
        ("rolling_6m.csv", rolling6),
        ("yearly_breakdown.csv", yearly_rows),
        ("monthly_breakdown.csv", monthly_rows),
    ]:
        if not rows:
            continue
        with (out_dir / name).open("w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)

    plot_pack(points, dd_points, years, month_grid, rolling3, rolling6, yearly_rows, out_dir / "equity_diagnostics.png")

    print(json.dumps(summary, indent=2))
    print("\nWrote:")
    for fn in [
        "equity_diagnostics_summary.json",
        "rolling_3m.csv",
        "rolling_6m.csv",
        "yearly_breakdown.csv",
        "monthly_breakdown.csv",
        "equity_diagnostics.png" if HAS_MPL else None,
    ]:
        if fn:
            print(f"- {out_dir / fn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
