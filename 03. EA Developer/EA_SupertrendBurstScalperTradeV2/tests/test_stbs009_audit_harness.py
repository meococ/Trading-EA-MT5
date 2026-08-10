from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV2"
RESEARCH = PACKAGE / "research"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_module("stbs009_builder", RESEARCH / "build_stbs009_audit_packet.py")
RUNNER = load_module("stbs009_runner", RESEARCH / "run_stbs009_model0_audit.py")


class HarnessIdentityTests(unittest.TestCase):
    def synthetic_probe(self) -> tuple[bytes, dict]:
        registry_raw = BUILDER.REGISTRY.read_bytes()
        parent_raw, _ = BUILDER.latest_row_from_bytes(registry_raw, BUILDER.PARENT)
        validation = {field: False for field in BUILDER.PROBE_FALSE_FIELDS}
        validation.update({
            "authority": BUILDER.AUTHORITY,
            "packet_build_authorized": True,
            "packet_build_attempt_id": BUILDER.PACKET_ATTEMPT,
            "packet_build_attempt_limit": 1,
            "model0_audit_attempt_id": BUILDER.RUN_ATTEMPT,
            "model0_audit_attempt_limit": 1,
            "hyp008_terminal_row_sha256": BUILDER.sha_bytes(parent_raw),
            "reviewed_packet_builder_sha256": BUILDER.sha_file(BUILDER.BUILDER),
            "reviewed_model0_audit_launcher_sha256": BUILDER.sha_file(BUILDER.RUNNER),
            "reviewed_audit_harness_test_sha256": BUILDER.sha_file(BUILDER.HARNESS_TEST),
            "reviewed_source_contract_test_sha256": BUILDER.sha_file(BUILDER.SOURCE_TEST),
            "reviewed_source_scenario_test_sha256": BUILDER.sha_file(BUILDER.SCENARIO_TEST),
            "governance_addendum_sha256": BUILDER.sha_file(BUILDER.GOVERNANCE_ADDENDUM),
            "static_engineering_result_sha256": BUILDER.sha_file(BUILDER.STATIC_RESULT),
            "nonrepaint_manifest_sha256": BUILDER.sha_file(BUILDER.NONREPAINT_MANIFEST),
            "nonrepaint_audit_sha256": BUILDER.sha_file(BUILDER.NONREPAINT_AUDIT),
            "ea_contract_sha256": BUILDER.sha_file(BUILDER.EA_CONTRACT),
            "static_ex5_sha256": BUILDER.sha_file(BUILDER.EX5),
            "static_compile_log_sha256": BUILDER.sha_file(BUILDER.COMPILE_LOG),
            "cost_source_manifest_sha256": BUILDER.sha_file(BUILDER.COST),
            "hyp008_failure_sha256": BUILDER.sha_file(BUILDER.HYP008_FAILURE),
            "hyp008_independent_review_sha256": BUILDER.sha_file(BUILDER.HYP008_REVIEW),
            "independent_pre_packet_review_sha256": BUILDER.sha_file(BUILDER.PRE_PACKET_REVIEW),
            "gitignore_sha256": BUILDER.sha_file(BUILDER.GITIGNORE),
            "alphafactory_sha256": BUILDER.sha_file(BUILDER.ALPHA),
            "quant_analyzer_sha256": BUILDER.sha_file(BUILDER.QUANT_ANALYZER),
            "parent_oracle_sha256": BUILDER.ORACLE_SHA256,
        })
        row = {
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": BUILDER.HYPOTHESIS,
            "ea_name": "EA_SupertrendBurstScalperTradeV2",
            "state": "probe", "parent_candidate": BUILDER.PARENT,
            "feature_family": "h1-supertrend-fastpath-audit",
            "lane": "XAUUSD-M15-STBS009-AUDIT", "symbol": "XAUUSD",
            "timeframe": "M15", "window": {"from": "2018.01.01", "to": "2022.12.31"},
            "model": 0, "source_path": BUILDER.repo_path(BUILDER.SOURCE),
            "source_hash": BUILDER.sha_file(BUILDER.SOURCE),
            "prereg_path": BUILDER.repo_path(BUILDER.PREREG),
            "prereg_sha256": BUILDER.sha_file(BUILDER.PREREG),
            "exact_overrides": "InpAuditOnly=true",
            "evidence_contract_kind": "data_acquisition",
            "data_acceptance_contract": BUILDER.EXPECTED_DATA_ACCEPTANCE,
            "verdict": "FROZEN_STBS009_PACKET_BUILD_AUTHORIZED",
            "updated_at_utc": "2026-08-09T10:00:00Z", "run_ids": [],
            "metrics": {
                "packet_build_attempts_consumed": 0,
                "model0_audit_attempts_consumed": 0,
                "run_compile_attempts_consumed": 0, "model0_runs": 0,
                "mt5_launches": 0, "orders_executed": 0, "trades_simulated": 0,
                "returns_computed": 0, "performance_trials_executed": 0,
                "economics_executed": False, "research_validation_opened": False,
                "research_holdout_opened": False,
            },
            "validation": validation,
        }
        return registry_raw, row

    def test_fresh_ids_and_audit_contract_are_exact(self) -> None:
        self.assertEqual(BUILDER.HYPOTHESIS, "HYP-STBS-XAUUSD-M15-009")
        self.assertEqual(BUILDER.PACKET_ATTEMPT, "STBS009-PACKET-BUILD-001")
        self.assertEqual(BUILDER.RUN_ATTEMPT, "STBS009-MODEL0-AUDIT-001")
        self.assertEqual(RUNNER.RUN_ATTEMPT, "STBS009-MODEL0-AUDIT-001")
        self.assertEqual(RUNNER.EA_NAME, "EA_SupertrendBurstScalperTradeV2")
        self.assertEqual(RUNNER.EXACT_OVERRIDES, "InpAuditOnly=true")
        self.assertEqual(RUNNER.AUTHORITY, "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE")

    def test_authority_surface_forbids_trade_and_economics(self) -> None:
        for field in (
            "trade_api_authorized", "performance_metrics_authorized",
            "outcome_prices_authorized", "post_event_ohlc_authorized",
            "economics_authorized", "optimization_authorized",
            "validation_authorized", "holdout_authorized",
            "paper_trading_authorized", "live_trading_authorized",
            "same_id_retry_authorized", "registry_mutation_allowed",
        ):
            self.assertIn(field, BUILDER.PROBE_FALSE_FIELDS)
            self.assertIn(field, RUNNER.RUN_FALSE_FIELDS)
        self.assertEqual(
            set(RUNNER.RUN_TRUE_FIELDS),
            {
                "model0_audit_run_authorized", "mt5_authorized", "model0_authorized",
                "model0_data_acquisition_authorized", "run_compile_authorized",
                "mql5_compile_authorized", "artifact_collection_authorized",
                "comparator_execution_authorized",
            },
        )

    def test_frozen_parent_oracle_hash_is_literal_and_current(self) -> None:
        self.assertEqual(BUILDER.ORACLE_SHA256, RUNNER.ORACLE_SHA256)
        self.assertEqual(BUILDER.sha_file(BUILDER.ORACLE), BUILDER.ORACLE_SHA256)

    def test_claim_precedes_every_bound_read_or_alpha_launch(self) -> None:
        builder_text = BUILDER.BUILDER.read_text(encoding="utf-8")
        runner_text = RUNNER.RUNNER.read_text(encoding="utf-8")
        self.assertLess(builder_text.index("marker = claim_packet()"),
                        builder_text.index("result = build_packet(marker)"))
        execute_text = runner_text[runner_text.index("def execute(declared_receipt_sha") :]
        self.assertLess(execute_text.index("marker = claim(declared_receipt_sha)"),
                        execute_text.index("validate_authority_after_claim(marker"))
        self.assertLess(execute_text.index("validate_packet_chain_after_claim(row)"),
                        execute_text.index("subprocess.run(command"))

    def test_alpha_command_is_frozen_audit_only_300_seconds(self) -> None:
        command = RUNNER.build_alpha_command("A" * 64)
        self.assertIn("EA_SupertrendBurstScalperTradeV2", command)
        self.assertEqual(command[command.index("-Model") + 1], "0")
        self.assertEqual(command[command.index("-TimeoutSec") + 1], "300")
        self.assertEqual(command[command.index("-Overrides") + 1], "InpAuditOnly=true")
        self.assertEqual(command[command.index("-From") + 1], "2005.01.01")
        self.assertEqual(command[command.index("-To") + 1], "2023.01.01")

    def test_packet_data_acceptance_and_chronology_fail_closed(self) -> None:
        receipt = {"data_acceptance_contract": RUNNER.EXPECTED_DATA_ACCEPTANCE}
        task = {"data_acceptance_contract": RUNNER.EXPECTED_DATA_ACCEPTANCE}
        RUNNER.require_data_acceptance_documents(receipt, task)
        bad = dict(RUNNER.EXPECTED_DATA_ACCEPTANCE)
        bad["require_series_proof"] = False
        with self.assertRaisesRegex(ValueError, "data-acceptance"):
            RUNNER.require_data_acceptance_documents(receipt, {"data_acceptance_contract": bad})
        times = [f"2026-08-09T10:0{minute}:00Z" for minute in range(6)]
        RUNNER.require_packet_chronology(*times)
        with self.assertRaisesRegex(ValueError, "chronology"):
            RUNNER.require_packet_chronology(times[0], times[2], times[1], *times[3:])

    def test_success_terminal_binds_attempt_start(self) -> None:
        runner_text = RUNNER.RUNNER.read_text(encoding="utf-8")
        complete_block = runner_text[runner_text.index('"status": "COMPLETE"') :]
        self.assertIn('"attempt_started_sha256": sha_file(marker)', complete_block)

    def test_attempt_roots_are_absent_before_authority(self) -> None:
        self.assertFalse(BUILDER.PACKET_ROOT.exists())
        self.assertFalse(RUNNER.ATTEMPT_ROOT.exists())

    def test_synthetic_probe_matches_builder_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            review = Path(tmp) / "review.md"
            review.write_text(
                "# HYP009 independent pre-packet review\n\n"
                "Verdict: `PASS_PRE_PACKET_AUTHORITY`\n",
                encoding="utf-8",
            )
            registry_raw, row = self.synthetic_probe()
            row["validation"]["independent_pre_packet_review_sha256"] = BUILDER.sha_file(review)
            candidate_raw = json.dumps(row, separators=(",", ":")).encode("utf-8")
            with mock.patch.object(BUILDER, "PRE_PACKET_REVIEW", review):
                raw, validated = BUILDER.validate_packet_authority(
                    registry_raw.rstrip(b"\n") + b"\n" + candidate_raw + b"\n"
                )
        self.assertEqual(raw, candidate_raw)
        self.assertEqual(validated["hypothesis_id"], BUILDER.HYPOTHESIS)

    def test_probe_rejects_any_trade_permission(self) -> None:
        registry_raw, row = self.synthetic_probe()
        row["validation"]["trade_api_authorized"] = True
        candidate_raw = json.dumps(row, separators=(",", ":")).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "no_run_permissions"):
            BUILDER.validate_packet_authority(
                registry_raw.rstrip(b"\n") + b"\n" + candidate_raw + b"\n"
            )

    def test_probe_rejects_oracle_hash_substitution(self) -> None:
        registry_raw, row = self.synthetic_probe()
        row["validation"]["parent_oracle_sha256"] = "A" * 64
        candidate_raw = json.dumps(row, separators=(",", ":")).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "parent_oracle_sha256|frozen ST003 oracle"):
            BUILDER.validate_packet_authority(
                registry_raw.rstrip(b"\n") + b"\n" + candidate_raw + b"\n"
            )


