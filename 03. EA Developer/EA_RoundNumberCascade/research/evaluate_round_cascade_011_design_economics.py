#!/usr/bin/env python3
"""Fail-closed DESIGN economics evaluator for HYP011.

Importing this module is inert. Production execution requires:
--run-reviewed-design-economics, --workspace-root, a reviewed run-packet SHA
burned into REVIEWED_RUN_PACKET_SHA256, exact hash-bound HYP010 eligible source,
exact HYP002 detail join, latest registry authority, and a fresh evidence root.

This is a fresh pre-outcome economics child enabled by outcome-blind HYP010
source classification. It is not a post-hoc market rescue of HYP009.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
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


HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-011"
PARENT_CANDIDATE = "HYP-ROUND-CASCADE-EURUSD-M5-010"
SOURCE_SIGNAL_HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-002"
PACKAGE_NAME = "EA_RoundNumberCascade"
PLAN_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-011_DESIGN_ECONOMICS_PLAN.md"
)
FROZEN_PLAN_SHA256 = "B711C7BD30AD066C5F5C6DC404A7126A37475E2F8B047E6B95973D3DFDFCEFF3"
EVALUATOR_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "evaluate_round_cascade_011_design_economics.py"
)
TEST_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/tests/"
    "test_evaluate_round_cascade_011_design_economics.py"
)
RUN_PACKET_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-011_DESIGN_ECONOMICS_RUN_PACKET.json"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-011_DESIGN_ECONOMICS_IMPLEMENTATION_REVIEW_RECEIPT.json"
)

SOURCE_LEDGER_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/"
    "HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl"
)
SOURCE_LEDGER_SHA256 = "8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE"
SOURCE_DETAIL_COUNTS = {"TRUE_0050": 1229, "SHIFTED_0025": 1220}

HYP010_EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-010_EXECUTION_SOURCE/"
    "HYP010-EXEC-SOURCE-001"
)
ELIGIBLE_LEDGER_REL = f"{HYP010_EVIDENCE_ROOT_REL}/round_cascade_010_eligible_source_ledger.jsonl"
HYP010_REPORT_REL = f"{HYP010_EVIDENCE_ROOT_REL}/round_cascade_010_execution_source_report.json"
HYP010_RECEIPT_REL = f"{HYP010_EVIDENCE_ROOT_REL}/execution_source_receipt.json"
HYP010_TERMINAL_REL = f"{HYP010_EVIDENCE_ROOT_REL}/attempt_terminal.json"
ELIGIBLE_LEDGER_SHA256 = "C6E054433E9A0D12ACAB3E88063E266E31407F387A1A9E21F0A681A5F4A3A6F9"
HYP010_REPORT_SHA256 = "8A4CBFF9D4CF8ED9917D41AFFAB80BB3BB8FB1E8743838CB25BC4F4CD0AC8D6C"
HYP010_RECEIPT_SHA256 = "7DF404716561D3C041D6A4C5763C8061D73F0AEEA7A180AFBFE26F38D2F63E0C"
HYP010_TERMINAL_SHA256 = "489819A783B5D59FA0ED14D9CA6DFEA235E0CB64D95BCBDD80B85796D135D1AC"
HYP010_STARTED_SHA256 = "F9CCA7F59293F2A2384886ED1DF827D89BE84F3026886664BE9344F36F9F8DFA"
HYP010_INELIGIBLE_LEDGER_SHA256 = "955E892516F17BE1024BFC8562C6B0CAE47A7BC9B54C85948E3C08CED3311429"
HYP010_CLASSIFICATION_SHA256 = "5C2A9BE4A6791F910785EA67BA297500D3E005AAC69A4EE20417ACE758B2EF8F"
HYP010_ATTEMPT_ID = "HYP010-EXEC-SOURCE-001"
HYP010_PASS_STATUS = "PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP011_DESIGN_ECONOMICS"

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
ATTEMPT_ID = "HYP011-DESIGN-ECON-001"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-011_DESIGN_ECONOMICS/"
    f"{ATTEMPT_ID}"
)
DESIGN_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
DESIGN_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
PUBLIC_M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
COLLECTION_PLAN_SHA256 = "F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382"
CUSTODIAN_TOOL_SHA256 = "5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C"

# Economics trade population = HYP010 eligible counts (not full HYP002).
EXPECTED_SIGNAL_COUNTS = {"TRUE_0050": 1218, "SHIFTED_0025": 1213}
ELIGIBLE_STATUS = "ELIGIBLE_EXACT_COMPLETE_M5_NONOVERLAP"
ELIGIBLE_KEYS = {
    "arm",
    "complete_m5_starts",
    "planned_entry_time_utc",
    "reserved_exit_time_utc",
    "source_identity",
    "source_lf_row_sha256",
    "status",
}
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
EXECUTION_EVIDENCE_CLASS = "BROKER_OBSERVED_M1_PROXY_KILL_ONLY"
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
class ObservedMarketIndex:
    m1_rows: tuple[dict[str, Any], ...]
    m1_times: tuple[datetime, ...]
    aligned_entry_times: tuple[datetime, ...]
    complete_m5_starts: tuple[datetime, ...]


@dataclass(frozen=True)
class MappedSignal:
    planned_entry_time_utc: datetime
    entry_time_utc: datetime
    exit_time_utc: datetime
    entry_row_index: int
    surveillance_end_index: int
    exit_close_row_index: int
    reserved_exit_time_utc: datetime


@dataclass(frozen=True)
class TradeResult:
    arm: str
    planned_entry_time_utc: datetime
    entry_time_utc: datetime
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


def lf_row_sha256(raw_line: bytes) -> str:
    """Canonical HYP002 LF-row hash: SHA256(raw_json_line + LF)."""
    if raw_line.endswith(b"\n"):
        raise EngineeringInvalid("LF-row hash input must not include trailing newline")
    return sha256_bytes(raw_line + b"\n")


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


def _m1_timestamp_only(row: dict[str, Any]) -> datetime:
    if set(row) != M1_KEYS:
        raise EngineeringInvalid("M1 row schema mismatch")
    return parse_utc(row["time_utc"])


def build_observed_market_index(m1_rows: Iterable[dict[str, Any]]) -> ObservedMarketIndex:
    """Stream a timestamp-only index without sorting or duplicating M1 dicts."""
    row_refs: list[dict[str, Any]] = []
    times: list[datetime] = []
    aligned_entries: list[datetime] = []
    complete_starts: list[datetime] = []
    previous: datetime | None = None
    current_bin: datetime | None = None
    current_bin_times: list[datetime] = []

    def finish_bin() -> None:
        if current_bin is None:
            return
        expected = [current_bin + timedelta(minutes=offset) for offset in range(5)]
        if current_bin_times == expected:
            complete_starts.append(current_bin)

    for raw in m1_rows:
        at = _m1_timestamp_only(raw)
        if previous is not None and at <= previous:
            raise EngineeringInvalid(f"non-increasing M1 timestamp: {at.isoformat()}")
        row_refs.append(raw)
        times.append(at)
        if at.minute % 5 == 0:
            aligned_entries.append(at)
        bin_start = at - timedelta(minutes=at.minute % 5)
        if current_bin is None:
            current_bin = bin_start
        elif bin_start != current_bin:
            finish_bin()
            current_bin = bin_start
            current_bin_times = []
        current_bin_times.append(at)
        previous = at
    finish_bin()

    return ObservedMarketIndex(
        m1_rows=tuple(row_refs),
        m1_times=tuple(times),
        aligned_entry_times=tuple(aligned_entries),
        complete_m5_starts=tuple(complete_starts),
    )


def map_signal_to_market(
    signal: dict[str, Any],
    market: ObservedMarketIndex,
    *,
    reserved_exit_time_utc: datetime | None = None,
) -> MappedSignal:
    """Exact-entry mapping: complete M5 bar must start at planned_entry_time_utc."""
    checked = validate_signal_row(_serialize_signal_times(signal))
    planned = checked["planned_entry_time_utc"]

    complete_index = bisect_left(market.complete_m5_starts, planned)
    if (
        complete_index >= len(market.complete_m5_starts)
        or market.complete_m5_starts[complete_index] != planned
    ):
        raise EngineeringInvalid("no exact complete observed M5 entry at planned_entry_time_utc")

    horizon = market.complete_m5_starts[complete_index : complete_index + 12]
    if len(horizon) != 12:
        raise EngineeringInvalid("right-censored observed M5 horizon")
    if horizon[0] != planned:
        raise EngineeringInvalid("entry is not the first horizon bar")
    exit_bar_start = horizon[-1]
    exit_time = exit_bar_start + timedelta(minutes=5)
    if reserved_exit_time_utc is not None and exit_time != reserved_exit_time_utc:
        raise EngineeringInvalid("reserved_exit_time_utc mismatch")

    entry_time = planned
    entry_row_index = bisect_left(market.m1_times, entry_time)
    if entry_row_index >= len(market.m1_times) or market.m1_times[entry_row_index] != entry_time:
        raise EngineeringInvalid("mapped entry row is absent")
    exit_close_time = exit_bar_start + timedelta(minutes=4)
    exit_close_row_index = bisect_left(market.m1_times, exit_close_time)
    if (
        exit_close_row_index >= len(market.m1_times)
        or market.m1_times[exit_close_row_index] != exit_close_time
    ):
        raise EngineeringInvalid("mapped exit close row is absent")
    surveillance_end_index = bisect_left(market.m1_times, exit_time)
    if surveillance_end_index <= exit_close_row_index:
        raise EngineeringInvalid("mapped stop-surveillance range is incomplete")
    return MappedSignal(
        planned_entry_time_utc=planned,
        entry_time_utc=entry_time,
        exit_time_utc=exit_time,
        entry_row_index=entry_row_index,
        surveillance_end_index=surveillance_end_index,
        exit_close_row_index=exit_close_row_index,
        reserved_exit_time_utc=exit_time,
    )


def validate_signal_row(row: dict[str, Any]) -> dict[str, Any]:
    if set(row) != SIGNAL_KEYS:
        raise EngineeringInvalid("signal row schema mismatch")
    if row["hypothesis_id"] != SOURCE_SIGNAL_HYPOTHESIS_ID:
        raise EngineeringInvalid("signal parent hypothesis mismatch")
    arm = str(row["arm"])
    if arm not in EXPECTED_SIGNAL_COUNTS and arm not in SOURCE_DETAIL_COUNTS:
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


def load_hyp002_detail_index(path: Path, expected_sha256: str) -> dict[tuple[str, datetime, str], dict[str, Any]]:
    """Index HYP002 detail rows by arm+planned+LF-row SHA; recompute every LF hash."""
    payload = read_verified_bytes_once(path, expected_sha256)
    index: dict[tuple[str, datetime, str], dict[str, Any]] = {}
    arm_counts = {arm: 0 for arm in SOURCE_DETAIL_COUNTS}
    for number, raw_line in enumerate(payload.splitlines(), start=1):
        if not raw_line.strip():
            raise EngineeringInvalid(f"blank HYP002 detail line {number}")
        row_hash = lf_row_sha256(raw_line)
        value = strict_json_loads(raw_line, label=f"HYP002 detail line {number}")
        if not isinstance(value, dict):
            raise EngineeringInvalid(f"non-object HYP002 detail row {number}")
        signal = validate_signal_row(value)
        key = (signal["arm"], signal["planned_entry_time_utc"], row_hash)
        if key in index:
            raise EngineeringInvalid("duplicate HYP002 detail identity")
        index[key] = signal
        arm_counts[signal["arm"]] += 1
    for arm, expected in SOURCE_DETAIL_COUNTS.items():
        if arm_counts.get(arm, 0) != expected:
            raise EngineeringInvalid(f"{arm} HYP002 detail count {arm_counts.get(arm, 0)} != {expected}")
    return index


def validate_eligible_row(row: dict[str, Any]) -> dict[str, Any]:
    if set(row) != ELIGIBLE_KEYS:
        raise EngineeringInvalid("eligible row schema mismatch")
    if row.get("status") != ELIGIBLE_STATUS:
        raise EngineeringInvalid("eligible row status mismatch")
    if row.get("complete_m5_starts") != 12:
        raise EngineeringInvalid("eligible complete_m5_starts must be 12")
    arm = str(row["arm"])
    if arm not in EXPECTED_SIGNAL_COUNTS:
        raise EngineeringInvalid("unknown eligible arm")
    planned = parse_utc(row["planned_entry_time_utc"])
    reserved = parse_utc(row["reserved_exit_time_utc"])
    lf_hash = str(row["source_lf_row_sha256"]).upper()
    if re.fullmatch(r"[0-9A-F]{64}", lf_hash) is None:
        raise EngineeringInvalid("eligible source_lf_row_sha256 is not canonical SHA256")
    identity = str(row["source_identity"])
    expected_identity = f"{arm}|{iso_z(planned)}"
    if identity != expected_identity:
        raise EngineeringInvalid("eligible source_identity mismatch")
    return {
        "arm": arm,
        "planned_entry_time_utc": planned,
        "reserved_exit_time_utc": reserved,
        "source_lf_row_sha256": lf_hash,
        "source_identity": identity,
        "status": ELIGIBLE_STATUS,
        "complete_m5_starts": 12,
    }


def load_and_join_eligible_signals(
    eligible_path: Path,
    eligible_sha256: str,
    detail_index: dict[tuple[str, datetime, str], dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Join each eligible row exactly once to HYP002 detail; forbid missing/dup/fanout."""
    payload = read_verified_bytes_once(eligible_path, eligible_sha256)
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in EXPECTED_SIGNAL_COUNTS}
    seen_eligible: set[tuple[str, datetime, str]] = set()
    used_detail: set[tuple[str, datetime, str]] = set()

    for number, raw_line in enumerate(payload.splitlines(), start=1):
        if not raw_line.strip():
            raise EngineeringInvalid(f"blank eligible ledger line {number}")
        value = strict_json_loads(raw_line, label=f"eligible line {number}")
        if not isinstance(value, dict):
            raise EngineeringInvalid(f"non-object eligible row {number}")
        eligible = validate_eligible_row(value)
        key = (
            eligible["arm"],
            eligible["planned_entry_time_utc"],
            eligible["source_lf_row_sha256"],
        )
        if key in seen_eligible:
            raise EngineeringInvalid("duplicate eligible identity")
        seen_eligible.add(key)
        if key not in detail_index:
            raise EngineeringInvalid("eligible row missing HYP002 detail join")
        if key in used_detail:
            raise EngineeringInvalid("eligible join fanout onto used detail row")
        used_detail.add(key)
        detail = detail_index[key]
        # Forbid mutation: detail fields must match join keys exactly.
        if detail["arm"] != eligible["arm"]:
            raise EngineeringInvalid("joined detail arm mutation")
        if detail["planned_entry_time_utc"] != eligible["planned_entry_time_utc"]:
            raise EngineeringInvalid("joined detail planned_entry_time mutation")
        signal = dict(detail)
        signal["reserved_exit_time_utc"] = eligible["reserved_exit_time_utc"]
        signal["source_lf_row_sha256"] = eligible["source_lf_row_sha256"]
        by_arm[eligible["arm"]].append(signal)

    for arm, expected in EXPECTED_SIGNAL_COUNTS.items():
        by_arm[arm].sort(key=lambda item: item["planned_entry_time_utc"])
        if len(by_arm[arm]) != expected:
            raise EngineeringInvalid(f"{arm} eligible count {len(by_arm[arm])} != {expected}")
    return by_arm


