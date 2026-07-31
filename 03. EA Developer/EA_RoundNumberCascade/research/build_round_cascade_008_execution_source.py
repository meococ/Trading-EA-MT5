#!/usr/bin/env python3
"""One-shot, timestamp-only execution-source builder for Round Cascade HYP008.

Implementation-repair child of engineering-invalid HYP007. Importing this
module is inert. A production read requires both the explicit
``--execute-probe`` switch and an independently reviewed canonical registry-row
SHA in the sentinel below. This program never requests a price or volume
column and cannot calculate a trade or an economic result.

The sole intentional delta from HYP007 is the outcome-blind guard false
positive on safe timestamp diagnostic names: rename the HYP007 opened-style
diagnostic counters to design_shards_read and design_bytes_read, then validate
the three exact safe diagnostic keys as nonnegative plain integers before
bypassing the existing strict substring outcome guard. This is not a
market-rule or Stage-0 rescue.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, NamedTuple, Sequence


HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-008"
PARENT_HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-007"
SOURCE_HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-002"
EA_NAME = "EA_RoundNumberCascade"
FEATURE_FAMILY = "eurusd-round-cascade-nonoverlap-execution-source"
ATTEMPT_ID = "HYP008-EXEC-SOURCE-001"
ARM_ORDER = ("TRUE_0050", "SHIFTED_0025")

PLAN_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE_GUARD_REPAIR_PLAN.md"
)
PLAN_SHA256 = "1A153E509A8E7F5B43C355F86B398DE492F218A0947F695880B37A6DBE6A73CE"
BUILDER_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "build_round_cascade_008_execution_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/tests/"
    "test_build_round_cascade_008_execution_source.py"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REVIEW_RECEIPT_SCHEMA = "round_cascade_008_execution_source_implementation_review.v1"
PROBE_STATUS = "FROZEN_EXECUTION_SOURCE_ONE_SHOT_AUTHORIZED_PRE_RUN"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-008_EXECUTION_SOURCE/"
    f"{ATTEMPT_ID}"
)

PARENT_TERMINAL_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-007_EXECUTION_SOURCE/"
    "HYP007-EXEC-SOURCE-001/attempt_terminal.json"
)
PARENT_TERMINAL_SHA256 = "2135A63C5E30A826A119E6BAFB3276C09E4BDC0ABF5F9D5F3A70465BC163C771"
PARENT_STARTED_SHA256 = "6EA7B5F6B37B1FC8A3F415A734354F89F3C70A493140DB7C632E7F1477CC7A72"

SOURCE_LEDGER_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/"
    "HYP002-SOURCE-PREFLIGHT-001/round_cascade_source_ledger.jsonl"
)
SOURCE_LEDGER_SHA256 = "8172CB237B74CDA6DED53E5BCECB7DD80163A6BE506750FF1567C65CC31B9FBE"
EXPECTED_SOURCE_COUNTS = {"TRUE_0050": 1229, "SHIFTED_0025": 1220}
EXPECTED_NO_EXACT_COUNTS = {"TRUE_0050": 1, "SHIFTED_0025": 0}

M1_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002"
M1_MANIFEST_REL = f"{M1_ROOT_REL}/public/design_manifest.jsonl"
M1_RECEIPT_REL = f"{M1_ROOT_REL}/public/design_receipt.json"
M1_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
M1_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
# Semantic object SHA of the exact historical DESIGN receipt after
# duplicate/nonfinite-safe parse: sha256(canonical_json(parsed_object)).
# Binds every field (including stage_path) without embedding machine paths.
# Distinct from raw-byte receipt SHA; never requires raw == canonical_json.
M1_RECEIPT_OBJECT_SHA256 = (
    "06AA44C3FB7E42BEDB781CD64826036F43CFFD806E2516F15886E848DAE1AD75"
)
M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
COLLECTION_PLAN_REL = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "DATASET-FIVEPERCENT-EURUSD-M1-SPLITVAULT-002_PLAN.md"
)
COLLECTION_PLAN_SHA256 = "F4321C66548B26E867A6CDF0B4B02B3E6B5E1CCA352AC5FB022B3FCA6C320382"
CUSTODIAN_REL = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "splitvault_002_custodian.py"
)
CUSTODIAN_SHA256 = "5F575BD261F556AFBE11ECB740450DA75FAC3FBFEF1666084452D9E031BF3D8C"

REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR_REL = "04. Memory/research/validate_candidate_registry.py"
REGISTRY_VALIDATOR_SHA256 = "B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0"
REGISTRY_SCHEMA_REL = "04. Memory/research/CANDIDATE_REGISTRY.schema.json"
REGISTRY_SCHEMA_SHA256 = "96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C"

# Independent review must replace this exact line before a real read.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

UTC = timezone.utc
EXPECTED_MANIFEST_DATES = 1_555
EXPECTED_DESIGN_ROWS = 1_859_820
DESIGN_START = date(2016, 1, 4)
DESIGN_END = date(2020, 12, 31)
EXPECTED_ARROW_SCHEMA = (
    ("time_server", "timestamp[ns]", True),
    ("time_utc", "timestamp[ns]", True),
    ("utc_offset_h", "int8", True),
    ("open", "float64", True),
    ("high", "float64", True),
    ("low", "float64", True),
    ("close", "float64", True),
    ("tick_volume", "uint64", True),
    ("spread", "int32", True),
    ("real_volume", "uint64", True),
)
SOURCE_ROW_FIELDS = {
    "hypothesis_id", "arm", "direction", "level_pips",
    "decision_bar_start_utc", "decision_time_utc", "planned_entry_time_utc",
    "atr20_pips", "cost_to_stop_ratio_1p5",
}
MANIFEST_ROW_FIELDS = {"bytes", "date", "relative_path", "rows", "sha256"}
M1_RECEIPT_FIELDS = {
    "collection_plan_sha256", "custodian_full_corpus_decoded",
    "custodian_tool_sha256", "design_dates", "design_manifest_sha256",
    "design_rows", "exact_once_status", "private_custody_digest",
    "private_custody_receipt_sha256", "research_holdout_opened",
    "research_validation_opened", "source_attempt_id", "source_bytes",
    "source_footer_length", "source_footer_sha256", "source_footer_start",
    "source_sha256", "stage_path", "stage_role",
    "supervisor_review_base_sha256", "verdict",
}
SEALED_FALSE_FIELDS = {
    "source_build_authorized", "economics_authorized",
    "performance_metrics_authorized", "outcome_prices_authorized",
    "post_entry_ohlc_authorized", "post_entry_price_projection_authorized",
    "validation_authorized", "holdout_authorized", "private_custody_authorized",
    "sealed_access_authorized", "model0_authorized", "model4_authorized",
    "mq5_authorized", "mql5_authorized", "mt5_authorized",
    "optimization_authorized", "charting_authorized",
    "research_validation_access_authorized", "research_holdout_access_authorized",
    "network_authorized", "paid_authorized", "paid_requests_authorized",
    "registry_mutation_allowed", "promotion_authorized", "promotion_eligible",
    "paper_trading_authorized", "live_trading_authorized",
}
SOURCE_ONLY_ZERO_METRICS = {
    "source_feasibility_attempts_consumed": 0,
    "source_runs_executed": 0,
    "post_entry_ohlc_rows_read": 0,
    "outcome_fields_emitted": 0,
    "returns_computed": 0,
    "trades_simulated": 0,
    "performance_trials_executed": 0,
    "economics_executed": False,
    "model0_runs": 0,
    "model4_runs": 0,
    "mt5_launches": 0,
    "mql5_files_created": 0,
    "research_validation_opened": False,
    "research_holdout_opened": False,
    "paid_requests_made": 0,
    "network_calls": 0,
}
# Exact safe timestamp diagnostics renamed from HYP007 *_opened names that
# falsely tripped the outcome-blind substring token "open".
SAFE_TIMESTAMP_DIAGNOSTIC_KEYS = frozenset(
    {
        "design_shards_read",
        "design_timestamp_rows_read",
        "design_bytes_read",
    }
)
AUTHORITY_BINDING_FIELDS = {
    "execution_source_attempt_limit", "execution_source_attempt_id",
    "execution_source_evidence_root", "probe_status",
    "source_feasibility_attempt_limit", "source_feasibility_attempt_id",
    "source_feasibility_evidence_root",
    "independent_implementation_review_status", "independent_pre_run_review_status",
    "independent_quant_prereg_review_status", "reviewed_builder_path",
    "reviewed_builder_base_sha256", "reviewed_test_path", "reviewed_test_sha256",
    "independent_review_receipt_path", "independent_review_receipt_schema",
    "independent_review_receipt_sha256", "source_ledger_path",
    "source_ledger_sha256", "source_true_count", "source_shifted_count",
    "design_manifest_path", "design_manifest_sha256", "design_receipt_path",
    "design_receipt_sha256", "public_m1_source_sha256", "collection_plan_path",
    "collection_plan_sha256", "custodian_tool_path", "custodian_tool_sha256",
    "registry_validator_path", "registry_validator_sha256", "registry_schema_path",
    "registry_schema_sha256", "parent_terminal_path", "parent_terminal_sha256",
}
AUTHORITY_TRUE_FIELDS = {
    "source_run_authorized", "execution_source_only", "source_feasibility_only",
}
REGISTRY_VALIDATION_FIELDS = (
    AUTHORITY_BINDING_FIELDS | AUTHORITY_TRUE_FIELDS | SEALED_FALSE_FIELDS
)
FORBIDDEN_PATH_PARTS = {"private", "validation", "holdout", "sealed"}

SUCCESS_ARTIFACT_ORDER = (
    "round_cascade_008_eligible_source_ledger.jsonl",
    "round_cascade_008_ineligible_source_ledger.jsonl",
    "round_cascade_008_execution_source_report.json",
    "execution_source_receipt.json",
    "attempt_terminal.json",
)

PASS_VERDICT = "PASS_EXECUTION_SOURCE_MAY_DRAFT_HYP009_DESIGN_ECONOMICS"


class ContractError(RuntimeError):
    """Fail-closed engineering or authority contract violation."""


class TimestampIndex(NamedTuple):
    observed_m1: tuple[datetime, ...]
    complete_m5_starts: tuple[datetime, ...]


class ClassificationResult(NamedTuple):
    eligible: tuple[dict[str, object], ...]
    ineligible: tuple[dict[str, object], ...]
    classification_sha256: str


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-F0-9]{64}", value) is not None


def _reject_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ContractError(f"non-finite JSON constant: {value}")


def _json_load(payload: bytes, *, label: str) -> object:
    try:
        return json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_pairs,
            parse_constant=_reject_constant,
        )
    except ContractError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid JSON in {label}") from exc


def parse_canonical_object(payload: bytes, *, label: str) -> dict[str, object]:
    value = _json_load(payload, label=label)
    if type(value) is not dict or canonical_json(value) != payload:
        raise ContractError(f"{label} is not one canonical JSON object")
    return value


def parse_historical_json_object(payload: bytes, *, label: str) -> dict[str, object]:
    """Parse a historical JSON object without requiring canonical bytes.

    Used for the exact SHA-bound public DESIGN receipt. Parsing remains
    duplicate-key-safe and nonfinite-safe; callers must SHA-bind the raw payload
    and require exact expected-object equality.
    """

    value = _json_load(payload, label=label)
    if type(value) is not dict:
        raise ContractError(f"{label} is not one JSON object")
    return value


def parse_canonical_jsonl(payload: bytes, *, label: str) -> list[dict[str, object]]:
    if not payload or not payload.endswith(b"\n") or b"\r" in payload:
        raise ContractError(f"{label} is not canonical LF JSONL")
    rows: list[dict[str, object]] = []
    for ordinal, line in enumerate(payload.splitlines(keepends=True), start=1):
        if line == b"\n":
            raise ContractError(f"blank line in {label}")
        value = _json_load(line[:-1], label=f"{label} line {ordinal}")
        if type(value) is not dict or canonical_json(value) + b"\n" != line:
            raise ContractError(f"{label} line {ordinal} is not canonical")
        rows.append(value)
    return rows


def parse_registry_jsonl(payload: bytes) -> tuple[list[dict[str, object]], list[bytes]]:
    """Parse historical registry formatting while preserving exact row bytes."""

    if not payload or not payload.endswith((b"\n", b"\r\n")):
        raise ContractError("registry must be newline terminated")
    rows: list[dict[str, object]] = []
    raw_rows: list[bytes] = []
    for ordinal, raw in enumerate(payload.splitlines(keepends=True), start=1):
        content = raw[:-2] if raw.endswith(b"\r\n") else raw[:-1]
        value = _json_load(content, label=f"registry line {ordinal}")
        if type(value) is not dict:
            raise ContractError("registry line is not an object")
        rows.append(value)
        raw_rows.append(raw)
    return rows, raw_rows


def reviewed_base_source_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [n for n, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        raise ContractError("builder must contain exactly one review sentinel")
    ordinal = matches[0]
    newline = b"\r\n" if lines[ordinal].endswith(b"\r\n") else b"\n"
    lines[ordinal] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def parse_utc(value: object, *, minute_aligned: bool = True) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ContractError("UTC timestamp must be canonical second-precision Z")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("invalid UTC timestamp") from exc
    if minute_aligned and (result.second or result.microsecond):
        raise ContractError("UTC timestamp must be minute aligned")
    return result


def _utc(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ContractError("timestamp must be datetime")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    result = value.astimezone(UTC)
    if result.second or result.microsecond:
        raise ContractError("timestamp index must be minute aligned")
    return result


def iso_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def source_identity(arm: str, planned: datetime) -> str:
    return f"{arm}|{iso_z(planned)}"


def _finite_number(value: object, *, label: str) -> float:
    if type(value) not in {int, float} or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ContractError(f"invalid finite source number: {label}")
    return float(value)


def load_source_ledger(payload: bytes, expected_sha256: str) -> dict[str, list[dict[str, object]]]:
    if not _is_sha(expected_sha256) or sha256_bytes(payload) != expected_sha256:
        raise ContractError("source ledger SHA binding mismatch")
    rows = parse_canonical_jsonl(payload, label="HYP002 source ledger")
    by_arm: dict[str, list[dict[str, object]]] = {arm: [] for arm in ARM_ORDER}
    seen: set[str] = set()
    previous: dict[str, datetime | None] = {arm: None for arm in ARM_ORDER}
    raw_lines = payload.splitlines(keepends=True)
    for row, raw_line in zip(rows, raw_lines, strict=True):
        if set(row) != SOURCE_ROW_FIELDS or row.get("hypothesis_id") != SOURCE_HYPOTHESIS_ID:
            raise ContractError("source row schema or hypothesis mismatch")
        arm = row.get("arm")
        if arm not in ARM_ORDER:
            raise ContractError("source arm mismatch")
        if row.get("direction") not in {"LONG", "SHORT"}:
            raise ContractError("source direction identity invalid")
        level_pips = row.get("level_pips")
        if type(level_pips) is not int or isinstance(level_pips, bool) or level_pips <= 0:
            raise ContractError("source lattice field is malformed")
        for key in ("decision_bar_start_utc", "decision_time_utc"):
            parse_utc(row[key])
        planned = parse_utc(row["planned_entry_time_utc"])
        _finite_number(row["atr20_pips"], label="atr20_pips")
        _finite_number(row["cost_to_stop_ratio_1p5"], label="cost_to_stop_ratio_1p5")
        identity = source_identity(str(arm), planned)
        if identity in seen:
            raise ContractError("duplicate source identity")
        if previous[str(arm)] is not None and planned <= previous[str(arm)]:
            raise ContractError("source arm is not strictly chronological")
        seen.add(identity)
        previous[str(arm)] = planned
        by_arm[str(arm)].append(
            {
                "arm": arm,
                "planned_entry_time_utc": planned,
                "source_lf_row_sha256": sha256_bytes(raw_line),
            }
        )
    actual = {arm: len(by_arm[arm]) for arm in ARM_ORDER}
    if actual != EXPECTED_SOURCE_COUNTS:
        raise ContractError(f"source input count mismatch: {actual}")
    return by_arm


def build_timestamp_index(rows: Iterable[object]) -> TimestampIndex:
    observed: list[datetime] = []
    complete: list[datetime] = []
    previous: datetime | None = None
    group_start: datetime | None = None
    group_mask = 0
    for raw in rows:
        if isinstance(raw, Mapping):
            if set(raw) != {"time_utc"}:
                raise ContractError("decoded row is not exact timestamp-only shape")
            raw = raw["time_utc"]
        value = _utc(raw)
        if previous is not None and value <= previous:
            raise ContractError("timestamp index must be strictly increasing")
        observed.append(value)
        candidate = value.replace(minute=value.minute - value.minute % 5)
        if group_start != candidate:
            if group_start is not None and group_mask == 0b11111:
                complete.append(group_start)
            group_start = candidate
            group_mask = 0
        group_mask |= 1 << (value.minute % 5)
        previous = value
    if group_start is not None and group_mask == 0b11111:
        complete.append(group_start)
    return TimestampIndex(tuple(observed), tuple(complete))


def _source_projection(row: Mapping[str, object]) -> tuple[str, datetime, str]:
    if set(row) != {"arm", "planned_entry_time_utc", "source_lf_row_sha256"}:
        raise ContractError("internal source projection schema mismatch")
    arm = row["arm"]
    planned = row["planned_entry_time_utc"]
    source_sha = row["source_lf_row_sha256"]
    if (
        arm not in ARM_ORDER or not isinstance(planned, datetime)
        or planned.tzinfo is None or not _is_sha(source_sha)
    ):
        raise ContractError("invalid internal source projection")
    return str(arm), planned.astimezone(UTC), str(source_sha)


def _classification_digest(
    eligible: Sequence[Mapping[str, object]],
    ineligible: Sequence[Mapping[str, object]],
) -> str:
    return sha256_bytes(canonical_json({"eligible": list(eligible), "ineligible": list(ineligible)}))


def classify_sources(
    sources_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
    timestamp_index: TimestampIndex,
) -> ClassificationResult:
    if set(sources_by_arm) != set(ARM_ORDER) or type(timestamp_index) is not TimestampIndex:
        raise ContractError("classifier requires exact arms and timestamp index")
    observed = timestamp_index.observed_m1
    m5 = timestamp_index.complete_m5_starts
    eligible: list[dict[str, object]] = []
    ineligible: list[dict[str, object]] = []
    for arm in ARM_ORDER:
        reserved_exit: datetime | None = None
        blocker_identity: str | None = None
        previous_planned: datetime | None = None
        observed_ordinal = 0
        m5_ordinal = 0
        for raw in sources_by_arm[arm]:
            row_arm, planned, source_sha = _source_projection(raw)
            if row_arm != arm or (previous_planned is not None and planned <= previous_planned):
                raise ContractError("classifier source order mismatch")
            previous_planned = planned
            identity = source_identity(arm, planned)
            while observed_ordinal < len(observed) and observed[observed_ordinal] < planned:
                observed_ordinal += 1
            exact = observed_ordinal < len(observed) and observed[observed_ordinal] == planned
            if not exact:
                next_observed = observed[observed_ordinal] if observed_ordinal < len(observed) else None
                delay = (
                    (next_observed - planned).total_seconds() / 60.0
                    if next_observed is not None else None
                )
                if delay is not None and float(delay).is_integer():
                    delay = int(delay)
                ineligible.append(
                    {
                        "arm": arm,
                        "source_identity": identity,
                        "source_lf_row_sha256": source_sha,
                        "planned_entry_time_utc": iso_z(planned),
                        "status": "NO_EXACT_ENTRY",
                        "next_observed_m1_utc": iso_z(next_observed) if next_observed else None,
                        "delay_minutes": delay,
                    }
                )
                continue
            if reserved_exit is not None and planned < reserved_exit:
                overlap = (reserved_exit - planned).total_seconds() / 60.0
                if float(overlap).is_integer():
                    overlap = int(overlap)
                ineligible.append(
                    {
                        "arm": arm,
                        "source_identity": identity,
                        "source_lf_row_sha256": source_sha,
                        "planned_entry_time_utc": iso_z(planned),
                        "status": "REFRACTORY_INELIGIBLE",
                        "blocking_eligible_identity": blocker_identity,
                        "blocking_reserved_exit_time_utc": iso_z(reserved_exit),
                        "overlap_minutes": overlap,
                    }
                )
                continue
            while m5_ordinal < len(m5) and m5[m5_ordinal] < planned:
                m5_ordinal += 1
            horizon = m5[m5_ordinal : m5_ordinal + 12]
            if len(horizon) != 12:
                raise ContractError(f"fewer than twelve complete M5 starts for {identity}")
            reserved_exit = horizon[-1] + timedelta(minutes=5)
            blocker_identity = identity
            eligible.append(
                {
                    "arm": arm,
                    "source_identity": identity,
                    "source_lf_row_sha256": source_sha,
                    "planned_entry_time_utc": iso_z(planned),
                    "status": "ELIGIBLE_EXACT_ENTRY_NONOVERLAP",
                    "complete_m5_starts": 12,
                    "reserved_exit_time_utc": iso_z(reserved_exit),
                }
            )
    assert_outcome_blind({"eligible": eligible, "ineligible": ineligible})
    digest = _classification_digest(eligible, ineligible)
    return ClassificationResult(tuple(eligible), tuple(ineligible), digest)


def replay_sources_independently(
    sources_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
    timestamp_index: TimestampIndex,
) -> ClassificationResult:
    """Rebuild the canonical classification with independent random-access logic."""

    if set(sources_by_arm) != set(ARM_ORDER) or type(timestamp_index) is not TimestampIndex:
        raise ContractError("replay requires exact arms and timestamp index")
    eligible: list[dict[str, object]] = []
    ineligible: list[dict[str, object]] = []
    for arm in ARM_ORDER:
        blocking: tuple[str, datetime] | None = None
        prior: datetime | None = None
        for raw in sources_by_arm[arm]:
            row_arm, planned, source_sha = _source_projection(raw)
            if row_arm != arm or (prior is not None and planned <= prior):
                raise ContractError("replay source order mismatch")
            prior = planned
            identity = source_identity(arm, planned)
            observed_ordinal = bisect.bisect_left(timestamp_index.observed_m1, planned)
            exact = (
                observed_ordinal < len(timestamp_index.observed_m1)
                and timestamp_index.observed_m1[observed_ordinal] == planned
            )
            if not exact:
                next_observed = (
                    timestamp_index.observed_m1[observed_ordinal]
                    if observed_ordinal < len(timestamp_index.observed_m1) else None
                )
                delay = (
                    (next_observed - planned).total_seconds() / 60.0
                    if next_observed is not None else None
                )
                if delay is not None and float(delay).is_integer():
                    delay = int(delay)
                ineligible.append(
                    {
                        "arm": arm, "source_identity": identity,
                        "source_lf_row_sha256": source_sha,
                        "planned_entry_time_utc": iso_z(planned),
                        "status": "NO_EXACT_ENTRY",
                        "next_observed_m1_utc": iso_z(next_observed) if next_observed else None,
                        "delay_minutes": delay,
                    }
                )
                continue
            if blocking is not None and planned < blocking[1]:
                overlap = (blocking[1] - planned).total_seconds() / 60.0
                if float(overlap).is_integer():
                    overlap = int(overlap)
                ineligible.append(
                    {
                        "arm": arm, "source_identity": identity,
                        "source_lf_row_sha256": source_sha,
                        "planned_entry_time_utc": iso_z(planned),
                        "status": "REFRACTORY_INELIGIBLE",
                        "blocking_eligible_identity": blocking[0],
                        "blocking_reserved_exit_time_utc": iso_z(blocking[1]),
                        "overlap_minutes": overlap,
                    }
                )
                continue
            horizon_ordinal = bisect.bisect_left(timestamp_index.complete_m5_starts, planned)
            horizon = timestamp_index.complete_m5_starts[horizon_ordinal : horizon_ordinal + 12]
            if len(horizon) != 12:
                raise ContractError(f"fewer than twelve complete M5 starts for {identity}")
            exit_at = horizon[-1] + timedelta(minutes=5)
            blocking = (identity, exit_at)
            eligible.append(
                {
                    "arm": arm, "source_identity": identity,
                    "source_lf_row_sha256": source_sha,
                    "planned_entry_time_utc": iso_z(planned),
                    "status": "ELIGIBLE_EXACT_ENTRY_NONOVERLAP",
                    "complete_m5_starts": 12,
                    "reserved_exit_time_utc": iso_z(exit_at),
                }
            )
    assert_outcome_blind({"eligible": eligible, "ineligible": ineligible})
    return ClassificationResult(
        tuple(eligible), tuple(ineligible), _classification_digest(eligible, ineligible)
    )


def require_replay_match(first: ClassificationResult, replay: ClassificationResult) -> None:
    if (
        first.classification_sha256 != replay.classification_sha256
        or first.eligible != replay.eligible
        or first.ineligible != replay.ineligible
    ):
        raise ContractError("independent deterministic replay mismatch")


def _actual_counts(result: ClassificationResult) -> dict[str, dict[str, int]]:
    counts = {
        status: {arm: 0 for arm in ARM_ORDER}
        for status in (
            "ELIGIBLE_EXACT_ENTRY_NONOVERLAP", "REFRACTORY_INELIGIBLE", "NO_EXACT_ENTRY"
        )
    }
    for row in (*result.eligible, *result.ineligible):
        counts[str(row["status"])][str(row["arm"])] += 1
    return counts


def evaluate_stage0(
    result: ClassificationResult,
    sources_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
    timestamp_index: TimestampIndex,
    *,
    replay: ClassificationResult,
) -> dict[str, object]:
    require_replay_match(result, replay)
    expected_identities = {
        source_identity(arm, _source_projection(row)[1])
        for arm in ARM_ORDER for row in sources_by_arm[arm]
    }
    actual_rows = (*result.eligible, *result.ineligible)
    actual_identities = [str(row.get("source_identity")) for row in actual_rows]
    if len(actual_identities) != len(set(actual_identities)) or set(actual_identities) != expected_identities:
        raise ContractError("eligible/ineligible ledgers do not reconcile source identities")
    if {arm: len(sources_by_arm[arm]) for arm in ARM_ORDER} != EXPECTED_SOURCE_COUNTS:
        raise ContractError("Stage-0 source input counts mismatch")
    counts = _actual_counts(result)
    if counts["NO_EXACT_ENTRY"] != EXPECTED_NO_EXACT_COUNTS:
        raise ContractError("fatal NO_EXACT_ENTRY expectation mismatch")

    observed = timestamp_index.observed_m1
    m5 = timestamp_index.complete_m5_starts
    previous_exit: dict[str, datetime | None] = {arm: None for arm in ARM_ORDER}
    for row in result.eligible:
        arm = str(row["arm"])
        planned = parse_utc(row["planned_entry_time_utc"])
        observed_ordinal = bisect.bisect_left(observed, planned)
        if observed_ordinal >= len(observed) or observed[observed_ordinal] != planned:
            raise ContractError("eligible row lacks exact observed M1")
        m5_ordinal = bisect.bisect_left(m5, planned)
        horizon = m5[m5_ordinal : m5_ordinal + 12]
        if len(horizon) != 12:
            raise ContractError("eligible row lacks complete horizon")
        expected_exit = horizon[-1] + timedelta(minutes=5)
        if parse_utc(row["reserved_exit_time_utc"]) != expected_exit:
            raise ContractError("eligible reserved exit mismatch")
        if previous_exit[arm] is not None and planned < previous_exit[arm]:
            raise ContractError("eligible arm-local reservations overlap")
        previous_exit[arm] = expected_exit
    if any(row.get("status") == "HORIZON_INCOMPLETE" for row in actual_rows):
        raise ContractError("horizon-incomplete classifications are forbidden")

    gates = {
        "exact_source_counts": True,
        "identity_reconciliation_exact_once": True,
        "fatal_no_exact_expectation": True,
        "eligible_exact_observed_m1": True,
        "eligible_twelve_complete_m5": True,
        "eligible_nonoverlap_per_arm": True,
        "no_horizon_incomplete": True,
        "independent_replay_hash_match": True,
        "timestamp_only_outcome_blind": True,
        "historical_design_receipt_sha_bound_object_equal": True,
        "canonical_design_manifest_sha_bound": True,
    }
    report = {
        "schema_version": "round_cascade_008_execution_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "verdict": PASS_VERDICT,
        "classification_sha256": result.classification_sha256,
        "source_input_counts": dict(EXPECTED_SOURCE_COUNTS),
        "actual_counts": counts,
        "gates": gates,
        "sealed_permissions": sealed_permissions(),
        "source_only_counters": executed_source_only_counters(),
        "hyp009_drafting_authorized": True,
    }
    assert_outcome_blind(report)
    return report


def assert_outcome_blind(value: object) -> None:
    allowed_entry_exit_keys = {
        "planned_entry_time_utc", "next_observed_m1_utc",
        "reserved_exit_time_utc", "blocking_reserved_exit_time_utc",
        "ELIGIBLE_EXACT_ENTRY_NONOVERLAP", "NO_EXACT_ENTRY",
    }
    allowed_guard_keys = {
        "timestamp_only_outcome_blind",
        "historical_design_receipt_sha_bound_object_equal",
        "canonical_design_manifest_sha_bound",
    }
    forbidden_tokens = (
        "open", "high", "low", "close", "price", "spread", "tick_volume",
        "real_volume", "direction", "trade", "return", "pnl", "profit", "pf",
        "dsr", "performance", "economic", "outcome", "win", "loss", "mfe", "mae",
    )

    def visit(item: object) -> None:
        if isinstance(item, Mapping):
            for raw_key, child in item.items():
                key = str(raw_key)
                if key in SEALED_FALSE_FIELDS:
                    if child is not False:
                        raise ContractError(f"sealed permission is not false: {key}")
                    continue
                if key in SOURCE_ONLY_ZERO_METRICS:
                    expected = SOURCE_ONLY_ZERO_METRICS[key]
                    if key in {"source_feasibility_attempts_consumed", "source_runs_executed"}:
                        if type(child) is not int or isinstance(child, bool) or child not in {0, 1}:
                            raise ContractError(f"invalid execution-source counter: {key}")
                    elif type(child) is not type(expected) or child != expected:
                        raise ContractError(f"nonzero prohibited counter: {key}")
                    continue
                if key in allowed_guard_keys:
                    visit(child)
                    continue
                # Exact safe timestamp diagnostics only. Validate nonnegative
                # plain integers before bypassing the substring token guard.
                # Do not allowlist arbitrary keys containing "open"/price tokens.
                if key in SAFE_TIMESTAMP_DIAGNOSTIC_KEYS:
                    if type(child) is not int or isinstance(child, bool) or child < 0:
                        raise ContractError(f"invalid safe diagnostic counter: {key}")
                    continue
                lowered = key.lower()
                if (
                    (("entry" in lowered or "exit" in lowered) and key not in allowed_entry_exit_keys)
                    or any(token in lowered for token in forbidden_tokens)
                ):
                    raise ContractError(f"forbidden outcome field: {key}")
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)


def expected_parent_terminal() -> dict[str, object]:
    return {
        "artifact_sha256": {"attempt_started.json": PARENT_STARTED_SHA256},
        "attempt_id": "HYP007-EXEC-SOURCE-001",
        "hyp008_drafting_authorized": False,
        "hypothesis_id": PARENT_HYPOTHESIS_ID,
        "promotion_evidence": False,
        "reason": {
            "message": "forbidden outcome field: design_shards_opened",
            "type": "ContractError",
        },
        "schema_version": "round_cascade_007_attempt_terminal.v1",
        "sealed_permissions": sealed_permissions(),
        "source_only_counters": {
            "economics_executed": False,
            "model0_runs": 0,
            "model4_runs": 0,
            "mql5_files_created": 0,
            "mt5_launches": 0,
            "network_calls": 0,
            "outcome_fields_emitted": 0,
            "paid_requests_made": 0,
            "performance_trials_executed": 0,
            "post_entry_ohlc_rows_read": 0,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "returns_computed": 0,
            "source_feasibility_attempts_consumed": 1,
            "source_runs_executed": 1,
            "trades_simulated": 0,
        },
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
    }


def validate_parent_terminal(payload: bytes) -> dict[str, object]:
    if sha256_bytes(payload) != PARENT_TERMINAL_SHA256:
        raise ContractError("parent terminal SHA binding mismatch")
    terminal = _json_load(payload, label="HYP007 parent terminal")
    if type(terminal) is not dict or terminal != expected_parent_terminal():
        raise ContractError("parent terminal object mismatch")
    return terminal


def expected_review_receipt(builder_payload: bytes, test_payload: bytes) -> dict[str, object]:
    return {
        "schema_version": REVIEW_RECEIPT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {
            "path": BUILDER_REL,
            "base_sha256": reviewed_base_source_sha256(builder_payload),
        },
        "reviewed_tests": {"path": TEST_REL, "sha256": sha256_bytes(test_payload)},
        "v1_plan": {"path": PLAN_REL, "sha256": PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }


def validate_review_receipt(
    payload: bytes,
    *,
    expected_sha256: str,
    builder_payload: bytes,
    test_payload: bytes,
) -> dict[str, object]:
    if not _is_sha(expected_sha256) or sha256_bytes(payload) != expected_sha256:
        raise ContractError("independent review receipt SHA mismatch")
    receipt = parse_canonical_object(payload, label="HYP008 review receipt")
    if receipt != expected_review_receipt(builder_payload, test_payload):
        raise ContractError("independent review receipt object mismatch")
    return receipt


def validate_public_metadata(
    receipt_payload: bytes,
    manifest_payload: bytes,
    *,
    expected_dates: int = EXPECTED_MANIFEST_DATES,
    expected_rows: int = EXPECTED_DESIGN_ROWS,
    expected_receipt_sha256: str | None = None,
    expected_receipt_object_sha256: str | None = None,
) -> list[dict[str, object]]:
    # Historical DESIGN receipt: raw-byte SHA + semantic object SHA equality.
    # Parse is duplicate-safe / nonfinite-safe. Do NOT require
    # canonical_json(receipt) == receipt_payload (raw canonical-byte equality).
    if expected_receipt_sha256 is not None:
        if not _is_sha(expected_receipt_sha256) or sha256_bytes(receipt_payload) != expected_receipt_sha256:
            raise ContractError("public DESIGN receipt SHA binding mismatch")
    receipt = parse_historical_json_object(receipt_payload, label="public DESIGN receipt")
    if set(receipt) != M1_RECEIPT_FIELDS:
        raise ContractError("public DESIGN receipt schema mismatch")
    # Exact expected-object equality via frozen sha256(canonical_json(object)).
    # Covers every field (including previously subset-only keys such as
    # stage_path) without hardcoding machine-local paths in source.
    if expected_receipt_object_sha256 is not None:
        if (
            not _is_sha(expected_receipt_object_sha256)
            or sha256_bytes(canonical_json(receipt)) != expected_receipt_object_sha256
        ):
            raise ContractError("public DESIGN receipt object equality mismatch")
    exact = {
        "collection_plan_sha256": COLLECTION_PLAN_SHA256,
        "custodian_full_corpus_decoded": True,
        "custodian_tool_sha256": CUSTODIAN_SHA256,
        "design_dates": expected_dates,
        "design_manifest_sha256": sha256_bytes(manifest_payload),
        "design_rows": expected_rows,
        "exact_once_status": "PASS",
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "source_sha256": M1_SOURCE_SHA256,
        "stage_role": "CUSTODY",
        "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
    }
    if any(receipt.get(key) != expected for key, expected in exact.items()):
        raise ContractError("public DESIGN receipt binding mismatch")
    for key in (
        "private_custody_digest", "private_custody_receipt_sha256",
        "source_footer_sha256", "supervisor_review_base_sha256",
    ):
        if not _is_sha(receipt.get(key)):
            raise ContractError("public DESIGN receipt digest malformed")
    for key in ("source_bytes", "source_footer_length", "source_footer_start"):
        if type(receipt.get(key)) is not int or int(receipt[key]) < 0:
            raise ContractError("public DESIGN receipt numeric field malformed")
    # Manifest remains canonical LF JSONL + exact caller SHA binding.
    # Receipt raw SHA + semantic object SHA must already have passed above.
    entries = parse_canonical_jsonl(manifest_payload, label="public DESIGN manifest")
    if len(entries) != expected_dates:
        raise ContractError("public DESIGN manifest date count mismatch")
    previous: str | None = None
    total_rows = 0
    for row in entries:
        if set(row) != MANIFEST_ROW_FIELDS:
            raise ContractError("public DESIGN manifest row schema mismatch")
        day = row.get("date")
        if not isinstance(day, str):
            raise ContractError("public DESIGN manifest date malformed")
        try:
            date.fromisoformat(day)
        except ValueError as exc:
            raise ContractError("public DESIGN manifest date malformed") from exc
        if previous is not None and day <= previous:
            raise ContractError("public DESIGN manifest dates are not strictly ordered")
        if row.get("relative_path") != f"public/DESIGN/{day}/m1.parquet":
            raise ContractError("public DESIGN manifest relative path mismatch")
        if type(row.get("rows")) is not int or int(row["rows"]) <= 0:
            raise ContractError("public DESIGN manifest row count malformed")
        if type(row.get("bytes")) is not int or int(row["bytes"]) <= 0 or not _is_sha(row.get("sha256")):
            raise ContractError("public DESIGN manifest file binding malformed")
        total_rows += int(row["rows"])
        previous = day
    if total_rows != expected_rows:
        raise ContractError("public DESIGN manifest total rows mismatch")
    if expected_dates == EXPECTED_MANIFEST_DATES and (
        entries[0]["date"] != DESIGN_START.isoformat()
        or entries[-1]["date"] != DESIGN_END.isoformat()
    ):
        raise ContractError("public DESIGN manifest boundary dates mismatch")
    return entries


def decode_timestamp_only_parquet(payload: bytes, *, label: str) -> tuple[dict[str, object], ...]:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ContractError("pyarrow is required for the reviewed timestamp decoder") from exc
    try:
        parquet_file = pq.ParquetFile(pa.BufferReader(payload))
        arrow_types = {
            "timestamp[ns]": pa.timestamp("ns"), "int8": pa.int8(),
            "float64": pa.float64(), "uint64": pa.uint64(), "int32": pa.int32(),
        }
        expected_schema = pa.schema(
            [pa.field(name, arrow_types[type_name], nullable=nullable)
             for name, type_name, nullable in EXPECTED_ARROW_SCHEMA]
        )
        if not parquet_file.schema_arrow.equals(expected_schema, check_metadata=True):
            raise ContractError(f"physical Parquet schema mismatch in {label}")
        if parquet_file.metadata.num_row_groups != 1:
            raise ContractError(f"Parquet row-group count mismatch in {label}")
        table = parquet_file.read(columns=["time_utc"])
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError(f"cannot decode reviewed Parquet shard: {label}") from exc
    if table.column_names != ["time_utc"] or table.num_columns != 1:
        raise ContractError("timestamp decoder returned extra columns")
    rows = tuple(table.to_pylist())
    for row in rows:
        if set(row) != {"time_utc"} or not isinstance(row["time_utc"], datetime):
            raise ContractError("decoded row is not exact timestamp-only shape")
        value = row["time_utc"]
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ContractError("decoded physical timestamp must be naive minute timestamp[ns]")
    return rows


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def stable_read_regular(path_value: Path | str, allowed_root_value: Path | str) -> bytes:
    path = Path(path_value).absolute()
    allowed_root = Path(allowed_root_value).resolve(strict=True)
    if not _inside(path, allowed_root):
        raise ContractError("path is outside allowed root")
    try:
        before_link = path.lstat()
    except OSError as exc:
        raise ContractError("reviewed file is unavailable") from exc
    if (
        not stat.S_ISREG(before_link.st_mode)
        or before_link.st_nlink != 1
        or _is_reparse(before_link)
        or path.is_symlink()
    ):
        raise ContractError("reviewed file must be a single-link regular non-reparse file")
    resolved = path.resolve(strict=True)
    if not _inside(resolved, allowed_root):
        raise ContractError("resolved file is outside allowed root")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(resolved, flags)
    try:
        opened = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after_open = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = resolved.lstat()
    if (
        _file_identity(before_link) != _file_identity(opened)
        or _file_identity(opened) != _file_identity(after_open)
        or _file_identity(after_open) != _file_identity(after_path)
        or not stat.S_ISREG(after_path.st_mode)
        or after_path.st_nlink != 1
        or _is_reparse(after_path)
    ):
        raise ContractError("reviewed file changed during stable read")
    payload = b"".join(chunks)
    if len(payload) != after_open.st_size:
        raise ContractError("stable read size mismatch")
    return payload


def workspace_file(workspace_root: Path, relative_path: str) -> Path:
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts or any(part.lower() in FORBIDDEN_PATH_PARTS for part in pure.parts):
        raise ContractError("forbidden or non-canonical workspace path")
    result = workspace_root.joinpath(*pure.parts).absolute()
    if not _inside(result, workspace_root.resolve(strict=True)):
        raise ContractError("workspace path escapes root")
    return result


def run_registry_validator(workspace_root: Path) -> None:
    validator = workspace_file(workspace_root, REGISTRY_VALIDATOR_REL)
    registry = workspace_file(workspace_root, REGISTRY_REL)
    schema = workspace_file(workspace_root, REGISTRY_SCHEMA_REL)
    validator_before = stable_read_regular(validator, workspace_root)
    schema_before = stable_read_regular(schema, workspace_root)
    registry_before = stable_read_regular(registry, workspace_root)
    if sha256_bytes(validator_before) != REGISTRY_VALIDATOR_SHA256 or sha256_bytes(schema_before) != REGISTRY_SCHEMA_SHA256:
        raise ContractError("canonical registry validator/schema hash mismatch")
    process = subprocess.run(
        [sys.executable, "-B", str(validator), "--registry", str(registry), "--schema", str(schema)],
        cwd=workspace_root, capture_output=True, text=True, timeout=60, check=False,
    )
    if process.returncode != 0 or "CANDIDATE_REGISTRY_OK" not in process.stdout:
        raise ContractError("canonical registry validator rejected authority snapshot")
    if (
        stable_read_regular(validator, workspace_root) != validator_before
        or stable_read_regular(schema, workspace_root) != schema_before
        or stable_read_regular(registry, workspace_root) != registry_before
    ):
        raise ContractError("registry authority files changed during validator execution")


def _expected_authority_bindings(builder_payload: bytes, test_payload: bytes) -> dict[str, object]:
    return {
        "execution_source_attempt_limit": 1,
        "execution_source_attempt_id": ATTEMPT_ID,
        "execution_source_evidence_root": EVIDENCE_ROOT_REL,
        "source_feasibility_attempt_limit": 1,
        "source_feasibility_attempt_id": ATTEMPT_ID,
        "source_feasibility_evidence_root": EVIDENCE_ROOT_REL,
        "probe_status": PROBE_STATUS,
        "independent_implementation_review_status": "PASS",
        "independent_pre_run_review_status": "PASS",
        "independent_quant_prereg_review_status": "PASS",
        "reviewed_builder_path": BUILDER_REL,
        "reviewed_builder_base_sha256": reviewed_base_source_sha256(builder_payload),
        "reviewed_test_path": TEST_REL,
        "reviewed_test_sha256": sha256_bytes(test_payload),
        "independent_review_receipt_path": REVIEW_RECEIPT_REL,
        "independent_review_receipt_schema": REVIEW_RECEIPT_SCHEMA,
        "source_ledger_path": SOURCE_LEDGER_REL,
        "source_ledger_sha256": SOURCE_LEDGER_SHA256,
        "source_true_count": EXPECTED_SOURCE_COUNTS["TRUE_0050"],
        "source_shifted_count": EXPECTED_SOURCE_COUNTS["SHIFTED_0025"],
        "design_manifest_path": M1_MANIFEST_REL,
        "design_manifest_sha256": M1_MANIFEST_SHA256,
        "design_receipt_path": M1_RECEIPT_REL,
        "design_receipt_sha256": M1_RECEIPT_SHA256,
        "public_m1_source_sha256": M1_SOURCE_SHA256,
        "collection_plan_path": COLLECTION_PLAN_REL,
        "collection_plan_sha256": COLLECTION_PLAN_SHA256,
        "custodian_tool_path": CUSTODIAN_REL,
        "custodian_tool_sha256": CUSTODIAN_SHA256,
        "registry_validator_path": REGISTRY_VALIDATOR_REL,
        "registry_validator_sha256": REGISTRY_VALIDATOR_SHA256,
        "registry_schema_path": REGISTRY_SCHEMA_REL,
        "registry_schema_sha256": REGISTRY_SCHEMA_SHA256,
        "parent_terminal_path": PARENT_TERMINAL_REL,
        "parent_terminal_sha256": PARENT_TERMINAL_SHA256,
    }


def validate_registry_authority(
    registry_payload: bytes,
    reviewed_row_sha256: str,
    *,
    builder_payload: bytes,
    test_payload: bytes,
) -> dict[str, object]:
    if not _is_sha(reviewed_row_sha256):
        raise ContractError("reviewed registry row SHA malformed")
    rows, raw_rows = parse_registry_jsonl(registry_payload)
    matches = [ordinal for ordinal, raw in enumerate(raw_rows) if sha256_bytes(raw) == reviewed_row_sha256]
    if len(matches) != 1:
        raise ContractError("reviewed registry row SHA is not unique")
    selected_ordinal = matches[0]
    row = rows[selected_ordinal]
    raw = raw_rows[selected_ordinal]
    if raw != canonical_json(row) + b"\n":
        raise ContractError("selected registry authority row is not canonical LF JSONL")
    latest = [ordinal for ordinal, item in enumerate(rows) if item.get("hypothesis_id") == HYPOTHESIS_ID]
    validation = row.get("validation")
    metrics = row.get("metrics")
    if (
        not latest or latest[-1] != selected_ordinal
        or row.get("record_type") != "hypothesis_state"
        or row.get("schema_version") != "alphafactory_candidate_registry.v1"
        or row.get("hypothesis_id") != HYPOTHESIS_ID
        or row.get("parent_candidate") != PARENT_HYPOTHESIS_ID
        or row.get("ea_name") != EA_NAME
        or row.get("feature_family") != FEATURE_FAMILY
        or row.get("state") != "probe"
        or row.get("model") is not None
        or row.get("source_path") is not None
        or row.get("source_hash") is not None
        or row.get("run_ids") != []
        or row.get("prereg_path") != PLAN_REL
        or row.get("prereg_sha256") != PLAN_SHA256
        or type(validation) is not dict
        or type(metrics) is not dict
    ):
        raise ContractError("registry execution-source identity mismatch")
    if set(validation) != REGISTRY_VALIDATION_FIELDS:
        raise ContractError("registry validation key whitelist mismatch")
    expected_bindings = _expected_authority_bindings(builder_payload, test_payload)
    if any(validation.get(key) != expected for key, expected in expected_bindings.items()):
        raise ContractError("registry execution-source binding mismatch")
    if any(validation.get(key) is not True for key in AUTHORITY_TRUE_FIELDS):
        raise ContractError("registry execution-source true permission mismatch")
    if any(validation.get(key) is not False for key in SEALED_FALSE_FIELDS):
        raise ContractError("registry sealed permission mismatch")
    if not _is_sha(validation.get("independent_review_receipt_sha256")):
        raise ContractError("registry review receipt SHA malformed")
    if set(metrics) != set(SOURCE_ONLY_ZERO_METRICS) or any(
        type(metrics[key]) is not type(expected) or metrics[key] != expected
        for key, expected in SOURCE_ONLY_ZERO_METRICS.items()
    ):
        raise ContractError("registry source-only zero metrics mismatch")
    return row


def sealed_permissions() -> dict[str, bool]:
    return {key: False for key in sorted(SEALED_FALSE_FIELDS)}


def executed_source_only_counters() -> dict[str, object]:
    result = dict(SOURCE_ONLY_ZERO_METRICS)
    result["source_feasibility_attempts_consumed"] = 1
    result["source_runs_executed"] = 1
    return result


def write_new_bytes(path: Path, payload: bytes) -> str:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise ContractError(f"create-new artifact already exists: {path.name}") from exc
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise ContractError("short artifact write")
            view = view[written:]
        os.fsync(descriptor)
        opened = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or _is_reparse(info)
        or opened.st_size != len(payload) or _file_identity(opened) != _file_identity(info)
        or path.read_bytes() != payload
    ):
        raise ContractError("durable create-new artifact verification failed")
    return sha256_bytes(payload)


def write_new_canonical(path: Path, value: object) -> str:
    return write_new_bytes(path, canonical_json(value))


def write_new_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> str:
    payload = b"".join(canonical_json(dict(row)) + b"\n" for row in rows)
    return write_new_bytes(path, payload)


def reserve_attempt(workspace_root: Path, reviewed_row_sha256: str) -> tuple[Path, dict[str, str]]:
    root = workspace_file(workspace_root, EVIDENCE_ROOT_REL)
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink() or _is_reparse(parent.lstat()):
        raise ContractError("evidence parent must not be a reparse point")
    try:
        root.mkdir()
    except FileExistsError as exc:
        raise ContractError("one-use evidence root already exists; replay forbidden") from exc
    started = {
        "schema_version": "round_cascade_008_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "plan_sha256": PLAN_SHA256,
        "source_ledger_sha256": SOURCE_LEDGER_SHA256,
        "design_manifest_sha256": M1_MANIFEST_SHA256,
        "design_receipt_sha256": M1_RECEIPT_SHA256,
        "permissions": {"timestamp_only": True, "hyp009_draft_only": True},
        "sealed_permissions": sealed_permissions(),
        "source_only_counters": executed_source_only_counters(),
    }
    assert_outcome_blind(started)
    digest = write_new_canonical(root / "attempt_started.json", started)
    return root, {"attempt_started.json": digest}


def load_public_timestamp_index(workspace_root: Path) -> tuple[TimestampIndex, dict[str, object]]:
    plan_payload = stable_read_regular(workspace_file(workspace_root, COLLECTION_PLAN_REL), workspace_root)
    custodian_payload = stable_read_regular(workspace_file(workspace_root, CUSTODIAN_REL), workspace_root)
    receipt_payload = stable_read_regular(workspace_file(workspace_root, M1_RECEIPT_REL), workspace_root)
    manifest_payload = stable_read_regular(workspace_file(workspace_root, M1_MANIFEST_REL), workspace_root)
    if (
        sha256_bytes(plan_payload) != COLLECTION_PLAN_SHA256
        or sha256_bytes(custodian_payload) != CUSTODIAN_SHA256
        or sha256_bytes(receipt_payload) != M1_RECEIPT_SHA256
        or sha256_bytes(manifest_payload) != M1_MANIFEST_SHA256
    ):
        raise ContractError("public DESIGN metadata/tool hash mismatch")
    entries = validate_public_metadata(
        receipt_payload,
        manifest_payload,
        expected_receipt_sha256=M1_RECEIPT_SHA256,
        expected_receipt_object_sha256=M1_RECEIPT_OBJECT_SHA256,
    )
    opened_bytes = 0

    def timestamp_rows() -> Iterable[dict[str, object]]:
        nonlocal opened_bytes
        for entry in entries:
            relative_path = str(entry["relative_path"])
            shard = workspace_file(workspace_root, f"{M1_ROOT_REL}/{relative_path}")
            payload = stable_read_regular(shard, workspace_root)
            if len(payload) != entry["bytes"] or sha256_bytes(payload) != entry["sha256"]:
                raise ContractError("manifest-bound public DESIGN shard mismatch")
            rows = decode_timestamp_only_parquet(payload, label=relative_path)
            if len(rows) != entry["rows"]:
                raise ContractError("manifest-bound public DESIGN shard row mismatch")
            for row in rows:
                value = row["time_utc"]
                if not isinstance(value, datetime) or value.date().isoformat() != entry["date"]:
                    raise ContractError("public DESIGN timestamp is outside manifest date")
                yield row
            opened_bytes += len(payload)

    index = build_timestamp_index(timestamp_rows())
    if len(index.observed_m1) != EXPECTED_DESIGN_ROWS:
        raise ContractError("public DESIGN decoded timestamp count mismatch")
    return index, {
        "design_shards_read": len(entries),
        "design_timestamp_rows_read": len(index.observed_m1),
        "design_bytes_read": opened_bytes,
    }


def persist_success(
    root: Path,
    artifact_hashes: dict[str, str],
    result: ClassificationResult,
    report: dict[str, object],
    registry_row_sha256: str,
) -> dict[str, object]:
    assert_outcome_blind({"eligible": result.eligible, "ineligible": result.ineligible, "report": report})
    artifact_hashes[SUCCESS_ARTIFACT_ORDER[0]] = write_new_jsonl(root / SUCCESS_ARTIFACT_ORDER[0], result.eligible)
    artifact_hashes[SUCCESS_ARTIFACT_ORDER[1]] = write_new_jsonl(root / SUCCESS_ARTIFACT_ORDER[1], result.ineligible)
    artifact_hashes[SUCCESS_ARTIFACT_ORDER[2]] = write_new_canonical(root / SUCCESS_ARTIFACT_ORDER[2], report)
    receipt = {
        "schema_version": "round_cascade_008_execution_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": registry_row_sha256,
        "classification_sha256": result.classification_sha256,
        "artifact_sha256": dict(artifact_hashes),
        "verdict": report["verdict"],
        "hyp009_drafting_authorized": True,
        "sealed_permissions": sealed_permissions(),
        "source_only_counters": executed_source_only_counters(),
    }
    assert_outcome_blind(receipt)
    artifact_hashes[SUCCESS_ARTIFACT_ORDER[3]] = write_new_canonical(root / SUCCESS_ARTIFACT_ORDER[3], receipt)
    terminal = {
        "schema_version": "round_cascade_008_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": PASS_VERDICT,
        "artifact_sha256": dict(artifact_hashes),
        "classification_sha256": result.classification_sha256,
        "promotion_evidence": False,
        "hyp009_drafting_authorized": True,
        "sealed_permissions": sealed_permissions(),
        "source_only_counters": executed_source_only_counters(),
    }
    assert_outcome_blind(terminal)
    artifact_hashes[SUCCESS_ARTIFACT_ORDER[4]] = write_new_canonical(root / SUCCESS_ARTIFACT_ORDER[4], terminal)
    return {"evidence_root": str(root), "artifact_sha256": artifact_hashes, "report": report}


def persist_engineering_failure(root: Path, artifact_hashes: dict[str, str], exc: Exception) -> None:
    terminal_path = root / "attempt_terminal.json"
    if terminal_path.exists():
        return
    terminal = {
        "schema_version": "round_cascade_008_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
        "reason": {"type": type(exc).__name__, "message": str(exc)},
        "artifact_sha256": dict(artifact_hashes),
        "promotion_evidence": False,
        "hyp009_drafting_authorized": False,
        "sealed_permissions": sealed_permissions(),
        "source_only_counters": executed_source_only_counters(),
    }
    write_new_canonical(terminal_path, terminal)


def execute_probe(*, workspace_root: Path, run_switch: bool) -> dict[str, object]:
    if not run_switch:
        raise ContractError("explicit run switch is required")
    if not _is_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("review sentinel is disarmed")
    workspace = workspace_root.resolve(strict=True)
    plan_payload = stable_read_regular(workspace_file(workspace, PLAN_REL), workspace)
    builder_payload = stable_read_regular(workspace_file(workspace, BUILDER_REL), workspace)
    test_payload = stable_read_regular(workspace_file(workspace, TEST_REL), workspace)
    registry_payload = stable_read_regular(workspace_file(workspace, REGISTRY_REL), workspace)
    if sha256_bytes(plan_payload) != PLAN_SHA256:
        raise ContractError("frozen plan hash mismatch")
    run_registry_validator(workspace)
    registry_row = validate_registry_authority(
        registry_payload, str(REVIEWED_REGISTRY_ROW_SHA256),
        builder_payload=builder_payload, test_payload=test_payload,
    )
    validation = registry_row["validation"]
    receipt_payload = stable_read_regular(workspace_file(workspace, REVIEW_RECEIPT_REL), workspace)
    validate_review_receipt(
        receipt_payload,
        expected_sha256=str(validation["independent_review_receipt_sha256"]),
        builder_payload=builder_payload,
        test_payload=test_payload,
    )
    parent_payload = stable_read_regular(workspace_file(workspace, PARENT_TERMINAL_REL), workspace)
    validate_parent_terminal(parent_payload)

    root, artifact_hashes = reserve_attempt(workspace, str(REVIEWED_REGISTRY_ROW_SHA256))
    try:
        source_payload = stable_read_regular(workspace_file(workspace, SOURCE_LEDGER_REL), workspace)
        sources = load_source_ledger(source_payload, SOURCE_LEDGER_SHA256)
        timestamp_index, readout = load_public_timestamp_index(workspace)
        result = classify_sources(sources, timestamp_index)
        replay = replay_sources_independently(sources, timestamp_index)
        report = evaluate_stage0(result, sources, timestamp_index, replay=replay)
        report["timestamp_readout"] = readout
        assert_outcome_blind(report)
        return persist_success(root, artifact_hashes, result, report, str(REVIEWED_REGISTRY_ROW_SHA256))
    except Exception as exc:
        persist_engineering_failure(root, artifact_hashes, exc)
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--execute-probe", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = execute_probe(workspace_root=args.workspace_root, run_switch=args.execute_probe)
    except ContractError as exc:
        print(f"HYP008_EXECUTION_SOURCE_ERROR {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
