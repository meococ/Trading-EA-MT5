#!/usr/bin/env python3
"""Source-contract regression tests for the post-kill hardened MQL5 kernel."""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "EA_UnicornPrecisionScalper.mq5"
FROZEN_HYP006 = ROOT / "source_snapshots" / "EA_UnicornPrecisionScalper_HYP-006_CB51EB2A.mq5"
ALERT_PRESET = ROOT.parent / "presets" / "ALERT_ONLY_HARDENED.set"
FROZEN_SHA256 = "CB51EB2A72CBD1567452F6EA33983C5EAB4C32506A6E3A1CD1E47DBFF182A7B8"


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    next_function = re.search(r"\n(?:bool|void|double|int|long|ulong|string|datetime)\s+\w+\s*\(", source[start + len(signature) :])
    if next_function is None:
        return source[start:]
    return source[start : start + len(signature) + next_function.start()]


class HardenedKernelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.frozen = FROZEN_HYP006.read_text(encoding="utf-8")

    def test_frozen_model0_source_remains_immutable(self) -> None:
        digest = hashlib.sha256(FROZEN_HYP006.read_bytes()).hexdigest().upper()
        self.assertEqual(digest, FROZEN_SHA256)

    def test_hardened_source_has_explicit_non_economic_identity(self) -> None:
        self.assertIn('ENGINEERING_STATUS="FIDELITY_M15_STRUCTURE_ALERT_ONLY_NO_RUN_AUTHORITY"', self.source)
        self.assertIn("#property version   \"1.24\"", self.source)
        self.assertIn("input long   InpMagic=5600717;", self.source)
        self.assertIn("input bool   InpUseEventAnchoredSweepState=true;", self.source)
        self.assertNotEqual(self.source, self.frozen)

    def test_alert_only_cannot_mutate_trades(self) -> None:
        self.assertIn("input bool   InpAllowRetiredResearchExecution=false;", self.source)
        self.assertIn("bool TradingMutationAllowed()", self.source)
        on_tick = function_body(self.source, "void OnTick()")
        self.assertIn("if(TradingMutationAllowed() && owned!=0)", on_tick)
        self.assertIn("ManageOwnedPosition(owned);", on_tick)
        self.assertNotIn("\n   ManageOwnedPosition(owned);", on_tick)
        self.assertIn("if(!TradingMutationAllowed())", on_tick)
        self.assertIn("if(!RiskGuardsAllow())", on_tick)
        mutation_gate = function_body(self.source, "bool TradingMutationAllowed()")
        self.assertIn("MQLInfoInteger(MQL_TESTER)", mutation_gate)

    def test_restart_waits_for_the_next_new_bar(self) -> None:
        on_init = function_body(self.source, "int OnInit()")
        self.assertIn("g_last_bar=CurrentM5BucketOpen();", on_init)
        self.assertIn("g_new_bar_ready=false;", on_init)

    def test_retired_execution_and_missing_costs_fail_closed(self) -> None:
        self.assertIn("input double InpEstimatedCommissionPerLotRoundTurn=0.0;", self.source)
        self.assertIn("input int    InpEstimatedSlippagePoints=0;", self.source)
        validate = function_body(self.source, "bool ValidateInputs()")
        self.assertIn("InpResearchAutoMode && !InpAllowRetiredResearchExecution", validate)
        self.assertIn("InpEstimatedCommissionPerLotRoundTurn<=0.0", validate)
        self.assertIn("InpEstimatedSlippagePoints<=0", validate)

    def test_risk_size_includes_declared_execution_cost(self) -> None:
        sizing = function_body(self.source, "double RiskSizedVolume(")
        self.assertIn("EstimatedExecutionCostOneLot", sizing)
        self.assertIn("total_loss_one_lot", sizing)
        self.assertIn("normalized_total_loss", sizing)
        self.assertIn("normalized_total_loss>risk_budget_account+0.01", sizing)
        self.assertNotIn("risk_account*1.05", sizing)

    def test_execution_deviation_is_bound_to_the_sized_slippage_budget(self) -> None:
        on_init = function_body(self.source, "int OnInit()")
        preflight = function_body(self.source, "bool PreflightMarketOrder(")
        self.assertIn("SetDeviationInPoints((ulong)MathMax(1,InpEstimatedSlippagePoints))", on_init)
        self.assertIn("request.deviation=(ulong)MathMax(1,InpEstimatedSlippagePoints);", preflight)
        self.assertNotIn("request.deviation=(ulong)MathMax(1,InpMaxSpreadPoints);", preflight)

    def test_actual_fill_reconciles_money_risk_and_arms_overshoot_close(self) -> None:
        capture = function_body(self.source, "bool CaptureInitialRiskFromPosition(")
        self.assertIn("OrderCalcProfit", capture)
        self.assertIn("g_planned_risk_account=actual_risk_account;", capture)
        self.assertIn("g_force_close_risk_overshoot=true;", capture)
        manage = function_body(self.source, "void ManageOwnedPosition(")
        self.assertIn("g_force_close_risk_overshoot", manage)
        self.assertIn("trade.PositionClose(ticket)", manage)
        open_signal = function_body(self.source, "bool OpenFromSignal(")
        self.assertIn("ManageOwnedPosition(owned)", open_signal)

    def test_order_is_preflighted_before_send(self) -> None:
        open_signal = function_body(self.source, "bool OpenFromSignal(")
        self.assertIn("PreflightMarketOrder", open_signal)
        self.assertLess(open_signal.index("PreflightMarketOrder"), open_signal.index("trade.Buy"))
        self.assertIn("OrderCheck(request,check)", self.source)

    def test_daily_trade_limit_counts_unique_entries(self) -> None:
        self.assertIn("int EntryPositionCountSince(", self.source)
        guards = function_body(self.source, "bool RiskGuardsAllow()")
        self.assertIn("EntryPositionCountSince(StartOfDay(TimeCurrent()),day_count_ok)", guards)

    def test_partial_fill_does_not_overwrite_initial_risk_with_zero(self) -> None:
        lifecycle = function_body(self.source, "void LogLifecycleDeal(")
        self.assertIn("if(g_pending_risk_points>0.0 && g_pending_risk_account>0.0)", lifecycle)
        self.assertIn("bool new_position=(g_position_identifier!=position_id);", lifecycle)

    def test_peak_equity_persistence_is_dormant_under_tester_only_authority(self) -> None:
        self.assertIn("input bool   InpPersistPeakEquityAcrossRestarts=true;", self.source)
        authority = function_body(self.source, "bool TradingMutationAllowed()")
        self.assertIn("MQLInfoInteger(MQL_TESTER)", authority)
        persist = function_body(self.source, "void PersistPeakEquityState()")
        self.assertIn("!TradingMutationAllowed()", persist)
        self.assertIn("MQLInfoInteger(MQL_TESTER)", persist)
        self.assertIn("GlobalVariableSet", persist)

    def test_break_even_uses_initial_fill_geometry(self) -> None:
        self.assertIn("double g_initial_risk_distance=0.0;", self.source)
        self.assertIn("bool CaptureInitialRiskFromPosition(", self.source)
        initial = function_body(self.source, "double InitialRiskDistance(")
        self.assertIn("g_initial_risk_position_identifier", initial)
        self.assertIn("g_initial_risk_distance", initial)

    def test_signal_rejections_are_counted_without_per_bar_file_spam(self) -> None:
        self.assertIn("enum SignalRejectReason", self.source)
        self.assertIn("int reject_reason;", self.source)
        self.assertIn("long g_signal_decisions[REJECT_REASON_COUNT];", self.source)
        on_deinit = function_body(self.source, "void OnDeinit(")
        self.assertIn("PrintSignalDecisionSummary();", on_deinit)

    def test_execution_has_explicit_fsm_and_transaction_transitions(self) -> None:
        self.assertIn("enum ExecutionState", self.source)
        self.assertIn("void SetExecutionState(", self.source)
        transaction = function_body(self.source, "void OnTradeTransaction(")
        self.assertIn("EXEC_MANAGING_POSITION", transaction)
        self.assertIn("EXEC_IDLE", transaction)

    def test_ownership_includes_strategy_identity_and_foreign_symbol_guard(self) -> None:
        owned = function_body(self.source, "bool IsOwnedPosition(")
        self.assertIn("POSITION_COMMENT", owned)
        self.assertIn("HYPOTHESIS_ID", owned)
        self.assertIn("bool ForeignSymbolPositionExists(bool &scan_ok)", self.source)
        preflight = function_body(self.source, "bool PreflightMarketOrder(")
        self.assertIn("ForeignSymbolPositionExists(position_scan_ok)", preflight)

    def test_position_and_order_enumeration_errors_fail_closed(self) -> None:
        self.assertIn("bool TryOwnedPositionTicket(ulong &owned_ticket)", self.source)
        positions = function_body(self.source, "bool ForeignSymbolPositionExists(")
        orders = function_body(self.source, "bool ForeignSymbolOrderExists(")
        self.assertIn("bool &scan_ok", positions)
        self.assertIn("bool &scan_ok", orders)
        self.assertIn("return false;", positions)
        self.assertIn("return false;", orders)
        preflight = function_body(self.source, "bool PreflightMarketOrder(")
        self.assertIn("!position_scan_ok", preflight)
        self.assertIn("!order_scan_ok", preflight)

    def test_broker_trade_mode_and_freeze_geometry_fail_closed(self) -> None:
        self.assertIn("bool BrokerTradingAllows(", self.source)
        preflight = function_body(self.source, "bool PreflightMarketOrder(")
        self.assertIn("BrokerTradingAllows(direction)", preflight)
        self.assertIn("bool ModificationGeometryValid(", self.source)
        modification = function_body(self.source, "bool ModificationGeometryValid(")
        self.assertIn("SYMBOL_TRADE_FREEZE_LEVEL", modification)

    def test_emergency_switch_blocks_new_entries_without_forced_flatten(self) -> None:
        self.assertIn("input bool   InpEmergencyBlockNewEntries=false;", self.source)
        guards = function_body(self.source, "bool RiskGuardsAllow()")
        self.assertIn("InpEmergencyBlockNewEntries", guards)

    def test_alert_preset_covers_every_input_and_stays_fail_closed(self) -> None:
        preset_rows = {
            line.split("=", 1)[0]: line.split("=", 1)[1]
            for line in ALERT_PRESET.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#") and "=" in line
        }
        source_inputs = set(re.findall(r"^input\s+\w+\s+(Inp\w+)=", self.source, re.MULTILINE))
        self.assertEqual(set(preset_rows), source_inputs)
        self.assertEqual(preset_rows["InpResearchAutoMode"], "false")
        self.assertEqual(preset_rows["InpAllowRetiredResearchExecution"], "false")
        self.assertEqual(preset_rows["InpUseEventAnchoredSweepState"], "true")

    def test_alert_defaults_do_not_create_empty_lifecycle_logs(self) -> None:
        self.assertIn("input bool   InpEnableTelemetry=false;", self.source)
        preset = ALERT_PRESET.read_text(encoding="utf-8")
        self.assertIn("InpEnableTelemetry=false", preset)

    def test_casebook_is_opt_in_alert_only_and_d_drive_only(self) -> None:
        self.assertIn("input bool   InpEnableAlertCasebook=false;", self.source)
        self.assertIn("input int    InpAlertCasebookMaxRows=200;", self.source)
        validate = function_body(self.source, "bool ValidateInputs()")
        self.assertIn("InpEnableAlertCasebook && TradingMutationAllowed()", validate)
        self.assertIn("AlertCasebookStorageAllowed()", validate)
        storage = function_body(self.source, "bool AlertCasebookStorageAllowed()")
        self.assertIn("TerminalInfoString(TERMINAL_DATA_PATH)", storage)
        self.assertIn('StringFind(data_path,"D:\\\\")', storage)
        self.assertNotIn("FILE_COMMON", self.source)

    def test_casebook_is_bounded_and_contains_no_outcome_fields(self) -> None:
        casebook = function_body(self.source, "bool WriteAlertCasebook(")
        self.assertIn("g_casebook_rows>=InpAlertCasebookMaxRows", casebook)
        self.assertIn("g_casebook_rows++", casebook)
        self.assertIn("ALERT_FIRST_CASEBOOK_V1", self.source)
        header = function_body(self.source, "bool OpenAlertCasebook()")
        for forbidden in ("forward_return", "mfe", "mae", "deal_profit", "pnl"):
            self.assertNotIn(forbidden, header.lower())

    def test_valid_alert_is_logged_before_any_mutation_path(self) -> None:
        on_tick = function_body(self.source, "void OnTick()")
        self.assertIn("WriteAlertCasebook(signal,spread_points)", on_tick)
        self.assertLess(
            on_tick.index("WriteAlertCasebook(signal,spread_points)"),
            on_tick.index("OpenFromSignal(signal)"),
        )

    def test_casebook_sweep_age_matches_frozen_probe_semantics(self) -> None:
        sweep = function_body(self.source, "bool FindRecentSweep(")
        self.assertIn("sweep_age_bars=j-left;", sweep)
        self.assertNotIn("sweep_age_bars=j;", sweep)

    def test_event_sweep_invalidation_covers_all_closed_bars_to_decision(self) -> None:
        sweep = function_body(self.source, "bool FindRecentSweep(")
        self.assertEqual(sweep.count("for(int k=0;k<j;k++)"), 2)
        self.assertNotIn("for(int k=left;k<j;k++)", sweep)

    def test_casebook_has_independent_configuration_provenance(self) -> None:
        self.assertIn('const string CASEBOOK_SOURCE_CONTRACT_ID=', self.source)
        self.assertIn('CASEBOOK_SOURCE_CONTRACT_ID="UPS_ALERT_FIRST_CASEBOOK_V1_4"', self.source)
        self.assertIn('input string InpExpectedSourceSha256="";', self.source)
        self.assertIn("bool WriteAlertCasebookMeta()", self.source)
        casebook_open = function_body(self.source, "bool OpenAlertCasebook()")
        self.assertIn("WriteAlertCasebookMeta()", casebook_open)
        meta = function_body(self.source, "bool WriteAlertCasebookMeta()")
        self.assertIn('"source_sha256"', meta)
        self.assertIn("InpExpectedSourceSha256", meta)
        for field in (
            "TERMINAL_DATA_PATH",
            "TERMINAL_BUILD",
            "ACCOUNT_SERVER",
            "InpServerUtcOffsetHours",
            "InpSweepLookback",
            "InpMinDisplacementAtr",
            "InpMinAutoScore",
        ):
            self.assertIn(field, meta)

    def test_new_bar_gate_fails_closed_on_missing_or_stale_time(self) -> None:
        gate = function_body(self.source, "void RefreshNewM5BarGate()")
        self.assertIn("if(current<=0)", gate)
        self.assertIn("if(current==g_last_bar)", gate)
        self.assertIn("if(current<g_last_bar)", gate)
        self.assertLess(gate.index("if(current<=0)"), gate.index("g_last_bar=current;"))
        self.assertLess(gate.index("if(current<g_last_bar)"), gate.index("g_last_bar=current;"))

    def test_risk_history_queries_fail_closed(self) -> None:
        self.assertIn("int EntryPositionCountSince(const datetime from_time,bool &history_ok)", self.source)
        self.assertIn("double RealizedNetSince(const datetime from_time,bool &history_ok)", self.source)
        self.assertIn("int ConsecutiveLosingPositionsSince(const datetime from_time,bool &history_ok)", self.source)
        guards = function_body(self.source, "bool RiskGuardsAllow()")
        self.assertIn("if(!day_count_ok || !streak_ok || !day_net_ok || !week_net_ok)", guards)
        for signature in (
            "int EntryPositionCountSince(",
            "double RealizedNetSince(",
            "int ConsecutiveLosingPositionsSince(",
        ):
            body = function_body(self.source, signature)
            self.assertIn("if(deal==0)", body)
            self.assertLess(body.index("if(deal==0)"), body.rindex("history_ok=true;"))

    def test_casebook_schema_can_label_breaker_fidelity(self) -> None:
        header = function_body(self.source, "bool OpenAlertCasebook()")
        self.assertIn('"label_true_breaker_valid"', header)

    def test_m15_structure_is_closed_bar_confirmed_and_hard_gated(self) -> None:
        self.assertIn("input int    InpStructurePivotStrength=2;", self.source)
        structure = function_body(self.source, "int ClosedSwingStructureState(")
        self.assertIn("CopyRates(_Symbol,timeframe,1,requested,bars)", structure)
        self.assertIn("IsConfirmedSwing", structure)
        evaluate = function_body(self.source, "SignalPlan EvaluateClosedSignal()")
        self.assertIn("ClosedSwingStructureState(PERIOD_M15,InpStructurePivotStrength)", evaluate)
        self.assertIn("REJECT_M15_STRUCTURE", evaluate)
        self.assertIn("if(m15_structure!=h4_bias)", evaluate)
        header = function_body(self.source, "bool OpenAlertCasebook()")
        self.assertIn('"m15_structure"', header)

    def test_position_mutations_require_completed_trade_retcode(self) -> None:
        self.assertIn("bool TradeResultCompleted(const bool sent)", self.source)
        manage = function_body(self.source, "void ManageOwnedPosition(")
        self.assertIn("TradeResultCompleted(trade.PositionClose(ticket))", manage)
        self.assertIn("TradeResultCompleted(trade.PositionModify(ticket,break_even,target))", manage)

    def test_casebook_records_server_time_and_offset(self) -> None:
        header = function_body(self.source, "bool OpenAlertCasebook()")
        self.assertIn('"decision_time_server"', header)
        self.assertIn('"server_utc_offset_hours"', header)
        writer = function_body(self.source, "bool WriteAlertCasebook(")
        self.assertIn("signal.decision_time_utc+InpServerUtcOffsetHours*3600", writer)

    def test_order_path_rechecks_spread_and_pending_exposure(self) -> None:
        open_signal = function_body(self.source, "bool OpenFromSignal(")
        self.assertIn("(tick.ask-tick.bid)/_Point>InpMaxSpreadPoints", open_signal)
        self.assertIn("bool ForeignSymbolOrderExists(bool &scan_ok)", self.source)
        preflight = function_body(self.source, "bool PreflightMarketOrder(")
        self.assertIn("ForeignSymbolOrderExists(order_scan_ok)", preflight)


if __name__ == "__main__":
    unittest.main()
