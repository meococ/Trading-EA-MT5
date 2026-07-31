#!/usr/bin/env python3
"""Render one VRAS trade with the active indicator surface visible.

The continuous series are reconstructed from the hash-bound FivePercent M1
bars using the parity-proven MT5 indicator functions.  The renderer fails if
the reconstructed entry snapshot does not match exact MT5 decision telemetry.
It writes a new indicator-rich artifact and never overwrites the Grok-bound
ten-chart casebook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_RegimeAdaptiveScalperV3" / "20260722_103759"
LOGS = RUN / "logs"
BARS = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_10"
CASES = EVIDENCE / "cases_selected_10.csv"
OUTPUT = EVIDENCE / "indicator_rich_v2"
TELEMETRY = next(LOGS.glob("*DecisionTelemetry*.csv"))

sys.path.insert(0, str(ROOT / "02. AlphaFactory" / "tools" / "research"))
from indicators import adx_mt5, atr_mt5, rsi_wilder  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def resample(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (
        frame.set_index("time_server")
        .sort_index()
        .resample(rule, label="left", closed="left")
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            tick_volume=("tick_volume", "sum"),
        )
        .dropna(subset=["open", "high", "low", "close"])
    )


def running_weighted_stats(frame: pd.DataFrame, anchor: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    selected = frame[frame.index >= anchor]
    typical = (selected["high"] + selected["low"] + selected["close"]) / 3.0
    weight = selected["tick_volume"].astype(float)
    total_weight = weight.cumsum()
    mean = (typical * weight).cumsum() / total_weight
    second = (typical.pow(2) * weight).cumsum() / total_weight
    sd = (second - mean.pow(2)).clip(lower=0.0).pow(0.5)
    return mean, sd


def draw_candles(ax: plt.Axes, bars: pd.DataFrame) -> None:
    for index, (_, row) in enumerate(bars.iterrows()):
        up = row["close"] >= row["open"]
        color = "#089981" if up else "#f23645"
        ax.vlines(index, row["low"], row["high"], color=color, linewidth=0.8, zorder=2)
        bottom = min(row["open"], row["close"])
        height = max(abs(row["close"] - row["open"]), 1e-7)
        ax.add_patch(Rectangle((index - 0.34, bottom), 0.68, height, facecolor=color, edgecolor=color, alpha=0.95, zorder=3))


def xlabels(ax: plt.Axes, bars: pd.DataFrame, count: int = 10) -> None:
    ticks = np.unique(np.linspace(0, len(bars) - 1, min(count, len(bars))).astype(int))
    ax.set_xticks(ticks)
    ax.set_xticklabels([bars.index[i].strftime("%m-%d\n%H:%M") for i in ticks], fontsize=8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", default="VRAS-003-C07-P74")
    parser.add_argument("--cases-file", type=Path, default=CASES)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    args.cases_file = args.cases_file.resolve()
    args.output_dir = args.output_dir.resolve()

    cases = pd.read_csv(args.cases_file)
    selected = cases[cases["case_id"].eq(args.case_id)]
    if len(selected) != 1:
        raise SystemExit(f"Expected one selected case for {args.case_id}, found {len(selected)}")
    case = selected.iloc[0]
    entry_server = pd.Timestamp(case["entry_time_server"])
    exit_server = pd.Timestamp(case["exit_time_server"])
    case_kind = str(case.get("case_kind", "TRADE"))
    telemetry_status = str(case.get("telemetry_status", "ORDER_ACCEPTED"))
    is_trade = case_kind == "TRADE"

    telemetry = pd.read_csv(TELEMETRY)
    telemetry["server_time"] = pd.to_datetime(telemetry["server_time"])
    exact_rows = telemetry[
        telemetry["server_time"].eq(entry_server) & telemetry["status"].eq(telemetry_status)
    ]
    if len(exact_rows) != 1:
        raise RuntimeError(f"Exact {telemetry_status} telemetry row not found")
    exact = exact_rows.iloc[0]

    load_start = entry_server - pd.Timedelta(days=12)
    load_end = exit_server + pd.Timedelta(hours=3)
    minute = pd.read_parquet(
        BARS,
        columns=["time_server", "open", "high", "low", "close", "tick_volume"],
        filters=[("time_server", ">=", load_start), ("time_server", "<=", load_end)],
    )
    minute["time_server"] = pd.to_datetime(minute["time_server"])
    m5 = resample(minute, "5min")
    m15 = resample(minute, "15min")
    m5["atr14"] = atr_mt5(m5, 14)
    m5["adx14"] = adx_mt5(m5, 14)
    m5["rsi14"] = rsi_wilder(m5["close"], 14)

    offset = entry_server - pd.Timestamp(exact["utc_time"])
    session_anchor_server = pd.Timestamp(exact["session_anchor_utc"]) + offset
    avwap_anchor_server = pd.Timestamp(exact["avwap_anchor_server"])
    is_trend = int(exact["regime"]) == 1

    session_vwap, session_sd = running_weighted_stats(m5, session_anchor_server)
    equal = m5[m5.index >= session_anchor_server]
    equal_typical = (equal["high"] + equal["low"] + equal["close"]) / 3.0
    shadow_vwap = equal_typical.expanding().mean()
    if is_trend:
        avwap, _ = running_weighted_stats(m5, avwap_anchor_server)
    else:
        avwap = pd.Series(np.nan, index=m5.index, dtype=float)
    m15_vwap, _ = running_weighted_stats(m15, session_anchor_server)

    decision_bar = entry_server - pd.Timedelta(minutes=5)
    # MT5 CopyRates(PERIOD_M15, shift=1) reads the last fully closed M15 bar.
    # Entries may occur on any M5 boundary, not only an M15 boundary.
    m15_decision_bar = entry_server.floor("15min") - pd.Timedelta(minutes=15)
    recomputed = {
        "adx": float(m5.loc[decision_bar, "adx14"]),
        "atr": float(m5.loc[decision_bar, "atr14"]),
        "rsi": float(m5.loc[decision_bar, "rsi14"]),
        "session_vwap": float(session_vwap.loc[decision_bar]),
        "session_sd": float(session_sd.loc[decision_bar]),
        "shadow_vwap": float(shadow_vwap.loc[decision_bar]),
        "anchored_vwap": float(avwap.loc[decision_bar]) if is_trend else 0.0,
        "m15_close": float(m15.loc[m15_decision_bar, "close"]) if is_trend else 0.0,
        "m15_vwap": float(m15_vwap.loc[m15_decision_bar]) if is_trend else 0.0,
    }
    tolerances = {
        "adx": 1e-5,
        "atr": 5.1e-6,
        "rsi": 1e-5,
        "session_vwap": 5.1e-6,
        "session_sd": 5.1e-6,
        "shadow_vwap": 5.1e-6,
        "anchored_vwap": 5.1e-6,
        "m15_close": 5.1e-6,
        "m15_vwap": 5.1e-6,
    }
    parity: dict[str, dict] = {}
    for key, value in recomputed.items():
        mt5_value = float(exact[key])
        delta = abs(value - mt5_value)
        passed = delta <= tolerances[key]
        parity[key] = {
            "recomputed": value,
            "mt5_telemetry": mt5_value,
            "absolute_delta": delta,
            "tolerance": tolerances[key],
            "pass": passed,
        }
        if not passed:
            raise RuntimeError(f"Entry parity failed for {key}: {parity[key]}")

    plot_start = session_anchor_server - pd.Timedelta(minutes=30)
    plot_end = exit_server.ceil("5min") + pd.Timedelta(minutes=45)
    view = m5[(m5.index >= plot_start) & (m5.index <= plot_end)].copy()
    if view.empty:
        raise RuntimeError("No chart bars in requested view")
    view["session_vwap"] = session_vwap.reindex(view.index)
    view["session_sd"] = session_sd.reindex(view.index)
    view["shadow_vwap"] = shadow_vwap.reindex(view.index)
    view["avwap"] = avwap.reindex(view.index)
    view["upper2"] = view["session_vwap"] + 2.0 * view["session_sd"]
    view["lower2"] = view["session_vwap"] - 2.0 * view["session_sd"]
    view["upper1"] = view["session_vwap"] + view["session_sd"]
    view["lower1"] = view["session_vwap"] - view["session_sd"]

    x = np.arange(len(view))
    entry_x = int(np.searchsorted(view.index.values, entry_server.to_datetime64(), side="left"))
    exit_bar = exit_server.floor("5min")
    exit_x = int(np.searchsorted(view.index.values, exit_bar.to_datetime64(), side="left"))
    entry_indicator_x = max(0, entry_x - 1)

    fig = plt.figure(figsize=(20, 13))
    grid = fig.add_gridspec(4, 2, height_ratios=[2.2, 2.2, 1.1, 1.1], hspace=0.22, wspace=0.12)
    ax_price = fig.add_subplot(grid[0:2, :])
    ax_adx = fig.add_subplot(grid[2, 0], sharex=ax_price)
    ax_rsi = fig.add_subplot(grid[2, 1], sharex=ax_price)
    ax_vol = fig.add_subplot(grid[3, 0], sharex=ax_price)
    ax_bias = fig.add_subplot(grid[3, 1], sharex=ax_price)

    draw_candles(ax_price, view)
    ax_price.plot(x, view["session_vwap"], color="#1479ff", linewidth=1.8, label="Session VWAP (tick-volume)")
    ax_price.plot(x, view["upper2"], color="#8e44ad", linewidth=1.0, linestyle="--", label="VWAP +2SD")
    ax_price.plot(x, view["lower2"], color="#8e44ad", linewidth=1.0, linestyle="--", label="VWAP -2SD")
    ax_price.fill_between(x, view["lower1"].to_numpy(float), view["upper1"].to_numpy(float), color="#3498db", alpha=0.08, label="VWAP +/-1SD")
    ax_price.plot(x, view["shadow_vwap"], color="#7f8c8d", linewidth=1.1, linestyle=":", label="Shadow equal-weight VWAP")
    if is_trend:
        ax_price.plot(x, view["avwap"], color="#f39c12", linewidth=1.8, linestyle="-.", label="Confirmed anchored VWAP")
    ax_price.axhline(float(case["stop_price"]), color="#e74c3c", linestyle="--", linewidth=1.3, label="Initial SL" if is_trade else "Proposed SL")
    ax_price.axhline(float(case["target_price"]), color="#27ae60", linestyle="--", linewidth=1.3, label="Planned TP" if is_trade else "Proposed TP")
    ax_price.axvspan(entry_x, exit_x, color="#f1c40f", alpha=0.10, label="Held interval" if is_trade else "Post-reject observation")
    ax_price.axvline(entry_x, color="#2c3e50", linewidth=1.4)
    ax_price.scatter(entry_x, float(case["entry_price"]), marker="v" if int(case["direction"]) < 0 else "^", s=150, color="#2c3e50", zorder=8, label="Entry" if is_trade else "Rejected candidate")
    if is_trade:
        ax_price.scatter(exit_x, float(case["exit_price"]), marker="X", s=130, color="#f39c12", edgecolor="black", zorder=8, label="Actual exit")
    ax_price.set_ylabel("EURUSD bid")
    ax_price.set_title("PRICE + ACTIVE VWAP SURFACE (continuous, parity checked at entry)", fontsize=13, weight="bold")
    ax_price.grid(alpha=0.18)
    ax_price.legend(loc="upper left", fontsize=8, ncol=4)

    ax_adx.plot(x, view["adx14"], color="#8e44ad", linewidth=1.8, label="ADX14 MT5")
    ax_adx.axhline(25.0, color="#27ae60", linestyle="--", label="Trend enter 25")
    ax_adx.axhline(19.0, color="#e74c3c", linestyle="--", label="Trend exit 19")
    ax_adx.fill_between(x, 19.0, 25.0, color="#f1c40f", alpha=0.12, label="Hysteresis band")
    ax_adx.scatter(entry_indicator_x, recomputed["adx"], color="black", s=45, zorder=5)
    ax_adx.set_ylim(0, max(55, float(np.nanmax(view["adx14"])) + 5))
    ax_adx.set_title(f"ADX14 — entry {recomputed['adx']:.2f}, regime={exact['regime']} TREND", fontsize=10, weight="bold")
    ax_adx.legend(fontsize=7, ncol=2)
    ax_adx.grid(alpha=0.2)

    ax_rsi.plot(x, view["rsi14"], color="#2980b9", linewidth=1.8, label="RSI14 MT5")
    ax_rsi.axhline(75.0, color="#e74c3c", linestyle="--", label="Range short ceiling 75")
    ax_rsi.axhline(25.0, color="#27ae60", linestyle="--", label="Range long floor 25")
    ax_rsi.axhline(50.0, color="#7f8c8d", linestyle=":")
    ax_rsi.scatter(entry_indicator_x, recomputed["rsi"], color="black", s=45, zorder=5)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_title(f"RSI14 — entry {recomputed['rsi']:.2f}; telemetry-only in TREND mode", fontsize=10, weight="bold")
    ax_rsi.legend(fontsize=7, ncol=2)
    ax_rsi.grid(alpha=0.2)

    atr_pips = view["atr14"] / 0.0001
    sd_pips = view["session_sd"] / 0.0001
    ax_vol.plot(x, atr_pips, color="#d35400", linewidth=1.8, label="ATR14 (pips)")
    ax_vol.plot(x, sd_pips, color="#8e44ad", linewidth=1.4, label="Session SD (pips)")
    ax_vol.plot(x, 0.30 * atr_pips, color="#7f8c8d", linestyle="--", linewidth=1.0, label="SD floor = 0.30 ATR")
    ax_vol.scatter(entry_indicator_x, recomputed["atr"] / 0.0001, color="black", s=45, zorder=5)
    ax_vol.set_title(f"VOLATILITY — entry ATR={recomputed['atr']/0.0001:.2f}p, session SD={recomputed['session_sd']/0.0001:.2f}p", fontsize=10, weight="bold")
    ax_vol.set_ylabel("pips")
    ax_vol.legend(fontsize=7, ncol=3)
    ax_vol.grid(alpha=0.2)

    if is_trend:
        m5_decision_time = view.index + pd.Timedelta(minutes=5)
        session_gap = (view["close"] - view["session_vwap"]) / 0.0001
        avwap_gap = (view["close"] - view["avwap"]) / 0.0001
        ax_bias.plot(x, session_gap, color="#1479ff", linewidth=1.4, label="M5 close - session VWAP")
        ax_bias.plot(x, avwap_gap, color="#f39c12", linewidth=1.4, label="M5 close - AVWAP")
        m15_gap = ((m15["close"] - m15_vwap) / 0.0001).dropna()
        m15_decisions = m15_gap.index + pd.Timedelta(minutes=15)
        m15_x = np.searchsorted(m5_decision_time.values, m15_decisions.values, side="left")
        valid = (m15_x >= 0) & (m15_x < len(view)) & (m15_decisions >= m5_decision_time.min()) & (m15_decisions <= m5_decision_time.max())
        ax_bias.step(m15_x[valid], m15_gap.to_numpy()[valid], where="post", color="#9b59b6", linewidth=1.6, label="M15 close - M15 VWAP")
        ax_bias.axhline(0.0, color="black", linestyle="--", linewidth=1.0, label="Direction gate zero")
        ax_bias.scatter(entry_indicator_x, (recomputed["m15_close"] - recomputed["m15_vwap"]) / 0.0001, color="black", s=45, zorder=5)
        direction_word = "long" if int(case["direction"]) > 0 else "short"
        ax_bias.set_title(f"VWAP BIAS DISTANCE — {direction_word} direction gate", fontsize=10, weight="bold")
        ax_bias.set_ylabel("pips")
        ax_bias.legend(fontsize=7, ncol=2)
    else:
        zscore = (view["close"] - view["session_vwap"]) / view["session_sd"].replace(0.0, np.nan)
        ax_bias.plot(x, zscore, color="#8e44ad", linewidth=1.7, label="Close location in session SD")
        ax_bias.axhline(2.0, color="#e74c3c", linestyle="--", label="Range short location +2SD")
        ax_bias.axhline(-2.0, color="#27ae60", linestyle="--", label="Range long location -2SD")
        ax_bias.axhline(0.0, color="black", linestyle=":", linewidth=1.0, label="Session VWAP")
        entry_z = (float(view.iloc[entry_indicator_x]["close"]) - recomputed["session_vwap"]) / recomputed["session_sd"]
        ax_bias.scatter(entry_indicator_x, entry_z, color="black", s=45, zorder=5)
        ax_bias.set_title("RANGE LOCATION — AVWAP and M15 bias are dormant", fontsize=10, weight="bold")
        ax_bias.set_ylabel("SD units")
        ax_bias.legend(fontsize=7, ncol=2)
    ax_bias.grid(alpha=0.2)

    for ax in (ax_adx, ax_rsi, ax_vol, ax_bias):
        ax.axvline(entry_x, color="#2c3e50", linewidth=1.1, alpha=0.8)
        ax.axvline(exit_x, color="#f39c12", linewidth=1.0, alpha=0.7)
    for ax in (ax_price, ax_adx, ax_rsi):
        ax.tick_params(labelbottom=False)
    xlabels(ax_vol, view)
    xlabels(ax_bias, view)
    ax_price.set_xlim(-1, len(view))

    parity_label = "ENTRY PARITY PASS 9/9"
    outcome_label = (
        f"exit {exit_server} | net {float(case['net_R']):+.3f}R / ${float(case['net_usd']):+.2f} | {case['exit_class']}"
        if is_trade
        else f"status {telemetry_status} | NOT TRADED | observation ends {exit_server}"
    )
    footer = (
        f"{case['case_id']} | {case['event']} | decision server {entry_server} | {outcome_label} | {parity_label}\n"
        f"Exact MT5 entry telemetry: ADX={float(exact['adx']):.6f}, ATR={float(exact['atr']):.5f}, RSI={float(exact['rsi']):.6f}, "
        f"VWAP={float(exact['session_vwap']):.5f}, SD={float(exact['session_sd']):.5f}, AVWAP={float(exact['anchored_vwap']):.5f}, "
        f"M15 close/VWAP={float(exact['m15_close']):.5f}/{float(exact['m15_vwap']):.5f}, spread={float(exact['spread_pips']):.2f}p, est cost={float(exact['estimated_cost_pips']):.2f}p.\n"
        "Continuous series: D-side M1 -> broker-server M5/M15; indicators use parity-proven MT5 formulas. "
        "Lines are diagnostic outside entry; exact entry snapshot is telemetry-bound. Outcome-aware anatomy, not blinded evidence."
    )
    title_kind = "TRADE OVERVIEW" if is_trade else "REJECTED-CANDIDATE DIAGNOSTIC"
    fig.suptitle(f"VRAS INDICATOR-RICH {title_kind} — {case['case_id']}", fontsize=17, weight="bold", y=0.99)
    fig.text(0.012, 0.012, footer, fontsize=8.7, family="monospace", va="bottom")
    fig.subplots_adjust(top=0.95, bottom=0.115, left=0.055, right=0.985)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    image = args.output_dir / f"{case['case_id']}_indicator_rich.png"
    fig.savefig(image, dpi=180, facecolor="white")
    plt.close(fig)

    manifest = {
        "schema_version": "vras_indicator_rich_case.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_id": case["case_id"],
        "position_id": int(case["position_id"]),
        "case_kind": case_kind,
        "telemetry_status": telemetry_status,
        "image": str(image.relative_to(ROOT)).replace("\\", "/"),
        "image_sha256": sha256(image),
        "image_bytes": image.stat().st_size,
        "source_m1": str(BARS.relative_to(ROOT)).replace("\\", "/"),
        "source_m1_sha256": sha256(BARS),
        "telemetry": str(TELEMETRY.relative_to(ROOT)).replace("\\", "/"),
        "telemetry_sha256": sha256(TELEMETRY),
        "time_axis": "broker_server_time",
        "continuous_series": [
            "session_vwap_tick_weighted",
            "session_sd_tick_weighted",
            "shadow_vwap_equal_weighted",
            "confirmed_anchored_vwap",
            "adx14_mt5",
            "atr14_mt5",
            "rsi14_mt5",
            "m15_close_minus_m15_vwap",
        ],
        "entry_parity": parity,
        "entry_parity_pass": all(item["pass"] for item in parity.values()),
        "fidelity_boundary": "Continuous series are diagnostic outside entry; exact entry snapshot is MT5 telemetry-bound. Chart is outcome-aware.",
    }
    manifest_path = args.output_dir / f"{case['case_id']}_indicator_rich_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "VRAS_INDICATOR_RICH_CHART_OK", "image": str(image), "manifest": str(manifest_path), "entry_parity": parity_label}, indent=2))


if __name__ == "__main__":
    main()
