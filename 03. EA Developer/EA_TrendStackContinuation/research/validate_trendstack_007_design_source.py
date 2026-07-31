"""Independent fail-closed validator for a HYP007 synthetic projection stage.

The validator deliberately duplicates the public-metadata and stage-lineage
rules instead of importing the projector.  It never receives a capability for
opening an upstream public Parquet shard; only the unpublished output shards
inside ``stage_root`` may be decoded.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-007"
COLLECTION_ID = "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002"
HEX = frozenset("0123456789ABCDEF")
DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
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


class InvalidStageValidation(RuntimeError):
    pass


@dataclass(frozen=True)
class DecodedOutputShard:
    schema: tuple[tuple[str, str, bool], ...]
    row_groups: int
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class ValidationAuthority:
    projection_attempt_id: str
    active_contract_sha256: str
    task_packet_sha256: str
    validator_tool_sha256: str
    public_receipt_sha256: str
    public_manifest_sha256: str
    selection_manifest_sha256: str


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION")
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except Exception as exc:
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION") from exc


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json(payload: bytes) -> object:
    text = payload.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _object(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = _json(payload)
    if type(value) is not dict or canonical_json(value) + b"\n" != payload:
        raise ValueError
    return value


def _jsonl(payload: bytes) -> list[dict[str, object]]:
    if type(payload) is not bytes or not payload or not payload.endswith(b"\n") or b"\n\n" in payload:
        raise ValueError
    rows = []
    for line in payload.splitlines():
        value = _json(line)
        if type(value) is not dict or canonical_json(value) != line:
            raise ValueError
        rows.append(value)
    return rows


def _validate_runtime_authority_documents(contract_bundle: bytes, task_packet: bytes) -> None:
    bundle = _json(contract_bundle)
    task = _json(task_packet)
    if (
        type(bundle) is not dict or canonical_json(bundle) + b"\n" != contract_bundle
        or set(bundle) != {"contracts", "hypothesis_id", "schema_version"}
        or bundle["schema_version"] != "trendstack_007_active_source_contract_bundle.v2"
        or bundle["hypothesis_id"] != HYPOTHESIS_ID
        or type(bundle["contracts"]) is not list or len(bundle["contracts"]) != 4
        or type(task) is not dict or task.get("hypothesis_id") != HYPOTHESIS_ID
        or task.get("schema_version") != "trendstack_007_source_implementation_task_packet.v4"
    ):
        raise ValueError
    expected_roles = ("base_v4", "output_schema_v5", "metadata_map_v6", "terminal_tree_v7")
    for entry, role in zip(bundle["contracts"], expected_roles):
        if (
            type(entry) is not dict or set(entry) != {"path", "role", "sha256"}
            or entry["role"] != role or not _valid_sha(entry["sha256"])
            or type(entry["path"]) is not str or not entry["path"]
        ):
            raise ValueError
        path = Path(entry["path"])
        if path.is_absolute() or ":" in entry["path"] or any(part in ("", ".", "..") for part in path.parts):
            raise ValueError


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


def _date(value: object) -> str:
    if type(value) is not str or datetime.strptime(value, "%Y-%m-%d").date().isoformat() != value:
        raise ValueError
    return value


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


def _stable_read(path_value: Path | str, root_value: Path | str) -> bytes:
    try:
        path = Path(path_value).absolute()
        root = Path(root_value).absolute()
        if path == root or not _inside(path, root):
            raise ValueError
        relative = path.relative_to(root)
        if any(":" in component for component in relative.parts):
            raise ValueError
        root_info = os.lstat(root)
        if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink() or _reparse(root_info):
            raise ValueError
        current = root
        directory_anchors = [(root, _identity(root_info))]
        for component in relative.parts[:-1]:
            current = current / component
            info = os.lstat(current)
            if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or _reparse(info):
                raise ValueError
            directory_anchors.append((current, _identity(info)))
        before = os.lstat(path)
        if not stat.S_ISREG(before.st_mode) or path.is_symlink() or _reparse(before) or before.st_nlink != 1:
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
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION") from exc


def _exclusive_write(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes or os.path.lexists(path):
        raise ValueError
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if _stable_read(path, path.parent) != payload:
        raise ValueError


def _shape_values(shape: object) -> tuple[int, int, str, str, str]:
    values = tuple(
        getattr(shape, name, None)
        for name in ("expected_dates", "expected_unselected_dates", "expected_date_set_sha256", "first_date", "last_date")
    )
    expected, unselected, date_set, first, last = values
    if (
        type(expected) is not int or expected <= 0
        or type(unselected) is not int or unselected < 0
        or not _valid_sha(date_set)
        or _date(first) != first or _date(last) != last or first > last
    ):
        raise ValueError
    return values


def _public_lineage(
    receipt_payload: bytes,
    manifest_payload: bytes,
    selection_payload: bytes,
    shape: object,
) -> tuple[tuple[str, ...], dict[str, dict[str, object]], str]:
    expected, unselected, expected_date_set, first, last = _shape_values(shape)
    receipt = _object(receipt_payload)
    expected_receipt_fields = {
        "collection_id", "design_dates", "design_manifest_sha256", "raw_source_opens",
        "research_holdout_opened", "research_validation_opened", "schema_version",
        "source_attempt_id", "source_rows", "unselected_shard_opens", "verdict",
    }
    if (
        set(receipt) != expected_receipt_fields
        or receipt["collection_id"] != COLLECTION_ID
        or receipt["schema_version"] != "h1_splitvault_002_public_receipt.v1"
        or receipt["design_manifest_sha256"] != sha256_bytes(manifest_payload)
        or receipt["raw_source_opens"] != 1
        or receipt["unselected_shard_opens"] != 0
        or receipt["research_validation_opened"] is not False
        or receipt["research_holdout_opened"] is not False
        or type(receipt["design_dates"]) is not int
    ):
        raise ValueError
    selection = _jsonl(selection_payload)
    if any(
        set(row) != {"date", "schema_version"}
        or row["schema_version"] != "trendstack_006_design_date_selection.v1"
        for row in selection
    ):
        raise ValueError
    dates = tuple(_date(row["date"]) for row in selection)
    date_set = sha256_bytes(DATE_SET_PREFIX + b"".join(day.encode("ascii") + b"\n" for day in dates))
    if (
        dates != tuple(sorted(set(dates))) or len(dates) != expected
        or dates[0] != first or dates[-1] != last or date_set != expected_date_set
    ):
        raise ValueError
    fields = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
    mapping = {}
    for row in _jsonl(manifest_payload):
        day = _date(row.get("date"))
        if (
            set(row) != fields or day in mapping
            or row["schema_version"] != "h1_splitvault_002_public_design_shard.v1"
            or row["relative_path"] != f"public/DESIGN/{day}/h1.parquet"
            or type(row["bytes"]) is not int or row["bytes"] <= 0
            or type(row["rows"]) is not int or row["rows"] <= 0
            or not _valid_sha(row["sha256"])
        ):
            raise ValueError
        mapping[day] = dict(row)
    if (
        tuple(mapping) != tuple(sorted(mapping))
        or len(mapping) != receipt["design_dates"]
        or not set(dates).issubset(mapping)
        or len(mapping) - len(dates) != unselected
    ):
        raise ValueError
    return dates, mapping, date_set


def _validate_output(decoded: DecodedOutputShard, day: str) -> None:
    if (
        type(decoded) is not DecodedOutputShard
        or decoded.schema != EXPECTED_ARROW_SCHEMA
        or decoded.row_groups != 1
        or len(decoded.rows) != 1
    ):
        raise ValueError
    row = decoded.rows[0]
    if type(row) is not dict or set(row) != {item[0] for item in EXPECTED_ARROW_SCHEMA} or any(value is None for value in row.values()):
        raise ValueError
    utc = row["time_utc"]
    server = row["time_server"]
    offset = row["utc_offset_h"]
    if (
        type(utc) is not datetime or type(server) is not datetime
        or utc.tzinfo is not None or server.tzinfo is not None
        or utc != datetime.fromisoformat(day + "T12:00:00")
        or type(offset) is not int or isinstance(offset, bool) or not -128 <= offset <= 127
        or server - utc != timedelta(hours=offset)
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


def _data_tree(manifest_rows: list[dict[str, object]]) -> str:
    document = {
        "files": [
            {"relative_path": row["relative_path"], "bytes": row["bytes"], "sha256": row["sha256"]}
            for row in sorted(manifest_rows, key=lambda item: item["relative_path"])
        ],
        "schema_version": "trendstack_007_projection_data_tree.v1",
    }
    return sha256_bytes(canonical_json(document))


def stage_output_identity_digest_no_payload(
    stage_root: Path | str,
    manifest_payload: bytes,
    expected_shards: int,
) -> str:
    """Re-derive the frozen staged-file identity digest using lstat only."""

    try:
        if type(expected_shards) is not int or expected_shards <= 0:
            raise ValueError
        stage = Path(stage_root).absolute()
        stage_info = os.lstat(stage)
        if not stat.S_ISDIR(stage_info.st_mode) or stage.is_symlink() or _reparse(stage_info):
            raise ValueError
        device = int(stage_info.st_dev)
        directory_anchors = {stage: _identity(stage_info)}
        rows = _jsonl(manifest_payload)
        if len(rows) != expected_shards:
            raise ValueError
        identities = []
        previous = None
        fields = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
        for row in rows:
            day = _date(row.get("date"))
            relative = f"DESIGN/{day}/h1_1200.parquet"
            if (
                set(row) != fields or row["relative_path"] != relative
                or row["rows"] != 1 or row["schema_version"] != "trendstack_007_projection_manifest_row.v1"
                or type(row["bytes"]) is not int or row["bytes"] <= 0
                or not _valid_sha(row["sha256"]) or (previous is not None and day <= previous)
            ):
                raise ValueError
            path = stage / Path(relative)
            if not _inside(path, stage):
                raise ValueError
            current = stage
            for component in Path(relative).parts[:-1]:
                current = current / component
                directory = os.lstat(current)
                if (
                    not stat.S_ISDIR(directory.st_mode) or current.is_symlink() or _reparse(directory)
                    or int(directory.st_dev) != device
                ):
                    raise ValueError
                identity = _identity(directory)
                if current in directory_anchors and directory_anchors[current] != identity:
                    raise ValueError
                directory_anchors[current] = identity
            info = os.lstat(path)
            if (
                not stat.S_ISREG(info.st_mode) or path.is_symlink() or _reparse(info)
                or int(info.st_nlink) != 1 or int(info.st_size) != row["bytes"]
            ):
                raise ValueError
            identities.append({
                "bytes": row["bytes"],
                "platform_file_identity": list(_identity(info)),
                "relative_path": relative,
            })
            previous = day
        if any(_identity(os.lstat(path)) != identity for path, identity in directory_anchors.items()):
            raise ValueError
        return sha256_bytes(canonical_json({
            "files": identities,
            "schema_version": "trendstack_007_validated_file_identities.v1",
        }))
    except Exception as exc:
        if isinstance(exc, InvalidStageValidation):
            raise
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION") from exc


def validate_stage_synthetic(
    *,
    stage_root: Path | str,
    evidence_root: Path | str,
    authority: ValidationAuthority,
    shape: object,
    public_receipt: bytes,
    public_manifest: bytes,
    selection_manifest: bytes,
    decode_output: Callable[[bytes], DecodedOutputShard],
    active_contract_reads: int = 0,
    task_packet_reads: int = 0,
) -> dict[str, object]:
    """Independently validate one unpublished stage and emit one receipt."""

    try:
        if (
            type(authority) is not ValidationAuthority
            or not _valid_attempt(authority.projection_attempt_id)
            or any(not _valid_sha(getattr(authority, field)) for field in (
                "active_contract_sha256", "task_packet_sha256", "validator_tool_sha256",
                "public_receipt_sha256", "public_manifest_sha256", "selection_manifest_sha256",
            ))
            or not callable(decode_output)
            or active_contract_reads not in (0, 1)
            or task_packet_reads not in (0, 1)
        ):
            raise ValueError
        if (
            sha256_bytes(public_receipt) != authority.public_receipt_sha256
            or sha256_bytes(public_manifest) != authority.public_manifest_sha256
            or sha256_bytes(selection_manifest) != authority.selection_manifest_sha256
        ):
            raise ValueError
        dates, public_mapping, date_set = _public_lineage(
            public_receipt, public_manifest, selection_manifest, shape
        )
        stage = Path(stage_root).absolute()
        evidence = Path(evidence_root).absolute()
        stage_info = os.lstat(stage)
        evidence_info = os.lstat(evidence)
        if (
            not stat.S_ISDIR(stage_info.st_mode) or stage.is_symlink() or _reparse(stage_info)
            or not stat.S_ISDIR(evidence_info.st_mode) or evidence.is_symlink() or _reparse(evidence_info)
            or os.path.lexists(evidence / "validation_receipt.json")
        ):
            raise ValueError
        top_level = {entry.name for entry in os.scandir(stage)}
        if top_level != set(METADATA_FILES) | {"DESIGN"}:
            raise ValueError
        metadata_payloads = {name: _stable_read(stage / name, stage) for name in METADATA_FILES}
        metadata_hashes = {name: sha256_bytes(payload) for name, payload in metadata_payloads.items()}

        requests = _jsonl(metadata_payloads["projection_requests.jsonl"])
        request_receipt = _object(metadata_payloads["projection_request_receipt.json"])
        manifest_rows = _jsonl(metadata_payloads["design_1200_manifest.jsonl"])
        trace_rows = _jsonl(metadata_payloads["design_1200_source_trace.jsonl"])
        reconciliation = _object(metadata_payloads["design_1200_reconciliation.json"])
        projector_receipt = _object(metadata_payloads["design_1200_projector_receipt.json"])
        request_sha = sha256_bytes(metadata_payloads["projection_requests.jsonl"])
        manifest_sha = sha256_bytes(metadata_payloads["design_1200_manifest.jsonl"])
        trace_sha = sha256_bytes(metadata_payloads["design_1200_source_trace.jsonl"])
        reconciliation_sha = sha256_bytes(metadata_payloads["design_1200_reconciliation.json"])

        if len(requests) != len(dates) or len(manifest_rows) != len(dates) or len(trace_rows) != len(dates):
            raise ValueError
        request_fields = {"date", "input_relative_path", "request_index", "schema_version"}
        manifest_fields = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
        trace_fields = {
            "date", "input_bytes", "input_relative_path", "input_sha256", "output_bytes",
            "output_relative_path", "output_sha256", "request_index", "rows", "schema_version",
        }
        for index, day in enumerate(dates):
            request = requests[index]
            manifest = manifest_rows[index]
            trace = trace_rows[index]
            source = public_mapping[day]
            output_relative = f"DESIGN/{day}/h1_1200.parquet"
            if (
                set(request) != request_fields
                or request != {
                    "date": day, "input_relative_path": source["relative_path"], "request_index": index,
                    "schema_version": "trendstack_007_projection_request.v1",
                }
                or set(manifest) != manifest_fields
                or manifest.get("date") != day or manifest.get("relative_path") != output_relative
                or manifest.get("rows") != 1
                or manifest.get("schema_version") != "trendstack_007_projection_manifest_row.v1"
                or type(manifest.get("bytes")) is not int or manifest["bytes"] <= 0
                or not _valid_sha(manifest.get("sha256"))
                or set(trace) != trace_fields
                or trace != {
                    "date": day, "input_bytes": source["bytes"],
                    "input_relative_path": source["relative_path"], "input_sha256": source["sha256"],
                    "output_bytes": manifest["bytes"], "output_relative_path": output_relative,
                    "output_sha256": manifest["sha256"], "request_index": index, "rows": 1,
                    "schema_version": "trendstack_007_projection_trace.v1",
                }
            ):
                raise ValueError
        expected_request_receipt = {
            "date_set_sha256": date_set, "first_date": dates[0], "last_date": dates[-1],
            "request_count": len(dates), "request_sha256": request_sha,
            "schema_version": "trendstack_007_projection_request_receipt.v1",
        }
        if request_receipt != expected_request_receipt:
            raise ValueError
        data_tree_sha = _data_tree(manifest_rows)
        expected_reconciliation = {
            "data_tree_sha256": data_tree_sha, "date_set_sha256": date_set,
            "expected_rows": len(dates), "hypothesis_id": HYPOTHESIS_ID,
            "manifest_sha256": manifest_sha, "output_rows": len(dates), "output_shards": len(dates),
            "projection_attempt_id": authority.projection_attempt_id,
            "projector_selected_shard_opens": len(dates), "request_count": len(dates),
            "request_sha256": request_sha, "schema_version": "trendstack_007_projection_reconciliation.v1",
            "trace_rows": len(dates), "trace_sha256": trace_sha,
        }
        if reconciliation != expected_reconciliation:
            raise ValueError
        expected_access = {
            "clock_tool_reads": 1, "feature_or_economics_opens": 0, "hyp006_partial_stage_opens": 0,
            "public_manifest_reads": 1, "public_receipt_reads": 1, "raw_source_opens": 0,
            "sealed_holdout_opens": 0, "sealed_validation_opens": 0,
            "selected_public_shard_opens": len(dates), "selection_manifest_reads": 1,
            "unselected_public_shard_opens": 0,
        }
        expected_projector_receipt = {
            "active_contract_sha256": authority.active_contract_sha256,
            "data_tree_sha256": data_tree_sha, "economics_opened": False,
            "hypothesis_id": HYPOTHESIS_ID, "manifest_sha256": manifest_sha,
            "output_rows": len(dates), "output_shards": len(dates),
            "projection_attempt_id": authority.projection_attempt_id,
            "projector_access": expected_access,
            "public_manifest_sha256": sha256_bytes(public_manifest),
            "public_receipt_sha256": sha256_bytes(public_receipt),
            "reconciliation_sha256": reconciliation_sha,
            "research_holdout_opened": False, "research_validation_opened": False,
            "schema_version": "trendstack_007_projector_receipt.v1",
            "selection_manifest_sha256": sha256_bytes(selection_manifest),
            "task_packet_sha256": authority.task_packet_sha256, "trace_sha256": trace_sha,
            "verdict": "READY_FOR_INDEPENDENT_STAGE_VALIDATION",
        }
        if projector_receipt != expected_projector_receipt:
            raise ValueError

        design_root = stage / "DESIGN"
        design_info = os.lstat(design_root)
        if not stat.S_ISDIR(design_info.st_mode) or design_root.is_symlink() or _reparse(design_info):
            raise ValueError
        if {entry.name for entry in os.scandir(design_root)} != set(dates):
            raise ValueError
        for index, day in enumerate(dates):
            day_root = design_root / day
            day_info = os.lstat(day_root)
            if (
                not stat.S_ISDIR(day_info.st_mode) or day_root.is_symlink() or _reparse(day_info)
                or {entry.name for entry in os.scandir(day_root)} != {"h1_1200.parquet"}
            ):
                raise ValueError
            path = day_root / "h1_1200.parquet"
            payload = _stable_read(path, stage)
            manifest = manifest_rows[index]
            if len(payload) != manifest["bytes"] or sha256_bytes(payload) != manifest["sha256"]:
                raise ValueError
            _validate_output(decode_output(payload), day)
        identities_sha = stage_output_identity_digest_no_payload(
            stage, metadata_payloads["design_1200_manifest.jsonl"], len(dates)
        )
        validator_access = {
            "active_contract_reads": active_contract_reads, "feature_or_economics_opens": 0,
            "public_manifest_reads": 1, "public_receipt_reads": 1, "public_shard_opens": 0,
            "raw_source_opens": 0, "sealed_holdout_opens": 0, "sealed_validation_opens": 0,
            "selection_manifest_reads": 1, "stage_metadata_file_reads": len(METADATA_FILES),
            "staged_output_shard_opens": len(dates), "task_packet_reads": task_packet_reads,
        }
        receipt = {
            "active_contract_sha256": authority.active_contract_sha256,
            "data_tree_sha256": data_tree_sha, "hypothesis_id": HYPOTHESIS_ID,
            "manifest_sha256": manifest_sha,
            "output_rows": len(dates), "output_shards": len(dates),
            "projection_attempt_id": authority.projection_attempt_id,
            "projector_receipt_sha256": metadata_hashes["design_1200_projector_receipt.json"],
            "reconciliation_sha256": reconciliation_sha,
            "request_sha256": request_sha,
            "schema_version": "trendstack_007_projection_validation_receipt.v1",
            "stage_metadata_hashes": metadata_hashes,
            "stage_root_identity": list(_identity(os.lstat(stage))),
            "task_packet_sha256": authority.task_packet_sha256,
            "trace_sha256": trace_sha,
            "validated_file_identities_sha256": identities_sha,
            "validator_access": validator_access,
            "validator_tool_sha256": authority.validator_tool_sha256,
            "verdict": "PASS_INDEPENDENT_STAGE_VALIDATION",
        }
        _exclusive_write(evidence / "validation_receipt.json", canonical_json(receipt) + b"\n")
        return receipt
    except Exception as exc:
        if isinstance(exc, InvalidStageValidation):
            raise
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION") from exc


def validate_stage_from_paths(
    *,
    workspace_root: Path | str,
    public_receipt_path: Path | str,
    public_manifest_path: Path | str,
    selection_manifest_path: Path | str,
    active_contract_bundle_path: Path | str,
    active_contract_bundle_sha256: str,
    implementation_task_packet_path: Path | str,
    implementation_task_packet_sha256: str,
    **validation_arguments,
) -> dict[str, object]:
    """Own independent public-metadata reads without any shard capability."""

    try:
        root = Path(workspace_root).absolute()
        receipt = _stable_read(public_receipt_path, root)
        manifest = _stable_read(public_manifest_path, root)
        selection = _stable_read(selection_manifest_path, root)
        contract_bundle = _stable_read(active_contract_bundle_path, root)
        task_packet = _stable_read(implementation_task_packet_path, root)
        if (
            not _valid_sha(active_contract_bundle_sha256)
            or not _valid_sha(implementation_task_packet_sha256)
            or sha256_bytes(contract_bundle) != active_contract_bundle_sha256
            or sha256_bytes(task_packet) != implementation_task_packet_sha256
        ):
            raise ValueError
        _validate_runtime_authority_documents(contract_bundle, task_packet)
        return validate_stage_synthetic(
            public_receipt=receipt,
            public_manifest=manifest,
            selection_manifest=selection,
            active_contract_reads=1,
            task_packet_reads=1,
            **validation_arguments,
        )
    except Exception as exc:
        if isinstance(exc, InvalidStageValidation):
            raise
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION") from exc


def pyarrow_output_decoder() -> Callable[[bytes], DecodedOutputShard]:
    """Create the independent production Parquet decoder lazily."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        arrow_types = (
            pa.timestamp("ns"), pa.timestamp("ns"), pa.int8(), pa.float64(), pa.float64(),
            pa.float64(), pa.float64(), pa.uint64(), pa.int32(), pa.uint64(),
        )

        def decode(payload: bytes) -> DecodedOutputShard:
            parquet = pq.ParquetFile(pa.BufferReader(payload))
            schema = tuple(
                (
                    field.name,
                    EXPECTED_ARROW_SCHEMA[index][1]
                    if index < len(arrow_types) and field.type == arrow_types[index]
                    else "INVALID:" + str(field.type),
                    field.nullable,
                )
                for index, field in enumerate(parquet.schema_arrow)
            )
            rows = parquet.read().to_pylist()
            for row in rows:
                for name in ("time_server", "time_utc"):
                    value = row.get(name)
                    if type(value) is not datetime and hasattr(value, "to_pydatetime"):
                        row[name] = value.to_pydatetime()
            return DecodedOutputShard(schema, parquet.num_row_groups, tuple(rows))

        return decode
    except Exception as exc:
        raise InvalidStageValidation("INVALID_STAGE_VALIDATION") from exc
