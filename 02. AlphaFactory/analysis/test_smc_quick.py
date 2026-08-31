"""Quick test for SMC Engine with real data"""
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from smc_engine import SMCEngine

def fetch_forex_data(symbol, start='2024-07-01', end='2024-12-31'):
    """Fetch forex data - try MT5 first, then yfinance"""
    # Try MT5 first
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 5000)
            mt5.shutdown()
            if rates is not None and len(rates) > 100:
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                print(f"  MT5: {len(df)} bars")
                return df[['open', 'high', 'low', 'close']]
    except:
        pass
    
    # Fallback to yfinance (last 730 days only for 1h)
    try:
        import yfinance as yf
        
        yf_map = {
            'EURUSD': 'EURUSD=X',
            'GBPUSD': 'GBPUSD=X',
            'USDJPY': 'USDJPY=X',
            'BTCUSD': 'BTC-USD',
            'XAUUSD': 'GC=F',
        }
        
        ticker = yf_map.get(symbol, symbol)
        df = yf.download(ticker, start=start, end=end, interval='1h', progress=False)
        
        if df.empty:
            # Try daily data for longer history
            df = yf.download(ticker, start='2022-01-01', end=end, interval='1d', progress=False)
            if not df.empty:
                print(f"  YF Daily: {len(df)} bars")
        else:
            print(f"  YF Hourly: {len(df)} bars")
        
        if df.empty:
            return None
        
        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).lower() for c in df.columns]
        return df[['open', 'high', 'low', 'close']]
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def backtest_simple(df, symbol, engine):
    """Simple backtest without VectorBT"""
    signals = engine.generate_signals(df)
    
    close = signals['close'].values
    entries_long = signals['entry_long'].values
    entries_short = signals['entry_short'].values
    sl_long = signals['sl_long'].values
    tp_long = signals['tp_long'].values
    sl_short = signals['sl_short'].values
    tp_short = signals['tp_short'].values
    
    trades = []
    position = 0
    entry_price = entry_sl = entry_tp = 0
    entry_idx = 0
    
    for i in range(1, len(close)):
        # Check exits
        if position == 1:
            if close[i] <= entry_sl:
                trades.append({'type': 'L', 'pnl': entry_sl - entry_price, 'result': 'SL'})
                position = 0
            elif close[i] >= entry_tp:
                trades.append({'type': 'L', 'pnl': entry_tp - entry_price, 'result': 'TP'})
                position = 0
        elif position == -1:
            if close[i] >= entry_sl:
                trades.append({'type': 'S', 'pnl': entry_price - entry_sl, 'result': 'SL'})
                position = 0
            elif close[i] <= entry_tp:
                trades.append({'type': 'S', 'pnl': entry_price - entry_tp, 'result': 'TP'})
                position = 0
        
        # Check entries
        if position == 0:
            if entries_long[i] and not np.isnan(sl_long[i]):
                position = 1
                entry_price = close[i]
                entry_sl = sl_long[i]
                entry_tp = tp_long[i]
            elif entries_short[i] and not np.isnan(sl_short[i]):
                position = -1
                entry_price = close[i]
                entry_sl = sl_short[i]
                entry_tp = tp_short[i]
    
    if len(trades) == 0:
        return {'symbol': symbol, 'trades': 0, 'pf': 0, 'win_rate': 0}
    
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf['pnl'] > 0]
    losses = tdf[tdf['pnl'] < 0]
    
    gross_p = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_l = abs(losses['pnl'].sum()) if len(losses) > 0 else 1
    
    return {
        'symbol': symbol,
        'trades': len(tdf),
        'long': len(tdf[tdf['type'] == 'L']),
        'short': len(tdf[tdf['type'] == 'S']),
        'win_rate': round(len(wins) / len(tdf) * 100, 1),
        'pf': round(gross_p / gross_l, 2) if gross_l > 0 else 0,
        'gross_p': round(gross_p, 4),
        'gross_l': round(gross_l, 4),
    }

def main():
    print("=" * 60)
    print("SMC MULTI-ASSET TEST")
    print("=" * 60)
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD']
    
    # Test different parameter sets
    configs = [
        {'name': 'Baseline', 'use_ob': True, 'use_fvg': True, 'use_pd_zone': True, 'rr_ratio': 2.0},
        {'name': 'OB Only', 'use_ob': True, 'use_fvg': False, 'use_pd_zone': True, 'rr_ratio': 2.0},
        {'name': 'FVG Only', 'use_ob': False, 'use_fvg': True, 'use_pd_zone': True, 'rr_ratio': 2.0},
        {'name': 'No PD Zone', 'use_ob': True, 'use_fvg': True, 'use_pd_zone': False, 'rr_ratio': 2.0},
        {'name': 'Structure Only', 'use_ob': False, 'use_fvg': False, 'use_pd_zone': False, 'rr_ratio': 2.0},
    ]
    
    all_results = []
    
    for symbol in symbols:
        print(f"\nFetching {symbol}...")
        df = fetch_forex_data(symbol)
        
        if df is None or len(df) < 500:
            print(f"  Insufficient data for {symbol}")
            continue
        
        print(f"  Loaded {len(df)} bars")
        
        for cfg in configs:
            engine = SMCEngine(
                ltf_swing_len=5,
                use_ob=cfg['use_ob'],
                use_fvg=cfg['use_fvg'],
                use_pd_zone=cfg['use_pd_zone'],
                rr_ratio=cfg['rr_ratio'],
            )
            
            result = backtest_simple(df, symbol, engine)
            result['config'] = cfg['name']
            all_results.append(result)
            
            if result['trades'] > 0:
                print(f"  {cfg['name']}: Trades={result['trades']}, WR={result['win_rate']}%, PF={result['pf']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    results_df = pd.DataFrame(all_results)
    
    # Group by config
    for cfg_name in results_df['config'].unique():
        cfg_data = results_df[results_df['config'] == cfg_name]
        valid = cfg_data[cfg_data['trades'] > 0]
        
        if len(valid) > 0:
            avg_pf = valid['pf'].mean()
            avg_wr = valid['win_rate'].mean()
            total_trades = valid['trades'].sum()
            print(f"\n{cfg_name}:")
            print(f"  Avg PF: {avg_pf:.2f}")
            print(f"  Avg WR: {avg_wr:.1f}%")
            print(f"  Total Trades: {total_trades}")
    
    # Save
    results_df.to_csv('smc_test_results.csv', index=False)
    print("\nResults saved to smc_test_results.csv")

if __name__ == "__main__":
    main()
