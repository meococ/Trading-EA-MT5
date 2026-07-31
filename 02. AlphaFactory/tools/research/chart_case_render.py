#!/usr/bin/env python3
"""Render per-case candlestick images from hash-bound bar data + a case list.

Purpose: ground every chart claim in pixels rendered from the SAME bar data
the engine computed on (no broker-terminal dependency, no C-side writes).

Modes:
- asof (default): draws ONLY bars closed before the entry timestamp — the
  information set available at the decision. Entry price is marked at the
  right edge; outcome-derived label/net/exit text is hidden. Use for
  setup-quality review and labeling.
- anatomy: draws through the exit plus --post-bars. Outcome view only; never
  use anatomy images to justify entry-quality claims.

Inputs:
- --bars: parquet with a time column (--time-col, default time_utc) and
  open/high/low/close.
- --cases: CSV with columns: case_id, entry_time_utc, direction (1|-1),
  entry; optional: sl, tp, exit_time_utc, exit, reason, label.
Optional forensic context:
- --context-timeframe adds one larger-timeframe panel built from completed
  bars plus the current point-in-time partial bar. Even in anatomy mode, that
  panel stops at the entry decision so future outcome cannot leak into
  setup/context analysis.
- --context-entry-position center places the current HTF/entry candle at the
  horizontal midpoint. With --context-post-bars 0 it reserves the right half
  as FUTURE HIDDEN; positive values disclose post-entry HTF outcome bars.

Output: one PNG per case + cases_manifest.json
(schema chart_case_render.v2) with SHA256 per image and enforced cutoffs.
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

SCHEMA = "chart_case_render.v2"
CONTEXT_TIMEFRAMES = {
    "M15": ("15min", pd.Timedelta(minutes=15)),
    "H1": ("1h", pd.Timedelta(hours=1)),
    "H4": ("4h", pd.Timedelta(hours=4)),
    "D1": ("1d", pd.Timedelta(days=1)),
}


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
        partial = bool(r.get("_is_partial", False))
        color = "#1565c0" if partial else ("#2e7d32" if up else "#c62828")
        ax.vlines(i, r["low"], r["high"], color=color, linewidth=0.8)
        body_lo, body_hi = sorted((r["open"], r["close"]))
        height = max(body_hi - body_lo, 1e-12)
        ax.add_patch(
            plt.Rectangle(
                (i - 0.35, body_lo),
                0.7,
                height,
                facecolor="none" if partial else color,
                edgecolor=color,
                linewidth=1.2 if partial else 0.5,
                hatch="///" if partial else None,
            )
        )
        if bool(r.get("_is_entry_bar", False)) and pd.notna(r.get("_asof_close")):
            partial_lo, partial_hi = sorted((r["_asof_open"], r["_asof_close"]))
            ax.vlines(
                i, r["_asof_low"], r["_asof_high"], color="#1565c0",
                linewidth=1.1, zorder=6,
            )
            ax.add_patch(
                plt.Rectangle(
                    (i - 0.35, partial_lo),
                    0.7,
                    max(partial_hi - partial_lo, 1e-12),
                    facecolor="none",
                    edgecolor="#1565c0",
                    linewidth=1.3,
                    hatch="///",
                    zorder=6,
                )
            )
    ax.set_xlim(-1, len(df))
    ticks = list(x)[:: max(1, len(df) // 8)]
    ax.set_xticks(ticks)
    ax.set_xticklabels([df["_t"].iloc[i].strftime("%m-%d %H:%M") for i in ticks],
                       rotation=30, ha="right", fontsize=7)


def add_overlays(ax, df: pd.DataFrame, overlays: list[str]) -> None:
    source = (
        df.loc[~df["_is_partial"].fillna(False)].copy()
        if "_is_partial" in df.columns
        else df
    )
    for spec in overlays:
        kind, _, arg = spec.partition(":")
        period = int(arg)
        if kind == "sma":
            series = source["close"].rolling(period).mean()
        elif kind == "ema":
            series = source["close"].ewm(span=period, adjust=False).mean()
        else:
            raise SystemExit(f"unknown overlay: {spec}")
        ax.plot(source.index, series, linewidth=1.0, label=f"{kind.upper()}{period}")


def has_value(case: dict, key: str) -> bool:
    value = case.get(key)
    return value not in (None, "", "nan") and pd.notna(value)


def bar_x_at_or_after(df: pd.DataFrame, timestamp: pd.Timestamp) -> int:
    values = df["_t"].to_numpy(dtype="datetime64[ns]")
    index = int(values.searchsorted(timestamp.to_datetime64(), side="left"))
    return min(max(index, 0), len(df) - 1)


def bar_x_at_or_before(df: pd.DataFrame, timestamp: pd.Timestamp) -> int:
    values = df["_t"].to_numpy(dtype="datetime64[ns]")
    index = int(values.searchsorted(timestamp.to_datetime64(), side="right")) - 1
    return min(max(index, 0), len(df) - 1)


def build_context_window(
    bars: pd.DataFrame,
    entry_t: pd.Timestamp,
    timeframe: str,
    context_bars: int,
) -> tuple[pd.DataFrame, pd.Timedelta, dict[str, object]]:
    rule, duration = CONTEXT_TIMEFRAMES[timeframe]
    frame = (
        bars.set_index("_t")[["open", "high", "low", "close"]]
        .resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
        .reset_index()
    )
    frame["_bar_close"] = frame["_t"] + duration
    complete = frame[frame["_bar_close"] <= entry_t].copy()
    complete["_is_partial"] = False
    complete["_available_through"] = complete["_bar_close"]

    positive_deltas = bars["_t"].diff().dropna()
    positive_deltas = positive_deltas[positive_deltas > pd.Timedelta(0)]
    source_duration = positive_deltas.median() if not positive_deltas.empty else duration
    source_closed = bars[(bars["_t"] + source_duration) <= entry_t]
    bucket_start = entry_t.floor(rule)
    scheduled_close = bucket_start + duration
    partial_source = source_closed[
        (source_closed["_t"] >= bucket_start)
        & (source_closed["_t"] < scheduled_close)
    ]
    partial_included = bool(
        bucket_start < entry_t < scheduled_close and not partial_source.empty
    )
    available_through = None
    if partial_included:
        available_through = pd.Timestamp(
            (partial_source["_t"] + source_duration).max()
        )
        partial = pd.DataFrame(
            [
                {
                    "_t": bucket_start,
                    "open": float(partial_source["open"].iloc[0]),
                    "high": float(partial_source["high"].max()),
                    "low": float(partial_source["low"].min()),
                    "close": float(partial_source["close"].iloc[-1]),
                    "_bar_close": scheduled_close,
                    "_is_partial": True,
                    "_available_through": available_through,
                }
            ]
        )
        window = pd.concat(
            [complete.tail(max(1, context_bars - 1)), partial], ignore_index=True
        )
    else:
        window = complete.tail(context_bars).reset_index(drop=True)
    last_complete_close = (
        pd.Timestamp(complete["_bar_close"].iloc[-1]) if not complete.empty else None
    )
    metadata = {
        "partial_bar_included": partial_included,
        "partial_bar_start": str(bucket_start) if partial_included else None,
        "partial_available_through": str(available_through) if partial_included else None,
        "partial_scheduled_close": str(scheduled_close) if partial_included else None,
        "last_complete_bar_close": str(last_complete_close) if last_complete_close else None,
        "source_bar_duration_seconds": int(source_duration.total_seconds()),
        "cutoff_enforced": bool(
            (last_complete_close is None or last_complete_close <= entry_t)
            and (available_through is None or available_through <= entry_t)
        ),
    }
    return window.reset_index(drop=True), duration, metadata


def build_context_anatomy_window(
    bars: pd.DataFrame,
    entry_t: pd.Timestamp,
    timeframe: str,
    context_bars: int,
    context_post_bars: int,
    asof_window: pd.DataFrame,
    asof_meta: dict[str, object],
) -> tuple[pd.DataFrame, dict[str, object]]:
    rule, duration = CONTEXT_TIMEFRAMES[timeframe]
    frame = (
        bars.set_index("_t")[["open", "high", "low", "close"]]
        .resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
        .reset_index()
    )
    frame["_bar_close"] = frame["_t"] + duration
    source_duration = pd.Timedelta(seconds=int(asof_meta["source_bar_duration_seconds"]))
    data_available_through = pd.Timestamp(bars["_t"].max()) + source_duration
    frame = frame[frame["_bar_close"] <= data_available_through].reset_index(drop=True)
    bucket_start = entry_t.floor(rule)
    matches = frame.index[frame["_t"] == bucket_start].tolist()
    if not matches:
        return pd.DataFrame(), {
            "entry_bar_full_outcome": False,
            "post_entry_bars_drawn": 0,
            "first_post_entry_bar_start": None,
            "last_post_entry_bar_close": None,
        }
    entry_index = int(matches[0])
    first = max(0, entry_index - context_bars)
    last = min(len(frame), entry_index + 1 + context_post_bars)
    window = frame.iloc[first:last].copy().reset_index(drop=True)
    local_entry_index = entry_index - first
    window["_is_partial"] = False
    window["_is_entry_bar"] = False
    window["_is_post_entry"] = False
    window.loc[local_entry_index, "_is_entry_bar"] = True
    window.loc[window.index > local_entry_index, "_is_post_entry"] = True
    for column in ("open", "high", "low", "close"):
        window[f"_asof_{column}"] = float("nan")
    partial = asof_window.loc[asof_window["_is_partial"].fillna(False)]
    if not partial.empty:
        partial_row = partial.iloc[-1]
        for column in ("open", "high", "low", "close"):
            window.loc[local_entry_index, f"_asof_{column}"] = float(partial_row[column])
    future = window.loc[window["_is_post_entry"]]
    metadata = {
        "entry_index": local_entry_index,
        "entry_bar_full_outcome": True,
        "entry_bar_start": str(bucket_start),
        "entry_bar_close": str(bucket_start + duration),
        "post_entry_bars_drawn": int(len(future)),
        "first_post_entry_bar_start": (
            str(future["_t"].iloc[0]) if not future.empty else None
        ),
        "last_post_entry_bar_close": (
            str(future["_bar_close"].iloc[-1]) if not future.empty else None
        ),
    }
    return window, metadata


def context_metrics(
    frame: pd.DataFrame,
    direction: int,
    overlays: list[str],
    entry_price: float,
) -> dict[str, object]:
    if frame.empty:
        return {}
    result: dict[str, object] = {
        "last_close": float(frame["close"].iloc[-1]),
        "range_position_20": None,
        "directional_return_5": None,
        "ema_alignment": "NOT_REQUESTED",
    }
    recent = frame.tail(20)
    low = float(recent["low"].min())
    high = float(recent["high"].max())
    if high > low:
        result["range_position_20"] = float((entry_price - low) / (high - low))
    if len(frame) >= 6:
        result["directional_return_5"] = float(
            direction * (frame["close"].iloc[-1] - frame["close"].iloc[-6])
        )
    ema_periods = []
    for spec in overlays:
        kind, _, arg = spec.partition(":")
        if kind == "ema":
            ema_periods.append(int(arg))
    if len(ema_periods) >= 2:
        fast_period, slow_period = sorted(ema_periods)[:2]
        fast = float(frame["close"].ewm(span=fast_period, adjust=False).mean().iloc[-1])
        slow = float(frame["close"].ewm(span=slow_period, adjust=False).mean().iloc[-1])
        result["ema_fast"] = fast
        result["ema_slow"] = slow
        result["ema_alignment"] = (
            "ALIGNED" if direction * (fast - slow) > 0 else "OPPOSED_OR_FLAT"
        )
    return result


def trade_summary(case: dict, entry_t: pd.Timestamp, side: str, mode: str) -> str:
    lines = [
        f"{side} entry  {entry_t:%Y-%m-%d %H:%M:%S}  @ {float(case['entry']):.5f}",
    ]
    if mode == "anatomy" and has_value(case, "exit_time_utc") and has_value(case, "exit"):
        exit_t = pd.Timestamp(case["exit_time_utc"])
        hold_minutes = (exit_t - entry_t).total_seconds() / 60.0
        lines.append(
            f"EXIT        {exit_t:%Y-%m-%d %H:%M:%S}  @ {float(case['exit']):.5f}"
        )
        lines.append(f"Hold {hold_minutes:.1f} min | reason={case.get('reason', '')}")
    if has_value(case, "sl") and has_value(case, "tp"):
        lines.append(f"SL {float(case['sl']):.5f} | TP {float(case['tp']):.5f}")
    if mode == "anatomy" and case.get("label"):
        lines.append(str(case["label"]))
    return "\n".join(lines)


def draw_setup_chain(
    ax,
    window: pd.DataFrame,
    case: dict,
    entry_t: pd.Timestamp,
    entry_x: float,
    direction: int,
) -> dict[str, object]:
    required = (
        "sweep_time_utc",
        "confirmation_time_utc",
        "pivot",
        "sweep_high",
        "sweep_low",
        "sweep_close",
        "confirmation_close",
    )
    if not all(has_value(case, key) for key in required):
        return {"rendered": False, "reason": "optional setup-chain fields missing"}

    sweep_t = pd.Timestamp(case["sweep_time_utc"])
    confirmation_t = pd.Timestamp(case["confirmation_time_utc"])
    sweep_x = bar_x_at_or_before(window, sweep_t)
    confirmation_x = bar_x_at_or_before(window, confirmation_t)
    pivot = float(case["pivot"])
    sweep_high = float(case["sweep_high"])
    sweep_low = float(case["sweep_low"])
    sweep_close = float(case["sweep_close"])
    confirmation_close = float(case["confirmation_close"])
    sweep_price = sweep_low if direction > 0 else sweep_high
    sweep_bar_time = pd.Timestamp(window["_t"].iloc[sweep_x])
    confirmation_bar_time = pd.Timestamp(window["_t"].iloc[confirmation_x])
    sequence_valid = bool(sweep_t < confirmation_t < entry_t)
    reclaimed = bool(
        (direction > 0 and sweep_low < pivot and sweep_close > pivot)
        or (direction < 0 and sweep_high > pivot and sweep_close < pivot)
    )
    opposite_extreme_broken = bool(
        (direction > 0 and confirmation_close > sweep_high)
        or (direction < 0 and confirmation_close < sweep_low)
    )

    ax.hlines(
        pivot,
        max(-0.5, sweep_x - 8),
        entry_x + 0.45,
        color="#8a6d1d",
        linewidth=1.0,
        linestyle=(0, (3, 2)),
        zorder=4,
    )
    ax.plot(
        [sweep_x, confirmation_x, entry_x],
        [sweep_price, confirmation_close, float(case["entry"])],
        color="#475569",
        linewidth=0.9,
        linestyle=(0, (2, 2)),
        zorder=6,
    )
    ax.scatter(
        [sweep_x],
        [sweep_price],
        marker="D",
        s=78,
        facecolor="#f59e0b",
        edgecolor="#78350f",
        linewidth=0.8,
        zorder=9,
    )
    ax.scatter(
        [confirmation_x],
        [confirmation_close],
        marker="s",
        s=72,
        facecolor="#0f766e",
        edgecolor="#042f2e",
        linewidth=0.8,
        zorder=9,
    )
    sweep_depth = (
        f"{float(case['sweep_depth_pips']):.1f}p"
        if has_value(case, "sweep_depth_pips")
        else "?"
    )
    reclaim_size = (
        f"{float(case['sweep_reclaim_pips']):.1f}p"
        if has_value(case, "sweep_reclaim_pips")
        else "?"
    )
    body_multiple = (
        f"{float(case['confirmation_body_vs_prior20']):.2f}x"
        if has_value(case, "confirmation_body_vs_prior20")
        else "?"
    )
    close_strength = (
        f"{100.0 * float(case['confirmation_directional_close_location']):.0f}%"
        if has_value(case, "confirmation_directional_close_location")
        else "?"
    )
    lag = (
        f"{int(float(case['bars_after_sweep']))} bars"
        if has_value(case, "bars_after_sweep")
        else "?"
    )
    sweep_offset = (-72, 45) if direction < 0 else (-72, -42)
    confirmation_offset = (-118, -66) if direction < 0 else (-118, 38)
    ax.annotate(
        f"SWEEP + RECLAIM {sweep_t:%H:%M}\n"
        f"pivot {pivot:.5f} | depth {sweep_depth} | reclaim {reclaim_size}",
        xy=(sweep_x, sweep_price),
        xytext=sweep_offset,
        textcoords="offset points",
        fontsize=7.2,
        fontweight="bold",
        color="#92400e",
        arrowprops={"arrowstyle": "->", "color": "#92400e", "lw": 0.8},
        bbox={"boxstyle": "round,pad=0.22", "fc": "#fffbeb", "ec": "#f59e0b", "alpha": 0.94},
    )
    ax.annotate(
        f"CONFIRM {confirmation_t:%H:%M}\n"
        f"body {body_multiple} | dir-close {close_strength} | lag {lag}",
        xy=(confirmation_x, confirmation_close),
        xytext=confirmation_offset,
        textcoords="offset points",
        fontsize=7.2,
        fontweight="bold",
        color="#0f766e",
        arrowprops={"arrowstyle": "->", "color": "#0f766e", "lw": 0.8},
        bbox={"boxstyle": "round,pad=0.22", "fc": "#f0fdfa", "ec": "#0f766e", "alpha": 0.94},
    )
    ax.text(
        0.01,
        0.015,
        "RULE CHAIN  PIVOT -> SWEEP/RECLAIM -> CONFIRM -> ENTRY",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=7.2,
        fontweight="bold",
        color="#334155",
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#94a3b8", "alpha": 0.9},
    )
    return {
        "rendered": True,
        "sequence_valid": sequence_valid,
        "pivot_price": pivot,
        "pivot_breached_and_reclaimed": reclaimed,
        "opposite_sweep_extreme_broken_by_confirmation": opposite_extreme_broken,
        "sweep_time": str(sweep_t),
        "sweep_marker_bar_time": str(sweep_bar_time),
        "sweep_marker_price": sweep_price,
        "confirmation_time": str(confirmation_t),
        "confirmation_marker_bar_time": str(confirmation_bar_time),
        "confirmation_marker_price": confirmation_close,
        "confirmation_body_vs_prior20": (
            float(case["confirmation_body_vs_prior20"])
            if has_value(case, "confirmation_body_vs_prior20")
            else None
        ),
        "confirmation_directional_close_location": (
            float(case["confirmation_directional_close_location"])
            if has_value(case, "confirmation_directional_close_location")
            else None
        ),
        "bars_after_sweep": (
            int(float(case["bars_after_sweep"]))
            if has_value(case, "bars_after_sweep")
            else None
        ),
    }


def render_case(
    bars: pd.DataFrame,
    case: dict,
    out_dir: Path,
    mode: str,
    pre_bars: int,
    post_bars: int,
    overlays: list[str],
    context_timeframe: str | None,
    context_bars: int,
    context_overlays: list[str],
    context_entry_position: str,
    context_post_bars: int,
) -> dict:
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

    if context_timeframe:
        fig, (ax, context_ax) = plt.subplots(
            1,
            2,
            figsize=(16, 6.6),
            dpi=120,
            gridspec_kw={"width_ratios": [1.75, 1.0]},
        )
    else:
        fig, ax = plt.subplots(figsize=(11, 5.5), dpi=110)
        context_ax = None
    draw_candles(ax, window)
    if overlays:
        add_overlays(ax, window, overlays)
        ax.legend(loc="upper right", fontsize=7, framealpha=0.85)

    direction = int(case.get("direction", 0) or 0)
    side = {1: "LONG", -1: "SHORT"}.get(direction, "?")
    entry = float(case["entry"])
    ax.axhline(entry, color="#1565c0", linewidth=1.0, linestyle="--")
    if mode == "anatomy":
        entry_x = bar_x_at_or_after(window, entry_t)
        entry_marker_bar_time = str(window["_t"].iloc[int(entry_x)])
    else:
        entry_x = len(window) - 0.15
        entry_marker_bar_time = None
    entry_marker = "^" if direction > 0 else "v"
    ax.scatter(
        [entry_x], [entry], marker=entry_marker, s=110, color="#1565c0",
        edgecolor="#0d1b2a", linewidth=0.8, zorder=8,
    )
    setup_chain_result = draw_setup_chain(
        ax, window, case, entry_t, entry_x, direction
    )
    ax.annotate(
        f"ENTRY {entry_t:%m-%d %H:%M:%S}\n{entry:.5f} ({side})",
        xy=(entry_x, entry), fontsize=8, fontweight="bold", color="#1565c0",
        xytext=((12, 18) if setup_chain_result["rendered"] else (-105, 18)),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#1565c0", "lw": 0.9},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#1565c0", "alpha": 0.9},
    )
    risk_lines_rendered = {"sl": False, "tp": False}
    for key, color in (("sl", "#c62828"), ("tp", "#2e7d32")):
        val = case.get(key)
        if val not in (None, "", "nan") and pd.notna(val):
            ax.axhline(float(val), color=color, linewidth=1.0, linestyle=":")
            ax.annotate(key.upper(), xy=(0, float(val)), fontsize=8, color=color)
            risk_lines_rendered[key] = True
    exit_marker_rendered = False
    exit_marker_bar_time = None
    if mode == "anatomy" and has_value(case, "exit") and has_value(case, "exit_time_utc"):
        exit_t = pd.Timestamp(case["exit_time_utc"])
        exit_x = bar_x_at_or_before(window, exit_t)
        exit_marker_bar_time = str(window["_t"].iloc[exit_x])
        ax.axhline(float(case["exit"]), color="#6a1b9a", linewidth=0.8, linestyle="-.")
        ax.scatter(
            [exit_x], [float(case["exit"])], marker="X", s=120,
            color="#6a1b9a", edgecolor="#0d1b2a", linewidth=0.8, zorder=8,
        )
        ax.annotate(
            f"EXIT {exit_t:%m-%d %H:%M:%S}\n{float(case['exit']):.5f} | {case.get('reason', '')}",
            xy=(exit_x, float(case["exit"])), fontsize=8, fontweight="bold",
            color="#6a1b9a", xytext=(12, -34), textcoords="offset points",
            arrowprops={"arrowstyle": "->", "color": "#6a1b9a", "lw": 0.9},
            bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#6a1b9a", "alpha": 0.9},
        )
        exit_marker_rendered = True

    label = case.get("label", "")
    ax.set_title(
        f"M5 {mode} | executed trade lifecycle",
        fontsize=10,
        loc="left",
    )
    ax.grid(alpha=0.2)
    ax.text(
        0.01,
        0.99,
        trade_summary(case, entry_t, side, mode),
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=7.5,
        family="monospace",
        bbox={"boxstyle": "round,pad=0.35", "fc": "#f8fafc", "ec": "#64748b", "alpha": 0.93},
    )

    context_result = None
    if context_timeframe and context_ax is not None:
        asof_context_window, duration, context_meta = build_context_window(
            bars, entry_t, context_timeframe, context_bars
        )
        context_view = "asof"
        anatomy_meta = {
            "entry_bar_full_outcome": False,
            "post_entry_bars_drawn": 0,
            "first_post_entry_bar_start": None,
            "last_post_entry_bar_close": None,
        }
        if context_post_bars > 0:
            context_window, anatomy_meta = build_context_anatomy_window(
                bars,
                entry_t,
                context_timeframe,
                context_bars,
                context_post_bars,
                asof_context_window,
                context_meta,
            )
            context_view = "anatomy"
        else:
            context_window = asof_context_window
        if len(context_window) < 5:
            plt.close(fig)
            return {"case_id": case["case_id"], "status": "SKIP_INSUFFICIENT_CONTEXT_BARS"}
        draw_candles(context_ax, context_window)
        if context_overlays:
            add_overlays(context_ax, context_window, context_overlays)
            context_ax.legend(loc="lower right", fontsize=7, framealpha=0.85)
        context_ax.axhline(entry, color="#1565c0", linewidth=0.9, linestyle="--")
        entry_marker_on_partial = bool(context_meta["partial_bar_included"])
        context_entry_x = (
            int(anatomy_meta["entry_index"])
            if context_view == "anatomy"
            else (len(context_window) - 1 if entry_marker_on_partial else len(context_window) - 0.15)
        )
        context_ax.scatter(
            [context_entry_x], [entry], marker=entry_marker, s=95,
            color="#1565c0", edgecolor="#0d1b2a", linewidth=0.8, zorder=8,
        )
        if entry_marker_on_partial:
            entry_annotation = (
                f"ENTRY {context_timeframe} FULL CANDLE\n"
                f"blue hatch = as-of {entry_t:%H:%M:%S}\n"
                "full candle = outcome"
                if context_view == "anatomy"
                else f"CURRENT {context_timeframe} PARTIAL\nas-of {entry_t:%H:%M:%S}"
            )
            context_low = float(context_window["low"].min())
            context_high = float(context_window["high"].max())
            annotation_offset = (
                (-118, -58)
                if entry >= (context_low + context_high) / 2.0
                else (-118, 18)
            )
            context_ax.annotate(
                entry_annotation,
                xy=(context_entry_x, entry),
                xytext=annotation_offset,
                textcoords="offset points",
                fontsize=7.5,
                fontweight="bold",
                color="#1565c0",
                arrowprops={"arrowstyle": "->", "color": "#1565c0", "lw": 0.9},
                bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#1565c0", "alpha": 0.9},
            )
        future_region_hidden = False
        post_entry_outcome_region = False
        if context_entry_position == "center":
            left_limit = -1.0
            right_limit = context_entry_x + (context_entry_x - left_limit)
            future_start = context_entry_x + 0.5
            outcome_disclosed = context_view == "anatomy"
            context_ax.axvspan(
                future_start,
                right_limit,
                facecolor="#fff7ed" if outcome_disclosed else "#e2e8f0",
                edgecolor="#fb923c" if outcome_disclosed else "#94a3b8",
                hatch=None if outcome_disclosed else "..",
                alpha=0.48 if outcome_disclosed else 0.55,
                linewidth=0.0,
                zorder=-10,
            )
            context_ax.set_xlim(left_limit, right_limit)
            context_ax.text(
                (future_start + right_limit) / 2.0,
                0.50,
                "POST-ENTRY\nOUTCOME" if outcome_disclosed else "FUTURE\nHIDDEN",
                transform=context_ax.get_xaxis_transform(),
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                color="#c2410c" if outcome_disclosed else "#64748b",
                alpha=0.78,
            )
            future_region_hidden = not outcome_disclosed
            post_entry_outcome_region = outcome_disclosed
        x_left, x_right = context_ax.get_xlim()
        entry_anchor_fraction = (context_entry_x - x_left) / (x_right - x_left)
        complete_context = context_window.loc[
            context_window["_bar_close"] <= entry_t
        ].copy()
        last_complete_close = pd.Timestamp(context_meta["last_complete_bar_close"])
        metrics = context_metrics(
            complete_context, direction, context_overlays, entry
        )
        context_ax.set_title(
            (
                f"{context_timeframe} anatomy | ENTRY centered; outcome disclosed"
                if context_view == "anatomy"
                else f"{context_timeframe} context | point-in-time at ENTRY"
            ),
            fontsize=10,
            loc="left",
        )
        range_position = metrics.get("range_position_20")
        range_text = (
            f"{float(range_position):.3f}" if range_position is not None else "undefined"
        )
        context_ax.text(
            0.01,
            0.99,
            f"Decision cutoff: {entry_t:%Y-%m-%d %H:%M:%S}\n"
            f"Last closed HTF: {last_complete_close:%Y-%m-%d %H:%M:%S}\n"
            f"Current HTF partial: {'YES' if entry_marker_on_partial else 'NO'}\n"
            f"Post-entry HTF bars: {anatomy_meta['post_entry_bars_drawn']}\n"
            f"Closed-bar EMA context: {metrics.get('ema_alignment', 'NOT_REQUESTED')}\n"
            f"Entry loc vs closed 20-bar range: {range_text}",
            transform=context_ax.transAxes,
            va="top",
            ha="left",
            fontsize=7.5,
            family="monospace",
            bbox={"boxstyle": "round,pad=0.35", "fc": "#f8fafc", "ec": "#64748b", "alpha": 0.93},
        )
        context_ax.grid(alpha=0.2)
        context_result = {
            "timeframe": context_timeframe,
            "view": context_view,
            "bars_drawn": int(len(context_window)),
            "first_bar": str(context_window["_t"].iloc[0]),
            "last_bar": str(context_window["_t"].iloc[-1]),
            "last_bar_close": str(last_complete_close),
            "last_complete_bar_close": str(last_complete_close),
            "entry_cutoff": str(entry_t),
            "partial_bar_included": context_meta["partial_bar_included"],
            "partial_bar_start": context_meta["partial_bar_start"],
            "partial_available_through": context_meta["partial_available_through"],
            "partial_scheduled_close": context_meta["partial_scheduled_close"],
            "entry_marker_on_partial_bar": entry_marker_on_partial,
            "entry_bar_full_outcome": anatomy_meta["entry_bar_full_outcome"],
            "post_entry_bars_requested": context_post_bars,
            "post_entry_bars_drawn": anatomy_meta["post_entry_bars_drawn"],
            "first_post_entry_bar_start": anatomy_meta["first_post_entry_bar_start"],
            "last_post_entry_bar_close": anatomy_meta["last_post_entry_bar_close"],
            "entry_position": context_entry_position,
            "entry_anchor_fraction": round(float(entry_anchor_fraction), 6),
            "future_region_hidden": future_region_hidden,
            "post_entry_outcome_region": post_entry_outcome_region,
            "decision_state_cutoff_enforced": context_meta["cutoff_enforced"],
            "cutoff_enforced": bool(
                context_meta["cutoff_enforced"] and context_view == "asof"
            ),
            "duration_seconds": int(duration.total_seconds()),
            "source_bar_duration_seconds": context_meta["source_bar_duration_seconds"],
            "metrics": metrics,
            "note": (
                "HTF anatomy discloses the full entry candle and later HTF bars; "
                "the blue hatch preserves the as-of-entry partial state."
                if context_view == "anatomy"
                else "HTF panel is outcome-blind: completed HTF bars plus an optional "
                "hatched current HTF partial aggregated only from source bars closed by entry."
            ),
        }

    fig.suptitle(
        f"{case['case_id']} | {side} | entry {entry_t}"
        + (f" | {label}" if mode == "anatomy" and label else ""),
        fontsize=10,
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.975))
    suffix = f"_{context_timeframe.lower()}" if context_timeframe else ""
    out = out_dir / f"{case['case_id']}_{mode}{suffix}.png"
    fig.savefig(out)
    plt.close(fig)

    return {
        "case_id": case["case_id"], "status": "RENDERED", "mode": mode,
        "label": str(label),
        "direction": direction,
        "png": out.name, "sha256": sha256_file(out),
        "entry_marker_rendered": True,
        "entry_marker_time": str(entry_t),
        "entry_marker_bar_time": entry_marker_bar_time,
        "sl_line_rendered": risk_lines_rendered["sl"],
        "tp_line_rendered": risk_lines_rendered["tp"],
        "exit_marker_rendered": exit_marker_rendered,
        "exit_marker_bar_time": exit_marker_bar_time,
        "bars_drawn": int(len(window)),
        "first_bar": str(window["_t"].iloc[0]), "last_bar": str(window["_t"].iloc[-1]),
        "cutoff_enforced": bool(mode != "asof" or window["_t"].iloc[-1] < entry_t),
        "outcome_hidden": mode == "asof",
        "net_r_hidden": mode == "asof",
        "label_hidden_in_image": mode == "asof",
        "setup_chain": setup_chain_result,
        "context": context_result,
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
    ap.add_argument(
        "--context-timeframe",
        choices=tuple(CONTEXT_TIMEFRAMES),
        help="Optional larger-timeframe as-of-entry panel: M15, H1, H4 or D1",
    )
    ap.add_argument("--context-bars", type=int, default=48)
    ap.add_argument(
        "--context-entry-position",
        choices=("right", "center"),
        default="right",
        help=(
            "Place the HTF entry candle at the right edge (default) or at the "
            "horizontal center with the future region visibly hidden"
        ),
    )
    ap.add_argument(
        "--context-post-bars",
        type=int,
        default=0,
        help=(
            "Number of completed HTF bars after the entry candle to disclose. "
            "Values above zero create an explicitly outcome-bearing HTF anatomy panel."
        ),
    )
    ap.add_argument(
        "--context-overlay",
        action="append",
        default=[],
        help="sma:N or ema:N for the HTF panel, repeatable",
    )
    ap.add_argument("--max-cases", type=int, default=12)
    args = ap.parse_args()
    if args.context_bars < 5:
        raise SystemExit("--context-bars must be at least 5")
    if args.context_post_bars < 0:
        raise SystemExit("--context-post-bars must be non-negative")
    if args.context_post_bars and not args.context_timeframe:
        raise SystemExit("--context-post-bars requires --context-timeframe")
    if args.context_post_bars and args.context_entry_position != "center":
        raise SystemExit("--context-post-bars requires --context-entry-position center")

    bars = pd.read_parquet(args.bars)
    if args.time_col not in bars.columns:
        raise SystemExit(f"time column missing: {args.time_col}")
    bars = bars.sort_values(args.time_col).reset_index(drop=True)
    bars["_t"] = pd.to_datetime(bars[args.time_col])

    cases = pd.read_csv(args.cases).head(args.max_cases).to_dict("records")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    results = [render_case(bars, c, args.out_dir, args.mode,
                           args.pre_bars, args.post_bars, args.overlay,
                           args.context_timeframe, args.context_bars,
                           args.context_overlay, args.context_entry_position,
                           args.context_post_bars)
               for c in cases]
    manifest = {
        "schema_version": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bars": str(args.bars), "bars_sha256": sha256_file(args.bars),
        "time_col": args.time_col,
        "cases": str(args.cases), "cases_sha256": sha256_file(args.cases),
        "mode": args.mode, "pre_bars": args.pre_bars, "post_bars": args.post_bars,
        "overlays": args.overlay,
        "context_timeframe": args.context_timeframe,
        "context_bars": args.context_bars,
        "context_overlays": args.context_overlay,
        "context_entry_position": args.context_entry_position,
        "context_post_bars": args.context_post_bars,
        "results": results,
    }
    out = args.out_dir / "cases_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    rendered = sum(1 for r in results if r["status"] == "RENDERED")
    print(f"CHART_CASES rendered={rendered} skipped={len(results) - rendered} manifest={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
