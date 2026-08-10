from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/research"
BUILDER_PATH = RESEARCH / "build_stbs002_audit_packet.py"
RUNNER_PATH = RESEARCH / "run_stbs002_mt5_audit.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load(BUILDER_PATH, "stbs002_builder_under_test")
RUNNER = load(RUNNER_PATH, "stbs002_runner_under_test")


class Stbs002GovernanceHarnessTests(unittest.TestCase):
    def test_fresh_outer_and_inherited_inner_identities_are_exact(self) -> None:
        self.assertEqual(BUILDER.HYPOTHESIS_ID, "HYP-STBS-XAUUSD-M15-002")
        self.assertEqual(BUILDER.INNER_IMPLEMENTATION_ID, "HYP-STBS-XAUUSD-M15-001")
        self.assertEqual(RUNNER.OUTER_ID, BUILDER.HYPOTHESIS_ID)
        self.assertEqual(RUNNER.INNER_ID, BUILDER.INNER_IMPLEMENTATION_ID)
        self.assertEqual(BUILDER.PACKET_ATTEMPT_ID, "STBS002-PACKET-BUILD-001")
        self.assertEqual(RUNNER.OUTER_ATTEMPT_ID, "STBS002-MT5-AUDIT-001")

    def test_asof_was_frozen_before_prereg_and_is_not_future(self) -> None:
        asof = datetime.fromisoformat(BUILDER.ASOF.replace("Z", "+00:00"))
        prereg = datetime.fromisoformat("2026-08-09T02:38:28+00:00")
        self.assertLessEqual(asof, prereg)
        self.assertLessEqual(prereg, datetime.now(timezone.utc))

    def test_source_and_parent_evidence_are_unchanged(self) -> None:
        source = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/EA_SupertrendBurstScalper.mq5"
        self.assertEqual(BUILDER.sha256_file(source), BUILDER.SOURCE_SHA256)
        self.assertEqual(
            BUILDER.PARENT_TERMINAL_ROW_SHA256,
            "DCF06201068DDDC52D6B225FD871F1D7A0691F9EB4B864D969A7BFD1422DF8C2",
        )
        self.assertEqual(
            RUNNER.BASE_RUNNER_SHA256,
            "C4F2976F919EF9345CFC15891A9A8066F1FB5D474635C88BB29D047456645C14",
        )
        self.assertEqual(BUILDER.FROZEN_BASE_RUNNER_SHA256, RUNNER.BASE_RUNNER_SHA256)

    def test_outer_alpha_invocation_uses_hyp002_and_frozen_model0_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text("{}\n", encoding="utf-8")
            command = RUNNER.BASE.build_alpha_command(receipt)
        joined = " ".join(command)
        self.assertIn("-HypothesisId HYP-STBS-XAUUSD-M15-002", joined)
        self.assertIn("-Period M15", joined)
        self.assertIn("-From 2005.01.01 -To 2023.01.01", joined)
        self.assertIn("-Model 0", joined)
        self.assertIn("-Overrides InpAuditOnly=true", joined)
        self.assertIn("-TelemetryTier off", joined)

    def test_inner_journal_identity_is_scoped_and_outer_is_restored(self) -> None:
        events = RUNNER.BASE.load_expected_events()
        lines = []
        for row in events:
            exact = row["executable_event"] == 1
            fields = {
                "source": "fixture",
                "decision": "fixture",
                "source_epoch": row["source_epoch"],
                "decision_epoch": row["next_source_epoch"],
                "direction": row["direction"],
                "exact_next": "true" if exact else "false",
            }
            if exact:
                long = row["direction"] == "LONG"
                fields.update(
                    {
                        "atr_ready": "true",
                        "geometry_ready": "true",
                        "atr": 2.0,
                        "entry": 2000.0,
                        "sl": 1998.0 if long else 2002.0,
                        "tp": 2003.0 if long else 1997.0,
                        "volume": 0.1,
                        "audit": "true",
                    }
                )
            else:
                fields["consumed"] = "true"
            lines.append("STBS_SIGNAL|" + "|".join(f"{k}={v}" for k, v in fields.items()))
        summary = {
            "hypothesis": RUNNER.INNER_ID,
            "reason": 0,
            **RUNNER.BASE.EXPECTED_COUNTS,
            "entries": 0,
            "entry_rejects": 0,
            "closes": 0,
            "failed": "false",
        }
        lines.append("STBS_SUMMARY|" + "|".join(f"{k}={v}" for k, v in summary.items()))
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "journal.log"
            journal.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = RUNNER.validate_inner_journal(journal)
        self.assertEqual(result["raw"], 690)
        self.assertEqual(RUNNER.BASE.HYPOTHESIS_ID, RUNNER.OUTER_ID)

    def test_exact_hyp002_attempt_roots_are_ignored_once(self) -> None:
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for attempt in ("STBS002-PACKET-BUILD-001", "STBS002-MT5-AUDIT-001"):
            rule = (
                "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
                f"HYP-STBS-XAUUSD-M15-002/{attempt}/"
            )
            self.assertEqual(lines.count(rule), 1)

    def test_attempt_and_preflight_roots_are_absent(self) -> None:
        self.assertFalse(BUILDER.PACKET_EVIDENCE_DIR.exists())
        self.assertFalse(RUNNER.OUTER_ROOT.exists())
        self.assertFalse(
            (RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-002/V1").exists()
        )

    def test_packet_claim_is_exclusive(self) -> None:
        original = BUILDER.PACKET_EVIDENCE_DIR
        with tempfile.TemporaryDirectory() as directory:
            BUILDER.PACKET_EVIDENCE_DIR = Path(directory) / "attempt"
            try:
                marker = BUILDER.claim_packet_attempt()
                self.assertTrue(marker.is_file())
                with self.assertRaises(FileExistsError):
                    BUILDER.claim_packet_attempt()
            finally:
                BUILDER.PACKET_EVIDENCE_DIR = original

    def test_hyp001_failure_is_explicitly_bound_by_builder(self) -> None:
        source = BUILDER_PATH.read_text(encoding="utf-8")
        self.assertIn("hyp001_chronology_failure", source)
        self.assertIn("hyp001_invalid_packet_receipt", source)
        self.assertIn("hyp001_invalid_packet_terminal", source)
        self.assertIn("hyp001_terminal_contract(failed_hypothesis)", source)
        self.assertIn('"hyp001_terminal_row_sha256"', source)
        runner = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertIn("hyp001_terminal_contract(failed_hypothesis)", runner)
        self.assertIn("contract receipt HYP001 terminal row mismatch", runner)
        self.assertIn("chronology_is_valid(", runner)
        self.assertIn("frozen HYP001 runner dependency changed", runner)

    def test_terminal_metrics_and_permissions_fail_closed(self) -> None:
        validation = {
            name: False for name in BUILDER.HYP001_TERMINAL_FALSE_FIELDS
        }
        validation.update(
            {
                "chronology_failure_sha256": BUILDER.HYP001_FAILURE_SHA256,
                "packet_build_receipt_sha256": BUILDER.HYP001_PACKET_RECEIPT_SHA256,
                "packet_build_attempt_terminal_sha256": BUILDER.HYP001_PACKET_TERMINAL_SHA256,
            }
        )
        row = {
            "state": "killed",
            "verdict": "KILL_PACKET_AUTHORITY_TIMESTAMP_AFTER_ATTEMPT_NO_MT5",
            "metrics": {
                "packet_build_attempts_consumed": 1,
                "mt5_audit_attempts_consumed": 0,
                "run_compile_attempts_consumed": 0,
            },
            "validation": validation,
        }
        self.assertTrue(BUILDER.hyp001_terminal_contract(row))
        self.assertTrue(RUNNER.hyp001_terminal_contract(row))
        for metric, value in (
            ("packet_build_attempts_consumed", 0),
            ("mt5_audit_attempts_consumed", 1),
            ("run_compile_attempts_consumed", 1),
        ):
            mutated = json.loads(json.dumps(row))
            mutated["metrics"][metric] = value
            with self.subTest(metric=metric):
                self.assertFalse(BUILDER.hyp001_terminal_contract(mutated))
                self.assertFalse(RUNNER.hyp001_terminal_contract(mutated))
        for permission in BUILDER.HYP001_TERMINAL_FALSE_FIELDS:
            mutated = json.loads(json.dumps(row))
            mutated["validation"][permission] = True
            with self.subTest(permission=permission):
                self.assertFalse(BUILDER.hyp001_terminal_contract(mutated))
                self.assertFalse(RUNNER.hyp001_terminal_contract(mutated))

    def test_six_timestamp_chain_rejects_every_order_inversion(self) -> None:
        start = datetime(2026, 8, 9, 5, 0, tzinfo=timezone.utc)
        valid = [start + timedelta(seconds=index) for index in range(6)]
        self.assertTrue(RUNNER.chronology_is_valid(*valid))
        for index in range(1, 6):
            mutated = list(valid)
            mutated[index] = mutated[index - 1] - timedelta(seconds=1)
            with self.subTest(index=index):
                self.assertFalse(RUNNER.chronology_is_valid(*mutated))

    def test_actual_hyp001_artifact_tampering_fails(self) -> None:
        actual = (
            BUILDER.HYP001_FAILURE_PATH,
            BUILDER.HYP001_PACKET_RECEIPT_PATH,
            BUILDER.HYP001_PACKET_TERMINAL_PATH,
        )
        self.assertTrue(BUILDER.hyp001_artifacts_match(*actual))
        for mutation_index in range(3):
            with self.subTest(mutation_index=mutation_index), tempfile.TemporaryDirectory() as directory:
                copies = []
                for index, source in enumerate(actual):
                    target = Path(directory) / f"artifact_{index}"
                    shutil.copyfile(source, target)
                    copies.append(target)
                copies[mutation_index].write_bytes(
                    copies[mutation_index].read_bytes() + b"tamper"
                )
                self.assertFalse(BUILDER.hyp001_artifacts_match(*copies))
        runner_source = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertIn("HYP001 chronology failure", runner_source)
        self.assertIn("HYP001 invalid packet receipt", runner_source)
        self.assertIn("HYP001 invalid packet terminal", runner_source)


if __name__ == "__main__":
    unittest.main()
