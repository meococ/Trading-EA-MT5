from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name(
    "analyze_cme6e_option_pin_design_futures_reference.py"
)
SPEC = importlib.util.spec_from_file_location("futures_analysis", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FuturesReferenceTests(unittest.TestCase):
    def request(self) -> dict:
        return {
            "event_id": "E1",
            "request_id": "R1",
            "underlying": "6EH8",
            "expiration_utc": "2018-01-03T20:00:00Z",
            "decision_utc": "2018-01-03T19:45:00Z",
            "start": "2018-01-03T19:44:00Z",
            "end": "2018-01-03T19:45:00Z",
            "pin_strike": 1.205,
        }

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "symbol": ["6EH8", "6EH8", "6EH8"],
                "bid_px_00": [1.2040, 1.2048, 1.2050],
                "ask_px_00": [1.2041, 1.2047, 1.2051],
                "bid_sz_00": [2, 2, 2],
                "ask_sz_00": [3, 3, 3],
            },
            index=pd.DatetimeIndex(
                [
                    "2018-01-03T19:44:10Z",
                    "2018-01-03T19:44:50Z",
                    "2018-01-03T19:45:00Z",
                ],
                name="ts_recv",
            ),
        )

    def test_uses_latest_valid_not_crossed_or_at_decision(self) -> None:
        result = MODULE.select_reference(self.frame(), self.request())
        self.assertTrue(result["reference_valid"])
        self.assertEqual(result["reference_mid"], "1.20405")
        self.assertEqual(result["primary_direction"], "BUY")
        self.assertEqual(result["post_decision_receive_rows"], 1)

    def test_symbol_mismatch_fails_closed(self) -> None:
        frame = self.frame()
        frame["symbol"] = "6EM8"
        result = MODULE.select_reference(frame, self.request())
        self.assertFalse(result["reference_valid"])
        self.assertEqual(result["rejection_reason"], "SYMBOL_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
