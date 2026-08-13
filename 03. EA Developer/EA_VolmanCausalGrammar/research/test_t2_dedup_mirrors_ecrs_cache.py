from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import nan

import pytest

import t2_dedup_mirrors as frozen
import t2_dedup_mirrors_ecrs_cache as cached


def _bars(
    count: int,
    *,
    start: datetime = datetime(2020, 1, 6, 6, 0, tzinfo=timezone.utc),
    gap_after: int | None = None,
    nan_volume_at: int | None = None,
    nan_high_at: int | None = None,
    spread_at: tuple[int, float] | None = None,
) -> list[frozen.EcrsBar]:
    rows: list[frozen.EcrsBar] = []
    current = start
    close = 1.1000
    for index in range(count):
        if gap_after is not None and index == gap_after + 1:
            current += timedelta(minutes=10)
        drift = (0.00003 if index % 7 < 4 else -0.00002) + (index % 5) * 0.000001
        next_close = close + drift
        high = max(close, next_close) + 0.00004
        low = min(close, next_close) - 0.00004
        if nan_high_at == index:
            high = nan
        volume = float(80 + (index * 17) % 61)
        if nan_volume_at == index:
            volume = nan
        spread = 5.0
        if spread_at is not None and spread_at[0] == index:
            spread = spread_at[1]
        rows.append(frozen.EcrsBar(current, close, high, low, next_close, volume, spread))
        close = next_close
        current += timedelta(minutes=5)
    return rows


def _assert_trace_and_event_parity(
    rows: list[frozen.EcrsBar],
    *,
    news_times: tuple[datetime, ...] = (),
) -> None:
    calendar = frozen.synthetic_news_calendar(news_times)
    old_state = frozen._ecrs_state(rows)
    new_state = cached.build_cached_ecrs_state(rows)
    for index in range(len(rows)):
        old = frozen._ecrs_v1_gate_trace_from_state(
            old_state,
            index,
            symbol="EURUSD",
            timeframe="M5",
            news_calendar=calendar,
            allow_formula_generalization=False,
        )
        new = cached.ecrs_v1_gate_trace_cached_from_state(
            new_state,
            index,
            symbol="EURUSD",
            timeframe="M5",
            news_calendar=calendar,
            allow_formula_generalization=False,
        )
        assert new == old, f"trace mismatch at index {index}"
    old_events = frozen.emit_ecrs_v1_identities(
        rows,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    new_events = cached.emit_ecrs_v1_identities_cached(
        rows,
        symbol="EURUSD",
        news_calendar=calendar,
        allow_synthetic_calendar=True,
    )
    assert new_events == old_events
    assert [row["event_key"] for row in new_events] == [row["event_key"] for row in old_events]


@pytest.mark.parametrize("count", [0, 1, 2, 19, 20, 21, 60])
def test_cached_trace_and_events_match_frozen_at_short_and_indicator_boundaries(count: int) -> None:
    _assert_trace_and_event_parity(_bars(count))


def test_cached_trace_and_events_match_frozen_with_nan_indicator_inputs() -> None:
    _assert_trace_and_event_parity(_bars(60, nan_volume_at=22, nan_high_at=25))


def test_cached_trace_and_events_match_frozen_news_session_spread_and_gap_cases() -> None:
    rows = _bars(
        80,
        gap_after=31,
        spread_at=(45, 9.0),
    )
    news_time = rows[50].time_utc
    _assert_trace_and_event_parity(rows, news_times=(news_time,))


def test_cached_trace_matches_frozen_exact_requested_indices() -> None:
    rows = _bars(40)
    calendar = frozen.synthetic_news_calendar([])
    old_state = frozen._ecrs_state(rows)
    new_state = cached.build_cached_ecrs_state(rows)
    for index in (0, 19, len(rows) - 1):
        assert cached.ecrs_v1_gate_trace_cached_from_state(
            new_state,
            index,
            symbol="EURUSD",
            timeframe="M5",
            news_calendar=calendar,
            allow_formula_generalization=False,
        ) == frozen._ecrs_v1_gate_trace_from_state(
            old_state,
            index,
            symbol="EURUSD",
            timeframe="M5",
            news_calendar=calendar,
            allow_formula_generalization=False,
        )


def test_cached_successor_builds_each_rolling_array_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []
    original = frozen._rolling_mean

    def counted(values, period):
        calls.append((len(values), period))
        return original(values, period)

    monkeypatch.setattr(frozen, "_rolling_mean", counted)
    cached.emit_ecrs_v1_identities_cached(
        _bars(60),
        symbol="EURUSD",
        news_calendar=frozen.synthetic_news_calendar([]),
        allow_synthetic_calendar=True,
    )
    assert calls == [(60, 14), (60, 20), (60, 20)]


def test_cached_successor_does_not_mutate_frozen_state_values() -> None:
    rows = _bars(35)
    frozen_state = frozen._ecrs_state(rows)
    cached_state = cached.build_cached_ecrs_state(rows)
    for key in ("bars", "closes", "highs", "lows", "volumes", "atr14", "ema20", "er"):
        assert cached_state[key] == frozen_state[key]
    assert set(cached_state) == set(frozen_state) | {"atr_sma20", "tv_sma20"}
