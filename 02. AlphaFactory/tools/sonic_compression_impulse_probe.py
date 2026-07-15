#!/usr/bin/env python3
"""Offline compression-to-impulse probe for Sonic R XAU M5 research.

This is intentionally analysis-only. It reads closed-bar PVSRA/SR sidecars,
generates a small pre-defined family of compression breakout / post-sweep
launch candidates, labels their forward MFE/MAE in R, and reports whether any
configuration deserves an EA implementation pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
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


def parse_ts(value: str | None) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def logs_dir(run_dir: Path) -> Path:
    for candidate in (run_dir / "analysis" / "logs", run_dir / "logs"):
        if candidate.exists():
            return candidate
    return run_dir / "analysis" / "logs"


def half_year(ts: datetime) -> str:
    return f"{ts.year}H{1 if ts.month <= 6 else 2}"


def profit_factor(values: Iterable[float]) -> float:
    vals = list(values)
    gross_win = sum(value for value in vals if value > 0)
    gross_loss = -sum(value for value in vals if value < 0)
    if gross_loss <= 0:
        return 999.99 if gross_win > 0 else 0.0
    return gross_win / gross_loss


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


@dataclass(slots=True)
class Bar:
    server_ts: datetime
    bar_time: datetime
    open: float
    high: float
    low: float
    close: float
    range_pips: float
    body_pips: float
    close_location: float
    vol_vs_avg_20: float
    seq_5_high_volume_count: int
    seq_5_net_range_atr: float
    seq_5_close_delta_pips: float
    pva_rising: bool
    pva_climax: bool
    pva_highest: bool
    level_zone: str


@dataclass(frozen=True, slots=True)
class ProbeConfig:
    config_id: str
    setup: str
    lookback: int
    atr_lookback: int
    max_width_atr: float
    min_crosses: int
    expansion_mult: float
    min_body_ratio: float
    min_vol_vs_avg: float
    max_breakout_extension_atr: float
    require_sweep: bool
    sweep_lookback: int
    stop_mode: str
    stop_buffer_atr: float
    max_risk_atr: float
    target_rr: float
    horizon_bars: int


@dataclass
class Candidate:
    config_id: str
    setup: str
    server_ts: str
    bar_time: str
    direction: str
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
    expansion_ratio: float
    body_ratio: float
    vol_vs_avg_20: float
    pvsra_strength: float
    breakout_extension_atr: float
    sweep_recent: bool
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


def strict_configs() -> list[ProbeConfig]:
    return [
        ProbeConfig(
            "CI_36_MICRO_R12",
            "COMPRESSION_IMPULSE",
            36,
            20,
            4.5,
            4,
            1.25,
            0.48,
            1.10,
            0.75,
            False,
            8,
            "micro_swing",
            0.20,
            1.80,
            1.20,
            12,
        ),
        ProbeConfig(
            "CI_48_MICRO_R12",
            "COMPRESSION_IMPULSE",
            48,
            20,
            5.5,
            5,
            1.20,
            0.45,
            1.00,
            0.70,
            False,
            10,
            "micro_swing",
            0.20,
            2.00,
            1.20,
            12,
        ),
        ProbeConfig(
            "CI_72_RANGE_R15",
            "COMPRESSION_IMPULSE",
            72,
            20,
            6.5,
            6,
            1.35,
            0.50,
            1.20,
            0.85,
            False,
            12,
            "range_edge",
            0.12,
            3.20,
            1.50,
            18,
        ),
        ProbeConfig(
            "CI_EXPLOSIVE_36_R15",
            "COMPRESSION_IMPULSE",
            36,
            20,
            5.5,
            3,
            1.65,
            0.55,
            1.50,
            0.95,
            False,
            8,
            "micro_swing",
            0.25,
            2.20,
            1.50,
            12,
        ),
        ProbeConfig(
            "PSL_36_MICRO_R12",
            "POST_SWEEP_LAUNCH",
            36,
            20,
            6.0,
            3,
            1.15,
            0.45,
            1.00,
            0.80,
            True,
            10,
            "micro_swing",
            0.20,
            2.20,
            1.20,
            14,
        ),
        ProbeConfig(
            "PSL_48_RANGE_R12",
            "POST_SWEEP_LAUNCH",
            48,
            20,
            7.0,
            4,
            1.10,
            0.42,
            1.00,
            0.90,
            True,
            14,
            "range_edge",
            0.10,
            3.50,
            1.20,
            18,
        ),
        ProbeConfig(
            "PSL_EXPLOSIVE_36_R10",
            "POST_SWEEP_LAUNCH",
            36,
            20,
            7.0,
            3,
            1.45,
            0.52,
            1.35,
            0.90,
            True,
            12,
            "micro_swing",
            0.25,
            2.40,
            1.00,
            10,
        ),
        ProbeConfig(
            "CI_24_FAST_R10",
            "COMPRESSION_IMPULSE",
            24,
            20,
            4.0,
            3,
            1.30,
            0.50,
            1.20,
            0.70,
            False,
            6,
            "micro_swing",
            0.20,
            1.60,
            1.00,
            8,
        ),
    ]


def exploratory_configs() -> list[ProbeConfig]:
    return [
        ProbeConfig(
            "CI_24_LOOSE_R08",
            "COMPRESSION_IMPULSE_LOOSE",
            24,
            20,
            6.0,
            2,
            1.05,
            0.35,
            0.80,
            1.20,
            False,
            6,
            "micro_swing",
            0.18,
            2.20,
            0.80,
            8,
        ),
        ProbeConfig(
            "CI_36_LOOSE_R10",
            "COMPRESSION_IMPULSE_LOOSE",
            36,
            20,
            7.0,
            2,
            1.00,
            0.35,
            0.80,
            1.25,
            False,
            8,
            "micro_swing",
            0.18,
            2.40,
            1.00,
            10,
        ),
        ProbeConfig(
            "CI_48_LOOSE_R10",
            "COMPRESSION_IMPULSE_LOOSE",
            48,
            20,
            8.0,
            2,
            1.00,
            0.33,
            0.75,
            1.35,
            False,
            10,
            "micro_swing",
            0.18,
            2.80,
            1.00,
            12,
        ),
        ProbeConfig(
            "CI_12_FAST_R08",
            "FAST_BOX_IMPULSE",
            12,
            20,
            4.5,
            1,
            1.15,
            0.38,
            0.85,
            1.10,
            False,
            4,
            "micro_swing",
            0.18,
            1.80,
            0.80,
            6,
        ),
        ProbeConfig(
            "PSL_24_LOOSE_R08",
            "POST_SWEEP_LAUNCH_LOOSE",
            24,
            20,
            7.0,
            1,
            1.00,
            0.34,
            0.75,
            1.20,
            True,
            8,
            "micro_swing",
            0.18,
            2.40,
            0.80,
            8,
        ),
        ProbeConfig(
            "PSL_36_LOOSE_R10",
            "POST_SWEEP_LAUNCH_LOOSE",
            36,
            20,
            8.0,
            2,
            1.00,
            0.34,
            0.75,
            1.35,
            True,
            12,
            "micro_swing",
            0.18,
            2.80,
            1.00,
            10,
        ),
        ProbeConfig(
            "PSL_48_RANGE_LOOSE_R08",
            "POST_SWEEP_LAUNCH_LOOSE",
            48,
            20,
            9.0,
            2,
            0.95,
            0.32,
            0.70,
            1.45,
            True,
            14,
            "range_edge",
            0.08,
            4.00,
            0.80,
            12,
        ),
        ProbeConfig(
            "CI_72_LOOSE_R12",
            "COMPRESSION_IMPULSE_LOOSE",
            72,
            20,
            10.0,
            3,
            0.95,
            0.32,
            0.70,
            1.50,
            False,
            16,
            "micro_swing",
            0.18,
            3.00,
            1.20,
            16,
        ),
    ]


def micro_scalp_configs() -> list[ProbeConfig]:
    return [
        ProbeConfig(
            "MICRO_BOX12_R04",
            "MICRO_IMPULSE_SCALP",
            12,
            20,
            4.5,
            1,
            0.95,
            0.32,
            0.70,
            1.15,
            False,
            4,
            "micro_swing",
            0.16,
            1.80,
            0.40,
            4,
        ),
        ProbeConfig(
            "MICRO_BOX12_R06",
            "MICRO_IMPULSE_SCALP",
            12,
            20,
            4.5,
            1,
            0.95,
            0.32,
            0.70,
            1.15,
            False,
            4,
            "micro_swing",
            0.16,
            1.80,
            0.60,
            5,
        ),
        ProbeConfig(
            "MICRO_BOX24_R04",
            "MICRO_IMPULSE_SCALP",
            24,
            20,
            6.0,
            1,
            0.95,
            0.32,
            0.70,
            1.20,
            False,
            6,
            "micro_swing",
            0.16,
            2.20,
            0.40,
            4,
        ),
        ProbeConfig(
            "MICRO_BOX24_R06",
            "MICRO_IMPULSE_SCALP",
            24,
            20,
            6.0,
            1,
            0.95,
            0.32,
            0.70,
            1.20,
            False,
            6,
            "micro_swing",
            0.16,
            2.20,
            0.60,
            6,
        ),
        ProbeConfig(
            "MICRO_SWEEP12_R04",
            "MICRO_SWEEP_SCALP",
            12,
            20,
            5.5,
            1,
            0.90,
            0.30,
            0.65,
            1.20,
            True,
            5,
            "micro_swing",
            0.16,
            2.00,
            0.40,
            4,
        ),
        ProbeConfig(
            "MICRO_SWEEP24_R06",
            "MICRO_SWEEP_SCALP",
            24,
            20,
            7.0,
            1,
            0.90,
            0.30,
            0.65,
            1.30,
            True,
            8,
            "micro_swing",
            0.16,
            2.40,
            0.60,
            6,
        ),
    ]


def build_configs(profile: str) -> list[ProbeConfig]:
    if profile == "strict":
        return strict_configs()
    if profile == "exploratory":
        return exploratory_configs()
    if profile == "micro":
        return micro_scalp_configs()
    return strict_configs() + exploratory_configs() + micro_scalp_configs()


def load_bars(path: Path) -> tuple[list[Bar], float, dict[str, Any]]:
    bars: list[Bar] = []
    pip_sizes: list[float] = []
    skipped = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("data_status") not in ("", "OK"):
                skipped["bad_status"] += 1
                continue
            server_ts = parse_ts(row.get("server_ts"))
            bar_time = parse_ts(row.get("bar_time"))
            if server_ts is None or bar_time is None:
                skipped["bad_time"] += 1
                continue
            high = safe_float(row.get("bar_high"))
            low = safe_float(row.get("bar_low"))
            range_pips = safe_float(row.get("bar_range_pips"))
            if high <= 0 or low <= 0 or high < low:
                skipped["bad_ohlc"] += 1
                continue
            if range_pips > 0 and high > low:
                pip_sizes.append((high - low) / range_pips)
            bars.append(
                Bar(
                    server_ts=server_ts,
                    bar_time=bar_time,
                    open=safe_float(row.get("bar_open")),
                    high=high,
                    low=low,
                    close=safe_float(row.get("bar_close")),
                    range_pips=range_pips,
                    body_pips=safe_float(row.get("bar_body_pips")),
                    close_location=safe_float(row.get("close_location_0_1"), 0.5),
                    vol_vs_avg_20=safe_float(row.get("vol_vs_avg_20")),
                    seq_5_high_volume_count=int(safe_float(row.get("seq_5_high_volume_count"), 0)),
                    seq_5_net_range_atr=safe_float(row.get("seq_5_net_range_atr")),
                    seq_5_close_delta_pips=safe_float(row.get("seq_5_close_delta_pips")),
                    pva_rising=safe_bool(row.get("candidate_pva_rising_150")),
                    pva_climax=safe_bool(row.get("candidate_pva_climax_200")),
                    pva_highest=safe_bool(row.get("candidate_pva_highest_20")),
                    level_zone=(row.get("level_zone") or "NONE").strip() or "NONE",
                )
            )
    bars.sort(key=lambda item: item.server_ts)
    pip_size = statistics.median(pip_sizes) if pip_sizes else 0.01
    meta = {
        "source": str(path),
        "loaded_bars": len(bars),
        "skipped": dict(skipped),
        "pip_size": pip_size,
    }
    return bars, pip_size, meta


def pvsra_strength(bar: Bar) -> float:
    strength = 0.0
    if bar.pva_climax:
        strength += 2.0
    if bar.pva_rising:
        strength += 1.25
    if bar.pva_highest:
        strength += 1.0
    if bar.vol_vs_avg_20 >= 2.0:
        strength += 1.0
    elif bar.vol_vs_avg_20 >= 1.5:
        strength += 0.5
    if bar.seq_5_high_volume_count > 0:
        strength += 0.5
    return strength


def session_bucket(hour: int) -> str:
    if 7 <= hour <= 10:
        return "LONDON_EARLY"
    if 11 <= hour <= 14:
        return "LONDON_MID"
    if 15 <= hour <= 18:
        return "NY_OVERLAP"
    if 19 <= hour <= 22:
        return "NY_LATE"
    return "OFF"


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


def recent_sweep(
    bars: list[Bar],
    idx: int,
    cfg: ProbeConfig,
    direction: int,
    range_high: float,
    range_low: float,
    atr_price: float,
) -> bool:
    start = max(0, idx - cfg.sweep_lookback)
    window = bars[start : idx + 1]
    tol = 0.05 * atr_price
    if direction > 0:
        return min(bar.low for bar in window) <= range_low + tol
    return max(bar.high for bar in window) >= range_high - tol


def stop_price(
    bars: list[Bar],
    idx: int,
    cfg: ProbeConfig,
    direction: int,
    range_high: float,
    range_low: float,
    atr_price: float,
) -> float:
    if cfg.stop_mode == "range_edge":
        return range_low - cfg.stop_buffer_atr * atr_price if direction > 0 else range_high + cfg.stop_buffer_atr * atr_price
    start = max(0, idx - 5)
    window = bars[start : idx + 1]
    if direction > 0:
        return min(bar.low for bar in window) - cfg.stop_buffer_atr * atr_price
    return max(bar.high for bar in window) + cfg.stop_buffer_atr * atr_price


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


def maybe_candidate(
    bars: list[Bar],
    idx: int,
    cfg: ProbeConfig,
    direction: int,
    pip_size: float,
    cost_r: float,
) -> Candidate | None:
    bar = bars[idx]
    hour = bar.server_ts.hour
    bucket = session_bucket(hour)
    if bucket == "OFF":
        return None
    if bar.server_ts.weekday() >= 4:
        return None

    prior = bars[idx - cfg.lookback : idx]
    atr_window = bars[idx - cfg.atr_lookback : idx]
    avg_range_pips = statistics.mean(max(0.01, item.range_pips) for item in atr_window)
    atr_price = avg_range_pips * pip_size
    if avg_range_pips <= 0 or atr_price <= 0:
        return None

    range_high = max(item.high for item in prior)
    range_low = min(item.low for item in prior)
    width_price = range_high - range_low
    if width_price <= 0:
        return None
    width_pips = width_price / pip_size
    width_atr = width_pips / avg_range_pips
    if width_atr > cfg.max_width_atr:
        return None

    midpoint = (range_high + range_low) * 0.5
    crosses = price_cross_count(bars, idx, cfg.lookback, midpoint)
    if crosses < cfg.min_crosses:
        return None

    body_price = abs(bar.close - bar.open)
    range_price = max(bar.high - bar.low, pip_size)
    body_ratio = body_price / range_price
    if body_ratio < cfg.min_body_ratio:
        return None
    expansion_ratio = bar.range_pips / avg_range_pips if avg_range_pips > 0 else 0.0
    if expansion_ratio < cfg.expansion_mult:
        return None
    if bar.vol_vs_avg_20 < cfg.min_vol_vs_avg:
        return None

    if direction > 0:
        if bar.close <= range_high or bar.close <= bar.open or bar.close_location < 0.62:
            return None
        breakout_extension_atr = (bar.close - range_high) / atr_price
    else:
        if bar.close >= range_low or bar.close >= bar.open or bar.close_location > 0.38:
            return None
        breakout_extension_atr = (range_low - bar.close) / atr_price
    if breakout_extension_atr < 0 or breakout_extension_atr > cfg.max_breakout_extension_atr:
        return None

    swept = recent_sweep(bars, idx, cfg, direction, range_high, range_low, atr_price)
    if cfg.require_sweep and not swept:
        return None

    entry = bar.close
    stop = stop_price(bars, idx, cfg, direction, range_high, range_low, atr_price)
    risk = abs(entry - stop)
    risk_pips = risk / pip_size if pip_size > 0 else 0.0
    if risk <= 0 or risk_pips <= 0:
        return None
    if risk_pips / avg_range_pips > cfg.max_risk_atr:
        return None
    if direction > 0 and stop >= entry:
        return None
    if direction < 0 and stop <= entry:
        return None
    target = entry + direction * cfg.target_rr * risk
    hit_tp, hit_sl, label_r, mfe_r, mae_r, bars_to_mfe, bars_to_mae = label_candidate(
        bars, idx, direction, entry, stop, target, cfg.horizon_bars
    )
    return Candidate(
        config_id=cfg.config_id,
        setup=cfg.setup,
        server_ts=bar.server_ts.strftime("%Y.%m.%d %H:%M:%S"),
        bar_time=bar.bar_time.strftime("%Y.%m.%d %H:%M:%S"),
        direction="LONG" if direction > 0 else "SHORT",
        entry=round(entry, 5),
        stop=round(stop, 5),
        target=round(target, 5),
        target_rr=cfg.target_rr,
        risk_pips=round(risk_pips, 3),
        compression_bars=cfg.lookback,
        width_pips=round(width_pips, 3),
        width_atr=round(width_atr, 4),
        avg_range_pips=round(avg_range_pips, 3),
        cross_count=crosses,
        expansion_ratio=round(expansion_ratio, 4),
        body_ratio=round(body_ratio, 4),
        vol_vs_avg_20=round(bar.vol_vs_avg_20, 4),
        pvsra_strength=round(pvsra_strength(bar), 4),
        breakout_extension_atr=round(breakout_extension_atr, 4),
        sweep_recent=swept,
        session_bucket=bucket,
        hour=hour,
        weekday=bar.server_ts.weekday(),
        half_year=half_year(bar.server_ts),
        year=bar.server_ts.year,
        hit_tp_first=hit_tp,
        hit_sl_first=hit_sl,
        label_r=round(label_r, 6),
        label_r_after_cost=round(label_r - cost_r, 6),
        mfe_r=round(mfe_r, 6),
        mae_r=round(mae_r, 6),
        bars_to_mfe=bars_to_mfe,
        bars_to_mae=bars_to_mae,
    )


def scan_candidates(bars: list[Bar], pip_size: float, cost_r: float, configs: list[ProbeConfig]) -> list[Candidate]:
    max_lookback = max(cfg.lookback for cfg in configs)
    max_atr = max(cfg.atr_lookback for cfg in configs)
    max_horizon = max(cfg.horizon_bars for cfg in configs)
    candidates: list[Candidate] = []
    for idx in range(max(max_lookback, max_atr), len(bars) - max_horizon - 1):
        for cfg in configs:
            if idx < max(cfg.lookback, cfg.atr_lookback):
                continue
            for direction in (1, -1):
                candidate = maybe_candidate(bars, idx, cfg, direction, pip_size, cost_r)
                if candidate is not None:
                    candidates.append(candidate)
    return candidates


def summarize_group(rows: list[Candidate], min_count: int) -> dict[str, Any]:
    values = [row.label_r for row in rows]
    values_cost = [row.label_r_after_cost for row in rows]
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
    pf_cost = profit_factor(values_cost)
    mean_cost = statistics.mean(values_cost) if values_cost else 0.0
    verdict = "PASS_RESEARCH_SCREEN"
    fail_reasons: list[str] = []
    if len(rows) < min_count:
        fail_reasons.append("too_few_candidates")
    if pf_cost < 1.25:
        fail_reasons.append("pf_after_cost_below_1_25")
    if mean_cost <= 0.03:
        fail_reasons.append("mean_r_after_cost_below_0_03")
    if positive_halves < 9:
        fail_reasons.append("half_year_stability_below_9")
    if positive_years < 4:
        fail_reasons.append("year_stability_below_4")
    if fail_reasons:
        verdict = "REJECT"
    return {
        "count": len(rows),
        "sum_r": round(sum(values), 6),
        "sum_r_after_cost": round(sum(values_cost), 6),
        "mean_r": round(statistics.mean(values), 6) if values else 0.0,
        "mean_r_after_cost": round(mean_cost, 6),
        "median_r_after_cost": round(statistics.median(values_cost), 6) if values_cost else 0.0,
        "p25_r_after_cost": round(percentile(values_cost, 0.25), 6),
        "p75_r_after_cost": round(percentile(values_cost, 0.75), 6),
        "pf_r": round(profit_factor(values), 6),
        "pf_r_after_cost": round(pf_cost, 6),
        "win_rate": round(sum(1 for value in values if value > 0) / len(values), 6) if values else 0.0,
        "tp_rate": round(sum(1 for row in rows if row.hit_tp_first) / len(rows), 6) if rows else 0.0,
        "sl_rate": round(sum(1 for row in rows if row.hit_sl_first) / len(rows), 6) if rows else 0.0,
        "positive_half_years": positive_halves,
        "total_half_years": len(by_half),
        "positive_years": positive_years,
        "total_years": len(by_year),
        "best_half_year": max(by_half.items(), key=lambda item: item[1]) if by_half else None,
        "worst_half_year": min(by_half.items(), key=lambda item: item[1]) if by_half else None,
        "best_year": max(by_year.items(), key=lambda item: item[1]) if by_year else None,
        "worst_year": min(by_year.items(), key=lambda item: item[1]) if by_year else None,
        "best_hour": max(by_hour.items(), key=lambda item: item[1]) if by_hour else None,
        "worst_hour": min(by_hour.items(), key=lambda item: item[1]) if by_hour else None,
        "by_session_sum_r_after_cost": {key: round(value, 6) for key, value in sorted(by_session.items())},
        "verdict": verdict,
        "fail_reasons": fail_reasons,
    }


def summarize(candidates: list[Candidate], min_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_config: dict[str, list[Candidate]] = defaultdict(list)
    by_setup: dict[str, list[Candidate]] = defaultdict(list)
    by_direction: dict[str, list[Candidate]] = defaultdict(list)
    for row in candidates:
        by_config[row.config_id].append(row)
        by_setup[row.setup].append(row)
        by_direction[row.direction].append(row)

    config_rows = []
    for config_id, rows in sorted(by_config.items()):
        summary = summarize_group(rows, min_count)
        summary["config_id"] = config_id
        summary["setup"] = rows[0].setup if rows else ""
        config_rows.append(summary)
    config_rows.sort(key=lambda row: (row["verdict"] != "PASS_RESEARCH_SCREEN", -row["pf_r_after_cost"], -row["count"]))

    overall = summarize_group(candidates, min_count)
    overall.update(
        {
            "verdict": "PASS_HAS_RESEARCH_CANDIDATE"
            if any(row["verdict"] == "PASS_RESEARCH_SCREEN" for row in config_rows)
            else "REJECT_NO_PASSER",
            "setup_summary": {key: summarize_group(rows, min_count) for key, rows in sorted(by_setup.items())},
            "direction_summary": {key: summarize_group(rows, min_count) for key, rows in sorted(by_direction.items())},
            "passing_configs": [row["config_id"] for row in config_rows if row["verdict"] == "PASS_RESEARCH_SCREEN"],
        }
    )
    return overall, config_rows


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


def render_markdown(result: dict[str, Any], config_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Sonic Compression-To-Impulse Probe",
        "",
        f"- Run: `{result['run_id']}`",
        f"- Source bars: `{result['load_meta']['loaded_bars']}`",
        f"- Candidates: `{result['overall']['count']}`",
        f"- Verdict: `{result['overall']['verdict']}`",
        f"- Cost assumption: `{result['cost_r']}` R per candidate",
        "",
        "## Overall",
        "",
        f"- PF after cost: `{result['overall']['pf_r_after_cost']}`",
        f"- Sum R after cost: `{result['overall']['sum_r_after_cost']}`",
        f"- Mean R after cost: `{result['overall']['mean_r_after_cost']}`",
        f"- Positive half-years: `{result['overall']['positive_half_years']}/{result['overall']['total_half_years']}`",
        f"- Positive years: `{result['overall']['positive_years']}/{result['overall']['total_years']}`",
        "",
        "## Top Configs",
        "",
        "| config | setup | n | PF cost | mean R cost | half-years | years | verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in config_rows[:12]:
        lines.append(
            "| {config_id} | {setup} | {count} | {pf_r_after_cost} | {mean_r_after_cost} | {positive_half_years}/{total_half_years} | {positive_years}/{total_years} | {verdict} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
        ]
    )
    if result["overall"]["verdict"] == "PASS_HAS_RESEARCH_CANDIDATE":
        lines.append("At least one offline config passed the research screen. Pre-register a single default-off EA lane before backtesting.")
    else:
        lines.append("No config passed the pre-registered research screen. Do not patch EA entry logic from this probe.")
    return "\n".join(lines) + "\n"


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = run_dir_for(args.run, args.ea_name)
    if not run_dir.exists():
        raise SystemExit(f"run not found: {run_dir}")
    log_root = logs_dir(run_dir)
    pvsra_files = sorted(log_root.glob("*_PVSRA_SR_Fields_*.csv"))
    if not pvsra_files:
        raise SystemExit(f"missing PVSRA/SR sidecar under {log_root}")
    configs = build_configs(args.profile)
    bars, pip_size, load_meta = load_bars(pvsra_files[0])
    candidates = scan_candidates(bars, pip_size, args.cost_r, configs)
    overall, config_rows = summarize(candidates, args.min_count)

    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    candidate_rows = [asdict(row) for row in candidates[: args.max_candidate_rows]]
    result = {
        "schema_version": "sonic_compression_impulse_probe.v1",
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "cost_r": args.cost_r,
        "profile": args.profile,
        "min_count": args.min_count,
        "candidate_rows_written": len(candidate_rows),
        "candidate_rows_truncated": len(candidates) > len(candidate_rows),
        "load_meta": load_meta,
        "configs": [asdict(cfg) for cfg in configs],
        "overall": overall,
        "by_config": config_rows,
    }
    suffix = "" if args.profile == "strict" else f"_{args.profile}"
    json_path = analysis_dir / f"sonic_compression_impulse_probe{suffix}.json"
    md_path = analysis_dir / f"sonic_compression_impulse_probe{suffix}.md"
    cfg_path = analysis_dir / f"sonic_compression_impulse_by_config{suffix}.csv"
    candidates_path = analysis_dir / f"sonic_compression_impulse_candidates{suffix}.csv"
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="AlphaFactory run id or run directory")
    parser.add_argument("--ea-name", default=DEFAULT_EA)
    parser.add_argument("--cost-r", type=float, default=0.05, help="R cost deducted from every candidate label")
    parser.add_argument("--profile", choices=("strict", "exploratory", "micro", "all"), default="strict")
    parser.add_argument("--min-count", type=int, default=240, help="Minimum candidate count for a research passer")
    parser.add_argument("--max-candidate-rows", type=int, default=25000)
    return parser


def main() -> int:
    args = build_parser().parse_args()
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