class RunManifestContractTests(unittest.TestCase):
    @staticmethod
    def funding_report() -> str:
        header = "".join(
            f"<td{' colspan=2' if i in (4, 8) else ''}><b>h{i}</b></td>"
            for i in range(11)
        )
        values = [
            "2005.01.01 00:00:00", "1", "", "balance", "", "0.00", "0.00", "",
            "0.00", "0.00", "10000.00", "10000.00", "",
        ]
        return (
            f"<table><b>Orders</b><tr>{header}</tr><tr><td></td></tr>"
            "<b>Deals</b><tr><td>Time</td></tr>"
            f"<tr>{''.join(f'<td>{value}</td>' for value in values)}</tr></table>"
        )

    @staticmethod
    def config_text(run_id: str) -> str:
        return (
            "[Tester]\n"
            f"Expert=AlphaFactoryRuns\\{RUNNER.EA_NAME}\\{run_id}\\{RUNNER.EA_NAME}.ex5\n"
            "Symbol=XAUUSD\nPeriod=M15\nOptimization=0\nVisual=0\nModel=0\n"
            "ExecutionMode=0\nDates=2\nFromDate=2005.01.01\nToDate=2023.01.01\n"
            f"Report=MQL5\\Profiles\\Tester\\AlphaRuns\\{run_id}\\report.html\n"
            "ReplaceReport=1\nShutdownTerminal=1\nDeposit=10000\nCurrency=USD\n"
            "Leverage=100\n[TesterInputs]\nInpAuditOnly=true||true||0||true||N\n"
        )

    def build_fixture(self, base: Path) -> tuple[Path, dict, dict[str, Path]]:
        run_id = "20260809_123456"
        runs_root = base / "runs" / RUNNER.EA_NAME
        run_dir = runs_root / run_id
        snapshot = run_dir / "snapshot"
        source_snapshot = snapshot / "source" / f"{RUNNER.EA_NAME}.mq5"
        ex5_snapshot = snapshot / "build" / f"{RUNNER.EA_NAME}.ex5"
        config_snapshot = snapshot / "config" / "config.ini"
        staged_root = base / "tester_experts" / RUNNER.EA_NAME
        staged_ex5 = staged_root / run_id / f"{RUNNER.EA_NAME}.ex5"
        alpha_tester = base / "AlphaTester"
        live_config = alpha_tester / run_id / "config.ini"
        canonical_ex5 = base / "package" / f"{RUNNER.EA_NAME}.ex5"
        run_compile_log = base / "attempt" / "run_compile_log.bin"
        receipt = base / "receipt.json"
        report = run_dir / "report.html"
        journal = run_dir / "logs" / "tester_journal_delta.log"
        summary = run_dir / "analysis" / "enhanced_summary.json"
        for path in (
            source_snapshot, ex5_snapshot, config_snapshot, staged_ex5, live_config,
            canonical_ex5, run_compile_log, receipt, report, journal, summary,
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
        source_snapshot.write_bytes(RUNNER.SOURCE.read_bytes())
        for path in (ex5_snapshot, staged_ex5, canonical_ex5):
            path.write_bytes(b"fresh-run-ex5")
        config = self.config_text(run_id)
        config_snapshot.write_text(config, encoding="utf-8")
        live_config.write_text(config, encoding="utf-8")
        run_compile_log.write_text("Result: 0 errors, 0 warnings\n", encoding="utf-8")
        receipt.write_text("{}\n", encoding="utf-8")
        report.write_text(self.funding_report(), encoding="utf-16")
        journal.write_text(JournalContractTests().make_journal(1), encoding="utf-8")
        summary.write_text(json.dumps({
            "schema_version": "alphafactory_zero_trade_collection_summary.v1",
            "n_trades": 0, "performance_metrics_authorized": False,
        }), encoding="utf-8")
        ex5_sha = RUNNER.sha_file(ex5_snapshot)
        config_sha = RUNNER.sha_file(config_snapshot)
        journal_sha = RUNNER.sha_file(journal)
        manifest = {
            "schema_version": "alphafactory_run_manifest.v2", "run_id": run_id,
            "hypothesis_id": RUNNER.HYPOTHESIS, "run_role": "control",
            "ea_name": RUNNER.EA_NAME, "symbol": "XAUUSD", "period": "M15",
            "from": "2005.01.01", "to": "2023.01.01", "model": 0,
            "execution_mode": 0, "fixed_delay_ms": 0, "timeout_sec": 300,
            "overrides": RUNNER.EXACT_OVERRIDES, "deposit": 10000, "leverage": 100,
            "spread": "current", "telemetry_tier": "off", "telemetry_profile": "none",
            "visual_mode": False, "indicator_dependencies": [],
            "main_file": str(RUNNER.SOURCE.resolve()),
            "compiled_ex5_file": str(canonical_ex5.resolve()),
            "ex5_file": str(staged_ex5.resolve()), "tester_ex5_path": str(staged_ex5.resolve()),
            "config_file": str(live_config.resolve()), "local_run_dir": str(run_dir.resolve()),
            "report_path": str(report.resolve()), "snapshot_root": str(snapshot.resolve()),
            "source_snapshot": str(source_snapshot.resolve()),
            "ex5_snapshot": str(ex5_snapshot.resolve()),
            "config_snapshot": str(config_snapshot.resolve()), "include_snapshots": [],
            "source_sha256": RUNNER.SOURCE_SHA256, "ex5_sha256": ex5_sha,
            "tester_ex5_sha256": ex5_sha, "config_sha256": config_sha,
            "report_sha256": RUNNER.sha_file(report),
            "includes_sha256": hashlib.sha256(b"").hexdigest().upper(),
            "required_sidecars": [],
            "sidecars": [{"path": "logs/tester_journal_delta.log", "sha256": journal_sha,
                          "length": journal.stat().st_size, "row_count": None}],
            "contract_receipt_sha256": RUNNER.sha_file(receipt),
            "contract_symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
            "data_quality_gate": {
                "history_quality": 98, "actual_from": "2004.06.11",
                "actual_to": "2026.07.30", "coverage_class": "FULL_2018_PLUS",
                "journal_path": "logs/tester_journal_delta.log", "journal_sha256": journal_sha,
                "journal_truncated": False,
                "series_proof": {"m5_synchronized": 1, "copytime_result": 1,
                                 "copytime_last_error": 0, "copytime_first_epoch": 1,
                                 "m5_first_epoch": 1},
            },
        }
        manifest_path = run_dir / "run_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        paths = {
            "runs_root": runs_root, "staged_root": staged_root,
            "alpha_tester": alpha_tester, "canonical_ex5": canonical_ex5,
            "run_compile_log": run_compile_log, "receipt": receipt,
            "manifest": manifest_path, "staged_ex5": staged_ex5,
            "config_snapshot": config_snapshot,
        }
        return run_dir.resolve(), manifest, paths

    def patch_fixture(self, paths: dict[str, Path]):
        return mock.patch.multiple(
            RUNNER, RUNS_ROOT=paths["runs_root"], TESTER_EXPERTS_ROOT=paths["staged_root"],
            ALPHA_TESTER_ROOT=paths["alpha_tester"], CANONICAL_EX5=paths["canonical_ex5"],
            RUN_COMPILE_LOG_ARCHIVE=paths["run_compile_log"], RECEIPT=paths["receipt"],
        )

    def test_exact_manifest_config_and_staged_ex5_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, _, paths = self.build_fixture(Path(tmp))
            with self.patch_fixture(paths):
                result = RUNNER.validate_run(run_dir)
        self.assertEqual(result["counts"]["executable"], 683)

    def test_manifest_contract_mutations_fail_closed(self) -> None:
        mutations = {
            "schema_version": "wrong", "run_role": "train", "deposit": 9999,
            "leverage": 500, "spread": "10", "visual_mode": True,
            "required_sidecars": ["bad"],
            "contract_symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                run_dir, manifest, paths = self.build_fixture(Path(tmp))
                manifest[field] = value
                paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
                with self.patch_fixture(paths), self.assertRaisesRegex(ValueError, "manifest mismatch"):
                    RUNNER.validate_run(run_dir)

    def test_tampered_staged_ex5_and_config_fail_closed(self) -> None:
        for target in ("staged_ex5", "config_snapshot"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                run_dir, _, paths = self.build_fixture(Path(tmp))
                paths[target].write_bytes(paths[target].read_bytes() + b"tamper")
                with self.patch_fixture(paths), self.assertRaises(ValueError):
                    RUNNER.validate_run(run_dir)

    def test_exact_new_run_set_rejects_extra_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            old = root / "20260809_123455"
            intended = root / "20260809_123456"
            extra = root / "20260809_123457"
            with mock.patch.object(RUNNER, "RUNS_ROOT", root):
                RUNNER.require_exact_new_run({old}, {old, intended}, intended)
                with self.assertRaisesRegex(ValueError, "exactly a fresh"):
                    RUNNER.require_exact_new_run({old}, {old, intended, extra}, intended)
                with self.assertRaisesRegex(ValueError, "exactly a fresh"):
                    RUNNER.require_exact_new_run({old}, {intended}, intended)

    def test_static_compile_archives_use_single_authorized_buffers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ex5 = root / "static.ex5"
            log = root / "static.log"
            ex5_archive = root / "evidence" / "static.ex5"
            log_archive = root / "evidence" / "static.log"
            ex5.write_bytes(b"authorized-ex5")
            log.write_text("Result: 0 errors, 0 warnings\n", encoding="utf-16")
            validation = {
                "static_ex5_sha256": BUILDER.sha_file(ex5),
                "static_compile_log_sha256": BUILDER.sha_file(log),
            }
            original_capture = BUILDER.stable_bytes

            def capture_then_mutate(path: Path) -> bytes:
                raw = original_capture(path)
                if path == ex5:
                    path.write_bytes(b"changed-after-authorized-capture")
                return raw

            with mock.patch.multiple(
                BUILDER, EX5=ex5, COMPILE_LOG=log,
                STATIC_EX5_ARCHIVE=ex5_archive, STATIC_LOG_ARCHIVE=log_archive,
            ), mock.patch.object(BUILDER, "stable_bytes", side_effect=capture_then_mutate):
                BUILDER.archive_static_compile(validation)
            self.assertEqual(ex5_archive.read_bytes(), b"authorized-ex5")
            self.assertNotEqual(ex5_archive.read_bytes(), ex5.read_bytes())

    def test_static_compile_authority_hash_mutation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ex5 = root / "static.ex5"
            log = root / "static.log"
            ex5.write_bytes(b"actual-ex5")
            log.write_text("Result: 0 errors, 0 warnings\n", encoding="utf-16")
            with mock.patch.multiple(
                BUILDER, EX5=ex5, COMPILE_LOG=log,
                STATIC_EX5_ARCHIVE=root / "out.ex5", STATIC_LOG_ARCHIVE=root / "out.log",
            ), self.assertRaisesRegex(ValueError, "packet authority"):
                BUILDER.archive_static_compile({
                    "static_ex5_sha256": "A" * 64,
                    "static_compile_log_sha256": BUILDER.sha_file(log),
                })


class JournalContractTests(unittest.TestCase):
    def make_journal(self, multiplicity: int = 2) -> str:
        oracle_rows = RUNNER.load_oracle_rows()
        by_server_epoch = {int(row["source_epoch"]): row for row in oracle_rows}
        events = [row for row in oracle_rows if row.get("raw_event") == 1]
        events.sort(key=lambda row: int(row["source_epoch"]))
        records: list[str] = []
        for row in events:
            direction = row["direction"]
            next_row = by_server_epoch[int(row["next_source_epoch"])]
            source_utc = RUNNER.iso_epoch(row["time_utc"])
            decision_utc = RUNNER.iso_epoch(next_row["time_utc"])
            source_server = RUNNER.server_axis_text(int(row["source_epoch"]))
            decision_server = RUNNER.server_axis_text(int(row["next_source_epoch"]))
            if row["executable_event"] == 1:
                sl, tp = (1.0, 3.0) if direction == "LONG" else (3.0, 1.0)
                payload = (
                    f"STBS_SIGNAL|source={source_server}|decision={decision_server}|"
                    f"source_epoch={source_utc}|decision_epoch={decision_utc}|"
                    f"direction={direction}|exact_next=true|atr_ready=true|geometry_ready=true|"
                    f"atr=1.0|entry=2.0|sl={sl}|tp={tp}|volume=1.0|audit=true"
                )
            else:
                payload = (
                    f"STBS_SIGNAL|source={source_server}|decision={decision_server}|"
                    f"source_epoch={source_utc}|decision_epoch={decision_utc}|"
                    f"direction={direction}|exact_next=false|consumed=true"
                )
            records.extend([payload] * multiplicity)
        summary = (
            "STBS_SUMMARY|hypothesis=HYP-STBS-XAUUSD-M15-009|reason=1|raw=690|"
            "executable=683|gaps=7|long=339|short=344|atr_ready=683|"
            "geometry_ready=683|entries=0|entry_rejects=0|closes=0|"
            "exec_state=0|exit_intent=0|failed=false"
        )
        records.extend([summary] * multiplicity)
        return "\n".join(records) + "\n"

    def test_duplicate_journal_normalizes_to_exact_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.log"
            path.write_text(self.make_journal(), encoding="utf-8")
            result = RUNNER.validate_signal_journal(path)
        self.assertEqual(result["raw"], 690)
        self.assertEqual(result["executable"], 683)
        self.assertEqual(result["journal_record_multiplicity"], 2)

    def test_conflicting_duplicate_signal_fails(self) -> None:
        text = self.make_journal()
        text = text.replace("|direction=LONG|", "|direction=SHORT|", 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.log"
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
                RUNNER.validate_signal_journal(path)

    def test_any_order_gateway_record_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.log"
            path.write_text(self.make_journal(1) + "STBS_REQUEST_RESULT|request_id=1\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "forbidden"):
                RUNNER.validate_signal_journal(path)


class ReportContractTests(unittest.TestCase):
    @staticmethod
    def funding_report(side: str = "balance", heading: str = "Orders") -> str:
        header = "".join(
            f"<td{' colspan=2' if i in (4, 8) else ''}><b>h{i}</b></td>"
            for i in range(11)
        )
        deal_cells = [
            "2005.01.01 00:00:00", "1", "", side, "", "0.00", "0.00", "",
            "0.00", "0.00", "10000.00", "10000.00", "",
        ]
        return (
            f"<table><b>{heading}</b><tr>{header}</tr><tr><td></td></tr>"
            "<b>Deals</b><tr><td>Time</td></tr>"
            f"<tr>{''.join(f'<td>{value}</td>' for value in deal_cells)}</tr></table>"
        )

    def test_exact_empty_orders_shape(self) -> None:
        self.assertTrue(RUNNER.orders_section_is_empty(self.funding_report()))
        self.assertTrue(RUNNER.orders_section_is_empty(
            self.funding_report(heading="C\u00e1c l\u1ec7nh \u0111\u1eb7t")
        ))
        self.assertFalse(RUNNER.orders_section_is_empty(
            self.funding_report().replace("colspan=2", "colspan=bad", 1)
        ))
        self.assertFalse(RUNNER.orders_section_is_empty(
            self.funding_report(heading="CÃ¡c lá»‡nh Ä‘áº·t")
        ))
        duplicate = self.funding_report().replace("<b>Deals</b>", "<b>Orders</b><b>Deals</b>")
        self.assertFalse(RUNNER.orders_section_is_empty(duplicate))

    def test_only_exact_funding_deal_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.html"
            bad = Path(tmp) / "bad.html"
            good.write_text(self.funding_report(), encoding="utf-16")
            bad.write_text(self.funding_report("buy"), encoding="utf-16")
            RUNNER.exact_funding_only(good)
            with self.assertRaisesRegex(ValueError, "sole tester-start funding"):
                RUNNER.exact_funding_only(bad)


if __name__ == "__main__":
    unittest.main()
