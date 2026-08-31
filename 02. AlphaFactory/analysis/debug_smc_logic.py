"""
Debug SMC Logic - Tìm hiểu tại sao Python có signals mà MT5 không có
"""
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

def main():
    print("=" * 60)
    print("DEBUG SMC LOGIC")
    print("=" * 60)
    
    # Connect MT5
    if not mt5.initialize():
        print("MT5 init failed")
        return
    
    # Get XAUUSD H1 data
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 500)
    mt5.shutdown()
    
    if rates is None:
        print("No data")
        return
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"Data: {len(df)} bars")
    print(f"Range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    # Parameters
    swing_len = 5
    fvg_min_atr = 0.3
    premium = 0.70
    discount = 0.30
    
    # Calculate ATR
    tr = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            np.abs(df['high'] - df['close'].shift(1)),
            np.abs(df['low'] - df['close'].shift(1))
        )
    )
    atr = tr.rolling(14).mean()
    
    signals = []
    
    for i in range(60, len(df)):
        close = df['close'].iloc[i]
        
        # Find swing high/low in last 50 bars
        swing_high = 0
        swing_low = float('inf')
        
        for j in range(swing_len, 50):
            idx = i - j
            if idx < swing_len:
                break
            
            # Check swing high
            if swing_high == 0:
                is_sh = True
                h = df['high'].iloc[idx]
                for k in range(1, swing_len + 1):
                    if df['high'].iloc[idx - k] > h or df['high'].iloc[idx + k] > h:
                        is_sh = False
                        break
                if is_sh:
                    swing_high = h
            
            # Check swing low
            if swing_low == float('inf'):
                is_sl = True
                l = df['low'].iloc[idx]
                for k in range(1, swing_len + 1):
                    if df['low'].iloc[idx - k] < l or df['low'].iloc[idx + k] < l:
                        is_sl = False
                        break
                if is_sl:
                    swing_low = l
            
            if swing_high > 0 and swing_low < float('inf'):
                break
        
        if swing_high == 0 or swing_low == float('inf'):
            continue
        
        # Bias
        bias = 0
        if close > swing_high:
            bias = 1
        elif close < swing_low:
            bias = -1
        
        # Zone
        range_ = swing_high - swing_low
        if range_ <= 0:
            continue
        pd_level = (close - swing_low) / range_
        zone = 0
        if pd_level >= premium:
            zone = 1
        elif pd_level <= discount:
            zone = -1
        
        # FVG
        bull_fvg = False
        bear_fvg = False
        cur_atr = atr.iloc[i]
        
        for j in range(2, 30):
            idx = i - j
            if idx < 2:
                break
            
            low_j = df['low'].iloc[idx]
            high_j2 = df['high'].iloc[idx - 2]
            high_j = df['high'].iloc[idx]
            low_j2 = df['low'].iloc[idx - 2]
            
            # Bullish FVG
            if not bull_fvg and low_j > high_j2:
                gap = low_j - high_j2
                if gap >= cur_atr * fvg_min_atr:
                    if close <= low_j and close >= high_j2:
                        bull_fvg = True
            
            # Bearish FVG
            if not bear_fvg and high_j < low_j2:
                gap = low_j2 - high_j
                if gap >= cur_atr * fvg_min_atr:
                    if close >= high_j and close <= low_j2:
                        bear_fvg = True
        
        # Signal check
        long_sig = (bias == 1) and (zone == -1 or bull_fvg)
        short_sig = (bias == -1) and (zone == 1 or bear_fvg)
        
        if long_sig or short_sig:
            signals.append({
                'bar': i,
                'time': df['time'].iloc[i],
                'close': close,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'bias': bias,
                'zone': zone,
                'bull_fvg': bull_fvg,
                'bear_fvg': bear_fvg,
                'signal': 'LONG' if long_sig else 'SHORT'
            })
    
    print(f"\nSignals found: {len(signals)}")
    
    if len(signals) > 0:
        print("\nLast 10 signals:")
        for s in signals[-10:]:
            print(f"  {s['time']} | {s['signal']} | Close={s['close']:.2f} | "
                  f"SH={s['swing_high']:.2f} SL={s['swing_low']:.2f} | "
                  f"Bias={s['bias']} Zone={s['zone']} BullFVG={s['bull_fvg']} BearFVG={s['bear_fvg']}")
    else:
        print("\n!!! NO SIGNALS - Checking why...")
        
        # Debug last 10 bars
        print("\nLast 10 bars analysis:")
        for i in range(len(df) - 10, len(df)):
            close = df['close'].iloc[i]
            
            # Quick check swings
            swing_high = df['high'].iloc[i-50:i].max()
            swing_low = df['low'].iloc[i-50:i].min()
            
            bias = 0
            if close > swing_high:
                bias = 1
            elif close < swing_low:
                bias = -1
            
            range_ = swing_high - swing_low
            pd_level = (close - swing_low) / range_ if range_ > 0 else 0.5
            zone = 0
            if pd_level >= premium:
                zone = 1
            elif pd_level <= discount:
                zone = -1
            
            print(f"  Bar {i}: Close={close:.2f} SH={swing_high:.2f} SL={swing_low:.2f} "
                  f"Bias={bias} Zone={zone} PDLevel={pd_level:.2f}")

if __name__ == "__main__":
    main()
