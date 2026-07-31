#!/usr/bin/env python3
"""Inert source/cadence probe for HYP-ARUC-EURUSD-M15-002.

Importing and default CLI execution cannot read real DESIGN data. A later real
read requires an explicit switch and an exact latest canonical registry row
whose raw SHA replaces the ``REVIEWED_REGISTRY_ROW_SHA256`` sentinel. The
computational surface is intentionally usable with synthetic rows.
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
from typing import Any, Callable, Iterable, Mapping, NamedTuple, Sequence


HYPOTHESIS_ID = "HYP-ARUC-EURUSD-M15-002"
PARENT_HYPOTHESIS_ID = "HYP-ARUC-EURUSD-M15-001"
EA_NAME = "EA_ActivityResponseContinuation"
FAMILY = "activity-response-underreaction-continuation"
ATTEMPT_ID = "ARUC002-SOURCE-ATTEMPT-001"

PLAN_REL = (
    "03. EA Developer/EA_ActivityResponseContinuation/research/"
    "HYP-ARUC-EURUSD-M15-002_SOURCE_FEASIBILITY_PLAN.md"
)
PLAN_SHA256 = "D1381633DD7DE6EA84CDFFA54E867338C2A1FC7D0148F89C22FEE95CF3B373CF"
BUILDER_REL = (
    "03. EA Developer/EA_ActivityResponseContinuation/research/"
    "build_aruc_002_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_ActivityResponseContinuation/research/tests/"
    "test_build_aruc_002_source.py"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_ActivityResponseContinuation/research/"
    "evidence/HYP-ARUC-EURUSD-M15-002_SOURCE_FEASIBILITY_ATTEMPTS/"
    f"{ATTEMPT_ID}"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_ActivityResponseContinuation/research/"
    "HYP-ARUC-EURUSD-M15-002_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REVIEW_RECEIPT_SCHEMA = "aruc_002_source_implementation_review_receipt.v1"
PROBE_STATUS = "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN"
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

# Independent review must replace this exact sentinel before any real read.
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
H1_RECEIPT_FIELDS = {
    "collection_id",
    "design_dates",
    "design_manifest_sha256",
    "raw_source_opens",
    "research_holdout_opened",
    "research_validation_opened",
    "schema_version",
    "source_attempt_id",
    "source_rows",
    "unselected_shard_opens",
    "verdict",
}


class ContractError(RuntimeError):
    """A fail-closed contract violation."""


class DecodedShard(NamedTuple):
    schema: tuple[tuple[str, str, bool], ...]
    row_groups: int
    rows: tuple[dict[str, object], ...]


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
    """Parse strict JSONL content without rewriting legitimate historical formatting."""

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


class ImmutableBytesFile(NamedTuple):
    """Minimal immutable path adapter consumed by the canonical registry validator."""

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


def validate_registry_snapshot(
    *,
    registry_payload: bytes,
    validator_payload: bytes,
    schema_payload: bytes,
    validator_path: Path,
) -> None:
    """Run the exact hash-bound canonical validator over immutable input adapters."""

    if sha256_bytes(validator_payload) != REGISTRY_VALIDATOR_SHA256:
        raise ContractError("canonical registry validator SHA mismatch")
    if sha256_bytes(schema_payload) != REGISTRY_SCHEMA_SHA256:
        raise ContractError("canonical registry schema SHA mismatch")
    try:
        module = types.ModuleType("_aruc_verified_candidate_registry_validator")
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
        return os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(root)))) == os.path.normcase(str(root))
    except ValueError:
        return False


def stable_read_regular(path_value: Path | str, allowed_root_value: Path | str) -> bytes:
    """Read one single-link regular file while pinning every directory identity."""

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
    kind: str,
    receipt_payload: bytes,
    manifest_payload: bytes,
    expected_receipt_sha256: str,
    expected_manifest_sha256: str,
    expected_dates: Sequence[str] | None = None,
) -> list[dict[str, object]]:
    """Validate exact public metadata and return only the frozen DESIGN date rows."""

    if kind not in {"M1", "H1"}:
        raise ContractError("unknown public metadata kind")
    if (
        not _valid_sha(expected_receipt_sha256)
        or not _valid_sha(expected_manifest_sha256)
        or sha256_bytes(receipt_payload) != expected_receipt_sha256
        or sha256_bytes(manifest_payload) != expected_manifest_sha256
    ):
        raise ContractError("public metadata hash mismatch")
    receipt = parse_canonical_object(receipt_payload, label=f"{kind} receipt")
    all_rows = parse_canonical_jsonl(manifest_payload, label=f"{kind} manifest")
    if receipt.get("design_manifest_sha256") != sha256_bytes(manifest_payload):
        raise ContractError("receipt does not bind exact manifest")
    if receipt.get("research_validation_opened") is not False or receipt.get("research_holdout_opened") is not False:
        raise ContractError("receipt did not keep sealed branches closed")
    if type(receipt.get("design_dates")) is not int or receipt["design_dates"] != len(all_rows):
        raise ContractError("receipt design-date count mismatch")

    if kind == "M1":
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
        row_schema = None
        leaf = "m1.parquet"
    else:
        if (
            set(receipt) != H1_RECEIPT_FIELDS
            or receipt.get("collection_id") != H1_COLLECTION_ID
            or receipt.get("schema_version") != H1_RECEIPT_SCHEMA
            or receipt.get("raw_source_opens") != 1
            or receipt.get("unselected_shard_opens") != 0
            or receipt.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
            or type(receipt.get("source_rows")) is not int
        ):
            raise ContractError("H1 receipt contract mismatch")
        manifest_fields = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
        row_schema = H1_MANIFEST_ROW_SCHEMA
        leaf = "h1.parquet"

    previous: str | None = None
    for row in all_rows:
        day = _canonical_day(row.get("date"))
        if (
            set(row) != manifest_fields
            or (previous is not None and day <= previous)
            or row.get("relative_path") != f"public/DESIGN/{day}/{leaf}"
            or type(row.get("bytes")) is not int
            or row["bytes"] <= 0
            or type(row.get("rows")) is not int
            or row["rows"] <= 0
            or not _valid_sha(row.get("sha256"))
            or (row_schema is not None and row.get("schema_version") != row_schema)
        ):
            raise ContractError("manifest path/schema/hash/bytes/rows contract mismatch")
        previous = day
    manifest_row_total = sum(int(row["rows"]) for row in all_rows)
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
    if expected_dates is not None and selected_days != tuple(expected_dates):
        raise ContractError("selected DESIGN dates mismatch")
    if kind == "M1":
        if (
            manifest_row_total != EXPECTED_M1_DESIGN_ROWS
            or receipt.get("design_rows") != EXPECTED_M1_DESIGN_ROWS
        ):
            raise ContractError("M1 DESIGN row-count contract mismatch")
    else:
        if manifest_row_total != EXPECTED_H1_DESIGN_ROWS:
            raise ContractError("H1 DESIGN row-count contract mismatch")
        if receipt.get("source_rows") != EXPECTED_H1_RAW_SOURCE_ROWS:
            raise ContractError("H1 raw-source row-count contract mismatch")
    return all_rows


def validate_matching_manifest_date_sequences(
    m1_entries: Sequence[Mapping[str, object]],
    h1_entries: Sequence[Mapping[str, object]],
) -> tuple[str, ...]:
    m1_dates = tuple(_canonical_day(row.get("date")) for row in m1_entries)
    h1_dates = tuple(_canonical_day(row.get("date")) for row in h1_entries)
    if m1_dates != h1_dates:
        raise ContractError("M1/H1 manifest date sequence mismatch")
    return m1_dates


def weekday_decision_dates(entries: Sequence[Mapping[str, object]]) -> tuple[date, ...]:
    manifest_dates = tuple(date.fromisoformat(_canonical_day(row.get("date"))) for row in entries)
    selected = tuple(day for day in manifest_dates if day.weekday() < 5)
    if len(manifest_dates) == EXPECTED_MANIFEST_DATES and len(selected) != EXPECTED_BUSINESS_DECISION_DATES:
        raise ContractError("weekday decision-date count mismatch")
    return _business_date_tuple(selected)


def _finite_price(value: object) -> float:
    if type(value) not in {float, int} or isinstance(value, bool):
        raise ContractError("invalid OHLC type")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ContractError("invalid OHLC value")
    return number


def validate_decoded_shard(
    decoded: DecodedShard,
    *,
    kind: str,
    day: str,
    expected_rows: int,
    server_offset_hours: Callable[[datetime], int],
    server_to_utc: Callable[[datetime], datetime],
) -> tuple[dict[str, object], ...]:
    """Enforce producer schema, one row group and the audited server clock."""

    try:
        if (
            kind not in {"M1", "H1"}
            or type(decoded) is not DecodedShard
            or decoded.schema != EXPECTED_ARROW_SCHEMA
            or decoded.row_groups != 1
            or type(expected_rows) is not int
            or expected_rows <= 0
            or len(decoded.rows) != expected_rows
        ):
            raise ValueError
        expected_keys = {field[0] for field in EXPECTED_ARROW_SCHEMA}
        previous: datetime | None = None
        for row in decoded.rows:
            if type(row) is not dict or set(row) != expected_keys or any(value is None for value in row.values()):
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
                or not -128 <= offset <= 127
                or utc_value.second
                or utc_value.microsecond
                or server.second
                or server.microsecond
                or utc_value.date().isoformat() != day
                or server - utc_value != timedelta(hours=offset)
                or server_offset_hours(server) != offset
                or server_to_utc(server) != utc_value
                or (kind == "H1" and utc_value.minute != 0)
                or (previous is not None and utc_value <= previous)
            ):
                raise ValueError
            previous = utc_value
            open_price, high, low, close = (_finite_price(row[name]) for name in ("open", "high", "low", "close"))
            if not (low <= open_price <= high and low <= close <= high):
                raise ValueError
            for name, maximum in (("tick_volume", 2**64 - 1), ("spread", 2**31 - 1), ("real_volume", 2**64 - 1)):
                value = row[name]
                if type(value) is not int or isinstance(value, bool) or not 0 <= value <= maximum:
                    raise ValueError
        return decoded.rows
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("decoded shard schema/row-group/timezone/clock contract mismatch") from exc


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


def _m15_floor(at: datetime) -> datetime:
    return at.replace(minute=at.minute - at.minute % 15, second=0, microsecond=0)


def _sign(value: float | int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def build_complete_m15(rows: Iterable[Mapping[str, object]]) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Aggregate exact M15 bins and compute Q without losing the prior close."""

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
    times = [item[0] for item in ordered]
    if times != sorted(times) or len(times) != len(set(times)):
        raise ContractError("M1 timestamps are duplicated or unordered")
    lookup = {at: row for at, row in ordered}
    groups: dict[datetime, list[tuple[datetime, Mapping[str, object]]]] = defaultdict(list)
    for at, row in ordered:
        groups[_m15_floor(at)].append((at, row))

    complete: list[dict[str, object]] = []
    incomplete = 0
    for bucket in sorted(groups):
        group = groups[bucket]
        expected = [bucket + timedelta(minutes=index) for index in range(15)]
        observed = [item[0] for item in group]
        previous = lookup.get(bucket - timedelta(minutes=1))
        if len(group) != 15 or observed != expected or previous is None:
            incomplete += 1
            continue
        previous_close = _ohlc(previous)[3]
        signs: list[int] = []
        volumes: list[int] = []
        q = 0
        for _, row in group:
            close = _ohlc(row)[3]
            volume = _tick_volume(row)
            direction = _sign(close - previous_close)
            signs.append(direction)
            volumes.append(volume)
            q += direction * volume
            previous_close = close
        ohlc_values = [_ohlc(row) for _, row in group]
        complete.append(
            {
                "time_utc": bucket,
                "availability_utc": bucket + timedelta(minutes=15),
                "date": bucket.date(),
                "slot": (bucket.hour, bucket.minute),
                "open": ohlc_values[0][0],
                "high": max(item[1] for item in ohlc_values),
                "low": min(item[2] for item in ohlc_values),
                "close": ohlc_values[-1][3],
                "q": q,
                "sum_tv": sum(volumes),
                "price_signs": tuple(signs),
                "tick_volumes": tuple(volumes),
            }
        )
    return complete, {
        "observed_bins": len(groups),
        "complete_bins": len(complete),
        "incomplete_bins": incomplete,
    }


