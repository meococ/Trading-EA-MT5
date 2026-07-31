#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_trades(run: Path) -> list[dict]:
    path = next((run / "analysis" / "logs").glob("*_LifecycleTrades_*.csv"))
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    groups = defaultdict(list)
    for row in rows:
        groups[row["position_id"]].append(row)
    trades = []
    for pid, events in groups.items():
        entry = next(r for r in events if r["action"] == "OPEN")
        close = next(r for r in events if r["is_final_close"] == "1")
        direction = 1 if entry["order_type"] == "BUY" else -1
        distance = float(entry["risk_pts"]) * 0.00001
        entry_price = float(entry["price"])
        trades.append({
            "position_id": pid, "direction": direction, "side": entry["order_type"],
            "entry_time": pd.Timestamp(entry["event_time"]), "exit_time": pd.Timestamp(close["event_time"]),
            "entry": entry_price, "exit": float(close["price"]),
            "sl": entry_price - direction * distance,
            "tp": entry_price + direction * 1.5 * distance,
            "risk_pips": distance / 0.0001,
            "net": sum(float(r["deal_net"]) for r in events),
        })
    return trades


def prepare_bars(data_path: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    raw = pd.read_parquet(data_path, columns=["time_server", "open", "high", "low", "close", "tick_volume"])
    raw["time_server"] = pd.to_datetime(raw["time_server"])
    raw = raw[(raw["time_server"] >= start - pd.Timedelta(days=20)) & (raw["time_server"] <= end + pd.Timedelta(hours=6))]
    raw = raw.set_index("time_server").sort_index()
    m5 = raw.resample("5min", label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "tick_volume": "sum"
    }).dropna()
    typical = (m5.high + m5.low + m5.close) / 3.0
    m5["vwap48"] = (typical * m5.tick_volume).rolling(48).sum() / m5.tick_volume.rolling(48).sum()
    prev_close = m5.close.shift(1)
    tr = pd.concat([(m5.high - m5.low), (m5.high - prev_close).abs(), (m5.low - prev_close).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14).mean()
    h1 = raw.resample("1h", label="left", closed="left").agg({"close": "last"}).dropna()
    h1["ema200_closed"] = h1.close.ewm(span=200, adjust=False).mean().shift(1)
    m5["h1_ema200_closed"] = h1.ema200_closed.reindex(m5.index, method="ffill")
    return m5


def render(case: dict, bars: pd.DataFrame, title: str, out: Path) -> None:
    view = bars.loc[case["entry_time"] - pd.Timedelta(hours=4):case["exit_time"] + pd.Timedelta(hours=3)].copy()
    x = np.arange(len(view))
    fig, (ax, atr_ax) = plt.subplots(2, 1, figsize=(15, 8.5), sharex=True, gridspec_kw={"height_ratios": [4, 1]})
    for i, row in enumerate(view.itertuples()):
        color = "#24a148" if row.close >= row.open else "#da1e28"
        ax.vlines(i, row.low, row.high, color=color, linewidth=0.8)
        body_low, body_high = sorted((row.open, row.close))
        ax.add_patch(plt.Rectangle((i - 0.34, body_low), 0.68, max(body_high - body_low, 0.000005),
                                   facecolor=color, edgecolor=color, linewidth=0.6))
    ax.plot(x, view.vwap48, color="#8a3ffc", linewidth=1.5, label="Rolling VWAP 48 (closed M5)")
    ax.plot(x, view.h1_ema200_closed, color="#0072c3", linewidth=1.5, label="Closed H1 EMA200")
    entry_x = int(np.searchsorted(view.index.values, np.datetime64(case["entry_time"])))
    exit_x = int(np.searchsorted(view.index.values, np.datetime64(case["exit_time"])))
    ax.axhline(case["entry"], color="#161616", linestyle="--", linewidth=1.0, label="Entry")
    ax.axhline(case["sl"], color="#da1e28", linestyle="--", linewidth=1.2, label=f"Initial SL ({case['risk_pips']:.1f} pip)")
    ax.axhline(case["tp"], color="#198038", linestyle="--", linewidth=1.2, label="TP 1.5R")
    ax.scatter([entry_x], [case["entry"]], marker="^" if case["direction"] > 0 else "v", s=90, color="#161616", zorder=5)
    ax.scatter([exit_x], [case["exit"]], marker="X", s=80, color="#fa4d56", zorder=5, label="Exit")
    ax.axvspan(entry_x, exit_x, color="#f1c21b", alpha=0.08)
    ax.set_title(title)
    ax.set_ylabel("EURUSD")
    ax.grid(alpha=0.18)
    ax.legend(loc="best", ncol=2, fontsize=9)
    atr_ax.plot(x, view.atr14 / 0.0001, color="#ff832b", linewidth=1.4, label="ATR14 (pips)")
    atr_ax.axhline(4.0, color="#8d8d8d", linestyle=":", linewidth=1.0, label="Control min 4 pip")
    atr_ax.set_ylabel("ATR pips")
    atr_ax.grid(alpha=0.18)
    atr_ax.legend(loc="best", fontsize=8)
    ticks = np.linspace(0, len(view) - 1, min(10, len(view)), dtype=int)
    atr_ax.set_xticks(ticks)
    atr_ax.set_xticklabels([view.index[i].strftime("%m-%d\n%H:%M") for i in ticks], fontsize=8)
    fig.suptitle(f"{case['side']} position {case['position_id']} | net USD {case['net']:.2f} | actual broker-server time", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--control", type=Path, required=True)
    p.add_argument("--challenger", type=Path, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    selected = []
    for arm, run in (("control", args.control), ("challenger", args.challenger)):
        trades = load_trades(run)
        selected.extend([(arm, "best", max(trades, key=lambda t: t["net"])),
                         (arm, "worst", min(trades, key=lambda t: t["net"]))])
    start = min(case["entry_time"] for _, _, case in selected)
    end = max(case["exit_time"] for _, _, case in selected)
    bars = prepare_bars(args.data, start, end)
    manifest = {"schema_version": "vras_hyp006_chart_anatomy.v1", "hypothesis_id": "HYP-VRAS-EURUSD-M5-006",
                "data_path": str(args.data), "data_sha256": sha(args.data), "cases": []}
    for arm, label, case in selected:
        name = f"HYP006_{arm}_{label}_P{case['position_id']}.png"
        out = args.out / name
        render(case, bars, f"HYP006 {arm.upper()} {label.upper()} — indicators and trade geometry", out)
        manifest["cases"].append({**case, "entry_time": str(case["entry_time"]), "exit_time": str(case["exit_time"]),
                                  "arm": arm, "label": label, "image": name, "image_sha256": sha(out)})
    (args.out / "cases_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
