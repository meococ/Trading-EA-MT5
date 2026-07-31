from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
DESIGN_PLAN_SHA256 = "06AB038A59A9CEEF3E47734E892CCC04A98F43D6E82B9373A2C8680EBB6DA0A9"
DESIGN_PLAN_V2_SHA256 = "3E31F1229C1BD4DBAB05D977E9F9FB5BB553EE65F097BB0B43B787AC9A1EC4C6"
DESIGN_PLAN_V2_RELATIVE_PATH = "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN_V2.md"
DESIGN_DATE_SET_SHA256 = "4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A"
DESIGN_DATE_SET_CANONICAL_BYTES = 14_301
DESIGN_DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
SOURCE_PLAN_SHA256 = "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
STAGE0_LEDGER_SHA256 = "3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7"
STAGE0_RECEIPT_SHA256 = "5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE"
STAGE0_ACCESS_TRACE_SHA256 = "6C292ECA2A8332CAD1872F5C78843C5B80BE81A6B865C88AF3FB75C6678E4F15"
STAGE0_RECONCILIATION_SHA256 = "7C59560205B0C43DE6C4E26AA7BD266FD45261DC6CEC3BFFB3681EB625E4B56F"
PACKET_MANIFEST_SHA256 = "D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA"
PACKET_RECEIPT_SHA256 = "DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320"
PACKET_SET_SHA256 = "22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
EXPECTED_REQUEST_COUNT = 1297
EXPECTED_TOTAL_ROWS = 466_920
WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "trendstack_002_design_m1"
EXPECTED_FIRST_DATE = "2016-01-04"
EXPECTED_LAST_DATE = "2020-12-31"
DESIGN_START = datetime(2016, 1, 4, tzinfo=timezone.utc)
VALIDATION_START = datetime(2021, 1, 1, tzinfo=timezone.utc)
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
SHA256_RE = re.compile(r"[0-9A-F]{64}\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
REQUEST_SCHEMA = "trendstack_002_design_m1_request.v1"
RECEIPT_SCHEMA = "trendstack_002_design_request_plan_receipt.v1"
REQUEST_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "request_id",
    "sequence",
    "split",
    "opportunity_id",
    "canonical_from_utc",
    "canonical_to_inclusive_utc",
    "api_server_wall_from_encoded_as_utc",
    "api_server_wall_to_encoded_as_utc",
    "from_clock_roundtrip_status",
    "to_clock_roundtrip_status",
    "expected_rows",
    "source_plan_sha256",
    "design_plan_sha256",
}


class InvalidEngineering(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidEngineering(f"INVALID_ENGINEERING {message}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_design_date_set_bytes(dates: list[str]) -> bytes:
    _require(type(dates) is list and bool(dates), "DESIGN date-set is empty or malformed")
    prior = None
    encoded = []
    for value in dates:
        _require(type(value) is str and DATE_RE.fullmatch(value) is not None, "DESIGN date-set member malformed")
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise InvalidEngineering("INVALID_ENGINEERING DESIGN date-set member malformed") from exc
        _require(DESIGN_START <= parsed < VALIDATION_START, "DESIGN date-set contains validation/holdout date")
        _require(prior is None or value > prior, "DESIGN date-set is duplicate/non-monotonic")
        prior = value
        encoded.append(value.encode("ascii") + b"\n")
    return DESIGN_DATE_SET_PREFIX + b"".join(encoded)


def _validate_frozen_design_date_set(dates: list[str]) -> tuple[str, int]:
    payload = canonical_design_date_set_bytes(dates)
    observed = sha256_bytes(payload)
    _require(len(payload) == DESIGN_DATE_SET_CANONICAL_BYTES, "DESIGN date-set canonical byte count mismatch")
    _require(observed == DESIGN_DATE_SET_SHA256, "DESIGN date-set hash mismatch")
    return observed, len(payload)


def _lstat_no_reparse(path: Path):
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING filesystem path cannot be inspected") from exc
    attributes = getattr(metadata, "st_file_attributes", 0)
    _require(not stat.S_ISLNK(metadata.st_mode), "symlink input is forbidden")
    _require(not attributes & FILE_ATTRIBUTE_REPARSE_POINT, "reparse-point input is forbidden")
    return metadata


def _validate_component_chain(path: Path) -> Path:
    absolute = Path(os.path.abspath(os.fspath(path)))
    parts = absolute.parts
    _require(bool(parts), "empty filesystem path")
    current = Path(parts[0])
    _lstat_no_reparse(current)
    for part in parts[1:]:
        current /= part
        _lstat_no_reparse(current)
    return absolute


def _file_identity(metadata) -> tuple:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_nlink,
        getattr(metadata, "st_file_attributes", 0),
    )


def _handle_identity(metadata) -> tuple:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_nlink,
        getattr(metadata, "st_file_attributes", 0),
    )


