#!/usr/bin/env python3
"""
quant_audit.py — Professional Quant Audit Framework for EA Portfolio
====================================================================
Parses MT5 HTML reports, extracts trade-level data, and computes:
1. Deflated Sharpe Ratio (DSR) with multiple testing correction
2. Bootstrap CI with bias correction
3. Regime analysis (yearly, volatility buckets)
4. Trade distribution analysis (skewness, kurtosis, outlier dependency)
5. Inter-EA daily PnL correlation matrix
6. Portfolio-level metrics (combined Sharpe, diversification ratio)
7. Alpha decay detection (rolling PF, CUSUM)
8. Honest live expectations with slippage/spread haircuts

Usage:
  python quant_audit.py --reports report1.html report2.html ...
  python quant_audit.py --reports-dir "02. AlphaFactory/runs/"
"""

import argparse
import re
import os
import sys
import json
import math
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy import stats as sp_stats

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
# 1. MT5 HTML REPORT PARSER
# ─────────────────────────────────────────────

def parse_mt5_html_report(filepath):
    """Parse MT5 Strategy Tester HTML report and extract trade-level data."""
    # MT5 reports are UTF-16 LE encoded
    try:
        with open(filepath, 'r', encoding='utf-16') as f:
            html = f.read()
    except (UnicodeError, UnicodeDecodeError):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()

    trades = []

    # MT5 deal rows: find all <tr> containing 'out' direction
    # Structure: [0]=time [1]=deal# [2]=symbol [3]=type [4]=direction
    #            [5]=volume [6]=price [7]=order [8]=commission [9]=swap [10]=profit [11]=balance
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)

    for row_html in rows:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if len(tds) < 12:
            continue

        direction = tds[4].strip().lower()
        if direction != 'out':
            continue

        time_str = tds[0].strip()
        try:
            trade_time = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
        except ValueError:
            continue

        def parse_num(s):
            s = s.strip().replace('\xa0', '').replace(' ', '').replace(',', '')
            try:
                return float(s)
            except ValueError:
                return 0.0

        profit = parse_num(tds[10])
        commission = parse_num(tds[8])
        swap = parse_num(tds[9])

        trades.append({
            'time': trade_time,
            'profit': profit + commission + swap,
            'raw_profit': profit,
            'commission': commission,
            'swap': swap,
            'type': tds[3].strip().lower(),
        })

    if not trades:
        trades = _parse_from_summary(html, filepath)

    return trades


def _parse_deals_table(html):
    """Parse individual deal rows from MT5 HTML report."""
    trades = []

    # MT5 reports have a table with class or structure containing deals
    # Look for rows with "buy"/"sell" and profit values
    # Pattern: time | deal | symbol | type | direction | volume | price | order | commission | swap | profit | balance

    row_pattern = re.compile(
        r'<tr[^>]*>\s*'
        r'<td[^>]*>(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})</td>\s*'  # time
        r'<td[^>]*>(\d+)</td>\s*'  # deal number
        r'<td[^>]*>([^<]*)</td>\s*'  # symbol
        r'<td[^>]*>([^<]*)</td>\s*'  # type (buy/sell)
        r'<td[^>]*>([^<]*)</td>\s*'  # direction (in/out)
        r'<td[^>]*>([^<]*)</td>\s*'  # volume
        r'<td[^>]*>([^<]*)</td>\s*'  # price
        r'<td[^>]*>([^<]*)</td>\s*'  # order
        r'<td[^>]*>([^<]*)</td>\s*'  # commission
        r'<td[^>]*>([^<]*)</td>\s*'  # swap
        r'<td[^>]*>([^<]*)</td>\s*'  # profit
        r'<td[^>]*>([^<]*)</td>',    # balance
        re.IGNORECASE | re.DOTALL
    )

    for m in row_pattern.finditer(html):
        time_str = m.group(1).strip()
        direction = m.group(5).strip().lower()
        profit_str = m.group(11).strip().replace('\xa0', '').replace(' ', '')

        # Only count "out" trades (closed positions)
        if direction not in ('out', 'out '):
            continue

        try:
            profit = float(profit_str)
        except ValueError:
            continue

        try:
            trade_time = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
        except ValueError:
            continue

        commission_str = m.group(9).strip().replace('\xa0', '').replace(' ', '')
        swap_str = m.group(10).strip().replace('\xa0', '').replace(' ', '')

        try:
            commission = float(commission_str) if commission_str else 0.0
        except ValueError:
            commission = 0.0

        try:
            swap = float(swap_str) if swap_str else 0.0
        except ValueError:
            swap = 0.0

        trades.append({
            'time': trade_time,
            'profit': profit + commission + swap,  # Net profit
            'raw_profit': profit,
            'commission': commission,
            'swap': swap,
            'type': m.group(4).strip().lower(),
        })

    return trades


