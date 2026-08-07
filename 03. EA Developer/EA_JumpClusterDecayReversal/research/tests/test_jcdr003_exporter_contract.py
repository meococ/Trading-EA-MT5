from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
# HYP-003 is terminal and the canonical source now advances to HYP-004.  Keep
# this regression contract bound to the immutable source snapshot of the one
# HYP-003 run so successor work cannot rewrite its historical evidence.
EA = (
    ROOT
    / "02. AlphaFactory"
    / "runs"
    / "EA_JumpClusterDecayReversal"
    / "20260807_140336"
    / "snapshot"
    / "source"
    / "EA_JumpClusterDecayReversal.mq5"
)
PLAN = (
    ROOT
    / "03. EA Developer"
    / "EA_JumpClusterDecayReversal"
    / "research"
    / "HYP-JCDR-EURUSD-M5-003_INDICATOR_ROUTING_FEASIBILITY_PLAN.md"
)


class Jcdr003ExporterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = EA.read_text(encoding="utf-8")
        cls.plan = PLAN.read_text(encoding="utf-8")

    def test_exact_identity_is_fail_closed(self) -> None:
        self.assertIn('InpHypothesisId!="HYP-JCDR-EURUSD-M5-003"', self.source)
        self.assertIn("_Period!=PERIOD_M5", self.source)
        self.assertIn("_Symbol!=InpExpectedSymbol", self.source)

    def test_frozen_analysis_window_is_fail_closed_inside_wider_tester_envelope(self) -> None:
        self.assertIn('InpAnalysisFrom    = "2016.01.04"', self.source)
        self.assertIn('InpAnalysisTo      = "2020.12.31"', self.source)
        self.assertIn('InpAnalysisFrom!="2016.01.04" || InpAnalysisTo!="2020.12.31"', self.source)
        gate = self.source.index("if(bar.time<analysis_from || bar.time>analysis_to)")
        first_ohlc = min(self.source.index(f"bar.{field}=i{field.capitalize()}", gate) for field in ("open", "high", "low", "close"))
        self.assertLess(gate, first_ohlc)
        window_body = self.source[gate:first_ohlc]
        self.assertIn("ResetFormation()", window_body)
        self.assertIn("g_last_processed_time=0", window_body)

    def test_no_trade_entry_api_exists(self) -> None:
        forbidden = (
            "#include <Trade/Trade.mqh>",
            "CTrade",
            "OrderSend(",
            ".Buy(",
            ".Sell(",
            "PositionClose(",
            "PositionModify(",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)

    def test_price_ohlc_reads_are_closed_bar_only(self) -> None:
        for fn in ("iOpen", "iHigh", "iLow", "iClose"):
            calls = re.findall(rf"{fn}\([^;]+\);", self.source)
            self.assertTrue(calls, fn)
            self.assertTrue(all(call.rstrip().endswith(",1);") for call in calls), calls)

    def test_indicator_reads_are_shift_one(self) -> None:
        calls = re.findall(r"ReadBufferValue\([^;]+\);", self.source)
        self.assertGreaterEqual(len(calls), 20)
        self.assertTrue(all(re.search(r",1,[^)]+\);$", call) for call in calls), calls)

    def test_all_five_default_only_paths_are_frozen(self) -> None:
        names = (
            "AI_Regime_Detection",
            "Volatility_Regime_Classifier_QuantRegime",
            "Modern_Bollinger_Bands_GBB",
            "QQE_MOD",
            "TB_Smart_Money_Concept_2026",
        )
        for name in names:
            self.assertIn(f'"AlphaFactory\\\\{name}"', self.source)

    def test_jcdr_constants_match_preregistration(self) -> None:
        expected = (
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
        )
        for token in expected:
            self.assertIn(token, self.source)

    def test_prior_scale_bootstraps_from_all_usable_returns(self) -> None:
        start = self.source.index("bool PriorMedianAbs48")
        end = self.source.index("bool TryFormCluster", start)
        body = self.source[start:end]
        self.assertIn("if(!IsUsable(g_bars[i].ret_pips))", body)
        self.assertNotIn("!g_bars[i].jump_class_valid ||", body)
        process = self.source[self.source.index("void ProcessClosedBar"):]
        self.assertLess(process.index("PriorMedianAbs48(scale)"), process.index("AppendBar(bar)"))

    def test_cost_gate_uses_median_of_event_ratios(self) -> None:
        self.assertIn("g_pass_cost_ratios[m]=JCDR_COST_GEOMETRY_PIP/stop_pips", self.source)
        self.assertIn("const double median_cost_ratio=MedianArray(g_pass_cost_ratios)", self.source)

    def test_telemetry_integrity_is_fail_closed(self) -> None:
        self.assertIn("const uint written=FileWrite(g_csv_handle", self.source)
        self.assertIn("if(written==0)", self.source)
        self.assertIn("const uint header_written=FileWrite(g_csv_handle", self.source)
        self.assertIn("if(header_written==0)", self.source)
        self.assertIn("g_telemetry_fatal=true", self.source)
        self.assertIn("gate_telemetry=(!g_telemetry_fatal && g_telemetry_write_failures==0)", self.source)
        self.assertIn("gate_no_trade && gate_telemetry", self.source)
        self.assertIn("const uint meta_written=FileWriteString(meta,payload)", self.source)
        self.assertIn("meta_written<(uint)StringLen(payload)", self.source)

    def test_event_counters_commit_only_after_both_arm_rows(self) -> None:
        export = self.source[self.source.index("bool ExportDecision"):self.source.index("void ProcessClosedBar")]
        both_written = export.index("if(!true_written || !follow_written)")
        raw_commit = export.index("g_raw_events++")
        arm_commit = export.index("g_arm_rows+=2")
        self.assertLess(both_written, raw_commit)
        self.assertLess(both_written, arm_commit)
        write_arm = self.source[self.source.index("bool WriteArmRow"):self.source.index("bool ExportDecision")]
        self.assertNotIn("g_arm_rows++", write_arm)
        self.assertNotIn("g_router_pass_arm_rows++", write_arm)

    def test_zero_trade_proof_includes_history_orders_and_selection_status(self) -> None:
        self.assertIn("const bool history_selected=HistorySelect(0,TimeCurrent())", self.source)
        self.assertIn("HistoryDealsTotal()", self.source)
        self.assertIn("HistoryOrdersTotal()", self.source)
        self.assertIn("OrdersTotal()", self.source)
        self.assertIn("PositionsTotal()", self.source)
        self.assertIn("history_selected && deals==0 && historical_orders==0", self.source)

    def test_runtime_proves_complete_frozen_window_traversal(self) -> None:
        self.assertIn("g_seen_pre_window=true", self.source)
        self.assertIn("g_seen_post_window=true", self.source)
        self.assertIn("first_analysis_date==20160104", self.source)
        self.assertIn("last_analysis_date==20201231", self.source)
        self.assertIn("bar.time==analysis_from", self.source)
        self.assertIn("bar.time==analysis_to", self.source)
        self.assertIn("g_seen_exact_first_bar && g_seen_exact_last_bar", self.source)
        self.assertIn("const bool gate_coverage=", self.source)
        self.assertIn("gate_no_trade && gate_telemetry && gate_coverage", self.source)

    def test_runtime_summary_format_placeholder_count_matches_arguments(self) -> None:
        start = self.source.index("const string payload=StringFormat(")
        end = self.source.index("\n\n   int meta=", start)
        block = self.source[start:end]
        literal = re.search(r'StringFormat\(\s*"((?:\\.|[^"\\])*)"\s*,', block, re.S)
        self.assertIsNotNone(literal)
        placeholders = re.findall(r"%(?:I64d|[-+0-9.#]*[dfs])", literal.group(1))

        args_text = block[literal.end():].rstrip()
        self.assertTrue(args_text.endswith("));"), args_text[-40:])
        args_text = args_text[:-3]
        args: list[str] = []
        depth = 0
        quoted = False
        escaped = False
        token: list[str] = []
        for char in args_text:
            if quoted:
                token.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
                token.append(char)
            elif char == "(":
                depth += 1
                token.append(char)
            elif char == ")":
                depth -= 1
                token.append(char)
            elif char == "," and depth == 0:
                args.append("".join(token).strip())
                token = []
            else:
                token.append(char)
        args.append("".join(token).strip())
        self.assertTrue(all(args))
        self.assertEqual(len(placeholders), len(args), (len(placeholders), len(args)))

    def test_aird_uses_pane_level_and_event_cluster_sign(self) -> None:
        self.assertIn("s.aird_confidence>=80.0", self.source)
        self.assertIn("const int continuation_regime=(cluster_sign>0 ? 0 : 1)", self.source)

    def test_qqe_is_event_level_not_arm_direction(self) -> None:
        self.assertIn("cluster_sign>0 && s.qqe_composite==1.0", self.source)
        self.assertIn("cluster_sign<0 && s.qqe_composite==-1.0", self.source)
        self.assertNotRegex(self.source, r"BuildRouterSnapshot\([^,]+direction")

    def test_tb_distance_is_shared_before_arm_export(self) -> None:
        snapshot_pos = self.source.index("BuildRouterSnapshot(g_pending.dominant_sign")
        true_arm_pos = self.source.index('WriteArmRow(signal_id,"TRUE_REVERSAL"')
        follow_arm_pos = self.source.index('WriteArmRow(signal_id,"FOLLOW_CONTROL"')
        self.assertLess(snapshot_pos, true_arm_pos)
        self.assertLess(snapshot_pos, follow_arm_pos)
        self.assertIn("MathMax(s.base_stop_pips,s.tb_envelope_pips)", self.source)

    def test_export_schema_has_no_outcome_fields(self) -> None:
        header_start = self.source.index('FileWrite(g_csv_handle,\n      "record_type"')
        header_end = self.source.index("FileFlush(g_csv_handle);", header_start)
        header = self.source[header_start:header_end].lower()
        for forbidden in ("pnl", "profit", "mfe", "mae", "exit_price", "outcome", "balance", "equity"):
            self.assertNotIn(forbidden, header)

    def test_plan_declares_new_native_surface_not_parent_identity(self) -> None:
        self.assertIn("fresh data/construction surface", self.plan)
        self.assertIn("not an event-identity replay", self.plan)


if __name__ == "__main__":
    unittest.main()
