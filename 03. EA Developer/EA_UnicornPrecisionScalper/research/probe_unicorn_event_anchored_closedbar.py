#!/usr/bin/env python3
"""Frozen no-outcome event-state probe for HYP-UPS-XAU-M5-005."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

from probe_unicorn_closedbar import atr, best_overlap_ratio, last_closed_trend, trend_series


HYPOTHESIS_ID = "HYP-UPS-XAU-M5-005"
WINDOW_FROM = datetime(2024, 1, 1, tzinfo=timezone.utc)
WINDOW_TO = datetime(2025, 12, 26, tzinfo=timezone.utc)
WARMUP_FROM = WINDOW_FROM - timedelta(days=180)
SESSION_START_HOUR = 7
SESSION_END_HOUR = 16
FIXED_STATE_BARS = 4
SWEEP_LOOKBACK = 12
MAX_CASEBOOK_ROWS = 200


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def is_sweep(rates: np.ndarray, index: int, direction: int) -> tuple[bool, float]:
    if index < SWEEP_LOOKBACK:
        return False, 0.0
    prior_low = float(np.min(rates["low"][index - SWEEP_LOOKBACK : index]))
    prior_high = float(np.max(rates["high"][index - SWEEP_LOOKBACK : index]))
    if direction > 0:
        passed = float(rates[index]["low"]) < prior_low and float(rates[index]["close"]) > prior_low
        return passed, float(rates[index]["low"])
    passed = float(rates[index]["high"]) > prior_high and float(rates[index]["close"]) < prior_high
    return passed, float(rates[index]["high"])


def find_fixed_sweep(rates: np.ndarray, left: int, direction: int) -> tuple[int, float] | None:
    for index in range(left, left - FIXED_STATE_BARS, -1):
        passed, extreme = is_sweep(rates, index, direction)
        if passed:
            return index, extreme
    return None


def structurally_invalidated(
    rates: np.ndarray, sweep_index: int, left: int, direction: int, extreme: float
) -> bool:
    closes = rates["close"][sweep_index + 1 : left + 1].astype(float)
    if direction > 0:
        return bool(np.any(closes <= extreme))
    return bool(np.any(closes >= extreme))


def find_event_sweep(rates: np.ndarray, left: int, direction: int) -> tuple[int, float] | None:
    left_close = datetime.fromtimestamp(int(rates[left]["time"]) + 5 * 60, tz=timezone.utc)
    session_open = left_close.replace(hour=SESSION_START_HOUR, minute=0, second=0, microsecond=0)
    for index in range(left, SWEEP_LOOKBACK - 1, -1):
        bar_close = datetime.fromtimestamp(int(rates[index]["time"]) + 5 * 60, tz=timezone.utc)
        if bar_close < session_open:
            break
        passed, extreme = is_sweep(rates, index, direction)
        if passed and not structurally_invalidated(rates, index, left, direction, extreme):
            return index, extreme
    return None


def detect(rates: np.ndarray, h4: np.ndarray, d1: np.ndarray) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    atr14 = atr(rates, 14)
    h4_close_times, h4_trend = trend_series(h4, 4 * 60 * 60)
    d1_close_times, d1_trend = trend_series(d1, 24 * 60 * 60)
    event_candidates: list[dict[str, object]] = []
    control_candidates: list[dict[str, object]] = []

    for i in range(72, len(rates)):
        decision_time = int(rates[i]["time"]) + 5 * 60
        dt = datetime.fromtimestamp(decision_time, tz=timezone.utc)
        if dt < WINDOW_FROM or dt >= WINDOW_TO or not (SESSION_START_HOUR <= dt.hour < SESSION_END_HOUR):
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
        body = abs(float(rates[middle]["close"]) - float(rates[middle]["open"]))
        body_atr = body / current_atr
        if body_atr < 1.20:
            continue

        direction = 0
        fvg_lo = fvg_hi = 0.0
        if h4_bias > 0 and float(rates[middle]["close"]) > float(rates[middle]["open"]):
            if float(rates[right]["low"]) > float(rates[left]["high"]):
                direction = 1
                fvg_lo, fvg_hi = float(rates[left]["high"]), float(rates[right]["low"])
        elif h4_bias < 0 and float(rates[middle]["close"]) < float(rates[middle]["open"]):
            if float(rates[right]["high"]) < float(rates[left]["low"]):
                direction = -1
                fvg_lo, fvg_hi = float(rates[right]["high"]), float(rates[left]["low"])
        fvg_atr = (fvg_hi - fvg_lo) / current_atr
        if direction == 0 or fvg_atr < 0.05:
            continue

        overlap = best_overlap_ratio(rates, max(0, left - 8), left, direction, fvg_lo, fvg_hi)
        if overlap < 0.10:
            continue
        range_lo = float(np.min(rates["low"][i - 24 : i + 1]))
        range_hi = float(np.max(rates["high"][i - 24 : i + 1]))
        midpoint = (range_lo + range_hi) / 2.0
        pd_ok = float(rates[right]["close"]) <= midpoint if direction > 0 else float(rates[right]["close"]) >= midpoint
        score = 15 + (10 if d1_bias == h4_bias else 0) + 15
        score += 20 if body_atr >= 1.80 else 15
        score += 10 + (20 if overlap >= 0.25 else 15) + (10 if pd_ok else 0)
        if score < 75:
            continue

        fixed_sweep = find_fixed_sweep(rates, left, direction)
        event_sweep = find_event_sweep(rates, left, direction)
        common = {
            "decision_time_utc": dt.isoformat().replace("+00:00", "Z"),
            "direction": "long" if direction > 0 else "short",
            "score": score,
            "body_atr": round(body_atr, 6),
            "fvg_atr": round(fvg_atr, 6),
            "overlap_ratio": round(overlap, 6),
            "spread_points": int(rates[i]["spread"]),
            "h4_bias": h4_bias,
            "d1_bias": d1_bias,
        }
        if fixed_sweep is not None:
            index, extreme = fixed_sweep
            control_candidates.append(
                common | {"sweep_age_bars": left - index, "sweep_extreme": round(extreme, 6)}
            )
        if event_sweep is not None:
            index, extreme = event_sweep
            invalidated = structurally_invalidated(rates, index, left, direction, extreme)
            event_candidates.append(
                common
                | {
                    "sweep_age_bars": left - index,
                    "sweep_extreme": round(extreme, 6),
                    "fixed_control_eligible": left - index < FIXED_STATE_BARS,
                    "structural_invalidation_checked": True,
                    "invalidated_before_decision": invalidated,
                }
            )
    return event_candidates, control_candidates


def deterministic_casebook(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    if len(candidates) <= MAX_CASEBOOK_ROWS:
        return candidates
    indices = np.linspace(0, len(candidates) - 1, MAX_CASEBOOK_ROWS, dtype=int)
    return [candidates[int(index)] for index in indices]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--probe-output", type=Path, required=True)
    parser.add_argument("--casebook-output", type=Path, required=True)
    args = parser.parse_args()

    if not mt5.initialize(path=str(args.terminal), timeout=60_000, portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected:
            raise RuntimeError("MT5 terminal is not connected")
        data_path = Path(terminal.data_path).resolve()
        if data_path.drive.upper() != "D:":
            raise RuntimeError(f"portable MT5 data path must be on D:, got {data_path}")

        m5 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M5, WARMUP_FROM, WINDOW_TO)
        h4 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_H4, WARMUP_FROM - timedelta(days=180), WINDOW_TO)
        d1 = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_D1, WARMUP_FROM - timedelta(days=3650), WINDOW_TO)
        if m5 is None or h4 is None or d1 is None:
            raise RuntimeError(f"MT5 rates unavailable: {mt5.last_error()}")

        event_candidates, control_candidates = detect(m5, h4, d1)
        casebook_rows = deterministic_casebook(event_candidates)
        direction_counts = Counter(str(item["direction"]) for item in event_candidates)
        month_counts = Counter(str(item["decision_time_utc"])[:7] for item in event_candidates)
        late_count = sum(int(item["sweep_age_bars"]) >= FIXED_STATE_BARS for item in event_candidates)
        invalid_count = sum(bool(item["invalidated_before_decision"]) for item in event_candidates)
        elapsed_weeks = (WINDOW_TO - WINDOW_FROM).total_seconds() / (7 * 24 * 60 * 60)
        cadence = len(event_candidates) / elapsed_weeks
        late_share = late_count / len(event_candidates) if event_candidates else 0.0

        casebook = {
            "schema_version": "unicorn_event_state_casebook.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "purpose": "bounded deterministic closed-bar event labels; no forward outcome",
            "selection": "all chronological candidates when <=200; otherwise 200 evenly spaced chronological rows",
            "row_count": len(casebook_rows),
            "rows": casebook_rows,
        }
        args.casebook_output.parent.mkdir(parents=True, exist_ok=True)
        args.casebook_output.write_text(json.dumps(casebook, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        criteria = {
            "cadence_ge_2_0": cadence >= 2.0,
            "cadence_le_5_0": cadence <= 5.0,
            "active_months_ge_20": len(month_counts) >= 20,
            "long_candidates_ge_30": direction_counts["long"] >= 30,
            "short_candidates_ge_30": direction_counts["short"] >= 30,
            "casebook_rows_100_to_200": 100 <= len(casebook_rows) <= MAX_CASEBOOK_ROWS,
            "late_state_share_ge_0_20": late_share >= 0.20,
            "challenger_gt_matched_control": len(event_candidates) > len(control_candidates),
            "invalidated_candidates_eq_0": invalid_count == 0,
        }
        verdict = "PASS" if all(criteria.values()) else "FAIL"
        payload = {
            "schema_version": "unicorn_event_state_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "purpose": "opportunity density and state validity only; not a fill or profitability backtest",
            "probe_script_sha256": sha256_file(Path(__file__)),
            "parent_feature_script_sha256": sha256_file(Path(__file__).parent / "probe_unicorn_closedbar.py"),
            "casebook_path": str(args.casebook_output.resolve()),
            "casebook_sha256": sha256_file(args.casebook_output),
            "terminal": {
                "company": terminal.company,
                "build": terminal.build,
                "connected": bool(terminal.connected),
                "portable": True,
                "data_path": str(data_path),
            },
            "data": {
                "symbol": args.symbol,
                "window_from": "2024.01.01",
                "window_to_inclusive": "2025.12.25",
                "m5_bars": len(m5),
                "h4_bars": len(h4),
                "d1_bars": len(d1),
                "elapsed_calendar_weeks": elapsed_weeks,
                "raw_bars_persisted_to_workspace": False,
                "outcomes_evaluated": False,
            },
            "result": {
                "challenger_candidates": len(event_candidates),
                "matched_control_candidates": len(control_candidates),
                "additional_candidates": len(event_candidates) - len(control_candidates),
                "candidates_per_elapsed_week": cadence,
                "direction_counts": dict(sorted(direction_counts.items())),
                "active_months": len(month_counts),
                "monthly_counts": dict(sorted(month_counts.items())),
                "late_state_candidates": late_count,
                "late_state_share": late_share,
                "maximum_sweep_age_bars": max((int(item["sweep_age_bars"]) for item in event_candidates), default=0),
                "invalidated_candidates": invalid_count,
                "casebook_rows": len(casebook_rows),
                "criteria": criteria,
                "verdict": verdict,
            },
        }
        args.probe_output.parent.mkdir(parents=True, exist_ok=True)
        args.probe_output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(payload["result"], ensure_ascii=False))
        print(f"PROBE_ARTIFACT={args.probe_output.resolve()}")
        print(f"CASEBOOK_ARTIFACT={args.casebook_output.resolve()}")
        return 0 if verdict == "PASS" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
