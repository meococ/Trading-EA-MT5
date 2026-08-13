from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_IntradayEntropyMomentum.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
REPORT = ROOT / "research/evidence/HYP-IDEM-XAUUSD-M5-001/IDEM001-SOURCE-001/source_report.json"


class IdemMqlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SOURCE.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_entropy_formula_and_reference_are_exact(self) -> None:
        for marker in (
            "const int SESSION_ROWS=192;", "const int REFERENCE_DAYS=20;",
            "if(value>0.0) positive++;", "else if(value<0.0) negative++;",
            "entropy=-p*MathLog(p)-(1.0-p)*MathLog(1.0-p);",
            "sessions[current-REFERENCE_DAYS+i].entropy",
            "today.entropy>=reference_entropy", "today.session_return>0.0 ? 1 : -1",
        ):
            self.assertIn(marker, self.text)

    def test_closed_bar_exact_next_and_design_only(self) -> None:
        self.assertIn("available.hour!=16 || available.min!=0", self.text)
        self.assertIn("decision.hour!=15 || decision.min!=55", self.text)
        self.assertIn("(long)(availability_time-decision_time)!=300", self.text)
        self.assertRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M5,1,HISTORY_BARS,rates\)")
        self.assertNotRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M5,0,")

    def test_risk_target_and_skip_counter_are_frozen(self) -> None:
        for marker in (
            "const int STOP_LOOKBACK_BARS=12;", "const double STOP_BUFFER_ATR=0.20;",
            "const double TARGET_R=1.50;", "CopyBuffer(g_atr_handle,0,1,1,value)",
            "CeilToTick(raw_target,tick_size) : FloorToTick(raw_target,tick_size)",
            "g_risk_lock_skips++;", "risk_lock_skips=%I64d",
        ):
            self.assertIn(marker, self.text)

    def test_identity_and_source_pass(self) -> None:
        self.assertIn('EXPECTED_HYPOTHESIS="HYP-IDEM-XAUUSD-M5-002"', self.text)
        self.assertIn('EXPECTED_VARIANT="INTRADAY_ENTROPY_MOMENTUM"', self.text)
        self.assertIn("InpMagic!=5604406", self.text)
        self.assertEqual(self.contract["execution_profile"]["timeframe"], "M5")
        self.assertFalse(self.contract["execution_profile"]["promotion_eligible"])
        self.assertTrue(self.report["all_gates_pass"])
        self.assertEqual(self.report["executable_events"], 638)
        self.assertEqual(self.report["directions"], {"LONG": 344, "SHORT": 294})

    def test_d0_and_summary_schema_are_present(self) -> None:
        for marker in (
            "m1_server_first_epoch=", "terminal_maxbars=", "copytime_from_epoch=",
            "runtime_failed=%s", "close_attempts=%I64d", "close_rejects=%I64d",
        ):
            self.assertIn(marker, self.text)

    def test_required_flatten_retry_is_rate_limited_per_native_bar(self) -> None:
        for marker in (
            "datetime g_last_close_attempt_bar=0;",
            "if(g_last_close_attempt_bar==current_open)",
            "g_last_close_attempt_bar=current_open;",
            "g_close_attempts++;",
            "g_close_rejects++;",
        ):
            self.assertIn(marker, self.text)
        self.assertLess(
            self.text.index("if(g_last_close_attempt_bar==current_open)"),
            self.text.index('CloseOwned("UTC_2000_OR_DAY_ROLL")'),
        )

    def test_no_current_bar_or_stale_isds_fields(self) -> None:
        self.assertNotRegex(self.text, r"CopyBuffer\([^\n]*,0,0,")
        self.assertNotRegex(self.text, r"i(?:Close|Open|High|Low)\([^\n]*,0\)")
        for stale in ("today.rho", "recent_return", "ISDS001"):
            self.assertNotIn(stale, self.text)


if __name__ == "__main__":
    unittest.main()
