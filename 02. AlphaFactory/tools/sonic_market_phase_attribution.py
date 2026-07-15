#!/usr/bin/env python3
"""Attribute Sonic R trades to simple market-phase buckets.

The intent is falsification, not model fitting.  The script streams the
PVSRA/SR sidecar, joins only around actual trade entry bars, and reports where
the EA makes or loses money by phase, lane, session, year, half-year, and hour.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"

TIME_FORMATS = ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def parse_ts(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def newest_file(root: Path, pattern: str) -> Path | None:
    files = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def newest_standard_trade_file(root: Path) -> Path | None:
    files = [
        path
        for path in root.glob("*_Trades_*.csv")
        if "_PX6_" not in path.name and "_Ghost_" not in path.name
    ]
    files = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def newest_signals_file(root: Path) -> Path | None:
    files = sorted(root.glob("*_Signals_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


@dataclass
class Trade:
    row_id: int
    entry_ts: datetime
    exit_ts: datetime | None
    engine_variant: str
    entry_reason: str
    exit_reason: str
    direction: str
    session_tag: str
    weekday_tag: str
    pnl_net: float
    realized_r: float
    initial_r_points: float
    hold_minutes: float


def load_trades(path: Path) -> list[Trade]:
    trades: list[Trade] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_id, row in enumerate(reader, start=1):
            if (row.get("is_final_close") or "1").strip() not in {"1", "true", "TRUE"}:
                continue
            entry_ts = parse_ts(row.get("entry_server_ts", ""))
            if entry_ts is None:
                continue
            trades.append(
                Trade(
                    row_id=row_id,
                    entry_ts=entry_ts,
                    exit_ts=parse_ts(row.get("exit_server_ts", "")),
                    engine_variant=(row.get("engine_variant") or "UNKNOWN").strip() or "UNKNOWN",
                    entry_reason=(row.get("entry_reason") or "UNKNOWN").strip() or "UNKNOWN",
                    exit_reason=(row.get("exit_reason") or "UNKNOWN").strip() or "UNKNOWN",
                    direction=(row.get("direction") or "UNKNOWN").strip() or "UNKNOWN",
                    session_tag=(row.get("session_tag") or "UNKNOWN").strip() or "UNKNOWN",
                    weekday_tag=(row.get("weekday_tag") or "UNKNOWN").strip() or "UNKNOWN",
                    pnl_net=safe_float(row.get("pnl_net")),
                    realized_r=safe_float(row.get("realized_r")),
                    initial_r_points=safe_float(row.get("initial_r_points")),
                    hold_minutes=safe_float(row.get("hold_minutes")),
                )
            )
    return trades


def profit_factor(values: Iterable[float]) -> float:
    gross_win = sum(v for v in values if v > 0)
    gross_loss = -sum(v for v in values if v < 0)
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def bucket_summary(trades: list[Trade], labels: dict[int, dict[str, Any]], key: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        label = labels.get(trade.row_id, {})
        if key == "year":
            bucket = str(trade.entry_ts.year)
        elif key == "half_year":
            bucket = f"{trade.entry_ts.year}H{1 if trade.entry_ts.month <= 6 else 2}"
        elif key == "month":
            bucket = trade.entry_ts.strftime("%Y-%m")
        elif key == "hour":
            bucket = f"{trade.entry_ts.hour:02d}"
        elif key == "session":
            bucket = trade.session_tag
        elif key == "weekday":
            bucket = trade.weekday_tag
        elif key == "lane":
            bucket = trade.engine_variant
        elif key == "direction":
            bucket = trade.direction
        else:
            bucket = str(label.get(key, "UNJOINED") or "UNJOINED")
        buckets[bucket].append(trade)

    rows: list[dict[str, Any]] = []
    for bucket, members in buckets.items():
        pnls = [t.pnl_net for t in members]
        rs = [t.realized_r for t in members]
        wins = [v for v in pnls if v > 0]
        rows.append(
            {
                "bucket": bucket,
                "n": len(members),
                "net": round(sum(pnls), 2),
                "pf": round(profit_factor(pnls), 4),
                "win_rate_pct": round(100.0 * len(wins) / len(members), 2) if members else 0.0,
                "avg_r": round(sum(rs) / len(rs), 4) if rs else 0.0,
                "median_r": round(sorted(rs)[len(rs) // 2], 4) if rs else 0.0,
            }
        )
    return sorted(rows, key=lambda item: (-item["n"], item["bucket"]))


def classify_phase(
    close: float,
    lows36: list[float],
    highs36: list[float],
    closes36: list[float],
    ranges20: list[float],
) -> dict[str, Any]:
    if len(closes36) < 36 or len(ranges20) < 10:
        return {
            "market_phase": "UNKNOWN",
            "trend_delta_atr_36": None,
            "range_width_atr_36": None,
            "close_pos_36": None,
            "cross_count_36": None,
        }

    avg_range = max(sum(ranges20) / len(ranges20), 0.000001)
    hi = max(highs36)
    lo = min(lows36)
    width = max(hi - lo, 0.000001)
    delta = close - closes36[0]
    delta_atr = delta / avg_range
    width_atr = width / avg_range
    close_pos = (close - lo) / width
    mid = (hi + lo) / 2.0

    signs: list[int] = []
    for item in closes36:
        if item > mid:
            signs.append(1)
        elif item < mid:
            signs.append(-1)
        else:
            signs.append(0)
    cross_count = 0
    previous = 0
    for sign in signs:
        if sign == 0:
            continue
        if previous and sign != previous:
            cross_count += 1
        previous = sign

    if delta_atr >= 1.25 and close_pos >= 0.62:
        phase = "IMPULSE_UP"
    elif delta_atr <= -1.25 and close_pos <= 0.38:
        phase = "IMPULSE_DOWN"
    elif abs(delta_atr) <= 1.0 and cross_count >= 5 and width_atr <= 3.0:
        phase = "SIDEWAY_COMPRESSED"
    elif abs(delta_atr) <= 1.2 and cross_count >= 4 and width_atr <= 6.0:
        phase = "SIDEWAY_WIDE"
    else:
        phase = "TRANSITION"

    return {
        "market_phase": phase,
        "trend_delta_atr_36": round(delta_atr, 4),
        "range_width_atr_36": round(width_atr, 4),
        "close_pos_36": round(close_pos, 4),
        "cross_count_36": cross_count,
    }


def stream_phase_labels(pvsra_path: Path, trades: list[Trade]) -> dict[int, dict[str, Any]]:
    by_time: dict[datetime, list[Trade]] = defaultdict(list)
    lookup: dict[datetime, list[tuple[int, float]]] = defaultdict(list)
    for trade in trades:
        by_time[trade.entry_ts].append(trade)
        for offset_minutes in (-5, 0, 5):
            candidate = trade.entry_ts + timedelta(minutes=offset_minutes)
            lookup[candidate].append((trade.row_id, abs(offset_minutes)))

    labels: dict[int, dict[str, Any]] = {}
    best_distance: dict[int, float] = {}
    highs36: deque[float] = deque(maxlen=36)
    lows36: deque[float] = deque(maxlen=36)
    closes36: deque[float] = deque(maxlen=36)
    ranges20: deque[float] = deque(maxlen=20)

    with pvsra_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            ts = parse_ts(row.get("server_ts", ""))
            close = safe_float(row.get("bar_close"))
            high = safe_float(row.get("bar_high"))
            low = safe_float(row.get("bar_low"))
            bar_range = safe_float(row.get("bar_range_pips"), max(high - low, 0.0))
            if close <= 0 or high <= 0 or low <= 0:
                continue

            highs36.append(high)
            lows36.append(low)
            closes36.append(close)
            ranges20.append(max(bar_range, high - low, 0.000001))

            if ts is None or ts not in lookup:
                continue

            features = classify_phase(close, list(lows36), list(highs36), list(closes36), list(ranges20))
            features.update(
                {
                    "joined_server_ts": ts.strftime("%Y.%m.%d %H:%M:%S"),
                    "bar_spread": safe_float(row.get("bar_spread")),
                    "bar_range_pips": safe_float(row.get("bar_range_pips")),
                    "vol_rank_20": safe_int(row.get("vol_rank_20")),
                    "vol_vs_avg_20": safe_float(row.get("vol_vs_avg_20")),
                    "dist_close_to_quarter_pips": safe_float(row.get("dist_close_to_quarter_pips")),
                    "dist_high_to_prior_swing_high_pips": safe_float(row.get("dist_high_to_prior_swing_high_pips")),
                    "dist_low_to_prior_swing_low_pips": safe_float(row.get("dist_low_to_prior_swing_low_pips")),
                    "breaks_prior_swing_high": (row.get("breaks_prior_swing_high") or "").lower() == "true",
                    "breaks_prior_swing_low": (row.get("breaks_prior_swing_low") or "").lower() == "true",
                    "seq_5_high_volume_count": safe_int(row.get("seq_5_high_volume_count")),
                    "seq_5_climax_count": safe_int(row.get("seq_5_climax_count")),
                    "seq_context_candidate": (row.get("seq_context_candidate") or "").strip(),
                }
            )
            for row_id, distance in lookup[ts]:
                if row_id not in best_distance or distance < best_distance[row_id]:
                    labels[row_id] = dict(features)
                    labels[row_id]["join_distance_minutes"] = distance
                    best_distance[row_id] = distance
    return labels


def stream_signal_context(signals_path: Path, trades: list[Trade], labels: dict[int, dict[str, Any]]) -> int:
    lookup: dict[tuple[datetime, str, str], list[int]] = defaultdict(list)
    fallback_lookup: dict[tuple[datetime, str], list[int]] = defaultdict(list)
    for trade in trades:
        lookup[(trade.entry_ts, trade.direction, trade.engine_variant)].append(trade.row_id)
        fallback_lookup[(trade.entry_ts, trade.direction)].append(trade.row_id)

    joined = 0
    with signals_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("blocked_or_fired") or "").strip().upper() != "FIRED":
                continue
            ts = parse_ts(row.get("server_ts", ""))
            if ts is None:
                continue
            direction = (row.get("direction") or "").strip()
            variant = (row.get("engine_variant") or "").strip()
            row_ids = lookup.get((ts, direction, variant))
            if not row_ids:
                row_ids = fallback_lookup.get((ts, direction), [])
            if not row_ids:
                continue
            signal_fields = {
                "signal_engine_variant": variant,
                "signal_dragon_angle_class": (row.get("dragon_angle_class") or "").strip(),
                "signal_pvsra_bias": (row.get("pvsra_bias") or "").strip(),
                "signal_pvsra_event": (row.get("pvsra_event") or "").strip(),
                "signal_level_kind": (row.get("level_kind") or "").strip(),
                "signal_level_distance_pips": safe_float(row.get("level_distance_pips")),
                "signal_htf_bias_score": safe_float(row.get("htf_bias_score")),
                "signal_context_score": safe_float(row.get("context_score")),
                "signal_quality_score": safe_float(row.get("quality_score")),
                "signal_pvsra_grade": safe_int(row.get("pvsra_grade")),
                "signal_level_zone": (row.get("level_zone") or "").strip(),
                "signal_news_distance_min": safe_float(row.get("news_distance_min")),
                "signal_minutes_to_forced_flat": safe_float(row.get("minutes_to_forced_flat")),
                "signal_spread_pips": safe_float(row.get("spread_pips")),
                "signal_spread_regime": (row.get("spread_regime") or "").strip(),
                "signal_dragon_slope_atr": safe_float(row.get("dragon_slope_atr")),
                "signal_trend_slope_atr": safe_float(row.get("trend_slope_atr")),
                "signal_tick_volume_pct": safe_float(row.get("tick_volume_pct")),
                "signal_recent_accum_bias": safe_float(row.get("recent_accum_bias")),
                "signal_body_ratio": safe_float(row.get("body_ratio")),
                "signal_range_atr": safe_float(row.get("range_atr")),
                "signal_h1_bias": safe_int(row.get("h1_bias")),
                "signal_h4_bias": safe_int(row.get("h4_bias")),
                "signal_state_reason": (row.get("state_reason") or "").strip(),
            }
            for row_id in row_ids:
                labels.setdefault(row_id, {}).update(signal_fields)
                joined += 1
    return joined


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def trade_label_rows(trades: list[Trade], labels: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trade in trades:
        label = labels.get(trade.row_id, {})
        rows.append(
            {
                "row_id": trade.row_id,
                "entry_server_ts": trade.entry_ts.strftime("%Y.%m.%d %H:%M:%S"),
                "exit_server_ts": trade.exit_ts.strftime("%Y.%m.%d %H:%M:%S") if trade.exit_ts else "",
                "engine_variant": trade.engine_variant,
                "entry_reason": trade.entry_reason,
                "exit_reason": trade.exit_reason,
                "direction": trade.direction,
                "session_tag": trade.session_tag,
                "weekday_tag": trade.weekday_tag,
                "hour": trade.entry_ts.hour,
                "pnl_net": round(trade.pnl_net, 2),
                "realized_r": round(trade.realized_r, 4),
                "hold_minutes": round(trade.hold_minutes, 2),
                "market_phase": label.get("market_phase", "UNJOINED"),
                "trend_delta_atr_36": label.get("trend_delta_atr_36"),
                "range_width_atr_36": label.get("range_width_atr_36"),
                "close_pos_36": label.get("close_pos_36"),
                "cross_count_36": label.get("cross_count_36"),
                "bar_spread": label.get("bar_spread"),
                "vol_rank_20": label.get("vol_rank_20"),
                "vol_vs_avg_20": label.get("vol_vs_avg_20"),
                "dist_close_to_quarter_pips": label.get("dist_close_to_quarter_pips"),
                "seq_5_high_volume_count": label.get("seq_5_high_volume_count"),
                "seq_5_climax_count": label.get("seq_5_climax_count"),
                "seq_context_candidate": label.get("seq_context_candidate"),
                "join_distance_minutes": label.get("join_distance_minutes"),
                "signal_dragon_angle_class": label.get("signal_dragon_angle_class"),
                "signal_pvsra_bias": label.get("signal_pvsra_bias"),
                "signal_pvsra_event": label.get("signal_pvsra_event"),
                "signal_level_kind": label.get("signal_level_kind"),
                "signal_level_distance_pips": label.get("signal_level_distance_pips"),
                "signal_htf_bias_score": label.get("signal_htf_bias_score"),
                "signal_context_score": label.get("signal_context_score"),
                "signal_quality_score": label.get("signal_quality_score"),
                "signal_pvsra_grade": label.get("signal_pvsra_grade"),
                "signal_level_zone": label.get("signal_level_zone"),
                "signal_news_distance_min": label.get("signal_news_distance_min"),
                "signal_minutes_to_forced_flat": label.get("signal_minutes_to_forced_flat"),
                "signal_spread_pips": label.get("signal_spread_pips"),
                "signal_spread_regime": label.get("signal_spread_regime"),
                "signal_dragon_slope_atr": label.get("signal_dragon_slope_atr"),
                "signal_trend_slope_atr": label.get("signal_trend_slope_atr"),
                "signal_tick_volume_pct": label.get("signal_tick_volume_pct"),
                "signal_recent_accum_bias": label.get("signal_recent_accum_bias"),
                "signal_body_ratio": label.get("signal_body_ratio"),
                "signal_range_atr": label.get("signal_range_atr"),
                "signal_h1_bias": label.get("signal_h1_bias"),
                "signal_h4_bias": label.get("signal_h4_bias"),
                "signal_state_reason": label.get("signal_state_reason"),
            }
        )
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Sonic Market Phase Attribution - {payload['run_id']}",
        "",
        "## Verdict",
        "",
        f"- Trades: `{payload['trade_count']}`",
        f"- PVSRA joined: `{payload['joined_count']}` / `{payload['trade_count']}`",
        f"- Net: `${payload['overall']['net']}`",
        f"- PF: `{payload['overall']['pf']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Phase Breakdown",
        "",
        "| Phase | N | Net | PF | Win% | Avg R |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["by_market_phase"]:
        lines.append(
            f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} | {row['win_rate_pct']} | {row['avg_r']} |"
        )
    lines.extend(["", "## Year Breakdown", "", "| Year | N | Net | PF | Win% | Avg R |", "|---|---:|---:|---:|---:|---:|"])
    for row in payload["by_year"]:
        lines.append(
            f"| {row['bucket']} | {row['n']} | {row['net']} | {row['pf']} | {row['win_rate_pct']} | {row['avg_r']} |"
        )
    lines.extend(["", "## Lane x Phase", "", "| Lane | Phase | N | Net | PF | Win% | Avg R |", "|---|---|---:|---:|---:|---:|---:|"])
    for row in payload["by_lane_phase"][:30]:
        lines.append(
            f"| {row['lane']} | {row['phase']} | {row['n']} | {row['net']} | {row['pf']} | {row['win_rate_pct']} | {row['avg_r']} |"
        )
    lines.extend(["", "## Findings", ""])
    for finding in payload["findings"]:
        lines.append(f"- {finding}")
    lines.append("")
    return "\n".join(lines)


def pair_summary(trades: list[Trade], labels: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[Trade]] = defaultdict(list)
    for trade in trades:
        phase = labels.get(trade.row_id, {}).get("market_phase", "UNJOINED")
        buckets[(trade.engine_variant, str(phase))].append(trade)

    rows: list[dict[str, Any]] = []
    for (lane, phase), members in buckets.items():
        pnls = [t.pnl_net for t in members]
        rs = [t.realized_r for t in members]
        wins = [v for v in pnls if v > 0]
        rows.append(
            {
                "lane": lane,
                "phase": phase,
                "n": len(members),
                "net": round(sum(pnls), 2),
                "pf": round(profit_factor(pnls), 4),
                "win_rate_pct": round(100.0 * len(wins) / len(members), 2) if members else 0.0,
                "avg_r": round(sum(rs) / len(rs), 4) if rs else 0.0,
            }
        )
    return sorted(rows, key=lambda item: (-item["n"], item["lane"], item["phase"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Attribute Sonic R trades by market phase.")
    parser.add_argument("run", help="Run id or run directory.")
    parser.add_argument("--ea", default=DEFAULT_EA, help="EA name under AlphaFactory runs.")
    parser.add_argument("--out", default="", help="Optional output directory.")
    args = parser.parse_args()

    run_dir = run_dir_for(args.run, args.ea)
    logs_dir = run_dir / "analysis" / "logs"
    if not logs_dir.exists():
        raise SystemExit(f"logs directory not found: {logs_dir}")

    trade_path = newest_standard_trade_file(logs_dir)
    pvsra_path = newest_file(logs_dir, "*_PVSRA_SR_Fields_*.csv")
    signals_path = newest_signals_file(logs_dir)
    if trade_path is None:
        raise SystemExit(f"trade sidecar not found under {logs_dir}")

    trades = load_trades(trade_path)
    labels: dict[int, dict[str, Any]] = {}
    if pvsra_path is not None:
        labels = stream_phase_labels(pvsra_path, trades)
    signal_joined_count = 0
    if signals_path is not None:
        signal_joined_count = stream_signal_context(signals_path, trades, labels)

    pnls = [trade.pnl_net for trade in trades]
    overall = {
        "n": len(trades),
        "net": round(sum(pnls), 2),
        "pf": round(profit_factor(pnls), 4),
        "win_rate_pct": round(100.0 * len([v for v in pnls if v > 0]) / len(pnls), 2) if pnls else 0.0,
    }

    findings: list[str] = []
    by_phase = bucket_summary(trades, labels, "market_phase")
    phase_map = {row["bucket"]: row for row in by_phase}
    sideway_net = sum(row["net"] for row in by_phase if str(row["bucket"]).startswith("SIDEWAY"))
    impulse_net = sum(row["net"] for row in by_phase if str(row["bucket"]).startswith("IMPULSE"))
    if overall["pf"] < 1.0:
        findings.append("Long-window current stack is not robust: overall PF is below 1.0.")
    if sideway_net < 0:
        findings.append(f"Sideway phases are net negative ({sideway_net:.2f}); do not loosen range entries without a new thesis.")
    if impulse_net > 0 and sideway_net < 0:
        findings.append("Current edge is more trend/impulse-dependent than range-scalping capable.")
    for year_row in bucket_summary(trades, labels, "year"):
        if year_row["n"] >= 40 and year_row["pf"] < 0.9:
            findings.append(f"Year {year_row['bucket']} is a weak regime: PF {year_row['pf']} over {year_row['n']} trades.")

    verdict = "REVIEW"
    if overall["pf"] < 1.0:
        verdict = "FAIL_LONG_WINDOW"
    elif any(row["bucket"].startswith("SIDEWAY") and row["pf"] < 1.0 for row in by_phase):
        verdict = "REVIEW_SIDEWAY_FRAGILE"

    payload = {
        "schema_version": "sonic_market_phase_attribution.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "trade_file": str(trade_path),
        "pvsra_file": str(pvsra_path) if pvsra_path else None,
        "signals_file": str(signals_path) if signals_path else None,
        "trade_count": len(trades),
        "joined_count": len(labels),
        "signal_joined_count": signal_joined_count,
        "overall": overall,
        "verdict": verdict,
        "by_market_phase": by_phase,
        "by_year": bucket_summary(trades, labels, "year"),
        "by_half_year": bucket_summary(trades, labels, "half_year"),
        "by_session": bucket_summary(trades, labels, "session"),
        "by_weekday": bucket_summary(trades, labels, "weekday"),
        "by_hour": bucket_summary(trades, labels, "hour"),
        "by_lane": bucket_summary(trades, labels, "lane"),
        "by_direction": bucket_summary(trades, labels, "direction"),
        "by_lane_phase": pair_summary(trades, labels),
        "findings": findings,
    }

    out_dir = Path(args.out).resolve() if args.out else run_dir / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "market_phase_attribution.json"
    md_path = out_dir / "market_phase_attribution.md"
    csv_path = out_dir / "market_phase_attribution_by_phase.csv"
    lane_phase_csv_path = out_dir / "market_phase_attribution_by_lane_phase.csv"
    trade_labels_csv_path = out_dir / "market_phase_trade_labels.csv"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    write_csv(csv_path, by_phase)
    write_csv(lane_phase_csv_path, payload["by_lane_phase"])
    write_csv(trade_labels_csv_path, trade_label_rows(trades, labels))

    print(json.dumps({"run_id": run_dir.name, "verdict": verdict, "outputs": [str(json_path), str(md_path)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
