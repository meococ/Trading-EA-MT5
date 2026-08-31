"""
EURJPY + EURUSD Gap Fill — Deep Iteration
The strongest edge found in grand scan:
  EURJPY+ Gap Fill: PF=1.38, 97/yr, IS=1.56, OOS=1.28, 6/7yr
  EURUSD+ Gap Fill: PF=1.25, 77/yr, IS=1.13, OOS=1.39, 4/7yr

Fine-tune: gap threshold, SL/TP, max hold, direction, day filter
Also test: GBPJPY+, GBPUSD+, USDJPY+ for portfolio potential

Author: Max (AlphaFactory research lane)
Date: 2026-03-21
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATE_FROM = datetime(2019, 1, 1)
DATE_TO = datetime(2026, 1, 1)
TF = mt5.TIMEFRAME_M15

PAIRS = {
    'EURJPY+': 0.018,
    'EURUSD+': 0.00012,
    'GBPJPY+': 0.025,
    'GBPUSD+': 0.00018,
    'USDJPY+': 0.015,
}


def load_and_prepare(symbol):
    if not mt5.initialize(): return None
    info = mt5.symbol_info(symbol)
    if info is None: mt5.shutdown(); return None
    if not info.visible: mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, TF, DATE_FROM, DATE_TO)
    mt5.shutdown()
    if rates is None or len(rates) < 1000: return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['hour'] = df.index.hour
    df['dow'] = df.index.dayofweek
    df['date'] = df.index.date
    df['year'] = df.index.year
    tr = pd.DataFrame()
    tr['hl'] = df['high'] - df['low']
    tr['hc'] = abs(df['high'] - df['close'].shift(1))
    tr['lc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = tr.max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean()
    daily_close = df.groupby('date')['close'].last()
    prev_close = daily_close.shift(1)
    df['prev_day_close'] = df['date'].map(prev_close.to_dict())
    return df


def build_daily(df):
    daily = {}
    for date, group in df.groupby('date'):
        atr_vals = group['atr14'].dropna()
        if len(atr_vals) == 0: continue
        prev_c = group['prev_day_close'].iloc[0]
        if pd.isna(prev_c) or prev_c <= 0: continue
        daily[date] = {
            'bars': group, 'atr': atr_vals.iloc[0],
            'dow': group['dow'].iloc[0], 'year': group['year'].iloc[0],
            'prev_close': prev_c,
        }
    return daily


def simulate_trade(bars, direction, sl_dist, tp_dist, max_hold=16):
    if len(bars) == 0: return None, 'no_bars', 0
    entry = bars.iloc[0]['open']
    sl = entry - sl_dist if direction == 1 else entry + sl_dist
    tp = entry + tp_dist if direction == 1 else entry - tp_dist
    for i in range(min(max_hold, len(bars))):
        bar = bars.iloc[i]
        if direction == 1:
            if bar['low'] <= sl: return sl, 'sl', i
            if bar['high'] >= tp: return tp, 'tp', i
        else:
            if bar['high'] >= sl: return sl, 'sl', i
            if bar['low'] <= tp: return tp, 'tp', i
    return bars.iloc[min(max_hold-1, len(bars)-1)]['close'], 'timeout', min(max_hold-1, len(bars)-1)


def scan_gap_fill(daily, spread, min_gap=0.3, sl_mult=1.5, tp_mode='gap',
                  tp_mult=0.8, max_hold=8, direction_filter=0, skip_days=None,
                  entry_bar_idx=0, check_hour=None):
    """
    Gap fill scanner with many tunable parameters.
    tp_mode: 'gap' = TP is fraction of gap size; 'atr' = TP is multiple of ATR
    entry_bar_idx: 0 = enter on first bar, 1 = enter on second bar (confirmation)
    check_hour: if set, only enter at this hour
    """
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        if skip_days and d['dow'] in skip_days: continue
        atr = d['atr']

        first_bar = d['bars'].iloc[0]
        gap = first_bar['open'] - d['prev_close']
        if abs(gap) < min_gap * atr: continue

        direction = -1 if gap > 0 else 1  # Fade the gap
        if direction_filter != 0 and direction != direction_filter: continue

        # Entry
        if check_hour is not None:
            entry_bars = d['bars'][d['bars']['hour'] == check_hour]
            if len(entry_bars) == 0: continue
            remaining = d['bars'].loc[d['bars'].index >= entry_bars.iloc[0].name]
        else:
            remaining = d['bars'].iloc[1 + entry_bar_idx:]

        if len(remaining) < 2: continue

        sl_dist = sl_mult * atr
        if tp_mode == 'gap':
            tp_dist = abs(gap) * tp_mult
        else:
            tp_dist = tp_mult * atr

        # Minimum TP = 0.2 ATR (to cover spread)
        tp_dist = max(tp_dist, 0.2 * atr)

        exit_p, exit_r, bars_held = simulate_trade(remaining, direction, sl_dist, tp_dist, max_hold)
        if exit_p is None: continue
        pnl = (exit_p - remaining.iloc[0]['open']) * direction - spread
        results.append({
            'date': date, 'year': d['year'], 'dow': d['dow'],
            'pnl': pnl, 'direction': direction, 'exit_reason': exit_r,
            'bars_held': bars_held, 'gap_atr': abs(gap)/atr
        })
    return pd.DataFrame(results) if results else None


def full_analysis(name, df_r):
    if df_r is None or len(df_r) == 0: return None
    n = len(df_r)
    yrs = max(df_r['year'].nunique(), 1)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    pf = gp / gl
    wr = len(wins) / n * 100
    net = df_r['pnl'].sum()
    avg_w = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_l = losses['pnl'].mean() if len(losses) > 0 else 0

    # Max consec loss
    consec = 0; max_consec = 0
    for _, row in df_r.iterrows():
        if row['pnl'] <= 0: consec += 1; max_consec = max(max_consec, consec)
        else: consec = 0

    # Max DD
    equity = 0; peak = 0; max_dd = 0
    for _, row in df_r.iterrows():
        equity += row['pnl']
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    # Yearly
    yr_data = []
    for year, yg in df_r.groupby('year'):
        yw = yg[yg['pnl'] > 0]; yl = yg[yg['pnl'] <= 0]
        ygp = yw['pnl'].sum() if len(yw) > 0 else 0
        ygl = abs(yl['pnl'].sum()) if len(yl) > 0 else 0.001
        yr_data.append({'year': year, 'n': len(yg), 'pf': ygp/ygl, 'net': yg['pnl'].sum()})

    # IS/OOS
    is_d = df_r[df_r['year'] <= 2022]; oos_d = df_r[df_r['year'] >= 2023]
    is_pf = (is_d[is_d['pnl']>0]['pnl'].sum() / max(abs(is_d[is_d['pnl']<=0]['pnl'].sum()), 0.001)) if len(is_d) > 5 else 0
    oos_pf = (oos_d[oos_d['pnl']>0]['pnl'].sum() / max(abs(oos_d[oos_d['pnl']<=0]['pnl'].sum()), 0.001)) if len(oos_d) > 5 else 0

    # DOW
    dow_data = {}
    for dow in range(5):
        dg = df_r[df_r['dow'] == dow]
        if len(dg) > 0:
            dw = dg[dg['pnl']>0]; dl = dg[dg['pnl']<=0]
            dpf = dw['pnl'].sum() / max(abs(dl['pnl'].sum()), 0.001)
            dow_data[dow] = {'n': len(dg), 'pf': dpf, 'net': dg['pnl'].sum()}

    yrs_pos = sum(1 for y in yr_data if y['net'] > 0)

    # Average hold time
    avg_hold_h = df_r['bars_held'].mean() * 15 / 60 if 'bars_held' in df_r.columns else 0

    return {
        'name': name, 'n': n, 'n_yr': n/yrs, 'wr': wr, 'pf': pf, 'net': net,
        'avg_w': avg_w, 'avg_l': avg_l, 'max_consec': max_consec, 'max_dd': max_dd,
        'avg_hold_h': avg_hold_h,
        'is_pf': is_pf, 'oos_pf': oos_pf,
        'yrs_pos': yrs_pos, 'yrs_tot': yrs,
        'years': yr_data, 'dows': dow_data
    }


def print_analysis(a):
    if a is None: return
    print(f"\n  --- {a['name']} ---")
    print(f"  N={a['n']} ({a['n_yr']:.0f}/yr) | WR={a['wr']:.1f}% | PF={a['pf']:.2f} | Net={a['net']:.4f}")
    print(f"  IS={a['is_pf']:.2f} OOS={a['oos_pf']:.2f} | AvgHold={a['avg_hold_h']:.1f}h | ConsecL={a['max_consec']} | DD={a['max_dd']:.4f}")
    print(f"  Yr+: {a['yrs_pos']}/{a['yrs_tot']}")
    for y in a['years']:
        print(f"    {y['year']}: n={y['n']:<4} PF={y['pf']:.2f}  Net={y['net']:.4f}")
    dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    for dow, dd in sorted(a['dows'].items()):
        print(f"    {dow_names[dow]}: n={dd['n']:<4} PF={dd['pf']:.2f}")


if __name__ == '__main__':
    print("=" * 80)
    print("  GAP FILL DEEP ITERATION — EURJPY + EURUSD + PORTFOLIO")
    print("=" * 80)

    all_summaries = []

    for symbol, spread in PAIRS.items():
        print(f"\n{'='*60}")
        print(f"  {symbol}")
        print(f"{'='*60}")

        df = load_and_prepare(symbol)
        if df is None: print("  [SKIP]"); continue
        print(f"  [OK] {len(df)} bars")
        daily = build_daily(df)

        # DIM 1: Gap threshold
        print("\n  --- DIM-1: Gap Threshold ---")
        for gap in [0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.0]:
            r = scan_gap_fill(daily, spread, min_gap=gap)
            a = full_analysis(f"{symbol} Gap>={gap}ATR", r)
            if a and a['n'] >= 30:
                print(f"  Gap>={gap}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f} IS={a['is_pf']:.2f} OOS={a['oos_pf']:.2f} Yr+={a['yrs_pos']}/{a['yrs_tot']}")
                all_summaries.append(a)

        # DIM 2: SL multiplier
        print("\n  --- DIM-2: SL Multiplier ---")
        for sl in [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
            r = scan_gap_fill(daily, spread, sl_mult=sl)
            a = full_analysis(f"{symbol} SL={sl}ATR", r)
            if a and a['n'] >= 30:
                print(f"  SL={sl}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f} IS={a['is_pf']:.2f} OOS={a['oos_pf']:.2f}")
                all_summaries.append(a)

        # DIM 3: TP mode
        print("\n  --- DIM-3: TP Mode ---")
        for tp_m, tp_v in [('gap', 0.5), ('gap', 0.8), ('gap', 1.0), ('gap', 1.2),
                            ('atr', 0.5), ('atr', 1.0), ('atr', 1.5), ('atr', 2.0)]:
            r = scan_gap_fill(daily, spread, tp_mode=tp_m, tp_mult=tp_v)
            a = full_analysis(f"{symbol} TP={tp_m}{tp_v}", r)
            if a and a['n'] >= 30:
                print(f"  TP={tp_m}{tp_v}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f} WR={a['wr']:.0f}%")
                all_summaries.append(a)

        # DIM 4: Max hold
        print("\n  --- DIM-4: Max Hold ---")
        for mh in [4, 6, 8, 12, 16, 24]:
            r = scan_gap_fill(daily, spread, max_hold=mh)
            a = full_analysis(f"{symbol} MaxH={mh}({mh*15/60:.1f}h)", r)
            if a and a['n'] >= 30:
                print(f"  MaxH={mh}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f} AvgH={a['avg_hold_h']:.1f}h")
                all_summaries.append(a)

        # DIM 5: Direction
        print("\n  --- DIM-5: Direction ---")
        for d, dn in [(-1, 'Short'), (1, 'Long'), (0, 'Both')]:
            r = scan_gap_fill(daily, spread, direction_filter=d)
            a = full_analysis(f"{symbol} {dn}", r)
            if a and a['n'] >= 30:
                print(f"  {dn}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f} Yr+={a['yrs_pos']}/{a['yrs_tot']}")
                all_summaries.append(a)

        # DIM 6: Skip days
        print("\n  --- DIM-6: Day Filters ---")
        for skip, sn in [(None, 'NoSkip'), ([0], 'SkipMon'), ([4], 'SkipFri'),
                          ([0,4], 'SkipMonFri')]:
            r = scan_gap_fill(daily, spread, skip_days=skip)
            a = full_analysis(f"{symbol} {sn}", r)
            if a and a['n'] >= 30:
                print(f"  {sn}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f}")
                all_summaries.append(a)

        # DIM 7: Entry with confirmation bar
        print("\n  --- DIM-7: Entry Timing ---")
        for eidx in [0, 1]:
            r = scan_gap_fill(daily, spread, entry_bar_idx=eidx)
            a = full_analysis(f"{symbol} EntryBar={eidx}", r)
            if a and a['n'] >= 30:
                print(f"  EntryBar={eidx}: N={a['n']} ({a['n_yr']:.0f}/yr) PF={a['pf']:.2f}")
                all_summaries.append(a)

        # Print best combo for this pair
        best_for_pair = [s for s in all_summaries if s['name'].startswith(symbol)]
        if best_for_pair:
            best_for_pair.sort(key=lambda x: x['pf'], reverse=True)
            print(f"\n  BEST for {symbol}: {best_for_pair[0]['name']}")
            print_analysis(best_for_pair[0])

    # FINAL SUMMARY
    all_summaries.sort(key=lambda x: x['pf'], reverse=True)
    print(f"\n{'='*80}")
    print(f"  FINAL RANKINGS — Top 20 Gap Fill Variants")
    print(f"{'='*80}")
    print(f"{'Name':<50} {'N':<5} {'N/yr':<5} {'WR%':<5} {'PF':<6} {'IS':<6} {'OOS':<6} {'Yr+':<5} {'Hold':<5}")
    for s in all_summaries[:20]:
        print(f"{s['name'][:50]:<50} {s['n']:<5} {s['n_yr']:<5.0f} {s['wr']:<5.1f} {s['pf']:<6.2f} {s['is_pf']:<6.2f} {s['oos_pf']:<6.2f} {s['yrs_pos']}/{s['yrs_tot']} {s['avg_hold_h']:<5.1f}")

    # Walk-forward detail for top candidates
    print(f"\n{'='*80}")
    print(f"  TOP 3 DETAILED")
    print(f"{'='*80}")
    for s in all_summaries[:3]:
        print_analysis(s)

    print(f"\n  Total variants tested: {len(all_summaries)}")
    prof = len([s for s in all_summaries if s['pf'] > 1.0])
    strong = len([s for s in all_summaries if s['pf'] > 1.3])
    print(f"  Profitable: {prof}/{len(all_summaries)}")
    print(f"  Strong (PF>1.3): {strong}")
    print(f"{'='*80}")
