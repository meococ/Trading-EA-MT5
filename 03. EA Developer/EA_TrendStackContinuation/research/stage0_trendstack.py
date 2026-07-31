"""Deterministic, outcome-blind Stage-0 scanner for TrendStack.

This module implements only the H1 pre-entry observation contract frozen in
HYP-TRENDSTACK-EURUSD-H1-001. It never opens M1, trade paths, PnL, or the
2023+ holdout. A PASS means only that the frozen observation-count gates are
met; it does not authorize an economic claim or an EA build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pyarrow_dataset


WORKSPACE = Path(__file__).resolve().parents[3]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from indicators import atr_mt5  # noqa: E402
from sealed_loader import sha256_file  # noqa: E402


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-001"
PLAN_REL = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "HYP-TRENDSTACK-EURUSD-H1-001_PROBE_PLAN.md"
)
PLAN_SHA256 = "891291042FB326EF67411A0763015B4E3E68654F59E4B323C2217F1E8015B6F0"
DATA_REL = "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet"
DATA_SHA256 = "71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08"
MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json"

WARMUP_START = pd.Timestamp("2015-01-02")
DESIGN_START = pd.Timestamp("2016-01-04")
VALIDATION_START = pd.Timestamp("2021-01-01")
HOLDOUT_START = pd.Timestamp("2023-01-01")
DECISION_HOURS = tuple(range(6, 12))

SPLIT_LIMITS = {
    "DESIGN": {"minimum": 522, "maximum": 1302},
    "VALIDATION": {"minimum": 209, "maximum": 521},
}
MIN_DIRECTION_COUNT = 50

REQUIRED_H1_COLUMNS = {"time_utc", "open", "high", "low", "close"}
FORBIDDEN_LEDGER_TOKENS = (
    "pnl",
    "profit",
    "expectancy",
    "forward",
    "mfe",
    "mae",
    "winner",
    "loser",
    "gross_r",
    "net_r",
    "exit_price",
    "stop_hit",
    "target_hit",
)

LEDGER_COLUMNS = [
    "hypothesis_id",
    "plan_sha256",
    "opportunity_id",
    "split",
    "decision_time_utc",
    "access_rows_released",
    "access_cumulative_visible_rows",
    "access_max_visible_time_utc",
    "access_causal_pass",
    "prior_finalized_rows_immutable",
    "valid_daily_closes_before",
    "m252_direction",
    "m252_label",
    "m252_reason",
    "m252_oldest_source_date",
    "m252_latest_source_date",
    "m6_direction",
    "m6_label",
    "m6_reason",
    "m6_first_source_time_utc",
    "m6_last_source_time_utc",
    "atr20",
    "atr20_reason",
    "atr20_source_time_utc",
    "base_eligible",
    "base_exclusion_reason",
    "alignment",
    "control_m252_eligible",
    "control_m6_eligible",
    "challenger_stack_eligible",
    "negative_disagree_eligible",
    "challenger_rejection_reason",
    "opportunity_snapshot_sha256",
]


def _normalise_h1(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_H1_COLUMNS - set(frame.columns)
    if missing:
        raise RuntimeError(f"MISSING H1 COLUMNS: {sorted(missing)}")
    out = frame.copy()
    out["time_utc"] = pd.to_datetime(out["time_utc"], utc=True).dt.tz_localize(None)
    return out.sort_values("time_utc", kind="mergesort").reset_index(drop=True)


def _valid_ohlc_mask(frame: pd.DataFrame) -> pd.Series:
    values = frame[["open", "high", "low", "close"]].apply(
        pd.to_numeric, errors="coerce"
    )
    finite_positive = pd.Series(
        np.isfinite(values.to_numpy()).all(axis=1)
        & (values.to_numpy() > 0.0).all(axis=1),
        index=frame.index,
    )
    geometry = (
        (values["high"] >= values[["open", "close"]].max(axis=1))
        & (values["low"] <= values[["open", "close"]].min(axis=1))
        & (values["high"] >= values["low"])
    )
    return finite_positive & geometry


def _iso(timestamp: Any) -> str:
    return pd.Timestamp(timestamp).isoformat()


def _direction_label(direction: int | None) -> str | None:
    if direction == 1:
        return "LONG"
    if direction == -1:
        return "SHORT"
    if direction == 0:
        return "FLAT"
    return None


class CausalParquetCursor:
    """Release H1 rows only as the virtual decision clock advances.

    The Arrow scanner is holdout-filtered before row decoding. Its batch size is
    one row, so at most one look-ahead row can exist inside the accessor; that
    row is never returned to, or materialized in, the decision state before its
    timestamp is legal.
    """

    def __init__(self, path: Path, expected_sha256: str = DATA_SHA256):
        self.path = Path(path)
        self.data_sha256 = sha256_file(self.path)
        if self.data_sha256 != expected_sha256:
            raise RuntimeError(
                f"DATA HASH MISMATCH: expected={expected_sha256} actual={self.data_sha256}"
            )
        dataset = pyarrow_dataset.dataset(str(self.path), format="parquet")
        missing = REQUIRED_H1_COLUMNS - set(dataset.schema.names)
        if missing:
            raise RuntimeError(f"MISSING H1 COLUMNS: {sorted(missing)}")
        columns = ["time_utc", "open", "high", "low", "close"]
        scanner = dataset.scanner(
            columns=columns,
            filter=(
                pyarrow_dataset.field("time_utc")
                < np.datetime64("2023-01-01T00:00:00", "ns")
            ),
            batch_size=1,
            use_threads=False,
        )
        self._batches = iter(scanner.to_batches())
        self._buffer: dict | None = None
        self._source_exhausted = False
        self._last_source_time: pd.Timestamp | None = None
        self._last_cutoff: pd.Timestamp | None = None
        self._first_visible_time: pd.Timestamp | None = None
        self._max_visible_time: pd.Timestamp | None = None
        self._rows_returned = 0
        self._max_internal_buffer_rows = 0
        self.holdout_rows_returned = 0

    def _fill_buffer(self) -> None:
        if self._buffer is not None or self._source_exhausted:
            return
        while True:
            try:
                batch = next(self._batches)
            except StopIteration:
                self._source_exhausted = True
                return
            if batch.num_rows:
                break
        payload = batch.to_pydict()
        if batch.num_rows != 1:
            raise RuntimeError("CAUSAL CURSOR BATCH SIZE VIOLATION")
        row = {column: payload[column][0] for column in payload}
        timestamp = pd.Timestamp(row["time_utc"])
        if timestamp >= HOLDOUT_START:
            raise RuntimeError("HOLDOUT ROW DECODED BY FILTERED CURSOR")
        if self._last_source_time is not None and timestamp < self._last_source_time:
            raise RuntimeError("PARQUET SOURCE CHRONOLOGY VIOLATION")
        self._last_source_time = timestamp
        row["time_utc"] = timestamp
        self._buffer = row
        self._max_internal_buffer_rows = max(self._max_internal_buffer_rows, 1)

    def advance_to(self, decision_cutoff: Any) -> tuple[pd.DataFrame, dict]:
        cutoff = pd.Timestamp(decision_cutoff)
        if cutoff > HOLDOUT_START:
            raise RuntimeError("HOLDOUT ACCESS FORBIDDEN")
        if self._last_cutoff is not None and cutoff <= self._last_cutoff:
            raise RuntimeError("VIRTUAL DECISION CLOCK MUST ADVANCE STRICTLY")
        released: list[dict] = []
        while True:
            self._fill_buffer()
            if self._buffer is None or pd.Timestamp(self._buffer["time_utc"]) >= cutoff:
                break
            row = self._buffer
            self._buffer = None
            timestamp = pd.Timestamp(row["time_utc"])
            if timestamp >= HOLDOUT_START:
                self.holdout_rows_returned += 1
                raise RuntimeError("HOLDOUT ROW RETURNED TO DECISION STATE")
            released.append(row)
            self._rows_returned += 1
            if self._first_visible_time is None:
                self._first_visible_time = timestamp
            self._max_visible_time = timestamp
        self._last_cutoff = cutoff
        if released:
            frame = _normalise_h1(pd.DataFrame(released))
            first_released = _iso(frame["time_utc"].min())
            last_released = _iso(frame["time_utc"].max())
        else:
            frame = pd.DataFrame(columns=["time_utc", "open", "high", "low", "close"])
            first_released = None
            last_released = None
        causal_pass = self._max_visible_time is None or self._max_visible_time < cutoff
        if not causal_pass:
            raise RuntimeError("CAUSAL CURSOR RELEASED A FUTURE ROW")
        trace = {
            "decision_cutoff": _iso(cutoff),
            "rows_released": int(len(frame)),
            "cumulative_visible_rows": int(self._rows_returned),
            "first_released_time_utc": first_released,
            "last_released_time_utc": last_released,
            "max_visible_time_utc": (
                _iso(self._max_visible_time) if self._max_visible_time is not None else None
            ),
            "causal_pass": causal_pass,
        }
        return frame, trace

    def receipt(self) -> dict:
        return {
            "bars_path": str(self.path),
            "data_sha256": self.data_sha256,
            "timeframe": "H1",
            "access_method": "pyarrow.dataset.Scanner.to_batches",
            "predicate": "time_utc < 2023-01-01T00:00:00",
            "batch_size_rows": 1,
            "max_internal_lookahead_rows": self._max_internal_buffer_rows,
            "rows_returned_to_decision_state": self._rows_returned,
            "first_row_returned": (
                _iso(self._first_visible_time) if self._first_visible_time is not None else None
            ),
            "last_row_returned": (
                _iso(self._max_visible_time) if self._max_visible_time is not None else None
            ),
            "holdout_rows_returned": self.holdout_rows_returned,
            "holdout_opened": False,
        }


def build_valid_daily_sequence(h1: pd.DataFrame) -> pd.DataFrame:
    """Classify UTC days and retain only causal daily closes from valid days."""
    bars = _normalise_h1(h1)
    bars["date_utc"] = bars["time_utc"].dt.normalize()
    records: list[dict] = []
    for date_utc, day in bars.groupby("date_utc", sort=True):
        distinct_opens = int(day["time_utc"].nunique())
        duplicate_opens = int(day["time_utc"].duplicated(keep=False).sum())
        on_hour = (
            (day["time_utc"].dt.minute == 0)
            & (day["time_utc"].dt.second == 0)
            & (day["time_utc"].dt.microsecond == 0)
        )
        reason: str | None = None
        if duplicate_opens:
            reason = "DUPLICATE_UTC_OPEN"
        elif not bool(on_hour.all()):
            reason = "IRREGULAR_H1_UTC_OPEN"
        elif not bool(_valid_ohlc_mask(day).all()):
            reason = "INVALID_OHLC"
        elif distinct_opens < 20:
            reason = "PARTIAL_DAY_LT20"
        latest = day.sort_values("time_utc", kind="mergesort").iloc[-1]
        records.append(
            {
                "date_utc": pd.Timestamp(date_utc),
                "valid": reason is None,
                "exclusion_reason": reason,
                "distinct_h1_opens": distinct_opens,
                "row_count": int(len(day)),
                "daily_close": float(latest["close"]) if reason is None else np.nan,
                "close_time_utc": latest["time_utc"] if reason is None else pd.NaT,
            }
        )
    columns = [
        "date_utc",
        "valid",
        "exclusion_reason",
        "distinct_h1_opens",
        "row_count",
        "daily_close",
        "close_time_utc",
    ]
    if not records:
        return pd.DataFrame(columns=columns).set_index("date_utc")
    return pd.DataFrame(records, columns=columns).set_index("date_utc").sort_index()


def compute_m252(daily: pd.DataFrame, decision_date: Any) -> dict:
    """Compute sign(C[-1] / C[-253] - 1) using dates strictly before d."""
    decision_date = pd.Timestamp(decision_date).normalize()
    accepted = daily.loc[(daily.index < decision_date) & daily["valid"]].sort_index()
    result = {
        "direction": None,
        "reason": None,
        "valid_closes_before": int(len(accepted)),
        "oldest_source_date": None,
        "latest_source_date": None,
    }
    if len(accepted) < 253:
        result["reason"] = "INSUFFICIENT_M252_HISTORY"
        return result
    oldest = accepted.iloc[-253]
    latest = accepted.iloc[-1]
    oldest_close = float(oldest["daily_close"])
    latest_close = float(latest["daily_close"])
    if not np.isfinite([oldest_close, latest_close]).all() or min(oldest_close, latest_close) <= 0:
        result["reason"] = "NONFINITE_M252_INPUT"
        return result
    result["oldest_source_date"] = str(accepted.index[-253].date())
    result["latest_source_date"] = str(accepted.index[-1].date())
    if latest_close == oldest_close:
        result["direction"] = 0
        result["reason"] = "M252_EQUALITY"
    else:
        result["direction"] = 1 if latest_close > oldest_close else -1
    return result


def compute_m6(day_rows: pd.DataFrame, decision_date: Any) -> dict:
    """Compute the 06:00-open to 11:00-close sign, ignoring every later bar."""
    day = _normalise_h1(day_rows)
    decision_date = pd.Timestamp(decision_date).normalize()
    targets = [decision_date + pd.Timedelta(hours=hour) for hour in DECISION_HOURS]
    selected: list[pd.Series] = []
    for target in targets:
        matched = day.loc[day["time_utc"] == target]
        if matched.empty:
            return {
                "direction": None,
                "reason": "MISSING_SIX_HOUR_BAR",
                "first_source_time_utc": None,
                "last_source_time_utc": None,
            }
        if len(matched) != 1:
            return {
                "direction": None,
                "reason": "DUPLICATE_SIX_HOUR_BAR",
                "first_source_time_utc": None,
                "last_source_time_utc": None,
            }
        selected.append(matched.iloc[0])
    six = pd.DataFrame(selected).reset_index(drop=True)
    if not bool(_valid_ohlc_mask(six).all()):
        return {
            "direction": None,
            "reason": "INVALID_SIX_HOUR_OHLC",
            "first_source_time_utc": None,
            "last_source_time_utc": None,
        }
    first_open = float(six.iloc[0]["open"])
    last_close = float(six.iloc[-1]["close"])
    direction = 0 if last_close == first_open else (1 if last_close > first_open else -1)
    return {
        "direction": direction,
        "reason": "M6_EQUALITY" if direction == 0 else None,
        "first_source_time_utc": _iso(six.iloc[0]["time_utc"]),
        "last_source_time_utc": _iso(six.iloc[-1]["time_utc"]),
    }


def atr20_at_decision(h1: pd.DataFrame, decision_date: Any) -> dict:
    """Evaluate simple TR(20) at the closed 11:00 H1 bar, never at 12:00."""
    bars = _normalise_h1(h1)
    decision_date = pd.Timestamp(decision_date).normalize()
    source_time = decision_date + pd.Timedelta(hours=11)
    exact = bars.loc[bars["time_utc"] == source_time]
    if exact.empty:
        return {"value": None, "reason": "MISSING_ATR20_SOURCE_BAR", "source_time_utc": None}
    if len(exact) != 1:
        return {"value": None, "reason": "DUPLICATE_ATR20_SOURCE_BAR", "source_time_utc": None}
    causal = bars.loc[bars["time_utc"] <= source_time].copy()
    tail = causal.tail(21)
    if tail["time_utc"].duplicated(keep=False).any():
        return {"value": None, "reason": "AMBIGUOUS_ATR20_SEQUENCE", "source_time_utc": None}
    if len(causal) < 20 or not bool(_valid_ohlc_mask(causal.tail(20)).all()):
        return {"value": None, "reason": "INSUFFICIENT_OR_INVALID_ATR20", "source_time_utc": None}
    value = float(atr_mt5(causal[["open", "high", "low", "close"]], 20).iloc[-1])
    if not np.isfinite(value) or value <= 0:
        return {"value": None, "reason": "NONPOSITIVE_ATR20", "source_time_utc": None}
    return {"value": value, "reason": None, "source_time_utc": _iso(source_time)}


class CausalTrendStackState:
    """Historical state containing only rows released by the virtual clock."""

    def __init__(self):
        self._bars: list[dict] = []
        self._positions: dict[pd.Timestamp, list[int]] = {}
        self._day_rows: dict[pd.Timestamp, list[dict]] = {}
        self._daily_records: list[dict] = []
        self._finalized_daily_dates: set[pd.Timestamp] = set()
        self._last_visible_time: pd.Timestamp | None = None
        self._previous_close: float | None = None

    @property
    def visible_rows(self) -> int:
        return len(self._bars)

    @property
    def max_visible_time(self) -> pd.Timestamp | None:
        return self._last_visible_time

    def ingest(self, released: pd.DataFrame, decision_cutoff: Any) -> None:
        cutoff = pd.Timestamp(decision_cutoff)
        for row in released.to_dict(orient="records"):
            timestamp = pd.Timestamp(row["time_utc"])
            if timestamp >= cutoff:
                raise RuntimeError("FUTURE ROW MATERIALIZED IN DECISION STATE")
            if self._last_visible_time is not None and timestamp < self._last_visible_time:
                raise RuntimeError("DECISION STATE CHRONOLOGY VIOLATION")
            open_price = float(row["open"])
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            if self._previous_close is None:
                true_range = high - low
            else:
                true_range = max(
                    high - low,
                    abs(high - self._previous_close),
                    abs(low - self._previous_close),
                )
            stored = {
                "time_utc": timestamp,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "_true_range": float(true_range),
            }
            position = len(self._bars)
            self._bars.append(stored)
            self._positions.setdefault(timestamp, []).append(position)
            self._day_rows.setdefault(timestamp.normalize(), []).append(stored)
            self._previous_close = close
            self._last_visible_time = timestamp

    def finalize_daily_closes_before(self, decision_date: Any) -> None:
        decision_date = pd.Timestamp(decision_date).normalize()
        eligible_dates = sorted(
            date
            for date in self._day_rows
            if date < decision_date and date not in self._finalized_daily_dates
        )
        for date in eligible_dates:
            day = pd.DataFrame(self._day_rows[date]).drop(columns="_true_range")
            classified = build_valid_daily_sequence(day)
            record = dict(classified.loc[date])
            record["date_utc"] = date
            self._daily_records.append(record)
            self._finalized_daily_dates.add(date)

    def daily_frame(self) -> pd.DataFrame:
        if not self._daily_records:
            columns = [
                "valid",
                "exclusion_reason",
                "distinct_h1_opens",
                "row_count",
                "daily_close",
                "close_time_utc",
            ]
            return pd.DataFrame(columns=columns, index=pd.DatetimeIndex([], name="date_utc"))
        return (
            pd.DataFrame(self._daily_records)
            .set_index("date_utc")
            .sort_index(kind="mergesort")
        )

    def current_day_frame(self, decision_date: Any) -> pd.DataFrame:
        date = pd.Timestamp(decision_date).normalize()
        rows = self._day_rows.get(date, [])
        if not rows:
            return pd.DataFrame(columns=["time_utc", "open", "high", "low", "close"])
        return pd.DataFrame(rows).drop(columns="_true_range")

    def atr20_at_decision(self, decision_date: Any) -> dict:
        decision_date = pd.Timestamp(decision_date).normalize()
        source_time = decision_date + pd.Timedelta(hours=11)
        positions = self._positions.get(source_time, [])
        if not positions:
            return {"value": None, "reason": "MISSING_ATR20_SOURCE_BAR", "source_time_utc": None}
        if len(positions) != 1:
            return {"value": None, "reason": "DUPLICATE_ATR20_SOURCE_BAR", "source_time_utc": None}
        position = positions[0]
        tail21 = self._bars[max(0, position - 20) : position + 1]
        timestamps = [row["time_utc"] for row in tail21]
        if len(timestamps) != len(set(timestamps)):
            return {"value": None, "reason": "AMBIGUOUS_ATR20_SEQUENCE", "source_time_utc": None}
        tail20 = tail21[-20:]
        if len(tail20) < 20:
            return {"value": None, "reason": "INSUFFICIENT_OR_INVALID_ATR20", "source_time_utc": None}
        frame = pd.DataFrame(tail20)
        if not bool(_valid_ohlc_mask(frame).all()):
            return {"value": None, "reason": "INSUFFICIENT_OR_INVALID_ATR20", "source_time_utc": None}
        value = float(np.mean([row["_true_range"] for row in tail20]))
        if not np.isfinite(value) or value <= 0:
            return {"value": None, "reason": "NONPOSITIVE_ATR20", "source_time_utc": None}
        return {"value": value, "reason": None, "source_time_utc": _iso(source_time)}


def arm_eligibility(base_eligible: bool, m252: int | None, m6: int | None) -> dict:
    m252_ok = bool(base_eligible and m252 in (-1, 1))
    m6_ok = bool(base_eligible and m6 in (-1, 1))
    return {
        "control_m252_eligible": m252_ok,
        "control_m6_eligible": m6_ok,
        "challenger_stack_eligible": bool(m252_ok and m6_ok and m252 == m6),
        "negative_disagree_eligible": bool(m252_ok and m6_ok and m252 == -m6),
    }


def assert_outcome_blind_ledger(ledger: pd.DataFrame) -> None:
    for column in ledger.columns:
        lowered = str(column).lower()
        if any(token in lowered for token in FORBIDDEN_LEDGER_TOKENS):
            raise RuntimeError(f"OUTCOME COLUMN FORBIDDEN: {column}")


def _freeze_opportunity_row(row: dict) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def _frozen_rows_sha256(rows: list[str]) -> str:
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest().upper()


def build_opportunity_ledger(
    cursor: CausalParquetCursor,
    design_start: Any = DESIGN_START,
    validation_start: Any = VALIDATION_START,
    holdout_start: Any = HOLDOUT_START,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Advance a causal clock and freeze each opportunity before the next step."""
    design_start = pd.Timestamp(design_start).normalize()
    validation_start = pd.Timestamp(validation_start).normalize()
    holdout_start = pd.Timestamp(holdout_start).normalize()
    if not design_start < validation_start < holdout_start:
        raise ValueError("INVALID SPLIT BOUNDS")

    state = CausalTrendStackState()
    frozen_rows: list[str] = []
    access_traces: list[dict] = []
    for decision_sequence, decision_date in enumerate(
        pd.date_range(design_start, holdout_start, inclusive="left", freq="D"),
        start=1,
    ):
        cutoff = decision_date + pd.Timedelta(hours=12)
        prior_digest = _frozen_rows_sha256(frozen_rows)
        released, trace = cursor.advance_to(cutoff)
        state.ingest(released, cutoff)
        if _frozen_rows_sha256(frozen_rows) != prior_digest:
            raise RuntimeError("FINALIZED OPPORTUNITY MUTATED AFTER CLOCK ADVANCE")
        if state.max_visible_time is not None and state.max_visible_time >= cutoff:
            raise RuntimeError("DECISION STATE CONTAINS A FUTURE ROW")
        state.finalize_daily_closes_before(decision_date)
        daily = state.daily_frame()
        split = "DESIGN" if decision_date < validation_start else "VALIDATION"
        m252 = compute_m252(daily, decision_date)
        m6 = compute_m6(state.current_day_frame(decision_date), decision_date)
        atr = state.atr20_at_decision(decision_date)

        if m252["direction"] not in (-1, 1):
            base_reason = m252["reason"]
        elif m6["direction"] is None:
            base_reason = m6["reason"]
        elif atr["reason"] is not None:
            base_reason = atr["reason"]
        else:
            base_reason = None
        base_eligible = base_reason is None
        arms = arm_eligibility(base_eligible, m252["direction"], m6["direction"])
        if not base_eligible:
            challenger_reason = base_reason
        elif m6["direction"] == 0:
            challenger_reason = "M6_EQUALITY"
        elif arms["challenger_stack_eligible"]:
            challenger_reason = None
        else:
            challenger_reason = "M252_M6_DISAGREE"

        for source in (m6["last_source_time_utc"], atr["source_time_utc"]):
            if source is not None and pd.Timestamp(source) >= cutoff:
                raise RuntimeError(f"CURRENT-DAY CAUSALITY VIOLATION: {source} >= {cutoff}")

        row = {
            "hypothesis_id": HYPOTHESIS_ID,
            "plan_sha256": PLAN_SHA256,
            "opportunity_id": str(decision_date.date()),
            "split": split,
            "decision_time_utc": _iso(cutoff),
            "access_rows_released": trace["rows_released"],
            "access_cumulative_visible_rows": trace["cumulative_visible_rows"],
            "access_max_visible_time_utc": trace["max_visible_time_utc"],
            "access_causal_pass": trace["causal_pass"],
            "prior_finalized_rows_immutable": True,
            "valid_daily_closes_before": m252["valid_closes_before"],
            "m252_direction": m252["direction"],
            "m252_label": _direction_label(m252["direction"]),
            "m252_reason": m252["reason"],
            "m252_oldest_source_date": m252["oldest_source_date"],
            "m252_latest_source_date": m252["latest_source_date"],
            "m6_direction": m6["direction"],
            "m6_label": _direction_label(m6["direction"]),
            "m6_reason": m6["reason"],
            "m6_first_source_time_utc": m6["first_source_time_utc"],
            "m6_last_source_time_utc": m6["last_source_time_utc"],
            "atr20": atr["value"],
            "atr20_reason": atr["reason"],
            "atr20_source_time_utc": atr["source_time_utc"],
            "base_eligible": base_eligible,
            "base_exclusion_reason": base_reason,
            "alignment": (
                bool(m252["direction"] == m6["direction"])
                if m252["direction"] in (-1, 1) and m6["direction"] in (-1, 1)
                else None
            ),
            **arms,
            "challenger_rejection_reason": challenger_reason,
        }
        snapshot_payload = _freeze_opportunity_row(row)
        row["opportunity_snapshot_sha256"] = hashlib.sha256(
            snapshot_payload.encode("utf-8")
        ).hexdigest().upper()
        frozen_rows.append(_freeze_opportunity_row(row))
        access_traces.append(
            {
                "decision_sequence": decision_sequence,
                **trace,
                "prior_finalized_rows_immutable": True,
            }
        )
    ledger = pd.DataFrame(
        [json.loads(payload) for payload in frozen_rows], columns=LEDGER_COLUMNS
    )
    assert_outcome_blind_ledger(ledger)
    if ledger["opportunity_id"].duplicated().any():
        raise RuntimeError("DUPLICATE OPPORTUNITY ID")
    access_trace_sha256 = hashlib.sha256(
        _json_bytes({"decision_access_trace": access_traces})
    ).hexdigest().upper()
    access_summary = {
        "access_contract": "CAUSAL_BOUNDED_STREAM_V1",
        "decision_count": int(len(access_traces)),
        "causal_decisions_passed": int(sum(bool(row["causal_pass"]) for row in access_traces)),
        "immutable_prior_row_rechecks_passed": int(
            sum(bool(row["prior_finalized_rows_immutable"]) for row in access_traces)
        ),
        "access_trace_sha256": access_trace_sha256,
        "access_trace_storage": "opportunity_ledger.csv per-decision access_* columns",
        "cursor_receipt": cursor.receipt(),
    }
    return ledger, state.daily_frame(), access_summary


