from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


RESEARCH = Path(__file__).resolve().parents[1]
WRAPPER_PATH = RESEARCH / "compare_st010_sealed_recovery_parity.py"


def load_module():
    spec = importlib.util.spec_from_file_location("st010_wrapper_test", WRAPPER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wrapper = load_module()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def authority_row(validation_overrides: dict | None = None) -> dict:
    validation = {
        "reviewed_sealed_comparator_sha256": file_sha(WRAPPER_PATH),
        "reviewed_hyp009_comparator_sha256": wrapper.HYP009_COMPARATOR_SHA256,
        "reviewed_recovery_collector_sha256": file_sha(RESEARCH / "collect_st009_existing_run.py"),
        "reviewed_sealed_comparator_test_sha256": file_sha(Path(__file__)),
        "reviewed_mql_source_sha256": wrapper.BASE.EXPECTED_SOURCE_SHA256,
        "reviewed_mql_source_path": "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/snapshot/source/EA_SupertrendStateFlip.mq5",
        "historical_hyp009_authority_row_sha256": wrapper.HISTORICAL_AUTHORITY_ROW_SHA256,
        "hyp009_terminal_row_sha256": wrapper.HYP009_TERMINAL_ROW_SHA256,
        "hyp009_collection_receipt_sha256": wrapper.COLLECTION_RECEIPT_SHA256,
        "hyp009_collection_terminal_sha256": wrapper.COLLECTION_TERMINAL_SHA256,
        "hyp009_read_disclosure_path": "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-009_POST_TERMINAL_READ_DISCLOSURE.md",
        "hyp009_read_disclosure_sha256": wrapper.DISCLOSURE_SHA256,
        "artifact_collection_authorized": False,
        "comparator_execution_authorized": True,
        "comparator_attempt_id": wrapper.COMPARATOR_ATTEMPT_ID,
        "comparator_attempt_limit": 1,
        "mt5_authorized": False,
        "mt5_parity_run_authorized": False,
        "compile_authorized": False,
        "run_compile_authorized": False,
        "mql5_compile_authorized": False,
        "standalone_compile_authorized": False,
        "trade_api_authorized": False,
        "performance_metrics_authorized": False,
        "outcome_prices_authorized": False,
        "post_event_ohlc_authorized": False,
        "economics_authorized": False,
        "optimization_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "research_validation_access_authorized": False,
        "research_holdout_access_authorized": False,
        "promotion_eligible": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "market_edge_claim_authorized": False,
        "same_id_retry_authorized": False,
        "registry_mutation_allowed": False,
    }
    validation.update(validation_overrides or {})
    return {
        "hypothesis_id": wrapper.AUTHORITY_HYPOTHESIS_ID,
        "state": "screened",
        "model": 0,
        "verdict": "FROZEN_ST010_SEALED_COMPARATOR_AUTHORIZED",
        "metrics": {"comparator_attempts_consumed": 0},
        "validation": validation,
    }


def minimal_args() -> SimpleNamespace:
    return SimpleNamespace(
        artifact_collector=RESEARCH / "collect_st009_existing_run.py",
        test_source=Path(__file__),
        mql_source=wrapper.RUN_SOURCE_SNAPSHOT,
        registry=None,
    )


def test_identity_and_frozen_dependency() -> None:
    assert wrapper.AUTHORITY_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-010"
    assert wrapper.COLLECTION_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-009"
    assert wrapper.RUN_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-008"
    assert wrapper.TARGET_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-003"
    assert wrapper.COMPARATOR_ATTEMPT_ID == "ST010-COMPARATOR-001"
    assert wrapper.HYP009_COMPARATOR_SHA256 == file_sha(RESEARCH / "compare_st009_existing_run_parity.py")


def test_no_execution_or_mutable_source_surface() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert "subprocess" not in text
    assert "alpha.ps1" not in text
    assert "Common/Files" not in text
    assert "CANONICAL_COMPILE_LOG" not in text
    assert 'artifact_collection_authorized") is False' in text


def test_preclaim_authority_does_not_hash_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = authority_row()
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    args = minimal_args()
    args.registry = registry

    def forbidden(*_args, **_kwargs):
        raise AssertionError("artifact binding ran before claim")

    monkeypatch.setattr(wrapper.BASE.BASE, "require_bound_file", forbidden)
    wrapper.validate_registry_authority(registry, args)
    assert "require_bound_file" not in inspect.getsource(wrapper.validate_registry_authority)
    assert "require_bound_file" in inspect.getsource(wrapper.validate_authority_bound_files)
    base_execute = inspect.getsource(wrapper.BASE.execute)
    assert base_execute.index("marker = BASE.claim_comparator") < base_execute.index("BASE.validate_oracle_chain")
    assert "validate_authority_bound_files(args)" in inspect.getsource(wrapper.validate_oracle_chain_after_claim)


def test_postclaim_validator_hashes_actual_source(tmp_path: Path) -> None:
    row = authority_row()
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    tampered = tmp_path / "EA_SupertrendStateFlip.mq5"
    tampered.write_text("tampered", encoding="utf-8")
    args = minimal_args()
    args.registry = registry
    args.mql_source = tampered
    with pytest.raises(ValueError, match="mql_source_file"):
        wrapper.validate_authority_bound_files(args)


@pytest.mark.parametrize(
    ("field", "value", "gate"),
    [
        ("reviewed_mql_source_sha256", None, "source"),
        ("reviewed_mql_source_path", "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5", "source_path"),
        ("historical_hyp009_authority_row_sha256", "BAD", "historical_row"),
        ("hyp009_terminal_row_sha256", "BAD", "terminal_row"),
        ("hyp009_read_disclosure_sha256", "BAD", "disclosure_metadata"),
        ("artifact_collection_authorized", True, "no_collection"),
        ("mql5_compile_authorized", True, "no_compile"),
        ("research_validation_access_authorized", True, "no_research"),
        ("same_id_retry_authorized", True, "no_retry_mutation"),
        ("registry_mutation_allowed", True, "no_retry_mutation"),
    ],
)
def test_authority_mutations_fail_before_any_bound_read(
    field: str, value: object, gate: str, tmp_path: Path
) -> None:
    row = authority_row({field: value})
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=gate):
        wrapper.validate_registry_authority(registry, minimal_args())


def test_historical_and_terminal_rows_are_separate_invariants() -> None:
    text = WRAPPER_PATH.read_text(encoding="utf-8")
    assert 'bindings.get("registry", {}).get("latest_row_sha256") != HISTORICAL_AUTHORITY_ROW_SHA256' in text
    assert 'hashlib.sha256(terminal_raw).hexdigest().upper() != HYP009_TERMINAL_ROW_SHA256' in text
    assert "rows[-1]" in text
    assert "historical HYP009 authority row missing or ambiguous" in text
    assert wrapper.DISCLOSURE_SHA256 == file_sha(wrapper.DISCLOSURE_PATH)
    assert '"hyp009_read_disclosure": (DISCLOSURE_PATH' in text


def test_canonical_roots_are_frozen() -> None:
    assert wrapper.COLLECTION_ROOT.as_posix().endswith(
        "HYP-ST-XAUUSD-H1-009/ST009-ARTIFACT-COLLECT-001"
    )
    assert wrapper.COMPARATOR_ROOT.as_posix().endswith(
        "HYP-ST-XAUUSD-H1-010/ST010-COMPARATOR-001"
    )
