"""Strict missing-OI and temporal tests for HYP002 source analysis."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name(
    "analyze_cme6e_option_pin_design_source_002.py"
)
SPEC = importlib.util.spec_from_file_location("option_pin_source_002", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


DECISION = pd.Timestamp("2019-07-12T13:45:00Z")
REFERENCE = pd.Timestamp("2019-07-11T00:00:00Z")


def request() -> dict[str, object]:
    return {
        "event_id": "EVT001",
        "request_id": "REQ001",
        "asset": "2EU",
        "underlying": "6EU9",
        "expiration_utc": "2019-07-12T14:00:00Z",
        "decision_utc": DECISION.isoformat(),
        "required_oi_reference_utc": REFERENCE.isoformat(),
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
    }


def contracts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "raw_symbol": "2EUN9 C1130",
                "instrument_class": "C",
                "strike_price": 1.13,
                "instrument_ids": "1",
            },
            {
                "raw_symbol": "2EUN9 P1130",
                "instrument_class": "P",
                "strike_price": 1.13,
                "instrument_ids": "2",
            },
        ]
    )


def stat(
    symbol: str,
    instrument_id: int,
    quantity: int,
    *,
    ts: str = "2019-07-12T01:00:00Z",
    ts_ref: pd.Timestamp = REFERENCE,
) -> dict[str, object]:
    return {
        "ts_recv": pd.Timestamp(ts),
        "ts_event": pd.Timestamp(ts),
        "instrument_id": instrument_id,
        "ts_ref": ts_ref,
        "quantity": quantity,
        "sequence": instrument_id,
        "stat_type": 9,
        "update_action": 1,
        "symbol": symbol,
    }


class StrictSourceTests(unittest.TestCase):
    def test_missing_contract_is_unknown_and_invalid(self) -> None:
        statistics = pd.DataFrame([stat("2EUN9 C1130", 1, 10)])
        result, surface = module.analyze_event(request(), statistics, contracts())
        self.assertEqual(result["missing_oi_count"], 1)
        self.assertFalse(result["complete_published_oi_surface"])
        self.assertFalse(result["source_valid"])
        self.assertTrue(surface.empty)

    def test_explicit_zero_is_known_and_can_complete_surface(self) -> None:
        statistics = pd.DataFrame(
            [
                stat("2EUN9 C1130", 1, 10),
                stat("2EUN9 P1130", 2, 0),
            ]
        )
        result, surface = module.analyze_event(request(), statistics, contracts())
        self.assertEqual(result["missing_oi_count"], 0)
        self.assertTrue(result["complete_published_oi_surface"])
        self.assertTrue(result["source_valid"])
        self.assertTrue(result["unique_positive_pin"])
        self.assertEqual(result["pin_strike"], 1.13)
        self.assertFalse(surface.empty)

    def test_wrong_reference_date_is_unknown(self) -> None:
        older = pd.Timestamp("2019-07-10T00:00:00Z")
        statistics = pd.DataFrame(
            [
                stat("2EUN9 C1130", 1, 10, ts_ref=older),
                stat("2EUN9 P1130", 2, 5, ts_ref=older),
            ]
        )
        result, _ = module.analyze_event(request(), statistics, contracts())
        self.assertEqual(result["missing_oi_count"], 2)
        self.assertFalse(result["source_valid"])

    def test_any_postdecision_payload_record_fails_event(self) -> None:
        statistics = pd.DataFrame(
            [
                stat("2EUN9 C1130", 1, 10),
                stat("2EUN9 P1130", 2, 5),
                stat("2EUN9 C1130", 1, 11, ts="2019-07-12T13:45:00Z"),
            ]
        )
        result, _ = module.analyze_event(request(), statistics, contracts())
        self.assertEqual(result["post_decision_rows"], 1)
        self.assertFalse(result["source_valid"])


if __name__ == "__main__":
    unittest.main()

