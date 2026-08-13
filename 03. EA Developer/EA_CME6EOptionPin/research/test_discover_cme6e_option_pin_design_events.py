"""Focused clock, overlap, and statistics-request tests."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).with_name("discover_cme6e_option_pin_design_events.py")
SPEC = importlib.util.spec_from_file_location("option_pin_discovery", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def contracts(collide: bool = False) -> pd.DataFrame:
    rows = []
    for asset in (["2EU", "EUU"] if collide else ["2EU"]):
        for option_class, instrument_id in [("C", 1), ("P", 2)]:
            rows.append(
                {
                    "instrument_id": instrument_id + (10 if asset == "EUU" else 0),
                    "raw_symbol": f"{asset}-{option_class}",
                    "instrument_class": option_class,
                    "expiration": pd.Timestamp("2019-07-12T14:00:00Z"),
                    "underlying": "6EU9",
                    "asset": asset,
                    "strike_price": 1.13,
                }
            )
    return pd.DataFrame(rows)


class DiscoveryTests(unittest.TestCase):
    def test_ser_clocks_cover_dst(self) -> None:
        self.assertTrue(module.clock_valid(pd.Timestamp("2019-01-11T20:00:00Z")))
        self.assertTrue(module.clock_valid(pd.Timestamp("2019-07-12T14:00:00Z")))
        self.assertTrue(module.clock_valid(pd.Timestamp("2019-11-08T15:00:00Z")))
        self.assertFalse(module.clock_valid(pd.Timestamp("2019-07-12T19:00:00Z")))

    def test_overlap_skips_all_colliding_families(self) -> None:
        events, collisions, counts = module.discover_events(contracts(collide=True))
        self.assertEqual(len(collisions), 2)
        self.assertEqual(counts["collision_groups"], 1)
        self.assertEqual(len(module.eligible_events(events)), 0)

    def test_request_stops_at_decision(self) -> None:
        events, _, _ = module.discover_events(contracts())
        eligible = module.eligible_events(events)
        requests = module.statistics_requests(eligible)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["start"], "2019-07-12T00:00:00Z")
        self.assertEqual(requests[0]["end"], "2019-07-12T13:45:00Z")
        self.assertEqual(
            requests[0]["max_oi_reference_utc"], "2019-07-11T00:00:00Z"
        )

    def test_contract_catalog_collapses_instrument_id_remaps(self) -> None:
        frame = contracts()
        remap = frame.iloc[[0]].copy()
        remap["instrument_id"] = 99
        frame = pd.concat([frame, remap], ignore_index=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contracts.csv"
            module.write_contracts(path, frame)
            text = path.read_text(encoding="ascii")
        self.assertIn("1;99", text)

    def test_expiration_revision_is_latest_state_not_identity_drift(self) -> None:
        frame = contracts()
        frame["ts_recv"] = pd.Timestamp("2019-07-01T00:00:00Z")
        frame["ts_event"] = pd.Timestamp("2019-07-01T00:00:00Z")
        revised = frame.iloc[[0]].copy()
        revised["ts_recv"] = pd.Timestamp("2019-07-05T00:00:00Z")
        revised["ts_event"] = pd.Timestamp("2019-07-05T00:00:00Z")
        revised["expiration"] = pd.Timestamp("2019-07-12T17:00:00Z")
        combined = pd.concat([frame, revised], ignore_index=True)
        stable, unstable, expiration_revised = module.stable_contracts(combined)
        call = stable[stable["raw_symbol"] == "2EU-C"].iloc[0]
        self.assertEqual(unstable, [])
        self.assertEqual(expiration_revised, ["2EU-C"])
        self.assertEqual(call["expiration"], pd.Timestamp("2019-07-12T17:00:00Z"))


if __name__ == "__main__":
    unittest.main()
