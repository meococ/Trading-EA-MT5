#!/usr/bin/env python3
"""Fail-closed DESIGN economics evaluator for HYP004.

Importing this module is inert. Production execution requires:
--run-reviewed-design-economics, --workspace-root, a reviewed run-packet SHA
burned into REVIEWED_RUN_PACKET_SHA256, exact hash-bound inputs, latest registry
authority, and a fresh evidence root.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-004"
PARENT_CANDIDATE = "HYP-ROUND-CASCADE-EURUSD-M5-003"
SOURCE_SIGNAL_HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-002"
PACKAGE_NAME = "EA_RoundNumberCascade"
PLAN_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS_PLAN_V2.md"
)
FROZEN_PLAN_SHA256 = "8BCD8AB9AC004E9CB39138E38906D9A0AADDAA729983DBDBE540E6B77C9D920F"
EVALUATOR_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "evaluate_round_cascade_004_design_economics.py"
)
TEST_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/tests/"
    "test_evaluate_round_cascade_004_design_economics.py"
)
RUN_PACKET_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS_RUN_PACKET.json"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
SOURCE_LEDGER_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/"
    "HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl"
)
SOURCE_EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/"
    "HYP002-SOURCE-PREFLIGHT-001"
)
SOURCE_STARTED_REL = f"{SOURCE_EVIDENCE_ROOT_REL}/attempt_started.json"
SOURCE_REPORT_REL = f"{SOURCE_EVIDENCE_ROOT_REL}/round_cascade_source_report.json"
SOURCE_RECEIPT_REL = f"{SOURCE_EVIDENCE_ROOT_REL}/source_feasibility_receipt.json"
SOURCE_TERMINAL_REL = f"{SOURCE_EVIDENCE_ROOT_REL}/attempt_terminal.json"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
PARENT_HYP003_EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-003_DESIGN_ECONOMICS/"
    "HYP003-DESIGN-ECON-001"
)
PARENT_HYP003_STARTED_REL = f"{PARENT_HYP003_EVIDENCE_ROOT_REL}/attempt_started.json"
PARENT_HYP003_TERMINAL_REL = f"{PARENT_HYP003_EVIDENCE_ROOT_REL}/attempt_terminal.json"
DESIGN_MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_manifest.jsonl"
DESIGN_RECEIPT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002/public/design_receipt.json"
COLLECTION_PLAN_REL = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md"
)
CUSTODIAN_TOOL_REL = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "splitvault_002_custodian.py"
)
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
ATTEMPT_ID = "HYP004-DESIGN-ECON-001"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-004_DESIGN_ECONOMICS/"
    f"{ATTEMPT_ID}"
)
PARENT_HYP003_STARTED_SHA256 = "5756A85BDEDDC64289187CFB07FF918C197DD38AFF8B965B8B92332E5A3F6A22"
PARENT_HYP003_TERMINAL_SHA256 = "2A7780D984AC7626C14E0D95560C71E323CBD0083D569CD0141748C7EB149A22"
SOURCE_LEDGER_SHA256 = "8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE"
SOURCE_STARTED_SHA256 = "2C1E662CA21C5B5713B7FE16E128FD738012E96964430B4F5BB9421AD6AE7F06"
SOURCE_REPORT_SHA256 = "E6AEE8603A922FB87497843A9302D8D24C90E000B154E61264EB8A290B3492D0"
SOURCE_RECEIPT_SHA256 = "C52A47071F10E6DFE1EAEB8C2AAC899ED4B7C915E71AB932193A57130CBAF23A"
SOURCE_TERMINAL_SHA256 = "2B2BD6F91EC77FCA824DF96AC6FB99C33911AB678415A055AFA5B8AAF4F849D4"
DESIGN_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
DESIGN_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
PUBLIC_M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
COLLECTION_PLAN_SHA256 = "F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382"
CUSTODIAN_TOOL_SHA256 = "5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C"
EXPECTED_SIGNAL_COUNTS = {"TRUE_0050": 1229, "SHIFTED_0025": 1220}
SIGNAL_KEYS = {
    "hypothesis_id",
    "arm",
    "direction",
    "level_pips",
    "decision_bar_start_utc",
    "decision_time_utc",
    "planned_entry_time_utc",
    "atr20_pips",
    "cost_to_stop_ratio_1p5",
}
M1_KEYS = {"time_utc", "open", "high", "low", "close"}
DESIGN_YEARS = [2016, 2017, 2018, 2019, 2020]
ELAPSED_WEEKS = 260.5714285714
COST_TIERS_PIPS = [1.50, 2.25, 3.00]
RISK_FRACTION = 0.0025
FORBIDDEN_AUTHORITY_FIELDS = (
    "source_build_authorized",
    "source_run_authorized",
    "validation_authorized",
    "research_validation_access_authorized",
    "holdout_authorized",
    "research_holdout_access_authorized",
    "private_custody_authorized",
    "monolithic_source_authorized",
    "mq5_authorized",
    "mql5_authorized",
    "mt5_authorized",
    "model0_authorized",
    "model4_authorized",
    "optimization_authorized",
    "network_authorized",
    "paid_authorized",
    "paid_requests_authorized",
    "promotion_authorized",
    "promotion_eligible",
    "paper_trading_authorized",
    "live_trading_authorized",
)
ARTIFACT_ORDER = (
    "attempt_started.json",
    "design_economics_trade_ledger.jsonl",
    "design_arm_cost_metrics.json",
    "design_yearly_metrics.json",
    "design_drawdown_metrics.json",
    "design_dsr_inputs.json",
    "design_gate_report.json",
    "design_economics_receipt.json",
    "attempt_terminal.json",
)

# Independent review must replace this exact sentinel. While None, production
# execution is impossible even with the explicit CLI flag.
REVIEWED_RUN_PACKET_SHA256: str | None = None


class EngineeringInvalid(Exception):
    """Raised when a frozen engineering invariant fails."""


@dataclass(frozen=True)
class M5Bar:
    time_utc: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class TradeResult:
    arm: str
    planned_entry_time_utc: datetime
    exit_time_utc: datetime
    direction: str
    entry_bid: float
    exit_bid: float
    stop_bid: float
    atr20_pips: float
    gross_R: float
    exit_reason: str
    year: int


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_reviewer_bound_source(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    pattern = re.compile(
        r"^REVIEWED_RUN_PACKET_SHA256: str \| None = (None|\"[0-9A-F]{64}\"|'[0-9A-F]{64}')$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise EngineeringInvalid("review sentinel line must appear exactly once in canonical form")
    normalized = text[: matches[0].start()] + "REVIEWED_RUN_PACKET_SHA256: str | None = None" + text[matches[0].end() :]
    return normalized.encode("utf-8")


def reviewer_base_sha256(payload: bytes) -> str:
    return sha256_bytes(normalize_reviewer_bound_source(payload))


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise EngineeringInvalid(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise EngineeringInvalid(f"non-finite JSON value: {value}")


def strict_json_loads(payload: bytes, *, label: str) -> Any:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except EngineeringInvalid:
        raise
    except Exception as exc:
        raise EngineeringInvalid(f"invalid {label} JSON") from exc
    _assert_no_nonfinite(value, label)
    return value


def strict_jsonl_loads(payload: bytes, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, raw in enumerate(payload.decode("utf-8").splitlines(), start=1):
        if not raw.strip():
            raise EngineeringInvalid(f"blank {label} line {number}")
        value = strict_json_loads(raw.encode("utf-8"), label=f"{label} line {number}")
        if not isinstance(value, dict):
            raise EngineeringInvalid(f"non-object {label} row {number}")
        rows.append(value)
    return rows


def _assert_no_nonfinite(value: Any, label: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise EngineeringInvalid(f"non-finite {label} value")
    if isinstance(value, dict):
        for child in value.values():
            _assert_no_nonfinite(child, label)
    elif isinstance(value, list):
        for child in value:
            _assert_no_nonfinite(child, label)


def load_json_file(path: Path, expected_sha256: str | None = None, *, label: str = "file") -> Any:
    payload = read_verified_bytes_once(path, expected_sha256) if expected_sha256 else read_regular_file(path)
    return strict_json_loads(payload, label=label)


def load_jsonl_file(path: Path, expected_sha256: str | None = None, *, label: str = "file") -> list[dict[str, Any]]:
    payload = read_verified_bytes_once(path, expected_sha256) if expected_sha256 else read_regular_file(path)
    return strict_jsonl_loads(payload, label=label)


def parse_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise EngineeringInvalid(f"invalid timestamp: {value!r}") from exc
    else:
        raise EngineeringInvalid(f"invalid timestamp: {value!r}")
    if dt.tzinfo is None:
        raise EngineeringInvalid(f"timestamp is not timezone-aware: {value!r}")
    out = dt.astimezone(timezone.utc)
    if out.second or out.microsecond:
        raise EngineeringInvalid(f"timestamp is not minute-aligned: {value!r}")
    return out


def _num(row: dict[str, Any], key: str) -> float:
    if key not in row:
        raise EngineeringInvalid(f"missing numeric field {key}")
    try:
        out = float(row[key])
    except Exception as exc:
        raise EngineeringInvalid(f"invalid numeric field {key}") from exc
    if not math.isfinite(out):
        raise EngineeringInvalid(f"non-finite numeric field {key}")
    return out


def validate_m1_row(row: dict[str, Any]) -> dict[str, Any]:
    if set(row) != M1_KEYS:
        raise EngineeringInvalid("M1 row schema mismatch")
    at = parse_utc(row["time_utc"])
    if at.minute % 1 != 0 or at.second or at.microsecond:
        raise EngineeringInvalid("M1 timestamp is not minute aligned")
    out = {"time_utc": at}
    for key in ("open", "high", "low", "close"):
        value = _num(row, key)
        if value <= 0:
            raise EngineeringInvalid(f"M1 {key} must be positive")
        out[key] = value
    if out["high"] < max(out["open"], out["close"]) or out["low"] > min(out["open"], out["close"]):
        raise EngineeringInvalid("M1 OHLC geometry violation")
    return out


def project_twelve_m5_bars(m1_rows: Iterable[dict[str, Any]], entry_time_utc: Any) -> list[M5Bar]:
    start = parse_utc(entry_time_utc)
    by_time: dict[datetime, dict[str, Any]] = {}
    for raw in m1_rows:
        row = validate_m1_row(raw)
        ts = row["time_utc"]
        if ts in by_time:
            raise EngineeringInvalid(f"duplicate M1 minute: {ts.isoformat()}")
        by_time[ts] = row

    bars: list[M5Bar] = []
    for bar_index in range(12):
        bar_start = start + timedelta(minutes=5 * bar_index)
        minutes: list[dict[str, Any]] = []
        for minute_offset in range(5):
            ts = bar_start + timedelta(minutes=minute_offset)
            row = by_time.get(ts)
            if row is None:
                raise EngineeringInvalid(f"missing M1 minute: {ts.isoformat()}")
            minutes.append(row)
        bars.append(
            M5Bar(
                time_utc=bar_start,
                open=float(minutes[0]["open"]),
                high=max(float(row["high"]) for row in minutes),
                low=min(float(row["low"]) for row in minutes),
                close=float(minutes[-1]["close"]),
            )
        )

    expected = {start + timedelta(minutes=i) for i in range(60)}
    extras = set(by_time) - expected
    if extras:
        raise EngineeringInvalid(f"unexpected M1 minute outside required window: {min(extras).isoformat()}")
    return bars


def validate_signal_row(row: dict[str, Any]) -> dict[str, Any]:
    if set(row) != SIGNAL_KEYS:
        raise EngineeringInvalid("signal row schema mismatch")
    if row["hypothesis_id"] != SOURCE_SIGNAL_HYPOTHESIS_ID:
        raise EngineeringInvalid("signal parent hypothesis mismatch")
    arm = str(row["arm"])
    if arm not in EXPECTED_SIGNAL_COUNTS:
        raise EngineeringInvalid("unknown signal arm")
    direction = str(row["direction"]).upper()
    if direction not in {"LONG", "SHORT"}:
        raise EngineeringInvalid("invalid signal direction")
    entry_time = parse_utc(row["planned_entry_time_utc"])
    if parse_utc(row["decision_time_utc"]) != entry_time:
        raise EngineeringInvalid("decision_time and planned_entry_time mismatch")
    decision_bar_start = parse_utc(row["decision_bar_start_utc"])
    if entry_time - decision_bar_start != timedelta(minutes=5):
        raise EngineeringInvalid("entry time is not one M5 bar after decision start")
    atr20_pips = _num(row, "atr20_pips")
    if atr20_pips <= 0:
        raise EngineeringInvalid("atr20_pips must be positive")
    ratio = _num(row, "cost_to_stop_ratio_1p5")
    if not math.isclose(ratio, 1.5 / atr20_pips, rel_tol=1e-10, abs_tol=1e-12):
        raise EngineeringInvalid("cost_to_stop_ratio_1p5 mismatch")
    level = _num(row, "level_pips")
    if level <= 0 or int(level) != level:
        raise EngineeringInvalid("level_pips must be positive integer")
    out = dict(row)
    out["arm"] = arm
    out["direction"] = direction
    out["planned_entry_time_utc"] = entry_time
    out["decision_time_utc"] = entry_time
    out["decision_bar_start_utc"] = decision_bar_start
    out["atr20_pips"] = atr20_pips
    return out


def load_source_signals(path: Path, expected_sha256: str) -> dict[str, list[dict[str, Any]]]:
    rows = load_jsonl_file(path, expected_sha256, label="HYP002 source ledger")
    by_arm = {arm: [] for arm in EXPECTED_SIGNAL_COUNTS}
    seen_keys: set[tuple[str, datetime]] = set()
    for row in rows:
        signal = validate_signal_row(row)
        key = (signal["arm"], signal["planned_entry_time_utc"])
        if key in seen_keys:
            raise EngineeringInvalid("duplicate signal identity")
        seen_keys.add(key)
        by_arm[signal["arm"]].append(signal)
    for arm, expected in EXPECTED_SIGNAL_COUNTS.items():
        by_arm[arm].sort(key=lambda item: item["planned_entry_time_utc"])
        if len(by_arm[arm]) != expected:
            raise EngineeringInvalid(f"{arm} signal count {len(by_arm[arm])} != {expected}")
    return by_arm


def simulate_signal(signal: dict[str, Any], m1_rows: Iterable[dict[str, Any]]) -> TradeResult:
    checked = validate_signal_row(_serialize_signal_times(signal))
    entry_time = checked["planned_entry_time_utc"]
    direction = checked["direction"]
    atr20_pips = checked["atr20_pips"]
    bars = project_twelve_m5_bars(m1_rows, entry_time)
    entry_bid = bars[0].open
    stop_distance = atr20_pips * 0.0001
    sign = 1.0 if direction == "LONG" else -1.0
    stop_bid = entry_bid - stop_distance if direction == "LONG" else entry_bid + stop_distance

    for bar in bars:
        stopped = bar.low <= stop_bid if direction == "LONG" else bar.high >= stop_bid
        if stopped:
            return TradeResult(
                arm=checked["arm"],
                planned_entry_time_utc=entry_time,
                exit_time_utc=bar.time_utc + timedelta(minutes=5),
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=stop_bid,
                stop_bid=stop_bid,
                atr20_pips=atr20_pips,
                gross_R=-1.0,
                exit_reason="STOP",
                year=entry_time.year,
            )

    exit_bid = bars[-1].close
    return TradeResult(
        arm=checked["arm"],
        planned_entry_time_utc=entry_time,
        exit_time_utc=entry_time + timedelta(minutes=60),
        direction=direction,
        entry_bid=entry_bid,
        exit_bid=exit_bid,
        stop_bid=stop_bid,
        atr20_pips=atr20_pips,
        gross_R=sign * (exit_bid - entry_bid) / stop_distance,
        exit_reason="TIME",
        year=entry_time.year,
    )


def _serialize_signal_times(signal: dict[str, Any]) -> dict[str, Any]:
    out = dict(signal)
    for key in ("decision_bar_start_utc", "decision_time_utc", "planned_entry_time_utc"):
        if isinstance(out.get(key), datetime):
            out[key] = iso_z(out[key])
    return out


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def assert_no_overlap(trades: list[TradeResult]) -> None:
    ordered = sorted(trades, key=lambda row: row.planned_entry_time_utc)
    prior_exit: datetime | None = None
    for trade in ordered:
        if prior_exit is not None and trade.planned_entry_time_utc < prior_exit:
            raise EngineeringInvalid("overlapping trades in arm")
        prior_exit = trade.exit_time_utc


def validate_trade_counts(trades_by_arm: dict[str, list[TradeResult]]) -> None:
    for arm, expected in EXPECTED_SIGNAL_COUNTS.items():
        actual = len(trades_by_arm.get(arm, []))
        if actual != expected:
            raise EngineeringInvalid(f"{arm} trade count {actual} != {expected}")


def net_R(trade: TradeResult, round_trip_cost_pips: float) -> float:
    if trade.atr20_pips <= 0 or not math.isfinite(trade.atr20_pips):
        raise EngineeringInvalid("atr20_pips must be positive finite")
    value = trade.gross_R - (round_trip_cost_pips / trade.atr20_pips)
    if not math.isfinite(value):
        raise EngineeringInvalid("non-finite net_R")
    return value


def profit_factor(values: Iterable[float]) -> dict[str, Any]:
    vals = [float(v) for v in values]
    if any(not math.isfinite(v) for v in vals):
        raise EngineeringInvalid("non-finite PF input")
    wins = sum(v for v in vals if v > 0)
    losses = -sum(v for v in vals if v < 0)
    if losses > 0:
        return {"status": "FINITE", "value": wins / losses}
    if wins > 0:
        return {"status": "NO_LOSS", "value": None}
    return {"status": "NO_WIN_NO_LOSS", "value": None}


def relative_pf(true_pf: dict[str, Any], shifted_pf: dict[str, Any]) -> dict[str, Any]:
    true_value = _pf_numeric(true_pf)
    shifted_value = _pf_numeric(shifted_pf)
    if true_pf["status"] == "NO_LOSS" and shifted_pf["status"] == "NO_LOSS":
        return {"status": "ZERO_BOTH_NO_LOSS", "value": None}
    if true_value is None or shifted_value is None:
        return {"status": "UNDEFINED", "value": None}
    if math.isinf(true_value) and not math.isinf(shifted_value):
        return {"status": "POSITIVE_INFINITY", "value": None}
    if math.isinf(shifted_value) and not math.isinf(true_value):
        return {"status": "NEGATIVE_INFINITY", "value": None}
    delta = true_value - shifted_value
    if not math.isfinite(delta):
        raise EngineeringInvalid("non-finite relative PF")
    return {"status": "FINITE", "value": delta}


def _pf_numeric(pf: dict[str, Any]) -> float | None:
    status = pf.get("status")
    if status == "FINITE":
        value = float(pf["value"])
        if not math.isfinite(value):
            raise EngineeringInvalid("non-finite PF value")
        return value
    if status == "NO_LOSS":
        return math.inf
    if status == "NO_WIN_NO_LOSS":
        return None
    raise EngineeringInvalid("unknown PF status")


def arm_cost_metrics(trades: list[TradeResult], cost_pips: float) -> dict[str, Any]:
    vals = [net_R(trade, cost_pips) for trade in sorted(trades, key=lambda row: row.planned_entry_time_utc)]
    if not vals:
        raise EngineeringInvalid("empty trade metrics")
    return {
        "cost_pips": cost_pips,
        "trade_count": len(vals),
        "mean_net_R": sum(vals) / len(vals),
        "total_net_R": sum(vals),
        "profit_factor": profit_factor(vals),
        "net_R": vals,
    }


def fixed_year_totals(trades: list[TradeResult], cost_pips: float) -> dict[str, Any]:
    totals = {str(year): 0.0 for year in DESIGN_YEARS}
    for trade in trades:
        key = str(trade.year)
        if key not in totals:
            raise EngineeringInvalid(f"trade year outside DESIGN years: {trade.year}")
        totals[key] += net_R(trade, cost_pips)
    return {"year_totals": totals, "positive_year_count": sum(1 for value in totals.values() if value > 0)}


def cadence_per_elapsed_week(trade_count: int) -> float:
    return trade_count / ELAPSED_WEEKS


def compounding_drawdown_pct(trades: list[TradeResult], cost_pips: float) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for trade in sorted(trades, key=lambda row: row.planned_entry_time_utc):
        equity *= 1.0 + RISK_FRACTION * net_R(trade, cost_pips)
        if equity <= 0 or not math.isfinite(equity):
            raise EngineeringInvalid("non-positive or non-finite equity factor")
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd * 100.0


def sample_sharpe(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return 0.0 if var <= 0 else mean / math.sqrt(var)


def sample_variance(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)


def population_skew_kurt(vals: list[float]) -> tuple[float, float]:
    if not vals:
        raise EngineeringInvalid("empty DSR input")
    mean = sum(vals) / len(vals)
    m2 = sum((v - mean) ** 2 for v in vals) / len(vals)
    if m2 <= 0:
        return 0.0, 3.0
    m3 = sum((v - mean) ** 3 for v in vals) / len(vals)
    m4 = sum((v - mean) ** 4 for v in vals) / len(vals)
    return m3 / (m2 ** 1.5), m4 / (m2 * m2)


def load_verified_dsr(workspace_root: Path):
    path = resolve_workspace_file(workspace_root, DSR_REL)
    payload = read_verified_bytes_once(path, DSR_SHA256)
    namespace: dict[str, Any] = {"__builtins__": __builtins__, "__name__": "_hyp004_verified_dsr"}
    code = compile(payload, str(path), "exec")
    exec(code, namespace)
    if "dsr" not in namespace:
        raise EngineeringInvalid("verified DSR has no dsr function")
    return namespace["dsr"], sha256_bytes(payload)


def dsr_inputs_and_value(true_net: list[float], shifted_net: list[float], workspace_root: Path | None = None) -> dict[str, Any]:
    if any(not math.isfinite(v) for v in true_net + shifted_net):
        raise EngineeringInvalid("non-finite DSR input")
    if len(true_net) != EXPECTED_SIGNAL_COUNTS["TRUE_0050"]:
        raise EngineeringInvalid("TRUE DSR observation count mismatch")
    dsr_func, dsr_sha = load_verified_dsr(workspace_root or Path.cwd())
    true_sr = sample_sharpe(true_net)
    shifted_sr = sample_sharpe(shifted_net)
    skew, kurt = population_skew_kurt(true_net)
    var_trials = sample_variance([true_sr, shifted_sr])
    value = float(dsr_func(true_sr, len(true_net), skew, kurt, var_trials, 2))
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise EngineeringInvalid("DSR is non-finite or out of range")
    return {
        "dsr_tool_sha256": dsr_sha,
        "true_sharpe": true_sr,
        "shifted_sharpe": shifted_sr,
        "trial_variance": var_trials,
        "true_skew": skew,
        "true_non_excess_kurtosis": kurt,
        "n_trials": 2,
        "n_obs": len(true_net),
        "dsr": value,
    }


def evaluate_gates(trades_by_arm: dict[str, list[TradeResult]], workspace_root: Path | None = None) -> dict[str, Any]:
    validate_trade_counts(trades_by_arm)
    for trades in trades_by_arm.values():
        assert_no_overlap(trades)

    true_metrics = {cost: arm_cost_metrics(trades_by_arm["TRUE_0050"], cost) for cost in COST_TIERS_PIPS}
    shifted_metrics = {cost: arm_cost_metrics(trades_by_arm["SHIFTED_0025"], cost) for cost in COST_TIERS_PIPS}
    yearly = fixed_year_totals(trades_by_arm["TRUE_0050"], 1.50)
    drawdown = compounding_drawdown_pct(trades_by_arm["TRUE_0050"], 1.50)
    dsr_report = dsr_inputs_and_value(true_metrics[1.50]["net_R"], shifted_metrics[1.50]["net_R"], workspace_root)
    rel_pf = relative_pf(true_metrics[1.50]["profit_factor"], shifted_metrics[1.50]["profit_factor"])
    rel_mean = true_metrics[1.50]["mean_net_R"] - shifted_metrics[1.50]["mean_net_R"]

    gate_rows = [
        ("TRUE cadence", 2.0 <= cadence_per_elapsed_week(len(trades_by_arm["TRUE_0050"])) <= 5.0),
        ("TRUE PF at 1.50 pips", _pf_gate(true_metrics[1.50]["profit_factor"], 1.30, strict=True)),
        ("TRUE PF at 2.25 pips", _pf_gate(true_metrics[2.25]["profit_factor"], 1.25, strict=False)),
        ("TRUE PF at 3.00 pips", _pf_gate(true_metrics[3.00]["profit_factor"], 1.00, strict=False)),
        ("TRUE mean net R at 1.50 pips", true_metrics[1.50]["mean_net_R"] >= 0.08),
        ("TRUE total net R at 1.50 pips", true_metrics[1.50]["total_net_R"] > 0),
        ("TRUE positive DESIGN years at 1.50 pips", yearly["positive_year_count"] >= 4),
        ("TRUE max compounding DD", drawdown <= 6.0),
        ("TRUE DSR at 1.50 pips", dsr_report["dsr"] >= 0.95),
        ("TRUE PF minus SHIFTED PF", _relative_pf_gate(rel_pf, 0.15)),
        ("TRUE mean net R minus SHIFTED mean net R", rel_mean >= 0.05),
    ]
    all_pass = all(passed for _, passed in gate_rows)
    return {
        "status": "PASS_DESIGN_ECONOMICS_MAY_BUILD_EA" if all_pass else "KILL_DESIGN_ECONOMICS_NO_EDGE",
        "gates": [{"name": name, "passed": passed} for name, passed in gate_rows],
        "true_metrics": true_metrics,
        "shifted_metrics": shifted_metrics,
        "yearly": yearly,
        "drawdown_pct": drawdown,
        "dsr": dsr_report,
        "relative_pf": rel_pf,
        "relative_mean_net_R": rel_mean,
    }


def _pf_gate(pf: dict[str, Any], threshold: float, *, strict: bool) -> bool:
    value = _pf_numeric(pf)
    if value is None:
        return False
    return value > threshold if strict else value >= threshold


def _relative_pf_gate(delta: dict[str, Any], threshold: float) -> bool:
    if delta["status"] == "POSITIVE_INFINITY":
        return True
    if delta["status"] != "FINITE":
        return False
    return float(delta["value"]) >= threshold


def resolve_workspace_file(workspace_root: Path, rel_path: str) -> Path:
    if Path(rel_path).is_absolute():
        raise EngineeringInvalid(f"path must be relative: {rel_path}")
    root = workspace_root.resolve()
    candidate = root / rel_path
    relative = Path(rel_path)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise EngineeringInvalid(f"symlink forbidden: {rel_path}")
    path = candidate.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise EngineeringInvalid(f"path escapes workspace: {rel_path}") from exc
    return path


def assert_regular_single_link_file(path: Path) -> None:
    if path.is_symlink():
        raise EngineeringInvalid(f"symlink forbidden: {path}")
    if not path.is_file():
        raise EngineeringInvalid(f"file missing: {path}")
    stat = path.stat()
    if getattr(stat, "st_nlink", 1) != 1:
        raise EngineeringInvalid(f"hardlink forbidden: {path}")


def read_regular_file(path: Path) -> bytes:
    assert_regular_single_link_file(path)
    return path.read_bytes()


def read_verified_bytes_once(path: Path, expected_sha256: str | None = None) -> bytes:
    payload = read_regular_file(path)
    if expected_sha256 is not None and sha256_bytes(payload) != expected_sha256.upper():
        raise EngineeringInvalid(f"SHA256 mismatch for {path}")
    return payload


def validate_self_and_review(workspace_root: Path, packet: dict[str, Any]) -> dict[str, str]:
    evaluator_path = resolve_workspace_file(workspace_root, EVALUATOR_REL)
    if evaluator_path.resolve() != Path(__file__).resolve():
        raise EngineeringInvalid("canonical evaluator path mismatch")
    evaluator_payload = read_regular_file(evaluator_path)
    test_payload = read_regular_file(resolve_workspace_file(workspace_root, TEST_REL))
    plan_sha = sha256_file(resolve_workspace_file(workspace_root, PLAN_REL))
    if plan_sha != FROZEN_PLAN_SHA256:
        raise EngineeringInvalid("plan SHA mismatch")
    expected_base_sha = str(packet.get("reviewed_evaluator_base_sha256", "")).upper()
    expected_test_sha = str(packet.get("reviewed_test_sha256", "")).upper()
    actual_base_sha = reviewer_base_sha256(evaluator_payload)
    actual_test_sha = sha256_bytes(test_payload)
    if actual_base_sha != expected_base_sha:
        raise EngineeringInvalid("reviewed evaluator base SHA mismatch")
    if actual_test_sha != expected_test_sha:
        raise EngineeringInvalid("reviewed test SHA mismatch")
    review_rel = str(packet.get("review_receipt_path", ""))
    review_sha = str(packet.get("review_receipt_sha256", "")).upper()
    review = load_json_file(resolve_workspace_file(workspace_root, review_rel), review_sha, label="review receipt")
    expected_review = {
        "schema": "round_cascade_design_economics_implementation_review_v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "review_status": "PASS_TO_PREPARE_AUTHORITY",
        "reviewed_plan_path": PLAN_REL,
        "reviewed_plan_sha256": FROZEN_PLAN_SHA256,
        "reviewed_evaluator_path": EVALUATOR_REL,
        "reviewed_evaluator_base_sha256": actual_base_sha,
        "reviewed_test_path": TEST_REL,
        "reviewed_test_sha256": actual_test_sha,
        "authority_granted": False,
        "permissions_reviewed": {
            "economics_authorized": True,
            "post_entry_ohlc_authorized": True,
            "performance_metrics_authorized": True,
            "public_design_m1_authorized": True,
            **{field: False for field in FORBIDDEN_AUTHORITY_FIELDS},
        },
    }
    if review != expected_review:
        raise EngineeringInvalid("review receipt contract mismatch")
    return {
        "evaluator_base_sha256": actual_base_sha,
        "test_sha256": actual_test_sha,
        "plan_sha256": plan_sha,
        "review_receipt_sha256": review_sha,
    }


def validate_run_packet(packet: dict[str, Any], packet_sha256: str, workspace_root: Path | None = None) -> None:
    if REVIEWED_RUN_PACKET_SHA256 is None:
        raise EngineeringInvalid("reviewed run packet sentinel is not armed")
    if packet_sha256.upper() != REVIEWED_RUN_PACKET_SHA256.upper():
        raise EngineeringInvalid("run packet SHA256 is not the reviewed sentinel")
    required = {
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_candidate": PARENT_CANDIDATE,
        "plan_path": PLAN_REL,
        "plan_sha256": FROZEN_PLAN_SHA256,
        "attempt_id": ATTEMPT_ID,
        "evidence_root": EVIDENCE_ROOT_REL,
        "registry_path": REGISTRY_REL,
        "source_ledger_path": SOURCE_LEDGER_REL,
        "source_ledger_sha256": SOURCE_LEDGER_SHA256,
        "source_started_path": SOURCE_STARTED_REL,
        "source_started_sha256": SOURCE_STARTED_SHA256,
        "source_report_path": SOURCE_REPORT_REL,
        "source_report_sha256": SOURCE_REPORT_SHA256,
        "source_receipt_path": SOURCE_RECEIPT_REL,
        "source_receipt_sha256": SOURCE_RECEIPT_SHA256,
        "source_terminal_path": SOURCE_TERMINAL_REL,
        "source_terminal_sha256": SOURCE_TERMINAL_SHA256,
        "parent_hyp003_started_path": PARENT_HYP003_STARTED_REL,
        "parent_hyp003_started_sha256": PARENT_HYP003_STARTED_SHA256,
        "parent_hyp003_terminal_path": PARENT_HYP003_TERMINAL_REL,
        "parent_hyp003_terminal_sha256": PARENT_HYP003_TERMINAL_SHA256,
        "design_manifest_path": DESIGN_MANIFEST_REL,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_receipt_path": DESIGN_RECEIPT_REL,
        "design_receipt_sha256": DESIGN_RECEIPT_SHA256,
        "public_m1_source_sha256": PUBLIC_M1_SOURCE_SHA256,
        "collection_plan_path": COLLECTION_PLAN_REL,
        "collection_plan_sha256": COLLECTION_PLAN_SHA256,
        "custodian_tool_path": CUSTODIAN_TOOL_REL,
        "custodian_tool_sha256": CUSTODIAN_TOOL_SHA256,
        "dsr_path": DSR_REL,
        "dsr_sha256": DSR_SHA256,
        "expected_true_signals": EXPECTED_SIGNAL_COUNTS["TRUE_0050"],
        "expected_shifted_signals": EXPECTED_SIGNAL_COUNTS["SHIFTED_0025"],
        "evaluator_path": EVALUATOR_REL,
        "test_path": TEST_REL,
        "review_receipt_path": REVIEW_RECEIPT_REL,
        "reviewed_evaluator_base_sha256": packet.get("reviewed_evaluator_base_sha256"),
        "reviewed_test_sha256": packet.get("reviewed_test_sha256"),
        "review_receipt_sha256": packet.get("review_receipt_sha256"),
        "economics_authorized": True,
        "post_entry_ohlc_authorized": True,
        "performance_metrics_authorized": True,
        "public_design_m1_authorized": True,
        "attempt_limit": 1,
    }
    exact_keys = set(required) | set(FORBIDDEN_AUTHORITY_FIELDS) | {"registry_authority"}
    if set(packet) != exact_keys:
        raise EngineeringInvalid("run packet schema keys mismatch")
    for key, expected in required.items():
        if packet.get(key) != expected:
            raise EngineeringInvalid(f"run packet {key} mismatch")
    for key in (
        "reviewed_evaluator_base_sha256",
        "reviewed_test_sha256",
        "review_receipt_sha256",
    ):
        value = packet.get(key)
        if not isinstance(value, str) or re.fullmatch(r"[0-9A-F]{64}", value) is None:
            raise EngineeringInvalid(f"run packet {key} is not canonical SHA256")
    if packet.get("registry_authority") is not True:
        raise EngineeringInvalid("registry authority is not explicit true")
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        if packet.get(field) is not False:
            raise EngineeringInvalid(f"forbidden authority not false: {field}")
    if workspace_root is not None:
        validate_self_and_review(workspace_root, packet)


def validate_latest_registry_authority(workspace_root: Path, packet_sha256: str, packet: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = load_jsonl_file(resolve_workspace_file(workspace_root, REGISTRY_REL), label="candidate registry")
    latest = None
    for row in rows:
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            latest = row
    if latest is None:
        raise EngineeringInvalid("missing HYP004 registry row")
    if latest.get("state") != "probe":
        raise EngineeringInvalid("latest registry state mismatch")
    if latest.get("parent_candidate") != PARENT_CANDIDATE:
        raise EngineeringInvalid("latest registry parent mismatch")
    validation = latest.get("validation")
    if not isinstance(validation, dict):
        raise EngineeringInvalid("registry validation missing")
    if validation.get("design_economics_run_authorized") is not True:
        raise EngineeringInvalid("latest registry row does not authorize DESIGN economics")
    if validation.get("run_packet_sha256") != packet_sha256:
        raise EngineeringInvalid("registry run packet hash mismatch")
    required_validation = {
        "attempt_id": ATTEMPT_ID,
        "evidence_root": EVIDENCE_ROOT_REL,
        "attempts_consumed": 0,
        "attempt_limit": 1,
        "evaluator_path": EVALUATOR_REL,
        "test_path": TEST_REL,
        "run_packet_path": RUN_PACKET_REL,
        "review_receipt_path": REVIEW_RECEIPT_REL,
        "parent_hyp003_terminal_path": PARENT_HYP003_TERMINAL_REL,
        "parent_hyp003_terminal_sha256": PARENT_HYP003_TERMINAL_SHA256,
        "collection_plan_path": COLLECTION_PLAN_REL,
        "collection_plan_sha256": COLLECTION_PLAN_SHA256,
        "custodian_tool_path": CUSTODIAN_TOOL_REL,
        "custodian_tool_sha256": CUSTODIAN_TOOL_SHA256,
        "economics_authorized": True,
        "post_entry_ohlc_authorized": True,
        "performance_metrics_authorized": True,
        "public_design_m1_authorized": True,
    }
    for key, expected in required_validation.items():
        if validation.get(key) != expected:
            raise EngineeringInvalid(f"registry {key} mismatch")
    for key in ("evaluator_base_sha256", "test_sha256", "review_receipt_sha256"):
        if not isinstance(validation.get(key), str) or not validation[key]:
            raise EngineeringInvalid(f"registry {key} missing")
    if packet is not None:
        expected_hashes = {
            "evaluator_base_sha256": packet["reviewed_evaluator_base_sha256"],
            "test_sha256": packet["reviewed_test_sha256"],
            "review_receipt_sha256": packet["review_receipt_sha256"],
        }
        for key, expected in expected_hashes.items():
            if validation.get(key) != expected:
                raise EngineeringInvalid(f"registry {key} mismatch")
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        if validation.get(field) is not False:
            raise EngineeringInvalid(f"registry forbidden authority not false: {field}")
    if latest.get("prereg_path") != PLAN_REL or latest.get("prereg_sha256") != FROZEN_PLAN_SHA256:
        raise EngineeringInvalid("registry prereg binding mismatch")
    return latest


def validate_hyp002_artifacts(workspace_root: Path, packet: dict[str, Any]) -> dict[str, str]:
    bindings = {
        "source_started": (packet["source_started_path"], SOURCE_STARTED_SHA256),
        "source_ledger": (packet["source_ledger_path"], SOURCE_LEDGER_SHA256),
        "source_report": (packet["source_report_path"], SOURCE_REPORT_SHA256),
        "source_receipt": (packet["source_receipt_path"], SOURCE_RECEIPT_SHA256),
        "source_terminal": (packet["source_terminal_path"], SOURCE_TERMINAL_SHA256),
    }
    out: dict[str, str] = {}
    for name, (rel_path, expected_sha) in bindings.items():
        out[f"{name}_sha256"] = sha256_bytes(read_verified_bytes_once(resolve_workspace_file(workspace_root, rel_path), expected_sha))
    receipt = load_json_file(resolve_workspace_file(workspace_root, packet["source_receipt_path"]), SOURCE_RECEIPT_SHA256, label="HYP002 receipt")
    report = load_json_file(resolve_workspace_file(workspace_root, packet["source_report_path"]), SOURCE_REPORT_SHA256, label="HYP002 report")
    terminal = load_json_file(resolve_workspace_file(workspace_root, packet["source_terminal_path"]), SOURCE_TERMINAL_SHA256, label="HYP002 terminal")
    if terminal.get("state") != "SUCCEEDED" or terminal.get("verdict") != "PASS_SOURCE_FEASIBILITY":
        raise EngineeringInvalid("HYP002 terminal verdict mismatch")
    receipt_hashes = receipt.get("artifacts")
    expected_receipt_hashes = {
        "attempt_started.json": SOURCE_STARTED_SHA256,
        "round_cascade_source_report.json": SOURCE_REPORT_SHA256,
        "round_cascade_source_ledger.jsonl": SOURCE_LEDGER_SHA256,
    }
    if receipt_hashes != expected_receipt_hashes:
        raise EngineeringInvalid("HYP002 receipt artifact hash-chain mismatch")
    expected_terminal_hashes = {
        "attempt_started_sha256": SOURCE_STARTED_SHA256,
        "report_sha256": SOURCE_REPORT_SHA256,
        "ledger_sha256": SOURCE_LEDGER_SHA256,
        "source_feasibility_receipt_sha256": SOURCE_RECEIPT_SHA256,
    }
    for field, expected in expected_terminal_hashes.items():
        if terminal.get(field) != expected:
            raise EngineeringInvalid(f"HYP002 terminal {field} mismatch")
    if report.get("verdict") != "PASS_SOURCE_FEASIBILITY":
        raise EngineeringInvalid("HYP002 report verdict mismatch")
    if receipt.get("hypothesis_id") != SOURCE_SIGNAL_HYPOTHESIS_ID or receipt.get("verdict") != "PASS_SOURCE_FEASIBILITY":
        raise EngineeringInvalid("HYP002 receipt identity/verdict mismatch")
    expected_zero_counters = {
        "post_decision_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "performance_trials_executed": 0,
        "economic_simulation_executed": False,
        "mt5_launches": 0,
        "mql5_files_created": 0,
        "research_validation_opened": False,
        "research_holdout_opened": False,
        "network_calls": 0,
    }
    if report.get("zero_counters") != expected_zero_counters:
        raise EngineeringInvalid("HYP002 report zero counters mismatch")
    if receipt.get("zero_counters") != expected_zero_counters:
        raise EngineeringInvalid("HYP002 receipt zero counters mismatch")
    source_contract = report.get("source_contract")
    if not isinstance(source_contract, dict):
        raise EngineeringInvalid("HYP002 report source contract missing")
    if source_contract.get("design_manifest_sha256") != DESIGN_MANIFEST_SHA256:
        raise EngineeringInvalid("HYP002 report DESIGN manifest mismatch")
    if source_contract.get("design_receipt_sha256") != DESIGN_RECEIPT_SHA256:
        raise EngineeringInvalid("HYP002 report DESIGN receipt mismatch")
    if source_contract.get("public_m1_source_sha256") != PUBLIC_M1_SOURCE_SHA256:
        raise EngineeringInvalid("HYP002 report public source mismatch")
    if (
        terminal.get("economics_executed") is not False
        or terminal.get("mt5_launches") != 0
        or terminal.get("mql5_files_created") != 0
    ):
        raise EngineeringInvalid("HYP002 terminal sealed counters mismatch")
    return out


def validate_hyp003_parent_terminal(workspace_root: Path, packet: dict[str, Any]) -> dict[str, str]:
    bindings = {
        "parent_hyp003_started": (packet["parent_hyp003_started_path"], PARENT_HYP003_STARTED_SHA256),
        "parent_hyp003_terminal": (packet["parent_hyp003_terminal_path"], PARENT_HYP003_TERMINAL_SHA256),
    }
    out: dict[str, str] = {}
    for name, (rel_path, expected_sha) in bindings.items():
        out[f"{name}_sha256"] = sha256_bytes(read_verified_bytes_once(resolve_workspace_file(workspace_root, rel_path), expected_sha))
    started = load_json_file(
        resolve_workspace_file(workspace_root, packet["parent_hyp003_started_path"]),
        PARENT_HYP003_STARTED_SHA256,
        label="HYP003 started",
    )
    terminal = load_json_file(
        resolve_workspace_file(workspace_root, packet["parent_hyp003_terminal_path"]),
        PARENT_HYP003_TERMINAL_SHA256,
        label="HYP003 terminal",
    )
    if started.get("hypothesis_id") != PARENT_CANDIDATE or started.get("attempt_id") != "HYP003-DESIGN-ECON-001":
        raise EngineeringInvalid("HYP003 started identity mismatch")
    if terminal.get("hypothesis_id") != PARENT_CANDIDATE or terminal.get("attempt_id") != "HYP003-DESIGN-ECON-001":
        raise EngineeringInvalid("HYP003 terminal identity mismatch")
    if terminal.get("status") != "ENGINEERING_INVALID_NO_MARKET_VERDICT":
        raise EngineeringInvalid("HYP003 terminal is not engineering-invalid")
    reason = str(terminal.get("reason", ""))
    if "timezone-aware" not in reason or "Timestamp('2016-01-05 00:00:00')" not in reason:
        raise EngineeringInvalid("HYP003 terminal failure reason mismatch")
    artifact_hashes = terminal.get("artifact_sha256")
    if artifact_hashes != {"attempt_started.json": PARENT_HYP003_STARTED_SHA256}:
        raise EngineeringInvalid("HYP003 terminal artifact hash-chain mismatch")
    return out


def validate_design_receipt(workspace_root: Path) -> dict[str, str]:
    manifest_payload = read_verified_bytes_once(resolve_workspace_file(workspace_root, DESIGN_MANIFEST_REL), DESIGN_MANIFEST_SHA256)
    collection_plan_payload = read_verified_bytes_once(
        resolve_workspace_file(workspace_root, COLLECTION_PLAN_REL), COLLECTION_PLAN_SHA256
    )
    custodian_payload = read_verified_bytes_once(
        resolve_workspace_file(workspace_root, CUSTODIAN_TOOL_REL), CUSTODIAN_TOOL_SHA256
    )
    receipt = load_json_file(resolve_workspace_file(workspace_root, DESIGN_RECEIPT_REL), DESIGN_RECEIPT_SHA256, label="DESIGN receipt")
    required_receipt = {
        "collection_plan_sha256": COLLECTION_PLAN_SHA256,
        "custodian_tool_sha256": CUSTODIAN_TOOL_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "source_sha256": PUBLIC_M1_SOURCE_SHA256,
        "research_validation_opened": False,
        "research_holdout_opened": False,
    }
    if not set(required_receipt) <= set(receipt):
        raise EngineeringInvalid("DESIGN receipt schema mismatch")
    for field, expected in required_receipt.items():
        if receipt.get(field) != expected:
            raise EngineeringInvalid(f"DESIGN receipt {field} mismatch")
    return {
        "design_manifest_sha256": sha256_bytes(manifest_payload),
        "design_receipt_sha256": DESIGN_RECEIPT_SHA256,
        "collection_plan_sha256": sha256_bytes(collection_plan_payload),
        "custodian_tool_sha256": sha256_bytes(custodian_payload),
    }


def required_dates_for_signals(signals_by_arm: dict[str, list[dict[str, Any]]]) -> set[str]:
    dates: set[str] = set()
    for signals in signals_by_arm.values():
        for signal in signals:
            start = signal["planned_entry_time_utc"]
            for minute in range(60):
                dates.add((start + timedelta(minutes=minute)).date().isoformat())
    return dates


def load_manifest_entries(workspace_root: Path, required_dates: set[str]) -> list[dict[str, Any]]:
    rows = load_jsonl_file(resolve_workspace_file(workspace_root, DESIGN_MANIFEST_REL), DESIGN_MANIFEST_SHA256, label="DESIGN manifest")
    selected: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for row in rows:
        if set(row) != {"date", "relative_path", "sha256", "bytes", "rows"}:
            raise EngineeringInvalid("DESIGN manifest schema mismatch")
        date_text = str(row["date"])
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text) is None:
            raise EngineeringInvalid("DESIGN manifest date mismatch")
        expected_relative = f"public/DESIGN/{date_text}/m1.parquet"
        if row["relative_path"] != expected_relative:
            raise EngineeringInvalid("DESIGN manifest relative path/date mismatch")
        if not isinstance(row["sha256"], str) or re.fullmatch(r"[0-9A-F]{64}", row["sha256"]) is None:
            raise EngineeringInvalid("DESIGN manifest shard SHA mismatch")
        for numeric in ("bytes", "rows"):
            if isinstance(row[numeric], bool) or not isinstance(row[numeric], int) or row[numeric] <= 0:
                raise EngineeringInvalid(f"DESIGN manifest {numeric} mismatch")
        if date_text in seen_dates:
            raise EngineeringInvalid("duplicate DESIGN manifest date")
        seen_dates.add(date_text)
        if date_text in required_dates:
            selected.append(row)
    missing = required_dates - {str(row["date"]) for row in selected}
    if missing:
        raise EngineeringInvalid(f"missing DESIGN shard date: {sorted(missing)[0]}")
    return selected


def resolve_design_shard_file(workspace_root: Path, manifest_relative_path: str) -> Path:
    relative = PurePosixPath(manifest_relative_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise EngineeringInvalid(f"invalid DESIGN manifest relative path: {manifest_relative_path}")
    if len(relative.parts) < 3 or relative.parts[:2] != ("public", "DESIGN"):
        raise EngineeringInvalid(f"DESIGN shard is outside public DESIGN split: {manifest_relative_path}")
    dataset_root_rel = Path(DESIGN_MANIFEST_REL).parent.parent
    dataset_root = resolve_workspace_file(workspace_root, dataset_root_rel.as_posix())
    shard_rel = dataset_root_rel.joinpath(*relative.parts).as_posix()
    shard_path = resolve_workspace_file(workspace_root, shard_rel)
    try:
        shard_path.relative_to(dataset_root)
    except ValueError as exc:
        raise EngineeringInvalid(f"DESIGN shard escapes dataset root: {manifest_relative_path}") from exc
    return shard_path


def decode_manifest_bound_public_design_parquet(
    workspace_root: Path, entry: dict[str, Any], payload: bytes
) -> tuple[Path, list[dict[str, Any]]]:
    if set(entry) != {"date", "relative_path", "sha256", "bytes", "rows"}:
        raise EngineeringInvalid("DESIGN manifest entry schema mismatch")
    date_text = str(entry["date"])
    expected_relative = f"public/DESIGN/{date_text}/m1.parquet"
    if entry["relative_path"] != expected_relative:
        raise EngineeringInvalid("DESIGN manifest entry path/date mismatch")
    shard_path = resolve_design_shard_file(workspace_root, expected_relative)
    if shard_path.suffix.lower() != ".parquet":
        raise EngineeringInvalid("public DESIGN shard is not parquet")
    expected_sha = str(entry["sha256"])
    if re.fullmatch(r"[0-9A-F]{64}", expected_sha) is None or sha256_bytes(payload) != expected_sha:
        raise EngineeringInvalid(f"DESIGN shard SHA mismatch: {expected_relative}")
    if isinstance(entry["bytes"], bool) or not isinstance(entry["bytes"], int) or len(payload) != entry["bytes"]:
        raise EngineeringInvalid(f"DESIGN shard byte count mismatch: {expected_relative}")
    if isinstance(entry["rows"], bool) or not isinstance(entry["rows"], int) or entry["rows"] <= 0:
        raise EngineeringInvalid(f"DESIGN shard row count contract mismatch: {expected_relative}")

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise EngineeringInvalid("pyarrow is required for parquet DESIGN shards") from exc
    expected_schema = pa.schema(
        [
            ("time_server", pa.timestamp("ns")),
            ("time_utc", pa.timestamp("ns")),
            ("utc_offset_h", pa.int8()),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("tick_volume", pa.uint64()),
            ("spread", pa.int32()),
            ("real_volume", pa.uint64()),
        ]
    )
    parquet_file = pq.ParquetFile(io.BytesIO(payload))
    if not parquet_file.schema_arrow.equals(expected_schema, check_metadata=True):
        raise EngineeringInvalid(f"{expected_relative} parquet producer schema mismatch")
    if parquet_file.num_row_groups != 1:
        raise EngineeringInvalid(f"{expected_relative} parquet row-group count mismatch")
    table = parquet_file.read(columns=sorted(M1_KEYS))
    rows: list[dict[str, Any]] = []
    for raw in table.to_pylist():
        value = raw.get("time_utc")
        if not isinstance(value, datetime) or value.tzinfo is not None:
            raise EngineeringInvalid(f"{expected_relative} parquet time_utc is not naive datetime")
        row = dict(raw)
        row["time_utc"] = value.replace(tzinfo=timezone.utc)
        rows.append(validate_m1_row(row))
    if len(rows) != entry["rows"]:
        raise EngineeringInvalid(f"DESIGN shard row count mismatch: {expected_relative}")
    return shard_path, rows


def load_required_m1_rows(workspace_root: Path, signals_by_arm: dict[str, list[dict[str, Any]]]) -> dict[datetime, dict[str, Any]]:
    required_dates = required_dates_for_signals(signals_by_arm)
    rows_by_time: dict[datetime, dict[str, Any]] = {}
    for entry in load_manifest_entries(workspace_root, required_dates):
        rel_path = str(entry["relative_path"])
        shard_path = resolve_design_shard_file(workspace_root, rel_path)
        payload = read_verified_bytes_once(shard_path, str(entry["sha256"]))
        decoded_path, daily_rows = decode_manifest_bound_public_design_parquet(workspace_root, entry, payload)
        if decoded_path != shard_path:
            raise EngineeringInvalid(f"DESIGN shard path changed during decode: {rel_path}")
        expected_date = str(entry["date"])
        previous: datetime | None = None
        for row in daily_rows:
            at = row["time_utc"]
            if at.date().isoformat() != expected_date:
                raise EngineeringInvalid(f"DESIGN shard out-of-date row: {rel_path}")
            if previous is not None and at <= previous:
                raise EngineeringInvalid(f"DESIGN shard timestamps are duplicated or unordered: {rel_path}")
            if at in rows_by_time:
                raise EngineeringInvalid("duplicate M1 timestamp across shards")
            rows_by_time[at] = row
            previous = at
    return rows_by_time


def read_m1_shard(payload: bytes, path: Path, *, label: str) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return [validate_m1_row(row) for row in strict_jsonl_loads(payload, label=label)]
    if suffix == ".csv":
        text = payload.decode("utf-8").splitlines()
        reader = csv.DictReader(text)
        if set(reader.fieldnames or []) != M1_KEYS:
            raise EngineeringInvalid(f"{label} CSV schema mismatch")
        return [validate_m1_row(row) for row in reader]
    if suffix == ".parquet":
        raise EngineeringInvalid("parquet decoding requires manifest-bound public DESIGN boundary")
    raise EngineeringInvalid(f"unsupported DESIGN shard format: {suffix}")


def simulate_all(signals_by_arm: dict[str, list[dict[str, Any]]], m1_by_time: dict[datetime, dict[str, Any]]) -> dict[str, list[TradeResult]]:
    trades_by_arm: dict[str, list[TradeResult]] = {arm: [] for arm in EXPECTED_SIGNAL_COUNTS}
    for arm, signals in signals_by_arm.items():
        for signal in signals:
            start = signal["planned_entry_time_utc"]
            window = [m1_by_time[start + timedelta(minutes=i)] for i in range(60) if start + timedelta(minutes=i) in m1_by_time]
            if len(window) != 60:
                raise EngineeringInvalid("missing exact M1 entry window")
            trades_by_arm[arm].append(simulate_signal(signal, window))
        assert_no_overlap(trades_by_arm[arm])
    validate_trade_counts(trades_by_arm)
    return trades_by_arm


def trade_to_json(trade: TradeResult) -> dict[str, Any]:
    row = asdict(trade)
    row["planned_entry_time_utc"] = iso_z(trade.planned_entry_time_utc)
    row["exit_time_utc"] = iso_z(trade.exit_time_utc)
    return row


def create_fresh_evidence_root(workspace_root: Path, evidence_root_rel: str | None = None) -> Path:
    root = resolve_workspace_file(workspace_root, evidence_root_rel or EVIDENCE_ROOT_REL)
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise EngineeringInvalid("evidence root already exists") from exc
    return root


def write_json_new(path: Path, value: Any) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    return write_bytes_new(path, payload.encode("utf-8"))


def write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> str:
    payload = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    return write_bytes_new(path, payload)


def write_bytes_new(path: Path, payload: bytes) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(str(path), flags)
    with os.fdopen(fd, "wb") as fh:
        fh.write(payload)
    return sha256_bytes(payload)


def write_failure_terminal(evidence_root: Path, reason: str, artifact_hashes: dict[str, str]) -> None:
    present_hashes = dict(artifact_hashes)
    for artifact in evidence_root.iterdir():
        if artifact.is_file() and artifact.name not in present_hashes and artifact.name != "attempt_terminal.json":
            present_hashes[artifact.name] = sha256_file(artifact)
    terminal = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
        "reason": reason,
        "artifact_sha256": present_hashes,
    }
    target = evidence_root / "attempt_terminal.json"
    if not target.exists():
        write_json_new(target, terminal)


def write_success_artifacts(
    evidence_root: Path,
    packet_sha: str,
    trades_by_arm: dict[str, list[TradeResult]],
    gate_report: dict[str, Any],
    initial_hashes: dict[str, str] | None = None,
) -> dict[str, str]:
    hashes: dict[str, str] = dict(initial_hashes or {})
    trade_rows = [
        trade_to_json(trade)
        for arm in ("TRUE_0050", "SHIFTED_0025")
        for trade in sorted(trades_by_arm[arm], key=lambda row: row.planned_entry_time_utc)
    ]
    hashes["design_economics_trade_ledger.jsonl"] = write_jsonl_new(evidence_root / "design_economics_trade_ledger.jsonl", trade_rows)
    arm_metrics = {"TRUE_0050": gate_report["true_metrics"], "SHIFTED_0025": gate_report["shifted_metrics"]}
    hashes["design_arm_cost_metrics.json"] = write_json_new(evidence_root / "design_arm_cost_metrics.json", arm_metrics)
    hashes["design_yearly_metrics.json"] = write_json_new(evidence_root / "design_yearly_metrics.json", gate_report["yearly"])
    hashes["design_drawdown_metrics.json"] = write_json_new(evidence_root / "design_drawdown_metrics.json", {"true_1p5_max_dd_pct": gate_report["drawdown_pct"]})
    hashes["design_dsr_inputs.json"] = write_json_new(evidence_root / "design_dsr_inputs.json", gate_report["dsr"])
    hashes["design_gate_report.json"] = write_json_new(evidence_root / "design_gate_report.json", gate_report)
    receipt = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "run_packet_sha256": packet_sha,
        "artifact_sha256": dict(hashes),
        "verdict": gate_report["status"],
    }
    hashes["design_economics_receipt.json"] = write_json_new(evidence_root / "design_economics_receipt.json", receipt)
    complete_prior = dict(hashes)
    terminal = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": gate_report["status"],
        "receipt_sha256": hashes["design_economics_receipt.json"],
        "artifact_sha256": complete_prior,
    }
    hashes["attempt_terminal.json"] = write_json_new(evidence_root / "attempt_terminal.json", terminal)
    return hashes


def execute_reviewed_design_economics(workspace_root: Path, run_packet_path: Path) -> int:
    workspace_root = workspace_root.resolve()
    if REVIEWED_RUN_PACKET_SHA256 is None:
        raise EngineeringInvalid("production disarmed: REVIEWED_RUN_PACKET_SHA256 is None")
    expected_packet_path = resolve_workspace_file(workspace_root, RUN_PACKET_REL)
    packet_path = run_packet_path if run_packet_path.is_absolute() else workspace_root / run_packet_path
    if packet_path.resolve() != expected_packet_path:
        raise EngineeringInvalid("run packet path is not the canonical reviewed path")
    packet_payload = read_regular_file(expected_packet_path)
    packet_sha = sha256_bytes(packet_payload)
    packet = strict_json_loads(packet_payload, label="run packet")
    if not isinstance(packet, dict):
        raise EngineeringInvalid("run packet must be an object")

    validate_run_packet(packet, packet_sha, workspace_root)
    validate_latest_registry_authority(workspace_root, packet_sha, packet)
    validate_hyp002_artifacts(workspace_root, packet)
    validate_hyp003_parent_terminal(workspace_root, packet)
    validate_design_receipt(workspace_root)
    load_verified_dsr(workspace_root)
    signals_by_arm = load_source_signals(resolve_workspace_file(workspace_root, SOURCE_LEDGER_REL), SOURCE_LEDGER_SHA256)

    evidence_root = create_fresh_evidence_root(workspace_root)
    artifact_hashes: dict[str, str] = {}
    try:
        started = {
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "run_packet_sha256": packet_sha,
            "status": "STARTED",
        }
        artifact_hashes["attempt_started.json"] = write_json_new(evidence_root / "attempt_started.json", started)
        m1_rows = load_required_m1_rows(workspace_root, signals_by_arm)
        trades_by_arm = simulate_all(signals_by_arm, m1_rows)
        gate_report = evaluate_gates(trades_by_arm, workspace_root)
        write_success_artifacts(evidence_root, packet_sha, trades_by_arm, gate_report, artifact_hashes)
        return 0
    except Exception as exc:
        write_failure_terminal(evidence_root, str(exc), artifact_hashes)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-reviewed-design-economics", action="store_true")
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--run-packet", type=Path, default=Path(RUN_PACKET_REL))
    args = parser.parse_args(argv)
    if not args.run_reviewed_design_economics:
        print("DISARMED: import-safe evaluator; pass --run-reviewed-design-economics with reviewed packet authority.")
        return 2
    if args.workspace_root is None:
        print("ENGINEERING_INVALID_NO_MARKET_VERDICT: --workspace-root is required", file=sys.stderr)
        return 1
    try:
        return execute_reviewed_design_economics(args.workspace_root, args.run_packet)
    except EngineeringInvalid as exc:
        print(f"ENGINEERING_INVALID_NO_MARKET_VERDICT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
