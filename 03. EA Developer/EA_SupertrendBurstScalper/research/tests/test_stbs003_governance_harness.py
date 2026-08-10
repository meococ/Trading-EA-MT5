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
BUILDER_PATH = RESEARCH / "build_stbs003_audit_packet.py"
RUNNER_PATH = RESEARCH / "run_stbs003_mt5_audit.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load(BUILDER_PATH, "stbs003_builder_under_test")
RUNNER = load(RUNNER_PATH, "stbs003_runner_under_test")


def terminal_row() -> dict:
    validation = {name: False for name in BUILDER.HYP002_TERMINAL_FALSE_FIELDS}
    validation.update(
        {
            "failure_document_sha256": BUILDER.HYP002_FAILURE_SHA256,
            "independent_post_failure_review_sha256": (
                BUILDER.HYP002_POST_FAILURE_REVIEW_SHA256
            ),
            "mt5_attempt_started_sha256": BUILDER.HYP002_ATTEMPT_STARTED_SHA256,
            "mt5_attempt_terminal_sha256": BUILDER.HYP002_ATTEMPT_TERMINAL_SHA256,
            "alpha_stdout_sha256": BUILDER.HYP002_ALPHA_STDOUT_SHA256,
            "alpha_stderr_sha256": BUILDER.HYP002_ALPHA_STDERR_SHA256,
        }
    )
    return {
        "state": "killed",
        "verdict": "KILL_PRE_ALPHA_GIT_STATUS_PATHSET_DRIFT_NO_COMPILE_NO_MT5",
        "metrics": {
            "packet_build_attempts_consumed": 1,
            "mt5_audit_attempts_consumed": 1,
            "run_compile_attempts_consumed": 0,
            "model0_runs": 0,
            "mt5_launches": 0,
        },
        "validation": validation,
    }


