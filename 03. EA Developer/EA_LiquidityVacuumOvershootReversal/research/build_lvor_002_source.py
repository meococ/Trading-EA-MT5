#!/usr/bin/env python3
"""Inert outcome-blind source probe for HYP-LVOR-EURUSD-M15-002.

The module is synthetic-testable. Real public DESIGN cannot be opened unless a
future independent review arms the exact latest canonical registry-row hash and
the caller supplies the explicit one-shot run switch.
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
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Callable, Iterable, Mapping, NamedTuple, Sequence


HYPOTHESIS_ID = "HYP-LVOR-EURUSD-M15-002"
PARENT_HYPOTHESIS_ID = "HYP-LVOR-EURUSD-M15-001"
EA_NAME = "EA_LiquidityVacuumOvershootReversal"
FAMILY = "liquidity-vacuum-overshoot-reversal"
ATTEMPT_ID = "LVOR002-SOURCE-ATTEMPT-001"
PLAN_REL = (
    "03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/"
    "HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_PLAN.md"
)
PLAN_SHA256 = "C9B32B9D381E244B6287D2F50E773294A7B18407ED56A3A6FA35B801D1ABF414"
BUILDER_REL = (
    "03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/"
    "build_lvor_002_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/tests/"
    "test_build_lvor_002_source.py"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/"
    "HYP-LVOR-EURUSD-M15-002_SOURCE_FEASIBILITY_ATTEMPTS/"
    f"{ATTEMPT_ID}"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/"
    "HYP-LVOR-EURUSD-M15-002_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REVIEW_RECEIPT_SCHEMA = "lvor_002_source_implementation_review_receipt.v1"
PROBE_STATUS = "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN"
PARENT_TERMINAL_REL = (
    "03. EA Developer/EA_LiquidityVacuumOvershootReversal/research/evidence/"
    "HYP-LVOR-EURUSD-M15-001_SOURCE_FEASIBILITY_ATTEMPTS/"
    "LVOR001-SOURCE-ATTEMPT-001/attempt_terminal.json"
)
PARENT_TERMINAL_SHA256 = "F0CFC1AE6496E0C3799CA5D424A8E2F2DA3271971CE97BB5ACCD1CDB67D62384"
PARENT_ATTEMPT_STARTED_SHA256 = "D7109B7ACA72B6639C8E3271E858EF8B284C017A252310AD9A83A0FCE52C62EA"
PARENT_REVIEWED_REGISTRY_ROW_SHA256 = "722E3BA3260D953FBD865EA4ED2F735A6609003C193045AA1AF5781DFF5299D8"

REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR_REL = "04. Memory/research/validate_candidate_registry.py"
REGISTRY_VALIDATOR_SHA256 = "B04B379E11F556A0CF3E6C3264768176310FF01CF360CC3B92464C51A2996DD0"
REGISTRY_SCHEMA_REL = "04. Memory/research/CANDIDATE_REGISTRY.schema.json"
REGISTRY_SCHEMA_SHA256 = "96C80D3C46A105A9754CA1325F3DD6C160D92A9D5800ECBC402DE0F40C612F5C"
CLOCK_REL = "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"

M1_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/splitvault_002"
M1_MANIFEST_REL = f"{M1_ROOT_REL}/public/design_manifest.jsonl"
M1_RECEIPT_REL = f"{M1_ROOT_REL}/public/design_receipt.json"
M1_MANIFEST_SHA256 = "A8A091DA8365602CB1D02BA571E96B4FB00B50621A73166B8CEDDBC1A7EED8C7"
M1_RECEIPT_SHA256 = "8109B11B6054517B9904FB4ACEF25EB7C6BD2485487CA9D69340DDC7E7D27FF8"
M1_SOURCE_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
H1_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/h1_splitvault_002"
H1_MANIFEST_REL = f"{H1_ROOT_REL}/public/design_manifest.jsonl"
H1_RECEIPT_REL = f"{H1_ROOT_REL}/public/design_receipt.json"
H1_MANIFEST_SHA256 = "DA513911B01B1C4232611225C77A4F22E9E3C89E719EE530923BD574D06451E5"
H1_RECEIPT_SHA256 = "623328512F0CB77B52B155F6CD314EA2B47DAC40636A7714BD38167BEA807B13"
H1_COLLECTION_ID = "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002"
H1_RECEIPT_SCHEMA = "h1_splitvault_002_public_receipt.v1"
H1_MANIFEST_ROW_SCHEMA = "h1_splitvault_002_public_design_shard.v1"

# Independent review must replace this exact sentinel before a real read.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

UTC = timezone.utc
PIP = 0.0001
DESIGN_START = date(2016, 1, 4)
DESIGN_END = date(2020, 12, 31)
EXPECTED_MANIFEST_DATES = 1_555
EXPECTED_BUSINESS_DECISION_DATES = 1_298
EXPECTED_SUNDAY_DATES = 257
EXPECTED_M1_DESIGN_ROWS = 1_859_820
EXPECTED_H1_DESIGN_ROWS = 31_057
EXPECTED_H1_RAW_SOURCE_ROWS = 71_785
ELAPSED_CALENDAR_WEEKS = 260.5714285714
HEX = frozenset("0123456789ABCDEF")
FORBIDDEN_PATH_PARTS = frozenset({"private", "sealed", "validation", "holdout"})
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
INTENDED_TRUE_VALIDATION_FIELDS = {"source_feasibility_only", "source_run_authorized"}
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
    "clock_path",
    "clock_sha256",
    "design_m1_manifest_path",
    "design_m1_manifest_sha256",
    "design_m1_receipt_path",
    "design_m1_receipt_sha256",
    "design_m1_source_sha256",
    "design_h1_manifest_path",
    "design_h1_manifest_sha256",
    "design_h1_receipt_path",
    "design_h1_receipt_sha256",
    "design_h1_price_side",
    "registry_validator_path",
    "registry_validator_sha256",
    "registry_schema_path",
    "registry_schema_sha256",
    "parent_terminal_path",
    "parent_terminal_sha256",
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
M1_RECEIPT_FIELDS = {
    "collection_plan_sha256", "custodian_full_corpus_decoded", "custodian_tool_sha256",
    "design_dates", "design_manifest_sha256", "design_rows", "exact_once_status",
    "private_custody_digest", "private_custody_receipt_sha256", "research_holdout_opened",
    "research_validation_opened", "source_bytes", "source_footer_length",
    "source_footer_start", "source_footer_sha256", "source_sha256", "source_attempt_id",
    "stage_path", "stage_role", "supervisor_review_base_sha256", "verdict",
}
H1_RECEIPT_FIELDS = {
    "collection_id", "design_dates", "design_manifest_sha256", "raw_source_opens",
    "research_holdout_opened", "research_validation_opened", "schema_version",
    "source_attempt_id", "source_rows", "unselected_shard_opens", "verdict",
}


class ContractError(RuntimeError):
    """A fail-closed contract violation."""


class DecodedShard(NamedTuple):
    schema: tuple[tuple[str, str, bool], ...]
    row_groups: int
    rows: tuple[dict[str, object], ...]


class TimestampIndex(NamedTuple):
    """Immutable, one-time validated timestamp indexes shared by every signal."""

    observed_m1: tuple[datetime, ...]
    complete_m5_starts: tuple[datetime, ...]


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
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
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
        if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
            raise ValueError
        value = _json_load(payload[:-1])
        if type(value) is not dict or canonical_json(value) + b"\n" != payload:
            raise ValueError
        return value
    except Exception as exc:
        raise ContractError(f"invalid canonical {label}") from exc


def parse_canonical_jsonl(payload: bytes, *, label: str) -> list[dict[str, object]]:
    try:
        if not payload or not payload.endswith(b"\n") or b"\n\n" in payload:
            raise ValueError
        rows = []
        for line in payload.splitlines():
            value = _json_load(line)
            if type(value) is not dict or canonical_json(value) != line:
                raise ValueError
            rows.append(value)
        return rows
    except Exception as exc:
        raise ContractError(f"invalid canonical {label}") from exc


def parse_registry_jsonl(payload: bytes) -> tuple[list[dict[str, object]], list[bytes]]:
    try:
        if not payload:
            raise ValueError("empty registry")
        raw_rows = payload.splitlines(keepends=True)
        rows: list[dict[str, object]] = []
        for number, record in enumerate(raw_rows, start=1):
            if not record.endswith(b"\n") or record.endswith(b"\r\n") or record.count(b"\n") != 1:
                raise ValueError(f"line {number}: exact terminal LF required")
            encoding = "utf-8-sig" if number == 1 else "utf-8"
            raw = record[:-1].decode(encoding, errors="strict")
            if not raw.strip():
                raise ValueError(f"line {number}: blank row")
            value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
            if type(value) is not dict:
                raise ValueError("registry row root")
            rows.append(value)
        return rows, raw_rows
    except Exception as exc:
        raise ContractError("invalid strict registry JSONL") from exc


def validate_registry_snapshot(
    *, registry_payload: bytes, validator_payload: bytes, schema_payload: bytes, validator_path: Path
) -> None:
    if sha256_bytes(validator_payload) != REGISTRY_VALIDATOR_SHA256:
        raise ContractError("canonical registry validator SHA mismatch")
    if sha256_bytes(schema_payload) != REGISTRY_SCHEMA_SHA256:
        raise ContractError("canonical registry schema SHA mismatch")
    try:
        module = types.ModuleType("_lvor_verified_candidate_registry_validator")
        module.__file__ = str(Path(validator_path).absolute())
        exec(compile(validator_payload, module.__file__, "exec"), module.__dict__)
        validate = getattr(module, "validate_registry", None)
        if not callable(validate):
            raise ValueError("validator callable missing")
        errors = validate(
            ImmutableBytesFile(REGISTRY_REL, registry_payload),
            ImmutableBytesFile(REGISTRY_SCHEMA_REL, schema_payload),
        )
        if type(errors) is not list or any(type(error) is not str for error in errors) or errors:
            raise ValueError("validator errors")
    except Exception as exc:
        raise ContractError("canonical registry validator failed closed") from exc


def reviewed_base_source_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
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
        int(info.st_dev), int(info.st_ino), int(info.st_size), int(info.st_mtime_ns),
        int(info.st_nlink), int(getattr(info, "st_file_attributes", 0)),
    )


def _inside(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(root)))) == os.path.normcase(str(root))
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
            current /= component
            info = os.lstat(current)
            if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _is_reparse(info):
                raise ValueError("directory alias")
            anchors.append((current, _identity(info)))
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or path.is_symlink() or _is_reparse(before) or int(before.st_nlink) != 1:
            raise ValueError("file alias")
        pinned = _identity(before)
        flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(path, flags)
        try:
            if _identity(os.fstat(descriptor)) != pinned:
                raise ValueError("identity changed")
            chunks = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            final = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        payload = b"".join(chunks)
        if _identity(final) != pinned or _identity(os.lstat(path)) != pinned or len(payload) != pinned[2] or any(_identity(os.lstat(directory)) != identity for directory, identity in anchors):
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


def _business_date_tuple(values: Sequence[date]) -> tuple[date, ...]:
    days = tuple(values)
    if (
        any(type(day) is not date or day.weekday() >= 5 for day in days)
        or days != tuple(sorted(days))
        or len(days) != len(set(days))
    ):
        raise ContractError("invalid business-date contract")
    return days


def validate_public_metadata(
    *,
    kind: str,
    receipt_payload: bytes,
    manifest_payload: bytes,
    expected_receipt_sha256: str,
    expected_manifest_sha256: str,
) -> list[dict[str, object]]:
    if kind not in {"M1", "H1"}:
        raise ContractError("unknown public metadata kind")
    if sha256_bytes(receipt_payload) != expected_receipt_sha256 or sha256_bytes(manifest_payload) != expected_manifest_sha256:
        raise ContractError("public metadata hash mismatch")
    receipt = parse_canonical_object(receipt_payload, label=f"{kind} receipt")
    rows = parse_canonical_jsonl(manifest_payload, label=f"{kind} manifest")
    if (
        receipt.get("design_manifest_sha256") != sha256_bytes(manifest_payload)
        or receipt.get("research_validation_opened") is not False
        or receipt.get("research_holdout_opened") is not False
        or receipt.get("design_dates") != len(rows)
    ):
        raise ContractError("public receipt binding mismatch")
    if kind == "M1":
        if (
            set(receipt) != M1_RECEIPT_FIELDS
            or receipt.get("custodian_full_corpus_decoded") is not True
            or receipt.get("exact_once_status") != "PASS"
            or receipt.get("source_sha256") != M1_SOURCE_SHA256
            or receipt.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
        ):
            raise ContractError("M1 receipt contract mismatch")
        fields = {"bytes", "date", "relative_path", "rows", "sha256"}
        leaf = "m1.parquet"
    else:
        if (
            set(receipt) != H1_RECEIPT_FIELDS
            or receipt.get("collection_id") != H1_COLLECTION_ID
            or receipt.get("schema_version") != H1_RECEIPT_SCHEMA
            or receipt.get("raw_source_opens") != 1
            or receipt.get("unselected_shard_opens") != 0
            or receipt.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
        ):
            raise ContractError("H1 receipt contract mismatch")
        fields = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
        leaf = "h1.parquet"
    previous: str | None = None
    for row in rows:
        day = _canonical_day(row.get("date"))
        if (
            set(row) != fields
            or (previous is not None and day <= previous)
            or row.get("relative_path") != f"public/DESIGN/{day}/{leaf}"
            or type(row.get("bytes")) is not int
            or row["bytes"] <= 0
            or type(row.get("rows")) is not int
            or row["rows"] <= 0
            or not _valid_sha(row.get("sha256"))
            or (kind == "H1" and row.get("schema_version") != H1_MANIFEST_ROW_SCHEMA)
        ):
            raise ContractError("manifest path/schema/hash/bytes/rows contract mismatch")
        previous = day
    selected = tuple(str(row["date"]) for row in rows)
    if (
        len(selected) != EXPECTED_MANIFEST_DATES
        or selected[0] != DESIGN_START.isoformat()
        or selected[-1] != DESIGN_END.isoformat()
        or sum(date.fromisoformat(day).weekday() < 5 for day in selected) != EXPECTED_BUSINESS_DECISION_DATES
        or sum(date.fromisoformat(day).weekday() == 6 for day in selected) != EXPECTED_SUNDAY_DATES
        or any(date.fromisoformat(day).weekday() == 5 for day in selected)
    ):
        raise ContractError("production DESIGN date boundary mismatch")
    total = sum(int(row["rows"]) for row in rows)
    if kind == "M1" and (total != EXPECTED_M1_DESIGN_ROWS or receipt.get("design_rows") != total):
        raise ContractError("M1 DESIGN row-count contract mismatch")
    if kind == "H1" and (total != EXPECTED_H1_DESIGN_ROWS or receipt.get("source_rows") != EXPECTED_H1_RAW_SOURCE_ROWS):
        raise ContractError("H1 DESIGN row-count contract mismatch")
    return rows


def validate_matching_manifest_date_sequences(
    m1_entries: Sequence[Mapping[str, object]], h1_entries: Sequence[Mapping[str, object]]
) -> tuple[str, ...]:
    m1_dates = tuple(_canonical_day(row.get("date")) for row in m1_entries)
    h1_dates = tuple(_canonical_day(row.get("date")) for row in h1_entries)
    if m1_dates != h1_dates:
        raise ContractError("M1/H1 manifest date sequence mismatch")
    return m1_dates


def weekday_decision_dates(entries: Sequence[Mapping[str, object]]) -> tuple[date, ...]:
    selected = tuple(
        date.fromisoformat(_canonical_day(row.get("date")))
        for row in entries
        if date.fromisoformat(_canonical_day(row.get("date"))).weekday() < 5
    )
    if len(entries) == EXPECTED_MANIFEST_DATES and len(selected) != EXPECTED_BUSINESS_DECISION_DATES:
        raise ContractError("weekday decision-date count mismatch")
    return _business_date_tuple(selected)


def _finite_price(value: object) -> float:
    if type(value) not in {int, float} or isinstance(value, bool):
        raise ContractError("invalid OHLC type")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ContractError("invalid OHLC value")
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


def _tick_volume(row: Mapping[str, object]) -> int:
    value = row.get("tick_volume")
    if type(value) is not int or isinstance(value, bool) or value < 0:
        raise ContractError("invalid tick volume")
    return value


def validate_decoded_shard(
    decoded: DecodedShard,
    *,
    kind: str,
    day: str,
    expected_rows: int,
    server_offset_hours: Callable[[datetime], int],
    server_to_utc: Callable[[datetime], datetime],
) -> tuple[dict[str, object], ...]:
    try:
        if (
            kind not in {"M1", "H1"}
            or type(decoded) is not DecodedShard
            or decoded.schema != EXPECTED_ARROW_SCHEMA
            or decoded.row_groups != 1
            or len(decoded.rows) != expected_rows
        ):
            raise ValueError
        keys = {field[0] for field in EXPECTED_ARROW_SCHEMA}
        previous: datetime | None = None
        for row in decoded.rows:
            if type(row) is not dict or set(row) != keys or any(value is None for value in row.values()):
                raise ValueError
            utc_value = row["time_utc"]
            server = row["time_server"]
            offset = row["utc_offset_h"]
            if (
                type(utc_value) is not datetime
                or type(server) is not datetime
                or utc_value.tzinfo is not None
                or server.tzinfo is not None
                or type(offset) is not int
                or isinstance(offset, bool)
                or utc_value.second
                or utc_value.microsecond
                or utc_value.date().isoformat() != day
                or server - utc_value != timedelta(hours=offset)
                or server_offset_hours(server) != offset
                or server_to_utc(server) != utc_value
                or (kind == "H1" and utc_value.minute != 0)
                or (previous is not None and utc_value <= previous)
            ):
                raise ValueError
            previous = utc_value
            _ohlc(row)
            for name, maximum in (("tick_volume", 2**64 - 1), ("spread", 2**31 - 1), ("real_volume", 2**64 - 1)):
                value = row[name]
                if type(value) is not int or isinstance(value, bool) or not 0 <= value <= maximum:
                    raise ValueError
        return decoded.rows
    except Exception as exc:
        raise ContractError("decoded shard schema/row-group/timezone/clock contract mismatch") from exc


def _floor_minutes(at: datetime, width: int) -> datetime:
    return at.replace(minute=at.minute - at.minute % width, second=0, microsecond=0)


def _aggregate_exact(
    ordered: Sequence[tuple[datetime, Mapping[str, object]]], width: int
) -> tuple[list[dict[str, object]], int]:
    groups: dict[datetime, list[tuple[datetime, Mapping[str, object]]]] = defaultdict(list)
    for at, row in ordered:
        groups[_floor_minutes(at, width)].append((at, row))
    complete: list[dict[str, object]] = []
    incomplete = 0
    for start in sorted(groups):
        group = groups[start]
        if [at for at, _ in group] != [start + timedelta(minutes=i) for i in range(width)]:
            incomplete += 1
            continue
        prices = [_ohlc(row) for _, row in group]
        complete.append(
            {
                "time_utc": start,
                "availability_utc": start + timedelta(minutes=width),
                "date": start.date(),
                "slot": (start.hour, start.minute),
                "open": prices[0][0],
                "high": max(item[1] for item in prices),
                "low": min(item[2] for item in prices),
                "close": prices[-1][3],
                "sum_tv": sum(_tick_volume(row) for _, row in group),
            }
        )
    return complete, incomplete


def build_complete_bars(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
    ordered: list[tuple[datetime, Mapping[str, object]]] = []
    for row in rows:
        try:
            at = _as_utc(row["time_utc"])
        except KeyError as exc:
            raise ContractError("M1 row missing time_utc") from exc
        if at.second or at.microsecond:
            raise ContractError("M1 timestamp is not minute aligned")
        _ohlc(row)
        _tick_volume(row)
        ordered.append((at, row))
    times = [at for at, _ in ordered]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ContractError("M1 timestamps are duplicated or unordered")
    m15, m15_incomplete = _aggregate_exact(ordered, 15)
    m5, m5_incomplete = _aggregate_exact(ordered, 5)
    return m15, m5, {
        "m15_observed": len(m15) + m15_incomplete,
        "m15_complete": len(m15),
        "m15_incomplete": m15_incomplete,
        "m5_observed": len(m5) + m5_incomplete,
        "m5_complete": len(m5),
        "m5_incomplete": m5_incomplete,
    }


def following_confirmation(
    m15: Mapping[str, object], m5_by_start: Mapping[datetime, Mapping[str, object]]
) -> Mapping[str, object] | None:
    start = _as_utc(m15.get("availability_utc"))
    confirmation = m5_by_start.get(start)
    if confirmation is None:
        return None
    if _as_utc(confirmation.get("availability_utc")) != start + timedelta(minutes=5):
        raise ContractError("immediate confirmation shape mismatch")
    return confirmation


def _prepare_activity_indexes(
    bars: Sequence[Mapping[str, object]], business_dates: Sequence[date]
) -> tuple[
    tuple[date, ...],
    Mapping[date, int],
    Mapping[tuple[date, tuple[int, int]], Mapping[str, object]],
]:
    days = _business_date_tuple(business_dates)
    date_index = {day: ordinal for ordinal, day in enumerate(days)}
    lookup: dict[tuple[date, tuple[int, int]], Mapping[str, object]] = {}
    for bar in bars:
        key = (bar.get("date"), bar.get("slot"))
        if type(key[0]) is not date or type(key[1]) is not tuple or key in lookup:
            raise ContractError("activity bars have invalid or duplicate date/slot")
        lookup[key] = bar
    return days, types.MappingProxyType(date_index), types.MappingProxyType(lookup)


def _activity_ratio_indexed(
    current: Mapping[str, object],
    days: tuple[date, ...],
    date_index: Mapping[date, int],
    bars_by_date_slot: Mapping[tuple[date, tuple[int, int]], Mapping[str, object]],
    *,
    lookback: int = 20,
) -> float | None:
    current_date = current.get("date")
    slot = current.get("slot")
    ordinal = date_index.get(current_date) if type(current_date) is date else None
    if ordinal is None or ordinal < lookback:
        return None
    history = []
    for prior_day in days[ordinal - lookback : ordinal]:
        prior = bars_by_date_slot.get((prior_day, slot))
        if prior is None or type(prior.get("sum_tv")) is not int or prior["sum_tv"] < 0:
            return None
        history.append(int(prior["sum_tv"]))
    numerator = current.get("sum_tv")
    denominator = float(median(history))
    if type(numerator) is not int or numerator < 0 or denominator <= 0:
        return None
    return numerator / denominator


def activity_ratio_for(
    current: Mapping[str, object],
    bars: Sequence[Mapping[str, object]],
    business_dates: Sequence[date],
) -> float | None:
    days, date_index, lookup = _prepare_activity_indexes(bars, business_dates)
    return _activity_ratio_indexed(current, days, date_index, lookup)


def _shifted_activity_indexed(
    current: Mapping[str, object],
    days: tuple[date, ...],
    date_index: Mapping[date, int],
    bars_by_date_slot: Mapping[tuple[date, tuple[int, int]], Mapping[str, object]],
    *,
    shift_dates: int = 5,
    lookback: int = 20,
) -> dict[str, object] | None:
    current_date = current.get("date")
    slot = current.get("slot")
    ordinal = date_index.get(current_date) if type(current_date) is date else None
    if ordinal is None or ordinal - shift_dates < lookback:
        return None
    source_date = days[ordinal - shift_dates]
    source = bars_by_date_slot.get((source_date, slot))
    if source is None:
        return None
    activity = _activity_ratio_indexed(
        source, days, date_index, bars_by_date_slot, lookback=lookback
    )
    if activity is None:
        return None
    return {"source_date": source_date, "activity": activity}


def shifted_activity_for(
    current: Mapping[str, object],
    bars: Sequence[Mapping[str, object]],
    business_dates: Sequence[date],
    *,
    shift_dates: int = 5,
) -> dict[str, object] | None:
    days, date_index, lookup = _prepare_activity_indexes(bars, business_dates)
    return _shifted_activity_indexed(
        current, days, date_index, lookup, shift_dates=shift_dates
    )


def _true_range(current: Mapping[str, object], previous_close: float | None) -> float:
    _, high, low, _ = _ohlc(current)
    return high - low if previous_close is None else max(
        high - low, abs(high - previous_close), abs(low - previous_close)
    )


def wilder_atr20_by_close(
    h1_bars: Sequence[Mapping[str, object]],
) -> list[tuple[datetime, float]]:
    ordered = sorted(h1_bars, key=lambda row: _as_utc(row["time_utc"]))
    times = [_as_utc(row["time_utc"]) for row in ordered]
    if times != [_as_utc(row["time_utc"]) for row in h1_bars] or len(times) != len(set(times)):
        raise ContractError("H1 bars are duplicated or unordered")
    true_ranges = []
    previous_close: float | None = None
    for row in ordered:
        true_ranges.append(_true_range(row, previous_close))
        previous_close = _ohlc(row)[3]
    if len(true_ranges) < 20:
        return []
    atr = sum(true_ranges[:20]) / 20.0
    if not math.isfinite(atr) or atr <= 0:
        raise ContractError("invalid ATR20 seed")
    result = [(times[19] + timedelta(hours=1), atr)]
    for ordinal in range(20, len(true_ranges)):
        atr = (19.0 * atr + true_ranges[ordinal]) / 20.0
        if not math.isfinite(atr) or atr <= 0:
            raise ContractError("invalid Wilder ATR20")
        result.append((times[ordinal] + timedelta(hours=1), atr))
    return result


def latest_wilder_atr20(
    h1_bars: Sequence[Mapping[str, object]], availability: datetime
) -> float | None:
    decision = _as_utc(availability)
    values = wilder_atr20_by_close(h1_bars)
    closes = [item[0] for item in values]
    ordinal = bisect.bisect_right(closes, decision) - 1
    return None if ordinal < 0 else values[ordinal][1]


def _decision_slot(at: datetime) -> bool:
    local = at.time().replace(tzinfo=None)
    return at.weekday() < 5 and time(6, 0) <= local < time(18, 0) and at.minute % 15 == 0


def price_surface(
    m15: Mapping[str, object], confirmation_m5: Mapping[str, object], *, atr20: float
) -> dict[str, object] | None:
    if type(atr20) not in {int, float} or isinstance(atr20, bool) or not math.isfinite(float(atr20)) or atr20 <= 0:
        raise ContractError("invalid ATR20")
    at = _as_utc(m15.get("time_utc"))
    m15_available = _as_utc(m15.get("availability_utc"))
    confirm_start = _as_utc(confirmation_m5.get("time_utc"))
    decision = _as_utc(confirmation_m5.get("availability_utc"))
    if confirm_start != m15_available or decision != confirm_start + timedelta(minutes=5):
        raise ContractError("confirmation is not immediately following M15")
    open_price, high, low, close = _ohlc(m15)
    confirm_open, _, _, confirm_close = _ohlc(confirmation_m5)
    span = high - low
    body = close - open_price
    if span <= 0 or body == 0:
        return None
    range_ratio = span / float(atr20)
    efficiency = abs(body) / span
    bullish = body > 0
    outer_fraction = (close - low) / span if bullish else (high - close) / span
    midpoint = (open_price + close) / 2.0
    confirmation_opposite = confirm_close < confirm_open if bullish else confirm_close > confirm_open
    midpoint_cross = confirm_close < midpoint if bullish else confirm_close > midpoint
    epsilon = 1e-12
    if not (
        0.50 - epsilon <= range_ratio <= 1.25 + epsilon
        and efficiency >= 0.70 - epsilon
        and outer_fraction >= 0.80 - epsilon
        and confirmation_opposite
        and midpoint_cross
    ):
        return None
    return {
        "time_utc": at,
        "availability_utc": decision,
        "direction": "SHORT" if bullish else "LONG",
        "year": at.year,
        "atr20": float(atr20),
        "range_atr_ratio": range_ratio,
        "impulse_efficiency": efficiency,
        "outer_close_fraction": outer_fraction,
        "confirmation_cross": True,
        "cost_to_sl_ratio": 1.50 / (float(atr20) / PIP),
    }


def select_daily_signals(
    candidates: Sequence[Mapping[str, object]], *, arm: str
) -> list[dict[str, object]]:
    if arm not in {"PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY"}:
        raise ContractError("unknown signal arm")
    selected: list[dict[str, object]] = []
    consumed: set[date] = set()
    for candidate in sorted(candidates, key=lambda row: _as_utc(row["time_utc"])):
        at = _as_utc(candidate["time_utc"])
        if not _decision_slot(at) or at.date() in consumed:
            continue
        if candidate.get("direction") not in {"LONG", "SHORT"}:
            continue
        if arm == "PRIMARY":
            activity = candidate.get("activity")
            if type(activity) not in {int, float} or isinstance(activity, bool) or not math.isfinite(float(activity)) or activity > 0.85:
                continue
        elif arm == "SHIFTED_ACTIVITY":
            shifted = candidate.get("shifted_activity")
            if type(shifted) not in {int, float} or isinstance(shifted, bool) or not math.isfinite(float(shifted)) or shifted > 0.85:
                continue
            if type(candidate.get("shifted_source_date")) is not date:
                continue
        row = dict(candidate)
        row["arm"] = arm
        selected.append(row)
        consumed.add(at.date())
    return selected


def _freeze_timestamp_sequence(
    values: Iterable[datetime], *, width_minutes: int
) -> tuple[datetime, ...]:
    frozen: list[datetime] = []
    previous: datetime | None = None
    for raw in values:
        value = _as_utc(raw)
        if (
            value.second
            or value.microsecond
            or (width_minutes == 5 and value.minute % 5)
            or (previous is not None and value <= previous)
        ):
            raise ContractError("timestamp index must be aligned and strictly increasing")
        frozen.append(value)
        previous = value
    return tuple(frozen)


def build_timestamp_index(
    observed_m1_timestamps: Iterable[datetime],
    complete_m5_starts: Iterable[datetime],
) -> TimestampIndex:
    """Traverse and validate each raw index exactly once, then freeze it."""

    return TimestampIndex(
        _freeze_timestamp_sequence(observed_m1_timestamps, width_minutes=1),
        _freeze_timestamp_sequence(complete_m5_starts, width_minutes=5),
    )


def map_timestamp_horizon(
    decision: datetime,
    timestamp_index: TimestampIndex,
) -> dict[str, object]:
    available = _as_utc(decision)
    if type(timestamp_index) is not TimestampIndex:
        raise ContractError("prevalidated timestamp index is required")
    observed_m1 = timestamp_index.observed_m1
    observed_m5 = timestamp_index.complete_m5_starts
    entry_ordinal = bisect.bisect_left(observed_m1, available)
    if entry_ordinal >= len(observed_m1):
        return {
            "entry_observed_m1_utc": None,
            "entry_delay_minutes": None,
            "m5_horizon_starts": tuple(),
            "exit_availability_utc": None,
            "delayed_over_60m": False,
            "unavailable": True,
            "right_censored": False,
            "source_executable": False,
            "reason": "NO_ENTRY_OBSERVED",
        }
    entry = observed_m1[entry_ordinal]
    delay = (entry - available).total_seconds() / 60.0
    m5_ordinal = bisect.bisect_left(observed_m5, entry)
    horizon = observed_m5[m5_ordinal : m5_ordinal + 6]
    delayed = delay > 60.0
    right_censored = len(horizon) < 6
    executable = not delayed and not right_censored
    reason = "SOURCE_EXECUTABLE" if executable else "RIGHT_CENSORED_LT6" if right_censored else "ENTRY_DELAY_GT_60M"
    return {
        "entry_observed_m1_utc": entry,
        "entry_delay_minutes": delay,
        "m5_horizon_starts": horizon,
        "exit_availability_utc": horizon[-1] + timedelta(minutes=5) if len(horizon) == 6 else None,
        "delayed_over_60m": delayed,
        "unavailable": False,
        "right_censored": right_censored,
        "source_executable": executable,
        "reason": reason,
    }

def _iso_z(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _serialize_horizon(value: Mapping[str, object]) -> dict[str, object]:
    result = dict(value)
    for key in ("entry_observed_m1_utc", "exit_availability_utc"):
        if result[key] is not None:
            result[key] = _iso_z(result[key])
    result["m5_horizon_starts"] = [_iso_z(item) for item in result["m5_horizon_starts"]]
    return result


def build_arm_ledgers(
    signals_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
    timestamp_index: TimestampIndex,
) -> dict[str, list[dict[str, object]]]:
    arms = ("PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY")
    if type(signals_by_arm) is not dict or set(signals_by_arm) != set(arms):
        raise ContractError("all three frozen arms are required")
    ledgers: dict[str, list[dict[str, object]]] = {}
    seen: set[str] = set()
    for arm in arms:
        ledger = []
        for signal in sorted(signals_by_arm[arm], key=lambda row: _as_utc(row["time_utc"])):
            at = _as_utc(signal["time_utc"])
            decision = _as_utc(signal["availability_utc"])
            direction = signal.get("direction")
            if direction not in {"LONG", "SHORT"} or signal.get("year") != at.year:
                raise ContractError("invalid prospective signal identity")
            features = {
                "atr20": float(signal["atr20"]),
                "range_atr_ratio": float(signal["range_atr_ratio"]),
                "impulse_efficiency": float(signal["impulse_efficiency"]),
                "outer_close_fraction": float(signal["outer_close_fraction"]),
                "confirmation_cross": signal["confirmation_cross"],
                "cost_to_sl_ratio": float(signal["cost_to_sl_ratio"]),
            }
            if arm == "PRIMARY":
                features["activity"] = float(signal["activity"])
            elif arm == "SHIFTED_ACTIVITY":
                shifted_date = signal.get("shifted_source_date")
                if type(shifted_date) is not date:
                    raise ContractError("invalid shifted source date")
                features["shifted_activity"] = float(signal["shifted_activity"])
                features["shifted_source_date"] = shifted_date.isoformat()
            identity = f"{HYPOTHESIS_ID}|{arm}|{_iso_z(at)}|{direction}".encode("ascii")
            signal_id = f"LVOR002-{arm}-{sha256_bytes(identity)[:16]}"
            if signal_id in seen:
                raise ContractError("duplicate prospective signal identity")
            seen.add(signal_id)
            ledger.append(
                {
                    "signal_id": signal_id,
                    "arm": arm,
                    "impulse_start_utc": _iso_z(at),
                    "decision_utc": _iso_z(decision),
                    "direction": direction,
                    "year": at.year,
                    "causal_features": features,
                    "horizon": _serialize_horizon(
                        map_timestamp_horizon(decision, timestamp_index)
                    ),
                }
            )
        ledgers[arm] = ledger
    assert_outcome_blind(ledgers)
    return ledgers


def evaluate_stage0_gates(
    primary_signals: Sequence[Mapping[str, object]],
    *,
    elapsed_weeks: float,
    formation_complete: int,
    formation_scheduled: int,
    horizon_records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    count = len(primary_signals)
    if (
        type(elapsed_weeks) not in {int, float}
        or isinstance(elapsed_weeks, bool)
        or not math.isfinite(float(elapsed_weeks))
        or elapsed_weeks <= 0
        or type(formation_complete) is not int
        or type(formation_scheduled) is not int
        or not 0 <= formation_complete <= formation_scheduled
        or len(horizon_records) != count
    ):
        raise ContractError("invalid Stage-0 gate inputs")
    directions = Counter(str(row.get("direction")) for row in primary_signals)
    years = Counter(row.get("year") for row in primary_signals)
    if set(directions) - {"LONG", "SHORT"} or any(type(year) is not int for year in years):
        raise ContractError("invalid PRIMARY identity")
    ratios = []
    for row in primary_signals:
        value = row.get("cost_to_sl_ratio")
        if type(value) not in {int, float} or isinstance(value, bool) or not math.isfinite(float(value)) or value < 0:
            raise ContractError("invalid cost geometry ratio")
        ratios.append(float(value))
    cadence = count / float(elapsed_weeks)
    long_share = directions["LONG"] / count if count else 0.0
    short_share = directions["SHORT"] / count if count else 0.0
    max_year_share = max(years.values(), default=0) / count if count else 0.0
    formation_ratio = formation_complete / formation_scheduled if formation_scheduled else 0.0
    executable = sum(row.get("source_executable") is True for row in horizon_records)
    horizon_ratio = executable / count if count else 0.0
    median_ratio = median(ratios) if ratios else None
    gates = {
        "cadence_2_to_5_per_week": 2.0 <= cadence <= 5.0,
        "long_share_at_least_0_25": long_share >= 0.25,
        "short_share_at_least_0_25": short_share >= 0.25,
        "no_year_over_0_30": max_year_share <= 0.30,
        "formation_ratio_at_least_0_99": formation_ratio >= 0.99,
        "source_executable_horizon_ratio_at_least_0_99": horizon_ratio >= 0.99,
        "median_cost_to_sl_ratio_at_most_0_25": median_ratio is not None and median_ratio <= 0.25,
        "at_least_20_primary_per_side": directions["LONG"] >= 20 and directions["SHORT"] >= 20,
    }
    return {
        "verdict": "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY" if all(gates.values()) else "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY",
        "gates": gates,
        "metrics": {
            "primary_count": count,
            "cadence_per_elapsed_week": cadence,
            "long_count": directions["LONG"],
            "short_count": directions["SHORT"],
            "long_share": long_share,
            "short_share": short_share,
            "year_counts": {str(year): years[year] for year in sorted(years)},
            "max_year_share": max_year_share,
            "formation_complete": formation_complete,
            "formation_scheduled": formation_scheduled,
            "formation_ratio": formation_ratio,
            "source_executable_horizon_ratio": horizon_ratio,
            "median_cost_to_sl_ratio": median_ratio,
        },
    }


def assert_outcome_blind(value: object) -> None:
    forbidden = (
        "return", "pnl", "profit", "dsr", "post_entry", "trade", "win", "loss",
        "mfe", "mae", "target_hit", "stop_hit",
    )

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
                if any(token in str(key).lower() for token in forbidden):
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
            ordinal for ordinal, raw in enumerate(raw_rows, start=1)
            if sha256_bytes(raw) == reviewed_row_sha256
        ]
        if len(matches) != 1:
            raise ValueError("reviewed row binding")
        index = matches[0]
        row = rows[index - 1]
        if canonical_json(row) + b"\n" != raw_rows[index - 1]:
            raise ContractError("selected registry row is not canonical")
        latest = [
            ordinal for ordinal, item in enumerate(rows, start=1)
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
            or row.get("parent_candidate") != PARENT_HYPOTHESIS_ID
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
            "clock_path": CLOCK_REL,
            "clock_sha256": CLOCK_SHA256,
            "design_m1_manifest_path": M1_MANIFEST_REL,
            "design_m1_manifest_sha256": M1_MANIFEST_SHA256,
            "design_m1_receipt_path": M1_RECEIPT_REL,
            "design_m1_receipt_sha256": M1_RECEIPT_SHA256,
            "design_m1_source_sha256": M1_SOURCE_SHA256,
            "design_h1_manifest_path": H1_MANIFEST_REL,
            "design_h1_manifest_sha256": H1_MANIFEST_SHA256,
            "design_h1_receipt_path": H1_RECEIPT_REL,
            "design_h1_receipt_sha256": H1_RECEIPT_SHA256,
            "design_h1_price_side": "BID",
            "registry_validator_path": REGISTRY_VALIDATOR_REL,
            "registry_validator_sha256": REGISTRY_VALIDATOR_SHA256,
            "registry_schema_path": REGISTRY_SCHEMA_REL,
            "registry_schema_sha256": REGISTRY_SCHEMA_SHA256,
            "parent_terminal_path": PARENT_TERMINAL_REL,
            "parent_terminal_sha256": PARENT_TERMINAL_SHA256,
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
    """Bind real canonical review bytes to HYP002 source, tests and frozen plan."""

    if not _valid_sha(expected_sha256) or sha256_bytes(payload) != expected_sha256:
        raise ContractError("independent review receipt SHA binding mismatch")
    receipt = parse_canonical_object(payload, label="LVOR implementation review receipt")
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


def validate_parent_terminal(payload: bytes) -> dict[str, object]:
    """Require the exact engineering-invalid HYP001 terminal and nothing else."""

    if sha256_bytes(payload) != PARENT_TERMINAL_SHA256:
        raise ContractError("parent terminal SHA binding mismatch")
    terminal = parse_canonical_object(payload, label="HYP001 parent terminal")
    expected = {
        "artifact_hashes": {
            "attempt_started.json": PARENT_ATTEMPT_STARTED_SHA256,
        },
        "attempt_id": "LVOR001-SOURCE-ATTEMPT-001",
        "hypothesis_id": PARENT_HYPOTHESIS_ID,
        "reason": {
            "message": "forbidden outcome field: complete_m15_plus_following_m5",
            "type": "ContractError",
        },
        "reviewed_registry_row_sha256": PARENT_REVIEWED_REGISTRY_ROW_SHA256,
        "schema_version": "lvor_001_attempt_terminal.v1",
        "sealed_permissions": _sealed_permissions(),
        "source_only_counters": _executed_source_only_counters(),
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
    }
    if terminal != expected:
        raise ContractError("parent terminal identity/reason/artifact/counter binding mismatch")
    return terminal


def _load_clock_functions(
    payload: bytes,
) -> tuple[Callable[[datetime], int], Callable[[datetime], datetime]]:
    if sha256_bytes(payload) != CLOCK_SHA256:
        raise ContractError("clock SHA mismatch")
    module = types.ModuleType("_lvor_verified_fivepercent_clock")
    exec(compile(payload, CLOCK_REL, "exec"), module.__dict__)
    offset = getattr(module, "server_offset_hours", None)
    converter = getattr(module, "server_to_utc", None)
    if not callable(offset) or not callable(converter):
        raise ContractError("clock callable contract mismatch")
    return offset, converter


def _decode_parquet(payload: bytes) -> DecodedShard:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        expected_types = (
            pa.timestamp("ns"), pa.timestamp("ns"), pa.int8(), pa.float64(), pa.float64(),
            pa.float64(), pa.float64(), pa.uint64(), pa.int32(), pa.uint64(),
        )
        parquet = pq.ParquetFile(pa.BufferReader(payload))
        physical = []
        for ordinal, field in enumerate(parquet.schema_arrow):
            label = EXPECTED_ARROW_SCHEMA[ordinal][1] if ordinal < len(expected_types) and field.type == expected_types[ordinal] else f"INVALID:{field.type}"
            physical.append((field.name, label, field.nullable))
        rows = parquet.read().to_pylist()
        for row in rows:
            for field in ("time_server", "time_utc"):
                value = row.get(field)
                if type(value) is not datetime and hasattr(value, "to_pydatetime"):
                    row[field] = value.to_pydatetime()
        return DecodedShard(tuple(physical), parquet.num_row_groups, tuple(rows))
    except Exception as exc:
        raise ContractError("Parquet decoder failure") from exc


def _load_public_rows(
    *,
    workspace: Path,
    kind: str,
    root_rel: str,
    entries: Sequence[Mapping[str, object]],
    offset: Callable[[datetime], int],
    converter: Callable[[datetime], datetime],
) -> list[dict[str, object]]:
    root = workspace / root_rel
    result = []
    for entry in entries:
        payload = stable_read_regular(root / Path(str(entry["relative_path"])), root)
        if len(payload) != entry["bytes"] or sha256_bytes(payload) != entry["sha256"]:
            raise ContractError("manifest shard SHA/bytes mismatch")
        rows = validate_decoded_shard(
            _decode_parquet(payload),
            kind=kind,
            day=str(entry["date"]),
            expected_rows=int(entry["rows"]),
            server_offset_hours=offset,
            server_to_utc=converter,
        )
        for row in rows:
            copied = dict(row)
            copied["time_utc"] = row["time_utc"].replace(tzinfo=UTC)
            result.append(copied)
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
                "schema_version": "lvor_002_attempt_started.v1",
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
            raise ContractError("attempt reservation failed after mkdir and terminal persistence failed") from terminal_exc
        raise
    return root


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
    names = (
        "attempt_started.json",
        "lvor_002_source_report.json",
        "lvor_002_source_ledger.jsonl",
        "source_feasibility_receipt.json",
    )
    return {
        name: sha256_bytes(_artifact_bytes(root / name))
        for name in names
        if (root / name).exists()
    }


def _flatten_ledgers(
    report: Mapping[str, object], *, reviewed_row_sha256: str, attempt_started_sha256: str
) -> list[dict[str, object]]:
    ledgers = report.get("signal_ledgers")
    arms = ("PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY")
    if type(ledgers) is not dict or tuple(ledgers) != arms:
        raise ContractError("report does not contain exact three-arm ledgers")
    flattened = []
    for arm in arms:
        rows = ledgers[arm]
        if type(rows) is not list:
            raise ContractError("source ledger arm is malformed")
        for row in rows:
            if type(row) is not dict or row.get("arm") != arm:
                raise ContractError("source ledger row arm mismatch")
            if set(row) & {
                "schema_version", "hypothesis_id", "attempt_id",
                "reviewed_registry_row_sha256", "attempt_started_sha256",
            }:
                raise ContractError("source ledger row collides with durable binding")
            flattened.append(
                {
                    "schema_version": "lvor_002_source_ledger_row.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "reviewed_registry_row_sha256": reviewed_row_sha256,
                    "attempt_started_sha256": attempt_started_sha256,
                    **row,
                }
            )
    assert_outcome_blind(flattened)
    return flattened


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
    _write_new_canonical(root / "lvor_002_source_report.json", enriched)
    flattened = _flatten_ledgers(
        enriched,
        reviewed_row_sha256=reviewed_row_sha256,
        attempt_started_sha256=started_sha,
    )
    _write_new_jsonl(root / "lvor_002_source_ledger.jsonl", flattened)
    first_hashes = _existing_artifact_hashes(root)
    stage0 = enriched.get("stage0")
    verdict = stage0.get("verdict") if type(stage0) is dict else None
    if verdict not in {
        "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY",
        "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY",
    }:
        raise ContractError("source report has invalid Stage-0 verdict")
    terminal_status = (
        "PASS_SOURCE_FEASIBILITY"
        if verdict == "SOURCE_PASS_FUTURE_ECONOMICS_PREREG_ONLY"
        else "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"
    )
    receipt = {
        "schema_version": "lvor_002_source_feasibility_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "stage0_verdict": verdict,
        "terminal_status": terminal_status,
        "artifact_hashes": first_hashes,
        "source_only_counters": _executed_source_only_counters(),
        "sealed_permissions": _sealed_permissions(),
    }
    assert_outcome_blind(receipt)
    _write_new_canonical(root / "source_feasibility_receipt.json", receipt)
    all_hashes = _existing_artifact_hashes(root)
    terminal = {
        "schema_version": "lvor_002_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "status": terminal_status,
        "artifact_hashes": all_hashes,
        "source_only_counters": _executed_source_only_counters(),
        "sealed_permissions": _sealed_permissions(),
    }
    assert_outcome_blind(terminal)
    _write_new_canonical(root / "attempt_terminal.json", terminal)
    return enriched


def _persist_engineering_failure(
    root: Path, reviewed_row_sha256: str, error: Exception
) -> None:
    terminal = root / "attempt_terminal.json"
    if terminal.exists():
        return
    value = {
        "schema_version": "lvor_002_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha256,
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
        "reason": {"type": type(error).__name__, "message": str(error)[:1000]},
        "artifact_hashes": _existing_artifact_hashes(root),
        "source_only_counters": _executed_source_only_counters(),
        "sealed_permissions": _sealed_permissions(),
    }
    assert_outcome_blind(value)
    _write_new_canonical(terminal, value)


def _scan_source(
    m1_rows: Sequence[Mapping[str, object]],
    h1_rows: Sequence[Mapping[str, object]],
    business_dates: Sequence[date],
) -> dict[str, object]:
    m15_bars, m5_bars, quality = build_complete_bars(m1_rows)
    days, date_index, m15_lookup = _prepare_activity_indexes(m15_bars, business_dates)
    m5_by_start = types.MappingProxyType(
        {bar["time_utc"]: bar for bar in m5_bars}
    )
    if len(m5_by_start) != len(m5_bars):
        raise ContractError("duplicate complete M5 start")
    atr_values = wilder_atr20_by_close(h1_rows)
    atr_closes = [item[0] for item in atr_values]
    timestamp_index = build_timestamp_index(
        (_as_utc(row["time_utc"]) for row in m1_rows),
        (_as_utc(bar["time_utc"]) for bar in m5_bars),
    )

    features: list[dict[str, object]] = []
    reasons: Counter[str] = Counter()
    formation_scheduled = max(0, len(days) - 20) * 48
    formation_complete = 0
    for m15 in m15_bars:
        at = _as_utc(m15["time_utc"])
        if not _decision_slot(at):
            continue
        ordinal = date_index.get(at.date())
        if ordinal is None:
            raise ContractError("M15 date is outside manifest business dates")
        confirmation = following_confirmation(m15, m5_by_start)
        if ordinal >= 20 and confirmation is not None:
            formation_complete += 1
        if confirmation is None:
            reasons["FOLLOWING_M5_INCOMPLETE"] += 1
            continue
        decision = _as_utc(confirmation["availability_utc"])
        atr_ordinal = bisect.bisect_right(atr_closes, decision) - 1
        if atr_ordinal < 0:
            reasons["H1_ATR20_UNAVAILABLE"] += 1
            continue
        surface = price_surface(m15, confirmation, atr20=atr_values[atr_ordinal][1])
        if surface is None:
            continue
        activity = _activity_ratio_indexed(m15, days, date_index, m15_lookup)
        shifted = _shifted_activity_indexed(m15, days, date_index, m15_lookup)
        if activity is None:
            reasons["PRIOR20_ACTIVITY_UNAVAILABLE"] += 1
        if shifted is None:
            reasons["SHIFTED_ACTIVITY_UNAVAILABLE"] += 1
        candidate = dict(surface)
        if activity is not None:
            candidate["activity"] = activity
        if shifted is not None:
            candidate["shifted_activity"] = shifted["activity"]
            candidate["shifted_source_date"] = shifted["source_date"]
        features.append(candidate)

    signals = {
        arm: select_daily_signals(features, arm=arm)
        for arm in ("PRIMARY", "PRICE_ONLY", "SHIFTED_ACTIVITY")
    }
    ledgers = build_arm_ledgers(signals, timestamp_index)
    horizons = [row["horizon"] for row in ledgers["PRIMARY"]]
    stage0 = evaluate_stage0_gates(
        signals["PRIMARY"],
        elapsed_weeks=ELAPSED_CALENDAR_WEEKS,
        formation_complete=formation_complete,
        formation_scheduled=formation_scheduled,
        horizon_records=horizons,
    )
    report = {
        "schema_version": "lvor_002_source_feasibility_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "feature_family": FAMILY,
        "evidence_class": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
        "mechanism_status": "PLAUSIBLE_UNVALIDATED_FALSIFICATION_PRIORS",
        "activity_proxy": "BROKER_TICK_VOLUME_NOT_TRANSACTION_VOLUME",
        "source_contract": {
            "design_start": DESIGN_START.isoformat(),
            "design_end": DESIGN_END.isoformat(),
            "elapsed_calendar_weeks": ELAPSED_CALENDAR_WEEKS,
            "m1_manifest_sha256": M1_MANIFEST_SHA256,
            "m1_receipt_sha256": M1_RECEIPT_SHA256,
            "m1_source_sha256": M1_SOURCE_SHA256,
            "h1_manifest_sha256": H1_MANIFEST_SHA256,
            "h1_receipt_sha256": H1_RECEIPT_SHA256,
            "h1_price_side": "BID",
            "manifest_dates": EXPECTED_MANIFEST_DATES,
            "business_decision_dates": EXPECTED_BUSINESS_DECISION_DATES,
            "m1_design_rows": EXPECTED_M1_DESIGN_ROWS,
            "h1_design_rows": EXPECTED_H1_DESIGN_ROWS,
            "m15_m5_quality": quality,
        },
        "arm_counts": {arm: len(rows) for arm, rows in ledgers.items()},
        "signal_ledgers": ledgers,
        "formation_funnel": {
            "scheduled_after_activity_warmup": formation_scheduled,
            "formed_m15_plus_confirm_m5": formation_complete,
            "complete_ratio": formation_complete / formation_scheduled if formation_scheduled else 0.0,
            "ineligibility_reasons": dict(sorted(reasons.items())),
        },
        "horizon_funnel": {
            "primary": len(horizons),
            "source_executable": sum(row["source_executable"] is True for row in horizons),
            "delayed_over_60m": sum(row["delayed_over_60m"] is True for row in horizons),
            "unavailable": sum(row["unavailable"] is True for row in horizons),
            "right_censored": sum(row["right_censored"] is True for row in horizons),
        },
        "stage0": stage0,
        "economics_authorized": False,
        "future_economics_requires_separate_prereg": True,
        "source_pass_is_not_edge_evidence": True,
    }
    assert_outcome_blind(report)
    return report


def _read_and_scan_design(
    workspace: Path,
    offset: Callable[[datetime], int],
    converter: Callable[[datetime], datetime],
) -> dict[str, object]:
    """Open public DESIGN only after caller has durably reserved the attempt."""

    m1_entries = validate_public_metadata(
        kind="M1",
        receipt_payload=stable_read_regular(workspace / M1_RECEIPT_REL, workspace),
        manifest_payload=stable_read_regular(workspace / M1_MANIFEST_REL, workspace),
        expected_receipt_sha256=M1_RECEIPT_SHA256,
        expected_manifest_sha256=M1_MANIFEST_SHA256,
    )
    h1_entries = validate_public_metadata(
        kind="H1",
        receipt_payload=stable_read_regular(workspace / H1_RECEIPT_REL, workspace),
        manifest_payload=stable_read_regular(workspace / H1_MANIFEST_REL, workspace),
        expected_receipt_sha256=H1_RECEIPT_SHA256,
        expected_manifest_sha256=H1_MANIFEST_SHA256,
    )
    validate_matching_manifest_date_sequences(m1_entries, h1_entries)
    m1_rows = _load_public_rows(
        workspace=workspace,
        kind="M1",
        root_rel=M1_ROOT_REL,
        entries=m1_entries,
        offset=offset,
        converter=converter,
    )
    h1_rows = _load_public_rows(
        workspace=workspace,
        kind="H1",
        root_rel=H1_ROOT_REL,
        entries=h1_entries,
        offset=offset,
        converter=converter,
    )
    return _scan_source(m1_rows, h1_rows, weekday_decision_dates(m1_entries))


def execute_probe(*, workspace_root: Path, run_switch: bool) -> dict[str, object]:
    if run_switch is not True:
        raise ContractError("source probe is disarmed; explicit run switch is required")
    if REVIEWED_REGISTRY_ROW_SHA256 is None:
        raise ContractError("source probe is disarmed; reviewed registry-row sentinel is absent")
    if not _valid_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("reviewed registry-row sentinel is invalid")

    workspace = Path(workspace_root).absolute()
    builder_payload = stable_read_regular(workspace / BUILDER_REL, workspace)
    test_payload = stable_read_regular(workspace / TEST_REL, workspace)
    if sha256_bytes(stable_read_regular(workspace / PLAN_REL, workspace)) != PLAN_SHA256:
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
    if (
        validation.get("parent_terminal_path") != PARENT_TERMINAL_REL
        or validation.get("parent_terminal_sha256") != PARENT_TERMINAL_SHA256
    ):
        raise ContractError("registry parent terminal authority is malformed")
    parent_terminal_payload = stable_read_regular(
        workspace / PARENT_TERMINAL_REL, workspace
    )
    validate_parent_terminal(parent_terminal_payload)
    receipt_payload = stable_read_regular(workspace / REVIEW_RECEIPT_REL, workspace)
    validate_review_receipt(
        receipt_payload,
        expected_sha256=validation.get("independent_review_receipt_sha256"),
        builder_payload=builder_payload,
        test_payload=test_payload,
    )
    offset, converter = _load_clock_functions(
        stable_read_regular(workspace / CLOCK_REL, workspace)
    )

    # Reservation and STARTED receipt are durable before any DESIGN metadata.
    root = _reserve_attempt(workspace, REVIEWED_REGISTRY_ROW_SHA256)
    try:
        report = _read_and_scan_design(workspace, offset, converter)
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
    parser.add_argument("--run-reviewed-source-feasibility", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = execute_probe(
        workspace_root=args.workspace_root,
        run_switch=args.run_reviewed_source_feasibility,
    )
    print(canonical_json(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
