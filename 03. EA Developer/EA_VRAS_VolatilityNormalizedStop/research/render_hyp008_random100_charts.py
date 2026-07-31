#!/usr/bin/env python3
"""Render the frozen HYP008 random-100 decision/anatomy chart pair.

Decision charts are outcome blind by construction.  Exact values at the entry
decision come from the hash-bound ORDER_ACCEPTED telemetry.  Indicator paths
recomputed from broker bars are always labelled NON_PARITY_DIAGNOSTIC.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
RENDERER = Path(__file__).resolve()
PKG = ROOT / "03. EA Developer" / "EA_VRAS_VolatilityNormalizedStop"
RESEARCH = PKG / "research"
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100"
SELECTION_PATH = EVIDENCE / "selection_manifest.json"
CASES_PATH = EVIDENCE / "cases_random_100.csv"
CHARTS = EVIDENCE / "charts"
DECISION_DIR = CHARTS / "decision_asof"
ANATOMY_DIR = CHARTS / "anatomy"
MANIFEST_PATH = EVIDENCE / "chart_manifest.json"

EXPECTED_HYPOTHESIS = "HYP-VRAS-EURUSD-M5-008"
EXPECTED_RUN = "20260722_233420"
PIP = 0.0001
PRICE_TOLERANCE = 0.000011
INDICATOR_TOLERANCE = 0.000011


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def fail(message: str) -> None:
    raise RuntimeError(message)


def workspace_path(path_text: str) -> Path:
    path = (ROOT / Path(path_text)).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        fail(f"Binding escapes workspace: {path_text}")
    return path


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def exact_float(left: Any, right: Any, tolerance: float, label: str) -> None:
    if not math.isfinite(float(left)) or not math.isfinite(float(right)):
        fail(f"Non-finite parity value for {label}")
    if abs(float(left) - float(right)) > tolerance:
        fail(f"Parity mismatch {label}: {left} != {right} (tol={tolerance})")


def load_selection() -> tuple[dict[str, Any], list[dict[str, str]], dict[str, dict[str, str]]]:
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    if selection.get("hypothesis_id") != EXPECTED_HYPOTHESIS:
        fail("Selection hypothesis mismatch")
    if selection.get("run_id") != EXPECTED_RUN:
        fail("Selection run mismatch")
    if selection.get("sample_size") != 100:
        fail("Selection must contain exactly 100 cases")

    bindings = selection.get("bindings", {})
    required = {
        "run_manifest", "lifecycle", "decision_telemetry", "run_meta", "source",
        "tester_report", "bars_m1", "bars_h1", "cases_csv",
    }
    if not required.issubset(bindings):
        fail(f"Selection bindings missing: {sorted(required - set(bindings))}")
    for name in sorted(required):
        binding = bindings[name]
        path = workspace_path(binding["path"])
        if not path.is_file():
            fail(f"Missing bound input {name}: {path}")
        actual = sha256(path)
        if actual != binding["sha256"]:
            fail(f"Frozen input hash mismatch for {name}: {actual} != {binding['sha256']}")
    if workspace_path(bindings["cases_csv"]["path"]) != CASES_PATH.resolve():
        fail("Selection cases_csv path is not the frozen random-100 CSV")

    with CASES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        cases = list(csv.DictReader(handle))
    if len(cases) != 100:
        fail(f"Expected exactly 100 CSV cases, got {len(cases)}")
    case_ids = [row["case_id"] for row in cases]
    positions = [int(row["position_id"]) for row in cases]
    if case_ids != selection.get("case_ids"):
        fail("CSV case order differs from frozen selection")
    if positions != selection.get("position_ids"):
        fail("CSV position order differs from frozen selection")
    if len(set(case_ids)) != 100 or len(set(positions)) != 100:
        fail("Frozen sample contains duplicate case or position IDs")
    return selection, cases, bindings


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def report_close_comments(report: Path) -> dict[int, str]:
    tables = pd.read_html(report)
    if len(tables) < 2:
        fail("Tester report does not expose the orders/deals table")
    table = tables[1]
    comments: dict[int, str] = {}
    for row in table.itertuples(index=False, name=None):
        if len(row) < 13 or str(row[4]).strip().lower() != "out":
            continue
        try:
            deal_id = int(float(row[1]))
        except (TypeError, ValueError):
            continue
        comment = "" if pd.isna(row[12]) else str(row[12]).strip()
        if deal_id in comments:
            fail(f"Duplicate report close deal {deal_id}")
        comments[deal_id] = comment or "UNKNOWN"
    if not comments:
        fail("No exact close comments parsed from tester report")
    return comments


def verify_exact_evidence(
    cases: list[dict[str, str]], bindings: dict[str, dict[str, str]]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    telemetry_path = workspace_path(bindings["decision_telemetry"]["path"])
    lifecycle_path = workspace_path(bindings["lifecycle"]["path"])
    report_path = workspace_path(bindings["tester_report"]["path"])
    runmeta_path = workspace_path(bindings["run_meta"]["path"])

    accepted: dict[tuple[str, int], dict[str, str]] = {}
    for row in load_csv(telemetry_path):
        if row["status"] != "ORDER_ACCEPTED":
            continue
        key = (row["server_time"], int(row["direction"]))
        if key in accepted:
            fail(f"Duplicate ORDER_ACCEPTED key {key}")
        accepted[key] = row
    if len(accepted) != 3611:
        fail(f"Expected 3611 ORDER_ACCEPTED rows, got {len(accepted)}")

    lifecycle: dict[str, list[dict[str, str]]] = {}
    for row in load_csv(lifecycle_path):
        lifecycle.setdefault(row["position_id"], []).append(row)
    if len(lifecycle) != 3611:
        fail(f"Expected 3611 lifecycle positions, got {len(lifecycle)}")
    comments = report_close_comments(report_path)
    runmeta = json.loads(runmeta_path.read_text(encoding="utf-8"))
    if runmeta.get("hypothesis_id") != EXPECTED_HYPOTHESIS:
        fail("RunMeta hypothesis mismatch")
    if runmeta.get("variant_tag") != "CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON_V2":
        fail("RunMeta variant mismatch")

    evidence: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = case["case_id"]
        direction = int(case["direction"])
        entry_time = case["entry_time_server"]
        decision = accepted.get((entry_time, direction))
        if decision is None:
            fail(f"No exact telemetry row for {case_id}")
        exact_float(case["entry"], decision["entry"], PRICE_TOLERANCE, f"{case_id} entry")
        exact_float(case["sl"], decision["stop"], PRICE_TOLERANCE, f"{case_id} stop")
        exact_float(case["tp"], decision["target"], PRICE_TOLERANCE, f"{case_id} target")
        for key in ("h1_close", "h1_ema", "rolling_vwap_48", "atr14"):
            exact_float(case[key], decision[key], INDICATOR_TOLERANCE, f"{case_id} {key}")
        exact_float(case["spread_pips"], decision["spread_pips"], 0.00011, f"{case_id} spread")

        events = lifecycle.get(case["position_id"], [])
        opens = [row for row in events if row["action"] == "OPEN"]
        closes = [row for row in events if row["is_final_close"] == "1"]
        if len(opens) != 1 or len(closes) != 1:
            fail(f"Lifecycle not exact one OPEN/final CLOSE for {case_id}")
        opened, closed = opens[0], closes[0]
        if opened["event_time"] != entry_time or closed["event_time"] != case["exit_time_server"]:
            fail(f"Lifecycle server-time mismatch for {case_id}")
        if (opened["order_type"] == "BUY") != (direction > 0):
            fail(f"Lifecycle direction mismatch for {case_id}")
        exact_float(case["entry"], opened["price"], PRICE_TOLERANCE, f"{case_id} lifecycle entry")
        exact_float(case["exit"], closed["price"], PRICE_TOLERANCE, f"{case_id} lifecycle exit")
        close_deal = int(closed["deal"])
        if close_deal != int(case["close_deal_id"]):
            fail(f"Close deal mismatch for {case_id}")
        report_comment = comments.get(close_deal, "UNKNOWN")
        if report_comment != case["exact_exit_comment"]:
            fail(f"Exact report comment mismatch for {case_id}: {report_comment!r}")

        entry_server = pd.Timestamp(case["entry_time_server"])
        entry_utc = pd.Timestamp(case["entry_time_utc"])
        offset = pd.Timedelta(hours=float(case["server_utc_offset_h"]))
        if entry_server - offset != entry_utc:
            fail(f"Frozen server/UTC entry mapping mismatch for {case_id}")
        exit_server = pd.Timestamp(case["exit_time_server"])
        exit_utc = pd.Timestamp(case["exit_time_utc"])
        if exit_server - offset != exit_utc:
            fail(f"Frozen server/UTC exit mapping mismatch for {case_id}")

        evidence[case_id] = {
            "telemetry": decision,
            "open": opened,
            "close": closed,
            "report_close_comment": report_comment,
        }
    return evidence, runmeta


def aggregate(raw: pd.DataFrame, frequency: str) -> pd.DataFrame:
    return raw.resample(frequency, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    ).dropna(subset=["open", "high", "low", "close"])


def prepare_bars(
    cases: list[dict[str, str]], bindings: dict[str, dict[str, str]]
) -> dict[str, pd.DataFrame]:
    first = min(pd.Timestamp(case["entry_time_server"]) for case in cases)
    last = max(pd.Timestamp(case["exit_time_server"]) for case in cases)
    m1_path = workspace_path(bindings["bars_m1"]["path"])
    h1_path = workspace_path(bindings["bars_h1"]["path"])

    raw = pd.read_parquet(
        m1_path,
        columns=["time_server", "open", "high", "low", "close", "tick_volume"],
    )
    raw["time_server"] = pd.to_datetime(raw["time_server"])
    raw = raw[(raw["time_server"] >= first - pd.Timedelta(days=8)) &
              (raw["time_server"] <= last + pd.Timedelta(hours=2))]
    if raw.empty or raw["time_server"].duplicated().any():
        fail("M1 broker-server bars are empty or duplicate")
    raw = raw.set_index("time_server").sort_index()
    m5 = aggregate(raw, "5min")
    m15 = aggregate(raw, "15min")
    typical = (m5["high"] + m5["low"] + m5["close"]) / 3.0
    volume = m5["tick_volume"].astype(float)
    m5["vwap48_diagnostic"] = (typical * volume).rolling(48).sum() / volume.rolling(48).sum()
    previous = m5["close"].shift(1)
    true_range = pd.concat(
        [m5["high"] - m5["low"], (m5["high"] - previous).abs(), (m5["low"] - previous).abs()],
        axis=1,
    ).max(axis=1)
    m5["atr14_wilder_diagnostic"] = true_range.ewm(
        alpha=1.0 / 14.0, adjust=False, min_periods=14
    ).mean()

    h1 = pd.read_parquet(
        h1_path,
        columns=["time_server", "open", "high", "low", "close", "tick_volume"],
    )
    h1["time_server"] = pd.to_datetime(h1["time_server"])
    if h1.empty or h1["time_server"].duplicated().any():
        fail("H1 broker-server bars are empty or duplicate")
    h1 = h1.set_index("time_server").sort_index()
    if h1.index.min() > pd.Timestamp("2015-01-03"):
        fail("H1 EMA path does not include the bound 2015 history start")
    h1["ema200_diagnostic"] = h1["close"].ewm(span=200, adjust=False).mean()
    h1 = h1[(h1.index >= first - pd.Timedelta(days=30)) &
            (h1.index <= last + pd.Timedelta(hours=2))]
    return {"m1": raw, "m5": m5, "m15": m15, "h1": h1}


def closed_view(frame: pd.DataFrame, entry: pd.Timestamp, minutes: int, count: int) -> pd.DataFrame:
    view = frame[frame.index + pd.Timedelta(minutes=minutes) <= entry].tail(count).copy()
    if len(view) < min(count, 10):
        fail(f"Insufficient closed {minutes}-minute context at {entry}")
    return view


def candle_plot(ax: plt.Axes, frame: pd.DataFrame, width: float = 0.64) -> None:
    for index, row in enumerate(frame.itertuples()):
        color = "#198038" if row.close >= row.open else "#da1e28"
        ax.vlines(index, row.low, row.high, color=color, linewidth=0.7)
        low, high = sorted((row.open, row.close))
        ax.add_patch(plt.Rectangle(
            (index - width / 2, low), width, max(high - low, 0.000005),
            facecolor=color, edgecolor=color, linewidth=0.45,
        ))
    ax.grid(alpha=0.16)


def time_ticks(ax: plt.Axes, frame: pd.DataFrame, count: int = 7) -> None:
    if frame.empty:
        return
    ticks = np.unique(np.linspace(0, len(frame) - 1, min(count, len(frame)), dtype=int))
    ax.set_xticks(ticks)
    ax.set_xticklabels([frame.index[index].strftime("%m-%d\n%H:%M") for index in ticks], fontsize=7)


def decision_diagnostics(case: dict[str, str], bars: dict[str, pd.DataFrame]) -> dict[str, Any]:
    entry_time = pd.Timestamp(case["entry_time_server"])
    direction = int(case["direction"])
    closed_m5 = closed_view(bars["m5"], entry_time, 5, 80)
    signal = closed_m5.iloc[-1]
    previous = closed_m5.iloc[-2]
    exact_vwap = float(case["rolling_vwap_48"])
    if direction > 0:
        pullback = bool(signal.low <= exact_vwap and signal.close > exact_vwap)
        breakout = bool(signal.close > previous.high)
        exact_h1_gate = float(case["h1_close"]) > float(case["h1_ema"])
        swing = float(closed_m5.tail(10)["low"].min())
        raw_stop = swing - 1.5 * PIP
    else:
        pullback = bool(signal.high >= exact_vwap and signal.close < exact_vwap)
        breakout = bool(signal.close < previous.low)
        exact_h1_gate = float(case["h1_close"]) < float(case["h1_ema"])
        swing = float(closed_m5.tail(10)["high"].max())
        raw_stop = swing + 1.5 * PIP
    raw_distance = direction * (float(case["entry"]) - raw_stop)
    exact_atr = float(case["atr14"])
    computed_distance = max(raw_distance, exact_atr)
    computed_stop = float(case["entry"]) - direction * computed_distance
    return {
        "signal_bar_start_server": signal.name.strftime("%Y.%m.%d %H:%M:%S"),
        "signal_bar_end_server": (signal.name + pd.Timedelta(minutes=5)).strftime("%Y.%m.%d %H:%M:%S"),
        "trigger_pullback_exact_vwap": pullback,
        "trigger_breakout_previous_bar": breakout,
        "h1_gate_exact_telemetry": bool(exact_h1_gate),
        "swing_10_extreme_diagnostic": swing,
        "raw_structural_stop_diagnostic": raw_stop,
        "raw_distance_pips_diagnostic": raw_distance / PIP,
        "atr_floor_pips_exact_telemetry": exact_atr / PIP,
        "computed_final_stop_diagnostic": computed_stop,
        "computed_stop_delta_pips": (computed_stop - float(case["sl"])) / PIP,
        "computed_paths_status": "NON_PARITY_DIAGNOSTIC",
    }


def save_figure(fig: plt.Figure, path: Path, metadata: dict[str, Any]) -> None:
    fig.savefig(
        path,
        dpi=150,
        facecolor="white",
        metadata={
            "Title": f"{metadata['case_id']} {metadata['mode']}",
            "Description": json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        },
    )
    plt.close(fig)
    if not path.is_file() or path.stat().st_size < 10_000:
        fail(f"Rendered PNG missing or implausibly small: {path}")


def render_decision(
    case: dict[str, str], bars: dict[str, pd.DataFrame], diagnostic: dict[str, Any], out: Path
) -> dict[str, Any]:
    entry_time = pd.Timestamp(case["entry_time_server"])
    direction = int(case["direction"])
    m5 = closed_view(bars["m5"], entry_time, 5, 80)
    m15 = closed_view(bars["m15"], entry_time, 15, 28)
    h1 = closed_view(bars["h1"], entry_time, 60, 30)

    fig = plt.figure(figsize=(16, 10.5))
    grid = fig.add_gridspec(3, 2, height_ratios=[3.3, 2.0, 1.05], hspace=0.36, wspace=0.18)
    ax_m5 = fig.add_subplot(grid[0, :])
    ax_m15 = fig.add_subplot(grid[1, 0])
    ax_h1 = fig.add_subplot(grid[1, 1])
    ax_atr = fig.add_subplot(grid[2, 0])
    ax_text = fig.add_subplot(grid[2, 1])

    candle_plot(ax_m5, m5)
    x5 = np.arange(len(m5))
    ax_m5.plot(x5, m5["vwap48_diagnostic"], color="#8a3ffc", linewidth=1.5,
               label="VWAP48 path - NON_PARITY_DIAGNOSTIC")
    marker_x = len(m5) - 0.1
    marker = "^" if direction > 0 else "v"
    ax_m5.scatter([marker_x], [float(case["entry"])], marker=marker, s=110,
                  color="#161616", zorder=7, label="Exact entry")
    ax_m5.scatter([marker_x], [float(case["rolling_vwap_48"])], marker="D", s=45,
                  color="#8a3ffc", zorder=7, label="Exact telemetry VWAP48")
    ax_m5.axhline(float(case["sl"]), color="#da1e28", linestyle="--", linewidth=1.0,
                  label="Proposed structural SL")
    ax_m5.axhline(float(case["tp"]), color="#198038", linestyle="--", linewidth=1.0,
                  label="Proposed TP 1.5R")
    ax_m5.axvspan(len(m5) - 1.5, len(m5) - 0.5, color="#f1c21b", alpha=0.14,
                  label="Closed trigger bar")
    ax_m5.set_xlim(-0.7, len(m5) + 0.6)
    ax_m5.set_ylabel("EURUSD M5")
    ax_m5.set_title(f"{case['case_id']} | DECISION AS-OF | broker server time | OUTCOME HIDDEN")
    ax_m5.legend(loc="best", fontsize=7, ncol=3)
    time_ticks(ax_m5, m5, 9)

    candle_plot(ax_m15, m15)
    ax_m15.set_title("M15 closed context - NON_PARITY_DIAGNOSTIC")
    ax_m15.set_ylabel("EURUSD")
    time_ticks(ax_m15, m15)

    candle_plot(ax_h1, h1)
    x1 = np.arange(len(h1))
    ax_h1.plot(x1, h1["ema200_diagnostic"], color="#0072c3", linewidth=1.4,
               label="EMA200 path from bound 2015 history - NON_PARITY_DIAGNOSTIC")
    ax_h1.scatter([len(h1) - 0.1], [float(case["h1_close"])], marker="o", s=42,
                  color="#161616", zorder=7, label="Exact closed H1 close")
    ax_h1.scatter([len(h1) - 0.1], [float(case["h1_ema"])], marker="D", s=38,
                  color="#0072c3", zorder=7, label="Exact closed H1 EMA200")
    ax_h1.set_xlim(-0.7, len(h1) + 0.6)
    ax_h1.set_title("H1 trend gate (closed bar only)")
    ax_h1.legend(loc="best", fontsize=7)
    time_ticks(ax_h1, h1)

    ax_atr.plot(x5, m5["atr14_wilder_diagnostic"] / PIP, color="#ff832b", linewidth=1.3,
                label="ATR14 path - NON_PARITY_DIAGNOSTIC")
    ax_atr.scatter([marker_x], [float(case["atr14"]) / PIP], marker="D", s=42,
                   color="#a2191f", label="Exact telemetry ATR14")
    ax_atr.set_ylabel("ATR pips")
    ax_atr.grid(alpha=0.16)
    ax_atr.legend(loc="best", fontsize=7)
    time_ticks(ax_atr, m5)

    ax_text.axis("off")
    trigger = "PASS" if diagnostic["trigger_pullback_exact_vwap"] and diagnostic["trigger_breakout_previous_bar"] else "DIAGNOSTIC_MISMATCH"
    gate = "PASS" if diagnostic["h1_gate_exact_telemetry"] else "FAIL"
    text = (
        f"{case['side']} | entry {float(case['entry']):.5f} | SL {float(case['sl']):.5f} | TP {float(case['tp']):.5f}\n"
        f"Exact telemetry: H1 close {float(case['h1_close']):.5f}, EMA200 {float(case['h1_ema']):.5f}, "
        f"VWAP48 {float(case['rolling_vwap_48']):.5f}\n"
        f"ATR14 {float(case['atr14']) / PIP:.2f} pip | spread {float(case['spread_pips']):.2f} pip\n"
        f"H1 gate {gate} | pullback+breakout {trigger}\n"
        f"Stop: swing10 + 1.5 pip buffer, ATR floor 1.0x, max structural 3.0x\n"
        f"Exact telemetry is parity authority; all continuous paths are NON_PARITY_DIAGNOSTIC."
    )
    ax_text.text(0.0, 0.95, text, va="top", ha="left", fontsize=9.2, linespacing=1.45,
                 bbox={"boxstyle": "round,pad=0.5", "facecolor": "#f4f4f4", "edgecolor": "#8d8d8d"})
    fig.suptitle("No post-entry bars or outcome fields are rendered", fontsize=11, y=0.995)

    metadata = {
        "schema_version": "vras_chart_png_contract.v1",
        "case_id": case["case_id"],
        "mode": "decision_asof",
        "time_axis": "broker_server_time",
        "outcome_hidden": True,
        "post_entry_bars": 0,
    }
    save_figure(fig, out, metadata)
    payload = {
        "case_id": case["case_id"],
        "position_id": int(case["position_id"]),
        "entry_time_server": case["entry_time_server"],
        "direction": direction,
        "side": case["side"],
        "entry": float(case["entry"]),
        "proposed_sl": float(case["sl"]),
        "proposed_tp": float(case["tp"]),
        "telemetry": {
            "status": case["telemetry_status"],
            "h1_close": float(case["h1_close"]),
            "h1_ema": float(case["h1_ema"]),
            "rolling_vwap_48": float(case["rolling_vwap_48"]),
            "atr14": float(case["atr14"]),
            "spread_pips": float(case["spread_pips"]),
        },
        "diagnostic": diagnostic,
        "path": relative(out),
        "sha256": sha256(out),
        "time_axis": "broker_server_time",
        "outcome_hidden": True,
        "post_entry_bars": 0,
        "latest_m5_bar_end_server": (m5.index[-1] + pd.Timedelta(minutes=5)).strftime("%Y.%m.%d %H:%M:%S"),
        "latest_m15_bar_end_server": (m15.index[-1] + pd.Timedelta(minutes=15)).strftime("%Y.%m.%d %H:%M:%S"),
        "latest_h1_bar_end_server": (h1.index[-1] + pd.Timedelta(hours=1)).strftime("%Y.%m.%d %H:%M:%S"),
        "png_contract": metadata,
    }
    return payload


def anatomy_excursions(case: dict[str, str], m1: pd.DataFrame) -> dict[str, Any]:
    entry_time = pd.Timestamp(case["entry_time_server"])
    exit_time = pd.Timestamp(case["exit_time_server"])
    path = m1[(m1.index >= entry_time.floor("min")) & (m1.index <= exit_time.floor("min"))]
    if path.empty:
        fail(f"Missing M1 path for {case['case_id']}")
    direction = int(case["direction"])
    entry = float(case["entry"])
    risk = abs(entry - float(case["sl"]))
    if direction > 0:
        favorable = float(path["high"].max()) - entry
        adverse = float(path["low"].min()) - entry
        ambiguous = (path["high"] >= float(case["tp"])) & (path["low"] <= float(case["sl"]))
    else:
        favorable = entry - float(path["low"].min())
        adverse = entry - float(path["high"].max())
        ambiguous = (path["low"] <= float(case["tp"])) & (path["high"] >= float(case["sl"]))
    return {
        "status": "M1_OHLC_DIAGNOSTIC",
        "mfe_pips": favorable / PIP,
        "mae_pips_signed": adverse / PIP,
        "mfe_r": favorable / risk if risk > 0 else None,
        "mae_r_signed": adverse / risk if risk > 0 else None,
        "initial_sl_and_tp_same_m1_bar_count": int(ambiguous.sum()),
        "intraminute_first_passage": "AMBIGUOUS_NOT_INFERRED" if bool(ambiguous.any()) else "NOT_REQUIRED_FROM_OHLC",
    }


def anatomy_view(frame: pd.DataFrame, entry: pd.Timestamp, exit_: pd.Timestamp, pre: pd.Timedelta) -> pd.DataFrame:
    view = frame[(frame.index >= entry - pre) & (frame.index < exit_)].copy()
    if view.empty:
        fail(f"Missing anatomy bars at {entry} -> {exit_}")
    return view


def event_x(frame: pd.DataFrame, when: pd.Timestamp) -> int:
    return max(0, min(len(frame) - 1, int(frame.index.searchsorted(when, side="right") - 1)))


def render_anatomy(
    case: dict[str, str], bars: dict[str, pd.DataFrame], excursions: dict[str, Any], out: Path
) -> dict[str, Any]:
    entry_time = pd.Timestamp(case["entry_time_server"])
    exit_time = pd.Timestamp(case["exit_time_server"])
    m5 = anatomy_view(bars["m5"], entry_time, exit_time, pd.Timedelta(hours=4))
    m15 = anatomy_view(bars["m15"], entry_time, exit_time, pd.Timedelta(hours=8))
    h1 = anatomy_view(bars["h1"], entry_time, exit_time, pd.Timedelta(hours=24))
    direction = int(case["direction"])

    fig = plt.figure(figsize=(16, 10.5))
    grid = fig.add_gridspec(2, 2, height_ratios=[3.2, 2.0], hspace=0.34, wspace=0.18)
    ax_m5 = fig.add_subplot(grid[0, :])
    ax_m15 = fig.add_subplot(grid[1, 0])
    ax_h1 = fig.add_subplot(grid[1, 1])

    candle_plot(ax_m5, m5)
    x5 = np.arange(len(m5))
    ax_m5.plot(x5, m5["vwap48_diagnostic"], color="#8a3ffc", linewidth=1.3,
               label="VWAP48 - NON_PARITY_DIAGNOSTIC")
    entry_x = event_x(m5, entry_time)
    exit_x = event_x(m5, exit_time)
    ax_m5.axhline(float(case["entry"]), color="#161616", linestyle="--", linewidth=0.9, label="Exact entry")
    ax_m5.axhline(float(case["sl"]), color="#da1e28", linestyle="--", linewidth=1.1, label="Initial structural SL")
    ax_m5.axhline(float(case["tp"]), color="#198038", linestyle="--", linewidth=1.1, label="Nominal TP 1.5R")
    ax_m5.scatter([entry_x], [float(case["entry"])], marker="^" if direction > 0 else "v",
                  s=100, color="#161616", zorder=7)
    ax_m5.scatter([exit_x], [float(case["exit"])], marker="X", s=90, color="#fa4d56",
                  zorder=7, label="Exact report-bound final close")
    ax_m5.axvspan(entry_x, exit_x, color="#f1c21b", alpha=0.07)
    ax_m5.set_title(f"{case['case_id']} | ANATOMY | {case['side']} | broker server time")
    ax_m5.set_ylabel("EURUSD M5")
    ax_m5.legend(loc="best", fontsize=7, ncol=3)
    time_ticks(ax_m5, m5, 10)

    candle_plot(ax_m15, m15)
    ax_m15.axhline(float(case["entry"]), color="#161616", linestyle="--", linewidth=0.8)
    ax_m15.axhline(float(case["sl"]), color="#da1e28", linestyle="--", linewidth=0.8)
    ax_m15.axhline(float(case["tp"]), color="#198038", linestyle="--", linewidth=0.8)
    ax_m15.set_title("M15 path through exact final close")
    time_ticks(ax_m15, m15)

    candle_plot(ax_h1, h1)
    ax_h1.plot(np.arange(len(h1)), h1["ema200_diagnostic"], color="#0072c3", linewidth=1.3,
               label="EMA200 from full bound 2015 history - NON_PARITY_DIAGNOSTIC")
    ax_h1.set_title("H1 regime context")
    ax_h1.legend(loc="best", fontsize=7)
    time_ticks(ax_h1, h1)

    exit_reason = case["exact_exit_comment"] or "UNKNOWN"
    fig.suptitle(
        f"Exact exit: {case['exact_exit_class']} | report comment: {exit_reason} | "
        f"exit {float(case['exit']):.5f} | net R {float(case['net_r']):+.3f} | "
        f"MFE {excursions['mfe_r']:+.2f}R / MAE {excursions['mae_r_signed']:+.2f}R (M1_OHLC_DIAGNOSTIC)",
        fontsize=10.5, y=0.995,
    )
    metadata = {
        "schema_version": "vras_chart_png_contract.v1",
        "case_id": case["case_id"],
        "mode": "anatomy",
        "time_axis": "broker_server_time",
        "outcome_aware": True,
        "exit_source": "EXACT_TESTER_REPORT_BOUND_COMMENT",
    }
    save_figure(fig, out, metadata)
    return {
        "case_id": case["case_id"],
        "position_id": int(case["position_id"]),
        "entry_time_server": case["entry_time_server"],
        "exit_time_server": case["exit_time_server"],
        "direction": direction,
        "side": case["side"],
        "entry": float(case["entry"]),
        "initial_sl": float(case["sl"]),
        "nominal_tp_1_5r": float(case["tp"]),
        "exit": float(case["exit"]),
        "net_r": float(case["net_r"]),
        "label": case["label"],
        "exact_exit_class": case["exact_exit_class"],
        "exact_exit_comment": exit_reason,
        "active_stop_at_exit": float(case["active_stop_at_exit"]) if case["active_stop_at_exit"] else None,
        "excursions": excursions,
        "path": relative(out),
        "sha256": sha256(out),
        "time_axis": "broker_server_time",
        "outcome_aware": True,
        "png_contract": metadata,
    }


def expected_image_paths(cases: list[dict[str, str]]) -> tuple[set[Path], set[Path]]:
    decisions = {DECISION_DIR / f"{case['case_id']}_decision_asof.png" for case in cases}
    anatomy = {ANATOMY_DIR / f"{case['case_id']}_anatomy.png" for case in cases}
    return decisions, anatomy


def reject_stale_extras(expected: set[Path], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    extras = set(folder.glob("*.png")) - expected
    if extras:
        fail(f"Unexpected stale PNGs in {folder}: {[path.name for path in sorted(extras)]}")


def main() -> int:
    selection, cases, bindings = load_selection()
    input_hashes_before = {
        name: sha256(workspace_path(binding["path"])) for name, binding in bindings.items()
    }
    selection_hash = sha256(SELECTION_PATH)
    evidence, runmeta = verify_exact_evidence(cases, bindings)
    bars = prepare_bars(cases, bindings)

    decision_paths, anatomy_paths = expected_image_paths(cases)
    reject_stale_extras(decision_paths, DECISION_DIR)
    reject_stale_extras(anatomy_paths, ANATOMY_DIR)

    records: list[dict[str, Any]] = []
    for index, case in enumerate(cases, 1):
        diagnostic = decision_diagnostics(case, bars)
        decision_out = DECISION_DIR / f"{case['case_id']}_decision_asof.png"
        anatomy_out = ANATOMY_DIR / f"{case['case_id']}_anatomy.png"
        decision = render_decision(case, bars, diagnostic, decision_out)
        excursions = anatomy_excursions(case, bars["m1"])
        anatomy = render_anatomy(case, bars, excursions, anatomy_out)
        records.append({
            "case_id": case["case_id"],
            "position_id": int(case["position_id"]),
            "draw_index": index,
            "parity": {
                "status": "PASS",
                "telemetry_status": evidence[case["case_id"]]["telemetry"]["status"],
                "lifecycle_open_final_close": "PASS",
                "tester_report_close_comment": "PASS",
            },
            "decision_asof": decision,
            "anatomy": anatomy,
        })
        if index % 10 == 0:
            print(f"rendered_cases={index}/100", flush=True)

    input_hashes_after = {
        name: sha256(workspace_path(binding["path"])) for name, binding in bindings.items()
    }
    if input_hashes_before != input_hashes_after or sha256(SELECTION_PATH) != selection_hash:
        fail("A bound input changed during rendering; manifest withheld")
    actual_decisions = set(DECISION_DIR.glob("*.png"))
    actual_anatomy = set(ANATOMY_DIR.glob("*.png"))
    if actual_decisions != decision_paths or actual_anatomy != anatomy_paths:
        fail("Rendered image coverage is not exact 100 decision + 100 anatomy")

    manifest = {
        "schema_version": "vras_hyp008_random100_charts.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": EXPECTED_HYPOTHESIS,
        "run_id": EXPECTED_RUN,
        "forensic_only": True,
        "case_count": 100,
        "image_count": 200,
        "decision_image_count": 100,
        "anatomy_image_count": 100,
        "case_ids": [case["case_id"] for case in cases],
        "position_ids": [int(case["position_id"]) for case in cases],
        "time_contract": {
            "chart_axis": "broker_server_time",
            "utc_fields": "frozen upstream with fivepercent_server_clock; not recomputed by renderer",
        },
        "decision_contract": {
            "outcome_blind": True,
            "post_entry_bars": 0,
            "forbidden": [
                "label", "net_usd", "net_r", "exit_time_server", "exit_time_utc", "exit",
                "exact_exit_class", "exact_exit_comment", "active_stop_at_exit", "anatomy_path",
            ],
            "exact_authority": "ORDER_ACCEPTED_DECISION_TELEMETRY",
            "computed_paths": "NON_PARITY_DIAGNOSTIC",
        },
        "indicator_contract": {
            "active_surface": [
                "closed_h1_ema200_gate", "closed_m5_rolling_vwap48", "closed_m5_atr14",
                "pullback_then_previous_bar_breakout", "swing10_plus_1_5pip_buffer",
                "atr_floor_1x", "max_structural_atr_3x", "spread",
            ],
            "h1_ema_history_start": "2015",
            "continuous_paths": "NON_PARITY_DIAGNOSTIC",
        },
        "input_bindings": {
            "selection_manifest": {"path": relative(SELECTION_PATH), "sha256": selection_hash},
            **{
                name: {"path": binding["path"], "sha256": input_hashes_after[name]}
                for name, binding in sorted(bindings.items())
            },
            "renderer_source": {"path": relative(RENDERER), "sha256": sha256(RENDERER)},
        },
        "parity_summary": {
            "status": "PASS",
            "sample_order": "PASS_EXACT_100",
            "order_accepted_telemetry": "PASS_EXACT_100",
            "lifecycle_open_final_close": "PASS_EXACT_100",
            "tester_report_close_comments": "PASS_EXACT_100",
            "computed_indicator_paths": "NON_PARITY_DIAGNOSTIC",
            "runmeta_variant": runmeta["variant_tag"],
        },
        "cases": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "HYP008_RANDOM100_CHARTS_RENDERED",
        "manifest": relative(MANIFEST_PATH),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "case_count": len(records),
        "image_count": len(actual_decisions) + len(actual_anatomy),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"HYP008_RANDOM100_RENDER_FAIL: {exc}", file=sys.stderr)
        raise
