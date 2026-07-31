#!/usr/bin/env python3
"""Outcome-blind, import-inert source inventory for HYP-TRILAG-EURJPY-M1-001.

Importing this module and default CLI execution never open real HCC, MT5,
registry or evidence paths. A production attempt requires explicit
--production, an armed REVIEWED_REGISTRY_ROW_SHA256 sentinel matching the
LF-terminated latest registry row SHA, and a registry row that still authorizes
source_build + source_run. Only opaque path identity and streaming SHA-256 are
performed; no bar, price, residual, return, signal, trade, cost or outcome is
decoded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Mapping, Sequence


HYPOTHESIS_ID = "HYP-TRILAG-EURJPY-M1-001"
EA_NAME = "EA_TriangularConsensusLag"
FEATURE_FAMILY = "m1-triangular-parity-consensus-lag-source-inventory"
ATTEMPT_ID = "TRILAG001-SOURCE-001"

PLAN_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "HYP-TRILAG-EURJPY-M1-001_SOURCE_FEASIBILITY_PLAN.md"
)
PLAN_SHA256 = "A9ECD2AAD05265845800D82A50656BCD5933F4B921D1F6CBD056E683A69CD826"
BUILDER_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/build_trilag_001_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/tests/"
    "test_build_trilag_001_source.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "HYP-TRILAG-EURJPY-M1-001_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
    "HYP-TRILAG-EURJPY-M1-001_SOURCE_FEASIBILITY/"
    f"{ATTEMPT_ID}"
)
REQUIRED_STORAGE_DRIVE = "D:"

# Canonical D-side broker-history root (relative to workspace; no user path).
HISTORY_ROOT_REL = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/"
    "Bases/FivePercentOnline-Real/history"
)
PORTABLE_RUNTIME_MARKER = "02. AlphaFactory/runtime/mt5-portable-fivepercent"

BROKER_SYMBOLS: tuple[str, ...] = ("EURUSD", "USDJPY", "EURJPY")
DESIGN_YEARS: tuple[int, ...] = tuple(range(2016, 2025))  # 2016..2024 inclusive
RESEARCH_HOLDOUT_MIN_YEAR = 2025
EXPECTED_HCC_COUNT = len(BROKER_SYMBOLS) * len(DESIGN_YEARS)  # 27

# Reserved identity for a later child; never computed at source stage.
RESERVED_TRIANGULAR_IDENTITY: dict[str, object] = {
    "information_set": "completed_m1_spot_bars_only_later",
    "parity_identity": "log(EURJPY)=log(EURUSD)+log(USDJPY)",
    "lead_legs": ["EURUSD", "USDJPY"],
    "lag_execution_leg": "EURJPY",
    "execution_earliest": "next_observed_bar_or_tick_after_decision_close",
    "same_day_flat": True,
    "source_stage_computes_identity": False,
    "toxicity_future_path_label_forbidden": True,
    "no_generic_basket_or_pair_zscore": True,
}

# Independent review must replace this exact sentinel before any real read.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

HEX = frozenset("0123456789ABCDEF")
CHUNK_SIZE = 1024 * 1024

PASS_STATUS = "PASS_SOURCE_FEASIBILITY_FUTURE_CHILD_PREREG_ONLY"
FAIL_STATUS = "FAIL_SOURCE_FEASIBILITY_NO_ECONOMICS_AUTHORITY"
ENGINEERING_INVALID = "ENGINEERING_INVALID_NO_MARKET_VERDICT"
RECEIPT_NON_TERMINAL = "NON_TERMINAL_SOURCE_RESULT_AWAITING_ATTEMPT_TERMINAL"

OUTCOME_BLIND_COUNTERS: dict[str, object] = {
    "bars_read": 0,
    "timestamps_read": 0,
    "prices_read": 0,
    "residuals_computed": 0,
    "returns_computed": 0,
    "ranks_computed": 0,
    "signals_generated": 0,
    "trades_simulated": 0,
    "costs_computed": 0,
    "outcomes_opened": 0,
    "hcc_payloads_decoded": 0,
    "economics_executed": False,
    "performance_trials_executed": 0,
    "model0_runs": 0,
    "model4_runs": 0,
    "mt5_launches": 0,
    "mql5_files_created": 0,
    "network_calls": 0,
    "paid_requests_made": 0,
    "research_validation_opened": False,
    "research_holdout_opened": False,
    "source_feasibility_attempts_consumed": 0,
    "source_runs_executed": 0,
}


class ContractError(RuntimeError):
    """Fail-closed contract violation (engineering, not market no-edge)."""


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("non-canonical or non-finite JSON value") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("hash input must be bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in HEX for char in value)


def normalized_builder_base_sha256(payload: bytes) -> str:
    """Hash the reviewed disarmed builder even while its one-shot sentinel is armed."""

    if type(payload) is not bytes:
        raise ContractError("builder payload must be bytes")
    lines = payload.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("builder must contain exactly one valid registry-row sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def _is_reparse(info: os.stat_result) -> bool:
    return bool(int(getattr(info, "st_file_attributes", 0)) & 0x400)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        int(info.st_nlink),
        int(getattr(info, "st_file_attributes", 0)),
    )


def _os_fs_path(path: Path) -> str:
    text = str(Path(path).absolute())
    if os.name == "nt" and not text.startswith("\\\\?\\"):
        return "\\\\?\\" + text
    return text


def expected_hcc_relative_paths() -> tuple[str, ...]:
    """Exact 3 x 9 DESIGN paths; no parent enumeration; no holdout years."""

    paths: list[str] = []
    for symbol in BROKER_SYMBOLS:
        for year in DESIGN_YEARS:
            if year >= RESEARCH_HOLDOUT_MIN_YEAR:
                raise ContractError("holdout year leaked into DESIGN path construction")
            paths.append(f"{symbol}/{year}.hcc")
    if len(paths) != EXPECTED_HCC_COUNT:
        raise ContractError("expected HCC path count is not 27")
    return tuple(paths)


def expected_hcc_paths(history_root: Path) -> tuple[Path, ...]:
    root = Path(history_root)
    return tuple(root / relative for relative in expected_hcc_relative_paths())


def assert_path_contained(path: Path, root: Path, *, label: str) -> Path:
    """Fail-closed containment: resolved path must stay under root."""

    try:
        resolved_root = Path(root).resolve(strict=False)
        resolved_path = Path(path).resolve(strict=False)
    except OSError as exc:
        raise ContractError(f"{label} path resolve failed") from exc
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ContractError(f"{label} escapes allowed root") from exc
    # Reject explicit parent tokens in the unreolved relative form when under root.
    raw = Path(path)
    if any(part in {"", ".", ".."} for part in raw.parts if part not in {raw.anchor, raw.drive}):
        # Absolute paths may include drive; check only relative segments when possible.
        pass
    text = str(path).replace("\\", "/")
    if "/../" in f"/{text}/" or text.endswith("/..") or text.startswith("../"):
        raise ContractError(f"{label} contains path-escape segment")
    return resolved_path


def validate_portable_history_root(history_root: Path, workspace: Path) -> Path:
    """Require exact portable history path under workspace; real prod forces D: via workspace."""

    workspace = Path(workspace).resolve(strict=False)
    expected = (workspace / HISTORY_ROOT_REL).resolve(strict=False)
    root = Path(history_root).resolve(strict=False)
    if os.path.normcase(str(root)) != os.path.normcase(str(expected)):
        raise ContractError("history root is not the exact portable FivePercent history path")
    root_text = str(root)
    workspace_text = str(workspace)
    if os.name == "nt":
        root_drive = Path(root_text).drive.upper()
        workspace_drive = Path(workspace_text).drive.upper()
        if not root_drive or root_drive != workspace_drive:
            raise ContractError("history root drive must match workspace drive")
        if root_drive != REQUIRED_STORAGE_DRIVE.upper():
            raise ContractError("history root must live on drive D:")
    marker = PORTABLE_RUNTIME_MARKER.replace("/", os.sep)
    normalized_root = root_text.replace("/", os.sep).lower()
    if marker.lower() not in normalized_root:
        raise ContractError("history root is not under portable AlphaFactory runtime")
    assert_path_contained(root, workspace, label="history root")
    return root

def _reject_symlink_or_reparse(path: Path, info: os.stat_result, *, label: str) -> None:
    if path.is_symlink() or _is_reparse(info):
        raise ContractError(f"{label} is symlink/reparse-like and rejected")


def hash_opaque_stable(path: Path, *, allowed_root: Path | None = None) -> dict[str, object]:
    """Stream opaque bytes into SHA-256 with before/after identity stability.

    Does not decode, parse or retain file content. Rejects missing, empty,
    non-regular and symlink/reparse-like sources. Optional root containment.
    """

    path = Path(path)
    if allowed_root is not None:
        assert_path_contained(path, allowed_root, label=path.name)

    try:
        before = os.lstat(path)
    except FileNotFoundError as exc:
        raise ContractError(f"source missing: {path.name}") from exc
    except OSError as exc:
        raise ContractError(f"source unreadable: {path.name}") from exc

    _reject_symlink_or_reparse(path, before, label=path.name)
    if not stat.S_ISREG(before.st_mode):
        raise ContractError(f"source is not a regular file: {path.name}")
    if int(before.st_size) <= 0:
        raise ContractError(f"source is empty: {path.name}")

    pinned = _identity(before)
    digest = hashlib.sha256()
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    fs_path = _os_fs_path(path)
    try:
        descriptor = os.open(fs_path, flags)
    except OSError as exc:
        raise ContractError(f"source open failed: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != pinned:
            raise ContractError(f"source identity changed before read: {path.name}")
        while True:
            chunk = os.read(descriptor, CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    try:
        after = os.lstat(path)
    except OSError as exc:
        raise ContractError(f"source vanished after hash: {path.name}") from exc

    if (
        _identity(final) != pinned
        or _identity(after) != pinned
        or path.is_symlink()
        or _is_reparse(after)
        or not stat.S_ISREG(after.st_mode)
    ):
        raise ContractError(f"source unstable across hash: {path.name}")

    sha = digest.hexdigest().upper()
    if not _valid_sha(sha):
        raise ContractError(f"invalid SHA-256 for {path.name}")
    return {
        "path": str(path).replace("\\", "/"),
        "name": path.name,
        "size_bytes": int(pinned[2]),
        "mtime_ns": int(pinned[3]),
        "sha256": sha,
        "stable": True,
        "regular_file": True,
        "symlink_or_reparse": False,
        "empty": False,
    }


def build_source_inventory(*, history_root: Path) -> dict[str, object]:
    """Hash exact DESIGN 27-file HCC set; no symbol cache; outcome counters zero."""

    history_root = Path(history_root)
    hcc_paths = expected_hcc_paths(history_root)
    allowed_relative = set(expected_hcc_relative_paths())

    for path in hcc_paths:
        name = path.name
        if path.stem.isdigit() and int(path.stem) >= RESEARCH_HOLDOUT_MIN_YEAR:
            raise ContractError("holdout HCC path constructed")
        symbol = path.parent.name
        if symbol not in BROKER_SYMBOLS:
            raise ContractError(f"unexpected broker symbol in path set: {symbol}")
        year_token = path.stem
        if not year_token.isdigit() or int(year_token) not in DESIGN_YEARS:
            raise ContractError(f"unexpected year in path set: {path.name}")
        relative = f"{symbol}/{path.name}"
        if relative not in allowed_relative:
            raise ContractError(f"path not in exact allowed set: {relative}")
        assert_path_contained(path, history_root, label=relative)

    hcc_records: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    for path in hcc_paths:
        record = hash_opaque_stable(path, allowed_root=history_root)
        try:
            relative = path.relative_to(Path(history_root)).as_posix()
        except ValueError:
            relative = path.name
        if relative in seen_paths:
            raise ContractError(f"duplicate inventory path: {relative}")
        seen_paths.add(relative)
        if relative not in allowed_relative:
            raise ContractError(f"inventoried path outside exact set: {relative}")
        record["relative_path"] = relative
        record["broker_symbol"] = path.parent.name
        record["year"] = int(path.stem)
        hcc_records.append(record)

    if len(hcc_records) != EXPECTED_HCC_COUNT:
        raise ContractError("HCC inventory count is not 27")
    if len(seen_paths) != EXPECTED_HCC_COUNT:
        raise ContractError("duplicate path detected in inventory")

    years_by_symbol: dict[str, list[int]] = {symbol: [] for symbol in BROKER_SYMBOLS}
    for record in hcc_records:
        symbol = str(record["broker_symbol"])
        if symbol not in years_by_symbol:
            raise ContractError(f"unexpected symbol in inventory: {symbol}")
        years_by_symbol[symbol].append(int(record["year"]))
    for symbol, years in years_by_symbol.items():
        if sorted(years) != list(DESIGN_YEARS):
            raise ContractError(f"symbol {symbol} missing exact DESIGN year intersection")
        if len(years) != len(set(years)):
            raise ContractError(f"symbol {symbol} has duplicate years")

    inventory_body = {
        "schema_version": "trilag_001_source_inventory.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "feature_family": FEATURE_FAMILY,
        "ea_name": EA_NAME,
        "broker_symbols": list(BROKER_SYMBOLS),
        "design_years": list(DESIGN_YEARS),
        "research_holdout_payload_min_year": RESEARCH_HOLDOUT_MIN_YEAR,
        "expected_design_hcc_files": EXPECTED_HCC_COUNT,
        "observed_design_hcc_files": len(hcc_records),
        "symbol_cache_files": [],
        "symbol_cache_required": False,
        "reserved_triangular_identity": dict(RESERVED_TRIANGULAR_IDENTITY),
        "hcc_files": hcc_records,
        "outcome_blind_counters": dict(OUTCOME_BLIND_COUNTERS),
        "parent_directory_enumeration": False,
        "holdout_enumeration": False,
        "hcc_decode": False,
        "metatrader5_import": False,
    }
    inventory_sha = sha256_bytes(canonical_json(inventory_body))
    return {
        **inventory_body,
        "inventory_sha256": inventory_sha,
    }


def evaluate_inventory_gates(inventory: Mapping[str, object]) -> dict[str, object]:
    gates = {
        "exact_27_design_hcc_present_stable": (
            inventory.get("observed_design_hcc_files") == EXPECTED_HCC_COUNT
            and type(inventory.get("hcc_files")) is list
            and len(inventory["hcc_files"]) == EXPECTED_HCC_COUNT  # type: ignore[index]
            and all(
                type(row) is dict and row.get("stable") is True and _valid_sha(row.get("sha256"))
                for row in inventory["hcc_files"]  # type: ignore[index]
            )
        ),
        "common_year_intersection_2016_2024": (
            inventory.get("design_years") == list(DESIGN_YEARS)
            and inventory.get("broker_symbols") == list(BROKER_SYMBOLS)
        ),
        "no_symbol_cache_contract": (
            inventory.get("symbol_cache_required") is False
            and inventory.get("symbol_cache_files") == []
        ),
        "reserved_identity_not_computed": (
            type(inventory.get("reserved_triangular_identity")) is dict
            and inventory["reserved_triangular_identity"].get(  # type: ignore[index]
                "source_stage_computes_identity"
            )
            is False
        ),
        "outcome_blind_counters_hard_zero": inventory.get("outcome_blind_counters")
        == OUTCOME_BLIND_COUNTERS,
        "no_holdout_access": inventory.get("holdout_enumeration") is False
        and inventory.get("research_holdout_payload_min_year")
        == RESEARCH_HOLDOUT_MIN_YEAR,
        "no_hcc_decode": inventory.get("hcc_decode") is False,
        "no_metatrader5_import": inventory.get("metatrader5_import") is False,
    }
    passed = all(bool(value) is True for value in gates.values())
    return {
        "gates": gates,
        "all_passed": passed,
        "status": PASS_STATUS if passed else FAIL_STATUS,
    }


def parse_registry_jsonl(payload: bytes) -> tuple[list[dict[str, object]], list[bytes]]:
    try:
        if type(payload) is not bytes or not payload:
            raise ValueError("empty registry")
        raw_rows = payload.splitlines(keepends=True)
        rows: list[dict[str, object]] = []
        for line_number, record in enumerate(raw_rows, start=1):
            if (
                not record.endswith(b"\n")
                or record.endswith(b"\r\n")
                or record.count(b"\n") != 1
            ):
                raise ValueError(f"line {line_number}: exact terminal LF required")
            encoding = "utf-8-sig" if line_number == 1 else "utf-8"
            raw = record[:-1].decode(encoding, errors="strict")
            if not raw.strip():
                raise ValueError(f"line {line_number}: blank registry row")
            value = json.loads(raw)
            if type(value) is not dict:
                raise ValueError(f"line {line_number}: registry row root is not an object")
            rows.append(value)
        return rows, raw_rows
    except Exception as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid strict registry JSONL") from exc


def validate_production_registry_authority(
    registry_payload: bytes,
    reviewed_row_sha256: str,
) -> dict[str, object]:
    if not _valid_sha(reviewed_row_sha256):
        raise ContractError("reviewed registry-row sentinel is invalid")
    rows, raw_rows = parse_registry_jsonl(registry_payload)
    if not rows or not raw_rows:
        raise ContractError("registry is empty")
    # Detect blank/duplicate raw rows among LF-terminated records.
    seen_raw: set[bytes] = set()
    for raw in raw_rows:
        if raw in seen_raw:
            raise ContractError("duplicate registry row payload")
        seen_raw.add(raw)
    latest_raw = raw_rows[-1]
    latest_row = rows[-1]
    latest_sha = sha256_bytes(latest_raw)
    if latest_sha != reviewed_row_sha256:
        raise ContractError(
            "reviewed registry-row sentinel does not match LF-terminated latest row SHA"
        )
    validation = latest_row.get("validation")
    if type(validation) is not dict:
        raise ContractError("latest registry row missing validation object")
    if (
        latest_row.get("hypothesis_id") != HYPOTHESIS_ID
        or latest_row.get("state") != "probe"
        or latest_row.get("ea_name") != EA_NAME
        or latest_row.get("prereg_sha256") != PLAN_SHA256
        or latest_row.get("prereg_path") != PLAN_REL
        or validation.get("source_build_authorized") is not True
        or validation.get("source_run_authorized") is not True
    ):
        raise ContractError(
            "latest registry row is not HYP-TRILAG-EURJPY-M1-001 probe with "
            "source_build_authorized=true and source_run_authorized=true "
            "and matching prereg SHA"
        )
    required_bindings = {
        "reviewed_builder_path": BUILDER_REL,
        "reviewed_test_path": TEST_REL,
        "independent_review_receipt_path": REVIEW_RECEIPT_REL,
    }
    for field, expected in required_bindings.items():
        if validation.get(field) != expected:
            raise ContractError(f"latest registry row has wrong {field}")
    for field in (
        "reviewed_builder_base_sha256",
        "reviewed_test_sha256",
        "independent_review_receipt_sha256",
    ):
        if not _valid_sha(validation.get(field)):
            raise ContractError(f"latest registry row has invalid {field}")
    return latest_row


def _write_new_bytes(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes:
        raise ContractError("artifact payload must be bytes")
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ContractError(f"artifact already exists: {path.name}")
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{os.urandom(8).hex()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0))
    try:
        descriptor = os.open(_os_fs_path(temp), flags, 0o600)
        try:
            offset = 0
            while offset < len(payload):
                written = os.write(descriptor, payload[offset:])
                if written <= 0:
                    raise OSError("short artifact write")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        temp_fs = _os_fs_path(temp)
        path_fs = _os_fs_path(path)
        temp_info = os.lstat(temp_fs)
        if (
            not stat.S_ISREG(temp_info.st_mode)
            or os.path.islink(temp_fs)
            or _is_reparse(temp_info)
            or int(temp_info.st_nlink) != 1
            or int(temp_info.st_size) != len(payload)
        ):
            raise OSError("artifact identity mismatch")
        os.link(temp_fs, path_fs)
        os.unlink(temp_fs)
        info = os.lstat(path_fs)
        if (
            not stat.S_ISREG(info.st_mode)
            or os.path.islink(path_fs)
            or _is_reparse(info)
            or int(info.st_nlink) != 1
            or int(info.st_size) != len(payload)
        ):
            raise OSError("published artifact identity mismatch")
    except Exception as exc:
        try:
            temp_fs = _os_fs_path(temp)
            if os.path.lexists(temp_fs):
                os.unlink(temp_fs)
        except OSError:
            pass
        raise ContractError(f"exclusive artifact write failed: {path.name}") from exc


def _write_new_canonical(path: Path, value: object) -> None:
    _write_new_bytes(path, canonical_json(value) + b"\n")


def _mkdir_parents(path: Path) -> None:
    current = Path(path).absolute()
    parts = current.parts
    if os.name == "nt" and len(parts[0]) == 2 and parts[0][1] == ":":
        acc = Path(parts[0] + os.sep)
        start = 1
    else:
        acc = Path(parts[0])
        start = 1
    for component in parts[start:]:
        acc = acc / component
        try:
            os.mkdir(acc)
        except FileExistsError:
            info = os.lstat(acc)
            if not stat.S_ISDIR(info.st_mode) or Path(acc).is_symlink() or _is_reparse(info):
                raise ContractError(f"path component is not a private directory: {acc}")
            continue
        info = os.lstat(acc)
        if not stat.S_ISDIR(info.st_mode) or Path(acc).is_symlink() or _is_reparse(info):
            raise ContractError(f"path component mkdir failed: {acc}")


def reserve_evidence_root(workspace: Path) -> Path:
    workspace = Path(workspace).absolute()
    relative = Path(EVIDENCE_ROOT_REL)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ContractError("invalid evidence-root contract")
    root = workspace / relative
    if root.exists():
        raise ContractError(
            "attempt evidence root already exists; one-use reservation rejected"
        )
    parent = root.parent
    if not parent.exists():
        _mkdir_parents(parent)
    try:
        os.mkdir(root)
    except FileExistsError as exc:
        raise ContractError(
            "attempt evidence root already exists; one-use reservation rejected"
        ) from exc
    info = os.lstat(root)
    if not stat.S_ISDIR(info.st_mode) or root.is_symlink() or _is_reparse(info):
        raise ContractError("attempt evidence root reservation failed")
    return root


def _read_file_bytes(path: Path) -> bytes:
    path = Path(path)
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise ContractError(f"required file missing or unreadable: {path.name}") from exc
    if not stat.S_ISREG(before.st_mode) or path.is_symlink() or _is_reparse(before):
        raise ContractError(f"refusing non-regular read: {path.name}")
    pinned = _identity(before)
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(_os_fs_path(path), flags)
    except OSError as exc:
        raise ContractError(f"required file open failed: {path.name}") from exc
    try:
        if _identity(os.fstat(descriptor)) != pinned:
            raise ContractError(f"identity changed before read: {path.name}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after = os.lstat(path)
    except OSError as exc:
        raise ContractError(f"required file vanished: {path.name}") from exc
    if _identity(final) != pinned or _identity(after) != pinned:
        raise ContractError(f"unstable read: {path.name}")
    payload = b"".join(chunks)
    if len(payload) != int(before.st_size):
        raise ContractError(f"short read: {path.name}")
    return payload


def run_production(
    *,
    workspace_root: Path,
    production: bool,
) -> dict[str, object]:
    """Fail-closed production inventory. Requires explicit production flag + gates."""

    if production is not True:
        raise ContractError(
            "production source inventory is disarmed; explicit --production is required"
        )
    if REVIEWED_REGISTRY_ROW_SHA256 is None:
        raise ContractError(
            "production source inventory is disarmed; reviewed registry-row sentinel is absent"
        )
    if not _valid_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("reviewed registry-row sentinel is invalid")

    workspace = Path(workspace_root).resolve(strict=True)
    if os.name == "nt" and Path(str(workspace)).drive.upper() != REQUIRED_STORAGE_DRIVE.upper():
        raise ContractError("production workspace must live on the required D: drive")

    reg_path = workspace / REGISTRY_REL
    registry_payload = _read_file_bytes(reg_path)
    authority = validate_production_registry_authority(
        registry_payload, REVIEWED_REGISTRY_ROW_SHA256
    )
    validation = authority["validation"]
    if type(validation) is not dict:
        raise ContractError("latest registry row missing validation bindings")

    plan_path = workspace / PLAN_REL
    plan_payload = _read_file_bytes(plan_path)
    if sha256_bytes(plan_payload) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")

    builder_path = workspace / BUILDER_REL
    test_path = workspace / TEST_REL
    review_receipt_path = workspace / REVIEW_RECEIPT_REL
    builder_payload = _read_file_bytes(builder_path)
    builder_sha = sha256_bytes(builder_payload)
    builder_base_sha = normalized_builder_base_sha256(builder_payload)
    test_sha = sha256_bytes(_read_file_bytes(test_path))
    review_receipt_sha = sha256_bytes(_read_file_bytes(review_receipt_path))
    if builder_base_sha != validation.get("reviewed_builder_base_sha256"):
        raise ContractError("reviewed disarmed builder SHA mismatch")
    if test_sha != validation.get("reviewed_test_sha256"):
        raise ContractError("reviewed test SHA mismatch")
    if review_receipt_sha != validation.get("independent_review_receipt_sha256"):
        raise ContractError("independent review receipt SHA mismatch")

    hist = workspace / HISTORY_ROOT_REL
    hist = validate_portable_history_root(hist, workspace)
    evidence_root = reserve_evidence_root(workspace)

    started = {
        "schema_version": "trilag_001_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
        "status": "STARTED",
        "evidence_root": EVIDENCE_ROOT_REL,
        "outcome_blind_counters": dict(OUTCOME_BLIND_COUNTERS),
        "builder_sha256_runtime": builder_sha,
        "reviewed_builder_base_sha256": builder_base_sha,
        "test_sha256_runtime": test_sha,
        "independent_review_receipt_sha256": review_receipt_sha,
    }
    try:
        _write_new_canonical(evidence_root / "attempt_started.json", started)
        started_sha = sha256_bytes(canonical_json(started) + b"\n")

        inventory = build_source_inventory(history_root=hist)
        inventory_doc = {
            **inventory,
            "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
            "attempt_started_sha256": started_sha,
        }
        _write_new_canonical(evidence_root / "source_inventory.json", inventory_doc)
        inventory_file_sha = sha256_bytes(canonical_json(inventory_doc) + b"\n")

        gate_result = evaluate_inventory_gates(inventory)
        receipt = {
            "schema_version": "trilag_001_source_feasibility_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
            "attempt_started_sha256": started_sha,
            "source_inventory_sha256": inventory_file_sha,
            "inventory_body_sha256": inventory.get("inventory_sha256"),
            "gate_result": gate_result,
            "status": RECEIPT_NON_TERMINAL,
            "terminal_is_sole_authoritative_completion": True,
            "outcome_blind_counters": dict(OUTCOME_BLIND_COUNTERS),
            "economics_authorized": False,
            "promotion_authorized": False,
            "live_trading_authorized": False,
        }
        if receipt.get("status") == PASS_STATUS:
            raise ContractError("receipt must never claim authoritative PASS")
        _write_new_canonical(evidence_root / "source_feasibility_receipt.json", receipt)
        receipt_sha = sha256_bytes(canonical_json(receipt) + b"\n")

        if gate_result["all_passed"]:
            terminal_status = PASS_STATUS
        else:
            terminal_status = FAIL_STATUS

        terminal = {
            "schema_version": "trilag_001_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
            "attempt_started_sha256": started_sha,
            "source_inventory_sha256": inventory_file_sha,
            "source_feasibility_receipt_sha256": receipt_sha,
            "status": terminal_status,
            "terminal_is_sole_authoritative_completion": True,
            "gate_result": gate_result,
            "outcome_blind_counters": {
                **OUTCOME_BLIND_COUNTERS,
                "source_feasibility_attempts_consumed": 1,
                "source_runs_executed": 1,
            },
            "market_verdict": None,
            "no_edge_claim": False,
            "engineering_only": terminal_status != PASS_STATUS,
        }
        _write_new_canonical(evidence_root / "attempt_terminal.json", terminal)
        return terminal
    except Exception as exc:
        failure = {
            "schema_version": "trilag_001_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
            "status": ENGINEERING_INVALID,
            "terminal_is_sole_authoritative_completion": True,
            "error": f"{type(exc).__name__}: {exc}",
            "outcome_blind_counters": {
                **OUTCOME_BLIND_COUNTERS,
                "source_feasibility_attempts_consumed": 1,
                "source_runs_executed": 1,
            },
            "market_verdict": None,
            "no_edge_claim": False,
            "engineering_only": True,
        }
        terminal_path = evidence_root / "attempt_terminal.json"
        if not terminal_path.exists():
            try:
                _write_new_canonical(terminal_path, failure)
            except Exception:
                pass
        if isinstance(exc, ContractError):
            raise
        raise ContractError(f"production inventory failed: {exc}") from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--production",
        action="store_true",
        help="Explicit arm for the single real source-inventory attempt.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_production(
        workspace_root=args.workspace_root,
        production=bool(args.production),
    )
    sys.stdout.write(canonical_json(report).decode("utf-8") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
