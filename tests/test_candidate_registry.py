import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "03. EA Developer" / "EA_SonicR" / "research"
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

import validate_candidate_registry as registry_validator  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def flatten_schema_errors(errors):
    for error in errors:
        yield error
        yield from flatten_schema_errors(error.context)


class CandidateRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (RESEARCH_DIR / "CANDIDATE_REGISTRY.schema.json").read_text(
                encoding="utf-8-sig"
            )
        )
        cls.rows = [
            json.loads(line)
            for line in (RESEARCH_DIR / "CANDIDATE_REGISTRY.jsonl")
            .read_text(encoding="utf-8-sig")
            .splitlines()
            if line.strip()
        ]

    def test_current_whole_ledger_passes_schema_and_semantics(self) -> None:
        self.assertEqual(registry_validator.WORKSPACE, ROOT)
        self.assertEqual(len(self.rows), 54)
        for row in self.rows:
            with self.subTest(row=row.get("hypothesis_id") or row.get("record_type")):
                jsonschema.validate(row, self.schema)
                self.assertEqual(registry_validator.validate_row_semantics(row), [])

    def test_evidence_free_confirmed_row_is_rejected(self) -> None:
        row = copy.deepcopy(self.rows[-1])
        row["state"] = "confirmed"
        row["verdict"] = "confirm"
        row["metrics"].update(
            {
                "trades": 100,
                "elapsed_days": 365,
                "elapsed_calendar_weeks": 365 / 7,
                "trades_per_elapsed_week": 100 / (365 / 7),
                "cost_pf_x1": 1.31,
                "cost_pf_x1_5": 1.25,
                "cost_pf_x2": 1.0,
                "net_r_x1_5": 1.0,
            }
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(row, self.schema)

    def test_portfolio_state_requires_portfolio_only_artifacts(self) -> None:
        row = copy.deepcopy(self.rows[-1])
        row["state"] = "portfolio-sleeve"
        row["verdict"] = "portfolio-candidate"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(row, self.schema)

    def test_promotion_states_require_model_zero(self) -> None:
        for state in ("challenger", "confirmed", "portfolio-sleeve"):
            with self.subTest(state=state):
                row = copy.deepcopy(self.rows[-1])
                row["state"] = state
                errors = list(
                    flatten_schema_errors(
                        jsonschema.Draft202012Validator(self.schema).iter_errors(row)
                    )
                )
                self.assertTrue(
                    any("model" in list(error.absolute_path) for error in errors),
                    f"{state} must fail specifically on non-Model-0 evidence",
                )

    def test_offline_target_cannot_enter_evidence_states_under_same_id(self) -> None:
        prior_offline = copy.deepcopy(self.rows[-1])
        for state in ("challenger", "confirmed", "portfolio-sleeve"):
            with self.subTest(state=state):
                row = copy.deepcopy(prior_offline)
                row["state"] = state
                row["model"] = 0
                errors = registry_validator.validate_row_semantics(
                    row, prior_rows=[prior_offline]
                )
                self.assertTrue(
                    any("offline/preflight target requires a new hypothesis_id" in error for error in errors)
                )

    def test_generic_offline_metadata_cannot_bypass_target_guard(self) -> None:
        prior_offline = copy.deepcopy(self.rows[-1])
        prior_offline["hypothesis_id"] = "HYP-GENERIC-OFFLINE-PREFLIGHT-001"
        row = copy.deepcopy(prior_offline)
        row["state"] = "challenger"
        row["model"] = 0
        errors = registry_validator.validate_row_semantics(
            row, prior_rows=[prior_offline]
        )
        self.assertTrue(
            any("offline/preflight target requires a new hypothesis_id" in error for error in errors)
        )
        intermediate = copy.deepcopy(prior_offline)
        intermediate.update(
            {
                "state": "screened",
                "model": 1,
                "setup_type": "EA patch screen",
                "source_provenance": "matched tester evidence",
                "exact_overrides": "InpFixture=1",
            }
        )
        errors_after_intermediate = registry_validator.validate_row_semantics(
            row, prior_rows=[prior_offline, intermediate]
        )
        self.assertTrue(
            any(
                "offline/preflight target requires a new hypothesis_id" in error
                for error in errors_after_intermediate
            )
        )
        reason_only = copy.deepcopy(prior_offline)
        reason_only.update(
            {
                "model": "research_design",
                "setup_type": "research candidate",
                "source_provenance": "local evidence",
                "exact_overrides": None,
                "lane": "generic_research",
                "feature_family": "generic",
                "reason": "Offline evidence only; an EA patch needs a new contract.",
            }
        )
        self.assertTrue(
            any(
                "offline/preflight target requires a new hypothesis_id" in error
                for error in registry_validator.validate_row_semantics(
                    row, prior_rows=[reason_only]
                )
            )
        )

    def test_challenger_requires_hash_bound_control_and_nonrepaint_evidence(self) -> None:
        row = copy.deepcopy(self.rows[-1])
        row["state"] = "challenger"
        errors = list(
            flatten_schema_errors(
                jsonschema.Draft202012Validator(self.schema).iter_errors(row)
            )
        )
        messages = "\n".join(error.message for error in errors)
        for required in (
            "readout_hash",
            "matched_control_evidence",
            "nonrepaint_audit",
            "preflight_evidence",
        ):
            with self.subTest(required=required):
                self.assertIn(required, messages)

    def test_portfolio_components_require_prior_confirmed_rows(self) -> None:
        row = copy.deepcopy(self.rows[-1])
        row["state"] = "portfolio-sleeve"
        row["portfolio_evidence"] = {"component_ids": [row["hypothesis_id"], "MISSING"]}
        errors = registry_validator.validate_row_semantics(row, prior_rows=[])
        self.assertTrue(any("previously confirmed component" in error for error in errors))

    def test_schema_invalid_inputs_fail_closed_without_crashing(self) -> None:
        self.assertEqual(
            registry_validator.validate_row_semantics([]),
            ["registry row must be a JSON object"],
        )
        errors = []
        registry_validator.validate_split(
            "train",
            {"controls": [{"control_id": []}]},
            "HYP-MALFORMED-FIXTURE",
            [],
            {},
            errors,
        )
        self.assertTrue(any("control_id must be a string" in error for error in errors))

    def test_full_promotion_fixture_binds_splits_arithmetic_controls_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            hypothesis_id = "HYP-SR-GENERIC-PROMOTION-TEST-001"
            run_ids = ["control-run", "challenger-run"]
            paths = {
                name: workspace / name
                for name in (
                    "source.mq5",
                    "compiled.ex5",
                    "readout.md",
                    "report.json",
                    "control_report.raw",
                    "challenger_report.raw",
                    "underlying_evidence.json",
                    "producer.py",
                )
            }
            paths["source.mq5"].write_text(
                "// closed-bar fixture source\n" + "double fixture_value = 1.0;\n" * 12,
                encoding="utf-8",
            )
            paths["compiled.ex5"].write_bytes(bytes(range(256)) * 2)
            paths["producer.py"].write_text(
                "#!/usr/bin/env python3\n"
                "# Hash-bound fixture producer.\n"
                + "def produce(payload):\n    return dict(payload)\n" * 8,
                encoding="utf-8",
            )
            paths["control_report.raw"].write_text(
                "<html><title>MT5 Strategy Tester Report</title><body>"
                + "control trade profit loss drawdown " * 24
                + "</body></html>",
                encoding="utf-8",
            )
            paths["challenger_report.raw"].write_text(
                "<html><title>MT5 Strategy Tester Report</title><body>"
                + "challenger trade profit loss drawdown " * 24
                + "</body></html>",
                encoding="utf-8",
            )
            paths["report.json"].write_text(
                json.dumps({"report": "split", "rows": list(range(80))}),
                encoding="utf-8",
            )
            paths["underlying_evidence.json"].write_text(
                "arbitrary text that is intentionally not strict JSON",
                encoding="utf-8",
            )

            def artifact_ref(path: Path) -> dict[str, str]:
                return {"path": path.name, "sha256": sha256(path)}

            def write_json(name: str, payload: dict) -> dict[str, str]:
                path = workspace / name
                path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                return artifact_ref(path)

            arbitrary_text_ref = artifact_ref(paths["underlying_evidence.json"])
            source_hash = sha256(paths["source.mq5"])
            compiled_hash = sha256(paths["compiled.ex5"])
            control_overrides = "fixture_feature=off"
            exact_overrides = "fixture_feature=on"

            producer_counter = 0

            def producer_payload(
                artifact_type: str,
                *,
                bound_run_ids: list[str] | None = None,
                output_result: dict | None = None,
                **extra,
            ) -> dict:
                nonlocal producer_counter
                producer_counter += 1
                receipt_run_ids = bound_run_ids or run_ids
                output_schema = f"fixture_{artifact_type}.v1"
                output_ref = write_json(
                    f"producer_output_{producer_counter}_{artifact_type}.json",
                    {
                        "schema_version": output_schema,
                        "artifact_type": artifact_type,
                        "status": "PASS",
                        "hypothesis_id": hypothesis_id,
                        "run_ids": receipt_run_ids,
                        "result": output_result
                        or {
                            "verified": True,
                            "records": 100,
                            "identity": artifact_type,
                        },
                    },
                )
                return {
                    "schema_version": registry_validator.PRODUCER_SCHEMA,
                    "artifact_type": artifact_type,
                    "status": "PASS",
                    "hypothesis_id": hypothesis_id,
                    "run_ids": receipt_run_ids,
                    "producer": artifact_ref(paths["producer.py"]),
                    "producer_exit_code": 0,
                    "output": output_ref,
                    "output_schema_version": output_schema,
                    **extra,
                }

            controls = [
                {
                    "control_id": control,
                    "cost_pf_x1_delta": 0.15,
                    "mean_net_r_per_trade_x1_delta": 0.05,
                    "passed": True,
                }
                for control in ("S555", "S618", "S670")
            ]

            def split(
                split_name: str,
                window: str,
                trades: int,
                days: int,
                positive: int,
                total: int,
            ):
                evidence = {
                    "window": window,
                    "report": artifact_ref(paths["report.json"]),
                    "trades": trades,
                    "elapsed_days": days,
                    "elapsed_calendar_weeks": days / 7,
                    "trades_per_elapsed_week": trades / (days / 7),
                    "cost_pf_x1": 1.31,
                    "cost_pf_x1_5": 1.25,
                    "cost_pf_x2": 1.0,
                    "net_r_x1_5": 10.0,
                    "mean_net_r_per_trade_x1": 0.1,
                    "positive_years": positive,
                    "total_years": total,
                    "max_component_share_x1_5": 0.55,
                    "min_component_share_x1_5": 0.2,
                    "controls": copy.deepcopy(controls),
                }
                producer_ref = write_json(
                    f"{split_name}_cost_producer.json",
                    producer_payload(
                        "cost_stress",
                        split=split_name,
                        window=window,
                        provenance_status="VERIFIED",
                    ),
                )
                cost_ref = write_json(
                    f"{split_name}_cost_attestation.json",
                    {
                        "schema_version": "registry_cost_attestation.v1",
                        "status": "VERIFIED",
                        "hypothesis_id": hypothesis_id,
                        "split": split_name,
                        "window": window,
                        "evidence": producer_ref,
                    },
                )
                metric_fields = {
                    key: value
                    for key, value in evidence.items()
                    if key
                    in {
                        "trades",
                        "elapsed_days",
                        "elapsed_calendar_weeks",
                        "trades_per_elapsed_week",
                        "cost_pf_x1",
                        "cost_pf_x1_5",
                        "cost_pf_x2",
                        "net_r_x1_5",
                        "mean_net_r_per_trade_x1",
                        "positive_years",
                        "total_years",
                        "max_component_share_x1_5",
                        "min_component_share_x1_5",
                    }
                }
                outcome_ref = write_json(
                    f"{split_name}_outcome_attestation.json",
                    {
                        "schema_version": "registry_split_outcome.v1",
                        "artifact_type": "split_outcome",
                        "status": "PASS",
                        "hypothesis_id": hypothesis_id,
                        "run_ids": run_ids,
                        "producer_evidence": write_json(
                            f"{split_name}_outcome_producer.json",
                            producer_payload("split_outcome"),
                        ),
                        "split": split_name,
                        "window": window,
                        "report": evidence["report"],
                        "metrics": metric_fields,
                        "controls": copy.deepcopy(controls),
                        "no_censor": {
                            "frozen_episodes": trades + 10,
                            "complete_after_join": trades + 10,
                            "missing": 0,
                            "outcome_rows": trades,
                        },
                    },
                )
                evidence["cost_manifest"] = cost_ref
                evidence["outcome_artifact"] = outcome_ref
                return evidence

            gate_names = (
                "validate_full",
                "walk_forward",
                "pbo_cscv",
                "reality_check_spa",
                "monte_carlo",
                "robustness_suite",
                "equity_audit",
                "cost_stress",
                "execution_audit",
                "nonrepaint_audit",
                "casebook",
            )
            gate_refs = {}
            for gate in gate_names:
                producer_ref = write_json(
                    f"{gate}_producer.json", producer_payload(gate)
                )
                gate_refs[gate] = write_json(
                    f"{gate}_attestation.json",
                    {
                        "schema_version": "registry_gate_attestation.v1",
                        "gate": gate,
                        "status": "PASS",
                        "hypothesis_id": hypothesis_id,
                        "run_ids": run_ids,
                        "evidence": producer_ref,
                    },
                )

            control_report = artifact_ref(paths["control_report.raw"])
            challenger_report = artifact_ref(paths["challenger_report.raw"])

            include_path = workspace / "SNR_Fixture.mqh"
            include_path.write_text(
                "// fixture include\n" + "double closed_bar_value = 2.0;\n" * 8,
                encoding="utf-8",
            )
            config_paths = {
                role: workspace / f"{role}_tester.ini"
                for role in ("control", "challenger")
            }
            for role, config_path in config_paths.items():
                overrides = control_overrides if role == "control" else exact_overrides
                config_path.write_text(
                    "[Tester]\n"
                    "Symbol=XAUUSD\n"
                    "Period=M15\n"
                    "Model=0\n"
                    "ExecutionMode=0\n"
                    "FromDate=2019.01.01\n"
                    "ToDate=2025.12.31\n"
                    "Deposit=100000\n"
                    "Leverage=100\n"
                    + "; bound tester configuration\n" * 4
                    + "[TesterInputs]\n"
                    + "\n".join(
                        f"{key}={value}||{value}||0||{value}||N"
                        for key, value in (
                            item.split("=", 1) for item in overrides.split(";") if item
                        )
                    )
                    + "\n",
                    encoding="utf-16" if role == "control" else "utf-8",
                )

            def run_manifest_payload(
                run_id: str,
                run_role: str,
                overrides: str,
                report: dict[str, str],
            ) -> dict:
                config_path = config_paths[run_role]
                return {
                    "schema_version": registry_validator.RUN_MANIFEST_SCHEMA,
                    "hypothesis_id": hypothesis_id,
                    "run_id": run_id,
                    "run_role": run_role,
                    "symbol": "XAUUSD",
                    "period": "M15",
                    "from": "2019.01.01",
                    "to": "2025.12.31",
                    "model": 0,
                    "execution_mode": 0,
                    "fixed_delay_ms": 0,
                    "deposit": 100000,
                    "leverage": 100,
                    "spread": "current",
                    "overrides": overrides,
                    "source_snapshot": paths["source.mq5"].name,
                    "source_sha256": source_hash,
                    "ex5_snapshot": paths["compiled.ex5"].name,
                    "ex5_sha256": compiled_hash,
                    "tester_ex5_path": paths["compiled.ex5"].name,
                    "tester_ex5_sha256": compiled_hash,
                    "config_snapshot": config_path.name,
                    "config_sha256": sha256(config_path),
                    "report_path": report["path"],
                    "report_sha256": report["sha256"],
                    "include_snapshots": [
                        {
                            "snapshot_path": include_path.name,
                            "sha256": sha256(include_path),
                        }
                    ],
                    "broker_fingerprint": "A" * 64,
                    "server_fingerprint": "B" * 64,
                    "account_fingerprint": "C" * 64,
                    "data_fingerprint": "D" * 64,
                    "generated_at_utc": "2026-07-11T00:00:00+00:00",
                }

            control_manifest_payload = run_manifest_payload(
                "control-run", "control", control_overrides, control_report
            )
            challenger_manifest_payload = run_manifest_payload(
                "challenger-run", "challenger", exact_overrides, challenger_report
            )
            control_manifest = write_json(
                "control_run_manifest.json", control_manifest_payload
            )
            challenger_manifest = write_json(
                "challenger_run_manifest.json", challenger_manifest_payload
            )
            matched_identity = {
                field: control_manifest_payload[field]
                for field in (
                    "symbol",
                    "period",
                    "from",
                    "to",
                    "model",
                    "execution_mode",
                    "fixed_delay_ms",
                    "deposit",
                    "leverage",
                    "spread",
                    "broker_fingerprint",
                    "server_fingerprint",
                    "account_fingerprint",
                    "data_fingerprint",
                )
            }
            matched_control_comparison = write_json(
                "matched_control_comparison.json",
                {
                    "schema_version": "registry_matched_control_comparison.v1",
                    "artifact_type": "matched_control_comparison",
                    "status": "PASS",
                    "hypothesis_id": hypothesis_id,
                    "run_ids": run_ids,
                    "control_run_id": "control-run",
                    "challenger_run_id": "challenger-run",
                    "control_manifest": control_manifest,
                    "challenger_manifest": challenger_manifest,
                    "matched_identity_sha256": registry_validator.canonical_json_sha256(
                        matched_identity
                    ),
                    "producer_evidence": write_json(
                        "matched_control_comparison_producer.json",
                        producer_payload(
                            "matched_control_comparison",
                            output_result={
                                "control_report": control_report,
                                "challenger_report": challenger_report,
                                "matched_identity_sha256": registry_validator.canonical_json_sha256(
                                    matched_identity
                                ),
                                "net_delta": 1.0,
                                "risk_adjusted_delta": 0.1,
                            },
                        ),
                    ),
                    "net_delta": 1.0,
                    "risk_adjusted_delta": 0.1,
                },
            )
            nonrepaint_ref = write_json(
                "nonrepaint_audit.json",
                {
                    "schema_version": registry_validator.NONREPAINT_SCHEMA,
                    "status": "PASS",
                    "hypothesis_id": hypothesis_id,
                    "run_id": "challenger-run",
                    "manifest": challenger_manifest["path"],
                    "manifest_sha256": challenger_manifest["sha256"],
                    "audited_files": [
                        {"path": paths["source.mq5"].name, "sha256": source_hash},
                        {"path": include_path.name, "sha256": sha256(include_path)},
                    ],
                    "findings": [],
                    "allowed_new_bar_gates": [],
                    "generated_at_utc": "2026-07-11T00:01:00+00:00",
                },
            )
            train_window = "2019-01-01T00:00:00Z/2023-01-01T00:00:00Z"
            holdout_window = "2023-01-01T00:00:00Z/2026-01-01T00:00:00Z"
            stability_window = "2019-01-01T00:00:00Z/2026-01-01T00:00:00Z"
            month_buckets = [
                {
                    "period": f"{year:04d}-{month:02d}",
                    "net_r": 10 / 48 if year < 2023 else 10 / 36,
                }
                for year in range(2019, 2026)
                for month in range(1, 13)
            ]
            half_year_buckets = [
                {
                    "period": f"{year:04d}-H{half}",
                    "net_r": sum(
                        bucket["net_r"]
                        for bucket in month_buckets[index * 6 : index * 6 + 6]
                    ),
                }
                for index, (year, half) in enumerate(
                    (year, half)
                    for year in range(2019, 2026)
                    for half in (1, 2)
                )
            ]
            year_buckets = [
                {
                    "period": f"{year:04d}",
                    "net_r": sum(
                        bucket["net_r"]
                        for bucket in month_buckets[index * 12 : index * 12 + 12]
                    ),
                }
                for index, year in enumerate(range(2019, 2026))
            ]
            stability_metrics = {
                "months": 84,
                "positive_months": 84,
                "positive_month_ratio": 1.0,
                "max_month_positive_profit_share": 1 / 72,
                "half_years": 14,
                "positive_half_years": 14,
                "positive_half_year_ratio": 1.0,
                "max_half_year_positive_profit_share": 1 / 12,
                "years": 7,
                "positive_years": 7,
                "positive_year_ratio": 1.0,
                "max_year_positive_profit_share": 1 / 6,
            }
            stability_payload = {
                "schema_version": "registry_stability_surface.v1",
                "artifact_type": "stability_surface",
                "status": "PASS",
                "hypothesis_id": hypothesis_id,
                "run_ids": run_ids,
                "producer_evidence": write_json(
                    "stability_surface_producer.json",
                    producer_payload("stability_surface"),
                ),
                "window": stability_window,
                "metrics": stability_metrics,
                "month_buckets": month_buckets,
                "half_year_buckets": half_year_buckets,
                "year_buckets": year_buckets,
            }
            stability_ref = write_json(
                "stability_surface.json",
                stability_payload,
            )

            preflight_ref = write_json(
                "preflight_clearance.json",
                {
                    "schema_version": registry_validator.PREFLIGHT_SCHEMA,
                    "artifact_type": "preflight_clearance",
                    "status": "PASS",
                    "hypothesis_id": hypothesis_id,
                    "run_ids": run_ids,
                    "target_contract": {
                        "evidence_mode": "ea_patch",
                        "cost_data_status": "VERIFIED",
                        "symbols": ["XAUUSD"],
                        "train_window": train_window,
                        "holdout_window": holdout_window,
                        "required_controls": ["S555", "S618", "S670"],
                    },
                    "producer_evidence": write_json(
                        "preflight_cost_producer.json",
                        producer_payload(
                            "cost_data_preflight",
                            output_result={
                                "cost_data_status": "VERIFIED",
                                "symbols": {
                                    "XAUUSD": {
                                        "status": "VERIFIED",
                                        "spread_coverage_ratio": 1.0,
                                        "commission_lifecycles": 30,
                                        "slippage_roundturn_samples": 100,
                                        "slippage_buy_samples": 30,
                                        "slippage_sell_samples": 30,
                                    }
                                },
                            },
                        ),
                    ),
                },
            )
            paths["readout.md"].write_text(
                "---\n"
                f"schema_version: {registry_validator.READOUT_SCHEMA}\n"
                f"hypothesis_id: {hypothesis_id}\n"
                "state: confirmed\n"
                f"run_ids: {json.dumps(run_ids)}\n"
                f"source_sha256: {source_hash}\n"
                f"compiled_sha256: {compiled_hash}\n"
                "control_run_id: control-run\n"
                "challenger_run_id: challenger-run\n"
                "---\n"
                "# Promotion Readout\n\n"
                "## Identity\n\nBound hypothesis and state.\n\n"
                "## Source Identity\n\nSource, EX5, config, and report hashes verified.\n\n"
                "## Runs\n\nMatched Model 0 control and challenger with identical execution identity.\n\n"
                "## Validation Artifacts\n\nFull validation, cost, robustness, and non-repaint evidence attached.\n\n"
                "## Verdict\n\nConfirmed only after independent train and holdout gates.\n",
                encoding="utf-8",
            )

            row = copy.deepcopy(self.rows[-1])
            row.update(
                {
                    "hypothesis_id": hypothesis_id,
                    "state": "confirmed",
                    "verdict": "confirm",
                    "model": 0,
                    "setup_type": "EA patch matched Model 0 promotion fixture",
                    "symbol": "XAUUSD",
                    "timeframe": "M15",
                    "window": stability_window,
                    "readout_path": paths["readout.md"].name,
                    "readout_hash": sha256(paths["readout.md"]),
                    "source_path": paths["source.mq5"].name,
                    "source_hash": source_hash,
                    "compiled_artifact_path": paths["compiled.ex5"].name,
                    "compiled_artifact_hash": compiled_hash,
                    "exact_overrides": exact_overrides,
                    "matched_control_run_id": "control-run",
                    "matched_control_evidence": {
                        "control_run_id": "control-run",
                        "challenger_run_id": "challenger-run",
                        "control_overrides": control_overrides,
                        "challenger_overrides": exact_overrides,
                        "control_manifest": control_manifest,
                        "challenger_manifest": challenger_manifest,
                        "control_report": control_report,
                        "challenger_report": challenger_report,
                        "comparison": matched_control_comparison,
                    },
                    "nonrepaint_audit": nonrepaint_ref,
                    "preflight_evidence": preflight_ref,
                    "run_ids": run_ids,
                    "promotion_evidence": {
                        "train": split(
                            "train",
                            train_window,
                            500,
                            1461,
                            4,
                            4,
                        ),
                        "holdout": split(
                            "holdout",
                            holdout_window,
                            350,
                            1096,
                            3,
                            3,
                        ),
                        "stability": {
                            "artifact": stability_ref,
                            "window": stability_window,
                            **stability_metrics,
                        },
                        "validation_artifacts": gate_refs,
                    },
                }
            )
            row["metrics"].update(
                {
                    "trades": 850,
                    "elapsed_days": 2557,
                    "elapsed_calendar_weeks": 2557 / 7,
                    "trades_per_elapsed_week": 850 / (2557 / 7),
                    "cost_pf_x1": 1.31,
                    "cost_pf_x1_5": 1.25,
                    "cost_pf_x2": 1.0,
                    "net_r_x1_5": 20.0,
                }
            )
            row["validation"].update(
                {
                    "validate_full": "PASS",
                    "wfa": "PASS",
                    "pbo_cscv": "PASS",
                    "reality_check_spa": "PASS",
                    "monte_carlo": "PASS",
                    "robustness_suite": "PASS",
                    "equity_audit": "PASS",
                    "cost_stress": "PASS",
                    "execution_audit": "PASS",
                    "sidecar_completeness": "PASS",
                    "casebook_status": "PASS",
                }
            )

            jsonschema.validate(row, self.schema)
            with mock.patch.object(registry_validator, "WORKSPACE", workspace):
                self.assertEqual(registry_validator.validate_row_semantics(row), [])

                blocked_preflight = copy.deepcopy(row)
                blocked_preflight_payload = json.loads(
                    (workspace / preflight_ref["path"]).read_text(encoding="utf-8")
                )
                blocked_receipt = json.loads(
                    (
                        workspace
                        / blocked_preflight_payload["producer_evidence"]["path"]
                    ).read_text(encoding="utf-8")
                )
                blocked_output = json.loads(
                    (workspace / blocked_receipt["output"]["path"]).read_text(
                        encoding="utf-8"
                    )
                )
                blocked_output["result"]["symbols"]["XAUUSD"][
                    "spread_coverage_ratio"
                ] = 0.04
                blocked_receipt["output"] = write_json(
                    "blocked_preflight_output.json", blocked_output
                )
                blocked_preflight_payload["producer_evidence"] = write_json(
                    "blocked_preflight_receipt.json", blocked_receipt
                )
                blocked_preflight["preflight_evidence"] = write_json(
                    "blocked_preflight.json", blocked_preflight_payload
                )
                self.assertTrue(
                    any(
                        "spread_coverage_ratio >= 0.95" in error
                        for error in registry_validator.validate_row_semantics(
                            blocked_preflight
                        )
                    )
                )

                split_total_mismatch = copy.deepcopy(row)
                split_total_mismatch["promotion_evidence"]["train"]["net_r_x1_5"] = 11.0
                self.assertTrue(
                    any(
                        "monthly net_r does not reconcile to train/holdout split totals"
                        in error
                        for error in registry_validator.validate_row_semantics(
                            split_total_mismatch
                        )
                    )
                )

                inconsistent = copy.deepcopy(row)
                inconsistent["promotion_evidence"]["train"]["elapsed_calendar_weeks"] = 1
                self.assertTrue(
                    any(
                        "elapsed_calendar_weeks" in error
                        for error in registry_validator.validate_row_semantics(inconsistent)
                    )
                )

                bad_hash = copy.deepcopy(row)
                bad_hash["promotion_evidence"]["holdout"]["report"]["sha256"] = "0" * 64
                self.assertTrue(
                    any(
                        "SHA256 mismatch" in error
                        for error in registry_validator.validate_row_semantics(bad_hash)
                    )
                )

                bad_readout_hash = copy.deepcopy(row)
                bad_readout_hash["readout_hash"] = "0" * 64
                self.assertTrue(
                    any(
                        "readout" in error and "SHA256 mismatch" in error
                        for error in registry_validator.validate_row_semantics(
                            bad_readout_hash
                        )
                    )
                )

                unrelated_readout = workspace / "unrelated_readout.md"
                unrelated_readout.write_text(
                    "This is unrelated prose with no machine identity.",
                    encoding="utf-8",
                )
                unrelated_readout_row = copy.deepcopy(row)
                unrelated_readout_row["readout_path"] = unrelated_readout.name
                unrelated_readout_row["readout_hash"] = sha256(unrelated_readout)
                self.assertTrue(
                    any(
                        "readout machine identity" in error
                        for error in registry_validator.validate_row_semantics(
                            unrelated_readout_row
                        )
                    )
                )

                wrong_identity_readout = workspace / "wrong_identity_readout.md"
                wrong_identity_readout.write_text(
                    paths["readout.md"]
                    .read_text(encoding="utf-8")
                    .replace(hypothesis_id, "HYP-WRONG-READOUT-IDENTITY", 1),
                    encoding="utf-8",
                )
                wrong_identity_row = copy.deepcopy(row)
                wrong_identity_row["readout_path"] = wrong_identity_readout.name
                wrong_identity_row["readout_hash"] = sha256(wrong_identity_readout)
                self.assertTrue(
                    any(
                        "machine identity hypothesis_id" in error
                        for error in registry_validator.validate_row_semantics(
                            wrong_identity_row
                        )
                    )
                )

                commented_heading_readout = workspace / "commented_heading_readout.md"
                commented_body = paths["readout.md"].read_text(encoding="utf-8")
                for section in (
                    "## Identity",
                    "## Source Identity",
                    "## Runs",
                    "## Validation Artifacts",
                    "## Verdict",
                ):
                    commented_body = commented_body.replace(
                        section, f"<!-- {section} -->"
                    )
                commented_heading_readout.write_text(commented_body, encoding="utf-8")
                commented_heading_row = copy.deepcopy(row)
                commented_heading_row["readout_path"] = commented_heading_readout.name
                commented_heading_row["readout_hash"] = sha256(
                    commented_heading_readout
                )
                self.assertTrue(
                    any(
                        "required section is missing" in error
                        for error in registry_validator.validate_row_semantics(
                            commented_heading_row
                        )
                    )
                )

                arbitrary_text_gate = copy.deepcopy(row)
                arbitrary_text_gate["promotion_evidence"]["validation_artifacts"][
                    "walk_forward"
                ] = write_json(
                    "walk_forward_text_attestation.json",
                    {
                        "schema_version": "registry_gate_attestation.v1",
                        "gate": "walk_forward",
                        "status": "PASS",
                        "hypothesis_id": hypothesis_id,
                        "run_ids": run_ids,
                        "evidence": arbitrary_text_ref,
                    },
                )
                self.assertTrue(
                    any(
                        "not strict JSON" in error
                        for error in registry_validator.validate_row_semantics(
                            arbitrary_text_gate
                        )
                    )
                )

                bad_producer_ref = write_json(
                    "bad_gate_producer.json",
                    {
                        **producer_payload("walk_forward"),
                        "status": "FAIL",
                        "hypothesis_id": "WRONG-HYPOTHESIS",
                        "run_ids": ["wrong-run"],
                        "producer_exit_code": False,
                    },
                )
                bad_producer_gate = copy.deepcopy(row)
                bad_producer_gate["promotion_evidence"]["validation_artifacts"][
                    "walk_forward"
                ] = write_json(
                    "walk_forward_bad_producer_attestation.json",
                    {
                        "schema_version": "registry_gate_attestation.v1",
                        "gate": "walk_forward",
                        "status": "PASS",
                        "hypothesis_id": hypothesis_id,
                        "run_ids": run_ids,
                        "evidence": bad_producer_ref,
                    },
                )
                bad_producer_errors = registry_validator.validate_row_semantics(
                    bad_producer_gate
                )
                for field in (
                    "status",
                    "hypothesis_id",
                    "run_ids",
                    "producer_exit_code",
                ):
                    with self.subTest(bad_producer_field=field):
                        self.assertTrue(
                            any(field in error for error in bad_producer_errors)
                        )

                bad_nonrepaint = copy.deepcopy(row)
                bad_nonrepaint["nonrepaint_audit"] = write_json(
                    "bad_nonrepaint_audit.json",
                    {
                        "schema_version": "registry_nonrepaint_audit.v1",
                        "artifact_type": "nonrepaint_audit",
                        "status": "PASS",
                        "hypothesis_id": hypothesis_id,
                        "run_ids": run_ids,
                        "producer": "candidate-registry-test-producer",
                        "producer_exit_code": 0,
                        "source_sha256": source_hash,
                        "bar_zero_violations": 1,
                        "lookahead_violations": 0,
                    },
                )
                self.assertTrue(
                    any(
                        "schema_version must equal" in error
                        and registry_validator.NONREPAINT_SCHEMA in error
                        for error in registry_validator.validate_row_semantics(
                            bad_nonrepaint
                        )
                    )
                )

                valid_nonrepaint_payload = json.loads(
                    (workspace / nonrepaint_ref["path"]).read_text(encoding="utf-8")
                )
                self.assertNotIn("producer", valid_nonrepaint_payload)

                bad_control = copy.deepcopy(row)
                bad_control["matched_control_evidence"]["control_run_id"] = "wrong-run"
                self.assertTrue(
                    any(
                        "control_run_id must equal matched_control_run_id" in error
                        for error in registry_validator.validate_row_semantics(bad_control)
                    )
                )

                for manifest_field, invalid_value in (
                    ("model", 1),
                    ("source_sha256", "0" * 64),
                    ("ex5_sha256", "0" * 64),
                    ("overrides", "wrong-overrides"),
                    ("run_id", "wrong-run"),
                    ("tester_ex5_sha256", "0" * 64),
                ):
                    with self.subTest(challenger_manifest_field=manifest_field):
                        bad_manifest_payload = copy.deepcopy(
                            challenger_manifest_payload
                        )
                        bad_manifest_payload[manifest_field] = invalid_value
                        bad_manifest = copy.deepcopy(row)
                        bad_manifest["matched_control_evidence"][
                            "challenger_manifest"
                        ] = write_json(
                            f"challenger_manifest_bad_{manifest_field}.json",
                            bad_manifest_payload,
                        )
                        self.assertTrue(
                            any(
                                f"challenger_manifest: {manifest_field}" in error
                                for error in registry_validator.validate_row_semantics(
                                    bad_manifest
                                )
                            )
                        )

                copied_report_path = workspace / "copied_challenger_report.raw"
                copied_report_path.write_bytes(paths["control_report.raw"].read_bytes())
                copied_report = artifact_ref(copied_report_path)
                copied_report_manifest_payload = copy.deepcopy(
                    challenger_manifest_payload
                )
                copied_report_manifest_payload["report_path"] = copied_report["path"]
                copied_report_manifest_payload["report_sha256"] = copied_report["sha256"]
                copied_report_row = copy.deepcopy(row)
                copied_report_row["matched_control_evidence"].update(
                    {
                        "challenger_report": copied_report,
                        "challenger_manifest": write_json(
                            "challenger_manifest_copied_report.json",
                            copied_report_manifest_payload,
                        ),
                    }
                )
                self.assertTrue(
                    any(
                        "reports must have distinct content hashes" in error
                        for error in registry_validator.validate_row_semantics(
                            copied_report_row
                        )
                    )
                )

                unmatched_control_manifest_payload = copy.deepcopy(
                    control_manifest_payload
                )
                unmatched_control_manifest_payload.update(
                    {
                        "symbol": "EURUSD",
                        "period": "H1",
                        "from": "2019.01.01",
                        "to": "2020.12.31",
                        "deposit": 10000,
                        "broker_fingerprint": "A" * 64,
                    }
                )
                unmatched_challenger_manifest_payload = copy.deepcopy(
                    challenger_manifest_payload
                )
                unmatched_challenger_manifest_payload.update(
                    {
                        "symbol": "XAUUSD",
                        "period": "M5",
                        "from": "2024.01.01",
                        "to": "2025.12.31",
                        "deposit": 100000,
                        "broker_fingerprint": "B" * 64,
                    }
                )
                unmatched_control_manifest = write_json(
                    "control_manifest_unmatched_context.json",
                    unmatched_control_manifest_payload,
                )
                unmatched_challenger_manifest = write_json(
                    "challenger_manifest_unmatched_context.json",
                    unmatched_challenger_manifest_payload,
                )
                unmatched_comparison_payload = {
                    **json.loads(
                        (
                            workspace
                            / matched_control_comparison["path"]
                        ).read_text(encoding="utf-8")
                    ),
                    "control_manifest": unmatched_control_manifest,
                    "challenger_manifest": unmatched_challenger_manifest,
                }
                unmatched_row = copy.deepcopy(row)
                unmatched_row["matched_control_evidence"].update(
                    {
                        "control_manifest": unmatched_control_manifest,
                        "challenger_manifest": unmatched_challenger_manifest,
                        "comparison": write_json(
                            "matched_control_unmatched_context.json",
                            unmatched_comparison_payload,
                        ),
                    }
                )
                self.assertTrue(
                    any(
                        "matched run identity differs" in error
                        for error in registry_validator.validate_row_semantics(
                            unmatched_row
                        )
                    )
                )

                bad_stability_ratio = copy.deepcopy(row)
                bad_stability_ratio["promotion_evidence"]["stability"][
                    "positive_month_ratio"
                ] = 0.5
                self.assertTrue(
                    any(
                        "positive_month_ratio does not match recomputed bucket surface"
                        in error
                        for error in registry_validator.validate_row_semantics(
                            bad_stability_ratio
                        )
                    )
                )

                duplicate_period_payload = copy.deepcopy(stability_payload)
                duplicate_period_payload["month_buckets"][1]["period"] = (
                    duplicate_period_payload["month_buckets"][0]["period"]
                )
                duplicate_period = copy.deepcopy(row)
                duplicate_period["promotion_evidence"]["stability"][
                    "artifact"
                ] = write_json(
                    "stability_duplicate_period.json", duplicate_period_payload
                )
                self.assertTrue(
                    any(
                        "no gaps, duplicates, or reordering" in error
                        for error in registry_validator.validate_row_semantics(
                            duplicate_period
                        )
                    )
                )

                short_surface_payload = copy.deepcopy(stability_payload)
                short_surface_payload["month_buckets"].pop()
                short_surface = copy.deepcopy(row)
                short_surface["promotion_evidence"]["stability"][
                    "artifact"
                ] = write_json("stability_short_surface.json", short_surface_payload)
                self.assertTrue(
                    any(
                        "must contain exactly 84 buckets" in error
                        for error in registry_validator.validate_row_semantics(
                            short_surface
                        )
                    )
                )

                aggregate_mismatch_payload = copy.deepcopy(stability_payload)
                aggregate_mismatch_payload["half_year_buckets"][0]["net_r"] = 5.0
                aggregate_mismatch = copy.deepcopy(row)
                aggregate_mismatch["promotion_evidence"]["stability"][
                    "artifact"
                ] = write_json(
                    "stability_aggregate_mismatch.json", aggregate_mismatch_payload
                )
                self.assertTrue(
                    any(
                        "does not equal the underlying month buckets" in error
                        for error in registry_validator.validate_row_semantics(
                            aggregate_mismatch
                        )
                    )
                )

                self_attested_count_payload = copy.deepcopy(stability_payload)
                self_attested_count_payload["metrics"]["positive_months"] = 83
                self_attested_count_payload["metrics"]["positive_month_ratio"] = 83 / 84
                self_attested_count = copy.deepcopy(row)
                self_attested_count["promotion_evidence"]["stability"].update(
                    {
                        "positive_months": 83,
                        "positive_month_ratio": 83 / 84,
                        "artifact": write_json(
                            "stability_self_attested_count.json",
                            self_attested_count_payload,
                        ),
                    }
                )
                self.assertTrue(
                    any(
                        "positive_months does not match recomputed bucket surface"
                        in error
                        for error in registry_validator.validate_row_semantics(
                            self_attested_count
                        )
                    )
                )

                near_zero_months = [
                    {
                        "period": bucket["period"],
                        "net_r": 1e-13 if index % 6 < 3 else -1.5e-13,
                    }
                    for index, bucket in enumerate(month_buckets)
                ]
                near_zero_metrics = {
                    "months": 84,
                    "positive_months": 42,
                    "positive_month_ratio": 0.5,
                    "max_month_positive_profit_share": 1 / 42,
                    "half_years": 14,
                    "positive_half_years": 14,
                    "positive_half_year_ratio": 1.0,
                    "max_half_year_positive_profit_share": 1 / 14,
                    "years": 7,
                    "positive_years": 7,
                    "positive_year_ratio": 1.0,
                    "max_year_positive_profit_share": 1 / 7,
                }
                near_zero_payload = copy.deepcopy(stability_payload)
                near_zero_payload.update(
                    {
                        "metrics": near_zero_metrics,
                        "month_buckets": near_zero_months,
                        "half_year_buckets": [
                            {"period": bucket["period"], "net_r": 1.5e-13}
                            for bucket in half_year_buckets
                        ],
                        "year_buckets": [
                            {"period": bucket["period"], "net_r": 3e-13}
                            for bucket in year_buckets
                        ],
                    }
                )
                near_zero_sign_flip = copy.deepcopy(row)
                near_zero_sign_flip["promotion_evidence"]["stability"].update(
                    {
                        **near_zero_metrics,
                        "artifact": write_json(
                            "stability_near_zero_sign_flip.json", near_zero_payload
                        ),
                    }
                )
                jsonschema.validate(near_zero_sign_flip, self.schema)
                near_zero_errors = registry_validator.validate_row_semantics(
                    near_zero_sign_flip
                )
                self.assertTrue(
                    any(
                        "does not equal the underlying month buckets" in error
                        for error in near_zero_errors
                    )
                )
                self.assertTrue(
                    any(
                        "positive_half_years does not match recomputed bucket surface"
                        in error
                        for error in near_zero_errors
                    )
                )

                giant_integer_payload = copy.deepcopy(stability_payload)
                giant_integer_payload["month_buckets"][0]["net_r"] = 10**4000
                giant_integer_row = copy.deepcopy(row)
                giant_integer_row["promotion_evidence"]["stability"][
                    "artifact"
                ] = write_json(
                    "stability_giant_integer.json", giant_integer_payload
                )
                self.assertTrue(
                    any(
                        "net_r must be a finite number" in error
                        for error in registry_validator.validate_row_semantics(
                            giant_integer_row
                        )
                    )
                )

                overflowing_sum_payload = copy.deepcopy(stability_payload)
                for bucket in overflowing_sum_payload["month_buckets"][:6]:
                    bucket["net_r"] = 1e308
                overflowing_sum_row = copy.deepcopy(row)
                overflowing_sum_row["promotion_evidence"]["stability"][
                    "artifact"
                ] = write_json(
                    "stability_overflowing_sum.json", overflowing_sum_payload
                )
                self.assertTrue(
                    any(
                        "numeric overflow while summing bucket net_r" in error
                        for error in registry_validator.validate_row_semantics(
                            overflowing_sum_row
                        )
                    )
                )

                missing_stability = copy.deepcopy(row)
                del missing_stability["promotion_evidence"]["stability"]
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(missing_stability, self.schema)

                for total_field, invalid_total in (
                    ("months", 83),
                    ("half_years", 13),
                    ("years", 6),
                ):
                    with self.subTest(stability_total=total_field):
                        bad_total = copy.deepcopy(row)
                        bad_total["promotion_evidence"]["stability"][
                            total_field
                        ] = invalid_total
                        with self.assertRaises(jsonschema.ValidationError):
                            jsonschema.validate(bad_total, self.schema)

                for count_field, invalid_count in (
                    ("positive_months", 41),
                    ("positive_half_years", 8),
                    ("positive_years", 3),
                ):
                    with self.subTest(stability_count=count_field):
                        bad_count = copy.deepcopy(row)
                        bad_count["promotion_evidence"]["stability"][
                            count_field
                        ] = invalid_count
                        with self.assertRaises(jsonschema.ValidationError):
                            jsonschema.validate(bad_count, self.schema)

                for concentration_field, invalid_share in (
                    ("max_month_positive_profit_share", 0.21),
                    ("max_half_year_positive_profit_share", 0.36),
                    ("max_year_positive_profit_share", 0.41),
                ):
                    with self.subTest(stability_concentration=concentration_field):
                        concentrated_stability = copy.deepcopy(row)
                        concentrated_stability["promotion_evidence"]["stability"][
                            concentration_field
                        ] = invalid_share
                        with self.assertRaises(jsonschema.ValidationError):
                            jsonschema.validate(concentrated_stability, self.schema)

                portfolio = copy.deepcopy(row)
                portfolio["state"] = "portfolio-sleeve"
                portfolio["verdict"] = "portfolio-candidate"
                component_ids = [hypothesis_id, "HYP-SR-SECOND-CONFIRMED-TEST-001"]
                component_run_ids = sorted(
                    [
                        *run_ids,
                        "component2-control",
                        "component2-challenger",
                    ]
                )
                component_runs = {
                    hypothesis_id: sorted(run_ids),
                    "HYP-SR-SECOND-CONFIRMED-TEST-001": [
                        "component2-challenger",
                        "component2-control",
                    ],
                }
                portfolio_readout = workspace / "portfolio_readout.md"
                portfolio_readout.write_text(
                    paths["readout.md"]
                    .read_text(encoding="utf-8")
                    .replace("state: confirmed", "state: portfolio-sleeve"),
                    encoding="utf-8",
                )
                portfolio["readout_path"] = portfolio_readout.name
                portfolio["readout_hash"] = sha256(portfolio_readout)
                portfolio_metrics = {
                    "correlation_exposure": {
                        "max_pairwise_abs_correlation": 0.25
                    },
                    "overlap_audit": {"max_overlap_share": 0.20},
                    "portfolio_drawdown": {
                        "portfolio_p95_dd_pct": 8.0,
                        "risk_budget_dd_pct": 10.0,
                    },
                    "combined_cost_stress": {
                        "combined_cost_pf_x1_5": 1.30,
                        "combined_cost_pf_x2": 1.05,
                    },
                }
                portfolio_refs = {
                    artifact_type: write_json(
                        f"portfolio_{artifact_type}.json",
                        {
                            "schema_version": "registry_portfolio_evidence.v1",
                            "artifact_type": artifact_type,
                            "status": "PASS",
                            "hypothesis_id": hypothesis_id,
                            "run_ids": component_run_ids,
                            "component_ids": component_ids,
                            "component_run_ids": component_run_ids,
                            "component_runs": component_runs,
                            "metrics": portfolio_metrics[artifact_type],
                            "producer_evidence": write_json(
                                f"portfolio_{artifact_type}_producer.json",
                                producer_payload(
                                    artifact_type,
                                    bound_run_ids=component_run_ids,
                                ),
                            ),
                        },
                    )
                    for artifact_type in (
                        "correlation_exposure",
                        "overlap_audit",
                        "portfolio_drawdown",
                        "combined_cost_stress",
                    )
                }
                portfolio["portfolio_evidence"] = {
                    "component_ids": component_ids,
                    "component_run_ids": component_run_ids,
                    "component_runs": component_runs,
                    **portfolio_refs,
                    "max_pairwise_abs_correlation": 0.25,
                    "max_overlap_share": 0.20,
                    "portfolio_p95_dd_pct": 8.0,
                    "risk_budget_dd_pct": 10.0,
                    "combined_cost_pf_x1_5": 1.30,
                    "combined_cost_pf_x2": 1.05,
                }
                prior_rows = [
                    {
                        "record_type": "candidate",
                        "hypothesis_id": component_id,
                        "state": "confirmed",
                        "run_ids": (
                            run_ids
                            if component_id == hypothesis_id
                            else ["component2-control", "component2-challenger"]
                        ),
                    }
                    for component_id in component_ids
                ]
                jsonschema.validate(portfolio, self.schema)
                self.assertEqual(
                    registry_validator.validate_row_semantics(portfolio, prior_rows), []
                )
                missing_component_runs = copy.deepcopy(portfolio)
                missing_component_runs["portfolio_evidence"].pop("component_run_ids")
                self.assertTrue(
                    any(
                        "component_run_ids must equal the union" in error
                        for error in registry_validator.validate_row_semantics(
                            missing_component_runs, prior_rows
                        )
                    )
                )
                wrong_component_mapping = copy.deepcopy(portfolio)
                wrong_component_mapping["portfolio_evidence"]["component_runs"] = {
                    hypothesis_id: sorted(run_ids),
                    "HYP-SR-SECOND-CONFIRMED-TEST-001": sorted(run_ids),
                }
                self.assertTrue(
                    any(
                        "component_runs must resolve every confirmed component" in error
                        for error in registry_validator.validate_row_semantics(
                            wrong_component_mapping, prior_rows
                        )
                    )
                )

                wrong_portfolio_metric = copy.deepcopy(portfolio)
                wrong_correlation_payload = json.loads(
                    (
                        workspace
                        / portfolio_refs["correlation_exposure"]["path"]
                    ).read_text(encoding="utf-8")
                )
                wrong_correlation_payload["metrics"][
                    "max_pairwise_abs_correlation"
                ] = 0.99
                wrong_portfolio_metric["portfolio_evidence"][
                    "correlation_exposure"
                ] = write_json(
                    "portfolio_correlation_wrong_metric.json",
                    wrong_correlation_payload,
                )
                self.assertTrue(
                    any(
                        "metric max_pairwise_abs_correlation does not match registry"
                        in error
                        for error in registry_validator.validate_row_semantics(
                            wrong_portfolio_metric, prior_rows
                        )
                    )
                )

                wrong_portfolio_runs = copy.deepcopy(portfolio)
                wrong_overlap_payload = json.loads(
                    (
                        workspace
                        / portfolio_refs["overlap_audit"]["path"]
                    ).read_text(encoding="utf-8")
                )
                wrong_overlap_payload["run_ids"] = ["wrong-run"]
                wrong_portfolio_runs["portfolio_evidence"]["overlap_audit"] = write_json(
                    "portfolio_overlap_wrong_runs.json",
                    wrong_overlap_payload,
                )
                self.assertTrue(
                    any(
                        "run_ids must equal" in error
                        for error in registry_validator.validate_row_semantics(
                            wrong_portfolio_runs, prior_rows
                        )
                    )
                )

                unresolved_portfolio = copy.deepcopy(portfolio)
                self.assertTrue(
                    any(
                        "previously confirmed component" in error
                        for error in registry_validator.validate_row_semantics(
                            unresolved_portfolio, prior_rows[:1]
                        )
                    )
                )

                failed_gate = copy.deepcopy(row)
                failed_gate["validation"]["wfa"] = "FAIL"
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.validate(failed_gate, self.schema)


if __name__ == "__main__":
    unittest.main()
