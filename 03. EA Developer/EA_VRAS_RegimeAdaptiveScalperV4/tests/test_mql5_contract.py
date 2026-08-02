from __future__ import annotations

import json
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "EA_VRAS_RegimeAdaptiveScalperV4.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
PREREG = PACKAGE / "research" / "HYP-VRAS-USDJPY-M5-001_PREREG.md"
ENGINEERING_AMENDMENT = (
    PACKAGE / "research" / "HYP-VRAS-USDJPY-M5-001_ENGINEERING_AMENDMENT.md"
)


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_atomic_defaults_are_frozen():
    text = source_text()
    assert 'InpHypothesisId="HYP-VRAS-USDJPY-M5-001"' in text
    assert "InpMagic=5601601" in text
    assert 'if(_Symbol!="USDJPY" || _Period!=PERIOD_M5)' in text
    assert "InpOuWindow=72" in text
    assert "InpVarianceRatioQ=5" in text
    assert "InpEntryZ=2.0" in text
    assert "InpTailStopZ=4.0" in text
    assert "InpDirectionMultiplier=1" in text


def test_decision_data_are_closed_bar_only():
    text = source_text()
    assert "CopyClose(_Symbol,PERIOD_M5,1,InpOuWindow" in text
    assert "CopyTime(_Symbol,PERIOD_M5,1,InpOuWindow" in text
    assert "CopyBuffer(g_atr_handle,0,1,1" in text
    assert not re.search(r"Copy(?:Close|Rates)\([^\n]*,\s*0\s*,", text)
    assert not re.search(r"CopyBuffer\([^,]+,[^,]+,\s*0\s*,", text)
    assert not re.search(r"i(?:Open|High|Low|Close)\([^\n]*,\s*0\s*\)", text)


def test_execution_is_synchronous_tester_only_with_server_stops():
    text = source_text()
    assert "OrderCheck(request,check)" in text
    assert "check.retcode!=0" in text
    assert "OrderSend(request,result)" in text
    assert "OrderSendAsync" not in text
    assert "MQLInfoInteger(MQL_TESTER)" in text
    assert "request.sl=stop" in text
    assert "request.tp=target" in text


def test_mandatory_exits_do_not_depend_on_a_valid_ou_estimate():
    text = source_text()
    on_tick = text.split("void OnTick()", 1)[1]
    mandatory_call = on_tick.index("ManageMandatoryClosedBar(current_bar)")
    estimator_call = on_tick.index("ComputeOuState(current_bar,state)")
    assert mandatory_call < estimator_call
    assert "MustFlattenForClock(ServerToUtc(current_bar))" in text
    assert "current_bar-entry_bar_open>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5)" in text


def test_entry_risk_telemetry_is_bound_before_order_send_callback():
    text = source_text()
    entry_function = text.split("bool TryOpenTrade", 1)[1].split(
        "bool PositionIdentifierExists", 1
    )[0]
    assert entry_function.index("g_worst_entry_bound=geometry_entry") < entry_function.index(
        "OrderSend(request,result)"
    )
    assert entry_function.index("g_planned_risk_account=risk_account") < entry_function.index(
        "OrderSend(request,result)"
    )
    assert entry_function.index("g_planned_volume=volume") < entry_function.index(
        "OrderSend(request,result)"
    )
    assert entry_function.index("g_planned_risk_per_lot=risk_account/volume") < entry_function.index(
        "OrderSend(request,result)"
    )


def test_partial_fills_receive_proportional_risk_and_use_immutable_fill_bound():
    text = source_text()
    lifecycle = text.split("void LogLifecycleDeal", 1)[1].split(
        "void FlushPendingLifecycleDeals", 1
    )[0]
    assert "deal_volume=HistoryDealGetDouble(deal,DEAL_VOLUME)" in lifecycle
    assert "deal_initial_risk=g_stop_risk_per_lot*deal_volume" in lifecycle
    assert "DoubleToString(deal_initial_risk,8)" in lifecycle
    reconciler = text.split("void ReconcileLifecycleEntryDeal", 1)[1].split(
        "void FlushPendingLifecycleDeals", 1
    )[0]
    assert "direction*(confirmed_price-g_worst_entry_bound)>0.5*_Point" in reconciler
    assert "g_worst_entry_bound=confirmed_price" not in reconciler


def test_pending_exit_reconciliation_blocks_entry_and_cleanup_is_position_scoped():
    text = source_text()
    entry_function = text.split("bool TryOpenTrade", 1)[1].split(
        "bool PositionIdentifierExists", 1
    )[0]
    assert "ArraySize(g_pending_lifecycle_exit_deals)>0" in entry_function
    lifecycle = text.split("void LogLifecycleDeal", 1)[1].split(
        "void FlushPendingLifecycleDeals", 1
    )[0]
    assert "if(final_close && position_id==g_position_identifier)" in lifecycle


