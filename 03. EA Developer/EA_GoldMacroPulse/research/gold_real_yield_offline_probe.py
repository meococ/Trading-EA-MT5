#!/usr/bin/env python3
"""Frozen causal real-yield shock probe versus matched XAU momentum control."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = HERE / "HYP-GMP-XAU-M15-REALYIELD-001_FROZEN_PREREG.md"
YIELD_DATA = HERE / "data/DFII10_2019_2024.csv"
HYPOTHESIS_ID = "HYP-GMP-XAU-M15-REALYIELD-001"
EA_NAME = "EA_GoldMacroPulse"
SYMBOL = "XAUUSD"
FROM_UTC = datetime(2022, 1, 1, tzinfo=timezone.utc)
TO_UTC = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
ATR_PERIOD = 14
YIELD_SHOCK_PERCENTAGE_POINTS = 0.05
ENTRY_HOUR_UTC = 14
ENTRY_MINUTE_UTC = 30
STOP_ATR_MULT = 1.5
TARGET_R = 1.5
MAX_HOLD_BARS = 26
COST_PROXY_POINTS = 82.0
RISK_PCT = 0.25
ELAPSED_WEEKS = (TO_UTC.date() - FROM_UTC.date()).days / 7.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_m15() -> pd.DataFrame:
    parts: list[np.ndarray] = []
    for year in range(2022, 2025):
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M15, start, end)
        if rates is None:
            raise RuntimeError(f"copy_rates_range failed: {mt5.last_error()}")
        if len(rates) > 1:
            parts.append(rates)
    if not parts:
        raise RuntimeError("no XAUUSD M15 bars")
    frame = pd.DataFrame(np.concatenate(parts))
    frame = frame.drop_duplicates(subset=["time"]).sort_values("time")
    frame["time_utc"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.loc[
        (frame["time_utc"] >= pd.Timestamp(FROM_UTC))
        & (frame["time_utc"] <= pd.Timestamp(TO_UTC))
    ].reset_index(drop=True)
    frame["utc_date"] = frame["time_utc"].dt.date
    return frame


def wilder_atr(frame: pd.DataFrame, period: int) -> np.ndarray:
    high = frame["high"].to_numpy(float)
    low = frame["low"].to_numpy(float)
    close = frame["close"].to_numpy(float)
    previous = np.r_[np.nan, close[:-1]]
    true_range = np.nanmax(
        np.vstack([high - low, np.abs(high - previous), np.abs(low - previous)]),
        axis=0,
    )
    return pd.Series(true_range).ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean().to_numpy()


def load_yield_shocks() -> pd.DataFrame:
    panel = pd.read_csv(YIELD_DATA)
    required = {"observation_date", "DFII10"}
    if not required.issubset(panel.columns):
        raise RuntimeError(f"yield panel missing columns: {sorted(required - set(panel.columns))}")
    panel["observation_date"] = pd.to_datetime(panel["observation_date"], errors="raise")
    panel["yield"] = pd.to_numeric(panel["DFII10"], errors="coerce")
    panel = panel.dropna(subset=["yield"]).sort_values("observation_date").reset_index(drop=True)
    panel["delta_yield"] = panel["yield"].diff()
    panel = panel.loc[panel["delta_yield"].abs() >= YIELD_SHOCK_PERCENTAGE_POINTS].copy()
    return panel


def entry_indices_by_date(frame: pd.DataFrame) -> dict[date, int]:
    selected = frame.loc[
        (frame["time_utc"].dt.hour == ENTRY_HOUR_UTC)
        & (frame["time_utc"].dt.minute == ENTRY_MINUTE_UTC)
    ]
    return {row.utc_date: int(index) for index, row in selected.iterrows()}


def bind_signals_to_next_trading_date(
    shocks: pd.DataFrame,
    entries: dict[date, int],
) -> list[dict[str, Any]]:
    trading_dates = sorted(entries)
    bound: dict[date, dict[str, Any]] = {}
    for row in shocks.itertuples(index=False):
        observation_date = row.observation_date.date()
        position = bisect.bisect_right(trading_dates, observation_date)
        if position >= len(trading_dates):
            continue
        signal_date = trading_dates[position]
        if signal_date < FROM_UTC.date() or signal_date > TO_UTC.date():
            continue
        bound[signal_date] = {
            "observation_date": observation_date,
            "signal_date": signal_date,
            "delta_yield": float(row.delta_yield),
            "entry_idx": entries[signal_date],
        }
    return [bound[key] for key in sorted(bound)]


@dataclass
class Trade:
    role: str
    signal_date: str
    observation_date: str
    direction: int
    delta_yield: float
    entry_time_utc: str
    exit_time_utc: str
    risk_points: float
    gross_r: float
    cost_r: float
    net_r: float
    exit_reason: str


def simulate_trade(
    frame: pd.DataFrame,
    atr: np.ndarray,
    signal: dict[str, Any],
    direction: int,
    point: float,
    role: str,
) -> Trade | None:
    entry_idx = int(signal["entry_idx"])
    if entry_idx < 97 or entry_idx >= len(frame) or not math.isfinite(atr[entry_idx - 1]):
        return None
    entry = float(frame.loc[entry_idx, "open"])
    risk_distance = STOP_ATR_MULT * float(atr[entry_idx - 1])
    if risk_distance <= point:
        return None
    stop = entry - direction * risk_distance
    target = entry + direction * TARGET_R * risk_distance
    exit_idx = entry_idx
    gross_r = 0.0
    exit_reason = "TIME"
    end = min(len(frame), entry_idx + MAX_HOLD_BARS)
    for index in range(entry_idx, end):
        high = float(frame.loc[index, "high"])
        low = float(frame.loc[index, "low"])
        stopped = low <= stop if direction == 1 else high >= stop
        targeted = high >= target if direction == 1 else low <= target
        if stopped:
            gross_r = -1.0
            exit_idx = index
            exit_reason = "STOP"
            break
        if targeted:
            gross_r = TARGET_R
            exit_idx = index
            exit_reason = "TARGET"
            break
        if index == end - 1:
            close = float(frame.loc[index, "close"])
            gross_r = direction * (close - entry) / risk_distance
            exit_idx = index
    risk_points = risk_distance / point
    cost_r = COST_PROXY_POINTS / risk_points
    return Trade(
        role=role,
        signal_date=str(signal["signal_date"]),
        observation_date=str(signal["observation_date"]),
        direction=direction,
        delta_yield=float(signal["delta_yield"]),
        entry_time_utc=frame.loc[entry_idx, "time_utc"].isoformat(),
        exit_time_utc=frame.loc[exit_idx, "time_utc"].isoformat(),
        risk_points=risk_points,
        gross_r=gross_r,
        cost_r=cost_r,
        net_r=gross_r - cost_r,
        exit_reason=exit_reason,
    )


def momentum_direction(frame: pd.DataFrame, entry_idx: int) -> int:
    previous_close = float(frame.loc[entry_idx - 1, "close"])
    day_ago_close = float(frame.loc[entry_idx - 97, "close"])
    if previous_close > day_ago_close:
        return 1
    if previous_close < day_ago_close:
        return -1
    return 0


def evaluate(
    frame: pd.DataFrame,
    atr: np.ndarray,
    signals: list[dict[str, Any]],
    point: float,
) -> tuple[list[Trade], list[Trade], dict[str, int]]:
    control: list[Trade] = []
    challenger: list[Trade] = []
    counts = {
        "eligible_yield_shocks": len(signals),
        "warmup_skipped": 0,
        "control_trades": 0,
        "challenger_trades": 0,
    }
    for signal in signals:
        entry_idx = int(signal["entry_idx"])
        if entry_idx < 97:
            counts["warmup_skipped"] += 1
            continue
        external_direction = -1 if signal["delta_yield"] > 0 else 1
        control_direction = momentum_direction(frame, entry_idx)
        if control_direction != 0:
            trade = simulate_trade(frame, atr, signal, control_direction, point, "control")
            if trade is not None:
                control.append(trade)
        trade = simulate_trade(frame, atr, signal, external_direction, point, "challenger")
        if trade is not None:
            challenger.append(trade)
    counts["control_trades"] = len(control)
    counts["challenger_trades"] = len(challenger)
    return control, challenger, counts


def metrics(trades: list[Trade]) -> dict[str, Any]:
    values = np.array([trade.net_r for trade in trades], dtype=float)
    positive = values[values > 0]
    negative = values[values < 0]
    pf_infinite = bool(len(positive) and not len(negative))
    pf = float(positive.sum() / abs(negative.sum())) if len(negative) else None
    equity = np.cumsum(values) if len(values) else np.array([], dtype=float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdown = peaks[1:] - equity if len(equity) else np.array([], dtype=float)
    by_year: dict[str, float] = {}
    for trade in trades:
        year = trade.entry_time_utc[:4]
        by_year[year] = by_year.get(year, 0.0) + trade.net_r
    return {
        "trades": len(trades),
        "trades_per_elapsed_week": len(trades) / ELAPSED_WEEKS,
        "profit_factor_cost_proxy": pf,
        "profit_factor_infinite": pf_infinite,
        "net_r": float(values.sum()) if len(values) else 0.0,
        "expectancy_r": float(values.mean()) if len(values) else 0.0,
        "max_drawdown_r": float(drawdown.max()) if len(drawdown) else 0.0,
        "max_drawdown_pct_at_0_25_risk": float(drawdown.max() * RISK_PCT) if len(drawdown) else 0.0,
        "positive_years": sum(1 for value in by_year.values() if value > 0),
        "by_year_net_r": by_year,
    }


def gate_metrics(control: dict[str, Any], challenger: dict[str, Any]) -> dict[str, bool]:
    control_pf = math.inf if control["profit_factor_infinite"] else float(control["profit_factor_cost_proxy"] or 0.0)
    challenger_pf = math.inf if challenger["profit_factor_infinite"] else float(challenger["profit_factor_cost_proxy"] or 0.0)
    if challenger["profit_factor_infinite"]:
        pf_margin = not control["profit_factor_infinite"]
    elif control["profit_factor_infinite"]:
        pf_margin = False
    else:
        pf_margin = challenger_pf >= control_pf + 0.10
    return {
        "cadence_min": challenger["trades_per_elapsed_week"] >= 2.0,
        "cadence_max": challenger["trades_per_elapsed_week"] <= 5.0,
        "pf": challenger_pf >= 1.35,
        "expectancy": challenger["expectancy_r"] >= 0.10,
        "drawdown": challenger["max_drawdown_pct_at_0_25_risk"] <= 8.0,
        "positive_years": challenger["positive_years"] >= 2,
        "net_positive_and_not_below_control": challenger["net_r"] > 0 and challenger["net_r"] >= control["net_r"],
        "pf_margin_over_control": pf_margin,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    for required in (PREREG, YIELD_DATA):
        if not required.is_file():
            raise SystemExit(f"frozen input missing: {required}")
    if not mt5.initialize(path=str(args.terminal), timeout=60_000, portable=True):
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None:
            raise RuntimeError(f"terminal_info unavailable: {mt5.last_error()}")
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"symbol_select {SYMBOL} failed: {mt5.last_error()}")
        symbol = mt5.symbol_info(SYMBOL)
        if symbol is None or symbol.point <= 0:
            raise RuntimeError("XAUUSD point geometry unavailable")
        frame = load_m15()
        atr = wilder_atr(frame, ATR_PERIOD)
        entries = entry_indices_by_date(frame)
        shocks = load_yield_shocks()
        signals = bind_signals_to_next_trading_date(shocks, entries)
        control_trades, challenger_trades, counts = evaluate(frame, atr, signals, float(symbol.point))
        control = metrics(control_trades)
        challenger = metrics(challenger_trades)
        gates = gate_metrics(control, challenger)
        verdict = "CONTINUE_TO_EA_BUILD" if all(gates.values()) else "KILL_AT_OFFLINE_PROBE"
        account_fingerprint = None
        if account is not None:
            identity = f"{account.server}|{account.currency}|{account.leverage}"
            account_fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest().upper()
        result = {
            "schema_version": "gold_macro_real_yield_probe.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "ea_name": EA_NAME,
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "verdict": verdict,
            "promotion_eligible": False,
            "cost_status": "UNVERIFIED_P99_SPREAD_ONLY_NO_COMMISSION_SLIPPAGE",
            "window": {"from": FROM_UTC.isoformat(), "to": TO_UTC.isoformat()},
            "symbol": SYMBOL,
            "point": float(symbol.point),
            "bars": {"m15": len(frame), "entry_dates": len(entries)},
            "source_hashes": {
                "prereg_sha256": sha256_file(PREREG),
                "probe_script_sha256": sha256_file(Path(__file__)),
                "dfii10_train_sha256": sha256_file(YIELD_DATA),
            },
            "source_urls": {
                "dfii10": "https://fred.stlouisfed.org/series/DFII10",
                "h15_schedule": "https://www.federalreserve.gov/releases/h15/",
                "chicago_fed_rationale": "https://www.chicagofed.org/publications/chicago-fed-letter/2021/464",
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
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"verdict": verdict, "counts": counts, "control": control, "challenger": challenger, "gates": gates}, indent=2, allow_nan=False))
        return 0 if verdict == "CONTINUE_TO_EA_BUILD" else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
