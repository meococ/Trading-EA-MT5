"""Regression tests for causal swing detection in analysis/smc_engine.py.

A pivot at bar i is only knowable once the `length` bars to its right have
CLOSED — i.e. at confirmation bar i + length. The pre-fix code fed the pivot
index straight into determine_structure/calculate_pd_zone, so a swing was
treated as tradeable `length` bars before it could possibly be known
(lookahead bias). Same contract as tb_smc_closedbar_replay.py is_pivot_*,
where `index` IS the confirmation bar for `pivot_index = index - length`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
sys.path.insert(0, str(ANALYSIS))

from smc_engine import SMCEngine  # noqa: E402


LENGTH = 5
N_BARS = 40
PIVOT_H = 20
PIVOT_L = 30


def _hl(n: int = N_BARS) -> tuple[np.ndarray, np.ndarray]:
    """Strictly decreasing highs / increasing lows: zero natural pivots, so
    any injected spike/dip is the ONLY swing point in the series."""
    high = np.array([100.0 - 0.01 * i for i in range(n)])
    low = np.array([90.0 + 0.01 * i for i in range(n)])
    return high, low


def test_pivot_not_reported_before_confirmation() -> None:
    """Feeding a truncated series that ends before the confirmation bar must
    NOT report the pivot — detection may not touch bars right of the edge."""
    high, low = _hl()
    high[PIVOT_H] = 110.0  # visibly a swing high at bar PIVOT_H
    engine = SMCEngine()

    confirm = PIVOT_H + LENGTH
    # Every prefix ending at or before confirm-1 must hide the pivot.
    for end in range(PIVOT_H + 1, confirm + 1):
        sh_idx, _, sh_conf, sl_idx, _, _ = engine.detect_swing_points(
            high[:end], low[:end], LENGTH
        )
        assert PIVOT_H not in sh_idx, (
            f"pivot at {PIVOT_H} leaked into a series ending at bar {end - 1} "
            f"(confirmable only at {confirm})"
        )
        assert len(sh_conf) == 0


def test_pivot_reported_at_confirmation_bar() -> None:
    """The pivot is reported exactly once bar pivot+length exists, stamped at
    the pivot bar with confirmed_at = pivot + length, never beyond n-1."""
    high, low = _hl()
    high[PIVOT_H] = 110.0
    low[PIVOT_L] = 80.0  # swing low at PIVOT_L, confirm at PIVOT_L + LENGTH
    engine = SMCEngine()

    # Exactly the confirmation bar as the right edge: first visible here.
    confirm_h = PIVOT_H + LENGTH
    sh_idx, sh_prices, sh_conf, sl_idx, sl_prices, sl_conf = (
        engine.detect_swing_points(high[: confirm_h + 1], low[: confirm_h + 1], LENGTH)
    )
    assert list(sh_idx) == [PIVOT_H]
    assert sh_prices[0] == 110.0
    assert sh_conf[0] == confirm_h

    # Full series: both pivots, pivot timestamps kept, confirms in bounds.
    sh_idx, sh_prices, sh_conf, sl_idx, sl_prices, sl_conf = engine.detect_swing_points(
        high, low, LENGTH
    )
    assert list(sh_idx) == [PIVOT_H]
    assert list(sl_idx) == [PIVOT_L]
    assert sh_conf[0] == PIVOT_H + LENGTH
    assert sl_conf[0] == PIVOT_L + LENGTH
    assert sl_prices[0] == 80.0
    # No out-of-bounds-right access: every confirmation index is a real bar.
    assert sh_conf.max() <= N_BARS - 1
    assert sl_conf.max() <= N_BARS - 1


def test_unconfirmed_pivot_does_not_hide_confirmed_swing() -> None:
    """A still-unconfirmed newer pivot must not mask an older confirmed swing.

    H1 pivot high at bar 10 (110, confirmed at 15). H2 pivot high at bar 20
    (115, confirmed at 25). At bar 22 price closes at 112 — above the
    CONFIRMED 110 but below the not-yet-knowable 115. Under lookahead the
    engine already 'knew' 115 and suppressed the break; causally, bar 22
    must fire bullish BOS against 110.
    """
    n = N_BARS
    high, low = _hl(n)
    high[10] = 110.0
    high[20] = 115.0
    open_ = np.full(n, 95.0)
    close = np.full(n, 95.0)
    # Bar 22: close 112, high 113 (< 115 so the H2 pivot stays valid).
    open_[22] = 111.0
    high[22] = 113.0
    low[22] = 111.0
    close[22] = 112.0
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})

    engine = SMCEngine(ltf_swing_len=LENGTH, use_ob=False, use_fvg=False, use_pd_zone=False)
    signals = engine.generate_signals(df)

    assert signals["bos"].iloc[22] == 1, "close>confirmed 110 at bar 22 must BOS"
    assert signals["bias"].iloc[22] == 1
    # Sanity: pivot H2 only becomes known at bar 25 — nothing before 15 or
    # between 16..24 may reference it.
    sh_idx, _, sh_conf, *_ = engine.detect_swing_points(high, low, LENGTH)
    assert list(sh_idx) == [10, 20]
    assert list(sh_conf) == [15, 25]
