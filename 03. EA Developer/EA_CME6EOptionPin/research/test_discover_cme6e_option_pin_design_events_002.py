"""Focused tests for corrected point-in-time option definition discovery."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name(
    "discover_cme6e_option_pin_design_events_002.py"
)
SPEC = importlib.util.spec_from_file_location("option_pin_discovery_002", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def row(
    *,
    ts: str,
    expiration: str = "2019-07-12T14:00:00Z",
    instrument_id: int = 1,
    raw_symbol: str = "2EUN9 C1130",
) -> dict[str, object]:
    return {
        "ts_recv": pd.Timestamp(ts),
        "ts_event": pd.Timestamp(ts),
        "instrument_id": instrument_id,
        "raw_symbol": raw_symbol,
        "instrument_class": "C",
        "expiration": pd.Timestamp(expiration),
        "underlying": "6EU9",
        "asset": "2EU",
        "strike_price": 1.13,
    }


class PitDiscoveryTests(unittest.TestCase):
    def test_ignores_latest_overall_when_received_after_decision(self) -> None:
        frame = pd.DataFrame(
            [
                row(ts="2019-07-10T12:00:00Z"),
                row(ts="2019-07-13T00:00:00Z"),
            ]
        )
        stable, audit = module.stable_contracts_pit(frame)
        selected = stable.iloc[0]
        self.assertEqual(selected["ts_recv"], pd.Timestamp("2019-07-10T12:00:00Z"))
        self.assertEqual(audit["selected_definition_post_decision_count"], 0)

    def test_drops_symbol_when_no_definition_is_knowable_at_decision(self) -> None:
        frame = pd.DataFrame([row(ts="2019-07-13T00:00:00Z")])
        with self.assertRaises(module.DiscoveryError):
            module.stable_contracts_pit(frame)

    def test_accepts_expiration_revision_published_before_revised_decision(self) -> None:
        frame = pd.DataFrame(
            [
                row(ts="2019-07-01T00:00:00Z"),
                row(
                    ts="2019-07-05T00:00:00Z",
                    expiration="2019-07-12T17:00:00Z",
                ),
            ]
        )
        stable, audit = module.stable_contracts_pit(frame)
        selected = stable.iloc[0]
        self.assertEqual(
            selected["expiration"], pd.Timestamp("2019-07-12T17:00:00Z")
        )
        self.assertEqual(audit["predecision_expiration_revision_symbol_count"], 1)

    def test_late_expiration_revision_cannot_rewrite_past_event(self) -> None:
        frame = pd.DataFrame(
            [
                row(ts="2019-07-01T00:00:00Z"),
                row(
                    ts="2019-07-13T00:00:00Z",
                    expiration="2019-07-12T17:00:00Z",
                ),
            ]
        )
        stable, audit = module.stable_contracts_pit(frame)
        selected = stable.iloc[0]
        self.assertEqual(
            selected["expiration"], pd.Timestamp("2019-07-12T14:00:00Z")
        )
        self.assertEqual(audit["predecision_expiration_revision_symbol_count"], 0)

    def test_expiry_extension_after_first_decision_keeps_earliest_fixed_point(self) -> None:
        frame = pd.DataFrame(
            [
                row(ts="2019-07-12T13:44:59Z"),
                row(
                    ts="2019-07-12T13:45:01Z",
                    expiration="2019-07-12T16:00:00Z",
                ),
            ]
        )
        stable, audit = module.stable_contracts_pit(frame)
        selected = stable.iloc[0]
        self.assertEqual(
            selected["expiration"], pd.Timestamp("2019-07-12T14:00:00Z")
        )
        self.assertEqual(audit["multiple_fixed_point_symbol_count"], 1)

    def test_request_freezes_unknown_missing_oi_policy(self) -> None:
        contracts = pd.DataFrame(
            [
                {
                    "instrument_id": 1,
                    "raw_symbol": "2EUN9 C1130",
                    "instrument_class": "C",
                    "expiration": pd.Timestamp("2019-07-12T14:00:00Z"),
                    "underlying": "6EU9",
                    "asset": "2EU",
                    "strike_price": 1.13,
                },
                {
                    "instrument_id": 2,
                    "raw_symbol": "2EUN9 P1130",
                    "instrument_class": "P",
                    "expiration": pd.Timestamp("2019-07-12T14:00:00Z"),
                    "underlying": "6EU9",
                    "asset": "2EU",
                    "strike_price": 1.13,
                },
            ]
        )
        events, _, _ = module.base.discover_events(contracts)
        requests = module.statistics_requests_pit(module.base.eligible_events(events))
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["missing_oi_policy"], "UNKNOWN_EVENT_INVALID")
        self.assertEqual(
            requests[0]["definition_selection"],
            "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT",
        )


if __name__ == "__main__":
    unittest.main()
