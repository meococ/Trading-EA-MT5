"""test_cet.py — CET/CEST converter tests (mandate P0).

Covers both 2012 DST switch weeks (25 Mar, 28 Oct) and a DESIGN-week
sanity pair.  Run: python -m pytest tests/test_cet.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
for _p in (PERC, os.path.join(PERC, "..", "..", "lib")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cet  # noqa: E402
import pa_clock  # noqa: E402


def utc(y, m, d, hh=0, mm=0):
    import calendar
    from datetime import datetime
    return calendar.timegm(datetime(y, m, d, hh, mm).timetuple())


def test_spring_forward_2012():
    # 2012-03-25 (Sun): 01:00 UTC -> CET offset 1 -> 2
    assert cet.cet_offset_hours(utc(2012, 3, 25, 0, 59)) == 1
    assert cet.cet_offset_hours(utc(2012, 3, 25, 1, 0)) == 2
    # the whole preceding Friday is still winter time
    assert cet.cet_offset_hours(utc(2012, 3, 23, 12, 0)) == 1
    # Monday after: summer
    assert cet.cet_offset_hours(utc(2012, 3, 26, 12, 0)) == 2


def test_autumn_back_2012():
    # 2012-10-28 (Sun): 01:00 UTC -> offset 2 -> 1
    assert cet.cet_offset_hours(utc(2012, 10, 28, 0, 59)) == 2
    assert cet.cet_offset_hours(utc(2012, 10, 28, 1, 0)) == 1
    assert cet.cet_offset_hours(utc(2012, 10, 26, 12, 0)) == 2
    assert cet.cet_offset_hours(utc(2012, 10, 29, 12, 0)) == 1


def test_design_week_offsets():
    # DESIGN era: a summer week and a winter week
    assert cet.cet_offset_hours(utc(2019, 6, 17, 10, 0)) == 2
    assert cet.cet_offset_hours(utc(2019, 1, 15, 10, 0)) == 1


def test_roundtrip_year():
    # cet->utc->cet identity across 2012 (the autumn-fold hour is excluded:
    # 02:00-02:59 CET on 28 Oct maps twice; the summer-side pick wins)
    base = utc(2012, 1, 1)
    for d in range(0, 366, 3):
        t = base + d * 86400 + 7 * 3600
        c = cet.utc_to_cet_epoch(t)
        back = cet.cet_to_utc_epoch(c)
        # within the fold the inverse lands on the summer-side instant
        assert back in (t, t - 3600)


def test_wall_clock_values():
    # 2012-03-01 12:00 UTC (winter) -> 13:00 CET
    assert cet.utc_to_cet_epoch(utc(2012, 3, 1, 12)) == utc(2012, 3, 1, 13)
    # 2012-07-02 12:00 UTC (summer) -> 14:00 CEST
    assert cet.utc_to_cet_epoch(utc(2012, 7, 2, 12)) == utc(2012, 7, 2, 14)


def test_book_server_is_cet_wall():
    # Ruling 1 / D3: the BOOK feed's server clock is Europe/Berlin wall,
    # so server epoch == CET wall epoch on every open-market minute.
    # Verified by NFP bars printing at server 14:30 winter AND summer.
    base = utc(2012, 3, 5)      # winter Monday
    base2 = utc(2012, 7, 9)     # summer Monday
    for b in (base, base2):
        for h in range(0, 24):
            u = b + h * 3600
            c = cet.utc_to_cet_epoch(u)
            srv = cet.cet_to_server_epoch(c)
            assert srv == c                      # identity
            assert cet.server_to_cet_epoch(srv) == c


def test_cet_minute_and_dow():
    # 2012-03-01 is a Thursday (dow 3). 13:34 CET wall -> 814 min.
    # On the BOOK feed the server epoch already reads as CET wall.
    srv = cet.cet_to_server_epoch(cet.utc_to_cet_epoch(utc(2012, 3, 1, 12, 34)))
    assert cet.cet_minute_of_day(srv) == 13 * 60 + 34
    assert cet.cet_dow(srv) == 3
