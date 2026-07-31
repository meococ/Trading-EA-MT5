#!/usr/bin/env python3
"""Fail-closed DESIGN economics evaluator for HYP-VCEX-EURUSD-M15-002.

Importing this module is inert. Production execution requires:
--run-reviewed-design-economics, --workspace-root, a reviewed run-packet SHA
burned into REVIEWED_RUN_PACKET_SHA256, exact hash-bound HYP001 source PASS
artifacts, latest registry authority, and a fresh evidence root.

This is a fresh pre-outcome economics child enabled by outcome-blind HYP001
source classification. It is not a post-hoc market rescue of any prior object.
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
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-VCEX-EURUSD-M15-002"
PARENT_CANDIDATE = "HYP-VCEX-EURUSD-M15-001"
PACKAGE_NAME = "EA_VolumeClockExhaustion"
FAMILY = "volume-clock-early-impulse-exhaustion-reversal-design-economics"
PLAN_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/"
    "HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS_PLAN.md"
)
FROZEN_PLAN_SHA256 = "3FE2F25BADE3F29407F76C38407ED10325A6EA6819388F1C67896C2C17AF9494"
EVALUATOR_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/"
    "evaluate_vcex_002_design_economics.py"
)
TEST_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/tests/"
    "test_evaluate_vcex_002_design_economics.py"
)
RUN_PACKET_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/"
    "HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS_RUN_PACKET.json"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/"
    "HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS_IMPLEMENTATION_REVIEW_RECEIPT.json"
)

HYP001_EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/evidence/"
    "HYP-VCEX-EURUSD-M15-001_SOURCE_FEASIBILITY/VCEX001-SOURCE-001"
)
SOURCE_TERMINAL_REL = f"{HYP001_EVIDENCE_ROOT_REL}/attempt_terminal.json"
SOURCE_RECEIPT_REL = f"{HYP001_EVIDENCE_ROOT_REL}/source_feasibility_receipt.json"
SOURCE_CLASSIFICATION_REL = f"{HYP001_EVIDENCE_ROOT_REL}/vcex_001_source_classifications.jsonl"
SOURCE_LEDGER_REL = f"{HYP001_EVIDENCE_ROOT_REL}/vcex_001_source_ledger.jsonl"
SOURCE_REPORT_REL = f"{HYP001_EVIDENCE_ROOT_REL}/vcex_001_source_report.json"
SOURCE_STARTED_REL = f"{HYP001_EVIDENCE_ROOT_REL}/attempt_started.json"

SOURCE_TERMINAL_SHA256 = "74832896B42BEE53E4375069B56CFDEB5114BCA66A24E068DC7041F5612C1D49"
SOURCE_RECEIPT_SHA256 = "0D1911848896B9E4D30C21A32AF3720A9D4A0C9A2C231DEFAD2DF73F1E191425"
SOURCE_CLASSIFICATION_SHA256 = "FDD3D608A70D54634511A582E202D431D42F04EEEFBB0239233BB38D32407D06"
SOURCE_LEDGER_SHA256 = "EA608B72DBF146E45FD568BD5A1AA9EC2691D2AE1BF78F244C007F157BDD1978"
SOURCE_REPORT_SHA256 = "7911A5C9D0585F7F897BAD3779E67F3EA717754DEBB3DE3EB9EFB18AD5E93845"
SOURCE_ATTEMPT_STARTED_SHA256 = "8D4B7E750448CA3E337A7338C0A27B3A711C47F3B7BA1F304962AB0012658ABF"
SOURCE_REGISTRY_ROW_SHA256 = "CD420E208611FE27590903590134A5E434920D3C53B25F4469DE27D2FA02D352"
CLASSIFICATION_DIGEST_SHA256 = "7FFF418FB2AC78B38651B3A455D69A45333FE1C4EC7CEB1F04FEE7E6F79703F2"
CANONICAL_DIGEST_SHA256 = "07006B208371AEAB2CD97C0B44A34E742269AD9C8A155D536966AE31A9B16169"

HYP001_ATTEMPT_ID = "VCEX001-SOURCE-001"
HYP001_PASS_STATUS = "PASS_SOURCE_FEASIBILITY"
HYP001_STAGE0_VERDICT = "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY"
RECEIPT_NON_TERMINAL_STATUS = "NON_TERMINAL_SOURCE_RESULT_AWAITING_ATTEMPT_TERMINAL"

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
ATTEMPT_ID = "VCEX002-DESIGN-ECON-001"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_VolumeClockExhaustion/research/evidence/"
    "HYP-VCEX-EURUSD-M15-002_DESIGN_ECONOMICS/"
    f"{ATTEMPT_ID}"
)
DESIGN_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
DESIGN_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
PUBLIC_M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
COLLECTION_PLAN_SHA256 = "F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382"
CUSTODIAN_TOOL_SHA256 = "5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C"

EXPECTED_SIGNAL_COUNTS = {"TRUE": 807, "FOLLOW_CONTROL": 807}
EXPECTED_CLASSIFICATION_TOTAL = 812
EXPECTED_EXECUTABLE = 807
EXPECTED_EXCLUDED = 5
EXECUTABLE_STATUS = "SOURCE_EXECUTABLE"
EXCLUDED_STATUS = "HORIZON_INCOMPLETE"
CLASSIFICATION_SCHEMA = "vcex_001_source_classification_row.v1"
LEDGER_SCHEMA = "vcex_001_source_ledger_row.v1"
CLASSIFICATION_KEYS = {
    "attempt_id",
    "attempt_started_sha256",
    "decision_utc",
    "entry_open_utc",
    "hypothesis_id",
    "observed_horizon_bars",
    "required_horizon_bars",
    "reviewed_registry_row_sha256",
    "schema_version",
    "source_signal_id",
    "status",
}
LEDGER_KEYS = {
    "arm",
    "atr14_pips",
    "attempt_id",
    "attempt_started_sha256",
    "candidate_id",
    "cost_to_stop_ratio",
    "decision_utc",
    "direction",
    "entry_open_utc",
    "h",
    "hypothesis_id",
    "p_early",
    "p_late",
    "reviewed_registry_row_sha256",
    "schema_version",
    "slot",
    "source_signal_id",
    "stop_distance_pips",
    "tau",
    "time_exit_utc",
    "year",
}
PAIR_SHARED_FIELDS = (
    "decision_utc",
    "entry_open_utc",
    "time_exit_utc",
    "stop_distance_pips",
    "h",
    "tau",
    "p_early",
    "p_late",
)
M1_KEYS = {"time_utc", "open", "high", "low", "close"}
DESIGN_YEARS = [2016, 2017, 2018, 2019, 2020]
ELAPSED_WEEKS = (date(2020, 12, 31) - date(2016, 1, 4)).days / 7.0
COST_TIERS_PIPS = [1.50, 2.25, 3.00]
RISK_PCT_POINTS = 0.5  # fixed 0.5% of initial equity 100 => +0.5 equity units per 1R
INITIAL_EQUITY = 100.0
HORIZON_MINUTES = 120
PIP = 0.0001
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


@dataclass(frozen=True)
class MappedSignal:
    source_signal_id: str
    arm: str
    direction: str
    decision_utc: datetime
    entry_open_utc: datetime
    time_exit_utc: datetime
    stop_distance_pips: float
    entry_row_index: int
    exit_close_row_index: int
    surveillance_end_index: int
    year: int


@dataclass(frozen=True)
class TradeResult:
    arm: str
    source_signal_id: str
    decision_utc: datetime
    entry_open_utc: datetime
    time_exit_utc: datetime
    entry_time_utc: datetime
    exit_time_utc: datetime
    direction: str
    entry_bid: float
    exit_bid: float
    stop_bid: float
    tp_bid: float
    stop_distance_pips: float
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
    normalized = (
        text[: matches[0].start()]
        + "REVIEWED_RUN_PACKET_SHA256: str | None = None"
        + text[matches[0].end() :]
    )
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


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


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
    out = {"time_utc": at}
    for key in ("open", "high", "low", "close"):
        value = _num(row, key)
        if value <= 0:
            raise EngineeringInvalid(f"M1 {key} must be positive")
        out[key] = value
    if out["high"] < max(out["open"], out["close"]) or out["low"] > min(out["open"], out["close"]):
        raise EngineeringInvalid("M1 OHLC geometry violation")
    return out


def build_observed_market_index(m1_rows: Iterable[dict[str, Any]]) -> ObservedMarketIndex:
    row_refs: list[dict[str, Any]] = []
    times: list[datetime] = []
    previous: datetime | None = None
    for raw in m1_rows:
        if set(raw) != M1_KEYS:
            raise EngineeringInvalid("M1 row schema mismatch")
        at = parse_utc(raw["time_utc"])
        if previous is not None and at <= previous:
            raise EngineeringInvalid(f"non-increasing M1 timestamp: {at.isoformat()}")
        row_refs.append(raw)
        times.append(at)
        previous = at
    return ObservedMarketIndex(m1_rows=tuple(row_refs), m1_times=tuple(times))


def validate_classification_row(row: dict[str, Any]) -> dict[str, Any]:
    if set(row) != CLASSIFICATION_KEYS:
        raise EngineeringInvalid("classification row schema mismatch")
    if row.get("schema_version") != CLASSIFICATION_SCHEMA:
        raise EngineeringInvalid("classification schema_version mismatch")
    if row.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("classification hypothesis mismatch")
    if row.get("attempt_id") != HYP001_ATTEMPT_ID:
        raise EngineeringInvalid("classification attempt mismatch")
    if str(row.get("attempt_started_sha256", "")).upper() != SOURCE_ATTEMPT_STARTED_SHA256:
        raise EngineeringInvalid("classification attempt_started hash mismatch")
    if str(row.get("reviewed_registry_row_sha256", "")).upper() != SOURCE_REGISTRY_ROW_SHA256:
        raise EngineeringInvalid("classification registry row hash mismatch")
    status = str(row["status"])
    if status not in {EXECUTABLE_STATUS, EXCLUDED_STATUS}:
        raise EngineeringInvalid("classification status mismatch")
    source_signal_id = str(row["source_signal_id"])
    if not source_signal_id:
        raise EngineeringInvalid("empty source_signal_id")
    decision = parse_utc(row["decision_utc"])
    entry = parse_utc(row["entry_open_utc"])
    observed = row["observed_horizon_bars"]
    required = row["required_horizon_bars"]
    if not isinstance(observed, int) or isinstance(observed, bool) or observed < 0:
        raise EngineeringInvalid("observed_horizon_bars invalid")
    if required != 8:
        raise EngineeringInvalid("required_horizon_bars must be 8")
    if status == EXECUTABLE_STATUS and observed != 8:
        raise EngineeringInvalid("executable classification must observe 8 bars")
    if status == EXCLUDED_STATUS and observed >= 8:
        raise EngineeringInvalid("excluded classification must observe fewer than 8 bars")
    return {
        "source_signal_id": source_signal_id,
        "status": status,
        "decision_utc": decision,
        "entry_open_utc": entry,
        "observed_horizon_bars": observed,
        "required_horizon_bars": required,
    }


def validate_ledger_row(row: dict[str, Any]) -> dict[str, Any]:
    if set(row) != LEDGER_KEYS:
        raise EngineeringInvalid("ledger row schema mismatch")
    if row.get("schema_version") != LEDGER_SCHEMA:
        raise EngineeringInvalid("ledger schema_version mismatch")
    if row.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("ledger hypothesis mismatch")
    if row.get("attempt_id") != HYP001_ATTEMPT_ID:
        raise EngineeringInvalid("ledger attempt mismatch")
    if str(row.get("attempt_started_sha256", "")).upper() != SOURCE_ATTEMPT_STARTED_SHA256:
        raise EngineeringInvalid("ledger attempt_started hash mismatch")
    if str(row.get("reviewed_registry_row_sha256", "")).upper() != SOURCE_REGISTRY_ROW_SHA256:
        raise EngineeringInvalid("ledger registry row hash mismatch")
    arm = str(row["arm"])
    if arm not in EXPECTED_SIGNAL_COUNTS:
        raise EngineeringInvalid("unknown ledger arm")
    direction = str(row["direction"]).upper()
    if direction not in {"LONG", "SHORT"}:
        raise EngineeringInvalid("invalid ledger direction")
    source_signal_id = str(row["source_signal_id"])
    if not source_signal_id:
        raise EngineeringInvalid("empty ledger source_signal_id")
    decision = parse_utc(row["decision_utc"])
    entry = parse_utc(row["entry_open_utc"])
    time_exit = parse_utc(row["time_exit_utc"])
    if time_exit - entry != timedelta(minutes=HORIZON_MINUTES):
        raise EngineeringInvalid("time_exit is not entry + 120 minutes")
    stop_distance_pips = _num(row, "stop_distance_pips")
    if stop_distance_pips <= 0:
        raise EngineeringInvalid("stop_distance_pips must be positive")
    year = row["year"]
    if not isinstance(year, int) or isinstance(year, bool) or year not in DESIGN_YEARS:
        raise EngineeringInvalid("ledger year outside DESIGN years")
    h = row["h"]
    if not isinstance(h, int) or isinstance(h, bool) or h < 0 or h > 14:
        raise EngineeringInvalid("invalid h")
    out = {
        "arm": arm,
        "source_signal_id": source_signal_id,
        "direction": direction,
        "decision_utc": decision,
        "entry_open_utc": entry,
        "time_exit_utc": time_exit,
        "stop_distance_pips": stop_distance_pips,
        "h": h,
        "tau": _num(row, "tau"),
        "p_early": _num(row, "p_early"),
        "p_late": _num(row, "p_late"),
        "atr14_pips": _num(row, "atr14_pips"),
        "cost_to_stop_ratio": _num(row, "cost_to_stop_ratio"),
        "slot": row["slot"],
        "year": year,
        "candidate_id": str(row["candidate_id"]),
    }
    return out


def load_and_validate_source_population(
    classification_path: Path,
    classification_sha256: str,
    ledger_path: Path,
    ledger_sha256: str,
) -> dict[str, list[dict[str, Any]]]:
    """Validate exact HYP001 classifications+ledger and return paired arm lists."""
    classifications = load_jsonl_file(classification_path, classification_sha256, label="classifications")
    if len(classifications) != EXPECTED_CLASSIFICATION_TOTAL:
        raise EngineeringInvalid(
            f"classification count {len(classifications)} != {EXPECTED_CLASSIFICATION_TOTAL}"
        )
    executable_ids: set[str] = set()
    excluded_ids: set[str] = set()
    seen_class_ids: set[str] = set()
    for row in classifications:
        checked = validate_classification_row(row)
        sid = checked["source_signal_id"]
        if sid in seen_class_ids:
            raise EngineeringInvalid("duplicate classification source_signal_id")
        seen_class_ids.add(sid)
        if checked["status"] == EXECUTABLE_STATUS:
            executable_ids.add(sid)
        else:
            excluded_ids.add(sid)
    if len(executable_ids) != EXPECTED_EXECUTABLE:
        raise EngineeringInvalid(f"executable count {len(executable_ids)} != {EXPECTED_EXECUTABLE}")
    if len(excluded_ids) != EXPECTED_EXCLUDED:
        raise EngineeringInvalid(f"excluded count {len(excluded_ids)} != {EXPECTED_EXCLUDED}")
    if executable_ids & excluded_ids:
        raise EngineeringInvalid("classification status conflict on source_signal_id")

    ledger_rows = load_jsonl_file(ledger_path, ledger_sha256, label="source ledger")
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in EXPECTED_SIGNAL_COUNTS}
    by_id_arm: dict[str, dict[str, dict[str, Any]]] = {}
    for row in ledger_rows:
        checked = validate_ledger_row(row)
        sid = checked["source_signal_id"]
        if sid in excluded_ids:
            raise EngineeringInvalid("excluded source_signal_id mapped to ledger row")
        if sid not in executable_ids:
            raise EngineeringInvalid("ledger source_signal_id not executable")
        arm = checked["arm"]
        id_map = by_id_arm.setdefault(sid, {})
        if arm in id_map:
            raise EngineeringInvalid("duplicate ledger arm for source_signal_id")
        id_map[arm] = checked
        by_arm[arm].append(checked)

    if set(by_id_arm) != executable_ids:
        raise EngineeringInvalid("ledger source_signal_id projection mismatch")
    for sid, arms in by_id_arm.items():
        if set(arms) != {"TRUE", "FOLLOW_CONTROL"}:
            raise EngineeringInvalid("executable source_signal_id missing matched arms")
        true_row = arms["TRUE"]
        follow_row = arms["FOLLOW_CONTROL"]
        for field in PAIR_SHARED_FIELDS:
            if true_row[field] != follow_row[field]:
                raise EngineeringInvalid(f"paired ledger field mismatch: {field}")
        if {true_row["direction"], follow_row["direction"]} != {"LONG", "SHORT"}:
            raise EngineeringInvalid("TRUE/FOLLOW_CONTROL directions must be opposite")
        if true_row["direction"] == follow_row["direction"]:
            raise EngineeringInvalid("TRUE/FOLLOW_CONTROL directions must not match")

    for arm, expected in EXPECTED_SIGNAL_COUNTS.items():
        by_arm[arm].sort(key=lambda item: (item["entry_open_utc"], item["source_signal_id"]))
        if len(by_arm[arm]) != expected:
            raise EngineeringInvalid(f"{arm} ledger count {len(by_arm[arm])} != {expected}")
    # Max one signal per UTC day (by decision date) for TRUE arm; FOLLOW mirrors.
    assert_max_one_per_day(by_arm["TRUE"])
    assert_max_one_per_day(by_arm["FOLLOW_CONTROL"])
    assert_reserved_nonoverlap(by_arm["TRUE"])
    assert_reserved_nonoverlap(by_arm["FOLLOW_CONTROL"])
    return by_arm


def assert_max_one_per_day(signals: list[dict[str, Any]]) -> None:
    seen_days: set[date] = set()
    for signal in signals:
        day = signal["decision_utc"].date()
        if day in seen_days:
            raise EngineeringInvalid("more than one signal per UTC day")
        seen_days.add(day)


def assert_reserved_nonoverlap(signals: list[dict[str, Any]]) -> None:
    ordered = sorted(signals, key=lambda row: row["entry_open_utc"])
    prior_exit: datetime | None = None
    for signal in ordered:
        entry = signal["entry_open_utc"]
        exit_at = signal["time_exit_utc"]
        if prior_exit is not None and entry < prior_exit:
            raise EngineeringInvalid("overlapping reserved intervals in arm")
        prior_exit = exit_at


def map_signal_to_market(signal: dict[str, Any], market: ObservedMarketIndex) -> MappedSignal:
    entry = signal["entry_open_utc"]
    time_exit = signal["time_exit_utc"]
    if time_exit - entry != timedelta(minutes=HORIZON_MINUTES):
        raise EngineeringInvalid("time_exit is not entry + 120 minutes")
    entry_index = bisect_left(market.m1_times, entry)
    if entry_index >= len(market.m1_times) or market.m1_times[entry_index] != entry:
        raise EngineeringInvalid("exact entry M1 bar missing")
    expected_times = [entry + timedelta(minutes=offset) for offset in range(HORIZON_MINUTES)]
    if entry_index + HORIZON_MINUTES > len(market.m1_times):
        raise EngineeringInvalid("right-censored 120-minute M1 horizon")
    observed = list(market.m1_times[entry_index : entry_index + HORIZON_MINUTES])
    if observed != expected_times:
        # Distinguish gap vs incomplete.
        if any(t not in set(market.m1_times) for t in expected_times):
            raise EngineeringInvalid("gap or missing minute in 120-minute horizon")
        raise EngineeringInvalid("non-contiguous 120-minute M1 horizon")
    if market.m1_times[entry_index + HORIZON_MINUTES - 1] + timedelta(minutes=1) != time_exit:
        raise EngineeringInvalid("entry and time-exit window mismatch")
    exit_close_index = entry_index + HORIZON_MINUTES - 1
    surveillance_end = entry_index + HORIZON_MINUTES
    return MappedSignal(
        source_signal_id=str(signal["source_signal_id"]),
        arm=str(signal["arm"]),
        direction=str(signal["direction"]),
        decision_utc=signal["decision_utc"],
        entry_open_utc=entry,
        time_exit_utc=time_exit,
        stop_distance_pips=float(signal["stop_distance_pips"]),
        entry_row_index=entry_index,
        exit_close_row_index=exit_close_index,
        surveillance_end_index=surveillance_end,
        year=int(signal["year"]),
    )


def _validated_market_price_row(market: ObservedMarketIndex, row_index: int) -> dict[str, Any]:
    if row_index < 0 or row_index >= len(market.m1_rows):
        raise EngineeringInvalid("mapped M1 row index is out of range")
    row = validate_m1_row(market.m1_rows[row_index])
    if row["time_utc"] != market.m1_times[row_index]:
        raise EngineeringInvalid("mapped M1 timestamp changed before price simulation")
    return row


def simulate_mapped_signal(mapped: MappedSignal, market: ObservedMarketIndex) -> TradeResult:
    entry_row = _validated_market_price_row(market, mapped.entry_row_index)
    if entry_row["time_utc"] != mapped.entry_open_utc:
        raise EngineeringInvalid("mapped entry timestamp mismatch")
    entry_bid = float(entry_row["open"])
    stop_distance = mapped.stop_distance_pips * PIP
    if stop_distance <= 0 or not math.isfinite(stop_distance):
        raise EngineeringInvalid("stop distance must be positive finite")
    direction = mapped.direction
    sign = 1.0 if direction == "LONG" else -1.0
    if direction == "LONG":
        stop_bid = entry_bid - stop_distance
        tp_bid = entry_bid + stop_distance
    else:
        stop_bid = entry_bid + stop_distance
        tp_bid = entry_bid - stop_distance

    for row_index in range(mapped.entry_row_index, mapped.surveillance_end_index):
        row = _validated_market_price_row(market, row_index)
        at = row["time_utc"]
        open_bid = float(row["open"])
        high_bid = float(row["high"])
        low_bid = float(row["low"])
        # Open beyond adverse stop: exit at open with gross_R <= -1.
        if direction == "LONG":
            open_beyond_stop = open_bid < stop_bid or (
                open_bid <= stop_bid and row_index > mapped.entry_row_index
            )
            open_beyond_tp = open_bid > tp_bid or (
                open_bid >= tp_bid and row_index > mapped.entry_row_index
            )
        else:
            open_beyond_stop = open_bid > stop_bid or (
                open_bid >= stop_bid and row_index > mapped.entry_row_index
            )
            open_beyond_tp = open_bid < tp_bid or (
                open_bid <= tp_bid and row_index > mapped.entry_row_index
            )
        # Entry open equals entry; only post-entry opens can gap through barriers.
        if row_index > mapped.entry_row_index and open_beyond_stop:
            gross_r = sign * (open_bid - entry_bid) / stop_distance
            if not math.isfinite(gross_r):
                raise EngineeringInvalid("non-finite open-gap gross_R")
            # Beyond stop => gross_R must be <= -1; equality at exact stop is -1.
            if direction == "LONG":
                if open_bid < stop_bid and gross_r > -1.0:
                    raise EngineeringInvalid("open-gap adverse gross_R must be <= -1")
            else:
                if open_bid > stop_bid and gross_r > -1.0:
                    raise EngineeringInvalid("open-gap adverse gross_R must be <= -1")
            return TradeResult(
                arm=mapped.arm,
                source_signal_id=mapped.source_signal_id,
                decision_utc=mapped.decision_utc,
                entry_open_utc=mapped.entry_open_utc,
                time_exit_utc=mapped.time_exit_utc,
                entry_time_utc=mapped.entry_open_utc,
                exit_time_utc=at,
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=open_bid,
                stop_bid=stop_bid,
                tp_bid=tp_bid,
                stop_distance_pips=mapped.stop_distance_pips,
                gross_R=gross_r if open_bid != stop_bid else -1.0,
                exit_reason="OPEN_GAP_STOP",
                year=mapped.year,
            )
        if row_index > mapped.entry_row_index and open_beyond_tp:
            gross_r = sign * (open_bid - entry_bid) / stop_distance
            if not math.isfinite(gross_r):
                raise EngineeringInvalid("non-finite open-gap favorable gross_R")
            # Cap favorable open at +1R.
            capped = min(1.0, gross_r)
            return TradeResult(
                arm=mapped.arm,
                source_signal_id=mapped.source_signal_id,
                decision_utc=mapped.decision_utc,
                entry_open_utc=mapped.entry_open_utc,
                time_exit_utc=mapped.time_exit_utc,
                entry_time_utc=mapped.entry_open_utc,
                exit_time_utc=at,
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=open_bid,
                stop_bid=stop_bid,
                tp_bid=tp_bid,
                stop_distance_pips=mapped.stop_distance_pips,
                gross_R=capped,
                exit_reason="OPEN_GAP_TP",
                year=mapped.year,
            )

        # Intra-bar barriers: adverse stop wins when both touch.
        if direction == "LONG":
            hit_stop = low_bid <= stop_bid
            hit_tp = high_bid >= tp_bid
        else:
            hit_stop = high_bid >= stop_bid
            hit_tp = low_bid <= tp_bid
        if hit_stop:
            return TradeResult(
                arm=mapped.arm,
                source_signal_id=mapped.source_signal_id,
                decision_utc=mapped.decision_utc,
                entry_open_utc=mapped.entry_open_utc,
                time_exit_utc=mapped.time_exit_utc,
                entry_time_utc=mapped.entry_open_utc,
                exit_time_utc=at + timedelta(minutes=1),
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=stop_bid,
                stop_bid=stop_bid,
                tp_bid=tp_bid,
                stop_distance_pips=mapped.stop_distance_pips,
                gross_R=-1.0,
                exit_reason="STOP",
                year=mapped.year,
            )
        if hit_tp:
            return TradeResult(
                arm=mapped.arm,
                source_signal_id=mapped.source_signal_id,
                decision_utc=mapped.decision_utc,
                entry_open_utc=mapped.entry_open_utc,
                time_exit_utc=mapped.time_exit_utc,
                entry_time_utc=mapped.entry_open_utc,
                exit_time_utc=at + timedelta(minutes=1),
                direction=direction,
                entry_bid=entry_bid,
                exit_bid=tp_bid,
                stop_bid=stop_bid,
                tp_bid=tp_bid,
                stop_distance_pips=mapped.stop_distance_pips,
                gross_R=1.0,
                exit_reason="TP",
                year=mapped.year,
            )

    exit_row = _validated_market_price_row(market, mapped.exit_close_row_index)
    if exit_row["time_utc"] + timedelta(minutes=1) != mapped.time_exit_utc:
        raise EngineeringInvalid("time-exit close row mismatch")
    exit_bid = float(exit_row["close"])
    gross_r = sign * (exit_bid - entry_bid) / stop_distance
    if not math.isfinite(gross_r):
        raise EngineeringInvalid("non-finite time-exit gross_R")
    return TradeResult(
        arm=mapped.arm,
        source_signal_id=mapped.source_signal_id,
        decision_utc=mapped.decision_utc,
        entry_open_utc=mapped.entry_open_utc,
        time_exit_utc=mapped.time_exit_utc,
        entry_time_utc=mapped.entry_open_utc,
        exit_time_utc=mapped.time_exit_utc,
        direction=direction,
        entry_bid=entry_bid,
        exit_bid=exit_bid,
        stop_bid=stop_bid,
        tp_bid=tp_bid,
        stop_distance_pips=mapped.stop_distance_pips,
        gross_R=gross_r,
        exit_reason="TIME",
        year=mapped.year,
    )


def simulate_signal(signal: dict[str, Any], m1_rows: Iterable[dict[str, Any]]) -> TradeResult:
    market = build_observed_market_index(m1_rows)
    mapped = map_signal_to_market(signal, market)
    return simulate_mapped_signal(mapped, market)


def assert_no_overlap(trades: list[TradeResult]) -> None:
    ordered = sorted(trades, key=lambda row: row.entry_time_utc)
    prior_exit: datetime | None = None
    for trade in ordered:
        if prior_exit is not None and trade.entry_time_utc < prior_exit:
            raise EngineeringInvalid("overlapping trades in arm")
        prior_exit = trade.exit_time_utc


def validate_trade_counts(trades_by_arm: dict[str, list[TradeResult]]) -> None:
    for arm, expected in EXPECTED_SIGNAL_COUNTS.items():
        actual = len(trades_by_arm.get(arm, []))
        if actual != expected:
            raise EngineeringInvalid(f"{arm} trade count {actual} != {expected}")


def net_R(trade: TradeResult, round_trip_cost_pips: float) -> float:
    if trade.stop_distance_pips <= 0 or not math.isfinite(trade.stop_distance_pips):
        raise EngineeringInvalid("stop_distance_pips must be positive finite")
    value = trade.gross_R - (round_trip_cost_pips / trade.stop_distance_pips)
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


def relative_pf(true_pf: dict[str, Any], control_pf: dict[str, Any]) -> dict[str, Any]:
    true_value = _pf_numeric(true_pf)
    control_value = _pf_numeric(control_pf)
    if true_pf["status"] == "NO_LOSS" and control_pf["status"] == "NO_LOSS":
        return {"status": "ZERO_BOTH_NO_LOSS", "value": None}
    if true_value is None or control_value is None:
        return {"status": "UNDEFINED", "value": None}
    if math.isinf(true_value) and not math.isinf(control_value):
        return {"status": "POSITIVE_INFINITY", "value": None}
    if math.isinf(control_value) and not math.isinf(true_value):
        return {"status": "NEGATIVE_INFINITY", "value": None}
    delta = true_value - control_value
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
    vals = [net_R(trade, cost_pips) for trade in sorted(trades, key=lambda row: row.entry_open_utc)]
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


def fixed_initial_equity_drawdown_pct(trades: list[TradeResult], cost_pips: float) -> float:
    equity = INITIAL_EQUITY
    peak = INITIAL_EQUITY
    max_dd = 0.0
    cumulative_net = 0.0
    for trade in sorted(trades, key=lambda row: row.entry_open_utc):
        cumulative_net += net_R(trade, cost_pips)
        equity = INITIAL_EQUITY + RISK_PCT_POINTS * cumulative_net
        if not math.isfinite(equity):
            raise EngineeringInvalid("non-finite equity path")
        peak = max(peak, equity)
        if peak <= 0 or not math.isfinite(peak):
            raise EngineeringInvalid("non-positive or non-finite peak equity")
        dd = (peak - equity) / peak * 100.0
        if not math.isfinite(dd):
            raise EngineeringInvalid("non-finite drawdown")
        max_dd = max(max_dd, dd)
    if not math.isfinite(max_dd):
        raise EngineeringInvalid("non-finite max drawdown")
    return max_dd


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
    namespace: dict[str, Any] = {"__builtins__": __builtins__, "__name__": "_vcex002_verified_dsr"}
    code = compile(payload, str(path), "exec")
    exec(code, namespace)
    if "dsr" not in namespace:
        raise EngineeringInvalid("verified DSR has no dsr function")
    return namespace["dsr"], sha256_bytes(payload)


def dsr_inputs_and_value(
    true_net: list[float], control_net: list[float], workspace_root: Path | None = None
) -> dict[str, Any]:
    if any(not math.isfinite(v) for v in true_net + control_net):
        raise EngineeringInvalid("non-finite DSR input")
    if len(true_net) != EXPECTED_SIGNAL_COUNTS["TRUE"]:
        raise EngineeringInvalid("TRUE DSR observation count mismatch")
    if len(control_net) != EXPECTED_SIGNAL_COUNTS["FOLLOW_CONTROL"]:
        raise EngineeringInvalid("FOLLOW_CONTROL DSR observation count mismatch")
    dsr_func, dsr_sha = load_verified_dsr(workspace_root or Path.cwd())
    true_sr = sample_sharpe(true_net)
    control_sr = sample_sharpe(control_net)
    skew, kurt = population_skew_kurt(true_net)
    var_trials = sample_variance([true_sr, control_sr])
    value = float(dsr_func(true_sr, len(true_net), skew, kurt, var_trials, 2))
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise EngineeringInvalid("DSR is non-finite or out of range")
    return {
        "dsr_tool_sha256": dsr_sha,
        "true_sharpe": true_sr,
        "follow_control_sharpe": control_sr,
        "trial_variance": var_trials,
        "true_skew": skew,
        "true_non_excess_kurtosis": kurt,
        "n_trials": 2,
        "n_obs": len(true_net),
        "dsr": value,
    }


def evaluate_gates(
    trades_by_arm: dict[str, list[TradeResult]], workspace_root: Path | None = None
) -> dict[str, Any]:
    validate_trade_counts(trades_by_arm)
    for trades in trades_by_arm.values():
        assert_no_overlap(trades)

    true_metrics = {cost: arm_cost_metrics(trades_by_arm["TRUE"], cost) for cost in COST_TIERS_PIPS}
    control_metrics = {
        cost: arm_cost_metrics(trades_by_arm["FOLLOW_CONTROL"], cost) for cost in COST_TIERS_PIPS
    }
    yearly = fixed_year_totals(trades_by_arm["TRUE"], 1.50)
    drawdown = fixed_initial_equity_drawdown_pct(trades_by_arm["TRUE"], 1.50)
    dsr_report = dsr_inputs_and_value(
        true_metrics[1.50]["net_R"], control_metrics[1.50]["net_R"], workspace_root
    )
    if dsr_report["n_obs"] != EXPECTED_SIGNAL_COUNTS["TRUE"]:
        raise EngineeringInvalid("DSR n_obs mismatch")
    if dsr_report["n_trials"] != 2:
        raise EngineeringInvalid("DSR n_trials mismatch")
    rel_pf = relative_pf(true_metrics[1.50]["profit_factor"], control_metrics[1.50]["profit_factor"])
    rel_mean = true_metrics[1.50]["mean_net_R"] - control_metrics[1.50]["mean_net_R"]
    cadence = cadence_per_elapsed_week(len(trades_by_arm["TRUE"]))

    gate_rows = [
        ("TRUE cadence", 2.0 <= cadence <= 5.0),
        ("TRUE PF at 1.50 pips", _pf_gate(true_metrics[1.50]["profit_factor"], 1.30, strict=False)),
        ("TRUE PF at 2.25 pips", _pf_gate(true_metrics[2.25]["profit_factor"], 1.25, strict=False)),
        ("TRUE PF at 3.00 pips", _pf_gate(true_metrics[3.00]["profit_factor"], 1.00, strict=True)),
        ("TRUE mean net R at 1.50 pips", true_metrics[1.50]["mean_net_R"] > 0),
        ("TRUE total net R at 1.50 pips", true_metrics[1.50]["total_net_R"] > 0),
        ("TRUE positive DESIGN years at 1.50 pips", yearly["positive_year_count"] >= 3),
        ("TRUE fixed-initial-equity max DD", drawdown < 8.0),
        ("TRUE DSR at 1.50 pips", dsr_report["dsr"] >= 0.95),
        ("TRUE PF minus FOLLOW_CONTROL PF", _relative_pf_gate(rel_pf, 0.15)),
        ("TRUE mean net R minus FOLLOW_CONTROL mean net R", rel_mean >= 0.05),
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
        "follow_control_metrics": control_metrics,
        "yearly": yearly,
        "drawdown_pct": drawdown,
        "dsr": dsr_report,
        "relative_pf": rel_pf,
        "relative_mean_net_R": rel_mean,
        "cadence_per_elapsed_week": cadence,
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
    stat_result = path.stat()
    if getattr(stat_result, "st_nlink", 1) != 1:
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
        "schema": "vcex_002_design_economics_implementation_review_v1",
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
        "source_terminal_path": SOURCE_TERMINAL_REL,
        "source_terminal_sha256": SOURCE_TERMINAL_SHA256,
        "source_receipt_path": SOURCE_RECEIPT_REL,
        "source_receipt_sha256": SOURCE_RECEIPT_SHA256,
        "source_classification_path": SOURCE_CLASSIFICATION_REL,
        "source_classification_sha256": SOURCE_CLASSIFICATION_SHA256,
        "source_ledger_path": SOURCE_LEDGER_REL,
        "source_ledger_sha256": SOURCE_LEDGER_SHA256,
        "source_report_path": SOURCE_REPORT_REL,
        "source_report_sha256": SOURCE_REPORT_SHA256,
        "source_attempt_started_sha256": SOURCE_ATTEMPT_STARTED_SHA256,
        "source_registry_row_sha256": SOURCE_REGISTRY_ROW_SHA256,
        "classification_digest_sha256": CLASSIFICATION_DIGEST_SHA256,
        "canonical_digest_sha256": CANONICAL_DIGEST_SHA256,
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
        "expected_true_signals": EXPECTED_SIGNAL_COUNTS["TRUE"],
        "expected_follow_control_signals": EXPECTED_SIGNAL_COUNTS["FOLLOW_CONTROL"],
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


def validate_latest_registry_authority(
    workspace_root: Path, packet_sha256: str, packet: dict[str, Any] | None = None
) -> dict[str, Any]:
    rows = load_jsonl_file(resolve_workspace_file(workspace_root, REGISTRY_REL), label="candidate registry")
    latest = None
    for row in rows:
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            latest = row
    if latest is None:
        raise EngineeringInvalid("missing HYP002 registry row")
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
        "source_terminal_path": SOURCE_TERMINAL_REL,
        "source_terminal_sha256": SOURCE_TERMINAL_SHA256,
        "source_ledger_path": SOURCE_LEDGER_REL,
        "source_ledger_sha256": SOURCE_LEDGER_SHA256,
        "source_classification_path": SOURCE_CLASSIFICATION_REL,
        "source_classification_sha256": SOURCE_CLASSIFICATION_SHA256,
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


def _source_only_counters_ok(counters: Any) -> bool:
    if not isinstance(counters, dict):
        return False
    return (
        counters.get("economics_executed") is False
        and counters.get("trades_simulated") == 0
        and counters.get("returns_computed") == 0
        and counters.get("post_entry_ohlc_rows_read") == 0
        and counters.get("outcome_fields_emitted") == 0
        and counters.get("mt5_launches") == 0
        and counters.get("mql5_files_created") == 0
        and counters.get("network_calls") == 0
    )


def validate_hyp001_source_chain_before_price(workspace_root: Path, packet: dict[str, Any]) -> dict[str, str]:
    """Bind HYP001 terminal/receipt/report/classifications/ledger before DESIGN price access."""
    bindings = {
        "source_terminal": (packet["source_terminal_path"], SOURCE_TERMINAL_SHA256),
        "source_receipt": (packet["source_receipt_path"], SOURCE_RECEIPT_SHA256),
        "source_report": (packet["source_report_path"], SOURCE_REPORT_SHA256),
        "source_classification": (packet["source_classification_path"], SOURCE_CLASSIFICATION_SHA256),
        "source_ledger": (packet["source_ledger_path"], SOURCE_LEDGER_SHA256),
    }
    out: dict[str, str] = {}
    for name, (rel_path, expected_sha) in bindings.items():
        out[f"{name}_sha256"] = sha256_bytes(
            read_verified_bytes_once(resolve_workspace_file(workspace_root, rel_path), expected_sha)
        )

    terminal = load_json_file(
        resolve_workspace_file(workspace_root, packet["source_terminal_path"]),
        SOURCE_TERMINAL_SHA256,
        label="HYP001 terminal",
    )
    receipt = load_json_file(
        resolve_workspace_file(workspace_root, packet["source_receipt_path"]),
        SOURCE_RECEIPT_SHA256,
        label="HYP001 receipt",
    )
    report = load_json_file(
        resolve_workspace_file(workspace_root, packet["source_report_path"]),
        SOURCE_REPORT_SHA256,
        label="HYP001 report",
    )

    if terminal.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("HYP001 terminal hypothesis mismatch")
    if terminal.get("attempt_id") != HYP001_ATTEMPT_ID:
        raise EngineeringInvalid("HYP001 terminal attempt mismatch")
    if terminal.get("status") != HYP001_PASS_STATUS:
        raise EngineeringInvalid("HYP001 terminal status mismatch")
    if terminal.get("stage0_verdict") != HYP001_STAGE0_VERDICT:
        raise EngineeringInvalid("HYP001 terminal stage0 verdict mismatch")
    if terminal.get("sole_authoritative_completion") is not True:
        raise EngineeringInvalid("HYP001 terminal is not sole authoritative completion")
    if str(terminal.get("reviewed_registry_row_sha256", "")).upper() != SOURCE_REGISTRY_ROW_SHA256:
        raise EngineeringInvalid("HYP001 terminal registry row hash mismatch")
    expected_terminal_artifacts = {
        "attempt_started.json": SOURCE_ATTEMPT_STARTED_SHA256,
        "source_feasibility_receipt.json": SOURCE_RECEIPT_SHA256,
        "vcex_001_source_classifications.jsonl": SOURCE_CLASSIFICATION_SHA256,
        "vcex_001_source_ledger.jsonl": SOURCE_LEDGER_SHA256,
        "vcex_001_source_report.json": SOURCE_REPORT_SHA256,
    }
    if terminal.get("artifact_hashes") != expected_terminal_artifacts:
        raise EngineeringInvalid("HYP001 terminal artifact hash-chain mismatch")
    if not _source_only_counters_ok(terminal.get("source_only_counters")):
        raise EngineeringInvalid("HYP001 terminal sealed counters mismatch")

    if receipt.get("hypothesis_id") != PARENT_CANDIDATE:
        raise EngineeringInvalid("HYP001 receipt hypothesis mismatch")
    if receipt.get("status") != RECEIPT_NON_TERMINAL_STATUS:
        raise EngineeringInvalid("HYP001 receipt must remain non-terminal")
    if receipt.get("terminal_is_sole_authoritative_completion") is not True:
        raise EngineeringInvalid("HYP001 receipt must declare terminal-sole authority")
    if receipt.get("stage0_verdict") != HYP001_STAGE0_VERDICT:
        raise EngineeringInvalid("HYP001 receipt stage0 verdict mismatch")
    if receipt.get("stage0_verdict_is_non_authoritative_calculation") is not True:
        raise EngineeringInvalid("HYP001 receipt stage0 must be non-authoritative")
    # Non-terminal receipt must not claim PASS_SOURCE_FEASIBILITY.
    if HYP001_PASS_STATUS in json.dumps(receipt, sort_keys=True):
        raise EngineeringInvalid("HYP001 receipt must never claim PASS_SOURCE_FEASIBILITY")
    expected_receipt_artifacts = {
        "attempt_started.json": SOURCE_ATTEMPT_STARTED_SHA256,
        "vcex_001_source_classifications.jsonl": SOURCE_CLASSIFICATION_SHA256,
        "vcex_001_source_ledger.jsonl": SOURCE_LEDGER_SHA256,
        "vcex_001_source_report.json": SOURCE_REPORT_SHA256,
    }
    if receipt.get("artifact_hashes") != expected_receipt_artifacts:
        raise EngineeringInvalid("HYP001 receipt artifact hash-chain mismatch")
    if not _source_only_counters_ok(receipt.get("source_only_counters")):
        raise EngineeringInvalid("HYP001 receipt sealed counters mismatch")

    if report.get("hypothesis_id") not in {None, PARENT_CANDIDATE}:
        # Report may nest identity; require sealed counters when present.
        pass
    if isinstance(report, dict) and "source_only_counters" in report:
        if not _source_only_counters_ok(report.get("source_only_counters")):
            raise EngineeringInvalid("HYP001 report sealed counters mismatch")
    return out


def validate_design_receipt(workspace_root: Path) -> dict[str, str]:
    manifest_payload = read_verified_bytes_once(
        resolve_workspace_file(workspace_root, DESIGN_MANIFEST_REL), DESIGN_MANIFEST_SHA256
    )
    collection_plan_payload = read_verified_bytes_once(
        resolve_workspace_file(workspace_root, COLLECTION_PLAN_REL), COLLECTION_PLAN_SHA256
    )
    custodian_payload = read_verified_bytes_once(
        resolve_workspace_file(workspace_root, CUSTODIAN_TOOL_REL), CUSTODIAN_TOOL_SHA256
    )
    receipt = load_json_file(
        resolve_workspace_file(workspace_root, DESIGN_RECEIPT_REL), DESIGN_RECEIPT_SHA256, label="DESIGN receipt"
    )
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
    rows = load_jsonl_file(
        resolve_workspace_file(workspace_root, DESIGN_MANIFEST_REL), DESIGN_MANIFEST_SHA256, label="DESIGN manifest"
    )
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
    # Economics decodes only OHLC timestamps after authority.
    table = parquet_file.read(columns=sorted(M1_KEYS))
    rows: list[dict[str, Any]] = []
    for raw in table.to_pylist():
        value = raw.get("time_utc")
        if not isinstance(value, datetime) or value.tzinfo is not None:
            raise EngineeringInvalid(f"{expected_relative} parquet time_utc is not naive datetime")
        row = {
            "time_utc": value.replace(tzinfo=timezone.utc),
            "open": raw["open"],
            "high": raw["high"],
            "low": raw["low"],
            "close": raw["close"],
        }
        rows.append(validate_m1_row(row))
    if len(rows) != entry["rows"]:
        raise EngineeringInvalid(f"DESIGN shard row count mismatch: {expected_relative}")
    return shard_path, rows


def load_required_m1_rows(
    workspace_root: Path, signals_by_arm: dict[str, list[dict[str, Any]]]
) -> dict[datetime, dict[str, Any]]:
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


def simulate_all(
    signals_by_arm: dict[str, list[dict[str, Any]]], m1_by_time: dict[datetime, dict[str, Any]]
) -> dict[str, list[TradeResult]]:
    for arm, signals in signals_by_arm.items():
        assert_reserved_nonoverlap(signals)
        assert_max_one_per_day(signals)

    market = build_observed_market_index(
        [m1_by_time[t] for t in sorted(m1_by_time)]
    )
    mapped_by_arm: dict[str, list[tuple[dict[str, Any], MappedSignal]]] = {
        arm: [] for arm in EXPECTED_SIGNAL_COUNTS
    }
    for arm, signals in signals_by_arm.items():
        for signal in signals:
            mapped_by_arm[arm].append((signal, map_signal_to_market(signal, market)))
        if len(mapped_by_arm[arm]) != EXPECTED_SIGNAL_COUNTS[arm]:
            raise EngineeringInvalid(
                f"{arm} mapped signal count {len(mapped_by_arm[arm])} != {EXPECTED_SIGNAL_COUNTS[arm]}"
            )

    trades_by_arm: dict[str, list[TradeResult]] = {arm: [] for arm in EXPECTED_SIGNAL_COUNTS}
    for arm, mapped_signals in mapped_by_arm.items():
        for signal, mapped in mapped_signals:
            trades_by_arm[arm].append(simulate_mapped_signal(mapped, market))
        assert_no_overlap(trades_by_arm[arm])
        # Reassert max one/day after mapping.
        days = [trade.decision_utc.date() for trade in trades_by_arm[arm]]
        if len(days) != len(set(days)):
            raise EngineeringInvalid("mapped trades violate max one per UTC day")
    validate_trade_counts(trades_by_arm)
    return trades_by_arm


def trade_to_json(trade: TradeResult) -> dict[str, Any]:
    row = asdict(trade)
    for key in (
        "decision_utc",
        "entry_open_utc",
        "time_exit_utc",
        "entry_time_utc",
        "exit_time_utc",
    ):
        row[key] = iso_z(getattr(trade, key))
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


def _existing_artifact_hashes(evidence_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if not evidence_root.exists():
        return hashes
    for artifact in evidence_root.iterdir():
        if artifact.is_file() and artifact.name != "attempt_terminal.json":
            hashes[artifact.name] = sha256_file(artifact)
    return hashes


def _safe_unlink_attempt_terminal(evidence_root: Path) -> None:
    terminal = Path(evidence_root) / "attempt_terminal.json"
    if terminal.name != "attempt_terminal.json":
        raise EngineeringInvalid("refusing terminal unlink with non-canonical name")
    try:
        info = os.lstat(terminal)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
        raise EngineeringInvalid("attempt_terminal path is a directory; cannot replace safely")
    try:
        os.unlink(terminal)
    except FileNotFoundError:
        return
    except OSError as unlink_exc:
        raise EngineeringInvalid("failed to remove suspect attempt_terminal") from unlink_exc
    try:
        os.lstat(terminal)
    except FileNotFoundError:
        return
    raise EngineeringInvalid("suspect attempt_terminal still present after unlink")


def write_failure_terminal(evidence_root: Path, reason: str, artifact_hashes: dict[str, str]) -> None:
    """Write ENGINEERING_INVALID terminal; never preserve a suspect PASS."""
    present_hashes = dict(artifact_hashes)
    present_hashes.update(_existing_artifact_hashes(evidence_root))
    _safe_unlink_attempt_terminal(evidence_root)
    terminal = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "promotion_evidence": False,
        "reason": reason,
        "artifact_sha256": present_hashes,
        "sole_authoritative_completion": True,
    }
    target = evidence_root / "attempt_terminal.json"
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
        for arm in ("TRUE", "FOLLOW_CONTROL")
        for trade in sorted(trades_by_arm[arm], key=lambda row: row.entry_open_utc)
    ]
    hashes["design_economics_trade_ledger.jsonl"] = write_jsonl_new(
        evidence_root / "design_economics_trade_ledger.jsonl", trade_rows
    )
    arm_metrics = {
        "TRUE": gate_report["true_metrics"],
        "FOLLOW_CONTROL": gate_report["follow_control_metrics"],
    }
    hashes["design_arm_cost_metrics.json"] = write_json_new(
        evidence_root / "design_arm_cost_metrics.json", arm_metrics
    )
    hashes["design_yearly_metrics.json"] = write_json_new(
        evidence_root / "design_yearly_metrics.json", gate_report["yearly"]
    )
    hashes["design_drawdown_metrics.json"] = write_json_new(
        evidence_root / "design_drawdown_metrics.json",
        {
            "true_1p5_max_dd_pct": gate_report["drawdown_pct"],
            "method": "fixed_initial_equity_no_compounding",
            "initial_equity": INITIAL_EQUITY,
            "risk_pct_points": RISK_PCT_POINTS,
        },
    )
    hashes["design_dsr_inputs.json"] = write_json_new(
        evidence_root / "design_dsr_inputs.json", gate_report["dsr"]
    )
    hashes["design_gate_report.json"] = write_json_new(
        evidence_root / "design_gate_report.json", gate_report
    )
    receipt = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "run_packet_sha256": packet_sha,
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "promotion_evidence": False,
        "status": "NON_TERMINAL_DESIGN_ECONOMICS_RECEIPT",
        "terminal_is_sole_authoritative_completion": True,
        "artifact_sha256": dict(hashes),
        "verdict": gate_report["status"],
    }
    # Non-terminal receipt cannot authorize PASS as sole completion.
    if receipt["status"] == "PASS_DESIGN_ECONOMICS_MAY_BUILD_EA":
        raise EngineeringInvalid("receipt must remain non-terminal")
    hashes["design_economics_receipt.json"] = write_json_new(
        evidence_root / "design_economics_receipt.json", receipt
    )
    complete_prior = dict(hashes)
    terminal = {
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": gate_report["status"],
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "promotion_evidence": False,
        "receipt_sha256": hashes["design_economics_receipt.json"],
        "artifact_sha256": complete_prior,
        "sole_authoritative_completion": True,
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
    # HYP001 chain + exact population join must complete before DESIGN price access.
    validate_hyp001_source_chain_before_price(workspace_root, packet)
    signals_by_arm = load_and_validate_source_population(
        resolve_workspace_file(workspace_root, SOURCE_CLASSIFICATION_REL),
        SOURCE_CLASSIFICATION_SHA256,
        resolve_workspace_file(workspace_root, SOURCE_LEDGER_REL),
        SOURCE_LEDGER_SHA256,
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
        artifact_hashes["attempt_started.json"] = write_json_new(
            evidence_root / "attempt_started.json", started
        )
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
        print(
            "DISARMED: import-safe evaluator; pass --run-reviewed-design-economics "
            "with reviewed packet authority."
        )
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
