from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[2]
V7 = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV7/EA_SupertrendBurstScalperTradeV7.mq5"
V8 = PACKAGE / "EA_SupertrendBurstScalperTradeV8.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST = PACKAGE / "research/HYP-STBS-XAUUSD-M15-021_RESEARCH_COST_SOURCE_MANIFEST.json"
PREREG = PACKAGE / "research/HYP-STBS-XAUUSD-M15-021_MODEL0_BASELINE_PREREG.md"


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


def test_fresh_v8_trade_identity_is_fail_closed():
    text = source(V8)
    assert '#property version   "8.00"' in text
    assert 'InpHypothesisId        = "HYP-STBS-XAUUSD-M15-021"' in text
    assert 'InpVariantTag          = "STBS_H1_FLIP_M15_BURST_TRADE_V8_STABLE_LIFECYCLE"' in text
    assert "InpMagic               = 5604121" in text
    assert 'EA_NAME              = "EA_SupertrendBurstScalperTradeV8"' in text
    assert 'InpHypothesisId!="HYP-STBS-XAUUSD-M15-021"' in text
    assert 'InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V8_STABLE_LIFECYCLE"' in text
    assert "InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604121" in text


def test_signal_geometry_sizing_and_order_gateways_are_unchanged():
    old = source(V7)
    new = source(V8)
    for signature in (
        "bool AdvanceSupertrend(",
        "bool BuildEntryGeometry(",
        "bool SelectMarginSafeVolume(",
    ):
        assert function_body(new, signature) == function_body(old, signature)
    assert new.count("OrderSend(request,result)") == 3
    signal = function_body(new, "void ConsumeFlipEvent(")
    for needle in (
        "raw_event=prior_state!=0 && prior_state!=g_st_state",
        "next_time==bar.time+PeriodSeconds(PERIOD_H1)",
        "ClosedM15AtrAtDecision(next_time,decision_m15_shift,atr)",
        "BuildEntryGeometry(direction,atr,probe)",
        "SelectMarginSafeVolume(probe,false)",
    ):
        assert needle in signal
    process = function_body(new, "bool ProcessNewClosedH1Bars(")
    assert "bars[index].time>=DESIGN_START_TIME && bars[index].time<DESIGN_END_TIME" in process
    margin = function_body(new, "MarginSafetyResult EvaluateMarginCandidate(")
    for needle in (
        "required_margin>equity*InpMaxNewPositionMarginPct/100.0",
        "threshold=MathMax(InpMinProjectedMarginLevelPct",
        "reserve=MathMax(remaining_headroom*InpMoneyHeadroomReserveFactor",
        "safe=check.margin_free>=threshold && check.equity-check.margin>=threshold",
    ):
        assert needle in margin


def test_trade_callback_only_schedules_stable_history_replay():
    text = source(V8)
    callback = function_body(text, "void OnTradeTransaction(")
    assert "!ScheduleLifecycleReconcile(transaction.deal)" in callback
    assert 'FailRuntime("lifecycle_queue_allocation_failed")' in callback
    assert "LogLifecycleDeal(" not in callback
    assert "HistoryDealGetDouble" not in callback
    assert "HistoryDealGetInteger" not in callback
    assert "RegisterForcedStopout" not in callback
    assert "request_id" in callback and "transaction.type==TRADE_TRANSACTION_REQUEST" in callback


def test_replay_uses_full_history_and_exact_position_identity():
    text = source(V8)
    owned = function_body(text, "bool ResolvePositionOwnership(")
    volumes = function_body(text, "bool PositionDealVolumesThrough(")
    context = function_body(text, "bool RecoverTelemetryContextFromHistory(")
    for body in (owned, volumes, context):
        assert "HistorySelect(SOURCE_START_TIME,TimeCurrent()+PeriodSeconds(PERIOD_H1))" in body
        assert "HistorySelectByPosition" not in body
        assert "DEAL_POSITION_ID" in body
    assert "owned_open_found" in volumes
    assert "close_volume<=open_volume+1e-8" in volumes
    logger = function_body(text, "bool LogLifecycleDeal(")
    assert logger.index("const double volume=HistoryDealGetDouble") < logger.index("ResolvePositionOwnership(position_id")
    assert logger.index("const datetime deal_time=") < logger.index("ResolvePositionOwnership(position_id")
    assert "HistoryDealGetDouble" not in logger[logger.index("ResolvePositionOwnership(position_id") :]
    assert "STBS_LIFECYCLE_REJECT|stage=%s|deal=%I64u" in text
    assert "STBS_DEAL_FINAL" not in logger


