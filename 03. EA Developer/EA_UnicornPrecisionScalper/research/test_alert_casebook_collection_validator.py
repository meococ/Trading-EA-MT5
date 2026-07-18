from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from validate_alert_casebook_collection import LABEL_COLUMNS, validate


class AlertCasebookCollectionValidatorTests(unittest.TestCase):
    def build_fixture(
        self,
        root: Path,
        *,
        prefilled_label: bool = False,
        source_contract: str = "UPS_ALERT_FIRST_CASEBOOK_V1_3",
    ) -> Path:
        logs = root / "logs"
        analysis = root / "analysis"
        logs.mkdir(parents=True)
        analysis.mkdir(parents=True)
        extra_columns = ["m15_structure"] if source_contract.endswith("V1_4") else []
        header = [
            "schema_version", "contract_id", "source_contract_id", "source_sha256", "run_id",
            "event_id", "decision_time_utc", "symbol", *extra_columns, *LABEL_COLUMNS,
        ]
        with (logs / "XAUUSD_AlertCasebook_RUN1.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            for number in (1, 2):
                row = {field: "" for field in header}
                row.update(
                    schema_version="alert_first_casebook.v1",
                    contract_id="ALERT_FIRST_CASEBOOK_V1",
                    source_contract_id=source_contract,
                    source_sha256="A" * 64,
                    run_id="RUN1",
                    event_id=f"EVENT{number}",
                    decision_time_utc=f"2025.01.0{number} 10:00:00",
                    symbol="XAUUSD",
                )
                if extra_columns:
                    row["m15_structure"] = "1"
                if prefilled_label and number == 2:
                    row["label_trade_quality_accept"] = "1"
                writer.writerow(row)
        extra_meta = ["structure_pivot_strength"] if source_contract.endswith("V1_4") else []
        meta_header = [
            "contract_id", "source_contract_id", "source_sha256", "run_id", "period",
            "terminal_data_path", "casebook_max_rows", *extra_meta,
        ]
        with (logs / "XAUUSD_AlertCasebookMeta_RUN1.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=meta_header)
            writer.writeheader()
            writer.writerow(
                {
                    "contract_id": "ALERT_FIRST_CASEBOOK_V1",
                    "source_contract_id": source_contract,
                    "source_sha256": "A" * 64,
                    "run_id": "RUN1",
                    "period": "PERIOD_M5",
                    "terminal_data_path": r"D:\portable",
                    "casebook_max_rows": "200",
                    **({"structure_pivot_strength": "2"} if extra_meta else {}),
                }
            )
        (analysis / "enhanced_summary.json").write_text(
            json.dumps({"n_trades": 0}), encoding="utf-8"
        )
        (root / "run_manifest.json").write_text(
            json.dumps(
                {
                    "hypothesis_id": (
                        "DATA-ACQ-UNICORN-CASEBOOK-V1-003"
                        if source_contract.endswith("V1_4")
                        else "DATA-ACQ-UNICORN-CASEBOOK-V1-002"
                    ),
                    "source_sha256": "A" * 64,
                    "telemetry_tier": "off",
                    "mt5_storage_contract": {
                        "required_drive": "D:",
                        "portable_mode": True,
                        "common_files_allowed": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_valid_zero_trade_blank_label_collection_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = validate(self.build_fixture(Path(temp)), min_rows=2)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["detector_rows"], 2)
        self.assertEqual(result["strategy_tester_trades"], 0)

    def test_v14_requires_and_accepts_m15_structure_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = validate(
                self.build_fixture(
                    Path(temp), source_contract="UPS_ALERT_FIRST_CASEBOOK_V1_4"
                ),
                min_rows=2,
            )
        self.assertEqual(result["source_contract_id"], "UPS_ALERT_FIRST_CASEBOOK_V1_4")

    def test_prefilled_label_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.build_fixture(Path(temp), prefilled_label=True)
            with self.assertRaisesRegex(ValueError, "prefilled human label"):
                validate(fixture, min_rows=2)

    def test_source_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self.build_fixture(Path(temp))
            manifest_path = fixture / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_sha256"] = "B" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source SHA256 mismatch"):
                validate(fixture, min_rows=2)

    def test_breaker_label_is_part_of_the_blank_label_contract(self) -> None:
        self.assertIn("label_true_breaker_valid", LABEL_COLUMNS)


if __name__ == "__main__":
    unittest.main()
