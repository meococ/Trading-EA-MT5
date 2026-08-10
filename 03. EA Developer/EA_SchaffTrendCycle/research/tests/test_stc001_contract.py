import json
import math
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "03. EA Developer" / "EA_SchaffTrendCycle"
SOURCE = PACKAGE / "EA_SchaffTrendCycle.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
PREREG = PACKAGE / "research" / "HYP-STC-EURUSD-M15-001_FROZEN_PREREG.md"
COMPILE_LOG = PACKAGE / "EA_SchaffTrendCycle.log"
EX5 = PACKAGE / "EA_SchaffTrendCycle.ex5"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def ema(values, length):
    alpha = 2.0 / (length + 1.0)
    out = [values[0]]
    for value in values[1:]:
        out.append(out[-1] + alpha * (value - out[-1]))
    return out


def rolling_stochastic(values, cycle):
    out = [None] * len(values)
    prior = 50.0
    for i in range(cycle - 1, len(values)):
        window = values[i - cycle + 1 : i + 1]
        if any(value is None for value in window):
            continue
        lo, hi = min(window), max(window)
        prior = 100.0 * (values[i] - lo) / (hi - lo) if hi - lo > 1e-14 else prior
        out[i] = min(100.0, max(0.0, prior))
    return out


def ema_available(values, length):
    alpha = 2.0 / (length + 1.0)
    out = [None] * len(values)
    prior = None
    for i, value in enumerate(values):
        if value is None:
            continue
        prior = value if prior is None else prior + alpha * (value - prior)
        out[i] = prior
    return out


def stc_reference(closes):
    fast = ema(closes, 23)
    slow = ema(closes, 50)
    macd = [a - b for a, b in zip(fast, slow)]
    k1 = rolling_stochastic(macd, 10)
    d1 = ema_available(k1, 3)
    k2 = rolling_stochastic(d1, 10)
    return macd, ema_available(k2, 3)


