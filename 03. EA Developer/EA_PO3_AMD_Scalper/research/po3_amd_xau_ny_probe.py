#!/usr/bin/env python3
"""Frozen New York branch probe for HYP-PO3-AMD-SCALP-M5-XAU-003."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import po3_amd_xau_normalized_probe as normalized


base = normalized.base
HERE = Path(__file__).resolve().parent
SPEC = HERE / "HYP-PO3-AMD-SCALP-M5-XAU-003_FROZEN_PREREG.md"
NORMALIZED_DEPENDENCY = HERE / "po3_amd_xau_normalized_probe.py"
H001_BASE_DEPENDENCY = HERE / "po3_amd_xau_offline_probe.py"
HYPOTHESIS_ID = "HYP-PO3-AMD-SCALP-M5-XAU-003"


def in_ny_entry_window(ts_et: pd.Timestamp) -> bool:
    minute = ts_et.hour * 60 + ts_et.minute
    return 420 <= minute < 600


def evaluate(frame: pd.DataFrame, point: float):
    highs = frame["high"].to_numpy(float)
    lows = frame["low"].to_numpy(float)
    opens = frame["open"].to_numpy(float)
    closes = frame["close"].to_numpy(float)
    atr = frame["atr"].to_numpy(float)
    control: list[base.Trade] = []
    challenger: list[base.Trade] = []
    counts = {
        "days_total": 0,
        "asia_atr_ready": 0,
        "range_ratio_ok": 0,
        "sweeps": 0,
        "displacements": 0,
        "fvgs": 0,
        "retests": 0,
    }
    frame = frame.copy()
    frame["trade_date"] = frame["time_et"].map(base.trade_date_for)
    for trade_date, day in frame.groupby("trade_date", sort=True):
        counts["days_total"] += 1
        day_indices = day.index.to_numpy()
        asia = day.loc[(day["time_et"].dt.hour >= 20) | (day["time_et"].dt.hour < 3)]
        if asia.empty:
            continue
        asia_atr = asia["atr"].to_numpy(float)
        asia_atr = asia_atr[np.isfinite(asia_atr)]
        if len(asia_atr) == 0:
            continue
        asia_atr_ref = float(np.median(asia_atr))
        if asia_atr_ref <= 0.0:
            continue
        counts["asia_atr_ready"] += 1
        asia_high = float(asia["high"].max())
        asia_low = float(asia["low"].min())
        range_ratio = (asia_high - asia_low) / asia_atr_ref
        if not (normalized.ASIA_MIN_RANGE_ATR <= range_ratio <= normalized.ASIA_MAX_RANGE_ATR):
            continue
        counts["range_ratio_ok"] += 1
        manipulation = day.loc[(day["time_et"].dt.hour >= 7) & (day["time_et"].dt.hour < 10)]
        control_done = False
        challenger_done = False
        for sweep_idx in manipulation.index:
            if not math.isfinite(atr[sweep_idx]) or atr[sweep_idx] / point < base.ATR_MIN_PTS:
                continue
            bias = int(frame.loc[sweep_idx, "h4_bias"])
            direction = 0
            if bias == 1 and lows[sweep_idx] <= asia_low - point and closes[sweep_idx] > asia_low:
                direction = 1
            elif bias == -1 and highs[sweep_idx] >= asia_high + point and closes[sweep_idx] < asia_high:
                direction = -1
            if direction == 0:
                continue
            counts["sweeps"] += 1
            sweep_extreme = lows[sweep_idx] if direction == 1 else highs[sweep_idx]
            stop = (
                sweep_extreme - base.SL_BUFFER_PTS * point
                if direction == 1
                else sweep_extreme + base.SL_BUFFER_PTS * point
            )
            if not control_done and sweep_idx + 1 in day_indices:
                trade = base.simulate_trade(frame, sweep_idx + 1, direction, stop, point, "control", trade_date)
                if trade is not None:
                    control.append(trade)
                    control_done = True
            pivot_idx = base.last_confirmed_pivot(
                highs if direction == 1 else lows,
                sweep_idx,
                base.SWING_STRENGTH,
                direction == 1,
            )
            if pivot_idx is None:
                continue
            mss_level = highs[pivot_idx] if direction == 1 else lows[pivot_idx]
            for disp_idx in range(sweep_idx + 1, min(len(frame), sweep_idx + base.DISPLACEMENT_BARS + 1)):
                if frame.loc[disp_idx, "trade_date"] != trade_date:
                    break
                body = abs(closes[disp_idx] - opens[disp_idx])
                mss = closes[disp_idx] > mss_level if direction == 1 else closes[disp_idx] < mss_level
                if not (body >= base.DISPLACEMENT_ATR * atr[disp_idx] and mss):
                    continue
                counts["displacements"] += 1
                if disp_idx < 2:
                    continue
                if direction == 1 and lows[disp_idx] > highs[disp_idx - 2]:
                    fvg_low, fvg_high = highs[disp_idx - 2], lows[disp_idx]
                elif direction == -1 and highs[disp_idx] < lows[disp_idx - 2]:
                    fvg_low, fvg_high = highs[disp_idx], lows[disp_idx - 2]
                else:
                    continue
                counts["fvgs"] += 1
                for retest_idx in range(disp_idx + 1, min(len(frame), disp_idx + base.RETEST_BARS + 1)):
                    if frame.loc[retest_idx, "trade_date"] != trade_date:
                        break
                    if not in_ny_entry_window(frame.loc[retest_idx, "time_et"]):
                        continue
                    overlap = lows[retest_idx] <= fvg_high and highs[retest_idx] >= fvg_low
                    direction_close = (
                        closes[retest_idx] > opens[retest_idx]
                        if direction == 1
                        else closes[retest_idx] < opens[retest_idx]
                    )
                    if not (overlap and direction_close):
                        continue
                    counts["retests"] += 1
                    if retest_idx + 1 < len(frame):
                        trade = base.simulate_trade(
                            frame,
                            retest_idx + 1,
                            direction,
                            stop,
                            point,
                            "challenger",
                            trade_date,
                        )
                        if trade is not None:
                            challenger.append(trade)
                            challenger_done = True
                    break
                if challenger_done:
                    break
            if challenger_done and control_done:
                break
    return control, challenger, counts


def output_argument() -> Path:
    try:
        return Path(sys.argv[sys.argv.index("--out") + 1])
    except (ValueError, IndexError) as exc:
        raise SystemExit("--out is required") from exc


def main() -> int:
    normalized.SPEC = SPEC
    normalized.BASE_PROBE = NORMALIZED_DEPENDENCY
    normalized.HYPOTHESIS_ID = HYPOTHESIS_ID
    normalized.evaluate = evaluate
    normalized.__file__ = str(Path(__file__).resolve())
    result_code = normalized.main()
    out = output_argument()
    evidence = json.loads(out.read_text(encoding="utf-8"))
    evidence["session"] = {
        "timezone": "America/New_York",
        "manipulation_start": "07:00",
        "entry_confirmation_end": "10:00",
        "branch": "NEW_YORK",
    }
    evidence["source_hashes"]["h001_base_dependency_sha256"] = normalized.sha256_file(H001_BASE_DEPENDENCY)
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())

