#!/usr/bin/env python3
"""Frozen closed-bar PO3-AMD XAUUSD probe versus a sweep-only control.

This is a cheap research screen, not Strategy Tester or promotion evidence.
It intentionally uses one parameter set and writes one hash-bound JSON result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = HERE / "HYP-PO3-AMD-SCALP-M5-XAU-001_PROBE_SPEC.md"
REPORT = ROOT / "05. Playbook/Strategy/PO3_AMD_Scalper_Deep_Research_Report.html"
HYPOTHESIS_ID = "HYP-PO3-AMD-SCALP-M5-XAU-001"
EA_NAME = "EA_PO3_AMD_Scalper"
SYMBOL = "XAUUSD"
FROM_UTC = datetime(2022, 1, 1, tzinfo=timezone.utc)
TO_UTC = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
POINT_FALLBACK = 0.01

ASIA_MIN_PTS = 80.0
ASIA_MAX_PTS = 300.0
ATR_PERIOD = 14
ATR_MIN_PTS = 15.0
DISPLACEMENT_ATR = 1.5
DISPLACEMENT_BARS = 3
RETEST_BARS = 6
SWING_STRENGTH = 2
SL_BUFFER_PTS = 40.0
MAX_HOLD_BARS = 18
TIME_STOP_BARS = 6
COST_PROXY_PTS = 35.0
RISK_PCT = 0.25
ELAPSED_WEEKS = (TO_UTC.date() - FROM_UTC.date()).days / 7.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load_rates(timeframe: int) -> pd.DataFrame:
    parts: list[np.ndarray] = []
    for year in range(2022, 2025):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        rates = mt5.copy_rates_range(SYMBOL, timeframe, start, end)
        if rates is None:
            raise RuntimeError(f"copy_rates_range failed tf={timeframe}: {mt5.last_error()}")
        if len(rates) > 1:
            parts.append(rates)
    if not parts:
        raise RuntimeError(f"no {SYMBOL} rates for timeframe={timeframe}")
    raw = np.concatenate(parts)
    frame = pd.DataFrame(raw).drop_duplicates(subset=["time"]).sort_values("time")
    frame["time_utc"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.loc[(frame["time_utc"] >= pd.Timestamp(FROM_UTC)) & (frame["time_utc"] <= pd.Timestamp(TO_UTC))]
    return frame.reset_index(drop=True)


def wilder_atr(frame: pd.DataFrame, period: int) -> np.ndarray:
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    close = frame["close"].to_numpy(float)
    prev = np.r_[np.nan, close[:-1]]
    tr = np.nanmax(np.vstack([high - low, np.abs(high - prev), np.abs(low - prev)]), axis=0)
    return pd.Series(tr).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().to_numpy()


def confirmed_pivots(values: np.ndarray, strength: int, high: bool) -> list[int]:
    result: list[int] = []
    for i in range(strength, len(values) - strength):
        left = values[i - strength : i]
        right = values[i + 1 : i + strength + 1]
        if high and values[i] > float(np.max(left)) and values[i] > float(np.max(right)):
            result.append(i)
        if not high and values[i] < float(np.min(left)) and values[i] < float(np.min(right)):
            result.append(i)
    return result


def build_h4_bias(h4: pd.DataFrame) -> pd.DataFrame:
    highs = h4["high"].to_numpy(float)
    lows = h4["low"].to_numpy(float)
    closes = h4["close"].to_numpy(float)
    high_pivots = set(confirmed_pivots(highs, SWING_STRENGTH, True))
    low_pivots = set(confirmed_pivots(lows, SWING_STRENGTH, False))
    known_highs: list[int] = []
    known_lows: list[int] = []
    rows: list[dict[str, Any]] = []
    for j in range(len(h4)):
        confirmed_index = j - SWING_STRENGTH
        if confirmed_index in high_pivots:
            known_highs.append(confirmed_index)
        if confirmed_index in low_pivots:
            known_lows.append(confirmed_index)
        bias = 0
        midpoint = math.nan
        if len(known_highs) >= 2 and len(known_lows) >= 2:
            h0, h1 = known_highs[-2], known_highs[-1]
            l0, l1 = known_lows[-2], known_lows[-1]
            midpoint = (max(highs[h0], highs[h1]) + min(lows[l0], lows[l1])) / 2.0
            if highs[h1] > highs[h0] and lows[l1] > lows[l0] and closes[j] <= midpoint:
                bias = 1
            elif highs[h1] < highs[h0] and lows[l1] < lows[l0] and closes[j] >= midpoint:
                bias = -1
        rows.append(
            {
                "available_utc": h4.loc[j, "time_utc"] + pd.Timedelta(hours=4),
                "h4_bias": bias,
                "h4_midpoint": midpoint,
            }
        )
    return pd.DataFrame(rows)


def in_entry_window(ts_et: pd.Timestamp) -> bool:
    minute = ts_et.hour * 60 + ts_et.minute
    return 180 <= minute < 270


def trade_date_for(ts_et: pd.Timestamp):
    day = ts_et.date()
    if ts_et.hour >= 20:
        return day + pd.Timedelta(days=1)
    return day


def last_confirmed_pivot(values: np.ndarray, before: int, strength: int, high: bool) -> int | None:
    latest = before - strength
    for i in range(latest, strength - 1, -1):
        left = values[i - strength : i]
        right = values[i + 1 : i + strength + 1]
        if high and values[i] > float(np.max(left)) and values[i] > float(np.max(right)):
            return i
        if not high and values[i] < float(np.min(left)) and values[i] < float(np.min(right)):
            return i
    return None


@dataclass
class Trade:
    role: str
    trade_date: str
    direction: int
    entry_time_utc: str
    entry: float
    stop: float
    risk_points: float
    exit_time_utc: str
    gross_r: float
    cost_r: float
    net_r: float
    exit_reason: str


def simulate_trade(frame: pd.DataFrame, entry_idx: int, direction: int, stop: float, point: float, role: str, trade_date: str) -> Trade | None:
    if entry_idx >= len(frame):
        return None
    entry = float(frame.loc[entry_idx, "open"])
    risk = entry - stop if direction == 1 else stop - entry
    if risk <= max(point, 1e-12):
        return None
    risk_points = risk / point
    realized = 0.0
    remaining = 1.0
    be_armed = False
    partial_done = False
    exit_reason = "MAX_HOLD"
    exit_r = 0.0
    exit_idx = entry_idx
    for j in range(entry_idx, min(len(frame), entry_idx + MAX_HOLD_BARS)):
        high = float(frame.loc[j, "high"])
        low = float(frame.loc[j, "low"])
        close = float(frame.loc[j, "close"])
        stop_now = entry if be_armed else stop
        stopped = low <= stop_now if direction == 1 else high >= stop_now
        if stopped:
            exit_r = 0.0 if be_armed else -1.0
            exit_reason = "BREAKEVEN" if be_armed else "STOP"
            exit_idx = j
            break
        favorable = (high - entry) / risk if direction == 1 else (entry - low) / risk
        if favorable >= 1.0:
            be_armed = True
        if favorable >= 2.0 and not partial_done:
            realized += 1.0
            remaining = 0.5
            partial_done = True
        if favorable >= 3.0:
            exit_r = 3.0
            exit_reason = "TARGET_3R"
            exit_idx = j
            break
        if j - entry_idx + 1 >= TIME_STOP_BARS and not be_armed:
            exit_r = ((close - entry) / risk) if direction == 1 else ((entry - close) / risk)
            exit_reason = "TIME_STOP_30M"
            exit_idx = j
            break
        ts_et = frame.loc[j, "time_et"]
        if ts_et.hour >= 16:
            exit_r = ((close - entry) / risk) if direction == 1 else ((entry - close) / risk)
            exit_reason = "HARD_FLAT_16ET"
            exit_idx = j
            break
        if j == min(len(frame), entry_idx + MAX_HOLD_BARS) - 1:
            exit_r = ((close - entry) / risk) if direction == 1 else ((entry - close) / risk)
            exit_idx = j
    gross_r = realized + remaining * exit_r
    cost_r = COST_PROXY_PTS / risk_points
    net_r = gross_r - cost_r
    return Trade(
        role=role,
        trade_date=str(trade_date),
        direction=direction,
        entry_time_utc=frame.loc[entry_idx, "time_utc"].isoformat(),
        entry=entry,
        stop=stop,
        risk_points=risk_points,
        exit_time_utc=frame.loc[exit_idx, "time_utc"].isoformat(),
        gross_r=gross_r,
        cost_r=cost_r,
        net_r=net_r,
        exit_reason=exit_reason,
    )


def evaluate(frame: pd.DataFrame, point: float) -> tuple[list[Trade], list[Trade], dict[str, int]]:
    highs = frame["high"].to_numpy(float)
    lows = frame["low"].to_numpy(float)
    opens = frame["open"].to_numpy(float)
    closes = frame["close"].to_numpy(float)
    atr = frame["atr"].to_numpy(float)
    control: list[Trade] = []
    challenger: list[Trade] = []
    counts = {"days_total": 0, "range_ok": 0, "sweeps": 0, "displacements": 0, "fvgs": 0, "retests": 0}
    frame = frame.copy()
    frame["trade_date"] = frame["time_et"].map(trade_date_for)
    for trade_date, day in frame.groupby("trade_date", sort=True):
        counts["days_total"] += 1
        day_indices = day.index.to_numpy()
        asia = day.loc[(day["time_et"].dt.hour >= 20) | (day["time_et"].dt.hour < 3)]
        if asia.empty:
            continue
        asia_high = float(asia["high"].max())
        asia_low = float(asia["low"].min())
        range_pts = (asia_high - asia_low) / point
        if not (ASIA_MIN_PTS <= range_pts <= ASIA_MAX_PTS):
            continue
        counts["range_ok"] += 1
        manipulation = day.loc[(day["time_et"].dt.hour >= 3) & (day["time_et"].dt.hour < 5)]
        control_done = False
        challenger_done = False
        for sweep_idx in manipulation.index:
            if not math.isfinite(atr[sweep_idx]) or atr[sweep_idx] / point < ATR_MIN_PTS:
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
            stop = sweep_extreme - SL_BUFFER_PTS * point if direction == 1 else sweep_extreme + SL_BUFFER_PTS * point
            if not control_done and sweep_idx + 1 in day_indices:
                trade = simulate_trade(frame, sweep_idx + 1, direction, stop, point, "control", trade_date)
                if trade is not None:
                    control.append(trade)
                    control_done = True
            pivot_idx = last_confirmed_pivot(highs if direction == 1 else lows, sweep_idx, SWING_STRENGTH, direction == 1)
            if pivot_idx is None:
                continue
            mss_level = highs[pivot_idx] if direction == 1 else lows[pivot_idx]
            for disp_idx in range(sweep_idx + 1, min(len(frame), sweep_idx + DISPLACEMENT_BARS + 1)):
                if frame.loc[disp_idx, "trade_date"] != trade_date:
                    break
                body = abs(closes[disp_idx] - opens[disp_idx])
                mss = closes[disp_idx] > mss_level if direction == 1 else closes[disp_idx] < mss_level
                if not (body >= DISPLACEMENT_ATR * atr[disp_idx] and mss):
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
                for retest_idx in range(disp_idx + 1, min(len(frame), disp_idx + RETEST_BARS + 1)):
                    if frame.loc[retest_idx, "trade_date"] != trade_date:
                        break
                    ts_et = frame.loc[retest_idx, "time_et"]
                    if not in_entry_window(ts_et):
                        continue
                    overlap = lows[retest_idx] <= fvg_high and highs[retest_idx] >= fvg_low
                    direction_close = closes[retest_idx] > opens[retest_idx] if direction == 1 else closes[retest_idx] < opens[retest_idx]
                    if not (overlap and direction_close):
                        continue
                    counts["retests"] += 1
                    if retest_idx + 1 < len(frame):
                        trade = simulate_trade(frame, retest_idx + 1, direction, stop, point, "challenger", trade_date)
                        if trade is not None:
                            challenger.append(trade)
                            challenger_done = True
                    break
                if challenger_done:
                    break
            if challenger_done and control_done:
                break
    return control, challenger, counts


def metrics(trades: list[Trade]) -> dict[str, Any]:
    values = np.array([trade.net_r for trade in trades], dtype=float)
    positives = values[values > 0]
    negatives = values[values < 0]
    pf_infinite = bool(len(positives) and not len(negatives))
    pf = float(positives.sum() / abs(negatives.sum())) if len(negatives) else None
    equity = np.cumsum(values) if len(values) else np.array([], dtype=float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdowns_r = peaks[1:] - equity if len(equity) else np.array([], dtype=float)
    by_year: dict[str, float] = {}
    for trade in trades:
        year = trade.entry_time_utc[:4]
        by_year[year] = by_year.get(year, 0.0) + trade.net_r
    return {
        "trades": len(trades),
        "trades_per_elapsed_week": len(trades) / ELAPSED_WEEKS,
        "gross_profit_r": float(positives.sum()) if len(positives) else 0.0,
        "gross_loss_r": float(negatives.sum()) if len(negatives) else 0.0,
        "profit_factor_cost_proxy": pf,
        "profit_factor_infinite": pf_infinite,
        "net_r": float(values.sum()) if len(values) else 0.0,
        "expectancy_r": float(values.mean()) if len(values) else 0.0,
        "max_drawdown_r": float(drawdowns_r.max()) if len(drawdowns_r) else 0.0,
        "max_drawdown_pct_at_0_25_risk": float(drawdowns_r.max() * RISK_PCT) if len(drawdowns_r) else 0.0,
        "positive_years": sum(1 for value in by_year.values() if value > 0),
        "by_year_net_r": by_year,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not SPEC.is_file() or not REPORT.is_file():
        raise SystemExit("probe spec or research report is missing")
    if not mt5.initialize(path=str(args.terminal), timeout=60_000):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None:
            raise RuntimeError(f"terminal_info unavailable: {mt5.last_error()}")
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"symbol_select {SYMBOL} failed: {mt5.last_error()}")
        symbol = mt5.symbol_info(SYMBOL)
        point = float(symbol.point) if symbol is not None and symbol.point > 0 else POINT_FALLBACK
        m5 = load_rates(mt5.TIMEFRAME_M5)
        h4 = load_rates(mt5.TIMEFRAME_H4)
        m5["time_et"] = m5["time_utc"].dt.tz_convert("America/New_York")
        m5["atr"] = wilder_atr(m5, ATR_PERIOD)
        bias = build_h4_bias(h4)
        m5 = pd.merge_asof(
            m5.sort_values("time_utc"),
            bias.sort_values("available_utc"),
            left_on="time_utc",
            right_on="available_utc",
            direction="backward",
        ).reset_index(drop=True)
        m5["h4_bias"] = m5["h4_bias"].fillna(0).astype(int)
        control, challenger, counts = evaluate(m5, point)
        control_metrics = metrics(control)
        challenger_metrics = metrics(challenger)
        control_pf = math.inf if control_metrics["profit_factor_infinite"] else float(control_metrics["profit_factor_cost_proxy"] or 0.0)
        challenger_pf = math.inf if challenger_metrics["profit_factor_infinite"] else float(challenger_metrics["profit_factor_cost_proxy"] or 0.0)
        if challenger_metrics["profit_factor_infinite"]:
            pf_margin = not control_metrics["profit_factor_infinite"]
        elif control_metrics["profit_factor_infinite"]:
            pf_margin = False
        else:
            pf_margin = challenger_pf >= control_pf + 0.20
        gates = {
            "cadence_min": challenger_metrics["trades_per_elapsed_week"] >= 2.0,
            "cadence_max": challenger_metrics["trades_per_elapsed_week"] <= 5.0,
            "pf": challenger_pf >= 1.5,
            "expectancy": challenger_metrics["expectancy_r"] >= 0.4,
            "drawdown": challenger_metrics["max_drawdown_pct_at_0_25_risk"] <= 5.0,
            "positive_years": challenger_metrics["positive_years"] >= 2,
            "net_positive_and_not_below_control": challenger_metrics["net_r"] > 0 and challenger_metrics["net_r"] >= control_metrics["net_r"],
            "pf_margin_over_control": pf_margin,
        }
        verdict = "CONTINUE_TO_PREREG" if all(gates.values()) else "KILL_AT_OFFLINE_PROBE"
        account_fingerprint = None
        if account is not None:
            safe_identity = f"{account.server}|{account.currency}|{account.leverage}"
            account_fingerprint = hashlib.sha256(safe_identity.encode("utf-8")).hexdigest().upper()
        result = {
            "schema_version": "po3_amd_offline_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "ea_name": EA_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "verdict": verdict,
            "promotion_eligible": False,
            "cost_status": "UNVERIFIED_REPORT_ASSUMPTION",
            "window": {"from": FROM_UTC.isoformat(), "to": TO_UTC.isoformat()},
            "symbol": SYMBOL,
            "point": point,
            "bars": {"m5": len(m5), "h4": len(h4)},
            "source_hashes": {
                "probe_spec_sha256": sha256_file(SPEC),
                "probe_script_sha256": sha256_file(Path(__file__)),
                "research_report_sha256": sha256_file(REPORT),
            },
            "terminal": {
                "build": terminal.build,
                "connected": terminal.connected,
                "data_path": terminal.data_path,
                "account_fingerprint": account_fingerprint,
            },
            "gate_counts": counts,
            "control": control_metrics,
            "challenger": challenger_metrics,
            "gates": gates,
            "trades": {
                "control": [asdict(item) for item in control],
                "challenger": [asdict(item) for item in challenger],
            },
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"verdict": verdict, "control": control_metrics, "challenger": challenger_metrics, "gates": gates}, indent=2, allow_nan=False))
        return 0 if verdict == "CONTINUE_TO_PREREG" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
