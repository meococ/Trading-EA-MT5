"""test_book_loader.py — every wall of the BOOK loader must bite.

Run from research/perception/:  python -m pytest tests/test_book_loader.py
"""

import os
import sys
import types

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
GOLDEN = os.path.join(PERC, "golden")
for _p in (PERC, GOLDEN, os.path.join(PERC, "..", "..", "lib")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import book_loader  # noqa: E402


def _banned_keys():
    return [k for k in sys.modules
            if str(k).split(".")[-1] in book_loader.BANNED_MODULES]


@pytest.fixture(autouse=True)
def _clean_banned():
    """No banned module (any dotted form) leaks between tests."""
    saved = {k: sys.modules[k] for k in _banned_keys()}
    for k in _banned_keys():
        sys.modules.pop(k, None)
    yield
    for k in _banned_keys():
        sys.modules.pop(k, None)
    sys.modules.update(saved)


@pytest.mark.parametrize("mod", sorted(book_loader.BANNED_MODULES))
def test_refuses_when_outcome_module_loaded(mod):
    sys.modules[mod] = types.ModuleType(mod)
    with pytest.raises(book_loader.BookWallError):
        book_loader.load_m1("2012-03-05 08:00", "2012-03-05 09:00")


def test_refuses_dotted_variant():
    sys.modules["lib.pa_eval"] = types.ModuleType("lib.pa_eval")
    with pytest.raises(book_loader.BookWallError):
        book_loader.load_m1("2012-03-05 08:00", "2012-03-05 09:00")


@pytest.mark.parametrize("lo,hi", [
    ("2012-02-12 23:55", "2012-02-13 01:00"),   # before window
    ("2012-09-07 23:00", "2012-09-08 00:05"),   # past end
    ("2010-06-01 00:00", "2010-06-01 01:00"),   # other 2010-2015 data
    ("2016-03-01 00:00", "2016-03-01 01:00"),   # DESIGN is NOT book data
])
def test_refuses_out_of_window(lo, hi):
    with pytest.raises(book_loader.BookWallError):
        book_loader.load_m1(lo, hi)


def test_loads_book_slice():
    d = book_loader.load_m1("2012-03-05 07:00", "2012-03-05 12:00")
    assert d["symbol"] == "EURUSD" and d["split"] == "BOOK" and d["pip"] == 1e-4
    n = len(d["t"])
    assert n > 200                      # ~5 h of minutes
    assert np.all(np.diff(d["t"]) > 0)
    # CET minute-of-day must cover 07:00..12:00 CET
    assert d["cet_min"][0] <= 7 * 60 + 1
    assert d["cet_min"][-1] >= 12 * 60 - 1
    # OHLC sanity
    assert np.all(d["h"] >= d["l"]) and np.all(d["h"] >= d["c"])
    assert np.all(d["l"] <= d["o"]) or np.all(d["l"] <= d["c"])


def test_load_m5_completeness():
    d = book_loader.load_m5("2012-03-05 07:00", "2012-03-05 12:00")
    assert d["tf"] == "M5"
    assert np.all(d["t"] % 300 == 0)
    # all complete 5-source bars
    assert len(d["t"]) >= 55            # 5 h * 12, minus boundary raggedness


def test_window_bounds_cover_casebook():
    lo_srv, hi_srv = book_loader.book_bounds_server()
    d = book_loader.load_m1()
    assert d["t"][0] >= lo_srv and d["t"][-1] < hi_srv
    # warm-up starts before 1 Mar and the window runs past 31 Aug
    import cet
    cet_e = d["cet"]
    import calendar
    from datetime import datetime
    mar1 = calendar.timegm(datetime(2012, 3, 1).timetuple())
    sep1 = calendar.timegm(datetime(2012, 9, 1).timetuple())
    assert cet_e[0] < mar1 and cet_e[-1] >= sep1 - 300
