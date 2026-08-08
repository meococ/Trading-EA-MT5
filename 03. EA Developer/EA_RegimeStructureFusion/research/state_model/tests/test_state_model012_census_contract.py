from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[5]
CENSUS = ROOT / "03. EA Developer" / "EA_RegimeStructureFusionStateCensus" / "EA_RegimeStructureFusionStateCensus.mq5"
BASE = ROOT / "03. EA Developer" / "EA_RegimeStructureFusion" / "EA_RegimeStructureFusion.mq5"


class StateModel012CensusContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper = CENSUS.read_text(encoding="utf-8")
        cls.base = BASE.read_text(encoding="utf-8")

    def test_discovery_window_is_hard_bounded(self):
        self.assertIn("source_time<InpCensusFrom || source_time>InpCensusTo", self.wrapper)
        self.assertIn("InpCensusTo<=InpCensusFrom", self.wrapper)

    def test_export_runs_only_after_closed_bar_counter_advances(self):
        self.assertIn("long before=g_closed_bars_seen;", self.wrapper)
        self.assertIn("if(g_closed_bars_seen>before) ExportCensusClosedBar();", self.wrapper)
        self.assertIn("datetime source_time=iTime(_Symbol,PERIOD_M5,1);", self.wrapper)

    def test_all_five_indicator_families_are_exported(self):
        for token in (
            '"aird_regime"', '"vrc_regime"', '"mbb_upper"',
            '"tb_bias"', '"qqe_primary"'
        ):
            self.assertIn(token, self.wrapper)

    def test_census_has_no_future_label_columns(self):
        header = self.wrapper.split("bool OpenCensus()", 1)[1].split("void ExportCensusClosedBar()", 1)[0]
        for forbidden in ("future_return", "future_high", "future_low", "label", "target_return"):
            self.assertNotIn(forbidden, header.lower())

    def test_batch_flush_is_bounded_and_final_flush_exists(self):
        self.assertIn("InpCensusFlushEveryRows<1", self.wrapper)
        self.assertIn("g_census_rows%InpCensusFlushEveryRows==0", self.wrapper)
        deinit = self.wrapper.split("void OnDeinit(const int reason)", 1)[1]
        self.assertIn("FileFlush(g_census_handle)", deinit)

    def test_wrapper_fails_closed_if_any_trade_route_is_enabled(self):
        self.assertIn("if(InpAllowRangeMode || InpAllowTrendMode || InpAllowBreakoutMode) return(false);", self.wrapper)
        self.assertIn("InpUseStructuralEventSequence || InpUsePathManagement", self.wrapper)

    def test_base_indicator_reads_are_closed_bar_only(self):
        self.assertIn("CopyBuffer(handle,buffer,1,1,data)", self.base)
        self.assertIn("CopyBuffer(handle,buffer,2,1,data)", self.base)
        self.assertNotRegex(self.base, r"CopyBuffer\([^\n]*,\s*0\s*,")


if __name__ == "__main__":
    unittest.main()
