#!/usr/bin/env python3
"""Frozen HYP011 Stage-0 first-passage identity probe.

This module is outcome-blind by construction: it reconstructs closed-bar
decision state only, writes deterministic decision ledgers, and rejects paths or
schemas that look like lifecycle/report/case/outcome evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
CLOCK_PATH = ROOT / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
M1_PATH = ROOT / "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
H1_PATH = ROOT / "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet"
TELEMETRY_PATH = ROOT / "02. AlphaFactory/runs/EA_VRAS_VolatilityNormalizedStop/20260722_233420/analysis/logs/EURUSD_DecisionTelemetry_HYP-VRAS-EURUSD-M5-008_188132734.csv"
sys.path.insert(0, str(CLOCK_PATH.parent))
from fivepercent_server_clock import server_to_utc  # noqa: E402


HYPOTHESIS_ID = "HYP-VRAS-EURUSD-M5-011"
PLAN_SHA256 = "4C3091C1C7A28FB48778B7B4510E22FD1AC6552EA95B4713C21303ED1CC237F2"
M1_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
H1_SHA256 = "71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
TELEMETRY_SHA256 = "C510692DB20D710D92FCDE52C8628B158D98AAFE00BD3211E5E36E74254EDF66"

DISCOVERY_START = pd.Timestamp("2019-01-01 00:00:00")
DISCOVERY_END = pd.Timestamp("2022-12-31 23:59:59")
DISCOVERY_END_EXCLUSIVE = pd.Timestamp("2023-01-01 00:00:00")
M5_DELTA = pd.Timedelta(minutes=5)
H1_DELTA = pd.Timedelta(hours=1)
PARITY_TOLERANCE = 5.1e-6

FORBIDDEN_PATH_PATTERNS = (
    "lifecycle",
    "report",
    "casebook",
    "random100",
    "random-100",
    "random_sample",
    "random-sample",
    "anatomy",
)
FORBIDDEN_COLUMN_RE = re.compile(
    r"(^|[_\s-])("
    r"exit|outcome|profit|pnl|p_l|pl|net|return|mfe|mae|drawdown|"
    r"sl|tp|stop|target|takeprofit|stoploss|balance|equity|deal"
    r")($|[_\s-])",
    re.IGNORECASE,
)
BOUND_TELEMETRY_SCHEMA = (
    "server_time",
    "variant",
    "status",
    "direction",
    "h1_close",
    "h1_ema",
    "rolling_vwap_48",
    "atr14",
    "entry",
    "stop",
    "target",
    "spread_pips",
)
PARITY_TELEMETRY_FIELDS = (
    "server_time",
    "status",
    "direction",
    "h1_close",
    "h1_ema",
    "rolling_vwap_48",
    "atr14",
)


class ContractViolation(ValueError):
    """Raised when the frozen HYP011 safety contract is violated."""


@dataclass(frozen=True)
class Candidate:
    origin_id: str
    origin_time: pd.Timestamp
    origin_close_time: pd.Timestamp
    origin_utc: datetime
    direction: int
    frozen_l: float
    reclaim_high: float
    reclaim_low: float
    h1_direction: int
    hold_time: pd.Timestamp | None = None
    pair_extreme: float | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def assert_expected_hash(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected.upper():
        raise ContractViolation(f"SHA256 mismatch for {path}: {actual} != {expected.upper()}")


def assert_exact_path(actual: Path, expected: Path) -> None:
    actual_key = os.path.normcase(str(actual.resolve()))
    expected_key = os.path.normcase(str(expected.resolve()))
    if actual_key != expected_key:
        raise ContractViolation(f"non-canonical input path: {actual} != {expected}")


def assert_allowed_path(path: Path) -> None:
    lowered = str(path).replace("\\", "/").lower()
    for pattern in FORBIDDEN_PATH_PATTERNS:
        if pattern in lowered:
            raise ContractViolation(f"forbidden outcome-adjacent path: {path}")
    if "decisiontelemetry" in lowered:
        return
    if "lifecycletrades" in lowered or "report.html" in lowered:
        raise ContractViolation(f"forbidden run artifact path: {path}")


def assert_allowed_schema(columns: Iterable[str]) -> None:
    bad = [col for col in columns if FORBIDDEN_COLUMN_RE.search(str(col).strip().lower())]
    if bad:
        raise ContractViolation(f"forbidden post-decision schema fields: {bad}")


def parse_server_time(value: Any) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value.tz_convert(None) if value.tzinfo else value
    text = str(value).strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt))
        except ValueError:
            pass
    parsed = pd.to_datetime(text)
    return parsed.tz_convert(None) if getattr(parsed, "tzinfo", None) else pd.Timestamp(parsed)


def to_utc(ts_server: pd.Timestamp) -> datetime:
    return server_to_utc(ts_server.to_pydatetime())


def in_session(ts_server_close: pd.Timestamp) -> bool:
    return in_session_utc(to_utc(ts_server_close))


def in_session_utc(utc: datetime) -> bool:
    minute = utc.hour * 60 + utc.minute
    return 7 * 60 <= minute < 16 * 60 + 30


def same_utc_day(a: datetime, b: datetime) -> bool:
    return a.date() == b.date()


def mt5_ema(series: pd.Series, period: int) -> pd.Series:
    return series.astype(float).ewm(span=period, adjust=False).mean()


def mt5_atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous = frame["close"].shift(1)
    tr = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous).abs(),
            (frame["low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def build_m5_from_m1(m1: pd.DataFrame) -> pd.DataFrame:
    required = {"time_server", "open", "high", "low", "close", "tick_volume"}
    missing = required - set(m1.columns)
    if missing:
        raise ContractViolation(f"M1 bars missing columns: {sorted(missing)}")
    data = m1[list(required)].copy()
    data["time_server"] = pd.to_datetime(data["time_server"])
    data.sort_values("time_server", inplace=True, ignore_index=True)
    if data["time_server"].duplicated().any():
        raise ContractViolation("duplicated M1 timestamp")
    bucket = data["time_server"].dt.floor("5min")
    minute_offset = ((data["time_server"] - bucket) / pd.Timedelta(minutes=1)).astype(int)
    minute_aligned = data["time_server"] == bucket + minute_offset * pd.Timedelta(minutes=1)
    data["minute_bit"] = [1 << int(value) if 0 <= int(value) <= 4 else 0 for value in minute_offset]
    data["minute_aligned"] = minute_aligned.astype(int)
    indexed = data.set_index("time_server", drop=False)
    grouped = indexed.resample("5min", label="left", closed="left")
    m5 = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        minute_count=("close", "count"),
        minute_mask=("minute_bit", "sum"),
        aligned_count=("minute_aligned", "sum"),
    )
    m5 = m5[m5["minute_count"] > 0].copy()
    m5["contiguous_m1"] = (
        (m5["minute_count"] == 5)
        & (m5["minute_mask"] == 31)
        & (m5["aligned_count"] == 5)
    )
    m5.drop(columns=["minute_mask", "aligned_count"], inplace=True)
    complete = m5["contiguous_m1"].astype(bool)
    typical = ((m5["high"] + m5["low"] + m5["close"]) / 3.0).where(complete)
    volume = m5["tick_volume"].astype(float).where(complete)
    denom = volume.rolling(48).sum()
    m5["vwap48"] = (typical * volume).rolling(48).sum() / denom
    m5.loc[denom <= 0.0, "vwap48"] = math.nan
    indicator_bars = m5[["high", "low", "close"]].where(complete)
    m5["atr14"] = mt5_atr(indicator_bars, 14)
    return m5


def prepare_h1(h1: pd.DataFrame) -> pd.DataFrame:
    required = {"time_server", "close"}
    missing = required - set(h1.columns)
    if missing:
        raise ContractViolation(f"H1 bars missing columns: {sorted(missing)}")
    out = h1.copy()
    out["time_server"] = pd.to_datetime(out["time_server"])
    out.sort_values("time_server", inplace=True, ignore_index=True)
    if out["time_server"].duplicated().any():
        raise ContractViolation("duplicated H1 timestamp")
    out["ema200"] = mt5_ema(out["close"], 200)
    out.set_index("time_server", inplace=True, drop=False)
    return out


def closed_h1_at(h1: pd.DataFrame, m5_close_time: pd.Timestamp) -> pd.Series | None:
    cutoff = m5_close_time - H1_DELTA
    position = int(h1.index.searchsorted(cutoff, side="right")) - 1
    if position < 0:
        return None
    return h1.iloc[position]


def h1_bias(row: pd.Series | None) -> int:
    if row is None:
        return 0
    close = float(row["close"])
    ema = float(row["ema200"])
    if not math.isfinite(close) or not math.isfinite(ema) or close == ema:
        return 0
    return 1 if close > ema else -1


def is_long_reclaim(row: pd.Series, previous: pd.Series) -> bool:
    level = float(row["vwap48"])
    return float(previous["close"]) <= level and float(row["low"]) <= level and float(row["close"]) > level


def is_short_reclaim(row: pd.Series, previous: pd.Series) -> bool:
    level = float(row["vwap48"])
    return float(previous["close"]) >= level and float(row["high"]) >= level and float(row["close"]) < level


def direction_name(direction: int) -> str:
    return "LONG" if direction > 0 else "SHORT"


def origin_id(ts: pd.Timestamp, direction: int) -> str:
    return f"{ts.strftime('%Y%m%d%H%M')}_{direction_name(direction)}"


def comparator_immediate(row: pd.Series, previous: pd.Series, direction: int) -> bool:
    if direction > 0:
        return float(row["close"]) > float(previous["high"])
    return float(row["close"]) < float(previous["low"])


def comparator_one_bar(row: pd.Series, hold: pd.Series, direction: int, level: float, h1_same: bool) -> bool:
    if not h1_same:
        return False
    if direction > 0:
        return float(hold["close"]) > level and float(hold["close"]) > float(row["high"])
    return float(hold["close"]) < level and float(hold["close"]) < float(row["low"])


def _finite_bar(row: pd.Series, names: Iterable[str]) -> bool:
    return all(math.isfinite(float(row[name])) for name in names)


def run_stage0_fsm(m5: pd.DataFrame, h1: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Evaluate the frozen FSM over already reconstructed M5 and prepared H1 bars."""
    m5 = m5.sort_index().copy()
    h1 = h1.sort_index().copy()
    if m5.index.duplicated().any():
        raise ContractViolation("duplicated M5 timestamp")

    events: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()
    accepted_lags: list[int] = []
    accepted_origins: set[str] = set()
    immediate_origins: set[str] = set()
    one_bar_origins: set[str] = set()
    direction_counts: Counter[str] = Counter()
    candidate: Candidate | None = None
    prior_time: pd.Timestamp | None = None

    rows = list(m5.iterrows())
    for idx, (ts, row) in enumerate(rows):
        close_time = ts + M5_DELTA
        contiguous = bool(row.get("contiguous_m1", True)) and (
            prior_time is None or ts - prior_time == M5_DELTA
        )
        if not contiguous:
            counters["data_gap_reset"] += 1
            candidate = None
        prior_time = ts

        h1_row = closed_h1_at(h1, close_time)
        bias = h1_bias(h1_row)
        utc_close = to_utc(close_time)
        session_ok = in_session_utc(utc_close)
        current_valid = contiguous and _finite_bar(row, ("open", "high", "low", "close", "vwap48"))

        if candidate is not None:
            elapsed = int((ts - candidate.origin_time) / M5_DELTA)
            same_day = same_utc_day(candidate.origin_utc, utc_close)
            if not current_valid:
                counters["data_gap_reset"] += 1
                candidate = None
            elif not session_ok or not same_day:
                counters["session_expiry"] += 1
                candidate = None
            elif bias != candidate.h1_direction:
                counters["h1_flip"] += 1
                candidate = None
            elif candidate.hold_time is None:
                expected_hold = ts - candidate.origin_time == M5_DELTA
                hold_side = (
                    float(row["close"]) > candidate.frozen_l
                    if candidate.direction > 0
                    else float(row["close"]) < candidate.frozen_l
                )
                if expected_hold and hold_side:
                    if comparator_one_bar(
                        row=candidate_to_origin_row(candidate),
                        hold=row,
                        direction=candidate.direction,
                        level=candidate.frozen_l,
                        h1_same=True,
                    ):
                        one_bar_origins.add(candidate.origin_id)
                    pair_extreme = (
                        max(candidate.reclaim_high, float(row["high"]))
                        if candidate.direction > 0
                        else min(candidate.reclaim_low, float(row["low"]))
                    )
                    candidate = Candidate(
                        **{
                            **candidate.__dict__,
                            "hold_time": ts,
                            "pair_extreme": pair_extreme,
                        }
                    )
                    counters["hold_pass"] += 1
                else:
                    counters["hold_fail"] += 1
                    candidate = None
            elif elapsed >= 48:
                counters["expiry_48_bar"] += 1
                candidate = None
            elif candidate.direction > 0 and float(row["close"]) <= candidate.frozen_l:
                counters["vwap_recross_invalidation"] += 1
                candidate = None
            elif candidate.direction < 0 and float(row["close"]) >= candidate.frozen_l:
                counters["vwap_recross_invalidation"] += 1
                candidate = None
            elif candidate.direction > 0 and float(row["close"]) > float(candidate.pair_extreme):
                record = accepted_record(candidate, ts, close_time, utc_close, row, h1_row, elapsed)
                events.append(record)
                accepted_origins.add(candidate.origin_id)
                direction_counts[record["direction"]] += 1
                accepted_lags.append(elapsed)
                counters["first_passage_accept"] += 1
                candidate = None
            elif candidate.direction < 0 and float(row["close"]) < float(candidate.pair_extreme):
                record = accepted_record(candidate, ts, close_time, utc_close, row, h1_row, elapsed)
                events.append(record)
                accepted_origins.add(candidate.origin_id)
                direction_counts[record["direction"]] += 1
                accepted_lags.append(elapsed)
                counters["first_passage_accept"] += 1
                candidate = None

        if candidate is not None or idx == 0 or not current_valid or not session_ok:
            continue
        previous = rows[idx - 1][1]
        if (
            not bool(previous.get("contiguous_m1", True))
            or not _finite_bar(previous, ("high", "low", "close"))
            or bias == 0
        ):
            continue

        direction = 0
        if bias > 0 and is_long_reclaim(row, previous):
            direction = 1
        elif bias < 0 and is_short_reclaim(row, previous):
            direction = -1
        if direction == 0:
            continue

        oid = origin_id(ts, direction)
        counters["raw_reclaim"] += 1
        if comparator_immediate(row, previous, direction):
            immediate_origins.add(oid)
        candidate = Candidate(
            origin_id=oid,
            origin_time=ts,
            origin_close_time=close_time,
            origin_utc=utc_close,
            direction=direction,
            frozen_l=float(row["vwap48"]),
            reclaim_high=float(row["high"]),
            reclaim_low=float(row["low"]),
            h1_direction=bias,
        )

    summary = build_summary(counters, events, accepted_lags, direction_counts, accepted_origins, immediate_origins, one_bar_origins)
    return events, summary


