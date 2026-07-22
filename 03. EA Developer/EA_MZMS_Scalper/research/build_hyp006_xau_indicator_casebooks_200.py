#!/usr/bin/env python3
"""Build two 100-image, indicator-rich loser casebooks for HYP-006.

The selection is frozen before rendering. Each PNG contains a closed-bar
decision view and an outcome view, with the active strategy surfaces rendered
from the post-run FivePercent M5 bar export: EMA200, MACD 12/26/9 histogram,
RSI14, ADX14, ATR14, and lifecycle entry/SL/TP/exit geometry.

The recomputed indicators are diagnostic visual context, not MT5 tester parity
proof. Lifecycle and the exact source snapshot remain execution truth.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006"
RUN_ID = "20260721_190051"
SEED = 5600722
SAMPLE_SIZE = 100
POINT = 0.01
RR = 1.60

RUN_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_MZMS_Scalper" / RUN_ID
LIFECYCLE = (
    RUN_DIR
    / "logs"
    / "XAUUSD_LifecycleTrades_HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_85323953.csv"
)
RUN_META = (
    RUN_DIR
    / "logs"
    / "XAUUSD_RunMeta_HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_85323953.json"
)
SOURCE = RUN_DIR / "snapshot" / "source" / "EA_MZMS_Scalper.mq5"
REPORT = RUN_DIR / "report.html"
TERMINAL = (
    ROOT
    / "02. AlphaFactory"
    / "runtime"
    / "mt5-portable-fivepercent"
    / "terminal64.exe"
)
OLD_SELECTION = (
    Path(__file__).resolve().parent
    / "evidence"
    / f"{HYPOTHESIS_ID}_GROK_RANDOM_LOSER_FORENSICS"
    / "selection_manifest.json"
)
OUT = (
    Path(__file__).resolve().parent
    / "evidence"
    / f"{HYPOTHESIS_ID}_GROK_INDICATOR_FORENSICS_200"
)
BARS_FILE = OUT / "data" / "XAUUSD_M5_with_recomputed_strategy_indicators.parquet"
SELECTION_FILE = OUT / "selection_manifest.json"
FEATURES_FILE = OUT / "entry_indicator_features.csv"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_server_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def aggregate_losers() -> tuple[list[dict[str, Any]], int]:
    with LIFECYCLE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["position_id"]].append(row)

    losers: list[dict[str, Any]] = []
    for position_id, position_rows in grouped.items():
        position_rows.sort(key=lambda row: row["event_time"])
        opens = [row for row in position_rows if row["action"] == "OPEN"]
        closes = [row for row in position_rows if row["action"] == "CLOSE"]
        if len(position_rows) != 2 or len(opens) != 1 or len(closes) != 1:
            raise RuntimeError(f"position {position_id} violates exact lifecycle pair")
        opened, closed = opens[0], closes[0]
        net = sum(float(row["deal_net"]) for row in position_rows)
        if net >= 0.0:
            continue
        direction = 1 if opened["order_type"] == "BUY" else -1
        entry = float(opened["price"])
        risk_pts = float(opened["risk_pts"])
        risk_account = float(opened["initial_risk_account"])
        risk_price = risk_pts * POINT
        entry_time = parse_server_time(opened["event_time"])
        exit_time = parse_server_time(closed["event_time"])
        losers.append(
            {
                "position_id": int(position_id),
                "direction": direction,
                "side": opened["order_type"],
                "entry_time_server": opened["event_time"],
                "entry": entry,
                "exit_time_server": closed["event_time"],
                "exit": float(closed["price"]),
                "risk_pts": risk_pts,
                "initial_risk_account": risk_account,
                "net_usd": net,
                "net_R": net / risk_account if risk_account > 0.0 else None,
                "sl": entry - direction * risk_price if risk_pts > 0.0 else None,
                "tp": entry + direction * RR * risk_price if risk_pts > 0.0 else None,
                "hold_minutes": (exit_time - entry_time).total_seconds() / 60.0,
            }
        )
    losers.sort(key=lambda item: int(item["position_id"]))
    return losers, len(grouped)


def old_position_ids() -> set[int]:
    if not OLD_SELECTION.exists():
        return set()
    data = json.loads(OLD_SELECTION.read_text(encoding="utf-8"))
    return {
        int(position_id)
        for worker in data.get("workers", {}).values()
        for position_id in worker.get("position_ids", [])
    }


def freeze_selection() -> dict[str, Any]:
    losers, population_positions = aggregate_losers()
    excluded = old_position_ids()
    eligible = [item for item in losers if int(item["position_id"]) not in excluded]
    random.Random(SEED).shuffle(eligible)
    required = SAMPLE_SIZE * 2
    if len(eligible) < required:
        raise RuntimeError(f"need {required} eligible losers, found {len(eligible)}")
    workers = {
        "worker_a": eligible[:SAMPLE_SIZE],
        "worker_b": eligible[SAMPLE_SIZE:required],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "charts" / "worker_a").mkdir(parents=True, exist_ok=True)
    (OUT / "charts" / "worker_b").mkdir(parents=True, exist_ok=True)
    frozen = {
        "schema_version": "mzms_indicator_forensics_selection.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "validity_verdict": "INVALID_ENGINEERING_RUN",
        "invalidity_reason": "tester_history_quality_98_below_frozen_99_gate",
        "selection_frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_frozen_before_chart_rendering": True,
        "population_rule": "exact OPEN+CLOSE lifecycle pairs; loser iff sum(deal_net) < 0",
        "population_positions": population_positions,
        "losing_positions": len(losers),
        "excluded_prior_reviewed_positions": sorted(excluded),
        "eligible_losing_positions_after_exclusion": len(eligible),
        "seed": SEED,
        "sampling_method": (
            "sort numeric position_id, exclude prior 40 reviewed positions, deterministic "
            "Python random.Random shuffle; worker_a indices 0:100, worker_b 100:200"
        ),
        "sample_size_per_worker": SAMPLE_SIZE,
        "disjoint_worker_samples": True,
        "one_indicator_rich_png_per_position": True,
        "expected_pngs_per_worker": SAMPLE_SIZE,
        "source_artifacts": {
            "lifecycle": str(LIFECYCLE),
            "lifecycle_sha256": sha256_file(LIFECYCLE),
            "run_meta": str(RUN_META),
            "run_meta_sha256": sha256_file(RUN_META),
            "report": str(REPORT),
            "report_sha256": sha256_file(REPORT),
            "source_snapshot": str(SOURCE),
            "source_snapshot_sha256": sha256_file(SOURCE),
        },
        "workers": {
            worker: {
                "sample_slice": "0:100" if worker == "worker_a" else "100:200",
                "position_ids": [int(item["position_id"]) for item in records],
                "cases": records,
            }
            for worker, records in workers.items()
        },
        "interpretation_boundary": (
            "Loser-only image review is mechanism discovery. It cannot estimate population "
            "prevalence, prove causality, tune thresholds, or repair invalid parent history."
        ),
    }
    SELECTION_FILE.write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    return frozen


def export_full_m5_history() -> pd.DataFrame:
    if not mt5.initialize(path=str(TERMINAL), portable=True, timeout=60_000):
        raise RuntimeError(f"MetaTrader5 initialize failed: {mt5.last_error()}")
    frames: list[pd.DataFrame] = []
    start = datetime(2017, 1, 1, tzinfo=timezone.utc)
    finish = datetime(2026, 7, 22, tzinfo=timezone.utc)
    cursor = start
    try:
        while cursor < finish:
            boundary = min(datetime(cursor.year + 1, 1, 1, tzinfo=timezone.utc), finish)
            rates = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M5, cursor, boundary)
            if rates is None or len(rates) == 0:
                raise RuntimeError(
                    f"no XAUUSD M5 rates for {cursor:%Y}: {mt5.last_error()}"
                )
            frames.append(pd.DataFrame(rates))
            print(f"EXPORT year={cursor.year} rows={len(rates)}", flush=True)
            cursor = boundary
    finally:
        mt5.shutdown()
    bars = pd.concat(frames, ignore_index=True)
    bars = bars.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    bars["time_utc"] = pd.to_datetime(bars["time"], unit="s", utc=True).dt.tz_localize(None)
    return bars[
        ["time_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    ]


def recompute_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    result = bars.copy()
    close = result["close"].astype(float)
    high = result["high"].astype(float)
    low = result["low"].astype(float)
    ema = lambda series, period: series.ewm(span=period, adjust=False).mean()
    rma = lambda series, period: series.ewm(alpha=1.0 / period, adjust=False).mean()

    result["ema200"] = ema(close, 200)
    result["macd_main"] = ema(close, 12) - ema(close, 26)
    result["macd_signal"] = ema(result["macd_main"], 9)
    result["macd_hist"] = result["macd_main"] - result["macd_signal"]

    delta = close.diff()
    average_gain = rma(delta.clip(lower=0.0), 14)
    average_loss = rma((-delta.clip(upper=0.0)), 14)
    rs = average_gain / average_loss.replace(0.0, np.nan)
    result["rsi14"] = 100.0 - (100.0 / (1.0 + rs))

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            (high - low).abs(),
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr14"] = rma(true_range, 14)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
    plus_di = 100.0 * rma(plus_dm, 14) / result["atr14"]
    minus_di = 100.0 * rma(minus_dm, 14) / result["atr14"]
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    result["adx14"] = rma(dx, 14)
    return result


def entry_feature_rows(
    bars: pd.DataFrame, selection: dict[str, Any]
) -> list[dict[str, Any]]:
    times = bars["time_utc"].to_numpy(dtype="datetime64[ns]")
    rows: list[dict[str, Any]] = []
    for worker, worker_data in selection["workers"].items():
        for number, case in enumerate(worker_data["cases"], 1):
            entry_time = np.datetime64(parse_server_time(case["entry_time_server"]))
            entry_index = int(times.searchsorted(entry_time, side="left"))
            if entry_index < 3:
                raise RuntimeError(f"insufficient closed bars for P{case['position_id']}")
            shift3, shift2, shift1 = (
                bars.iloc[entry_index - 3],
                bars.iloc[entry_index - 2],
                bars.iloc[entry_index - 1],
            )
            local_bottom = bool(
                shift1.macd_hist > shift2.macd_hist
                and shift2.macd_hist < shift3.macd_hist
                and shift2.macd_hist <= 0.0
            )
            local_top = bool(
                shift1.macd_hist < shift2.macd_hist
                and shift2.macd_hist > shift3.macd_hist
                and shift2.macd_hist >= 0.0
            )
            delta_atr = float(abs(shift1.macd_hist - shift2.macd_hist) / shift1.atr14)
            bullish = bool(shift1.close > shift1.open and shift1.close > shift1.ema200)
            bearish = bool(shift1.close < shift1.open and shift1.close < shift1.ema200)
            rsi_long = bool(42.0 <= shift1.rsi14 <= 58.0 and shift1.rsi14 > shift2.rsi14)
            rsi_short = bool(42.0 <= shift1.rsi14 <= 58.0 and shift1.rsi14 < shift2.rsi14)
            direction = int(case["direction"])
            parity = bool(
                shift1.adx14 >= 18.0
                and delta_atr >= 0.01
                and (
                    (direction > 0 and local_bottom and bullish and rsi_long)
                    or (direction < 0 and local_top and bearish and rsi_short)
                )
            )
            rows.append(
                {
                    "worker": worker,
                    "case_id": f"{worker[-1].upper()}-{number:03d}-P{case['position_id']}",
                    "position_id": int(case["position_id"]),
                    "side": case["side"],
                    "entry_time_server": case["entry_time_server"],
                    "shift1_bar_time": str(shift1.time_utc),
                    "shift2_bar_time": str(shift2.time_utc),
                    "shift3_bar_time": str(shift3.time_utc),
                    "ema200": float(shift1.ema200),
                    "macd_hist1": float(shift1.macd_hist),
                    "macd_hist2": float(shift2.macd_hist),
                    "macd_hist3": float(shift3.macd_hist),
                    "local_bottom_recomputed": local_bottom,
                    "local_top_recomputed": local_top,
                    "delta_atr_recomputed": delta_atr,
                    "rsi1_recomputed": float(shift1.rsi14),
                    "rsi2_recomputed": float(shift2.rsi14),
                    "adx1_recomputed": float(shift1.adx14),
                    "atr1_recomputed": float(shift1.atr14),
                    "bullish_ema_recomputed": bullish,
                    "bearish_ema_recomputed": bearish,
                    "source_direction_conditions_recomputed": parity,
                }
            )
    return rows


def write_features(rows: list[dict[str, Any]]) -> None:
    with FEATURES_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_worker_cases(selection: dict[str, Any], features: list[dict[str, Any]]) -> None:
    feature_by_position = {int(item["position_id"]): item for item in features}
    for worker, worker_data in selection["workers"].items():
        path = OUT / f"{worker}_cases.csv"
        rows: list[dict[str, Any]] = []
        for number, case in enumerate(worker_data["cases"], 1):
            feature = feature_by_position[int(case["position_id"])]
            rows.append(
                {
                    "case_id": f"{worker[-1].upper()}-{number:03d}-P{case['position_id']}",
                    "position_id": int(case["position_id"]),
                    "side": case["side"],
                    "direction": int(case["direction"]),
                    "entry_time_server": case["entry_time_server"],
                    "entry": float(case["entry"]),
                    "sl": "" if case["sl"] is None else float(case["sl"]),
                    "tp": "" if case["tp"] is None else float(case["tp"]),
                    "exit_time_server": case["exit_time_server"],
                    "exit": float(case["exit"]),
                    "net_usd": float(case["net_usd"]),
                    "net_R": "" if case["net_R"] is None else float(case["net_R"]),
                    "hold_minutes": float(case["hold_minutes"]),
                    "risk_pts": float(case["risk_pts"]),
                    "recomputed_signal_parity": feature[
                        "source_direction_conditions_recomputed"
                    ],
                }
            )
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def prepare() -> None:
    selection = freeze_selection()
    if BARS_FILE.exists():
        bars = pd.read_parquet(BARS_FILE).sort_values("time_utc").reset_index(drop=True)
        print(f"REUSE bars={BARS_FILE} rows={len(bars)}", flush=True)
    else:
        bars = recompute_indicators(export_full_m5_history())
        bars.to_parquet(BARS_FILE, index=False)
    features = entry_feature_rows(bars, selection)
    write_features(features)
    write_worker_cases(selection, features)

    selection["bar_indicator_artifact"] = {
        "path": str(BARS_FILE),
        "sha256": sha256_file(BARS_FILE),
        "row_count": len(bars),
        "first_bar": str(bars["time_utc"].min()),
        "last_bar": str(bars["time_utc"].max()),
        "source": "MetaTrader5.copy_rates_range from portable FivePercent terminal on D:",
        "clock_note": (
            "time_utc is a renderer compatibility name; raw MT5 epochs are aligned "
            "directly with lifecycle server-clock timestamps"
        ),
        "formulas": (
            "pandas recursive EMA/RMA approximation for EMA200, MACD12/26/9, RSI14, "
            "ATR14 and ADX14"
        ),
        "fidelity_boundary": (
            "Recomputed indicators are visual diagnostic context, not MT5 CopyBuffer "
            "parity and not tester tick-history repair. Lifecycle/source are truth."
        ),
    }
    selection["entry_indicator_features"] = {
        "path": str(FEATURES_FILE),
        "sha256": sha256_file(FEATURES_FILE),
        "rows": len(features),
        "recomputed_full_direction_condition_passes": sum(
            str(item["source_direction_conditions_recomputed"]).lower() == "true"
            for item in features
        ),
        "interpretation": (
            "A recomputed FAIL is not an EA logic violation; it records post-run bar/formula "
            "non-parity under the already-invalid 98% parent history."
        ),
    }
    for worker in ("worker_a", "worker_b"):
        case_path = OUT / f"{worker}_cases.csv"
        selection["workers"][worker]["case_csv"] = str(case_path)
        selection["workers"][worker]["case_csv_sha256"] = sha256_file(case_path)
    SELECTION_FILE.write_text(json.dumps(selection, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "selection": str(SELECTION_FILE),
                "bars": str(BARS_FILE),
                "bar_rows": len(bars),
                "features": len(features),
                "recomputed_parity": selection["entry_indicator_features"][
                    "recomputed_full_direction_condition_passes"
                ],
            },
            indent=2,
        )
    )


def draw_candles(ax: Any, frame: pd.DataFrame) -> None:
    for index, row in enumerate(frame.itertuples(index=False)):
        up = row.close >= row.open
        color = "#15803d" if up else "#dc2626"
        ax.vlines(index, row.low, row.high, color=color, linewidth=0.7, zorder=2)
        lower = min(row.open, row.close)
        height = max(abs(row.close - row.open), 1e-8)
        ax.add_patch(
            plt.Rectangle(
                (index - 0.34, lower),
                0.68,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.35,
                zorder=3,
            )
        )
    ax.set_xlim(-1, len(frame))


def time_ticks(ax: Any, frame: pd.DataFrame) -> None:
    step = max(1, len(frame) // 7)
    ticks = list(range(0, len(frame), step))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [pd.Timestamp(frame["time_utc"].iloc[index]).strftime("%m-%d %H:%M") for index in ticks],
        rotation=25,
        ha="right",
        fontsize=7,
    )


def draw_indicator_column(
    axes: list[Any],
    frame: pd.DataFrame,
    case: dict[str, str],
    feature: dict[str, str],
    outcome: bool,
) -> None:
    price_ax, macd_ax, rsi_ax, adx_ax = axes
    draw_candles(price_ax, frame)
    price_ax.plot(range(len(frame)), frame["ema200"], color="#2563eb", linewidth=1.2, label="EMA200")
    price_ax.axhline(float(case["entry"]), color="#1d4ed8", linestyle="--", linewidth=1.0, label="Entry")
    if case["sl"]:
        price_ax.axhline(float(case["sl"]), color="#dc2626", linestyle=":", linewidth=1.0, label="SL")
    if case["tp"]:
        price_ax.axhline(float(case["tp"]), color="#15803d", linestyle=":", linewidth=1.0, label="TP")

    entry_t = pd.Timestamp(case["entry_time_server"])
    entry_x = int(frame["time_utc"].to_numpy(dtype="datetime64[ns]").searchsorted(entry_t.to_datetime64()))
    entry_x = min(max(entry_x, 0), len(frame) - 1)
    price_ax.scatter([entry_x], [float(case["entry"])], marker="^" if int(case["direction"]) > 0 else "v", s=85, color="#1d4ed8", edgecolor="black", zorder=7)
    if outcome:
        exit_t = pd.Timestamp(case["exit_time_server"])
        exit_x = int(frame["time_utc"].to_numpy(dtype="datetime64[ns]").searchsorted(exit_t.to_datetime64()))
        exit_x = min(max(exit_x, 0), len(frame) - 1)
        price_ax.scatter([exit_x], [float(case["exit"])], marker="X", s=95, color="#7e22ce", edgecolor="black", zorder=8)
        for ax in axes:
            ax.axvline(entry_x, color="#1d4ed8", linestyle="--", linewidth=0.7, alpha=0.7)
            ax.axvline(exit_x, color="#7e22ce", linestyle="-.", linewidth=0.7, alpha=0.7)
    else:
        price_ax.annotate(
            "ENTRY",
            (entry_x, float(case["entry"])),
            xytext=(-42, 18),
            textcoords="offset points",
            fontsize=8,
            color="#1d4ed8",
            fontweight="bold",
            arrowprops={"arrowstyle": "->", "color": "#1d4ed8"},
        )
    price_ax.set_title("DECISION: closed bars only" if not outcome else "OUTCOME: entry through exit", fontsize=10, fontweight="bold")
    price_ax.legend(loc="upper left", fontsize=7, ncol=4)
    price_ax.grid(alpha=0.18)

    colors = np.where(frame["macd_hist"].to_numpy() >= 0.0, "#16a34a", "#dc2626")
    macd_ax.bar(range(len(frame)), frame["macd_hist"], color=colors, width=0.75, alpha=0.72)
    macd_ax.plot(range(len(frame)), frame["macd_main"], color="#0f172a", linewidth=0.75, label="MACD main")
    macd_ax.plot(range(len(frame)), frame["macd_signal"], color="#f59e0b", linewidth=0.75, label="signal")
    macd_ax.axhline(0.0, color="black", linewidth=0.55)
    if not outcome and len(frame) >= 3:
        for offset, label in ((-3, "s3"), (-2, "s2"), (-1, "s1")):
            x = len(frame) + offset
            y = float(frame["macd_hist"].iloc[offset])
            macd_ax.scatter([x], [y], s=30, color="#7c3aed", zorder=5)
            macd_ax.annotate(label, (x, y), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=7)
    macd_ax.set_ylabel("MACD", fontsize=8)
    macd_ax.legend(loc="upper left", fontsize=6, ncol=2)
    macd_ax.grid(alpha=0.15)

    rsi_ax.plot(range(len(frame)), frame["rsi14"], color="#7c3aed", linewidth=1.0)
    rsi_ax.axhspan(42.0, 58.0, color="#ddd6fe", alpha=0.35)
    rsi_ax.axhline(42.0, color="#6d28d9", linestyle=":", linewidth=0.7)
    rsi_ax.axhline(58.0, color="#6d28d9", linestyle=":", linewidth=0.7)
    rsi_ax.set_ylim(0, 100)
    rsi_ax.set_ylabel("RSI14", fontsize=8)
    rsi_ax.grid(alpha=0.15)

    adx_ax.plot(range(len(frame)), frame["adx14"], color="#0f766e", linewidth=1.0, label="ADX14")
    adx_ax.axhline(18.0, color="#0f766e", linestyle=":", linewidth=0.8, label="ADX gate 18")
    atr_ax = adx_ax.twinx()
    atr_ax.plot(range(len(frame)), frame["atr14"], color="#f97316", linewidth=0.8, alpha=0.8, label="ATR14")
    adx_ax.set_ylabel("ADX14", fontsize=8)
    atr_ax.set_ylabel("ATR14", fontsize=8, color="#f97316")
    adx_ax.grid(alpha=0.15)
    adx_ax.legend(loc="upper left", fontsize=6, ncol=2)
    time_ticks(adx_ax, frame)
    price_ax.tick_params(labelbottom=False)
    macd_ax.tick_params(labelbottom=False)
    rsi_ax.tick_params(labelbottom=False)

    if not outcome:
        parity = str(feature["source_direction_conditions_recomputed"]).lower() == "true"
        direction = "BOTTOM/LONG" if int(case["direction"]) > 0 else "TOP/SHORT"
        snapshot = (
            f"Lifecycle signal: {direction}\n"
            f"hist s3/s2/s1: {float(feature['macd_hist3']):+.4f} / "
            f"{float(feature['macd_hist2']):+.4f} / {float(feature['macd_hist1']):+.4f}\n"
            f"|hist1-hist2|/ATR: {float(feature['delta_atr_recomputed']):.4f} (gate 0.01)\n"
            f"RSI s2->s1: {float(feature['rsi2_recomputed']):.1f}->{float(feature['rsi1_recomputed']):.1f} (42-58 + slope)\n"
            f"ADX: {float(feature['adx1_recomputed']):.1f} (gate 18) | ATR: {float(feature['atr1_recomputed']):.2f}\n"
            f"post-run recomputed full-condition parity: {'PASS' if parity else 'NON-PARITY'}"
        )
        price_ax.text(
            0.99,
            0.02,
            snapshot,
            transform=price_ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=7.3,
            family="monospace",
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#64748b", "alpha": 0.92},
        )


def render_worker(worker: str) -> None:
    if worker not in {"worker_a", "worker_b"}:
        raise ValueError(worker)
    cases_path = OUT / f"{worker}_cases.csv"
    with cases_path.open("r", encoding="utf-8", newline="") as handle:
        cases = list(csv.DictReader(handle))
    with FEATURES_FILE.open("r", encoding="utf-8", newline="") as handle:
        features = {row["case_id"]: row for row in csv.DictReader(handle) if row["worker"] == worker}
    bars = pd.read_parquet(BARS_FILE).sort_values("time_utc").reset_index(drop=True)
    times = bars["time_utc"].to_numpy(dtype="datetime64[ns]")
    output_dir = OUT / "charts" / worker
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for index, case in enumerate(cases, 1):
        entry_t = np.datetime64(parse_server_time(case["entry_time_server"]))
        exit_t = np.datetime64(parse_server_time(case["exit_time_server"]))
        entry_index = int(times.searchsorted(entry_t, side="left"))
        exit_index = int(times.searchsorted(exit_t, side="right"))
        decision = bars.iloc[max(0, entry_index - 180):entry_index].copy().reset_index(drop=True)
        outcome = bars.iloc[max(0, entry_index - 48):min(len(bars), exit_index + 8)].copy().reset_index(drop=True)
        if len(decision) < 100 or len(outcome) < 20:
            raise RuntimeError(f"insufficient chart bars for {case['case_id']}")

        fig = plt.figure(figsize=(20, 14), constrained_layout=True)
        grid = fig.add_gridspec(4, 2, height_ratios=[3.4, 1.15, 0.9, 0.95])
        left_axes = [fig.add_subplot(grid[row, 0]) for row in range(4)]
        right_axes = [fig.add_subplot(grid[row, 1]) for row in range(4)]
        draw_indicator_column(left_axes, decision, case, features[case["case_id"]], outcome=False)
        draw_indicator_column(right_axes, outcome, case, features[case["case_id"]], outcome=True)
        net_r_label = "N/A" if not case["net_R"] else f"{float(case['net_R']):.3f}R"
        fig.suptitle(
            f"{case['case_id']} | {case['side']} XAUUSD M5 | entry {case['entry_time_server']} @ {float(case['entry']):.2f} "
            f"| exit {case['exit_time_server']} @ {float(case['exit']):.2f} | {net_r_label} | hold {float(case['hold_minutes']):.1f}m",
            fontsize=13,
            fontweight="bold",
        )
        fig.text(
            0.5,
            0.002,
            "ACTIVE CONTRACT: closed-bar MACD histogram local extremum + ATR-normalized delta + EMA200 + RSI14 + ADX14 | "
            "Indicators recomputed from post-run M5 bars for visualization; lifecycle/source are truth; parent run INVALID 98% < 99%.",
            ha="center",
            fontsize=8.3,
            color="#7f1d1d",
        )
        image_path = output_dir / f"{case['case_id']}_strategy_indicators.png"
        fig.savefig(image_path, dpi=120, facecolor="white")
        plt.close(fig)
        results.append(
            {
                "case_id": case["case_id"],
                "position_id": int(case["position_id"]),
                "side": case["side"],
                "image": image_path.name,
                "sha256": sha256_file(image_path),
                "decision_bars": len(decision),
                "outcome_bars": len(outcome),
                "decision_cutoff_enforced": bool(decision["time_utc"].max() < pd.Timestamp(case["entry_time_server"])),
                "indicators": ["EMA200", "MACD12/26/9", "RSI14", "ADX14", "ATR14"],
                "recomputed_signal_parity": str(case["recomputed_signal_parity"]).lower() == "true",
            }
        )
        if index % 10 == 0:
            print(f"RENDER worker={worker} completed={index}/{len(cases)}", flush=True)

    manifest = {
        "schema_version": "mzms_strategy_indicator_casebook.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "worker": worker,
        "validity_boundary": "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99",
        "selection_manifest": str(SELECTION_FILE),
        "selection_manifest_sha256": sha256_file(SELECTION_FILE),
        "bars": str(BARS_FILE),
        "bars_sha256": sha256_file(BARS_FILE),
        "source_snapshot": str(SOURCE),
        "source_snapshot_sha256": sha256_file(SOURCE),
        "case_csv": str(cases_path),
        "case_csv_sha256": sha256_file(cases_path),
        "image_count": len(results),
        "one_png_per_position": True,
        "decision_region_outcome_blind": True,
        "combined_png_contains_outcome_region": True,
        "indicator_fidelity_boundary": (
            "Recomputed from post-run M5 bar export; not MT5 CopyBuffer or tester tick parity."
        ),
        "results": results,
    }
    manifest_path = output_dir / "casebook_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"CASEBOOK_OK worker={worker} images={len(results)} manifest={manifest_path}")


def verify() -> None:
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    a = set(selection["workers"]["worker_a"]["position_ids"])
    b = set(selection["workers"]["worker_b"]["position_ids"])
    old = set(selection["excluded_prior_reviewed_positions"])
    if len(a) != SAMPLE_SIZE or len(b) != SAMPLE_SIZE or not a.isdisjoint(b):
        raise RuntimeError("sample count/disjointness failed")
    if (a | b) & old:
        raise RuntimeError("prior reviewed position leaked into new sample")
    for worker in ("worker_a", "worker_b"):
        manifest_path = OUT / "charts" / worker / "casebook_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["image_count"] != SAMPLE_SIZE or len(manifest["results"]) != SAMPLE_SIZE:
            raise RuntimeError(f"{worker} image count failed")
        for item in manifest["results"]:
            image_path = manifest_path.parent / item["image"]
            if not image_path.exists() or sha256_file(image_path) != item["sha256"]:
                raise RuntimeError(f"image hash failed: {image_path}")
            if not item["decision_cutoff_enforced"]:
                raise RuntimeError(f"decision cutoff failed: {image_path}")
    print("INDICATOR_CASEBOOK_PACKET_OK workers=2 images_per_worker=100 total_images=200")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "render", "verify"))
    parser.add_argument("--worker", choices=("worker_a", "worker_b"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "render":
        if not args.worker:
            raise SystemExit("render requires --worker")
        render_worker(args.worker)
    else:
        verify()


if __name__ == "__main__":
    main()