class StcContractTests(unittest.TestCase):
    def test_identity_and_single_indicator_mechanism(self):
        text = source()
        self.assertIn('EXPECTED_HYPOTHESIS="HYP-STC-EURUSD-M15-001"', text)
        self.assertIn('EXPECTED_VARIANT="STC_CLASSIC_TREND_CYCLE_V1"', text)
        self.assertIn('EXPECTED_SYMBOL="EURUSD"', text)
        for forbidden in ("iCustom(", "ADX", "Bollinger", "QQE", "WaveTrend", "PERIOD_H1"):
            self.assertNotIn(forbidden, text)

    def test_formula_constants_and_double_stochastic(self):
        text = source()
        expected = {
            "STC_FAST_EMA": "23",
            "STC_SLOW_EMA": "50",
            "STC_CYCLE": "10",
            "STC_D1": "3",
            "STC_D2": "3",
            "STC_LOWER": "25.0",
            "STC_UPPER": "75.0",
        }
        for name, value in expected.items():
            self.assertRegex(text, rf"const (?:int|double)\s+{name}\s*=\s*{re.escape(value)};")
        self.assertEqual(text.count("WindowRange("), 3)  # definition plus two passes
        self.assertIn("PreloadIndicatorState()", text)
        self.assertIn("AdvanceIndicatorState(const MqlRates &bar)", text)
        self.assertNotIn("STC_HISTORY_BARS", text)
        closes = [1.1 + 0.0002 * i + 0.001 * math.sin(i / 5.0) for i in range(200)]
        macd, stc = stc_reference(closes)
        self.assertTrue(math.isfinite(macd[-1]))
        self.assertTrue(math.isfinite(stc[-1]))
        self.assertGreaterEqual(stc[-1], 0.0)
        self.assertLessEqual(stc[-1], 100.0)
        _, prefix_stc = stc_reference(closes[:-1])
        self.assertAlmostEqual(prefix_stc[-1], stc[-2], places=15)

    def test_signal_predicates_are_exact_and_trend_aligned(self):
        text = source()
        self.assertIn("g_previous_stc<=STC_LOWER && g_current_stc>STC_LOWER && g_current_macd>0.0", text)
        self.assertIn("g_previous_stc>=STC_UPPER && g_current_stc<STC_UPPER && g_current_macd<0.0", text)
        self.assertNotIn("g_current_macd>=0.0", text)
        self.assertNotIn("g_current_macd<=0.0", text)

    def test_closed_bar_and_exact_next_clock(self):
        text = source()
        self.assertIn("const datetime STC_PRELOAD_FIRST=D'2015.01.02 09:00';", text)
        self.assertIn("const datetime STC_PRELOAD_LAST=D'2015.12.31 20:00';", text)
        self.assertIn("const int      STC_PRELOAD_BARS=24776;", text)
        self.assertIn("SERIES_SYNCHRONIZED", text)
        self.assertIn("last_closed!=STC_PRELOAD_LAST", text)
        self.assertIn("Bars(_Symbol,PERIOD_M15,STC_PRELOAD_FIRST,last_closed)", text)
        self.assertIn("preload_count!=STC_PRELOAD_BARS", text)
        self.assertIn("CopyRates(_Symbol,PERIOD_M15,1,preload_count,rates)", text)
        self.assertIn("rates[0].time!=STC_PRELOAD_FIRST", text)
        self.assertIn("rates[copied-1].time!=last_closed", text)
        self.assertIn("bar.time<=g_indicator_bar_time", text)
        self.assertIn("CopyRates(_Symbol,PERIOD_M15,1,1,rates)", text)
        self.assertIn("SERIES_LASTBAR_DATE", text)
        self.assertIn("(long)(availability_time-decision_time)!=900", text)
        for field in ("iOpen", "iHigh", "iLow", "iClose"):
            self.assertNotIn(f"{field}(_Symbol,PERIOD_M15,0)", text)

    def test_risk_target_and_time_exit_are_frozen(self):
        text = source()
        self.assertIn("const int    ATR_PERIOD=14;", text)
        self.assertIn("const double STOP_ATR_MULTIPLIER=1.50;", text)
        self.assertIn("const double TARGET_R=1.50;", text)
        self.assertIn("STOP_ATR_MULTIPLIER*signal.atr", text)
        self.assertIn("entry+TARGET_R*risk", text)
        self.assertIn("entry-TARGET_R*risk", text)
        self.assertIn("held_bars>=InpMaxHoldBars", text)
        self.assertIn("InpMaxHoldBars==16", text)

    def test_one_first_signal_per_day_and_no_session_filter(self):
        text = source()
        self.assertIn("date_key==g_consumed_signal_date", text)
        self.assertIn("g_consumed_signal_date=date_key", text)
        self.assertIn("InpMaxTradesPerDay==1", text)
        for forbidden in ("TradeStart", "TradeEnd", "AsianStart", "London", "NewYork"):
            self.assertNotIn(forbidden, text)

    def test_design_and_weekend_boundaries(self):
        text = source()
        self.assertIn("const datetime DESIGN_FROM=D'2016.01.04 00:00';", text)
        self.assertIn("const datetime DESIGN_TO=D'2021.01.01 00:00';", text)
        self.assertIn("p.day_of_week==5 && p.hour>=InpFridayFlattenHour", text)
        self.assertIn("InpFridayFlattenHour==20", text)

    def test_risk_sizing_and_order_checks_fail_closed(self):
        text = source()
        self.assertIn("OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit)", text)
        self.assertIn("equity*InpRiskPercent/100.0", text)
        self.assertIn("MathFloor(raw_volume/step+1e-9)*step", text)
        self.assertIn("OrderCalcMargin(order_type,_Symbol,sized,entry,required_margin)", text)
        self.assertIn("OrderCheck(request,check) || check.retcode!=0", text)
        self.assertEqual(text.count("OrderSend(request,result)"), 2)
        self.assertIn("return(retcode==TRADE_RETCODE_DONE);", text)

    def test_contract_is_frozen_model0_baseline(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["telemetry_profile"], "none")
        profile = contract["execution_profile"]
        self.assertEqual(profile["authority"], "registered-untuned-model0-baseline")
        self.assertEqual(profile["timeframe"], "M15")
        self.assertEqual(profile["expected_symbol"], "EURUSD")
        self.assertTrue(profile["closed_bar_only"])
        self.assertFalse(profile["no_trade_api"])
        self.assertFalse(profile["promotion_eligible"])

    def test_prereg_freezes_economic_and_sealed_windows(self):
        text = PREREG.read_text(encoding="utf-8")
        self.assertIn("`2016.01.04-2021.01.01`", text)
        self.assertIn("`2021.01.01-2022.01.01`", text)
        self.assertIn("`2022.01.01-2023.01.01`", text)
        self.assertIn("PF `>1.30`", text)
        self.assertIn("cadence `2-5/week`", text)
        self.assertIn("x1.5 PF `>=1.25`", text)
        self.assertIn("x2 PF `>=1.00`", text)

    def test_fresh_compile_is_zero_error_zero_warning(self):
        self.assertTrue(EX5.is_file())
        self.assertGreater(EX5.stat().st_size, 0)
        log = COMPILE_LOG.read_text(encoding="utf-16", errors="replace")
        self.assertEqual(log.count("Result: 0 errors, 0 warnings"), 1)


if __name__ == "__main__":
    unittest.main()
