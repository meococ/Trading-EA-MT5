#!/usr/bin/env python3
"""Explicit no-live QFSI capture starter for FivePercentOnline-Real.

Safety:
- Read-only MT5 surface only (terminal/account/symbol/ticks/history).
- Never places, modifies, or closes orders/positions.
- Fail-closed if observed server != expected server.
- Must be started and stopped explicitly (no cron).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import execution_data_foundation as foundation  # noqa: E402

EXPECTED_DEFAULT = "FivePercentOnline-Real"
SYMBOLS_DEFAULT = ("EURUSD", "GBPUSD", "XAUUSD", "USDJPY")
CLOCK_GRID_MS = 15 * 60 * 1000
CLOCK_RESIDUAL_LIMIT_MS = 30 * 1000
CLOCK_ABSOLUTE_LIMIT_MS = 14 * 60 * 60 * 1000


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def infer_tick_clock_offset_ms(raw_tick_msc: int, receipt_utc_msc: int) -> int:
    """Infer broker-server epoch offset on a 15-minute timezone grid."""
    delta = int(raw_tick_msc) - int(receipt_utc_msc)
    offset = int(round(delta / CLOCK_GRID_MS)) * CLOCK_GRID_MS
    if abs(offset) > CLOCK_ABSOLUTE_LIMIT_MS:
        raise RuntimeError(f"tick clock offset outside +/-14h: {offset} ms")
    residual = abs(delta - offset)
    if residual > CLOCK_RESIDUAL_LIMIT_MS:
        raise RuntimeError(
            f"tick clock residual exceeds 30s: delta={delta} offset={offset} residual={residual}"
        )
    return offset


def normalize_tick_utc_msc(raw_tick_msc: int, offset_ms: int) -> int:
    normalized = int(raw_tick_msc) - int(offset_ms)
    if normalized <= 0:
        raise RuntimeError("normalized tick timestamp is non-positive")
    return normalized


def fresh_normalized_tick_msc(
    raw_tick_msc: int, offset_ms: int, last_seen_utc_msc: int
) -> int | None:
    """Return a normalized timestamp only when it advances the UTC cursor."""
    normalized = normalize_tick_utc_msc(raw_tick_msc, offset_ms)
    return normalized if normalized > int(last_seen_utc_msc) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_csv(path: Path, fields: list[str], row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new_file:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def artifact_ref(path: Path | None, status: str, method: str) -> dict[str, Any]:
    if path is None or not path.exists() or status in {"MISSING", "NOT_APPLICABLE"}:
        return {"status": status, "completeness_method": method}
    return {
        "status": status,
        "completeness_method": method,
        "path": str(path.as_posix()),
        "sha256": sha256_file(path),
        "row_count": count_csv_rows(path),
    }


def export_commission_lifecycles(
    mt5: Any,
    session_root: Path,
    symbols: list[str],
    lookback_days: int,
) -> dict[str, Path]:
    """Write one commission CSV per symbol. Returns paths only for symbols with rows."""
    end = utc_now()
    start = end - timedelta(days=lookback_days)
    deals = mt5.history_deals_get(start, end)
    by_symbol_rows: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    if deals:
        by_pos: dict[int, list[Any]] = {}
        for deal in deals:
            symbol = str(getattr(deal, "symbol", "") or "")
            if symbol not in symbols:
                continue
            pos_id = int(getattr(deal, "position_id", 0) or 0)
            if pos_id <= 0:
                continue
            by_pos.setdefault(pos_id, []).append(deal)

        account = mt5.account_info()
        currency = str(account.currency if account else "USD")
        for pos_id, group in sorted(by_pos.items()):
            group = sorted(group, key=lambda d: int(getattr(d, "time_msc", 0) or 0))
            if len(group) < 2:
                continue
            symbol = str(group[0].symbol)
            volumes = [float(getattr(d, "volume", 0) or 0) for d in group]
            lot = max(volumes) if volumes else 0.0
            if lot <= 0:
                continue
            commission_sum = sum(float(getattr(d, "commission", 0) or 0) for d in group)
            open_t = datetime.fromtimestamp(int(group[0].time), tz=timezone.utc)
            close_t = datetime.fromtimestamp(int(group[-1].time), tz=timezone.utc)
            by_symbol_rows.setdefault(symbol, []).append(
                {
                    "position_id": str(pos_id),
                    "symbol": symbol,
                    "account_currency": currency,
                    "round_turn_account_per_lot": abs(commission_sum) / lot,
                    "conversion_method": "per_trade_contemporaneous",
                    "open_time_utc": iso_utc(open_t),
                    "close_time_utc": iso_utc(close_t),
                    "source": "mt5_account_history_deals",
                }
            )

    paths: dict[str, Path] = {}
    session_root.mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        path = session_root / f"{symbol}_commission_lifecycles.csv"
        rows = by_symbol_rows.get(symbol, [])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(foundation.COMMISSION_FIELDS))
            writer.writeheader()
            writer.writerows(rows)
        if rows:
            paths[symbol] = path
    return paths


def run_capture(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 Python package is unavailable") from exc

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    stop_path = Path(args.stop_file).resolve() if args.stop_file else None
    session_root = Path(args.out_dir).resolve()
    session_root.mkdir(parents=True, exist_ok=True)
    capture_id = args.capture_id
    symbols = list(args.symbols)

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        observed = str(account.server or "")
        if observed != args.expected_server:
            payload = {
                "schema_version": "alphafactory_qfsi_capture_session.v1",
                "created_at_utc": iso_utc(utc_now()),
                "capture_id": capture_id,
                "status": "BLOCKED_STILL_WRONG_SERVER",
                "expected_server": args.expected_server,
                "observed_server": observed,
                "orders_sent": 0,
                "positions_opened": 0,
            }
            write_json(session_root / "session_start.json", payload)
            return payload

        for symbol in symbols:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"cannot select symbol for clock probe: {symbol}")
        clock_receipt = utc_now()
        clock_tick = mt5.symbol_info_tick(symbols[0])
        if clock_tick is None:
            raise RuntimeError(f"clock probe tick unavailable: {symbols[0]}")
        tick_clock_offset_ms = infer_tick_clock_offset_ms(
            int(clock_tick.time_msc), int(clock_receipt.timestamp() * 1000)
        )

        server_fp = foundation.sha256_text(observed)
        account_fp = foundation.sha256_text(f"{observed}|{account.login}|{account.currency}")
        start_payload = {
            "schema_version": "alphafactory_qfsi_capture_session.v1",
            "created_at_utc": iso_utc(utc_now()),
            "capture_id": capture_id,
            "status": "CAPTURE_STARTED",
            "mode": "PASSIVE_READ_ONLY_NO_LIVE_ORDERS",
            "expected_server": args.expected_server,
            "observed_server": observed,
            "server_fingerprint": server_fp,
            "account_fingerprint": account_fp,
            "account_currency": str(account.currency or ""),
            "terminal_build": int(terminal.build),
            "observed_tick_clock_offset_seconds": tick_clock_offset_ms // 1000,
            "symbols": symbols,
            "duration_sec": int(args.duration_sec),
            "poll_ms": int(args.poll_ms),
            "stop_file": str(stop_path) if stop_path else None,
            "safety": {
                "read_only": True,
                "orders_sent": 0,
                "positions_opened": 0,
                "live_trading_authorized": False,
            },
        }
        write_json(session_root / "session_start.json", start_payload)

        # Quote-only research lanes can explicitly prohibit account-history reads.
        commission_paths = (
            {}
            if args.skip_account_history
            else export_commission_lifecycles(
                mt5, session_root, symbols, lookback_days=int(args.history_days)
            )
        )
        commission_counts = {
            symbol: count_csv_rows(path) for symbol, path in commission_paths.items()
        }
        for symbol in symbols:
            commission_counts.setdefault(symbol, 0)

        # Empty slippage placeholder — cannot invent independent pre-send refs.
        for symbol in symbols:
            slippage_path = session_root / f"{symbol}_slippage_fills.csv"
            with slippage_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=sorted(foundation.SLIPPAGE_FIELDS))
                writer.writeheader()

        symbol_meta: dict[str, dict[str, Any]] = {}
        last_seen_msc: dict[str, int] = {s: 0 for s in symbols}
        for symbol in symbols:
            info = mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"symbol missing on Real Market Watch: {symbol}")
            if not info.visible:
                mt5.symbol_select(symbol, True)
            symbol_meta[symbol] = {
                "digits": int(info.digits),
                "point": float(info.point),
                "pip_size": float(info.point) * (10 if int(info.digits) in (3, 5) else 1),
            }
            quote_path = session_root / f"{symbol}_quote_ticks.csv"
            hb_path = session_root / f"{symbol}_heartbeats.csv"
            if not quote_path.exists():
                with quote_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=sorted(foundation.TICK_FIELDS))
                    writer.writeheader()
            if not hb_path.exists():
                with hb_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=sorted(foundation.HEARTBEAT_FIELDS))
                    writer.writeheader()

        deadline = time.time() + max(1, int(args.duration_sec))
        poll_s = max(0.2, int(args.poll_ms) / 1000.0)
        heartbeat_rows = 0
        quote_rows = 0
        ipc_retries = 0
        # Tolerate brief IPC contention from other read-only probes on same terminal.
        max_ipc_retries = max(5, int(getattr(args, "max_ipc_retries", 120)))
        tick_errors = 0
        try:
            while time.time() < deadline:
                if stop_path is not None and stop_path.exists():
                    break
                terminal = mt5.terminal_info()
                account = mt5.account_info()
                if terminal is None or account is None:
                    ipc_retries += 1
                    if ipc_retries > max_ipc_retries:
                        raise RuntimeError(
                            f"MT5 metadata lost after {max_ipc_retries} retries: {mt5.last_error()}"
                        )
                    mt5.shutdown()
                    time.sleep(1.0)
                    if not mt5.initialize():
                        time.sleep(1.0)
                        continue
                    continue
                ipc_retries = 0
                observed_now = str(account.server or "")
                if observed_now != args.expected_server:
                    raise RuntimeError(
                        f"server drifted during capture: expected={args.expected_server} observed={observed_now}"
                    )
                now = utc_now()
                now_msc = int(now.timestamp() * 1000)
                connected = 1 if bool(terminal.connected) else 0
                for symbol in symbols:
                    append_csv(
                        session_root / f"{symbol}_heartbeats.csv",
                        sorted(foundation.HEARTBEAT_FIELDS),
                        {
                            "time_msc": now_msc,
                            "time_utc": iso_utc(now),
                            "connected": connected,
                            "server_fingerprint": server_fp,
                            "terminal_build": int(terminal.build),
                        },
                    )
                    heartbeat_rows += 1
                    # Prefer symbol_info_tick + short-range copy; tolerate empty/IPC-soft failures.
                    try:
                        tick_now = mt5.symbol_info_tick(symbol)
                        if tick_now is not None:
                            t_msc = fresh_normalized_tick_msc(
                                int(tick_now.time_msc),
                                tick_clock_offset_ms,
                                last_seen_msc[symbol],
                            )
                        else:
                            t_msc = None
                        if t_msc is not None:
                            last_seen_msc[symbol] = t_msc
                            append_csv(
                                session_root / f"{symbol}_quote_ticks.csv",
                                sorted(foundation.TICK_FIELDS),
                                {
                                    "time_msc": t_msc,
                                    "time_utc": iso_utc(
                                        datetime.fromtimestamp(t_msc / 1000, tz=timezone.utc)
                                    ),
                                    "symbol": symbol,
                                    "bid": float(tick_now.bid),
                                    "ask": float(tick_now.ask),
                                    "last": float(tick_now.last),
                                    "volume_real": float(getattr(tick_now, "volume_real", 0) or 0),
                                    "flags": int(getattr(tick_now, "flags", 0) or 0),
                                },
                            )
                            quote_rows += 1
                        end = now
                        start = now - timedelta(seconds=3)
                        ticks = mt5.copy_ticks_range(
                            symbol, start, end + timedelta(milliseconds=1), mt5.COPY_TICKS_ALL
                        )
                    except Exception as tick_exc:  # noqa: BLE001 — keep session alive
                        tick_errors += 1
                        if tick_errors <= 3 or tick_errors % 50 == 0:
                            write_json(
                                session_root / "tick_soft_error.json",
                                {
                                    "created_at_utc": iso_utc(utc_now()),
                                    "symbol": symbol,
                                    "tick_errors": tick_errors,
                                    "error": f"{type(tick_exc).__name__}: {tick_exc}",
                                },
                            )
                        continue
                    if ticks is None:
                        continue
                    for tick in ticks:
                        t_msc = fresh_normalized_tick_msc(
                            int(tick["time_msc"]),
                            tick_clock_offset_ms,
                            last_seen_msc[symbol],
                        )
                        if t_msc is None:
                            continue
                        last_seen_msc[symbol] = t_msc
                        append_csv(
                            session_root / f"{symbol}_quote_ticks.csv",
                            sorted(foundation.TICK_FIELDS),
                            {
                                "time_msc": t_msc,
                                "time_utc": iso_utc(
                                    datetime.fromtimestamp(t_msc / 1000, tz=timezone.utc)
                                ),
                                "symbol": symbol,
                                "bid": float(tick["bid"]),
                                "ask": float(tick["ask"]),
                                "last": float(tick["last"]),
                                "volume_real": float(tick["volume_real"]),
                                "flags": int(tick["flags"]),
                            },
                        )
                        quote_rows += 1
                # Progress marker so watchers can detect stalled writers.
                if heartbeat_rows % 60 == 0:
                    write_json(
                        session_root / "capture_progress.json",
                        {
                            "created_at_utc": iso_utc(utc_now()),
                            "heartbeat_rows": heartbeat_rows,
                            "quote_rows": quote_rows,
                            "tick_errors": tick_errors,
                            "ipc_retries_peak_window": ipc_retries,
                            "deadline_utc": iso_utc(
                                datetime.fromtimestamp(deadline, tz=timezone.utc)
                            ),
                        },
                    )
                time.sleep(poll_s)
        except Exception as loop_exc:
            # Fail closed with an auditable crash receipt (006 died with no session_end).
            write_json(
                session_root / "session_crash.json",
                {
                    "schema_version": "alphafactory_qfsi_capture_session.v1",
                    "created_at_utc": iso_utc(utc_now()),
                    "capture_id": capture_id,
                    "status": "CAPTURE_CRASHED",
                    "error": f"{type(loop_exc).__name__}: {loop_exc}",
                    "heartbeat_rows_written": heartbeat_rows,
                    "quote_rows_written": quote_rows,
                    "tick_errors": tick_errors,
                    "ipc_retries_at_crash": ipc_retries,
                    "expected_server": args.expected_server,
                    "safety": {
                        "read_only": True,
                        "orders_sent": 0,
                        "positions_opened": 0,
                        "live_trading_authorized": False,
                    },
                },
            )
            raise

        # Build partial capture manifest (hash-bound). Slippage stays MISSING.
        symbol_nodes = []
        for symbol in symbols:
            quote_path = session_root / f"{symbol}_quote_ticks.csv"
            hb_path = session_root / f"{symbol}_heartbeats.csv"
            c_path = commission_paths.get(symbol)
            c_status = "PARTIAL" if c_path is not None else "MISSING"
            symbol_nodes.append(
                {
                    "symbol": symbol,
                    "digits": symbol_meta[symbol]["digits"],
                    "point": symbol_meta[symbol]["point"],
                    "pip_size": symbol_meta[symbol]["pip_size"],
                    "quote_ticks": artifact_ref(quote_path, "PARTIAL", "PASSIVE_HEARTBEAT"),
                    "heartbeats": artifact_ref(hb_path, "PARTIAL", "PASSIVE_HEARTBEAT"),
                    "commission_lifecycles": artifact_ref(
                        c_path,
                        c_status,
                        "ACCOUNT_HISTORY" if c_status == "PARTIAL" else "NONE",
                    ),
                    "slippage_fills": {
                        "status": "MISSING",
                        "completeness_method": "NONE",
                    },
                }
            )

        # Relative paths inside evidence root for schema friendliness
        # Keep absolute sha/row in a sidecar; schema wants path strings.
        # Rewrite paths relative to session_root for portability.
        for node in symbol_nodes:
            for key in ("quote_ticks", "heartbeats", "commission_lifecycles"):
                art = node[key]
                if art.get("path"):
                    p = Path(art["path"])
                    try:
                        art["path"] = str(p.relative_to(session_root).as_posix())
                    except ValueError:
                        art["path"] = p.name

        manifest = {
            "schema_version": "alphafactory_execution_data_capture.v1",
            "created_at_utc": iso_utc(utc_now()),
            "capture_id": capture_id,
            "purpose": "QFSI_DATA_FEASIBILITY_ONLY",
            "capture_mode": "PASSIVE_READ_ONLY",
            "broker_identity": {
                "expected_server": args.expected_server,
                "observed_server": observed,
                "server_fingerprint": server_fp,
                "account_fingerprint": account_fp,
                "account_currency": str(account.currency or ""),
                "terminal_build": int(terminal.build),
                "observed_tick_clock_offset_seconds": tick_clock_offset_ms // 1000,
            },
            "research_gates": {
                "minimum_quote_elapsed_days": 90,
                "minimum_quote_rows_per_elapsed_day": 1000,
                "minimum_connected_heartbeat_ratio": 0.95,
                "maximum_heartbeat_gap_ms": 60000,
                "minimum_commission_lifecycles_per_symbol": 30,
                "minimum_slippage_fills_per_symbol": 100,
                "minimum_slippage_buys_per_symbol": 30,
                "minimum_slippage_sells_per_symbol": 30,
                "maximum_reference_age_ms": 1000,
            },
            "symbols": symbol_nodes,
            "safety": {
                "read_only": True,
                "orders_sent": 0,
                "positions_opened": 0,
                "live_trading_authorized": False,
            },
        }
        manifest_path = session_root / f"{capture_id}.manifest.json"
        write_json(manifest_path, manifest)

        end_payload = {
            "schema_version": "alphafactory_qfsi_capture_session.v1",
            "created_at_utc": iso_utc(utc_now()),
            "capture_id": capture_id,
            "status": "CAPTURE_WINDOW_COMPLETE_PARTIAL",
            "expected_server": args.expected_server,
            "observed_server": observed,
            "server_match": True,
            "observed_tick_clock_offset_seconds": tick_clock_offset_ms // 1000,
            "heartbeat_rows_written": heartbeat_rows,
            "quote_rows_written": quote_rows,
            "commission_lifecycle_counts": commission_counts,
            "slippage_fills": 0,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "reprice_ready": False,
            "reprice_blockers": [
                "QFSI_SAMPLE_GATES_NOT_MET",
                "SLIPPAGE_FILLS_MISSING",
                "COMMISSION_SAMPLE_BELOW_30_PER_SYMBOL",
                "QUOTE_ELAPSED_DAYS_BELOW_90",
            ],
            "safety": {
                "read_only": True,
                "orders_sent": 0,
                "positions_opened": 0,
                "live_trading_authorized": False,
            },
        }
        write_json(session_root / "session_end.json", end_payload)
        return end_payload
    finally:
        mt5.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-server", default=EXPECTED_DEFAULT)
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS_DEFAULT))
    parser.add_argument("--capture-id", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--duration-sec", type=int, default=120)
    parser.add_argument("--poll-ms", type=int, default=1000)
    parser.add_argument("--history-days", type=int, default=365)
    parser.add_argument(
        "--skip-account-history",
        action="store_true",
        help="Do not call history_deals_get; emit quote/heartbeat artifacts only.",
    )
    parser.add_argument("--stop-file", default="")
    parser.add_argument(
        "--max-ipc-retries",
        type=int,
        default=120,
        help="Consecutive MT5 metadata misses before hard fail (default 120 ≈ 2 min).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = run_capture(args)
        print(json.dumps({"status": "OK", "payload_status": payload.get("status"), "out": args.out_dir}))
        return 0 if payload.get("status") != "BLOCKED_STILL_WRONG_SERVER" else 3
    except Exception as exc:
        # Best-effort crash receipt if run_capture raised before writing session_crash.
        try:
            session_root = Path(args.out_dir).resolve()
            crash_path = session_root / "session_crash.json"
            if session_root.exists() and not crash_path.exists():
                write_json(
                    crash_path,
                    {
                        "schema_version": "alphafactory_qfsi_capture_session.v1",
                        "created_at_utc": iso_utc(utc_now()),
                        "capture_id": args.capture_id,
                        "status": "CAPTURE_CRASHED",
                        "error": f"{type(exc).__name__}: {exc}",
                        "expected_server": args.expected_server,
                        "safety": {
                            "read_only": True,
                            "orders_sent": 0,
                            "positions_opened": 0,
                            "live_trading_authorized": False,
                        },
                    },
                )
        except Exception:
            pass
        print(json.dumps({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
