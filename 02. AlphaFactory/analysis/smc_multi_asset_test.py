"""
SMC Multi-Asset Backtester
==========================
Test SMC strategy across multiple assets using VectorBT
Assets: EURUSD, GBPUSD, USDJPY, BTCUSD, XAUUSD

Author: AlphaFactory
"""

import numpy as np
import pandas as pd
import vectorbt as vbt
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from smc_engine import SMCEngine, resample_to_htf, get_htf_bias

# =============================================================================
# DATA FETCHING
# =============================================================================
def fetch_data_yfinance(symbol: str, start: str, end: str, interval: str = '1h') -> pd.DataFrame:
    """Fetch data from Yahoo Finance"""
    import yfinance as yf
    
    # Map symbols
    yf_symbols = {
        'EURUSD': 'EURUSD=X',
        'GBPUSD': 'GBPUSD=X', 
        'USDJPY': 'USDJPY=X',
        'BTCUSD': 'BTC-USD',
        'XAUUSD': 'GC=F',  # Gold futures
        'GOLD': 'GC=F',
    }
    
    yf_symbol = yf_symbols.get(symbol, symbol)
    
    print(f"Fetching {symbol} ({yf_symbol})...")
    df = yf.download(yf_symbol, start=start, end=end, interval=interval, progress=False)
    
    if df.empty:
        raise ValueError(f"No data for {symbol}")
    
    # Standardize columns
    df.columns = [c.lower() for c in df.columns]
    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df.dropna(inplace=True)
    
    print(f"  Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    return df


def fetch_data_mt5(symbol: str, timeframe: str = 'H1', bars: int = 50000) -> pd.DataFrame:
    """Fetch data from MT5"""
    try:
        import MetaTrader5 as mt5
        
        if not mt5.initialize():
            raise Exception("MT5 not initialized")
        
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }
        
        tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        
        if rates is None or len(rates) == 0:
            raise ValueError(f"No data for {symbol}")
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        mt5.shutdown()
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    except Exception as e:
        print(f"MT5 error: {e}, falling back to yfinance")
        return None


