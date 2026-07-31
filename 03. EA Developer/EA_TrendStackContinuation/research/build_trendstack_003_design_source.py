"""Build a sealed, outcome-blind DESIGN M1 source from narrow capabilities."""

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


PUBLIC_ERROR = "INVALID_DESIGN_SOURCE"
PARENT_HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
PARENT_LEDGER_SCHEMA = "trendstack_002_stage0_eligibility_ledger_row.v1"
PROJECTION_SCHEMA = "trendstack_003_design_projection_row.v1"
PROJECTION_RECEIPT_SCHEMA = "trendstack_003_design_projection_receipt.v1"
SOURCE_VERDICT = "PENDING_INDEPENDENT_VALIDATION"
PENDING_TREE_SCHEMA = "trendstack_003_pending_tree.v1"
DESIGN_DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
_HEX = frozenset("0123456789ABCDEF")
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
_WRAPPER_FIELDS = {
    "schema_version",
    "opportunity_id",
    "split",
    "parent_row_sha256",
    "parent_row_canonical_b64",
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


class InvalidDesignSource(RuntimeError):
    pass


class ProjectionAuthority:
    def __init__(
        self,
        *,
        parent_ledger_sha256: str,
        parent_receipt_sha256: str,
        design_date_set_sha256: str,
        expected_design_dates: int,
        projector_tool_sha256: str,
    ) -> None:
        self.parent_ledger_sha256 = parent_ledger_sha256
        self.parent_receipt_sha256 = parent_receipt_sha256
        self.design_date_set_sha256 = design_date_set_sha256
        self.expected_design_dates = expected_design_dates
        self.projector_tool_sha256 = projector_tool_sha256


class ProjectionCapability:
    def __init__(self, projection: bytes, receipt: bytes) -> None:
        self.__projection = bytes(projection)
        self.__receipt = bytes(receipt)

    def projection_bytes(self) -> bytes:
        return self.__projection

    def receipt_bytes(self) -> bytes:
        return self.__receipt

    @classmethod
    def from_bytes_for_testing(cls, projection: bytes, receipt: bytes) -> "ProjectionCapability":
        if type(projection) is not bytes or type(receipt) is not bytes:
            raise InvalidDesignSource(PUBLIC_ERROR)
        return cls(projection, receipt)


class DesignSourceContract:
    def __init__(
        self,
        *,
        design_date_set_sha256: str,
        expected_design_dates: int,
        expected_rows_per_day: int,
        expected_total_rows: int,
        first_design_date: str,
        last_design_date: str,
        builder_tool_sha256: str,
        source_attempt_id: str,
        design_stage_path: str,
        stage_role: str,
        supervisor_review_base_sha256: str,
    ) -> None:
        self.design_date_set_sha256 = design_date_set_sha256
        self.expected_design_dates = expected_design_dates
        self.expected_rows_per_day = expected_rows_per_day
        self.expected_total_rows = expected_total_rows
        self.first_design_date = first_design_date
        self.last_design_date = last_design_date
        self.builder_tool_sha256 = builder_tool_sha256
        self.source_attempt_id = source_attempt_id
        self.design_stage_path = design_stage_path
        self.stage_role = stage_role
        self.supervisor_review_base_sha256 = supervisor_review_base_sha256


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise InvalidDesignSource(PUBLIC_ERROR)
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


def canonical_design_date_set_bytes(dates: list[str]) -> bytes:
    try:
        if type(dates) is not list or not dates:
            raise ValueError
        encoded: list[bytes] = []
        previous: str | None = None
        for value in dates:
            if type(value) is not str:
                raise ValueError
            parsed = datetime.strptime(value, "%Y-%m-%d")
            if parsed < datetime(2016, 1, 4) or parsed >= datetime(2021, 1, 1):
                raise ValueError
            if previous is not None and value <= previous:
                raise ValueError
            previous = value
            encoded.append(value.encode("ascii") + b"\n")
        return DESIGN_DATE_SET_PREFIX + b"".join(encoded)
    except Exception as exc:
        raise InvalidDesignSource(PUBLIC_ERROR) from exc


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


def _directory_chain(path: Path) -> None:
    current = path.absolute().parent
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
    _directory_chain(path)
    before = _identity(path)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != before[:2]:
            raise ValueError
        payload = handle.read()
        closed_identity = os.fstat(handle.fileno())
    if before != _identity(path) or len(payload) != int(closed_identity.st_size):
        raise ValueError
    return payload


def _exclusive_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    if _stable_read(path) != payload:
        raise ValueError


def _parse_json_object(payload: bytes) -> dict[str, object]:
    if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(payload)
    if type(value) is not dict or _canonical(value) + b"\n" != payload:
        raise ValueError
    return value


def _parse_jsonl(payload: bytes) -> list[tuple[dict[str, object], bytes]]:
    if not payload or not payload.endswith(b"\n"):
        raise ValueError
    result: list[tuple[dict[str, object], bytes]] = []
    for line in payload.splitlines():
        value = json.loads(line)
        if type(value) is not dict or _canonical(value) != line:
            raise ValueError
        result.append((value, line))
    return result


def _validate_projection_authority(authority: ProjectionAuthority) -> None:
    if type(authority) is not ProjectionAuthority or set(authority.__dict__) != {
        "parent_ledger_sha256",
        "parent_receipt_sha256",
        "design_date_set_sha256",
        "expected_design_dates",
        "projector_tool_sha256",
    }:
        raise ValueError
    for key in ("parent_ledger_sha256", "parent_receipt_sha256", "design_date_set_sha256", "projector_tool_sha256"):
        if not _valid_sha(authority.__dict__[key]):
            raise ValueError
    if type(authority.expected_design_dates) is not int or authority.expected_design_dates <= 0:
        raise ValueError


def _validate_parent_row(row: dict[str, object]) -> None:
    if set(row) != _PARENT_FIELDS:
        raise ValueError
    if row["schema_version"] != PARENT_LEDGER_SCHEMA or row["hypothesis_id"] != PARENT_HYPOTHESIS_ID:
        raise ValueError
    if row["split"] not in ("DESIGN", "VALIDATION_FEATURE_ONLY"):
        raise ValueError
    if type(row["row_index"]) is not int or row["row_index"] < 0:
        raise ValueError
    day = row["opportunity_id"]
    if type(day) is not str or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
        raise ValueError
    for key in (
        "feature_complete",
        "control_m252_only_eligible",
        "control_m6_only_eligible",
        "challenger_stack_eligible",
        "negative_disagree_eligible",
    ):
        if type(row[key]) is not bool:
            raise ValueError
    pairs = (
        ("control_m252_only_eligible", "control_m252_only_direction"),
        ("control_m6_only_eligible", "control_m6_only_direction"),
        ("challenger_stack_eligible", "challenger_stack_direction"),
        ("negative_disagree_eligible", "negative_disagree_direction"),
    )
    for eligible_key, direction_key in pairs:
        direction = row[direction_key]
        if row[eligible_key]:
            if type(direction) is not int or direction not in (-1, 1):
                raise ValueError
        elif direction is not None:
            raise ValueError
    if row["challenger_stack_eligible"] and row["negative_disagree_eligible"]:
        raise ValueError
    if row["exclusion_reason"] is not None and type(row["exclusion_reason"]) is not str:
        raise ValueError
    if type(row["max_source_time_utc"]) is not str or row["max_source_time_utc"] != day + "T11:00:00":
        raise ValueError
    if type(row["packet_path"]) is not str or not row["packet_path"].endswith("/" + day + ".json"):
        raise ValueError
    for key in ("next_prefix_sha256", "packet_file_sha256", "packet_payload_sha256", "prior_prefix_sha256", "row_payload_sha256", "source_chain_sha256"):
        if not _valid_sha(row[key]):
            raise ValueError


def project_design_stage0(
    parent_ledger_path: Path | str,
    parent_receipt_path: Path | str,
    authority: ProjectionAuthority,
) -> ProjectionCapability:
    try:
        _validate_projection_authority(authority)
        ledger_path = Path(parent_ledger_path).absolute()
        receipt_path = Path(parent_receipt_path).absolute()
        ledger = _stable_read(ledger_path)
        receipt = _stable_read(receipt_path)
        if (
            sha256_bytes(ledger) != authority.parent_ledger_sha256
            or sha256_bytes(receipt) != authority.parent_receipt_sha256
        ):
            raise ValueError
        projected: list[dict[str, object]] = []
        dates: list[str] = []
        seen_rows: set[int] = set()
        for expected_index, (row, original) in enumerate(_parse_jsonl(ledger)):
            _validate_parent_row(row)
            index = int(row["row_index"])
            if index != expected_index or index in seen_rows:
                raise ValueError
            seen_rows.add(index)
            if row["split"] == "DESIGN":
                day = str(row["opportunity_id"])
                dates.append(day)
                projected.append(
                    {
                        "opportunity_id": day,
                        "parent_row_canonical_b64": base64.b64encode(original).decode("ascii"),
                        "parent_row_sha256": sha256_bytes(original),
                        "schema_version": PROJECTION_SCHEMA,
                        "split": "DESIGN",
                    }
                )
        if len(projected) != authority.expected_design_dates or dates != sorted(set(dates)):
            raise ValueError
        if sha256_bytes(canonical_design_date_set_bytes(dates)) != authority.design_date_set_sha256:
            raise ValueError
        projection_payload = b"".join(_canonical(item) + b"\n" for item in projected)
        projection_receipt = {
            "design_date_set_sha256": authority.design_date_set_sha256,
            "design_rows": len(projected),
            "parent_ledger_sha256": authority.parent_ledger_sha256,
            "parent_receipt_sha256": authority.parent_receipt_sha256,
            "projection_sha256": sha256_bytes(projection_payload),
            "projector_tool_sha256": authority.projector_tool_sha256,
            "schema_version": PROJECTION_RECEIPT_SCHEMA,
            "verdict": "DESIGN_ONLY_PROJECTION_ACCEPTED",
        }
        return ProjectionCapability(projection_payload, _canonical(projection_receipt) + b"\n")
    except Exception as exc:
        if isinstance(exc, InvalidDesignSource) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignSource(PUBLIC_ERROR) from exc


def decode_projected_parent_row(wrapper: dict[str, object]) -> dict[str, object]:
    try:
        if type(wrapper) is not dict or set(wrapper) != _WRAPPER_FIELDS:
            raise ValueError
        if wrapper["schema_version"] != PROJECTION_SCHEMA or wrapper["split"] != "DESIGN":
            raise ValueError
        encoded = wrapper["parent_row_canonical_b64"]
        if type(encoded) is not str or not _valid_sha(wrapper["parent_row_sha256"]):
            raise ValueError
        original = base64.b64decode(encoded.encode("ascii"), validate=True)
        if sha256_bytes(original) != wrapper["parent_row_sha256"]:
            raise ValueError
        row = json.loads(original)
        if type(row) is not dict or _canonical(row) != original:
            raise ValueError
        _validate_parent_row(row)
        if row["split"] != "DESIGN" or row["opportunity_id"] != wrapper["opportunity_id"]:
            raise ValueError
        return row
    except Exception as exc:
        if isinstance(exc, InvalidDesignSource) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignSource(PUBLIC_ERROR) from exc


def _validate_contract(contract: DesignSourceContract) -> None:
    if type(contract) is not DesignSourceContract or set(contract.__dict__) != {
        "design_date_set_sha256",
        "expected_design_dates",
        "expected_rows_per_day",
        "expected_total_rows",
        "first_design_date",
        "last_design_date",
        "builder_tool_sha256",
        "source_attempt_id",
        "design_stage_path",
        "stage_role",
        "supervisor_review_base_sha256",
    }:
        raise ValueError
    if (
        not _valid_sha(contract.design_date_set_sha256)
        or not _valid_sha(contract.builder_tool_sha256)
        or not _valid_sha(contract.supervisor_review_base_sha256)
        or not _valid_source_attempt_id(contract.source_attempt_id)
        or type(contract.design_stage_path) is not str
        or not Path(contract.design_stage_path).is_absolute()
        or contract.stage_role != "DESIGN"
    ):
        raise ValueError
    verified_sha256 = globals().get("__verified_sha256__")
    if verified_sha256 is not None and contract.builder_tool_sha256 != verified_sha256:
        raise ValueError
    for key in ("expected_design_dates", "expected_rows_per_day", "expected_total_rows"):
        if type(contract.__dict__[key]) is not int or contract.__dict__[key] <= 0:
            raise ValueError
    if contract.expected_total_rows != contract.expected_design_dates * contract.expected_rows_per_day:
        raise ValueError
    if contract.expected_rows_per_day != 360:
        raise ValueError
    datetime.strptime(contract.first_design_date, "%Y-%m-%d")
    datetime.strptime(contract.last_design_date, "%Y-%m-%d")


def _validated_projection(capability: ProjectionCapability, contract: DesignSourceContract):
    if type(capability) is not ProjectionCapability:
        raise ValueError
    projection = capability.projection_bytes()
    receipt_payload = capability.receipt_bytes()
    receipt = _parse_json_object(receipt_payload)
    required_receipt = {
        "design_date_set_sha256",
        "design_rows",
        "parent_ledger_sha256",
        "parent_receipt_sha256",
        "projection_sha256",
        "projector_tool_sha256",
        "schema_version",
        "verdict",
    }
    if set(receipt) != required_receipt or receipt["schema_version"] != PROJECTION_RECEIPT_SCHEMA:
        raise ValueError
    if receipt["verdict"] != "DESIGN_ONLY_PROJECTION_ACCEPTED" or receipt["projection_sha256"] != sha256_bytes(projection):
        raise ValueError
    if type(receipt["design_rows"]) is not int or receipt["design_rows"] <= 0:
        raise ValueError
    for key in ("design_date_set_sha256", "parent_ledger_sha256", "parent_receipt_sha256", "projection_sha256", "projector_tool_sha256"):
        if not _valid_sha(receipt[key]):
            raise ValueError
    rows = _parse_jsonl(projection)
    decoded = [decode_projected_parent_row(wrapper) for wrapper, _ in rows]
    dates = [str(row["opportunity_id"]) for row in decoded]
    if (
        len(dates) != contract.expected_design_dates
        or dates != sorted(set(dates))
        or dates[0] != contract.first_design_date
        or dates[-1] != contract.last_design_date
        or sha256_bytes(canonical_design_date_set_bytes(dates)) != contract.design_date_set_sha256
        or receipt["design_date_set_sha256"] != contract.design_date_set_sha256
        or receipt["design_rows"] != contract.expected_design_dates
    ):
        raise ValueError
    return projection, receipt_payload, decoded, dates


def _validated_window(payload: bytes, day: str) -> pa.Table:
    parquet = pq.ParquetFile(pa.BufferReader(payload))
    if not parquet.schema_arrow.equals(_SOURCE_SCHEMA, check_metadata=False):
        raise ValueError
    table = parquet.read()
    start = datetime.fromisoformat(day + "T12:01:00")
    end = datetime.fromisoformat(day + "T18:00:00")
    selected: list[dict[str, object]] = []
    for item in table.to_pylist():
        utc = item["time_utc"]
        if isinstance(utc, datetime) and start <= utc <= end:
            selected.append(item)
    if len(selected) != 360:
        raise ValueError
    for index, item in enumerate(selected):
        expected = start + timedelta(minutes=index)
        utc = item["time_utc"]
        server = item["time_server"]
        offset = item["utc_offset_h"]
        if not isinstance(utc, datetime) or not isinstance(server, datetime) or type(offset) is not int:
            raise ValueError
        if utc != expected or server - utc != timedelta(hours=offset):
            raise ValueError
        values = [item[key] for key in ("open", "high", "low", "close")]
        if any(type(value) is not float or not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError
        open_value, high, low, close = values
        if not (low <= open_value <= high and low <= close <= high):
            raise ValueError
    return pa.Table.from_pylist(selected, schema=_SOURCE_SCHEMA)


def _write_parquet(path: Path, table: pa.Table) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        pq.write_table(table, handle, row_group_size=table.num_rows)
        handle.flush()
        os.fsync(handle.fileno())
    payload = _stable_read(path)
    reopened = pq.ParquetFile(pa.BufferReader(payload))
    if reopened.metadata.num_rows != table.num_rows or reopened.metadata.num_row_groups != 1:
        raise ValueError
    return len(payload), sha256_bytes(payload)


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


def _pending_tree_digest(root: Path, relative_paths: set[str]) -> str:
    entries: list[dict[str, object]] = []
    for relative in sorted(relative_paths):
        payload = _stable_read(root / relative)
        entries.append({"bytes": len(payload), "relative_path": relative, "sha256": sha256_bytes(payload)})
    return sha256_bytes(_canonical({"files": entries, "schema_version": PENDING_TREE_SCHEMA}))


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


def build_design_source(
    design_capability,
    projection: ProjectionCapability,
    output_root: Path | str,
    contract: DesignSourceContract,
    lifecycle_hook: Callable[[str], None] | None = None,
    *,
    attempt_root: Path | str | None = None,
    expected_attempt_identity: tuple[int, ...] | None = None,
) -> dict[str, object]:
    output = Path(output_root).absolute()
    attempt = Path(attempt_root).absolute() if attempt_root is not None else Path(contract.design_stage_path).absolute()
    try:
        _validate_contract(contract)
        if (
            attempt_root is None
            or attempt != Path(contract.design_stage_path).absolute()
            or attempt.parent != output.parent
            or attempt.name != "." + output.name + ".attempt-" + contract.source_attempt_id
        ):
            raise ValueError
        projection_payload, projection_receipt, parent_rows, dates = _validated_projection(projection, contract)
        _directory_chain(output)
        parent_identity = _directory_identity(output.parent)
        if output.exists():
            raise ValueError
        available = tuple(design_capability.design_dates())
        if type(available) is not tuple or tuple(dates) != available:
            raise ValueError
        public_receipt = design_capability.public_receipt_bytes()
        public_manifest = design_capability.public_manifest_bytes()
        if type(public_receipt) is not bytes or type(public_manifest) is not bytes:
            raise ValueError
        public_receipt_value = _parse_json_object(public_receipt)
        if (
            public_receipt_value.get("verdict") != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
            or public_receipt_value.get("source_attempt_id") != contract.source_attempt_id
            or public_receipt_value.get("stage_role") != "CUSTODY"
            or public_receipt_value.get("supervisor_review_base_sha256")
            != contract.supervisor_review_base_sha256
        ):
            raise ValueError
        manifest_items = [item for item, _ in _parse_jsonl(public_manifest)]
        manifest_map: dict[str, str] = {}
        for item in manifest_items:
            day = item.get("date")
            digest = item.get("sha256")
            if type(day) is not str or not _valid_sha(digest) or day in manifest_map:
                raise ValueError
            manifest_map[day] = digest
        if tuple(sorted(manifest_map)) != tuple(dates):
            raise ValueError
        with os.scandir(attempt) as entries:
            attempt_is_empty = next(entries, None) is None
        if (
            type(expected_attempt_identity) is not tuple
            or len(expected_attempt_identity) != 6
            or any(type(value) is not int for value in expected_attempt_identity)
            or _directory_identity(attempt) != expected_attempt_identity
            or not attempt_is_empty
        ):
            raise ValueError
        attempt_identity = expected_attempt_identity
        _exclusive_write(attempt / "design_stage0_projection.jsonl", projection_payload)
        _exclusive_write(attempt / "design_stage0_projection_receipt.json", projection_receipt)
        request_rows = [
            {
                "date": day,
                "end_utc": day + "T18:00:00",
                "parent_opportunity_id": str(row["opportunity_id"]),
                "request_id": "HYP003::" + day + "::M1_SOURCE",
                "schema_version": "trendstack_003_design_request.v1",
                "start_utc": day + "T12:01:00",
            }
            for day, row in zip(dates, parent_rows)
        ]
        request_payload = b"".join(_canonical(item) + b"\n" for item in request_rows)
        _exclusive_write(attempt / "design_request_plan.jsonl", request_payload)
        request_receipt = {
            "design_date_set_sha256": contract.design_date_set_sha256,
            "request_count": len(request_rows),
            "request_plan_sha256": sha256_bytes(request_payload),
            "schema_version": "trendstack_003_design_request_receipt.v1",
        }
        request_receipt_payload = _canonical(request_receipt) + b"\n"
        _exclusive_write(attempt / "design_request_plan_receipt.json", request_receipt_payload)
        manifest_rows: list[dict[str, object]] = []
        trace_rows: list[dict[str, object]] = []
        total_rows = 0
        for index, day in enumerate(dates):
            payload = design_capability.read_design_day(day)
            if type(payload) is not bytes or sha256_bytes(payload) != manifest_map[day]:
                raise ValueError
            table = _validated_window(payload, day)
            relative = Path("raw_m1") / "DESIGN" / day / "1201_1800.parquet"
            size, digest = _write_parquet(attempt / relative, table)
            total_rows += table.num_rows
            manifest_rows.append(
                {
                    "bytes": size,
                    "date": day,
                    "relative_path": relative.as_posix(),
                    "rows": table.num_rows,
                    "sha256": digest,
                }
            )
            trace_rows.append(
                {
                    "date": day,
                    "input_day_sha256": sha256_bytes(payload),
                    "output_sha256": digest,
                    "request_index": index,
                    "rows": table.num_rows,
                    "schema_version": "trendstack_003_design_source_trace.v1",
                }
            )
        if total_rows != contract.expected_total_rows or len(manifest_rows) != contract.expected_design_dates:
            raise ValueError
        manifest_payload = b"".join(_canonical(item) + b"\n" for item in manifest_rows)
        trace_payload = b"".join(_canonical(item) + b"\n" for item in trace_rows)
        _exclusive_write(attempt / "design_m1_manifest.jsonl", manifest_payload)
        _exclusive_write(attempt / "design_source_access_trace.jsonl", trace_payload)
        reconciliation = {
            "date_set_sha256": sha256_bytes(canonical_design_date_set_bytes([str(item["date"]) for item in manifest_rows])),
            "exact_once_status": "PASS",
            "manifest_rows": len(manifest_rows),
            "m1_rows": total_rows,
            "schema_version": "trendstack_003_design_source_reconciliation.v1",
            "trace_rows": len(trace_rows),
        }
        reconciliation_payload = _canonical(reconciliation) + b"\n"
        _exclusive_write(attempt / "design_source_reconciliation.json", reconciliation_payload)
        pending_files = {
            "design_request_plan.jsonl",
            "design_request_plan_receipt.json",
            "design_stage0_projection.jsonl",
            "design_stage0_projection_receipt.json",
            "design_m1_manifest.jsonl",
            "design_source_access_trace.jsonl",
            "design_source_reconciliation.json",
            *{str(item["relative_path"]) for item in manifest_rows},
        }
        pending_tree_sha256 = _pending_tree_digest(attempt, pending_files)
        receipt: dict[str, object] = {
            "builder_tool_sha256": contract.builder_tool_sha256,
            "custodian_full_corpus_decoded": True,
            "custodian_public_manifest_sha256": sha256_bytes(public_manifest),
            "custodian_public_receipt_sha256": sha256_bytes(public_receipt),
            "design_date_set_sha256": contract.design_date_set_sha256,
            "economics_opened": False,
            "m1_manifest_sha256": sha256_bytes(manifest_payload),
            "m1_rows": total_rows,
            "performance_trials_executed": 0,
            "pending_tree_sha256": pending_tree_sha256,
            "projection_sha256": sha256_bytes(projection_payload),
            "projection_receipt_sha256": sha256_bytes(projection_receipt),
            "request_count": len(request_rows),
            "request_plan_sha256": sha256_bytes(request_payload),
            "request_receipt_sha256": sha256_bytes(request_receipt_payload),
            "reconciliation_sha256": sha256_bytes(reconciliation_payload),
            "research_holdout_opened": False,
            "research_validation_opened": False,
            "schema_version": "trendstack_003_design_source_receipt.v1",
            "source_attempt_id": contract.source_attempt_id,
            "stage_path": contract.design_stage_path,
            "stage_role": contract.stage_role,
            "supervisor_review_base_sha256": contract.supervisor_review_base_sha256,
            "trace_sha256": sha256_bytes(trace_payload),
            "verdict": SOURCE_VERDICT,
        }
        receipt_payload = _canonical(receipt) + b"\n"
        _exclusive_write(attempt / "design_m1_source_receipt.json", receipt_payload)
        if lifecycle_hook is not None:
            lifecycle_hook("before_publish")
        _publish_no_replace(attempt, output, parent_identity, attempt_identity)
        return {**receipt, "pending_receipt_sha256": sha256_bytes(receipt_payload)}
    except Exception as exc:
        if isinstance(exc, InvalidDesignSource) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidDesignSource(PUBLIC_ERROR) from exc