def candidate_to_origin_row(candidate: Candidate) -> pd.Series:
    """Expose only the frozen reclaim extremes needed by the comparator."""
    return pd.Series({"high": candidate.reclaim_high, "low": candidate.reclaim_low})


def accepted_record(
    candidate: Candidate,
    decision_time: pd.Timestamp,
    decision_close_time: pd.Timestamp,
    decision_utc: datetime,
    row: pd.Series,
    h1_row: pd.Series | None,
    lag: int,
) -> dict[str, Any]:
    h1_close = float(h1_row["close"]) if h1_row is not None else math.nan
    h1_ema = float(h1_row["ema200"]) if h1_row is not None else math.nan
    return {
        "schema_version": "hyp011_stage0_event_ledger.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "origin_id": candidate.origin_id,
        "origin_time_server": candidate.origin_time.strftime("%Y-%m-%d %H:%M:%S"),
        "decision_time_server": decision_time.strftime("%Y-%m-%d %H:%M:%S"),
        "decision_close_server": decision_close_time.strftime("%Y-%m-%d %H:%M:%S"),
        "decision_close_utc": decision_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "direction": direction_name(candidate.direction),
        "frozen_vwap48": round(candidate.frozen_l, 10),
        "pair_extreme": round(float(candidate.pair_extreme), 10),
        "decision_close": round(float(row["close"]), 10),
        "h1_close": round(h1_close, 10),
        "h1_ema200": round(h1_ema, 10),
        "decision_lag_bars": lag,
        "resolution": "FIRST_PASSAGE_ACCEPT",
    }


