"""Contract-only tests for HYP002 statistics quoting."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "quote_cme6e_option_pin_design_statistics_002.py"
)
SPEC = importlib.util.spec_from_file_location("option_pin_quote_002", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def valid_request() -> dict[str, object]:
    return {
        "schema_version": "cme6e_option_pin_statistics_request.v2",
        "hypothesis_id": module.HYPOTHESIS_ID,
        "campaign_id": module.CAMPAIGN_ID,
        "request_id": "REQ001",
        "event_id": "EVT001",
        "dataset": "GLBX.MDP3",
        "schema": "statistics",
        "symbols": ["2EU.OPT"],
        "stype_in": "parent",
        "stype_out": "instrument_id",
        "start": "2019-07-12T00:00:00Z",
        "end": "2019-07-12T13:45:00Z",
        "definition_selection": "EARLIEST_VALID_EXPIRY_DECISION_FIXED_POINT",
        "missing_oi_policy": "UNKNOWN_EVENT_INVALID",
    }


class QuoteContractTests(unittest.TestCase):
    def write_requests(self, values: list[dict[str, object]]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "requests.jsonl"
        path.write_text(
            "".join(json.dumps(value) + "\n" for value in values),
            encoding="ascii",
        )
        return path

    def test_accepts_exact_hyp002_contract(self) -> None:
        requests = module.load_requests(self.write_requests([valid_request()]))
        self.assertEqual(len(requests), 1)

    def test_rejects_zero_completion(self) -> None:
        request = valid_request()
        request["missing_oi_policy"] = "ZERO_COMPLETE"
        with self.assertRaises(module.QuoteError):
            module.load_requests(self.write_requests([request]))

    def test_rejects_duplicate_request_ids(self) -> None:
        request = valid_request()
        with self.assertRaises(module.QuoteError):
            module.load_requests(self.write_requests([request, request]))


if __name__ == "__main__":
    unittest.main()

