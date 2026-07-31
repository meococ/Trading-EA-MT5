"""Outcome-blind SCC Stage-0 identity, cadence, and geometry probe.

Implements the immutable HYP-SCC-EURUSD-M5-001 V1 plan. The scanner never
computes trade outcomes, future excursions, exits, PnL, PF, expectancy, win
rate, balance, equity, or drawdown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[3]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from indicators import atr_mt5  # noqa: E402
from sealed_loader import elapsed_weeks, load_sealed_bars, sha256_file  # noqa: E402


HYPOTHESIS_ID = "HYP-SCC-EURUSD-M5-001"
PLAN_REL = (
    "03. EA Developer/EA_SweepCascadeContinuation/research/"
    "HYP-SCC-EURUSD-M5-001_PROBE_PLAN.md"
)
PLAN_SHA256 = "6541239D88FFF99D9C8D1E2B3C78645ECE0BE01A69FFCF32BA1620ED6557FA3B"
MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json"
MANIFEST_SHA256 = "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54"
DATA_REL = "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
DATA_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
CLOCK_REL = "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
DESIGN_START = pd.Timestamp("2019-01-01 00:00:00")
DESIGN_END = pd.Timestamp("2023-01-01 00:00:00")
HOLDOUT_START = DESIGN_END
PIP = 0.0001
PASSAGE_HORIZON = 12
FORBIDDEN_OUTCOME_TOKENS = (
    "pnl",
    "profit",
    "return",
    "expectancy",
    "mfe",
    "mae",
    "win_rate",
    "winrate",
    "target_hit",
    "stop_hit",
    "exit_price",
    "balance",
    "equity",
    "drawdown",
)


def resample_complete_m5(m1: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Build left-labelled UTC M5 bars from exact offsets 0..4 only."""
    required = {
        "time_utc",
        "time_server",
        "utc_offset_h",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    }
    missing = required - set(m1.columns)
    if missing:
        raise RuntimeError(f"MISSING M1 COLUMNS: {sorted(missing)}")
    src = m1.copy()
    src["time_utc"] = pd.to_datetime(src["time_utc"])
    src["time_server"] = pd.to_datetime(src["time_server"])
    if src["time_utc"].duplicated(keep=False).any():
        raise RuntimeError("DUPLICATE M1 UTC TIMESTAMP")
    if (src["time_utc"].dt.second != 0).any() or (
        src["time_utc"].dt.microsecond != 0
    ).any():
        raise RuntimeError("M1 TIMESTAMP NOT MINUTE ALIGNED")
    src = src.sort_values("time_utc").reset_index(drop=True)
    src["_bin"] = src["time_utc"].dt.floor("5min")
    src["_offset"] = src["time_utc"].dt.minute % 5
    grouped = src.groupby("_bin", sort=True)
    bars = grouped.agg(
        time_server=("time_server", "first"),
        utc_offset_h=("utc_offset_h", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        _rows=("time_utc", "size"),
        _unique_minutes=("time_utc", "nunique"),
        _offset_count=("_offset", "nunique"),
        _offset_min=("_offset", "min"),
        _offset_max=("_offset", "max"),
    ).reset_index(names="time_utc")
    complete = (
        (bars["_rows"] == 5)
        & (bars["_unique_minutes"] == 5)
        & (bars["_offset_count"] == 5)
        & (bars["_offset_min"] == 0)
        & (bars["_offset_max"] == 4)
    )
    quality = {
        "input_m1_rows": int(len(src)),
        "total_m5_bins": int(len(bars)),
        "complete_m5_bins": int(complete.sum()),
        "incomplete_m5_bins": int((~complete).sum()),
    }
    keep = [
        "time_utc",
        "time_server",
        "utc_offset_h",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    ]
    return bars.loc[complete, keep].reset_index(drop=True), quality


def mark_confirmed_pivots(
    bars: pd.DataFrame, strength: int = 2
) -> pd.DataFrame:
    """Expose a strict N-strength pivot only before the scan bar opens."""
    if strength < 1:
        raise ValueError("strength must be >= 1")
    high = bars["high"].to_numpy(float)
    low = bars["low"].to_numpy(float)
    n = len(bars)
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for p in range(strength, n - strength):
        is_high[p] = bool(
            high[p] > np.max(high[p - strength : p])
            and high[p] > np.max(high[p + 1 : p + strength + 1])
        )
        is_low[p] = bool(
            low[p] < np.min(low[p - strength : p])
            and low[p] < np.min(low[p + 1 : p + strength + 1])
        )

    last_high = np.full(n, np.nan)
    last_low = np.full(n, np.nan)
    last_high_index = np.full(n, np.nan)
    last_low_index = np.full(n, np.nan)
    high_value = low_value = np.nan
    high_index = low_index = np.nan
    for scan in range(n):
        pivot = scan - strength - 1
        if pivot >= strength:
            if is_high[pivot]:
                high_value, high_index = high[pivot], float(pivot)
            if is_low[pivot]:
                low_value, low_index = low[pivot], float(pivot)
        last_high[scan], last_high_index[scan] = high_value, high_index
        last_low[scan], last_low_index[scan] = low_value, low_index
    return pd.DataFrame(
        {
            "pivot_high_flag": is_high,
            "pivot_low_flag": is_low,
            "last_pivot_high": last_high,
            "last_pivot_high_index": last_high_index,
            "last_pivot_low": last_low,
            "last_pivot_low_index": last_low_index,
        },
        index=bars.index,
    )


def add_stage0_features(bars: pd.DataFrame) -> pd.DataFrame:
    out = bars.copy()
    out["atr"] = atr_mt5(out, 14)
    return pd.concat([out, mark_confirmed_pivots(out, 2)], axis=1)


def _contiguous(times: pd.Series, left: int, right: int) -> bool:
    return (
        pd.Timestamp(times.iloc[right]) - pd.Timestamp(times.iloc[left])
        == pd.Timedelta(minutes=5)
    )


def _utc_date(value: Any):
    return pd.Timestamp(value).date()


def _terminal_row(active: dict[str, Any], reason: str, index: int, time) -> dict:
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "origin_id": active["origin_id"],
        "direction": active["direction"],
        "pivot_side": active["pivot_side"],
        "pivot_index": active["pivot_index"],
        "pivot_price": active["pivot_price"],
        "break_index": active["break_index"],
        "break_time_utc": active["break_time_utc"],
        "hold_index": active.get("hold_index"),
        "terminal_index": int(index),
        "terminal_time_utc": str(pd.Timestamp(time)),
        "terminal_reason": reason,
        "passage_lag": int(active.get("passage_lag", 0)),
    }


