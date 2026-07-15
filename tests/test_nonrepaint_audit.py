import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "02. AlphaFactory" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import audit_mql5_nonrepaint as audit  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class NonRepaintAuditTests(unittest.TestCase):
    def make_fixture(self, root: Path, source_text: str, include_text: str = ""):
        run_dir = root / "run"
        snapshot = run_dir / "snapshot"
        source = snapshot / "source" / "EA.mq5"
        include = snapshot / "includes" / "EA" / "One.mqh"
        source.parent.mkdir(parents=True)
        include.parent.mkdir(parents=True)
        source.write_text(source_text, encoding="utf-8")
        include.write_text(include_text, encoding="utf-8")
        manifest = run_dir / "run_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "run_id": "fixture",
                    "hypothesis_id": "H-FIXTURE",
                    "snapshot_root": str(snapshot),
                    "source_snapshot": str(source),
                    "source_sha256": sha(source),
                    "include_snapshots": [
                        {"snapshot_path": str(include), "sha256": sha(include)}
                    ],
                }
            ),
            encoding="utf-8",
        )
        return manifest, root / "audit.json"

    def test_closed_bar_calls_and_structural_new_bar_gate_pass(self) -> None:
        source = """
void OnTick() {
  datetime bar_time = iTime(_Symbol, PERIOD_CURRENT, 0);
  if(bar_time == g_lastBar) { return; }
  g_lastBar = bar_time;
  CopyRates(_Symbol, PERIOD_M15, 1, 20, rates);
  CopyBuffer(handle, 0, 1, 20, values);
  double close1 = iClose(_Symbol, PERIOD_M15, 1);
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            manifest, output = self.make_fixture(Path(tmp), source)
            self.assertEqual(audit.run(manifest, output), 0)
            payload = json.loads(output.read_text())
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(len(payload["allowed_new_bar_gates"]), 1)

    def test_bar_zero_data_calls_fail(self) -> None:
        cases = {
            "copy_rates": "CopyRates(_Symbol, PERIOD_M15, 0, 20, rates);",
            "copy_buffer": "CopyBuffer(handle, 0, 0, 20, values);",
            "series": "double x=iClose(_Symbol, PERIOD_M15, 0);",
            "array": "double x=Close[0];",
            "itime_not_gate": "datetime x=iTime(_Symbol, PERIOD_M15, 0); Use(x);",
            "dynamic_copy_shift": "CopyRates(_Symbol, PERIOD_M15, shift, 20, rates);",
            "dynamic_buffer_shift": "CopyBuffer(handle, 0, start_pos, 20, values);",
            "dynamic_series_shift": "double x=iClose(_Symbol, PERIOD_M15, shift);",
            "dynamic_time_shift": "datetime x=iTime(_Symbol, PERIOD_M15, shift);",
            "copy_close_zero": "CopyClose(_Symbol, PERIOD_M15, 0, 20, values);",
            "highest_zero_window": "int x=iHighest(_Symbol, PERIOD_M15, MODE_HIGH, 20, 0);",
            "lowest_dynamic_window": "int x=iLowest(_Symbol, PERIOD_M15, MODE_LOW, 20, shift);",
        }
        for label, source in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                manifest, output = self.make_fixture(Path(tmp), source)
                self.assertEqual(audit.run(manifest, output), 1)
                self.assertEqual(json.loads(output.read_text())["status"], "FAIL")

    def test_snapshot_hash_drift_fails_before_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest, output = self.make_fixture(
                Path(tmp), "CopyRates(_Symbol, PERIOD_M15, 1, 20, rates);"
            )
            payload = json.loads(manifest.read_text())
            Path(payload["source_snapshot"]).write_text("// drift", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                audit.run(manifest, output)


if __name__ == "__main__":
    unittest.main()
