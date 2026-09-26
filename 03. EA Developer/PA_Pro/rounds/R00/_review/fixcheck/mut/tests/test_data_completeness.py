"""E2 gaps (R00 review): resample completeness + warm-up flag aggregation.

Two data-plane behaviours the referee reasons on:
- an incomplete M5/H1 bucket must be dropped and counted, never silently used;
- a TF bar counts as warm-up if ANY of its M1 members is warm-up (``max``), so
  a bucket that straddles the split boundary can never produce signals.
"""

from datetime import datetime, timezone

import numpy as np

import pa_clock
import pa_data

START_2016 = int(datetime(2016, 1, 1, tzinfo=timezone.utc).timestamp())


def _m1(t, warmup):
    t = np.asarray(t, dtype=np.int64)
    n = len(t)
    c = np.full(n, 1.1000, dtype=np.float64)
    return {"t": t, "o": c.copy(), "h": c.copy(), "l": c.copy(), "c": c.copy(),
            "pip": 1e-4, "symbol": "SYNX", "split": "DESIGN",
            "warmup": np.asarray(warmup, dtype=bool)}


def test_incomplete_tf_buckets_are_dropped_and_counted():
    start = int(pa_clock.utc_epoch_to_server(START_2016))   # server, hour-aligned
    n = 180                                                  # 3 server hours
    t = np.int64(start) + np.arange(n, dtype=np.int64) * 60
    keep = np.ones(n, dtype=bool)
    keep[[3, 61]] = False        # one missing minute in M5 bucket 0 / M5 bucket 12
    m1 = _m1(t[keep], np.zeros(int(keep.sum()), dtype=bool))

    m5 = pa_data.resample(m1, "M5")
    assert m5["n_src"] == 5
    assert m5["dropped"] == 2
    assert len(m5["t"]) == 36 - 2
    starts = set(int(x) for x in m5["t"])
    assert start not in starts                    # bucket 0 dropped
    assert start + 12 * 300 not in starts         # bucket 12 dropped
    assert start + 300 in starts                  # its neighbour survived

    h1 = pa_data.resample(m1, "H1")
    assert h1["n_src"] == 60
    assert h1["dropped"] == 2
    assert [int(x) for x in h1["t"]] == [start + 2 * 3600]   # only hour 2 complete

    m15 = pa_data.resample(m1, "M15")
    assert m15["n_src"] == 15
    assert m15["dropped"] == 2
    assert len(m15["t"]) == 12 - 2


def test_warmup_flag_uses_any_member_and_boundary_is_2016_01_01():
    start_srv = int(pa_clock.utc_epoch_to_server(START_2016))   # server 02:00
    srv0 = start_srv - 2 * 3600                                 # server 00:00
    n = 8 * 60                                                  # 2 warm + 6 live hours
    t = np.int64(srv0) + np.arange(n, dtype=np.int64) * 60
    utc = pa_clock.server_to_utc_epoch(t)
    warm = utc < START_2016
    assert warm[:120].all() and not warm[120:].any()            # exactly pre-boundary
    m1 = _m1(t, warm)

    h4 = pa_data.resample(m1, "H4")
    assert len(h4["t"]) == 2
    # the 00:00-03:59 bucket contains 120 warm-up minutes AND 120 live minutes:
    # `max` aggregation must flag it warm-up (the boundary bar is excluded)
    assert [bool(x) for x in h4["warmup"]] == [True, False]

    m5 = pa_data.resample(m1, "M5")
    start_srv_epoch = start_srv
    expected = [bool(x) for x in (m5["t"] < start_srv_epoch)]
    assert [bool(x) for x in m5["warmup"]] == expected
    assert sum(expected) == 24