def _distribution(values: pd.Series) -> dict[str, Any]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return {
            "count": 0,
            "min": None,
            "p25": None,
            "median": None,
            "p75": None,
            "max": None,
        }
    return {
        "count": int(len(clean)),
        "min": float(clean.min()),
        "p25": float(clean.quantile(0.25)),
        "median": float(clean.median()),
        "p75": float(clean.quantile(0.75)),
        "max": float(clean.max()),
    }


def assert_outcome_blind(frame: pd.DataFrame) -> None:
    for column in frame.columns:
        lowered = str(column).lower()
        if any(token in lowered for token in FORBIDDEN_OUTCOME_TOKENS):
            raise RuntimeError(f"OUTCOME COLUMN FORBIDDEN: {column}")


def _candidate_row(
    bars: pd.DataFrame,
    active: dict[str, Any],
    retest_index: int,
) -> dict[str, Any]:
    times = bars["time_utc"]
    direction = active["direction"]
    break_index = active["break_index"]
    hold_index = active["hold_index"]
    atr = float(bars.iloc[retest_index]["atr"])
    entry_index = retest_index + 1
    entry_available = bool(
        entry_index < len(bars)
        and _contiguous(times, retest_index, entry_index)
        and _utc_date(times.iloc[entry_index]) == active["attempt_date"]
    )
    entry_price = (
        float(bars.iloc[entry_index]["open"]) if entry_available else np.nan
    )
    if direction == "LONG":
        complex_extreme = float(
            bars.loc[[break_index, hold_index, retest_index], "low"].min()
        )
        initial_stop = complex_extreme - 0.25 * atr
        risk_price = entry_price - initial_stop if entry_available else np.nan
    else:
        complex_extreme = float(
            bars.loc[[break_index, hold_index, retest_index], "high"].max()
        )
        initial_stop = complex_extreme + 0.25 * atr
        risk_price = initial_stop - entry_price if entry_available else np.nan
    risk_pips = risk_price / PIP if np.isfinite(risk_price) else np.nan
    geometry_valid = bool(np.isfinite(risk_pips) and risk_pips > 0)

    def cost_r(pips: float) -> float:
        return float(pips / risk_pips) if geometry_valid else np.nan

    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "origin_id": active["origin_id"],
        "direction": direction,
        "pivot_side": active["pivot_side"],
        "pivot_index": active["pivot_index"],
        "pivot_time_utc": active["pivot_time_utc"],
        "pivot_confirm_index": active["pivot_confirm_index"],
        "pivot_confirm_time_utc": active["pivot_confirm_time_utc"],
        "pivot_price": active["pivot_price"],
        "break_index": break_index,
        "break_time_utc": active["break_time_utc"],
        "hold_index": hold_index,
        "hold_time_utc": str(pd.Timestamp(times.iloc[hold_index])),
        "retest_index": int(retest_index),
        "retest_time_utc": str(pd.Timestamp(times.iloc[retest_index])),
        "decision_time_utc": str(pd.Timestamp(times.iloc[retest_index])),
        "passage_lag": int(active["passage_lag"]),
        "entry_reference_available": entry_available,
        "entry_reference_index": int(entry_index) if entry_available else None,
        "entry_reference_time_utc": (
            str(pd.Timestamp(times.iloc[entry_index])) if entry_available else None
        ),
        "entry_reference_price": entry_price,
        "atr14_mt5_retest": atr,
        "complex_extreme": complex_extreme,
        "initial_stop": initial_stop,
        "initial_risk_pips": float(risk_pips),
        "geometry_valid": geometry_valid,
        "cost_r_0_5": cost_r(0.5),
        "cost_r_1_5": cost_r(1.5),
        "cost_r_2_25": cost_r(2.25),
        "cost_r_3_0": cost_r(3.0),
        "calendar_year": int(_utc_date(times.iloc[retest_index]).year),
    }