def build_summary(
    counters: Counter[str],
    events: list[dict[str, Any]],
    accepted_lags: list[int],
    direction_counts: Counter[str],
    accepted_origins: set[str],
    immediate_origins: set[str],
    one_bar_origins: set[str],
) -> dict[str, Any]:
    by_year: dict[str, int] = Counter(row["decision_close_utc"][:4] for row in events)
    elapsed_weeks = (DISCOVERY_END_EXCLUSIVE - DISCOVERY_START).total_seconds() / (7 * 86400)
    per_year_weeks = {
        str(year): (pd.Timestamp(f"{year + 1}-01-01") - pd.Timestamp(f"{year}-01-01")).total_seconds()
        / (7 * 86400)
        for year in range(2019, 2023)
    }

    def jaccard(other: set[str]) -> float:
        union = accepted_origins | other
        return round(len(accepted_origins & other) / len(union), 9) if union else 0.0

    gates = {
        "accepted_events_gte_350": len(events) >= 350,
        "pooled_cadence_2_to_5": 2.0 <= len(events) / elapsed_weeks <= 5.0,
        "yearly_cadence_2_to_5": all(
            2.0 <= by_year.get(str(year), 0) / per_year_weeks[str(year)] <= 5.0
            for year in range(2019, 2023)
        ),
        "both_directions_gte_50": direction_counts.get("LONG", 0) >= 50 and direction_counts.get("SHORT", 0) >= 50,
        "jaccard_hyp008_lte_0_80": jaccard(immediate_origins) <= 0.80,
        "jaccard_one_bar_lte_0_80": jaccard(one_bar_origins) <= 0.80,
        "lag_ge_3_share_gte_20pct": (
            sum(1 for lag in accepted_lags if lag >= 3) / len(accepted_lags) >= 0.20
            if accepted_lags
            else False
        ),
    }
    return {
        "schema_version": "hyp011_stage0_summary.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "outcome_blind_attestation": True,
        "counts": {key: int(counters.get(key, 0)) for key in (
            "raw_reclaim",
            "hold_pass",
            "hold_fail",
            "first_passage_accept",
            "vwap_recross_invalidation",
            "h1_flip",
            "session_expiry",
            "expiry_48_bar",
            "data_gap_reset",
        )},
        "accepted_cadence_per_elapsed_week": round(len(events) / elapsed_weeks, 9),
        "accepted_cadence_by_year": {
            str(year): round(by_year.get(str(year), 0) / per_year_weeks[str(year)], 9)
            for year in range(2019, 2023)
        },
        "direction_counts": dict(direction_counts),
        "decision_lag_distribution": {str(k): int(v) for k, v in Counter(accepted_lags).items()},
        "origin_overlap": {
            "HYP008_IMMEDIATE": {
                "accepted": len(accepted_origins),
                "comparator": len(immediate_origins),
                "intersection": len(accepted_origins & immediate_origins),
                "jaccard": jaccard(immediate_origins),
            },
            "ONE_BAR_CONFIRM": {
                "accepted": len(accepted_origins),
                "comparator": len(one_bar_origins),
                "intersection": len(accepted_origins & one_bar_origins),
                "jaccard": jaccard(one_bar_origins),
            },
        },
        "gates": gates,
        "verdict": "STAGE0_IDENTITY_CADENCE_PASS" if all(gates.values()) else "PARK_STAGE0_IDENTITY_OR_CADENCE_FAIL",
    }