def _bar_index(
    bars: Sequence[Mapping[str, object]],
) -> dict[tuple[date, tuple[int, int]], Mapping[str, object]]:
    result: dict[tuple[date, tuple[int, int]], Mapping[str, object]] = {}
    for bar in bars:
        key = (bar.get("date"), bar.get("slot"))
        if type(key[0]) is not date or type(key[1]) is not tuple or key in result:
            raise ContractError("activity bars have invalid or duplicate date/slot")
        result[key] = bar
    return result


def _business_date_tuple(values: Sequence[date]) -> tuple[date, ...]:
    dates = tuple(values)
    if (
        any(type(day) is not date or day.weekday() >= 5 for day in dates)
        or len(dates) != len(set(dates))
        or dates != tuple(sorted(dates))
    ):
        raise ContractError("invalid business-date contract")
    return dates


def activity_ratio_for(
    current: Mapping[str, object],
    bars: Sequence[Mapping[str, object]],
    business_dates: Sequence[date],
    *,
    lookback: int = 20,
) -> float | None:
    dates = _business_date_tuple(business_dates)
    if type(lookback) is not int or lookback <= 0:
        raise ContractError("invalid business-date contract")
    current_date = current.get("date")
    slot = current.get("slot")
    try:
        index = dates.index(current_date)
    except ValueError:
        return None
    if index < lookback:
        return None
    mapping = _bar_index(bars)
    values: list[int] = []
    for prior_date in dates[index - lookback : index]:
        prior = mapping.get((prior_date, slot))
        if prior is None or type(prior.get("sum_tv")) is not int or prior["sum_tv"] < 0:
            return None
        values.append(int(prior["sum_tv"]))
    denominator = float(median(values))
    numerator = current.get("sum_tv")
    if type(numerator) is not int or numerator < 0 or denominator <= 0:
        return None
    return numerator / denominator


