#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[2]
SCRIPT = WORKSPACE / "02. AlphaFactory" / "tools" / "inspect_dtcc_fx_options_schema.py"


def load_module():
    spec = importlib.util.spec_from_file_location("inspect_dtcc_fx_options_schema", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DtccSchemaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_samples_span_all_known_layout_eras(self) -> None:
        self.assertEqual(set(self.module.SAMPLES), {"2018-01-02", "2020-12-01", "2023-01-03", "2024-07-16", "2025-01-02"})

    def test_sources_are_official_dtcc_buckets(self) -> None:
        for url in self.module.SAMPLES.values():
            self.assertTrue(url.startswith("https://kgc0418-tdw-data"))
            self.assertIn("amazonaws.com/", url)

    def test_output_is_d_only_and_source_probe_has_no_mt5(self) -> None:
        self.assertEqual(self.module.ROOT.drive.upper(), "D:")
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("MetaTrader5", source)
        self.assertIn('"price_bars_loaded": 0', source)
        self.assertIn('"performance_metrics_produced": False', source)

    def test_deep_archive_is_not_misreported_as_downloadable(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("OBJECT_EXISTS_BUT_ARCHIVED_GET_UNAVAILABLE", source)
        self.assertIn("DEEP_ARCHIVE", source)
        self.assertIn("FAIL_7_YEAR_ACCESS", source)


if __name__ == "__main__":
    unittest.main()
