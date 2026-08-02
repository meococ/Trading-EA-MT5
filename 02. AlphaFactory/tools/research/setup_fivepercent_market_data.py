#!/usr/bin/env python3
"""Create a hash-bound, zero-trade FivePercent five-asset bar foundation.

The production path is explicit and one-use. It attaches only to the bound
portable terminal, verifies server/storage/trading state, reads native bars,
and publishes versioned Parquet plus a reconciled manifest. It never queries
orders, positions, deals, PnL, or strategy outcomes.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[3]
DATASET_ID = "DATA-FIVEPERCENT-5ASSET-MULTITF-004"
SYMBOLS = ("EURUSD", "USDJPY", "GBPUSD", "XAUUSD", "BTCUSD")
SYMBOL_ALIASES = {"JPYUSD": "USDJPY", "GPBUSD": "GBPUSD"}
TIMEFRAMES = ("M1", "M5", "H1", "H4")
TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "H1": 60, "H4": 240}
FRAME_COLUMNS = (
    "symbol",
    "timeframe",
    "source_epoch",
    "time_server",
    "time_utc",
    "utc_offset_h",
    "utc_ambiguous",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
)
EXPECTED_GEOMETRY = {
    "EURUSD": {"digits": 5, "point": 0.00001},
    "USDJPY": {"digits": 3, "point": 0.001},
    "GBPUSD": {"digits": 5, "point": 0.00001},
    "XAUUSD": {"digits": 2, "point": 0.01},
    "BTCUSD": {"digits": 2, "point": 0.01},
}
EXPECTED_UTC_AMBIGUOUS_ROWS = {
    (symbol, timeframe): 0 for symbol in SYMBOLS for timeframe in TIMEFRAMES
}
EXPECTED_UTC_AMBIGUOUS_ROWS.update(
    {
        ("BTCUSD", "M1"): 170,
        ("BTCUSD", "M5"): 56,
        ("BTCUSD", "H1"): 10,
    }
)
EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY_FRAGMENT = "Five Percent Online Ltd"
REQUESTED_START_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)
CUTOFF_UTC = datetime(2026, 8, 1, 23, 59, 59, tzinfo=timezone.utc)
MIN_TERMINAL_MAXBARS = 20_000_000
HISTORY_SYNC_TIMEOUT_SECONDS = 120.0
HISTORY_SYNC_RETRY_SECONDS = 2.0
HISTORY_CHUNK_YEARS = 10

TERMINAL_REL = "02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe"
COMMON_CONFIG_REL = (
    "02. AlphaFactory/runtime/mt5-portable-fivepercent/config/common.ini"
)
CLOCK_REL = "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
PLAN_REL = (
    "03. EA Developer/EA_FiveAssetDataFoundation/research/"
    "DATA-FIVEPERCENT-5ASSET-MULTITF-004_PLAN.md"
)
TEST_REL = "02. AlphaFactory/tests/test_setup_fivepercent_market_data.py"
AUTHORITY_REL = (
    "03. EA Developer/EA_FiveAssetDataFoundation/research/"
    "DATA-FIVEPERCENT-5ASSET-MULTITF-004_RUN_AUTHORITY.json"
)
DATA_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/"
    f"{DATASET_ID}"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_FiveAssetDataFoundation/research/evidence/"
    f"{DATASET_ID}"
)


class ContractError(RuntimeError):
    """Fail-closed data setup violation; never an economic verdict."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def atomic_write(path: Path, payload: bytes, *, create_new: bool = True) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if create_new and target.exists():
        raise ContractError(f"create-new target exists: {target}")
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, value: object, *, create_new: bool = True) -> None:
    atomic_write(path, canonical_json(value), create_new=create_new)