# =============================================================================
# VECTORBT BACKTESTER
# =============================================================================
def backtest_smc(
    df: pd.DataFrame,
    symbol: str,
    engine: SMCEngine,
    init_cash: float = 10000,
    size_pct: float = 0.02,  # 2% per trade
    fees: float = 0.0001,    # 0.01% commission
) -> dict:
    """
    Backtest SMC strategy with VectorBT
    
    Returns dict with performance metrics
    """
    # Generate signals
    signals = engine.generate_signals(df)
    
    # Extract entries
    entries_long = signals['entry_long'].values
    entries_short = signals['entry_short'].values
    
    # Count signals
    n_long_signals = entries_long.sum()
    n_short_signals = entries_short.sum()
    
    if n_long_signals + n_short_signals == 0:
        return {
            'symbol': symbol,
            'total_trades': 0,
            'net_profit': 0,
            'pf': 0,
            'win_rate': 0,
            'max_dd': 0,
            'sharpe': 0,
            'long_trades': 0,
            'short_trades': 0,
            'error': 'No signals generated'
        }
    
    # Get SL/TP levels
    sl_long = signals['sl_long'].values
    tp_long = signals['tp_long'].values
    sl_short = signals['sl_short'].values
    tp_short = signals['tp_short'].values
    
    close = signals['close'].values
    
    # Simple backtest simulation (VectorBT style)
    # For now, simulate without actual VBT to keep it simple
    
    trades = []
    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0
    entry_sl = 0
    entry_tp = 0
    entry_idx = 0
    
    for i in range(1, len(close)):
        # Check exit first
        if position == 1:  # Long position
            if close[i] <= entry_sl:  # SL hit
                pnl = entry_sl - entry_price
                trades.append({'type': 'long', 'entry': entry_price, 'exit': entry_sl, 
                              'pnl': pnl, 'bars': i - entry_idx, 'result': 'sl'})
                position = 0
            elif close[i] >= entry_tp:  # TP hit
                pnl = entry_tp - entry_price
                trades.append({'type': 'long', 'entry': entry_price, 'exit': entry_tp,
                              'pnl': pnl, 'bars': i - entry_idx, 'result': 'tp'})
                position = 0
        
        elif position == -1:  # Short position
            if close[i] >= entry_sl:  # SL hit
                pnl = entry_price - entry_sl
                trades.append({'type': 'short', 'entry': entry_price, 'exit': entry_sl,
                              'pnl': pnl, 'bars': i - entry_idx, 'result': 'sl'})
                position = 0
            elif close[i] <= entry_tp:  # TP hit
                pnl = entry_price - entry_tp
                trades.append({'type': 'short', 'entry': entry_price, 'exit': entry_tp,
                              'pnl': pnl, 'bars': i - entry_idx, 'result': 'tp'})
                position = 0
        
        # Check entry
        if position == 0:
            if entries_long[i] and not np.isnan(sl_long[i]) and not np.isnan(tp_long[i]):
                position = 1
                entry_price = close[i]
                entry_sl = sl_long[i]
                entry_tp = tp_long[i]
                entry_idx = i
            elif entries_short[i] and not np.isnan(sl_short[i]) and not np.isnan(tp_short[i]):
                position = -1
                entry_price = close[i]
                entry_sl = sl_short[i]
                entry_tp = tp_short[i]
                entry_idx = i
    
    # Calculate metrics
    if len(trades) == 0:
        return {
            'symbol': symbol,
            'total_trades': 0,
            'net_profit': 0,
            'pf': 0,
            'win_rate': 0,
            'max_dd': 0,
            'sharpe': 0,
            'long_trades': n_long_signals,
            'short_trades': n_short_signals,
            'error': 'No completed trades'
        }
    
    trades_df = pd.DataFrame(trades)
    
    total_trades = len(trades_df)
    long_trades = len(trades_df[trades_df['type'] == 'long'])
    short_trades = len(trades_df[trades_df['type'] == 'short'])
    
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] < 0]
    
    gross_profit = wins['pnl'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
    net_profit = gross_profit - gross_loss
    
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    
    # Equity curve for DD calculation
    equity = [init_cash]
    for t in trades:
        # Normalize PnL to account size
        trade_pnl = (t['pnl'] / t['entry']) * init_cash * size_pct
        equity.append(equity[-1] + trade_pnl)
    
    equity = np.array(equity)
    running_max = np.maximum.accumulate(equity)
    drawdown = (running_max - equity) / running_max * 100
    max_dd = drawdown.max()
    
    # Sharpe (simplified)
    returns = np.diff(equity) / equity[:-1]
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    
    # Average trade metrics
    avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_loss = abs(losses['pnl'].mean()) if len(losses) > 0 else 0
    avg_rr = avg_win / avg_loss if avg_loss > 0 else 0
    
    return {
        'symbol': symbol,
        'total_trades': total_trades,
        'long_trades': long_trades,
        'short_trades': short_trades,
        'win_rate': round(win_rate, 2),
        'pf': round(pf, 2),
        'net_profit': round(net_profit, 2),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),
        'max_dd': round(max_dd, 2),
        'sharpe': round(sharpe, 2),
        'avg_win': round(avg_win, 4),
        'avg_loss': round(avg_loss, 4),
        'avg_rr': round(avg_rr, 2),
        'bars': len(df),
        'signals_long': n_long_signals,
        'signals_short': n_short_signals,
    }


