"""Closed-bar, no-outcome LSS-OB M15 detector engine.

This module may emit decision-time setup identities and funnel counts only. It
must never calculate a forward result, fill result, stop/target outcome, PnL,
MFE, MAE, win rate, expectancy, drawdown, or profit factor.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

WORKSPACE = Path(__file__).resolve().parents[3]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from indicators import adx_mt5, atr_mt5  # noqa: E402


CONTRACT_ID = "lss_ob_m15_fidelity_density.v1"
PIP_SIZE = 0.0001


@dataclass(frozen=True)
class FrozenSpec:
    pivot_strength: int = 2
    sweep_lookback: int = 20
    displacement_bars: int = 3
    displacement_atr_multiple: float = 1.8
    atr_period: int = 14
    adx_period: int = 14
    min_adx: float = 25.0
    retest_bars: int = 12
    confirmation_body_ratio: float = 0.60
    confirmation_outer_fraction: float = 0.25
    news_blackout_minutes: int = 30
    stop_buffer_pips: float = 1.5
    min_stop_pips: float = 8.0
    max_stop_pips: float = 12.0


@dataclass
class SetupState:
    direction: int
    session_id: int
    pivot_time: pd.Timestamp
    sweep_idx: int
    sweep_time: pd.Timestamp
    sweep_extreme: float
    displacement_idx: int | None = None
    displacement_time: pd.Timestamp | None = None
    ob_idx: int | None = None
    ob_time: pd.Timestamp | None = None
    ob_low: float | None = None
    ob_high: float | None = None
    overlap_low: float | None = None
    overlap_high: float | None = None


class NewsGuard:
    def __init__(self, event_times: Iterable[pd.Timestamp], blackout_minutes: int) -> None:
        times = pd.to_datetime(list(event_times), utc=True).tz_convert(None)
        self._epochs = np.sort(times.astype("int64").to_numpy())
        self._radius_ns = int(pd.Timedelta(minutes=blackout_minutes).value)

    def blocked(self, decision_time: pd.Timestamp) -> bool:
        if not len(self._epochs):
            return False
        value = int(pd.Timestamp(decision_time).value)
        left = int(np.searchsorted(self._epochs, value - self._radius_ns, side="left"))
        return left < len(self._epochs) and int(self._epochs[left]) <= value + self._radius_ns


def resample_ohlc(m1: pd.DataFrame, rule: str) -> pd.DataFrame:
    required = {"time_utc", "open", "high", "low", "close", "tick_volume"}
    missing = required - set(m1.columns)
    if missing:
        raise ValueError(f"missing M1 columns: {sorted(missing)}")
    src = m1.loc[:, sorted(required)].copy()
    src["time_utc"] = pd.to_datetime(src["time_utc"])
    src = src.sort_values("time_utc").drop_duplicates("time_utc", keep=False)
    indexed = src.set_index("time_utc")
    out = indexed.resample(rule, closed="left", label="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        m1_count=("close", "count"),
    )
    out = out.dropna(subset=["open", "high", "low", "close"]).reset_index()
    minutes = int(pd.Timedelta(rule).total_seconds() // 60)
    out["decision_time_utc"] = out["time_utc"] + pd.Timedelta(minutes=minutes)
    return out


def confirmed_pivot_frame(bars: pd.DataFrame, strength: int) -> pd.DataFrame:
    if strength < 1:
        raise ValueError("pivot strength must be positive")
    n = len(bars)
    highs = bars["high"].to_numpy(float)
    lows = bars["low"].to_numpy(float)
    last_high = np.full(n, np.nan)
    last_low = np.full(n, np.nan)
    high_idx = np.full(n, -1, dtype=int)
    low_idx = np.full(n, -1, dtype=int)
    current_high = np.nan
    current_low = np.nan
    current_high_idx = -1
    current_low_idx = -1
    for confirmation_idx in range(n):
        pivot_idx = confirmation_idx - strength
        if pivot_idx >= strength:
            left = slice(pivot_idx - strength, pivot_idx)
            right = slice(pivot_idx + 1, confirmation_idx + 1)
            if highs[pivot_idx] > np.max(highs[left]) and highs[pivot_idx] > np.max(highs[right]):
                current_high = float(highs[pivot_idx])
                current_high_idx = pivot_idx
            if lows[pivot_idx] < np.min(lows[left]) and lows[pivot_idx] < np.min(lows[right]):
                current_low = float(lows[pivot_idx])
                current_low_idx = pivot_idx
        last_high[confirmation_idx] = current_high
        last_low[confirmation_idx] = current_low
        high_idx[confirmation_idx] = current_high_idx
        low_idx[confirmation_idx] = current_low_idx
    return pd.DataFrame(
        {
            "pivot_high": last_high,
            "pivot_low": last_low,
            "pivot_high_idx": high_idx,
            "pivot_low_idx": low_idx,
        },
        index=bars.index,
    )


def _htf_context(bars: pd.DataFrame, strength: int, include_bias: bool) -> pd.DataFrame:
    pivots = confirmed_pivot_frame(bars, strength)
    out = bars[["decision_time_utc", "close"]].copy()
    out = pd.concat([out, pivots], axis=1)
    if include_bias:
        bias = np.zeros(len(out), dtype=int)
        current = 0
        for i in range(len(out)):
            high = out.at[i, "pivot_high"]
            low = out.at[i, "pivot_low"]
            close = float(out.at[i, "close"])
            if np.isfinite(high) and close > high:
                current = 1
            elif np.isfinite(low) and close < low:
                current = -1
            bias[i] = current
        out["h1_bias"] = bias
    return out


def attach_context(m15: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame, spec: FrozenSpec) -> pd.DataFrame:
    base = m15.sort_values("decision_time_utc").reset_index(drop=True).copy()
    h1c = _htf_context(h1.reset_index(drop=True), spec.pivot_strength, True)[
        ["decision_time_utc", "h1_bias"]
    ]
    h4c = _htf_context(h4.reset_index(drop=True), spec.pivot_strength, False)[
        ["decision_time_utc", "pivot_low", "pivot_high"]
    ].rename(columns={"pivot_low": "h4_low", "pivot_high": "h4_high"})
    base = pd.merge_asof(base, h1c, on="decision_time_utc", direction="backward")
    base = pd.merge_asof(base, h4c, on="decision_time_utc", direction="backward")
    base["atr_mt5"] = atr_mt5(base, spec.atr_period)
    base["adx_mt5"] = adx_mt5(base, spec.adx_period)
    return base


def session_id(bar_open_utc: pd.Timestamp) -> int:
    ts = pd.Timestamp(bar_open_utc)
    minute = ts.hour * 60 + ts.minute
    if 7 * 60 <= minute < 10 * 60:
        return 1
    if 13 * 60 <= minute < 16 * 60:
        return 2
    return 0


def context_aligned(row: pd.Series, direction: int) -> bool:
    bias = int(row.get("h1_bias", 0) or 0)
    low = float(row.get("h4_low", np.nan))
    high = float(row.get("h4_high", np.nan))
    price = float(row["close"])
    if bias != direction or not (np.isfinite(low) and np.isfinite(high) and low < high):
        return False
    if not (low <= price <= high):
        return False
    midpoint = (low + high) / 2.0
    return price <= midpoint if direction > 0 else price >= midpoint


def strict_fvg(bars: pd.DataFrame, index: int, direction: int) -> tuple[float, float] | None:
    if index < 2:
        return None
    if direction > 0 and float(bars.at[index, "low"]) > float(bars.at[index - 2, "high"]):
        return float(bars.at[index - 2, "high"]), float(bars.at[index, "low"])
    if direction < 0 and float(bars.at[index, "high"]) < float(bars.at[index - 2, "low"]):
        return float(bars.at[index, "high"]), float(bars.at[index - 2, "low"])
    return None


def find_order_block(
    bars: pd.DataFrame, start_index: int, displacement_index: int, direction: int
) -> tuple[int, float, float, float, float] | None:
    for index in range(displacement_index - 1, start_index - 1, -1):
        open_ = float(bars.at[index, "open"])
        close = float(bars.at[index, "close"])
        opposite = close < open_ if direction > 0 else close > open_
        if not opposite:
            continue
        wick_low = float(bars.at[index, "low"])
        wick_high = float(bars.at[index, "high"])
        intermediate = bars.iloc[index + 1 : displacement_index]
        if direction > 0 and len(intermediate) and (intermediate["close"] < wick_low).any():
            continue
        if direction < 0 and len(intermediate) and (intermediate["close"] > wick_high).any():
            continue
        return index, min(open_, close), max(open_, close), wick_low, wick_high
    return None


def is_confirmation(bars: pd.DataFrame, index: int, direction: int, spec: FrozenSpec) -> bool:
    if index < 1:
        return False
    row = bars.iloc[index]
    prev = bars.iloc[index - 1]
    open_, close = float(row.open), float(row.close)
    prev_open, prev_close = float(prev.open), float(prev.close)
    range_ = float(row.high - row.low)
    if range_ <= 0:
        return False
    engulf = (
        close > open_ and open_ <= prev_close and close >= prev_open
        if direction > 0
        else close < open_ and open_ >= prev_close and close <= prev_open
    )
    body_ratio = abs(close - open_) / range_
    outer = (
        close >= float(row.low) + (1.0 - spec.confirmation_outer_fraction) * range_
        if direction > 0
        else close <= float(row.low) + spec.confirmation_outer_fraction * range_
    )
    directional = close > open_ if direction > 0 else close < open_
    return bool(engulf or (directional and body_ratio >= spec.confirmation_body_ratio and outer))


def _first_quote(m1: pd.DataFrame, decision_time: pd.Timestamp) -> float | None:
    times = pd.to_datetime(m1["time_utc"]).to_numpy(dtype="datetime64[ns]")
    idx = int(np.searchsorted(times, np.datetime64(pd.Timestamp(decision_time)), side="left"))
    if idx >= len(m1):
        return None
    return float(m1.iloc[idx]["open"])


def _risk_geometry(
    m1: pd.DataFrame, row: pd.Series, state: SetupState, direction: int, spec: FrozenSpec
) -> tuple[float, float, float] | None:
    entry = _first_quote(m1, pd.Timestamp(row["decision_time_utc"]))
    if entry is None or state.ob_low is None or state.ob_high is None:
        return None
    buffer = spec.stop_buffer_pips * PIP_SIZE
    if direction > 0:
        stop = min(state.sweep_extreme, state.ob_low) - buffer
        distance = (entry - stop) / PIP_SIZE
    else:
        stop = max(state.sweep_extreme, state.ob_high) + buffer
        distance = (stop - entry) / PIP_SIZE
    if not (spec.min_stop_pips <= distance <= spec.max_stop_pips):
        return None
    return entry, stop, float(distance)


def _event_id(arm: str, direction: int, state: SetupState, decision_time: pd.Timestamp) -> str:
    key = "|".join(
        [
            CONTRACT_ID,
            arm,
            "EURUSD",
            "M15",
            "long" if direction > 0 else "short",
            state.pivot_time.isoformat(),
            state.sweep_time.isoformat(),
            str(state.displacement_time.isoformat() if state.displacement_time is not None else ""),
            str(state.ob_time.isoformat() if state.ob_time is not None else ""),
            pd.Timestamp(decision_time).isoformat(),
        ]
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24].upper()
    return f"LSSOB-M15-V1-{digest}"


def _make_event(
    arm: str,
    row: pd.Series,
    state: SetupState,
    geometry: tuple[float, float, float],
) -> dict:
    direction = state.direction
    decision = pd.Timestamp(row["decision_time_utc"])
    entry, stop, distance = geometry
    return {
        "event_id": _event_id(arm, direction, state, decision),
        "contract_id": CONTRACT_ID,
        "arm": arm,
        "symbol": "EURUSD",
        "timeframe": "M15",
        "direction": "long" if direction > 0 else "short",
        "pivot_open_utc": state.pivot_time.isoformat(),
        "sweep_open_utc": state.sweep_time.isoformat(),
        "displacement_open_utc": state.displacement_time.isoformat(),
        "order_block_open_utc": state.ob_time.isoformat(),
        "decision_time_utc": decision.isoformat(),
        "session_id": int(state.session_id),
        "ob_low": float(state.ob_low),
        "ob_high": float(state.ob_high),
        "overlap_low": float(state.overlap_low),
        "overlap_high": float(state.overlap_high),
        "entry_reference": entry,
        "stop_reference": stop,
        "risk_distance_pips": distance,
        "h1_bias": int(row["h1_bias"]),
        "h4_low": float(row["h4_low"]),
        "h4_high": float(row["h4_high"]),
        "adx_mt5": float(row["adx_mt5"]),
    }


def scan_detector(
    m15: pd.DataFrame,
    m1: pd.DataFrame,
    news: NewsGuard,
    spec: FrozenSpec | None = None,
) -> tuple[list[dict], dict]:
    spec = spec or FrozenSpec()
    bars = m15.sort_values("time_utc").reset_index(drop=True).copy()
    pivots = confirmed_pivot_frame(bars, spec.pivot_strength)
    for column in pivots.columns:
        bars[column] = pivots[column]
    if "atr_mt5" not in bars:
        bars["atr_mt5"] = atr_mt5(bars, spec.atr_period)
    if "adx_mt5" not in bars:
        bars["adx_mt5"] = adx_mt5(bars, spec.adx_period)

    funnel = {
        "m15_bars": int(len(bars)),
        "session_bars": 0,
        "context_aligned_bars": 0,
        "sweeps": 0,
        "displacement_fvg": 0,
        "valid_ob_fvg_overlap": 0,
        "control_ready": 0,
        "first_overlap_touches": 0,
        "confirmed_retests": 0,
        "challenger_ready": 0,
        "news_rejections": 0,
        "adx_rejections": 0,
        "risk_geometry_rejections": 0,
        "invalidations": 0,
        "expiries": 0,
    }
    events: list[dict] = []
    active: SetupState | None = None

    for i in range(len(bars)):
        row = bars.iloc[i]
        sid = session_id(row["time_utc"])
        if sid:
            funnel["session_bars"] += 1

        if active is not None:
            direction = active.direction
            if active.displacement_idx is None:
                if i > active.sweep_idx + spec.displacement_bars:
                    funnel["expiries"] += 1
                    active = None
                elif i > active.sweep_idx:
                    invalid = (
                        (direction > 0 and float(row.close) < active.sweep_extreme)
                        or (direction < 0 and float(row.close) > active.sweep_extreme)
                        or sid != active.session_id
                        or not context_aligned(row, direction)
                    )
                    if invalid:
                        funnel["invalidations"] += 1
                        active = None
                    else:
                        body = float(row.close - row.open)
                        directional = body > 0 if direction > 0 else body < 0
                        atr_value = float(row["atr_mt5"])
                        gap = strict_fvg(bars, i, direction)
                        if directional and np.isfinite(atr_value) and abs(body) >= spec.displacement_atr_multiple * atr_value and gap:
                            funnel["displacement_fvg"] += 1
                            ob = find_order_block(bars, active.sweep_idx, i, direction)
                            if ob is not None:
                                ob_idx, ob_body_low, ob_body_high, ob_low, ob_high = ob
                                overlap_low = max(ob_body_low, gap[0])
                                overlap_high = min(ob_body_high, gap[1])
                                if overlap_low < overlap_high:
                                    funnel["valid_ob_fvg_overlap"] += 1
                                    active.displacement_idx = i
                                    active.displacement_time = pd.Timestamp(row["time_utc"])
                                    active.ob_idx = ob_idx
                                    active.ob_time = pd.Timestamp(bars.at[ob_idx, "time_utc"])
                                    active.ob_low = ob_low
                                    active.ob_high = ob_high
                                    active.overlap_low = overlap_low
                                    active.overlap_high = overlap_high
                                    if not np.isfinite(float(row["adx_mt5"])) or float(row["adx_mt5"]) <= spec.min_adx:
                                        funnel["adx_rejections"] += 1
                                    elif news.blocked(pd.Timestamp(row["decision_time_utc"])):
                                        funnel["news_rejections"] += 1
                                    else:
                                        geometry = _risk_geometry(m1, row, active, direction, spec)
                                        if geometry is None:
                                            funnel["risk_geometry_rejections"] += 1
                                        else:
                                            funnel["control_ready"] += 1
                                            events.append(_make_event("CONTROL", row, active, geometry))
            else:
                if i <= active.displacement_idx:
                    continue
                too_old = i > active.displacement_idx + spec.retest_bars
                invalid = (
                    too_old
                    or sid != active.session_id
                    or not context_aligned(row, direction)
                    or (direction > 0 and float(row.close) < active.sweep_extreme)
                    or (direction < 0 and float(row.close) > active.sweep_extreme)
                )
                if invalid:
                    funnel["expiries" if too_old or sid != active.session_id else "invalidations"] += 1
                    active = None
                else:
                    touched = float(row.low) <= float(active.overlap_high) and float(row.high) >= float(active.overlap_low)
                    if touched:
                        funnel["first_overlap_touches"] += 1
                        if is_confirmation(bars, i, direction, spec):
                            funnel["confirmed_retests"] += 1
                            if not np.isfinite(float(row["adx_mt5"])) or float(row["adx_mt5"]) <= spec.min_adx:
                                funnel["adx_rejections"] += 1
                            elif news.blocked(pd.Timestamp(row["decision_time_utc"])):
                                funnel["news_rejections"] += 1
                            else:
                                geometry = _risk_geometry(m1, row, active, direction, spec)
                                if geometry is None:
                                    funnel["risk_geometry_rejections"] += 1
                                else:
                                    funnel["challenger_ready"] += 1
                                    events.append(_make_event("LSS_OB_CHALLENGER", row, active, geometry))
                        else:
                            funnel["invalidations"] += 1
                        active = None

        if active is None and sid:
            candidates: list[tuple[int, int, float, pd.Timestamp]] = []
            low_idx = int(row["pivot_low_idx"])
            high_idx = int(row["pivot_high_idx"])
            if (
                low_idx >= 0
                and 1 <= i - low_idx <= spec.sweep_lookback
                and float(row.low) < float(row.pivot_low)
                and float(row.close) > float(row.pivot_low)
                and context_aligned(row, 1)
            ):
                candidates.append((1, low_idx, float(row.low), pd.Timestamp(bars.at[low_idx, "time_utc"])))
            if (
                high_idx >= 0
                and 1 <= i - high_idx <= spec.sweep_lookback
                and float(row.high) > float(row.pivot_high)
                and float(row.close) < float(row.pivot_high)
                and context_aligned(row, -1)
            ):
                candidates.append((-1, high_idx, float(row.high), pd.Timestamp(bars.at[high_idx, "time_utc"])))
            if candidates:
                direction, _, extreme, pivot_time = candidates[0]
                funnel["context_aligned_bars"] += 1
                funnel["sweeps"] += 1
                active = SetupState(
                    direction=direction,
                    session_id=sid,
                    pivot_time=pivot_time,
                    sweep_idx=i,
                    sweep_time=pd.Timestamp(row["time_utc"]),
                    sweep_extreme=extreme,
                )

    ordered = sorted(events, key=lambda event: (event["decision_time_utc"], event["arm"], event["event_id"]))
    ids = [event["event_id"] for event in ordered]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate deterministic event ID")
    return ordered, funnel


def elapsed_weeks(start: str, end: str) -> float:
    days = (pd.Timestamp(end).date() - pd.Timestamp(start).date()).days + 1
    return days / 7.0


def density_summary(events: list[dict]) -> dict:
    challenger = [event for event in events if event["arm"] == "LSS_OB_CHALLENGER"]
    windows = {
        "pooled": ("2019-01-03", "2022-12-31"),
        "train": ("2019-01-03", "2020-12-31"),
        "validation": ("2021-01-01", "2022-12-31"),
    }
    result: dict[str, dict] = {}
    for name, (start, end) in windows.items():
        lo = pd.Timestamp(start)
        hi_exclusive = pd.Timestamp(end) + pd.Timedelta(days=1)
        count = sum(lo <= pd.Timestamp(event["decision_time_utc"]) < hi_exclusive for event in challenger)
        weeks = elapsed_weeks(start, end)
        result[name] = {
            "event_count": int(count),
            "elapsed_calendar_days": int(round(weeks * 7)),
            "elapsed_calendar_weeks": weeks,
            "events_per_elapsed_week": count / weeks,
        }
    return result


def density_verdict(summary: dict) -> tuple[str, list[dict]]:
    gates: list[dict] = []
    for name in ("pooled", "train", "validation"):
        row = summary[name]
        minimum_count = 300 if name == "pooled" else 100
        gates.extend(
            [
                {
                    "gate": f"{name}_minimum_count",
                    "threshold": minimum_count,
                    "actual": row["event_count"],
                    "status": "PASS" if row["event_count"] >= minimum_count else "FAIL",
                },
                {
                    "gate": f"{name}_cadence_floor",
                    "threshold": 2.0,
                    "actual": row["events_per_elapsed_week"],
                    "status": "PASS" if row["events_per_elapsed_week"] >= 2.0 else "FAIL",
                },
                {
                    "gate": f"{name}_cadence_ceiling",
                    "threshold": 5.0,
                    "actual": row["events_per_elapsed_week"],
                    "status": "PASS" if row["events_per_elapsed_week"] <= 5.0 else "FAIL",
                },
            ]
        )
    if any(gate["status"] == "FAIL" and gate["gate"].endswith("cadence_ceiling") for gate in gates):
        return "PARK_OVERBROAD_DETECTOR_NO_BUILD", gates
    if any(gate["status"] == "FAIL" for gate in gates):
        return "TERMINAL_STOP_FIDELITY_CADENCE_NO_BUILD_NO_MODEL0", gates
    return "DENSITY_FEASIBLE_ONLY", gates


FORBIDDEN_OUTPUT_KEYS = {
    "pnl",
    "profit",
    "loss",
    "return",
    "mfe",
    "mae",
    "fill",
    "trade_result",
    "win_rate",
    "profit_factor",
    "expectancy",
    "drawdown",
}


def assert_no_outcome_schema(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden outcome/performance key: {key}")
            assert_no_outcome_schema(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_outcome_schema(child)
