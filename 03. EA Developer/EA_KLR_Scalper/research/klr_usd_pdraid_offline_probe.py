#!/usr/bin/env python3
"""Frozen KLR USD-gated prior-day liquidity-raid probe.

This is a one-shot closed-bar research screen for
HYP-KLR-USD-PDLRAID-M5-XAU-001. It is not Strategy Tester evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = HERE / "HYP-KLR-USD-PDLRAID-M5-XAU-001_FROZEN_PREREG.md"
USD_DATA = HERE / "data/DTWEXBGS.csv"
REPORT = ROOT / "05. Playbook/Strategy/KLR_Scalper_Deep_Research_Report.md"
HYPOTHESIS_ID = "HYP-KLR-USD-PDLRAID-M5-XAU-001"
EA_NAME = "EA_KLR_Scalper"
SYMBOL = "XAUUSD"
FROM_UTC = datetime(2022, 1, 1, tzinfo=timezone.utc)
TO_UTC = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
ELAPSED_WEEKS = (TO_UTC.date() - FROM_UTC.date()).days / 7.0

ATR_PERIOD = 14
PIVOT_STRENGTH = 2
DISPLACEMENT_ATR = 1.0
DISPLACEMENT_BARS = 4
RETEST_BARS = 6
STOP_ATR_BUFFER = 0.10
TARGET_R = 2.0
MAX_HOLD_BARS = 12
RISK_PCT = 0.25
COST_POINTS = 35.0
LONDON = (120, 300)
NEW_YORK = (510, 660)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def path_drive(path: str) -> str:
    return os.path.splitdrive(os.path.abspath(path))[0].upper()


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
    mask = (frame["time_utc"] >= pd.Timestamp(FROM_UTC)) & (
        frame["time_utc"] <= pd.Timestamp(TO_UTC)
    )
    return frame.loc[mask].reset_index(drop=True)


def wilder_atr(frame: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    close = frame["close"].to_numpy(float)
    previous = np.r_[np.nan, close[:-1]]
    true_range = np.nanmax(
        np.vstack([high - low, np.abs(high - previous), np.abs(low - previous)]), axis=0
    )
    return (
        pd.Series(true_range)
        .ewm(alpha=1.0 / period, adjust=False, min_periods=period)
        .mean()
        .to_numpy()
    )


def confirmed_pivots(values: np.ndarray, strength: int, high: bool) -> set[int]:
    result: set[int] = set()
    for index in range(strength, len(values) - strength):
        left = values[index - strength : index]
        right = values[index + 1 : index + strength + 1]
        if high and values[index] > float(np.max(left)) and values[index] > float(np.max(right)):
            result.add(index)
        if not high and values[index] < float(np.min(left)) and values[index] < float(np.min(right)):
            result.add(index)
    return result


def build_m15_bias(frame: pd.DataFrame) -> pd.DataFrame:
    highs = frame["high"].to_numpy(float)
    lows = frame["low"].to_numpy(float)
    high_pivots = confirmed_pivots(highs, PIVOT_STRENGTH, True)
    low_pivots = confirmed_pivots(lows, PIVOT_STRENGTH, False)
    known_highs: list[int] = []
    known_lows: list[int] = []
    rows: list[dict[str, Any]] = []
    for closed_index in range(len(frame)):
        newly_confirmed = closed_index - PIVOT_STRENGTH
        if newly_confirmed in high_pivots:
            known_highs.append(newly_confirmed)
        if newly_confirmed in low_pivots:
            known_lows.append(newly_confirmed)
        bias = 0
        if len(known_highs) >= 2 and len(known_lows) >= 2:
            h0, h1 = known_highs[-2:]
            l0, l1 = known_lows[-2:]
            if highs[h1] > highs[h0] and lows[l1] > lows[l0]:
                bias = 1
            elif highs[h1] < highs[h0] and lows[l1] < lows[l0]:
                bias = -1
        rows.append(
            {
                "available_utc": frame.loc[closed_index, "time_utc"] + pd.Timedelta(minutes=15),
                "m15_bias": bias,
            }
        )
    return pd.DataFrame(rows)


def load_usd_changes(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    if list(data.columns) != ["observation_date", "DTWEXBGS"]:
        raise ValueError(f"unexpected USD CSV columns: {list(data.columns)}")
    data["observation_date"] = pd.to_datetime(data["observation_date"], errors="raise")
    data["DTWEXBGS"] = pd.to_numeric(data["DTWEXBGS"], errors="coerce")
    data = data.dropna().sort_values("observation_date").reset_index(drop=True)
    data["usd_change"] = data["DTWEXBGS"].diff()
    return data.dropna(subset=["usd_change"])


def usd_change_for_trade_date(data: pd.DataFrame, trade_date: Any) -> float:
    cutoff = pd.Timestamp(trade_date) - BDay(2)
    eligible = data.loc[data["observation_date"] <= cutoff]
    if eligible.empty:
        return math.nan
    return float(eligible.iloc[-1]["usd_change"])


def eligible_window(ts_et: pd.Timestamp) -> tuple[int, int] | None:
    minute = ts_et.hour * 60 + ts_et.minute
    for start, end in (LONDON, NEW_YORK):
        if start <= minute < end:
            return start, end
    return None


def previous_day_levels(frame: pd.DataFrame) -> dict[Any, tuple[float, float]]:
    daily = (
        frame.groupby("et_date", sort=True)
        .agg(day_high=("high", "max"), day_low=("low", "min"))
        .reset_index()
    )
    result: dict[Any, tuple[float, float]] = {}
    previous: tuple[float, float] | None = None
    for row in daily.itertuples(index=False):
        if previous is not None:
            result[row.et_date] = previous
        previous = (float(row.day_high), float(row.day_low))
    return result


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
    exit_reason: str


def simulate_trade(
    frame: pd.DataFrame,
    entry_index: int,
    direction: int,
    stop: float,
    point: float,
    role: str,
    trade_date: Any,
    window_end: int,
) -> Trade | None:
    if entry_index >= len(frame) or frame.loc[entry_index, "et_date"] != trade_date:
        return None
    entry = float(frame.loc[entry_index, "open"])
    risk = entry - stop if direction == 1 else stop - entry
    if risk <= max(point, 1e-12):
        return None
    exit_index = entry_index
    exit_r = 0.0
    exit_reason = "MAX_HOLD"
    for index in range(entry_index, min(len(frame), entry_index + MAX_HOLD_BARS)):
        if frame.loc[index, "et_date"] != trade_date:
            exit_reason = "DAY_FLAT"
            break
        high = float(frame.loc[index, "high"])
        low = float(frame.loc[index, "low"])
        close = float(frame.loc[index, "close"])
        stopped = low <= stop if direction == 1 else high >= stop
        target = entry + TARGET_R * risk if direction == 1 else entry - TARGET_R * risk
        targeted = high >= target if direction == 1 else low <= target
        exit_index = index
        if stopped:
            exit_r = -1.0
            exit_reason = "STOP"
            break
        if targeted:
            exit_r = TARGET_R
            exit_reason = "TARGET"
            break
        close_minute = frame.loc[index, "time_et"].hour * 60 + frame.loc[index, "time_et"].minute + 5
        if close_minute >= window_end:
            exit_r = (close - entry) / risk if direction == 1 else (entry - close) / risk
            exit_reason = "SESSION_FLAT"
            break
        if index == min(len(frame), entry_index + MAX_HOLD_BARS) - 1:
            exit_r = (close - entry) / risk if direction == 1 else (entry - close) / risk
    return Trade(
        role=role,
        trade_date=str(trade_date),
        direction=direction,
        entry_time_utc=frame.loc[entry_index, "time_utc"].isoformat(),
        entry=entry,
        stop=stop,
        risk_points=risk / point,
        exit_time_utc=frame.loc[exit_index, "time_utc"].isoformat(),
        gross_r=float(exit_r),
        exit_reason=exit_reason,
    )


def evaluate(
    frame: pd.DataFrame, usd_data: pd.DataFrame, point: float
) -> tuple[list[Trade], list[Trade], list[Trade], dict[str, int]]:
    highs = frame["high"].to_numpy(float)
    lows = frame["low"].to_numpy(float)
    opens = frame["open"].to_numpy(float)
    closes = frame["close"].to_numpy(float)
    atr = frame["atr"].to_numpy(float)
    levels = previous_day_levels(frame)
    sweep_control: list[Trade] = []
    core_control: list[Trade] = []
    challenger: list[Trade] = []
    counts = {
        "days_total": 0,
        "days_with_prior_levels": 0,
        "days_with_usd": 0,
        "sweeps": 0,
        "displacements": 0,
        "fvgs": 0,
        "retests": 0,
        "usd_aligned_retests": 0,
    }
    for trade_date, day in frame.groupby("et_date", sort=True):
        counts["days_total"] += 1
        if trade_date not in levels:
            continue
        counts["days_with_prior_levels"] += 1
        usd_change = usd_change_for_trade_date(usd_data, trade_date)
        if math.isfinite(usd_change) and usd_change != 0:
            counts["days_with_usd"] += 1
        prior_high, prior_low = levels[trade_date]
        sweep_done = False
        core_done = False
        challenger_done = False
        day_index_set = set(day.index.to_numpy())
        for sweep_index in day.index:
            window = eligible_window(frame.loc[sweep_index, "time_et"])
            if window is None or not math.isfinite(atr[sweep_index]):
                continue
            bias = int(frame.loc[sweep_index, "m15_bias"])
            direction = 0
            if bias == 1 and lows[sweep_index] < prior_low and closes[sweep_index] > prior_low:
                direction = 1
            elif bias == -1 and highs[sweep_index] > prior_high and closes[sweep_index] < prior_high:
                direction = -1
            if direction == 0:
                continue
            counts["sweeps"] += 1
            sweep_extreme = lows[sweep_index] if direction == 1 else highs[sweep_index]
            stop = (
                sweep_extreme - STOP_ATR_BUFFER * atr[sweep_index]
                if direction == 1
                else sweep_extreme + STOP_ATR_BUFFER * atr[sweep_index]
            )
            if not sweep_done and sweep_index + 1 in day_index_set:
                trade = simulate_trade(
                    frame,
                    sweep_index + 1,
                    direction,
                    stop,
                    point,
                    "control_sweep",
                    trade_date,
                    window[1],
                )
                if trade is not None:
                    sweep_control.append(trade)
                    sweep_done = True
            for displacement_index in range(
                sweep_index + 1, min(len(frame), sweep_index + DISPLACEMENT_BARS + 1)
            ):
                if frame.loc[displacement_index, "et_date"] != trade_date:
                    break
                displacement_window = eligible_window(frame.loc[displacement_index, "time_et"])
                if displacement_window != window or not math.isfinite(atr[displacement_index]):
                    continue
                body = abs(closes[displacement_index] - opens[displacement_index])
                mss = (
                    closes[displacement_index] > highs[sweep_index]
                    if direction == 1
                    else closes[displacement_index] < lows[sweep_index]
                )
                if body < DISPLACEMENT_ATR * atr[displacement_index] or not mss:
                    continue
                counts["displacements"] += 1
                if displacement_index < 2:
                    continue
                if direction == 1 and lows[displacement_index] > highs[displacement_index - 2]:
                    fvg_low, fvg_high = highs[displacement_index - 2], lows[displacement_index]
                elif direction == -1 and highs[displacement_index] < lows[displacement_index - 2]:
                    fvg_low, fvg_high = highs[displacement_index], lows[displacement_index - 2]
                else:
                    continue
                counts["fvgs"] += 1
                for retest_index in range(
                    displacement_index + 1, min(len(frame), displacement_index + RETEST_BARS + 1)
                ):
                    if frame.loc[retest_index, "et_date"] != trade_date:
                        break
                    if eligible_window(frame.loc[retest_index, "time_et"]) != window:
                        continue
                    overlap = lows[retest_index] <= fvg_high and highs[retest_index] >= fvg_low
                    direction_close = (
                        closes[retest_index] > opens[retest_index]
                        if direction == 1
                        else closes[retest_index] < opens[retest_index]
                    )
                    if not overlap or not direction_close:
                        continue
                    counts["retests"] += 1
                    entry_index = retest_index + 1
                    if not core_done:
                        trade = simulate_trade(
                            frame,
                            entry_index,
                            direction,
                            stop,
                            point,
                            "control_core",
                            trade_date,
                            window[1],
                        )
                        if trade is not None:
                            core_control.append(trade)
                            core_done = True
                    usd_aligned = (direction == 1 and usd_change < 0) or (
                        direction == -1 and usd_change > 0
                    )
                    if usd_aligned and not challenger_done:
                        counts["usd_aligned_retests"] += 1
                        trade = simulate_trade(
                            frame,
                            entry_index,
                            direction,
                            stop,
                            point,
                            "challenger",
                            trade_date,
                            window[1],
                        )
                        if trade is not None:
                            challenger.append(trade)
                            challenger_done = True
                    break
                if core_done and (challenger_done or not math.isfinite(usd_change)):
                    break
            if sweep_done and core_done and challenger_done:
                break
    return sweep_control, core_control, challenger, counts


def metrics(trades: list[Trade], cost_multiplier: float) -> dict[str, Any]:
    values = np.array(
        [trade.gross_r - cost_multiplier * COST_POINTS / trade.risk_points for trade in trades],
        dtype=float,
    )
    wins = values[values > 0]
    losses = values[values < 0]
    infinite_pf = bool(len(wins) and not len(losses))
    profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) else None
    equity = np.cumsum(values) if len(values) else np.array([], dtype=float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdown = peaks[1:] - equity if len(equity) else np.array([], dtype=float)
    by_year: dict[str, float] = {}
    for trade, value in zip(trades, values, strict=True):
        year = trade.entry_time_utc[:4]
        by_year[year] = by_year.get(year, 0.0) + float(value)
    return {
        "trades": len(trades),
        "trades_per_elapsed_week": len(trades) / ELAPSED_WEEKS,
        "cost_multiplier": cost_multiplier,
        "profit_factor": profit_factor,
        "profit_factor_infinite": infinite_pf,
        "net_r": float(values.sum()) if len(values) else 0.0,
        "expectancy_r": float(values.mean()) if len(values) else 0.0,
        "max_drawdown_r": float(drawdown.max()) if len(drawdown) else 0.0,
        "max_drawdown_pct_at_0_25_risk": float(drawdown.max() * RISK_PCT) if len(drawdown) else 0.0,
        "positive_years": sum(value > 0 for value in by_year.values()),
        "by_year_net_r": by_year,
    }


def finite_pf(result: dict[str, Any]) -> float:
    if result["profit_factor_infinite"]:
        return math.inf
    return float(result["profit_factor"] or 0.0)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--required-drive", default="D:")
    args = parser.parse_args()

    for required in (PREREG, USD_DATA, REPORT):
        if not required.is_file():
            raise SystemExit(f"missing frozen input: {required}")
    required_drive = args.required_drive.rstrip("\\/").upper()
    terminal_path = args.terminal.resolve()
    if path_drive(str(terminal_path)) != required_drive:
        raise SystemExit(f"terminal must be on {required_drive}: {terminal_path}")

    if not mt5.initialize(path=str(terminal_path), timeout=60_000, portable=True):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None:
            raise RuntimeError(f"terminal_info unavailable: {mt5.last_error()}")
        if path_drive(str(terminal.data_path)) != required_drive:
            raise RuntimeError(f"MT5 data_path is not on {required_drive}: {terminal.data_path}")
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"symbol_select failed: {mt5.last_error()}")
        symbol = mt5.symbol_info(SYMBOL)
        if symbol is None or symbol.point <= 0:
            raise RuntimeError("XAUUSD symbol geometry unavailable")
        point = float(symbol.point)
        m5 = load_rates(mt5.TIMEFRAME_M5)
        m15 = load_rates(mt5.TIMEFRAME_M15)
        m5["time_et"] = m5["time_utc"].dt.tz_convert("America/New_York")
        m5["et_date"] = m5["time_et"].dt.date
        m5["atr"] = wilder_atr(m5)
        bias = build_m15_bias(m15)
        m5["closed_utc"] = m5["time_utc"] + pd.Timedelta(minutes=5)
        m5 = pd.merge_asof(
            m5.sort_values("closed_utc"),
            bias.sort_values("available_utc"),
            left_on="closed_utc",
            right_on="available_utc",
            direction="backward",
        ).reset_index(drop=True)
        m5["m15_bias"] = m5["m15_bias"].fillna(0).astype(int)
        usd_data = load_usd_changes(USD_DATA)
        sweep, core, challenger, counts = evaluate(m5, usd_data, point)
        sweep_x1 = metrics(sweep, 1.0)
        core_x1 = metrics(core, 1.0)
        challenger_x1 = metrics(challenger, 1.0)
        challenger_x15 = metrics(challenger, 1.5)
        challenger_x2 = metrics(challenger, 2.0)
        challenger_pf = finite_pf(challenger_x1)
        core_pf = finite_pf(core_x1)
        pf_advantage = (
            (not math.isinf(core_pf)) if math.isinf(challenger_pf) else challenger_pf >= core_pf + 0.15
        )
        retention = len(challenger) / len(core) if core else 0.0
        gates = {
            "cadence_min": challenger_x1["trades_per_elapsed_week"] >= 2.0,
            "cadence_max": challenger_x1["trades_per_elapsed_week"] <= 5.0,
            "pf_x1": challenger_pf >= 1.30,
            "pf_x1_5": finite_pf(challenger_x15) >= 1.25,
            "pf_x2": finite_pf(challenger_x2) >= 1.00,
            "expectancy_positive": challenger_x1["expectancy_r"] > 0.0,
            "drawdown": challenger_x1["max_drawdown_pct_at_0_25_risk"] <= 5.0,
            "positive_years": challenger_x1["positive_years"] >= 2,
            "net_not_below_core": challenger_x1["net_r"] > 0
            and challenger_x1["net_r"] >= core_x1["net_r"],
            "pf_advantage_over_core": pf_advantage,
            "core_trade_retention": retention >= 0.50,
        }
        verdict = "CONTINUE_TO_EA_BUILD" if all(gates.values()) else "KILL_AT_OFFLINE_PROBE"
        payload = {
            "schema_version": "klr_usd_pdraid_offline_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "ea_name": EA_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "verdict": verdict,
            "promotion_eligible": False,
            "window": {"from": FROM_UTC.isoformat(), "to": TO_UTC.isoformat()},
            "symbol": SYMBOL,
            "point": point,
            "bars": {"m5": len(m5), "m15": len(m15)},
            "source_hashes": {
                "prereg_sha256": sha256_file(PREREG),
                "probe_script_sha256": sha256_file(Path(__file__)),
                "research_report_sha256": sha256_file(REPORT),
                "dtwexbgs_sha256": sha256_file(USD_DATA),
            },
            "storage": {
                "terminal": str(terminal_path),
                "data_path": str(terminal.data_path),
                "commondata_path": str(terminal.commondata_path),
                "required_drive": required_drive,
                "file_common_allowed": False,
                "passed": path_drive(str(terminal.data_path)) == required_drive,
            },
            "cost_status": "UNVERIFIED_35_POINT_PROXY",
            "gate_counts": counts,
            "controls": {"sweep_x1": sweep_x1, "core_x1": core_x1},
            "challenger": {"x1": challenger_x1, "x1_5": challenger_x15, "x2": challenger_x2},
            "comparison": {"pf_advantage": pf_advantage, "core_trade_retention": retention},
            "gates": gates,
            "trades": {
                "control_sweep": [asdict(item) for item in sweep],
                "control_core": [asdict(item) for item in core],
                "challenger": [asdict(item) for item in challenger],
            },
        }
        atomic_json(args.out.resolve(), payload)
        print(
            json.dumps(
                {
                    "verdict": verdict,
                    "counts": counts,
                    "core": core_x1,
                    "challenger": payload["challenger"],
                    "gates": gates,
                },
                indent=2,
                ensure_ascii=True,
                allow_nan=False,
            )
        )
        return 0 if verdict == "CONTINUE_TO_EA_BUILD" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
