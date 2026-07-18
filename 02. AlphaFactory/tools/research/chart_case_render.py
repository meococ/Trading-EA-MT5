#!/usr/bin/env python3
"""Render per-case candlestick images from hash-bound bar data + a case list.

Purpose: ground every chart claim in pixels rendered from the SAME bar data
the engine computed on (no broker-terminal dependency, no C-side writes).

Modes:
- asof (default): draws ONLY bars closed before the entry timestamp — the
  information set available at the decision. Entry price is marked at the
  right edge. Use for setup-quality review and labeling.
- anatomy: draws through the exit plus --post-bars. Outcome view only; never
  use anatomy images to justify entry-quality claims.

Inputs:
- --bars: parquet with a time column (--time-col, default time_utc) and
  open/high/low/close.
- --cases: CSV with columns: case_id, entry_time_utc, direction (1|-1),
  entry; optional: sl, tp, exit_time_utc, exit, reason, label.
Output: one PNG per case + cases_manifest.json
(schema chart_case_render.v1) with SHA256 per image and the enforced cutoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SCHEMA = "chart_case_render.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def draw_candles(ax, df: pd.DataFrame) -> None:
    x = range(len(df))
    for i, (_, r) in enumerate(df.iterrows()):
        up = r["close"] >= r["open"]
        color = "#2e7d32" if up else "#c62828"
        ax.vlines(i, r["low"], r["high"], color=color, linewidth=0.8)
        body_lo, body_hi = sorted((r["open"], r["close"]))
        height = max(body_hi - body_lo, 1e-12)
        ax.add_patch(plt.Rectangle((i - 0.35, body_lo), 0.7, height,
                                   facecolor=color, edgecolor=color, linewidth=0.5))
    ax.set_xlim(-1, len(df))
    ticks = list(x)[:: max(1, len(df) // 8)]
    ax.set_xticks(ticks)
    ax.set_xticklabels([df["_t"].iloc[i].strftime("%m-%d %H:%M") for i in ticks],
                       rotation=30, ha="right", fontsize=7)


def add_overlays(ax, df: pd.DataFrame, overlays: list[str]) -> None:
    for spec in overlays:
        kind, _, arg = spec.partition(":")
        period = int(arg)
        if kind == "sma":
            series = df["close"].rolling(period).mean()
        elif kind == "ema":
            series = df["close"].ewm(span=period, adjust=False).mean()
        else:
            raise SystemExit(f"unknown overlay: {spec}")
        ax.plot(range(len(df)), series, linewidth=1.0, label=f"{kind.upper()}{period}")


def render_case(bars: pd.DataFrame, case: dict, out_dir: Path, mode: str,
                pre_bars: int, post_bars: int, overlays: list[str]) -> dict:
    entry_t = pd.Timestamp(case["entry_time_utc"])
    closed = bars[bars["_t"] < entry_t]
    if len(closed) < 5:
        return {"case_id": case["case_id"], "status": "SKIP_INSUFFICIENT_BARS"}
    start = max(0, len(closed) - pre_bars)
    if mode == "asof":
        window = closed.iloc[start:]
        cutoff_note = "asof: no bar at/after entry time is drawn"
    else:
        exit_t = pd.Timestamp(case["exit_time_utc"]) if case.get("exit_time_utc") else entry_t
        after = bars[bars["_t"] >= entry_t]
        upto = after[after["_t"] <= exit_t]
        post = after[after["_t"] > exit_t].head(post_bars)
        window = pd.concat([closed.iloc[start:], upto, post])
        cutoff_note = "anatomy: outcome view, not entry-quality evidence"
    window = window.reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=110)
    draw_candles(ax, window)
    if overlays:
        add_overlays(ax, window, overlays)
        ax.legend(loc="upper left", fontsize=7)

    direction = int(case.get("direction", 0) or 0)
    side = {1: "LONG", -1: "SHORT"}.get(direction, "?")
    entry = float(case["entry"])
    ax.axhline(entry, color="#1565c0", linewidth=1.0, linestyle="--")
    ax.annotate(f"entry {entry:.5f} ({side})", xy=(len(window) - 1, entry),
                fontsize=8, color="#1565c0", xytext=(-120, 8),
                textcoords="offset points")
    for key, color in (("sl", "#c62828"), ("tp", "#2e7d32")):
        val = case.get(key)
        if val not in (None, "", "nan") and pd.notna(val):
            ax.axhline(float(val), color=color, linewidth=1.0, linestyle=":")
            ax.annotate(key.upper(), xy=(0, float(val)), fontsize=8, color=color)
    if mode == "anatomy" and case.get("exit") not in (None, "", "nan") and pd.notna(case.get("exit")):
        ax.axhline(float(case["exit"]), color="#6a1b9a", linewidth=0.8, linestyle="-.")
        ax.annotate(f"exit ({case.get('reason', '')})", xy=(len(window) - 1, float(case["exit"])),
                    fontsize=8, color="#6a1b9a", xytext=(-90, -12), textcoords="offset points")

    label = case.get("label", "")
    ax.set_title(f"{case['case_id']} | {side} @ {entry_t} | mode={mode}"
                 + (f" | {label}" if label else ""), fontsize=9)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    out = out_dir / f"{case['case_id']}_{mode}.png"
    fig.savefig(out)
    plt.close(fig)

    return {
        "case_id": case["case_id"], "status": "RENDERED", "mode": mode,
        "png": out.name, "sha256": sha256_file(out),
        "bars_drawn": int(len(window)),
        "first_bar": str(window["_t"].iloc[0]), "last_bar": str(window["_t"].iloc[-1]),
        "cutoff_enforced": bool(mode != "asof" or window["_t"].iloc[-1] < entry_t),
        "note": cutoff_note,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bars", required=True, type=Path)
    ap.add_argument("--time-col", default="time_utc")
    ap.add_argument("--cases", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--mode", choices=("asof", "anatomy"), default="asof")
    ap.add_argument("--pre-bars", type=int, default=120)
    ap.add_argument("--post-bars", type=int, default=40)
    ap.add_argument("--overlay", action="append", default=[],
                    help="sma:N or ema:N, repeatable")
    ap.add_argument("--max-cases", type=int, default=12)
    args = ap.parse_args()

    bars = pd.read_parquet(args.bars)
    if args.time_col not in bars.columns:
        raise SystemExit(f"time column missing: {args.time_col}")
    bars = bars.sort_values(args.time_col).reset_index(drop=True)
    bars["_t"] = pd.to_datetime(bars[args.time_col])

    cases = pd.read_csv(args.cases).head(args.max_cases).to_dict("records")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    results = [render_case(bars, c, args.out_dir, args.mode,
                           args.pre_bars, args.post_bars, args.overlay)
               for c in cases]
    manifest = {
        "schema_version": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bars": str(args.bars), "bars_sha256": sha256_file(args.bars),
        "cases": str(args.cases), "cases_sha256": sha256_file(args.cases),
        "mode": args.mode, "pre_bars": args.pre_bars, "post_bars": args.post_bars,
        "overlays": args.overlay, "results": results,
    }
    out = args.out_dir / "cases_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    rendered = sum(1 for r in results if r["status"] == "RENDERED")
    print(f"CHART_CASES rendered={rendered} skipped={len(results) - rendered} manifest={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
