from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_idov_source.py"
SPEC = importlib.util.spec_from_file_location("idov_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def session(closes: list[float], volumes: list[float]) -> pd.DataFrame:
    times = pd.date_range("2020-01-02T00:00:00Z", periods=192, freq="5min")
    return pd.DataFrame({
        "time_utc": times,
        "source_epoch": (times.astype("int64") // 10**9).astype("int64"),
        "utc_date": times.date,
        "open": closes,
        "high": [x + 0.1 for x in closes],
        "low": [x - 0.1 for x in closes],
        "close": closes,
        "tick_volume": volumes,
    })


class IdovSourceTests(unittest.TestCase):
    def test_positive_price_negative_flow_emits_short(self) -> None:
        closes = [100.0] + [99.0] * 191
        closes[-1] = 101.0
        volumes = [10.0] * 192
        volumes[1] = 1000.0
        measure = MODULE.measure_session(session(closes, volumes))
        self.assertIsNotNone(measure)
        self.assertGreater(measure["session_return"], 0)
        self.assertLess(measure["signed_tick_volume_flow"], 0)
        self.assertEqual(MODULE.select_direction(measure), "SHORT")

    def test_negative_price_positive_flow_emits_long(self) -> None:
        closes = [100.0] * 192
        closes[1] = 101.0
        closes[-1] = 99.0
        volumes = [10.0] * 192
        volumes[1] = 1000.0
        measure = MODULE.measure_session(session(closes, volumes))
        self.assertIsNotNone(measure)
        self.assertLess(measure["session_return"], 0)
        self.assertGreater(measure["signed_tick_volume_flow"], 0)
        self.assertEqual(MODULE.select_direction(measure), "LONG")

    def test_agreement_and_equalities_emit_nothing(self) -> None:
        for measure in (
            {"session_return": 1.0, "signed_tick_volume_flow": 1.0},
            {"session_return": -1.0, "signed_tick_volume_flow": -1.0},
            {"session_return": 0.0, "signed_tick_volume_flow": 1.0},
            {"session_return": 1.0, "signed_tick_volume_flow": 0.0},
        ):
            self.assertIsNone(MODULE.select_direction(measure))

    def test_current_volume_belongs_to_current_close_change(self) -> None:
        closes = [100.0] + [99.0] * 191
        volumes = [1.0] * 192
        volumes[0] = 9999.0
        volumes[1] = 7.0
        measure = MODULE.measure_session(session(closes, volumes))
        self.assertEqual(measure["signed_tick_volume_flow"], -7.0)

    def test_ledger_mapping_contains_no_outcome_fields(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in ("future_return", "post_event", "pnl", "profit_factor", "target_hit"):
            self.assertNotIn(forbidden, text.lower())
        self.assertIn('"decision_year": int(availability.year)', text)

    def test_attempt_root_is_absent_before_the_scan(self) -> None:
        self.assertFalse(MODULE.ATTEMPT_ROOT.exists())


if __name__ == "__main__":
    unittest.main()
