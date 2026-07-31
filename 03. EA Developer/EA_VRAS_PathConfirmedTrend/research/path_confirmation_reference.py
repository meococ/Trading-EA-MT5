"""Outcome-blind reference for the frozen HYP-004 one-bar confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math


@dataclass(frozen=True)
class PendingTrend:
    direction: int
    decision_server: datetime
    setup_high: float
    setup_low: float
    frozen_stop: float


@dataclass(frozen=True)
class ConfirmationDecision:
    confirmed: bool
    reason: str
    stop: float


def confirm_pending(
    pending: PendingTrend,
    *,
    current_server: datetime,
    regime_trend: bool,
    close: float,
    session_vwap: float,
    anchored_vwap: float,
    m15_close: float,
    m15_vwap: float,
) -> ConfirmationDecision:
    values = (close, session_vwap, anchored_vwap, m15_close, m15_vwap, pending.frozen_stop)
    if pending.direction not in (-1, 1) or not all(math.isfinite(value) for value in values):
        return ConfirmationDecision(False, "DATA_INVALID", pending.frozen_stop)
    if current_server != pending.decision_server + timedelta(minutes=5):
        return ConfirmationDecision(False, "EXPIRED", pending.frozen_stop)
    if not regime_trend:
        return ConfirmationDecision(False, "REGIME_REJECT", pending.frozen_stop)
    if pending.direction > 0:
        if close <= pending.setup_high:
            return ConfirmationDecision(False, "EXTREME_BREAK_REJECT", pending.frozen_stop)
        if close <= session_vwap or close <= anchored_vwap:
            return ConfirmationDecision(False, "MEAN_STACK_REJECT", pending.frozen_stop)
        if m15_close <= m15_vwap:
            return ConfirmationDecision(False, "M15_REJECT", pending.frozen_stop)
    else:
        if close >= pending.setup_low:
            return ConfirmationDecision(False, "EXTREME_BREAK_REJECT", pending.frozen_stop)
        if close >= session_vwap or close >= anchored_vwap:
            return ConfirmationDecision(False, "MEAN_STACK_REJECT", pending.frozen_stop)
        if m15_close >= m15_vwap:
            return ConfirmationDecision(False, "M15_REJECT", pending.frozen_stop)
    return ConfirmationDecision(True, "PATH_CONFIRM_ACCEPTED", pending.frozen_stop)
