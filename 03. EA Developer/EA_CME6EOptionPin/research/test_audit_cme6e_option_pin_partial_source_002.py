"""Arithmetic tests for fail-only HYP002 partial source audit."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "audit_cme6e_option_pin_partial_source_002.py"
)
SPEC = importlib.util.spec_from_file_location("option_pin_partial_audit_002", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MonotonicVerdictTests(unittest.TestCase):
    def test_partial_data_can_kill_when_failure_budget_is_exceeded(self) -> None:
        result = module.monotonic_verdict(
            planned_events=516,
            acquired_events=291,
            invalid_acquired_events=26,
        )
        self.assertEqual(result["required_valid_events"], 491)
        self.assertEqual(result["maximum_invalid_events"], 25)
        self.assertTrue(result["source_validity_gate_mathematically_impossible"])
        self.assertEqual(result["verdict"], "KILL_SOURCE_DESIGN_MONOTONIC_PARTIAL")

    def test_partial_data_never_passes_even_when_all_acquired_are_valid(self) -> None:
        result = module.monotonic_verdict(
            planned_events=516,
            acquired_events=291,
            invalid_acquired_events=0,
        )
        self.assertFalse(result["source_validity_gate_mathematically_impossible"])
        self.assertEqual(
            result["verdict"], "ACQUISITION_INCOMPLETE_NO_SOURCE_VERDICT"
        )

    def test_exact_failure_budget_is_not_enough_to_kill(self) -> None:
        result = module.monotonic_verdict(
            planned_events=516,
            acquired_events=291,
            invalid_acquired_events=25,
        )
        self.assertFalse(result["source_validity_gate_mathematically_impossible"])


if __name__ == "__main__":
    unittest.main()
