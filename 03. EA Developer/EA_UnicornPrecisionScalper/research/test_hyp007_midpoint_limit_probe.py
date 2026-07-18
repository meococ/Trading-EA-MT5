#!/usr/bin/env python3
"""Contract tests for the frozen HYP-UPS-XAU-M5-007 fill probe."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "probe_unicorn_midpoint_limit_fill.py"
PREREG = ROOT / "HYP-UPS-XAU-M5-007_FROZEN_PREREG.md"


def load_module():
    spec = importlib.util.spec_from_file_location("hyp007_probe", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load HYP-007 probe")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MidpointLimitProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.prereg = PREREG.read_text(encoding="utf-8")

    @staticmethod
    def rates(rows: list[tuple[float, float, float]]) -> np.ndarray:
        result = np.zeros(len(rows), dtype=[("low", "f8"), ("high", "f8"), ("close", "f8")])
        for index, (low, high, close) in enumerate(rows):
            result[index] = (low, high, close)
        return result

    def test_long_limit_touch_fills(self) -> None:
        rates = self.rates([(101, 102, 101.5), (99.5, 102, 101), (101, 103, 102)])
        result = self.module.limit_fill_within(rates, 0, 1, 100.0, 98.0, 2)
        self.assertEqual(result["status"], "filled")
        self.assertEqual(result["offset"], 1)

    def test_close_invalidation_cancels_before_later_touch(self) -> None:
        rates = self.rates([(101, 102, 101.5), (100.5, 102, 97.5), (99, 103, 101)])
        result = self.module.limit_fill_within(rates, 0, 1, 100.0, 98.0, 2)
        self.assertEqual(result["status"], "invalidated")

    def test_expiry_has_no_market_fallback(self) -> None:
        rates = self.rates([(101, 102, 101.5), (100.5, 102, 101), (100.2, 103, 102)])
        result = self.module.limit_fill_within(rates, 0, 1, 100.0, 98.0, 2)
        self.assertEqual(result["status"], "expired")

    def test_frozen_contract_is_no_pnl_and_d_only(self) -> None:
        self.assertIn('HYPOTHESIS_ID = "HYP-UPS-XAU-M5-007"', self.source)
        self.assertIn("EXPIRY_BARS = 3", self.source)
        self.assertIn('data_path.drive.upper() != "D:"', self.source)
        self.assertIn('"outcomes_evaluated": False', self.source)
        self.assertNotIn("order_send", self.source.lower())
        self.assertNotIn("trade.Buy", self.source)
        self.assertIn("No chase, no market fallback", self.prereg)


if __name__ == "__main__":
    unittest.main()