def _object_identity(metadata) -> tuple:
    return (
        metadata.st_dev,
        metadata.st_ino,
        getattr(metadata, "st_file_attributes", 0),
    )


def read_stable_file(path: Path) -> bytes:
    path = _validate_component_chain(Path(path))
    before = _lstat_no_reparse(path)
    _require(stat.S_ISREG(before.st_mode), "input is not a regular file")
    _require(before.st_nlink == 1, "hardlinked input is forbidden")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require(_handle_identity(opened) == _handle_identity(before), "input identity changed before read")
            payload = stream.read()
            _require(_handle_identity(os.fstat(stream.fileno())) == _handle_identity(before), "input changed during read")
        after = _lstat_no_reparse(path)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING stable input read failed") from exc
    _require(_file_identity(after) == _file_identity(before), "input identity changed after read")
    _require(len(payload) == before.st_size, "input size changed during read")
    return payload


def _parse_json(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING invalid JSON: {label}") from exc
    _require(isinstance(value, dict), f"JSON object required: {label}")
    return value


def _parse_jsonl(raw: bytes, label: str) -> list[dict]:
    _require(raw.endswith(b"\n"), f"JSONL must end with newline: {label}")
    rows = []
    for index, line in enumerate(raw.splitlines(), start=1):
        _require(bool(line), f"blank JSONL row: {label}:{index}")
        row = _parse_json(line, f"{label}:{index}")
        _require(line == canonical_json_bytes(row), f"noncanonical JSONL row: {label}:{index}")
        rows.append(row)
    _require(bool(rows), f"empty JSONL: {label}")
    return rows


def load_clock(clock_path: Path, expected_sha256: str = CLOCK_SHA256):
    raw = read_stable_file(clock_path)
    _require(sha256_bytes(raw) == expected_sha256, "clock-tool hash mismatch")
    spec = importlib.util.spec_from_file_location("trendstack_002_frozen_clock", clock_path)
    _require(spec is not None and spec.loader is not None, "clock tool cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _require(callable(getattr(module, "server_to_utc", None)), "clock tool has no server_to_utc")
    return module


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_to_server_boundary(value: datetime, clock_module) -> tuple[str, str]:
    utc = value.astimezone(timezone.utc)
    naive_utc = utc.replace(tzinfo=None)
    matches = []
    for offset in (2, 3):
        server = naive_utc + timedelta(hours=offset)
        if clock_module.server_to_utc(server) == naive_utc:
            matches.append(server)
    _require(len(matches) == 1, f"clock boundary ambiguity: {_format_utc(utc)}")
    encoded = matches[0].replace(tzinfo=timezone.utc)
    roundtrip = clock_module.server_to_utc(encoded.replace(tzinfo=None))
    _require(roundtrip == naive_utc, "clock boundary round-trip mismatch")
    return encoded.isoformat(), "PASS"


def build_request_rows(design_dates: list[str], clock_module) -> list[dict]:
    rows = []
    for sequence, value in enumerate(design_dates, start=1):
        _require(type(value) is str and DATE_RE.fullmatch(value) is not None, "invalid DESIGN date")
        try:
            day = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise InvalidEngineering("INVALID_ENGINEERING invalid DESIGN date") from exc
        start = day.replace(hour=12, minute=1)
        end = day.replace(hour=18, minute=0)
        server_from, from_status = _utc_to_server_boundary(start, clock_module)
        server_to, to_status = _utc_to_server_boundary(end, clock_module)
        rows.append(
            {
                "schema_version": REQUEST_SCHEMA,
                "hypothesis_id": HYPOTHESIS_ID,
                "request_id": f"M1-DESIGN-{sequence:04d}-{day:%Y%m%d}",
                "sequence": sequence,
                "split": "DESIGN",
                "opportunity_id": value,
                "canonical_from_utc": _format_utc(start),
                "canonical_to_inclusive_utc": _format_utc(end),
                "api_server_wall_from_encoded_as_utc": server_from,
                "api_server_wall_to_encoded_as_utc": server_to,
                "from_clock_roundtrip_status": from_status,
                "to_clock_roundtrip_status": to_status,
                "expected_rows": 360,
                "source_plan_sha256": SOURCE_PLAN_SHA256,
                "design_plan_sha256": DESIGN_PLAN_SHA256,
            }
        )
    return rows


def validate_request_rows(rows: list[dict], expected_count: int = EXPECTED_REQUEST_COUNT) -> None:
    _require(type(rows) is list and len(rows) == expected_count, "request count mismatch")
    ids = []
    dates = []
    prior_date = None
    for sequence, row in enumerate(rows, start=1):
        _require(isinstance(row, dict) and set(row) == REQUEST_FIELDS, "request schema mismatch")
        _require(row["schema_version"] == REQUEST_SCHEMA, "request schema version mismatch")
        _require(row["hypothesis_id"] == HYPOTHESIS_ID, "request hypothesis mismatch")
        _require(type(row["sequence"]) is int and row["sequence"] == sequence, "request sequence mismatch")
        _require(row["split"] == "DESIGN", "non-DESIGN request is forbidden")
        day_text = row["opportunity_id"]
        _require(type(day_text) is str and DATE_RE.fullmatch(day_text) is not None, "request date malformed")
        try:
            day = datetime.strptime(day_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise InvalidEngineering("INVALID_ENGINEERING request date malformed") from exc
        _require(DESIGN_START <= day < VALIDATION_START, "validation/holdout request is forbidden")
        _require(prior_date is None or day > prior_date, "request dates are duplicate/non-monotonic")
        prior_date = day
        expected_id = f"M1-DESIGN-{sequence:04d}-{day:%Y%m%d}"
        _require(row["request_id"] == expected_id, "request ID mismatch")
        _require(row["canonical_from_utc"] == _format_utc(day.replace(hour=12, minute=1)), "request start mismatch")
        _require(row["canonical_to_inclusive_utc"] == _format_utc(day.replace(hour=18)), "request end mismatch")
        _require(row["expected_rows"] == 360 and type(row["expected_rows"]) is int, "expected-row mismatch")
        _require(row["from_clock_roundtrip_status"] == "PASS", "request start clock status mismatch")
        _require(row["to_clock_roundtrip_status"] == "PASS", "request end clock status mismatch")
        _require(row["source_plan_sha256"] == SOURCE_PLAN_SHA256, "request source-plan mismatch")
        _require(row["design_plan_sha256"] == DESIGN_PLAN_SHA256, "request design-plan mismatch")
        ids.append(row["request_id"])
        dates.append(day_text)
    _require(len(set(ids)) == len(ids) and len(set(dates)) == len(dates), "duplicate request identity")
    if expected_count == EXPECTED_REQUEST_COUNT:
        _require(dates[0] == EXPECTED_FIRST_DATE and dates[-1] == EXPECTED_LAST_DATE, "request boundary dates mismatch")
        _require(sum(row["expected_rows"] for row in rows) == EXPECTED_TOTAL_ROWS, "total expected rows mismatch")
        _validate_frozen_design_date_set(dates)


def expected_upstream_hashes() -> dict[str, str]:
    return {
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "design_plan_v2_sha256": DESIGN_PLAN_V2_SHA256,
        "stage0_eligibility_ledger_sha256": STAGE0_LEDGER_SHA256,
        "stage0_receipt_sha256": STAGE0_RECEIPT_SHA256,
        "stage0_access_trace_sha256": STAGE0_ACCESS_TRACE_SHA256,
        "stage0_reconciliation_sha256": STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": PACKET_RECEIPT_SHA256,
        "decision_packet_set_sha256": PACKET_SET_SHA256,
    }


def _paths_overlap(left: Path, right: Path) -> bool:
    left = Path(os.path.abspath(os.fspath(left)))
    right = Path(os.path.abspath(os.fspath(right)))
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def _prepare_output_root(output_root: Path, input_paths: list[Path] | tuple[Path, ...]) -> tuple[Path, tuple, tuple]:
    root = Path(os.path.abspath(os.fspath(output_root)))
    _require(not os.path.lexists(root), "request output root must be create-new")
    parent = _validate_component_chain(root.parent)
    parent_before = _lstat_no_reparse(parent)
    _require(stat.S_ISDIR(parent_before.st_mode), "request output parent is not a directory")
    for input_path in input_paths:
        checked_input = _validate_component_chain(Path(input_path))
        _require(not _paths_overlap(root, checked_input), "request output overlaps an input path")
    try:
        root.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING request output root must be create-new") from exc
    parent_after = _lstat_no_reparse(parent)
    _require(_object_identity(parent_after) == _object_identity(parent_before), "request output parent identity changed")
    root_after = _lstat_no_reparse(root)
    _require(stat.S_ISDIR(root_after.st_mode), "request output root is not a directory")
    return root, _object_identity(parent_before), _object_identity(root_after)


def _write_new(path: Path, payload: bytes, expected_root_identity: tuple | None = None) -> None:
    parent = _validate_component_chain(path.parent)
    if expected_root_identity is not None:
        _require(_object_identity(_lstat_no_reparse(parent)) == expected_root_identity, "request output root identity changed")
    try:
        with path.open("x+b") as stream:
            opened = os.fstat(stream.fileno())
            _require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1, "request output file identity invalid")
            opened_identity = _object_identity(opened)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            after_handle = os.fstat(stream.fileno())
            _require(_object_identity(after_handle) == opened_identity, "request output file identity changed")
            _require(after_handle.st_nlink == 1 and after_handle.st_size == len(payload), "request output file size/link invalid")
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING create-new output failed") from exc
    after_path = _lstat_no_reparse(path)
    _require(_object_identity(after_path) == opened_identity and after_path.st_nlink == 1, "request output path identity changed")
    _require(read_stable_file(path) == payload, "request output readback mismatch")


def persist_request_plan(
    rows: list[dict],
    output_root: Path,
    upstream_hashes: dict[str, str],
    clock_sha256: str,
    builder_sha256: str,
    *,
    input_paths: list[Path] | tuple[Path, ...] = (),
) -> dict:
    validate_request_rows(rows)
    _require(upstream_hashes == expected_upstream_hashes(), "upstream hash set mismatch")
    _require(clock_sha256 == CLOCK_SHA256, "clock hash mismatch")
    _require(SHA256_RE.fullmatch(builder_sha256) is not None, "builder hash malformed")
    root, parent_identity, root_identity = _prepare_output_root(output_root, input_paths)
    plan_payload = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    plan_path = root / "design_request_plan.jsonl"
    _write_new(plan_path, plan_payload, root_identity)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        **upstream_hashes,
        "design_plan_v2_path": DESIGN_PLAN_V2_RELATIVE_PATH,
        "design_date_set_sha256": DESIGN_DATE_SET_SHA256,
        "design_date_set_canonical_bytes": DESIGN_DATE_SET_CANONICAL_BYTES,
        "request_plan_sha256": sha256_bytes(plan_payload),
        "request_plan_builder_sha256": builder_sha256,
        "clock_tool_sha256": clock_sha256,
        "request_count": len(rows),
        "expected_m1_rows": sum(row["expected_rows"] for row in rows),
        "first_design_date": rows[0]["opportunity_id"],
        "last_design_date": rows[-1]["opportunity_id"],
        "canonical_create_new": True,
        "forbidden_field_scan": "PASS",
        "design_m1_opened": False,
        "validation_m1_opened": False,
        "holdout_opened": False,
        "economics_computed": False,
        "verdict": "REQUEST_PLAN_READY_FOR_INDEPENDENT_REVIEW",
    }
    _write_new(root / "design_request_plan_receipt.json", canonical_json_bytes(receipt) + b"\n", root_identity)
    _require(_object_identity(_lstat_no_reparse(root.parent)) == parent_identity, "request output parent identity changed")
    _require(_object_identity(_lstat_no_reparse(root)) == root_identity, "request output root identity changed")
    _require(read_stable_file(plan_path) == plan_payload, "request plan readback mismatch")
    return receipt


def _safe_packet_path(packet_root: Path, relative: str) -> Path:
    logical = PurePosixPath(relative)
    _require(not logical.is_absolute() and len(logical.parts) == 2, "packet path is not canonical")
    _require(all(part not in {"", ".", ".."} for part in logical.parts), "packet path escapes root")
    target = Path(packet_root) / Path(*logical.parts)
    root = _validate_component_chain(Path(packet_root))
    checked = _validate_component_chain(target)
    try:
        checked.relative_to(root)
    except ValueError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING packet path escapes root") from exc
    return checked


def extract_design_dates(stage0_ledger_path: Path, stage0_receipt_path: Path, decision_packet_root: Path) -> list[str]:
    receipt_raw = read_stable_file(stage0_receipt_path)
    _require(sha256_bytes(receipt_raw) == STAGE0_RECEIPT_SHA256, "Stage-0 receipt file hash mismatch")
    receipt = _parse_json(receipt_raw, "stage0 receipt")
    expected_receipt = {
        "engineering_status": "PASS",
        "stage0_verdict": "PASS",
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "eligibility_ledger_sha256": STAGE0_LEDGER_SHA256,
        "access_trace_sha256": STAGE0_ACCESS_TRACE_SHA256,
        "reconciliation_sha256": STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": PACKET_RECEIPT_SHA256,
        "packet_set_sha256": PACKET_SET_SHA256,
    }
    for field, expected in expected_receipt.items():
        _require(receipt.get(field) == expected, f"Stage-0 receipt {field} mismatch")
    ledger_raw = read_stable_file(stage0_ledger_path)
    _require(sha256_bytes(ledger_raw) == STAGE0_LEDGER_SHA256, "Stage-0 ledger hash mismatch")
    ledger = _parse_jsonl(ledger_raw, "stage0 ledger")
    design_rows = [row for row in ledger if row.get("split") == "DESIGN"]
    _require(len(design_rows) == EXPECTED_REQUEST_COUNT, "DESIGN ledger date count mismatch")
    dates = []
    for expected_index, row in enumerate(design_rows):
        _require(row.get("hypothesis_id") == HYPOTHESIS_ID, "ledger hypothesis mismatch")
        _require(type(row.get("row_index")) is int and row["row_index"] == expected_index, "ledger row index malformed")
        relative = row.get("packet_path")
        _require(type(relative) is str and relative == f"DESIGN/{row.get('opportunity_id')}.json", "ledger packet path mismatch")
        packet_path = _safe_packet_path(decision_packet_root, relative)
        packet_raw = read_stable_file(packet_path)
        _require(sha256_bytes(packet_raw) == row.get("packet_file_sha256"), "ledger/packet hash mismatch")
        packet = _parse_json(packet_raw, relative)
        _require(packet.get("hypothesis_id") == HYPOTHESIS_ID, "packet hypothesis mismatch")
        _require(packet.get("split") == "DESIGN", "non-DESIGN packet opened")
        _require(packet.get("opportunity_id") == row.get("opportunity_id"), "ledger/packet opportunity mismatch")
        _require(packet.get("source_plan_sha256") == SOURCE_PLAN_SHA256, "packet source-plan mismatch")
        dates.append(row["opportunity_id"])
    _require(dates == sorted(dates) and len(set(dates)) == len(dates), "DESIGN dates duplicate/non-monotonic")
    _validate_frozen_design_date_set(dates)
    return dates


def build_request_plan(
    stage0_ledger_path: Path,
    stage0_receipt_path: Path,
    decision_packet_root: Path,
    output_root: Path,
    clock_path: Path,
) -> dict:
    _require(
        Path(os.path.abspath(os.fspath(output_root))) == Path(os.path.abspath(os.fspath(DEFAULT_OUTPUT_ROOT))),
        "request-plan output root is not canonical",
    )
    design_plan_path = Path(__file__).with_name("HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN.md")
    design_plan_v2_path = Path(__file__).with_name("HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN_V2.md")
    source_plan_path = Path(__file__).with_name("HYP-TRENDSTACK-EURUSD-H1-002_SOURCE_PLAN.md")
    _require(sha256_bytes(read_stable_file(design_plan_path)) == DESIGN_PLAN_SHA256, "frozen DESIGN_PLAN hash mismatch")
    _require(sha256_bytes(read_stable_file(design_plan_v2_path)) == DESIGN_PLAN_V2_SHA256, "frozen DESIGN_PLAN_V2 hash mismatch")
    _require(sha256_bytes(read_stable_file(source_plan_path)) == SOURCE_PLAN_SHA256, "frozen SOURCE_PLAN hash mismatch")
    clock = load_clock(clock_path)
    dates = extract_design_dates(stage0_ledger_path, stage0_receipt_path, decision_packet_root)
    rows = build_request_rows(dates, clock)
    validate_request_rows(rows)
    return persist_request_plan(
        rows,
        output_root,
        expected_upstream_hashes(),
        sha256_bytes(read_stable_file(clock_path)),
        sha256_bytes(read_stable_file(Path(__file__))),
        input_paths=(
            stage0_ledger_path,
            stage0_receipt_path,
            decision_packet_root,
            clock_path,
            design_plan_path,
            design_plan_v2_path,
            source_plan_path,
            Path(__file__),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build frozen TrendStack-002 DESIGN M1 request plan")
    parser.add_argument("--stage0-ledger", type=Path, required=True)
    parser.add_argument("--stage0-receipt", type=Path, required=True)
    parser.add_argument("--decision-packet-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--clock-tool", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = build_request_plan(
            args.stage0_ledger,
            args.stage0_receipt,
            args.decision_packet_root,
            args.output_root,
            args.clock_tool,
        )
    except (InvalidEngineering, FileExistsError) as exc:
        print(json.dumps({"verdict": "INVALID_ENGINEERING", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"verdict": receipt["verdict"], "request_plan_sha256": receipt["request_plan_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
