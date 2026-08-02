#!/usr/bin/env python3
"""Build explicitly non-promotable XAU cost-proxy evidence on the D: workspace.

The slippage leg measures direction-aware adverse movement from a reference
quote to the first executable quote after a fixed latency.  It never labels a
future quote as an observed fill.  The commission leg takes the maximum
same-symbol round-turn-per-lot value from a legacy Strategy Tester trade log.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


QUOTE_FIELDS = (
    "sample_id",
    "reference_timestamp",
    "future_timestamp",
    "symbol",
    "side",
    "reference_side",
    "reference_price",
    "future_quote_price",
    "pip_size",
    "latency_ms",
    "actual_delay_ms",
)
COMMISSION_FIELDS = (
    "position_id",
    "symbol",
    "account_currency",
    "round_turn_account_per_lot",
    "source_kind",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def nearest_rank_p90(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("P90 requires at least one value")
    return ordered[max(0, math.ceil(0.90 * len(ordered)) - 1)]


def iso_millis(epoch_ms: int) -> str:
    return (
        datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="milliseconds")
    )


def atomic_csv(path: Path, fieldnames: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def slice_spread_evidence(
    source: Path, output: Path, symbol: str, date_from: str, date_to: str
) -> dict[str, Any]:
    start = datetime.strptime(date_from, "%Y.%m.%d").date()
    end = datetime.strptime(date_to, "%Y.%m.%d").date()
    if end < start:
        raise ValueError("spread slice end precedes start")
    if source.resolve() == output.resolve():
        count = 0
        first_timestamp = ""
        last_timestamp = ""
        with source.open("r", encoding="utf-8-sig", newline="") as input_handle:
            reader = csv.DictReader(input_handle)
            required = {"timestamp", "symbol", "bid", "ask"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"spread source is missing columns: {sorted(missing)}")
            for row_number, row in enumerate(reader, start=2):
                timestamp = datetime.fromisoformat(str(row.get("timestamp") or "").removesuffix("Z"))
                if not start <= timestamp.date() <= end:
                    raise ValueError(
                        f"in-place spread source row {row_number} is outside the requested slice"
                    )
                if str(row.get("symbol") or "") != symbol:
                    raise ValueError(f"spread source row {row_number} symbol mismatch")
                bid = float(str(row.get("bid") or "nan"))
                ask = float(str(row.get("ask") or "nan"))
                if not math.isfinite(bid) or not math.isfinite(ask) or not 0 < bid <= ask:
                    raise ValueError(f"spread source row {row_number} has invalid BID/ASK")
                count += 1
                first_timestamp = first_timestamp or str(row["timestamp"])
                last_timestamp = str(row["timestamp"])
        if count <= 0:
            raise ValueError("spread slice contains no rows")
        return {
            "from": date_from,
            "to": date_to,
            "sample_count": count,
            "total_count": count,
            "coverage_ratio": 1.0,
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    count = 0
    first_timestamp = ""
    last_timestamp = ""
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as input_handle, temporary.open(
            "w", encoding="utf-8", newline=""
        ) as output_handle:
            reader = csv.DictReader(input_handle)
            required = {"timestamp", "symbol", "bid", "ask"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"spread source is missing columns: {sorted(missing)}")
            writer = csv.DictWriter(output_handle, fieldnames=["timestamp", "symbol", "bid", "ask"])
            writer.writeheader()
            for row_number, row in enumerate(reader, start=2):
                timestamp = datetime.fromisoformat(str(row.get("timestamp") or "").removesuffix("Z"))
                if not start <= timestamp.date() <= end:
                    continue
                if str(row.get("symbol") or "") != symbol:
                    raise ValueError(f"spread source row {row_number} symbol mismatch")
                bid = float(str(row.get("bid") or "nan"))
                ask = float(str(row.get("ask") or "nan"))
                if not math.isfinite(bid) or not math.isfinite(ask) or not 0 < bid <= ask:
                    raise ValueError(f"spread source row {row_number} has invalid BID/ASK")
                writer.writerow(
                    {
                        "timestamp": row["timestamp"],
                        "symbol": symbol,
                        "bid": row["bid"],
                        "ask": row["ask"],
                    }
                )
                count += 1
                first_timestamp = first_timestamp or str(row["timestamp"])
                last_timestamp = str(row["timestamp"])
        if count <= 0:
            raise ValueError("spread slice contains no rows")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "from": date_from,
        "to": date_to,
        "sample_count": count,
        "total_count": count,
        "coverage_ratio": 1.0,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
    }


def load_unique_quotes(
    root: Path | None,
    symbol: str,
    explicit_sources: Iterable[Path] = (),
) -> tuple[list[tuple[int, float, float]], list[Path]]:
    selected_sources = [Path(path).resolve() for path in explicit_sources]
    if selected_sources:
        sources = sorted(selected_sources, key=lambda path: str(path).lower())
    elif root is not None:
        sources = sorted(root.rglob(f"{symbol}_quote_ticks.csv"), key=lambda path: str(path).lower())
    else:
        sources = []
    if not sources:
        raise ValueError(f"no {symbol} quote CSVs were selected")
    if len({str(path).lower() for path in sources}) != len(sources):
        raise ValueError("quote source selection contains duplicate paths")
    unique: dict[tuple[int, float, float], tuple[int, float, float]] = {}
    for source in sources:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"time_msc", "bid", "ask", "symbol"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"quote source {source} is missing columns: {sorted(missing)}")
            for row_number, row in enumerate(reader, start=2):
                if str(row.get("symbol") or "") != symbol:
                    raise ValueError(f"quote source {source} row {row_number} symbol mismatch")
                timestamp = int(float(str(row.get("time_msc") or "")))
                bid = float(str(row.get("bid") or "nan"))
                ask = float(str(row.get("ask") or "nan"))
                if not math.isfinite(bid) or not math.isfinite(ask) or not 0 < bid <= ask:
                    raise ValueError(f"quote source {source} row {row_number} has invalid BID/ASK")
                unique[(timestamp, bid, ask)] = (timestamp, bid, ask)
    quotes = sorted(unique.values())
    if len(quotes) < 100:
        raise ValueError("quote evidence has fewer than 100 unique observations")
    return quotes, sources


def build_quote_proxy(
    quotes: list[tuple[int, float, float]],
    symbol: str,
    pip_size: float,
    latency_ms: int,
    max_wait_ms: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if pip_size <= 0 or latency_ms <= 0 or max_wait_ms < 0:
        raise ValueError("invalid quote-proxy geometry or latency contract")
    times = [row[0] for row in quotes]
    output: list[dict[str, Any]] = []
    adverse: dict[str, list[float]] = {"BUY": [], "SELL": []}
    pair_index = 0
    index = 0
    while index < len(quotes):
        reference = quotes[index]
        future_index = bisect.bisect_left(times, reference[0] + latency_ms, index + 1)
        if future_index >= len(quotes):
            break
        future = quotes[future_index]
        actual_delay_ms = future[0] - reference[0]
        if actual_delay_ms > latency_ms + max_wait_ms:
            index += 1
            continue
        pair_index += 1
        for side, price_index, reference_side in (("BUY", 2, "ask"), ("SELL", 1, "bid")):
            reference_price = reference[price_index]
            future_price = future[price_index]
            adverse_pips = (
                max(0.0, (future_price - reference_price) / pip_size)
                if side == "BUY"
                else max(0.0, (reference_price - future_price) / pip_size)
            )
            adverse[side].append(adverse_pips)
            output.append(
                {
                    "sample_id": f"Q{pair_index:06d}-{side}",
                    "reference_timestamp": iso_millis(reference[0]),
                    "future_timestamp": iso_millis(future[0]),
                    "symbol": symbol,
                    "side": side,
                    "reference_side": reference_side,
                    "reference_price": f"{reference_price:.8f}",
                    "future_quote_price": f"{future_price:.8f}",
                    "pip_size": f"{pip_size:.8f}",
                    "latency_ms": latency_ms,
                    "actual_delay_ms": actual_delay_ms,
                }
            )
        index = future_index
    if pair_index < 50:
        raise ValueError("fixed-latency quote proxy has fewer than 50 non-overlapping pairs")
    buy_p90 = nearest_rank_p90(adverse["BUY"])
    sell_p90 = nearest_rank_p90(adverse["SELL"])
    return output, {
        "pair_count": pair_index,
        "sample_count": len(output),
        "buy_count": len(adverse["BUY"]),
        "sell_count": len(adverse["SELL"]),
        "p90_buy": buy_p90,
        "p90_sell": sell_p90,
        "p90_roundturn": buy_p90 + sell_p90,
        "latency_ms": latency_ms,
        "max_quote_wait_ms": max_wait_ms,
        "first_reference_timestamp": output[0]["reference_timestamp"],
        "last_reference_timestamp": output[-1]["reference_timestamp"],
    }


def build_commission_proxy(
    source: Path, symbol: str, account_currency: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"position_id", "symbol", "volume", "commission", "is_final_close"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"legacy trades source is missing columns: {sorted(missing)}")
        lifecycle_rows: dict[str, list[tuple[int, dict[str, str]]]] = {}
        for row_number, row in enumerate(reader, start=2):
            if str(row.get("symbol") or "") != symbol:
                continue
            position_id = str(row.get("position_id") or "").strip()
            if not position_id:
                raise ValueError(f"legacy trades row {row_number} has an empty position_id")
            volume = float(str(row.get("volume") or "nan"))
            commission = float(str(row.get("commission") or "nan"))
            if not math.isfinite(volume) or not math.isfinite(commission) or volume <= 0:
                raise ValueError(f"legacy trades row {row_number} has invalid volume/commission")
            lifecycle_rows.setdefault(position_id, []).append((row_number, dict(row)))

        rows: list[dict[str, Any]] = []
        for position_id, lifecycle in lifecycle_rows.items():
            final_rows = [
                row_number
                for row_number, row in lifecycle
                if str(row.get("is_final_close") or "").strip() == "1"
            ]
            if len(final_rows) != 1:
                raise ValueError(
                    f"legacy position {position_id} needs exactly one final close; "
                    f"found {len(final_rows)}"
                )
            entry_volumes = [
                float(str(row.get("volume") or "nan"))
                for _, row in lifecycle
                if str(row.get("action") or "").strip().upper() == "OPEN"
                or str(row.get("entry_kind") or "").strip().upper()
                in {"IN", "DEAL_ENTRY_IN", "ENTRY"}
            ]
            if not entry_volumes:
                raise ValueError(
                    f"legacy position {position_id} has no explicit entry-volume row; "
                    "refusing to infer lifecycle volume from entry and exit rows"
                )
            lifecycle_volume = sum(entry_volumes)
            lifecycle_commission = sum(
                abs(float(str(row.get("commission") or "nan"))) for _, row in lifecycle
            )
            per_lot = lifecycle_commission / lifecycle_volume
            if per_lot <= 0:
                raise ValueError(
                    f"legacy position {position_id} has nonpositive lifecycle commission proxy"
                )
            rows.append(
                {
                    "position_id": position_id,
                    "symbol": symbol,
                    "account_currency": account_currency,
                    "round_turn_account_per_lot": f"{per_lot:.8f}",
                    "source_kind": "strategy_tester_simulation",
                }
            )
    rows.sort(key=lambda row: str(row["position_id"]))
    if len(rows) < 30:
        raise ValueError("legacy tester commission proxy has fewer than 30 lifecycles")
    values = [float(row["round_turn_account_per_lot"]) for row in rows]
    return rows, {
        "sample_count": len(rows),
        "minimum": min(values),
        "p50": sorted(values)[(len(values) - 1) // 2],
        "p90": nearest_rank_p90(values),
        "maximum": max(values),
        "statistic_used": "maximum",
        "source_kind": "strategy_tester_simulation",
    }


def display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quotes-root")
    parser.add_argument("--quote-source", action="append", default=[])
    parser.add_argument("--legacy-trades", required=True)
    parser.add_argument("--spread-source", required=True)
    parser.add_argument("--spread-from", required=True)
    parser.add_argument("--spread-to", required=True)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--account-currency", default="USD")
    parser.add_argument("--pip-size", type=float, default=0.01)
    parser.add_argument("--latency-ms", type=int, default=1000)
    parser.add_argument("--max-wait-ms", type=int, default=500)
    parser.add_argument("--slippage-out", required=True)
    parser.add_argument("--commission-out", required=True)
    parser.add_argument("--spread-out", required=True)
    parser.add_argument("--receipt-out", required=True)
    args = parser.parse_args()

    repo_root = ALPHA_ROOT = Path(__file__).resolve().parents[2]
    quotes_root = Path(args.quotes_root).resolve() if args.quotes_root else None
    quote_sources_selected = [Path(path).resolve() for path in args.quote_source]
    if quotes_root is None and not quote_sources_selected:
        raise ValueError("either --quotes-root or at least one --quote-source is required")
    legacy_trades = Path(args.legacy_trades).resolve()
    spread_source = Path(args.spread_source).resolve()
    slippage_out = Path(args.slippage_out).resolve()
    commission_out = Path(args.commission_out).resolve()
    spread_out = Path(args.spread_out).resolve()
    receipt_out = Path(args.receipt_out).resolve()

    quotes, quote_sources = load_unique_quotes(
        quotes_root, args.symbol, quote_sources_selected
    )
    quote_rows, quote_summary = build_quote_proxy(
        quotes,
        args.symbol,
        args.pip_size,
        args.latency_ms,
        args.max_wait_ms,
    )
    commission_rows, commission_summary = build_commission_proxy(
        legacy_trades, args.symbol, args.account_currency
    )
    spread_summary = slice_spread_evidence(
        spread_source, spread_out, args.symbol, args.spread_from, args.spread_to
    )
    atomic_csv(slippage_out, QUOTE_FIELDS, quote_rows)
    atomic_csv(commission_out, COMMISSION_FIELDS, commission_rows)
    raw_quote_sources = [
        {
            "path": display_path(path, repo_root),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in quote_sources
    ]
    receipt = {
        "schema_version": "alphafactory_research_cost_proxy_evidence.v1",
        "promotion_eligible": False,
        "fill_observed": False,
        "symbol": args.symbol,
        "quote_input": {
            "root": display_path(quotes_root, repo_root) if quotes_root is not None else None,
            "selection_mode": "explicit_sources" if quote_sources_selected else "recursive_root",
            "source_count": len(quote_sources),
            "unique_quote_count": len(quotes),
            "sources": raw_quote_sources,
        },
        "quote_latency_proxy": {
            **quote_summary,
            "output": display_path(slippage_out, repo_root),
            "output_sha256": sha256_file(slippage_out),
        },
        "historical_spread": {
            **spread_summary,
            "raw_source": display_path(spread_source, repo_root),
            "raw_source_sha256": sha256_file(spread_source),
            "output": display_path(spread_out, repo_root),
            "output_sha256": sha256_file(spread_out),
        },
        "tester_commission_proxy": {
            **commission_summary,
            "raw_source": display_path(legacy_trades, repo_root),
            "raw_source_sha256": sha256_file(legacy_trades),
            "output": display_path(commission_out, repo_root),
            "output_sha256": sha256_file(commission_out),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": display_path(Path(__file__), repo_root),
        "generator_sha256": sha256_file(Path(__file__)),
    }
    atomic_json(receipt_out, receipt)
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
