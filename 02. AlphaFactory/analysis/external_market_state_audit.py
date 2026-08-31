#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
External market-state audit for validated EA trade logs.

Joins trade exits to external D1 ATR percentile and D1 trend state derived from
separately downloaded MT5 price data, then reports by-state performance.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class TradeRow:
    entry_time: str
    exit_time: str
    side: str
    profit: float


def read_trades(path: Path) -> List[TradeRow]:
    out: List[TradeRow] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                profit = float(row.get("profit", ""))
            except Exception:
                continue
            out.append(
                TradeRow(
                    entry_time=row.get("entry_time", ""),
                    exit_time=row.get("exit_time", ""),
                    side=row.get("side", ""),
                    profit=profit,
                )
            )
    return out


def read_d1(path: Path) -> List[dict]:
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def rolling_percentile(values: List[float], idx: int, window: int) -> float:
    start = max(0, idx - window)
    sample = values[start:idx]
    if not sample:
        return 0.5
    v = values[idx]
    less_eq = sum(1 for x in sample if x <= v)
    return less_eq / len(sample)


def build_daily_states(d1_rows: List[dict], atr_window: int, ema_fast: int, ema_slow: int) -> Dict[str, dict]:
    highs = [float(r["High"]) for r in d1_rows]
    lows = [float(r["Low"]) for r in d1_rows]
    closes = [float(r["Close"]) for r in d1_rows]
    dates = [str(r["Date"])[:10] for r in d1_rows]

    trs: List[float] = []
    prev_close = None
    for h, l, c in zip(highs, lows, closes):
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c

    atrs: List[float] = []
    for i in range(len(trs)):
        start = max(0, i - atr_window + 1)
        atrs.append(sum(trs[start:i + 1]) / (i - start + 1))

    def ema(values: List[float], span: int) -> List[float]:
        alpha = 2.0 / (span + 1.0)
        out: List[float] = []
        prev = None
        for v in values:
            prev = v if prev is None else (alpha * v + (1 - alpha) * prev)
            out.append(prev)
        return out

    ema_f = ema(closes, ema_fast)
    ema_s = ema(closes, ema_slow)

    states: Dict[str, dict] = {}
    for i, d in enumerate(dates):
        atr_pct = rolling_percentile(atrs, i, 252)
        if atr_pct >= 0.67:
            vol_bucket = "HIGH_VOL"
        elif atr_pct <= 0.33:
            vol_bucket = "LOW_VOL"
        else:
            vol_bucket = "MID_VOL"

        if ema_f[i] > ema_s[i]:
            trend_bucket = "UPTREND"
        elif ema_f[i] < ema_s[i]:
            trend_bucket = "DOWNTREND"
        else:
            trend_bucket = "FLAT"

        states[d] = {
            "atr": atrs[i],
            "atr_percentile": round(atr_pct, 4),
            "vol_bucket": vol_bucket,
            "trend_bucket": trend_bucket,
            "close": closes[i],
        }
    return states


def stat_block(profits: List[float]) -> dict:
    if not profits:
        return {
            "n": 0,
            "net_profit": 0.0,
            "profit_factor": 0.0,
            "win_rate_pct": 0.0,
            "expectancy": 0.0,
        }
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = gp / gl if gl > 0 else 999.99
    return {
        "n": len(profits),
        "net_profit": round(sum(profits), 2),
        "profit_factor": round(pf, 3),
        "win_rate_pct": round(100.0 * len(wins) / len(profits), 2),
        "expectancy": round(sum(profits) / len(profits), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--d1", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--atr-window", type=int, default=14)
    ap.add_argument("--ema-fast", type=int, default=20)
    ap.add_argument("--ema-slow", type=int, default=50)
    args = ap.parse_args()

    trades = read_trades(Path(args.trades))
    d1_rows = read_d1(Path(args.d1))
    states = build_daily_states(d1_rows, args.atr_window, args.ema_fast, args.ema_slow)

    by_vol: Dict[str, List[float]] = {"LOW_VOL": [], "MID_VOL": [], "HIGH_VOL": [], "UNKNOWN": []}
    by_trend: Dict[str, List[float]] = {"UPTREND": [], "DOWNTREND": [], "FLAT": [], "UNKNOWN": []}
    cross: Dict[Tuple[str, str], List[float]] = {}
    enriched: List[dict] = []

    for t in trades:
        d = t.exit_time[:10]
        state = states.get(d)
        if not state:
            vol = "UNKNOWN"
            trend = "UNKNOWN"
            atr_pct = None
        else:
            vol = state["vol_bucket"]
            trend = state["trend_bucket"]
            atr_pct = state["atr_percentile"]
        by_vol.setdefault(vol, []).append(t.profit)
        by_trend.setdefault(trend, []).append(t.profit)
        cross.setdefault((vol, trend), []).append(t.profit)
        enriched.append({
            "entry_time": t.entry_time,
            "exit_time": t.exit_time,
            "side": t.side,
            "profit": t.profit,
            "vol_bucket": vol,
            "trend_bucket": trend,
            "atr_percentile": atr_pct,
        })

    result = {
        "label": args.label,
        "atr_window": args.atr_window,
        "ema_fast": args.ema_fast,
        "ema_slow": args.ema_slow,
        "by_vol_bucket": {k: stat_block(v) for k, v in by_vol.items()},
        "by_trend_bucket": {k: stat_block(v) for k, v in by_trend.items()},
        "by_cross_bucket": {f"{k[0]}__{k[1]}": stat_block(v) for k, v in sorted(cross.items())},
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "external_market_state_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    with (out_dir / "external_market_state_trades.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["entry_time", "exit_time", "side", "profit", "vol_bucket", "trend_bucket", "atr_percentile"])
        w.writeheader()
        w.writerows(enriched)

    print(json.dumps(result, indent=2))
    print(f"Wrote: {out_dir / 'external_market_state_summary.json'}")
    print(f"Wrote: {out_dir / 'external_market_state_trades.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
