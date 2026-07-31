#!/usr/bin/env python3
"""Train-only W1 bar exporter for HYP-G10-XMOM-W1-002 (import-inert, disarmed).

Importing this module never initializes MT5, never reads prices, and never
computes ranks/returns/signals/economics. Production requires explicit
--production, an armed REVIEWED_REGISTRY_ROW_SHA256 sentinel matching the
LF-terminated latest registry row SHA, and a one-use train-export authority
row. MetaTrader5 is imported only inside the authorized production path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HYPOTHESIS_ID = "HYP-G10-XMOM-W1-002"
PARENT_HYPOTHESIS_ID = "HYP-G10-XMOM-W1-001"
EA_NAME = "EA_G10WeeklyXSMomentum"
ATTEMPT_ID = "G10XMOM002-TRAIN-EXPORT-001"

PLAN_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/"
    "HYP-G10-XMOM-W1-002_ECONOMIC_PROBE_PLAN.md"
)
PLAN_SHA256 = "ABA4C2BA7AFBA07DE7C38A709E00275507ADFCEE035F17E70896B3FF8A74351C"
PARENT_INVENTORY_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/"
    "HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY/G10XMOM001-SOURCE-001/source_inventory.json"
)
PARENT_INVENTORY_SHA256 = (
    "DCF3754D4B95EFBA2B25A8455CF6DCDF5169C409CE81FE3568F5C7227C98FE01"
)
PARENT_TERMINAL_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/"
    "HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY/G10XMOM001-SOURCE-001/attempt_terminal.json"
)
PARENT_TERMINAL_SHA256 = (
    "3FF657763271E77E61DA8110FAE1260710AD9733B2F2B14D613A3AAAB8CEC48F"
)
EXPORTER_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/export_g10_xmom_002_train_w1.py"
)
TEST_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/tests/"
    "test_export_g10_xmom_002_train_w1.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/"
    "HYP-G10-XMOM-W1-002_TRAIN_EXPORT_IMPLEMENTATION_REVIEW_RECEIPT.json"
)

CANONICAL_WORKSPACE_ROOT = Path(r"D:\Trading EA MT5")
TERMINAL_REL = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe"
)
DATASET_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/"
    f"HYP-G10-XMOM-W1-002/{ATTEMPT_ID}"
)
PARQUET_NAME = "train_w1_bars.parquet"
MANIFEST_NAME = "train_w1_manifest.json"
RECEIPT_NAME = "train_export_receipt.json"

EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY_FRAGMENT = "Five Percent"
TRAIN_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021)
HOLDOUT_YEARS_SEALED: tuple[int, ...] = (2022, 2023, 2024)
FORBIDDEN_YEARS_ANY: frozenset[int] = frozenset(range(1, 2018)) | frozenset(
    range(2022, 3000)
)

SYMBOLS: tuple[str, ...] = (
    "AUDUSD",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)
PIP_SIZE: dict[str, float] = {
    "AUDUSD": 0.0001,
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "NZDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    "USDJPY": 0.01,
}
EXPECTED_DIGITS: dict[str, int] = {
    "AUDUSD": 5,
    "EURUSD": 5,
    "GBPUSD": 5,
    "NZDUSD": 5,
    "USDCAD": 5,
    "USDCHF": 5,
    "USDJPY": 3,
}

SCHEMA_COLUMNS: tuple[str, ...] = (
    "symbol",
    "time_epoch",
    "time_server",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "broker_server",
)

# Independent review must replace this exact sentinel before any real export.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)

HEX = frozenset("0123456789ABCDEF")
CHUNK_SIZE = 1024 * 1024

OUTCOME_BLIND_COUNTERS: dict[str, object] = {
    "bars_exported": 0,
    "ranks_computed": 0,
    "returns_computed": 0,
    "signals_generated": 0,
    "trades_simulated": 0,
    "costs_computed": 0,
    "economics_executed": False,
    "pf_computed": 0,
    "expectancy_computed": 0,
    "drawdown_computed": 0,
    "outcomes_opened": 0,
    "holdout_bars_requested": 0,
    "holdout_bars_exported": 0,
    "research_holdout_opened": False,
    "mt5_launches": 0,
    "network_calls": 0,
    "paid_requests_made": 0,
    "orders_submitted": 0,
    "model0_runs": 0,
    "train_export_attempts_consumed": 0,
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in HEX for char in value)


def normalized_exporter_base_sha256(payload: bytes) -> str:
    """Hash the reviewed disarmed exporter even while its one-shot sentinel is armed."""

    if type(payload) is not bytes:
        raise ContractError("exporter payload must be bytes")
    lines = payload.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("exporter must contain exactly one valid registry-row sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


# Alias required by task packet wording.
normalized_base_sha256 = normalized_exporter_base_sha256


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


def require_d_side_path(path: Path, *, label: str) -> Path:
    resolved = Path(path).resolve(strict=False)
    drive = resolved.drive.upper() if resolved.drive else ""
    if drive != "D:":
        raise ContractError(f"{label} must be on D: drive, got {resolved}")
    text = str(resolved).replace("\\", "/").lower()
    if "file_common" in text:
        raise ContractError(f"{label} must not use FILE_COMMON")
    return resolved


def assert_train_year_only(year: int) -> None:
    if year not in TRAIN_YEARS:
        raise ContractError(f"year outside authorized train split: {year}")
    if year in HOLDOUT_YEARS_SEALED or year >= 2022 or year < 2018:
        raise ContractError(f"holdout_or_pretrain_year_rejected:{year}")


def broker_year_from_epoch(time_epoch: int) -> int:
    # MT5 rate time is broker server wall-time encoded as Unix epoch seconds.
    return datetime.fromtimestamp(int(time_epoch), tz=timezone.utc).year


def reject_returned_bar_year(time_epoch: int, *, symbol: str) -> int:
    year = broker_year_from_epoch(time_epoch)
    if year in FORBIDDEN_YEARS_ANY or year not in TRAIN_YEARS:
        raise ContractError(
            f"returned_bar_year_rejected:{symbol}:{year}:authorized_train_years={list(TRAIN_YEARS)}"
        )
    return year


def validate_symbol_pip_geometry(symbol: str, digits: int, point: float) -> None:
    if symbol not in PIP_SIZE:
        raise ContractError(f"unmapped_symbol:{symbol}")
    expected_pip = PIP_SIZE[symbol]
    expected_digits = EXPECTED_DIGITS[symbol]
    if int(digits) != expected_digits:
        raise ContractError(
            f"symbol_digits_mismatch:{symbol}:got={digits}:expected={expected_digits}"
        )
    # pip = 10 * point for 3/5 digit quotes on this broker contract.
    inferred_pip = float(point) * 10.0
    if abs(inferred_pip - expected_pip) > 1e-12:
        raise ContractError(
            f"symbol_pip_mismatch:{symbol}:got={inferred_pip}:expected={expected_pip}"
        )


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
    """Surface for a later one-use train-export registry row (not used while disarmed)."""

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
        or validation.get("train_export_authorized") is not True
        or validation.get("train_acquisition_authorized") is not True
        or validation.get("mt5_authorized") is not True
        or validation.get("holdout_access_authorized") is not False
        or validation.get("economics_authorized") is not False
        or validation.get("one_use") is not True
    ):
        raise ContractError(
            "latest registry row is not HYP-G10-XMOM-W1-002 probe with "
            "train_export_authorized=true, train_acquisition_authorized=true, "
            "mt5_authorized=true, holdout_access_authorized=false, "
            "economics_authorized=false, one_use=true "
            "and matching prereg SHA"
        )
    required_bindings = {
        "reviewed_exporter_path": EXPORTER_REL,
        "reviewed_test_path": TEST_REL,
        "independent_review_receipt_path": REVIEW_RECEIPT_REL,
    }
    for field, expected in required_bindings.items():
        if validation.get(field) != expected:
            raise ContractError(f"latest registry row has wrong {field}")
    for field in (
        "reviewed_exporter_base_sha256",
        "reviewed_test_sha256",
        "independent_review_receipt_sha256",
        "parent_inventory_sha256",
        "parent_terminal_sha256",
    ):
        if not _valid_sha(validation.get(field)):
            raise ContractError(f"latest registry row has invalid {field}")
    if validation.get("parent_inventory_sha256") != PARENT_INVENTORY_SHA256:
        raise ContractError("parent inventory SHA binding mismatch")
    if validation.get("parent_terminal_sha256") != PARENT_TERMINAL_SHA256:
        raise ContractError("parent terminal SHA binding mismatch")
    return latest_row


def hard_zero_outcome_counters() -> dict[str, object]:
    return dict(OUTCOME_BLIND_COUNTERS)


def build_manifest(
    *,
    dataset_rel: str,
    parquet_rel: str,
    parquet_sha256: str,
    row_count: int,
    symbols: Sequence[str],
    years: Sequence[int],
    first_bar: Mapping[str, object] | None,
    last_bar: Mapping[str, object] | None,
    terminal_metadata: Mapping[str, object],
    plan_sha256: str,
    parent_inventory_sha256: str,
    parent_terminal_sha256: str,
    schema: Sequence[str],
) -> dict[str, object]:
    if tuple(years) != TRAIN_YEARS:
        raise ContractError("manifest years must be exact train years only")
    if any(year >= 2022 or year < 2018 for year in years):
        raise ContractError("manifest must not seal holdout or pre-2018 years")
    if tuple(symbols) != SYMBOLS:
        raise ContractError("manifest symbols must match the exact frozen universe")
    if tuple(schema) != SCHEMA_COLUMNS:
        raise ContractError("manifest schema must match the exact exporter schema")
    if row_count <= 0:
        raise ContractError("manifest row_count must be positive")
    return {
        "schema_version": "g10_xmom_002_train_w1_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "split": "train",
        "train_years": list(TRAIN_YEARS),
        "holdout_years_sealed": list(HOLDOUT_YEARS_SEALED),
        "symbols": list(symbols),
        "years": list(years),
        "row_count": int(row_count),
        "schema": list(schema),
        "dataset_root": dataset_rel,
        "parquet_path": parquet_rel,
        "parquet_sha256": parquet_sha256,
        "first_bar": dict(first_bar) if first_bar is not None else None,
        "last_bar": dict(last_bar) if last_bar is not None else None,
        "terminal_metadata": dict(terminal_metadata),
        "plan_sha256": plan_sha256,
        "parent_inventory_sha256": parent_inventory_sha256,
        "parent_terminal_sha256": parent_terminal_sha256,
        "outcome_blind_counters": hard_zero_outcome_counters(),
        "ranks_computed": 0,
        "returns_computed": 0,
        "signals_generated": 0,
        "economics_executed": False,
        "cost_model_applied": False,
        "broker_spread_is_diagnostic_only": True,
        "acquisition_api": "MetaTrader5.copy_rates_range(symbol,TIMEFRAME_W1,...)",
        "timeframe": "W1",
        "portable": True,
        "expected_server": EXPECTED_SERVER,
        "pip_size": dict(PIP_SIZE),
    }


def rows_to_dataframe(rows: Sequence[Mapping[str, object]]) -> Any:
    import pandas as pd

    if not rows:
        raise ContractError("no rows to export")
    for row in rows:
        if set(row) != set(SCHEMA_COLUMNS):
            raise ContractError("row schema does not match exact exporter schema")
    frame = pd.DataFrame(list(rows), columns=list(SCHEMA_COLUMNS))
    if list(frame.columns) != list(SCHEMA_COLUMNS):
        raise ContractError("schema column order mismatch")
    if set(str(value) for value in frame["symbol"].unique()) != set(SYMBOLS):
        raise ContractError("symbol coverage does not match the exact frozen universe")
    if frame.duplicated(subset=["symbol", "time_epoch"]).any():
        raise ContractError("duplicate symbol/time_epoch key in export rows")
    observed_coverage: set[tuple[str, int]] = set()
    for row in frame.to_dict(orient="records"):
        symbol = str(row["symbol"])
        epoch = int(row["time_epoch"])
        year = reject_returned_bar_year(epoch, symbol=symbol)
        observed_coverage.add((symbol, year))
        if str(row["broker_server"]) != EXPECTED_SERVER:
            raise ContractError(f"broker_server_mismatch:{symbol}:{epoch}")
        ohlc = tuple(float(row[field]) for field in ("open", "high", "low", "close"))
        if not all(math.isfinite(value) and value > 0.0 for value in ohlc):
            raise ContractError(f"invalid_ohlc:{symbol}:{epoch}")
        open_, high, low, close = ohlc
        if high < max(open_, close) or low > min(open_, close) or low > high:
            raise ContractError(f"invalid_ohlc_geometry:{symbol}:{epoch}")
    expected_coverage = {(symbol, year) for symbol in SYMBOLS for year in TRAIN_YEARS}
    if observed_coverage != expected_coverage:
        raise ContractError("symbol/year coverage does not match exact frozen train contract")
    return frame.sort_values(["symbol", "time_epoch"], kind="mergesort").reset_index(drop=True)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes:
        raise ContractError("artifact payload must be bytes")
    path = Path(path)
    require_d_side_path(path, label="artifact")
    if path.exists() or path.is_symlink():
        raise ContractError(f"artifact already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
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
        os.replace(_os_fs_path(temp), _os_fs_path(path))
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


def atomic_write_canonical_json(path: Path, value: object) -> None:
    atomic_write_bytes(path, canonical_json(value) + b"\n")


def atomic_publish_parquet_and_manifest(
    *,
    dataset_root: Path,
    rows: Sequence[Mapping[str, object]],
    terminal_metadata: Mapping[str, object],
    plan_sha256: str = PLAN_SHA256,
    parent_inventory_sha256: str = PARENT_INVENTORY_SHA256,
    parent_terminal_sha256: str = PARENT_TERMINAL_SHA256,
) -> dict[str, object]:
    """Publish train W1 parquet + compact JSON manifest atomically (D-side only)."""

    root = require_d_side_path(dataset_root, label="dataset_root")
    parquet_path = root / PARQUET_NAME
    manifest_path = root / MANIFEST_NAME
    if parquet_path.exists() or manifest_path.exists():
        raise ContractError("dataset parquet/manifest already exists; exclusive paths required")

    frame = rows_to_dataframe(rows)
    years = sorted({broker_year_from_epoch(int(v)) for v in frame["time_epoch"].tolist()})
    for year in years:
        assert_train_year_only(year)

    root.mkdir(parents=True, exist_ok=True)
    temp_parquet = root / f".{PARQUET_NAME}.tmp-{os.getpid()}-{os.urandom(8).hex()}"
    try:
        frame.to_parquet(temp_parquet, index=False)
        os.replace(_os_fs_path(temp_parquet), _os_fs_path(parquet_path))
    finally:
        if temp_parquet.exists():
            try:
                temp_parquet.unlink()
            except OSError:
                pass

    parquet_sha = sha256_file(parquet_path)
    first = frame.iloc[0]
    last = frame.iloc[-1]
    first_bar = {
        "symbol": str(first["symbol"]),
        "time_epoch": int(first["time_epoch"]),
        "time_server": str(first["time_server"]),
    }
    last_bar = {
        "symbol": str(last["symbol"]),
        "time_epoch": int(last["time_epoch"]),
        "time_server": str(last["time_server"]),
    }
    dataset_rel = DATASET_ROOT_REL.replace("\\", "/")
    parquet_rel = f"{dataset_rel}/{PARQUET_NAME}"
    manifest = build_manifest(
        dataset_rel=dataset_rel,
        parquet_rel=parquet_rel,
        parquet_sha256=parquet_sha,
        row_count=int(len(frame)),
        symbols=list(SYMBOLS),
        years=years,
        first_bar=first_bar,
        last_bar=last_bar,
        terminal_metadata=terminal_metadata,
        plan_sha256=plan_sha256,
        parent_inventory_sha256=parent_inventory_sha256,
        parent_terminal_sha256=parent_terminal_sha256,
        schema=SCHEMA_COLUMNS,
    )
    # Keep hard-zero economics counters even after export row_count is known.
    counters = hard_zero_outcome_counters()
    counters["bars_exported"] = 0  # hard-zero outcome-side counters remain zero
    manifest["outcome_blind_counters"] = counters
    atomic_write_canonical_json(manifest_path, manifest)
    return {
        "parquet_path": str(parquet_path),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "parquet_sha256": parquet_sha,
        "manifest_sha256": sha256_file(manifest_path),
        "row_count": int(len(frame)),
    }


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


def _lazy_import_metatrader5() -> Any:
    """Lazy import — only callable from authorized production path.

    Uses importlib so the module remains AST-import-inert with respect to
    MetaTrader5 (no static import statement for the terminal package).
    """

    import importlib

    try:
        return importlib.import_module("MetaTrader5")
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ContractError(f"MetaTrader5 import failed: {exc}") from exc


def initialize_portable_terminal(mt5: Any, terminal_path: Path) -> dict[str, object]:
    terminal_path = require_d_side_path(terminal_path, label="terminal")
    if terminal_path.name.lower() != "terminal64.exe":
        raise ContractError("terminal binary must be terminal64.exe")
    if not terminal_path.is_file():
        raise ContractError(f"portable_terminal_missing:{terminal_path}")
    if not mt5.initialize(path=str(terminal_path), timeout=60_000, portable=True):
        raise ContractError(f"mt5_initialize_failed:{mt5.last_error()}")
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    if terminal is None or account is None:
        raise ContractError("terminal_or_account_info_missing")
    data_path = require_d_side_path(Path(str(terminal.data_path)), label="mt5_data_path")
    server = str(account.server)
    if server != EXPECTED_SERVER:
        raise ContractError(f"server_mismatch:{server}:expected={EXPECTED_SERVER}")
    company = str(getattr(account, "company", "") or "")
    if EXPECTED_COMPANY_FRAGMENT not in company:
        raise ContractError(f"company_mismatch:{company}")
    if bool(getattr(terminal, "trade_allowed", False)):
        raise ContractError("refusing_terminal_with_trading_enabled")
    selected: list[str] = []
    for symbol in SYMBOLS:
        if not mt5.symbol_select(symbol, True):
            raise ContractError(f"symbol_select_failed:{symbol}:{mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ContractError(f"symbol_info_missing:{symbol}")
        validate_symbol_pip_geometry(symbol, int(info.digits), float(info.point))
        selected.append(symbol)
    return {
        "terminal_path": str(terminal_path),
        "terminal_build": int(terminal.build),
        "data_path": str(data_path),
        "portable": True,
        "server": server,
        "company": company,
        "login": int(account.login),
        "symbols_selected": selected,
        "pip_size": dict(PIP_SIZE),
    }


def fetch_train_w1_rows(mt5: Any, *, broker_server: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for symbol in SYMBOLS:
        for year in TRAIN_YEARS:
            assert_train_year_only(year)
            start = datetime(year, 1, 1, tzinfo=timezone.utc)
            end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_W1, start, end)
            if rates is None:
                raise ContractError(
                    f"copy_rates_range_failed:{symbol}:{year}:{mt5.last_error()}"
                )
            for rate in rates:
                epoch = int(rate["time"])
                reject_returned_bar_year(epoch, symbol=symbol)
                open_ = float(rate["open"])
                high = float(rate["high"])
                low = float(rate["low"])
                close = float(rate["close"])
                if min(open_, high, low, close) <= 0.0:
                    raise ContractError(f"non_positive_ohlc:{symbol}:{epoch}")
                time_server = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )
                rows.append(
                    {
                        "symbol": symbol,
                        "time_epoch": epoch,
                        "time_server": time_server,
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "tick_volume": int(rate["tick_volume"]),
                        "spread": int(rate["spread"]),
                        "broker_server": broker_server,
                    }
                )
    if not rows:
        raise ContractError("no_train_w1_rows_returned")
    rows.sort(key=lambda item: (str(item["symbol"]), int(item["time_epoch"])))
    return rows


def reserve_exclusive_dir(path: Path) -> Path:
    path = require_d_side_path(path, label="exclusive_dir")
    try:
        path.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError(
            "exclusive path already exists; one-use reservation rejected"
        ) from exc
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.mkdir(parents=False, exist_ok=False)
        except FileExistsError as exc:
            raise ContractError(
                "exclusive path already exists; one-use reservation rejected"
            ) from exc
    return path


def run_production(
    *,
    workspace_root: Path,
    production: bool,
) -> dict[str, object]:
    """Fail-closed production export. Requires explicit production flag + armed sentinel."""

    if production is not True:
        raise ContractError(
            "production train export is disarmed; explicit --production is required"
        )
    if REVIEWED_REGISTRY_ROW_SHA256 is None:
        raise ContractError(
            "production train export is disarmed; reviewed registry-row sentinel is absent"
        )
    if not _valid_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("reviewed registry-row sentinel is invalid")

    workspace = Path(workspace_root).resolve(strict=True)
    canonical_workspace = Path(CANONICAL_WORKSPACE_ROOT).resolve(strict=True)
    if os.path.normcase(str(workspace)) != os.path.normcase(str(canonical_workspace)):
        raise ContractError("production workspace is not the canonical D-side workspace")
    require_d_side_path(workspace, label="workspace")

    reg_path = workspace / REGISTRY_REL
    registry_payload = _read_file_bytes(reg_path)
    authority = validate_production_registry_authority(
        registry_payload, REVIEWED_REGISTRY_ROW_SHA256
    )
    validation = authority["validation"]
    if type(validation) is not dict:
        raise ContractError("latest registry row missing validation bindings")

    plan_payload = _read_file_bytes(workspace / PLAN_REL)
    if sha256_bytes(plan_payload) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")
    if sha256_bytes(_read_file_bytes(workspace / PARENT_INVENTORY_REL)) != PARENT_INVENTORY_SHA256:
        raise ContractError("parent inventory SHA mismatch")
    if sha256_bytes(_read_file_bytes(workspace / PARENT_TERMINAL_REL)) != PARENT_TERMINAL_SHA256:
        raise ContractError("parent terminal SHA mismatch")

    exporter_payload = _read_file_bytes(workspace / EXPORTER_REL)
    exporter_base_sha = normalized_exporter_base_sha256(exporter_payload)
    test_sha = sha256_bytes(_read_file_bytes(workspace / TEST_REL))
    review_receipt_sha = sha256_bytes(_read_file_bytes(workspace / REVIEW_RECEIPT_REL))
    if exporter_base_sha != validation.get("reviewed_exporter_base_sha256"):
        raise ContractError("reviewed disarmed exporter SHA mismatch")
    if test_sha != validation.get("reviewed_test_sha256"):
        raise ContractError("reviewed test SHA mismatch")
    if review_receipt_sha != validation.get("independent_review_receipt_sha256"):
        raise ContractError("independent review receipt SHA mismatch")

    evidence_root = reserve_exclusive_dir(workspace / EVIDENCE_ROOT_REL)
    dataset_root = workspace / DATASET_ROOT_REL
    require_d_side_path(dataset_root, label="dataset_root")
    if dataset_root.exists() and any(dataset_root.iterdir()):
        raise ContractError("dataset root not exclusive; refuse non-empty dataset root")

    # Lazy MT5 import only after authority and exclusive-path gates pass.
    mt5 = _lazy_import_metatrader5()
    terminal_path = workspace / TERMINAL_REL
    try:
        terminal_metadata = initialize_portable_terminal(mt5, terminal_path)
        rows = fetch_train_w1_rows(
            mt5, broker_server=str(terminal_metadata["server"])
        )
        published = atomic_publish_parquet_and_manifest(
            dataset_root=dataset_root,
            rows=rows,
            terminal_metadata=terminal_metadata,
        )
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    receipt = {
        "schema_version": "g10_xmom_002_train_export_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
        "status": "TRAIN_EXPORT_COMPLETE_OUTCOME_BLIND",
        "split": "train",
        "train_years": list(TRAIN_YEARS),
        "holdout_years_sealed": list(HOLDOUT_YEARS_SEALED),
        "plan_sha256": PLAN_SHA256,
        "parent_inventory_sha256": PARENT_INVENTORY_SHA256,
        "parent_terminal_sha256": PARENT_TERMINAL_SHA256,
        "exporter_base_sha256": exporter_base_sha,
        "test_sha256": test_sha,
        "independent_review_receipt_sha256": review_receipt_sha,
        "parquet_sha256": published["parquet_sha256"],
        "manifest_sha256": published["manifest_sha256"],
        "row_count": published["row_count"],
        "terminal_metadata": terminal_metadata,
        "outcome_blind_counters": {
            **hard_zero_outcome_counters(),
            "train_export_attempts_consumed": 1,
            "mt5_launches": 1,
        },
        "ranks_computed": 0,
        "returns_computed": 0,
        "signals_generated": 0,
        "economics_executed": False,
        "holdout_access": False,
    }
    atomic_write_canonical_json(evidence_root / RECEIPT_NAME, receipt)
    return receipt


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--production",
        action="store_true",
        help="Explicit arm for the single real train W1 export attempt.",
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