def _validated_market_price_row(
    market: ObservedMarketIndex, row_index: int
) -> dict[str, Any]:
    if row_index < 0 or row_index >= len(market.m1_rows):
        raise EngineeringInvalid("mapped M1 row index is out of range")
    row = validate_m1_row(market.m1_rows[row_index])
    if row["time_utc"] != market.m1_times[row_index]:
        raise EngineeringInvalid("mapped M1 timestamp changed before price simulation")
    return row


def simulate_mapped_signal(
    signal: dict[str, Any], mapped: MappedSignal, market: ObservedMarketIndex
) -> TradeResult:
    checked = validate_signal_row(_serialize_signal_times(signal))
    planned_entry_time = checked["planned_entry_time_utc"]
    direction = checked["direction"]
    atr20_pips = checked["atr20_pips"]
    if mapped.planned_entry_time_utc != planned_entry_time:
        raise EngineeringInvalid("mapped signal identity mismatch")
    if mapped.entry_time_utc != planned_entry_time:
        raise EngineeringInvalid("exact-entry invariant violated")
    entry_time = mapped.entry_time_utc
    entry_row = _validated_market_price_row(market, mapped.entry_row_index)
    if entry_row["time_utc"] != entry_time:
        raise EngineeringInvalid("mapped entry timestamp mismatch")
    entry_bid = float(entry_row["open"])
    stop_distance = atr20_pips * 0.0001
    sign = 1.0 if direction == "LONG" else -1.0
    stop_bid = entry_bid - stop_distance if direction == "LONG" else entry_bid + stop_distance

    previous_time: datetime | None = None
    for row_index in range(mapped.entry_row_index, mapped.surveillance_end_index):
        row = _validated_market_price_row(market, row_index)
        at = row["time_utc"]
        gap_reopen = previous_time is not None and at - previous_time > timedelta(minutes=1)
        open_bid = float(row["open"])
        gap_stopped = gap_reopen and (
            open_bid <= stop_bid if direction == "LONG" else open_bid >= stop_bid
        )
        if gap_stopped:
            gross_r = sign * (open_bid - entry_bid) / stop_distance
            return TradeResult(
                arm=checked["arm"],
                planned_entry_time_utc=planned_entry_time,
                entry_time_utc=entry_time,
                exit_time_utc=at,
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=open_bid,
                stop_bid=stop_bid,
                atr20_pips=atr20_pips,
                gross_R=gross_r,
                exit_reason="GAP_STOP",
                year=planned_entry_time.year,
            )
        stopped = row["low"] <= stop_bid if direction == "LONG" else row["high"] >= stop_bid
        if stopped:
            return TradeResult(
                arm=checked["arm"],
                planned_entry_time_utc=planned_entry_time,
                entry_time_utc=entry_time,
                exit_time_utc=at + timedelta(minutes=1),
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=stop_bid,
                stop_bid=stop_bid,
                atr20_pips=atr20_pips,
                gross_R=-1.0,
                exit_reason="STOP",
                year=planned_entry_time.year,
            )
        previous_time = at

    exit_row = _validated_market_price_row(market, mapped.exit_close_row_index)
    if exit_row["time_utc"] + timedelta(minutes=1) != mapped.exit_time_utc:
        raise EngineeringInvalid("mapped time-exit row mismatch")
    exit_bid = float(exit_row["close"])
    return TradeResult(
        arm=checked["arm"],
        planned_entry_time_utc=planned_entry_time,
        entry_time_utc=entry_time,
        exit_time_utc=mapped.exit_time_utc,
        direction=direction,
        entry_bid=entry_bid,
        exit_bid=exit_bid,
        stop_bid=stop_bid,
        atr20_pips=atr20_pips,
        gross_R=sign * (exit_bid - entry_bid) / stop_distance,
        exit_reason="TIME",
        year=planned_entry_time.year,
    )


