#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
London Session Breakout Strategy - Python Proof-of-Concept
============================================================
Khai thác institutional flow vào London session.

Logic:
1. Calculate Asian session range (00:00-07:59 UTC)
2. Wait for London open (08:00 UTC)
3. Entry: Break of Asian High/Low trong 2-4h đầu London
4. Exit: End of NY overlap (16:00 UTC) hoặc R:R target
5. Filter: Minimum Asian range (avoid low volatility)

Edge Source:
- Institutional flow khi London market mở
- Asian range acts as natural S/R levels
- Time-based exit avoids overnight risk

Usage:
  python london_breakout.py --data "path/to/XAUUSD_H1.csv"
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class LondonConfig:
    """Strategy parameters"""
    # Session times (UTC)
    asian_start: int = 0      # 00:00 UTC
    asian_end: int = 8        # 08:00 UTC (London open)
    london_start: int = 8     # 08:00 UTC
    entry_window: int = 4     # Entry allowed until 12:00 UTC
    exit_hour: int = 16       # Force exit at 16:00 UTC (NY afternoon)
    
    # Entry rules
    breakout_buffer_pct: float = 0.0  # % buffer above/below range
    min_range_atr_mult: float = 0.5   # Min Asian range as ATR multiple
    max_range_atr_mult: float = 3.0   # Max Asian range (avoid news days)
    
    # Exit rules  
    rr_target: float = 1.5    # Risk:Reward target
    use_time_exit: bool = True
    
    # Risk
    atr_period: int = 20
    risk_pct: float = 0.02
    
    # Filters
    long_only: bool = False
    short_only: bool = False


# ============================================================
# CORE FUNCTIONS
# ============================================================

@dataclass
class Trade:
    """Single trade record"""
    entry_date: datetime
    entry_time: datetime
    entry_price: float
    direction: int  # 1 = Long, -1 = Short
    stop_loss: float
    take_profit: float
    asian_high: float
    asian_low: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl: float = 0.0


