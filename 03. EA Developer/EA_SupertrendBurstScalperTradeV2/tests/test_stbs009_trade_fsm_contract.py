from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV2/EA_SupertrendBurstScalperTradeV2.mq5"
TEXT = SOURCE.read_text(encoding="utf-8")


def test_fresh_trade_identity_is_hard_guarded() -> None:
    assert '"HYP-STBS-XAUUSD-M15-009"' in TEXT
    assert '"STBS_H1_FLIP_M15_BURST_TRADE_FSM_V2"' in TEXT
    assert "InpAuditOnly           = false" in TEXT
    assert "InpMagic               = 5604109" in TEXT
    assert "InpEnableTelemetry || InpMagic!=5604109" in TEXT
    assert "InpAuditOnly || InpEnableTelemetry" not in TEXT


def test_design_window_only_emits_or_trades() -> None:
    block = TEXT[TEXT.index("bool ProcessNewClosedH1Bars"):TEXT.index("bool RecoverEntryClock")]
    assert "bars[index].time>=DESIGN_START_TIME" in block
    assert "bars[index].time<DESIGN_END_TIME" in block
    assert "else if(!InpAuditOnly)" not in block
    assert block.count("ConsumeFlipEvent") == 1
    entry_clock = TEXT[TEXT.index("bool EntryClockAllowed"):TEXT.index("bool FlattenRequired")]
    flatten = TEXT[TEXT.index("bool FlattenRequired"):TEXT.index("string PersistentKey")]
    assert "server_time<DESIGN_START_TIME || server_time>=DESIGN_END_TIME" in entry_clock
    assert "server_time<DESIGN_START_TIME || server_time>=DESIGN_END_TIME" in flatten


def test_explicit_fsm_and_reconciliation_exist() -> None:
    for token in ("EXEC_FLAT", "EXEC_ENTRY_PENDING", "EXEC_OPEN", "EXEC_EXIT_PENDING", "EXEC_MANAGE_ONLY"):
        assert token in TEXT
    assert "CountOwnedPositions" in TEXT
    assert "CountOwnedOrders" in TEXT
    assert "ReconcileExecutionState" in TEXT
    assert "PositionMatchesExpectation" in TEXT


def test_request_acceptance_is_not_counted_as_execution() -> None:
    submit = TEXT[TEXT.index("bool SubmitEntry"):TEXT.index("void ConsumeFlipEvent")]
    reconcile = TEXT[TEXT.index("bool ReconcileExecutionState"):TEXT.index("void TryPendingReverse")]
    assert "TRADE_RETCODE_DONE_PARTIAL" in TEXT and "TRADE_RETCODE_PLACED" in TEXT
    assert "g_entries_submitted++" not in submit
    assert "g_entries_submitted++" in reconcile
    assert "g_closes_submitted++" in reconcile


def test_actual_position_protection_is_verified() -> None:
    block = TEXT[TEXT.index("bool PositionMatchesExpectation"):TEXT.index("bool ReconcileExecutionState")]
    for token in ("POSITION_TYPE", "POSITION_VOLUME", "POSITION_PRICE_OPEN", "POSITION_SL", "POSITION_TP"):
        assert token in block
    assert "volume_step*0.5" in block
    assert "tick_size*0.5" in block


def test_risk_and_execution_state_are_persistent() -> None:
    for suffix in ("PEAK", "DAYEQ", "DAYKEY", "ENTRY", "BLOCK", "EXIT", "DIR", "VOL", "SL", "TP", "RDIR", "RATR", "RTIME", "REQ", "ORDHI", "ORDLO", "DEALHI", "DEALLO", "REQTIME"):
        assert f'"{suffix}"' in TEXT
    for token in ("RISKGEN", "EXECGEN", "SnapshotHash", "HASHHI", "HASHLO", "GlobalVariablesFlush", "NewerUncommittedSnapshotExists", "ValidUlongPart"):
        assert token in TEXT
    assert "AnyOwnedHistoryExists" in TEXT
    assert "risk_anchor_missing_or_corrupt" in TEXT


def test_exit_retry_friday_weekend_and_runtime_management() -> None:
    assert "parts.day_of_week==0 || parts.day_of_week==6" in TEXT
    assert "SubmitCancelOrder" in TEXT
    assert "ManageLifecycle(server_time);" in TEXT
    assert TEXT.index("ManageLifecycle(server_time);") < TEXT.index("if(g_runtime_failed)\n      return;", TEXT.index("void OnTick"))
    assert "ExpertRemove" not in TEXT


