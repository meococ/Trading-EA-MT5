"""
Test SMC v2 Logic - Structure Break + Pullback
"""
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

def test_smc_v2(symbol, bars=2000):
    print(f"\n{'='*50}")
    print(f"Testing SMC v2 on {symbol}")
    print(f"{'='*50}")
    
    if not mt5.initialize():
        print("MT5 init failed")
        return None
    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, bars)
    mt5.shutdown()
    
    if rates is None:
        print("No data")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"Data: {len(df)} bars from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    # Params
    swing_len = 5
    pullback_pct = 0.50
    rr = 2.0
    
    # Track state
    bullish_break = False
    bearish_break = False
    break_bar = 0
    last_sh = 0
    last_sl = 0
    
    trades = []
    in_trade = False
    entry_price = 0
    sl_price = 0
    tp_price = 0
    trade_type = ""
    
    for i in range(60, len(df)):
        close = df['close'].iloc[i]
        close_prev = df['close'].iloc[i-1]
        
        # Find swings
        swing_high = 0
        swing_low = float('inf')
        
        for j in range(swing_len, 100):
            idx = i - j
            if idx < swing_len:
                break
            
            # Swing high
            if swing_high == 0:
                is_sh = True
                h = df['high'].iloc[idx]
                for k in range(1, swing_len + 1):
                    if idx - k < 0 or idx + k >= len(df):
                        is_sh = False
                        break
                    if df['high'].iloc[idx - k] > h or df['high'].iloc[idx + k] > h:
                        is_sh = False
                        break
                if is_sh:
                    swing_high = h
            
            # Swing low
            if swing_low == float('inf'):
                is_sl = True
                l = df['low'].iloc[idx]
                for k in range(1, swing_len + 1):
                    if idx - k < 0 or idx + k >= len(df):
                        is_sl = False
                        break
                    if df['low'].iloc[idx - k] < l or df['low'].iloc[idx + k] < l:
                        is_sl = False
                        break
                if is_sl:
                    swing_low = l
            
            if swing_high > 0 and swing_low < float('inf'):
                break
        
        if swing_high == 0 or swing_low == float('inf'):
            continue
        
        range_ = swing_high - swing_low
        if range_ <= 0:
            continue
        
        # Check exit first
        if in_trade:
            if trade_type == "LONG":
                if close <= sl_price:
                    pnl = sl_price - entry_price
                    trades.append({'type': 'L', 'pnl': pnl, 'exit': 'SL'})
                    in_trade = False
                elif close >= tp_price:
                    pnl = tp_price - entry_price
                    trades.append({'type': 'L', 'pnl': pnl, 'exit': 'TP'})
                    in_trade = False
            elif trade_type == "SHORT":
                if close >= sl_price:
                    pnl = entry_price - sl_price
                    trades.append({'type': 'S', 'pnl': pnl, 'exit': 'SL'})
                    in_trade = False
                elif close <= tp_price:
                    pnl = entry_price - tp_price
                    trades.append({'type': 'S', 'pnl': pnl, 'exit': 'TP'})
                    in_trade = False
            continue
        
        # Detect structure break
        if not bullish_break and close > swing_high and close_prev <= swing_high:
            bullish_break = True
            bearish_break = False
            break_bar = i
            last_sh = swing_high
            last_sl = swing_low
        
        if not bearish_break and close < swing_low and close_prev >= swing_low:
            bearish_break = True
            bullish_break = False
            break_bar = i
            last_sh = swing_high
            last_sl = swing_low
        
        # Entry on pullback
        if bullish_break and break_bar > 0:
            bars_since = i - break_bar
            if bars_since > 20:
                bullish_break = False
                continue
            
            pullback_range = last_sh - last_sl
            pullback_level = last_sh - pullback_range * pullback_pct
            
            if close <= pullback_level and close > last_sl:
                entry_price = close
                sl_price = last_sl - pullback_range * 0.1
                sl_dist = entry_price - sl_price
                tp_price = entry_price + sl_dist * rr
                trade_type = "LONG"
                in_trade = True
                bullish_break = False
        
        if bearish_break and break_bar > 0:
            bars_since = i - break_bar
            if bars_since > 20:
                bearish_break = False
                continue
            
            pullback_range = last_sh - last_sl
            pullback_level = last_sl + pullback_range * pullback_pct
            
            if close >= pullback_level and close < last_sh:
                entry_price = close
                sl_price = last_sh + pullback_range * 0.1
                sl_dist = sl_price - entry_price
                tp_price = entry_price - sl_dist * rr
                trade_type = "SHORT"
                in_trade = True
                bearish_break = False
    
    # Results
    if len(trades) == 0:
        print("NO TRADES")
        return {'symbol': symbol, 'trades': 0}
    
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf['pnl'] > 0]
    losses = tdf[tdf['pnl'] < 0]
    
    gw = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.001
    pf = gw / gl
    wr = len(wins) / len(tdf) * 100
    
    print(f"Trades: {len(tdf)} (L={len(tdf[tdf['type']=='L'])}, S={len(tdf[tdf['type']=='S'])})")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}")
    print(f"PF: {pf:.2f}, WR: {wr:.1f}%")
    
    return {'symbol': symbol, 'trades': len(tdf), 'pf': round(pf, 2), 'wr': round(wr, 1)}

def main():
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
    results = []
    
    for sym in symbols:
        r = test_smc_v2(sym, 3000)
        if r:
            results.append(r)
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for r in results:
        if r['trades'] > 0:
            print(f"{r['symbol']}: T={r['trades']} PF={r['pf']} WR={r['wr']}%")
        else:
            print(f"{r['symbol']}: NO TRADES")

if __name__ == "__main__":
    main()
