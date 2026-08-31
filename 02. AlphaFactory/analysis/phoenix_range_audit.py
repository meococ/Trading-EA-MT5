#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phoenix_range_audit.py
======================

Attach Asian-session range features to Phoenix trades by reconstructing
daily Asian boxes from MT5 M15 history.

Why?
- A range-percentile filter failed badly.
- Before testing another filter, we need evidence on which Asian-range buckets
  actually carry edge for this specific strategy.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import MetaTrader5 as mt5

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

from quant_analyzer import parse_deals, deals_to_trades, Trade


@dataclass
class DayFeature:
    day: str
    asian_open: float
    asian_close: float
    asian_high: float
    asian_low: float
    asian_range_pts: float
    asian_dir: int
    pct_rank_20d: Optional[float]


def mt5_init() -> None:
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")


def mt5_shutdown() -> None:
    mt5.shutdown()


def pct_rank(history: List[float], value: float) -> Optional[float]:
    if len(history) < 10:
        return None
    le = sum(1 for x in history if x <= value)
    return 100.0 * le / len(history)


def build_day_features(symbol: str,
                       start_dt: datetime,
                       end_dt: datetime,
                       asian_start: int,
                       asian_end: int,
                       timeframe=mt5.TIMEFRAME_M15) -> Dict[str, DayFeature]:
    rates = mt5.copy_rates_range(symbol, timeframe, start_dt, end_dt)
    if rates is None or len(rates) == 0:
        raise SystemExit(f"No rates returned for {symbol}")

    point = mt5.symbol_info(symbol).point
    if not point or point <= 0:
        point = 0.01

    raw_days: Dict[str, List[dict]] = defaultdict(list)
    for r in rates:
        ts = datetime.fromtimestamp(int(r["time"]))
        raw_days[ts.strftime("%Y-%m-%d")].append({
            "ts": ts,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
        })

    out: Dict[str, DayFeature] = {}
    hist: List[float] = []
    for day in sorted(raw_days.keys()):
        bars = [b for b in sorted(raw_days[day], key=lambda x: x["ts"]) if asian_start <= b["ts"].hour < asian_end]
        if not bars:
            continue
        asian_open = bars[0]["open"]
        asian_close = bars[-1]["close"]
        asian_high = max(b["high"] for b in bars)
        asian_low = min(b["low"] for b in bars)
        rng = (asian_high - asian_low) / point
        direction = 1 if asian_close > asian_open else (-1 if asian_close < asian_open else 0)
        pr = pct_rank(hist[-20:], rng)
        out[day] = DayFeature(
            day=day,
            asian_open=asian_open,
            asian_close=asian_close,
            asian_high=asian_high,
            asian_low=asian_low,
            asian_range_pts=rng,
            asian_dir=direction,
            pct_rank_20d=pr,
        )
        hist.append(rng)
    return out


def bucket_name_pct(p: Optional[float]) -> str:
    if p is None:
        return "NA"
    if p < 20:
        return "0-20"
    if p < 40:
        return "20-40"
    if p < 60:
        return "40-60"
    if p < 80:
        return "60-80"
    return "80-100"


def bucket_name_range(rng: float) -> str:
    if rng < 600:
        return "<600"
    if rng < 900:
        return "600-900"
    if rng < 1200:
        return "900-1200"
    return ">=1200"