def select_first100_order_accepted(telemetry_path: Path) -> list[dict[str, str]]:
    assert_allowed_path(telemetry_path)
    assert_expected_hash(telemetry_path, TELEMETRY_SHA256)
    with telemetry_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise ContractViolation("empty decision telemetry")
        if tuple(header) != BOUND_TELEMETRY_SCHEMA:
            unexpected = [field for field in header if field not in BOUND_TELEMETRY_SCHEMA]
            if unexpected:
                assert_allowed_schema(unexpected)
            raise ContractViolation(f"decision telemetry schema mismatch: {header}")
        projected_indexes = {field: header.index(field) for field in PARITY_TELEMETRY_FIELDS}
        rows = []
        for file_index, values in enumerate(reader):
            if len(values) != len(header):
                raise ContractViolation(f"malformed decision telemetry row {file_index}")
            row = {field: values[index] for field, index in projected_indexes.items()}
            if row.get("status") == "ORDER_ACCEPTED":
                enriched = dict(row)
                enriched["_file_index"] = str(file_index)
                enriched["_parsed_server_time"] = parse_server_time(row["server_time"]).strftime("%Y-%m-%d %H:%M:%S")
                rows.append(enriched)
    rows.sort(key=lambda r: (r["_parsed_server_time"], normalize_direction(r.get("direction", "")), int(r["_file_index"])))
    return rows[:100]


