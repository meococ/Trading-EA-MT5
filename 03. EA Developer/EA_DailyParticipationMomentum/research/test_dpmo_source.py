from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).with_name("analyze_dpmo_source.py")
SPEC = importlib.util.spec_from_file_location("analyze_dpmo_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def build_days(last_direction: str = "LONG", last_volume: float = 200.0) -> pd.DataFrame:
    frames = []
    for index, day in enumerate(pd.bdate_range("2018-01-02", periods=21)):
        utc = pd.date_range(day.tz_localize("UTC"), periods=193, freq="5min")
        if index == 20 and last_direction == "SHORT":
            close = np.linspace(101.0, 100.0, 193)
        else:
            close = np.linspace(100.0, 101.0, 193)
        volume = last_volume if index == 20 else 100.0
        epoch = (utc.astype("int64") // 1_000_000_000).to_numpy(dtype=np.int64)
        frames.append(pd.DataFrame({
            "symbol": ["XAUUSD"] * 193,
            "timeframe": ["M5"] * 193,
            "source_epoch": epoch,
            "time_server": pd.to_datetime(epoch, unit="s"),
            "time_utc": utc,
            "utc_ambiguous": [False] * 193,
            "open": close,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "tick_volume": np.full(193, volume),
        }))
    return pd.concat(frames, ignore_index=True)


class DpmoSourceTests(unittest.TestCase):
    def test_prior20_median_excludes_current_and_emits_long(self) -> None:
        frame, _ = MODULE.BASE.validate_frame(build_days("LONG", 200.0))
        raw, diagnostics = MODULE.extract_events(frame)
        self.assertEqual(diagnostics["complete_sessions"], 21)
        self.assertEqual(len(raw), 1)
        self.assertEqual(raw[0]["direction"], "LONG")
        self.assertEqual(raw[0]["prior20_median_activity"], 19200.0)
        self.assertEqual(raw[0]["activity"], 38400.0)
        self.assertTrue(raw[0]["exact_next"])

    def test_negative_return_emits_short(self) -> None:
        frame, _ = MODULE.BASE.validate_frame(build_days("SHORT", 200.0))
        raw, _ = MODULE.extract_events(frame)
        self.assertEqual([row["direction"] for row in raw], ["SHORT"])
        self.assertLess(raw[0]["session_return"], 0.0)

    def test_activity_equality_does_not_emit(self) -> None:
        frame, _ = MODULE.BASE.validate_frame(build_days("LONG", 100.0))
        raw, _ = MODULE.extract_events(frame)
        self.assertEqual(raw, [])

    def test_incomplete_current_session_does_not_enter_history_or_emit(self) -> None:
        frame = build_days("LONG", 200.0)
        last_day = frame["time_utc"].dt.date.max()
        drop_index = frame[(frame["time_utc"].dt.date == last_day) & (frame["time_utc"].dt.hour == 8)].index[0]
        frame = frame.drop(index=drop_index).reset_index(drop=True)
        frame, _ = MODULE.BASE.validate_frame(frame)
        raw, diagnostics = MODULE.extract_events(frame)
        self.assertEqual(diagnostics["complete_sessions"], 20)
        self.assertEqual(raw, [])

    def test_report_keeps_row_floor_as_gate(self) -> None:
        frame, observed = MODULE.BASE.validate_frame(build_days())
        report, _ = MODULE.analyze(frame, observed)
        self.assertFalse(report["gates"]["design_rows_gte_300000"])
        self.assertEqual(report["parameters"]["activity_lookback_sessions"], 20)

    def test_shared_validator_hash_is_literal_and_current(self) -> None:
        self.assertEqual(MODULE.sha256_file(MODULE.BASE_PATH), MODULE.BASE_SHA256)

    def test_claim_before_bound_reads_and_structured_failure(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("claim_attempt()"), source.index("initial = frozen_hashes()"))
        self.assertIn('"failure_context": context', source)
        self.assertIn('"gate_results": {}', source)

    def test_prereg_forbids_single_factor_emission(self) -> None:
        prereg = Path(__file__).with_name("HYP-DPMO-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md").read_text(encoding="utf-8")
        self.assertIn("Current activity is excluded", prereg)
        self.assertIn("neither volume nor return", prereg)
        self.assertIn("No post-16:00 price", prereg)


if __name__ == "__main__":
    unittest.main()