def scan_scc_events(
    bars: pd.DataFrame,
    design_start: pd.Timestamp | None = None,
    design_end: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Run the frozen single-attempt/day SCC FSM without outcome reads."""
    required = {
        "time_utc",
        "open",
        "high",
        "low",
        "close",
        "atr",
        "last_pivot_high",
        "last_pivot_high_index",
        "last_pivot_low",
        "last_pivot_low_index",
    }
    missing = required - set(bars.columns)
    if missing:
        raise RuntimeError(f"MISSING M5 COLUMNS: {sorted(missing)}")
    design_start = pd.Timestamp(design_start or bars["time_utc"].min())
    design_end = pd.Timestamp(
        design_end or (pd.Timestamp(bars["time_utc"].max()) + pd.Timedelta(minutes=5))
    )
    times = pd.to_datetime(bars["time_utc"]).reset_index(drop=True)
    close = bars["close"].to_numpy(float)
    high = bars["high"].to_numpy(float)
    low = bars["low"].to_numpy(float)
    pivot_high = bars["last_pivot_high"].to_numpy(float)
    pivot_low = bars["last_pivot_low"].to_numpy(float)
    pivot_high_index = bars["last_pivot_high_index"].to_numpy(float)
    pivot_low_index = bars["last_pivot_low_index"].to_numpy(float)

    consumed_high: set[int] = set()
    consumed_low: set[int] = set()
    attempted_dates: set[Any] = set()
    active: dict[str, Any] | None = None
    control_rows: list[dict[str, Any]] = []
    challenger_rows: list[dict[str, Any]] = []
    terminal_rows: list[dict[str, Any]] = []
    funnel = {
        "raw_break_arms": 0,
        "long_break_arms": 0,
        "short_break_arms": 0,
        "ambiguous_break_bars": 0,
        "hold_pass": 0,
        "reject_hold": 0,
        "accepted_retests": 0,
        "reject_close_inside": 0,
        "expire_12": 0,
        "reject_gap": 0,
        "reject_day_boundary": 0,
        "reject_end_of_data": 0,
        "blocked_by_daily_attempt_cap": 0,
    }

    def raw_conditions(index: int) -> tuple[bool, bool]:
        if index <= 0 or not _contiguous(times, index - 1, index):
            return False, False
        ph_idx = (
            int(pivot_high_index[index])
            if np.isfinite(pivot_high_index[index])
            else None
        )
        pl_idx = (
            int(pivot_low_index[index])
            if np.isfinite(pivot_low_index[index])
            else None
        )
        long_ok = bool(
            ph_idx is not None
            and ph_idx not in consumed_high
            and ph_idx <= index - 3
            and np.isfinite(pivot_high[index])
            and close[index - 1] <= pivot_high[index]
            and close[index] > pivot_high[index]
        )
        short_ok = bool(
            pl_idx is not None
            and pl_idx not in consumed_low
            and pl_idx <= index - 3
            and np.isfinite(pivot_low[index])
            and close[index - 1] >= pivot_low[index]
            and close[index] < pivot_low[index]
        )
        return long_ok, short_ok

    for index in range(1, len(bars)):
        timestamp = pd.Timestamp(times.iloc[index])
        in_design = design_start <= timestamp < design_end

        if active is not None:
            reason: str | None = None
            accepted = False
            if not _contiguous(times, active["last_index"], index):
                reason = "REJECT_GAP"
                funnel["reject_gap"] += 1
            elif _utc_date(timestamp) != active["attempt_date"]:
                reason = "REJECT_DAY_BOUNDARY"
                funnel["reject_day_boundary"] += 1
            elif active["state"] == "HOLD":
                outside = (
                    close[index] > active["pivot_price"]
                    if active["direction"] == "LONG"
                    else close[index] < active["pivot_price"]
                )
                if not outside:
                    reason = "REJECT_HOLD"
                    funnel["reject_hold"] += 1
                else:
                    active["state"] = "RETEST"
                    active["hold_index"] = int(index)
                    active["last_index"] = int(index)
                    active["passage_lag"] = 0
                    funnel["hold_pass"] += 1
                    continue
            else:
                active["passage_lag"] += 1
                if active["direction"] == "LONG":
                    close_inside = close[index] <= active["pivot_price"]
                    retest = (
                        low[index] <= active["pivot_price"]
                        and close[index] > active["pivot_price"]
                    )
                else:
                    close_inside = close[index] >= active["pivot_price"]
                    retest = (
                        high[index] >= active["pivot_price"]
                        and close[index] < active["pivot_price"]
                    )
                if close_inside:
                    reason = "REJECT_CLOSE_INSIDE"
                    funnel["reject_close_inside"] += 1
                elif retest:
                    reason = "ACCEPT_RETEST"
                    accepted = True
                    funnel["accepted_retests"] += 1
                elif active["passage_lag"] >= PASSAGE_HORIZON:
                    reason = "EXPIRE_12"
                    funnel["expire_12"] += 1
                else:
                    active["last_index"] = int(index)
                    continue

            if reason is not None:
                terminal_rows.append(_terminal_row(active, reason, index, timestamp))
                if accepted:
                    challenger_rows.append(_candidate_row(bars, active, index))
                active = None
                # A date-boundary resolution may fall through to a fresh WAIT
                # decision on the new date. Same-date resolutions remain capped.

        if not in_design:
            continue
        attempt_date = _utc_date(timestamp)
        long_ok, short_ok = raw_conditions(index)
        if attempt_date in attempted_dates:
            if long_ok or short_ok:
                funnel["blocked_by_daily_attempt_cap"] += 1
            continue
        if long_ok and short_ok:
            funnel["ambiguous_break_bars"] += 1
            continue
        if not long_ok and not short_ok:
            continue

        direction = "LONG" if long_ok else "SHORT"
        pivot_side = "HIGH" if long_ok else "LOW"
        pivot_index = int(
            pivot_high_index[index] if long_ok else pivot_low_index[index]
        )
        pivot_price = float(pivot_high[index] if long_ok else pivot_low[index])
        pivot_confirm_index = pivot_index + 2
        origin_id = (
            f"{pivot_side}:{pivot_index}:"
            f"{pd.Timestamp(times.iloc[index]).isoformat()}"
        )
        attempted_dates.add(attempt_date)
        if long_ok:
            consumed_high.add(pivot_index)
            funnel["long_break_arms"] += 1
        else:
            consumed_low.add(pivot_index)
            funnel["short_break_arms"] += 1
        funnel["raw_break_arms"] += 1
        active = {
            "state": "HOLD",
            "origin_id": origin_id,
            "direction": direction,
            "pivot_side": pivot_side,
            "pivot_index": pivot_index,
            "pivot_time_utc": str(pd.Timestamp(times.iloc[pivot_index])),
            "pivot_confirm_index": pivot_confirm_index,
            "pivot_confirm_time_utc": str(
                pd.Timestamp(times.iloc[pivot_confirm_index])
            ),
            "pivot_price": pivot_price,
            "break_index": int(index),
            "break_time_utc": str(timestamp),
            "attempt_date": attempt_date,
            "last_index": int(index),
            "passage_lag": 0,
        }
        control_rows.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "origin_id": origin_id,
                "direction": direction,
                "pivot_side": pivot_side,
                "pivot_index": pivot_index,
                "pivot_time_utc": active["pivot_time_utc"],
                "pivot_confirm_index": pivot_confirm_index,
                "pivot_confirm_time_utc": active["pivot_confirm_time_utc"],
                "pivot_price": pivot_price,
                "break_index": int(index),
                "break_time_utc": str(timestamp),
                "decision_time_utc": str(timestamp),
                "break_distance_pips": float(
                    (
                        close[index] - pivot_price
                        if direction == "LONG"
                        else pivot_price - close[index]
                    )
                    / PIP
                ),
                "atr14_mt5_break": float(bars.iloc[index]["atr"]),
                "calendar_year": int(attempt_date.year),
            }
        )

    if active is not None:
        funnel["reject_end_of_data"] += 1
        terminal_rows.append(
            _terminal_row(
                active,
                "REJECT_END_OF_DATA",
                len(bars) - 1,
                times.iloc[-1],
            )
        )

    control = pd.DataFrame(control_rows)
    challenger = pd.DataFrame(challenger_rows)
    terminals = pd.DataFrame(terminal_rows)
    for frame in (control, challenger, terminals):
        assert_outcome_blind(frame)
    return {
        "funnel": funnel,
        "control_candidates": control,
        "challenger_candidates": challenger,
        "terminal_ledger": terminals,
        "consumed_pivot_highs": len(consumed_high),
        "consumed_pivot_lows": len(consumed_low),
    }


def _frame_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode(
        "utf-8"
    )


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _evaluate_gates(
    result: dict[str, Any],
    deterministic: bool,
    seal_receipt: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    control = result["control_candidates"]
    challenger = result["challenger_candidates"]
    funnel = result["funnel"]
    weeks = elapsed_weeks("2019-01-01", "2022-12-31")
    count = int(len(challenger))
    cadence = count / weeks
    year_counts = {
        str(year): int((challenger.get("calendar_year", pd.Series(dtype=int)) == year).sum())
        for year in range(2019, 2023)
    }
    year_cadence = {
        str(year): year_counts[str(year)]
        / elapsed_weeks(f"{year}-01-01", f"{year}-12-31")
        for year in range(2019, 2023)
    }
    directions = (
        challenger["direction"].value_counts().to_dict()
        if not challenger.empty
        else {}
    )
    max_year_share = (
        max(year_counts.values()) / count if count else None
    )
    lag_share = (
        float((challenger["passage_lag"] >= 2).mean())
        if not challenger.empty
        else None
    )
    risk = _distribution(
        challenger.get("initial_risk_pips", pd.Series(dtype=float))
    )
    cost = _distribution(challenger.get("cost_r_1_5", pd.Series(dtype=float)))
    entry_available_share = (
        float(challenger["entry_reference_available"].mean())
        if not challenger.empty
        else 0.0
    )
    control_ids = set(control.get("origin_id", pd.Series(dtype=str)))
    challenger_ids = set(challenger.get("origin_id", pd.Series(dtype=str)))
    strict_subset = bool(challenger_ids < control_ids)
    pivot_duplicates = (
        int(control.duplicated(["pivot_side", "pivot_index"]).sum())
        if not control.empty
        else 0
    )
    outcome_columns = []
    for frame in (control, challenger, result["terminal_ledger"]):
        for column in frame.columns:
            lowered = str(column).lower()
            if any(token in lowered for token in FORBIDDEN_OUTCOME_TOKENS):
                outcome_columns.append(str(column))

    gates = {
        "hash_and_holdout_seal": {
            "threshold": "all exact; holdout=0",
            "actual": int(seal_receipt["holdout_bars_loaded"]),
            "passed": int(seal_receipt["holdout_bars_loaded"]) == 0,
        },
        "deterministic_replay": {
            "threshold": True,
            "actual": deterministic,
            "passed": deterministic,
        },
        "pivot_and_identity_integrity": {
            "threshold": "reuse=0 ambiguous=0 strict_subset",
            "actual": {
                "pivot_reuse": pivot_duplicates,
                "ambiguous": funnel["ambiguous_break_bars"],
                "strict_subset": strict_subset,
            },
            "passed": (
                pivot_duplicates == 0
                and funnel["ambiguous_break_bars"] == 0
                and strict_subset
            ),
        },
        "minimum_accepted_events": {
            "threshold": 418,
            "actual": count,
            "passed": count >= 418,
        },
        "cadence_pooled_and_each_year": {
            "threshold": "2.00..5.00",
            "actual": {"pooled": cadence, "by_year": year_cadence},
            "passed": (
                2.0 <= cadence <= 5.0
                and all(2.0 <= value <= 5.0 for value in year_cadence.values())
            ),
        },
        "direction_minimum": {
            "threshold": {"LONG": 100, "SHORT": 100},
            "actual": {
                "LONG": int(directions.get("LONG", 0)),
                "SHORT": int(directions.get("SHORT", 0)),
            },
            "passed": (
                int(directions.get("LONG", 0)) >= 100
                and int(directions.get("SHORT", 0)) >= 100
            ),
        },
        "maximum_year_share": {
            "threshold": 0.35,
            "actual": max_year_share,
            "passed": bool(max_year_share is not None and max_year_share <= 0.35),
        },
        "variable_first_passage": {
            "threshold": 0.20,
            "actual": lag_share,
            "passed": bool(lag_share is not None and lag_share >= 0.20),
        },
        "risk_geometry": {
            "threshold": {"median_pips": 7.5, "p25_pips": 5.0},
            "actual": {"median_pips": risk["median"], "p25_pips": risk["p25"]},
            "passed": bool(
                risk["median"] is not None
                and risk["p25"] is not None
                and risk["median"] >= 7.5
                and risk["p25"] >= 5.0
            ),
        },
        "cost_in_r_1_5pip": {
            "threshold": {"median_max": 0.20, "p75_max": 0.30},
            "actual": {"median": cost["median"], "p75": cost["p75"]},
            "passed": bool(
                cost["median"] is not None
                and cost["p75"] is not None
                and cost["median"] <= 0.20
                and cost["p75"] <= 0.30
            ),
        },
        "entry_reference_integrity": {
            "threshold": 1.0,
            "actual": entry_available_share,
            "passed": entry_available_share == 1.0,
        },
        "outcome_blind_columns": {
            "threshold": 0,
            "actual": sorted(set(outcome_columns)),
            "passed": not outcome_columns,
        },
    }
    passed = all(gate["passed"] for gate in gates.values())
    verdict = (
        "PASS_STAGE0_OPEN_SEPARATE_ECONOMIC_PREREG"
        if passed
        else "PARK_STAGE0_REQUIRED_GATE_FAIL_NO_OUTCOME_READ"
    )
    return (
        {
            "gates": gates,
            "accepted_count": count,
            "accepted_per_elapsed_week": cadence,
            "elapsed_calendar_weeks": weeks,
            "year_counts": year_counts,
            "year_cadence": year_cadence,
            "direction_counts": {
                "LONG": int(directions.get("LONG", 0)),
                "SHORT": int(directions.get("SHORT", 0)),
            },
            "max_year_share": max_year_share,
            "lag_ge_2_share": lag_share,
            "risk_pips": risk,
            "cost_r_1_5pip": cost,
            "entry_reference_available_share": entry_available_share,
            "strict_treatment_subset": strict_subset,
            "pivot_reuse_count": pivot_duplicates,
        },
        verdict,
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def run_probe(output_dir: Path) -> dict[str, Any]:
    paths = {
        "plan": WORKSPACE / PLAN_REL,
        "manifest": WORKSPACE / MANIFEST_REL,
        "data": WORKSPACE / DATA_REL,
        "clock": WORKSPACE / CLOCK_REL,
    }
    expected = {
        "plan": PLAN_SHA256,
        "manifest": MANIFEST_SHA256,
        "data": DATA_SHA256,
        "clock": CLOCK_SHA256,
    }
    actual = {key: sha256_file(path) for key, path in paths.items()}
    if actual != expected:
        raise RuntimeError(f"HASH BINDING FAILURE expected={expected} actual={actual}")

    sealed, seal_receipt = load_sealed_bars(paths["data"], HOLDOUT_START)
    sealed["time_utc"] = pd.to_datetime(sealed["time_utc"])
    design_m1 = sealed.loc[
        (sealed["time_utc"] >= DESIGN_START)
        & (sealed["time_utc"] < DESIGN_END)
    ].reset_index(drop=True)
    bars, quality = resample_complete_m5(design_m1)
    featured = add_stage0_features(bars)
    first = scan_scc_events(featured, DESIGN_START, DESIGN_END)
    second = scan_scc_events(featured, DESIGN_START, DESIGN_END)
    first_bytes = {
        "control": _frame_bytes(first["control_candidates"]),
        "challenger": _frame_bytes(first["challenger_candidates"]),
        "terminal": _frame_bytes(first["terminal_ledger"]),
    }
    second_bytes = {
        "control": _frame_bytes(second["control_candidates"]),
        "challenger": _frame_bytes(second["challenger_candidates"]),
        "terminal": _frame_bytes(second["terminal_ledger"]),
    }
    deterministic = all(first_bytes[key] == second_bytes[key] for key in first_bytes)
    metrics, verdict = _evaluate_gates(first, deterministic, seal_receipt)

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths = {
        "control_csv": output_dir / "stage0_control_breaks.csv",
        "challenger_csv": output_dir / "stage0_scc_candidates.csv",
        "terminal_csv": output_dir / "stage0_terminal_states.csv",
        "result_json": output_dir / "stage0_result.json",
    }
    artifact_paths["control_csv"].write_bytes(first_bytes["control"])
    artifact_paths["challenger_csv"].write_bytes(first_bytes["challenger"])
    artifact_paths["terminal_csv"].write_bytes(first_bytes["terminal"])
    artifact_hashes = {
        "control_csv_sha256": _sha_bytes(first_bytes["control"]),
        "challenger_csv_sha256": _sha_bytes(first_bytes["challenger"]),
        "terminal_csv_sha256": _sha_bytes(first_bytes["terminal"]),
    }
    result = {
        "schema_version": "scc_stage0_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "verdict": verdict,
        "promotion_eligible": False,
        "outcome_blind_attestation": True,
        "source_build_authorized": verdict.startswith("PASS_STAGE0"),
        "model0_authorized": False,
        "economic_metrics_authorized": False,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "manifest_path": MANIFEST_REL,
        "manifest_sha256": MANIFEST_SHA256,
        "data_path": DATA_REL,
        "data_sha256": DATA_SHA256,
        "clock_path": CLOCK_REL,
        "clock_sha256": CLOCK_SHA256,
        "scanner_path": str(Path(__file__).resolve().relative_to(WORKSPACE)).replace(
            "\\", "/"
        ),
        "scanner_sha256": sha256_file(Path(__file__).resolve()),
        "design_start": str(DESIGN_START),
        "design_end_exclusive": str(DESIGN_END),
        "seal_receipt": seal_receipt,
        "quality": quality,
        "confirmed_fractal_highs": int(
            featured.get("pivot_high_flag", pd.Series(dtype=bool)).sum()
        ),
        "confirmed_fractal_lows": int(
            featured.get("pivot_low_flag", pd.Series(dtype=bool)).sum()
        ),
        "consumed_pivot_highs": first["consumed_pivot_highs"],
        "consumed_pivot_lows": first["consumed_pivot_lows"],
        "funnel": first["funnel"],
        "control_breaks": int(len(first["control_candidates"])),
        "artifacts": artifact_hashes,
        **metrics,
        "cost_status": "UNVERIFIED_PROXY",
        "news_status": "NOT_APPLICABLE_STAGE0",
    }
    safe = _json_safe(result)
    artifact_paths["result_json"].write_text(
        json.dumps(safe, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    safe["artifacts"]["result_json_sha256"] = sha256_file(
        artifact_paths["result_json"]
    )
    return safe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parent
            / "evidence"
            / "HYP-SCC-EURUSD-M5-001_STAGE0"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_probe(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

