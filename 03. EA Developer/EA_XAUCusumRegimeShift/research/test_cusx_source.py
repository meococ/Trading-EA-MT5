from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).with_name("analyze_cusx_source.py")
SPEC = importlib.util.spec_from_file_location("analyze_cusx_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def synthetic_frame(rows: int = 180, step: float = 0.12) -> pd.DataFrame:
    epoch = np.arange(rows, dtype=np.int64) * 300 + MODULE.START_EPOCH
    close = 1300.0 + np.arange(rows, dtype=float) * step
    utc = pd.to_datetime(epoch - 7200, unit="s", utc=True)
    return pd.DataFrame({
        "symbol": ["XAUUSD"] * rows,
        "timeframe": ["M5"] * rows,
        "source_epoch": epoch,
        "time_server": pd.to_datetime(epoch, unit="s"),
        "time_utc": utc,
        "utc_ambiguous": [False] * rows,
        "open": close - 0.02,
        "high": close + 0.08,
        "low": close - 0.08,
        "close": close,
        "tick_volume": np.full(rows, 100.0),
    })


class CusxSourceTests(unittest.TestCase):
    def test_atr_excludes_current_true_range(self) -> None:
        frame = synthetic_frame(80, step=0.02)
        baseline = MODULE.compute_atr48_prev(frame)
        changed = frame.copy()
        changed.loc[60, "high"] += 100.0
        current_changed = MODULE.compute_atr48_prev(changed)
        self.assertAlmostEqual(float(baseline.iloc[60]), float(current_changed.iloc[60]))
        self.assertGreater(float(current_changed.iloc[61]), float(baseline.iloc[61]))

    def test_positive_drift_emits_one_long_until_opposite_state(self) -> None:
        frame = synthetic_frame(180, step=0.12)
        raw, diagnostics = MODULE.extract_events(frame)
        longs = [row for row in raw if row["direction"] == "LONG"]
        shorts = [row for row in raw if row["direction"] == "SHORT"]
        self.assertEqual(len(longs), 1)
        self.assertEqual(len(shorts), 0)
        self.assertEqual(longs[0]["prior_polarity"], 0)
        self.assertGreaterEqual(longs[0]["splus_at_hit"], MODULE.THRESHOLD)
        self.assertEqual(diagnostics["direction_conflicts"], 0)

    def test_gap_resets_polarity_and_allows_fresh_same_direction_hit(self) -> None:
        frame = synthetic_frame(260, step=0.12)
        frame.loc[150:, "source_epoch"] += 3600
        frame.loc[150:, "time_server"] += pd.Timedelta(hours=1)
        frame.loc[150:, "time_utc"] += pd.Timedelta(hours=1)
        raw, diagnostics = MODULE.extract_events(frame)
        self.assertGreaterEqual(diagnostics["gap_resets"], 1)
        self.assertEqual([row["direction"] for row in raw], ["LONG", "LONG"])
        self.assertEqual(raw[1]["prior_polarity"], 0)

    def test_negative_drift_emits_one_short(self) -> None:
        frame = synthetic_frame(180, step=-0.12)
        raw, _ = MODULE.extract_events(frame)
        self.assertEqual([row["direction"] for row in raw], ["SHORT"])
        self.assertLessEqual(raw[0]["sminus_at_hit"], -MODULE.THRESHOLD)

    def test_validate_frame_records_row_and_contract_results(self) -> None:
        frame = synthetic_frame(80, step=0.02)
        valid, observed = MODULE.validate_frame(frame)
        self.assertEqual(len(valid), 80)
        self.assertEqual(observed["design_rows"], 80)
        self.assertTrue(observed["chronology_strict"])
        self.assertTrue(observed["geometry_all_valid"])

    def test_row_floor_is_report_gate_not_validator_exception(self) -> None:
        frame = synthetic_frame(180, step=0.02)
        valid, observed = MODULE.validate_frame(frame)
        report, _ = MODULE.analyze(valid, observed)
        self.assertFalse(report["gates"]["design_rows_gte_300000"])
        self.assertEqual(report["design_rows"], 180)

    def test_failure_terminal_contract_contains_structured_context(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"failure_context": context', source)
        self.assertIn('"observed": {}', source)
        self.assertIn('"gate_results": {}', source)
        self.assertLess(source.index("claim_attempt()"), source.index("initial_hashes = frozen_input_hashes()"))

    def test_frozen_prereg_has_no_outcome_fields_in_ledger(self) -> None:
        prereg = Path(__file__).with_name("HYP-CUSX-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md").read_text(encoding="utf-8")
        self.assertIn("No post-decision price is permitted", prereg)
        self.assertIn("h=3.00", prereg)
        self.assertNotIn("profit_factor", json.dumps(MODULE.extract_events(synthetic_frame())[0]))


if __name__ == "__main__":
    unittest.main()
