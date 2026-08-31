#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EA_Gold_IBS_Trend_Alpha - Python Proof-of-Concept
==================================================
Enhanced IBS Mean Reversion với Trend Filter cho XAUUSD H4

Logic:
1. Regime Filter: Close > SMA200 = Uptrend, Close < SMA200 = Downtrend
2. Entry: IBS < 0.2 (Long trong Uptrend), IBS > 0.8 (Short trong Downtrend)
3. Exit: Close > Previous High (Long), Close < Previous Low (Short)
4. Time Stop: Max 5 bars holding

Target: WinRate > 55%, PF > 1.3 (realistic, không ảo tưởng)

Usage:
  python ibs_trend_alpha.py --data "path/to/XAUUSD_H4.csv"
  python ibs_trend_alpha.py --download  # Download từ yfinance
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Config:
    """Strategy parameters - dễ dàng tune sau"""
    # Regime Filter
    sma_period: int = 200
    
    # IBS Trigger
    ibs_oversold: float = 0.2      # Long trigger
    ibs_overbought: float = 0.8   # Short trigger
    
    # Exit Rules
    max_holding_bars: int = 5     # Time-based hard stop
    
    # Risk Management
    atr_period: int = 20
    risk_per_trade: float = 0.02  # 2% risk
    
    # Filters
    min_atr_filter: float = 5.0   # Minimum ATR để trade (tránh market "ngủ")
    max_gap_atr_mult: float = 2.0 # Ignore if gap > 2*ATR


# ============================================================
# IBS CALCULATION
# ============================================================

