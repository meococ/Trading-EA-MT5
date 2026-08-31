#!/usr/bin/env python3
"""Import Owner MT5 Account History / live history into QFSI commission evidence.

Modes:
  --from-live-mt5     Read-only history_deals_get from connected Real terminal
  --from-drop DIR     Parse Owner-dropped CSV/HTML in the drop folder

Never invents slippage fills. Never places orders. Fail-closed on wrong server.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import execution_data_foundation as foundation  # noqa: E402

EXPECTED_SERVER = "FivePercentOnline-Real"
TARGET_SYMBOLS = ("EURUSD", "GBPUSD", "XAUUSD", "USDJPY")
SCHEMA = "alphafactory_deal_history_import.v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def empty_slippage(session_root: Path, symbols: list[str]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for symbol in symbols:
        path = session_root / f"{symbol}_slippage_fills.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(foundation.SLIPPAGE_FIELDS))
            writer.writeheader()
        paths[symbol] = path
    return paths


def write_commission_csvs(
    session_root: Path, by_symbol_rows: dict[str, list[dict[str, Any]]], symbols: list[str]
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for symbol in symbols:
        path = session_root / f"{symbol}_commission_lifecycles.csv"
        rows = by_symbol_rows.get(symbol, [])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(foundation.COMMISSION_FIELDS))
            writer.writeheader()
            writer.writerows(rows)
        paths[symbol] = path
    return paths


def lifecycles_from_mt5_deals(deals: Any, currency: str) -> dict[str, list[dict[str, Any]]]:
    by_pos: dict[int, list[Any]] = defaultdict(list)
    for deal in deals or []:
        symbol = str(getattr(deal, "symbol", "") or "")
        pos_id = int(getattr(deal, "position_id", 0) or 0)
        if pos_id <= 0 or not symbol:
            continue
        by_pos[pos_id].append(deal)

    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
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
        if abs(commission_sum) <= 0:
            # Keep zero-commission closed lifecycles only if we want completeness;
            # QFSI validate_commission requires positive round_turn — skip zeros.
            continue
        open_t = datetime.fromtimestamp(int(group[0].time), tz=timezone.utc)
        close_t = datetime.fromtimestamp(int(group[-1].time), tz=timezone.utc)
        out[symbol].append(
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
    return out


def from_live_mt5(out_dir: Path, history_days: int) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package unavailable") from exc
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            raise RuntimeError(f"MT5 metadata unavailable: {mt5.last_error()}")
        observed = str(account.server or "")
        if observed != EXPECTED_SERVER:
            return {
                "schema_version": SCHEMA,
                "status": "BLOCKED_WRONG_SERVER",
                "expected_server": EXPECTED_SERVER,
                "observed_server": observed,
            }
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=history_days)
        deals = mt5.history_deals_get(start, end)
        raw_path = out_dir / "raw_history_deals.csv"
        fields = [
            "ticket",
            "order",
            "time",
            "time_msc",
            "symbol",
            "type",
            "entry",
            "volume",
            "price",
            "commission",
            "swap",
            "profit",
            "fee",
            "position_id",
            "comment",
        ]
        with raw_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for d in deals or []:
                writer.writerow({k: getattr(d, k, "") for k in fields})

        by_symbol = lifecycles_from_mt5_deals(deals, str(account.currency or "USD"))
        # Always emit target FX symbols (may be empty) + any extra symbols found
        symbols = list(TARGET_SYMBOLS)
        for sym in sorted(by_symbol):
            if sym not in symbols:
                symbols.append(sym)
        commission_paths = write_commission_csvs(out_dir, by_symbol, symbols)
        slippage_paths = empty_slippage(out_dir, list(TARGET_SYMBOLS))
        counts = {s: len(by_symbol.get(s, [])) for s in symbols}
        payload = {
            "schema_version": SCHEMA,
            "status": "IMPORTED_LIVE_HISTORY_PARTIAL",
            "created_at_utc": iso_utc(end),
            "mode": "FROM_LIVE_MT5_READONLY",
            "expected_server": EXPECTED_SERVER,
            "observed_server": observed,
            "server_fingerprint": foundation.sha256_text(observed),
            "account_fingerprint": foundation.sha256_text(
                f"{observed}|{account.login}|{account.currency}"
            ),
            "account_currency": str(account.currency or ""),
            "terminal_build": int(terminal.build),
            "history_lookback_days": history_days,
            "raw_deal_count": 0 if deals is None else len(deals),
            "commission_lifecycle_counts": counts,
            "slippage_fills": 0,
            "slippage_status": "MISSING_NOT_ZERO_CANNOT_MINT",
            "artifacts": {
                "raw_history_deals": {
                    "path": str(raw_path),
                    "sha256": sha256_file(raw_path),
                    "rows": 0 if deals is None else len(deals),
                },
                "commission_lifecycles": {
                    s: {
                        "path": str(commission_paths[s]),
                        "sha256": sha256_file(commission_paths[s]),
                        "rows": counts.get(s, 0),
                    }
                    for s in symbols
                },
                "slippage_fills": {
                    s: {
                        "path": str(slippage_paths[s]),
                        "sha256": sha256_file(slippage_paths[s]),
                        "rows": 0,
                    }
                    for s in TARGET_SYMBOLS
                },
            },
            "gates_remaining": {
                "commission_need_per_symbol": 30,
                "usdJPY_commission": counts.get("USDJPY", 0),
                "eurusd_commission": counts.get("EURUSD", 0),
                "slippage_need_per_symbol": 100,
                "quote_days_need": 90,
            },
            "safety": {"orders_sent": 0, "positions_opened": 0, "read_only": True},
        }
        write_json(out_dir / "import_manifest.json", payload)
        return payload
    finally:
        mt5.shutdown()


def _parse_float(raw: str) -> float:
    s = (raw or "").strip().replace(" ", "").replace(",", "")
    if not s or s == "—":
        return 0.0
    return float(s)


def lifecycles_from_owner_csv(path: Path, currency: str = "USD") -> dict[str, list[dict[str, Any]]]:
    """Best-effort MT5 Deal History CSV (Account History → Deals → export).

    Accepted header aliases (case-insensitive):
      Time / Time (UTC), Symbol, Volume / Lots, Commission, Position / Position ID / Position ticket
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    # Strip HTML wrapper if Owner saved "Webpage, HTML only" that still has a table
    if "<html" in text.lower() or "<table" in text.lower():
        return lifecycles_from_owner_html(path, currency)

    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError(f"CSV has no header: {path}")
    norm = {h: re.sub(r"\s+", " ", h).strip().lower() for h in reader.fieldnames}

    def col(*names: str) -> str | None:
        for n in names:
            for orig, low in norm.items():
                if low == n:
                    return orig
        return None

    c_time = col("time", "time (utc)", "open time", "close time")
    c_sym = col("symbol")
    c_vol = col("volume", "lots", "volume (lots)")
    c_comm = col("commission")
    c_pos = col("position", "position id", "position ticket", "positionid")
    if not all([c_time, c_sym, c_vol, c_comm, c_pos]):
        raise ValueError(
            f"CSV missing required columns (need Time/Symbol/Volume/Commission/Position): {path.name}"
        )

    by_pos: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reader:
        pos = str(row.get(c_pos) or "").strip()
        sym = str(row.get(c_sym) or "").strip()
        if not pos or not sym:
            continue
        by_pos[pos].append(row)

    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pos, rows in by_pos.items():
        if len(rows) < 2:
            continue
        sym = str(rows[0].get(c_sym) or "").strip()
        lot = max(_parse_float(str(r.get(c_vol) or "0")) for r in rows)
        if lot <= 0:
            continue
        commission_sum = sum(_parse_float(str(r.get(c_comm) or "0")) for r in rows)
        if abs(commission_sum) <= 0:
            continue
        times = [str(r.get(c_time) or "").strip() for r in rows]
        times = [t for t in times if t]
        if not times:
            continue
        open_t, close_t = times[0], times[-1]
        # Normalize to Z if bare
        def norm_t(t: str) -> str:
            t = t.replace(".", "-") if re.match(r"^\d{4}\.", t) else t
            if "T" not in t and " " in t:
                t = t.replace(" ", "T", 1)
            if not t.endswith("Z") and "+" not in t:
                t = t + "Z"
            return t

        out[sym].append(
            {
                "position_id": pos,
                "symbol": sym,
                "account_currency": currency,
                "round_turn_account_per_lot": abs(commission_sum) / lot,
                "conversion_method": "per_trade_contemporaneous",
                "open_time_utc": norm_t(open_t),
                "close_time_utc": norm_t(close_t),
                "source": f"owner_deal_export:{path.name}",
            }
        )
    return out


