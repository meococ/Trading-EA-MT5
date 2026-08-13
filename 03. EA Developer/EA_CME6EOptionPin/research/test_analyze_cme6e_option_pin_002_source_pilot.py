"""Focused tests for quarterly pilot absent-OI handling."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name(
    "analyze_cme6e_option_pin_002_source_pilot.py"
)
SPEC = importlib.util.spec_from_file_location("option_pin_analysis_002", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ZeroCompletionTests(unittest.TestCase):
    def test_zero_completion_preserves_positive_unique_max(self) -> None:
        definitions = pd.DataFrame(
            {
                "instrument_id": [1, 2, 3, 4],
                "instrument_class": ["C", "P", "C", "P"],
                "strike_price": [1.12, 1.12, 1.13, 1.13],
                "symbol": ["C112", "P112", "C113", "P113"],
            }
        )
        oi = pd.DataFrame(
            {
                "instrument_id": [1, 3, 4],
                "instrument_class": ["C", "C", "P"],
                "strike_price": [1.12, 1.13, 1.13],
                "quantity": [20, 30, 15],
            }
        )
        completed, missing = module.zero_complete(definitions, oi)
        surface = module.analysis.aggregate_surface(completed)
        pin, total, unique = module.surface_max(surface)
        self.assertEqual(missing["instrument_id"].tolist(), [2])
        self.assertTrue(unique)
        self.assertEqual(pin, 1.13)
        self.assertEqual(total, 45)

    def test_surface_max_fails_on_tie(self) -> None:
        surface = pd.DataFrame(
            {
                "strike_price": [1.12, 1.13],
                "call_oi": [10, 20],
                "put_oi": [20, 10],
                "total_oi": [30, 30],
            }
        )
        self.assertEqual(module.surface_max(surface), (None, None, False))


if __name__ == "__main__":
    unittest.main()
