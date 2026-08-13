from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_DailyParticipationMomentum.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
RESEARCH = ROOT / "research"
SOURCE_REPORT = (
    RESEARCH
    / "evidence/HYP-DPMO-XAUUSD-M5-001/DPMO-SOURCE-001/source_report.json"
)


class DpmoMqlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SOURCE.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))

    def test_source_gate_is_the_frozen_mapping(self) -> None:
        required = (
            "const int ACTIVITY_LOOKBACK=20;",
            "const int SESSION_ROWS=192;",
            "today.activity>median",
            "today.end_close>today.start_close ? 1 : -1",
            "ArraySort(values);",
            "(values[ACTIVITY_LOOKBACK/2-1]+values[ACTIVITY_LOOKBACK/2])/2.0",
        )
        for marker in required:
            self.assertIn(marker, self.text)

    def test_decision_is_closed_1555_and_exact_1600(self) -> None:
        self.assertIn("available.hour!=16 || available.min!=0", self.text)
        self.assertIn("decision.hour!=15 || decision.min!=55", self.text)
        self.assertIn("(long)(availability_time-decision_time)!=300", self.text)
        self.assertRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M5,1,HISTORY_BARS,rates\)")
        self.assertNotRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M5,0,")

    def test_session_is_exact_and_current_excluded_from_median(self) -> None:
        self.assertIn("count!=SESSION_ROWS", self.text)
        self.assertIn("(long)(last_utc-first_utc)!=(SESSION_ROWS-1)*300", self.text)
        self.assertIn("sessions[current_index-ACTIVITY_LOOKBACK+i].activity", self.text)
        self.assertIn("bar.tick_volume>0", self.text)
        self.assertIn("if(utc<DESIGN_FROM || utc>=DESIGN_TO)", self.text)

    def test_attach_mid_bar_cannot_backfill_the_current_decision(self) -> None:
        self.assertIn(
            "if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)",
            self.text,
        )
        on_tick = self.text.split("void OnTick()", 1)[1]
        self.assertIn("if(current_open==g_last_bar_open)", on_tick)

    def test_d0_series_proof_matches_alphafactory_schema(self) -> None:
        for marker in (
            "m1_server_first_epoch=",
            "m1_terminal_first_epoch=",
            "terminal_maxbars=",
            "copytime_from_epoch=",
        ):
            self.assertIn(marker, self.text)

    def test_execution_mapping_is_frozen(self) -> None:
        for marker in (
            "const int STOP_LOOKBACK_BARS=12;",
            "const double STOP_BUFFER_ATR=0.20;",
            "const double TARGET_R=1.50;",
            "CopyBuffer(g_atr_handle,0,1,1,value)",
            "InpSessionFlattenHourUtc=20",
            "InpRiskPercent=0.10",
            "OrderCalcProfit",
            "OrderCalcMargin",
        ):
            self.assertIn(marker, self.text)
        for forbidden in ("trailing", "break_even", "break-even", "optimization"):
            self.assertNotIn(forbidden, self.text.lower())

    def test_identity_and_contract(self) -> None:
        self.assertIn('EXPECTED_HYPOTHESIS="HYP-DPMO-XAUUSD-M5-001"', self.text)
        self.assertIn('EXPECTED_SYMBOL="XAUUSD"', self.text)
        profile = self.contract["execution_profile"]
        self.assertEqual(profile["timeframe"], "M5")
        self.assertEqual(profile["expected_symbol"], "XAUUSD")
        self.assertTrue(profile["closed_bar_only"])
        self.assertFalse(profile["promotion_eligible"])

    def test_source_evidence_still_passes_without_outcomes(self) -> None:
        self.assertTrue(self.report["all_gates_pass"])
        self.assertFalse(self.report["outcomes_opened"])
        self.assertFalse(self.report["economics_evaluated"])
        self.assertEqual(self.report["executable_events"], 599)
        self.assertAlmostEqual(self.report["cadence_per_week"], 2.2962760131434834)
        self.assertEqual(self.report["directions"], {"LONG": 301, "SHORT": 298})

    def test_no_signal_indicator_reads_from_current_bar(self) -> None:
        self.assertNotRegex(self.text, r"CopyBuffer\([^\n]*,0,0,")
        self.assertNotRegex(self.text, r"i(?:Close|Open|High|Low)\([^\n]*,0\)")
        self.assertNotIn("rates[last+1]", self.text)

    def test_source_hash_is_recordable(self) -> None:
        digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
        self.assertRegex(digest, r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
