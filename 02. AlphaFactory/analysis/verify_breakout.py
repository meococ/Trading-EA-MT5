"""
Verify simple breakout logic - exact match with EA_Test_Trades
"""
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

def test_breakout(symbol, bars=1000):
    print(f"\n{symbol}:")
    
    if not mt5.initialize():
        return None
    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, bars)
    mt5.shutdown()
    
    if rates is None:
        print("  No data")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    trades = []
    in_trade = False
    entry = sl = tp = 0
    trade_type = ""
    
    for i in range(25, len(df)):
        close = df['close'].iloc[i]
        
        # Check exit
        if in_trade:
            if trade_type == "BUY":
                if close <= sl:
                    trades.append({'type': 'B', 'pnl': sl - entry, 'exit': 'SL'})
                    in_trade = False
                elif close >= tp:
                    trades.append({'type': 'B', 'pnl': tp - entry, 'exit': 'TP'})
                    in_trade = False
            else:
                if close >= sl:
                    trades.append({'type': 'S', 'pnl': entry - sl, 'exit': 'SL'})
                    in_trade = False
                elif close <= tp:
                    trades.append({'type': 'S', 'pnl': entry - tp, 'exit': 'TP'})
                    in_trade = False
            if in_trade:
                continue
        
        # 20-bar high/low (bars 1-20 from current)
        high20 = df['high'].iloc[i-21:i-1].max()
        low20 = df['low'].iloc[i-21:i-1].min()
        close1 = df['close'].iloc[i-1]
        
        # Breakout up - close[1] > high of bars 2-21
        if close1 > high20:
            entry = close1
            sl = low20
            sl_dist = entry - sl
            tp = entry + sl_dist * 2
            trade_type = "BUY"
            in_trade = True
        
        # Breakout down
        elif close1 < low20:
            entry = close1
            sl = high20
            sl_dist = sl - entry
            tp = entry - sl_dist * 2
            trade_type = "SELL"
            in_trade = True
    
    if len(trades) == 0:
        print("  NO TRADES")
        return None
    
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf['pnl'] > 0]
    losses = tdf[tdf['pnl'] < 0]
    
    gw = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    
    print(f"  Trades: {len(tdf)} | Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"  PF: {gw/gl:.2f} | WR: {len(wins)/len(tdf)*100:.1f}%")
    
    return len(tdf)

print("=" * 50)
print("BREAKOUT VERIFICATION")
print("=" * 50)

symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
for sym in symbols:
    test_breakout(sym, 2000)
