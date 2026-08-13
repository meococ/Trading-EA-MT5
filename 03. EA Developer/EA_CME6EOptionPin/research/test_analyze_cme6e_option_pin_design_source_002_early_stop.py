from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "analyze_cme6e_option_pin_design_source_002_early_stop.py"
)
SPEC = importlib.util.spec_from_file_location("hyp002_early_stop", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EarlyStopMathTests(unittest.TestCase):
    def test_516_events_at_95_percent_becomes_impossible_at_26_invalid(self) -> None:
        self.assertEqual(
            MODULE.minimum_invalid_for_impossible_gate(516, 0.95),
            26,
        )
        self.assertGreaterEqual((516 - 25) / 516, 0.95)
        self.assertLess((516 - 26) / 516, 0.95)

    def test_invalid_gate_inputs_fail_closed(self) -> None:
        for total, gate in ((0, 0.95), (516, 0.0), (516, 1.1)):
            with self.assertRaises(ValueError):
                MODULE.minimum_invalid_for_impossible_gate(total, gate)


if __name__ == "__main__":
    unittest.main()