def lifecycles_from_owner_html(path: Path, currency: str = "USD") -> dict[str, list[dict[str, Any]]]:
    """Parse MT5 Account History HTML export Deal table (best-effort)."""
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = raw.decode("utf-8", errors="replace")

    # Reuse AlphaFactory tester HTML parser when section exists
    analysis = TOOLS.parent / "analysis"
    if str(analysis) not in sys.path:
        sys.path.insert(0, str(analysis))
    try:
        from quant_analyzer import parse_deals_from_html_report  # type: ignore

        deals = parse_deals_from_html_report(path)
    except Exception:
        deals = []

    if not deals:
        raise ValueError(f"Could not parse Deal rows from HTML: {path}")

    by_pos: dict[str, list[Any]] = defaultdict(list)
    for d in deals:
        pos = str(getattr(d, "position_id", "") or getattr(d, "position", "") or "").strip()
        sym = str(getattr(d, "symbol", "") or "").strip()
        if not pos or not sym:
            continue
        by_pos[pos].append(d)

    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pos, group in by_pos.items():
        if len(group) < 2:
            continue
        sym = str(getattr(group[0], "symbol", "") or "")
        lot = max(float(getattr(d, "volume", 0) or 0) for d in group)
        if lot <= 0:
            continue
        commission_sum = sum(float(getattr(d, "commission", 0) or 0) for d in group)
        if abs(commission_sum) <= 0:
            continue
        # time fields vary
        def t_of(d: Any) -> str:
            for attr in ("time_utc", "time", "open_time"):
                v = getattr(d, attr, None)
                if v is None:
                    continue
                if isinstance(v, datetime):
                    return iso_utc(v)
                return str(v)

        times = [t_of(d) for d in group]
        times = [t for t in times if t]
        out[sym].append(
            {
                "position_id": pos,
                "symbol": sym,
                "account_currency": currency,
                "round_turn_account_per_lot": abs(commission_sum) / lot,
                "conversion_method": "per_trade_contemporaneous",
                "open_time_utc": times[0] if times else iso_utc(datetime.now(timezone.utc)),
                "close_time_utc": times[-1] if times else iso_utc(datetime.now(timezone.utc)),
                "source": f"owner_deal_export_html:{path.name}",
            }
        )
    return out


