#!/usr/bin/env python3
"""One-shot TRAIN source exporter for HYP-LOMX-MULTI-M1-001.

Importing this module is inert. The production path requires an explicit flag,
the SHA-256 of the latest matching registry row, a frozen preregistration, and
a registry row that authorizes source access while keeping economics disabled.
Only 2016-2020 M1 bars are requested; validation and holdout are never read.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


HYPOTHESIS_ID = "HYP-LOMX-MULTI-M1-001"
EA_NAME = "EA_LondonOpenMultiAssetMomentum"
ATTEMPT_ID = "LOMX001-TRAIN-SOURCE-001"
PLAN_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "HYP-LOMX-MULTI-M1-001_TRAIN_PROBE_PLAN_V2.md"
)
SCRIPT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "export_lomx_001_train_source.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
TERMINAL_REL = "02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe"
DATA_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/LondonOpenMultiAssetMomentum/"
    "HYP-LOMX-MULTI-M1-001"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)

EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY_FRAGMENT = "Five Percent"
TRAIN_YEARS = (2016, 2017, 2018, 2019, 2020)
FORBIDDEN_YEAR_MIN = 2021
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "EURJPY", "XAUUSD")
LOCAL_TZ = "Europe/London"
REQUIRED_HHMM = (800, 830, 1200, 1530, 1600, 1630)
MIN_DATE_COVERAGE = 0.95
MIN_POSITIVE_SPREAD_COVERAGE = 0.95

SCHEMA_COLUMNS = (
    "symbol",
    "local_date",
    "open_0800",
    "open_0830",
    "open_1200",
    "open_1530",
    "open_1600",
    "open_1630",
    "spread_0830_points",
    "spread_1200_points",
    "spread_1530_points",
    "spread_1600_points",
    "spread_1630_points",
    "point",
    "digits",
    "broker_server",
)


class ContractError(RuntimeError):
    """Fail-closed source or authority violation."""


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
        raise ContractError("non-canonical JSON value") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_d_path(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D: {resolved}")
    return resolved


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.exists():
        raise ContractError(f"stale temporary file: {tmp}")
    tmp.write_bytes(payload)
    tmp.replace(path)


def reserve_directory(path: Path) -> Path:
    path = require_d_path(path, label="output directory")
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError(f"one-shot output already exists: {path}") from exc
    return path


def expected_weekdays(start: date, end: date) -> int:
    if end < start:
        raise ContractError("invalid date interval")
    return len(pd.bdate_range(start=start.isoformat(), end=end.isoformat()))


def extract_daily_windows(
    rates: Any,
    *,
    symbol: str,
    point: float,
    digits: int,
    broker_server: str,
) -> list[dict[str, object]]:
    """Project exact London timestamps from one symbol-year M1 rate array."""

    if rates is None or len(rates) == 0:
        return []
    frame = pd.DataFrame(rates)
    required = {"time", "open", "spread"}
    if not required.issubset(frame.columns):
        raise ContractError(f"rate schema mismatch for {symbol}")
    utc = pd.to_datetime(frame["time"], unit="s", utc=True)
    if (utc.dt.year >= FORBIDDEN_YEAR_MIN).any():
        raise ContractError(f"forbidden 2021+ row returned for {symbol}")
    local = utc.dt.tz_convert(LOCAL_TZ)
    frame = frame.assign(
        local_date=local.dt.strftime("%Y-%m-%d"),
        weekday=local.dt.weekday,
        hhmm=local.dt.hour * 100 + local.dt.minute,
    )
    frame = frame[(frame["weekday"] < 5) & frame["hhmm"].isin(REQUIRED_HHMM)]
    if frame.empty:
        return []
    if frame.duplicated(["local_date", "hhmm"]).any():
        raise ContractError(f"duplicate London timestamp for {symbol}")
    open_pivot = frame.pivot(index="local_date", columns="hhmm", values="open")
    spread_pivot = frame.pivot(index="local_date", columns="hhmm", values="spread")
    rows: list[dict[str, object]] = []
    for local_date, opens in open_pivot.iterrows():
        if any(key not in opens.index or pd.isna(opens[key]) for key in REQUIRED_HHMM):
            continue
        spreads = spread_pivot.loc[local_date]
        values = [float(opens[key]) for key in REQUIRED_HHMM]
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ContractError(f"invalid open value for {symbol}:{local_date}")
        rows.append(
            {
                "symbol": symbol,
                "local_date": str(local_date),
                "open_0800": float(opens[800]),
                "open_0830": float(opens[830]),
                "open_1200": float(opens[1200]),
                "open_1530": float(opens[1530]),
                "open_1600": float(opens[1600]),
                "open_1630": float(opens[1630]),
                "spread_0830_points": int(spreads[830]),
                "spread_1200_points": int(spreads[1200]),
                "spread_1530_points": int(spreads[1530]),
                "spread_1600_points": int(spreads[1600]),
                "spread_1630_points": int(spreads[1630]),
                "point": float(point),
                "digits": int(digits),
                "broker_server": broker_server,
            }
        )
    return rows


def summarize_source(frame: pd.DataFrame) -> dict[str, object]:
    if list(frame.columns) != list(SCHEMA_COLUMNS):
        raise ContractError("daily source schema mismatch")
    summary: dict[str, object] = {}
    expected = expected_weekdays(date(2016, 1, 1), date(2020, 12, 31))
    for symbol in SYMBOLS:
        part = frame.loc[frame["symbol"] == symbol].copy()
        if part.empty:
            raise ContractError(f"no complete days for {symbol}")
        if part["local_date"].duplicated().any():
            raise ContractError(f"duplicate local dates for {symbol}")
        if not part["local_date"].is_monotonic_increasing:
            raise ContractError(f"unsorted local dates for {symbol}")
        spread_cols = [column for column in part.columns if column.startswith("spread_")]
        positive = float((part[spread_cols] > 0).to_numpy().mean())
        coverage = float(len(part) / expected)
        if coverage < MIN_DATE_COVERAGE:
            raise ContractError(f"date coverage below gate for {symbol}: {coverage:.6f}")
        if positive < MIN_POSITIVE_SPREAD_COVERAGE:
            raise ContractError(
                f"positive spread coverage below gate for {symbol}: {positive:.6f}"
            )
        summary[symbol] = {
            "rows": int(len(part)),
            "first_local_date": str(part["local_date"].iloc[0]),
            "last_local_date": str(part["local_date"].iloc[-1]),
            "expected_weekdays": expected,
            "date_coverage": coverage,
            "positive_spread_coverage": positive,
            "point": float(part["point"].iloc[0]),
            "digits": int(part["digits"].iloc[0]),
        }
    return summary


def latest_registry_row(registry_path: Path) -> tuple[dict[str, object], str]:
    payload = registry_path.read_bytes()
    matches: list[tuple[dict[str, object], bytes]] = []
    for raw in payload.splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((row, raw))
    if not matches:
        raise ContractError("matching registry row absent")
    row, raw = matches[-1]
    return row, sha256_bytes(raw + b"\n")


def verify_authority(workspace: Path, reviewed_registry_sha: str) -> dict[str, object]:
    plan = workspace / PLAN_REL
    script = workspace / SCRIPT_REL
    registry = workspace / REGISTRY_REL
    for path in (plan, script, registry):
        if not path.is_file():
            raise ContractError(f"required authority file missing: {path}")
    row, row_sha = latest_registry_row(registry)
    if row_sha != reviewed_registry_sha.upper():
        raise ContractError("reviewed registry SHA does not match latest row")
    if row.get("state") != "idea":
        raise ContractError("source export requires latest state=idea")
    if row.get("prereg_path") != PLAN_REL:
        raise ContractError("registry prereg path mismatch")
    if str(row.get("prereg_sha256", "")).upper() != sha256_file(plan):
        raise ContractError("registry prereg hash mismatch")
    if row.get("source_path") is not None or row.get("source_hash") is not None:
        raise ContractError("research probe must not impersonate canonical EA source")
    validation = row.get("validation") or {}
    if validation.get("reviewed_source_exporter_path") != SCRIPT_REL:
        raise ContractError("registry reviewed source exporter path mismatch")
    if str(validation.get("reviewed_source_exporter_sha256", "")).upper() != sha256_file(script):
        raise ContractError("registry reviewed source exporter hash mismatch")
    if validation.get("source_run_authorized") is not True:
        raise ContractError("source run is not authorized")
    if validation.get("economics_authorized") is not False:
        raise ContractError("economics must remain disabled during source export")
    if validation.get("research_validation_access_authorized") is not False:
        raise ContractError("validation access must remain disabled")
    if validation.get("research_holdout_access_authorized") is not False:
        raise ContractError("holdout access must remain disabled")
    return {
        "registry_row_sha256": row_sha,
        "plan_sha256": sha256_file(plan),
        "script_sha256": sha256_file(script),
    }


def initialize_terminal(mt5: Any, terminal_path: Path) -> tuple[dict[str, object], dict[str, tuple[float, int]]]:
    if not mt5.initialize(path=str(terminal_path), portable=True, timeout=60_000):
        raise ContractError(f"mt5 initialize failed: {mt5.last_error()}")
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    if terminal is None or account is None:
        raise ContractError("terminal/account info missing")
    if str(account.server) != EXPECTED_SERVER:
        raise ContractError(f"server mismatch: {account.server}")
    if EXPECTED_COMPANY_FRAGMENT not in str(getattr(account, "company", "")):
        raise ContractError("company mismatch")
    if bool(getattr(terminal, "trade_allowed", False)):
        raise ContractError("refusing terminal with trading enabled")
    require_d_path(Path(str(terminal.data_path)), label="MT5 data path")
    geometry: dict[str, tuple[float, int]] = {}
    for symbol in SYMBOLS:
        if not mt5.symbol_select(symbol, True):
            raise ContractError(f"symbol_select failed: {symbol}")
        info = mt5.symbol_info(symbol)
        if info is None or float(info.point) <= 0.0 or int(info.digits) <= 0:
            raise ContractError(f"invalid symbol geometry: {symbol}")
        geometry[symbol] = (float(info.point), int(info.digits))
    metadata = {
        "terminal_path": str(terminal_path),
        "terminal_build": int(terminal.build),
        "data_path": str(terminal.data_path),
        "portable": True,
        "server": str(account.server),
        "company": str(getattr(account, "company", "")),
        "login": int(account.login),
        "trade_allowed": False,
        "symbols_selected": list(SYMBOLS),
    }
    return metadata, geometry


def export_train_source(workspace: Path, *, reviewed_registry_sha: str) -> dict[str, object]:
    workspace = require_d_path(workspace, label="workspace")
    authority = verify_authority(workspace, reviewed_registry_sha)
    data_root = reserve_directory(workspace / DATA_ROOT_REL)
    evidence_root = reserve_directory(workspace / EVIDENCE_ROOT_REL)
    terminal_path = require_d_path(workspace / TERMINAL_REL, label="terminal")
    mt5 = importlib.import_module("MetaTrader5")
    rows: list[dict[str, object]] = []
    terminal_meta: dict[str, object]
    try:
        terminal_meta, geometry = initialize_terminal(mt5, terminal_path)
        for symbol in SYMBOLS:
            point, digits = geometry[symbol]
            for year in TRAIN_YEARS:
                start = datetime(year, 1, 1, tzinfo=timezone.utc)
                end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
                if rates is None:
                    raise ContractError(
                        f"copy_rates_range failed: {symbol}:{year}:{mt5.last_error()}"
                    )
                rows.extend(
                    extract_daily_windows(
                        rates,
                        symbol=symbol,
                        point=point,
                        digits=digits,
                        broker_server=EXPECTED_SERVER,
                    )
                )
    finally:
        mt5.shutdown()
    frame = pd.DataFrame(rows, columns=SCHEMA_COLUMNS)
    frame = frame.sort_values(["symbol", "local_date"], kind="mergesort").reset_index(drop=True)
    source_summary = summarize_source(frame)
    parquet_path = data_root / "train_daily_windows.parquet"
    frame.to_parquet(parquet_path, index=False, compression="zstd")
    manifest = {
        "schema_version": "lomx_001_train_source_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "split": "TRAIN",
        "train_years": list(TRAIN_YEARS),
        "validation_years_sealed": [2021, 2022, 2023, 2024],
        "holdout_rule": "EVERY_YEAR_2025PLUS_FORBIDDEN",
        "symbols": list(SYMBOLS),
        "timezone": LOCAL_TZ,
        "required_hhmm": list(REQUIRED_HHMM),
        "bar_contract": "BROKER_BID_M1_EXACT_LOCAL_TIMESTAMP_OPEN",
        "row_count": int(len(frame)),
        "schema": list(frame.columns),
        "per_symbol": source_summary,
        "parquet_path": str(parquet_path.relative_to(workspace)).replace("\\", "/"),
        "parquet_sha256": sha256_file(parquet_path),
        "authority": authority,
        "terminal_metadata": terminal_meta,
        "outcome_blind_counters": {
            "returns_computed": 0,
            "signals_generated": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "pf_computed": 0,
            "expectancy_computed": 0,
            "drawdown_computed": 0,
            "economics_executed": False,
            "validation_rows_requested": 0,
            "holdout_rows_requested": 0,
            "orders_submitted": 0,
            "paid_requests_made": 0,
            "model0_runs": 0,
            "source_attempts_consumed": 1,
        },
    }
    manifest_path = data_root / "train_source_manifest.json"
    atomic_write(manifest_path, canonical_json(manifest) + b"\n")
    receipt = {
        "schema_version": "lomx_001_train_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "TRAIN_SOURCE_COMPLETE_ECONOMICS_DISABLED",
        "manifest_path": str(manifest_path.relative_to(workspace)).replace("\\", "/"),
        "manifest_sha256": sha256_file(manifest_path),
        "parquet_sha256": manifest["parquet_sha256"],
        "row_count": int(len(frame)),
        "authority": authority,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    receipt_path = evidence_root / "train_source_receipt.json"
    atomic_write(receipt_path, canonical_json(receipt) + b"\n")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=r"D:\Trading EA MT5")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--reviewed-registry-row-sha256")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.production:
        raise ContractError("production is disarmed; pass --production")
    if not args.reviewed_registry_row_sha256:
        raise ContractError("reviewed registry row SHA is required")
    receipt = export_train_source(
        Path(args.workspace),
        reviewed_registry_sha=str(args.reviewed_registry_row_sha256),
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"LOMX_SOURCE_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
