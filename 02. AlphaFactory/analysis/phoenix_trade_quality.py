#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phoenix_trade_quality.py
========================

Enhanced trade-level forensics for Phoenix-style EAs.
Extends quant_analyzer with:
- Entry/Exit price extraction from deals
- R-multiple estimation (if SL derivable from comment/deal structure)
- Close reason classification (SL/TP/Friday/Trail/Manual)
- Duration bucketing
- Win/Loss clustering analysis (consecutive streaks & pain periods)
- Underwater period autopsy with per-trade attribution

Usage:
  python phoenix_trade_quality.py --report <report.html> --out <output_dir>

Outputs:
  - trade_quality.csv: Per-trade metrics
  - close_reasons.json: Breakdown by close type
  - pain_clusters.csv: Worst underwater periods with trade attribution
  - duration_analysis.json: Performance by trade duration bucket
  - streak_analysis.json: Win/loss streak distribution
  - trade_quality_summary.json: Overall quality metrics
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except Exception:
    HAS_MPL = False

from quant_analyzer import parse_deals, Deal

START_EQUITY = 10000.0


# ============================================================
# Enhanced Trade with price data
# ============================================================

@dataclass
class EnhancedTrade:
    """Trade with full price & quality metrics."""
    ticket: int
    entry_time: datetime
    exit_time: datetime
    side: str               # buy/sell
    entry_price: float
    exit_price: float
    volume: float
    profit: float
    commission: float
    swap: float
    net_profit: float       # profit + commission + swap
    duration_minutes: float
    entry_comment: str
    exit_comment: str

    # Derived metrics
    close_reason: str       # SL / TP / Friday / Trail / BE / Manual / Unknown
    pips: float             # Price movement in pips
    year: int
    month: int
    hour: int               # Entry hour
    day_of_week: int        # 0=Mon, 6=Sun


# ============================================================
# Deal -> Enhanced Trade conversion
# ============================================================

def deals_to_enhanced_trades(deals: List[Deal]) -> List[EnhancedTrade]:
    """Convert deals to enhanced trades with full price data."""
    trades = []
    open_positions = []  # list of dicts: {entry_deal, remaining_vol, out_deals}
    eps = 1e-9

    for d in deals:
        side = (d.side or "").strip().lower()
        direction = (d.direction or "").strip().lower()

        if side == "balance":
            continue

        if direction == "in":
            open_positions.append({
                "entry": d,
                "remaining": abs(d.volume),
                "outs": [],
            })
            continue

        if direction != "out":
            continue

        remaining_out = abs(d.volume)
        if remaining_out <= eps:
            continue

        # Match FIFO against open positions (opposite side)
        target_side = "buy" if side == "sell" else "sell"

        while remaining_out > eps and open_positions:
            # Find matching entry
            best_idx = None
            for i, pos in enumerate(open_positions):
                if pos["remaining"] > eps:
                    entry_side = (pos["entry"].side or "").strip().lower()
                    if entry_side == target_side:
                        best_idx = i
                        break

            if best_idx is None:
                # Fallback: first available
                for i, pos in enumerate(open_positions):
                    if pos["remaining"] > eps:
                        best_idx = i
                        break

            if best_idx is None:
                break

            pos = open_positions[best_idx]
            fill = min(remaining_out, pos["remaining"])
            pos["remaining"] -= fill
            remaining_out -= fill
            pos["outs"].append(d)

            # Emit trade when position fully closed
            if pos["remaining"] <= eps:
                entry_deal = pos["entry"]
                out_deals = pos["outs"]
                total_profit = sum(x.profit for x in out_deals)
                total_commission = sum(x.commission for x in out_deals) + entry_deal.commission
                total_swap = sum(x.swap for x in out_deals)
                exit_price = out_deals[-1].price if out_deals else entry_deal.price
                exit_time = out_deals[-1].time if out_deals else entry_deal.time

                entry_side = (entry_deal.side or "").strip().lower()
                duration = (exit_time - entry_deal.time).total_seconds() / 60.0

                # Pips calculation (gold: 1 pip = 0.1, point = 0.01)
                if entry_side == "buy":
                    pips = (exit_price - entry_deal.price) * 10.0
                else:
                    pips = (entry_deal.price - exit_price) * 10.0

                # Close reason classification
                close_reason = classify_close_reason(out_deals[-1], total_profit, duration)

                et = EnhancedTrade(
                    ticket=entry_deal.deal_id,
                    entry_time=entry_deal.time,
                    exit_time=exit_time,
                    side=entry_side,
                    entry_price=entry_deal.price,
                    exit_price=exit_price,
                    volume=abs(entry_deal.volume),
                    profit=total_profit,
                    commission=total_commission,
                    swap=total_swap,
                    net_profit=total_profit + total_commission + total_swap,
                    duration_minutes=duration,
                    entry_comment=entry_deal.comment or "",
                    exit_comment=out_deals[-1].comment if out_deals else "",
                    close_reason=close_reason,
                    pips=pips,
                    year=entry_deal.time.year,
                    month=entry_deal.time.month,
                    hour=entry_deal.time.hour,
                    day_of_week=entry_deal.time.weekday(),
                )
                trades.append(et)
                open_positions.pop(best_idx)

    return trades


