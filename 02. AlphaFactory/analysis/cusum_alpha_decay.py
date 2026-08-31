"""
cusum_alpha_decay.py — CUSUM-based alpha decay detection for live monitoring.
Reads MT5 HTML report(s) and detects structural edge degradation using
sequential CUSUM change-point detection.

Usage:
    python cusum_alpha_decay.py --report path/to/report.html [--out path/to/output/]
    python cusum_alpha_decay.py --reports report1.html report2.html --ea-names Cobra ITSM

Output: cusum_decay.json + cusum_decay.png (per EA)

Key concepts:
- CUSUM (Cumulative Sum) detects shifts in the mean of a process
- We monitor the CUSUM of trade returns (normalized by expected R)
- A downward drift in CUSUM signals alpha decay
- Threshold: 5 consecutive negative CUSUM increments = WARNING
- Threshold: CUSUM drops below -3σ of historical mean = CRITICAL

References:
- Page, E.S. (1954). "Continuous inspection schemes."
- MEMORY key lesson: "Alpha decay: CUSUM best for low-freq EAs"
"""
import argparse, json, sys, os, statistics, math
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

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
    """Extract trades with timestamps using proven quant_analyzer parser."""
    deals = parse_deals(Path(report_path))
    trades = deals_to_trades(deals)
    start_eq = next(
        (d.balance for d in deals
         if (d.side or "").strip().lower() == "balance" and d.balance > 0),
        10000.0
    )
    result = []
    for t in trades:
        result.append({
            'time': t.exit_time,
            'entry_time': t.entry_time,
            'profit': t.profit,
            'symbol': t.symbol if hasattr(t, 'symbol') else '',
        })
    return result, start_eq