def canonical_symbols(values: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in values:
        token = str(raw).strip().upper()
        token = SYMBOL_ALIASES.get(token, token)
        if token not in SYMBOLS:
            raise ContractError(f"unsupported symbol: {raw}")
        if token in normalized:
            raise ContractError(f"duplicate symbol after normalization: {token}")
        normalized.append(token)
    if tuple(normalized) != SYMBOLS:
        raise ContractError(
            f"symbol order/scope mismatch: expected {','.join(SYMBOLS)}"
        )
    return tuple(normalized)


def _resolve_bound_path(raw: str) -> Path:
    candidate = Path(raw)
    return candidate.resolve() if candidate.is_absolute() else (WORKSPACE / candidate).resolve()


def _require_d_path(raw: str | Path, label: str) -> Path:
    path = Path(raw).resolve()
    if path.drive.upper() != "D:":
        raise ContractError(f"{label} must resolve to D: {path}")
    return path


def validate_terminal_contract(
    terminal: Mapping[str, object], account: Mapping[str, object]
) -> None:
    if bool(terminal.get("trade_allowed")):
        raise ContractError("terminal-side trading enabled")
    if not bool(terminal.get("connected", True)):
        raise ContractError("terminal is not connected")
    _require_d_path(str(terminal.get("data_path", "")), "terminal data path")
    if (
        str(account.get("server")) != EXPECTED_SERVER
        or EXPECTED_COMPANY_FRAGMENT not in str(account.get("company", ""))
    ):
        raise ContractError(
            "broker identity mismatch: "
            f"{account.get('server')} / {account.get('company')}"
        )
    maxbars = terminal.get("maxbars")
    if maxbars is not None and int(maxbars) < MIN_TERMINAL_MAXBARS:
        raise ContractError(
            f"terminal maxbars too small: {maxbars} < {MIN_TERMINAL_MAXBARS}"
        )


def validate_symbol_geometry(symbol: str, digits: int, point: float) -> None:
    expected = EXPECTED_GEOMETRY.get(symbol)
    if expected is None:
        raise ContractError(f"unsupported symbol geometry: {symbol}")
    if int(digits) != int(expected["digits"]) or not math.isclose(
        float(point), float(expected["point"]), rel_tol=0.0, abs_tol=1e-12
    ):
        raise ContractError(
            f"symbol geometry mismatch: {symbol} digits={digits} point={point}"
        )


def _load_clock_module() -> Any:
    path = WORKSPACE / CLOCK_REL
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load clock model: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _utc_offsets(server_time: pd.Series) -> np.ndarray:
    """Vectorized equivalent of the canonical era-aware clock model."""
    clock = _load_clock_module()
    guess = server_time - pd.Timedelta(hours=2)
    years = guess.dt.year.to_numpy()
    values = np.full(len(server_time), 2, dtype=np.int8)
    for year in np.unique(years):
        if int(year) >= 2024:
            start = clock._nth_sunday(int(year), 3, 2).replace(
                hour=7, tzinfo=None
            )
            end = clock._nth_sunday(int(year), 11, 1).replace(
                hour=6, tzinfo=None
            )
        else:
            start = clock._last_sunday(int(year), 3).replace(
                hour=1, tzinfo=None
            )
            end = clock._last_sunday(int(year), 10).replace(
                hour=1, tzinfo=None
            )
        mask = (years == year) & (guess >= start).to_numpy() & (guess < end).to_numpy()
        values[mask] = 3
    return values


def rates_to_frame(
    rates: Sequence[object] | np.ndarray,
    *,
    symbol: str,
    timeframe: str,
    cutoff_utc: datetime,
) -> pd.DataFrame:
    if symbol not in SYMBOLS or timeframe not in TIMEFRAMES:
        raise ContractError(f"invalid frame identity: {symbol}/{timeframe}")
    if cutoff_utc.tzinfo is None:
        raise ContractError("cutoff must be timezone-aware")
    raw = pd.DataFrame(rates)
    required = {
        "time",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    }
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ContractError(f"MT5 rates schema missing: {missing}")
    server = pd.to_datetime(raw["time"], unit="s", utc=True).dt.tz_localize(None)
    offsets = _utc_offsets(server)
    utc = pd.to_datetime(
        server - pd.to_timedelta(offsets, unit="h"), utc=True
    )
    frame = pd.DataFrame(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "source_epoch": pd.to_numeric(raw["time"], errors="raise").to_numpy(
                dtype=np.int64
            ),
            "time_server": server,
            "time_utc": utc,
            "utc_offset_h": offsets,
            "utc_ambiguous": False,
            "open": pd.to_numeric(raw["open"], errors="coerce").to_numpy(float),
            "high": pd.to_numeric(raw["high"], errors="coerce").to_numpy(float),
            "low": pd.to_numeric(raw["low"], errors="coerce").to_numpy(float),
            "close": pd.to_numeric(raw["close"], errors="coerce").to_numpy(float),
            "tick_volume": pd.to_numeric(raw["tick_volume"], errors="coerce").to_numpy(),
            "spread": pd.to_numeric(raw["spread"], errors="coerce").to_numpy(),
            "real_volume": pd.to_numeric(raw["real_volume"], errors="coerce").to_numpy(),
        },
        columns=list(FRAME_COLUMNS),
    )
    duration = pd.Timedelta(minutes=TIMEFRAME_MINUTES[timeframe])
    legal = frame["time_utc"] + duration <= pd.Timestamp(cutoff_utc)
    frame = frame.loc[legal].reset_index(drop=True)
    ambiguous = frame["time_utc"].duplicated(keep=False)
    ambiguous_groups = int(frame.loc[ambiguous, "time_utc"].nunique())
    frame.loc[ambiguous, "utc_ambiguous"] = True
    frame.loc[ambiguous, "time_utc"] = pd.NaT
    frame.attrs["utc_ambiguous_rows"] = int(ambiguous.sum())
    frame.attrs["utc_ambiguous_groups"] = ambiguous_groups
    return frame


