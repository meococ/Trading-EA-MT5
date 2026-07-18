#!/usr/bin/env python3
"""Focused tests for the no-outcome signal-identity audit."""

from __future__ import annotations

import unittest

import numpy as np

from audit_unicorn_signal_identity import invalidated_through_decision


class SignalIdentityAuditTests(unittest.TestCase):
    def test_invalidation_includes_middle_and_decision_bars(self) -> None:
        rates = np.zeros(6, dtype=[("close", "f8")])
        rates[1]["close"] = 99.0
        self.assertTrue(invalidated_through_decision(rates, 0, 1, 1, 100.0))

    def test_non_breaching_closed_bars_preserve_sweep(self) -> None:
        rates = np.zeros(6, dtype=[("close", "f8")])
        rates[1:4]["close"] = [100.5, 101.0, 102.0]
        self.assertFalse(invalidated_through_decision(rates, 0, 1, 1, 100.0))


if __name__ == "__main__":
    unittest.main()
