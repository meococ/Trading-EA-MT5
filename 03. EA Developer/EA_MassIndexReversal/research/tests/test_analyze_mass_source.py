import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "03. EA Developer" / "EA_MassIndexReversal" / "research" / "analyze_mass_source.py"
PREREG = ROOT / "03. EA Developer" / "EA_MassIndexReversal" / "research" / "HYP-MASS-EURUSD-M15-001_FROZEN_PREREG.md"
SPEC = importlib.util.spec_from_file_location("mass_source", SCRIPT)
MASS = importlib.util.module_from_spec(SPEC)
sys.modules["mass_source"] = MASS
SPEC.loader.exec_module(MASS)


def bulge_bars(direction=1, break_next=False, start="2016-01-04"):
    n = 180
    times = pd.date_range(start, periods=n, freq="15min")
    ranges = np.r_[np.ones(70), np.full(15, 10.0), np.ones(n - 85)]
    close = np.linspace(1.0, 2.0, n) if direction > 0 else np.linspace(2.0, 1.0, n)
    bars = pd.DataFrame({
        "time_server": times,
        "open": close,
        "high": close + ranges / 2.0,
        "low": close - ranges / 2.0,
        "close": close,
        "first_utc": times,
        "m1_rows": 1,
    })
    if break_next:
        bars.loc[97:, "time_server"] += pd.Timedelta(minutes=15)
    return bars


class MassSourceTests(unittest.TestCase):
    def test_ema_uses_exact_recursive_alpha(self):
        got = MASS.ema(np.array([1.0, 2.0, 3.0]), 9)
        self.assertTrue(np.allclose(got, [1.0, 1.2, 1.56], rtol=0, atol=1e-15))

    def test_bulge_completion_emits_one_directional_event(self):
        long_report, long_ledger = MASS.analyze(bulge_bars(direction=1))
        short_report, short_ledger = MASS.analyze(bulge_bars(direction=-1))
        self.assertEqual(long_report["events"]["executable"], 1)
        self.assertEqual(short_report["events"]["executable"], 1)
        self.assertEqual(json.loads(long_ledger)["direction"], "LONG")
        self.assertEqual(json.loads(short_ledger)["direction"], "SHORT")
        self.assertNotIn("high", json.loads(long_ledger))
        self.assertNotIn("close", json.loads(long_ledger))

    def test_exact_next_gap_consumes_event(self):
        report, ledger = MASS.analyze(bulge_bars(direction=1, break_next=True))
        self.assertEqual(report["events"]["raw"], 1)
        self.assertEqual(report["events"]["executable"], 0)
        self.assertEqual(report["events"]["gap_rejects"], 1)
        self.assertEqual(ledger, b"")

    def test_design_end_availability_is_rejected(self):
        start = MASS.DESIGN_TO - pd.Timedelta(minutes=97 * 15)
        report, ledger = MASS.analyze(bulge_bars(direction=1, start=start))
        self.assertEqual(report["events"]["raw"], 1)
        self.assertEqual(report["events"]["executable"], 0)
        self.assertEqual(report["events"]["boundary_rejects"], 1)
        self.assertEqual(ledger, b"")

    def test_invalid_mass_resets_armed_state(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            re.compile(r"if not math\.isfinite\(current_mass\):\s+armed = False\s+continue"),
        )

    def test_prereg_has_no_outcome_rescue(self):
        text = PREREG.read_text(encoding="utf-8")
        self.assertIn("strictly `>27`", text)
        self.assertIn("strictly `<26.5`", text)
        self.assertIn("Executable candidates `>=500`", text)
        self.assertIn("No economic/no-edge", text)
        for forbidden in ("profit target optimization", "best session", "best weekday"):
            self.assertNotIn(forbidden, text.lower())


if __name__ == "__main__":
    unittest.main()
