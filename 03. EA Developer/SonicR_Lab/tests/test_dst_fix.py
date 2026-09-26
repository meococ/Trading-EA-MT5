"""T0 (2F): UK DST edge fix - hand-computed London hours.

Bug: _last_sunday returned the 1st-of-next-month when that day was a
Sunday, placing the UK transition one week late in years where
Apr 1 / Nov 1 is a Sunday: Mar 2012, Mar 2018, Oct 2015, Oct 2020.
Server clock follows US DST (UTC+3 EDT / +2 EST); London = UTC+0/+1.
"""
import datetime as dt

import numpy as np

from src import data as dm
from src.components import sessions


def _ctm(y, m, d, hh, mm=0):
    return int(dt.datetime(y, m, d, hh, mm,
                           tzinfo=dt.timezone.utc).timestamp())


def _lon_hour(y, m, d, hh, mm=0):
    return int(dm.london_parts(np.array([_ctm(y, m, d, hh, mm)]))[0][0])


def test_t0_uk_last_sunday_2012_03():
    # Apr 1 2012 = Sunday -> bug week Mar 26-30 (UK already BST).
    # server 18:30 (US EDT -> utc 15:30) -> London BST 16:30.
    assert _lon_hour(2012, 3, 29, 18, 30) == 16
    assert _lon_hour(2012, 3, 25, 4, 0) == 1   # switch day 01:00 UTC


def test_t0_uk_last_sunday_2018_03():
    # Apr 1 2018 = Sunday -> bug week Mar 26-30.
    assert _lon_hour(2018, 3, 27, 18, 30) == 16


def test_t0_uk_last_sunday_2015_10():
    # Nov 1 2015 = Sunday -> bug week Oct 26-30 (UK already GMT).
    # server 08:15 (US EDT -> utc 05:15) -> London GMT 05:15.
    # buggy code had label 06:15 (in london_ext); true London is outside.
    assert _lon_hour(2015, 10, 26, 8, 15) == 5
    assert _lon_hour(2015, 10, 27, 8, 30) == 5
    # spec case: true London 06:15-06:45 = server 09:15-09:45 this week
    assert _lon_hour(2015, 10, 26, 9, 15) == 6
    assert _lon_hour(2015, 10, 27, 9, 45) == 6
    assert _lon_hour(2015, 10, 25, 5, 0) == 2   # utc 02:00, past 01:00 off


def test_t0_uk_last_sunday_2020_10():
    # Nov 1 2020 = Sunday -> bug week Oct 26-30 (inside VALIDATION).
    assert _lon_hour(2020, 10, 28, 12, 0) == 9  # server-3h gap


def test_t0_us_uk_gap_directions():
    # March gap week (US EDT on, UK GMT): london = server - 3h.
    assert _lon_hour(2015, 3, 11, 12, 0) == 9
    # Oct/Nov gap week (UK GMT off, US EDT on): london = server - 3h.
    assert _lon_hour(2015, 10, 28, 12, 0) == 9
    # Normal summer (both on): london = server - 2h.
    assert _lon_hour(2015, 7, 15, 12, 0) == 10
    # Winter (both off): london = server - 2h.
    assert _lon_hour(2015, 12, 15, 12, 0) == 10


def test_t0_friday_flatten_bug_week():
    # Friday 2015-10-30 20:00 London GMT -> utc 20:00 -> server 23:00
    # (US still EDT until Nov 1 06:00 UTC).
    mon = _ctm(2015, 10, 26, 9, 0)
    flat = int(sessions.friday_flatten_ctm(np.array([mon]))[0])
    assert flat == _ctm(2015, 10, 30, 23, 0)
