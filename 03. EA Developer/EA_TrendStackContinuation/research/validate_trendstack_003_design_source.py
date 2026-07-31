"""Independent, fail-closed validator for the published HYP-003 DESIGN tree."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import pyarrow as pa
import pyarrow.parquet as pq


PUBLIC_ERROR = "INVALID_DESIGN_VALIDATION"
READY_VERDICT = "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
PENDING_VERDICT = "PENDING_INDEPENDENT_VALIDATION"
PENDING_TREE_SCHEMA = "trendstack_003_pending_tree.v1"
DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
PROJECTION_SCHEMA = "trendstack_003_design_projection_row.v1"
PARENT_SCHEMA = "trendstack_002_stage0_eligibility_ledger_row.v1"
PARENT_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
_HEX = frozenset("0123456789ABCDEF")
_BASE_FILES = {
    "design_request_plan.jsonl",
    "design_request_plan_receipt.json",
    "design_stage0_projection.jsonl",
    "design_stage0_projection_receipt.json",
    "design_m1_manifest.jsonl",
    "design_m1_source_receipt.json",
    "design_source_access_trace.jsonl",
    "design_source_reconciliation.json",
}
_REQUEST_FIELDS = {"date", "end_utc", "parent_opportunity_id", "request_id", "schema_version", "start_utc"}
_TRACE_FIELDS = {"date", "input_day_sha256", "output_sha256", "request_index", "rows", "schema_version"}
_PARENT_FIELDS = {
    "challenger_stack_direction",
    "challenger_stack_eligible",
    "control_m252_only_direction",
    "control_m252_only_eligible",
    "control_m6_only_direction",
    "control_m6_only_eligible",
    "exclusion_reason",
    "feature_complete",
    "hypothesis_id",
    "max_source_time_utc",
    "negative_disagree_direction",
    "negative_disagree_eligible",
    "next_prefix_sha256",
    "opportunity_id",
    "packet_file_sha256",
    "packet_path",
    "packet_payload_sha256",
    "prior_prefix_sha256",
    "row_index",
    "row_payload_sha256",
    "schema_version",
    "source_chain_sha256",
    "split",
}
_SOURCE_RECEIPT_FIELDS = {
    "builder_tool_sha256",
    "custodian_full_corpus_decoded",
    "custodian_public_manifest_sha256",
    "custodian_public_receipt_sha256",
    "design_date_set_sha256",
    "economics_opened",
    "m1_manifest_sha256",
    "m1_rows",
    "performance_trials_executed",
    "pending_tree_sha256",
    "projection_sha256",
    "projection_receipt_sha256",
    "request_count",
    "request_plan_sha256",
    "request_receipt_sha256",
    "reconciliation_sha256",
    "research_holdout_opened",
    "research_validation_opened",
    "schema_version",
    "source_attempt_id",
    "stage_path",
    "stage_role",
    "supervisor_review_base_sha256",
    "trace_sha256",
    "verdict",
}
_SOURCE_SCHEMA = pa.schema(
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


class InvalidDesignValidation(RuntimeError):
    pass


class ValidationAuthority:
    def __init__(
        self,
        *,
        design_date_set_sha256: str,
        expected_design_dates: int,
        expected_rows_per_day: int,
        expected_total_rows: int,
        first_design_date: str,
        last_design_date: str,
        validator_tool_sha256: str,
        validator_test_sha256: str,
        custodian_public_receipt_sha256: str,
        custodian_public_manifest_sha256: str,
        expected_pending_receipt_sha256: str,
        expected_pending_tree_sha256: str,
        parent_ledger_sha256: str,
        parent_receipt_sha256: str,
        projector_tool_sha256: str,
        builder_tool_sha256: str,
        source_attempt_id: str,
        design_stage_path: str,
        stage_role: str,
        supervisor_review_base_sha256: str,
        custody_design_day_sha256: dict[str, str],
        expected_root_identity: tuple[int, ...],
        expected_directory_identities: dict[str, tuple[int, ...]],
        expected_file_identities: dict[str, tuple[int, ...]],
    ) -> None:
        self.design_date_set_sha256 = design_date_set_sha256
        self.expected_design_dates = expected_design_dates
        self.expected_rows_per_day = expected_rows_per_day
        self.expected_total_rows = expected_total_rows
        self.first_design_date = first_design_date
        self.last_design_date = last_design_date
        self.validator_tool_sha256 = validator_tool_sha256
        self.validator_test_sha256 = validator_test_sha256
        self.custodian_public_receipt_sha256 = custodian_public_receipt_sha256
        self.custodian_public_manifest_sha256 = custodian_public_manifest_sha256
        self.expected_pending_receipt_sha256 = expected_pending_receipt_sha256
        self.expected_pending_tree_sha256 = expected_pending_tree_sha256
        self.parent_ledger_sha256 = parent_ledger_sha256
        self.parent_receipt_sha256 = parent_receipt_sha256
        self.projector_tool_sha256 = projector_tool_sha256
        self.builder_tool_sha256 = builder_tool_sha256
        self.source_attempt_id = source_attempt_id
        self.design_stage_path = design_stage_path
        self.stage_role = stage_role
        self.supervisor_review_base_sha256 = supervisor_review_base_sha256
        self.custody_design_day_sha256 = dict(custody_design_day_sha256)
        self.expected_root_identity = tuple(expected_root_identity)
        self.expected_directory_identities = dict(expected_directory_identities)
        self.expected_file_identities = dict(expected_file_identities)


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(character in _HEX for character in value)


def _valid_source_attempt_id(value: object) -> bool:
    prefix = "HYP003-SOURCE-ATTEMPT-"
    return (
        type(value) is str
        and value.isascii()
        and value.startswith(prefix)
        and len(value) == len(prefix) + 16
        and all(character in _HEX for character in value[len(prefix) :])
    )


def _identity(path: Path) -> tuple[int, int, int, int, int, int, int]:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISREG(info.st_mode) or attributes & reparse or info.st_nlink != 1:
        raise ValueError
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
        int(info.st_nlink),
        attributes,
    )


def _directory_ok(path: Path) -> None:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISDIR(info.st_mode) or attributes & reparse:
        raise ValueError


def _directory_identity(path: Path) -> tuple[int, int, int, int, int, int]:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISDIR(info.st_mode) or attributes & reparse:
        raise ValueError
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
        attributes,
    )


def _stable_read(path: Path, expected_identity: tuple[int, ...]) -> bytes:
    if _identity(path) != expected_identity:
        raise ValueError
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != expected_identity[:2]:
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    if _identity(path) != expected_identity or int(final.st_size) != len(payload):
        raise ValueError
    return payload


def _canonical_object(payload: bytes) -> dict[str, object]:
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(payload)
    if type(value) is not dict or _canonical(value) + b"\n" != payload:
        raise ValueError
    return value


def _canonical_rows(payload: bytes) -> list[dict[str, object]]:
    if not payload or not payload.endswith(b"\n"):
        raise ValueError
    rows = []
    for line in payload.splitlines():
        value = json.loads(line)
        if type(value) is not dict or _canonical(value) != line:
            raise ValueError
        rows.append(value)
    return rows


def _date_set_bytes(dates: list[str]) -> bytes:
    if not dates or dates != sorted(set(dates)):
        raise ValueError
    for day in dates:
        if datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
            raise ValueError
        if day < "2016-01-04" or day >= "2021-01-01":
            raise ValueError
    return DATE_SET_PREFIX + b"".join(day.encode("ascii") + b"\n" for day in dates)


def _validate_authority(authority: ValidationAuthority) -> None:
    expected = {
        "design_date_set_sha256",
        "expected_design_dates",
        "expected_rows_per_day",
        "expected_total_rows",
        "first_design_date",
        "last_design_date",
        "validator_tool_sha256",
        "validator_test_sha256",
        "custodian_public_receipt_sha256",
        "custodian_public_manifest_sha256",
        "expected_pending_receipt_sha256",
        "expected_pending_tree_sha256",
        "parent_ledger_sha256",
        "parent_receipt_sha256",
        "projector_tool_sha256",
        "builder_tool_sha256",
        "source_attempt_id",
        "design_stage_path",
        "stage_role",
        "supervisor_review_base_sha256",
        "custody_design_day_sha256",
        "expected_root_identity",
        "expected_directory_identities",
        "expected_file_identities",
    }
    if type(authority) is not ValidationAuthority or set(authority.__dict__) != expected:
        raise ValueError
    for key in (
        "design_date_set_sha256",
        "validator_tool_sha256",
        "validator_test_sha256",
        "custodian_public_receipt_sha256",
        "custodian_public_manifest_sha256",
        "expected_pending_receipt_sha256",
        "expected_pending_tree_sha256",
        "parent_ledger_sha256",
        "parent_receipt_sha256",
        "projector_tool_sha256",
        "builder_tool_sha256",
        "supervisor_review_base_sha256",
    ):
        if not _valid_sha(authority.__dict__[key]):
            raise ValueError
    if (
        not _valid_source_attempt_id(authority.source_attempt_id)
        or type(authority.design_stage_path) is not str
        or not Path(authority.design_stage_path).is_absolute()
        or authority.stage_role != "DESIGN"
    ):
        raise ValueError
    if type(authority.custody_design_day_sha256) is not dict or not authority.custody_design_day_sha256:
        raise ValueError
    if any(type(day) is not str or not _valid_sha(digest) for day, digest in authority.custody_design_day_sha256.items()):
        raise ValueError
    if (
        type(authority.expected_root_identity) is not tuple
        or type(authority.expected_directory_identities) is not dict
        or type(authority.expected_file_identities) is not dict
        or authority.expected_directory_identities.get(".") != authority.expected_root_identity
    ):
        raise ValueError
    for identities in (authority.expected_directory_identities, authority.expected_file_identities):
        if any(
            type(relative) is not str
            or type(identity) is not tuple
            or not identity
            or any(type(value) is not int for value in identity)
            for relative, identity in identities.items()
        ):
            raise ValueError
    for key in ("expected_design_dates", "expected_rows_per_day", "expected_total_rows"):
        if type(authority.__dict__[key]) is not int or authority.__dict__[key] <= 0:
            raise ValueError
    if authority.expected_rows_per_day != 360:
        raise ValueError
    if authority.expected_total_rows != authority.expected_design_dates * authority.expected_rows_per_day:
        raise ValueError


def _inventory(root: Path) -> tuple[tuple[int, ...], dict[str, tuple[int, ...]], dict[str, tuple[int, ...]]]:
    root_identity = _directory_identity(root)
    files: dict[str, tuple[int, ...]] = {}
    directories: dict[str, tuple[int, ...]] = {".": root_identity}
    pending = [root]
    while pending:
        current = pending.pop()
        _directory_identity(current)
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                info = os.lstat(path)
                attributes = int(getattr(info, "st_file_attributes", 0))
                reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
                if attributes & reparse:
                    raise ValueError
                if stat.S_ISDIR(info.st_mode):
                    directories[relative] = _directory_identity(path)
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    files[relative] = _identity(path)
                else:
                    raise ValueError
    if _directory_identity(root) != root_identity:
        raise ValueError
    for relative, identity in directories.items():
        target = root if relative == "." else root / relative
        if _directory_identity(target) != identity:
            raise ValueError
    return root_identity, files, directories


def _decode_projection(wrapper: dict[str, object]) -> dict[str, object]:
    expected = {"schema_version", "opportunity_id", "split", "parent_row_sha256", "parent_row_canonical_b64"}
    if (
        set(wrapper) != expected
        or wrapper["schema_version"] != PROJECTION_SCHEMA
        or wrapper["split"] != "DESIGN"
        or type(wrapper["opportunity_id"]) is not str
    ):
        raise ValueError
    encoded = wrapper["parent_row_canonical_b64"]
    if type(encoded) is not str or not _valid_sha(wrapper["parent_row_sha256"]):
        raise ValueError
    original = base64.b64decode(encoded.encode("ascii"), validate=True)
    if _digest(original) != wrapper["parent_row_sha256"]:
        raise ValueError
    row = json.loads(original)
    if type(row) is not dict or _canonical(row) != original:
        raise ValueError
    if set(row) != _PARENT_FIELDS or row.get("schema_version") != PARENT_SCHEMA or row.get("hypothesis_id") != PARENT_ID:
        raise ValueError
    if row.get("split") != "DESIGN" or row.get("opportunity_id") != wrapper["opportunity_id"]:
        raise ValueError
    return row


def _validate_shard(payload: bytes, day: str, expected_rows: int) -> None:
    parquet = pq.ParquetFile(pa.BufferReader(payload))
    if not parquet.schema_arrow.equals(_SOURCE_SCHEMA, check_metadata=False):
        raise ValueError
    if parquet.metadata.num_row_groups != 1 or parquet.metadata.num_rows != expected_rows:
        raise ValueError
    rows = parquet.read().to_pylist()
    start = datetime.fromisoformat(day + "T12:01:00")
    for index, row in enumerate(rows):
        utc = row["time_utc"]
        server = row["time_server"]
        offset = row["utc_offset_h"]
        if not isinstance(utc, datetime) or not isinstance(server, datetime) or type(offset) is not int:
            raise ValueError
        if utc != start + timedelta(minutes=index) or server - utc != timedelta(hours=offset):
            raise ValueError
        values = [row[key] for key in ("open", "high", "low", "close")]
        if any(type(value) is not float or not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError
        open_value, high, low, close = values
        if not (low <= open_value <= high and low <= close <= high):
            raise ValueError


def validate_design_source(
    output_root: Path | str,
    authority: ValidationAuthority,
    lifecycle_hook: Callable[[str], None] | None = None,
) -> dict[str, object]:
    try:
        _validate_authority(authority)
        root = Path(output_root).absolute()
        expected_stage = root.parent / ("." + root.name + ".attempt-" + authority.source_attempt_id)
        if Path(authority.design_stage_path).absolute() != expected_stage:
            raise ValueError
        root_identity, files, directories = _inventory(root)
        if (
            root_identity != authority.expected_root_identity
            or files != authority.expected_file_identities
            or directories != authority.expected_directory_identities
        ):
            raise ValueError
        if lifecycle_hook is not None:
            lifecycle_hook("after_inventory")

        base_payloads = {
            name: _stable_read(root / name, files[name])
            for name in _BASE_FILES
            if name in files
        }
        if set(base_payloads) != _BASE_FILES:
            raise ValueError
        requests = _canonical_rows(base_payloads["design_request_plan.jsonl"])
        projections = _canonical_rows(base_payloads["design_stage0_projection.jsonl"])
        manifest = _canonical_rows(base_payloads["design_m1_manifest.jsonl"])
        trace = _canonical_rows(base_payloads["design_source_access_trace.jsonl"])
        request_receipt = _canonical_object(base_payloads["design_request_plan_receipt.json"])
        projection_receipt = _canonical_object(base_payloads["design_stage0_projection_receipt.json"])
        reconciliation = _canonical_object(base_payloads["design_source_reconciliation.json"])
        source_receipt = _canonical_object(base_payloads["design_m1_source_receipt.json"])

        dates = [str(item.get("date")) for item in requests]
        if (
            len(dates) != authority.expected_design_dates
            or dates[0] != authority.first_design_date
            or dates[-1] != authority.last_design_date
            or _digest(_date_set_bytes(dates)) != authority.design_date_set_sha256
        ):
            raise ValueError
        for day, request in zip(dates, requests):
            if set(request) != _REQUEST_FIELDS:
                raise ValueError
            if (
                request["schema_version"] != "trendstack_003_design_request.v1"
                or request["date"] != day
                or request["parent_opportunity_id"] != day
                or request["request_id"] != "HYP003::" + day + "::M1_SOURCE"
                or request["start_utc"] != day + "T12:01:00"
                or request["end_utc"] != day + "T18:00:00"
            ):
                raise ValueError
        if [str(item.get("date")) for item in manifest] != dates or [str(item.get("date")) for item in trace] != dates:
            raise ValueError
        decoded = [_decode_projection(item) for item in projections]
        if [str(item["opportunity_id"]) for item in decoded] != dates:
            raise ValueError

        expected_files = set(_BASE_FILES)
        expected_directories = {".", "raw_m1", "raw_m1/DESIGN"}
        for day in dates:
            expected_directories.add("raw_m1/DESIGN/" + day)
            expected_files.add("raw_m1/DESIGN/" + day + "/1201_1800.parquet")
        if set(files) != expected_files or set(directories) != expected_directories:
            raise ValueError

        total_rows = 0
        pending_tree_payloads = {
            relative: payload
            for relative, payload in base_payloads.items()
            if relative != "design_m1_source_receipt.json"
        }
        for index, day in enumerate(dates):
            relative = "raw_m1/DESIGN/" + day + "/1201_1800.parquet"
            payload = _stable_read(root / relative, files[relative])
            pending_tree_payloads[relative] = payload
            item = manifest[index]
            if set(item) != {"bytes", "date", "relative_path", "rows", "sha256"}:
                raise ValueError
            if (
                item["date"] != day
                or item["relative_path"] != relative
                or type(item["rows"]) is not int
                or item["rows"] != authority.expected_rows_per_day
                or type(item["bytes"]) is not int
                or item["bytes"] != len(payload)
                or item["sha256"] != _digest(payload)
            ):
                raise ValueError
            _validate_shard(payload, day, authority.expected_rows_per_day)
            trace_item = trace[index]
            if set(trace_item) != _TRACE_FIELDS:
                raise ValueError
            if (
                trace_item.get("schema_version") != "trendstack_003_design_source_trace.v1"
                or trace_item.get("date") != day
                or trace_item.get("request_index") != index
                or trace_item.get("input_day_sha256") != authority.custody_design_day_sha256.get(day)
                or trace_item.get("output_sha256") != item["sha256"]
                or trace_item.get("rows") != item["rows"]
            ):
                raise ValueError
            total_rows += int(item["rows"])
        if total_rows != authority.expected_total_rows:
            raise ValueError
        if set(authority.custody_design_day_sha256) != set(dates):
            raise ValueError

        bindings = {
            "request_plan_sha256": _digest(base_payloads["design_request_plan.jsonl"]),
            "request_receipt_sha256": _digest(base_payloads["design_request_plan_receipt.json"]),
            "projection_sha256": _digest(base_payloads["design_stage0_projection.jsonl"]),
            "projection_receipt_sha256": _digest(base_payloads["design_stage0_projection_receipt.json"]),
            "m1_manifest_sha256": _digest(base_payloads["design_m1_manifest.jsonl"]),
            "trace_sha256": _digest(base_payloads["design_source_access_trace.jsonl"]),
            "reconciliation_sha256": _digest(base_payloads["design_source_reconciliation.json"]),
        }
        if any(source_receipt.get(key) != value for key, value in bindings.items()):
            raise ValueError
        if set(source_receipt) != _SOURCE_RECEIPT_FIELDS or source_receipt.get("verdict") != PENDING_VERDICT:
            raise ValueError
        if set(request_receipt) != {"design_date_set_sha256", "request_count", "request_plan_sha256", "schema_version"}:
            raise ValueError
        if (
            request_receipt.get("schema_version") != "trendstack_003_design_request_receipt.v1"
            or request_receipt.get("request_plan_sha256") != bindings["request_plan_sha256"]
            or request_receipt.get("design_date_set_sha256") != authority.design_date_set_sha256
            or request_receipt.get("request_count") != authority.expected_design_dates
        ):
            raise ValueError
        if set(projection_receipt) != {
            "design_date_set_sha256",
            "design_rows",
            "parent_ledger_sha256",
            "parent_receipt_sha256",
            "projection_sha256",
            "projector_tool_sha256",
            "schema_version",
            "verdict",
        }:
            raise ValueError
        if (
            projection_receipt.get("schema_version") != "trendstack_003_design_projection_receipt.v1"
            or projection_receipt.get("verdict") != "DESIGN_ONLY_PROJECTION_ACCEPTED"
            or projection_receipt.get("projection_sha256") != bindings["projection_sha256"]
            or projection_receipt.get("design_date_set_sha256") != authority.design_date_set_sha256
            or projection_receipt.get("design_rows") != authority.expected_design_dates
            or projection_receipt.get("parent_ledger_sha256") != authority.parent_ledger_sha256
            or projection_receipt.get("parent_receipt_sha256") != authority.parent_receipt_sha256
            or projection_receipt.get("projector_tool_sha256") != authority.projector_tool_sha256
        ):
            raise ValueError
        if set(reconciliation) != {
            "date_set_sha256",
            "exact_once_status",
            "manifest_rows",
            "m1_rows",
            "schema_version",
            "trace_rows",
        }:
            raise ValueError
        if (
            reconciliation.get("schema_version") != "trendstack_003_design_source_reconciliation.v1"
            or reconciliation.get("exact_once_status") != "PASS"
            or reconciliation.get("date_set_sha256") != authority.design_date_set_sha256
            or reconciliation.get("manifest_rows") != authority.expected_design_dates
            or reconciliation.get("trace_rows") != authority.expected_design_dates
            or reconciliation.get("m1_rows") != total_rows
        ):
            raise ValueError
        if (
            source_receipt.get("schema_version") != "trendstack_003_design_source_receipt.v1"
            or source_receipt.get("design_date_set_sha256") != authority.design_date_set_sha256
            or source_receipt.get("request_count") != authority.expected_design_dates
            or source_receipt.get("m1_rows") != authority.expected_total_rows
            or source_receipt.get("custodian_public_receipt_sha256") != authority.custodian_public_receipt_sha256
            or source_receipt.get("custodian_public_manifest_sha256") != authority.custodian_public_manifest_sha256
            or source_receipt.get("builder_tool_sha256") != authority.builder_tool_sha256
            or source_receipt.get("source_attempt_id") != authority.source_attempt_id
            or source_receipt.get("stage_path") != authority.design_stage_path
            or source_receipt.get("stage_role") != authority.stage_role
            or source_receipt.get("supervisor_review_base_sha256")
            != authority.supervisor_review_base_sha256
            or source_receipt.get("pending_tree_sha256") != authority.expected_pending_tree_sha256
            or source_receipt.get("custodian_full_corpus_decoded") is not True
            or source_receipt.get("economics_opened") is not False
            or source_receipt.get("research_validation_opened") is not False
            or source_receipt.get("research_holdout_opened") is not False
            or type(source_receipt.get("performance_trials_executed")) is not int
            or source_receipt.get("performance_trials_executed") != 0
        ):
            raise ValueError
        source_receipt_sha256 = _digest(base_payloads["design_m1_source_receipt.json"])
        if source_receipt_sha256 != authority.expected_pending_receipt_sha256:
            raise ValueError
        pending_entries = [
            {"bytes": len(payload), "relative_path": relative, "sha256": _digest(payload)}
            for relative, payload in sorted(pending_tree_payloads.items())
        ]
        if _digest(_canonical({"files": pending_entries, "schema_version": PENDING_TREE_SCHEMA})) != authority.expected_pending_tree_sha256:
            raise ValueError
        result = {
            "design_date_set_sha256": authority.design_date_set_sha256,
            "source_receipt_sha256": source_receipt_sha256,
            "source_attempt_id": authority.source_attempt_id,
            "stage_path": authority.design_stage_path,
            "stage_role": authority.stage_role,
            "supervisor_review_base_sha256": authority.supervisor_review_base_sha256,
            "validated_dates": len(dates),
            "validated_m1_rows": total_rows,
            "validator_test_sha256": authority.validator_test_sha256,
            "validator_tool_sha256": authority.validator_tool_sha256,
            "verdict": READY_VERDICT,
        }
        if lifecycle_hook is not None:
            lifecycle_hook("before_final_inventory")
        final_root_identity, final_files, final_directories = _inventory(root)
        if (
            final_root_identity != root_identity
            or final_files != files
            or final_directories != directories
        ):
            raise ValueError
        return result
    except Exception as exc:
        if isinstance(exc, InvalidDesignValidation) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignValidation(PUBLIC_ERROR) from exc
