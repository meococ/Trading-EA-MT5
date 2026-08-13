from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).parents[1] / "analyze_isds_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_isds_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def complete_day(closes: np.ndarray) -> pd.DataFrame:
    times = pd.date_range("2018-01-02", periods=193, freq="5min", tz="UTC")
    epoch = (times.astype("int64") // 1_000_000_000).astype("int64")
    return pd.DataFrame({
        "symbol": ["XAUUSD"] * 193, "timeframe": ["M5"] * 193,
        "source_epoch": epoch, "time_server": pd.to_datetime(epoch, unit="s"),
        "time_utc": times, "utc_ambiguous": [False] * 193,
        "open": closes, "high": closes + 0.1, "low": closes - 0.1,
        "close": closes, "tick_volume": np.full(193, 100.0),
    })


class IsdsSourceTests(unittest.TestCase):
    def test_persistent_positive_recent_maps_long(self) -> None:
        increments = 0.10 + 0.05 * np.sin(np.linspace(0.0, 4.0 * np.pi, 192))
        closes = np.r_[100.0, 100.0 + np.cumsum(increments)]
        frame, _ = MODULE.DPMO.BASE.validate_frame(complete_day(closes))
        raw, diagnostics = MODULE.extract_events(frame)
        self.assertEqual(diagnostics["complete_sessions"], 1)
        self.assertEqual([row["direction"] for row in raw], ["LONG"])
        self.assertGreater(raw[0]["lag1_return_correlation"], 0.0)

    def test_antipersistent_positive_recent_maps_short(self) -> None:
        increments = np.tile([-0.10, 0.20], 96)
        increments[-6:] = np.array([-0.05, 0.10, -0.05, 0.10, -0.05, 0.10])
        closes = np.r_[100.0, 100.0 + np.cumsum(increments)]
        frame, _ = MODULE.DPMO.BASE.validate_frame(complete_day(closes))
        raw, _ = MODULE.extract_events(frame)
        self.assertEqual([row["direction"] for row in raw], ["SHORT"])
        self.assertLess(raw[0]["lag1_return_correlation"], 0.0)
        self.assertGreater(raw[0]["recent_30m_return"], 0.0)

    def test_flat_day_fails_measurement(self) -> None:
        frame, _ = MODULE.DPMO.BASE.validate_frame(complete_day(np.full(193, 100.0)))
        raw, diagnostics = MODULE.extract_events(frame)
        self.assertEqual(raw, [])
        self.assertEqual(diagnostics["valid_measurements"], 0)

    def test_dependency_hash_is_frozen(self) -> None:
        self.assertEqual(MODULE.sha256_file(MODULE.DPMO_PATH), MODULE.DPMO_SHA256)

    def test_claim_precedes_source_read(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("claim_attempt()"), source.index("source = DPMO.BASE.read_design()"))
        self.assertIn('"failure_context": context', source)

    def test_prereg_closes_paid_and_posthoc_paths(self) -> None:
        prereg = (MODULE_PATH.parent / "HYP-ISDS-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md").read_text(encoding="utf-8")
        self.assertIn("no paid data", prereg.lower())
        self.assertIn("Do not rescue", prereg)
        self.assertIn("lag-1 correlation", prereg)


if __name__ == "__main__":
    unittest.main()
