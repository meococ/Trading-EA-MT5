"""Fail-closed HYP007 12:00 UTC DESIGN source projector.

Importing this module is inert.  Production payload authority is intentionally
absent; callers must supply already-reviewed metadata bytes and a bounded shard
reader.  The callable surface is also used by the synthetic acceptance suite.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import types
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-007"
COLLECTION_ID = "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002"
PUBLIC_RECEIPT_SCHEMA = "h1_splitvault_002_public_receipt.v1"
PUBLIC_MANIFEST_SCHEMA = "h1_splitvault_002_public_design_shard.v1"
SELECTION_SCHEMA = "trendstack_006_design_date_selection.v1"
DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
HEX = frozenset("0123456789ABCDEF")

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
METADATA_FILES = (
    "projection_requests.jsonl",
    "projection_request_receipt.json",
    "design_1200_manifest.jsonl",
    "design_1200_source_trace.jsonl",
    "design_1200_reconciliation.json",
    "design_1200_projector_receipt.json",
)
PUBLIC_RECEIPT_FIELDS = {
    "collection_id", "design_dates", "design_manifest_sha256", "raw_source_opens",
    "research_holdout_opened", "research_validation_opened", "schema_version",
    "source_attempt_id", "source_rows", "unselected_shard_opens", "verdict",
}
PUBLIC_MANIFEST_FIELDS = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}


class InvalidProjection(RuntimeError):
    pass


@dataclass(frozen=True)
class DecodedShard:
    schema: tuple[tuple[str, str, bool], ...]
    row_groups: int
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class ProjectionAuthority:
    projection_attempt_id: str
    active_contract_sha256: str
    task_packet_sha256: str
    public_receipt_sha256: str
    public_manifest_sha256: str
    selection_manifest_sha256: str


@dataclass(frozen=True)
class ProjectionShape:
    expected_dates: int
    expected_unselected_dates: int
    expected_date_set_sha256: str
    first_date: str
    last_date: str


PRODUCTION_SHAPE = ProjectionShape(
    expected_dates=1297,
    expected_unselected_dates=258,
    expected_date_set_sha256="4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A",
    first_date="2016-01-04",
    last_date="2020-12-31",
)


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise InvalidProjection("INVALID_PROJECTION")
    return hashlib.sha256(payload).hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in HEX for char in value)


def _valid_attempt(value: object) -> bool:
    prefix = "HYP007-SOURCE-PROJECTION-"
    return (
        type(value) is str
        and value.startswith(prefix)
        and len(value) == len(prefix) + 16
        and all(char in HEX for char in value[len(prefix):])
    )


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except Exception as exc:
        raise InvalidProjection("INVALID_PROJECTION") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json_load(payload: bytes) -> object:
    if type(payload) is not bytes:
        raise ValueError
    text = payload.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def parse_object(payload: bytes) -> dict[str, object]:
    try:
        if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
            raise ValueError
        value = _json_load(payload)
        if type(value) is not dict or canonical_json(value) + b"\n" != payload:
            raise ValueError
        return value
    except Exception as exc:
        raise InvalidProjection("INVALID_PROJECTION") from exc


def parse_jsonl(payload: bytes) -> list[dict[str, object]]:
    try:
        if type(payload) is not bytes or not payload or not payload.endswith(b"\n") or b"\n\n" in payload:
            raise ValueError
        rows = []
        for line in payload.splitlines():
            value = _json_load(line)
            if type(value) is not dict or canonical_json(value) != line:
                raise ValueError
            rows.append(value)
        return rows
    except Exception as exc:
        raise InvalidProjection("INVALID_PROJECTION") from exc


def _reparse(info: os.stat_result) -> bool:
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
    """Read one regular, single-link file without accepting path indirection."""

    try:
        path = Path(path_value).absolute()
        root = Path(allowed_root_value).absolute()
        if not _inside(path, root) or path == root:
            raise ValueError
        relative = path.relative_to(root)
        if any(":" in component for component in relative.parts):
            raise ValueError
        current = root
        root_info = os.lstat(root)
        if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink() or _reparse(root_info):
            raise ValueError
        directory_anchors = [(root, _identity(root_info))]
        for component in relative.parts[:-1]:
            current = current / component
            info = os.lstat(current)
            if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _reparse(info):
                raise ValueError
            directory_anchors.append((current, _identity(info)))
        before = os.lstat(path)
        if (
            not stat.S_ISREG(before.st_mode)
            or path.is_symlink()
            or _reparse(before)
            or int(before.st_nlink) != 1
        ):
            raise ValueError
        anchor = _identity(before)
        flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if _identity(opened) != anchor:
                raise ValueError
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
        if (
            _identity(final) != anchor
            or _identity(os.lstat(path)) != anchor
            or len(payload) != anchor[2]
            or any(_identity(os.lstat(directory)) != identity for directory, identity in directory_anchors)
        ):
            raise ValueError
        return payload
    except Exception as exc:
        raise InvalidProjection("INVALID_PROJECTION") from exc


def _exclusive_write(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes or os.path.lexists(path):
        raise InvalidProjection("INVALID_PROJECTION")
    path.parent.mkdir(parents=True, exist_ok=True)
    parent_info = os.lstat(path.parent)
    if not stat.S_ISDIR(parent_info.st_mode) or path.parent.is_symlink() or _reparse(parent_info):
        raise InvalidProjection("INVALID_PROJECTION")
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if stable_read_regular(path, path.parent) != payload:
        raise InvalidProjection("INVALID_PROJECTION")


def _validate_authority(authority: ProjectionAuthority, shape: ProjectionShape) -> None:
    if (
        type(authority) is not ProjectionAuthority
        or not _valid_attempt(authority.projection_attempt_id)
        or any(not _valid_sha(getattr(authority, field)) for field in (
            "active_contract_sha256", "task_packet_sha256", "public_receipt_sha256",
            "public_manifest_sha256", "selection_manifest_sha256",
        ))
        or type(shape) is not ProjectionShape
        or type(shape.expected_dates) is not int
        or shape.expected_dates <= 0
        or type(shape.expected_unselected_dates) is not int
        or shape.expected_unselected_dates < 0
        or not _valid_sha(shape.expected_date_set_sha256)
    ):
        raise InvalidProjection("INVALID_PROJECTION")


def _date(day: object) -> str:
    if type(day) is not str or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
        raise ValueError
    return day


def _metadata_mapping(
    authority: ProjectionAuthority,
    shape: ProjectionShape,
    public_receipt: bytes,
    public_manifest: bytes,
    selection_manifest: bytes,
) -> tuple[tuple[str, ...], dict[str, dict[str, object]], int]:
    if (
        sha256_bytes(public_receipt) != authority.public_receipt_sha256
        or sha256_bytes(public_manifest) != authority.public_manifest_sha256
        or sha256_bytes(selection_manifest) != authority.selection_manifest_sha256
    ):
        raise ValueError
    receipt = parse_object(public_receipt)
    if (
        set(receipt) != PUBLIC_RECEIPT_FIELDS
        or receipt["collection_id"] != COLLECTION_ID
        or receipt["schema_version"] != PUBLIC_RECEIPT_SCHEMA
        or receipt["design_manifest_sha256"] != sha256_bytes(public_manifest)
        or type(receipt["design_dates"]) is not int
        or receipt["raw_source_opens"] != 1
        or receipt["unselected_shard_opens"] != 0
        or receipt["research_validation_opened"] is not False
        or receipt["research_holdout_opened"] is not False
    ):
        raise ValueError
    selection_rows = parse_jsonl(selection_manifest)
    dates = tuple(row.get("date") for row in selection_rows)
    if any(set(row) != {"date", "schema_version"} or row["schema_version"] != SELECTION_SCHEMA for row in selection_rows):
        raise ValueError
    dates = tuple(_date(day) for day in dates)
    date_set = sha256_bytes(DATE_SET_PREFIX + b"".join(day.encode("ascii") + b"\n" for day in dates))
    if (
        dates != tuple(sorted(set(dates)))
        or len(dates) != shape.expected_dates
        or dates[0] != shape.first_date
        or dates[-1] != shape.last_date
        or date_set != shape.expected_date_set_sha256
    ):
        raise ValueError
    manifest_rows = parse_jsonl(public_manifest)
    mapping = {}
    for row in manifest_rows:
        day = _date(row.get("date"))
        if (
            set(row) != PUBLIC_MANIFEST_FIELDS
            or row["schema_version"] != PUBLIC_MANIFEST_SCHEMA
            or day in mapping
            or row["relative_path"] != f"public/DESIGN/{day}/h1.parquet"
            or type(row["bytes"]) is not int
            or row["bytes"] <= 0
            or type(row["rows"]) is not int
            or row["rows"] <= 0
            or not _valid_sha(row["sha256"])
        ):
            raise ValueError
        mapping[day] = dict(row)
    if (
        tuple(mapping) != tuple(sorted(mapping))
        or len(mapping) != receipt["design_dates"]
        or not set(dates).issubset(mapping)
        or len(mapping) - len(dates) != shape.expected_unselected_dates
    ):
        raise ValueError
    return dates, mapping, date_set


def _validate_row(row: dict[str, object], day: str, server_offset_hours, server_to_utc) -> None:
    if type(row) is not dict or set(row) != {field[0] for field in EXPECTED_ARROW_SCHEMA} or any(value is None for value in row.values()):
        raise ValueError
    utc = row["time_utc"]
    server = row["time_server"]
    offset = row["utc_offset_h"]
    if (
        type(utc) is not datetime
        or type(server) is not datetime
        or utc.tzinfo is not None
        or server.tzinfo is not None
        or type(offset) is not int
        or isinstance(offset, bool)
        or not -128 <= offset <= 127
        or server - utc != timedelta(hours=offset)
        or server_offset_hours(server) != offset
        or server_to_utc(server) != utc
    ):
        raise ValueError
    for name in ("open", "high", "low", "close"):
        value = row[name]
        if type(value) is not float or not math.isfinite(value) or value <= 0:
            raise ValueError
    if not (row["low"] <= row["open"] <= row["high"] and row["low"] <= row["close"] <= row["high"]):
        raise ValueError
    for name, maximum in (("tick_volume", 2**64 - 1), ("spread", 2**31 - 1), ("real_volume", 2**64 - 1)):
        value = row[name]
        if type(value) is not int or isinstance(value, bool) or not 0 <= value <= maximum:
            raise ValueError
    if utc != datetime.fromisoformat(day + "T12:00:00"):
        raise ValueError


def _validate_decoded_input(decoded: DecodedShard, day: str, expected_rows: int, server_offset_hours, server_to_utc) -> dict[str, object]:
    if type(decoded) is not DecodedShard or decoded.schema != EXPECTED_ARROW_SCHEMA or decoded.row_groups != 1:
        raise ValueError
    if len(decoded.rows) != expected_rows or any(type(row) is not dict for row in decoded.rows):
        raise ValueError
    utc_values = [row.get("time_utc") for row in decoded.rows]
    if any(type(value) is not datetime for value in utc_values) or utc_values != sorted(utc_values) or len(set(utc_values)) != len(utc_values):
        raise ValueError
    matches = [row for row in decoded.rows if row.get("time_utc") == datetime.fromisoformat(day + "T12:00:00")]
    if len(matches) != 1:
        raise ValueError
    _validate_row(matches[0], day, server_offset_hours, server_to_utc)
    return dict(matches[0])


def _data_tree(manifest_rows: list[dict[str, object]]) -> str:
    document = {
        "files": [
            {"relative_path": row["relative_path"], "bytes": row["bytes"], "sha256": row["sha256"]}
            for row in sorted(manifest_rows, key=lambda item: item["relative_path"])
        ],
        "schema_version": "trendstack_007_projection_data_tree.v1",
    }
    return sha256_bytes(canonical_json(document))


def project_stage_synthetic(
    *,
    stage_root: Path | str,
    authority: ProjectionAuthority,
    shape: ProjectionShape,
    public_receipt: bytes,
    public_manifest: bytes,
    selection_manifest: bytes,
    shard_reader: Callable[[str, str], bytes],
    decode_input: Callable[[bytes], DecodedShard],
    encode_output: Callable[[dict[str, object]], bytes],
    decode_output: Callable[[bytes], DecodedShard],
    server_offset_hours: Callable[[datetime], int],
    server_to_utc: Callable[[datetime], datetime],
) -> dict[str, object]:
    """Build one unpublished stage from bounded capabilities."""

    try:
        _validate_authority(authority, shape)
        if not all(callable(value) for value in (shard_reader, decode_input, encode_output, decode_output, server_offset_hours, server_to_utc)):
            raise ValueError
        dates, public_mapping, date_set_sha = _metadata_mapping(
            authority, shape, public_receipt, public_manifest, selection_manifest
        )
        stage = Path(stage_root).absolute()
        if os.path.lexists(stage):
            raise ValueError
        stage.parent.mkdir(parents=True, exist_ok=True)
        stage.mkdir()
        requests = [
            {
                "date": day,
                "input_relative_path": public_mapping[day]["relative_path"],
                "request_index": index,
                "schema_version": "trendstack_007_projection_request.v1",
            }
            for index, day in enumerate(dates)
        ]
        request_payload = b"".join(canonical_json(row) + b"\n" for row in requests)
        request_sha = sha256_bytes(request_payload)
        _exclusive_write(stage / "projection_requests.jsonl", request_payload)
        request_receipt = {
            "date_set_sha256": date_set_sha,
            "first_date": dates[0],
            "last_date": dates[-1],
            "request_count": len(dates),
            "request_sha256": request_sha,
            "schema_version": "trendstack_007_projection_request_receipt.v1",
        }
        _exclusive_write(stage / "projection_request_receipt.json", canonical_json(request_receipt) + b"\n")

        manifest_rows = []
        trace_rows = []
        selected_opens = 0
        for index, day in enumerate(dates):
            source = public_mapping[day]
            input_payload = shard_reader(day, source["relative_path"])
            selected_opens += 1
            if (
                type(input_payload) is not bytes
                or len(input_payload) != source["bytes"]
                or sha256_bytes(input_payload) != source["sha256"]
            ):
                raise ValueError
            row = _validate_decoded_input(
                decode_input(input_payload), day, source["rows"], server_offset_hours, server_to_utc
            )
            output_payload = encode_output(row)
            if type(output_payload) is not bytes or not output_payload:
                raise ValueError
            output_decoded = decode_output(output_payload)
            if (
                type(output_decoded) is not DecodedShard
                or output_decoded.schema != EXPECTED_ARROW_SCHEMA
                or output_decoded.row_groups != 1
                or output_decoded.rows != (row,)
            ):
                raise ValueError
            relative = f"DESIGN/{day}/h1_1200.parquet"
            _exclusive_write(stage / Path(relative), output_payload)
            output_sha = sha256_bytes(output_payload)
            manifest_rows.append({
                "bytes": len(output_payload), "date": day, "relative_path": relative, "rows": 1,
                "schema_version": "trendstack_007_projection_manifest_row.v1", "sha256": output_sha,
            })
            trace_rows.append({
                "date": day, "input_bytes": source["bytes"],
                "input_relative_path": source["relative_path"], "input_sha256": source["sha256"],
                "output_bytes": len(output_payload), "output_relative_path": relative,
                "output_sha256": output_sha, "request_index": index, "rows": 1,
                "schema_version": "trendstack_007_projection_trace.v1",
            })
        manifest_payload = b"".join(canonical_json(row) + b"\n" for row in manifest_rows)
        trace_payload = b"".join(canonical_json(row) + b"\n" for row in trace_rows)
        manifest_sha = sha256_bytes(manifest_payload)
        trace_sha = sha256_bytes(trace_payload)
        data_tree_sha = _data_tree(manifest_rows)
        _exclusive_write(stage / "design_1200_manifest.jsonl", manifest_payload)
        _exclusive_write(stage / "design_1200_source_trace.jsonl", trace_payload)
        projector_access = {
            "clock_tool_reads": 1, "feature_or_economics_opens": 0, "hyp006_partial_stage_opens": 0,
            "public_manifest_reads": 1, "public_receipt_reads": 1, "raw_source_opens": 0,
            "sealed_holdout_opens": 0, "sealed_validation_opens": 0,
            "selected_public_shard_opens": selected_opens, "selection_manifest_reads": 1,
            "unselected_public_shard_opens": 0,
        }
        reconciliation = {
            "data_tree_sha256": data_tree_sha, "date_set_sha256": date_set_sha,
            "expected_rows": shape.expected_dates, "hypothesis_id": HYPOTHESIS_ID,
            "manifest_sha256": manifest_sha, "output_rows": len(dates), "output_shards": len(dates),
            "projection_attempt_id": authority.projection_attempt_id,
            "projector_selected_shard_opens": selected_opens, "request_count": len(dates),
            "request_sha256": request_sha, "schema_version": "trendstack_007_projection_reconciliation.v1",
            "trace_rows": len(trace_rows), "trace_sha256": trace_sha,
        }
        reconciliation_payload = canonical_json(reconciliation) + b"\n"
        _exclusive_write(stage / "design_1200_reconciliation.json", reconciliation_payload)
        projector_receipt = {
            "active_contract_sha256": authority.active_contract_sha256,
            "data_tree_sha256": data_tree_sha, "economics_opened": False, "hypothesis_id": HYPOTHESIS_ID,
            "manifest_sha256": manifest_sha, "output_rows": len(dates), "output_shards": len(dates),
            "projection_attempt_id": authority.projection_attempt_id, "projector_access": projector_access,
            "public_manifest_sha256": authority.public_manifest_sha256,
            "public_receipt_sha256": authority.public_receipt_sha256,
            "reconciliation_sha256": sha256_bytes(reconciliation_payload),
            "research_holdout_opened": False, "research_validation_opened": False,
            "schema_version": "trendstack_007_projector_receipt.v1",
            "selection_manifest_sha256": authority.selection_manifest_sha256,
            "task_packet_sha256": authority.task_packet_sha256, "trace_sha256": trace_sha,
            "verdict": "READY_FOR_INDEPENDENT_STAGE_VALIDATION",
        }
        _exclusive_write(stage / "design_1200_projector_receipt.json", canonical_json(projector_receipt) + b"\n")
        metadata_hashes = {
            name: sha256_bytes(stable_read_regular(stage / name, stage))
            for name in METADATA_FILES
        }
        return {
            "data_tree_sha256": data_tree_sha,
            "manifest_sha256": manifest_sha,
            "output_rows": len(dates),
            "output_shards": len(dates),
            "projector_access": projector_access,
            "reconciliation_sha256": sha256_bytes(reconciliation_payload),
            "stage_metadata_hashes": metadata_hashes,
            "trace_sha256": trace_sha,
            "verdict": "READY_FOR_INDEPENDENT_STAGE_VALIDATION",
        }
    except Exception as exc:
        if isinstance(exc, InvalidProjection):
            raise
        raise InvalidProjection("INVALID_PROJECTION") from exc


def project_stage_from_paths(
    *,
    workspace_root: Path | str,
    public_receipt_path: Path | str,
    public_manifest_path: Path | str,
    selection_manifest_path: Path | str,
    **projection_arguments,
) -> dict[str, object]:
    """Own the three upstream metadata reads, then execute the projector.

    Parquet access remains a narrow injected ``shard_reader`` capability.  A
    production supervisor can therefore bind it to the reviewed allowlist,
    while tests can prove access counts without granting ambient filesystem
    authority.
    """

    try:
        root = Path(workspace_root).absolute()
        receipt = stable_read_regular(public_receipt_path, root)
        manifest = stable_read_regular(public_manifest_path, root)
        selection = stable_read_regular(selection_manifest_path, root)
        return project_stage_synthetic(
            public_receipt=receipt,
            public_manifest=manifest,
            selection_manifest=selection,
            **projection_arguments,
        )
    except Exception as exc:
        if isinstance(exc, InvalidProjection):
            raise
        raise InvalidProjection("INVALID_PROJECTION") from exc


def verified_clock_functions(
    clock_path: Path | str,
    workspace_root: Path | str,
    expected_sha256: str,
) -> tuple[Callable[[datetime], int], Callable[[datetime], datetime]]:
    """Load the SHA-bound clock source without ambient path import lookup."""

    try:
        if not _valid_sha(expected_sha256):
            raise ValueError
        path = Path(clock_path).absolute()
        payload = stable_read_regular(path, workspace_root)
        if sha256_bytes(payload) != expected_sha256:
            raise ValueError
        module = types.ModuleType("_trendstack_007_verified_clock")
        module.__file__ = str(path)
        exec(compile(payload, str(path), "exec"), module.__dict__)
        offset = getattr(module, "server_offset_hours", None)
        to_utc = getattr(module, "server_to_utc", None)
        if not callable(offset) or not callable(to_utc):
            raise ValueError
        return offset, to_utc
    except Exception as exc:
        if isinstance(exc, InvalidProjection):
            raise
        raise InvalidProjection("INVALID_PROJECTION") from exc


def bounded_public_shard_reader(
    workspace_root: Path | str,
    allowed_shard_root: Path | str,
) -> Callable[[str, str], bytes]:
    """Create a reader that can address only the reviewed DESIGN template."""

    root = Path(workspace_root).absolute()
    shard_root = Path(allowed_shard_root).absolute()
    if not _inside(shard_root, root) or shard_root == root:
        raise InvalidProjection("INVALID_PROJECTION")

    def read(day: str, relative_path: str) -> bytes:
        try:
            canonical_day = _date(day)
            expected = f"public/DESIGN/{canonical_day}/h1.parquet"
            if relative_path != expected:
                raise ValueError
            path = shard_root / canonical_day / "h1.parquet"
            return stable_read_regular(path, shard_root)
        except Exception as exc:
            if isinstance(exc, InvalidProjection):
                raise
            raise InvalidProjection("INVALID_PROJECTION") from exc

    return read


def pyarrow_projection_codecs() -> tuple[
    Callable[[bytes], DecodedShard],
    Callable[[dict[str, object]], bytes],
    Callable[[bytes], DecodedShard],
]:
    """Create production Parquet codecs lazily; importing this module stays inert."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        arrow_schema = pa.schema([
            pa.field("time_server", pa.timestamp("ns"), nullable=True),
            pa.field("time_utc", pa.timestamp("ns"), nullable=True),
            pa.field("utc_offset_h", pa.int8(), nullable=True),
            pa.field("open", pa.float64(), nullable=True),
            pa.field("high", pa.float64(), nullable=True),
            pa.field("low", pa.float64(), nullable=True),
            pa.field("close", pa.float64(), nullable=True),
            pa.field("tick_volume", pa.uint64(), nullable=True),
            pa.field("spread", pa.int32(), nullable=True),
            pa.field("real_volume", pa.uint64(), nullable=True),
        ])

        def physical_schema(schema) -> tuple[tuple[str, str, bool], ...]:
            values = []
            for index, field in enumerate(schema):
                expected_type = arrow_schema[index].type if index < len(arrow_schema) else None
                label = EXPECTED_ARROW_SCHEMA[index][1] if field.type == expected_type else "INVALID:" + str(field.type)
                values.append((field.name, label, field.nullable))
            return tuple(values)

        def decode(payload: bytes) -> DecodedShard:
            parquet = pq.ParquetFile(pa.BufferReader(payload))
            rows = parquet.read().to_pylist()
            for row in rows:
                for name in ("time_server", "time_utc"):
                    value = row.get(name)
                    if type(value) is not datetime and hasattr(value, "to_pydatetime"):
                        row[name] = value.to_pydatetime()
            return DecodedShard(
                physical_schema(parquet.schema_arrow), parquet.num_row_groups,
                tuple(rows),
            )

        def encode(row: dict[str, object]) -> bytes:
            table = pa.Table.from_pylist([row], schema=arrow_schema)
            sink = pa.BufferOutputStream()
            pq.write_table(
                table, sink, row_group_size=1, compression="NONE",
                use_dictionary=False, write_statistics=False,
            )
            return sink.getvalue().to_pybytes()

        return decode, encode, decode
    except Exception as exc:
        raise InvalidProjection("INVALID_PROJECTION") from exc