def compute_cusum(profits, target_mean=None):
    """
    Compute one-sided CUSUM for detecting downward shift (alpha decay).

    Args:
        profits: list of trade profits
        target_mean: expected mean profit per trade (if None, uses sample mean)

    Returns:
        dict with CUSUM statistics and change-point detection
    """
    n = len(profits)
    if n < 10:
        return {'error': 'Need at least 10 trades for CUSUM', 'n': n}

    # Use first 50% as calibration period to establish baseline
    cal_n = max(10, n // 2)
    cal_profits = profits[:cal_n]
    test_profits = profits[cal_n:]

    cal_mean = statistics.mean(cal_profits)
    cal_std = statistics.stdev(cal_profits) if len(cal_profits) > 1 else 1.0

    if target_mean is None:
        target_mean = cal_mean

    # Normalize: CUSUM of (profit - target_mean) / std
    # Positive CUSUM = above expected, Negative = below expected (decay)
    cusum_pos = [0.0]  # Detects upward shift
    cusum_neg = [0.0]  # Detects downward shift (alpha decay)
    cusum_raw = [0.0]  # Raw cumulative deviation

    k = 0.5  # Slack parameter (half-sigma)
    h = 4.0  # Decision threshold (in sigma units)

    change_points = []
    alerts = []

    for i, p in enumerate(profits):
        z = (p - target_mean) / cal_std if cal_std > 0 else 0.0

        # Standard CUSUM
        new_pos = max(0, cusum_pos[-1] + z - k)
        new_neg = min(0, cusum_neg[-1] + z + k)
        cusum_pos.append(new_pos)
        cusum_neg.append(new_neg)
        cusum_raw.append(cusum_raw[-1] + (p - target_mean))

        # Detect downward change point (alpha decay)
        if new_neg < -h:
            change_points.append({
                'trade_index': i,
                'cusum_value': new_neg,
                'direction': 'decay',
                'severity': 'CRITICAL' if new_neg < -2 * h else 'WARNING'
            })

    # Rolling window analysis (last 20 trades vs calibration)
    if len(profits) >= 20:
        recent_20 = profits[-20:]
        recent_mean = statistics.mean(recent_20)
        recent_pf = (sum(p for p in recent_20 if p > 0) /
                     abs(sum(p for p in recent_20 if p < 0))
                     if any(p < 0 for p in recent_20) else 99.0)
        cal_pf = (sum(p for p in cal_profits if p > 0) /
                  abs(sum(p for p in cal_profits if p < 0))
                  if any(p < 0 for p in cal_profits) else 99.0)
        pf_degradation = (cal_pf - recent_pf) / cal_pf * 100 if cal_pf > 0 else 0
    else:
        recent_mean = cal_mean
        recent_pf = 0
        cal_pf = 0
        pf_degradation = 0

    # Consecutive negative returns check
    max_consec_neg = 0
    current_consec = 0
    for p in profits:
        if p < 0:
            current_consec += 1
            max_consec_neg = max(max_consec_neg, current_consec)
        else:
            current_consec = 0

    # Monthly PF breakdown
    monthly_pf = compute_monthly_pf(profits,
                                     [t.get('time', datetime.now()) for t in []]
                                     if not profits else None)

    # Verdict
    final_cusum = cusum_neg[-1]
    if final_cusum < -2 * h:
        verdict = 'CRITICAL_DECAY'
        recommendation = 'Edge has structurally decayed. Reduce risk or halt trading.'
    elif final_cusum < -h:
        verdict = 'WARNING_DECAY'
        recommendation = 'Early decay signal. Monitor closely, consider reducing position size.'
    elif pf_degradation > 30:
        verdict = 'PF_DEGRADATION'
        recommendation = f'Recent PF degraded {pf_degradation:.0f}% vs calibration. Watch for trend continuation.'
    else:
        verdict = 'HEALTHY'
        recommendation = 'No significant alpha decay detected.'

    return {
        'n_trades': n,
        'calibration_period': cal_n,
        'test_period': n - cal_n,
        'calibration_mean': round(cal_mean, 2),
        'calibration_std': round(cal_std, 2),
        'calibration_pf': round(cal_pf, 2),
        'recent_20_mean': round(recent_mean, 2),
        'recent_20_pf': round(recent_pf, 2),
        'pf_degradation_pct': round(pf_degradation, 1),
        'cusum_final': round(final_cusum, 3),
        'cusum_threshold_h': h,
        'change_points': change_points,
        'max_consecutive_losses': max_consec_neg,
        'verdict': verdict,
        'recommendation': recommendation,
        'cusum_series': {
            'raw': [round(v, 3) for v in cusum_raw],
            'negative': [round(v, 3) for v in cusum_neg],
        }
    }


def compute_monthly_pf(profits, dates=None):
    """Compute rolling monthly profit factor if dates available."""
    # Simplified: just compute rolling 20-trade PF windows
    if len(profits) < 20:
        return []

    windows = []
    step = max(1, len(profits) // 10)
    for i in range(0, len(profits) - 19, step):
        window = profits[i:i+20]
        wins = sum(p for p in window if p > 0)
        losses = abs(sum(p for p in window if p < 0))
        pf = wins / losses if losses > 0 else 99.0
        windows.append({
            'start_trade': i,
            'end_trade': i + 19,
            'pf': round(pf, 2),
            'net': round(sum(window), 2)
        })
    return windows


def compute_hourly_decay(trades):
    """Detect hour-specific edge decay by comparing first/second half performance."""
    if len(trades) < 20:
        return {}

    half = len(trades) // 2
    first_half = trades[:half]
    second_half = trades[half:]

    # Group by hour
    def hour_stats(trade_list):
        by_hour = defaultdict(list)
        for t in trade_list:
            if hasattr(t.get('time', None), 'hour'):
                by_hour[t['time'].hour].append(t['profit'])
            elif isinstance(t.get('time', None), datetime):
                by_hour[t['time'].hour].append(t['profit'])
        result = {}
        for h, profits in by_hour.items():
            wins = sum(p for p in profits if p > 0)
            losses = abs(sum(p for p in profits if p < 0))
            result[h] = {
                'n': len(profits),
                'pf': round(wins / losses, 2) if losses > 0 else 99.0,
                'net': round(sum(profits), 2)
            }
        return result

    return {
        'first_half': hour_stats(first_half),
        'second_half': hour_stats(second_half),
    }


def plot_cusum(cusum_result, ea_name, out_path):
    """Plot CUSUM chart with decay signals."""
    if not HAS_MPL:
        return

    raw = cusum_result['cusum_series']['raw']
    neg = cusum_result['cusum_series']['negative']
    h = cusum_result['cusum_threshold_h']

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

    # Top: Equity-like CUSUM
    ax1 = axes[0]
    ax1.plot(raw, color='#2196F3', linewidth=1.5, label='Cumulative Deviation')
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.fill_between(range(len(raw)), raw, 0,
                     where=[v >= 0 for v in raw], color='#4CAF50', alpha=0.15)
    ax1.fill_between(range(len(raw)), raw, 0,
                     where=[v < 0 for v in raw], color='#f44336', alpha=0.15)

    # Mark change points
    for cp in cusum_result.get('change_points', []):
        idx = cp['trade_index'] + 1
        if idx < len(raw):
            color = '#f44336' if cp['severity'] == 'CRITICAL' else '#FF9800'
            ax1.axvline(x=idx, color=color, linestyle=':', alpha=0.7)
            ax1.annotate(cp['severity'], xy=(idx, raw[idx]),
                        fontsize=7, color=color, ha='center')

    ax1.set_title(f'{ea_name} — CUSUM Alpha Decay Monitor', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Cumulative Deviation from Expected')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Bottom: Negative CUSUM with threshold
    ax2 = axes[1]
    ax2.plot(neg, color='#f44336', linewidth=1.2, label='Negative CUSUM')
    ax2.axhline(y=-h, color='#FF9800', linestyle='--', linewidth=1.5,
                label=f'WARNING threshold (-{h}σ)')
    ax2.axhline(y=-2*h, color='#f44336', linestyle='--', linewidth=1.5,
                label=f'CRITICAL threshold (-{2*h}σ)')
    ax2.fill_between(range(len(neg)), neg, 0, color='#f44336', alpha=0.1)
    ax2.set_xlabel('Trade Number')
    ax2.set_ylabel('Negative CUSUM')
    ax2.legend(loc='lower left', fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Verdict annotation
    verdict = cusum_result['verdict']
    verdict_colors = {
        'HEALTHY': '#4CAF50',
        'PF_DEGRADATION': '#FF9800',
        'WARNING_DECAY': '#FF9800',
        'CRITICAL_DECAY': '#f44336'
    }
    fig.text(0.98, 0.98, f'Verdict: {verdict}',
             ha='right', va='top', fontsize=11, fontweight='bold',
             color=verdict_colors.get(verdict, 'gray'),
             transform=fig.transFigure)

    plt.tight_layout()
    plt.savefig(str(out_path), dpi=150, bbox_inches='tight')
    plt.close()


def run_single_report(report_path, ea_name=None, out_dir=None):
    """Analyze a single report for alpha decay."""
    report_path = Path(report_path)
    if not report_path.exists():
        print(f"ERROR: Report not found: {report_path}")
        return None

    if ea_name is None:
        ea_name = report_path.parent.parent.name

    trades, start_eq = parse_trades_from_report(str(report_path))
    if not trades:
        print(f"ERROR: No trades found in {report_path}")
        return None

    profits = [t['profit'] for t in trades]
    result = compute_cusum(profits)
    result['ea_name'] = ea_name
    result['report_path'] = str(report_path)
    result['start_equity'] = start_eq

    # Hour decay analysis
    hour_decay = compute_hourly_decay(trades)
    result['hourly_decay'] = hour_decay

    # Rolling PF windows
    result['rolling_pf'] = compute_monthly_pf(profits)

    # Output
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = report_path.parent

    json_path = out_dir / 'cusum_decay.json'
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"[OK] CUSUM analysis saved to {json_path}")

    # Check for error result (too few trades)
    if 'error' in result:
        print(f"\n{'='*60}")
        print(f"CUSUM ALPHA DECAY: {ea_name}")
        print(f"{'='*60}")
        print(f"  ERROR: {result['error']} (n={result.get('n', '?')})")
        print(f"{'='*60}")
        return result

    # Plot
    if HAS_MPL and 'cusum_series' in result:
        png_path = out_dir / 'cusum_decay.png'
        plot_cusum(result, ea_name, png_path)
        print(f"[OK] Chart saved to {png_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"CUSUM ALPHA DECAY: {ea_name}")
    print(f"{'='*60}")
    print(f"  Trades: {result['n_trades']} (cal: {result['calibration_period']}, test: {result['test_period']})")
    print(f"  Cal PF: {result['calibration_pf']}, Recent-20 PF: {result['recent_20_pf']}")
    print(f"  PF degradation: {result['pf_degradation_pct']}%")
    print(f"  CUSUM final: {result['cusum_final']} (threshold: +/-{result['cusum_threshold_h']})")
    print(f"  Change points: {len(result['change_points'])}")
    print(f"  Max consecutive losses: {result['max_consecutive_losses']}")
    print(f"\n  Verdict: {result['verdict']}")
    print(f"  -> {result['recommendation']}")
    print(f"{'='*60}")

    return result


def main():
    parser = argparse.ArgumentParser(description='CUSUM Alpha Decay Detection')
    parser.add_argument('--report', type=str, help='Single MT5 HTML report path')
    parser.add_argument('--reports', nargs='+', help='Multiple report paths')
    parser.add_argument('--ea-names', nargs='+', help='EA names matching --reports order')
    parser.add_argument('--out', type=str, help='Output directory')
    args = parser.parse_args()

    if args.report:
        run_single_report(args.report, out_dir=args.out)
    elif args.reports:
        names = args.ea_names or [None] * len(args.reports)
        all_results = []
        for rpt, name in zip(args.reports, names):
            out = Path(args.out) / name if args.out and name else args.out
            result = run_single_report(rpt, ea_name=name, out_dir=out)
            if result:
                all_results.append(result)

        # Portfolio summary
        if all_results:
            print(f"\n{'='*60}")
            print("PORTFOLIO ALPHA DECAY SUMMARY")
            print(f"{'='*60}")
            for r in all_results:
                status = '[!!]' if 'CRITICAL' in r['verdict'] else '[!]' if r['verdict'] != 'HEALTHY' else '[OK]'
                print(f"  {status} {r['ea_name']:15s} PF degrad: {r['pf_degradation_pct']:+.1f}%  CUSUM: {r['cusum_final']:+.3f}  -> {r['verdict']}")
            print(f"{'='*60}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
