from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/research"
TEMPLATE = RESEARCH / "HYP-STBS-XAUUSD-M15-001_TERMINAL_ROW_TEMPLATE.json"
REGISTRY = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
VALIDATOR = ROOT / "04. Memory/research/validate_candidate_registry.py"


class Stbs001TerminalRowTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.row = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_terminal_identity_and_consumption_are_exact(self) -> None:
        row = self.row
        self.assertEqual(row["state"], "killed")
        self.assertEqual(
            row["verdict"], "KILL_PACKET_AUTHORITY_TIMESTAMP_AFTER_ATTEMPT_NO_MT5"
        )
        self.assertEqual(row["metrics"]["packet_build_attempts_consumed"], 1)
        self.assertEqual(row["metrics"]["mt5_audit_attempts_consumed"], 0)
        self.assertEqual(row["metrics"]["run_compile_attempts_consumed"], 0)

    def test_terminal_timestamp_follows_invalid_probe_but_must_wait_for_real_clock(self) -> None:
        terminal = datetime.fromisoformat(
            self.row["updated_at_utc"].replace("Z", "+00:00")
        )
        invalid_probe = datetime.fromisoformat("2026-08-09T04:46:00+00:00")
        self.assertGreater(terminal, invalid_probe)
        now = datetime.now(timezone.utc)
        self.assertGreaterEqual(
            now,
            terminal,
            "actual UTC has not reached the append-only terminal gate",
        )

    def test_template_validates_against_full_append_only_registry(self) -> None:
        raw = json.dumps(self.row, separators=(",", ":"), ensure_ascii=False).encode()
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "registry.jsonl"
            candidate.write_bytes(REGISTRY.read_bytes() + raw + b"\n")
            completed = subprocess.run(
                ["python", "-B", str(VALIDATOR), "--registry", str(candidate)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
