from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


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
DSR_TOOL_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
CLOCK_TOOL_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
EXPECTED_DESIGN_DATES = 1297
EXPECTED_TOTAL_ARM_ROWS = 3881
EXPECTED_ARM_COUNTS = {
    "CONTROL_M252_ONLY": 1297,
    "CONTROL_M6_ONLY": 1292,
    "CHALLENGER_STACK": 661,
    "NEGATIVE_DISAGREE": 631,
}
ARMS = tuple(EXPECTED_ARM_COUNTS)
COSTS = (("1_50", 1.50), ("2_25", 2.25), ("3_00", 3.00))
ELAPSED_WEEKS = 260.571428571
DESIGN_START = date(2016, 1, 4)
DESIGN_END = date(2020, 12, 31)
DESIGN_DAYS = 1824
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
SHA256_RE = re.compile(r"[0-9A-F]{64}\Z")
WORKSPACE = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_PLAN_PATH = RESEARCH_ROOT / "HYP-TRENDSTACK-EURUSD-H1-002_SOURCE_PLAN.md"
DEFAULT_DESIGN_PLAN_PATH = RESEARCH_ROOT / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN.md"
DEFAULT_DESIGN_PLAN_V2_PATH = RESEARCH_ROOT / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN_V2.md"
DEFAULT_STAGE0_ROOT = RESEARCH_ROOT / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0"
DEFAULT_REQUEST_BUILDER_PATH = RESEARCH_ROOT / "build_trendstack_002_design_request_plan.py"
DEFAULT_ACQUISITION_PATH = RESEARCH_ROOT / "acquire_trendstack_002_design_m1.py"
DEFAULT_CLOCK_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
DEFAULT_EVALUATION_ROOT = RESEARCH_ROOT / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN"
DEFAULT_DECISION_SOURCE_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "trendstack_002"
DEFAULT_DECISION_PACKET_ROOT = DEFAULT_DECISION_SOURCE_ROOT / "decision_packets"
TRADE_SCHEMA = "trendstack_002_design_trade_row.v1"
DAILY_SCHEMA = "trendstack_002_design_daily_book_row.v1"
RESULT_SCHEMA = "trendstack_002_design_economic_result.v1"
RECEIPT_SCHEMA = "trendstack_002_design_evaluation_receipt.v1"
RUN_PACKET_SCHEMA = "trendstack_002_design_run_packet.v1"
RUN_PACKET_FILENAME = "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
RUN_PACKET_VERDICT = "FROZEN_DESIGN_M1_PROXY_ONE_RUN_AUTHORIZED"
REQUEST_SCHEMA = "trendstack_002_design_m1_request.v1"
REQUEST_RECEIPT_SCHEMA = "trendstack_002_design_request_plan_receipt.v1"
M1_MANIFEST_SCHEMA = "trendstack_002_design_m1_manifest_row.v1"
M1_RECEIPT_SCHEMA = "trendstack_002_design_m1_source_receipt.v1"
RAW_M1_COLUMNS = [
    "request_id",
    "opportunity_id",
    "time_server",
    "time_utc",
    "utc_offset_h",
    "bid_open",
    "bid_high",
    "bid_low",
    "bid_close",
    "tick_volume",
    "spread_points",
    "real_volume",
]
RUN_PACKET_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "verdict",
    "source_plan_sha256",
    "design_plan_sha256",
    "design_plan_v2_path",
    "design_plan_v2_sha256",
    "design_date_set_sha256",
    "stage0_eligibility_ledger_sha256",
    "stage0_receipt_sha256",
    "stage0_access_trace_sha256",
    "stage0_reconciliation_sha256",
    "decision_packet_manifest_sha256",
    "decision_packet_receipt_sha256",
    "decision_packet_set_sha256",
    "request_plan_sha256",
    "request_plan_receipt_sha256",
    "request_count",
    "expected_m1_rows",
    "first_design_date",
    "last_design_date",
    "request_plan_builder_sha256",
    "acquisition_tool_sha256",
    "evaluator_tool_sha256",
    "clock_tool_sha256",
    "dsr_tool_sha256",
    "design_m1_output_root",
    "design_m1_authorized",
    "validation_m1_authorized",
    "holdout_authorized",
    "model0_authorized",
    "promotion_authorized",
}
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
REQUEST_RECEIPT_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "source_plan_sha256",
    "design_plan_sha256",
    "design_plan_v2_path",
    "design_plan_v2_sha256",
    "design_date_set_sha256",
    "design_date_set_canonical_bytes",
    "stage0_eligibility_ledger_sha256",
    "stage0_receipt_sha256",
    "stage0_access_trace_sha256",
    "stage0_reconciliation_sha256",
    "decision_packet_manifest_sha256",
    "decision_packet_receipt_sha256",
    "decision_packet_set_sha256",
    "request_plan_sha256",
    "request_plan_builder_sha256",
    "clock_tool_sha256",
    "request_count",
    "expected_m1_rows",
    "first_design_date",
    "last_design_date",
    "canonical_create_new",
    "forbidden_field_scan",
    "design_m1_opened",
    "validation_m1_opened",
    "holdout_opened",
    "economics_computed",
    "verdict",
}
M1_MANIFEST_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "request_id",
    "opportunity_id",
    "split",
    "shard_path",
    "rows",
    "row_groups",
    "first_utc_time",
    "last_utc_time",
    "canonical_row_content_sha256",
    "shard_sha256",
    "shard_bytes",
    "geometry_status",
    "unique_chronological_grid_status",
    "holdout_rows_received",
    "request_plan_sha256",
    "request_plan_receipt_sha256",
    "run_packet_sha256",
    "source_plan_sha256",
    "design_plan_sha256",
    "runtime_hashes",
}
M1_RECEIPT_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "source_plan_sha256",
    "design_plan_sha256",
    "request_plan_sha256",
    "request_plan_receipt_sha256",
    "run_packet_sha256",
    "design_m1_manifest_sha256",
    "request_count",
    "shard_file_count",
    "m1_rows",
    "first_design_date",
    "last_design_date",
    "runtime_provenance",
    "all_shard_hashes_verified",
    "design_m1_opened",
    "validation_m1_opened",
    "holdout_opened",
    "economics_computed",
    "physical_partition_status",
    "verdict",
}
RUNTIME_PROVENANCE_FIELDS = {
    "terminal_executable_label",
    "terminal_executable_sha256",
    "python_executable_label",
    "python_executable_sha256",
    "metatrader5_version",
    "metatrader5_native_module_label",
    "metatrader5_native_module_sha256",
    "clock_tool_label",
    "clock_tool_sha256",
    "acquisition_tool_label",
    "acquisition_tool_sha256",
    "source_plan_sha256",
    "design_plan_sha256",
    "run_packet_sha256",
    "pandas_version",
    "pyarrow_version",
    "account_guard",
}
ACCOUNT_GUARD_FIELDS = {
    "terminal_build",
    "terminal_trade_allowed",
    "terminal_connected",
    "account_mode",
    "server",
    "company",
    "symbol",
    "symbol_digits",
    "symbol_point",
    "symbol_selected",
    "symbol_visible",
}
RUNTIME_HASH_FIELDS = {
    "terminal_executable_sha256",
    "python_executable_sha256",
    "metatrader5_native_module_sha256",
    "clock_tool_sha256",
    "acquisition_tool_sha256",
    "source_plan_sha256",
    "design_plan_sha256",
    "run_packet_sha256",
}
EVALUATION_UPSTREAM_FIELDS = {
    "source_plan_sha256",
    "design_plan_sha256",
    "stage0_eligibility_ledger_sha256",
    "stage0_receipt_sha256",
    "stage0_access_trace_sha256",
    "stage0_reconciliation_sha256",
    "decision_packet_manifest_sha256",
    "decision_packet_receipt_sha256",
    "decision_packet_set_sha256",
    "request_plan_sha256",
    "request_plan_receipt_sha256",
    "run_packet_sha256",
    "request_plan_builder_sha256",
    "acquisition_tool_sha256",
    "evaluator_tool_sha256",
    "clock_tool_sha256",
    "dsr_tool_sha256",
    "design_m1_manifest_sha256",
    "design_m1_source_receipt_sha256",
}