def classify_close_reason(exit_deal: Deal, profit: float, duration_min: float) -> str:
    """Classify why a trade was closed based on deal comment and context."""
    comment = (exit_deal.comment or "").strip().lower()

    # Common MT5 close reason patterns
    if "sl" in comment or "stop loss" in comment:
        return "SL"
    if "tp" in comment or "take profit" in comment:
        return "TP"
    if "friday" in comment or "flatten" in comment:
        return "FRIDAY"
    if "trail" in comment:
        return "TRAIL"
    if "be" in comment or "breakeven" in comment:
        return "BE"
    if "news" in comment:
        return "NEWS"
    if "kill" in comment or "emergency" in comment:
        return "KILL"
    if "dd" in comment:
        return "DD_GUARD"

    # Heuristic fallback based on profit/duration
    # If profit is very close to zero and positive -> likely BE
    if 0 < profit < 1.0:
        return "BE_LIKELY"

    # If closed on Friday afternoon
    if exit_deal.time.weekday() == 4 and exit_deal.time.hour >= 16:
        return "FRIDAY_LIKELY"

    return "UNKNOWN"


# ============================================================
# Analysis functions
# ============================================================

def analyze_close_reasons(trades: List[EnhancedTrade]) -> Dict:
    """Breakdown by close reason."""
    reasons = defaultdict(lambda: {"count": 0, "total_profit": 0.0, "wins": 0, "losses": 0})

    for t in trades:
        r = reasons[t.close_reason]
        r["count"] += 1
        r["total_profit"] += t.net_profit
        if t.profit > 0:
            r["wins"] += 1
        else:
            r["losses"] += 1

    result = {}
    for reason, stats in sorted(reasons.items(), key=lambda x: -x[1]["count"]):
        wr = stats["wins"] / stats["count"] * 100 if stats["count"] > 0 else 0
        result[reason] = {
            "count": stats["count"],
            "total_profit": round(stats["total_profit"], 2),
            "avg_profit": round(stats["total_profit"] / stats["count"], 2) if stats["count"] > 0 else 0,
            "win_rate": round(wr, 1),
            "pct_of_total": round(stats["count"] / len(trades) * 100, 1) if trades else 0,
        }
    return result


def analyze_duration(trades: List[EnhancedTrade]) -> Dict:
    """Performance by trade duration buckets."""
    buckets = {
        "0-30min": (0, 30),
        "30-60min": (30, 60),
        "1-2h": (60, 120),
        "2-4h": (120, 240),
        "4-8h": (240, 480),
        "8h+": (480, 99999),
    }

    result = {}
    for name, (lo, hi) in buckets.items():
        bucket_trades = [t for t in trades if lo <= t.duration_minutes < hi]
        if not bucket_trades:
            result[name] = {"count": 0}
            continue

        wins = sum(1 for t in bucket_trades if t.profit > 0)
        total_pnl = sum(t.net_profit for t in bucket_trades)
        avg_dur = statistics.mean(t.duration_minutes for t in bucket_trades)

        result[name] = {
            "count": len(bucket_trades),
            "total_profit": round(total_pnl, 2),
            "avg_profit": round(total_pnl / len(bucket_trades), 2),
            "win_rate": round(wins / len(bucket_trades) * 100, 1),
            "avg_duration_min": round(avg_dur, 0),
        }
    return result


