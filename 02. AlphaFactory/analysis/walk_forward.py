#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Walk-Forward Analysis
=====================
Validates strategy by splitting data into IS (in-sample) and OOS (out-of-sample).
Detects overfitting by comparing IS vs OOS performance.

Usage:
  python walk_forward.py --report "path/to/report.html" --windows 5
"""

import argparse
import json
from pathlib import Path
from typing import List
from datetime import datetime
from collections import defaultdict

from quant_analyzer import parse_deals, deals_to_trades, Trade, profit_factor, bucket_stats


ANALYSIS_KIND = "fixed_parameter_temporal_slicing"
QUARANTINE_REASON = (
    "This diagnostic applies one already-fixed strategy to chronological slices; "
    "it performs no per-window parameter optimization or locked OOS re-test."
)


def walk_forward_analysis(trades: List[Trade], n_windows: int = 5, is_ratio: float = 0.7) -> dict:
    """
    Perform walk-forward analysis.
    
    Args:
        trades: List of trades sorted by time
        n_windows: Number of walk-forward windows
        is_ratio: Ratio of In-Sample to total window (0.7 = 70% IS, 30% OOS)
    
    Returns:
        Dict with WFA results
    """
    if len(trades) < n_windows * 20:
        return {
            "analysis_kind": ANALYSIS_KIND,
            "promotion_eligible": False,
            "promotion_status": "DIAGNOSTIC_ONLY",
            "quarantine_reason": QUARANTINE_REASON,
            "error": f"Not enough trades ({len(trades)}) for {n_windows} windows",
        }
    
    # Sort by exit time
    sorted_trades = sorted(trades, key=lambda t: t.exit_time)
    
    # Calculate window size
    window_size = len(sorted_trades) // n_windows
    is_size = int(window_size * is_ratio)
    oos_size = window_size - is_size
    
    results = []
    
    for i in range(n_windows):
        start_idx = i * window_size
        is_end_idx = start_idx + is_size
        oos_end_idx = start_idx + window_size
        
        # Handle last window
        if i == n_windows - 1:
            oos_end_idx = len(sorted_trades)
        
        is_trades = sorted_trades[start_idx:is_end_idx]
        oos_trades = sorted_trades[is_end_idx:oos_end_idx]
        
        if not is_trades or not oos_trades:
            continue
        
        is_stats = bucket_stats(is_trades)
        oos_stats = bucket_stats(oos_trades)
        
        # v11.0 FIX: Cap PF to avoid NaN from inf / inf
        # bucket_stats returns float("inf") when no losing trades exist
        PF_CAP = 999.99
        is_pf = min(is_stats.get("profit_factor", 1), PF_CAP)
        oos_pf = min(oos_stats.get("profit_factor", 1), PF_CAP)
        
        degradation = (is_pf - oos_pf) / is_pf * 100 if is_pf > 0 else 0
        
        results.append({
            "window": i + 1,
            "period": {
                "is_start": is_trades[0].entry_time.isoformat(),
                "is_end": is_trades[-1].exit_time.isoformat(),
                "oos_start": oos_trades[0].entry_time.isoformat(),
                "oos_end": oos_trades[-1].exit_time.isoformat(),
            },
            "in_sample": {
                "trades": is_stats["n"],
                "profit_factor": round(is_pf, 2),
                "net_profit": round(is_stats.get("net_profit", 0), 2),
                "win_rate": round(is_stats.get("win_rate_pct", 0), 1),
            },
            "out_of_sample": {
                "trades": oos_stats["n"],
                "profit_factor": round(oos_pf, 2),
                "net_profit": round(oos_stats.get("net_profit", 0), 2),
                "win_rate": round(oos_stats.get("win_rate_pct", 0), 1),
            },
            "degradation_pct": round(degradation, 1),
            "oos_profitable": oos_pf > 1.0,
        })
    
    # Aggregate statistics
    is_pfs = [r["in_sample"]["profit_factor"] for r in results]
    oos_pfs = [r["out_of_sample"]["profit_factor"] for r in results]
    degradations = [r["degradation_pct"] for r in results]
    oos_profitable_count = sum(1 for r in results if r["oos_profitable"])
    
    # Calculate efficiency ratio (OOS PF / IS PF)
    avg_is_pf = sum(is_pfs) / len(is_pfs) if is_pfs else 0
    avg_oos_pf = sum(oos_pfs) / len(oos_pfs) if oos_pfs else 0
    efficiency_ratio = avg_oos_pf / avg_is_pf if avg_is_pf > 0 else 0
    
    return {
        "analysis_kind": ANALYSIS_KIND,
        "promotion_eligible": False,
        "promotion_status": "DIAGNOSTIC_ONLY",
        "quarantine_reason": QUARANTINE_REASON,
        "methodology": {
            "parameters_reoptimized_per_window": False,
            "oos_locked_after_optimization": False,
            "description": "Fixed-parameter chronological IS/OOS slicing only; not promotion-grade WFA.",
        },
        "n_windows": n_windows,
        "is_ratio": is_ratio,
        "total_trades": len(trades),
        "windows": results,
        "summary": {
            "avg_is_pf": round(avg_is_pf, 2),
            "avg_oos_pf": round(avg_oos_pf, 2),
            "avg_degradation_pct": round(sum(degradations) / len(degradations) if degradations else 0, 1),
            "oos_profitable_windows": oos_profitable_count,
            "oos_profitable_ratio": round(oos_profitable_count / len(results) if results else 0, 2),
            "efficiency_ratio": round(efficiency_ratio, 2),
        },
        "verdict": get_wfa_verdict(efficiency_ratio, oos_profitable_count, len(results)),
    }


def get_wfa_verdict(efficiency: float, oos_wins: int, total_windows: int) -> dict:
    """Describe the temporal-slice diagnostic without granting promotion power."""
    oos_ratio = oos_wins / total_windows if total_windows > 0 else 0
    
    if efficiency >= 0.8 and oos_ratio >= 0.8:
        return {
            "level": "EXCELLENT",
            "emoji": "🟢",
            "message": "Strategy shows strong robustness. Minimal overfitting detected.",
            "recommendation": "Diagnostic only. Run optimization-aware WFA before any promotion claim."
        }
    elif efficiency >= 0.6 and oos_ratio >= 0.6:
        return {
            "level": "GOOD",
            "emoji": "🟡",
            "message": "Strategy shows acceptable robustness with some degradation.",
            "recommendation": "Diagnostic only. Run optimization-aware WFA before any promotion claim."
        }
    elif efficiency >= 0.4 and oos_ratio >= 0.4:
        return {
            "level": "WARNING",
            "emoji": "🟠",
            "message": "Significant degradation detected. Possible overfitting.",
            "recommendation": "Review strategy logic; this fixed-parameter slice cannot support promotion."
        }
    else:
        return {
            "level": "POOR",
            "emoji": "🔴",
            "message": "Strategy fails OOS validation. Likely overfitted.",
            "recommendation": "Do NOT promote; fundamental redesign may be needed."
        }


def print_wfa_report(results: dict):
    """Print formatted WFA report"""
    print("\n" + "=" * 70)
    print("WALK-FORWARD ANALYSIS REPORT")
    print("=" * 70)
    print("STATUS: DIAGNOSTIC ONLY - FIXED-PARAMETER TEMPORAL SLICING")
    print(f"Reason: {results['quarantine_reason']}")
    print(f"Windows: {results['n_windows']} | IS/OOS Split: {results['is_ratio']:.0%}/{1-results['is_ratio']:.0%}")
    print(f"Total Trades: {results['total_trades']}")
    
    print("\n## WINDOW BREAKDOWN")
    print("-" * 70)
    print(f"{'Win':>4} | {'IS PF':>7} | {'IS Win%':>7} | {'OOS PF':>7} | {'OOS Win%':>8} | {'Degrad':>7} | Pass")
    print("-" * 70)
    
    for w in results["windows"]:
        is_data = w["in_sample"]
        oos_data = w["out_of_sample"]
        pass_mark = "✓" if w["oos_profitable"] else "✗"
        print(f"{w['window']:>4} | {is_data['profit_factor']:>7.2f} | {is_data['win_rate']:>6.1f}% | "
              f"{oos_data['profit_factor']:>7.2f} | {oos_data['win_rate']:>7.1f}% | "
              f"{w['degradation_pct']:>6.1f}% | {pass_mark}")
    
    print("-" * 70)
    
    # Summary
    s = results["summary"]
    print(f"\n## SUMMARY")
    print("-" * 40)
    print(f"  Avg IS Profit Factor:   {s['avg_is_pf']:.2f}")
    print(f"  Avg OOS Profit Factor:  {s['avg_oos_pf']:.2f}")
    print(f"  Avg Degradation:        {s['avg_degradation_pct']:.1f}%")
    print(f"  OOS Profitable Windows: {s['oos_profitable_windows']}/{results['n_windows']} ({s['oos_profitable_ratio']:.0%})")
    print(f"  Efficiency Ratio:       {s['efficiency_ratio']:.2f} (OOS PF / IS PF)")
    
    # Verdict
    v = results["verdict"]
    print(f"\n## VERDICT: {v['emoji']} {v['level']}")
    print("-" * 40)
    print(f"  {v['message']}")
    print(f"  → {v['recommendation']}")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Walk-Forward Analysis")
    parser.add_argument("--report", required=True, help="Path to MT5 HTML report")
    parser.add_argument("--windows", "-w", type=int, default=5, help="Number of WFA windows")
    parser.add_argument("--ratio", "-r", type=float, default=0.7, help="IS ratio (default 0.7)")
    parser.add_argument("--out", default="", help="Output directory")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    args = parser.parse_args()
    
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}")
        return 1
    
    # Parse trades
    deals = parse_deals(report_path)
    trades = deals_to_trades(deals)
    
    if len(trades) < 50:
        print(f"WARNING: Only {len(trades)} trades. WFA results may be unreliable.")
    
    # Run WFA
    print(f"Running Walk-Forward Analysis with {args.windows} windows...")
    results = walk_forward_analysis(trades, args.windows, args.ratio)
    
    if "error" in results:
        print(f"ERROR: {results['error']}")
        return 1
    
    if not args.quiet:
        print_wfa_report(results)
    
    # Save results
    if args.out:
        out_dir = Path(args.out)
    else:
        out_dir = report_path.parent / "walk_forward"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "wfa_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
