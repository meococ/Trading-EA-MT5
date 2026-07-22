#!/usr/bin/env python3
"""Freeze, render, and packetize ten VRAS Model-0 chart-forensics cases.

The sample is selected mechanically from lifecycle truth before any chart is
rendered.  Each output PNG is a combined forensic view: an explicitly
outcome-hidden M5 decision panel, an outcome anatomy panel, and M15/H1 context.
MT5 decision telemetry is printed verbatim at the entry snapshot; price bars
come from the hash-bound FivePercent EURUSD M1 parquet and are resampled to
closed M5/M15/H1 bid bars for visualization.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
RESEARCH = Path(__file__).resolve().parent
HYPOTHESIS_ID = "HYP-VRAS-EURUSD-M5-003"
RUN_ID = "20260722_103759"
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_RegimeAdaptiveScalperV3" / RUN_ID
LOGS = RUN / "logs"
LIFECYCLE = next(LOGS.glob("*LifecycleTrades*.csv"))
TELEMETRY = next(LOGS.glob("*DecisionTelemetry*.csv"))
RUN_META = next(LOGS.glob("*RunMeta*.json"))
BARS_M1 = ROOT / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
PREREG = RESEARCH / f"{HYPOTHESIS_ID}_FROZEN_PREREG.md"
SOURCE = RUN / "snapshot" / "source" / "EA_VRAS_RegimeAdaptiveScalperV3.mq5"
REPORT = RUN / "report.html"
RUN_MANIFEST = RUN / "run_manifest.json"
READOUT = RESEARCH / f"{HYPOTHESIS_ID}_READOUT.md"
EVIDENCE = RESEARCH / "evidence" / f"{HYPOTHESIS_ID}_GROK_CHART_FORENSICS_10"
CHARTS = EVIDENCE / "charts"
SEED = 5600722


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resample_ohlc(frame: pd.DataFrame, rule: str, *, time_col: str) -> pd.DataFrame:
    source = frame.set_index(time_col).sort_index()
    bars = source.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    )
    return bars.dropna(subset=["open", "high", "low", "close"])


def load_position_truth() -> pd.DataFrame:
    lifecycle = pd.read_csv(LIFECYCLE)
    telemetry = pd.read_csv(TELEMETRY)
    lifecycle["event_time"] = pd.to_datetime(lifecycle["event_time"])
    telemetry["server_time"] = pd.to_datetime(telemetry["server_time"])
    telemetry["utc_time"] = pd.to_datetime(telemetry["utc_time"])

    opens = lifecycle[lifecycle["action"].eq("OPEN")].copy()
    closes = lifecycle[
        lifecycle["action"].eq("CLOSE") & lifecycle["is_final_close"].eq(1)
    ].copy()
    position_net = lifecycle.groupby("position_id", as_index=False)["deal_net"].sum()
    position_net = position_net.rename(columns={"deal_net": "net_usd"})
    accepted = telemetry[telemetry["status"].eq("ORDER_ACCEPTED")].copy()

    positions = opens.merge(
        closes[["position_id", "event_time", "price"]],
        on="position_id",
        suffixes=("_entry", "_exit"),
        validate="one_to_one",
    ).merge(position_net, on="position_id", validate="one_to_one")
    positions = positions.merge(
        accepted,
        left_on="event_time_entry",
        right_on="server_time",
        how="left",
        validate="one_to_one",
        suffixes=("_lifecycle", "_telemetry"),
    )
    if len(positions) != 93:
        raise RuntimeError(f"Expected 93 reconciled positions, found {len(positions)}")
    if positions["event"].isna().any():
        raise RuntimeError("At least one lifecycle OPEN did not match ORDER_ACCEPTED telemetry")
    if not np.allclose(
        positions["price_entry"].astype(float), positions["entry"].astype(float), atol=1e-9
    ):
        raise RuntimeError("Lifecycle entry price and decision telemetry entry do not match")

    positions["position_id"] = positions["position_id"].astype(int)
    positions["direction"] = np.where(positions["order_type"].eq("BUY"), 1, -1)
    positions["entry_time_server"] = positions["event_time_entry"]
    positions["entry_time_utc"] = positions["utc_time"]
    offsets = positions["entry_time_server"] - positions["entry_time_utc"]
    positions["exit_time_server"] = positions["event_time_exit"]
    positions["exit_time_utc"] = positions["exit_time_server"] - offsets
    positions["entry_price"] = positions["price_entry"].astype(float)
    positions["exit_price"] = positions["price_exit"].astype(float)
    positions["stop_price"] = positions["stop"].astype(float)
    positions["target_price"] = positions["target"].astype(float)
    positions["initial_risk_account"] = positions["initial_risk_account"].astype(float)
    positions["net_R"] = positions["net_usd"] / positions["initial_risk_account"]
    positions["outcome"] = np.where(positions["net_R"].gt(0), "WIN", "LOSS")
    positions["hold_minutes"] = (
        positions["exit_time_utc"] - positions["entry_time_utc"]
    ).dt.total_seconds() / 60.0
    positions["atr"] = positions["atr"].astype(float)
    positions["adx"] = positions["adx"].astype(float)
    positions["rsi"] = positions["rsi"].astype(float)
    positions["regime_label"] = np.where(positions["regime"].astype(int).eq(1), "TREND", "RANGE")
    anchor = pd.to_datetime(positions["session_anchor_utc"])
    elapsed = (positions["entry_time_utc"] - anchor).dt.total_seconds() / 3600.0
    positions["session_phase"] = np.select(
        [elapsed.lt(4.0), elapsed.lt(8.0)],
        ["LONDON_EARLY", "LONDON_NY_OVERLAP"],
        default="NY_LATE",
    )
    positions["risk_bucket"] = pd.qcut(
        positions["risk_pts"].rank(method="first"), 3, labels=["LOW", "MID", "HIGH"]
    ).astype(str)
    positions["atr_bucket"] = pd.qcut(
        positions["atr"].rank(method="first"), 3, labels=["LOW", "MID", "HIGH"]
    ).astype(str)

    tolerance = 0.00003
    target_gap = (positions["exit_price"] - positions["target_price"]).abs()
    stop_gap = (positions["exit_price"] - positions["stop_price"]).abs()
    positions["exit_class"] = np.select(
        [target_gap.le(tolerance), stop_gap.le(tolerance)],
        ["TARGET_LEVEL", "STOP_LEVEL"],
        default="NON_LEVEL_FINAL_CLOSE",
    )
    return positions.sort_values("entry_time_utc").reset_index(drop=True)


def closest_to_median(frame: pd.DataFrame) -> pd.Series:
    median = frame["net_R"].median()
    return frame.loc[(frame["net_R"] - median).abs().idxmin()]


def freeze_sample(positions: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    selected: list[tuple[str, pd.Series, str]] = []
    used: set[int] = set()

    def add(stratum: str, row: pd.Series, reason: str) -> None:
        pid = int(row["position_id"])
        if pid in used:
            raise RuntimeError(f"Sampling collision for position_id={pid}")
        used.add(pid)
        selected.append((stratum, row, reason))

    winners = positions[positions["net_R"].gt(0)]
    losers = positions[positions["net_R"].lt(0)]
    add("winner_tail", winners.loc[winners["net_R"].idxmax()], "Maximum net_R winner in the 93-position population")
    add("loser_tail", losers.loc[losers["net_R"].idxmin()], "Minimum net_R loser in the 93-position population")
    add(
        "winner_median",
        closest_to_median(winners[~winners["position_id"].isin(used)]),
        "Positive-net position closest to the remaining winner median net_R",
    )
    add(
        "loser_median",
        closest_to_median(losers[~losers["position_id"].isin(used)]),
        "Negative-net position closest to the remaining loser median net_R",
    )
    range_winners = winners[winners["regime_label"].eq("RANGE") & ~winners["position_id"].isin(used)]
    range_losers = losers[losers["regime_label"].eq("RANGE") & ~losers["position_id"].isin(used)]
    add("range_winner", range_winners.loc[range_winners["net_R"].idxmax()], "Best net_R within the minority RANGE winner population")
    add("range_loser", range_losers.loc[range_losers["net_R"].idxmin()], "Worst net_R within the minority RANGE loser population")

    rng = np.random.default_rng(SEED)
    remaining_winners = winners[~winners["position_id"].isin(used)]
    remaining_losers = losers[~losers["position_id"].isin(used)]
    random_winner = remaining_winners.iloc[int(rng.integers(0, len(remaining_winners)))]
    add("seeded_random_winner", random_winner, f"Uniform winner draw with frozen seed {SEED}")
    random_loser = remaining_losers.iloc[int(rng.integers(0, len(remaining_losers)))]
    add("seeded_random_loser", random_loser, f"Uniform loser draw with frozen seed {SEED}")

    remaining_winners = winners[
        winners["regime_label"].eq("TREND") & ~winners["position_id"].isin(used)
    ]
    remaining_losers = losers[
        losers["regime_label"].eq("TREND") & ~losers["position_id"].isin(used)
    ]
    best: tuple[float, pd.Series, pd.Series] | None = None
    for _, win in remaining_winners.iterrows():
        for _, loss in remaining_losers.iterrows():
            score = 0.0
            score += 100.0 if int(win["direction"]) != int(loss["direction"]) else 0.0
            score += 12.0 if win["session_phase"] != loss["session_phase"] else 0.0
            score += 6.0 if win["risk_bucket"] != loss["risk_bucket"] else 0.0
            score += 4.0 if win["atr_bucket"] != loss["atr_bucket"] else 0.0
            score += abs(math.log(max(float(win["atr"]), 1e-9) / max(float(loss["atr"]), 1e-9)))
            score += abs((win["entry_time_utc"] - loss["entry_time_utc"]).days) / 365.0
            if best is None or score < best[0]:
                best = (score, win, loss)
    if best is None:
        raise RuntimeError("Could not form a disjoint TREND winner/loser matched pair")
    match_score, matched_winner, matched_loser = best
    reason = (
        "Minimum-distance TREND pair over direction, session phase, risk bucket, "
        f"ATR bucket/value and nearby date; match_score={match_score:.6f}"
    )
    add("matched_trend_winner", matched_winner, reason)
    add("matched_trend_loser", matched_loser, reason)

    rows: list[dict] = []
    for number, (stratum, row, reason) in enumerate(selected, start=1):
        item = row.to_dict()
        item["case_id"] = f"VRAS-003-C{number:02d}-P{int(row['position_id'])}"
        item["stratum"] = stratum
        item["context_reason"] = reason
        rows.append(item)
    sample = pd.DataFrame(rows)
    if len(sample) != 10 or sample["position_id"].nunique() != 10:
        raise RuntimeError("Frozen sample must contain exactly ten unique positions")

    manifest = {
        "schema_version": "vras_grok_chart_selection.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "frozen_before_chart_render": True,
        "frozen_at_utc": utc_now(),
        "seed": SEED,
        "population_definition": "All 93 lifecycle positions with one OPEN, one final CLOSE, and one exact ORDER_ACCEPTED telemetry row",
        "population_positions": 93,
        "sample_size": 10,
        "sampling_rule": [
            "maximum and median positive net_R",
            "minimum and median negative net_R",
            "best RANGE winner and worst RANGE loser",
            "one seeded uniform winner and one seeded uniform loser from unused positions",
            "one disjoint minimum-distance TREND winner/loser pair matched on direction, session, risk, ATR, and date",
        ],
        "manual_chart_view_before_freeze": False,
        "outcome_based_manual_selection_forbidden": True,
        "case_ids": sample["case_id"].tolist(),
        "position_ids": [int(value) for value in sample["position_id"].tolist()],
        "strata": sample["stratum"].tolist(),
    }
    return sample, manifest


def draw_candles(ax: plt.Axes, bars: pd.DataFrame, *, reserve_future: bool = False) -> None:
    if bars.empty:
        raise RuntimeError("Cannot draw an empty candle frame")
    x = np.arange(len(bars))
    for idx, (_, row) in enumerate(bars.iterrows()):
        up = row["close"] >= row["open"]
        color = "#16a085" if up else "#c0392b"
        ax.vlines(idx, row["low"], row["high"], color=color, linewidth=0.8, zorder=2)
        bottom = min(row["open"], row["close"])
        height = max(abs(row["close"] - row["open"]), 1e-7)
        ax.add_patch(Rectangle((idx - 0.32, bottom), 0.64, height, color=color, alpha=0.9, zorder=3))
    tick_count = min(7, len(bars))
    ticks = np.unique(np.linspace(0, len(bars) - 1, tick_count).astype(int))
    ax.set_xticks(ticks)
    ax.set_xticklabels([bars.index[i].strftime("%m-%d\n%H:%M") for i in ticks], fontsize=7)
    if reserve_future:
        ax.set_xlim(-1, max(2 * len(bars) - 1, len(bars) + 10))
        ax.axvspan(len(bars) - 0.5, max(2 * len(bars) - 1, len(bars) + 10), color="#ecf0f1", alpha=0.9)
        ax.text(len(bars) * 1.45, float(bars["close"].median()), "FUTURE HIDDEN", ha="center", va="center", color="#7f8c8d", fontsize=10, weight="bold")
    else:
        ax.set_xlim(-1, len(bars))
    ax.grid(alpha=0.18)


def add_entry_snapshot_levels(ax: plt.Axes, row: pd.Series, *, include_geometry: bool) -> None:
    levels = [
        (float(row["session_vwap"]), "Session VWAP @ entry", "#2980b9", "--"),
        (float(row["session_vwap"]) + 2.0 * float(row["session_sd"]), "+2 SD @ entry", "#8e44ad", ":"),
        (float(row["session_vwap"]) - 2.0 * float(row["session_sd"]), "-2 SD @ entry", "#8e44ad", ":"),
    ]
    if float(row["anchored_vwap"]) > 0:
        levels.append((float(row["anchored_vwap"]), "AVWAP @ entry", "#d35400", "-."))
    if include_geometry:
        levels.extend(
            [
                (float(row["entry_price"]), "Entry", "#2c3e50", "-"),
                (float(row["stop_price"]), "Initial SL", "#e74c3c", "--"),
                (float(row["target_price"]), "Planned TP", "#27ae60", "--"),
            ]
        )
    for value, label, color, style in levels:
        ax.axhline(value, color=color, linestyle=style, linewidth=1.0, alpha=0.85, label=label)


def bar_slice(bars: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return bars[(bars.index >= start) & (bars.index <= end)].copy()


def render_case(row: pd.Series, m1: pd.DataFrame, m5: pd.DataFrame, m15: pd.DataFrame, h1: pd.DataFrame) -> dict:
    # Price alignment is deliberately performed on broker server time.  The
    # parquet UTC clock follows a different DST convention during transition
    # weeks than the EA's frozen clock contract; using it would move fills to
    # the wrong candles even though the server-time price matches exactly.
    entry = pd.Timestamp(row["entry_time_server"])
    exit_time = pd.Timestamp(row["exit_time_server"])
    m5_asof = m5[m5.index < entry].tail(60)
    anatomy_end = exit_time.ceil("5min") + pd.Timedelta(minutes=60)
    m5_anatomy = bar_slice(m5, entry - pd.Timedelta(minutes=225), anatomy_end)
    m15_asof = m15[m15.index < entry].tail(36)
    h1_asof = h1[h1.index < entry].tail(30)

    path = bar_slice(m1, entry.floor("min"), exit_time.ceil("min"))
    stop_distance = abs(float(row["entry_price"]) - float(row["stop_price"]))
    direction = int(row["direction"])
    if path.empty or stop_distance <= 0:
        mae_r = float("nan")
        mfe_r = float("nan")
    elif direction == 1:
        mfe_r = (float(path["high"].max()) - float(row["entry_price"])) / stop_distance
        mae_r = (float(row["entry_price"]) - float(path["low"].min())) / stop_distance
    else:
        mfe_r = (float(row["entry_price"]) - float(path["low"].min())) / stop_distance
        mae_r = (float(path["high"].max()) - float(row["entry_price"])) / stop_distance

    figure, axes = plt.subplots(2, 2, figsize=(18, 12), constrained_layout=False)
    ax_decision, ax_anatomy, ax_m15, ax_h1 = axes.flatten()
    draw_candles(ax_decision, m5_asof, reserve_future=True)
    add_entry_snapshot_levels(ax_decision, row, include_geometry=True)
    ax_decision.axvline(len(m5_asof) - 0.5, color="#2c3e50", linewidth=1.4)
    ax_decision.set_title("M5 DECISION-AS-OF — broker server time; closed bars only; outcome hidden", fontsize=11, weight="bold")
    ax_decision.legend(loc="upper left", fontsize=7, ncol=2)

    draw_candles(ax_anatomy, m5_anatomy)
    add_entry_snapshot_levels(ax_anatomy, row, include_geometry=True)
    entry_x = int(np.searchsorted(m5_anatomy.index.values, entry.to_datetime64(), side="left"))
    exit_x = int(np.searchsorted(m5_anatomy.index.values, exit_time.to_datetime64(), side="right") - 1)
    entry_x = max(0, min(entry_x, len(m5_anatomy) - 1))
    exit_x = max(0, min(exit_x, len(m5_anatomy) - 1))
    ax_anatomy.scatter(entry_x, float(row["entry_price"]), marker="^" if direction == 1 else "v", s=110, color="#2c3e50", zorder=7, label="Entry marker")
    ax_anatomy.scatter(exit_x, float(row["exit_price"]), marker="X", s=100, color="#f39c12", edgecolor="black", zorder=7, label="Actual exit")
    ax_anatomy.axvspan(entry_x, exit_x, color="#f1c40f", alpha=0.08, label="Held interval")
    ax_anatomy.set_title(
        f"M5 OUTCOME ANATOMY — {row['outcome']} {row['net_R']:+.3f}R | {row['exit_class']} | hold {row['hold_minutes']:.1f}m",
        fontsize=11,
        weight="bold",
    )
    ax_anatomy.legend(loc="upper left", fontsize=7, ncol=2)

    draw_candles(ax_m15, m15_asof, reserve_future=True)
    if float(row["m15_vwap"]) > 0:
        ax_m15.axhline(float(row["m15_vwap"]), color="#2980b9", linestyle="--", linewidth=1.1, label="M15 VWAP @ entry")
        ax_m15.axhline(float(row["m15_close"]), color="#2c3e50", linestyle=":", linewidth=1.1, label="M15 close @ entry")
        ax_m15.legend(loc="upper left", fontsize=7)
    ax_m15.set_title("M15 decision context — broker server time; future hidden", fontsize=10, weight="bold")

    draw_candles(ax_h1, h1_asof, reserve_future=True)
    ax_h1.set_title("H1 decision context — broker server time; future hidden", fontsize=10, weight="bold")

    for ax in axes.flatten():
        ax.set_ylabel("EURUSD bid")

    active_logic = (
        "Range gates active: +/-2SD location + rejection candle + RSI; AVWAP/M15 dormant"
        if row["regime_label"] == "RANGE"
        else "Trend gates active: session VWAP pullback + confirmed AVWAP + M15 VWAP bias; RSI is telemetry-only"
    )
    metadata = (
        f"{row['case_id']} | stratum={row['stratum']} | position={int(row['position_id'])} | {row['event']} | "
        f"entry server={entry} | EA telemetry UTC={row['entry_time_utc']}\n"
        f"MT5 entry telemetry: regime={row['regime_label']} ORDER_ACCEPTED | ADX14={row['adx']:.3f} "
        f"(enter>=25, exit<19, dwell=6) | ATR14={row['atr']:.5f} | RSI14={row['rsi']:.3f} "
        f"(range long>25, short<75) | session VWAP={float(row['session_vwap']):.5f} SD={float(row['session_sd']):.5f} | "
        f"shadow VWAP={float(row['shadow_vwap']):.5f} SD={float(row['shadow_sd']):.5f}\n"
        f"AVWAP={float(row['anchored_vwap']):.5f} | M15 close/VWAP={float(row['m15_close']):.5f}/{float(row['m15_vwap']):.5f} | "
        f"spread={float(row['spread_pips']):.2f}p | estimated round-trip cost={float(row['estimated_cost_pips']):.2f}p | "
        f"risk={float(row['risk_pts']):.0f} points / ${float(row['initial_risk_account']):.2f}\n"
        f"Lifecycle outcome: net=${float(row['net_usd']):+.2f} ({float(row['net_R']):+.3f}R) | "
        f"MFE={mfe_r:.3f}R MAE={mae_r:.3f}R (bid-bar diagnostic) | {active_logic}\n"
        "Fidelity boundary: candles are D-side FivePercent M1 bid bars aligned on broker server_time and resampled for visualization; "
        "parquet time_utc is not used for price alignment because its DST convention diverges from EA telemetry during transition weeks. "
        "Entry indicator values are exact MT5 telemetry. "
        "Combined view is outcome-aware and cannot support a blind entry-quality claim."
    )
    figure.suptitle(f"VRAS REAL MODEL-0 FORENSIC CHART — {row['case_id']}", fontsize=15, weight="bold", y=0.985)
    figure.text(0.015, 0.012, metadata, fontsize=8.4, family="monospace", va="bottom")
    figure.subplots_adjust(top=0.94, bottom=0.17, hspace=0.28, wspace=0.16)

    output = CHARTS / f"{row['case_id']}_forensics.png"
    figure.savefig(output, dpi=180, facecolor="white")
    plt.close(figure)
    return {
        "case_id": row["case_id"],
        "position_id": int(row["position_id"]),
        "stratum": row["stratum"],
        "image": str(output.relative_to(ROOT)).replace("\\", "/"),
        "absolute_path": str(output),
        "sha256": sha256(output),
        "bytes": output.stat().st_size,
        "entry_time_server": entry.isoformat(),
        "exit_time_server": exit_time.isoformat(),
        "entry_time_utc_ea_telemetry": pd.Timestamp(row["entry_time_utc"]).isoformat(),
        "exit_time_utc_ea_telemetry": pd.Timestamp(row["exit_time_utc"]).isoformat(),
        "direction": int(row["direction"]),
        "event": row["event"],
        "regime": row["regime_label"],
        "net_R": round(float(row["net_R"]), 9),
        "net_usd": round(float(row["net_usd"]), 2),
        "mae_R_bid_bar_diagnostic": round(float(mae_r), 6),
        "mfe_R_bid_bar_diagnostic": round(float(mfe_r), 6),
        "decision_panel_outcome_hidden": True,
        "combined_file_outcome_aware": True,
        "m15_context_rendered": True,
        "h1_context_rendered": True,
        "mt5_entry_telemetry_rendered": True,
    }


def response_schema(batch_id: str) -> dict:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    return {
        "type": "object",
        "properties": {
            "batch_id": {"type": "string", "const": batch_id},
            "validity_boundary": {"type": "string"},
            "image_inspection_supported": {"type": "boolean"},
            "coverage": {
                "type": "object",
                "properties": {
                    "expected_images": {"type": "integer", "const": 5},
                    "images_opened": {"type": "integer", "minimum": 0, "maximum": 5},
                    "all_cases_reported": {"type": "boolean"},
                },
                "required": ["expected_images", "images_opened", "all_cases_reported"],
                "additionalProperties": False,
            },
            "cases": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "position_id": {"type": "integer"},
                        "image_opened": {"type": "boolean"},
                        "decision_panel_observation": {"type": "string"},
                        "outcome_anatomy_observation": {"type": "string"},
                        "success_or_failure_mechanism": {"type": "string"},
                        "strategy_logic_link": {"type": "string"},
                        "evidence_label": {"type": "string", "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"]},
                        "confidence": confidence,
                        "fidelity_note": {"type": "string"},
                    },
                    "required": [
                        "case_id",
                        "position_id",
                        "image_opened",
                        "decision_panel_observation",
                        "outcome_anatomy_observation",
                        "success_or_failure_mechanism",
                        "strategy_logic_link",
                        "evidence_label",
                        "confidence",
                        "fidelity_note",
                    ],
                    "additionalProperties": False,
                },
            },
            "ranked_mechanisms": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "minimum": 1, "maximum": 4},
                        "label": {"type": "string"},
                        "case_ids": {"type": "array", "items": {"type": "string"}},
                        "finding": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": ["rank", "label", "case_ids", "finding", "confidence"],
                    "additionalProperties": False,
                },
            },
            "logic_or_fidelity_contradictions": {"type": "array", "items": {"type": "string"}},
            "illegal_posthoc_actions_rejected": {"type": "array", "items": {"type": "string"}},
            "batch_verdict": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "batch_id",
            "validity_boundary",
            "image_inspection_supported",
            "coverage",
            "cases",
            "ranked_mechanisms",
            "logic_or_fidelity_contradictions",
            "illegal_posthoc_actions_rejected",
            "batch_verdict",
            "limitations",
        ],
        "additionalProperties": False,
    }


def build_requests(chart_rows: list[dict], selection_path: Path, packet_path: Path) -> None:
    for batch_id, batch_rows in (("A", chart_rows[:5]), ("B", chart_rows[5:])):
        batch_manifest = {
            "schema_version": "vras_grok_chart_batch.v1",
            "batch_id": batch_id,
            "hypothesis_id": HYPOTHESIS_ID,
            "run_id": RUN_ID,
            "image_count": 5,
            "images": batch_rows,
        }
        batch_manifest_path = EVIDENCE / f"grok_batch_{batch_id.lower()}_manifest.json"
        batch_manifest_path.write_text(json.dumps(batch_manifest, indent=2, default=str), encoding="utf-8")
        context = ROOT / ".context" / f"vras-003-grok-chart-{batch_id.lower()}-20260722"
        context.mkdir(parents=True, exist_ok=True)
        expected = [item["case_id"] for item in batch_rows]
        positions = [item["position_id"] for item in batch_rows]
        prompt = (
            f"Review exactly five REAL VRAS Model-0 combined forensic PNGs in batch {batch_id}. "
            f"Read the batch manifest {batch_manifest_path}, frozen selection {selection_path}, packet {packet_path}, "
            f"terminal readout {READOUT}, and exact run source {SOURCE}. Open every image absolute_path using image-capable inspection. "
            f"Expected case IDs in exact manifest order: {expected}; position IDs: {positions}. "
            "Each PNG contains an M5 decision-as-of panel, an M5 outcome anatomy panel, M15 and H1 decision context, "
            "and exact MT5 entry telemetry. Analyze price location, rejection/pullback structure, VWAP/SD/AVWAP/M15 confluence, "
            "ADX hysteresis context, RSI when active, stop/target geometry, MAE/MFE, hold, spread/cost, and why the path won or lost. "
            "The file is outcome-aware, so do not claim blinded entry assessment. Candles and MAE/MFE are D-side M1 bid-bar visualization "
            "aligned on broker server_time. The parquet UTC clock is intentionally not used for price alignment because its DST convention "
            "diverges from the EA clock during transition weeks; EA UTC remains printed as telemetry metadata. "
            "entry indicator values are exact MT5 telemetry. The tested object is terminal KILL for negative expectancy/cadence/regime whipsaw; "
            "this is advisory postmortem only. Do not propose threshold tuning, session/year vetoes, rerun, source patch, promotion, or rescue. "
            "Patterns may only be labeled HYPOTHESIS for a future independent preregistration. Report exactly five cases. "
            "If image inspection is unavailable, set image_inspection_supported=false and do not fabricate observations."
        )
        request = {
            "task": f"vras-003-grok-chart-forensics-{batch_id.lower()}",
            "request": {
                "model": "grok-4.5",
                "reasoning_effort": "high",
                "input": [
                    {
                        "role": "system",
                        "content": (
                            "You are a read-only senior systematic-trading chart forensic reviewer. "
                            "Use local evidence only; separate OBSERVED, STRONG_INFERENCE, HYPOTHESIS, and UNKNOWN. "
                            "You have no authority to modify files, rerun MT5, tune the killed EA, or use web search."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": f"vras_chart_forensics_batch_{batch_id.lower()}",
                        "schema": response_schema(batch_id),
                    },
                },
            },
            "meta": {
                "purpose": f"VRAS HYP-003 real chart forensics batch {batch_id}",
                "sample_seed": SEED,
                "expected_case_ids": expected,
                "expected_position_ids": positions,
                "authority": "ADVISORY_FORENSICS_ONLY",
            },
        }
        (context / "grok-request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    positions = load_position_truth()
    sample, selection_manifest = freeze_sample(positions)

    positions_path = EVIDENCE / "positions_truth_93.csv"
    selection_path = EVIDENCE / "selection_manifest.json"
    cases_path = EVIDENCE / "cases_selected_10.csv"
    positions.to_csv(positions_path, index=False, quoting=csv.QUOTE_MINIMAL)
    if selection_path.exists():
        frozen_selection = json.loads(selection_path.read_text(encoding="utf-8"))
        if frozen_selection.get("case_ids") != selection_manifest.get("case_ids"):
            raise RuntimeError("Existing frozen selection differs from deterministic resampling result")
        selection_manifest = frozen_selection
    else:
        selection_path.write_text(json.dumps(selection_manifest, indent=2), encoding="utf-8")
    sample.to_csv(cases_path, index=False, quoting=csv.QUOTE_MINIMAL)

    # Rendering begins only after the selection artifact exists on disk.
    m1 = pd.read_parquet(
        BARS_M1,
        columns=["time_server", "time_utc", "open", "high", "low", "close", "tick_volume"],
    )
    m1["time_server"] = pd.to_datetime(m1["time_server"])
    m1["time_utc"] = pd.to_datetime(m1["time_utc"])
    window_start = sample["entry_time_server"].min() - pd.Timedelta(days=4)
    window_end = sample["exit_time_server"].max() + pd.Timedelta(days=4)
    m1 = m1[(m1["time_server"] >= window_start) & (m1["time_server"] <= window_end)].copy()
    m5 = resample_ohlc(m1, "5min", time_col="time_server")
    m15 = resample_ohlc(m1, "15min", time_col="time_server")
    h1 = resample_ohlc(m1, "1h", time_col="time_server")

    m1_server = m1.set_index("time_server").sort_index()
    chart_rows = [render_case(row, m1_server, m5, m15, h1) for _, row in sample.iterrows()]
    casebook = {
        "schema_version": "vras_grok_chart_casebook.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "selection_manifest": str(selection_path.relative_to(ROOT)).replace("\\", "/"),
        "selection_manifest_sha256": sha256(selection_path),
        "source_m1_bars": str(BARS_M1.relative_to(ROOT)).replace("\\", "/"),
        "source_m1_sha256": sha256(BARS_M1),
        "primary_visualization": "M5 resampled closed bid bars aligned on broker server_time",
        "clock_fidelity_boundary": "EA telemetry UTC and parquet time_utc use different DST conventions during transition weeks; chart price alignment uses exact broker server_time",
        "context_timeframes": ["M15", "H1"],
        "indicator_source": "exact MT5 decision telemetry at entry snapshot",
        "combined_view_outcome_blind_limitation": True,
        "image_count": len(chart_rows),
        "images": chart_rows,
    }
    casebook_path = EVIDENCE / "casebook_manifest.json"
    casebook_path.write_text(json.dumps(casebook, indent=2), encoding="utf-8")

    packet = {
        "schema_version": "alphafactory_grok_chart_forensics_packet.v1",
        "created_at_utc": utc_now(),
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": "EA_VRAS_RegimeAdaptiveScalperV3",
        "run_id": RUN_ID,
        "authority": "ADVISORY_FORENSICS_ONLY",
        "validity_boundary": "VALID_DIAGNOSTIC_MODEL0; PROMOTION_INELIGIBLE; TERMINAL KILL FOR NEGATIVE EXPECTANCY/CADENCE/REGIME_WHIPSAW; COST PROVENANCE UNVERIFIED",
        "bindings": {
            "frozen_plan": {"path": str(PREREG.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(PREREG)},
            "source_snapshot": {"path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(SOURCE)},
            "run_manifest": {"path": str(RUN_MANIFEST.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(RUN_MANIFEST)},
            "report": {"path": str(REPORT.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(REPORT)},
            "lifecycle": {"path": str(LIFECYCLE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(LIFECYCLE)},
            "run_meta": {"path": str(RUN_META.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(RUN_META)},
            "decision_bars": {"path": str(BARS_M1.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(BARS_M1)},
            "indicator_capture": {
                "path": str(TELEMETRY.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(TELEMETRY),
                "provenance": "mt5_decision_telemetry",
            },
            "selection_manifest": {"path": str(selection_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(selection_path)},
            "casebook_manifest": {"path": str(casebook_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(casebook_path)},
        },
        "sampling_contract": {
            "frozen_before_chart_view": True,
            "seed": SEED,
            "population_definition": selection_manifest["population_definition"],
            "population_positions": 93,
            "strata": selection_manifest["sampling_rule"],
            "worker_assignment": "two disjoint sequential batches",
            "worker_a_cases": 5,
            "worker_b_cases": 5,
            "outcome_based_manual_selection_forbidden": True,
        },
        "chart_contract": {
            "primary_timeframe": "M5",
            "context_timeframes": ["M15", "H1"],
            "time_axes": ["broker_server_time_for_price_alignment", "ea_telemetry_utc_in_metadata"],
            "clock_fidelity_boundary": "parquet time_utc is not used for chart alignment because its DST convention can differ by one hour from the EA clock contract during transition weeks",
            "decision_asof_panel": {"closed_bars_only": True, "outcome_hidden_inside_panel": True, "future_region_hidden": True},
            "anatomy_panel": {"entry_visible": True, "initial_sl_visible": True, "tp_visible": True, "actual_exit_visible": True, "mae_mfe_hold_visible": True},
            "combined_file": {"outcome_aware": True, "cannot_support_blind_entry_claim": True},
            "active_indicator_contract": {"entry_snapshot_exact_mt5_telemetry": True, "all_active_gate_values_labeled": True},
            "rendering": {"canonical_high_resolution_png": True, "per_image_sha256_bound": True, "image_count": 10},
        },
        "grok_runner_contract": {
            "request_root": ".context/vras-003-grok-chart-{a|b}-20260722",
            "dry_run_before_actual": True,
            "cases_per_job": 5,
            "global_backend_concurrency": 1,
            "reasoning_effort": "high",
            "no_subagents": True,
            "web_search_disabled": True,
            "timeout_seconds": 600,
        },
        "response_acceptance": {
            "runner_success": True,
            "response_useful": True,
            "schema_pass": True,
            "exact_case_and_position_ids": True,
            "image_opened_true_per_case": True,
            "unique_union_matches_frozen_manifest": True,
            "parent_lifecycle_and_source_qc": True,
        },
        "output_contract": {
            "evidence_labels": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"],
            "direct_ea_patch_authorized": False,
            "rerun_or_rescue_authorized": False,
            "new_hypotheses_require_fresh_preregistration": True,
        },
    }
    packet_path = EVIDENCE / "GROK_CHART_FORENSICS_PACKET.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    build_requests(chart_rows, selection_path, packet_path)
    print(
        json.dumps(
            {
                "status": "VRAS_GROK_CHART_PACKET_READY",
                "population": 93,
                "selected": 10,
                "images": 10,
                "selection_manifest": str(selection_path),
                "casebook_manifest": str(casebook_path),
                "packet": str(packet_path),
                "request_a": str(ROOT / ".context" / "vras-003-grok-chart-a-20260722" / "grok-request.json"),
                "request_b": str(ROOT / ".context" / "vras-003-grok-chart-b-20260722" / "grok-request.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
