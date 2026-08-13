from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "quote_cme6e_option_pin_design_futures_reference.py"
)
SPEC = importlib.util.spec_from_file_location("futures_quote", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FuturesRequestTests(unittest.TestCase):
    def test_builds_exact_raw_symbol_sixty_second_window(self) -> None:
        pin = {
            "event_id": "E1",
            "underlying": "6EH8",
            "expiration_utc": "2018-01-03T20:00:00Z",
            "decision_utc": "2018-01-03T19:45:00Z",
            "pin_strike": "1.205",
            "pin_total_oi": "1034",
        }
        original_expected = MODULE.EXPECTED_REQUESTS
        MODULE.EXPECTED_REQUESTS = 1
        try:
            request = MODULE.build_requests([pin])[0]
        finally:
            MODULE.EXPECTED_REQUESTS = original_expected
        self.assertEqual(request["symbols"], ["6EH8"])
        self.assertEqual(request["stype_in"], "raw_symbol")
        self.assertEqual(request["start"], "2018-01-03T19:44:00Z")
        self.assertEqual(request["end"], "2018-01-03T19:45:00Z")

    def test_excludes_frozen_degraded_date_before_quote(self) -> None:
        pin = {
            "event_id": "E2",
            "underlying": "6EH9",
            "expiration_utc": "2019-02-22T20:00:00Z",
            "decision_utc": "2019-02-22T19:45:00Z",
            "pin_strike": "1.135",
            "pin_total_oi": "100",
        }
        original_expected = MODULE.EXPECTED_REQUESTS
        MODULE.EXPECTED_REQUESTS = 0
        try:
            self.assertEqual(MODULE.build_requests([pin]), [])
        finally:
            MODULE.EXPECTED_REQUESTS = original_expected


if __name__ == "__main__":
    unittest.main()
