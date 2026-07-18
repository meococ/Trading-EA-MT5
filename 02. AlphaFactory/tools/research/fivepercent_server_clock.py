"""FivePercentOnline-Real server-time -> UTC clock model (canonical).

Server = UTC+2 winter / UTC+3 summer with the DST calendar switching BY ERA:
EU last-Sunday calendar through 2023, US second-Sunday calendar from 2024.
Established and verified on every trading week 2015-2026 via Friday-17:00
New-York close anchors (evidence:
`03. EA Developer/EA_HybridRegimeMR/research/evidence/EURUSD_PULL_AUDIT.json`);
the `year >= 2024` branch below is that measured convention change, not a bug.
DST transitions fall on closed-market weekends, so no live bar is ambiguous.
Revalidate on new pulls with the weekly close-anchor method.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _nth_sunday(year: int, month: int, n: int) -> datetime:
    d = datetime(year, month, 1, tzinfo=timezone.utc)
    first_sunday = d + timedelta(days=(6 - d.weekday()) % 7)
    return first_sunday + timedelta(days=7 * (n - 1))


def _last_sunday(year: int, month: int) -> datetime:
    if month == 12:
        nxt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        nxt = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    last_day = nxt - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


def is_us_dst(utc: datetime) -> bool:
    """US: 2nd Sunday March 07:00 UTC -> 1st Sunday November 06:00 UTC."""
    start = _nth_sunday(utc.year, 3, 2).replace(hour=7)
    end = _nth_sunday(utc.year, 11, 1).replace(hour=6)
    return start <= utc < end


def is_eu_dst(utc: datetime) -> bool:
    """EU: last Sunday March 01:00 UTC -> last Sunday October 01:00 UTC."""
    start = _last_sunday(utc.year, 3).replace(hour=1)
    end = _last_sunday(utc.year, 10).replace(hour=1)
    return start <= utc < end


def server_offset_hours(ts_server_naive: datetime) -> int:
    """UTC offset (+2/+3) for a naive FivePercent server timestamp."""
    guess = ts_server_naive.replace(tzinfo=timezone.utc) - timedelta(hours=2)
    if guess.year >= 2024:
        return 3 if is_us_dst(guess) else 2
    return 3 if is_eu_dst(guess) else 2


def server_to_utc(ts_server_naive: datetime) -> datetime:
    return ts_server_naive - timedelta(hours=server_offset_hours(ts_server_naive))


if __name__ == "__main__":
    # gap-week checks: mid-March 2015 (US DST on, EU off) must be +2 (EU era);
    # mid-March 2024 must be +3 (US era); July always +3; January always +2.
    assert server_offset_hours(datetime(2015, 3, 18, 12, 0)) == 2
    assert server_offset_hours(datetime(2024, 3, 20, 12, 0)) == 3
    assert server_offset_hours(datetime(2020, 7, 15, 12, 0)) == 3
    assert server_offset_hours(datetime(2022, 1, 15, 12, 0)) == 2
    print("SELF-TEST PASS  era-hybrid DST model (EU<=2023, US>=2024)")
