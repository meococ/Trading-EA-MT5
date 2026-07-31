#!/usr/bin/env python3
"""Inert outcome-blind source probe for HYP-JCDR-EURUSD-M1-001.

Importing and default CLI execution cannot read real DESIGN data. A later real
read requires --execute-probe and an exact latest canonical registry row whose
raw SHA replaces the REVIEWED_REGISTRY_ROW_SHA256 sentinel. The computational
surface is intentionally usable with synthetic OHLC rows only.
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
import types
from collections import Counter, deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping, NamedTuple, Sequence


HYPOTHESIS_ID = "HYP-JCDR-EURUSD-M1-001"
EA_NAME = "EA_JumpClusterDecayReversal"
FAMILY = "jump-cluster-decay-reversal"
ATTEMPT_ID = "JCDR001-SOURCE-001"

PLAN_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "HYP-JCDR-EURUSD-M1-001_SOURCE_FEASIBILITY_PLAN.md"
)
PLAN_SHA256 = "15EE54A6071C3C8A81B6F07480BFB7813F82138C5C06347F169E026AB239FEB1"
BUILDER_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "build_jcdr_001_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/tests/"
    "test_build_jcdr_001_source.py"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/evidence/"
    "HYP-JCDR-EURUSD-M1-001_SOURCE_FEASIBILITY/"
    f"{ATTEMPT_ID}"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "HYP-JCDR-EURUSD-M1-001_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REVIEW_RECEIPT_SCHEMA = "jcdr_001_source_implementation_review_receipt.v1"
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
LOOKBACK_RETURNS = 240
JUMP_FLOOR_PIPS = 1.20
JUMP_SCALE_MULT = 3.0
CLUSTER_BARS = 15
MIN_CLUSTER_JUMPS = 3
COHERENCE_MIN = 0.80
MIN_DISPLACEMENT_PIPS = 4.0
DECAY_MAX_BARS = 10
RETRACE_MIN = 0.25
RETRACE_MAX = 1.00
NO_JUMP_LOOKBACK = 2  # decision + two predecessors
HORIZON_BARS = 60
MIN_STOP_PIPS = 6.0
STOP_BUFFER_PIPS = 0.50
COST_PIPS = 1.50

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
# Signal path uses OHLC only. tick_volume/spread may appear only in producer-schema
# validation for production shards and are never used as features.
SIGNAL_COLUMNS = ("time_utc", "open", "high", "low", "close")
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


class _RollingAbsMedian:
    """O(log W) push rolling median over a fixed window of absolute values."""

    __slots__ = ("window", "values", "sorted_vals")

    def __init__(self, window: int) -> None:
        if type(window) is not int or window <= 0:
            raise ContractError("rolling median window must be positive int")
        self.window = window
        self.values: deque[float] = deque()
        self.sorted_vals: list[float] = []

    def push(self, value: float) -> None:
        number = float(value)
        if not math.isfinite(number):
            raise ContractError("non-finite value in rolling scale window")
        ax = abs(number)
        if len(self.values) == self.window:
            old = self.values.popleft()
            index = bisect.bisect_left(self.sorted_vals, old)
            if index >= len(self.sorted_vals) or self.sorted_vals[index] != old:
                raise ContractError("rolling scale multiset corruption")
            del self.sorted_vals[index]
        self.values.append(ax)
        bisect.insort(self.sorted_vals, ax)

    def ready(self) -> bool:
        return len(self.values) == self.window

    def median(self) -> float:
        if not self.ready():
            raise ContractError("rolling scale median requested before window filled")
        width = self.window
        mid = width // 2
        if width % 2 == 1:
            return float(self.sorted_vals[mid])
        return 0.5 * (float(self.sorted_vals[mid - 1]) + float(self.sorted_vals[mid]))


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
        module = types.ModuleType("_jcdr_verified_candidate_registry_validator")
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


def weekday_decision_dates(entries: Sequence[Mapping[str, object]]) -> tuple[date, ...]:
    selected = tuple(
        date.fromisoformat(_canonical_day(row.get("date")))
        for row in entries
        if date.fromisoformat(_canonical_day(row.get("date"))).weekday() < 5
    )
    if len(entries) == EXPECTED_MANIFEST_DATES and len(selected) != EXPECTED_BUSINESS_DECISION_DATES:
        raise ContractError("weekday decision-date count mismatch")
    if (
        any(day.weekday() >= 5 for day in selected)
        or selected != tuple(sorted(selected))
        or len(selected) != len(set(selected))
    ):
        raise ContractError("invalid business-date contract")
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


def _finite_spread(value: object) -> int:
    if type(value) not in {float, int} or isinstance(value, bool):
        raise ContractError("invalid spread type")
    number = float(value)
    if not math.isfinite(number) or number < 0 or number != int(number):
        raise ContractError("invalid spread value")
    return int(number)


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


def split_contiguous_m1(
    rows: Sequence[Mapping[str, object]],
) -> tuple[list[list[dict[str, object]]], dict[str, int]]:
    """Split into exact contiguous minute segments; never bridge gaps/duplicates."""

    ordered: list[dict[str, object]] = []
    for row in rows:
        if type(row) is not dict and not isinstance(row, Mapping):
            raise ContractError("M1 row must be a mapping")
        at = _as_utc(row["time_utc"])
        if not _minute_aligned(at):
            raise ContractError("M1 timestamp must be minute-aligned")
        open_price, high, low, close = _ohlc(row)
        ordered.append(
            {
                "time_utc": at,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
            }
        )
    ordered.sort(key=lambda item: item["time_utc"])
    times = [item["time_utc"] for item in ordered]
    if len(times) != len(set(times)):
        raise ContractError("duplicate M1 timestamps")
    segments: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    gap_breaks = 0
    for item in ordered:
        if not current:
            current = [item]
            continue
        previous = current[-1]["time_utc"]
        delta = item["time_utc"] - previous
        if delta == timedelta(minutes=1):
            current.append(item)
        elif delta > timedelta(minutes=1):
            gap_breaks += 1
            segments.append(current)
            current = [item]
        else:
            raise ContractError("non-increasing M1 timestamps after sort")
    if current:
        segments.append(current)
    quality = {
        "input_rows": len(ordered),
        "contiguous_rows": sum(len(segment) for segment in segments),
        "segments": len(segments),
        "gap_breaks": gap_breaks,
    }
    return segments, quality


def compute_jump_state(
    segment: Sequence[Mapping[str, object]],
) -> tuple[list[float | None], list[float | None], list[bool], list[float | None]]:
    """Per-bar return, robust scale (prior-240 excl. current), jump flag, threshold."""

    n = len(segment)
    returns: list[float | None] = [None] * n
    scales: list[float | None] = [None] * n
    jumps: list[bool] = [False] * n
    thresholds: list[float | None] = [None] * n
    roller = _RollingAbsMedian(LOOKBACK_RETURNS)
    for index in range(1, n):
        close_now = float(segment[index]["close"])
        close_prev = float(segment[index - 1]["close"])
        ret = (close_now - close_prev) / PIP
        if not math.isfinite(ret):
            raise ContractError("non-finite M1 return")
        returns[index] = ret
        # Scale uses exact 240 returns ending at t-1 (exclude current).
        if roller.ready():
            scale = roller.median()
            if not math.isfinite(scale) or scale < 0:
                raise ContractError("invalid robust scale")
            scales[index] = scale
            threshold = max(JUMP_FLOOR_PIPS, JUMP_SCALE_MULT * scale)
            thresholds[index] = threshold
            jumps[index] = ge_inclusive(abs(ret), threshold)
        # Push current return after scale for this bar so next bar can use it.
        roller.push(ret)
    return returns, scales, jumps, thresholds


def try_form_cluster(
    segment: Sequence[Mapping[str, object]],
    returns: Sequence[float | None],
    jumps: Sequence[bool],
    peak_index: int,
) -> dict[str, object] | None:
    """Form a frozen 15-bar cluster peak ending on a jump bar, or None."""

    if peak_index < CLUSTER_BARS - 1:
        return None
    if not jumps[peak_index]:
        return None
    start = peak_index - (CLUSTER_BARS - 1)
    jump_indices = [index for index in range(start, peak_index + 1) if jumps[index]]
    if len(jump_indices) < MIN_CLUSTER_JUMPS:
        return None
    signs: list[int] = []
    for index in jump_indices:
        ret = returns[index]
        if ret is None:
            return None
        sign = _sign(float(ret))
        if sign == 0:
            return None
        signs.append(sign)
    n_pos = sum(1 for sign in signs if sign > 0)
    n_neg = len(signs) - n_pos
    if n_pos == n_neg:
        return None
    if n_pos > n_neg:
        dominant = 1
        coherence = n_pos / float(len(signs))
    else:
        dominant = -1
        coherence = n_neg / float(len(signs))
    if not ge_inclusive(coherence, COHERENCE_MIN):
        return None
    first_jump = jump_indices[0]
    anchor = float(segment[first_jump]["open"])
    peak_close = float(segment[peak_index]["close"])
    signed_disp_pips = (peak_close - anchor) / PIP
    if not math.isfinite(signed_disp_pips):
        return None
    if _sign(signed_disp_pips) != dominant:
        return None
    if not ge_inclusive(abs(signed_disp_pips), MIN_DISPLACEMENT_PIPS):
        return None
    if dominant > 0:
        extreme = max(float(segment[index]["high"]) for index in range(start, peak_index + 1))
    else:
        extreme = min(float(segment[index]["low"]) for index in range(start, peak_index + 1))
    distance = abs(extreme - anchor)
    if not math.isfinite(distance) or not gt_strict(distance, 0.0):
        return None
    return {
        "peak_index": peak_index,
        "window_start": start,
        "first_jump_index": first_jump,
        "dominant_sign": dominant,
        "coherence": float(coherence),
        "jump_count": len(jump_indices),
        "anchor": anchor,
        "extreme": extreme,
        "distance": distance,
        "signed_disp_pips": float(signed_disp_pips),
        "peak_time": _as_utc(segment[peak_index]["time_utc"]),
    }


def retracement_fraction(
    *,
    dominant_sign: int,
    extreme: float,
    anchor: float,
    decision_close: float,
) -> float | None:
    distance = abs(extreme - anchor)
    if not math.isfinite(distance) or not gt_strict(distance, 0.0):
        return None
    if dominant_sign > 0:
        # Up cluster: re-entry from high extreme toward lower anchor.
        frac = (extreme - decision_close) / distance
    else:
        frac = (decision_close - extreme) / distance
    if not math.isfinite(frac):
        return None
    return float(frac)


def three_bar_no_jump(jumps: Sequence[bool], decision_index: int) -> bool:
    if decision_index < NO_JUMP_LOOKBACK:
        return False
    for index in range(decision_index - NO_JUMP_LOOKBACK, decision_index + 1):
        if jumps[index]:
            return False
    return True


def select_raw_signals(
    segments: Sequence[Sequence[Mapping[str, object]]],
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Causal cluster-decay decisions; first per UTC date only."""

    selected: list[dict[str, object]] = []
    consumed_dates: set[date] = set()
    funnel = Counter()
    for segment in segments:
        if len(segment) < LOOKBACK_RETURNS + CLUSTER_BARS + DECAY_MAX_BARS + 2:
            funnel["SEGMENT_TOO_SHORT"] += 1
            continue
        returns, scales, jumps, thresholds = compute_jump_state(segment)
        pending: dict[str, object] | None = None
        for index in range(len(segment)):
            cluster = try_form_cluster(segment, returns, jumps, index)
            if cluster is not None:
                pending = cluster
                funnel["CLUSTER_PEAK"] += 1
            if pending is None:
                continue
            peak_index = int(pending["peak_index"])
            if index <= peak_index:
                continue
            if index > peak_index + DECAY_MAX_BARS:
                pending = None
                funnel["DECAY_EXPIRED"] += 1
                continue
            if not three_bar_no_jump(jumps, index):
                funnel["JUMP_IN_DECAY_WINDOW"] += 1
                continue
            close = float(segment[index]["close"])
            frac = retracement_fraction(
                dominant_sign=int(pending["dominant_sign"]),
                extreme=float(pending["extreme"]),
                anchor=float(pending["anchor"]),
                decision_close=close,
            )
            if frac is None:
                funnel["RETRACE_UNDEFINED"] += 1
                continue
            if not (ge_inclusive(frac, RETRACE_MIN) and le_inclusive(frac, RETRACE_MAX)):
                funnel["RETRACE_OUT_OF_BAND"] += 1
                continue
            decision = _as_utc(segment[index]["time_utc"])
            day = decision.date()
            if day in consumed_dates:
                funnel["DAILY_REFRACTORY"] += 1
                pending = None
                continue
            dominant = int(pending["dominant_sign"])
            true_dir = "SHORT" if dominant > 0 else "LONG"
            follow_dir = "LONG" if dominant > 0 else "SHORT"
            extreme = float(pending["extreme"])
            anchor = float(pending["anchor"])
            stop_pips = max(MIN_STOP_PIPS, abs(extreme - anchor) / PIP + STOP_BUFFER_PIPS)
            if not math.isfinite(stop_pips) or stop_pips <= 0:
                funnel["INVALID_STOP"] += 1
                pending = None
                continue
            cost_ratio = COST_PIPS / stop_pips
            entry_candidate = decision + timedelta(minutes=1)
            selected.append(
                {
                    "time_utc": decision,
                    "availability_utc": entry_candidate,
                    "date": day,
                    "year": decision.year,
                    "dominant_sign": dominant,
                    "coherence": float(pending["coherence"]),
                    "jump_count": int(pending["jump_count"]),
                    "retracement": float(frac),
                    "anchor": anchor,
                    "extreme": extreme,
                    "signed_disp_pips": float(pending["signed_disp_pips"]),
                    "stop_distance_pips": float(stop_pips),
                    "cost_to_stop_ratio": float(cost_ratio),
                    "true_direction": true_dir,
                    "follow_control_direction": follow_dir,
                    "cluster_peak_utc": _iso_z(pending["peak_time"]),
                    "scale_at_peak": scales[peak_index],
                    "threshold_at_peak": thresholds[peak_index],
                }
            )
            consumed_dates.add(day)
            funnel["DECISION"] += 1
            pending = None
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
    return f"JCDR001-SRC-{sha256_bytes(identity)[:16]}"


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
        if availability != decision + timedelta(minutes=1):
            raise ContractError("signal availability must equal next M1 open")
        day = decision.date()
        if day in seen_dates:
            raise ContractError("raw first-per-day contract violated")
        seen_dates.add(day)
        source_signal_id = assign_source_signal_id(decision)
        if source_signal_id in seen_source_ids:
            raise ContractError("duplicate source_signal_id")
        seen_source_ids.add(source_signal_id)
        # Entry requires contiguous next-minute observation.
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
            "dominant_sign": int(signal["dominant_sign"]),
            "coherence": float(signal["coherence"]),
            "jump_count": int(signal["jump_count"]),
            "retracement": float(signal["retracement"]),
            "signed_disp_pips": float(signal["signed_disp_pips"]),
            "stop_distance_pips": float(signal["stop_distance_pips"]),
            "cost_to_stop_ratio": float(signal["cost_to_stop_ratio"]),
            "cluster_peak_utc": str(signal["cluster_peak_utc"]),
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
            candidate_id = f"JCDR001-{arm}-{sha256_bytes(identity)[:16]}"
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


