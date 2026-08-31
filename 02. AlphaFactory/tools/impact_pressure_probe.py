#!/usr/bin/env python3
"""Frozen MT5-native screening probe for Impact-per-Pressure Continuation.

This is a discovery probe, not an EA backtest and not promotion evidence.  It
reads historical ticks from the currently connected MT5 terminal, aggregates
closed M15 bars, compares the proposed price-path statistic with one matched
return-shock control, and writes hash-bound research artifacts.  It has no
order, position, or trading mutation calls.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics
from collections import deque
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

# Factory isolate only. The old default was r"C:\Program Files\MetaTrader 5\
# terminal64.exe", which does not exist on this machine; a bare fallback would
# have attached to the Owner GUI instead. See tools/factory_paths.py.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from tools.factory_paths import factory_mt5_terminal as _factory_mt5_terminal


def _default_terminal() -> str | None:
    """Resolve the pinned factory terminal, or None so argparse still builds."""
    try:
        return str(_factory_mt5_terminal())
    except Exception:
        return None

BAR_MS = 15 * 60 * 1000
QUOTE_FLAG_MASK = 2 | 4  # TICK_FLAG_BID | TICK_FLAG_ASK
STRESS_A_PIPS = 0.8  # 0.2 pip slippage/side + 0.4 pip RT commission
STRESS_B_PIPS = 1.2  # 0.3 pip slippage/side + 0.6 pip RT commission


@dataclass(slots=True)
class BarFeature:
    symbol: str
    bar_ms: int
    point: float
    pip_size: float
    first_bid: float
    first_ask: float
    last_bid: float
    last_ask: float
    bid_min: float
    bid_max: float
    ask_min: float
    ask_max: float
    start_mid: float
    end_mid: float
    move_points: float
    path_points: float
    nq: int
    netq: int
    ipp: float
    pe: float
    raw: float
    median_spread_points: float
    base_valid: bool
    continuous_prev: bool = False
    return_points: float | None = None
    raw_z: float | None = None
    return_z: float | None = None
    spread_ratio: float | None = None
    eligible: bool = False


@dataclass(slots=True)
class Trade:
    strategy: str
    symbol: str
    signal_ms: int
    entry_ms: int
    exit_ms: int
    direction: int
    signal_score: float
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    initial_stop_pips: float
    exit_reason: str
    gross_pips: float
    net_pips_a: float
    net_pips_b: float
    net_r_a: float
    net_r_b: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1000)


def month_ranges(start: datetime, end: datetime) -> Iterable[tuple[datetime, datetime]]:
    cursor = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    while cursor < end:
        next_month = (
            datetime(cursor.year + 1, 1, 1, tzinfo=timezone.utc)
            if cursor.month == 12
            else datetime(cursor.year, cursor.month + 1, 1, tzinfo=timezone.utc)
        )
        yield max(cursor, start), min(next_month, end)
        cursor = next_month


def robust_z(value: float, history: Sequence[float]) -> float | None:
    if len(history) < 20:
        return None
    median = statistics.median(history)
    mad = statistics.median(abs(item - median) for item in history)
    if mad <= 0:
        return None
    return (value - median) / mad


def impact_components(mid: Sequence[float], point: float) -> dict[str, float | int | bool]:
    """Compute the frozen report formula from one closed bar's mid quotes."""
    if len(mid) < 2 or point <= 0:
        return {
            "move_points": 0.0,
            "path_points": 0.0,
            "nq": 0,
            "netq": 0,
            "ipp": 0.0,
            "pe": 0.0,
            "raw": 0.0,
            "base_valid": False,
        }
    diffs = [float(mid[index] - mid[index - 1]) for index in range(1, len(mid))]
    nonzero = [diff for diff in diffs if diff != 0.0]
    move_points = float((mid[-1] - mid[0]) / point)
    path_points = float(sum(abs(diff) for diff in nonzero) / point)
    nq = len(nonzero)
    netq = sum(1 if diff > 0 else -1 for diff in nonzero)
    ipp = abs(move_points) / max(1, abs(netq))
    pe = abs(move_points) / max(1.0, path_points)
    raw = (1.0 if move_points > 0 else -1.0 if move_points < 0 else 0.0) * math.log1p(ipp * pe)
    return {
        "move_points": move_points,
        "path_points": path_points,
        "nq": nq,
        "netq": netq,
        "ipp": ipp,
        "pe": pe,
        "raw": raw,
        "base_valid": nq >= 2 and path_points > 0,
    }


