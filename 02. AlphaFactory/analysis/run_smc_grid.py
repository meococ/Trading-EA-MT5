"""
SMC Grid Test - Test nhiều configs
"""
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, '.')
from smc_engine import SMCEngine

def get_mt5_data(symbol, bars=5000):
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return None
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, bars)
        mt5.shutdown()
        if rates is None:
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df[['open', 'high', 'low', 'close']]
    except:
        return None

def backtest(df, engine):
    signals = engine.generate_signals(df)
    close = signals['close'].values
    entry_long = signals['entry_long'].values
    entry_short = signals['entry_short'].values
    sl_long = signals['sl_long'].values
    tp_long = signals['tp_long'].values
    sl_short = signals['sl_short'].values
    tp_short = signals['tp_short'].values
    
    trades = []
    pos = 0
    entry_p = sl_p = tp_p = 0
    
    for i in range(len(close)):
        if pos == 1:
            if close[i] <= sl_p:
                trades.append({'pnl': sl_p - entry_p})
                pos = 0
            elif close[i] >= tp_p:
                trades.append({'pnl': tp_p - entry_p})
                pos = 0
        elif pos == -1:
            if close[i] >= sl_p:
                trades.append({'pnl': entry_p - sl_p})
                pos = 0
            elif close[i] <= tp_p:
                trades.append({'pnl': entry_p - tp_p})
                pos = 0
        
        if pos == 0:
            if entry_long[i] and not np.isnan(sl_long[i]):
                pos, entry_p, sl_p, tp_p = 1, close[i], sl_long[i], tp_long[i]
            elif entry_short[i] and not np.isnan(sl_short[i]):
                pos, entry_p, sl_p, tp_p = -1, close[i], sl_short[i], tp_short[i]
    
    if len(trades) == 0:
        return 0, 0, 0
    
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf['pnl'] > 0]
    losses = tdf[tdf['pnl'] < 0]
    gw = wins['pnl'].sum() if len(wins) > 0 else 0
    gl = abs(losses['pnl'].sum()) if len(losses) > 0 else 0.0001
    pf = gw / gl if gl > 0 else 0
    wr = len(wins) / len(tdf) * 100
    return len(tdf), round(pf, 2), round(wr, 1)

def main():
    print("SMC GRID TEST")
    print("=" * 60)
    
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD']
    
    configs = [
        {'name': 'FVG+PD', 'use_ob': False, 'use_fvg': True, 'use_pd_zone': True},
        {'name': 'OB+PD', 'use_ob': True, 'use_fvg': False, 'use_pd_zone': True},
        {'name': 'Both+PD', 'use_ob': True, 'use_fvg': True, 'use_pd_zone': True},
        {'name': 'FVG only', 'use_ob': False, 'use_fvg': True, 'use_pd_zone': False},
        {'name': 'OB only', 'use_ob': True, 'use_fvg': False, 'use_pd_zone': False},
        {'name': 'Struct', 'use_ob': False, 'use_fvg': False, 'use_pd_zone': False},
    ]
    
    all_results = []
    
    for sym in symbols:
        df = get_mt5_data(sym, 5000)
        if df is None:
            print(f"{sym}: No data")
            continue
        
        print(f"\n{sym} ({len(df)} bars):")
        
        for cfg in configs:
            engine = SMCEngine(
                ltf_swing_len=5,
                use_ob=cfg['use_ob'],
                use_fvg=cfg['use_fvg'],
                use_pd_zone=cfg['use_pd_zone'],
                rr_ratio=2.0
            )
            trades, pf, wr = backtest(df, engine)
            
            result = {'symbol': sym, 'config': cfg['name'], 'trades': trades, 'pf': pf, 'wr': wr}
            all_results.append(result)
            
            status = "OK" if pf > 1.2 else ("EDGE" if pf > 1.0 else "NO")
            print(f"  {cfg['name']:10s}: T={trades:3d} PF={pf:5.2f} WR={wr:5.1f}% [{status}]")
    
    print("\n" + "=" * 60)
    print("BEST CONFIGS BY SYMBOL:")
    print("=" * 60)
    
    rdf = pd.DataFrame(all_results)
    for sym in rdf['symbol'].unique():
        sym_data = rdf[rdf['symbol'] == sym]
        valid = sym_data[sym_data['trades'] >= 10]
        if len(valid) > 0:
            best = valid.loc[valid['pf'].idxmax()]
            print(f"{sym}: {best['config']} (PF={best['pf']}, T={best['trades']})")
    
    print("\n" + "=" * 60)
    print("BEST CONFIGS OVERALL:")
    print("=" * 60)
    
    for cfg_name in rdf['config'].unique():
        cfg_data = rdf[(rdf['config'] == cfg_name) & (rdf['trades'] >= 5)]
        if len(cfg_data) > 0:
            avg_pf = cfg_data['pf'].mean()
            total_t = cfg_data['trades'].sum()
            print(f"{cfg_name:10s}: Avg PF={avg_pf:.2f}, Total T={total_t}")
    
    rdf.to_csv('smc_grid_results.csv', index=False)
    print("\nSaved to smc_grid_results.csv")

if __name__ == "__main__":
    main()
