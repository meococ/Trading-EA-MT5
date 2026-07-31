from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys


RESEARCH = Path(__file__).resolve().parents[1] / "research"
sys.path.insert(0, str(RESEARCH))

from path_confirmation_reference import PendingTrend, confirm_pending


def pending(direction: int) -> PendingTrend:
    return PendingTrend(
        direction=direction,
        decision_server=datetime(2026, 1, 5, 10, 0),
        setup_high=1.1010,
        setup_low=1.0990,
        frozen_stop=1.0980 if direction > 0 else 1.1020,
    )


def test_long_requires_exact_next_bar_and_breaks_setup_high() -> None:
    item = pending(1)
    decision = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=5),
        regime_trend=True,
        close=1.1011,
        session_vwap=1.1000,
        anchored_vwap=1.1002,
        m15_close=1.1008,
        m15_vwap=1.1004,
    )
    assert decision.confirmed
    assert decision.stop == item.frozen_stop


def test_non_adjacent_bar_expires_without_resurrection() -> None:
    item = pending(1)
    result = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=10),
        regime_trend=True,
        close=1.1020,
        session_vwap=1.1000,
        anchored_vwap=1.1000,
        m15_close=1.1010,
        m15_vwap=1.1000,
    )
    assert not result.confirmed
    assert result.reason == "EXPIRED"


def test_long_rejects_without_extreme_break() -> None:
    item = pending(1)
    result = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=5),
        regime_trend=True,
        close=item.setup_high,
        session_vwap=1.1000,
        anchored_vwap=1.1000,
        m15_close=1.1010,
        m15_vwap=1.1000,
    )
    assert not result.confirmed
    assert result.reason == "EXTREME_BREAK_REJECT"


def test_long_rejects_mean_stack_or_m15_failure() -> None:
    item = pending(1)
    mean_fail = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=5),
        regime_trend=True,
        close=1.1011,
        session_vwap=1.1012,
        anchored_vwap=1.1000,
        m15_close=1.1010,
        m15_vwap=1.1000,
    )
    assert mean_fail.reason == "MEAN_STACK_REJECT"
    m15_fail = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=5),
        regime_trend=True,
        close=1.1011,
        session_vwap=1.1000,
        anchored_vwap=1.1000,
        m15_close=1.1000,
        m15_vwap=1.1000,
    )
    assert m15_fail.reason == "M15_REJECT"


def test_short_is_exact_mirror() -> None:
    item = pending(-1)
    passed = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=5),
        regime_trend=True,
        close=1.0989,
        session_vwap=1.1000,
        anchored_vwap=1.0998,
        m15_close=1.0990,
        m15_vwap=1.0995,
    )
    assert passed.confirmed and passed.stop == item.frozen_stop
    failed = confirm_pending(
        item,
        current_server=item.decision_server + timedelta(minutes=5),
        regime_trend=False,
        close=1.0989,
        session_vwap=1.1000,
        anchored_vwap=1.0998,
        m15_close=1.0990,
        m15_vwap=1.0995,
    )
    assert failed.reason == "REGIME_REJECT"
