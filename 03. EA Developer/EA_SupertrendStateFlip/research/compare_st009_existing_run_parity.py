#!/usr/bin/env python3
"""Run HYP009 correctness-only parity on the sealed artifacts recovered from HYP008."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AUTHORITY_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-009"
RUN_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
TARGET_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-003"
COLLECTION_ATTEMPT_ID = "ST009-ARTIFACT-COLLECT-001"
COMPARATOR_ATTEMPT_ID = "ST009-COMPARATOR-001"
COLLECTION_ROOT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-009/ST009-ARTIFACT-COLLECT-001"
COMPARATOR_ROOT = ROOT / "03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-009/ST009-COMPARATOR-001"
EXPECTED_RUN_MANIFEST_SHA256 = "AC9CA6A3878E6545A86FD743FE3918F3EE3D913024676F48B54C62DEC771B9F8"
EXPECTED_SOURCE_SHA256 = "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
EXPECTED_EX5_SHA256 = "DCE8F2EB93F9FCF6BF827151F576664D21316C5693E76B3886FCC289C499710C"
EXPECTED_COMPILE_SHA256 = "B766F5FBC26B8BAD7679E6D736E588EFA8462DFA1CDBB3E7D1F23550AD9E170D"
EXPECTED_REPORT_SHA256 = "178901C855F050FA18217762509F791870D8CB2A2903CEF08C0436E8A7EE79EB"
EXPECTED_SOURCE_COMMON_SHA256 = "C404DDE7922C757CC0B1B3D7E3AF8F48C7A4E0F219716314A138D1AC4AB61DD3"
FROZEN_SUMMARY = (
    "ST003_SUMMARY|run=ST003-MT5-PARITY-001|reason=1|rows=29460|raw=690|"
    "executable=683|gaps=7|long=339|short=344|failed=false"
)
BASE_COMPARATOR_SHA256 = "0DA75EED50E420209A0A70E48E21FE46D93F21B17D100CA27BF9F0D7DA9BD367"


def load_base():
    path = Path(__file__).resolve().with_name("compare_st003_mql5_parity.py")
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != BASE_COMPARATOR_SHA256:
        raise ValueError("frozen HYP008 comparator dependency hash drift")
    spec = importlib.util.spec_from_file_location("st008_comparator_dependency", path)
    if not spec or not spec.loader:
        raise ValueError("cannot load frozen parity comparator dependency")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_base()
ORIGINAL_NONREPAINT_VALIDATOR = BASE.validate_nonrepaint_audit


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def validate_registry_authority(registry_path: Path, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, str]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == AUTHORITY_HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing HYP009 comparator authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_ST009_EXISTING_RUN_RECOVERY_AUTHORIZED",
        "collector": validation.get("reviewed_recovery_collector_sha256") == sha256_file(args.artifact_collector.resolve()),
        "comparator": validation.get("reviewed_recovery_comparator_sha256") == sha256_file(Path(__file__).resolve()),
        "test": validation.get("reviewed_recovery_test_sha256") == sha256_file(args.test_source.resolve()),
        "collect_id": validation.get("artifact_collection_attempt_id") == COLLECTION_ATTEMPT_ID,
        "collect_limit": validation.get("artifact_collection_attempt_limit") == 1,
        "collect_unconsumed": metrics.get("artifact_collection_attempts_consumed") == 0,
        "compare": validation.get("comparator_execution_authorized") is True,
        "compare_id": validation.get("comparator_attempt_id") == COMPARATOR_ATTEMPT_ID,
        "compare_limit": validation.get("comparator_attempt_limit") == 1,
        "compare_unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "no_mt5": validation.get("mt5_authorized") is False and validation.get("mt5_parity_run_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_outcomes": validation.get("performance_metrics_authorized") is False,
        "no_live": validation.get("live_trading_authorized") is False,
        "no_compile": validation.get("compile_authorized") is False
        and validation.get("run_compile_authorized") is False
        and validation.get("mql5_compile_authorized") is False
        and validation.get("standalone_compile_authorized") is False,
        "no_trade_api": validation.get("trade_api_authorized") is False,
        "no_outcome_prices": validation.get("outcome_prices_authorized") is False and validation.get("post_event_ohlc_authorized") is False,
        "no_optimization": validation.get("optimization_authorized") is False,
        "no_validation": validation.get("validation_authorized") is False and validation.get("research_validation_access_authorized") is False,
        "no_holdout": validation.get("holdout_authorized") is False and validation.get("research_holdout_access_authorized") is False,
        "no_paper": validation.get("paper_trading_authorized") is False,
        "no_promotion": validation.get("promotion_eligible") is False,
        "no_market_edge": validation.get("market_edge_claim_authorized") is False,
        "no_retry_mutation": validation.get("same_id_retry_authorized") is False
        and validation.get("registry_mutation_allowed") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP009 comparator authority failed: {failed}")
    bound = {
        "oracle": (args.oracle, validation.get("oracle_sha256")),
        "oracle_start": (args.oracle_start, validation.get("oracle_start_sha256")),
        "oracle_report": (args.oracle_report, validation.get("oracle_report_sha256")),
        "oracle_receipt": (args.oracle_receipt, validation.get("oracle_receipt_sha256")),
        "oracle_terminal": (args.oracle_terminal, validation.get("oracle_terminal_sha256")),
        "mql_source": (args.mql_source, validation.get("reviewed_mql_source_sha256")),
        "test_source": (args.test_source, validation.get("reviewed_recovery_test_sha256")),
        "legacy_test": (args.legacy_test_source, validation.get("reviewed_hyp003_test_sha256")),
        "nonrepaint_manifest": (args.nonrepaint_manifest, validation.get("nonrepaint_manifest_sha256")),
        "nonrepaint_audit": (args.nonrepaint_audit, validation.get("nonrepaint_audit_sha256")),
        "contract_receipt": (args.contract_receipt, validation.get("hyp008_contract_receipt_sha256")),
        "collector": (args.artifact_collector, validation.get("reviewed_recovery_collector_sha256")),
        "authority_prereg": (args.authority_prereg, row.get("prereg_sha256")),
    }
    for label, (path, expected) in bound.items():
        BASE.require_bound_file(path.resolve(), str(expected or ""), label)
    return row, {
        "registry_sha256": sha256_file(registry_path),
        "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def validate_artifact_collection_chain(args: argparse.Namespace) -> None:
    receipt = load_json(args.artifact_receipt)
    terminal = load_json(args.artifact_terminal)
    if (
        receipt.get("schema_version") != "st009_existing_run_artifact_recovery_receipt.v1"
        or receipt.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or receipt.get("run_hypothesis_id") != RUN_HYPOTHESIS_ID
        or receipt.get("attempt_id") != COLLECTION_ATTEMPT_ID
        or receipt.get("summary_occurrences") != 2
        or receipt.get("summary_distinct") != 1
        or receipt.get("verdict") != "EXISTING_HYP008_ARTIFACT_RECOVERY_PASS"
        or receipt.get("orders_executed") != 0
        or receipt.get("trades_executed") != 0
        or receipt.get("economics_evaluated") is not False
    ):
        raise ValueError("HYP009 artifact recovery receipt mismatch")
    counters = receipt.get("counters", {})
    expected_counters = {
        "rows": 29460, "raw_events": 690, "executable_events": 683,
        "gap_rejected_events": 7, "long_events": 339, "short_events": 344,
    }
    if any(counters.get(key) != value for key, value in expected_counters.items()):
        raise ValueError("HYP009 artifact recovery counters mismatch")
    bindings = receipt.get("bindings", {})
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
    wrong_paths = [
        name for name, expected in canonical_paths.items()
        if actual_paths[name].resolve() != expected.resolve()
    ]
    if wrong_paths:
        raise ValueError(f"HYP009 canonical recovery path mismatch: {wrong_paths}")
    latest_raw = next(
        raw for raw in reversed(args.registry.resolve().read_bytes().splitlines())
        if raw.strip() and json.loads(raw.decode("utf-8")).get("hypothesis_id") == AUTHORITY_HYPOTHESIS_ID
    )
    if bindings.get("registry", {}).get("latest_row_sha256") != hashlib.sha256(latest_raw).hexdigest().upper():
        raise ValueError("HYP009 recovery receipt authority-row binding mismatch")
    exact_paths = {
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
    for label, path in exact_paths.items():
        binding = bindings.get(label, {})
        if not BASE.same_path(binding.get("path"), path.resolve()) or binding.get("sha256") != sha256_file(path.resolve()):
            raise ValueError(f"HYP009 artifact binding mismatch: {label}")
    if (
        bindings.get("common_csv", {}).get("sha256") != bindings.get("recovered_csv", {}).get("sha256")
        or bindings.get("compile_log", {}).get("sha256") != bindings.get("recovered_compile_log", {}).get("sha256")
        or bindings.get("common_csv", {}).get("captured_sha256") != EXPECTED_SOURCE_COMMON_SHA256
        or bindings.get("compile_log", {}).get("captured_sha256") != EXPECTED_COMPILE_SHA256
    ):
        raise ValueError("HYP009 mutable-source capture/recovery reconciliation mismatch")
    if (
        terminal.get("schema_version") != "st009_existing_run_artifact_recovery_terminal.v1"
        or terminal.get("hypothesis_id") != AUTHORITY_HYPOTHESIS_ID
        or terminal.get("attempt_id") != COLLECTION_ATTEMPT_ID
        or terminal.get("status") != "COMPLETE"
        or terminal.get("receipt_sha256") != sha256_file(args.artifact_receipt)
        or terminal.get("same_id_retry_authorized") is not False
    ):
        raise ValueError("HYP009 artifact recovery terminal mismatch")


def validate_inherited_nonrepaint(audit: Path, manifest: Path, *, require_collection_authority: bool) -> None:
    old = BASE.AUTHORITY_HYPOTHESIS_ID
    BASE.AUTHORITY_HYPOTHESIS_ID = RUN_HYPOTHESIS_ID
    try:
        ORIGINAL_NONREPAINT_VALIDATOR(audit, manifest, require_collection_authority=require_collection_authority)
    finally:
        BASE.AUTHORITY_HYPOTHESIS_ID = old


def validate_alpha_run(args: argparse.Namespace, authority_row: dict[str, Any]) -> dict[str, Any]:
    del authority_row
    run_dir = args.alpha_run_dir.resolve()
    manifest = load_json(args.run_manifest)
    exact = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": RUN_HYPOTHESIS_ID, "run_role": "control",
        "ea_name": "EA_SupertrendStateFlip", "symbol": "XAUUSD", "period": "H1",
        "from": "2005.01.01", "to": "2023.01.01", "model": 0,
        "execution_mode": 0, "fixed_delay_ms": 0, "overrides": BASE.EXACT_OVERRIDES,
        "telemetry_tier": "off", "telemetry_profile": "none", "deposit": 10000,
        "leverage": 100, "spread": "current",
    }
    wrong = [key for key, value in exact.items() if manifest.get(key) != value]
    if wrong or args.run_manifest.resolve() != run_dir / "run_manifest.json":
        raise ValueError(f"inherited HYP008 run contract mismatch: {wrong}")
    if sha256_file(args.run_manifest) != EXPECTED_RUN_MANIFEST_SHA256:
        raise ValueError("inherited HYP008 run manifest hash mismatch")
    if Path(str(manifest.get("local_run_dir", ""))).resolve() != run_dir:
        raise ValueError("inherited run local_run_dir mismatch")
    source_snapshot = run_dir / "snapshot/source/EA_SupertrendStateFlip.mq5"
    ex5_snapshot = run_dir / "snapshot/build/EA_SupertrendStateFlip.ex5"
    if (
        args.compiled_ex5.resolve() != ex5_snapshot
        or sha256_file(source_snapshot) != EXPECTED_SOURCE_SHA256
        or sha256_file(ex5_snapshot) != EXPECTED_EX5_SHA256
        or manifest.get("source_sha256") != EXPECTED_SOURCE_SHA256
        or manifest.get("ex5_sha256") != EXPECTED_EX5_SHA256
        or manifest.get("tester_ex5_sha256") != EXPECTED_EX5_SHA256
        or sha256_file(args.compile_log.resolve()) != EXPECTED_COMPILE_SHA256
        or sha256_file(args.tester_report.resolve()) != EXPECTED_REPORT_SHA256
        or manifest.get("report_sha256") != EXPECTED_REPORT_SHA256
        or manifest.get("contract_receipt_sha256") != sha256_file(args.contract_receipt.resolve())
    ):
        raise ValueError("inherited HYP008 source/compile/report binding mismatch")
    compile_text = BASE.decode_text(args.compile_log)
    if re.search(r"\b0\s+errors?\b", compile_text, re.I) is None or re.search(r"\b0\s+warnings?\b", compile_text, re.I) is None:
        raise ValueError("recovered compile log does not prove 0E/0W")
    journal = BASE.decode_text(args.tester_journal)
    if journal != FROZEN_SUMMARY + "\n" or "ST003_FATAL" in journal:
        raise ValueError("normalized HYP009 tester summary mismatch")

    analyzer_path = ROOT / "02. AlphaFactory/analysis/quant_analyzer.py"
    if sha256_file(analyzer_path) != BASE.QUANT_ANALYZER_SHA256:
        raise ValueError("quant analyzer hash drift")
    spec = importlib.util.spec_from_file_location("st009_quant_analyzer", analyzer_path)
    if not spec or not spec.loader:
        raise ValueError("cannot load quant analyzer")
    analyzer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analyzer
    spec.loader.exec_module(analyzer)
    if analyzer.parse_deals_from_html_report(args.tester_report):
        raise ValueError("zero-trade HYP008 report contains deals")
    BASE.tree_sha256(run_dir)
    return manifest


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def execute(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    if output_dir != COMPARATOR_ROOT.resolve():
        raise ValueError("HYP009 comparator output must use the canonical evidence root")
    authority_row, authority = validate_registry_authority(args.registry.resolve(), args)
    marker = BASE.claim_comparator(output_dir, authority)
    terminal_path = output_dir / "attempt_terminal.json"
    try:
        BASE.validate_oracle_chain(args)
        validate_inherited_nonrepaint(
            args.nonrepaint_audit, args.nonrepaint_manifest, require_collection_authority=True
        )
        validate_artifact_collection_chain(args)
        validate_alpha_run(args, authority_row)
        oracle = BASE.read_oracle(args.oracle.resolve())
        mql = BASE.read_mql(args.mql_audit.resolve())
        report = BASE.compare_rows(oracle, mql)
        replay = BASE.compare_rows(oracle, mql)
        if json_bytes(report) != json_bytes(replay):
            raise ValueError("HYP009 parity comparator replay mismatch")

        report_raw = json_bytes(report)
        report_path = output_dir / "st003_full_bar_parity_report.json"
        write_exclusive(report_path, report_raw)
        bindings = {
            "oracle": {"path": args.oracle.resolve().as_posix(), "sha256": sha256_file(args.oracle)},
            "mql_audit": {"path": args.mql_audit.resolve().as_posix(), "sha256": sha256_file(args.mql_audit)},
            "mql_source": {"path": args.mql_source.resolve().as_posix(), "sha256": sha256_file(args.mql_source)},
            "compiled_ex5": {"path": args.compiled_ex5.resolve().as_posix(), "sha256": sha256_file(args.compiled_ex5)},
            "test_source": {"path": args.test_source.resolve().as_posix(), "sha256": sha256_file(args.test_source)},
            "legacy_test_source": {"path": args.legacy_test_source.resolve().as_posix(), "sha256": sha256_file(args.legacy_test_source)},
            "alpha_run_directory": {"path": args.alpha_run_dir.resolve().as_posix(), "tree_sha256": BASE.tree_sha256(args.alpha_run_dir.resolve())},
            "run_manifest": {"path": args.run_manifest.resolve().as_posix(), "sha256": sha256_file(args.run_manifest)},
            "normalized_tester_summary": {"path": args.tester_journal.resolve().as_posix(), "sha256": sha256_file(args.tester_journal)},
            "tester_report": {"path": args.tester_report.resolve().as_posix(), "sha256": sha256_file(args.tester_report)},
            "recovered_compile_log": {"path": args.compile_log.resolve().as_posix(), "sha256": sha256_file(args.compile_log)},
            "contract_receipt": {"path": args.contract_receipt.resolve().as_posix(), "sha256": sha256_file(args.contract_receipt)},
            "artifact_collector": {"path": args.artifact_collector.resolve().as_posix(), "sha256": sha256_file(args.artifact_collector)},
            "artifact_recovery_receipt": {"path": args.artifact_receipt.resolve().as_posix(), "sha256": sha256_file(args.artifact_receipt)},
            "artifact_recovery_terminal": {"path": args.artifact_terminal.resolve().as_posix(), "sha256": sha256_file(args.artifact_terminal)},
            "nonrepaint_audit": {"path": args.nonrepaint_audit.resolve().as_posix(), "sha256": sha256_file(args.nonrepaint_audit)},
            "nonrepaint_manifest": {"path": args.nonrepaint_manifest.resolve().as_posix(), "sha256": sha256_file(args.nonrepaint_manifest)},
            "oracle_receipt": {"path": args.oracle_receipt.resolve().as_posix(), "sha256": sha256_file(args.oracle_receipt)},
            "oracle_terminal": {"path": args.oracle_terminal.resolve().as_posix(), "sha256": sha256_file(args.oracle_terminal)},
            "oracle_report": {"path": args.oracle_report.resolve().as_posix(), "sha256": sha256_file(args.oracle_report)},
            "authority_prereg": {"path": args.authority_prereg.resolve().as_posix(), "sha256": sha256_file(args.authority_prereg)},
            "candidate_registry": {"path": args.registry.resolve().as_posix(), **authority},
            "comparator": {"path": Path(__file__).resolve().as_posix(), "sha256": sha256_file(Path(__file__).resolve())},
            "attempt_started": {"path": marker.as_posix(), "sha256": sha256_file(marker)},
            "report": {"path": report_path.as_posix(), "sha256": hashlib.sha256(report_raw).hexdigest().upper()},
        }
        receipt = {
            "schema_version": "st009_full_bar_parity_receipt.v1",
            "authority_hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
            "run_hypothesis_id": RUN_HYPOTHESIS_ID,
            "target_hypothesis_id": TARGET_HYPOTHESIS_ID,
            "audit_run_id": BASE.AUDIT_RUN_ID,
            "attempt_id": COMPARATOR_ATTEMPT_ID,
            "bindings": bindings,
            "deterministic_replay": "PASS",
            "verdict": report["verdict"],
            "outcome_counters": {"orders": 0, "trades": 0, "returns": 0, "pnl": 0, "profit_factor": 0},
        }
        receipt_raw = json_bytes(receipt)
        receipt_path = output_dir / "st009_full_bar_parity_receipt.json"
        write_exclusive(receipt_path, receipt_raw)
        terminal = {
            "schema_version": "st009_full_bar_parity_terminal.v1",
            "authority_hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
            "run_hypothesis_id": RUN_HYPOTHESIS_ID,
            "target_hypothesis_id": TARGET_HYPOTHESIS_ID,
            "attempt_id": COMPARATOR_ATTEMPT_ID,
            "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "COMPLETE",
            "verdict": report["verdict"],
            "parity_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest().upper(),
            "same_id_retry_authorized": False,
        }
        write_exclusive(terminal_path, json_bytes(terminal))
        return report
    except Exception as exc:
        if not terminal_path.exists():
            write_exclusive(
                terminal_path,
                json_bytes(
                    {
                        "schema_version": "st009_full_bar_parity_terminal.v1",
                        "authority_hypothesis_id": AUTHORITY_HYPOTHESIS_ID,
                        "run_hypothesis_id": RUN_HYPOTHESIS_ID,
                        "target_hypothesis_id": TARGET_HYPOTHESIS_ID,
                        "attempt_id": COMPARATOR_ATTEMPT_ID,
                        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "status": "FAILED",
                        "verdict": "HYP009_FULL_BAR_PARITY_FAIL",
                        "error_type": type(exc).__name__,
                        "same_id_retry_authorized": False,
                    }
                ),
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "oracle", "oracle-start", "oracle-report", "oracle-receipt", "oracle-terminal",
        "mql-audit", "mql-source", "compiled-ex5", "test-source", "legacy-test-source",
        "alpha-run-dir", "run-manifest", "tester-journal", "tester-report", "compile-log",
        "contract-receipt", "artifact-collector", "artifact-receipt", "artifact-terminal",
        "nonrepaint-audit", "nonrepaint-manifest", "authority-prereg", "registry", "output-dir",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()

    BASE.AUTHORITY_HYPOTHESIS_ID = AUTHORITY_HYPOTHESIS_ID
    BASE.COMPARATOR_ATTEMPT_ID = COMPARATOR_ATTEMPT_ID
    BASE.__file__ = str(Path(__file__).resolve())
    BASE.validate_registry_authority = validate_registry_authority
    BASE.validate_artifact_collection_chain = validate_artifact_collection_chain
    BASE.validate_nonrepaint_audit = validate_inherited_nonrepaint
    BASE.validate_alpha_run = validate_alpha_run
    report = execute(args)
    print(json_bytes(report).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
