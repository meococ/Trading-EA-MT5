import json
import math
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "03. EA Developer" / "EA_KlingerPullback"
SOURCE = PACKAGE / "EA_KlingerPullback.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
PREREG = PACKAGE / "research" / "HYP-KVO-EURUSD-M15-004_FROZEN_PREREG.md"
JOURNAL_PROOF = PACKAGE / "research" / "HYP-KVO-EURUSD-M15-004_JOURNAL_BUDGET_PROOF.json"


def kvo_volume_force(bars):
    previous_sum = None
    previous_dm = 0.0
    previous_trend = -1
    cm = 0.0
    cm_ready = False
    out = []
    for high, low, close, volume in bars:
        dm = high - low
        source_sum = high + low + close
        if previous_sum is None:
            previous_sum = source_sum
            previous_dm = dm
            out.append(None)
            continue
        trend = 1 if source_sum > previous_sum else -1
        vf = None
        if not cm_ready:
            seed_cm = previous_dm + dm
            if seed_cm > 0:
                cm = seed_cm
                cm_ready = True
                vf = volume * 2.0 * (dm / cm - 1.0) * trend * 100.0
        else:
            cm = cm + dm if trend == previous_trend else previous_dm + dm
            vf = 0.0 if cm == 0 else volume * 2.0 * (dm / cm - 1.0) * trend * 100.0
        previous_sum = source_sum
        previous_dm = dm
        previous_trend = trend
        out.append(vf)
    return out


