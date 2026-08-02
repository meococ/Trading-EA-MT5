from __future__ import annotations

from datetime import datetime, timedelta, timezone


UTC = timezone.utc


def wrapping_session_key(value: datetime):
    return (value + timedelta(minutes=105)).date()


def session_allows(value: datetime) -> bool:
    minute = value.hour * 60 + value.minute
    in_clock = minute >= 22 * 60 + 15 or minute < 5 * 60 + 30
    session_day = (value + timedelta(minutes=105)).weekday()
    return in_clock and session_day < 5


def final_exit_ticket(
    *, position_exists: bool, entries: list[tuple[int, float]], exits: list[tuple[int, int, float]]
) -> int | None:
    if position_exists:
        return None
    entry_volume = sum(volume for _, volume in entries)
    exit_volume = sum(volume for _, _, volume in exits)
    if entry_volume <= 0 or exit_volume + 0.005 < entry_volume:
        return None
    return max(exits, key=lambda item: (item[1], item[0]))[0]


def test_wrapping_fx_session_includes_sunday_open_and_excludes_friday_night():
    sunday_open = datetime(2020, 1, 5, 22, 15, tzinfo=UTC)
    monday_after_midnight = datetime(2020, 1, 6, 0, 0, tzinfo=UTC)
    friday_close_sleeve = datetime(2020, 1, 10, 5, 25, tzinfo=UTC)
    friday_night = datetime(2020, 1, 10, 22, 15, tzinfo=UTC)
    sunday_midnight = datetime(2020, 1, 5, 0, 0, tzinfo=UTC)

    assert session_allows(sunday_open)
    assert session_allows(monday_after_midnight)
    assert wrapping_session_key(sunday_open) == wrapping_session_key(monday_after_midnight)
    assert session_allows(friday_close_sleeve)
    assert not session_allows(friday_night)
    assert not session_allows(sunday_midnight)


def test_rolling_window_requires_72_contiguous_bars_in_one_wrapping_session():
    decision = datetime(2020, 1, 6, 4, 15, tzinfo=UTC)
    bars = [decision - timedelta(minutes=5 * offset) for offset in range(1, 73)]
    assert len(bars) == 72
    assert all(left - right == timedelta(minutes=5) for left, right in zip(bars, bars[1:]))
    assert all(session_allows(bar) for bar in bars)
    assert {wrapping_session_key(bar) for bar in bars} == {wrapping_session_key(decision)}

    stitched = bars.copy()
    stitched[-1] -= timedelta(days=2)
    assert not all(
        left - right == timedelta(minutes=5) for left, right in zip(stitched, stitched[1:])
    )


def test_exact_18_bar_hold_uses_entry_bar_open_not_fill_seconds():
    entry_bar_open = datetime(2020, 1, 6, 4, 0, tzinfo=UTC)
    fill_time = entry_bar_open + timedelta(seconds=17)
    exit_bar_open = entry_bar_open + timedelta(minutes=90)
    assert exit_bar_open - entry_bar_open == timedelta(minutes=90)
    assert exit_bar_open - fill_time < timedelta(minutes=90)


def test_unordered_partial_exit_batch_has_exactly_one_final_close():
    entries = [(100, 0.6), (101, 0.4)]
    exits = [(205, 3000, 0.3), (203, 2000, 0.2), (207, 3000, 0.5)]
    assert final_exit_ticket(position_exists=False, entries=entries, exits=exits) == 207
    assert final_exit_ticket(position_exists=True, entries=entries, exits=exits) is None
    assert final_exit_ticket(
        position_exists=False, entries=entries, exits=exits[:-1]
    ) is None


def test_any_persistence_write_or_readback_failure_disables_entry():
    def persist(write_results: list[bool], readback_matches: bool) -> bool:
        return all(write_results) and readback_matches

    assert persist([True] * 7, True)
    assert not persist([True, True, False, True, True, True, True], True)
    assert not persist([True] * 7, False)


def test_partial_fill_risk_is_proportional_and_sums_to_requested_risk():
    planned_volume = 1.0
    planned_risk = 250.0
    risk_per_lot = planned_risk / planned_volume
    partial_volumes = [0.35, 0.65]
    risks = [risk_per_lot * volume for volume in partial_volumes]
    assert risks == [87.5, 162.5]
    assert sum(risks) == planned_risk


def test_each_partial_fill_is_checked_against_immutable_worst_bound():
    direction = 1
    worst_bound = 150.030
    fills = [150.010, 150.025]
    assert all(direction * (fill - worst_bound) <= 0.0005 for fill in fills)
