from __future__ import annotations

import importlib.util
import inspect
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RUNNER_PATH = ROOT / (
    "03. EA Developer/EA_SupertrendBurstScalper/research/run_stbs001_mt5_audit.py"
)
SPEC = importlib.util.spec_from_file_location("stbs001_mt5_audit_under_test", RUNNER_PATH)
assert SPEC and SPEC.loader
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
BUILDER_PATH = RUNNER_PATH.with_name("build_stbs001_audit_packet.py")
BUILDER_SPEC = importlib.util.spec_from_file_location(
    "stbs001_packet_builder_under_test", BUILDER_PATH
)
assert BUILDER_SPEC and BUILDER_SPEC.loader
BUILDER = importlib.util.module_from_spec(BUILDER_SPEC)
BUILDER_SPEC.loader.exec_module(BUILDER)


class Stbs001Mt5AuditHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RUNNER_PATH.read_text(encoding="utf-8")
        cls.oracle_events = RUNNER.load_expected_events()

    def synthetic_journal(self, mutate=None) -> str:
        lines: list[str] = []
        for index, row in enumerate(self.oracle_events):
            exact = row["executable_event"] == 1
            if exact:
                direction = row["direction"]
                entry, stop, target = (
                    (2000.0, 1998.0, 2003.0)
                    if direction == "LONG"
                    else (2000.0, 2002.0, 1997.0)
                )
                fields = {
                    "source": "fixture",
                    "decision": "fixture",
                    "source_epoch": row["source_epoch"],
                    "decision_epoch": row["next_source_epoch"],
                    "direction": direction,
                    "exact_next": "true",
                    "atr_ready": "true",
                    "geometry_ready": "true",
                    "atr": 2.0,
                    "entry": entry,
                    "sl": stop,
                    "tp": target,
                    "volume": 0.1,
                    "audit": "true",
                }
            else:
                fields = {
                    "source": "fixture",
                    "decision": "fixture",
                    "source_epoch": row["source_epoch"],
                    "decision_epoch": row["next_source_epoch"],
                    "direction": row["direction"],
                    "exact_next": "false",
                    "consumed": "true",
                }
            if mutate:
                mutate(index, fields)
            lines.append("prefix STBS_SIGNAL|" + "|".join(f"{k}={v}" for k, v in fields.items()))
        summary = {
            "hypothesis": RUNNER.HYPOTHESIS_ID,
            "reason": 0,
            **RUNNER.EXPECTED_COUNTS,
            "entries": 0,
            "entry_rejects": 0,
            "closes": 0,
            "failed": "false",
        }
        lines.append("prefix STBS_SUMMARY|" + "|".join(f"{k}={v}" for k, v in summary.items()))
        return "\n".join(lines) + "\n"

    def validate_text(self, text: str):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.log"
            path.write_text(text, encoding="utf-8")
            return RUNNER.validate_signal_journal(path)

    def test_exact_parent_population_passes(self) -> None:
        result = self.validate_text(self.synthetic_journal())
        self.assertEqual(
            {name: result[name] for name in RUNNER.EXPECTED_COUNTS},
            RUNNER.EXPECTED_COUNTS,
        )
        self.assertEqual(result["journal_record_multiplicity"], 1)

    def test_uniform_identical_multi_root_duplicates_pass(self) -> None:
        journal = self.synthetic_journal()
        result = self.validate_text(journal + journal)
        self.assertEqual(result["journal_record_multiplicity"], 2)

    def test_conflicting_or_nonuniform_duplicates_fail(self) -> None:
        first_exact = next(i for i, row in enumerate(self.oracle_events) if row["executable_event"] == 1)

        def mutate(index, fields):
            if index == first_exact:
                fields["geometry_ready"] = "false"

        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            self.validate_text(self.synthetic_journal() + self.synthetic_journal(mutate))
        first_signal = self.synthetic_journal().splitlines()[0]
        with self.assertRaisesRegex(ValueError, "multiplicity"):
            self.validate_text(first_signal + "\n" + self.synthetic_journal())

    def test_missing_m15_exactness_fails(self) -> None:
        first_exact = next(i for i, row in enumerate(self.oracle_events) if row["executable_event"] == 1)

        def mutate(index, fields):
            if index == first_exact:
                fields["exact_next"] = "false"

        with self.assertRaisesRegex(ValueError, "parent mismatch"):
            self.validate_text(self.synthetic_journal(mutate))

    def test_atr_geometry_and_wrong_side_mutations_fail(self) -> None:
        first_exact = next(i for i, row in enumerate(self.oracle_events) if row["executable_event"] == 1)
        for field, value, error in (
            ("atr_ready", "false", "readiness"),
            ("geometry_ready", "false", "readiness"),
            ("sl", "WRONG_SIDE", "wrong-sided"),
            ("volume", "0", "invalid geometry"),
        ):
            def mutate(index, fields, field=field, value=value):
                if index == first_exact:
                    if value == "WRONG_SIDE":
                        fields[field] = "2001.0" if fields["direction"] == "LONG" else "1999.0"
                    else:
                        fields[field] = value

            with self.subTest(field=field), self.assertRaisesRegex(ValueError, error):
                self.validate_text(self.synthetic_journal(mutate))

    def test_trade_or_fatal_journal_lines_fail(self) -> None:
        for token in (
            "STBS_FATAL|fixture",
            "STBS_ENTRY_REQUEST|fixture",
            "STBS_CLOSE_REQUEST|fixture",
            "STBS_DEAL|fixture",
        ):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "forbidden"):
                self.validate_text(token + "\n" + self.synthetic_journal())

    def test_summary_failure_or_duplicate_signal_fails(self) -> None:
        text = self.synthetic_journal().replace("failed=false", "failed=true")
        with self.assertRaisesRegex(ValueError, "summary failed mismatch"):
            self.validate_text(text)

    def test_orders_parser_requires_exact_empty_shape(self) -> None:
        report = ROOT / "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/report.html"
        html = report.read_text(encoding="utf-16")
        self.assertTrue(RUNNER.orders_section_is_empty(html))
        orders = html.find("<b>Các lệnh đặt</b>")
        deals = html.find("<b>Deals</b>", orders)
        self.assertGreaterEqual(orders, 0)
        self.assertGreater(deals, orders)
        mutated = html[:deals] + '<tr><td>rogue order</td></tr>' + html[deals:]
        self.assertFalse(RUNNER.orders_section_is_empty(mutated))

    def test_alpha_command_is_exact_model0_preload_and_no_telemetry_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            receipt.write_text("{}\n", encoding="utf-8")
            command = RUNNER.build_alpha_command(receipt)
        joined = " ".join(command)
        self.assertIn("-Period M15", joined)
        self.assertIn("-From 2005.01.01 -To 2023.01.01", joined)
        self.assertIn("-Model 0", joined)
        self.assertIn("-Overrides InpAuditOnly=true", joined)
        self.assertNotIn("InpEnableTelemetry", joined)
        self.assertIn("-TelemetryTier off", joined)

    def test_claim_precedes_parent_oracle_and_alpha_reads(self) -> None:
        marker = self.source.index("write_exclusive(\n        marker")
        bound = self.source.index("validate_bound_files_after_claim(row, contract_receipt)")
        alpha = self.source.index("completed = subprocess.run(")
        self.assertLess(marker, bound)
        self.assertLess(bound, alpha)
        self.assertLess(alpha, self.source.index("validated = validate_run"))

    def test_contract_receipt_bytes_are_not_read_before_mt5_claim(self) -> None:
        preclaim = inspect.getsource(RUNNER.validate_authority_metadata)
        marker_payload = inspect.getsource(RUNNER.execute).split(
            "validate_bound_files_after_claim", 1
        )[0]
        postclaim = inspect.getsource(RUNNER.validate_bound_files_after_claim)
        self.assertNotIn("sha256_file(contract_receipt)", preclaim)
        self.assertNotIn("sha256_file(contract_receipt)", marker_payload)
        self.assertIn("contract_receipt.read_text", postclaim)

    def test_packet_build_claim_is_exclusive_and_precedes_bound_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            attempt_root = Path(directory) / "attempt"
            marker = BUILDER.claim_packet_attempt(attempt_root)
            self.assertTrue(marker.is_file())
            payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(payload["attempt_id"], BUILDER.PACKET_ATTEMPT_ID)
            self.assertFalse(payload["same_id_retry_authorized"])
            with self.assertRaises(FileExistsError):
                BUILDER.claim_packet_attempt(attempt_root)
        main_source = inspect.getsource(BUILDER.main)
        self.assertLess(
            main_source.index("claim_packet_attempt()"),
            main_source.index("build_packet(marker)"),
        )
        self.assertIn('"status": "FAILED"', main_source)
        self.assertIn('"status": "COMPLETE"', main_source)

    def test_runner_requires_completed_packet_stage(self) -> None:
        authority = inspect.getsource(RUNNER.validate_authority_metadata)
        postclaim = inspect.getsource(RUNNER.validate_bound_files_after_claim)
        for token in (
            'validation.get("packet_build_attempt_id")',
            'validation.get("packet_build_attempt_limit") == 1',
            'metrics.get("packet_build_attempts_consumed") == 1',
            'validation.get("packet_build_attempt_terminal_sha256"',
        ):
            self.assertIn(token, authority)
        self.assertIn('terminal.get("status") == "COMPLETE"', postclaim)
        self.assertIn('receipt.get("authority_row_sha256")', postclaim)

    def test_packet_attempt_root_is_exactly_ignored_and_hash_bound(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        exact = (
            "03. EA Developer/EA_SupertrendBurstScalper/research/evidence/"
            "HYP-STBS-XAUUSD-M15-001/STBS001-PACKET-BUILD-001/"
        )
        self.assertEqual(gitignore.count(exact), 1)
        builder = BUILDER_PATH.read_text(encoding="utf-8")
        self.assertIn('file_evidence("gitignore", gitignore)', builder)
        self.assertIn('"gitignore": "gitignore"', self.source)

    def test_run_snapshot_paths_and_hashes_are_exact(self) -> None:
        required = (
            'snapshot_root / "source" / f"{EA_NAME}.mq5"',
            'snapshot_root / "build" / f"{EA_NAME}.ex5"',
            'snapshot_root / "config" / "config.ini"',
            'manifest.get("ex5_sha256") == sha256_file(ex5_snapshot)',
            'manifest.get("tester_ex5_sha256") == sha256_file(ex5_snapshot)',
            'manifest.get("config_sha256") == sha256_file(config_snapshot)',
        )
        for token in required:
            self.assertIn(token, self.source)

    def test_all_broad_permissions_fail_closed(self) -> None:
        required_false = {
            "trade_api_authorized",
            "performance_metrics_authorized",
            "outcome_prices_authorized",
            "post_event_ohlc_authorized",
            "economics_authorized",
            "packet_build_authorized",
            "source_run_authorized",
            "artifact_collection_authorized",
            "comparator_execution_authorized",
            "optimization_authorized",
            "validation_authorized",
            "holdout_authorized",
            "research_validation_access_authorized",
            "research_holdout_access_authorized",
            "model4_authorized",
            "model4_data_acquisition_authorized",
            "model4_performance_authorized",
            "visual_mode_authorized",
            "network_authorized",
            "paid_requests_authorized",
            "promotion_eligible",
            "paper_trading_authorized",
            "live_trading_authorized",
            "market_edge_claim_authorized",
            "compile_authorized",
            "standalone_compile_authorized",
            "same_id_retry_authorized",
            "registry_mutation_allowed",
        }
        for field in required_false:
            self.assertIn(f'"{field}"', self.source)
        self.assertIn('validation.get("mql5_compile_authorized") is True', self.source)

    def test_attempt_root_is_absent_before_authority(self) -> None:
        self.assertFalse(RUNNER.OUTPUT_DIR.exists())
        self.assertFalse(BUILDER.PACKET_EVIDENCE_DIR.exists())

    def test_packet_build_and_mt5_authority_are_two_distinct_rows(self) -> None:
        builder = BUILDER_PATH.read_text(encoding="utf-8")
        self.assertIn('row.get("state") == "probe"', builder)
        self.assertIn('"FROZEN_STBS001_PACKET_BUILD_AUTHORIZED"', builder)
        self.assertIn('validation.get("packet_build_authorized") is True', builder)
        self.assertIn('validation.get("mt5_audit_run_authorized") is False', builder)
        self.assertIn('row.get("state") == "screened"', self.source)
        self.assertIn('"FROZEN_STBS001_MT5_AUDIT_AUTHORIZED"', self.source)
        self.assertIn('validation.get("contract_receipt_sha256", "")', self.source)
        self.assertIn('validation["contract_receipt_sha256"]', self.source)


if __name__ == "__main__":
    unittest.main()
