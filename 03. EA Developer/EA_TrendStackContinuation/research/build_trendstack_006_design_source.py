"""Fail-closed HYP006 DESIGN H1 source builder.

The public entrypoint is deliberately frozen to the production 1,297-date /
9,079-row contract.  Tiny fixtures are available only through the explicitly
named testing entrypoint and never through packet or constructor overrides.
"""

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


PUBLIC_ERROR = "INVALID_DESIGN_SOURCE"
PENDING_VERDICT = "PENDING_INDEPENDENT_VALIDATION"
READY_VERDICT = "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
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
_SELECTION_SCHEMA = "trendstack_006_design_date_selection.v1"
_MAPPING_SCHEMA = "trendstack_006_selected_design_shard.v1"
_PUBLIC_MANIFEST_SCHEMA = "h1_splitvault_002_public_design_shard.v1"
_REQUEST_FIELDS = {"date", "end_utc", "request_id", "schema_version", "start_utc"}
_MAPPING_FIELDS = {"bytes", "date", "relative_path", "schema_version", "sha256"}
_MANIFEST_FIELDS = _MAPPING_FIELDS | {"rows"}
_PUBLIC_RECEIPT_FIELDS = {
    "collection_id", "design_dates", "design_manifest_sha256", "raw_source_opens",
    "research_holdout_opened", "research_validation_opened", "schema_version",
    "source_attempt_id", "source_rows", "unselected_shard_opens", "verdict",
}


class InvalidDesignSource(RuntimeError):
    pass


@dataclass(frozen=True)
class BuildShape:
    design_date_set_sha256: str
    expected_design_dates: int
    expected_rows_per_day: int
    expected_total_rows: int
    first_design_date: str
    last_design_date: str


PRODUCTION_SHAPE = BuildShape(
    FROZEN_DESIGN_DATE_SET_SHA256,
    FROZEN_DESIGN_DATES,
    FROZEN_ROWS_PER_DAY,
    FROZEN_TOTAL_ROWS,
    FROZEN_FIRST_DATE,
    FROZEN_LAST_DATE,
)


@dataclass(frozen=True)
class DesignSourceContract:
    builder_tool_sha256: str
    custodian_tool_sha256: str
    validator_tool_sha256: str
    custodian_test_sha256: str
    supervisor_test_sha256: str
    builder_test_sha256: str
    validator_test_sha256: str
    collection_plan_v1_sha256: str
    collection_plan_v2_sha256: str
    probe_plan_v1_sha256: str
    probe_plan_v2_sha256: str
    registry_sha256: str
    registry_row_index: int
    registry_row_sha256: str
    packet_sha256: str
    source_attempt_id: str
    design_stage_path: str
    stage_role: str
    supervisor_review_base_sha256: str
    custodian_public_receipt_sha256: str
    custodian_public_manifest_sha256: str
    selection_manifest_sha256: str
    selection_mapping_sha256: str


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise InvalidDesignSource(PUBLIC_ERROR)
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def canonical_design_date_set_bytes(dates: tuple[str, ...] | list[str]) -> bytes:
    try:
        if type(dates) not in (tuple, list) or not dates:
            raise ValueError
        previous: str | None = None
        encoded: list[bytes] = []
        for day in dates:
            if type(day) is not str or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
                raise ValueError
            if day < FROZEN_FIRST_DATE or day >= "2021-01-01" or (previous is not None and day <= previous):
                raise ValueError
            previous = day
            encoded.append(day.encode("ascii") + b"\n")
        return DESIGN_DATE_SET_PREFIX + b"".join(encoded)
    except Exception as exc:
        raise InvalidDesignSource(PUBLIC_ERROR) from exc


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


