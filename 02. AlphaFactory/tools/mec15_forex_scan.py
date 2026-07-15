"""
MEC-15 Forex Pairs Scan — Overnight Mean Reversion on forex pairs
Uses the correct symbol suffix (+)

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

SYMBOLS = ['EURUSD+', 'USDJPY+', 'GBPUSD+', 'GBPJPY+', 'EURJPY+', 'USDCHF+']
SPREAD_COSTS = {
    'EURUSD+': 0.00012,
    'USDJPY+': 0.015,
    'GBPUSD+': 0.00018,
    'GBPJPY+': 0.025,
    'EURJPY+': 0.018,
    'USDCHF+': 0.00015,
    'XAUUSD+': 0.30,
}
TF = mt5.TIMEFRAME_M15
DATE_FROM = datetime(2019, 1, 1)
DATE_TO = datetime(2026, 1, 1)


def load_and_prepare(symbol):
    if not mt5.initialize():
        return None
    info = mt5.symbol_info(symbol)
    if info is None:
        mt5.shutdown(); return None
    if not info.visible:
        mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, TF, DATE_FROM, DATE_TO)
    mt5.shutdown()
    if rates is None or len(rates) < 1000:
        return None

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
    ema50 = daily_close.ewm(span=50, adjust=False).mean()
    slope = ema50.diff(10) / ema50.shift(10)
    regime_map = {d: ('up' if s > 0.003 else ('down' if s < -0.003 else 'flat'))
                  for d, s in slope.items() if not pd.isna(s)}
    df['regime'] = df['date'].map(regime_map).fillna('flat')

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
            'regime': group['regime'].iloc[0],
            'dow': group['dow'].iloc[0], 'year': group['year'].iloc[0],
            'prev_close': prev_c,
        }
    return daily


def simulate_trade(bars, direction, sl_dist, tp_dist, max_hold=16):
    if len(bars) == 0: return None, 'no_bars'
    entry = bars.iloc[0]['open']
    sl = entry - sl_dist if direction == 1 else entry + sl_dist
    tp = entry + tp_dist if direction == 1 else entry - tp_dist
    for i in range(min(max_hold, len(bars))):
        bar = bars.iloc[i]
        if direction == 1:
            if bar['low'] <= sl: return sl, 'sl'
            if bar['high'] >= tp: return tp, 'tp'
        else:
            if bar['high'] >= sl: return sl, 'sl'
            if bar['low'] <= tp: return tp, 'tp'
    return bars.iloc[min(max_hold-1, len(bars)-1)]['close'], 'timeout'


def scan_overnight(daily, spread, check_hour=3, deviation_mult=0.3,
                   sl_mult=1.5, tp_mult=3.0, max_hold=16, direction_filter=0):
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        atr = d['atr']
        check_bars = d['bars'][d['bars']['hour'] == check_hour]
        if len(check_bars) == 0: continue
        current = check_bars.iloc[-1]['close']
        dev = current - d['prev_close']
        direction = -1 if dev > deviation_mult * atr else (1 if dev < -deviation_mult * atr else 0)
        if direction == 0: continue
        if direction_filter != 0 and direction != direction_filter: continue
        remaining = d['bars'].loc[d['bars'].index > check_bars.iloc[-1].name]
        if len(remaining) < 2: continue
        entry = remaining.iloc[0]['open']
        exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, max_hold)
        if exit_p is None: continue
        pnl = (exit_p - entry) * direction - spread
        results.append({'date': date, 'year': d['year'], 'pnl': pnl, 'direction': direction})
    return pd.DataFrame(results) if results else None


def analyze(name, df_r):
    if df_r is None or len(df_r) == 0:
        return None
    n = len(df_r)
    yrs = max(df_r['year'].nunique(), 1)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001

    is_d = df_r[df_r['year'] <= 2022]
    oos_d = df_r[df_r['year'] >= 2023]
    is_pf = (is_d[is_d['pnl']>0]['pnl'].sum() / abs(is_d[is_d['pnl']<=0]['pnl'].sum())) if len(is_d) > 10 else 0
    oos_pf = (oos_d[oos_d['pnl']>0]['pnl'].sum() / abs(oos_d[oos_d['pnl']<=0]['pnl'].sum())) if len(oos_d) > 10 else 0

    yrs_pos = sum(1 for _, yg in df_r.groupby('year') if yg['pnl'].sum() > 0)

    return {
        'name': name, 'n': n, 'n_yr': n/yrs, 'wr': len(wins)/n*100,
        'pf': gp/gl, 'net': df_r['pnl'].sum(),
        'is_pf': is_pf, 'oos_pf': oos_pf,
        'yrs_pos': yrs_pos, 'yrs_tot': yrs
    }


if __name__ == '__main__':
    print("=" * 80)
    print("  MEC-15 FOREX PAIRS SCAN")
    print("  Overnight Mean Reversion on 6 forex pairs")
    print("=" * 80)

    all_results = []

    for symbol in SYMBOLS:
        print(f"\n{'='*60}")
        print(f"  {symbol}")
        print(f"{'='*60}")

        df = load_and_prepare(symbol)
        if df is None:
            print(f"  [SKIP] No data for {symbol}")
            continue

        print(f"  [OK] {len(df)} bars, {df['date'].nunique()} days")
        daily = build_daily(df)
        spread = SPREAD_COSTS.get(symbol, 0.0002)

        configs = [
            # Core configs
            (3, 0.3, 1.5, 3.0, 16, 0, 'Both'),
            (3, 0.3, 2.0, 4.0, 32, 0, 'Both'),
            (3, 0.3, 1.5, 3.0, 16, -1, 'Short'),
            (3, 0.3, 1.5, 3.0, 16, 1, 'Long'),
            (3, 0.3, 2.0, 4.0, 32, -1, 'Short'),
            (3, 0.3, 2.0, 4.0, 32, 1, 'Long'),
            # Different deviation
            (3, 0.2, 1.5, 3.0, 16, 0, 'Both_D0.2'),
            (3, 0.5, 1.5, 3.0, 16, 0, 'Both_D0.5'),
            # Tighter SL
            (3, 0.3, 1.0, 2.0, 16, 0, 'Both_Tight'),
            (3, 0.3, 1.0, 3.0, 16, 0, 'Both_1:3'),
            # Different check hours
            (2, 0.3, 1.5, 3.0, 16, 0, 'Both_CH2'),
            (4, 0.3, 1.5, 3.0, 16, 0, 'Both_CH4'),
            (5, 0.3, 1.5, 3.0, 16, 0, 'Both_CH5'),
        ]

        for ch, dev, sl, tp, mh, df_filt, label in configs:
            r = scan_overnight(daily, spread, ch, dev, sl, tp, mh, df_filt)
            name = f"{symbol} {label} SL={sl} TP={tp}"
            a = analyze(name, r)
            if a and a['n'] >= 30:
                all_results.append(a)

    # Sort and display
    all_results.sort(key=lambda x: x['pf'], reverse=True)

    print(f"\n{'='*80}")
    print(f"  CROSS-PAIR RANKING (Top 30)")
    print(f"{'='*80}")
    print(f"{'Name':<50} {'N':<5} {'N/yr':<5} {'WR%':<5} {'PF':<6} {'IS':<6} {'OOS':<6} {'Yr+':<5}")

    for s in all_results[:30]:
        print(f"{s['name'][:50]:<50} {s['n']:<5} {s['n_yr']:<5.0f} {s['wr']:<5.1f} {s['pf']:<6.2f} {s['is_pf']:<6.2f} {s['oos_pf']:<6.2f} {s['yrs_pos']}/{s['yrs_tot']}")

    # Best per symbol
    print(f"\n  Best per symbol:")
    seen = set()
    for s in all_results:
        sym = s['name'].split()[0]
        if sym not in seen:
            seen.add(sym)
            print(f"  >> {s['name']}")
            print(f"     PF={s['pf']:.2f} IS={s['is_pf']:.2f} OOS={s['oos_pf']:.2f} N={s['n']} ({s['n_yr']:.0f}/yr) Yr+={s['yrs_pos']}/{s['yrs_tot']}")

    # How many are profitable?
    profitable = len([r for r in all_results if r['pf'] > 1.0])
    strong = len([r for r in all_results if r['pf'] > 1.2])
    print(f"\n  Summary: {profitable}/{len(all_results)} profitable (PF>1.0), {strong} strong (PF>1.2)")
    print(f"{'='*80}")