def shifted_tick_features(
    current: Mapping[str, object],
    bars: Sequence[Mapping[str, object]],
    business_dates: Sequence[date],
    *,
    shift_dates: int = 5,
    lookback: int = 20,
) -> dict[str, object] | None:
    dates = _business_date_tuple(business_dates)
    current_date = current.get("date")
    slot = current.get("slot")
    if type(shift_dates) is not int or shift_dates <= 0:
        raise ContractError("invalid shifted-date contract")
    try:
        current_index = dates.index(current_date)
    except ValueError:
        return None
    source_index = current_index - shift_dates
    if source_index < lookback:
        return None
    mapping = _bar_index(bars)
    source = mapping.get((dates[source_index], slot))
    if source is None:
        return None
    signs = current.get("price_signs")
    volumes = source.get("tick_volumes")
    if (
        type(signs) not in {tuple, list}
        or type(volumes) not in {tuple, list}
        or len(signs) != 15
        or len(volumes) != 15
        or any(type(value) is not int or isinstance(value, bool) or value not in {-1, 0, 1} for value in signs)
        or any(type(value) is not int or isinstance(value, bool) or value < 0 for value in volumes)
    ):
        return None
    shifted = dict(source)
    activity = activity_ratio_for(shifted, bars, dates, lookback=lookback)
    if activity is None:
        return None
    return {
        "source_date": dates[source_index],
        "q": sum(int(sign) * int(volume) for sign, volume in zip(signs, volumes)),
        "sum_tv": sum(int(value) for value in volumes),
        "activity": activity,
    }


