"""Simulator unit tests: pending fill, SL-first rule, costs, flatten."""
import numpy as np
import pandas as pd
import pytest

from src import data as data_mod
from src import sim


def _mk_m1(start_ctm, n, px=1.1000):
    t = start_ctm + np.arange(n) * 60
    o = np.full(n, px); h = px + 0.0005
    h = np.full(n, px + 0.0005); l = np.full(n, px - 0.0005)
    c = np.full(n, px); tv = np.full(n, 100.0)
    return {"t": t.astype(np.int64), "o": o, "h": h, "l": l, "c": c,
            "tv": tv, "suspect": np.zeros(n, bool)}


def _mk_tf15(m1):
    return data_mod.resample(m1, 15)


def test_pending_fill_and_tp():
    m1 = _mk_m1(1600000000, 200)
    tf = _mk_tf15(m1)
    # signal on tf bar 0; buy stop at 1.1010; M1 px rises in bar 20..
    m1["h"][30:] = 1.1020; m1["o"][30:] = 1.1008
    m1["c"][30:] = 1.1015; m1["l"][30:] = 1.1000
    orders = [{"t": 0, "dir": 1, "entry": 1.1010, "sl": 1.0990,
               "tp": 1.1018, "expiry_ctm": tf["t"][0] + 4 * 900,
               "meta": {"cfg": "T"}}]
    tr = sim.run_trades(m1, tf, orders, "EURUSD")
    assert len(tr) == 1
    row = tr.iloc[0]
    assert row["entry"] == pytest.approx(1.1010)
    assert row["reason"] == "tp"
    assert row["exit"] == pytest.approx(1.1018)


def test_sl_first_on_ambiguous_bar():
    m1 = _mk_m1(1600000000, 200)
    tf = _mk_tf15(m1)
    # one M1 bar contains BOTH sl and tp -> SL wins
    m1["h"][30] = 1.1030; m1["l"][30] = 1.0985; m1["o"][30] = 1.1005
    m1["c"][30] = 1.0990
    orders = [{"t": 0, "dir": 1, "entry": 1.1010, "sl": 1.0990,
               "tp": 1.1020, "expiry_ctm": tf["t"][0] + 4 * 900,
               "meta": {"cfg": "T"}}]
    tr = sim.run_trades(m1, tf, orders, "EURUSD")
    assert len(tr) == 1
    assert tr.iloc[0]["reason"] in ("sl", "sl_same")
    assert tr.iloc[0]["exit"] == pytest.approx(1.0990)


def test_pending_expires():
    m1 = _mk_m1(1600000000, 200)
    tf = _mk_tf15(m1)
    orders = [{"t": 0, "dir": 1, "entry": 1.2000, "sl": 1.0990,
               "tp": 1.3000, "expiry_ctm": tf["t"][0] + 4 * 900,
               "meta": {"cfg": "T"}}]
    tr = sim.run_trades(m1, tf, orders, "EURUSD")
    assert len(tr) == 0


def test_one_position_at_a_time():
    m1 = _mk_m1(1600000000, 300)
    tf = _mk_tf15(m1)
    m1["h"][30:] = 1.1020; m1["o"][30:] = 1.1008
    m1["l"][30:] = 1.1000; m1["c"][30:] = 1.1015
    od = {"t": 0, "dir": 1, "entry": 1.1010, "sl": 1.0990,
          "tp": 1.2500, "expiry_ctm": tf["t"][0] + 4 * 900,
          "meta": {"cfg": "T"}}
    od2 = {"t": 3, "dir": 1, "entry": 1.1010, "sl": 1.0990,
           "tp": 1.2500, "expiry_ctm": tf["t"][3] + 4 * 900,
           "meta": {"cfg": "T"}}
    tr = sim.run_trades(m1, tf, [od, od2], "EURUSD")
    assert len(tr) == 1                     # second signal skipped (busy)


def test_cost_fields():
    m1 = _mk_m1(1600000000, 200)
    tf = _mk_tf15(m1)
    m1["h"][30:] = 1.1020; m1["o"][30:] = 1.1008
    m1["l"][30:] = 1.1000; m1["c"][30:] = 1.1015
    orders = [{"t": 0, "dir": 1, "entry": 1.1010, "sl": 1.1000,
               "tp": 1.1020, "expiry_ctm": tf["t"][0] + 4 * 900,
               "meta": {"cfg": "T"}}]
    tr = sim.run_trades(m1, tf, orders, "EURUSD")
    row = tr.iloc[0]
    cost = data_mod.COST["EURUSD"]
    expect = cost["spread"] + 2 * cost["slip_side"] + cost["comm"]
    assert row["cost_x1_px"] == pytest.approx(expect)
    assert row["pnl_px_x2"] == pytest.approx(
        (row["exit"] - row["entry"]) - 2 * expect)
