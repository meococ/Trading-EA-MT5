from __future__ import annotations

import unittest

from probe_mss_bos_alignment import mss_bos_close


def bar(high: float, low: float, close: float) -> dict[str, object]:
    return {"h": high, "l": low, "c": close}


class MssBosAlignmentTests(unittest.TestCase):
    def test_bullish_close_breaks_latest_pre_sweep_high(self) -> None:
        sample = [
            bar(5, 3, 4),
            bar(10, 4, 6),
            bar(6, 3, 5),
            bar(7, 2, 6),
            bar(8, 1, 7),
            bar(9, 2, 8),
            bar(9, 3, 9),
            bar(9, 4, 9.5),
            bar(11, 5, 10.5),
            bar(12, 6, 11),
        ]
        found, level, index = mss_bos_close(
            sample, direction=1, sweep_age_bars=2, strength=1
        )
        self.assertTrue(found)
        self.assertEqual(10, level)
        self.assertEqual(8, index)

    def test_wick_without_close_does_not_count(self) -> None:
        sample = [
            bar(5, 3, 4),
            bar(10, 4, 6),
            bar(6, 3, 5),
            bar(7, 2, 6),
            bar(8, 1, 7),
            bar(9, 2, 8),
            bar(11, 3, 9),
            bar(12, 4, 9.5),
            bar(13, 5, 9.9),
            bar(12, 6, 9.8),
        ]
        found, level, index = mss_bos_close(
            sample, direction=1, sweep_age_bars=2, strength=1
        )
        self.assertFalse(found)
        self.assertEqual(10, level)
        self.assertIsNone(index)

    def test_invalid_direction_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "direction"):
            mss_bos_close([], direction=0, sweep_age_bars=0)


if __name__ == "__main__":
    unittest.main()
