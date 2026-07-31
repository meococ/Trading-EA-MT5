"""Independent fail-closed validator for HYP006 DESIGN H1 source trees."""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


PUBLIC_ERROR = "INVALID_DESIGN_VALIDATION"
READY_VERDICT = "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
PENDING_VERDICT = "PENDING_INDEPENDENT_VALIDATION"
FROZEN_DESIGN_DATES = 1_297
FROZEN_ROWS_PER_DAY = 7
FROZEN_TOTAL_ROWS = 9_079
FROZEN_FIRST_DATE = "2016-01-04"
FROZEN_LAST_DATE = "2020-12-31"
FROZEN_DESIGN_DATE_SET_SHA256 = "4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A"
DESIGN_DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
EXPECTED_SCHEMA = pa.schema(
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
_HEX = frozenset("0123456789ABCDEF")
REGISTRY_ROW_INDEX = 282
REGISTRY_ROW_SHA256 = "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E"
_SELECTION_FIELDS = {"date", "schema_version"}
_MAPPING_FIELDS = {"bytes", "date", "relative_path", "schema_version", "sha256"}
_REQUEST_FIELDS = {"date", "end_utc", "request_id", "schema_version", "start_utc"}
_REQUEST_RECEIPT_FIELDS = {
    "design_date_set_sha256",
    "request_count",
    "request_plan_sha256",
    "schema_version",
    "selection_manifest_sha256",
    "selection_mapping_sha256",
}
_MANIFEST_FIELDS = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
_TRACE_FIELDS = {"date", "input_day_sha256", "mapping_sha256", "output_sha256", "request_index", "rows", "schema_version"}
_RECONCILIATION_FIELDS = {
    "date_set_sha256",
    "exact_once_status",
    "h1_rows",
    "manifest_rows",
    "mapping_rows",
    "request_rows",
    "schema_version",
    "trace_rows",
}
_RECEIPT_FIELDS = {
    "builder_test_sha256",
    "builder_tool_sha256",
    "collection_plan_v1_sha256",
    "collection_plan_v2_sha256",
    "custodian_public_manifest_sha256",
    "custodian_public_receipt_sha256",
    "custodian_test_sha256",
    "custodian_tool_sha256",
    "design_date_set_sha256",
    "economics_opened",
    "h1_manifest_sha256",
    "h1_rows",
    "packet_sha256",
    "pending_tree_sha256",
    "performance_trials_executed",
    "probe_plan_v1_sha256",
    "probe_plan_v2_sha256",
    "raw_source_opens",
    "reconciliation_sha256",
    "registry_sha256",
    "request_count",
    "request_plan_sha256",
    "request_receipt_sha256",
    "research_holdout_opened",
    "research_validation_opened",
    "schema_version",
    "selected_shard_opens",
    "selection_manifest_sha256",
    "selection_mapping_sha256",
    "source_attempt_id",
    "registry_row_index",
    "registry_row_sha256",
    "stage_path",
    "stage_role",
    "supervisor_review_base_sha256",
    "supervisor_test_sha256",
    "trace_sha256",
    "unselected_shard_opens",
    "validator_test_sha256",
    "validator_tool_sha256",
    "verdict",
}
_BASE_FILES = {
    "design_date_selection.jsonl",
    "design_shard_mapping.jsonl",
    "design_request_plan.jsonl",
    "design_request_plan_receipt.json",
    "design_h1_manifest.jsonl",
    "design_source_access_trace.jsonl",
    "design_source_reconciliation.json",
    "design_h1_source_receipt.json",
}


class InvalidDesignValidation(RuntimeError):
    pass


@dataclass(frozen=True)
class ValidationShape:
    design_date_set_sha256: str
    expected_design_dates: int
    expected_rows_per_day: int
    expected_total_rows: int
    first_design_date: str
    last_design_date: str


PRODUCTION_SHAPE = ValidationShape(
    FROZEN_DESIGN_DATE_SET_SHA256,
    FROZEN_DESIGN_DATES,
    FROZEN_ROWS_PER_DAY,
    FROZEN_TOTAL_ROWS,
    FROZEN_FIRST_DATE,
    FROZEN_LAST_DATE,
)


@dataclass(frozen=True)
class ValidationAuthority:
    validator_tool_sha256: str
    validator_test_sha256: str
    builder_tool_sha256: str
    builder_test_sha256: str
    custodian_tool_sha256: str
    custodian_test_sha256: str
    supervisor_test_sha256: str
    collection_plan_v1_sha256: str
    collection_plan_v2_sha256: str
    probe_plan_v1_sha256: str
    probe_plan_v2_sha256: str
    registry_sha256: str
    registry_row_index: int
    registry_row_sha256: str
    packet_sha256: str
    source_attempt_id: str
    stage_path: str
    stage_role: str
    supervisor_review_base_sha256: str
    custodian_public_receipt_sha256: str
    custodian_public_manifest_sha256: str
    selection_manifest_sha256: str
    selection_mapping_sha256: str
    expected_receipt_sha256: str
    expected_tree_sha256: str


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in _HEX for char in value)


