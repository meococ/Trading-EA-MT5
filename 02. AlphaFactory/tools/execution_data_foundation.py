#!/usr/bin/env python3
"""Read-only execution-data probe, inventory, and fail-closed bundle validator.

This tool never places, modifies, or closes an order. Its MT5 surface is limited
to terminal/account metadata, symbol metadata, quote history, and account-history
counts. Raw account identifiers and individual trade rows are never emitted by
the probe command.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


TOOLS_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = TOOLS_DIR.parent
REPO_ROOT = ALPHA_ROOT.parent
SCHEMA_PATH = ALPHA_ROOT / "schemas" / "execution_data_capture_manifest.v1.schema.json"
MANIFEST_SCHEMA = "alphafactory_execution_data_capture.v1"
INVENTORY_SCHEMA = "alphafactory_execution_data_inventory.v1"
PROBE_SCHEMA = "alphafactory_mt5_readonly_probe.v1"

TICK_FIELDS = {
    "time_msc",
    "time_utc",
    "symbol",
    "bid",
    "ask",
    "last",
    "volume_real",
    "flags",
}
HEARTBEAT_FIELDS = {
    "time_msc",
    "time_utc",
    "connected",
    "server_fingerprint",
    "terminal_build",
}
COMMISSION_FIELDS = {
    "position_id",
    "symbol",
    "account_currency",
    "round_turn_account_per_lot",
    "conversion_method",
    "open_time_utc",
    "close_time_utc",
    "source",
}
SLIPPAGE_FIELDS = {
    "fill_id",
    "symbol",
    "side",
    "reference_side",
    "reference_time_msc",
    "request_time_msc",
    "fill_time_msc",
    "reference_price",
    "fill_price",
    "pip_size",
    "source",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def positive(value: Any, label: str) -> float:
    number = finite(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be > 0")
    return number


def integer(value: Any, label: str) -> int:
    number = finite(value, label)
    if not number.is_integer():
        raise ValueError(f"{label} must be an integer")
    return int(number)


def parse_utc(value: Any, label: str) -> datetime:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def open_csv(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    return path.open("r", encoding="utf-8-sig", newline="")


def read_rows(path: Path, required: set[str], label: str) -> list[dict[str, str]]:
    with open_csv(path) as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"{label} missing columns: {missing}")
        rows = [dict(row) for row in reader]
    return rows


def percentile(values: Iterable[float], fraction: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def resolve_artifact(
    node: dict[str, Any], manifest_path: Path, label: str
) -> Path | None:
    # A PARTIAL artifact is still evidence and must be integrity/content checked.
    # Its status remains a promotion blocker below, but skipping the file here
    # would let malformed or mis-clocked smoke captures evade validation.
    if node.get("status") not in {"AVAILABLE", "PARTIAL"}:
        return None
    path = Path(str(node.get("path") or ""))
    if not path.is_absolute():
        path = manifest_path.parent / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"{label} file does not exist: {path}")
    expected = str(node.get("sha256") or "").upper()
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} sha256 mismatch")
    return path


def verify_declared_rows(node: dict[str, Any], actual: int, label: str) -> None:
    declared = integer(node.get("row_count"), f"{label}.row_count")
    if declared != actual:
        raise ValueError(f"{label}.row_count mismatch: {declared} != {actual}")


def validate_ticks(
    path: Path, node: dict[str, Any], symbol: str
) -> dict[str, Any]:
    rows = read_rows(path, TICK_FIELDS, "quote_ticks")
    verify_declared_rows(node, len(rows), "quote_ticks")
    if not rows:
        raise ValueError("quote_ticks contains no rows")
    last_msc: int | None = None
    spreads: list[float] = []
    first_msc: int | None = None
    for index, row in enumerate(rows, start=2):
        if str(row.get("symbol") or "") != symbol:
            raise ValueError(f"quote_ticks row {index} symbol mismatch")
        time_msc = integer(row.get("time_msc"), f"quote_ticks row {index} time_msc")
        if last_msc is not None and time_msc <= last_msc:
            raise ValueError(f"quote_ticks row {index} is not strictly monotonic")
        expected_time = datetime.fromtimestamp(time_msc / 1000.0, tz=timezone.utc)
        actual_time = parse_utc(row.get("time_utc"), f"quote_ticks row {index} time_utc")
        if abs((actual_time - expected_time).total_seconds()) > 0.001:
            raise ValueError(f"quote_ticks row {index} time_utc/time_msc mismatch")
        bid = positive(row.get("bid"), f"quote_ticks row {index} bid")
        ask = positive(row.get("ask"), f"quote_ticks row {index} ask")
        if ask < bid:
            raise ValueError(f"quote_ticks row {index} ask < bid")
        spreads.append(ask - bid)
        first_msc = time_msc if first_msc is None else first_msc
        last_msc = time_msc
    assert first_msc is not None and last_msc is not None
    return {
        "row_count": len(rows),
        "from_time_msc": first_msc,
        "to_time_msc": last_msc,
        "from_utc": iso_utc(datetime.fromtimestamp(first_msc / 1000.0, tz=timezone.utc)),
        "to_utc": iso_utc(datetime.fromtimestamp(last_msc / 1000.0, tz=timezone.utc)),
        "elapsed_days": (last_msc - first_msc) / 86_400_000.0,
        "spread_price_p50": percentile(spreads, 0.50),
        "spread_price_p90": percentile(spreads, 0.90),
    }


def validate_heartbeats(
    path: Path,
    node: dict[str, Any],
    expected_server_fingerprint: str,
) -> dict[str, Any]:
    rows = read_rows(path, HEARTBEAT_FIELDS, "heartbeats")
    verify_declared_rows(node, len(rows), "heartbeats")
    if not rows:
        raise ValueError("heartbeats contains no rows")
    last_msc: int | None = None
    first_msc: int | None = None
    connected = 0
    max_gap_ms = 0
    for index, row in enumerate(rows, start=2):
        time_msc = integer(row.get("time_msc"), f"heartbeats row {index} time_msc")
        if last_msc is not None:
            if time_msc < last_msc:
                raise ValueError(f"heartbeats row {index} is not monotonic")
            max_gap_ms = max(max_gap_ms, time_msc - last_msc)
        expected_time = datetime.fromtimestamp(time_msc / 1000.0, tz=timezone.utc)
        actual_time = parse_utc(row.get("time_utc"), f"heartbeats row {index} time_utc")
        if abs((actual_time - expected_time).total_seconds()) > 0.001:
            raise ValueError(f"heartbeats row {index} time_utc/time_msc mismatch")
        if str(row.get("server_fingerprint") or "").upper() != expected_server_fingerprint.upper():
            raise ValueError(f"heartbeats row {index} server fingerprint mismatch")
        state = str(row.get("connected") or "").strip().lower()
        if state not in {"0", "1", "false", "true"}:
            raise ValueError(f"heartbeats row {index} connected is invalid")
        connected += int(state in {"1", "true"})
        first_msc = time_msc if first_msc is None else first_msc
        last_msc = time_msc
    assert first_msc is not None and last_msc is not None
    return {
        "row_count": len(rows),
        "connected_count": connected,
        "connected_ratio": connected / len(rows),
        "elapsed_days": (last_msc - first_msc) / 86_400_000.0,
        "maximum_gap_ms": max_gap_ms,
    }


def validate_commission(
    path: Path,
    node: dict[str, Any],
    symbol: str,
    account_currency: str,
) -> dict[str, Any]:
    rows = read_rows(path, COMMISSION_FIELDS, "commission_lifecycles")
    verify_declared_rows(node, len(rows), "commission_lifecycles")
    ids: set[str] = set()
    values: list[float] = []
    for index, row in enumerate(rows, start=2):
        position_id = str(row.get("position_id") or "").strip()
        if not position_id or position_id in ids:
            raise ValueError(f"commission row {index} duplicate/empty position_id")
        ids.add(position_id)
        if str(row.get("symbol") or "") != symbol:
            raise ValueError(f"commission row {index} symbol mismatch")
        if str(row.get("account_currency") or "") != account_currency:
            raise ValueError(f"commission row {index} account currency mismatch")
        if str(row.get("conversion_method") or "") != "per_trade_contemporaneous":
            raise ValueError(f"commission row {index} conversion method is not contemporaneous")
        if not str(row.get("source") or "").strip():
            raise ValueError(f"commission row {index} source is empty")
        open_time = parse_utc(row.get("open_time_utc"), f"commission row {index} open_time")
        close_time = parse_utc(row.get("close_time_utc"), f"commission row {index} close_time")
        if close_time < open_time:
            raise ValueError(f"commission row {index} closes before it opens")
        values.append(
            positive(
                row.get("round_turn_account_per_lot"),
                f"commission row {index} round_turn_account_per_lot",
            )
        )
    return {
        "lifecycle_count": len(rows),
        "p50_round_turn_account_per_lot": percentile(values, 0.50),
        "p90_round_turn_account_per_lot": percentile(values, 0.90),
    }


def validate_slippage(
    path: Path,
    node: dict[str, Any],
    symbol: str,
    expected_pip_size: float,
    maximum_reference_age_ms: int,
) -> dict[str, Any]:
    rows = read_rows(path, SLIPPAGE_FIELDS, "slippage_fills")
    verify_declared_rows(node, len(rows), "slippage_fills")
    ids: set[str] = set()
    buy_values: list[float] = []
    sell_values: list[float] = []
    for index, row in enumerate(rows, start=2):
        fill_id = str(row.get("fill_id") or "").strip()
        if not fill_id or fill_id in ids:
            raise ValueError(f"slippage row {index} duplicate/empty fill_id")
        ids.add(fill_id)
        if str(row.get("symbol") or "") != symbol:
            raise ValueError(f"slippage row {index} symbol mismatch")
        if not str(row.get("source") or "").strip():
            raise ValueError(f"slippage row {index} source is empty")
        side = str(row.get("side") or "").upper()
        reference_side = str(row.get("reference_side") or "").upper()
        if (side, reference_side) not in {("BUY", "ASK"), ("SELL", "BID")}:
            raise ValueError(f"slippage row {index} side/reference pairing is invalid")
        reference_time = integer(
            row.get("reference_time_msc"), f"slippage row {index} reference_time_msc"
        )
        request_time = integer(
            row.get("request_time_msc"), f"slippage row {index} request_time_msc"
        )
        fill_time = integer(
            row.get("fill_time_msc"), f"slippage row {index} fill_time_msc"
        )
        if not reference_time <= request_time <= fill_time:
            raise ValueError(f"slippage row {index} timestamps are not decision-time safe")
        if request_time - reference_time > maximum_reference_age_ms:
            raise ValueError(f"slippage row {index} reference is too stale")
        pip_size = positive(row.get("pip_size"), f"slippage row {index} pip_size")
        if not math.isclose(pip_size, expected_pip_size, rel_tol=0, abs_tol=1e-12):
            raise ValueError(f"slippage row {index} pip_size mismatch")
        reference = positive(
            row.get("reference_price"), f"slippage row {index} reference_price"
        )
        fill = positive(row.get("fill_price"), f"slippage row {index} fill_price")
        adverse = max(
            (fill - reference) / pip_size
            if side == "BUY"
            else (reference - fill) / pip_size,
            0.0,
        )
        (buy_values if side == "BUY" else sell_values).append(adverse)
    return {
        "sample_count": len(rows),
        "buy_count": len(buy_values),
        "sell_count": len(sell_values),
        "p90_buy_adverse_pips": percentile(buy_values, 0.90),
        "p90_sell_adverse_pips": percentile(sell_values, 0.90),
    }


def validate_schema(payload: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if errors:
        snippets = []
        for error in errors[:10]:
            path = ".".join(str(part) for part in error.path) or "$"
            snippets.append(f"{path}: {error.message}")
        raise ValueError("manifest schema invalid: " + "; ".join(snippets))


def validate_bundle(manifest_path: Path) -> dict[str, Any]:
    payload = load_json(manifest_path)
    validate_schema(payload)
    if payload.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("unsupported manifest schema")
    gates = payload["research_gates"]
    broker = payload["broker_identity"]
    manifest_created_msc = int(
        parse_utc(payload["created_at_utc"], "created_at_utc").timestamp() * 1000
    )
    server_match = broker["expected_server"] == broker["observed_server"]
    results: list[dict[str, Any]] = []
    symbols_seen = [str(item.get("symbol") or "") for item in payload["symbols"]]
    if len(symbols_seen) != len(set(symbols_seen)):
        raise ValueError("manifest contains duplicate symbols")
    required_symbols = (
        {"EURUSD", "GBPUSD", "XAUUSD"}
        if payload["purpose"] == "QFSI_DATA_FEASIBILITY_ONLY"
        else {"XAUUSD"}
    )
    missing_required_symbols = sorted(required_symbols - set(symbols_seen))
    global_blockers = (
        ["MISSING_REQUIRED_SYMBOLS:" + ",".join(missing_required_symbols)]
        if missing_required_symbols
        else []
    )
    for item in payload["symbols"]:
        symbol = item["symbol"]
        blockers: list[str] = []
        metrics: dict[str, Any] = {}
        if not server_match:
            blockers.append("BROKER_SERVER_MISMATCH")
        if item["quote_ticks"].get("completeness_method") not in {
            "PASSIVE_HEARTBEAT",
            "VENUE_SEQUENCE_NUMBERS",
        }:
            blockers.append("QUOTE_COMPLETENESS_UNPROVEN")
        for key, validator in (
            (
                "quote_ticks",
                lambda path, node: validate_ticks(path, node, symbol),
            ),
            (
                "heartbeats",
                lambda path, node: validate_heartbeats(
                    path, node, broker["server_fingerprint"]
                ),
            ),
            (
                "commission_lifecycles",
                lambda path, node: validate_commission(
                    path, node, symbol, broker["account_currency"]
                ),
            ),
            (
                "slippage_fills",
                lambda path, node: validate_slippage(
                    path,
                    node,
                    symbol,
                    float(item["pip_size"]),
                    int(gates["maximum_reference_age_ms"]),
                ),
            ),
        ):
            node = item[key]
            status = str(node.get("status") or "MISSING")
            if status != "AVAILABLE":
                blockers.append(f"{key.upper()}_{status}")
            path = resolve_artifact(node, manifest_path, f"{symbol}.{key}")
            if path is None:
                continue
            metrics[key] = validator(path, node)
        ticks = metrics.get("quote_ticks") or {}
        heartbeats = metrics.get("heartbeats") or {}
        commission = metrics.get("commission_lifecycles") or {}
        slippage = metrics.get("slippage_fills") or {}
        if ticks and ticks.get("elapsed_days", 0) < gates["minimum_quote_elapsed_days"]:
            blockers.append("QUOTE_WINDOW_TOO_SHORT")
        if ticks and ticks.get("to_time_msc", 0) > manifest_created_msc + 1000:
            blockers.append("QUOTE_CLOCK_FUTURE_OF_MANIFEST")
        if ticks:
            elapsed = max(float(ticks.get("elapsed_days", 0)), 1.0)
            if ticks.get("row_count", 0) / elapsed < gates["minimum_quote_rows_per_elapsed_day"]:
                blockers.append("QUOTE_DENSITY_TOO_LOW")
        if heartbeats and heartbeats.get("connected_ratio", 0) < gates["minimum_connected_heartbeat_ratio"]:
            blockers.append("HEARTBEAT_CONNECTED_RATIO_LOW")
        if heartbeats and heartbeats.get("elapsed_days", 0) < gates["minimum_quote_elapsed_days"]:
            blockers.append("HEARTBEAT_WINDOW_TOO_SHORT")
        if heartbeats and heartbeats.get("maximum_gap_ms", 0) > gates["maximum_heartbeat_gap_ms"]:
            blockers.append("HEARTBEAT_GAP_TOO_LARGE")
        if commission and commission.get("lifecycle_count", 0) < gates["minimum_commission_lifecycles_per_symbol"]:
            blockers.append("COMMISSION_SAMPLE_TOO_SMALL")
        if slippage:
            if slippage.get("sample_count", 0) < gates["minimum_slippage_fills_per_symbol"]:
                blockers.append("SLIPPAGE_SAMPLE_TOO_SMALL")
            if slippage.get("buy_count", 0) < gates["minimum_slippage_buys_per_symbol"]:
                blockers.append("SLIPPAGE_BUY_SAMPLE_TOO_SMALL")
            if slippage.get("sell_count", 0) < gates["minimum_slippage_sells_per_symbol"]:
                blockers.append("SLIPPAGE_SELL_SAMPLE_TOO_SMALL")
        unique_blockers = sorted(set(blockers + global_blockers))
        results.append(
            {
                "symbol": symbol,
                "verdict": "GO_FOR_PREREG_DESIGN" if not unique_blockers else "BLOCKED",
                "blockers": unique_blockers,
                "metrics": metrics,
            }
        )
    overall = (
        "GO_FOR_PREREG_DESIGN"
        if results and all(item["verdict"] == "GO_FOR_PREREG_DESIGN" for item in results)
        else "STOP_DATA_FRONTIER"
    )
    return {
        "schema_version": "alphafactory_execution_data_validation.v1",
        "created_at_utc": iso_utc(utc_now()),
        "producer": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "manifest_schema": {
            "path": str(SCHEMA_PATH.resolve()),
            "sha256": sha256_file(SCHEMA_PATH),
        },
        "manifest": str(manifest_path.resolve()),
        "manifest_sha256": sha256_file(manifest_path),
        "server_match": server_match,
        "verdict": overall,
        "global_blockers": global_blockers,
        "symbols": results,
        "authorization": {
            "hypothesis_or_prereg": overall == "GO_FOR_PREREG_DESIGN",
            "ea_edit_compile_backtest": False,
            "live_trading": False,
        },
    }


def mt5_probe(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 Python package is unavailable") from exc
    init_args: dict[str, Any] = {}
    if args.terminal_path:
        init_args["path"] = args.terminal_path
    if not mt5.initialize(**init_args):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        observed_server = str(account.server or "")
        server_fingerprint = sha256_text(observed_server)
        account_fingerprint = sha256_text(
            f"{observed_server}|{account.login}|{account.currency}"
        )
        symbols: list[dict[str, Any]] = []
        for symbol in args.symbols:
            info = mt5.symbol_info(symbol)
            current_tick = mt5.symbol_info_tick(symbol)
            node: dict[str, Any] = {
                "symbol": symbol,
                "exists": info is not None,
                "visible": bool(info.visible) if info is not None else None,
                "digits": int(info.digits) if info is not None else None,
                "point": float(info.point) if info is not None else None,
                "last_tick_utc": None,
                "history_sample": None,
            }
            if current_tick is not None and int(current_tick.time) > 0:
                end = datetime.fromtimestamp(int(current_tick.time), tz=timezone.utc)
                start = end - timedelta(hours=args.sample_hours)
                ticks = mt5.copy_ticks_range(symbol, start, end + timedelta(seconds=1), mt5.COPY_TICKS_ALL)
                sample_count = 0 if ticks is None else len(ticks)
                spreads: list[float] = []
                monotonic = True
                previous: int | None = None
                if ticks is not None:
                    for tick in ticks:
                        time_msc = int(tick["time_msc"])
                        monotonic = monotonic and (previous is None or time_msc >= previous)
                        previous = time_msc
                        bid = float(tick["bid"])
                        ask = float(tick["ask"])
                        if bid > 0 and ask >= bid:
                            spreads.append(ask - bid)
                node["last_tick_utc"] = iso_utc(end)
                node["history_sample"] = {
                    "from_utc": iso_utc(start),
                    "to_utc": iso_utc(end),
                    "row_count": sample_count,
                    "valid_bid_ask_count": len(spreads),
                    "valid_bid_ask_ratio": len(spreads) / sample_count if sample_count else 0.0,
                    "timestamp_monotonic": monotonic,
                    "spread_price_p50": percentile(spreads, 0.50),
                    "spread_price_p90": percentile(spreads, 0.90),
                    "completeness_status": "UNPROVEN_HISTORY_SAMPLE",
                }
            symbols.append(node)
        return {
            "schema_version": PROBE_SCHEMA,
            "created_at_utc": iso_utc(utc_now()),
            "producer": {
                "path": str(Path(__file__).resolve()),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "mode": "READ_ONLY_NO_ORDER_OPERATIONS",
            "expected_server": args.expected_server,
            "observed_server": observed_server,
            "server_match": observed_server == args.expected_server,
            "server_fingerprint": server_fingerprint,
            "account_fingerprint": account_fingerprint,
            "account_currency": str(account.currency or ""),
            "terminal": {
                "build": int(terminal.build),
                "connected": bool(terminal.connected),
                "trade_allowed": bool(terminal.trade_allowed),
            },
            "symbols": symbols,
            "safety": {
                "read_only": true_value(),
                "orders_sent": 0,
                "positions_opened": 0,
                "live_trading_authorized": false_value(),
            },
            "verdict": (
                "TARGET_SERVER_READONLY_PROBE_COMPLETE"
                if observed_server == args.expected_server
                else "BROKER_SERVER_MISMATCH"
            ),
        }
    finally:
        mt5.shutdown()


def true_value() -> bool:
    return True


def false_value() -> bool:
    return False


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    evidence_root = Path(args.evidence_root).resolve()
    probe_path = Path(args.probe).resolve()
    prior_audit_path = Path(args.prior_audit).resolve()
    probe = load_json(probe_path)
    if probe.get("schema_version") != PROBE_SCHEMA:
        raise ValueError("probe has the wrong schema")
    manifests = sorted(evidence_root.rglob("*.manifest.json")) if evidence_root.exists() else []
    validations: list[dict[str, Any]] = []
    invalid_manifests: list[dict[str, str]] = []
    for manifest in manifests:
        try:
            validations.append(validate_bundle(manifest))
        except Exception as exc:  # fail-closed inventory must retain invalid evidence
            invalid_manifests.append(
                {"path": str(manifest), "error": f"{type(exc).__name__}: {exc}"}
            )
    eligible = [item for item in validations if item.get("verdict") == "GO_FOR_PREREG_DESIGN"]
    proxy_summaries = list((ALPHA_ROOT / "runs").rglob("slippage_summary.json"))
    raw_named_files = []
    if evidence_root.exists():
        for path in evidence_root.rglob("*"):
            if path.is_file() and any(
                token in path.name.lower()
                for token in ("quote", "tick", "commission", "slippage", "fill")
            ):
                raw_named_files.append(path)
    return {
        "schema_version": INVENTORY_SCHEMA,
        "created_at_utc": iso_utc(utc_now()),
        "producer": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "manifest_schema": {
            "path": str(SCHEMA_PATH.resolve()),
            "sha256": sha256_file(SCHEMA_PATH),
        },
        "expected_server": args.expected_server,
        "probe": {
            "path": str(probe_path),
            "sha256": sha256_file(probe_path),
            "observed_server": probe.get("observed_server"),
            "server_match": probe.get("observed_server") == args.expected_server,
            "verdict": probe.get("verdict"),
        },
        "prior_cost_audit": {
            "path": str(prior_audit_path),
            "sha256": sha256_file(prior_audit_path),
        },
        "evidence_root": str(evidence_root),
        "capture_manifest_count": len(manifests),
        "validated_bundle_count": len(validations),
        "eligible_bundle_count": len(eligible),
        "invalid_manifests": invalid_manifests,
        "raw_named_evidence_file_count": len(raw_named_files),
        "tester_proxy_slippage_summary_count": len(proxy_summaries),
        "tester_proxy_is_broker_evidence": false_value(),
        "qfsi": {
            "verdict": "GO_FOR_PREREG_DESIGN" if eligible else "STOP_DATA_FRONTIER",
            "blockers": sorted(
                set(
                    (["BROKER_SERVER_MISMATCH"] if probe.get("observed_server") != args.expected_server else [])
                    + (["NO_ELIGIBLE_HASH_BOUND_EXECUTION_BUNDLE"] if not eligible else [])
                )
            ),
        },
        "gvbci": {
            "verdict": "COST_QUOTE_AND_LICENSE_REVIEW_ONLY",
            "data_present_locally": false_value(),
        },
        "scfis": {
            "verdict": "EXCLUDED",
            "reason": "No lawful segmented customer-flow data is present.",
        },
        "authorization": {
            "hypothesis_or_prereg": false_value(),
            "ea_edit_compile_backtest": false_value(),
            "live_trading": false_value(),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe-mt5", help="read-only MT5 environment and quote-history probe")
    probe.add_argument("--expected-server", required=True)
    probe.add_argument("--symbols", nargs="+", required=True)
    probe.add_argument("--sample-hours", type=int, default=1)
    probe.add_argument("--terminal-path")
    probe.add_argument("--out", required=True)

    validate = subparsers.add_parser("validate", help="validate one hash-bound execution-data bundle")
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--out", required=True)

    inventory = subparsers.add_parser("inventory", help="inventory existing eligible execution evidence")
    inventory.add_argument("--expected-server", required=True)
    inventory.add_argument("--probe", required=True)
    inventory.add_argument("--evidence-root", required=True)
    inventory.add_argument("--prior-audit", required=True)
    inventory.add_argument("--out", required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "probe-mt5":
            payload = mt5_probe(args)
        elif args.command == "validate":
            payload = validate_bundle(Path(args.manifest).resolve())
        else:
            payload = build_inventory(args)
        write_json_atomic(Path(args.out).resolve(), payload)
        print(json.dumps({"status": "OK", "verdict": payload.get("verdict") or payload.get("qfsi", {}).get("verdict"), "out": str(Path(args.out).resolve())}))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