def calculate_atr(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate ATR"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def get_asian_range(df: pd.DataFrame, date: datetime, config: LondonConfig) -> Tuple[float, float, float]:
    """
    Get Asian session High/Low for a given date.
    Returns: (asian_high, asian_low, asian_range)
    """
    # Filter bars for Asian session of this date
    asian_bars = df[
        (df.index.date == date.date()) &
        (df.index.hour >= config.asian_start) &
        (df.index.hour < config.asian_end)
    ]
    
    if asian_bars.empty:
        return None, None, None
    
    asian_high = asian_bars['High'].max()
    asian_low = asian_bars['Low'].min()
    asian_range = asian_high - asian_low
    
    return asian_high, asian_low, asian_range


def run_backtest(df: pd.DataFrame, config: LondonConfig) -> List[Trade]:
    """
    Run London Breakout backtest.
    
    Requires H1 or smaller timeframe data with proper datetime index.
    """
    trades: List[Trade] = []
    
    # Add ATR
    df = df.copy()
    df['ATR'] = calculate_atr(df, config.atr_period)
    
    # Get unique dates
    dates = df.index.normalize().unique()
    
    position = 0  # 0 = flat, 1 = long, -1 = short
    current_trade: Optional[Trade] = None
    
    for date in dates:
        # Get Asian range for this day
        asian_high, asian_low, asian_range = get_asian_range(df, date, config)
        
        if asian_high is None:
            continue
        
        # Get ATR at London open
        london_open_time = pd.Timestamp(date).replace(hour=config.london_start)
        atr_at_open = df.loc[:london_open_time, 'ATR'].iloc[-1] if london_open_time in df.index or len(df.loc[:london_open_time]) > 0 else None
        
        if atr_at_open is None or pd.isna(atr_at_open):
            continue
        
        # Filter: Check range size
        if asian_range < atr_at_open * config.min_range_atr_mult:
            continue  # Range too small
        if asian_range > atr_at_open * config.max_range_atr_mult:
            continue  # Range too big (news day)
        
        # Get London session bars
        london_bars = df[
            (df.index.date == date.date()) &
            (df.index.hour >= config.london_start) &
            (df.index.hour < config.exit_hour)
        ]
        
        if london_bars.empty:
            continue
        
        # Process each London bar
        for idx, row in london_bars.iterrows():
            hour = idx.hour
            
            # Check exit first
            if position != 0 and current_trade is not None:
                exit_triggered = False
                exit_reason = ""
                exit_price = 0
                
                # Time exit
                if config.use_time_exit and hour >= config.exit_hour:
                    exit_triggered = True
                    exit_reason = "Time Exit"
                    exit_price = row['Close']
                
                # R:R Target
                if position == 1:  # Long
                    if row['High'] >= current_trade.take_profit:
                        exit_triggered = True
                        exit_reason = "TP Hit"
                        exit_price = current_trade.take_profit
                    elif row['Low'] <= current_trade.stop_loss:
                        exit_triggered = True
                        exit_reason = "SL Hit"
                        exit_price = current_trade.stop_loss
                else:  # Short
                    if row['Low'] <= current_trade.take_profit:
                        exit_triggered = True
                        exit_reason = "TP Hit"
                        exit_price = current_trade.take_profit
                    elif row['High'] >= current_trade.stop_loss:
                        exit_triggered = True
                        exit_reason = "SL Hit"
                        exit_price = current_trade.stop_loss
                
                if exit_triggered:
                    current_trade.exit_time = idx
                    current_trade.exit_price = exit_price
                    current_trade.exit_reason = exit_reason
                    
                    if position == 1:
                        current_trade.pnl = exit_price - current_trade.entry_price
                    else:
                        current_trade.pnl = current_trade.entry_price - exit_price
                    
                    trades.append(current_trade)
                    position = 0
                    current_trade = None
            
            # Check entry (only during entry window)
            if position == 0 and hour < config.london_start + config.entry_window:
                buffer = asian_range * config.breakout_buffer_pct
                
                # Long breakout
                if not config.short_only and row['High'] > asian_high + buffer:
                    entry_price = asian_high + buffer
                    sl = asian_low
                    risk = entry_price - sl
                    tp = entry_price + (risk * config.rr_target)
                    
                    position = 1
                    current_trade = Trade(
                        entry_date=date,
                        entry_time=idx,
                        entry_price=entry_price,
                        direction=1,
                        stop_loss=sl,
                        take_profit=tp,
                        asian_high=asian_high,
                        asian_low=asian_low,
                    )
                
                # Short breakout
                elif not config.long_only and row['Low'] < asian_low - buffer:
                    entry_price = asian_low - buffer
                    sl = asian_high
                    risk = sl - entry_price
                    tp = entry_price - (risk * config.rr_target)
                    
                    position = -1
                    current_trade = Trade(
                        entry_date=date,
                        entry_time=idx,
                        entry_price=entry_price,
                        direction=-1,
                        stop_loss=sl,
                        take_profit=tp,
                        asian_high=asian_high,
                        asian_low=asian_low,
                    )
        
        # Force close at end of day if still in position
        if position != 0 and current_trade is not None:
            last_bar = london_bars.iloc[-1]
            current_trade.exit_time = london_bars.index[-1]
            current_trade.exit_price = last_bar['Close']
            current_trade.exit_reason = "EOD Exit"
            
            if position == 1:
                current_trade.pnl = last_bar['Close'] - current_trade.entry_price
            else:
                current_trade.pnl = current_trade.entry_price - last_bar['Close']
            
            trades.append(current_trade)
            position = 0
            current_trade = None
    
    return trades


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
    
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
    
    # Max consecutive losses
    max_consec_loss = 0
    consec_loss = 0
    for p in pnls:
        if p < 0:
            consec_loss += 1
            max_consec_loss = max(max_consec_loss, consec_loss)
        else:
            consec_loss = 0
    
    # Direction breakdown
    long_trades = [t for t in trades if t.direction == 1]
    short_trades = [t for t in trades if t.direction == -1]
    
    # Exit breakdown
    exit_reasons = {}
    for t in trades:
        reason = t.exit_reason
        if reason not in exit_reasons:
            exit_reasons[reason] = {"count": 0, "pnl": 0}
        exit_reasons[reason]["count"] += 1
        exit_reasons[reason]["pnl"] += t.pnl
    
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
        "long_trades": len(long_trades),
        "long_pnl": round(sum(t.pnl for t in long_trades), 2),
        "short_trades": len(short_trades),
        "short_pnl": round(sum(t.pnl for t in short_trades), 2),
        "exit_breakdown": exit_reasons,
    }


