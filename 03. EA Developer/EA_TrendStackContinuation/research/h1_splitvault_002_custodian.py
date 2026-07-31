"""HYP006 H1 source custody guards.

This module exposes no path reader for the real H1 corpus.  The caller must
provide an already authorized byte reader, and the reader can fire only after a
durable ATTEMPT_CONSUMED marker has been verified.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import ctypes
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


PUBLIC_ERROR = "INVALID_CUSTODY"
REGISTRY_ROW_INDEX = 282
REGISTRY_ROW_SHA256 = "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E"
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


class InvalidCustody(RuntimeError):
    pass


@dataclass(frozen=True)
class CustodyAuthority:
    source_sha256: str
    source_bytes: int
    source_footer_length: int
    source_footer_start: int
    source_footer_sha256: str
    source_manifest_sha256: str
    clock_sha256: str
    collection_plan_v1_sha256: str
    collection_plan_v2_sha256: str
    registry_row_index: int
    registry_row_sha256: str
    source_attempt_id: str
    expected_source_rows: int = 71785
    expected_source_row_groups: int = 1
    marker_bindings: tuple[tuple[str, object], ...] = ()
    expected_split_rows: tuple[tuple[str, int], ...] = ()
    clock_converter: object = None


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in _HEX for char in value)


def _valid_attempt_id(value: object) -> bool:
    prefix = "HYP006-SOURCE-ATTEMPT-"
    return (
        type(value) is str
        and value.startswith(prefix)
        and len(value) == len(prefix) + 16
        and all(char in _HEX for char in value[len(prefix) :])
    )


def _validate_authority(authority: CustodyAuthority) -> None:
    if type(authority) is not CustodyAuthority:
        raise ValueError
    for key in (
        "source_sha256",
        "source_footer_sha256",
        "source_manifest_sha256",
        "clock_sha256",
        "collection_plan_v1_sha256",
        "collection_plan_v2_sha256",
        "registry_row_sha256",
    ):
        if not _valid_sha(getattr(authority, key)):
            raise ValueError
    if (
        authority.registry_row_index != REGISTRY_ROW_INDEX
        or authority.registry_row_sha256 != REGISTRY_ROW_SHA256
        or not _valid_attempt_id(authority.source_attempt_id)
        or type(authority.source_bytes) is not int
        or authority.source_bytes <= 12
        or type(authority.source_footer_length) is not int
        or authority.source_footer_length <= 0
        or type(authority.source_footer_start) is not int
        or authority.source_footer_start < 4
        or authority.source_footer_start + authority.source_footer_length + 8 != authority.source_bytes
        or type(authority.expected_source_rows) is not int
        or authority.expected_source_rows <= 0
        or authority.expected_source_row_groups != 1
        or type(authority.marker_bindings) is not tuple
        or type(authority.expected_split_rows) is not tuple
        or (authority.clock_converter is not None and not callable(authority.clock_converter))
    ):
        raise ValueError
    if any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        for item in authority.marker_bindings
    ):
        raise ValueError
    split_names = {"PRE_DESIGN", "DESIGN", "VALIDATION", "HOLDOUT"}
    if authority.expected_split_rows and (
        {item[0] for item in authority.expected_split_rows} != split_names
        or any(type(item[1]) is not int or item[1] < 0 for item in authority.expected_split_rows)
    ):
        raise ValueError


def _footer(payload: bytes) -> tuple[int, int, str]:
    if type(payload) is not bytes or len(payload) < 12 or payload[:4] != b"PAR1" or payload[-4:] != b"PAR1":
        raise ValueError
    length = int.from_bytes(payload[-8:-4], "little", signed=False)
    start = len(payload) - 8 - length
    if length <= 0 or start < 4:
        raise ValueError
    return length, start, _digest(payload[start:])


def verify_source_payload(payload: bytes, authority: CustodyAuthority) -> dict[str, object]:
    try:
        _validate_authority(authority)
        length, start, footer_sha = _footer(payload)
        parquet = pq.ParquetFile(pa.BufferReader(payload))
        if (
            _digest(payload) != authority.source_sha256
            or len(payload) != authority.source_bytes
            or length != authority.source_footer_length
            or start != authority.source_footer_start
            or footer_sha != authority.source_footer_sha256
            or not parquet.schema_arrow.equals(EXPECTED_SCHEMA, check_metadata=False)
            or parquet.metadata.num_row_groups != authority.expected_source_row_groups
            or parquet.metadata.num_rows != authority.expected_source_rows
        ):
            raise ValueError
        previous = None
        seen = set()
        for row in parquet.read().to_pylist():
            utc = row["time_utc"]
            server = row["time_server"]
            offset = row["utc_offset_h"]
            if (
                not isinstance(utc, datetime)
                or not isinstance(server, datetime)
                or type(offset) is not int
                or utc in seen
                or (previous is not None and utc <= previous)
                or server - utc != timedelta(hours=offset)
                or (
                    authority.clock_converter is not None
                    and authority.clock_converter(server) != utc
                )
                or any(row.get(name) is None for name in EXPECTED_SCHEMA.names)
            ):
                raise ValueError
            seen.add(utc)
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
        return {
            "registry_row_index": authority.registry_row_index,
            "registry_row_sha256": authority.registry_row_sha256,
            "schema_status": "PASS_EXACT_ARROW_SCHEMA_BID_CLOSED_H1",
            "source_attempt_id": authority.source_attempt_id,
            "source_bytes": len(payload),
            "source_footer_length": length,
            "source_footer_sha256": footer_sha,
            "source_footer_start": start,
            "source_sha256": _digest(payload),
        }
    except Exception as exc:
        if isinstance(exc, InvalidCustody) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidCustody(PUBLIC_ERROR) from exc


class RawSourceCapability:
    def __init__(self, reader, authority: CustodyAuthority) -> None:
        if not callable(reader):
            raise InvalidCustody(PUBLIC_ERROR)
        _validate_authority(authority)
        self._reader = reader
        self._authority = authority
        self._opened = False
        self._attempted_opens = 0

    def _verify_marker(self, marker: dict[str, object]) -> None:
        if (
            type(marker) is not dict
            or marker.get("verdict") != "ATTEMPT_CONSUMED"
            or marker.get("source_attempt_id") != self._authority.source_attempt_id
            or marker.get("registry_row_index") != REGISTRY_ROW_INDEX
            or marker.get("registry_row_sha256") != REGISTRY_ROW_SHA256
            or marker.get("source_sha256") != self._authority.source_sha256
            or any(marker.get(key) != value for key, value in self._authority.marker_bindings)
        ):
            raise ValueError
        required = {
            "verdict",
            "source_attempt_id",
            "registry_row_index",
            "registry_row_sha256",
            "source_sha256",
            *(key for key, _value in self._authority.marker_bindings),
        }
        if set(marker) != required:
            raise ValueError

    def open_after_marker(self, marker: dict[str, object]) -> bytes:
        try:
            self._verify_marker(marker)
            if self._opened:
                raise ValueError
            self._opened = True
            self._attempted_opens += 1
            payload = self._reader()
            verify_source_payload(payload, self._authority)
            return payload
        except Exception as exc:
            if isinstance(exc, InvalidCustody) and str(exc) == PUBLIC_ERROR:
                raise
            raise InvalidCustody(PUBLIC_ERROR) from exc

    def attempted_open_count(self) -> int:
        return self._attempted_opens


class SelectedShardCapability:
    def __init__(self, *, selected_dates: tuple[str, ...], selected_hashes: dict[str, str], day_reader) -> None:
        if (
            type(selected_dates) is not tuple
            or type(selected_hashes) is not dict
            or set(selected_dates) != set(selected_hashes)
            or tuple(sorted(selected_dates)) != selected_dates
            or any(not _valid_sha(value) for value in selected_hashes.values())
            or not callable(day_reader)
        ):
            raise InvalidCustody(PUBLIC_ERROR)
        self._dates = selected_dates
        self._hashes = dict(selected_hashes)
        self._reader = day_reader
        self._opened: set[str] = set()
        self._attempted = {day: 0 for day in selected_dates}

    def design_dates(self) -> tuple[str, ...]:
        return self._dates

    def read_design_day(self, day: str) -> bytes:
        try:
            if day not in self._hashes or day in self._opened:
                raise ValueError
            self._opened.add(day)
            self._attempted[day] += 1
            payload = self._reader(day)
            if type(payload) is not bytes or _digest(payload) != self._hashes[day]:
                raise ValueError
            return payload
        except Exception as exc:
            raise InvalidCustody(PUBLIC_ERROR) from exc

    def attempted_open_counts(self) -> dict[str, int]:
        return dict(self._attempted)


class DesignCapability:
    def __init__(
        self,
        selected_hashes: dict[str, str],
        day_reader,
        public_receipt: bytes,
        public_manifest: bytes,
    ) -> None:
        if not callable(day_reader) or any(not _valid_sha(value) for value in selected_hashes.values()):
            raise InvalidCustody(PUBLIC_ERROR)
        self._hashes = dict(selected_hashes)
        self._reader = day_reader
        self._receipt = bytes(public_receipt)
        self._manifest = bytes(public_manifest)
        self._opened = {day: 0 for day in self._hashes}
        self._consumed: set[str] = set()

    def design_dates(self) -> tuple[str, ...]:
        return tuple(sorted(self._hashes))

    def read_design_day(self, day: str) -> bytes:
        if day not in self._hashes or day in self._consumed:
            raise InvalidCustody(PUBLIC_ERROR)
        self._consumed.add(day)
        self._opened[day] += 1
        try:
            payload = self._reader(day)
            if type(payload) is not bytes or _digest(payload) != self._hashes[day]:
                raise ValueError
            return payload
        except Exception as exc:
            raise InvalidCustody(PUBLIC_ERROR) from exc

    def public_receipt_bytes(self) -> bytes:
        return self._receipt

    def public_manifest_bytes(self) -> bytes:
        return self._manifest

    def open_counts(self) -> dict[str, int]:
        return dict(self._opened)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


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
    first = kernel32.FindFirstStreamW
    first.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    first.restype = ctypes.c_void_p
    handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        if ctypes.get_last_error() not in (1, 38):
            raise OSError(ctypes.get_last_error(), "FindFirstStreamW")
        return
    try:
        names = [data.name]
        next_stream = kernel32.FindNextStreamW
        next_stream.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        next_stream.restype = ctypes.c_int
        while next_stream(handle, ctypes.byref(data)):
            names.append(data.name)
    finally:
        close = kernel32.FindClose
        close.argtypes = [ctypes.c_void_p]
        close.restype = ctypes.c_int
        close(handle)
    if names != ["::$DATA"]:
        raise ValueError


def _node_info(path: Path, *, directory: bool) -> os.stat_result:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    if path.is_symlink() or attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
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


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (int(info.st_dev), int(info.st_ino), int(info.st_size), int(info.st_mtime_ns), int(info.st_ctime_ns))


def _directory_anchor(info: os.stat_result) -> tuple[int, int, int, int]:
    return (int(info.st_dev), int(info.st_ino), int(info.st_mode), int(getattr(info, "st_file_attributes", 0)))


def _stable_read(path: Path) -> bytes:
    _directory_chain(path)
    before = _node_info(path, directory=False)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != (int(before.st_dev), int(before.st_ino)):
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    if _file_identity(before) != _file_identity(_node_info(path, directory=False)) or int(final.st_size) != len(payload):
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
    while not os.path.lexists(current):
        missing.append(current)
        current = current.parent
    _node_info(current, directory=True)
    for directory in reversed(missing):
        directory.mkdir()
        _node_info(directory, directory=True)
        _fsync_directory(directory.parent)


def _exclusive_write(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes or os.path.lexists(path):
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


def _split_for(utc: datetime) -> str:
    if utc < datetime(2016, 1, 4):
        return "PRE_DESIGN"
    if utc < datetime(2021, 1, 1):
        return "DESIGN"
    if utc < datetime(2023, 1, 1):
        return "VALIDATION"
    return "HOLDOUT"


def _write_day(stage: Path, split_name: str, day: str, rows: list[dict[str, object]]) -> dict[str, object]:
    branch = "public" if split_name == "DESIGN" else "sealed"
    relative = Path(branch) / split_name / day / "h1.parquet"
    path = stage / relative
    table = pa.Table.from_pylist(rows, schema=EXPECTED_SCHEMA)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, row_group_size=table.num_rows)
    payload = sink.getvalue().to_pybytes()
    _exclusive_write(path, payload)
    return {
        "bytes": len(payload),
        "date": day,
        "relative_path": relative.as_posix(),
        "rows": table.num_rows,
        "sha256": _digest(payload),
        "split": split_name,
    }


def run_custody(
    source_reader,
    *,
    source_manifest_payload: bytes,
    clock_payload: bytes,
    output_root: Path | str,
    stage_root: Path | str,
    authority: CustodyAuthority,
    marker: dict[str, object],
) -> tuple[dict[str, object], DesignCapability]:
    try:
        if _digest(source_manifest_payload) != authority.source_manifest_sha256 or _digest(clock_payload) != authority.clock_sha256:
            raise ValueError
        manifest_text = source_manifest_payload.decode("utf-8", errors="ignore").lower()
        if not all(token in manifest_text for token in ("eurusd", "h1", "closed", "bid")):
            raise ValueError
        output = Path(output_root).absolute()
        stage = Path(stage_root).absolute()
        _directory_chain(output)
        if (
            os.path.lexists(output)
            or os.path.lexists(stage)
            or stage.parent != output.parent
            or stage.name != "." + output.name + ".attempt-" + authority.source_attempt_id
        ):
            raise ValueError
        parent_anchor = _directory_anchor(_node_info(output.parent, directory=True))
        stage.mkdir(parents=False)
        _fsync_directory(stage.parent)
        stage_anchor = _directory_anchor(_node_info(stage, directory=True))
        raw = RawSourceCapability(source_reader, authority)
        payload = raw.open_after_marker(marker)
        parquet = pq.ParquetFile(pa.BufferReader(payload))
        entries: list[dict[str, object]] = []
        current_key = None
        current_rows: list[dict[str, object]] = []
        for row in parquet.read().to_pylist():
            utc = row["time_utc"]
            key = (_split_for(utc), utc.date().isoformat())
            if current_key is not None and key != current_key:
                entries.append(_write_day(stage, current_key[0], current_key[1], current_rows))
                current_rows = []
            current_key = key
            current_rows.append(row)
        if current_key is not None:
            entries.append(_write_day(stage, current_key[0], current_key[1], current_rows))
        if sum(int(entry["rows"]) for entry in entries) != authority.expected_source_rows:
            raise ValueError
        split_rows = {
            split: sum(int(entry["rows"]) for entry in entries if entry["split"] == split)
            for split in ("PRE_DESIGN", "DESIGN", "VALIDATION", "HOLDOUT")
        }
        if authority.expected_split_rows and split_rows != dict(authority.expected_split_rows):
            raise ValueError
        public_rows = [
            {
                "bytes": entry["bytes"],
                "date": entry["date"],
                "relative_path": entry["relative_path"],
                "rows": entry["rows"],
                "schema_version": "h1_splitvault_002_public_design_shard.v1",
                "sha256": entry["sha256"],
            }
            for entry in entries
            if entry["split"] == "DESIGN"
        ]
        public_rows.sort(key=lambda row: str(row["date"]))
        public_manifest = b"".join(_canonical(row) + b"\n" for row in public_rows)
        receipt = {
            "collection_id": "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002",
            "design_dates": len(public_rows),
            "design_manifest_sha256": _digest(public_manifest),
            "raw_source_opens": 1,
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "schema_version": "h1_splitvault_002_public_receipt.v1",
            "source_attempt_id": authority.source_attempt_id,
            "source_rows": authority.expected_source_rows,
            "unselected_shard_opens": 0,
            "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
        }
        receipt_payload = _canonical(receipt) + b"\n"
        _exclusive_write(stage / "public" / "design_manifest.jsonl", public_manifest)
        _exclusive_write(stage / "public" / "design_receipt.json", receipt_payload)
        if (
            _directory_anchor(_node_info(stage, directory=True)) != stage_anchor
            or _directory_anchor(_node_info(output.parent, directory=True)) != parent_anchor
            or os.path.lexists(output)
        ):
            raise ValueError
        _publish_no_replace(stage, output)
        _fsync_directory(output.parent)
        if (
            _directory_anchor(_node_info(output, directory=True)) != stage_anchor
            or _directory_anchor(_node_info(output.parent, directory=True)) != parent_anchor
        ):
            raise ValueError
        hashes = {str(row["date"]): str(row["sha256"]) for row in public_rows}
        paths = {str(row["date"]): str(row["relative_path"]) for row in public_rows}
        return receipt, DesignCapability(
            hashes,
            lambda day: _stable_read(output / paths[day]),
            receipt_payload,
            public_manifest,
        )
    except Exception as exc:
        if isinstance(exc, InvalidCustody) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidCustody(PUBLIC_ERROR) from exc