def _true_range(current: Mapping[str, object], previous_close: float | None) -> float:
    _, high, low, _ = _ohlc(current)
    return high - low if previous_close is None else max(high - low, abs(high - previous_close), abs(low - previous_close))


def wilder_atr20_by_close(h1_bars: Sequence[Mapping[str, object]]) -> list[tuple[datetime, float]]:
    ordered = sorted(h1_bars, key=lambda row: _as_utc(row["time_utc"]))
    times = [_as_utc(row["time_utc"]) for row in ordered]
    if times != [_as_utc(row["time_utc"]) for row in h1_bars] or len(times) != len(set(times)):
        raise ContractError("H1 bars are duplicated or unordered")
    true_ranges: list[float] = []
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
    for index in range(20, len(true_ranges)):
        atr = (19.0 * atr + true_ranges[index]) / 20.0
        if not math.isfinite(atr) or atr <= 0:
            raise ContractError("invalid Wilder ATR20")
        result.append((times[index] + timedelta(hours=1), atr))
    return result


def latest_wilder_atr20(h1_bars: Sequence[Mapping[str, object]], availability: datetime) -> float | None:
    decision = _as_utc(availability)
    values = wilder_atr20_by_close(h1_bars)
    ends = [item[0] for item in values]
    index = bisect.bisect_right(ends, decision) - 1
    return None if index < 0 else values[index][1]


def _decision_slot(at: datetime) -> bool:
    return at.weekday() < 5 and time(7, 0) <= at.time().replace(tzinfo=None) < time(15, 0) and at.minute % 15 == 0


