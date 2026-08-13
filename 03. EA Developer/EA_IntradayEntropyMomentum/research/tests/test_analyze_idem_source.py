from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


PATH = Path(__file__).resolve().parents[1] / "analyze_idem_source.py"
SPEC = importlib.util.spec_from_file_location("idem_source", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def complete_day(closes: np.ndarray) -> pd.DataFrame:
    times = pd.date_range("2020-01-02", periods=192, freq="5min", tz="UTC")
    epoch = (times.astype("int64") // 10**9).to_numpy(dtype=np.int64)
    return pd.DataFrame({
        "symbol": ["XAUUSD"] * 192,
        "timeframe": ["M5"] * 192,
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s"),
        "time_utc": times,
        "utc_ambiguous": [False] * 192,
        "open": closes,
        "high": closes + 0.1,
        "low": closes - 0.1,
        "close": closes,
        "tick_volume": 10,
    })


class IdemSourceTests(unittest.TestCase):
    def test_one_sided_path_has_zero_entropy(self) -> None:
        closes = 100.0 + np.arange(192) * 0.01
        frame, _ = MODULE.DPMO.BASE.validate_frame(complete_day(closes))
        measure = MODULE.measure_session(frame)
        self.assertIsNotNone(measure)
        self.assertEqual(measure["entropy"], 0.0)
        self.assertGreater(measure["session_return"], 0.0)

    def test_balanced_signs_have_high_entropy(self) -> None:
        returns = np.array([0.001 if i % 2 == 0 else -0.001 for i in range(191)])
        closes = np.r_[100.0, 100.0 * np.exp(np.cumsum(returns))]
        frame, _ = MODULE.DPMO.BASE.validate_frame(complete_day(closes))
        measure = MODULE.measure_session(frame)
        self.assertIsNotNone(measure)
        self.assertGreater(measure["entropy"], 0.69)

    def test_current_is_excluded_and_strictly_below_median(self) -> None:
        history = [0.5] * 20
        self.assertEqual(MODULE.select_direction({"entropy": 0.49, "session_return": 0.01}, history), "LONG")
        self.assertEqual(MODULE.select_direction({"entropy": 0.49, "session_return": -0.01}, history), "SHORT")
        self.assertIsNone(MODULE.select_direction({"entropy": 0.5, "session_return": 0.01}, history))
        self.assertIsNone(MODULE.select_direction({"entropy": 0.1, "session_return": 0.01}, history[:19]))

    def test_zero_session_return_does_not_emit(self) -> None:
        self.assertIsNone(MODULE.select_direction({"entropy": 0.1, "session_return": 0.0}, [0.5] * 20))

    def test_frozen_dependency_hash(self) -> None:
        self.assertEqual(MODULE.sha256_file(MODULE.DPMO_PATH), MODULE.DPMO_SHA256)

    def test_claim_precedes_design_read(self) -> None:
        source = PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("claim_attempt()"), source.index("source = DPMO.BASE.read_design()"))


if __name__ == "__main__":
    unittest.main()
