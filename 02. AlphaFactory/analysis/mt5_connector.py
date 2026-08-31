#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5 Native Python Connector
===========================
Direct integration với MetaTrader 5 terminal qua official Python package.

Chức năng:
1. Lấy historical data trực tiếp từ MT5
2. Lấy account info và positions
3. Export data cho VectorBT analysis
4. So sánh VectorBT vs MT5 data

Installation:
  pip install MetaTrader5

Usage:
  python mt5_connector.py --action info
  python mt5_connector.py --action data --symbol XAUUSD --timeframe H1 --bars 1000
  python mt5_connector.py --action export --symbol XAUUSD --out "data/XAUUSD_H1.csv"
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Pin every MT5 attach to the factory isolate. A bare mt5.initialize() grabs
# whichever terminal is already running, which on the Owner machine is the GUI
# terminal being traded from -- see tools/factory_paths.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.factory_paths import FactoryPathError, mt5_initialize_kwargs  # noqa: E402


# ============================================================
# TIMEFRAME MAPPING
# ============================================================

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1 if HAS_MT5 else 1,
    "M5": mt5.TIMEFRAME_M5 if HAS_MT5 else 5,
    "M15": mt5.TIMEFRAME_M15 if HAS_MT5 else 15,
    "M30": mt5.TIMEFRAME_M30 if HAS_MT5 else 30,
    "H1": mt5.TIMEFRAME_H1 if HAS_MT5 else 60,
    "H4": mt5.TIMEFRAME_H4 if HAS_MT5 else 240,
    "D1": mt5.TIMEFRAME_D1 if HAS_MT5 else 1440,
    "W1": mt5.TIMEFRAME_W1 if HAS_MT5 else 10080,
    "MN1": mt5.TIMEFRAME_MN1 if HAS_MT5 else 43200,
}


# ============================================================
# CONNECTION
# ============================================================

def connect_mt5() -> bool:
    """
    Initialize connection to MT5 terminal.
    Returns True if successful.
    """
    if not HAS_MT5:
        print("ERROR: MetaTrader5 package not installed.")
        print("Install with: pip install MetaTrader5")
        return False
    
    try:
        init_kwargs = mt5_initialize_kwargs()
    except FactoryPathError as exc:
        print(f"ERROR: cannot resolve the factory MT5 isolate.\n{exc}")
        return False

    if not mt5.initialize(**init_kwargs):
        print(f"ERROR: MT5 initialization failed. Error: {mt5.last_error()}")
        print(f"Factory terminal: {init_kwargs['path']}")
        return False
    
    return True


def disconnect_mt5():
    """Shutdown MT5 connection."""
    if HAS_MT5:
        mt5.shutdown()


# ============================================================
# ACCOUNT INFO
# ============================================================

def get_account_info() -> dict:
    """Get current account information."""
    if not connect_mt5():
        return {}
    
    account = mt5.account_info()
    if account is None:
        disconnect_mt5()
        return {}
    
    info = {
        "login": account.login,
        "server": account.server,
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "free_margin": account.margin_free,
        "leverage": account.leverage,
        "profit": account.profit,
        "currency": account.currency,
        "trade_mode": "Demo" if account.trade_mode == 0 else "Real",
    }
    
    disconnect_mt5()
    return info


def get_terminal_info() -> dict:
    """Get MT5 terminal information."""
    if not connect_mt5():
        return {}
    
    terminal = mt5.terminal_info()
    if terminal is None:
        disconnect_mt5()
        return {}
    
    info = {
        "connected": terminal.connected,
        "trade_allowed": terminal.trade_allowed,
        "path": terminal.path,
        "data_path": terminal.data_path,
        "company": terminal.company,
        "build": terminal.build,
    }
    
    disconnect_mt5()
    return info


# ============================================================
# HISTORICAL DATA
# ============================================================

