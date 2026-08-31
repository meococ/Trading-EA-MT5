"""
GRAND EDGE SCAN — All non-gold instruments
Tests overnight MR + session breakout + momentum on:
  - NSDQ+ (Nasdaq 100), SP+ (S&P 500), DOW+ (Dow Jones)
  - DAX+ (German index), NIKKEI+, ASX+
  - WTI+, BRENT+ (Oil)
  - Top forex pairs: EURUSD+, USDJPY+, GBPUSD+, GBPJPY+, EURJPY+

Mechanisms tested per instrument:
  M1: Overnight Mean Reversion (from gold research)
  M2: Session Open Breakout (first 30min high/low break)
  M3: Momentum Continuation (strong bar -> follow)
  M4: Gap Fill (overnight gap -> fade)
  M5: Time-of-Day Mean Reversion (specific hour has reversion tendency)

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

DATE_FROM = datetime(2019, 1, 1)
DATE_TO = datetime(2026, 1, 1)
TF = mt5.TIMEFRAME_M15

# Symbol configs: {symbol: spread_cost}
INSTRUMENTS = {
    # Indices
    'NSDQ+': 2.0,     # ~2 points
    'SP+': 0.5,        # ~0.5 points
    'DOW+': 3.0,       # ~3 points
    'DAX+': 1.5,       # ~1.5 points
    'NIKKEI+': 15.0,   # ~15 yen
    'ASX+': 2.0,       # ~2 points
    # Oil
    'WTI+': 0.04,      # ~4 cents
    'BRENT+': 0.04,    # ~4 cents
    # Top forex
    'EURUSD+': 0.00012,
    'USDJPY+': 0.015,
    'GBPJPY+': 0.025,
    'EURJPY+': 0.018,
}


def load_and_prepare(symbol, tf=TF):
    if not mt5.initialize():
        return None
    info = mt5.symbol_info(symbol)
    if info is None:
        mt5.shutdown(); return None
    if not info.visible:
        mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_range(symbol, tf, DATE_FROM, DATE_TO)
    mt5.shutdown()
    if rates is None or len(rates) < 500:
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
    daily_open = df.groupby('date')['open'].first()
    daily_high = df.groupby('date')['high'].max()
    daily_low = df.groupby('date')['low'].min()

    prev_close = daily_close.shift(1)
    df['prev_day_close'] = df['date'].map(prev_close.to_dict())
    df['day_open'] = df['date'].map(daily_open.to_dict())

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


# ===========================================================================
# MECHANISM SCANNERS
# ===========================================================================

def scan_M1_overnight_mr(daily, spread, direction_filter=-1):
    """Overnight mean reversion (adapted from MEC-15)"""
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        atr = d['atr']
        check_bars = d['bars'][d['bars']['hour'] == 3]
        if len(check_bars) == 0: continue
        current = check_bars.iloc[-1]['close']
        dev = current - d['prev_close']
        direction = -1 if dev > 0.3 * atr else (1 if dev < -0.3 * atr else 0)
        if direction == 0: continue
        if direction_filter != 0 and direction != direction_filter: continue
        remaining = d['bars'].loc[d['bars'].index > check_bars.iloc[-1].name]
        if len(remaining) < 2: continue
        entry = remaining.iloc[0]['open']
        exit_p, _ = simulate_trade(remaining, direction, 2.0*atr, 4.0*atr, 32)
        if exit_p is None: continue
        pnl = (exit_p - entry) * direction - spread
        results.append({'year': d['year'], 'pnl': pnl})
    return pd.DataFrame(results) if results else None


def scan_M2_session_breakout(daily, spread, session_start=8, session_end=10, direction_filter=0):
    """Opening range breakout: build range in first 2 bars of session, trade breakout"""
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        atr = d['atr']
        # Build opening range (session_start to session_start+1)
        range_bars = d['bars'][(d['bars']['hour'] >= session_start) & (d['bars']['hour'] < session_start + 1)]
        if len(range_bars) < 2: continue
        range_hi = range_bars['high'].max()
        range_lo = range_bars['low'].min()
        range_width = range_hi - range_lo
        if range_width < 0.1 * atr or range_width > 2.0 * atr: continue

        # Look for breakout in session window
        trade_bars = d['bars'][(d['bars']['hour'] >= session_start + 1) & (d['bars']['hour'] <= session_end)]
        if len(trade_bars) < 2: continue

        for idx, bar in trade_bars.iterrows():
            direction = 0
            if bar['close'] > range_hi and bar['close'] > bar['open']:
                direction = 1  # Bullish breakout
            elif bar['close'] < range_lo and bar['close'] < bar['open']:
                direction = -1  # Bearish breakout
            if direction == 0: continue
            if direction_filter != 0 and direction != direction_filter: continue

            remaining = d['bars'].loc[d['bars'].index > idx]
            if len(remaining) < 2: break
            exit_p, _ = simulate_trade(remaining, direction, 1.5*atr, 3.0*atr, 16)
            if exit_p is None: break
            pnl = (exit_p - remaining.iloc[0]['open']) * direction - spread
            results.append({'year': d['year'], 'pnl': pnl})
            break  # One trade per day per session
    return pd.DataFrame(results) if results else None


def scan_M3_momentum(daily, spread, min_body_ratio=0.6, direction_filter=0):
    """Strong candle momentum: if M15 bar has body > 60% of range and > 0.5 ATR, follow"""
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        atr = d['atr']
        bars = d['bars'][(d['bars']['hour'] >= 8) & (d['bars']['hour'] <= 16)]
        traded_today = False
        for idx, bar in bars.iterrows():
            if traded_today: break
            body = abs(bar['close'] - bar['open'])
            rng = bar['high'] - bar['low']
            if rng <= 0: continue
            ratio = body / rng
            if ratio < min_body_ratio: continue
            if body < 0.5 * atr: continue  # Need significant move
            direction = 1 if bar['close'] > bar['open'] else -1
            if direction_filter != 0 and direction != direction_filter: continue

            remaining = d['bars'].loc[d['bars'].index > idx]
            if len(remaining) < 2: break
            exit_p, _ = simulate_trade(remaining, direction, 1.0*atr, 2.0*atr, 12)
            if exit_p is None: break
            pnl = (exit_p - remaining.iloc[0]['open']) * direction - spread
            results.append({'year': d['year'], 'pnl': pnl})
            traded_today = True
    return pd.DataFrame(results) if results else None


def scan_M4_gap_fill(daily, spread, min_gap=0.3):
    """Gap fill: if open deviates from prev close > 0.3 ATR, fade toward prev close"""
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        atr = d['atr']
        first_bar = d['bars'].iloc[0]
        gap = first_bar['open'] - d['prev_close']
        if abs(gap) < min_gap * atr: continue
        direction = -1 if gap > 0 else 1  # Fade the gap
        remaining = d['bars'].iloc[1:]
        if len(remaining) < 2: continue
        exit_p, _ = simulate_trade(remaining, direction, 1.5*atr, abs(gap)*0.8, 8)
        if exit_p is None: continue
        pnl = (exit_p - remaining.iloc[0]['open']) * direction - spread
        results.append({'year': d['year'], 'pnl': pnl})
    return pd.DataFrame(results) if results else None


def scan_M5_time_mr(daily, spread, entry_hour=15, direction_filter=0):
    """Time-of-day MR: at specific hour, fade last 2h direction"""
    results = []
    for date, d in daily.items():
        if d['atr'] <= 0 or d['dow'] >= 5: continue
        atr = d['atr']
        pre_bars = d['bars'][(d['bars']['hour'] >= entry_hour - 2) & (d['bars']['hour'] < entry_hour)]
        entry_bars = d['bars'][d['bars']['hour'] == entry_hour]
        if len(pre_bars) < 4 or len(entry_bars) == 0: continue

        pre_move = pre_bars.iloc[-1]['close'] - pre_bars.iloc[0]['open']
        if abs(pre_move) < 0.3 * atr: continue
        direction = -1 if pre_move > 0 else 1  # Fade
        if direction_filter != 0 and direction != direction_filter: continue

        remaining = d['bars'].loc[d['bars'].index > entry_bars.iloc[0].name]
        if len(remaining) < 2: continue
        exit_p, _ = simulate_trade(remaining, direction, 1.5*atr, 2.0*atr, 8)
        if exit_p is None: continue
        pnl = (exit_p - remaining.iloc[0]['open']) * direction - spread
        results.append({'year': d['year'], 'pnl': pnl})
    return pd.DataFrame(results) if results else None


def analyze(name, df_r):
    if df_r is None or len(df_r) == 0:
        return None
    n = len(df_r)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    yrs = max(df_r['year'].nunique(), 1)
    yrs_pos = sum(1 for _, yg in df_r.groupby('year') if yg['pnl'].sum() > 0)

    is_d = df_r[df_r['year'] <= 2022]
    oos_d = df_r[df_r['year'] >= 2023]
    is_pf = (is_d[is_d['pnl']>0]['pnl'].sum() / max(abs(is_d[is_d['pnl']<=0]['pnl'].sum()), 0.001)) if len(is_d) > 5 else 0
    oos_pf = (oos_d[oos_d['pnl']>0]['pnl'].sum() / max(abs(oos_d[oos_d['pnl']<=0]['pnl'].sum()), 0.001)) if len(oos_d) > 5 else 0

    return {'name': name, 'n': n, 'n_yr': n/yrs, 'wr': len(wins)/n*100,
            'pf': gp/gl, 'net': df_r['pnl'].sum(), 'is_pf': is_pf,
            'oos_pf': oos_pf, 'yrs_pos': yrs_pos, 'yrs_tot': yrs}


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("  GRAND EDGE SCAN — ALL INSTRUMENTS × 5 MECHANISMS")
    print("=" * 80)

    all_results = []

    for symbol, spread in INSTRUMENTS.items():
        print(f"\n{'='*60}")
        print(f"  {symbol}")
        print(f"{'='*60}")

        df = load_and_prepare(symbol)
        if df is None:
            print(f"  [SKIP] No data")
            continue
        print(f"  [OK] {len(df)} bars, {df['date'].nunique()} days")
        daily = build_daily(df)

        # M1: Overnight MR
        for d in [-1, 1, 0]:
            d_name = {-1: 'Short', 1: 'Long', 0: 'Both'}[d]
            r = scan_M1_overnight_mr(daily, spread, d)
            a = analyze(f"{symbol} M1_OvernightMR {d_name}", r)
            if a and a['n'] >= 20: all_results.append(a)

        # M2: Session Breakout (try different session starts)
        for ss in [8, 9, 13, 14, 15]:
            for d in [0, 1, -1]:
                d_name = {-1: 'Short', 1: 'Long', 0: 'Both'}[d]
                r = scan_M2_session_breakout(daily, spread, session_start=ss, session_end=ss+3, direction_filter=d)
                a = analyze(f"{symbol} M2_SessBreak H{ss} {d_name}", r)
                if a and a['n'] >= 20: all_results.append(a)

        # M3: Momentum
        for d in [0, 1, -1]:
            d_name = {-1: 'Short', 1: 'Long', 0: 'Both'}[d]
            r = scan_M3_momentum(daily, spread, direction_filter=d)
            a = analyze(f"{symbol} M3_Momentum {d_name}", r)
            if a and a['n'] >= 20: all_results.append(a)

        # M4: Gap Fill
        r = scan_M4_gap_fill(daily, spread)
        a = analyze(f"{symbol} M4_GapFill", r)
        if a and a['n'] >= 20: all_results.append(a)

        # M5: Time MR (try different hours)
        for h in [11, 13, 15, 17]:
            r = scan_M5_time_mr(daily, spread, entry_hour=h)
            a = analyze(f"{symbol} M5_TimeMR H{h}", r)
            if a and a['n'] >= 20: all_results.append(a)

    # FINAL RANKING
    all_results.sort(key=lambda x: x['pf'], reverse=True)

    print(f"\n{'='*80}")
    print(f"  GRAND RANKING — Top 30 (all instruments × mechanisms)")
    print(f"{'='*80}")
    print(f"{'Name':<55} {'N':<5} {'N/yr':<5} {'WR%':<5} {'PF':<6} {'IS':<6} {'OOS':<6} {'Yr+':<5}")
    for s in all_results[:30]:
        print(f"{s['name'][:55]:<55} {s['n']:<5} {s['n_yr']:<5.0f} {s['wr']:<5.1f} {s['pf']:<6.2f} {s['is_pf']:<6.2f} {s['oos_pf']:<6.2f} {s['yrs_pos']}/{s['yrs_tot']}")

    # Count profitable
    prof = len([r for r in all_results if r['pf'] > 1.0])
    strong = len([r for r in all_results if r['pf'] > 1.2])
    print(f"\n  Total variants: {len(all_results)}")
    print(f"  Profitable (PF>1.0): {prof} ({prof*100//max(len(all_results),1)}%)")
    print(f"  Strong (PF>1.2): {strong}")

    # Best per instrument
    print(f"\n  Best per instrument:")
    seen = set()
    for s in all_results:
        sym = s['name'].split()[0]
        if sym not in seen:
            seen.add(sym)
            print(f"  >> {s['name']}")
            print(f"     PF={s['pf']:.2f} IS={s['is_pf']:.2f} OOS={s['oos_pf']:.2f} N={s['n']} ({s['n_yr']:.0f}/yr)")

    # Best per mechanism
    print(f"\n  Best per mechanism:")
    mechs = {}
    for s in all_results:
        parts = s['name'].split()
        mech = parts[1] if len(parts) > 1 else 'unknown'
        if mech not in mechs or s['pf'] > mechs[mech]['pf']:
            mechs[mech] = s
    for mech, s in sorted(mechs.items(), key=lambda x: x[1]['pf'], reverse=True):
        print(f"  >> {mech}: {s['name']}")
        print(f"     PF={s['pf']:.2f} IS={s['is_pf']:.2f} OOS={s['oos_pf']:.2f} N={s['n']} ({s['n_yr']:.0f}/yr)")

    print(f"\n{'='*80}")