def simulate_signal(
    signal: dict[str, Any],
    m1_rows: Iterable[dict[str, Any]],
    *,
    reserved_exit_time_utc: datetime | None = None,
) -> TradeResult:
    market = build_observed_market_index(m1_rows)
    mapped = map_signal_to_market(signal, market, reserved_exit_time_utc=reserved_exit_time_utc)
    return simulate_mapped_signal(signal, mapped, market)


def _serialize_signal_times(signal: dict[str, Any]) -> dict[str, Any]:
    out = dict(signal)
    for key in (
        "decision_bar_start_utc",
        "decision_time_utc",
        "planned_entry_time_utc",
        "reserved_exit_time_utc",
    ):
        if isinstance(out.get(key), datetime):
            out[key] = iso_z(out[key])
    # validate_signal_row only accepts SIGNAL_KEYS; strip join annotations.
    return {key: out[key] for key in SIGNAL_KEYS}


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def assert_no_overlap(trades: list[TradeResult]) -> None:
    ordered = sorted(trades, key=lambda row: row.entry_time_utc)
    prior_exit: datetime | None = None
    for trade in ordered:
        if prior_exit is not None and trade.entry_time_utc < prior_exit:
            raise EngineeringInvalid("overlapping trades in arm")
        prior_exit = trade.exit_time_utc


