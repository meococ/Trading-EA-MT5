from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "EA_SupertrendBurstScalper.mq5"
PREREG = ROOT / "research" / "HYP-STBS-XAUUSD-M15-001_ENGINEERING_PREREG.md"


class SupertrendBurstEngineeringContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")

    def test_frozen_identity_is_audit_only_and_cannot_trade(self) -> None:
        self.assertIn('InpHypothesisId!="HYP-STBS-XAUUSD-M15-001"', self.source)
        self.assertIn('InpVariantTag!="STBS_H1_FLIP_M15_BURST_ENGINEERING"', self.source)
        self.assertRegex(self.source, r"!InpAuditOnly\s*\|\|")
        self.assertIn("InpEnableTelemetry     = false;", self.source)
        self.assertIn("!InpAuditOnly || InpEnableTelemetry", self.source)
        self.assertIn("if(InpAuditOnly)\n      return;", self.source)

    def test_parent_supertrend_formula_is_direct_and_unrounded(self) -> None:
        required = [
            "const double next_atr=(9.0*g_st_atr+tr)/10.0;",
            "const double basic_upper=hl2+ST_FACTOR*next_atr;",
            "const double basic_lower=hl2-ST_FACTOR*next_atr;",
            "bar.close>next_upper",
            "bar.close<next_lower",
            "g_supertrend=(g_st_state==STATE_UP) ? g_final_lower : g_final_upper;",
        ]
        for token in required:
            self.assertIn(token, self.source)
        self.assertNotIn("iSuperTrend", self.source)
        self.assertNotIn("iCustom", self.source)
        advance = self.source.split("bool AdvanceSupertrend", 1)[1].split(
            "bool RebuildFrozenSupertrend", 1
        )[0]
        self.assertNotIn("NormalizeDouble", advance)
        self.assertNotIn("epsilon", advance.lower())

    def test_state_rebuild_and_incremental_reads_are_closed_bar_only(self) -> None:
        self.assertIn("CopyRates(_Symbol,PERIOD_H1,1,total_bars-1,history)", self.source)
        self.assertIn("CopyRates(_Symbol,PERIOD_H1,1,prior_shift-1,bars)", self.source)
        self.assertNotRegex(self.source, r"CopyRates\([^\n]+PERIOD_H1\s*,\s*0\s*,")

    def test_exact_next_event_is_consumed_not_queued(self) -> None:
        self.assertIn(
            "next_time==bar.time+PeriodSeconds(PERIOD_H1)", self.source
        )
        self.assertIn("g_gap_events++;", self.source)
        self.assertIn('exact_next=false|consumed=true', self.source)
        self.assertIn(
            "iBarShift(_Symbol,PERIOD_M15,next_time,true)", self.source
        )
        self.assertRegex(
            self.source,
            r"next_time==bar\.time\+PeriodSeconds\(PERIOD_H1\)\s*&&\s*"
            r"decision_m15_shift>=0",
        )
        self.assertIn("CurrentBarOpen(PERIOD_M15)!=next_time", self.source)

    def test_current_bar_gates_and_restart_recovery_are_auditable(self) -> None:
        self.assertIn(
            "SeriesInfoInteger(_Symbol,timeframe,SERIES_LASTBAR_DATE)", self.source
        )
        self.assertNotRegex(self.source, r"iTime\([^\n]+,\s*0\s*\)")
        self.assertIn("seconds-seconds%period_seconds", self.source)
        self.assertIn(
            "iBarShift(_Symbol,PERIOD_M15,candidate,true)>=0 ? candidate : 0",
            self.source,
        )

    def test_m15_atr_is_bound_to_each_exact_decision_and_closed_bar(self) -> None:
        self.assertIn("iATR(_Symbol,PERIOD_M15,M15_ATR_PERIOD)", self.source)
        self.assertRegex(
            self.source,
            r"CopyBuffer\(g_m15_atr_handle\s*,\s*0\s*,\s*1\s*,\s*requested\s*,\s*values\)",
        )
        self.assertIn("const int prior_shift=iBarShift", self.source)
        self.assertIn("if(prior_shift!=decision_shift+1)", self.source)
        self.assertIn("const int requested=prior_shift;", self.source)
        self.assertIn("atr=values[0];", self.source)
        self.assertIn(
            "ClosedM15AtrAtDecision(next_time,decision_m15_shift,atr)", self.source
        )
        self.assertNotRegex(
            self.source,
            r"CopyBuffer\(g_m15_atr_handle\s*,\s*0\s*,\s*0\s*,",
        )

    def test_signal_journal_exposes_parent_comparison_epochs(self) -> None:
        self.assertEqual(self.source.count("source_epoch=%I64d|decision_epoch=%I64d"), 2)
        self.assertIn("(long)ServerToUtc(bar.time)", self.source)
        self.assertIn("(long)ServerToUtc(next_time)", self.source)

    def test_audit_geometry_is_pure_and_reuses_entry_plan(self) -> None:
        self.assertIn("bool BuildEntryPlan", self.source)
        self.assertIn("OrderCalcMargin", self.source)
        self.assertIn("const bool geometry_ready=", self.source)
        self.assertIn("BuildEntryPlan(direction,atr,probe)", self.source)
        self.assertIn("if(!BuildEntryPlan(direction,atr,plan))", self.source)
        audit_slice = self.source.split("const bool geometry_ready=", 1)[1].split(
            "if(InpAuditOnly)", 1
        )[0]
        self.assertNotIn("OrderSend", audit_slice)

    def test_init_failures_are_explicit_and_m15_only(self) -> None:
        self.assertIn('_Symbol!="XAUUSD" || _Period!=PERIOD_M15', self.source)
        self.assertGreaterEqual(self.source.count("g_runtime_failed=true;"), 4)
        self.assertIn("STBS_FATAL|m15_atr_handle_failed", self.source)
        self.assertIn("STBS_FATAL|prehistory_or_state_rebuild_failed", self.source)

    def test_data_quality_series_proof_is_nondecision_and_fail_closed(self) -> None:
        self.assertIn("DATA_EPOCH_D0_SERIES_PROOF", self.source)
        self.assertIn(
            "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)",
            self.source,
        )
        self.assertIn("if(!EmitDataQualitySeriesProof())", self.source)
        self.assertIn("STBS_FATAL|data_quality_series_proof_failed", self.source)
        proof = self.source.split("bool EmitDataQualitySeriesProof", 1)[1].split(
            "bool ValidBar", 1
        )[0]
        for forbidden in ("OrderSend", "BuildEntryPlan", "ConsumeFlipEvent"):
            self.assertNotIn(forbidden, proof)

    def test_frozen_correctness_invocation_preloads_inception(self) -> None:
        self.assertIn("`2005.01.01` through `2023.01.01`, Model `0`", self.prereg)
        self.assertIn("override string contains only `InpAuditOnly=true`", self.prereg)
        self.assertIn("signals remain emitted/scored only inside", self.prereg)

    def test_backlog_and_missing_m15_fixture_contract(self) -> None:
        def event_is_executable(source: int, decision: int, m15_opens: set[int]) -> bool:
            return decision == source + 3600 and decision in m15_opens

        self.assertTrue(event_is_executable(10_000, 13_600, {13_600}))
        self.assertFalse(event_is_executable(10_000, 17_200, {17_200}))
        self.assertFalse(event_is_executable(10_000, 13_600, set()))

        # CopyBuffer(start=1,count=decision_shift+1) is physically oldest-first;
        # values[0] is therefore the ATR at the bar immediately before decision.
        atr_by_shift = {1: 1.1, 2: 2.2, 3: 3.3, 4: 4.4}
        decision_shift = 3
        requested = decision_shift + 1
        physical = [atr_by_shift[s] for s in range(requested, 0, -1)]
        self.assertEqual(physical[0], atr_by_shift[decision_shift + 1])

    def test_stop_target_use_tick_size_and_no_widening_epsilon(self) -> None:
        self.assertIn("SYMBOL_TRADE_TICK_SIZE", self.source)
        self.assertIn("MathFloor(price/tick_size)*tick_size", self.source)
        self.assertIn("MathCeil(price/tick_size)*tick_size", self.source)
        self.assertIn("InpTargetRR*risk_distance", self.source)
        normalizers = self.source.split("double NormalizePriceDown", 1)[1].split(
            "bool LastClosedM15Atr", 1
        )[0]
        self.assertNotIn("1e-", normalizers)

    def test_risk_sizing_floors_volume_and_uses_order_calc_profit(self) -> None:
        self.assertIn("OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit)", self.source)
        self.assertIn("MathFloor((risk_cash/MathAbs(one_lot_profit))/step)*step", self.source)
        self.assertNotIn("MathCeil((risk_cash", self.source)
        self.assertIn("if(volume<minimum)", self.source)

    def test_reverse_requires_synchronous_close_and_confirmed_flat(self) -> None:
        self.assertIn(
            'if(!SubmitClose(owned,"STBS_OPPOSITE_FLIP") || OwnedPositionTicket()!=0)',
            self.source,
        )
        self.assertIn("ForeignSymbolExposureExists()", self.source)
        self.assertIn("request.position=ticket;", self.source)

    def test_time_and_weekend_controls_are_fixed(self) -> None:
        self.assertIn("shift>=InpMaxHoldBars", self.source)
        self.assertIn("InpMaxHoldBars!=8", self.source)
        self.assertIn("parts.day_of_week==0 || parts.day_of_week==6", self.source)
        self.assertIn("InpFridayEntryCutoffUtcMinutes!=18*60", self.source)
        self.assertIn("InpFridayFlattenUtcMinutes!=20*60", self.source)

    def test_no_external_file_or_live_side_channel(self) -> None:
        forbidden = ["FILE_COMMON", "WebRequest", "Socket", "Sleep(", "EventSetTimer"]
        for token in forbidden:
            self.assertNotIn(token, self.source)
        self.assertIn("OnTradeTransaction", self.source)
        self.assertIn("STBS_DEAL|", self.source)

    def test_prereg_keeps_outcomes_and_holdouts_closed(self) -> None:
        self.assertIn("Orders, performance metrics, PnL, PF, returns", self.prereg)
        self.assertIn("Validation: `2023-01-01` through `2024-12-31`, sealed", self.prereg)
        self.assertIn("`fill_observed=false`", self.prereg)


if __name__ == "__main__":
    unittest.main()
