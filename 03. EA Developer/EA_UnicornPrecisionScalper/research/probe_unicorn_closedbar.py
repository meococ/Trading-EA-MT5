#!/usr/bin/env python3
"""Closed-bar opportunity-density probe for HYP-UPS-XAU-M5-001.

This is intentionally not a backtest. It does not simulate fills or optimize
thresholds. Raw MT5 bars remain in the terminal data store; only the bounded
JSON summary is written to the workspace on drive D.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np


HYPOTHESIS_ID = "HYP-UPS-XAU-M5-001"
WINDOW_FROM = datetime(2024, 1, 1, tzinfo=timezone.utc)
WINDOW_TO = datetime(2026, 7, 16, tzinfo=timezone.utc)
WARMUP_FROM = WINDOW_FROM - timedelta(days=180)


def ema(values: np.ndarray, period: int) -> np.ndarray:
    result = np.empty(len(values), dtype=float)
    result[:] = np.nan
    if len(values) < period:
        return result
    seed = float(np.mean(values[:period]))
    result[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    for i in range(period, len(values)):
        result[i] = alpha * float(values[i]) + (1.0 - alpha) * result[i - 1]
    return result


def atr(rates: np.ndarray, period: int) -> np.ndarray:
    high = rates["high"].astype(float)
    low = rates["low"].astype(float)
    close = rates["close"].astype(float)
    previous = np.roll(close, 1)
    previous[0] = close[0]
    true_range = np.maximum(high - low, np.maximum(np.abs(high - previous), np.abs(low - previous)))
    output = np.empty(len(rates), dtype=float)
    output[:] = np.nan
    if len(rates) >= period:
        rolling = np.convolve(true_range, np.ones(period, dtype=float), mode="valid") / period
        output[period - 1 :] = rolling
    return output


def trend_series(rates: np.ndarray, seconds_per_bar: int) -> tuple[np.ndarray, np.ndarray]:
    close = rates["close"].astype(float)
    fast = ema(close, 20)
    slow = ema(close, 50)
    trend = np.zeros(len(rates), dtype=np.int8)
    valid = np.isfinite(fast) & np.isfinite(slow)
    trend[valid & (close > fast) & (fast > slow)] = 1
    trend[valid & (close < fast) & (fast < slow)] = -1
    close_times = rates["time"].astype(np.int64) + seconds_per_bar
    return close_times, trend


def last_closed_trend(close_times: np.ndarray, trend: np.ndarray, decision_time: int) -> int:
    index = int(np.searchsorted(close_times, decision_time, side="right") - 1)
    return int(trend[index]) if index >= 0 else 0


def best_overlap_ratio(rates: np.ndarray, start: int, end: int, direction: int, lo: float, hi: float) -> float:
    width = max(hi - lo, 0.0)
    if width <= 0.0:
        return 0.0
    best = 0.0
    for j in range(start, end + 1):
        opposite = rates[j]["close"] < rates[j]["open"] if direction > 0 else rates[j]["close"] > rates[j]["open"]
        if not opposite:
            continue
        candle_lo = min(float(rates[j]["open"]), float(rates[j]["close"]))
        candle_hi = max(float(rates[j]["open"]), float(rates[j]["close"]))
        overlap = max(0.0, min(hi, candle_hi) - max(lo, candle_lo))
        best = max(best, overlap / width)
    return best


def detect(rates: np.ndarray, h4: np.ndarray, d1: np.ndarray) -> list[dict[str, object]]:
    atr14 = atr(rates, 14)
    h4_close_times, h4_trend = trend_series(h4, 4 * 60 * 60)
    d1_close_times, d1_trend = trend_series(d1, 24 * 60 * 60)
    found: list[dict[str, object]] = []
    for i in range(64, len(rates)):
        decision_time = int(rates[i]["time"]) + 5 * 60
        dt = datetime.fromtimestamp(decision_time, tz=timezone.utc)
        if dt < WINDOW_FROM or dt >= WINDOW_TO or not (7 <= dt.hour < 16):
            continue
        if int(rates[i]["spread"]) > 35:
            continue
        current_atr = float(atr14[i - 1])
        if not np.isfinite(current_atr) or current_atr <= 0.0:
            continue
        h4_bias = last_closed_trend(h4_close_times, h4_trend, decision_time)
        d1_bias = last_closed_trend(d1_close_times, d1_trend, decision_time)
        if h4_bias == 0 or d1_bias == -h4_bias:
            continue

        left, middle, right = i - 2, i - 1, i
        prior_low = float(np.min(rates["low"][left - 12 : left]))
        prior_high = float(np.max(rates["high"][left - 12 : left]))
        bull_sweep = float(rates[left]["low"]) < prior_low and float(rates[left]["close"]) > prior_low
        bear_sweep = float(rates[left]["high"]) > prior_high and float(rates[left]["close"]) < prior_high
        body = abs(float(rates[middle]["close"]) - float(rates[middle]["open"]))
        body_atr = body / current_atr
        if body_atr < 1.20:
            continue

        direction = 0
        fvg_lo = fvg_hi = 0.0
        if bull_sweep and h4_bias > 0 and float(rates[middle]["close"]) > float(rates[middle]["open"]):
            if float(rates[right]["low"]) > float(rates[left]["high"]):
                direction = 1
                fvg_lo, fvg_hi = float(rates[left]["high"]), float(rates[right]["low"])
        elif bear_sweep and h4_bias < 0 and float(rates[middle]["close"]) < float(rates[middle]["open"]):
            if float(rates[right]["high"]) < float(rates[left]["low"]):
                direction = -1
                fvg_lo, fvg_hi = float(rates[right]["high"]), float(rates[left]["low"])
        if direction == 0 or (fvg_hi - fvg_lo) / current_atr < 0.05:
            continue

        overlap = best_overlap_ratio(rates, max(0, left - 6), left, direction, fvg_lo, fvg_hi)
        if overlap < 0.10:
            continue
        range_lo = float(np.min(rates["low"][i - 24 : i + 1]))
        range_hi = float(np.max(rates["high"][i - 24 : i + 1]))
        midpoint = (range_lo + range_hi) / 2.0
        pd_ok = float(rates[right]["close"]) <= midpoint if direction > 0 else float(rates[right]["close"]) >= midpoint
        score = 15 + (10 if d1_bias == h4_bias else 0) + 15
        score += 20 if body_atr >= 1.80 else 15
        score += 10
        score += 20 if overlap >= 0.25 else 15
        score += 10 if pd_ok else 0
        if score < 75:
            continue
        found.append(
            {
                "decision_time_utc": dt.isoformat().replace("+00:00", "Z"),
                "direction": "long" if direction > 0 else "short",
                "score": score,
                "body_atr": round(body_atr, 6),
                "overlap_ratio": round(overlap, 6),
                "spread_points": int(rates[i]["spread"]),
            }
        )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", default=r"C:\Program Files\MetaTrader 5\terminal64.exe")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not mt5.initialize(path=args.terminal):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected:
            raise RuntimeError("MT5 terminal is not connected")
        m5 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M5, WARMUP_FROM, WINDOW_TO)
        h4 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_H4, WARMUP_FROM - timedelta(days=180), WINDOW_TO)
        d1 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_D1, WARMUP_FROM - timedelta(days=3650), WINDOW_TO)
        if m5 is None or h4 is None or d1 is None:
            raise RuntimeError(f"MT5 rates unavailable: {mt5.last_error()}")
        candidates = detect(m5, h4, d1)
        month_counts = Counter(item["decision_time_utc"][:7] for item in candidates)
        direction_counts = Counter(item["direction"] for item in candidates)
        monthly_values = sorted(month_counts.values())
        median_monthly = float(np.median(monthly_values)) if monthly_values else 0.0
        criteria = {
            "min_candidates_120": len(candidates) >= 120,
            "min_long_20": direction_counts["long"] >= 20,
            "min_short_20": direction_counts["short"] >= 20,
            "min_active_months_24": len(month_counts) >= 24,
            "median_candidates_per_active_month_ge_4": median_monthly >= 4.0,
        }
        source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
        payload = {
            "schema_version": "unicorn_closedbar_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "purpose": "opportunity density only; not a fill or profitability backtest",
            "source_sha256": source_sha,
            "terminal": {
                "company": terminal.company,
                "build": terminal.build,
                "connected": bool(terminal.connected),
                "trade_allowed": bool(terminal.trade_allowed),
                "data_path": terminal.data_path,
            },
            "data": {
                "symbol": args.symbol,
                "window_from": WINDOW_FROM.strftime("%Y.%m.%d"),
                "window_to_inclusive": "2026.07.15",
                "m5_bars": len(m5),
                "h4_bars": len(h4),
                "d1_bars": len(d1),
                "raw_bars_persisted_to_workspace": False,
            },
            "result": {
                "candidate_count": len(candidates),
                "direction_counts": dict(sorted(direction_counts.items())),
                "active_months": len(month_counts),
                "median_candidates_per_active_month": median_monthly,
                "monthly_counts": dict(sorted(month_counts.items())),
                "criteria": criteria,
                "verdict": "PASS" if all(criteria.values()) else "FAIL",
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload["result"], ensure_ascii=False))
        print(f"PROBE_ARTIFACT={args.output.resolve()}")
        return 0 if all(criteria.values()) else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
