"""Focused tests for the source-only option OI semantics."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name(
    "analyze_cme6e_option_pin_001_source_pilot.py"
)
SPEC = importlib.util.spec_from_file_location("option_pin_analysis", MODULE_PATH)
assert SPEC and SPEC.loader
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


def definition_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_recv": pd.Timestamp("2019-07-12T12:00:00Z"),
                "ts_event": pd.Timestamp("2019-07-12T12:00:00Z"),
                "instrument_id": instrument_id,
                "instrument_class": option_class,
                "security_update_action": "A",
                "user_defined_instrument": "N",
                "asset": "2EU",
                "underlying": "6EU9",
                "expiration": pd.Timestamp("2019-07-12T14:00:00Z"),
                "strike_price": strike,
                "symbol": f"TEST-{instrument_id}",
            }
            for instrument_id, option_class, strike in [
                (1, "C", 1.12),
                (2, "P", 1.12),
                (3, "C", 1.13),
                (4, "P", 1.13),
            ]
        ]
    )


def statistics_frame(equal_max: bool = False) -> pd.DataFrame:
    quantities = [10, 20, 40, 5] if not equal_max else [10, 20, 20, 10]
    return pd.DataFrame(
        [
            {
                "ts_recv": pd.Timestamp("2019-07-12T13:00:00Z"),
                "ts_event": pd.Timestamp("2019-07-12T13:00:00Z"),
                "instrument_id": instrument_id,
                "ts_ref": pd.Timestamp("2019-07-11T00:00:00Z"),
                "quantity": quantity,
                "sequence": instrument_id,
                "stat_type": 9,
                "symbol": f"TEST-{instrument_id}",
            }
            for instrument_id, quantity in enumerate(quantities, start=1)
        ]
    )


class SourceSemanticsTests(unittest.TestCase):
    def test_unique_max_passes_without_direction(self) -> None:
        definitions, definition_counts = analysis.select_definitions(
            definition_frame()
        )
        oi, oi_counts = analysis.select_open_interest(
            statistics_frame(), definitions
        )
        surface = analysis.aggregate_surface(oi)
        gates, pin, max_oi = analysis.determine_gates(
            definitions, definition_counts, oi, oi_counts, surface
        )
        self.assertTrue(all(gates.values()))
        self.assertEqual(pin, 1.13)
        self.assertEqual(max_oi, 45)

    def test_tied_max_fails_closed(self) -> None:
        definitions, definition_counts = analysis.select_definitions(
            definition_frame()
        )
        oi, oi_counts = analysis.select_open_interest(
            statistics_frame(equal_max=True), definitions
        )
        surface = analysis.aggregate_surface(oi)
        gates, pin, max_oi = analysis.determine_gates(
            definitions, definition_counts, oi, oi_counts, surface
        )
        self.assertFalse(gates["unique_positive_max_oi_strike"])
        self.assertIsNone(pin)
        self.assertIsNone(max_oi)

    def test_future_reference_is_excluded(self) -> None:
        definitions, _ = analysis.select_definitions(definition_frame())
        stats = statistics_frame()
        stats.loc[stats["instrument_id"] == 4, "ts_ref"] = pd.Timestamp(
            "2019-07-12T00:00:00Z"
        )
        oi, counts = analysis.select_open_interest(stats, definitions)
        self.assertNotIn(4, oi["instrument_id"].tolist())
        self.assertEqual(counts["selected_by_class"]["P"], 1)

    def test_post_decision_record_is_rejected(self) -> None:
        definitions = definition_frame()
        definitions.loc[0, "ts_event"] = pd.Timestamp("2019-07-12T13:45:00Z")
        with self.assertRaises(analysis.AnalysisError):
            analysis.select_definitions(definitions)


if __name__ == "__main__":
    unittest.main()
