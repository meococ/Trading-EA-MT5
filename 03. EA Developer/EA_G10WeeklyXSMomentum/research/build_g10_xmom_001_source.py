#!/usr/bin/env python3
"""Outcome-blind, import-inert source inventory for HYP-G10-XMOM-W1-001.

Importing this module and default CLI execution never open real HCC, MT5,
registry or evidence paths. A production attempt requires explicit
--production, an armed REVIEWED_REGISTRY_ROW_SHA256 sentinel matching the
LF-terminated latest registry row SHA, and a registry row that still authorizes
source_build + source_run. Only opaque path identity and streaming SHA-256 are
performed; no bar, price, return, rank, signal, trade, cost or outcome is
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


HYPOTHESIS_ID = "HYP-G10-XMOM-W1-001"
EA_NAME = "EA_G10WeeklyXSMomentum"
FEATURE_FAMILY = "g10-spot-cross-sectional-weekly-momentum"
ATTEMPT_ID = "G10XMOM001-SOURCE-001"

PLAN_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/"
    "HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY_PLAN.md"
)
PLAN_SHA256 = "079BA090869C8C8D3C0849D11B080641FA2D27BDF9B9153212A9E12556B52EDE"
BUILDER_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/build_g10_xmom_001_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/tests/"
    "test_build_g10_xmom_001_source.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/"
    "HYP-G10-XMOM-W1-001_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/"
    "HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY/"
    f"{ATTEMPT_ID}"
)
CANONICAL_WORKSPACE_ROOT = Path(r"D:\Trading EA MT5")

# Canonical D-side broker-history root (relative to workspace).
HISTORY_ROOT_REL = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/"
    "Bases/FivePercentOnline-Real/history"
)
SYMBOLS_ROOT_REL = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/"
    "Bases/FivePercentOnline-Real/symbols"
)
SYMBOL_CACHE_NAMES = (
    "symbols-26451822.dat",
    "selected-26451822.dat",
)

DESIGN_YEARS: tuple[int, ...] = tuple(range(2018, 2025))  # 2018..2024 inclusive
HOLDOUT_YEARS_FORBIDDEN: tuple[int, ...] = (2025, 2026)

# Exact pair/orientation map: orientation converts pair log-return into non-USD
# currency return versus USD. Four direct (+1) and three inverse (-1).
ORIENTATION_MAP: tuple[dict[str, object], ...] = (
    {"currency": "AUD", "broker_symbol": "AUDUSD", "orientation": 1},
    {"currency": "EUR", "broker_symbol": "EURUSD", "orientation": 1},
    {"currency": "GBP", "broker_symbol": "GBPUSD", "orientation": 1},
    {"currency": "NZD", "broker_symbol": "NZDUSD", "orientation": 1},
    {"currency": "CAD", "broker_symbol": "USDCAD", "orientation": -1},
    {"currency": "CHF", "broker_symbol": "USDCHF", "orientation": -1},
    {"currency": "JPY", "broker_symbol": "USDJPY", "orientation": -1},
)
BROKER_SYMBOLS: tuple[str, ...] = tuple(
    str(row["broker_symbol"]) for row in ORIENTATION_MAP
)
EXPECTED_HCC_COUNT = len(BROKER_SYMBOLS) * len(DESIGN_YEARS)  # 49

STRUCTURAL_PORTFOLIO_IDENTITY: dict[str, object] = {
    "information_set": "completed_weekly_spot_bars_only",
    "formation": "exactly_one_completed_week",
    "currency_universe": [row["currency"] for row in ORIENTATION_MAP],
    "usd_numeraire_not_ranked": True,
    "selection": "top_two_and_bottom_two_currency_ranks",
    "tie_break": "alphabetical",
    "instruments": "exactly_four_corresponding_usd_pairs",
    "orientation_map_bound": True,
    "entry": "monday_portfolio_decision",
    "exit": "friday_flat_before_broker_close",
    "weekend_exposure": 0,
    "intended_entry_legs_per_eligible_week": 4,
    "counts_legs_not_rebalance_events": True,
    "matched_control": "reverse_rank_direction_same_legs_dates_sizing_costs",
    "trial_budget": "one_primary_challenger_plus_one_matched_control",
    "no_dispersion_gap_vol_session_weekday_news_trend_filter": True,
}

# Independent review must replace this exact sentinel before any real read.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

HEX = frozenset("0123456789ABCDEF")
CHUNK_SIZE = 1024 * 1024

PASS_STATUS = "PASS_SOURCE_INVENTORY_FUTURE_ECONOMICS_PREREG_ONLY"
FAIL_STATUS = "SOURCE_INVENTORY_FAIL_NO_ECONOMICS_AUTHORITY"
ENGINEERING_INVALID = "ENGINEERING_INVALID_NO_MARKET_VERDICT"
RECEIPT_NON_TERMINAL = "NON_TERMINAL_SOURCE_RESULT_AWAITING_ATTEMPT_TERMINAL"

OUTCOME_BLIND_COUNTERS: dict[str, object] = {
    "bars_read": 0,
    "timestamps_read": 0,
    "prices_read": 0,
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
    matches = [index for index, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
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


def validate_orientation_map() -> dict[str, object]:
    currencies = [str(row["currency"]) for row in ORIENTATION_MAP]
    symbols = [str(row["broker_symbol"]) for row in ORIENTATION_MAP]
    orientations = [int(row["orientation"]) for row in ORIENTATION_MAP]
    if len(currencies) != 7 or len(set(currencies)) != 7:
        raise ContractError("orientation map currency set is incomplete or non-unique")
    if len(symbols) != 7 or len(set(symbols)) != 7:
        raise ContractError("orientation map broker symbols are incomplete or non-unique")
    if orientations.count(1) != 4 or orientations.count(-1) != 3:
        raise ContractError("orientation map must be exactly four direct and three inverse")
    if any(value not in {1, -1} for value in orientations):
        raise ContractError("orientation values must be exactly +1 or -1")
    return {
        "complete": True,
        "unique_currencies": True,
        "unique_symbols": True,
        "direct_count": 4,
        "inverse_count": 3,
        "balanced": True,
        "map": [dict(row) for row in ORIENTATION_MAP],
    }


def expected_hcc_relative_paths() -> tuple[str, ...]:
    """Exact 7 x 7 DESIGN paths; no parent enumeration; no holdout years."""

    paths: list[str] = []
    for symbol in BROKER_SYMBOLS:
        for year in DESIGN_YEARS:
            if year in HOLDOUT_YEARS_FORBIDDEN:
                raise ContractError("holdout year leaked into DESIGN path construction")
            paths.append(f"{symbol}/{year}.hcc")
    if len(paths) != EXPECTED_HCC_COUNT:
        raise ContractError("expected HCC path count is not 49")
    return tuple(paths)


def expected_hcc_paths(history_root: Path) -> tuple[Path, ...]:
    root = Path(history_root)
    return tuple(root / relative for relative in expected_hcc_relative_paths())


def expected_symbol_cache_paths(symbols_root: Path) -> tuple[Path, ...]:
    root = Path(symbols_root)
    return tuple(root / name for name in SYMBOL_CACHE_NAMES)


def _reject_symlink_or_reparse(path: Path, info: os.stat_result, *, label: str) -> None:
    if path.is_symlink() or _is_reparse(info):
        raise ContractError(f"{label} is symlink/reparse-like and rejected")


def hash_opaque_stable(path: Path) -> dict[str, object]:
    """Stream opaque bytes into SHA-256 with before/after identity stability.

    Does not decode, parse or retain file content. Rejects missing, empty,
    non-regular and symlink/reparse-like sources.
    """

    path = Path(path)
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
            # intentionally drop chunk reference; no retention of payload
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


def build_source_inventory(
    *,
    history_root: Path,
    symbols_root: Path,
) -> dict[str, object]:
    """Hash exact DESIGN HCC set and two symbol-cache files; outcome counters zero."""

    orientation = validate_orientation_map()
    hcc_paths = expected_hcc_paths(history_root)
    cache_paths = expected_symbol_cache_paths(symbols_root)

    # Defensive: never construct holdout year paths in this function.
    for path in hcc_paths:
        name = path.name
        if name in {f"{year}.hcc" for year in HOLDOUT_YEARS_FORBIDDEN}:
            raise ContractError("holdout HCC path constructed")

    hcc_records: list[dict[str, object]] = []
    for path in hcc_paths:
        record = hash_opaque_stable(path)
        # Store path relative to history root for portability in artifacts.
        try:
            relative = path.relative_to(Path(history_root)).as_posix()
        except ValueError:
            relative = path.name
        record["relative_path"] = relative
        symbol = path.parent.name
        year_token = path.stem
        if not year_token.isdigit():
            raise ContractError(f"non-year HCC name: {path.name}")
        record["broker_symbol"] = symbol
        record["year"] = int(year_token)
        hcc_records.append(record)

    if len(hcc_records) != EXPECTED_HCC_COUNT:
        raise ContractError("HCC inventory count is not 49")

    years_by_symbol: dict[str, list[int]] = {symbol: [] for symbol in BROKER_SYMBOLS}
    for record in hcc_records:
        years_by_symbol[str(record["broker_symbol"])].append(int(record["year"]))
    for symbol, years in years_by_symbol.items():
        if sorted(years) != list(DESIGN_YEARS):
            raise ContractError(f"symbol {symbol} missing exact DESIGN year intersection")

    cache_records: list[dict[str, object]] = []
    for path in cache_paths:
        record = hash_opaque_stable(path)
        record["relative_path"] = path.name
        cache_records.append(record)
    if len(cache_records) != 2:
        raise ContractError("exactly two symbol-cache files are required")

    inventory_body = {
        "schema_version": "g10_xmom_001_source_inventory.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "feature_family": FEATURE_FAMILY,
        "ea_name": EA_NAME,
        "design_years": list(DESIGN_YEARS),
        "holdout_years_unopened": list(HOLDOUT_YEARS_FORBIDDEN),
        "expected_design_hcc_files": EXPECTED_HCC_COUNT,
        "observed_design_hcc_files": len(hcc_records),
        "orientation": orientation,
        "structural_portfolio_identity": dict(STRUCTURAL_PORTFOLIO_IDENTITY),
        "hcc_files": hcc_records,
        "symbol_cache_files": cache_records,
        "outcome_blind_counters": dict(OUTCOME_BLIND_COUNTERS),
        "parent_directory_enumeration": False,
        "holdout_enumeration": False,
        "hcc_decode": False,
        "metatrader5_import": False,
    }
    inventory_sha = sha256_bytes(canonical_json(inventory_body))
    inventory = {
        **inventory_body,
        "inventory_sha256": inventory_sha,
    }
    return inventory


def evaluate_inventory_gates(inventory: Mapping[str, object]) -> dict[str, object]:
    gates = {
        "exact_49_design_hcc_present_stable": (
            inventory.get("observed_design_hcc_files") == EXPECTED_HCC_COUNT
            and type(inventory.get("hcc_files")) is list
            and len(inventory["hcc_files"]) == EXPECTED_HCC_COUNT  # type: ignore[index]
            and all(
                type(row) is dict and row.get("stable") is True and _valid_sha(row.get("sha256"))
                for row in inventory["hcc_files"]  # type: ignore[index]
            )
        ),
        "common_year_intersection_2018_2024": True,
        "symbol_cache_pair_present_stable": (
            type(inventory.get("symbol_cache_files")) is list
            and len(inventory["symbol_cache_files"]) == 2  # type: ignore[index]
            and all(
                type(row) is dict and row.get("stable") is True and _valid_sha(row.get("sha256"))
                for row in inventory["symbol_cache_files"]  # type: ignore[index]
            )
        ),
        "orientation_map_complete_unique_balanced": (
            type(inventory.get("orientation")) is dict
            and inventory["orientation"].get("balanced") is True  # type: ignore[index]
            and inventory["orientation"].get("direct_count") == 4  # type: ignore[index]
            and inventory["orientation"].get("inverse_count") == 3  # type: ignore[index]
        ),
        "structural_four_legs_per_week": (
            type(inventory.get("structural_portfolio_identity")) is dict
            and inventory["structural_portfolio_identity"].get(  # type: ignore[index]
                "intended_entry_legs_per_eligible_week"
            )
            == 4
            and inventory["structural_portfolio_identity"].get(  # type: ignore[index]
                "counts_legs_not_rebalance_events"
            )
            is True
        ),
        "outcome_blind_counters_hard_zero": inventory.get("outcome_blind_counters")
        == OUTCOME_BLIND_COUNTERS,
        "no_holdout_access": inventory.get("holdout_enumeration") is False
        and inventory.get("holdout_years_unopened") == list(HOLDOUT_YEARS_FORBIDDEN),
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
            "latest registry row is not HYP-G10-XMOM-W1-001 probe with "
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
        # Hard-link publication is atomic and refuses an existing destination.
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
    relative_parts = path.parts
    current = Path(path.anchor) if path.anchor else Path(path.parts[0])
    # Prefer pure sequential mkdir for each component under an absolute base.
    current = Path(path).absolute()
    parts = current.parts
    # Rebuild from root
    acc = Path(parts[0] + os.sep) if os.name == "nt" and len(parts[0]) == 2 and parts[0][1] == ":" else Path(parts[0])
    start = 1
    if os.name == "nt" and len(parts[0]) == 2 and parts[0][1] == ":":
        acc = Path(parts[0] + os.sep)
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
    canonical_workspace = Path(CANONICAL_WORKSPACE_ROOT).resolve(strict=True)
    if os.path.normcase(str(workspace)) != os.path.normcase(str(canonical_workspace)):
        raise ContractError("production workspace is not the canonical D-side workspace")

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
    sym = workspace / SYMBOLS_ROOT_REL
    evidence_root = reserve_evidence_root(workspace)

    started = {
        "schema_version": "g10_xmom_001_attempt_started.v1",
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

        inventory = build_source_inventory(history_root=hist, symbols_root=sym)
        inventory_doc = {
            **inventory,
            "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
            "attempt_started_sha256": started_sha,
        }
        _write_new_canonical(evidence_root / "source_inventory.json", inventory_doc)
        inventory_file_sha = sha256_bytes(canonical_json(inventory_doc) + b"\n")

        gate_result = evaluate_inventory_gates(inventory)
        receipt = {
            "schema_version": "g10_xmom_001_source_feasibility_receipt.v1",
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

        terminal_status = gate_result["status"] if gate_result["all_passed"] else FAIL_STATUS
        if gate_result["all_passed"]:
            terminal_status = PASS_STATUS
        else:
            terminal_status = FAIL_STATUS

        terminal = {
            "schema_version": "g10_xmom_001_attempt_terminal.v1",
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
        # Best-effort terminal for engineering failure after reservation.
        failure = {
            "schema_version": "g10_xmom_001_attempt_terminal.v1",
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
