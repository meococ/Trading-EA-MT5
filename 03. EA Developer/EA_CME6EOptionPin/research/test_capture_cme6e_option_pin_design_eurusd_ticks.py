from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).with_name(
    "capture_cme6e_option_pin_design_eurusd_ticks.py"
)
SPEC = importlib.util.spec_from_file_location("tick_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


DTYPE = np.dtype(
    [
        ("time", "i8"), ("bid", "f8"), ("ask", "f8"), ("last", "f8"),
        ("volume", "u8"), ("time_msc", "i8"), ("flags", "u4"),
        ("volume_real", "f8"),
    ]
)


class TickSelectionTests(unittest.TestCase):
    def test_first_tick_at_or_after_clock_with_valid_book(self) -> None:
        clock = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)
        base = int(clock.timestamp() * 1000)
        ticks = np.array(
            [
                (base // 1000, 1.1, 1.1001, 0, 0, base - 1, 0, 0),
                (base // 1000, 1.1, 1.1, 0, 0, base, 0, 0),
                (base // 1000, 1.1, 1.1002, 0, 0, base + 1, 0, 0),
            ],
            dtype=DTYPE,
        )
        selected = MODULE.select_first_valid_tick(ticks, clock)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["time_msc"], base + 1)


if __name__ == "__main__":
    unittest.main()
