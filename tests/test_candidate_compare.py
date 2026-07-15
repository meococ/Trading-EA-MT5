import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "02. AlphaFactory" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import sonic_candidate_compare as comparator  # noqa: E402


class CandidateComparatorExitContractTests(unittest.TestCase):
    def invoke(self, verdict: str) -> tuple[int, dict]:
        payload = {
            "schema_version": "sonic_candidate_compare.v1",
            "baseline": {"run_id": "control"},
            "candidate": {"run_id": "challenger"},
            "findings": [] if verdict == "RESEARCH_PASS" else ["pf_below_1_30"],
            "verdict": verdict,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "compare.json"
            argv = [
                "sonic_candidate_compare.py",
                "challenger",
                "--baseline",
                "control",
                "--out",
                str(output),
            ]
            with (
                mock.patch.object(comparator, "compare", return_value=payload),
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                code = comparator.main()
            return code, json.loads(output.read_text(encoding="utf-8"))

    def test_review_is_nonzero_and_cannot_be_mistaken_for_success(self) -> None:
        code, artifact = self.invoke("REVIEW")
        self.assertEqual(code, 1)
        self.assertEqual(artifact["verdict"], "REVIEW")

    def test_only_research_pass_returns_zero(self) -> None:
        code, artifact = self.invoke("RESEARCH_PASS")
        self.assertEqual(code, 0)
        self.assertEqual(artifact["verdict"], "RESEARCH_PASS")


if __name__ == "__main__":
    unittest.main()
