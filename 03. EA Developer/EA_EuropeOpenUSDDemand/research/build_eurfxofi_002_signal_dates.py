#!/usr/bin/env python3
"""Build the clock-corrected, outcome-blind signal-date ledger for HYP002."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-002"
ATTEMPT_ID = "EURFXOFI002-SIGNAL-DATE-SELECTION-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-002_SOURCE_PLAN.md"
TOOL_REL = BASE_REL + "build_eurfxofi_002_signal_dates.py"
TEST_REL = BASE_REL + "tests/test_build_eurfxofi_002_signal_dates.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
PARQUET_REL = "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json"
AUDIT_REL = "03. EA Developer/EA_HybridRegimeMR/research/evidence/EURUSD_PULL_AUDIT.json"
CLOCK_REL = "02. AlphaFactory/tools/research/fivepercent_server_clock.py"
TERMINAL_REL = "02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe"
OUTPUT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)
LEDGER_NAME = "signal_dates.jsonl"
RECEIPT_NAME = "signal_date_selection_receipt.json"

PLAN_SHA256 = "22B7D673666F6038DD8EB5FC31D1D5E1C646F9897C88CC1C487A19F6154F7009"
PARQUET_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
MANIFEST_SHA256 = "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54"
AUDIT_SHA256 = "C21B5BC82681261FBED6681A1505B8B4D6AB8DAEA6571CCE814C46B9E99AA410"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"

EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY_FRAGMENT = "Five Percent"
BERLIN = ZoneInfo("Europe/Berlin")
PIP_SIZE = 0.0001
LOOKBACK = 60
MIN_HISTORY = 40
SEED_START = date(2015, 1, 1)
POPULATION_START = date(2016, 1, 1)
SLOTS = {"open": time(7, 59), "entry": time(14, 14)}
ALLOWED_SOURCE_COLUMNS = ("time_utc", "close")
MIN_SELECTED = 1200
MAX_SELECTED = 1500

REVIEWED_REGISTRY_ROW_SHA256: str | None = "1EB92F54B10BBF0D5A2982D9F6B53DDF263A5156638FB300409AFFE48EA2E808"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class SelectionError(RuntimeError):
    """Fail-closed engineering error; never an economic verdict."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def normalized_tool_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise SelectionError("tool must contain exactly one valid registry sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise SelectionError(f"{label} must stay on D:")
    return resolved


def split_for_day(day: date) -> str:
    if 2016 <= day.year <= 2020:
        return "TRAIN"
    if 2021 <= day.year <= 2024:
        return "VALIDATION"
    if day.year >= 2025:
        return "HOLDOUT"
    raise SelectionError(f"day is outside the V2 population: {day}")


def iter_weekdays(start: date, end: date) -> Iterable[date]:
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def target_timestamp_map(cutoff: date) -> dict[datetime, tuple[date, str]]:
    if cutoff < POPULATION_START:
        raise SelectionError("cutoff precedes the V2 population")
    targets: dict[datetime, tuple[date, str]] = {}
    for day in iter_weekdays(SEED_START, cutoff):
        for slot, wall_time in SLOTS.items():
            local = datetime.combine(day, wall_time, tzinfo=BERLIN)
            utc_naive = local.astimezone(timezone.utc).replace(tzinfo=None)
            if utc_naive in targets:
                raise SelectionError("duplicate UTC target timestamp")
            targets[utc_naive] = (day, slot)
    return targets


def load_clock(path: Path) -> Any:
    if sha256_file(path) != CLOCK_SHA256:
        raise SelectionError("clock model hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi_v2_clock", path)
    if spec is None or spec.loader is None:
        raise SelectionError("cannot load clock model")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def utc_to_server_naive(utc_naive: datetime, clock: Any) -> datetime:
    matches = []
    for offset in (2, 3):
        candidate = utc_naive + timedelta(hours=offset)
        if clock.server_to_utc(candidate) == utc_naive:
            matches.append(candidate)
    if len(matches) != 1:
        raise SelectionError(f"clock inverse is not unique for {utc_naive.isoformat()}")
    return matches[0]