def get_historical_data(symbol: str, timeframe: str = "H1", bars: int = 1000) -> pd.DataFrame:
    """
    Get historical OHLCV data from MT5.
    
    Args:
        symbol: Trading symbol (e.g., "XAUUSD")
        timeframe: Timeframe string (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
        bars: Number of bars to fetch
    
    Returns:
        DataFrame with columns: time, open, high, low, close, tick_volume, spread, real_volume
    """
    if not HAS_PANDAS:
        print("ERROR: pandas required. pip install pandas")
        return pd.DataFrame()
    
    if not connect_mt5():
        return pd.DataFrame()
    
    tf = TIMEFRAMES.get(timeframe.upper())
    if tf is None:
        print(f"ERROR: Invalid timeframe {timeframe}. Valid: {list(TIMEFRAMES.keys())}")
        disconnect_mt5()
        return pd.DataFrame()
    
    # Fetch data
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    
    if rates is None or len(rates) == 0:
        print(f"ERROR: No data for {symbol}. Error: {mt5.last_error()}")
        disconnect_mt5()
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    disconnect_mt5()
    return df


def get_ticks(symbol: str, count: int = 1000) -> pd.DataFrame:
    """
    Get tick data from MT5.
    Useful for understanding intra-bar price movements.
    """
    if not HAS_PANDAS:
        return pd.DataFrame()
    
    if not connect_mt5():
        return pd.DataFrame()
    
    ticks = mt5.copy_ticks_from_pos(symbol, 0, count, mt5.COPY_TICKS_ALL)
    
    if ticks is None or len(ticks) == 0:
        print(f"ERROR: No ticks for {symbol}")
        disconnect_mt5()
        return pd.DataFrame()
    
    df = pd.DataFrame(ticks)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    disconnect_mt5()
    return df


# ============================================================
# DATA EXPORT
# ============================================================

def export_to_csv(symbol: str, timeframe: str, bars: int, output_path: str) -> bool:
    """Export historical data to CSV for VectorBT."""
    df = get_historical_data(symbol, timeframe, bars)
    
    if df.empty:
        return False
    
    # Rename columns for VectorBT compatibility
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Spread', 'RealVolume']
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output)
    print(f"✅ Exported {len(df)} bars to {output}")
    return True


def export_for_vectorbt(symbol: str, timeframe: str = "H1", days: int = 365, output_dir: str = "") -> str:
    """
    Export data in VectorBT-ready format.
    Returns path to exported file.
    """
    # Calculate bars needed
    bars_per_day = {
        "M1": 1440, "M5": 288, "M15": 96, "M30": 48,
        "H1": 24, "H4": 6, "D1": 1, "W1": 0.14, "MN1": 0.033
    }
    
    bars = int(days * bars_per_day.get(timeframe.upper(), 24))
    
    if not output_dir:
        output_dir = Path(__file__).parent.parent.parent / "01. vectorbt" / "data"
    
    output_path = Path(output_dir) / f"{symbol}_{timeframe}.csv"
    
    if export_to_csv(symbol, timeframe, bars, str(output_path)):
        return str(output_path)
    return ""


# ============================================================
# SYMBOLS INFO
# ============================================================

def get_symbols() -> list:
    """Get list of available symbols."""
    if not connect_mt5():
        return []
    
    symbols = mt5.symbols_get()
    
    if symbols is None:
        disconnect_mt5()
        return []
    
    result = [s.name for s in symbols if s.visible]
    
    disconnect_mt5()
    return result


def get_symbol_info(symbol: str) -> dict:
    """Get detailed symbol information."""
    if not connect_mt5():
        return {}
    
    info = mt5.symbol_info(symbol)
    
    if info is None:
        disconnect_mt5()
        return {}
    
    result = {
        "symbol": info.name,
        "description": info.description,
        "spread": info.spread,
        "digits": info.digits,
        "point": info.point,
        "trade_contract_size": info.trade_contract_size,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "trade_mode": info.trade_mode,
        "bid": info.bid,
        "ask": info.ask,
    }
    
    disconnect_mt5()
    return result


# ============================================================
# POSITIONS & HISTORY
# ============================================================

