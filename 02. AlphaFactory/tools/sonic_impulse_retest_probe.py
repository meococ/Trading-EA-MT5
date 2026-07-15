#!/usr/bin/env python3
"""Offline post-impulse retest probe for Sonic R XAU M5 research.

The compression breakout probe showed that chasing the breakout close is weak.
This script tests the trader-like alternative: detect a compression breakout,
then only label the first pullback/retest/reclaim of the broken level.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from sonic_compression_impulse_probe import (  # noqa: E402
    ALPHA_ROOT,
    DEFAULT_EA,
    Bar,
    half_year,
    label_candidate,
    load_bars,
    logs_dir,
    price_cross_count,
    profit_factor,
    run_dir_for,
    session_bucket,
)


@dataclass(frozen=True, slots=True)
class RetestConfig:
    config_id: str
    lookback: int
    atr_lookback: int
    max_width_atr: float
    min_crosses: int
    breakout_expansion_mult: float
    min_breakout_body_ratio: float
    min_breakout_vol_vs_avg: float
    max_breakout_extension_atr: float
    retest_window: int
    retest_tolerance_atr: float
    max_entry_extension_atr: float
    require_rejection: bool
    stop_buffer_atr: float
    max_risk_atr: float
    target_rr: float
    horizon_bars: int


@dataclass
class RetestCandidate:
    config_id: str
    setup: str
    breakout_ts: str
    server_ts: str
    bar_time: str
    direction: str
    retest_bars_after_breakout: int
    entry: float
    stop: float
    target: float
    target_rr: float
    risk_pips: float
    compression_bars: int
    width_pips: float
    width_atr: float
    avg_range_pips: float
    cross_count: int
    breakout_extension_atr: float
    entry_extension_atr: float
    breakout_expansion_ratio: float
    breakout_body_ratio: float
    retest_body_ratio: float
    retest_rejection_ratio: float
    breakout_vol_vs_avg_20: float
    session_bucket: str
    hour: int
    weekday: int
    half_year: str
    year: int
    hit_tp_first: bool
    hit_sl_first: bool
    label_r: float
    label_r_after_cost: float
    mfe_r: float
    mae_r: float
    bars_to_mfe: int
    bars_to_mae: int


def configs() -> list[RetestConfig]:
    return [
        RetestConfig("RETEST_12_R06", 12, 20, 4.5, 1, 1.05, 0.35, 0.75, 1.25, 5, 0.35, 0.80, True, 0.16, 1.80, 0.60, 8),
        RetestConfig("RETEST_24_R08", 24, 20, 6.0, 2, 1.00, 0.34, 0.75, 1.25, 7, 0.40, 0.85, True, 0.18, 2.20, 0.80, 10),
        RetestConfig("RETEST_24_R10", 24, 20, 6.0, 2, 1.00, 0.34, 0.75, 1.35, 8, 0.45, 0.95, False, 0.18, 2.40, 1.00, 12),
        RetestConfig("RETEST_36_R08", 36, 20, 7.0, 2, 1.00, 0.34, 0.75, 1.35, 8, 0.45, 0.90, True, 0.18, 2.60, 0.80, 12),
        RetestConfig("RETEST_36_R12", 36, 20, 7.0, 2, 1.05, 0.36, 0.85, 1.35, 10, 0.45, 1.00, False, 0.18, 2.80, 1.20, 16),
        RetestConfig("RETEST_48_R10", 48, 20, 8.0, 3, 1.00, 0.34, 0.75, 1.45, 10, 0.50, 1.00, True, 0.18, 3.00, 1.00, 16),
    ]


def safe_mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def breakout_ok(
    bars: list[Bar],
    idx: int,
    cfg: RetestConfig,
    direction: int,
    range_high: float,
    range_low: float,
    avg_range_pips: float,
    atr_price: float,
) -> tuple[bool, float, float]:
    bar = bars[idx]
    body = abs(bar.close - bar.open)
    bar_range = max(bar.high - bar.low, atr_price * 0.01)
    body_ratio = body / bar_range
    expansion_ratio = bar.range_pips / avg_range_pips if avg_range_pips > 0 else 0.0
    if expansion_ratio < cfg.breakout_expansion_mult:
        return False, 0.0, 0.0
    if body_ratio < cfg.min_breakout_body_ratio or bar.vol_vs_avg_20 < cfg.min_breakout_vol_vs_avg:
        return False, 0.0, 0.0
    if direction > 0:
        if bar.close <= range_high or bar.close <= bar.open or bar.close_location < 0.58:
            return False, 0.0, 0.0
        extension = (bar.close - range_high) / atr_price
    else:
        if bar.close >= range_low or bar.close >= bar.open or bar.close_location > 0.42:
            return False, 0.0, 0.0
        extension = (range_low - bar.close) / atr_price
    return 0 <= extension <= cfg.max_breakout_extension_atr, extension, body_ratio


def rejection_ratio(bar: Bar, direction: int) -> tuple[float, float]:
    body = abs(bar.close - bar.open)
    rng = max(bar.high - bar.low, 0.00001)
    lower_wick = min(bar.open, bar.close) - bar.low
    upper_wick = bar.high - max(bar.open, bar.close)
    body_ratio = body / rng
    reject = lower_wick / rng if direction > 0 else upper_wick / rng
    return body_ratio, reject


def find_retest(
    bars: list[Bar],
    breakout_idx: int,
    cfg: RetestConfig,
    direction: int,
    level: float,
    atr_price: float,
) -> tuple[int, float, float] | None:
    tol = cfg.retest_tolerance_atr * atr_price
    for offset in range(1, cfg.retest_window + 1):
        idx = breakout_idx + offset
        if idx >= len(bars):
            return None
        bar = bars[idx]
        body_ratio, reject = rejection_ratio(bar, direction)
        if direction > 0:
            touched = bar.low <= level + tol
            reclaimed = bar.close >= level and bar.close > bar.open
            extension = (bar.close - level) / atr_price
        else:
            touched = bar.high >= level - tol
            reclaimed = bar.close <= level and bar.close < bar.open
            extension = (level - bar.close) / atr_price
        if not touched or not reclaimed:
            continue
        if extension < -0.05 or extension > cfg.max_entry_extension_atr:
            continue
        if cfg.require_rejection and reject < 0.20 and body_ratio < 0.35:
            continue
        return idx, extension, reject
    return None


def build_candidate(
    bars: list[Bar],
    breakout_idx: int,
    retest_idx: int,
    cfg: RetestConfig,
    direction: int,
    level: float,
    pip_size: float,
    cost_r: float,
    range_high: float,
    range_low: float,
    width_pips: float,
    width_atr: float,
    avg_range_pips: float,
    cross_count: int,
    breakout_extension: float,
    entry_extension: float,
    breakout_body_ratio: float,
) -> RetestCandidate | None:
    atr_price = avg_range_pips * pip_size
    entry_bar = bars[retest_idx]
    entry = entry_bar.close
    if direction > 0:
        swing_low = min(bar.low for bar in bars[max(0, retest_idx - 3) : retest_idx + 1])
        stop = min(swing_low, level) - cfg.stop_buffer_atr * atr_price
    else:
        swing_high = max(bar.high for bar in bars[max(0, retest_idx - 3) : retest_idx + 1])
        stop = max(swing_high, level) + cfg.stop_buffer_atr * atr_price
    risk = abs(entry - stop)
    risk_pips = risk / pip_size if pip_size > 0 else 0.0
    if risk <= 0 or risk_pips / avg_range_pips > cfg.max_risk_atr:
        return None
    if direction > 0 and stop >= entry:
        return None
    if direction < 0 and stop <= entry:
        return None
    target = entry + direction * cfg.target_rr * risk
    hit_tp, hit_sl, label_r, mfe_r, mae_r, bars_to_mfe, bars_to_mae = label_candidate(
        bars, retest_idx, direction, entry, stop, target, cfg.horizon_bars
    )
    body_ratio, reject = rejection_ratio(entry_bar, direction)
    breakout_bar = bars[breakout_idx]
    return RetestCandidate(
        config_id=cfg.config_id,
        setup="POST_IMPULSE_RETEST",
        breakout_ts=breakout_bar.server_ts.strftime("%Y.%m.%d %H:%M:%S"),
        server_ts=entry_bar.server_ts.strftime("%Y.%m.%d %H:%M:%S"),
        bar_time=entry_bar.bar_time.strftime("%Y.%m.%d %H:%M:%S"),
        direction="LONG" if direction > 0 else "SHORT",
        retest_bars_after_breakout=retest_idx - breakout_idx,
        entry=round(entry, 5),
        stop=round(stop, 5),
        target=round(target, 5),
        target_rr=cfg.target_rr,
        risk_pips=round(risk_pips, 3),
        compression_bars=cfg.lookback,
        width_pips=round(width_pips, 3),
        width_atr=round(width_atr, 4),
        avg_range_pips=round(avg_range_pips, 3),
        cross_count=cross_count,
        breakout_extension_atr=round(breakout_extension, 4),
        entry_extension_atr=round(entry_extension, 4),
        breakout_expansion_ratio=round(breakout_bar.range_pips / avg_range_pips, 4),
        breakout_body_ratio=round(breakout_body_ratio, 4),
        retest_body_ratio=round(body_ratio, 4),
        retest_rejection_ratio=round(reject, 4),
        breakout_vol_vs_avg_20=round(breakout_bar.vol_vs_avg_20, 4),
        session_bucket=session_bucket(entry_bar.server_ts.hour),
        hour=entry_bar.server_ts.hour,
        weekday=entry_bar.server_ts.weekday(),
        half_year=half_year(entry_bar.server_ts),
        year=entry_bar.server_ts.year,
        hit_tp_first=hit_tp,
        hit_sl_first=hit_sl,
        label_r=round(label_r, 6),
        label_r_after_cost=round(label_r - cost_r, 6),
        mfe_r=round(mfe_r, 6),
        mae_r=round(mae_r, 6),
        bars_to_mfe=bars_to_mfe,
        bars_to_mae=bars_to_mae,
    )


def scan(bars: list[Bar], pip_size: float, cost_r: float) -> list[RetestCandidate]:
    all_configs = configs()
    max_lookback = max(cfg.lookback for cfg in all_configs)
    max_atr = max(cfg.atr_lookback for cfg in all_configs)
    max_window = max(cfg.retest_window + cfg.horizon_bars for cfg in all_configs)
    candidates: list[RetestCandidate] = []
    seen: set[tuple[str, int, int]] = set()
    for idx in range(max(max_lookback, max_atr), len(bars) - max_window - 1):
        bar = bars[idx]
        if session_bucket(bar.server_ts.hour) == "OFF" or bar.server_ts.weekday() >= 4:
            continue
        for cfg in all_configs:
            if idx < max(cfg.lookback, cfg.atr_lookback):
                continue
            prior = bars[idx - cfg.lookback : idx]
            atr_window = bars[idx - cfg.atr_lookback : idx]
            avg_range_pips = safe_mean([max(0.01, item.range_pips) for item in atr_window])
            atr_price = avg_range_pips * pip_size
            if avg_range_pips <= 0 or atr_price <= 0:
                continue
            range_high = max(item.high for item in prior)
            range_low = min(item.low for item in prior)
            width_price = range_high - range_low
            if width_price <= 0:
                continue
            width_pips = width_price / pip_size
            width_atr = width_pips / avg_range_pips
            if width_atr > cfg.max_width_atr:
                continue
            mid = (range_high + range_low) * 0.5
            crosses = price_cross_count(bars, idx, cfg.lookback, mid)
            if crosses < cfg.min_crosses:
                continue
            for direction in (1, -1):
                ok, breakout_extension, breakout_body = breakout_ok(
                    bars, idx, cfg, direction, range_high, range_low, avg_range_pips, atr_price
                )
                if not ok:
                    continue
                level = range_high if direction > 0 else range_low
                retest = find_retest(bars, idx, cfg, direction, level, atr_price)
                if retest is None:
                    continue
                retest_idx, entry_extension, _reject = retest
                entry_bar = bars[retest_idx]
                if session_bucket(entry_bar.server_ts.hour) == "OFF" or entry_bar.server_ts.weekday() >= 4:
                    continue
                key = (cfg.config_id, retest_idx, direction)
                if key in seen:
                    continue
                seen.add(key)
                candidate = build_candidate(
                    bars,
                    idx,
                    retest_idx,
                    cfg,
                    direction,
                    level,
                    pip_size,
                    cost_r,
                    range_high,
                    range_low,
                    width_pips,
                    width_atr,
                    avg_range_pips,
                    crosses,
                    breakout_extension,
                    entry_extension,
                    breakout_body,
                )
                if candidate is not None:
                    candidates.append(candidate)
    return candidates


def summarize_group(rows: list[RetestCandidate], min_count: int) -> dict[str, Any]:
    values = [row.label_r for row in rows]
    cost_values = [row.label_r_after_cost for row in rows]
    by_half: dict[str, float] = defaultdict(float)
    by_year: dict[int, float] = defaultdict(float)
    by_hour: dict[int, float] = defaultdict(float)
    by_session: dict[str, float] = defaultdict(float)
    for row in rows:
        by_half[row.half_year] += row.label_r_after_cost
        by_year[row.year] += row.label_r_after_cost
        by_hour[row.hour] += row.label_r_after_cost
        by_session[row.session_bucket] += row.label_r_after_cost
    positive_halves = sum(1 for value in by_half.values() if value > 0)
    positive_years = sum(1 for value in by_year.values() if value > 0)
    pf_cost = profit_factor(cost_values)
    mean_cost = safe_mean(cost_values)
    fails: list[str] = []
    if len(rows) < min_count:
        fails.append("too_few_candidates")
    if pf_cost < 1.25:
        fails.append("pf_after_cost_below_1_25")
    if mean_cost <= 0.03:
        fails.append("mean_r_after_cost_below_0_03")
    if positive_halves < 9:
        fails.append("half_year_stability_below_9")
    if positive_years < 4:
        fails.append("year_stability_below_4")
    return {
        "count": len(rows),
        "sum_r": round(sum(values), 6),
        "sum_r_after_cost": round(sum(cost_values), 6),
        "mean_r_after_cost": round(mean_cost, 6),
        "median_r_after_cost": round(statistics.median(cost_values), 6) if cost_values else 0.0,
        "p25_r_after_cost": round(percentile(cost_values, 0.25), 6),
        "p75_r_after_cost": round(percentile(cost_values, 0.75), 6),
        "pf_r": round(profit_factor(values), 6),
        "pf_r_after_cost": round(pf_cost, 6),
        "win_rate": round(sum(1 for value in values if value > 0) / len(values), 6) if values else 0.0,
        "tp_rate": round(sum(1 for row in rows if row.hit_tp_first) / len(rows), 6) if rows else 0.0,
        "sl_rate": round(sum(1 for row in rows if row.hit_sl_first) / len(rows), 6) if rows else 0.0,
        "positive_half_years": positive_halves,
        "total_half_years": len(by_half),
        "positive_years": positive_years,
        "total_years": len(by_year),
        "best_hour": max(by_hour.items(), key=lambda item: item[1]) if by_hour else None,
        "worst_hour": min(by_hour.items(), key=lambda item: item[1]) if by_hour else None,
        "best_year": max(by_year.items(), key=lambda item: item[1]) if by_year else None,
        "worst_year": min(by_year.items(), key=lambda item: item[1]) if by_year else None,
        "by_session_sum_r_after_cost": {key: round(value, 6) for key, value in sorted(by_session.items())},
        "verdict": "REJECT" if fails else "PASS_RESEARCH_SCREEN",
        "fail_reasons": fails,
    }


def summarize(candidates: list[RetestCandidate], min_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_config: dict[str, list[RetestCandidate]] = defaultdict(list)
    by_direction: dict[str, list[RetestCandidate]] = defaultdict(list)
    for row in candidates:
        by_config[row.config_id].append(row)
        by_direction[row.direction].append(row)
    config_rows = []
    for key, rows in sorted(by_config.items()):
        summary = summarize_group(rows, min_count)
        summary["config_id"] = key
        config_rows.append(summary)
    config_rows.sort(key=lambda row: (row["verdict"] != "PASS_RESEARCH_SCREEN", -row["pf_r_after_cost"], -row["count"]))
    overall = summarize_group(candidates, min_count)
    overall["direction_summary"] = {key: summarize_group(rows, min_count) for key, rows in sorted(by_direction.items())}
    overall["passing_configs"] = [row["config_id"] for row in config_rows if row["verdict"] == "PASS_RESEARCH_SCREEN"]
    overall["verdict"] = "PASS_HAS_RESEARCH_CANDIDATE" if overall["passing_configs"] else "REJECT_NO_PASSER"
    return overall, config_rows


def render_markdown(result: dict[str, Any], config_rows: list[dict[str, Any]]) -> str:
    overall = result["overall"]
    lines = [
        "# Sonic Post-Impulse Retest Probe",
        "",
        f"- Run: `{result['run_id']}`",
        f"- Source bars: `{result['load_meta']['loaded_bars']}`",
        f"- Candidates: `{overall['count']}`",
        f"- Verdict: `{overall['verdict']}`",
        f"- Cost assumption: `{result['cost_r']}` R per candidate",
        "",
        "## Overall",
        "",
        f"- PF after cost: `{overall['pf_r_after_cost']}`",
        f"- Sum R after cost: `{overall['sum_r_after_cost']}`",
        f"- Mean R after cost: `{overall['mean_r_after_cost']}`",
        f"- Positive half-years: `{overall['positive_half_years']}/{overall['total_half_years']}`",
        f"- Positive years: `{overall['positive_years']}/{overall['total_years']}`",
        "",
        "## Top Configs",
        "",
        "| config | n | PF cost | mean R cost | half-years | years | verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in config_rows:
        lines.append(
            "| {config_id} | {count} | {pf_r_after_cost} | {mean_r_after_cost} | {positive_half_years}/{total_half_years} | {positive_years}/{total_years} | {verdict} |".format(
                **row
            )
        )
    lines.extend(["", "## Decision", ""])
    if overall["passing_configs"]:
        lines.append("At least one retest config passed. Pre-register one default-off lane before EA coding.")
    else:
        lines.append("No retest config passed the research screen. Do not code a post-impulse retest lane from this evidence.")
    return "\n".join(lines) + "\n"


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = run_dir_for(args.run, args.ea_name)
    if not run_dir.exists():
        raise SystemExit(f"run not found: {run_dir}")
    pvsra_files = sorted(logs_dir(run_dir).glob("*_PVSRA_SR_Fields_*.csv"))
    if not pvsra_files:
        raise SystemExit(f"missing PVSRA/SR sidecar under {logs_dir(run_dir)}")
    bars, pip_size, load_meta = load_bars(pvsra_files[0])
    candidates = scan(bars, pip_size, args.cost_r)
    overall, config_rows = summarize(candidates, args.min_count)
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    candidate_rows = [asdict(row) for row in candidates[: args.max_candidate_rows]]
    result = {
        "schema_version": "sonic_impulse_retest_probe.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "cost_r": args.cost_r,
        "min_count": args.min_count,
        "candidate_rows_written": len(candidate_rows),
        "candidate_rows_truncated": len(candidates) > len(candidate_rows),
        "load_meta": load_meta,
        "configs": [asdict(cfg) for cfg in configs()],
        "overall": overall,
        "by_config": config_rows,
    }
    json_path = analysis_dir / "sonic_impulse_retest_probe.json"
    md_path = analysis_dir / "sonic_impulse_retest_probe.md"
    cfg_path = analysis_dir / "sonic_impulse_retest_by_config.csv"
    candidates_path = analysis_dir / "sonic_impulse_retest_candidates.csv"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(result, config_rows), encoding="utf-8")
    write_csv(cfg_path, config_rows)
    write_csv(candidates_path, candidate_rows)
    result["outputs"] = {
        "json": str(json_path),
        "markdown": str(md_path),
        "by_config_csv": str(cfg_path),
        "candidates_csv": str(candidates_path),
    }
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("run", help="AlphaFactory run id or run directory")
    cli.add_argument("--ea-name", default=DEFAULT_EA)
    cli.add_argument("--cost-r", type=float, default=0.05)
    cli.add_argument("--min-count", type=int, default=240)
    cli.add_argument("--max-candidate-rows", type=int, default=25000)
    return cli


def main() -> int:
    args = parser().parse_args()
    result = run_probe(args)
    overall = result["overall"]
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "verdict": overall["verdict"],
                "candidates": overall["count"],
                "pf_r_after_cost": overall["pf_r_after_cost"],
                "sum_r_after_cost": overall["sum_r_after_cost"],
                "positive_half_years": f"{overall['positive_half_years']}/{overall['total_half_years']}",
                "passing_configs": overall["passing_configs"],
                "markdown": result["outputs"]["markdown"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
