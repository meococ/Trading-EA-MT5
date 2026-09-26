"""T14 (A1G): spike detector on the known bogus winners + flag rate
among VALIDATION TP winners (EUR+XAU, H1 FR, E0' files)."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import data as dm
from src import e0
from src import spike


def _e(y, m, d, hh=0, mm=0, ss=0):
    return int(dt.datetime(y, m, d, hh, mm, ss,
                           tzinfo=dt.timezone.utc).timestamp())


def _trade(sym, sig_ctm, e1=False, pre_e0=True):
    tag = "" if pre_e0 else "_e0s"
    f = (f"out/trades_2fval_{sym}_X0-HOLD{tag}"
         f"{'_e1' if e1 else ''}.csv")
    df = pd.read_csv(f)
    return df[df.sig_ctm == sig_ctm].iloc[0]


def _m1(sym, lo, hi):
    m1 = dm.load_m1(sym, lo, hi)
    return m1, e0.second_stamp(m1)


def test_t14_eurusd_bogus_winner_flagged():
    # pre-E0' file: TP filled at 0.6808 (bar open) on the second-
    # stamped bar; neighbours never printed that low -> spike flag.
    tr = _trade("EURUSD", 1666177200, e1=False, pre_e0=True)
    assert tr["reason"] == "tp" and tr["r_x1"] > 50
    m1, v = _m1("EURUSD", _e(2022, 10, 17), _e(2022, 10, 21))
    r = spike.spike_flag(m1, v, int(tr["dir"]), float(tr["exit"]),
                         int(tr["exit_ctm"]))
    assert r["flag"], r


def test_t14_usdcad_bogus_winner_flagged():
    tr = _trade("USDCAD", 1586447100, e1=False, pre_e0=True)
    assert tr["r_x1"] > 100
    m1, v = _m1("USDCAD", _e(2020, 4, 8), _e(2020, 4, 12))
    r = spike.spike_flag(m1, v, int(tr["dir"]), float(tr["exit"]),
                         int(tr["exit_ctm"]))
    assert r["flag"], r


@pytest.fixture(scope="module")
def flag_rate():
    """Flag rate among VALIDATION TP winners, EUR+XAU, H1 FR, E0'."""
    rows = []
    for sym in ("EURUSD", "XAUUSD"):
        df = pd.read_csv(f"out/trades_2fval_{sym}_AMONLY_e0s_e1.csv")
        w = df[(df.reason == "tp") & (df.r_x1 > 0)]
        m1 = dm.load_m1(sym, dm.VALIDATION[0], dm.VALIDATION[1])
        v = e0.second_stamp(m1)
        med = spike.day_med_range(m1, v)
        for _, tr in w.iterrows():
            r = spike.spike_flag(m1, v, int(tr["dir"]),
                                 float(tr["exit"]),
                                 int(tr["exit_ctm"]), med)
            rows.append({"sym": sym, "sig_ctm": int(tr["sig_ctm"]),
                         "exit_ctm": int(tr["exit_ctm"]),
                         "r_x1": tr["r_x1"], **r})
    return pd.DataFrame(rows)


def test_t14_flag_rate_reported(flag_rate):
    n = len(flag_rate)
    nf = int(flag_rate["flag"].sum())
    print(f"[T14] TP winners={n} flagged={nf} "
          f"({nf/max(n,1):.1%})")
    print(flag_rate[flag_rate["flag"]].to_string(index=False))
    flag_rate.to_csv("out/t14_flagged_val_tp.csv", index=False)
    # no threshold tuning: just assert the report ran
    assert n > 0
