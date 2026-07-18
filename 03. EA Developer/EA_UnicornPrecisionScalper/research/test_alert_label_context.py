from __future__ import annotations

import unittest
import csv
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from extract_alert_label_context import (
    LABEL_COLUMNS,
    assert_no_forbidden_keys,
    compact_bars,
    read_casebook,
)


class AlertLabelContextTests(unittest.TestCase):
    def write_casebook(
        self,
        path: Path,
        *,
        contract: str = "UPS_ALERT_FIRST_CASEBOOK_V1_3",
        source_sha256: str = "A" * 64,
        include_breaker: bool = True,
    ) -> None:
        label_columns = sorted(LABEL_COLUMNS)
        if not include_breaker:
            label_columns = [
                column for column in label_columns
                if column != "label_true_breaker_valid"
            ]
        fieldnames = [
            "schema_version",
            "source_contract_id",
            "source_sha256",
            "event_id",
            "decision_time_utc",
            *label_columns,
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for index in range(200):
                row = {
                    "schema_version": "alert_first_casebook.v1",
                    "source_contract_id": contract,
                    "source_sha256": source_sha256,
                    "event_id": f"event-{index:03d}",
                    "decision_time_utc": "2025.01.02 03:04:05",
                }
                row.update({column: "" for column in label_columns})
                writer.writerow(row)

    def test_v13_casebook_is_source_bound_and_breaker_label_complete(self) -> None:
        self.assertIn("label_true_breaker_valid", LABEL_COLUMNS)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "casebook.csv"
            self.write_casebook(path)
            rows = read_casebook(path, "A" * 64)
            self.assertEqual(200, len(rows))

    def test_v12_or_missing_breaker_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "casebook.csv"
            self.write_casebook(path, contract="UPS_ALERT_FIRST_CASEBOOK_V1_2")
            with self.assertRaisesRegex(ValueError, "source contract mismatch"):
                read_casebook(path, "A" * 64)
            self.write_casebook(path, include_breaker=False)
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                read_casebook(path, "A" * 64)

    def test_source_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "casebook.csv"
            self.write_casebook(path)
            with self.assertRaisesRegex(ValueError, "source SHA256 mismatch"):
                read_casebook(path, "B" * 64)

    def test_compact_bars_rejects_future_bar(self) -> None:
        rates = np.array(
            [
                (100, 1.0, 2.0, 0.5, 1.5, 3),
                (200, 1.5, 2.5, 1.0, 2.0, 4),
            ],
            dtype=[
                ("time", "i8"),
                ("open", "f8"),
                ("high", "f8"),
                ("low", "f8"),
                ("close", "f8"),
                ("spread", "i8"),
            ],
        )
        cutoff = datetime.fromtimestamp(150, tz=timezone.utc)
        with self.assertRaisesRegex(ValueError, "future/incomplete bar"):
            compact_bars(rates, cutoff, timedelta(seconds=50), 2, timedelta(0))

    def test_outcome_like_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "forbidden outcome key"):
            assert_no_forbidden_keys({"event": {"forward_return": 0.1}})


if __name__ == "__main__":
    unittest.main()