# =============================================================================
# MULTI-ASSET TEST
# =============================================================================
def run_multi_asset_test(
    symbols: list = ['EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'XAUUSD'],
    start_date: str = '2023-01-01',
    end_date: str = '2024-12-31',
    timeframe: str = '1h',
    engine_params: dict = None,
) -> pd.DataFrame:
    """
    Run SMC backtest across multiple assets
    
    Returns DataFrame with results for each asset
    """
    if engine_params is None:
        engine_params = {
            'ltf_swing_len': 5,
            'use_ob': True,
            'ob_min_atr': 0.3,
            'use_fvg': True,
            'fvg_min_atr': 0.5,
            'use_pd_zone': True,
            'premium_level': 0.70,
            'discount_level': 0.30,
            'rr_ratio': 2.0,
        }
    
    engine = SMCEngine(**engine_params)
    results = []
    
    print("=" * 60)
    print("SMC MULTI-ASSET BACKTEST")
    print("=" * 60)
    print(f"Period: {start_date} to {end_date}")
    print(f"Timeframe: {timeframe}")
    print(f"Symbols: {', '.join(symbols)}")
    print("=" * 60)
    
    for symbol in symbols:
        try:
            # Try MT5 first, then yfinance
            df = fetch_data_mt5(symbol, timeframe.upper())
            if df is None:
                df = fetch_data_yfinance(symbol, start_date, end_date, timeframe)
            
            if df is not None and len(df) > 100:
                result = backtest_smc(df, symbol, engine)
                results.append(result)
                
                print(f"\n{symbol}:")
                print(f"  Trades: {result['total_trades']} (L:{result['long_trades']}, S:{result['short_trades']})")
                print(f"  Win Rate: {result['win_rate']}%")
                print(f"  PF: {result['pf']}")
                print(f"  Max DD: {result['max_dd']}%")
            else:
                print(f"\n{symbol}: Insufficient data")
                results.append({'symbol': symbol, 'error': 'Insufficient data'})
                
        except Exception as e:
            print(f"\n{symbol}: Error - {str(e)}")
            results.append({'symbol': symbol, 'error': str(e)})
    
    results_df = pd.DataFrame(results)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    valid_results = results_df[results_df['total_trades'] > 0]
    if len(valid_results) > 0:
        print(f"\nValid backtests: {len(valid_results)}/{len(symbols)}")
        print(f"Total trades: {valid_results['total_trades'].sum()}")
        print(f"Avg Win Rate: {valid_results['win_rate'].mean():.2f}%")
        print(f"Avg PF: {valid_results['pf'].mean():.2f}")
        print(f"Avg Max DD: {valid_results['max_dd'].mean():.2f}%")
        
        # Best performers
        if len(valid_results) > 1:
            best_pf = valid_results.loc[valid_results['pf'].idxmax()]
            print(f"\nBest PF: {best_pf['symbol']} (PF={best_pf['pf']})")
    
    return results_df


# =============================================================================
# PARAMETER OPTIMIZATION
# =============================================================================
def optimize_parameters(
    df: pd.DataFrame,
    symbol: str,
    param_grid: dict = None,
) -> pd.DataFrame:
    """
    Grid search for best SMC parameters
    """
    if param_grid is None:
        param_grid = {
            'ltf_swing_len': [3, 5, 7],
            'use_ob': [True, False],
            'use_fvg': [True, False],
            'use_pd_zone': [True, False],
            'rr_ratio': [1.5, 2.0, 2.5, 3.0],
        }
    
    results = []
    
    # Generate all combinations
    from itertools import product
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    total_combos = 1
    for v in values:
        total_combos *= len(v)
    
    print(f"Testing {total_combos} parameter combinations...")
    
    for combo in product(*values):
        params = dict(zip(keys, combo))
        
        # Skip invalid combinations
        if not params.get('use_ob', True) and not params.get('use_fvg', True):
            # Need at least one entry method
            continue
        
        engine = SMCEngine(**params)
        result = backtest_smc(df, symbol, engine)
        result.update(params)
        results.append(result)
    
    results_df = pd.DataFrame(results)
    
    # Sort by PF
    if 'pf' in results_df.columns:
        results_df = results_df.sort_values('pf', ascending=False)
    
    return results_df


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    # Run multi-asset test
    results = run_multi_asset_test(
        symbols=['EURUSD', 'GBPUSD', 'BTCUSD'],
        start_date='2023-01-01',
        end_date='2024-12-31',
        timeframe='1h',
    )
    
    # Save results
    results.to_csv('smc_multi_asset_results.csv', index=False)
    print("\nResults saved to smc_multi_asset_results.csv")
