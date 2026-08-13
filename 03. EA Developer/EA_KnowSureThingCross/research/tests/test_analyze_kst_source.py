from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).parents[1] / "analyze_kst_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_kst_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class KstSourceTests(unittest.TestCase):
    def test_constant_close_stays_zero_after_warmup(self) -> None:
        frame = pd.DataFrame({"close": np.full(100, 100.0)})
        values = MODULE.calculate_kst(frame)
        valid = values.dropna()
        self.assertGreater(len(valid), 0)
        self.assertTrue((valid["kst"] == 0.0).all())
        self.assertTrue((valid["signal"] == 0.0).all())

    def test_default_lengths_and_weights_are_literal(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("rcma1 + 2.0 * rcma2 + 3.0 * rcma3 + 4.0 * rcma4", source)
        self.assertIn("kst.rolling(9, min_periods=9).mean()", source)

    def test_sign_condition_is_part_of_cross(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("current_kst < 0.0", source)
        self.assertIn("current_kst > 0.0", source)

    def test_tlb_dependency_hash_is_frozen(self) -> None:
        self.assertEqual(MODULE.sha256_file(MODULE.TLB_PATH), MODULE.TLB_SHA256)

    def test_claim_precedes_source_read(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("claim_attempt()"), source.index("source = TLB.BASE.read_design()"))
        self.assertIn('"failure_context": context', source)

    def test_prereg_forbids_parameter_rescue_and_paid_data(self) -> None:
        prereg = (MODULE_PATH.parent / "HYP-KST-XAUUSD-M15-001_FROZEN_SOURCE_PREREG.md").read_text(encoding="utf-8")
        self.assertIn("No paid data", prereg)
        self.assertIn("Do not rescue", prereg)
        self.assertIn("10,15,20,30,10,10,10,15,9", prereg)


if __name__ == "__main__":
    unittest.main()
