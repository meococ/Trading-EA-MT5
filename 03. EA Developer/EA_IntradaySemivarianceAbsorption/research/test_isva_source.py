from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).with_name("analyze_isva_source.py")
SPEC = importlib.util.spec_from_file_location("analyze_isva_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def day_frame(day: str, direction: str = "LONG", include_next: bool = True) -> pd.DataFrame:
    periods = 193 if include_next else 192
    utc = pd.date_range(f"{day}T00:00:00Z", periods=periods, freq="5min")
    if direction == "LONG":
        close = np.concatenate(([100.0, 90.0], np.linspace(90.1, 101.0, periods - 2)))
    elif direction == "SHORT":
        close = np.concatenate(([100.0, 110.0], np.linspace(109.9, 99.0, periods - 2)))
    else:
        close = np.full(periods, 100.0)
    epoch = (utc.astype("int64") // 1_000_000_000).to_numpy(dtype=np.int64)
    return pd.DataFrame({
        "symbol": ["XAUUSD"] * periods,
        "timeframe": ["M5"] * periods,
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s"),
        "time_utc": utc,
        "utc_ambiguous": [False] * periods,
        "open": close,
        "high": close + 0.2,
        "low": close - 0.2,
        "close": close,
        "tick_volume": np.full(periods, 100.0),
    })


class IsvaSourceTests(unittest.TestCase):
    def test_long_joint_state(self) -> None:
        frame = day_frame("2018-01-02", "LONG")
        valid, _ = MODULE.validate_frame(frame)
        raw, diagnostics = MODULE.extract_events(valid)
        self.assertEqual(diagnostics["complete_sessions"], 1)
        self.assertEqual(len(raw), 1)
        self.assertEqual(raw[0]["direction"], "LONG")
        self.assertGreater(raw[0]["rvminus"], raw[0]["rvplus"])
        self.assertGreaterEqual(raw[0]["clv"], MODULE.HIGH_CLV)
        self.assertTrue(raw[0]["exact_next"])

    def test_short_joint_state(self) -> None:
        frame = day_frame("2018-01-03", "SHORT")
        valid, _ = MODULE.validate_frame(frame)
        raw, _ = MODULE.extract_events(valid)
        self.assertEqual([row["direction"] for row in raw], ["SHORT"])
        self.assertGreater(raw[0]["rvplus"], raw[0]["rvminus"])
        self.assertLessEqual(raw[0]["clv"], MODULE.LOW_CLV)

    def test_incomplete_session_is_consumed_without_signal(self) -> None:
        frame = day_frame("2018-01-04", "LONG").drop(index=80).reset_index(drop=True)
        raw, diagnostics = MODULE.extract_events(frame.assign(utc_date=frame["time_utc"].dt.date))
        self.assertEqual(raw, [])
        self.assertEqual(diagnostics["complete_sessions"], 0)

    def test_missing_exact_1600_row_marks_raw_nonexecutible(self) -> None:
        frame = day_frame("2018-01-05", "LONG", include_next=False)
        valid, _ = MODULE.validate_frame(frame)
        raw, _ = MODULE.extract_events(valid)
        self.assertEqual(len(raw), 1)
        self.assertFalse(raw[0]["exact_next"])

    def test_flat_path_is_invalid_not_directional(self) -> None:
        frame = day_frame("2018-01-08", "FLAT")
        session = frame.iloc[:192].copy()
        self.assertIsNotNone(MODULE.session_measure(session))
        valid, _ = MODULE.validate_frame(frame)
        raw, _ = MODULE.extract_events(valid)
        self.assertEqual(raw, [])

    def test_row_floor_is_reported_not_raised(self) -> None:
        frame = day_frame("2018-01-09", "LONG")
        valid, observed = MODULE.validate_frame(frame)
        report, _ = MODULE.analyze(valid, observed)
        self.assertEqual(report["design_rows"], 193)
        self.assertFalse(report["gates"]["design_rows_gte_300000"])

    def test_claim_precedes_bound_reads_and_failure_is_structured(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("claim_attempt()"), source.index("initial = frozen_hashes()"))
        self.assertIn('"failure_context": context', source)
        self.assertIn('"gate_results": {}', source)

    def test_prereg_freezes_joint_not_single_factor(self) -> None:
        text = Path(__file__).with_name("HYP-ISVA-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md").read_text(encoding="utf-8")
        self.assertIn("RVminus>RVplus", text)
        self.assertIn("CLV>=2/3", text)
        self.assertIn("No post-16:00 price", text)


if __name__ == "__main__":
    unittest.main()
