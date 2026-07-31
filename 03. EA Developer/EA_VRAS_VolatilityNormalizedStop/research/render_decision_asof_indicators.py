#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def candles(ax, frame: pd.DataFrame, offset: int = 0) -> None:
    for i, row in enumerate(frame.itertuples(), offset):
        color = "#24a148" if row.close >= row.open else "#da1e28"
        ax.vlines(i, row.low, row.high, color=color, linewidth=0.7)
        lo, hi = sorted((row.open, row.close))
        ax.add_patch(plt.Rectangle((i - 0.32, lo), 0.64, max(hi - lo, 0.000005),
                                   facecolor=color, edgecolor=color, linewidth=0.5))


def prepare(data: Path, cases: list[dict]) -> pd.DataFrame:
    times = [pd.Timestamp(c["entry_time_utc"]) for c in cases]
    raw = pd.read_parquet(data, columns=["time_server", "open", "high", "low", "close", "tick_volume"])
    raw["time_server"] = pd.to_datetime(raw["time_server"])
    raw = raw[(raw.time_server >= min(times) - pd.Timedelta(days=20)) &
              (raw.time_server <= max(times) + pd.Timedelta(minutes=1))]
    raw = raw.set_index("time_server").sort_index()
    m5 = raw.resample("5min", label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "tick_volume": "sum"
    }).dropna()
    typical = (m5.high + m5.low + m5.close) / 3
    m5["vwap48"] = (typical * m5.tick_volume).rolling(48).sum() / m5.tick_volume.rolling(48).sum()
    prev = m5.close.shift(1)
    tr = pd.concat([m5.high - m5.low, (m5.high - prev).abs(), (m5.low - prev).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14).mean()
    h1 = raw.resample("1h", label="left", closed="left").agg({"close": "last"}).dropna()
    h1["ema200"] = h1.close.ewm(span=200, adjust=False).mean().shift(1)
    m5["h1ema"] = h1.ema200.reindex(m5.index, method="ffill")
    return m5


def render(case: dict, m5: pd.DataFrame, out: Path) -> dict:
    entry_time = pd.Timestamp(case["entry_time_utc"])
    decision = m5[m5.index < entry_time].tail(80)
    m15 = m5[m5.index < entry_time].resample("15min", label="left", closed="left").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "h1ema": "last"
    }).dropna().tail(18)
    fig, (ax, atr_ax, ctx) = plt.subplots(3, 1, figsize=(14, 10),
        gridspec_kw={"height_ratios": [4, 1, 2.2]})
    x = np.arange(len(decision))
    candles(ax, decision)
    ax.plot(x, decision.vwap48, color="#8a3ffc", linewidth=1.5, label="Rolling VWAP48 — closed M5")
    ax.plot(x, decision.h1ema, color="#0072c3", linewidth=1.5, label="EMA200 — closed H1")
    entry_x = len(decision) - 0.2
    ax.scatter([entry_x], [float(case["entry"])], marker="^" if int(case["direction"]) > 0 else "v",
               s=100, color="#161616", zorder=6, label="Entry decision")
    ax.axvline(entry_x, color="#8d8d8d", linestyle=":")
    ax.set_title(f"{case['case_id']} — DECISION AS-OF (outcome hidden, server time)")
    ax.set_ylabel("EURUSD")
    ax.legend(loc="best", fontsize=8, ncol=3)
    ax.grid(alpha=0.18)
    atr_ax.plot(x, decision.atr14 / 0.0001, color="#ff832b", label="ATR14 — closed M5")
    atr_ax.axhline(4.0, color="#8d8d8d", linestyle=":", label="Control 4-pip floor")
    atr_ax.set_ylabel("ATR pips")
    atr_ax.legend(loc="best", fontsize=8)
    atr_ax.grid(alpha=0.18)
    candles(ctx, m15, 0)
    ctx.plot(np.arange(len(m15)), m15.h1ema, color="#0072c3", linewidth=1.2, label="Closed H1 EMA200")
    center = len(m15)
    ctx.set_xlim(-0.5, 2 * len(m15) - 0.5)
    ctx.axvspan(center - 0.5, 2 * len(m15) - 0.5, color="#d9d9d9", alpha=0.6)
    ctx.text(center + len(m15) / 2, np.nanmean([m15.low.min(), m15.high.max()]), "FUTURE HIDDEN",
             ha="center", va="center", fontsize=13, color="#525252")
    ctx.scatter([center - 0.2], [float(case["entry"])], marker="o", s=60, color="#161616")
    ctx.set_title("M15 context — entry centered; no post-entry bars")
    ctx.set_ylabel("M15")
    ctx.legend(loc="best", fontsize=8)
    ctx.grid(alpha=0.18)
    ticks = np.linspace(0, len(decision) - 1, 8, dtype=int)
    atr_ax.set_xticks(ticks)
    atr_ax.set_xticklabels([decision.index[i].strftime("%m-%d\n%H:%M") for i in ticks], fontsize=8)
    ctx.set_xticks([])
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return {
        "case_id": case["case_id"], "status": "RENDERED", "mode": "asof",
        "label": "OUTCOME_HIDDEN", "direction": int(case["direction"]), "png": out.name,
        "sha256": digest(out), "entry_marker_rendered": True,
        "entry_marker_time": case["entry_time_utc"], "entry_marker_bar_time": case["entry_time_utc"],
        "cutoff_enforced": True, "outcome_hidden": True, "net_r_hidden": True,
        "label_hidden_in_image": True,
        "context": {"timeframe": "M15", "view": "asof", "entry_position": "center",
                    "future_region_hidden": True, "post_entry_outcome_region": False,
                    "post_entry_bars_drawn": 0, "decision_state_cutoff_enforced": True,
                    "note": "All plotted M5/H1 indicators stop before entry; future M15 region is hidden."},
        "note": "NON_PARITY_DIAGNOSTIC recompute from hash-bound M1 broker-server bars",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bars", type=Path, required=True)
    p.add_argument("--cases", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = list(csv.DictReader(args.cases.open(encoding="utf-8-sig")))
    m5 = prepare(args.bars, cases)
    results = []
    for case in cases:
        out = args.out / f"{case['case_id']}_decision_asof_indicators.png"
        results.append(render(case, m5, out))
    manifest = {"schema_version": "chart_case_render.v2",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bars": str(args.bars), "bars_sha256": digest(args.bars),
        "cases": str(args.cases), "cases_sha256": digest(args.cases), "mode": "asof",
        "pre_bars": 80, "post_bars": 0,
        "overlays": ["rolling_vwap48_closed_m5", "ema200_closed_h1", "atr14_closed_m5"],
        "indicator_provenance": "diagnostic_recompute_nonparity_labeled",
        "time_axis": "broker_server_time", "context_timeframe": "M15",
        "context_bars": 36, "context_entry_position": "center", "context_post_bars": 0,
        "results": results}
    (args.out / "cases_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"DECISION_ASOF_INDICATORS rendered={len(results)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