def evaluate_stage0_gates(ledger: pd.DataFrame) -> dict:
    split_counts: dict[str, dict] = {}
    gates: dict[str, dict] = {}
    for split, limits in SPLIT_LIMITS.items():
        eligible = ledger.loc[
            (ledger["split"] == split) & ledger["challenger_stack_eligible"].astype(bool)
        ]
        count = int(len(eligible))
        longs = int((eligible["m252_direction"] == 1).sum())
        shorts = int((eligible["m252_direction"] == -1).sum())
        split_counts[split] = {"challenger": count, "long": longs, "short": shorts}
        gates[f"{split.lower()}_challenger_count"] = {
            "passed": limits["minimum"] <= count <= limits["maximum"],
            "actual": count,
            "minimum": limits["minimum"],
            "maximum": limits["maximum"],
        }
        gates[f"{split.lower()}_long_coverage"] = {
            "passed": longs >= MIN_DIRECTION_COUNT,
            "actual": longs,
            "minimum": MIN_DIRECTION_COUNT,
        }
        gates[f"{split.lower()}_short_coverage"] = {
            "passed": shorts >= MIN_DIRECTION_COUNT,
            "actual": shorts,
            "minimum": MIN_DIRECTION_COUNT,
        }
    failures = [name for name, gate in gates.items() if not gate["passed"]]
    return {
        "verdict": "PASS" if not failures else "PARK",
        "verdict_reason": (
            "FROZEN_STAGE0_OBSERVATION_GATES_PASS"
            if not failures
            else "FROZEN_STAGE0_OBSERVATION_GATE_FAILURE"
        ),
        "failed_gates": failures,
        "gates": gates,
        "split_counts": split_counts,
    }


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_new(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)


