from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - tests inject a bounded fake API.
    mt5 = None


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
SYMBOL = "EURUSD"
TIMEFRAME = "M1"
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
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
EXPECTED_REQUEST_COUNT = 1297
EXPECTED_TOTAL_ROWS = 466_920
EXPECTED_FIRST_DATE = "2016-01-04"
EXPECTED_LAST_DATE = "2020-12-31"
EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"
EXPECTED_DIGITS = 5
EXPECTED_POINT = 0.00001
REQUIRED_DATA_DRIVE = "D:"
WORKSPACE = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / SYMBOL / "trendstack_002_design_m1"
DEFAULT_DSR_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "dsr.py"
DEFAULT_STAGE0_ROOT = RESEARCH_ROOT / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0"
DEFAULT_PACKET_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / SYMBOL / "trendstack_002"
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
SHA256_RE = re.compile(r"[0-9A-F]{64}\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
REQUEST_SCHEMA = "trendstack_002_design_m1_request.v1"
MANIFEST_SCHEMA = "trendstack_002_design_m1_manifest_row.v1"
RECEIPT_SCHEMA = "trendstack_002_design_m1_source_receipt.v1"
RUN_PACKET_SCHEMA = "trendstack_002_design_run_packet.v1"
RUN_PACKET_FILENAME = "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
RUN_PACKET_VERDICT = "FROZEN_DESIGN_M1_PROXY_ONE_RUN_AUTHORIZED"
REQUEST_RECEIPT_SCHEMA = "trendstack_002_design_request_plan_receipt.v1"
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
RAW_COLUMNS = [
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
AUTHORITY_PATH_FIELDS = {
    "source_plan": "source_plan_sha256",
    "design_plan": "design_plan_sha256",
    "design_plan_v2": "design_plan_v2_sha256",
    "stage0_ledger": "stage0_eligibility_ledger_sha256",
    "stage0_receipt": "stage0_receipt_sha256",
    "stage0_access_trace": "stage0_access_trace_sha256",
    "stage0_reconciliation": "stage0_reconciliation_sha256",
    "decision_packet_manifest": "decision_packet_manifest_sha256",
    "decision_packet_receipt": "decision_packet_receipt_sha256",
    "request_plan_builder": "request_plan_builder_sha256",
    "evaluator": "evaluator_tool_sha256",
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
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise InvalidEngineering("INVALID_ENGINEERING DESIGN date-set member malformed") from exc
        _require(EXPECTED_FIRST_DATE <= value < "2021-01-01", "DESIGN date-set contains validation/holdout date")
        _require(prior is None or value > prior, "DESIGN date-set is duplicate/non-monotonic")
        prior = value
        encoded.append(value.encode("ascii") + b"\n")
    return DESIGN_DATE_SET_PREFIX + b"".join(encoded)


def _validate_frozen_design_date_set(dates: list[str], packet_sha256: str) -> None:
    payload = canonical_design_date_set_bytes(dates)
    observed = sha256_bytes(payload)
    _require(packet_sha256 == DESIGN_DATE_SET_SHA256, "run-packet DESIGN date-set hash mismatch")
    if EXPECTED_REQUEST_COUNT == 1297:
        _require(len(payload) == DESIGN_DATE_SET_CANONICAL_BYTES, "DESIGN date-set canonical byte count mismatch")
        _require(observed == DESIGN_DATE_SET_SHA256, "DESIGN date-set hash mismatch")


def _lstat_no_reparse(path: Path):
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING filesystem path cannot be inspected") from exc
    attributes = getattr(metadata, "st_file_attributes", 0)
    _require(not stat.S_ISLNK(metadata.st_mode), "symlink is forbidden")
    _require(not attributes & FILE_ATTRIBUTE_REPARSE_POINT, "reparse point is forbidden")
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


def default_authority_paths() -> dict[str, Path]:
    return {
        "source_plan": RESEARCH_ROOT / "HYP-TRENDSTACK-EURUSD-H1-002_SOURCE_PLAN.md",
        "design_plan": RESEARCH_ROOT / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN.md",
        "design_plan_v2": RESEARCH_ROOT / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_PLAN_V2.md",
        "stage0_ledger": DEFAULT_STAGE0_ROOT / "stage0_eligibility_ledger.jsonl",
        "stage0_receipt": DEFAULT_STAGE0_ROOT / "stage0_receipt.json",
        "stage0_access_trace": DEFAULT_STAGE0_ROOT / "stage0_access_trace.jsonl",
        "stage0_reconciliation": DEFAULT_STAGE0_ROOT / "stage0_reconciliation.json",
        "decision_packet_manifest": DEFAULT_PACKET_ROOT / "decision_packet_manifest.jsonl",
        "decision_packet_receipt": DEFAULT_PACKET_ROOT / "decision_packet_receipt.json",
        "request_plan_builder": RESEARCH_ROOT / "build_trendstack_002_design_request_plan.py",
        "evaluator": RESEARCH_ROOT / "evaluate_trendstack_002_design.py",
    }


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
        "clock_tool_sha256": CLOCK_SHA256,
        "dsr_tool_sha256": DSR_SHA256,
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
    _require(type(packet["request_count"]) is int and packet["request_count"] == EXPECTED_REQUEST_COUNT, "run-packet request count mismatch")
    _require(type(packet["expected_m1_rows"]) is int and packet["expected_m1_rows"] == EXPECTED_TOTAL_ROWS, "run-packet M1 row count mismatch")
    _require(packet["first_design_date"] == EXPECTED_FIRST_DATE, "run-packet first DESIGN date mismatch")
    _require(packet["last_design_date"] == EXPECTED_LAST_DATE, "run-packet last DESIGN date mismatch")
    expected_flags = {
        "design_m1_authorized": True,
        "validation_m1_authorized": False,
        "holdout_authorized": False,
        "model0_authorized": False,
        "promotion_authorized": False,
    }
    for field, expected in expected_flags.items():
        _require(type(packet[field]) is bool and packet[field] is expected, f"run-packet {field} mismatch")
    _require(type(packet["design_m1_output_root"]) is str and bool(packet["design_m1_output_root"]), "run-packet output root malformed")
    return packet, sha256_bytes(raw)


def _verify_authority_files(packet: dict, authority_paths: dict[str, Path], clock_path: Path, dsr_path: Path) -> None:
    _require(set(authority_paths) == set(AUTHORITY_PATH_FIELDS), "authority path set mismatch")
    for name, packet_field in AUTHORITY_PATH_FIELDS.items():
        observed = sha256_bytes(read_stable_file(Path(authority_paths[name])))
        _require(observed == packet[packet_field], f"authority file hash mismatch: {name}")
    _require(sha256_bytes(read_stable_file(Path(__file__))) == packet["acquisition_tool_sha256"], "acquisition self-hash mismatch")
    _require(sha256_bytes(read_stable_file(clock_path)) == packet["clock_tool_sha256"], "clock tool hash mismatch")
    _require(sha256_bytes(read_stable_file(dsr_path)) == packet["dsr_tool_sha256"], "DSR tool hash mismatch")


def read_request_receipt(path: Path, packet: dict) -> dict:
    raw = read_stable_file(path)
    _require(sha256_bytes(raw) == packet["request_plan_receipt_sha256"], "request receipt hash mismatch")
    receipt = _parse_json(raw, "request-plan receipt")
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
        "clock_tool_sha256": CLOCK_SHA256,
        "request_count": EXPECTED_REQUEST_COUNT,
        "expected_m1_rows": EXPECTED_TOTAL_ROWS,
        "first_design_date": EXPECTED_FIRST_DATE,
        "last_design_date": EXPECTED_LAST_DATE,
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


def _load_clock(clock_path: Path):
    raw = read_stable_file(clock_path)
    _require(sha256_bytes(raw) == CLOCK_SHA256, "clock-tool hash mismatch")
    spec = importlib.util.spec_from_file_location("trendstack_002_design_m1_clock", clock_path)
    _require(spec is not None and spec.loader is not None, "clock tool cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_utc(value: Any, label: str) -> datetime:
    _require(type(value) is str and value.endswith("Z"), f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING invalid {label}") from exc
    _require(parsed.tzinfo is not None, f"timezone missing: {label}")
    return parsed.astimezone(timezone.utc)


def _parse_server_encoded(value: Any, label: str) -> datetime:
    _require(type(value) is str, f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidEngineering(f"INVALID_ENGINEERING invalid {label}") from exc
    _require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, f"server boundary encoding mismatch: {label}")
    return parsed.astimezone(timezone.utc)


def read_request_plan(path: Path, expected_sha256: str, clock_path: Path, expected_date_set_sha256: str = DESIGN_DATE_SET_SHA256) -> list[dict]:
    _require(SHA256_RE.fullmatch(expected_sha256 or "") is not None, "request-plan expected hash malformed")
    raw = read_stable_file(path)
    _require(sha256_bytes(raw) == expected_sha256, "request-plan hash mismatch")
    clock = _load_clock(clock_path)
    rows = _parse_jsonl(raw, "design request plan")
    _require(len(rows) == EXPECTED_REQUEST_COUNT, "request-plan count mismatch")
    prior_date = None
    ids = []
    total_rows = 0
    for sequence, row in enumerate(rows, start=1):
        _require(set(row) == REQUEST_FIELDS, "request-plan schema mismatch")
        _require(row["schema_version"] == REQUEST_SCHEMA, "request-plan schema version mismatch")
        _require(row["hypothesis_id"] == HYPOTHESIS_ID and row["split"] == "DESIGN", "request-plan identity mismatch")
        _require(type(row["sequence"]) is int and row["sequence"] == sequence, "request-plan sequence mismatch")
        day = row["opportunity_id"]
        _require(type(day) is str and DATE_RE.fullmatch(day) is not None, "request-plan date malformed")
        _require("2016-01-04" <= day < "2021-01-01", "validation/holdout M1 request is forbidden")
        _require(prior_date is None or day > prior_date, "request-plan dates duplicate/non-monotonic")
        prior_date = day
        _require(row["request_id"] == f"M1-DESIGN-{sequence:04d}-{day.replace('-', '')}", "request-plan ID mismatch")
        start = _parse_utc(row["canonical_from_utc"], "request start")
        end = _parse_utc(row["canonical_to_inclusive_utc"], "request end")
        _require(start.strftime("%Y-%m-%d") == day and (start.hour, start.minute, start.second) == (12, 1, 0), "request start mismatch")
        _require(end.strftime("%Y-%m-%d") == day and (end.hour, end.minute, end.second) == (18, 0, 0), "request end mismatch")
        _require(int((end - start).total_seconds() // 60) + 1 == 360, "request window row count mismatch")
        encoded_from = _parse_server_encoded(row["api_server_wall_from_encoded_as_utc"], "server request start")
        encoded_to = _parse_server_encoded(row["api_server_wall_to_encoded_as_utc"], "server request end")
        from_roundtrip = clock.server_to_utc(encoded_from.replace(tzinfo=None))
        to_roundtrip = clock.server_to_utc(encoded_to.replace(tzinfo=None))
        _require(from_roundtrip == start.replace(tzinfo=None), "request start clock drift")
        _require(to_roundtrip == end.replace(tzinfo=None), "request end clock drift")
        _require(row["from_clock_roundtrip_status"] == row["to_clock_roundtrip_status"] == "PASS", "request clock status mismatch")
        _require(type(row["expected_rows"]) is int and row["expected_rows"] == 360, "request expected rows mismatch")
        _require(row["source_plan_sha256"] == SOURCE_PLAN_SHA256, "request SOURCE_PLAN mismatch")
        _require(row["design_plan_sha256"] == DESIGN_PLAN_SHA256, "request DESIGN_PLAN mismatch")
        ids.append(row["request_id"])
        total_rows += row["expected_rows"]
    _require(len(set(ids)) == len(ids), "duplicate request ID")
    _require(rows[0]["opportunity_id"] == EXPECTED_FIRST_DATE, "request first date mismatch")
    _require(rows[-1]["opportunity_id"] == EXPECTED_LAST_DATE, "request last date mismatch")
    _require(total_rows == EXPECTED_TOTAL_ROWS, "request total expected rows mismatch")
    _validate_frozen_design_date_set([row["opportunity_id"] for row in rows], expected_date_set_sha256)
    return rows


def validate_runtime_guards(mt5_api: Any, terminal: Any, account: Any, symbol: Any) -> dict:
    _require(terminal is not None and account is not None and symbol is not None, "terminal metadata unavailable")
    trade_allowed = getattr(terminal, "trade_allowed", None)
    connected = getattr(terminal, "connected", None)
    build = getattr(terminal, "build", None)
    trade_mode = getattr(account, "trade_mode", None)
    demo_constant = getattr(mt5_api, "ACCOUNT_TRADE_MODE_DEMO", None)
    server = getattr(account, "server", None)
    company = getattr(account, "company", None)
    digits = getattr(symbol, "digits", None)
    point = getattr(symbol, "point", None)
    selected = getattr(symbol, "select", None)
    visible = getattr(symbol, "visible", None)
    _require(type(trade_allowed) is bool and trade_allowed is False, "terminal-side trading flag is not exact false")
    _require(type(connected) is bool and connected is True, "terminal connected flag is not exact true")
    _require(type(build) is int and not isinstance(build, bool), "terminal build is malformed")
    _require(type(trade_mode) is int and not isinstance(trade_mode, bool) and trade_mode == 0, "account is not exact DEMO mode 0")
    _require(type(demo_constant) is int and not isinstance(demo_constant, bool) and demo_constant == 0, "MT5 DEMO constant mismatch")
    _require(type(server) is str and server == EXPECTED_SERVER, "broker server identity mismatch")
    _require(type(company) is str and company == EXPECTED_COMPANY, "broker company identity mismatch")
    _require(type(digits) is int and not isinstance(digits, bool) and digits == EXPECTED_DIGITS, "EURUSD digits mismatch")
    _require(type(point) in (int, float) and not isinstance(point, bool), "EURUSD point type mismatch")
    _require(math.isfinite(float(point)) and float(point) == EXPECTED_POINT, "EURUSD point mismatch")
    _require(type(selected) is bool and selected is True, "EURUSD selected flag mismatch")
    _require(type(visible) is bool and visible is True, "EURUSD visible flag mismatch")
    return {
        "terminal_build": build,
        "terminal_trade_allowed": False,
        "terminal_connected": True,
        "account_mode": "DEMO",
        "server": server,
        "company": company,
        "symbol": SYMBOL,
        "symbol_digits": digits,
        "symbol_point": float(point),
        "symbol_selected": True,
        "symbol_visible": True,
    }


def normalize_m1_rates(rates: Any, request: dict, clock_module) -> pd.DataFrame:
    _require(rates is not None and len(rates) == 360, "M1 response row count mismatch")
    frame = pd.DataFrame(rates)
    required = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    _require(required <= set(frame.columns), "M1 response fields missing")
    frame["time_server"] = pd.to_datetime(frame["time"], unit="s")
    frame["time_utc"] = frame["time_server"].map(lambda value: clock_module.server_to_utc(value.to_pydatetime().replace(tzinfo=None)))
    expected_start = _parse_utc(request["canonical_from_utc"], "request start").replace(tzinfo=None)
    expected_grid = [expected_start + pd.Timedelta(minutes=index) for index in range(360)]
    observed_grid = [pd.Timestamp(value).to_pydatetime() for value in frame["time_utc"]]
    _require(observed_grid == expected_grid, "M1 response grid is missing/duplicate/out-of-window")
    numeric = frame[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    _require(bool(np.isfinite(values).all()) and bool((values > 0).all()), "M1 OHLC is nonfinite/nonpositive")
    geometry = (
        (numeric["high"] >= numeric[["open", "close"]].max(axis=1))
        & (numeric["low"] <= numeric[["open", "close"]].min(axis=1))
        & (numeric["high"] >= numeric["low"])
    )
    _require(bool(geometry.all()), "M1 OHLC geometry invalid")
    offsets = []
    for server, utc in zip(frame["time_server"], frame["time_utc"]):
        delta = server.to_pydatetime().replace(tzinfo=None) - pd.Timestamp(utc).to_pydatetime().replace(tzinfo=None)
        _require(delta.total_seconds() in (7200, 10800), "M1 server/UTC offset invalid")
        offsets.append(int(delta.total_seconds() // 3600))
    result = pd.DataFrame(
        {
            "request_id": request["request_id"],
            "opportunity_id": request["opportunity_id"],
            "time_server": frame["time_server"].dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "time_utc": pd.to_datetime(frame["time_utc"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "utc_offset_h": np.asarray(offsets, dtype=np.int8),
            "bid_open": numeric["open"].astype(float),
            "bid_high": numeric["high"].astype(float),
            "bid_low": numeric["low"].astype(float),
            "bid_close": numeric["close"].astype(float),
            "tick_volume": pd.to_numeric(frame["tick_volume"], errors="raise").astype("int64"),
            "spread_points": pd.to_numeric(frame["spread"], errors="raise").astype("int32"),
            "real_volume": pd.to_numeric(frame["real_volume"], errors="raise").astype("int64"),
        }
    )
    _require(list(result.columns) == RAW_COLUMNS, "normalized M1 schema mismatch")
    return result


def _canonical_row_content_sha256(frame: pd.DataFrame) -> str:
    payload = b""
    for record in frame.to_dict(orient="records"):
        normalized = {
            key: int(value) if key in {"utc_offset_h", "tick_volume", "spread_points", "real_volume"}
            else float(value) if key.startswith("bid_")
            else str(value)
            for key, value in record.items()
        }
        payload += canonical_json_bytes(normalized) + b"\n"
    return sha256_bytes(payload)


def _write_parquet_new(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not path.exists(), "M1 shard target already exists")
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd", row_group_size=len(frame))
    parquet = pq.ParquetFile(path)
    _require(parquet.metadata.num_row_groups == 1 and parquet.metadata.num_rows == 360, "M1 parquet geometry mismatch")


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise InvalidEngineering("INVALID_ENGINEERING create-new artifact failed") from exc


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


def _validate_output_root(output_root: Path, input_paths: tuple[Path, ...] = ()) -> Path:
    root = Path(os.path.abspath(os.fspath(output_root)))
    if REQUIRED_DATA_DRIVE is not None:
        _require(root.drive.upper() == REQUIRED_DATA_DRIVE.upper(), "DESIGN M1 data root must be on D drive")
        _require(root == DEFAULT_DATA_ROOT.resolve(strict=False), "DESIGN M1 output root is not canonical")
    for input_path in input_paths:
        checked = _validate_component_chain(Path(input_path))
        _require(not _paths_overlap(root, checked), "DESIGN M1 output overlaps an authority input")
    if os.path.lexists(root):
        _validate_component_chain(root)
        allowed_existing = {"design_request_plan.jsonl", "design_request_plan_receipt.json", "quarantine"}
        illegal = [child.name for child in root.iterdir() if child.name not in allowed_existing]
        _require(not illegal, f"active DESIGN M1 artifacts already exist: {sorted(illegal)}")
    else:
        parent = _validate_component_chain(root.parent)
        _require(parent.is_dir(), "output parent is not a directory")
        root.mkdir(exist_ok=False)
    return root


def _create_attempt(root: Path) -> Path:
    attempts = root / "_attempts"
    attempts.mkdir(exist_ok=True)
    attempt = attempts / secrets.token_hex(16)
    attempt.mkdir(exist_ok=False)
    return attempt


def _quarantine(root: Path, attempt: Path, reason: BaseException, run_packet_sha256: str) -> Path:
    if attempt.exists():
        failure = {
            "schema_version": "trendstack_002_design_m1_failure.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "verdict": "INVALID_ENGINEERING",
            "failure_type": type(reason).__name__,
            "run_packet_sha256": run_packet_sha256,
        }
        failure_path = attempt / "failure_manifest.json"
        if not failure_path.exists():
            _write_new(failure_path, canonical_json_bytes(failure) + b"\n")
    quarantine = root / "quarantine"
    quarantine.mkdir(exist_ok=True)
    destination = quarantine / attempt.name
    os.rename(attempt, destination)
    attempts = root / "_attempts"
    if attempts.exists() and not any(attempts.iterdir()):
        attempts.rmdir()
    return destination


def _publish(root: Path, attempt: Path) -> None:
    expected = {"raw_m1", "design_m1_manifest.jsonl", "design_m1_source_receipt.json"}
    _require({child.name for child in attempt.iterdir()} == expected, "attempt artifact set mismatch")
    moved = []
    try:
        for name in sorted(expected):
            target = root / name
            _require(not target.exists(), "publish target already exists")
            os.rename(attempt / name, target)
            moved.append(target)
        attempt.rmdir()
        attempts = root / "_attempts"
        if not any(attempts.iterdir()):
            attempts.rmdir()
    except BaseException as exc:
        rollback = root / "quarantine" / attempt.name
        rollback.mkdir(parents=True, exist_ok=False)
        for target in moved:
            os.rename(target, rollback / target.name)
        if attempt.exists():
            os.rename(attempt, rollback / "attempt_remaining")
        raise InvalidEngineering("INVALID_ENGINEERING acquisition publish failed") from exc


def _runtime_provenance(terminal_path: Path, guard: dict, mt5_api: Any, clock_path: Path, run_packet_sha256: str) -> dict:
    native = Path(mt5_api._core.__file__)
    python = Path(sys.executable)
    return {
        "terminal_executable_label": terminal_path.name,
        "terminal_executable_sha256": sha256_bytes(read_stable_file(terminal_path)),
        "python_executable_label": python.name,
        "python_executable_sha256": sha256_bytes(read_stable_file(python)),
        "metatrader5_version": str(mt5_api.__version__),
        "metatrader5_native_module_label": native.name,
        "metatrader5_native_module_sha256": sha256_bytes(read_stable_file(native)),
        "clock_tool_label": clock_path.name,
        "clock_tool_sha256": sha256_bytes(read_stable_file(clock_path)),
        "acquisition_tool_label": Path(__file__).name,
        "acquisition_tool_sha256": sha256_bytes(read_stable_file(Path(__file__))),
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "design_plan_sha256": DESIGN_PLAN_SHA256,
        "run_packet_sha256": run_packet_sha256,
        "pandas_version": pd.__version__,
        "pyarrow_version": pa.__version__,
        "account_guard": guard,
    }


def _safe_shard_path(root: Path, day: str) -> tuple[str, Path]:
    relative = PurePosixPath("raw_m1") / "DESIGN" / day / "1201_1800.parquet"
    _require(all(part not in {"", ".", ".."} for part in relative.parts), "unsafe M1 shard path")
    return relative.as_posix(), root / Path(*relative.parts)


def _reopen_validate_attempt(attempt: Path, manifest: list[dict]) -> None:
    observed = sorted(
        path.relative_to(attempt).as_posix()
        for path in (attempt / "raw_m1").rglob("*.parquet")
    )
    expected = sorted(row["shard_path"] for row in manifest)
    _require(observed == expected, "physical M1 shard set mismatch")
    for row in manifest:
        path = attempt / Path(*PurePosixPath(row["shard_path"]).parts)
        raw = read_stable_file(path)
        _require(sha256_bytes(raw) == row["shard_sha256"], "M1 shard hash mismatch")
        parquet = pq.ParquetFile(path)
        _require(parquet.metadata.num_row_groups == 1 and parquet.metadata.num_rows == 360, "M1 shard row-group mismatch")


def acquire_design_m1(
    request_plan_path: Path,
    request_receipt_path: Path,
    run_packet_path: Path,
    *,
    terminal_path: Path,
    output_root: Path,
    mt5_api: Any = mt5,
    clock_path: Path,
    dsr_path: Path = DEFAULT_DSR_PATH,
    authority_paths: dict[str, Path] | None = None,
) -> dict:
    packet, run_packet_sha256 = read_run_packet(run_packet_path)
    canonical_root = Path(_canonical_path_text(output_root))
    _require(Path(_canonical_path_text(request_plan_path)) == canonical_root / "design_request_plan.jsonl", "request plan is outside canonical DESIGN M1 root")
    _require(Path(_canonical_path_text(request_receipt_path)) == canonical_root / "design_request_plan_receipt.json", "request receipt is outside canonical DESIGN M1 root")
    paths = default_authority_paths() if authority_paths is None else {key: Path(value) for key, value in authority_paths.items()}
    if REQUIRED_DATA_DRIVE is not None:
        canonical_paths = default_authority_paths()
        _require(set(paths) == set(canonical_paths), "authority path set mismatch")
        for name, canonical_path in canonical_paths.items():
            _require(Path(_canonical_path_text(paths[name])) == Path(_canonical_path_text(canonical_path)), f"authority path is not canonical: {name}")
    _verify_authority_files(packet, paths, clock_path, dsr_path)
    read_request_receipt(request_receipt_path, packet)
    rows = read_request_plan(request_plan_path, packet["request_plan_sha256"], clock_path, packet["design_date_set_sha256"])
    terminal_path = Path(terminal_path)
    _require(mt5_api is not None, "MT5 API is unavailable")
    read_stable_file(terminal_path)
    _require(packet["design_m1_output_root"] == _canonical_path_text(output_root), "run-packet DESIGN M1 output root mismatch")
    input_paths = tuple(paths.values()) + (
        Path(run_packet_path),
        Path(clock_path),
        Path(dsr_path),
        terminal_path,
        Path(__file__),
    )
    root = _validate_output_root(output_root, input_paths)
    attempt = _create_attempt(root)
    receipt = None
    failure: BaseException | None = None
    try:
        try:
            initialized = bool(mt5_api.initialize(path=str(terminal_path), portable=True, timeout=60_000))
            _require(initialized, f"MT5 initialize failed: {mt5_api.last_error()}")
            guard = validate_runtime_guards(
                mt5_api,
                mt5_api.terminal_info(),
                mt5_api.account_info(),
                mt5_api.symbol_info(SYMBOL),
            )
            runtime = _runtime_provenance(terminal_path, guard, mt5_api, clock_path, run_packet_sha256)
            runtime_hashes = {key: value for key, value in runtime.items() if key.endswith("sha256")}
            clock = _load_clock(clock_path)
            manifest = []
            for request in rows:
                api_from = _parse_server_encoded(request["api_server_wall_from_encoded_as_utc"], "server request start")
                api_to = _parse_server_encoded(request["api_server_wall_to_encoded_as_utc"], "server request end")
                rates = mt5_api.copy_rates_range(SYMBOL, mt5_api.TIMEFRAME_M1, api_from, api_to)
                frame = normalize_m1_rates(rates, request, clock)
                relative, shard_path = _safe_shard_path(attempt, request["opportunity_id"])
                _write_parquet_new(shard_path, frame)
                shard_raw = read_stable_file(shard_path)
                manifest.append(
                    {
                        "schema_version": MANIFEST_SCHEMA,
                        "hypothesis_id": HYPOTHESIS_ID,
                        "request_id": request["request_id"],
                        "opportunity_id": request["opportunity_id"],
                        "split": "DESIGN",
                        "shard_path": relative,
                        "rows": 360,
                        "row_groups": 1,
                        "first_utc_time": frame["time_utc"].iloc[0],
                        "last_utc_time": frame["time_utc"].iloc[-1],
                        "canonical_row_content_sha256": _canonical_row_content_sha256(frame),
                        "shard_sha256": sha256_bytes(shard_raw),
                        "shard_bytes": len(shard_raw),
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
                )
            _require(len(manifest) == EXPECTED_REQUEST_COUNT, "M1 manifest request count mismatch")
            manifest_payload = b"".join(canonical_json_bytes(row) + b"\n" for row in manifest)
            _write_new(attempt / "design_m1_manifest.jsonl", manifest_payload)
            _reopen_validate_attempt(attempt, manifest)
            receipt = {
                "schema_version": RECEIPT_SCHEMA,
                "hypothesis_id": HYPOTHESIS_ID,
                "source_plan_sha256": SOURCE_PLAN_SHA256,
                "design_plan_sha256": DESIGN_PLAN_SHA256,
                "request_plan_sha256": packet["request_plan_sha256"],
                "request_plan_receipt_sha256": packet["request_plan_receipt_sha256"],
                "run_packet_sha256": run_packet_sha256,
                "design_m1_manifest_sha256": sha256_bytes(manifest_payload),
                "request_count": len(manifest),
                "shard_file_count": len(manifest),
                "m1_rows": sum(row["rows"] for row in manifest),
                "first_design_date": manifest[0]["opportunity_id"],
                "last_design_date": manifest[-1]["opportunity_id"],
                "runtime_provenance": runtime,
                "all_shard_hashes_verified": True,
                "design_m1_opened": True,
                "validation_m1_opened": False,
                "holdout_opened": False,
                "economics_computed": False,
                "physical_partition_status": "PASS",
                "verdict": "DESIGN_M1_SOURCE_READY_FOR_OFFLINE_EVALUATION",
            }
            _write_new(attempt / "design_m1_source_receipt.json", canonical_json_bytes(receipt) + b"\n")
        except BaseException as exc:
            failure = exc
    finally:
        try:
            mt5_api.shutdown()
        except BaseException as exc:
            failure = InvalidEngineering("INVALID_ENGINEERING MT5 shutdown failed")
    if failure is not None:
        _quarantine(root, attempt, failure, run_packet_sha256)
        if isinstance(failure, InvalidEngineering):
            raise failure
        raise InvalidEngineering(f"INVALID_ENGINEERING acquisition failed: {type(failure).__name__}") from failure
    _require(receipt is not None, "acquisition receipt missing")
    _publish(root, attempt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acquire frozen TrendStack-002 DESIGN M1 source")
    parser.add_argument("--request-plan", type=Path, required=True)
    parser.add_argument("--request-receipt", type=Path, required=True)
    parser.add_argument("--run-packet", type=Path, required=True)
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--clock-tool", type=Path, required=True)
    parser.add_argument("--dsr-tool", type=Path, default=DEFAULT_DSR_PATH)
    args = parser.parse_args(argv)
    try:
        receipt = acquire_design_m1(
            args.request_plan,
            args.request_receipt,
            args.run_packet,
            terminal_path=args.terminal,
            output_root=args.output_root,
            clock_path=args.clock_tool,
            dsr_path=args.dsr_tool,
        )
    except (InvalidEngineering, FileExistsError) as exc:
        print(json.dumps({"verdict": "INVALID_ENGINEERING", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"verdict": receipt["verdict"], "request_count": receipt["request_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
