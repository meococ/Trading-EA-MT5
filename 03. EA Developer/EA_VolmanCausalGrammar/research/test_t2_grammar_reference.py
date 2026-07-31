from __future__ import annotations

from datetime import datetime, timedelta, timezone
from random import Random

import pytest

from t2_grammar_reference import (
    Bar,
    ARM_MASKS,
    Barrier,
    CAPABILITY_STATUS,
    CostInputs,
    BrokerSchedule,
    DailyArmLedger,
    ModelContext,
    a0_candidate,
    a1_candidate,
    a2_candidate,
    a3_candidate,
    a3_candidate_with_audit,
    a4_select,
    close_break,
    close_only_label,
    compute_indicators,
    cost_geometry,
    daily_entry_decision,
    daily_entry_decision_from_finalized,
    derived_invalidation,
    first_margin_crossing,
    fit_sigmoid_calibration,
    fit_train_normalization,
    fit_weighted_logistic,
    generated_engine_events,
    apply_normalization,
    apply_sigmoid_calibration,
    attach_model_context,
    common_feature_vector,
    equal_year_weights,
    lock_barrier,
    masked_features,
    nearest_opposing_room,
    parity_vector,
    predict_logistic,
    pressure_true,
    round_grid_room,
    schedule_state,
    schedule_step,
    select_nearest_break_and_consume,
)


def bars_from_closes(closes, start=1.0, step_minutes=5):
    t0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
    bars = []
    for i, c in enumerate(closes):
        bars.append(Bar(t0 + timedelta(minutes=i * step_minutes), c - 0.08, c + 0.02, c - 0.10, c))
    return bars


def mirror_bars(bars):
    return [
        Bar(b.utc_open, -b.open, -b.low, -b.high, -b.close)
        for b in bars
    ]


def manual_barrier(bars, side="LONG", price=3.0, lock_index=30, atr=0.20, expiry=None):
    return Barrier("EURUSD", side, price, lock_index, bars[lock_index].utc_open, (14, 22, lock_index), atr, f"B-{side}", expiry or lock_index + 12)


def positive_a1_bars():
    closes = [1.0 + i * 0.01 for i in range(26)]
    closes += [1.30, 1.45, 1.60, 1.75, 1.90, 2.05]  # pressure through 31
    closes += [2.940, 2.945, 2.950, 2.955, 2.960, 2.965, 2.970, 2.975, 3.05]
    bars = []
    t0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
    for i, c in enumerate(closes):
        high = c + 0.02
        low = c - (0.16 if i < 32 else 0.08)
        if 32 <= i <= 39:
            high = 3.00 + (0.01 if i % 2 == 0 else -0.005)
            low = 2.86 + 0.015 * (i - 32)
        if i == 40:
            high = 3.08
            low = 2.96
        bars.append(Bar(t0 + timedelta(minutes=5 * i), c - 0.04, high, low, c))
    ind = compute_indicators(bars)
    barrier = manual_barrier(bars, "LONG", 3.0, 30, ind.atr14[30] or 0.2)
    return bars, ind, barrier


def positive_a2_bars():
    bars, _, barrier = positive_a1_bars()
    bars = list(bars)
    bars[38] = Bar(bars[38].utc_open, 2.92, 3.00, 2.93, 2.995)
    bars[39] = Bar(bars[39].utc_open, 2.95, 2.99, 2.94, 2.96)
    return bars, compute_indicators(bars), barrier


def positive_a3_bars():
    closes = [1.0 + i * 0.01 for i in range(26)]
    closes += [1.30, 1.48, 1.66, 1.84, 2.02, 2.20, 2.38, 2.56]
    closes += [2.46, 2.43, 2.45, 2.50]
    bars = list(bars_from_closes(closes))
    bars[35] = Bar(bars[35].utc_open, 2.40, 2.45, 2.00, 2.43)
    bars[36] = Bar(bars[36].utc_open, 2.42, 2.46, 2.40, 2.45)
    bars[37] = Bar(bars[37].utc_open, 2.44, 2.52, 2.43, 2.50)
    ind = compute_indicators(bars)
    support = manual_barrier(bars, "SHORT", 2.00, 20, ind.atr14[33] or 0.2, expiry=60)
    return bars, ind, support