def analyze_streaks(trades: List[EnhancedTrade]) -> Dict:
    """Win/loss streak distribution."""
    if not trades:
        return {}

    streaks = []
    current_type = None
    current_len = 0
    current_pnl = 0.0

    for t in trades:
        is_win = t.profit > 0
        stype = "win" if is_win else "loss"

        if stype == current_type:
            current_len += 1
            current_pnl += t.net_profit
        else:
            if current_type is not None:
                streaks.append({"type": current_type, "length": current_len, "pnl": round(current_pnl, 2)})
            current_type = stype
            current_len = 1
            current_pnl = t.net_profit

    if current_type is not None:
        streaks.append({"type": current_type, "length": current_len, "pnl": round(current_pnl, 2)})

    # Summarize
    win_streaks = [s for s in streaks if s["type"] == "win"]
    loss_streaks = [s for s in streaks if s["type"] == "loss"]

    return {
        "max_win_streak": max((s["length"] for s in win_streaks), default=0),
        "max_loss_streak": max((s["length"] for s in loss_streaks), default=0),
        "avg_win_streak": round(statistics.mean(s["length"] for s in win_streaks), 1) if win_streaks else 0,
        "avg_loss_streak": round(statistics.mean(s["length"] for s in loss_streaks), 1) if loss_streaks else 0,
        "worst_loss_streak_pnl": round(min((s["pnl"] for s in loss_streaks), default=0), 2),
        "best_win_streak_pnl": round(max((s["pnl"] for s in win_streaks), default=0), 2),
        "total_streaks": len(streaks),
        "streaks_top10_worst": sorted(loss_streaks, key=lambda s: s["pnl"])[:10],
    }


def analyze_pain_clusters(trades: List[EnhancedTrade], top_n: int = 20) -> List[Dict]:
    """Find worst underwater periods with per-trade attribution."""
    if not trades:
        return []

    # Build equity curve
    equity = START_EQUITY
    peak = equity
    underwater_start = None
    clusters = []
    current_cluster_trades = []

    for t in trades:
        equity += t.net_profit

        if equity > peak:
            # End underwater period
            if underwater_start is not None and current_cluster_trades:
                dd_pct = (peak - min_eq) / peak * 100 if peak > 0 else 0
                clusters.append({
                    "start": underwater_start.strftime("%Y-%m-%d"),
                    "end": t.exit_time.strftime("%Y-%m-%d"),
                    "days": (t.exit_time - underwater_start).days,
                    "n_trades": len(current_cluster_trades),
                    "pnl": round(sum(ct.net_profit for ct in current_cluster_trades), 2),
                    "dd_pct": round(dd_pct, 2),
                    "worst_trade_pnl": round(min(ct.net_profit for ct in current_cluster_trades), 2),
                    "close_reasons": dict(defaultdict(int, {
                        ct.close_reason: 1 for ct in current_cluster_trades
                    })),
                })
            peak = equity
            underwater_start = None
            current_cluster_trades = []
            min_eq = equity
        else:
            if underwater_start is None:
                underwater_start = t.entry_time
                min_eq = equity
            else:
                min_eq = min(min_eq, equity)
            current_cluster_trades.append(t)

    # Handle still-underwater at end
    if underwater_start is not None and current_cluster_trades:
        dd_pct = (peak - min_eq) / peak * 100 if peak > 0 else 0
        clusters.append({
            "start": underwater_start.strftime("%Y-%m-%d"),
            "end": trades[-1].exit_time.strftime("%Y-%m-%d"),
            "days": (trades[-1].exit_time - underwater_start).days,
            "n_trades": len(current_cluster_trades),
            "pnl": round(sum(ct.net_profit for ct in current_cluster_trades), 2),
            "dd_pct": round(dd_pct, 2),
            "worst_trade_pnl": round(min(ct.net_profit for ct in current_cluster_trades), 2),
            "close_reasons": {},
        })

    # Sort by worst DD
    clusters.sort(key=lambda c: -c["dd_pct"])
    return clusters[:top_n]


