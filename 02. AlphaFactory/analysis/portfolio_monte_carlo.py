#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio-Level Monte Carlo Simulation
========================================
Combines trade streams from all 6 validated EA instances, scales P&L by
optimal-risk / current-risk ratios from portfolio_optimization_result.json,
then runs 10,000 shuffled-order simulations on the combined stream.

Outputs:
  - Console report
  - 02. AlphaFactory/analysis/portfolio_mc_result.json

Metrics reported:
  - Total trades, annualised trades/yr (8-yr backtest)
  - P50 / P95 / P99 max drawdown
  - Sharpe ratio (annualised, from daily P&L of median simulation path)
  - Calmar ratio (annual return / P95 DD)
  - P(positive year) across simulations
  - Prop-firm pass rate (8% profit target, 8% max-DD cap, 100-trade blocks)
"""

import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANALYSIS_DIR = Path(__file__).parent
BASE = ANALYSIS_DIR.parent          # AlphaFactory root
RUNS = BASE / "runs"

sys.path.insert(0, str(ANALYSIS_DIR))
from quant_analyzer import parse_deals, deals_to_trades, Trade

# ---------------------------------------------------------------------------
# Canonical EA definitions  (mirrors portfolio_optimizer.py EA_CONFIGS)
# ---------------------------------------------------------------------------
EA_CONFIGS = {
    "Cobra_XAUUSD": {
        "report": RUNS / "EA_Cobra"        / "20260402_221001" / "report.html",
        "current_risk": 0.42,
    },
    "SilverBullet_USDJPY": {
        "report": RUNS / "EA_SilverBullet" / "20260402_225249" / "report.html",
        "current_risk": 0.36,
    },
    "InsideBar_USDJPY": {
        "report": RUNS / "EA_InsideBar"    / "20260402_225507" / "report.html",
        "current_risk": 0.29,
    },
    "InsideBar_GBPUSD": {
        "report": RUNS / "EA_InsideBar"    / "20260329_092112" / "report.html",
        "current_risk": 0.42,
    },
    "ITSM_USDJPY": {
        "report": RUNS / "EA_ITSM"         / "20260405_000436" / "report.html",
        "current_risk": 0.26,
    },
    "LondonNY_USDJPY": {
        "report": RUNS / "EA_LondonNY"     / "20260403_012503" / "report.html",
        "current_risk": 0.36,
    },
}

BACKTEST_YEARS   = 8          # 2018-2026 window used across all EAs
START_EQUITY     = 10_000.0   # reference account size ($)
N_SIMS           = 10_000
PROP_TARGET_PCT  = 0.08       # 8% profit target
PROP_MAX_DD_PCT  = 0.08       # 8% max drawdown limit
PROP_BLOCK_SIZE  = 100        # trades per evaluation block


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_optimal_weights() -> Dict[str, float]:
    """Load optimal_weights from portfolio_optimization_result.json."""
    result_path = ANALYSIS_DIR / "portfolio_optimization_result.json"
    if not result_path.exists():
        raise FileNotFoundError(f"portfolio_optimization_result.json not found at {result_path}")
    with open(result_path) as f:
        data = json.load(f)
    return data["optimal_weights"]


def extract_trades(report_path: Path, ea_name: str) -> List[Trade]:
    if not report_path.exists():
        print(f"  [WARN] Report not found, skipping {ea_name}: {report_path}")
        return []
    deals = parse_deals(report_path)
    trades = deals_to_trades(deals)
    print(f"  {ea_name:28s}: {len(trades):4d} trades parsed")
    return trades


def scale_trades(trades: List[Trade], scale: float) -> List[float]:
    """Return list of scaled P&L values (float)."""
    return [t.profit * scale for t in trades]


def percentile(sorted_data: list, p: float) -> float:
    """p in [0,100]. sorted_data must already be sorted ascending."""
    if not sorted_data:
        return 0.0
    idx = p / 100.0 * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def simulate_equity_path(profits: List[float], start: float) -> Tuple[float, float, List[float]]:
    """
    Simulate one equity path.
    Returns (max_drawdown_pct, final_equity, daily_pnl_list).
    max_drawdown_pct is in [0, 100].
    daily_pnl_list holds per-trade increments (for Sharpe proxy).
    """
    equity = start
    peak   = start
    max_dd = 0.0

    for p in profits:
        equity += p
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100.0 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd, equity, profits   # pass-through profits for daily Sharpe


def compute_daily_sharpe(profits: List[float], start_equity: float) -> float:
    """
    Approximate annualised Sharpe from per-trade P&L treated as daily returns
    (conservative: trades >> trading days, so this underestimates Sharpe slightly).
    Returns 0 if insufficient data.
    """
    if len(profits) < 30:
        return 0.0
    # Convert to fractional return per trade
    returns = [p / start_equity for p in profits]
    mu  = statistics.mean(returns)
    sigma = statistics.stdev(returns)
    if sigma == 0:
        return 0.0
    # Annualise: assume ~252 trades/yr (portfolio level)
    annual_factor = math.sqrt(252)
    return (mu / sigma) * annual_factor


def prop_firm_pass(profits: List[float], start_equity: float,
                   target: float = PROP_TARGET_PCT,
                   max_dd: float = PROP_MAX_DD_PCT,
                   block: int = PROP_BLOCK_SIZE) -> bool:
    """
    Evaluate a single simulation path against prop-firm rules.
    Slide a window of `block` trades through the shuffled stream.
    Pass = hit profit target in at least one block WITHOUT breaching max_dd
    anywhere in that block.
    """
    n = len(profits)
    if n < block:
        block = n
    target_abs = start_equity * target
    dd_limit   = start_equity * max_dd

    for start_idx in range(0, n - block + 1, block // 2):   # 50% overlap
        chunk = profits[start_idx: start_idx + block]
        eq    = start_equity
        peak  = eq
        max_dd_abs = 0.0
        net_gain   = 0.0

        for p in chunk:
            eq     += p
            net_gain += p
            if eq > peak:
                peak = eq
            dd_abs = peak - eq
            if dd_abs > max_dd_abs:
                max_dd_abs = dd_abs

        if max_dd_abs <= dd_limit and net_gain >= target_abs:
            return True
    return False


def p_positive_year(profits: List[float], sim_annual_n: int) -> float:
    """
    Given a shuffled simulation path (all trades), estimate P(positive year)
    by slicing into year-sized blocks of sim_annual_n trades.
    Returns fraction of year blocks with positive net P&L.
    """
    n = len(profits)
    if n < sim_annual_n:
        # Too few trades: whole path is one year
        return 1.0 if sum(profits) > 0 else 0.0

    positive = 0
    total    = 0
    for start in range(0, n - sim_annual_n + 1, sim_annual_n):
        block_pnl = sum(profits[start: start + sim_annual_n])
        positive += (1 if block_pnl > 0 else 0)
        total    += 1
    return positive / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Main simulation
# ---------------------------------------------------------------------------

def run_portfolio_mc() -> dict:
    print("\n" + "=" * 65)
    print("PORTFOLIO MONTE CARLO SIMULATION  (10,000 paths)")
    print("=" * 65)

    # --- Load optimal weights ---
    print("\n[1] Loading optimal weights ...")
    optimal_weights = load_optimal_weights()
    print(f"  Optimal weights: {optimal_weights}")

    # --- Parse all EA trades ---
    print("\n[2] Parsing EA reports ...")
    all_scaled_profits: List[float] = []
    ea_trade_counts: Dict[str, int] = {}

    for ea_name, cfg in EA_CONFIGS.items():
        trades = extract_trades(cfg["report"], ea_name)
        if not trades:
            continue

        ea_trade_counts[ea_name] = len(trades)

        opt_risk  = optimal_weights.get(ea_name, cfg["current_risk"])
        curr_risk = cfg["current_risk"]
        scale     = opt_risk / curr_risk if curr_risk > 0 else 1.0

        scaled = scale_trades(trades, scale)
        all_scaled_profits.extend(scaled)

        print(f"    scale={scale:.4f}  ({curr_risk:.2f}% -> {opt_risk:.2f}%)  "
              f"total P&L contrib: ${sum(scaled):,.0f}")

    total_trades  = len(all_scaled_profits)
    trades_per_yr = total_trades / BACKTEST_YEARS

    print(f"\n  Total portfolio trades : {total_trades:,}")
    print(f"  Annualised trades/yr   : {trades_per_yr:.0f}  (over {BACKTEST_YEARS}-yr backtest)")

    if total_trades < 50:
        print("[ERROR] Fewer than 50 combined trades — aborting simulation.")
        return {}

    # Compute total net P&L (unshuffled) for annualised return reference
    total_net_pnl = sum(all_scaled_profits)
    ann_return_pct = (total_net_pnl / START_EQUITY) / BACKTEST_YEARS * 100.0

    print(f"  Total net P&L (scaled) : ${total_net_pnl:,.2f}")
    print(f"  Annualised return      : {ann_return_pct:.2f}%  (on $10K account)")

    # --- Monte Carlo ---
    print(f"\n[3] Running {N_SIMS:,} Monte Carlo simulations ...")

    max_dds:       List[float] = []   # % per sim
    final_equities: List[float] = []
    prop_pass_count: int = 0
    positive_yr_fracs: List[float] = []
    sharpes: List[float] = []

    # Use integer trade count for year-block slicing
    annual_n = max(1, round(trades_per_yr))

    for i in range(N_SIMS):
        shuffled = all_scaled_profits.copy()
        random.shuffle(shuffled)

        max_dd, final_eq, _ = simulate_equity_path(shuffled, START_EQUITY)
        max_dds.append(max_dd)
        final_equities.append(final_eq)

        # Sharpe (only compute for 10% sample to save time)
        if i % 10 == 0:
            sh = compute_daily_sharpe(shuffled, START_EQUITY)
            sharpes.append(sh)

        # P(positive year)
        py = p_positive_year(shuffled, annual_n)
        positive_yr_fracs.append(py)

        # Prop firm pass
        if prop_firm_pass(shuffled, START_EQUITY):
            prop_pass_count += 1

        if (i + 1) % 1000 == 0:
            print(f"  ... {i+1:,} / {N_SIMS:,} done", flush=True)

    # --- Compute metrics ---
    max_dds.sort()
    final_equities.sort()

    dd_p50 = percentile(max_dds, 50)
    dd_p95 = percentile(max_dds, 95)
    dd_p99 = percentile(max_dds, 99)

    sharpe_median  = statistics.median(sharpes) if sharpes else 0.0
    p_pos_yr       = statistics.mean(positive_yr_fracs)
    prop_pass_rate = prop_pass_count / N_SIMS

    # Calmar = annual return / P95 DD  (both in %)
    calmar = ann_return_pct / dd_p95 if dd_p95 > 0 else 0.0

    # --- Print report ---
    print("\n" + "=" * 65)
    print("PORTFOLIO MONTE CARLO RESULTS")
    print("=" * 65)
    print(f"  Total trades            : {total_trades:,}")
    print(f"  Trades/yr (annualised)  : {trades_per_yr:.0f}")
    print(f"  Annualised return       : {ann_return_pct:.2f}%")
    print()
    print(f"  Max Drawdown P50        : {dd_p50:.2f}%")
    print(f"  Max Drawdown P95        : {dd_p95:.2f}%   <- expect this")
    print(f"  Max Drawdown P99        : {dd_p99:.2f}%   <- extreme case")
    print()
    print(f"  Sharpe Ratio (median)   : {sharpe_median:.3f}")
    print(f"  Calmar Ratio            : {calmar:.3f}  (annRet / P95 DD)")
    print()
    print(f"  P(positive year)        : {p_pos_yr*100:.1f}%")
    print(f"  Prop-firm pass rate     : {prop_pass_rate*100:.1f}%  "
          f"(8% target, 8% DD cap, {PROP_BLOCK_SIZE}-trade blocks)")
    print()

    # Risk rating
    if dd_p95 < 10:
        rating = "EXCELLENT (< 10% P95 DD)"
    elif dd_p95 < 15:
        rating = "GOOD (< 15% P95 DD)"
    elif dd_p95 < 25:
        rating = "ACCEPTABLE (< 25% P95 DD)"
    else:
        rating = "HIGH RISK (>= 25% P95 DD)"
    print(f"  Risk rating             : {rating}")
    print("=" * 65)

    # --- Build result dict ---
    result = {
        "meta": {
            "n_simulations"   : N_SIMS,
            "backtest_years"  : BACKTEST_YEARS,
            "start_equity"    : START_EQUITY,
            "prop_target_pct" : PROP_TARGET_PCT,
            "prop_max_dd_pct" : PROP_MAX_DD_PCT,
            "prop_block_size" : PROP_BLOCK_SIZE,
        },
        "ea_trade_counts"  : ea_trade_counts,
        "portfolio": {
            "total_trades"          : total_trades,
            "trades_per_yr"         : round(trades_per_yr, 1),
            "total_net_pnl_scaled"  : round(total_net_pnl, 2),
            "annualised_return_pct" : round(ann_return_pct, 3),
        },
        "drawdown": {
            "p50_pct": round(dd_p50, 3),
            "p95_pct": round(dd_p95, 3),
            "p99_pct": round(dd_p99, 3),
            "max_pct": round(max(max_dds), 3),
        },
        "ratios": {
            "sharpe_median"    : round(sharpe_median, 4),
            "calmar"           : round(calmar, 4),
        },
        "pass_rates": {
            "p_positive_year"  : round(p_pos_yr, 5),
            "prop_firm_pass"   : round(prop_pass_rate, 5),
        },
        "risk_rating": rating,
        "optimal_weights_used": optimal_weights,
    }

    # Save
    out_path = ANALYSIS_DIR / "portfolio_mc_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {out_path}")

    return result


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    random.seed(42)   # reproducible baseline
    run_portfolio_mc()