def _validate_shape(shape: BuildShape) -> None:
    if type(shape) is not BuildShape or not _valid_sha(shape.design_date_set_sha256):
        raise ValueError
    if (
        type(shape.expected_design_dates) is not int
        or type(shape.expected_rows_per_day) is not int
        or type(shape.expected_total_rows) is not int
        or shape.expected_design_dates <= 0
        or shape.expected_rows_per_day != 7
        or shape.expected_total_rows != shape.expected_design_dates * shape.expected_rows_per_day
        or datetime.strptime(shape.first_design_date, "%Y-%m-%d").date().isoformat() != shape.first_design_date
        or datetime.strptime(shape.last_design_date, "%Y-%m-%d").date().isoformat() != shape.last_design_date
        or shape.first_design_date > shape.last_design_date
    ):
        raise ValueError


def _validate_contract(contract: DesignSourceContract) -> None:
    if type(contract) is not DesignSourceContract:
        raise ValueError
    for key, value in contract.__dict__.items():
        if key.endswith("_sha256") and not _valid_sha(value):
            raise ValueError
    if (
        type(contract.registry_row_index) is not int
        or contract.registry_row_index != REGISTRY_ROW_INDEX
        or contract.registry_row_sha256 != REGISTRY_ROW_SHA256
        or not _valid_attempt_id(contract.source_attempt_id)
        or contract.stage_role != "DESIGN"
        or type(contract.design_stage_path) is not str
        or not Path(contract.design_stage_path).is_absolute()
    ):
        raise ValueError
    verified = globals().get("__verified_sha256__")
    if verified is not None and contract.builder_tool_sha256 != verified:
        raise ValueError


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
        error = ctypes.get_last_error()
        if error not in (1, 38):
            raise OSError(error, "FindFirstStreamW")
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


def _node_info(path: Path, *, directory: bool) -> os.stat_result:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    if attributes & reparse or path.is_symlink():
        raise ValueError
    if directory:
        if not stat.S_ISDIR(info.st_mode) or (path != Path(path.anchor) and path.is_mount()):
            raise ValueError
    elif not stat.S_ISREG(info.st_mode) or int(info.st_nlink) != 1:
        raise ValueError
    _assert_no_ads(path)
    return info


def _directory_chain(path: Path) -> None:
    current = path.absolute().parent
    while True:
        _node_info(current, directory=True)
        if current.parent == current:
            return
        current = current.parent


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (int(info.st_dev), int(info.st_ino), int(info.st_size), int(info.st_mtime_ns), int(info.st_ctime_ns))


def _directory_anchor(info: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(getattr(info, "st_file_attributes", 0)),
    )


def _stable_read(path: Path) -> bytes:
    _directory_chain(path)
    before = _node_info(path, directory=False)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != (int(before.st_dev), int(before.st_ino)):
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    if _identity(before) != _identity(_node_info(path, directory=False)) or int(final.st_size) != len(payload):
        raise ValueError
    return payload


