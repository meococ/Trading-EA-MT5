#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pseudo Holdout Split
====================
Split trades into in-sample / holdout by time.
Note: This is a pseudo-holdout from a single backtest.
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


def _read_trades_csv(path: Path) -> List[Tuple[datetime, float]]:
    trades = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            exit_time = row.get("exit_time") or row.get("ExitTime") or ""
            profit = row.get("profit") or row.get("Profit") or ""
            if not exit_time:
                continue
            try:
                t = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
                p = float(profit)
            except Exception:
                continue
            trades.append((t, p))
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
    pf = (gp / gl) if gl > 0 else 999.99  # v11.2: cap to avoid NaN in JSON
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
    ap = argparse.ArgumentParser(description="Pseudo holdout split by time")
    ap.add_argument("--trades", required=True, help="Path to trades.csv")
    ap.add_argument("--holdout-pct", type=float, default=0.1, help="Holdout percentage (0-1)")
    ap.add_argument("--min-trades", type=int, default=30, help="Minimum trades per split")
    ap.add_argument("--out", default="", help="Output directory")
    args = ap.parse_args()

    trades = _read_trades_csv(Path(args.trades))
    if len(trades) < args.min_trades * 2:
        print("ERROR: Not enough trades for holdout split")
        return 1

    trades.sort(key=lambda x: x[0])
    split_idx = int(len(trades) * (1 - args.holdout_pct))
    split_idx = max(args.min_trades, min(split_idx, len(trades) - args.min_trades))

    in_sample = trades[:split_idx]
    holdout = trades[split_idx:]

    result = {
        "holdout_pct": args.holdout_pct,
        "split_time": in_sample[-1][0].isoformat(),
        "in_sample": _stats([p for _, p in in_sample]),
        "holdout": _stats([p for _, p in holdout]),
        "note": "Pseudo-holdout from a single backtest; not a true unseen dataset.",
    }

    out_dir = Path(args.out) if args.out else Path(args.trades).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "holdout_split.json"
    out_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"[Holdout] saved: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