def get_positions() -> list:
    """Get current open positions."""
    if not connect_mt5():
        return []
    
    positions = mt5.positions_get()
    
    if positions is None:
        disconnect_mt5()
        return []
    
    result = []
    for p in positions:
        result.append({
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume,
            "price_open": p.price_open,
            "price_current": p.price_current,
            "profit": p.profit,
            "sl": p.sl,
            "tp": p.tp,
            "time": datetime.fromtimestamp(p.time),
        })
    
    disconnect_mt5()
    return result


def get_history_deals(days: int = 30) -> list:
    """Get historical deals."""
    if not connect_mt5():
        return []
    
    from_date = datetime.now() - timedelta(days=days)
    to_date = datetime.now()
    
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None:
        disconnect_mt5()
        return []
    
    result = []
    for d in deals:
        result.append({
            "ticket": d.ticket,
            "order": d.order,
            "symbol": d.symbol,
            "type": d.type,
            "entry": d.entry,
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "commission": d.commission,
            "swap": d.swap,
            "time": datetime.fromtimestamp(d.time),
        })
    
    disconnect_mt5()
    return result


# ============================================================
# CLI
# ============================================================

def print_info(info: dict, title: str):
    """Pretty print info dict."""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print('=' * 50)
    for k, v in info.items():
        print(f"  {k}: {v}")
    print()


def main():
    parser = argparse.ArgumentParser(description="MT5 Native Python Connector")
    parser.add_argument("--action", "-a", default="info",
                       choices=["info", "terminal", "data", "ticks", "export", "symbols", "positions", "history"],
                       help="Action to perform")
    parser.add_argument("--symbol", "-s", default="XAUUSD", help="Trading symbol")
    parser.add_argument("--timeframe", "-tf", default="H1", help="Timeframe")
    parser.add_argument("--bars", "-b", type=int, default=1000, help="Number of bars")
    parser.add_argument("--days", "-d", type=int, default=365, help="Days of history")
    parser.add_argument("--out", "-o", default="", help="Output path")
    args = parser.parse_args()
    
    if not HAS_MT5:
        print("ERROR: MetaTrader5 package not installed.")
        print("Install with: pip install MetaTrader5")
        return 1
    
    if args.action == "info":
        info = get_account_info()
        if info:
            print_info(info, "ACCOUNT INFO")
        else:
            print("Failed to get account info. Is MT5 running?")
            return 1
    
    elif args.action == "terminal":
        info = get_terminal_info()
        if info:
            print_info(info, "TERMINAL INFO")
        else:
            return 1
    
    elif args.action == "data":
        df = get_historical_data(args.symbol, args.timeframe, args.bars)
        if not df.empty:
            print(f"\n{args.symbol} {args.timeframe} - {len(df)} bars")
            print(df.tail(10))
        else:
            return 1
    
    elif args.action == "ticks":
        df = get_ticks(args.symbol, args.bars)
        if not df.empty:
            print(f"\n{args.symbol} ticks - {len(df)} records")
            print(df.tail(10))
        else:
            return 1
    
    elif args.action == "export":
        path = export_for_vectorbt(args.symbol, args.timeframe, args.days, args.out)
        if not path:
            return 1
        print(f"Exported to: {path}")
    
    elif args.action == "symbols":
        symbols = get_symbols()
        print(f"\nAvailable symbols ({len(symbols)}):")
        for s in symbols[:50]:  # Show first 50
            print(f"  {s}")
        if len(symbols) > 50:
            print(f"  ... and {len(symbols) - 50} more")
    
    elif args.action == "positions":
        positions = get_positions()
        print(f"\nOpen positions ({len(positions)}):")
        for p in positions:
            print(f"  {p['symbol']} {p['type']} {p['volume']} @ {p['price_open']} | P/L: {p['profit']}")
    
    elif args.action == "history":
        deals = get_history_deals(args.days)
        print(f"\nHistory deals ({len(deals)}) - last {args.days} days:")
        for d in deals[-10:]:  # Show last 10
            print(f"  {d['time']} {d['symbol']} {d['volume']} @ {d['price']} | {d['profit']}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