def write_stage0_artifacts(
    output_dir: Path,
    ledger: pd.DataFrame,
    result: dict,
    replace_invalid: bool = False,
) -> dict[str, Path]:
    """Hash-bind artifacts; replace only when explicitly repairing invalid evidence."""
    output_dir = Path(output_dir)
    ledger_path = output_dir / "opportunity_ledger.csv"
    result_path = output_dir / "stage0_result.json"
    receipt_path = output_dir / "reconciliation_receipt.json"
    targets = (ledger_path, result_path, receipt_path)
    if not replace_invalid:
        for path in targets:
            if path.exists():
                raise FileExistsError(f"IMMUTABLE STAGE0 ARTIFACT EXISTS: {path}")
    if result.get("outcomes_opened") is not False or result.get("holdout_opened") is not False:
        raise RuntimeError("OUTCOME/HOLDOUT ATTESTATION MUST BE FALSE")
    assert_outcome_blind_ledger(ledger)
    output_dir.mkdir(parents=True, exist_ok=True)

    if replace_invalid:
        write_paths = tuple(path.with_name(f".{path.name}.causal-repair.tmp") for path in targets)
        for path in write_paths:
            if path.exists():
                raise FileExistsError(f"STALE CAUSAL REPAIR TEMP EXISTS: {path}")
    else:
        write_paths = targets
    write_ledger, write_result, write_receipt = write_paths

    ledger_bytes = ledger.to_csv(index=False, lineterminator="\n").encode("utf-8")
    _write_new(write_ledger, ledger_bytes)
    ledger_hash = sha256_file(write_ledger)

    stored_result = dict(result)
    stored_result["artifacts"] = {
        "opportunity_ledger": "opportunity_ledger.csv",
        "opportunity_ledger_rows": int(len(ledger)),
        "opportunity_ledger_sha256": ledger_hash,
        "reconciliation_receipt": "reconciliation_receipt.json",
    }
    _write_new(write_result, _json_bytes(stored_result))
    result_hash = sha256_file(write_result)

    access_proof = stored_result.get("causal_access_proof", {})
    receipt = {
        "schema_version": "trendstack_stage0_reconciliation.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "plan_sha256": stored_result.get("plan_sha256"),
        "data_sha256": stored_result.get("data_hashes", {}).get("h1"),
        "scanner_sha256": stored_result.get("scanner_sha256"),
        "opportunity_ledger_rows": int(len(ledger)),
        "opportunity_ids_unique": bool(not ledger["opportunity_id"].duplicated().any()),
        "opportunity_ledger_sha256": ledger_hash,
        "stage0_result_sha256": result_hash,
        "access_contract": access_proof.get("access_contract"),
        "access_trace_sha256": access_proof.get("access_trace_sha256"),
        "causal_decisions_passed": access_proof.get("causal_decisions_passed"),
        "immutable_prior_row_rechecks_passed": access_proof.get(
            "immutable_prior_row_rechecks_passed"
        ),
        "max_visible_strictly_before_every_cutoff": access_proof.get(
            "max_visible_strictly_before_every_cutoff"
        ),
        "m1_opened": False,
        "outcomes_opened": False,
        "holdout_opened": False,
        "reconciled": True,
    }
    _write_new(write_receipt, _json_bytes(receipt))
    if replace_invalid:
        for temporary, target in zip(write_paths, targets):
            temporary.replace(target)
    return {
        "ledger_path": ledger_path,
        "result_path": result_path,
        "receipt_path": receipt_path,
    }