def test_flat_lifecycle_fast_path_is_periodic_and_fail_closed() -> None:
    gate = TEXT[TEXT.index("bool LifecycleRequiresTick"):TEXT.index("int OnInit")]
    for token in (
        "new_m15_bar",
        "g_exec_state!=EXEC_FLAT",
        "g_exit_intent!=EXIT_NONE",
        "g_expected_direction!=0",
        "g_reverse_direction!=0",
        "g_pending_request_id!=0",
        "g_pending_order_id!=0",
        "g_pending_deal_id!=0",
        "g_request_started!=0",
        "g_runtime_failed",
    ):
        assert token in gate
    on_tick = TEXT[TEXT.index("void OnTick"):TEXT.index("void OnTradeTransaction")]
    assert "full_lifecycle=LifecycleRequiresTick(new_m15_bar)" in on_tick
    assert "if(!full_lifecycle)" in on_tick
    assert "OwnedExposureExists(owned_exposure)" in on_tick
    assert "idle_inventory_enumeration_failed" in on_tick
    assert "else if(owned_exposure)" in on_tick
    assert "if(full_lifecycle)" in on_tick
    assert "ManageLifecycle(server_time);" in on_tick
    assert on_tick.index("g_current_m15_open=m15_open") < on_tick.index("LifecycleRequiresTick")
    regression = on_tick[on_tick.index("if(m15_open<g_current_m15_open)"):on_tick.index("g_current_m15_open=m15_open")]
    assert regression.index('FailRuntime("m15_time_regressed")') < regression.index("ManageLifecycle(server_time)")


def test_execution_snapshot_writes_only_changed_payloads() -> None:
    persist = TEXT[TEXT.index("bool PersistExecutionIntent"):TEXT.index("bool LoadExecutionIntent")]
    load = TEXT[TEXT.index("bool LoadExecutionIntent"):TEXT.index("void ClearEntryExpectation")]
    assert "ExecutionSnapshotPayload(\n      0," in persist
    assert "const string payload=ExecutionSnapshotPayload(" in persist
    assert "g_execution_payload_ready && payload==g_execution_payload_cache" in persist
    assert persist.index("g_execution_payload_ready &&") < persist.index("const long generation=")
    assert persist.index("g_execution_generation=generation") < persist.index("g_execution_payload_cache=payload")
    assert "g_execution_payload_ready=true" in persist
    assert "ExecutionSnapshotPayload(\n      0," in load
    assert load.index("g_execution_generation=generation") < load.index("g_execution_payload_ready=true")


def test_position_plus_order_is_cancelled_before_close_retry() -> None:
    manage = TEXT[TEXT.index("void ManageLifecycle"):TEXT.index("void FailRuntime")]
    assert "orders>0 && (positions>0 || g_exit_intent!=EXIT_NONE)" in manage
    assert manage.index("SubmitCancelOrder(order_ticket)") < manage.index("SubmitClose(ticket")
    assert "if(positions>0)" in manage


def test_pending_entry_is_cancelled_at_weekend_or_design_end() -> None:
    manage = TEXT[TEXT.index("void ManageLifecycle"):TEXT.index("void FailRuntime")]
    assert "FlattenRequired(server_time) && (positions>0 || orders>0)" in manage
    assert "SetExitIntent(EXIT_FRIDAY_WEEKEND)" in manage


def test_corrupt_intent_with_exposure_enters_manage_only() -> None:
    on_init = TEXT[TEXT.index("int OnInit()"):TEXT.index("void OnDeinit")]
    assert on_init.index("if(!OwnedExposureExists(owned_exposure))") < on_init.index("if(!LoadExecutionIntent())")
    corrupt = on_init[on_init.index("if(!LoadExecutionIntent())"):on_init.index("if(!LoadOrInitializeRiskAnchors")]
    assert "if(owned_exposure)" in corrupt
    assert "g_exec_state=EXEC_MANAGE_ONLY" in corrupt
    assert "SetExitIntent(EXIT_RUNTIME_FAULT)" in corrupt
    assert "return INIT_SUCCEEDED" in corrupt


def test_trade_transactions_reconcile_all_event_types() -> None:
    block = TEXT[TEXT.index("void OnTradeTransaction"):TEXT.index("double OnTester")]
    request_branch = block[:block.index("if(transaction.type==TRADE_TRANSACTION_DEAL_ADD")]
    deal_branch = block[block.index("if(transaction.type==TRADE_TRANSACTION_DEAL_ADD"):]
    assert "TRADE_TRANSACTION_REQUEST" in request_branch
    assert "result.request_id" in request_branch and "result.retcode" in request_branch
    assert "result.request_id" not in deal_branch and "result.retcode" not in deal_branch
    assert "request_retcode" not in deal_branch
    assert "ReconcileExecutionState();" in block
    assert "TRADE_TRANSACTION_DEAL_ADD" in block


def test_time_exit_boundary_is_eight_completed_bars() -> None:
    manage = TEXT[TEXT.index("void ManageLifecycle"):TEXT.index("void FailRuntime")]
    assert "const int entry_shift=" in manage
    assert "if(entry_shift<0)" in manage
    assert "SetExitIntent(EXIT_ENTRY_CLOCK_UNKNOWN)" in manage
    assert "else if(entry_shift>=InpMaxHoldBars)" in manage
    assert "SetExitIntent(EXIT_TIME)" in manage
    assert "InpMaxHoldBars         = 8" in TEXT


