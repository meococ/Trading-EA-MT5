#!/usr/bin/env python3
"""Outcome-blind Stage-0 scanner for HYP-ROUND-CASCADE-EURUSD-M5-001.

Importing this module is inert.  The production path is deliberately disarmed:
it requires both ``--run-reviewed-stage0`` and an independently reviewed
registry-row SHA to replace ``REVIEWED_REGISTRY_ROW_SHA256``.  Stage-0 reads
only public DESIGN OHLC through the decision bar and never projects a next bar,
return, trade, PnL, or other economic outcome.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import io
import json
import math
import os
import re
import stat
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, Callable, Iterable, Mapping, Sequence


HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-001"
PACKAGE_NAME = "EA_RoundNumberCascade"
PLAN_REL = "03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-001_PROBE_PLAN.md"
FROZEN_PLAN_SHA256 = "AA8667AA33FD271289CD1C0477F9A61E1D44CE0060D71EF5766E7C5D788E934A"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
BUILDER_REL = "03. EA Developer/EA_RoundNumberCascade/research/build_round_cascade_001_source.py"
TEST_REL = "03. EA Developer/EA_RoundNumberCascade/research/tests/test_build_round_cascade_001_source.py"
INDEPENDENT_REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-001_INDEPENDENT_SOURCE_REVIEW_RECEIPT.json"
)
INDEPENDENT_REVIEW_SCHEMA = "round_cascade_independent_source_review.v1"
ATTEMPT_ID = "HYP001-SOURCE-PREFLIGHT-001"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-001_SOURCE_FEASIBILITY/"
    f"{ATTEMPT_ID}"
)
DESIGN_MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl"
DESIGN_RECEIPT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json"
SPLITVAULT_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002"

DESIGN_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
DESIGN_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
PUBLIC_M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"

# Independent review must replace this exact sentinel before a production scan.
REVIEWED_REGISTRY_ROW_SHA256: str | None = "767AB94EF6E52EAC7670CE4C81FFE7E8748C67A9E384E65DB834E8A8F9F7D4DA"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

UTC = timezone.utc
PIP = Decimal("0.0001")
QUOTE_POINT = Decimal("0.00001")
POINTS_PER_PIP = 10
DESIGN_START = datetime(2016, 1, 4, tzinfo=UTC)
DESIGN_END = datetime(2021, 1, 1, tzinfo=UTC)
PUBLIC_ATR_WARMUP_START = datetime(2015, 1, 1, tzinfo=UTC)
ELAPSED_WEEKS = 260.5714285714
ARMS = ("TRUE_0050", "SHIFTED_0025")
ARM_OFFSETS_PIPS = {"TRUE_0050": 0, "SHIFTED_0025": 25}

FORBIDDEN_PATH_PARTS = {"validation", "holdout", "private", "sealed"}
FORBIDDEN_OUTCOME_KEY_PARTS = (
    "next_open",
    "future_",
    "return",
    "pnl",
    "profit",
    "win_rate",
    "expectancy",
    "mfe",
    "mae",
    "trade",
    "target_hit",
    "stop_hit",
)

SEALED_FALSE_FIELDS = (
    "performance_metrics_authorized",
    "economics_authorized",
    "model0_authorized",
    "model4_authorized",
    "mt5_authorized",
    "mql5_authorized",
    "research_validation_access_authorized",
    "research_holdout_access_authorized",
    "network_authorized",
    "paid_requests_authorized",
    "promotion_eligible",
)


class ContractError(RuntimeError):
    """Fail-closed violation of the frozen source-only contract."""


def canonical_json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractError("artifact contains a non-JSON or non-finite value") from exc
    return (encoded + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def reviewed_base_source_sha256(payload: bytes) -> str:
    """Hash source with only the reviewed-row sentinel normalized to ``None``."""

    lines = payload.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        raise ContractError("builder source must contain exactly one review sentinel")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_reparse(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _assert_no_aliases(path: Path) -> None:
    absolute = _absolute(path)
    for candidate in list(reversed(absolute.parents)) + [absolute]:
        if candidate.exists() or candidate.is_symlink():
            if candidate.is_symlink() or _is_reparse(candidate):
                raise ContractError(f"path contains symlink or reparse point: {candidate}")


def assert_contained(path: Path, *, exact_root: Path) -> tuple[Path, Path]:
    absolute_path = _absolute(path)
    absolute_root = _absolute(exact_root)
    _assert_no_aliases(absolute_root)
    if not absolute_root.exists() or not absolute_root.is_dir():
        raise ContractError(f"exact root is missing or invalid: {absolute_root}")
    try:
        relative = absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise ContractError(f"path is outside exact root: {absolute_path}") from exc
    if any(part.lower() in FORBIDDEN_PATH_PARTS for part in relative.parts):
        raise ContractError(f"forbidden custody path: {relative}")
    _assert_no_aliases(absolute_path)
    return absolute_path, relative


def read_verified_bytes_once(path: Path, expected_sha256: str, *, exact_root: Path) -> bytes:
    absolute, _ = assert_contained(path, exact_root=exact_root)
    try:
        info = absolute.stat()
    except FileNotFoundError as exc:
        raise ContractError(f"authority file is missing: {absolute}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ContractError(f"authority must be a single-link regular file: {absolute}")
    with absolute.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ContractError(f"authority must be a single-link regular file: {absolute}")
        payload = handle.read()
        after = os.fstat(handle.fileno())
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity or len(payload) != after.st_size:
        raise ContractError(f"authority changed during read: {absolute}")
    actual = sha256_bytes(payload)
    if actual != expected_sha256.upper():
        raise ContractError(f"SHA256 mismatch for {absolute}: expected {expected_sha256}, got {actual}")
    return payload


def read_safe_bytes_once(path: Path, *, exact_root: Path) -> bytes:
    """Read exact bytes once after the same regular-file/containment checks."""

    absolute, _ = assert_contained(path, exact_root=exact_root)
    try:
        info = absolute.stat()
    except FileNotFoundError as exc:
        raise ContractError(f"authority file is missing: {absolute}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ContractError(f"authority must be a single-link regular file: {absolute}")
    with absolute.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ContractError(f"authority must be a single-link regular file: {absolute}")
        payload = handle.read()
        after = os.fstat(handle.fileno())
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(payload) != after.st_size
    ):
        raise ContractError(f"authority changed during read: {absolute}")
    return payload


def write_new_json(path: Path, value: Any, *, exact_root: Path) -> str:
    absolute, _ = assert_contained(path, exact_root=exact_root)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_aliases(absolute.parent)
    payload = canonical_json_bytes(value)
    try:
        with absolute.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ContractError(f"terminal artifact already exists: {absolute}") from exc
    return sha256_bytes(payload)


def write_new_bytes(path: Path, payload: bytes, *, exact_root: Path) -> str:
    absolute, _ = assert_contained(path, exact_root=exact_root)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_aliases(absolute.parent)
    try:
        with absolute.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ContractError(f"terminal artifact already exists: {absolute}") from exc
    return sha256_bytes(payload)


def create_evidence_root(path: Path, *, workspace_root: Path) -> Path:
    absolute, _ = assert_contained(path, exact_root=workspace_root)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    _assert_no_aliases(absolute.parent)
    try:
        absolute.mkdir()
    except FileExistsError as exc:
        raise ContractError(f"source feasibility attempt already exists: {absolute}") from exc
    return absolute


def price_to_points(price: Any) -> int:
    try:
        value = Decimal(str(price))
    except Exception as exc:
        raise ContractError(f"invalid price: {price!r}") from exc
    if not value.is_finite() or value <= 0:
        raise ContractError(f"invalid price: {price!r}")
    points = value / QUOTE_POINT
    if points != points.to_integral_value():
        raise ContractError(f"price is outside quote-point grid: {price!r}")
    return int(points)


def classify_lattice_cross(previous_close: Any, current_close: Any, *, arm: str) -> dict[str, Any] | None:
    """Classify the frozen cross using integer-pip arithmetic only."""

    if arm not in ARM_OFFSETS_PIPS:
        raise ContractError(f"unknown arm: {arm}")
    previous = price_to_points(previous_close)
    current = price_to_points(current_close)
    offset = ARM_OFFSETS_PIPS[arm] * POINTS_PER_PIP
    spacing = 50 * POINTS_PER_PIP

    lower_level = current - ((current - offset) % spacing)
    long_distance = current - lower_level
    if POINTS_PER_PIP <= long_distance <= 10 * POINTS_PER_PIP and previous < lower_level:
        return {"direction": "LONG", "level_pips": lower_level // POINTS_PER_PIP}

    upper_distance = (offset - current) % spacing
    upper_level = current + upper_distance
    if POINTS_PER_PIP <= upper_distance <= 10 * POINTS_PER_PIP and previous > upper_level:
        return {"direction": "SHORT", "level_pips": upper_level // POINTS_PER_PIP}
    return None


def _utc_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ContractError(f"invalid UTC timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    return parsed


def _validate_ohlc(row: Mapping[str, Any]) -> tuple[float, float, float, float]:
    try:
        open_price, high, low, close = (float(row[key]) for key in ("open", "high", "low", "close"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("M1 row is missing numeric OHLC") from exc
    if not all(math.isfinite(value) for value in (open_price, high, low, close)):
        raise ContractError("M1 row contains non-finite OHLC")
    if low > min(open_price, close) or high < max(open_price, close) or low > high:
        raise ContractError("M1 row has invalid OHLC ordering")
    return open_price, high, low, close


def _floor_time(at: datetime, minutes: int) -> datetime:
    discard = at.minute % minutes
    return at.replace(minute=at.minute - discard, second=0, microsecond=0)


def _aggregate_complete(rows: Iterable[Mapping[str, Any]], *, minutes: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    groups: dict[datetime, list[tuple[datetime, float, float, float, float]]] = defaultdict(list)
    for row in rows:
        try:
            at = _utc_datetime(row["time_utc"])
        except KeyError as exc:
            raise ContractError("M1 row is missing time_utc") from exc
        if at.second or at.microsecond:
            raise ContractError(f"M1 timestamp is not minute-aligned: {at.isoformat()}")
        open_price, high, low, close = _validate_ohlc(row)
        groups[_floor_time(at, minutes)].append((at, open_price, high, low, close))

    complete: list[dict[str, Any]] = []
    incomplete = 0
    for bucket in sorted(groups):
        group = sorted(groups[bucket], key=lambda item: item[0])
        expected = [bucket + timedelta(minutes=offset) for offset in range(minutes)]
        observed = [item[0] for item in group]
        if len(group) != minutes or observed != expected:
            incomplete += 1
            continue
        complete.append(
            {
                "time_utc": bucket,
                "open": group[0][1],
                "high": max(item[2] for item in group),
                "low": min(item[3] for item in group),
                "close": group[-1][4],
            }
        )
    return complete, {
        "observed_bins": len(groups),
        "complete_bins": len(complete),
        "incomplete_bins": incomplete,
    }


def aggregate_complete_m5(rows: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    return _aggregate_complete(rows, minutes=5)


def aggregate_complete_h1(rows: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    return _aggregate_complete(rows, minutes=60)


def atr20_shift1(h1_bars: Sequence[Mapping[str, Any]], decision_time: Any) -> float | None:
    """Return MT5-style SMA(TR,20), shift 1, from ordered complete H1 bars.

    Calendar continuity is intentionally not required: weekend/holiday gaps are
    valid, but the selected sequence must contain 21 ordered trading bars.
    """

    decision = _utc_datetime(decision_time)
    decision_hour = decision.replace(minute=0, second=0, microsecond=0)
    eligible = sorted(
        (bar for bar in h1_bars if _utc_datetime(bar["time_utc"]) < decision_hour),
        key=lambda bar: _utc_datetime(bar["time_utc"]),
    )
    if len(eligible) < 21:
        return None
    selected = eligible[-21:]
    times = [_utc_datetime(bar["time_utc"]) for bar in selected]
    if len(times) != len(set(times)) or times != sorted(times):
        raise ContractError("H1 ATR input is duplicated or unordered")
    true_ranges: list[float] = []
    for previous, current in zip(selected, selected[1:]):
        _, high, low, _ = _validate_ohlc(current)
        previous_close = float(previous["close"])
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    if len(true_ranges) != 20:
        raise ContractError("ATR20 requires exactly 20 true ranges")
    value = sum(true_ranges) / 20.0
    if not math.isfinite(value) or value < 0:
        raise ContractError("ATR20 is invalid")
    return value


def build_atr_lookup(m5_bars: Sequence[Mapping[str, Any]], h1_bars: Sequence[Mapping[str, Any]]) -> dict[datetime, float]:
    ordered_h1 = sorted(h1_bars, key=lambda row: _utc_datetime(row["time_utc"]))
    h1_times = [_utc_datetime(row["time_utc"]) for row in ordered_h1]
    if len(h1_times) != len(set(h1_times)) or h1_times != sorted(h1_times):
        raise ContractError("H1 ATR input is duplicated or unordered")
    true_ranges_by_index: list[float | None] = [None]
    for previous, current in zip(ordered_h1, ordered_h1[1:]):
        _, high, low, _ = _validate_ohlc(current)
        previous_close = float(previous["close"])
        true_range = max(high - low, abs(high - previous_close), abs(low - previous_close))
        if not math.isfinite(true_range) or true_range < 0:
            raise ContractError("ATR20 true range is invalid")
        true_ranges_by_index.append(true_range)

    lookup: dict[datetime, float] = {}
    for bar in m5_bars:
        decision = _utc_datetime(bar["time_utc"])
        decision_hour = decision.replace(minute=0, second=0, microsecond=0)
        eligible_count = bisect.bisect_left(h1_times, decision_hour)
        if eligible_count < 21:
            continue
        selected_ranges = true_ranges_by_index[eligible_count - 20 : eligible_count]
        if len(selected_ranges) != 20 or any(value is None for value in selected_ranges):
            raise ContractError("ATR20 requires exactly 20 true ranges")
        atr_value = sum(float(value) for value in selected_ranges) / 20.0
        if not math.isfinite(atr_value) or atr_value < 0:
            raise ContractError("ATR20 is invalid")
        lookup[decision] = atr_value
    return lookup


def _iso_z(value: Any) -> str:
    return _utc_datetime(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def scan_arm_with_quality(
    m5_bars: Sequence[Mapping[str, Any]],
    atr_by_decision: Mapping[Any, float],
    *,
    arm: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if arm not in ARMS:
        raise ContractError(f"unknown arm: {arm}")
    normalized_atr = {_utc_datetime(key): float(value) for key, value in atr_by_decision.items()}
    bars = sorted(m5_bars, key=lambda row: _utc_datetime(row["time_utc"]))
    accepted_dates: set[str] = set()
    signals: list[dict[str, Any]] = []
    candidates = 0
    atr_complete = 0
    for previous, current in zip(bars, bars[1:]):
        previous_time = _utc_datetime(previous["time_utc"])
        decision_bar_start = _utc_datetime(current["time_utc"])
        if decision_bar_start - previous_time != timedelta(minutes=5):
            continue
        decision_time = decision_bar_start + timedelta(minutes=5)
        day = decision_time.date().isoformat()
        if day in accepted_dates:
            continue
        hit = classify_lattice_cross(previous["close"], current["close"], arm=arm)
        if hit is None:
            continue
        # The first eligible decision consumes the arm/day even if ATR is absent.
        accepted_dates.add(day)
        candidates += 1
        atr_price = normalized_atr.get(decision_bar_start)
        if atr_price is None or not math.isfinite(atr_price) or atr_price <= 0:
            continue
        atr_complete += 1
        atr_pips = atr_price / float(PIP)
        signal = {
            "hypothesis_id": HYPOTHESIS_ID,
            "arm": arm,
            "direction": hit["direction"],
            "level_pips": hit["level_pips"],
            "decision_bar_start_utc": _iso_z(decision_bar_start),
            "decision_time_utc": _iso_z(decision_time),
            "planned_entry_time_utc": _iso_z(decision_time),
            "atr20_pips": atr_pips,
            "cost_to_stop_ratio_1p5": 1.5 / atr_pips,
        }
        assert_outcome_blind([signal])
        signals.append(signal)
    return signals, {"eligible_candidates": candidates, "atr_complete_candidates": atr_complete}


def scan_arm_signals(
    m5_bars: Sequence[Mapping[str, Any]], atr_by_decision: Mapping[Any, float], *, arm: str
) -> list[dict[str, Any]]:
    return scan_arm_with_quality(m5_bars, atr_by_decision, arm=arm)[0]


def assert_outcome_blind(value: Any) -> None:
    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                lowered = str(key).lower()
                if any(token in lowered for token in FORBIDDEN_OUTCOME_KEY_PARTS):
                    raise ContractError(f"forbidden outcome field: {key}")
                walk(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                walk(child)

    walk(value)


def _arm_gate_metrics(signals: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    count = len(signals)
    directions = [str(row["direction"]) for row in signals]
    years: dict[int, int] = defaultdict(int)
    for row in signals:
        years[_utc_datetime(row["decision_time_utc"]).year] += 1
    ratios = [float(row["cost_to_stop_ratio_1p5"]) for row in signals]
    return {
        "count": count,
        "cadence_per_elapsed_week": count / ELAPSED_WEEKS,
        "long_share": directions.count("LONG") / count if count else 0.0,
        "short_share": directions.count("SHORT") / count if count else 0.0,
        "max_single_year_share": max(years.values(), default=0) / count if count else 1.0,
        "median_cost_to_stop_ratio_1p5": median(ratios) if ratios else None,
    }


def evaluate_source_gates(
    signals_by_arm: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    m5_complete_ratio: float,
    signal_atr_complete_ratio: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    if set(signals_by_arm) != set(ARMS):
        raise ContractError("both frozen arms are required")
    if signal_atr_complete_ratio is not None and set(signal_atr_complete_ratio) != set(ARMS):
        raise ContractError("both frozen arms are required")
    for rows in signals_by_arm.values():
        assert_outcome_blind(rows)
    arm_metrics = {arm: _arm_gate_metrics(signals_by_arm[arm]) for arm in ARMS}
    gates: list[dict[str, Any]] = []

    def gate(name: str, actual: Any, passed: bool, threshold: str) -> None:
        gates.append({"name": name, "actual": actual, "threshold": threshold, "passed": bool(passed)})

    gate("global_m5_complete_ratio", m5_complete_ratio, m5_complete_ratio >= 0.99, ">=0.99")
    for arm in ARMS:
        metrics = arm_metrics[arm]
        gate(
            f"{arm}_cadence",
            metrics["cadence_per_elapsed_week"],
            2.0 <= metrics["cadence_per_elapsed_week"] <= 5.0,
            "2.0..5.0 per elapsed week",
        )
        gate(f"{arm}_long_share", metrics["long_share"], metrics["long_share"] >= 0.25, ">=0.25")
        gate(f"{arm}_short_share", metrics["short_share"], metrics["short_share"] >= 0.25, ">=0.25")
        gate(
            f"{arm}_max_single_year_share",
            metrics["max_single_year_share"],
            metrics["max_single_year_share"] <= 0.30,
            "<=0.30",
        )
        ratio = metrics["median_cost_to_stop_ratio_1p5"]
        gate(
            f"{arm}_median_cost_to_stop_ratio_1p5",
            ratio,
            isinstance(ratio, (int, float)) and math.isfinite(ratio) and ratio <= 0.25,
            "<=0.25",
        )
    verdict = "PASS_SOURCE_FEASIBILITY" if all(item["passed"] for item in gates) else "PARK_SOURCE_FEASIBILITY_FAILED"
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "evidence_class": "OUTCOME_BLIND_SOURCE_FEASIBILITY_ONLY",
        "verdict": verdict,
        "arm_metrics": arm_metrics,
        "audit_metrics": {
            "signal_atr_complete_ratio": dict(signal_atr_complete_ratio or {}),
        },
        "gates": gates,
        "zero_counters": {
            "post_decision_ohlc_rows_read": 0,
            "outcome_fields_emitted": 0,
            "performance_trials_executed": 0,
            "economic_simulation_executed": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "research_validation_opened": False,
            "research_holdout_opened": False,
            "network_calls": 0,
        },
    }


def _strict_json_object(payload: bytes, *, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ContractError(f"non-finite JSON constant in {label}: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} JSON must be an object")
    return value


def guard_production_run(
    *,
    run_switch: bool,
    reviewed_registry_sha256: str | None,
    registry_payload: bytes,
    builder_payload: bytes | None = None,
    test_payload: bytes | None = None,
    review_receipt_payload: bytes | None = None,
) -> dict[str, Any]:
    if not run_switch:
        raise ContractError("explicit run switch --run-reviewed-stage0 is required")
    if reviewed_registry_sha256 is None:
        raise ContractError("reviewed registry row SHA256 is not armed")
    expected = reviewed_registry_sha256.upper()
    if len(expected) != 64 or any(ch not in "0123456789ABCDEF" for ch in expected):
        raise ContractError("reviewed registry row SHA256 is invalid")
    matched: dict[str, Any] | None = None
    for number, raw_line in enumerate(registry_payload.splitlines(), start=1):
        if not raw_line.strip():
            continue
        row_payload = raw_line + b"\n"
        if sha256_bytes(row_payload) != expected:
            continue
        row = _strict_json_object(raw_line, label=f"reviewed registry row {number}")
        matched = row
        break
    if matched is None:
        raise ContractError("reviewed registry row SHA256 is absent from exact registry bytes")
    validation = matched.get("validation")
    if (
        matched.get("record_type") != "hypothesis_state"
        or matched.get("schema_version") != "alphafactory_candidate_registry.v1"
        or matched.get("hypothesis_id") != HYPOTHESIS_ID
        or matched.get("ea_name") != PACKAGE_NAME
        or matched.get("state") != "probe"
        or matched.get("model") is not None
        or matched.get("source_path") is not None
        or matched.get("source_hash") is not None
        or matched.get("run_ids") != []
        or not isinstance(validation, dict)
    ):
        raise ContractError("reviewed registry row identity is invalid")
    if matched.get("prereg_path") != PLAN_REL or matched.get("prereg_sha256") != FROZEN_PLAN_SHA256:
        raise ContractError("reviewed registry row does not bind the frozen plan")
    if validation.get("source_build_authorized") is not False:
        raise ContractError("reviewed registry row must freeze the reviewed build")
    if validation.get("source_run_authorized") is not True:
        raise ContractError("reviewed registry row does not authorize the source run")
    required_sealed = {
        "source_feasibility_only": True,
        "source_feasibility_attempt_limit": 1,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_receipt_sha256": DESIGN_RECEIPT_SHA256,
        "public_m1_source_sha256": PUBLIC_M1_SOURCE_SHA256,
        "source_feasibility_attempt_id": ATTEMPT_ID,
        "source_feasibility_evidence_root": EVIDENCE_ROOT_REL,
    }
    if any(validation.get(key) != expected_value for key, expected_value in required_sealed.items()):
        raise ContractError("reviewed registry row sealed authority fields are invalid")
    if any(validation.get(key) is not False for key in SEALED_FALSE_FIELDS):
        raise ContractError("reviewed registry row must keep economics/runtime/private access sealed")

    if builder_payload is None or test_payload is None or review_receipt_payload is None:
        return matched
    builder_base_sha = reviewed_base_source_sha256(builder_payload)
    test_sha = sha256_bytes(test_payload)
    receipt_sha = sha256_bytes(review_receipt_payload)
    expected_bindings = {
        "reviewed_builder_path": BUILDER_REL,
        "reviewed_builder_base_sha256": builder_base_sha,
        "reviewed_test_path": TEST_REL,
        "reviewed_test_sha256": test_sha,
        "independent_review_receipt_path": INDEPENDENT_REVIEW_RECEIPT_REL,
        "independent_review_receipt_sha256": receipt_sha,
    }
    if any(validation.get(key) != value for key, value in expected_bindings.items()):
        raise ContractError("reviewed implementation binding mismatch")
    review = _strict_json_object(review_receipt_payload, label="independent source review receipt")
    expected_review = {
        "schema_version": INDEPENDENT_REVIEW_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {"path": BUILDER_REL, "base_sha256": builder_base_sha},
        "reviewed_tests": {"path": TEST_REL, "sha256": test_sha},
        "v1_plan": {"path": PLAN_REL, "sha256": FROZEN_PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    if review != expected_review:
        raise ContractError("independent source review receipt contract mismatch")
    return matched


def _load_jsonl(payload: bytes, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(payload.decode("utf-8").splitlines(), start=1):
        if not raw.strip():
            raise ContractError(f"blank {label} line {number}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError(f"invalid {label} JSON at line {number}") from exc
        if not isinstance(value, dict):
            raise ContractError(f"non-object {label} row at line {number}")
        rows.append(value)
    return rows


def _load_public_design_aggregates(
    workspace_root: Path, manifest_payload: bytes
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Read each DESIGN shard once and retain only M5/H1 aggregates."""

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - host dependency check
        raise ContractError("pyarrow is required for a production source scan") from exc

    splitvault_root = workspace_root / SPLITVAULT_ROOT_REL
    m5_bars: list[dict[str, Any]] = []
    h1_bars: list[dict[str, Any]] = []
    m5_quality = {"observed_bins": 0, "complete_bins": 0, "incomplete_bins": 0}
    previous_day: datetime | None = None
    previous_last_time: datetime | None = None
    for entry in _load_jsonl(manifest_payload, label="DESIGN manifest"):
        try:
            day = datetime.fromisoformat(str(entry["date"])).replace(tzinfo=UTC)
            relative = Path(str(entry["relative_path"]))
            expected_sha = str(entry["sha256"])
        except (KeyError, ValueError) as exc:
            raise ContractError("DESIGN manifest row is malformed") from exc
        if not (DESIGN_START.date() <= day.date() < DESIGN_END.date()):
            continue
        if previous_day is not None and day <= previous_day:
            raise ContractError("DESIGN manifest dates are duplicated or unordered")
        previous_day = day
        if relative.parts[:2] != ("public", "DESIGN"):
            raise ContractError(f"manifest shard is outside public DESIGN: {relative}")
        shard_payload = read_verified_bytes_once(splitvault_root / relative, expected_sha, exact_root=splitvault_root)
        if len(shard_payload) != int(entry.get("bytes", -1)):
            raise ContractError(f"manifest shard byte count mismatch: {relative}")
        table = pq.read_table(io.BytesIO(shard_payload), columns=["time_utc", "open", "high", "low", "close"])
        if table.num_rows != int(entry.get("rows", -1)):
            raise ContractError(f"manifest shard row count mismatch: {relative}")
        daily_rows: list[dict[str, Any]] = []
        for row in table.to_pylist():
            at = _utc_datetime(row["time_utc"])
            if at.date() != day.date() or not (DESIGN_START <= at < DESIGN_END):
                raise ContractError(f"DESIGN shard contains out-of-date row: {relative}")
            row["time_utc"] = at
            daily_rows.append(row)
        times = [row["time_utc"] for row in daily_rows]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ContractError(f"DESIGN shard timestamps are duplicated or unordered: {relative}")
        if previous_last_time is not None and times and times[0] <= previous_last_time:
            raise ContractError("DESIGN shard boundary timestamps are not strictly increasing")
        if times:
            previous_last_time = times[-1]
        daily_m5, daily_m5_quality = aggregate_complete_m5(daily_rows)
        daily_h1, _ = aggregate_complete_h1(daily_rows)
        m5_bars.extend(daily_m5)
        h1_bars.extend(daily_h1)
        for key in m5_quality:
            m5_quality[key] += daily_m5_quality[key]
    return m5_bars, h1_bars, m5_quality