def _count_reasons(series: pd.Series) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in series.dropna()).items()))


def _arm_counts(ledger: pd.DataFrame) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for split in ("DESIGN", "VALIDATION"):
        part = ledger.loc[ledger["split"] == split]
        result[split] = {
            column: int(part[column].astype(bool).sum())
            for column in (
                "control_m252_eligible",
                "control_m6_eligible",
                "challenger_stack_eligible",
                "negative_disagree_eligible",
            )
        }
    return result


def run_stage0(
    data_path: Path, output_dir: Path, replace_invalid: bool = False
) -> dict:
    plan_path = WORKSPACE / PLAN_REL
    actual_plan_hash = sha256_file(plan_path)
    if actual_plan_hash != PLAN_SHA256:
        raise RuntimeError(
            f"FROZEN PLAN HASH MISMATCH: expected={PLAN_SHA256} actual={actual_plan_hash}"
        )

    manifest_path = WORKSPACE / MANIFEST_REL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    h1_manifest_rows = [row for row in manifest.get("files", []) if row.get("file") == Path(DATA_REL).name]
    if len(h1_manifest_rows) != 1 or h1_manifest_rows[0].get("sha256") != DATA_SHA256:
        raise RuntimeError("MANIFEST H1 HASH CONTRACT MISMATCH")

    cursor = CausalParquetCursor(Path(data_path), DATA_SHA256)
    ledger, daily, access_summary = build_opportunity_ledger(cursor)
    gate_result = evaluate_stage0_gates(ledger)

    visible = pd.to_datetime(ledger["access_max_visible_time_utc"])
    cutoffs = pd.to_datetime(ledger["decision_time_utc"])
    max_visible_before_cutoff = bool((visible.dropna() < cutoffs[visible.notna()]).all())
    if not max_visible_before_cutoff or not bool(ledger["access_causal_pass"].all()):
        raise RuntimeError("PER-DECISION CAUSAL ACCESS RECONCILIATION FAILED")
    cursor_receipt = access_summary["cursor_receipt"]

    daily_exclusions = _count_reasons(daily.loc[~daily["valid"], "exclusion_reason"])
    result = {
        "schema_version": "trendstack_stage0_outcome_blind.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "stage": "STAGE0_H1_OBSERVATION_ONLY",
        "verdict": gate_result["verdict"],
        "verdict_reason": gate_result["verdict_reason"],
        "failed_gates": gate_result["failed_gates"],
        "plan_path": PLAN_REL,
        "plan_sha256": actual_plan_hash,
        "scanner_path": str(Path(__file__).resolve().relative_to(WORKSPACE)).replace("\\", "/"),
        "scanner_sha256": sha256_file(Path(__file__).resolve()),
        "manifest_path": MANIFEST_REL,
        "manifest_sha256": sha256_file(manifest_path),
        "data_path": str(Path(data_path).resolve().relative_to(WORKSPACE)).replace("\\", "/"),
        "data_hashes": {"h1": DATA_SHA256},
        "load_receipt": cursor_receipt,
        "split_windows": {
            "DESIGN": {"start": "2016-01-04", "end_exclusive": "2021-01-01"},
            "VALIDATION": {"start": "2021-01-01", "end_exclusive": "2023-01-01"},
            "HOLDOUT": {"start": "2023-01-01", "opened": False},
        },
        "data_quality": {
            "h1_rows_released_to_decision_state": int(
                cursor_receipt["rows_returned_to_decision_state"]
            ),
            "first_h1_bar_released": cursor_receipt["first_row_returned"],
            "last_h1_bar_released": cursor_receipt["last_row_returned"],
            "duplicate_utc_opens_in_finalized_days": int(
                (daily["row_count"] - daily["distinct_h1_opens"]).clip(lower=0).sum()
            ),
            "valid_daily_closes": int(daily["valid"].sum()),
            "invalid_daily_closes": int((~daily["valid"]).sum()),
            "daily_exclusion_counts": daily_exclusions,
        },
        "opportunity_reconciliation": {
            "calendar_rows": int(len(ledger)),
            "base_eligible": int(ledger["base_eligible"].astype(bool).sum()),
            "base_exclusion_counts": _count_reasons(ledger["base_exclusion_reason"]),
            "challenger_rejection_counts": _count_reasons(ledger["challenger_rejection_reason"]),
            "arm_counts": _arm_counts(ledger),
            "split_direction_counts": gate_result["split_counts"],
        },
        "gates": gate_result["gates"],
        "causal_access_proof": {
            **access_summary,
            "max_visible_strictly_before_every_cutoff": max_visible_before_cutoff,
            "full_frame_materialization": False,
            "per_decision_trace_columns": [
                "decision_time_utc",
                "access_rows_released",
                "access_cumulative_visible_rows",
                "access_max_visible_time_utc",
                "access_causal_pass",
                "prior_finalized_rows_immutable",
                "opportunity_snapshot_sha256",
            ],
            "future_rows_returned_to_decision_state": 0,
            "holdout_rows_returned_to_decision_state": int(
                cursor_receipt["holdout_rows_returned"]
            ),
        },
        "causality_attestation": {
            "decision_clock": "12:00:00 UTC",
            "latest_current_day_h1_input": "11:00:00 UTC",
            "m252_uses_dates_strictly_before_opportunity": True,
            "row_at_or_after_decision_cutoff_returned_to_state": False,
            "prior_opportunity_rows_mutated_after_finalization": False,
        },
        "completed_entry_observation": {
            "opened": False,
            "reason": "M1_FORBIDDEN_IN_STAGE0_H1_ONLY",
            "DESIGN": None,
            "VALIDATION": None,
        },
        "m1_opened": False,
        "outcomes_opened": False,
        "holdout_opened": False,
        "economic_metrics_computed": False,
        "promotion_eligible": False,
    }
    written = write_stage0_artifacts(
        output_dir, ledger, result, replace_invalid=replace_invalid
    )
    stored = json.loads(written["result_path"].read_text(encoding="utf-8"))
    return stored


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=WORKSPACE / DATA_REL)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            WORKSPACE
            / "03. EA Developer"
            / "EA_TrendStackContinuation"
            / "research"
            / "evidence"
            / "HYP-TRENDSTACK-EURUSD-H1-001_STAGE0"
        ),
    )
    parser.add_argument(
        "--replace-invalid-evidence",
        action="store_true",
        help="Atomically replace the three known-invalid Stage-0 artifacts.",
    )
    args = parser.parse_args()
    artifact = run_stage0(
        args.data,
        args.output_dir,
        replace_invalid=args.replace_invalid_evidence,
    )
    print(
        json.dumps(
            {
                "verdict": artifact["verdict"],
                "DESIGN": artifact["opportunity_reconciliation"]["split_direction_counts"]["DESIGN"],
                "VALIDATION": artifact["opportunity_reconciliation"]["split_direction_counts"]["VALIDATION"],
                "outcomes_opened": artifact["outcomes_opened"],
                "holdout_opened": artifact["holdout_opened"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
