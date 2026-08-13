from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_ivrl_source.py"
SPEC = importlib.util.spec_from_file_location("ivrl_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def frame_from_returns(returns: list[float]) -> pd.DataFrame:
    closes = [100.0]
    for value in returns:
        closes.append(closes[-1] * float(np.exp(value)))
    times = pd.date_range("2020-01-02T00:00:00Z", periods=192, freq="5min")
    return pd.DataFrame({
        "time_utc": times,
        "source_epoch": (times.astype("int64") // 10**9).astype("int64"),
        "utc_date": times.date,
        "open": closes,
        "high": [x + 0.1 for x in closes],
        "low": [x - 0.1 for x in closes],
        "close": closes,
        "tick_volume": [10.0] * 192,
    })


class IvrlSourceTests(unittest.TestCase):
    def test_late_variance_positive_displacement_emits_long(self) -> None:
        measure = MODULE.measure_session(frame_from_returns([0.001] * 95 + [0.003] * 96))
        self.assertGreater(measure["late_mean_squared_return"], measure["early_mean_squared_return"])
        self.assertGreater(measure["late_session_return"], 0.0)
        self.assertEqual(MODULE.select_direction(measure), "LONG")

    def test_late_variance_negative_displacement_emits_short(self) -> None:
        measure = MODULE.measure_session(frame_from_returns([0.001] * 95 + [-0.003] * 96))
        self.assertGreater(measure["late_mean_squared_return"], measure["early_mean_squared_return"])
        self.assertLess(measure["late_session_return"], 0.0)
        self.assertEqual(MODULE.select_direction(measure), "SHORT")

    def test_exact_split_and_formula(self) -> None:
        returns = np.asarray([0.001 + i * 1e-6 for i in range(191)])
        measure = MODULE.measure_session(frame_from_returns(returns.tolist()))
        self.assertEqual(measure["early_return_count"], 95)
        self.assertEqual(measure["late_return_count"], 96)
        self.assertAlmostEqual(measure["early_mean_squared_return"], float(np.mean(returns[:95] ** 2)), places=15)
        self.assertAlmostEqual(measure["late_mean_squared_return"], float(np.mean(returns[95:] ** 2)), places=15)
        self.assertAlmostEqual(measure["late_session_return"], float(np.sum(returns[95:])), places=12)

    def test_equal_or_early_dominant_variance_emits_nothing(self) -> None:
        for measure in (
            {"early_mean_squared_return": 1.0, "late_mean_squared_return": 1.0, "late_session_return": 1.0},
            {"early_mean_squared_return": 2.0, "late_mean_squared_return": 1.0, "late_session_return": -1.0},
            {"early_mean_squared_return": 0.0, "late_mean_squared_return": 1.0, "late_session_return": 0.0},
        ):
            self.assertIsNone(MODULE.select_direction(measure))

    def test_ledger_has_no_outcome_fields(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8").lower()
        for forbidden in ("future_return", "post_event", "pnl", "profit_factor", "target_hit"):
            self.assertNotIn(forbidden, text)

    def test_source_attempt_is_terminal_after_sole_scan(self) -> None:
        self.assertTrue(MODULE.START_PATH.exists())
        self.assertTrue(MODULE.RECEIPT_PATH.exists())
        self.assertTrue(MODULE.TERMINAL_PATH.exists())


if __name__ == "__main__":
    unittest.main()
