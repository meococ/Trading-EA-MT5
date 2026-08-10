from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[2]
V9 = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV9/EA_SupertrendBurstScalperTradeV9.mq5"
V10 = PACKAGE / "EA_SupertrendBurstScalperTradeV10.mq5"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def function_body(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unterminated function: {signature}")


def money_stress(
    *,
    equity: float,
    check_margin: float,
    check_free: float,
    current_margin: float,
    entry_margin: float,
    stop_margin: float,
    stop_profit_before_charge: float,
    volume: float = 1.0,
    round_turn_charge_per_lot: float = 4.40,
    protected: float = 92_000.0,
    reserve_factor: float = 0.20,
    floor_pct: float = 1.0,
) -> tuple[bool, float, float]:
    stop_profit = stop_profit_before_charge - volume * round_turn_charge_per_lot
    stressed_equity = equity + stop_profit
    stressed_margin = max(check_margin, current_margin + max(entry_margin, stop_margin))
    extra_margin = max(0.0, stressed_margin - check_margin)
    stressed_check_free = check_free + stop_profit - extra_margin
    stressed_balance_free = stressed_equity - stressed_margin
    if stressed_equity <= protected:
        return False, stressed_check_free, math.inf
    reserve = max(
        (stressed_equity - protected) * reserve_factor,
        stressed_equity * floor_pct / 100.0,
    )
    threshold = protected + reserve
    return (
        stressed_check_free >= threshold and stressed_balance_free >= threshold,
        stressed_check_free,
        threshold,
    )


def test_fresh_v10_identity_is_fail_closed():
    text = source(V10)
    assert '#property version   "10.00"' in text
    assert 'InpHypothesisId        = "HYP-STBS-XAUUSD-M15-023"' in text
    assert 'InpVariantTag          = "STBS_H1_FLIP_M15_BURST_TRADE_V10_SL_STRESSED_MARGIN"' in text
    assert "InpMagic               = 5604123" in text
    assert 'EA_NAME              = "EA_SupertrendBurstScalperTradeV10"' in text
    assert 'InpHypothesisId!="HYP-STBS-XAUUSD-M15-023"' in text
    assert 'InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V10_SL_STRESSED_MARGIN"' in text
    assert "InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604123" in text


def test_signal_geometry_exit_and_runtime_backstop_are_unchanged():
    old = source(V9)
    new = source(V10)
    for signature in (
        "bool AdvanceSupertrend(",
        "bool BuildEntryGeometry(",
        "bool SubmitEntry(",
        "bool SubmitClose(",
        "bool SubmitCancelOrder(",
        "void ConsumeFlipEvent(",
        "bool ProcessNewClosedH1Bars(",
        "MarginSafetyResult EvaluateActualMargin(",
    ):
        assert function_body(new, signature) == function_body(old, signature)
    assert new.count("OrderSend(request,result)") == 3
    manage = function_body(new, "bool ReconcileExecutionState(")
    assert 'STBS_FATAL|actual_margin_contract_failed|result=%d' in manage
    assert "g_runtime_failed=true" in manage
    assert "SetExitIntent(EXIT_RUNTIME_FAULT)" in manage
    assert "g_margin_emergencies++" in manage


def test_candidate_uses_frozen_sl_profit_and_margin_stress():
    text = source(V10)
    assert "FROZEN_ROUND_TURN_COMMISSION_ACCOUNT_PER_LOT = 4.40" in text
    body = function_body(text, "MarginSafetyResult EvaluateMarginCandidate(")
    for needle in (
        "adverse_deviation=point*(double)InpDeviationPoints",
        "plan.entry+adverse_deviation",
        "plan.entry-adverse_deviation",
        "OrderCalcProfit(plan.order_type,_Symbol,volume,worst_fill,plan.stop,stop_profit_before_charge)",
        "stop_profit_before_charge>=0.0",
        "reserved_charge=volume*FROZEN_ROUND_TURN_COMMISSION_ACCOUNT_PER_LOT",
        "stressed_profit=stop_profit_before_charge-reserved_charge",
        "OrderCalcMargin(plan.order_type,_Symbol,volume,worst_fill,worst_fill_required_margin)",
        "OrderCalcMargin(plan.order_type,_Symbol,volume,plan.stop,stop_required_margin)",
        "candidate_required_margin=MathMax(required_margin",
        "stressed_equity=check.equity+stressed_profit",
        "stressed_margin=MathMax(check.margin",
        "stressed_check_free=check.margin_free+stressed_profit-extra_margin",
        "stressed_balance_free=stressed_equity-stressed_margin",
        "safe=stressed_check_free>=threshold && stressed_balance_free>=threshold",
        "safe=stressed_margin_level>=threshold",
    ):
        assert needle in body
    assert "safe=check.margin_free>=threshold" not in body
    assert "safe=check.margin_level>=threshold" not in body


def test_downward_only_broker_step_search_is_preserved():
    old = function_body(source(V9), "bool SelectMarginSafeVolume(")
    new = function_body(source(V10), "bool SelectMarginSafeVolume(")
    assert new == old
    assert "MathFloor(plan.volume/step)*step" in new
    assert "candidate=NormalizeDouble(candidate-step,digits)" in new
    assert "MARGIN_SAFETY_FATAL" in new
    assert "STBS_MARGIN_REJECT|min_volume_unsafe=true" in new


def test_money_mode_rejects_a_candidate_that_only_current_state_would_accept():
    safe, stressed_free, threshold = money_stress(
        equity=100_000.0,
        check_margin=5_000.0,
        check_free=95_000.0,
        current_margin=0.0,
        entry_margin=5_000.0,
        stop_margin=5_000.0,
        stop_profit_before_charge=-2_000.0,
    )
    assert 95_000.0 >= 93_600.0  # old current-price admission would pass
    assert stressed_free == 92_995.6
    assert threshold == 93_199.12
    assert safe is False


def test_money_mode_accepts_a_smaller_stressed_candidate():
    safe, stressed_free, threshold = money_stress(
        equity=100_000.0,
        check_margin=4_000.0,
        check_free=96_000.0,
        current_margin=0.0,
        entry_margin=4_000.0,
        stop_margin=4_000.0,
        stop_profit_before_charge=-1_500.0,
    )
    assert stressed_free == 94_495.6
    assert threshold == 93_299.12
    assert safe is True


def test_stressed_equity_at_or_below_protected_money_level_rejects():
    safe, _, threshold = money_stress(
        equity=93_000.0,
        check_margin=500.0,
        check_free=92_500.0,
        current_margin=0.0,
        entry_margin=500.0,
        stop_margin=500.0,
        stop_profit_before_charge=-1_000.0,
    )
    assert safe is False
    assert math.isinf(threshold)


def test_full_round_turn_charge_closes_the_exact_money_boundary():
    without_charge, _, threshold_without = money_stress(
        equity=100_000.0,
        check_margin=5_000.0,
        check_free=95_000.0,
        current_margin=0.0,
        entry_margin=5_000.0,
        stop_margin=5_000.0,
        stop_profit_before_charge=-1_750.0,
        round_turn_charge_per_lot=0.0,
    )
    with_charge, stressed_free, threshold_with = money_stress(
        equity=100_000.0,
        check_margin=5_000.0,
        check_free=95_000.0,
        current_margin=0.0,
        entry_margin=5_000.0,
        stop_margin=5_000.0,
        stop_profit_before_charge=-1_750.0,
    )
    assert without_charge is True
    assert 93_250.0 >= threshold_without
    assert stressed_free == 93_245.6
    assert stressed_free < threshold_with
    assert with_charge is False


def test_adverse_deviation_is_applied_against_both_directions():
    text = source(V10)
    body = function_body(text, "MarginSafetyResult EvaluateMarginCandidate(")
    assert "? plan.entry+adverse_deviation" in body
    assert ": plan.entry-adverse_deviation" in body
    assert "request.deviation=(ulong)InpDeviationPoints" in body
    assert "InpDeviationPoints!=20" in text


def test_stress_fields_are_persisted_only_after_pass():
    text = source(V10)
    body = function_body(text, "MarginSafetyResult EvaluateMarginCandidate(")
    pass_index = body.index("if(!safe)\n      return MARGIN_SAFETY_UNSAFE;")
    for assignment in (
        "plan.stressed_loss=stressed_profit",
        "plan.stressed_equity=stressed_equity",
        "plan.stressed_margin=stressed_margin",
        "plan.stressed_free_margin=stressed_check_free",
        "plan.stressed_margin_level=stressed_margin_level",
    ):
        assert body.index(assignment) > pass_index