def test_replay_is_retried_before_signal_processing_and_finalized_on_deinit():
    text = source(V8)
    tick = function_body(text, "void OnTick()")
    deinit = function_body(text, "void OnDeinit(")
    assert tick.index("TryLifecycleReconcile()") < tick.index("UpdateRiskAnchors(server_time)")
    assert "REQUEST_VISIBILITY_TIMEOUT_SECONDS" in function_body(text, "bool TryLifecycleReconcile()")
    assert "ReconcileLifecycleHistory()" in function_body(text, "int OnInit()")
    assert "ReconcileLifecycleHistory()" in deinit
    assert "lifecycle_unresolved_tickets" in deinit
    assert "g_lifecycle_positions_opened!=g_lifecycle_positions_final_closed" in deinit
    replay = function_body(text, "bool ReconcileLifecycleHistory()")
    assert "DEAL_TIME_MSC" in replay
    assert "deal_times[prior]==time_msc && deals[prior]>ticket" in replay
    assert "for(int pass=0;pass<2;pass++)" in replay


def test_each_callback_ticket_requires_an_explicit_ack():
    text = source(V8)
    schedule = function_body(text, "bool ScheduleLifecycleReconcile(")
    assert "g_pending_lifecycle_deals[total]=deal" in schedule
    assert "PendingLifecycleDealQueued(deal)" in schedule
    resolver = function_body(text, "bool LifecycleDealResolved(")
    assert "DealAlreadyLogged(deal)" in resolver
    assert "HistoryDealSelect(deal)" in resolver
    assert "ResolvePositionOwnership(position_id,opening_found,owned)" in resolver
    compact = function_body(text, "bool CompactResolvedLifecycleDeals(")
    assert "LifecycleDealResolved(g_pending_lifecycle_deals[read_index],resolved)" in compact
    assert "ArrayResize(g_pending_lifecycle_deals,write_index)" in compact
    retry = function_body(text, "bool TryLifecycleReconcile(")
    assert "ArraySize(g_pending_lifecycle_deals)==0" in retry
    assert 'FailRuntime("lifecycle_history_reconcile_timeout")' in retry


def test_actual_margin_evidence_is_once_per_position_or_failure():
    text = source(V8)
    actual = function_body(text, "MarginSafetyResult EvaluateActualMargin(")
    assert "g_last_actual_margin_logged_position_id!=position_identifier" in actual
    assert "if(!safe || position_identifier==0)" in actual
    assert "STBS_MARGIN_ACTUAL_UNSAFE|position=%I64u" in actual
    assert "g_last_actual_margin_logged_position_id=position_identifier" in actual
    assert "g_actual_margin_safe_positions++" in actual
    assert '\\"actual_margin_safe_positions\\":%I64d' in text


def test_normal_path_journal_is_bounded_and_sidecars_remain_authoritative():
    text = source(V8)
    assert "STBS_DEAL_QUEUED" not in text
    assert "STBS_DEAL_FINAL" not in text
    assert "STBS_ENTRY_REQUEST" not in text
    assert "STBS_CLOSE_REQUEST" not in text
    assert "STBS_CANCEL_REQUEST" not in text
    assert "STBS_MARGIN_CHECK" not in text
    assert "STBS_MARGIN_UNSAFE" in text
    callback = function_body(text, "void OnTradeTransaction(")
    assert "result.retcode!=TRADE_RETCODE_DONE" in callback
    signal = function_body(text, "void ConsumeFlipEvent(")
    assert "required_free=%.8f" in signal
    assert "source=%s|decision=%s" not in signal
    assert "audit=false" not in signal
    assert signal.count("STBS_SIGNAL") == 2
    assert signal.count("if(InpAuditOnly)") == 3


def test_journal_capture_preserves_the_frozen_one_mib_contract():
    alpha = source(ROOT / "02. AlphaFactory/alpha.ps1")
    loop = source(ROOT / "02. AlphaFactory/tools/research_loop_engine.ps1")
    prereg = source(PREREG)
    assert "max_journal_delta_bytes = 1048576L" in alpha
    assert "[int64]$MaxBytes = 1048576" in alpha
    assert "-ne 1048576L" in loop
    assert "Journal raw-byte cap remains exactly `1,048,576`" in prereg


def test_hyp021_cost_and_one_shot_prereg_are_exact():
    cost = json.loads(COST.read_text(encoding="utf-8"))
    assert cost["evidence_tier"] == "RESEARCH_PROXY"
    assert cost["promotion_eligible"] is False
    assert cost["data_fingerprint"] == "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25"
    assert cost["account_fingerprint"] == "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
    assert cost["run_meta_contract"]["hypothesis_id"] == "HYP-STBS-XAUUSD-M15-021"
    assert cost["run_meta_contract"]["magic"] == 5604121
    assert cost["commission_provenance"]["value"] == 4.4
    assert cost["slippage_provenance"]["sample_count"] == 31176
    assert json.loads(CONTRACT.read_text(encoding="utf-8"))["telemetry_profile"] == "lifecycle-v3"
    prereg = PREREG.read_text(encoding="utf-8")
    assert "STBS021-MODEL0-TRAIN-001" in prereg
    assert "Journal raw-byte cap remains exactly `1,048,576`" in prereg
    assert "PF after x1 costs strictly greater than `1.30`" in prereg
    assert "58B6BAD2E3AEA23B9F257A86E813A5341865AEA582ABC8543B76F5E56C61E915" in prereg