def normalize_direction(value: Any) -> int:
    text = str(value).strip().upper()
    if text in {"1", "BUY", "LONG"}:
        return 1
    if text in {"-1", "SELL", "SHORT"}:
        return -1
    raise ContractViolation(f"unknown direction value: {value}")


def lookup_m5_row(m5: pd.DataFrame, close_time: pd.Timestamp) -> pd.Series:
    if (
        close_time.second != 0
        or close_time.microsecond != 0
        or close_time.minute % 5 != 0
    ):
        raise ContractViolation(f"telemetry timestamp is not an exact M5 boundary: {close_time}")
    open_time = close_time - M5_DELTA
    if open_time not in m5.index:
        raise ContractViolation(f"missing M5 decision bar for close {close_time}")
    return m5.loc[open_time]


def parity_first100(rows: list[dict[str, str]], m5: pd.DataFrame, h1: pd.DataFrame) -> dict[str, Any]:
    checked = 0
    max_deltas = {"h1_close": 0.0, "h1_ema200": 0.0, "vwap48": 0.0, "atr14": 0.0}
    for row in rows:
        server_time = parse_server_time(row["server_time"])
        m5_row = lookup_m5_row(m5, server_time)
        h1_row = closed_h1_at(h1, server_time)
        if h1_row is None:
            raise ContractViolation(f"missing closed H1 for telemetry {server_time}")
        expected_direction = h1_bias(h1_row)
        if expected_direction == 0:
            raise ContractViolation(f"non-finite or neutral H1 parity state at {server_time}")
        if normalize_direction(row["direction"]) != expected_direction:
            raise ContractViolation(f"direction parity fail at {server_time}")
        for field, actual in (
            ("h1_close", float(h1_row["close"])),
            ("h1_ema200", float(h1_row["ema200"])),
            ("vwap48", float(m5_row["vwap48"])),
            ("atr14", float(m5_row["atr14"])),
        ):
            telemetry_field = {
                "h1_ema200": "h1_ema",
                "vwap48": "rolling_vwap_48",
            }.get(field, field)
            if telemetry_field not in row:
                raise ContractViolation(f"missing telemetry parity field: {telemetry_field}")
            telemetry_value = float(row[telemetry_field])
            if not math.isfinite(actual) or not math.isfinite(telemetry_value):
                raise ContractViolation(f"non-finite {field} parity value at {server_time}")
            delta = abs(actual - telemetry_value)
            max_deltas[field] = max(max_deltas[field], delta)
            if delta > PARITY_TOLERANCE:
                raise ContractViolation(f"{field} parity delta {delta} exceeds tolerance at {server_time}")
        checked += 1
    return {"checked": checked, "passed": checked == 100, "max_deltas": max_deltas}


