#!/usr/bin/env python3
"""Offline XAU sideway/range-rotation probe for EA_SonicR telemetry.

This is an analysis tool, not an EA mutator. It reads the PVSRA/SR sidecar
emitted by telemetry runs and tests whether outer-quartile range rejections
would have had enough forward MFE/MAE to justify coding an executable lane.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def half_key(ts: datetime) -> str:
    return f"{ts.year}H{1 if ts.month <= 6 else 2}"


@dataclass
class Bar:
    server_ts: datetime
    bar_time: datetime
    open: float
    high: float
    low: float
    close: float
    range_pips: float
    body_pips: float
    upper_wick_pips: float
    lower_wick_pips: float
    vol_vs_avg_20: float
    seq_5_high_volume_count: int
    pva_rising: bool
    pva_climax: bool
    pva_highest: bool
    level_zone: str


@dataclass
class Candidate:
    bar_time: str
    server_ts: str
    direction: str
    setup: str
    entry: float
    stop: float
    target: float
    target_rr: float
    range_width_atr: float
    cross_count: int
    pvsra_strength: float
    hour: int
    weekday: str
    half: str
    hit_tp_first: bool
    hit_sl_first: bool
    label_r: float
    mfe_r: float
    mae_r: float
    bars_to_mfe: int
    bars_to_mae: int


def load_bars(path: Path) -> list[Bar]:
    rows: list[Bar] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("data_status") not in ("", "OK"):
                continue
            try:
                server_ts = parse_time(r["server_ts"])
                bar_time = parse_time(r["bar_time"])
            except (KeyError, ValueError):
                continue
            rows.append(
                Bar(
                    server_ts=server_ts,
                    bar_time=bar_time,
                    open=safe_float(r.get("bar_open")),
                    high=safe_float(r.get("bar_high")),
                    low=safe_float(r.get("bar_low")),
                    close=safe_float(r.get("bar_close")),
                    range_pips=safe_float(r.get("bar_range_pips")),
                    body_pips=safe_float(r.get("bar_body_pips")),
                    upper_wick_pips=safe_float(r.get("upper_wick_pips")),
                    lower_wick_pips=safe_float(r.get("lower_wick_pips")),
                    vol_vs_avg_20=safe_float(r.get("vol_vs_avg_20")),
                    seq_5_high_volume_count=int(safe_float(r.get("seq_5_high_volume_count"), 0)),
                    pva_rising=parse_bool(r.get("candidate_pva_rising_150", "")),
                    pva_climax=parse_bool(r.get("candidate_pva_climax_200", "")),
                    pva_highest=parse_bool(r.get("candidate_pva_highest_20", "")),
                    level_zone=r.get("level_zone") or "NONE",
                )
            )
    rows.sort(key=lambda b: b.server_ts)
    return rows


def price_cross_count(bars: list[Bar], start: int, lookback: int, midpoint: float) -> int:
    crosses = 0
    prev = 0
    for idx in range(start - lookback, start):
        sign = 1 if bars[idx].close > midpoint else (-1 if bars[idx].close < midpoint else 0)
        if sign and prev and sign != prev:
            crosses += 1
        if sign:
            prev = sign
    return crosses


def pvsra_strength(bar: Bar) -> float:
    strength = 0.0
    if bar.pva_climax:
        strength += 2.0
    if bar.pva_rising:
        strength += 1.5
    if bar.pva_highest:
        strength += 1.0
    if bar.vol_vs_avg_20 >= 2.0:
        strength += 1.0
    elif bar.vol_vs_avg_20 >= 1.5:
        strength += 0.5
    if bar.seq_5_high_volume_count > 0:
        strength += 0.5
    return strength


def label_candidate(
    bars: list[Bar],
    idx: int,
    direction: int,
    entry: float,
    stop: float,
    target: float,
    horizon: int,
) -> tuple[bool, bool, float, float, float, int, int]:
    risk = abs(entry - stop)
    if risk <= 0:
        return False, False, 0.0, 0.0, 0.0, 0, 0
    max_fav = 0.0
    max_adv = 0.0
    bars_to_mfe = 0
    bars_to_mae = 0
    hit_tp = False
    hit_sl = False
    label_r = 0.0
    last_close = entry
    for offset in range(1, min(horizon, len(bars) - idx - 1) + 1):
        bar = bars[idx + offset]
        last_close = bar.close
        if direction > 0:
            fav = (bar.high - entry) / risk
            adv = (entry - bar.low) / risk
            target_hit = bar.high >= target
            stop_hit = bar.low <= stop
        else:
            fav = (entry - bar.low) / risk
            adv = (bar.high - entry) / risk
            target_hit = bar.low <= target
            stop_hit = bar.high >= stop
        if fav > max_fav:
            max_fav = fav
            bars_to_mfe = offset
        if adv > max_adv:
            max_adv = adv
            bars_to_mae = offset
        if target_hit and stop_hit:
            hit_sl = True
            label_r = -1.0
            break
        if target_hit:
            hit_tp = True
            label_r = abs(target - entry) / risk
            break
        if stop_hit:
            hit_sl = True
            label_r = -1.0
            break
    if not hit_tp and not hit_sl:
        final_r = ((last_close - entry) / risk) if direction > 0 else ((entry - last_close) / risk)
        label_r = max(-1.0, min(abs(target - entry) / risk, final_r))
    return hit_tp, hit_sl, label_r, max_fav, max_adv, bars_to_mfe, bars_to_mae


def weekday_name(ts: datetime) -> str:
    return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][ts.weekday()]


def probe(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run)
    logs = run / "analysis" / "logs"
    if not logs.exists():
        logs = run / "logs"
    files = sorted(logs.glob("*_PVSRA_SR_Fields_*.csv"))
    if not files:
        raise SystemExit(f"missing PVSRA/SR sidecar under {logs}")
    bars = load_bars(files[0])
    candidates: list[Candidate] = []
    lookback = args.lookback
    atr_lookback = args.atr_lookback
    for idx in range(max(lookback, atr_lookback), len(bars) - args.horizon_bars - 1):
        bar = bars[idx]
        hour = bar.server_ts.hour
        if hour < args.session_start_hour or hour > args.session_end_hour:
            continue
        if bar.server_ts.weekday() >= 4:
            continue
        prior = bars[idx - lookback : idx]
        atr_window = bars[idx - atr_lookback : idx]
        atr = statistics.mean(max(0.01, b.range_pips) for b in atr_window)
        range_high = max(b.high for b in prior)
        range_low = min(b.low for b in prior)
        width = range_high - range_low
        if atr <= 0 or width <= 0:
            continue
        width_atr = width / atr
        if width_atr < args.min_width_atr or width_atr > args.max_width_atr:
            continue
        mid = (range_high + range_low) * 0.5
        crosses = price_cross_count(bars, idx, lookback, mid)
        if crosses < args.min_crosses:
            continue
        strength = pvsra_strength(bar)
        if strength < args.min_pvsra_strength:
            continue
        lower_q = range_low + 0.25 * width
        upper_q = range_high - 0.25 * width
        body = abs(bar.close - bar.open)
        lower_wick = min(bar.open, bar.close) - bar.low
        upper_wick = bar.high - max(bar.open, bar.close)
        setups: list[tuple[str, int, float, float, float]] = []
        if (
            bar.low <= lower_q
            and bar.close > lower_q
            and bar.close <= mid
            and bar.close > bar.open
            and lower_wick >= max(args.wick_atr * atr, args.wick_body * body)
        ):
            entry = bar.close
            stop = bar.low - args.stop_atr * atr
            target = mid
            risk = entry - stop
            rr = (target - entry) / risk if risk > 0 else 0.0
            if rr >= args.min_rr:
                setups.append(("inner_long", 1, entry, stop, target))
        if (
            bar.high >= upper_q
            and bar.close < upper_q
            and bar.close >= mid
            and bar.close < bar.open
            and upper_wick >= max(args.wick_atr * atr, args.wick_body * body)
        ):
            entry = bar.close
            stop = bar.high + args.stop_atr * atr
            target = mid
            risk = stop - entry
            rr = (entry - target) / risk if risk > 0 else 0.0
            if rr >= args.min_rr:
                setups.append(("inner_short", -1, entry, stop, target))
        for setup, direction, entry, stop, target in setups:
            hit_tp, hit_sl, label_r, mfe_r, mae_r, bars_to_mfe, bars_to_mae = label_candidate(
                bars, idx, direction, entry, stop, target, args.horizon_bars
            )
            candidates.append(
                Candidate(
                    bar_time=bar.bar_time.strftime("%Y.%m.%d %H:%M:%S"),
                    server_ts=bar.server_ts.strftime("%Y.%m.%d %H:%M:%S"),
                    direction="LONG" if direction > 0 else "SHORT",
                    setup=setup,
                    entry=round(entry, 3),
                    stop=round(stop, 3),
                    target=round(target, 3),
                    target_rr=round(abs(target - entry) / abs(entry - stop), 4),
                    range_width_atr=round(width_atr, 4),
                    cross_count=crosses,
                    pvsra_strength=round(strength, 3),
                    hour=hour,
                    weekday=weekday_name(bar.server_ts),
                    half=half_key(bar.server_ts),
                    hit_tp_first=hit_tp,
                    hit_sl_first=hit_sl,
                    label_r=round(label_r, 4),
                    mfe_r=round(mfe_r, 4),
                    mae_r=round(mae_r, 4),
                    bars_to_mfe=bars_to_mfe,
                    bars_to_mae=bars_to_mae,
                )
            )
    return summarize(run, files[0], bars, candidates, args)


def bucket_summary(candidates: list[Candidate], attr: str) -> list[dict[str, Any]]:
    out = []
    groups: dict[str, list[Candidate]] = defaultdict(list)
    for c in candidates:
        groups[str(getattr(c, attr))].append(c)
    for key, rows in sorted(groups.items()):
        out.append(summarize_rows(key, rows))
    return out


def summarize_rows(key: str, rows: list[Candidate]) -> dict[str, Any]:
    total = len(rows)
    label_sum = sum(c.label_r for c in rows)
    tp = sum(1 for c in rows if c.hit_tp_first)
    sl = sum(1 for c in rows if c.hit_sl_first)
    return {
        "bucket": key,
        "n": total,
        "label_r_sum": round(label_sum, 4),
        "label_r_mean": round(label_sum / total, 4) if total else 0.0,
        "tp_first_rate": round(tp / total, 4) if total else 0.0,
        "sl_first_rate": round(sl / total, 4) if total else 0.0,
        "avg_target_rr": round(statistics.mean(c.target_rr for c in rows), 4) if rows else 0.0,
        "avg_mfe_r": round(statistics.mean(c.mfe_r for c in rows), 4) if rows else 0.0,
        "avg_mae_r": round(statistics.mean(c.mae_r for c in rows), 4) if rows else 0.0,
    }


def summarize(run: Path, source: Path, bars: list[Bar], candidates: list[Candidate], args: argparse.Namespace) -> dict[str, Any]:
    summary = {
        "schema_version": "sonic_sideway_range_probe.v1",
        "run_id": run.name,
        "source": str(source),
        "bars": len(bars),
        "parameters": vars(args),
        "candidate_count": len(candidates),
        "overall": summarize_rows("all", candidates) if candidates else {},
        "by_setup": bucket_summary(candidates, "setup"),
        "by_direction": bucket_summary(candidates, "direction"),
        "by_half": bucket_summary(candidates, "half"),
        "by_weekday": bucket_summary(candidates, "weekday"),
        "by_hour": bucket_summary(candidates, "hour"),
        "top_positive": [asdict(c) for c in sorted(candidates, key=lambda c: c.label_r, reverse=True)[:20]],
        "top_negative": [asdict(c) for c in sorted(candidates, key=lambda c: c.label_r)[:20]],
    }
    return summary


def write_outputs(summary: dict[str, Any], out_base: Path) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    out_base.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    candidates = [*summary.get("top_positive", []), *summary.get("top_negative", [])]
    if candidates:
        with out_base.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(candidates[0].keys()))
            writer.writeheader()
            writer.writerows(candidates)
    lines = [
        "# Sonic Sideway Range Probe",
        "",
        f"Run: `{summary['run_id']}`",
        f"Bars: `{summary['bars']}`",
        f"Candidates: `{summary['candidate_count']}`",
        "",
        "## Overall",
        "",
        "```json",
        json.dumps(summary.get("overall", {}), indent=2),
        "```",
        "",
        "## By Half",
        "",
    ]
    for row in summary.get("by_half", []):
        lines.append(f"- `{row['bucket']}`: n={row['n']}, labelR={row['label_r_sum']}, meanR={row['label_r_mean']}, TP={row['tp_first_rate']}, SL={row['sl_first_rate']}")
    lines.extend(["", "## By Setup", ""])
    for row in summary.get("by_setup", []):
        lines.append(f"- `{row['bucket']}`: n={row['n']}, labelR={row['label_r_sum']}, meanR={row['label_r_mean']}, TP={row['tp_first_rate']}, SL={row['sl_first_rate']}")
    out_base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", help="AlphaFactory run directory or path")
    parser.add_argument("--lookback", type=int, default=36)
    parser.add_argument("--atr-lookback", type=int, default=20)
    parser.add_argument("--horizon-bars", type=int, default=12)
    parser.add_argument("--min-width-atr", type=float, default=0.8)
    parser.add_argument("--max-width-atr", type=float, default=3.6)
    parser.add_argument("--min-crosses", type=int, default=3)
    parser.add_argument("--min-pvsra-strength", type=float, default=1.0)
    parser.add_argument("--min-rr", type=float, default=0.8)
    parser.add_argument("--wick-atr", type=float, default=0.08)
    parser.add_argument("--wick-body", type=float, default=0.6)
    parser.add_argument("--stop-atr", type=float, default=0.25)
    parser.add_argument("--session-start-hour", type=int, default=8)
    parser.add_argument("--session-end-hour", type=int, default=17)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    run = Path(args.run)
    if not run.exists():
        run = Path("02. AlphaFactory") / "runs" / "EA_SonicR" / args.run
    summary = probe(argparse.Namespace(**{**vars(args), "run": str(run)}))
    out = Path(args.out) if args.out else run / "analysis" / "sonic_sideway_range_probe"
    write_outputs(summary, out)
    print(json.dumps({k: summary[k] for k in ("run_id", "candidate_count", "overall", "by_half", "by_setup")}, indent=2))


if __name__ == "__main__":
    main()
