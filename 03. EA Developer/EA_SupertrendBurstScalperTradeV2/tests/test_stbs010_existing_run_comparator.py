from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "research" / "compare_stbs010_existing_run.py"
SPEC = importlib.util.spec_from_file_location("stbs010_comparator_under_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StructuredCompileResultTests(unittest.TestCase):
    def write_log(self, directory: Path, result_lines: list[str]) -> Path:
        path = directory / "compile.log"
        text = "header\n" + "\n".join(result_lines) + "\nfooter\n"
        path.write_bytes(text.encode("utf-16"))
        return path

    def test_accepts_exact_metaeditor_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = MODULE.parse_structured_compile_result(self.write_log(
                Path(td), ["Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'"]
            ))
            self.assertEqual((result["errors"], result["warnings"], result["elapsed_ms"], result["cpu"]),
                             (0, 0, 722, "X64 Regular"))

    def test_rejects_all_frozen_compile_mutations(self) -> None:
        bad_cases = (
            ["Result: 0 errors, 0 warnings"],
            ["Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'",
             "Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'"],
            ["Result: 1 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'"],
            ["Result: 0 errors, 1 warnings, 722 ms elapsed, cpu='X64 Regular'"],
            ["Result: 0 errors, 0 warnings, 0 ms elapsed, cpu='X64 Regular'"],
            ["Result: 0 errors, 0 warnings, -1 ms elapsed, cpu='X64 Regular'"],
            ["Result: 0 errors, 0 warnings, 1.5 ms elapsed, cpu='X64 Regular'"],
            ["Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='ARM64'"],
            ["Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular' junk"],
            ["Result: 0 errors, 0 warnings, 722 ms elapsed, cpu=X64 Regular"],
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for index, lines in enumerate(bad_cases):
                with self.subTest(index=index, lines=lines):
                    with self.assertRaises(ValueError):
                        MODULE.parse_structured_compile_result(self.write_log(root, lines))

    def test_actual_frozen_compile_log_passes(self) -> None:
        result = MODULE.parse_structured_compile_result(MODULE.PARENT_RUN_COMPILE_LOG)
        self.assertEqual(result["line"],
                         "Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'")


class GovernanceContractTests(unittest.TestCase):
    def make_authority_fixture(self, root: Path, mutation=None):
        review = root / "HYP010_REVIEW.md"
        review.write_text(
            "# HYP010 pre-comparator independent review\n\n"
            "Verdict: `PASS_PRE_COMPARATOR`\n\nSynthetic authority fixture.\n",
            encoding="utf-8",
        )
        validation = {name: False for name in MODULE.FALSE_AUTHORITIES}
        validation.update({name: True for name in MODULE.TRUE_AUTHORITIES})
        validation.update({
            "authority": MODULE.AUTHORITY,
            "comparator_attempt_id": MODULE.ATTEMPT,
            "comparator_attempt_limit": 1,
            "reviewed_comparator_path": SCRIPT.relative_to(MODULE.ROOT).as_posix(),
            "reviewed_comparator_sha256": MODULE.sha_file(SCRIPT),
            "reviewed_hyp009_runner_path": MODULE.BASE.relative_to(MODULE.ROOT).as_posix(),
            "reviewed_hyp009_runner_sha256": MODULE.BASE_SHA256,
            "reviewed_test_path": Path(__file__).resolve().relative_to(MODULE.ROOT).as_posix(),
            "reviewed_test_sha256": MODULE.sha_file(Path(__file__).resolve()),
            "independent_review_path": review.relative_to(MODULE.ROOT).as_posix(),
            "independent_review_sha256": MODULE.sha_file(review),
            "independent_review_status": "PASS_PRE_COMPARATOR",
            "gitignore_path": MODULE.GITIGNORE.relative_to(MODULE.ROOT).as_posix(),
            "gitignore_sha256": MODULE.sha_file(MODULE.GITIGNORE),
            "comparator_evidence_root": MODULE.OUTPUT_ROOT.relative_to(MODULE.ROOT).as_posix(),
            "hyp009_terminal_row_sha256": MODULE.PARENT_TERMINAL_ROW_SHA256,
        })
        row = {
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": MODULE.HYPOTHESIS,
            "ea_name": "EA_SupertrendBurstScalperTradeV2",
            "state": "screened",
            "parent_candidate": MODULE.PARENT,
            "feature_family": "h1-supertrend-fastpath-audit-recovery",
            "lane": "XAUUSD-M15-STBS010-COMPARATOR",
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "window": {"from": "2018.01.01", "to": "2022.12.31"},
            "model": 0,
            "source_provenance": "Synthetic HYP010 test fixture.",
            "source_path": MODULE.SOURCE.relative_to(MODULE.ROOT).as_posix(),
            "source_hash": MODULE.SOURCE_SHA256,
            "prereg_path": MODULE.PREREG.relative_to(MODULE.ROOT).as_posix(),
            "prereg_sha256": MODULE.sha_file(MODULE.PREREG),
            "exact_overrides": "InpAuditOnly=true",
            "evidence_contract_kind": "data_acquisition",
            "data_acceptance_contract": MODULE.EXPECTED_DATA_ACCEPTANCE,
            "verdict": MODULE.AUTHORITY_VERDICT,
            "reason": "Synthetic authority fixture.",
            "updated_at_utc": MODULE.now_text(),
            "run_ids": [],
            "metrics": {
                "comparator_attempt_limit": 1,
                "comparator_attempts_consumed": 0,
                "model0_runs": 0,
                "mt5_launches": 0,
                "orders_executed": 0,
                "trades_simulated": 0,
                "returns_computed": 0,
                "performance_trials_executed": 0,
                "economics_executed": False,
                "research_validation_opened": False,
                "research_holdout_opened": False,
            },
            "validation": validation,
        }
        if mutation is not None:
            mutation(row)
        registry = root / "registry.jsonl"
        registry.write_bytes(MODULE.REGISTRY.read_bytes() + MODULE.json_bytes(row))
        return registry, review

    def test_claim_is_first_external_content_action(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        body = source[source.index("def execute("):source.index("def main(")]
        self.assertLess(body.index("marker = claim(registry)"),
                        body.index("validate_authority_after_claim"))
        self.assertLess(body.index("marker = claim(registry)"), body.index("load_parent_runner"))
        self.assertNotIn("subprocess", source)
        self.assertNotIn("alpha.ps1", source.lower())

    def test_only_collection_and_comparator_can_be_true(self) -> None:
        self.assertEqual(set(MODULE.TRUE_AUTHORITIES),
                         {"artifact_collection_authorized", "comparator_execution_authorized"})
        required_false = {
            "mt5_authorized", "compile_authorized", "run_compile_authorized",
            "mql5_compile_authorized", "trade_api_authorized",
            "performance_metrics_authorized", "outcome_prices_authorized",
            "economics_authorized", "optimization_authorized", "validation_authorized",
            "holdout_authorized", "paper_trading_authorized", "live_trading_authorized",
            "same_id_retry_authorized", "registry_mutation_allowed",
        }
        self.assertTrue(required_false.issubset(set(MODULE.FALSE_AUTHORITIES)))

    def test_parent_terminal_row_is_exact(self) -> None:
        raw = MODULE.REGISTRY.read_bytes()
        parent_raw, row = MODULE.latest_row(raw, MODULE.PARENT)
        self.assertEqual(MODULE.sha_bytes(parent_raw), MODULE.PARENT_TERMINAL_ROW_SHA256)
        self.assertEqual(row["state"], "killed")
        self.assertEqual(row["verdict"], MODULE.PARENT_TERMINAL_VERDICT)

    def test_all_parent_bindings_match_actual_bytes(self) -> None:
        for label, (path, expected) in MODULE.PARENT_BINDINGS.items():
            with self.subTest(label=label):
                self.assertTrue(path.is_file())
                self.assertEqual(MODULE.sha_file(path), expected)

    def test_oracle_hash_is_literal_and_actual(self) -> None:
        raw = MODULE.BASE.read_bytes()
        self.assertEqual(MODULE.sha_bytes(raw), MODULE.BASE_SHA256)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(MODULE.ORACLE_SHA256, source)

    def test_evidence_root_is_fresh(self) -> None:
        self.assertEqual(MODULE.ATTEMPT, "STBS010-COMPARATOR-001")
        self.assertFalse(MODULE.OUTPUT_ROOT.exists())

    def test_evidence_root_has_exact_gitignore_rule(self) -> None:
        rule = MODULE.OUTPUT_ROOT.relative_to(MODULE.ROOT).as_posix() + "/"
        lines = MODULE.GITIGNORE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count(rule), 1)
        probe = MODULE.OUTPUT_ROOT / "attempt_started.json"
        completed = subprocess.run(
            ["git", "-C", str(MODULE.ROOT), "check-ignore", "-q", str(probe)],
            check=False,
        )
        self.assertEqual(completed.returncode, 0)

    def test_valid_screened_authority_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE.ROOT) as td:
            registry, review = self.make_authority_fixture(Path(td))
            with mock.patch.object(MODULE, "REVIEW", review):
                _, authority, bindings = MODULE.validate_authority_after_claim(registry)
            self.assertEqual(authority["hyp009_terminal_row_sha256"],
                             MODULE.PARENT_TERMINAL_ROW_SHA256)
            self.assertIn("comparator", {item["label"] for item in bindings})
            self.assertIn("gitignore", {item["label"] for item in bindings})

    def test_every_permission_attempt_and_bound_hash_mutation_fails(self) -> None:
        mutations = []
        for name in MODULE.TRUE_AUTHORITIES:
            mutations.append((f"true_{name}", lambda row, key=name: row["validation"].__setitem__(key, False)))
        for name in MODULE.FALSE_AUTHORITIES:
            mutations.append((f"false_{name}", lambda row, key=name: row["validation"].__setitem__(key, True)))
        mutations.extend((
            ("attempt_consumed", lambda row: row["metrics"].__setitem__("comparator_attempts_consumed", 1)),
            ("metric_limit", lambda row: row["metrics"].__setitem__("comparator_attempt_limit", 2)),
            ("validation_limit", lambda row: row["validation"].__setitem__("comparator_attempt_limit", 2)),
            ("run_ids", lambda row: row.__setitem__("run_ids", ["20260809_181119"])),
            ("research_validation", lambda row: row["metrics"].__setitem__("research_validation_opened", True)),
            ("research_holdout", lambda row: row["metrics"].__setitem__("research_holdout_opened", True)),
            ("self_hash", lambda row: row["validation"].__setitem__("reviewed_comparator_sha256", "0" * 64)),
            ("test_hash", lambda row: row["validation"].__setitem__("reviewed_test_sha256", "0" * 64)),
            ("gitignore_hash", lambda row: row["validation"].__setitem__("gitignore_sha256", "0" * 64)),
            ("parent_raw", lambda row: row["validation"].__setitem__("hyp009_terminal_row_sha256", "0" * 64)),
        ))
        with tempfile.TemporaryDirectory(dir=MODULE.ROOT) as td:
            root = Path(td)
            for index, (label, mutation) in enumerate(mutations):
                case = root / f"case_{index}"
                case.mkdir()
                registry, review = self.make_authority_fixture(case, mutation)
                with self.subTest(label=label), mock.patch.object(MODULE, "REVIEW", review):
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        MODULE.validate_authority_after_claim(registry)

    def test_claim_is_exclusive_and_failure_is_durable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "registry.jsonl"
            registry.write_text("{}\n", encoding="utf-8")
            output = root / "attempt"
            with mock.patch.object(MODULE, "REGISTRY", registry), \
                    mock.patch.object(MODULE, "OUTPUT_ROOT", output):
                marker = MODULE.claim(registry)
                self.assertTrue(marker.is_file())
                with self.assertRaises(FileExistsError):
                    MODULE.claim(registry)

    def test_execute_failure_writes_terminal_after_claim(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "registry.jsonl"
            registry.write_text("{}\n", encoding="utf-8")
            output = root / "attempt"
            with mock.patch.object(MODULE, "REGISTRY", registry), \
                    mock.patch.object(MODULE, "OUTPUT_ROOT", output):
                with self.assertRaises(ValueError):
                    MODULE.execute(registry)
            terminal = json.loads((output / "attempt_terminal.json").read_text(encoding="utf-8"))
            self.assertEqual(terminal["status"], "FAILED")
            self.assertEqual(terminal["verdict"], "STBS010_COMPARATOR_FAILED_CONSUMED")
            self.assertFalse(terminal["same_id_retry_authorized"])


class CompatibilityScopeTests(unittest.TestCase):
    def test_legacy_compatibility_is_scoped_to_one_frozen_log(self) -> None:
        compile_line = "Result: 0 errors, 0 warnings, 722 ms elapsed, cpu='X64 Regular'"

        class FakeBase:
            def __init__(self) -> None:
                self.decode_artifact = lambda path: compile_line

            def validate_run(self, run_dir: Path):
                normalized = self.decode_artifact(MODULE.PARENT_RUN_COMPILE_LOG)
                if normalized != "Result: 0 errors, 0 warnings":
                    raise AssertionError(normalized)
                return {
                    "counts": {**MODULE.EXPECTED_COUNTS, "journal_record_multiplicity": 2},
                }

        fake = FakeBase()
        with mock.patch.object(MODULE, "parse_structured_compile_result", return_value={
            "errors": 0, "warnings": 0, "elapsed_ms": 722,
            "cpu": "X64 Regular", "line": compile_line,
        }):
            validated, _ = MODULE.recovered_validate_run(fake)
        self.assertEqual(validated["counts"]["raw"], 690)
        self.assertEqual(fake.decode_artifact(Path("other.log")), compile_line)


if __name__ == "__main__":
    unittest.main()
