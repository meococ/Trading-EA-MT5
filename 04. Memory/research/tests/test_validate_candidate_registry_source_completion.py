from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_candidate_registry.py"
SPEC = importlib.util.spec_from_file_location("candidate_registry_validator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def test_source_completion_can_revoke_build_and_run_authority(monkeypatch, tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"{}\n")
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
    monkeypatch.setattr(SUT, "normalized_workspace_path", lambda *_args: artifact)

    prior_validation = {
        "source_build_authorized": True,
        "source_run_authorized": True,
        "source_feasibility_attempt_id": "ATTEMPT-001",
        "probe_status": "RUN_AUTHORIZED",
        **{field: False for field in SUT.SOURCE_ONLY_FALSE_FIELDS},
    }
    prior_metrics = dict(SUT.SOURCE_ONLY_ZERO_METRICS)
    prior = {
        "hypothesis_id": "HYP-TEST-001",
        "state": "probe",
        "verdict": "RUN_AUTHORIZED",
        "reason": "pre-run",
        "updated_at_utc": "2026-01-01T00:00:00Z",
        "run_ids": [],
        "metrics": prior_metrics,
        "validation": prior_validation,
    }

    successor = copy.deepcopy(prior)
    successor.update(
        verdict="PASS_SOURCE_FEASIBILITY",
        reason="one-shot source inventory passed",
        updated_at_utc="2026-01-01T00:01:00Z",
        run_ids=["ATTEMPT-001"],
    )
    successor["metrics"]["source_feasibility_attempts_consumed"] = 1
    successor["metrics"]["source_runs_executed"] = 1
    successor["validation"].update(
        source_build_authorized=False,
        source_run_authorized=False,
        probe_status="PASS_SOURCE_INVENTORY",
        source_feasibility_result_valid=True,
        source_feasibility_verdict="PASS_SOURCE_FEASIBILITY",
        economic_edge_evaluated=False,
        market_no_edge_claim_authorized=False,
    )
    for stem in (
        "attempt_started",
        "attempt_terminal",
        "source_report",
        "source_ledger",
        "source_feasibility_receipt",
    ):
        successor["validation"][f"{stem}_path"] = f"evidence/{stem}.json"
        successor["validation"][f"{stem}_sha256"] = artifact_sha

    assert SUT._generic_source_only_completion_errors(prior, 2, successor) == []