def test_pressure_and_a1_positive_and_long_short_mirror():
    bars, ind, barrier = positive_a1_bars()
    assert CAPABILITY_STATUS["status"] == "PARTIAL_PRE_BUILD_REFERENCE"
    assert pressure_true(bars, ind, 31, "LONG")
    cand = a1_candidate(bars, ind, barrier, 40)
    assert cand and cand.arm == "A1_PATTERN_BREAK"
    assert a0_candidate(bars, ind, barrier, 40)

    mb = mirror_bars(bars)
    mind = compute_indicators(mb)
    mbarrier = manual_barrier(mb, "SHORT", -3.0, 30, mind.atr14[30] or 0.2)
    mcand = a1_candidate(mb, mind, mbarrier, 40)
    assert mcand and mcand.side == "SHORT"


def test_a2_combi_positive_and_inside_reject():
    bars, ind, barrier = positive_a2_bars()
    assert a2_candidate(bars, ind, barrier, 40, tick=0.01)

    broken = list(bars)
    broken[39] = Bar(broken[39].utc_open, 2.95, 3.05, 2.80, 2.96)
    assert a2_candidate(broken, compute_indicators(broken), barrier, 40, tick=0.01) is None


def test_duplicate_barrier_and_close_break_consumption_rule():
    closes = [1.0 + i * 0.01 for i in range(40)]
    bars = bars_from_closes(closes)
    ind = compute_indicators(bars)
    old = manual_barrier(bars, "LONG", bars[30].high, 30, ind.atr14[30] or 0.1)
    assert lock_barrier(bars, ind, "EURUSD", 32, "LONG", 0.00001, [old]) is None

    b = manual_barrier(bars, "LONG", 1.30, 20, 0.1)
    bars2 = list(bars)
    bars2[25] = Bar(bars2[25].utc_open, 1.28, 1.29, 1.24, 1.28)
    bars2[26] = Bar(bars2[26].utc_open, 1.31, 1.35, 1.30, 1.32)
    assert close_break(bars2, compute_indicators(bars2), b, 26)
    chosen, updated = select_nearest_break_and_consume(bars2, compute_indicators(bars2), [b, manual_barrier(bars2, "LONG", 1.31, 20, 0.1)], 26, "LONG")
    assert chosen and chosen.price == pytest.approx(1.30)
    assert sum(1 for x in updated if x.consumed) == 2
    equal = manual_barrier(bars2, "LONG", bars2[25].close, 20, 0.1)
    chosen2, updated2 = select_nearest_break_and_consume(bars2, compute_indicators(bars2), [equal], 26, "LONG")
    assert chosen2 is None
    assert updated2[0].consumed


def test_a3_reversal_and_pbp_exclusion():
    bars, ind, support = positive_a3_bars()
    cand = a3_candidate(bars, ind, 37, "LONG", [support])
    assert cand is not None and cand.reject_reason is None

    broken = manual_barrier(bars, "LONG", 2.35, 28, ind.atr14[33] or 0.2)
    broken = Barrier(**{**broken.__dict__, "consumed": True, "consumed_index": 34})
    rejected = a3_candidate(bars, ind, 37, "LONG", [support, broken], [broken])
    assert rejected and rejected.reject_reason == "SKIP_PBP_EXCLUDED"
    rejected2, audit = a3_candidate_with_audit(bars, ind, 37, "LONG", [support, broken], [broken], tick=0.01)
    assert rejected2 and rejected2.reject_reason == "SKIP_PBP_EXCLUDED"
    assert audit and audit[0].event_type in {"PBP_BREAK_WINDOW", "PBP_TOMBSTONE_CONTACT"}
    assert audit[0].producer_spec_sha256
    assert audit[0].symbol == "EURUSD"
    assert audit[0].timeframe == "M5"
    assert audit[0].trigger_index == 37
    assert audit[0].trigger_utc == bars[37].utc_open
    assert audit[0].barrier_side == "LONG"
    assert audit[0].barrier_price_ticks is not None
    assert audit[0].barrier_id == broken.barrier_id
    assert audit[0].lock_utc == broken.lock_utc
    if audit[0].event_type == "PBP_BREAK_WINDOW":
        assert audit[0].decision_index == audit[0].break_index
        assert audit[0].decision_utc == audit[0].break_utc
        assert audit[0].break_index is not None and audit[0].break_utc == bars[audit[0].break_index].utc_open
    if audit[0].event_type == "PBP_TOMBSTONE_CONTACT":
        assert audit[0].decision_index == audit[0].contact_index
        assert audit[0].decision_utc == audit[0].contact_utc
        assert audit[0].contact_index is not None and audit[0].contact_utc == bars[audit[0].contact_index].utc_open
        assert audit[0].consumed_index == 34


