from pathlib import Path
import re
import unittest


SOURCE = Path(__file__).parents[1] / "EA_WickReject_XAU_M15_V1.mq5"


class CbwrMqlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")

    def test_closed_bar_copy_starts_at_shift_one(self):
        self.assertRegex(self.text, r"CopyRates\(_Symbol,PERIOD_M15,1,required,rates\)")
        self.assertRegex(self.text, r"CopyBuffer\(g_atr_handle,0,1,needed,values\)")

    def test_swing_excludes_signal_bar(self):
        self.assertIn("for(int i=1;i<=InpSwingBars;i++)", self.text)
        self.assertIn("const MqlRates bar=rates[0];", self.text)

    def test_entry_is_new_bar_gated(self):
        self.assertIn("if(current_bar_open==g_last_bar_open)", self.text)
        self.assertIn("BuildSignal(current_bar_open,signal)", self.text)

    def test_no_future_or_live_bar_price_reads(self):
        banned = ["CopyRates(_Symbol,PERIOD_M15,0", "CopyBuffer(g_atr_handle,0,0"]
        for token in banned:
            self.assertNotIn(token, self.text)

    def test_no_grid_or_martingale_primitives(self):
        lowered = self.text.lower()
        for token in ["martingale", "gridstep", "positionclosepartial"]:
            self.assertNotIn(token, lowered)

    def test_primary_and_control_are_exactly_bound(self):
        self.assertIn("SWING8_PRIMARY", self.text)
        self.assertIn("NO_SWING_CONTROL", self.text)
        self.assertIn("InpRequireSwing && !touches_swing", self.text)

    def test_time_and_flat_exits_exist(self):
        for token in ["TIME_STOP", "DAILY_FLAT", "FRIDAY_FLAT"]:
            self.assertIn(token, self.text)

    def test_frozen_identity(self):
        self.assertGreaterEqual(len(re.findall(r'HYP-CBWR-XAUUSD-M15-003', self.text)), 2)
        self.assertIn('const string EXPECTED_HYPOTHESIS="HYP-CBWR-XAUUSD-M15-003";', self.text)


if __name__ == "__main__":
    unittest.main()
