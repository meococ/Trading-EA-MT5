"""
DEEP OPTIMIZATION — Gap Fill Long on EURUSD+, EURJPY+, GBPJPY+

Fine-grid search across ALL meaningful dimensions:
  1. Gap threshold: 0.2 to 1.5 ATR (step 0.05)
  2. SL: 0.5 to 5.0 ATR (step 0.25)
  3. TP mode: gap fraction (0.4 to 1.5) vs ATR multiple (0.5 to 4.0)
  4. Max hold: 2 to 32 bars (step 2) = 30min to 8h
  5. Entry timing: bar 0 (immediate) vs bar 1 (confirmation) vs specific hours
  6. Day filter: individual days + combos
  7. Gap direction thresholds (asymmetric)
  8. COMBO optimization: best SL × best TP × best Gap × best MaxHold

Direction: LONG ONLY (Short is confirmed negative on all 3 pairs)

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
    'EURUSD+': 0.00012,
    'EURJPY+': 0.018,
    'GBPJPY+': 0.025,
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


def simulate_trade(bars, sl_dist, tp_dist, max_hold=16):
    """LONG only trade"""
    if len(bars) == 0: return None, 'no_bars', 0
    entry = bars.iloc[0]['open']
    sl = entry - sl_dist
    tp = entry + tp_dist
    for i in range(min(max_hold, len(bars))):
        bar = bars.iloc[i]
        if bar['low'] <= sl: return sl, 'sl', i
        if bar['high'] >= tp: return tp, 'tp', i
    return bars.iloc[min(max_hold-1, len(bars)-1)]['close'], 'timeout', min(max_hold-1, len(bars)-1)


def run_config(daily, spread, gap_min=0.3, sl_mult=1.5, tp_mode='gap',
               tp_val=0.8, max_hold=8, skip_days=None, entry_hour=None):
    """Run a single config on all daily data. Long only gap-down fade."""
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        if skip_days and d['dow'] in skip_days: continue
        atr = d['atr']

        first_bar = d['bars'].iloc[0]
        gap = first_bar['open'] - d['prev_close']
        # LONG only: gap must be DOWN (negative gap)
        if gap >= 0: continue
        if abs(gap) < gap_min * atr: continue

        # Entry
        if entry_hour is not None:
            entry_bars = d['bars'][d['bars']['hour'] == entry_hour]
            if len(entry_bars) == 0: continue
            remaining = d['bars'].loc[d['bars'].index >= entry_bars.iloc[0].name]
        else:
            remaining = d['bars'].iloc[1:]

        if len(remaining) < 2: continue

        sl_dist = sl_mult * atr
        if tp_mode == 'gap':
            tp_dist = abs(gap) * tp_val
        else:
            tp_dist = tp_val * atr
        tp_dist = max(tp_dist, 0.15 * atr)

        exit_p, exit_r, bars_held = simulate_trade(remaining, sl_dist, tp_dist, max_hold)
        if exit_p is None: continue
        pnl = (exit_p - remaining.iloc[0]['open']) - spread
        results.append({
            'year': d['year'], 'dow': d['dow'], 'pnl': pnl,
            'exit_reason': exit_r, 'bars_held': bars_held
        })
    return pd.DataFrame(results) if results else None


def quick_score(df_r):
    """Fast scoring: returns (PF, N, N/yr, WR, IS_PF, OOS_PF, Yr+)"""
    if df_r is None or len(df_r) < 20: return None
    n = len(df_r)
    yrs = max(df_r['year'].nunique(), 1)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    pf = gp / gl
    wr = len(wins) / n * 100

    is_d = df_r[df_r['year'] <= 2022]; oos_d = df_r[df_r['year'] >= 2023]
    is_pf = (is_d[is_d['pnl']>0]['pnl'].sum() / max(abs(is_d[is_d['pnl']<=0]['pnl'].sum()), 0.001)) if len(is_d) > 5 else 0
    oos_pf = (oos_d[oos_d['pnl']>0]['pnl'].sum() / max(abs(oos_d[oos_d['pnl']<=0]['pnl'].sum()), 0.001)) if len(oos_d) > 5 else 0

    yrs_pos = sum(1 for _, yg in df_r.groupby('year') if yg['pnl'].sum() > 0)

    # Max consec loss
    consec = 0; max_consec = 0
    for _, row in df_r.iterrows():
        if row['pnl'] <= 0: consec += 1; max_consec = max(max_consec, consec)
        else: consec = 0

    avg_hold_h = df_r['bars_held'].mean() * 15 / 60

    # Exit reason distribution
    tp_pct = (df_r['exit_reason'] == 'tp').sum() / n * 100
    sl_pct = (df_r['exit_reason'] == 'sl').sum() / n * 100
    to_pct = (df_r['exit_reason'] == 'timeout').sum() / n * 100

    return {
        'pf': pf, 'n': n, 'n_yr': n/yrs, 'wr': wr,
        'is_pf': is_pf, 'oos_pf': oos_pf,
        'yrs_pos': yrs_pos, 'yrs_tot': yrs,
        'max_consec': max_consec, 'avg_hold_h': avg_hold_h,
        'tp_pct': tp_pct, 'sl_pct': sl_pct, 'to_pct': to_pct,
        'net': df_r['pnl'].sum()
    }


if __name__ == '__main__':
    print("=" * 80)
    print("  DEEP OPTIMIZATION — Gap Fill LONG on 3 JPY/EUR pairs")
    print("=" * 80)

    for symbol, spread in PAIRS.items():
        print(f"\n{'='*70}")
        print(f"  {symbol} — DEEP OPTIMIZATION")
        print(f"{'='*70}")

        df = load_and_prepare(symbol)
        if df is None: print("  [SKIP]"); continue
        daily = build_daily(df)
        print(f"  {len(df)} bars, {len(daily)} days")

        best_configs = []

        # =====================================================================
        # PHASE 1: Individual dimension sweeps (find boundaries)
        # =====================================================================

        # 1A: Gap threshold fine sweep
        print(f"\n  [1A] Gap Threshold:")
        for gap in np.arange(0.15, 1.55, 0.05):
            gap = round(gap, 2)
            r = run_config(daily, spread, gap_min=gap)
            s = quick_score(r)
            if s:
                print(f"    Gap>={gap:.2f}: N={s['n']:<5} PF={s['pf']:.2f} IS={s['is_pf']:.2f} OOS={s['oos_pf']:.2f} Yr+={s['yrs_pos']}/{s['yrs_tot']}")

        # 1B: SL fine sweep
        print(f"\n  [1B] SL Multiplier:")
        for sl in np.arange(0.5, 5.25, 0.25):
            sl = round(sl, 2)
            r = run_config(daily, spread, sl_mult=sl)
            s = quick_score(r)
            if s:
                print(f"    SL={sl:.2f}: N={s['n']:<5} PF={s['pf']:.2f} WR={s['wr']:.0f}% TP={s['tp_pct']:.0f}% SL={s['sl_pct']:.0f}% TO={s['to_pct']:.0f}%")

        # 1C: TP fine sweep (gap mode)
        print(f"\n  [1C] TP Gap Fraction:")
        for tp in np.arange(0.3, 1.65, 0.05):
            tp = round(tp, 2)
            r = run_config(daily, spread, tp_mode='gap', tp_val=tp)
            s = quick_score(r)
            if s:
                print(f"    TP=gap×{tp:.2f}: N={s['n']:<5} PF={s['pf']:.2f} WR={s['wr']:.0f}% TP={s['tp_pct']:.0f}%")

        # 1D: TP fine sweep (ATR mode)
        print(f"\n  [1D] TP ATR Multiple:")
        for tp in np.arange(0.5, 4.25, 0.25):
            tp = round(tp, 2)
            r = run_config(daily, spread, tp_mode='atr', tp_val=tp)
            s = quick_score(r)
            if s:
                print(f"    TP=ATR×{tp:.2f}: N={s['n']:<5} PF={s['pf']:.2f} WR={s['wr']:.0f}%")

        # 1E: Max hold fine sweep
        print(f"\n  [1E] Max Hold (bars):")
        for mh in range(2, 34, 2):
            r = run_config(daily, spread, max_hold=mh)
            s = quick_score(r)
            if s:
                print(f"    MaxH={mh}({mh*15/60:.1f}h): PF={s['pf']:.2f} AvgH={s['avg_hold_h']:.1f}h TO={s['to_pct']:.0f}%")

        # 1F: Entry hour
        print(f"\n  [1F] Entry Hour:")
        for h in range(0, 10):
            r = run_config(daily, spread, entry_hour=h)
            s = quick_score(r)
            if s and s['n'] >= 20:
                print(f"    EntryH={h}: N={s['n']:<5} PF={s['pf']:.2f} Yr+={s['yrs_pos']}/{s['yrs_tot']}")

        # 1G: Day filters (single day exclusions)
        print(f"\n  [1G] Day Exclusions:")
        dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        for skip in [None, [0], [1], [2], [3], [4], [3,4], [0,4], [1,3]]:
            label = 'None' if skip is None else '+'.join(dow_names[d] for d in skip)
            r = run_config(daily, spread, skip_days=skip)
            s = quick_score(r)
            if s:
                print(f"    Skip={label}: N={s['n']:<5} PF={s['pf']:.2f}")

        # =====================================================================
        # PHASE 2: COMBO OPTIMIZATION (top 50 combos)
        # =====================================================================
        print(f"\n  [PHASE 2] COMBO GRID SEARCH")

        # Key parameter sets based on individual sweeps
        gap_range = [0.25, 0.30, 0.35, 0.40, 0.50, 0.75]
        sl_range = [1.5, 2.0, 2.5, 3.0, 4.0]
        tp_configs = [('gap', 0.8), ('gap', 1.0), ('gap', 1.2), ('atr', 2.0), ('atr', 3.0)]
        hold_range = [4, 6, 8, 10, 12]
        skip_configs = [None, [3,4], [4]]

        combo_results = []
        total = len(gap_range) * len(sl_range) * len(tp_configs) * len(hold_range) * len(skip_configs)
        print(f"  Searching {total} combos...")

        count = 0
        for gap in gap_range:
            for sl in sl_range:
                for tp_m, tp_v in tp_configs:
                    for mh in hold_range:
                        for skip in skip_configs:
                            count += 1
                            r = run_config(daily, spread, gap_min=gap, sl_mult=sl,
                                          tp_mode=tp_m, tp_val=tp_v, max_hold=mh,
                                          skip_days=skip)
                            s = quick_score(r)
                            if s and s['pf'] > 1.0:
                                label_skip = 'None' if skip is None else str(skip)
                                combo_results.append({
                                    'gap': gap, 'sl': sl, 'tp_m': tp_m, 'tp_v': tp_v,
                                    'mh': mh, 'skip': label_skip, **s
                                })

        combo_results.sort(key=lambda x: x['pf'], reverse=True)

        print(f"\n  TOP 15 COMBOS for {symbol}:")
        print(f"  {'Gap':<5} {'SL':<5} {'TP':<10} {'MH':<4} {'Skip':<8} {'PF':<6} {'IS':<6} {'OOS':<6} {'N':<5} {'N/yr':<5} {'WR':<5} {'Yr+':<5} {'ConsL':<5} {'Hold':<5}")
        for c in combo_results[:15]:
            tp_str = f"{c['tp_m']}{c['tp_v']}"
            print(f"  {c['gap']:<5} {c['sl']:<5} {tp_str:<10} {c['mh']:<4} {c['skip']:<8} {c['pf']:<6.2f} {c['is_pf']:<6.2f} {c['oos_pf']:<6.2f} {c['n']:<5} {c['n_yr']:<5.0f} {c['wr']:<5.1f} {c['yrs_pos']}/{c['yrs_tot']} {c['max_consec']:<5} {c['avg_hold_h']:<5.1f}")

        # Also show combos with best balance (PF > 1.3 AND N/yr > 50 AND Yr+ >= 6)
        balanced = [c for c in combo_results if c['pf'] > 1.3 and c['n_yr'] > 50 and c['yrs_pos'] >= 6]
        balanced.sort(key=lambda x: x['pf'], reverse=True)
        print(f"\n  BALANCED COMBOS (PF>1.3 + N/yr>50 + Yr+>=6):")
        for c in balanced[:10]:
            tp_str = f"{c['tp_m']}{c['tp_v']}"
            print(f"  {c['gap']:<5} {c['sl']:<5} {tp_str:<10} {c['mh']:<4} {c['skip']:<8} {c['pf']:<6.2f} {c['is_pf']:<6.2f} {c['oos_pf']:<6.2f} {c['n']:<5} {c['n_yr']:<5.0f} {c['wr']:<5.1f} {c['yrs_pos']}/{c['yrs_tot']} {c['max_consec']:<5} {c['avg_hold_h']:<5.1f}")

        # Report summary
        prof_combos = len([c for c in combo_results if c['pf'] > 1.0])
        strong_combos = len([c for c in combo_results if c['pf'] > 1.5])
        print(f"\n  Summary: {len(combo_results)}/{total} profitable | {strong_combos} strong (PF>1.5) | {len(balanced)} balanced")

    print(f"\n{'='*80}")
    print("  OPTIMIZATION COMPLETE")
    print(f"{'='*80}")