def test_a3_invalid_release_or_contact_emits_no_pbp_audit_and_tick_normalizes():
    bars, ind, support = positive_a3_bars()
    broken = manual_barrier(bars, "LONG", 2.35, 28, ind.atr14[33] or 0.2)
    broken = Barrier(**{**broken.__dict__, "consumed": True, "consumed_index": 34})
    invalid_release = list(bars)
    invalid_release[37] = Bar(invalid_release[37].utc_open, 2.44, 2.45, 2.43, 2.44)
    cand, audit = a3_candidate_with_audit(invalid_release, compute_indicators(invalid_release), 37, "LONG", [support, broken], [broken], tick=0.01)
    assert cand is None and audit == ()

    no_contact = Barrier(**{**broken.__dict__, "price": 9.99, "barrier_id": "JPY_TICK"})
    cand2, audit2 = a3_candidate_with_audit(bars, ind, 37, "LONG", [support, no_contact], [no_contact], tick=0.01)
    assert cand2 is not None and cand2.reject_reason is None and audit2 == ()

    early = Barrier(**{**broken.__dict__, "price": 2.00, "barrier_id": "XAU_TICK", "consumed_index": 34})
    rejected, audit3 = a3_candidate_with_audit(bars, ind, 37, "LONG", [support], [early], tick=0.10)
    assert rejected and rejected.reject_reason == "SKIP_PBP_EXCLUDED"
    assert audit3[0].event_type == "PBP_TOMBSTONE_CONTACT"
    assert audit3[0].contact_index == 35
    assert audit3[0].barrier_price_ticks == round(2.00 / 0.10)


def test_cost_counted_once_break_even_and_rejects():
    g = cost_geometry(1.2000, 1.1990, 0.0012, CostInputs(0.00008, 0.00010, 7.0, 0.00001, 1.0))
    expected_cost = 0.00010 + 7.0 / 1.0 * 0.00001 + 2 * 0.00001
    assert g["cost"] == pytest.approx(expected_cost)
    assert g["p_BE"] == pytest.approx((1 + expected_cost / 0.0010) / 3)
    assert first_margin_crossing(0.0, 0.001)
    with pytest.raises(ValueError):
        cost_geometry(1.2, 1.2, 0.001, CostInputs(0.1, 0.1, 1, 0.01, 1))


def test_next_open_daily_label_cost_once_and_room():
    bars, ind, barrier = positive_a1_bars()
    cand = a1_candidate(bars, ind, barrier, 40)
    more = list(bars)
    t = more[-1].utc_open
    for k in range(1, 15):
        close = 3.43 if k == 2 else 3.06
        more.append(Bar(t + timedelta(minutes=5 * k), close - 0.01, close + 0.02, close - 0.02, close))
    cost = CostInputs(0.002, 0.003, 0.01, 0.001, 1.0)
    inv = derived_invalidation(more, compute_indicators(more), cand)
    decision = daily_entry_decision(more, cand, -0.01, 0.02, invalidation=inv, cost=cost)
    assert not decision.accepted and decision.reason == "SKIP_ENTRY_GAP_RECHECK" and decision.entry_index == 41 and decision.consumed_date
    label = close_only_label(more, 41, "LONG", more[41].open, 0.15, decision.geometry["cost"])
    assert label.label == 1 and label.exit_reason == "CLOSE_TARGET"
    assert label.net_r == pytest.approx((2 * 0.15 - decision.geometry["cost"]) / 0.15)
    assert not daily_entry_decision(more, cand, 0.01, 0.02, invalidation=inv, cost=cost).consumed_date
    opposing = Barrier("EURUSD", "LONG", 3.50, 20, more[20].utc_open, (10, 15, 20), 0.2, "OPPOSING", 60)
    assert nearest_opposing_room(3.05, "LONG", 0.10, [opposing], barrier.barrier_id) == pytest.approx(4.5)
    with pytest.raises(ValueError, match="INSUFFICIENT_CLOSE_ONLY_HORIZON"):
        close_only_label(more[:45], decision.entry_index, "LONG", decision.entry_reference, decision.geometry["r"], decision.geometry["cost"])