def from_drop(drop_dir: Path, out_dir: Path, currency: str) -> dict[str, Any]:
    files = sorted(
        [
            p
            for p in drop_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".csv", ".htm", ".html", ".txt"}
            and not p.name.startswith("_")
            and p.name.lower() != "readme.md"
        ]
    )
    if not files:
        return {
            "schema_version": SCHEMA,
            "status": "NO_OWNER_FILES_IN_DROP",
            "drop_dir": str(drop_dir),
            "hint": "Drop MT5 Account History Deal export (CSV or HTML) into this folder.",
        }

    merged: dict[str, list[dict[str, Any]]] = defaultdict(list)
    sources: list[dict[str, Any]] = []
    for path in files:
        try:
            if path.suffix.lower() in {".htm", ".html"}:
                part = lifecycles_from_owner_html(path, currency)
            else:
                part = lifecycles_from_owner_csv(path, currency)
        except Exception as exc:
            sources.append(
                {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "status": "PARSE_FAIL",
                    "error": str(exc),
                }
            )
            continue
        n = sum(len(v) for v in part.values())
        sources.append(
            {
                "path": str(path),
                "sha256": sha256_file(path),
                "status": "PARSED",
                "lifecycle_rows": n,
                "symbols": {k: len(v) for k, v in part.items()},
            }
        )
        for sym, rows in part.items():
            # de-dupe by position_id
            seen = {r["position_id"] for r in merged[sym]}
            for row in rows:
                if row["position_id"] not in seen:
                    merged[sym].append(row)
                    seen.add(row["position_id"])

    symbols = list(TARGET_SYMBOLS)
    for sym in sorted(merged):
        if sym not in symbols:
            symbols.append(sym)
    commission_paths = write_commission_csvs(out_dir, merged, symbols)
    slippage_paths = empty_slippage(out_dir, list(TARGET_SYMBOLS))
    counts = {s: len(merged.get(s, [])) for s in symbols}
    payload = {
        "schema_version": SCHEMA,
        "status": "IMPORTED_OWNER_DROP",
        "created_at_utc": iso_utc(datetime.now(timezone.utc)),
        "mode": "FROM_OWNER_DROP",
        "expected_server": EXPECTED_SERVER,
        "drop_dir": str(drop_dir),
        "sources": sources,
        "commission_lifecycle_counts": counts,
        "slippage_fills": 0,
        "slippage_status": "MISSING_NOT_ZERO_CANNOT_MINT_FROM_DEAL_EXPORT",
        "artifacts": {
            "commission_lifecycles": {
                s: {
                    "path": str(commission_paths[s]),
                    "sha256": sha256_file(commission_paths[s]),
                    "rows": counts.get(s, 0),
                }
                for s in symbols
            },
            "slippage_fills": {
                s: {
                    "path": str(slippage_paths[s]),
                    "sha256": sha256_file(slippage_paths[s]),
                    "rows": 0,
                }
                for s in TARGET_SYMBOLS
            },
        },
        "gates_remaining": {
            "commission_need_per_symbol": 30,
            "note": "Deal export can raise commission N; slippage still needs side-referenced fills or broker exec report",
        },
        "safety": {"orders_sent": 0, "invented_costs": False},
    }
    write_json(out_dir / "import_manifest.json", payload)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-live-mt5", action="store_true")
    ap.add_argument("--from-drop", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--history-days", type=int, default=3650)
    ap.add_argument("--account-currency", default="USD")
    args = ap.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.from_live_mt5:
        payload = from_live_mt5(out_dir, args.history_days)
    elif args.from_drop:
        payload = from_drop(args.from_drop.resolve(), out_dir, args.account_currency)
    else:
        ap.error("Specify --from-live-mt5 or --from-drop DIR")
        return 2

    print(json.dumps(payload, indent=2))
    return 0 if payload.get("status") not in {"BLOCKED_WRONG_SERVER"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