def bucket_stats(trades: Iterable[Trade]) -> Dict[str, float]:
    items = list(trades)
    wins = [t.profit for t in items if t.profit > 0]
    losses = [t.profit for t in items if t.profit < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_win / gross_loss if gross_loss > 0 else (999.99 if gross_win > 0 else 0.0)
    return {
        "n": len(items),
        "net_profit": round(sum(t.profit for t in items), 2),
        "profit_factor": round(pf, 3),
        "win_rate_pct": round((len(wins) / len(items) * 100.0) if items else 0.0, 1),
    }


def plot_bucket_charts(pct_rows: List[Dict[str, float]],
                       rng_rows: List[Dict[str, float]],
                       out_path: Path) -> None:
    if not HAS_MPL:
        return
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, rows, title in [
        (axs[0], pct_rows, "PF by Asian Range Percentile"),
        (axs[1], rng_rows, "PF by Asian Range Size"),
    ]:
        labels = [r["bucket"] for r in rows]
        vals = [r["profit_factor"] for r in rows]
        colors = ["forestgreen" if v >= 1.0 else "firebrick" for v in vals]
        ax.bar(labels, vals, color=colors)
        ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
        ax.set_title(title)
        ax.set_ylabel("PF")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Phoenix Asian range audit")
    ap.add_argument("--report", required=True)
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--asian-start", type=int, default=0)
    ap.add_argument("--asian-end", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    report = Path(args.report)
    if not report.exists():
        raise SystemExit(f"Report not found: {report}")

    out_dir = Path(args.out) if args.out else (report.parent / "range_audit")
    out_dir.mkdir(parents=True, exist_ok=True)

    deals = parse_deals(report)
    trades = sorted(deals_to_trades(deals), key=lambda t: t.entry_time)
    if not trades:
        raise SystemExit("No trades parsed")

    mt5_init()
    try:
        start_dt = trades[0].entry_time - timedelta(days=30)
        end_dt = trades[-1].exit_time + timedelta(days=2)
        features = build_day_features(args.symbol, start_dt, end_dt, args.asian_start, args.asian_end)
    finally:
        mt5_shutdown()

    pct_buckets: Dict[str, List[Trade]] = defaultdict(list)
    rng_buckets: Dict[str, List[Trade]] = defaultdict(list)
    rows = []
    missing_days = 0

    for t in trades:
        day = t.entry_time.strftime("%Y-%m-%d")
        feat = features.get(day)
        if feat is None:
            missing_days += 1
            continue
        pct_bucket = bucket_name_pct(feat.pct_rank_20d)
        rng_bucket = bucket_name_range(feat.asian_range_pts)
        pct_buckets[pct_bucket].append(t)
        rng_buckets[rng_bucket].append(t)
        rows.append({
            "entry_time": t.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": t.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "profit": round(t.profit, 2),
            "asian_range_pts": round(feat.asian_range_pts, 2),
            "pct_rank_20d": round(feat.pct_rank_20d, 2) if feat.pct_rank_20d is not None else "",
            "pct_bucket": pct_bucket,
            "range_bucket": rng_bucket,
            "asian_dir": feat.asian_dir,
        })

    pct_order = ["NA", "0-20", "20-40", "40-60", "60-80", "80-100"]
    pct_rows = []
    for b in pct_order:
        stats = bucket_stats(pct_buckets.get(b, []))
        pct_rows.append({"bucket": b, **stats})

    rng_order = ["<600", "600-900", "900-1200", ">=1200"]
    rng_rows = []
    for b in rng_order:
        stats = bucket_stats(rng_buckets.get(b, []))
        rng_rows.append({"bucket": b, **stats})

    summary = {
        "report": str(report),
        "symbol": args.symbol,
        "n_trades": len(trades),
        "n_mapped_trades": len(rows),
        "missing_day_features": missing_days,
        "best_pct_bucket": max((r for r in pct_rows if r["n"] > 0), key=lambda x: x["profit_factor"]),
        "worst_pct_bucket": min((r for r in pct_rows if r["n"] > 0), key=lambda x: x["profit_factor"]),
        "best_range_bucket": max((r for r in rng_rows if r["n"] > 0), key=lambda x: x["profit_factor"]),
        "worst_range_bucket": min((r for r in rng_rows if r["n"] > 0), key=lambda x: x["profit_factor"]),
    }

    with (out_dir / "trade_range_features.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "entry_time", "exit_time", "profit", "asian_range_pts", "pct_rank_20d",
            "pct_bucket", "range_bucket", "asian_dir"])
        wr.writeheader()
        wr.writerows(rows)

    with (out_dir / "pct_bucket_summary.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["bucket", "n", "net_profit", "profit_factor", "win_rate_pct"])
        wr.writeheader()
        wr.writerows(pct_rows)

    with (out_dir / "range_bucket_summary.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["bucket", "n", "net_profit", "profit_factor", "win_rate_pct"])
        wr.writeheader()
        wr.writerows(rng_rows)

    with (out_dir / "day_features.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["day", "asian_open", "asian_close", "asian_high", "asian_low", "asian_range_pts", "asian_dir", "pct_rank_20d"])
        for day in sorted(features.keys()):
            feat = features[day]
            wr.writerow([
                feat.day,
                round(feat.asian_open, 5),
                round(feat.asian_close, 5),
                round(feat.asian_high, 5),
                round(feat.asian_low, 5),
                round(feat.asian_range_pts, 2),
                feat.asian_dir,
                round(feat.pct_rank_20d, 2) if feat.pct_rank_20d is not None else "",
            ])

    with (out_dir / "range_audit_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    plot_bucket_charts(pct_rows, rng_rows, out_dir / "range_bucket_charts.png")

    print(json.dumps(summary, indent=2))
    print("\nWrote:")
    for name in [
        "trade_range_features.csv",
        "pct_bucket_summary.csv",
        "range_bucket_summary.csv",
        "day_features.csv",
        "range_audit_summary.json",
        "range_bucket_charts.png" if HAS_MPL else None,
    ]:
        if name:
            print(f"- {out_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
