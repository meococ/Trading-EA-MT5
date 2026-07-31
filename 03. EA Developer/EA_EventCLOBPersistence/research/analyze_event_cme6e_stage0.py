#!/usr/bin/env python3
"""Outcome-blind Stage 0B-D analysis for frozen CME 6E design segments.

This module decodes only local, manifest-bound DBNStore files. It has no remote
API surface and must not be used to open price outcomes or validation source.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


class Stage0Error(RuntimeError):
    """Fail-closed Stage 0 contract violation."""


SOURCE_INVOCATION_PATH = Path(__file__)
SOURCE_PATH = SOURCE_INVOCATION_PATH.resolve()
WORKSPACE = SOURCE_PATH.parents[3]
PACKAGE_ROOT = SOURCE_PATH.parent.parent
RESEARCH_ROOT = SOURCE_PATH.parent
TEST_PATH = PACKAGE_ROOT / "tests" / "test_event_cme6e_stage0.py"

TASK_PACKET_PATH = (
    RESEARCH_ROOT
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_SOURCE_TASK_PACKET.json"
)
TASK_PACKET_SHA256 = "5B4B636AB925E6579F4B5084339EC6E5E613266F3384C4CDA34B0D4D73FDA588"
V2_TASK_PACKET_PATH = (
    RESEARCH_ROOT
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_SOURCE_TASK_PACKET_V2.json"
)
V2_TASK_PACKET_SHA256 = "6658ED3EFF6323F29DC99E8B2A8BF2A38A776FBA3AC63D0692CDC1F077870CDD"
V3_TASK_PACKET_PATH = (
    RESEARCH_ROOT
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_SOURCE_TASK_PACKET_V3.json"
)
V3_TASK_PACKET_SHA256 = "7F42B75E19A5AB2AA3FDE714F815671EBC063A54098C941F69A3533CC8C2ED37"
RUN_AUTHORITY_PATH = (
    RESEARCH_ROOT
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_RUN_AUTHORITY.json"
)
REQUIRED_PYTHON_RELATIVE_PATH = (
    "02. AlphaFactory/runtime/python-databento/Scripts/python.exe"
)
REQUIRED_PYTHON_PATH = WORKSPACE / Path(REQUIRED_PYTHON_RELATIVE_PATH)
REQUIRED_PYTHON_SHA256 = "0B471133E110CFB53A061CAD528CE8E517D7B9AC41A0A396C39AD795A487FC14"
REQUIRED_DATABENTO_VERSION = "0.54.0"
V14_PACKET_PATH = (
    RESEARCH_ROOT
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_TASK_PACKET_V14.json"
)
V14_PACKET_SHA256 = "E752003D652DD1B204DAE2EEC84F0149DF89C70BC4C42C80C089D6CD923F730D"
PREREG_PATH = (
    RESEARCH_ROOT / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_PROBE_PLAN.md"
)
PREREG_SHA256 = "62A3AB66C64083D9967D91A0D634DEF29641AE7F3A05D3C59CBC153AAF4B3CBF"
CLOCK_PATH = RESEARCH_ROOT / "source" / "point_release_clocks_2019_2022.csv"
CLOCK_SHA256 = "5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B"
CLOCK_MANIFEST_PATH = RESEARCH_ROOT / "source" / "point_release_clock_manifest.json"
CLOCK_MANIFEST_SHA256 = "B61CDFA6DCAE82308E4CD2A60DAFF195C297FD8523D41CDCA0788694657AC636"

CANONICAL_DATA_ROOT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_event_clob_design_segments"
)
RAW_ROOT = CANONICAL_DATA_ROOT / "raw"
DOWNLOAD_MANIFEST_PATH = CANONICAL_DATA_ROOT / "download_manifest.json"
DOWNLOAD_MANIFEST_SHA256 = "9438133803AF33E52C641DF149D04AA8E1CA8B1DD5A510795E0B55C3D2698229"
AUTHORITY_RECEIPT_PATH = CANONICAL_DATA_ROOT / "acquisition_authority_receipt.json"
AUTHORITY_RECEIPT_SHA256 = "15D2878DA8F461219E29DBBDD34B42F8B74116DB6B7A1EA9F5AF060748A4FA13"
LIVE_REQUOTE_PLAN_PATH = CANONICAL_DATA_ROOT / "live_requote_plan.json"
LIVE_REQUOTE_PLAN_SHA256 = "EA180B16DBD258EE807B06E1F92BDB7FCF6A98DB6B41C9877918C30CF791EC5F"
LIVE_REQUOTE_RECEIPT_PATH = CANONICAL_DATA_ROOT / "live_requote_receipt.json"
LIVE_REQUOTE_RECEIPT_SHA256 = "01D94E6467724EF1D25362C09F56EBFB10635DC0DE24833F1B384260570D3168"

REGISTRY_PATH = WORKSPACE / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR_PATH = (
    WORKSPACE / "04. Memory" / "research" / "validate_candidate_registry.py"
)
V14_PREFIX_ROWS = 272
V14_PREFIX_SHA256 = "C0C3BFA3328CBD83DC5335E06F774A3C3800A6418C4363A8A27F140F2DCC4739"
HYPOTHESIS_ID = "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002"
HYPOTHESIS_ROW_SHA256_SEQUENCE = (
    "B352E22DE06889E3FDF139A7857CEAECB123944E42CDF1564C9CE3B54AF01F3D",
    "8B88B70C26060FF8A2A13F506990ADE3C6A27C2860C5618E51FBD77115B109CF",
    "AAE0F493502C13EB8C75C9105C83C6B6F325043D59BBB120075063401C907C45",
)

LEDGER_PATH = CANONICAL_DATA_ROOT / "stage0_event_feature_ledger.csv"
OUTPUT_MANIFEST_PATH = CANONICAL_DATA_ROOT / "stage0_source_quality_manifest.json"
READOUT_PATH = (
    RESEARCH_ROOT
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_STAGE0_SOURCE_READOUT.md"
)

DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
EXPECTED_REQUESTS = 658
EXPECTED_EVENTS = 329
DESIGN_YEARS = {2019, 2020}
ELAPSED_DESIGN_WEEKS = 104.428571
MIN_FEATURE_EVENTS = 209
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_NONEMPTY_COVERAGE = 0.99
ONE_SECOND_NS = 1_000_000_000
PRICE_SCALE = 1_000_000_000
TICK_SIZE = 0.00005
TICK_RAW = int(TICK_SIZE * PRICE_SCALE)
MIN_RECORDS = 30
MAX_SPREAD_TICKS = 2.0
FAILURE_VERDICT = "PARK_STAGE0B_DESIGN_SOURCE_OR_CADENCE"
PASS_VERDICT = "PASS_STAGE0B_DESIGN_SOURCE_AND_CADENCE"

SEGMENT_OFFSETS = {
    "PRE": (-60, -15),
    "LATE": (45, 60),
}

LEDGER_FIELDS = [
    "event_clock_id",
    "event_time_utc",
    "pre_request_id",
    "late_request_id",
    "pre_start_utc",
    "pre_end_utc",
    "late_start_utc",
    "late_end_utc",
    "pre_filename",
    "late_filename",
    "pre_source_empty",
    "late_source_empty",
    "pre_record_count",
    "late_record_count",
    "pre_sha256",
    "late_sha256",
    "pre_segment_quality",
    "late_segment_quality",
    "pre_quality_reason_codes",
    "late_quality_reason_codes",
    "pair_quality_pass",
    "pair_quality_reason_codes",
    "i5_pre",
    "i5_late",
    "delta_i5",
    "late_median_spread_ticks",
    "feature_eligible",
    "direction",
]

PROHIBITED_READ_COUNTERS = {
    "databento_client_constructions": 0,
    "eurusd_price_reads": 0,
    "middle_window_reads": 0,
    "network_calls": 0,
    "outcome_field_reads": 0,
    "paid_calls": 0,
    "validation_source_reads": 0,
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _lexical_key(path: Path) -> str:
    return os.path.normcase(os.fspath(Path(path)))


def _is_reparse_component(path: Path) -> bool:
    try:
        stat = path.lstat()
    except OSError as exc:
        raise Stage0Error(f"cannot stat path component: {path}") from exc
    anchor = Path(path.anchor) if path.anchor else None
    is_nonroot_mount = bool(anchor is not None and path != anchor and path.is_mount())
    return (
        path.is_symlink()
        or is_nonroot_mount
        or bool(getattr(stat, "st_file_attributes", 0) & 0x400)
        or bool(getattr(stat, "st_reparse_tag", 0))
    )


def validate_secure_path(
    path: Path,
    *,
    expected: Path,
    containment_root: Path,
    must_exist: bool,
) -> Path:
    """Validate lexical identity, containment and every existing path component."""
    actual = Path(path)
    canonical = Path(expected)
    root = Path(containment_root)
    if not actual.is_absolute() or not canonical.is_absolute() or not root.is_absolute():
        raise Stage0Error(f"path must be absolute: {actual}")
    if _lexical_key(actual) != _lexical_key(canonical):
        raise Stage0Error(
            f"path must use its lexical exact path: expected {canonical}, got {actual}"
        )
    try:
        common = os.path.commonpath([os.fspath(canonical), os.fspath(root)])
    except ValueError as exc:
        raise Stage0Error(f"path escapes containment root: {canonical}") from exc
    if os.path.normcase(common) != os.path.normcase(os.fspath(root)):
        raise Stage0Error(f"path escapes containment root: {canonical}")
    try:
        resolved = canonical.resolve(strict=must_exist)
        resolved_root = root.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise Stage0Error(f"resolved path escapes containment root: {canonical}") from exc
    if root.drive.upper() == "D:" and canonical.drive.upper() != "D:":
        raise Stage0Error(f"production path is not contained on D: {canonical}")

    current = Path(canonical.anchor)
    missing_seen = False
    for part in canonical.parts[1:]:
        current = current / part
        if current.exists() or current.is_symlink():
            if missing_seen:
                raise Stage0Error(f"path contains an inconsistent missing ancestor: {current}")
            if _is_reparse_component(current):
                raise Stage0Error(f"path contains a reparse component: {current}")
        else:
            missing_seen = True
    if must_exist and not canonical.exists():
        raise Stage0Error(f"required path is missing: {canonical}")
    if not must_exist and not canonical.exists() and not canonical.parent.is_dir():
        raise Stage0Error(f"output parent is missing: {canonical.parent}")
    return canonical


def _require_hash(path: Path, expected: str, label: str) -> str:
    validate_secure_path(
        path,
        expected=path,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    if not path.is_file():
        raise Stage0Error(f"missing frozen {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise Stage0Error(
            f"frozen {label} hash mismatch: expected {expected}, got {actual}"
        )
    return actual


def _load_json(path: Path) -> dict[str, Any]:
    validate_secure_path(
        path,
        expected=path,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Stage0Error(f"invalid JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise Stage0Error(f"JSON artifact root is not an object: {path}")
    return value


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise Stage0Error(f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise Stage0Error(f"timestamp is not UTC: {value}")
    return parsed.astimezone(timezone.utc)


def parse_utc_ns(value: str) -> int:
    parsed = parse_utc(value)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = parsed - epoch
    return (
        delta.days * 86_400 * ONE_SECOND_NS
        + delta.seconds * ONE_SECOND_NS
        + delta.microseconds * 1_000
    )


def datetime_ns(value: datetime) -> int:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise Stage0Error("DBN metadata timestamp is not UTC")
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = value.astimezone(timezone.utc) - epoch
    return (
        delta.days * 86_400 * ONE_SECOND_NS
        + delta.seconds * ONE_SECOND_NS
        + delta.microseconds * 1_000
    )


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def expected_request_contract(
    event_clock_id: str, event_time_utc: str, segment: str
) -> dict[str, Any]:
    if segment not in SEGMENT_OFFSETS:
        raise Stage0Error(f"unknown segment: {segment}")
    event_time = parse_utc(event_time_utc)
    start_offset, end_offset = SEGMENT_OFFSETS[segment]
    start = event_time + timedelta(seconds=start_offset)
    end = event_time + timedelta(seconds=end_offset)
    filename = (
        f"{event_clock_id}_{segment}_{start.strftime('%Y%m%dT%H%M%S')}_"
        f"{end.strftime('%Y%m%dT%H%M%S')}.dbn.zst"
    )
    return {
        "request_id": f"{event_clock_id}_{segment}",
        "event_clock_id": event_clock_id,
        "event_time_utc": format_utc(event_time),
        "segment": segment,
        "start": format_utc(start),
        "end": format_utc(end),
        "duration_seconds": int((end - start).total_seconds()),
        "filename": filename,
    }


def validate_request_contract(request: dict[str, Any]) -> None:
    try:
        event_id = str(request["event_clock_id"])
        event_time = str(request["event_time_utc"])
        segment = str(request["segment"])
    except KeyError as exc:
        raise Stage0Error(f"request lacks identity field: {exc}") from exc
    if parse_utc(event_time).year not in DESIGN_YEARS:
        raise Stage0Error(f"request is outside frozen design year: {event_id}")
    expected = expected_request_contract(event_id, event_time, segment)
    for field in (
        "request_id",
        "event_clock_id",
        "event_time_utc",
        "segment",
        "start",
        "end",
        "duration_seconds",
        "filename",
    ):
        if request.get(field) != expected[field]:
            label = "bounds" if field in {"start", "end", "duration_seconds"} else field
            raise Stage0Error(
                f"request {event_id}/{segment} {label} mismatch: "
                f"expected {expected[field]!r}, got {request.get(field)!r}"
            )


def validate_unique_requests(requests: Sequence[dict[str, Any]]) -> None:
    seen_requests: set[str] = set()
    seen_segments: set[tuple[str, str]] = set()
    for request in requests:
        request_id = str(request.get("request_id", ""))
        identity = (
            str(request.get("event_clock_id", "")),
            str(request.get("segment", "")),
        )
        if request_id in seen_requests or identity in seen_segments:
            raise Stage0Error(f"duplicate request identity: {request_id or identity}")
        seen_requests.add(request_id)
        seen_segments.add(identity)


def _is_reparse(path: Path) -> bool:
    return _is_reparse_component(path)


def _file_identity(stat: os.stat_result) -> tuple[int, int]:
    return (int(stat.st_dev), int(stat.st_ino))


@contextmanager
def _open_binary_no_reparse(path: Path):
    """Open one read handle while refusing to traverse a final-component reparse point."""
    if os.name == "nt":
        import ctypes
        import msvcrt
        from ctypes import wintypes

        create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
        create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            os.fspath(path),
            0x80000000,  # GENERIC_READ
            0x00000001 | 0x00000002 | 0x00000004,  # share read/write/delete
            None,
            3,  # OPEN_EXISTING
            0x00200000 | 0x08000000,  # OPEN_REPARSE_POINT | SEQUENTIAL_SCAN
            None,
        )
        invalid_handle = wintypes.HANDLE(-1).value
        if handle == invalid_handle:
            error = ctypes.get_last_error()
            raise OSError(error, f"CreateFileW failed for {path}")
        try:
            descriptor = msvcrt.open_osfhandle(
                int(handle), os.O_RDONLY | os.O_BINARY
            )
        except Exception:
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(handle)
            raise
    else:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb", closefd=True) as stream:
        yield stream


def _run_identity_read_hook(
    hook: Callable[[str, str, Path, Any], None] | None,
    phase: str,
    point: str,
    path: Path,
    handle: Any = None,
) -> None:
    if hook is not None:
        hook(phase, point, path, handle)


def _identity_bound_read(
    path: Path,
    *,
    containment_root: Path,
    phase: str,
    original_identity: Sequence[int] | None = None,
    expected_bytes: int | None = None,
    expected_sha256: str | None = None,
    expected_payload: bytes | None = None,
    _test_hook: Callable[[str, str, Path, Any], None] | None = None,
) -> dict[str, Any]:
    """Read once from one handle and bind path/handle identity on both sides."""
    validate_secure_path(
        path,
        expected=path,
        containment_root=containment_root,
        must_exist=True,
    )
    if not path.is_file():
        raise Stage0Error(f"identity-bound input is not a regular file: {path}")
    try:
        path_before = path.lstat()
        _run_identity_read_hook(
            _test_hook, phase, "after_path_before", path
        )
        with _open_binary_no_reparse(path) as handle:
            handle_before = os.fstat(handle.fileno())
            _run_identity_read_hook(
                _test_hook, phase, "after_handle_before", path, handle
            )
            payload = handle.read()
            _run_identity_read_hook(
                _test_hook, phase, "after_handle_read", path, handle
            )
            handle_after = os.fstat(handle.fileno())
            _run_identity_read_hook(
                _test_hook, phase, "after_handle_after", path, handle
            )
        _run_identity_read_hook(
            _test_hook, phase, "before_path_after", path
        )
        path_after = path.lstat()
    except OSError as exc:
        raise Stage0Error(f"identity-bound read failed ({phase}): {path}") from exc

    identity = _file_identity(path_before)
    identities = (
        identity,
        _file_identity(handle_before),
        _file_identity(handle_after),
        _file_identity(path_after),
    )
    if len(set(identities)) != 1 or (
        original_identity is not None
        and identity != tuple(int(item) for item in original_identity)
    ):
        raise Stage0Error(f"DBN identity changed {phase}: {path.name}")
    actual_hash = sha256_bytes(payload)
    if expected_bytes is not None and len(payload) != expected_bytes:
        raise Stage0Error(
            f"DBN changed after byte binding during {phase}: size mismatch: {path.name}"
        )
    if expected_sha256 is not None and actual_hash != expected_sha256.upper():
        raise Stage0Error(
            f"DBN changed after byte binding during {phase}: hash mismatch: {path.name}"
        )
    if expected_payload is not None and payload != expected_payload:
        raise Stage0Error(
            f"DBN changed after byte binding during {phase}: payload mismatch: {path.name}"
        )
    return {
        "payload": payload,
        "identity": identity,
        "bytes": len(payload),
        "sha256": actual_hash,
    }


def capture_verified_snapshot(
    path: Path,
    request: dict[str, Any],
    *,
    containment_root: Path,
    _test_hook: Callable[[str, str, Path, Any], None] | None = None,
) -> dict[str, Any]:
    expected_bytes = request.get("bytes")
    if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool):
        raise Stage0Error(f"manifest DBN size is invalid: {request.get('request_id')}")
    expected_hash = request.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise Stage0Error(f"manifest DBN hash is invalid: {request.get('request_id')}")
    verified = _identity_bound_read(
        path,
        containment_root=containment_root,
        phase="initial byte binding",
        expected_bytes=expected_bytes,
        expected_sha256=expected_hash,
        _test_hook=_test_hook,
    )
    return {
        "path": path,
        "containment_root": containment_root,
        **verified,
    }


def revalidate_verified_snapshot(
    snapshot: dict[str, Any],
    *,
    phase: str,
    _test_hook: Callable[[str, str, Path, Any], None] | None = None,
) -> None:
    path = Path(snapshot["path"])
    _identity_bound_read(
        path,
        containment_root=Path(snapshot["containment_root"]),
        phase=phase,
        original_identity=snapshot["identity"],
        expected_bytes=int(snapshot["bytes"]),
        expected_sha256=str(snapshot["sha256"]),
        expected_payload=bytes(snapshot["payload"]),
        _test_hook=_test_hook,
    )


def decode_verified_snapshot(
    path: Path,
    request: dict[str, Any],
    *,
    containment_root: Path,
    decoder: Callable[[bytes, dict[str, Any]], dict[str, Any]],
    _test_hook: Callable[[str, str, Path, Any], None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = capture_verified_snapshot(
        path,
        request,
        containment_root=containment_root,
    )
    revalidate_verified_snapshot(
        snapshot, phase="before decode", _test_hook=_test_hook
    )
    decoded = decoder(snapshot["payload"], request)
    revalidate_verified_snapshot(
        snapshot, phase="after decode", _test_hook=_test_hook
    )
    return decoded, snapshot


def verify_file_binding(path: Path, request: dict[str, Any]) -> dict[str, Any]:
    snapshot = capture_verified_snapshot(path, request, containment_root=path.parent)
    return {"bytes": snapshot["bytes"], "sha256": snapshot["sha256"]}


def verify_raw_file_set(raw_root: Path, requests: Sequence[dict[str, Any]]) -> None:
    validate_secure_path(
        raw_root,
        expected=raw_root,
        containment_root=raw_root,
        must_exist=True,
    )
    if not raw_root.is_dir():
        raise Stage0Error(f"raw root is missing or unsafe: {raw_root}")
    expected = {str(item.get("filename", "")) for item in requests}
    if "" in expected:
        raise Stage0Error("manifest contains an empty DBN filename")
    actual_entries = list(raw_root.iterdir())
    unsafe = [
        item.name
        for item in actual_entries
        if not item.is_file() or _is_reparse_component(item)
    ]
    if unsafe:
        raise Stage0Error(f"raw root contains unsafe entries: {sorted(unsafe)}")
    actual = {item.name for item in actual_entries}
    extras = sorted(actual - expected)
    missing = sorted(expected - actual)
    if extras:
        raise Stage0Error(f"unmanifested extra DBN file(s): {extras}")
    if missing:
        raise Stage0Error(f"manifest DBN file(s) missing: {missing}")


def verify_decoded_record_count(
    request: dict[str, Any], decoded: dict[str, Any]
) -> None:
    records_value = decoded.get("records")
    try:
        actual = len(records_value)
    except TypeError as exc:
        raise Stage0Error("decoded DBN records are not sized") from exc
    expected = request.get("records")
    if not isinstance(expected, int) or isinstance(expected, bool) or actual != expected:
        raise Stage0Error(
            f"DBN record-count mismatch for {request.get('request_id')}: "
            f"expected {expected}, got {actual}"
        )


def _record_value(record: Any, field: str) -> Any:
    try:
        value = record[field]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise Stage0Error(f"MBP-10 record lacks required field: {field}") from exc
    return value.item() if hasattr(value, "item") else value


def _append_once(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def analyze_segment(
    records_value: Iterable[Any],
    *,
    start_ns: int,
    end_ns: int,
    expected_instrument_id: int | None,
    metadata_reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    rows = list(records_value)
    reasons = list(dict.fromkeys(str(item) for item in metadata_reason_codes))
    timestamps: list[int] = []
    imbalances: list[float] = []
    spreads: list[float] = []
    if len(rows) < MIN_RECORDS:
        _append_once(reasons, "RECORD_COUNT_LT_30")
    if expected_instrument_id is None:
        _append_once(reasons, "INSTRUMENT_MAPPING_INVALID")

    for row in rows:
        try:
            timestamp = int(_record_value(row, "ts_event"))
            instrument_id = int(_record_value(row, "instrument_id"))
            bid_sizes = [float(_record_value(row, f"bid_sz_{level:02d}")) for level in range(5)]
            ask_sizes = [float(_record_value(row, f"ask_sz_{level:02d}")) for level in range(5)]
            bid_px = float(_record_value(row, "bid_px_00"))
            ask_px = float(_record_value(row, "ask_px_00"))
        except (Stage0Error, TypeError, ValueError, OverflowError):
            _append_once(reasons, "MBP10_REQUIRED_FIELD_INVALID")
            continue
        timestamps.append(timestamp)
        if not start_ns <= timestamp < end_ns:
            _append_once(reasons, "TS_EVENT_OUTSIDE_HALF_OPEN_SEGMENT")
        if expected_instrument_id is None or instrument_id != expected_instrument_id:
            _append_once(reasons, "INSTRUMENT_ID_MISMATCH")
        denominator = sum(bid_sizes) + sum(ask_sizes)
        if (
            not all(math.isfinite(value) and value >= 0 for value in (*bid_sizes, *ask_sizes))
            or not math.isfinite(denominator)
            or denominator <= 0
        ):
            _append_once(reasons, "I5_DENOMINATOR_NONPOSITIVE_OR_NONFINITE")
        else:
            imbalances.append((sum(bid_sizes) - sum(ask_sizes)) / denominator)
        spread_ticks = (ask_px - bid_px) / TICK_RAW
        spreads.append(spread_ticks)

    if any(right < left for left, right in zip(timestamps, timestamps[1:])):
        _append_once(reasons, "TS_EVENT_NONMONOTONIC")
    positive_gaps = [right - left for left, right in zip(timestamps, timestamps[1:])]
    max_gap = max(positive_gaps, default=None)
    if max_gap is not None and max_gap > ONE_SECOND_NS:
        _append_once(reasons, "MAX_GAP_GT_1S")
    if timestamps and end_ns - timestamps[-1] > ONE_SECOND_NS:
        _append_once(reasons, "FINAL_STALENESS_GT_1S")

    i5_median = statistics.median(imbalances) if len(imbalances) == len(rows) and rows else None
    median_spread = statistics.median(spreads) if len(spreads) == len(rows) and rows else None
    return {
        "record_count": len(rows),
        "quality_pass": not reasons,
        "reason_codes": reasons,
        "i5_median": i5_median,
        "median_spread_ticks": median_spread,
        "first_ts_event_ns": timestamps[0] if timestamps else None,
        "last_ts_event_ns": timestamps[-1] if timestamps else None,
        "max_gap_ns": max_gap,
    }


def explicit_source_empty_segment(
    metadata_reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "record_count": 0,
        "quality_pass": False,
        "reason_codes": ["EXPLICIT_SOURCE_EMPTY", *metadata_reason_codes],
        "i5_median": None,
        "median_spread_ticks": None,
        "first_ts_event_ns": None,
        "last_ts_event_ns": None,
        "max_gap_ns": None,
    }


def evaluate_pair(
    pre: dict[str, Any], late: dict[str, Any]
) -> dict[str, Any]:
    reasons: list[str] = []
    if not pre.get("quality_pass"):
        reasons.append("PRE_SEGMENT_QUALITY_FAIL")
    if not late.get("quality_pass"):
        reasons.append("LATE_SEGMENT_QUALITY_FAIL")
    spread = late.get("median_spread_ticks")
    if not isinstance(spread, (int, float)) or isinstance(spread, bool) or not math.isfinite(float(spread)):
        reasons.append("LATE_MEDIAN_SPREAD_NONFINITE")
    elif float(spread) < 0:
        reasons.append("LATE_MEDIAN_SPREAD_NEGATIVE")
    elif float(spread) > MAX_SPREAD_TICKS:
        reasons.append("LATE_MEDIAN_SPREAD_GT_2_TICKS")

    i5_pre = pre.get("i5_median")
    i5_late = late.get("i5_median")
    delta: float | None = None
    if isinstance(i5_pre, (int, float)) and isinstance(i5_late, (int, float)):
        delta = float(i5_late) - float(i5_pre)
    pair_quality = not reasons
    eligible = False
    direction = ""
    if (
        pair_quality
        and delta is not None
        and math.isfinite(float(i5_late))
        and math.isfinite(delta)
        and float(i5_late) != 0.0
        and delta != 0.0
        and ((float(i5_late) > 0 and delta > 0) or (float(i5_late) < 0 and delta < 0))
    ):
        eligible = True
        direction = "LONG" if float(i5_late) > 0 else "SHORT"
    return {
        "pair_quality_pass": pair_quality,
        "pair_reason_codes": reasons,
        "i5_pre": i5_pre,
        "i5_late": i5_late,
        "delta_i5": delta,
        "late_median_spread_ticks": spread,
        "feature_eligible": eligible,
        "direction": direction,
    }


def decoded_metadata_reason_codes(
    decoded: dict[str, Any], request: dict[str, Any]
) -> list[str]:
    reasons: list[str] = []
    expected_values = {
        "dataset": (DATASET, "DBN_DATASET_MISMATCH"),
        "schema": (SCHEMA, "DBN_SCHEMA_MISMATCH"),
        "stype_in": (STYPE_IN, "DBN_STYPE_IN_MISMATCH"),
        "stype_out": (STYPE_OUT, "DBN_STYPE_OUT_MISMATCH"),
        "symbols": ([SYMBOL], "DBN_SYMBOL_MISMATCH"),
    }
    for field, (expected, reason) in expected_values.items():
        if decoded.get(field) != expected:
            reasons.append(reason)
    if decoded.get("mapping_ok") is not True or not isinstance(
        decoded.get("expected_instrument_id"), int
    ):
        reasons.append("INSTRUMENT_MAPPING_INVALID")
    if decoded.get("metadata_start_ns") != parse_utc_ns(str(request.get("start"))):
        reasons.append("DBN_METADATA_START_MISMATCH")
    if decoded.get("metadata_end_ns") != parse_utc_ns(str(request.get("end"))):
        reasons.append("DBN_METADATA_END_MISMATCH")
    return reasons


def _decode_local_dbn(payload: bytes, request: dict[str, Any]) -> dict[str, Any]:
    try:
        import databento as db
    except ImportError as exc:
        raise Stage0Error(
            "Databento DBN runtime is unavailable; use the dedicated D-side runtime"
        ) from exc
    try:
        store = db.DBNStore.from_bytes(payload)
        records_value = store.to_ndarray()
    except Exception as exc:
        raise Stage0Error(
            f"local DBNStore decode failed: {request.get('filename')}: {exc}"
        ) from exc

    event_date = parse_utc(str(request["event_time_utc"])).date()
    mappings = store.mappings
    entries = mappings.get(SYMBOL, []) if isinstance(mappings, dict) else []
    active_ids: list[int] = []
    for item in entries:
        try:
            start_date = item["start_date"]
            end_date = item["end_date"]
            instrument_id = int(item["symbol"])
        except (KeyError, TypeError, ValueError):
            continue
        if isinstance(start_date, date) and isinstance(end_date, date) and start_date <= event_date < end_date:
            active_ids.append(instrument_id)
    unique_ids = sorted(set(active_ids))
    mapping_ok = len(unique_ids) == 1 and set(mappings) == {SYMBOL}
    return {
        "dataset": str(store.dataset),
        "schema": str(store.schema),
        "stype_in": str(store.stype_in),
        "stype_out": str(store.stype_out),
        "symbols": [str(item) for item in store.symbols],
        "mapping_ok": mapping_ok,
        "expected_instrument_id": unique_ids[0] if mapping_ok else None,
        "metadata_start_ns": datetime_ns(store.start),
        "metadata_end_ns": datetime_ns(store.end),
        "records": records_value,
    }


def cadence_is_legal(value: float) -> bool:
    return math.isfinite(value) and MIN_CADENCE <= value <= MAX_CADENCE


def summarize_population(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    event_count = len(rows)
    denominator = EXPECTED_EVENTS
    pre_nonempty = sum(not bool(row.get("pre_source_empty")) for row in rows)
    late_nonempty = sum(not bool(row.get("late_source_empty")) for row in rows)
    paired_nonempty = sum(
        not bool(row.get("pre_source_empty")) and not bool(row.get("late_source_empty"))
        for row in rows
    )
    source_quality = sum(bool(row.get("pair_quality_pass")) for row in rows)
    feature_eligible = sum(bool(row.get("feature_eligible")) for row in rows)
    fatal_integrity = sum(bool(row.get("fatal_source_integrity_failure")) for row in rows)
    pre_records = sum(int(row.get("pre_record_count", 0) or 0) for row in rows)
    late_records = sum(int(row.get("late_record_count", 0) or 0) for row in rows)
    source_empty_files = sum(bool(row.get("pre_source_empty")) for row in rows) + sum(
        bool(row.get("late_source_empty")) for row in rows
    )
    direction_counts = {
        "LONG": sum(row.get("direction") == "LONG" for row in rows),
        "SHORT": sum(row.get("direction") == "SHORT" for row in rows),
    }
    quality_reason_counts: dict[str, int] = {}
    for row in rows:
        for field in (
            "pre_quality_reason_codes",
            "late_quality_reason_codes",
            "pair_quality_reason_codes",
        ):
            for reason in row.get(field, []) or []:
                quality_reason_counts[str(reason)] = quality_reason_counts.get(str(reason), 0) + 1
    cadence = feature_eligible / ELAPSED_DESIGN_WEEKS
    coverages = {
        "pre_nonempty_coverage": pre_nonempty / denominator,
        "late_nonempty_coverage": late_nonempty / denominator,
        "paired_nonempty_event_coverage": paired_nonempty / denominator,
    }
    gates = {
        "request_identity_count": {
            "pass": event_count * 2 == EXPECTED_REQUESTS,
            "actual": event_count * 2,
            "expected": EXPECTED_REQUESTS,
        },
        "event_pair_count": {
            "pass": event_count == EXPECTED_EVENTS,
            "actual": event_count,
            "expected": EXPECTED_EVENTS,
        },
        "pre_nonempty_coverage": {
            "pass": coverages["pre_nonempty_coverage"] >= MIN_NONEMPTY_COVERAGE,
            "actual": coverages["pre_nonempty_coverage"],
            "minimum": MIN_NONEMPTY_COVERAGE,
        },
        "late_nonempty_coverage": {
            "pass": coverages["late_nonempty_coverage"] >= MIN_NONEMPTY_COVERAGE,
            "actual": coverages["late_nonempty_coverage"],
            "minimum": MIN_NONEMPTY_COVERAGE,
        },
        "paired_nonempty_event_coverage": {
            "pass": coverages["paired_nonempty_event_coverage"] >= MIN_NONEMPTY_COVERAGE,
            "actual": coverages["paired_nonempty_event_coverage"],
            "minimum": MIN_NONEMPTY_COVERAGE,
        },
        "feature_eligible_count": {
            "pass": feature_eligible >= MIN_FEATURE_EVENTS,
            "actual": feature_eligible,
            "minimum": MIN_FEATURE_EVENTS,
        },
        "feature_eligible_cadence": {
            "pass": cadence_is_legal(cadence),
            "actual": cadence,
            "minimum": MIN_CADENCE,
            "maximum": MAX_CADENCE,
            "elapsed_weeks": ELAPSED_DESIGN_WEEKS,
        },
        "fatal_source_integrity_failures": {
            "pass": fatal_integrity == 0,
            "actual": fatal_integrity,
            "expected": 0,
        },
        "prohibited_reads": {
            "pass": all(value == 0 for value in PROHIBITED_READ_COUNTERS.values()),
            "actual": dict(PROHIBITED_READ_COUNTERS),
        },
    }
    failed = [name for name, gate in gates.items() if gate["pass"] is not True]
    return {
        "event_count": event_count,
        "pre_nonempty_count": pre_nonempty,
        "late_nonempty_count": late_nonempty,
        "paired_nonempty_event_count": paired_nonempty,
        **coverages,
        "source_quality_paired_count": source_quality,
        "source_quality_failure_count": paired_nonempty - source_quality,
        "feature_eligible_count": feature_eligible,
        "sign_feature_ineligible_count": source_quality - feature_eligible,
        "pre_record_count_total": pre_records,
        "late_record_count_total": late_records,
        "source_empty_file_count": source_empty_files,
        "direction_counts": direction_counts,
        "quality_reason_counts": dict(sorted(quality_reason_counts.items())),
        "feature_eligible_cadence_per_elapsed_week": cadence,
        "elapsed_design_weeks": ELAPSED_DESIGN_WEEKS,
        "fatal_source_integrity_failure_count": fatal_integrity,
        "gates": gates,
        "failure_reasons": failed,
        "stage0_pass": not failed,
        "verdict": PASS_VERDICT if not failed else FAILURE_VERDICT,
    }


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise Stage0Error("non-finite value cannot enter deterministic ledger")
        if value == 0:
            value = 0.0
        return format(value, ".15g")
    if isinstance(value, (list, tuple)):
        return "|".join(str(item) for item in value)
    return str(value)


def render_ledger(rows: Sequence[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=LEDGER_FIELDS,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in sorted(
        rows, key=lambda item: (str(item["event_time_utc"]), str(item["event_clock_id"]))
    ):
        writer.writerow({field: _csv_cell(row.get(field)) for field in LEDGER_FIELDS})
    return output.getvalue().encode("utf-8")


def render_json(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def build_output_manifest(
    *,
    bindings: dict[str, Any],
    raw_bindings: Sequence[dict[str, Any]],
    summary: dict[str, Any],
    analyzer_sha256: str,
    tests_sha256: str,
    ledger_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "event_clob_stage0_source_quality_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": (
            "STAGE0B_D_OUTCOME_BLIND_PASS"
            if summary["stage0_pass"]
            else "STAGE0B_D_OUTCOME_BLIND_FAIL"
        ),
        "verdict": summary["verdict"],
        "bindings": bindings,
        "artifacts": {
            "analyzer": {
                "path": _workspace_path(SOURCE_PATH),
                "sha256": analyzer_sha256,
            },
            "tests": {
                "path": _workspace_path(TEST_PATH),
                "sha256": tests_sha256,
            },
            "feature_ledger": {
                "path": _workspace_path(LEDGER_PATH),
                "sha256": ledger_sha256,
                "rows": summary["event_count"],
            },
        },
        "raw_files": sorted(
            (
                {
                    key: value
                    for key, value in item.items()
                    if not str(key).startswith("_")
                }
                for item in raw_bindings
            ),
            key=lambda item: item["request_id"],
        ),
        "counters": {
            "request_identities": len(raw_bindings),
            "events": summary["event_count"],
            "pre_nonempty": summary["pre_nonempty_count"],
            "late_nonempty": summary["late_nonempty_count"],
            "paired_nonempty_events": summary["paired_nonempty_event_count"],
            "source_quality_paired_events": summary["source_quality_paired_count"],
            "source_quality_failures": summary["source_quality_failure_count"],
            "feature_eligible_events": summary["feature_eligible_count"],
            "sign_feature_ineligible_events": summary[
                "sign_feature_ineligible_count"
            ],
            "pre_records": summary["pre_record_count_total"],
            "late_records": summary["late_record_count_total"],
            "source_empty_files": summary["source_empty_file_count"],
        },
        "direction_counts": summary["direction_counts"],
        "quality_reason_counts": summary["quality_reason_counts"],
        "coverages": {
            "pre_nonempty": summary["pre_nonempty_coverage"],
            "late_nonempty": summary["late_nonempty_coverage"],
            "paired_nonempty_events": summary["paired_nonempty_event_coverage"],
        },
        "elapsed_design_weeks": summary["elapsed_design_weeks"],
        "feature_eligible_cadence_per_elapsed_week": summary[
            "feature_eligible_cadence_per_elapsed_week"
        ],
        "gates": summary["gates"],
        "failure_reasons": summary["failure_reasons"],
        "prohibited_read_counters": dict(PROHIBITED_READ_COUNTERS),
        "outcome_blindness": {
            "market_edge_verdict": False,
            "outcome_fields_used": False,
            "price_data_read": False,
            "validation_source_sealed": True,
        },
    }


def _workspace_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(WORKSPACE.resolve())
    except ValueError as exc:
        raise Stage0Error(f"path escapes workspace: {path}") from exc
    return relative.as_posix()


def _same_exact_path(actual: Path, expected: Path) -> bool:
    return (
        actual.is_absolute()
        and expected.is_absolute()
        and _lexical_key(actual) == _lexical_key(expected)
    )


def validate_exact_cli_paths(
    *,
    data_root: Path,
    task_packet: Path,
    prereg: Path,
    clock_csv: Path,
    ledger_out: Path,
    manifest_out: Path,
    readout_out: Path,
) -> None:
    expected = {
        "data root": (data_root, CANONICAL_DATA_ROOT),
        "task packet": (task_packet, TASK_PACKET_PATH),
        "preregistration": (prereg, PREREG_PATH),
        "clock CSV": (clock_csv, CLOCK_PATH),
        "feature ledger": (ledger_out, LEDGER_PATH),
        "output manifest": (manifest_out, OUTPUT_MANIFEST_PATH),
        "readout": (readout_out, READOUT_PATH),
    }
    output_labels = {"feature ledger", "output manifest", "readout"}
    for label, (actual, canonical) in expected.items():
        if not _same_exact_path(Path(actual), canonical):
            raise Stage0Error(
                f"{label} must use the exact canonical path: {canonical}"
            )
        validate_secure_path(
            Path(actual),
            expected=canonical,
            containment_root=WORKSPACE,
            must_exist=label not in output_labels,
        )
    if CANONICAL_DATA_ROOT.drive.upper() != "D:":
        raise Stage0Error("Stage0 data root is not on the exact D: drive")


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _strict_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8-sig"),
            parse_constant=_reject_nonfinite,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise Stage0Error("strict JSON decode failed") from exc


RUN_AUTHORITY_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "base_packet_path",
    "base_packet_sha256",
    "amendment_path",
    "amendment_sha256",
    "review_verdict",
    "reviewed_analyzer_path",
    "reviewed_analyzer_sha256",
    "reviewed_tests_path",
    "reviewed_tests_sha256",
    "required_python_relative_path",
    "required_python_sha256",
    "required_python_version",
    "required_databento_version",
    "live_stage0_authorized",
}


def _relative_contract_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise Stage0Error(f"reviewed path escapes its contract root: {path}") from exc


def _reviewed_root(path: Path, preferred: Path) -> Path:
    try:
        common = os.path.commonpath([os.fspath(path), os.fspath(preferred)])
    except ValueError:
        common = ""
    return preferred if os.path.normcase(common) == os.path.normcase(os.fspath(preferred)) else WORKSPACE


def _require_bound_hash(path: Path, expected: str, *, root: Path, label: str) -> str:
    validate_secure_path(
        path,
        expected=path,
        containment_root=root,
        must_exist=True,
    )
    if not path.is_file():
        raise Stage0Error(f"bound {label} is not a file: {path}")
    actual = sha256_file(path)
    if actual != expected.upper():
        raise Stage0Error(
            f"{label} hash mismatch: expected {expected.upper()}, got {actual}"
        )
    return actual


def validate_run_authority(
    authority_path: Path,
    expected_sha256: str,
    *,
    expected_path: Path = RUN_AUTHORITY_PATH,
    containment_root: Path = WORKSPACE,
    reviewed_analyzer_path: Path = SOURCE_PATH,
    reviewed_tests_path: Path = TEST_PATH,
) -> dict[str, Any]:
    authority_path = Path(authority_path)
    validate_secure_path(
        authority_path,
        expected=Path(expected_path),
        containment_root=Path(containment_root),
        must_exist=authority_path.exists(),
    )
    if not authority_path.is_file():
        raise Stage0Error(f"missing run-authority receipt: {authority_path}")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise Stage0Error("expected run-authority SHA256 is invalid")
    try:
        receipt_bytes = authority_path.read_bytes()
    except OSError as exc:
        raise Stage0Error(f"cannot read run-authority receipt: {authority_path}") from exc
    receipt_hash = sha256_bytes(receipt_bytes)
    if receipt_hash != expected_sha256.upper():
        raise Stage0Error(
            f"run-authority hash mismatch: expected {expected_sha256.upper()}, "
            f"got {receipt_hash}"
        )
    payload = _strict_json(receipt_bytes)
    if not isinstance(payload, dict) or set(payload) != RUN_AUTHORITY_FIELDS:
        raise Stage0Error("run-authority receipt fields are not exact")
    if payload["schema_version"] != "event_clob_stage0_run_authority.v1":
        raise Stage0Error("run-authority schema mismatch")
    if payload["hypothesis_id"] != HYPOTHESIS_ID:
        raise Stage0Error("run-authority hypothesis mismatch")
    if payload["review_verdict"] != "PASS":
        raise Stage0Error("run-authority independent review verdict is not PASS")
    if payload["live_stage0_authorized"] is not True:
        raise Stage0Error("live Stage0 is not authorized by run-authority receipt")

    base_expected = {
        "base_packet_path": _workspace_path(TASK_PACKET_PATH),
        "base_packet_sha256": TASK_PACKET_SHA256,
        "amendment_path": _workspace_path(V3_TASK_PACKET_PATH),
        "amendment_sha256": V3_TASK_PACKET_SHA256,
    }
    for field, expected in base_expected.items():
        if payload[field] != expected:
            label = "base packet" if field.startswith("base_") else "amendment"
            raise Stage0Error(f"run-authority {label} binding mismatch: {field}")
    _require_hash(TASK_PACKET_PATH, TASK_PACKET_SHA256, "base packet")
    _require_hash(V2_TASK_PACKET_PATH, V2_TASK_PACKET_SHA256, "V2 amendment")
    _require_hash(V3_TASK_PACKET_PATH, V3_TASK_PACKET_SHA256, "amendment")

    analyzer_root = _reviewed_root(Path(reviewed_analyzer_path), Path(containment_root))
    tests_root = _reviewed_root(Path(reviewed_tests_path), Path(containment_root))
    if Path(reviewed_analyzer_path) == SOURCE_PATH:
        validate_secure_path(
            SOURCE_INVOCATION_PATH,
            expected=SOURCE_PATH,
            containment_root=WORKSPACE,
            must_exist=True,
        )
    expected_analyzer_contract_path = _relative_contract_path(
        Path(reviewed_analyzer_path), analyzer_root
    )
    expected_tests_contract_path = _relative_contract_path(
        Path(reviewed_tests_path), tests_root
    )
    if payload["reviewed_analyzer_path"] != expected_analyzer_contract_path:
        raise Stage0Error("run-authority reviewed analyzer path mismatch")
    if payload["reviewed_tests_path"] != expected_tests_contract_path:
        raise Stage0Error("run-authority reviewed tests path mismatch")
    _require_bound_hash(
        Path(reviewed_analyzer_path),
        str(payload["reviewed_analyzer_sha256"]),
        root=analyzer_root,
        label="reviewed analyzer",
    )
    _require_bound_hash(
        Path(reviewed_tests_path),
        str(payload["reviewed_tests_sha256"]),
        root=tests_root,
        label="reviewed tests",
    )

    if payload["required_python_relative_path"] != REQUIRED_PYTHON_RELATIVE_PATH:
        raise Stage0Error("run-authority runtime path mismatch")
    if payload["required_python_sha256"] != REQUIRED_PYTHON_SHA256:
        raise Stage0Error("run-authority runtime hash mismatch")
    validate_secure_path(
        Path(sys.executable),
        expected=REQUIRED_PYTHON_PATH,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    _require_hash(REQUIRED_PYTHON_PATH, REQUIRED_PYTHON_SHA256, "runtime")
    if payload["required_python_version"] != platform.python_version():
        raise Stage0Error("run-authority Python version mismatch")
    try:
        import databento as db
    except ImportError as exc:
        raise Stage0Error("required Databento runtime is unavailable") from exc
    if (
        payload["required_databento_version"] != REQUIRED_DATABENTO_VERSION
        or getattr(db, "__version__", None) != REQUIRED_DATABENTO_VERSION
    ):
        raise Stage0Error("run-authority Databento version mismatch")
    return {
        "path": authority_path,
        "expected_path": Path(expected_path),
        "containment_root": Path(containment_root),
        "expected_sha256": receipt_hash,
        "receipt_bytes": receipt_bytes,
        "reviewed_analyzer_path": Path(reviewed_analyzer_path),
        "reviewed_tests_path": Path(reviewed_tests_path),
        "payload": payload,
    }


def revalidate_run_authority(snapshot: dict[str, Any]) -> dict[str, Any]:
    current = validate_run_authority(
        Path(snapshot["path"]),
        str(snapshot["expected_sha256"]),
        expected_path=Path(snapshot["expected_path"]),
        containment_root=Path(snapshot["containment_root"]),
        reviewed_analyzer_path=Path(snapshot["reviewed_analyzer_path"]),
        reviewed_tests_path=Path(snapshot["reviewed_tests_path"]),
    )
    if current["receipt_bytes"] != snapshot["receipt_bytes"]:
        raise Stage0Error("run-authority receipt bytes changed before publication")
    return current


def _iter_decoded_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _iter_decoded_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_decoded_strings(item)


class _RegistrySnapshotAdapter:
    def __init__(self, payload: bytes) -> None:
        self.payload = bytes(payload)

    def is_file(self) -> bool:
        return True

    def read_text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self.payload.decode(encoding, errors)

    def __str__(self) -> str:
        return "<immutable-stage0-registry-snapshot>"


def _registry_receipt(snapshot: bytes) -> str:
    rows = [raw for raw in snapshot.decode("utf-8-sig").splitlines() if raw]
    hypotheses = {str(_strict_json(raw.encode("utf-8"))["hypothesis_id"]) for raw in rows}
    return f"CANDIDATE_REGISTRY_OK rows={len(rows)} hypotheses={len(hypotheses)}"


def _validate_registry_snapshot(snapshot: bytes) -> str:
    try:
        spec = importlib.util.spec_from_file_location(
            "event_clob_stage0_registry_validator", REGISTRY_VALIDATOR_PATH
        )
        if spec is None or spec.loader is None:
            raise Stage0Error("cannot load canonical registry validator")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        errors = validator.validate_registry(
            _RegistrySnapshotAdapter(snapshot), validator.DEFAULT_SCHEMA
        )
    except ModuleNotFoundError:
        python = shutil.which("python")
        if not python or Path(python).resolve() == Path(sys.executable).resolve():
            raise Stage0Error(
                "canonical registry validator runtime with jsonschema is unavailable"
            )
        helper = (
            "import importlib.util,json,sys\n"
            "from pathlib import Path\n"
            "payload=sys.stdin.buffer.read()\n"
            "class Snapshot:\n"
            " def is_file(self): return True\n"
            " def read_text(self,encoding='utf-8',errors='strict'): "
            "return payload.decode(encoding,errors)\n"
            " def __str__(self): return '<immutable-stage0-registry-snapshot>'\n"
            "path=Path(sys.argv[1]).resolve()\n"
            "spec=importlib.util.spec_from_file_location('stage0_registry_validator',path)\n"
            "module=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "errors=module.validate_registry(Snapshot(),module.DEFAULT_SCHEMA)\n"
            "print(json.dumps(errors,ensure_ascii=False))\n"
        )
        completed = subprocess.run(
            [python, "-B", "-X", "utf8", "-c", helper, str(REGISTRY_VALIDATOR_PATH)],
            cwd=WORKSPACE,
            input=snapshot,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).decode(
                "utf-8", errors="replace"
            )
            raise Stage0Error(f"canonical registry validator failed: {detail.strip()}")
        try:
            errors = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Stage0Error("canonical registry validator returned malformed output") from exc
    except Stage0Error:
        raise
    except Exception as exc:
        raise Stage0Error(f"canonical registry validator failed: {exc}") from exc
    if errors:
        raise Stage0Error("canonical registry validator failed: " + " | ".join(errors))
    return _registry_receipt(snapshot)


def verify_registry_authority() -> dict[str, Any]:
    validate_secure_path(
        REGISTRY_PATH,
        expected=REGISTRY_PATH,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    validate_secure_path(
        REGISTRY_VALIDATOR_PATH,
        expected=REGISTRY_VALIDATOR_PATH,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    if not REGISTRY_PATH.is_file():
        raise Stage0Error("canonical registry is missing or unsafe")
    snapshot = REGISTRY_PATH.read_bytes()
    lines = snapshot.splitlines(keepends=True)
    if len(lines) < V14_PREFIX_ROWS:
        raise Stage0Error("V14 registry prefix is truncated")
    for raw in lines:
        if not raw.endswith(b"\n") or raw.endswith(b"\r\n"):
            raise Stage0Error("registry is not strict LF JSONL")
    prefix = b"".join(lines[:V14_PREFIX_ROWS])
    if sha256_bytes(prefix) != V14_PREFIX_SHA256:
        raise Stage0Error("V14 exact 272-row registry prefix mismatch")
    v14 = _load_json(V14_PACKET_PATH)
    tokens = tuple(
        str(item).casefold()
        for item in v14["append_tolerance_contract"][
            "reject_appended_rows_if_serialized_content_mentions_any_case_insensitive_token"
        ]
    )
    parsed: list[tuple[bytes, dict[str, Any]]] = []
    for index, raw in enumerate(lines, 1):
        row = _strict_json(raw[:-1])
        if not isinstance(row, dict):
            raise Stage0Error(f"registry row {index} is not an object")
        parsed.append((raw[:-1], row))
        if index > V14_PREFIX_ROWS:
            conflict = next(
                (
                    token
                    for text in _iter_decoded_strings(row)
                    for token in tokens
                    if token in text.casefold()
                ),
                None,
            )
            if conflict is not None:
                raise Stage0Error(
                    f"registry append contains EventCLOB conflict token: {conflict}"
                )
    hypothesis_rows = [
        (raw, row) for raw, row in parsed if row.get("hypothesis_id") == HYPOTHESIS_ID
    ]
    row_hashes = tuple(sha256_bytes(raw) for raw, _row in hypothesis_rows)
    if row_hashes != HYPOTHESIS_ROW_SHA256_SEQUENCE:
        raise Stage0Error("exact HYP-002 registry history mismatch")
    latest = hypothesis_rows[-1][1]
    if (
        latest.get("state") != "parked"
        or latest.get("verdict") != "PARK_DESIGN_SOURCE_PAYMENT_AUTHORITY_UNMET"
    ):
        raise Stage0Error("HYP-002 registry terminal state/verdict mismatch")
    validator_result = _validate_registry_snapshot(snapshot)
    return {
        "path": _workspace_path(REGISTRY_PATH),
        "sha256": sha256_bytes(snapshot),
        "rows": len(lines),
        "prefix_rows": V14_PREFIX_ROWS,
        "prefix_sha256": V14_PREFIX_SHA256,
        "validator_result": validator_result,
        "hypothesis_row_sha256_sequence": list(row_hashes),
        "latest_state": latest["state"],
        "latest_verdict": latest["verdict"],
    }


def verify_frozen_bindings() -> dict[str, Any]:
    validate_secure_path(
        CANONICAL_DATA_ROOT,
        expected=CANONICAL_DATA_ROOT,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    validate_secure_path(
        RAW_ROOT,
        expected=RAW_ROOT,
        containment_root=CANONICAL_DATA_ROOT,
        must_exist=True,
    )
    if not CANONICAL_DATA_ROOT.is_dir():
        raise Stage0Error("exact D-side Stage0 root is missing or unsafe")
    if not RAW_ROOT.is_dir():
        raise Stage0Error("exact D-side Stage0 raw root is missing or unsafe")
    bindings = {
        "task_packet_sha256": _require_hash(
            TASK_PACKET_PATH, TASK_PACKET_SHA256, "Stage0 task packet"
        ),
        "v2_amendment_sha256": _require_hash(
            V2_TASK_PACKET_PATH, V2_TASK_PACKET_SHA256, "Stage0 V2 amendment"
        ),
        "v3_amendment_sha256": _require_hash(
            V3_TASK_PACKET_PATH, V3_TASK_PACKET_SHA256, "Stage0 V3 amendment"
        ),
        "v14_source_task_packet_sha256": _require_hash(
            V14_PACKET_PATH, V14_PACKET_SHA256, "V14 source task packet"
        ),
        "prereg_sha256": _require_hash(PREREG_PATH, PREREG_SHA256, "preregistration"),
        "download_manifest_sha256": _require_hash(
            DOWNLOAD_MANIFEST_PATH, DOWNLOAD_MANIFEST_SHA256, "download manifest"
        ),
        "acquisition_authority_receipt_sha256": _require_hash(
            AUTHORITY_RECEIPT_PATH,
            AUTHORITY_RECEIPT_SHA256,
            "acquisition authority receipt",
        ),
        "live_requote_plan_sha256": _require_hash(
            LIVE_REQUOTE_PLAN_PATH, LIVE_REQUOTE_PLAN_SHA256, "live requote plan"
        ),
        "live_requote_receipt_sha256": _require_hash(
            LIVE_REQUOTE_RECEIPT_PATH,
            LIVE_REQUOTE_RECEIPT_SHA256,
            "live requote receipt",
        ),
        "clock_csv_sha256": _require_hash(CLOCK_PATH, CLOCK_SHA256, "clock CSV"),
        "clock_manifest_sha256": _require_hash(
            CLOCK_MANIFEST_PATH, CLOCK_MANIFEST_SHA256, "clock manifest"
        ),
    }
    packet = _load_json(TASK_PACKET_PATH)
    sealed = packet.get("sealed_inputs", {})
    authority = packet.get("authority_chain", {})
    if (
        packet.get("hypothesis_id") != HYPOTHESIS_ID
        or sealed.get("data_root") != _workspace_path(CANONICAL_DATA_ROOT)
        or sealed.get("download_manifest", {}).get("sha256")
        != DOWNLOAD_MANIFEST_SHA256
        or sealed.get("validation_source_sealed") is not True
        or sealed.get("outcome_fields_used") is not False
        or sealed.get("price_data_read") is not False
        or authority.get("owner_ceiling_usd") != 3.5
        or authority.get("owner_plan_id")
        != "DEDDE7F292738C16A200C59903F7839C85B728818805AA09D46D3E7F188E0C16"
    ):
        raise Stage0Error("Stage0 task packet outcome-sealing contract mismatch")
    source_manifest = _load_json(DOWNLOAD_MANIFEST_PATH)
    if (
        source_manifest.get("authorization_basis_plan_id")
        != authority["owner_plan_id"]
        or source_manifest.get("approved_max_usd") != authority["owner_ceiling_usd"]
        or source_manifest.get("validation_source_sealed") is not True
        or source_manifest.get("outcome_fields_used") is not False
        or source_manifest.get("price_data_read") is not False
    ):
        raise Stage0Error("download manifest authority/outcome sealing mismatch")
    bindings["registry"] = verify_registry_authority()
    return bindings


def load_design_clocks(path: Path = CLOCK_PATH) -> list[dict[str, str]]:
    validate_secure_path(
        path,
        expected=CLOCK_PATH,
        containment_root=WORKSPACE,
        must_exist=True,
    )
    rows: list[dict[str, str]] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {
                "event_clock_id",
                "event_time_utc",
            }.issubset(reader.fieldnames):
                raise Stage0Error("clock CSV lacks frozen identity fields")
            for raw in reader:
                event_id = str(raw["event_clock_id"])
                event_time = str(raw["event_time_utc"])
                if parse_utc(event_time).year in DESIGN_YEARS:
                    rows.append(
                        {"event_clock_id": event_id, "event_time_utc": event_time}
                    )
    except OSError as exc:
        raise Stage0Error(f"cannot read frozen clock CSV: {path}") from exc
    rows.sort(key=lambda item: (item["event_time_utc"], item["event_clock_id"]))
    identities = [item["event_clock_id"] for item in rows]
    timestamps = [item["event_time_utc"] for item in rows]
    if len(rows) != EXPECTED_EVENTS:
        raise Stage0Error(f"design clock coverage is {len(rows)}/{EXPECTED_EVENTS}")
    if len(set(identities)) != len(rows) or len(set(timestamps)) != len(rows):
        raise Stage0Error("design clocks contain duplicate identity or timestamp")
    return rows


def validate_manifest_contract(
    manifest: dict[str, Any], clocks: Sequence[dict[str, str]]
) -> dict[str, dict[str, dict[str, Any]]]:
    exact_top = {
        "schema_version": "event_clob_cme6e_mbp10_download_manifest.v1",
        "status": "DOWNLOADED_FULL_DBN_VALIDATION_PASS",
        "hypothesis_id": HYPOTHESIS_ID,
        "profile": "design-segments",
        "in_flight": None,
        "paid_requests_completed": EXPECTED_REQUESTS,
        "timeseries_calls": EXPECTED_REQUESTS,
        "validation_source_sealed": True,
        "outcome_fields_used": False,
        "price_data_read": False,
    }
    for field, expected in exact_top.items():
        if manifest.get(field) != expected:
            raise Stage0Error(
                f"download manifest {field} mismatch: expected {expected!r}, "
                f"got {manifest.get(field)!r}"
            )
    requests = manifest.get("downloads")
    if not isinstance(requests, list) or len(requests) != EXPECTED_REQUESTS:
        raise Stage0Error(
            f"download manifest request coverage is "
            f"{len(requests) if isinstance(requests, list) else 'invalid'}/{EXPECTED_REQUESTS}"
        )
    if not all(isinstance(item, dict) for item in requests):
        raise Stage0Error("download manifest contains a non-object request")
    validate_unique_requests(requests)
    clock_map = {item["event_clock_id"]: item["event_time_utc"] for item in clocks}
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for request in requests:
        validate_request_contract(request)
        event_id = str(request["event_clock_id"])
        if clock_map.get(event_id) != request["event_time_utc"]:
            raise Stage0Error(f"request clock identity/time mismatch: {event_id}")
        segment = str(request["segment"])
        grouped.setdefault(event_id, {})[segment] = request
        source_empty = request.get("source_empty")
        record_count = request.get("records")
        if not isinstance(source_empty, bool):
            raise Stage0Error(f"source_empty flag is invalid: {request['request_id']}")
        if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count < 0:
            raise Stage0Error(f"manifest record count is invalid: {request['request_id']}")
        if source_empty:
            evidence = request.get("charged_empty_evidence")
            if record_count != 0 or not isinstance(evidence, dict) or any(
                evidence.get(field) is not True
                for field in (
                    "paid_request_completed",
                    "response_validated",
                    "retry_prohibited",
                )
            ):
                raise Stage0Error(
                    f"explicit source-empty evidence is invalid: {request['request_id']}"
                )
        elif record_count <= 0 or request.get("charged_empty_evidence") is not None:
            raise Stage0Error(f"nonempty request evidence is invalid: {request['request_id']}")
    if set(grouped) != set(clock_map):
        raise Stage0Error("download manifest event identities do not match design clocks")
    for event_id, segments in grouped.items():
        if set(segments) != {"PRE", "LATE"}:
            raise Stage0Error(f"event pair is incomplete: {event_id}")
    return grouped


FATAL_SEGMENT_REASONS = {
    "DBN_DATASET_MISMATCH",
    "DBN_SCHEMA_MISMATCH",
    "DBN_STYPE_IN_MISMATCH",
    "DBN_STYPE_OUT_MISMATCH",
    "DBN_SYMBOL_MISMATCH",
    "INSTRUMENT_MAPPING_INVALID",
    "INSTRUMENT_ID_MISMATCH",
    "TS_EVENT_NONMONOTONIC",
    "TS_EVENT_OUTSIDE_HALF_OPEN_SEGMENT",
    "DBN_METADATA_START_MISMATCH",
    "DBN_METADATA_END_MISMATCH",
}


def analyze_snapshot(
    *,
    manifest: dict[str, Any],
    clocks: Sequence[dict[str, str]],
    raw_root: Path,
    record_loader: Callable[[bytes, dict[str, Any]], dict[str, Any]] = _decode_local_dbn,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    grouped = validate_manifest_contract(manifest, clocks)
    requests = [item for segments in grouped.values() for item in segments.values()]
    verify_raw_file_set(raw_root, requests)
    rows: list[dict[str, Any]] = []
    raw_bindings: list[dict[str, Any]] = []
    ordered_clocks = sorted(
        clocks, key=lambda item: (item["event_time_utc"], item["event_clock_id"])
    )
    for clock in ordered_clocks:
        event_id = clock["event_clock_id"]
        segments = grouped[event_id]
        analyzed: dict[str, dict[str, Any]] = {}
        segment_bindings: dict[str, dict[str, Any]] = {}
        for segment in ("PRE", "LATE"):
            request = segments[segment]
            path = raw_root / str(request["filename"])
            if Path(str(request["filename"])).name != str(request["filename"]):
                raise Stage0Error(f"manifest DBN path escaped raw root: {request['request_id']}")
            validate_secure_path(
                path,
                expected=raw_root / str(request["filename"]),
                containment_root=raw_root,
                must_exist=True,
            )
            decoded, file_binding = decode_verified_snapshot(
                path,
                request,
                containment_root=raw_root,
                decoder=record_loader,
            )
            segment_bindings[segment] = file_binding
            if not isinstance(decoded, dict):
                raise Stage0Error(f"DBN decoder returned invalid payload: {request['request_id']}")
            verify_decoded_record_count(request, decoded)
            metadata_reasons = decoded_metadata_reason_codes(decoded, request)
            if request["source_empty"]:
                result = explicit_source_empty_segment(metadata_reasons)
            else:
                result = analyze_segment(
                    decoded["records"],
                    start_ns=parse_utc_ns(request["start"]),
                    end_ns=parse_utc_ns(request["end"]),
                    expected_instrument_id=decoded.get("expected_instrument_id"),
                    metadata_reason_codes=metadata_reasons,
                )
            analyzed[segment] = result
            raw_bindings.append(
                {
                    "request_id": request["request_id"],
                    "event_clock_id": request["event_clock_id"],
                    "segment": segment,
                    "filename": request["filename"],
                    "source_empty": request["source_empty"],
                    "bytes": file_binding["bytes"],
                    "sha256": file_binding["sha256"],
                    "_verified_identity": file_binding["identity"],
                    "records": request["records"],
                }
            )
        pair = evaluate_pair(analyzed["PRE"], analyzed["LATE"])
        all_reasons = [
            *analyzed["PRE"]["reason_codes"],
            *analyzed["LATE"]["reason_codes"],
        ]
        fatal_integrity = any(reason in FATAL_SEGMENT_REASONS for reason in all_reasons)
        pre = segments["PRE"]
        late = segments["LATE"]
        rows.append(
            {
                "event_clock_id": event_id,
                "event_time_utc": clock["event_time_utc"],
                "pre_request_id": pre["request_id"],
                "late_request_id": late["request_id"],
                "pre_start_utc": pre["start"],
                "pre_end_utc": pre["end"],
                "late_start_utc": late["start"],
                "late_end_utc": late["end"],
                "pre_filename": pre["filename"],
                "late_filename": late["filename"],
                "pre_source_empty": pre["source_empty"],
                "late_source_empty": late["source_empty"],
                "pre_record_count": analyzed["PRE"]["record_count"],
                "late_record_count": analyzed["LATE"]["record_count"],
                "pre_sha256": segment_bindings["PRE"]["sha256"],
                "late_sha256": segment_bindings["LATE"]["sha256"],
                "pre_segment_quality": analyzed["PRE"]["quality_pass"],
                "late_segment_quality": analyzed["LATE"]["quality_pass"],
                "pre_quality_reason_codes": analyzed["PRE"]["reason_codes"],
                "late_quality_reason_codes": analyzed["LATE"]["reason_codes"],
                "pair_quality_pass": pair["pair_quality_pass"],
                "pair_quality_reason_codes": pair["pair_reason_codes"],
                "i5_pre": pair["i5_pre"],
                "i5_late": pair["i5_late"],
                "delta_i5": pair["delta_i5"],
                "late_median_spread_ticks": pair["late_median_spread_ticks"],
                "feature_eligible": pair["feature_eligible"],
                "direction": pair["direction"],
                "fatal_source_integrity_failure": fatal_integrity,
            }
        )
    summary = summarize_population(rows)
    return rows, summary, sorted(raw_bindings, key=lambda item: item["request_id"])


def revalidate_raw_bindings(
    raw_root: Path,
    raw_bindings: Sequence[dict[str, Any]],
    *,
    _test_hook: Callable[[str, str, Path, Any], None] | None = None,
) -> None:
    for binding in raw_bindings:
        filename = str(binding.get("filename", ""))
        if not filename or Path(filename).name != filename:
            raise Stage0Error("raw binding contains an unsafe filename")
        path = raw_root / filename
        original_identity = binding.get("_verified_identity")
        if not isinstance(original_identity, (tuple, list)) or len(original_identity) != 2:
            raise Stage0Error(f"raw binding lacks verified identity: {filename}")
        _identity_bound_read(
            path,
            containment_root=raw_root,
            phase="final raw revalidation",
            original_identity=original_identity,
            expected_bytes=int(binding.get("bytes", -1)),
            expected_sha256=str(binding.get("sha256", "")),
            _test_hook=_test_hook,
        )


def render_readout(summary: dict[str, Any]) -> bytes:
    lines = [
        "# Stage 0B-D source readout — HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002",
        "",
        f"Verdict: `{summary['verdict']}`",
        "",
        "## Acquisition reconciliation",
        "",
        f"- Canonical event pairs: {summary['event_count']}/{EXPECTED_EVENTS}.",
        f"- Canonical request identities: {summary['event_count'] * 2}/{EXPECTED_REQUESTS}.",
        "- Every identity was reconciled to the frozen manifest, local DBN size/hash, record count and exact PRE/LATE bounds.",
        "",
        "## Source coverage and quality",
        "",
        f"- PRE nonempty: {summary['pre_nonempty_count']}/{EXPECTED_EVENTS} ({summary['pre_nonempty_coverage']:.6f}).",
        f"- LATE nonempty: {summary['late_nonempty_count']}/{EXPECTED_EVENTS} ({summary['late_nonempty_coverage']:.6f}).",
        f"- Paired nonempty: {summary['paired_nonempty_event_count']}/{EXPECTED_EVENTS} ({summary['paired_nonempty_event_coverage']:.6f}).",
        f"- Source-quality paired events: {summary['source_quality_paired_count']}.",
        f"- Source-quality failures among paired nonempty events: {summary['source_quality_failure_count']}.",
        f"- Sign/feature-eligible events: {summary['feature_eligible_count']}.",
        f"- Sign/feature-ineligible events after source quality: {summary['sign_feature_ineligible_count']}.",
        f"- Eligible cadence: {summary['feature_eligible_cadence_per_elapsed_week']:.6f} events per elapsed week over {ELAPSED_DESIGN_WEEKS} weeks.",
        "",
        "## Gate result",
        "",
    ]
    for name, gate in summary["gates"].items():
        lines.append(f"- {name}: {'PASS' if gate['pass'] else 'FAIL'}.")
    lines.extend(
        [
            "",
            "This is an outcome-blind source and feature-supply verdict only. It is not a market edge verdict, and no EURUSD outcome was opened.",
            "The source campaign remains bound to the Owner USD 3.50 ceiling and DEDDE7F2 authorization basis.",
            "Validation source remains sealed. Stage 1 requires a separate pre-outcome task packet and Lead Quant authority after independent review of this evidence.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _write_immutable(path: Path, payload: bytes, *, expected: Path) -> None:
    validate_secure_path(
        path,
        expected=expected,
        containment_root=WORKSPACE,
        must_exist=path.exists(),
    )
    if path.exists():
        if not path.is_file():
            raise Stage0Error(f"output path exists but is unsafe: {path}")
        if path.read_bytes() != payload:
            raise Stage0Error(f"immutable Stage0 output already exists with different bytes: {path}")
        return
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise Stage0Error(f"stale Stage0 temporary output exists: {temporary}")
    validate_secure_path(
        temporary,
        expected=temporary,
        containment_root=WORKSPACE,
        must_exist=False,
    )
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    validate_secure_path(
        path,
        expected=expected,
        containment_root=WORKSPACE,
        must_exist=False,
    )
    temporary.replace(path)


def run_stage0(
    *,
    run_authority: Path,
    expected_run_authority_sha256: str,
    data_root: Path = CANONICAL_DATA_ROOT,
    task_packet: Path = TASK_PACKET_PATH,
    prereg: Path = PREREG_PATH,
    clock_csv: Path = CLOCK_PATH,
    ledger_out: Path = LEDGER_PATH,
    manifest_out: Path = OUTPUT_MANIFEST_PATH,
    readout_out: Path = READOUT_PATH,
) -> dict[str, Any]:
    validate_exact_cli_paths(
        data_root=data_root,
        task_packet=task_packet,
        prereg=prereg,
        clock_csv=clock_csv,
        ledger_out=ledger_out,
        manifest_out=manifest_out,
        readout_out=readout_out,
    )
    authority_snapshot = validate_run_authority(
        run_authority,
        expected_run_authority_sha256,
    )
    bindings = verify_frozen_bindings()
    bindings["run_authority"] = {
        "path": _workspace_path(run_authority),
        "sha256": authority_snapshot["expected_sha256"],
        "reviewed_analyzer_sha256": authority_snapshot["payload"][
            "reviewed_analyzer_sha256"
        ],
        "reviewed_tests_sha256": authority_snapshot["payload"][
            "reviewed_tests_sha256"
        ],
    }
    clocks = load_design_clocks(clock_csv)
    manifest = _load_json(DOWNLOAD_MANIFEST_PATH)
    rows, summary, raw_bindings = analyze_snapshot(
        manifest=manifest,
        clocks=clocks,
        raw_root=data_root / "raw",
    )
    ledger_bytes = render_ledger(rows)
    output_manifest = build_output_manifest(
        bindings=bindings,
        raw_bindings=raw_bindings,
        summary=summary,
        analyzer_sha256=sha256_file(SOURCE_PATH),
        tests_sha256=sha256_file(TEST_PATH),
        ledger_sha256=sha256_bytes(ledger_bytes),
    )
    manifest_bytes = render_json(output_manifest)
    readout_bytes = render_readout(summary)
    revalidate_run_authority(authority_snapshot)
    rebound = verify_frozen_bindings()
    for key, value in rebound.items():
        if bindings.get(key) != value:
            raise Stage0Error(f"frozen binding changed before publication: {key}")
    revalidate_raw_bindings(data_root / "raw", raw_bindings)
    output_contracts = (
        (ledger_out, LEDGER_PATH),
        (manifest_out, OUTPUT_MANIFEST_PATH),
        (readout_out, READOUT_PATH),
    )
    for output, expected in output_contracts:
        validate_secure_path(
            output,
            expected=expected,
            containment_root=WORKSPACE,
            must_exist=output.exists(),
        )
    _write_immutable(ledger_out, ledger_bytes, expected=LEDGER_PATH)
    _write_immutable(manifest_out, manifest_bytes, expected=OUTPUT_MANIFEST_PATH)
    _write_immutable(readout_out, readout_bytes, expected=READOUT_PATH)
    return {
        "summary": summary,
        "ledger_sha256": sha256_bytes(ledger_bytes),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "readout_sha256": sha256_bytes(readout_bytes),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-authority", type=Path, required=True)
    parser.add_argument("--expected-run-authority-sha256", required=True)
    parser.add_argument("--data-root", type=Path, default=CANONICAL_DATA_ROOT)
    parser.add_argument("--task-packet", type=Path, default=TASK_PACKET_PATH)
    parser.add_argument("--prereg", type=Path, default=PREREG_PATH)
    parser.add_argument("--clock-csv", type=Path, default=CLOCK_PATH)
    parser.add_argument("--ledger-out", type=Path, default=LEDGER_PATH)
    parser.add_argument("--manifest-out", type=Path, default=OUTPUT_MANIFEST_PATH)
    parser.add_argument("--readout-out", type=Path, default=READOUT_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_stage0(
            run_authority=args.run_authority,
            expected_run_authority_sha256=args.expected_run_authority_sha256,
            data_root=args.data_root,
            task_packet=args.task_packet,
            prereg=args.prereg,
            clock_csv=args.clock_csv,
            ledger_out=args.ledger_out,
            manifest_out=args.manifest_out,
            readout_out=args.readout_out,
        )
    except Stage0Error as exc:
        print(f"EVENT_CLOB_STAGE0_BLOCKED reason={exc}", file=sys.stderr)
        return 2
    summary = result["summary"]
    print(
        "EVENT_CLOB_STAGE0 "
        f"verdict={summary['verdict']} events={summary['event_count']} "
        f"source_quality={summary['source_quality_paired_count']} "
        f"feature_eligible={summary['feature_eligible_count']} "
        f"cadence={summary['feature_eligible_cadence_per_elapsed_week']:.6f} "
        "network_calls=0 outcome_fields_used=false price_data_read=false"
    )
    return 0 if summary["stage0_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