def assert_reserved_nonoverlap(signals: list[dict[str, Any]]) -> None:
    """Re-assert arm-local nonoverlap on eligible reserved-exit intervals."""
    ordered = sorted(signals, key=lambda row: row["planned_entry_time_utc"])
    prior_exit: datetime | None = None
    for signal in ordered:
        planned = signal["planned_entry_time_utc"]
        reserved = signal["reserved_exit_time_utc"]
        if not isinstance(planned, datetime):
            planned = parse_utc(planned)
        if not isinstance(reserved, datetime):
            reserved = parse_utc(reserved)
        if prior_exit is not None and planned < prior_exit:
            raise EngineeringInvalid("overlapping eligible reservations in arm")
        prior_exit = reserved


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
    namespace: dict[str, Any] = {"__builtins__": __builtins__, "__name__": "_hyp011_verified_dsr"}
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
    if len(true_net) != 1218 and EXPECTED_SIGNAL_COUNTS["TRUE_0050"] == 1218:
        raise EngineeringInvalid("TRUE DSR n_obs must be 1218 for HYP011")
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
    if dsr_report["n_obs"] != EXPECTED_SIGNAL_COUNTS["TRUE_0050"]:
        raise EngineeringInvalid("DSR n_obs mismatch")
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
        "execution_evidence": {
            "class": EXECUTION_EVIDENCE_CLASS,
            "tick_exact": False,
            "promotion_evidence": False,
        },
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
        "eligible_ledger_path": ELIGIBLE_LEDGER_REL,
        "eligible_ledger_sha256": ELIGIBLE_LEDGER_SHA256,
        "hyp010_report_path": HYP010_REPORT_REL,
        "hyp010_report_sha256": HYP010_REPORT_SHA256,
        "hyp010_receipt_path": HYP010_RECEIPT_REL,
        "hyp010_receipt_sha256": HYP010_RECEIPT_SHA256,
        "hyp010_terminal_path": HYP010_TERMINAL_REL,
        "hyp010_terminal_sha256": HYP010_TERMINAL_SHA256,
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
        raise EngineeringInvalid("missing HYP011 registry row")
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
        "hyp010_terminal_path": HYP010_TERMINAL_REL,
        "hyp010_terminal_sha256": HYP010_TERMINAL_SHA256,
        "eligible_ledger_path": ELIGIBLE_LEDGER_REL,
        "eligible_ledger_sha256": ELIGIBLE_LEDGER_SHA256,
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