def test_enumeration_and_trade_checks_fail_closed() -> None:
    positions = TEXT[TEXT.index("bool CountOwnedPositions"):TEXT.index("bool CountOwnedOrders")]
    orders = TEXT[TEXT.index("bool CountOwnedOrders"):TEXT.index("bool OwnedExposureExists")]
    assert "return false;" in positions and "return false;" in orders
    assert "ResetLastError();" in positions and "GetLastError()!=0" in positions
    assert "ResetLastError();" in orders and "GetLastError()!=0" in orders
    assert "if(!OrderCheck(request,check) || !CheckApproved(check))" in TEXT
    approved = TEXT[TEXT.index("bool CheckApproved"):TEXT.index("bool SubmitCancelOrder")]
    accepted = TEXT[TEXT.index("bool RequestAcceptedForTracking"):TEXT.index("bool CheckApproved")]
    assert "check.retcode==0" in approved
    assert "TRADE_RETCODE_DONE" not in approved
    assert "TRADE_RETCODE_DONE" in accepted
    assert "TRADE_RETCODE_DONE_PARTIAL" in accepted
    assert "TRADE_RETCODE_PLACED" in accepted


def test_trade_child_is_tester_only_and_not_optimization() -> None:
    on_init = TEXT[TEXT.index("int OnInit()"):TEXT.index("void OnDeinit")]
    assert "!MQLInfoInteger(MQL_TESTER)" in on_init
    assert "MQLInfoInteger(MQL_OPTIMIZATION)" in on_init


def test_audit_mode_is_no_send_but_uses_same_signal_and_geometry_path() -> None:
    signal = TEXT[TEXT.index("void ConsumeFlipEvent"):TEXT.index("bool ProcessNewClosedH1Bars")]
    assert signal.index("BuildEntryPlan(direction,atr,probe)") < signal.index("if(InpAuditOnly)")
    assert signal.index("if(InpAuditOnly)") < signal.index("SubmitEntry(direction,atr,next_time)")
    assert signal.count("ConsumeFlipEvent") == 1
    for start, end, reason in (
        ("bool SubmitCancelOrder", "bool SubmitClose", "audit_cancel_gateway_forbidden"),
        ("bool SubmitClose", "int VolumeDigits", "audit_close_gateway_forbidden"),
        ("bool SubmitEntry", "void ConsumeFlipEvent", "audit_entry_gateway_forbidden"),
    ):
        gateway = TEXT[TEXT.index(start):TEXT.index(end)]
        assert "if(InpAuditOnly)" in gateway
        assert reason in gateway
        assert gateway.index("if(InpAuditOnly)") < gateway.index("OrderSend(request,result)")
    assert TEXT.count("OrderSend(request,result)") == 3


def test_transient_flat_request_cannot_reenter() -> None:
    reconcile = TEXT[TEXT.index("bool ReconcileExecutionState"):TEXT.index("void TryPendingReverse")]
    assert "g_exec_state==EXEC_ENTRY_PENDING" in reconcile
    assert "REQUEST_VISIBILITY_TIMEOUT_SECONDS" in reconcile
    assert "g_transient_flat_ticks++" in reconcile
    assert reconcile.index("g_exec_state==EXEC_ENTRY_PENDING") < reconcile.index("ClearEntryExpectation()")


def test_same_tick_exit_barrier_is_persisted_and_blocks_entry() -> None:
    exit_block = TEXT[TEXT.index("bool SetExitIntent"):TEXT.index("ENUM_ORDER_TYPE_FILLING FillingMode")]
    signal = TEXT[TEXT.index("void ConsumeFlipEvent"):TEXT.index("bool ProcessNewClosedH1Bars")]
    reverse = TEXT[TEXT.index("void TryPendingReverse"):TEXT.index("void ManageLifecycle")]
    assert "intent!=EXIT_OPPOSITE_FLIP" in exit_block
    assert "g_entry_block_until" in exit_block
    assert "next_time<g_entry_block_until" in signal
    assert "g_reverse_decision<g_entry_block_until" in reverse
    assert "g_runtime_failed ||" in reverse


def test_close_then_reverse_is_persisted_and_same_bar_bounded() -> None:
    assert "g_reverse_direction=direction" in TEXT
    assert "SetExitIntent(EXIT_OPPOSITE_FLIP)" in TEXT
    reverse = TEXT[TEXT.index("void TryPendingReverse"):TEXT.index("void ManageLifecycle")]
    assert "CurrentBarOpen(PERIOD_M15)!=g_reverse_decision" in reverse
    assert "SubmitEntry(direction,atr,decision)" in reverse
