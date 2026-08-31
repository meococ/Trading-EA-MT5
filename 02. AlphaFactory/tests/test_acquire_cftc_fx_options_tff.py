#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


WORKSPACE = Path(__file__).resolve().parents[2]
SCRIPT = WORKSPACE / "02. AlphaFactory" / "tools" / "acquire_cftc_fx_options_tff.py"
TEST_ROOT = WORKSPACE / "02. AlphaFactory" / "external" / "_test_cftc_acquire" / "raw"


def load_module():
    spec = importlib.util.spec_from_file_location("acquire_cftc_fx_options_tff", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CftcAcquisitionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def tearDown(self) -> None:
        shutil.rmtree(TEST_ROOT.parent, ignore_errors=True)

    def test_contract_has_both_official_tff_archives(self) -> None:
        self.assertEqual(
            set(self.module.URLS),
            {"futures_only", "futures_options_combined"},
        )
        for template in self.module.URLS.values():
            self.assertTrue(template.startswith("https://www.cftc.gov/files/dea/history/"))

    def test_output_contract_rejects_c_drive(self) -> None:
        with self.assertRaises(SystemExit):
            self.module.ensure_d_drive(Path(r"C:\forbidden\cftc"))

    def test_manifest_is_hash_bound_and_does_not_claim_holdout(self) -> None:
        def fake_download(_url: str, destination: Path) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(destination, "w") as archive:
                archive.writestr("sample.txt", "header\n")

        with patch.object(self.module, "download_atomic", side_effect=fake_download):
            result = self.module.acquire(TEST_ROOT, (2023,), refresh=True)
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["holdout_years_downloaded"], [])
        self.assertEqual(len(manifest["records"]), 2)
        self.assertTrue(all(len(row["sha256"]) == 64 for row in manifest["records"]))
        self.assertTrue(all(str(row["path"]).startswith("02. AlphaFactory/external/") for row in manifest["records"]))


if __name__ == "__main__":
    unittest.main()
