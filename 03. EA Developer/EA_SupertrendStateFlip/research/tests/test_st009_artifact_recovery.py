from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


RESEARCH = Path(__file__).resolve().parents[1]
COLLECTOR_PATH = RESEARCH / "collect_st009_existing_run.py"
COMPARATOR_PATH = RESEARCH / "compare_st009_existing_run_parity.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector = load_module("st009_collector_test", COLLECTOR_PATH)
comparator = load_module("st009_comparator_test", COMPARATOR_PATH)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_fresh_attempt_ids_and_no_mt5_launcher_surface() -> None:
    assert collector.AUTHORITY_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-009"
    assert collector.ATTEMPT_ID == "ST009-ARTIFACT-COLLECT-001"
    assert comparator.COMPARATOR_ATTEMPT_ID == "ST009-COMPARATOR-001"
    text = COLLECTOR_PATH.read_text(encoding="utf-8")
    assert "subprocess" not in text
    assert "alpha.ps1" not in text
    assert "Tester/logs" not in text
    assert "rglob" not in text


def test_claim_precedes_every_existing_run_or_common_read() -> None:
    text = COLLECTOR_PATH.read_text(encoding="utf-8")
    claim = text.index("marker = claim(authority)")
    artifact_map = text.index('files = {', claim)
    assert claim < artifact_map
    assert 'write_exclusive(terminal_path' in text
    assert '"status": "FAILED"' in text
    assert '"same_id_retry_authorized": False' in text


def test_identical_run_local_summaries_are_normalized_once(tmp_path: Path) -> None:
    journal = tmp_path / "tester_journal_delta.log"
    journal.write_text(
        "terminal prefix " + collector.FROZEN_SUMMARY + "\n"
        "Core 01 prefix " + collector.FROZEN_SUMMARY + "\n",
        encoding="utf-8",
    )
    normalized, count = collector.validate_identical_current_summaries(journal)
    assert normalized == (collector.FROZEN_SUMMARY + "\n").encode("ascii")
    assert count == 2


def test_distinct_or_fatal_run_local_summary_fails_closed(tmp_path: Path) -> None:
    journal = tmp_path / "tester_journal_delta.log"
    journal.write_text(
        collector.FROZEN_SUMMARY + "\n" + collector.FROZEN_SUMMARY.replace("raw=690", "raw=691") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing, distinct or not frozen"):
        collector.validate_identical_current_summaries(journal)
    journal.write_text("ST003_FATAL|current\n" + collector.FROZEN_SUMMARY + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contains ST003_FATAL"):
        collector.validate_identical_current_summaries(journal)


def test_collector_authority_forbids_mt5_and_is_one_shot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "hypothesis_id": collector.AUTHORITY_HYPOTHESIS_ID,
        "state": "screened",
        "model": 0,
        "verdict": "FROZEN_ST009_EXISTING_RUN_RECOVERY_AUTHORIZED",
        "metrics": {"artifact_collection_attempts_consumed": 0},
        "validation": {
            "artifact_collection_authorized": True,
            "artifact_collection_attempt_id": collector.ATTEMPT_ID,
            "artifact_collection_attempt_limit": 1,
            "reviewed_recovery_collector_sha256": file_sha(COLLECTOR_PATH),
            "mt5_authorized": False,
            "mt5_parity_run_authorized": False,
            "economics_authorized": False,
            "performance_metrics_authorized": False,
            "live_trading_authorized": False,
            "compile_authorized": False,
            "run_compile_authorized": False,
            "mql5_compile_authorized": False,
            "standalone_compile_authorized": False,
            "trade_api_authorized": False,
            "outcome_prices_authorized": False,
            "post_event_ohlc_authorized": False,
            "optimization_authorized": False,
            "validation_authorized": False,
            "holdout_authorized": False,
            "research_validation_access_authorized": False,
            "research_holdout_access_authorized": False,
            "promotion_eligible": False,
            "paper_trading_authorized": False,
            "market_edge_claim_authorized": False,
            "same_id_retry_authorized": False,
            "registry_mutation_allowed": False,
        },
    }
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    collector.validate_registry(registry)
    row["validation"]["mt5_authorized"] = True
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no_mt5"):
        collector.validate_registry(registry)
    row["validation"]["mt5_authorized"] = False
    row["metrics"]["artifact_collection_attempts_consumed"] = 1
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unconsumed"):
        collector.validate_registry(registry)


@pytest.mark.parametrize(
    ("field", "gate"),
    [
        ("mql5_compile_authorized", "no_compile"),
        ("standalone_compile_authorized", "no_compile"),
        ("research_validation_access_authorized", "no_research"),
        ("research_holdout_access_authorized", "no_research"),
        ("same_id_retry_authorized", "no_retry_mutation"),
        ("registry_mutation_allowed", "no_retry_mutation"),
    ],
)
def test_collector_rejects_broadened_authority(field: str, gate: str, tmp_path: Path) -> None:
    validation = {
        "artifact_collection_authorized": True,
        "artifact_collection_attempt_id": collector.ATTEMPT_ID,
        "artifact_collection_attempt_limit": 1,
        "reviewed_recovery_collector_sha256": file_sha(COLLECTOR_PATH),
        "mt5_authorized": False,
        "mt5_parity_run_authorized": False,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "live_trading_authorized": False,
        "compile_authorized": False,
        "run_compile_authorized": False,
        "mql5_compile_authorized": False,
        "standalone_compile_authorized": False,
        "trade_api_authorized": False,
        "outcome_prices_authorized": False,
        "post_event_ohlc_authorized": False,
        "optimization_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "research_validation_access_authorized": False,
        "research_holdout_access_authorized": False,
        "promotion_eligible": False,
        "paper_trading_authorized": False,
        "market_edge_claim_authorized": False,
        "same_id_retry_authorized": False,
        "registry_mutation_allowed": False,
    }
    validation[field] = True
    row = {
        "hypothesis_id": collector.AUTHORITY_HYPOTHESIS_ID,
        "state": "screened",
        "model": 0,
        "verdict": "FROZEN_ST009_EXISTING_RUN_RECOVERY_AUTHORIZED",
        "metrics": {"artifact_collection_attempts_consumed": 0},
        "validation": validation,
    }
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=gate):
        collector.validate_registry(registry)


