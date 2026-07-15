"""
Edge Scanner — Python scan for 3 untested gold intraday mechanisms
MEC-11: London Fix Anomaly (10:30 AM London)
MEC-13: Asian Stop Hunt pre-London
MEC-02: Asian Sweep Fade

Uses MetaTrader5 Python API to pull XAUUSD+ M15 OHLCV data.
Outputs: per-mechanism signal stats, simulated P&L, yearly breakdown.

Author: Max (AlphaFactory research lane)
Date: 2026-03-21
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

# Server time offsets (E8 = UTC+2 winter, UTC+3 summer)
# We'll detect DST from the data. For now assume UTC+2 baseline.
SERVER_UTC_OFFSET = 2  # hours

# Asian session (server hours): 00:00–07:59 server = 22:00–05:59 UTC (prev day)
ASIAN_START_H = 0
ASIAN_END_H = 8      # exclusive

# London open server hour
LONDON_START_H = 8

# London Fix: 10:30 AM London = 10:30 UTC in winter = 12:30 server (UTC+2)
# In summer (UTC+3): 10:30 UTC = 13:30 server but London is BST=UTC+1 so 10:30 BST = 09:30 UTC = 12:30 server
# Simplification: fix bar = server hour 12, minute 30 → bar starting at 12:15 or 12:30
LONDON_FIX_SERVER_H = 12  # 10:30 London ≈ 12:30 server (approximate)
LONDON_FIX_SERVER_M = 30

# Pre-London stop hunt window: 07:00–07:59 server (05:00-05:59 UTC)
PRE_LONDON_H = 7

# Spread cost estimate (points) — gold on E8
SPREAD_COST_PTS = 30  # ~$0.30 per micro lot

# Risk per trade (for P&L sizing) — fixed SL/TP approach
FIXED_SL_ATR_MULT = 1.0
FIXED_TP_ATR_MULT = 1.5

# ===========================================================================
# DATA LOADING
# ===========================================================================
def load_data():
    """Load M15 data from MT5"""
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

    # Add time components
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['dow'] = df.index.dayofweek  # 0=Mon, 4=Fri
    df['date'] = df.index.date
    df['year'] = df.index.year

    # Calculate ATR-14 on M15
    tr = pd.DataFrame()
    tr['hl'] = df['high'] - df['low']
    tr['hc'] = abs(df['high'] - df['close'].shift(1))
    tr['lc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = tr.max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean()

    print(f"[OK] Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    print(f"     Years: {df['year'].min()}-{df['year'].max()}")

    mt5.shutdown()
    return df


def build_daily_sessions(df):
    """Build daily Asian range (H/L during Asian session)"""
    daily = {}
    for date, group in df.groupby('date'):
        asian = group[(group['hour'] >= ASIAN_START_H) & (group['hour'] < ASIAN_END_H)]
        if len(asian) < 4:  # need at least 4 bars (1h) of Asian data
            continue

        asian_hi = asian['high'].max()
        asian_lo = asian['low'].min()
        asian_range = asian_hi - asian_lo
        asian_close = asian['close'].iloc[-1]
        asian_atr = asian['atr14'].iloc[-1] if not pd.isna(asian['atr14'].iloc[-1]) else None

        # London bars
        london = group[(group['hour'] >= LONDON_START_H) & (group['hour'] < 18)]

        # Pre-London bar (07:xx)
        pre_london = group[group['hour'] == PRE_LONDON_H]

        # Fix bar (12:30 server → bar starting at 12:15 or 12:30)
        fix_bars = group[(group['hour'] == LONDON_FIX_SERVER_H) & (group['minute'] >= 15) & (group['minute'] <= 30)]

        daily[date] = {
            'asian_hi': asian_hi,
            'asian_lo': asian_lo,
            'asian_range': asian_range,
            'asian_close': asian_close,
            'asian_atr': asian_atr,
            'london': london,
            'pre_london': pre_london,
            'fix_bars': fix_bars,
            'all_bars': group,
            'dow': group['dow'].iloc[0],
            'year': group['year'].iloc[0]
        }

    return daily


# ===========================================================================
# MEC-11: London Fix Anomaly Scanner
# ===========================================================================
def scan_london_fix(daily):
    """
    Hypothesis: Price deviates before LBMA AM Fix (10:30 London ≈ 12:30 server).
    After fix, price reverts toward pre-deviation level.

    Signal: At fix bar close (12:30 server), if price > asian_hi → short (revert down)
                                              if price < asian_lo → long (revert up)
    TP/SL: ATR-based. Hold max 2h (8 bars).
    """
    results = []

    for date, d in daily.items():
        if d['asian_atr'] is None or d['asian_atr'] <= 0:
            continue
        if d['dow'] >= 5:  # skip weekends
            continue
        if len(d['fix_bars']) == 0:
            continue

        atr = d['asian_atr']
        fix_bar = d['fix_bars'].iloc[-1]  # last bar in fix window
        fix_close = fix_bar['close']
        fix_time = fix_bar.name

        asian_hi = d['asian_hi']
        asian_lo = d['asian_lo']
        asian_mid = (asian_hi + asian_lo) / 2

        # Measure deviation from Asian range
        deviation = 0
        direction = 0  # 1=long, -1=short

        if fix_close > asian_hi:
            # Price above Asian high at fix → expect reversion down
            deviation = fix_close - asian_hi
            direction = -1  # short
        elif fix_close < asian_lo:
            # Price below Asian low at fix → expect reversion up
            deviation = asian_lo - fix_close
            direction = 1  # long
        else:
            # Price inside Asian range at fix → no signal
            continue

        # Only trade if deviation is meaningful (> 0.3 ATR)
        if deviation < 0.3 * atr:
            continue

        # Simulate entry at next bar open after fix
        post_fix = d['all_bars'].loc[d['all_bars'].index > fix_time]
        if len(post_fix) < 2:
            continue

        entry_price = post_fix.iloc[0]['open']
        sl_dist = FIXED_SL_ATR_MULT * atr
        tp_dist = FIXED_TP_ATR_MULT * atr

        if direction == 1:  # long
            sl = entry_price - sl_dist
            tp = entry_price + tp_dist
        else:  # short
            sl = entry_price + sl_dist
            tp = entry_price - tp_dist

        # Walk through subsequent bars (max 8 bars = 2h)
        exit_price = None
        exit_reason = None
        for i in range(len(post_fix)):
            if i >= 8:  # max hold
                exit_price = post_fix.iloc[i]['open']
                exit_reason = 'timeout'
                break

            bar = post_fix.iloc[i]
            if direction == 1:  # long
                if bar['low'] <= sl:
                    exit_price = sl
                    exit_reason = 'sl'
                    break
                if bar['high'] >= tp:
                    exit_price = tp
                    exit_reason = 'tp'
                    break
            else:  # short
                if bar['high'] >= sl:
                    exit_price = sl
                    exit_reason = 'sl'
                    break
                if bar['low'] <= tp:
                    exit_price = tp
                    exit_reason = 'tp'
                    break

        if exit_price is None:
            exit_price = post_fix.iloc[-1]['close']
            exit_reason = 'eod'

        # P&L
        pnl_raw = (exit_price - entry_price) * direction
        pnl_net = pnl_raw - (SPREAD_COST_PTS * 0.01)  # spread in price terms

        results.append({
            'date': date,
            'year': d['year'],
            'dow': d['dow'],
            'direction': direction,
            'deviation_atr': deviation / atr,
            'entry': entry_price,
            'exit': exit_price,
            'exit_reason': exit_reason,
            'pnl_raw': pnl_raw,
            'pnl_net': pnl_net,
            'atr': atr
        })

    return pd.DataFrame(results)


# ===========================================================================
# MEC-13: Asian Stop Hunt pre-London Scanner
# ===========================================================================
def scan_asian_stop_hunt(daily):
    """
    Hypothesis: In the bar(s) just before London open (07:xx server),
    price sweeps Asian H or L then reverses back inside range.
    Trade: Fade the sweep (buy if sweep low then close inside, sell if sweep high then close inside).
    """
    results = []

    for date, d in daily.items():
        if d['asian_atr'] is None or d['asian_atr'] <= 0:
            continue
        if d['dow'] >= 5:
            continue
        if len(d['pre_london']) == 0:
            continue

        atr = d['asian_atr']
        asian_hi = d['asian_hi']
        asian_lo = d['asian_lo']
        asian_range = d['asian_range']

        # Skip if Asian range too narrow (< 0.5 ATR)
        if asian_range < 0.5 * atr:
            continue

        # Check pre-London bars for sweep pattern
        for _, bar in d['pre_london'].iterrows():
            sweep_hi = bar['high'] > asian_hi  # swept above
            sweep_lo = bar['low'] < asian_lo   # swept below
            close_inside = bar['close'] >= asian_lo and bar['close'] <= asian_hi

            direction = 0
            if sweep_lo and not sweep_hi and close_inside:
                # Swept low, closed inside → long (stop hunt completed)
                direction = 1
            elif sweep_hi and not sweep_lo and close_inside:
                # Swept high, closed inside → short
                direction = -1
            else:
                continue

            # Entry at London open (next bar after 07:xx)
            london_bars = d['london']
            if len(london_bars) < 2:
                continue

            entry_price = london_bars.iloc[0]['open']
            sl_dist = FIXED_SL_ATR_MULT * atr
            tp_dist = FIXED_TP_ATR_MULT * atr

            if direction == 1:
                sl = entry_price - sl_dist
                tp = entry_price + tp_dist
            else:
                sl = entry_price + sl_dist
                tp = entry_price - tp_dist

            # Walk max 12 bars (3h)
            exit_price = None
            exit_reason = None
            for i in range(min(12, len(london_bars))):
                lbar = london_bars.iloc[i]
                if direction == 1:
                    if lbar['low'] <= sl:
                        exit_price = sl; exit_reason = 'sl'; break
                    if lbar['high'] >= tp:
                        exit_price = tp; exit_reason = 'tp'; break
                else:
                    if lbar['high'] >= sl:
                        exit_price = sl; exit_reason = 'sl'; break
                    if lbar['low'] <= tp:
                        exit_price = tp; exit_reason = 'tp'; break

            if exit_price is None:
                exit_price = london_bars.iloc[min(11, len(london_bars)-1)]['close']
                exit_reason = 'timeout'

            pnl_raw = (exit_price - entry_price) * direction
            pnl_net = pnl_raw - (SPREAD_COST_PTS * 0.01)

            results.append({
                'date': date,
                'year': d['year'],
                'dow': d['dow'],
                'direction': direction,
                'sweep_type': 'low_sweep' if direction == 1 else 'high_sweep',
                'entry': entry_price,
                'exit': exit_price,
                'exit_reason': exit_reason,
                'pnl_raw': pnl_raw,
                'pnl_net': pnl_net,
                'atr': atr
            })
            break  # only 1 signal per day

    return pd.DataFrame(results)


# ===========================================================================
# MEC-02: Asian Sweep Fade Scanner
# ===========================================================================
def scan_asian_sweep_fade(daily):
    """
    Hypothesis: During first 3h of London (08:00-10:59 server), if price sweeps
    Asian H or L then CLOSES back inside the range → fade toward opposite extreme.

    Different from MEC-13: This happens DURING London (not pre-London).
    The sweep is from institutional flow that fails to sustain.
    """
    results = []

    for date, d in daily.items():
        if d['asian_atr'] is None or d['asian_atr'] <= 0:
            continue
        if d['dow'] >= 5:
            continue

        atr = d['asian_atr']
        asian_hi = d['asian_hi']
        asian_lo = d['asian_lo']
        asian_range = d['asian_range']
        asian_mid = (asian_hi + asian_lo) / 2

        if asian_range < 0.5 * atr:
            continue

        # Check first 3h of London (08:00-10:59 server)
        early_london = d['all_bars'][(d['all_bars']['hour'] >= 8) & (d['all_bars']['hour'] <= 10)]

        signal_found = False
        for idx in range(len(early_london)):
            bar = early_london.iloc[idx]

            sweep_hi = bar['high'] > asian_hi + 0.1 * atr  # meaningful sweep (> 0.1 ATR beyond)
            sweep_lo = bar['low'] < asian_lo - 0.1 * atr
            close_inside = bar['close'] >= asian_lo and bar['close'] <= asian_hi

            direction = 0
            if sweep_hi and not sweep_lo and close_inside:
                # Swept high then reclaimed → short (fade back down)
                direction = -1
            elif sweep_lo and not sweep_hi and close_inside:
                # Swept low then reclaimed → long (fade back up)
                direction = 1
            else:
                continue

            # Entry at NEXT bar open
            remaining = d['all_bars'].loc[d['all_bars'].index > bar.name]
            if len(remaining) < 2:
                continue

            entry_price = remaining.iloc[0]['open']
            sl_dist = FIXED_SL_ATR_MULT * atr
            # TP target: Asian mid (mean reversion target)
            if direction == 1:
                tp_target = asian_mid
                tp_dist = max(tp_target - entry_price, 0.5 * atr)
            else:
                tp_target = asian_mid
                tp_dist = max(entry_price - tp_target, 0.5 * atr)

            if direction == 1:
                sl = entry_price - sl_dist
                tp = entry_price + tp_dist
            else:
                sl = entry_price + sl_dist
                tp = entry_price - tp_dist

            # Walk max 16 bars (4h)
            exit_price = None
            exit_reason = None
            for i in range(min(16, len(remaining))):
                rbar = remaining.iloc[i]
                if direction == 1:
                    if rbar['low'] <= sl:
                        exit_price = sl; exit_reason = 'sl'; break
                    if rbar['high'] >= tp:
                        exit_price = tp; exit_reason = 'tp'; break
                else:
                    if rbar['high'] >= sl:
                        exit_price = sl; exit_reason = 'sl'; break
                    if rbar['low'] <= tp:
                        exit_price = tp; exit_reason = 'tp'; break

            if exit_price is None:
                exit_price = remaining.iloc[min(15, len(remaining)-1)]['close']
                exit_reason = 'timeout'

            pnl_raw = (exit_price - entry_price) * direction
            pnl_net = pnl_raw - (SPREAD_COST_PTS * 0.01)

            results.append({
                'date': date,
                'year': d['year'],
                'dow': d['dow'],
                'direction': direction,
                'sweep_type': 'low_sweep' if direction == 1 else 'high_sweep',
                'entry': entry_price,
                'exit': exit_price,
                'exit_reason': exit_reason,
                'pnl_raw': pnl_raw,
                'pnl_net': pnl_net,
                'atr': atr
            })
            signal_found = True
            break  # 1 signal per day

    return pd.DataFrame(results)


# ===========================================================================
# ANALYSIS HELPERS
# ===========================================================================
def analyze_results(name, df_results):
    """Print analysis summary for a mechanism"""
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")

    if df_results is None or len(df_results) == 0:
        print("  NO SIGNALS FOUND")
        return

    n = len(df_results)
    years = df_results['year'].nunique()
    trades_per_yr = n / years if years > 0 else 0

    wins = df_results[df_results['pnl_net'] > 0]
    losses = df_results[df_results['pnl_net'] <= 0]

    total_pnl = df_results['pnl_net'].sum()
    avg_pnl = df_results['pnl_net'].mean()

    win_rate = len(wins) / n * 100 if n > 0 else 0
    avg_win = wins['pnl_net'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl_net'].mean() if len(losses) > 0 else 0

    gross_profit = wins['pnl_net'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl_net'].sum()) if len(losses) > 0 else 0.001
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    # Normalize by ATR for cross-instrument comparison
    avg_pnl_atr = (df_results['pnl_net'] / df_results['atr']).mean()

    # Exit reason distribution
    exit_dist = df_results['exit_reason'].value_counts()

    print(f"  Trades: {n} ({trades_per_yr:.0f}/yr)")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  PF: {pf:.2f}")
    print(f"  Total P&L: ${total_pnl:.2f} (per lot)")
    print(f"  Avg P&L: ${avg_pnl:.2f}")
    print(f"  Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
    print(f"  Avg P&L (ATR-normalized): {avg_pnl_atr:.3f}R")
    print(f"  Direction split: Long {len(df_results[df_results['direction']==1])} | Short {len(df_results[df_results['direction']==-1])}")
    print()
    print(f"  Exit reasons:")
    for reason, count in exit_dist.items():
        print(f"    {reason}: {count} ({count/n*100:.0f}%)")

    # Yearly breakdown
    print(f"\n  Yearly Breakdown:")
    print(f"  {'Year':<6} {'Trades':<8} {'WR%':<8} {'PF':<8} {'Net$':<10} {'Avg$/trade':<12}")
    for year, yg in df_results.groupby('year'):
        yw = yg[yg['pnl_net'] > 0]
        yl = yg[yg['pnl_net'] <= 0]
        ywr = len(yw) / len(yg) * 100 if len(yg) > 0 else 0
        ygp = yw['pnl_net'].sum() if len(yw) > 0 else 0
        ygl = abs(yl['pnl_net'].sum()) if len(yl) > 0 else 0.001
        ypf = ygp / ygl if ygl > 0 else 0
        ynet = yg['pnl_net'].sum()
        yavg = yg['pnl_net'].mean()
        print(f"  {year:<6} {len(yg):<8} {ywr:<8.1f} {ypf:<8.2f} {ynet:<10.2f} {yavg:<12.2f}")

    # Day-of-week breakdown
    print(f"\n  Day-of-Week:")
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    for dow in range(5):
        dg = df_results[df_results['dow'] == dow]
        if len(dg) == 0:
            print(f"  {dow_names[dow]:<6} --")
            continue
        dw = dg[dg['pnl_net'] > 0]
        dl = dg[dg['pnl_net'] <= 0]
        dwr = len(dw) / len(dg) * 100
        dgp = dw['pnl_net'].sum() if len(dw) > 0 else 0
        dgl = abs(dl['pnl_net'].sum()) if len(dl) > 0 else 0.001
        dpf = dgp / dgl if dgl > 0 else 0
        dnet = dg['pnl_net'].sum()
        print(f"  {dow_names[dow]:<6} n={len(dg):<4} WR={dwr:.0f}%  PF={dpf:.2f}  Net=${dnet:.2f}")

    return {
        'name': name,
        'trades': n,
        'trades_yr': trades_per_yr,
        'wr': win_rate,
        'pf': pf,
        'net': total_pnl,
        'avg_pnl_atr': avg_pnl_atr
    }


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == '__main__':
    print("=" * 70)
    print("  GOLD EDGE SCANNER — 3 Untested Mechanisms")
    print("  XAUUSD+ M15 | 2019–2025")
    print("=" * 70)

    # Load data
    df = load_data()

    # Build daily session structure
    print("\n[INFO] Building daily sessions...")
    daily = build_daily_sessions(df)
    print(f"[OK] {len(daily)} trading days built")

    # Scan all 3 mechanisms
    print("\n[INFO] Scanning MEC-11: London Fix Anomaly...")
    fix_results = scan_london_fix(daily)

    print("[INFO] Scanning MEC-13: Asian Stop Hunt...")
    hunt_results = scan_asian_stop_hunt(daily)

    print("[INFO] Scanning MEC-02: Asian Sweep Fade...")
    fade_results = scan_asian_sweep_fade(daily)

    # Analyze
    summaries = []
    s1 = analyze_results("MEC-11: London Fix Anomaly (10:30 reversion)", fix_results)
    if s1: summaries.append(s1)

    s2 = analyze_results("MEC-13: Asian Stop Hunt (pre-London fade)", hunt_results)
    if s2: summaries.append(s2)

    s3 = analyze_results("MEC-02: Asian Sweep Fade (London reclaim)", fade_results)
    if s3: summaries.append(s3)

    # Summary comparison
    print(f"\n{'='*70}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Mechanism':<45} {'N':<6} {'N/yr':<7} {'WR%':<7} {'PF':<7} {'AvgR':<8}")
    for s in summaries:
        print(f"  {s['name']:<45} {s['trades']:<6} {s['trades_yr']:<7.0f} {s['wr']:<7.1f} {s['pf']:<7.2f} {s['avg_pnl_atr']:<8.3f}")

    print(f"\n  Spread cost assumed: {SPREAD_COST_PTS} points (~${SPREAD_COST_PTS*0.01:.2f}/unit)")
    print(f"  SL = {FIXED_SL_ATR_MULT}×ATR | TP = {FIXED_TP_ATR_MULT}×ATR")
    print(f"\n{'='*70}")
    print("  DONE")
    print(f"{'='*70}")
