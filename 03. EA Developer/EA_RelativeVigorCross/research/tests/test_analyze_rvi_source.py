import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "03. EA Developer" / "EA_RelativeVigorCross" / "research" / "analyze_rvi_source.py"
SPEC = importlib.util.spec_from_file_location("rvi_source", SCRIPT)
RVI = importlib.util.module_from_spec(SPEC)
sys.modules["rvi_source"] = RVI
SPEC.loader.exec_module(RVI)


def frame(start="2016-01-04", count=24):
    t = pd.date_range(start, periods=count, freq="1h")
    x = np.linspace(1.0, 1.1, count)
    return pd.DataFrame({"time_server": t, "time_utc": t, "open": x, "high": x + 0.01, "low": x - 0.01, "close": x + 0.001})


def fake_lines(count, direction):
    main = np.zeros(count); signal = np.zeros(count)
    if direction == "LONG":
        main[15], signal[15], main[16], signal[16] = -0.2, -0.1, -0.05, -0.1
    else:
        main[15], signal[15], main[16], signal[16] = 0.2, 0.1, 0.05, 0.1
    return main, signal


class RviSourceTests(unittest.TestCase):
    def test_metaquotes_weighted_main_and_signal(self):
        f = frame(count=40)
        f["close"] = f["open"] + np.sin(np.arange(40) / 3.0) * 0.003
        main, signal = RVI.rvi_values(f)
        self.assertTrue(np.isnan(main[:12]).all())
        self.assertTrue(np.isfinite(main[12:]).all())
        self.assertTrue(np.isnan(signal[:15]).all())
        expected = (main[15] + 2 * main[14] + 2 * main[13] + main[12]) / 6.0
        self.assertAlmostEqual(signal[15], expected, places=15)

    def test_long_and_short_crosses_are_exact(self):
        for direction in ("LONG", "SHORT"):
            f = frame()
            with patch.object(RVI, "rvi_values", return_value=fake_lines(len(f), direction)):
                report, ledger = RVI.analyze(f)
            self.assertEqual(report["events"]["executable"], 1)
            event = json.loads(ledger)
            self.assertEqual(event["direction"], direction)
            self.assertNotIn("open", event)
            self.assertNotIn("close", event)

    def test_exact_next_and_design_end_fail_closed(self):
        f = frame(start=RVI.DESIGN_TO - pd.Timedelta(hours=17))
        with patch.object(RVI, "rvi_values", return_value=fake_lines(len(f), "LONG")):
            report, ledger = RVI.analyze(f)
        self.assertEqual(report["events"]["raw"], 1)
        self.assertEqual(report["events"]["boundary_rejects"], 1)
        self.assertEqual(ledger, b"")
        f = frame(); f.loc[17:, "time_server"] += pd.Timedelta(hours=1)
        with patch.object(RVI, "rvi_values", return_value=fake_lines(len(f), "LONG")):
            report, ledger = RVI.analyze(f)
        self.assertEqual(report["events"]["gap_rejects"], 1)
        self.assertEqual(ledger, b"")

    def test_prereg_and_source_freeze_native_formula(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PERIOD = 10", text)
        self.assertIn("weighted_kernel", text)
        self.assertIn("range(16, len(frame))", text)
        self.assertIn("main[i] < 0.0 and signal[i] < 0.0", text)
        self.assertIn("main[i] > 0.0 and signal[i] > 0.0", text)


if __name__ == "__main__":
    unittest.main()