def test_public_daily_decision_rejects_caller_forged_invalidation():
    bars, ind, barrier = positive_a1_bars()
    cand = a1_candidate(bars, ind, barrier, 40)
    more = list(bars)
    t = more[-1].utc_open
    for k in range(1, 15):
        close = 3.43 if k == 2 else 3.06
        more.append(Bar(t + timedelta(minutes=5 * k), close - 0.01, close + 0.02, close - 0.02, close))
    cost = CostInputs(0.002, 0.003, 0.01, 0.001, 1.0)
    derived = derived_invalidation(more, compute_indicators(more), cand)

    with pytest.raises(ValueError, match="caller invalidation mismatch"):
        daily_entry_decision(more, cand, -0.01, 0.02, invalidation=2.90, cost=cost)

    decision = daily_entry_decision(more, cand, -0.01, 0.02, invalidation=derived, cost=cost)
    assert not decision.accepted and decision.reason == "SKIP_ENTRY_GAP_RECHECK"


def test_daily_finalized_wrapper_rejects_cleanly_and_consumes_quota():
    bars, ind, barrier = positive_a1_bars()
    cand = a1_candidate(bars, ind, barrier, 40, tick=0.01)
    more = list(bars)
    t = more[-1].utc_open
    for k in range(1, 15):
        more.append(Bar(t + timedelta(minutes=5 * k), 3.05, 3.08, 3.00, 3.06))
    ind = compute_indicators(more)
    cost = CostInputs(0.002, 0.003, 0.01, 0.001, 1.0)
    too_close = Barrier("EURUSD", "LONG", 3.10, 20, more[20].utc_open, (1, 2, 3), 0.2, "CLOSE", 80)
    ledger = DailyArmLedger.empty()

    decision = daily_entry_decision_from_finalized(
        more,
        ind,
        cand,
        -1,
        1,
        cost,
        ledger,
        active_barriers=[too_close],
        tick=0.01,
        median_train_atr=0.2,
    )
    assert decision.reason == "SKIP_INSUFFICIENT_ROOM"
    assert decision.consumed_date
    second = daily_entry_decision_from_finalized(
        more,
        ind,
        cand,
        -1,
        1,
        cost,
        ledger,
        active_barriers=[],
        tick=0.01,
        median_train_atr=0.2,
    )
    assert second.reason == "SKIP_UTC_DATE_ARM_ALREADY_CONSUMED"


def test_daily_finalized_wrapper_verifies_context_before_ledger_consumption():
    bars, ind, barrier = positive_a1_bars()
    cand = a1_candidate(bars, ind, barrier, 40, tick=0.01)
    more = list(bars)
    t = more[-1].utc_open
    for k in range(1, 15):
        more.append(Bar(t + timedelta(minutes=5 * k), 3.05, 3.08, 3.00, 3.06))
    ind = compute_indicators(more)
    cost = CostInputs(0.002, 0.003, 0.01, 0.001, 1.0)
    finalized = finalize_candidate_context_import()(more, ind, cand, [], cost, tick=0.01, median_train_atr=0.2)
    forged = type(finalized)(
        finalized.arm,
        finalized.side,
        finalized.trigger_index,
        finalized.barrier,
        finalized.features | {"derived_invalidation": finalized.features["derived_invalidation"] + 0.01},
        finalized.reject_reason,
    )
    ledger = DailyArmLedger.empty()

    with pytest.raises(ValueError, match="finalized candidate context mismatch: derived_invalidation"):
        daily_entry_decision_from_finalized(
            more,
            ind,
            forged,
            -1,
            1,
            cost,
            ledger,
            active_barriers=[],
            tick=0.01,
            median_train_atr=0.2,
        )
    assert ledger.consumed == set()


def test_nearest_opposing_room_ignores_wrong_side_barriers():
    bars, _, barrier = positive_a1_bars()
    wrong = Barrier("EURUSD", "SHORT", 3.10, 20, bars[20].utc_open, (1, 2, 3), 0.2, "WRONG", 60)
    right = Barrier("EURUSD", "LONG", 3.50, 20, bars[20].utc_open, (1, 2, 3), 0.2, "RIGHT", 60)

    assert nearest_opposing_room(3.05, "LONG", 0.10, [wrong], barrier.barrier_id) == float("inf")
    assert nearest_opposing_room(3.05, "LONG", 0.10, [wrong, right], barrier.barrier_id) == pytest.approx(4.5)