def _fsync_directory(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0x40000000, 0x7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateFileW")
    try:
        flush = kernel32.FlushFileBuffers
        flush.argtypes = [ctypes.c_void_p]
        flush.restype = ctypes.c_int
        if not flush(handle):
            raise OSError(ctypes.get_last_error(), "FlushFileBuffers")
    finally:
        close = kernel32.CloseHandle
        close.argtypes = [ctypes.c_void_p]
        close.restype = ctypes.c_int
        close(handle)


def _mkdirs(path: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    _directory_chain(current / "child")
    for directory in reversed(missing):
        directory.mkdir()
        _node_info(directory, directory=True)
        _fsync_directory(directory.parent)


def _exclusive_write(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes or path.exists():
        raise ValueError
    _mkdirs(path.parent)
    _directory_chain(path)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_directory(path.parent)
    if _stable_read(path) != payload:
        raise ValueError


def _publish_no_replace(source: Path, destination: Path) -> None:
    if os.name == "nt":
        os.rename(source, destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError("atomic no-replace rename unavailable")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _canonical_object(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(payload)
    if type(value) is not dict or canonical_json(value) + b"\n" != payload:
        raise ValueError
    return value


def _canonical_rows(payload: bytes) -> list[dict[str, object]]:
    if type(payload) is not bytes or not payload or not payload.endswith(b"\n"):
        raise ValueError
    result: list[dict[str, object]] = []
    for line in payload.splitlines():
        value = json.loads(line)
        if type(value) is not dict or canonical_json(value) != line:
            raise ValueError
        result.append(value)
    return result


def _validate_metadata(capability, dates: tuple[str, ...], contract: DesignSourceContract) -> tuple[bytes, bytes, bytes, bytes, dict[str, dict[str, object]]]:
    selection = capability.selection_manifest_bytes()
    mapping = capability.selection_mapping_bytes()
    public_receipt = capability.public_receipt_bytes()
    public_manifest = capability.public_manifest_bytes()
    if (
        sha256_bytes(selection) != contract.selection_manifest_sha256
        or sha256_bytes(mapping) != contract.selection_mapping_sha256
        or sha256_bytes(public_receipt) != contract.custodian_public_receipt_sha256
        or sha256_bytes(public_manifest) != contract.custodian_public_manifest_sha256
    ):
        raise ValueError
    selection_rows = _canonical_rows(selection)
    if any(set(row) != {"date", "schema_version"} or row["schema_version"] != _SELECTION_SCHEMA for row in selection_rows):
        raise ValueError
    if tuple(str(row["date"]) for row in selection_rows) != dates:
        raise ValueError
    mapping_rows = _canonical_rows(mapping)
    mapping_by_date: dict[str, dict[str, object]] = {}
    for row in mapping_rows:
        day = row.get("date")
        relative = row.get("relative_path")
        if (
            set(row) != _MAPPING_FIELDS
            or row.get("schema_version") != _MAPPING_SCHEMA
            or type(day) is not str
            or day in mapping_by_date
            or relative != f"public/DESIGN/{day}/h1.parquet"
            or type(row.get("bytes")) is not int
            or int(row["bytes"]) <= 0
            or not _valid_sha(row.get("sha256"))
        ):
            raise ValueError
        mapping_by_date[day] = row
    if tuple(mapping_by_date) != dates:
        raise ValueError
    public_rows = _canonical_rows(public_manifest)
    public_by_date: dict[str, dict[str, object]] = {}
    for row in public_rows:
        day = row.get("date")
        if (
            set(row) != _MANIFEST_FIELDS
            or row.get("schema_version") != _PUBLIC_MANIFEST_SCHEMA
            or type(day) is not str
            or day in public_by_date
            or row.get("relative_path") != f"public/DESIGN/{day}/h1.parquet"
            or type(row.get("rows")) is not int
            or int(row["rows"]) <= 0
        ):
            raise ValueError
        public_by_date[day] = row
    if not set(dates).issubset(public_by_date):
        raise ValueError
    for day in dates:
        public = public_by_date[day]
        mapped = mapping_by_date[day]
        if any(public[key] != mapped[key] for key in ("date", "relative_path", "bytes", "sha256")):
            raise ValueError
    receipt = _canonical_object(public_receipt)
    if (
        set(receipt) != _PUBLIC_RECEIPT_FIELDS
        or receipt.get("collection_id") != "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002"
        or receipt.get("schema_version") != "h1_splitvault_002_public_receipt.v1"
        or receipt.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
        or receipt.get("source_attempt_id") != contract.source_attempt_id
        or receipt.get("design_manifest_sha256") != sha256_bytes(public_manifest)
        or type(receipt.get("design_dates")) is not int
        or receipt.get("design_dates") != len(public_rows)
        or type(receipt.get("source_rows")) is not int
        or receipt.get("source_rows") <= 0
        or receipt.get("research_validation_opened") is not False
        or receipt.get("research_holdout_opened") is not False
        or receipt.get("raw_source_opens") != 1
        or type(receipt.get("raw_source_opens")) is not int
        or receipt.get("unselected_shard_opens") != 0
        or type(receipt.get("unselected_shard_opens")) is not int
    ):
        raise ValueError
    return selection, mapping, public_receipt, public_manifest, mapping_by_date


def _validate_day_payload(payload: bytes, day: str) -> pa.Table:
    parquet = pq.ParquetFile(pa.BufferReader(payload))
    if not parquet.schema_arrow.equals(EXPECTED_SCHEMA, check_metadata=False) or parquet.metadata.num_row_groups != 1:
        raise ValueError
    rows = parquet.read().to_pylist()
    previous: datetime | None = None
    selected: list[dict[str, object]] = []
    for row in rows:
        if set(row) != set(EXPECTED_SCHEMA.names) or any(row[name] is None for name in EXPECTED_SCHEMA.names):
            raise ValueError
        utc = row["time_utc"]
        server = row["time_server"]
        offset = row["utc_offset_h"]
        if (
            not isinstance(utc, datetime)
            or not isinstance(server, datetime)
            or type(offset) is not int
            or utc.tzinfo is not None
            or server.tzinfo is not None
            or utc.date().isoformat() != day
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
        if utc.minute == 0 and utc.second == 0 and utc.microsecond == 0 and 12 <= utc.hour <= 18:
            selected.append(row)
    expected = [datetime.fromisoformat(f"{day}T{hour:02d}:00:00") for hour in range(12, 19)]
    if [row["time_utc"] for row in selected] != expected:
        raise ValueError
    return pa.Table.from_pylist(selected, schema=EXPECTED_SCHEMA)


def _write_parquet(path: Path, table: pa.Table) -> tuple[int, str]:
    _mkdirs(path.parent)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, row_group_size=table.num_rows)
    payload = sink.getvalue().to_pybytes()
    reopened = pq.ParquetFile(pa.BufferReader(payload))
    if reopened.metadata.num_rows != table.num_rows or reopened.metadata.num_row_groups != 1:
        raise ValueError
    _exclusive_write(path, payload)
    return len(payload), sha256_bytes(payload)


def _tree_sha(root: Path, relatives: set[str]) -> str:
    entries = []
    for relative in sorted(relatives):
        payload = _stable_read(root / relative)
        entries.append({"bytes": len(payload), "relative_path": relative, "sha256": sha256_bytes(payload)})
    return sha256_bytes(canonical_json({"files": entries, "schema_version": "trendstack_006_pending_tree.v1"}))


def _build_design_source(capability, output_root: Path | str, contract: DesignSourceContract, shape: BuildShape) -> dict[str, object]:
    _validate_contract(contract)
    _validate_shape(shape)
    output = Path(output_root).absolute()
    stage = Path(contract.design_stage_path).absolute()
    _directory_chain(output)
    if (
        output.exists()
        or stage.exists()
        or stage.parent != output.parent
        or stage.name != "." + output.name + ".attempt-" + contract.source_attempt_id
    ):
        raise ValueError
    parent_identity = _directory_anchor(_node_info(output.parent, directory=True))
    stage.mkdir(parents=False)
    _fsync_directory(stage.parent)
    stage_identity = _directory_anchor(_node_info(stage, directory=True))
    dates = capability.design_dates()
    if (
        type(dates) is not tuple
        or dates != tuple(sorted(set(dates)))
        or len(dates) != shape.expected_design_dates
        or dates[0] != shape.first_design_date
        or dates[-1] != shape.last_design_date
        or sha256_bytes(canonical_design_date_set_bytes(dates)) != shape.design_date_set_sha256
    ):
        raise ValueError
    selection, mapping, public_receipt, public_manifest, mapped = _validate_metadata(capability, dates, contract)
    _exclusive_write(stage / "design_date_selection.jsonl", selection)
    _exclusive_write(stage / "design_shard_mapping.jsonl", mapping)
    request_rows = [
        {
            "date": day,
            "end_utc": day + "T18:00:00",
            "request_id": "HYP006::" + day + "::H1_SOURCE",
            "schema_version": "trendstack_006_design_request.v1",
            "start_utc": day + "T12:00:00",
        }
        for day in dates
    ]
    request_payload = b"".join(canonical_json(row) + b"\n" for row in request_rows)
    _exclusive_write(stage / "design_request_plan.jsonl", request_payload)
    request_receipt = {
        "design_date_set_sha256": shape.design_date_set_sha256,
        "request_count": shape.expected_design_dates,
        "request_plan_sha256": sha256_bytes(request_payload),
        "schema_version": "trendstack_006_design_request_receipt.v1",
        "selection_manifest_sha256": contract.selection_manifest_sha256,
        "selection_mapping_sha256": contract.selection_mapping_sha256,
    }
    request_receipt_payload = canonical_json(request_receipt) + b"\n"
    _exclusive_write(stage / "design_request_plan_receipt.json", request_receipt_payload)
    manifest_rows: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []
    shard_files: set[str] = set()
    total = 0
    for index, day in enumerate(dates):
        payload = capability.read_design_day(day)
        if type(payload) is not bytes or len(payload) != mapped[day]["bytes"] or sha256_bytes(payload) != mapped[day]["sha256"]:
            raise ValueError
        table = _validate_day_payload(payload, day)
        relative = f"raw_h1/DESIGN/{day}/1200_1800.parquet"
        size, digest = _write_parquet(stage / relative, table)
        total += table.num_rows
        manifest_rows.append(
            {
                "bytes": size,
                "date": day,
                "relative_path": relative,
                "rows": table.num_rows,
                "schema_version": "trendstack_006_design_h1_manifest_row.v1",
                "sha256": digest,
            }
        )
        trace_rows.append(
            {
                "date": day,
                "input_day_sha256": mapped[day]["sha256"],
                "mapping_sha256": contract.selection_mapping_sha256,
                "output_sha256": digest,
                "request_index": index,
                "rows": table.num_rows,
                "schema_version": "trendstack_006_design_source_trace.v1",
            }
        )
        shard_files.add(relative)
    if total != shape.expected_total_rows or len(manifest_rows) != shape.expected_design_dates:
        raise ValueError
    open_counts = capability.open_count_summary()
    if (
        type(open_counts) is not dict
        or open_counts != {
            "raw_source_opens": 1,
            "selected_shard_opens": shape.expected_design_dates,
            "unselected_shard_opens": 0,
        }
    ):
        raise ValueError
    manifest_payload = b"".join(canonical_json(row) + b"\n" for row in manifest_rows)
    trace_payload = b"".join(canonical_json(row) + b"\n" for row in trace_rows)
    _exclusive_write(stage / "design_h1_manifest.jsonl", manifest_payload)
    _exclusive_write(stage / "design_source_access_trace.jsonl", trace_payload)
    reconciliation = {
        "date_set_sha256": sha256_bytes(canonical_design_date_set_bytes(list(dates))),
        "exact_once_status": "PASS",
        "h1_rows": total,
        "manifest_rows": len(manifest_rows),
        "mapping_rows": len(mapped),
        "request_rows": len(request_rows),
        "schema_version": "trendstack_006_design_source_reconciliation.v1",
        "trace_rows": len(trace_rows),
    }
    reconciliation_payload = canonical_json(reconciliation) + b"\n"
    _exclusive_write(stage / "design_source_reconciliation.json", reconciliation_payload)
    base_files = {
        "design_date_selection.jsonl",
        "design_shard_mapping.jsonl",
        "design_request_plan.jsonl",
        "design_request_plan_receipt.json",
        "design_h1_manifest.jsonl",
        "design_source_access_trace.jsonl",
        "design_source_reconciliation.json",
    }
    pending_tree_sha = _tree_sha(stage, base_files | shard_files)
    receipt = {
        "builder_test_sha256": contract.builder_test_sha256,
        "builder_tool_sha256": contract.builder_tool_sha256,
        "collection_plan_v1_sha256": contract.collection_plan_v1_sha256,
        "collection_plan_v2_sha256": contract.collection_plan_v2_sha256,
        "custodian_public_manifest_sha256": sha256_bytes(public_manifest),
        "custodian_public_receipt_sha256": sha256_bytes(public_receipt),
        "custodian_test_sha256": contract.custodian_test_sha256,
        "custodian_tool_sha256": contract.custodian_tool_sha256,
        "design_date_set_sha256": shape.design_date_set_sha256,
        "economics_opened": False,
        "h1_manifest_sha256": sha256_bytes(manifest_payload),
        "h1_rows": total,
        "packet_sha256": contract.packet_sha256,
        "pending_tree_sha256": pending_tree_sha,
        "performance_trials_executed": 0,
        "probe_plan_v1_sha256": contract.probe_plan_v1_sha256,
        "probe_plan_v2_sha256": contract.probe_plan_v2_sha256,
        "raw_source_opens": open_counts["raw_source_opens"],
        "reconciliation_sha256": sha256_bytes(reconciliation_payload),
        "registry_sha256": contract.registry_sha256,
        "request_count": len(request_rows),
        "request_plan_sha256": sha256_bytes(request_payload),
        "request_receipt_sha256": sha256_bytes(request_receipt_payload),
        "research_holdout_opened": False,
        "research_validation_opened": False,
        "schema_version": "trendstack_006_design_source_receipt.v1",
        "selected_shard_opens": open_counts["selected_shard_opens"],
        "selection_manifest_sha256": contract.selection_manifest_sha256,
        "selection_mapping_sha256": contract.selection_mapping_sha256,
        "source_attempt_id": contract.source_attempt_id,
        "registry_row_index": contract.registry_row_index,
        "registry_row_sha256": contract.registry_row_sha256,
        "stage_path": contract.design_stage_path,
        "stage_role": contract.stage_role,
        "supervisor_review_base_sha256": contract.supervisor_review_base_sha256,
        "supervisor_test_sha256": contract.supervisor_test_sha256,
        "trace_sha256": sha256_bytes(trace_payload),
        "unselected_shard_opens": open_counts["unselected_shard_opens"],
        "validator_test_sha256": contract.validator_test_sha256,
        "validator_tool_sha256": contract.validator_tool_sha256,
        "verdict": PENDING_VERDICT,
    }
    receipt_payload = canonical_json(receipt) + b"\n"
    _exclusive_write(stage / "design_h1_source_receipt.json", receipt_payload)
    if (
        _directory_anchor(_node_info(stage, directory=True)) != stage_identity
        or _directory_anchor(_node_info(output.parent, directory=True)) != parent_identity
        or output.exists()
    ):
        raise ValueError
    _publish_no_replace(stage, output)
    _fsync_directory(output.parent)
    if (
        _directory_anchor(_node_info(output, directory=True)) != stage_identity
        or _directory_anchor(_node_info(output.parent, directory=True)) != parent_identity
    ):
        raise ValueError
    return {**receipt, "pending_receipt_sha256": sha256_bytes(receipt_payload)}


def build_design_source(capability, output_root: Path | str, contract: DesignSourceContract) -> dict[str, object]:
    """Production entrypoint: constants cannot be supplied or overridden."""
    try:
        return _build_design_source(capability, output_root, contract, PRODUCTION_SHAPE)
    except Exception as exc:
        if isinstance(exc, InvalidDesignSource) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignSource(PUBLIC_ERROR) from exc


def build_design_source_for_testing(
    capability,
    output_root: Path | str,
    contract: DesignSourceContract,
    *,
    shape: BuildShape,
) -> dict[str, object]:
    """Explicit fixture-only entrypoint used by temp synthetic tests."""
    try:
        if shape == PRODUCTION_SHAPE:
            raise ValueError
        return _build_design_source(capability, output_root, contract, shape)
    except Exception as exc:
        if isinstance(exc, InvalidDesignSource) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignSource(PUBLIC_ERROR) from exc
