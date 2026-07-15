#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Risk Sizing Optimizer
================================
Computes optimal risk% per EA based on:
- Per-EA Kelly Criterion (capped at half-Kelly)
- Daily PnL correlation matrix
- Peak-hour overlap penalty
- USDJPY concentration constraint

Usage:
  python portfolio_optimizer.py

Input: Hardcoded canonical run paths (validated runs only)
Output: Recommended risk% per EA, correlation matrix, portfolio metrics
"""

import sys, json, math
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict

# Add analysis dir to path
ANALYSIS_DIR = Path(__file__).parent
sys.path.insert(0, str(ANALYSIS_DIR))
from quant_analyzer import parse_deals, deals_to_trades, Trade

# ============================================================
# CANONICAL VALIDATED RUNS
# ============================================================
BASE = Path(__file__).parent.parent  # AlphaFactory root
RUNS = BASE / "runs"

EA_CONFIGS = {
    # === POST SESSION-24 EQUITY AUDIT PORTFOLIO (6 instances) ===
    # Removed: Spark (FAIL: R²=0.810, spike dep 136%), Gotobi (FAIL: Friday crutch),
    #          OvernightGold (INVALIDATED: R²=0.659, beta disguise)
    "Cobra_XAUUSD": {
        "report": RUNS / "EA_Cobra" / "20260402_221001" / "report.html",
        "symbol": "XAUUSD",
        "current_risk": 0.42,
        "session_hours": [16],       # NYC KZ hour 16 ONLY (hr17 WFA FAIL)
        "days": [1,2,3,5],          # skip Thu
    },
    "SilverBullet_USDJPY": {
        "report": RUNS / "EA_SilverBullet" / "20260402_225249" / "report.html",
        "symbol": "USDJPY",
        "current_risk": 0.36,
        "session_hours": [11, 12, 16, 17, 18],  # London + NY KZ
        "days": [1,2,3,4],          # skip Fri
    },
    "InsideBar_USDJPY": {
        "report": RUNS / "EA_InsideBar" / "20260402_225507" / "report.html",
        "symbol": "USDJPY",
        "current_risk": 0.29,
        "session_hours": [9, 10, 11, 16, 17],
        "days": [1,2,3,4,5],
    },
    "InsideBar_GBPUSD": {
        "report": RUNS / "EA_InsideBar" / "20260329_092112" / "report.html",
        "symbol": "GBPUSD",
        "current_risk": 0.42,
        "session_hours": [9, 10, 11, 16, 17],
        "days": [2,4,5],           # skip Mon+Wed
    },
    "ITSM_USDJPY": {
        "report": RUNS / "EA_ITSM" / "20260405_000436" / "report.html",
        "symbol": "USDJPY",
        "current_risk": 0.26,
        "session_hours": [15, 16],   # NY KZ H15-17 (entries at 15-16)
        "days": [1,3,4],            # Mon, Wed, Thu (skip Tue+Fri)
    },
    "LondonNY_USDJPY": {
        "report": RUNS / "EA_LondonNY" / "20260403_012503" / "report.html",
        "symbol": "USDJPY",
        "current_risk": 0.36,
        "session_hours": [15, 16, 17, 18],  # NY entry H15-18
        "days": [1,2,3,4,5],       # all days
    },
}


def extract_trades(report_path: Path) -> List[Trade]:
    """Parse HTML report and extract trade list."""
    if not report_path.exists():
        print(f"[WARN] Report not found: {report_path}")
        return []
    deals = parse_deals(report_path)
    return deals_to_trades(deals)


def trades_to_daily_pnl(trades: List[Trade]) -> Dict[str, float]:
    """Convert trade list to daily PnL dictionary (date_str -> total_pnl)."""
    daily = defaultdict(float)
    for t in trades:
        day_str = t.exit_time.strftime("%Y-%m-%d")
        daily[day_str] += t.profit
    return dict(daily)


def kelly_criterion(trades: List[Trade]) -> float:
    """Calculate Kelly Criterion (half-Kelly capped)."""
    if len(trades) < 30:
        return 0.0

    wins = [t.profit for t in trades if t.profit > 0]
    losses = [abs(t.profit) for t in trades if t.profit <= 0]

    if not wins or not losses:
        return 0.0

    win_rate = len(wins) / len(trades)
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)

    if avg_loss == 0:
        return 0.0

    win_loss_ratio = avg_win / avg_loss

    # Kelly formula: f* = (p * b - q) / b
    # where p = win rate, q = 1-p, b = win/loss ratio
    kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

    # Half-Kelly (conservative)
    half_kelly = kelly / 2.0

    # Cap at reasonable range
    return max(0.0, min(half_kelly, 0.02))  # Max 2% per trade


def compute_correlation_matrix(daily_pnls: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """Compute pairwise correlation of daily PnL across EAs."""
    ea_names = list(daily_pnls.keys())

    # Get union of all dates
    all_dates = set()
    for pnl in daily_pnls.values():
        all_dates.update(pnl.keys())
    all_dates = sorted(all_dates)

    # Build aligned series (0 for no-trade days)
    series = {}
    for ea in ea_names:
        series[ea] = [daily_pnls[ea].get(d, 0.0) for d in all_dates]

    # Compute correlation
    def pearson(x, y):
        n = len(x)
        if n < 10:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        sx = math.sqrt(sum((xi - mx)**2 for xi in x) / n)
        sy = math.sqrt(sum((yi - my)**2 for yi in y) / n)
        if sx == 0 or sy == 0:
            return 0.0
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / n
        return cov / (sx * sy)

    corr = {}
    for ea1 in ea_names:
        corr[ea1] = {}
        for ea2 in ea_names:
            corr[ea1][ea2] = round(pearson(series[ea1], series[ea2]), 3)

    return corr


def peak_hour_overlap(configs: Dict) -> Dict[str, List[str]]:
    """Find which EAs overlap at each hour."""
    hour_map = defaultdict(list)
    for ea, cfg in configs.items():
        for h in cfg.get("session_hours", []):
            hour_map[h].append(ea)

    # Only return hours with 2+ EAs
    return {h: eas for h, eas in hour_map.items() if len(eas) >= 2}


def usdjpy_concentration(configs: Dict, weights: Dict[str, float]) -> float:
    """Calculate USDJPY share of total risk."""
    total = sum(weights.values())
    usdjpy_total = sum(w for ea, w in weights.items() if configs[ea]["symbol"] == "USDJPY")
    return usdjpy_total / total if total > 0 else 0


def optimize_portfolio(ea_configs: Dict) -> Dict:
    """Main optimization: Kelly + correlation + overlap + concentration."""

    print("=" * 60)
    print("PORTFOLIO RISK SIZING OPTIMIZER")
    print("=" * 60)

    # Step 1: Extract trades and compute Kelly for each EA
    print("\n--- Step 1: Kelly Criterion per EA ---")
    ea_trades = {}
    ea_daily_pnl = {}
    ea_kelly = {}

    for ea_name, cfg in ea_configs.items():
        trades = extract_trades(cfg["report"])
        ea_trades[ea_name] = trades
        ea_daily_pnl[ea_name] = trades_to_daily_pnl(trades)
        kelly = kelly_criterion(trades)
        ea_kelly[ea_name] = kelly

        wins = sum(1 for t in trades if t.profit > 0)
        losses = sum(1 for t in trades if t.profit <= 0)
        wr = wins / len(trades) * 100 if trades else 0
        avg_w = sum(t.profit for t in trades if t.profit > 0) / max(wins, 1)
        avg_l = sum(abs(t.profit) for t in trades if t.profit <= 0) / max(losses, 1)

        print(f"  {ea_name:25s}: {len(trades):4d} trades, WR {wr:5.1f}%, "
              f"AvgW/L={avg_w:.1f}/{avg_l:.1f}, Kelly={kelly*100:.3f}%")

    # Step 2: Correlation matrix
    print("\n--- Step 2: Daily PnL Correlation Matrix ---")
    corr = compute_correlation_matrix(ea_daily_pnl)

    ea_names = list(ea_configs.keys())
    # Print header
    print(f"  {'':25s}", end="")
    for ea in ea_names:
        print(f"  {ea[:8]:>8s}", end="")
    print()
    for ea1 in ea_names:
        print(f"  {ea1:25s}", end="")
        for ea2 in ea_names:
            c = corr[ea1][ea2]
            marker = "**" if abs(c) > 0.3 else "  "
            print(f"  {c:7.3f}{marker[0]}", end="")
        print()

    # Step 3: Peak hour overlap
    print("\n--- Step 3: Peak Hour Overlap ---")
    overlaps = peak_hour_overlap(ea_configs)
    for h, eas in sorted(overlaps.items()):
        print(f"  Hour {h:2d}: {', '.join(eas)}")

    # Step 4: Compute optimal weights
    print("\n--- Step 4: Optimal Risk Sizing ---")

    optimal_weights = {}
    for ea_name in ea_names:
        base_risk = ea_kelly[ea_name] * 100  # as percentage

        # If Kelly = 0 (too few trades), use minimum
        if base_risk <= 0:
            base_risk = 0.2

        # Cap at current risk level (conservative)
        base_risk = min(base_risk, ea_configs[ea_name]["current_risk"])

        # Correlation penalty: if highly correlated with another EA, reduce
        max_corr = 0
        for other in ea_names:
            if other != ea_name:
                c = abs(corr[ea_name].get(other, 0))
                if c > max_corr:
                    max_corr = c

        # Penalty: reduce by up to 30% for highly correlated EAs
        corr_penalty = 1.0 - (max_corr * 0.3) if max_corr > 0.2 else 1.0

        # Peak overlap penalty: reduce if in crowded hour
        overlap_count = 0
        for h, eas in overlaps.items():
            if ea_name in eas:
                overlap_count = max(overlap_count, len(eas))

        overlap_penalty = 1.0
        if overlap_count >= 3:
            overlap_penalty = 0.85  # 15% reduction for 3+ EAs same hour
        elif overlap_count >= 4:
            overlap_penalty = 0.70  # 30% reduction for 4+ EAs

        adjusted_risk = base_risk * corr_penalty * overlap_penalty
        adjusted_risk = max(0.2, round(adjusted_risk, 2))  # Min 0.2%

        optimal_weights[ea_name] = adjusted_risk

    # Step 5: USDJPY concentration check
    usdjpy_share = usdjpy_concentration(ea_configs, optimal_weights)
    print(f"\n  USDJPY Concentration: {usdjpy_share*100:.1f}%")

    if usdjpy_share > 0.55:
        print("  [WARN] USDJPY > 55%! Reducing USDJPY EAs proportionally...")
        target_share = 0.55
        reduction = target_share / usdjpy_share
        for ea_name in ea_names:
            if ea_configs[ea_name]["symbol"] == "USDJPY":
                optimal_weights[ea_name] = max(0.2, round(optimal_weights[ea_name] * reduction, 2))
        usdjpy_share = usdjpy_concentration(ea_configs, optimal_weights)
        print(f"  New USDJPY Concentration: {usdjpy_share*100:.1f}%")

    # Step 6: Summary
    print("\n" + "=" * 60)
    print("RECOMMENDED RISK SIZING")
    print("=" * 60)

    total_risk = 0
    for ea_name in ea_names:
        curr = ea_configs[ea_name]["current_risk"]
        opt = optimal_weights[ea_name]
        delta = opt - curr
        marker = "UP" if delta > 0 else ("DN" if delta < 0 else "==")
        print(f"  {ea_name:25s}: {curr:.2f}% -> {opt:.2f}%  {marker}")
        total_risk += opt

    print(f"\n  Total concurrent risk: {total_risk:.2f}%")
    print(f"  USDJPY share: {usdjpy_concentration(ea_configs, optimal_weights)*100:.1f}%")

    # Compute peak concurrent
    peak_risk = {}
    for h, eas in overlaps.items():
        peak_risk[h] = sum(optimal_weights[ea] for ea in eas)

    if peak_risk:
        worst_hour = max(peak_risk, key=peak_risk.get)
        print(f"  Peak hour risk: {peak_risk[worst_hour]:.2f}% (hour {worst_hour})")

    # Output JSON
    result = {
        "optimal_weights": optimal_weights,
        "current_weights": {ea: cfg["current_risk"] for ea, cfg in ea_configs.items()},
        "kelly_raw": {ea: round(k * 100, 4) for ea, k in ea_kelly.items()},
        "correlation_matrix": corr,
        "peak_hour_overlaps": {str(h): eas for h, eas in overlaps.items()},
        "usdjpy_concentration": round(usdjpy_share, 4),
        "total_risk": round(total_risk, 4),
    }

    output_path = ANALYSIS_DIR / "portfolio_optimization_result.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {output_path}")

    return result


if __name__ == "__main__":
    optimize_portfolio(EA_CONFIGS)
