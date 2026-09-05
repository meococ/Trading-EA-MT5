"""Observation-plane session snapshot for Grok SessionStart.

Attach-only: mt5.initialize() with no path= and no login kwargs.
path= launches a terminal (2026-08-31 empty-process incident). If the Owner
GUI is not already running, this script records connected=false and exits.

Not an AlphaFactory research attach. Do not "fix" this by adding path=.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any


def _emit(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=True, separators=(",", ":"))
    sys.stdout.write("\n")


def main() -> int:
    now = datetime.now(timezone.utc)
    base: dict[str, Any] = {
        "ok": False,
        "captured_at_utc": now.isoformat(),
        "plane": "observation",
        "authority": False,
        "note": "Cache only. Not GOAL.md. Read MCP get_trading_account_info for mcp_trade_allowed.",
    }
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError:
        base["error"] = "MetaTrader5 package missing"
        _emit(base)
        return 0

    # Attach to an already-running terminal. Do not pass path=.
    if not mt5.initialize():
        base["error"] = "attach failed; Owner GUI terminal is not running"
        base["last_error"] = list(mt5.last_error())
        _emit(base)
        return 0

    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        acc = account._asdict() if account is not None else {}
        term = terminal._asdict() if terminal is not None else {}
        terminal_path = str(term.get("path") or "")
        isolate = "runtime" in terminal_path.replace("/", "\\").lower() and "mt5-portable" in terminal_path.lower()

        last_deal_epoch = None
        deals = mt5.history_deals_get(now - timedelta(days=40), now) or ()
        for deal in deals:
            stamp = int(getattr(deal, "time", 0) or 0)
            if last_deal_epoch is None or stamp > last_deal_epoch:
                last_deal_epoch = stamp

        days_since = None
        if last_deal_epoch:
            last_dt = datetime.fromtimestamp(last_deal_epoch, tz=timezone.utc)
            days_since = (now - last_dt).days

        warning = None
        if last_deal_epoch is None:
            warning = "No deals in the last 40 days. The5ers 30-calendar-day inactivity rule can close the account. Do not open a keepalive trade via MCP."
        elif days_since is not None and days_since >= 20:
            warning = (
                f"{days_since} days since last deal (30-day inactivity close). "
                "Do not send mt5__trade_*. Tell the Owner."
            )
        if isolate:
            warning = (
                (warning + " ") if warning else ""
            ) + "Attached terminal looks like the factory isolate, not the Owner GUI."

        payload = {
            "ok": True,
            "captured_at_utc": now.isoformat(),
            "plane": "observation",
            "authority": False,
            "login": acc.get("login"),
            "server": acc.get("server"),
            "company": acc.get("company"),
            "trade_mode": acc.get("trade_mode"),
            "balance": acc.get("balance"),
            "equity": acc.get("equity"),
            "margin": acc.get("margin"),
            "profit": acc.get("profit"),
            "currency": acc.get("currency"),
            "terminal_path": terminal_path,
            "terminal_build": term.get("build"),
            "server_connected": bool(term.get("connected")),
            "experts_trade_allowed": bool(term.get("trade_allowed")),
            "mcp_trade_allowed": "unknown_use_mcp",
            "last_deal_epoch": last_deal_epoch,
            "days_since_last_deal": days_since,
            "warning": warning,
            "note": "Cache only. mcp_trade_allowed is MCP-only; call get_trading_account_info.",
        }
        _emit(payload)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
