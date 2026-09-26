"""Clock golden vectors: EU DST switches (2019), mod-1440 wrap, round-trip."""

import numpy as np
import pandas as pd

import pa_clock as pc


def _e(s):
    return int(pd.Timestamp(s, tz="UTC").timestamp())


def test_dst_switch_2019_march():
    # 2019-03-31 is the last Sunday of March: summer starts at server 01:00
    assert pc.server_offset_hours(_e("2019-03-30 23:59:00")) == 2
    assert pc.server_offset_hours(_e("2019-03-31 00:59:00")) == 2
    assert pc.server_offset_hours(_e("2019-03-31 01:00:00")) == 3
    assert pc.server_offset_hours(_e("2019-03-31 12:00:00")) == 3


def test_dst_switch_2019_october():
    # 2019-10-27 is the last Sunday of October: winter resumes at server 01:00
    assert pc.server_offset_hours(_e("2019-10-26 23:59:00")) == 3
    assert pc.server_offset_hours(_e("2019-10-27 00:59:00")) == 3
    assert pc.server_offset_hours(_e("2019-10-27 01:00:00")) == 2
    assert pc.server_offset_hours(_e("2019-12-31 12:00:00")) == 2


def test_offset_vectorized_matches_scalars():
    ts = np.array([_e("2019-03-31 00:59:00"), _e("2019-03-31 01:00:00"),
                   _e("2019-10-27 00:59:00"), _e("2019-10-27 01:00:00"),
                   _e("2020-07-01 12:00:00")])
    got = pc.server_offset_hours(ts)
    assert list(got) == [2, 3, 3, 2, 3]
    for v in ts:
        assert pc.server_offset_hours(int(v)) == int(pc.server_offset_hours(np.array([v]))[0])


def test_mod_1440_wrap_crosses_to_previous_utc_day():
    # server 00:30 in summer (+3) -> 21:30 UTC of the PREVIOUS day, not -0:30
    s_summer = _e("2021-06-15 00:30:00")
    assert (s_summer % 86400) // 60 == 30
    assert pc.utc_minute_of_day(s_summer) == 21 * 60 + 30
    # winter (+2): 00:30 server -> 22:30 UTC of the previous day
    s_winter = _e("2021-01-15 00:30:00")
    assert pc.utc_minute_of_day(s_winter) == 22 * 60 + 30
    # every value is inside [0, 1440)
    mins = pc.utc_minute_of_day(np.arange(_e("2019-03-30 00:00:00"),
                                          _e("2019-11-10 00:00:00"), 3600))
    assert mins.min() >= 0 and mins.max() < 1440


def test_round_trip_server_utc():
    stamps = ["2019-01-15 12:34:00", "2019-03-31 00:30:00", "2019-03-31 03:30:00",
              "2019-06-15 12:34:00", "2019-10-27 00:30:00", "2019-10-27 05:00:00",
              "2020-02-29 23:59:00"]
    for s in stamps:
        t = _e(s)
        u = pc.server_to_utc_epoch(t)
        back = pc.utc_epoch_to_server(u)
        assert back == t, s
    # and the UTC shift equals the offset at that server instant
    t = _e("2019-06-15 12:34:00")
    assert pc.server_to_utc_epoch(t) == t - 3 * 3600
    t = _e("2019-01-15 12:34:00")
    assert pc.server_to_utc_epoch(t) == t - 2 * 3600


def test_weekday_is_correct_not_legacy():
    # 2019-04-01 Monday, 2019-04-04 Thursday, 2019-04-07 Sunday
    assert pc.server_dow(_e("2019-04-01 10:00:00")) == 0
    assert pc.server_dow(_e("2019-04-04 10:00:00")) == 3
    assert pc.server_dow(_e("2019-04-07 10:00:00")) == 6
    # the frozen formula was Sunday=0, so "dow == 4" fired on THURSDAY
    assert pc.legacy_server_dow(_e("2019-04-04 10:00:00")) == 4
    assert pc.legacy_server_dow(_e("2019-04-07 10:00:00")) == 0


def test_server_day_start_utc():
    t = _e("2019-06-15 12:34:00")          # summer, +3
    assert pc.server_day_start_utc(t) == _e("2019-06-14 21:00:00")
    t = _e("2019-01-15 12:34:00")          # winter, +2
    assert pc.server_day_start_utc(t) == _e("2019-01-14 22:00:00")