def validate_hyp010_chain_before_price(workspace_root: Path, packet: dict[str, Any]) -> dict[str, str]:
    """Bind HYP010 report/receipt/terminal/eligible ledger before DESIGN price access."""
    bindings = {
        "eligible_ledger": (packet["eligible_ledger_path"], ELIGIBLE_LEDGER_SHA256),
        "hyp010_report": (packet["hyp010_report_path"], HYP010_REPORT_SHA256),
        "hyp010_receipt": (packet["hyp010_receipt_path"], HYP010_RECEIPT_SHA256),
        "hyp010_terminal": (packet["hyp010_terminal_path"], HYP010_TERMINAL_SHA256),
    }
    out: dict[str, str] = {}
    for name, (rel_path, expected_sha) in bindings.items():
        out[f"{name}_sha256"] = sha256_bytes(
            read_verified_bytes_once(resolve_workspace_file(workspace_root, rel_path), expected_sha)
        )

    report = load_json_file(
        resolve_workspace_file(workspace_root, packet["hyp010_report_path"]),
        HYP010_REPORT_SHA256,
        label="HYP010 report",
    )
    receipt = load_json_file(
        resolve_workspace_file(workspace_root, packet["hyp010_receipt_path"]),
        HYP010_RECEIPT_SHA256,
        label="HYP010 receipt",
    )
    terminal = load_json_file(
        resolve_workspace_file(workspace_root, packet["hyp010_terminal_path"]),
        HYP010_TERMINAL_SHA256,
        label="HYP010 terminal",
    )

    if report.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("HYP010 report hypothesis mismatch")
    if report.get("attempt_id") != HYP010_ATTEMPT_ID:
        raise EngineeringInvalid("HYP010 report attempt mismatch")
    if report.get("verdict") != HYP010_PASS_STATUS:
        raise EngineeringInvalid("HYP010 report verdict mismatch")
    if report.get("hyp011_drafting_authorized") is not True:
        raise EngineeringInvalid("HYP010 report does not authorize HYP011 drafting")
    actual_counts = report.get("actual_counts", {}).get(ELIGIBLE_STATUS, {})
    if actual_counts.get("TRUE_0050") != 1218 or actual_counts.get("SHIFTED_0025") != 1213:
        raise EngineeringInvalid("HYP010 report eligible counts mismatch")
    if report.get("classification_sha256") != HYP010_CLASSIFICATION_SHA256:
        raise EngineeringInvalid("HYP010 report classification hash mismatch")

    if receipt.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("HYP010 receipt hypothesis mismatch")
    if receipt.get("verdict") != HYP010_PASS_STATUS:
        raise EngineeringInvalid("HYP010 receipt verdict mismatch")
    if receipt.get("hyp011_drafting_authorized") is not True:
        raise EngineeringInvalid("HYP010 receipt does not authorize HYP011 drafting")
    expected_receipt_artifacts = {
        "attempt_started.json": HYP010_STARTED_SHA256,
        "round_cascade_010_eligible_source_ledger.jsonl": ELIGIBLE_LEDGER_SHA256,
        "round_cascade_010_execution_source_report.json": HYP010_REPORT_SHA256,
        "round_cascade_010_ineligible_source_ledger.jsonl": HYP010_INELIGIBLE_LEDGER_SHA256,
    }
    if receipt.get("artifact_sha256") != expected_receipt_artifacts:
        raise EngineeringInvalid("HYP010 receipt artifact hash-chain mismatch")

    if terminal.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("HYP010 terminal hypothesis mismatch")
    if terminal.get("attempt_id") != HYP010_ATTEMPT_ID:
        raise EngineeringInvalid("HYP010 terminal attempt mismatch")
    if terminal.get("status") != HYP010_PASS_STATUS:
        raise EngineeringInvalid("HYP010 terminal status mismatch")
    if terminal.get("hyp011_drafting_authorized") is not True:
        raise EngineeringInvalid("HYP010 terminal does not authorize HYP011 drafting")
    expected_terminal_artifacts = {
        "attempt_started.json": HYP010_STARTED_SHA256,
        "execution_source_receipt.json": HYP010_RECEIPT_SHA256,
        "round_cascade_010_eligible_source_ledger.jsonl": ELIGIBLE_LEDGER_SHA256,
        "round_cascade_010_execution_source_report.json": HYP010_REPORT_SHA256,
        "round_cascade_010_ineligible_source_ledger.jsonl": HYP010_INELIGIBLE_LEDGER_SHA256,
    }
    if terminal.get("artifact_sha256") != expected_terminal_artifacts:
        raise EngineeringInvalid("HYP010 terminal artifact hash-chain mismatch")
    if terminal.get("classification_sha256") != HYP010_CLASSIFICATION_SHA256:
        raise EngineeringInvalid("HYP010 terminal classification hash mismatch")

    # Sealed source-only counters must show no economics/price outcomes.
    for blob_name, blob in (("report", report), ("receipt", receipt), ("terminal", terminal)):
        counters = blob.get("source_only_counters")
        if not isinstance(counters, dict):
            raise EngineeringInvalid(f"HYP010 {blob_name} source_only_counters missing")
        if (
            counters.get("economics_executed") is not False
            or counters.get("trades_simulated") != 0
            or counters.get("returns_computed") != 0
            or counters.get("post_entry_ohlc_rows_read") != 0
            or counters.get("outcome_fields_emitted") != 0
            or counters.get("mt5_launches") != 0
            or counters.get("mql5_files_created") != 0
            or counters.get("network_calls") != 0
        ):
            raise EngineeringInvalid(f"HYP010 {blob_name} sealed counters mismatch")
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