def calculate_ibs(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """
    Internal Bar Strength (IBS)
    IBS = (Close - Low) / (High - Low)
    
    IBS < 0.2: Oversold (giá đóng cửa gần đáy)
    IBS > 0.8: Overbought (giá đóng cửa gần đỉnh)
    """
    range_hl = high - low
    # Tránh division by zero khi High = Low (doji)
    range_hl = range_hl.replace(0, np.nan)
    ibs = (close - low) / range_hl
    return ibs.fillna(0.5)  # Doji = neutral


def calculate_regime(close: pd.Series, sma_period: int = 200) -> pd.Series:
    """
    Regime Detection dựa trên SMA
    1 = Uptrend (Close > SMA)
    -1 = Downtrend (Close < SMA)
    0 = Neutral (Close = SMA)
    """
    sma = close.rolling(window=sma_period).mean()
    regime = np.where(close > sma, 1, np.where(close < sma, -1, 0))
    return pd.Series(regime, index=close.index)


# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_signals(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """
    Generate entry signals based on IBS + Regime Filter
    
    Long: Regime = 1 AND IBS < oversold
    Short: Regime = -1 AND IBS > overbought
    """
    df = df.copy()
    
    # Calculate indicators
    df['IBS'] = calculate_ibs(df['High'], df['Low'], df['Close'])
    df['SMA200'] = df['Close'].rolling(window=config.sma_period).mean()
    df['Regime'] = calculate_regime(df['Close'], config.sma_period)
    df['ATR'] = calculate_atr(df['High'], df['Low'], df['Close'], config.atr_period)
    
    # Previous High/Low for exit
    df['Prev_High'] = df['High'].shift(1)
    df['Prev_Low'] = df['Low'].shift(1)
    
    # Gap detection
    df['Gap'] = abs(df['Open'] - df['Close'].shift(1))
    df['Gap_Filter'] = df['Gap'] < (df['ATR'] * config.max_gap_atr_mult)
    
    # ATR Filter (tránh market quá yên tĩnh)
    df['ATR_Filter'] = df['ATR'] > config.min_atr_filter
    
    # Entry signals
    df['Long_Signal'] = (
        (df['Regime'] == 1) & 
        (df['IBS'] < config.ibs_oversold) &
        df['Gap_Filter'] &
        df['ATR_Filter']
    )
    
    df['Short_Signal'] = (
        (df['Regime'] == -1) & 
        (df['IBS'] > config.ibs_overbought) &
        df['Gap_Filter'] &
        df['ATR_Filter']
    )
    
    return df


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Average True Range"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


# ============================================================
# BACKTESTING ENGINE
# ============================================================

@dataclass
class Trade:
    """Single trade record"""
    entry_idx: int
    entry_time: datetime
    entry_price: float
    direction: int  # 1 = Long, -1 = Short
    exit_idx: Optional[int] = None
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl: float = 0.0
    bars_held: int = 0


def run_backtest(df: pd.DataFrame, config: Config, long_only: bool = False) -> Tuple[List[Trade], pd.DataFrame]:
    """
    Run backtest với IBS Trend Alpha logic
    
    Exit Rules:
    1. Long: Close > Previous High
    2. Short: Close < Previous Low  
    3. Time stop: Max 5 bars
    """
    trades: List[Trade] = []
    df = df.copy()
    
    position = 0  # 0 = flat, 1 = long, -1 = short
    current_trade: Optional[Trade] = None
    
    for i in range(config.sma_period + 1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # Skip if NaN
        if pd.isna(row['IBS']) or pd.isna(row['ATR']):
            continue
        
        # Check exit first (if in position)
        if position != 0 and current_trade is not None:
            bars_held = i - current_trade.entry_idx
            exit_triggered = False
            exit_reason = ""
            
            if position == 1:  # Long position
                # Exit: Close > Previous High
                if row['Close'] > prev_row['High']:
                    exit_triggered = True
                    exit_reason = "Target Hit"
            else:  # Short position
                # Exit: Close < Previous Low
                if row['Close'] < prev_row['Low']:
                    exit_triggered = True
                    exit_reason = "Target Hit"
            
            # Time stop
            if bars_held >= config.max_holding_bars:
                exit_triggered = True
                exit_reason = "Time Stop"
            
            if exit_triggered:
                current_trade.exit_idx = i
                current_trade.exit_time = row.name
                current_trade.exit_price = row['Close']
                current_trade.exit_reason = exit_reason
                current_trade.bars_held = bars_held
                
                # Calculate PnL (in points)
                if position == 1:
                    current_trade.pnl = current_trade.exit_price - current_trade.entry_price
                else:
                    current_trade.pnl = current_trade.entry_price - current_trade.exit_price
                
                trades.append(current_trade)
                position = 0
                current_trade = None
        
        # Check entry (if flat)
        if position == 0:
            if row['Long_Signal']:
                position = 1
                current_trade = Trade(
                    entry_idx=i,
                    entry_time=row.name,
                    entry_price=row['Close'],
                    direction=1
                )
            elif row['Short_Signal'] and not long_only:
                position = -1
                current_trade = Trade(
                    entry_idx=i,
                    entry_time=row.name,
                    entry_price=row['Close'],
                    direction=-1
                )
    
    # Close any open position at end
    if current_trade is not None:
        current_trade.exit_idx = len(df) - 1
        current_trade.exit_time = df.iloc[-1].name
        current_trade.exit_price = df.iloc[-1]['Close']
        current_trade.exit_reason = "End of Data"
        current_trade.bars_held = current_trade.exit_idx - current_trade.entry_idx
        if position == 1:
            current_trade.pnl = current_trade.exit_price - current_trade.entry_price
        else:
            current_trade.pnl = current_trade.entry_price - current_trade.exit_price
        trades.append(current_trade)
    
    return trades, df


# ============================================================
# STATISTICS
# ============================================================

def calculate_stats(trades: List[Trade]) -> dict:
    """Calculate performance statistics"""
    if not trades:
        return {"error": "No trades"}
    
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    total_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    
    win_rate = win_count / total_trades if total_trades > 0 else 0
    
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    avg_win = np.mean(wins) if wins else 0
    avg_loss = abs(np.mean(losses)) if losses else 0
    
    # Expectancy
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    # Risk/Reward
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
    
    # Max consecutive losses (quan trọng cho tâm lý)
    max_consec_loss = 0
    consec_loss = 0
    for p in pnls:
        if p < 0:
            consec_loss += 1
            max_consec_loss = max(max_consec_loss, consec_loss)
        else:
            consec_loss = 0
    
    # Breakdown by direction
    long_trades = [t for t in trades if t.direction == 1]
    short_trades = [t for t in trades if t.direction == -1]
    long_pnl = sum(t.pnl for t in long_trades)
    short_pnl = sum(t.pnl for t in short_trades)
    
    # Breakdown by exit reason
    exit_reasons = {}
    for t in trades:
        reason = t.exit_reason
        if reason not in exit_reasons:
            exit_reasons[reason] = {"count": 0, "pnl": 0}
        exit_reasons[reason]["count"] += 1
        exit_reasons[reason]["pnl"] += t.pnl
    
    # Avg bars held
    avg_bars = np.mean([t.bars_held for t in trades])
    
    return {
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate * 100, 1),
        "profit_factor": round(profit_factor, 2),
        "total_pnl": round(sum(pnls), 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "rr_ratio": round(rr_ratio, 2),
        "max_consec_losses": max_consec_loss,
        "avg_bars_held": round(avg_bars, 1),
        "long_trades": len(long_trades),
        "short_trades": len(short_trades),
        "long_pnl": round(long_pnl, 2),
        "short_pnl": round(short_pnl, 2),
        "exit_breakdown": exit_reasons,
    }


# ============================================================
# DATA LOADING
# ============================================================

def load_data(filepath: str) -> pd.DataFrame:
    """Load OHLCV data from CSV"""
    df = pd.read_csv(filepath, parse_dates=['time'] if 'time' in pd.read_csv(filepath, nrows=1).columns else [0])
    
    # Standardize column names
    col_map = {
        'time': 'Time', 'Time': 'Time', 'datetime': 'Time', 'date': 'Time',
        'open': 'Open', 'Open': 'Open',
        'high': 'High', 'High': 'High',
        'low': 'Low', 'Low': 'Low',
        'close': 'Close', 'Close': 'Close',
        'volume': 'Volume', 'Volume': 'Volume', 'tick_volume': 'Volume',
    }
    
    df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})
    
    if 'Time' in df.columns:
        df.set_index('Time', inplace=True)
    
    return df


def download_data(symbol: str = "GC=F", period: str = "5y", interval: str = "4h") -> pd.DataFrame:
    """Download data từ Yahoo Finance (Gold Futures)"""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance")
        return pd.DataFrame()
    
    print(f"Downloading {symbol} {interval} data...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    
    if df.empty:
        print("WARNING: No data from yfinance. Trying alternative...")
        # Try với period shorter (yfinance có giới hạn cho intraday)
        df = ticker.history(period="2y", interval="1h")
        if not df.empty:
            # Resample to H4
            df = df.resample('4h').agg({
                'Open': 'first',
                'High': 'max', 
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
    
    return df


# ============================================================
# MAIN
# ============================================================

def print_results(stats: dict, config: Config):
    """Pretty print results"""
    print("\n" + "=" * 70)
    print("  EA_GOLD_IBS_TREND_ALPHA - BACKTEST RESULTS")
    print("=" * 70)
    
    print(f"\n📊 CONFIGURATION:")
    print(f"   SMA Period:      {config.sma_period}")
    print(f"   IBS Oversold:    {config.ibs_oversold}")
    print(f"   IBS Overbought:  {config.ibs_overbought}")
    print(f"   Max Hold Bars:   {config.max_holding_bars}")
    
    print(f"\n📈 PERFORMANCE:")
    print(f"   Total Trades:    {stats['total_trades']}")
    print(f"   Win Rate:        {stats['win_rate']}%")
    print(f"   Profit Factor:   {stats['profit_factor']}")
    print(f"   Total PnL:       {stats['total_pnl']} points")
    print(f"   Expectancy:      {stats['expectancy']} points/trade")
    
    print(f"\n💰 TRADE ANALYSIS:")
    print(f"   Avg Win:         {stats['avg_win']} points")
    print(f"   Avg Loss:        {stats['avg_loss']} points")
    print(f"   R:R Ratio:       {stats['rr_ratio']}")
    print(f"   Max Consec Loss: {stats['max_consec_losses']}")
    print(f"   Avg Bars Held:   {stats['avg_bars_held']}")
    
    print(f"\n📊 DIRECTION BREAKDOWN:")
    print(f"   Long Trades:     {stats['long_trades']} ({stats['long_pnl']} pts)")
    print(f"   Short Trades:    {stats['short_trades']} ({stats['short_pnl']} pts)")
    
    print(f"\n🚪 EXIT BREAKDOWN:")
    for reason, data in stats['exit_breakdown'].items():
        print(f"   {reason}: {data['count']} trades ({data['pnl']:.1f} pts)")
    
    # Verdict
    print("\n" + "-" * 70)
    pf = stats['profit_factor']
    wr = stats['win_rate']
    
    if pf >= 1.5 and wr >= 55:
        verdict = "🟢 PROMISING - Proceed to MT5 backtest"
    elif pf >= 1.3 and wr >= 50:
        verdict = "🟡 MODERATE - May work, test MT5 early"
    elif pf >= 1.1:
        verdict = "🟠 MARGINAL - Needs improvement"
    else:
        verdict = "🔴 FAIL - No edge detected"
    
    print(f"   VERDICT: {verdict}")
    print(f"\n⚠️  REMINDER: Expect 30-50% degradation in MT5!")
    print(f"   If PF={pf} here → Expect PF {pf*0.6:.2f}-{pf*0.8:.2f} in MT5")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="EA_Gold_IBS_Trend_Alpha Backtest")
    parser.add_argument("--data", "-d", help="Path to OHLCV CSV file")
    parser.add_argument("--download", action="store_true", help="Download data from yfinance")
    parser.add_argument("--sma", type=int, default=200, help="SMA period for trend filter")
    parser.add_argument("--ibs-low", type=float, default=0.2, help="IBS oversold threshold")
    parser.add_argument("--ibs-high", type=float, default=0.8, help="IBS overbought threshold")
    parser.add_argument("--max-bars", type=int, default=5, help="Max holding bars")
    parser.add_argument("--long-only", action="store_true", help="Only take long trades")
    parser.add_argument("--output", "-o", help="Output trades to CSV")
    args = parser.parse_args()
    
    # Load data
    if args.download:
        df = download_data()
    elif args.data:
        df = load_data(args.data)
    else:
        # Try default path
        default_path = Path(__file__).parent.parent.parent / "01. vectorbt" / "data" / "XAUUSD_H4.csv"
        if default_path.exists():
            df = load_data(str(default_path))
        else:
            print("ERROR: No data source specified.")
            print("Use --data <path> or --download")
            return 1
    
    if df.empty:
        print("ERROR: No data loaded")
        return 1
    
    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Configure
    config = Config(
        sma_period=args.sma,
        ibs_oversold=args.ibs_low,
        ibs_overbought=args.ibs_high,
        max_holding_bars=args.max_bars,
    )
    
    # Long-only mode
    long_only = args.long_only
    
    # Generate signals
    df = generate_signals(df, config)
    
    # Run backtest
    trades, df = run_backtest(df, config, long_only)
    
    if not trades:
        print("ERROR: No trades generated. Check data and parameters.")
        return 1
    
    # Calculate stats
    stats = calculate_stats(trades)
    
    # Print results
    print_results(stats, config)
    
    # Export if requested
    if args.output:
        trades_df = pd.DataFrame([{
            'Entry Time': t.entry_time,
            'Exit Time': t.exit_time,
            'Direction': 'Long' if t.direction == 1 else 'Short',
            'Entry Price': t.entry_price,
            'Exit Price': t.exit_price,
            'PnL': t.pnl,
            'Bars Held': t.bars_held,
            'Exit Reason': t.exit_reason,
        } for t in trades])
        trades_df.to_csv(args.output, index=False)
        print(f"\n✅ Trades exported to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