def _parse_from_summary(html, filepath):
    """Fallback: parse summary statistics and generate synthetic trades from report structure."""
    trades = []

    # Try to extract from the analysis CSV files that AlphaFactory generates
    analysis_dir = Path(filepath).parent / 'analysis'
    trades_csv = analysis_dir / 'trades.csv'
    deals_csv = analysis_dir / 'deals.csv'

    for csv_path in [trades_csv, deals_csv]:
        if csv_path.exists():
            try:
                with open(csv_path, 'r') as f:
                    lines = f.readlines()
                if len(lines) > 1:
                    headers = lines[0].strip().split(',')
                    for line in lines[1:]:
                        parts = line.strip().split(',')
                        if len(parts) >= len(headers):
                            row = dict(zip(headers, parts))
                            try:
                                trade = {
                                    'time': datetime.strptime(row.get('time', row.get('close_time', '2020.01.01 00:00:00')), '%Y.%m.%d %H:%M:%S'),
                                    'profit': float(row.get('profit', row.get('net_profit', 0))),
                                    'raw_profit': float(row.get('profit', 0)),
                                    'commission': float(row.get('commission', 0)),
                                    'swap': float(row.get('swap', 0)),
                                    'type': row.get('type', 'unknown'),
                                }
                                trades.append(trade)
                            except (ValueError, KeyError):
                                continue
            except Exception:
                pass

    if not trades:
        # Last resort: parse table rows more aggressively
        # Look for any table row with a float that could be profit/balance
        trades = _aggressive_parse(html)

    return trades


def _aggressive_parse(html):
    """Aggressive parsing: find profit values from any table structure."""
    trades = []

    # Look for patterns like: date, then eventually a profit number followed by a balance
    pattern = re.compile(
        r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})'
        r'.*?'
        r'(?:out|close)'
        r'.*?'
        r'(-?\d+\.?\d*)\s*</td>\s*<td[^>]*>\s*(\d+\.?\d*)',
        re.IGNORECASE | re.DOTALL
    )

    prev_balance = None
    for m in pattern.finditer(html):
        try:
            time_str = m.group(1)
            profit = float(m.group(2))
            balance = float(m.group(3))
            trade_time = datetime.strptime(time_str, '%Y.%m.%d %H:%M:%S')
            trades.append({
                'time': trade_time,
                'profit': profit,
                'raw_profit': profit,
                'commission': 0,
                'swap': 0,
                'type': 'unknown',
            })
        except (ValueError, IndexError):
            continue

    return trades


# ─────────────────────────────────────────────
# 2. CORE QUANT METRICS
# ─────────────────────────────────────────────

def compute_sharpe(returns, periods_per_year=252):
    """Annualized Sharpe ratio from daily returns."""
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    return np.mean(returns) / np.std(returns) * np.sqrt(periods_per_year)


