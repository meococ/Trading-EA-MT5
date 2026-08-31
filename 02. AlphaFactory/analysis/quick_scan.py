#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Strategy Scanner using VectorBT
======================================
Rapid validation of strategy ideas before MT5 implementation.

Usage:
  python quick_scan.py --strategy "SMA crossover" --symbol XAUUSD --timeframe 1H
  python quick_scan.py --custom custom_strategy.py
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add vectorbt to path
VECTORBT_PATH = Path(__file__).parent.parent.parent / "01. vectorbt"
if VECTORBT_PATH.exists():
    sys.path.insert(0, str(VECTORBT_PATH))

try:
    import vectorbt as vbt
    import numpy as np
    import pandas as pd
    HAS_VBT = True
except ImportError as e:
    HAS_VBT = False
    VBT_ERROR = str(e)


# ============================================================
# PRE-DEFINED STRATEGIES
# ============================================================

def sma_crossover(price: pd.Series, fast: int = 10, slow: int = 50) -> tuple:
    """Simple Moving Average Crossover"""
    fast_ma = vbt.MA.run(price, fast)
    slow_ma = vbt.MA.run(price, slow)
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    return entries, exits


def ema_crossover(price: pd.Series, fast: int = 12, slow: int = 26) -> tuple:
    """Exponential Moving Average Crossover"""
    fast_ema = vbt.MA.run(price, fast, ewm=True)
    slow_ema = vbt.MA.run(price, slow, ewm=True)
    entries = fast_ema.ma_crossed_above(slow_ema)
    exits = fast_ema.ma_crossed_below(slow_ema)
    return entries, exits


def rsi_oversold(price: pd.Series, period: int = 14, oversold: int = 30, overbought: int = 70) -> tuple:
    """RSI Mean Reversion"""
    rsi = vbt.RSI.run(price, period)
    entries = rsi.rsi_crossed_below(oversold)
    exits = rsi.rsi_crossed_above(overbought)
    return entries, exits


def bollinger_breakout(price: pd.Series, period: int = 20, std: float = 2.0) -> tuple:
    """Bollinger Bands Breakout"""
    bb = vbt.BBANDS.run(price, period, std)
    entries = price > bb.upper
    exits = price < bb.middle
    return entries, exits


def macd_crossover(price: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """MACD Histogram Crossover"""
    macd = vbt.MACD.run(price, fast, slow, signal)
    entries = macd.macd_crossed_above(macd.signal)
    exits = macd.macd_crossed_below(macd.signal)
    return entries, exits


STRATEGIES = {
    "sma": sma_crossover,
    "ema": ema_crossover,
    "rsi": rsi_oversold,
    "bollinger": bollinger_breakout,
    "macd": macd_crossover,
}


# ============================================================
# PARAMETER OPTIMIZATION
# ============================================================

def optimize_sma(price: pd.Series) -> dict:
    """Grid search for best SMA parameters"""
    windows = np.arange(5, 101, 5)
    fast_ma, slow_ma = vbt.MA.run_combs(price, window=windows, r=2, short_names=['fast', 'slow'])
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    
    pf = vbt.Portfolio.from_signals(price, entries, exits, init_cash=10000, fees=0.0001)
    
    # Find best combination
    returns = pf.total_return()
    best_idx = returns.idxmax()
    best_pf = pf[best_idx]
    
    return {
        "best_params": {"fast": best_idx[0], "slow": best_idx[1]},
        "total_return": float(returns.max()),
        "sharpe": float(best_pf.sharpe_ratio()),
        "max_dd": float(best_pf.max_drawdown()),
        "trades": int(best_pf.trades.count()),
    }


# ============================================================
# MAIN SCANNER
# ============================================================

def download_data(symbol: str, timeframe: str = "1h", days: int = 365) -> pd.Series:
	"""Load price data, prefer local CSV, fallback to Yahoo Finance.

	Priority:
	1. Local CSV (02. AlphaFactory/data or 01. vectorbt/data)
	2. Yahoo Finance download (current behaviour)
	"""
	# --- 1) Try local CSV first ---
	# Map VectorBT timeframe -> MT5/CSV timeframe suffix
	tf_map = {
	    "1h": "H1",
	    "4h": "H4",
	    "1d": "D1",
	}
	mtf = tf_map.get(timeframe.lower())
	if mtf is not None:
	    fname = f"{symbol.upper()}_{mtf}.csv"
	    # AlphaFactory-local data folder
	    alpha_data_root = Path(__file__).parent.parent / "data"
	    vbt_data_root = VECTORBT_PATH / "data"
	    candidates = [
	        alpha_data_root / fname,
	        vbt_data_root / fname,
	    ]
	    for path in candidates:
	        if path.is_file():
	            print(f"Using local data: {path}")
	            df = pd.read_csv(path, index_col=0, parse_dates=True)
	            if 'Close' in df.columns:
	                return df['Close']
	            # Fallback: try typical MT5 export column names
	            close_col = None
	            for col in ['close', 'Close', 'CLOSE']:
	                if col in df.columns:
	                    close_col = col
	                    break
	            if close_col is not None:
	                return df[close_col]

	# --- 2) Fallback to Yahoo Finance ---
	# Map symbol to YF ticker
	yf_map = {
	    "XAUUSD": "GC=F",      # Gold futures
	    "EURUSD": "EURUSD=X",
	    "GBPUSD": "GBPUSD=X",
	    "USDJPY": "USDJPY=X",
	    "BTCUSD": "BTC-USD",
	    "ETHUSD": "ETH-USD",
	    "SPX": "^GSPC",
	    "NDX": "^IXIC",
	}
	
	ticker = yf_map.get(symbol.upper(), symbol)
	
	# Calculate period
	end = datetime.now()
	start = end - timedelta(days=days)
	
	print(f"Downloading {ticker} data...")
	data = vbt.YFData.download(
	    ticker, 
	    start=start.strftime("%Y-%m-%d"),
	    end=end.strftime("%Y-%m-%d"),
	    interval=timeframe
	)
	
	return data.get('Close')


def run_scan(price: pd.Series, strategy_name: str, **kwargs) -> dict:
    """Run a strategy scan"""
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES.keys())}")
    
    strategy_fn = STRATEGIES[strategy_name]
    entries, exits = strategy_fn(price, **kwargs)
    
    # Run backtest
    pf = vbt.Portfolio.from_signals(
        price, entries, exits,
        init_cash=10000,
        fees=0.0001,  # 1 pip spread approx
        freq='1h'
    )
    
    # Extract metrics
    stats = pf.stats()
    trades = pf.trades.records_readable
    
    return {
        "strategy": strategy_name,
        "params": kwargs,
        "n_trades": int(pf.trades.count()),
        "win_rate": float(pf.trades.win_rate()) if pf.trades.count() > 0 else 0,
        "profit_factor": float(pf.trades.profit_factor()) if pf.trades.count() > 0 else 0,
        "total_return_pct": float(pf.total_return() * 100),
        "sharpe_ratio": float(pf.sharpe_ratio()) if not np.isnan(pf.sharpe_ratio()) else 0,
        "max_drawdown_pct": float(pf.max_drawdown() * 100),
        "avg_trade_duration": str(pf.trades.avg_duration()) if pf.trades.count() > 0 else "N/A",
        "expectancy": float(pf.trades.expectancy()) if pf.trades.count() > 0 else 0,
    }