def load_data(filepath: str) -> pd.DataFrame:
    """Load OHLCV data with datetime index"""
    df = pd.read_csv(filepath)
    
    # Find datetime column
    time_cols = ['time', 'Time', 'datetime', 'date', 'Date']
    time_col = None
    for col in time_cols:
        if col in df.columns:
            time_col = col
            break
    
    if time_col is None:
        # Assume first column is datetime
        time_col = df.columns[0]
    
    df[time_col] = pd.to_datetime(df[time_col])
    df.set_index(time_col, inplace=True)
    
    # Standardize column names
    col_map = {
        'open': 'Open', 'Open': 'Open',
        'high': 'High', 'High': 'High',
        'low': 'Low', 'Low': 'Low',
        'close': 'Close', 'Close': 'Close',
    }
    df = df.rename(columns={c: col_map.get(c, c) for c in df.columns})
    
    return df


def print_results(stats: dict, config: LondonConfig):
    """Pretty print results"""
    print("\n" + "=" * 70)
    print("  LONDON BREAKOUT STRATEGY - BACKTEST RESULTS")
    print("=" * 70)
    
    print(f"\n📊 CONFIGURATION:")
    print(f"   Asian Session:   {config.asian_start}:00 - {config.asian_end}:00 UTC")
    print(f"   Entry Window:    {config.london_start}:00 - {config.london_start + config.entry_window}:00 UTC")
    print(f"   Exit Hour:       {config.exit_hour}:00 UTC")
    print(f"   R:R Target:      {config.rr_target}")
    
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
    
    if pf >= 1.5 and wr >= 45:
        verdict = "🟢 PROMISING - Proceed to MT5 backtest"
    elif pf >= 1.3 and wr >= 40:
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
    parser = argparse.ArgumentParser(description="London Breakout Strategy Backtest")
    parser.add_argument("--data", "-d", required=True, help="Path to H1 OHLCV CSV file")
    parser.add_argument("--rr", type=float, default=1.5, help="Risk:Reward target")
    parser.add_argument("--entry-window", type=int, default=4, help="Entry window hours after London open")
    parser.add_argument("--long-only", action="store_true", help="Only take long trades")
    parser.add_argument("--short-only", action="store_true", help="Only take short trades")
    parser.add_argument("--output", "-o", help="Output trades to CSV")
    args = parser.parse_args()
    
    # Load data
    df = load_data(args.data)
    print(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Configure
    config = LondonConfig(
        rr_target=args.rr,
        entry_window=args.entry_window,
        long_only=args.long_only,
        short_only=args.short_only,
    )
    
    # Run backtest
    trades = run_backtest(df, config)
    
    if not trades:
        print("ERROR: No trades generated. Check data timeframe (requires H1).")
        return 1
    
    # Calculate stats
    stats = calculate_stats(trades)
    
    # Print results
    print_results(stats, config)
    
    # Export if requested
    if args.output:
        trades_df = pd.DataFrame([{
            'Entry Date': t.entry_date,
            'Entry Time': t.entry_time,
            'Direction': 'Long' if t.direction == 1 else 'Short',
            'Entry Price': t.entry_price,
            'SL': t.stop_loss,
            'TP': t.take_profit,
            'Exit Time': t.exit_time,
            'Exit Price': t.exit_price,
            'Exit Reason': t.exit_reason,
            'PnL': t.pnl,
            'Asian High': t.asian_high,
            'Asian Low': t.asian_low,
        } for t in trades])
        trades_df.to_csv(args.output, index=False)
        print(f"\n✅ Trades exported to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