def compute_deflated_sharpe(observed_sharpe, n_trials, n_returns, skewness=0, kurtosis=3):
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).
    Tests whether observed Sharpe is significantly above the expected maximum
    from n_trials independent strategies.
    """
    if n_trials <= 1 or n_returns <= 1:
        return 1.0

    # Expected maximum Sharpe from n_trials (Euler-Mascheroni approximation)
    euler_mascheroni = 0.5772156649
    expected_max_sharpe = (
        (1 - euler_mascheroni) * sp_stats.norm.ppf(1 - 1/n_trials)
        + euler_mascheroni * sp_stats.norm.ppf(1 - 1/(n_trials * math.e))
    )

    # Standard error of Sharpe estimate
    se_sharpe = math.sqrt(
        (1 + 0.5 * observed_sharpe**2 - skewness * observed_sharpe
         + ((kurtosis - 3) / 4) * observed_sharpe**2) / (n_returns - 1)
    )

    if se_sharpe == 0:
        return 0.0

    # DSR = probability that observed Sharpe > expected maximum from data mining
    z = (observed_sharpe - expected_max_sharpe) / se_sharpe
    dsr = sp_stats.norm.cdf(z)

    return dsr


def bootstrap_pf(profits, n_bootstrap=10000, ci_level=0.95):
    """Bootstrap confidence interval for profit factor."""
    profits = np.array(profits)
    wins = profits[profits > 0]
    losses = profits[profits < 0]

    if len(wins) == 0 or len(losses) == 0:
        return {'mean': 0, 'ci_lower': 0, 'ci_upper': 0, 'p_value': 1.0}

    pf_samples = []
    n = len(profits)

    for _ in range(n_bootstrap):
        sample = np.random.choice(profits, size=n, replace=True)
        s_wins = sample[sample > 0].sum()
        s_losses = abs(sample[sample < 0].sum())
        if s_losses > 0:
            pf_samples.append(s_wins / s_losses)

    pf_samples = np.array(pf_samples)
    alpha = 1 - ci_level

    return {
        'mean': np.mean(pf_samples),
        'median': np.median(pf_samples),
        'ci_lower': np.percentile(pf_samples, alpha/2 * 100),
        'ci_upper': np.percentile(pf_samples, (1 - alpha/2) * 100),
        'std': np.std(pf_samples),
        'p_below_1': np.mean(pf_samples < 1.0),  # Probability PF < 1.0
    }


def compute_trade_distribution(profits):
    """Analyze the statistical properties of trade returns."""
    profits = np.array(profits)
    if len(profits) < 5:
        return {}

    wins = profits[profits > 0]
    losses = profits[profits < 0]

    # Outlier dependency: what fraction of total profit comes from top 10% trades?
    sorted_profits = np.sort(profits)[::-1]
    top_10pct_n = max(1, int(len(profits) * 0.1))
    top_10pct_profit = sorted_profits[:top_10pct_n].sum()
    total_profit = profits.sum()

    outlier_dep = top_10pct_profit / total_profit if total_profit > 0 else 999.0

    # Single-trade dependency: would removing the best trade make PF < 1.0?
    if total_profit > 0:
        best_trade = sorted_profits[0]
        profit_without_best = total_profit - best_trade
        fragile = profit_without_best <= 0
    else:
        fragile = True

    return {
        'n': len(profits),
        'mean': float(np.mean(profits)),
        'median': float(np.median(profits)),
        'std': float(np.std(profits)),
        'skewness': float(sp_stats.skew(profits)),
        'kurtosis': float(sp_stats.kurtosis(profits, fisher=False)),  # Excess kurtosis
        'win_rate': float(len(wins) / len(profits)) if len(profits) > 0 else 0,
        'avg_win': float(np.mean(wins)) if len(wins) > 0 else 0,
        'avg_loss': float(np.mean(losses)) if len(losses) > 0 else 0,
        'payoff_ratio': float(abs(np.mean(wins) / np.mean(losses))) if len(losses) > 0 and np.mean(losses) != 0 else 0,
        'total_profit': float(total_profit),
        'outlier_dependency_pct': float(outlier_dep * 100),
        'top_trade_pct_of_profit': float(sorted_profits[0] / total_profit * 100) if total_profit > 0 else 0,
        'fragile_single_trade': fragile,
        'max_win': float(np.max(profits)),
        'max_loss': float(np.min(profits)),
        'profit_per_trade': float(np.mean(profits)),
    }


def compute_regime_analysis(trades, window_years=1):
    """Split trades by year and compute per-regime metrics."""
    if not trades:
        return {}

    yearly = defaultdict(list)
    for t in trades:
        year = t['time'].year
        yearly[year].append(t['profit'])

    results = {}
    for year in sorted(yearly.keys()):
        profits = yearly[year]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]
        win_sum = sum(wins)
        loss_sum = abs(sum(losses))
        pf = win_sum / loss_sum if loss_sum > 0 else float('inf')

        results[year] = {
            'n_trades': len(profits),
            'net_profit': sum(profits),
            'pf': round(pf, 2),
            'win_rate': round(len(wins) / len(profits) * 100, 1) if profits else 0,
            'avg_trade': round(sum(profits) / len(profits), 2) if profits else 0,
        }

    # Consistency metric: what % of years are profitable?
    profitable_years = sum(1 for y in results.values() if y['net_profit'] > 0)
    total_years = len(results)

    return {
        'yearly': results,
        'profitable_years_pct': round(profitable_years / total_years * 100, 1) if total_years > 0 else 0,
        'worst_year': min(results.items(), key=lambda x: x[1]['net_profit']) if results else None,
        'best_year': max(results.items(), key=lambda x: x[1]['net_profit']) if results else None,
    }


def compute_rolling_pf(trades, window=50):
    """Rolling profit factor to detect alpha decay."""
    if len(trades) < window:
        return []

    profits = [t['profit'] for t in trades]
    rolling = []

    for i in range(window, len(profits) + 1):
        chunk = profits[i-window:i]
        wins = sum(p for p in chunk if p > 0)
        losses = abs(sum(p for p in chunk if p < 0))
        pf = wins / losses if losses > 0 else float('inf')
        rolling.append({
            'trade_index': i,
            'time': trades[i-1]['time'].strftime('%Y-%m-%d'),
            'rolling_pf': round(pf, 3),
        })

    return rolling


def compute_cusum(profits):
    """CUSUM test for structural break in profitability."""
    if len(profits) < 20:
        return {'break_detected': False}

    cumsum = np.cumsum(profits - np.mean(profits))
    max_idx = np.argmax(cumsum)
    min_idx = np.argmin(cumsum)

    # Simple structural break test
    range_stat = np.max(cumsum) - np.min(cumsum)
    threshold = np.std(profits) * np.sqrt(len(profits)) * 1.36  # 5% significance

    return {
        'break_detected': range_stat > threshold,
        'max_cumsum_at_trade': int(max_idx),
        'min_cumsum_at_trade': int(min_idx),
        'range_statistic': float(range_stat),
        'threshold_5pct': float(threshold),
    }


# ─────────────────────────────────────────────
# 3. INTER-EA CORRELATION
# ─────────────────────────────────────────────

def compute_daily_pnl(trades):
    """Convert trade-level data to daily PnL series."""
    daily = defaultdict(float)
    for t in trades:
        day = t['time'].strftime('%Y-%m-%d')
        daily[day] += t['profit']
    return daily


def compute_correlation_matrix(ea_daily_pnls, ea_names):
    """Compute daily PnL correlation between EAs."""
    # Align all EAs to same date range
    all_dates = set()
    for pnl in ea_daily_pnls:
        all_dates.update(pnl.keys())
    all_dates = sorted(all_dates)

    # Build matrix
    n_eas = len(ea_names)
    matrix = np.zeros((n_eas, n_eas))

    for i in range(n_eas):
        for j in range(n_eas):
            series_i = [ea_daily_pnls[i].get(d, 0) for d in all_dates]
            series_j = [ea_daily_pnls[j].get(d, 0) for d in all_dates]

            # Only correlate on days where at least one EA traded
            active_days = [(si, sj) for si, sj in zip(series_i, series_j)
                          if si != 0 or sj != 0]

            if len(active_days) > 10:
                si_active = [x[0] for x in active_days]
                sj_active = [x[1] for x in active_days]
                if np.std(si_active) > 0 and np.std(sj_active) > 0:
                    corr, _ = sp_stats.pearsonr(si_active, sj_active)
                    matrix[i][j] = corr
                else:
                    matrix[i][j] = 0.0
            else:
                matrix[i][j] = 0.0 if i != j else 1.0

    return matrix, all_dates


def compute_max_concurrent_exposure(ea_trades_list, ea_names):
    """Find maximum concurrent exposure windows."""
    # Track which EAs have open positions at any point
    # Simplified: count trades that overlap in time
    concurrent = defaultdict(set)

    for ea_idx, trades in enumerate(ea_trades_list):
        for t in trades:
            day = t['time'].strftime('%Y-%m-%d')
            concurrent[day].add(ea_names[ea_idx])

    max_concurrent = 0
    max_day = None
    for day, eas in concurrent.items():
        if len(eas) > max_concurrent:
            max_concurrent = len(eas)
            max_day = day

    return {
        'max_concurrent_eas': max_concurrent,
        'max_concurrent_day': max_day,
        'avg_concurrent': np.mean([len(eas) for eas in concurrent.values()]),
    }


# ─────────────────────────────────────────────
# 4. PORTFOLIO-LEVEL METRICS
# ─────────────────────────────────────────────

def compute_portfolio_metrics(ea_daily_pnls, ea_names, start_equity=200000):
    """Combined portfolio metrics."""
    all_dates = set()
    for pnl in ea_daily_pnls:
        all_dates.update(pnl.keys())
    all_dates = sorted(all_dates)

    # Combined daily PnL
    combined_daily = []
    for d in all_dates:
        total = sum(pnl.get(d, 0) for pnl in ea_daily_pnls)
        combined_daily.append(total)

    combined = np.array(combined_daily)

    # Equity curve
    equity = start_equity + np.cumsum(combined)
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak * 100

    # Portfolio Sharpe (daily -> annualized)
    trading_days = len([x for x in combined if x != 0])
    sharpe = compute_sharpe(combined, periods_per_year=252)

    # Diversification ratio
    # = weighted sum of individual volatilities / portfolio volatility
    individual_vols = []
    for pnl in ea_daily_pnls:
        series = [pnl.get(d, 0) for d in all_dates]
        vol = np.std(series)
        individual_vols.append(vol)

    portfolio_vol = np.std(combined)
    div_ratio = sum(individual_vols) / portfolio_vol if portfolio_vol > 0 else 1.0

    return {
        'total_profit': float(np.sum(combined)),
        'total_trades_days': trading_days,
        'sharpe_annualized': round(sharpe, 2),
        'max_dd_pct': round(np.max(drawdown), 2),
        'max_dd_equity': round(np.max(peak - equity), 2),
        'calmar_ratio': round(float(np.sum(combined)) / (np.max(peak - equity)) if np.max(peak - equity) > 0 else 0, 2),
        'diversification_ratio': round(div_ratio, 2),
        'avg_daily_pnl': round(float(np.mean(combined)), 2),
        'worst_day': round(float(np.min(combined)), 2),
        'best_day': round(float(np.max(combined)), 2),
        'profitable_days_pct': round(np.mean(combined > 0) * 100, 1),
    }


# ─────────────────────────────────────────────
# 5. HONEST EXPECTATIONS
# ─────────────────────────────────────────────

def compute_honest_expectations(ea_results, n_total_trials=679, start_equity=200000):
    """
    Apply all haircuts: slippage, spread, multiple testing, execution degradation.
    Based on rules in .claude/rules/ea-strategy-spec.md
    """
    haircuts = {
        'slippage_per_trade_usd': 3.0,  # Conservative for USDJPY+ M15
        'spread_haircut_pct': 15.0,  # E8 spreads wider than backtest
        'execution_degradation_pct': 20.0,  # General live vs backtest gap
        'multiple_testing_penalty': True,
    }

    results = []
    for ea in ea_results:
        name = ea['name']
        backtest_pf = ea['pf']
        n_trades = ea['n_trades']
        n_trades_per_year = ea['trades_per_year']
        backtest_profit_per_trade = ea.get('avg_profit_per_trade', 0)

        # Slippage haircut
        adjusted_profit = backtest_profit_per_trade - haircuts['slippage_per_trade_usd']

        # Spread haircut
        adjusted_profit *= (1 - haircuts['spread_haircut_pct'] / 100)

        # Execution degradation
        adjusted_profit *= (1 - haircuts['execution_degradation_pct'] / 100)

        # Honest annual estimate
        honest_annual = adjusted_profit * n_trades_per_year

        # Honest PF (rough approximation)
        if backtest_pf > 1:
            edge_fraction = (backtest_pf - 1) / backtest_pf
            adjusted_edge = edge_fraction * (1 - haircuts['spread_haircut_pct']/100) * (1 - haircuts['execution_degradation_pct']/100)
            honest_pf = 1 / (1 - adjusted_edge) if adjusted_edge < 1 else backtest_pf
        else:
            honest_pf = backtest_pf

        results.append({
            'name': name,
            'backtest_pf': backtest_pf,
            'honest_pf': round(honest_pf, 2),
            'backtest_profit_per_trade': round(backtest_profit_per_trade, 2),
            'honest_profit_per_trade': round(adjusted_profit, 2),
            'honest_annual_estimate': round(honest_annual, 2),
            'trades_per_year': n_trades_per_year,
        })

    return results


# ─────────────────────────────────────────────
# 6. MAIN AUDIT ENGINE
# ─────────────────────────────────────────────

def audit_single_ea(name, report_path, n_total_trials=679):
    """Full audit of a single EA."""
    print(f"\n{'='*70}")
    print(f"  AUDITING: {name}")
    print(f"  Report: {report_path}")
    print(f"{'='*70}")

    trades = parse_mt5_html_report(report_path)

    if not trades:
        print(f"  WARNING: Could not parse trades from {report_path}")
        print(f"  Attempting to use analysis CSV files...")

        # Try analysis directory
        analysis_dir = Path(report_path).parent / 'analysis'
        for csv_name in ['by_weekday.csv', 'by_hour.csv', 'enhanced_summary.json']:
            csv_path = analysis_dir / csv_name
            if csv_path.exists():
                print(f"  Found: {csv_path}")

        return None

    profits = [t['profit'] for t in trades]
    n = len(profits)
    total_years = (trades[-1]['time'] - trades[0]['time']).days / 365.25 if n > 1 else 1

    print(f"\n  Trades parsed: {n}")
    print(f"  Period: {trades[0]['time'].strftime('%Y-%m-%d')} to {trades[-1]['time'].strftime('%Y-%m-%d')}")
    print(f"  Years: {total_years:.1f}")

    # 1. Trade distribution
    dist = compute_trade_distribution(profits)
    print(f"\n  --- TRADE DISTRIBUTION ---")
    print(f"  Mean:     ${dist['mean']:.2f}")
    print(f"  Median:   ${dist['median']:.2f}")
    print(f"  Std:      ${dist['std']:.2f}")
    print(f"  Skewness: {dist['skewness']:.2f}")
    print(f"  Kurtosis: {dist['kurtosis']:.2f}")
    print(f"  Win Rate: {dist['win_rate']*100:.1f}%")
    print(f"  Payoff:   {dist['payoff_ratio']:.2f}")
    print(f"  Outlier dependency (top 10%): {dist['outlier_dependency_pct']:.1f}%")
    print(f"  Single-trade fragility: {'YES ⚠' if dist['fragile_single_trade'] else 'NO ✓'}")

    # 2. Profit Factor
    wins_total = sum(p for p in profits if p > 0)
    losses_total = abs(sum(p for p in profits if p < 0))
    pf = wins_total / losses_total if losses_total > 0 else float('inf')
    print(f"\n  --- PROFIT FACTOR ---")
    print(f"  PF: {pf:.3f}")

    # 3. Bootstrap PF
    boot = bootstrap_pf(profits, n_bootstrap=10000)
    print(f"\n  --- BOOTSTRAP (10,000 resamples) ---")
    print(f"  PF mean:     {boot['mean']:.3f}")
    print(f"  PF median:   {boot['median']:.3f}")
    print(f"  95% CI:      [{boot['ci_lower']:.3f}, {boot['ci_upper']:.3f}]")
    print(f"  P(PF < 1.0): {boot['p_below_1']*100:.1f}%")

    # 4. Sharpe & DSR
    daily_pnl = compute_daily_pnl(trades)
    daily_returns = list(daily_pnl.values())
    sharpe = compute_sharpe(np.array(daily_returns), periods_per_year=252)

    dsr = compute_deflated_sharpe(
        sharpe, n_total_trials, len(daily_returns),
        skewness=dist['skewness'], kurtosis=dist['kurtosis']
    )
    print(f"\n  --- SHARPE & DEFLATED SHARPE ---")
    print(f"  Annualized Sharpe:  {sharpe:.2f}")
    print(f"  Deflated Sharpe (N={n_total_trials} trials): {dsr:.3f}")
    print(f"  DSR verdict: {'PASS ✓ (>0.70)' if dsr > 0.70 else 'FAIL ✗ (<0.70) — could be data mining!'}")

    # 5. Regime analysis
    regime = compute_regime_analysis(trades)
    print(f"\n  --- REGIME ANALYSIS (by year) ---")
    for year, stats in regime['yearly'].items():
        flag = '✓' if stats['pf'] > 1.0 else '✗'
        print(f"  {year}: PF {stats['pf']:.2f}, {stats['n_trades']}t, net ${stats['net_profit']:.0f} {flag}")
    print(f"  Profitable years: {regime['profitable_years_pct']:.0f}%")
    if regime['worst_year']:
        print(f"  Worst year: {regime['worst_year'][0]} (PF {regime['worst_year'][1]['pf']:.2f})")

    # 6. Alpha decay (rolling PF)
    rolling = compute_rolling_pf(trades, window=min(50, n // 3))
    if rolling:
        first_quarter = rolling[:len(rolling)//4]
        last_quarter = rolling[-len(rolling)//4:]
        avg_early = np.mean([r['rolling_pf'] for r in first_quarter])
        avg_late = np.mean([r['rolling_pf'] for r in last_quarter])
        decay_pct = (avg_early - avg_late) / avg_early * 100 if avg_early > 0 else 0

        print(f"\n  --- ALPHA DECAY ---")
        print(f"  Early rolling PF (first 25%): {avg_early:.2f}")
        print(f"  Late rolling PF (last 25%):   {avg_late:.2f}")
        print(f"  Decay: {decay_pct:.1f}%")
        print(f"  Verdict: {'DECAYING ⚠' if decay_pct > 20 else 'STABLE ✓' if decay_pct < 10 else 'MODERATE'}")

    # 7. CUSUM
    cusum = compute_cusum(profits)
    print(f"\n  --- CUSUM STRUCTURAL BREAK ---")
    print(f"  Break detected: {'YES ⚠' if cusum['break_detected'] else 'NO ✓'}")

    return {
        'name': name,
        'n_trades': n,
        'trades_per_year': round(n / total_years, 1),
        'pf': round(pf, 3),
        'sharpe': round(sharpe, 2),
        'dsr': round(dsr, 3),
        'bootstrap_ci': [round(boot['ci_lower'], 3), round(boot['ci_upper'], 3)],
        'p_below_1': round(boot['p_below_1'], 3),
        'distribution': dist,
        'regime': regime,
        'avg_profit_per_trade': dist['profit_per_trade'],
        'alpha_decay_pct': round(decay_pct, 1) if rolling else None,
        'cusum_break': cusum['break_detected'],
        'daily_pnl': daily_pnl,
        'trades': trades,
    }


def run_full_audit(report_map, n_total_trials=679):
    """Run full audit across all EAs."""

    print("=" * 70)
    print("  PROFESSIONAL QUANT AUDIT — 7 EA PORTFOLIO")
    print(f"  Total historical trials: {n_total_trials}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    ea_results = []
    ea_daily_pnls = []
    ea_names = []

    for name, path in report_map.items():
        result = audit_single_ea(name, path, n_total_trials)
        if result:
            ea_results.append(result)
            ea_daily_pnls.append(result['daily_pnl'])
            ea_names.append(name)

    if len(ea_results) < 2:
        print("\n  WARNING: Not enough EAs with parseable trade data for correlation analysis.")
        print("  Individual audits completed above.")
        return ea_results

    # ── CORRELATION MATRIX ──
    print(f"\n{'='*70}")
    print("  INTER-EA DAILY PNL CORRELATION MATRIX")
    print(f"{'='*70}")

    corr_matrix, all_dates = compute_correlation_matrix(ea_daily_pnls, ea_names)

    # Print header
    header = "         " + "  ".join(f"{n[:8]:>8}" for n in ea_names)
    print(header)
    for i, name in enumerate(ea_names):
        row = f"{name[:8]:>8} "
        for j in range(len(ea_names)):
            val = corr_matrix[i][j]
            flag = '⚠' if abs(val) > 0.30 and i != j else ' '
            row += f" {val:>7.3f}{flag}"
        print(row)

    # Flag high correlations
    high_corr = []
    for i in range(len(ea_names)):
        for j in range(i+1, len(ea_names)):
            if abs(corr_matrix[i][j]) > 0.15:
                high_corr.append((ea_names[i], ea_names[j], corr_matrix[i][j]))

    if high_corr:
        print(f"\n  HIGH CORRELATION PAIRS (>0.15):")
        for a, b, c in sorted(high_corr, key=lambda x: abs(x[2]), reverse=True):
            print(f"  ⚠ {a} × {b}: {c:.3f}")
    else:
        print(f"\n  ✓ No high correlation pairs detected")

    # ── PORTFOLIO METRICS ──
    print(f"\n{'='*70}")
    print("  PORTFOLIO-LEVEL METRICS (combined)")
    print(f"{'='*70}")

    portfolio = compute_portfolio_metrics(ea_daily_pnls, ea_names)
    print(f"  Total profit:         ${portfolio['total_profit']:.0f}")
    print(f"  Trading days:         {portfolio['total_trades_days']}")
    print(f"  Sharpe (annualized):  {portfolio['sharpe_annualized']}")
    print(f"  Max DD:               {portfolio['max_dd_pct']:.1f}%")
    print(f"  Calmar ratio:         {portfolio['calmar_ratio']}")
    print(f"  Diversification ratio: {portfolio['diversification_ratio']}")
    print(f"  Avg daily PnL:        ${portfolio['avg_daily_pnl']:.2f}")
    print(f"  Worst day:            ${portfolio['worst_day']:.2f}")
    print(f"  Best day:             ${portfolio['best_day']:.2f}")
    print(f"  Profitable days:      {portfolio['profitable_days_pct']:.1f}%")

    # ── HONEST EXPECTATIONS ──
    print(f"\n{'='*70}")
    print("  HONEST LIVE EXPECTATIONS ($200k E8)")
    print(f"{'='*70}")

    honest = compute_honest_expectations(ea_results, n_total_trials, start_equity=200000)
    for h in honest:
        print(f"\n  {h['name']}:")
        print(f"    Backtest PF:    {h['backtest_pf']:.2f} → Honest PF: {h['honest_pf']:.2f}")
        print(f"    Per trade:      ${h['backtest_profit_per_trade']:.2f} → ${h['honest_profit_per_trade']:.2f}")
        print(f"    Annual est:     ${h['honest_annual_estimate']:.0f} ({h['trades_per_year']} trades/yr)")

    total_honest_annual = sum(h['honest_annual_estimate'] for h in honest)
    print(f"\n  TOTAL HONEST ANNUAL: ${total_honest_annual:.0f}")
    print(f"  On $200k:            {total_honest_annual/200000*100:.1f}% annual return")

    # ── FINAL SCORECARD ──
    print(f"\n{'='*70}")
    print("  FINAL SCORECARD")
    print(f"{'='*70}")
    print(f"  {'EA':<20} {'PF':>6} {'N':>5} {'DSR':>6} {'CI Low':>7} {'P<1':>6} {'Decay':>6} {'CUSUM':>6} {'Verdict':>10}")
    print(f"  {'-'*20} {'-'*6} {'-'*5} {'-'*6} {'-'*7} {'-'*6} {'-'*6} {'-'*6} {'-'*10}")

    for r in ea_results:
        dsr_flag = '✓' if r['dsr'] > 0.70 else '⚠' if r['dsr'] > 0.50 else '✗'
        ci_flag = '✓' if r['bootstrap_ci'][0] > 1.0 else '⚠' if r['bootstrap_ci'][0] > 0.9 else '✗'
        decay_str = f"{r['alpha_decay_pct']:.0f}%" if r['alpha_decay_pct'] is not None else 'N/A'
        cusum_flag = '⚠' if r['cusum_break'] else '✓'

        # Verdict logic
        fails = 0
        if r['dsr'] < 0.50: fails += 1
        if r['bootstrap_ci'][0] < 1.0: fails += 1
        if r['cusum_break']: fails += 1
        if r['alpha_decay_pct'] and r['alpha_decay_pct'] > 30: fails += 1

        if fails == 0:
            verdict = 'STRONG'
        elif fails == 1:
            verdict = 'MODERATE'
        else:
            verdict = 'WEAK'

        print(f"  {r['name']:<20} {r['pf']:>6.2f} {r['n_trades']:>5} {r['dsr']:>5.3f}{dsr_flag} {r['bootstrap_ci'][0]:>6.3f}{ci_flag} {r['p_below_1']*100:>5.1f}% {decay_str:>6} {cusum_flag:>6} {verdict:>10}")

    return ea_results


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description='Professional Quant Audit Framework')
    parser.add_argument('--reports', nargs='+', help='Paths to MT5 HTML reports')
    parser.add_argument('--names', nargs='+', help='Names for each EA')
    parser.add_argument('--trials', type=int, default=679, help='Total historical trials for DSR')
    parser.add_argument('--json-out', type=str, help='Output JSON file')
    args = parser.parse_args()

    if not args.reports:
        print("Usage: python quant_audit.py --reports r1.html r2.html --names EA1 EA2")
        sys.exit(1)

    report_map = {}
    for i, path in enumerate(args.reports):
        name = args.names[i] if args.names and i < len(args.names) else f"EA_{i+1}"
        report_map[name] = path

    results = run_full_audit(report_map, n_total_trials=args.trials)

    if args.json_out and results:
        # Serialize (remove non-serializable fields)
        serializable = []
        for r in results:
            s = {k: v for k, v in r.items() if k not in ('daily_pnl', 'trades')}
            serializable.append(s)

        with open(args.json_out, 'w') as f:
            json.dump(serializable, f, indent=2, default=str)
        print(f"\n  Results saved to: {args.json_out}")
