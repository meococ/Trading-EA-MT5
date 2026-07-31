"""Prepare physically isolated H1 source packets for TrendStack HYP-002.

This is a read-only source process. It can request broker H1 bars and create
hash-bound raw shards and decision packets. It has no order, execution,
economic-evaluation, or strategy-performance surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


WORKSPACE = Path(__file__).resolve().parents[3]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from fivepercent_server_clock import server_offset_hours, server_to_utc  # noqa: E402


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
PLAN_REL = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "HYP-TRENDSTACK-EURUSD-H1-002_SOURCE_PLAN.md"
)
PLAN_SHA256 = "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
CLOCK_REL = "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
DATA_ROOT_REL = "02. AlphaFactory/data/fivepercent/EURUSD/trendstack_002"

EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY = "Five Percent Online Ltd"
SYMBOL = "EURUSD"
EXPECTED_DIGITS = 5
EXPECTED_POINT = 0.00001

SOURCE_START = pd.Timestamp("2015-01-02T00:00:00Z")
DESIGN_START = pd.Timestamp("2016-01-04T00:00:00Z")
VALIDATION_START = pd.Timestamp("2021-01-01T00:00:00Z")
HOLDOUT_START = pd.Timestamp("2023-01-01T00:00:00Z")
FROZEN_DATA_ROOT = (WORKSPACE / DATA_ROOT_REL).resolve()

RAW_COLUMNS = [
    "time_server",
    "time_utc",
    "utc_offset_h",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
    "request_id",
]
PACKET_ALLOWLIST = {
    "schema_version",
    "hypothesis_id",
    "opportunity_id",
    "split",
    "decision_cutoff_utc",
    "m252_direction",
    "m6_direction",
    "alignment",
    "atr20",
    "control_m252_eligible",
    "control_m6_eligible",
    "challenger_stack_eligible",
    "negative_disagree_eligible",
    "exclusion_reason",
    "valid_prior_close_count",
    "max_source_time_utc",
    "source_shard_chain_hashes",
    "source_chain_sha256",
    "extractor_sha256",
    "source_plan_sha256",
    "packet_payload_sha256",
}
FORBIDDEN_PACKET_KEYS = {
    "open",
    "high",
    "low",
    "close",
    "return",
    "pnl",
    "profit",
    "exit",
    "mfe",
    "mae",
    "future_price",
    "entry_price",
    "login",
    "password",
    "credential",
}
FORBIDDEN_PACKET_SUBSTRINGS = (
    "pnl",
    "profit",
    "future_price",
    "entry_price",
    "exit_price",
    "mfe",
    "mae",
    "credential",
    "password",
)
PACKET_SPLITS = {"DESIGN", "VALIDATION_FEATURE_ONLY"}
PACKET_EXCLUSION_REASONS = {
    None,
    "INSUFFICIENT_M252_HISTORY",
    "M252_EQUALITY",
    "MISSING_SIX_HOUR_BAR",
    "INSUFFICIENT_OR_INVALID_ATR20",
    "M6_EQUALITY",
    "M252_M6_DISAGREE",
}
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
REQUEST_MANIFEST_FIELDS = {
    "record_type",
    "request_id",
    "canonical_from_utc",
    "canonical_to_inclusive_utc",
    "source_end_exclusive_utc",
    "api_server_wall_from_encoded_as_utc",
    "api_server_wall_to_encoded_as_utc",
    "canonical_roundtrip_status",
    "symbol",
    "timeframe",
    "response",
    "runtime_hashes",
}
REQUEST_RESPONSE_FIELDS = {
    "rows",
    "first_server_time",
    "last_server_time",
    "first_utc_time",
    "last_utc_time",
    "duplicate_utc_opens",
    "gap_count",
    "maximum_gap_hours",
    "gap_multiple_status",
    "geometry_status",
    "holdout_rows_received",
}
REQUEST_CHUNK_FIELDS = (
    "request_id",
    "canonical_from_utc",
    "canonical_to_inclusive_utc",
    "source_end_exclusive_utc",
    "api_server_wall_from_encoded_as_utc",
    "api_server_wall_to_encoded_as_utc",
    "canonical_roundtrip_status",
)
SHARD_MANIFEST_FIELDS = {
    "record_type",
    "shard_path",
    "split",
    "date_utc",
    "segment",
    "rows",
    "bytes",
    "sha256",
    "canonical_row_content_sha256",
    "first_utc_time",
    "last_utc_time",
    "request_ids",
    "row_groups",
    "duplicate_utc_opens",
    "gap_multiple_status",
    "geometry_status",
    "holdout_rows_received",
    "runtime_hashes",
}
RUNTIME_PROVENANCE_FIELDS = {
    "terminal_executable_label",
    "terminal_executable_sha256",
    "terminal_build",
    "python_executable_label",
    "python_executable_sha256",
    "metatrader5_version",
    "metatrader5_native_module_label",
    "metatrader5_native_module_sha256",
    "clock_tool_label",
    "clock_tool_sha256",
    "extractor_label",
    "extractor_sha256",
    "source_plan_label",
    "source_plan_sha256",
    "account_guard",
    "pandas_version",
    "pyarrow_version",
}
RUNTIME_HASH_FIELDS = {
    "terminal_executable_sha256",
    "python_executable_sha256",
    "metatrader5_native_module_sha256",
    "clock_tool_sha256",
    "extractor_sha256",
    "source_plan_sha256",
}
ACCOUNT_GUARD_FIELDS = {
    "terminal_build",
    "terminal_trade_allowed",
    "account_mode",
    "server",
    "company",
    "symbol",
    "symbol_digits",
    "symbol_point",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validate_output_root(
    output_root: Path, frozen_root: Path = FROZEN_DATA_ROOT
) -> Path:
    resolved = Path(output_root).resolve()
    frozen = Path(frozen_root).resolve()
    if resolved != frozen and frozen not in resolved.parents:
        raise RuntimeError(
            f"INVALID_ENGINEERING output root escapes frozen root: {resolved}"
        )
    if Path(output_root).exists() and Path(output_root).is_symlink():
        raise RuntimeError("INVALID_ENGINEERING output root may not be a symlink")
    return resolved


def _safe_relative_path(root: Path, relative: str) -> Path:
    logical = PurePosixPath(relative)
    if logical.is_absolute() or not logical.parts or any(
        part in {"", ".", ".."} for part in logical.parts
    ):
        raise RuntimeError(f"INVALID_ENGINEERING unsafe relative path: {relative}")
    target = (Path(root) / Path(*logical.parts)).resolve()
    resolved_root = Path(root).resolve()
    if resolved_root not in target.parents:
        raise RuntimeError(f"INVALID_ENGINEERING path escapes root: {relative}")
    return target


def create_attempt_root(
    output_root: Path, *, frozen_root: Path = FROZEN_DATA_ROOT
) -> Path:
    root = validate_output_root(output_root, frozen_root)
    root.mkdir(parents=True, exist_ok=True)
    attempts = root / "_attempts"
    attempts.mkdir(exist_ok=True)
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + secrets.token_hex(8)
    )
    attempt = attempts / run_id
    attempt.mkdir(exist_ok=False)
    return attempt


def quarantine_attempt(output_root: Path, attempt_root: Path) -> Path:
    root = Path(output_root).resolve()
    attempt = Path(attempt_root).resolve()
    if root not in attempt.parents or attempt.parent.name != "_attempts":
        raise RuntimeError("INVALID_ENGINEERING invalid attempt quarantine path")
    quarantine_parent = root / "quarantine"
    quarantine_parent.mkdir(exist_ok=True)
    destination = quarantine_parent / attempt.name
    os.rename(attempt, destination)
    attempts_parent = root / "_attempts"
    if attempts_parent.exists() and not any(attempts_parent.iterdir()):
        attempts_parent.rmdir()
    return destination


def publish_attempt(output_root: Path, attempt_root: Path) -> None:
    root = Path(output_root).resolve()
    attempt = Path(attempt_root).resolve()
    expected = {
        "raw_h1",
        "source_manifest.jsonl",
        "source_validation_receipt.json",
        "decision_packets",
        "decision_packet_manifest.jsonl",
        "decision_packet_receipt.json",
    }
    observed = {child.name for child in attempt.iterdir()}
    if observed != expected:
        raise RuntimeError(
            f"INVALID_ENGINEERING attempt artifact set mismatch: {sorted(observed)}"
        )
    published: list[Path] = []
    try:
        for name in sorted(expected):
            source = attempt / name
            target = root / name
            os.rename(source, target)
            published.append(target)
        attempt.rmdir()
        attempts_parent = root / "_attempts"
        if attempts_parent.exists() and not any(attempts_parent.iterdir()):
            attempts_parent.rmdir()
    except Exception:
        quarantine_parent = root / "quarantine"
        quarantine_parent.mkdir(exist_ok=True)
        destination = quarantine_parent / attempt.name
        destination.mkdir(exist_ok=False)
        for target in published:
            os.rename(target, destination / target.name)
        if attempt.exists():
            os.rename(attempt, destination / "attempt_remaining")
        attempts_parent = root / "_attempts"
        if attempts_parent.exists() and not any(attempts_parent.iterdir()):
            attempts_parent.rmdir()
        raise


def _as_utc(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp


def utc_to_server_api_datetime(value: datetime) -> datetime:
    """Encode a canonical UTC boundary as MT5 server-wall epoch."""
    utc = _as_utc(value)
    naive_utc = utc.tz_localize(None).to_pydatetime()
    matches: list[datetime] = []
    for offset in (2, 3):
        server = naive_utc + timedelta(hours=offset)
        if server_to_utc(server) == naive_utc:
            matches.append(server)
    if len(matches) != 1:
        raise RuntimeError(
            f"INVALID_ENGINEERING clock boundary ambiguity utc={utc.isoformat()} matches={len(matches)}"
        )
    return matches[0].replace(tzinfo=timezone.utc)


def _next_month(timestamp: pd.Timestamp) -> pd.Timestamp:
    if timestamp.month == 12:
        return pd.Timestamp(datetime(timestamp.year + 1, 1, 1, tzinfo=timezone.utc))
    return pd.Timestamp(datetime(timestamp.year, timestamp.month + 1, 1, tzinfo=timezone.utc))


def month_chunks(
    start: Any = SOURCE_START, end_exclusive: Any = HOLDOUT_START
) -> list[dict]:
    start = _as_utc(start)
    end_exclusive = _as_utc(end_exclusive)
    if not SOURCE_START <= start < end_exclusive <= HOLDOUT_START:
        raise ValueError("source range is outside the frozen non-holdout contract")
    chunks: list[dict] = []
    cursor = start
    index = 1
    while cursor < end_exclusive:
        boundary = min(_next_month(cursor), end_exclusive)
        canonical_to = boundary - pd.Timedelta(seconds=1)
        api_from = pd.Timestamp(utc_to_server_api_datetime(cursor.to_pydatetime()))
        api_to = pd.Timestamp(
            utc_to_server_api_datetime(canonical_to.to_pydatetime())
        )
        roundtrip_from = pd.Timestamp(
            server_to_utc(api_from.to_pydatetime().replace(tzinfo=None)), tz="UTC"
        )
        roundtrip_to = pd.Timestamp(
            server_to_utc(api_to.to_pydatetime().replace(tzinfo=None)), tz="UTC"
        )
        if roundtrip_from != cursor or roundtrip_to != canonical_to:
            raise RuntimeError("INVALID_ENGINEERING canonical/API boundary round-trip mismatch")
        if canonical_to >= HOLDOUT_START or api_to < api_from:
            raise RuntimeError("INVALID_ENGINEERING illegal canonical request boundary")
        chunks.append(
            {
                "request_id": f"H1-{index:03d}-{cursor:%Y%m}",
                "canonical_from_utc": cursor.isoformat(),
                "canonical_to_inclusive_utc": canonical_to.isoformat(),
                "source_end_exclusive_utc": boundary.isoformat(),
                "api_server_wall_from_encoded_as_utc": api_from.isoformat(),
                "api_server_wall_to_encoded_as_utc": api_to.isoformat(),
                "canonical_roundtrip_status": "PASS",
            }
        )
        cursor = boundary
        index += 1
    return chunks


def validate_runtime_guards(
    mt5_api: Any, terminal: Any, account: Any, symbol: Any
) -> dict:
    if terminal is None or account is None or symbol is None:
        raise RuntimeError("INVALID_ENGINEERING MT5 metadata unavailable")
    if bool(terminal.trade_allowed):
        raise RuntimeError("INVALID_ENGINEERING terminal-side trading is enabled")
    if int(account.trade_mode) != int(mt5_api.ACCOUNT_TRADE_MODE_DEMO):
        raise RuntimeError("INVALID_ENGINEERING account is not DEMO")
    if str(account.server) != EXPECTED_SERVER or str(account.company) != EXPECTED_COMPANY:
        raise RuntimeError(
            "INVALID_ENGINEERING broker identity mismatch: "
            f"{account.server} / {account.company}"
        )
    if int(symbol.digits) != EXPECTED_DIGITS or not math.isclose(
        float(symbol.point), EXPECTED_POINT, abs_tol=1e-12
    ):
        raise RuntimeError("INVALID_ENGINEERING EURUSD symbol geometry mismatch")
    return {
        "terminal_build": int(terminal.build),
        "terminal_trade_allowed": False,
        "account_mode": "DEMO",
        "server": str(account.server),
        "company": str(account.company),
        "symbol": SYMBOL,
        "symbol_digits": int(symbol.digits),
        "symbol_point": float(symbol.point),
    }


def _valid_geometry(frame: pd.DataFrame) -> pd.Series:
    values = frame[["open", "high", "low", "close"]].apply(
        pd.to_numeric, errors="coerce"
    )
    finite_positive = pd.Series(
        np.isfinite(values.to_numpy()).all(axis=1)
        & (values.to_numpy() > 0).all(axis=1),
        index=frame.index,
    )
    return finite_positive & (
        (values["high"] >= values[["open", "close"]].max(axis=1))
        & (values["low"] <= values[["open", "close"]].min(axis=1))
        & (values["high"] >= values["low"])
    )


def normalize_rates(rates: Any, chunk: dict) -> tuple[pd.DataFrame, dict]:
    if rates is None or len(rates) == 0:
        raise RuntimeError(
            f"INVALID_ENGINEERING no H1 rows returned request={chunk['request_id']}"
        )
    frame = pd.DataFrame(rates)
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
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"INVALID_ENGINEERING missing H1 fields: {sorted(missing)}")
    frame["time_server"] = pd.to_datetime(frame["time"], unit="s")
    frame["utc_offset_h"] = frame["time_server"].map(
        lambda value: server_offset_hours(value.to_pydatetime().replace(tzinfo=None))
    )
    frame["time_utc"] = frame["time_server"] - pd.to_timedelta(
        frame["utc_offset_h"], unit="h"
    )
    source_start = _as_utc(chunk["canonical_from_utc"]).tz_localize(None)
    source_end = _as_utc(chunk["source_end_exclusive_utc"]).tz_localize(None)
    if not frame["time_utc"].is_monotonic_increasing:
        raise RuntimeError("INVALID_ENGINEERING non-monotonic returned UTC opens")
    duplicate_count = int(frame["time_utc"].duplicated(keep=False).sum())
    if duplicate_count:
        raise RuntimeError("INVALID_ENGINEERING duplicate returned UTC opens")
    if bool(((frame["time_utc"] < source_start) | (frame["time_utc"] >= source_end)).any()):
        raise RuntimeError("INVALID_ENGINEERING returned row outside request range")
    if bool((frame["time_utc"] >= HOLDOUT_START.tz_localize(None)).any()):
        raise RuntimeError("INVALID_ENGINEERING holdout row returned")
    on_hour = (
        frame["time_utc"].dt.minute.eq(0)
        & frame["time_utc"].dt.second.eq(0)
        & frame["time_utc"].dt.microsecond.eq(0)
    )
    if not bool(on_hour.all()):
        raise RuntimeError("INVALID_ENGINEERING non-H1 UTC open returned")
    if not bool(_valid_geometry(frame).all()):
        raise RuntimeError("INVALID_ENGINEERING invalid returned OHLC geometry")
    gaps = frame["time_utc"].diff().dropna().dt.total_seconds() / 3600.0
    if len(gaps) and not bool(((gaps > 0) & np.isclose(gaps % 1.0, 0.0)).all()):
        raise RuntimeError("INVALID_ENGINEERING H1 gap is not a positive whole-hour multiple")
    normalized = frame[
        [
            "time_server",
            "time_utc",
            "utc_offset_h",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
            "spread",
            "real_volume",
        ]
    ].copy()
    normalized["utc_offset_h"] = normalized["utc_offset_h"].astype(np.int8)
    quality = {
        "rows": int(len(normalized)),
        "first_server_time": pd.Timestamp(normalized["time_server"].iloc[0]).isoformat(),
        "last_server_time": pd.Timestamp(normalized["time_server"].iloc[-1]).isoformat(),
        "first_utc_time": pd.Timestamp(normalized["time_utc"].iloc[0]).isoformat(),
        "last_utc_time": pd.Timestamp(normalized["time_utc"].iloc[-1]).isoformat(),
        "duplicate_utc_opens": 0,
        "gap_count": int((gaps > 1).sum()) if len(gaps) else 0,
        "maximum_gap_hours": float(gaps.max()) if len(gaps) else 0.0,
        "gap_multiple_status": "PASS",
        "geometry_status": "PASS",
        "holdout_rows_received": 0,
    }
    return normalized, quality


def split_for_date(date: Any) -> str:
    date = _as_utc(date).normalize()
    if date < DESIGN_START:
        return "WARMUP"
    if date < VALIDATION_START:
        return "DESIGN"
    if date < HOLDOUT_START:
        return "VALIDATION_FEATURE_ONLY"
    raise RuntimeError("INVALID_ENGINEERING holdout date has no source split")


def canonical_row_content_sha256(frame: pd.DataFrame) -> str:
    records = []
    for row in frame[RAW_COLUMNS].to_dict(orient="records"):
        records.append(
            {
                key: (
                    pd.Timestamp(value).isoformat()
                    if key in {"time_server", "time_utc"}
                    else int(value)
                    if key in {"utc_offset_h", "tick_volume", "spread", "real_volume"}
                    else float(value)
                    if key in {"open", "high", "low", "close"}
                    else str(value)
                )
                for key, value in row.items()
            }
        )
    return sha256_bytes(b"\n".join(canonical_json_bytes(row) for row in records) + b"\n")


def write_daily_shards(
    h1: pd.DataFrame, output_root: Path, runtime_hashes: dict
) -> tuple[list[dict], dict[pd.Timestamp, dict]]:
    frame = h1.copy()
    frame["time_utc"] = pd.to_datetime(frame["time_utc"])
    frame["time_server"] = pd.to_datetime(frame["time_server"])
    frame["date_utc"] = frame["time_utc"].dt.normalize()
    planned: list[tuple[Path, pd.DataFrame, str, str, pd.Timestamp]] = []
    for date, day in frame.groupby("date_utc", sort=True):
        split = split_for_date(pd.Timestamp(date).tz_localize("UTC"))
        for segment, mask in (
            ("pre12", day["time_utc"].dt.hour < 12),
            ("post12", day["time_utc"].dt.hour >= 12),
        ):
            shard = day.loc[mask, RAW_COLUMNS].copy()
            if shard.empty:
                continue
            relative = (
                PurePosixPath("raw_h1")
                / split
                / str(pd.Timestamp(date).date())
                / f"{segment}.parquet"
            )
            path = _safe_relative_path(output_root, relative.as_posix())
            planned.append((path, shard, split, segment, pd.Timestamp(date)))

    records: list[dict] = []
    index: dict[pd.Timestamp, dict] = {}
    for path, shard, split, segment, date in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(shard, preserve_index=False)
        with path.open("xb") as stream:
            pq.write_table(
                table,
                stream,
                compression="zstd",
                row_group_size=int(len(shard)),
                write_statistics=True,
            )
        metadata = pq.ParquetFile(path).metadata
        if metadata.num_row_groups != 1:
            raise RuntimeError("INVALID_ENGINEERING raw shard row-group count is not one")
        hours = shard["time_utc"].dt.hour
        mixed = bool((hours >= 12).any()) if segment == "pre12" else bool((hours < 12).any())
        if mixed:
            raise RuntimeError("INVALID_ENGINEERING raw shard mixes pre12/post12")
        relative = path.relative_to(output_root).as_posix()
        record = {
            "record_type": "shard",
            "shard_path": relative,
            "split": split,
            "date_utc": str(date.date()),
            "segment": segment,
            "rows": int(len(shard)),
            "bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
            "canonical_row_content_sha256": canonical_row_content_sha256(shard),
            "first_utc_time": pd.Timestamp(shard["time_utc"].iloc[0]).isoformat(),
            "last_utc_time": pd.Timestamp(shard["time_utc"].iloc[-1]).isoformat(),
            "request_ids": sorted(shard["request_id"].astype(str).unique().tolist()),
            "row_groups": int(metadata.num_row_groups),
            "duplicate_utc_opens": int(shard["time_utc"].duplicated(keep=False).sum()),
            "gap_multiple_status": "PASS",
            "geometry_status": "PASS",
            "holdout_rows_received": 0,
            "runtime_hashes": runtime_hashes,
        }
        records.append(record)
        entry = index.setdefault(date, {})
        entry[f"{segment}_sha256"] = record["sha256"]
        entry[f"{segment}_path"] = relative
    return records, index


def _daily_table(h1: pd.DataFrame) -> pd.DataFrame:
    frame = h1.copy()
    frame["time_utc"] = pd.to_datetime(frame["time_utc"])
    frame["date_utc"] = frame["time_utc"].dt.normalize()
    records = []
    for date, day in frame.groupby("date_utc", sort=True):
        duplicate = int(day["time_utc"].duplicated(keep=False).sum())
        valid = (
            duplicate == 0
            and int(day["time_utc"].nunique()) >= 20
            and bool(_valid_geometry(day).all())
        )
        latest = day.iloc[-1]
        records.append(
            {
                "date_utc": pd.Timestamp(date),
                "valid": bool(valid),
                "daily_close": float(latest["close"]) if valid else np.nan,
                "close_time_utc": latest["time_utc"] if valid else pd.NaT,
            }
        )
    return pd.DataFrame(records).set_index("date_utc").sort_index()


def _decision_context(h1: pd.DataFrame) -> dict:
    frame = h1.copy()
    frame["time_utc"] = pd.to_datetime(frame["time_utc"])
    frame = frame.sort_values("time_utc", kind="mergesort").reset_index(drop=True)
    previous = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous).abs(),
            (frame["low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr20"] = true_range.rolling(20).mean()
    frame["date_utc"] = frame["time_utc"].dt.normalize()
    return {
        "frame": frame,
        "daily": _daily_table(frame),
        "by_date": {
            date: day.drop(columns="date_utc")
            for date, day in frame.groupby("date_utc", sort=True)
        },
    }


def _m252(daily: pd.DataFrame, decision_date: pd.Timestamp) -> dict:
    accepted = daily.loc[(daily.index < decision_date) & daily["valid"]]
    result = {
        "direction": None,
        "reason": None,
        "count": int(len(accepted)),
        "latest_time": None,
    }
    if len(accepted) < 253:
        result["reason"] = "INSUFFICIENT_M252_HISTORY"
        return result
    oldest = float(accepted.iloc[-253]["daily_close"])
    latest = float(accepted.iloc[-1]["daily_close"])
    result["latest_time"] = pd.Timestamp(accepted.iloc[-1]["close_time_utc"])
    if latest == oldest:
        result["direction"] = 0
        result["reason"] = "M252_EQUALITY"
    else:
        result["direction"] = 1 if latest > oldest else -1
    return result


def _m6(day: pd.DataFrame, decision_date: pd.Timestamp) -> dict:
    selected = []
    for hour in range(6, 12):
        target = decision_date + pd.Timedelta(hours=hour)
        matched = day.loc[day["time_utc"] == target]
        if len(matched) == 0:
            return {"direction": None, "reason": "MISSING_SIX_HOUR_BAR", "latest_time": None}
        if len(matched) != 1:
            return {"direction": None, "reason": "DUPLICATE_SIX_HOUR_BAR", "latest_time": None}
        selected.append(matched.iloc[0])
    six = pd.DataFrame(selected)
    if not bool(_valid_geometry(six).all()):
        return {"direction": None, "reason": "INVALID_SIX_HOUR_OHLC", "latest_time": None}
    first_open = float(six.iloc[0]["open"])
    last_close = float(six.iloc[-1]["close"])
    direction = 0 if last_close == first_open else (1 if last_close > first_open else -1)
    return {
        "direction": direction,
        "reason": "M6_EQUALITY" if direction == 0 else None,
        "latest_time": pd.Timestamp(six.iloc[-1]["time_utc"]),
    }


def _atr20(context: dict, decision_date: pd.Timestamp) -> dict:
    source_time = decision_date + pd.Timedelta(hours=11)
    matched = context["frame"].loc[context["frame"]["time_utc"] == source_time]
    if len(matched) == 0:
        return {"value": None, "reason": "MISSING_ATR20_SOURCE_BAR", "latest_time": None}
    if len(matched) != 1:
        return {"value": None, "reason": "DUPLICATE_ATR20_SOURCE_BAR", "latest_time": None}
    value = float(matched.iloc[0]["atr20"])
    if not np.isfinite(value) or value <= 0:
        return {"value": None, "reason": "INSUFFICIENT_OR_INVALID_ATR20", "latest_time": None}
    return {"value": value, "reason": None, "latest_time": source_time}


def scan_packet_forbidden(packet: dict) -> list[str]:
    failures: list[str] = []
    unknown = set(packet) - PACKET_ALLOWLIST
    if unknown:
        failures.append(f"unknown_fields={sorted(unknown)}")

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = str(key).lower()
                child_path = f"{path}.{key}" if path else str(key)
                if lowered in FORBIDDEN_PACKET_KEYS or any(
                    token in lowered for token in FORBIDDEN_PACKET_SUBSTRINGS
                ):
                    failures.append(f"forbidden_field={child_path}")
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str):
            lowered_value = value.lower()
            forbidden_words = (
                "m1",
                "outcome",
                "pnl",
                "profit",
                "return",
                "mfe",
                "mae",
                "exit",
                "holdout",
                "raw_ohlc",
                "credential",
                "password",
            )
            if any(re.search(rf"(^|[^a-z0-9]){word}([^a-z0-9]|$)", lowered_value) for word in forbidden_words):
                failures.append(f"forbidden_value={path}")
            if (
                re.match(r"^[a-zA-Z]:[\\/]", value)
                or value.startswith(("/", "\\", "file://"))
                or "..\\" in value
                or "../" in value
            ):
                failures.append(f"local_or_absolute_path_value={path}")

    walk(packet)
    return sorted(set(failures))


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def validate_packet_schema(
    packet: dict, *, require_payload_hash: bool = True
) -> list[str]:
    failures = scan_packet_forbidden(packet)
    expected = set(PACKET_ALLOWLIST)
    if not require_payload_hash:
        expected.remove("packet_payload_sha256")
    missing = expected - set(packet)
    extra = set(packet) - expected
    if missing:
        failures.append(f"missing_fields={sorted(missing)}")
    if extra:
        failures.append(f"extra_fields={sorted(extra)}")
    if missing or extra:
        return sorted(set(failures))

    if packet["schema_version"] != "trendstack_002_decision_packet.v1":
        failures.append("invalid_schema_version")
    if packet["hypothesis_id"] != HYPOTHESIS_ID:
        failures.append("invalid_hypothesis_id")
    if type(packet["split"]) is not str or packet["split"] not in PACKET_SPLITS:
        failures.append("invalid_split")
    opportunity: pd.Timestamp | None = None
    cutoff: pd.Timestamp | None = None
    max_source: pd.Timestamp | None = None
    try:
        if type(packet["opportunity_id"]) is not str:
            raise TypeError("opportunity_id must be a string")
        opportunity = pd.Timestamp(packet["opportunity_id"])
        if opportunity.tzinfo is not None:
            opportunity = opportunity.tz_convert("UTC").tz_localize(None)
        if str(opportunity.date()) != packet["opportunity_id"]:
            failures.append("invalid_opportunity_id")
        if not DESIGN_START.tz_localize(None) <= opportunity < HOLDOUT_START.tz_localize(None):
            failures.append("opportunity_outside_frozen_range")
        expected_split = (
            "DESIGN"
            if opportunity < VALIDATION_START.tz_localize(None)
            else "VALIDATION_FEATURE_ONLY"
        )
        if packet["split"] != expected_split:
            failures.append("split_date_mismatch")
        if type(packet["decision_cutoff_utc"]) is not str:
            raise TypeError("decision_cutoff_utc must be a string")
        cutoff = _as_utc(packet["decision_cutoff_utc"]).tz_localize(None)
        expected_cutoff = opportunity.normalize() + pd.Timedelta(hours=12)
        if cutoff != expected_cutoff:
            failures.append("invalid_decision_cutoff")
        if packet["max_source_time_utc"] is not None:
            if type(packet["max_source_time_utc"]) is not str:
                raise TypeError("max_source_time_utc must be a string or null")
            max_source = _as_utc(packet["max_source_time_utc"]).tz_localize(None)
            if max_source >= cutoff:
                failures.append("noncausal_max_source_time")
            if (
                max_source < SOURCE_START.tz_localize(None)
                or max_source.normalize() > opportunity
                or max_source.minute != 0
                or max_source.second != 0
                or max_source.microsecond != 0
            ):
                failures.append("invalid_max_source_time_relation")
    except (TypeError, ValueError, OverflowError):
        failures.append("invalid_packet_timestamp")
    for field in ("m252_direction", "m6_direction"):
        value = packet[field]
        if value is not None and (type(value) is not int or value not in (-1, 0, 1)):
            failures.append(f"invalid_{field}")
    if packet["alignment"] is not None and type(packet["alignment"]) is not bool:
        failures.append("invalid_alignment_type")
    atr = packet["atr20"]
    if atr is not None and (
        type(atr) not in (int, float) or isinstance(atr, bool) or not math.isfinite(atr) or atr <= 0
    ):
        failures.append("invalid_atr20")
    bool_fields = (
        "control_m252_eligible",
        "control_m6_eligible",
        "challenger_stack_eligible",
        "negative_disagree_eligible",
    )
    for field in bool_fields:
        if type(packet[field]) is not bool:
            failures.append(f"invalid_{field}_type")
    if type(packet["valid_prior_close_count"]) is not int or packet["valid_prior_close_count"] < 0:
        failures.append("invalid_valid_prior_close_count")
    if type(packet["exclusion_reason"]) not in (str, type(None)):
        failures.append("invalid_exclusion_reason_type")
    elif packet["exclusion_reason"] not in PACKET_EXCLUSION_REASONS:
        failures.append("invalid_exclusion_reason")
    m252 = packet["m252_direction"]
    m6 = packet["m6_direction"]
    count = packet["valid_prior_close_count"]
    if type(count) is int and count >= 0:
        if m252 in (-1, 0, 1) and count < 253:
            failures.append("m252_direction_requires_253_closes")
        if m252 is None and count >= 253:
            failures.append("missing_m252_direction_with_sufficient_history")
        if opportunity is not None:
            available_prior_calendar_dates = max(
                0,
                int(
                    (
                        opportunity.normalize() - SOURCE_START.tz_localize(None).normalize()
                    ).days
                ),
            )
            if count > available_prior_calendar_dates:
                failures.append("valid_prior_close_count_exceeds_calendar_bound")

    expected_alignment = (
        bool(m252 == m6) if m252 in (-1, 1) and m6 in (-1, 1) else None
    )
    if packet["alignment"] != expected_alignment:
        failures.append("alignment_direction_mismatch")

    atr_complete = type(atr) in (int, float) and not isinstance(atr, bool) and math.isfinite(atr) and atr > 0
    feature_complete = bool(m252 in (-1, 1) and m6 in (-1, 0, 1) and atr_complete)
    expected_control_m252 = feature_complete
    expected_control_m6 = bool(feature_complete and m6 in (-1, 1))
    expected_challenger = bool(expected_control_m6 and m252 == m6)
    expected_disagree = bool(expected_control_m6 and m252 == -m6)
    expected_flags = {
        "control_m252_eligible": expected_control_m252,
        "control_m6_eligible": expected_control_m6,
        "challenger_stack_eligible": expected_challenger,
        "negative_disagree_eligible": expected_disagree,
    }
    for field, expected_value in expected_flags.items():
        if packet[field] != expected_value:
            failures.append(f"{field.removesuffix('_eligible')}_eligibility_mismatch")

    allowed_exclusions: set[str | None]
    if m252 is None and type(count) is int and count < 253:
        allowed_exclusions = {"INSUFFICIENT_M252_HISTORY"}
    elif m252 == 0:
        allowed_exclusions = {"M252_EQUALITY"}
    elif m252 in (-1, 1) and m6 is None:
        allowed_exclusions = {"MISSING_SIX_HOUR_BAR"}
    elif m252 in (-1, 1) and m6 in (-1, 0, 1) and not atr_complete:
        allowed_exclusions = {"INSUFFICIENT_OR_INVALID_ATR20"}
    elif m252 in (-1, 1) and m6 == 0:
        allowed_exclusions = {"M6_EQUALITY"}
    elif m252 in (-1, 1) and m6 == -m252:
        allowed_exclusions = {"M252_M6_DISAGREE"}
    elif m252 in (-1, 1) and m6 == m252:
        allowed_exclusions = {None}
    else:
        allowed_exclusions = set()
    if packet["exclusion_reason"] not in allowed_exclusions:
        failures.append("exclusion_reason_mismatch")

    chain = packet["source_shard_chain_hashes"]
    if not isinstance(chain, dict) or set(chain) != {
        "prior_completed_shards_sha256",
        "current_pre12_sha256",
    }:
        failures.append("invalid_source_shard_chain_schema")
    else:
        if not _is_sha256(chain["prior_completed_shards_sha256"]):
            failures.append("invalid_prior_chain_sha256")
        if chain["current_pre12_sha256"] is not None and not _is_sha256(
            chain["current_pre12_sha256"]
        ):
            failures.append("invalid_current_pre12_sha256")
        if packet["source_chain_sha256"] != sha256_bytes(canonical_json_bytes(chain)):
            failures.append("source_chain_sha256_mismatch")
        current_feature_exists = bool(m6 is not None or atr_complete)
        expected_current_max = (
            opportunity + pd.Timedelta(hours=11) if opportunity is not None else None
        )
        if (
            chain["current_pre12_sha256"] is None
            or max_source is None
            or opportunity is None
            or max_source.normalize() != opportunity
        ):
            failures.append("causal_source_evidence_required")
        if current_feature_exists:
            if chain["current_pre12_sha256"] is None:
                failures.append("current_feature_requires_current_pre12_sha256")
            if max_source != expected_current_max:
                failures.append("current_feature_max_source_mismatch")
                if atr_complete:
                    failures.append("atr20_source_time_mismatch")
    for field in ("source_chain_sha256", "extractor_sha256", "source_plan_sha256"):
        if not _is_sha256(packet[field]):
            failures.append(f"invalid_{field}")
    if packet["source_plan_sha256"] != PLAN_SHA256:
        failures.append("source_plan_sha256_mismatch")
    if require_payload_hash:
        if not _is_sha256(packet["packet_payload_sha256"]):
            failures.append("invalid_packet_payload_sha256")
        else:
            unhashed = dict(packet)
            observed = unhashed.pop("packet_payload_sha256")
            if sha256_bytes(canonical_json_bytes(unhashed)) != observed:
                failures.append("packet_payload_sha256_mismatch")
    return sorted(set(failures))


def _derive_causal_source_fields(
    h1: pd.DataFrame,
    shard_index: dict[pd.Timestamp, dict],
    decision_date: Any,
    prior_chain_sha256: str,
    *,
    context: dict,
) -> tuple[dict[str, str], pd.Timestamp]:
    decision_date = pd.Timestamp(decision_date).normalize()
    cutoff = decision_date + pd.Timedelta(hours=12)
    if not _is_sha256(prior_chain_sha256):
        raise RuntimeError("INVALID_ENGINEERING invalid builder prior shard chain")
    normalized_index = {
        pd.Timestamp(date).normalize(): shards for date, shards in shard_index.items()
    }
    current = normalized_index.get(decision_date, {})
    current_pre12_sha256 = current.get("pre12_sha256")
    if not _is_sha256(current_pre12_sha256):
        raise RuntimeError(
            "INVALID_ENGINEERING decision date has no verified current pre12 shard"
        )

    frame = context["frame"]
    current_source = frame.loc[
        (frame["time_utc"] >= decision_date) & (frame["time_utc"] < cutoff)
    ]
    if current_source.empty:
        raise RuntimeError(
            "INVALID_ENGINEERING current pre12 shard has no causal source row"
        )
    max_source = pd.Timestamp(current_source["time_utc"].max())
    if (
        max_source.normalize() != decision_date
        or max_source >= cutoff
        or max_source.minute != 0
        or max_source.second != 0
        or max_source.microsecond != 0
    ):
        raise RuntimeError("INVALID_ENGINEERING invalid builder-derived source timestamp")

    accepted_prior_dates = context["daily"].loc[
        (context["daily"].index < decision_date) & context["daily"]["valid"]
    ].index
    for prior_date in accepted_prior_dates:
        shards = normalized_index.get(pd.Timestamp(prior_date).normalize(), {})
        if not _is_sha256(shards.get("pre12_sha256")) or not _is_sha256(
            shards.get("post12_sha256")
        ):
            raise RuntimeError(
                "INVALID_ENGINEERING M252 source date is absent from bound shard chain"
            )
    return (
        {
            "prior_completed_shards_sha256": prior_chain_sha256,
            "current_pre12_sha256": current_pre12_sha256,
        },
        max_source,
    )


def _derive_feature_projection(
    context: dict, decision_date: Any
) -> tuple[dict, list[pd.Timestamp]]:
    decision_date = pd.Timestamp(decision_date).normalize()
    day = context["by_date"].get(
        decision_date,
        pd.DataFrame(columns=["time_utc", "open", "high", "low", "close"]),
    )
    m252 = _m252(context["daily"], decision_date)
    m6 = _m6(day, decision_date)
    atr = _atr20(context, decision_date)
    if m252["direction"] not in (-1, 1):
        base_reason = m252["reason"]
    elif m6["direction"] is None:
        base_reason = m6["reason"]
    elif atr["reason"] is not None:
        base_reason = atr["reason"]
    else:
        base_reason = None
    base = base_reason is None
    control_m252 = bool(base and m252["direction"] in (-1, 1))
    control_m6 = bool(base and m6["direction"] in (-1, 1))
    challenger = bool(control_m252 and control_m6 and m252["direction"] == m6["direction"])
    disagree = bool(control_m252 and control_m6 and m252["direction"] == -m6["direction"])
    if base_reason:
        exclusion = base_reason
    elif m6["direction"] == 0:
        exclusion = "M6_EQUALITY"
    elif disagree:
        exclusion = "M252_M6_DISAGREE"
    else:
        exclusion = None
    source_times = [
        pd.Timestamp(value)
        for value in (m252["latest_time"], m6["latest_time"], atr["latest_time"])
        if value is not None
    ]
    return {
        "m252_direction": m252["direction"],
        "m6_direction": m6["direction"],
        "alignment": (
            bool(m252["direction"] == m6["direction"])
            if m252["direction"] in (-1, 1) and m6["direction"] in (-1, 1)
            else None
        ),
        "atr20": atr["value"],
        "control_m252_eligible": control_m252,
        "control_m6_eligible": control_m6,
        "challenger_stack_eligible": challenger,
        "negative_disagree_eligible": disagree,
        "exclusion_reason": exclusion,
        "valid_prior_close_count": m252["count"],
    }, source_times


def packet_set_sha256(payloads: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for relative, payload in sorted(payloads.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
    return digest.hexdigest().upper()


def write_packet_files(
    payloads: dict[str, bytes], output_root: Path
) -> list[dict]:
    root = Path(output_root) / "decision_packets"
    planned = [
        (_safe_relative_path(root, relative), relative, payload)
        for relative, payload in sorted(payloads.items())
    ]
    records = []
    for path, relative, payload in planned:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)
        records.append(
            {
                "packet_path": relative,
                "packet_file_sha256": sha256_file(path),
                "packet_bytes": int(path.stat().st_size),
            }
        )
    return records


def _chain_update(previous: str, date: pd.Timestamp, shards: dict) -> str:
    payload = {
        "previous": previous,
        "date_utc": str(date.date()),
        "pre12_sha256": shards.get("pre12_sha256"),
        "post12_sha256": shards.get("post12_sha256"),
    }
    return sha256_bytes(canonical_json_bytes(payload))


def build_packet_set(
    h1: pd.DataFrame,
    shard_index: dict[pd.Timestamp, dict],
    extractor_sha256: str,
    plan_sha256: str,
    decision_dates: list[Any] | pd.DatetimeIndex | None = None,
) -> tuple[dict[str, bytes], list[dict]]:
    context = _decision_context(h1)
    shard_dates = sorted(shard_index)
    shard_cursor = 0
    prior_chain = sha256_bytes(b"TRENDSTACK_002_EMPTY_SHARD_CHAIN")
    payloads: dict[str, bytes] = {}
    records: list[dict] = []
    dates = (
        pd.DatetimeIndex(
            [
                date
                for date in shard_dates
                if DESIGN_START.tz_localize(None)
                <= date
                < HOLDOUT_START.tz_localize(None)
                and _is_sha256(shard_index[date].get("pre12_sha256"))
            ]
        )
        if decision_dates is None
        else pd.DatetimeIndex(pd.to_datetime(list(decision_dates))).sort_values()
    )
    if dates.duplicated().any():
        raise RuntimeError("INVALID_ENGINEERING duplicate decision dates")
    for decision_date in dates:
        decision_date = pd.Timestamp(decision_date).normalize()
        if not DESIGN_START.tz_localize(None) <= decision_date < HOLDOUT_START.tz_localize(None):
            raise RuntimeError("INVALID_ENGINEERING decision date outside frozen splits")
        while shard_cursor < len(shard_dates) and shard_dates[shard_cursor] < decision_date:
            date = shard_dates[shard_cursor]
            prior_chain = _chain_update(prior_chain, date, shard_index[date])
            shard_cursor += 1
        source_chain, max_source = _derive_causal_source_fields(
            h1,
            shard_index,
            decision_date,
            prior_chain,
            context=context,
        )
        split = "DESIGN" if decision_date < VALIDATION_START.tz_localize(None) else "VALIDATION_FEATURE_ONLY"
        projection, feature_source_times = _derive_feature_projection(
            context, decision_date
        )
        cutoff = decision_date + pd.Timedelta(hours=12)
        if max_source >= cutoff or any(
            source_time > max_source for source_time in feature_source_times
        ):
            raise RuntimeError(
                "INVALID_ENGINEERING feature source exceeds bound shard evidence"
            )
        packet = {
            "schema_version": "trendstack_002_decision_packet.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "opportunity_id": str(decision_date.date()),
            "split": split,
            "decision_cutoff_utc": cutoff.isoformat(),
            **projection,
            "max_source_time_utc": max_source.isoformat(),
            "source_shard_chain_hashes": source_chain,
            "source_chain_sha256": sha256_bytes(canonical_json_bytes(source_chain)),
            "extractor_sha256": extractor_sha256,
            "source_plan_sha256": plan_sha256,
        }
        failures = validate_packet_schema(packet, require_payload_hash=False)
        if failures:
            raise RuntimeError(f"INVALID_ENGINEERING builder packet schema: {failures}")
        packet["packet_payload_sha256"] = sha256_bytes(canonical_json_bytes(packet))
        failures = validate_packet_schema(packet, require_payload_hash=True)
        if failures:
            raise RuntimeError(f"INVALID_ENGINEERING finalized packet schema: {failures}")
        relative = f"{split}/{decision_date.date()}.json"
        payloads[relative] = pretty_json_bytes(packet)
        records.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "opportunity_id": packet["opportunity_id"],
                "split": split,
                "packet_path": relative,
                "packet_payload_sha256": packet["packet_payload_sha256"],
                "source_chain_sha256": packet["source_chain_sha256"],
                "max_source_time_utc": packet["max_source_time_utc"],
                "extractor_sha256": extractor_sha256,
                "source_plan_sha256": plan_sha256,
                "forbidden_field_scan": "PASS",
            }
        )
    return payloads, records


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def write_jsonl_new(path: Path, records: list[dict]) -> None:
    payload = b"".join(canonical_json_bytes(record) + b"\n" for record in records)
    _write_new(path, payload)


def write_json_new(path: Path, payload: dict) -> None:
    _write_new(path, pretty_json_bytes(payload))


def _read_jsonl(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise RuntimeError(
                f"INVALID_ENGINEERING blank JSONL row {path.name}:{line_number}"
            )
        records.append(json.loads(line))
    return records


def _logical_metadata_scan(payload: Any, path: str = "root") -> list[str]:
    failures: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            failures.extend(_logical_metadata_scan(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            failures.extend(_logical_metadata_scan(value, f"{path}[{index}]"))
    elif isinstance(payload, str):
        if (
            re.match(r"^[A-Za-z]:[\\/]", payload)
            or payload.startswith(("/", "\\", "file://"))
        ):
            failures.append(path)
    return failures


def _require_exact_manifest_fields(record: dict, expected: set[str], label: str) -> None:
    if not isinstance(record, dict) or set(record) != expected:
        observed = set(record) if isinstance(record, dict) else set()
        raise RuntimeError(
            "INVALID_ENGINEERING "
            f"{label} manifest schema mismatch missing={sorted(expected - observed)} "
            f"extra={sorted(observed - expected)}"
        )


def _validate_runtime_hashes(runtime_hashes: Any) -> None:
    if (
        not isinstance(runtime_hashes, dict)
        or set(runtime_hashes) != RUNTIME_HASH_FIELDS
        or any(not _is_sha256(value) for value in runtime_hashes.values())
        or runtime_hashes.get("source_plan_sha256") != PLAN_SHA256
        or runtime_hashes.get("clock_tool_sha256")
        != sha256_file(WORKSPACE / CLOCK_REL)
        or runtime_hashes.get("extractor_sha256") != sha256_file(Path(__file__))
    ):
        raise RuntimeError("INVALID_ENGINEERING invalid manifest runtime hashes")


def validate_runtime_provenance(runtime: Any) -> None:
    if not isinstance(runtime, dict) or set(runtime) != RUNTIME_PROVENANCE_FIELDS:
        raise RuntimeError("INVALID_ENGINEERING runtime provenance schema mismatch")
    runtime_hashes = {key: runtime[key] for key in RUNTIME_HASH_FIELDS}
    try:
        _validate_runtime_hashes(runtime_hashes)
    except RuntimeError as exc:
        raise RuntimeError("INVALID_ENGINEERING runtime provenance hash mismatch") from exc

    exact_labels = {
        "terminal_executable_label": "terminal64.exe",
        "clock_tool_label": Path(CLOCK_REL).name,
        "extractor_label": Path(__file__).name,
        "source_plan_label": Path(PLAN_REL).name,
    }
    for field, expected in exact_labels.items():
        if runtime[field] != expected:
            raise RuntimeError("INVALID_ENGINEERING runtime provenance label mismatch")
    for field in (
        "python_executable_label",
        "metatrader5_native_module_label",
    ):
        label = runtime[field]
        if (
            type(label) is not str
            or not label
            or Path(label).name != label
            or "/" in label
            or "\\" in label
        ):
            raise RuntimeError("INVALID_ENGINEERING runtime provenance label mismatch")
    for field in (
        "metatrader5_version",
        "pandas_version",
        "pyarrow_version",
    ):
        if type(runtime[field]) is not str or not runtime[field]:
            raise RuntimeError("INVALID_ENGINEERING runtime provenance version mismatch")

    guard = runtime["account_guard"]
    if not isinstance(guard, dict) or set(guard) != ACCOUNT_GUARD_FIELDS:
        raise RuntimeError("INVALID_ENGINEERING runtime provenance account-guard schema mismatch")
    if (
        type(runtime["terminal_build"]) is not int
        or runtime["terminal_build"] <= 0
        or guard["terminal_build"] != runtime["terminal_build"]
        or guard["terminal_trade_allowed"] is not False
        or guard["account_mode"] != "DEMO"
        or guard["server"] != EXPECTED_SERVER
        or guard["company"] != EXPECTED_COMPANY
        or guard["symbol"] != SYMBOL
        or guard["symbol_digits"] != EXPECTED_DIGITS
        or type(guard["symbol_point"]) not in (int, float)
        or isinstance(guard["symbol_point"], bool)
        or not math.isclose(float(guard["symbol_point"]), EXPECTED_POINT, abs_tol=1e-12)
    ):
        raise RuntimeError("INVALID_ENGINEERING runtime provenance account-guard mismatch")
    if _logical_metadata_scan(runtime):
        raise RuntimeError("INVALID_ENGINEERING runtime provenance contains local/absolute path")


def _validate_frozen_request_universe(request_records: list[dict]) -> None:
    expected_chunks = month_chunks()
    if len(expected_chunks) != 96:
        raise RuntimeError("INVALID_ENGINEERING frozen request universe is not 96 chunks")
    if any(not isinstance(record, dict) for record in request_records):
        raise RuntimeError("INVALID_ENGINEERING request universe contains non-object record")
    expected_ids = [chunk["request_id"] for chunk in expected_chunks]
    observed_ids = [record.get("request_id") for record in request_records]
    if (
        len(request_records) != 96
        or len(set(observed_ids)) != 96
        or set(observed_ids) != set(expected_ids)
    ):
        raise RuntimeError("INVALID_ENGINEERING request universe identity/count mismatch")
    observed_by_id = {record["request_id"]: record for record in request_records}
    for chunk in expected_chunks:
        observed = observed_by_id[chunk["request_id"]]
        if any(observed.get(field) != chunk[field] for field in REQUEST_CHUNK_FIELDS):
            raise RuntimeError("INVALID_ENGINEERING request universe boundary/ID mismatch")

    ordered = [observed_by_id[request_id] for request_id in expected_ids]
    first_start = _manifest_utc_naive(
        ordered[0]["canonical_from_utc"], "frozen request start"
    )
    final_end = _manifest_utc_naive(
        ordered[-1]["source_end_exclusive_utc"], "frozen request end"
    )
    if (
        first_start != SOURCE_START.tz_localize(None)
        or final_end != HOLDOUT_START.tz_localize(None)
    ):
        raise RuntimeError("INVALID_ENGINEERING request universe endpoint mismatch")
    for previous, current in zip(ordered, ordered[1:]):
        previous_end = _manifest_utc_naive(
            previous["source_end_exclusive_utc"], "request end"
        )
        current_start = _manifest_utc_naive(
            current["canonical_from_utc"], "request start"
        )
        if previous_end != current_start:
            raise RuntimeError("INVALID_ENGINEERING request universe gap/overlap")


def _manifest_utc_naive(value: Any, label: str) -> pd.Timestamp:
    if type(value) is not str:
        raise RuntimeError(f"INVALID_ENGINEERING {label} timestamp is not a string")
    try:
        return _as_utc(value).tz_localize(None)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError(f"INVALID_ENGINEERING invalid {label} timestamp") from exc


def _manifest_server_naive(value: Any, label: str) -> pd.Timestamp:
    if type(value) is not str:
        raise RuntimeError(f"INVALID_ENGINEERING {label} timestamp is not a string")
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError(f"INVALID_ENGINEERING invalid {label} timestamp") from exc
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp


def reopen_validate_shards(
    output_root: Path,
) -> tuple[pd.DataFrame, dict[pd.Timestamp, dict], dict]:
    root = Path(output_root).resolve()
    manifest_path = _safe_relative_path(root, "source_manifest.jsonl")
    records = _read_jsonl(manifest_path)
    if any(not isinstance(record, dict) for record in records):
        raise RuntimeError("INVALID_ENGINEERING source manifest row is not an object")
    if any(record.get("record_type") not in {"request", "shard"} for record in records):
        raise RuntimeError("INVALID_ENGINEERING unknown source manifest record type")
    request_records = [record for record in records if record.get("record_type") == "request"]
    shard_records = [record for record in records if record.get("record_type") == "shard"]
    if not request_records:
        raise RuntimeError("INVALID_ENGINEERING source manifest contains no requests")
    if not shard_records:
        raise RuntimeError("INVALID_ENGINEERING source manifest contains no shards")
    _validate_frozen_request_universe(request_records)

    request_contracts: dict[str, dict] = {}
    runtime_contract: dict | None = None
    for record in request_records:
        _require_exact_manifest_fields(record, REQUEST_MANIFEST_FIELDS, "request")
        request_id = record["request_id"]
        if type(request_id) is not str or not request_id or request_id in request_contracts:
            raise RuntimeError("INVALID_ENGINEERING duplicate/invalid request manifest record")
        if record["symbol"] != SYMBOL or record["timeframe"] != "H1":
            raise RuntimeError("INVALID_ENGINEERING request symbol/timeframe mismatch")
        if record["canonical_roundtrip_status"] != "PASS":
            raise RuntimeError("INVALID_ENGINEERING request boundary round-trip not PASS")
        _validate_runtime_hashes(record["runtime_hashes"])
        if runtime_contract is None:
            runtime_contract = record["runtime_hashes"]
        elif record["runtime_hashes"] != runtime_contract:
            raise RuntimeError("INVALID_ENGINEERING request runtime hash drift")

        canonical_from = _manifest_utc_naive(
            record["canonical_from_utc"], "canonical request start"
        )
        canonical_to = _manifest_utc_naive(
            record["canonical_to_inclusive_utc"], "canonical request ceiling"
        )
        source_end = _manifest_utc_naive(
            record["source_end_exclusive_utc"], "canonical request end"
        )
        if (
            canonical_from < SOURCE_START.tz_localize(None)
            or canonical_from >= source_end
            or canonical_to != source_end - pd.Timedelta(seconds=1)
            or source_end > HOLDOUT_START.tz_localize(None)
        ):
            raise RuntimeError("INVALID_ENGINEERING invalid canonical request range")
        api_from = _manifest_server_naive(
            record["api_server_wall_from_encoded_as_utc"], "API request start"
        )
        api_to = _manifest_server_naive(
            record["api_server_wall_to_encoded_as_utc"], "API request ceiling"
        )
        if (
            pd.Timestamp(server_to_utc(api_from.to_pydatetime())) != canonical_from
            or pd.Timestamp(server_to_utc(api_to.to_pydatetime())) != canonical_to
        ):
            raise RuntimeError("INVALID_ENGINEERING request boundary linkage mismatch")

        response = record["response"]
        _require_exact_manifest_fields(response, REQUEST_RESPONSE_FIELDS, "request response")
        if (
            type(response["rows"]) is not int
            or response["rows"] <= 0
            or type(response["duplicate_utc_opens"]) is not int
            or response["duplicate_utc_opens"] != 0
            or type(response["gap_count"]) is not int
            or response["gap_count"] < 0
            or type(response["maximum_gap_hours"]) not in (int, float)
            or isinstance(response["maximum_gap_hours"], bool)
            or not math.isfinite(response["maximum_gap_hours"])
            or response["maximum_gap_hours"] < 0
            or response["gap_multiple_status"] != "PASS"
            or response["geometry_status"] != "PASS"
            or response["holdout_rows_received"] != 0
        ):
            raise RuntimeError("INVALID_ENGINEERING invalid request response metadata")
        response_first_utc = _manifest_utc_naive(
            response["first_utc_time"], "response first UTC"
        )
        response_last_utc = _manifest_utc_naive(
            response["last_utc_time"], "response last UTC"
        )
        response_first_server = _manifest_server_naive(
            response["first_server_time"], "response first server"
        )
        response_last_server = _manifest_server_naive(
            response["last_server_time"], "response last server"
        )
        if (
            not canonical_from <= response_first_utc <= response_last_utc < source_end
            or pd.Timestamp(server_to_utc(response_first_server.to_pydatetime()))
            != response_first_utc
            or pd.Timestamp(server_to_utc(response_last_server.to_pydatetime()))
            != response_last_utc
        ):
            raise RuntimeError("INVALID_ENGINEERING request response range/clock mismatch")
        request_contracts[request_id] = {
            "record": record,
            "canonical_from": canonical_from,
            "source_end": source_end,
        }

    ordered_requests = sorted(
        request_contracts.values(), key=lambda contract: contract["canonical_from"]
    )
    for previous, current in zip(ordered_requests, ordered_requests[1:]):
        if previous["source_end"] > current["canonical_from"]:
            raise RuntimeError("INVALID_ENGINEERING overlapping canonical request ranges")

    manifested_path_list = [record.get("shard_path") for record in shard_records]
    if any(type(path) is not str for path in manifested_path_list) or len(
        set(manifested_path_list)
    ) != len(manifested_path_list):
        raise RuntimeError("INVALID_ENGINEERING duplicate/invalid shard manifest record")
    manifested_paths = set(manifested_path_list)
    raw_root = _safe_relative_path(root, "raw_h1")
    if raw_root.is_symlink() or not raw_root.is_dir():
        raise RuntimeError("INVALID_ENGINEERING raw shard root missing or symlinked")
    physical_paths = {
        path.relative_to(root).as_posix()
        for path in raw_root.rglob("*")
        if path.is_file()
    }
    if manifested_paths != physical_paths:
        raise RuntimeError("INVALID_ENGINEERING shard manifest/file-set mismatch")

    frames: list[pd.DataFrame] = []
    index: dict[pd.Timestamp, dict] = {}
    for record in shard_records:
        _require_exact_manifest_fields(record, SHARD_MANIFEST_FIELDS, "shard")
        relative = record["shard_path"]
        logical = PurePosixPath(relative)
        # A valid shard path has raw_h1/split/date/segment.parquet (four parts).
        if (
            "\\" in relative
            or logical.as_posix() != relative
            or len(logical.parts) != 4
            or logical.parts[0] != "raw_h1"
        ):
            raise RuntimeError("INVALID_ENGINEERING invalid shard path depth")
        split, date_text, filename = logical.parts[1:]
        segment = Path(filename).stem
        if split not in {"WARMUP", "DESIGN", "VALIDATION_FEATURE_ONLY"}:
            raise RuntimeError("INVALID_ENGINEERING invalid shard split")
        if segment not in {"pre12", "post12"}:
            raise RuntimeError("INVALID_ENGINEERING invalid shard segment")
        date = pd.Timestamp(date_text)
        if date >= HOLDOUT_START.tz_localize(None):
            raise RuntimeError("INVALID_ENGINEERING holdout shard path")
        expected_split = split_for_date(date.tz_localize("UTC"))
        if split != expected_split:
            raise RuntimeError("INVALID_ENGINEERING shard split/date mismatch")
        expected_relative = (
            PurePosixPath("raw_h1") / split / str(date.date()) / f"{segment}.parquet"
        ).as_posix()
        if (
            record["split"] != split
            or record["date_utc"] != str(date.date())
            or record["segment"] != segment
            or relative != expected_relative
        ):
            raise RuntimeError("INVALID_ENGINEERING shard path/partition metadata mismatch")
        _validate_runtime_hashes(record["runtime_hashes"])
        if record["runtime_hashes"] != runtime_contract:
            raise RuntimeError("INVALID_ENGINEERING shard runtime hash drift")
        path = _safe_relative_path(root, relative)
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("INVALID_ENGINEERING shard missing or symlinked")
        if type(record["bytes"]) is not int or record["bytes"] != path.stat().st_size:
            raise RuntimeError("INVALID_ENGINEERING persisted shard byte-count mismatch")
        if sha256_file(path) != record["sha256"]:
            raise RuntimeError("INVALID_ENGINEERING persisted shard hash mismatch")
        parquet_file = pq.ParquetFile(path)
        if (
            parquet_file.metadata.num_row_groups != 1
            or record["row_groups"] != parquet_file.metadata.num_row_groups
        ):
            raise RuntimeError("INVALID_ENGINEERING persisted shard row-group mismatch")
        frame = parquet_file.read().to_pandas()
        if (
            list(frame.columns) != RAW_COLUMNS
            or type(record["rows"]) is not int
            or len(frame) != record["rows"]
        ):
            raise RuntimeError("INVALID_ENGINEERING persisted shard schema/row mismatch")
        frame["time_utc"] = pd.to_datetime(frame["time_utc"])
        frame["time_server"] = pd.to_datetime(frame["time_server"])
        if canonical_row_content_sha256(frame) != record["canonical_row_content_sha256"]:
            raise RuntimeError("INVALID_ENGINEERING persisted shard content hash mismatch")
        if frame["time_utc"].duplicated(keep=False).any() or not frame["time_utc"].is_monotonic_increasing:
            raise RuntimeError("INVALID_ENGINEERING persisted shard chronology mismatch")
        duplicate_count = int(frame["time_utc"].duplicated(keep=False).sum())
        if record["duplicate_utc_opens"] != duplicate_count:
            raise RuntimeError("INVALID_ENGINEERING shard duplicate-count mismatch")
        if not bool(_valid_geometry(frame).all()):
            raise RuntimeError("INVALID_ENGINEERING persisted shard geometry mismatch")
        if record["geometry_status"] != "PASS":
            raise RuntimeError("INVALID_ENGINEERING shard geometry status mismatch")
        if not bool((frame["time_utc"].dt.normalize() == date).all()):
            raise RuntimeError("INVALID_ENGINEERING persisted shard date partition mismatch")
        on_hour = (
            frame["time_utc"].dt.minute.eq(0)
            & frame["time_utc"].dt.second.eq(0)
            & frame["time_utc"].dt.microsecond.eq(0)
        )
        if not bool(on_hour.all()):
            raise RuntimeError("INVALID_ENGINEERING persisted shard contains non-H1 open")
        hours = frame["time_utc"].dt.hour
        if segment == "pre12" and not bool((hours < 12).all()):
            raise RuntimeError("INVALID_ENGINEERING pre12 shard contains post12 row")
        if segment == "post12" and not bool((hours >= 12).all()):
            raise RuntimeError("INVALID_ENGINEERING post12 shard contains pre12 row")
        if bool((frame["time_utc"] >= HOLDOUT_START.tz_localize(None)).any()):
            raise RuntimeError("INVALID_ENGINEERING persisted holdout row")
        holdout_rows = int((frame["time_utc"] >= HOLDOUT_START.tz_localize(None)).sum())
        if record["holdout_rows_received"] != holdout_rows:
            raise RuntimeError("INVALID_ENGINEERING shard holdout-count mismatch")
        gaps = frame["time_utc"].diff().dropna().dt.total_seconds() / 3600.0
        gap_status = (
            "PASS"
            if not len(gaps)
            or bool(((gaps > 0) & np.isclose(gaps % 1.0, 0.0)).all())
            else "FAIL"
        )
        if record["gap_multiple_status"] != gap_status:
            raise RuntimeError("INVALID_ENGINEERING shard gap status mismatch")
        observed_request_ids = sorted(frame["request_id"].astype(str).unique().tolist())
        if record["request_ids"] != observed_request_ids:
            raise RuntimeError("INVALID_ENGINEERING shard request-ID metadata mismatch")
        first_utc = pd.Timestamp(frame["time_utc"].iloc[0])
        last_utc = pd.Timestamp(frame["time_utc"].iloc[-1])
        if (
            _manifest_utc_naive(record["first_utc_time"], "shard first UTC") != first_utc
            or _manifest_utc_naive(record["last_utc_time"], "shard last UTC") != last_utc
        ):
            raise RuntimeError("INVALID_ENGINEERING shard UTC boundary mismatch")
        canonical_utc = frame["time_server"].map(
            lambda value: pd.Timestamp(server_to_utc(pd.Timestamp(value).to_pydatetime()))
        )
        canonical_offsets = frame["time_server"].map(
            lambda value: server_offset_hours(pd.Timestamp(value).to_pydatetime())
        )
        if (
            not canonical_utc.reset_index(drop=True).equals(
                frame["time_utc"].reset_index(drop=True)
            )
            or not canonical_offsets.reset_index(drop=True).equals(
                frame["utc_offset_h"].astype(int).reset_index(drop=True)
            )
        ):
            raise RuntimeError("INVALID_ENGINEERING shard server/UTC clock mismatch")
        frames.append(frame)
        entry = index.setdefault(date, {})
        entry[f"{segment}_sha256"] = record["sha256"]
        entry[f"{segment}_path"] = relative
    reconstructed = pd.concat(frames, ignore_index=True)
    if not reconstructed["time_utc"].is_monotonic_increasing:
        raise RuntimeError("INVALID_ENGINEERING reopened global chronology mismatch")
    if reconstructed["time_utc"].duplicated(keep=False).any():
        raise RuntimeError("INVALID_ENGINEERING reopened global duplicate UTC opens")
    observed_request_ids = set(reconstructed["request_id"].astype(str))
    if observed_request_ids != set(request_contracts):
        raise RuntimeError("INVALID_ENGINEERING orphan request record or source row")
    for request_id, contract in request_contracts.items():
        response = contract["record"]["response"]
        selected = reconstructed.loc[
            reconstructed["request_id"].astype(str) == request_id
        ].sort_values("time_utc", kind="mergesort")
        if len(selected) != response["rows"]:
            raise RuntimeError("INVALID_ENGINEERING request response row-count mismatch")
        first_utc = pd.Timestamp(selected["time_utc"].iloc[0])
        last_utc = pd.Timestamp(selected["time_utc"].iloc[-1])
        first_server = pd.Timestamp(selected["time_server"].iloc[0])
        last_server = pd.Timestamp(selected["time_server"].iloc[-1])
        if (
            not bool(
                (
                    (selected["time_utc"] >= contract["canonical_from"])
                    & (selected["time_utc"] < contract["source_end"])
                ).all()
            )
            or _manifest_utc_naive(response["first_utc_time"], "response first UTC")
            != first_utc
            or _manifest_utc_naive(response["last_utc_time"], "response last UTC")
            != last_utc
            or _manifest_server_naive(
                response["first_server_time"], "response first server"
            )
            != first_server
            or _manifest_server_naive(
                response["last_server_time"], "response last server"
            )
            != last_server
        ):
            raise RuntimeError("INVALID_ENGINEERING request response boundary mismatch")
        duplicate_count = int(selected["time_utc"].duplicated(keep=False).sum())
        gaps = selected["time_utc"].diff().dropna().dt.total_seconds() / 3600.0
        gap_count = int((gaps > 1).sum()) if len(gaps) else 0
        maximum_gap = float(gaps.max()) if len(gaps) else 0.0
        gap_multiple_status = (
            "PASS"
            if not len(gaps)
            or bool(((gaps > 0) & np.isclose(gaps % 1.0, 0.0)).all())
            else "FAIL"
        )
        if (
            response["duplicate_utc_opens"] != duplicate_count
            or response["gap_count"] != gap_count
            or not math.isclose(
                float(response["maximum_gap_hours"]), maximum_gap, abs_tol=1e-12
            )
            or response["gap_multiple_status"] != gap_multiple_status
            or response["geometry_status"]
            != ("PASS" if bool(_valid_geometry(selected).all()) else "FAIL")
            or response["holdout_rows_received"]
            != int((selected["time_utc"] >= HOLDOUT_START.tz_localize(None)).sum())
        ):
            raise RuntimeError("INVALID_ENGINEERING request response content mismatch")
    return reconstructed, index, {
        "physical_partition_status": "PASS",
        "shard_file_count": int(len(shard_records)),
        "source_rows": int(len(reconstructed)),
        "all_shard_hashes_verified": True,
        "all_shards_single_row_group": True,
        "no_mixed_segments": True,
        "no_2023_row_or_file": True,
    }


def persist_source_package(
    h1: pd.DataFrame,
    request_records: list[dict],
    output_root: Path,
    runtime: dict,
    *,
    decision_dates: list[Any] | pd.DatetimeIndex | None = None,
) -> dict:
    root = Path(output_root)
    validate_runtime_provenance(runtime)
    _validate_frozen_request_universe(request_records)
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("INVALID_ENGINEERING attempt root is not empty")
    logical_failures = _logical_metadata_scan(runtime)
    if logical_failures:
        raise RuntimeError(
            f"INVALID_ENGINEERING absolute runtime metadata: {logical_failures}"
        )
    root.mkdir(parents=True, exist_ok=True)
    runtime_hashes = {
        key: value for key, value in runtime.items() if key.endswith("sha256")
    }
    shard_records, shard_index = write_daily_shards(h1, root, runtime_hashes)
    normalized_requests = [
        {**record, "runtime_hashes": runtime_hashes} for record in request_records
    ]
    source_manifest_path = root / "source_manifest.jsonl"
    write_jsonl_new(source_manifest_path, normalized_requests + shard_records)

    ram_payloads, _ = build_packet_set(
        h1,
        shard_index,
        runtime["extractor_sha256"],
        PLAN_SHA256,
        decision_dates=decision_dates,
    )
    reopened_h1, reopened_index, physical = reopen_validate_shards(root)
    disk_payloads, disk_packet_records = build_packet_set(
        reopened_h1,
        reopened_index,
        runtime["extractor_sha256"],
        PLAN_SHA256,
        decision_dates=decision_dates,
    )
    if ram_payloads != disk_payloads or packet_set_sha256(ram_payloads) != packet_set_sha256(
        disk_payloads
    ):
        raise RuntimeError(
            "INVALID_ENGINEERING disk-reopened packet rebuild is not byte-identical"
        )

    source_receipt = {
        "schema_version": "trendstack_002_source_validation.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": PLAN_SHA256,
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "request_count": int(len(request_records)),
        "shard_file_count": physical["shard_file_count"],
        "source_rows": physical["source_rows"],
        "maximum_utc_timestamp": pd.Timestamp(reopened_h1["time_utc"].max()).isoformat(),
        "runtime_provenance": runtime,
        "all_shard_hashes_verified": True,
        "no_2023_canonical_request": True,
        "no_2023_row": True,
        "no_2023_file": True,
        "m1_opened": False,
        "outcomes_opened": False,
        "physical_partition_status": "PASS",
    }
    source_receipt_path = root / "source_validation_receipt.json"
    write_json_new(source_receipt_path, source_receipt)

    file_records = write_packet_files(disk_payloads, root)
    files_by_path = {record["packet_path"]: record for record in file_records}
    packet_manifest_records = [
        {**record, **files_by_path[record["packet_path"]]}
        for record in disk_packet_records
    ]
    packet_manifest_path = root / "decision_packet_manifest.jsonl"
    write_jsonl_new(packet_manifest_path, packet_manifest_records)
    packet_receipt = {
        "schema_version": "trendstack_002_decision_packet_receipt.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "source_plan_sha256": PLAN_SHA256,
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "source_validation_receipt_sha256": sha256_file(source_receipt_path),
        "decision_packet_manifest_sha256": sha256_file(packet_manifest_path),
        "packet_count": int(len(disk_payloads)),
        "unique_opportunity_ids": len(
            {record["opportunity_id"] for record in packet_manifest_records}
        )
        == len(packet_manifest_records),
        "packet_set_sha256": packet_set_sha256(disk_payloads),
        "deterministic_rebuild_status": "PASS_DISK_REOPEN",
        "forbidden_field_scan": "PASS",
        "maximum_source_time_utc": max(
            record["max_source_time_utc"] for record in packet_manifest_records
        ),
        "no_2023_packet": True,
        "m1_opened": False,
        "outcomes_opened": False,
        "holdout_opened": False,
        "economic_metrics_computed": False,
        "strategy_process_raw_source_access": "NOT_YET_VERIFIED_STAGE0_REQUIRED",
        "verdict": "SOURCE_READY_FOR_INDEPENDENT_STAGE0_REVIEW",
    }
    if _logical_metadata_scan(source_receipt) or _logical_metadata_scan(packet_receipt):
        raise RuntimeError("INVALID_ENGINEERING receipt contains local/absolute path")
    packet_receipt_path = root / "decision_packet_receipt.json"
    write_json_new(packet_receipt_path, packet_receipt)
    return packet_receipt


def runtime_provenance(
    terminal_path: Path, guard: dict, mt5_api: Any = mt5
) -> dict:
    plan_path = WORKSPACE / PLAN_REL
    clock_path = WORKSPACE / CLOCK_REL
    extractor = Path(__file__).resolve()
    python_executable = Path(sys.executable).resolve()
    native_module = Path(mt5_api._core.__file__).resolve()
    if sha256_file(plan_path) != PLAN_SHA256:
        raise RuntimeError("INVALID_ENGINEERING frozen source-plan hash mismatch")
    return {
        "terminal_executable_label": terminal_path.name,
        "terminal_executable_sha256": sha256_file(terminal_path),
        "terminal_build": guard["terminal_build"],
        "python_executable_label": python_executable.name,
        "python_executable_sha256": sha256_file(python_executable),
        "metatrader5_version": str(mt5_api.__version__),
        "metatrader5_native_module_label": native_module.name,
        "metatrader5_native_module_sha256": sha256_file(native_module),
        "clock_tool_label": Path(CLOCK_REL).name,
        "clock_tool_sha256": sha256_file(clock_path),
        "extractor_label": extractor.name,
        "extractor_sha256": sha256_file(extractor),
        "source_plan_label": Path(PLAN_REL).name,
        "source_plan_sha256": PLAN_SHA256,
        "account_guard": guard,
        "pandas_version": pd.__version__,
        "pyarrow_version": pa.__version__,
    }


def ensure_publishable_target(
    output_root: Path, frozen_root: Path = FROZEN_DATA_ROOT
) -> Path:
    root = validate_output_root(output_root, frozen_root)
    if root.exists():
        illegal = {
            child.name for child in root.iterdir() if child.name != "quarantine"
        }
        if illegal:
            raise RuntimeError(
                f"INVALID_ENGINEERING target data root has active artifacts: {sorted(illegal)}"
            )
    return root


def acquire_source(
    terminal_path: Path,
    output_root: Path,
    *,
    mt5_api: Any = mt5,
    frozen_root: Path = FROZEN_DATA_ROOT,
) -> dict:
    terminal_path = Path(terminal_path)
    output_root = ensure_publishable_target(output_root, frozen_root)
    if not terminal_path.is_file():
        raise RuntimeError("INVALID_ENGINEERING explicit terminal executable is absent")
    if sha256_file(WORKSPACE / PLAN_REL) != PLAN_SHA256:
        raise RuntimeError("INVALID_ENGINEERING frozen source-plan hash mismatch")

    try:
        initialized = bool(
            mt5_api.initialize(
                path=str(terminal_path), portable=True, timeout=60_000
            )
        )
        if not initialized:
            raise RuntimeError(
                f"INVALID_ENGINEERING MT5 initialize failed: {mt5_api.last_error()}"
            )
        terminal = mt5_api.terminal_info()
        account = mt5_api.account_info()
        symbol = mt5_api.symbol_info(SYMBOL)
        guard = validate_runtime_guards(mt5_api, terminal, account, symbol)
        runtime = runtime_provenance(terminal_path, guard, mt5_api)
        runtime_hashes = {
            key: value
            for key, value in runtime.items()
            if key.endswith("sha256")
        }

        request_records: list[dict] = []
        frames: list[pd.DataFrame] = []
        previous_last: pd.Timestamp | None = None
        for chunk in month_chunks():
            canonical_from = _as_utc(chunk["canonical_from_utc"])
            canonical_to = _as_utc(chunk["canonical_to_inclusive_utc"])
            if canonical_from >= HOLDOUT_START or canonical_to >= HOLDOUT_START:
                raise RuntimeError("INVALID_ENGINEERING attempted canonical 2023 request")
            api_from = datetime.fromisoformat(
                chunk["api_server_wall_from_encoded_as_utc"]
            )
            api_to = datetime.fromisoformat(
                chunk["api_server_wall_to_encoded_as_utc"]
            )
            if pd.Timestamp(
                server_to_utc(api_from.replace(tzinfo=None)), tz="UTC"
            ) != canonical_from or pd.Timestamp(
                server_to_utc(api_to.replace(tzinfo=None)), tz="UTC"
            ) != canonical_to:
                raise RuntimeError("INVALID_ENGINEERING request boundary round-trip drift")
            rates = mt5_api.copy_rates_range(
                SYMBOL, mt5_api.TIMEFRAME_H1, api_from, api_to
            )
            frame, quality = normalize_rates(rates, chunk)
            if previous_last is not None and pd.Timestamp(frame["time_utc"].iloc[0]) <= previous_last:
                raise RuntimeError("INVALID_ENGINEERING cross-request duplicate/non-monotonic row")
            previous_last = pd.Timestamp(frame["time_utc"].iloc[-1])
            frame["request_id"] = chunk["request_id"]
            frames.append(frame)
            request_records.append(
                {
                    "record_type": "request",
                    **chunk,
                    "symbol": SYMBOL,
                    "timeframe": "H1",
                    "response": quality,
                    "runtime_hashes": runtime_hashes,
                }
            )
        h1 = pd.concat(frames, ignore_index=True)
        if h1["time_utc"].duplicated(keep=False).any() or not h1["time_utc"].is_monotonic_increasing:
            raise RuntimeError("INVALID_ENGINEERING global source chronology failure")
        if bool((h1["time_utc"] >= HOLDOUT_START.tz_localize(None)).any()):
            raise RuntimeError("INVALID_ENGINEERING global holdout row received")
        attempt = create_attempt_root(output_root, frozen_root=frozen_root)
        try:
            receipt = persist_source_package(
                h1, request_records, attempt, runtime
            )
            publish_attempt(output_root, attempt)
            return receipt
        except Exception:
            if attempt.exists():
                quarantine_attempt(output_root, attempt)
            raise
    finally:
        # The API shutdown call is idempotent and is attempted even when
        # initialize returned false or metadata/guard validation raised.
        mt5_api.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=WORKSPACE / DATA_ROOT_REL)
    args = parser.parse_args()
    try:
        receipt = acquire_source(args.terminal, args.output_root)
    except (RuntimeError, FileExistsError) as exc:
        print(json.dumps({"verdict": "INVALID_ENGINEERING", "reason": str(exc)}))
        return 2
    print(
        json.dumps(
            {
                "verdict": receipt["verdict"],
                "packet_count": receipt["packet_count"],
                "packet_set_sha256": receipt["packet_set_sha256"],
                "outcomes_opened": receipt["outcomes_opened"],
                "holdout_opened": receipt["holdout_opened"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