def test_final_close_telemetry_is_deferred_and_history_reconciled():
    text = source_text()
    transaction = text.split("void OnTradeTransaction", 1)[1].split(
        "void OnTick()", 1
    )[0]
    assert "QueueLifecycleExitDeal(trans.deal)" in transaction
    assert "ReconcileLifecycleEntryDeal(trans.deal)" in transaction
    assert "ExitFinalDisposition" in text
    assert "HistorySelectByPosition(position_id)" in text
    assert "latest_exit_deal" in text
    assert "exit_volume+0.5*volume_step<entry_volume" in text
    on_tick = text.split("void OnTick()", 1)[1]
    assert on_tick.index("FlushPendingLifecycleDeals(false)") < on_tick.index(
        "EnforceTickRisk()"
    )


def test_prop_risk_is_persistent_and_fail_closed():
    text = source_text()
    for token in (
        "GlobalVariableSet",
        "GlobalVariablesFlush",
        "InpDailySoftStopPct=2.0",
        "InpDailyHardStopPct=3.5",
        "InpMaxAccountDrawdownPct=8.0",
        "AverageLastTenEntryLots",
        "InpMaxTradesPerDay=3",
        "MustFlattenForClock",
        "bool PersistRiskState()",
        "GlobalVariableGet",
        "g_persistence_fault",
    ):
        assert token in text
    entry_function = text.split("bool TryOpenTrade", 1)[1].split(
        "bool PositionIdentifierExists", 1
    )[0]
    assert "g_persistence_fault" in entry_function


def test_wrapping_session_and_hold_contract_are_explicit():
    text = source_text()
    assert "WrappingSessionKey" in text
    assert "WrappingSessionDayAllows" in text
    assert "bar_times[i]-bar_times[i+1]!=PeriodSeconds(PERIOD_M5)" in text
    assert "WrappingSessionKey(bar_utc)!=decision_session_key" in text
    assert "g_entry_bar_open=state.decision_server" in text
    assert "current_bar-entry_bar_open>=InpMaxHoldBars*PeriodSeconds(PERIOD_M5)" in text


def test_geometry_is_gated_on_worst_allowed_fill():
    text = source_text()
    assert "geometry_entry=entry+direction*InpSlippageOneWayPips*PipSize()" in text
    assert "BuildGeometry(state,direction,geometry_entry,stop,target)" in text
    assert "RiskSizedVolume(direction,geometry_entry,stop,risk_account,stop_risk_per_lot)" in text
    assert "g_confirmed_fill_breach" in text


def test_risk_sizing_does_not_double_count_entry_slippage_bound():
    risk_function = source_text().split("double RiskSizedVolume", 1)[1].split(
        "double NormalizePrice", 1
    )[0]
    assert "remaining_cost_pips=InpCommissionPips+InpSlippageOneWayPips" in risk_function
    assert "2.0*InpSlippageOneWayPips" not in risk_function


def test_lifecycle_risk_money_and_points_share_stop_only_basis():
    text = source_text()
    lifecycle = text.split("void LogLifecycleDeal", 1)[1].split(
        "void ReconcileLifecycleEntryDeal", 1
    )[0]
    assert "deal_initial_risk=g_stop_risk_per_lot*deal_volume" in lifecycle
    assert "deal_initial_risk=g_planned_risk_per_lot*deal_volume" not in lifecycle
    assert "MathAbs(g_worst_entry_bound-g_initial_stop)/_Point" in lifecycle


def test_engineering_amendment_freezes_adverse_bound_geometry_without_post_fill_widening():
    amendment = ENGINEERING_AMENDMENT.read_text(encoding="utf-8")
    assert "adverse entry bound" in amendment
    assert "does not widen the server stop" in amendment
    assert "remaining exit slippage" in amendment


def test_no_true_flow_or_multi_engine_claims_leak_into_source():
    upper = source_text().upper()
    for forbidden in ("VPIN", "CVD", "LOB OFI", "ORDER FLOW IMBALANCE", "VOLUME SPIKE DELTA"):
        assert forbidden not in upper
    assert "VOLMAN" not in upper
    assert "LIQUIDITY SWEEP" not in upper


def test_lifecycle_v3_contract_and_sidecars():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract == {
        "schema_version": "alphafactory_ea_contract.v1",
        "telemetry_profile": "lifecycle-v3",
        "market_phase_adapter": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "variant_tag_input": "InpVariantTag",
    }
    text = source_text()
    assert "_LifecycleTrades_" in text
    assert "_DecisionTelemetry_" in text
    assert "_RunMeta_" in text
    assert '"promotion_eligible\\\":false' in text
    assert '"persistence_fault\\\":%s' in text
    assert '"confirmed_fill_breach\\\":%s' in text
    assert '"pending_lifecycle_exit_deals\\\":%d' in text
    assert "g_run_persistence_fault_seen=true" in text
    assert "g_run_confirmed_fill_breach_seen=true" in text