def print_results(results: dict):
    """Pretty print scan results"""
    print("\n" + "=" * 60)
    print("QUICK SCAN RESULTS")
    print("=" * 60)
    print(f"Strategy: {results['strategy']}")
    print(f"Params:   {results['params']}")
    print("-" * 40)
    print(f"Trades:        {results['n_trades']}")
    print(f"Win Rate:      {results['win_rate']:.1%}")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Total Return:  {results['total_return_pct']:.1f}%")
    print(f"Sharpe Ratio:  {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:  {results['max_drawdown_pct']:.1f}%")
    print(f"Expectancy:    ${results['expectancy']:.2f}")
    print("-" * 40)
    
    # Quick verdict
    pf = results['profit_factor']
    if pf >= 1.5:
        verdict = "🟢 PROMISING - Worth implementing in MT5"
    elif pf >= 1.2:
        verdict = "🟡 MODERATE - May work with filters"
    elif pf >= 1.0:
        verdict = "🟠 MARGINAL - Needs significant improvement"
    else:
        verdict = "🔴 UNPROFITABLE - Do not proceed"
    
    print(f"\nVERDICT: {verdict}")
    print("\n⚠️  Note: VectorBT results typically degrade 30-50% in MT5")
    print("    Expect lower PF in real MT5 backtest.")
    print("=" * 60)


def main():
    if not HAS_VBT:
        print(f"ERROR: VectorBT not available: {VBT_ERROR}")
        print("Install with: pip install vectorbt")
        return 1
    
    parser = argparse.ArgumentParser(description="Quick Strategy Scanner")
    parser.add_argument("--strategy", "-s", default="sma", 
                       choices=list(STRATEGIES.keys()),
                       help="Strategy to test")
    parser.add_argument("--symbol", default="XAUUSD", help="Symbol to test")
    parser.add_argument("--timeframe", "-tf", default="1h", help="Timeframe (1h, 4h, 1d)")
    parser.add_argument("--days", type=int, default=365, help="Days of history")
    parser.add_argument("--optimize", action="store_true", help="Run parameter optimization")
    parser.add_argument("--all", action="store_true", help="Test all strategies")
    args = parser.parse_args()
    
    # Download data
    try:
        price = download_data(args.symbol, args.timeframe, args.days)
        print(f"Data: {len(price)} bars from {price.index[0]} to {price.index[-1]}")
    except Exception as e:
        print(f"ERROR downloading data: {e}")
        return 1
    
    if args.all:
        # Test all strategies
        print("\n🔍 Testing all strategies...")
        results = []
        for name in STRATEGIES.keys():
            try:
                r = run_scan(price, name)
                results.append(r)
                print(f"  {name}: PF={r['profit_factor']:.2f}, Trades={r['n_trades']}")
            except Exception as e:
                print(f"  {name}: ERROR - {e}")
        
        # Sort by PF
        results.sort(key=lambda x: x['profit_factor'], reverse=True)
        print("\n📊 RANKING:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['strategy']}: PF={r['profit_factor']:.2f}")
        
    elif args.optimize:
        print("\n🔧 Running optimization...")
        if args.strategy == "sma":
            opt = optimize_sma(price)
            print(f"Best params: {opt['best_params']}")
            print(f"Total return: {opt['total_return']:.1%}")
            print(f"Sharpe: {opt['sharpe']:.2f}")
        else:
            print("Optimization only available for SMA strategy currently")
    else:
        # Single strategy scan
        results = run_scan(price, args.strategy)
        print_results(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
