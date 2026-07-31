from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
VALIDATOR_PATH = ROOT / "04. Memory/research/validate_candidate_registry.py"
SCHEMA_PATH = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.schema.json"
REGISTRY_PATH = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
PLAN_REL = "03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-001_PROBE_PLAN.md"
BUILDER_REL = "03. EA Developer/EA_RoundNumberCascade/research/build_round_cascade_001_source.py"
TEST_REL = "03. EA Developer/EA_RoundNumberCascade/research/tests/test_build_round_cascade_001_source.py"
RECEIPT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-001_INDEPENDENT_SOURCE_REVIEW_RECEIPT.json"
)
EVIDENCE_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-001_SOURCE_FEASIBILITY/HYP001-SOURCE-PREFLIGHT-001"
)
RECEIPT_SCHEMA = "round_cascade_independent_source_review.v1"


def load_validator():
    spec = importlib.util.spec_from_file_location("round_registry_validator_test", VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def copy_file(root: Path, relative: str) -> bytes:
    payload = (ROOT / relative).read_bytes()
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return payload


def make_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    validator = load_validator()
    monkeypatch.setattr(validator, "WORKSPACE", tmp_path)
    plan_payload = copy_file(tmp_path, PLAN_REL)
    builder_payload = copy_file(tmp_path, BUILDER_REL)
    test_payload = copy_file(tmp_path, TEST_REL)

    rows = [json.loads(line) for line in REGISTRY_PATH.read_text(encoding="utf-8").splitlines()]
    prior = next(
        row
        for row in reversed(rows)
        if row["hypothesis_id"] == "HYP-ROUND-CASCADE-EURUSD-M5-001"
        and row["state"] == "probe"
        and row["validation"].get("source_build_authorized") is True
        and row["validation"].get("source_run_authorized") is False
    )
    assert prior["hypothesis_id"] == "HYP-ROUND-CASCADE-EURUSD-M5-001"
    assert sha256(plan_payload) == prior["prereg_sha256"]
    builder_path = tmp_path / BUILDER_REL
    errors: list[str] = []
    builder_base_sha = validator._reviewed_base_source_sha256(builder_path, "test", errors)
    assert errors == [] and builder_base_sha
    test_sha = sha256(test_payload)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "hypothesis_id": prior["hypothesis_id"],
        "review_status": "PASS",
        "reviewed_builder": {"path": BUILDER_REL, "base_sha256": builder_base_sha},
        "reviewed_tests": {"path": TEST_REL, "sha256": test_sha},
        "v1_plan": {"path": PLAN_REL, "sha256": prior["prereg_sha256"]},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    receipt_payload = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    receipt_path = tmp_path / RECEIPT_REL
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(receipt_payload)

    successor = copy.deepcopy(prior)
    successor["updated_at_utc"] = "2026-07-28T20:00:00Z"
    successor["verdict"] = "FROZEN_SOURCE_FEASIBILITY_RUN_AUTHORIZED_AFTER_INDEPENDENT_REVIEW"
    successor["reason"] = "Reviewed source-only implementation is bound for exactly one attempt; all outcomes and runtimes remain sealed."
    validation = successor["validation"]
    validation["probe_status"] = successor["verdict"]
    validation["source_build_authorized"] = False
    validation["source_run_authorized"] = True
    validation.update(
        {
            "independent_implementation_review_status": "PASS",
            "independent_pre_run_review_status": "PASS",
            "independent_quant_prereg_review_status": "PASS",
            "reviewed_builder_path": BUILDER_REL,
            "reviewed_builder_base_sha256": builder_base_sha,
            "reviewed_test_path": TEST_REL,
            "reviewed_test_sha256": test_sha,
            "independent_review_receipt_path": RECEIPT_REL,
            "independent_review_receipt_schema": RECEIPT_SCHEMA,
            "independent_review_receipt_sha256": sha256(receipt_payload),
            "source_feasibility_attempt_id": "HYP001-SOURCE-PREFLIGHT-001",
            "source_feasibility_evidence_root": EVIDENCE_REL,
        }
    )
    return validator, prior, successor


def transition_errors(validator, prior: dict, successor: dict) -> list[str]:
    return validator._generic_source_only_authority_transition_errors(prior, 2, successor)


def test_valid_generic_probe_to_probe_source_only_authority_successor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    assert transition_errors(validator, prior, successor) == []
    registry = tmp_path / "registry.jsonl"
    registry.write_bytes(
        json.dumps(prior, separators=(",", ":"), ensure_ascii=True).encode()
        + b"\n"
        + json.dumps(successor, separators=(",", ":"), ensure_ascii=True).encode()
        + b"\n"
    )
    assert validator.validate_registry(registry, SCHEMA_PATH) == []


@pytest.mark.parametrize(
    "mutator",
    [
        lambda row: row.__setitem__("ea_name", "EA_Other"),
        lambda row: row.__setitem__("prereg_path", row["prereg_path"] + ".other"),
        lambda row: row["window"].__setitem__("from", "2017.01.01"),
        lambda row: row.__setitem__("model", 0),
        lambda row: row["acceptance_contract"].__setitem__("min_profit_factor", 1.31),
    ],
)
def test_rejects_frozen_contract_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutator
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    mutator(successor)
    assert transition_errors(validator, prior, successor)


@pytest.mark.parametrize("field", ["economics_authorized", "model0_authorized", "mt5_authorized", "network_authorized"])
def test_rejects_forbidden_runtime_or_economic_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    successor["validation"][field] = True
    assert any(field in error for error in transition_errors(validator, prior, successor))
    del successor["validation"][field]
    assert transition_errors(validator, prior, successor)


@pytest.mark.parametrize(
    "field",
    ["reviewed_builder_base_sha256", "reviewed_test_sha256", "independent_review_receipt_sha256"],
)
def test_rejects_tampered_review_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    successor["validation"][field] = "0" * 64
    assert transition_errors(validator, prior, successor)


def test_rejects_existing_or_outside_evidence_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    (tmp_path / EVIDENCE_REL).mkdir(parents=True)
    errors = transition_errors(validator, prior, successor)
    validator._validate_generic_source_root_absent(successor, 2, errors)
    assert any("must be absent" in error for error in errors)
    successor["validation"]["source_feasibility_evidence_root"] = "outside/HYP001-SOURCE-PREFLIGHT-001"
    assert transition_errors(validator, prior, successor)


def test_rejects_hyp007_bindings_or_nonzero_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    successor["validation"]["source_run_bindings"] = {}
    assert transition_errors(validator, prior, successor)
    successor["validation"].pop("source_run_bindings")
    successor["metrics"]["source_runs_executed"] = 1
    assert any("counters" in error for error in transition_errors(validator, prior, successor))


def test_rejects_noncompact_authority_successor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator, prior, successor = make_contract(tmp_path, monkeypatch)
    registry = tmp_path / "registry.jsonl"
    registry.write_bytes(
        json.dumps(prior, separators=(",", ":"), ensure_ascii=True).encode()
        + b"\n"
        + json.dumps(successor, separators=(", ", ": "), ensure_ascii=True).encode()
        + b"\n"
    )
    errors = validator.validate_registry(registry, SCHEMA_PATH)
    assert any("compact insertion-order JSON" in error for error in errors)


def test_exact_hyp001_duplicate_terminal_reconciliation_is_one_use(tmp_path: Path) -> None:
    validator = load_validator()
    assert validator.validate_registry(REGISTRY_PATH, SCHEMA_PATH) == []
    records = REGISTRY_PATH.read_bytes().splitlines(keepends=True)
    assert len(records) >= 294
    row = json.loads(records[293])
    row["reason"] = row["reason"] + " tampered"
    records[293] = json.dumps(row, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"
    mutated = tmp_path / "mutated_registry.jsonl"
    mutated.write_bytes(b"".join(records))
    errors = validator.validate_registry(mutated, SCHEMA_PATH)
    assert any("illegal transition parked->parked" in error for error in errors)
