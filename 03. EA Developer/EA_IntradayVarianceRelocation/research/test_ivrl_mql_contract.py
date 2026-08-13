from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_IntradayVarianceRelocation.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
REPORT = ROOT / "research/evidence/HYP-IVRL-XAUUSD-M5-001/IVRL001-SOURCE-001/source_report.json"
PARENT_SOURCE = ROOT.parents[1] / "02. AlphaFactory/runs/EA_IntradayVarianceRelocation/20260811_142221/snapshot/source/EA_IntradayVarianceRelocation.mq5"


class IvrlMqlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SOURCE.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))

    def test_variance_relocation_formula_is_exact(self) -> None:
        for marker in (
            "const int SESSION_ROWS=192;", "const int EARLY_RETURN_COUNT=95;",
            "const int LATE_RETURN_COUNT=96;", "early_squared_sum+=value*value;",
            "late_squared_sum+=value*value;",
            "early_squared_sum/(double)EARLY_RETURN_COUNT",
            "late_squared_sum/(double)LATE_RETURN_COUNT",
            "MathLog(closes[SESSION_ROWS-1]/closes[EARLY_RETURN_COUNT])",
            "today.late_mean_squared_return<=today.early_mean_squared_return",
            "today.late_session_return>0.0 ? 1 : -1",
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
        self.assertIn('EXPECTED_HYPOTHESIS="HYP-IVRL-XAUUSD-M5-002"', self.text)
        self.assertIn('EXPECTED_VARIANT="INTRADAY_VARIANCE_RELOCATION"', self.text)
        self.assertIn("InpMagic!=5604411", self.text)
        self.assertEqual(self.contract["execution_profile"]["timeframe"], "M5")
        self.assertFalse(self.contract["execution_profile"]["promotion_eligible"])
        self.assertTrue(self.report["all_gates_pass"])
        self.assertEqual(self.report["executable_events"], 1196)
        self.assertEqual(self.report["directions"], {"LONG": 607, "SHORT": 589})

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
        for stale in ("today.rho", "today.entropy", "prior20_entropy", "IDEM002"):
            self.assertNotIn(stale, self.text)

    def test_revision_is_identity_only(self) -> None:
        parent = PARENT_SOURCE.read_text(encoding="utf-8")

        def normalized(value: str) -> str:
            return (value
                    .replace("HYP-IVRL-XAUUSD-M5-001", "HYP-IVRL-XAUUSD-M5-REV")
                    .replace("HYP-IVRL-XAUUSD-M5-002", "HYP-IVRL-XAUUSD-M5-REV")
                    .replace("IVRL001", "IVRLREV")
                    .replace("IVRL002", "IVRLREV")
                    .replace("5604410", "56044XX")
                    .replace("5604411", "56044XX"))

        self.assertEqual(normalized(parent), normalized(self.text))


if __name__ == "__main__":
    unittest.main()