def load_manifest_entries(workspace_root: Path, required_dates: set[str] | None) -> list[dict[str, Any]]:
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
        if required_dates is None or date_text in required_dates:
            selected.append(row)
    if required_dates is not None:
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
    if not any(signals_by_arm.values()):
        raise EngineeringInvalid("source signal population is empty")
    rows_by_time: dict[datetime, dict[str, Any]] = {}
    for entry in load_manifest_entries(workspace_root, None):
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
    for arm, signals in signals_by_arm.items():
        assert_reserved_nonoverlap(signals)

    market = build_observed_market_index(m1_by_time.values())
    mapped_by_arm: dict[str, list[tuple[dict[str, Any], MappedSignal]]] = {
        arm: [] for arm in EXPECTED_SIGNAL_COUNTS
    }
    for arm, signals in signals_by_arm.items():
        for signal in signals:
            reserved = signal["reserved_exit_time_utc"]
            if not isinstance(reserved, datetime):
                reserved = parse_utc(reserved)
            mapped_by_arm[arm].append(
                (signal, map_signal_to_market(signal, market, reserved_exit_time_utc=reserved))
            )
        if len(mapped_by_arm[arm]) != EXPECTED_SIGNAL_COUNTS[arm]:
            raise EngineeringInvalid(
                f"{arm} mapped signal count {len(mapped_by_arm[arm])} != {EXPECTED_SIGNAL_COUNTS[arm]}"
            )

    trades_by_arm: dict[str, list[TradeResult]] = {arm: [] for arm in EXPECTED_SIGNAL_COUNTS}
    for arm, mapped_signals in mapped_by_arm.items():
        for signal, mapped in mapped_signals:
            trades_by_arm[arm].append(simulate_mapped_signal(signal, mapped, market))
        assert_no_overlap(trades_by_arm[arm])
    validate_trade_counts(trades_by_arm)
    return trades_by_arm