def generate_summary(trades: List[EnhancedTrade]) -> Dict:
    """Overall quality summary."""
    if not trades:
        return {"error": "no trades"}

    total = len(trades)
    wins = [t for t in trades if t.profit > 0]
    losses = [t for t in trades if t.profit <= 0]
    net = sum(t.net_profit for t in trades)

    gross_win = sum(t.profit for t in wins) if wins else 0
    gross_loss = abs(sum(t.profit for t in losses)) if losses else 0
    pf = gross_win / gross_loss if gross_loss > 0 else 999.99

    # Duration stats
    durations = [t.duration_minutes for t in trades]

    return {
        "total_trades": total,
        "net_profit": round(net, 2),
        "profit_factor": round(pf, 4),
        "win_rate": round(len(wins) / total * 100, 1),
        "avg_win": round(statistics.mean(t.profit for t in wins), 2) if wins else 0,
        "avg_loss": round(statistics.mean(t.profit for t in losses), 2) if losses else 0,
        "avg_net_per_trade": round(net / total, 2),
        "commission_total": round(sum(t.commission for t in trades), 2),
        "swap_total": round(sum(t.swap for t in trades), 2),
        "avg_duration_min": round(statistics.mean(durations), 0),
        "median_duration_min": round(statistics.median(durations), 0),
        "years_covered": sorted(set(t.year for t in trades)),
        "close_reason_breakdown": analyze_close_reasons(trades),
    }


# ============================================================
# CSV Export
# ============================================================

