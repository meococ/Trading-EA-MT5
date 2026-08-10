from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "research" / "compare_stbs011_summary_bom.py"
SPEC = importlib.util.spec_from_file_location("stbs011_comparator_under_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExactBomDecoderTests(unittest.TestCase):
    def write(self, root: Path, name: str, raw: bytes) -> Path:
        path = root / name
        path.write_bytes(raw)
        return path

    def decode_temp(self, path: Path):
        return MODULE.decode_exact_bom_json(
            path, expected_path=path, expected_sha256=MODULE.sha_file(path)
        )

    def test_exact_single_bom_strict_json_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = self.write(Path(td), "summary.json", MODULE.UTF8_BOM + b'{"n_trades":0}')
            text, payload = self.decode_temp(path)
            self.assertEqual(text, '{"n_trades":0}')
            self.assertEqual(payload, {"n_trades": 0})

    def test_bom_encoding_and_single_document_mutations_fail(self) -> None:
        cases = {
            "absent": b'{"n_trades":0}',
            "double": MODULE.UTF8_BOM * 2 + b'{"n_trades":0}',
            "interior": MODULE.UTF8_BOM + b'{"x":"' + MODULE.UTF8_BOM + b'"}',
            "invalid_utf8": MODULE.UTF8_BOM + b'{"x":"\xff"}',
            "malformed": MODULE.UTF8_BOM + b'{"x":',
            "trailing_json": MODULE.UTF8_BOM + b'{"x":1}{"y":2}',
            "trailing_junk": MODULE.UTF8_BOM + b'{"x":1} junk',
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, raw in cases.items():
                with self.subTest(name=name):
                    path = self.write(root, f"{name}.json", raw)
                    with self.assertRaises((ValueError, UnicodeDecodeError, json.JSONDecodeError)):
                        self.decode_temp(path)

    def test_wrong_path_and_hash_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self.write(root, "first.json", MODULE.UTF8_BOM + b"{}")
            second = self.write(root, "second.json", MODULE.UTF8_BOM + b"{}")
            with self.assertRaises(ValueError):
                MODULE.decode_exact_bom_json(first, expected_path=second,
                                             expected_sha256=MODULE.sha_file(first))
            with self.assertRaises(ValueError):
                MODULE.decode_exact_bom_json(first, expected_path=first,
                                             expected_sha256="0" * 64)

    def test_actual_summary_has_exact_frozen_bom_and_hash(self) -> None:
        self.assertEqual(MODULE.sha_file(MODULE.SUMMARY), MODULE.SUMMARY_SHA256)
        raw = MODULE.SUMMARY.read_bytes()
        self.assertTrue(raw.startswith(MODULE.UTF8_BOM))
        self.assertNotIn(MODULE.UTF8_BOM, raw[len(MODULE.UTF8_BOM):])


class GoldenPathIntegrationTests(unittest.TestCase):
    def test_decoder_is_scoped_and_complete_golden_path_is_transformed(self) -> None:
        stages = []
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / "other.json"
            other.write_text("OTHER", encoding="utf-8")

            class FakeHyp010:
                pass

            fake = FakeHyp010()

            def original_recovery(base):
                stages.extend(("compile", "manifest", "config", "dq"))
                summary_text = MODULE.SUMMARY.read_text(encoding="utf-8")
                self.assertEqual(summary_text, '{"schema_version":"ok"}')
                self.assertEqual(other.read_text(encoding="utf-8"), "OTHER")
                stages.extend(("summary", "orders", "funding", "journal", "oracle"))
                return {"counts": {"raw": 690}}, {"errors": 0}

            fake.recovered_validate_run = original_recovery

            def fake_build_report(base):
                fake.recovered_validate_run(base)
                return ({
                    "schema_version": "stbs010_existing_run_comparator_report.v1",
                    "hypothesis_id": "HYP-STBS-XAUUSD-M15-010",
                    "verdict": "old",
                    "raw": 690,
                }, [{"label": "fixture", "path": str(other), "sha256": MODULE.sha_file(other)}])

            fake.build_report = fake_build_report
            with mock.patch.object(MODULE, "decode_exact_bom_json",
                                   return_value=('{"schema_version":"ok"}', {"schema_version": "ok"})):
                report, bindings = MODULE.build_report(fake, object())
        self.assertEqual(stages, ["compile", "manifest", "config", "dq", "summary",
                                  "orders", "funding", "journal", "oracle"])
        self.assertEqual(report["schema_version"], "stbs011_summary_bom_comparator_report.v1")
        self.assertEqual(report["hypothesis_id"], MODULE.HYPOTHESIS)
        self.assertEqual(report["verdict"], MODULE.PASS_VERDICT)
        self.assertEqual(bindings[0]["label"], "fixture")

    def test_replay_mismatch_is_explicitly_rejected_by_execute_source(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("report_raw != json_bytes(second) or first_extra != second_extra", source)
        self.assertIn("bound input changed before receipt", source)

    def test_inherited_hyp009_run_oracle_and_receipt_inputs_enter_receipt_surface(self) -> None:
        hyp010 = types.SimpleNamespace(PARENT_BINDINGS={
            "parent_runner": (Path(__file__).resolve(), MODULE.sha_file(Path(__file__).resolve())),
            "run_manifest": (MODULE.RUN_DIR / "run_manifest.json",
                             "8837FB5635865AA5791181D22E7F16418C63A5D39A5F235D59539E38B2F3C5E5"),
        })
        bindings = []
        MODULE.bind_inherited_inputs(hyp010, bindings)
        labels = {item["label"] for item in bindings}
        self.assertEqual(labels, {"hyp010_parent_runner", "hyp010_run_manifest"})

    def test_actual_frozen_hyp010_dependency_loads_and_closes_binding_surface(self) -> None:
        hyp010 = MODULE.load_hyp010()
        bindings = []
        MODULE.bind_inherited_inputs(hyp010, bindings)
        labels = {item["label"] for item in bindings}
        self.assertTrue({
            "hyp010_parent_runner", "hyp010_parent_packet_receipt",
            "hyp010_parent_oracle", "hyp010_run_manifest", "hyp010_run_report",
            "hyp010_run_journal", "hyp010_run_summary",
        }.issubset(labels))


class GovernanceTests(unittest.TestCase):
    def make_authority_fixture(self, root: Path, mutation=None):
        review = root / "HYP011_REVIEW.md"
        review.write_text(
            "# HYP011 pre-comparator independent review\n\n"
            "Verdict: `PASS_PRE_COMPARATOR`\n\nSynthetic fixture.\n",
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
            "reviewed_hyp010_comparator_path": MODULE.HYP010_COMPARATOR.relative_to(MODULE.ROOT).as_posix(),
            "reviewed_hyp010_comparator_sha256": MODULE.HYP010_COMPARATOR_SHA256,
            "reviewed_test_path": Path(__file__).resolve().relative_to(MODULE.ROOT).as_posix(),
            "reviewed_test_sha256": MODULE.sha_file(Path(__file__).resolve()),
            "independent_review_path": review.relative_to(MODULE.ROOT).as_posix(),
            "independent_review_sha256": MODULE.sha_file(review),
            "independent_review_status": "PASS_PRE_COMPARATOR",
            "gitignore_path": MODULE.GITIGNORE.relative_to(MODULE.ROOT).as_posix(),
            "gitignore_sha256": MODULE.sha_file(MODULE.GITIGNORE),
            "comparator_evidence_root": MODULE.OUTPUT_ROOT.relative_to(MODULE.ROOT).as_posix(),
            "hyp010_terminal_row_sha256": MODULE.PARENT_TERMINAL_ROW_SHA256,
            "frozen_summary_sha256": MODULE.SUMMARY_SHA256,
        })
        row = {
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": MODULE.HYPOTHESIS,
            "ea_name": "EA_SupertrendBurstScalperTradeV2",
            "state": "screened",
            "parent_candidate": MODULE.PARENT,
            "feature_family": "h1-supertrend-fastpath-audit-summary-bom-recovery",
            "lane": "XAUUSD-M15-STBS011-COMPARATOR",
            "symbol": "XAUUSD", "timeframe": "M15",
            "window": {"from": "2018.01.01", "to": "2022.12.31"},
            "model": 0,
            "source_provenance": "Synthetic HYP011 fixture.",
            "source_path": MODULE.SOURCE.relative_to(MODULE.ROOT).as_posix(),
            "source_hash": MODULE.SOURCE_SHA256,
            "prereg_path": MODULE.PREREG.relative_to(MODULE.ROOT).as_posix(),
            "prereg_sha256": MODULE.sha_file(MODULE.PREREG),
            "exact_overrides": "InpAuditOnly=true",
            "evidence_contract_kind": "data_acquisition",
            "data_acceptance_contract": MODULE.EXPECTED_DATA_ACCEPTANCE,
            "verdict": MODULE.AUTHORITY_VERDICT,
            "reason": "Synthetic fixture.",
            "updated_at_utc": MODULE.now_text(),
            "run_ids": [],
            "metrics": {
                "comparator_attempt_limit": 1, "comparator_attempts_consumed": 0,
                "model0_runs": 0, "mt5_launches": 0, "orders_executed": 0,
                "trades_simulated": 0, "returns_computed": 0,
                "performance_trials_executed": 0, "economics_executed": False,
                "research_validation_opened": False, "research_holdout_opened": False,
            },
            "validation": validation,
        }
        if mutation:
            mutation(row)
        registry = root / "registry.jsonl"
        registry.write_bytes(MODULE.REGISTRY.read_bytes() + MODULE.json_bytes(row))
        return registry, review

    def test_claim_precedes_every_bound_read(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        body = source[source.index("def execute("):source.index("def main(")]
        self.assertLess(body.index("marker = claim(registry)"),
                        body.index("validate_authority_after_claim"))
        self.assertLess(body.index("marker = claim(registry)"), body.index("load_hyp010"))
        self.assertNotIn("subprocess", source)
        self.assertNotIn("alpha.ps1", source.lower())

    def test_exact_ignore_and_fresh_root(self) -> None:
        rule = MODULE.OUTPUT_ROOT.relative_to(MODULE.ROOT).as_posix() + "/"
        self.assertEqual(MODULE.GITIGNORE.read_text(encoding="utf-8").splitlines().count(rule), 1)
        self.assertEqual(subprocess.run(
            ["git", "-C", str(MODULE.ROOT), "check-ignore", "-q",
             str(MODULE.OUTPUT_ROOT / "attempt_started.json")], check=False
        ).returncode, 0)
        self.assertFalse(MODULE.OUTPUT_ROOT.exists())

    def test_parent_bindings_match(self) -> None:
        for label, (path, expected) in MODULE.PARENT_BINDINGS.items():
            with self.subTest(label=label):
                self.assertEqual(MODULE.sha_file(path), expected)

    def test_valid_authority_and_mutations(self) -> None:
        with tempfile.TemporaryDirectory(dir=MODULE.ROOT) as td:
            root = Path(td)
            good = root / "good"
            good.mkdir()
            registry, review = self.make_authority_fixture(good)
            with mock.patch.object(MODULE, "REVIEW", review):
                authority, bindings = MODULE.validate_authority_after_claim(registry)
            self.assertEqual(authority["hyp010_terminal_row_sha256"], MODULE.PARENT_TERMINAL_ROW_SHA256)
            self.assertIn("comparator", {item["label"] for item in bindings})

            mutations = []
            for name in MODULE.TRUE_AUTHORITIES:
                mutations.append((name, lambda row, key=name: row["validation"].__setitem__(key, False)))
            for name in MODULE.FALSE_AUTHORITIES:
                mutations.append((name, lambda row, key=name: row["validation"].__setitem__(key, True)))
            mutations.extend((
                ("consumed", lambda row: row["metrics"].__setitem__("comparator_attempts_consumed", 1)),
                ("run_ids", lambda row: row.__setitem__("run_ids", ["bad"])),
                ("parent", lambda row: row["validation"].__setitem__("hyp010_terminal_row_sha256", "0" * 64)),
                ("summary", lambda row: row["validation"].__setitem__("frozen_summary_sha256", "0" * 64)),
                ("self", lambda row: row["validation"].__setitem__("reviewed_comparator_sha256", "0" * 64)),
            ))
            for index, (label, mutation) in enumerate(mutations):
                case = root / f"case_{index}"
                case.mkdir()
                registry, review = self.make_authority_fixture(case, mutation)
                with self.subTest(label=label), mock.patch.object(MODULE, "REVIEW", review):
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        MODULE.validate_authority_after_claim(registry)

    def test_failure_after_claim_writes_no_retry_terminal(self) -> None:
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
            self.assertFalse(terminal["same_id_retry_authorized"])


if __name__ == "__main__":
    unittest.main()
