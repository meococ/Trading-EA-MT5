"""
Edge Variant Scanner — Iterate parameter variants for gold intraday mechanisms
Tests: SL/TP ratios, direction filters, regime gates, timing variants

Author: Max (AlphaFactory research lane)
Date: 2026-03-21
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import warnings
warnings.filterwarnings('ignore')

# ===========================================================================
# CONFIG
# ===========================================================================
SYMBOL = "XAUUSD+"
TF = mt5.TIMEFRAME_M15
DATE_FROM = datetime(2019, 1, 1)
DATE_TO = datetime(2026, 1, 1)

SPREAD_COST = 0.30  # $0.30 per unit in price terms

# ===========================================================================
# DATA LOADING (reuse from edge_scanner.py)
# ===========================================================================
def load_data():
    if not mt5.initialize():
        print(f"[ERR] MT5 init failed: {mt5.last_error()}")
        sys.exit(1)

    rates = mt5.copy_rates_range(SYMBOL, TF, DATE_FROM, DATE_TO)
    if rates is None or len(rates) == 0:
        print(f"[ERR] No data for {SYMBOL}")
        mt5.shutdown()
        sys.exit(1)

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['dow'] = df.index.dayofweek
    df['date'] = df.index.date
    df['year'] = df.index.year

    # ATR-14
    tr = pd.DataFrame()
    tr['hl'] = df['high'] - df['low']
    tr['hc'] = abs(df['high'] - df['close'].shift(1))
    tr['lc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = tr.max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean()

    # D1 EMA50 for regime detection
    # Build daily close series
    daily_close = df.groupby('date')['close'].last()
    ema50 = daily_close.ewm(span=50, adjust=False).mean()
    ema50_slope = ema50.diff(10) / ema50.shift(10)  # 10-day slope
    regime_map = {}
    for d, slope in ema50_slope.items():
        if pd.isna(slope):
            regime_map[d] = 'flat'
        elif slope > 0.005:
            regime_map[d] = 'trending_up'
        elif slope < -0.005:
            regime_map[d] = 'trending_down'
        else:
            regime_map[d] = 'flat'
    df['regime'] = df['date'].map(regime_map).fillna('flat')

    print(f"[OK] Loaded {len(df)} bars, {df['date'].nunique()} days")
    mt5.shutdown()
    return df


def build_daily(df):
    daily = {}
    for date, group in df.groupby('date'):
        asian = group[(group['hour'] >= 0) & (group['hour'] < 8)]
        if len(asian) < 4:
            continue

        daily[date] = {
            'asian_hi': asian['high'].max(),
            'asian_lo': asian['low'].min(),
            'asian_range': asian['high'].max() - asian['low'].min(),
            'atr': asian['atr14'].iloc[-1] if not pd.isna(asian['atr14'].iloc[-1]) else None,
            'regime': group['regime'].iloc[0],
            'dow': group['dow'].iloc[0],
            'year': group['year'].iloc[0],
            'bars': group
        }
    return daily


# ===========================================================================
# GENERIC TRADE SIMULATOR
# ===========================================================================
def simulate_trade(bars_after_signal, direction, sl_dist, tp_dist, max_hold_bars=16):
    """Walk through bars, return (exit_price, exit_reason)"""
    if len(bars_after_signal) == 0:
        return None, 'no_bars'

    entry = bars_after_signal.iloc[0]['open']

    if direction == 1:  # long
        sl = entry - sl_dist
        tp = entry + tp_dist
    else:  # short
        sl = entry + sl_dist
        tp = entry - tp_dist

    for i in range(min(max_hold_bars, len(bars_after_signal))):
        bar = bars_after_signal.iloc[i]
        if direction == 1:
            if bar['low'] <= sl:
                return sl, 'sl'
            if bar['high'] >= tp:
                return tp, 'tp'
        else:
            if bar['high'] >= sl:
                return sl, 'sl'
            if bar['low'] <= tp:
                return tp, 'tp'

    # Timeout
    last_idx = min(max_hold_bars - 1, len(bars_after_signal) - 1)
    return bars_after_signal.iloc[last_idx]['close'], 'timeout'


# ===========================================================================
# MEC-11 VARIANTS: London Fix Anomaly
# ===========================================================================
def scan_fix_variant(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None,
                     deviation_min=0.3, fix_hour=12, max_hold=8):
    """
    direction_filter: 0=both, 1=long only, -1=short only
    regime_filter: None=all, 'trending_up', 'trending_down', 'trending'(both), 'flat'
    """
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if regime_filter:
            if regime_filter == 'trending':
                if d['regime'] == 'flat':
                    continue
            elif d['regime'] != regime_filter:
                continue

        atr = d['atr']
        # Fix bar: hour=fix_hour, min around 30
        fix_bars = d['bars'][(d['bars']['hour'] == fix_hour) & (d['bars']['minute'] >= 15) & (d['bars']['minute'] <= 30)]
        if len(fix_bars) == 0:
            continue

        fix_close = fix_bars.iloc[-1]['close']
        fix_time = fix_bars.iloc[-1].name

        # Deviation
        direction = 0
        if fix_close > d['asian_hi']:
            deviation = fix_close - d['asian_hi']
            direction = -1  # short (revert down)
        elif fix_close < d['asian_lo']:
            deviation = d['asian_lo'] - fix_close
            direction = 1  # long (revert up)
        else:
            continue

        if deviation < deviation_min * atr:
            continue
        if direction_filter != 0 and direction != direction_filter:
            continue

        # Entry
        post = d['bars'].loc[d['bars'].index > fix_time]
        if len(post) < 2:
            continue

        entry = post.iloc[0]['open']
        exit_p, exit_r = simulate_trade(post, direction, sl_mult * atr, tp_mult * atr, max_hold)
        if exit_p is None:
            continue

        pnl = (exit_p - entry) * direction - SPREAD_COST
        results.append({
            'date': date, 'year': d['year'], 'pnl': pnl,
            'direction': direction, 'exit_reason': exit_r
        })

    return pd.DataFrame(results)


# ===========================================================================
# MEC-02 VARIANTS: Asian Sweep Fade
# ===========================================================================
def scan_sweep_variant(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None,
                       sweep_min_atr=0.1, scan_hours=(8,11), max_hold=16):
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if d['asian_range'] < 0.5 * d['atr']:
            continue
        if regime_filter:
            if regime_filter == 'trending':
                if d['regime'] == 'flat':
                    continue
            elif d['regime'] != regime_filter:
                continue

        atr = d['atr']
        early = d['bars'][(d['bars']['hour'] >= scan_hours[0]) & (d['bars']['hour'] <= scan_hours[1])]

        for _, bar in early.iterrows():
            sweep_hi = bar['high'] > d['asian_hi'] + sweep_min_atr * atr
            sweep_lo = bar['low'] < d['asian_lo'] - sweep_min_atr * atr
            close_inside = d['asian_lo'] <= bar['close'] <= d['asian_hi']

            direction = 0
            if sweep_hi and not sweep_lo and close_inside:
                direction = -1
            elif sweep_lo and not sweep_hi and close_inside:
                direction = 1
            else:
                continue

            if direction_filter != 0 and direction != direction_filter:
                continue

            remaining = d['bars'].loc[d['bars'].index > bar.name]
            if len(remaining) < 2:
                continue

            entry = remaining.iloc[0]['open']
            exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, max_hold)
            if exit_p is None:
                continue

            pnl = (exit_p - entry) * direction - SPREAD_COST
            results.append({
                'date': date, 'year': d['year'], 'pnl': pnl,
                'direction': direction, 'exit_reason': exit_r
            })
            break  # 1 per day

    return pd.DataFrame(results)


# ===========================================================================
# MEC-EXTRA: Pure session breakout (Asian range) with different SL/TP
# ===========================================================================
def scan_breakout_variant(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None,
                          entry_hours=(8, 17), brk_buffer_atr=0.1, max_hold=16, skip_wed=True):
    """Classic Asian range breakout — buy above Asian high, sell below Asian low.
    Different from sweep fade: this trades WITH the breakout, not against it."""
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if skip_wed and d['dow'] == 2:
            continue
        if d['asian_range'] < 0.5 * d['atr'] or d['asian_range'] > 8.0 * d['atr']:
            continue
        if regime_filter:
            if regime_filter == 'trending':
                if d['regime'] == 'flat':
                    continue
            elif d['regime'] != regime_filter:
                continue

        atr = d['atr']
        buf = brk_buffer_atr * atr

        trading_bars = d['bars'][(d['bars']['hour'] >= entry_hours[0]) & (d['bars']['hour'] <= entry_hours[1])]

        for idx in range(1, len(trading_bars)):
            bar = trading_bars.iloc[idx]
            prev = trading_bars.iloc[idx - 1]

            # Closed-bar breakout detection (shift=1 logic)
            direction = 0
            body = abs(prev['close'] - prev['open'])
            rng = prev['high'] - prev['low']
            if rng <= 0:
                continue
            body_ratio = body / rng

            if body_ratio < 0.35:  # need decent body
                continue

            if prev['close'] > d['asian_hi'] + buf and prev['close'] > prev['open']:
                direction = 1  # bullish breakout
            elif prev['close'] < d['asian_lo'] - buf and prev['close'] < prev['open']:
                direction = -1  # bearish breakout
            else:
                continue

            if direction_filter != 0 and direction != direction_filter:
                continue

            # Entry at current bar open
            entry = bar['open']
            remaining = d['bars'].loc[d['bars'].index >= bar.name]
            exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, max_hold)
            if exit_p is None:
                continue

            pnl = (exit_p - entry) * direction - SPREAD_COST
            results.append({
                'date': date, 'year': d['year'], 'pnl': pnl,
                'direction': direction, 'exit_reason': exit_r
            })
            break  # 1 per day

    return pd.DataFrame(results)


# ===========================================================================
# ANALYSIS
# ===========================================================================
def quick_stats(df_r):
    if df_r is None or len(df_r) == 0:
        return {'n': 0, 'n_yr': 0, 'wr': 0, 'pf': 0, 'net': 0, 'avg': 0}
    n = len(df_r)
    yrs = max(df_r['year'].nunique(), 1)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    return {
        'n': n,
        'n_yr': n / yrs,
        'wr': len(wins) / n * 100,
        'pf': gp / gl,
        'net': df_r['pnl'].sum(),
        'avg': df_r['pnl'].mean(),
        # Yearly PFs
        'years_pos': sum(1 for _, yg in df_r.groupby('year') if yg['pnl'].sum() > 0),
        'years_tot': yrs
    }


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("  GOLD EDGE VARIANT SCANNER")
    print("  XAUUSD+ M15 | 2019-2025 | Parameter grid")
    print("=" * 80)

    df = load_data()
    daily = build_daily(df)
    print(f"[OK] {len(daily)} trading days\n")

    # Count regime distribution
    regime_counts = {}
    for d in daily.values():
        r = d['regime']
        regime_counts[r] = regime_counts.get(r, 0) + 1
    print(f"Regime distribution: {regime_counts}\n")

    # Parameter grids
    sl_tp_combos = [
        (0.5, 0.5),   # tight scalp
        (0.5, 0.75),
        (0.5, 1.0),
        (0.75, 0.75),
        (0.75, 1.0),
        (0.75, 1.5),
        (1.0, 1.0),
        (1.0, 1.5),
        (1.0, 2.0),
        (1.5, 2.0),
        (1.5, 3.0),   # wide swing
    ]

    regimes = [None, 'trending', 'trending_up', 'flat']
    directions = [0, 1, -1]  # both, long-only, short-only

    all_results = []

    # ==============================================================
    # SCAN 1: MEC-11 London Fix variants
    # ==============================================================
    print("=" * 80)
    print("  SCANNING MEC-11: London Fix Anomaly Variants")
    print("=" * 80)
    for sl, tp in sl_tp_combos:
        for rgm in regimes:
            for dir_f in directions:
                r = scan_fix_variant(daily, sl, tp, dir_f, rgm)
                s = quick_stats(r)
                if s['n'] >= 30:  # minimum sample
                    all_results.append({
                        'mec': 'MEC-11_Fix',
                        'sl': sl, 'tp': tp,
                        'dir': dir_f, 'regime': rgm or 'all',
                        **s
                    })

    # ==============================================================
    # SCAN 2: MEC-02 Asian Sweep Fade variants
    # ==============================================================
    print("  SCANNING MEC-02: Asian Sweep Fade Variants")
    for sl, tp in sl_tp_combos:
        for rgm in regimes:
            for dir_f in directions:
                r = scan_sweep_variant(daily, sl, tp, dir_f, rgm)
                s = quick_stats(r)
                if s['n'] >= 30:
                    all_results.append({
                        'mec': 'MEC-02_Sweep',
                        'sl': sl, 'tp': tp,
                        'dir': dir_f, 'regime': rgm or 'all',
                        **s
                    })

    # ==============================================================
    # SCAN 3: Classic Asian Breakout (MEC-01 variant — different SL/TP)
    # ==============================================================
    print("  SCANNING MEC-01: Asian Range Breakout Variants")
    for sl, tp in sl_tp_combos:
        for rgm in regimes:
            for dir_f in directions:
                r = scan_breakout_variant(daily, sl, tp, dir_f, rgm)
                s = quick_stats(r)
                if s['n'] >= 30:
                    all_results.append({
                        'mec': 'MEC-01_Breakout',
                        'sl': sl, 'tp': tp,
                        'dir': dir_f, 'regime': rgm or 'all',
                        **s
                    })

    # ==============================================================
    # RESULTS
    # ==============================================================
    results_df = pd.DataFrame(all_results)

    # Sort by PF descending
    results_df.sort_values('pf', ascending=False, inplace=True)

    print(f"\n{'='*80}")
    print(f"  TOP 30 VARIANTS BY PROFIT FACTOR (min 30 trades)")
    print(f"{'='*80}")
    print(f"{'Mech':<20} {'SL':<5} {'TP':<5} {'Dir':<5} {'Regime':<15} {'N':<6} {'N/yr':<6} {'WR%':<6} {'PF':<7} {'Net$':<10} {'Yr+':<5}")

    for _, row in results_df.head(30).iterrows():
        dir_str = {0: 'both', 1: 'long', -1: 'shrt'}[row['dir']]
        print(f"{row['mec']:<20} {row['sl']:<5.1f} {row['tp']:<5.1f} {dir_str:<5} {row['regime']:<15} {row['n']:<6} {row['n_yr']:<6.0f} {row['wr']:<6.1f} {row['pf']:<7.2f} {row['net']:<10.1f} {row['years_pos']}/{row['years_tot']}")

    # Also show top variants per mechanism
    for mec in ['MEC-01_Breakout', 'MEC-11_Fix', 'MEC-02_Sweep']:
        sub = results_df[results_df['mec'] == mec].head(5)
        print(f"\n  Top 5 {mec}:")
        for _, row in sub.iterrows():
            dir_str = {0: 'both', 1: 'long', -1: 'shrt'}[row['dir']]
            print(f"    SL={row['sl']:.1f} TP={row['tp']:.1f} {dir_str:<5} {row['regime']:<15} n={row['n']:<4} PF={row['pf']:.2f} Net=${row['net']:.1f} Yr+={row['years_pos']}/{row['years_tot']}")

    # Quick edge summary
    print(f"\n{'='*80}")
    print(f"  EDGE VERDICT")
    print(f"{'='*80}")
    best = results_df.iloc[0] if len(results_df) > 0 else None
    if best is not None and best['pf'] > 1.0:
        print(f"  ✅ BEST: {best['mec']} SL={best['sl']} TP={best['tp']} dir={best['dir']} regime={best['regime']}")
        print(f"     PF={best['pf']:.2f}, N={best['n']}, N/yr={best['n_yr']:.0f}, WR={best['wr']:.1f}%")
        print(f"     Net=${best['net']:.2f}, Years positive: {best['years_pos']}/{best['years_tot']}")
        if best['pf'] < 1.2:
            print(f"     ⚠️  WARNING: PF < 1.2 — edge may be too thin after spread/slippage")
        if best['n_yr'] < 50:
            print(f"     ⚠️  WARNING: <50 trades/yr — may not reach 120+ target")
    else:
        print(f"  ❌ NO VARIANT found with PF > 1.0")
        print(f"     Gold intraday scalping does NOT have a robust edge with these mechanisms")

    # Count how many variants are profitable
    profitable = len(results_df[results_df['pf'] > 1.0])
    total = len(results_df)
    print(f"\n  Profitable variants: {profitable}/{total} ({profitable/total*100:.0f}%)")

    print(f"\n{'='*80}")