def execute_with_terminal_guard(
    evidence_root: Path,
    *,
    workspace_root: Path,
    started_payload: Mapping[str, Any],
    work: Callable[[Path, str], dict[str, Any]],
) -> dict[str, Any]:
    evidence = create_evidence_root(evidence_root, workspace_root=workspace_root)
    started_sha = write_new_json(
        evidence / "attempt_started.json", dict(started_payload), exact_root=evidence
    )
    try:
        return work(evidence, started_sha)
    except BaseException as exc:
        failure = {
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "state": "FAILED",
            "verdict": "ENGINEERING_ABORTED_NO_ECONOMIC_VERDICT",
            "attempt_started_sha256": started_sha,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "economics_executed": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
        }
        try:
            write_new_json(evidence / "attempt_terminal.json", failure, exact_root=evidence)
        except BaseException as terminal_exc:
            raise ContractError(
                f"source attempt failed ({exc}); terminal write also failed ({terminal_exc})"
            ) from exc
        raise


def write_success_artifacts(
    evidence_root: Path,
    *,
    report: Mapping[str, Any],
    signals_by_arm: Mapping[str, Sequence[Mapping[str, Any]]],
    attempt_started_sha256: str,
    registry_row_sha256: str,
    review_binding: Mapping[str, str],
) -> dict[str, Any]:
    assert_outcome_blind(report)
    for arm in ARMS:
        assert_outcome_blind(signals_by_arm[arm])
    ledger_payload = b"".join(
        canonical_json_bytes(row) for arm in ARMS for row in signals_by_arm[arm]
    )
    ledger_sha = write_new_bytes(
        evidence_root / "round_cascade_source_ledger.jsonl",
        ledger_payload,
        exact_root=evidence_root,
    )
    report_sha = write_new_json(
        evidence_root / "round_cascade_source_report.json", dict(report), exact_root=evidence_root
    )
    receipt = {
        "schema_version": "round_cascade_source_feasibility_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "evidence_class": "OUTCOME_BLIND_SOURCE_FEASIBILITY_ONLY",
        "verdict": report["verdict"],
        "v1_plan": {"path": PLAN_REL, "sha256": FROZEN_PLAN_SHA256},
        "reviewed_registry_row_sha256": registry_row_sha256,
        "review_binding": dict(review_binding),
        "artifacts": {
            "attempt_started.json": attempt_started_sha256,
            "round_cascade_source_report.json": report_sha,
            "round_cascade_source_ledger.jsonl": ledger_sha,
        },
        "zero_counters": dict(report["zero_counters"]),
    }
    receipt_sha = write_new_json(
        evidence_root / "source_feasibility_receipt.json", receipt, exact_root=evidence_root
    )
    terminal = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "state": "SUCCEEDED",
        "verdict": report["verdict"],
        "attempt_started_sha256": attempt_started_sha256,
        "source_feasibility_receipt_sha256": receipt_sha,
        "report_sha256": report_sha,
        "ledger_sha256": ledger_sha,
        "economics_executed": False,
        "mt5_launches": 0,
        "mql5_files_created": 0,
    }
    terminal_sha = write_new_json(
        evidence_root / "attempt_terminal.json", terminal, exact_root=evidence_root
    )
    return {
        "report": dict(report),
        "artifact_hashes": {
            "attempt_started.json": attempt_started_sha256,
            "round_cascade_source_report.json": report_sha,
            "round_cascade_source_ledger.jsonl": ledger_sha,
            "source_feasibility_receipt.json": receipt_sha,
            "attempt_terminal.json": terminal_sha,
        },
    }