def _valid_attempt_id(value: object) -> bool:
    prefix = "HYP006-SOURCE-ATTEMPT-"
    return (
        type(value) is str
        and value.isascii()
        and value.startswith(prefix)
        and len(value) == len(prefix) + 16
        and all(char in _HEX for char in value[len(prefix) :])
    )


def _assert_no_ads(path: Path) -> None:
    raw = str(path)
    tail = raw[2:] if len(raw) >= 2 and raw[1] == ":" else raw
    if ":" in tail:
        raise ValueError
    if os.name != "nt" or not path.exists() or path == Path(path.anchor):
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    class _StreamData(ctypes.Structure):
        _fields_ = [("size", ctypes.c_longlong), ("name", ctypes.c_wchar * 296)]

    data = _StreamData()
    find_first = kernel32.FindFirstStreamW
    find_first.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    find_first.restype = ctypes.c_void_p
    handle = find_first(str(path), 0, ctypes.byref(data), 0)
    invalid = ctypes.c_void_p(-1).value
    if handle == invalid:
        if ctypes.get_last_error() not in (1, 38):
            raise OSError(ctypes.get_last_error(), "FindFirstStreamW")
        return
    try:
        names = [data.name]
        find_next = kernel32.FindNextStreamW
        find_next.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        find_next.restype = ctypes.c_int
        while find_next(handle, ctypes.byref(data)):
            names.append(data.name)
    finally:
        find_close = kernel32.FindClose
        find_close.argtypes = [ctypes.c_void_p]
        find_close.restype = ctypes.c_int
        find_close(handle)
    if names != ["::$DATA"]:
        raise ValueError


def _file_identity(path: Path) -> tuple[int, int, int, int, int, int, int]:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if not stat.S_ISREG(info.st_mode) or attributes & reparse or path.is_symlink() or int(info.st_nlink) != 1:
        raise ValueError
    _assert_no_ads(path)
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_ctime_ns),
        int(info.st_nlink),
        attributes,
    )


def _directory_identity(path: Path) -> tuple[int, int, int, int, int, int]:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if (
        not stat.S_ISDIR(info.st_mode)
        or attributes & reparse
        or path.is_symlink()
        or (path != Path(path.anchor) and path.is_mount())
    ):
        raise ValueError
    _assert_no_ads(path)
    return (int(info.st_dev), int(info.st_ino), int(info.st_mode), int(info.st_mtime_ns), int(info.st_ctime_ns), attributes)


def _stable_read(path: Path, expected_identity: tuple[int, ...] | None = None) -> bytes:
    identity = _file_identity(path)
    if expected_identity is not None and identity != expected_identity:
        raise ValueError
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != identity[:2]:
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    if _file_identity(path) != identity or int(final.st_size) != len(payload):
        raise ValueError
    return payload


