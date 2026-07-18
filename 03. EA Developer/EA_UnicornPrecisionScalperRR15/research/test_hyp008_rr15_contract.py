#!/usr/bin/env python3
"""Contract tests for the one-change HYP-008 RR=1.50 replay."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "EA_UnicornPrecisionScalperRR15.mq5"
FROZEN = (
    ROOT.parent.parent
    / "EA_UnicornPrecisionScalper"
    / "research"
    / "source_snapshots"
    / "EA_UnicornPrecisionScalper_HYP-006_CB51EB2A.mq5"
)


class Hyp008RR15ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.frozen = FROZEN.read_text(encoding="utf-8")

    def test_identity_and_target_are_exact(self) -> None:
        self.assertIn('EA_NAME="EA_UnicornPrecisionScalperRR15"', self.source)
        self.assertIn('HYPOTHESIS_ID="HYP-UPS-XAU-M5-008"', self.source)
        self.assertIn('input double InpTargetRR=1.50;', self.source)

    def test_rr15_is_permitted_but_invalid_targets_still_fail_closed(self) -> None:
        self.assertIn('InpTargetRR<1.0', self.source)
        self.assertNotIn('InpTargetRR<2.0', self.source)

    def test_only_rr_and_operational_identity_differ_from_hyp006(self) -> None:
        normalized = self.source
        normalized = normalized.replace('#property version   "1.01"', '#property version   "1.00"')
        normalized = normalized.replace(
            'EA_NAME="EA_UnicornPrecisionScalperRR15"',
            'EA_NAME="EA_UnicornPrecisionScalper"',
        )
        normalized = normalized.replace(
            'HYPOTHESIS_ID="HYP-UPS-XAU-M5-008"',
            'HYPOTHESIS_ID="HYP-UPS-XAU-M5-006"',
        )
        normalized = normalized.replace(
            'input double InpTargetRR=1.50;',
            'input double InpTargetRR=2.50;',
        )
        normalized = normalized.replace('InpTargetRR<1.0', 'InpTargetRR<2.0')
        self.assertEqual(normalized.rstrip("\n"), self.frozen.rstrip("\n"))

    def test_frozen_signal_and_management_defaults_remain_unchanged(self) -> None:
        self.assertIn('input bool   InpUseEventAnchoredSweepState=false;', self.source)
        self.assertIn('input double InpBreakEvenR=1.00;', self.source)
        self.assertIn('input int    InpMaxHoldMinutes=90;', self.source)
        self.assertIn('input int    InpMaxSpreadPoints=35;', self.source)


if __name__ == "__main__":
    unittest.main()
