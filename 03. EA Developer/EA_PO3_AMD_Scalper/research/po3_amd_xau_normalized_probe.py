#!/usr/bin/env python3
"""Frozen ATR-normalized PO3-AMD probe for HYP-...-002.

The immutable HYP-001 module supplies data loading, closed-bar H4 bias,
trade simulation and metric utilities. This file owns the new normalized
Asian-range decision and hashes that dependency into its evidence packet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

import po3_amd_xau_offline_probe as base


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = HERE / "HYP-PO3-AMD-SCALP-M5-XAU-002_FROZEN_PREREG.md"
BASE_PROBE = HERE / "po3_amd_xau_offline_probe.py"
REPORT = ROOT / "05. Playbook/Strategy/PO3_AMD_Scalper_Deep_Research_Report.html"
HYPOTHESIS_ID = "HYP-PO3-AMD-SCALP-M5-XAU-002"
EA_NAME = "EA_PO3_AMD_Scalper"
ASIA_MIN_RANGE_ATR = 80.0 / 60.0
ASIA_MAX_RANGE_ATR = 300.0 / 20.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def evaluate(frame: pd.DataFrame, point: float) -> tuple[list[base.Trade], list[base.Trade], dict[str, int]]:
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
        if not (ASIA_MIN_RANGE_ATR <= range_ratio <= ASIA_MAX_RANGE_ATR):
            continue
        counts["range_ratio_ok"] += 1
        manipulation = day.loc[(day["time_et"].dt.hour >= 3) & (day["time_et"].dt.hour < 5)]
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
                    if not base.in_entry_window(frame.loc[retest_idx, "time_et"]):
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


def gate_metrics(control: dict[str, Any], challenger: dict[str, Any]) -> dict[str, bool]:
    control_pf = math.inf if control["profit_factor_infinite"] else float(control["profit_factor_cost_proxy"] or 0.0)
    challenger_pf = (
        math.inf if challenger["profit_factor_infinite"] else float(challenger["profit_factor_cost_proxy"] or 0.0)
    )
    if challenger["profit_factor_infinite"]:
        pf_margin = not control["profit_factor_infinite"]
    elif control["profit_factor_infinite"]:
        pf_margin = False
    else:
        pf_margin = challenger_pf >= control_pf + 0.20
    return {
        "cadence_min": challenger["trades_per_elapsed_week"] >= 2.0,
        "cadence_max": challenger["trades_per_elapsed_week"] <= 5.0,
        "pf": challenger_pf >= 1.5,
        "expectancy": challenger["expectancy_r"] >= 0.4,
        "drawdown": challenger["max_drawdown_pct_at_0_25_risk"] <= 5.0,
        "positive_years": challenger["positive_years"] >= 2,
        "net_positive_and_not_below_control": challenger["net_r"] > 0 and challenger["net_r"] >= control["net_r"],
        "pf_margin_over_control": pf_margin,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    for required in (SPEC, BASE_PROBE, REPORT):
        if not required.is_file():
            raise SystemExit(f"required frozen input missing: {required}")
    if not mt5.initialize(path=str(args.terminal), timeout=60_000):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None:
            raise RuntimeError(f"terminal_info unavailable: {mt5.last_error()}")
        if not mt5.symbol_select(base.SYMBOL, True):
            raise RuntimeError(f"symbol_select {base.SYMBOL} failed: {mt5.last_error()}")
        symbol = mt5.symbol_info(base.SYMBOL)
        point = float(symbol.point) if symbol is not None and symbol.point > 0 else base.POINT_FALLBACK
        m5 = base.load_rates(mt5.TIMEFRAME_M5)
        h4 = base.load_rates(mt5.TIMEFRAME_H4)
        m5["time_et"] = m5["time_utc"].dt.tz_convert("America/New_York")
        m5["atr"] = base.wilder_atr(m5, base.ATR_PERIOD)
        bias = base.build_h4_bias(h4)
        m5 = pd.merge_asof(
            m5.sort_values("time_utc"),
            bias.sort_values("available_utc"),
            left_on="time_utc",
            right_on="available_utc",
            direction="backward",
        ).reset_index(drop=True)
        m5["h4_bias"] = m5["h4_bias"].fillna(0).astype(int)
        control_trades, challenger_trades, counts = evaluate(m5, point)
        control = base.metrics(control_trades)
        challenger = base.metrics(challenger_trades)
        gates = gate_metrics(control, challenger)
        verdict = "CONTINUE_TO_EA_BUILD" if all(gates.values()) else "KILL_AT_OFFLINE_PROBE"
        account_fingerprint = None
        if account is not None:
            safe_identity = f"{account.server}|{account.currency}|{account.leverage}"
            account_fingerprint = hashlib.sha256(safe_identity.encode("utf-8")).hexdigest().upper()
        result = {
            "schema_version": "po3_amd_normalized_offline_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "ea_name": EA_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "verdict": verdict,
            "promotion_eligible": False,
            "cost_status": "UNVERIFIED_REPORT_ASSUMPTION",
            "window": {"from": base.FROM_UTC.isoformat(), "to": base.TO_UTC.isoformat()},
            "symbol": base.SYMBOL,
            "point": point,
            "normalization": {
                "asia_atr_reference": "median closed M5 Wilder ATR(14) inside completed Asian box",
                "min_range_atr": ASIA_MIN_RANGE_ATR,
                "max_range_atr": ASIA_MAX_RANGE_ATR,
            },
            "bars": {"m5": len(m5), "h4": len(h4)},
            "source_hashes": {
                "prereg_sha256": sha256_file(SPEC),
                "probe_script_sha256": sha256_file(Path(__file__)),
                "base_probe_dependency_sha256": sha256_file(BASE_PROBE),
                "research_report_sha256": sha256_file(REPORT),
            },
            "terminal": {
                "build": terminal.build,
                "connected": terminal.connected,
                "data_path": terminal.data_path,
                "account_fingerprint": account_fingerprint,
            },
            "gate_counts": counts,
            "control": control,
            "challenger": challenger,
            "gates": gates,
            "trades": {
                "control": [asdict(item) for item in control_trades],
                "challenger": [asdict(item) for item in challenger_trades],
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"verdict": verdict, "counts": counts, "control": control, "challenger": challenger, "gates": gates}, indent=2, allow_nan=False))
        return 0 if verdict == "CONTINUE_TO_EA_BUILD" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())

