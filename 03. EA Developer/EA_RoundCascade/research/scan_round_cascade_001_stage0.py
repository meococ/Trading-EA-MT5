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
import stat
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence


HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-001"
PACKAGE_NAME = "EA_RoundCascade"
PLAN_REL = "03. EA Developer/EA_RoundCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-001_PROBE_PLAN.md"
FROZEN_PLAN_SHA256 = "F605C32E65DF2F516AD9B4E013BCFD5F177831B3D1F6B4CCE88917061769B139"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
DESIGN_MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl"
DESIGN_RECEIPT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json"
SPLITVAULT_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002"

DESIGN_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
DESIGN_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
PUBLIC_M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"

# Independent review must replace this exact sentinel before a production scan.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None

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


class ContractError(RuntimeError):
    """Fail-closed violation of the frozen source-only contract."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


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
        payload = handle.read()
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
        return handle.read()


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
        decision_time = _utc_datetime(current["time_utc"])
        if decision_time - previous_time != timedelta(minutes=5):
            continue
        day = decision_time.date().isoformat()
        if day in accepted_dates:
            continue
        hit = classify_lattice_cross(previous["close"], current["close"], arm=arm)
        if hit is None:
            continue
        # The first eligible decision consumes the arm/day even if ATR is absent.
        accepted_dates.add(day)
        candidates += 1
        atr_price = normalized_atr.get(decision_time)
        if atr_price is None or not math.isfinite(atr_price) or atr_price <= 0:
            continue
        atr_complete += 1
        atr_pips = atr_price / float(PIP)
        signal = {
            "hypothesis_id": HYPOTHESIS_ID,
            "arm": arm,
            "direction": hit["direction"],
            "level_pips": hit["level_pips"],
            "decision_time_utc": _iso_z(decision_time),
            "planned_entry_time_utc": _iso_z(decision_time + timedelta(minutes=5)),
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
        "median_cost_to_stop_ratio_1p5": median(ratios) if ratios else math.inf,
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
        gate(f"{arm}_count", metrics["count"], 522 <= metrics["count"] <= 1302, "522..1302")
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
        gate(
            f"{arm}_median_cost_to_stop_ratio_1p5",
            metrics["median_cost_to_stop_ratio_1p5"],
            metrics["median_cost_to_stop_ratio_1p5"] <= 0.25,
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


def guard_production_run(
    *, run_switch: bool, reviewed_registry_sha256: str | None, registry_payload: bytes
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
        try:
            row = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError(f"reviewed registry row is invalid JSON at line {number}") from exc
        if not isinstance(row, dict):
            raise ContractError("reviewed registry row is not an object")
        matched = row
        break
    if matched is None:
        raise ContractError("reviewed registry row SHA256 is absent from exact registry bytes")
    validation = matched.get("validation")
    if matched.get("hypothesis_id") != HYPOTHESIS_ID or not isinstance(validation, dict):
        raise ContractError("reviewed registry row identity is invalid")
    if matched.get("prereg_path") != PLAN_REL or matched.get("prereg_sha256") != FROZEN_PLAN_SHA256:
        raise ContractError("reviewed registry row does not bind the frozen plan")
    if validation.get("source_run_authorized") is not True:
        raise ContractError("reviewed registry row does not authorize the source run")
    required_sealed = {
        "source_feasibility_only": True,
        "economics_authorized": False,
        "research_validation_access_authorized": False,
        "research_holdout_access_authorized": False,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_receipt_sha256": DESIGN_RECEIPT_SHA256,
        "public_m1_source_sha256": PUBLIC_M1_SOURCE_SHA256,
    }
    if any(validation.get(key) != expected_value for key, expected_value in required_sealed.items()):
        raise ContractError("reviewed registry row sealed authority fields are invalid")
    if validation.get("economics_authorized") is not False:
        raise ContractError("reviewed registry row must keep economics sealed")
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


def _load_public_design_rows(workspace_root: Path, manifest_payload: bytes) -> list[dict[str, Any]]:
    """Read hash-bound public DESIGN shards once; no validation/holdout path is legal."""

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - host dependency check
        raise ContractError("pyarrow is required for a production source scan") from exc

    splitvault_root = workspace_root / SPLITVAULT_ROOT_REL
    rows: list[dict[str, Any]] = []
    for entry in _load_jsonl(manifest_payload, label="DESIGN manifest"):
        try:
            day = datetime.fromisoformat(str(entry["date"])).replace(tzinfo=UTC)
            relative = Path(str(entry["relative_path"]))
            expected_sha = str(entry["sha256"])
        except (KeyError, ValueError) as exc:
            raise ContractError("DESIGN manifest row is malformed") from exc
        if not (PUBLIC_ATR_WARMUP_START.date() <= day.date() < DESIGN_END.date()):
            continue
        if relative.parts[:2] != ("public", "DESIGN"):
            raise ContractError(f"manifest shard is outside public DESIGN: {relative}")
        shard_payload = read_verified_bytes_once(splitvault_root / relative, expected_sha, exact_root=splitvault_root)
        if len(shard_payload) != int(entry.get("bytes", -1)):
            raise ContractError(f"manifest shard byte count mismatch: {relative}")
        table = pq.read_table(io.BytesIO(shard_payload), columns=["time_utc", "open", "high", "low", "close"])
        if table.num_rows != int(entry.get("rows", -1)):
            raise ContractError(f"manifest shard row count mismatch: {relative}")
        for row in table.to_pylist():
            at = _utc_datetime(row["time_utc"])
            if PUBLIC_ATR_WARMUP_START <= at < DESIGN_END:
                row["time_utc"] = at
                rows.append(row)
    rows.sort(key=lambda row: row["time_utc"])
    return rows


def execute_stage0(*, workspace_root: Path, output_root: Path, run_switch: bool) -> dict[str, Any]:
    root = _absolute(workspace_root)
    assert_contained(root, exact_root=root)
    registry_payload = read_safe_bytes_once(root / REGISTRY_REL, exact_root=root)
    guard_production_run(
        run_switch=run_switch,
        reviewed_registry_sha256=REVIEWED_REGISTRY_ROW_SHA256,
        registry_payload=registry_payload,
    )
    read_verified_bytes_once(root / PLAN_REL, FROZEN_PLAN_SHA256, exact_root=root)
    manifest_payload = read_verified_bytes_once(root / DESIGN_MANIFEST_REL, DESIGN_MANIFEST_SHA256, exact_root=root)
    receipt_payload = read_verified_bytes_once(root / DESIGN_RECEIPT_REL, DESIGN_RECEIPT_SHA256, exact_root=root)
    try:
        receipt = json.loads(receipt_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("DESIGN receipt is invalid JSON") from exc
    if receipt.get("source_sha256") != PUBLIC_M1_SOURCE_SHA256:
        raise ContractError("public M1 source SHA does not match DESIGN receipt")
    if receipt.get("design_manifest_sha256") != DESIGN_MANIFEST_SHA256:
        raise ContractError("DESIGN manifest SHA does not match DESIGN receipt")

    m1_rows = _load_public_design_rows(root, manifest_payload)
    decision_m1_rows = [row for row in m1_rows if DESIGN_START <= row["time_utc"] < DESIGN_END]
    m5_bars, m5_quality = aggregate_complete_m5(decision_m1_rows)
    h1_bars, _ = aggregate_complete_h1(m1_rows)
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
    m5_ratio = m5_quality["complete_bins"] / m5_quality["observed_bins"] if m5_quality["observed_bins"] else 0.0
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
    }
    assert_outcome_blind(report)
    output = _absolute(output_root)
    assert_contained(output, exact_root=root)
    output.mkdir(parents=True, exist_ok=False)
    write_new_json(output / "round_cascade_stage0_report.json", report, exact_root=output)
    ledger_path = output / "round_cascade_stage0_ledger.jsonl"
    try:
        with ledger_path.open("xb") as handle:
            for arm in ARMS:
                for row in signals_by_arm[arm]:
                    handle.write(canonical_json_bytes(row))
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ContractError(f"terminal artifact already exists: {ledger_path}") from exc
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-reviewed-stage0", action="store_true")
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    execute_stage0(
        workspace_root=args.workspace_root,
        output_root=args.output_root,
        run_switch=args.run_reviewed_stage0,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
