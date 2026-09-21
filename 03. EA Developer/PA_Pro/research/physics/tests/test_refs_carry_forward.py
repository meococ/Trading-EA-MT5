"""R02-A F3 regression: daily reference levels carry forward for the whole day.

Against the pre-fix code only the first bar of each server day saw pdh/pdl/pdc
(`refs.py:59-67`); `levels_at` on any other bar omitted them.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

import phys_common as pc  # noqa: E402  (adds lib + struct/zones to sys.path)


def _two_day_bars():
    t = np.asarray([0, 300, 86400, 86700, 87000, 172800], dtype=np.int64)
    h = np.asarray([1.1005, 1.1002, 1.1010, 1.1015, 1.1008, 1.1000])
    l = np.asarray([1.0995, 1.0990, 1.0985, 1.0980, 1.0990, 1.0990])
    c = np.asarray([1.1000, 1.0992, 1.1000, 1.1005, 1.0995, 1.0995])
    import pa_clock

    return {"t": t, "h": h, "l": l, "c": c, "pip": 1e-4,
            "dow": pa_clock.server_dow(t + 300),
            "utc_min": pa_clock.utc_minute_of_day(t + 300)}


def test_daily_levels_carry_forward_all_day():
    from refs import RefBook

    b = _two_day_bars()
    rb = RefBook(b, None)
    # day 0: no previous day yet
    assert np.isnan(rb.pdh[0]) and np.isnan(rb.pdl[0]) and np.isnan(rb.pdc[0])
    assert np.isnan(rb.pdh[1])
    # day 1 (bars 2..4): day 0 H/L/C on EVERY bar
    day0_hi, day0_lo, day0_c = 1.1005, 1.0990, 1.0992
    for i in (2, 3, 4):
        assert rb.pdh[i] == day0_hi, i
        assert rb.pdl[i] == day0_lo, i
        assert rb.pdc[i] == day0_c, i
    # day 2 (bar 5): day 1 H/L/C
    assert rb.pdh[5] == 1.1015 and rb.pdl[5] == 1.0980 and rb.pdc[5] == 1.0995
    # levels_at exposes them on every bar of the day, not only the rollover
    for i in (2, 3, 4):
        kinds = {k for k, _ in rb.levels_at(i)}
        assert {"pdh", "pdl", "pdc"} <= kinds, (i, kinds)
    assert {"pdh", "pdl", "pdc"} <= {k for k, _ in rb.levels_at(5)}