def evaluate_stage0_gates(
    *,
    true_signals: Sequence[Mapping[str, object]],
    follow_signals: Sequence[Mapping[str, object]],
    raw_first_per_day_count: int,
    horizon_records: Sequence[Mapping[str, object]],
    formation_complete: int,
    formation_scheduled: int,
    elapsed_weeks: float,
) -> dict[str, object]:
    if (
        type(elapsed_weeks) not in {int, float}
        or isinstance(elapsed_weeks, bool)
        or not math.isfinite(float(elapsed_weeks))
        or float(elapsed_weeks) <= 0
        or type(formation_complete) is not int
        or type(formation_scheduled) is not int
        or not 0 <= formation_complete <= formation_scheduled
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
    formation_ratio = formation_complete / formation_scheduled if formation_scheduled else 0.0
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
    gates = {
        "outcome_blind_plane_intact": True,
        "follow_control_matched_true_one_to_one": follow_match,
        "formation_domain_completeness_at_least_0_99": ge_inclusive(formation_ratio, 0.99),
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
    if len(gates) != 11:
        raise ContractError("Stage-0 must expose exactly eleven gates")
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
            "formation_complete": formation_complete,
            "formation_scheduled": formation_scheduled,
            "formation_completeness_ratio": formation_ratio,
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
        "spread",
    }
    forbidden_fragments = (
        "post_entry",
        "target_hit",
        "stop_hit",
        "entry_price",
        "exit_price",
        "tick_volume",
    )
    allowed_entry_exit = {
        "entry_open_utc",
        "time_exit_utc",
        "required_m1_starts",
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
    receipt = parse_canonical_object(payload, label="JCDR implementation review receipt")
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
    """Validate producer schema including tick_volume/spread; signal uses OHLC only."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(pa.BufferReader(payload))
        schema_names = set(parquet.schema_arrow.names)
        missing = [name for name in PRODUCER_SCHEMA_COLUMNS if name not in schema_names]
        if missing:
            raise ValueError(f"missing producer columns: {missing}")
        # Read producer columns for schema validation, then keep signal columns only.
        table = parquet.read(columns=list(PRODUCER_SCHEMA_COLUMNS))
        rows = table.to_pylist()
        signal_rows: list[dict[str, object]] = []
        for row in rows:
            # Schema-validate tick_volume/spread then discard — never as signal.
            _finite_tick_volume(row["tick_volume"])
            _finite_spread(row["spread"])
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
            cleaned.append(
                {
                    "time_utc": utc_value.replace(tzinfo=UTC),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                }
            )
        return tuple(cleaned)
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("decoded shard day/OHLC contract mismatch") from exc


def _load_public_rows(
    *,
    workspace: Path,
    entries: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    root = workspace / M1_ROOT_REL
    result: list[dict[str, object]] = []
    for entry in entries:
        relative = Path(str(entry["relative_path"]))
        # Fail-closed: every opened shard must be public DESIGN path only.
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
    try:
        descriptor = os.open(path, flags, 0o600)
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
        info = os.lstat(path)
        if (
            not stat.S_ISREG(info.st_mode)
            or path.is_symlink()
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
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or _is_reparse(info) or int(info.st_nlink) != 1:
        raise ContractError("durable artifact identity mismatch")
    payload = path.read_bytes()
    if len(payload) != int(info.st_size) or _identity(os.lstat(path)) != _identity(info):
        raise ContractError("durable artifact changed during readback")
    return payload


def _existing_artifact_hashes(root: Path) -> dict[str, str]:
    try:
        names = sorted(
            entry.name
            for entry in os.scandir(root)
            if entry.is_file(follow_symlinks=False) and entry.name != "attempt_terminal.json"
        )
    except FileNotFoundError as exc:
        raise ContractError("evidence root missing during artifact hash binding") from exc
    hashes: dict[str, str] = {}
    for name in names:
        path = root / name
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or path.is_symlink() or _is_reparse(info):
            raise ContractError(f"non-regular artifact rejected: {name}")
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
                "schema_version": "jcdr_001_attempt_started.v1",
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
                    "schema_version": "jcdr_001_source_ledger_row.v1",
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
    _write_new_canonical(root / "jcdr_001_source_report.json", enriched)
    classifications = enriched.get("raw_signal_classifications")
    if type(classifications) is not list:
        raise ContractError("report missing exact-once classifications")
    classification_rows = []
    for row in classifications:
        if type(row) is not dict:
            raise ContractError("classification row malformed")
        classification_rows.append(
            {
                "schema_version": "jcdr_001_source_classification_row.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "reviewed_registry_row_sha256": reviewed_row_sha256,
                "attempt_started_sha256": started_sha,
                **row,
            }
        )
    assert_outcome_blind(classification_rows)
    _write_new_jsonl(root / "jcdr_001_source_classifications.jsonl", classification_rows)
    flattened = _flatten_ledgers(
        enriched,
        reviewed_row_sha256=reviewed_row_sha256,
        attempt_started_sha256=started_sha,
    )
    _write_new_jsonl(root / "jcdr_001_source_ledger.jsonl", flattened)
    first_hashes = _existing_artifact_hashes(root)
    stage0 = enriched.get("stage0")
    verdict = stage0.get("verdict") if type(stage0) is dict else None
    terminal_status = _stage0_to_terminal_status(verdict)
    receipt = {
        "schema_version": "jcdr_001_source_feasibility_receipt.v1",
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
        "schema_version": "jcdr_001_attempt_terminal.v1",
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
    try:
        info = os.lstat(terminal)
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode):
        raise ContractError("attempt_terminal path is a directory; cannot replace safely")
    try:
        os.unlink(terminal)
    except FileNotFoundError:
        return
    except OSError as unlink_exc:
        raise ContractError("failed to remove suspect attempt_terminal") from unlink_exc
    try:
        os.lstat(terminal)
    except FileNotFoundError:
        return
    raise ContractError("suspect attempt_terminal still present after unlink")


def _persist_engineering_failure(root: Path, reviewed_row_sha256: str, error: Exception) -> None:
    terminal = Path(root) / "attempt_terminal.json"
    _safe_unlink_attempt_terminal(Path(root))
    value = {
        "schema_version": "jcdr_001_attempt_terminal.v1",
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
        }
        _ohlc(item)
        copied.append(item)
    return tuple(copied)


def _immutable_date_copy(business_dates: Sequence[date]) -> tuple[date, ...]:
    copied = tuple(date(day.year, day.month, day.day) for day in business_dates)
    if any(type(day) is not date for day in copied):
        raise ContractError("business dates must be date objects")
    return copied


def formation_domain_counts(
    segments: Sequence[Sequence[Mapping[str, object]]],
    quality: Mapping[str, int],
) -> tuple[int, int]:
    """Formation completeness: bars with full prior-240 scale vs all contiguous rows."""

    scheduled = int(quality["contiguous_rows"])
    complete = 0
    for segment in segments:
        if len(segment) <= LOOKBACK_RETURNS:
            continue
        # Bars with index >= LOOKBACK_RETURNS+? : first return at 1, scale ready at index 241.
        # Indices with valid scale: LOOKBACK_RETURNS + 1 .. n-1 inclusive count.
        complete += max(0, len(segment) - (LOOKBACK_RETURNS + 1))
    if complete > scheduled:
        raise ContractError("formation complete exceeds scheduled")
    return complete, scheduled


def canonical_scan_projection(report: Mapping[str, object]) -> dict[str, object]:
    stage0 = report.get("stage0")
    if type(stage0) is not dict:
        raise ContractError("scan projection requires stage0")
    projection = {
        "hypothesis_id": report.get("hypothesis_id"),
        "attempt_id": report.get("attempt_id"),
        "arm_counts": report.get("arm_counts"),
        "population": report.get("population"),
        "formation_diagnostics": report.get("formation_diagnostics"),
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
    business_dates: Sequence[date],
) -> dict[str, object]:
    """One-pass pure scan. Does not call independent replay (no recursion)."""

    if business_dates is None:
        raise ContractError("business_dates required")
    _ = _immutable_date_copy(business_dates)  # validate date objects
    segments, quality = split_contiguous_m1(m1_rows)
    observed = {_as_utc(row["time_utc"]) for segment in segments for row in segment}
    raw, funnel = select_raw_signals(segments)
    ledgers = build_matched_ledgers(raw, observed)
    formation_complete, formation_scheduled = formation_domain_counts(segments, quality)
    stage0 = evaluate_stage0_gates(
        true_signals=ledgers["TRUE"],
        follow_signals=ledgers["FOLLOW_CONTROL"],
        raw_first_per_day_count=int(ledgers["raw_first_per_day_count"]),
        horizon_records=ledgers["horizons"],
        formation_complete=formation_complete,
        formation_scheduled=formation_scheduled,
        elapsed_weeks=ELAPSED_CALENDAR_WEEKS,
    )
    exact_once = ledgers["exact_once"]
    report = {
        "schema_version": "jcdr_001_source_feasibility_report.v1",
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
            "m1_quality": quality,
            "plan_sha256": PLAN_SHA256,
            "robust_scale_lookback": LOOKBACK_RETURNS,
            "jump_floor_pips": JUMP_FLOOR_PIPS,
            "jump_scale_mult": JUMP_SCALE_MULT,
            "cluster_bars": CLUSTER_BARS,
            "min_cluster_jumps": MIN_CLUSTER_JUMPS,
            "coherence_min": COHERENCE_MIN,
            "min_displacement_pips": MIN_DISPLACEMENT_PIPS,
            "decay_max_bars": DECAY_MAX_BARS,
            "retrace_band": [RETRACE_MIN, RETRACE_MAX],
            "horizon_bars": HORIZON_BARS,
            "matched_arms": list(ARM_NAMES),
            "ohlc_only_signal_inputs": True,
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
        "formation_diagnostics": {
            "scheduled_rows": formation_scheduled,
            "complete_scale_rows": formation_complete,
            "completeness_ratio": formation_complete / formation_scheduled if formation_scheduled else 0.0,
            "funnel": funnel,
            "m1_quality": quality,
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
    business_dates: Sequence[date],
    primary_report: Mapping[str, object],
) -> dict[str, object]:
    if type(primary_report) is not dict and not isinstance(primary_report, Mapping):
        raise ContractError("primary report must be a mapping")
    m1_copy = _immutable_m1_copy(m1_rows)
    dates_copy = _immutable_date_copy(business_dates)
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
    business_dates: Sequence[date],
    *,
    with_independent_replay: bool = True,
) -> dict[str, object]:
    primary = scan_source_once(m1_rows, business_dates)
    if with_independent_replay is not True:
        return primary
    replay_meta = independent_replay_scan(m1_rows, business_dates, primary)
    report = dict(primary)
    report["independent_replay"] = replay_meta
    report["canonical_digest_sha256"] = replay_meta["primary_canonical_digest_sha256"]
    report["replay_canonical_digest_sha256"] = replay_meta["replay_canonical_digest_sha256"]
    report["exact_once_reconciliation"] = True
    assert_outcome_blind(report)
    return report


def assert_independent_replay_rejects_mutation(
    m1_rows: Sequence[Mapping[str, object]],
    business_dates: Sequence[date],
    *,
    mode: str,
) -> None:
    primary = scan_source_once(m1_rows, business_dates)
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
        independent_replay_scan(m1_rows, business_dates, mutated)
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
    return scan_source(m1_rows, weekday_decision_dates(m1_entries), with_independent_replay=True)


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
