"""Calendar-only, fail-closed parquet custody splitter.

This module deliberately knows only immutable input bindings and calendar
boundaries.  Its public capability exposes DESIGN bytes and nothing else.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

import pyarrow as pa
import pyarrow.parquet as pq


PUBLIC_ERROR = "INVALID_CUSTODY"
PUBLIC_VERDICT = "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
_HEX = frozenset("0123456789ABCDEF")
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


class InvalidCustody(RuntimeError):
    pass


class CustodyAuthority:
    def __init__(
        self,
        *,
        collection_plan_sha256: str,
        source_sha256: str,
        source_bytes: int,
        source_manifest_sha256: str,
        source_footer_length: int,
        source_footer_start: int,
        source_footer_sha256: str,
        clock_sha256: str,
        custodian_tool_sha256: str,
        supervisor_review_base_sha256: str,
        source_attempt_id: str,
        custody_stage_path: str,
        custody_stage_identity: tuple[int, ...],
        stage_role: str,
        source_identity: tuple[int, ...],
    ) -> None:
        self.collection_plan_sha256 = collection_plan_sha256
        self.source_sha256 = source_sha256
        self.source_bytes = source_bytes
        self.source_manifest_sha256 = source_manifest_sha256
        self.source_footer_length = source_footer_length
        self.source_footer_start = source_footer_start
        self.source_footer_sha256 = source_footer_sha256
        self.clock_sha256 = clock_sha256
        self.custodian_tool_sha256 = custodian_tool_sha256
        self.supervisor_review_base_sha256 = supervisor_review_base_sha256
        self.source_attempt_id = source_attempt_id
        self.custody_stage_path = custody_stage_path
        self.custody_stage_identity = tuple(custody_stage_identity)
        self.stage_role = stage_role
        self.source_identity = tuple(source_identity)


class DesignCapability:
    """Opaque access to the immutable public DESIGN projection."""

    __slots__ = ("date_payloads", "receipt_payload", "manifest_payload")

    def __init__(self, date_payloads: dict[str, bytes], receipt_payload: bytes, manifest_payload: bytes) -> None:
        self.date_payloads = {day: bytes(payload) for day, payload in date_payloads.items()}
        self.receipt_payload = bytes(receipt_payload)
        self.manifest_payload = bytes(manifest_payload)

    def __repr__(self) -> str:
        return f"<DesignCapability public-design-only dates={len(self.date_payloads)}>"

    def design_dates(self) -> tuple[str, ...]:
        return tuple(sorted(self.date_payloads))

    def read_design_day(self, day: str) -> bytes:
        try:
            if type(day) is not str or day not in self.date_payloads:
                raise ValueError
            datetime.strptime(day, "%Y-%m-%d")
            return bytes(self.date_payloads[day])
        except Exception as exc:
            raise InvalidCustody(PUBLIC_ERROR) from exc

    def public_receipt_bytes(self) -> bytes:
        try:
            return bytes(self.receipt_payload)
        except Exception as exc:
            raise InvalidCustody(PUBLIC_ERROR) from exc

    def public_manifest_bytes(self) -> bytes:
        try:
            return bytes(self.manifest_payload)
        except Exception as exc:
            raise InvalidCustody(PUBLIC_ERROR) from exc


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in _HEX for char in value)


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


def _regular_directory_chain(path: Path) -> None:
    absolute = path.absolute()
    current = absolute.parent
    while True:
        info = os.lstat(current)
        attributes = int(getattr(info, "st_file_attributes", 0))
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        if not stat.S_ISDIR(info.st_mode) or attributes & reparse:
            raise ValueError
        if current.parent == current:
            return
        current = current.parent


def _stable_read(path: Path) -> bytes:
    _regular_directory_chain(path)
    before = _identity(path)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != before[:2]:
            raise ValueError
        payload = handle.read()
        after_open = os.fstat(handle.fileno())
    after = _identity(path)
    if before != after or int(after_open.st_size) != len(payload):
        raise ValueError
    return payload


def _confined_path(root: Path, relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError
    target = (root / relative_path).resolve(strict=True)
    if target != root and root not in target.parents:
        raise ValueError
    return target


def parquet_footer_sha256(path: Path | str) -> str:
    try:
        return _footer_contract(_stable_read(Path(path)))[2]
    except Exception as exc:
        raise InvalidCustody(PUBLIC_ERROR) from exc


def _validate_authority(authority: CustodyAuthority) -> None:
    if type(authority) is not CustodyAuthority:
        raise ValueError
    expected = {
        "collection_plan_sha256",
        "source_sha256",
        "source_bytes",
        "source_manifest_sha256",
        "source_footer_length",
        "source_footer_start",
        "source_footer_sha256",
        "clock_sha256",
        "custodian_tool_sha256",
        "supervisor_review_base_sha256",
        "source_attempt_id",
        "custody_stage_path",
        "custody_stage_identity",
        "stage_role",
        "source_identity",
    }
    if set(authority.__dict__) != expected:
        raise ValueError
    for key in (
        "collection_plan_sha256",
        "source_sha256",
        "source_manifest_sha256",
        "source_footer_sha256",
        "clock_sha256",
        "custodian_tool_sha256",
        "supervisor_review_base_sha256",
    ):
        if not _valid_sha(authority.__dict__[key]):
            raise ValueError
    for key, value in authority.__dict__.items():
        if key in {"source_bytes", "source_footer_length", "source_footer_start"}:
            if type(value) is not int or value <= 0:
                raise ValueError
    if (
        authority.source_footer_start < 4
        or authority.source_footer_start + authority.source_footer_length + 8 != authority.source_bytes
        or authority.source_footer_sha256 == "92E8403266EF971ED2F4C05523ECB6C10AE5B5723F0F7504E09694663A779727"
        or
        type(authority.source_attempt_id) is not str
        or not authority.source_attempt_id.startswith("HYP004-SOURCE-ATTEMPT-")
        or len(authority.source_attempt_id) != len("HYP004-SOURCE-ATTEMPT-") + 16
        or any(character not in _HEX for character in authority.source_attempt_id[-16:])
        or type(authority.custody_stage_path) is not str
        or not Path(authority.custody_stage_path).is_absolute()
        or type(authority.custody_stage_identity) is not tuple
        or len(authority.custody_stage_identity) != 6
        or any(type(value) is not int for value in authority.custody_stage_identity)
        or authority.stage_role != "CUSTODY"
        or type(authority.source_identity) is not tuple
        or len(authority.source_identity) != 7
        or any(type(value) is not int for value in authority.source_identity)
    ):
        raise ValueError


def _footer_contract(payload: bytes) -> tuple[int, int, str]:
    if type(payload) is not bytes or len(payload) < 12 or payload[:4] != b"PAR1" or payload[-4:] != b"PAR1":
        raise ValueError
    length = int.from_bytes(payload[-8:-4], byteorder="little", signed=False)
    start = len(payload) - 8 - length
    if length <= 0 or start < 4 or start >= len(payload) - 8:
        raise ValueError
    return length, start, _digest(payload[start:])


def _load_clock(payload: bytes, label: str):
    namespace: dict[str, object] = {"__name__": "_bound_calendar_clock", "__file__": label}
    code = compile(payload, label, "exec")
    exec(code, namespace)
    converter = namespace.get("server_to_utc")
    if not callable(converter):
        raise ValueError
    return converter


def _split_for(when: datetime) -> str:
    if when < datetime(2016, 1, 4):
        return "PRE_DESIGN"
    if when < datetime(2021, 1, 1):
        return "DESIGN"
    if when < datetime(2023, 1, 1):
        return "VALIDATION"
    return "HOLDOUT"


def _validate_row(item: dict[str, object], previous: datetime | None, converter) -> datetime:
    utc = item.get("time_utc")
    server = item.get("time_server")
    offset = item.get("utc_offset_h")
    if not isinstance(utc, datetime) or not isinstance(server, datetime) or type(offset) is not int:
        raise ValueError
    if utc.tzinfo is not None or server.tzinfo is not None:
        raise ValueError
    if utc.second != 0 or utc.microsecond != 0 or server.second != 0 or server.microsecond != 0:
        raise ValueError
    if previous is not None and utc <= previous:
        raise ValueError
    converted = converter(server)
    if getattr(converted, "tzinfo", None) is not None:
        converted = converted.replace(tzinfo=None)
    if converted != utc or server - utc != timedelta(hours=offset):
        raise ValueError
    values = [item.get(key) for key in ("open", "high", "low", "close")]
    if any(type(value) is not float or not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError
    open_value, high, low, close = values
    if not (low <= open_value <= high and low <= close <= high):
        raise ValueError
    return utc


def _exclusive_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if _stable_read(path) != payload:
        raise ValueError


def _write_day(attempt: Path, split_name: str, day: str, rows: list[dict[str, object]]) -> dict[str, object]:
    branch = "public" if split_name == "DESIGN" else "sealed"
    relative = Path(branch) / split_name / day / "m1.parquet"
    target = attempt / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=_SOURCE_SCHEMA)
    with target.open("xb") as handle:
        pq.write_table(table, handle, row_group_size=len(rows))
        handle.flush()
        os.fsync(handle.fileno())
    payload = _stable_read(target)
    reopened = pq.ParquetFile(pa.BufferReader(payload))
    if reopened.metadata.num_rows != len(rows) or reopened.metadata.num_row_groups != 1:
        raise ValueError
    return {
        "date": day,
        "relative_path": relative.as_posix(),
        "rows": len(rows),
        "bytes": len(payload),
        "sha256": _digest(payload),
        "split": split_name,
    }


def _rows_from_payload(payload: bytes) -> Iterable[dict[str, object]]:
    parquet = pq.ParquetFile(pa.BufferReader(payload))
    if not parquet.schema_arrow.equals(_SOURCE_SCHEMA, check_metadata=False):
        raise ValueError
    for batch in parquet.iter_batches(batch_size=65_536):
        yield from batch.to_pylist()


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


def _directory_anchor(identity: tuple[int, ...]) -> tuple[int, int, int, int]:
    if type(identity) is not tuple or len(identity) != 6 or any(type(value) is not int for value in identity):
        raise ValueError
    return (identity[0], identity[1], identity[2], identity[5])


def _publish_no_replace(attempt: Path, output: Path, parent_identity: tuple[int, ...], attempt_identity: tuple[int, ...]) -> None:
    if (
        _directory_anchor(_directory_identity(output.parent)) != _directory_anchor(parent_identity)
        or _directory_anchor(_directory_identity(attempt)) != _directory_anchor(attempt_identity)
    ):
        raise ValueError
    try:
        os.lstat(output)
    except FileNotFoundError:
        pass
    else:
        raise ValueError
    os.rename(attempt, output)
    if _directory_anchor(_directory_identity(output)) != _directory_anchor(attempt_identity):
        raise ValueError


def run_custody(
    source_path: Path | str,
    source_manifest_path: Path | str,
    collection_plan_path: Path | str,
    clock_path: Path | str,
    output_root: Path | str,
    authority: CustodyAuthority,
    lifecycle_hook: Callable[[str], None] | None = None,
) -> tuple[dict[str, object], DesignCapability]:
    output = Path(output_root).absolute()
    attempt = Path(authority.custody_stage_path).absolute()
    try:
        _validate_authority(authority)
        _regular_directory_chain(output)
        parent_identity = _directory_identity(output.parent)
        if (
            output.exists()
            or attempt.parent != output.parent
            or attempt.name != "." + output.name + ".attempt-" + authority.source_attempt_id
            or attempt.resolve(strict=True) != attempt
            or _directory_identity(attempt) != authority.custody_stage_identity
        ):
            raise ValueError
        with os.scandir(attempt) as stage_entries:
            if next(stage_entries, None) is not None:
                raise ValueError
        source = Path(source_path).absolute()
        manifest = Path(source_manifest_path).absolute()
        plan = Path(collection_plan_path).absolute()
        clock = Path(clock_path).absolute()
        paths = (source, manifest, plan, clock)
        if len({str(path.resolve(strict=True)).lower() for path in paths}) != len(paths):
            raise ValueError
        initial_identity = tuple(authority.source_identity)
        _regular_directory_chain(source)
        if lifecycle_hook is not None:
            lifecycle_hook("after_source_lstat")
        if _identity(source) != initial_identity or _directory_identity(attempt) != authority.custody_stage_identity:
            raise ValueError
        manifest_payload = _stable_read(manifest)
        plan_payload = _stable_read(plan)
        clock_payload = _stable_read(clock)
        if lifecycle_hook is not None:
            lifecycle_hook("before_source_open")
        if _directory_identity(attempt) != authority.custody_stage_identity:
            raise ValueError
        source_payload = _stable_read(source)
        if lifecycle_hook is not None:
            lifecycle_hook("after_source_open")
        if _directory_identity(attempt) != authority.custody_stage_identity:
            raise ValueError
        observed_footer_length, observed_footer_start, observed_footer_sha256 = _footer_contract(source_payload)
        if (
            _digest(source_payload) != authority.source_sha256
            or len(source_payload) != authority.source_bytes
            or observed_footer_length != authority.source_footer_length
            or observed_footer_start != authority.source_footer_start
            or observed_footer_sha256 != authority.source_footer_sha256
            or _digest(manifest_payload) != authority.source_manifest_sha256
            or _digest(plan_payload) != authority.collection_plan_sha256
            or _digest(clock_payload) != authority.clock_sha256
        ):
            raise ValueError
        converter = _load_clock(clock_payload, str(clock))
        attempt_identity = authority.custody_stage_identity
        entries: list[dict[str, object]] = []
        current_key: tuple[str, str] | None = None
        current_rows: list[dict[str, object]] = []
        previous: datetime | None = None
        decoded = 0
        for item in _rows_from_payload(source_payload):
            utc = _validate_row(item, previous, converter)
            previous = utc
            key = (_split_for(utc), utc.date().isoformat())
            if current_key is not None and key != current_key:
                entries.append(_write_day(attempt, current_key[0], current_key[1], current_rows))
                current_rows = []
            current_key = key
            current_rows.append(item)
            decoded += 1
        if current_key is not None:
            entries.append(_write_day(attempt, current_key[0], current_key[1], current_rows))
        if decoded == 0 or sum(int(entry["rows"]) for entry in entries) != decoded:
            raise ValueError
        if lifecycle_hook is not None:
            lifecycle_hook("after_source_decode")
        if (
            _identity(source) != initial_identity
            or _directory_anchor(_directory_identity(attempt)) != _directory_anchor(attempt_identity)
        ):
            raise ValueError

        design_entries = {str(entry["date"]): entry for entry in entries if entry["split"] == "DESIGN"}
        public_rows = [
            {
                "bytes": entry["bytes"],
                "date": entry["date"],
                "relative_path": entry["relative_path"],
                "rows": entry["rows"],
                "sha256": entry["sha256"],
            }
            for entry in sorted(design_entries.values(), key=lambda value: str(value["date"]))
        ]
        public_manifest = b"".join(_canonical(entry) + b"\n" for entry in public_rows)
        _exclusive_write(attempt / "public" / "design_manifest.jsonl", public_manifest)
        private_manifest = b"".join(
            _canonical(entry) + b"\n" for entry in sorted(entries, key=lambda value: (str(value["date"]), str(value["split"])))
        )
        _exclusive_write(attempt / "private" / "custody_manifest.jsonl", private_manifest)
        opaque_digest = _digest(private_manifest)
        split_counts = {
            split_name: sum(int(entry["rows"]) for entry in entries if entry["split"] == split_name)
            for split_name in ("PRE_DESIGN", "DESIGN", "VALIDATION", "HOLDOUT")
        }
        private_receipt = {
            "collection_plan_sha256": authority.collection_plan_sha256,
            "custody_manifest_sha256": opaque_digest,
            "custodian_tool_sha256": authority.custodian_tool_sha256,
            "exact_once_status": "PASS",
            "schema_version": "splitvault_002_private_custody_receipt.v1",
            "source_attempt_id": authority.source_attempt_id,
            "source_bytes": authority.source_bytes,
            "source_footer_length": authority.source_footer_length,
            "source_footer_start": authority.source_footer_start,
            "source_footer_sha256": authority.source_footer_sha256,
            "source_rows": decoded,
            "source_sha256": authority.source_sha256,
            "split_rows": split_counts,
            "stage_path": authority.custody_stage_path,
            "stage_role": authority.stage_role,
            "supervisor_review_base_sha256": authority.supervisor_review_base_sha256,
        }
        private_receipt_payload = _canonical(private_receipt) + b"\n"
        _exclusive_write(attempt / "private" / "custody_receipt.json", private_receipt_payload)
        receipt: dict[str, object] = {
            "collection_plan_sha256": authority.collection_plan_sha256,
            "custodian_full_corpus_decoded": True,
            "custodian_tool_sha256": authority.custodian_tool_sha256,
            "design_dates": len(design_entries),
            "design_manifest_sha256": _digest(public_manifest),
            "design_rows": sum(int(entry["rows"]) for entry in design_entries.values()),
            "exact_once_status": "PASS",
            "private_custody_digest": opaque_digest,
            "private_custody_receipt_sha256": _digest(private_receipt_payload),
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "source_bytes": authority.source_bytes,
            "source_footer_length": authority.source_footer_length,
            "source_footer_start": authority.source_footer_start,
            "source_footer_sha256": authority.source_footer_sha256,
            "source_sha256": authority.source_sha256,
            "source_attempt_id": authority.source_attempt_id,
            "stage_path": authority.custody_stage_path,
            "stage_role": authority.stage_role,
            "supervisor_review_base_sha256": authority.supervisor_review_base_sha256,
            "verdict": PUBLIC_VERDICT,
        }
        public_receipt_payload = _canonical(receipt) + b"\n"
        _exclusive_write(attempt / "public" / "design_receipt.json", public_receipt_payload)
        design_payloads = {
            day: _stable_read(attempt / str(entry["relative_path"]))
            for day, entry in design_entries.items()
        }
        if lifecycle_hook is not None:
            lifecycle_hook("before_publish")
        _publish_no_replace(attempt, output, parent_identity, attempt_identity)
        capability = DesignCapability(design_payloads, public_receipt_payload, public_manifest)
        return receipt, capability
    except Exception as exc:
        if isinstance(exc, InvalidCustody) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidCustody(PUBLIC_ERROR) from exc
