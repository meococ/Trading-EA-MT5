from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from probe_m15_structure_alignment import load_rows, structure_state


def bars(highs: list[float], lows: list[float]) -> list[dict[str, object]]:
    return [
        {"t": f"2024-01-01T00:{index:02d}:00Z", "h": high, "l": low}
        for index, (high, low) in enumerate(zip(highs, lows, strict=True))
    ]


class M15StructureAlignmentTests(unittest.TestCase):
    def test_higher_highs_and_higher_lows_are_bullish(self) -> None:
        sample = bars(
            [5, 10, 6, 7, 8, 12, 7, 8, 9, 14, 10],
            [4, 5, 3, 4, 1, 4, 5, 6, 2, 7, 8],
        )
        self.assertEqual(1, structure_state(sample, strength=1))

    def test_lower_highs_and_lower_lows_are_bearish(self) -> None:
        sample = bars(
            [5, 14, 8, 7, 6, 12, 7, 6, 5, 10, 6],
            [4, 5, 3, 4, 2, 4, 5, 3, 1, 4, 5],
        )
        self.assertEqual(-1, structure_state(sample, strength=1))

    def test_insufficient_confirmed_swings_are_neutral(self) -> None:
        self.assertEqual(0, structure_state(bars([1, 2, 3], [0, 1, 2]), strength=1))

    def test_outcome_bearing_context_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "label_context_batch_01.json"
            path.write_text(
                json.dumps(
                    {
                        "authority": "PRE_OUTCOME_LABEL_CONTEXT_ONLY",
                        "outcomes_included": True,
                        "row_count": 0,
                        "rows": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "outcome-bearing"):
                load_rows([path])


if __name__ == "__main__":
    unittest.main()