def write_trade_csv(trades: List[EnhancedTrade], path: Path):
    """Write per-trade CSV for external analysis."""
    if not trades:
        return

    fields = [
        "ticket", "entry_time", "exit_time", "side", "entry_price", "exit_price",
        "volume", "profit", "commission", "swap", "net_profit", "pips",
        "duration_minutes", "close_reason", "year", "month", "hour", "day_of_week",
        "entry_comment", "exit_comment",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for t in trades:
            row = {
                "ticket": t.ticket,
                "entry_time": t.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": t.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "side": t.side,
                "entry_price": f"{t.entry_price:.5f}",
                "exit_price": f"{t.exit_price:.5f}",
                "volume": f"{t.volume:.2f}",
                "profit": f"{t.profit:.2f}",
                "commission": f"{t.commission:.2f}",
                "swap": f"{t.swap:.2f}",
                "net_profit": f"{t.net_profit:.2f}",
                "pips": f"{t.pips:.1f}",
                "duration_minutes": f"{t.duration_minutes:.0f}",
                "close_reason": t.close_reason,
                "year": t.year,
                "month": t.month,
                "hour": t.hour,
                "day_of_week": t.day_of_week,
                "entry_comment": t.entry_comment,
                "exit_comment": t.exit_comment,
            }
            writer.writerow(row)


# ============================================================
# Chart generation
# ============================================================

def plot_trade_quality(trades: List[EnhancedTrade], out_dir: Path):
    """Generate trade quality chart pack."""
    if not HAS_MPL or not trades:
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Phoenix Trade Quality Analysis", fontsize=14, fontweight="bold")

    # 1. Equity curve with underwater shading
    ax = axes[0, 0]
    equity = START_EQUITY
    eq_times = []
    eq_values = []
    peak = equity
    for t in trades:
        equity += t.net_profit
        eq_times.append(t.exit_time)
        eq_values.append(equity)
        peak = max(peak, equity)

    ax.plot(eq_times, eq_values, "b-", linewidth=0.8, label="Equity")
    ax.set_title("Equity Curve")
    ax.set_ylabel("$")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 2. Profit by hour
    ax = axes[0, 1]
    hour_pnl = defaultdict(float)
    hour_count = defaultdict(int)
    for t in trades:
        hour_pnl[t.hour] += t.net_profit
        hour_count[t.hour] += 1
    hours = sorted(hour_pnl.keys())
    colors = ["green" if hour_pnl[h] >= 0 else "red" for h in hours]
    ax.bar(hours, [hour_pnl[h] for h in hours], color=colors, alpha=0.7)
    ax.set_title("Net Profit by Entry Hour")
    ax.set_xlabel("Hour (server time)")
    ax.set_ylabel("$")
    ax.grid(True, alpha=0.3)

    # 3. Close reason pie
    ax = axes[1, 0]
    reasons = analyze_close_reasons(trades)
    labels = list(reasons.keys())
    sizes = [reasons[r]["count"] for r in labels]
    if sizes:
        ax.pie(sizes, labels=labels, autopct="%1.0f%%", startangle=90)
    ax.set_title("Close Reasons")

    # 4. Monthly PnL heatmap (year vs month)
    ax = axes[1, 1]
    monthly = defaultdict(float)
    for t in trades:
        monthly[(t.year, t.month)] += t.net_profit
    years = sorted(set(k[0] for k in monthly.keys()))
    months = list(range(1, 13))
    data = []
    for y in years:
        row = [monthly.get((y, m), 0) for m in months]
        data.append(row)
    if data:
        im = ax.imshow(data, cmap="RdYlGn", aspect="auto")
        ax.set_yticks(range(len(years)))
        ax.set_yticklabels(years)
        ax.set_xticks(range(12))
        ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], fontsize=7)
        ax.set_title("Monthly P&L Heatmap")
        plt.colorbar(im, ax=ax, shrink=0.8)

    plt.tight_layout()
    plt.savefig(out_dir / "trade_quality.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[trade_quality] Chart saved: {out_dir / 'trade_quality.png'}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Phoenix Trade Quality Analyzer")
    parser.add_argument("--report", required=True, help="MT5 report file (HTML)")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--charts", action="store_true", help="Generate charts")
    args = parser.parse_args()

    report_path = Path(args.report)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[trade_quality] Parsing: {report_path}")
    deals = parse_deals(report_path)
    print(f"[trade_quality] Deals: {len(deals)}")

    trades = deals_to_enhanced_trades(deals)
    print(f"[trade_quality] Trades: {len(trades)}")

    if not trades:
        print("[trade_quality] ERROR: No trades found")
        return

    # 1. Trade quality CSV
    csv_path = out_dir / "trade_quality.csv"
    write_trade_csv(trades, csv_path)
    print(f"[trade_quality] CSV: {csv_path} ({len(trades)} trades)")

    # 2. Close reasons
    close_reasons = analyze_close_reasons(trades)
    with open(out_dir / "close_reasons.json", "w") as f:
        json.dump(close_reasons, f, indent=2)
    print(f"[trade_quality] Close reasons: {list(close_reasons.keys())}")

    # 3. Duration analysis
    duration = analyze_duration(trades)
    with open(out_dir / "duration_analysis.json", "w") as f:
        json.dump(duration, f, indent=2)

    # 4. Streak analysis
    streaks = analyze_streaks(trades)
    with open(out_dir / "streak_analysis.json", "w") as f:
        json.dump(streaks, f, indent=2, default=str)
    print(f"[trade_quality] Max loss streak: {streaks.get('max_loss_streak', 0)}")

    # 5. Pain clusters
    clusters = analyze_pain_clusters(trades)
    with open(out_dir / "pain_clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)
    print(f"[trade_quality] Pain clusters: {len(clusters)}")

    # 6. Summary
    summary = generate_summary(trades)
    with open(out_dir / "trade_quality_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[trade_quality] Summary: PF={summary['profit_factor']}, WR={summary['win_rate']}%, "
          f"Net=${summary['net_profit']}")

    # 7. Charts
    if args.charts:
        plot_trade_quality(trades, out_dir)

    print(f"[trade_quality] DONE. Output: {out_dir}")


if __name__ == "__main__":
    main()
