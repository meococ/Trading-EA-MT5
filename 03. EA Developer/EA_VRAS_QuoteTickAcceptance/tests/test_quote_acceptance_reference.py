"""Red/green tests for the deterministic HYP-013 quote acceptance reference."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

from quote_acceptance_reference import (  # noqa: E402
    AGE_MAX_MS,
    AGE_MIN_MS,
    CSV_COLUMNS,
    EVENT_ARMED,
    EVENT_OBSERVE,
    HYPOTHESIS_ID,
    MAX_GAP_MS,
    MAX_SPREAD_RATIO,
    MIN_IMBALANCE,
    MIN_PRICE_CHANGES,
    MIN_QUOTE_UPDATES,
    POINT,
    PREARM_MIN,
    PREARM_RING,
    QuoteAcceptanceEngine,
    TERMINAL_ACCEPTED,
    TERMINAL_DEINIT,
    TERMINAL_EXPIRE,
    TERMINAL_GAP,
    TERMINAL_INVALID,
    TERMINAL_SPREAD,
    TERMINAL_STATES,
    TERMINAL_VWAP,
    build_monotonic_prearm,
    compute_rolling_vwap,
    evaluate_closed_bar_arm,
    imbalance_ratio,
    normalize_server_tick_msc,
    prearm_median_spread,
    quote_is_valid,
)


VWAP = 1.10000
SPREAD = 0.00010  # 10 points on 5-digit
BID0 = 1.10050


def test_server_tick_clock_normalizes_to_utc():
    assert normalize_server_tick_msc(1_784_784_337_089, 10_800_000) == 1_784_773_537_089


def _engine_with_prearm(n: int = PREARM_MIN, spread: float = SPREAD, bid: float = BID0):
    eng = QuoteAcceptanceEngine(point=POINT, run_id="test")
    eng.seed_prearm_quotes(build_monotonic_prearm(n=n, start_msc=1_000_000, bid=bid, spread=spread))
    return eng


def _arm_long(eng: QuoteAcceptanceEngine, arm_msc: int = 2_000_000, bid: float = BID0, spread: float = SPREAD):
    assert eng.try_arm_from_closed_bar("long", VWAP, arm_bar_time=1_700_000_000)
    ev = eng.on_quote(arm_msc, bid, bid + spread)
    assert ev is not None and ev.event == EVENT_ARMED
    return ev


def _arm_short(eng: QuoteAcceptanceEngine, arm_msc: int = 2_000_000, bid: float = 1.09950, spread: float = SPREAD):
    # short: VWAP above market
    assert eng.try_arm_from_closed_bar("short", VWAP, arm_bar_time=1_700_000_000)
    ev = eng.on_quote(arm_msc, bid, bid + spread)
    assert ev is not None and ev.event == EVENT_ARMED
    return ev


def _push_path(
    eng: QuoteAcceptanceEngine,
    *,
    start_msc: int,
    n: int,
    mid_step: float,
    step_msc: int = 500,
    base_bid: float,
    spread: float = SPREAD,
    age_target_ms: int | None = None,
):
    """Push n observation quotes with mid moving by mid_step each price-changing tick."""
    events = []
    bid = base_bid
    t = start_msc
    for i in range(n):
        if age_target_ms is not None and i == n - 1:
            t = eng.arm_time_msc + age_target_ms
        else:
            t = start_msc + i * step_msc
        bid = base_bid + i * mid_step
        ev = eng.on_quote(t, bid, bid + spread)
        if ev is not None:
            events.append(ev)
        if eng.arm_terminal is not None:
            break
    return events


# ---------------------------------------------------------------------------
# Closed-bar arm
# ---------------------------------------------------------------------------

def test_closed_bar_long_and_short_mirror():
    long_sig = evaluate_closed_bar_arm(
        h1_close=1.12,
        h1_ema=1.10,
        shift1_high=1.1010,
        shift1_low=1.0990,
        shift1_close=1.1005,
        shift2_high=1.1000,
        shift2_low=1.0980,
        vwap=1.1000,
    )
    assert long_sig == "long"
    short_sig = evaluate_closed_bar_arm(
        h1_close=1.08,
        h1_ema=1.10,
        shift1_high=1.1010,
        shift1_low=1.0990,
        shift1_close=1.0995,
        shift2_high=1.1020,
        shift2_low=1.1000,
        vwap=1.1000,
    )
    assert short_sig == "short"
    none_sig = evaluate_closed_bar_arm(
        h1_close=1.12,
        h1_ema=1.10,
        shift1_high=1.1010,
        shift1_low=1.1005,  # low above vwap — no touch
        shift1_close=1.1008,
        shift2_high=1.1000,
        shift2_low=1.0980,
        vwap=1.1000,
    )
    assert none_sig is None


def test_vwap_skips_zero_volume_rows():
    bars = [
        {"high": 1.1, "low": 1.0, "close": 1.05, "tick_volume": 0},
        {"high": 2.0, "low": 2.0, "close": 2.0, "tick_volume": 10},
    ]
    assert abs(compute_rolling_vwap(bars) - 2.0) < 1e-12
    assert compute_rolling_vwap([{"high": 1, "low": 1, "close": 1, "tick_volume": 0}]) == 0.0


# ---------------------------------------------------------------------------
# Pre-arm / dedup / median
# ---------------------------------------------------------------------------

def test_prearm_dedup_non_monotonic_time():
    eng = QuoteAcceptanceEngine()
    eng.on_quote(1000, 1.1, 1.1001)
    eng.on_quote(1000, 1.1, 1.1002)  # duplicate time — skipped
    eng.on_quote(999, 1.1, 1.1003)   # non-monotonic — skipped
    eng.on_quote(1001, 1.1, 1.1004)
    assert len(eng.prearm_spreads) == 2


def test_prearm_median_and_minimum_gate():
    spreads = [0.00010 + (i % 5) * 0.00001 for i in range(PREARM_MIN)]
    med = prearm_median_spread(spreads)
    assert med == prearm_median_spread(sorted(spreads))
    eng = _engine_with_prearm(n=PREARM_MIN - 1)
    eng.try_arm_from_closed_bar("long", VWAP, 1)
    # Freeze attempt with insufficient pre-arm drops pending
    assert eng.on_quote(2_000_000, BID0, BID0 + SPREAD) is None
    assert eng.arm_active is False
    assert eng.pending_direction is None


def test_prearm_ring_caps_at_60():
    eng = QuoteAcceptanceEngine()
    for i in range(PREARM_RING + 25):
        eng.on_quote(1_000_000 + i, 1.1, 1.1 + 0.00010)
    assert len(eng.prearm_spreads) == PREARM_RING


def test_zero_prearm_median_cannot_freeze_arm():
    eng = _engine_with_prearm(spread=0.0)
    assert eng.try_arm_from_closed_bar("long", VWAP, 1)
    assert eng.on_quote(2_000_000, BID0, BID0) is None
    assert eng.arm_active is False
    assert eng.pending_direction is None


def test_invalid_quote_helpers():
    assert quote_is_valid(10, 1.1, 1.2, None)
    assert not quote_is_valid(10, 1.1, 1.0, None)  # ask < bid
    assert not quote_is_valid(10, -1.0, 1.0, None)
    assert not quote_is_valid(10, 1.1, 1.2, 10)
    assert not quote_is_valid(9, 1.1, 1.2, 10)


# ---------------------------------------------------------------------------
# Terminal states
# ---------------------------------------------------------------------------

def test_reject_vwap_recross_long_and_short():
    eng = _engine_with_prearm()
    _arm_long(eng, bid=1.10050)
    # long: bid must stay strictly above VWAP; touch rejects
    ev = eng.on_quote(2_000_500, VWAP, VWAP + SPREAD)
    assert ev is not None and ev.event == TERMINAL_VWAP

    eng2 = _engine_with_prearm(bid=1.09950)
    _arm_short(eng2, bid=1.09950)
    # short: ask must stay strictly below VWAP
    ev2 = eng2.on_quote(2_000_500, VWAP - SPREAD, VWAP)
    assert ev2 is not None and ev2.event == TERMINAL_VWAP


def test_reject_spread_spike():
    eng = _engine_with_prearm(spread=SPREAD)
    _arm_long(eng, spread=SPREAD)
    # spike > 1.50 * median (median ~ SPREAD)
    wide = SPREAD * (MAX_SPREAD_RATIO + 0.1)
    ev = eng.on_quote(2_000_500, BID0 + 0.00001, BID0 + 0.00001 + wide)
    assert ev is not None and ev.event == TERMINAL_SPREAD


def test_reject_stale_gap():
    eng = _engine_with_prearm()
    _arm_long(eng)
    ev = eng.on_quote(2_000_000 + MAX_GAP_MS + 1, BID0 + 0.00001, BID0 + 0.00001 + SPREAD)
    assert ev is not None and ev.event == TERMINAL_GAP


def test_reject_invalid_quote_while_active():
    eng = _engine_with_prearm()
    _arm_long(eng)
    ev = eng.on_quote(2_000_000, BID0, BID0 + SPREAD)  # non-increasing time
    assert ev is not None and ev.event == TERMINAL_INVALID


def test_expire_no_acceptance():
    eng = _engine_with_prearm()
    _arm_long(eng)
    # Stream quotes with small gaps so only age expiry can fire (no stale gap).
    # Unchanged mid → no directional expansion → cannot accept.
    ev = None
    step = 1_000  # 1s < 15s max gap
    steps = (AGE_MAX_MS // step) + 2
    for i in range(1, steps + 1):
        t = 2_000_000 + i * step
        ev = eng.on_quote(t, BID0, BID0 + SPREAD)
        if eng.arm_terminal is not None:
            break
    assert eng.arm_terminal == TERMINAL_EXPIRE
    assert ev is not None and ev.event == TERMINAL_EXPIRE


def test_deinit_active_arm():
    eng = _engine_with_prearm()
    _arm_long(eng)
    ev = eng.on_deinit(2_050_000)
    assert ev is not None and ev.event == TERMINAL_DEINIT
    assert eng.arm_active is False


def test_accepted_observation_long_path():
    """Construct a path that satisfies all eight gates inside the age window."""
    eng = _engine_with_prearm(spread=SPREAD)
    _arm_long(eng, arm_msc=2_000_000, bid=BID0, spread=SPREAD)

    # Need >=20 updates, >=12 price changes, imbalance >=0.60,
    # net expansion >= arm spread, spread<=median, no spike/gap/vwap.
    # Move mid up steadily (directional for long).
    n = 25
    step = 0.00002  # 2 points per tick
    # Ensure last tick lands in [30s, 120s]
    for i in range(n):
        if i < n - 1:
            t = 2_000_000 + 1000 + i * 1000  # 1s steps → ends ~25s, still early
        else:
            t = 2_000_000 + AGE_MIN_MS  # exactly 30s on last
        bid = BID0 + (i + 1) * step
        # keep bid strictly above VWAP
        assert bid > VWAP
        ev = eng.on_quote(t, bid, bid + SPREAD)
        if eng.arm_terminal is not None:
            break
    assert eng.arm_terminal == TERMINAL_ACCEPTED, (
        eng.arm_terminal,
        eng.quote_updates,
        eng.price_changes,
        eng.directional_moves,
        eng.opposite_moves,
        imbalance_ratio(eng.directional_moves, eng.opposite_moves),
    )
    assert eng.events[-1].event == TERMINAL_ACCEPTED
    assert eng.events[-1].promotion_eligible is False
    assert eng.events[0].event == EVENT_ARMED


def test_accepted_observation_short_symmetry():
    eng = _engine_with_prearm(bid=1.09950, spread=SPREAD)
    _arm_short(eng, arm_msc=2_000_000, bid=1.09950, spread=SPREAD)
    base = 1.09950
    step = -0.00002  # downticks for short directional
    n = 25
    for i in range(n):
        if i < n - 1:
            t = 2_000_000 + 1000 + i * 1000
        else:
            t = 2_000_000 + AGE_MIN_MS
        bid = base + (i + 1) * step
        ask = bid + SPREAD
        assert ask < VWAP
        eng.on_quote(t, bid, ask)
        if eng.arm_terminal is not None:
            break
    assert eng.arm_terminal == TERMINAL_ACCEPTED


# ---------------------------------------------------------------------------
# Individual acceptance gates (negative paths)
# ---------------------------------------------------------------------------

def test_gate_min_quote_updates_blocks_accept():
    eng = _engine_with_prearm()
    _arm_long(eng)
    # One big directional jump at age 30s but only 1 update
    bid = BID0 + 0.00100
    ev = eng.on_quote(2_000_000 + AGE_MIN_MS, bid, bid + SPREAD)
    assert ev is not None
    assert ev.event != TERMINAL_ACCEPTED
    assert eng.quote_updates == 1


def test_gate_imbalance_blocks_accept():
    eng = _engine_with_prearm()
    _arm_long(eng)
    # Alternate up/down → imbalance ~0.5
    bid = BID0
    for i in range(25):
        t = 2_000_000 + 1000 + i * 1000
        if i == 24:
            t = 2_000_000 + AGE_MIN_MS
        delta = 0.00002 if (i % 2 == 0) else -0.00002
        bid = BID0 + delta
        if bid <= VWAP:
            bid = VWAP + 0.00005
        eng.on_quote(t, bid, bid + SPREAD)
        if eng.arm_terminal is not None:
            break
    assert eng.arm_terminal != TERMINAL_ACCEPTED


def test_gate_net_expansion_requires_arm_spread():
    eng = _engine_with_prearm(spread=SPREAD)
    _arm_long(eng, spread=SPREAD)
    # Tiny upward moves that never reach one full arm spread net
    tiny = SPREAD / 100.0
    for i in range(25):
        t = 2_000_000 + 1000 + i * 1000
        if i == 24:
            t = 2_000_000 + AGE_MIN_MS
        bid = BID0 + (i + 1) * tiny
        eng.on_quote(t, bid, bid + SPREAD)
        if eng.arm_terminal is not None:
            break
    assert eng.arm_terminal != TERMINAL_ACCEPTED


def test_gate_current_spread_vs_prearm_median():
    eng = _engine_with_prearm(spread=SPREAD)
    _arm_long(eng, spread=SPREAD)
    wide = SPREAD * 1.2  # > median but < 1.50 spike threshold
    assert wide <= MAX_SPREAD_RATIO * SPREAD
    for i in range(25):
        t = 2_000_000 + 1000 + i * 1000
        if i == 24:
            t = 2_000_000 + AGE_MIN_MS
        bid = BID0 + (i + 1) * 0.00002
        eng.on_quote(t, bid, bid + wide)
        if eng.arm_terminal is not None:
            break
    # Should not accept while current spread > prearm median
    assert eng.arm_terminal != TERMINAL_ACCEPTED


def test_age_window_before_30s_cannot_accept():
    eng = _engine_with_prearm()
    _arm_long(eng)
    for i in range(25):
        t = 2_000_000 + 200 + i * 200  # max age ~5s
        bid = BID0 + (i + 1) * 0.00002
        eng.on_quote(t, bid, bid + SPREAD)
        if eng.arm_terminal is not None:
            break
    assert eng.arm_terminal not in (TERMINAL_ACCEPTED, None) or eng.arm_terminal is None
    if eng.arm_terminal is None:
        assert eng.events[-1].event == EVENT_OBSERVE
        assert eng.events[-1].age_ms < AGE_MIN_MS


# ---------------------------------------------------------------------------
# Immutability / one arm / CSV / constants
# ---------------------------------------------------------------------------

def test_terminal_state_is_immutable():
    eng = _engine_with_prearm()
    _arm_long(eng)
    eng.on_quote(2_000_000 + MAX_GAP_MS + 5, BID0 + 0.00001, BID0 + 0.00001 + SPREAD)
    assert eng.arm_terminal == TERMINAL_GAP
    n_events = len(eng.events)
    # Further quotes must not emit another terminal for same arm
    eng.on_quote(2_000_000 + MAX_GAP_MS + 1000, BID0 + 0.00002, BID0 + 0.00002 + SPREAD)
    terminals = [e.event for e in eng.events if e.event in TERMINAL_STATES]
    assert terminals == [TERMINAL_GAP]
    assert len(eng.events) >= n_events  # may add nothing material for same arm


def test_cannot_overwrite_active_arm():
    eng = _engine_with_prearm()
    _arm_long(eng)
    assert eng.try_arm_from_closed_bar("short", VWAP, 99) is False
    assert eng.direction == "long"


def test_csv_columns_frozen():
    assert CSV_COLUMNS[0] == "schema_version"
    assert CSV_COLUMNS[-1] == "promotion_eligible"
    assert "frozen_vwap" in CSV_COLUMNS
    assert "prearm_median_spread_points" in CSV_COLUMNS
    assert HYPOTHESIS_ID == "HYP-VRAS-EURUSD-M5-014"


def test_frozen_constants():
    assert PREARM_RING == 60
    assert PREARM_MIN == 30
    assert AGE_MIN_MS == 30_000
    assert AGE_MAX_MS == 120_000
    assert MIN_QUOTE_UPDATES == 20
    assert MIN_PRICE_CHANGES == 12
    assert MIN_IMBALANCE == 0.60
    assert MAX_SPREAD_RATIO == 1.50
    assert MAX_GAP_MS == 15_000


def test_observe_events_before_terminal():
    eng = _engine_with_prearm()
    _arm_long(eng)
    for i in range(3):
        eng.on_quote(2_000_100 + i * 100, BID0 + 0.00001 * (i + 1), BID0 + 0.00001 * (i + 1) + SPREAD)
    kinds = [e.event for e in eng.events]
    assert kinds[0] == EVENT_ARMED
    assert EVENT_OBSERVE in kinds


def test_promotion_eligible_always_false_on_rows():
    eng = _engine_with_prearm()
    _arm_long(eng)
    eng.on_deinit(2_010_000)
    for e in eng.events:
        row = e.as_row()
        assert row["promotion_eligible"] is False
        assert set(CSV_COLUMNS) == set(row.keys())
