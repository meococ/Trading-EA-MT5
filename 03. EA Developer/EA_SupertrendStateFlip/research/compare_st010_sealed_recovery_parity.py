#!/usr/bin/env python3
"""Run HYP010 parity from the sealed HYP009 artifact-recovery chain only."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-010"
COLLECTION_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-009"
RUN_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
TARGET_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
COLLECTION_ATTEMPT_ID = "ST009-ARTIFACT-COLLECT-001"
COMPARATOR_ATTEMPT_ID = "ST010-COMPARATOR-001"
COLLECTION_ROOT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-009/ST009-ARTIFACT-COLLECT-001"
COMPARATOR_ROOT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-010/ST010-COMPARATOR-001"
RUN_SOURCE_SNAPSHOT = ROOT / "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/snapshot/source/EA_SupertrendStateFlip.mq5"
HISTORICAL_AUTHORITY_ROW_SHA256 = "3BAD69ED145D3133AA806792DAD836243F08B9264C2BBB44627F9ACB99882A70"
HYP009_TERMINAL_ROW_SHA256 = "75120889128610339D5DCE0A0F11B471E3D38F3597C728BC8DB5085C5DB0B70D"
COLLECTION_RECEIPT_SHA256 = "398194E68C53E7C78BD7963EAD4AB9A64B4ABC889CF9510EAF1E73A84C41E434"
COLLECTION_TERMINAL_SHA256 = "838D2A803CDA6F071DF057F2DC3E973CFCB12FCB46179AC4DA995AD146B6BD72"
HYP009_COMPARATOR_SHA256 = "A68CB44C72BAC8BB73BC151C21150E9968826764BFD6EB3580640CBBA7E067E1"
COLLECTOR_SHA256 = "8BC9B55070779E0B9B8E8834F95DD6F58512B25EB2976A1CBED8A30B8319EF2D"
DISCLOSURE_PATH = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-009_POST_TERMINAL_READ_DISCLOSURE.md"
DISCLOSURE_SHA256 = "C85948D1CBF333A3F57517D9E4D8CDA20F17947759CE20113D22239F1FCB1CFA"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_hyp009():
    path = Path(__file__).resolve().with_name("compare_st009_existing_run_parity.py")
    if sha256_file(path) != HYP009_COMPARATOR_SHA256:
        raise ValueError("frozen HYP009 comparator dependency hash drift")
    spec = importlib.util.spec_from_file_location("st010_hyp009_comparator_dependency", path)
    if not spec or not spec.loader:
        raise ValueError("cannot load frozen HYP009 comparator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_hyp009()
ORIGINAL_ORACLE_CHAIN_VALIDATOR = BASE.BASE.validate_oracle_chain


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def registry_rows(path: Path, hypothesis_id: str) -> list[tuple[bytes, dict[str, Any]]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == hypothesis_id:
            matches.append((raw, row))
    return matches


def validate_registry_authority(registry_path: Path, args: Any) -> tuple[dict[str, Any], dict[str, str]]:
    matches = registry_rows(registry_path, AUTHORITY_HYPOTHESIS_ID)
    if not matches:
        raise ValueError("missing HYP010 comparator-only authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_ST010_SEALED_COMPARATOR_AUTHORIZED",
        "comparator": validation.get("reviewed_sealed_comparator_sha256") == sha256_file(Path(__file__).resolve()),
        "dependency": validation.get("reviewed_hyp009_comparator_sha256") == HYP009_COMPARATOR_SHA256,
        "collector_metadata": validation.get("reviewed_recovery_collector_sha256") == COLLECTOR_SHA256,
        "test_metadata": isinstance(validation.get("reviewed_sealed_comparator_test_sha256"), str)
        and len(validation.get("reviewed_sealed_comparator_test_sha256")) == 64,
        "source": validation.get("reviewed_mql_source_sha256") == BASE.EXPECTED_SOURCE_SHA256,
        "source_path": args.mql_source.resolve() == RUN_SOURCE_SNAPSHOT.resolve()
        and validation.get("reviewed_mql_source_path") == "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257/snapshot/source/EA_SupertrendStateFlip.mq5",
        "historical_row": validation.get("historical_hyp009_authority_row_sha256") == HISTORICAL_AUTHORITY_ROW_SHA256,
        "terminal_row": validation.get("hyp009_terminal_row_sha256") == HYP009_TERMINAL_ROW_SHA256,
        "collection_receipt": validation.get("hyp009_collection_receipt_sha256") == COLLECTION_RECEIPT_SHA256,
        "collection_terminal": validation.get("hyp009_collection_terminal_sha256") == COLLECTION_TERMINAL_SHA256,
        "disclosure_metadata": validation.get("hyp009_read_disclosure_path")
        == "03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-009_POST_TERMINAL_READ_DISCLOSURE.md"
        and validation.get("hyp009_read_disclosure_sha256") == DISCLOSURE_SHA256,
        "no_collection": validation.get("artifact_collection_authorized") is False,
        "compare": validation.get("comparator_execution_authorized") is True,
        "compare_id": validation.get("comparator_attempt_id") == COMPARATOR_ATTEMPT_ID,
        "compare_limit": validation.get("comparator_attempt_limit") == 1,
        "compare_unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "no_mt5": validation.get("mt5_authorized") is False and validation.get("mt5_parity_run_authorized") is False,
        "no_compile": validation.get("compile_authorized") is False
        and validation.get("run_compile_authorized") is False
        and validation.get("mql5_compile_authorized") is False
        and validation.get("standalone_compile_authorized") is False,
        "no_trade": validation.get("trade_api_authorized") is False,
        "no_outcomes": validation.get("performance_metrics_authorized") is False
        and validation.get("outcome_prices_authorized") is False
        and validation.get("post_event_ohlc_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_research": validation.get("optimization_authorized") is False
        and validation.get("validation_authorized") is False
        and validation.get("holdout_authorized") is False
        and validation.get("research_validation_access_authorized") is False
        and validation.get("research_holdout_access_authorized") is False,
        "no_deploy": validation.get("promotion_eligible") is False
        and validation.get("paper_trading_authorized") is False
        and validation.get("live_trading_authorized") is False
        and validation.get("market_edge_claim_authorized") is False,
        "no_retry_mutation": validation.get("same_id_retry_authorized") is False
        and validation.get("registry_mutation_allowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP010 comparator authority failed: {failed}")
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def validate_authority_bound_files(args: Any) -> None:
    matches = registry_rows(args.registry.resolve(), AUTHORITY_HYPOTHESIS_ID)
    if not matches:
        raise ValueError("missing HYP010 post-claim authority")
    _, row = matches[-1]
    validation = row.get("validation", {})
    actual_checks = {
        "collector_file": sha256_file(args.artifact_collector.resolve())
        == validation.get("reviewed_recovery_collector_sha256"),
        "test_file": sha256_file(args.test_source.resolve())
        == validation.get("reviewed_sealed_comparator_test_sha256"),
        "mql_source_file": sha256_file(args.mql_source.resolve())
        == validation.get("reviewed_mql_source_sha256"),
    }
    failed = [name for name, passed in actual_checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP010 post-claim artifact binding failed: {failed}")
    bound = {
        "oracle": (args.oracle, validation.get("oracle_sha256")),
        "oracle_start": (args.oracle_start, validation.get("oracle_start_sha256")),
        "oracle_report": (args.oracle_report, validation.get("oracle_report_sha256")),
        "oracle_receipt": (args.oracle_receipt, validation.get("oracle_receipt_sha256")),
        "oracle_terminal": (args.oracle_terminal, validation.get("oracle_terminal_sha256")),
        "mql_source": (args.mql_source, validation.get("reviewed_mql_source_sha256")),
        "test_source": (args.test_source, validation.get("reviewed_sealed_comparator_test_sha256")),
        "legacy_test": (args.legacy_test_source, validation.get("reviewed_hyp003_test_sha256")),
        "nonrepaint_manifest": (args.nonrepaint_manifest, validation.get("nonrepaint_manifest_sha256")),
        "nonrepaint_audit": (args.nonrepaint_audit, validation.get("nonrepaint_audit_sha256")),
        "contract_receipt": (args.contract_receipt, validation.get("hyp008_contract_receipt_sha256")),
        "collector": (args.artifact_collector, validation.get("reviewed_recovery_collector_sha256")),
        "authority_prereg": (args.authority_prereg, row.get("prereg_sha256")),
        "hyp009_read_disclosure": (DISCLOSURE_PATH, validation.get("hyp009_read_disclosure_sha256")),
    }
    for label, (path, expected) in bound.items():
        BASE.BASE.require_bound_file(path.resolve(), str(expected or ""), label)


def validate_oracle_chain_after_claim(args: Any) -> None:
    validate_authority_bound_files(args)
    ORIGINAL_ORACLE_CHAIN_VALIDATOR(args)


def validate_artifact_collection_chain(args: Any) -> None:
    receipt = load_json(args.artifact_receipt)
    terminal = load_json(args.artifact_terminal)
    if (
        receipt.get("schema_version") != "st009_existing_run_artifact_recovery_receipt.v1"
        or receipt.get("hypothesis_id") != COLLECTION_HYPOTHESIS_ID
        or receipt.get("run_hypothesis_id") != RUN_HYPOTHESIS_ID
        or receipt.get("attempt_id") != COLLECTION_ATTEMPT_ID
        or receipt.get("summary_occurrences") != 2
        or receipt.get("summary_distinct") != 1
        or receipt.get("verdict") != "EXISTING_HYP008_ARTIFACT_RECOVERY_PASS"
        or receipt.get("orders_executed") != 0
        or receipt.get("trades_executed") != 0
        or receipt.get("economics_evaluated") is not False
    ):
        raise ValueError("sealed HYP009 artifact recovery receipt mismatch")
    expected_counters = {
        "rows": 29460,
        "raw_events": 690,
        "executable_events": 683,
        "gap_rejected_events": 7,
        "long_events": 339,
        "short_events": 344,
    }
    counters = receipt.get("counters", {})
    if any(counters.get(key) != value for key, value in expected_counters.items()):
        raise ValueError("sealed HYP009 recovery counters mismatch")

    if sha256_file(args.artifact_receipt.resolve()) != COLLECTION_RECEIPT_SHA256:
        raise ValueError("sealed HYP009 collection receipt hash mismatch")
    if sha256_file(args.artifact_terminal.resolve()) != COLLECTION_TERMINAL_SHA256:
        raise ValueError("sealed HYP009 collection terminal hash mismatch")

    rows = registry_rows(args.registry.resolve(), COLLECTION_HYPOTHESIS_ID)
    historical = [
        row for raw, row in rows
        if hashlib.sha256(raw).hexdigest().upper() == HISTORICAL_AUTHORITY_ROW_SHA256
    ]
    if len(historical) != 1 or historical[0].get("state") != "screened":
        raise ValueError("historical HYP009 authority row missing or ambiguous")
    terminal_raw, terminal_row = rows[-1]
    if (
        hashlib.sha256(terminal_raw).hexdigest().upper() != HYP009_TERMINAL_ROW_SHA256
        or terminal_row.get("state") != "killed"
        or terminal_row.get("verdict") != "KILL_EXACT_COMPARATOR_AUTHORITY_BINDING"
        or terminal_row.get("metrics", {}).get("artifact_collection_attempts_consumed") != 1
        or terminal_row.get("metrics", {}).get("comparator_attempts_consumed") != 0
        or terminal_row.get("validation", {}).get("historical_authority_row_sha256") != HISTORICAL_AUTHORITY_ROW_SHA256
        or terminal_row.get("validation", {}).get("collection_receipt_sha256") != COLLECTION_RECEIPT_SHA256
        or terminal_row.get("validation", {}).get("collection_terminal_sha256") != COLLECTION_TERMINAL_SHA256
    ):
        raise ValueError("terminal HYP009 lineage mismatch")

    bindings = receipt.get("bindings", {})
    if bindings.get("registry", {}).get("latest_row_sha256") != HISTORICAL_AUTHORITY_ROW_SHA256:
        raise ValueError("HYP009 receipt did not bind the frozen historical authority row")
    canonical_paths = {
        "artifact_receipt": COLLECTION_ROOT / "artifact_recovery_receipt.json",
        "artifact_terminal": COLLECTION_ROOT / "attempt_terminal.json",
        "mql_audit": COLLECTION_ROOT / "st003_mql5_parity.csv",
        "tester_journal": COLLECTION_ROOT / "st009_normalized_tester_summary.log",
        "compile_log": COLLECTION_ROOT / "ST004_MetaEditor_compile.log",
        "collector": ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/collect_st009_existing_run.py",
    }
    actual_paths = {
        "artifact_receipt": args.artifact_receipt,
        "artifact_terminal": args.artifact_terminal,
        "mql_audit": args.mql_audit,
        "tester_journal": args.tester_journal,
        "compile_log": args.compile_log,
        "collector": args.artifact_collector,
    }
    wrong = [name for name, expected in canonical_paths.items() if actual_paths[name].resolve() != expected.resolve()]
    if wrong:
        raise ValueError(f"HYP010 canonical sealed-input path mismatch: {wrong}")
    exact_bindings = {
        "recovered_csv": args.mql_audit,
        "normalized_summary": args.tester_journal,
        "recovered_compile_log": args.compile_log,
        "collector": args.artifact_collector,
        "run_manifest": args.run_manifest,
        "report": args.tester_report,
        "source": args.mql_source,
        "ex5": args.compiled_ex5,
        "contract_receipt": args.contract_receipt,
    }
    for label, path in exact_bindings.items():
        binding = bindings.get(label, {})
        if not BASE.BASE.same_path(binding.get("path"), path.resolve()) or binding.get("sha256") != sha256_file(path.resolve()):
            raise ValueError(f"sealed HYP009 artifact binding mismatch: {label}")
    if (
        bindings.get("common_csv", {}).get("sha256") != bindings.get("recovered_csv", {}).get("sha256")
        or bindings.get("compile_log", {}).get("sha256") != bindings.get("recovered_compile_log", {}).get("sha256")
        or bindings.get("common_csv", {}).get("captured_sha256") != BASE.EXPECTED_SOURCE_COMMON_SHA256
        or bindings.get("compile_log", {}).get("captured_sha256") != BASE.EXPECTED_COMPILE_SHA256
    ):
        raise ValueError("sealed mutable-source recovery reconciliation mismatch")
    if (
        terminal.get("schema_version") != "st009_existing_run_artifact_recovery_terminal.v1"
        or terminal.get("hypothesis_id") != COLLECTION_HYPOTHESIS_ID
        or terminal.get("attempt_id") != COLLECTION_ATTEMPT_ID
        or terminal.get("status") != "COMPLETE"
        or terminal.get("receipt_sha256") != COLLECTION_RECEIPT_SHA256
        or terminal.get("same_id_retry_authorized") is not False
    ):
        raise ValueError("sealed HYP009 artifact recovery terminal mismatch")


def main() -> int:
    BASE.AUTHORITY_HYPOTHESIS_ID = AUTHORITY_HYPOTHESIS_ID
    BASE.RUN_HYPOTHESIS_ID = RUN_HYPOTHESIS_ID
    BASE.TARGET_HYPOTHESIS_ID = TARGET_HYPOTHESIS_ID
    BASE.COLLECTION_ATTEMPT_ID = COLLECTION_ATTEMPT_ID
    BASE.COMPARATOR_ATTEMPT_ID = COMPARATOR_ATTEMPT_ID
    BASE.COLLECTION_ROOT = COLLECTION_ROOT
    BASE.COMPARATOR_ROOT = COMPARATOR_ROOT
    BASE.__file__ = str(Path(__file__).resolve())
    BASE.validate_registry_authority = validate_registry_authority
    BASE.validate_artifact_collection_chain = validate_artifact_collection_chain
    BASE.BASE.validate_oracle_chain = validate_oracle_chain_after_claim
    return BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
