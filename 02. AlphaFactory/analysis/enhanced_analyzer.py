#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Quant Analyzer for Heroic EA
=====================================
Extends heroic_quant_analyzer.py with:
- Session breakdown (Asia/Europe/NY)
- Hour-of-day / Day-of-week analysis
- Streak analysis (consecutive wins/losses)
- Weakness detection
- Visual charts (matplotlib)
- Auto-recommendations

Usage:
  python enhanced_analyzer.py --report "path/to/report.html" --charts
"""

import argparse
import csv
import json
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

# Import from existing analyzer
from quant_analyzer import (
    parse_deals, deals_to_trades, Trade, Deal,
    compute_max_drawdown, profit_factor, bucket_stats,
    file_fingerprint, percentile
)

# Try matplotlib for charts
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def get_session(hour: int) -> str:
    """Determine trading session from UTC hour"""
    if 0 <= hour < 8:
        return "Asia"
    elif 8 <= hour < 14:
        return "Europe"
    elif 14 <= hour < 21:
        return "NewYork"
    else:
        return "OffHours"


def analyze_by_session(trades: List[Trade]) -> Dict[str, dict]:
    """Breakdown by trading session"""
    buckets = defaultdict(list)
    for t in trades:
        session = get_session(t.entry_time.hour)
        buckets[session].append(t)
    
    results = {}
    for session in ["Asia", "Europe", "NewYork", "OffHours"]:
        if session in buckets:
            results[session] = bucket_stats(buckets[session])
        else:
            results[session] = {"n": 0, "net_profit": 0, "profit_factor": 0, "win_rate_pct": 0}
    return results


def analyze_by_hour(trades: List[Trade]) -> Dict[int, dict]:
    """Breakdown by hour of day (entry time)"""
    buckets = defaultdict(list)
    for t in trades:
        buckets[t.entry_time.hour].append(t)
    
    results = {}
    for hour in range(24):
        if hour in buckets:
            results[hour] = bucket_stats(buckets[hour])
        else:
            results[hour] = {"n": 0, "net_profit": 0, "profit_factor": 0, "win_rate_pct": 0}
    return results


def analyze_by_weekday(trades: List[Trade]) -> Dict[str, dict]:
    """Breakdown by day of week"""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    buckets = defaultdict(list)
    for t in trades:
        day = days[t.entry_time.weekday()]
        buckets[day].append(t)
    
    results = {}
    for day in days:
        if day in buckets:
            results[day] = bucket_stats(buckets[day])
        else:
            results[day] = {"n": 0, "net_profit": 0, "profit_factor": 0, "win_rate_pct": 0}
    return results


def analyze_streaks(trades: List[Trade]) -> dict:
    """Analyze winning/losing streaks"""
    if not trades:
        return {"max_win_streak": 0, "max_loss_streak": 0, "current_streak": 0}
    
    max_win = 0
    max_loss = 0
    current = 0
    prev_win = None
    
    for t in trades:
        is_win = t.profit > 0
        if prev_win is None:
            current = 1
        elif is_win == prev_win:
            current += 1
        else:
            if prev_win:
                max_win = max(max_win, current)
            else:
                max_loss = max(max_loss, current)
            current = 1
        prev_win = is_win
    
    # Final streak
    if prev_win:
        max_win = max(max_win, current)
    else:
        max_loss = max(max_loss, current)
    
    return {
        "max_win_streak": max_win,
        "max_loss_streak": max_loss,
        "current_streak": current if prev_win else -current,
        "current_streak_type": "win" if prev_win else "loss"
    }


def detect_weaknesses(trades: List[Trade], by_session: dict, by_hour: dict, 
                      by_weekday: dict, by_year: List[dict]) -> List[dict]:
    """Detect strategy weaknesses and generate recommendations"""
    weaknesses = []
    
    # 1. Session weaknesses
    for session, stats in by_session.items():
        if stats["n"] >= 20:  # Minimum sample
            if stats["profit_factor"] < 0.9:
                weaknesses.append({
                    "type": "session",
                    "severity": "HIGH",
                    "area": session,
                    "metric": f"PF={stats['profit_factor']:.2f}",
                    "trades": stats["n"],
                    "recommendation": f"Consider disabling {session} session trading"
                })
            elif stats["profit_factor"] < 1.0:
                weaknesses.append({
                    "type": "session",
                    "severity": "MEDIUM",
                    "area": session,
                    "metric": f"PF={stats['profit_factor']:.2f}",
                    "trades": stats["n"],
                    "recommendation": f"Monitor {session} session closely"
                })
    
    # 2. Hour weaknesses
    bad_hours = []
    for hour, stats in by_hour.items():
        if stats["n"] >= 10 and stats["profit_factor"] < 0.8:
            bad_hours.append(hour)
    if bad_hours:
        weaknesses.append({
            "type": "hour",
            "severity": "MEDIUM",
            "area": f"Hours {bad_hours}",
            "metric": "PF < 0.8",
            "trades": sum(by_hour[h]["n"] for h in bad_hours),
            "recommendation": f"Avoid trading at hours: {bad_hours}"
        })
    
    # 3. Weekday weaknesses
    for day, stats in by_weekday.items():
        if stats["n"] >= 20 and stats["profit_factor"] < 0.9:
            weaknesses.append({
                "type": "weekday",
                "severity": "MEDIUM",
                "area": day,
                "metric": f"PF={stats['profit_factor']:.2f}",
                "trades": stats["n"],
                "recommendation": f"Review {day} trading rules"
            })
    
    # 4. Yearly regime weaknesses
    for year_stats in by_year:
        if year_stats["n"] >= 30 and year_stats["profit_factor"] < 0.9:
            weaknesses.append({
                "type": "year",
                "severity": "HIGH",
                "area": str(year_stats.get("year", "Unknown")),
                "metric": f"PF={year_stats['profit_factor']:.2f}, Net={year_stats['net_profit']:.0f}",
                "trades": year_stats["n"],
                "recommendation": f"Strategy struggled in {year_stats.get('year')} - review market regime"
            })
    
    # 5. Overall edge check
    all_profits = [t.profit for t in trades]
    pf = profit_factor(trades)
    if pf < 1.05:
        weaknesses.append({
            "type": "overall",
            "severity": "CRITICAL",
            "area": "Strategy Edge",
            "metric": f"PF={pf:.2f}",
            "trades": len(trades),
            "recommendation": "Strategy has minimal/no edge. Consider fundamental changes."
        })
    
    return sorted(weaknesses, key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[x["severity"]])


def generate_charts(trades: List[Trade], out_dir: Path, start_equity: float):
    """Generate visual charts using matplotlib"""
    if not HAS_MATPLOTLIB:
        print("WARNING: matplotlib not installed. Skipping charts.")
        return
    
    # 1. Equity Curve
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Equity curve
    ax1 = axes[0, 0]
    equity = [start_equity]
    dates = [trades[0].entry_time if trades else datetime.now()]
    for t in trades:
        equity.append(equity[-1] + t.profit)
        dates.append(t.exit_time)
    ax1.plot(dates, equity, 'b-', linewidth=0.8)
    ax1.fill_between(dates, start_equity, equity, alpha=0.3)
    ax1.set_title('Equity Curve')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Equity ($)')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True, alpha=0.3)
    
    # Drawdown
    ax2 = axes[0, 1]
    peak = equity[0]
    dd = []
    for e in equity:
        peak = max(peak, e)
        dd.append((e - peak) / peak * 100 if peak > 0 else 0)
    ax2.fill_between(dates, 0, dd, color='red', alpha=0.5)
    ax2.set_title('Drawdown %')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Drawdown %')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(True, alpha=0.3)
    
    # Profit distribution
    ax3 = axes[1, 0]
    profits = [t.profit for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    ax3.hist(profits, bins=50, color='gray', alpha=0.7, edgecolor='black')
    ax3.axvline(x=0, color='red', linestyle='--', linewidth=2)
    ax3.set_title(f'Profit Distribution (W:{len(wins)} L:{len(losses)})')
    ax3.set_xlabel('Profit ($)')
    ax3.set_ylabel('Frequency')
    ax3.grid(True, alpha=0.3)
    
    # Session performance
    ax4 = axes[1, 1]
    by_session = analyze_by_session(trades)
    sessions = ["Asia", "Europe", "NewYork", "OffHours"]
    pfs = [by_session[s]["profit_factor"] if by_session[s]["n"] > 0 else 0 for s in sessions]
    counts = [by_session[s]["n"] for s in sessions]
    colors = ['green' if pf > 1 else 'red' for pf in pfs]
    bars = ax4.bar(sessions, pfs, color=colors, alpha=0.7)
    ax4.axhline(y=1.0, color='black', linestyle='--', linewidth=1)
    ax4.set_title('Profit Factor by Session')
    ax4.set_ylabel('Profit Factor')
    for bar, count in zip(bars, counts):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                f'n={count}', ha='center', va='bottom', fontsize=8)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(out_dir / "analysis_charts.png", dpi=150)
    plt.close()
    
    # 2. Hour heatmap
    fig, ax = plt.subplots(figsize=(12, 4))
    by_hour = analyze_by_hour(trades)
    hours = list(range(24))
    pfs = [by_hour[h]["profit_factor"] if by_hour[h]["n"] > 0 else 1.0 for h in hours]
    counts = [by_hour[h]["n"] for h in hours]
    colors = ['green' if pf > 1 else 'red' if pf < 1 else 'gray' for pf in pfs]
    bars = ax.bar(hours, pfs, color=colors, alpha=0.7)
    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1)
    ax.set_title('Profit Factor by Hour (UTC)')
    ax.set_xlabel('Hour')
    ax.set_ylabel('Profit Factor')
    ax.set_xticks(hours)
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                    f'{count}', ha='center', va='bottom', fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(out_dir / "hour_analysis.png", dpi=150)
    plt.close()
    
    print(f"Charts saved to {out_dir}")


def generate_text_report(summary: dict, weaknesses: List[dict], 
                         by_session: dict, by_hour: dict, 
                         by_weekday: dict, streaks: dict,
                         out_dir: Path):
    """Generate human-readable analysis report"""
    lines = []
    lines.append("=" * 60)
    lines.append("HEROIC EA - ENHANCED ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Overall Summary
    lines.append("## OVERALL PERFORMANCE")
    lines.append("-" * 40)
    lines.append(f"Trades: {summary.get('n_trades', 0)}")
    lines.append(f"Net Profit: ${summary.get('net_profit', 0):.2f}")
    lines.append(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")
    lines.append(f"Win Rate: {summary.get('win_rate_pct', 0):.1f}%")
    lines.append(f"Max Drawdown: {summary.get('max_drawdown_pct', 0):.1f}%")
    lines.append(f"Expectancy: ${summary.get('expectancy_per_trade', 0):.2f}/trade")
    lines.append("")
    
    # Streaks
    lines.append("## STREAK ANALYSIS")
    lines.append("-" * 40)
    lines.append(f"Max Winning Streak: {streaks['max_win_streak']} trades")
    lines.append(f"Max Losing Streak: {streaks['max_loss_streak']} trades")
    lines.append(f"Current Streak: {abs(streaks['current_streak'])} ({streaks['current_streak_type']})")
    lines.append("")
    
    # Session breakdown
    lines.append("## SESSION BREAKDOWN")
    lines.append("-" * 40)
    lines.append(f"{'Session':<12} {'Trades':>8} {'Net':>12} {'PF':>8} {'WinRate':>10}")
    for session in ["Asia", "Europe", "NewYork", "OffHours"]:
        s = by_session.get(session, {})
        lines.append(f"{session:<12} {s.get('n', 0):>8} {s.get('net_profit', 0):>12.0f} "
                    f"{s.get('profit_factor', 0):>8.2f} {s.get('win_rate_pct', 0):>9.1f}%")
    lines.append("")
    
    # Weekday breakdown
    lines.append("## WEEKDAY BREAKDOWN")
    lines.append("-" * 40)
    lines.append(f"{'Day':<12} {'Trades':>8} {'Net':>12} {'PF':>8} {'WinRate':>10}")
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        s = by_weekday.get(day, {})
        lines.append(f"{day:<12} {s.get('n', 0):>8} {s.get('net_profit', 0):>12.0f} "
                    f"{s.get('profit_factor', 0):>8.2f} {s.get('win_rate_pct', 0):>9.1f}%")
    lines.append("")
    
    # Weaknesses
    lines.append("## WEAKNESS DETECTION")
    lines.append("-" * 40)
    if not weaknesses:
        lines.append("✅ No significant weaknesses detected")
    else:
        for w in weaknesses:
            emoji = "🔴" if w["severity"] == "CRITICAL" else "🟠" if w["severity"] == "HIGH" else "🟡"
            lines.append(f"{emoji} [{w['severity']}] {w['type'].upper()}: {w['area']}")
            lines.append(f"   Metric: {w['metric']} (n={w['trades']})")
            lines.append(f"   → {w['recommendation']}")
            lines.append("")
    
    # Recommendations
    lines.append("## RECOMMENDATIONS")
    lines.append("-" * 40)
    
    pf = summary.get('profit_factor', 0)
    if pf < 1.0:
        lines.append("🔴 CRITICAL: Strategy is losing money. Do NOT trade live.")
        lines.append("   - Review entry logic fundamentally")
        lines.append("   - Consider different strategy type (mean reversion?)")
    elif pf < 1.1:
        lines.append("🟠 WARNING: Minimal edge. High risk for live trading.")
        lines.append("   - Reduce position size significantly")
        lines.append("   - Add meaningful filters")
    elif pf < 1.3:
        lines.append("🟡 CAUTION: Moderate edge. Proceed with care.")
        lines.append("   - Start with small live test")
        lines.append("   - Monitor drawdowns closely")
    else:
        lines.append("🟢 GOOD: Solid edge detected.")
        lines.append("   - Validate with walk-forward analysis")
        lines.append("   - Check for overfitting")
    
    lines.append("")
    lines.append("=" * 60)
    
    report_text = "\n".join(lines)
    (out_dir / "analysis_report.txt").write_text(report_text, encoding="utf-8")
    # v11.0 FIX: Handle Windows cp1252 console encoding for emoji/unicode
    try:
        print(report_text)
    except UnicodeEncodeError:
        print(report_text.encode("ascii", errors="replace").decode("ascii"))
    return report_text


def main():
    ap = argparse.ArgumentParser(description="Enhanced Quant Analyzer for Heroic EA")
    ap.add_argument("--report", required=True, help="Path to MT5 report")
    ap.add_argument("--out", default="", help="Output directory")
    ap.add_argument("--charts", action="store_true", help="Generate visual charts")
    args = ap.parse_args()
    
    report_path = Path(args.report)
    if not report_path.exists():
        raise SystemExit(f"Report not found: {report_path}")
    
    out_dir = Path(args.out) if args.out else (report_path.parent / "enhanced_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse data
    deals = parse_deals(report_path)
    trades = deals_to_trades(deals)
    
    if not trades:
        raise SystemExit("No trades found in report")
    
    # Get start equity
    # v11.0 FIX: Case-insensitive balance detection (MT5 locale may return "Balance")
    start_equity = next((d.balance for d in deals if (d.side or "").strip().lower() == "balance" and d.balance > 0), 10000)
    
    # Run analyses
    by_session = analyze_by_session(trades)
    by_hour = analyze_by_hour(trades)
    by_weekday = analyze_by_weekday(trades)
    streaks = analyze_streaks(trades)
    
    # Yearly stats for weakness detection
    yearly_buckets = defaultdict(list)
    for t in trades:
        yearly_buckets[t.exit_time.year].append(t)
    by_year = []
    for year, ts in sorted(yearly_buckets.items()):
        stats = bucket_stats(ts)
        stats["year"] = year
        by_year.append(stats)
    
    # Compute summary
    trade_profits = [t.profit for t in trades]
    final_equity = start_equity + sum(trade_profits)
    wins = [p for p in trade_profits if p > 0]
    losses = [p for p in trade_profits if p < 0]
    
    equity_curve = []
    cur = start_equity
    for p in trade_profits:
        cur += p
        equity_curve.append(cur)
    dd_abs, dd_pct = compute_max_drawdown(equity_curve)
    
    summary = {
        "n_trades": len(trades),
        "net_profit": final_equity - start_equity,
        "profit_factor": profit_factor(trades),
        "win_rate_pct": (len(wins) / len(trade_profits) * 100) if trade_profits else 0,
        "avg_win": sum(wins) / len(wins) if wins else 0,
        "avg_loss": sum(losses) / len(losses) if losses else 0,
        "max_drawdown_pct": dd_pct,
        "max_drawdown_abs": dd_abs,
        "expectancy_per_trade": sum(trade_profits) / len(trade_profits) if trade_profits else 0,
        "start_equity": start_equity,
        "final_equity": final_equity,
    }
    
    # Detect weaknesses
    weaknesses = detect_weaknesses(trades, by_session, by_hour, by_weekday, by_year)
    
    # Save outputs
    # Session CSV
    with open(out_dir / "by_session.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["session", "n", "net_profit", "profit_factor", "win_rate_pct", "avg_win", "avg_loss"])
        for session in ["Asia", "Europe", "NewYork", "OffHours"]:
            s = by_session[session]
            w.writerow([session, s.get("n", 0), f"{s.get('net_profit', 0):.2f}", f"{s.get('profit_factor', 0):.2f}",
                       f"{s.get('win_rate_pct', 0):.1f}", f"{s.get('avg_win', 0):.2f}", f"{s.get('avg_loss', 0):.2f}"])
    
    # Hour CSV
    with open(out_dir / "by_hour.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hour", "n", "net_profit", "profit_factor", "win_rate_pct"])
        for hour in range(24):
            s = by_hour[hour]
            w.writerow([hour, s.get("n", 0), f"{s.get('net_profit', 0):.2f}", f"{s.get('profit_factor', 0):.2f}",
                       f"{s.get('win_rate_pct', 0):.1f}"])
    
    # Weekday CSV
    with open(out_dir / "by_weekday.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["weekday", "n", "net_profit", "profit_factor", "win_rate_pct"])
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            s = by_weekday[day]
            w.writerow([day, s.get("n", 0), f"{s.get('net_profit', 0):.2f}", f"{s.get('profit_factor', 0):.2f}",
                       f"{s.get('win_rate_pct', 0):.1f}"])
    
    # Weaknesses JSON
    with open(out_dir / "weaknesses.json", "w", encoding="utf-8") as f:
        json.dump(weaknesses, f, indent=2, ensure_ascii=False)
    
    # Summary JSON
    summary["streaks"] = streaks
    summary["weaknesses_count"] = len(weaknesses)
    with open(out_dir / "enhanced_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Generate charts
    if args.charts:
        generate_charts(trades, out_dir, start_equity)
    
    # Generate text report
    generate_text_report(summary, weaknesses, by_session, by_hour, by_weekday, streaks, out_dir)
    
    print(f"\nOutputs saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
