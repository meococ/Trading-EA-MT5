#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phoenix_scalp_forensics.py
==========================

Forensic layer tailored for Phoenix-style intraday/session EAs.

Purpose
-------
- Parse MT5 report directly
- Rebuild equity and underwater periods
- Highlight regime/month/hour pain clusters
- Produce a compact chart pack for iterative EA research

Outputs
-------
- forensics_summary.json
- underwater_periods.csv
- hourly_breakdown.csv
- monthly_heatmap.csv
- rolling_3m.csv
- phoenix_forensics.png (if matplotlib available)
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except Exception:
    HAS_MPL = False

from quant_analyzer import parse_deals, deals_to_trades, Trade


START_EQUITY = 10000.0


def _pf(gross_win: float, gross_loss: float) -> float:
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _bucket_stats(trades: Iterable[Trade]) -> Dict[str, float]:
    items = list(trades)
    wins = [t.profit for t in items if t.profit > 0]
    losses = [t.profit for t in items if t.profit < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "n": len(items),
        "net_profit": sum(t.profit for t in items),
        "profit_factor": _pf(gross_win, gross_loss),
        "win_rate_pct": (len(wins) / len(items) * 100.0) if items else 0.0,
        "avg_win": statistics.mean(wins) if wins else 0.0,
        "avg_loss": statistics.mean(losses) if losses else 0.0,
    }


@dataclass
class EquityPoint:
    ts: datetime
    equity: float


@dataclass
class UnderwaterPeriod:
    peak_time: datetime
    trough_time: datetime
    recovery_time: Optional[datetime]
    peak_equity: float
    trough_equity: float
    max_dd_pct: float

    @property
    def recovered(self) -> bool:
        return self.recovery_time is not None

    @property
    def duration_days(self) -> float:
        end = self.recovery_time or self.trough_time
        return round((end - self.peak_time).total_seconds() / 86400.0, 2)


def rebuild_equity(trades: List[Trade], start_equity: float = START_EQUITY) -> List[EquityPoint]:
    bal = start_equity
    out: List[EquityPoint] = []
    for t in sorted(trades, key=lambda x: x.exit_time):
        bal += t.profit
        out.append(EquityPoint(t.exit_time, round(bal, 2)))
    return out


def compute_underwater_periods(points: List[EquityPoint]) -> List[UnderwaterPeriod]:
    if not points:
        return []

    peak_equity = START_EQUITY
    peak_time = points[0].ts
    trough_equity = peak_equity
    trough_time = peak_time
    in_period = False
    periods: List[UnderwaterPeriod] = []
    curr_max_dd = 0.0

    for p in points:
        if p.equity >= peak_equity:
            if in_period:
                periods.append(
                    UnderwaterPeriod(
                        peak_time=peak_time,
                        trough_time=trough_time,
                        recovery_time=p.ts,
                        peak_equity=peak_equity,
                        trough_equity=trough_equity,
                        max_dd_pct=round(curr_max_dd, 2),
                    )
                )
                in_period = False
                trough_equity = p.equity
                trough_time = p.ts
                curr_max_dd = 0.0
            peak_equity = p.equity
            peak_time = p.ts
            continue

        dd_pct = ((peak_equity - p.equity) / peak_equity * 100.0) if peak_equity > 0 else 0.0
        if not in_period:
            in_period = True
            trough_equity = p.equity
            trough_time = p.ts
            curr_max_dd = dd_pct
        elif p.equity < trough_equity:
            trough_equity = p.equity
            trough_time = p.ts
            curr_max_dd = max(curr_max_dd, dd_pct)
        else:
            curr_max_dd = max(curr_max_dd, dd_pct)

    if in_period:
        periods.append(
            UnderwaterPeriod(
                peak_time=peak_time,
                trough_time=trough_time,
                recovery_time=None,
                peak_equity=peak_equity,
                trough_equity=trough_equity,
                max_dd_pct=round(curr_max_dd, 2),
            )
        )

    periods.sort(key=lambda x: (x.max_dd_pct, x.duration_days), reverse=True)
    return periods


