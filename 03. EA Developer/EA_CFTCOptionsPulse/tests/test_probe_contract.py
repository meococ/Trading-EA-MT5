#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path


WORKSPACE = Path(r"D:\Trading EA MT5")
SCRIPT = WORKSPACE / "03. EA Developer" / "EA_CFTCOptionsPulse" / "research" / "cftc_options_pulse_offline_probe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cftc_options_pulse_offline_probe", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ProbeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_options_residual_is_combined_minus_futures(self) -> None:
        self.assertEqual(self.module.options_residual(150, 90, 100, 80), 40)

    def test_report_is_delayed_to_following_monday(self) -> None:
        tuesday = date(2023, 7, 11)
        self.assertEqual(tuesday + timedelta(days=self.module.RELEASE_LAG_DAYS), date(2023, 7, 17))
        self.assertEqual((tuesday + timedelta(days=self.module.RELEASE_LAG_DAYS)).weekday(), 0)

    def test_exact_contract_codes_prevent_cross_rate_matches(self) -> None:
        self.assertEqual({row["code"] for row in self.module.CONTRACTS.values()}, {"099741", "096742", "097741"})

    def test_holdout_is_absent_from_acquisition_and_price_range(self) -> None:
        self.assertEqual(self.module.YEARS[-1], 2023)
        self.assertEqual(self.module.HOLDOUT_YEARS, (2024, 2025))
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("datetime(2023, 12, 31, 23, 59", source)
        self.assertNotIn("range(2017, 2026)", source)

    def test_rules_have_no_signal_magnitude_threshold(self) -> None:
        self.assertEqual(self.module.sign(1e-12), 1)
        self.assertEqual(self.module.sign(-1e-12), -1)
        self.assertEqual(self.module.sign(0.0), 0)

    def test_portable_terminal_and_cost_contract_are_frozen(self) -> None:
        self.assertEqual(self.module.TERMINAL_PATH.drive.upper(), "D:")
        self.assertEqual(self.module.ENTRY_TIME_UTC.hour, 7)
        self.assertEqual(self.module.EXIT_TIME_UTC.hour, 16)
        self.assertEqual(self.module.COST_X1_PIPS, {"EURUSD": 1.5, "GBPUSD": 2.0, "USDJPY": 1.5})

    def test_mt5_readiness_fix_does_not_change_strategy_contract(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("timeout=60_000, portable=True", source)
        self.assertIn("mt5.symbol_select(symbol, True)", source)
        self.assertIn("for attempt in range(1, 6)", source)


if __name__ == "__main__":
    unittest.main()
