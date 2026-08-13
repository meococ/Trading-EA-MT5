from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).parents[1] / "analyze_tlb_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_tlb_source", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def m15_frame(closes: list[float]) -> pd.DataFrame:
    times = pd.date_range("2018-01-02", periods=len(closes), freq="15min", tz="UTC")
    return pd.DataFrame({
        "time_utc": times,
        "source_epoch": (times.astype("int64") // 1_000_000_000).astype("int64"),
        "open": closes,
        "high": closes,
        "low": closes,
        "close": closes,
    })


class ThreeLineBreakSourceTests(unittest.TestCase):
    def test_reversal_requires_three_prior_lines(self) -> None:
        raw, diagnostics = MODULE.extract_events(m15_frame([100, 101, 102, 103, 99, 98, 104, 105]))
        self.assertEqual(diagnostics["confirmed_lines"], 7)
        self.assertEqual([row["direction"] for row in raw], ["SHORT", "LONG"])
        self.assertTrue(all(row["exact_next"] for row in raw))
        self.assertEqual(raw[0]["three_line_lower"], 100.0)
        self.assertEqual(raw[1]["three_line_upper"], 103.0)

    def test_equality_and_inside_band_create_no_line(self) -> None:
        raw, diagnostics = MODULE.extract_events(m15_frame([100, 101, 102, 103, 103, 102, 101, 100]))
        self.assertEqual(raw, [])
        self.assertEqual(diagnostics["confirmed_lines"], 3)

    def test_gap_consumes_raw_reversal_without_executable_event(self) -> None:
        frame = m15_frame([100, 101, 102, 103, 99, 98])
        frame.loc[5, "time_utc"] = frame.loc[4, "time_utc"] + pd.Timedelta(minutes=30)
        frame.loc[5, "source_epoch"] = int(frame.loc[4, "source_epoch"]) + 1800
        raw, _ = MODULE.extract_events(frame)
        self.assertEqual(len(raw), 1)
        self.assertFalse(raw[0]["exact_next"])

    def test_exact_m15_aggregation_rejects_incomplete_bucket(self) -> None:
        times = pd.date_range("2018-01-02", periods=6, freq="5min", tz="UTC")
        frame = pd.DataFrame({
            "time_utc": times,
            "source_epoch": (times.astype("int64") // 1_000_000_000).astype("int64"),
            "open": [1.0] * 6, "high": [2.0] * 6, "low": [0.5] * 6,
            "close": [1.5] * 6,
        }).drop(index=4).reset_index(drop=True)
        m15, diagnostics = MODULE.aggregate_m15(frame)
        self.assertEqual(len(m15), 1)
        self.assertEqual(diagnostics["rejected_m15_buckets"], 1)

    def test_shared_validator_hash_is_frozen(self) -> None:
        self.assertEqual(MODULE.sha256_file(MODULE.BASE_PATH), MODULE.BASE_SHA256)

    def test_claim_precedes_bound_reads_and_failure_is_structured(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index("claim_attempt()"), source.index("initial = frozen_hashes()"))
        self.assertIn('"failure_context": context', source)

    def test_prereg_forbids_rescue_and_paid_data(self) -> None:
        prereg = (MODULE_PATH.parent / "HYP-TLB-XAUUSD-M15-001_FROZEN_SOURCE_PREREG.md").read_text(encoding="utf-8")
        self.assertIn("No paid data is used", prereg)
        self.assertIn("Do not rescue", prereg)
        self.assertIn("last `min(3,n)` confirmed", prereg)


if __name__ == "__main__":
    unittest.main()
