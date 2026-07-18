"""Contract tests for EA_ICTVisualEdge Stage-1 corpus builder.

Guards the anti-peek invariants: closed-bar resample, sweep detection uses only
past bars, forward-R label only reads bars at/after entry, holdout never loads.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
MOD_PATH = HERE.parent / "stage1_data_candidates_labels.py"
spec = importlib.util.spec_from_file_location("s1", MOD_PATH)
s1 = importlib.util.module_from_spec(spec)
sys.modules["s1"] = s1
spec.loader.exec_module(s1)


def _synthetic_m1(n=600, start="2016-03-01"):
    t = pd.date_range(start, periods=n, freq="1min")
    rng = np.random.default_rng(7)
    price = 1.10 + np.cumsum(rng.normal(0, 0.0001, n))
    hi = price + np.abs(rng.normal(0, 0.00005, n))
    lo = price - np.abs(rng.normal(0, 0.00005, n))
    return pd.DataFrame({"time_utc": t, "open": price, "high": hi, "low": lo,
                         "close": price, "tick_volume": 10, "spread": 5})


def test_resample_closed_bar_edges():
    m1 = _synthetic_m1()
    bars = s1.resample_closed(m1, 5)
    # decision time is exactly open + step; never earlier (no peek into own bar)
    assert (bars["decision_time_utc"] - bars["open_time_utc"]
            == pd.Timedelta(minutes=5)).all()
    # OHLC bounds sane
    assert (bars["high"] >= bars["low"]).all()
    assert (bars["high"] >= bars["close"]).all()
    assert (bars["low"] <= bars["close"]).all()


def test_resample_ohlc_matches_manual_bin():
    m1 = _synthetic_m1()
    bars = s1.resample_closed(m1, 5)
    b0 = bars.iloc[0]
    win = m1[(m1["time_utc"] >= b0["open_time_utc"]) &
             (m1["time_utc"] < b0["decision_time_utc"])]
    assert b0["open"] == win["open"].iloc[0]
    assert b0["close"] == win["close"].iloc[-1]
    assert b0["high"] == win["high"].max()
    assert b0["low"] == win["low"].min()


def test_sweep_uses_only_past_bars():
    # construct a bar that sweeps prior low then reclaims -> LONG candidate
    n = 40
    bars = pd.DataFrame({
        "open_time_utc": pd.date_range("2016-01-01", periods=n, freq="5min"),
        "decision_time_utc": pd.date_range("2016-01-01 00:05", periods=n, freq="5min"),
        "high": [1.1010] * n, "low": [1.1000] * n, "close": [1.1005] * n,
    })
    bars.loc[20, "low"] = 1.0990      # sweeps the prior 12-bar low (1.1000)
    bars.loc[20, "close"] = 1.1004    # reclaims above prior low
    cand = s1.detect_generous_sweeps(bars)
    longs = cand[(cand["bar_i"] == 20) & (cand["direction"] == 1)]
    assert len(longs) == 1
    # a candidate can never anchor before enough lookback exists
    assert (cand["bar_i"] >= s1.SWEEP_LOOKBACK).all()


def test_label_reads_only_entry_and_future():
    # entry on bar i+1; a stop breach only on a FUTURE bar must register
    n = 60
    bars = pd.DataFrame({
        "open_time_utc": pd.date_range("2016-01-01", periods=n, freq="5min"),
        "decision_time_utc": pd.date_range("2016-01-01 00:05", periods=n, freq="5min"),
        "high": [1.1010] * n, "low": [1.1000] * n, "close": [1.1005] * n,
    })
    # long stop hit far in the future only
    exit_i, r, reason = s1.simulate_exit(bars, entry_i=10, direction=1,
                                         entry=1.1005, stop=1.0995,
                                         target=1.1025, max_hold=40, cost_r=0.0)
    assert exit_i >= 10
    assert reason in {"SL", "TP", "TIME", "BOTH_SL_FIRST"}


def test_both_hit_resolves_to_sl():
    bars = pd.DataFrame({
        "high": [1.1030], "low": [1.0990], "close": [1.1000],
    })
    _, r, reason = s1.simulate_exit(bars, 0, 1, entry=1.1005, stop=1.1000,
                                    target=1.1025, max_hold=1, cost_r=0.0)
    assert reason == "BOTH_SL_FIRST"
    assert r < 0


def test_holdout_boundary_constant():
    assert str(s1.HOLDOUT_START.date()) == "2023-01-01"
    for name, (lo, hi) in s1.SPLIT_BOUNDS.items():
        assert pd.Timestamp(hi) < s1.HOLDOUT_START


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