def select_daily_signals(candidates: Sequence[Mapping[str, object]], *, arm: str) -> list[dict[str, object]]:
    if arm not in {"PRIMARY", "PRICE_ONLY", "SHIFTED_TICKS"}:
        raise ContractError("unknown signal arm")
    selected: list[dict[str, object]] = []
    consumed: set[date] = set()
    ordered = sorted(candidates, key=lambda row: _as_utc(row["time_utc"]))
    for candidate in ordered:
        at = _as_utc(candidate["time_utc"])
        availability = _as_utc(candidate["availability_utc"])
        if availability != at + timedelta(minutes=15) or not _decision_slot(at) or at.date() in consumed:
            continue
        try:
            response = float(candidate["r"])
            atr = float(candidate["atr20"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(response) or not math.isfinite(atr) or atr <= 0 or not 0.15 <= abs(response) <= 0.50:
            continue
        direction = _sign(response)
        if arm != "PRICE_ONLY":
            prefix = "" if arm == "PRIMARY" else "shifted_"
            try:
                activity = float(candidate[f"{prefix}a"])
                q = int(candidate[f"{prefix}q"])
                sum_tv = int(candidate[f"{prefix}sum_tv"])
            except (KeyError, TypeError, ValueError):
                continue
            if (
                not math.isfinite(activity)
                or activity < 1.50
                or sum_tv <= 0
                or abs(q) / sum_tv < 0.55
                or _sign(q) == 0
                or _sign(q) != _sign(response)
            ):
                continue
            direction = _sign(q)
        row = dict(candidate)
        row["arm"] = arm
        row["direction"] = "LONG" if direction > 0 else "SHORT"
        row["year"] = at.year
        row["cost_to_sl_ratio"] = 1.50 / (atr / PIP)
        selected.append(row)
        consumed.add(at.date())
    return selected


def map_observed_horizon(
    availability: datetime,
    observed_complete_m15_opens: Sequence[datetime],
) -> dict[str, object]:
    decision = _as_utc(availability)
    if any(type(value) is not datetime for value in observed_complete_m15_opens):
        raise ContractError("horizon accepts timestamps only")
    observed = [_as_utc(value) for value in observed_complete_m15_opens]
    if observed != sorted(observed) or len(observed) != len(set(observed)):
        raise ContractError("observed horizon timestamps are duplicated or unordered")
    index = bisect.bisect_left(observed, decision)
    if index >= len(observed):
        return {
            "entry_open_utc": None,
            "entry_delay_minutes": None,
            "exit_availability_utc": None,
            "observed_horizon_bars": 0,
            "delayed_over_60m": False,
            "unavailable": True,
            "right_censored": False,
            "source_executable": False,
            "reason": "NO_ENTRY_OBSERVED",
        }
    entry = observed[index]
    delay = (entry - decision).total_seconds() / 60.0
    horizon = observed[index : index + 4]
    delayed = delay > 60.0
    right_censored = len(horizon) < 4
    source_executable = not delayed and not right_censored
    reason = "SOURCE_EXECUTABLE" if source_executable else "RIGHT_CENSORED_LT4" if right_censored else "ENTRY_DELAY_GT_60M"
    return {
        "entry_open_utc": entry,
        "entry_delay_minutes": delay,
        "exit_availability_utc": horizon[-1] + timedelta(minutes=15) if len(horizon) == 4 else None,
        "observed_horizon_bars": len(horizon),
        "delayed_over_60m": delayed,
        "unavailable": False,
        "right_censored": right_censored,
        "source_executable": source_executable,
        "reason": reason,
    }


def horizon_funnel(records: Sequence[Mapping[str, object]]) -> dict[str, int]:
    return {
        "primary": len(records),
        "source_executable": sum(record.get("source_executable") is True for record in records),
        "delayed_over_60m": sum(record.get("delayed_over_60m") is True for record in records),
        "unavailable": sum(record.get("unavailable") is True for record in records),
        "right_censored": sum(record.get("right_censored") is True for record in records),
    }


def _iso_z(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _finite_feature(value: object, *, label: str) -> float:
    if type(value) not in {int, float} or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ContractError(f"invalid ledger feature: {label}")
    return float(value)


def _serialize_horizon(value: Mapping[str, object]) -> dict[str, object]:
    expected = {
        "entry_open_utc",
        "entry_delay_minutes",
        "exit_availability_utc",
        "observed_horizon_bars",
        "delayed_over_60m",
        "unavailable",
        "right_censored",
        "source_executable",
        "reason",
    }
    if set(value) != expected:
        raise ContractError("horizon mapping shape mismatch")
    result = dict(value)
    for key in ("entry_open_utc", "exit_availability_utc"):
        timestamp = result[key]
        if timestamp is not None:
            result[key] = _iso_z(timestamp)
    return result


def build_arm_ledgers(
    signals_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
    observed_complete_m15_opens: Sequence[datetime],
) -> dict[str, list[dict[str, object]]]:
    """Freeze deterministic, timestamp-only prospective selections for all arms."""

    arms = ("PRIMARY", "PRICE_ONLY", "SHIFTED_TICKS")
    if type(signals_by_arm) is not dict or set(signals_by_arm) != set(arms):
        raise ContractError("all three frozen arms are required")
    observed = tuple(observed_complete_m15_opens)
    # Validate once before any arm is serialized.
    if observed:
        map_observed_horizon(observed[0], observed)
    ledgers: dict[str, list[dict[str, object]]] = {}
    seen_ids: set[str] = set()
    for arm in arms:
        ledger: list[dict[str, object]] = []
        ordered = sorted(signals_by_arm[arm], key=lambda row: _as_utc(row["time_utc"]))
        for signal in ordered:
            decision = _as_utc(signal["time_utc"])
            availability = _as_utc(signal["availability_utc"])
            direction = signal.get("direction")
            year = signal.get("year")
            if (
                availability != decision + timedelta(minutes=15)
                or direction not in {"LONG", "SHORT"}
                or type(year) is not int
                or isinstance(year, bool)
                or year != decision.year
            ):
                raise ContractError("invalid prospective signal identity")
            atr = _finite_feature(signal.get("atr20"), label="atr20")
            response = _finite_feature(signal.get("r"), label="r")
            cost_ratio = _finite_feature(signal.get("cost_to_sl_ratio"), label="cost_to_sl_ratio")
            if atr <= 0 or cost_ratio < 0:
                raise ContractError("invalid prospective stop geometry")
            features: dict[str, object] = {"r": response, "atr20": atr, "cost_to_sl_ratio": cost_ratio}
            if arm != "PRICE_ONLY":
                prefix = "" if arm == "PRIMARY" else "shifted_"
                activity = _finite_feature(signal.get(f"{prefix}a"), label=f"{prefix}a")
                q = signal.get(f"{prefix}q")
                sum_tv = signal.get(f"{prefix}sum_tv")
                if (
                    type(q) is not int
                    or isinstance(q, bool)
                    or type(sum_tv) is not int
                    or isinstance(sum_tv, bool)
                    or sum_tv <= 0
                ):
                    raise ContractError("invalid prospective activity features")
                if arm == "PRIMARY":
                    features = {
                        "a": activity,
                        "q": q,
                        "sum_tv": sum_tv,
                        "r": response,
                        "atr20": atr,
                        "cost_to_sl_ratio": cost_ratio,
                    }
                else:
                    source_date = signal.get("shifted_source_date")
                    if type(source_date) is not date:
                        raise ContractError("invalid shifted source date")
                    features = {
                        "shifted_a": activity,
                        "shifted_q": q,
                        "shifted_sum_tv": sum_tv,
                        "shifted_source_date": source_date.isoformat(),
                        "r": response,
                        "atr20": atr,
                        "cost_to_sl_ratio": cost_ratio,
                    }
            identity = f"{HYPOTHESIS_ID}|{arm}|{_iso_z(decision)}|{direction}".encode("ascii")
            signal_id = f"ARUC002-{arm}-{sha256_bytes(identity)[:16]}"
            if signal_id in seen_ids:
                raise ContractError("duplicate prospective signal identity")
            seen_ids.add(signal_id)
            ledger.append(
                {
                    "signal_id": signal_id,
                    "arm": arm,
                    "decision_utc": _iso_z(decision),
                    "availability_utc": _iso_z(availability),
                    "direction": direction,
                    "year": year,
                    "causal_features": features,
                    "horizon": _serialize_horizon(
                        map_observed_horizon(availability, observed)
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
        not math.isfinite(float(elapsed_weeks))
        or elapsed_weeks <= 0
        or type(formation_complete) is not int
        or type(formation_scheduled) is not int
        or not 0 <= formation_complete <= formation_scheduled
        or len(horizon_records) != count
    ):
        raise ContractError("invalid Stage-0 gate inputs")
    directions = Counter(str(row.get("direction")) for row in primary_signals)
    if set(directions) - {"LONG", "SHORT"}:
        raise ContractError("invalid PRIMARY direction")
    years = Counter(row.get("year") for row in primary_signals)
    if any(type(year) is not int for year in years):
        raise ContractError("invalid PRIMARY year")
    ratios: list[float] = []
    for row in primary_signals:
        value = row.get("cost_to_sl_ratio")
        if type(value) not in {int, float} or isinstance(value, bool) or not math.isfinite(float(value)) or value < 0:
            raise ContractError("invalid cost geometry ratio")
        ratios.append(float(value))
    cadence = count / elapsed_weeks
    long_share = directions["LONG"] / count if count else 0.0
    short_share = directions["SHORT"] / count if count else 0.0
    max_year_share = max(years.values(), default=0) / count if count else 0.0
    formation_ratio = formation_complete / formation_scheduled if formation_scheduled else 0.0
    executable = sum(record.get("source_executable") is True for record in horizon_records)
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
    forbidden = ("return", "pnl", "profit", "dsr", "post_entry", "trade", "mfe", "mae", "target_hit", "stop_hit")

    def visit(item: object) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                lowered = str(key).lower()
                if any(token in lowered for token in forbidden):
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
    """Require the sentinel-selected row to be the exact latest authority for this child."""

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
        if (
            set(metrics) != set(SOURCE_ONLY_ZERO_METRICS)
            or any(
                type(metrics[key]) is not type(expected) or metrics[key] != expected
                for key, expected in SOURCE_ONLY_ZERO_METRICS.items()
            )
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


def _load_clock_functions(payload: bytes) -> tuple[Callable[[datetime], int], Callable[[datetime], datetime]]:
    if sha256_bytes(payload) != CLOCK_SHA256:
        raise ContractError("clock SHA mismatch")
    module = types.ModuleType("_aruc_verified_fivepercent_clock")
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
        physical: list[tuple[str, str, bool]] = []
        for index, field in enumerate(parquet.schema_arrow):
            label = EXPECTED_ARROW_SCHEMA[index][1] if index < len(expected_types) and field.type == expected_types[index] else f"INVALID:{field.type}"
            physical.append((field.name, label, field.nullable))
        rows = parquet.read().to_pylist()
        for row in rows:
            for field in ("time_server", "time_utc"):
                value = row.get(field)
                if type(value) is not datetime and hasattr(value, "to_pydatetime"):
                    row[field] = value.to_pydatetime()
        return DecodedShard(tuple(physical), parquet.num_row_groups, tuple(rows))
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
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
    result: list[dict[str, object]] = []
    for entry in entries:
        relative = Path(str(entry["relative_path"]))
        payload = stable_read_regular(root / relative, root)
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


def _scan_source(m1_rows: Sequence[Mapping[str, object]], h1_rows: Sequence[Mapping[str, object]], business_dates: Sequence[date]) -> dict[str, object]:
    bars, quality = build_complete_m15(m1_rows)
    atr_values = wilder_atr20_by_close(h1_rows)
    atr_ends = [item[0] for item in atr_values]
    features: list[dict[str, object]] = []
    reasons: Counter[str] = Counter()
    date_index = {day: index for index, day in enumerate(business_dates)}
    formation_scheduled = max(0, len(business_dates) - 20) * 32
    formation_complete = 0
    for bar in bars:
        at = _as_utc(bar["time_utc"])
        if not _decision_slot(at):
            continue
        index = date_index.get(at.date())
        if index is None:
            raise ContractError("M15 bar date is outside manifest business dates")
        if index >= 20:
            formation_complete += 1
        atr_index = bisect.bisect_right(atr_ends, bar["availability_utc"]) - 1
        atr = atr_values[atr_index][1] if atr_index >= 0 else None
        if atr is None:
            reasons["H1_ATR20_UNAVAILABLE"] += 1
            continue
        activity = activity_ratio_for(bar, bars, business_dates, lookback=20)
        if activity is None:
            reasons["PRIOR20_ACTIVITY_UNAVAILABLE"] += 1
        shifted = shifted_tick_features(bar, bars, business_dates, shift_dates=5, lookback=20)
        if shifted is None:
            reasons["SHIFTED_HISTORY_UNAVAILABLE"] += 1
        open_price, _, _, close = _ohlc(bar)
        candidate = {
            **bar,
            "atr20": atr,
            "r": (close - open_price) / atr,
        }
        if activity is not None:
            candidate["a"] = activity
        if shifted is not None:
            candidate.update(
                {
                    "shifted_a": shifted["activity"],
                    "shifted_q": shifted["q"],
                    "shifted_sum_tv": shifted["sum_tv"],
                    "shifted_source_date": shifted["source_date"],
                }
            )
        features.append(candidate)
    primary = select_daily_signals(features, arm="PRIMARY")
    price_only = select_daily_signals(features, arm="PRICE_ONLY")
    shifted = select_daily_signals(features, arm="SHIFTED_TICKS")
    observed = [bar["time_utc"] for bar in bars]
    ledgers = build_arm_ledgers(
        {"PRIMARY": primary, "PRICE_ONLY": price_only, "SHIFTED_TICKS": shifted},
        observed,
    )
    horizons = [row["horizon"] for row in ledgers["PRIMARY"]]
    gate_report = evaluate_stage0_gates(
        primary,
        elapsed_weeks=ELAPSED_CALENDAR_WEEKS,
        formation_complete=formation_complete,
        formation_scheduled=formation_scheduled,
        horizon_records=horizons,
    )
    report = {
        "schema_version": "aruc_002_source_feasibility_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "feature_family": FAMILY,
        "evidence_class": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
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
            "sunday_history_dates": EXPECTED_SUNDAY_DATES,
            "m1_design_rows": EXPECTED_M1_DESIGN_ROWS,
            "h1_design_rows": EXPECTED_H1_DESIGN_ROWS,
            "h1_raw_source_rows": EXPECTED_H1_RAW_SOURCE_ROWS,
            "m15_quality": quality,
        },
        "arm_counts": {
            arm: len(rows) for arm, rows in ledgers.items()
        },
        "signal_ledgers": ledgers,
        "formation_funnel": {
            "scheduled_after_warmup": formation_scheduled,
            "complete_after_warmup": formation_complete,
            "complete_ratio": formation_complete / formation_scheduled if formation_scheduled else 0.0,
            "ineligibility_reasons": dict(sorted(reasons.items())),
        },
        "horizon_funnel": horizon_funnel(horizons),
        "stage0": gate_report,
        "economics_authorized": False,
        "future_economics_requires_separate_prereg": True,
    }
    assert_outcome_blind(report)
    return report


def execute_probe(*, workspace_root: Path, run_switch: bool) -> dict[str, object]:
    """Execute only after disarm checks and all authority bindings pass."""

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
    registry_validator_payload = stable_read_regular(workspace / REGISTRY_VALIDATOR_REL, workspace)
    registry_schema_payload = stable_read_regular(workspace / REGISTRY_SCHEMA_REL, workspace)
    validate_registry_snapshot(
        registry_payload=registry_payload,
        validator_payload=registry_validator_payload,
        schema_payload=registry_schema_payload,
        validator_path=workspace / REGISTRY_VALIDATOR_REL,
    )
    validate_registry_authority(
        registry_payload,
        REVIEWED_REGISTRY_ROW_SHA256,
        builder_payload=builder_payload,
        test_payload=test_payload,
    )
    clock_payload = stable_read_regular(workspace / CLOCK_REL, workspace)
    offset, converter = _load_clock_functions(clock_payload)

    # No DESIGN receipt, manifest or shard is opened before the authority above.
    m1_receipt = stable_read_regular(workspace / M1_RECEIPT_REL, workspace)
    m1_manifest = stable_read_regular(workspace / M1_MANIFEST_REL, workspace)
    h1_receipt = stable_read_regular(workspace / H1_RECEIPT_REL, workspace)
    h1_manifest = stable_read_regular(workspace / H1_MANIFEST_REL, workspace)
    m1_entries = validate_public_metadata(
        kind="M1",
        receipt_payload=m1_receipt,
        manifest_payload=m1_manifest,
        expected_receipt_sha256=M1_RECEIPT_SHA256,
        expected_manifest_sha256=M1_MANIFEST_SHA256,
    )
    h1_entries = validate_public_metadata(
        kind="H1",
        receipt_payload=h1_receipt,
        manifest_payload=h1_manifest,
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
    business_dates = weekday_decision_dates(m1_entries)
    return _scan_source(m1_rows, h1_rows, business_dates)


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