class Kvo004SourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.journal_proof = json.loads(JOURNAL_PROOF.read_text(encoding="utf-8"))

    def test_identity_and_frozen_inputs(self):
        self.assertIn('EXPECTED_HYPOTHESIS="HYP-KVO-EURUSD-M15-004"', self.source)
        self.assertIn('EXPECTED_SYMBOL="EURUSD"', self.source)
        self.assertIn("InpMagic==5604004", self.source)
        self.assertEqual(self.contract["execution_profile"]["expected_symbol"], "EURUSD")
        self.assertEqual(self.contract["inputs"]["InpMagic"], 5604004)

    def test_formula_and_flat_safe_initialization(self):
        values = kvo_volume_force([
            (1.0, 1.0, 1.0, 10),
            (1.0, 1.0, 1.0, 11),
            (1.2, 1.0, 1.1, 12),
            (1.2, 1.2, 1.2, 13),
        ])
        self.assertIsNone(values[0])
        self.assertIsNone(values[1])
        self.assertTrue(math.isfinite(values[2]))
        self.assertTrue(math.isfinite(values[3]))
        self.assertIn("const int trend=(source_sum>g_previous_sum ? 1 : -1);", self.source)
        self.assertIn("vf=(g_cm==0.0 ? 0.0", self.source)
        self.assertNotIn("MathAbs(dm/g_cm", self.source)

    def test_closed_bar_and_exact_next_contract(self):
        self.assertRegex(self.source, r"CopyRates\(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates\)")
        self.assertIn("availability_time-decision_time)!=900", self.source)
        self.assertIn("CopyBuffer(g_atr_handle,0,1,1,data)", self.source)
        self.assertNotRegex(self.source, r"CopyBuffer\([^\n]*,0,0,1,")
        self.assertIn("current_open==g_last_bar_open", self.source)

    def test_preload_is_complete_origin_bound_and_ordered(self):
        required = [
            "SERIES_SYNCHRONIZED",
            "SERIES_BARS_COUNT",
            "SERIES_FIRSTDATE",
            "SERIES_LASTBAR_DATE",
            "(long)available!=series_count",
            "copied!=requested",
            "history[0].time!=(datetime)first_epoch",
            "history[copied-1].time!=expected_last",
            "history[i].time<=history[i-1].time",
            "KVO004_PRELOAD synchronized=",
        ]
        for token in required:
            self.assertIn(token, self.source)

    def test_documented_fsm_boundaries_are_literal(self):
        required = [
            "ko<0.0 && bar.close>g_close_ema100",
            "ko>0.0 && bar.close<g_close_ema100",
            "g_previous_ko<=g_previous_ko_signal",
            "ko>g_ko_signal_ema",
            "g_previous_ko>=g_previous_ko_signal",
            "ko<g_ko_signal_ema",
            "consumed_state",
        ]
        for token in required:
            self.assertIn(token, self.source)

    def test_risk_exit_and_no_rescue_filters(self):
        self.assertIn("const double TARGET_R=1.50;", self.source)
        self.assertIn("const int    MAX_HOLD_BARS=16;", self.source)
        self.assertIn("InpMaxTradesPerDay==1", self.source)
        self.assertIn("OrderCalcProfit", self.source)
        self.assertIn("OrderCalcMargin", self.source)
        self.assertNotRegex(self.source, r"Inp(Session|ADX|News|Spread|Direction)")
        self.assertIn("No trailing, breakeven, partial exit", self.prereg)

    def test_d0_proof_is_read_only_and_trade_gateway_is_bounded(self):
        self.assertIn("DATA_EPOCH_D0_SERIES_PROOF", self.source)
        self.assertEqual(self.source.count("OrderSend(request,result)"), 2)
        self.assertIn("positions!=0 || orders!=0", self.source)

    def test_rejected_entry_is_nonfatal_only_after_zero_inventory_reconciliation(self):
        self.assertIn("const bool send_ok=OrderSend(request,result);", self.source)
        self.assertIn("if(!send_ok && !definitive_no_fill)", self.source)
        self.assertIn("reason=ENTRY_SEND_TRANSPORT", self.source)
        self.assertIn("result.retcode==TRADE_RETCODE_MARKET_CLOSED", self.source)
        self.assertIn("result.order==0 && result.deal==0", self.source)
        self.assertIn("reason=ENTRY_REJECT_UNKNOWN", self.source)
        self.assertIn("!OwnedPositionCount(positions) || !OwnedOrderCount(orders)", self.source)
        self.assertIn("reason=ENTRY_REJECT_AMBIGUOUS", self.source)
        fatal = self.source.index('PrintFormat("KVO004_FATAL reason=ENTRY_REJECT_AMBIGUOUS')
        branch = self.source.rfind("if(!OwnedPositionCount(positions)", 0, fatal)
        between = self.source[branch:self.source.index("g_entries_accepted++;", fatal)]
        self.assertIn("g_runtime_failed=true;", between)

    def test_trade_mode_journal_is_compact(self):
        self.assertNotIn('PrintFormat("KVO004_SIGNAL', self.source)
        self.assertNotIn('PrintFormat("KVO004_ENTRY', self.source)
        self.assertNotIn('PrintFormat("KVO004_ORDER_CHECK_REJECT', self.source)
        self.assertNotIn('PrintFormat("KVO004_ORDER_SEND_REJECT', self.source)
        self.assertIn('PrintFormat("KVO004_SUMMARY', self.source)
        self.assertIn('PrintFormat("KVO004_FATAL', self.source)

    def test_journal_cap_uses_full_raw_signal_path(self):
        proof = self.journal_proof
        self.assertEqual(proof["parent_run_id"], "20260810_210309")
        self.assertEqual(proof["parent_closed_bars"], 197804)
        self.assertEqual(proof["parent_raw_signals"], 9524)
        self.assertEqual(proof["diagnostic_compact_utf16_estimated_bytes"], 118200)
        self.assertEqual(proof["train_calendar_days"], 2919)
        self.assertEqual(proof["bounded_native_lines_per_source"], 29957)
        self.assertEqual(proof["bounded_total_bytes"], 16626216)
        self.assertEqual(proof["max_journal_delta_bytes"], 33554432)
        self.assertGreater(proof["headroom_multiple"], 2.0)
        self.assertIn("max_journal_delta_bytes=33554432", self.prereg)


if __name__ == "__main__":
    unittest.main()
