from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_IntradaySerialDependenceSwitch.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
REPORT = ROOT / "research/evidence/HYP-ISDS-XAUUSD-M5-001/ISDS001-SOURCE-001/source_report.json"


class IsdsMqlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SOURCE.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_signal_formula_is_exact(self) -> None:
        for marker in (
            "const int SESSION_ROWS=192;",
            "const int pairs=SESSION_ROWS-2;",
            "covariance+=dx*dy;",
            "const double rho=covariance/denominator;",
            "closes[SESSION_ROWS-1]/closes[SESSION_ROWS-7]",
            "today.rho>0.0 && today.recent_return>0.0",
            "today.rho<0.0 && today.recent_return<0.0",
        ):
            self.assertIn(marker, self.text)

    def test_closed_1555_exact_1600_and_design_only(self) -> None:
        self.assertIn("available.hour!=16 || available.min!=0", self.text)
        self.assertIn("decision.hour!=15 || decision.min!=55", self.text)
        self.assertIn("(long)(availability_time-decision_time)!=300", self.text)
        self.assertIn("if(utc<DESIGN_FROM || utc>=DESIGN_TO)", self.text)
        self.assertRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M5,1,HISTORY_BARS,rates\)")
        self.assertNotRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M5,0,")

    def test_exact_session_and_restart_bar_gate(self) -> None:
        self.assertIn("count!=SESSION_ROWS", self.text)
        self.assertIn("(long)(last_utc-first_utc)!=(SESSION_ROWS-1)*300", self.text)
        self.assertIn("bar.tick_volume>0", self.text)
        self.assertIn("if(!CurrentBarOpen(g_last_bar_open) || g_last_bar_open<=0)", self.text)
        self.assertIn("if(current_open==g_last_bar_open)", self.text.split("void OnTick()", 1)[1])

    def test_d0_preflight_schema_is_present(self) -> None:
        for marker in ("m1_server_first_epoch=", "m1_terminal_first_epoch=", "terminal_maxbars=", "copytime_from_epoch="):
            self.assertIn(marker, self.text)

    def test_risk_and_exit_mapping_is_frozen(self) -> None:
        for marker in (
            "const int STOP_LOOKBACK_BARS=12;", "const double STOP_BUFFER_ATR=0.20;",
            "const double TARGET_R=1.50;", "CopyBuffer(g_atr_handle,0,1,1,value)",
            "InpSessionFlattenHourUtc=20", "InpRiskPercent=0.10", "OrderCalcProfit", "OrderCalcMargin",
        ):
            self.assertIn(marker, self.text)
        self.assertIn(
            "const double tp=(signal.direction>0 ? CeilToTick(raw_target,tick_size) : FloorToTick(raw_target,tick_size));",
            self.text,
        )
        self.assertNotIn(
            "const double tp=(signal.direction>0 ? FloorToTick(raw_target,tick_size) : CeilToTick(raw_target,tick_size));",
            self.text,
        )

    def test_identity_contract_and_source_pass(self) -> None:
        self.assertIn('EXPECTED_HYPOTHESIS="HYP-ISDS-XAUUSD-M5-001"', self.text)
        self.assertIn('EXPECTED_VARIANT="INTRADAY_SERIAL_DEPENDENCE_SWITCH"', self.text)
        self.assertEqual(self.contract["execution_profile"]["timeframe"], "M5")
        self.assertFalse(self.contract["execution_profile"]["promotion_eligible"])
        self.assertTrue(self.report["all_gates_pass"])
        self.assertEqual(self.report["executable_events"], 1275)
        self.assertEqual(self.report["directions"], {"LONG": 626, "SHORT": 649})

    def test_no_current_bar_indicator_reads(self) -> None:
        self.assertNotRegex(self.text, r"CopyBuffer\([^\n]*,0,0,")
        self.assertNotRegex(self.text, r"i(?:Close|Open|High|Low)\([^\n]*,0\)")
        self.assertNotIn("rates[last+1]", self.text)

    def test_source_hash_is_recordable(self) -> None:
        self.assertRegex(hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper(), r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
