"""
equity_curve_audit.py — Deep equity curve diagnostics for validation pipeline.
Reads an MT5 HTML report and produces quantitative health metrics.

Usage:
    python equity_curve_audit.py --report path/to/report.html [--out path/to/output/]

Output: equity_audit.json + equity_audit.png
"""
import argparse, json, sys, os, statistics
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Reuse existing MT5 parser from quant_analyzer (proven, handles UTF-16)
sys.path.insert(0, str(Path(__file__).parent))
from quant_analyzer import parse_deals, deals_to_trades

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def parse_trades_from_report(report_path: str):
    """Extract trades using proven quant_analyzer parser."""
    deals = parse_deals(Path(report_path))
    trades = deals_to_trades(deals)
    # Get start equity from balance deal
    start_eq = next((d.balance for d in deals if (d.side or "").strip().lower() == "balance" and d.balance > 0), 10000.0)
    result = []
    for t in trades:
        result.append({
            'time': t.exit_time,
            'profit': t.profit,
            'type': 'trade'
        })
    return result, start_eq


def compute_audit(trades, start_equity=10000.0):
    """Compute all equity curve health metrics."""
    if not trades:
        return {'error': 'No trades found'}

    trades.sort(key=lambda t: t['time'])
    n = len(trades)
    profits = [t['profit'] for t in trades]

    # Build equity curve
    equity = [start_equity]
    dates = [trades[0]['time']]
    for t in trades:
        equity.append(equity[-1] + t['profit'])
        dates.append(t['time'])

    # --- 1. Basic stats ---
    total_profit = sum(profits)
    mean_profit = total_profit / n
    median_profit = sorted(profits)[n // 2]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    win_rate = len(wins) / n * 100

    # --- 2. Drawdown analysis ---
    peak = equity[0]
    max_dd_pct = 0
    max_dd_abs = 0
    dd_start_idx = 0
    max_dd_recovery_trades = 0
    current_dd_start = 0
    in_drawdown = False

    for i, e in enumerate(equity):
        if e >= peak:
            if in_drawdown:
                recovery = i - current_dd_start
                max_dd_recovery_trades = max(max_dd_recovery_trades, recovery)
            peak = e
            in_drawdown = False
        else:
            if not in_drawdown:
                current_dd_start = i
                in_drawdown = True
            dd = (peak - e) / peak * 100
            if dd > max_dd_pct:
                max_dd_pct = dd
                max_dd_abs = peak - e

    # If still in drawdown at end
    if in_drawdown:
        max_dd_recovery_trades = max(max_dd_recovery_trades, len(equity) - current_dd_start)

    # --- 3. Flat period detection ---
    # Find longest period where equity didn't make new high
    longest_flat_trades = 0
    longest_flat_days = 0
    flat_start = 0
    current_peak = equity[0]
    for i in range(1, len(equity)):
        if equity[i] > current_peak:
            flat_len = i - flat_start
            if flat_len > longest_flat_trades:
                longest_flat_trades = flat_len
                flat_days = (dates[i] - dates[flat_start]).days if i < len(dates) and flat_start < len(dates) else 0
                longest_flat_days = flat_days
            current_peak = equity[i]
            flat_start = i
    # Check final stretch
    if len(equity) - flat_start > longest_flat_trades:
        longest_flat_trades = len(equity) - flat_start
        longest_flat_days = (dates[-1] - dates[flat_start]).days if flat_start < len(dates) else 0

    # --- 4. Spike dependency ---
    # What % of total profit comes from top 5% of trades
    sorted_profits = sorted(profits, reverse=True)
    top_5_pct_count = max(1, n // 20)
    top_5_pct_profit = sum(sorted_profits[:top_5_pct_count])
    spike_dependency = (top_5_pct_profit / total_profit * 100) if total_profit > 0 else 0

    # Single biggest trade as % of total profit
    max_single = max(profits) if profits else 0
    single_trade_dependency = (max_single / total_profit * 100) if total_profit > 0 else 0

    # --- 5. Monthly consistency ---
    monthly_pnl = defaultdict(float)
    for t in trades:
        key = t['time'].strftime('%Y-%m')
        monthly_pnl[key] += t['profit']

    months = list(monthly_pnl.values())
    losing_months = sum(1 for m in months if m < 0)
    losing_month_pct = losing_months / len(months) * 100 if months else 0

    # Best month as % of total
    best_month = max(months) if months else 0
    best_month_pct = (best_month / total_profit * 100) if total_profit > 0 else 0

    # --- 6. Weekday analysis ---
    weekday_pnl = defaultdict(list)
    for t in trades:
        wd = t['time'].weekday()  # 0=Mon, 4=Fri
        weekday_pnl[wd].append(t['profit'])

    weekday_stats = {}
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for wd in sorted(weekday_pnl.keys()):
        pnls = weekday_pnl[wd]
        w = sum(1 for p in pnls if p > 0)
        l = sum(1 for p in pnls if p <= 0)
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 99.0
        weekday_stats[day_names[wd]] = {
            'trades': len(pnls), 'net': round(sum(pnls), 2),
            'pf': round(pf, 2), 'win_rate': round(w / len(pnls) * 100, 1)
        }

    # Friday close crutch check
    friday_pf = weekday_stats.get('Fri', {}).get('pf', 0)
    other_avg_pf = 0
    other_count = 0
    for d, s in weekday_stats.items():
        if d != 'Fri' and d not in ('Sat', 'Sun') and s['trades'] > 0:
            other_avg_pf += s['pf']
            other_count += 1
    other_avg_pf = other_avg_pf / other_count if other_count > 0 else 1.0
    friday_crutch = friday_pf > 2 * other_avg_pf if other_avg_pf > 0 else False

    # --- 7. Weekend holding check ---
    weekend_trades = 0
    for t in trades:
        wd = t['time'].weekday()
        if wd == 0:  # Monday — trade might have been open over weekend
            weekend_trades += 1
    # Rough heuristic: if trade exits on Monday, it may have been held over weekend
    weekend_pct = weekend_trades / n * 100

    # --- 8. Equity curve linearity (R²) ---
    # Simple linear regression R² on cumulative equity
    import statistics
    x = list(range(len(equity)))
    y = equity
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    slope = ss_xy / ss_xx if ss_xx > 0 else 0
    intercept = y_mean - slope * x_mean
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # --- Compile results ---
    result = {
        'trades': n,
        'total_profit': round(total_profit, 2),
        'mean_profit_per_trade': round(mean_profit, 2),
        'median_profit_per_trade': round(median_profit, 2),
        'win_rate_pct': round(win_rate, 1),
        'max_dd_pct': round(max_dd_pct, 1),
        'max_dd_abs': round(max_dd_abs, 2),
        'max_dd_recovery_trades': max_dd_recovery_trades,
        'longest_flat_trades': longest_flat_trades,
        'longest_flat_days': longest_flat_days,
        'spike_dependency_top5pct': round(spike_dependency, 1),
        'single_trade_dependency_pct': round(single_trade_dependency, 1),
        'monthly_losing_pct': round(losing_month_pct, 1),
        'best_month_pct_of_total': round(best_month_pct, 1),
        'equity_curve_r_squared': round(r_squared, 4),
        'weekday_stats': weekday_stats,
        'friday_crutch_flag': friday_crutch,
        'weekend_exit_pct': round(weekend_pct, 1),
    }

    # --- Flags + Composite Score ---
    # Score: 0 = perfect, higher = worse. REJECT if score >= 5.
    flags = []
    score = 0.0

    if spike_dependency > 50:
        flags.append(f'SPIKE_DEPENDENT: top 5% trades = {spike_dependency:.0f}% of profit')
        score += 1.0  # Common for breakout strategies, only severe with other flags
    if single_trade_dependency > 30:
        flags.append(f'SINGLE_TRADE_RISK: biggest trade = {single_trade_dependency:.0f}% of profit')
        score += 1.5
    if longest_flat_days > 365:
        flags.append(f'LONG_FLAT: {longest_flat_days}d without new equity high')
        score += 1.5 if longest_flat_days > 730 else 1.0  # >2yr = severe
    elif longest_flat_days > 120:
        flags.append(f'FLAT_PERIOD: {longest_flat_days}d without new equity high')
        score += 0.5
    if losing_month_pct > 45:
        flags.append(f'INCONSISTENT: {losing_month_pct:.0f}% of months losing')
        score += 1.0
    if best_month_pct > 40:
        flags.append(f'MONTH_SPIKE: best month = {best_month_pct:.0f}% of total profit')
        score += 1.5
    if friday_crutch:
        flags.append('FRIDAY_CRUTCH: Friday PF > 2x other days')
        score += 0.5  # May be legitimate for calendar strategies
    if r_squared < 0.75:
        flags.append(f'CHOPPY_EQUITY: R2 = {r_squared:.3f} (SEVERE, want >= 0.85)')
        score += 2.0  # SEVERE: strong indicator of beta/regime-dependence
    elif r_squared < 0.85:
        flags.append(f'LOW_R2: R2 = {r_squared:.3f} (want >= 0.85)')
        score += 1.0
    if max_dd_recovery_trades > n * 0.3:
        flags.append(f'SLOW_RECOVERY: {max_dd_recovery_trades} trades to recover from max DD')
        score += 1.0
    if median_profit <= 0:
        flags.append('NEGATIVE_MEDIAN: median trade is a loss')
        score += 0.5  # Normal for trend-following (many small losses, few big wins)

    # Composite interaction: spike dep + low R2 + long flat = BETA DISGUISE
    if spike_dependency > 80 and r_squared < 0.80 and longest_flat_days > 730:
        flags.append('BETA_DISGUISE: spike dep + low R2 + multi-year flat = directional beta, NOT alpha')
        score += 3.0  # Fatal combination

    result['flags'] = flags
    result['composite_score'] = round(score, 1)
    if score >= 5.0:
        result['verdict'] = 'REJECT'
    elif score >= 3.0:
        result['verdict'] = 'FAIL'
    elif score >= 1.5:
        result['verdict'] = 'WARN'
    else:
        result['verdict'] = 'PASS'

    return result, equity, dates


def plot_audit(equity, dates, result, out_path):
    """Generate equity curve audit chart."""
    if not HAS_MPL:
        print('[equity_audit] matplotlib not available, skipping chart')
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f"Equity Curve Audit — {result['trades']} trades, "
                 f"R²={result['equity_curve_r_squared']:.3f}, "
                 f"Verdict: {result['verdict']}", fontsize=13, fontweight='bold')

    # 1. Equity curve with regression line
    ax1 = axes[0, 0]
    ax1.plot(dates, equity, 'b-', linewidth=0.7, label='Equity')
    # Regression line
    x = list(range(len(equity)))
    import statistics
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(equity)
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, equity))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    slope = ss_xy / ss_xx if ss_xx > 0 else 0
    intercept = y_mean - slope * x_mean
    reg_line = [slope * xi + intercept for xi in x]
    ax1.plot(dates, reg_line, 'r--', linewidth=1, alpha=0.7, label=f'Linear fit R²={result["equity_curve_r_squared"]:.3f}')
    ax1.legend(fontsize=8)
    ax1.set_title('Equity Curve + Linearity')
    ax1.grid(True, alpha=0.3)

    # 2. Drawdown
    ax2 = axes[0, 1]
    peak = equity[0]
    dd = []
    for e in equity:
        peak = max(peak, e)
        dd.append((e - peak) / peak * 100 if peak > 0 else 0)
    ax2.fill_between(dates, 0, dd, color='red', alpha=0.5)
    ax2.set_title(f'Drawdown (max {result["max_dd_pct"]:.1f}%, recovery {result["max_dd_recovery_trades"]} trades)')
    ax2.set_ylabel('DD %')
    ax2.grid(True, alpha=0.3)

    # 3. Monthly PnL bar chart
    ax3 = axes[1, 0]
    monthly = defaultdict(float)
    # Reconstruct from equity
    for i in range(1, len(equity)):
        if i < len(dates):
            key = dates[i].strftime('%Y-%m')
            monthly[key] += equity[i] - equity[i - 1]
    months_sorted = sorted(monthly.keys())
    vals = [monthly[m] for m in months_sorted]
    colors = ['green' if v > 0 else 'red' for v in vals]
    ax3.bar(range(len(vals)), vals, color=colors, alpha=0.7)
    ax3.set_title(f'Monthly PnL ({result["monthly_losing_pct"]:.0f}% losing months)')
    ax3.set_xticks(range(0, len(months_sorted), max(1, len(months_sorted) // 10)))
    ax3.set_xticklabels([months_sorted[i] for i in range(0, len(months_sorted), max(1, len(months_sorted) // 10))],
                        rotation=45, fontsize=7)
    ax3.grid(True, alpha=0.3)

    # 4. Flags summary
    ax4 = axes[1, 1]
    ax4.axis('off')
    flags_text = '\n'.join(result['flags']) if result['flags'] else 'ALL CLEAR — No flags'
    color = 'green' if result['verdict'] == 'PASS' else ('orange' if result['verdict'] == 'WARN' else 'red')
    ax4.text(0.05, 0.95, f"VERDICT: {result['verdict']}", transform=ax4.transAxes,
             fontsize=16, fontweight='bold', color=color, va='top')
    ax4.text(0.05, 0.80, flags_text, transform=ax4.transAxes, fontsize=9,
             va='top', fontfamily='monospace', wrap=True)
    # Key metrics
    metrics = (f"Spike dep (top 5%): {result['spike_dependency_top5pct']:.0f}%\n"
               f"Single trade dep: {result['single_trade_dependency_pct']:.0f}%\n"
               f"Longest flat: {result['longest_flat_days']}d\n"
               f"Median trade: ${result['median_profit_per_trade']:.2f}\n"
               f"Weekend exits: {result['weekend_exit_pct']:.0f}%\n"
               f"Friday crutch: {'YES' if result['friday_crutch_flag'] else 'No'}")
    ax4.text(0.05, 0.35, metrics, transform=ax4.transAxes, fontsize=9,
             va='top', fontfamily='monospace')

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'[equity_audit] Chart saved: {out_path}')


def main():
    parser = argparse.ArgumentParser(description='Equity curve audit for EA validation pipeline')
    parser.add_argument('--report', required=True, help='Path to MT5 HTML report')
    parser.add_argument('--out', default=None, help='Output directory (default: same as report)')
    parser.add_argument('--equity', type=float, default=10000.0, help='Starting equity')
    args = parser.parse_args()

    if not os.path.isfile(args.report):
        print(f'ERROR: Report not found: {args.report}')
        sys.exit(1)

    out_dir = Path(args.out) if args.out else Path(args.report).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'[equity_audit] Parsing: {args.report}')
    trades, start_eq = parse_trades_from_report(args.report)
    if args.equity != 10000.0:
        start_eq = args.equity
    print(f'[equity_audit] Found {len(trades)} trades, start equity ${start_eq:.0f}')

    if not trades:
        print('ERROR: No trades found in report')
        sys.exit(1)

    result, equity, dates = compute_audit(trades, start_eq)

    # Save JSON
    json_path = out_dir / 'equity_audit.json'
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f'[equity_audit] JSON saved: {json_path}')

    # Save chart
    if HAS_MPL:
        png_path = out_dir / 'equity_audit.png'
        plot_audit(equity, dates, result, str(png_path))

    # Print summary
    print(f'\n=== EQUITY AUDIT RESULT ===')
    print(f'Trades: {result["trades"]}')
    print(f'Total profit: ${result["total_profit"]:.2f}')
    print(f'Median per trade: ${result["median_profit_per_trade"]:.2f}')
    print(f'Max DD: {result["max_dd_pct"]:.1f}% (recovery: {result["max_dd_recovery_trades"]} trades)')
    print(f'Equity R²: {result["equity_curve_r_squared"]:.4f}')
    print(f'Spike dep (top 5%): {result["spike_dependency_top5pct"]:.0f}%')
    print(f'Losing months: {result["monthly_losing_pct"]:.0f}%')
    print(f'Friday crutch: {"YES [!]" if result["friday_crutch_flag"] else "No"}')
    print(f'Verdict: {result["verdict"]} (score {result["composite_score"]})')
    if result['flags']:
        print(f'Flags:')
        for flag in result['flags']:
            print(f'  [!] {flag}')

    return result


if __name__ == '__main__':
    main()
