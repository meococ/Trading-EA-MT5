"""
Extended Edge Scanner — 5 NEW untested gold intraday mechanisms
MEC-15: Overnight Mean Reversion (Asian session)
MEC-16: Volume Spike Reversal (tick volume anomaly)
MEC-17: End-of-Day Momentum Fade (NY close reversion)
MEC-18: London-NY Overlap Divergence (session disconnect)
MEC-19: Opening Range Breakout (first 30min of each session)

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
SPREAD_COST = 0.30  # $0.30 per unit

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

    # ATR-14
    tr = pd.DataFrame()
    tr['hl'] = df['high'] - df['low']
    tr['hc'] = abs(df['high'] - df['close'].shift(1))
    tr['lc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = tr.max(axis=1)
    df['atr14'] = df['tr'].rolling(14).mean()

    # Volume MA for spike detection
    df['vol_ma20'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma20'].clip(lower=1)

    # D1 EMA50 regime
    daily_close = df.groupby('date')['close'].last()
    ema50 = daily_close.ewm(span=50, adjust=False).mean()
    slope = ema50.diff(10) / ema50.shift(10)
    regime_map = {d: ('trending_up' if s > 0.005 else ('trending_down' if s < -0.005 else 'flat'))
                  for d, s in slope.items() if not pd.isna(s)}
    df['regime'] = df['date'].map(regime_map).fillna('flat')

    # Previous day close (for overnight mean reversion)
    prev_close = daily_close.shift(1)
    df['prev_day_close'] = df['date'].map(prev_close.to_dict())

    print(f"[OK] Loaded {len(df)} bars, {df['date'].nunique()} days")
    mt5.shutdown()
    return df


def build_daily(df):
    daily = {}
    for date, group in df.groupby('date'):
        asian = group[(group['hour'] >= 0) & (group['hour'] < 8)]
        london = group[(group['hour'] >= 8) & (group['hour'] < 14)]
        ny = group[(group['hour'] >= 14) & (group['hour'] < 21)]
        overlap = group[(group['hour'] >= 14) & (group['hour'] < 17)]  # LDN/NY overlap

        if len(asian) < 4:
            continue

        atr = asian['atr14'].iloc[-1] if not pd.isna(asian['atr14'].iloc[-1]) else None

        daily[date] = {
            'asian_hi': asian['high'].max(),
            'asian_lo': asian['low'].min(),
            'asian_range': asian['high'].max() - asian['low'].min(),
            'asian_close': asian['close'].iloc[-1],
            'atr': atr,
            'regime': group['regime'].iloc[0],
            'dow': group['dow'].iloc[0],
            'year': group['year'].iloc[0],
            'prev_close': group['prev_day_close'].iloc[0] if not pd.isna(group['prev_day_close'].iloc[0]) else None,
            'bars': group,
            'asian': asian,
            'london': london,
            'ny': ny,
            'overlap': overlap,
        }
    return daily


def simulate_trade(bars, direction, sl_dist, tp_dist, max_hold=16):
    if len(bars) == 0:
        return None, 'no_bars'
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


def quick_stats(df_r):
    if df_r is None or len(df_r) == 0:
        return {'n': 0, 'n_yr': 0, 'wr': 0, 'pf': 0, 'net': 0, 'avg': 0, 'years_pos': 0, 'years_tot': 0}
    n = len(df_r)
    yrs = max(df_r['year'].nunique(), 1)
    wins = df_r[df_r['pnl'] > 0]
    losses = df_r[df_r['pnl'] <= 0]
    gp = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    return {
        'n': n, 'n_yr': n/yrs,
        'wr': len(wins)/n*100,
        'pf': gp/gl,
        'net': df_r['pnl'].sum(),
        'avg': df_r['pnl'].mean(),
        'years_pos': sum(1 for _, yg in df_r.groupby('year') if yg['pnl'].sum() > 0),
        'years_tot': yrs
    }


# ===========================================================================
# MEC-15: Overnight Mean Reversion
# ===========================================================================
def scan_overnight_mr(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None):
    """
    Asian session (00:00-07:59 server) price reverts toward previous NY close.
    Entry: if Asian open drifts away from prev close -> fade back.
    Check at H02-H03: if price > prev_close + threshold -> short. Vice versa -> long.
    """
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if d['prev_close'] is None or d['prev_close'] <= 0:
            continue
        if regime_filter:
            if regime_filter == 'trending' and d['regime'] == 'flat': continue
            elif regime_filter not in ('trending', None) and d['regime'] != regime_filter: continue

        atr = d['atr']
        prev_c = d['prev_close']

        # Check at hour 2-3 (2h into Asian)
        check_bars = d['asian'][(d['asian']['hour'] >= 2) & (d['asian']['hour'] <= 3)]
        if len(check_bars) == 0:
            continue

        current_price = check_bars.iloc[-1]['close']
        deviation = current_price - prev_c

        direction = 0
        if deviation > 0.3 * atr:  # drifted up -> short (revert)
            direction = -1
        elif deviation < -0.3 * atr:  # drifted down -> long (revert)
            direction = 1
        else:
            continue

        if direction_filter != 0 and direction != direction_filter:
            continue

        # Entry at next bar
        remaining = d['asian'].loc[d['asian'].index > check_bars.iloc[-1].name]
        if len(remaining) < 2:
            # If Asian running out, use London bars
            remaining = d['london']
        if len(remaining) < 2:
            continue

        entry = remaining.iloc[0]['open']
        exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, 16)
        if exit_p is None:
            continue

        pnl = (exit_p - entry) * direction - SPREAD_COST
        results.append({'date': date, 'year': d['year'], 'pnl': pnl, 'direction': direction, 'exit_reason': exit_r})

    return pd.DataFrame(results) if results else None


# ===========================================================================
# MEC-16: Volume Spike Reversal
# ===========================================================================
def scan_volume_spike_reversal(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None,
                                vol_threshold=2.5, scan_hours=(8, 17)):
    """
    When tick volume spikes > 2.5× MA20, AND price creates a significant wick,
    fade the spike direction (exhaustion signal).
    """
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if regime_filter:
            if regime_filter == 'trending' and d['regime'] == 'flat': continue
            elif regime_filter not in ('trending', None) and d['regime'] != regime_filter: continue

        atr = d['atr']
        session_bars = d['bars'][(d['bars']['hour'] >= scan_hours[0]) & (d['bars']['hour'] <= scan_hours[1])]

        for _, bar in session_bars.iterrows():
            if bar['vol_ratio'] < vol_threshold:
                continue

            rng = bar['high'] - bar['low']
            if rng <= 0:
                continue

            # Check for rejection wick
            body = abs(bar['close'] - bar['open'])
            upper_wick = bar['high'] - max(bar['close'], bar['open'])
            lower_wick = min(bar['close'], bar['open']) - bar['low']

            direction = 0
            if upper_wick > 0.5 * rng and upper_wick > 2 * body:
                # Long upper wick + volume spike = bearish exhaustion
                direction = -1
            elif lower_wick > 0.5 * rng and lower_wick > 2 * body:
                # Long lower wick + volume spike = bullish exhaustion
                direction = 1
            else:
                continue

            if direction_filter != 0 and direction != direction_filter:
                continue

            remaining = d['bars'].loc[d['bars'].index > bar.name]
            if len(remaining) < 2:
                continue

            entry = remaining.iloc[0]['open']
            exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, 12)
            if exit_p is None:
                continue

            pnl = (exit_p - entry) * direction - SPREAD_COST
            results.append({'date': date, 'year': d['year'], 'pnl': pnl, 'direction': direction, 'exit_reason': exit_r})
            break  # 1 per day

    return pd.DataFrame(results) if results else None


# ===========================================================================
# MEC-17: End-of-Day Momentum Fade
# ===========================================================================
def scan_eod_fade(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None):
    """
    Near end of NY session (h=19-20 server), if price has moved > 1 ATR
    from London open in one direction, fade it (mean reversion overnight).
    Hold max 6h into Asian session.
    """
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 4:  # skip Thu-Fri (weekend risk)
            continue
        if regime_filter:
            if regime_filter == 'trending' and d['regime'] == 'flat': continue
            elif regime_filter not in ('trending', None) and d['regime'] != regime_filter: continue

        atr = d['atr']

        # London open price
        if len(d['london']) == 0:
            continue
        ldn_open = d['london'].iloc[0]['open']

        # Late NY bars (19:xx - 20:xx server)
        late_ny = d['bars'][(d['bars']['hour'] >= 19) & (d['bars']['hour'] <= 20)]
        if len(late_ny) == 0:
            continue

        current = late_ny.iloc[-1]['close']
        move = current - ldn_open

        direction = 0
        if move > 1.0 * atr:  # big up move -> fade short
            direction = -1
        elif move < -1.0 * atr:  # big down move -> fade long
            direction = 1
        else:
            continue

        if direction_filter != 0 and direction != direction_filter:
            continue

        # Entry at next bar
        remaining = d['bars'].loc[d['bars'].index > late_ny.iloc[-1].name]
        if len(remaining) < 2:
            continue

        entry = remaining.iloc[0]['open']
        exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, 24)  # hold overnight
        if exit_p is None:
            continue

        pnl = (exit_p - entry) * direction - SPREAD_COST
        results.append({'date': date, 'year': d['year'], 'pnl': pnl, 'direction': direction, 'exit_reason': exit_r})

    return pd.DataFrame(results) if results else None


# ===========================================================================
# MEC-18: London-NY Overlap Divergence
# ===========================================================================
def scan_overlap_divergence(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None):
    """
    During London-NY overlap (14:00-16:59 server), if price breaks a new intraday
    extreme but fails to hold (closes back), fade the failed breakout.
    """
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if regime_filter:
            if regime_filter == 'trending' and d['regime'] == 'flat': continue
            elif regime_filter not in ('trending', None) and d['regime'] != regime_filter: continue

        atr = d['atr']
        overlap = d['overlap']
        if len(overlap) < 2:
            continue

        # Intraday high/low before overlap
        pre_overlap = d['bars'][d['bars']['hour'] < 14]
        if len(pre_overlap) < 4:
            continue
        day_hi = pre_overlap['high'].max()
        day_lo = pre_overlap['low'].min()

        for _, bar in overlap.iterrows():
            # Check for failed breakout
            broke_hi = bar['high'] > day_hi + 0.1 * atr
            broke_lo = bar['low'] < day_lo - 0.1 * atr
            close_inside = bar['close'] <= day_hi and bar['close'] >= day_lo

            direction = 0
            if broke_hi and not broke_lo and close_inside:
                direction = -1  # failed breakout high -> short
            elif broke_lo and not broke_hi and close_inside:
                direction = 1  # failed breakout low -> long
            else:
                continue

            if direction_filter != 0 and direction != direction_filter:
                continue

            remaining = d['bars'].loc[d['bars'].index > bar.name]
            if len(remaining) < 2:
                continue

            entry = remaining.iloc[0]['open']
            exit_p, exit_r = simulate_trade(remaining, direction, sl_mult * atr, tp_mult * atr, 12)
            if exit_p is None:
                continue

            pnl = (exit_p - entry) * direction - SPREAD_COST
            results.append({'date': date, 'year': d['year'], 'pnl': pnl, 'direction': direction, 'exit_reason': exit_r})
            break  # 1 per day

    return pd.DataFrame(results) if results else None


# ===========================================================================
# MEC-19: Opening Range Breakout (30min ORB per session)
# ===========================================================================
def scan_orb(daily, sl_mult, tp_mult, direction_filter=0, regime_filter=None,
             session='london', orb_bars=2):
    """
    First 30min (2 bars M15) of London or NY: build mini-range, then trade breakout.
    """
    results = []
    for date, d in daily.items():
        if d['atr'] is None or d['atr'] <= 0 or d['dow'] >= 5:
            continue
        if regime_filter:
            if regime_filter == 'trending' and d['regime'] == 'flat': continue
            elif regime_filter not in ('trending', None) and d['regime'] != regime_filter: continue

        atr = d['atr']
        if session == 'london':
            sess_bars = d['london']
        else:
            sess_bars = d['ny']

        if len(sess_bars) < orb_bars + 4:
            continue

        # ORB range = first N bars
        orb = sess_bars.iloc[:orb_bars]
        orb_hi = orb['high'].max()
        orb_lo = orb['low'].min()
        orb_range = orb_hi - orb_lo

        if orb_range < 0.3 * atr or orb_range > 3.0 * atr:
            continue

        # Wait for breakout in subsequent bars
        post_orb = sess_bars.iloc[orb_bars:]
        for _, bar in post_orb.iterrows():
            direction = 0
            if bar['close'] > orb_hi and bar['close'] > bar['open']:
                direction = 1  # bullish breakout
            elif bar['close'] < orb_lo and bar['close'] < bar['open']:
                direction = -1  # bearish breakout
            else:
                continue

            if direction_filter != 0 and direction != direction_filter:
                continue

            remaining = d['bars'].loc[d['bars'].index > bar.name]
            if len(remaining) < 2:
                continue

            entry = remaining.iloc[0]['open']
            # SL = ORB opposite extreme
            if direction == 1:
                sl_d = max(entry - orb_lo, sl_mult * atr)
                tp_d = tp_mult * sl_d
            else:
                sl_d = max(orb_hi - entry, sl_mult * atr)
                tp_d = tp_mult * sl_d

            exit_p, exit_r = simulate_trade(remaining, direction, sl_d, tp_d, 12)
            if exit_p is None:
                continue

            pnl = (exit_p - entry) * direction - SPREAD_COST
            results.append({'date': date, 'year': d['year'], 'pnl': pnl, 'direction': direction, 'exit_reason': exit_r})
            break  # 1 per day

    return pd.DataFrame(results) if results else None


# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("  EXTENDED GOLD EDGE SCANNER - 5 New Mechanisms")
    print("  XAUUSD+ M15 | 2019-2025")
    print("=" * 80)

    df = load_data()
    daily = build_daily(df)
    print(f"[OK] {len(daily)} trading days\n")

    sl_tp_combos = [
        (0.5, 0.75), (0.5, 1.0), (0.75, 1.0), (0.75, 1.5),
        (1.0, 1.0), (1.0, 1.5), (1.0, 2.0), (1.5, 2.0), (1.5, 3.0),
    ]
    regimes = [None, 'trending', 'trending_up', 'flat']
    directions = [0, 1, -1]

    all_results = []

    # Scan each mechanism
    mechanisms = {
        'MEC-15_OvernightMR': lambda sl, tp, d, r: scan_overnight_mr(daily, sl, tp, d, r),
        'MEC-16_VolSpike': lambda sl, tp, d, r: scan_volume_spike_reversal(daily, sl, tp, d, r),
        'MEC-17_EODFade': lambda sl, tp, d, r: scan_eod_fade(daily, sl, tp, d, r),
        'MEC-18_OverlapDiv': lambda sl, tp, d, r: scan_overlap_divergence(daily, sl, tp, d, r),
        'MEC-19_ORB_LDN': lambda sl, tp, d, r: scan_orb(daily, sl, tp, d, r, 'london'),
        'MEC-19_ORB_NY': lambda sl, tp, d, r: scan_orb(daily, sl, tp, d, r, 'ny'),
    }

    for mec_name, scan_fn in mechanisms.items():
        print(f"  Scanning {mec_name}...")
        for sl, tp in sl_tp_combos:
            for rgm in regimes:
                for dir_f in directions:
                    try:
                        r = scan_fn(sl, tp, dir_f, rgm)
                        s = quick_stats(r)
                        if s['n'] >= 20:
                            all_results.append({
                                'mec': mec_name,
                                'sl': sl, 'tp': tp,
                                'dir': dir_f, 'regime': rgm or 'all',
                                **s
                            })
                    except Exception as e:
                        pass

    results_df = pd.DataFrame(all_results)
    if len(results_df) == 0:
        print("\n  [!] NO RESULTS from any mechanism")
        sys.exit(0)

    results_df.sort_values('pf', ascending=False, inplace=True)

    print(f"\n{'='*80}")
    print(f"  TOP 30 VARIANTS BY PROFIT FACTOR")
    print(f"{'='*80}")
    print(f"{'Mech':<22} {'SL':<5} {'TP':<5} {'Dir':<5} {'Regime':<15} {'N':<6} {'N/yr':<6} {'WR%':<6} {'PF':<7} {'Net$':<10} {'Yr+':<5}")

    for _, row in results_df.head(30).iterrows():
        dir_str = {0: 'both', 1: 'long', -1: 'shrt'}[row['dir']]
        print(f"{row['mec']:<22} {row['sl']:<5.1f} {row['tp']:<5.1f} {dir_str:<5} {row['regime']:<15} {row['n']:<6} {row['n_yr']:<6.0f} {row['wr']:<6.1f} {row['pf']:<7.2f} {row['net']:<10.1f} {row['years_pos']}/{row['years_tot']}")

    # Per-mechanism top 3
    for mec in results_df['mec'].unique():
        sub = results_df[results_df['mec'] == mec].head(3)
        print(f"\n  Top 3 {mec}:")
        for _, row in sub.iterrows():
            dir_str = {0: 'both', 1: 'long', -1: 'shrt'}[row['dir']]
            print(f"    SL={row['sl']:.1f} TP={row['tp']:.1f} {dir_str:<5} {row['regime']:<15} n={row['n']:<4} n/yr={row['n_yr']:.0f} PF={row['pf']:.2f} Net=${row['net']:.1f} WR={row['wr']:.0f}% Yr+={row['years_pos']}/{row['years_tot']}")

    # Verdict
    print(f"\n{'='*80}")
    print(f"  EDGE VERDICT")
    print(f"{'='*80}")
    profitable = results_df[results_df['pf'] > 1.0]
    strong = results_df[results_df['pf'] > 1.2]
    print(f"  Total variants tested: {len(results_df)}")
    print(f"  PF > 1.0: {len(profitable)} ({len(profitable)/len(results_df)*100:.0f}%)")
    print(f"  PF > 1.2: {len(strong)} ({len(strong)/len(results_df)*100:.0f}%)")

    if len(strong) > 0:
        best = strong.iloc[0]
        dir_str = {0: 'both', 1: 'long', -1: 'shrt'}[best['dir']]
        print(f"\n  BEST: {best['mec']} SL={best['sl']} TP={best['tp']} {dir_str} {best['regime']}")
        print(f"  PF={best['pf']:.2f} N={best['n']} N/yr={best['n_yr']:.0f} WR={best['wr']:.1f}%")
        print(f"  Net=${best['net']:.2f} Years+={best['years_pos']}/{best['years_tot']}")
    elif len(profitable) > 0:
        best = profitable.iloc[0]
        dir_str = {0: 'both', 1: 'long', -1: 'shrt'}[best['dir']]
        print(f"\n  BEST (thin edge): {best['mec']} SL={best['sl']} TP={best['tp']} {dir_str} {best['regime']}")
        print(f"  PF={best['pf']:.2f} N={best['n']} N/yr={best['n_yr']:.0f}")
        print(f"  WARNING: PF < 1.2 = too thin for live trading with slippage")
    else:
        print(f"\n  NO VARIANT with PF > 1.0 found across all 5 mechanisms")

    print(f"\n{'='*80}")
