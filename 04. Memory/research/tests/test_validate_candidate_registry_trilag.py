from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
MODULE_PATH = RESEARCH / "validate_candidate_registry.py"
REGISTRY_PATH = RESEARCH / "CANDIDATE_REGISTRY.jsonl"
SPEC = importlib.util.spec_from_file_location("candidate_registry_validator_trilag", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def actual_transition() -> tuple[dict[str, object], dict[str, object]]:
    rows = [
        json.loads(line)
        for line in REGISTRY_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
        and json.loads(line).get("hypothesis_id") == SUT.TRILAG_HYP002_ID
    ]
    prior = next(
        row for row in rows
        if row.get("verdict") == "FROZEN_DESIGN_EXPORT_RUN_AUTHORIZED"
    )
    successor = next(
        row for row in rows
        if row.get("verdict") == "FROZEN_DESIGN_STRUCTURE_EVALUATION_AUTHORIZED"
    )
    return prior, successor


def test_trilag_export_can_open_exact_one_use_structural_evaluation(
    monkeypatch, tmp_path: Path
) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"{}\n")
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: artifact)
    prior, successor = actual_transition()
    assert SUT._trilag_export_to_structure_transition_errors(
        prior, 350, successor
    ) == []


def test_trilag_transition_rejects_metric_or_authority_drift(monkeypatch, tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_bytes(b"{}\n")
    monkeypatch.setattr(SUT, "verify_binding", lambda *_args: artifact)
    prior, successor = actual_transition()

    metric_drift = copy.deepcopy(successor)
    metric_drift["metrics"]["prices_read"] -= 1
    errors = SUT._trilag_export_to_structure_transition_errors(
        prior, 350, metric_drift
    )
    assert any("metrics must exactly reconcile" in error for error in errors)

    authority_drift = copy.deepcopy(successor)
    authority_drift["validation"]["economics_authorized"] = True
    errors = SUT._trilag_export_to_structure_transition_errors(
        prior, 350, authority_drift
    )
    assert any("economics_authorized" in error for error in errors)


def test_latest_trilag_authority_requires_absent_evidence_root(
    monkeypatch, tmp_path: Path
) -> None:
    _, successor = actual_transition()
    errors: list[str] = []
    monkeypatch.setattr(SUT, "normalized_workspace_path", lambda *_args: tmp_path / "absent")
    SUT._validate_trilag_structure_root_absent(successor, 350, errors)
    assert errors == []

    existing = tmp_path / "existing"
    existing.mkdir()
    monkeypatch.setattr(SUT, "normalized_workspace_path", lambda *_args: existing)
    SUT._validate_trilag_structure_root_absent(successor, 350, errors)
    assert any("structural evidence root must be absent" in error for error in errors)
