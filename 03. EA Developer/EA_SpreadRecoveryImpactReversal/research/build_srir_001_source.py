#!/usr/bin/env python3
"""Inert outcome-blind source probe for HYP-SRIR-EURUSD-M5-001.

Importing and default CLI execution cannot read real DESIGN data. A later real
read requires --execute-probe and an exact latest canonical registry row whose
raw SHA replaces the REVIEWED_REGISTRY_ROW_SHA256 sentinel. The computational
surface is intentionally usable with synthetic M1 OHLC+spread rows only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import types
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping, NamedTuple, Sequence


HYPOTHESIS_ID = "HYP-SRIR-EURUSD-M5-001"
EA_NAME = "EA_SpreadRecoveryImpactReversal"
FAMILY = "bar-spread-shock-recovery-price-impact-reversal"
ATTEMPT_ID = "SRIR001-SOURCE-001"

PLAN_REL = (
    "03. EA Developer/EA_SpreadRecoveryImpactReversal/research/"
    "HYP-SRIR-EURUSD-M5-001_SOURCE_FEASIBILITY_PLAN_V2.md"
)
PLAN_SHA256 = "156E3F6A6BC2D9C29CBACF96380E8980B9245717E36EA3656077C15B29BB74C0"
BUILDER_REL = (
    "03. EA Developer/EA_SpreadRecoveryImpactReversal/research/"
    "build_srir_001_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_SpreadRecoveryImpactReversal/research/tests/"
    "test_build_srir_001_source.py"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_SpreadRecoveryImpactReversal/research/evidence/"
    "HYP-SRIR-EURUSD-M5-001_SOURCE_FEASIBILITY/"
    f"{ATTEMPT_ID}"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_SpreadRecoveryImpactReversal/research/"
    "HYP-SRIR-EURUSD-M5-001_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REVIEW_RECEIPT_SCHEMA = "srir_001_source_implementation_review_receipt.v1"
PROBE_STATUS = "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN"

REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR_REL = "04. Memory/research/validate_candidate_registry.py"
REGISTRY_VALIDATOR_SHA256 = "B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0"
REGISTRY_SCHEMA_REL = "04. Memory/research/CANDIDATE_REGISTRY.schema.json"
REGISTRY_SCHEMA_SHA256 = "96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C"

M1_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002"
M1_MANIFEST_REL = f"{M1_ROOT_REL}/public/design_manifest.jsonl"
M1_RECEIPT_REL = f"{M1_ROOT_REL}/public/design_receipt.json"
M1_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
M1_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"

# Independent review must replace this exact sentinel before any real read.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

UTC = timezone.utc
PIP = 0.0001
POINT = 0.00001
MINUTES_PER_M5 = 5
ATR_PERIOD = 20
BURN_IN_ELIGIBLE_DATES = 20
BASELINE_LOOKBACK_DATES = 20
SHOCK_SPREAD_MULT = 2.0
SHOCK_SPREAD_EXCESS_POINTS = 5.0
RECOVERY_SPREAD_MULT = 1.25
BODY_MIN_PIPS = 4.0
BODY_ATR_MULT = 0.50
BODY_RANGE_MIN = 0.65
OUTER_CLOSE_FRAC = 0.80
RETRACE_FRAC = 0.25
RECOVERY_MAX_BARS = 3
HORIZON_BARS = 60
MIN_STOP_PIPS = 6.0
STOP_BUFFER_PIPS = 0.50
COST_PIPS = 1.50
SCAN_MINUTE_START = 7 * 60  # 07:00
SCAN_MINUTE_END = 15 * 60 + 40  # 15:40 inclusive
DOMAIN_M1_MINUTE_END = 16 * 60  # exclusive upper for scan+recovery M1 cover

_BOUNDARY_ULP_COUNT = 4


def _boundary_tol(*values: float) -> float:
    """Finite-only ULP-scaled tolerance. Callers must reject non-finite first."""

    span = 0.0
    for value in values:
        unit = math.ulp(abs(float(value)))
        if unit > span:
            span = unit
    return _BOUNDARY_ULP_COUNT * span


def le_inclusive(left: float, right: float) -> bool:
    a = float(left)
    b = float(right)
    if not math.isfinite(a) or not math.isfinite(b):
        return False
    return a <= b + _boundary_tol(a, b)


def ge_inclusive(left: float, right: float) -> bool:
    a = float(left)
    b = float(right)
    if not math.isfinite(a) or not math.isfinite(b):
        return False
    return a >= b - _boundary_tol(a, b)


def lt_strict(left: float, right: float) -> bool:
    a = float(left)
    b = float(right)
    if not math.isfinite(a) or not math.isfinite(b):
        return False
    return a < b - _boundary_tol(a, b)


def gt_strict(left: float, right: float) -> bool:
    a = float(left)
    b = float(right)
    if not math.isfinite(a) or not math.isfinite(b):
        return False
    return a > b + _boundary_tol(a, b)


DESIGN_START = date(2016, 1, 4)
DESIGN_END = date(2020, 12, 31)
EXPECTED_MANIFEST_DATES = 1_555
EXPECTED_BUSINESS_DECISION_DATES = 1_298
EXPECTED_SUNDAY_DATES = 257
EXPECTED_M1_DESIGN_ROWS = 1_859_820
ELAPSED_CALENDAR_WEEKS = (DESIGN_END - DESIGN_START).days / 7.0
HEX = frozenset("0123456789ABCDEF")
FORBIDDEN_PATH_PARTS = frozenset({"private", "sealed", "validation", "holdout"})
# Signal path uses timestamp, OHLC and producer spread only.
SIGNAL_COLUMNS = ("time_utc", "open", "high", "low", "close", "spread")
PRODUCER_SCHEMA_COLUMNS = (
    "time_server",
    "time_utc",
    "utc_offset_h",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
)
ARM_NAMES = ("TRUE", "FOLLOW_CONTROL")

SEALED_FALSE_FIELDS = (
    "source_build_authorized",
    "economics_authorized",
    "performance_metrics_authorized",
    "outcome_prices_authorized",
    "post_entry_ohlc_authorized",
    "post_entry_price_projection_authorized",
    "validation_authorized",
    "holdout_authorized",
    "private_custody_authorized",
    "sealed_access_authorized",
    "model0_authorized",
    "model4_authorized",
    "mq5_authorized",
    "mql5_authorized",
    "mt5_authorized",
    "optimization_authorized",
    "charting_authorized",
    "research_validation_access_authorized",
    "research_holdout_access_authorized",
    "network_authorized",
    "paid_authorized",
    "paid_requests_authorized",
    "registry_mutation_allowed",
    "promotion_authorized",
    "promotion_eligible",
    "paper_trading_authorized",
    "live_trading_authorized",
)
INTENDED_TRUE_VALIDATION_FIELDS = {
    "source_feasibility_only",
    "source_run_authorized",
}
REGISTRY_BINDING_VALIDATION_FIELDS = {
    "source_feasibility_attempt_limit",
    "source_feasibility_attempt_id",
    "source_feasibility_evidence_root",
    "probe_status",
    "independent_implementation_review_status",
    "independent_pre_run_review_status",
    "independent_quant_prereg_review_status",
    "reviewed_builder_path",
    "reviewed_builder_base_sha256",
    "reviewed_test_path",
    "reviewed_test_sha256",
    "independent_review_receipt_path",
    "independent_review_receipt_schema",
    "independent_review_receipt_sha256",
    "design_m1_manifest_path",
    "design_m1_manifest_sha256",
    "design_m1_receipt_path",
    "design_m1_receipt_sha256",
    "design_m1_source_sha256",
    "registry_validator_path",
    "registry_validator_sha256",
    "registry_schema_path",
    "registry_schema_sha256",
}
REGISTRY_VALIDATION_FIELDS = (
    INTENDED_TRUE_VALIDATION_FIELDS
    | set(SEALED_FALSE_FIELDS)
    | REGISTRY_BINDING_VALIDATION_FIELDS
)
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
OUTCOME_BLIND_COUNTER_EXPECTATIONS = {
    key: value
    for key, value in SOURCE_ONLY_ZERO_METRICS.items()
    if key not in {"source_feasibility_attempts_consumed", "source_runs_executed"}
}

M1_RECEIPT_FIELDS = {
    "collection_plan_sha256",
    "custodian_full_corpus_decoded",
    "custodian_tool_sha256",
    "design_dates",
    "design_manifest_sha256",
    "design_rows",
    "exact_once_status",
    "private_custody_digest",
    "private_custody_receipt_sha256",
    "research_holdout_opened",
    "research_validation_opened",
    "source_bytes",
    "source_footer_length",
    "source_footer_start",
    "source_footer_sha256",
    "source_sha256",
    "source_attempt_id",
    "stage_path",
    "stage_role",
    "supervisor_review_base_sha256",
    "verdict",
}

RECEIPT_NON_TERMINAL_STATUS = "NON_TERMINAL_SOURCE_RESULT_AWAITING_ATTEMPT_TERMINAL"
TERMINAL_PASS_STATUS = "PASS_SOURCE_FEASIBILITY"
TERMINAL_FAIL_STATUS = "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"
TERMINAL_ENGINEERING_INVALID = "ENGINEERING_INVALID_NO_MARKET_VERDICT"
STAGE0_PASS = "PASS_SOURCE_FEASIBILITY_FUTURE_ECONOMICS_PREREG_ONLY"
STAGE0_FAIL = "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"


class ContractError(RuntimeError):
    """A fail-closed contract violation."""


class DecodedShard(NamedTuple):
    columns: tuple[str, ...]
    row_groups: int
    rows: tuple[dict[str, object], ...]


class ImmutableBytesFile(NamedTuple):
    label: str
    payload: bytes

    def is_file(self) -> bool:
        return True

    def read_bytes(self) -> bytes:
        return self.payload

    def read_text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self.payload.decode(encoding, errors=errors)

    def __str__(self) -> str:
        return self.label


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("non-canonical or non-finite JSON value") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("hash input must be bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in HEX for char in value)


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_load(payload: bytes) -> object:
    return json.loads(
        payload.decode("utf-8", errors="strict"),
        object_pairs_hook=_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def parse_canonical_object(payload: bytes, *, label: str) -> dict[str, object]:
    try:
        if type(payload) is not bytes or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
            raise ValueError
        value = _json_load(payload[:-1])
        if type(value) is not dict or canonical_json(value) + b"\n" != payload:
            raise ValueError
        return value
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(f"invalid canonical {label}") from exc


def parse_canonical_jsonl(payload: bytes, *, label: str) -> list[dict[str, object]]:
    try:
        if type(payload) is not bytes or not payload or not payload.endswith(b"\n") or b"\n\n" in payload:
            raise ValueError
        rows: list[dict[str, object]] = []
        for line in payload.splitlines():
            value = _json_load(line)
            if type(value) is not dict or canonical_json(value) != line:
                raise ValueError
            rows.append(value)
        return rows
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(f"invalid canonical {label}") from exc


def parse_registry_jsonl(payload: bytes) -> tuple[list[dict[str, object]], list[bytes]]:
    try:
        if type(payload) is not bytes or not payload:
            raise ValueError("empty registry")
        raw_rows = payload.splitlines(keepends=True)
        rows: list[dict[str, object]] = []
        for line_number, record in enumerate(raw_rows, start=1):
            if (
                not record.endswith(b"\n")
                or record.endswith(b"\r\n")
                or record.count(b"\n") != 1
            ):
                raise ValueError(f"line {line_number}: exact terminal LF required")
            encoding = "utf-8-sig" if line_number == 1 else "utf-8"
            raw = record[:-1].decode(encoding, errors="strict")
            if not raw.strip():
                raise ValueError(f"line {line_number}: blank registry row")
            value = json.loads(
                raw,
                object_pairs_hook=_pairs,
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
            if type(value) is not dict:
                raise ValueError(f"line {line_number}: registry row root is not an object")
            rows.append(value)
        return rows, raw_rows
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid strict registry JSONL") from exc


def validate_registry_snapshot(
    *,
    registry_payload: bytes,
    validator_payload: bytes,
    schema_payload: bytes,
    validator_path: Path,
) -> None:
    if sha256_bytes(validator_payload) != REGISTRY_VALIDATOR_SHA256:
        raise ContractError("canonical registry validator SHA mismatch")
    if sha256_bytes(schema_payload) != REGISTRY_SCHEMA_SHA256:
        raise ContractError("canonical registry schema SHA mismatch")
    try:
        module = types.ModuleType("_srir_verified_candidate_registry_validator")
        module.__file__ = str(Path(validator_path).absolute())
        exec(compile(validator_payload, module.__file__, "exec"), module.__dict__)
        validate = getattr(module, "validate_registry", None)
        if not callable(validate):
            raise ValueError("validate_registry callable missing")
        errors = validate(
            ImmutableBytesFile(REGISTRY_REL, registry_payload),
            ImmutableBytesFile(REGISTRY_SCHEMA_REL, schema_payload),
        )
        if type(errors) is not list or any(type(error) is not str for error in errors):
            raise ValueError("validator returned malformed errors")
        if errors:
            raise ContractError("canonical registry validator reported errors")
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("canonical registry validator failed closed") from exc


def reviewed_base_source_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        raise ContractError("builder must contain exactly one reviewed registry-row sentinel")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n"
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def _is_reparse(info: os.stat_result) -> bool:
    return bool(int(getattr(info, "st_file_attributes", 0)) & 0x400)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_nlink),
        int(getattr(info, "st_file_attributes", 0)),
    )


def _inside(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath(
            (os.path.normcase(str(path)), os.path.normcase(str(root)))
        ) == os.path.normcase(str(root))
    except ValueError:
        return False


def stable_read_regular(path_value: Path | str, allowed_root_value: Path | str) -> bytes:
    try:
        path = Path(path_value).absolute()
        root = Path(allowed_root_value).absolute()
        if not _inside(path, root) or path == root:
            raise ValueError("path escape")
        relative = path.relative_to(root)
        if any(":" in part or part.lower() in FORBIDDEN_PATH_PARTS for part in relative.parts):
            raise ValueError("forbidden path")
        root_info = os.lstat(root)
        if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink() or _is_reparse(root_info):
            raise ValueError("root alias")
        anchors = [(root, _identity(root_info))]
        current = root
        for component in relative.parts[:-1]:
            current = current / component
            info = os.lstat(current)
            if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _is_reparse(info):
                raise ValueError("directory alias")
            anchors.append((current, _identity(info)))
        before = os.lstat(path)
        if (
            not stat.S_ISREG(before.st_mode)
            or path.is_symlink()
            or _is_reparse(before)
            or int(before.st_nlink) != 1
        ):
            raise ValueError("file alias")
        pinned = _identity(before)
        flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(path, flags)
        try:
            if _identity(os.fstat(descriptor)) != pinned:
                raise ValueError("identity changed")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            final = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        payload = b"".join(chunks)
        if (
            _identity(final) != pinned
            or _identity(os.lstat(path)) != pinned
            or len(payload) != pinned[2]
            or any(_identity(os.lstat(directory)) != identity for directory, identity in anchors)
        ):
            raise ValueError("identity changed")
        return payload
    except Exception as exc:
        raise ContractError("path alias/link/reparse or unstable file rejected") from exc


def _canonical_day(value: object) -> str:
    try:
        if type(value) is not str or date.fromisoformat(value).isoformat() != value:
            raise ValueError
        return value
    except Exception as exc:
        raise ContractError("invalid manifest date") from exc


def validate_public_metadata(
    *,
    receipt_payload: bytes,
    manifest_payload: bytes,
    expected_receipt_sha256: str,
    expected_manifest_sha256: str,
) -> list[dict[str, object]]:
    if (
        not _valid_sha(expected_receipt_sha256)
        or not _valid_sha(expected_manifest_sha256)
        or sha256_bytes(receipt_payload) != expected_receipt_sha256
        or sha256_bytes(manifest_payload) != expected_manifest_sha256
    ):
        raise ContractError("public metadata hash mismatch")
    receipt = parse_canonical_object(receipt_payload, label="M1 receipt")
    all_rows = parse_canonical_jsonl(manifest_payload, label="M1 manifest")
    if receipt.get("design_manifest_sha256") != sha256_bytes(manifest_payload):
        raise ContractError("receipt does not bind exact manifest")
    if receipt.get("research_validation_opened") is not False or receipt.get("research_holdout_opened") is not False:
        raise ContractError("receipt did not keep sealed branches closed")
    if type(receipt.get("design_dates")) is not int or receipt["design_dates"] != len(all_rows):
        raise ContractError("receipt design-date count mismatch")
    if (
        set(receipt) != M1_RECEIPT_FIELDS
        or receipt.get("custodian_full_corpus_decoded") is not True
        or receipt.get("exact_once_status") != "PASS"
        or receipt.get("source_sha256") != M1_SOURCE_SHA256
        or receipt.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
        or type(receipt.get("design_rows")) is not int
    ):
        raise ContractError("M1 receipt contract mismatch")
    manifest_fields = {"bytes", "date", "relative_path", "rows", "sha256"}
    previous: str | None = None
    for row in all_rows:
        day = _canonical_day(row.get("date"))
        if (
            set(row) != manifest_fields
            or (previous is not None and day <= previous)
            or row.get("relative_path") != f"public/DESIGN/{day}/m1.parquet"
            or type(row.get("bytes")) is not int
            or row["bytes"] <= 0
            or type(row.get("rows")) is not int
            or row["rows"] <= 0
            or not _valid_sha(row.get("sha256"))
        ):
            raise ContractError("manifest path/schema/hash/bytes/rows contract mismatch")
        previous = day
    selected_days = tuple(str(row["date"]) for row in all_rows)
    if (
        len(selected_days) != EXPECTED_MANIFEST_DATES
        or not selected_days
        or selected_days[0] != DESIGN_START.isoformat()
        or selected_days[-1] != DESIGN_END.isoformat()
        or any(not DESIGN_START <= date.fromisoformat(day) <= DESIGN_END for day in selected_days)
        or sum(date.fromisoformat(day).weekday() < 5 for day in selected_days)
        != EXPECTED_BUSINESS_DECISION_DATES
        or sum(date.fromisoformat(day).weekday() == 6 for day in selected_days)
        != EXPECTED_SUNDAY_DATES
        or any(date.fromisoformat(day).weekday() == 5 for day in selected_days)
    ):
        raise ContractError("production DESIGN date boundary mismatch")
    total = sum(int(row["rows"]) for row in all_rows)
    if total != EXPECTED_M1_DESIGN_ROWS or receipt.get("design_rows") != total:
        raise ContractError("M1 DESIGN row-count contract mismatch")
    return all_rows


def all_source_dates(entries: Sequence[Mapping[str, object]]) -> tuple[date, ...]:
    selected = tuple(
        date.fromisoformat(_canonical_day(row.get("date"))) for row in entries
    )
    if selected != tuple(sorted(selected)) or len(selected) != len(set(selected)):
        raise ContractError("invalid source-date contract")
    return selected


def weekday_decision_dates(entries: Sequence[Mapping[str, object]]) -> tuple[date, ...]:
    selected = tuple(
        day
        for day in all_source_dates(entries)
        if day.weekday() < 5
    )
    if len(entries) == EXPECTED_MANIFEST_DATES and len(selected) != EXPECTED_BUSINESS_DECISION_DATES:
        raise ContractError("weekday decision-date count mismatch")
    if any(day.weekday() >= 5 for day in selected):
        raise ContractError("invalid business-date contract")
    return selected


def eligible_baseline_dates(source_dates: Sequence[date]) -> tuple[date, ...]:
    """V2 baseline calendar: bound manifest dates, Monday through Friday only."""

    selected = tuple(day for day in source_dates if day.weekday() < 5)
    if any(day.weekday() >= 5 for day in selected):
        raise ContractError("weekend leaked into eligible baseline calendar")
    return selected


def _finite_price(value: object) -> float:
    if type(value) not in {float, int} or isinstance(value, bool):
        raise ContractError("invalid OHLC type")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ContractError("invalid OHLC value")
    return number


def _finite_tick_volume(value: object) -> int:
    if type(value) not in {float, int} or isinstance(value, bool):
        raise ContractError("invalid tick_volume type")
    number = float(value)
    if not math.isfinite(number) or number < 0 or number != int(number):
        raise ContractError("invalid tick_volume value")
    return int(number)


def _finite_real_volume(value: object) -> float:
    if type(value) not in {float, int} or isinstance(value, bool):
        raise ContractError("invalid real_volume type")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ContractError("invalid real_volume value")
    return number


def _producer_spread(value: object) -> float:
    """Accept finite producer spread; non-positive is valid as a raw field but not usable."""

    if type(value) not in {float, int} or isinstance(value, bool):
        raise ContractError("invalid spread type")
    number = float(value)
    if not math.isfinite(number):
        raise ContractError("non-finite spread")
    return number


def positive_finite_spread(value: object) -> float | None:
    """Return positive finite producer points, else None (unavailable)."""

    if type(value) not in {float, int} or isinstance(value, bool):
        return None
    number = float(value)
    if not math.isfinite(number) or not gt_strict(number, 0.0):
        return None
    return number


def _as_utc(value: object) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ContractError("timestamp must be explicit UTC")
    return value.astimezone(UTC)


def _ohlc(row: Mapping[str, object]) -> tuple[float, float, float, float]:
    try:
        values = tuple(_finite_price(row[name]) for name in ("open", "high", "low", "close"))
    except KeyError as exc:
        raise ContractError("row is missing OHLC") from exc
    open_price, high, low, close = values
    if not (low <= open_price <= high and low <= close <= high):
        raise ContractError("invalid OHLC ordering")
    return open_price, high, low, close


def _sign(value: float) -> int:
    if not math.isfinite(value) or value == 0.0:
        return 0
    return 1 if value > 0.0 else -1


def _iso_z(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _minute_aligned(at: datetime) -> bool:
    local = _as_utc(at)
    return local.second == 0 and local.microsecond == 0


def _m5_floor(at: datetime) -> datetime:
    local = _as_utc(at)
    return local.replace(minute=local.minute - local.minute % MINUTES_PER_M5, second=0, microsecond=0)


def slot_index(at: datetime) -> int:
    local = _as_utc(at)
    if local.minute % MINUTES_PER_M5 != 0 or local.second or local.microsecond:
        raise ContractError("slot requires exact M5 start")
    return local.hour * 12 + local.minute // MINUTES_PER_M5


def in_scan_domain(at: datetime) -> bool:
    local = _as_utc(at)
    if local.weekday() >= 5:
        return False
    if local.second or local.microsecond or local.minute % MINUTES_PER_M5 != 0:
        return False
    minute_of_day = local.hour * 60 + local.minute
    return SCAN_MINUTE_START <= minute_of_day <= SCAN_MINUTE_END


def scan_domain_slots_per_day() -> int:
    return (SCAN_MINUTE_END - SCAN_MINUTE_START) // MINUTES_PER_M5 + 1


def in_scan_recovery_m1_domain(at: datetime) -> bool:
    """M1 minutes covering scan domain plus three-bar recovery window."""

    local = _as_utc(at)
    if local.weekday() >= 5 or local.second or local.microsecond:
        return False
    minute_of_day = local.hour * 60 + local.minute
    return SCAN_MINUTE_START <= minute_of_day < DOMAIN_M1_MINUTE_END


def _true_range(high: float, low: float, previous_close: float) -> float:
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def build_complete_m5(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Aggregate exact UTC M5 blocks; never bridge gaps; incomplete blocks discarded."""

    ordered: list[tuple[datetime, Mapping[str, object]]] = []
    for row in rows:
        try:
            at = _as_utc(row["time_utc"])
        except KeyError as exc:
            raise ContractError("M1 row missing time_utc") from exc
        if not _minute_aligned(at):
            raise ContractError("M1 timestamp is not minute aligned")
        _ohlc(row)
        if "spread" not in row:
            raise ContractError("M1 row missing spread")
        # Reject non-finite at parse; non-positive stays and makes block spread unavailable.
        if type(row["spread"]) not in {float, int} or isinstance(row["spread"], bool):
            raise ContractError("invalid spread type")
        if not math.isfinite(float(row["spread"])):
            raise ContractError("non-finite spread")
        ordered.append((at, row))
    times = [item[0] for item in ordered]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ContractError("M1 timestamps are duplicated or unordered")
    groups: dict[datetime, list[tuple[datetime, Mapping[str, object]]]] = defaultdict(list)
    for at, row in ordered:
        groups[_m5_floor(at)].append((at, row))

    complete: list[dict[str, object]] = []
    incomplete = 0
    for bucket in sorted(groups):
        group = groups[bucket]
        expected = [bucket + timedelta(minutes=index) for index in range(MINUTES_PER_M5)]
        observed = [item[0] for item in group]
        if len(group) != MINUTES_PER_M5 or observed != expected:
            incomplete += 1
            continue
        ohlc_values = [_ohlc(row) for _, row in group]
        minute_open = [item[0] for item in ohlc_values]
        minute_high = [item[1] for item in ohlc_values]
        minute_low = [item[2] for item in ohlc_values]
        minute_close = [item[3] for item in ohlc_values]
        spreads: list[float | None] = []
        block_spread: float | None = None
        available = True
        for _, row in group:
            points = positive_finite_spread(row["spread"])
            spreads.append(points)
            if points is None:
                available = False
            elif block_spread is None or points > block_spread:
                block_spread = points
        if not available:
            block_spread = None
        complete.append(
            {
                "time_utc": bucket,
                "availability_utc": bucket + timedelta(minutes=MINUTES_PER_M5),
                "date": bucket.date(),
                "slot": slot_index(bucket),
                "open": minute_open[0],
                "high": max(minute_high),
                "low": min(minute_low),
                "close": minute_close[-1],
                "block_spread_points": block_spread,
                "spread_available": block_spread is not None and gt_strict(float(block_spread), 0.0),
            }
        )
    return complete, {
        "observed_bins": len(groups),
        "complete_bins": len(complete),
        "incomplete_bins": incomplete,
        "input_m1_rows": len(ordered),
    }