def month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def rolling_month_clusters(monthly_net: Dict[str, float], window: int = 3) -> List[Dict[str, float]]:
    keys = sorted(monthly_net.keys())
    out = []
    for i in range(len(keys) - window + 1):
        chunk = keys[i:i + window]
        net = sum(monthly_net[k] for k in chunk)
        out.append({
            "start": chunk[0],
            "end": chunk[-1],
            "months": window,
            "net_profit": round(net, 2),
        })
    return sorted(out, key=lambda x: x["net_profit"])


def build_month_heatmap(monthly_net: Dict[str, float]) -> Tuple[List[int], List[List[float]]]:
    years = sorted({int(k[:4]) for k in monthly_net.keys()})
    grid: List[List[float]] = []
    for y in years:
        row = []
        for m in range(1, 13):
            row.append(round(monthly_net.get(f"{y:04d}-{m:02d}", 0.0), 2))
        grid.append(row)
    return years, grid


def plot_forensics(points: List[EquityPoint],
                   periods: List[UnderwaterPeriod],
                   year_rows: List[Dict[str, float]],
                   years: List[int],
                   heatmap: List[List[float]],
                   hour_rows: List[Dict[str, float]],
                   out_path: Path) -> None:
    if not HAS_MPL or not points:
        return

    fig, axs = plt.subplots(2, 2, figsize=(16, 10))

    # Equity
    ax = axs[0, 0]
    xs = [p.ts for p in points]
    ys = [p.equity for p in points]
    ax.plot(xs, ys, color="royalblue", linewidth=1.4)
    ax.fill_between(xs, ys, START_EQUITY, color="steelblue", alpha=0.15)
    ax.set_title("Phoenix Equity Forensics")
    ax.set_ylabel("Equity ($)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for p in periods[:3]:
        end = p.recovery_time or p.trough_time
        ax.axvspan(p.peak_time, end, color="red", alpha=0.08)

    # Underwater heatmap
    ax = axs[0, 1]
    im = ax.imshow(heatmap, cmap="RdYlGn", aspect="auto")
    ax.set_title("Monthly Net Profit Heatmap")
    ax.set_xticks(range(12))
    ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], rotation=45)
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels([str(y) for y in years])
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Net Profit")

    # Yearly returns
    ax = axs[1, 0]
    y_labels = [str(r["year"]) for r in year_rows]
    y_vals = [r["return_pct"] for r in year_rows]
    colors = ["forestgreen" if v >= 0 else "firebrick" for v in y_vals]
    ax.bar(y_labels, y_vals, color=colors)
    ax.axhline(0.0, color="black", linewidth=1)
    ax.set_title("Yearly Return % (reconstructed)")
    ax.set_ylabel("%")

    # Hourly PF
    ax = axs[1, 1]
    h_labels = [str(r["hour"]) for r in hour_rows]
    h_vals = [r["profit_factor"] for r in hour_rows]
    colors = ["forestgreen" if v >= 1.0 else "firebrick" for v in h_vals]
    ax.bar(h_labels, h_vals, color=colors)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set_title("Profit Factor by Entry Hour")
    ax.set_ylabel("PF")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Phoenix Scalp Forensics")
    ap.add_argument("--report", required=True, help="Path to MT5 HTML report")
    ap.add_argument("--out", default="", help="Output directory")
    args = ap.parse_args()

    report = Path(args.report)
    if not report.exists():
        raise SystemExit(f"Report not found: {report}")

    out_dir = Path(args.out) if args.out else (report.parent / "forensics")
    out_dir.mkdir(parents=True, exist_ok=True)

    deals = parse_deals(report)
    trades = deals_to_trades(deals)
    trades = sorted(trades, key=lambda t: t.exit_time)
    if not trades:
        raise SystemExit("No trades parsed from report")

    points = rebuild_equity(trades)
    uw = compute_underwater_periods(points)

    by_year: Dict[int, List[Trade]] = defaultdict(list)
    by_hour: Dict[int, List[Trade]] = defaultdict(list)
    monthly_net: Dict[str, float] = defaultdict(float)

    for t in trades:
        by_year[t.exit_time.year].append(t)
        by_hour[t.entry_time.hour].append(t)
        monthly_net[month_key(t.exit_time)] += t.profit

    year_rows = []
    bal = START_EQUITY
    for y in sorted(by_year):
        stats = _bucket_stats(by_year[y])
        ret = stats["net_profit"] / bal * 100.0 if bal > 0 else 0.0
        bal += stats["net_profit"]
        year_rows.append({
            "year": y,
            "n": stats["n"],
            "net_profit": round(stats["net_profit"], 2),
            "profit_factor": round(stats["profit_factor"], 3),
            "return_pct": round(ret, 2),
        })

    hour_rows = []
    for h in range(24):
        stats = _bucket_stats(by_hour.get(h, []))
        hour_rows.append({
            "hour": h,
            "n": stats["n"],
            "net_profit": round(stats["net_profit"], 2),
            "profit_factor": round(stats["profit_factor"], 3),
            "win_rate_pct": round(stats["win_rate_pct"], 1),
        })

    years, heatmap = build_month_heatmap(monthly_net)
    rolling3 = rolling_month_clusters(monthly_net, window=3)

    summary = {
        "report": str(report),
        "n_trades": len(trades),
        "start_equity": START_EQUITY,
        "final_equity": round(points[-1].equity, 2),
        "top_underwater_periods": [
            {
                "peak_time": p.peak_time.strftime("%Y-%m-%d %H:%M:%S"),
                "trough_time": p.trough_time.strftime("%Y-%m-%d %H:%M:%S"),
                "recovery_time": p.recovery_time.strftime("%Y-%m-%d %H:%M:%S") if p.recovery_time else None,
                "max_dd_pct": p.max_dd_pct,
                "duration_days": p.duration_days,
                "recovered": p.recovered,
            }
            for p in uw[:10]
        ],
        "worst_year": min(year_rows, key=lambda x: x["net_profit"]),
        "best_year": max(year_rows, key=lambda x: x["net_profit"]),
        "worst_hour": min((r for r in hour_rows if r["n"] > 0), key=lambda x: x["profit_factor"]),
        "best_hour": max((r for r in hour_rows if r["n"] > 0), key=lambda x: x["profit_factor"]),
        "worst_rolling_3m": rolling3[:10],
    }

    with (out_dir / "forensics_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with (out_dir / "underwater_periods.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["peak_time", "trough_time", "recovery_time", "max_dd_pct", "duration_days", "recovered"])
        for p in uw:
            wr.writerow([
                p.peak_time.strftime("%Y-%m-%d %H:%M:%S"),
                p.trough_time.strftime("%Y-%m-%d %H:%M:%S"),
                p.recovery_time.strftime("%Y-%m-%d %H:%M:%S") if p.recovery_time else "",
                p.max_dd_pct,
                p.duration_days,
                int(p.recovered),
            ])

    with (out_dir / "hourly_breakdown.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["hour", "n", "net_profit", "profit_factor", "win_rate_pct"])
        wr.writeheader()
        wr.writerows(hour_rows)

    with (out_dir / "monthly_heatmap.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["year", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        for y, row in zip(years, heatmap):
            wr.writerow([y] + row)

    with (out_dir / "rolling_3m.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["start", "end", "months", "net_profit"])
        wr.writeheader()
        wr.writerows(rolling3)

    plot_forensics(points, uw, year_rows, years, heatmap, hour_rows, out_dir / "phoenix_forensics.png")

    print(json.dumps(summary, indent=2))
    print("\nWrote:")
    for name in [
        "forensics_summary.json",
        "underwater_periods.csv",
        "hourly_breakdown.csv",
        "monthly_heatmap.csv",
        "rolling_3m.csv",
        "phoenix_forensics.png" if HAS_MPL else None,
    ]:
        if name:
            print(f"- {out_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
