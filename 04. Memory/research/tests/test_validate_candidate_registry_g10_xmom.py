from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_candidate_registry.py"
SPEC = importlib.util.spec_from_file_location("candidate_registry_validator_g10", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def test_g10_export_completion_can_open_one_use_train_evaluation(monkeypatch, tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"{}\n")
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: artifact)
    monkeypatch.setattr(SUT, "normalized_workspace_path", lambda *_args: tmp_path / "absent")

    prior_validation = {
        "train_export_authorized": True,
        "train_acquisition_authorized": True,
        "train_price_data_acquisition_authorized": True,
        "train_source_run_authorized": True,
        "mt5_authorized": True,
        "train_economics_authorized": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "holdout_access_authorized": False,
        "promotion_authorized": False,
        "one_use": True,
    }
    prior = {
        "hypothesis_id": SUT.G10_XMOM_HYP002_ID,
        "state": "probe",
        "verdict": "EXPORT_AUTHORIZED",
        "reason": "before export",
        "updated_at_utc": "2026-01-01T00:00:00Z",
        "run_ids": [],
        "metrics": {},
        "validation": prior_validation,
    }
    successor = copy.deepcopy(prior)
    successor.update(
        verdict="FROZEN_ONE_SHOT_TRAIN_EVALUATION_AUTHORIZED",
        reason="export passed",
        updated_at_utc="2026-01-01T00:01:00Z",
        run_ids=[SUT.G10_XMOM_EXPORT_ATTEMPT_ID],
        metrics={
            "train_source_attempts_consumed": 1,
            "mt5_launches": 1,
            "w1_bars_read": 1456,
            "prices_read": 1456,
            "returns_computed": 0,
            "ranks_computed": 0,
            "signals_generated": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "outcomes_opened": 0,
            "performance_trials_executed": 0,
            "economics_executed": False,
            "research_holdout_opened": False,
        },
    )
    successor["validation"].update(
        train_export_authorized=False,
        train_acquisition_authorized=False,
        train_price_data_acquisition_authorized=False,
        train_source_run_authorized=False,
        mt5_authorized=False,
        train_evaluate_authorized=True,
        train_economics_authorized=True,
        performance_metrics_authorized=True,
        economics_authorized=True,
        dataset_manifest_path="02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002/train_w1_manifest.json",
        dataset_manifest_sha256="A" * 64,
        dataset_parquet_path="02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002/train_w1_bars.parquet",
        dataset_parquet_sha256="B" * 64,
        dataset_row_count=1456,
        train_export_receipt_path="03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EXPORT-001/train_export_receipt.json",
        train_export_receipt_sha256="C" * 64,
        train_eval_attempt_id="G10XMOM002-TRAIN-EVAL-001",
        train_eval_evidence_root="03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EVAL-001",
    )

    assert SUT._g10_xmom_export_to_eval_transition_errors(prior, 2, successor) == []


def test_historical_g10_eval_authority_allows_terminal_evidence_but_latest_does_not(
    monkeypatch, tmp_path
):
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"{}\n")
    eval_root = tmp_path / "eval"
    eval_root.mkdir()
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: artifact)
    monkeypatch.setattr(SUT, "normalized_workspace_path", lambda *_args: eval_root)

    prior_validation = {
        "train_export_authorized": True,
        "train_acquisition_authorized": True,
        "train_price_data_acquisition_authorized": True,
        "train_source_run_authorized": True,
        "mt5_authorized": True,
        "train_economics_authorized": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "holdout_access_authorized": False,
        "promotion_authorized": False,
        "one_use": True,
    }
    prior = {
        "hypothesis_id": SUT.G10_XMOM_HYP002_ID,
        "state": "probe",
        "verdict": "EXPORT_AUTHORIZED",
        "reason": "before export",
        "updated_at_utc": "2026-01-01T00:00:00Z",
        "run_ids": [],
        "metrics": {},
        "validation": prior_validation,
    }
    successor = copy.deepcopy(prior)
    successor.update(
        verdict="FROZEN_ONE_SHOT_TRAIN_EVALUATION_AUTHORIZED",
        reason="export passed",
        updated_at_utc="2026-01-01T00:01:00Z",
        run_ids=[SUT.G10_XMOM_EXPORT_ATTEMPT_ID],
        metrics={
            "train_source_attempts_consumed": 1,
            "mt5_launches": 1,
            "w1_bars_read": 1456,
            "prices_read": 1456,
            "returns_computed": 0,
            "ranks_computed": 0,
            "signals_generated": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "outcomes_opened": 0,
            "performance_trials_executed": 0,
            "economics_executed": False,
            "research_holdout_opened": False,
        },
    )
    successor["validation"].update(
        train_export_authorized=False,
        train_acquisition_authorized=False,
        train_price_data_acquisition_authorized=False,
        train_source_run_authorized=False,
        mt5_authorized=False,
        train_evaluate_authorized=True,
        train_economics_authorized=True,
        performance_metrics_authorized=True,
        economics_authorized=True,
        dataset_manifest_path="02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002/train_w1_manifest.json",
        dataset_manifest_sha256="A" * 64,
        dataset_parquet_path="02. AlphaFactory/data/fivepercent/G10WeeklyXSMomentum/HYP-G10-XMOM-W1-002/train_w1_bars.parquet",
        dataset_parquet_sha256="B" * 64,
        dataset_row_count=1456,
        train_export_receipt_path="03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence/HYP-G10-XMOM-W1-002/G10XMOM002-TRAIN-EXPORT-001/train_export_receipt.json",
        train_export_receipt_sha256="C" * 64,
        train_eval_attempt_id="G10XMOM002-TRAIN-EVAL-001",
        train_eval_evidence_root="eval",
    )

    historical_errors = SUT._g10_xmom_export_to_eval_transition_errors(
        prior, 2, successor
    )
    latest_errors: list[str] = []
    SUT._validate_g10_xmom_eval_root_absent(successor, 2, latest_errors)

    assert historical_errors == []
    assert latest_errors == [
        "line 2 HYP-G10-XMOM-W1-002 latest evaluation authority: "
        "train evaluation evidence root must be absent"
    ]