def load_exact_base_rows(
    parquet: Path,
    targets: dict[datetime, tuple[date, str]],
) -> pd.DataFrame:
    """Expose only exact signal-time rows from the full-history parquet."""

    try:
        import pyarrow as pa
        import pyarrow.dataset as ds
    except ImportError as exc:
        raise SelectionError("pyarrow is required for exact-row projection") from exc
    values = pa.array(list(targets), type=pa.timestamp("ns"))
    dataset = ds.dataset(parquet, format="parquet")
    table = dataset.to_table(
        columns=list(ALLOWED_SOURCE_COLUMNS),
        filter=ds.field("time_utc").isin(values),
    )
    if tuple(table.column_names) != ALLOWED_SOURCE_COLUMNS:
        raise SelectionError("base projection column drift")
    frame = table.to_pandas()
    frame["time_utc"] = pd.to_datetime(frame["time_utc"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    if (
        frame["time_utc"].isna().any()
        or frame["close"].isna().any()
        or frame["time_utc"].duplicated().any()
        or not np.isfinite(frame["close"].to_numpy(dtype=float)).all()
        or (frame["close"] <= 0).any()
    ):
        raise SelectionError("base exact-row integrity failed")
    rows: list[dict[str, object]] = []
    for stamp, close in frame.itertuples(index=False, name=None):
        stamp = pd.Timestamp(stamp).to_pydatetime().replace(tzinfo=None)
        identity = targets.get(stamp)
        if identity is None:
            raise SelectionError("parquet returned a non-target row")
        day, slot = identity
        rows.append({"local_date": day, "slot": slot, "close": float(close), "source": "canonical_parquet"})
    return pd.DataFrame(rows, columns=["local_date", "slot", "close", "source"])


def pull_current_exact_rows(
    *,
    terminal: Path,
    days: list[date],
    clock: Any,
) -> tuple[pd.DataFrame, dict[str, object]]:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SelectionError("MetaTrader5 package is required for current refresh") from exc
    if not mt5.initialize(path=str(terminal), portable=True, timeout=60_000):
        raise SelectionError(f"MT5 initialize failed: {mt5.last_error()}")
    calls = 0
    rows: list[dict[str, object]] = []
    try:
        terminal_info = mt5.terminal_info()
        account = mt5.account_info()
        if terminal_info is None or account is None:
            raise SelectionError(f"MT5 metadata unavailable: {mt5.last_error()}")
        if terminal_info.trade_allowed is not False:
            raise SelectionError("current-refresh terminal must have trading disabled")
        if account.server != EXPECTED_SERVER or EXPECTED_COMPANY_FRAGMENT not in str(account.company):
            raise SelectionError("current-refresh broker identity mismatch")
        info = mt5.symbol_info("EURUSD")
        if info is None or int(info.digits) != 5 or not math.isclose(float(info.point), 0.00001, rel_tol=0.0, abs_tol=1e-12):
            raise SelectionError("EURUSD symbol geometry mismatch")
        for day in days:
            daily: list[dict[str, object]] = []
            for slot, wall_time in SLOTS.items():
                local = datetime.combine(day, wall_time, tzinfo=BERLIN)
                utc_naive = local.astimezone(timezone.utc).replace(tzinfo=None)
                server = utc_to_server_naive(utc_naive, clock)
                encoded = server.replace(tzinfo=timezone.utc)
                rates = mt5.copy_rates_range(
                    "EURUSD",
                    mt5.TIMEFRAME_M1,
                    encoded,
                    encoded + timedelta(seconds=59),
                )
                calls += 1
                if rates is None:
                    raise SelectionError(f"MT5 exact-bar call failed for {day} {slot}: {mt5.last_error()}")
                if len(rates) == 0:
                    daily = []
                    break
                if len(rates) != 1:
                    raise SelectionError(f"MT5 exact-bar call returned {len(rates)} rows")
                raw_server = datetime.fromtimestamp(int(rates[0]["time"]), tz=timezone.utc).replace(tzinfo=None)
                if raw_server != server or clock.server_to_utc(raw_server) != utc_naive:
                    raise SelectionError("MT5 exact-bar clock mismatch")
                close = float(rates[0]["close"])
                if not math.isfinite(close) or close <= 0:
                    raise SelectionError("MT5 exact-bar close is invalid")
                daily.append({"local_date": day, "slot": slot, "close": close, "source": "mt5_exact_refresh"})
            if len(daily) == len(SLOTS):
                rows.extend(daily)
        metadata = {
            "terminal_path": str(terminal),
            "terminal_build": int(terminal_info.build),
            "server": str(account.server),
            "company": str(account.company),
            "login": int(account.login),
            "trade_allowed": False,
            "copy_rates_range_calls": calls,
            "orders_submitted": 0,
        }
    finally:
        mt5.shutdown()
    return pd.DataFrame(rows, columns=["local_date", "slot", "close", "source"]), metadata


def build_selection(exact_rows: pd.DataFrame, cutoff: date) -> pd.DataFrame:
    required = {"local_date", "slot", "close", "source"}
    if set(exact_rows.columns) != required:
        raise SelectionError("exact-row schema drift")
    if exact_rows.empty or exact_rows.duplicated(["local_date", "slot"]).any():
        raise SelectionError("exact rows are empty or duplicated")
    if not set(exact_rows["slot"]).issubset(SLOTS):
        raise SelectionError("unexpected exact-row slot")
    pivot = exact_rows.pivot(index="local_date", columns="slot", values="close")
    for slot in SLOTS:
        if slot not in pivot:
            pivot[slot] = np.nan
    pivot = pivot[["open", "entry"]].dropna().sort_index()
    pressure = (pivot["entry"] - pivot["open"]) / PIP_SIZE
    threshold = pressure.abs().shift(1).rolling(LOOKBACK, min_periods=MIN_HISTORY).median()
    eligible = (
        threshold.notna()
        & (pressure.abs() >= threshold)
        & (pressure != 0.0)
    )
    selected = pivot.loc[eligible].copy()
    selected = selected.loc[
        (pd.Index(selected.index) >= POPULATION_START)
        & (pd.Index(selected.index) <= cutoff)
    ]
    pressure = pressure.loc[selected.index]
    threshold = threshold.loc[selected.index]
    rows = []
    for day in selected.index:
        p = float(pressure.loc[day])
        rows.append(
            {
                "request_id": f"ECBFX-{day.isoformat()}",
                "local_date": day.isoformat(),
                "split": split_for_day(day),
                "direction_from_pressure": -1 if p > 0 else 1,
                "pre_fix_pressure_pips": round(p, 10),
                "pressure_threshold_pips": round(float(threshold.loc[day]), 10),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        raise SelectionError("selection produced zero dates")
    return out


def validate_selection(selection: pd.DataFrame) -> dict[str, int]:
    expected = {
        "request_id",
        "local_date",
        "split",
        "direction_from_pressure",
        "pre_fix_pressure_pips",
        "pressure_threshold_pips",
    }
    if set(selection.columns) != expected:
        raise SelectionError("selection schema drift")
    dates = selection["local_date"].tolist()
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise SelectionError("selection dates are duplicated or unsorted")
    if not MIN_SELECTED <= len(selection) <= MAX_SELECTED:
        raise SelectionError(f"selection population outside frozen range: {len(selection)}")
    if not set(selection["direction_from_pressure"]) == {-1, 1}:
        raise SelectionError("selection must contain both pressure directions")
    counts = {name: int((selection["split"] == name).sum()) for name in ("TRAIN", "VALIDATION", "HOLDOUT")}
    if any(value <= 0 for value in counts.values()):
        raise SelectionError("one or more V2 partitions are absent")
    return counts


def validate_authority(workspace: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise SelectionError("registry sentinel is not armed")
    plan = workspace / PLAN_REL
    tool = workspace / TOOL_REL
    test = workspace / TEST_REL
    registry = workspace / REGISTRY_REL
    if sha256_file(plan) != PLAN_SHA256:
        raise SelectionError("V2 plan hash drift")
    tool_payload = tool.read_bytes()
    tool_base = normalized_tool_base_sha256(tool_payload)
    test_sha = sha256_file(test)
    candidates: list[tuple[dict[str, object], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            candidates.append((row, raw + b"\n"))
    if not candidates:
        raise SelectionError("hypothesis absent from registry")
    row, line = candidates[-1]
    row_sha = sha256_bytes(line)
    validation = row.get("validation", {})
    if not isinstance(validation, dict):
        raise SelectionError("registry validation contract malformed")
    expected = {
        "source_plan_v2_sha256": PLAN_SHA256,
        "reviewed_signal_date_tool_base_sha256": tool_base,
        "reviewed_signal_date_test_sha256": test_sha,
        "canonical_m1_sha256": PARQUET_SHA256,
        "canonical_clock_sha256": CLOCK_SHA256,
    }
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256:
        raise SelectionError("sentinel does not bind the latest HYP001 row")
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise SelectionError("registry state or V2 plan binding invalid")
    if validation.get("source_date_selection_authorized") is not True:
        raise SelectionError("source-date selection authority absent")
    for key, value in expected.items():
        if validation.get(key) != value:
            raise SelectionError(f"registry binding mismatch: {key}")
    for key in (
        "paid_acquisition_authorized",
        "economics_authorized",
        "mql5_authorized",
        "model0_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise SelectionError(f"forbidden authority open: {key}")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise SelectionError("signal-date selection attempt already consumed")
    return {
        "registry_row_sha256": row_sha,
        "tool_base_sha256": tool_base,
        "tool_file_sha256": sha256_bytes(tool_payload),
        "test_sha256": test_sha,
    }


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def execute(workspace: Path, cutoff: date, production_refresh: bool) -> Path:
    workspace = require_d(workspace, "workspace")
    latest_complete = datetime.now(BERLIN).date() - timedelta(days=1)
    if cutoff != latest_complete:
        raise SelectionError(
            f"production cutoff must be latest complete Europe/Berlin day {latest_complete}"
        )
    authority = validate_authority(workspace)
    bindings = {
        PARQUET_REL: PARQUET_SHA256,
        MANIFEST_REL: MANIFEST_SHA256,
        AUDIT_REL: AUDIT_SHA256,
        CLOCK_REL: CLOCK_SHA256,
    }
    for rel, expected_sha in bindings.items():
        path = require_d(workspace / rel, rel)
        if not path.is_file() or sha256_file(path) != expected_sha:
            raise SelectionError(f"bound source missing or drifted: {rel}")
    targets = target_timestamp_map(cutoff)
    base = load_exact_base_rows(workspace / PARQUET_REL, targets)
    complete_base = base.groupby("local_date")["slot"].nunique()
    complete_days = complete_base[complete_base == len(SLOTS)].index.tolist()
    if not complete_days:
        raise SelectionError("canonical parquet has no complete exact-slot days")
    last_complete_base = max(complete_days)
    refresh_days = list(iter_weekdays(last_complete_base + timedelta(days=1), cutoff))
    refresh = pd.DataFrame(columns=["local_date", "slot", "close", "source"])
    terminal_metadata: dict[str, object] = {
        "refresh_required": bool(refresh_days),
        "copy_rates_range_calls": 0,
        "orders_submitted": 0,
    }
    if refresh_days:
        if not production_refresh:
            raise SelectionError("current exact-slot refresh is required but not authorized by CLI")
        clock = load_clock(workspace / CLOCK_REL)
        refresh, terminal_metadata = pull_current_exact_rows(
            terminal=require_d(workspace / TERMINAL_REL, "MT5 terminal"),
            days=refresh_days,
            clock=clock,
        )
    combined = pd.concat([base, refresh], ignore_index=True)
    combined = combined.sort_values(["local_date", "slot", "source"], kind="stable")
    combined = combined.drop_duplicates(["local_date", "slot"], keep="last")
    selection = build_selection(combined, cutoff)
    split_counts = validate_selection(selection)
    output_root = require_d(workspace / OUTPUT_ROOT_REL, "selection output root")
    if output_root.exists():
        raise SelectionError("exclusive signal-date output root already exists")
    ledger = output_root / LEDGER_NAME
    ledger_payload = b"".join(
        canonical_json(row) + b"\n" for row in selection.to_dict(orient="records")
    )
    write_new(ledger, ledger_payload)
    receipt = output_root / RECEIPT_NAME
    payload = {
        "schema_version": "eurfxofi002_signal_date_selection.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "OUTCOME_BLIND_SIGNAL_DATE_SELECTION_COMPLETE",
        "cutoff_local_date": cutoff.isoformat(),
        "last_complete_base_local_date": last_complete_base.isoformat(),
        "selection_rule": {
            "timezone": "Europe/Berlin",
            "slots": ["07:59", "14:14"],
            "pressure_pips": "(close_14:14-close_07:59)/0.0001",
            "threshold": "abs_pressure.shift(1).rolling(60,min_periods=40).median()",
            "condition": "abs_pressure>=threshold and pressure!=0",
        },
        "selected_dates": int(len(selection)),
        "split_counts": split_counts,
        "first_selected_local_date": str(selection.iloc[0]["local_date"]),
        "last_selected_local_date": str(selection.iloc[-1]["local_date"]),
        "base_exact_rows_exposed": int(len(base)),
        "refresh_exact_rows_exposed": int(len(refresh)),
        "refresh_weekdays_requested": len(refresh_days),
        "terminal_metadata": terminal_metadata,
        "ledger_path": str(ledger.relative_to(workspace)).replace("\\", "/"),
        "ledger_sha256": sha256_file(ledger),
        "bindings": {
            "plan_path": PLAN_REL,
            "plan_sha256": PLAN_SHA256,
            "tool_path": TOOL_REL,
            "tool_base_sha256": authority["tool_base_sha256"],
            "tool_file_sha256": authority["tool_file_sha256"],
            "test_path": TEST_REL,
            "test_sha256": authority["test_sha256"],
            "registry_row_sha256": authority["registry_row_sha256"],
            "canonical_m1_path": PARQUET_REL,
            "canonical_m1_sha256": PARQUET_SHA256,
            "canonical_manifest_path": MANIFEST_REL,
            "canonical_manifest_sha256": MANIFEST_SHA256,
            "pull_audit_path": AUDIT_REL,
            "pull_audit_sha256": AUDIT_SHA256,
            "clock_path": CLOCK_REL,
            "clock_sha256": CLOCK_SHA256,
        },
        "information_boundary": {
            "source_columns": list(ALLOWED_SOURCE_COLUMNS),
            "source_slots_only": ["07:59", "14:14"],
            "post_decision_bars_read": 0,
            "target_returns_read": 0,
            "outcome_fields_used": [],
            "paid_requests_made": 0,
            "databento_calls": 0,
            "orders_submitted": 0,
            "economics_executed": False,
            "validation_opened": False,
            "holdout_opened": False,
            "mql5_files_created": 0,
            "model0_runs": 0,
        },
        "authority_after_result": {
            "free_metadata_quote_may_be_preregistered": True,
            "paid_acquisition_authorized": False,
            "economics_authorized": False,
            "mql5_authorized": False,
            "model0_authorized": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
        },
    }
    write_new(receipt, canonical_json(payload) + b"\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    parser.add_argument("--as-of-local-date", required=True)
    parser.add_argument("--production-refresh", action="store_true")
    args = parser.parse_args()
    try:
        cutoff = datetime.strptime(args.as_of_local_date, "%Y-%m-%d").date()
        receipt = execute(args.workspace.resolve(), cutoff, args.production_refresh)
        result = json.loads(receipt.read_text(encoding="utf-8"))
        print(
            "EURFXOFI002_SIGNAL_DATES_OK "
            f"selected={result['selected_dates']} splits={result['split_counts']} "
            f"cutoff={result['cutoff_local_date']} paid=0 outcomes=0"
        )
        print(f"RECEIPT {receipt}")
        return 0
    except SelectionError as exc:
        print(f"EURFXOFI002_SIGNAL_DATES_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
