from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_candidate_registry.py"
SPEC = importlib.util.spec_from_file_location("candidate_registry_validator_model4", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def _row(*, model: int, validation: dict | None = None) -> dict:
    return {
        "hypothesis_id": "HYP-MODEL4-COLLECTION-TEST",
        "ea_name": "EA_Model4CollectionTest",
        "state": "screened",
        "model": model,
        "source_path": "03. EA Developer/EA_Model4CollectionTest/EA_Model4CollectionTest.mq5",
        "source_hash": "A" * 64,
        "prereg_path": "03. EA Developer/EA_Model4CollectionTest/research/PROBE_PLAN.json",
        "prereg_sha256": "B" * 64,
        "updated_at_utc": "2026-07-31T00:00:00Z",
        "window": {"from": "1970.01.01", "to": "2026.07.30"},
        "validation": validation or {},
    }


def _validate(monkeypatch, row: dict, tmp_path: Path) -> list[str]:
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"{}\n")
    monkeypatch.setattr(SUT, "verify_source_binding", lambda *_args: artifact)
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: artifact)
    errors: list[str] = []
    SUT.validate_row_bindings(row, 1, errors)
    return errors


def _model4_validation(**overrides) -> dict:
    payload = {
        "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "model4_data_acquisition_authorized": True,
        "model4_performance_authorized": False,
        "promotion_eligible": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
    }
    payload.update(overrides)
    return payload


def test_model4_screened_requires_exact_data_acquisition_authority(monkeypatch, tmp_path):
    errors = _validate(monkeypatch, _row(model=4), tmp_path)

    assert any("validation.authority" in error for error in errors)


def test_model4_screened_accepts_exact_no_performance_gates(monkeypatch, tmp_path):
    errors = _validate(monkeypatch, _row(model=4, validation=_model4_validation()), tmp_path)

    assert errors == []


def test_model0_screened_remains_valid_without_new_authority(monkeypatch, tmp_path):
    errors = _validate(
        monkeypatch,
        _row(
            model=0,
            validation={"authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"},
        ),
        tmp_path,
    )

    assert errors == []


def test_model4_authority_rejects_wrong_model_or_performance_permissions(
    monkeypatch, tmp_path
):
    model0_errors = _validate(
        monkeypatch,
        _row(model=0, validation=_model4_validation()),
        tmp_path,
    )
    old_authority_errors = _validate(
        monkeypatch,
        _row(
            model=4,
            validation=_model4_validation(authority="DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"),
        ),
        tmp_path,
    )
    performance_errors = _validate(
        monkeypatch,
        _row(model=4, validation=_model4_validation(performance_metrics_authorized=True)),
        tmp_path,
    )
    sidecar_permission_errors = _validate(
        monkeypatch,
        _row(model=4, validation=_model4_validation(model4_performance_authorized=True)),
        tmp_path,
    )

    assert any("requires Model 4" in error for error in model0_errors)
    assert any("validation.authority" in error for error in old_authority_errors)
    assert any("performance_metrics_authorized=False" in error for error in performance_errors)
    assert any("model4_performance_authorized=False" in error for error in sidecar_permission_errors)


def test_terminal_source_snapshot_amendment_is_one_field_pair_only(
    monkeypatch, tmp_path
):
    artifact = tmp_path / "source_snapshot.mq5"
    artifact.write_text("// frozen\n", encoding="utf-8")
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: artifact)
    prior = _row(model=4, validation=_model4_validation())
    prior["state"] = "parked"
    prior["reason"] = "terminal"
    prior["run_ids"] = ["RUN-1"]
    row = copy.deepcopy(prior)
    row["updated_at_utc"] = "2026-07-31T00:01:00Z"
    row["reason"] = "Bind the immutable terminal source snapshot."
    row["validation"]["source_snapshot_path"] = (
        "03. EA Developer/EA_Model4CollectionTest/research/source_snapshots/"
        "EA_Model4CollectionTest_HYP-MODEL4-COLLECTION-TEST.mq5"
    )
    row["validation"]["source_snapshot_sha256"] = "A" * 64

    assert SUT._terminal_snapshot_amendment_errors(prior, 2, row) == []

    row["run_ids"] = ["RUN-1", "RUN-2"]
    errors = SUT._terminal_snapshot_amendment_errors(prior, 2, row)
    assert any("prohibited top-level change 'run_ids'" in error for error in errors)


