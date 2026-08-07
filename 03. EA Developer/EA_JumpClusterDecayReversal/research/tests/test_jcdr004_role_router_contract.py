from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
# HYP004 is terminal.  Its regression contract must follow the immutable
# AlphaFactory run snapshot after the canonical source advances to HYP005.
EA = (
    ROOT
    / "02. AlphaFactory"
    / "runs"
    / "EA_JumpClusterDecayReversal"
    / "20260807_164858"
    / "snapshot"
    / "source"
    / "EA_JumpClusterDecayReversal.mq5"
)
PREREG = (
    ROOT
    / "03. EA Developer"
    / "EA_JumpClusterDecayReversal"
    / "research"
    / "HYP-JCDR-EURUSD-M5-004_ROLE_AWARE_SOURCE_PREREG.md"
)


class Jcdr004RoleRouterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = EA.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")

    def test_exact_identity_and_fixed_window_are_fail_closed(self) -> None:
        self.assertIn('InpHypothesisId!="HYP-JCDR-EURUSD-M5-004"', self.source)
        self.assertIn("_Period!=PERIOD_M5", self.source)
        self.assertIn("_Symbol!=InpExpectedSymbol", self.source)
        self.assertIn('InpAnalysisFrom!="2016.01.04" || InpAnalysisTo!="2020.12.31"', self.source)
        gate = self.source.index("if(bar.time<analysis_from || bar.time>analysis_to)")
        first_ohlc = min(
            self.source.index(f"bar.{field}=i{field.capitalize()}", gate)
            for field in ("open", "high", "low", "close")
        )
        self.assertLess(gate, first_ohlc)
        self.assertIn("ResetFormation()", self.source[gate:first_ohlc])

    def test_no_trade_api_and_closed_bar_reads_only(self) -> None:
        for token in (
            "#include <Trade/Trade.mqh>",
            "CTrade",
            "OrderSend(",
            ".Buy(",
            ".Sell(",
            "PositionClose(",
            "PositionModify(",
        ):
            self.assertNotIn(token, self.source)
        for fn in ("iOpen", "iHigh", "iLow", "iClose"):
            calls = re.findall(rf"{fn}\([^;]+\);", self.source)
            self.assertTrue(calls, fn)
            self.assertTrue(all(call.rstrip().endswith(",1);") for call in calls), calls)
        reads = re.findall(r"ReadClosedBufferValue\([^;]+\);", self.source)
        self.assertGreaterEqual(len(reads), 20)
        self.assertIn("CopyBuffer(handle,buffer,1,1,data)", self.source)

    def test_event_clock_constants_are_unchanged(self) -> None:
        for token in (
            "JCDR_SCALE_RETURNS       = 48",
            "JCDR_CLUSTER_BARS        = 15",
            "JCDR_MIN_JUMPS           = 3",
            "JCDR_MIN_COHERENCE       = 0.80",
            "JCDR_MIN_DISPLACEMENT_PIP= 4.0",
            "JCDR_JUMP_FLOOR_PIP      = 1.20",
            "JCDR_JUMP_MULTIPLIER     = 3.0",
            "JCDR_DECAY_MAX_BARS      = 10",
            "JCDR_RETRACE_MIN         = 0.25",
            "JCDR_RETRACE_MAX         = 1.00",
        ):
            self.assertIn(token, self.source)

    def test_route_priority_matches_frozen_role_contract(self) -> None:
        body = self.source[
            self.source.index("void BuildRouterSnapshot") : self.source.index("void AddRoutedStop")
        ]
        invalid = body.index("if(s.invalid_mask!=0)")
        squeeze = body.index("if(s.unreleased_squeeze)")
        follow = body.index("if(s.aird_follow && s.qqe_follow && follow_energy)")
        reversal = body.index("else if(!s.vrc_high_or_compression && !s.vrc_disorder)")
        self.assertLess(invalid, squeeze)
        self.assertLess(squeeze, follow)
        self.assertLess(follow, reversal)
        self.assertIn('s.route="FOLLOW_CONTROL"', body)
        self.assertIn('s.route="TRUE_REVERSAL"', body)
        self.assertIn('s.route="ABSTAIN_REGIME_CONFLICT"', body)

    def test_string_bearing_router_snapshot_is_initialized_explicitly(self) -> None:
        body = self.source[
            self.source.index("void BuildRouterSnapshot") : self.source.index("bool aird_read=true")
        ]
        self.assertNotIn("ZeroMemory(s)", body)
        self.assertIn('s.route="ABSTAIN_INVALID"', body)
        for token in (
            "s.aird_valid=EMPTY_VALUE",
            "s.vrc_valid=EMPTY_VALUE",
            "s.mbb_dc_valid=EMPTY_VALUE",
            "s.qqe_primary=EMPTY_VALUE",
            "s.tb_swing_high=EMPTY_VALUE",
            "s.planned_stop_pips=EMPTY_VALUE",
        ):
            self.assertIn(token, body)

    def test_indicators_have_distinct_roles(self) -> None:
        self.assertIn("s.aird_follow=true", self.source)
        self.assertIn("s.qqe_follow=((cluster_sign>0", self.source)
        self.assertIn("s.vrc_high_or_compression=(s.vrc_high_vol==1.0", self.source)
        self.assertIn("s.vrc_disorder=(s.vrc_chop>=61.8 && s.vrc_hurst>0.45)", self.source)
        self.assertIn("s.unreleased_squeeze=(s.mbb_squeeze==1.0 && s.mbb_release!=1.0)", self.source)
        self.assertNotIn("VETO_AIRD_CONTINUATION", self.source)
        self.assertNotIn("VETO_QQE_CONTINUATION", self.source)

    def test_tb_geometry_is_directional_and_causal(self) -> None:
        self.assertIn(
            "MathMin(MathMin(g_pending.anchor,g_pending.extreme),s.tb_swing_low)-JCDR_STOP_BUFFER_PIP*pip",
            self.source,
        )
        self.assertIn(
            "MathMax(MathMax(g_pending.anchor,g_pending.extreme),s.tb_swing_high)+JCDR_STOP_BUFFER_PIP*pip",
            self.source,
        )
        self.assertIn("s.corridor_pips=(s.tb_swing_high-decision_close)/pip", self.source)
        self.assertIn("s.corridor_pips=(decision_close-s.tb_swing_low)/pip", self.source)
        self.assertIn("s.planned_stop_pips<JCDR_MIN_STOP_PIP", self.source)
        self.assertIn("s.corridor_pips<s.planned_stop_pips", self.source)

    def test_only_routed_events_emit_adjacent_matched_rows(self) -> None:
        body = self.source[
            self.source.index("bool ExportDecision") : self.source.index("void ProcessClosedBar")
        ]
        self.assertLess(body.index("if(!snapshot.routed)"), body.index('WriteArmRow(signal_id,"ROLE_PRIMARY"'))
        self.assertIn('WriteArmRow(signal_id,"ROLE_PRIMARY"', body)
        self.assertIn('WriteArmRow(signal_id,"INVERSE_CONTROL"', body)
        self.assertIn("if(!primary_written || !inverse_written)", body)
        self.assertLess(body.index("if(!primary_written || !inverse_written)"), body.index("g_arm_rows+=2"))
        self.assertIn("const bool gate_match=(g_arm_rows==2*g_routed_events)", self.source)

    def test_fixed_window_series_proof_is_exact_and_fail_closed(self) -> None:
        self.assertEqual(self.source.count('PrintFormat("DATA_EPOCH_D0_SERIES_PROOF'), 1)
        self.assertIn("ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE", self.source)
        self.assertIn("ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE", self.source)
        self.assertIn("ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE", self.source)
        self.assertIn("const datetime copytime_from=(datetime)m5_first_epoch", self.source)
        self.assertIn("copytime_first_epoch!=m5_first_epoch", self.source)
        self.assertIn("g_series_proof_ok=EmitDataEpochSeriesProof()", self.source)

    def test_no_trade_proof_excludes_initial_balance_false_positive(self) -> None:
        self.assertIn("HistoryDealsTotal()", self.source)
        self.assertIn("HistoryDealGetTicket(i)", self.source)
        self.assertIn("type==DEAL_TYPE_BUY || type==DEAL_TYPE_SELL", self.source)
        self.assertIn("type==DEAL_TYPE_BALANCE", self.source)
        self.assertIn("trading_deals==0 && other_deals==0", self.source)
        self.assertIn("balance_operations<=1", self.source)
        self.assertIn("HistoryOrdersTotal()", self.source)

    def test_event_level_read_failures_are_accounted_not_silently_ignored(self) -> None:
        self.assertIn("const int read_failures_before=g_indicator_read_failures", self.source)
        self.assertIn("const int tb_mismatches_before=g_tb_contract_mismatches", self.source)
        self.assertIn('snapshot.route=="ABSTAIN_INVALID" && snapshot.invalid_mask!=0', self.source)
        self.assertIn("g_unaccounted_router_failures+=read_failure_delta", self.source)
        self.assertIn("g_unaccounted_router_failures+=tb_mismatch_delta", self.source)
        self.assertIn("g_accounted_indicator_read_failures==g_indicator_read_failures", self.source)
        self.assertIn("g_accounted_tb_contract_mismatches==g_tb_contract_mismatches", self.source)
        self.assertNotIn("g_indicator_read_failures==0 && g_tb_contract_mismatches==0", self.source)

    def test_runtime_gates_match_preregistered_population_thresholds(self) -> None:
        for token in (
            "g_raw_events>=500",
            "g_routed_events>=180",
            "cadence>=0.70 && cadence<=2.00",
            "g_primary_long>=80 && g_primary_short>=80",
            "g_route_reversal>=80 && g_route_follow>=80",
            "max_year_share<=0.30",
            "median_stop>=6.0",
            "median_cost_ratio<=0.25",
        ):
            self.assertIn(token, self.source)

    def test_export_schema_contains_no_outcome_fields(self) -> None:
        start = self.source.index('FileWrite(g_csv_handle,\n      "record_type"')
        end = self.source.index("FileFlush(g_csv_handle);", start)
        header_block = self.source[start:end]
        header = " ".join(re.findall(r'"([^"]+)"', header_block)).lower()
        for forbidden in (
            "availability_price",
            "entry_price",
            "exit_price",
            "target_hit",
            "stop_hit",
            "return",
            "mfe",
            "mae",
            "outcome",
            "pnl",
            "profit",
            "balance",
            "equity",
            "drawdown",
            "expectancy",
        ):
            self.assertNotIn(forbidden, header)
        self.assertIn('\\"post_availability_price_reads\\":0', self.source)
        self.assertIn('\\"performance_metrics_computed\\":0', self.source)

    def test_preregistration_explicitly_forbids_session_selection(self) -> None:
        self.assertIn("No hour/session filter is allowed in HYP-004", self.prereg)


if __name__ == "__main__":
    unittest.main()
