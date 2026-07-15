#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IBS Grid Search - Tìm best parameters
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from itertools import product

# Import từ ibs_trend_alpha
from ibs_trend_alpha import (
    Config, generate_signals, run_backtest, calculate_stats, load_data
)

def grid_search(df: pd.DataFrame, param_grid: dict) -> pd.DataFrame:
    """Run grid search over parameter combinations"""
    results = []
    
    # Generate all combinations
    keys = list(param_grid.keys())
    combinations = list(product(*param_grid.values()))
    
    print(f"Testing {len(combinations)} parameter combinations...")
    
    for i, combo in enumerate(combinations):
        params = dict(zip(keys, combo))
        
        config = Config(
            sma_period=params.get('sma', 200),
            ibs_oversold=params.get('ibs_low', 0.2),
            ibs_overbought=params.get('ibs_high', 0.8),
            max_holding_bars=params.get('max_bars', 5),
        )
        
        long_only = params.get('long_only', True)
        
        try:
            df_signals = generate_signals(df.copy(), config)
            trades, _ = run_backtest(df_signals, config, long_only)
            
            if len(trades) < 30:  # Min trades
                continue
                
            stats = calculate_stats(trades)
            
            results.append({
                **params,
                'trades': stats['total_trades'],
                'win_rate': stats['win_rate'],
                'pf': stats['profit_factor'],
                'expectancy': stats['expectancy'],
                'rr_ratio': stats['rr_ratio'],
                'total_pnl': stats['total_pnl'],
                'max_consec_loss': stats['max_consec_losses'],
            })
        except Exception as e:
            print(f"Error with {params}: {e}")
            continue
        
        if (i + 1) % 20 == 0:
            print(f"  Tested {i + 1}/{len(combinations)}")
    
    return pd.DataFrame(results)


def main():
    # Load H4 data
    data_path = Path(__file__).parent.parent.parent / "01. vectorbt" / "data" / "XAUUSD_H4.csv"
    
    if not data_path.exists():
        print(f"Data not found: {data_path}")
        return 1
    
    df = load_data(str(data_path))
    print(f"Loaded {len(df)} bars")
    
    # Define parameter grid
    param_grid = {
        'sma': [50, 100, 150, 200],
        'ibs_low': [0.1, 0.15, 0.2, 0.25, 0.3],
        'max_bars': [3, 5, 8, 10, 15],
        'long_only': [True],
    }
    
    # Run grid search
    results = grid_search(df, param_grid)
    
    if results.empty:
        print("No valid results")
        return 1
    
    # Sort by PF
    results = results.sort_values('pf', ascending=False)
    
    # Print top 20
    print("\n" + "=" * 80)
    print("TOP 20 PARAMETER COMBINATIONS (by Profit Factor)")
    print("=" * 80)
    print(results.head(20).to_string(index=False))
    
    # Print best by different metrics
    print("\n" + "-" * 80)
    print("BEST BY DIFFERENT METRICS:")
    print("-" * 80)
    
    best_pf = results.iloc[0]
    print(f"\n🏆 Best PF ({best_pf['pf']:.2f}):")
    print(f"   SMA={best_pf['sma']}, IBS={best_pf['ibs_low']}, MaxBars={best_pf['max_bars']}")
    print(f"   Trades={best_pf['trades']}, WR={best_pf['win_rate']}%, R:R={best_pf['rr_ratio']:.2f}")
    
    best_wr = results.sort_values('win_rate', ascending=False).iloc[0]
    print(f"\n🎯 Best Win Rate ({best_wr['win_rate']}%):")
    print(f"   SMA={best_wr['sma']}, IBS={best_wr['ibs_low']}, MaxBars={best_wr['max_bars']}")
    print(f"   PF={best_wr['pf']:.2f}, Trades={best_wr['trades']}")
    
    best_exp = results.sort_values('expectancy', ascending=False).iloc[0]
    print(f"\n💰 Best Expectancy ({best_exp['expectancy']:.2f} pts/trade):")
    print(f"   SMA={best_exp['sma']}, IBS={best_exp['ibs_low']}, MaxBars={best_exp['max_bars']}")
    print(f"   PF={best_exp['pf']:.2f}, WR={best_exp['win_rate']}%")
    
    # Filter for robust (trades > 200, PF > 1.1)
    robust = results[(results['trades'] >= 200) & (results['pf'] >= 1.1)]
    print(f"\n📊 ROBUST CANDIDATES (Trades >= 200, PF >= 1.1): {len(robust)}")
    if not robust.empty:
        print(robust.to_string(index=False))
    else:
        print("   None found - strategy may not have enough edge")
    
    # Save results
    output_path = Path(__file__).parent / "ibs_grid_results.csv"
    results.to_csv(output_path, index=False)
    print(f"\n✅ Results saved to {output_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
