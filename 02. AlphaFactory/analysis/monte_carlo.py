#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
Monte Carlo Simulation for Strategy Robustness
===============================================
Validates strategy by shuffling trade order and measuring risk.

Usage:
  python monte_carlo.py --report "path/to/report.html" --sims 1000
"""

import argparse
import json
import random
from pathlib import Path
from typing import List
import statistics

from quant_analyzer import parse_deals, deals_to_trades, Trade


DEFAULT_RANDOM_SEED = 1729


def monte_carlo_equity(
    trades: List[Trade],
    start_equity: float,
    n_sims: int = 1000,
    seed: int = DEFAULT_RANDOM_SEED,
) -> dict:
    """
    Run Monte Carlo simulation by shuffling trade order.
    
    Returns distribution of:
    - Final equity
    - Max drawdown
    - Worst drawdown
    """
    if n_sims <= 0:
        raise ValueError("n_sims must be positive")
    if not trades:
        raise ValueError("at least one completed trade is required")

    profits = [t.profit for t in trades]
    rng = random.Random(seed)
    
    final_equities = []
    max_drawdowns = []
    worst_equity = []
    
    for _ in range(n_sims):
        # Shuffle trades
        shuffled = profits.copy()
        rng.shuffle(shuffled)
        
        # Simulate equity curve
        equity = start_equity
        peak = equity
        max_dd = 0
        min_equity = equity
        
        for p in shuffled:
            equity += p
            peak = max(peak, equity)
            dd = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            min_equity = min(min_equity, equity)
        
        final_equities.append(equity)
        max_drawdowns.append(max_dd * 100)
        worst_equity.append(min_equity)
    
    # Calculate percentiles
    final_equities.sort()
    max_drawdowns.sort()
    worst_equity.sort()
    
    def percentile(data, p):
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]
    
    return {
        "n_simulations": n_sims,
        "n_trades": len(trades),
        "start_equity": start_equity,
        "random_seed": seed,
        
        # Final equity distribution
        "final_equity": {
            "mean": statistics.mean(final_equities),
            "std": statistics.stdev(final_equities) if len(final_equities) > 1 else 0,
            "median": statistics.median(final_equities),
            "p5": percentile(final_equities, 5),
            "p25": percentile(final_equities, 25),
            "p75": percentile(final_equities, 75),
            "p95": percentile(final_equities, 95),
            "min": min(final_equities),
            "max": max(final_equities),
        },
        
        # Max drawdown distribution
        "max_drawdown_pct": {
            "mean": statistics.mean(max_drawdowns),
            "median": statistics.median(max_drawdowns),
            "p50": percentile(max_drawdowns, 50),
            "p75": percentile(max_drawdowns, 75),
            "p95": percentile(max_drawdowns, 95),  # 95% worst case
            "p99": percentile(max_drawdowns, 99),  # Extreme case
            "max": max(max_drawdowns),
        },
        
        # Risk metrics — v11.2 FIX: Use worst_equity (min equity during sim),
        # not final_equities. A sim that drops 60% then recovers must count as ruin.
        "risk_of_ruin": {
            "prob_lose_50pct": sum(1 for w in worst_equity if w < start_equity * 0.5) / n_sims,
            "prob_lose_25pct": sum(1 for w in worst_equity if w < start_equity * 0.75) / n_sims,
            "prob_breakeven": sum(1 for w in worst_equity if w < start_equity) / n_sims,
        },
        
        # Worst case scenarios
        "worst_case": {
            "worst_final_equity": min(final_equities),
            "worst_drawdown_pct": max(max_drawdowns),
            "worst_equity_ever": min(worst_equity),
        }
    }


def print_monte_carlo_report(results: dict):
    """Print formatted Monte Carlo report"""
    print("\n" + "=" * 60)
    print("MONTE CARLO SIMULATION REPORT")
    print("=" * 60)
    print(f"Simulations: {results['n_simulations']:,}")
    print(f"Trades: {results['n_trades']}")
    print(f"Start Equity: ${results['start_equity']:,.2f}")
    
    print("\n## FINAL EQUITY DISTRIBUTION")
    print("-" * 40)
    fe = results['final_equity']
    print(f"  Mean:      ${fe['mean']:,.2f}")
    print(f"  Median:    ${fe['median']:,.2f}")
    print(f"  Std Dev:   ${fe['std']:,.2f}")
    print(f"  5th pct:   ${fe['p5']:,.2f}")
    print(f"  95th pct:  ${fe['p95']:,.2f}")
    print(f"  Range:     ${fe['min']:,.2f} - ${fe['max']:,.2f}")
    
    print("\n## MAX DRAWDOWN DISTRIBUTION")
    print("-" * 40)
    dd = results['max_drawdown_pct']
    print(f"  Mean:      {dd['mean']:.1f}%")
    print(f"  Median:    {dd['median']:.1f}%")
    print(f"  75th pct:  {dd['p75']:.1f}%")
    print(f"  95th pct:  {dd['p95']:.1f}%  ← EXPECT THIS DD")
    print(f"  99th pct:  {dd['p99']:.1f}%  ← Extreme case")
    print(f"  Worst:     {dd['max']:.1f}%")
    
    print("\n## RISK OF RUIN")
    print("-" * 40)
    ror = results['risk_of_ruin']
    print(f"  P(Lose 50%+):    {ror['prob_lose_50pct']:.1%}")
    print(f"  P(Lose 25%+):    {ror['prob_lose_25pct']:.1%}")
    print(f"  P(Below start):  {ror['prob_breakeven']:.1%}")
    
    print("\n## WORST CASE SCENARIOS")
    print("-" * 40)
    wc = results['worst_case']
    print(f"  Worst final equity: ${wc['worst_final_equity']:,.2f}")
    print(f"  Worst drawdown:     {wc['worst_drawdown_pct']:.1f}%")
    print(f"  Lowest equity ever: ${wc['worst_equity_ever']:,.2f}")
    
    # Recommendations
    print("\n## RECOMMENDATIONS")
    print("-" * 40)
    
    dd_95 = dd['p95']
    if dd_95 > 40:
        print("🔴 CRITICAL: 95th percentile DD > 40%. Very risky strategy.")
        print("   → Risk diagnostic fails; do not promote from this result")
    elif dd_95 > 25:
        print("🟠 WARNING: 95th percentile DD > 25%. Moderate risk.")
        print("   → Risk diagnostic is outside the current promotion budget")
    elif dd_95 > 15:
        print("🟡 CAUTION: 95th percentile DD > 15%.")
        print("   → Treat as risk evidence only; no sizing or deployment authorization")
    else:
        print("🟢 LOWER PATH RISK: 95th percentile DD < 15% in this simulation.")
        print("   → Still requires validate-full and all promotion gates; do not increase size from Monte Carlo alone")
    
    if ror['prob_lose_50pct'] > 0.01:
        print(f"\n⚠️  {ror['prob_lose_50pct']:.1%} chance of losing 50%+ of account!")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo Simulation")
    parser.add_argument("--report", required=True, help="Path to MT5 HTML report")
    parser.add_argument("--sims", type=int, default=1000, help="Number of simulations")
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED, help="Deterministic random seed")
    parser.add_argument("--equity", type=float, default=10000, help="Starting equity")
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
    
    if len(trades) < 30:
        print(f"WARNING: Only {len(trades)} trades. Monte Carlo less reliable.")
    
    # Get starting equity from deals if available
    start_equity = args.equity
    for d in deals:
        if (d.side or "").strip().lower() == "balance" and d.balance > 0:  # v11.0 FIX: case-insensitive
            start_equity = d.balance
            break
    
    # Run simulation
    print(f"Running {args.sims} Monte Carlo simulations...")
    results = monte_carlo_equity(trades, start_equity, args.sims, seed=args.seed)
    
    if not args.quiet:
        print_monte_carlo_report(results)
    
    # Save results
    if args.out:
        out_dir = Path(args.out)
    else:
        out_dir = report_path.parent / "monte_carlo"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "monte_carlo_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