@pytest.mark.parametrize(
    ("field", "gate"),
    [
        ("mql5_compile_authorized", "no_compile"),
        ("standalone_compile_authorized", "no_compile"),
        ("research_validation_access_authorized", "no_validation"),
        ("research_holdout_access_authorized", "no_holdout"),
        ("same_id_retry_authorized", "no_retry_mutation"),
        ("registry_mutation_allowed", "no_retry_mutation"),
    ],
)
def test_comparator_rejects_broadened_authority(field: str, gate: str, tmp_path: Path) -> None:
    validation = {
        "reviewed_recovery_collector_sha256": file_sha(COLLECTOR_PATH),
        "reviewed_recovery_comparator_sha256": file_sha(COMPARATOR_PATH),
        "reviewed_recovery_test_sha256": file_sha(Path(__file__)),
        "artifact_collection_attempt_id": comparator.COLLECTION_ATTEMPT_ID,
        "artifact_collection_attempt_limit": 1,
        "comparator_execution_authorized": True,
        "comparator_attempt_id": comparator.COMPARATOR_ATTEMPT_ID,
        "comparator_attempt_limit": 1,
        "mt5_authorized": False,
        "mt5_parity_run_authorized": False,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
        "live_trading_authorized": False,
        "compile_authorized": False,
        "run_compile_authorized": False,
        "mql5_compile_authorized": False,
        "standalone_compile_authorized": False,
        "trade_api_authorized": False,
        "outcome_prices_authorized": False,
        "post_event_ohlc_authorized": False,
        "optimization_authorized": False,
        "validation_authorized": False,
        "research_validation_access_authorized": False,
        "holdout_authorized": False,
        "research_holdout_access_authorized": False,
        "paper_trading_authorized": False,
        "promotion_eligible": False,
        "market_edge_claim_authorized": False,
        "same_id_retry_authorized": False,
        "registry_mutation_allowed": False,
    }
    validation[field] = True
    row = {
        "hypothesis_id": comparator.AUTHORITY_HYPOTHESIS_ID,
        "state": "screened",
        "model": 0,
        "verdict": "FROZEN_ST009_EXISTING_RUN_RECOVERY_AUTHORIZED",
        "metrics": {"artifact_collection_attempts_consumed": 0, "comparator_attempts_consumed": 0},
        "validation": validation,
    }
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    args = SimpleNamespace(artifact_collector=COLLECTOR_PATH, test_source=Path(__file__))
    with pytest.raises(ValueError, match=gate):
        comparator.validate_registry_authority(registry, args)


def test_comparator_uses_recovered_paths_and_inherited_hyp008_identity() -> None:
    text = COMPARATOR_PATH.read_text(encoding="utf-8")
    assert comparator.AUTHORITY_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-009"
    assert comparator.RUN_HYPOTHESIS_ID == "HYP-ST-XAUUSD-H1-008"
    assert '"normalized_summary": args.tester_journal' in text
    assert '"recovered_compile_log": args.compile_log' in text
    assert '"recovered_csv": args.mql_audit' in text
    assert 'BASE.AUTHORITY_HYPOTHESIS_ID = RUN_HYPOTHESIS_ID' in text
    assert 'BASE.__file__ = str(Path(__file__).resolve())' in text
    assert "report = BASE.execute(args)" not in text
    assert '"recovered_compile_log"' in text
    assert '"status": "FAILED"' in text
    assert 'write_exclusive(terminal_path' in text
    assert 'mutable-source capture/recovery reconciliation mismatch' in text
    assert 'HYP009 canonical recovery path mismatch' in text
    assert 'HYP009 recovery receipt authority-row binding mismatch' in text
    assert 'HYP009 comparator output must use the canonical evidence root' in text
    assert "ECONOMIC_CHILD_AUTHORIZED" not in text


def test_receipt_never_rehashes_mutable_sources_after_snapshot() -> None:
    text = COLLECTOR_PATH.read_text(encoding="utf-8")
    assert 'if label not in {"compile_log", "common_csv"}' in text
    assert '"sha256": compile_source_meta["captured_sha256"]' in text
    assert '"sha256": csv_source_meta["captured_sha256"]' in text
    assert 'captured mutable source hashes do not match sealed recovery artifacts' in text


def test_frozen_existing_artifact_hashes_are_declared() -> None:
    assert collector.EXPECTED["run_manifest"] == comparator.EXPECTED_RUN_MANIFEST_SHA256
    assert collector.EXPECTED["source"] == comparator.EXPECTED_SOURCE_SHA256
    assert collector.EXPECTED["ex5"] == comparator.EXPECTED_EX5_SHA256
    assert collector.EXPECTED["compile_log"] == comparator.EXPECTED_COMPILE_SHA256
    assert collector.EXPECTED["report"] == comparator.EXPECTED_REPORT_SHA256
    assert collector.BASE_COLLECTOR_SHA256 == file_sha(RESEARCH / "collect_st004_mt5_artifacts.py")
    assert comparator.BASE_COMPARATOR_SHA256 == file_sha(RESEARCH / "compare_st003_mql5_parity.py")