def trade_to_json(trade: TradeResult) -> dict[str, Any]:
    row = asdict(trade)
    row["planned_entry_time_utc"] = iso_z(trade.planned_entry_time_utc)
    row["entry_time_utc"] = iso_z(trade.entry_time_utc)
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
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "promotion_evidence": False,
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
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "promotion_evidence": False,
        "artifact_sha256": dict(hashes),
        "verdict": gate_report["status"],
    }
    hashes["design_economics_receipt.json"] = write_json_new(evidence_root / "design_economics_receipt.json", receipt)
    complete_prior = dict(hashes)
    terminal = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": gate_report["status"],
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "promotion_evidence": False,
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
    # HYP010 chain + HYP002 detail join must complete before DESIGN price access.
    validate_hyp010_chain_before_price(workspace_root, packet)
    detail_index = load_hyp002_detail_index(
        resolve_workspace_file(workspace_root, SOURCE_LEDGER_REL), SOURCE_LEDGER_SHA256
    )
    signals_by_arm = load_and_join_eligible_signals(
        resolve_workspace_file(workspace_root, ELIGIBLE_LEDGER_REL),
        ELIGIBLE_LEDGER_SHA256,
        detail_index,
    )
    validate_design_receipt(workspace_root)
    load_verified_dsr(workspace_root)

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