class InvalidEngineering(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidEngineering(f"INVALID_ENGINEERING {message}")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("non-canonical/non-finite JSON value") from exc


def canonical_design_date_set_bytes(dates: list[str]) -> bytes:
    _require(type(dates) is list and bool(dates), "DESIGN date-set is empty or malformed")
    prior = None
    encoded = []
    for value in dates:
        _require(type(value) is str, "DESIGN date-set member malformed")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise InvalidEngineering("INVALID_ENGINEERING DESIGN date-set member malformed") from exc
        _require(parsed.isoformat() == value and DESIGN_START <= parsed <= DESIGN_END, "DESIGN date-set contains non-DESIGN date")
        _require(prior is None or value > prior, "DESIGN date-set is duplicate/non-monotonic")
        prior = value
        encoded.append(value.encode("ascii") + b"\n")
    return DESIGN_DATE_SET_PREFIX + b"".join(encoded)


def _validate_frozen_design_date_set(dates: list[str], packet_sha256: str) -> None:
    payload = canonical_design_date_set_bytes(dates)
    observed = sha256_bytes(payload)
    _require(packet_sha256 == DESIGN_DATE_SET_SHA256, "run-packet DESIGN date-set hash mismatch")
    _require(len(payload) == DESIGN_DATE_SET_CANONICAL_BYTES, "DESIGN date-set canonical byte count mismatch")
    _require(observed == DESIGN_DATE_SET_SHA256, "DESIGN date-set hash mismatch")


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
    current = Path(absolute.parts[0])
    _lstat_no_reparse(current)
    for part in absolute.parts[1:]:
        current /= part
        _lstat_no_reparse(current)
    return absolute


def _path_identity(metadata) -> tuple:
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


def read_stable_file(path: Path) -> bytes:
    path = _validate_component_chain(Path(path))
    before = _lstat_no_reparse(path)
    _require(stat.S_ISREG(before.st_mode), "input is not a regular file")
    _require(before.st_nlink == 1, "hardlinked input is forbidden")
    try:
        with path.open("rb") as stream:
            _require(_handle_identity(os.fstat(stream.fileno())) == _handle_identity(before), "input identity changed")
            payload = stream.read()
            _require(_handle_identity(os.fstat(stream.fileno())) == _handle_identity(before), "input changed during read")
        after = _lstat_no_reparse(path)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING stable input read failed") from exc
    _require(_path_identity(after) == _path_identity(before), "input identity changed after read")
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
    return rows


def _canonical_path_text(path: Path) -> str:
    return os.fspath(Path(os.path.abspath(os.fspath(path))))


def read_run_packet(path: Path) -> tuple[dict, str]:
    path = Path(path)
    _require(path.name == RUN_PACKET_FILENAME, "canonical run-packet filename mismatch")
    raw = read_stable_file(path)
    packet = _parse_json(raw, "DESIGN run packet")
    _require(raw == canonical_json_bytes(packet) + b"\n", "run packet is not canonical JSON with one terminal newline")
    _require(set(packet) == RUN_PACKET_FIELDS, "run-packet schema mismatch")
    _require(packet["schema_version"] == RUN_PACKET_SCHEMA, "run-packet version mismatch")
    _require(packet["hypothesis_id"] == HYPOTHESIS_ID, "run-packet hypothesis mismatch")
    _require(packet["verdict"] == RUN_PACKET_VERDICT, "run-packet verdict is unauthorized")
    pinned = {
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "design_plan_v2_path": DESIGN_PLAN_V2_RELATIVE_PATH,
        "design_plan_v2_sha256": DESIGN_PLAN_V2_SHA256,
        "design_date_set_sha256": DESIGN_DATE_SET_SHA256,
        "stage0_eligibility_ledger_sha256": STAGE0_LEDGER_SHA256,
        "stage0_receipt_sha256": STAGE0_RECEIPT_SHA256,
        "stage0_access_trace_sha256": STAGE0_ACCESS_TRACE_SHA256,
        "stage0_reconciliation_sha256": STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": PACKET_RECEIPT_SHA256,
        "decision_packet_set_sha256": PACKET_SET_SHA256,
        "clock_tool_sha256": CLOCK_TOOL_SHA256,
        "dsr_tool_sha256": DSR_TOOL_SHA256,
    }
    for field, expected in pinned.items():
        _require(packet[field] == expected, f"run-packet {field} mismatch")
    for field in (
        "request_plan_sha256",
        "request_plan_receipt_sha256",
        "request_plan_builder_sha256",
        "acquisition_tool_sha256",
        "evaluator_tool_sha256",
    ):
        _require(type(packet[field]) is str and SHA256_RE.fullmatch(packet[field]) is not None, f"run-packet {field} malformed")
    _require(type(packet["request_count"]) is int and packet["request_count"] == EXPECTED_DESIGN_DATES, "run-packet request count mismatch")
    _require(type(packet["expected_m1_rows"]) is int and packet["expected_m1_rows"] == EXPECTED_DESIGN_DATES * 360, "run-packet M1 row count mismatch")
    _require(packet["first_design_date"] == DESIGN_START.isoformat(), "run-packet first DESIGN date mismatch")
    _require(packet["last_design_date"] == DESIGN_END.isoformat(), "run-packet last DESIGN date mismatch")
    flags = {
        "design_m1_authorized": True,
        "validation_m1_authorized": False,
        "holdout_authorized": False,
        "model0_authorized": False,
        "promotion_authorized": False,
    }
    for field, expected in flags.items():
        _require(type(packet[field]) is bool and packet[field] is expected, f"run-packet {field} mismatch")
    _require(type(packet["design_m1_output_root"]) is str and bool(packet["design_m1_output_root"]), "run-packet output root malformed")
    return packet, sha256_bytes(raw)


def _load_clock(clock_path: Path):
    raw = read_stable_file(clock_path)
    _require(sha256_bytes(raw) == CLOCK_TOOL_SHA256, "clock tool hash mismatch")
    spec = importlib.util.spec_from_file_location("trendstack_002_evaluator_clock", clock_path)
    _require(spec is not None and spec.loader is not None, "clock tool cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_utc(value: Any, label: str) -> datetime:
    _require(type(value) is str and value.endswith("Z"), f"{label} malformed")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING {label} malformed") from exc
    normalized = parsed.astimezone(timezone.utc)
    _require(value == normalized.strftime("%Y-%m-%dT%H:%M:%SZ"), f"{label} is not canonical UTC")
    return normalized


def _parse_server_encoded(value: Any, label: str) -> datetime:
    _require(type(value) is str, f"{label} malformed")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING {label} malformed") from exc
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, f"{label} encoding mismatch")
    return parsed.astimezone(timezone.utc)


def read_request_plan(path: Path, packet: dict, clock_path: Path) -> list[dict]:
    raw = read_stable_file(path)
    _require(sha256_bytes(raw) == packet["request_plan_sha256"], "request-plan hash mismatch")
    rows = _parse_jsonl(raw, "DESIGN request plan")
    _require(len(rows) == EXPECTED_DESIGN_DATES, "request-plan count mismatch")
    clock = _load_clock(clock_path)
    prior = None
    for sequence, row in enumerate(rows, start=1):
        _require(set(row) == REQUEST_FIELDS, "request-plan row schema mismatch")
        _require(row["schema_version"] == REQUEST_SCHEMA and row["hypothesis_id"] == HYPOTHESIS_ID and row["split"] == "DESIGN", "request-plan row identity mismatch")
        _require(type(row["sequence"]) is int and row["sequence"] == sequence, "request-plan sequence mismatch")
        day = row["opportunity_id"]
        _require(type(day) is str and DESIGN_START.isoformat() <= day <= DESIGN_END.isoformat(), "request-plan non-DESIGN date")
        _require(prior is None or day > prior, "request-plan dates duplicate/non-monotonic")
        prior = day
        _require(row["request_id"] == f"M1-DESIGN-{sequence:04d}-{day.replace('-', '')}", "request-plan ID mismatch")
        start = _parse_utc(row["canonical_from_utc"], "request start")
        end = _parse_utc(row["canonical_to_inclusive_utc"], "request end")
        _require(start.strftime("%Y-%m-%dT%H:%M:%SZ") == f"{day}T12:01:00Z", "request start mismatch")
        _require(end.strftime("%Y-%m-%dT%H:%M:%SZ") == f"{day}T18:00:00Z", "request end mismatch")
        _require(type(row["expected_rows"]) is int and row["expected_rows"] == 360, "request rows mismatch")
        server_from = _parse_server_encoded(row["api_server_wall_from_encoded_as_utc"], "server start")
        server_to = _parse_server_encoded(row["api_server_wall_to_encoded_as_utc"], "server end")
        _require(clock.server_to_utc(server_from.replace(tzinfo=None)) == start.replace(tzinfo=None), "request start clock drift")
        _require(clock.server_to_utc(server_to.replace(tzinfo=None)) == end.replace(tzinfo=None), "request end clock drift")
        _require(row["from_clock_roundtrip_status"] == row["to_clock_roundtrip_status"] == "PASS", "request clock status mismatch")
        _require(row["source_plan_sha256"] == SOURCE_PLAN_SHA256 and row["design_plan_sha256"] == DESIGN_PLAN_SHA256, "request plan binding mismatch")
    _require(rows[0]["opportunity_id"] == DESIGN_START.isoformat() and rows[-1]["opportunity_id"] == DESIGN_END.isoformat(), "request-plan boundary dates mismatch")
    _validate_frozen_design_date_set([row["opportunity_id"] for row in rows], packet["design_date_set_sha256"])
    return rows


def read_request_receipt(path: Path, packet: dict) -> dict:
    raw = read_stable_file(path)
    _require(sha256_bytes(raw) == packet["request_plan_receipt_sha256"], "request receipt hash mismatch")
    receipt = _parse_json(raw, "request receipt")
    _require(raw == canonical_json_bytes(receipt) + b"\n", "request receipt is not canonical")
    _require(set(receipt) == REQUEST_RECEIPT_FIELDS, "request receipt schema mismatch")
    expected = {
        "schema_version": REQUEST_RECEIPT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "design_plan_v2_path": DESIGN_PLAN_V2_RELATIVE_PATH,
        "design_plan_v2_sha256": DESIGN_PLAN_V2_SHA256,
        "design_date_set_sha256": packet["design_date_set_sha256"],
        "design_date_set_canonical_bytes": DESIGN_DATE_SET_CANONICAL_BYTES,
        "stage0_eligibility_ledger_sha256": STAGE0_LEDGER_SHA256,
        "stage0_receipt_sha256": STAGE0_RECEIPT_SHA256,
        "stage0_access_trace_sha256": STAGE0_ACCESS_TRACE_SHA256,
        "stage0_reconciliation_sha256": STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": PACKET_RECEIPT_SHA256,
        "decision_packet_set_sha256": PACKET_SET_SHA256,
        "request_plan_sha256": packet["request_plan_sha256"],
        "request_plan_builder_sha256": packet["request_plan_builder_sha256"],
        "clock_tool_sha256": CLOCK_TOOL_SHA256,
        "request_count": EXPECTED_DESIGN_DATES,
        "expected_m1_rows": EXPECTED_DESIGN_DATES * 360,
        "first_design_date": DESIGN_START.isoformat(),
        "last_design_date": DESIGN_END.isoformat(),
        "canonical_create_new": True,
        "forbidden_field_scan": "PASS",
        "design_m1_opened": False,
        "validation_m1_opened": False,
        "holdout_opened": False,
        "economics_computed": False,
        "verdict": "REQUEST_PLAN_READY_FOR_INDEPENDENT_REVIEW",
    }
    for field, value in expected.items():
        _require(type(receipt[field]) is type(value) and receipt[field] == value, f"request receipt {field} mismatch")
    return receipt


def _parse_time(value: Any) -> datetime:
    _require(type(value) is str and value.endswith("Z"), "M1 UTC timestamp malformed")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING M1 UTC timestamp malformed") from exc
    normalized = parsed.astimezone(timezone.utc)
    _require(value == normalized.strftime("%Y-%m-%dT%H:%M:%SZ"), "M1 UTC timestamp is not canonical")
    return normalized


def _validate_bars(bars: list[dict]) -> None:
    _require(type(bars) is list and len(bars) == 360, "M1 day must contain exactly 360 bars")
    first = _parse_time(bars[0].get("time_utc"))
    _require((first.hour, first.minute, first.second) == (12, 1, 0), "M1 day must start at 12:01 UTC")
    for index, bar in enumerate(bars):
        _require(isinstance(bar, dict), "M1 bar must be an object")
        observed = _parse_time(bar.get("time_utc"))
        _require(observed == first + timedelta(minutes=index), "M1 day grid missing/duplicate/non-monotonic")
        numbers = []
        for field in ("bid_open", "bid_high", "bid_low", "bid_close"):
            value = bar.get(field)
            _require(type(value) in (int, float) and not isinstance(value, bool), f"M1 {field} malformed")
            numbers.append(float(value))
        opening, high, low, closing = numbers
        _require(all(math.isfinite(value) and value > 0 for value in numbers), "M1 price nonfinite/nonpositive")
        _require(high >= max(opening, closing) and low <= min(opening, closing) and high >= low, "M1 OHLC geometry invalid")
    last = _parse_time(bars[-1]["time_utc"])
    _require((last.hour, last.minute, last.second) == (18, 0, 0) and last.date() == first.date(), "M1 day must end at 18:00 UTC")


def simulate_trade(bars: list[dict], *, direction: int, atr20: float) -> dict:
    _require(type(direction) is int and direction in (-1, 1), "trade direction must be exact -1/+1 int")
    _require(type(atr20) in (int, float) and not isinstance(atr20, bool), "ATR20 malformed")
    atr = float(atr20)
    _require(math.isfinite(atr) and atr > 0, "ATR20 must be finite positive")
    _validate_bars(bars)
    entry = float(bars[0]["bid_open"])
    stop = entry - atr if direction == 1 else entry + atr
    entry_touch = float(bars[0]["bid_low"]) <= stop if direction == 1 else float(bars[0]["bid_high"]) >= stop
    if entry_touch:
        exit_bid = stop
        exit_time = bars[0]["time_utc"]
        reason = "STOP_TOUCH_ENTRY"
    else:
        exit_bid = None
        exit_time = None
        reason = None
        for bar in bars[1:-1]:
            opening = float(bar["bid_open"])
            adverse_gap = opening <= stop if direction == 1 else opening >= stop
            if adverse_gap:
                exit_bid = opening
                exit_time = bar["time_utc"]
                reason = "STOP_GAP"
                break
            touched = float(bar["bid_low"]) <= stop if direction == 1 else float(bar["bid_high"]) >= stop
            if touched:
                exit_bid = stop
                exit_time = bar["time_utc"]
                reason = "STOP_TOUCH"
                break
        if exit_bid is None:
            exit_bid = float(bars[-1]["bid_open"])
            exit_time = bars[-1]["time_utc"]
            reason = "TIME_EXIT_1800"
    gross_r = direction * (exit_bid - entry) / atr
    _require(math.isfinite(gross_r), "gross R is nonfinite")
    return {
        "entry_time_utc": bars[0]["time_utc"],
        "entry_bid": entry,
        "stop_bid": stop,
        "exit_time_utc": exit_time,
        "exit_bid": exit_bid,
        "exit_reason": reason,
        "gross_R": gross_r,
    }


def apply_cost(gross_r: float, *, atr20: float, round_trip_cost_pips: float) -> float:
    values = (gross_r, atr20, round_trip_cost_pips)
    _require(all(type(value) in (int, float) and not isinstance(value, bool) for value in values), "cost arithmetic input malformed")
    _require(all(math.isfinite(float(value)) for value in values), "cost arithmetic input nonfinite")
    _require(float(atr20) > 0 and float(round_trip_cost_pips) >= 0, "cost arithmetic input out of range")
    stop_pips = float(atr20) / 0.0001
    result = float(gross_r) - float(round_trip_cost_pips) / stop_pips
    _require(math.isfinite(result), "net R is nonfinite")
    return result


def profit_factor(values: list[float]) -> dict[str, Any]:
    _require(type(values) is list and bool(values), "profit-factor sample is empty")
    normalized = [float(value) for value in values]
    _require(all(math.isfinite(value) for value in normalized), "profit-factor sample nonfinite")
    gains = sum(value for value in normalized if value > 0)
    losses = -sum(value for value in normalized if value < 0)
    if losses == 0:
        if gains == 0:
            return {"status": "NO_WIN_NO_LOSS", "value": None}
        return {"status": "NO_LOSS", "value": None}
    return {"status": "FINITE", "value": gains / losses}


def expand_arms(stage_row: dict, packet: dict) -> list[dict]:
    _require(stage_row.get("opportunity_id") == packet.get("opportunity_id"), "ledger/packet opportunity mismatch")
    _require(stage_row.get("split") == packet.get("split") == "DESIGN", "non-DESIGN arm input")
    _require(packet.get("hypothesis_id") == HYPOTHESIS_ID, "packet hypothesis mismatch")
    if "packet_file_sha256" in packet:
        _require(packet["packet_file_sha256"] == stage_row.get("packet_file_sha256"), "packet hash identity mismatch")
    atr = packet.get("atr20")
    _require(type(atr) in (int, float) and not isinstance(atr, bool) and math.isfinite(float(atr)) and float(atr) > 0, "packet ATR20 malformed")
    definitions = (
        ("CONTROL_M252_ONLY", "control_m252_only_eligible", "control_m252_only_direction"),
        ("CONTROL_M6_ONLY", "control_m6_only_eligible", "control_m6_only_direction"),
        ("CHALLENGER_STACK", "challenger_stack_eligible", "challenger_stack_direction"),
        ("NEGATIVE_DISAGREE", "negative_disagree_eligible", "negative_disagree_direction"),
    )
    result = []
    for arm, eligible_field, direction_field in definitions:
        eligible = stage_row.get(eligible_field)
        direction = stage_row.get(direction_field)
        _require(type(eligible) is bool, f"{arm} eligibility malformed")
        if eligible:
            _require(type(direction) is int and direction in (-1, 1), f"{arm} direction malformed")
            result.append(
                {
                    "opportunity_id": stage_row["opportunity_id"],
                    "arm": arm,
                    "direction": direction,
                    "atr20": float(atr),
                    "packet_file_sha256": stage_row.get("packet_file_sha256"),
                }
            )
        else:
            _require(direction is None, f"{arm} ineligible direction must be null")
    _require(not (stage_row.get("challenger_stack_eligible") and stage_row.get("negative_disagree_eligible")), "STACK/DISAGREE arm conflict")
    return result


def validate_arm_counts(counts: dict[str, int]) -> None:
    _require(counts == EXPECTED_ARM_COUNTS, f"arm count mismatch: {counts}")
    _require(sum(counts.values()) == EXPECTED_TOTAL_ARM_ROWS, "total arm-row count mismatch")


def _sample_sharpe(values: list[float]) -> float:
    _require(len(values) >= 2 and all(math.isfinite(float(value)) for value in values), "Sharpe sample invalid")
    deviation = statistics.stdev(values)
    if deviation == 0:
        return 0.0
    return statistics.fmean(values) / deviation


def _shape(values: list[float]) -> tuple[float, float]:
    mean = statistics.fmean(values)
    centered = [value - mean for value in values]
    m2 = statistics.fmean(value * value for value in centered)
    if m2 == 0:
        return 0.0, 3.0
    m3 = statistics.fmean(value**3 for value in centered)
    m4 = statistics.fmean(value**4 for value in centered)
    return m3 / (m2**1.5), m4 / (m2 * m2)


def compute_dsr(arm_returns: dict[str, list[float]], dsr_path: Path) -> dict:
    _require(set(arm_returns) == set(ARMS), "DSR requires exactly four frozen arm trials")
    raw = read_stable_file(dsr_path)
    _require(sha256_bytes(raw) == DSR_TOOL_SHA256, "canonical DSR tool hash mismatch")
    spec = importlib.util.spec_from_file_location("trendstack_002_canonical_dsr", dsr_path)
    _require(spec is not None and spec.loader is not None, "canonical DSR tool cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sharpes = {arm: _sample_sharpe(arm_returns[arm]) for arm in ARMS}
    variance = statistics.variance(sharpes.values())
    challenger = [float(value) for value in arm_returns["CHALLENGER_STACK"]]
    skew, kurtosis = _shape(challenger)
    value = float(
        module.dsr(
            sharpes["CHALLENGER_STACK"],
            len(challenger),
            skew,
            kurtosis,
            variance,
            4,
        )
    )
    _require(math.isfinite(value) and 0 <= value <= 1, "DSR result invalid")
    return {
        "dsr": value,
        "n_trials": 4,
        "var_sr_trials": variance,
        "arm_sharpes": sharpes,
        "challenger_skew": skew,
        "challenger_non_excess_kurtosis": kurtosis,
        "dsr_tool_sha256": DSR_TOOL_SHA256,
    }


def _pf_pass(pf: dict, threshold: float, *, strict: bool) -> bool:
    _require(isinstance(pf, dict) and set(pf) == {"status", "value"}, "PF status object malformed")
    if pf["status"] == "NO_LOSS":
        return True
    if pf["status"] != "FINITE" or type(pf["value"]) not in (int, float) or isinstance(pf["value"], bool):
        return False
    value = float(pf["value"])
    return value > threshold if strict else value >= threshold


def evaluate_gate_values(values: dict[str, Any]) -> dict:
    required = {
        "cadence",
        "pf_1_50",
        "pf_2_25",
        "pf_3_00",
        "mean_net_r_1_50",
        "total_net_r_1_50",
        "positive_years",
        "dsr_1_50",
        "stack_pf_delta_vs_best_standalone",
        "stack_mean_delta_vs_best_standalone",
        "stack_pf_delta_vs_disagree",
        "stack_mean_delta_vs_disagree",
    }
    _require(set(values) == required, "gate-value schema mismatch")
    checks = [
        ("G01", "cadence_2_to_5_inclusive", 2.0 <= float(values["cadence"]) <= 5.0, values["cadence"], "2.0<=x<=5.0"),
        ("G02", "pf_1_50_strict", _pf_pass(values["pf_1_50"], 1.30, strict=True), values["pf_1_50"], ">1.30"),
        ("G03", "pf_2_25", _pf_pass(values["pf_2_25"], 1.25, strict=False), values["pf_2_25"], ">=1.25"),
        ("G04", "pf_3_00", _pf_pass(values["pf_3_00"], 1.00, strict=False), values["pf_3_00"], ">=1.00"),
        ("G05", "mean_net_r_1_50", float(values["mean_net_r_1_50"]) >= 0.08, values["mean_net_r_1_50"], ">=0.08"),
        ("G06", "total_net_r_1_50_strict", float(values["total_net_r_1_50"]) > 0.0, values["total_net_r_1_50"], ">0"),
        ("G07", "positive_design_years", type(values["positive_years"]) is int and values["positive_years"] >= 4, values["positive_years"], ">=4"),
        ("G08", "dsr_four_trials", float(values["dsr_1_50"]) >= 0.95, values["dsr_1_50"], ">=0.95"),
        ("G09", "pf_delta_best_standalone", float(values["stack_pf_delta_vs_best_standalone"]) >= 0.15, values["stack_pf_delta_vs_best_standalone"], ">=0.15"),
        ("G10", "mean_delta_best_standalone", float(values["stack_mean_delta_vs_best_standalone"]) >= 0.05, values["stack_mean_delta_vs_best_standalone"], ">=0.05"),
        ("G11", "pf_delta_disagree", float(values["stack_pf_delta_vs_disagree"]) >= 0.15, values["stack_pf_delta_vs_disagree"], ">=0.15"),
        ("G12", "mean_delta_disagree", float(values["stack_mean_delta_vs_disagree"]) >= 0.05, values["stack_mean_delta_vs_disagree"], ">=0.05"),
    ]
    gates = [
        {"gate_id": gate_id, "name": name, "status": "PASS" if passed else "FAIL", "observed": observed, "threshold": threshold}
        for gate_id, name, passed, observed, threshold in checks
    ]
    return {"gates": gates, "all_pass": all(passed for _, _, passed, _, _ in checks)}


def build_daily_book(trade_rows: list[dict]) -> list[dict]:
    by_day_arm = {}
    for trade in trade_rows:
        day = trade.get("opportunity_id")
        arm = trade.get("arm")
        _require(type(day) is str and arm in ARMS, "daily-book trade identity malformed")
        _require(DESIGN_START.isoformat() <= day <= DESIGN_END.isoformat(), "daily-book trade outside DESIGN")
        key = (day, arm)
        _require(key not in by_day_arm, "duplicate arm/day trade")
        by_day_arm[key] = trade
    rows = []
    cursor = DESIGN_START
    while cursor <= DESIGN_END:
        day = cursor.isoformat()
        row = {"schema_version": DAILY_SCHEMA, "hypothesis_id": HYPOTHESIS_ID, "date_utc": day}
        for arm in ARMS:
            trade = by_day_arm.get((day, arm))
            for suffix, _ in COSTS:
                value = 0.0 if trade is None else float(trade[f"net_R_{suffix}"])
                _require(math.isfinite(value), "daily-book value nonfinite")
                row[f"{arm}_net_R_{suffix}"] = value
        rows.append(row)
        cursor += timedelta(days=1)
    _require(len(rows) == DESIGN_DAYS, "common daily book day count mismatch")
    return rows


def _finite_pf_value(pf: dict) -> float | None:
    if pf["status"] == "FINITE":
        return float(pf["value"])
    return None


def _pf_delta(challenger: dict, comparator: dict) -> tuple[float, str]:
    if challenger["status"] == "NO_LOSS" and comparator["status"] != "NO_LOSS":
        return 1.0e308, "CHALLENGER_NO_LOSS"
    if challenger["status"] == "NO_LOSS" and comparator["status"] == "NO_LOSS":
        return 0.0, "BOTH_NO_LOSS"
    if comparator["status"] == "NO_LOSS":
        return -1.0e308, "COMPARATOR_NO_LOSS"
    left = _finite_pf_value(challenger)
    right = _finite_pf_value(comparator)
    if left is None or right is None:
        return -1.0e308, "UNDEFINED"
    return left - right, "FINITE"


def _summarize_arm(rows: list[dict]) -> dict:
    _require(bool(rows), "arm has no evaluated trades")
    result = {"trade_count": len(rows)}
    for suffix, _ in COSTS:
        values = [float(row[f"net_R_{suffix}"]) for row in rows]
        result[f"cost_{suffix}"] = {
            "profit_factor": profit_factor(values),
            "mean_net_R": statistics.fmean(values),
            "total_net_R": sum(values),
        }
    if rows[0]["arm"] == "CHALLENGER_STACK":
        yearly = {}
        for year in range(2016, 2021):
            yearly[str(year)] = sum(float(row["net_R_1_50"]) for row in rows if row["opportunity_id"].startswith(str(year)))
        result["yearly_net_R_1_50"] = yearly
        result["positive_years_1_50"] = sum(value > 0 for value in yearly.values())
    return result


def _economic_result(trade_rows: list[dict], dsr_path: Path) -> dict:
    grouped = {arm: [row for row in trade_rows if row["arm"] == arm] for arm in ARMS}
    metrics = {arm: _summarize_arm(rows) for arm, rows in grouped.items()}
    returns = {arm: [float(row["net_R_1_50"]) for row in rows] for arm, rows in grouped.items()}
    dsr_result = compute_dsr(returns, dsr_path)
    challenger = metrics["CHALLENGER_STACK"]
    m252 = metrics["CONTROL_M252_ONLY"]
    m6 = metrics["CONTROL_M6_ONLY"]
    disagree = metrics["NEGATIVE_DISAGREE"]
    stack_pf = challenger["cost_1_50"]["profit_factor"]
    standalone_pf = max(
        (m252["cost_1_50"]["profit_factor"], m6["cost_1_50"]["profit_factor"]),
        key=lambda item: float("inf") if item["status"] == "NO_LOSS" else -float("inf") if item["value"] is None else item["value"],
    )
    pf_control_delta, pf_control_status = _pf_delta(stack_pf, standalone_pf)
    pf_disagree_delta, pf_disagree_status = _pf_delta(stack_pf, disagree["cost_1_50"]["profit_factor"])
    mean_control = max(m252["cost_1_50"]["mean_net_R"], m6["cost_1_50"]["mean_net_R"])
    gate_values = {
        "cadence": challenger["trade_count"] / ELAPSED_WEEKS,
        "pf_1_50": challenger["cost_1_50"]["profit_factor"],
        "pf_2_25": challenger["cost_2_25"]["profit_factor"],
        "pf_3_00": challenger["cost_3_00"]["profit_factor"],
        "mean_net_r_1_50": challenger["cost_1_50"]["mean_net_R"],
        "total_net_r_1_50": challenger["cost_1_50"]["total_net_R"],
        "positive_years": challenger["positive_years_1_50"],
        "dsr_1_50": dsr_result["dsr"],
        "stack_pf_delta_vs_best_standalone": pf_control_delta,
        "stack_mean_delta_vs_best_standalone": challenger["cost_1_50"]["mean_net_R"] - mean_control,
        "stack_pf_delta_vs_disagree": pf_disagree_delta,
        "stack_mean_delta_vs_disagree": challenger["cost_1_50"]["mean_net_R"] - disagree["cost_1_50"]["mean_net_R"],
    }
    gate_result = evaluate_gate_values(gate_values)
    return {
        "schema_version": RESULT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "engineering_status": "PASS",
        "verdict": "PROBE_SURVIVOR_DESIGN_ONLY" if gate_result["all_pass"] else "KILL",
        "cost_status": "UNVERIFIED_PROXY_KILL_ONLY",
        "trial_count": 4,
        "cost_tiers_are_trials": False,
        "arm_metrics": metrics,
        "dsr": dsr_result,
        "relative_pf_status": {
            "best_standalone": pf_control_status,
            "negative_disagree": pf_disagree_status,
        },
        "gate_values": gate_values,
        "gates": gate_result["gates"],
        "validation_m1_opened": False,
        "holdout_opened": False,
    }


def _write_new(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING create-new evaluation artifact failed") from exc


def persist_evaluation(
    output_root: Path,
    trade_rows: list[dict],
    daily_book: list[dict],
    economic_result: dict,
    upstream_hashes: dict[str, str],
    evaluator_sha256: str,
) -> dict:
    _require(len(trade_rows) == EXPECTED_TOTAL_ARM_ROWS, "evaluated arm-row count mismatch")
    _require(len(daily_book) == DESIGN_DAYS, "daily-book count mismatch")
    _require(economic_result.get("trial_count") == 4, "trial count mismatch")
    _require(SHA256_RE.fullmatch(evaluator_sha256 or "") is not None, "evaluator hash malformed")
    _require(set(upstream_hashes) == EVALUATION_UPSTREAM_FIELDS, "evaluation upstream hash schema mismatch")
    for field, value in upstream_hashes.items():
        _require(type(value) is str and SHA256_RE.fullmatch(value) is not None, f"evaluation upstream hash malformed: {field}")
    _require(upstream_hashes["evaluator_tool_sha256"] == evaluator_sha256, "evaluation evaluator hash mismatch")
    root = Path(output_root)
    try:
        root.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING evaluation output root must be create-new") from exc
    trade_payload = b"".join(canonical_json_bytes(row) + b"\n" for row in trade_rows)
    daily_payload = b"".join(canonical_json_bytes(row) + b"\n" for row in daily_book)
    result_payload = canonical_json_bytes(economic_result) + b"\n"
    _write_new(root / "design_trade_ledger.jsonl", trade_payload)
    _write_new(root / "design_daily_book.jsonl", daily_payload)
    _write_new(root / "design_economic_result.json", result_payload)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        **upstream_hashes,
        "evaluator_sha256": evaluator_sha256,
        "design_trade_ledger_sha256": sha256_bytes(trade_payload),
        "design_daily_book_sha256": sha256_bytes(daily_payload),
        "design_economic_result_sha256": sha256_bytes(result_payload),
        "evaluated_arm_rows": len(trade_rows),
        "daily_book_days": len(daily_book),
        "trial_count": 4,
        "engineering_status": "PASS",
        "verdict": economic_result["verdict"],
        "validation_m1_opened": False,
        "holdout_opened": False,
        "promotion_authorized": False,
    }
    _write_new(root / "design_evaluation_receipt.json", canonical_json_bytes(receipt) + b"\n")
    return receipt


def _safe_child(root: Path, relative: str) -> Path:
    logical = PurePosixPath(relative)
    _require(not logical.is_absolute() and logical.parts and all(part not in {"", ".", ".."} for part in logical.parts), "unsafe relative input path")
    root_checked = _validate_component_chain(root)
    target = _validate_component_chain(root / Path(*logical.parts))
    try:
        target.relative_to(root_checked)
    except ValueError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING input path escapes root") from exc
    return target


def _canonical_row_content_sha256(records: list[dict]) -> str:
    payload = b""
    for record in records:
        normalized = {
            key: int(value) if key in {"utc_offset_h", "tick_volume", "spread_points", "real_volume"}
            else float(value) if key.startswith("bid_")
            else str(value)
            for key, value in record.items()
        }
        payload += canonical_json_bytes(normalized) + b"\n"
    return sha256_bytes(payload)


def _read_day_from_shard(
    path: Path,
    expected_sha256: str,
    *,
    expected_day: str,
    expected_request: dict,
    expected_content_sha256: str | None = None,
) -> list[dict]:
    _require(type(expected_day) is str and DESIGN_START.isoformat() <= expected_day <= DESIGN_END.isoformat(), "shard expected day is outside DESIGN")
    _require(expected_request.get("opportunity_id") == expected_day, "shard/request opportunity mismatch")
    _require(type(expected_request.get("request_id")) is str, "shard request ID malformed")
    raw = read_stable_file(path)
    _require(type(expected_sha256) is str and SHA256_RE.fullmatch(expected_sha256) is not None and sha256_bytes(raw) == expected_sha256, "M1 shard hash mismatch")
    parquet = pq.ParquetFile(pa.BufferReader(raw))
    _require(parquet.metadata.num_row_groups == 1 and parquet.metadata.num_rows == 360, "M1 shard parquet geometry mismatch")
    table = parquet.read()
    _require(table.column_names == RAW_M1_COLUMNS, "M1 shard column schema mismatch")
    records = table.to_pylist()
    _require(len(records) == 360, "M1 shard row count mismatch")
    for record in records:
        _require(set(record) == set(RAW_M1_COLUMNS), "M1 shard record schema mismatch")
        _require(record["request_id"] == expected_request["request_id"], "M1 shard request ID mismatch")
        _require(record["opportunity_id"] == expected_day, "M1 shard opportunity mismatch")
        _require(type(record["utc_offset_h"]) is int and not isinstance(record["utc_offset_h"], bool) and record["utc_offset_h"] in (2, 3), "M1 shard UTC offset malformed")
        _require(type(record["time_server"]) is str, "M1 server timestamp malformed")
        try:
            server = datetime.fromisoformat(record["time_server"])
        except ValueError as exc:
            raise InvalidEngineering("INVALID_ENGINEERING M1 server timestamp malformed") from exc
        _require(server.tzinfo is None, "M1 server timestamp must be naive wall time")
        _require(record["time_server"] == server.strftime("%Y-%m-%dT%H:%M:%S"), "M1 server timestamp is not canonical")
        utc = _parse_time(record["time_utc"])
        _require(utc.date().isoformat() == expected_day, "M1 shard contains cross-day/validation/holdout timestamp")
        _require(server - utc.replace(tzinfo=None) == timedelta(hours=record["utc_offset_h"]), "M1 server/UTC provenance mismatch")
        for field in ("tick_volume", "spread_points", "real_volume"):
            _require(type(record[field]) is int and not isinstance(record[field], bool) and record[field] >= 0, f"M1 {field} malformed")
    content_sha = _canonical_row_content_sha256(records)
    if expected_content_sha256 is not None:
        _require(type(expected_content_sha256) is str and SHA256_RE.fullmatch(expected_content_sha256) is not None and content_sha == expected_content_sha256, "M1 canonical row content hash mismatch")
    bars = [
        {
            "time_utc": row["time_utc"],
            "bid_open": row["bid_open"],
            "bid_high": row["bid_high"],
            "bid_low": row["bid_low"],
            "bid_close": row["bid_close"],
        }
        for row in records
    ]
    _validate_bars(bars)
    _require(all(_parse_time(bar["time_utc"]).date().isoformat() == expected_day for bar in bars), "M1 bars escape frozen DESIGN day")
    return bars


def _verify_authority_files(
    packet: dict,
    *,
    source_plan_path: Path,
    design_plan_path: Path,
    design_plan_v2_path: Path,
    stage0_ledger_path: Path,
    stage0_receipt_path: Path,
    stage0_access_trace_path: Path,
    stage0_reconciliation_path: Path,
    decision_packet_manifest_path: Path,
    decision_packet_receipt_path: Path,
    request_plan_path: Path,
    request_receipt_path: Path,
    request_builder_path: Path,
    acquisition_tool_path: Path,
    clock_path: Path,
    dsr_path: Path,
) -> None:
    bindings = (
        (source_plan_path, "source_plan_sha256"),
        (design_plan_path, "design_plan_sha256"),
        (design_plan_v2_path, "design_plan_v2_sha256"),
        (stage0_ledger_path, "stage0_eligibility_ledger_sha256"),
        (stage0_receipt_path, "stage0_receipt_sha256"),
        (stage0_access_trace_path, "stage0_access_trace_sha256"),
        (stage0_reconciliation_path, "stage0_reconciliation_sha256"),
        (decision_packet_manifest_path, "decision_packet_manifest_sha256"),
        (decision_packet_receipt_path, "decision_packet_receipt_sha256"),
        (request_plan_path, "request_plan_sha256"),
        (request_receipt_path, "request_plan_receipt_sha256"),
        (request_builder_path, "request_plan_builder_sha256"),
        (acquisition_tool_path, "acquisition_tool_sha256"),
        (clock_path, "clock_tool_sha256"),
        (dsr_path, "dsr_tool_sha256"),
    )
    for path, field in bindings:
        _require(sha256_bytes(read_stable_file(path)) == packet[field], f"authority file hash mismatch: {field}")
    _require(sha256_bytes(read_stable_file(Path(__file__))) == packet["evaluator_tool_sha256"], "evaluator self-hash mismatch")


def _validate_runtime_provenance(provenance: Any, packet: dict, run_packet_sha256: str) -> dict[str, str]:
    _require(isinstance(provenance, dict) and set(provenance) == RUNTIME_PROVENANCE_FIELDS, "M1 runtime provenance schema mismatch")
    expected = {
        "clock_tool_sha256": packet["clock_tool_sha256"],
        "acquisition_tool_sha256": packet["acquisition_tool_sha256"],
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "run_packet_sha256": run_packet_sha256,
    }
    for field, value in expected.items():
        _require(provenance[field] == value, f"M1 runtime provenance {field} mismatch")
    for field in (
        "terminal_executable_sha256",
        "python_executable_sha256",
        "metatrader5_native_module_sha256",
    ):
        _require(type(provenance[field]) is str and SHA256_RE.fullmatch(provenance[field]) is not None, f"M1 runtime {field} malformed")
    for field in (
        "terminal_executable_label",
        "python_executable_label",
        "metatrader5_version",
        "metatrader5_native_module_label",
        "clock_tool_label",
        "acquisition_tool_label",
        "pandas_version",
        "pyarrow_version",
    ):
        _require(type(provenance[field]) is str and bool(provenance[field]), f"M1 runtime {field} malformed")
    guard = provenance["account_guard"]
    _require(isinstance(guard, dict) and set(guard) == ACCOUNT_GUARD_FIELDS, "M1 account guard schema mismatch")
    exact_guard = {
        "terminal_trade_allowed": False,
        "terminal_connected": True,
        "account_mode": "DEMO",
        "server": "FivePercentOnline-Real",
        "company": "Five Percent Online Ltd",
        "symbol": "EURUSD",
        "symbol_digits": 5,
        "symbol_point": 0.00001,
        "symbol_selected": True,
        "symbol_visible": True,
    }
    _require(type(guard["terminal_build"]) is int and not isinstance(guard["terminal_build"], bool), "M1 terminal build malformed")
    for field, value in exact_guard.items():
        _require(type(guard[field]) is type(value) and guard[field] == value, f"M1 account guard {field} mismatch")
    return {field: provenance[field] for field in RUNTIME_HASH_FIELDS}


def _read_m1_receipt(m1_root: Path, packet: dict, run_packet_sha256: str) -> tuple[dict, str, dict[str, str]]:
    receipt_raw = read_stable_file(m1_root / "design_m1_source_receipt.json")
    receipt = _parse_json(receipt_raw, "DESIGN M1 receipt")
    _require(receipt_raw == canonical_json_bytes(receipt) + b"\n", "M1 receipt is not canonical")
    _require(set(receipt) == M1_RECEIPT_FIELDS, "M1 receipt schema mismatch")
    expected = {
        "schema_version": M1_RECEIPT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "request_plan_sha256": packet["request_plan_sha256"],
        "request_plan_receipt_sha256": packet["request_plan_receipt_sha256"],
        "run_packet_sha256": run_packet_sha256,
        "request_count": EXPECTED_DESIGN_DATES,
        "shard_file_count": EXPECTED_DESIGN_DATES,
        "m1_rows": EXPECTED_DESIGN_DATES * 360,
        "first_design_date": DESIGN_START.isoformat(),
        "last_design_date": DESIGN_END.isoformat(),
        "all_shard_hashes_verified": True,
        "design_m1_opened": True,
        "validation_m1_opened": False,
        "holdout_opened": False,
        "economics_computed": False,
        "physical_partition_status": "PASS",
        "verdict": "DESIGN_M1_SOURCE_READY_FOR_OFFLINE_EVALUATION",
    }
    for field, value in expected.items():
        _require(type(receipt[field]) is type(value) and receipt[field] == value, f"M1 receipt {field} mismatch")
    _require(type(receipt["design_m1_manifest_sha256"]) is str and SHA256_RE.fullmatch(receipt["design_m1_manifest_sha256"]) is not None, "M1 manifest receipt hash malformed")
    runtime_hashes = _validate_runtime_provenance(receipt["runtime_provenance"], packet, run_packet_sha256)
    return receipt, sha256_bytes(receipt_raw), runtime_hashes


def _validate_manifest_row(row: dict, request: dict, runtime_hashes: dict[str, str], packet: dict, run_packet_sha256: str) -> None:
    _require(set(row) == M1_MANIFEST_FIELDS, "M1 manifest row schema mismatch")
    day = request["opportunity_id"]
    expected_path = f"raw_m1/DESIGN/{day}/1201_1800.parquet"
    exact = {
        "schema_version": M1_MANIFEST_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "request_id": request["request_id"],
        "opportunity_id": day,
        "split": "DESIGN",
        "shard_path": expected_path,
        "rows": 360,
        "row_groups": 1,
        "first_utc_time": f"{day}T12:01:00Z",
        "last_utc_time": f"{day}T18:00:00Z",
        "geometry_status": "PASS",
        "unique_chronological_grid_status": "PASS",
        "holdout_rows_received": 0,
        "request_plan_sha256": packet["request_plan_sha256"],
        "request_plan_receipt_sha256": packet["request_plan_receipt_sha256"],
        "run_packet_sha256": run_packet_sha256,
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "runtime_hashes": runtime_hashes,
    }
    for field, value in exact.items():
        _require(type(row[field]) is type(value) and row[field] == value, f"M1 manifest {field} mismatch")
    for field in ("canonical_row_content_sha256", "shard_sha256"):
        _require(type(row[field]) is str and SHA256_RE.fullmatch(row[field]) is not None, f"M1 manifest {field} malformed")
    _require(type(row["shard_bytes"]) is int and not isinstance(row["shard_bytes"], bool) and row["shard_bytes"] > 0, "M1 manifest shard bytes malformed")


def _validate_physical_shard_tree(m1_root: Path, expected_shards: list[str]) -> None:
    raw_root = _validate_component_chain(m1_root / "raw_m1")
    expected_files = sorted(expected_shards)
    allowed_directories = set()
    for relative in expected_files:
        logical = PurePosixPath(relative)
        _require(logical.parts[:2] == ("raw_m1", "DESIGN") and len(logical.parts) == 4, "M1 expected shard path malformed")
        _require(DESIGN_START.isoformat() <= logical.parts[2] <= DESIGN_END.isoformat(), "M1 expected shard path outside DESIGN")
        allowed_directories.add("raw_m1/DESIGN")
        allowed_directories.add(f"raw_m1/DESIGN/{logical.parts[2]}")
    observed_files = []
    observed_directories = set()
    for candidate in raw_root.rglob("*"):
        metadata = _lstat_no_reparse(candidate)
        relative = candidate.relative_to(m1_root).as_posix()
        if stat.S_ISDIR(metadata.st_mode):
            observed_directories.add(relative)
        elif stat.S_ISREG(metadata.st_mode):
            _require(metadata.st_nlink == 1, "M1 physical shard hardlink is forbidden")
            observed_files.append(relative)
        else:
            raise InvalidEngineering("INVALID_ENGINEERING unsupported object in M1 physical tree")
    _require(sorted(observed_files) == expected_files, "M1 physical shard file set mismatch")
    _require(observed_directories == allowed_directories, "M1 physical directory set contains validation/holdout/extra paths")


def _load_frozen_inputs(
    stage0_ledger_path: Path,
    stage0_receipt_path: Path,
    decision_packet_root: Path,
    m1_root: Path,
    request_rows: list[dict],
    authority_packet: dict,
    run_packet_sha256: str,
) -> tuple[list[dict], dict[str, list[dict]], dict[str, str]]:
    receipt_raw = read_stable_file(stage0_receipt_path)
    _require(sha256_bytes(receipt_raw) == STAGE0_RECEIPT_SHA256, "Stage-0 receipt hash mismatch")
    stage_receipt = _parse_json(receipt_raw, "Stage-0 receipt")
    expected_receipt_fields = {
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
    for field, expected in expected_receipt_fields.items():
        _require(stage_receipt.get(field) == expected, f"Stage-0 receipt {field} mismatch")
    ledger_raw = read_stable_file(stage0_ledger_path)
    _require(sha256_bytes(ledger_raw) == STAGE0_LEDGER_SHA256, "Stage-0 ledger hash mismatch")
    stage_rows = [row for row in _parse_jsonl(ledger_raw, "Stage-0 ledger") if row.get("split") == "DESIGN"]
    _require(len(stage_rows) == EXPECTED_DESIGN_DATES, "Stage-0 DESIGN date count mismatch")
    m1_root = _validate_component_chain(m1_root)
    _require(_canonical_path_text(m1_root) == authority_packet["design_m1_output_root"], "M1 root does not match run packet")
    m1_receipt, m1_receipt_sha256, runtime_hashes = _read_m1_receipt(m1_root, authority_packet, run_packet_sha256)
    manifest_raw = read_stable_file(m1_root / "design_m1_manifest.jsonl")
    _require(sha256_bytes(manifest_raw) == m1_receipt["design_m1_manifest_sha256"], "M1 manifest hash mismatch")
    manifest = _parse_jsonl(manifest_raw, "DESIGN M1 manifest")
    _require(len(manifest) == EXPECTED_DESIGN_DATES, "M1 manifest date count mismatch")
    stage_by_date = {row.get("opportunity_id"): row for row in stage_rows}
    request_by_date = {row.get("opportunity_id"): row for row in request_rows}
    manifest_by_date = {row.get("opportunity_id"): row for row in manifest}
    _require(len(stage_by_date) == len(request_by_date) == len(manifest_by_date) == EXPECTED_DESIGN_DATES, "duplicate/missing DESIGN join identity")
    _require(set(stage_by_date) == set(request_by_date) == set(manifest_by_date), "DESIGN join sets differ")
    expected_shards = sorted(row.get("shard_path") for row in manifest)
    _validate_physical_shard_tree(m1_root, expected_shards)
    packet_root = _validate_component_chain(decision_packet_root)
    all_trade_rows = []
    arm_counts = {arm: 0 for arm in ARMS}
    for day in sorted(stage_by_date):
        _require("2016-01-04" <= day < "2021-01-01", "non-DESIGN join date")
        stage = stage_by_date[day]
        relative_packet = stage.get("packet_path")
        _require(relative_packet == f"DESIGN/{day}.json", "Stage-0 packet path mismatch")
        packet_path = _safe_child(packet_root, relative_packet)
        packet_raw = read_stable_file(packet_path)
        _require(sha256_bytes(packet_raw) == stage.get("packet_file_sha256"), "Stage-0 packet file hash mismatch")
        decision_packet = _parse_json(packet_raw, relative_packet)
        request = request_by_date[day]
        manifest_row = manifest_by_date[day]
        _validate_manifest_row(manifest_row, request, runtime_hashes, authority_packet, run_packet_sha256)
        expected_shard = f"raw_m1/DESIGN/{day}/1201_1800.parquet"
        shard_path = _safe_child(m1_root, expected_shard)
        _require(len(read_stable_file(shard_path)) == manifest_row["shard_bytes"], "M1 shard byte size mismatch")
        day_bars = _read_day_from_shard(
            shard_path,
            manifest_row["shard_sha256"],
            expected_day=day,
            expected_request=request,
            expected_content_sha256=manifest_row["canonical_row_content_sha256"],
        )
        for arm_input in expand_arms(stage, decision_packet):
            simulation = simulate_trade(day_bars, direction=arm_input["direction"], atr20=arm_input["atr20"])
            trade = {
                "schema_version": TRADE_SCHEMA,
                "hypothesis_id": HYPOTHESIS_ID,
                "opportunity_id": day,
                "request_id": request["request_id"],
                "arm": arm_input["arm"],
                "direction": arm_input["direction"],
                "atr20": arm_input["atr20"],
                "packet_file_sha256": stage["packet_file_sha256"],
                "m1_shard_sha256": manifest_row["shard_sha256"],
                **simulation,
            }
            for suffix, cost in COSTS:
                trade[f"net_R_{suffix}"] = apply_cost(simulation["gross_R"], atr20=arm_input["atr20"], round_trip_cost_pips=cost)
            canonical_json_bytes(trade)
            all_trade_rows.append(trade)
            arm_counts[arm_input["arm"]] += 1
    validate_arm_counts(arm_counts)
    upstream = {
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "stage0_eligibility_ledger_sha256": STAGE0_LEDGER_SHA256,
        "stage0_receipt_sha256": STAGE0_RECEIPT_SHA256,
        "stage0_access_trace_sha256": STAGE0_ACCESS_TRACE_SHA256,
        "stage0_reconciliation_sha256": STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": PACKET_RECEIPT_SHA256,
        "decision_packet_set_sha256": PACKET_SET_SHA256,
        "request_plan_sha256": authority_packet["request_plan_sha256"],
        "request_plan_receipt_sha256": authority_packet["request_plan_receipt_sha256"],
        "run_packet_sha256": run_packet_sha256,
        "request_plan_builder_sha256": authority_packet["request_plan_builder_sha256"],
        "acquisition_tool_sha256": authority_packet["acquisition_tool_sha256"],
        "evaluator_tool_sha256": authority_packet["evaluator_tool_sha256"],
        "clock_tool_sha256": authority_packet["clock_tool_sha256"],
        "dsr_tool_sha256": authority_packet["dsr_tool_sha256"],
        "design_m1_manifest_sha256": sha256_bytes(manifest_raw),
        "design_m1_source_receipt_sha256": m1_receipt_sha256,
    }
    return all_trade_rows, {day: [] for day in stage_by_date}, upstream


def evaluate_design(
    *,
    run_packet_path: Path,
    stage0_ledger_path: Path,
    stage0_receipt_path: Path,
    decision_packet_root: Path,
    request_plan_path: Path,
    request_receipt_path: Path,
    m1_root: Path,
    output_root: Path,
    dsr_path: Path,
    source_plan_path: Path = DEFAULT_SOURCE_PLAN_PATH,
    design_plan_path: Path = DEFAULT_DESIGN_PLAN_PATH,
    design_plan_v2_path: Path = DEFAULT_DESIGN_PLAN_V2_PATH,
    stage0_access_trace_path: Path = DEFAULT_STAGE0_ROOT / "stage0_access_trace.jsonl",
    stage0_reconciliation_path: Path = DEFAULT_STAGE0_ROOT / "stage0_reconciliation.json",
    decision_packet_manifest_path: Path | None = None,
    decision_packet_receipt_path: Path | None = None,
    request_builder_path: Path = DEFAULT_REQUEST_BUILDER_PATH,
    acquisition_tool_path: Path = DEFAULT_ACQUISITION_PATH,
    clock_path: Path = DEFAULT_CLOCK_PATH,
) -> dict:
    authority_packet, run_packet_sha256 = read_run_packet(run_packet_path)
    canonical_m1_root = Path(_canonical_path_text(m1_root))
    _require(Path(_canonical_path_text(request_plan_path)) == canonical_m1_root / "design_request_plan.jsonl", "request plan is outside canonical DESIGN M1 root")
    _require(Path(_canonical_path_text(request_receipt_path)) == canonical_m1_root / "design_request_plan_receipt.json", "request receipt is outside canonical DESIGN M1 root")
    _require(Path(_canonical_path_text(output_root)) == Path(_canonical_path_text(DEFAULT_EVALUATION_ROOT)), "evaluation output root is not canonical")
    manifest_path = decision_packet_root.parent / "decision_packet_manifest.jsonl" if decision_packet_manifest_path is None else decision_packet_manifest_path
    packet_receipt_path = decision_packet_root.parent / "decision_packet_receipt.json" if decision_packet_receipt_path is None else decision_packet_receipt_path
    canonical_paths = {
        "source plan": (source_plan_path, DEFAULT_SOURCE_PLAN_PATH),
        "design plan": (design_plan_path, DEFAULT_DESIGN_PLAN_PATH),
        "design plan V2": (design_plan_v2_path, DEFAULT_DESIGN_PLAN_V2_PATH),
        "Stage-0 ledger": (stage0_ledger_path, DEFAULT_STAGE0_ROOT / "stage0_eligibility_ledger.jsonl"),
        "Stage-0 receipt": (stage0_receipt_path, DEFAULT_STAGE0_ROOT / "stage0_receipt.json"),
        "Stage-0 trace": (stage0_access_trace_path, DEFAULT_STAGE0_ROOT / "stage0_access_trace.jsonl"),
        "Stage-0 reconciliation": (stage0_reconciliation_path, DEFAULT_STAGE0_ROOT / "stage0_reconciliation.json"),
        "decision packet root": (decision_packet_root, DEFAULT_DECISION_PACKET_ROOT),
        "decision manifest": (manifest_path, DEFAULT_DECISION_SOURCE_ROOT / "decision_packet_manifest.jsonl"),
        "decision receipt": (packet_receipt_path, DEFAULT_DECISION_SOURCE_ROOT / "decision_packet_receipt.json"),
        "request builder": (request_builder_path, DEFAULT_REQUEST_BUILDER_PATH),
        "acquisition tool": (acquisition_tool_path, DEFAULT_ACQUISITION_PATH),
        "clock tool": (clock_path, DEFAULT_CLOCK_PATH),
        "DSR tool": (dsr_path, WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "dsr.py"),
    }
    for label, (observed, expected) in canonical_paths.items():
        _require(Path(_canonical_path_text(observed)) == Path(_canonical_path_text(expected)), f"{label} path is not canonical")
    _verify_authority_files(
        authority_packet,
        source_plan_path=source_plan_path,
        design_plan_path=design_plan_path,
        design_plan_v2_path=design_plan_v2_path,
        stage0_ledger_path=stage0_ledger_path,
        stage0_receipt_path=stage0_receipt_path,
        stage0_access_trace_path=stage0_access_trace_path,
        stage0_reconciliation_path=stage0_reconciliation_path,
        decision_packet_manifest_path=manifest_path,
        decision_packet_receipt_path=packet_receipt_path,
        request_plan_path=request_plan_path,
        request_receipt_path=request_receipt_path,
        request_builder_path=request_builder_path,
        acquisition_tool_path=acquisition_tool_path,
        clock_path=clock_path,
        dsr_path=dsr_path,
    )
    read_request_receipt(request_receipt_path, authority_packet)
    request_rows = read_request_plan(request_plan_path, authority_packet, clock_path)
    trade_rows, _, upstream = _load_frozen_inputs(
        stage0_ledger_path,
        stage0_receipt_path,
        decision_packet_root,
        m1_root,
        request_rows,
        authority_packet,
        run_packet_sha256,
    )
    economic_result = _economic_result(trade_rows, dsr_path)
    daily_book = build_daily_book(trade_rows)
    evaluator_sha = sha256_bytes(read_stable_file(Path(__file__)))
    return persist_evaluation(output_root, trade_rows, daily_book, economic_result, upstream, evaluator_sha)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline TrendStack-002 DESIGN evaluator")
    parser.add_argument("--run-packet", type=Path, required=True)
    parser.add_argument("--stage0-ledger", type=Path, required=True)
    parser.add_argument("--stage0-receipt", type=Path, required=True)
    parser.add_argument("--decision-packet-root", type=Path, required=True)
    parser.add_argument("--request-plan", type=Path, required=True)
    parser.add_argument("--request-receipt", type=Path, required=True)
    parser.add_argument("--m1-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--dsr-tool", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = evaluate_design(
            run_packet_path=args.run_packet,
            stage0_ledger_path=args.stage0_ledger,
            stage0_receipt_path=args.stage0_receipt,
            decision_packet_root=args.decision_packet_root,
            request_plan_path=args.request_plan,
            request_receipt_path=args.request_receipt,
            m1_root=args.m1_root,
            output_root=args.output_root,
            dsr_path=args.dsr_tool,
        )
    except (InvalidEngineering, FileExistsError, ValueError) as exc:
        print(json.dumps({"verdict": "INVALID_ENGINEERING", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"verdict": receipt["verdict"], "evaluated_arm_rows": receipt["evaluated_arm_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
