#!/usr/bin/env python3
"""Offline train-only evaluator for HYP-G10-XMOM-W1-002 (import-inert, disarmed).

Importing this module never opens real prices, registry rows, or holdout data.
Production requires explicit --production, an armed REVIEWED_REGISTRY_ROW_SHA256
sentinel, and a one-use train-evaluate authority row. Holdout years remain sealed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import stat
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HYPOTHESIS_ID = "HYP-G10-XMOM-W1-002"
PARENT_HYPOTHESIS_ID = "HYP-G10-XMOM-W1-001"
EA_NAME = "EA_G10WeeklyXSMomentum"
ATTEMPT_ID = "G10XMOM002-TRAIN-EVAL-001"

PLAN_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/"
    "HYP-G10-XMOM-W1-002_ECONOMIC_PROBE_PLAN.md"
)
PLAN_SHA256 = "ABA4C2BA7AFBA07DE7C38A709E00275507ADFCEE035F17E70896B3FF8A74351C"
PARENT_INVENTORY_SHA256 = (
    "DCF3754D4B95EFBA2B25A8455CF6DCDF5169C409CE81FE3568F5C7227C98FE01"
)
PARENT_TERMINAL_SHA256 = (
    "3FF657763271E77E61DA8110FAE1260710AD9733B2F2B14D613A3AAAB8CEC48F"
)
EVALUATOR_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/evaluate_g10_xmom_002_train.py"
)
TEST_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/tests/"
    "test_evaluate_g10_xmom_002_train.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/"
    "HYP-G10-XMOM-W1-002_TRAIN_EVAL_IMPLEMENTATION_REVIEW_RECEIPT.json"
)

CANONICAL_WORKSPACE_ROOT = Path(r"D:\Trading EA MT5")
DATASET_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/"
    f"HYP-G10-XMOM-W1-002/{ATTEMPT_ID}"
)
PARQUET_NAME = "train_w1_bars.parquet"
MANIFEST_NAME = "train_w1_manifest.json"
EXPECTED_SERVER = "FivePercentOnline-Real"
DATASET_SCHEMA_COLUMNS: tuple[str, ...] = (
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

TRAIN_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021)
HOLDOUT_YEARS_SEALED: tuple[int, ...] = (2022, 2023, 2024)
TRAIN_START = date(2018, 1, 1)
TRAIN_END = date(2021, 12, 31)

SYMBOLS: tuple[str, ...] = (
    "AUDUSD",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)
ORIENTATION_MAP: tuple[dict[str, object], ...] = (
    {"currency": "AUD", "broker_symbol": "AUDUSD", "orientation": 1},
    {"currency": "EUR", "broker_symbol": "EURUSD", "orientation": 1},
    {"currency": "GBP", "broker_symbol": "GBPUSD", "orientation": 1},
    {"currency": "NZD", "broker_symbol": "NZDUSD", "orientation": 1},
    {"currency": "CAD", "broker_symbol": "USDCAD", "orientation": -1},
    {"currency": "CHF", "broker_symbol": "USDCHF", "orientation": -1},
    {"currency": "JPY", "broker_symbol": "USDJPY", "orientation": -1},
)
CURRENCY_BY_SYMBOL: dict[str, str] = {
    str(row["broker_symbol"]): str(row["currency"]) for row in ORIENTATION_MAP
}
ORIENTATION_BY_SYMBOL: dict[str, int] = {
    str(row["broker_symbol"]): int(row["orientation"]) for row in ORIENTATION_MAP
}
ORIENTATION_BY_CURRENCY: dict[str, int] = {
    str(row["currency"]): int(row["orientation"]) for row in ORIENTATION_MAP
}
SYMBOL_BY_CURRENCY: dict[str, str] = {
    str(row["currency"]): str(row["broker_symbol"]) for row in ORIENTATION_MAP
}

PIP_SIZE: dict[str, float] = {
    "AUDUSD": 0.0001,
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "NZDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    "USDJPY": 0.01,
}
SPREAD_FLOOR_PIPS: dict[str, float] = {
    "EURUSD": 1.0,
    "GBPUSD": 1.4,
    "AUDUSD": 1.2,
    "NZDUSD": 1.5,
    "USDCAD": 1.4,
    "USDCHF": 1.4,
    "USDJPY": 1.2,
}
COMMISSION_RESERVE_PIPS = 0.7
SLIPPAGE_RESERVE_PIPS = 0.3
ROLLOVER_RESERVE_PIPS = 4.0
LEG_WEIGHT = 0.10
COST_MULTIPLIERS: dict[str, float] = {"x1": 1.0, "x1_5": 1.5, "x2": 2.0}

MIN_COMPLETE_WEEKS = 50
MIN_LEGS_PER_ARM = 200
PF_X1_MIN = 1.30  # strict greater than
PF_X1_5_MIN = 1.25  # inclusive
PF_X2_MIN = 1.00  # inclusive
CADENCE_MIN = 2.0
CADENCE_MAX = 5.0
MC_P95_DD_MAX_PCT = 8.0
MC_PATHS = 10_000
MC_SEED = 5600102

POSITIVE_MONTH_RATIO_MIN = 0.50
MAX_POS_MONTH_SHARE = 0.20
MIN_POS_HALF_YEARS = 9
MAX_POS_HALF_YEAR_SHARE = 0.35
MIN_POS_YEARS = 4
MAX_POS_YEAR_SHARE = 0.40
# Combined surface sizes are frozen for later dual-split reporting only.
COMBINED_MONTHS = 84
COMBINED_HALF_YEARS = 14
COMBINED_YEARS = 7

REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)
HEX = frozenset("0123456789ABCDEF")
CHUNK_SIZE = 1024 * 1024

VERDICT_SURVIVE = "TRAIN_SURVIVE_HOLDOUT_STILL_SEALED"
VERDICT_KILL = "TRAIN_KILL_HOLDOUT_REMAINS_SEALED"
VERDICT_INVALID = "INVALID_SAMPLE"


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


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    """Hash the reviewed disarmed evaluator even while its one-shot sentinel is armed."""

    if type(payload) is not bytes:
        raise ContractError("evaluator payload must be bytes")
    lines = payload.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("evaluator must contain exactly one valid registry-row sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


normalized_base_sha256 = normalized_evaluator_base_sha256


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
    return resolved


def elapsed_calendar_weeks(start: date, end: date) -> float:
    if end < start:
        raise ContractError("elapsed week bounds inverted")
    return ((end - start).days + 1) / 7.0


def train_elapsed_calendar_weeks() -> float:
    return elapsed_calendar_weeks(TRAIN_START, TRAIN_END)


def assert_train_split_years(years: Iterable[int]) -> None:
    for year in years:
        if year not in TRAIN_YEARS or year >= 2022 or year < 2018:
            raise ContractError(f"holdout_or_non_train_year_rejected:{year}")


def reject_holdout_access(years: Iterable[int] | None = None, *, split: str = "train") -> None:
    if split != "train":
        raise ContractError(f"holdout_or_non_train_split_rejected:{split}")
    if years is not None:
        assert_train_split_years(years)


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
    """Surface for a later one-use train-evaluate registry row (not used while disarmed)."""

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
        or validation.get("train_evaluate_authorized") is not True
        or validation.get("train_economics_authorized") is not True
        or validation.get("performance_metrics_authorized") is not True
        or validation.get("holdout_access_authorized") is not False
        or validation.get("promotion_authorized") is not False
        or validation.get("one_use") is not True
    ):
        raise ContractError(
            "latest registry row is not HYP-G10-XMOM-W1-002 probe with "
            "train_evaluate_authorized=true, train_economics_authorized=true, "
            "performance_metrics_authorized=true, holdout_access_authorized=false, "
            "promotion_authorized=false, one_use=true and matching prereg SHA"
        )
    required_bindings = {
        "reviewed_evaluator_path": EVALUATOR_REL,
        "reviewed_test_path": TEST_REL,
        "independent_review_receipt_path": REVIEW_RECEIPT_REL,
    }
    for field, expected in required_bindings.items():
        if validation.get(field) != expected:
            raise ContractError(f"latest registry row has wrong {field}")
    for field in (
        "reviewed_evaluator_base_sha256",
        "reviewed_test_sha256",
        "independent_review_receipt_sha256",
        "dataset_manifest_sha256",
        "dataset_parquet_sha256",
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


def x1_cost_pips(symbol: str) -> float:
    if symbol not in SPREAD_FLOOR_PIPS or symbol not in PIP_SIZE:
        raise ContractError(f"unmapped_cost_symbol:{symbol}")
    cost = (
        float(SPREAD_FLOOR_PIPS[symbol])
        + COMMISSION_RESERVE_PIPS
        + SLIPPAGE_RESERVE_PIPS
        + ROLLOVER_RESERVE_PIPS
    )
    if not math.isfinite(cost) or cost <= 0.0:
        raise ContractError(f"invalid_x1_cost:{symbol}:{cost}")
    return cost


def cost_return(symbol: str, entry_price: float, multiplier: float) -> float:
    if not math.isfinite(entry_price) or entry_price <= 0.0:
        raise ContractError(f"invalid_entry_price:{symbol}:{entry_price}")
    if not math.isfinite(multiplier) or multiplier <= 0.0:
        raise ContractError(f"invalid_cost_multiplier:{multiplier}")
    cost_pips = x1_cost_pips(symbol) * multiplier
    if not math.isfinite(cost_pips) or cost_pips <= 0.0:
        raise ContractError(f"invalid_scaled_cost:{symbol}:{cost_pips}")
    return cost_pips * PIP_SIZE[symbol] / entry_price


def oriented_log_return(open_: float, close: float, orientation: int) -> float:
    if orientation not in (1, -1):
        raise ContractError(f"invalid_orientation:{orientation}")
    if not all(math.isfinite(v) and v > 0.0 for v in (open_, close)):
        raise ContractError("non_finite_or_non_positive_formation_ohlc")
    return float(orientation) * math.log(close / open_)


def rank_currencies(formation_returns: Mapping[str, float]) -> list[tuple[str, float, int]]:
    """Descending oriented return ranks; exact ties break by currency code ascending."""

    if set(formation_returns) != set(ORIENTATION_BY_CURRENCY):
        raise ContractError("formation returns must cover exactly seven currencies")
    ordered = sorted(
        formation_returns.items(),
        key=lambda item: (-float(item[1]), str(item[0])),
    )
    out: list[tuple[str, float, int]] = []
    for index, (currency, value) in enumerate(ordered, start=1):
        out.append((currency, float(value), index))
    return out


def select_basket(ranked: Sequence[tuple[str, float, int]]) -> dict[str, object]:
    if len(ranked) != 7:
        raise ContractError("rank vector must contain seven currencies")
    top2 = [ranked[0][0], ranked[1][0]]
    bottom2 = [ranked[5][0], ranked[6][0]]
    if len(set(top2 + bottom2)) != 4:
        raise ContractError("selected basket must be four unique currencies")
    return {
        "long_currencies": top2,
        "short_currencies": bottom2,
        "ranks": {currency: rank for currency, _value, rank in ranked},
        "formation_returns": {currency: value for currency, value, _rank in ranked},
    }


def pair_direction(currency: str, side: str) -> int:
    orientation = ORIENTATION_BY_CURRENCY[currency]
    if side == "long":
        return orientation
    if side == "short":
        return -orientation
    raise ContractError(f"invalid_side:{side}")


def directed_pair_return(direction: int, entry: float, exit_: float) -> float:
    if direction not in (1, -1):
        raise ContractError(f"invalid_pair_direction:{direction}")
    if not all(math.isfinite(v) and v > 0.0 for v in (entry, exit_)):
        raise ContractError("non_finite_or_non_positive_trade_prices")
    return float(direction) * ((exit_ - entry) / entry)


def profit_factor(values: Sequence[float]) -> float | None:
    gains = sum(v for v in values if v > 0.0)
    losses = -sum(v for v in values if v < 0.0)
    if losses == 0.0:
        return None if gains == 0.0 else float("inf")
    return gains / losses


def equity_curve(weekly_returns: Sequence[float]) -> list[float]:
    equity = 1.0
    curve = [equity]
    for ret in weekly_returns:
        if not math.isfinite(ret):
            raise ContractError("non_finite_weekly_return")
        equity *= 1.0 + float(ret)
        curve.append(equity)
    return curve


def max_drawdown_pct(weekly_returns: Sequence[float]) -> float:
    curve = equity_curve(weekly_returns)
    peak = curve[0]
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0.0:
            max_dd = max(max_dd, (peak - value) / peak)
    return 100.0 * max_dd


def bootstrap_p95_max_drawdown(
    weekly_returns: Sequence[float],
    *,
    seed: int = MC_SEED,
    paths: int = MC_PATHS,
) -> float:
    """Deterministic bootstrap of path max DD using weekly basket returns."""

    series = [float(v) for v in weekly_returns]
    n = len(series)
    if n == 0:
        raise ContractError("bootstrap requires at least one weekly return")
    # Pure-Python LCG for platform-stable determinism (no numpy RNG drift).
    state = int(seed) & 0xFFFFFFFFFFFFFFFF

    def next_u01() -> float:
        nonlocal state
        state = (6364136223846793005 * state + 1) & 0xFFFFFFFFFFFFFFFF
        return state / float(1 << 64)

    path_dds: list[float] = []
    for _ in range(int(paths)):
        path = [series[int(next_u01() * n)] for _ in range(n)]
        path_dds.append(max_drawdown_pct(path))
    path_dds.sort()
    # Inclusive nearest-rank P95.
    index = min(n_paths_index(len(path_dds), 0.95), len(path_dds) - 1)
    return float(path_dds[index])


def n_paths_index(count: int, quantile: float) -> int:
    if count <= 0:
        raise ContractError("empty quantile population")
    # nearest rank method: ceil(q * N) - 1
    rank = int(math.ceil(quantile * count)) - 1
    return max(0, min(count - 1, rank))


def concentration_stats(period_nets: Mapping[str, float]) -> dict[str, object]:
    values = [float(v) for v in period_nets.values()]
    positive = [v for v in values if v > 0.0]
    if not values:
        return {
            "periods": 0,
            "positive_count": 0,
            "positive_ratio": None,
            "max_positive_share": None,
        }
    pos_sum = sum(positive)
    max_share = (max(positive) / pos_sum) if positive and pos_sum > 0.0 else None
    return {
        "periods": len(values),
        "positive_count": len(positive),
        "positive_ratio": len(positive) / len(values),
        "max_positive_share": max_share,
    }


def period_key_month(week_date: date) -> str:
    return f"{week_date.year:04d}-{week_date.month:02d}"


def period_key_half_year(week_date: date) -> str:
    half = 1 if week_date.month <= 6 else 2
    return f"{week_date.year:04d}-H{half}"


def period_key_year(week_date: date) -> str:
    return f"{week_date.year:04d}"


def _bar_ok(bar: Mapping[str, object] | None) -> bool:
    if bar is None:
        return False
    for field in ("open", "high", "low", "close"):
        value = bar.get(field)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0.0:
            return False
    return True


def index_bars_by_symbol_epoch(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, dict[int, dict[str, object]]]:
    indexed: dict[str, dict[int, dict[str, object]]] = {symbol: {} for symbol in SYMBOLS}
    for row in rows:
        symbol = str(row["symbol"])
        if symbol not in indexed:
            raise ContractError(f"unexpected_symbol:{symbol}")
        epoch = int(row["time_epoch"])
        year = datetime.fromtimestamp(epoch, tz=timezone.utc).year
        assert_train_split_years([year])
        if epoch in indexed[symbol]:
            raise ContractError(f"duplicate_bar:{symbol}:{epoch}")
        indexed[symbol][epoch] = dict(row)
    return indexed


def complete_week_epochs(
    indexed: Mapping[str, Mapping[int, Mapping[str, object]]],
) -> list[int]:
    """Epochs present for all seven symbols (complete weekly join)."""

    common: set[int] | None = None
    for symbol in SYMBOLS:
        epochs = set(indexed[symbol])
        common = epochs if common is None else (common & epochs)
    if not common:
        return []
    ordered = sorted(common)
    # Monotonic W1 sequence identity check: strictly increasing already by sort.
    return ordered


def evaluate_train_bars(
    rows: Sequence[Mapping[str, object]],
    *,
    split: str = "train",
) -> dict[str, object]:
    """Pure offline train evaluation on synthetic or sealed train rows."""

    reject_holdout_access(split=split)
    indexed = index_bars_by_symbol_epoch(rows)
    epochs = complete_week_epochs(indexed)
    funnel = {
        "elapsed_calendar_weeks": train_elapsed_calendar_weeks(),
        "complete_join_weeks": 0,
        "eligible_baskets": 0,
        "completed_legs_challenger": 0,
        "completed_legs_control": 0,
        "skipped_weeks": 0,
    }
    leg_rows: list[dict[str, object]] = []
    week_rows: list[dict[str, object]] = []
    skip_log: list[dict[str, object]] = []

    # Complete joins require a prior completed week for formation.
    for i in range(1, len(epochs)):
        prior_epoch = epochs[i - 1]
        curr_epoch = epochs[i]
        funnel["complete_join_weeks"] += 1
        gap_seconds = curr_epoch - prior_epoch
        if not (6 * 24 * 60 * 60 <= gap_seconds <= 8 * 24 * 60 * 60):
            skip_log.append(
                {
                    "week_epoch": curr_epoch,
                    "prior_epoch": prior_epoch,
                    "reason": "non_adjacent_completed_week_formation_rejected",
                    "gap_seconds": gap_seconds,
                }
            )
            funnel["skipped_weeks"] += 1
            continue
        prior_year = datetime.fromtimestamp(prior_epoch, tz=timezone.utc).year
        curr_year = datetime.fromtimestamp(curr_epoch, tz=timezone.utc).year
        try:
            assert_train_split_years([prior_year, curr_year])
        except ContractError as exc:
            skip_log.append(
                {
                    "week_epoch": curr_epoch,
                    "reason": str(exc),
                }
            )
            funnel["skipped_weeks"] += 1
            continue

        formation: dict[str, float] = {}
        formation_ok = True
        for symbol in SYMBOLS:
            bar = indexed[symbol].get(prior_epoch)
            if not _bar_ok(bar):
                formation_ok = False
                break
            assert bar is not None
            currency = CURRENCY_BY_SYMBOL[symbol]
            formation[currency] = oriented_log_return(
                float(bar["open"]),
                float(bar["close"]),
                ORIENTATION_BY_SYMBOL[symbol],
            )
        if not formation_ok or len(formation) != 7:
            skip_log.append(
                {
                    "week_epoch": curr_epoch,
                    "prior_epoch": prior_epoch,
                    "reason": "incomplete_or_invalid_seven_symbol_formation",
                }
            )
            funnel["skipped_weeks"] += 1
            continue

        ranked = rank_currencies(formation)
        basket = select_basket(ranked)
        long_currencies = list(basket["long_currencies"])  # type: ignore[arg-type]
        short_currencies = list(basket["short_currencies"])  # type: ignore[arg-type]
        selections: list[tuple[str, str, str, int]] = []
        for currency in long_currencies:
            symbol = SYMBOL_BY_CURRENCY[currency]
            selections.append((currency, symbol, "long", pair_direction(currency, "long")))
        for currency in short_currencies:
            symbol = SYMBOL_BY_CURRENCY[currency]
            selections.append((currency, symbol, "short", pair_direction(currency, "short")))
        if len(selections) != 4:
            skip_log.append(
                {
                    "week_epoch": curr_epoch,
                    "reason": "basket_not_four_legs",
                }
            )
            funnel["skipped_weeks"] += 1
            continue

        trade_bars: list[tuple[str, str, str, int, Mapping[str, object]]] = []
        all_ok = True
        for currency, symbol, side, direction in selections:
            bar = indexed[symbol].get(curr_epoch)
            if not _bar_ok(bar):
                all_ok = False
                break
            assert bar is not None
            trade_bars.append((currency, symbol, side, direction, bar))
        if not all_ok or len(trade_bars) != 4:
            skip_log.append(
                {
                    "week_epoch": curr_epoch,
                    "prior_epoch": prior_epoch,
                    "reason": "incomplete_four_leg_current_week_prices",
                    "selected": [item[1] for item in selections],
                }
            )
            funnel["skipped_weeks"] += 1
            continue

        funnel["eligible_baskets"] += 1
        week_date = datetime.fromtimestamp(curr_epoch, tz=timezone.utc).date()
        challenger_leg_nets: dict[str, list[float]] = {
            "x1": [],
            "x1_5": [],
            "x2": [],
        }
        control_leg_nets: dict[str, list[float]] = {
            "x1": [],
            "x1_5": [],
            "x2": [],
        }

        for currency, symbol, side, direction, bar in trade_bars:
            entry = float(bar["open"])
            exit_ = float(bar["close"])
            gross = directed_pair_return(direction, entry, exit_)
            x1_pips = x1_cost_pips(symbol)
            nets: dict[str, float] = {}
            for label, mult in COST_MULTIPLIERS.items():
                c_ret = cost_return(symbol, entry, mult)
                nets[label] = gross - c_ret
                challenger_leg_nets[label].append(nets[label])
            # Matched control: same selected legs, flipped pair direction, same costs.
            control_direction = -direction
            control_gross = directed_pair_return(control_direction, entry, exit_)
            control_nets: dict[str, float] = {}
            for label, mult in COST_MULTIPLIERS.items():
                c_ret = cost_return(symbol, entry, mult)
                control_nets[label] = control_gross - c_ret
                control_leg_nets[label].append(control_nets[label])

            ranks = basket["ranks"]
            assert isinstance(ranks, dict)
            for arm, arm_direction, arm_nets in (
                ("challenger", direction, nets),
                ("control", control_direction, control_nets),
            ):
                leg_rows.append(
                    {
                        "split": "train",
                        "arm": arm,
                        "week_epoch": curr_epoch,
                        "prior_epoch": prior_epoch,
                        "week_date": week_date.isoformat(),
                        "currency": currency,
                        "symbol": symbol,
                        "side": side,
                        "pair_direction": arm_direction,
                        "rank": int(ranks[currency]),
                        "formation_return": float(formation[currency]),
                        "entry": entry,
                        "exit": exit_,
                        "gross_return": (
                            gross if arm == "challenger" else control_gross
                        ),
                        "cost_pips_x1": x1_pips,
                        "net_return_x1": arm_nets["x1"],
                        "net_return_x1_5": arm_nets["x1_5"],
                        "net_return_x2": arm_nets["x2"],
                        "skip_reason": None,
                    }
                )
            funnel["completed_legs_challenger"] += 1
            funnel["completed_legs_control"] += 1

        def week_port(leg_nets: Sequence[float]) -> float:
            if len(leg_nets) != 4:
                raise ContractError("week portfolio requires exactly four legs")
            return LEG_WEIGHT * sum(leg_nets)

        ch_week = {
            label: week_port(challenger_leg_nets[label]) for label in COST_MULTIPLIERS
        }
        co_week = {
            label: week_port(control_leg_nets[label]) for label in COST_MULTIPLIERS
        }
        week_rows.append(
            {
                "split": "train",
                "week_epoch": curr_epoch,
                "prior_epoch": prior_epoch,
                "week_date": week_date.isoformat(),
                "eligible": True,
                "four_leg_complete": True,
                "challenger_return_x1": ch_week["x1"],
                "challenger_return_x1_5": ch_week["x1_5"],
                "challenger_return_x2": ch_week["x2"],
                "control_return_x1": co_week["x1"],
                "control_return_x1_5": co_week["x1_5"],
                "control_return_x2": co_week["x2"],
            }
        )

    return summarize_evaluation(leg_rows, week_rows, funnel, skip_log)


def _arm_leg_returns(leg_rows: Sequence[Mapping[str, object]], arm: str, field: str) -> list[float]:
    return [
        float(row[field])
        for row in leg_rows
        if row.get("arm") == arm and row.get(field) is not None
    ]


def summarize_evaluation(
    leg_rows: Sequence[Mapping[str, object]],
    week_rows: Sequence[Mapping[str, object]],
    funnel: Mapping[str, object],
    skip_log: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    elapsed = float(funnel["elapsed_calendar_weeks"])
    arms: dict[str, dict[str, object]] = {}
    for arm in ("challenger", "control"):
        legs_x1 = _arm_leg_returns(leg_rows, arm, "net_return_x1")
        legs_x15 = _arm_leg_returns(leg_rows, arm, "net_return_x1_5")
        legs_x2 = _arm_leg_returns(leg_rows, arm, "net_return_x2")
        week_field = f"{arm}_return_x1"
        weekly = [float(row[week_field]) for row in week_rows]
        mc_weekly = weekly + [0.0] * max(0, int(math.ceil(elapsed)) - len(weekly))
        pf_x1 = profit_factor(legs_x1)
        pf_x15 = profit_factor(legs_x15)
        pf_x2 = profit_factor(legs_x2)
        net_x1 = float(sum(legs_x1))
        expectancy_x1 = float(sum(legs_x1) / len(legs_x1)) if legs_x1 else float("nan")
        cadence = (len(legs_x1) / elapsed) if elapsed > 0 else float("nan")
        dd = max_drawdown_pct(weekly) if weekly else 0.0
        mc_p95 = bootstrap_p95_max_drawdown(mc_weekly) if weekly else float("nan")
        eq = equity_curve(weekly) if weekly else [1.0]

        month_net: dict[str, float] = {
            f"{year:04d}-{month:02d}": 0.0
            for year in TRAIN_YEARS
            for month in range(1, 13)
        }
        half_net: dict[str, float] = {
            f"{year:04d}-H{half}": 0.0
            for year in TRAIN_YEARS
            for half in (1, 2)
        }
        year_net: dict[str, float] = {str(year): 0.0 for year in TRAIN_YEARS}
        for row in week_rows:
            week_date = date.fromisoformat(str(row["week_date"]))
            ret = float(row[week_field])
            month_net[period_key_month(week_date)] = month_net.get(period_key_month(week_date), 0.0) + ret
            half_net[period_key_half_year(week_date)] = half_net.get(period_key_half_year(week_date), 0.0) + ret
            year_net[period_key_year(week_date)] = year_net.get(period_key_year(week_date), 0.0) + ret

        symbol_net: dict[str, float] = {}
        currency_net: dict[str, float] = {}
        side_net: dict[str, float] = {}
        for row in leg_rows:
            if row.get("arm") != arm:
                continue
            symbol = str(row["symbol"])
            currency = str(row["currency"])
            side = str(row["side"])
            value = float(row["net_return_x1"])
            symbol_net[symbol] = symbol_net.get(symbol, 0.0) + value
            currency_net[currency] = currency_net.get(currency, 0.0) + value
            side_net[side] = side_net.get(side, 0.0) + value

        arms[arm] = {
            "legs": len(legs_x1),
            "complete_weeks": len(week_rows),
            "profit_factor_x1": pf_x1,
            "profit_factor_x1_5": pf_x15,
            "profit_factor_x2": pf_x2,
            "net_return_x1": net_x1,
            "expectancy_x1": expectancy_x1,
            "cadence_legs_per_elapsed_week": cadence,
            "max_drawdown_pct_x1": dd,
            "mc_p95_max_drawdown_pct": mc_p95,
            "equity_end": eq[-1],
            "monthly": concentration_stats(month_net),
            "half_year": concentration_stats(half_net),
            "yearly": concentration_stats(year_net),
            "symbol_net_x1": symbol_net,
            "currency_net_x1": currency_net,
            "side_net_x1": side_net,
            "month_net_x1": month_net,
            "half_year_net_x1": half_net,
            "year_net_x1": year_net,
        }

    gates = build_train_gates(arms["challenger"], arms["control"])
    sample_ok = (
        int(arms["challenger"]["complete_weeks"]) >= MIN_COMPLETE_WEEKS
        and int(arms["challenger"]["legs"]) >= MIN_LEGS_PER_ARM
        and int(arms["control"]["legs"]) >= MIN_LEGS_PER_ARM
    )
    if not sample_ok:
        verdict = VERDICT_INVALID
    elif all(gates.values()):
        verdict = VERDICT_SURVIVE
    else:
        verdict = VERDICT_KILL

    return {
        "schema_version": "g10_xmom_002_train_eval.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "split": "train",
        "train_years": list(TRAIN_YEARS),
        "holdout_years_sealed": list(HOLDOUT_YEARS_SEALED),
        "holdout_access": False,
        "leg_weight": LEG_WEIGHT,
        "cost_model": {
            "spread_floor_pips": dict(SPREAD_FLOOR_PIPS),
            "commission_reserve_pips": COMMISSION_RESERVE_PIPS,
            "slippage_reserve_pips": SLIPPAGE_RESERVE_PIPS,
            "rollover_reserve_pips": ROLLOVER_RESERVE_PIPS,
            "multipliers": dict(COST_MULTIPLIERS),
            "status": "UNVERIFIED_CONSERVATIVE_RESEARCH_PROXY_NON_PROMOTABLE",
        },
        "funnel": dict(funnel),
        "arms": arms,
        "gates": gates,
        "all_gates_passed": all(gates.values()) if sample_ok else False,
        "sample_ok": sample_ok,
        "verdict": verdict,
        "leg_rows": list(leg_rows),
        "week_rows": list(week_rows),
        "skip_log": list(skip_log),
        "combined_surface_targets": {
            "months": COMBINED_MONTHS,
            "half_years": COMBINED_HALF_YEARS,
            "years": COMBINED_YEARS,
            "note": "Combined 2018-2024 concentration gates apply only after both splits pass.",
        },
        "concentration_gate_thresholds": {
            "positive_month_ratio_min": POSITIVE_MONTH_RATIO_MIN,
            "max_positive_month_share": MAX_POS_MONTH_SHARE,
            "min_positive_half_years": MIN_POS_HALF_YEARS,
            "max_positive_half_year_share": MAX_POS_HALF_YEAR_SHARE,
            "min_positive_years": MIN_POS_YEARS,
            "max_positive_year_share": MAX_POS_YEAR_SHARE,
        },
        "mc": {
            "paths": MC_PATHS,
            "seed": MC_SEED,
            "method": "bootstrap_weekly_basket_returns_pure_python_lcg",
        },
    }


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def build_train_gates(
    challenger: Mapping[str, object],
    control: Mapping[str, object],
) -> dict[str, bool]:
    pf_x1 = challenger.get("profit_factor_x1")
    pf_x15 = challenger.get("profit_factor_x1_5")
    pf_x2 = challenger.get("profit_factor_x2")
    control_pf = control.get("profit_factor_x1")
    cadence = challenger.get("cadence_legs_per_elapsed_week")
    mc = challenger.get("mc_p95_max_drawdown_pct")
    net = challenger.get("net_return_x1")
    exp = challenger.get("expectancy_x1")
    control_net = control.get("net_return_x1")

    return {
        "min_complete_weeks": int(challenger.get("complete_weeks", 0)) >= MIN_COMPLETE_WEEKS,
        "min_legs_challenger": int(challenger.get("legs", 0)) >= MIN_LEGS_PER_ARM,
        "min_legs_control": int(control.get("legs", 0)) >= MIN_LEGS_PER_ARM,
        "pf_x1_gt_1_30": _finite(pf_x1) and float(pf_x1) > PF_X1_MIN,  # type: ignore[arg-type]
        "pf_x1_5_gte_1_25": _finite(pf_x15) and float(pf_x15) >= PF_X1_5_MIN,  # type: ignore[arg-type]
        "pf_x2_gte_1_00": _finite(pf_x2) and float(pf_x2) >= PF_X2_MIN,  # type: ignore[arg-type]
        "net_return_x1_positive": _finite(net) and float(net) > 0.0,  # type: ignore[arg-type]
        "expectancy_x1_positive": _finite(exp) and float(exp) > 0.0,  # type: ignore[arg-type]
        "cadence_2_to_5": (
            _finite(cadence) and CADENCE_MIN <= float(cadence) <= CADENCE_MAX  # type: ignore[arg-type]
        ),
        "mc_p95_dd_lte_8_pct": _finite(mc) and float(mc) <= MC_P95_DD_MAX_PCT,  # type: ignore[arg-type]
        "beats_control_pf_x1": (
            _finite(pf_x1)
            and _finite(control_pf)
            and float(pf_x1) > float(control_pf)  # type: ignore[arg-type]
        ),
        "beats_control_net_x1": (
            _finite(net)
            and _finite(control_net)
            and float(net) > float(control_net)  # type: ignore[arg-type]
        ),
    }


def load_and_validate_train_dataset(
    *,
    dataset_root: Path,
    expected_manifest_sha256: str | None = None,
    expected_parquet_sha256: str | None = None,
    expected_plan_sha256: str = PLAN_SHA256,
    expected_parent_inventory_sha256: str = PARENT_INVENTORY_SHA256,
    expected_parent_terminal_sha256: str = PARENT_TERMINAL_SHA256,
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, str]]:
    import pandas as pd

    root = Path(dataset_root)
    manifest_path = root / MANIFEST_NAME
    parquet_path = root / PARQUET_NAME
    if not manifest_path.is_file() or not parquet_path.is_file():
        raise ContractError("train dataset parquet/manifest missing")
    manifest_payload = _read_file_bytes(manifest_path)
    parquet_payload = _read_file_bytes(parquet_path)
    manifest_sha = sha256_bytes(manifest_payload)
    parquet_sha = sha256_bytes(parquet_payload)
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise ContractError("dataset manifest SHA mismatch")
    if expected_parquet_sha256 is not None and parquet_sha != expected_parquet_sha256:
        raise ContractError("dataset parquet SHA mismatch")
    manifest = json.loads(manifest_payload)
    if manifest_payload != canonical_json(manifest) + b"\n":
        raise ContractError("dataset manifest must be compact canonical JSON")
    if manifest.get("hypothesis_id") != HYPOTHESIS_ID:
        raise ContractError("manifest hypothesis mismatch")
    if manifest.get("split") != "train":
        raise ContractError("manifest split must be train")
    if tuple(manifest.get("train_years", [])) != TRAIN_YEARS:
        raise ContractError("manifest train years mismatch")
    if tuple(manifest.get("years", [])) != TRAIN_YEARS:
        raise ContractError("manifest years must match exact train years")
    if tuple(manifest.get("symbols", [])) != SYMBOLS:
        raise ContractError("manifest symbols mismatch")
    if tuple(manifest.get("schema", [])) != DATASET_SCHEMA_COLUMNS:
        raise ContractError("manifest schema mismatch")
    if manifest.get("plan_sha256") != expected_plan_sha256:
        raise ContractError("manifest plan SHA mismatch")
    if manifest.get("parent_inventory_sha256") != expected_parent_inventory_sha256:
        raise ContractError("manifest parent inventory SHA mismatch")
    if manifest.get("parent_terminal_sha256") != expected_parent_terminal_sha256:
        raise ContractError("manifest parent terminal SHA mismatch")
    if manifest.get("parquet_sha256") != parquet_sha:
        raise ContractError("manifest parquet_sha256 does not match file")
    if any(
        int(manifest.get("outcome_blind_counters", {}).get(key, 1)) != 0
        for key in (
            "ranks_computed",
            "returns_computed",
            "signals_generated",
            "trades_simulated",
            "costs_computed",
        )
    ):
        raise ContractError("manifest outcome counters must remain hard-zero")
    if manifest.get("economics_executed") is not False:
        raise ContractError("manifest must not claim economics executed")

    frame = pd.read_parquet(io.BytesIO(parquet_payload))
    if tuple(str(column) for column in frame.columns) != DATASET_SCHEMA_COLUMNS:
        raise ContractError("parquet schema mismatch")
    if int(manifest.get("row_count", -1)) != int(len(frame)):
        raise ContractError("manifest row_count mismatch")
    rows = frame.to_dict(orient="records")
    if any(str(row.get("broker_server")) != EXPECTED_SERVER for row in rows):
        raise ContractError("parquet broker_server mismatch")
    years = sorted(
        {
            datetime.fromtimestamp(int(row["time_epoch"]), tz=timezone.utc).year
            for row in rows
        }
    )
    assert_train_split_years(years)
    reject_holdout_access(years, split="train")
    hashes = {
        "manifest_sha256": manifest_sha,
        "parquet_sha256": parquet_sha,
        "plan_sha256": expected_plan_sha256,
        "parent_inventory_sha256": expected_parent_inventory_sha256,
        "parent_terminal_sha256": expected_parent_terminal_sha256,
    }
    return rows, manifest, hashes


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes:
        raise ContractError("artifact payload must be bytes")
    path = Path(path)
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


def _read_file_bytes(path: Path) -> bytes:
    path = Path(path)
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise ContractError(f"required file missing or unreadable: {path.name}") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or int(before.st_nlink) != 1
        or path.is_symlink()
        or _is_reparse(before)
    ):
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
    if production is not True:
        raise ContractError(
            "production train evaluation is disarmed; explicit --production is required"
        )
    if REVIEWED_REGISTRY_ROW_SHA256 is None:
        raise ContractError(
            "production train evaluation is disarmed; reviewed registry-row sentinel is absent"
        )
    if not _valid_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("reviewed registry-row sentinel is invalid")

    workspace = Path(workspace_root).resolve(strict=True)
    canonical_workspace = Path(CANONICAL_WORKSPACE_ROOT).resolve(strict=True)
    if os.path.normcase(str(workspace)) != os.path.normcase(str(canonical_workspace)):
        raise ContractError("production workspace is not the canonical D-side workspace")

    registry_payload = _read_file_bytes(workspace / REGISTRY_REL)
    authority = validate_production_registry_authority(
        registry_payload, REVIEWED_REGISTRY_ROW_SHA256
    )
    validation = authority["validation"]
    if type(validation) is not dict:
        raise ContractError("latest registry row missing validation bindings")

    plan_payload = _read_file_bytes(workspace / PLAN_REL)
    if sha256_bytes(plan_payload) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")

    evaluator_payload = _read_file_bytes(workspace / EVALUATOR_REL)
    evaluator_base_sha = normalized_evaluator_base_sha256(evaluator_payload)
    test_sha = sha256_bytes(_read_file_bytes(workspace / TEST_REL))
    review_receipt_sha = sha256_bytes(_read_file_bytes(workspace / REVIEW_RECEIPT_REL))
    if evaluator_base_sha != validation.get("reviewed_evaluator_base_sha256"):
        raise ContractError("reviewed disarmed evaluator SHA mismatch")
    if test_sha != validation.get("reviewed_test_sha256"):
        raise ContractError("reviewed test SHA mismatch")
    if review_receipt_sha != validation.get("independent_review_receipt_sha256"):
        raise ContractError("independent review receipt SHA mismatch")

    rows, manifest, hashes = load_and_validate_train_dataset(
        dataset_root=workspace / DATASET_ROOT_REL,
        expected_manifest_sha256=str(validation["dataset_manifest_sha256"]),
        expected_parquet_sha256=str(validation["dataset_parquet_sha256"]),
    )
    result = evaluate_train_bars(rows, split="train")
    # Drop bulky row arrays from terminal JSON; write separately if needed.
    terminal = {
        "schema_version": "g10_xmom_002_train_eval_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
        "split": "train",
        "holdout_access": False,
        "plan_sha256": PLAN_SHA256,
        "parent_inventory_sha256": PARENT_INVENTORY_SHA256,
        "parent_terminal_sha256": PARENT_TERMINAL_SHA256,
        "dataset_manifest_sha256": hashes["manifest_sha256"],
        "dataset_parquet_sha256": hashes["parquet_sha256"],
        "evaluator_base_sha256": evaluator_base_sha,
        "test_sha256": test_sha,
        "independent_review_receipt_sha256": review_receipt_sha,
        "manifest_identity": {
            "row_count": manifest.get("row_count"),
            "years": manifest.get("years"),
            "symbols": manifest.get("symbols"),
        },
        "funnel": result["funnel"],
        "arms": {
            arm: {
                key: value
                for key, value in metrics.items()
                if key
                not in {
                    "month_net_x1",
                    "half_year_net_x1",
                    "year_net_x1",
                }
            }
            for arm, metrics in result["arms"].items()
        },
        "gates": result["gates"],
        "all_gates_passed": result["all_gates_passed"],
        "sample_ok": result["sample_ok"],
        "verdict": result["verdict"],
        "mc": result["mc"],
        "promotion_authorized": False,
        "holdout_authorized": False,
        "holdout_next_stage_eligible": result["verdict"] == VERDICT_SURVIVE,
    }

    evidence_root = workspace / EVIDENCE_ROOT_REL
    try:
        evidence_root.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError("exclusive evidence path already exists") from exc
    except FileNotFoundError:
        evidence_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            evidence_root.mkdir(parents=False, exist_ok=False)
        except FileExistsError as exc:
            raise ContractError("exclusive evidence path already exists") from exc

    legs_path = evidence_root / "train_eval_legs.json"
    weeks_path = evidence_root / "train_eval_weeks.json"
    atomic_write_canonical_json(legs_path, {"legs": result["leg_rows"]})
    atomic_write_canonical_json(
        weeks_path,
        {"weeks": result["week_rows"], "skips": result["skip_log"]},
    )
    terminal["train_eval_legs_sha256"] = sha256_file(legs_path)
    terminal["train_eval_weeks_sha256"] = sha256_file(weeks_path)
    atomic_write_canonical_json(evidence_root / "train_eval_terminal.json", terminal)
    return terminal


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--production",
        action="store_true",
        help="Explicit arm for the single real train evaluation attempt.",
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