class Stbs003GovernanceHarnessTests(unittest.TestCase):
    def test_fresh_outer_and_inherited_inner_identities_are_exact(self) -> None:
        self.assertEqual(BUILDER.HYPOTHESIS_ID, "HYP-STBS-XAUUSD-M15-003")
        self.assertEqual(BUILDER.INNER_IMPLEMENTATION_ID, "HYP-STBS-XAUUSD-M15-001")
        self.assertEqual(RUNNER.OUTER_ID, BUILDER.HYPOTHESIS_ID)
        self.assertEqual(RUNNER.INNER_ID, BUILDER.INNER_IMPLEMENTATION_ID)
        self.assertEqual(BUILDER.PACKET_ATTEMPT_ID, "STBS003-PACKET-BUILD-001")
        self.assertEqual(RUNNER.OUTER_ATTEMPT_ID, "STBS003-MT5-AUDIT-001")
        self.assertEqual(BUILDER.FAILED_HYPOTHESIS_ID, "HYP-STBS-XAUUSD-M15-002")
        self.assertEqual(RUNNER.FAILED_HYPOTHESIS_ID, BUILDER.FAILED_HYPOTHESIS_ID)

    def test_asof_was_frozen_before_prereg_and_is_not_future(self) -> None:
        asof = datetime.fromisoformat(BUILDER.ASOF.replace("Z", "+00:00"))
        prereg = datetime.fromisoformat("2026-08-09T05:05:56+00:00")
        self.assertLessEqual(asof, prereg)
        self.assertLessEqual(prereg, datetime.now(timezone.utc))

    def test_source_parent_and_base_runner_are_unchanged(self) -> None:
        source = ROOT / (
            "03. EA Developer/EA_SupertrendBurstScalper/"
            "EA_SupertrendBurstScalper.mq5"
        )
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

    def test_outer_alpha_invocation_is_hyp003_model0_audit_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text("{}\n", encoding="utf-8")
            command = RUNNER.BASE.build_alpha_command(receipt)
        joined = " ".join(command)
        self.assertIn("-HypothesisId HYP-STBS-XAUUSD-M15-003", joined)
        self.assertIn("-Period M15", joined)
        self.assertIn("-From 2005.01.01 -To 2023.01.01", joined)
        self.assertIn("-Model 0", joined)
        self.assertIn("-Overrides InpAuditOnly=true", joined)
        self.assertIn("-TelemetryTier off", joined)

    def test_exact_attempt_roots_are_ignored_once_and_absent(self) -> None:
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for attempt in ("STBS003-PACKET-BUILD-001", "STBS003-MT5-AUDIT-001"):
            rule = (
                "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
                f"HYP-STBS-XAUUSD-M15-003/{attempt}/"
            )
            self.assertEqual(lines.count(rule), 1)
        self.assertFalse(BUILDER.PACKET_EVIDENCE_DIR.exists())
        self.assertFalse(RUNNER.OUTER_ROOT.exists())
        self.assertFalse(
            (RESEARCH / "preflight/HYP-STBS-XAUUSD-M15-003/V1").exists()
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

    def test_hyp002_terminal_metrics_permissions_and_hashes_fail_closed(self) -> None:
        row = terminal_row()
        self.assertTrue(BUILDER.hyp002_terminal_contract(row))
        self.assertTrue(RUNNER.hyp002_terminal_contract(row))
        for metric, value in (
            ("packet_build_attempts_consumed", 0),
            ("mt5_audit_attempts_consumed", 0),
            ("run_compile_attempts_consumed", 1),
            ("model0_runs", 1),
            ("mt5_launches", 1),
        ):
            mutated = json.loads(json.dumps(row))
            mutated["metrics"][metric] = value
            with self.subTest(metric=metric):
                self.assertFalse(BUILDER.hyp002_terminal_contract(mutated))
                self.assertFalse(RUNNER.hyp002_terminal_contract(mutated))
        for permission in BUILDER.HYP002_TERMINAL_FALSE_FIELDS:
            mutated = json.loads(json.dumps(row))
            mutated["validation"][permission] = True
            with self.subTest(permission=permission):
                self.assertFalse(BUILDER.hyp002_terminal_contract(mutated))
                self.assertFalse(RUNNER.hyp002_terminal_contract(mutated))

    def test_actual_hyp002_artifact_tampering_fails(self) -> None:
        self.assertTrue(BUILDER.hyp002_artifacts_match())
        actual = (
            BUILDER.HYP002_FAILURE_PATH,
            BUILDER.HYP002_POST_FAILURE_REVIEW_PATH,
            BUILDER.HYP002_ATTEMPT_ROOT / "attempt_started.json",
            BUILDER.HYP002_ATTEMPT_ROOT / "attempt_terminal.json",
            BUILDER.HYP002_ATTEMPT_ROOT / "alpha_stdout.log",
            BUILDER.HYP002_ATTEMPT_ROOT / "alpha_stderr.log",
        )
        for mutation_index in range(len(actual)):
            with self.subTest(mutation_index=mutation_index), tempfile.TemporaryDirectory() as directory:
                copied_root = Path(directory)
                copies: list[Path] = []
                for index, source in enumerate(actual):
                    target = copied_root / f"artifact_{index}"
                    shutil.copyfile(source, target)
                    copies.append(target)
                copies[mutation_index].write_bytes(copies[mutation_index].read_bytes() + b"tamper")
                expected = (
                    BUILDER.HYP002_FAILURE_SHA256,
                    BUILDER.HYP002_POST_FAILURE_REVIEW_SHA256,
                    BUILDER.HYP002_ATTEMPT_STARTED_SHA256,
                    BUILDER.HYP002_ATTEMPT_TERMINAL_SHA256,
                    BUILDER.HYP002_ALPHA_STDOUT_SHA256,
                    BUILDER.HYP002_ALPHA_STDERR_SHA256,
                )
                self.assertFalse(
                    all(BUILDER.sha256_file(path) == digest for path, digest in zip(copies, expected))
                )

    def test_reserved_placeholder_is_present_once_and_not_evidence(self) -> None:
        status = [BUILDER.RESERVED_REVIEW_STATUS_LINE]
        contract = BUILDER.validate_reserved_placeholder(
            BUILDER.RESERVED_REVIEW_PATH,
            status,
        )
        self.assertEqual(contract["path"], BUILDER.RESERVED_REVIEW_REPO_PATH)
        self.assertFalse(contract["immutable_evidence"])
        for malformed in ([], status + status):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                BUILDER.validate_reserved_placeholder(BUILDER.RESERVED_REVIEW_PATH, malformed)
        with self.assertRaises(ValueError):
            BUILDER.validate_reserved_placeholder(
                BUILDER.RESERVED_REVIEW_PATH,
                status,
                (("forbidden", BUILDER.RESERVED_REVIEW_PATH),),
            )
        for invalid in (
            b"prefix" + BUILDER.RESERVED_PLACEHOLDER_BYTES,
            BUILDER.RESERVED_PLACEHOLDER_BYTES + b"suffix",
            b"Status: PASS_SCREENED_AUTHORITY\n",
            b"RESERVED_NON_AUTHORITATIVE_PLACEHOLDER",
        ):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                placeholder = Path(directory) / "placeholder.md"
                placeholder.write_bytes(invalid)
                with self.assertRaises(ValueError):
                    BUILDER.validate_reserved_placeholder(placeholder, status)

    def test_reserved_byte_change_keeps_path_set_but_path_mutation_fails(self) -> None:
        sealed = [" M .gitignore", BUILDER.RESERVED_REVIEW_STATUS_LINE]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.md"
            path.write_text(BUILDER.RESERVED_PLACEHOLDER_MARKER, encoding="utf-8")
            before = BUILDER.sha256_bytes("\n".join(sealed).encode("utf-8"))
            path.write_text("Status: PASS_SCREENED_AUTHORITY\n", encoding="utf-8")
            after = BUILDER.sha256_bytes("\n".join(sealed).encode("utf-8"))
            self.assertEqual(before, after)
        for mutated in (
            sealed[:-1],
            sealed + ['?? "new-path"'],
            [" M .gitignore", BUILDER.RESERVED_REVIEW_STATUS_LINE + ".renamed"],
        ):
            self.assertNotEqual(sealed, mutated)

    def test_final_review_semantics_and_receipt_contract_fail_closed(self) -> None:
        status = [BUILDER.RESERVED_REVIEW_STATUS_LINE]
        expected = RUNNER.expected_reserved_contract()
        with tempfile.TemporaryDirectory() as directory:
            review = Path(directory) / "review.md"
            review.write_text("Status: PASS_SCREENED_AUTHORITY\n", encoding="utf-8")
            row = {
                "validation": {
                    "reserved_post_packet_review_path": RUNNER.RESERVED_REVIEW_REPO_PATH,
                    "reserved_post_packet_review_sha256": RUNNER.BASE.sha256_file(review),
                }
            }
            receipt = {"reserved_mutable_control_paths": expected, "evidence": []}
            packet = {"reserved_mutable_control_paths": expected, "git_status": status}
            RUNNER.validate_final_review_contract(row, receipt, packet, review, status)
            review.write_text(RUNNER.RESERVED_PLACEHOLDER_MARKER, encoding="utf-8")
            row["validation"]["reserved_post_packet_review_sha256"] = RUNNER.BASE.sha256_file(review)
            with self.assertRaises(ValueError):
                RUNNER.validate_final_review_contract(row, receipt, packet, review, status)
            review.write_text("Status: PASS_SCREENED_AUTHORITY\n", encoding="utf-8")
            row["validation"]["reserved_post_packet_review_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                RUNNER.validate_final_review_contract(row, receipt, packet, review, status)
            row["validation"]["reserved_post_packet_review_sha256"] = RUNNER.BASE.sha256_file(review)
            bad_receipt = json.loads(json.dumps(receipt))
            bad_receipt["evidence"] = [{"path": str(review.resolve())}]
            with self.assertRaises(ValueError):
                RUNNER.validate_final_review_contract(row, bad_receipt, packet, review, status)

    def test_final_review_hash_and_semantics_use_one_byte_capture(self) -> None:
        first = b"Status: PASS_SCREENED_AUTHORITY\n"

        class MutablePath:
            def __init__(self, resolved: Path) -> None:
                self.resolved = resolved
                self.reads = 0

            def is_file(self) -> bool:
                return True

            def read_bytes(self) -> bytes:
                self.reads += 1
                if self.reads == 1:
                    return first
                return RUNNER.RESERVED_PLACEHOLDER_MARKER.encode("utf-8")

            def resolve(self) -> Path:
                return self.resolved

        with tempfile.TemporaryDirectory() as directory:
            path = MutablePath(Path(directory) / "review.md")
            row = {
                "validation": {
                    "reserved_post_packet_review_path": RUNNER.RESERVED_REVIEW_REPO_PATH,
                    "reserved_post_packet_review_sha256": RUNNER.BASE.sha256_bytes(first),
                }
            }
            receipt = {
                "reserved_mutable_control_paths": RUNNER.expected_reserved_contract(),
                "evidence": [],
            }
            packet = {
                "reserved_mutable_control_paths": RUNNER.expected_reserved_contract(),
                "git_status": [RUNNER.RESERVED_REVIEW_STATUS_LINE],
            }
            RUNNER.validate_final_review_contract(
                row,
                receipt,
                packet,
                path,  # type: ignore[arg-type]
                packet["git_status"],
            )
            self.assertEqual(path.reads, 1)

    def test_six_timestamp_chain_rejects_every_order_inversion(self) -> None:
        start = datetime(2026, 8, 9, 5, 0, tzinfo=timezone.utc)
        valid = [start + timedelta(seconds=index) for index in range(6)]
        self.assertTrue(RUNNER.chronology_is_valid(*valid))
        for index in range(1, 6):
            mutated = list(valid)
            mutated[index] = mutated[index - 1] - timedelta(seconds=1)
            with self.subTest(index=index):
                self.assertFalse(RUNNER.chronology_is_valid(*mutated))


if __name__ == "__main__":
    unittest.main()