def test_derived_invalidation_context_room_and_friday_horizon():
    bars, ind, barrier = positive_a1_bars()
    cand = a1_candidate(bars, ind, barrier, 40, tick=0.01)
    inv = derived_invalidation(bars, ind, cand)
    expected = min(b.low for b in bars[barrier.lock_index:41]) - 0.10 * ind.atr14[40]
    assert inv == pytest.approx(expected)
    bars = list(bars) + [Bar(bars[-1].utc_open + timedelta(minutes=5), 3.05, 3.08, 3.00, 3.06)]
    ind = compute_indicators(bars)
    too_close = Barrier("EURUSD", "LONG", 3.10, 20, bars[20].utc_open, (1, 2, 3), 0.2, "CLOSE", 60)
    finalized = finalize_candidate_context_import()(bars, ind, cand, [too_close], CostInputs(0.002, 0.003, 0.01, 0.001, 1.0), tick=0.01, median_train_atr=0.2)
    assert finalized.reject_reason == "SKIP_INSUFFICIENT_ROOM"

    friday = []
    start = datetime(2026, 1, 9, 22, 55, tzinfo=timezone.utc)
    for i in range(70):
        friday.append(Bar(start + timedelta(minutes=5*i), 1.0, 1.1, 0.9, 1.0))
    fc = type(cand)(cand.arm, cand.side, 5, cand.barrier, cand.features)
    assert daily_entry_decision(friday, fc, -1, 1, 0.9, CostInputs(0.001,0.001,0.001,0.001,1)).reason == "SKIP_FRIDAY_FLAT_HORIZON"


def finalize_candidate_context_import():
    from t2_grammar_reference import finalize_candidate_context
    return finalize_candidate_context


def test_round_grid_room_and_missing_flag():
    room, missing = round_grid_room(1932.5, "LONG", 5.0, 3.2, 0.01)
    assert missing == 0
    assert room > 0
    room2, missing2 = round_grid_room(1932.5, "LONG", 5.0, 0.0, 0.01)
    assert (room2, missing2) == (0.0, 1)


def test_a4_conflict_priority_and_margin_crossing():
    c1 = object()
    bars, _, barrier = positive_a1_bars()
    a1 = a1_candidate(bars, compute_indicators(bars), barrier, 40)
    a2 = a2_candidate(bars, compute_indicators(bars), barrier, 40)
    selected = a4_select([x for x in [a1, a2] if x])
    assert selected.arm in {"A2_PATTERN_BREAK_COMBI", "A1_PATTERN_BREAK"}

    short = type(a1)("A3_PULLBACK_REVERSAL", "SHORT", 40, None, {})  # same dataclass, opposite side
    conflict = a4_select([a1, short])
    assert conflict.reject_reason == "SKIP_DIRECTION_CONFLICT"
    assert c1 is not None


def test_gap_contiguity_prefix_invariance_and_warmup_surface():
    bars = bars_from_closes([1 + i * 0.01 for i in range(60)])
    pbars, _, barrier = positive_a1_bars()
    events = generated_engine_events(pbars, barrier, tick=0.01)
    suffix = list(pbars) + [Bar(pbars[-1].utc_open + timedelta(minutes=5), 3.1, 3.2, 3.0, 3.15)]
    assert events == generated_engine_events(suffix, barrier, tick=0.01)[: len(events)]

    gapped = list(bars)
    gapped[20] = Bar(gapped[20].utc_open + timedelta(minutes=10), gapped[20].open, gapped[20].high, gapped[20].low, gapped[20].close)
    from t2_grammar_reference import contiguous_m5

    assert contiguous_m5(bars, 0, 30)
    assert not contiguous_m5(gapped, 0, 30)
    assert schedule_state(bars[19], gapped[20]) == "UNEXPECTED_GAP_RESET_WARMUP_50"
    assert schedule_state(bars[19], gapped[20], in_position=True) == "DATA_GAP_EXIT"
    assert schedule_state(bars[19], gapped[20], scheduled_closed=True) == "SCHEDULED_RESET"
    sched = BrokerSchedule("BTCUSD", "UTC", "A"*64, weekend_coverage_only=True, remap_indices=frozenset({10}))
    assert schedule_step(bars[9], bars[10], sched, index=10, warmup_remaining=0).state == "SYMBOL_REMAP_RESET"
    sat = Bar(datetime(2026, 1, 10, tzinfo=timezone.utc), 1, 2, 0, 1)
    assert schedule_step(bars[0], sat, sched, index=11, warmup_remaining=0).state == "WEEKEND_COVERAGE_ONLY_RESET"
    assert schedule_step(bars[19], gapped[20], BrokerSchedule("EURUSD","UTC","B"*64), index=20, warmup_remaining=0, in_position=True).engineering_invalid
    ledger = DailyArmLedger.empty()
    assert ledger.try_consume("A1", bars[0].utc_open)
    assert not ledger.try_consume("A1", bars[1].utc_open)