def reconcile_exact_source_duplicates(
    rates: Sequence[object] | np.ndarray | pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Collapse only exact source duplicates; conflicting same-time bars fail."""
    raw = pd.DataFrame(rates)
    if "time" not in raw.columns:
        raise ContractError(f"MT5 rates schema missing time: {symbol}/{timeframe}")
    duplicate_mask = raw["time"].duplicated(keep=False)
    duplicate_rows = raw.loc[duplicate_mask]
    duplicate_groups = 0
    if not duplicate_rows.empty:
        for epoch, group in duplicate_rows.groupby("time", sort=False):
            duplicate_groups += 1
            if len(group.drop_duplicates()) != 1:
                raise ContractError(
                    "conflicting source bars share one epoch: "
                    f"{symbol}/{timeframe} epoch={int(epoch)} rows={len(group)}"
                )
    clean = raw.drop_duplicates(subset=["time"], keep="first").reset_index(drop=True)
    return clean, {
        "raw_source_rows": int(len(raw)),
        "source_exact_duplicate_groups": int(duplicate_groups),
        "source_exact_duplicate_rows_removed": int(len(raw) - len(clean)),
        "source_conflicting_duplicate_groups": 0,
    }


def _iso_utc(value: object) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_market_frame(
    frame: pd.DataFrame,
    symbol: str,
    timeframe: str,
    cutoff_utc: datetime,
) -> dict[str, object]:
    if tuple(frame.columns) != FRAME_COLUMNS:
        raise ContractError("published frame schema/order mismatch")
    if frame.empty:
        raise ContractError(f"no closed bars returned: {symbol}/{timeframe}")
    if not frame["symbol"].eq(symbol).all() or not frame["timeframe"].eq(timeframe).all():
        raise ContractError(f"mixed frame identity: {symbol}/{timeframe}")
    duplicate_source_count = int(
        frame["source_epoch"].duplicated(keep=False).sum()
    )
    if duplicate_source_count:
        raise ContractError(
            f"duplicate source epochs: {symbol}/{timeframe} count={duplicate_source_count}"
        )
    if not frame["source_epoch"].is_monotonic_increasing:
        raise ContractError(f"source epochs not strictly increasing: {symbol}/{timeframe}")
    ambiguous = frame["utc_ambiguous"].astype(bool)
    if not frame["time_utc"].isna().equals(ambiguous):
        raise ContractError(f"UTC ambiguity/null contract mismatch: {symbol}/{timeframe}")
    nominal_utc = pd.to_datetime(
        frame["time_server"]
        - pd.to_timedelta(frame["utc_offset_h"].to_numpy(), unit="h"),
        utc=True,
    )
    if ambiguous.any():
        if symbol != "BTCUSD":
            raise ContractError(f"unexpected UTC ambiguity: {symbol}/{timeframe}")
        for utc_value, group in frame.loc[ambiguous].groupby(
            nominal_utc.loc[ambiguous], sort=False
        ):
            server_span = group["time_server"].max() - group["time_server"].min()
            if (
                len(group) != 2
                or set(int(value) for value in group["utc_offset_h"]) != {2, 3}
                or server_span != pd.Timedelta(hours=1)
            ):
                raise ContractError(
                    "unsupported continuous-market UTC ambiguity: "
                    f"{symbol}/{timeframe} utc={utc_value} rows={len(group)}"
                )
    exact_utc = frame.loc[~ambiguous, "time_utc"]
    duplicate_count = int(exact_utc.duplicated(keep=False).sum())
    if duplicate_count:
        raise ContractError(
            f"duplicate non-null UTC timestamps: {symbol}/{timeframe} "
            f"count={duplicate_count}"
        )
    if not exact_utc.is_monotonic_increasing:
        raise ContractError(f"non-null UTC not increasing: {symbol}/{timeframe}")
    ohlc = frame[["open", "high", "low", "close"]].to_numpy(float)
    if not np.isfinite(ohlc).all() or np.any(ohlc <= 0):
        raise ContractError(f"invalid OHLC values: {symbol}/{timeframe}")
    if (
        (frame["high"] < frame[["open", "low", "close"]].max(axis=1)).any()
        or (frame["low"] > frame[["open", "high", "close"]].min(axis=1)).any()
    ):
        raise ContractError(f"inconsistent OHLC geometry: {symbol}/{timeframe}")
    for column in ("tick_volume", "spread", "real_volume"):
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any() or (values < 0).any():
            raise ContractError(f"invalid nonnegative field {column}: {symbol}/{timeframe}")
    duration = pd.Timedelta(minutes=TIMEFRAME_MINUTES[timeframe])
    if nominal_utc.iloc[-1] + duration > pd.Timestamp(cutoff_utc):
        raise ContractError(f"open bar leaked past cutoff: {symbol}/{timeframe}")
    step_seconds = TIMEFRAME_MINUTES[timeframe] * 60
    gaps = frame["source_epoch"].diff().dropna()
    nonstandard = gaps[gaps != step_seconds]
    return {
        "rows": int(len(frame)),
        "first_source_epoch": int(frame["source_epoch"].iloc[0]),
        "last_source_epoch": int(frame["source_epoch"].iloc[-1]),
        "first_time_server": str(frame["time_server"].iloc[0]),
        "last_time_server": str(frame["time_server"].iloc[-1]),
        "first_time_utc": _iso_utc(exact_utc.iloc[0]) if len(exact_utc) else None,
        "last_time_utc": _iso_utc(exact_utc.iloc[-1]) if len(exact_utc) else None,
        "first_time_utc_nominal": _iso_utc(nominal_utc.iloc[0]),
        "last_time_utc_nominal": _iso_utc(nominal_utc.iloc[-1]),
        "years_utc": sorted(int(year) for year in nominal_utc.dt.year.unique()),
        "duplicate_source_epoch": duplicate_source_count,
        "duplicate_time_utc": duplicate_count,
        "strictly_increasing": True,
        "primary_time_axis": "source_epoch",
        "utc_ambiguous_rows": int(ambiguous.sum()),
        "utc_ambiguous_groups": int(nominal_utc.loc[ambiguous].nunique()),
        "utc_complete": not bool(ambiguous.any()),
        "expected_step_seconds": step_seconds,
        "nonstandard_gap_count": int(len(nonstandard)),
        "largest_gap_seconds": float(nonstandard.max()) if len(nonstandard) else 0.0,
        "zero_spread_rows": int((frame["spread"] == 0).sum()),
        "zero_tick_volume_rows": int((frame["tick_volume"] == 0).sum()),
    }


def validate_run_authority(authority: Mapping[str, object]) -> None:
    if authority.get("schema_version") != "five_asset_data_run_authority.v1":
        raise ContractError("run authority schema mismatch")
    if authority.get("dataset_id") != DATASET_ID:
        raise ContractError("run authority dataset mismatch")
    if authority.get("authorized") is not True or authority.get("one_use") is not True:
        raise ContractError("run authority is not armed one-use")
    if tuple(authority.get("symbols", [])) != SYMBOLS:
        raise ContractError("run authority symbol scope mismatch")
    if tuple(authority.get("timeframes", [])) != TIMEFRAMES:
        raise ContractError("run authority timeframe scope mismatch")
    if authority.get("cutoff_utc") != CUTOFF_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"):
        raise ContractError("run authority cutoff mismatch")
    for label in ("plan", "tool", "test"):
        path = _resolve_bound_path(str(authority.get(f"{label}_path", "")))
        expected = str(authority.get(f"{label}_sha256", ""))
        actual = sha256_file(path)
        if actual != expected:
            raise ContractError(
                f"{label} SHA256 mismatch expected={expected} actual={actual}"
            )


def validate_storage_snapshot(path: Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != "alphafactory_mt5_storage_snapshot.v1":
        raise ContractError(f"storage snapshot schema mismatch: {path}")
    roots = payload.get("roots")
    if not isinstance(roots, list) or len(roots) != 4:
        raise ContractError(f"storage snapshot must contain four roots: {path}")
    return payload


def compare_storage_snapshots(before_path: Path, after_path: Path) -> dict[str, object]:
    before = validate_storage_snapshot(before_path)
    after = validate_storage_snapshot(after_path)
    keys = ("root", "exists", "file_count", "total_bytes", "metadata_sha256")
    before_rows = [{key: row.get(key) for key in keys} for row in before["roots"]]
    after_rows = [{key: row.get(key) for key in keys} for row in after["roots"]]
    return {
        "schema_version": "five_asset_data_storage_reconciliation.v1",
        "dataset_id": DATASET_ID,
        "before_path": str(Path(before_path)),
        "before_sha256": sha256_file(before_path),
        "after_path": str(Path(after_path)),
        "after_sha256": sha256_file(after_path),
        "protected_c_roots_unchanged": before_rows == after_rows,
        "before": before_rows,
        "after": after_rows,
    }


def _load_mt5() -> Any:
    try:
        import MetaTrader5 as mt5
    except Exception as exc:  # pragma: no cover - host dependent
        raise ContractError(f"MetaTrader5 import failed: {exc}") from exc
    return mt5


def _namedtuple_dict(value: object) -> dict[str, object]:
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    raise ContractError("MT5 metadata object lacks _asdict")


def initialize_terminal(mt5: Any, authority: Mapping[str, object]) -> dict[str, object]:
    terminal_path = _require_d_path(WORKSPACE / TERMINAL_REL, "terminal executable")
    expected_terminal_sha = str(authority.get("terminal_sha256", ""))
    if sha256_file(terminal_path) != expected_terminal_sha:
        raise ContractError("terminal executable SHA256 mismatch")
    clock_path = WORKSPACE / CLOCK_REL
    if sha256_file(clock_path) != str(authority.get("clock_sha256", "")):
        raise ContractError("clock model SHA256 mismatch")
    common_config = WORKSPACE / COMMON_CONFIG_REL
    if sha256_file(common_config) != str(authority.get("common_config_sha256", "")):
        raise ContractError("terminal common.ini SHA256 mismatch")
    if not mt5.initialize(path=str(terminal_path), timeout=60_000, portable=True):
        raise ContractError(f"MT5 initialize failed: {mt5.last_error()}")
    terminal_info = mt5.terminal_info()
    account_info = mt5.account_info()
    if terminal_info is None or account_info is None:
        raise ContractError(f"MT5 metadata unavailable: {mt5.last_error()}")
    terminal = _namedtuple_dict(terminal_info)
    account = _namedtuple_dict(account_info)
    validate_terminal_contract(terminal, account)
    geometry: dict[str, object] = {}
    for symbol in SYMBOLS:
        if not mt5.symbol_select(symbol, True):
            raise ContractError(f"symbol_select failed: {symbol}: {mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ContractError(f"symbol_info unavailable: {symbol}")
        validate_symbol_geometry(symbol, int(info.digits), float(info.point))
        geometry[symbol] = {
            "digits": int(info.digits),
            "point": float(info.point),
            "path": str(info.path),
            "trade_mode": int(info.trade_mode),
        }
    return {
        "terminal_path": str(terminal_path.relative_to(WORKSPACE)).replace("\\", "/"),
        "terminal_sha256": expected_terminal_sha,
        "common_config_path": COMMON_CONFIG_REL,
        "common_config_sha256": authority["common_config_sha256"],
        "terminal_build": int(terminal_info.build),
        "terminal_maxbars": int(terminal_info.maxbars),
        "data_path": str(terminal_info.data_path),
        "portable": True,
        "connected": bool(terminal_info.connected),
        "terminal_trade_allowed": bool(terminal_info.trade_allowed),
        "server": str(account_info.server),
        "company": str(account_info.company),
        "account_trade_mode": int(account_info.trade_mode),
        "symbol_geometry": geometry,
    }


def _timeframe_value(mt5: Any, timeframe: str) -> int:
    return int(getattr(mt5, f"TIMEFRAME_{timeframe}"))


def copy_rates_range_with_retry(
    mt5: Any,
    symbol: str,
    timeframe: int,
    date_from: datetime,
    date_to: datetime,
    *,
    timeout_seconds: float = HISTORY_SYNC_TIMEOUT_SECONDS,
    retry_seconds: float = HISTORY_SYNC_RETRY_SECONDS,
) -> np.ndarray:
    """Wait for MT5 IPC/history synchronization; empty valid ranges are allowed."""
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    last_error: object = None
    while True:
        attempts += 1
        rates = mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
        if rates is not None:
            return rates
        last_error = mt5.last_error()
        if isinstance(last_error, (list, tuple)) and last_error and last_error[0] == -2:
            raise ContractError(
                f"invalid MT5 history request: {symbol} last_error={last_error}"
            )
        if time.monotonic() >= deadline:
            raise ContractError(
                "history synchronization timed out: "
                f"{symbol} attempts={attempts} last_error={last_error}"
            )
        time.sleep(retry_seconds)


def copy_rates_range_chunked(
    mt5: Any,
    symbol: str,
    timeframe: int,
    date_from: datetime,
    date_to: datetime,
    *,
    chunk_years: int = HISTORY_CHUNK_YEARS,
) -> np.ndarray:
    """Read long M1 history in non-overlapping chunks below MT5's request cap."""
    if chunk_years <= 0 or date_from > date_to:
        raise ContractError("invalid history chunk bounds")
    chunks: list[np.ndarray] = []
    cursor = date_from
    while cursor <= date_to:
        next_boundary = datetime(
            cursor.year + chunk_years, 1, 1, tzinfo=timezone.utc
        )
        chunk_end = min(date_to, next_boundary - timedelta(seconds=1))
        rates = copy_rates_range_with_retry(
            mt5, symbol, timeframe, cursor, chunk_end
        )
        if len(rates) >= MIN_TERMINAL_MAXBARS:
            raise ContractError(
                f"terminal MaxBars cap reached in chunk: {symbol} "
                f"start={cursor.isoformat()} rows={len(rates)}"
            )
        if len(rates):
            chunks.append(rates)
        cursor = chunk_end + timedelta(seconds=1)
    if not chunks:
        raise ContractError(f"no history returned across chunks: {symbol}")
    return np.concatenate(chunks)


def pull_frame(mt5: Any, symbol: str, timeframe: str) -> pd.DataFrame:
    # The returned epoch represents broker server wall time. Extend the API end
    # by the maximum +3h server offset, then filter exact UTC bar closure below.
    request_end = CUTOFF_UTC + timedelta(hours=3)
    timeframe_value = _timeframe_value(mt5, timeframe)
    if timeframe == "M1":
        rates = copy_rates_range_chunked(
            mt5,
            symbol,
            timeframe_value,
            REQUESTED_START_UTC,
            request_end,
        )
    else:
        rates = copy_rates_range_with_retry(
            mt5,
            symbol,
            timeframe_value,
            REQUESTED_START_UTC,
            request_end,
        )
    if timeframe != "M1" and len(rates) >= MIN_TERMINAL_MAXBARS:
        raise ContractError(
            f"terminal MaxBars cap reached: {symbol}/{timeframe} rows={len(rates)}"
        )
    reconciled, duplicate_reconciliation = reconcile_exact_source_duplicates(
        rates, symbol=symbol, timeframe=timeframe
    )
    frame = rates_to_frame(
        reconciled,
        symbol=symbol,
        timeframe=timeframe,
        cutoff_utc=CUTOFF_UTC,
    )
    frame.attrs.update(duplicate_reconciliation)
    summary = validate_market_frame(frame, symbol, timeframe, CUTOFF_UTC)
    expected_ambiguous = EXPECTED_UTC_AMBIGUOUS_ROWS[(symbol, timeframe)]
    if int(summary["utc_ambiguous_rows"]) != expected_ambiguous:
        raise ContractError(
            "UTC ambiguity census drift: "
            f"{symbol}/{timeframe} expected={expected_ambiguous} "
            f"actual={summary['utc_ambiguous_rows']}"
        )
    return frame


def publish_frame(
    root: Path, frame: pd.DataFrame, symbol: str, timeframe: str
) -> dict[str, object]:
    target = root / symbol / f"{symbol}_{timeframe}_ALL_AVAILABLE_20260801.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ContractError(f"refusing to overwrite dataset file: {target}")
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        frame.to_parquet(temporary, index=False, compression="zstd")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    summary = validate_market_frame(frame, symbol, timeframe, CUTOFF_UTC)
    summary.update(
        {
            key: int(frame.attrs.get(key, 0))
            for key in (
                "raw_source_rows",
                "source_exact_duplicate_groups",
                "source_exact_duplicate_rows_removed",
                "source_conflicting_duplicate_groups",
            )
        }
    )
    summary.update(
        {
            "path": str(target.relative_to(WORKSPACE)).replace("\\", "/"),
            "bytes": int(target.stat().st_size),
            "sha256": sha256_file(target),
        }
    )
    return summary


def verify_manifest_files(manifest: Mapping[str, object]) -> None:
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(SYMBOLS) * len(TIMEFRAMES):
        raise ContractError("manifest file count mismatch")
    for item in files:
        if not isinstance(item, dict):
            raise ContractError("manifest file entry is not an object")
        path = WORKSPACE / str(item.get("path", ""))
        if not path.is_file():
            raise ContractError(f"manifest file missing: {path}")
        if path.stat().st_size != int(item.get("bytes", -1)):
            raise ContractError(f"manifest byte count mismatch: {path}")
        if sha256_file(path) != item.get("sha256"):
            raise ContractError(f"manifest SHA256 mismatch: {path}")


def run_production(authority_path: Path, before_snapshot: Path) -> dict[str, object]:
    authority = json.loads(Path(authority_path).read_text(encoding="utf-8"))
    validate_run_authority(authority)
    if sha256_file(before_snapshot) != authority.get("c_snapshot_before_sha256"):
        raise ContractError("protected-C before-snapshot SHA256 mismatch")
    validate_storage_snapshot(before_snapshot)
    root = _require_d_path(WORKSPACE / DATA_ROOT_REL, "dataset root")
    if root.exists() and any(root.iterdir()):
        raise ContractError(f"dataset root is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    evidence_root = WORKSPACE / EVIDENCE_ROOT_REL
    receipt_path = evidence_root / "export_receipt.json"
    manifest_path = root / "manifest.json"
    if receipt_path.exists() or manifest_path.exists():
        raise ContractError("one-use output already exists")

    mt5 = _load_mt5()
    files: list[dict[str, object]] = []
    terminal_metadata: dict[str, object] | None = None
    try:
        terminal_metadata = initialize_terminal(mt5, authority)
        for symbol in SYMBOLS:
            for timeframe in TIMEFRAMES:
                frame = pull_frame(mt5, symbol, timeframe)
                files.append(publish_frame(root, frame, symbol, timeframe))
                del frame
                gc.collect()
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    if terminal_metadata is None:
        raise ContractError("terminal metadata was not established")
    manifest = {
        "schema_version": "five_asset_market_data_manifest.v1",
        "dataset_id": DATASET_ID,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "RAW_BROKER_BARS_ZERO_TRADE_NO_OUTCOMES",
        "requested_start_utc": REQUESTED_START_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_utc": CUTOFF_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "symbols": list(SYMBOLS),
        "timeframes": list(TIMEFRAMES),
        "frame_schema": list(FRAME_COLUMNS),
        "bar_contract": (
            "NATIVE_MT5_BROKER_BID_BARS_FULLY_CLOSED_SOURCE_EPOCH_PRIMARY_"
            "NULL_UTC_WHEN_AMBIGUOUS"
        ),
        "clock_model_path": CLOCK_REL,
        "clock_model_sha256": authority["clock_sha256"],
        "plan_path": PLAN_REL,
        "plan_sha256": authority["plan_sha256"],
        "tool_path": str(Path(__file__).resolve().relative_to(WORKSPACE)).replace("\\", "/"),
        "tool_sha256": authority["tool_sha256"],
        "terminal": terminal_metadata,
        "files": files,
        "capabilities": {
            "symbol_identity_and_bar_history": True,
            "native_m1_m5_h1_h4": True,
            "primary_time_axis_source_epoch": True,
            "utc_nullable_only_when_flagged": True,
            "utc_exact_all_rows": not any(
                int(item["utc_ambiguous_rows"]) for item in files
            ),
            "utc_ambiguous_rows_total": int(
                sum(int(item["utc_ambiguous_rows"]) for item in files)
            ),
            "spread_column_is_cost_truth": False,
            "true_trade_side_volume": False,
            "true_cvd": False,
            "true_vpin": False,
            "lob_ofi": False,
            "tester_history_quality_measured": False,
            "t2_data_epoch_receipt": False,
        },
        "outcome_blind_counters": {
            "orders_submitted": 0,
            "trades_simulated": 0,
            "positions_queried": 0,
            "deals_queried": 0,
            "pnl_computed": 0,
            "profit_factor_computed": 0,
            "mfe_mae_computed": 0,
            "economics_executed": False,
            "validation_selected": False,
            "holdout_selected": False,
        },
    }
    verify_manifest_files(manifest)
    atomic_json(manifest_path, manifest)
    receipt = {
        "schema_version": "five_asset_data_export_receipt.v1",
        "dataset_id": DATASET_ID,
        "status": "EXPORT_COMPLETE_RAW_DATA_ONLY",
        "authority_path": str(Path(authority_path).relative_to(WORKSPACE)).replace("\\", "/"),
        "authority_sha256": sha256_file(authority_path),
        "manifest_path": str(manifest_path.relative_to(WORKSPACE)).replace("\\", "/"),
        "manifest_sha256": sha256_file(manifest_path),
        "published_file_count": len(files),
        "total_rows": int(sum(int(item["rows"]) for item in files)),
        "total_bytes": int(sum(int(item["bytes"]) for item in files)),
        "utc_ambiguous_rows_total": int(
            sum(int(item["utc_ambiguous_rows"]) for item in files)
        ),
        "source_exact_duplicate_rows_removed_total": int(
            sum(int(item["source_exact_duplicate_rows_removed"]) for item in files)
        ),
        "c_snapshot_before_path": str(Path(before_snapshot).relative_to(WORKSPACE)).replace("\\", "/"),
        "c_snapshot_before_sha256": sha256_file(before_snapshot),
        "orders_submitted": 0,
        "economics_executed": False,
        "t2_completion_claim": False,
        "promotion_eligible": False,
    }
    atomic_json(receipt_path, receipt)
    return receipt


def dry_run(authority_path: Path | None) -> dict[str, object]:
    authority_ok = False
    error = None
    if authority_path is not None and authority_path.exists():
        try:
            authority = json.loads(authority_path.read_text(encoding="utf-8"))
            validate_run_authority(authority)
            authority_ok = True
        except Exception as exc:  # dry-run reports blocker instead of mutating
            error = str(exc)
    return {
        "dataset_id": DATASET_ID,
        "symbols": list(SYMBOLS),
        "timeframes": list(TIMEFRAMES),
        "cutoff_utc": CUTOFF_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_root": DATA_ROOT_REL,
        "authority_valid": authority_ok,
        "execution_allowed": authority_ok,
        "blocker": error or (None if authority_ok else "run authority unavailable"),
        "mutated": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, default=WORKSPACE / AUTHORITY_REL)
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--c-snapshot-before", type=Path)
    parser.add_argument("--verify-c-snapshots", nargs=2, type=Path, metavar=("BEFORE", "AFTER"))
    parser.add_argument("--storage-receipt", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.verify_c_snapshots:
        if args.storage_receipt is None:
            raise ContractError("--storage-receipt is required for snapshot verification")
        result = compare_storage_snapshots(*args.verify_c_snapshots)
        atomic_json(args.storage_receipt, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["protected_c_roots_unchanged"] else 2
    if not args.production:
        print(json.dumps(dry_run(args.authority), sort_keys=True))
        return 0
    if args.c_snapshot_before is None:
        raise ContractError("--c-snapshot-before is required for production")
    receipt = run_production(args.authority, args.c_snapshot_before)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