def test_screened_prelaunch_evidence_correction_is_zero_exposure_only(
    monkeypatch, tmp_path
):
    hypothesis_id = "HYP-MODEL4-COLLECTION-TEST"
    correction = tmp_path / "correction.json"
    correction.write_text(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "classification": "PRELAUNCH_EVIDENCE_METADATA_CORRECTION",
                "original_receipt": {
                    "path": "original.json",
                    "sha256": "D" * 64,
                },
                "exposure_readback": {
                    "hyp005_execution_receipts": 0,
                    "economic_trials_consumed": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: correction)
    monkeypatch.setattr(SUT, "WORKSPACE", tmp_path)
    prior = _row(model=4, validation=_model4_validation())
    prior["run_ids"] = []
    prior["metrics"] = {
        "mt5_launches": 0,
        "economic_trials_consumed": 0,
        "trades_executed": 0,
        "economics_executed": False,
    }
    prior["validation"]["engineering_receipt_path"] = "original.json"
    prior["validation"]["engineering_receipt_sha256"] = "D" * 64
    row = copy.deepcopy(prior)
    row["updated_at_utc"] = "2026-07-31T00:01:00Z"
    row["reason"] = "Append-only prelaunch evidence metadata correction."
    row["validation"]["engineering_receipt_correction_path"] = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/correction.json"
    )
    row["validation"]["engineering_receipt_correction_sha256"] = "C" * 64

    assert SUT._prelaunch_evidence_correction_errors(prior, 2, row) == []

    row["metrics"]["mt5_launches"] = 1
    errors = SUT._prelaunch_evidence_correction_errors(prior, 2, row)
    assert any("zero prelaunch exposure" in error for error in errors)


