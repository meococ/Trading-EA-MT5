"""Focused tests for full-DESIGN event source semantics."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name("analyze_cme6e_option_pin_design_source.py")
SPEC = importlib.util.spec_from_file_location("option_pin_source_analysis", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class EventSourceTests(unittest.TestCase):
    def test_zero_completion_and_unique_pin(self) -> None:
        request = {
            "request_id": "R1",
            "event_id": "E1",
            "asset": "2EU",
            "underlying": "6EU9",
            "expiration_utc": "2019-07-12T14:00:00Z",
            "decision_utc": "2019-07-12T13:45:00Z",
            "max_oi_reference_utc": "2019-07-11T00:00:00Z",
        }
        contracts = pd.DataFrame(
            {
                "raw_symbol": ["C112", "P112", "C113", "P113"],
                "instrument_class": ["C", "P", "C", "P"],
                "strike_price": [1.12, 1.12, 1.13, 1.13],
                "instrument_ids": ["1", "2", "3", "4"],
            }
        )
        stats = pd.DataFrame(
            {
                "ts_recv": [pd.Timestamp("2019-07-12T13:00:00Z")] * 3,
                "ts_event": [pd.Timestamp("2019-07-12T13:00:00Z")] * 3,
                "instrument_id": [1, 3, 4],
                "ts_ref": [pd.Timestamp("2019-07-11T00:00:00Z")] * 3,
                "quantity": [20, 30, 15],
                "sequence": [1, 2, 3],
                "stat_type": [9, 9, 9],
                "symbol": ["C112", "C113", "P113"],
            }
        )
        result, surface = module.analyze_event(request, stats, contracts)
        self.assertTrue(result["source_valid"])
        self.assertTrue(result["unique_positive_pin"])
        self.assertEqual(result["pin_strike"], 1.13)
        self.assertEqual(result["pin_total_oi"], 45)
        self.assertEqual(result["missing_oi_count"], 1)
        self.assertEqual(int(surface["total_oi"].sum()), 65)

    def test_unresolved_instrument_id_fails_event(self) -> None:
        request = {
            "request_id": "R1",
            "event_id": "E1",
            "asset": "2EU",
            "underlying": "6EU9",
            "expiration_utc": "2019-07-12T14:00:00Z",
            "decision_utc": "2019-07-12T13:45:00Z",
            "max_oi_reference_utc": "2019-07-11T00:00:00Z",
        }
        contracts = pd.DataFrame(
            {
                "raw_symbol": ["C113", "P113"],
                "instrument_class": ["C", "P"],
                "strike_price": [1.13, 1.13],
                "instrument_ids": ["3", "4"],
            }
        )
        stats = pd.DataFrame(
            {
                "ts_recv": [pd.Timestamp("2019-07-12T13:00:00Z")] * 2,
                "ts_event": [pd.Timestamp("2019-07-12T13:00:00Z")] * 2,
                "instrument_id": [999, 4],
                "ts_ref": [pd.Timestamp("2019-07-11T00:00:00Z")] * 2,
                "quantity": [30, 15],
                "sequence": [1, 2],
                "stat_type": [9, 9],
                "symbol": ["C113", "P113"],
            }
        )
        result, _ = module.analyze_event(request, stats, contracts)
        self.assertFalse(result["source_valid"])
        self.assertEqual(result["unresolved_alias_rows"], 1)


if __name__ == "__main__":
    unittest.main()
