"""
MEC-15 Deep Iteration — Overnight Mean Reversion Short
Fine-tune: entry timing, deviation threshold, hold duration,
           SL/TP asymmetry, weekly patterns, yearly stability

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

SYMBOL = "XAUUSD+"
TF = mt5.TIMEFRAME_M15
DATE_FROM = datetime(2019, 1, 1)
DATE_TO = datetime(2026, 1, 1)
SPREAD_COST = 0.30

def load_data():
    if not mt5.initialize():
        print(f"[ERR] MT5 init failed"); sys.exit(1)
    rates = mt5.copy_rates_range(SYMBOL, TF, DATE_FROM, DATE_TO)
    if rates is None or len(rates) == 0:
        print(f"[ERR] No data"); sys.exit(1)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['dow'] = df.index.dayofweek
    df['date'] = df.index.date
    df['year'] = df.index.year

    tr = pd.DataFrame()
    tr['hl'] = df['high'] - df['low']
    tr['hc'] = abs(df['high'] - df['close'].shift(1))
    tr['lc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = tr.max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean()

    # D1 data for regime
    daily_close = df.groupby('date')['close'].last()
    ema50 = daily_close.ewm(span=50, adjust=False).mean()
    ema20 = daily_close.ewm(span=20, adjust=False).mean()
    slope = ema50.diff(10) / ema50.shift(10)
    regime_map = {}
    for d, s in slope.items():
        if pd.isna(s): regime_map[d] = 'flat'
        elif s > 0.005: regime_map[d] = 'up'
        elif s < -0.005: regime_map[d] = 'down'
        else: regime_map[d] = 'flat'
    df['regime'] = df['date'].map(regime_map).fillna('flat')

    # Prev day close
    prev_close = daily_close.shift(1)
    df['prev_day_close'] = df['date'].map(prev_close.to_dict())

    # Prev day high/low
    daily_hi = df.groupby('date')['high'].max()
    daily_lo = df.groupby('date')['low'].min()
    df['prev_day_hi'] = df['date'].map(daily_hi.shift(1).to_dict())
    df['prev_day_lo'] = df['date'].map(daily_lo.shift(1).to_dict())

    print(f"[OK] {len(df)} bars, {df['date'].nunique()} days")
    mt5.shutdown()
    return df


def build_daily(df):
    daily = {}
    for date, group in df.groupby('date'):
        atr_vals = group['atr14'].dropna()
        if len(atr_vals) == 0: continue
        prev_c = group['prev_day_close'].iloc[0]
        if pd.isna(prev_c) or prev_c <= 0: continue

        daily[date] = {
            'bars': group,
            'atr': atr_vals.iloc[0],
            'regime': group['regime'].iloc[0],
            'dow': group['dow'].iloc[0],
            'year': group['year'].iloc[0],
            'prev_close': prev_c,
            'prev_hi': group['prev_day_hi'].iloc[0],
            'prev_lo': group['prev_day_lo'].iloc[0],
        }
    return daily


def simulate_trade(bars, direction, sl_dist, tp_dist, max_hold=16):
    if len(bars) == 0: return None, 'no_bars', 0
    entry = bars.iloc[0]['open']
    if direction == 1:
        sl, tp = entry - sl_dist, entry + tp_dist
    else:
        sl, tp = entry + sl_dist, entry - tp_dist
    for i in range(min(max_hold, len(bars))):
        bar = bars.iloc[i]
        if direction == 1:
            if bar['low'] <= sl: return sl, 'sl', i
            if bar['high'] >= tp: return tp, 'tp', i
        else:
            if bar['high'] >= sl: return sl, 'sl', i
            if bar['low'] <= tp: return tp, 'tp', i
    last_i = min(max_hold-1, len(bars)-1)
    return bars.iloc[last_i]['close'], 'timeout', last_i


def scan_overnight(daily, check_hour=3, deviation_mult=0.3,
                   sl_mult=1.5, tp_mult=3.0, max_hold=16,
                   direction_filter=-1, regime_filter=None,
                   skip_days=None, entry_mode='next_bar'):
    """
    Configurable overnight MR scanner.
    check_hour: which hour to check deviation (0-7)
    deviation_mult: min deviation from prev close in ATR multiples
    entry_mode: 'next_bar' or 'prev_close_target' (TP = prev close)
    skip_days: list of dow to skip (0=Mon, 4=Fri)
    """
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if skip_days and d['dow'] in skip_days:
            continue
        if regime_filter:
            if regime_filter == 'up' and d['regime'] != 'up': continue
            if regime_filter == 'down' and d['regime'] != 'down': continue
            if regime_filter == 'trending' and d['regime'] == 'flat': continue

        atr = d['atr']
        # Check at specified hour
        check_bars = d['bars'][(d['bars']['hour'] >= check_hour) & (d['bars']['hour'] <= check_hour)]
        if len(check_bars) == 0:
            continue

        current = check_bars.iloc[-1]['close']
        deviation = current - d['prev_close']

        direction = 0
        if deviation > deviation_mult * atr:
            direction = -1  # drifted up -> short
        elif deviation < -deviation_mult * atr:
            direction = 1  # drifted down -> long
        else:
            continue

        if direction_filter != 0 and direction != direction_filter:
            continue

        # Entry
        remaining = d['bars'].loc[d['bars'].index > check_bars.iloc[-1].name]
        if len(remaining) < 2:
            continue

        entry = remaining.iloc[0]['open']

        if entry_mode == 'prev_close_target':
            # TP = previous close (mean reversion target)
            if direction == -1:
                tp_d = max(entry - d['prev_close'], 0.3 * atr)
                sl_d = sl_mult * atr
            else:
                tp_d = max(d['prev_close'] - entry, 0.3 * atr)
                sl_d = sl_mult * atr
        else:
            sl_d = sl_mult * atr
            tp_d = tp_mult * atr

        exit_p, exit_r, bars_held = simulate_trade(remaining, direction, sl_d, tp_d, max_hold)
        if exit_p is None:
            continue

        pnl = (exit_p - entry) * direction - SPREAD_COST
        results.append({
            'date': date, 'year': d['year'], 'dow': d['dow'],
            'pnl': pnl, 'direction': direction, 'exit_reason': exit_r,
            'bars_held': bars_held, 'deviation_atr': abs(deviation / atr),
            'regime': d['regime']
        })

    return pd.DataFrame(results) if results else None


def full_analysis(name, df_r):
    """Comprehensive analysis of a variant"""
    if df_r is None or len(df_r) == 0:
        print(f"  {name}: NO SIGNALS")
        return None

    n = len(df_r)
    yrs = max(df_r['year'].nunique(), 1)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    pf = gp / gl
    wr = len(wins) / n * 100
    avg_w = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_l = losses['pnl'].mean() if len(losses) > 0 else 0
    net = df_r['pnl'].sum()

    # Max consecutive losses
    consec = 0
    max_consec = 0
    for _, row in df_r.iterrows():
        if row['pnl'] <= 0:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0

    # Max drawdown simulation
    equity = 0
    peak = 0
    max_dd = 0
    for _, row in df_r.iterrows():
        equity += row['pnl']
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    # Yearly
    yr_data = []
    for year, yg in df_r.groupby('year'):
        yw = yg[yg['pnl'] > 0]
        yl = yg[yg['pnl'] <= 0]
        ygp = yw['pnl'].sum() if len(yw) > 0 else 0
        ygl = abs(yl['pnl'].sum()) if len(yl) > 0 else 0.001
        yr_data.append({'year': year, 'n': len(yg), 'pf': ygp/ygl,
                       'net': yg['pnl'].sum(), 'wr': len(yw)/len(yg)*100})

    # DOW
    dow_data = []
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    for dow in range(5):
        dg = df_r[df_r['dow'] == dow]
        if len(dg) == 0:
            dow_data.append({'dow': dow_names[dow], 'n': 0, 'pf': 0, 'net': 0})
            continue
        dw = dg[dg['pnl'] > 0]
        dl = dg[dg['pnl'] <= 0]
        dgp = dw['pnl'].sum() if len(dw) > 0 else 0
        dgl = abs(dl['pnl'].sum()) if len(dl) > 0 else 0.001
        dow_data.append({'dow': dow_names[dow], 'n': len(dg), 'pf': dgp/dgl, 'net': dg['pnl'].sum()})

    # Hold time distribution
    avg_hold = df_r['bars_held'].mean() * 15 / 60  # hours

    return {
        'name': name, 'n': n, 'n_yr': n/yrs, 'wr': wr, 'pf': pf,
        'net': net, 'avg_w': avg_w, 'avg_l': avg_l,
        'max_consec': max_consec, 'max_dd': max_dd,
        'avg_hold_h': avg_hold,
        'years': yr_data, 'dows': dow_data,
        'years_pos': sum(1 for y in yr_data if y['net'] > 0),
    }


def print_analysis(a):
    if a is None: return
    print(f"\n  --- {a['name']} ---")
    print(f"  N={a['n']} ({a['n_yr']:.0f}/yr) | WR={a['wr']:.1f}% | PF={a['pf']:.2f}")
    print(f"  Net=${a['net']:.2f} | AvgWin=${a['avg_w']:.2f} AvgLoss=${a['avg_l']:.2f}")
    print(f"  MaxConsecLoss={a['max_consec']} | MaxDD=${a['max_dd']:.2f} | AvgHold={a['avg_hold_h']:.1f}h")
    print(f"  Years+: {a['years_pos']}/{len(a['years'])}")
    for y in a['years']:
        print(f"    {y['year']}: n={y['n']:<4} PF={y['pf']:.2f}  WR={y['wr']:.0f}%  Net=${y['net']:.1f}")
    print(f"  Day of Week:")
    for d in a['dows']:
        if d['n'] > 0:
            print(f"    {d['dow']}: n={d['n']:<4} PF={d['pf']:.2f}  Net=${d['net']:.1f}")


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("  MEC-15 OVERNIGHT MEAN REVERSION - DEEP ITERATION")
    print("  XAUUSD+ M15 | 2019-2025")
    print("=" * 80)

    df = load_data()
    daily = build_daily(df)
    print(f"[OK] {len(daily)} days\n")

    results = []

    # DIMENSION 1: Check hour (when to measure deviation)
    print("=" * 60)
    print("  DIM-1: Entry Timing (check hour)")
    print("=" * 60)
    for ch in [1, 2, 3, 4, 5, 6]:
        r = scan_overnight(daily, check_hour=ch, sl_mult=1.5, tp_mult=3.0, direction_filter=-1)
        a = full_analysis(f"CheckH={ch} Short SL1.5 TP3.0", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 2: Deviation threshold
    print("\n" + "=" * 60)
    print("  DIM-2: Deviation Threshold")
    print("=" * 60)
    for dev in [0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75]:
        r = scan_overnight(daily, check_hour=3, deviation_mult=dev, sl_mult=1.5, tp_mult=3.0, direction_filter=-1)
        a = full_analysis(f"Dev={dev} Short", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 3: SL/TP ratios
    print("\n" + "=" * 60)
    print("  DIM-3: SL/TP Ratios")
    print("=" * 60)
    for sl, tp in [(0.5, 0.75), (0.75, 1.0), (0.75, 1.5), (1.0, 1.5),
                   (1.0, 2.0), (1.0, 3.0), (1.5, 2.0), (1.5, 3.0),
                   (2.0, 3.0), (2.0, 4.0)]:
        r = scan_overnight(daily, check_hour=3, sl_mult=sl, tp_mult=tp, direction_filter=-1)
        a = full_analysis(f"SL={sl} TP={tp} Short", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 4: Max hold time
    print("\n" + "=" * 60)
    print("  DIM-4: Max Hold Time")
    print("=" * 60)
    for mh in [4, 8, 12, 16, 24, 32, 48]:
        r = scan_overnight(daily, check_hour=3, sl_mult=1.5, tp_mult=3.0, max_hold=mh, direction_filter=-1)
        a = full_analysis(f"MaxHold={mh}bars({mh*15/60:.0f}h) Short", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 5: Direction
    print("\n" + "=" * 60)
    print("  DIM-5: Direction Filter")
    print("=" * 60)
    for d_filter in [-1, 1, 0]:
        d_name = {-1: 'Short', 1: 'Long', 0: 'Both'}[d_filter]
        r = scan_overnight(daily, check_hour=3, sl_mult=1.5, tp_mult=3.0, direction_filter=d_filter)
        a = full_analysis(f"Dir={d_name}", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 6: Regime
    print("\n" + "=" * 60)
    print("  DIM-6: Regime Filter")
    print("=" * 60)
    for rgm in [None, 'up', 'down', 'trending']:
        r = scan_overnight(daily, check_hour=3, sl_mult=1.5, tp_mult=3.0, direction_filter=-1, regime_filter=rgm)
        a = full_analysis(f"Regime={rgm or 'all'} Short", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 7: Skip days
    print("\n" + "=" * 60)
    print("  DIM-7: Day Filters")
    print("=" * 60)
    for skip in [None, [0], [4], [0, 4], [2], [0, 2]]:
        skip_name = f"Skip={skip}" if skip else "NoSkip"
        r = scan_overnight(daily, check_hour=3, sl_mult=1.5, tp_mult=3.0, direction_filter=-1, skip_days=skip)
        a = full_analysis(f"{skip_name} Short", r)
        if a: print_analysis(a); results.append(a)

    # DIMENSION 8: Entry mode (prev close target)
    print("\n" + "=" * 60)
    print("  DIM-8: Entry Mode (TP=prev close)")
    print("=" * 60)
    for sl in [0.75, 1.0, 1.5, 2.0]:
        r = scan_overnight(daily, check_hour=3, sl_mult=sl, tp_mult=0, direction_filter=-1,
                          entry_mode='prev_close_target')
        a = full_analysis(f"PrevClose Target SL={sl} Short", r)
        if a: print_analysis(a); results.append(a)

    # COMBINED BEST — try combining best dimensions
    print("\n" + "=" * 60)
    print("  COMBINED: Best Dimensions")
    print("=" * 60)

    # Best combo candidates based on above sweeps
    combos = [
        {'check_hour': 3, 'deviation_mult': 0.30, 'sl_mult': 1.5, 'tp_mult': 3.0, 'max_hold': 16, 'direction_filter': -1, 'regime_filter': 'up', 'skip_days': None},
        {'check_hour': 2, 'deviation_mult': 0.25, 'sl_mult': 1.5, 'tp_mult': 3.0, 'max_hold': 16, 'direction_filter': -1, 'regime_filter': 'up', 'skip_days': None},
        {'check_hour': 3, 'deviation_mult': 0.20, 'sl_mult': 1.0, 'tp_mult': 3.0, 'max_hold': 24, 'direction_filter': -1, 'regime_filter': None, 'skip_days': [0]},
        {'check_hour': 4, 'deviation_mult': 0.30, 'sl_mult': 1.5, 'tp_mult': 3.0, 'max_hold': 12, 'direction_filter': -1, 'regime_filter': 'trending', 'skip_days': [0, 4]},
        {'check_hour': 3, 'deviation_mult': 0.30, 'sl_mult': 2.0, 'tp_mult': 4.0, 'max_hold': 32, 'direction_filter': -1, 'regime_filter': None, 'skip_days': None},
    ]

    for i, combo in enumerate(combos):
        r = scan_overnight(daily, **combo)
        a = full_analysis(f"Combo-{i+1}: {combo}", r)
        if a: print_analysis(a); results.append(a)

    # FINAL SUMMARY
    print("\n" + "=" * 80)
    print("  FINAL RANKINGS (top 15 by PF, min 50 trades)")
    print("=" * 80)
    valid = [r for r in results if r['n'] >= 50]
    valid.sort(key=lambda x: x['pf'], reverse=True)
    print(f"{'Name':<55} {'N':<5} {'N/yr':<5} {'WR%':<5} {'PF':<6} {'Net$':<8} {'DD$':<7} {'Yr+':<5} {'ConsL':<5}")
    for r in valid[:15]:
        print(f"{r['name'][:55]:<55} {r['n']:<5} {r['n_yr']:<5.0f} {r['wr']:<5.1f} {r['pf']:<6.2f} {r['net']:<8.1f} {r['max_dd']:<7.1f} {r['years_pos']}/{len(r['years'])} {r['max_consec']:<5}")

    # WALK-FORWARD QUICK CHECK — split data in half
    print("\n" + "=" * 80)
    print("  WALK-FORWARD QUICK CHECK (2019-2022 IS vs 2023-2025 OOS)")
    print("=" * 80)

    # Use best config from first round
    r_full = scan_overnight(daily, check_hour=3, deviation_mult=0.30,
                            sl_mult=1.5, tp_mult=3.0, max_hold=16,
                            direction_filter=-1, regime_filter=None)
    if r_full is not None and len(r_full) > 0:
        is_data = r_full[r_full['year'] <= 2022]
        oos_data = r_full[r_full['year'] >= 2023]

        a_is = full_analysis("IS 2019-2022", is_data)
        a_oos = full_analysis("OOS 2023-2025", oos_data)

        if a_is and a_oos:
            print_analysis(a_is)
            print_analysis(a_oos)
            print(f"\n  IS PF: {a_is['pf']:.2f} | OOS PF: {a_oos['pf']:.2f}")
            if a_oos['pf'] > 1.0:
                print(f"  OOS PROFITABLE -> edge likely REAL")
            else:
                print(f"  OOS UNPROFITABLE -> edge may be SPURIOUS")

    print(f"\n{'='*80}")
    print(f"  DONE - {len(results)} variants tested")
    print(f"{'='*80}")
