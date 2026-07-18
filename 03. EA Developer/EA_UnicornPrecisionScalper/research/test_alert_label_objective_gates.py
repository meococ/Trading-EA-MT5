from __future__ import annotations

import unittest

from audit_alert_label_objective_gates import pivots


class AlertLabelObjectiveGateTests(unittest.TestCase):
    def test_strict_pivot_requires_two_sided_confirmation(self) -> None:
        lows = [5, 4, 3, 4, 5, 4, 2, 4, 5]
        bars = [{"l": value, "h": 10 - value} for value in lows]
        self.assertEqual(pivots(bars, "l", high=False), [2, 6])


if __name__ == "__main__":
    unittest.main()

