from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EA = ROOT / "03. EA Developer" / "EA_JumpClusterDecayReversal" / "EA_JumpClusterDecayReversal.mq5"
PREREG = (
    ROOT
    / "03. EA Developer"
    / "EA_JumpClusterDecayReversal"
    / "research"
    / "HYP-JCDR-EURUSD-M5-005_STAGE_ALIGNMENT_DIAGNOSTIC_PREREG.md"
)


class Jcdr005StageDiagnosticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = EA.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")

    def test_exact_identity_and_analysis_window_are_fail_closed(self) -> None:
        self.assertIn('InpHypothesisId!="HYP-JCDR-EURUSD-M5-005"', self.source)
        self.assertIn('_Symbol!="EURUSD"', self.source)
        self.assertIn('InpExpectedSymbol!="EURUSD"', self.source)
        self.assertIn('InpVariantTag!="JCDR_STAGE_ALIGNMENT_V1"', self.source)
        self.assertIn("_Period!=PERIOD_M5", self.source)
        self.assertIn("_Symbol!=InpExpectedSymbol", self.source)
        self.assertIn('InpAnalysisFrom!="2016.01.04" || InpAnalysisTo!="2020.12.31"', self.source)
        gate = self.source.index("if(bar.time<analysis_from || bar.time>analysis_to)")
        first_ohlc = min(
            self.source.index(f"bar.{field}=i{field.capitalize()}", gate)
            for field in ("open", "high", "low", "close")
        )
        self.assertLess(gate, first_ohlc)

    def test_event_clock_is_unchanged(self) -> None:
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

    def test_no_trade_api_and_no_forming_bar_price_read(self) -> None:
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
        self.assertIn("if(shift<1 || handle==INVALID_HANDLE", self.source)
        self.assertNotRegex(self.source, r"CopyBuffer\([^\n]*,0\s*,")

    def test_every_raw_event_writes_exactly_one_diagnostic_row(self) -> None:
        body = self.source[
            self.source.index("bool ExportDecision") : self.source.index("void ProcessClosedBar")
        ]
        self.assertEqual(body.count("WriteDiagnosticRow("), 1)
        self.assertIn("g_raw_events++", body)
        self.assertIn("g_diagnostic_rows++", body)
        self.assertNotIn("if(!snapshot.routed)", body)
        self.assertNotIn("ROLE_PRIMARY", body)
        self.assertNotIn("INVERSE_CONTROL", body)
        self.assertIn("g_diagnostic_rows==g_raw_events", self.source)

    def test_all_five_indicator_roles_export_continuous_and_temporal_state(self) -> None:
        required = (
            "aird_p_bull", "aird_raw_probability", "aird_aligned_probability", "aird_regime_age",
            "vrc_adx", "vrc_di_plus", "vrc_change_age", "vrc_cluster_alignment",
            "mbb_ker_percentile", "mbb_squeeze_score", "mbb_squeeze_age", "mbb_release_age",
            "qqe_primary_alignment", "qqe_composite_change_age", "qqe_zero_cross_age",
            "tb_structure_event", "tb_structure_age", "tb_sweep_high_age", "tb_displacement_ratio",
            "tb_nearest_liquidity_high", "tb_ready_mask",
        )
        for token in required:
            self.assertIn(token, self.source)
        self.assertIn("LatestFlagAge(g_vrc_handle,24,12", self.source)
        self.assertIn("ConsecutiveFlagAge(g_mbb_handle,23", self.source)
        self.assertIn("StateChangeAge(g_qqe_handle,8", self.source)
        self.assertIn("LatestEventAge(g_tb_handle,27,20", self.source)
        self.assertIn("TB MSS is +/-2", self.source)

    def test_tb_geometry_is_exported_for_both_counterfactual_directions(self) -> None:
        self.assertIn(
            "s.long_stop_level=MathMin(MathMin(g_pending.anchor,g_pending.extreme),s.tb_swing_low)",
            self.source,
        )
        self.assertIn(
            "s.short_stop_level=MathMax(MathMax(g_pending.anchor,g_pending.extreme),s.tb_swing_high)",
            self.source,
        )
        self.assertIn("s.long_corridor_pips=(s.tb_swing_high-decision_close)/pip", self.source)
        self.assertIn("s.short_corridor_pips=(decision_close-s.tb_swing_low)/pip", self.source)
        self.assertIn("long_geometry_pass", self.source)
        self.assertIn("short_geometry_pass", self.source)
        self.assertIn("s.long_geometry_pass=-1; s.short_geometry_pass=-1", self.source)
        self.assertNotIn("primary_sign", self.source)

    def test_read_failures_are_accounted_by_explicit_invalid_mask(self) -> None:
        self.assertIn("const int read_failures_before=g_indicator_read_failures", self.source)
        self.assertIn("if(snapshot.invalid_mask!=0) g_accounted_indicator_read_failures", self.source)
        self.assertIn("g_unaccounted_diagnostic_failures+=read_failure_delta", self.source)
        self.assertIn("g_accounted_indicator_read_failures==g_indicator_read_failures", self.source)
        self.assertIn("g_accounted_tb_contract_mismatches==g_tb_contract_mismatches", self.source)

    def test_runtime_gates_match_frozen_diagnostic_population(self) -> None:
        for token in (
            "g_raw_events>=900",
            "g_diagnostic_rows==g_raw_events",
            "invalid_core_share<=0.05",
            "g_complete_rows>=900",
            "g_tb_both_geometry_rows>=850",
            "max_year_share<=0.30",
        ):
            self.assertIn(token, self.source)

    def test_csv_schema_has_no_route_entry_or_outcome_columns(self) -> None:
        block = self.source[
            self.source.index('string header="record_type') : self.source.index(
                "const uint header_written", self.source.index('string header="record_type')
            )
        ]
        header = "".join(re.findall(r'"([^"]+)"', block)).lower()
        columns = {name.strip() for name in header.split(",")}
        for forbidden in (
            "availability_price", "entry_price", "exit_price", "entry_direction", "direction",
            "route", "arm", "target_hit", "stop_hit", "return", "mfe", "mae", "outcome",
            "pnl", "profit", "balance", "equity", "drawdown", "expectancy",
        ):
            self.assertNotIn(forbidden, columns)
        self.assertIn("decision_close", columns)
        self.assertIn("availability_research_clock", columns)
        self.assertIn("aird_raw_probability_01", columns)
        self.assertIn("aird_vol_percentile_01", columns)
        self.assertIn("aird_p_bull_pct", columns)
        self.assertIn("vrc_vol_percentile_pct", columns)
        self.assertIn("mbb_squeeze_score_pct", columns)
        self.assertIn('\\"post_availability_price_reads\\":0', self.source)
        self.assertIn('\\"outcomes_observed\\":false', self.source)

    def test_csv_header_and_row_have_identical_field_count(self) -> None:
        row_block = self.source[
            self.source.index("bool WriteDiagnosticRow") : self.source.index("bool ExportDecision")
        ]
        row_fields = 1 + len(re.findall(r"CsvAdd(?:String|Int|Double)\(row,", row_block))
        header_block = self.source[
            self.source.index('string header="record_type') : self.source.index(
                "const uint header_written", self.source.index('string header="record_type')
            )
        ]
        header = "".join(re.findall(r'"([^"]+)"', header_block))
        self.assertEqual(row_fields, len(header.split(",")))
        self.assertEqual(row_fields, 114)

    def test_prereg_forbids_edge_and_session_selection(self) -> None:
        self.assertIn("No HYP005 result can claim edge", self.prereg)
        self.assertIn("year and broker-hour strata for representativeness only, never selection", self.prereg)


if __name__ == "__main__":
    unittest.main()