def test_parity_vector_export_is_deterministic():
    bars, ind, barrier = positive_a1_bars()
    cand = a1_candidate(bars, ind, barrier, 40, tick=0.01)
    pv1 = parity_vector(cand, bars, ind)
    pv2 = parity_vector(cand, bars, ind)
    assert pv1 == pv2
    assert pv1["capability_status"] == "PARTIAL_PRE_BUILD_REFERENCE"
    assert pv1["barrier_id"] == barrier.barrier_id


def with_context(cand, rho=0.05, r_cash_atr=1.0):
    return attach_model_context(cand, ModelContext(room_r=2.5, round_grid_room_r=1.2, grid_feature_missing=0, rho=rho, r_cash_atr=r_cash_atr))


def test_feature_masks_normalization_year_weights_and_constant_logging():
    assert ARM_MASKS["A0_LOCKED_BARRIER_BREAK"] == (1, 2, 3, 13, 14)
    bars, ind, barrier = positive_a2_bars()
    raw_cand = a2_candidate(bars, ind, barrier, 40, tick=0.01)
    with pytest.raises(ValueError, match="missing required feature room_r"):
        common_feature_vector(raw_cand)
    cand = with_context(raw_cand)
    f = common_feature_vector(cand)
    assert len(f) == 26
    assert f[0] == pytest.approx(0.0)  # clip((3 touches - 3)/3)
    assert 0.0 <= f[2] <= 1.0
    assert 0.0 <= f[3] <= 2.0
    assert f[4] == pytest.approx(cand.features["pressure_duration"] / 12.0)
    assert f[24] == 1.0  # PBC one-hot
    assert masked_features(cand, "A4_CAUSAL_GRAMMAR_POLICY")[24] == 1.0
    assert masked_features(cand, "A0_LOCKED_BARRIER_BREAK")[4] == 0.0
    assert masked_features(cand, "A0_LOCKED_BARRIER_BREAK")[12] == pytest.approx(0.05)
    clipped = with_context(type(cand)(cand.arm, cand.side, cand.trigger_index, cand.barrier, cand.features | {"touch_count": 10.0, "break_margin_atr": 9.0}))
    cf = common_feature_vector(clipped)
    assert cf[0] == 1.0 and cf[2] == 1.0
    extreme = with_context(type(cand)(cand.arm, cand.side, cand.trigger_index, cand.barrier, cand.features | {
        "pressure_disp": 100.0,
        "pressure_er": -100.0,
        "pressure_mean_clv": 0.2,
        "pressure_ema_slope": 0.1,
    }))
    ef = common_feature_vector(extreme)
    expected_raw_mean = (100.0 / 0.60 + -100.0 / 0.55 + 0.2 / 0.20 + 0.1 / 0.10) / 4
    assert ef[3] == pytest.approx(max(0.0, min(2.0, expected_raw_mean)))
    rows = [f, [x + (0.1 if i == 0 else 0.0) for i, x in enumerate(f)], list(f)]
    norm = fit_train_normalization(rows)
    assert 1 in norm.constant_features
    z = apply_normalization(rows[0], norm)
    assert z[1] == 0.0
    times = [
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 2, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 1, tzinfo=timezone.utc),
    ]
    weights = equal_year_weights(times)
    assert weights[0] == weights[1] == pytest.approx(0.25)
    assert weights[2] == pytest.approx(0.5)


