from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .models import (
    AccountSnapshot,
    CalendarEvent,
    Direction,
    MarketSnapshot,
    PositionSnapshot,
    QuoteSnapshot,
    RiskState,
    StructuralEvent,
    TradeMode,
)


class CollectorError(RuntimeError):
    """Raised when a read-only MT5 snapshot cannot be collected safely."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def account_fingerprint(login: int, server: str, terminal_path: str) -> str:
    identity = f"{int(login)}\n{server.strip()}\n{str(Path(terminal_path).resolve()).casefold()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def terminal_path_sha256(terminal_path: str) -> str:
    return hashlib.sha256(str(Path(terminal_path).resolve()).casefold().encode("utf-8")).hexdigest()


def _namedtuple_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    raise CollectorError(f"unexpected MT5 value type: {type(value).__name__}")


def _trade_mode(value: int, mt5: Any) -> TradeMode:
    if value == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0):
        return TradeMode.DEMO
    if value == getattr(mt5, "ACCOUNT_TRADE_MODE_CONTEST", 1):
        return TradeMode.CONTEST
    if value == getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", 2):
        return TradeMode.REAL
    return TradeMode.UNKNOWN


def _risk_pct_for_position(position: Mapping[str, Any], quote: QuoteSnapshot, equity: float) -> float:
    stop_loss = float(position.get("sl") or 0.0)
    volume = float(position.get("volume") or 0.0)
    open_price = float(position.get("price_open") or 0.0)
    if stop_loss <= 0.0 or volume <= 0.0 or open_price <= 0.0 or equity <= 0.0:
        return 100.0
    risk_cash = abs(open_price - stop_loss) / quote.tick_size * quote.tick_value_loss * volume
    return min(100.0, max(0.0, risk_cash / equity * 100.0))


def _quote_time_mapping(
    raw_tick_epoch: int,
    captured_at_utc: datetime,
    explicit_offset_minutes: int | None,
    tick_time_basis: str | None,
) -> tuple[int | None, bool, str, int]:
    if (explicit_offset_minutes is None) != (tick_time_basis is None):
        raise CollectorError(
            "verified time mapping requires both server offset and tick_time_basis"
        )
    if explicit_offset_minutes is not None and tick_time_basis is not None:
        if not -14 * 60 <= explicit_offset_minutes <= 14 * 60:
            raise CollectorError("server UTC offset is outside the supported range")
        basis = tick_time_basis.upper()
        if basis == "UTC":
            return explicit_offset_minutes, True, "EXPLICIT_UTC_TICK_EPOCH", raw_tick_epoch
        if basis == "SERVER":
            return (
                explicit_offset_minutes,
                True,
                "EXPLICIT_SERVER_TICK_EPOCH",
                raw_tick_epoch - explicit_offset_minutes * 60,
            )
        raise CollectorError("tick_time_basis must be UTC or SERVER")
    if raw_tick_epoch <= 0:
        return None, False, "UNAVAILABLE", raw_tick_epoch
    difference_minutes = (raw_tick_epoch - captured_at_utc.timestamp()) / 60.0
    inferred = int(round(difference_minutes / 15.0) * 15)
    residual_seconds = abs(difference_minutes - inferred) * 60.0
    if -14 * 60 <= inferred <= 14 * 60 and residual_seconds <= 120:
        return (
            inferred,
            False,
            "INFERRED_SERVER_TICK_EPOCH_UNVERIFIED",
            raw_tick_epoch - inferred * 60,
        )
    return None, False, "UNAVAILABLE", raw_tick_epoch


def _risk_state_sha256(state: RiskState) -> str:
    content = json.dumps(
        state.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    return hashlib.sha256(content).hexdigest()


def collect_mt5_read_only(
    symbols: Iterable[str],
    *,
    terminal_path: str | None = None,
    risk_state: RiskState | Mapping[str, Any] | None = None,
    session_plan_id: str | None = None,
    verified_ledger_head_sha256: str | None = None,
    risk_state_ttl_seconds: int = 120,
    calendar: Iterable[CalendarEvent] = (),
    calendar_available: bool = False,
    calendar_asof_utc: datetime | None = None,
    server_utc_offset_minutes: int | None = None,
    tick_time_basis: str | None = None,
    structural_events: Iterable[StructuralEvent] = (),
    mt5_module: Any | None = None,
    captured_at_utc: datetime | None = None,
) -> tuple[MarketSnapshot, AccountSnapshot]:
    """Collect one read-only market/account snapshot.

    This function intentionally has no order/check/send surface.  Daily/weekly
    risk counters cannot be reconstructed from one terminal snapshot.  A typed
    RiskState is accepted only when its account, SessionPlan, verified ledger
    head and freshness all match; otherwise the snapshot remains incomplete and
    the risk gateway fails closed.
    """

    requested_symbols = tuple(dict.fromkeys(symbol.strip() for symbol in symbols if symbol.strip()))
    if not requested_symbols:
        raise CollectorError("at least one symbol is required")
    captured = captured_at_utc or utc_now()
    if captured.tzinfo is None or captured.utcoffset() != timezone.utc.utcoffset(captured):
        raise CollectorError("captured_at_utc must be UTC")

    if mt5_module is None:
        try:
            import MetaTrader5 as mt5_module  # type: ignore[no-redef]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise CollectorError("MetaTrader5 package is unavailable") from exc

    init_args: dict[str, Any] = {}
    if terminal_path:
        init_args["path"] = terminal_path
    if not mt5_module.initialize(**init_args):
        raise CollectorError(f"MT5 initialize failed: {mt5_module.last_error()}")

    try:
        terminal = _namedtuple_dict(mt5_module.terminal_info())
        account = _namedtuple_dict(mt5_module.account_info())
        if not terminal or not account:
            raise CollectorError(f"terminal/account info unavailable: {mt5_module.last_error()}")

        resolved_terminal = str(terminal.get("path") or terminal_path or "")
        if not resolved_terminal:
            raise CollectorError("terminal path unavailable")

        raw_ticks: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        first_tick_epoch = 0
        for symbol in requested_symbols:
            info = _namedtuple_dict(mt5_module.symbol_info(symbol))
            tick = _namedtuple_dict(mt5_module.symbol_info_tick(symbol))
            if not info or not tick:
                continue
            tick_epoch = int(tick.get("time") or 0)
            if tick_epoch > 0 and first_tick_epoch == 0:
                first_tick_epoch = tick_epoch
            raw_ticks[symbol] = (info, tick)
        (
            offset_minutes,
            time_mapping_verified,
            time_mapping_source,
            _first_tick_utc,
        ) = _quote_time_mapping(
            first_tick_epoch,
            captured,
            server_utc_offset_minutes,
            tick_time_basis,
        )

        quotes: list[QuoteSnapshot] = []
        quote_by_symbol: dict[str, QuoteSnapshot] = {}
        for symbol, (info, tick) in raw_ticks.items():
            point = float(info.get("point") or 0.0)
            bid = float(tick.get("bid") or 0.0)
            ask = float(tick.get("ask") or 0.0)
            tick_epoch = int(tick.get("time") or 0)
            if point <= 0.0 or bid <= 0.0 or ask <= 0.0 or tick_epoch <= 0:
                continue
            _, _, _, tick_utc_epoch = _quote_time_mapping(
                tick_epoch,
                captured,
                server_utc_offset_minutes,
                tick_time_basis,
            )
            quote = QuoteSnapshot(
                symbol=symbol,
                bid=bid,
                ask=ask,
                point=point,
                spread_points=(ask - bid) / point,
                tick_size=float(info.get("trade_tick_size") or point),
                tick_value_loss=float(
                    info.get("trade_tick_value_loss")
                    or info.get("trade_tick_value")
                    or 0.0
                ),
                volume_min=float(info.get("volume_min") or 0.0),
                volume_max=float(info.get("volume_max") or 0.0),
                volume_step=float(info.get("volume_step") or 0.0),
                stops_level_points=float(info.get("trade_stops_level") or 0.0),
                asof_utc=datetime.fromtimestamp(tick_utc_epoch, tz=timezone.utc),
                server_time=f"raw_epoch={tick_epoch}",
            )
            quotes.append(quote)
            quote_by_symbol[symbol] = quote

        positions_raw = mt5_module.positions_get()
        if positions_raw is None:
            raise CollectorError(f"positions_get failed: {mt5_module.last_error()}")
        equity = float(account.get("equity") or 0.0)
        positions: list[PositionSnapshot] = []
        for raw in positions_raw:
            position = _namedtuple_dict(raw)
            symbol = str(position.get("symbol") or "")
            quote = quote_by_symbol.get(symbol)
            if quote is None:
                raise CollectorError(f"open position symbol {symbol!r} lacks a valid quote snapshot")
            direction = Direction.LONG if int(position.get("type") or 0) == getattr(mt5_module, "POSITION_TYPE_BUY", 0) else Direction.SHORT
            positions.append(
                PositionSnapshot(
                    ticket=int(position.get("ticket") or 0),
                    symbol=symbol,
                    direction=direction,
                    volume=float(position.get("volume") or 0.0),
                    open_price=float(position.get("price_open") or 0.0),
                    current_price=float(position.get("price_current") or 0.0),
                    stop_loss=float(position.get("sl") or 0.0),
                    take_profit=float(position.get("tp") or 0.0),
                    risk_pct=_risk_pct_for_position(position, quote, equity),
                    magic=int(position.get("magic") or 0),
                    comment=str(position.get("comment") or ""),
                )
            )

        fingerprint = account_fingerprint(
            int(account.get("login") or 0),
            str(account.get("server") or ""),
            resolved_terminal,
        )
        parsed_risk: RiskState | None = None
        risk_rejection = "UNAVAILABLE"
        if risk_state is not None:
            try:
                parsed_risk = (
                    risk_state
                    if isinstance(risk_state, RiskState)
                    else RiskState.model_validate(risk_state)
                )
            except Exception as exc:
                raise CollectorError("risk_state is not a valid immutable RiskState") from exc
            age_seconds = (captured - parsed_risk.asof_utc).total_seconds()
            if parsed_risk.account_fingerprint.lower() != fingerprint.lower():
                risk_rejection = "ACCOUNT_FINGERPRINT_MISMATCH"
            elif not session_plan_id or parsed_risk.session_plan_id != session_plan_id:
                risk_rejection = "SESSION_PLAN_MISMATCH"
            elif (
                not verified_ledger_head_sha256
                or parsed_risk.ledger_head_sha256.lower()
                != verified_ledger_head_sha256.lower()
            ):
                risk_rejection = "LEDGER_HEAD_MISMATCH"
            elif age_seconds < 0 or age_seconds > risk_state_ttl_seconds:
                risk_rejection = "STALE_RISK_STATE"
            else:
                risk_rejection = "BOUND_RISK_STATE"
        risk_complete = risk_rejection == "BOUND_RISK_STATE"
        balance = float(account.get("balance") or 0.0)
        drawdown_pct = 0.0 if balance <= 0.0 else max(0.0, (balance - equity) / balance * 100.0)
        account_snapshot = AccountSnapshot(
            snapshot_id=f"ACCOUNT-{captured.strftime('%Y%m%dT%H%M%S.%fZ')}",
            captured_at_utc=captured,
            account_fingerprint=fingerprint,
            server=str(account.get("server") or "UNKNOWN"),
            trade_mode=_trade_mode(int(account.get("trade_mode", -1)), mt5_module),
            currency=str(account.get("currency") or "UNK"),
            balance=balance,
            equity=equity,
            margin_free=float(account.get("margin_free") or 0.0),
            drawdown_pct=min(100.0, drawdown_pct),
            daily_loss_pct=parsed_risk.daily_loss_pct if risk_complete and parsed_risk else 0.0,
            weekly_loss_pct=parsed_risk.weekly_loss_pct if risk_complete and parsed_risk else 0.0,
            open_risk_pct=min(100.0, sum(position.risk_pct for position in positions)),
            risk_metrics_complete=risk_complete,
            risk_metrics_source=risk_rejection,
            risk_state_sha256=_risk_state_sha256(parsed_risk) if risk_complete and parsed_risk else None,
            risk_state_asof_utc=parsed_risk.asof_utc if risk_complete and parsed_risk else None,
            risk_state_session_plan_id=(
                parsed_risk.session_plan_id if risk_complete and parsed_risk else None
            ),
            risk_state_ledger_head_sha256=(
                parsed_risk.ledger_head_sha256 if risk_complete and parsed_risk else None
            ),
            trades_this_session=(
                parsed_risk.trades_this_session if risk_complete and parsed_risk else 0
            ),
            consecutive_losses=(
                parsed_risk.consecutive_losses if risk_complete and parsed_risk else 0
            ),
            terminal_connected=bool(terminal.get("connected")),
            terminal_trade_allowed=bool(terminal.get("trade_allowed")),
            expert_trading_allowed=bool(account.get("trade_expert")),
            positions=tuple(positions),
        )
        market_snapshot = MarketSnapshot(
            snapshot_id=f"MARKET-{captured.strftime('%Y%m%dT%H%M%S.%fZ')}",
            captured_at_utc=captured,
            source="MetaTrader5 Python read-only collector",
            terminal_path_sha256=terminal_path_sha256(resolved_terminal),
            connected=bool(terminal.get("connected")),
            server_utc_offset_minutes=offset_minutes,
            time_mapping_verified=time_mapping_verified,
            time_mapping_source=time_mapping_source,
            calendar_available=calendar_available,
            calendar_asof_utc=calendar_asof_utc,
            quotes=tuple(quotes),
            structural_events=tuple(structural_events),
            calendar=tuple(calendar),
        )
        return market_snapshot, account_snapshot
    finally:
        mt5_module.shutdown()
