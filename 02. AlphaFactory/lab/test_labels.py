"""Unit test for labels._eval — hand-computed cases, BOTH sides.

Rule (hot.md 2026-09-19): any evaluator change must pass this before a
single cell is mined. Written after GATE A caught the side-swapped
SL/TP field bug (D1): for side=-1 the adverse excursion must come from
bar HIGHS (wick-touch), not lows.
"""
import numpy as np
import pandas as pd

import labels


def _mk(bars):
    """bars: list of (o,h,l,c). Returns a 1-pip=0.0001 plane."""
    df = pd.DataFrame(bars, columns=["o", "h", "l", "c"])
    df["suspect"] = False
    df["mod"] = 0
    df["dow"] = 2
    idx0 = 1_700_000_000
    df.index = pd.to_datetime(
        np.arange(len(df)) * 60 + idx0, unit="s")
    return df


def test_short_wick_touch_stop():
    # signal bar 0; entry open of bar1 at 1.1000; bar2 wicks to 1.1025
    # (touches -25p adverse) then closes 1.0990. sl=20 must fire at bar2.
    df = _mk([(1.1000, 1.1001, 1.0999, 1.1000),
              (1.1000, 1.1005, 1.0998, 1.1002),
              (1.1002, 1.1025, 1.0990, 1.0991),
              (1.0991, 1.0992, 1.0980, 1.0985)])
    r = labels.eval_events(df, np.array([True, False, False, False]),
                           side=-1, sl=20, tp=0, max_hold=2, pip=1e-4,
                           cost_rt=0.0)
    assert r["ret"][0] == -20.0, f"short wick-touch missed: {r['ret'][0]}"
    assert r["exit"][0] == "SL"
    assert r["mae"][0] <= -25.0 + 0.01, f"mae understated: {r['mae'][0]}"


def test_short_favorable_uses_lows():
    # short: bar2 dips to 1.0970 (+30p favorable), no stop touch.
    df = _mk([(1.1000, 1.1001, 1.0999, 1.1000),
              (1.1000, 1.1002, 1.0998, 1.0999),
              (1.0999, 1.1000, 1.0970, 1.0972),
              (1.0972, 1.0975, 1.0971, 1.0973)])
    r = labels.eval_events(df, np.array([True, False, False, False]),
                           side=-1, sl=20, tp=0, max_hold=2, pip=1e-4,
                           cost_rt=0.0)
    assert r["exit"][0] == "TIME"
    assert r["mfe"][0] >= 30.0 - 0.01, f"mfe understated: {r['mfe'][0]}"


def test_long_wick_touch_stop():
    # mirror: long entry 1.1000; bar2 wicks DOWN to 1.0975 -> SL -20.
    df = _mk([(1.1000, 1.1001, 1.0999, 1.1000),
              (1.1000, 1.1002, 1.0998, 1.0999),
              (1.0999, 1.1010, 1.0975, 1.0980),
              (1.0980, 1.0985, 1.0978, 1.0982)])
    r = labels.eval_events(df, np.array([True, False, False, False]),
                           side=1, sl=20, tp=0, max_hold=2, pip=1e-4,
                           cost_rt=0.0)
    assert r["ret"][0] == -20.0, f"long wick-touch missed: {r['ret'][0]}"
    assert r["exit"][0] == "SL"


def test_short_tp_uses_lows():
    # short tp=15 must fire when the LOW reaches entry-15p.
    df = _mk([(1.1000, 1.1001, 1.0999, 1.1000),
              (1.1000, 1.1002, 1.0998, 1.0999),
              (1.0999, 1.1000, 1.0983, 1.0986),
              (1.0986, 1.0988, 1.0980, 1.0984)])
    r = labels.eval_events(df, np.array([True, False, False, False]),
                           side=-1, sl=50, tp=15, max_hold=2, pip=1e-4,
                           cost_rt=0.0)
    assert r["ret"][0] == 15.0, f"short TP missed: {r['ret'][0]}"
    assert r["exit"][0] == "TP"


def test_tail_no_phantom_path():
    # event near data end: phantom bars must not trigger stops.
    df = _mk([(1.1000, 1.1001, 1.0999, 1.1000),
              (1.1000, 1.1002, 1.0998, 1.0999),
              (1.0999, 1.1000, 1.0990, 1.0995)])
    r = labels.eval_events(df, np.array([False, True, False]),
                           side=-1, sl=5, tp=0, max_hold=60, pip=1e-4,
                           cost_rt=0.0, drop_suspect_path=True)
    # padded bars are suspect=1 -> event dropped entirely (conservative)
    assert len(r["ret"]) == 0, "phantom tail produced a path"


if __name__ == "__main__":
    test_short_wick_touch_stop()
    test_short_favorable_uses_lows()
    test_long_wick_touch_stop()
    test_short_tp_uses_lows()
    test_tail_no_phantom_path()
    print("ALL PASS")