def test_screened_prelaunch_packet_authorization_is_hash_bound_and_zero_exposure(
    monkeypatch, tmp_path
):
    hypothesis_id = "HYP-MODEL4-COLLECTION-TEST"
    campaign = tmp_path / "04. Memory/research/CAMPAIGN_EXPOSURE.jsonl"
    campaign.parent.mkdir(parents=True)
    campaign_row = {
        "event": "DATA_REPAIR",
        "active_hypothesis_id": None,
        "data_repair": {
            "replacement_prereg": {
                "hypothesis_id": hypothesis_id,
                "sha256": "B" * 64,
            },
                "economic_trials_consumed": 0,
                "data_acquisition_authorized": True,
                "performance_metrics_authorized": False,
                "economics_authorized": False,
        },
    }
    campaign_body = json.dumps(campaign_row, separators=(",", ":")).encode("utf-8")
    campaign.write_bytes(campaign_body + b"\n")
    campaign_sha = hashlib.sha256(campaign_body).hexdigest().upper()
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "classification": "PRELAUNCH_PACKET_AUTHORITY",
                "campaign_data_repair_row_sha256": campaign_sha,
                "test_run": {"result": "PASS", "passed": 121, "failed": 0},
                "exposure_readback": {
                    "hyp005_execution_receipts": 0,
                    "hyp005_run_manifests": 0,
                    "trades_executed": 0,
                    "economic_trials_consumed": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: receipt)
    monkeypatch.setattr(SUT, "WORKSPACE", tmp_path)
    validation = _model4_validation(
        probe_status="SCREENED_PRELAUNCH_CAMPAIGN_BINDING_PENDING",
        campaign_prebinding_status="PENDING_DATA_REPAIR",
        task_packet_authorized_next=False,
        required_journal_marker_case_sensitive=False,
        packet_builder_wrapper_sha256="1" * 64,
        packet_builder_core_sha256="2" * 64,
        ledger_appender_core_sha256="3" * 64,
        packet_rebind_core_sha256="4" * 64,
        journal_parser_sha256="5" * 64,
        data_epoch_validator_sha256="6" * 64,
        runner_engine_sha256="7" * 64,
        bound_tests=[{"path": "old", "sha256": "8" * 64}],
        mt5_authorized=False,
        model4_authorized=False,
        trading_backtest_authorized=False,
        trades_authorized=False,
        optimization_authorized=False,
        validation_access_authorized=False,
        holdout_access_authorized=False,
        market_edge_claim_authorized=False,
        task_packets_created=False,
    )
    prior = _row(model=4, validation=validation)
    prior["run_ids"] = []
    prior["metrics"] = {
        "mt5_launches": 0,
        "economic_trials_consumed": 0,
        "trades_executed": 0,
        "economics_executed": False,
    }
    row = copy.deepcopy(prior)
    row["updated_at_utc"] = "2026-07-31T00:02:00Z"
    row["reason"] = "Append-only prelaunch packet authorization."
    row["verdict"] = "SCREENED_PRELAUNCH_PACKET_AUTHORIZED"
    changed_hashes = {
        "packet_builder_wrapper_sha256": "A" * 64,
        "packet_builder_core_sha256": "C" * 64,
        "ledger_appender_core_sha256": "D" * 64,
        "packet_rebind_core_sha256": "E" * 64,
        "journal_parser_sha256": "F" * 64,
        "data_epoch_validator_sha256": "0" * 64,
        "runner_engine_sha256": "9" * 64,
    }
    row["validation"].update(changed_hashes)
    row["validation"].update(
        {
            "probe_status": "SCREENED_PRELAUNCH_PACKET_AUTHORIZED",
            "campaign_prebinding_status": "BOUND_DATA_REPAIR",
            "task_packet_authorized_next": True,
            "required_journal_marker_case_sensitive": True,
            "bound_tests": [{"path": "new", "sha256": "A" * 64}],
            "campaign_data_repair_row_sha256": campaign_sha,
            "prepacket_control_plane_receipt_path": (
                "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
                f"{hypothesis_id}/receipt.json"
            ),
            "prepacket_control_plane_receipt_sha256": "A" * 64,
        }
    )

    assert SUT._prelaunch_packet_authorization_errors(prior, 3, row) == []

    authorized = copy.deepcopy(row)
    row["validation"]["mt5_authorized"] = True
    errors = SUT._prelaunch_packet_authorization_errors(prior, 3, row)
    assert any("unsafe authority flag 'mt5_authorized'" in error for error in errors)

    corrected_tests = [
        {"path": "new", "sha256": "A" * 64},
        {"path": "missing_scope_test", "sha256": "B" * 64},
    ]
    correction = tmp_path / "scope_correction.json"
    correction_payload = {
        "hypothesis_id": hypothesis_id,
        "classification": "PRELAUNCH_PACKET_SCOPE_CORRECTION",
        "original_receipt": {
            "path": authorized["validation"][
                "prepacket_control_plane_receipt_path"
            ],
            "sha256": authorized["validation"][
                "prepacket_control_plane_receipt_sha256"
            ],
        },
        "added_test_path": "missing_scope_test",
        "bound_tests": corrected_tests,
        "exact_rerun": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 121,
            "failed": 0,
            "declared_test_file_count": 2,
        },
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
        "control_plane_corrections": [
            {"path": "validator", "sha256": "C" * 64}
        ],
    }
    correction.write_text(
        json.dumps(correction_payload),
        encoding="utf-8",
    )
    corrected = copy.deepcopy(authorized)
    corrected["updated_at_utc"] = "2026-07-31T00:03:00Z"
    corrected["reason"] = "Append-only prelaunch packet scope correction."
    corrected["validation"]["bound_tests"] = corrected_tests
    corrected["validation"][
        "prepacket_control_plane_receipt_correction_path"
    ] = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/scope_correction.json"
    )
    corrected["validation"][
        "prepacket_control_plane_receipt_correction_sha256"
    ] = "D" * 64
    correction_path = corrected["validation"][
        "prepacket_control_plane_receipt_correction_path"
    ]

    artifact_map = {
        authorized["validation"]["prepacket_control_plane_receipt_path"]: receipt,
        correction_path: correction,
    }

    def verify_test_binding(path, *_args):
        return artifact_map.get(path, correction)

    monkeypatch.setattr(SUT, "verify_binding", verify_test_binding)

    assert (
        SUT._prelaunch_packet_scope_correction_errors(authorized, 4, corrected)
        == []
    )

    tampered = copy.deepcopy(correction_payload)
    tampered["exact_rerun"]["passed"] = 1
    correction.write_text(json.dumps(tampered), encoding="utf-8")
    errors = SUT._prelaunch_packet_scope_correction_errors(
        authorized, 4, corrected
    )
    assert any("identity/scope/test/exposure mismatch" in error for error in errors)

    tampered = copy.deepcopy(correction_payload)
    tampered["exact_rerun"]["declared_test_file_count"] = 1
    correction.write_text(json.dumps(tampered), encoding="utf-8")
    errors = SUT._prelaunch_packet_scope_correction_errors(
        authorized, 4, corrected
    )
    assert any("identity/scope/test/exposure mismatch" in error for error in errors)
    correction.write_text(json.dumps(correction_payload), encoding="utf-8")

    hardened_tests = copy.deepcopy(corrected_tests)
    hardened_tests[-1]["sha256"] = "E" * 64
    hardening = tmp_path / "scope_validator_hardening.json"
    hardening_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/scope_validator_hardening.json"
    )
    hardening_payload = {
        "hypothesis_id": hypothesis_id,
        "classification": "PRELAUNCH_SCOPE_VALIDATOR_HARDENING",
        "prior_scope_correction": {
            "path": correction_path,
            "sha256": corrected["validation"][
                "prepacket_control_plane_receipt_correction_sha256"
            ],
        },
        "bound_tests": hardened_tests,
        "exact_rerun": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 121,
            "failed": 0,
            "declared_test_file_count": 2,
        },
        "adversarial_guards": {
            "wrong_pass_count_rejected": True,
            "wrong_declared_file_count_rejected": True,
        },
        "control_plane": [{"path": "validator", "sha256": "F" * 64}],
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
    }
    hardening.write_text(json.dumps(hardening_payload), encoding="utf-8")
    artifact_map[hardening_path] = hardening
    hardened = copy.deepcopy(corrected)
    hardened["updated_at_utc"] = "2026-07-31T00:04:00Z"
    hardened["reason"] = "Append-only prelaunch scope validator hardening."
    hardened["validation"]["bound_tests"] = hardened_tests
    hardened["validation"][
        "prepacket_scope_validator_hardening_receipt_path"
    ] = hardening_path
    hardened["validation"][
        "prepacket_scope_validator_hardening_receipt_sha256"
    ] = "F" * 64

    assert (
        SUT._prelaunch_scope_validator_hardening_errors(corrected, 5, hardened)
        == []
    )

    packet_symbols = [
        "XAUUSD",
        "BTCUSD",
        "EURUSD",
        "USDJPY",
        "GBPUSD",
        "USDCHF",
        "USDCAD",
        "AUDUSD",
        "NZDUSD",
    ]
    hardened["validation"]["mandatory_symbols"] = packet_symbols
    packet_set = [
        {
            "symbol": symbol,
            "path": (
                "03. EA Developer/EA_Model4CollectionTest/research/preflight/"
                f"{hypothesis_id}/task_packet.{symbol}.control.json"
            ),
            "sha256": f"{index + 1:X}" * 64,
        }
        for index, symbol in enumerate(packet_symbols)
    ]
    authority_receipt = tmp_path / "xau_authority.json"
    authority_receipt_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/xau_authority.json"
    )
    xau_packet_path = packet_set[0]["path"]
    authority_receipt_payload = {
        "hypothesis_id": hypothesis_id,
        "classification": "PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORITY",
        "prior_registry": {
            "line": 5,
            "row_sha256": "1" * 64,
            "full_registry_sha256": "2" * 64,
        },
        "authorized_git_status": {
            "packet_sha256": "6" * 64,
            "current_sha256": "7" * 64,
        },
        "campaign_data_repair_row_sha256": campaign_sha,
        "packet_set": packet_set,
        "xau_dry_run": {
            "symbol": "XAUUSD",
            "exit_code": 0,
            "execution_allowed": True,
            "execution_blockers": [],
            "execute": False,
            "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
            "task_packet_path": xau_packet_path,
            "task_packet_sha256": packet_set[0]["sha256"],
        },
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 121,
            "failed": 0,
            "declared_test_file_count": 2,
        },
        "control_plane": [{"path": "validator", "sha256": "F" * 64}],
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
    }
    authority_receipt.write_text(
        json.dumps(authority_receipt_payload),
        encoding="utf-8",
    )
    artifact_map[authority_receipt_path] = authority_receipt
    launch_authorized = copy.deepcopy(hardened)
    launch_authorized["updated_at_utc"] = "2026-07-31T00:05:00Z"
    launch_authorized["reason"] = (
        "Append-only prelaunch XAU Model4 collection authorization."
    )
    launch_authorized["verdict"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORIZED"
    )
    launch_authorized["validation"]["probe_status"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_AUTHORIZED"
    )
    launch_authorized["validation"]["runner_engine_sha256"] = "3" * 64
    launch_authorized["validation"]["bound_tests"] = copy.deepcopy(hardened_tests)
    launch_authorized["validation"]["bound_tests"][-1]["sha256"] = "4" * 64
    launch_authorized["validation"]["task_packets_created"] = True
    launch_authorized["validation"]["task_packet_authorized_next"] = False
    launch_authorized["validation"].update(
        {
            "packet_set_dry_run_receipt_path": authority_receipt_path,
            "packet_set_dry_run_receipt_sha256": "5" * 64,
            "authorized_packet_registry_sha256": "2" * 64,
            "authorized_packet_registry_row_sha256": "1" * 64,
            "authorized_packet_git_status_sha256": "6" * 64,
            "authorized_current_git_status_sha256": "7" * 64,
            "xau_task_packet_path": xau_packet_path,
            "xau_task_packet_sha256": packet_set[0]["sha256"],
            "xau_model4_collection_launch_authorized": True,
            "mt5_data_collection_authorized": True,
            "model4_data_collection_authorized": True,
            "authorized_symbol": "XAUUSD",
            "authorized_symbol_order_index": 0,
            "authorized_launch_limit": 1,
            "authorized_launches_consumed": 0,
        }
    )

    assert (
        SUT._prelaunch_xau_model4_collection_authorization_errors(
            5,
            "1" * 64,
            "2" * 64,
            hardened,
            6,
            launch_authorized,
        )
        == []
    )

    unsafe = copy.deepcopy(launch_authorized)
    unsafe["validation"]["trades_authorized"] = True
    errors = SUT._prelaunch_xau_model4_collection_authorization_errors(
        5,
        "1" * 64,
        "2" * 64,
        hardened,
        6,
        unsafe,
    )
    assert any("must remain false" in error for error in errors)
    errors = SUT._prelaunch_xau_model4_collection_authorization_errors(
        5,
        "A" * 64,
        "2" * 64,
        hardened,
        6,
        launch_authorized,
    )
    assert any("identity/scope/test/exposure mismatch" in error for error in errors)

    dependency_paths = [
        "02. AlphaFactory/alpha.ps1",
        "02. AlphaFactory/alpha.local.ps1",
        "02. AlphaFactory/tools/mt5_storage_contract.ps1",
        "02. AlphaFactory/tools/ea_contract.ps1",
        "02. AlphaFactory/tools/log_storage.ps1",
        "02. AlphaFactory/tools/audit_mql5_nonrepaint.py",
    ]
    dependency_bindings = [
        {"path": path, "sha256": f"{index + 10:X}"[-1] * 64}
        for index, path in enumerate(dependency_paths)
    ]
    execute_receipt = tmp_path / "execute_gate_hardening.json"
    execute_receipt_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT.json"
    )
    launch_claim_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
    )
    execute_receipt_payload = {
        "schema_version": (
            "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v1"
        ),
        "hypothesis_id": hypothesis_id,
        "classification": "PRELAUNCH_XAU_MODEL4_EXECUTE_GATE_HARDENING",
        "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        "prior_registry": {
            "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
            "line": 6,
            "row_sha256": "A" * 64,
            "sha256": "B" * 64,
        },
        "prior_authority_receipt": {
            "path": authority_receipt_path,
            "sha256": "5" * 64,
        },
        "authorized_git_status": {"current_sha256": "C" * 64},
        "control_plane": {
            "runner": {
                "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                "sha256": "D" * 64,
            },
            "candidate_registry_validator": {
                "path": "04. Memory/research/validate_candidate_registry.py",
                "sha256": "E" * 64,
            },
            "alpha_entrypoint": {
                "path": "02. AlphaFactory/alpha.ps1",
                "sha256": dependency_bindings[0]["sha256"],
            },
            "execution_dependency_bindings": dependency_bindings,
        },
        "launch_claim_path": launch_claim_path,
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 122,
            "failed": 0,
            "declared_test_file_count": 2,
            "symbol": "XAUUSD",
            "model": 4,
            "run_role": "control",
            "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        },
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "launch_claims": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
        "verdict": "PASS_ONE_SHOT_XAU_EXECUTE_GATE",
    }
    execute_receipt.write_text(
        json.dumps(execute_receipt_payload),
        encoding="utf-8",
    )
    artifact_map[execute_receipt_path] = execute_receipt
    execute_authorized = copy.deepcopy(launch_authorized)
    execute_authorized["updated_at_utc"] = "2026-07-31T00:06:00Z"
    execute_authorized["reason"] = (
        "Append-only prelaunch XAU Model4 execute-gate hardening."
    )
    execute_authorized["verdict"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED"
    )
    execute_authorized["validation"]["probe_status"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_EXECUTE_AUTHORIZED"
    )
    execute_authorized["validation"]["runner_engine_sha256"] = "D" * 64
    execute_authorized["validation"]["bound_tests"] = copy.deepcopy(hardened_tests)
    execute_authorized["validation"]["bound_tests"][-1]["sha256"] = "9" * 64
    execute_authorized["validation"]["authorized_current_git_status_sha256"] = (
        "C" * 64
    )
    execute_authorized["validation"].update(
        {
            "candidate_registry_validator_sha256": "E" * 64,
            "alpha_entrypoint_sha256": dependency_bindings[0]["sha256"],
            "execution_dependency_bindings": dependency_bindings,
            "execute_gate_hardening_receipt_path": execute_receipt_path,
            "execute_gate_hardening_receipt_sha256": "F" * 64,
            "execute_gate_prior_registry_line": 6,
            "execute_gate_prior_registry_sha256": "B" * 64,
            "execute_gate_prior_registry_row_sha256": "A" * 64,
            "launch_claim_path": launch_claim_path,
        }
    )
    assert (
        SUT._prelaunch_xau_model4_execute_gate_hardening_errors(
            6,
            "A" * 64,
            "B" * 64,
            launch_authorized,
            7,
            execute_authorized,
        )
        == []
    )

    drifted_dependency = copy.deepcopy(execute_authorized)
    drifted_dependency["validation"]["execution_dependency_bindings"][0][
        "sha256"
    ] = "0" * 64
    errors = SUT._prelaunch_xau_model4_execute_gate_hardening_errors(
        6,
        "A" * 64,
        "B" * 64,
        launch_authorized,
        7,
        drifted_dependency,
    )
    assert any("alpha_entrypoint_sha256 must match" in error for error in errors)

    postlock_receipt = tmp_path / "execute_gate_hardening_v2.json"
    postlock_receipt_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V2.json"
    )
    postlock_tests = copy.deepcopy(execute_authorized["validation"]["bound_tests"])
    postlock_tests[0]["sha256"] = "6" * 64
    postlock_tests[1]["sha256"] = "7" * 64
    postlock_receipt_payload = {
        "schema_version": (
            "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v2"
        ),
        "hypothesis_id": hypothesis_id,
        "classification": (
            "PRELAUNCH_XAU_MODEL4_POSTLOCK_EXECUTE_GATE_HARDENING"
        ),
        "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        "verdict": "PASS_ONE_SHOT_XAU_POSTLOCK_EXECUTE_GATE",
        "prior_registry": {
            "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
            "line": 7,
            "sha256": "2" * 64,
            "row_sha256": "1" * 64,
        },
        "prior_authority_receipt": {
            "path": authority_receipt_path,
            "sha256": "5" * 64,
        },
        "authorized_git_status": {"current_sha256": "5" * 64},
        "control_plane": {
            "runner": {
                "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                "sha256": "3" * 64,
            },
            "candidate_registry_validator": {
                "path": "04. Memory/research/validate_candidate_registry.py",
                "sha256": "4" * 64,
            },
            "alpha_entrypoint": {
                "path": "02. AlphaFactory/alpha.ps1",
                "sha256": dependency_bindings[0]["sha256"],
            },
            "execution_dependency_bindings": dependency_bindings,
        },
        "launch_claim_path": launch_claim_path,
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 10,
            "failed": 0,
            "declared_test_selector_count": 4,
            "purpose": "POSTLOCK_GATE_TARGETED",
            "symbol": "XAUUSD",
            "model": 4,
            "run_role": "control",
            "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        },
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "launch_claims": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
    }
    postlock_receipt.write_text(
        json.dumps(postlock_receipt_payload),
        encoding="utf-8",
    )
    artifact_map[postlock_receipt_path] = postlock_receipt
    postlock_authorized = copy.deepcopy(execute_authorized)
    postlock_authorized["updated_at_utc"] = "2026-07-31T00:07:00Z"
    postlock_authorized["reason"] = (
        "Append-only post-lock execute-gate revalidation."
    )
    postlock_authorized["verdict"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
    )
    postlock_authorized["validation"]["probe_status"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_POSTLOCK_AUTHORIZED"
    )
    postlock_authorized["validation"]["runner_engine_sha256"] = "3" * 64
    postlock_authorized["validation"][
        "candidate_registry_validator_sha256"
    ] = "4" * 64
    postlock_authorized["validation"]["bound_tests"] = postlock_tests
    postlock_authorized["validation"][
        "authorized_current_git_status_sha256"
    ] = "5" * 64
    postlock_authorized["validation"][
        "execute_gate_hardening_receipt_path"
    ] = postlock_receipt_path
    postlock_authorized["validation"][
        "execute_gate_hardening_receipt_sha256"
    ] = "8" * 64
    postlock_authorized["validation"]["execute_gate_prior_registry_line"] = 7
    postlock_authorized["validation"][
        "execute_gate_prior_registry_sha256"
    ] = "2" * 64
    postlock_authorized["validation"][
        "execute_gate_prior_registry_row_sha256"
    ] = "1" * 64
    assert (
        SUT._prelaunch_xau_model4_postlock_revalidation_errors(
            7,
            "1" * 64,
            "2" * 64,
            execute_authorized,
            8,
            postlock_authorized,
        )
        == []
    )

    full_suite_receipt = tmp_path / "execute_gate_hardening_v3.json"
    full_suite_receipt_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V3.json"
    )
    full_suite_receipt_payload = {
        "schema_version": (
            "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v3"
        ),
        "hypothesis_id": hypothesis_id,
        "classification": (
            "PRELAUNCH_XAU_MODEL4_FULL_SUITE_EXECUTE_AUTHORIZATION"
        ),
        "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        "verdict": "PASS_ONE_SHOT_XAU_FULL_SUITE_EXECUTE_GATE",
        "prior_registry": {
            "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
            "line": 8,
            "sha256": "A" * 64,
            "row_sha256": "9" * 64,
        },
        "prior_authority_receipt": {
            "path": authority_receipt_path,
            "sha256": "5" * 64,
        },
        "authorized_git_status": {"current_sha256": "5" * 64},
        "control_plane": {
            "runner": {
                "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                "sha256": "3" * 64,
            },
            "candidate_registry_validator": {
                "path": "04. Memory/research/validate_candidate_registry.py",
                "sha256": "4" * 64,
            },
            "alpha_entrypoint": {
                "path": "02. AlphaFactory/alpha.ps1",
                "sha256": dependency_bindings[0]["sha256"],
            },
            "execution_dependency_bindings": dependency_bindings,
        },
        "launch_claim_path": launch_claim_path,
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 122,
            "failed": 0,
            "declared_test_file_count": 10,
            "symbol": "XAUUSD",
            "model": 4,
            "run_role": "control",
            "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        },
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "launch_claims": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
    }
    full_suite_receipt.write_text(
        json.dumps(full_suite_receipt_payload),
        encoding="utf-8",
    )
    artifact_map[full_suite_receipt_path] = full_suite_receipt
    full_suite_authorized = copy.deepcopy(postlock_authorized)
    full_suite_authorized["updated_at_utc"] = "2026-07-31T00:08:00Z"
    full_suite_authorized["reason"] = (
        "Append-only full-suite execute authorization."
    )
    full_suite_authorized["verdict"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
    )
    full_suite_authorized["validation"]["probe_status"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_FULL_SUITE_AUTHORIZED"
    )
    full_suite_authorized["validation"][
        "execute_gate_hardening_receipt_path"
    ] = full_suite_receipt_path
    full_suite_authorized["validation"][
        "execute_gate_hardening_receipt_sha256"
    ] = "B" * 64
    full_suite_authorized["validation"]["execute_gate_prior_registry_line"] = 8
    full_suite_authorized["validation"][
        "execute_gate_prior_registry_sha256"
    ] = "A" * 64
    full_suite_authorized["validation"][
        "execute_gate_prior_registry_row_sha256"
    ] = "9" * 64
    assert (
        SUT._prelaunch_xau_model4_full_suite_authorization_errors(
            8,
            "9" * 64,
            "A" * 64,
            postlock_authorized,
            9,
            full_suite_authorized,
        )
        == []
    )

    bridge_receipt = tmp_path / "execute_gate_hardening_v4.json"
    bridge_receipt_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V4.json"
    )
    bridge_tests = copy.deepcopy(full_suite_authorized["validation"]["bound_tests"])
    bridge_tests[0]["sha256"] = "C" * 64
    bridge_receipt_payload = {
        "schema_version": "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v4",
        "hypothesis_id": hypothesis_id,
        "classification": "PRELAUNCH_XAU_MODEL4_REGISTRY_LOCK_TOCTOU_TARGETED_HARDENING",
        "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        "verdict": "PASS_XAU_REGISTRY_LOCK_TOCTOU_TARGETED_GATE",
        "execution_authorized": False,
        "full_suite_attested": False,
        "prior_registry": {
            "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
            "line": 9,
            "sha256": "D" * 64,
            "row_sha256": "C" * 64,
        },
        "prior_execute_gate_receipt": {
            "path": full_suite_receipt_path,
            "sha256": "B" * 64,
        },
        "prior_authority_receipt": {
            "path": authority_receipt_path,
            "sha256": "5" * 64,
        },
        "authorized_git_status": {"current_sha256": "6" * 64},
        "control_plane": {
            "runner": {
                "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                "sha256": "C" * 64,
            },
            "candidate_registry_validator": {
                "path": "04. Memory/research/validate_candidate_registry.py",
                "sha256": "D" * 64,
            },
            "alpha_entrypoint": {
                "path": "02. AlphaFactory/alpha.ps1",
                "sha256": dependency_bindings[0]["sha256"],
            },
            "execution_dependency_bindings": dependency_bindings,
        },
        "bound_tests": bridge_tests,
        "launch_claim_path": launch_claim_path,
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 9,
            "failed": 0,
            "declared_test_selector_count": 3,
            "purpose": "REGISTRY_LOCK_TOCTOU_TARGETED",
            "symbol": "XAUUSD",
            "model": 4,
            "run_role": "control",
            "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        },
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "launch_claims": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
    }
    bridge_receipt.write_text(json.dumps(bridge_receipt_payload), encoding="utf-8")
    artifact_map[bridge_receipt_path] = bridge_receipt
    bridge = copy.deepcopy(full_suite_authorized)
    bridge["updated_at_utc"] = "2026-07-31T00:09:00Z"
    bridge["reason"] = (
        "Append-only registry-lock TOCTOU targeted hardening bridge."
    )
    bridge["verdict"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
    )
    bridge["validation"]["probe_status"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_TARGETED_VERIFIED"
    )
    bridge["validation"]["runner_engine_sha256"] = "C" * 64
    bridge["validation"]["candidate_registry_validator_sha256"] = "D" * 64
    bridge["validation"]["bound_tests"] = bridge_tests
    bridge["validation"]["authorized_current_git_status_sha256"] = "6" * 64
    bridge["validation"]["execute_gate_hardening_receipt_path"] = bridge_receipt_path
    bridge["validation"]["execute_gate_hardening_receipt_sha256"] = "E" * 64
    bridge["validation"]["execute_gate_prior_registry_line"] = 9
    bridge["validation"]["execute_gate_prior_registry_sha256"] = "D" * 64
    bridge["validation"]["execute_gate_prior_registry_row_sha256"] = "C" * 64
    assert (
        SUT._prelaunch_xau_model4_targeted_bridge_errors(
            9,
            "C" * 64,
            "D" * 64,
            full_suite_authorized,
            10,
            bridge,
        )
        == []
    )
    unsafe_bridge_receipt = copy.deepcopy(bridge_receipt_payload)
    unsafe_bridge_receipt["execution_authorized"] = True
    bridge_receipt.write_text(json.dumps(unsafe_bridge_receipt), encoding="utf-8")
    errors = SUT._prelaunch_xau_model4_targeted_bridge_errors(
        9,
        "C" * 64,
        "D" * 64,
        full_suite_authorized,
        10,
        bridge,
    )
    assert any("receipt identity/control-plane/test/exposure mismatch" in error for error in errors)
    bridge_receipt.write_text(json.dumps(bridge_receipt_payload), encoding="utf-8")

    final_receipt = tmp_path / "execute_gate_hardening_v5.json"
    final_receipt_path = (
        "03. EA Developer/EA_Model4CollectionTest/research/evidence/"
        f"{hypothesis_id}/HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V5.json"
    )
    final_receipt_payload = {
        "schema_version": "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v5",
        "hypothesis_id": hypothesis_id,
        "classification": "PRELAUNCH_XAU_MODEL4_REGISTRY_LOCK_FULL_SUITE_EXECUTE_AUTHORIZATION",
        "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        "verdict": "PASS_ONE_SHOT_XAU_REGISTRY_LOCK_FULL_SUITE_EXECUTE_GATE",
        "execution_authorized": True,
        "full_suite_attested": True,
        "prior_registry": {
            "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
            "line": 10,
            "sha256": "F" * 64,
            "row_sha256": "E" * 64,
        },
        "prior_bridge_receipt": {
            "path": bridge_receipt_path,
            "sha256": "E" * 64,
        },
        "prior_authority_receipt": {
            "path": authority_receipt_path,
            "sha256": "5" * 64,
        },
        "authorized_git_status": {"current_sha256": "6" * 64},
        "control_plane": bridge_receipt_payload["control_plane"],
        "bound_tests": bridge_tests,
        "launch_claim_path": launch_claim_path,
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 124,
            "failed": 0,
            "declared_test_file_count": 10,
            "symbol": "XAUUSD",
            "model": 4,
            "run_role": "control",
            "authority": SUT.MODEL4_DATA_ACQUISITION_AUTHORITY,
        },
        "exposure_readback": bridge_receipt_payload["exposure_readback"],
    }
    final_receipt.write_text(json.dumps(final_receipt_payload), encoding="utf-8")
    artifact_map[final_receipt_path] = final_receipt
    final_authorized = copy.deepcopy(bridge)
    final_authorized["updated_at_utc"] = "2026-07-31T00:10:00Z"
    final_authorized["reason"] = (
        "Append-only registry-lock full-suite execute authorization."
    )
    final_authorized["verdict"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED"
    )
    final_authorized["validation"]["probe_status"] = (
        "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED"
    )
    final_authorized["validation"]["execute_gate_hardening_receipt_path"] = final_receipt_path
    final_authorized["validation"]["execute_gate_hardening_receipt_sha256"] = "A" * 64
    final_authorized["validation"]["execute_gate_prior_registry_line"] = 10
    final_authorized["validation"]["execute_gate_prior_registry_sha256"] = "F" * 64
    final_authorized["validation"]["execute_gate_prior_registry_row_sha256"] = "E" * 64
    assert (
        SUT._prelaunch_xau_model4_registry_lock_full_suite_authorization_errors(
            10,
            "E" * 64,
            "F" * 64,
            bridge,
            11,
            final_authorized,
        )
        == []
    )
    wrong_count_receipt = copy.deepcopy(final_receipt_payload)
    wrong_count_receipt["exact_test_run"]["passed"] = 123
    final_receipt.write_text(json.dumps(wrong_count_receipt), encoding="utf-8")
    errors = SUT._prelaunch_xau_model4_registry_lock_full_suite_authorization_errors(
        10,
        "E" * 64,
        "F" * 64,
        bridge,
        11,
        final_authorized,
    )
    assert any("receipt identity/control-plane/test/exposure mismatch" in error for error in errors)
    final_receipt.write_text(json.dumps(final_receipt_payload), encoding="utf-8")

    claim_file = tmp_path / launch_claim_path
    claim_file.parent.mkdir(parents=True, exist_ok=True)
    claim_file.write_text("{}", encoding="utf-8")
    latest_errors: list[str] = []
    SUT._validate_latest_hyp005_execute_authority(
        11,
        final_authorized,
        latest_errors,
    )
    assert any("durable launch claim already exists" in error for error in latest_errors)

    corrected["run_ids"] = ["ILLEGAL-RUN"]
    errors = SUT._prelaunch_packet_scope_correction_errors(
        authorized, 4, corrected
    )
    assert any("run_ids must remain empty" in error for error in errors)
