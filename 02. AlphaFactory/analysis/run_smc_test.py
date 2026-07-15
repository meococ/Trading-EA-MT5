"""
SMC Test - Chạy đúng, không ảo tưởng
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, '.')
from smc_engine import SMCEngine

def get_mt5_data(symbol, bars=2000):
    """Lấy data từ MT5"""
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print(f"MT5 init failed")
            return None
        
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, bars)
        mt5.shutdown()
        
        if rates is None or len(rates) == 0:
            print(f"No data for {symbol}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df[['open', 'high', 'low', 'close']]
    except Exception as e:
        print(f"Error: {e}")
        return None

def simple_backtest(df, symbol, engine):
    """Backtest đơn giản - đếm trades và tính PnL"""
    signals = engine.generate_signals(df)
    
    close = signals['close'].values
    entry_long = signals['entry_long'].values
    entry_short = signals['entry_short'].values
    sl_long = signals['sl_long'].values
    tp_long = signals['tp_long'].values
    sl_short = signals['sl_short'].values
    tp_short = signals['tp_short'].values
    
    # Count signals
    long_signals = np.sum(entry_long)
    short_signals = np.sum(entry_short)
    
    # Simple trade simulation
    trades = []
    pos = 0  # 0=flat, 1=long, -1=short
    entry_p = 0
    sl_p = 0
    tp_p = 0
    
    for i in range(len(close)):
        # Exit check
        if pos == 1:
            if close[i] <= sl_p:
                trades.append({'dir': 'L', 'pnl': sl_p - entry_p, 'exit': 'SL'})
                pos = 0
            elif close[i] >= tp_p:
                trades.append({'dir': 'L', 'pnl': tp_p - entry_p, 'exit': 'TP'})
                pos = 0
        elif pos == -1:
            if close[i] >= sl_p:
                trades.append({'dir': 'S', 'pnl': entry_p - sl_p, 'exit': 'SL'})
                pos = 0
            elif close[i] <= tp_p:
                trades.append({'dir': 'S', 'pnl': entry_p - tp_p, 'exit': 'TP'})
                pos = 0
        
        # Entry check
        if pos == 0:
            if entry_long[i] and not np.isnan(sl_long[i]) and not np.isnan(tp_long[i]):
                pos = 1
                entry_p = close[i]
                sl_p = sl_long[i]
                tp_p = tp_long[i]
            elif entry_short[i] and not np.isnan(sl_short[i]) and not np.isnan(tp_short[i]):
                pos = -1
                entry_p = close[i]
                sl_p = sl_short[i]
                tp_p = tp_short[i]
    
    # Calc metrics
    if len(trades) == 0:
        return {
            'symbol': symbol,
            'signals_L': long_signals,
            'signals_S': short_signals,
            'trades': 0,
            'pf': 0,
            'wr': 0
        }
    
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf['pnl'] > 0]
    losses = tdf[tdf['pnl'] < 0]
    
    gross_win = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.0001
    
    return {
        'symbol': symbol,
        'signals_L': int(long_signals),
        'signals_S': int(short_signals),
        'trades': len(tdf),
        'wins': len(wins),
        'losses': len(losses),
        'pf': round(gross_win / gross_loss, 2) if gross_loss > 0 else 0,
        'wr': round(len(wins) / len(tdf) * 100, 1)
    }

def main():
    print("=" * 50)
    print("SMC BACKTEST - VERIFICATION")
    print("=" * 50)
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
    
    # Config: FVG + PD Zone (best from previous)
    engine = SMCEngine(
        ltf_swing_len=5,
        use_ob=False,
        use_fvg=True,
        use_pd_zone=True,
        premium_level=0.70,
        discount_level=0.30,
        rr_ratio=2.0
    )
    
    results = []
    for sym in symbols:
        print(f"\n{sym}:")
        df = get_mt5_data(sym, bars=3000)
        
        if df is None:
            print("  No data")
            continue
        
        print(f"  Data: {len(df)} bars")
        print(f"  Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
        
        r = simple_backtest(df, sym, engine)
        results.append(r)
        
        print(f"  Signals: L={r['signals_L']}, S={r['signals_S']}")
        print(f"  Trades: {r['trades']} (W={r.get('wins',0)}, L={r.get('losses',0)})")
        print(f"  PF: {r['pf']}, WR: {r['wr']}%")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if results:
        rdf = pd.DataFrame(results)
        print(rdf.to_string(index=False))
        
        valid = rdf[rdf['trades'] > 0]
        if len(valid) > 0:
            print(f"\nAvg PF: {valid['pf'].mean():.2f}")
            print(f"Avg WR: {valid['wr'].mean():.1f}%")
            print(f"Total trades: {valid['trades'].sum()}")

if __name__ == "__main__":
    main()