def _object(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(payload)
    if type(value) is not dict or _canonical(value) + b"\n" != payload:
        raise ValueError
    return value


def _rows(payload: bytes) -> list[dict[str, object]]:
    if type(payload) is not bytes or not payload or not payload.endswith(b"\n"):
        raise ValueError
    result: list[dict[str, object]] = []
    for line in payload.splitlines():
        value = json.loads(line)
        if type(value) is not dict or _canonical(value) != line:
            raise ValueError
        result.append(value)
    return result


def _date_set_sha(dates: list[str]) -> str:
    if not dates or dates != sorted(set(dates)):
        raise ValueError
    for day in dates:
        if datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day or day < FROZEN_FIRST_DATE or day >= "2021-01-01":
            raise ValueError
    return _digest(DESIGN_DATE_SET_PREFIX + b"".join(day.encode("ascii") + b"\n" for day in dates))


def _exact_types(
    value: object,
    fields: set[str],
    *,
    integer_fields: set[str] = frozenset(),
    boolean_fields: set[str] = frozenset(),
) -> None:
    if type(value) is not dict or set(value) != fields:
        raise ValueError
    for key in fields:
        expected = bool if key in boolean_fields else int if key in integer_fields else str
        if type(value[key]) is not expected:
            raise ValueError


def _validate_shape(shape: ValidationShape) -> None:
    if type(shape) is not ValidationShape or not _valid_sha(shape.design_date_set_sha256):
        raise ValueError
    if (
        type(shape.expected_design_dates) is not int
        or type(shape.expected_rows_per_day) is not int
        or type(shape.expected_total_rows) is not int
        or shape.expected_design_dates <= 0
        or shape.expected_rows_per_day != 7
        or shape.expected_total_rows != shape.expected_design_dates * 7
        or shape.first_design_date > shape.last_design_date
    ):
        raise ValueError


def _validate_authority(authority: ValidationAuthority) -> None:
    if type(authority) is not ValidationAuthority:
        raise ValueError
    if any(not _valid_sha(value) for key, value in authority.__dict__.items() if key.endswith("_sha256")):
        raise ValueError
    if (
        type(authority.registry_row_index) is not int
        or authority.registry_row_index != REGISTRY_ROW_INDEX
        or authority.registry_row_sha256 != REGISTRY_ROW_SHA256
        or not _valid_attempt_id(authority.source_attempt_id)
        or authority.stage_role != "DESIGN"
        or type(authority.stage_path) is not str
        or not Path(authority.stage_path).is_absolute()
    ):
        raise ValueError
    verified = globals().get("__verified_sha256__")
    if verified is not None and authority.validator_tool_sha256 != verified:
        raise ValueError


def _inventory_no_follow(root: Path) -> tuple[tuple[int, ...], dict[str, tuple[int, ...]], dict[str, tuple[int, ...]]]:
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
                if attributes & reparse or entry.is_symlink():
                    raise ValueError
                if stat.S_ISDIR(info.st_mode):
                    directories[relative] = _directory_identity(path)
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    files[relative] = _file_identity(path)
                else:
                    raise ValueError
    if _directory_identity(root) != root_identity:
        raise ValueError
    return root_identity, files, directories


def _validate_shard(payload: bytes, day: str, expected_rows: int = 7) -> None:
    try:
        parquet = pq.ParquetFile(pa.BufferReader(payload))
        if (
            not parquet.schema_arrow.equals(EXPECTED_SCHEMA, check_metadata=False)
            or parquet.metadata.num_row_groups != 1
            or parquet.metadata.num_rows != expected_rows
        ):
            raise ValueError
        rows = parquet.read().to_pylist()
        previous: datetime | None = None
        for index, row in enumerate(rows):
            if set(row) != set(EXPECTED_SCHEMA.names) or any(row[name] is None for name in EXPECTED_SCHEMA.names):
                raise ValueError
            utc = row["time_utc"]
            server = row["time_server"]
            offset = row["utc_offset_h"]
            expected = datetime.fromisoformat(f"{day}T{12 + index:02d}:00:00")
            if (
                not isinstance(utc, datetime)
                or not isinstance(server, datetime)
                or type(offset) is not int
                or utc != expected
                or (previous is not None and utc <= previous)
                or server - utc != timedelta(hours=offset)
            ):
                raise ValueError
            previous = utc
            values = [row[key] for key in ("open", "high", "low", "close")]
            if any(type(value) is not float or not math.isfinite(value) or value <= 0 for value in values):
                raise ValueError
            open_value, high, low, close = values
            if not (low <= open_value <= high and low <= close <= high):
                raise ValueError
            for key in ("tick_volume", "spread", "real_volume"):
                if type(row[key]) is not int or row[key] < 0:
                    raise ValueError
    except Exception as exc:
        if isinstance(exc, InvalidDesignValidation) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignValidation(PUBLIC_ERROR) from exc


def _tree_sha(payloads: dict[str, bytes]) -> str:
    entries = [
        {"bytes": len(payload), "relative_path": relative, "sha256": _digest(payload)}
        for relative, payload in sorted(payloads.items())
    ]
    return _digest(_canonical({"files": entries, "schema_version": "trendstack_006_pending_tree.v1"}))


def _validate_design_source(root_value: Path | str, authority: ValidationAuthority, shape: ValidationShape) -> dict[str, object]:
    _validate_authority(authority)
    _validate_shape(shape)
    root = Path(root_value).absolute()
    expected_stage = root.parent / ("." + root.name + ".attempt-" + authority.source_attempt_id)
    if Path(authority.stage_path).absolute() != expected_stage:
        raise ValueError
    root_identity, file_identities, directory_identities = _inventory_no_follow(root)
    if not _BASE_FILES.issubset(file_identities):
        raise ValueError
    payloads = {name: _stable_read(root / name, file_identities[name]) for name in _BASE_FILES}
    selection = _rows(payloads["design_date_selection.jsonl"])
    mapping = _rows(payloads["design_shard_mapping.jsonl"])
    requests = _rows(payloads["design_request_plan.jsonl"])
    request_receipt = _object(payloads["design_request_plan_receipt.json"])
    manifest = _rows(payloads["design_h1_manifest.jsonl"])
    trace = _rows(payloads["design_source_access_trace.jsonl"])
    reconciliation = _object(payloads["design_source_reconciliation.json"])
    receipt = _object(payloads["design_h1_source_receipt.json"])
    for row in selection:
        _exact_types(row, _SELECTION_FIELDS)
    for row in mapping:
        _exact_types(row, _MAPPING_FIELDS, integer_fields={"bytes"})
    for row in requests:
        _exact_types(row, _REQUEST_FIELDS)
    _exact_types(request_receipt, _REQUEST_RECEIPT_FIELDS, integer_fields={"request_count"})
    for row in manifest:
        _exact_types(row, _MANIFEST_FIELDS, integer_fields={"bytes", "rows"})
    for row in trace:
        _exact_types(row, _TRACE_FIELDS, integer_fields={"request_index", "rows"})
    _exact_types(
        reconciliation,
        _RECONCILIATION_FIELDS,
        integer_fields={"h1_rows", "manifest_rows", "mapping_rows", "request_rows", "trace_rows"},
    )
    _exact_types(
        receipt,
        _RECEIPT_FIELDS,
        integer_fields={
            "h1_rows", "performance_trials_executed", "raw_source_opens", "request_count",
            "registry_row_index", "selected_shard_opens", "unselected_shard_opens",
        },
        boolean_fields={"economics_opened", "research_holdout_opened", "research_validation_opened"},
    )
    if (
        _digest(payloads["design_date_selection.jsonl"]) != authority.selection_manifest_sha256
        or _digest(payloads["design_shard_mapping.jsonl"]) != authority.selection_mapping_sha256
    ):
        raise ValueError
    dates = [str(row.get("date")) for row in selection]
    if (
        len(dates) != shape.expected_design_dates
        or dates != sorted(set(dates))
        or dates[0] != shape.first_design_date
        or dates[-1] != shape.last_design_date
        or _date_set_sha(dates) != shape.design_date_set_sha256
        or any(set(row) != _SELECTION_FIELDS or row.get("schema_version") != "trendstack_006_design_date_selection.v1" for row in selection)
    ):
        raise ValueError
    mapping_by_date: dict[str, dict[str, object]] = {}
    for row in mapping:
        day = row.get("date")
        if (
            set(row) != _MAPPING_FIELDS
            or row.get("schema_version") != "trendstack_006_selected_design_shard.v1"
            or type(day) is not str
            or day in mapping_by_date
            or row.get("relative_path") != f"public/DESIGN/{day}/h1.parquet"
            or type(row.get("bytes")) is not int
            or int(row["bytes"]) <= 0
            or not _valid_sha(row.get("sha256"))
        ):
            raise ValueError
        mapping_by_date[day] = row
    if tuple(mapping_by_date) != tuple(dates):
        raise ValueError
    if [str(row.get("date")) for row in requests] != dates or [str(row.get("date")) for row in manifest] != dates or [str(row.get("date")) for row in trace] != dates:
        raise ValueError
    for day, request in zip(dates, requests):
        if (
            set(request) != _REQUEST_FIELDS
            or request.get("schema_version") != "trendstack_006_design_request.v1"
            or request.get("request_id") != f"HYP006::{day}::H1_SOURCE"
            or request.get("start_utc") != day + "T12:00:00"
            or request.get("end_utc") != day + "T18:00:00"
        ):
            raise ValueError
    expected_files = set(_BASE_FILES)
    expected_directories = {"." , "raw_h1", "raw_h1/DESIGN"}
    pending_payloads = {name: payload for name, payload in payloads.items() if name != "design_h1_source_receipt.json"}
    total = 0
    for index, day in enumerate(dates):
        relative = f"raw_h1/DESIGN/{day}/1200_1800.parquet"
        expected_files.add(relative)
        expected_directories.add(f"raw_h1/DESIGN/{day}")
        if relative not in file_identities:
            raise ValueError
        shard = _stable_read(root / relative, file_identities[relative])
        pending_payloads[relative] = shard
        item = manifest[index]
        if (
            set(item) != _MANIFEST_FIELDS
            or item.get("schema_version") != "trendstack_006_design_h1_manifest_row.v1"
            or item.get("date") != day
            or item.get("relative_path") != relative
            or item.get("rows") != shape.expected_rows_per_day
            or item.get("bytes") != len(shard)
            or item.get("sha256") != _digest(shard)
        ):
            raise ValueError
        _validate_shard(shard, day, shape.expected_rows_per_day)
        trace_item = trace[index]
        if (
            set(trace_item) != _TRACE_FIELDS
            or trace_item.get("schema_version") != "trendstack_006_design_source_trace.v1"
            or trace_item.get("date") != day
            or trace_item.get("request_index") != index
            or trace_item.get("input_day_sha256") != mapping_by_date[day]["sha256"]
            or trace_item.get("mapping_sha256") != authority.selection_mapping_sha256
            or trace_item.get("output_sha256") != item["sha256"]
            or trace_item.get("rows") != item["rows"]
        ):
            raise ValueError
        total += int(item["rows"])
    if total != shape.expected_total_rows or set(file_identities) != expected_files or set(directory_identities) != expected_directories:
        raise ValueError
    if _directory_identity(root) != root_identity:
        raise ValueError
    request_bindings = {
        "design_date_set_sha256": shape.design_date_set_sha256,
        "request_count": shape.expected_design_dates,
        "request_plan_sha256": _digest(payloads["design_request_plan.jsonl"]),
        "schema_version": "trendstack_006_design_request_receipt.v1",
        "selection_manifest_sha256": authority.selection_manifest_sha256,
        "selection_mapping_sha256": authority.selection_mapping_sha256,
    }
    if set(request_receipt) != _REQUEST_RECEIPT_FIELDS or request_receipt != request_bindings:
        raise ValueError
    expected_reconciliation = {
        "date_set_sha256": shape.design_date_set_sha256,
        "exact_once_status": "PASS",
        "h1_rows": shape.expected_total_rows,
        "manifest_rows": shape.expected_design_dates,
        "mapping_rows": shape.expected_design_dates,
        "request_rows": shape.expected_design_dates,
        "schema_version": "trendstack_006_design_source_reconciliation.v1",
        "trace_rows": shape.expected_design_dates,
    }
    if set(reconciliation) != _RECONCILIATION_FIELDS or reconciliation != expected_reconciliation:
        raise ValueError
    bindings = {
        "builder_test_sha256": authority.builder_test_sha256,
        "builder_tool_sha256": authority.builder_tool_sha256,
        "collection_plan_v1_sha256": authority.collection_plan_v1_sha256,
        "collection_plan_v2_sha256": authority.collection_plan_v2_sha256,
        "custodian_public_manifest_sha256": authority.custodian_public_manifest_sha256,
        "custodian_public_receipt_sha256": authority.custodian_public_receipt_sha256,
        "custodian_test_sha256": authority.custodian_test_sha256,
        "custodian_tool_sha256": authority.custodian_tool_sha256,
        "design_date_set_sha256": shape.design_date_set_sha256,
        "h1_manifest_sha256": _digest(payloads["design_h1_manifest.jsonl"]),
        "h1_rows": shape.expected_total_rows,
        "packet_sha256": authority.packet_sha256,
        "pending_tree_sha256": authority.expected_tree_sha256,
        "probe_plan_v1_sha256": authority.probe_plan_v1_sha256,
        "probe_plan_v2_sha256": authority.probe_plan_v2_sha256,
        "reconciliation_sha256": _digest(payloads["design_source_reconciliation.json"]),
        "registry_sha256": authority.registry_sha256,
        "request_count": shape.expected_design_dates,
        "request_plan_sha256": _digest(payloads["design_request_plan.jsonl"]),
        "request_receipt_sha256": _digest(payloads["design_request_plan_receipt.json"]),
        "selection_manifest_sha256": authority.selection_manifest_sha256,
        "selection_mapping_sha256": authority.selection_mapping_sha256,
        "source_attempt_id": authority.source_attempt_id,
        "registry_row_index": authority.registry_row_index,
        "registry_row_sha256": authority.registry_row_sha256,
        "stage_path": authority.stage_path,
        "stage_role": authority.stage_role,
        "supervisor_review_base_sha256": authority.supervisor_review_base_sha256,
        "supervisor_test_sha256": authority.supervisor_test_sha256,
        "trace_sha256": _digest(payloads["design_source_access_trace.jsonl"]),
        "validator_test_sha256": authority.validator_test_sha256,
        "validator_tool_sha256": authority.validator_tool_sha256,
    }
    if (
        set(receipt) != _RECEIPT_FIELDS
        or any(receipt.get(key) != value for key, value in bindings.items())
        or receipt.get("schema_version") != "trendstack_006_design_source_receipt.v1"
        or receipt.get("verdict") != PENDING_VERDICT
        or receipt.get("economics_opened") is not False
        or receipt.get("research_validation_opened") is not False
        or receipt.get("research_holdout_opened") is not False
        or receipt.get("performance_trials_executed") != 0
        or receipt.get("raw_source_opens") != 1
        or receipt.get("selected_shard_opens") != shape.expected_design_dates
        or receipt.get("unselected_shard_opens") != 0
    ):
        raise ValueError
    receipt_sha = _digest(payloads["design_h1_source_receipt.json"])
    if receipt_sha != authority.expected_receipt_sha256 or _tree_sha(pending_payloads) != authority.expected_tree_sha256:
        raise ValueError
    final_root, final_files, final_dirs = _inventory_no_follow(root)
    if final_root != root_identity or final_files != file_identities or final_dirs != directory_identities:
        raise ValueError
    return {
        "design_date_set_sha256": shape.design_date_set_sha256,
        "source_receipt_sha256": receipt_sha,
        "source_attempt_id": authority.source_attempt_id,
        "stage_path": authority.stage_path,
        "stage_role": authority.stage_role,
        "supervisor_review_base_sha256": authority.supervisor_review_base_sha256,
        "validated_dates": shape.expected_design_dates,
        "validated_h1_rows": shape.expected_total_rows,
        "validator_test_sha256": authority.validator_test_sha256,
        "validator_tool_sha256": authority.validator_tool_sha256,
        "verdict": READY_VERDICT,
    }


def validate_design_source(output_root: Path | str, authority: ValidationAuthority) -> dict[str, object]:
    """Production validator with a non-overridable 1,297-date contract."""
    try:
        return _validate_design_source(output_root, authority, PRODUCTION_SHAPE)
    except Exception as exc:
        if isinstance(exc, InvalidDesignValidation) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignValidation(PUBLIC_ERROR) from exc


def validate_design_source_for_testing(
    output_root: Path | str,
    authority: ValidationAuthority,
    *,
    shape: ValidationShape,
) -> dict[str, object]:
    try:
        if shape == PRODUCTION_SHAPE:
            raise ValueError
        return _validate_design_source(output_root, authority, shape)
    except Exception as exc:
        if isinstance(exc, InvalidDesignValidation) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignValidation(PUBLIC_ERROR) from exc