def attach_wilder_atr20(bars: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Prior closed Wilder ATR20 across contiguous completed M5; gap resets."""

    ordered = sorted(bars, key=lambda row: _as_utc(row["time_utc"]))
    times = [_as_utc(row["time_utc"]) for row in ordered]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ContractError("M5 bars are duplicated or unordered")
    enriched: list[dict[str, object]] = []
    tr_seed: list[float] = []
    atr_value: float | None = None
    prev_close: float | None = None
    prev_time: datetime | None = None
    for index, bar in enumerate(ordered):
        at = times[index]
        open_price, high, low, close = (
            float(bar["open"]),
            float(bar["high"]),
            float(bar["low"]),
            float(bar["close"]),
        )
        row = dict(bar)
        row["time_utc"] = at
        row["availability_utc"] = _as_utc(bar["availability_utc"])
        row["atr20"] = None
        row["atr20_prev"] = None
        row["contiguous_prev"] = False
        if prev_time is None or at - prev_time != timedelta(minutes=MINUTES_PER_M5) or prev_close is None:
            # Gap or start: reset ATR state; no TR without previous close.
            tr_seed = []
            atr_value = None
            row["atr20_prev"] = None
            enriched.append(row)
            prev_time = at
            prev_close = close
            continue
        row["contiguous_prev"] = True
        # Closed ATR available for this bar is previous bar's ATR (excludes current TR).
        row["atr20_prev"] = atr_value
        tr = _true_range(high, low, prev_close)
        if not math.isfinite(tr) or tr < 0:
            raise ContractError("invalid true range")
        if atr_value is None:
            tr_seed.append(tr)
            if len(tr_seed) == ATR_PERIOD:
                atr_value = sum(tr_seed) / float(ATR_PERIOD)
                if not math.isfinite(atr_value) or atr_value <= 0:
                    atr_value = None
                    tr_seed = []
        else:
            atr_value = (atr_value * (ATR_PERIOD - 1) + tr) / float(ATR_PERIOD)
            if not math.isfinite(atr_value) or atr_value <= 0:
                atr_value = None
                tr_seed = []
        row["atr20"] = atr_value
        enriched.append(row)
        prev_time = at
        prev_close = close
    return enriched


def build_slot_spread_by_date(
    bars: Sequence[Mapping[str, object]],
) -> dict[date, dict[int, float | None]]:
    """Map source date -> M5 slot -> max positive finite block spread (None if unavailable)."""

    by_date: dict[date, dict[int, float | None]] = defaultdict(dict)
    for bar in bars:
        day = bar["date"] if type(bar.get("date")) is date else _as_utc(bar["time_utc"]).date()
        slot = int(bar["slot"])
        if slot in by_date[day]:
            raise ContractError("duplicate M5 slot on source date")
        if bar.get("spread_available") is True and bar.get("block_spread_points") is not None:
            by_date[day][slot] = float(bar["block_spread_points"])
        else:
            by_date[day][slot] = None
    return dict(by_date)


def prior_20_baseline(
    *,
    source_dates: Sequence[date],
    date_index: Mapping[date, int],
    slot_maps: Mapping[date, Mapping[int, float | None]],
    day: date,
    slot: int,
) -> float | None:
    """Exact prior-20 eligible-weekday median; no fill; all 20 must be available."""

    if day not in date_index:
        return None
    index = date_index[day]
    if index < BASELINE_LOOKBACK_DATES:
        return None
    values: list[float] = []
    for prior in source_dates[index - BASELINE_LOOKBACK_DATES : index]:
        slot_map = slot_maps.get(prior)
        if slot_map is None or slot not in slot_map:
            return None
        points = slot_map[slot]
        if points is None or not math.isfinite(float(points)) or not gt_strict(float(points), 0.0):
            return None
        values.append(float(points))
    if len(values) != BASELINE_LOOKBACK_DATES:
        return None
    return float(median(values))


def is_qualifying_shock(
    bar: Mapping[str, object],
    *,
    baseline: float,
) -> dict[str, object] | None:
    """Return shock payload if bar qualifies, else None."""

    if not math.isfinite(baseline) or not gt_strict(baseline, 0.0):
        return None
    if bar.get("spread_available") is not True or bar.get("block_spread_points") is None:
        return None
    spread_pts = float(bar["block_spread_points"])
    if not ge_inclusive(spread_pts, SHOCK_SPREAD_MULT * baseline):
        return None
    if not ge_inclusive(spread_pts - baseline, SHOCK_SPREAD_EXCESS_POINTS):
        return None
    atr_prev = bar.get("atr20_prev")
    if (
        type(atr_prev) not in {int, float}
        or isinstance(atr_prev, bool)
        or not math.isfinite(float(atr_prev))
        or float(atr_prev) <= 0
    ):
        return None
    open_price = float(bar["open"])
    high = float(bar["high"])
    low = float(bar["low"])
    close = float(bar["close"])
    body = close - open_price
    body_abs = abs(body)
    body_pips = body_abs / PIP
    min_body_pips = max(BODY_MIN_PIPS, BODY_ATR_MULT * float(atr_prev) / PIP)
    if not ge_inclusive(body_pips, min_body_pips):
        return None
    bar_range = high - low
    if not math.isfinite(bar_range) or not gt_strict(bar_range, 0.0):
        return None
    if not ge_inclusive(body_abs / bar_range, BODY_RANGE_MIN):
        return None
    sign = _sign(body)
    if sign == 0:
        return None
    if sign > 0:
        # Upper 20% of range.
        if not ge_inclusive((close - low) / bar_range, OUTER_CLOSE_FRAC):
            return None
    else:
        if not ge_inclusive((high - close) / bar_range, OUTER_CLOSE_FRAC):
            return None
    return {
        "shock_time": _as_utc(bar["time_utc"]),
        "shock_date": _as_utc(bar["time_utc"]).date(),
        "slot": int(bar["slot"]),
        "baseline": float(baseline),
        "block_spread_points": spread_pts,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "body": body,
        "body_abs": body_abs,
        "sign": sign,
        "atr20_prev": float(atr_prev),
    }


def recovery_qualifies(
    *,
    shock: Mapping[str, object],
    recovery: Mapping[str, object],
    path_bars: Sequence[Mapping[str, object]],
) -> bool:
    """Causal recovery rules on recovery bar using frozen shock baseline."""

    if recovery.get("spread_available") is not True or recovery.get("block_spread_points") is None:
        return False
    rec_spread = float(recovery["block_spread_points"])
    baseline = float(shock["baseline"])
    if not le_inclusive(rec_spread, RECOVERY_SPREAD_MULT * baseline):
        return False
    rec_open = float(recovery["open"])
    rec_close = float(recovery["close"])
    rec_body = rec_close - rec_open
    rec_sign = _sign(rec_body)
    if rec_sign == 0 or rec_sign != -int(shock["sign"]):
        return False
    body_abs = float(shock["body_abs"])
    shock_close = float(shock["close"])
    if int(shock["sign"]) > 0:
        if not le_inclusive(rec_close, shock_close - RETRACE_FRAC * body_abs):
            return False
    else:
        if not ge_inclusive(rec_close, shock_close + RETRACE_FRAC * body_abs):
            return False
    # No new extreme from t+1 through r inclusive (path_bars).
    shock_high = float(shock["high"])
    shock_low = float(shock["low"])
    for bar in path_bars:
        if int(shock["sign"]) > 0:
            if gt_strict(float(bar["high"]), shock_high):
                return False
        else:
            if lt_strict(float(bar["low"]), shock_low):
                return False
    return True


def planned_stop_pips(*, shock: Mapping[str, object], recovery_close: float) -> float:
    if int(shock["sign"]) > 0:
        # Up shock / TRUE short.
        distance = (float(shock["high"]) - recovery_close) / PIP + STOP_BUFFER_PIPS
    else:
        distance = (recovery_close - float(shock["low"])) / PIP + STOP_BUFFER_PIPS
    if not math.isfinite(distance):
        raise ContractError("non-finite planned stop")
    return max(MIN_STOP_PIPS, float(distance))


def select_raw_signals(
    bars: Sequence[Mapping[str, object]],
    *,
    source_dates: Sequence[date],
    burn_in_dates: set[date],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Shock -> recovery state machine; first recovery decision per UTC date."""

    ordered = sorted(bars, key=lambda row: _as_utc(row["time_utc"]))
    date_index = {day: index for index, day in enumerate(source_dates)}
    slot_maps = build_slot_spread_by_date(ordered)
    selected: list[dict[str, object]] = []
    consumed: set[date] = set()
    funnel: Counter[str] = Counter()
    pending: dict[str, object] | None = None
    pending_path: list[dict[str, object]] = []
    bar_by_time = {_as_utc(bar["time_utc"]): bar for bar in ordered}

    for index, bar in enumerate(ordered):
        at = _as_utc(bar["time_utc"])
        day = at.date()
        # Contiguity break cancels pending (gap / incomplete chain).
        if pending is not None:
            expected = _as_utc(pending["last_seen"]) + timedelta(minutes=MINUTES_PER_M5)
            if at != expected:
                funnel["GAP_CANCEL"] += 1
                pending = None
                pending_path = []

        baseline: float | None = None
        if day not in burn_in_dates and day in date_index and in_scan_domain(at):
            baseline = prior_20_baseline(
                source_dates=source_dates,
                date_index=date_index,
                slot_maps=slot_maps,
                day=day,
                slot=int(bar["slot"]),
            )

        shock_payload = None
        if (
            day not in burn_in_dates
            and in_scan_domain(at)
            and baseline is not None
        ):
            shock_payload = is_qualifying_shock(bar, baseline=baseline)
            if shock_payload is not None:
                if pending is not None:
                    funnel["SHOCK_REPLACEMENT"] += 1
                pending = {
                    **shock_payload,
                    "shock_index": index,
                    "bars_seen": 0,
                    "last_seen": at,
                }
                pending_path = []
                funnel["SHOCK"] += 1

        if pending is None:
            continue

        # Do not evaluate recovery on the shock bar itself.
        if index <= int(pending["shock_index"]):
            pending["last_seen"] = at
            continue

        # Contiguous recovery path tracking.
        pending_path.append(dict(bar))
        pending["bars_seen"] = int(pending["bars_seen"]) + 1
        pending["last_seen"] = at
        bars_seen = int(pending["bars_seen"])
        if bars_seen > RECOVERY_MAX_BARS:
            funnel["RECOVERY_EXPIRED"] += 1
            pending = None
            pending_path = []
            continue

        # Gap inside recovery window already handled above; also require exact adjacency
        # from shock through this bar.
        shock_time = _as_utc(pending["shock_time"])
        expected_time = shock_time + timedelta(minutes=MINUTES_PER_M5 * bars_seen)
        if at != expected_time:
            funnel["GAP_CANCEL"] += 1
            pending = None
            pending_path = []
            continue

        if not recovery_qualifies(
            shock=pending,
            recovery=bar,
            path_bars=pending_path,
        ):
            if bars_seen == RECOVERY_MAX_BARS:
                funnel["RECOVERY_EXPIRED"] += 1
                pending = None
                pending_path = []
            else:
                funnel["RECOVERY_NOT_YET"] += 1
            continue

        decision_day = at.date()
        if decision_day in consumed:
            funnel["DAILY_REFRACTORY"] += 1
            pending = None
            pending_path = []
            continue

        recovery_close = float(bar["close"])
        stop_pips = planned_stop_pips(shock=pending, recovery_close=recovery_close)
        if not math.isfinite(stop_pips) or stop_pips <= 0:
            funnel["INVALID_STOP"] += 1
            pending = None
            pending_path = []
            continue
        cost_ratio = COST_PIPS / stop_pips
        shock_sign = int(pending["sign"])
        true_dir = "SHORT" if shock_sign > 0 else "LONG"
        follow_dir = "LONG" if shock_sign > 0 else "SHORT"
        entry = _as_utc(bar["availability_utc"])
        if entry != at + timedelta(minutes=MINUTES_PER_M5):
            raise ContractError("recovery availability must equal M5 close + next M1 open")
        selected.append(
            {
                "time_utc": at,
                "availability_utc": entry,
                "date": decision_day,
                "year": at.year,
                "slot": int(pending["slot"]),
                "shock_sign": shock_sign,
                "shock_time_utc": _iso_z(shock_time),
                "shock_open": float(pending["open"]),
                "shock_high": float(pending["high"]),
                "shock_low": float(pending["low"]),
                "shock_close": float(pending["close"]),
                "recovery_close": recovery_close,
                "baseline_spread_points": float(pending["baseline"]),
                "shock_spread_points": float(pending["block_spread_points"]),
                "recovery_spread_points": float(bar["block_spread_points"]),
                "atr20_prev_pips": float(pending["atr20_prev"]) / PIP,
                "stop_distance_pips": float(stop_pips),
                "cost_to_stop_ratio": float(cost_ratio),
                "true_direction": true_dir,
                "follow_control_direction": follow_dir,
                "recovery_bars": bars_seen,
            }
        )
        consumed.add(decision_day)
        funnel["DECISION"] += 1
        pending = None
        pending_path = []
        _ = bar_by_time  # reserved for future O(1) lookups; keep surface explicit

    return selected, dict(sorted(funnel.items()))


def map_horizon(
    entry: datetime,
    observed_m1: set[datetime],
) -> dict[str, object]:
    """Timestamp-only 60-minute horizon; never inspects post-entry OHLC."""

    entry_utc = _as_utc(entry)
    required = [entry_utc + timedelta(minutes=index) for index in range(HORIZON_BARS)]
    missing = [stamp for stamp in required if stamp not in observed_m1]
    complete = not missing
    return {
        "entry_open_utc": entry_utc,
        "time_exit_utc": entry_utc + timedelta(minutes=HORIZON_BARS) if complete else None,
        "required_m1_starts": required,
        "observed_horizon_bars": HORIZON_BARS - len(missing),
        "required_horizon_bars": HORIZON_BARS,
        "source_executable": complete,
        "reason": "SOURCE_EXECUTABLE" if complete else "HORIZON_INCOMPLETE",
    }


def assign_source_signal_id(decision: datetime) -> str:
    identity = f"{HYPOTHESIS_ID}|SOURCE|{_iso_z(decision)}".encode("ascii")
    return f"SRIR001-SRC-{sha256_bytes(identity)[:16]}"


def _classification_row(
    *,
    source_signal_id: str,
    decision: datetime,
    entry: datetime,
    status: str,
    observed_horizon_bars: int,
    required_horizon_bars: int,
) -> dict[str, object]:
    if status not in {"SOURCE_EXECUTABLE", "HORIZON_INCOMPLETE"}:
        raise ContractError("invalid classification status")
    if (
        type(observed_horizon_bars) is not int
        or type(required_horizon_bars) is not int
        or observed_horizon_bars < 0
        or required_horizon_bars != HORIZON_BARS
        or observed_horizon_bars > required_horizon_bars
    ):
        raise ContractError("invalid classification horizon counts")
    return {
        "source_signal_id": source_signal_id,
        "decision_utc": _iso_z(decision),
        "entry_open_utc": _iso_z(entry),
        "status": status,
        "observed_horizon_bars": observed_horizon_bars,
        "required_horizon_bars": required_horizon_bars,
    }


def _arm_identity_projection(
    true_rows: Sequence[Mapping[str, object]],
    follow_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    projection: list[dict[str, object]] = []
    for true_row, follow_row in zip(true_rows, follow_rows):
        projection.append(
            {
                "source_signal_id": true_row.get("source_signal_id"),
                "TRUE": {
                    "candidate_id": true_row.get("candidate_id"),
                    "decision_utc": true_row.get("decision_utc"),
                    "direction": true_row.get("direction"),
                },
                "FOLLOW_CONTROL": {
                    "candidate_id": follow_row.get("candidate_id"),
                    "decision_utc": follow_row.get("decision_utc"),
                    "direction": follow_row.get("direction"),
                },
            }
        )
    return projection


def classification_canonical_digest(
    classifications: Sequence[Mapping[str, object]],
    arm_projection: Sequence[Mapping[str, object]],
) -> str:
    payload = {
        "classifications": list(classifications),
        "arm_identity_projection": list(arm_projection),
    }
    assert_outcome_blind(payload)
    return sha256_bytes(canonical_json(payload))


def reconcile_exact_once(
    *,
    classifications: Sequence[Mapping[str, object]],
    true_rows: Sequence[Mapping[str, object]],
    follow_rows: Sequence[Mapping[str, object]],
    raw_first_per_day_count: int,
) -> dict[str, object]:
    if len(classifications) != raw_first_per_day_count:
        raise ContractError("classification count must equal raw first-per-day count")
    dates = [str(row.get("decision_utc"))[:10] for row in classifications]
    if len(dates) != len(set(dates)):
        raise ContractError("more than one raw decision on a UTC date")
    ids = [str(row.get("source_signal_id")) for row in classifications]
    if len(ids) != len(set(ids)):
        raise ContractError("source_signal_id is not unique")
    executable_ids = {
        str(row["source_signal_id"])
        for row in classifications
        if row.get("status") == "SOURCE_EXECUTABLE"
    }
    excluded_ids = {
        str(row["source_signal_id"])
        for row in classifications
        if row.get("status") == "HORIZON_INCOMPLETE"
    }
    if executable_ids & excluded_ids:
        raise ContractError("classification status conflict on source_signal_id")
    if len(executable_ids) + len(excluded_ids) != len(classifications):
        raise ContractError("classification status must be executable or excluded")
    true_by_id = {str(row.get("source_signal_id")): row for row in true_rows}
    follow_by_id = {str(row.get("source_signal_id")): row for row in follow_rows}
    if set(true_by_id) != executable_ids or set(follow_by_id) != executable_ids:
        raise ContractError("ledger source_signal_id projection mismatch")
    if len(true_by_id) != len(true_rows) or len(follow_by_id) != len(follow_rows):
        raise ContractError("duplicate ledger source_signal_id")
    for source_id in excluded_ids:
        if source_id in true_by_id or source_id in follow_by_id:
            raise ContractError("excluded source_signal_id mapped to ledger row")
    for source_id in executable_ids:
        if source_id not in true_by_id or source_id not in follow_by_id:
            raise ContractError("executable source_signal_id missing matched arms")
    arm_projection = _arm_identity_projection(true_rows, follow_rows)
    digest = classification_canonical_digest(classifications, arm_projection)
    executable = len(executable_ids)
    excluded = len(excluded_ids)
    raw_count = raw_first_per_day_count
    classification_count = len(classifications)
    if not (
        raw_count == classification_count == executable + excluded
        and classification_count == executable + excluded
    ):
        raise ContractError("exact-once count identity failed")
    return {
        "raw_first_per_day_count": raw_count,
        "classification_count": classification_count,
        "executable_count": executable,
        "excluded_count": excluded,
        "raw_equals_classifications": raw_count == classification_count,
        "classifications_equal_executable_plus_excluded": classification_count
        == executable + excluded,
        "max_one_decision_per_utc_date": True,
        "exact_once_reconciliation": True,
        "classification_digest_sha256": digest,
        "arm_identity_projection": arm_projection,
    }


def build_matched_ledgers(
    raw_signals: Sequence[Mapping[str, object]],
    observed_m1: set[datetime],
) -> dict[str, object]:
    """Exact-once classify every raw signal; ledger only horizon-complete pairs."""

    horizons: list[dict[str, object]] = []
    classifications: list[dict[str, object]] = []
    true_rows: list[dict[str, object]] = []
    follow_rows: list[dict[str, object]] = []
    seen_candidates: set[str] = set()
    seen_source_ids: set[str] = set()
    seen_dates: set[date] = set()
    excluded = 0
    for signal in sorted(raw_signals, key=lambda row: _as_utc(row["time_utc"])):
        decision = _as_utc(signal["time_utc"])
        availability = _as_utc(signal["availability_utc"])
        if availability != decision + timedelta(minutes=MINUTES_PER_M5):
            raise ContractError("signal availability must equal next M1 after recovery M5 close")
        day = decision.date()
        if day in seen_dates:
            raise ContractError("raw first-per-day contract violated")
        seen_dates.add(day)
        source_signal_id = assign_source_signal_id(decision)
        if source_signal_id in seen_source_ids:
            raise ContractError("duplicate source_signal_id")
        seen_source_ids.add(source_signal_id)
        if availability not in observed_m1:
            horizon = {
                "entry_open_utc": availability,
                "time_exit_utc": None,
                "required_m1_starts": [],
                "observed_horizon_bars": 0,
                "required_horizon_bars": HORIZON_BARS,
                "source_executable": False,
                "reason": "HORIZON_INCOMPLETE",
            }
        else:
            horizon = map_horizon(availability, observed_m1)
        status = (
            "SOURCE_EXECUTABLE"
            if horizon["source_executable"] is True
            else "HORIZON_INCOMPLETE"
        )
        classification = _classification_row(
            source_signal_id=source_signal_id,
            decision=decision,
            entry=horizon["entry_open_utc"],
            status=status,
            observed_horizon_bars=int(horizon["observed_horizon_bars"]),
            required_horizon_bars=int(horizon["required_horizon_bars"]),
        )
        classifications.append(classification)
        horizons.append(
            {
                "source_signal_id": source_signal_id,
                "source_executable": horizon["source_executable"],
                "reason": horizon["reason"],
                "observed_horizon_bars": horizon["observed_horizon_bars"],
                "required_horizon_bars": horizon["required_horizon_bars"],
            }
        )
        if horizon["source_executable"] is not True:
            excluded += 1
            continue
        features = {
            "shock_sign": int(signal["shock_sign"]),
            "shock_time_utc": str(signal["shock_time_utc"]),
            "baseline_spread_points": float(signal["baseline_spread_points"]),
            "shock_spread_points": float(signal["shock_spread_points"]),
            "recovery_spread_points": float(signal["recovery_spread_points"]),
            "atr20_prev_pips": float(signal["atr20_prev_pips"]),
            "stop_distance_pips": float(signal["stop_distance_pips"]),
            "cost_to_stop_ratio": float(signal["cost_to_stop_ratio"]),
            "recovery_bars": int(signal["recovery_bars"]),
            "slot": int(signal["slot"]),
        }
        for arm, direction_key in (
            ("TRUE", "true_direction"),
            ("FOLLOW_CONTROL", "follow_control_direction"),
        ):
            direction = signal[direction_key]
            if direction not in {"LONG", "SHORT"}:
                raise ContractError("invalid arm direction")
            identity = (
                f"{HYPOTHESIS_ID}|{arm}|{source_signal_id}|{_iso_z(decision)}|{direction}"
            ).encode("ascii")
            candidate_id = f"SRIR001-{arm}-{sha256_bytes(identity)[:16]}"
            if candidate_id in seen_candidates:
                raise ContractError("duplicate candidate identity")
            seen_candidates.add(candidate_id)
            row = {
                "candidate_id": candidate_id,
                "source_signal_id": source_signal_id,
                "arm": arm,
                "decision_utc": _iso_z(decision),
                "entry_open_utc": _iso_z(horizon["entry_open_utc"]),
                "time_exit_utc": _iso_z(horizon["time_exit_utc"]),
                "direction": direction,
                "year": int(signal["year"]),
                **features,
            }
            if arm == "TRUE":
                true_rows.append(row)
            else:
                follow_rows.append(row)
    if len(true_rows) != len(follow_rows):
        raise ContractError("TRUE/FOLLOW_CONTROL count mismatch")
    true_times = [row["decision_utc"] for row in true_rows]
    follow_times = [row["decision_utc"] for row in follow_rows]
    if true_times != follow_times:
        raise ContractError("TRUE/FOLLOW_CONTROL timestamp mismatch")
    for true_row, follow_row in zip(true_rows, follow_rows):
        if true_row["source_signal_id"] != follow_row["source_signal_id"]:
            raise ContractError("TRUE/FOLLOW_CONTROL source_signal_id mismatch")
        if {true_row["direction"], follow_row["direction"]} != {"LONG", "SHORT"}:
            raise ContractError("TRUE/FOLLOW_CONTROL directions must be opposite")
        if true_row["direction"] == follow_row["direction"]:
            raise ContractError("TRUE/FOLLOW_CONTROL directions must differ")
    reconciliation = reconcile_exact_once(
        classifications=classifications,
        true_rows=true_rows,
        follow_rows=follow_rows,
        raw_first_per_day_count=len(raw_signals),
    )
    if int(reconciliation["excluded_count"]) != excluded:
        raise ContractError("excluded count reconciliation failed")
    payload = {
        "raw_first_per_day_count": len(raw_signals),
        "horizon_excluded_count": excluded,
        "eligible_count": len(true_rows),
        "horizons": horizons,
        "classifications": classifications,
        "exact_once": reconciliation,
        "TRUE": true_rows,
        "FOLLOW_CONTROL": follow_rows,
    }
    assert_outcome_blind(payload)
    return payload


def domain_quality_metrics(
    *,
    m1_rows: Sequence[Mapping[str, object]],
    m5_bars: Sequence[Mapping[str, object]],
    source_dates: Sequence[date],
    burn_in_dates: set[date],
) -> dict[str, object]:
    """Post-burn-in scan-domain formation, positive-spread and baseline ratios."""

    post_burn_weekdays = [
        day for day in source_dates if day not in burn_in_dates and day.weekday() < 5
    ]
    slots_per_day = scan_domain_slots_per_day()
    formation_scheduled = len(post_burn_weekdays) * slots_per_day
    complete_scan = 0
    baseline_ready = 0
    date_index = {day: index for index, day in enumerate(source_dates)}
    slot_maps = build_slot_spread_by_date(m5_bars)
    for bar in m5_bars:
        at = _as_utc(bar["time_utc"])
        day = at.date()
        if day in burn_in_dates or not in_scan_domain(at):
            continue
        complete_scan += 1
        baseline = prior_20_baseline(
            source_dates=source_dates,
            date_index=date_index,
            slot_maps=slot_maps,
            day=day,
            slot=int(bar["slot"]),
        )
        if baseline is not None and gt_strict(baseline, 0.0):
            baseline_ready += 1
    if complete_scan > formation_scheduled:
        raise ContractError("complete scan bins exceed scheduled")
    formation_ratio = complete_scan / formation_scheduled if formation_scheduled else 0.0
    baseline_ratio = baseline_ready / complete_scan if complete_scan else 0.0

    positive = 0
    observed = 0
    for row in m1_rows:
        at = _as_utc(row["time_utc"])
        day = at.date()
        if day in burn_in_dates or not in_scan_recovery_m1_domain(at):
            continue
        observed += 1
        if positive_finite_spread(row["spread"]) is not None:
            positive += 1
    positive_ratio = positive / observed if observed else 0.0
    return {
        "formation_scheduled": formation_scheduled,
        "formation_complete": complete_scan,
        "formation_ratio": formation_ratio,
        "baseline_complete_scan_blocks": complete_scan,
        "baseline_available": baseline_ready,
        "baseline_availability_ratio": baseline_ratio,
        "positive_spread_observed_m1": observed,
        "positive_spread_count": positive,
        "positive_spread_ratio": positive_ratio,
        "post_burn_in_weekday_count": len(post_burn_weekdays),
        "slots_per_day": slots_per_day,
    }


def evaluate_stage0_gates(
    *,
    true_signals: Sequence[Mapping[str, object]],
    follow_signals: Sequence[Mapping[str, object]],
    raw_first_per_day_count: int,
    horizon_records: Sequence[Mapping[str, object]],
    domain_metrics: Mapping[str, object],
    source_only_counters: Mapping[str, object],
    elapsed_weeks: float,
) -> dict[str, object]:
    if (
        type(elapsed_weeks) not in {int, float}
        or isinstance(elapsed_weeks, bool)
        or not math.isfinite(float(elapsed_weeks))
        or float(elapsed_weeks) <= 0
        or type(raw_first_per_day_count) is not int
        or raw_first_per_day_count < 0
        or len(horizon_records) != raw_first_per_day_count
        or len(true_signals) != len(follow_signals)
    ):
        raise ContractError("invalid Stage-0 gate inputs")
    if [row.get("decision_utc") for row in true_signals] != [
        row.get("decision_utc") for row in follow_signals
    ]:
        raise ContractError("FOLLOW_CONTROL timestamps must match TRUE")
    count = len(true_signals)
    directions = Counter(str(row.get("direction")) for row in true_signals)
    if set(directions) - {"LONG", "SHORT"}:
        raise ContractError("invalid TRUE direction")
    years = Counter(row.get("year") for row in true_signals)
    if any(type(year) is not int or isinstance(year, bool) for year in years):
        raise ContractError("invalid year")
    cost_ratios: list[float] = []
    stop_pips: list[float] = []
    for row in true_signals:
        cost = row.get("cost_to_stop_ratio")
        stop = row.get("stop_distance_pips")
        if (
            type(cost) not in {int, float}
            or isinstance(cost, bool)
            or not math.isfinite(float(cost))
            or float(cost) < 0
            or type(stop) not in {int, float}
            or isinstance(stop, bool)
            or not math.isfinite(float(stop))
            or float(stop) <= 0
        ):
            raise ContractError("invalid geometry fields")
        cost_ratios.append(float(cost))
        stop_pips.append(float(stop))
    cadence = count / float(elapsed_weeks)
    long_share = directions["LONG"] / count if count else 0.0
    short_share = directions["SHORT"] / count if count else 0.0
    max_year_share = max(years.values(), default=0) / count if count else 0.0
    executable = sum(record.get("source_executable") is True for record in horizon_records)
    horizon_ratio = executable / raw_first_per_day_count if raw_first_per_day_count else 0.0
    median_cost = median(cost_ratios) if cost_ratios else None
    median_stop = median(stop_pips) if stop_pips else None
    follow_match = len(follow_signals) == count and all(
        true_row.get("decision_utc") == follow_row.get("decision_utc")
        and true_row.get("source_signal_id") == follow_row.get("source_signal_id")
        and {true_row.get("direction"), follow_row.get("direction")} == {"LONG", "SHORT"}
        for true_row, follow_row in zip(true_signals, follow_signals)
    )
    positive_ratio = float(domain_metrics["positive_spread_ratio"])
    formation_ratio = float(domain_metrics["formation_ratio"])
    baseline_ratio = float(domain_metrics["baseline_availability_ratio"])
    outcome_blind_intact = all(
        key in source_only_counters
        and type(source_only_counters[key]) is type(expected)
        and source_only_counters[key] == expected
        for key, expected in OUTCOME_BLIND_COUNTER_EXPECTATIONS.items()
    )
    gates = {
        "outcome_blind_plane_intact": outcome_blind_intact,
        "follow_control_matched_true_one_to_one": follow_match,
        "positive_finite_m1_spread_ratio_at_least_0_99": ge_inclusive(positive_ratio, 0.99),
        "exact_scheduled_m1_formation_completeness_at_least_0_99": ge_inclusive(
            formation_ratio, 0.99
        ),
        "frozen_prior_20_eligible_date_baseline_availability_at_least_0_99": ge_inclusive(
            baseline_ratio, 0.99
        ),
        "source_executable_horizon_ratio_at_least_0_99": ge_inclusive(horizon_ratio, 0.99),
        "true_cadence_2_to_5_per_elapsed_week": ge_inclusive(cadence, 2.0)
        and le_inclusive(cadence, 5.0),
        "true_long_share_at_least_0_25": ge_inclusive(long_share, 0.25),
        "true_short_share_at_least_0_25": ge_inclusive(short_share, 0.25),
        "max_calendar_year_share_at_most_0_35": le_inclusive(max_year_share, 0.35),
        "at_least_20_executable_true_per_direction": directions["LONG"] >= 20
        and directions["SHORT"] >= 20,
        "median_stop_distance_pips_at_least_6_0": median_stop is not None
        and ge_inclusive(median_stop, 6.0),
        "median_cost_to_stop_ratio_at_most_0_25": median_cost is not None
        and le_inclusive(median_cost, 0.25),
    }
    if len(gates) != 13:
        raise ContractError("Stage-0 must expose exactly thirteen gates")
    return {
        "verdict": STAGE0_PASS if all(gates.values()) else STAGE0_FAIL,
        "gates": gates,
        "metrics": {
            "eligible_count": count,
            "raw_first_per_day_count": raw_first_per_day_count,
            "horizon_executable_count": executable,
            "cadence_per_elapsed_week": cadence,
            "elapsed_calendar_weeks": float(elapsed_weeks),
            "long_count": directions["LONG"],
            "short_count": directions["SHORT"],
            "long_share": long_share,
            "short_share": short_share,
            "year_counts": {str(year): years[year] for year in sorted(years)},
            "max_year_share": max_year_share,
            "formation_complete": int(domain_metrics["formation_complete"]),
            "formation_scheduled": int(domain_metrics["formation_scheduled"]),
            "formation_completeness_ratio": formation_ratio,
            "positive_spread_ratio": positive_ratio,
            "baseline_availability_ratio": baseline_ratio,
            "source_executable_horizon_ratio": horizon_ratio,
            "median_cost_to_stop_ratio": median_cost,
            "median_stop_distance_pips": median_stop,
            "follow_control_count": len(follow_signals),
        },
    }


def assert_outcome_blind(value: object) -> None:
    forbidden_tokens = {
        "return",
        "pnl",
        "profit",
        "dsr",
        "trade",
        "win",
        "loss",
        "mfe",
        "mae",
    }
    forbidden_fragments = (
        "post_entry",
        "target_hit",
        "stop_hit",
        "entry_price",
        "exit_price",
        "tick_volume",
        "real_volume",
    )
    allowed_entry_exit = {
        "entry_open_utc",
        "time_exit_utc",
        "required_m1_starts",
    }
    # Spread is an authorized signal-state feature for SRIR; allow diagnostic keys.
    allowed_spread_keys = {
        "baseline_spread_points",
        "shock_spread_points",
        "recovery_spread_points",
        "block_spread_points",
        "positive_spread_ratio",
        "positive_spread_count",
        "positive_spread_observed_m1",
        "spread_available",
        "positive_finite_m1_spread_ratio_at_least_0_99",
    }

    def visit(item: object) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                if key in SEALED_FALSE_FIELDS:
                    if child is not False:
                        raise ContractError(f"sealed permission is not false: {key}")
                    continue
                if key in SOURCE_ONLY_ZERO_METRICS:
                    expected = SOURCE_ONLY_ZERO_METRICS[key]
                    if key in {"source_feasibility_attempts_consumed", "source_runs_executed"}:
                        if type(child) is not int or isinstance(child, bool) or child not in {0, 1}:
                            raise ContractError(f"invalid source-only counter: {key}")
                    elif type(child) is not type(expected) or child != expected:
                        raise ContractError(f"nonzero prohibited source-only counter: {key}")
                    continue
                lowered = str(key).lower()
                if key in allowed_spread_keys or lowered in allowed_spread_keys:
                    visit(child)
                    continue
                tokens = {token for token in re.split(r"[^a-z0-9]+", lowered) if token}
                has_entry_or_exit = "entry" in tokens or "exit" in tokens
                if (
                    has_entry_or_exit and lowered not in allowed_entry_exit
                ) or bool(tokens & forbidden_tokens) or any(
                    fragment in lowered for fragment in forbidden_fragments
                ):
                    raise ContractError(f"forbidden outcome field: {key}")
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)


def validate_registry_authority(
    registry_payload: bytes,
    reviewed_row_sha256: str,
    *,
    builder_payload: bytes,
    test_payload: bytes,
) -> dict[str, object]:
    try:
        if not _valid_sha(reviewed_row_sha256):
            raise ValueError("reviewed row SHA")
        rows, raw_rows = parse_registry_jsonl(registry_payload)
        matches = [
            position
            for position, raw_row in enumerate(raw_rows, start=1)
            if sha256_bytes(raw_row) == reviewed_row_sha256
        ]
        if len(matches) != 1:
            raise ValueError("reviewed row binding")
        index = matches[0]
        row = rows[index - 1]
        if canonical_json(row) + b"\n" != raw_rows[index - 1]:
            raise ContractError("selected registry row is not canonical")
        latest = [
            position
            for position, item in enumerate(rows, start=1)
            if item.get("hypothesis_id") == HYPOTHESIS_ID
        ]
        validation = row.get("validation")
        metrics = row.get("metrics")
        if (
            not latest
            or latest[-1] != index
            or row.get("record_type") != "hypothesis_state"
            or row.get("schema_version") != "alphafactory_candidate_registry.v1"
            or row.get("hypothesis_id") != HYPOTHESIS_ID
            or row.get("parent_candidate") is not None
            or row.get("ea_name") != EA_NAME
            or row.get("feature_family") != FAMILY
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
            raise ValueError("identity")
        if set(metrics) != set(SOURCE_ONLY_ZERO_METRICS) or any(
            type(metrics[key]) is not type(expected) or metrics[key] != expected
            for key, expected in SOURCE_ONLY_ZERO_METRICS.items()
        ):
            raise ContractError("registry source-only zero metrics mismatch")
        required = {
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
            "design_m1_manifest_path": M1_MANIFEST_REL,
            "design_m1_manifest_sha256": M1_MANIFEST_SHA256,
            "design_m1_receipt_path": M1_RECEIPT_REL,
            "design_m1_receipt_sha256": M1_RECEIPT_SHA256,
            "design_m1_source_sha256": M1_SOURCE_SHA256,
            "registry_validator_path": REGISTRY_VALIDATOR_REL,
            "registry_validator_sha256": REGISTRY_VALIDATOR_SHA256,
            "registry_schema_path": REGISTRY_SCHEMA_REL,
            "registry_schema_sha256": REGISTRY_SCHEMA_SHA256,
        }
        if set(validation) != REGISTRY_VALIDATION_FIELDS:
            raise ContractError("registry validation key whitelist mismatch")
        if (
            any(validation[field] is not True for field in INTENDED_TRUE_VALIDATION_FIELDS)
            or any(validation[key] != expected for key, expected in required.items())
            or not _valid_sha(validation.get("independent_review_receipt_sha256"))
        ):
            raise ContractError("registry source authority mismatch")
        if any(validation[field] is not False for field in SEALED_FALSE_FIELDS):
            raise ContractError("registry sealed authority aliases are invalid")
        return row
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("registry source authority mismatch") from exc


def validate_review_receipt(
    payload: bytes,
    *,
    expected_sha256: str,
    builder_payload: bytes,
    test_payload: bytes,
) -> dict[str, object]:
    if not _valid_sha(expected_sha256) or sha256_bytes(payload) != expected_sha256:
        raise ContractError("independent review receipt SHA binding mismatch")
    receipt = parse_canonical_object(payload, label="SRIR implementation review receipt")
    expected = {
        "schema_version": REVIEW_RECEIPT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {
            "path": BUILDER_REL,
            "base_sha256": reviewed_base_source_sha256(builder_payload),
        },
        "reviewed_tests": {
            "path": TEST_REL,
            "sha256": sha256_bytes(test_payload),
        },
        # Generic registry validator names this compatibility field v1_plan;
        # its path/SHA still bind the frozen SRIR V2 plan above.
        "v1_plan": {"path": PLAN_REL, "sha256": PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    if receipt != expected:
        raise ContractError("independent review receipt object binding mismatch")
    return receipt


def _decode_parquet_producer_schema(payload: bytes) -> DecodedShard:
    """Validate full producer schema; keep only OHLC+spread signal columns."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(pa.BufferReader(payload))
        schema_names = set(parquet.schema_arrow.names)
        missing = [name for name in PRODUCER_SCHEMA_COLUMNS if name not in schema_names]
        if missing:
            raise ValueError(f"missing producer columns: {missing}")
        table = parquet.read(columns=list(PRODUCER_SCHEMA_COLUMNS))
        rows = table.to_pylist()
        signal_rows: list[dict[str, object]] = []
        for row in rows:
            # Schema-validate then discard tick_volume / real_volume — never as features.
            _finite_tick_volume(row["tick_volume"])
            _finite_real_volume(row["real_volume"])
            spread = _producer_spread(row["spread"])
            value = row.get("time_utc")
            if type(value) is not datetime and hasattr(value, "to_pydatetime"):
                value = value.to_pydatetime()
            signal_rows.append(
                {
                    "time_utc": value,
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "spread": spread,
                }
            )
        return DecodedShard(SIGNAL_COLUMNS, parquet.num_row_groups, tuple(signal_rows))
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("Parquet decoder failure") from exc


def validate_decoded_signal_rows(
    decoded: DecodedShard,
    *,
    day: str,
    expected_rows: int,
) -> tuple[dict[str, object], ...]:
    try:
        if (
            type(decoded) is not DecodedShard
            or decoded.columns != SIGNAL_COLUMNS
            or type(expected_rows) is not int
            or expected_rows <= 0
            or len(decoded.rows) != expected_rows
        ):
            raise ValueError
        previous: datetime | None = None
        cleaned: list[dict[str, object]] = []
        for row in decoded.rows:
            if type(row) is not dict or set(row) != set(SIGNAL_COLUMNS):
                raise ValueError
            if any(value is None for value in row.values()):
                raise ValueError
            utc_value = row["time_utc"]
            if type(utc_value) is not datetime:
                raise ValueError
            if utc_value.tzinfo is not None:
                if utc_value.utcoffset() != timedelta(0):
                    raise ValueError
                utc_value = utc_value.replace(tzinfo=None)
            if utc_value.second or utc_value.microsecond or utc_value.date().isoformat() != day:
                raise ValueError
            if previous is not None and utc_value <= previous:
                raise ValueError
            previous = utc_value
            open_price, high, low, close = (_finite_price(row[name]) for name in ("open", "high", "low", "close"))
            if not (low <= open_price <= high and low <= close <= high):
                raise ValueError
            spread = _producer_spread(row["spread"])
            cleaned.append(
                {
                    "time_utc": utc_value.replace(tzinfo=UTC),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "spread": spread,
                }
            )
        return tuple(cleaned)
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("decoded shard day/OHLC/spread contract mismatch") from exc


def _load_public_rows(
    *,
    workspace: Path,
    entries: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    root = workspace / M1_ROOT_REL
    result: list[dict[str, object]] = []
    for entry in entries:
        relative = Path(str(entry["relative_path"]))
        parts = relative.parts
        if any(part.lower() in FORBIDDEN_PATH_PARTS for part in parts):
            raise ContractError("forbidden validation/holdout/private path rejected")
        if len(parts) < 2 or parts[0] != "public" or parts[1] != "DESIGN":
            raise ContractError("shard path is not public DESIGN")
        payload = stable_read_regular(root / relative, root)
        if len(payload) != entry["bytes"] or sha256_bytes(payload) != entry["sha256"]:
            raise ContractError("manifest shard SHA/bytes mismatch")
        rows = validate_decoded_signal_rows(
            _decode_parquet_producer_schema(payload),
            day=str(entry["date"]),
            expected_rows=int(entry["rows"]),
        )
        result.extend(rows)
    times = [row["time_utc"] for row in result]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ContractError("cross-shard timestamps are duplicated or unordered")
    return result


def _executed_source_only_counters() -> dict[str, object]:
    counters = dict(SOURCE_ONLY_ZERO_METRICS)
    counters["source_feasibility_attempts_consumed"] = 1
    counters["source_runs_executed"] = 1
    return counters


def _sealed_permissions() -> dict[str, bool]:
    return {field: False for field in SEALED_FALSE_FIELDS}


def _os_fs_path(path: Path) -> str:
    """Absolute filesystem path; apply Windows long-path prefix when needed."""

    text = str(Path(path).absolute())
    if os.name == "nt" and not text.startswith("\\\\?\\"):
        return "\\\\?\\" + text
    return text


def _write_new_bytes(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes:
        raise ContractError("artifact payload must be bytes")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | int(getattr(os, "O_BINARY", 0))
        | int(getattr(os, "O_NOFOLLOW", 0))
    )
    fs_path = _os_fs_path(path)
    try:
        descriptor = os.open(fs_path, flags, 0o600)
        try:
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise OSError("short artifact write")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        info = os.lstat(fs_path)
        path_obj = Path(path)
        if (
            not stat.S_ISREG(info.st_mode)
            or path_obj.is_symlink()
            or _is_reparse(info)
            or int(info.st_nlink) != 1
            or int(info.st_size) != len(payload)
        ):
            raise OSError("artifact identity mismatch")
    except Exception as exc:
        raise ContractError(f"exclusive artifact write failed: {path.name}") from exc


def _write_new_canonical(path: Path, value: object) -> None:
    _write_new_bytes(path, canonical_json(value) + b"\n")


def _write_new_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    payload = b"".join(canonical_json(row) + b"\n" for row in rows)
    _write_new_bytes(path, payload)


def _artifact_bytes(path: Path) -> bytes:
    fs_path = _os_fs_path(path)
    info = os.lstat(fs_path)
    if not stat.S_ISREG(info.st_mode) or _is_reparse(info) or int(info.st_nlink) != 1:
        raise ContractError("durable artifact identity mismatch")
    with open(fs_path, "rb") as handle:
        payload = handle.read()
    if len(payload) != int(info.st_size) or _identity(os.lstat(fs_path)) != _identity(info):
        raise ContractError("durable artifact changed during readback")
    return payload


def _existing_artifact_hashes(root: Path) -> dict[str, str]:
    try:
        names = sorted(
            entry.name
            for entry in os.scandir(_os_fs_path(root))
            if entry.is_file(follow_symlinks=False) and entry.name != "attempt_terminal.json"
        )
    except FileNotFoundError as exc:
        raise ContractError("evidence root missing during artifact hash binding") from exc
    hashes: dict[str, str] = {}
    for name in names:
        path = root / name
        fs_path = _os_fs_path(path)
        info = os.lstat(fs_path)
        if not stat.S_ISREG(info.st_mode) or _is_reparse(info):
            raise ContractError(f"non-regular evidence artifact: {name}")
        hashes[name] = sha256_bytes(_artifact_bytes(path))
    return hashes


def _reserve_attempt(workspace: Path, reviewed_row_sha256: str) -> Path:
    if not _valid_sha(reviewed_row_sha256):
        raise ContractError("attempt reservation requires reviewed registry-row SHA")
    workspace = Path(workspace).absolute()
    root_info = os.lstat(workspace)
    if not stat.S_ISDIR(root_info.st_mode) or workspace.is_symlink() or _is_reparse(root_info):
        raise ContractError("workspace root is not a private directory")
    relative = Path(EVIDENCE_ROOT_REL)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ContractError("invalid evidence-root contract")
    current = workspace
    for component in relative.parts[:-1]:
        current /= component
        try:
            os.mkdir(current)
        except FileExistsError:
            pass
        info = os.lstat(current)
        if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _is_reparse(info):
            raise ContractError("evidence parent is an alias or non-directory")
    root = current / relative.parts[-1]
    try:
        os.mkdir(root)
    except FileExistsError as exc:
        raise ContractError("attempt evidence root already exists; one-use reservation rejected") from exc
    info = os.lstat(root)
    if not stat.S_ISDIR(info.st_mode) or root.is_symlink() or _is_reparse(info):
        raise ContractError("attempt evidence root reservation failed")
    try:
        _write_new_canonical(
            root / "attempt_started.json",
            {
                "schema_version": "srir_001_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "reviewed_registry_row_sha256": reviewed_row_sha256,
                "status": "STARTED",
                "source_only_counters": _executed_source_only_counters(),
                "sealed_permissions": _sealed_permissions(),
            },
        )
    except Exception as exc:
        try:
            _persist_engineering_failure(root, reviewed_row_sha256, exc)
        except Exception as terminal_exc:
            raise ContractError(
                "attempt reservation failed after mkdir and terminal persistence failed"
            ) from terminal_exc
        raise
    return root


def _flatten_ledgers(
    report: Mapping[str, object], *, reviewed_row_sha256: str, attempt_started_sha256: str
) -> list[dict[str, object]]:
    ledgers = report.get("signal_ledgers")
    if type(ledgers) is not dict or set(ledgers) != {"TRUE", "FOLLOW_CONTROL"}:
        raise ContractError("report does not contain exact TRUE/FOLLOW_CONTROL ledgers")
    flattened: list[dict[str, object]] = []
    for arm in ARM_NAMES:
        rows = ledgers[arm]
        if type(rows) is not list:
            raise ContractError("source ledger arm is malformed")
        for row in rows:
            if type(row) is not dict or row.get("arm") != arm:
                raise ContractError("source ledger row arm mismatch")
            if set(row) & {
                "schema_version",
                "hypothesis_id",
                "attempt_id",
                "reviewed_registry_row_sha256",
                "attempt_started_sha256",
            }:
                raise ContractError("source ledger row collides with durable binding")
            flattened.append(
                {
                    "schema_version": "srir_001_source_ledger_row.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "reviewed_registry_row_sha256": reviewed_row_sha256,
                    "attempt_started_sha256": attempt_started_sha256,
                    **row,
                }
            )
    assert_outcome_blind(flattened)
    return flattened


def _stage0_to_terminal_status(verdict: object) -> str:
    if verdict == STAGE0_PASS:
        return TERMINAL_PASS_STATUS
    if verdict == STAGE0_FAIL:
        return TERMINAL_FAIL_STATUS
    raise ContractError("source report has invalid Stage-0 verdict")


def _assert_receipt_is_non_terminal(receipt: Mapping[str, object]) -> None:
    if receipt.get("status") != RECEIPT_NON_TERMINAL_STATUS:
        raise ContractError("receipt must remain non-terminal")
    if receipt.get("terminal_is_sole_authoritative_completion") is not True:
        raise ContractError("receipt must declare terminal-sole authority")
    if "terminal_status" in receipt:
        raise ContractError("receipt must not carry authoritative terminal_status")
    if receipt.get("status") == TERMINAL_PASS_STATUS:
        raise ContractError("receipt must never claim PASS_SOURCE_FEASIBILITY")
    status_blob = canonical_json({"status": receipt.get("status")}).decode("ascii")
    if TERMINAL_PASS_STATUS in status_blob:
        raise ContractError("receipt must never claim PASS_SOURCE_FEASIBILITY")


def _persist_success(
    root: Path, report: Mapping[str, object], reviewed_row_sha256: str
) -> dict[str, object]:
    assert_outcome_blind(report)
    started_sha = sha256_bytes(_artifact_bytes(root / "attempt_started.json"))
    enriched = dict(report)
    enriched["artifact_binding"] = {
        "attempt_id": ATTEMPT_ID,
        "attempt_started_sha256": started_sha,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
    }
    enriched["source_only_counters"] = _executed_source_only_counters()
    enriched["sealed_permissions"] = _sealed_permissions()
    assert_outcome_blind(enriched)
    _write_new_canonical(root / "source_report.json", enriched)
    classifications = enriched.get("raw_signal_classifications")
    if type(classifications) is not list:
        raise ContractError("report missing exact-once classifications")
    classification_rows = []
    for row in classifications:
        if type(row) is not dict:
            raise ContractError("classification row malformed")
        classification_rows.append(
            {
                "schema_version": "srir_001_source_classification_row.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "reviewed_registry_row_sha256": reviewed_row_sha256,
                "attempt_started_sha256": started_sha,
                **row,
            }
        )
    assert_outcome_blind(classification_rows)
    _write_new_jsonl(root / "source_classifications.jsonl", classification_rows)
    flattened = _flatten_ledgers(
        enriched,
        reviewed_row_sha256=reviewed_row_sha256,
        attempt_started_sha256=started_sha,
    )
    _write_new_jsonl(root / "source_ledger.jsonl", flattened)
    first_hashes = _existing_artifact_hashes(root)
    stage0 = enriched.get("stage0")
    verdict = stage0.get("verdict") if type(stage0) is dict else None
    terminal_status = _stage0_to_terminal_status(verdict)
    receipt = {
        "schema_version": "srir_001_source_feasibility_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "status": RECEIPT_NON_TERMINAL_STATUS,
        "stage0_verdict": verdict,
        "stage0_verdict_is_non_authoritative_calculation": True,
        "terminal_is_sole_authoritative_completion": True,
        "artifact_hashes": first_hashes,
        "source_only_counters": _executed_source_only_counters(),
        "sealed_permissions": _sealed_permissions(),
    }
    _assert_receipt_is_non_terminal(receipt)
    assert_outcome_blind(receipt)
    _write_new_canonical(root / "source_feasibility_receipt.json", receipt)
    all_hashes = _existing_artifact_hashes(root)
    terminal = {
        "schema_version": "srir_001_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "status": terminal_status,
        "stage0_verdict": verdict,
        "artifact_hashes": all_hashes,
        "source_only_counters": _executed_source_only_counters(),
        "sealed_permissions": _sealed_permissions(),
        "sole_authoritative_completion": True,
    }
    assert_outcome_blind(terminal)
    try:
        _write_new_canonical(root / "attempt_terminal.json", terminal)
    except Exception as terminal_write_exc:
        raise ContractError(
            "authoritative attempt_terminal write failed after non-terminal receipt"
        ) from terminal_write_exc
    return enriched


def _safe_unlink_attempt_terminal(root: Path) -> None:
    root_path = Path(root)
    terminal = root_path / "attempt_terminal.json"
    if terminal.name != "attempt_terminal.json":
        raise ContractError("refusing terminal unlink with non-canonical name")
    fs_path = _os_fs_path(terminal)
    try:
        info = os.lstat(fs_path)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
        raise ContractError("attempt_terminal path is a directory; cannot replace safely")
    try:
        os.unlink(fs_path)
    except FileNotFoundError:
        return
    except OSError as unlink_exc:
        raise ContractError("failed to remove suspect attempt_terminal") from unlink_exc
    try:
        os.lstat(fs_path)
    except FileNotFoundError:
        return
    raise ContractError("suspect attempt_terminal still present after unlink")


def _persist_engineering_failure(root: Path, reviewed_row_sha256: str, error: Exception) -> None:
    terminal = Path(root) / "attempt_terminal.json"
    _safe_unlink_attempt_terminal(Path(root))
    value = {
        "schema_version": "srir_001_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "status": TERMINAL_ENGINEERING_INVALID,
        "reason": {"type": type(error).__name__, "message": str(error)[:1000]},
        "artifact_hashes": _existing_artifact_hashes(root),
        "source_only_counters": _executed_source_only_counters(),
        "sealed_permissions": _sealed_permissions(),
        "sole_authoritative_completion": True,
    }
    assert_outcome_blind(value)
    try:
        _write_new_canonical(terminal, value)
    except Exception as write_exc:
        raise ContractError(
            "engineering-invalid terminal persistence failed after suspect removal"
        ) from write_exc


def _immutable_m1_copy(m1_rows: Sequence[Mapping[str, object]]) -> tuple[dict[str, object], ...]:
    copied: list[dict[str, object]] = []
    for row in m1_rows:
        if type(row) is not dict and not isinstance(row, Mapping):
            raise ContractError("M1 row must be a mapping")
        item = {
            "time_utc": _as_utc(row["time_utc"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "spread": float(row["spread"]),
        }
        _ohlc(item)
        if not math.isfinite(item["spread"]):
            raise ContractError("non-finite spread in immutable copy")
        copied.append(item)
    return tuple(copied)


def _immutable_date_copy(source_dates: Sequence[date]) -> tuple[date, ...]:
    copied = tuple(date(day.year, day.month, day.day) for day in source_dates)
    if any(type(day) is not date for day in copied):
        raise ContractError("source dates must be date objects")
    return copied


def canonical_scan_projection(report: Mapping[str, object]) -> dict[str, object]:
    stage0 = report.get("stage0")
    if type(stage0) is not dict:
        raise ContractError("scan projection requires stage0")
    projection = {
        "hypothesis_id": report.get("hypothesis_id"),
        "attempt_id": report.get("attempt_id"),
        "arm_counts": report.get("arm_counts"),
        "population": report.get("population"),
        "domain_diagnostics": report.get("domain_diagnostics"),
        "horizon_funnel": report.get("horizon_funnel"),
        "raw_signal_classifications": report.get("raw_signal_classifications"),
        "exact_once": report.get("exact_once"),
        "signal_ledgers": report.get("signal_ledgers"),
        "stage0": {
            "verdict": stage0.get("verdict"),
            "gates": stage0.get("gates"),
            "metrics": stage0.get("metrics"),
        },
        "economics_authorized": report.get("economics_authorized"),
        "post_entry_ohlc_rows_read": report.get("post_entry_ohlc_rows_read"),
        "outcome_fields_emitted": report.get("outcome_fields_emitted"),
        "returns_computed": report.get("returns_computed"),
        "trades_simulated": report.get("trades_simulated"),
        "performance_trials_executed": report.get("performance_trials_executed"),
    }
    assert_outcome_blind(projection)
    return projection


def scan_source_once(
    m1_rows: Sequence[Mapping[str, object]],
    source_dates: Sequence[date],
) -> dict[str, object]:
    """One-pass pure scan. Does not call independent replay (no recursion)."""

    dates = _immutable_date_copy(source_dates)
    if dates != tuple(sorted(dates)) or len(dates) != len(set(dates)):
        raise ContractError("source_dates must be unique and sorted")
    eligible_dates = eligible_baseline_dates(dates)
    burn_in = (
        set(eligible_dates[:BURN_IN_ELIGIBLE_DATES])
        if len(eligible_dates) >= BURN_IN_ELIGIBLE_DATES
        else set(eligible_dates)
    )
    m5_bars, quality = build_complete_m5(m1_rows)
    enriched = attach_wilder_atr20(m5_bars)
    observed = {_as_utc(row["time_utc"]) for row in m1_rows}
    raw, funnel = select_raw_signals(
        enriched,
        source_dates=eligible_dates,
        burn_in_dates=burn_in,
    )
    ledgers = build_matched_ledgers(raw, observed)
    domain_metrics = domain_quality_metrics(
        m1_rows=m1_rows,
        m5_bars=enriched,
        source_dates=eligible_dates,
        burn_in_dates=burn_in,
    )
    stage0 = evaluate_stage0_gates(
        true_signals=ledgers["TRUE"],
        follow_signals=ledgers["FOLLOW_CONTROL"],
        raw_first_per_day_count=int(ledgers["raw_first_per_day_count"]),
        horizon_records=ledgers["horizons"],
        domain_metrics=domain_metrics,
        source_only_counters=_executed_source_only_counters(),
        elapsed_weeks=ELAPSED_CALENDAR_WEEKS,
    )
    exact_once = ledgers["exact_once"]
    report = {
        "schema_version": "srir_001_source_feasibility_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "feature_family": FAMILY,
        "attempt_id": ATTEMPT_ID,
        "evidence_class": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
        "mechanism_status": "PLAUSIBLE_UNVALIDATED_FALSIFICATION_PRIORS",
        "literature_status": "MEASUREMENT_PRIOR_ONLY_NOT_PROFIT_PROOF",
        "source_contract": {
            "design_start": DESIGN_START.isoformat(),
            "design_end": DESIGN_END.isoformat(),
            "elapsed_calendar_weeks": ELAPSED_CALENDAR_WEEKS,
            "m1_manifest_sha256": M1_MANIFEST_SHA256,
            "m1_receipt_sha256": M1_RECEIPT_SHA256,
            "m1_source_sha256": M1_SOURCE_SHA256,
            "manifest_dates": EXPECTED_MANIFEST_DATES,
            "business_decision_dates": EXPECTED_BUSINESS_DECISION_DATES,
            "sunday_history_dates": EXPECTED_SUNDAY_DATES,
            "m1_design_rows": EXPECTED_M1_DESIGN_ROWS,
            "signal_columns": list(SIGNAL_COLUMNS),
            "producer_schema_columns": list(PRODUCER_SCHEMA_COLUMNS),
            "m5_quality": quality,
            "plan_sha256": PLAN_SHA256,
            "burn_in_eligible_dates": BURN_IN_ELIGIBLE_DATES,
            "baseline_lookback_dates": BASELINE_LOOKBACK_DATES,
            "atr_period": ATR_PERIOD,
            "shock_spread_mult": SHOCK_SPREAD_MULT,
            "shock_spread_excess_points": SHOCK_SPREAD_EXCESS_POINTS,
            "recovery_spread_mult": RECOVERY_SPREAD_MULT,
            "recovery_max_bars": RECOVERY_MAX_BARS,
            "horizon_bars": HORIZON_BARS,
            "scan_minute_start_utc": SCAN_MINUTE_START,
            "scan_minute_end_utc": SCAN_MINUTE_END,
            "matched_arms": list(ARM_NAMES),
            "ohlc_spread_signal_inputs": True,
            "producer_activity_fields_excluded_from_signal": True,
            "signal_uses_ohlc_and_spread_only": True,
        },
        "arm_counts": {
            "TRUE": len(ledgers["TRUE"]),
            "FOLLOW_CONTROL": len(ledgers["FOLLOW_CONTROL"]),
        },
        "signal_ledgers": {
            "TRUE": ledgers["TRUE"],
            "FOLLOW_CONTROL": ledgers["FOLLOW_CONTROL"],
        },
        "raw_signal_classifications": list(ledgers["classifications"]),
        "exact_once": {
            "raw_first_per_day_count": exact_once["raw_first_per_day_count"],
            "classification_count": exact_once["classification_count"],
            "executable_count": exact_once["executable_count"],
            "excluded_count": exact_once["excluded_count"],
            "raw_equals_classifications": exact_once["raw_equals_classifications"],
            "classifications_equal_executable_plus_excluded": exact_once[
                "classifications_equal_executable_plus_excluded"
            ],
            "max_one_decision_per_utc_date": exact_once["max_one_decision_per_utc_date"],
            "exact_once_reconciliation": exact_once["exact_once_reconciliation"],
            "classification_digest_sha256": exact_once["classification_digest_sha256"],
        },
        "population": {
            "raw_first_per_day_count": ledgers["raw_first_per_day_count"],
            "horizon_excluded_count": ledgers["horizon_excluded_count"],
            "eligible_count": ledgers["eligible_count"],
        },
        "domain_diagnostics": {
            **domain_metrics,
            "funnel": funnel,
            "m5_quality": quality,
        },
        "horizon_funnel": {
            "raw_first_per_day": ledgers["raw_first_per_day_count"],
            "source_executable": sum(
                row.get("source_executable") is True for row in ledgers["horizons"]
            ),
            "horizon_incomplete": sum(
                row.get("source_executable") is not True for row in ledgers["horizons"]
            ),
        },
        "stage0": stage0,
        "economics_authorized": False,
        "future_economics_requires_separate_prereg": True,
        "source_pass_is_not_edge_evidence": True,
        "post_entry_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
        "performance_trials_executed": 0,
    }
    assert_outcome_blind(report)
    return report


def independent_replay_scan(
    m1_rows: Sequence[Mapping[str, object]],
    source_dates: Sequence[date],
    primary_report: Mapping[str, object],
) -> dict[str, object]:
    if type(primary_report) is not dict and not isinstance(primary_report, Mapping):
        raise ContractError("primary report must be a mapping")
    m1_copy = _immutable_m1_copy(m1_rows)
    dates_copy = _immutable_date_copy(source_dates)
    primary_projection = canonical_scan_projection(primary_report)
    primary_digest = sha256_bytes(canonical_json(primary_projection))
    replay_report = scan_source_once(m1_copy, dates_copy)
    if replay_report is primary_report:
        raise ContractError("replay reused primary report object")
    replay_projection = canonical_scan_projection(replay_report)
    replay_digest = sha256_bytes(canonical_json(replay_projection))
    if primary_digest != replay_digest:
        raise ContractError("independent replay canonical digest mismatch")
    if canonical_json(primary_projection) != canonical_json(replay_projection):
        raise ContractError("independent replay projection byte mismatch")
    primary_exact = primary_report.get("exact_once")
    if type(primary_exact) is not dict or primary_exact.get("exact_once_reconciliation") is not True:
        raise ContractError("primary exact-once reconciliation missing")
    if primary_exact.get("classification_digest_sha256") != replay_report["exact_once"][
        "classification_digest_sha256"
    ]:
        raise ContractError("classification digest mismatch under independent replay")
    return {
        "primary_canonical_digest_sha256": primary_digest,
        "replay_canonical_digest_sha256": replay_digest,
        "exact_once_reconciliation": True,
        "digests_equal": True,
    }


def scan_source(
    m1_rows: Sequence[Mapping[str, object]],
    source_dates: Sequence[date],
    *,
    with_independent_replay: bool = True,
) -> dict[str, object]:
    primary = scan_source_once(m1_rows, source_dates)
    if with_independent_replay is not True:
        return primary
    replay_meta = independent_replay_scan(m1_rows, source_dates, primary)
    report = dict(primary)
    report["independent_replay"] = replay_meta
    report["canonical_digest_sha256"] = replay_meta["primary_canonical_digest_sha256"]
    report["replay_canonical_digest_sha256"] = replay_meta["replay_canonical_digest_sha256"]
    report["exact_once_reconciliation"] = True
    assert_outcome_blind(report)
    return report


def assert_independent_replay_rejects_mutation(
    m1_rows: Sequence[Mapping[str, object]],
    source_dates: Sequence[date],
    *,
    mode: str,
) -> None:
    primary = scan_source_once(m1_rows, source_dates)
    mutated = dict(primary)
    if mode == "omit_classification":
        classifications = list(mutated.get("raw_signal_classifications") or [])
        if not classifications:
            raise ContractError("no classification to omit")
        mutated["raw_signal_classifications"] = classifications[1:]
    elif mode == "reorder_classification":
        classifications = list(mutated.get("raw_signal_classifications") or [])
        if len(classifications) < 2:
            raise ContractError("need two classifications to reorder")
        classifications[0], classifications[1] = classifications[1], classifications[0]
        mutated["raw_signal_classifications"] = classifications
    elif mode == "mutate_ledger":
        ledgers = dict(mutated.get("signal_ledgers") or {})
        true_rows = list(ledgers.get("TRUE") or [])
        if not true_rows:
            raise ContractError("no TRUE ledger row to mutate")
        row = dict(true_rows[0])
        row["direction"] = "SHORT" if row.get("direction") == "LONG" else "LONG"
        true_rows[0] = row
        ledgers["TRUE"] = true_rows
        mutated["signal_ledgers"] = ledgers
    else:
        raise ContractError(f"unknown mutation mode: {mode}")
    try:
        independent_replay_scan(m1_rows, source_dates, mutated)
    except ContractError:
        return
    raise ContractError(f"independent replay failed to reject mutation mode={mode}")


def _read_and_scan_design(workspace: Path) -> dict[str, object]:
    m1_entries = validate_public_metadata(
        receipt_payload=stable_read_regular(workspace / M1_RECEIPT_REL, workspace),
        manifest_payload=stable_read_regular(workspace / M1_MANIFEST_REL, workspace),
        expected_receipt_sha256=M1_RECEIPT_SHA256,
        expected_manifest_sha256=M1_MANIFEST_SHA256,
    )
    m1_rows = _load_public_rows(workspace=workspace, entries=m1_entries)
    return scan_source(m1_rows, all_source_dates(m1_entries), with_independent_replay=True)


def execute_probe(*, workspace_root: Path, run_switch: bool) -> dict[str, object]:
    if run_switch is not True:
        raise ContractError("source probe is disarmed; explicit --execute-probe is required")
    if REVIEWED_REGISTRY_ROW_SHA256 is None:
        raise ContractError("source probe is disarmed; reviewed registry-row sentinel is absent")
    if not _valid_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("reviewed registry-row sentinel is invalid")

    workspace = Path(workspace_root).absolute()
    builder_payload = stable_read_regular(workspace / BUILDER_REL, workspace)
    test_payload = stable_read_regular(workspace / TEST_REL, workspace)
    plan_payload = stable_read_regular(workspace / PLAN_REL, workspace)
    if sha256_bytes(plan_payload) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")
    registry_payload = stable_read_regular(workspace / REGISTRY_REL, workspace)
    validator_payload = stable_read_regular(workspace / REGISTRY_VALIDATOR_REL, workspace)
    schema_payload = stable_read_regular(workspace / REGISTRY_SCHEMA_REL, workspace)
    validate_registry_snapshot(
        registry_payload=registry_payload,
        validator_payload=validator_payload,
        schema_payload=schema_payload,
        validator_path=workspace / REGISTRY_VALIDATOR_REL,
    )
    authority = validate_registry_authority(
        registry_payload,
        REVIEWED_REGISTRY_ROW_SHA256,
        builder_payload=builder_payload,
        test_payload=test_payload,
    )
    validation = authority.get("validation")
    if type(validation) is not dict:
        raise ContractError("registry review receipt authority is malformed")
    receipt_payload = stable_read_regular(workspace / REVIEW_RECEIPT_REL, workspace)
    validate_review_receipt(
        receipt_payload,
        expected_sha256=str(validation.get("independent_review_receipt_sha256")),
        builder_payload=builder_payload,
        test_payload=test_payload,
    )

    root = _reserve_attempt(workspace, REVIEWED_REGISTRY_ROW_SHA256)
    try:
        report = _read_and_scan_design(workspace)
        return _persist_success(root, report, REVIEWED_REGISTRY_ROW_SHA256)
    except Exception as exc:
        try:
            _persist_engineering_failure(root, REVIEWED_REGISTRY_ROW_SHA256, exc)
        except Exception as terminal_exc:
            raise ContractError("source attempt failed and terminal persistence failed") from terminal_exc
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--execute-probe", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = execute_probe(
        workspace_root=args.workspace_root,
        run_switch=args.execute_probe,
    )
    print(canonical_json(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