def test_weighted_logistic_and_calibration_are_deterministic_and_fatal_single_class():
    x_rows = [[-2.0] + [0.0]*25, [-1.0] + [0.0]*25, [1.0] + [0.0]*25, [2.0] + [0.0]*25]
    y = [0, 0, 1, 1]
    times = [
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 2, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        datetime(2021, 2, 1, tzinfo=timezone.utc),
    ]
    fit1 = fit_weighted_logistic(x_rows, y, times)
    fit2 = fit_weighted_logistic(x_rows, y, times)
    assert fit1 == fit2
    assert fit1.converged and fit1.iterations <= 1000 and fit1.grad_inf <= 1e-10
    assert predict_logistic(fit1.beta, x_rows[0]) < predict_logistic(fit1.beta, x_rows[-1])
    with pytest.raises(ValueError, match="length mismatch"):
        fit_weighted_logistic(x_rows[:-1], y, times)
    with pytest.raises(ValueError, match="dimension mismatch"):
        predict_logistic(fit1.beta, [1.0])
    with pytest.raises(ValueError):
        fit_weighted_logistic(x_rows, [1, 1, 1, 1], times)

    raw = [predict_logistic(fit1.beta, x) for x in x_rows]
    cal = fit_sigmoid_calibration(raw, y)
    assert cal.converged and cal.grad_inf <= 1e-10
    assert apply_sigmoid_calibration(raw[0], cal) < apply_sigmoid_calibration(raw[-1], cal)
    with pytest.raises(ValueError):
        fit_sigmoid_calibration(raw, [0, 0, 0, 0])
    with pytest.raises(ValueError, match="length mismatch"):
        fit_sigmoid_calibration(raw[:-1], y)


def jitter_decision_ohlc(bars, rng):
    out = list(bars)
    for i in range(len(out)):
        j = rng.uniform(-1e-6, 1e-6)
        b = out[i]
        open_ = min(max(b.open + j, b.low), b.high)
        close = min(max(b.close + j, b.low), b.high)
        out[i] = Bar(b.utc_open, open_, b.high, b.low, close)
    return out


def test_seed_20260732_perturbation_sensitivity_and_negative_order_controls():
    rng = Random(20260732)
    checks = []
    for side in ("LONG", "SHORT"):
        base, _, barrier = positive_a1_bars()
        if side == "SHORT":
            base = mirror_bars(base)
            barrier = manual_barrier(base, "SHORT", -3.0, 30, compute_indicators(base).atr14[30] or 0.2)
        checks.append(("A0", side, base, barrier, 40, lambda b, i, x, t: a0_candidate(b, i, x, t)))
        checks.append(("A1", side, base, barrier, 40, lambda b, i, x, t: a1_candidate(b, i, x, t)))

        b2, _, barrier2 = positive_a2_bars()
        if side == "SHORT":
            b2 = mirror_bars(b2)
            barrier2 = manual_barrier(b2, "SHORT", -3.0, 30, compute_indicators(b2).atr14[30] or 0.2)
        checks.append(("A2", side, b2, barrier2, 40, lambda b, i, x, t: a2_candidate(b, i, x, t)))

        b3, _, support = positive_a3_bars()
        if side == "SHORT":
            b3 = mirror_bars(b3)
            support = manual_barrier(b3, "LONG", -2.0, 20, compute_indicators(b3).atr14[33] or 0.2, expiry=60)
        checks.append(("A3", side, b3, support, 37, lambda b, i, x, t: a3_candidate(b, i, t, side, [x])))

    for arm, side, base, aux, t, fn in checks:
        hits = 0
        for _ in range(200):
            perturbed = jitter_decision_ohlc(base, rng)
            if fn(perturbed, compute_indicators(perturbed), aux, t):
                hits += 1
        assert hits / 200 >= 0.95, (arm, side, hits)

    for arm, _, base, barrier, t, fn in checks:
        # A0 has no event-order state, so sequence-negative control applies to
        # grammar arms only.
        if arm != "A0":
            for mode in ("shuffle", "reverse"):
                hits = 0
                for _ in range(200):
                    ordered = list(base)
                    lo, hi = (32, 40) if t == 40 else (35, 37)
                    segment = list(ordered[lo:hi])
                    if mode == "reverse":
                        segment = list(reversed(segment))
                    else:
                        rng.shuffle(segment)
                        segment = sorted(
                            segment,
                            key=lambda b: b.low if base[t].close > base[t - 1].close else -b.high,
                            reverse=True,
                        )
                    ordered[lo:hi] = segment
                    hits += int(bool(fn(ordered, compute_indicators(ordered), barrier, t)))
                assert hits / 200 <= 0.05, (arm, mode, hits)
