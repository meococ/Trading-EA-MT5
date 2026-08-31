#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baseline / Control Generator
============================
Generate random-entry baseline using same holding times and direction mix.
Requires MetaTrader5 package and symbol availability.
"""

import argparse
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except Exception:
    HAS_MT5 = False


TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1 if HAS_MT5 else 1,
    "M5": mt5.TIMEFRAME_M5 if HAS_MT5 else 5,
    "M15": mt5.TIMEFRAME_M15 if HAS_MT5 else 15,
    "M30": mt5.TIMEFRAME_M30 if HAS_MT5 else 30,
    "H1": mt5.TIMEFRAME_H1 if HAS_MT5 else 60,
    "H4": mt5.TIMEFRAME_H4 if HAS_MT5 else 240,
    "D1": mt5.TIMEFRAME_D1 if HAS_MT5 else 1440,
}


def _read_trades_csv(path: Path) -> List[Tuple[datetime, datetime, int, float]]:
    trades = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            entry_time = row.get("entry_time") or row.get("EntryTime") or ""
            exit_time = row.get("exit_time") or row.get("ExitTime") or ""
            side = (row.get("side") or row.get("Side") or "").strip().lower()
            profit = row.get("profit") or row.get("Profit") or ""
            if not entry_time or not exit_time:
                continue
            try:
                et = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
                xt = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
                p = float(profit)
            except Exception:
                continue
            direction = 1 if side == "buy" else -1 if side == "sell" else 0
            if direction == 0:
                continue
            trades.append((et, xt, direction, p))
    return trades


def _stats(profits: List[float]) -> dict:
    if not profits:
        return {
            "n": 0,
            "net_profit": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = (gp / gl) if gl > 0 else 999.99  # v11.2: cap
    win_rate = (len(wins) / len(profits) * 100.0) if profits else 0.0
    expectancy = sum(profits) / len(profits)
    return {
        "n": len(profits),
        "net_profit": sum(profits),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(pf, 3),
        "expectancy": round(expectancy, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Baseline / Control generator")
    ap.add_argument("--trades", required=True, help="Path to trades.csv")
    ap.add_argument("--symbol", required=True, help="Symbol for MT5 data")
    ap.add_argument("--timeframe", default="M15", help="Timeframe (M1/M5/M15/M30/H1/H4/D1)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--out", default="", help="Output directory")
    args = ap.parse_args()

    if not HAS_MT5:
        print("ERROR: MetaTrader5 package not installed")
        return 1

    trades = _read_trades_csv(Path(args.trades))
    if len(trades) < 10:
        print("ERROR: Not enough trades for baseline")
        return 1

    tf_key = args.timeframe.upper()
    if tf_key not in TIMEFRAME_MAP:
        print(f"ERROR: Invalid timeframe {args.timeframe}")
        return 1

    if not mt5.initialize():
        print(f"ERROR: MT5 initialize failed: {mt5.last_error()}")
        return 1
    if not mt5.symbol_select(args.symbol, True):
        print(f"ERROR: Symbol {args.symbol} not available in MT5")
        mt5.shutdown()
        return 1

    try:
        earliest = min(t[0] for t in trades) - timedelta(days=2)
        latest = max(t[1] for t in trades) + timedelta(days=2)
        rates = mt5.copy_rates_range(args.symbol, TIMEFRAME_MAP[tf_key], earliest, latest)
        if rates is None or len(rates) < 100:
            print("ERROR: Not enough rate data")
            return 1

        closes = [r["close"] for r in rates]
        times = [datetime.fromtimestamp(r["time"]) for r in rates]
        tf_minutes = int(tf_key[1:]) if tf_key.startswith("M") else 60 if tf_key == "H1" else 240 if tf_key == "H4" else 1440

        # Build holding periods in bars
        holds = []
        dirs = []
        actual_profits = []
        for et, xt, d, p in trades:
            dur_min = max(1.0, (xt - et).total_seconds() / 60.0)
            hold_bars = max(1, int(round(dur_min / tf_minutes)))
            holds.append(hold_bars)
            dirs.append(d)
            actual_profits.append(p)

        rng = random.Random(args.seed)
        max_hold = max(holds)
        if len(closes) <= max_hold + 5:
            print("ERROR: Rate data too short for holding periods")
            return 1

        baseline_profits = []
        for hold, d in zip(holds, dirs):
            idx = rng.randint(0, len(closes) - hold - 1)
            entry = closes[idx]
            exitp = closes[idx + hold]
            pnl = (exitp - entry) * d
            baseline_profits.append(pnl)

        result = {
            "symbol": args.symbol,
            "timeframe": tf_key,
            "n_trades": len(trades),
            "baseline_stats": _stats(baseline_profits),
            "actual_stats": _stats(actual_profits),
        }
    finally:
        mt5.shutdown()

    out_dir = Path(args.out) if args.out else Path(args.trades).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "baseline_control.json"
    out_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"[Baseline] saved: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
