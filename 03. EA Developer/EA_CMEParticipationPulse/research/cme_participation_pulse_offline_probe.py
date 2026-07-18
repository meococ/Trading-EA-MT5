#!/usr/bin/env python3
"""Single frozen pre-holdout probe for HYP-CME-OI-CONT-H1-FX-001."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import time as wall_clock
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5


WORKSPACE = Path(r"D:\Trading EA MT5")
PACKAGE = WORKSPACE / "03. EA Developer" / "EA_CMEParticipationPulse"
RESEARCH = PACKAGE / "research"
EVIDENCE = RESEARCH / "evidence"
SOURCE_ROOT = WORKSPACE / "02. AlphaFactory" / "external" / "cme_daily_volume"
FEATURE_PATH = SOURCE_ROOT / "fx_participation.csv"
PROFILE_PATH = SOURCE_ROOT / "fx_participation_profile.json"
MANIFEST_PATH = SOURCE_ROOT / "source_manifest.json"
TERMINAL_PATH = WORKSPACE / "02. AlphaFactory" / "runtime" / "mt5-portable-fivepercent" / "terminal64.exe"

HYPOTHESIS_ID = "HYP-CME-OI-CONT-H1-FX-001"
FEATURE_SHA256 = "0083BB12B9F0A9D679E7385D299CAB177121B6BB50FFD6186924E394CB854D50"
PROFILE_SHA256 = "9F926B9FAF8CD6E974693062A5D830E08ED324351DD7EA81C0A707BA1520FE18"
MANIFEST_SHA256 = "6226AE4B9BCE4379D150C0B7A627ECF4B177A960F4A7E6A1CBE099056989DDC1"
SYMBOL_ORDER = ("EURUSD", "GBPUSD", "USDJPY")
TRAIN = (date(2018, 1, 1), date(2021, 12, 31))
INTERNAL_VALIDATION = (date(2022, 1, 1), date(2023, 12, 31))
HOLDOUT_YEARS = (2024, 2025)
ANCHOR_TIME_UTC = time(20, 0)
ENTRY_TIME_UTC = time(17, 0)
EXIT_TIME_UTC = time(20, 0)
ATR_PERIOD = 14
STOP_ATR = 1.5
RISK_FRACTION = 0.0025
PIP_SIZE = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01}
COST_X1_PIPS = {"EURUSD": 1.5, "GBPUSD": 2.0, "USDJPY": 1.5}


@dataclass
class SignalEvent:
    previous_trade_date: str
    trade_date: str
    publication_date: str
    candidate_symbol: str
    candidate_oi_change: float
    candidate_direction: int
    control_symbol: str
    control_direction: int
    prior_moves: dict[str, float]


@dataclass
class Trade:
    arm: str
    split: str
    previous_trade_date: str
    trade_date: str
    publication_date: str
    symbol: str
    oi_change: float | None
    direction: int
    entry_time_utc: str
    exit_time_utc: str
    entry_price: float
    exit_price: float
    stop_price: float
    stop_distance_pips: float
    exit_reason: str
    gross_pips: float
    net_r_x1: float
    net_r_x1_5: float
    net_r_x2: float


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sign(value: float) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def split_for(value: date) -> str | None:
    if TRAIN[0] <= value <= TRAIN[1]:
        return "train"
    if INTERNAL_VALIDATION[0] <= value <= INTERNAL_VALIDATION[1]:
        return "internal_validation"
    return None


def load_source() -> tuple[list[date], dict[date, dict[str, dict[str, int]]], dict[str, Any]]:
    expected = {
        FEATURE_PATH: FEATURE_SHA256,
        PROFILE_PATH: PROFILE_SHA256,
        MANIFEST_PATH: MANIFEST_SHA256,
    }
    for path, frozen_hash in expected.items():
        actual = sha256_file(path)
        if actual != frozen_hash:
            raise RuntimeError(f"source_hash_mismatch:{path}:{actual}:{frozen_hash}")
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if profile.get("failures") != [] or profile.get("row_count") != 5289 or profile.get("date_count") != 1763:
        raise RuntimeError("source_profile_contract_failed")
    if profile.get("price_outcomes_accessed") is not False:
        raise RuntimeError("source_profile_outcome_contamination")
    by_date: dict[date, dict[str, dict[str, int]]] = {}
    with FEATURE_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            trade_date = date.fromisoformat(row["trade_date"])
            if trade_date.year in HOLDOUT_YEARS:
                raise RuntimeError(f"holdout_feature_loaded:{trade_date}")
            by_date.setdefault(trade_date, {})[row["symbol"]] = {
                "total_volume": int(row["total_volume"]),
                "open_interest": int(row["open_interest"]),
            }
    dates = sorted(by_date)
    for trade_date, rows in by_date.items():
        if tuple(symbol for symbol in SYMBOL_ORDER if symbol in rows) != SYMBOL_ORDER:
            raise RuntimeError(f"incomplete_source_date:{trade_date}:{sorted(rows)}")
    return dates, by_date, profile


def initialize_mt5() -> dict[str, Any]:
    if TERMINAL_PATH.drive.upper() != "D:" or not TERMINAL_PATH.is_file():
        raise RuntimeError(f"portable_terminal_missing_or_not_D:{TERMINAL_PATH}")
    if not mt5.initialize(path=str(TERMINAL_PATH), timeout=60_000, portable=True):
        raise RuntimeError(f"mt5_initialize_failed:{mt5.last_error()}")
    terminal = mt5.terminal_info()
    account = mt5.account_info()
    if terminal is None:
        raise RuntimeError("terminal_info_missing")
    data_path = Path(str(terminal.data_path)).resolve()
    if data_path.drive.upper() != "D:":
        raise RuntimeError(f"mt5_data_path_not_D:{data_path}")
    for symbol in SYMBOL_ORDER:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"symbol_select_failed:{symbol}:{mt5.last_error()}")
    return {
        "terminal_path": str(TERMINAL_PATH.resolve()),
        "terminal_build": int(terminal.build),
        "data_path": str(data_path),
        "commondata_path": str(terminal.commondata_path),
        "portable": True,
        "server": str(account.server) if account else None,
        "login": int(account.login) if account else None,
    }


def fetch_h1(symbol: str) -> list[dict[str, Any]]:
    rates = None
    errors: list[str] = []
    for attempt in range(1, 6):
        rates = mt5.copy_rates_range(
            symbol,
            mt5.TIMEFRAME_H1,
            datetime(2016, 12, 1, tzinfo=timezone.utc),
            datetime(2023, 12, 31, 23, 59, tzinfo=timezone.utc),
        )
        if rates is not None and len(rates) > 0:
            break
        errors.append(f"attempt={attempt}:{mt5.last_error()}")
        if attempt < 5:
            wall_clock.sleep(2.0)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"no_h1_rates:{symbol}:{'|'.join(errors)}")
    rows: list[dict[str, Any]] = []
    for rate in rates:
        timestamp = datetime.fromtimestamp(int(rate["time"]), tz=timezone.utc)
        if timestamp.year in HOLDOUT_YEARS:
            raise RuntimeError(f"holdout_bar_loaded:{symbol}:{timestamp.isoformat()}")
        rows.append(
            {
                "time": timestamp,
                "open": float(rate["open"]),
                "high": float(rate["high"]),
                "low": float(rate["low"]),
                "close": float(rate["close"]),
            }
        )
    return rows


def select_event(
    previous_date: date,
    trade_date: date,
    publication_date: date,
    source: dict[date, dict[str, dict[str, int]]],
    price_moves: dict[str, float],
) -> SignalEvent | None:
    oi_changes: dict[str, float] = {}
    for symbol in SYMBOL_ORDER:
        previous_oi = source[previous_date][symbol]["open_interest"]
        current_oi = source[trade_date][symbol]["open_interest"]
        if previous_oi <= 0:
            return None
        oi_changes[symbol] = current_oi / previous_oi - 1.0
    eligible = [symbol for symbol in SYMBOL_ORDER if oi_changes[symbol] > 0]
    if not eligible:
        return None
    candidate_symbol = max(eligible, key=lambda symbol: oi_changes[symbol])
    control_symbol = max(SYMBOL_ORDER, key=lambda symbol: abs(price_moves[symbol]))
    candidate_direction = sign(price_moves[candidate_symbol])
    control_direction = sign(price_moves[control_symbol])
    if candidate_direction == 0 or control_direction == 0:
        return None
    return SignalEvent(
        previous_trade_date=previous_date.isoformat(),
        trade_date=trade_date.isoformat(),
        publication_date=publication_date.isoformat(),
        candidate_symbol=candidate_symbol,
        candidate_oi_change=oi_changes[candidate_symbol],
        candidate_direction=candidate_direction,
        control_symbol=control_symbol,
        control_direction=control_direction,
        prior_moves=price_moves,
    )


def atr_before(rows: list[dict[str, Any]], entry_index: int) -> float | None:
    if entry_index < ATR_PERIOD + 1:
        return None
    true_ranges: list[float] = []
    for index in range(entry_index - ATR_PERIOD, entry_index):
        current = rows[index]
        previous_close = rows[index - 1]["close"]
        true_ranges.append(
            max(
                current["high"] - current["low"],
                abs(current["high"] - previous_close),
                abs(current["low"] - previous_close),
            )
        )
    return sum(true_ranges) / ATR_PERIOD


def simulate_trade(
    arm: str,
    event: SignalEvent,
    rows: list[dict[str, Any]],
    index_by_time: dict[datetime, int],
) -> Trade | None:
    symbol = event.candidate_symbol if arm == "candidate" else event.control_symbol
    direction = event.candidate_direction if arm == "candidate" else event.control_direction
    publication = date.fromisoformat(event.publication_date)
    entry_at = datetime.combine(publication, ENTRY_TIME_UTC, tzinfo=timezone.utc)
    exit_at = datetime.combine(publication, EXIT_TIME_UTC, tzinfo=timezone.utc)
    entry_index = index_by_time.get(entry_at)
    exit_index = index_by_time.get(exit_at)
    if entry_index is None or exit_index is None or exit_index <= entry_index:
        return None
    atr = atr_before(rows, entry_index)
    if atr is None or not math.isfinite(atr) or atr <= 0:
        return None
    entry_price = rows[entry_index]["open"]
    stop_distance = STOP_ATR * atr
    stop_price = entry_price - direction * stop_distance
    exit_price = rows[exit_index]["open"]
    exit_time = exit_at
    exit_reason = "time_exit"
    for index in range(entry_index, exit_index):
        bar = rows[index]
        if direction > 0 and bar["low"] <= stop_price:
            exit_price = min(stop_price, bar["open"])
            exit_time = bar["time"]
            exit_reason = "stop"
            break
        if direction < 0 and bar["high"] >= stop_price:
            exit_price = max(stop_price, bar["open"])
            exit_time = bar["time"]
            exit_reason = "stop"
            break
    pip = PIP_SIZE[symbol]
    gross_pips = direction * (exit_price - entry_price) / pip
    stop_pips = stop_distance / pip
    cost = COST_X1_PIPS[symbol]

    def net_r(multiplier: float) -> float:
        return (gross_pips - cost * multiplier) / stop_pips

    return Trade(
        arm=arm,
        split=str(split_for(publication)),
        previous_trade_date=event.previous_trade_date,
        trade_date=event.trade_date,
        publication_date=event.publication_date,
        symbol=symbol,
        oi_change=event.candidate_oi_change if arm == "candidate" else None,
        direction=direction,
        entry_time_utc=entry_at.isoformat(),
        exit_time_utc=exit_time.isoformat(),
        entry_price=entry_price,
        exit_price=exit_price,
        stop_price=stop_price,
        stop_distance_pips=stop_pips,
        exit_reason=exit_reason,
        gross_pips=gross_pips,
        net_r_x1=net_r(1.0),
        net_r_x1_5=net_r(1.5),
        net_r_x2=net_r(2.0),
    )


def profit_factor(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    if gains <= 0 or losses <= 0:
        return None
    return gains / losses


def max_drawdown_pct(values: list[float]) -> float:
    equity = 100.0
    peak = equity
    maximum = 0.0
    for value in values:
        equity *= max(0.0, 1.0 + RISK_FRACTION * value)
        peak = max(peak, equity)
        if peak > 0:
            maximum = max(maximum, 100.0 * (peak - equity) / peak)
    return maximum


def metrics(trades: list[Trade], split: str) -> dict[str, Any]:
    subset = [trade for trade in trades if trade.split == split]
    start, end = TRAIN if split == "train" else INTERNAL_VALIDATION
    elapsed_weeks = ((end - start).days + 1) / 7.0
    x1 = [trade.net_r_x1 for trade in subset]
    x1_5 = [trade.net_r_x1_5 for trade in subset]
    x2 = [trade.net_r_x2 for trade in subset]
    positive_r_by_year: dict[str, float] = {}
    net_r_by_year: dict[str, float] = {}
    for trade in subset:
        year = trade.entry_time_utc[:4]
        net_r_by_year[year] = net_r_by_year.get(year, 0.0) + trade.net_r_x1
        positive_r_by_year[year] = positive_r_by_year.get(year, 0.0) + max(0.0, trade.net_r_x1)
    total_positive = sum(positive_r_by_year.values())
    max_positive_year_share = max(positive_r_by_year.values(), default=0.0) / total_positive if total_positive > 0 else 1.0
    return {
        "trades": len(subset),
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_elapsed_week": len(subset) / elapsed_weeks,
        "gross_profit_factor": profit_factor([trade.gross_pips for trade in subset]),
        "profit_factor_x1": profit_factor(x1),
        "profit_factor_x1_5": profit_factor(x1_5),
        "profit_factor_x2": profit_factor(x2),
        "net_r_x1": sum(x1),
        "expectancy_r_x1": sum(x1) / len(x1) if x1 else None,
        "max_drawdown_pct_x1": max_drawdown_pct(x1),
        "symbol_trades": {symbol: sum(trade.symbol == symbol for trade in subset) for symbol in SYMBOL_ORDER},
        "net_r_by_year_x1": net_r_by_year,
        "max_positive_year_share": max_positive_year_share,
    }


def finite_threshold(value: float | None, threshold: float, inclusive: bool = False) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and (value >= threshold if inclusive else value > threshold)


def build_gates(
    candidate: dict[str, Any],
    control: dict[str, Any],
    split: str,
    candidate_price_skips: int,
    control_price_skips: int,
) -> dict[str, bool]:
    candidate_pf = candidate["profit_factor_x1"]
    control_pf = control["profit_factor_x1"]
    concentration_cap = 0.45 if split == "train" else 0.70
    return {
        "cadence_min_2": candidate["trades_per_elapsed_week"] >= 2.0,
        "cadence_max_5": candidate["trades_per_elapsed_week"] <= 5.0,
        "pf_x1_gt_1_30": finite_threshold(candidate_pf, 1.30),
        "pf_x1_5_gte_1_25": finite_threshold(candidate["profit_factor_x1_5"], 1.25, inclusive=True),
        "pf_x2_gte_1_00": finite_threshold(candidate["profit_factor_x2"], 1.00, inclusive=True),
        "net_r_x1_positive": candidate["net_r_x1"] > 0,
        "minimum_100_trades": candidate["trades"] >= 100,
        "max_dd_lte_5_5_pct": candidate["max_drawdown_pct_x1"] <= 5.5,
        "beats_control_pf_margin_0_10": (
            isinstance(candidate_pf, (int, float))
            and isinstance(control_pf, (int, float))
            and math.isfinite(candidate_pf)
            and math.isfinite(control_pf)
            and candidate_pf >= control_pf + 0.10
        ),
        "beats_control_net_r": candidate["net_r_x1"] > control["net_r_x1"],
        "candidate_price_skips_lte_2": candidate_price_skips <= 2,
        "control_price_skips_lte_2": control_price_skips <= 2,
        "positive_r_year_concentration": candidate["max_positive_year_share"] <= concentration_cap,
    }


def write_csv(path: Path, trades: list[Trade]) -> None:
    rows = [asdict(trade) for trade in trades]
    if not rows:
        raise RuntimeError("no_trades_to_write")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    dates, source, profile = load_source()
    mt5_identity: dict[str, Any] | None = None
    h1: dict[str, list[dict[str, Any]]] = {}
    try:
        mt5_identity = initialize_mt5()
        for symbol in SYMBOL_ORDER:
            h1[symbol] = fetch_h1(symbol)
    finally:
        mt5.shutdown()
    index_by_symbol = {
        symbol: {row["time"]: index for index, row in enumerate(rows)} for symbol, rows in h1.items()
    }
    events: list[SignalEvent] = []
    source_signal_skips = {"train": 0, "internal_validation": 0}
    for previous_date, trade_date, publication_date in zip(dates, dates[1:], dates[2:]):
        split = split_for(publication_date)
        if split is None:
            continue
        price_moves: dict[str, float] = {}
        missing = False
        for symbol in SYMBOL_ORDER:
            previous_at = datetime.combine(previous_date, ANCHOR_TIME_UTC, tzinfo=timezone.utc)
            current_at = datetime.combine(trade_date, ANCHOR_TIME_UTC, tzinfo=timezone.utc)
            previous_index = index_by_symbol[symbol].get(previous_at)
            current_index = index_by_symbol[symbol].get(current_at)
            if previous_index is None or current_index is None:
                missing = True
                break
            price_moves[symbol] = (
                h1[symbol][current_index]["open"] - h1[symbol][previous_index]["open"]
            ) / PIP_SIZE[symbol]
        if missing:
            source_signal_skips[split] += 1
            continue
        event = select_event(previous_date, trade_date, publication_date, source, price_moves)
        if event is not None:
            events.append(event)
    trades: list[Trade] = []
    price_skips = {
        "candidate": {"train": 0, "internal_validation": 0},
        "control": {"train": 0, "internal_validation": 0},
    }
    for event in events:
        split = str(split_for(date.fromisoformat(event.publication_date)))
        for arm in ("candidate", "control"):
            symbol = event.candidate_symbol if arm == "candidate" else event.control_symbol
            trade = simulate_trade(arm, event, h1[symbol], index_by_symbol[symbol])
            if trade is None:
                price_skips[arm][split] += 1
            else:
                trades.append(trade)
    trades.sort(key=lambda trade: (trade.entry_time_utc, trade.arm, SYMBOL_ORDER.index(trade.symbol)))
    metrics_by_arm: dict[str, dict[str, dict[str, Any]]] = {}
    gates: dict[str, dict[str, bool]] = {}
    for arm in ("candidate", "control"):
        arm_trades = [trade for trade in trades if trade.arm == arm]
        metrics_by_arm[arm] = {
            split: metrics(arm_trades, split) for split in ("train", "internal_validation")
        }
    for split in ("train", "internal_validation"):
        gates[split] = build_gates(
            metrics_by_arm["candidate"][split],
            metrics_by_arm["control"][split],
            split,
            price_skips["candidate"][split] + source_signal_skips[split],
            price_skips["control"][split] + source_signal_skips[split],
        )
    passed = all(all(split_gates.values()) for split_gates in gates.values())
    generated = datetime.now(timezone.utc)
    stamp = generated.strftime("%Y%m%d_%H%M%S")
    csv_path = EVIDENCE / f"{stamp}_HYP_CME_OI_CONT_H1_FX_001_TRADES.csv"
    json_path = EVIDENCE / f"{stamp}_HYP_CME_OI_CONT_H1_FX_001_PROBE.json"
    write_csv(csv_path, trades)
    result = {
        "schema_version": "alphafactory_offline_probe.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": generated.isoformat().replace("+00:00", "Z"),
        "verdict": "PASS_BUILD_AUTHORIZED" if passed else "KILL_AT_OFFLINE_PROBE",
        "all_gates_passed": passed,
        "holdout": {
            "years": list(HOLDOUT_YEARS),
            "feature_rows_loaded": 0,
            "price_bars_loaded": 0,
            "outcomes_evaluated": 0,
        },
        "contract": {
            "anchor_time_utc": ANCHOR_TIME_UTC.isoformat(),
            "entry_time_utc": ENTRY_TIME_UTC.isoformat(),
            "exit_time_utc": EXIT_TIME_UTC.isoformat(),
            "atr_period": ATR_PERIOD,
            "stop_atr": STOP_ATR,
            "risk_fraction": RISK_FRACTION,
            "cost_x1_pips": COST_X1_PIPS,
            "cost_status": "UNVERIFIED_CONSERVATIVE_RESEARCH_PROXY_NON_PROMOTABLE",
        },
        "source": {
            "manifest_path": MANIFEST_PATH.relative_to(WORKSPACE).as_posix(),
            "manifest_sha256": MANIFEST_SHA256,
            "feature_path": FEATURE_PATH.relative_to(WORKSPACE).as_posix(),
            "feature_sha256": FEATURE_SHA256,
            "profile_path": PROFILE_PATH.relative_to(WORKSPACE).as_posix(),
            "profile_sha256": PROFILE_SHA256,
            "profile": profile,
        },
        "mt5_identity": mt5_identity,
        "h1_identity": {
            symbol: {
                "bars": len(rows),
                "first_utc": rows[0]["time"].isoformat(),
                "last_utc": rows[-1]["time"].isoformat(),
            }
            for symbol, rows in h1.items()
        },
        "events": {
            "eligible": {
                split: sum(split_for(date.fromisoformat(event.publication_date)) == split for event in events)
                for split in ("train", "internal_validation")
            },
            "source_signal_skips": source_signal_skips,
            "price_skips": price_skips,
        },
        "metrics": metrics_by_arm,
        "gates": gates,
        "gate_pass_count": sum(result for split_gates in gates.values() for result in split_gates.values()),
        "gate_total": sum(len(split_gates) for split_gates in gates.values()),
        "trades_path": csv_path.relative_to(WORKSPACE).as_posix(),
    }
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": str(json_path),
                "trades": str(csv_path),
                "verdict": result["verdict"],
                "gate_pass_count": result["gate_pass_count"],
                "gate_total": result["gate_total"],
            },
            indent=2,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
