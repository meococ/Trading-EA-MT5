"""test_session_mirror.py - run-now coverage for the MQL5 clock/session port.

The MQL5 functions cannot execute without a terminal, so this test
transliterates them line-for-line (see quoted sources) and asserts every
generated golden vector in tests/clock_vectors.csv (truth = pa_clock /
pa_fill).  A mismatch here means the MQL5 ALGORITHM diverged; a mismatch in
the on-terminal self test means a transcription bug.  Light job - no
pa_slots needed.
"""

import calendar
import csv
import datetime as dt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DAY = 86400


# ---- transliteration of PA_Clock.mqh -------------------------------------

def pa_last_sunday_of_month(year, month):
    # MQL5: TimeToStruct(StringToTime("%04d.%02d.31")); return 31-day_of_week
    # MQL5 day_of_week: Sunday=0..Saturday=6
    wd = (dt.date(year, month, 31).weekday() + 1) % 7   # Mon0 -> Sun0
    return 31 - wd


def pa_server_offset_hours(server_time):
    # MQL5: offset 3 while server wall clock in
    # [last Sun of Mar 01:00, last Sun of Oct 01:00), else 2
    y = dt.datetime.utcfromtimestamp(server_time).year
    mar = calendar.timegm((y, 3, pa_last_sunday_of_month(y, 3), 1, 0, 0))
    oct_ = calendar.timegm((y, 10, pa_last_sunday_of_month(y, 10), 1, 0, 0))
    return 3 if mar <= server_time < oct_ else 2


def pa_utc_minute_of_day(server_epoch):
    off = pa_server_offset_hours(server_epoch)
    srv_min = (server_epoch % DAY) // 60
    return (srv_min - off * 60) % 1440


def pa_server_dow(server_epoch):
    return ((server_epoch // DAY) + 3) % 7


# ---- transliteration of CPaSession (corrected mode) ----------------------

def entry_veto(t):
    srv_h = (t % DAY) // 3600
    dow = pa_server_dow(t)
    if dow >= 5:
        return 2
    if dow == 4 and srv_h >= 20:
        return 1
    return 0


def in_session(um):
    return int((300 <= um < 660) or (690 <= um < 1050))


# ---- run every golden vector through the mirror --------------------------

def main():
    path = os.path.join(HERE, "clock_vectors.csv")
    bad = 0
    n = 0
    with open(path) as f:
        for row in csv.DictReader(f):
            t = int(row["t"])
            n += 1
            got = (
                pa_server_offset_hours(t),
                pa_utc_minute_of_day(t + 300),
                ((t + 300) % DAY) // 60,
                pa_server_dow(t + 300),
                entry_veto(t),
                in_session(pa_utc_minute_of_day(t + 300)),
            )
            want = (int(row["off_h"]), int(row["utc_min"]),
                    int(row["srv_min"]), int(row["dow"]),
                    int(row["veto"]), int(row["in_session"]))
            if got != want:
                print("MISMATCH t=%d got=%s want=%s" % (t, got, want))
                bad += 1
    print("%d vectors, %d mismatches -> %s" % (n, bad, "PASS" if not bad else "FAIL"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
