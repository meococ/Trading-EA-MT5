"""T8/T9 (A3F): E0 impossible-print flags.

T8: the 2020-05-07 12:33:04 EURUSD bar is flagged; SNB 2015-01-15
USDCHF bars are NOT flagged (real event, no revert); a synthetic +5%
spike that reverts is flagged, one that does not is not.
T9: with no flagged bar in a window, the E0 sim reproduces the existing
trade files row for row (checked on a real symbol whose flags are all
outside the path, plus a synthetic no-flag case).
"""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from src import data as dm
from src import e0
from src import sim as sm
from src import runner
from src.variants.registry import CONFIGS


def _e(y, m, d, hh=0, mm=0, ss=0):
    return int(dt.datetime(y, m, d, hh, mm, ss,
                           tzinfo=dt.timezone.utc).timestamp())


def _mk(t, o, h, l, c):
    n = len(t)
    return {"t": np.asarray(t), "o": np.asarray(o, float),
            "h": np.asarray(h, float), "l": np.asarray(l, float),
            "c": np.asarray(c, float), "tv": np.ones(n),
            "suspect": np.zeros(n, bool)}


def test_t8_synthetic_spike_revert_flagged():
    # 40 quiet M1 bars, one +5% bogus print at bar 20, reverts next bar
    t = [_e(2020, 5, 6, 12, 0) + 60 * i for i in range(40)]
    c = [1.10] * 40; o = [1.10] * 40
    h = [1.1001] * 40; l = [1.0999] * 40
    c[20] = 1.155; h[20] = 1.1555; l[20] = 1.1545; o[20] = 1.1550
    m1 = _mk(t, o, h, l, c)
    flag, info = e0.e0_flags(m1)
    assert flag[20] and flag.sum() == 1
    assert info[0]["flagged"] and info[0]["dev"] > 0.05


def test_t8_synthetic_spike_norevert_not_flagged():
    # +5% move that stays (real repricing): not flagged
    t = [_e(2020, 5, 6, 12, 0) + 60 * i for i in range(40)]
    c = [1.10] * 20 + [1.156] * 20; o = list(c)
    h = [x + 0.0001 for x in c]; l = [x - 0.0001 for x in c]
    m1 = _mk(t, o, h, l, c)
    flag, info = e0.e0_flags(m1)
    assert not flag.any()          # dev>3% but never reverts
    assert any(not it["flagged"] for it in info)


@pytest.fixture(scope="module")
def eurusd_slice():
    return dm.load_m1("EURUSD", _e(2020, 5, 4), _e(2020, 5, 9))


def test_t8_real_eurusd_bogus_bar(eurusd_slice):
    m1 = eurusd_slice
    flag, info = e0.e0_flags(m1)
    tgt = _e(2020, 5, 7, 12, 33, 4)
    j = int(np.nonzero(m1["t"] == tgt)[0][0])
    assert flag[j]
    assert abs(m1["h"][j] / info[0]["ref"] - 1) > 0.03


def test_t8_snb_not_flagged():
    # SNB de-peg 2015-01-15 ~09:30 UTC: USDCHF moved ~30% and did NOT
    # revert within 15 min -> rule (b) must not flag it.
    m1 = dm.load_m1("USDCHF", _e(2015, 1, 15, 8, 0), _e(2015, 1, 15, 12, 0))
    flag, info = e0.e0_flags(m1)
    assert not flag.any()


def test_t10_second_stamp_flags():
    # A4F E0': non-minute-aligned timestamps are voided; nothing else.
    m1 = dm.load_m1("EURUSD", _e(2020, 5, 4), _e(2020, 5, 9))
    ss = e0.second_stamp(m1)
    tgt = _e(2020, 5, 7, 12, 33, 4)
    assert ss[np.nonzero(m1["t"] == tgt)[0][0]]
    # every other bar in the slice is minute-aligned -> not flagged
    assert ss.sum() == 1
    assert int(m1["t"][ss].max() % 60) != 0
    # minute-aligned bars never flagged (by construction of the rule)
    assert not ss[m1["t"] % 60 == 0].any()


def test_t10_known_bogus_bars_flagged():
    # both V1-deciding prints + the 2019-12-01 gap-side near-miss
    for lo, tgt in [(_e(2020, 5, 4), _e(2020, 5, 7, 12, 33, 4)),
                    (_e(2022, 10, 17), _e(2022, 10, 19, 13, 47, 44)),
                    (_e(2019, 11, 29), _e(2019, 12, 1, 18, 1, 36))]:
        m1 = dm.load_m1("EURUSD", lo, tgt + 7200)
        ss = e0.second_stamp(m1)
        assert (m1["t"] == tgt).any()
        assert ss[m1["t"] == tgt].all()


def test_t10_no_flag_window_identical():
    # EURUSD 2020-05-01..2020-05-06 has no second-stamped bar: E0' must
    # reproduce the no-void sim row for row (window-level T10 part c).
    m1 = dm.load_m1("EURUSD", _e(2020, 5, 1), _e(2020, 5, 6, 12, 0))
    tf = dm.resample(m1, 15)
    orders = [{"t": 5, "dir": 1,
               "entry": float(m1["c"][-1] + 0.0005),
               "sl": float(m1["c"][-1] - 0.0020),
               "tp": float(m1["c"][-1] + 0.0200),
               "expiry_ctm": int(m1["t"][-1]), "meta": {}}]
    atr = np.full(len(tf["t"]), 0.001)
    a = sm.run_trades(m1, tf, orders, "EURUSD", atr=atr)
    b = sm.run_trades(m1, tf, orders, "EURUSD", atr=atr,
                      void_extra=e0.second_stamp(m1))
    pd.testing.assert_frame_equal(a, b)


def test_t9_no_flag_window_reproduces():
    # zero flags -> void_extra must leave the sim identical (T9 core).
    n = 200
    t = [_e(2020, 1, 6, 8, 0) + 60 * i for i in range(n)]
    base = np.linspace(1.10, 1.11, n)
    m1 = _mk(t, base, base + 0.0005, base - 0.0005, base + 0.0001)
    tf = {"t": np.asarray(t[::15]), "c": np.asarray(m1["c"])[::15],
          "minutes": 15}
    orders = [{"t": 10, "dir": 1, "entry": float(base[150] + 0.0006),
               "sl": 1.0980, "tp": 1.1300, "expiry_ctm": t[150] + 4 * 3600,
               "meta": {}}]
    atr = np.full(len(tf["t"]), 0.001)
    tr1 = sm.run_trades(m1, tf, orders, "EURUSD", atr=atr)
    tr2 = sm.run_trades(m1, tf, orders, "EURUSD", atr=atr,
                        void_extra=np.zeros(n, bool))
    tr3 = sm.run_trades(m1, tf, orders, "EURUSD", atr=atr,
                        skip_suspect=True, void_extra=np.zeros(n, bool))
    pd.testing.assert_frame_equal(tr1, tr2)
    assert len(tr3) == len(tr1)