def execute_stage0(*, workspace_root: Path, run_switch: bool) -> dict[str, Any]:
    root = _absolute(workspace_root)
    assert_contained(root, exact_root=root)
    executing_builder = _absolute(Path(__file__))
    expected_builder = _absolute(root / BUILDER_REL)
    if executing_builder != expected_builder:
        raise ContractError("executing builder is not the canonical reviewed path")

    registry_payload = read_safe_bytes_once(root / REGISTRY_REL, exact_root=root)
    builder_payload = read_safe_bytes_once(expected_builder, exact_root=root)
    test_payload = read_safe_bytes_once(root / TEST_REL, exact_root=root)
    review_receipt_payload = read_safe_bytes_once(
        root / INDEPENDENT_REVIEW_RECEIPT_REL, exact_root=root
    )
    registry_row = guard_production_run(
        run_switch=run_switch,
        reviewed_registry_sha256=REVIEWED_REGISTRY_ROW_SHA256,
        registry_payload=registry_payload,
        builder_payload=builder_payload,
        test_payload=test_payload,
        review_receipt_payload=review_receipt_payload,
    )
    read_verified_bytes_once(root / PLAN_REL, FROZEN_PLAN_SHA256, exact_root=root)
    manifest_payload = read_verified_bytes_once(
        root / DESIGN_MANIFEST_REL, DESIGN_MANIFEST_SHA256, exact_root=root
    )
    design_receipt_payload = read_verified_bytes_once(
        root / DESIGN_RECEIPT_REL, DESIGN_RECEIPT_SHA256, exact_root=root
    )
    design_receipt = _strict_json_object(design_receipt_payload, label="DESIGN receipt")
    if design_receipt.get("source_sha256") != PUBLIC_M1_SOURCE_SHA256:
        raise ContractError("public M1 source SHA does not match DESIGN receipt")
    if design_receipt.get("design_manifest_sha256") != DESIGN_MANIFEST_SHA256:
        raise ContractError("DESIGN manifest SHA does not match DESIGN receipt")
    if design_receipt.get("research_validation_opened") is not False:
        raise ContractError("DESIGN receipt does not prove validation stayed sealed")
    if design_receipt.get("research_holdout_opened") is not False:
        raise ContractError("DESIGN receipt does not prove holdout stayed sealed")

    validation = registry_row["validation"]
    review_binding = {
        "builder_base_sha256": validation["reviewed_builder_base_sha256"],
        "test_sha256": validation["reviewed_test_sha256"],
        "independent_review_receipt_sha256": validation["independent_review_receipt_sha256"],
    }
    started_payload = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "state": "STARTED",
        "evidence_class": "OUTCOME_BLIND_SOURCE_FEASIBILITY_ONLY",
        "v1_plan_sha256": FROZEN_PLAN_SHA256,
        "reviewed_registry_row_sha256": str(REVIEWED_REGISTRY_ROW_SHA256),
        "review_binding": review_binding,
        "zero_counters": {
            "source_shards_opened": 0,
            "post_decision_ohlc_rows_read": 0,
            "outcome_fields_emitted": 0,
            "performance_trials_executed": 0,
            "economics_executed": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "research_validation_opened": False,
            "research_holdout_opened": False,
            "network_calls": 0,
            "paid_requests_made": 0,
        },
    }

    def work(evidence: Path, started_sha: str) -> dict[str, Any]:
        m5_bars, h1_bars, m5_quality = _load_public_design_aggregates(root, manifest_payload)
        atr_lookup = build_atr_lookup(m5_bars, h1_bars)
        signals_by_arm: dict[str, list[dict[str, Any]]] = {}
        atr_ratios: dict[str, float] = {}
        for arm in ARMS:
            signals, quality = scan_arm_with_quality(m5_bars, atr_lookup, arm=arm)
            signals_by_arm[arm] = signals
            atr_ratios[arm] = (
                quality["atr_complete_candidates"] / quality["eligible_candidates"]
                if quality["eligible_candidates"]
                else 0.0
            )
        m5_ratio = (
            m5_quality["complete_bins"] / m5_quality["observed_bins"]
            if m5_quality["observed_bins"]
            else 0.0
        )
        report = evaluate_source_gates(
            signals_by_arm,
            m5_complete_ratio=m5_ratio,
            signal_atr_complete_ratio=atr_ratios,
        )
        report["source_contract"] = {
            "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
            "design_receipt_sha256": DESIGN_RECEIPT_SHA256,
            "public_m1_source_sha256": PUBLIC_M1_SOURCE_SHA256,
            "design_start": DESIGN_START.date().isoformat(),
            "design_end_exclusive": DESIGN_END.date().isoformat(),
            "elapsed_calendar_weeks": ELAPSED_WEEKS,
            "m5_quality": m5_quality,
        }
        return write_success_artifacts(
            evidence,
            report=report,
            signals_by_arm=signals_by_arm,
            attempt_started_sha256=started_sha,
            registry_row_sha256=str(REVIEWED_REGISTRY_ROW_SHA256),
            review_binding=review_binding,
        )

    return execute_with_terminal_guard(
        root / EVIDENCE_ROOT_REL,
        workspace_root=root,
        started_payload=started_payload,
        work=work,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-reviewed-stage0", action="store_true")
    parser.add_argument("--workspace-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    execute_stage0(
        workspace_root=args.workspace_root,
        run_switch=args.run_reviewed_stage0,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
