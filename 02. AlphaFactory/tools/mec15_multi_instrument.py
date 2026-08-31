"""
MEC-15 Extended Research — Multi-instrument + M5 + Direction analysis
Tests:
  1. Gold M5 (finer granularity for overnight MR)
  2. EURUSD M15 overnight MR
  3. USDJPY M15 overnight MR
  4. GBPUSD M15 overnight MR
  5. Gold M15 overnight MR LONG (flip direction)

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

SPREAD_COSTS = {
    'XAUUSD+': 0.30,    # ~30 points
    'XAUUSD': 0.30,
    'EURUSD': 0.00012,   # ~1.2 pips
    'USDJPY': 0.012,     # ~1.2 pips
    'GBPUSD': 0.00015,   # ~1.5 pips
}

DATE_FROM = datetime(2019, 1, 1)
DATE_TO = datetime(2026, 1, 1)


def load_symbol(symbol, tf):
    if not mt5.initialize():
        print(f"[ERR] MT5 init failed"); return None

    # Try with suffix first
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"  [WARN] {symbol} not found, trying alternatives...")
        # Try without +
        alt = symbol.replace('+', '')
        info = mt5.symbol_info(alt)
        if info is None:
            print(f"  [ERR] {alt} also not found")
            mt5.shutdown()
            return None
        symbol = alt

    if not info.visible:
        mt5.symbol_select(symbol, True)

    rates = mt5.copy_rates_range(symbol, tf, DATE_FROM, DATE_TO)
    if rates is None or len(rates) == 0:
        print(f"  [ERR] No data for {symbol}")
        mt5.shutdown()
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    df['dow'] = df.index.dayofweek
    df['date'] = df.index.date
    df['year'] = df.index.year

    # ATR
    tr = pd.DataFrame()
    tr['hl'] = df['high'] - df['low']
    tr['hc'] = abs(df['high'] - df['close'].shift(1))
    tr['lc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = tr.max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean()

    # Regime
    daily_close = df.groupby('date')['close'].last()
    ema50 = daily_close.ewm(span=50, adjust=False).mean()
    slope = ema50.diff(10) / ema50.shift(10)
    regime_map = {}
    for d, s in slope.items():
        if pd.isna(s): regime_map[d] = 'flat'
        elif s > 0.003: regime_map[d] = 'up'
        elif s < -0.003: regime_map[d] = 'down'
        else: regime_map[d] = 'flat'
    df['regime'] = df['date'].map(regime_map).fillna('flat')

    # Prev day close
    prev_close = daily_close.shift(1)
    df['prev_day_close'] = df['date'].map(prev_close.to_dict())

    print(f"  [OK] {symbol}: {len(df)} bars, {df['date'].nunique()} days, {df.index[0].date()} to {df.index[-1].date()}")
    return df, symbol


def build_daily_generic(df):
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
        }
    return daily


def simulate_trade(bars, direction, sl_dist, tp_dist, max_hold=16):
    if len(bars) == 0: return None, 'no_bars'
    entry = bars.iloc[0]['open']
    if direction == 1:
        sl, tp = entry - sl_dist, entry + tp_dist
    else:
        sl, tp = entry + sl_dist, entry - tp_dist
    for i in range(min(max_hold, len(bars))):
        bar = bars.iloc[i]
        if direction == 1:
            if bar['low'] <= sl: return sl, 'sl'
            if bar['high'] >= tp: return tp, 'tp'
        else:
            if bar['high'] >= sl: return sl, 'sl'
            if bar['low'] <= tp: return tp, 'tp'
    return bars.iloc[min(max_hold-1, len(bars)-1)]['close'], 'timeout'


def scan_overnight_generic(daily, spread_cost, check_hour=3, deviation_mult=0.3,
                           sl_mult=1.5, tp_mult=3.0, max_hold=16,
                           direction_filter=0, regime_filter=None):
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if regime_filter:
            if regime_filter == 'up' and d['regime'] != 'up': continue
            if regime_filter == 'trending' and d['regime'] == 'flat': continue

        atr = d['atr']
        check_bars = d['bars'][(d['bars']['hour'] >= check_hour) & (d['bars']['hour'] <= check_hour)]
        if len(check_bars) == 0:
            continue

        current = check_bars.iloc[-1]['close']
        deviation = current - d['prev_close']

        direction = 0
        if deviation > deviation_mult * atr:
            direction = -1
        elif deviation < -deviation_mult * atr:
            direction = 1
        else:
            continue

        if direction_filter != 0 and direction != direction_filter:
            continue

        remaining = d['bars'].loc[d['bars'].index > check_bars.iloc[-1].name]
        if len(remaining) < 2:
            continue

        entry = remaining.iloc[0]['open']
        exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, max_hold)
        if exit_p is None:
            continue

        pnl = (exit_p - entry) * direction - spread_cost
        results.append({
            'date': date, 'year': d['year'], 'dow': d['dow'],
            'pnl': pnl, 'direction': direction, 'exit_reason': exit_r
        })

    return pd.DataFrame(results) if results else None


def analyze_and_print(name, df_r, show_yearly=True):
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
    net = df_r['pnl'].sum()
    wr = len(wins) / n * 100

    # Yearly
    yrs_pos = 0
    yr_lines = []
    for year, yg in df_r.groupby('year'):
        yw = yg[yg['pnl'] > 0]
        yl = yg[yg['pnl'] <= 0]
        ygp = yw['pnl'].sum() if len(yw) > 0 else 0
        ygl = abs(yl['pnl'].sum()) if len(yl) > 0 else 0.001
        ynet = yg['pnl'].sum()
        ypf = ygp / ygl
        if ynet > 0: yrs_pos += 1
        yr_lines.append(f"    {year}: n={len(yg):<4} PF={ypf:.2f}  Net={ynet:>8.2f}")

    # Walk-forward
    is_data = df_r[df_r['year'] <= 2022]
    oos_data = df_r[df_r['year'] >= 2023]
    is_pf = 0
    oos_pf = 0
    if len(is_data) > 0:
        is_w = is_data[is_data['pnl'] > 0]['pnl'].sum()
        is_l = abs(is_data[is_data['pnl'] <= 0]['pnl'].sum())
        is_pf = is_w / is_l if is_l > 0 else 0
    if len(oos_data) > 0:
        oos_w = oos_data[oos_data['pnl'] > 0]['pnl'].sum()
        oos_l = abs(oos_data[oos_data['pnl'] <= 0]['pnl'].sum())
        oos_pf = oos_w / oos_l if oos_l > 0 else 0

    print(f"\n  {name}")
    print(f"  N={n} ({n/yrs:.0f}/yr) | WR={wr:.1f}% | PF={pf:.2f} | Net={net:.2f}")
    print(f"  Years+: {yrs_pos}/{yrs} | IS PF={is_pf:.2f} | OOS PF={oos_pf:.2f}")
    if show_yearly:
        for l in yr_lines:
            print(l)

    return {'name': name, 'n': n, 'n_yr': n/yrs, 'wr': wr, 'pf': pf,
            'net': net, 'yrs_pos': yrs_pos, 'yrs_tot': yrs,
            'is_pf': is_pf, 'oos_pf': oos_pf}


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("  MEC-15 EXTENDED RESEARCH")
    print("  Multi-instrument + M5 + Direction analysis")
    print("=" * 80)

    all_summaries = []

    # ============================================
    # 1. Gold M5
    # ============================================
    print("\n" + "=" * 60)
    print("  SECTION 1: XAUUSD+ M5 (finer granularity)")
    print("=" * 60)

    result = load_symbol("XAUUSD+", mt5.TIMEFRAME_M5)
    if result:
        df_m5, sym = result
        mt5.shutdown()
        daily_m5 = build_daily_generic(df_m5)

        configs = [
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': -1, 'deviation_mult': 0.3, 'max_hold': 48},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': -1, 'deviation_mult': 0.3, 'max_hold': 48},
            {'check_hour': 2, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': -1, 'deviation_mult': 0.3, 'max_hold': 48},
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 0, 'deviation_mult': 0.3, 'max_hold': 48},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': 0, 'deviation_mult': 0.3, 'max_hold': 96},
        ]
        for cfg in configs:
            r = scan_overnight_generic(daily_m5, SPREAD_COSTS['XAUUSD+'], **cfg)
            d_name = {0: 'Both', 1: 'Long', -1: 'Short'}[cfg['direction_filter']]
            name = f"M5 {d_name} CH={cfg['check_hour']} SL={cfg['sl_mult']} TP={cfg['tp_mult']} MH={cfg['max_hold']}"
            s = analyze_and_print(name, r)
            if s: all_summaries.append(s)

    # ============================================
    # 2-4. Forex pairs M15
    # ============================================
    forex_pairs = ['EURUSD', 'USDJPY', 'GBPUSD']
    for pair in forex_pairs:
        print(f"\n{'='*60}")
        print(f"  SECTION: {pair} M15 Overnight MR")
        print(f"{'='*60}")

        result = load_symbol(pair, mt5.TIMEFRAME_M15)
        if result is None:
            continue
        df_fx, sym = result
        mt5.shutdown()
        daily_fx = build_daily_generic(df_fx)
        spread = SPREAD_COSTS.get(pair, SPREAD_COSTS.get(sym, 0.0002))

        configs = [
            # Short only (main hypothesis)
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': -1, 'deviation_mult': 0.3},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': -1, 'deviation_mult': 0.3},
            # Long only
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 1, 'deviation_mult': 0.3},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': 1, 'deviation_mult': 0.3},
            # Both directions
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 0, 'deviation_mult': 0.3},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': 0, 'deviation_mult': 0.3},
            # Different deviation thresholds
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 0, 'deviation_mult': 0.2},
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 0, 'deviation_mult': 0.5},
            # Wide R:R
            {'check_hour': 3, 'sl_mult': 1.0, 'tp_mult': 3.0, 'direction_filter': 0, 'deviation_mult': 0.3},
            # Regime-filtered
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 0, 'deviation_mult': 0.3, 'regime_filter': 'trending'},
        ]
        for cfg in configs:
            r = scan_overnight_generic(daily_fx, spread, **cfg)
            d_name = {0: 'Both', 1: 'Long', -1: 'Short'}[cfg['direction_filter']]
            rgm = cfg.get('regime_filter', 'all')
            name = f"{pair} {d_name} CH={cfg['check_hour']} SL={cfg['sl_mult']} TP={cfg['tp_mult']} D={cfg['deviation_mult']} R={rgm}"
            s = analyze_and_print(name, r)
            if s: all_summaries.append(s)

    # ============================================
    # 5. Gold M15 — LONG direction
    # ============================================
    print(f"\n{'='*60}")
    print(f"  SECTION: XAUUSD+ M15 - LONG direction MR")
    print(f"{'='*60}")

    result = load_symbol("XAUUSD+", mt5.TIMEFRAME_M15)
    if result:
        df_g15, sym = result
        mt5.shutdown()
        daily_g15 = build_daily_generic(df_g15)

        configs = [
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 1, 'deviation_mult': 0.3},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': 1, 'deviation_mult': 0.3},
            {'check_hour': 3, 'sl_mult': 1.5, 'tp_mult': 3.0, 'direction_filter': 1, 'deviation_mult': 0.3, 'regime_filter': 'up'},
            {'check_hour': 3, 'sl_mult': 2.0, 'tp_mult': 4.0, 'direction_filter': 1, 'deviation_mult': 0.3, 'max_hold': 32},
        ]
        for cfg in configs:
            r = scan_overnight_generic(daily_g15, SPREAD_COSTS['XAUUSD+'], **cfg)
            rgm = cfg.get('regime_filter', 'all')
            mh = cfg.get('max_hold', 16)
            name = f"GOLD Long CH=3 SL={cfg['sl_mult']} TP={cfg['tp_mult']} R={rgm} MH={mh}"
            s = analyze_and_print(name, r)
            if s: all_summaries.append(s)

    # ============================================
    # FINAL COMPARISON
    # ============================================
    print(f"\n{'='*80}")
    print(f"  FINAL CROSS-INSTRUMENT COMPARISON")
    print(f"{'='*80}")
    all_summaries.sort(key=lambda x: x['pf'], reverse=True)
    print(f"{'Name':<65} {'N':<5} {'N/yr':<5} {'WR%':<5} {'PF':<6} {'IS':<6} {'OOS':<6} {'Yr+':<5}")
    for s in all_summaries[:20]:
        print(f"{s['name'][:65]:<65} {s['n']:<5} {s['n_yr']:<5.0f} {s['wr']:<5.1f} {s['pf']:<6.2f} {s['is_pf']:<6.2f} {s['oos_pf']:<6.2f} {s['yrs_pos']}/{s['yrs_tot']}")

    # Best per instrument
    print(f"\n  Best per instrument/timeframe:")
    seen = set()
    for s in all_summaries:
        key = s['name'].split()[0]
        if key not in seen:
            seen.add(key)
            print(f"    {s['name'][:70]}")
            print(f"      PF={s['pf']:.2f} IS={s['is_pf']:.2f} OOS={s['oos_pf']:.2f} N={s['n']} ({s['n_yr']:.0f}/yr) Yr+={s['yrs_pos']}/{s['yrs_tot']}")

    print(f"\n{'='*80}")