def write_json_deterministic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def deterministic_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_parquet(path: Path, expected_hash: str, columns: list[str]) -> pd.DataFrame:
    assert_allowed_path(path)
    assert_expected_hash(path, expected_hash)
    return pd.read_parquet(path, columns=columns)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m1", type=Path, default=M1_PATH)
    parser.add_argument("--h1", type=Path, default=H1_PATH)
    parser.add_argument(
        "--telemetry",
        type=Path,
        default=TELEMETRY_PATH,
    )
    parser.add_argument("--events-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assert_allowed_path(args.events_out)
    assert_allowed_path(args.summary_out)
    assert_exact_path(args.m1, M1_PATH)
    assert_exact_path(args.h1, H1_PATH)
    assert_exact_path(args.telemetry, TELEMETRY_PATH)
    plan = Path(__file__).with_name("HYP-VRAS-EURUSD-M5-011_STAGE0_PROBE_PLAN.md")
    assert_expected_hash(plan, PLAN_SHA256)
    assert_expected_hash(CLOCK_PATH, CLOCK_SHA256)
    m1 = load_parquet(args.m1, M1_SHA256, ["time_server", "open", "high", "low", "close", "tick_volume"])
    h1_raw = load_parquet(args.h1, H1_SHA256, ["time_server", "close"])
    m5 = build_m5_from_m1(m1)
    h1 = prepare_h1(h1_raw)
    telemetry_path = args.telemetry
    parity = parity_first100(select_first100_order_accepted(telemetry_path), m5, h1)
    view = m5[(m5.index >= DISCOVERY_START) & (m5.index < DISCOVERY_END_EXCLUSIVE)].copy()
    events, summary = run_stage0_fsm(view, h1)
    rerun_events, _ = run_stage0_fsm(view, h1)
    deterministic_rerun = deterministic_json_bytes(events) == deterministic_json_bytes(rerun_events)
    usable = view[
        view["contiguous_m1"].astype(bool)
        & view[["open", "high", "low", "close", "vwap48", "atr14"]].notna().all(axis=1)
    ]
    if usable.empty:
        raise ContractViolation("no usable discovery bars")
    summary["hashes"] = {
        "plan_sha256": PLAN_SHA256,
        "m1_sha256": M1_SHA256,
        "h1_sha256": H1_SHA256,
        "clock_sha256": CLOCK_SHA256,
        "decision_telemetry_sha256": TELEMETRY_SHA256,
        "probe_sha256": sha256_file(Path(__file__)),
    }
    summary["coverage"] = {
        "request_from_server": DISCOVERY_START.strftime("%Y-%m-%d %H:%M:%S"),
        "request_to_server_inclusive": DISCOVERY_END.strftime("%Y-%m-%d %H:%M:%S"),
        "reconstructed_m5_bars": int(len(view)),
        "usable_m5_bars": int(len(usable)),
        "first_usable_open_server": usable.index[0].strftime("%Y-%m-%d %H:%M:%S"),
        "first_usable_close_utc": to_utc(usable.index[0] + M5_DELTA).strftime("%Y-%m-%d %H:%M:%S"),
        "last_usable_open_server": usable.index[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "last_usable_close_utc": to_utc(usable.index[-1] + M5_DELTA).strftime("%Y-%m-%d %H:%M:%S"),
    }
    summary["parity_first100_order_accepted"] = parity
    summary["gates"]["parity_first100_order_accepted"] = parity["passed"]
    summary["gates"]["deterministic_event_ledger_rerun"] = deterministic_rerun
    summary["gates"]["effective_contract_hashes_verified"] = True
    summary["gates"]["outcome_blind_allowlist_projection"] = True
    summary["verdict"] = (
        "STAGE0_IDENTITY_CADENCE_PASS"
        if all(summary["gates"].values())
        else "PARK_STAGE0_IDENTITY_OR_CADENCE_FAIL"
    )
    write_json_deterministic(args.events_out, events)
    write_json_deterministic(args.summary_out, summary)
    print(json.dumps({"verdict": summary["verdict"], "events": len(events), "summary": str(args.summary_out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
