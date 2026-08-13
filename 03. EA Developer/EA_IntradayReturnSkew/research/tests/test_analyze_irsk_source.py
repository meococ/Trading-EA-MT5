from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_irsk_source.py"
SPEC = importlib.util.spec_from_file_location("irsk_source", MODULE_PATH)
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


class IrskSourceTests(unittest.TestCase):
    def test_positive_session_negative_skew_emits_short(self) -> None:
        returns = [0.001] * 190 + [-0.05]
        measure = MODULE.measure_session(frame_from_returns(returns))
        self.assertGreater(measure["session_return"], 0)
        self.assertLess(measure["realized_skewness"], 0)
        self.assertEqual(MODULE.select_direction(measure), "SHORT")

    def test_negative_session_positive_skew_emits_long(self) -> None:
        returns = [-0.001] * 190 + [0.05]
        measure = MODULE.measure_session(frame_from_returns(returns))
        self.assertLess(measure["session_return"], 0)
        self.assertGreater(measure["realized_skewness"], 0)
        self.assertEqual(MODULE.select_direction(measure), "LONG")

    def test_population_moment_formula(self) -> None:
        returns = [0.001] * 188 + [-0.01, 0.02, -0.03]
        measure = MODULE.measure_session(frame_from_returns(returns))
        values = np.asarray(returns)
        centered = values - values.mean()
        expected = np.mean(centered ** 3) / np.mean(centered ** 2) ** 1.5
        self.assertAlmostEqual(measure["realized_skewness"], expected, places=10)

    def test_zero_variance_is_invalid(self) -> None:
        self.assertIsNone(MODULE.measure_session(frame_from_returns([0.0] * 191)))

    def test_agreement_and_equalities_emit_nothing(self) -> None:
        for measure in (
            {"session_return": 1.0, "realized_skewness": 1.0},
            {"session_return": -1.0, "realized_skewness": -1.0},
            {"session_return": 0.0, "realized_skewness": 1.0},
            {"session_return": 1.0, "realized_skewness": 0.0},
        ):
            self.assertIsNone(MODULE.select_direction(measure))

    def test_ledger_has_no_outcome_fields(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8").lower()
        for forbidden in ("future_return", "post_event", "pnl", "profit_factor", "target_hit"):
            self.assertNotIn(forbidden, text)

    def test_attempt_root_absent_before_scan(self) -> None:
        self.assertFalse(MODULE.ATTEMPT_ROOT.exists())


if __name__ == "__main__":
    unittest.main()
