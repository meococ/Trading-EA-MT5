#!/usr/bin/env python3
"""Frozen pre-outcome probe for HYP-CFTC-FX-H1-001.

No parameter search is present. The script either passes every preregistered
train/internal-validation gate or kills the hypothesis before EA construction.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import time as wall_clock
import zipfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5


WORKSPACE = Path(r"D:\Trading EA MT5")
PACKAGE = WORKSPACE / "03. EA Developer" / "EA_CFTCOptionsPulse"
RESEARCH = PACKAGE / "research"
EVIDENCE = RESEARCH / "evidence"
MANIFEST_PATH = WORKSPACE / "02. AlphaFactory" / "external" / "cftc_fx_options_tff" / "source_manifest.json"
MANIFEST_SHA256 = "F281B9378A9D7774B2B2246EDC4D9A12ECD43698C5A9BDF919B3F8189EB7B7FD"
TERMINAL_PATH = WORKSPACE / "02. AlphaFactory" / "runtime" / "mt5-portable-fivepercent" / "terminal64.exe"

HYPOTHESIS_ID = "HYP-CFTC-FX-H1-001"
YEARS = tuple(range(2017, 2024))
HOLDOUT_YEARS = (2024, 2025)
TRAIN = (date(2018, 1, 1), date(2021, 12, 31))
INTERNAL_VALIDATION = (date(2022, 1, 1), date(2023, 12, 31))
RELEASE_LAG_DAYS = 6
ENTRY_TIME_UTC = time(7, 0)
EXIT_TIME_UTC = time(16, 0)
ATR_PERIOD = 14
STOP_ATR = 1.5
RISK_FRACTION = 0.0025
SYMBOL_ORDER = ("EURUSD", "GBPUSD", "USDJPY")
CONTRACTS = {
    "EURUSD": {"code": "099741", "name": "EURO FX - CHICAGO MERCANTILE EXCHANGE", "orientation": 1},
    "GBPUSD": {"code": "096742", "name": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE", "orientation": 1},
    "USDJPY": {"code": "097741", "name": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE", "orientation": -1},
}
PIP_SIZE = {"EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01}
COST_X1_PIPS = {"EURUSD": 1.5, "GBPUSD": 2.0, "USDJPY": 1.5}
COST_MULTIPLIERS = {"x1": 1.0, "x1_5": 1.5, "x2": 2.0}


@dataclass
class SignalEvent:
    symbol: str
    report_date: str
    entry_date: str
    options_net: float
    options_net_change: float
    futures_net: float
    futures_net_change: float
    candidate_direction: int
    control_direction: int


@dataclass
class Trade:
    arm: str
    split: str
    symbol: str
    report_date: str
    entry_time_utc: str
    exit_time_utc: str
    direction: int
    entry_price: float
    exit_price: float
    stop_price: float
    stop_distance_pips: float
    exit_reason: str
    gross_pips: float
    net_r_x1: float
    net_r_x1_5: float
    net_r_x2: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def split_for(d: date) -> str | None:
    if TRAIN[0] <= d <= TRAIN[1]:
        return "train"
    if INTERNAL_VALIDATION[0] <= d <= INTERNAL_VALIDATION[1]:
        return "internal_validation"
    return None


def sign(value: float) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def options_residual(combined_long: float, combined_short: float, futures_long: float, futures_short: float) -> float:
    return (combined_long - combined_short) - (futures_long - futures_short)


def load_manifest() -> dict[str, Any]:
    actual = sha256_file(MANIFEST_PATH)
    if actual != MANIFEST_SHA256:
        raise RuntimeError(f"manifest_sha_mismatch:{actual}:{MANIFEST_SHA256}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if tuple(manifest.get("years", [])) != YEARS:
        raise RuntimeError(f"manifest_years_mismatch:{manifest.get('years')}")
    if manifest.get("holdout_years_downloaded") != []:
        raise RuntimeError("holdout_archive_access_forbidden")
    return manifest


def load_cftc_events(manifest: dict[str, Any]) -> tuple[list[SignalEvent], list[dict[str, Any]], list[dict[str, Any]]]:
    by_dataset: dict[str, dict[tuple[str, date], dict[str, float]]] = {
        "futures_only": {},
        "futures_options_combined": {},
    }
    malformed: list[dict[str, Any]] = []
    source_identity: list[dict[str, Any]] = []
    symbol_by_code = {spec["code"]: symbol for symbol, spec in CONTRACTS.items()}

    for record in manifest["records"]:
        dataset = record["dataset"]
        year = int(record["year"])
        if year not in YEARS or dataset not in by_dataset:
            raise RuntimeError(f"unexpected_manifest_record:{dataset}:{year}")
        path = WORKSPACE / Path(record["path"])
        actual_sha = sha256_file(path)
        if actual_sha != str(record["sha256"]).upper():
            raise RuntimeError(f"archive_sha_mismatch:{path}:{actual_sha}")
        source_identity.append(
            {"dataset": dataset, "year": year, "path": record["path"], "sha256": actual_sha, "bytes": path.stat().st_size}
        )
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if not name.endswith("/")]
            if len(members) != 1:
                raise RuntimeError(f"unexpected_zip_members:{path}:{members}")
            with archive.open(members[0]) as binary:
                reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", errors="strict", newline=""))
                for row_number, row in enumerate(reader, 2):
                    code = (row.get("CFTC_Contract_Market_Code") or "").strip()
                    if code not in symbol_by_code:
                        continue
                    symbol = symbol_by_code[code]
                    expected = CONTRACTS[symbol]
                    try:
                        report_date = date.fromisoformat((row.get("Report_Date_as_YYYY-MM-DD") or "").strip())
                    except ValueError:
                        malformed.append({"dataset": dataset, "year": year, "row": row_number, "symbol": symbol, "reason": "invalid_report_date"})
                        continue
                    expected_kind = "FutOnly" if dataset == "futures_only" else "Combined"
                    if (row.get("FutOnly_or_Combined") or "").strip() != expected_kind:
                        malformed.append({"dataset": dataset, "report_date": report_date.isoformat(), "symbol": symbol, "reason": "wrong_dataset_kind"})
                        continue
                    if (row.get("Market_and_Exchange_Names") or "").strip() != expected["name"]:
                        malformed.append({"dataset": dataset, "report_date": report_date.isoformat(), "symbol": symbol, "reason": "market_name_mismatch"})
                        continue
                    try:
                        lev_long = float(row["Lev_Money_Positions_Long_All"])
                        lev_short = float(row["Lev_Money_Positions_Short_All"])
                    except (KeyError, TypeError, ValueError):
                        malformed.append({"dataset": dataset, "report_date": report_date.isoformat(), "symbol": symbol, "reason": "invalid_lev_money_position"})
                        continue
                    key = (code, report_date)
                    if key in by_dataset[dataset]:
                        malformed.append({"dataset": dataset, "report_date": report_date.isoformat(), "symbol": symbol, "reason": "duplicate_key"})
                        continue
                    by_dataset[dataset][key] = {"long": lev_long, "short": lev_short}

    keys = sorted(set(by_dataset["futures_only"]) | set(by_dataset["futures_options_combined"]), key=lambda item: (item[1], item[0]))
    paired: dict[str, list[tuple[date, float, float]]] = {symbol: [] for symbol in SYMBOL_ORDER}
    for code, report_date in keys:
        symbol = symbol_by_code[code]
        fut = by_dataset["futures_only"].get((code, report_date))
        combined = by_dataset["futures_options_combined"].get((code, report_date))
        if fut is None or combined is None:
            malformed.append({"dataset": "pair", "report_date": report_date.isoformat(), "symbol": symbol, "reason": "missing_pair"})
            continue
        futures_net = fut["long"] - fut["short"]
        residual = options_residual(combined["long"], combined["short"], fut["long"], fut["short"])
        paired[symbol].append((report_date, futures_net, residual))

    events: list[SignalEvent] = []
    for symbol in SYMBOL_ORDER:
        rows = sorted(paired[symbol])
        orientation = int(CONTRACTS[symbol]["orientation"])
        for previous, current in zip(rows, rows[1:]):
            report_date, futures_net, residual = current
            entry_date = report_date + timedelta(days=RELEASE_LAG_DAYS)
            if split_for(entry_date) is None:
                continue
            futures_change = futures_net - previous[1]
            residual_change = residual - previous[2]
            events.append(
                SignalEvent(
                    symbol=symbol,
                    report_date=report_date.isoformat(),
                    entry_date=entry_date.isoformat(),
                    options_net=residual,
                    options_net_change=residual_change,
                    futures_net=futures_net,
                    futures_net_change=futures_change,
                    candidate_direction=orientation * sign(residual_change),
                    control_direction=orientation * sign(futures_change),
                )
            )
    events.sort(key=lambda event: (event.entry_date, SYMBOL_ORDER.index(event.symbol)))
    return events, malformed, source_identity


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
    selected: list[str] = []
    for symbol in SYMBOL_ORDER:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"symbol_select_failed:{symbol}:{mt5.last_error()}")
        selected.append(symbol)
    return {
        "terminal_path": str(TERMINAL_PATH.resolve()),
        "terminal_build": int(terminal.build),
        "data_path": str(data_path),
        "commondata_path": str(terminal.commondata_path),
        "portable": True,
        "symbols_selected": selected,
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
            datetime(2017, 12, 1, tzinfo=timezone.utc),
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


def atr_before(rows: list[dict[str, Any]], entry_index: int) -> float | None:
    if entry_index < ATR_PERIOD + 1:
        return None
    true_ranges: list[float] = []
    for index in range(entry_index - ATR_PERIOD, entry_index):
        current = rows[index]
        previous_close = rows[index - 1]["close"]
        true_ranges.append(max(current["high"] - current["low"], abs(current["high"] - previous_close), abs(current["low"] - previous_close)))
    return sum(true_ranges) / ATR_PERIOD


def simulate_trade(arm: str, event: SignalEvent, direction: int, rows: list[dict[str, Any]], index_by_time: dict[datetime, int]) -> Trade | None:
    if direction == 0:
        return None
    entry_date = date.fromisoformat(event.entry_date)
    entry_at = datetime.combine(entry_date, ENTRY_TIME_UTC, tzinfo=timezone.utc)
    exit_at = datetime.combine(entry_date, EXIT_TIME_UTC, tzinfo=timezone.utc)
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
    pip = PIP_SIZE[event.symbol]
    gross_pips = direction * (exit_price - entry_price) / pip
    stop_pips = stop_distance / pip
    cost = COST_X1_PIPS[event.symbol]

    def net_r(multiplier: float) -> float:
        return (gross_pips - cost * multiplier) / stop_pips

    return Trade(
        arm=arm,
        split=str(split_for(entry_date)),
        symbol=event.symbol,
        report_date=event.report_date,
        entry_time_utc=entry_at.isoformat(),
        exit_time_utc=exit_time.isoformat(),
        direction=direction,
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
    year_net: dict[str, float] = {}
    for trade in subset:
        key = trade.entry_time_utc[:4]
        year_net[key] = year_net.get(key, 0.0) + trade.net_r_x1
    return {
        "trades": len(subset),
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_elapsed_week": len(subset) / elapsed_weeks,
        "profit_factor_x1": profit_factor(x1),
        "profit_factor_x1_5": profit_factor(x1_5),
        "profit_factor_x2": profit_factor(x2),
        "net_r_x1": sum(x1),
        "max_drawdown_pct_x1": max_drawdown_pct(x1),
        "symbol_trades": {symbol: sum(1 for trade in subset if trade.symbol == symbol) for symbol in SYMBOL_ORDER},
        "year_net_r_x1": year_net,
        "positive_years_x1": sum(1 for value in year_net.values() if value > 0),
    }


def finite_greater(value: float | None, threshold: float, inclusive: bool = False) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and (value >= threshold if inclusive else value > threshold)


def malformed_count_for_split(malformed: list[dict[str, Any]], split: str) -> int:
    count = 0
    for item in malformed:
        raw = item.get("report_date")
        if not raw:
            continue
        entry_date = date.fromisoformat(str(raw)) + timedelta(days=RELEASE_LAG_DAYS)
        if split_for(entry_date) == split:
            count += 1
    return count


def build_gates(candidate: dict[str, Any], control: dict[str, Any], split: str, malformed_count: int, skipped_prices: int) -> dict[str, bool]:
    min_symbol_trades = 40 if split == "train" else 20
    required_positive_years = 3 if split == "train" else 2
    candidate_pf = candidate["profit_factor_x1"]
    control_pf = control["profit_factor_x1"]
    return {
        "cadence_2_to_5": 2.0 <= candidate["trades_per_elapsed_week"] <= 5.0,
        "pf_x1_gt_1_30": finite_greater(candidate_pf, 1.30),
        "pf_x1_5_gte_1_25": finite_greater(candidate["profit_factor_x1_5"], 1.25, inclusive=True),
        "pf_x2_gte_1_00": finite_greater(candidate["profit_factor_x2"], 1.00, inclusive=True),
        "net_r_x1_positive": candidate["net_r_x1"] > 0,
        "max_dd_lte_5_5_pct": candidate["max_drawdown_pct_x1"] <= 5.5,
        "minimum_trades_each_symbol": all(value >= min_symbol_trades for value in candidate["symbol_trades"].values()),
        "positive_years": candidate["positive_years_x1"] >= required_positive_years,
        "beats_futures_control": (
            isinstance(candidate_pf, (int, float))
            and isinstance(control_pf, (int, float))
            and math.isfinite(candidate_pf)
            and math.isfinite(control_pf)
            and candidate_pf >= control_pf + 0.05
            and candidate["net_r_x1"] > control["net_r_x1"]
        ),
        "source_malformed_lte_2": malformed_count <= 2,
        "price_skips_lte_2": skipped_prices <= 2,
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
    manifest = load_manifest()
    events, malformed, source_identity = load_cftc_events(manifest)
    mt5_identity: dict[str, Any] | None = None
    h1: dict[str, list[dict[str, Any]]] = {}
    try:
        mt5_identity = initialize_mt5()
        for symbol in SYMBOL_ORDER:
            h1[symbol] = fetch_h1(symbol)
    finally:
        mt5.shutdown()

    index_by_symbol = {symbol: {row["time"]: index for index, row in enumerate(rows)} for symbol, rows in h1.items()}
    trades: list[Trade] = []
    price_skips = {"train": 0, "internal_validation": 0}
    eligible_counts = {"train": 0, "internal_validation": 0}
    zero_signal_counts = {"candidate": 0, "control": 0}
    for event in events:
        event_date = date.fromisoformat(event.entry_date)
        split = split_for(event_date)
        if split is None:
            continue
        if event.candidate_direction == 0:
            zero_signal_counts["candidate"] += 1
            continue
        eligible_counts[split] += 1
        candidate = simulate_trade("candidate", event, event.candidate_direction, h1[event.symbol], index_by_symbol[event.symbol])
        control = simulate_trade("control", event, event.control_direction, h1[event.symbol], index_by_symbol[event.symbol])
        if candidate is None:
            price_skips[split] += 1
        if event.control_direction == 0:
            zero_signal_counts["control"] += 1
        if candidate is not None:
            trades.append(candidate)
        if control is not None:
            trades.append(control)

    trades.sort(key=lambda trade: (trade.entry_time_utc, SYMBOL_ORDER.index(trade.symbol), trade.arm))
    metrics_by_arm: dict[str, dict[str, dict[str, Any]]] = {}
    gates: dict[str, dict[str, bool]] = {}
    for arm in ("candidate", "control"):
        arm_trades = [trade for trade in trades if trade.arm == arm]
        metrics_by_arm[arm] = {split: metrics(arm_trades, split) for split in ("train", "internal_validation")}
    for split in ("train", "internal_validation"):
        gates[split] = build_gates(
            metrics_by_arm["candidate"][split],
            metrics_by_arm["control"][split],
            split,
            malformed_count_for_split(malformed, split),
            price_skips[split],
        )
    passed = all(all(result.values()) for result in gates.values())
    generated = datetime.now(timezone.utc)
    stamp = generated.strftime("%Y%m%d_%H%M%S")
    csv_path = EVIDENCE / f"{stamp}_HYP_CFTC_FX_H1_001_TRADES.csv"
    json_path = EVIDENCE / f"{stamp}_HYP_CFTC_FX_H1_001_PROBE.json"
    write_csv(csv_path, trades)
    result = {
        "schema_version": "alphafactory_offline_probe.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": generated.isoformat().replace("+00:00", "Z"),
        "verdict": "PASS_BUILD_AUTHORIZED" if passed else "KILL_AT_OFFLINE_PROBE",
        "all_gates_passed": passed,
        "holdout": {
            "years": list(HOLDOUT_YEARS),
            "archives_downloaded": False,
            "price_bars_loaded": 0,
            "outcomes_evaluated": 0,
        },
        "contract": {
            "release_lag_days": RELEASE_LAG_DAYS,
            "entry_time_utc": ENTRY_TIME_UTC.isoformat(),
            "exit_time_utc": EXIT_TIME_UTC.isoformat(),
            "atr_period": ATR_PERIOD,
            "stop_atr": STOP_ATR,
            "risk_fraction": RISK_FRACTION,
            "cost_x1_pips": COST_X1_PIPS,
            "cost_status": "UNVERIFIED_CONSERVATIVE_RESEARCH_PROXY_NON_PROMOTABLE",
        },
        "source_manifest_path": MANIFEST_PATH.relative_to(WORKSPACE).as_posix(),
        "source_manifest_sha256": MANIFEST_SHA256,
        "source_identity": source_identity,
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
            "total_unsealed": len(events),
            "eligible_candidate": eligible_counts,
            "zero_signals": zero_signal_counts,
            "source_malformed_total": len(malformed),
            "source_malformed": malformed,
            "price_skips": price_skips,
        },
        "metrics": metrics_by_arm,
        "gates": gates,
        "gate_pass_count": sum(1 for split_gates in gates.values() for result in split_gates.values() if result),
        "gate_total": sum(len(split_gates) for split_gates in gates.values()),
        "trades_path": csv_path.relative_to(WORKSPACE).as_posix(),
    }
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"probe": str(json_path), "trades": str(csv_path), "verdict": result["verdict"], "gate_pass_count": result["gate_pass_count"], "gate_total": result["gate_total"]}, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