def aggregate_month(symbol: str, ticks: Any, point: float, pip_size: float) -> list[BarFeature]:
    """Aggregate one MT5 tick array into closed-bar features."""
    import numpy as np

    if ticks is None or len(ticks) == 0:
        return []
    flags = ticks["flags"]
    bid = ticks["bid"]
    ask = ticks["ask"]
    valid = ((flags & QUOTE_FLAG_MASK) != 0) & (bid > 0) & (ask > 0) & (ask >= bid)
    ticks = ticks[valid]
    if len(ticks) == 0:
        return []
    bar_ids = (ticks["time_msc"] // BAR_MS) * BAR_MS
    change = np.flatnonzero(np.r_[True, bar_ids[1:] != bar_ids[:-1], True])
    rows: list[BarFeature] = []
    for left, right in zip(change[:-1], change[1:]):
        group = ticks[left:right]
        mids = (group["bid"] + group["ask"]) / 2.0
        parts = impact_components(mids.tolist(), point)
        spreads = (group["ask"] - group["bid"]) / point
        rows.append(
            BarFeature(
                symbol=symbol,
                bar_ms=int(bar_ids[left]),
                point=point,
                pip_size=pip_size,
                first_bid=float(group["bid"][0]),
                first_ask=float(group["ask"][0]),
                last_bid=float(group["bid"][-1]),
                last_ask=float(group["ask"][-1]),
                bid_min=float(np.min(group["bid"])),
                bid_max=float(np.max(group["bid"])),
                ask_min=float(np.min(group["ask"])),
                ask_max=float(np.max(group["ask"])),
                start_mid=float(mids[0]),
                end_mid=float(mids[-1]),
                move_points=float(parts["move_points"]),
                path_points=float(parts["path_points"]),
                nq=int(parts["nq"]),
                netq=int(parts["netq"]),
                ipp=float(parts["ipp"]),
                pe=float(parts["pe"]),
                raw=float(parts["raw"]),
                median_spread_points=float(np.median(spreads)),
                base_valid=bool(parts["base_valid"]),
            )
        )
    return rows


def enrich_features(rows: list[BarFeature], c: float, n_min: int) -> None:
    raw_history: deque[float] = deque(maxlen=20)
    spread_history: deque[float] = deque(maxlen=20)
    return_history: deque[float] = deque(maxlen=20)
    previous: BarFeature | None = None
    for row in rows:
        row.continuous_prev = previous is not None and row.bar_ms - previous.bar_ms == BAR_MS
        if row.continuous_prev and previous is not None:
            row.return_points = (row.end_mid - previous.end_mid) / row.point
        if row.base_valid:
            row.raw_z = robust_z(row.raw, list(raw_history))
            if len(spread_history) >= 20:
                spread_base = statistics.median(spread_history)
                row.spread_ratio = row.median_spread_points / spread_base if spread_base > 0 else None
            raw_history.append(row.raw)
            spread_history.append(row.median_spread_points)
        if row.return_points is not None:
            row.return_z = robust_z(row.return_points, list(return_history))
            return_history.append(row.return_points)
        row.eligible = bool(
            row.base_valid
            and row.raw_z is not None
            and row.spread_ratio is not None
            and row.spread_ratio <= c
            and row.nq >= n_min
            and abs(row.move_points) > row.median_spread_points
        )
        previous = row


def write_features(path: Path, rows: Sequence[BarFeature]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [field.name for field in fields(BarFeature)]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_optional_float(value: str) -> float | None:
    return None if value in {"", "None", "null"} else float(value)


def read_features(path: Path) -> list[BarFeature]:
    rows: list[BarFeature] = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                BarFeature(
                    symbol=raw["symbol"],
                    bar_ms=int(raw["bar_ms"]),
                    point=float(raw["point"]),
                    pip_size=float(raw["pip_size"]),
                    first_bid=float(raw["first_bid"]),
                    first_ask=float(raw["first_ask"]),
                    last_bid=float(raw["last_bid"]),
                    last_ask=float(raw["last_ask"]),
                    bid_min=float(raw["bid_min"]),
                    bid_max=float(raw["bid_max"]),
                    ask_min=float(raw["ask_min"]),
                    ask_max=float(raw["ask_max"]),
                    start_mid=float(raw["start_mid"]),
                    end_mid=float(raw["end_mid"]),
                    move_points=float(raw["move_points"]),
                    path_points=float(raw["path_points"]),
                    nq=int(raw["nq"]),
                    netq=int(raw["netq"]),
                    ipp=float(raw["ipp"]),
                    pe=float(raw["pe"]),
                    raw=float(raw["raw"]),
                    median_spread_points=float(raw["median_spread_points"]),
                    base_valid=raw["base_valid"].lower() == "true",
                    continuous_prev=raw["continuous_prev"].lower() == "true",
                    return_points=parse_optional_float(raw["return_points"]),
                    raw_z=parse_optional_float(raw["raw_z"]),
                    return_z=parse_optional_float(raw["return_z"]),
                    spread_ratio=parse_optional_float(raw["spread_ratio"]),
                    eligible=raw["eligible"].lower() == "true",
                )
            )
    return rows


def matched_control_threshold(
    features: dict[str, list[BarFeature]], train_start_ms: int, train_end_ms: int, k: float
) -> tuple[float, int, int]:
    primary_count = sum(
        1
        for rows in features.values()
        for row in rows
        if train_start_ms <= row.bar_ms < train_end_ms
        and row.eligible
        and row.raw_z is not None
        and abs(row.raw_z) >= k
    )
    scores = sorted(
        (
            abs(row.return_z)
            for rows in features.values()
            for row in rows
            if train_start_ms <= row.bar_ms < train_end_ms
            and row.eligible
            and row.return_z is not None
        ),
        reverse=True,
    )
    if primary_count <= 0 or not scores:
        return math.inf, primary_count, 0
    if primary_count >= len(scores):
        threshold = scores[-1]
    elif scores[primary_count - 1] != scores[primary_count]:
        threshold = (scores[primary_count - 1] + scores[primary_count]) / 2.0
    else:
        threshold = scores[primary_count - 1]
    control_count = sum(score >= threshold for score in scores)
    return threshold, primary_count, control_count


def signal_for(row: BarFeature, strategy: str, threshold: float) -> tuple[int, float]:
    if not row.eligible:
        return 0, 0.0
    score = row.raw_z if strategy == "PRIMARY" else row.return_z
    if score is None or abs(score) < threshold:
        return 0, float(score or 0.0)
    return (1 if score > 0 else -1), float(score)


def close_trade(position: dict[str, Any], row: BarFeature, price: float, reason: str) -> Trade:
    direction = int(position["direction"])
    pip_size = float(position["pip_size"])
    gross_pips = direction * (price - float(position["entry_price"])) / pip_size
    stop_pips = float(position["initial_stop_pips"])
    net_a = gross_pips - STRESS_A_PIPS
    net_b = gross_pips - STRESS_B_PIPS
    return Trade(
        strategy=str(position["strategy"]),
        symbol=str(position["symbol"]),
        signal_ms=int(position["signal_ms"]),
        entry_ms=int(position["entry_ms"]),
        exit_ms=row.bar_ms,
        direction=direction,
        signal_score=float(position["signal_score"]),
        entry_price=float(position["entry_price"]),
        exit_price=price,
        stop_price=float(position["stop_price"]),
        target_price=float(position["target_price"]),
        initial_stop_pips=stop_pips,
        exit_reason=reason,
        gross_pips=gross_pips,
        net_pips_a=net_a,
        net_pips_b=net_b,
        net_r_a=net_a / stop_pips if stop_pips > 0 else 0.0,
        net_r_b=net_b / stop_pips if stop_pips > 0 else 0.0,
    )


def simulate_symbol(rows: Sequence[BarFeature], strategy: str, threshold: float) -> list[Trade]:
    trades: list[Trade] = []
    position: dict[str, Any] | None = None
    pending: tuple[BarFeature, int, float] | None = None
    previous_ms: int | None = None
    for row in rows:
        contiguous = previous_ms is not None and row.bar_ms - previous_ms == BAR_MS
        closed_at_open = False
        if position is not None and (position.get("exit_at_open") or row.bar_ms >= position["time_exit_ms"]):
            side = row.first_bid if position["direction"] > 0 else row.first_ask
            reason = "opposite_signal" if position.get("exit_at_open") else "time_stop"
            trades.append(close_trade(position, row, side, reason))
            position = None
            closed_at_open = True
        if position is None and pending is not None and contiguous and not closed_at_open:
            signal_row, direction, score = pending
            entry = row.first_ask if direction > 0 else row.first_bid
            move_price = abs(signal_row.move_points) * signal_row.point
            stop_distance = 0.5 * move_price
            if stop_distance > 0:
                position = {
                    "strategy": strategy,
                    "symbol": row.symbol,
                    "signal_ms": signal_row.bar_ms,
                    "entry_ms": row.bar_ms,
                    "direction": direction,
                    "signal_score": score,
                    "entry_price": entry,
                    "stop_price": entry - direction * stop_distance,
                    "target_price": entry + direction * move_price,
                    "initial_stop_pips": stop_distance / row.pip_size,
                    "pip_size": row.pip_size,
                    "time_exit_ms": row.bar_ms + 2 * BAR_MS,
                    "exit_at_open": False,
                }
        pending = None
        if position is not None:
            direction = int(position["direction"])
            if direction > 0:
                stop_hit = row.bid_min <= position["stop_price"]
                target_hit = row.bid_max >= position["target_price"]
                stop_fill = float(position["stop_price"])
                target_fill = float(position["target_price"])
            else:
                stop_hit = row.ask_max >= position["stop_price"]
                target_hit = row.ask_min <= position["target_price"]
                stop_fill = float(position["stop_price"])
                target_fill = float(position["target_price"])
            if stop_hit:  # adverse-first if both barriers occur in one M15 bar
                trades.append(close_trade(position, row, stop_fill, "stop" if not target_hit else "both_hit_adverse_first"))
                position = None
            elif target_hit:
                trades.append(close_trade(position, row, target_fill, "target"))
                position = None
        direction, score = signal_for(row, strategy, threshold)
        if position is not None and direction == -int(position["direction"]):
            position["exit_at_open"] = True
        elif position is None and direction != 0:
            pending = (row, direction, score)
        previous_ms = row.bar_ms
    if position is not None and rows:
        row = rows[-1]
        side = row.last_bid if position["direction"] > 0 else row.last_ask
        trades.append(close_trade(position, row, side, "end_of_data"))
    return trades


def profit_factor(values: Sequence[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    if losses <= 0:
        return None if gains <= 0 else math.inf
    return gains / losses


def max_drawdown(values: Sequence[float]) -> float:
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def concentration_share(items: Sequence[tuple[str, float]]) -> float | None:
    buckets: dict[str, float] = {}
    for key, value in items:
        buckets[key] = buckets.get(key, 0.0) + value
    positive = [max(0.0, value) for value in buckets.values()]
    total = sum(positive)
    return max(positive) / total if total > 0 and positive else None


def summarize_trades(trades: Sequence[Trade], start_ms: int, end_ms: int) -> dict[str, Any]:
    selected = sorted((trade for trade in trades if start_ms <= trade.entry_ms < end_ms), key=lambda item: item.exit_ms)
    net_b = [trade.net_pips_b for trade in selected]
    net_r_b = [trade.net_r_b for trade in selected]
    weeks = (end_ms - start_ms) / (7 * 24 * 60 * 60 * 1000)
    return {
        "trades": len(selected),
        "elapsed_calendar_weeks": weeks,
        "trades_per_elapsed_week": len(selected) / weeks if weeks > 0 else None,
        "pf_stress_a": profit_factor([trade.net_pips_a for trade in selected]),
        "pf_stress_b": profit_factor(net_b),
        "expectancy_pips_stress_b": statistics.mean(net_b) if net_b else None,
        "expectancy_r_stress_b": statistics.mean(net_r_b) if net_r_b else None,
        "net_pips_stress_b": sum(net_b),
        "max_drawdown_r_stress_b": max_drawdown(net_r_b),
        "year_positive_pnl_concentration": concentration_share(
            [(str(datetime.fromtimestamp(trade.entry_ms / 1000, tz=timezone.utc).year), trade.net_pips_b) for trade in selected]
        ),
        "symbol_positive_pnl_concentration": concentration_share([(trade.symbol, trade.net_pips_b) for trade in selected]),
        "side_positive_pnl_concentration": concentration_share(
            [("LONG" if trade.direction > 0 else "SHORT", trade.net_pips_b) for trade in selected]
        ),
        "long_trades": sum(trade.direction > 0 for trade in selected),
        "short_trades": sum(trade.direction < 0 for trade in selected),
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def write_trades(path: Path, trades: Sequence[Trade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [field.name for field in fields(Trade)]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def gate_decision(primary: dict[str, Any], control: dict[str, Any], data_ok: bool) -> dict[str, Any]:
    holdout = primary["holdout"]
    pooled = primary["pooled"]
    control_holdout = control["holdout"]
    checks = {
        "data": data_ok,
        "cadence": pooled["trades_per_elapsed_week"] is not None
        and 2.0 <= pooled["trades_per_elapsed_week"] <= 5.5,
        "sample": pooled["trades"] >= 180 and holdout["trades"] >= 60,
        "pf_stress_b": holdout["pf_stress_b"] is not None
        and pooled["pf_stress_b"] is not None
        and holdout["pf_stress_b"] >= 1.20
        and pooled["pf_stress_b"] >= 1.25,
        "expectancy": holdout["expectancy_pips_stress_b"] is not None
        and holdout["expectancy_pips_stress_b"] > 0,
        "drawdown": pooled["max_drawdown_r_stress_b"] <= 8.0,
        "concentration": all(
            value is not None and value <= limit
            for value, limit in (
                (pooled["year_positive_pnl_concentration"], 0.45),
                (pooled["symbol_positive_pnl_concentration"], 0.70),
                (pooled["side_positive_pnl_concentration"], 0.70),
            )
        ),
        "beats_control_holdout": all(
            candidate is not None and comparator is not None and candidate > comparator
            for candidate, comparator in (
                (holdout["pf_stress_b"], control_holdout["pf_stress_b"]),
                (holdout["expectancy_pips_stress_b"], control_holdout["expectancy_pips_stress_b"]),
                (holdout["net_pips_stress_b"], control_holdout["net_pips_stress_b"]),
            )
        ),
    }
    return {
        "checks": checks,
        "verdict": "CONTINUE_TO_PREREG" if all(checks.values()) else "KILL_AT_OFFLINE_PROBE",
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def extract_features(args: argparse.Namespace) -> tuple[dict[str, list[BarFeature]], dict[str, Any]]:
    import MetaTrader5 as mt5

    if not mt5.initialize(path=args.terminal):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    features: dict[str, list[BarFeature]] = {}
    coverage: dict[str, Any] = {}
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        observed_server = getattr(account, "server", None)
        if observed_server != args.expected_server:
            raise RuntimeError(f"server mismatch: expected {args.expected_server}, observed {observed_server}")
        if not args.research_only:
            raise RuntimeError("--research-only is mandatory")
        for symbol in args.symbols:
            info = mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"symbol unavailable: {symbol}")
            point = float(info.point)
            pip_size = point * (10.0 if int(info.digits) in {3, 5} else 1.0)
            rows: list[BarFeature] = []
            month_stats: list[dict[str, Any]] = []
            for month_start, month_end in month_ranges(args.warmup_start_dt, args.end_dt):
                ticks = mt5.copy_ticks_range(
                    symbol,
                    month_start,
                    month_end - timedelta(milliseconds=1),
                    mt5.COPY_TICKS_ALL,
                )
                count = 0 if ticks is None else len(ticks)
                month_rows = aggregate_month(symbol, ticks, point, pip_size)
                rows.extend(month_rows)
                month_stats.append(
                    {
                        "month": month_start.strftime("%Y-%m"),
                        "ticks": count,
                        "bars": len(month_rows),
                        "last_error": list(mt5.last_error()),
                    }
                )
            rows.sort(key=lambda item: item.bar_ms)
            enrich_features(rows, args.c, args.n_min)
            features[symbol] = rows
            coverage[symbol] = {
                "months": month_stats,
                "empty_months": [item["month"] for item in month_stats if item["ticks"] <= 0],
                "ticks": sum(item["ticks"] for item in month_stats),
                "bars": len(rows),
                "eligible_bars": sum(row.eligible for row in rows),
            }
            write_features(args.output_dir / f"features_{symbol}.csv.gz", rows)
        metadata = {
            "observed_server": observed_server,
            "server_fingerprint": hashlib.sha256(str(observed_server).encode()).hexdigest().upper(),
            "account_fingerprint": hashlib.sha256(
                f"{getattr(account, 'login', '')}|{observed_server}".encode()
            ).hexdigest().upper(),
            "terminal_build": getattr(terminal, "build", None),
            "terminal_connected": getattr(terminal, "connected", None),
            "terminal_trade_allowed": getattr(terminal, "trade_allowed", None),
            "coverage": coverage,
            "safety": {"read_only": True, "orders_sent": 0, "positions_opened": 0, "live_trading_authorized": False},
        }
        return features, metadata
    finally:
        mt5.shutdown()


def load_cached_features(args: argparse.Namespace) -> dict[str, list[BarFeature]]:
    return {symbol: read_features(args.output_dir / f"features_{symbol}.csv.gz") for symbol in args.symbols}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", default=_default_terminal())
    parser.add_argument("--expected-server", required=True)
    parser.add_argument("--research-only", action="store_true")
    parser.add_argument("--symbols", nargs="+", default=["EURUSD", "GBPUSD"])
    parser.add_argument("--warmup-start", default="2017-12-01T00:00:00Z")
    parser.add_argument("--train-start", default="2018-01-01T00:00:00Z")
    parser.add_argument("--train-end", default="2023-01-01T00:00:00Z")
    parser.add_argument("--end", default="2026-01-01T00:00:00Z")
    parser.add_argument("--k", type=float, default=2.7)
    parser.add_argument("--c", type=float, default=1.5)
    parser.add_argument("--n-min", type=int, default=30)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reuse-features", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.warmup_start_dt = datetime.fromisoformat(args.warmup_start.replace("Z", "+00:00"))
    args.end_dt = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_start_ms = utc_ms(args.train_start)
    train_end_ms = utc_ms(args.train_end)
    end_ms = utc_ms(args.end)
    if args.reuse_features:
        features = load_cached_features(args)
        mt5_metadata: dict[str, Any] = {"reused_features": True, "coverage": {}}
    else:
        features, mt5_metadata = extract_features(args)
    control_threshold, primary_train_count, control_train_count = matched_control_threshold(
        features, train_start_ms, train_end_ms, args.k
    )
    primary_trades: list[Trade] = []
    control_trades: list[Trade] = []
    for symbol in args.symbols:
        primary_trades.extend(simulate_symbol(features[symbol], "PRIMARY", args.k))
        control_trades.extend(simulate_symbol(features[symbol], "RETURN_CONTROL", control_threshold))
    primary_trades.sort(key=lambda item: item.exit_ms)
    control_trades.sort(key=lambda item: item.exit_ms)
    write_trades(args.output_dir / "trades_primary.csv", primary_trades)
    write_trades(args.output_dir / "trades_return_control.csv", control_trades)
    splits = {
        "train": (train_start_ms, train_end_ms),
        "holdout": (train_end_ms, end_ms),
        "pooled": (train_start_ms, end_ms),
    }
    primary_summary = {name: summarize_trades(primary_trades, *bounds) for name, bounds in splits.items()}
    control_summary = {name: summarize_trades(control_trades, *bounds) for name, bounds in splits.items()}
    coverage = mt5_metadata.get("coverage", {})
    data_ok = bool(coverage) and all(not coverage[symbol]["empty_months"] for symbol in args.symbols)
    decision = gate_decision(primary_summary, control_summary, data_ok)
    artifact_paths = [
        *(args.output_dir / f"features_{symbol}.csv.gz" for symbol in args.symbols),
        args.output_dir / "trades_primary.csv",
        args.output_dir / "trades_return_control.csv",
    ]
    summary = {
        "schema_version": "alphafactory_impact_pressure_probe.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "producer": {"path": str(Path(__file__).resolve()), "sha256": sha256_file(Path(__file__).resolve())},
        "status": "RESEARCH_ONLY_WRONG_BROKER_ALLOWED_FOR_FALSIFICATION",
        "contract": {
            "symbols": args.symbols,
            "timeframe": "M15",
            "warmup_start": args.warmup_start,
            "train": [args.train_start, args.train_end],
            "holdout": [args.train_end, args.end],
            "k": args.k,
            "c": args.c,
            "n_min": args.n_min,
            "stop_move_multiple": 0.5,
            "target_move_multiple": 1.0,
            "time_stop_bars": 2,
            "same_bar_both_hit_policy": "ADVERSE_FIRST",
            "stress_a_pips_round_turn": STRESS_A_PIPS,
            "stress_b_pips_round_turn": STRESS_B_PIPS,
            "control": "robust-z close-to-close return; train threshold matched to primary train signal count",
        },
        "proxy_identity_warning": {
            "q_definition": "sign(mid_t-mid_t-1)",
            "independent_order_flow_observed": False,
            "interpretation": "price-path transform; cited institutional order-flow evidence does not transfer automatically",
        },
        "control_matching": {
            "threshold": control_threshold,
            "primary_train_signal_count": primary_train_count,
            "control_train_signal_count": control_train_count,
        },
        "mt5": mt5_metadata,
        "primary": primary_summary,
        "return_control": control_summary,
        "decision": decision,
        "authorization": {
            "candidate_registry_or_prereg": decision["verdict"] == "CONTINUE_TO_PREREG",
            "ea_code_compile_backtest": False,
            "promotion": False,
            "live_trading": False,
        },
        "artifacts": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in artifact_paths
        ],
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(json_safe(summary), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "verdict": decision["verdict"], "failed_checks": decision["failed_checks"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
