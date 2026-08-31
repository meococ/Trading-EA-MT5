#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regime Split (Returns-based)
============================
Classify trade regimes based on rolling return statistics.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple


def _read_trades_csv(path: Path) -> List[Tuple[str, float]]:
    trades = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            exit_time = row.get("exit_time") or row.get("ExitTime") or ""
            profit = row.get("profit") or row.get("Profit") or ""
            if not exit_time:
                continue
            try:
                p = float(profit)
            except Exception:
                continue
            trades.append((exit_time, p))
    return trades


def _stats(profits: List[float]) -> Dict:
    if not profits:
        return {
            "n": 0,
            "net_profit": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
        }
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = (gp / gl) if gl > 0 else 999.99  # v11.2: cap
    win_rate = (len(wins) / len(profits) * 100.0) if profits else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    expectancy = sum(profits) / len(profits)
    return {
        "n": len(profits),
        "net_profit": sum(profits),
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(pf, 3),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
    }


def _regime_from_window(profits: List[float], z_thresh: float) -> str:
    mean = sum(profits) / len(profits)
    var = sum((p - mean) ** 2 for p in profits) / max(1, len(profits) - 1)
    std = math.sqrt(var)
    if std <= 0:
        return "RANGE"
    z = mean / std
    if z >= z_thresh:
        return "BULL"
    if z <= -z_thresh:
        return "BEAR"
    return "RANGE"


def regime_split(trades: List[Tuple[str, float]], window: int, z_thresh: float) -> dict:
    series = []
    for i in range(len(trades)):
        if i < window:
            series.append((trades[i][0], trades[i][1], "UNKNOWN"))
            continue
        win = [p for _, p in trades[i - window : i]]
        regime = _regime_from_window(win, z_thresh)
        series.append((trades[i][0], trades[i][1], regime))

    by_regime = {"BULL": [], "BEAR": [], "RANGE": [], "UNKNOWN": []}
    for _, p, r in series:
        by_regime[r].append(p)

    return {
        "window": window,
        "z_thresh": z_thresh,
        "regimes": {k: _stats(v) for k, v in by_regime.items()},
    }, series


def main() -> int:
    ap = argparse.ArgumentParser(description="Regime Split (returns-based)")
    ap.add_argument("--trades", required=True, help="Path to trades.csv")
    ap.add_argument("--window", type=int, default=30, help="Rolling window size (trades)")
    ap.add_argument("--z-thresh", type=float, default=0.3, help="Z threshold for regime classification")
    ap.add_argument("--out", default="", help="Output directory")
    args = ap.parse_args()

    trades = _read_trades_csv(Path(args.trades))
    if len(trades) < args.window + 5:
        print("ERROR: Not enough trades for regime split")
        return 1

    result, series = regime_split(trades, args.window, args.z_thresh)

    out_dir = Path(args.out) if args.out else Path(args.trades).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "regime_split.json"
    out_file.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    # Save series for inspection
    series_file = out_dir / "regime_series.csv"
    with series_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["exit_time", "profit", "regime"])
        w.writerows(series)

    print(f"[Regime Split] saved: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
